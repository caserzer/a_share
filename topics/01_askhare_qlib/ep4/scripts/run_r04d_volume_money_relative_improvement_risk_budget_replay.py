#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_csv, write_json  # noqa: E402
from run_r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic import (  # noqa: E402
    _artifact_hashes,
    _bool_series,
    _date_str,
    _hash_file,
    _hash_json,
    _hash_text,
    _load_calendar,
    _load_price_panel,
    _price_source_hash,
    _quantile,
    _safe_div,
    _split_bounds,
    _split_for_date,
    _to_bool,
    _wilson,
)


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04d_volume_money_relative_improvement_risk_budget_replay_v1.yaml"
FINAL_DECISIONS = {
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_upstream_r04c_state_changed",
    "blocked_pool_reconstruction_failed",
    "blocked_gate0_metric_replay_spec_failed",
    "blocked_policy_matrix_invalid",
    "blocked_selection_leakage_detected",
    "r04d_no_policy_passed_validation",
    "r04d_policy_validation_only_not_robust",
    "r04d_policy_passed_relative_improvement_diagnostic_only",
    "r04d_policy_strong_pass_diagnostic_only",
}


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _weighted_mean(frame: pd.DataFrame, value_col: str, weight_col: str = "event_weight") -> float:
    if frame.empty or value_col not in frame.columns:
        return np.nan
    values = pd.to_numeric(frame[value_col], errors="coerce")
    weights = pd.to_numeric(frame[weight_col], errors="coerce")
    mask = values.notna() & weights.notna() & (weights > 0)
    if not bool(mask.any()):
        return np.nan
    return float(np.average(values[mask], weights=weights[mask]))


def _weighted_quantile(values: pd.Series, weights: pd.Series, q: float) -> float:
    values = pd.to_numeric(values, errors="coerce")
    weights = pd.to_numeric(weights, errors="coerce")
    mask = values.notna() & weights.notna() & (weights > 0)
    if not bool(mask.any()):
        return np.nan
    v = values[mask].to_numpy(float)
    w = weights[mask].to_numpy(float)
    order = np.argsort(v)
    v = v[order]
    w = w[order]
    cdf = np.cumsum(w) / np.sum(w)
    return float(v[np.searchsorted(cdf, q, side="left").clip(0, len(v) - 1)])


def _event_id(pool_id: str, instrument: Any, anchor: Any, source_id: Any = "") -> str:
    return _hash_text(f"{pool_id}|{instrument}|{_date_str(anchor)}|{source_id}")


def _collapse_volume_money_from_r02(config: dict[str, Any], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    panel_path = topic_path(config["upstream_r02_family_precision"]["action_time_panel"])
    cols = [
        "instrument_id",
        "trade_date",
        "split",
        "condition_group_id",
        "family_id",
        "condition_text",
        "base_action_time_eligible_flag",
        "feature_complete_flag",
        "signal_occurs",
        "signal_episode_id",
    ]
    raw = pd.read_parquet(panel_path, columns=cols)
    family = str(config["pool"]["family_id"])
    pool_id = str(config["pool"]["pool_id"])
    raw["instrument_id"] = raw["instrument_id"].astype(str).str.upper()
    raw["trade_date"] = pd.to_datetime(raw["trade_date"]).dt.normalize()
    eligible = raw[
        raw["family_id"].astype(str).eq(family)
        & raw["signal_occurs"].map(_to_bool)
        & raw["feature_complete_flag"].map(_to_bool)
        & raw["base_action_time_eligible_flag"].map(_to_bool)
    ].copy()
    cal_map = {pd.Timestamp(date): idx for idx, date in enumerate(calendar)}
    gap = int(config["pool"]["episode_gap_trading_days"])
    rows: list[dict[str, Any]] = []
    for instrument, part in eligible.sort_values(["instrument_id", "trade_date"]).groupby("instrument_id", sort=False):
        current: dict[str, Any] | None = None
        prev_idx: int | None = None
        trigger_count = 0
        for row in part.itertuples(index=False):
            dt = pd.Timestamp(row.trade_date).normalize()
            idx = cal_map.get(dt)
            if idx is None:
                continue
            new_episode = current is None or prev_idx is None or idx - prev_idx > gap
            if new_episode:
                if current is not None:
                    current["episode_trigger_count"] = trigger_count
                    rows.append(current)
                source_id = str(getattr(row, "signal_episode_id", "")) or f"{instrument}|{dt.date()}"
                current = {
                    "pool_id": pool_id,
                    "instrument_id": str(instrument).upper(),
                    "anchor_signal_date": dt,
                    "source_split": row.split,
                    "source_event_id": source_id,
                    "condition_group_id": getattr(row, "condition_group_id", ""),
                    "condition_text": getattr(row, "condition_text", ""),
                }
                trigger_count = 1
            else:
                trigger_count += 1
            prev_idx = idx
        if current is not None:
            current["episode_trigger_count"] = trigger_count
            rows.append(current)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["pool_event_id"] = [
        _event_id(pool_id, row.instrument_id, row.anchor_signal_date, row.source_event_id)
        for row in out.itertuples(index=False)
    ]
    return out


def _load_event_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    r04c = config["upstream_r04c"]
    events = pd.read_parquet(topic_path(r04c["pool_event_panel"]))
    matched = pd.read_parquet(topic_path(r04c["matched_baseline_panel"]))
    profile = pd.read_csv(topic_path(r04c["hold120_pool_profile"]))
    return events, matched, profile


def _reconstruction_audit(config: dict[str, Any], r02_events: pd.DataFrame, r04c_events: pd.DataFrame, price: pd.DataFrame) -> pd.DataFrame:
    pool_id = str(config["pool"]["pool_id"])
    r04c_vm = r04c_events[r04c_events["pool_id"].eq(pool_id)].copy()
    overlap = r02_events[["pool_event_id", "instrument_id", "anchor_signal_date"]].merge(
        r04c_vm[["pool_event_id", "instrument_id", "anchor_signal_date", "entry_execution_date", "entry_price"]],
        on="pool_event_id",
        how="inner",
        suffixes=("_r04d", "_r04c"),
    )
    overlap["instrument_id"] = overlap["instrument_id_r04c"].astype(str).str.upper()
    price_entry = price[["instrument_id", "trade_date", "adjusted_open"]].rename(
        columns={"trade_date": "entry_execution_date", "adjusted_open": "r04d_entry_price"}
    )
    overlap["entry_execution_date"] = pd.to_datetime(overlap["entry_execution_date"]).dt.normalize()
    overlap = overlap.merge(price_entry, on=["instrument_id", "entry_execution_date"], how="left")
    overlap["entry_price_rel_diff"] = (overlap["r04d_entry_price"] / pd.to_numeric(overlap["entry_price"], errors="coerce") - 1.0).abs()
    anchor_mismatch = int(
        (
            pd.to_datetime(overlap["anchor_signal_date_r04d"]).dt.normalize()
            != pd.to_datetime(overlap["anchor_signal_date_r04c"]).dt.normalize()
        ).sum()
    ) if len(overlap) else 0
    tol = float(config["pool"]["max_entry_price_rel_diff"])
    p95 = _quantile(overlap["entry_price_rel_diff"], 0.95) if len(overlap) else np.nan
    max_diff = float(pd.to_numeric(overlap["entry_price_rel_diff"], errors="coerce").max()) if len(overlap) else np.nan
    status = (
        "passed"
        if _safe_div(len(overlap), len(r02_events)) >= 0.99
        and _safe_div(len(overlap), len(r04c_vm)) >= 0.99
        and (pd.isna(p95) or p95 <= tol)
        else "failed"
    )
    return pd.DataFrame(
        [
            {
                "pool_id": pool_id,
                "r04d_reconstructed_event_count": int(len(r02_events)),
                "r04c_volume_money_event_count": int(len(r04c_vm)),
                "overlap_event_count": int(len(overlap)),
                "overlap_share_vs_r04d": _safe_div(len(overlap), len(r02_events)),
                "overlap_share_vs_r04c": _safe_div(len(overlap), len(r04c_vm)),
                "anchor_date_mismatch_count": anchor_mismatch,
                "entry_date_mismatch_count": 0,
                "entry_price_rel_diff_p95": p95,
                "entry_price_rel_diff_max": max_diff,
                "entry_price_rel_diff_tolerance": tol,
                "reconciliation_status": status,
            }
        ]
    )


def _baseline_profile_context(config: dict[str, Any], profile: pd.DataFrame) -> pd.DataFrame:
    baseline_pool = str(config["pool"]["baseline_pool_id"])
    cols = ["split", "net_return_mean", "net_return_p10", "loss_le_minus5_rate"]
    out = profile[profile["pool_id"].eq(baseline_pool)][cols].copy()
    return out.rename(
        columns={
            "net_return_mean": "baseline_A_r04c_hold120_net_return_mean",
            "net_return_p10": "baseline_A_r04c_hold120_net_return_p10",
            "loss_le_minus5_rate": "baseline_A_r04c_hold120_loss_le_minus5_rate",
        }
    )


def _prepare_base_events(config: dict[str, Any], r04c_events: pd.DataFrame, matched_panel: pd.DataFrame) -> pd.DataFrame:
    pool_id = str(config["pool"]["pool_id"])
    baseline_pool = str(config["pool"]["baseline_pool_id"])
    vm = r04c_events[r04c_events["pool_id"].eq(pool_id)].copy()
    vm["replay_universe"] = "volume_money"
    vm["event_weight"] = 1.0
    matched = matched_panel[matched_panel["pool_id"].eq(pool_id)].copy()
    baseline = r04c_events[r04c_events["pool_id"].eq(baseline_pool)].copy()
    mb = matched.merge(
        baseline,
        left_on="baseline_pool_event_id",
        right_on="pool_event_id",
        how="left",
        suffixes=("_match", ""),
    )
    mb["replay_universe"] = "matched_baseline_A"
    mb["event_weight"] = pd.to_numeric(mb["weight"], errors="coerce").fillna(0.0)
    vm_cols = [
        "replay_universe",
        "event_weight",
        "pool_event_id",
        "source_event_id",
        "pool_id",
        "instrument_id",
        "anchor_signal_date",
        "split",
        "entry_execution_date",
        "entry_price",
        "entry_calendar_index",
        "market_regime_bucket",
        "industry_regime_bucket",
        "industry_target_key",
    ]
    for col in vm_cols:
        if col not in vm.columns:
            vm[col] = np.nan
        if col not in mb.columns:
            mb[col] = np.nan
    base = pd.concat([vm[vm_cols], mb[vm_cols]], ignore_index=True)
    base["source_pool_event_id"] = base["pool_event_id"].astype(str)
    base["r04d_event_id"] = base["replay_universe"].astype(str) + "|" + base["source_pool_event_id"].astype(str)
    base["instrument_id"] = base["instrument_id"].astype(str).str.upper()
    base["anchor_signal_date"] = pd.to_datetime(base["anchor_signal_date"]).dt.normalize()
    base["entry_execution_date"] = pd.to_datetime(base["entry_execution_date"]).dt.normalize()
    base["entry_price"] = pd.to_numeric(base["entry_price"], errors="coerce")
    base["split"] = base["split"].astype(str)
    return base.drop_duplicates(["r04d_event_id"]).reset_index(drop=True)


def _attach_entry_reconciliation(base: pd.DataFrame, price: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    price_entry = price[
        [
            "instrument_id",
            "trade_date",
            "calendar_index",
            "adjusted_open",
            "volume",
            "money",
            "suspended_or_dirty_bar",
        ]
    ].rename(
        columns={
            "trade_date": "entry_execution_date",
            "calendar_index": "r04d_entry_calendar_index",
            "adjusted_open": "r04d_replay_entry_price",
        }
    )
    out = base.merge(price_entry, on=["instrument_id", "entry_execution_date"], how="left")
    out["entry_price_rel_diff"] = (out["r04d_replay_entry_price"] / out["entry_price"] - 1.0).abs()
    tol = float(config["pool"]["max_entry_price_rel_diff"])
    executable = (
        (out["r04d_replay_entry_price"] > 0)
        & (out["volume"] > 0)
        & (out["money"] > 0)
        & (~_bool_series(out["suspended_or_dirty_bar"], default=True))
    )
    out["entry_reconciliation_status"] = np.where(
        out["r04d_replay_entry_price"].isna(),
        "missing_r04d_entry_price",
        np.where(out["entry_price_rel_diff"] > tol, "failed_price_mismatch", "passed"),
    )
    out["entry_valid_r04d"] = executable & out["entry_reconciliation_status"].eq("passed")
    out["entry_calendar_index"] = out["r04d_entry_calendar_index"]
    return out


def _build_policy_matrix(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    baseline_id = str(config["baseline"]["volume_money_hold120_baseline_policy_id"])
    for hold in config["policy_grid"]["holds"]:
        hold_id = str(hold["hold_rule_id"])
        max_hold = int(hold["max_holding_days"])
        for sizing_rule_id in ["fixed_size", "volatility_scaled"]:
            sizing_cfg = config["policy_grid"]["sizing"][sizing_rule_id]
            exit_specs: list[tuple[str, dict[str, Any]]] = [("no_exit", {})]
            for n in config["policy_grid"]["exits"]["time_stop"]["time_stop_days"]:
                exit_specs.append(("time_stop", {"time_stop_days": int(n)}))
            for activation in config["policy_grid"]["exits"]["break_even_after_gain"]["activation_gain_pct"]:
                exit_specs.append(("break_even_after_gain", {"activation_gain_pct": float(activation)}))
            for stop in config["policy_grid"]["exits"]["fixed_stop"]["stop_loss_pct"]:
                exit_specs.append(("fixed_stop", {"stop_loss_pct": float(stop)}))
            for exit_family, params in exit_specs:
                invalid = ""
                effective_static_offset: int | None = None
                if exit_family == "no_exit":
                    effective_static_offset = max_hold
                if exit_family == "time_stop":
                    if int(params["time_stop_days"]) >= max_hold:
                        invalid = "time_stop_days_ge_max_holding_days"
                    else:
                        effective_static_offset = int(params["time_stop_days"])
                if exit_family == "no_exit" and hold_id == "hold_120d" and sizing_rule_id == "fixed_size":
                    policy_id = baseline_id
                else:
                    param_part = "none" if not params else "_".join(f"{k}{v:g}" for k, v in sorted(params.items()))
                    policy_id = f"{hold_id}__{exit_family}__{param_part}__{sizing_rule_id}".replace("-", "m").replace(".", "p")
                formula = f"hold={max_hold};exit={exit_family};params={_canonical_json(params)};sizing={sizing_rule_id}"
                rows.append(
                    {
                        "policy_id": policy_id,
                        "policy_family_id": f"{exit_family}__{sizing_rule_id}",
                        "hold_rule_id": hold_id,
                        "hold_rule_max_days": max_hold,
                        "exit_rule_family_id": exit_family,
                        "exit_rule_id": exit_family if not params else f"{exit_family}__{_hash_json(params)[:8]}",
                        "sizing_rule_id": sizing_rule_id,
                        "parameter_set_id": _hash_text(f"{exit_family}|{_canonical_json(params)}|{sizing_rule_id}")[:12],
                        "parameter_values_json": _canonical_json({"exit": params, "sizing": sizing_cfg}),
                        "effective_static_exit_offset": effective_static_offset,
                        "is_train_selectable": invalid == "",
                        "is_validation_selectable": invalid == "",
                        "invalid_policy_reason": invalid,
                        "duplicate_policy_group_id": "",
                        "canonical_policy_id": policy_id,
                        "formula_text": formula,
                        "formula_hash": _hash_text(formula),
                    }
                )
    matrix = pd.DataFrame(rows)
    dup_candidates = matrix[matrix["invalid_policy_reason"].eq("") & matrix["effective_static_exit_offset"].notna()].copy()
    dup_candidates["_priority"] = np.where(dup_candidates["exit_rule_family_id"].eq("no_exit"), 0, 1)
    for (sizing, offset), part in dup_candidates.groupby(["sizing_rule_id", "effective_static_exit_offset"], dropna=False):
        if len(part) <= 1:
            continue
        canonical = part.sort_values(["_priority", "hold_rule_max_days", "policy_id"]).iloc[0]["policy_id"]
        group_id = f"static_exit_offset_{int(offset)}__{sizing}"
        idx = matrix["policy_id"].isin(part["policy_id"])
        matrix.loc[idx, "duplicate_policy_group_id"] = group_id
        matrix.loc[idx, "canonical_policy_id"] = canonical
        noncanon = idx & ~matrix["policy_id"].eq(canonical)
        matrix.loc[noncanon, "is_train_selectable"] = False
        matrix.loc[noncanon, "is_validation_selectable"] = False
        matrix.loc[noncanon, "invalid_policy_reason"] = "duplicate_equivalent_policy"
    matrix = matrix.drop(columns=["effective_static_exit_offset"])
    return matrix.sort_values(["policy_family_id", "hold_rule_max_days", "policy_id"]).reset_index(drop=True)


def _build_daily_path(base: pd.DataFrame, price: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    lookback = int(config["execution"]["pre_entry_lookback_trading_days"])
    max_offset = int(config["execution"]["max_holding_days"]) + int(config["execution"]["max_exit_execution_lag_trading_days"])
    offsets = np.arange(-lookback, max_offset + 1, dtype=int)
    left = pd.DataFrame(
        {
            "r04d_event_id": np.repeat(base["r04d_event_id"].to_numpy(), len(offsets)),
            "replay_universe": np.repeat(base["replay_universe"].to_numpy(), len(offsets)),
            "source_pool_event_id": np.repeat(base["source_pool_event_id"].to_numpy(), len(offsets)),
            "instrument_id": np.repeat(base["instrument_id"].to_numpy(), len(offsets)),
            "split": np.repeat(base["split"].to_numpy(), len(offsets)),
            "entry_execution_date": np.repeat(base["entry_execution_date"].to_numpy(), len(offsets)),
            "entry_calendar_index": np.repeat(base["entry_calendar_index"].to_numpy(), len(offsets)),
            "entry_price": np.repeat(base["r04d_replay_entry_price"].to_numpy(), len(offsets)),
            "calendar_offset": np.tile(offsets, len(base)),
        }
    )
    left["calendar_index"] = left["entry_calendar_index"].astype(float) + left["calendar_offset"]
    left = left[left["calendar_index"].notna()].copy()
    left["calendar_index"] = left["calendar_index"].astype(int)
    keep_cols = [
        "instrument_id",
        "calendar_index",
        "trade_date",
        "adjusted_open",
        "adjusted_close",
        "volume",
        "money",
        "suspended_or_dirty_bar",
        "stock_realized_vol_20d_asof_entry",
    ]
    out = left.merge(price[keep_cols], on=["instrument_id", "calendar_index"], how="left")
    out["executable_open_flag"] = (
        (out["adjusted_open"] > 0)
        & (out["volume"] > 0)
        & (out["money"] > 0)
        & (~_bool_series(out["suspended_or_dirty_bar"], default=True))
    )
    out["gross_adjusted_close_return_from_entry"] = out["adjusted_close"] / out["entry_price"] - 1.0
    return out.sort_values(["r04d_event_id", "calendar_offset"]).reset_index(drop=True)


def _attach_hold120_labels(base: pd.DataFrame, daily_path: pd.DataFrame, threshold: float) -> pd.DataFrame:
    post = daily_path[(daily_path["calendar_offset"] >= 0) & (daily_path["calendar_offset"] <= 120)].copy()
    agg = (
        post.groupby("r04d_event_id", as_index=False)
        .agg(
            gross_max_adjusted_close_return_from_entry_to_day120=("gross_adjusted_close_return_from_entry", "max"),
            path_close_count_0_120=("adjusted_close", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())),
        )
    )
    hits = post.loc[post["gross_adjusted_close_return_from_entry"] >= threshold].sort_values(["r04d_event_id", "calendar_offset"])
    first_hit = hits.drop_duplicates("r04d_event_id")[
        ["r04d_event_id", "trade_date", "calendar_offset"]
    ].rename(columns={"trade_date": "volume_money_hold120_first_plus50_hit_date", "calendar_offset": "volume_money_hold120_first_plus50_hit_offset"})
    out = base.merge(agg, on="r04d_event_id", how="left").merge(first_hit, on="r04d_event_id", how="left")
    out["volume_money_hold120_max_gain50_flag"] = out["gross_max_adjusted_close_return_from_entry_to_day120"] >= threshold
    return out


def _event_data(path: pd.DataFrame) -> dict[str, Any]:
    offsets = path["calendar_offset"].to_numpy(int)
    order = np.argsort(offsets)
    offsets = offsets[order]
    idx = {int(offset): i for i, offset in enumerate(offsets)}
    data = {"offsets": offsets, "idx": idx}
    for col in [
        "trade_date",
        "adjusted_open",
        "adjusted_close",
        "volume",
        "money",
        "suspended_or_dirty_bar",
        "executable_open_flag",
        "gross_adjusted_close_return_from_entry",
        "stock_realized_vol_20d_asof_entry",
    ]:
        data[col] = path[col].to_numpy()[order]
    return data


def _value(data: dict[str, Any], col: str, offset: int) -> Any:
    pos = data["idx"].get(int(offset))
    if pos is None:
        return np.nan
    return data[col][pos]


def _valid_closes(data: dict[str, Any], max_offset: int) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
    offsets = np.arange(0, max_offset + 1)
    values = np.array([_value(data, "gross_adjusted_close_return_from_entry", int(offset)) for offset in offsets], dtype=float)
    if not np.isfinite(values).all():
        return None, None
    return offsets, values


def _first_executable(data: dict[str, Any], signal_offset: int, max_lag: int) -> tuple[int | None, Any]:
    for offset in range(signal_offset + 1, signal_offset + max_lag + 1):
        flag = _value(data, "executable_open_flag", offset)
        price = _value(data, "adjusted_open", offset)
        date = _value(data, "trade_date", offset)
        if bool(flag) and np.isfinite(float(price)) and float(price) > 0:
            return offset, date
    return None, pd.NaT


def _position_weight(data: dict[str, Any], sizing_rule_id: str, config: dict[str, Any]) -> tuple[float, str]:
    if sizing_rule_id == "fixed_size":
        return 1.0, ""
    if sizing_rule_id == "volatility_scaled":
        vol = _value(data, "stock_realized_vol_20d_asof_entry", 0)
        if not np.isfinite(float(vol)) or float(vol) <= 0:
            return np.nan, "censored_by_missing_required_indicator"
        cfg = config["policy_grid"]["sizing"]["volatility_scaled"]
        return float(np.clip(float(cfg["target_vol"]) / float(vol), float(cfg["min_weight"]), float(cfg["max_weight"]))), ""
    return np.nan, "invalid_entry"


def _signal_offset(data: dict[str, Any], policy: pd.Series) -> tuple[int | None, str]:
    family = str(policy["exit_rule_family_id"])
    params_all = json.loads(policy["parameter_values_json"]) if str(policy["parameter_values_json"]) else {}
    params = params_all.get("exit", {})
    max_hold = int(policy["hold_rule_max_days"])
    offsets, returns = _valid_closes(data, max_hold)
    if offsets is None:
        return None, "censored_by_missing_price"
    if family == "no_exit":
        return max_hold, ""
    if family == "time_stop":
        return int(params["time_stop_days"]), ""
    if family == "fixed_stop":
        hit = np.where(returns <= float(params["stop_loss_pct"]))[0]
        return int(offsets[hit[0]]) if len(hit) else max_hold, ""
    if family == "break_even_after_gain":
        activated = False
        for offset, ret in zip(offsets, returns):
            if not activated and ret >= float(params["activation_gain_pct"]):
                activated = True
            if activated and ret <= 0.0:
                return int(offset), ""
        return max_hold, ""
    return None, "invalid_entry"


def _replay_event_policy(
    row: pd.Series,
    data: dict[str, Any],
    policy: pd.Series,
    config: dict[str, Any],
    bounds: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
) -> dict[str, Any]:
    base = {
        "r04d_event_id": row["r04d_event_id"],
        "source_pool_event_id": row["source_pool_event_id"],
        "replay_universe": row["replay_universe"],
        "event_weight": float(row.get("event_weight", 1.0)),
        "policy_id": policy["policy_id"],
        "policy_family_id": policy["policy_family_id"],
        "hold_rule_id": policy["hold_rule_id"],
        "exit_rule_id": policy["exit_rule_id"],
        "exit_rule_family_id": policy["exit_rule_family_id"],
        "sizing_rule_id": policy["sizing_rule_id"],
        "parameter_set_id": policy["parameter_set_id"],
        "parameter_values_json": policy["parameter_values_json"],
        "split": row["split"],
        "instrument_id": row["instrument_id"],
        "entry_execution_date": row["entry_execution_date"],
        "entry_price": row["r04d_replay_entry_price"],
        "market_regime_bucket": row.get("market_regime_bucket", ""),
        "industry_regime_bucket": row.get("industry_regime_bucket", ""),
        "calendar_year": int(pd.Timestamp(row["entry_execution_date"]).year),
        "volume_money_hold120_max_gain50_flag": bool(row.get("volume_money_hold120_max_gain50_flag", False)),
        "volume_money_hold120_first_plus50_hit_date": row.get("volume_money_hold120_first_plus50_hit_date", pd.NaT),
        "net_return_metric_basis": "weighted_net_return",
    }
    if not bool(row.get("entry_valid_r04d", False)):
        return {**base, "replay_status": "invalid_entry", "replay_complete": False}
    weight, weight_status = _position_weight(data, str(policy["sizing_rule_id"]), config)
    if weight_status:
        return {**base, "position_weight": np.nan, "replay_status": weight_status, "replay_complete": False}
    signal_offset, signal_status = _signal_offset(data, policy)
    if signal_status:
        return {**base, "position_weight": weight, "replay_status": signal_status, "replay_complete": False}
    exec_offset, exec_date = _first_executable(data, int(signal_offset), int(config["execution"]["max_exit_execution_lag_trading_days"]))
    if exec_offset is None:
        return {**base, "position_weight": weight, "exit_signal_offset": signal_offset, "replay_status": "censored_by_no_exit_execution", "replay_complete": False}
    if _split_for_date(exec_date, bounds) != str(row["split"]):
        return {
            **base,
            "position_weight": weight,
            "exit_signal_offset": signal_offset,
            "exit_execution_offset": exec_offset,
            "exit_execution_date": exec_date,
            "replay_status": "censored_by_split_boundary",
            "replay_complete": False,
        }
    exit_price = _value(data, "adjusted_open", int(exec_offset))
    entry_price = float(row["r04d_replay_entry_price"])
    gross_return = float(exit_price) / entry_price - 1.0
    cost = config["cost_model"]
    entry_cost = (float(cost["entry_slippage_bps"]) + float(cost["commission_bps_per_side"])) / 10000.0
    exit_cost = (float(cost["exit_slippage_bps"]) + float(cost["commission_bps_per_side"]) + float(cost["stamp_tax_bps_on_exit"])) / 10000.0
    total_cost_bps = float(cost["entry_slippage_bps"]) + float(cost["exit_slippage_bps"]) + 2.0 * float(cost["commission_bps_per_side"]) + float(cost["stamp_tax_bps_on_exit"])
    unweighted_net_return = gross_return - entry_cost - exit_cost
    weighted_net_return = float(weight) * unweighted_net_return
    offsets, close_returns = _valid_closes(data, int(signal_offset))
    max_adverse = float(np.nanmin(close_returns)) if offsets is not None else np.nan
    first_hit = pd.to_datetime(row.get("volume_money_hold120_first_plus50_hit_date"), errors="coerce")
    retained = bool(row.get("volume_money_hold120_max_gain50_flag", False)) and not pd.isna(first_hit) and pd.Timestamp(exec_date) > first_hit
    return {
        **base,
        "position_weight": weight,
        "exit_signal_offset": int(signal_offset),
        "exit_signal_date": _value(data, "trade_date", int(signal_offset)),
        "exit_execution_offset": int(exec_offset),
        "exit_execution_date": exec_date,
        "exit_price": float(exit_price),
        "gross_return": gross_return,
        "entry_cost": entry_cost,
        "exit_cost": exit_cost,
        "total_cost_bps": total_cost_bps,
        "unweighted_net_return": unweighted_net_return,
        "weighted_net_return": weighted_net_return,
        "net_return": weighted_net_return,
        "loss_le_minus5_flag": weighted_net_return <= -0.05,
        "loss_le_minus10_flag": weighted_net_return <= -0.10,
        "max_adverse_excursion": max_adverse,
        "avg_holding_days": int(exec_offset),
        "policy_retained_max_gain50_flag": retained,
        "replay_status": "replay_complete",
        "replay_complete": True,
    }


def _replay_policies(base: pd.DataFrame, daily_path: pd.DataFrame, policy_matrix: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    bounds = _split_bounds(config)
    valid_policies = policy_matrix[policy_matrix["invalid_policy_reason"].fillna("").eq("")].reset_index(drop=True)
    path_groups = {eid: _event_data(part) for eid, part in daily_path.groupby("r04d_event_id", sort=False)}
    rows: list[dict[str, Any]] = []
    for idx, event in base.iterrows():
        data = path_groups.get(event["r04d_event_id"])
        for _, policy in valid_policies.iterrows():
            if data is None:
                rows.append(
                    {
                        "r04d_event_id": event["r04d_event_id"],
                        "source_pool_event_id": event["source_pool_event_id"],
                        "replay_universe": event["replay_universe"],
                        "event_weight": event.get("event_weight", 1.0),
                        "policy_id": policy["policy_id"],
                        "policy_family_id": policy["policy_family_id"],
                        "hold_rule_id": policy["hold_rule_id"],
                        "exit_rule_id": policy["exit_rule_id"],
                        "exit_rule_family_id": policy["exit_rule_family_id"],
                        "sizing_rule_id": policy["sizing_rule_id"],
                        "parameter_set_id": policy["parameter_set_id"],
                        "parameter_values_json": policy["parameter_values_json"],
                        "split": event["split"],
                        "instrument_id": event["instrument_id"],
                        "replay_status": "censored_by_missing_price",
                        "replay_complete": False,
                        "net_return_metric_basis": "weighted_net_return",
                    }
                )
            else:
                rows.append(_replay_event_policy(event, data, policy, config, bounds))
        if (idx + 1) % 1000 == 0:
            print(f"replayed {idx + 1:,}/{len(base):,} R04d events", flush=True)
    replay = pd.DataFrame(rows)
    replay["replay_complete"] = _bool_series(replay["replay_complete"])
    return replay


def _summarize_volume(replay: pd.DataFrame, config: dict[str, Any], baseline_context: pd.DataFrame) -> pd.DataFrame:
    volume = replay[replay["replay_universe"].eq("volume_money")].copy()
    rows: list[dict[str, Any]] = []
    group_cols = [
        "policy_id",
        "policy_family_id",
        "hold_rule_id",
        "exit_rule_family_id",
        "sizing_rule_id",
        "parameter_set_id",
        "parameter_values_json",
        "split",
    ]
    for keys, part in volume.groupby(group_cols, dropna=False, sort=False):
        rec = dict(zip(group_cols, keys))
        complete = part[_bool_series(part["replay_complete"])].copy()
        event_count = int(len(part))
        replay_complete_count = int(len(complete))
        hold_winners = part[_bool_series(part["volume_money_hold120_max_gain50_flag"])]
        retained = int(_bool_series(hold_winners["policy_retained_max_gain50_flag"]).sum()) if len(hold_winners) else 0
        hold_count = int(len(hold_winners))
        lo, hi = _wilson(retained, hold_count)
        rec.update(
            {
                "event_count": event_count,
                "replay_complete_count": replay_complete_count,
                "censored_count": int(event_count - replay_complete_count),
                "censored_share": _safe_div(event_count - replay_complete_count, event_count),
                "net_return_mean": float(complete["weighted_net_return"].mean()) if replay_complete_count else np.nan,
                "net_return_median": _quantile(complete["weighted_net_return"], 0.50),
                "net_return_p10": _quantile(complete["weighted_net_return"], 0.10),
                "net_return_p25": _quantile(complete["weighted_net_return"], 0.25),
                "net_return_p75": _quantile(complete["weighted_net_return"], 0.75),
                "net_return_p90": _quantile(complete["weighted_net_return"], 0.90),
                "unweighted_net_return_mean": float(complete["unweighted_net_return"].mean()) if replay_complete_count else np.nan,
                "unweighted_net_return_p10": _quantile(complete["unweighted_net_return"], 0.10),
                "weighted_net_return_mean": float(complete["weighted_net_return"].mean()) if replay_complete_count else np.nan,
                "weighted_net_return_p10": _quantile(complete["weighted_net_return"], 0.10),
                "loss_le_minus5_rate": float(complete["loss_le_minus5_flag"].mean()) if replay_complete_count else np.nan,
                "loss_le_minus10_rate": float(complete["loss_le_minus10_flag"].mean()) if replay_complete_count else np.nan,
                "max_drawdown_p50": _quantile(complete["max_adverse_excursion"], 0.50),
                "max_drawdown_p90": _quantile(complete["max_adverse_excursion"], 0.90),
                "max_gain50_count": hold_count,
                "max_gain50_rate": _safe_div(hold_count, event_count),
                "max_gain50_retention_vs_volume_money_hold120": _safe_div(retained, hold_count),
                "max_gain50_retention_wilson_lower": lo,
                "max_gain50_retention_wilson_upper": hi,
                "policy_retained_max_gain50_count": retained,
                "avg_holding_days": float(complete["avg_holding_days"].mean()) if replay_complete_count else np.nan,
                "position_weight_mean": float(complete["position_weight"].mean()) if replay_complete_count else np.nan,
                "position_weight_p10": _quantile(complete["position_weight"], 0.10),
                "turnover_proxy": _safe_div(252.0, float(complete["avg_holding_days"].mean()) if replay_complete_count else np.nan),
                "cost_bps_mean": float(complete["total_cost_bps"].mean()) if replay_complete_count else np.nan,
                "net_return_metric_basis": "weighted_net_return",
            }
        )
        rows.append(rec)
    summary = pd.DataFrame(rows)
    baseline_id = str(config["baseline"]["volume_money_hold120_baseline_policy_id"])
    baseline = summary[summary["policy_id"].eq(baseline_id)][
        ["split", "net_return_mean", "net_return_p10", "loss_le_minus5_rate", "max_gain50_rate"]
    ].rename(
        columns={
            "net_return_mean": "volume_money_hold120_net_return_mean",
            "net_return_p10": "volume_money_hold120_net_return_p10",
            "loss_le_minus5_rate": "volume_money_hold120_loss_le_minus5_rate",
            "max_gain50_rate": "volume_money_hold120_max_gain50_rate",
        }
    )
    summary = summary.merge(baseline, on="split", how="left")
    summary["net_return_mean_delta_vs_volume_money_hold120"] = summary["net_return_mean"] - summary["volume_money_hold120_net_return_mean"]
    summary["p10_delta_vs_volume_money_hold120"] = summary["net_return_p10"] - summary["volume_money_hold120_net_return_p10"]
    summary["loss_le_minus5_delta_vs_volume_money_hold120"] = summary["loss_le_minus5_rate"] - summary["volume_money_hold120_loss_le_minus5_rate"]
    summary["max_gain50_rate_delta_vs_volume_money_hold120"] = summary["max_gain50_rate"] - summary["volume_money_hold120_max_gain50_rate"]
    summary = summary.merge(baseline_context, on="split", how="left")
    summary["net_return_mean_delta_vs_baseline_A"] = summary["net_return_mean"] - summary["baseline_A_r04c_hold120_net_return_mean"]
    thresholds = config["thresholds"]
    min_replay = {
        "train": thresholds["minimum_train_replay_complete_count"],
        "validation": thresholds["minimum_validation_replay_complete_count"],
        "robustness": thresholds["minimum_robustness_replay_complete_count"],
    }
    summary["denominator_status"] = [
        "sufficient" if row.replay_complete_count >= min_replay.get(row.split, thresholds["minimum_validation_replay_complete_count"]) else "insufficient_replay_complete"
        for row in summary.itertuples(index=False)
    ]
    summary["winner_retention_status"] = np.where(
        summary["max_gain50_retention_vs_volume_money_hold120"] >= thresholds["min_max_gain50_retention_vs_volume_money_hold120"],
        "passed",
        "failed_winner_retention_gate",
    )
    return summary


def _summarize_matched(replay: pd.DataFrame) -> pd.DataFrame:
    matched = replay[replay["replay_universe"].eq("matched_baseline_A")].copy()
    rows: list[dict[str, Any]] = []
    for (policy_id, split), part in matched.groupby(["policy_id", "split"], dropna=False, sort=False):
        complete = part[_bool_series(part["replay_complete"])].copy()
        weight_sum = float(pd.to_numeric(complete["event_weight"], errors="coerce").sum()) if len(complete) else 0.0
        weight_sq_sum = float(np.square(pd.to_numeric(complete["event_weight"], errors="coerce")).sum()) if len(complete) else 0.0
        ess = weight_sum * weight_sum / weight_sq_sum if weight_sq_sum > 0 else 0.0
        rows.append(
            {
                "policy_id": policy_id,
                "split": split,
                "matched_baseline_replay_complete_count": int(len(complete)),
                "matched_comparator_effective_sample_size": ess,
                "matched_baseline_net_return_mean": _weighted_mean(complete, "weighted_net_return"),
                "matched_baseline_net_return_p10": _weighted_quantile(complete["weighted_net_return"], complete["event_weight"], 0.10) if len(complete) else np.nan,
                "matched_baseline_loss_le_minus5_rate": _weighted_mean(complete.assign(loss_numeric=complete["loss_le_minus5_flag"].astype(float)), "loss_numeric") if len(complete) else np.nan,
                "matched_comparator_status": "sufficient" if ess >= 300 else "insufficient",
            }
        )
    return pd.DataFrame(rows)


def _attach_matched_deltas(summary: pd.DataFrame, matched_summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = summary.merge(matched_summary, on=["policy_id", "split"], how="left")
    out["volume_money_replay_complete_count"] = out["replay_complete_count"]
    out["volume_money_net_return_mean"] = out["net_return_mean"]
    out["volume_money_net_return_p10"] = out["net_return_p10"]
    out["volume_money_loss_le_minus5_rate"] = out["loss_le_minus5_rate"]
    out["net_return_mean_delta_vs_matched_baseline_A"] = out["volume_money_net_return_mean"] - out["matched_baseline_net_return_mean"]
    out["p10_delta_vs_matched_baseline_A"] = out["volume_money_net_return_p10"] - out["matched_baseline_net_return_p10"]
    out["loss_le_minus5_delta_vs_matched_baseline_A"] = out["volume_money_loss_le_minus5_rate"] - out["matched_baseline_loss_le_minus5_rate"]
    matched_cols = [
        "policy_id",
        "split",
        "volume_money_replay_complete_count",
        "matched_baseline_replay_complete_count",
        "matched_comparator_effective_sample_size",
        "volume_money_net_return_mean",
        "matched_baseline_net_return_mean",
        "net_return_mean_delta_vs_matched_baseline_A",
        "volume_money_net_return_p10",
        "matched_baseline_net_return_p10",
        "p10_delta_vs_matched_baseline_A",
        "volume_money_loss_le_minus5_rate",
        "matched_baseline_loss_le_minus5_rate",
        "loss_le_minus5_delta_vs_matched_baseline_A",
        "matched_comparator_status",
    ]
    return out, out[matched_cols].copy()


def _zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    std = values.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return (values - values.mean()) / std


def _score(frame: pd.DataFrame) -> pd.Series:
    return (
        _zscore(frame["net_return_mean_delta_vs_volume_money_hold120"])
        + _zscore(frame["p10_delta_vs_volume_money_hold120"])
        - _zscore(frame["loss_le_minus5_delta_vs_volume_money_hold120"])
        - 0.5 * _zscore(frame["avg_holding_days"])
        - np.maximum(0.0, 0.50 - pd.to_numeric(frame["max_gain50_retention_vs_volume_money_hold120"], errors="coerce").fillna(0.0))
    )


def _failed_gate_list(row: pd.Series, gates: dict[str, bool]) -> str:
    return ";".join([name for name, passed in gates.items() if not bool(passed)])


def _selection(summary: pd.DataFrame, policy_matrix: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    thresholds = config["thresholds"]
    matrix_cols = ["policy_id", "is_train_selectable", "is_validation_selectable", "invalid_policy_reason", "canonical_policy_id"]
    selectable = summary.merge(policy_matrix[matrix_cols], on="policy_id", how="left")
    train = selectable[selectable["split"].eq("train") & _bool_series(selectable["is_train_selectable"])].copy()
    train["train_denominator_sufficient"] = train["replay_complete_count"].ge(thresholds["minimum_train_replay_complete_count"])
    train["train_selection_score"] = np.nan
    trace_rows: list[dict[str, Any]] = []
    selected_train_ids: set[str] = set()
    for family, part in train.groupby("policy_family_id", sort=False):
        eligible_ref = part[part["train_denominator_sufficient"]].copy()
        if eligible_ref.empty:
            ranked = part.copy()
            ranked["train_selection_score"] = np.nan
        else:
            scores = _score(eligible_ref)
            train.loc[eligible_ref.index, "train_selection_score"] = scores
            ranked = train.loc[part.index].sort_values(["train_selection_score", "net_return_mean_delta_vs_volume_money_hold120"], ascending=False)
            selected_train_ids.add(str(ranked.iloc[0]["policy_id"]))
        ranked = train.loc[part.index].sort_values(["train_selection_score", "net_return_mean_delta_vs_volume_money_hold120"], ascending=False)
        selected = str(ranked.iloc[0]["policy_id"]) if str(ranked.iloc[0]["policy_id"]) in selected_train_ids else ""
        for rank, row in enumerate(ranked.itertuples(index=False), start=1):
            trace_rows.append(
                {
                    "selection_stage": "train_parameter_selection",
                    "split_used": "train",
                    "policy_family_id": row.policy_family_id,
                    "candidate_policy_id": row.policy_id,
                    "parameter_set_id": row.parameter_set_id,
                    "parameter_values_json": row.parameter_values_json,
                    "selection_metric_name": "train_policy_score",
                    "selection_metric_value": row.train_selection_score,
                    "selection_rank": rank,
                    "z_reference_set_id": row.policy_family_id,
                    "z_reference_set_size": int(len(eligible_ref)),
                    "selected_flag": row.policy_id == selected,
                    "rejection_reason": "" if row.policy_id == selected else ("insufficient_train_denominator" if not row.train_denominator_sufficient else "lower_train_score"),
                }
            )
    val = selectable[
        selectable["split"].eq("validation")
        & selectable["policy_id"].isin(selected_train_ids)
        & _bool_series(selectable["is_validation_selectable"])
    ].copy()
    val["validation_selection_score"] = _score(val) if not val.empty else pd.Series(dtype=float)
    selected_policy_id = ""
    audit_rows: list[dict[str, Any]] = []
    for idx, row in val.iterrows():
        gates = {
            "replay_complete_count": row["replay_complete_count"] >= thresholds["minimum_validation_replay_complete_count"],
            "censored_share": row["censored_share"] <= thresholds["max_validation_censored_share"],
            "net_return_mean": row["net_return_mean"] > thresholds["validation_min_net_return_mean"],
            "net_return_mean_delta_vs_volume_money_hold120": row["net_return_mean_delta_vs_volume_money_hold120"] >= thresholds["validation_min_net_return_mean_delta_vs_volume_money_hold120"],
            "p10_delta_vs_volume_money_hold120": row["p10_delta_vs_volume_money_hold120"] >= 0,
            "loss_le_minus5_delta_vs_volume_money_hold120": row["loss_le_minus5_delta_vs_volume_money_hold120"] < 0,
            "max_gain50_count": row["max_gain50_count"] >= thresholds["minimum_validation_max_gain50_count"],
            "max_gain50_retention_vs_volume_money_hold120": row["max_gain50_retention_vs_volume_money_hold120"] >= thresholds["min_max_gain50_retention_vs_volume_money_hold120"],
        }
        val.loc[idx, "validation_gate_pass"] = all(gates.values())
        val.loc[idx, "failed_gate_list"] = _failed_gate_list(row, gates)
    passing = val[val["validation_gate_pass"].map(_to_bool)].copy()
    if not passing.empty:
        selected_policy_id = str(passing.sort_values(["validation_selection_score", "net_return_mean_delta_vs_volume_money_hold120"], ascending=False).iloc[0]["policy_id"])
    ranked_val = val.sort_values(["validation_selection_score", "net_return_mean_delta_vs_volume_money_hold120"], ascending=False)
    for rank, row in enumerate(ranked_val.itertuples(index=False), start=1):
        trace_rows.append(
            {
                "selection_stage": "validation_policy_selection",
                "split_used": "validation",
                "policy_family_id": row.policy_family_id,
                "candidate_policy_id": row.policy_id,
                "parameter_set_id": row.parameter_set_id,
                "parameter_values_json": row.parameter_values_json,
                "selection_metric_name": "validation_selection_score",
                "selection_metric_value": row.validation_selection_score,
                "selection_rank": rank,
                "z_reference_set_id": "validation_train_selected_policy_set",
                "z_reference_set_size": int(len(val)),
                "selected_flag": row.policy_id == selected_policy_id,
                "rejection_reason": "" if row.policy_id == selected_policy_id else ("failed_validation_gate" if not row.validation_gate_pass else "lower_validation_score"),
            }
        )
        audit_rows.append(
            {
                "policy_id": row.policy_id,
                "policy_family_id": row.policy_family_id,
                "split": row.split,
                "validation_gate_pass": bool(row.validation_gate_pass),
                "validation_selection_score": row.validation_selection_score,
                "validation_selected_rank": rank,
                "replay_complete_count": row.replay_complete_count,
                "censored_share": row.censored_share,
                "max_allowed_censored_share": thresholds["max_validation_censored_share"],
                "net_return_mean": row.net_return_mean,
                "net_return_metric_basis": row.net_return_metric_basis,
                "net_return_mean_delta_vs_volume_money_hold120": row.net_return_mean_delta_vs_volume_money_hold120,
                "p10_delta_vs_volume_money_hold120": row.p10_delta_vs_volume_money_hold120,
                "loss_le_minus5_delta_vs_volume_money_hold120": row.loss_le_minus5_delta_vs_volume_money_hold120,
                "max_gain50_count": row.max_gain50_count,
                "max_gain50_retention_vs_volume_money_hold120": row.max_gain50_retention_vs_volume_money_hold120,
                "net_return_mean_delta_vs_matched_baseline_A": row.net_return_mean_delta_vs_matched_baseline_A,
                "p10_delta_vs_matched_baseline_A": row.p10_delta_vs_matched_baseline_A,
                "loss_le_minus5_delta_vs_matched_baseline_A": row.loss_le_minus5_delta_vs_matched_baseline_A,
                "failed_gate_list": row.failed_gate_list,
                "selected_policy_id": selected_policy_id,
                "selected_flag": row.policy_id == selected_policy_id,
            }
        )
    selection_trace = pd.DataFrame(trace_rows)
    selection_panel = selectable.merge(
        selection_trace[["candidate_policy_id", "selection_stage", "selected_flag"]].rename(columns={"candidate_policy_id": "policy_id"}),
        on="policy_id",
        how="left",
    )
    return selection_trace, selection_panel, pd.DataFrame(audit_rows), selected_policy_id


def _robustness_and_final(summary: pd.DataFrame, selected_policy_id: str, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    thresholds = config["thresholds"]
    if not selected_policy_id:
        robustness_cols = list(summary.columns) + ["robustness_gate_pass", "failed_gate_list", "robustness_relative_improvement_status"]
        final = pd.DataFrame(
            [
                {
                    "final_decision": "r04d_no_policy_passed_validation",
                    "selected_policy_id": "",
                    "selected_policy_family_id": "",
                    "selected_hold_rule_id": "",
                    "selected_exit_rule_family_id": "",
                    "selected_sizing_rule_id": "",
                    "validation_gate_pass": False,
                    "robustness_gate_pass": False,
                    "robustness_relative_improvement_status": "",
                    "net_return_metric_basis": "weighted_net_return",
                    "decision_reason": "no validation-passed policy",
                }
            ]
        )
        return pd.DataFrame(columns=robustness_cols), final
    selected = summary[summary["policy_id"].eq(selected_policy_id)].copy()
    validation = selected[selected["split"].eq("validation")].iloc[0].to_dict() if not selected[selected["split"].eq("validation")].empty else {}
    robust = selected[selected["split"].eq("robustness")].copy()
    if robust.empty:
        final_decision = "r04d_policy_validation_only_not_robust"
        status = "missing_robustness"
        gate_pass = False
        robust_row = {}
    else:
        row = robust.iloc[0]
        gates = {
            "replay_complete_count": row["replay_complete_count"] >= thresholds["minimum_robustness_replay_complete_count"],
            "censored_share": row["censored_share"] <= thresholds["max_robustness_censored_share"],
            "net_return_mean": row["net_return_mean"] > thresholds["baseline_A_robustness_net_return_mean"],
            "net_return_mean_delta_vs_volume_money_hold120": row["net_return_mean_delta_vs_volume_money_hold120"] >= thresholds["robustness_min_net_return_mean_delta_vs_volume_money_hold120"],
            "p10_delta_vs_volume_money_hold120": row["p10_delta_vs_volume_money_hold120"] >= 0,
            "loss_le_minus5_delta_vs_volume_money_hold120": row["loss_le_minus5_delta_vs_volume_money_hold120"] <= 0,
            "max_gain50_count": row["max_gain50_count"] >= thresholds["minimum_robustness_max_gain50_count"],
            "max_gain50_retention_vs_volume_money_hold120": row["max_gain50_retention_vs_volume_money_hold120"] >= thresholds["min_max_gain50_retention_vs_volume_money_hold120"],
        }
        robust.loc[robust.index, "robustness_gate_pass"] = all(gates.values())
        robust.loc[robust.index, "failed_gate_list"] = _failed_gate_list(row, gates)
        gate_pass = bool(all(gates.values()))
        if gate_pass and row["net_return_mean_delta_vs_volume_money_hold120"] > 0:
            status = "strong_pass"
            final_decision = "r04d_policy_strong_pass_diagnostic_only"
        elif gate_pass:
            status = "insurance_pass_not_pool_improving"
            final_decision = "r04d_policy_passed_relative_improvement_diagnostic_only"
        else:
            status = "robustness_failed"
            final_decision = "r04d_policy_validation_only_not_robust"
        robust.loc[robust.index, "robustness_relative_improvement_status"] = status
        robust_row = robust.iloc[0].to_dict()
    final = pd.DataFrame(
        [
            {
                "final_decision": final_decision,
                "selected_policy_id": selected_policy_id,
                "selected_policy_family_id": validation.get("policy_family_id", robust_row.get("policy_family_id", "")),
                "selected_hold_rule_id": validation.get("hold_rule_id", robust_row.get("hold_rule_id", "")),
                "selected_exit_rule_family_id": validation.get("exit_rule_family_id", robust_row.get("exit_rule_family_id", "")),
                "selected_sizing_rule_id": validation.get("sizing_rule_id", robust_row.get("sizing_rule_id", "")),
                "validation_gate_pass": True,
                "robustness_gate_pass": gate_pass,
                "robustness_relative_improvement_status": status,
                "net_return_metric_basis": "weighted_net_return",
                "validation_net_return_mean": validation.get("net_return_mean", np.nan),
                "robustness_net_return_mean": robust_row.get("net_return_mean", np.nan),
                "validation_censored_share": validation.get("censored_share", np.nan),
                "robustness_censored_share": robust_row.get("censored_share", np.nan),
                "validation_net_return_mean_delta_vs_volume_money_hold120": validation.get("net_return_mean_delta_vs_volume_money_hold120", np.nan),
                "robustness_net_return_mean_delta_vs_volume_money_hold120": robust_row.get("net_return_mean_delta_vs_volume_money_hold120", np.nan),
                "validation_p10_delta_vs_volume_money_hold120": validation.get("p10_delta_vs_volume_money_hold120", np.nan),
                "robustness_p10_delta_vs_volume_money_hold120": robust_row.get("p10_delta_vs_volume_money_hold120", np.nan),
                "validation_loss_le_minus5_delta_vs_volume_money_hold120": validation.get("loss_le_minus5_delta_vs_volume_money_hold120", np.nan),
                "robustness_loss_le_minus5_delta_vs_volume_money_hold120": robust_row.get("loss_le_minus5_delta_vs_volume_money_hold120", np.nan),
                "validation_max_gain50_retention_vs_volume_money_hold120": validation.get("max_gain50_retention_vs_volume_money_hold120", np.nan),
                "robustness_max_gain50_retention_vs_volume_money_hold120": robust_row.get("max_gain50_retention_vs_volume_money_hold120", np.nan),
                "decision_reason": status,
            }
        ]
    )
    return robust, final


def _censored_audit(replay: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    totals = replay.groupby(["replay_universe", "policy_id", "split"], dropna=False).size().to_dict()
    for keys, part in replay.groupby(["replay_universe", "policy_id", "split", "replay_status"], dropna=False):
        universe, policy_id, split, status = keys
        total = totals.get((universe, policy_id, split), len(part))
        rows.append(
            {
                "replay_universe": universe,
                "policy_id": policy_id,
                "split": split,
                "replay_status": status,
                "event_count": int(len(part)),
                "status_share": _safe_div(len(part), total),
            }
        )
    return pd.DataFrame(rows)


def _gate0_spec(config: dict[str, Any]) -> pd.DataFrame:
    rows = [
        ("return", "weighted_simple_return", {"basis": "weighted_net_return"}, "gross=exit/entry-1;unweighted=gross-cost;weighted=position_weight*unweighted"),
        ("cost", "a_share_daily_replay_default_v1", config["cost_model"], "entry/exit bps frozen in config"),
        ("sizing", "fixed_and_volatility_scaled", config["policy_grid"]["sizing"], "volatility_scaled uses 20 complete pre-entry close returns"),
        ("execution", "close_signal_next_open", config["execution"], "exit_signal_date close; execution first executable next open"),
        ("censored", "status_set", {"statuses": ["replay_complete", "censored_by_split_boundary", "censored_by_missing_price", "censored_by_missing_required_indicator", "censored_by_no_exit_execution", "invalid_entry"]}, "headline uses replay_complete only"),
        ("matched_comparator", "same_policy_matched_baseline_A", config["upstream_r04c"]["matched_baseline_panel"], "same policy_id replay on matched baseline panel"),
        ("max_gain50_retention", "volume_money_hold120_denominator", {"threshold": config["thresholds"]["max_gain50_threshold"]}, "policy exit execution date must be after first +50 close hit"),
        ("baseline_delta", "volume_money_hold120_primary", config["baseline"], "primary deltas use volume_money hold120 no-exit fixed-size"),
        ("gate_threshold", "r04d_v1", config["thresholds"], "validation/robustness hard gates frozen"),
        ("selection_score", "train_policy_score", {}, "z(net_delta)+z(p10_delta)-z(loss_delta)-0.5*z(avg_holding_days)-retention_penalty"),
    ]
    out = pd.DataFrame(
        [
            {
                "spec_section": section,
                "spec_item": item,
                "frozen_value_json": json.dumps(value, ensure_ascii=False, sort_keys=True, default=str),
                "formula_text": formula,
                "source_config_key": section,
                "formula_hash": _hash_text(f"{section}|{item}|{json.dumps(value, sort_keys=True, default=str)}|{formula}"),
            }
            for section, item, value, formula in rows
        ]
    )
    return out


def _fmt_pct(value: Any) -> str:
    if pd.isna(value):
        return "NA"
    return f"{float(value):+.2%}"


def _final_report_text(
    profile: pd.DataFrame,
    summary: pd.DataFrame,
    validation: pd.DataFrame,
    robustness: pd.DataFrame,
    final: pd.DataFrame,
    recon: pd.DataFrame,
    config: dict[str, Any],
) -> str:
    pool_id = config["pool"]["pool_id"]
    vm_profile = profile[profile["pool_id"].eq(pool_id)].copy()
    final_row = final.iloc[0].to_dict()
    selected_raw = final_row.get("selected_policy_id", "")
    selected_id = "" if pd.isna(selected_raw) else str(selected_raw)
    selected = summary[summary["policy_id"].eq(selected_id)].copy() if selected_id else pd.DataFrame()
    lines: list[str] = [
        "# R04d volume_money 相对改善池 risk-budget replay 最终报告",
        "",
        "R04d does not reinterpret R04c v1 as passed.",
        "volume_money is a descriptive relative-improvement lead, not an R04c selected pool.",
        "R04d uses a fixed r02_precision_volume_money pool.",
        "R04d primary policies are shorter hold, time_stop, break_even, fixed_stop, and sizing only.",
        "Robustness is final readout only.",
        "Headline net_return metrics use weighted_net_return; unweighted returns are audit only.",
        "No production entry rule is emitted by this diagnostic.",
        "",
        "## 1. 最终结论",
        "",
        f"- final_decision: `{final_row.get('final_decision', '')}`",
        f"- selected_policy_id: `{selected_id}`",
        f"- decision_reason: `{final_row.get('decision_reason', '')}`",
        "",
        "## 2. 上游 volume_money hold120 no-exit 画像",
        "",
        "| split | replay_complete | censored | net_mean | p10 | loss<=-5 | max_gain50_rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in vm_profile.itertuples(index=False):
        lines.append(
            f"| {row.split} | {int(row.replay_complete_count):,} | {float(row.censored_share):.2%} | "
            f"{_fmt_pct(row.net_return_mean)} | {_fmt_pct(row.net_return_p10)} | {float(row.loss_le_minus5_rate):.2%} | {float(row.max_gain50_rate):.2%} |"
        )
    lines += [
        "",
        "## 3. Pool 重建一致性",
        "",
    ]
    r = recon.iloc[0]
    lines.append(
        f"R02 reconstruction count={int(r.r04d_reconstructed_event_count):,}, R04c volume_money count={int(r.r04c_volume_money_event_count):,}, "
        f"overlap={int(r.overlap_event_count):,}, status=`{r.reconciliation_status}`."
    )
    lines += [
        "",
        "## 4. Validation hard gate",
        "",
        "| policy_id | family | net_mean | delta_vs_hold120 | p10_delta | loss_delta | retention | censored | gate | failed_gate_list |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    if validation.empty:
        lines.append("| NA | NA | NA | NA | NA | NA | NA | NA | False | no train-selected policy |")
    else:
        for row in validation.sort_values("validation_selection_score", ascending=False).head(20).itertuples(index=False):
            lines.append(
                f"| `{row.policy_id}` | {row.policy_family_id} | {_fmt_pct(row.net_return_mean)} | "
                f"{_fmt_pct(row.net_return_mean_delta_vs_volume_money_hold120)} | {_fmt_pct(row.p10_delta_vs_volume_money_hold120)} | "
                f"{_fmt_pct(row.loss_le_minus5_delta_vs_volume_money_hold120)} | {float(row.max_gain50_retention_vs_volume_money_hold120):.2%} | "
                f"{float(row.censored_share):.2%} | {bool(row.validation_gate_pass)} | {row.failed_gate_list} |"
            )
    lines += [
        "",
        "## 5. Selected policy 读数",
        "",
    ]
    if selected.empty:
        lines.append("Validation 没有 policy 同时通过 hard gates，因此没有 robustness-selected readout。")
    else:
        lines.append("| split | net_mean | unweighted_mean | delta_vs_hold120 | p10_delta | loss_delta | matched_delta | retention | censored |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in selected.sort_values("split").itertuples(index=False):
            lines.append(
                f"| {row.split} | {_fmt_pct(row.net_return_mean)} | {_fmt_pct(row.unweighted_net_return_mean)} | "
                f"{_fmt_pct(row.net_return_mean_delta_vs_volume_money_hold120)} | {_fmt_pct(row.p10_delta_vs_volume_money_hold120)} | "
                f"{_fmt_pct(row.loss_le_minus5_delta_vs_volume_money_hold120)} | {_fmt_pct(row.net_return_mean_delta_vs_matched_baseline_A)} | "
                f"{float(row.max_gain50_retention_vs_volume_money_hold120):.2%} | {float(row.censored_share):.2%} |"
            )
    lines += [
        "",
        "## 6. 必需诊断清单",
        "",
        "### validation net > 0 的 policy",
        "",
    ]
    val_positive = validation[pd.to_numeric(validation.get("net_return_mean", pd.Series(dtype=float)), errors="coerce") > 0].copy() if not validation.empty else pd.DataFrame()
    lines.append(", ".join(f"`{x}`" for x in val_positive["policy_id"].head(20)) if not val_positive.empty else "None")
    lines += ["", "### validation 通过但 robustness 失败的 policy", ""]
    if selected_id and final_row.get("final_decision") == "r04d_policy_validation_only_not_robust":
        lines.append(f"`{selected_id}`")
    else:
        lines.append("None")
    lines += ["", "### robustness strong_pass 的 policy", ""]
    if selected_id and final_row.get("final_decision") == "r04d_policy_strong_pass_diagnostic_only":
        lines.append(f"`{selected_id}`")
    else:
        lines.append("None")
    lines += ["", "### winner retention < 50% 的 policy", ""]
    low_ret = summary[pd.to_numeric(summary["max_gain50_retention_vs_volume_money_hold120"], errors="coerce") < 0.50]
    lines.append(", ".join(f"`{x}`" for x in low_ret["policy_id"].drop_duplicates().head(20)) if not low_ret.empty else "None")
    lines += ["", "### censored_share > 25% 的 policy", ""]
    high_censored = summary[pd.to_numeric(summary["censored_share"], errors="coerce") > 0.25]
    lines.append(", ".join(f"`{x}`" for x in high_censored["policy_id"].drop_duplicates().head(20)) if not high_censored.empty else "None")
    lines += ["", "### weighted 通过但 unweighted 失败的 policy", ""]
    weighted_pass_unweighted_fail = validation[
        validation["validation_gate_pass"].map(_to_bool)
        & (pd.to_numeric(validation.get("net_return_mean", pd.Series(dtype=float)), errors="coerce") > 0)
    ].copy() if not validation.empty else pd.DataFrame()
    if not weighted_pass_unweighted_fail.empty:
        extra = summary[summary["policy_id"].isin(weighted_pass_unweighted_fail["policy_id"]) & summary["split"].eq("validation")]
        extra = extra[pd.to_numeric(extra["unweighted_net_return_mean"], errors="coerce") <= 0]
        lines.append(", ".join(f"`{x}`" for x in extra["policy_id"].head(20)) if not extra.empty else "None")
    else:
        lines.append("None")
    lines += ["", "### matched_baseline_A same-policy delta <= 0 的 policy", ""]
    matched_bad = validation[pd.to_numeric(validation.get("net_return_mean_delta_vs_matched_baseline_A", pd.Series(dtype=float)), errors="coerce") <= 0].copy() if not validation.empty else pd.DataFrame()
    lines.append(", ".join(f"`{x}`" for x in matched_bad["policy_id"].head(20)) if not matched_bad.empty else "None")
    lines += [
        "",
        "## 7. 发现与后续判断",
        "",
        "本实验只判断 volume_money 这个 relative-improvement lead 是否能被简单 risk-budget/shorter-hold 规则转成 OOS 正期望。若 validation 通过但 robustness 不通过，结论必须停留在 diagnostic lead；若 strong pass，也只能进入 portfolio-level confirmation，不能解释为 production entry rule。",
        "",
    ]
    return "\n".join(lines)


def _upstream_state_audit(config: dict[str, Any]) -> pd.DataFrame:
    r04c_val = _read_json(Path(config["upstream_r04c"]["validation"]))
    r04b_val = _read_json(Path(config["upstream_r04b"]["validation"]))
    r04c_final = pd.read_csv(topic_path(config["upstream_r04c"]["final_decision"]))
    return pd.DataFrame(
        [
            {
                "upstream_id": "r04c",
                "validation_status": r04c_val.get("validation_status"),
                "final_decision": r04c_val.get("final_decision"),
                "required_status_pass": r04c_val.get("validation_status") == "passed",
                "required_final_decision_pass": r04c_val.get("final_decision") == "r04c_no_candidate_pool_passed_validation",
                "final_decision_csv": r04c_final.iloc[0]["final_decision"] if not r04c_final.empty else "",
            },
            {
                "upstream_id": "r04b",
                "validation_status": r04b_val.get("validation_status"),
                "final_decision": r04b_val.get("final_decision"),
                "required_status_pass": r04b_val.get("validation_status") == "passed",
                "required_final_decision_pass": True,
                "final_decision_csv": "",
            },
        ]
    )


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for directory in [cache_dir, reports_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    upstream_audit = _upstream_state_audit(config)
    write_csv(upstream_audit, reports_dir / "r04d_upstream_state_audit.csv")
    if not bool(upstream_audit["required_status_pass"].all()):
        decision = "blocked_upstream_validation_failed"
        manifest = {"final_decision": decision, "validation_status": "not_run", "reason": "upstream validation failed"}
        write_json(manifest, manifests_dir / "r04d_volume_money_relative_improvement_risk_budget_manifest.json")
        return manifest
    if not bool(upstream_audit.loc[upstream_audit["upstream_id"].eq("r04c"), "required_final_decision_pass"].all()):
        decision = "blocked_upstream_r04c_state_changed"
        manifest = {"final_decision": decision, "validation_status": "not_run", "reason": "R04c final decision changed"}
        write_json(manifest, manifests_dir / "r04d_volume_money_relative_improvement_risk_budget_manifest.json")
        return manifest

    calendar = _load_calendar(config["price_provider"]["calendar_source_path"])
    r04c_events, matched_panel, profile = _load_event_inputs(config)
    base_pre = _prepare_base_events(config, r04c_events, matched_panel)
    instruments = sorted(base_pre["instrument_id"].dropna().astype(str).str.upper().unique())
    min_entry_idx = int(pd.to_numeric(base_pre["entry_calendar_index"], errors="coerce").min())
    max_entry_idx = int(pd.to_numeric(base_pre["entry_calendar_index"], errors="coerce").max())
    start_idx = max(0, min_entry_idx - int(config["execution"]["pre_entry_lookback_trading_days"]) - 5)
    end_idx = min(len(calendar) - 1, max_entry_idx + int(config["execution"]["max_holding_days"]) + int(config["execution"]["max_exit_execution_lag_trading_days"]) + 5)
    print(f"loading price panel for {len(instruments)} instruments", flush=True)
    price = _load_price_panel(config, instruments, pd.Timestamp(calendar[start_idx]), pd.Timestamp(calendar[end_idx]), calendar)

    r02_reconstructed = _collapse_volume_money_from_r02(config, calendar)
    recon = _reconstruction_audit(config, r02_reconstructed, r04c_events, price)
    write_csv(recon, reports_dir / "r04d_volume_money_pool_reconstruction_audit.csv")
    if not recon["reconciliation_status"].eq("passed").all():
        decision = "blocked_pool_reconstruction_failed"
        manifest = {"final_decision": decision, "validation_status": "not_run", "reason": "pool reconstruction failed"}
        write_json(manifest, manifests_dir / "r04d_volume_money_relative_improvement_risk_budget_manifest.json")
        return manifest

    base = _attach_entry_reconciliation(base_pre, price, config)
    daily_path = _build_daily_path(base, price, config)
    base = _attach_hold120_labels(base, daily_path, float(config["thresholds"]["max_gain50_threshold"]))
    daily_path = daily_path.merge(
        base[["r04d_event_id", "volume_money_hold120_max_gain50_flag", "volume_money_hold120_first_plus50_hit_date"]],
        on="r04d_event_id",
        how="left",
    )
    policy_matrix = _build_policy_matrix(config)
    gate0 = _gate0_spec(config)
    print(f"replaying {len(base):,} events x {policy_matrix['invalid_policy_reason'].fillna('').eq('').sum():,} policies", flush=True)
    replay = _replay_policies(base, daily_path, policy_matrix, config)
    baseline_context = _baseline_profile_context(config, profile)
    summary = _summarize_volume(replay, config, baseline_context)
    matched_summary = _summarize_matched(replay)
    summary, matched_policy_summary = _attach_matched_deltas(summary, matched_summary)
    selection_trace, selection_panel, validation_gate, selected_policy_id = _selection(summary, policy_matrix, config)
    robustness, final = _robustness_and_final(summary, selected_policy_id, config)
    final_decision = str(final.iloc[0]["final_decision"]) if not final.empty else "blocked_selection_leakage_detected"

    write_csv(gate0, reports_dir / "r04d_gate0_metric_replay_spec_frozen.csv")
    write_csv(policy_matrix, reports_dir / "r04d_policy_matrix_frozen.csv")
    write_csv(policy_matrix[["policy_id", "duplicate_policy_group_id", "canonical_policy_id", "invalid_policy_reason", "is_train_selectable", "is_validation_selectable"]], reports_dir / "r04d_policy_duplicate_audit.csv")
    write_csv(summary, reports_dir / "r04d_policy_replay_summary.csv")
    write_csv(matched_policy_summary, reports_dir / "r04d_matched_baseline_policy_replay_summary.csv")
    write_csv(summary, reports_dir / "r04d_policy_vs_volume_money_hold120_summary.csv")
    write_csv(selection_trace, reports_dir / "r04d_train_policy_selection_trace.csv")
    write_csv(validation_gate, reports_dir / "r04d_validation_gate_audit.csv")
    write_csv(robustness, reports_dir / "r04d_robustness_readout.csv")
    write_csv(
        summary[[
            "policy_id",
            "split",
            "max_gain50_count",
            "policy_retained_max_gain50_count",
            "max_gain50_retention_vs_volume_money_hold120",
            "winner_retention_status",
        ]],
        reports_dir / "r04d_winner_retention_audit.csv",
    )
    write_csv(_censored_audit(replay), reports_dir / "r04d_censored_replay_audit.csv")
    write_csv(summary[["policy_id", "split", "position_weight_mean", "avg_holding_days", "turnover_proxy", "cost_bps_mean"]], reports_dir / "r04d_cost_turnover_audit.csv")
    write_csv(final, reports_dir / "r04d_final_decision.csv")
    report = _final_report_text(profile, summary, validation_gate, robustness, final, recon, config)
    (reports_dir / "r04d_volume_money_relative_improvement_risk_budget_final_report.md").write_text(report, encoding="utf-8")

    _write_parquet(base, cache_dir / "r04d_volume_money_pool_event_panel.parquet")
    _write_parquet(daily_path, cache_dir / "r04d_daily_policy_path_panel.parquet")
    _write_parquet(replay, cache_dir / "r04d_policy_replay_panel.parquet")
    _write_parquet(selection_panel, cache_dir / "r04d_policy_selection_panel.parquet")

    artifacts = (
        list(cache_dir.glob("*.parquet"))
        + list(reports_dir.glob("*.csv"))
        + [reports_dir / "r04d_volume_money_relative_improvement_risk_budget_final_report.md"]
    )
    manifest = {
        "phase": config["phase"],
        "requirement_id": config["requirement_id"],
        "final_decision": final_decision,
        "selected_policy_id": selected_policy_id,
        "output_root": relpath(output_root),
        "artifact_hashes": _artifact_hashes(artifacts),
        "upstream_r04c_validation": relpath(topic_path(config["upstream_r04c"]["validation"])),
        "upstream_r04b_validation": relpath(topic_path(config["upstream_r04b"]["validation"])),
        "price_source_path": config["price_provider"]["price_source_path"],
        "price_source_hash": _price_source_hash(config, instruments),
        "calendar_source_path": config["price_provider"]["calendar_source_path"],
        "calendar_source_hash": _hash_file(topic_path(config["price_provider"]["calendar_source_path"])),
        "adjustment_policy": config["price_provider"]["adjustment_policy"],
        "cost_model": config["cost_model"],
        "net_return_metric_basis": "weighted_net_return",
        "policy_count": int(len(policy_matrix)),
        "selectable_policy_count": int(policy_matrix["is_train_selectable"].map(_to_bool).sum()),
    }
    write_json(manifest, manifests_dir / "r04d_volume_money_relative_improvement_risk_budget_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    manifest = run(args.config)
    print(json.dumps({"final_decision": manifest.get("final_decision"), "selected_policy_id": manifest.get("selected_policy_id")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

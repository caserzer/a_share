#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
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
)


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04e_union_pool_portfolio_level_diagnostic_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
SOURCE_FAMILY_TO_POOL = {
    "volume_money": "r02_precision_volume_money",
    "range_breakout": "r02_precision_range_breakout",
    "pullback_drawdown": "r02_precision_pullback_drawdown",
}
ALLOWED_FINAL_DECISIONS = {
    "r04e_union_portfolio_strong_lead",
    "r04e_union_portfolio_conditional_lead",
    "r04e_union_validation_positive_but_robustness_mixed",
    "r04e_union_validation_positive_but_robustness_failed",
    "r04e_union_not_viable_validation",
    "r04e_long_only_validation_ceiling_suspected",
    "r04e_blocked_upstream_validation_failed",
    "r04e_blocked_upstream_state_changed",
    "r04e_blocked_missing_required_input",
    "r04e_blocked_validation_failed",
}
FORBIDDEN_POLICY_TOKENS = ("ATR", "EMA", "CTA", "profit_lock", "market_state_gate", "industry_state_gate")


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: str | Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


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
    return _hash_text(f"{pool_id}|{str(instrument).upper()}|{_date_str(anchor)}|{source_id}")


def _stable_key(*parts: Any) -> str:
    return _hash_text("|".join("" if pd.isna(part) else str(part) for part in parts))


def _load_required_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], str]:
    required = [
        config["upstream_r04c"]["validation"],
        config["upstream_r04c"]["manifest"],
        config["upstream_r04c"]["final_decision"],
        config["upstream_r04c"]["hold120_pool_profile"],
        config["upstream_r04c"]["matched_baseline_delta_summary"],
        config["upstream_r04c"]["overlap_uniqueness_audit"],
        config["upstream_r04c"]["concentration_audit"],
        config["upstream_r04c"]["pool_registry_frozen"],
        config["upstream_r04c"]["pool_event_panel"],
        config["upstream_r04c"]["matched_baseline_panel"],
        config["upstream_r04d"]["validation"],
        config["upstream_r04d"]["manifest"],
        config["upstream_r04d"]["final_decision"],
        config["upstream_r04b"]["validation"],
        config["upstream_r04b"]["manifest"],
        config["upstream_r02_family_precision"]["action_time_panel"],
        config["price_provider"]["calendar_source_path"],
        config["price_provider"]["instrument_source_path"],
    ]
    missing = [path for path in required if not topic_path(path).exists()]
    if missing:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}, "missing:" + ";".join(missing)

    r04c_val = _read_json(config["upstream_r04c"]["validation"])
    r04d_val = _read_json(config["upstream_r04d"]["validation"])
    r04b_val = _read_json(config["upstream_r04b"]["validation"])
    r04c_final = pd.read_csv(topic_path(config["upstream_r04c"]["final_decision"]))
    r04d_final = pd.read_csv(topic_path(config["upstream_r04d"]["final_decision"]))
    state = {
        "r04c_validation_status": r04c_val.get("validation_status", ""),
        "r04c_validation_final_decision": r04c_val.get("final_decision", ""),
        "r04c_csv_final_decision": "" if r04c_final.empty else str(r04c_final.iloc[0].get("final_decision", "")),
        "r04d_validation_status": r04d_val.get("validation_status", ""),
        "r04d_validation_final_decision": r04d_val.get("final_decision", ""),
        "r04d_csv_final_decision": "" if r04d_final.empty else str(r04d_final.iloc[0].get("final_decision", "")),
        "r04b_validation_status": r04b_val.get("validation_status", ""),
        "r04b_validation_final_decision": r04b_val.get("final_decision", ""),
    }
    if state["r04c_validation_status"] != "passed" or state["r04d_validation_status"] != "passed" or state["r04b_validation_status"] != "passed":
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), state, "upstream_validation_failed"
    if state["r04c_csv_final_decision"] != "r04c_no_candidate_pool_passed_validation":
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), state, "upstream_state_changed"
    if state["r04d_csv_final_decision"] != "r04d_no_policy_passed_validation":
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), state, "upstream_state_changed"

    r04c_events = pd.read_parquet(topic_path(config["upstream_r04c"]["pool_event_panel"]))
    r04c_matched = pd.read_parquet(topic_path(config["upstream_r04c"]["matched_baseline_panel"]))
    r04c_profile = pd.read_csv(topic_path(config["upstream_r04c"]["hold120_pool_profile"]))
    r04c_registry = pd.read_csv(topic_path(config["upstream_r04c"]["pool_registry_frozen"]))
    return r04c_events, r04c_matched, r04c_profile, r04c_registry, state, ""


def _upstream_state_audit(state: dict[str, Any], block_reason: str) -> pd.DataFrame:
    rows = [
        {
            "upstream_id": "r04c",
            "validation_status": state.get("r04c_validation_status", ""),
            "validation_final_decision": state.get("r04c_validation_final_decision", ""),
            "final_decision_csv": state.get("r04c_csv_final_decision", ""),
            "required_status_pass": state.get("r04c_validation_status", "") == "passed",
            "required_final_decision_pass": state.get("r04c_csv_final_decision", "") == "r04c_no_candidate_pool_passed_validation",
            "block_reason": block_reason,
        },
        {
            "upstream_id": "r04d",
            "validation_status": state.get("r04d_validation_status", ""),
            "validation_final_decision": state.get("r04d_validation_final_decision", ""),
            "final_decision_csv": state.get("r04d_csv_final_decision", ""),
            "required_status_pass": state.get("r04d_validation_status", "") == "passed",
            "required_final_decision_pass": state.get("r04d_csv_final_decision", "") == "r04d_no_policy_passed_validation",
            "block_reason": block_reason,
        },
        {
            "upstream_id": "r04b",
            "validation_status": state.get("r04b_validation_status", ""),
            "validation_final_decision": state.get("r04b_validation_final_decision", ""),
            "final_decision_csv": "",
            "required_status_pass": state.get("r04b_validation_status", "") == "passed",
            "required_final_decision_pass": True,
            "block_reason": block_reason,
        },
    ]
    return pd.DataFrame(rows)


def _collapse_source_pools(config: dict[str, Any], calendar: pd.DatetimeIndex) -> pd.DataFrame:
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
    families = set(config["union_pool"]["source_family_ids"])
    raw["instrument_id"] = raw["instrument_id"].astype(str).str.upper()
    raw["trade_date"] = pd.to_datetime(raw["trade_date"]).dt.normalize()
    eligible = raw[
        raw["family_id"].astype(str).isin(families)
        & raw["signal_occurs"].map(_to_bool)
        & raw["feature_complete_flag"].map(_to_bool)
        & raw["base_action_time_eligible_flag"].map(_to_bool)
    ].copy()
    cal_map = {pd.Timestamp(date): idx for idx, date in enumerate(calendar)}
    gap = int(config["union_pool"]["episode_gap_trading_days"])
    rows: list[dict[str, Any]] = []
    for (family, instrument), part in eligible.sort_values(["family_id", "instrument_id", "trade_date"]).groupby(["family_id", "instrument_id"], sort=False):
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
                source_id = str(getattr(row, "signal_episode_id", "")) or f"{instrument}|{family}|{dt.date()}"
                pool_id = SOURCE_FAMILY_TO_POOL[str(family)]
                current = {
                    "source_pool_event_id": _event_id(pool_id, instrument, dt, source_id),
                    "source_event_id": source_id,
                    "pool_id": pool_id,
                    "source_pool_id": pool_id,
                    "source_family_id": str(family),
                    "pool_family_id": f"r02_precision_{family}",
                    "pool_source_id": "r02_family_precision",
                    "adapter_id": "r02_family_precision_frozen_family_occurrence",
                    "pool_promotability_status": "frozen_descriptive_lead",
                    "instrument_id": str(instrument).upper(),
                    "anchor_signal_date": dt,
                    "source_split": row.split,
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
    out["source_family_set"] = out["source_family_id"]
    out["source_family_count"] = 1
    return out.sort_values(["source_family_id", "instrument_id", "anchor_signal_date"]).reset_index(drop=True)


def _price_bounds(config: dict[str, Any], calendar: pd.DatetimeIndex) -> tuple[pd.Timestamp, pd.Timestamp]:
    bounds = _split_bounds(config)
    start = bounds["train"][0]
    end = bounds["robustness"][1]
    end_idx = min(len(calendar) - 1, int(calendar.searchsorted(end, side="right")) + int(config["execution"]["max_holding_days"]) + int(config["execution"]["max_exit_execution_lag_trading_days"]) + 5)
    return start, pd.Timestamp(calendar[end_idx])


def _first_executable_after(price_by_inst: dict[str, pd.DataFrame], instrument: str, anchor: pd.Timestamp, calendar: pd.DatetimeIndex, max_lag: int) -> tuple[pd.Timestamp | pd.NaT, float, int | float, str]:
    inst = price_by_inst.get(str(instrument).upper())
    if inst is None or inst.empty:
        return pd.NaT, np.nan, np.nan, "invalid_entry"
    start = int(calendar.searchsorted(pd.Timestamp(anchor).normalize(), side="right"))
    indexed = inst.set_index("calendar_index", drop=False)
    for idx in range(start, start + max_lag + 1):
        if idx not in indexed.index:
            continue
        row = indexed.loc[idx]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        if bool(row["executable_open_flag"]) and np.isfinite(float(row["adjusted_open"])) and float(row["adjusted_open"]) > 0:
            return pd.Timestamp(row["trade_date"]).normalize(), float(row["adjusted_open"]), int(idx), "passed"
    return pd.NaT, np.nan, np.nan, "invalid_entry"


def _prepare_source_events(source: pd.DataFrame, r04c_events: pd.DataFrame, price: pd.DataFrame, calendar: pd.DatetimeIndex, config: dict[str, Any]) -> pd.DataFrame:
    if source.empty:
        return source
    price = price.copy()
    if "executable_open_flag" not in price.columns:
        price["executable_open_flag"] = (
            (price["adjusted_open"] > 0)
            & (price["volume"] > 0)
            & (price["money"] > 0)
            & (~_bool_series(price["suspended_or_dirty_bar"], default=True))
        )
    price_by_inst = {inst: part.sort_values("calendar_index").reset_index(drop=True) for inst, part in price.groupby("instrument_id", sort=False)}
    max_lag = int(config["execution"]["max_entry_execution_lag_trading_days"])
    entries = []
    for row in source.itertuples(index=False):
        entry_date, entry_price, entry_idx, status = _first_executable_after(price_by_inst, row.instrument_id, pd.Timestamp(row.anchor_signal_date), calendar, max_lag)
        entries.append((entry_date, entry_price, entry_idx, status))
    out = source.copy()
    out[["entry_execution_date", "entry_price", "entry_calendar_index", "entry_resolution_status"]] = pd.DataFrame(entries, index=out.index)
    out["entry_execution_date"] = pd.to_datetime(out["entry_execution_date"], errors="coerce").dt.normalize()
    out["entry_calendar_index"] = pd.to_numeric(out["entry_calendar_index"], errors="coerce")
    bounds = _split_bounds(config)
    out["split"] = out["entry_execution_date"].map(lambda value: _split_for_date(value, bounds))
    out["entry_calendar_year"] = out["entry_execution_date"].dt.year
    out["entry_calendar_quarter"] = out["entry_execution_date"].dt.to_period("Q").astype(str)
    meta_cols = [
        "pool_event_id",
        "pool_id",
        "entry_execution_date",
        "entry_price",
        "market_regime_bucket",
        "industry_regime_bucket",
        "industry_target_key",
        "stock_rps_60d",
        "stock_rps_minus_industry_rps_60d",
        "money_rank_20d",
        "industry_rps_60d",
    ]
    r04c_meta = r04c_events[r04c_events["pool_id"].isin(config["union_pool"]["source_pool_ids"])][meta_cols].copy()
    r04c_meta = r04c_meta.rename(
        columns={
            "pool_event_id": "source_pool_event_id",
            "entry_execution_date": "r04c_entry_execution_date",
            "entry_price": "r04c_entry_price",
        }
    )
    out = out.merge(r04c_meta, on=["source_pool_event_id", "pool_id"], how="left")
    out["r04c_entry_execution_date"] = pd.to_datetime(out["r04c_entry_execution_date"], errors="coerce").dt.normalize()
    out["entry_price_rel_diff_vs_r04c"] = (pd.to_numeric(out["entry_price"], errors="coerce") / pd.to_numeric(out["r04c_entry_price"], errors="coerce") - 1.0).abs()
    for col, default in [
        ("market_regime_bucket", "missing_market_regime"),
        ("industry_regime_bucket", "missing_industry"),
        ("industry_target_key", "missing_industry"),
    ]:
        out[col] = out[col].fillna(default)
    for col in ["stock_rps_60d", "stock_rps_minus_industry_rps_60d", "money_rank_20d", "industry_rps_60d"]:
        if col not in out.columns:
            out[col] = np.nan
    out["source_membership_authority"] = "r02_family_action_time_panel"
    out["episode_collapse_rule"] = f"episode_gap_trading_days={config['union_pool']['episode_gap_trading_days']}"
    return out.reset_index(drop=True)


def _source_reconciliation(source: pd.DataFrame, r04c_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    tol = float(config["union_pool"]["max_entry_price_rel_diff"])
    for pool_id in config["union_pool"]["source_pool_ids"]:
        src = source[source["pool_id"].eq(pool_id)].copy()
        r04c = r04c_events[r04c_events["pool_id"].eq(pool_id)].copy()
        overlap = src.merge(
            r04c[["pool_event_id", "entry_execution_date", "entry_price"]].rename(
                columns={"pool_event_id": "source_pool_event_id", "entry_execution_date": "r04c_entry_execution_date_check", "entry_price": "r04c_entry_price_check"}
            ),
            on="source_pool_event_id",
            how="inner",
        )
        entry_date_mismatch = 0
        p95 = np.nan
        max_diff = np.nan
        if not overlap.empty:
            entry_date_mismatch = int((pd.to_datetime(overlap["entry_execution_date"]).dt.normalize() != pd.to_datetime(overlap["r04c_entry_execution_date_check"]).dt.normalize()).sum())
            diff = (pd.to_numeric(overlap["entry_price"], errors="coerce") / pd.to_numeric(overlap["r04c_entry_price_check"], errors="coerce") - 1.0).abs()
            p95 = _quantile(diff, 0.95)
            max_diff = float(diff.max()) if len(diff.dropna()) else np.nan
        status = (
            "passed"
            if _safe_div(len(overlap), len(src)) >= 0.99
            and _safe_div(len(overlap), len(r04c)) >= 0.99
            and entry_date_mismatch == 0
            and (pd.isna(p95) or p95 <= tol)
            else "failed"
        )
        rows.append(
            {
                "pool_id": pool_id,
                "source_family_id": next((family for family, pid in SOURCE_FAMILY_TO_POOL.items() if pid == pool_id), ""),
                "r04e_reconstructed_event_count": int(len(src)),
                "r04c_event_count": int(len(r04c)),
                "overlap_event_count": int(len(overlap)),
                "overlap_share_vs_r04e": _safe_div(len(overlap), len(src)),
                "overlap_share_vs_r04c": _safe_div(len(overlap), len(r04c)),
                "entry_date_mismatch_count": entry_date_mismatch,
                "entry_price_rel_diff_p95": p95,
                "entry_price_rel_diff_max": max_diff,
                "entry_price_rel_diff_tolerance": tol,
                "reconciliation_status": status,
            }
        )
    return pd.DataFrame(rows)


def _build_union_events(source: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    valid = source[
        source["entry_resolution_status"].eq("passed")
        & source["split"].isin(SPLITS)
        & source["entry_execution_date"].notna()
    ].copy()
    rows: list[dict[str, Any]] = []
    union_pool_id = config["union_pool"]["union_pool_id"]
    for (instrument, entry_date), part in valid.sort_values(["instrument_id", "entry_execution_date", "source_family_id"]).groupby(["instrument_id", "entry_execution_date"], sort=False):
        families = sorted(part["source_family_id"].dropna().astype(str).unique())
        pool_ids = sorted(part["pool_id"].dropna().astype(str).unique())
        anchor = pd.to_datetime(part["anchor_signal_date"]).min()
        union_key = f"{instrument}|{_date_str(entry_date)}"
        entry_price = float(pd.to_numeric(part["entry_price"], errors="coerce").dropna().iloc[0]) if len(part["entry_price"].dropna()) else np.nan
        first = part.iloc[0]
        rows.append(
            {
                "r04e_event_id": "union|" + _stable_key(union_key),
                "union_event_key": union_key,
                "pool_id": union_pool_id,
                "replay_universe": "union_pool",
                "instrument_id": str(instrument).upper(),
                "anchor_signal_date": anchor,
                "entry_execution_date": pd.Timestamp(entry_date).normalize(),
                "entry_price": entry_price,
                "entry_calendar_index": first["entry_calendar_index"],
                "entry_calendar_year": int(pd.Timestamp(entry_date).year),
                "entry_calendar_quarter": pd.Timestamp(entry_date).to_period("Q").strftime("%YQ%q"),
                "split": first["split"],
                "source_pool_id_set": ";".join(pool_ids),
                "source_family_set": ";".join(families),
                "source_family_count": int(len(families)),
                "source_hit_count": int(len(part)),
                "source_pool_event_id_set": ";".join(sorted(part["source_pool_event_id"].astype(str).unique())),
                "market_regime_bucket": first.get("market_regime_bucket", "missing_market_regime"),
                "industry_regime_bucket": first.get("industry_regime_bucket", "missing_industry"),
                "industry_target_key": first.get("industry_target_key", "missing_industry"),
                "event_weight": 1.0,
                "cap_rank_key": _stable_key(str(instrument).upper(), _date_str(entry_date), union_key),
                "membership_filter_text": "fixed_source_families_only_no_market_industry_rps_gate",
            }
        )
    return pd.DataFrame(rows).sort_values(["split", "entry_execution_date", "instrument_id"]).reset_index(drop=True)


def _baseline_events(r04c_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    baseline_pool = config["union_pool"]["baseline_pool_id"]
    base = r04c_events[r04c_events["pool_id"].eq(baseline_pool)].copy()
    base = base[base["split"].isin(SPLITS) & base["entry_execution_date"].notna()].copy()
    base["r04e_event_id"] = "baseline_A|" + base["pool_event_id"].astype(str)
    base["replay_universe"] = "baseline_A"
    base["source_family_set"] = "baseline_A"
    base["source_family_count"] = 1
    base["source_pool_id_set"] = baseline_pool
    base["source_pool_event_id_set"] = base["pool_event_id"].astype(str)
    base["event_weight"] = 1.0
    base["cap_rank_key"] = [
        _stable_key(row.instrument_id, _date_str(row.entry_execution_date), row.pool_event_id)
        for row in base.itertuples(index=False)
    ]
    keep = [
        "r04e_event_id",
        "pool_event_id",
        "source_event_id",
        "pool_id",
        "replay_universe",
        "instrument_id",
        "anchor_signal_date",
        "entry_execution_date",
        "entry_price",
        "entry_calendar_index",
        "entry_calendar_year",
        "entry_calendar_quarter",
        "split",
        "source_pool_id_set",
        "source_family_set",
        "source_family_count",
        "source_pool_event_id_set",
        "market_regime_bucket",
        "industry_regime_bucket",
        "industry_target_key",
        "event_weight",
        "cap_rank_key",
    ]
    for col in keep:
        if col not in base.columns:
            base[col] = np.nan
    base["instrument_id"] = base["instrument_id"].astype(str).str.upper()
    base["entry_execution_date"] = pd.to_datetime(base["entry_execution_date"]).dt.normalize()
    base["anchor_signal_date"] = pd.to_datetime(base["anchor_signal_date"]).dt.normalize()
    return base[keep].reset_index(drop=True)


def _same_instrument_nearby_audit(union: pd.DataFrame, source: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    window = int(config["union_pool"]["nearby_window_trading_days"])
    source_valid = source[source["entry_resolution_status"].eq("passed") & source["split"].isin(SPLITS)].copy()
    source_by_inst = {inst: part["entry_calendar_index"].to_numpy(float) for inst, part in source_valid.groupby("instrument_id", sort=False)}
    union_by_inst = {inst: part.sort_values("entry_calendar_index").copy() for inst, part in union.groupby("instrument_id", sort=False)}
    rows: list[dict[str, Any]] = []
    for row in union.itertuples(index=False):
        idx = float(row.entry_calendar_index)
        source_indices = source_by_inst.get(row.instrument_id, np.array([], dtype=float))
        source_count = int(np.isfinite(source_indices).sum() and ((np.abs(source_indices - idx) <= window)).sum())
        part = union_by_inst.get(row.instrument_id, pd.DataFrame())
        if part.empty:
            union_count = 0
            prior = pd.NaT
            nxt = pd.NaT
        else:
            near = part[np.abs(pd.to_numeric(part["entry_calendar_index"], errors="coerce") - idx) <= window]
            union_count = int(len(near))
            prior_part = part[pd.to_numeric(part["entry_calendar_index"], errors="coerce") < idx].tail(1)
            next_part = part[pd.to_numeric(part["entry_calendar_index"], errors="coerce") > idx].head(1)
            prior = prior_part.iloc[0]["entry_execution_date"] if not prior_part.empty else pd.NaT
            nxt = next_part.iloc[0]["entry_execution_date"] if not next_part.empty else pd.NaT
        rows.append(
            {
                "split": row.split,
                "instrument_id": row.instrument_id,
                "union_event_key": row.union_event_key,
                "entry_execution_date": _date_str(row.entry_execution_date),
                "source_family_set": row.source_family_set,
                "nearby_window_trading_days": window,
                "same_instrument_nearby_source_event_count": source_count,
                "same_instrument_nearby_union_event_count": union_count,
                "nearest_prior_union_entry_execution_date": _date_str(prior),
                "nearest_next_union_entry_execution_date": _date_str(nxt),
                "nearby_event_status": "clustered_20d" if union_count > 1 else "isolated",
            }
        )
    return pd.DataFrame(rows)


def _event_overlap_audit(source: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    valid = source[source["entry_resolution_status"].eq("passed") & source["split"].isin(SPLITS)].copy()
    valid["event_key"] = valid["instrument_id"].astype(str) + "|" + valid["entry_execution_date"].map(_date_str)
    rows: list[dict[str, Any]] = []
    pools = list(config["union_pool"]["source_pool_ids"])
    for split in SPLITS:
        split_part = valid[valid["split"].eq(split)]
        for i, pool_a in enumerate(pools):
            for pool_b in pools[i + 1 :]:
                a = split_part[split_part["pool_id"].eq(pool_a)]
                b = split_part[split_part["pool_id"].eq(pool_b)]
                keys_a = set(a["event_key"])
                keys_b = set(b["event_key"])
                inst_a = set(a["instrument_id"])
                inst_b = set(b["instrument_id"])
                date_a = set(a["entry_execution_date"].map(_date_str))
                date_b = set(b["entry_execution_date"].map(_date_str))
                inter = len(keys_a & keys_b)
                uni = len(keys_a | keys_b)
                jaccard = _safe_div(inter, uni)
                status = "high_overlap" if jaccard > 0.45 else ("moderate_overlap" if jaccard > 0.25 else "low_overlap")
                rows.append(
                    {
                        "source_pool_id_a": pool_a,
                        "source_pool_id_b": pool_b,
                        "split": split,
                        "event_count_a": int(len(keys_a)),
                        "event_count_b": int(len(keys_b)),
                        "intersection_event_count": inter,
                        "union_event_count": uni,
                        "jaccard": jaccard,
                        "overlap_share_vs_a": _safe_div(inter, len(keys_a)),
                        "overlap_share_vs_b": _safe_div(inter, len(keys_b)),
                        "same_instrument_overlap_count": int(len(inst_a & inst_b)),
                        "same_instrument_overlap_share_vs_a": _safe_div(len(inst_a & inst_b), len(inst_a)),
                        "same_entry_date_overlap_count": int(len(date_a & date_b)),
                        "same_entry_date_overlap_share_vs_a": _safe_div(len(date_a & date_b), len(date_a)),
                        "overlap_status": status,
                    }
                )
    return pd.DataFrame(rows)


def _daily_candidate_count_audit(source: pd.DataFrame, union: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    source_valid = source[source["entry_resolution_status"].eq("passed") & source["split"].isin(SPLITS)].copy()
    for pool_id, part in source_valid.groupby("pool_id", sort=False):
        for (split, date), dpart in part.groupby(["split", "entry_execution_date"], sort=False):
            rows.append(
                {
                    "split": split,
                    "pool_id": pool_id,
                    "entry_execution_date": _date_str(date),
                    "daily_candidate_count": int(len(dpart)),
                    "unique_instrument_count": int(dpart["instrument_id"].nunique()),
                    "volume_money_count": int((dpart["source_family_id"] == "volume_money").sum()),
                    "range_breakout_count": int((dpart["source_family_id"] == "range_breakout").sum()),
                    "pullback_drawdown_count": int((dpart["source_family_id"] == "pullback_drawdown").sum()),
                }
            )
    for (split, date), dpart in union.groupby(["split", "entry_execution_date"], sort=False):
        rows.append(
            {
                "split": split,
                "pool_id": dpart.iloc[0]["pool_id"],
                "entry_execution_date": _date_str(date),
                "daily_candidate_count": int(len(dpart)),
                "unique_instrument_count": int(dpart["instrument_id"].nunique()),
                "volume_money_count": int(dpart["source_family_set"].astype(str).str.contains("volume_money").sum()),
                "range_breakout_count": int(dpart["source_family_set"].astype(str).str.contains("range_breakout").sum()),
                "pullback_drawdown_count": int(dpart["source_family_set"].astype(str).str.contains("pullback_drawdown").sum()),
            }
        )
    return pd.DataFrame(rows)


def _same_instrument_cluster_share(frame: pd.DataFrame, window: int) -> float:
    if frame.empty:
        return np.nan
    clustered = 0
    total = 0
    for _, part in frame.groupby("instrument_id", sort=False):
        idx = pd.to_numeric(part["entry_calendar_index"], errors="coerce").dropna().to_numpy(float)
        idx.sort()
        for pos, value in enumerate(idx):
            total += 1
            left = pos > 0 and value - idx[pos - 1] <= window
            right = pos < len(idx) - 1 and idx[pos + 1] - value <= window
            clustered += int(left or right)
    return _safe_div(clustered, total)


def _pseudo_diversification_audit(source: pd.DataFrame, union: pd.DataFrame, replay_hold120: pd.DataFrame, daily_counts: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    window = int(config["union_pool"]["nearby_window_trading_days"])
    thresholds = config["thresholds"]
    frames = []
    source_valid = source[source["entry_resolution_status"].eq("passed") & source["split"].isin(SPLITS)].copy()
    for pool_id, part in source_valid.groupby("pool_id", sort=False):
        frames.append((pool_id, part))
    frames.append((config["union_pool"]["union_pool_id"], union))
    rows: list[dict[str, Any]] = []
    complete_counts = replay_hold120[replay_hold120["policy_id"].eq(config["baseline"]["hold120_no_exit_policy_id"])].groupby(["pool_id", "split"])["replay_complete"].apply(lambda s: int(_bool_series(s).sum())).to_dict()
    for pool_id, frame in frames:
        for split in SPLITS:
            part = frame[frame["split"].eq(split)].copy()
            counts = daily_counts[(daily_counts["pool_id"].eq(pool_id)) & (daily_counts["split"].eq(split))]["daily_candidate_count"]
            instruments = part["instrument_id"].value_counts(normalize=True)
            industries = part["industry_target_key"].fillna("missing_industry").value_counts(normalize=True)
            years = part["entry_calendar_year"].value_counts(normalize=True)
            months = pd.to_datetime(part["entry_execution_date"]).dt.to_period("M").astype(str).value_counts(normalize=True)
            markets = part["market_regime_bucket"].fillna("missing_market_regime").value_counts(normalize=True)
            states = part["industry_regime_bucket"].fillna("missing_industry").value_counts(normalize=True)
            same_inst = _same_instrument_cluster_share(part, window)
            rec = {
                "split": split,
                "pool_id": pool_id,
                "event_count": int(len(part)),
                "replay_complete_count": complete_counts.get((pool_id, split), np.nan),
                "top1_calendar_year_share": float(years.iloc[0]) if len(years) else np.nan,
                "top1_calendar_month_share": float(months.iloc[0]) if len(months) else np.nan,
                "top1_instrument_share": float(instruments.iloc[0]) if len(instruments) else np.nan,
                "top5_instrument_share": float(instruments.iloc[:5].sum()) if len(instruments) else np.nan,
                "top1_industry_share": float(industries.iloc[0]) if len(industries) else np.nan,
                "top3_industry_share": float(industries.iloc[:3].sum()) if len(industries) else np.nan,
                "top1_market_state_share": float(markets.iloc[0]) if len(markets) else np.nan,
                "top1_industry_state_share": float(states.iloc[0]) if len(states) else np.nan,
                "daily_candidate_count_mean": float(counts.mean()) if len(counts) else np.nan,
                "daily_candidate_count_p50": _quantile(counts, 0.50),
                "daily_candidate_count_p90": _quantile(counts, 0.90),
                "daily_candidate_count_p95": _quantile(counts, 0.95),
                "daily_candidate_count_p99": _quantile(counts, 0.99),
                "same_instrument_20d_cluster_share": same_inst,
            }
            concentrated = (
                rec["top1_instrument_share"] > thresholds["pseudo_top1_instrument_concentrated_min"]
                or rec["top5_instrument_share"] > thresholds["pseudo_top5_instrument_concentrated_min"]
                or rec["top1_industry_share"] > thresholds["pseudo_top1_industry_concentrated_min"]
                or rec["same_instrument_20d_cluster_share"] > thresholds["pseudo_same_instrument_cluster_concentrated_min"]
                or rec["daily_candidate_count_p99"] > thresholds["pseudo_daily_candidate_p99_concentrated_min"]
            )
            sufficient = (
                rec["top1_instrument_share"] <= thresholds["pseudo_top1_instrument_sufficient_max"]
                and rec["top5_instrument_share"] <= thresholds["pseudo_top5_instrument_sufficient_max"]
                and rec["top1_industry_share"] <= thresholds["pseudo_top1_industry_sufficient_max"]
                and rec["same_instrument_20d_cluster_share"] <= thresholds["pseudo_same_instrument_cluster_sufficient_max"]
                and rec["daily_candidate_count_p99"] <= thresholds["pseudo_daily_candidate_p99_sufficient_max"]
            )
            rec["pseudo_diversification_status"] = "concentrated" if concentrated else ("sufficient" if sufficient else "watch")
            rows.append(rec)
    return pd.DataFrame(rows)


def _build_policy_matrix(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for hold in config["policy_grid"]["holds"]:
        hold_id = str(hold["hold_rule_id"])
        max_hold = int(hold["max_holding_days"])
        exit_specs: list[tuple[str, dict[str, Any]]] = [("no_exit", {})]
        for activation in config["policy_grid"]["exits"]["break_even_after_gain"]["activation_gain_pct"]:
            exit_specs.append(("break_even_after_gain", {"activation_gain_pct": float(activation)}))
        for stop in config["policy_grid"]["exits"]["fixed_stop"]["stop_loss_pct"]:
            exit_specs.append(("fixed_stop", {"stop_loss_pct": float(stop)}))
        for exit_family, params in exit_specs:
            invalid = ""
            param_part = "none" if not params else "_".join(f"{k}_{str(v).replace('-', 'm').replace('.', 'p')}" for k, v in sorted(params.items()))
            policy_id = f"{hold_id}__{exit_family}__{param_part}"
            formula = f"entry=next_open;hold={max_hold};exit={exit_family};params={_canonical_json(params)};sizing=fixed_size;cost={config['cost_model']['cost_model_id']}"
            rows.append(
                {
                    "policy_id": policy_id,
                    "policy_family_id": exit_family,
                    "hold_rule_id": hold_id,
                    "hold_rule_max_days": max_hold,
                    "exit_rule_family_id": exit_family,
                    "exit_rule_id": exit_family if not params else f"{exit_family}__{_hash_json(params)[:8]}",
                    "sizing_rule_id": "fixed_size",
                    "parameter_set_id": _hash_text(f"{exit_family}|{_canonical_json(params)}")[:12],
                    "parameter_values_json": _canonical_json({"exit": params, "sizing": {"position_weight": 1.0}}),
                    "is_train_selectable": invalid == "",
                    "is_validation_selectable": invalid == "",
                    "is_active_cap_sensitivity_policy": False,
                    "invalid_policy_reason": invalid,
                    "formula_text": formula,
                    "formula_hash": _hash_text(formula),
                }
            )
    matrix = pd.DataFrame(rows)
    return matrix.sort_values(["hold_rule_max_days", "exit_rule_family_id", "policy_id"]).reset_index(drop=True)


def _price_by_inst(price: pd.DataFrame) -> dict[str, pd.DataFrame]:
    price = price.copy()
    price["executable_open_flag"] = (
        (price["adjusted_open"] > 0)
        & (price["volume"] > 0)
        & (price["money"] > 0)
        & (~_bool_series(price["suspended_or_dirty_bar"], default=True))
    )
    return {inst: part.sort_values("calendar_index").set_index("calendar_index", drop=False) for inst, part in price.groupby("instrument_id", sort=False)}


def _event_data(row: pd.Series, price_by_inst: dict[str, pd.DataFrame], config: dict[str, Any]) -> dict[str, Any] | None:
    inst = price_by_inst.get(str(row["instrument_id"]).upper())
    if inst is None or pd.isna(row.get("entry_calendar_index", np.nan)):
        return None
    entry_idx = int(row["entry_calendar_index"])
    max_offset = int(config["execution"]["max_holding_days"]) + int(config["execution"]["max_exit_execution_lag_trading_days"])
    offsets = np.arange(0, max_offset + 1)
    indices = entry_idx + offsets
    if not set(indices).issubset(set(inst.index)):
        return None
    path = inst.loc[indices]
    if isinstance(path, pd.Series):
        path = path.to_frame().T
    path = path.reset_index(drop=True)
    entry_price = float(row["entry_price"])
    close = pd.to_numeric(path["adjusted_close"], errors="coerce").to_numpy(float)
    open_ = pd.to_numeric(path["adjusted_open"], errors="coerce").to_numpy(float)
    dates = pd.to_datetime(path["trade_date"]).dt.normalize().to_numpy()
    executable = _bool_series(path["executable_open_flag"]).to_numpy(bool)
    close_return = close / entry_price - 1.0
    return {
        "entry_price": entry_price,
        "offsets": offsets,
        "trade_date": dates,
        "adjusted_open": open_,
        "adjusted_close": close,
        "executable_open_flag": executable,
        "close_return_from_entry": close_return,
    }


def _signal_offset(data: dict[str, Any], policy: pd.Series) -> tuple[int | None, str]:
    max_hold = int(policy["hold_rule_max_days"])
    returns = np.asarray(data["close_return_from_entry"][: max_hold + 1], dtype=float)
    if len(returns) < max_hold + 1 or not np.isfinite(returns).all():
        return None, "censored_by_missing_price"
    family = str(policy["exit_rule_family_id"])
    params = json.loads(str(policy["parameter_values_json"])).get("exit", {})
    if family == "no_exit":
        return max_hold, ""
    if family == "fixed_stop":
        hit = np.where(returns <= float(params["stop_loss_pct"]))[0]
        return int(hit[0]) if len(hit) else max_hold, ""
    if family == "break_even_after_gain":
        activated = False
        for offset, ret in enumerate(returns):
            if not activated and ret >= float(params["activation_gain_pct"]):
                activated = True
            if activated and ret <= 0.0:
                return int(offset), ""
        return max_hold, ""
    return None, "invalid_policy"


def _first_exit_execution(data: dict[str, Any], signal_offset: int, max_lag: int) -> tuple[int | None, pd.Timestamp | pd.NaT]:
    for offset in range(signal_offset + 1, signal_offset + max_lag + 1):
        if offset >= len(data["adjusted_open"]):
            continue
        price = float(data["adjusted_open"][offset])
        if bool(data["executable_open_flag"][offset]) and np.isfinite(price) and price > 0:
            return int(offset), pd.Timestamp(data["trade_date"][offset]).normalize()
    return None, pd.NaT


def _replay_events(events: pd.DataFrame, policy_matrix: pd.DataFrame, price_by_inst: dict[str, pd.DataFrame], config: dict[str, Any], label: str) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    bounds = _split_bounds(config)
    cost = config["cost_model"]
    entry_cost = (float(cost["entry_slippage_bps"]) + float(cost["commission_bps_per_side"])) / 10000.0
    exit_cost = (float(cost["exit_slippage_bps"]) + float(cost["commission_bps_per_side"]) + float(cost["stamp_tax_bps_on_exit"])) / 10000.0
    total_cost_bps = float(cost["entry_slippage_bps"]) + float(cost["exit_slippage_bps"]) + 2.0 * float(cost["commission_bps_per_side"]) + float(cost["stamp_tax_bps_on_exit"])
    max_exit_lag = int(config["execution"]["max_exit_execution_lag_trading_days"])
    threshold = float(config["thresholds"]["max_gain50_threshold"])
    event_cache: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    valid_policies = policy_matrix[policy_matrix["invalid_policy_reason"].fillna("").eq("")].reset_index(drop=True)
    for idx, event in events.reset_index(drop=True).iterrows():
        data = _event_data(event, price_by_inst, config)
        event_id = str(event["r04e_event_id"])
        if data is not None:
            event_cache[event_id] = data
        hold_returns = data["close_return_from_entry"][:121] if data is not None and len(data["close_return_from_entry"]) >= 121 else np.array([])
        hold120_complete = len(hold_returns) == 121 and np.isfinite(hold_returns).all()
        hold120_max = float(np.nanmax(hold_returns)) if hold120_complete else np.nan
        hold120_flag = bool(hold120_complete and hold120_max >= threshold)
        first_hit_date = pd.NaT
        if hold120_flag:
            hit_offset = int(np.where(hold_returns >= threshold)[0][0])
            first_hit_date = pd.Timestamp(data["trade_date"][hit_offset]).normalize()
        base = {
            "r04e_event_id": event_id,
            "source_pool_event_id": event.get("source_pool_event_id", event.get("pool_event_id", "")),
            "union_event_key": event.get("union_event_key", ""),
            "pool_id": event["pool_id"],
            "replay_universe": event["replay_universe"],
            "event_weight": float(event.get("event_weight", 1.0)),
            "split": event["split"],
            "instrument_id": event["instrument_id"],
            "entry_execution_date": event["entry_execution_date"],
            "entry_price": event["entry_price"],
            "entry_calendar_year": event.get("entry_calendar_year", np.nan),
            "entry_calendar_quarter": event.get("entry_calendar_quarter", ""),
            "market_regime_bucket": event.get("market_regime_bucket", ""),
            "industry_regime_bucket": event.get("industry_regime_bucket", ""),
            "industry_target_key": event.get("industry_target_key", ""),
            "source_family_set": event.get("source_family_set", ""),
            "source_family_count": int(event.get("source_family_count", 1)),
            "cap_rank_key": event.get("cap_rank_key", ""),
            "hold120_no_exit_max_gain50_flag": hold120_flag,
            "hold120_no_exit_first_plus50_hit_date": first_hit_date,
            "hold120_no_exit_max_gain120d": hold120_max,
            "net_return_metric_basis": "unweighted_event_net_return",
        }
        for _, policy in valid_policies.iterrows():
            rec = {
                **base,
                "policy_id": policy["policy_id"],
                "policy_family_id": policy["policy_family_id"],
                "hold_rule_id": policy["hold_rule_id"],
                "hold_rule_max_days": policy["hold_rule_max_days"],
                "exit_rule_family_id": policy["exit_rule_family_id"],
                "exit_rule_id": policy["exit_rule_id"],
                "sizing_rule_id": policy["sizing_rule_id"],
                "parameter_set_id": policy["parameter_set_id"],
                "parameter_values_json": policy["parameter_values_json"],
                "replay_status": "censored_by_missing_price",
                "replay_complete": False,
            }
            if data is None:
                rows.append(rec)
                continue
            signal_offset, status = _signal_offset(data, policy)
            if status:
                rec["replay_status"] = status
                rows.append(rec)
                continue
            exit_offset, exit_date = _first_exit_execution(data, int(signal_offset), max_exit_lag)
            if exit_offset is None:
                rec.update({"exit_signal_offset": signal_offset, "replay_status": "censored_by_no_exit_execution"})
                rows.append(rec)
                continue
            if _split_for_date(exit_date, bounds) != str(event["split"]):
                rec.update({"exit_signal_offset": signal_offset, "exit_execution_offset": exit_offset, "exit_execution_date": exit_date, "replay_status": "censored_by_split_boundary"})
                rows.append(rec)
                continue
            exit_price = float(data["adjusted_open"][exit_offset])
            gross_return = exit_price / float(event["entry_price"]) - 1.0
            net_return = gross_return - entry_cost - exit_cost
            signal_returns = data["close_return_from_entry"][: int(signal_offset) + 1]
            policy_max_gain = float(np.nanmax(signal_returns)) if len(signal_returns) else np.nan
            max_adverse = float(np.nanmin(signal_returns)) if len(signal_returns) else np.nan
            retained = bool(hold120_flag and not pd.isna(first_hit_date) and pd.Timestamp(exit_date) > pd.Timestamp(first_hit_date))
            rec.update(
                {
                    "exit_signal_offset": int(signal_offset),
                    "exit_signal_date": pd.Timestamp(data["trade_date"][int(signal_offset)]).normalize(),
                    "exit_execution_offset": int(exit_offset),
                    "exit_execution_date": exit_date,
                    "exit_price": exit_price,
                    "gross_return": gross_return,
                    "entry_cost": entry_cost,
                    "exit_cost": exit_cost,
                    "total_cost_bps": total_cost_bps,
                    "net_return": net_return,
                    "loss_le_minus5_flag": net_return <= -0.05,
                    "loss_le_minus10_flag": net_return <= -0.10,
                    "max_adverse_excursion": max_adverse,
                    "max_gain_to_exit_signal": policy_max_gain,
                    "max_gain50_flag": policy_max_gain >= threshold,
                    "policy_retained_hold120_max_gain50_flag": retained,
                    "avg_holding_days": int(exit_offset),
                    "replay_status": "replay_complete",
                    "replay_complete": True,
                }
            )
            rows.append(rec)
        if (idx + 1) % 5000 == 0:
            print(f"replayed {idx + 1:,}/{len(events):,} {label} events", flush=True)
    out = pd.DataFrame(rows)
    out["replay_complete"] = _bool_series(out["replay_complete"])
    return out, event_cache


def _matched_baseline_reconstruction(union: pd.DataFrame, baseline: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    min_ess = float(config["thresholds"]["minimum_matched_comparator_effective_sample_size"])
    match_levels = [
        ("split", "entry_calendar_year", "entry_calendar_quarter", "market_regime_bucket", "industry_regime_bucket"),
        ("split", "entry_calendar_year", "market_regime_bucket", "industry_regime_bucket"),
        ("split", "entry_calendar_year", "market_regime_bucket"),
        ("split", "entry_calendar_year"),
    ]
    baseline_groups: dict[tuple[str, ...], dict[tuple[Any, ...], pd.Index]] = {}
    for level in match_levels:
        baseline_groups[level] = {key if isinstance(key, tuple) else (key,): part.index for key, part in baseline.groupby(list(level), dropna=False)}
    weights: dict[int, float] = defaultdict(float)
    fallback_counts: dict[tuple[str, str], int] = defaultdict(int)
    matched_by_split: dict[str, int] = defaultdict(int)
    total_by_split = union.groupby("split").size().to_dict()
    for _, event in union.iterrows():
        matched = False
        for level in match_levels:
            key = tuple(event[col] for col in level)
            idx = baseline_groups[level].get(key)
            if idx is None or len(idx) == 0:
                continue
            add = 1.0 / len(idx)
            for baseline_idx in idx:
                weights[int(baseline_idx)] += add
            fallback_name = "+".join(level)
            fallback_counts[(str(event["split"]), fallback_name)] += 1
            matched_by_split[str(event["split"])] += 1
            matched = True
            break
        if not matched:
            fallback_counts[(str(event["split"]), "unmatched")] += 1
    if weights:
        panel = baseline.loc[list(weights.keys())].copy()
        panel["event_weight"] = [weights[int(idx)] for idx in panel.index]
    else:
        panel = pd.DataFrame(columns=list(baseline.columns) + ["event_weight"])
    panel["matched_replay_universe"] = "matched_baseline_A"
    panel["matched_pool_id"] = config["union_pool"]["union_pool_id"]
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        split_match = panel[panel["split"].eq(split)].copy()
        weight_sum = float(split_match["event_weight"].sum()) if not split_match.empty else 0.0
        weight_sq_sum = float(np.square(split_match["event_weight"]).sum()) if not split_match.empty else 0.0
        ess = weight_sum * weight_sum / weight_sq_sum if weight_sq_sum > 0 else 0.0
        status = "sufficient" if ess >= min_ess and matched_by_split.get(split, 0) > 0 else "insufficient"
        total = int(total_by_split.get(split, 0))
        for (_, fallback), count in sorted((k, v) for k, v in fallback_counts.items() if k[0] == split):
            rows.append(
                {
                    "split": split,
                    "pool_id": config["union_pool"]["union_pool_id"],
                    "matched_comparator_status": status,
                    "matched_comparator_count": int(weight_sum),
                    "matched_comparator_unique_event_count": int(len(split_match)),
                    "matched_comparator_effective_sample_size": ess,
                    "matched_pool_event_count": int(matched_by_split.get(split, 0)),
                    "fallback_level": fallback,
                    "fallback_level_share": _safe_div(count, total),
                }
            )
        if not any(k[0] == split for k in fallback_counts):
            rows.append(
                {
                    "split": split,
                    "pool_id": config["union_pool"]["union_pool_id"],
                    "matched_comparator_status": status,
                    "matched_comparator_count": 0,
                    "matched_comparator_unique_event_count": 0,
                    "matched_comparator_effective_sample_size": ess,
                    "matched_pool_event_count": 0,
                    "fallback_level": "unmatched",
                    "fallback_level_share": 1.0,
                }
            )
    return panel.reset_index(drop=True), pd.DataFrame(rows)


def _matched_replay_from_baseline(baseline_replay: pd.DataFrame, matched_panel: pd.DataFrame) -> pd.DataFrame:
    if matched_panel.empty:
        return pd.DataFrame(columns=list(baseline_replay.columns))
    weights = matched_panel[["pool_event_id", "split", "event_weight"]].copy()
    replay = baseline_replay.merge(
        weights,
        left_on=["source_pool_event_id", "split"],
        right_on=["pool_event_id", "split"],
        how="inner",
        suffixes=("", "_matched"),
    )
    replay["event_weight"] = pd.to_numeric(replay["event_weight_matched"], errors="coerce").fillna(0.0)
    replay["pool_id"] = "matched_baseline_A"
    replay["replay_universe"] = "matched_baseline_A"
    replay["r04e_event_id"] = "matched_baseline_A|" + replay["source_pool_event_id"].astype(str)
    return replay.drop(columns=[c for c in ["pool_event_id", "event_weight_matched"] if c in replay.columns])


def _matched_summary(matched_replay: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    min_ess = float(config["thresholds"]["minimum_matched_comparator_effective_sample_size"])
    for (policy_id, split), part in matched_replay.groupby(["policy_id", "split"], sort=False, dropna=False):
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
                "matched_baseline_net_return_mean": _weighted_mean(complete, "net_return"),
                "matched_baseline_net_return_p10": _weighted_quantile(complete["net_return"], complete["event_weight"], 0.10) if len(complete) else np.nan,
                "matched_baseline_loss_le_minus5_rate": _weighted_mean(complete.assign(loss_numeric=complete["loss_le_minus5_flag"].astype(float)), "loss_numeric") if len(complete) else np.nan,
                "matched_comparator_status": "sufficient" if ess >= min_ess else "insufficient",
            }
        )
    return pd.DataFrame(rows)


def _summarize_event_replay(replay: pd.DataFrame, matched: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = ["pool_id", "replay_universe", "policy_id", "policy_family_id", "hold_rule_id", "exit_rule_family_id", "split"]
    for keys, part in replay.groupby(group_cols, dropna=False, sort=False):
        rec = dict(zip(group_cols, keys))
        complete = part[_bool_series(part["replay_complete"])].copy()
        event_count = int(len(part))
        replay_complete_count = int(len(complete))
        hold_winners = part[_bool_series(part["hold120_no_exit_max_gain50_flag"])]
        retained = int(_bool_series(hold_winners["policy_retained_hold120_max_gain50_flag"]).sum()) if len(hold_winners) else 0
        hold_count = int(len(hold_winners))
        rec.update(
            {
                "event_count": event_count,
                "replay_complete_count": replay_complete_count,
                "censored_count": event_count - replay_complete_count,
                "censored_share": _safe_div(event_count - replay_complete_count, event_count),
                "net_return_mean": float(complete["net_return"].mean()) if replay_complete_count else np.nan,
                "net_return_median": _quantile(complete["net_return"], 0.50),
                "net_return_p10": _quantile(complete["net_return"], 0.10),
                "net_return_p25": _quantile(complete["net_return"], 0.25),
                "net_return_p75": _quantile(complete["net_return"], 0.75),
                "net_return_p90": _quantile(complete["net_return"], 0.90),
                "loss_le_minus5_rate": float(complete["loss_le_minus5_flag"].mean()) if replay_complete_count else np.nan,
                "loss_le_minus10_rate": float(complete["loss_le_minus10_flag"].mean()) if replay_complete_count else np.nan,
                "max_drawdown_p50": _quantile(complete["max_adverse_excursion"], 0.50),
                "max_drawdown_p90": _quantile(complete["max_adverse_excursion"], 0.90),
                "max_gain50_count": int(complete["max_gain50_flag"].sum()) if replay_complete_count else 0,
                "max_gain50_rate": float(complete["max_gain50_flag"].mean()) if replay_complete_count else np.nan,
                "hold120_no_exit_max_gain50_count": hold_count,
                "policy_retained_hold120_max_gain50_count": retained,
                "policy_max_gain50_retention_rate_vs_hold120_no_exit": _safe_div(retained, hold_count),
                "max_gain120d_p90": _quantile(part["hold120_no_exit_max_gain120d"], 0.90),
                "avg_holding_days": float(complete["avg_holding_days"].mean()) if replay_complete_count else np.nan,
            }
        )
        rows.append(rec)
    summary = pd.DataFrame(rows)
    if matched.empty:
        for col in ["matched_comparator_status", "matched_comparator_effective_sample_size", "matched_baseline_net_return_mean", "matched_baseline_net_return_p10", "matched_baseline_loss_le_minus5_rate"]:
            summary[col] = np.nan
    else:
        summary = summary.merge(matched, on=["policy_id", "split"], how="left")
    union_pool = config["union_pool"]["union_pool_id"]
    is_union = summary["pool_id"].eq(union_pool)
    summary["net_return_mean_delta_vs_matched_baseline_A"] = np.where(is_union, summary["net_return_mean"] - summary["matched_baseline_net_return_mean"], np.nan)
    summary["p10_delta_vs_matched_baseline_A"] = np.where(is_union, summary["net_return_p10"] - summary["matched_baseline_net_return_p10"], np.nan)
    summary["loss_le_minus5_delta_vs_matched_baseline_A"] = np.where(is_union, summary["loss_le_minus5_rate"] - summary["matched_baseline_loss_le_minus5_rate"], np.nan)
    return summary


def _hold120_readiness(event_summary: pd.DataFrame, pseudo: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    policy_id = config["baseline"]["hold120_no_exit_policy_id"]
    union_pool = config["union_pool"]["union_pool_id"]
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        row = event_summary[(event_summary["pool_id"].eq(union_pool)) & (event_summary["policy_id"].eq(policy_id)) & (event_summary["split"].eq(split))]
        if row.empty:
            continue
        rec = row.iloc[0].to_dict()
        pseudo_row = pseudo[(pseudo["pool_id"].eq(union_pool)) & (pseudo["split"].eq(split))]
        pseudo_status = "" if pseudo_row.empty else str(pseudo_row.iloc[0]["pseudo_diversification_status"])
        rec["matched_baseline_net_return_mean"] = rec.get("matched_baseline_net_return_mean", np.nan)
        for col in ["top1_calendar_year_share", "top1_instrument_share", "top1_industry_share"]:
            rec[col] = np.nan if pseudo_row.empty else pseudo_row.iloc[0][col]
        reasons: list[str] = []
        thresholds = config["thresholds"]
        if split == "validation":
            if rec["replay_complete_count"] < thresholds["gate0_conditional_validation_replay_complete_count"]:
                reasons.append("insufficient_denominator")
            if rec.get("matched_comparator_status", "") != "sufficient":
                reasons.append("insufficient_matched_comparator")
            if pseudo_status == "concentrated":
                reasons.append("pseudo_diversification_concentrated")
            if rec["net_return_mean"] < thresholds["gate0_conditional_min_validation_net_return_mean"]:
                reasons.append("absolute_validation_net_too_weak")
            if rec["net_return_mean_delta_vs_matched_baseline_A"] < thresholds["gate0_min_matched_net_delta"]:
                reasons.append("matched_delta_too_weak")
            if rec["p10_delta_vs_matched_baseline_A"] < 0:
                reasons.append("p10_delta_negative")
            if rec["loss_le_minus5_delta_vs_matched_baseline_A"] >= 0:
                reasons.append("loss_delta_not_improved")
            strong = (
                rec["replay_complete_count"] >= thresholds["gate0_strong_validation_replay_complete_count"]
                and rec["net_return_mean"] > 0
                and rec["net_return_mean_delta_vs_matched_baseline_A"] >= thresholds["gate0_min_matched_net_delta"]
                and rec["p10_delta_vs_matched_baseline_A"] >= 0
                and rec["loss_le_minus5_delta_vs_matched_baseline_A"] < 0
                and rec.get("matched_comparator_status", "") == "sufficient"
                and pseudo_status != "concentrated"
            )
            conditional = (
                rec["replay_complete_count"] >= thresholds["gate0_conditional_validation_replay_complete_count"]
                and rec["net_return_mean"] >= thresholds["gate0_conditional_min_validation_net_return_mean"]
                and rec["net_return_mean_delta_vs_matched_baseline_A"] >= thresholds["gate0_min_matched_net_delta"]
                and rec["p10_delta_vs_matched_baseline_A"] >= 0
                and rec["loss_le_minus5_delta_vs_matched_baseline_A"] < 0
                and rec.get("matched_comparator_status", "") == "sufficient"
                and pseudo_status != "concentrated"
            )
            rec["readiness_status"] = "strong_go" if strong else ("conditional_go" if conditional else "stop")
            rec["readiness_failure_reason"] = "" if strong or conditional else "|".join(reasons)
        else:
            rec["readiness_status"] = "readout_only"
            rec["readiness_failure_reason"] = ""
        rec["pseudo_diversification_status"] = pseudo_status
        rows.append(rec)
    return pd.DataFrame(rows)


def _gate0_audit(readiness: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    validation = readiness[readiness["split"].eq("validation")]
    if validation.empty:
        return pd.DataFrame(
            [
                {
                    "split": "validation",
                    "gate0_status": "gate0_blocked_insufficient_inputs",
                    "readiness_status": "",
                    "readiness_failure_reason": "missing_validation_readiness",
                    "gate0_stop_category": "input_or_comparator_failure",
                }
            ]
        )
    row = validation.iloc[0]
    readiness_status = str(row["readiness_status"])
    if readiness_status == "strong_go":
        gate0_status = "gate0_strong_go"
    elif readiness_status == "conditional_go":
        gate0_status = "gate0_conditional_go"
    else:
        gate0_status = "gate0_stop_low_quality_union"
    reasons = str(row.get("readiness_failure_reason", ""))
    if gate0_status in {"gate0_strong_go", "gate0_conditional_go"}:
        category = "not_stopped"
    elif any(reason in reasons for reason in ["insufficient_denominator", "insufficient_matched_comparator", "pseudo_diversification_concentrated"]):
        category = "input_or_comparator_failure"
    elif (
        "absolute_validation_net_too_weak" in reasons
        and float(row.get("net_return_mean_delta_vs_matched_baseline_A", np.nan)) >= 0.02
        and float(row.get("p10_delta_vs_matched_baseline_A", np.nan)) >= 0
        and float(row.get("loss_le_minus5_delta_vs_matched_baseline_A", np.nan)) < 0
    ):
        category = "weak_absolute_but_left_tail_improved"
    else:
        category = "low_quality_union"
    rows.append(
        {
            "split": "validation",
            "gate0_status": gate0_status,
            "readiness_status": readiness_status,
            "readiness_failure_reason": reasons,
            "gate0_stop_category": category,
        }
    )
    return pd.DataFrame(rows)


def _event_daily_path(replay_policy: pd.DataFrame, event_cache: dict[str, dict[str, Any]], config: dict[str, Any]) -> pd.DataFrame:
    cost = config["cost_model"]
    entry_cost = (float(cost["entry_slippage_bps"]) + float(cost["commission_bps_per_side"])) / 10000.0
    exit_cost = (float(cost["exit_slippage_bps"]) + float(cost["commission_bps_per_side"]) + float(cost["stamp_tax_bps_on_exit"])) / 10000.0
    records: list[tuple[Any, ...]] = []
    cols = [
        "r04e_event_id",
        "policy_id",
        "split",
        "trade_date",
        "entry_execution_date",
        "exit_execution_date",
        "active_flag",
        "daily_gross_return",
        "daily_cost_return",
        "daily_net_return",
        "source_family_set",
        "source_family_count",
        "instrument_id",
        "cap_rank_key",
    ]
    complete = replay_policy[_bool_series(replay_policy["replay_complete"])].copy()
    for row in complete.itertuples(index=False):
        data = event_cache.get(row.r04e_event_id)
        if data is None or pd.isna(row.exit_execution_offset):
            continue
        exit_offset = int(row.exit_execution_offset)
        if exit_offset <= 0 or exit_offset >= len(data["adjusted_open"]):
            continue
        for offset in range(0, exit_offset + 1):
            if offset == 0:
                gross = float(data["adjusted_close"][0]) / float(data["entry_price"]) - 1.0
                daily_cost = entry_cost
            elif offset == exit_offset:
                prev_close = float(data["adjusted_close"][offset - 1])
                gross = float(data["adjusted_open"][offset]) / prev_close - 1.0 if prev_close > 0 else np.nan
                daily_cost = exit_cost
            else:
                prev_close = float(data["adjusted_close"][offset - 1])
                gross = float(data["adjusted_close"][offset]) / prev_close - 1.0 if prev_close > 0 else np.nan
                daily_cost = 0.0
            if not np.isfinite(gross):
                continue
            records.append(
                (
                    row.r04e_event_id,
                    row.policy_id,
                    row.split,
                    pd.Timestamp(data["trade_date"][offset]).normalize(),
                    pd.Timestamp(row.entry_execution_date).normalize(),
                    pd.Timestamp(row.exit_execution_date).normalize(),
                    True,
                    gross,
                    daily_cost,
                    gross - daily_cost,
                    row.source_family_set,
                    int(row.source_family_count),
                    row.instrument_id,
                    row.cap_rank_key,
                )
            )
    if not records:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame.from_records(records, columns=cols)


class _ParquetAppender:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.writer = None

    def append(self, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        import pyarrow as pa
        import pyarrow.parquet as pq

        self.path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pandas(frame, preserve_index=False)
        if self.writer is None:
            self.writer = pq.ParquetWriter(self.path, table.schema, compression="zstd")
        self.writer.write_table(table)

    def close(self) -> None:
        if self.writer is not None:
            self.writer.close()
            self.writer = None


def _split_calendar(calendar: pd.DatetimeIndex, config: dict[str, Any]) -> pd.DataFrame:
    bounds = _split_bounds(config)
    rows = []
    for split, (start, end) in bounds.items():
        dates = [pd.Timestamp(date).normalize() for date in calendar if start <= pd.Timestamp(date).normalize() <= end]
        rows.extend({"split": split, "trade_date": date} for date in dates)
    return pd.DataFrame(rows)


def _apply_cap(path: pd.DataFrame, cap: int | None) -> pd.DataFrame:
    if cap is None or path.empty:
        out = path.copy()
        out["raw_active_count"] = out.groupby(["split", "trade_date"])["r04e_event_id"].transform("nunique") if not out.empty else pd.Series(dtype=float)
        return out
    out = path.copy()
    out["raw_active_count"] = out.groupby(["split", "trade_date"])["r04e_event_id"].transform("nunique")
    out = out.sort_values(["split", "trade_date", "cap_rank_key", "r04e_event_id"]).copy()
    out["_cap_rank"] = out.groupby(["split", "trade_date"]).cumcount() + 1
    return out[out["_cap_rank"] <= int(cap)].drop(columns=["_cap_rank"])


def _weighted_path(path: pd.DataFrame, weighting: str, cap: int | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    capped = _apply_cap(path, cap)
    if capped.empty:
        return capped.assign(portfolio_event_weight_on_date=pd.Series(dtype=float)), pd.DataFrame()
    if weighting == "active_equal_weight":
        counts = capped.groupby(["split", "trade_date"])["r04e_event_id"].transform("nunique")
        capped = capped.copy()
        capped["portfolio_event_weight_on_date"] = 1.0 / counts
        fam = capped[["split", "trade_date", "r04e_event_id", "source_family_set", "source_family_count", "portfolio_event_weight_on_date", "daily_net_return"]].copy()
        fam["source_family_id"] = fam["source_family_set"].astype(str).str.split(";")
        fam = fam.explode("source_family_id")
        fam["family_part_weight"] = fam["portfolio_event_weight_on_date"] / pd.to_numeric(fam["source_family_count"], errors="coerce").replace(0, np.nan)
        return capped, fam
    if weighting != "family_balanced_active_equal_weight":
        raise ValueError(f"unsupported weighting: {weighting}")
    exp = capped[["split", "trade_date", "r04e_event_id", "source_family_set", "daily_net_return"]].copy()
    exp["source_family_id"] = exp["source_family_set"].astype(str).str.split(";")
    exp = exp.explode("source_family_id")
    counts = exp.groupby(["split", "trade_date", "source_family_id"])["r04e_event_id"].transform("nunique")
    active_family_count = exp.groupby(["split", "trade_date"])["source_family_id"].transform("nunique")
    exp["family_part_weight"] = 1.0 / active_family_count / counts
    weights = exp.groupby(["split", "trade_date", "r04e_event_id"], as_index=False)["family_part_weight"].sum()
    capped = capped.merge(weights.rename(columns={"family_part_weight": "portfolio_event_weight_on_date"}), on=["split", "trade_date", "r04e_event_id"], how="left")
    return capped, exp


def _portfolio_daily_from_path(path: pd.DataFrame, weighting: str, cap: int | None, calendar_frame: pd.DataFrame, portfolio_id: str, policy_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    weighted, family_parts = _weighted_path(path, weighting, cap)
    if weighted.empty:
        daily = calendar_frame.copy()
        daily["portfolio_id"] = portfolio_id
        daily["policy_id"] = policy_id
        daily["portfolio_weighting_id"] = weighting
        daily["daily_active_cap"] = "none" if cap is None else f"cap{int(cap)}"
        daily["portfolio_daily_net_return"] = 0.0
        daily["active_count"] = 0
        daily["raw_active_count"] = 0
        daily["gross_exposure"] = 0.0
        return daily, pd.DataFrame()
    weighted["weighted_daily_net_return"] = weighted["daily_net_return"] * weighted["portfolio_event_weight_on_date"]
    grouped = weighted.groupby(["split", "trade_date"], as_index=False).agg(
        portfolio_daily_net_return=("weighted_daily_net_return", "sum"),
        active_count=("r04e_event_id", "nunique"),
        raw_active_count=("raw_active_count", "max"),
        gross_exposure=("portfolio_event_weight_on_date", "sum"),
    )
    daily = calendar_frame.merge(grouped, on=["split", "trade_date"], how="left")
    daily["portfolio_daily_net_return"] = daily["portfolio_daily_net_return"].fillna(0.0)
    daily["active_count"] = daily["active_count"].fillna(0).astype(int)
    daily["raw_active_count"] = daily["raw_active_count"].fillna(0).astype(int)
    daily["gross_exposure"] = daily["gross_exposure"].fillna(0.0)
    daily["portfolio_id"] = portfolio_id
    daily["policy_id"] = policy_id
    daily["portfolio_weighting_id"] = weighting
    daily["daily_active_cap"] = "none" if cap is None else f"cap{int(cap)}"
    if not family_parts.empty:
        family_parts = family_parts.copy()
        family_parts["policy_id"] = policy_id
        family_parts["portfolio_id"] = portfolio_id
        family_parts["portfolio_weighting_id"] = weighting
        family_parts["daily_active_cap"] = "none" if cap is None else f"cap{int(cap)}"
    return daily, family_parts


def _max_drawdown_positive(returns: pd.Series) -> float:
    clean = pd.to_numeric(returns, errors="coerce").fillna(0.0).to_numpy(float)
    if len(clean) == 0:
        return np.nan
    wealth = np.cumprod(1.0 + clean)
    peak = np.maximum.accumulate(wealth)
    dd = wealth / peak - 1.0
    return float(abs(np.nanmin(dd)))


def _rolling_return(returns: pd.Series, window: int, agg: str) -> float:
    clean = pd.to_numeric(returns, errors="coerce").fillna(0.0)
    rolled = (1.0 + clean).rolling(window, min_periods=window).apply(np.prod, raw=True) - 1.0
    rolled = rolled.dropna()
    if rolled.empty:
        return np.nan
    return float(rolled.min() if agg == "min" else rolled.max())


def _portfolio_summaries(daily: pd.DataFrame, replay: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    complete = replay[_bool_series(replay["replay_complete"])].copy()
    if not complete.empty:
        complete["entry_month"] = pd.to_datetime(complete["entry_execution_date"]).dt.to_period("M").astype(str)
    complete_holding = complete.groupby(["policy_id", "split"])["avg_holding_days"].mean().to_dict()
    complete_turnover = complete.groupby(["policy_id", "split"]).size().to_dict()
    complete_turnover_month = complete.groupby(["policy_id", "split", "entry_month"]).size().to_dict() if not complete.empty else {}
    daily = daily.copy()
    daily["month"] = pd.to_datetime(daily["trade_date"]).dt.to_period("M").astype(str)
    for keys, part in daily.groupby(["portfolio_id", "portfolio_weighting_id", "daily_active_cap", "policy_id", "split"], sort=False, dropna=False):
        portfolio_id, weighting_id, cap, policy_id, split = keys
        returns = pd.to_numeric(part["portfolio_daily_net_return"], errors="coerce").fillna(0.0)
        active_counts = pd.to_numeric(part["active_count"], errors="coerce").fillna(0)
        active_only = active_counts[active_counts > 0]
        period_return = float(np.prod(1.0 + returns) - 1.0) if len(returns) else np.nan
        ann_return = (1.0 + period_return) ** (252.0 / len(returns)) - 1.0 if len(returns) and period_return > -1 else np.nan
        ann_vol = float(returns.std(ddof=0) * np.sqrt(252.0)) if len(returns) else np.nan
        rows.append(
            {
                "split": split,
                "portfolio_id": portfolio_id,
                "portfolio_weighting_id": weighting_id,
                "daily_active_cap": cap,
                "policy_id": policy_id,
                "trading_day_count": int(len(part)),
                "active_day_count": int((active_counts > 0).sum()),
                "active_day_share": _safe_div(int((active_counts > 0).sum()), len(part)),
                "daily_return_mean": float(returns.mean()) if len(returns) else np.nan,
                "daily_return_median": _quantile(returns, 0.50),
                "daily_return_p10": _quantile(returns, 0.10),
                "daily_return_p25": _quantile(returns, 0.25),
                "daily_return_p75": _quantile(returns, 0.75),
                "daily_return_p90": _quantile(returns, 0.90),
                "period_compounded_return": period_return,
                "annualized_return": ann_return,
                "annualized_vol": ann_vol,
                "sharpe_like": _safe_div(float(returns.mean() * 252.0), ann_vol),
                "max_drawdown": _max_drawdown_positive(returns),
                "worst_20d_return": _rolling_return(returns, 20, "min"),
                "best_20d_return": _rolling_return(returns, 20, "max"),
                "active_count_mean": float(active_only.mean()) if len(active_only) else 0.0,
                "active_count_p50": _quantile(active_only, 0.50),
                "active_count_p90": _quantile(active_only, 0.90),
                "active_count_p95": _quantile(active_only, 0.95),
                "active_count_p99": _quantile(active_only, 0.99),
                "turnover_event_count": int(complete_turnover.get((policy_id, split), 0)),
                "avg_holding_days": float(complete_holding.get((policy_id, split), np.nan)),
                "portfolio_denominator_status": "sufficient" if int((active_counts > 0).sum()) >= 60 else "insufficient_active_days",
            }
        )
        for month, mpart in part.groupby("month", sort=False):
            mreturns = pd.to_numeric(mpart["portfolio_daily_net_return"], errors="coerce").fillna(0.0)
            monthly_rows.append(
                {
                    "split": split,
                    "portfolio_id": portfolio_id,
                    "portfolio_weighting_id": weighting_id,
                    "daily_active_cap": cap,
                    "policy_id": policy_id,
                    "month": month,
                    "monthly_compounded_return": float(np.prod(1.0 + mreturns) - 1.0),
                    "active_day_share": _safe_div(int((mpart["active_count"] > 0).sum()), len(mpart)),
                    "active_count_mean": float(pd.to_numeric(mpart["active_count"], errors="coerce").mean()) if len(mpart) else np.nan,
                    "turnover_event_count": int(complete_turnover_month.get((policy_id, split, month), 0)),
                }
            )
    summary = pd.DataFrame(rows)
    monthly = pd.DataFrame(monthly_rows)
    monthly_stats = []
    for keys, part in monthly.groupby(["split", "portfolio_id", "portfolio_weighting_id", "daily_active_cap", "policy_id"], sort=False, dropna=False):
        returns = pd.to_numeric(part["monthly_compounded_return"], errors="coerce")
        worst_idx = returns.idxmin() if len(returns.dropna()) else None
        monthly_stats.append(
            {
                **dict(zip(["split", "portfolio_id", "portfolio_weighting_id", "daily_active_cap", "policy_id"], keys)),
                "monthly_count": int(len(part)),
                "monthly_return_mean": float(returns.mean()) if len(returns.dropna()) else np.nan,
                "monthly_return_median": _quantile(returns, 0.50),
                "monthly_return_p10": _quantile(returns, 0.10),
                "monthly_return_min": float(returns.min()) if len(returns.dropna()) else np.nan,
                "positive_month_rate": float((returns > 0).mean()) if len(returns.dropna()) else np.nan,
                "worst_month": "" if worst_idx is None else str(part.loc[worst_idx, "month"]),
                "worst_month_return": np.nan if worst_idx is None else float(part.loc[worst_idx, "monthly_compounded_return"]),
            }
        )
    monthly_summary = pd.DataFrame(monthly_stats)
    summary = summary.merge(monthly_summary, on=["split", "portfolio_id", "portfolio_weighting_id", "daily_active_cap", "policy_id"], how="left")
    monthly = monthly.merge(monthly_summary, on=["split", "portfolio_id", "portfolio_weighting_id", "daily_active_cap", "policy_id"], how="left")
    return summary, monthly


def _family_contribution(weighted_family_parts: pd.DataFrame, replay: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
    if weighted_family_parts.empty:
        return pd.DataFrame()
    fam = weighted_family_parts.copy()
    fam["daily_return_contribution"] = fam["daily_net_return"] * fam["family_part_weight"]
    daily_total = fam.groupby(["split", "portfolio_id", "policy_id", "trade_date"], as_index=False)["daily_return_contribution"].sum().rename(columns={"daily_return_contribution": "portfolio_daily_return"})
    fam = fam.merge(daily_total, on=["split", "portfolio_id", "policy_id", "trade_date"], how="left")
    rows = []
    group_cols = ["split", "portfolio_id", "policy_id", "source_family_id"]
    for keys, part in fam.groupby(group_cols, sort=False, dropna=False):
        rec = dict(zip(group_cols, keys))
        replay_part = replay[(replay["split"].eq(rec["split"])) & (replay["policy_id"].eq(rec["policy_id"])) & replay["source_family_set"].astype(str).str.contains(str(rec["source_family_id"]), regex=False)]
        rec.update(
            {
                "active_weight_share_mean": float(part.groupby("trade_date")["family_part_weight"].sum().mean()) if len(part) else np.nan,
                "event_count": int(replay_part["r04e_event_id"].nunique()),
                "daily_return_contribution_sum": float(part["daily_return_contribution"].sum()),
                "daily_return_contribution_mean": float(part["daily_return_contribution"].mean()) if len(part) else np.nan,
                "monthly_return_contribution_mean": np.nan,
                "loss_day_contribution_share": _safe_div(float(part.loc[part["portfolio_daily_return"] < 0, "daily_return_contribution"].sum()), float(daily_total.loc[daily_total["portfolio_daily_return"] < 0, "portfolio_daily_return"].sum())),
                "positive_day_contribution_share": _safe_div(float(part.loc[part["portfolio_daily_return"] > 0, "daily_return_contribution"].sum()), float(daily_total.loc[daily_total["portfolio_daily_return"] > 0, "portfolio_daily_return"].sum())),
                "max_gain50_event_count": int(_bool_series(replay_part["hold120_no_exit_max_gain50_flag"]).sum()) if not replay_part.empty else 0,
                "source_family_status": "additive_source_family",
            }
        )
        rows.append(rec)
    multi = replay[pd.to_numeric(replay["source_family_count"], errors="coerce") > 1].copy()
    for keys, part in multi.groupby(["split", "policy_id"], sort=False, dropna=False):
        split, policy_id = keys
        for portfolio_id in fam["portfolio_id"].dropna().unique():
            sub = fam[(fam["split"].eq(split)) & (fam["policy_id"].eq(policy_id)) & (fam["portfolio_id"].eq(portfolio_id)) & fam["r04e_event_id"].isin(part["r04e_event_id"])]
            rows.append(
                {
                    "split": split,
                    "portfolio_id": portfolio_id,
                    "policy_id": policy_id,
                    "source_family_id": "multi_family_collapsed",
                    "active_weight_share_mean": float(sub.groupby("trade_date")["family_part_weight"].sum().mean()) if len(sub) else 0.0,
                    "event_count": int(part["r04e_event_id"].nunique()),
                    "daily_return_contribution_sum": float(sub["daily_return_contribution"].sum()) if len(sub) else 0.0,
                    "daily_return_contribution_mean": float(sub["daily_return_contribution"].mean()) if len(sub) else np.nan,
                    "monthly_return_contribution_mean": np.nan,
                    "loss_day_contribution_share": np.nan,
                    "positive_day_contribution_share": np.nan,
                    "max_gain50_event_count": int(_bool_series(part["hold120_no_exit_max_gain50_flag"]).sum()),
                    "source_family_status": "non_additive_diagnostic_subset",
                }
            )
    return pd.DataFrame(rows)


def _baseline_comparison(union_summary: pd.DataFrame, baseline_summary: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["split", "portfolio_weighting_id", "daily_active_cap", "policy_id"]
    left = union_summary.copy()
    right = baseline_summary.copy()
    merged = left.merge(
        right[key_cols + ["period_compounded_return", "daily_return_mean", "monthly_return_p10", "max_drawdown", "worst_20d_return", "active_count_p95"]].rename(
            columns={
                "period_compounded_return": "baseline_A_period_compounded_return",
                "daily_return_mean": "baseline_A_daily_return_mean",
                "monthly_return_p10": "baseline_A_monthly_return_p10",
                "max_drawdown": "baseline_A_max_drawdown",
                "worst_20d_return": "baseline_A_worst_20d_return",
                "active_count_p95": "baseline_A_active_count_p95",
            }
        ),
        on=key_cols,
        how="left",
    )
    merged["portfolio_period_return_delta_vs_baseline_A"] = merged["period_compounded_return"] - merged["baseline_A_period_compounded_return"]
    merged["portfolio_daily_mean_delta_vs_baseline_A"] = merged["daily_return_mean"] - merged["baseline_A_daily_return_mean"]
    merged["portfolio_monthly_p10_delta_vs_baseline_A"] = merged["monthly_return_p10"] - merged["baseline_A_monthly_return_p10"]
    merged["portfolio_max_drawdown_delta_vs_baseline_A"] = merged["max_drawdown"] - merged["baseline_A_max_drawdown"]
    merged["portfolio_worst_20d_delta_vs_baseline_A"] = merged["worst_20d_return"] - merged["baseline_A_worst_20d_return"]
    merged["active_count_p95_delta_vs_baseline_A"] = merged["active_count_p95"] - merged["baseline_A_active_count_p95"]
    return merged


def _select_portfolio_policy(comparison: pd.DataFrame, event_summary: pd.DataFrame, gate0: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    thresholds = config["thresholds"]
    gate0_row = gate0.iloc[0].to_dict() if not gate0.empty else {"gate0_status": "gate0_blocked_insufficient_inputs", "gate0_stop_category": "input_or_comparator_failure"}
    gate0_ok = gate0_row["gate0_status"] in {"gate0_strong_go", "gate0_conditional_go"}
    validation = comparison[
        comparison["split"].eq("validation")
        & comparison["portfolio_id"].isin(["active_equal_weight_uncapped", "family_balanced_active_equal_weight_uncapped"])
        & comparison["daily_active_cap"].astype(str).eq("none")
    ].copy()
    event_val = event_summary[event_summary["split"].eq("validation") & event_summary["pool_id"].eq(config["union_pool"]["union_pool_id"])][
        ["policy_id", "policy_max_gain50_retention_rate_vs_hold120_no_exit"]
    ]
    validation = validation.merge(event_val, on="policy_id", how="left")
    rows: list[dict[str, Any]] = []
    for idx, row in validation.iterrows():
        strong_gates = {
            "gate0_status": gate0_ok,
            "period_compounded_return": row["period_compounded_return"] > 0,
            "daily_return_mean": row["daily_return_mean"] > 0,
            "monthly_return_p10": row["monthly_return_p10"] >= thresholds["validation_monthly_p10_min"],
            "max_drawdown_delta": row["portfolio_max_drawdown_delta_vs_baseline_A"] <= 0,
            "monthly_p10_delta": row["portfolio_monthly_p10_delta_vs_baseline_A"] >= 0,
            "right_tail_retention": row["policy_max_gain50_retention_rate_vs_hold120_no_exit"] >= thresholds["validation_strong_retention_min"],
            "active_day_share": row["active_day_share"] >= thresholds["validation_active_day_share_min"],
            "active_count_p95": row["active_count_p95"] <= thresholds["validation_uncapped_active_count_p95_max"],
        }
        conditional_gates = {
            "gate0_status": gate0_ok,
            "period_compounded_return": row["period_compounded_return"] > 0,
            "daily_return_mean": row["daily_return_mean"] > 0,
            "monthly_p10_delta": row["portfolio_monthly_p10_delta_vs_baseline_A"] >= 0,
            "max_drawdown_delta": row["portfolio_max_drawdown_delta_vs_baseline_A"] <= 0,
            "right_tail_retention": row["policy_max_gain50_retention_rate_vs_hold120_no_exit"] >= thresholds["validation_conditional_retention_min"],
        }
        strong = all(strong_gates.values())
        conditional = all(conditional_gates.values())
        status = "validation_portfolio_strong_pass" if strong else ("validation_portfolio_conditional_pass" if conditional else "validation_portfolio_failed")
        validation.loc[idx, "validation_portfolio_gate_status"] = status
        validation.loc[idx, "validation_gate_failed_list"] = ";".join([name for name, passed in (strong_gates if not strong else {}).items() if not passed]) if not strong else ""
        rows.append(
            {
                "split": "validation",
                "gate0_status": gate0_row["gate0_status"],
                "gate0_stop_category": gate0_row["gate0_stop_category"],
                "portfolio_id": row["portfolio_id"],
                "policy_id": row["policy_id"],
                "validation_portfolio_gate_status": status,
                "failed_gate_list": validation.loc[idx, "validation_gate_failed_list"],
                "period_compounded_return": row["period_compounded_return"],
                "monthly_return_p10": row["monthly_return_p10"],
                "portfolio_monthly_p10_delta_vs_baseline_A": row["portfolio_monthly_p10_delta_vs_baseline_A"],
                "max_drawdown": row["max_drawdown"],
                "portfolio_max_drawdown_delta_vs_baseline_A": row["portfolio_max_drawdown_delta_vs_baseline_A"],
                "active_count_p95": row["active_count_p95"],
                "policy_max_gain50_retention_rate_vs_hold120_no_exit": row["policy_max_gain50_retention_rate_vs_hold120_no_exit"],
            }
        )
    passing = validation[validation["validation_portfolio_gate_status"].isin(["validation_portfolio_strong_pass", "validation_portfolio_conditional_pass"])].copy()
    selected = pd.DataFrame()
    if not passing.empty:
        passing["_strength_rank"] = np.where(passing["validation_portfolio_gate_status"].eq("validation_portfolio_strong_pass"), 1, 0)
        passing["_portfolio_pref"] = np.where(passing["portfolio_id"].eq("family_balanced_active_equal_weight_uncapped"), 1, 0)
        selected = passing.sort_values(
            ["_strength_rank", "_portfolio_pref", "monthly_return_p10", "max_drawdown", "period_compounded_return", "avg_holding_days"],
            ascending=[False, False, False, True, False, True],
        ).head(1)
    if not selected.empty:
        selected_key = (selected.iloc[0]["portfolio_id"], selected.iloc[0]["policy_id"])
        validation["selected_flag"] = validation.apply(lambda r: (r["portfolio_id"], r["policy_id"]) == selected_key, axis=1)
    else:
        validation["selected_flag"] = False
    gate = pd.concat([gate0, pd.DataFrame(rows)], ignore_index=True, sort=False)
    return validation, gate, selected


def _robustness_readout(selected: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    portfolio_id = selected.iloc[0]["portfolio_id"]
    policy_id = selected.iloc[0]["policy_id"]
    robust = comparison[
        comparison["split"].eq("robustness")
        & comparison["portfolio_id"].eq(portfolio_id)
        & comparison["policy_id"].eq(policy_id)
    ].copy()
    if robust.empty:
        return pd.DataFrame(
            [
                {
                    "split": "robustness",
                    "portfolio_id": portfolio_id,
                    "policy_id": policy_id,
                    "robustness_status": "robustness_failed",
                    "failed_gate_list": "missing_robustness_readout",
                }
            ]
        )
    row = robust.iloc[0]
    confirmed = (
        row["period_compounded_return"] > 0
        and row["daily_return_mean"] > 0
        and row["portfolio_monthly_p10_delta_vs_baseline_A"] >= 0
        and row["portfolio_max_drawdown_delta_vs_baseline_A"] <= 0
    )
    mixed = row["period_compounded_return"] > 0 and row["daily_return_mean"] > 0 and not confirmed
    status = "robustness_confirmed" if confirmed else ("robustness_mixed" if mixed else "robustness_failed")
    robust["robustness_status"] = status
    robust["failed_gate_list"] = "" if confirmed else ";".join(
        [
            name
            for name, passed in {
                "period_compounded_return": row["period_compounded_return"] > 0,
                "daily_return_mean": row["daily_return_mean"] > 0,
                "monthly_p10_delta": row["portfolio_monthly_p10_delta_vs_baseline_A"] >= 0,
                "max_drawdown_delta": row["portfolio_max_drawdown_delta_vs_baseline_A"] <= 0,
            }.items()
            if not passed
        ]
    )
    return robust


def _final_decision(gate0: pd.DataFrame, selected: pd.DataFrame, robustness: pd.DataFrame) -> tuple[str, str]:
    gate0_row = gate0.iloc[0].to_dict() if not gate0.empty else {"gate0_stop_category": "input_or_comparator_failure"}
    if selected.empty:
        if gate0_row.get("gate0_stop_category") == "input_or_comparator_failure":
            return "r04e_union_not_viable_validation", "gate0 input/comparator failure"
        if gate0_row.get("gate0_stop_category") == "weak_absolute_but_left_tail_improved":
            return "r04e_long_only_validation_ceiling_suspected", "absolute validation weak but matched left-tail improved"
        return "r04e_union_not_viable_validation", "no validation portfolio pass"
    validation_status = str(selected.iloc[0]["validation_portfolio_gate_status"])
    robust_status = "robustness_failed" if robustness.empty else str(robustness.iloc[0]["robustness_status"])
    if validation_status == "validation_portfolio_conditional_pass" and robust_status in {"robustness_confirmed", "robustness_mixed"}:
        return "r04e_union_portfolio_conditional_lead", robust_status
    if validation_status == "validation_portfolio_strong_pass" and robust_status == "robustness_confirmed":
        return "r04e_union_portfolio_strong_lead", robust_status
    if validation_status == "validation_portfolio_strong_pass" and robust_status == "robustness_mixed":
        return "r04e_union_validation_positive_but_robustness_mixed", robust_status
    return "r04e_union_validation_positive_but_robustness_failed", robust_status


def _fmt_pct(value: Any) -> str:
    if pd.isna(value):
        return "NA"
    return f"{float(value):+.2%}"


def _report_text(
    final: pd.DataFrame,
    overlap: pd.DataFrame,
    pseudo: pd.DataFrame,
    readiness: pd.DataFrame,
    comparison: pd.DataFrame,
    validation_gate: pd.DataFrame,
    robustness: pd.DataFrame,
    family: pd.DataFrame,
    daily_counts: pd.DataFrame,
    config: dict[str, Any],
) -> str:
    final_row = final.iloc[0].to_dict()
    union_pool = config["union_pool"]["union_pool_id"]
    hold = readiness[readiness["split"].eq("validation")]
    hold_row = hold.iloc[0].to_dict() if not hold.empty else {}
    primary = comparison[
        comparison["split"].eq("validation")
        & comparison["portfolio_id"].isin(["active_equal_weight_uncapped", "family_balanced_active_equal_weight_uncapped"])
        & comparison["daily_active_cap"].astype(str).eq("none")
    ].copy()
    best_by_port = primary.sort_values("period_compounded_return", ascending=False).groupby("portfolio_id").head(1)
    pseudo_val = pseudo[(pseudo["split"].eq("validation")) & (pseudo["pool_id"].eq(union_pool))]
    pseudo_row = pseudo_val.iloc[0].to_dict() if not pseudo_val.empty else {}
    fam_val = family[family["split"].eq("validation")].copy() if not family.empty else pd.DataFrame()
    lines = [
        "# R04e union pool portfolio-level diagnostic 最终报告",
        "",
        "R04e uses R04c failed descriptive leads as a frozen union diagnostic.",
        "R04e does not reinterpret any R04c pool as having passed validation.",
        "R04e does not reinterpret R04d as a policy pass.",
        "R04c final decision remains r04c_no_candidate_pool_passed_validation.",
        "R04d final decision remains r04d_no_policy_passed_validation.",
        "diagnostic only; no production entry rule is emitted; upstream pools were selected after prior OOS descriptive review.",
        "",
        "## 1. 最终结论",
        "",
        f"- final_decision: `{final_row.get('final_decision', '')}`",
        f"- selected_portfolio_policy_id: `{final_row.get('selected_portfolio_policy_id', '')}`",
        f"- gate0_status: `{final_row.get('gate0_status', '')}`",
        f"- gate0_stop_category: `{final_row.get('gate0_stop_category', '')}`",
        f"- decision_reason: {final_row.get('decision_reason', '')}",
        "",
        "R04e 不改变 R04c/R04d 的失败结论；这里只判断三个 descriptive relative-improvement pools 的冻结 union 是否在组合层有新线索。",
        "",
        "## 2. Source overlap",
        "",
        "| split | pool_a | pool_b | count_a | count_b | intersection | jaccard | status |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in overlap.sort_values(["split", "source_pool_id_a", "source_pool_id_b"]).itertuples(index=False):
        lines.append(f"| {row.split} | `{row.source_pool_id_a}` | `{row.source_pool_id_b}` | {row.event_count_a:,} | {row.event_count_b:,} | {row.intersection_event_count:,} | {row.jaccard:.2%} | {row.overlap_status} |")
    lines += [
        "",
        "## 3. Union 分散性",
        "",
        f"Validation union pseudo_diversification_status=`{pseudo_row.get('pseudo_diversification_status', 'NA')}`，top1 instrument={_fmt_pct(pseudo_row.get('top1_instrument_share', np.nan))}，top5 instrument={_fmt_pct(pseudo_row.get('top5_instrument_share', np.nan))}，top1 industry={_fmt_pct(pseudo_row.get('top1_industry_share', np.nan))}，same-instrument 20d cluster={_fmt_pct(pseudo_row.get('same_instrument_20d_cluster_share', np.nan))}，daily candidate p99={pseudo_row.get('daily_candidate_count_p99', 'NA')}.",
        "",
        "## 4. Gate 0 hold120 no-exit",
        "",
        f"Validation hold120 no-exit net={_fmt_pct(hold_row.get('net_return_mean', np.nan))}，matched delta={_fmt_pct(hold_row.get('net_return_mean_delta_vs_matched_baseline_A', np.nan))}，p10 delta={_fmt_pct(hold_row.get('p10_delta_vs_matched_baseline_A', np.nan))}，loss<=-5 delta={_fmt_pct(hold_row.get('loss_le_minus5_delta_vs_matched_baseline_A', np.nan))}，readiness=`{hold_row.get('readiness_status', 'NA')}`.",
        "",
        "## 5. Portfolio validation",
        "",
        "Right-tail validation gates use `policy_max_gain50_retention_rate_vs_hold120_no_exit`, not raw `max_gain50_rate`.",
        "",
        "| portfolio | best_policy | period | daily_mean | monthly_p10 | m_p10_delta | max_dd | dd_delta | active_p95 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in best_by_port.itertuples(index=False):
        lines.append(
            f"| `{row.portfolio_id}` | `{row.policy_id}` | {_fmt_pct(row.period_compounded_return)} | {_fmt_pct(row.daily_return_mean)} | "
            f"{_fmt_pct(row.monthly_return_p10)} | {_fmt_pct(row.portfolio_monthly_p10_delta_vs_baseline_A)} | {_fmt_pct(row.max_drawdown)} | "
            f"{_fmt_pct(row.portfolio_max_drawdown_delta_vs_baseline_A)} | {row.active_count_p95:.1f} |"
        )
    lines += [
        "",
        "active_equal_weight 与 family_balanced 的优劣以 uncapped validation period return、monthly p10、drawdown delta 为主；active cap 只是容量敏感性，不能救回 primary gate。",
        "",
        "## 6. Event alpha vs portfolio aggregation",
        "",
        f"Event-level union hold120 validation net={_fmt_pct(hold_row.get('net_return_mean', np.nan))}。若 portfolio period return 优于 event net，主要解释应是组合层 calendar aggregation 和分散，而不是单事件均值已经转正。",
        "",
        "## 7. Family contribution",
        "",
        "| portfolio | policy | family | weight_share | contribution_sum | loss_share | positive_share | max_gain50_events |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in fam_val.sort_values(["portfolio_id", "policy_id", "source_family_id"]).head(40).itertuples(index=False):
        lines.append(
            f"| `{row.portfolio_id}` | `{row.policy_id}` | {row.source_family_id} | {_fmt_pct(row.active_weight_share_mean)} | "
            f"{_fmt_pct(row.daily_return_contribution_sum)} | {_fmt_pct(row.loss_day_contribution_share)} | {_fmt_pct(row.positive_day_contribution_share)} | {int(row.max_gain50_event_count)} |"
        )
    cap = comparison[comparison["split"].eq("validation") & comparison["portfolio_id"].astype(str).str.contains("cap")].copy()
    cap_best = cap.sort_values("period_compounded_return", ascending=False).head(5)
    lines += [
        "",
        "## 8. Active cap sensitivity",
        "",
        f"Validation daily candidate count max={int(daily_counts[daily_counts['pool_id'].eq(union_pool)]['daily_candidate_count'].max()) if not daily_counts.empty else 0}；active cap sensitivity 的最好结果如下，但不参与 primary selection。",
        "",
        "| portfolio | policy | period | monthly_p10_delta | dd_delta |",
        "|---|---|---:|---:|---:|",
    ]
    for row in cap_best.itertuples(index=False):
        lines.append(f"| `{row.portfolio_id}` | `{row.policy_id}` | {_fmt_pct(row.period_compounded_return)} | {_fmt_pct(row.portfolio_monthly_p10_delta_vs_baseline_A)} | {_fmt_pct(row.portfolio_max_drawdown_delta_vs_baseline_A)} |")
    robust_status = "NA" if robustness.empty else robustness.iloc[0].get("robustness_status", "NA")
    lines += [
        "",
        "## 9. 后续判断",
        "",
        f"Robustness readout=`{robust_status}`。如果 validation 仍失败或只体现少亏，当前证据更支持 `long_only_validation_ceiling_suspected` / `union_not_viable`，后续应优先问 portfolio sleeve、market-state cash sleeve 或 split/regime 问题，而不是回到 R04d v2 的单池 exit 参数扩展。",
        "",
    ]
    return "\n".join(lines)


def _portfolio_ids(weighting: str, cap: int | None) -> str:
    suffix = "uncapped" if cap is None else f"cap{int(cap)}"
    return f"{weighting}_{suffix}"


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for directory in [cache_dir, reports_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    r04c_events, _r04c_matched, _r04c_profile, _r04c_registry, state, block_reason = _load_required_inputs(config)
    write_csv(_upstream_state_audit(state, block_reason), reports_dir / "r04e_upstream_state_audit.csv")
    if block_reason:
        decision = "r04e_blocked_missing_required_input" if block_reason.startswith("missing:") else ("r04e_blocked_upstream_validation_failed" if block_reason == "upstream_validation_failed" else "r04e_blocked_upstream_state_changed")
        final = pd.DataFrame([{"final_decision": decision, "decision_reason": block_reason}])
        write_csv(final, reports_dir / "r04e_final_decision.csv")
        manifest = {
            "phase": config["phase"],
            "requirement_id": config["requirement_id"],
            "final_decision": decision,
            "output_root": relpath(output_root),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(manifest, manifests_dir / "r04e_union_pool_portfolio_level_manifest.json")
        return manifest

    calendar = _load_calendar(config["price_provider"]["calendar_source_path"])
    source_raw = _collapse_source_pools(config, calendar)
    baseline = _baseline_events(r04c_events, config)
    instruments = sorted(set(source_raw["instrument_id"].astype(str).str.upper()) | set(baseline["instrument_id"].astype(str).str.upper()))
    start, end = _price_bounds(config, calendar)
    print(f"loading price panel for {len(instruments)} instruments from {start.date()} to {end.date()}", flush=True)
    price = _load_price_panel(config, instruments, start, end, calendar)
    price_index = _price_by_inst(price)

    source = _prepare_source_events(source_raw, r04c_events, price, calendar, config)
    union = _build_union_events(source, config)
    recon = _source_reconciliation(source, r04c_events, config)
    nearby = _same_instrument_nearby_audit(union, source, config)
    overlap = _event_overlap_audit(source, config)
    daily_counts = _daily_candidate_count_audit(source, union)
    matched_panel, matched_audit = _matched_baseline_reconstruction(union, baseline, config)

    policy_matrix = _build_policy_matrix(config)
    print(f"replaying source={len(source):,}, union={len(union):,}, baseline={len(baseline):,} events x {len(policy_matrix):,} policies", flush=True)
    source_replay, _ = _replay_events(source.assign(replay_universe="source_pool", r04e_event_id="source|" + source["source_pool_event_id"].astype(str), event_weight=1.0, cap_rank_key=source.apply(lambda r: _stable_key(r["instrument_id"], _date_str(r["entry_execution_date"]), r["source_pool_event_id"]), axis=1)), policy_matrix, price_index, config, "source")
    union_replay, union_cache = _replay_events(union, policy_matrix, price_index, config, "union")
    baseline_replay, baseline_cache = _replay_events(baseline, policy_matrix, price_index, config, "baseline_A")
    matched_replay = _matched_replay_from_baseline(baseline_replay, matched_panel)
    matched_policy_summary = _matched_summary(matched_replay, config)
    combined_event_replay = pd.concat([source_replay, union_replay], ignore_index=True, sort=False)
    event_summary = _summarize_event_replay(combined_event_replay, matched_policy_summary, config)
    hold120_replay = combined_event_replay[combined_event_replay["policy_id"].eq(config["baseline"]["hold120_no_exit_policy_id"])].copy()
    pseudo = _pseudo_diversification_audit(source, union, hold120_replay, daily_counts, config)
    readiness = _hold120_readiness(event_summary, pseudo, config)
    gate0 = _gate0_audit(readiness)

    calendar_frame = _split_calendar(calendar, config)
    union_daily_frames: list[pd.DataFrame] = []
    baseline_daily_frames: list[pd.DataFrame] = []
    family_contrib_frames: list[pd.DataFrame] = []
    path_appender = _ParquetAppender(cache_dir / "r04e_event_policy_path_panel.parquet")
    caps: list[int | None] = [None] + [int(x) for x in config["portfolio_weighting"]["daily_active_cap"]["sensitivity"]]
    try:
        for policy_id in policy_matrix["policy_id"]:
            union_policy = union_replay[union_replay["policy_id"].eq(policy_id)].copy()
            baseline_policy = baseline_replay[baseline_replay["policy_id"].eq(policy_id)].copy()
            union_path = _event_daily_path(union_policy, union_cache, config)
            baseline_path = _event_daily_path(baseline_policy, baseline_cache, config)
            path_appender.append(union_path)
            for weighting in config["portfolio_weighting"]["primary"]:
                for cap in caps:
                    portfolio_id = _portfolio_ids(weighting, cap)
                    u_daily, u_fam = _portfolio_daily_from_path(union_path, weighting, cap, calendar_frame, portfolio_id, policy_id)
                    b_daily, _ = _portfolio_daily_from_path(baseline_path, weighting, cap, calendar_frame, portfolio_id, policy_id)
                    union_daily_frames.append(u_daily)
                    baseline_daily_frames.append(b_daily)
                    if cap is None and not u_fam.empty:
                        family_contrib_frames.append(_family_contribution(u_fam, union_policy, pd.DataFrame()))
            print(f"built portfolio daily path for {policy_id}", flush=True)
    finally:
        path_appender.close()
    if not (cache_dir / "r04e_event_policy_path_panel.parquet").exists():
        _write_parquet(pd.DataFrame(columns=["r04e_event_id", "policy_id", "split", "trade_date", "daily_net_return"]), cache_dir / "r04e_event_policy_path_panel.parquet")

    union_daily = pd.concat(union_daily_frames, ignore_index=True, sort=False)
    baseline_daily = pd.concat(baseline_daily_frames, ignore_index=True, sort=False)
    union_portfolio_summary, union_monthly = _portfolio_summaries(union_daily, union_replay, config)
    baseline_portfolio_summary, baseline_monthly = _portfolio_summaries(baseline_daily, baseline_replay, config)
    comparison = _baseline_comparison(union_portfolio_summary, baseline_portfolio_summary)
    family_contrib = pd.concat(family_contrib_frames, ignore_index=True, sort=False) if family_contrib_frames else pd.DataFrame()
    validation_gate, gate_audit, selected = _select_portfolio_policy(comparison, event_summary, gate0, config)
    robustness = _robustness_readout(selected, comparison)
    final_decision, decision_reason = _final_decision(gate0, selected, robustness)
    selected_policy = "" if selected.empty else str(selected.iloc[0]["policy_id"])
    selected_portfolio = "" if selected.empty else str(selected.iloc[0]["portfolio_id"])
    selected_portfolio_policy = "" if selected.empty else f"{selected_portfolio}|{selected_policy}"
    final = pd.DataFrame(
        [
            {
                "final_decision": final_decision,
                "selected_portfolio_policy_id": selected_portfolio_policy,
                "selected_portfolio_id": selected_portfolio,
                "selected_policy_id": selected_policy,
                "validation_portfolio_gate_status": "" if selected.empty else selected.iloc[0]["validation_portfolio_gate_status"],
                "robustness_status": "" if robustness.empty else robustness.iloc[0].get("robustness_status", ""),
                "gate0_status": gate0.iloc[0]["gate0_status"] if not gate0.empty else "",
                "gate0_stop_category": gate0.iloc[0]["gate0_stop_category"] if not gate0.empty else "",
                "decision_reason": decision_reason,
            }
        ]
    )

    write_csv(recon, reports_dir / "r04e_source_pool_reconciliation.csv")
    write_csv(overlap, reports_dir / "r04e_union_event_overlap_audit.csv")
    write_csv(nearby, reports_dir / "r04e_same_instrument_nearby_event_audit.csv")
    write_csv(pseudo, reports_dir / "r04e_pseudo_diversification_audit.csv")
    write_csv(daily_counts, reports_dir / "r04e_daily_candidate_count_audit.csv")
    write_csv(readiness, reports_dir / "r04e_union_hold120_readiness.csv")
    write_csv(policy_matrix, reports_dir / "r04e_policy_matrix_frozen.csv")
    write_csv(event_summary, reports_dir / "r04e_event_policy_replay_summary.csv")
    write_csv(comparison, reports_dir / "r04e_portfolio_policy_summary.csv")
    write_csv(union_monthly, reports_dir / "r04e_portfolio_monthly_summary.csv")
    write_csv(family_contrib, reports_dir / "r04e_family_contribution_decomposition.csv")
    write_csv(comparison, reports_dir / "r04e_baseline_A_portfolio_comparison.csv")
    write_csv(matched_audit, reports_dir / "r04e_matched_baseline_reconstruction_audit.csv")
    write_csv(gate_audit, reports_dir / "r04e_gate_audit.csv")
    write_csv(final, reports_dir / "r04e_final_decision.csv")
    report = _report_text(final, overlap, pseudo, readiness, comparison, validation_gate, robustness, family_contrib, daily_counts, config)
    (reports_dir / "r04e_union_pool_portfolio_level_final_report.md").write_text(report, encoding="utf-8")

    _write_parquet(source, cache_dir / "r04e_source_pool_event_panel.parquet")
    _write_parquet(union, cache_dir / "r04e_union_event_panel.parquet")
    _write_parquet(union_daily, cache_dir / "r04e_portfolio_daily_return_panel.parquet")
    _write_parquet(baseline_daily, cache_dir / "r04e_baseline_A_portfolio_daily_return_panel.parquet")
    _write_parquet(matched_replay, cache_dir / "r04e_matched_baseline_event_replay_panel.parquet")

    artifacts = (
        list(cache_dir.glob("*.parquet"))
        + list(reports_dir.glob("*.csv"))
        + [reports_dir / "r04e_union_pool_portfolio_level_final_report.md"]
    )
    runner_hash = _hash_file(Path(__file__).resolve())
    validator_path = EP4_DIR / "scripts" / "validate_r04e_union_pool_portfolio_level_diagnostic.py"
    manifest = {
        "phase": config["phase"],
        "requirement_id": config["requirement_id"],
        "config_path": relpath(topic_path(config_path)),
        "config_hash": _hash_file(topic_path(config_path)),
        "runner_hash": runner_hash,
        "validator_hash": _hash_file(validator_path) if validator_path.exists() else "",
        "upstream_r04c_manifest_hash": _hash_file(topic_path(config["upstream_r04c"]["manifest"])),
        "upstream_r04d_manifest_hash": _hash_file(topic_path(config["upstream_r04d"]["manifest"])),
        "upstream_r04b_manifest_hash": _hash_file(topic_path(config["upstream_r04b"]["manifest"])),
        "r02_family_action_time_panel_hash": _hash_file(topic_path(config["upstream_r02_family_precision"]["action_time_panel"])),
        "price_provider_hash": _price_source_hash(config, instruments),
        "cost_model_id": config["cost_model"]["cost_model_id"],
        "source_pool_ids": config["union_pool"]["source_pool_ids"],
        "union_pool_id": config["union_pool"]["union_pool_id"],
        "policy_matrix_hash": _hash_file(reports_dir / "r04e_policy_matrix_frozen.csv"),
        "portfolio_weighting_matrix_hash": _hash_text(_canonical_json(config["portfolio_weighting"])),
        "split_definition_hash": _hash_text(_canonical_json(config["split"])),
        "final_decision": final_decision,
        "selected_portfolio_policy_id": selected_portfolio_policy,
        "gate0_status": gate0.iloc[0]["gate0_status"] if not gate0.empty else "",
        "gate0_stop_category": gate0.iloc[0]["gate0_stop_category"] if not gate0.empty else "",
        "output_root": relpath(output_root),
        "artifact_hashes": _artifact_hashes(artifacts),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(manifest, manifests_dir / "r04e_union_pool_portfolio_level_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    manifest = run(args.config)
    print(json.dumps({"final_decision": manifest.get("final_decision"), "selected_portfolio_policy_id": manifest.get("selected_portfolio_policy_id")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

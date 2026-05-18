#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
    _load_calendar,
    _load_price_panel,
    _price_source_hash,
)


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04c_candidate_pool_scanner_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
FINAL_DECISIONS = {
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_price_materialization_mismatch",
    "blocked_pool_definition_invalid",
    "blocked_selection_leakage_detected",
    "r04c_no_candidate_pool_passed_validation",
    "r04c_candidate_pool_not_robust_scanner_complete",
    "r04c_candidate_pool_passed_diagnostic_only",
}
PROMOTABLE_ADAPTERS = {
    "r04_deterministic_auxiliary",
    "r02_family_precision_frozen_family_occurrence",
    "r03c_config_frozen_family_set_pool",
}
CONTROL_POOLS = {
    "baseline_A_r04_included_rps_episode_first_trigger",
    "baseline_A_matched_background",
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


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")


def _safe_div(numerator: float, denominator: float) -> float:
    if not np.isfinite(denominator) or denominator == 0:
        return np.nan
    if not np.isfinite(numerator):
        return np.nan
    return float(numerator) / float(denominator)


def _to_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _bool_series(values: pd.Series) -> pd.Series:
    return values.map(_to_bool).astype(bool)


def _date(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(ts) else ts.date().isoformat()


def _quantile(values: pd.Series, q: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.quantile(q)) if len(clean) else np.nan


def _weighted_quantile(values: pd.Series, weights: pd.Series, q: float) -> float:
    data = pd.DataFrame({"value": pd.to_numeric(values, errors="coerce"), "weight": pd.to_numeric(weights, errors="coerce")})
    data = data[(data["value"].notna()) & (data["weight"].notna()) & (data["weight"] > 0)].sort_values("value")
    if data.empty:
        return np.nan
    cutoff = q * data["weight"].sum()
    cumsum = data["weight"].cumsum()
    return float(data.loc[cumsum >= cutoff, "value"].iloc[0])


def _split_bounds(config: dict[str, Any]) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    split = config["split"]
    return {
        "train": (pd.Timestamp(split["train_start"]), pd.Timestamp(split["train_end"])),
        "validation": (pd.Timestamp(split["validation_start"]), pd.Timestamp(split["validation_end"])),
        "robustness": (pd.Timestamp(split["robustness_start"]), pd.Timestamp(split["robustness_end"])),
    }


def _split_for_date(value: Any, bounds: dict[str, tuple[pd.Timestamp, pd.Timestamp]]) -> str:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return "out_of_scope"
    dt = dt.normalize()
    for split, (start, end) in bounds.items():
        if start <= dt <= end:
            return split
    return "out_of_scope"


def _calendar_map(calendar: pd.DatetimeIndex) -> dict[pd.Timestamp, int]:
    return {pd.Timestamp(date): idx for idx, date in enumerate(calendar)}


def _load_instruments(path: str | Path) -> list[str]:
    resolved = topic_path(path)
    instruments: list[str] = []
    for line in resolved.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if parts:
            instruments.append(parts[0].upper())
    return sorted(set(instruments))


def _source_readiness(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for source_id, src in config["source_registry"].items():
        root = topic_path(src["source_root"])
        required = src.get("required_artifacts", [])
        present = True
        artifact_paths: list[Path] = []
        missing: list[str] = []
        for rel in required:
            if "*" in rel:
                matches = sorted(root.glob(rel))
                if matches:
                    artifact_paths.extend(matches)
                else:
                    present = False
                    missing.append(str(root / rel))
            else:
                path = root / rel
                if path.exists():
                    artifact_paths.append(path)
                else:
                    present = False
                    missing.append(str(path))
        digest = hashlib.sha256()
        for path in sorted(artifact_paths):
            if path.is_file():
                digest.update(relpath(path).encode())
                digest.update(_hash_file(path).encode())
        rows.append(
            {
                "source_id": source_id,
                "source_root": src["source_root"],
                "required_artifacts_present": present,
                "source_validation_status": "not_applicable",
                "source_hash": digest.hexdigest() if artifact_paths else "",
                "adapter_id": src.get("adapter_id", ""),
                "source_promotability_default": src.get("source_promotability_default", ""),
                "source_readiness_status": "available" if present else "unavailable_missing_artifacts",
                "unavailable_reason": "" if present else "missing_required_artifacts: " + ";".join(missing),
            }
        )
    return pd.DataFrame(rows)


def _registry_row(
    pool_id: str,
    pool_family_id: str,
    pool_source_id: str,
    adapter_id: str,
    pool_type: str,
    anchor_col: str,
    membership_rule: dict[str, Any],
    source_path: str,
    source_hash: str,
    status: str = "promotable",
    leakage: str = "no_known_oos_leakage",
    invalid: str = "",
    selection_allowed: str = "train",
    field_source_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rule_text = json.dumps(membership_rule, sort_keys=True, ensure_ascii=True)
    field_map = field_source_map or {}
    return {
        "pool_id": pool_id,
        "pool_family_id": pool_family_id,
        "pool_source_id": pool_source_id,
        "adapter_id": adapter_id,
        "pool_source_artifact_path": source_path,
        "pool_source_artifact_hash": source_hash,
        "pool_type": pool_type,
        "anchor_type": "source_observable_signal_date",
        "anchor_signal_date_column": anchor_col,
        "instrument_column": "instrument_id",
        "membership_rule_text": rule_text,
        "membership_rule_json": rule_text,
        "membership_rule_hash": _hash_json(membership_rule),
        "field_source_map_hash": _hash_json(field_map),
        "episode_collapse_rule": "episode_gap_trading_days=20",
        "selection_stage_allowed": selection_allowed,
        "pool_promotability_status": status,
        "leakage_risk_class": leakage,
        "invalid_pool_reason": invalid,
    }


def _event_id(pool_id: str, instrument: Any, anchor: Any, source_id: Any = "") -> str:
    return _hash_text(f"{pool_id}|{instrument}|{_date(anchor)}|{source_id}")


def _build_regime_lookup(regime: pd.DataFrame) -> pd.DataFrame:
    cols = ["instrument_id", "anchor_signal_date", "market_regime_bucket", "industry_regime_bucket", "industry_target_key"]
    out = regime[cols].copy()
    out["instrument_id"] = out["instrument_id"].astype(str).str.upper()
    out["anchor_signal_date"] = pd.to_datetime(out["anchor_signal_date"]).dt.normalize()
    out = out.dropna(subset=["instrument_id", "anchor_signal_date"]).drop_duplicates(["instrument_id", "anchor_signal_date"])
    return out


def _base_events_from_r04b(config: dict[str, Any]) -> pd.DataFrame:
    base = pd.read_parquet(topic_path(config["upstream_r04b"]["candidate_replay_base_panel"]))
    keep = base["entry_valid_r04b"].map(_to_bool) & base["split"].astype(str).isin(SPLITS)
    base = base.loc[keep].copy()
    base["instrument_id"] = base["instrument_id"].astype(str).str.upper()
    for col in ["anchor_signal_date", "entry_execution_date"]:
        base[col] = pd.to_datetime(base[col]).dt.normalize()
    out = pd.DataFrame(
        {
            "pool_event_id": [_event_id("baseline_A_r04_included_rps_episode_first_trigger", r.instrument_id, r.anchor_signal_date, r.r04_candidate_event_id) for r in base.itertuples(index=False)],
            "source_event_id": base["r04_candidate_event_id"].astype(str),
            "pool_id": "baseline_A_r04_included_rps_episode_first_trigger",
            "pool_family_id": "control_baseline_A",
            "pool_source_id": "r04_baseline_A",
            "adapter_id": "control_baseline_A",
            "pool_promotability_status": "control_baseline",
            "instrument_id": base["instrument_id"],
            "anchor_signal_date": base["anchor_signal_date"],
            "source_split": base["split"].astype(str),
            "source_entry_execution_date": base["entry_execution_date"],
            "source_entry_price": pd.to_numeric(base["r04b_replay_entry_price"], errors="coerce"),
            "market_regime_bucket": base["market_regime_bucket"].fillna("missing_market_regime"),
            "industry_regime_bucket": base["industry_regime_bucket"].fillna("missing_industry"),
            "industry_target_key": base["industry_target_key"].fillna("missing_industry"),
            "stock_rps_60d": pd.to_numeric(base.get("stock_rps_60d"), errors="coerce"),
            "stock_rps_minus_industry_rps_60d": pd.to_numeric(base.get("stock_rps_minus_industry_rps_60d"), errors="coerce"),
        }
    )
    return out


def _load_full_price(config: dict[str, Any], calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, str]:
    instruments = _load_instruments(config["price_provider"]["instrument_source_path"])
    start = pd.Timestamp(config["split"]["train_start"])
    end = pd.Timestamp(calendar.max())
    price = _load_price_panel(config, instruments, start, end, calendar)
    source_hash = _price_source_hash(config, instruments)
    return price, source_hash


def _derive_rank_fields(config: dict[str, Any], price: pd.DataFrame) -> pd.DataFrame:
    work = price[["instrument_id", "trade_date", "calendar_index", "adjusted_close", "money"]].copy()
    work = work.sort_values(["instrument_id", "calendar_index"])
    work["money_mean_20d"] = work.groupby("instrument_id", sort=False)["money"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    work["money_rank_20d"] = work.groupby("trade_date")["money_mean_20d"].rank(pct=True, method="average")
    work["stock_ret_60d"] = work.groupby("instrument_id", sort=False)["adjusted_close"].pct_change(60)

    membership_path = topic_path(config["local_inputs"]["pit_industry_membership"])
    if not membership_path.exists():
        work["industry_rps_60d"] = np.nan
        return work[["instrument_id", "trade_date", "money_rank_20d", "industry_rps_60d"]]
    membership = pd.read_csv(membership_path, usecols=["date", "instrument", "industry_target_key"])
    membership = membership.rename(columns={"date": "trade_date", "instrument": "instrument_id"})
    membership["instrument_id"] = membership["instrument_id"].astype(str).str.upper()
    membership["trade_date"] = pd.to_datetime(membership["trade_date"]).dt.normalize()
    joined = work[["instrument_id", "trade_date", "stock_ret_60d"]].merge(membership, on=["instrument_id", "trade_date"], how="left")
    industry = (
        joined.dropna(subset=["industry_target_key", "stock_ret_60d"])
        .groupby(["trade_date", "industry_target_key"], as_index=False)
        .agg(industry_ret_60d=("stock_ret_60d", "mean"))
    )
    industry["industry_rps_60d"] = industry.groupby("trade_date")["industry_ret_60d"].rank(pct=True, method="average")
    joined = joined[["instrument_id", "trade_date", "industry_target_key"]].merge(
        industry[["trade_date", "industry_target_key", "industry_rps_60d"]],
        on=["trade_date", "industry_target_key"],
        how="left",
    )
    out = work[["instrument_id", "trade_date", "money_rank_20d"]].merge(
        joined[["instrument_id", "trade_date", "industry_rps_60d"]],
        on=["instrument_id", "trade_date"],
        how="left",
    )
    return out


def _r04_auxiliary_events(
    base: pd.DataFrame,
    rank_fields: pd.DataFrame,
    config: dict[str, Any],
    registry_rows: list[dict[str, Any]],
    waterfall: list[dict[str, Any]],
) -> pd.DataFrame:
    field_map = config["r04_derived_field_source_map"]
    source_path = config["upstream_r04"]["regime_join_panel"]
    source_hash = _hash_file(topic_path(source_path))
    work = base.copy()
    work = work.merge(
        rank_fields.rename(columns={"trade_date": "anchor_signal_date"}),
        on=["instrument_id", "anchor_signal_date"],
        how="left",
    )
    definitions = [
        ("r04_rps95", {"stock_rps_60d": [">=", 0.95]}),
        ("r04_rps95_money80", {"stock_rps_60d": [">=", 0.95], "money_rank_20d": [">=", 0.80]}),
        ("r04_rps95_industry80", {"stock_rps_60d": [">=", 0.95], "industry_rps_60d": [">=", 0.80]}),
        ("r04_rps95_industry_relative10", {"stock_rps_60d": [">=", 0.95], "stock_rps_minus_industry_rps_60d": [">=", 0.10]}),
    ]
    frames: list[pd.DataFrame] = []
    for pool_id, rule in definitions:
        required = list(rule.keys())
        missing = [col for col in required if col not in work.columns or work[col].notna().sum() == 0]
        status = "promotable" if not missing else "unavailable"
        invalid = "" if not missing else "missing_required_logical_field_after_resolution"
        registry_rows.append(
            _registry_row(
                pool_id,
                "r04_deterministic_auxiliary",
                "r04_baseline_A",
                "r04_deterministic_auxiliary",
                "deterministic_auxiliary",
                "anchor_signal_date",
                rule,
                source_path,
                source_hash,
                status=status,
                invalid=invalid,
                field_source_map={k: field_map.get(k, {}) for k in required},
            )
        )
        mask = pd.Series(True, index=work.index)
        if not missing:
            for col, (_, threshold) in rule.items():
                mask &= pd.to_numeric(work[col], errors="coerce") >= float(threshold)
        selected = work.loc[mask].copy() if not missing else work.iloc[0:0].copy()
        selected["pool_id"] = pool_id
        selected["pool_family_id"] = "r04_deterministic_auxiliary"
        selected["pool_source_id"] = "r04_baseline_A"
        selected["adapter_id"] = "r04_deterministic_auxiliary"
        selected["pool_promotability_status"] = status
        selected["source_event_id"] = selected["source_event_id"].astype(str)
        selected["pool_event_id"] = [
            _event_id(pool_id, r.instrument_id, r.anchor_signal_date, r.source_event_id) for r in selected.itertuples(index=False)
        ]
        frames.append(selected)
        waterfall.append(
            {
                "pool_id": pool_id,
                "source_rows": int(len(work)),
                "after_membership_rule_rows": int(len(selected)),
                "after_episode_collapse_rows": int(len(selected)),
                "after_entry_resolution_rows": np.nan,
                "replay_complete_count": np.nan,
                "pool_promotability_status": status,
                "invalid_pool_reason": invalid,
            }
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _collapse_signal_events(df: pd.DataFrame, pool_id: str, gap: int, cal_map: dict[pd.Timestamp, int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for instrument, part in df.sort_values(["instrument_id", "trade_date"]).groupby("instrument_id", sort=False):
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
                current = {
                    "pool_id": pool_id,
                    "instrument_id": instrument,
                    "anchor_signal_date": dt,
                    "source_split": row.split,
                    "source_event_id": str(getattr(row, "signal_episode_id", "")) or f"{instrument}|{dt.date()}",
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
    return pd.DataFrame(rows)


def _r02_family_events(
    config: dict[str, Any],
    regime_lookup: pd.DataFrame,
    registry_rows: list[dict[str, Any]],
    waterfall: list[dict[str, Any]],
    cal_map: dict[pd.Timestamp, int],
) -> pd.DataFrame:
    src = config["source_registry"]["r02_family_precision"]
    root = topic_path(src["source_root"])
    panel_path = root / "cache/r02_family_action_time_panel.parquet"
    source_hash = _hash_file(panel_path) if panel_path.exists() else ""
    mapping = {
        "momentum_rps": "r02_precision_momentum_rps",
        "oscillator": "r02_precision_oscillator",
        "price_trend": "r02_precision_price_trend",
        "pullback_drawdown": "r02_precision_pullback_drawdown",
        "range_breakout": "r02_precision_range_breakout",
        "volatility_band": "r02_precision_volatility_band",
        "volume_money": "r02_precision_volume_money",
    }
    for family, pool_id in mapping.items():
        registry_rows.append(
            _registry_row(
                pool_id,
                "r02_family_precision",
                "r02_family_precision",
                "r02_family_precision_frozen_family_occurrence",
                "upstream_family_occurrence",
                "trade_date",
                {
                    "family_id": family,
                    "signal_occurs": True,
                    "feature_complete_flag": True,
                    "base_action_time_eligible_flag": True,
                },
                relpath(panel_path),
                source_hash,
            )
        )
    if not panel_path.exists():
        return pd.DataFrame()
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
    raw["instrument_id"] = raw["instrument_id"].astype(str).str.upper()
    raw["trade_date"] = pd.to_datetime(raw["trade_date"]).dt.normalize()
    eligible = raw[
        raw["family_id"].astype(str).isin(mapping)
        & raw["signal_occurs"].map(_to_bool)
        & raw["feature_complete_flag"].map(_to_bool)
        & raw["base_action_time_eligible_flag"].map(_to_bool)
    ].copy()
    frames: list[pd.DataFrame] = []
    gap = int(config["execution"]["episode_gap_trading_days"])
    for family, pool_id in mapping.items():
        part = eligible[eligible["family_id"].astype(str).eq(family)].copy()
        collapsed = _collapse_signal_events(part, pool_id, gap, cal_map)
        if collapsed.empty:
            waterfall.append(
                {
                    "pool_id": pool_id,
                    "source_rows": int(len(part)),
                    "after_membership_rule_rows": int(len(part)),
                    "after_episode_collapse_rows": 0,
                    "after_entry_resolution_rows": np.nan,
                    "replay_complete_count": np.nan,
                    "pool_promotability_status": "promotable",
                    "invalid_pool_reason": "",
                }
            )
            continue
        collapsed["pool_family_id"] = "r02_family_precision"
        collapsed["pool_source_id"] = "r02_family_precision"
        collapsed["adapter_id"] = "r02_family_precision_frozen_family_occurrence"
        collapsed["pool_promotability_status"] = "promotable"
        collapsed["pool_event_id"] = [
            _event_id(pool_id, r.instrument_id, r.anchor_signal_date, r.source_event_id) for r in collapsed.itertuples(index=False)
        ]
        frames.append(collapsed)
        waterfall.append(
            {
                "pool_id": pool_id,
                "source_rows": int(len(part)),
                "after_membership_rule_rows": int(len(part)),
                "after_episode_collapse_rows": int(len(collapsed)),
                "after_entry_resolution_rows": np.nan,
                "replay_complete_count": np.nan,
                "pool_promotability_status": "promotable",
                "invalid_pool_reason": "",
            }
        )
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if out.empty:
        return out
    out = out.merge(regime_lookup.rename(columns={"anchor_signal_date": "anchor_signal_date"}), on=["instrument_id", "anchor_signal_date"], how="left")
    out["market_regime_bucket"] = out["market_regime_bucket"].fillna("missing_market_regime")
    out["industry_regime_bucket"] = out["industry_regime_bucket"].fillna("missing_industry")
    out["industry_target_key"] = out["industry_target_key"].fillna("missing_industry")
    return out


def _r03c_events(config: dict[str, Any], registry_rows: list[dict[str, Any]], waterfall: list[dict[str, Any]]) -> pd.DataFrame:
    adapter_cfg = config.get("r03c_adapter", {})
    keys = [str(k) for k in adapter_cfg.get("r03c_promotable_pooling_keys", [])]
    src = config["source_registry"]["r03c_family_set_pooling"]
    root = topic_path(src["source_root"])
    panel_path = root / "cache/r03c_family_set_pooling_panel.parquet"
    key_col = adapter_cfg.get("r03c_pooling_key_column", "pooling_key")
    anchor_col = adapter_cfg.get("r03c_anchor_signal_date_column", "step_signal_date")
    instrument_col = adapter_cfg.get("r03c_instrument_column", "instrument_id")
    registry_rows.append(
        _registry_row(
            "r03c_config_frozen_family_set_pool",
            "r03c_family_set_pooling",
            "r03c_family_set_pooling",
            "r03c_config_frozen_family_set_pool",
            "upstream_family_set_config",
            anchor_col,
            {"keys": keys, "key_column": key_col, "anchor_column": anchor_col},
            relpath(panel_path),
            _hash_file(panel_path) if panel_path.exists() else "",
            status="promotable" if keys else "descriptive_lead_only_no_config_keys",
            selection_allowed="train" if keys else "none",
        )
    )
    if not keys or not panel_path.exists():
        waterfall.append(
            {
                "pool_id": "r03c_config_frozen_family_set_pool",
                "source_rows": 0,
                "after_membership_rule_rows": 0,
                "after_episode_collapse_rows": 0,
                "after_entry_resolution_rows": np.nan,
                "replay_complete_count": np.nan,
                "pool_promotability_status": "descriptive_lead_only_no_config_keys",
                "invalid_pool_reason": "no_r03c_promotable_pooling_keys",
            }
        )
        return pd.DataFrame()
    raw = pd.read_parquet(panel_path)
    required = {key_col, anchor_col, instrument_col, "split"}
    if not required.issubset(raw.columns):
        return pd.DataFrame()
    part = raw[raw[key_col].astype(str).isin(keys)].copy()
    part["instrument_id"] = part[instrument_col].astype(str).str.upper()
    part["anchor_signal_date"] = pd.to_datetime(part[anchor_col]).dt.normalize()
    part["pool_id"] = "r03c_config_frozen_family_set_pool"
    part["pool_family_id"] = "r03c_family_set_pooling"
    part["pool_source_id"] = "r03c_family_set_pooling"
    part["adapter_id"] = "r03c_config_frozen_family_set_pool"
    part["pool_promotability_status"] = "promotable"
    part["source_split"] = part["split"].astype(str)
    part["source_event_id"] = part[key_col].astype(str) + "|" + part.get("seed_episode_id", part.index.astype(str)).astype(str)
    part["pool_event_id"] = [_event_id("r03c_config_frozen_family_set_pool", r.instrument_id, r.anchor_signal_date, r.source_event_id) for r in part.itertuples(index=False)]
    for col in ["market_regime_bucket", "industry_regime_bucket", "industry_target_key"]:
        if col not in part.columns:
            part[col] = "missing_market_regime" if col == "market_regime_bucket" else "missing_industry"
    return part[["pool_event_id", "source_event_id", "pool_id", "pool_family_id", "pool_source_id", "adapter_id", "pool_promotability_status", "instrument_id", "anchor_signal_date", "source_split", "market_regime_bucket", "industry_regime_bucket", "industry_target_key"]]


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
            return pd.Timestamp(row["trade_date"]), float(row["adjusted_open"]), int(idx), ""
    return pd.NaT, np.nan, np.nan, "invalid_entry"


def _prepare_events(events: pd.DataFrame, price: pd.DataFrame, calendar: pd.DatetimeIndex, config: dict[str, Any]) -> pd.DataFrame:
    if events.empty:
        return events
    price = price.copy()
    price["executable_open_flag"] = (
        (price["adjusted_open"] > 0)
        & (price["volume"] > 0)
        & (price["money"] > 0)
        & (~price["suspended_or_dirty_bar"].map(_to_bool))
    )
    price_by_inst = {inst: part.sort_values("calendar_index").reset_index(drop=True) for inst, part in price.groupby("instrument_id", sort=False)}
    bounds = _split_bounds(config)
    max_lag = int(config["execution"]["max_entry_execution_lag_trading_days"])
    rows: list[dict[str, Any]] = []
    for row in events.itertuples(index=False):
        anchor = pd.Timestamp(row.anchor_signal_date).normalize()
        source_split = str(getattr(row, "source_split", ""))
        split = source_split if source_split in SPLITS else _split_for_date(anchor, bounds)
        entry_date = getattr(row, "source_entry_execution_date", pd.NaT)
        entry_price = getattr(row, "source_entry_price", np.nan)
        entry_idx = np.nan
        status = ""
        entry_price_numeric = pd.to_numeric(pd.Series([entry_price]), errors="coerce").iloc[0]
        needs_entry_resolution = pd.isna(entry_date) or pd.isna(entry_price_numeric) or not np.isfinite(float(entry_price_numeric))
        if needs_entry_resolution:
            entry_date, entry_price, entry_idx, status = _first_executable_after(price_by_inst, row.instrument_id, anchor, calendar, max_lag)
        else:
            entry_date = pd.Timestamp(entry_date).normalize()
            inst = price_by_inst.get(str(row.instrument_id).upper())
            if inst is None:
                status = "invalid_entry"
            else:
                match = inst[inst["trade_date"].eq(entry_date)]
                if match.empty:
                    status = "invalid_entry"
                else:
                    entry_idx = int(match.iloc[0]["calendar_index"])
                    entry_price = float(match.iloc[0]["adjusted_open"])
        rec = row._asdict()
        rec.update(
            {
                "split": split,
                "entry_execution_date": entry_date,
                "entry_price": entry_price,
                "entry_calendar_index": entry_idx,
                "entry_resolution_status": status or "passed",
            }
        )
        rows.append(rec)
    out = pd.DataFrame(rows)
    out["anchor_signal_date"] = pd.to_datetime(out["anchor_signal_date"]).dt.normalize()
    out["entry_execution_date"] = pd.to_datetime(out["entry_execution_date"], errors="coerce").dt.normalize()
    out["entry_calendar_year"] = out["entry_execution_date"].dt.year
    out["entry_calendar_quarter"] = out["entry_execution_date"].dt.to_period("Q").astype(str)
    out["market_regime_bucket"] = out["market_regime_bucket"].fillna("missing_market_regime")
    out["industry_regime_bucket"] = out["industry_regime_bucket"].fillna("missing_industry")
    out["industry_target_key"] = out["industry_target_key"].fillna("missing_industry")
    return out


def _replay_events(events: pd.DataFrame, price: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    price_by_inst = {inst: part.sort_values("calendar_index").set_index("calendar_index", drop=False) for inst, part in price.groupby("instrument_id", sort=False)}
    bounds = _split_bounds(config)
    max_hold = int(config["execution"]["max_holding_days"])
    max_exit_lag = int(config["execution"]["max_exit_execution_lag_trading_days"])
    cost = config["cost_model"]
    entry_cost = (float(cost["entry_slippage_bps"]) + float(cost["commission_bps_per_side"])) / 10000.0
    exit_cost = (float(cost["exit_slippage_bps"]) + float(cost["commission_bps_per_side"]) + float(cost["stamp_tax_bps_on_exit"])) / 10000.0
    total_cost_bps = float(cost["entry_slippage_bps"]) + float(cost["exit_slippage_bps"]) + 2 * float(cost["commission_bps_per_side"]) + float(cost["stamp_tax_bps_on_exit"])
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(events.itertuples(index=False), start=1):
        rec = row._asdict()
        rec.update(
            {
                "replay_status": "invalid_entry",
                "replay_complete": False,
                "exit_signal_date": pd.NaT,
                "exit_execution_date": pd.NaT,
                "exit_execution_offset": np.nan,
                "exit_price": np.nan,
                "gross_return": np.nan,
                "net_return": np.nan,
                "loss_le_minus5_flag": False,
                "loss_le_minus10_flag": False,
                "max_gain_120d": np.nan,
                "max_drawdown_120d": np.nan,
                "max_gain50_flag": False,
                "avg_holding_days": np.nan,
            }
        )
        if str(row.entry_resolution_status) != "passed" or pd.isna(row.entry_calendar_index):
            rows.append(rec)
            continue
        inst = price_by_inst.get(str(row.instrument_id).upper())
        if inst is None:
            rec["replay_status"] = "censored_by_missing_price"
            rows.append(rec)
            continue
        entry_idx = int(row.entry_calendar_index)
        path_indices = list(range(entry_idx, entry_idx + max_hold + 1))
        if not all(path_idx in inst.index for path_idx in path_indices):
            rec["replay_status"] = "censored_by_missing_price"
            rows.append(rec)
            continue
        path = inst.loc[path_indices]
        if isinstance(path, pd.Series):
            path = path.to_frame().T
        close = pd.to_numeric(path["adjusted_close"], errors="coerce")
        if close.isna().any() or (close <= 0).any():
            rec["replay_status"] = "censored_by_missing_price"
            rows.append(rec)
            continue
        close_return = close / float(row.entry_price) - 1.0
        max_gain = float(close_return.max())
        max_drawdown = float(close_return.min())
        signal_idx = entry_idx + max_hold
        rec["exit_signal_date"] = pd.Timestamp(inst.loc[signal_idx]["trade_date"]) if signal_idx in inst.index else pd.NaT
        exit_row = None
        exit_offset = None
        for exec_idx in range(signal_idx + 1, signal_idx + max_exit_lag + 1):
            if exec_idx not in inst.index:
                continue
            cand = inst.loc[exec_idx]
            if isinstance(cand, pd.DataFrame):
                cand = cand.iloc[0]
            if bool(cand["executable_open_flag"]) and np.isfinite(float(cand["adjusted_open"])) and float(cand["adjusted_open"]) > 0:
                exit_row = cand
                exit_offset = exec_idx - entry_idx
                break
        if exit_row is None:
            rec.update({"replay_status": "censored_by_no_exit_execution", "max_gain_120d": max_gain, "max_drawdown_120d": max_drawdown, "max_gain50_flag": max_gain >= float(config["thresholds"]["max_gain50_threshold"])})
            rows.append(rec)
            continue
        exit_date = pd.Timestamp(exit_row["trade_date"]).normalize()
        if _split_for_date(exit_date, bounds) != str(row.split):
            rec.update({"replay_status": "censored_by_split_boundary", "exit_execution_date": exit_date, "exit_execution_offset": exit_offset, "max_gain_120d": max_gain, "max_drawdown_120d": max_drawdown, "max_gain50_flag": max_gain >= float(config["thresholds"]["max_gain50_threshold"])})
            rows.append(rec)
            continue
        gross = float(exit_row["adjusted_open"]) / float(row.entry_price) - 1.0
        net = gross - entry_cost - exit_cost
        rec.update(
            {
                "replay_status": "replay_complete",
                "replay_complete": True,
                "exit_execution_date": exit_date,
                "exit_execution_offset": exit_offset,
                "exit_price": float(exit_row["adjusted_open"]),
                "gross_return": gross,
                "net_return": net,
                "entry_cost": entry_cost,
                "exit_cost": exit_cost,
                "total_cost_bps": total_cost_bps,
                "loss_le_minus5_flag": net <= -0.05,
                "loss_le_minus10_flag": net <= -0.10,
                "max_gain_120d": max_gain,
                "max_drawdown_120d": max_drawdown,
                "max_gain50_flag": max_gain >= float(config["thresholds"]["max_gain50_threshold"]),
                "avg_holding_days": exit_offset,
            }
        )
        rows.append(rec)
        if idx % 20000 == 0:
            print(f"replayed {idx:,}/{len(events):,} pool events", flush=True)
    out = pd.DataFrame(rows)
    out["replay_complete"] = out["replay_complete"].map(_to_bool)
    return out


def _profile(replay: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    thresholds = config["thresholds"]
    min_complete = {
        "train": thresholds["minimum_train_replay_complete_count"],
        "validation": thresholds["minimum_validation_replay_complete_count"],
        "robustness": thresholds["minimum_robustness_replay_complete_count"],
    }
    for keys, part in replay.groupby(["pool_id", "pool_family_id", "pool_source_id", "adapter_id", "pool_promotability_status", "split"], dropna=False, sort=False):
        pool_id, family, source, adapter, status, split = keys
        complete = part[part["replay_complete"].map(_to_bool)].copy()
        event_count = int(len(part))
        replay_complete_count = int(len(complete))
        years = complete["entry_calendar_year"].value_counts(normalize=True)
        instruments = complete["instrument_id"].value_counts(normalize=True)
        industries = complete["industry_target_key"].value_counts(normalize=True)
        rec = {
            "pool_id": pool_id,
            "pool_family_id": family,
            "pool_source_id": source,
            "adapter_id": adapter,
            "pool_promotability_status": status,
            "split": split,
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
            "max_drawdown_p50": _quantile(complete["max_drawdown_120d"], 0.50),
            "max_drawdown_p90": _quantile(complete["max_drawdown_120d"], 0.90),
            "max_gain50_count": int(complete["max_gain50_flag"].sum()) if replay_complete_count else 0,
            "max_gain50_rate": float(complete["max_gain50_flag"].mean()) if replay_complete_count else np.nan,
            "max_gain120d_p90": _quantile(complete["max_gain_120d"], 0.90),
            "avg_holding_days": float(complete["avg_holding_days"].mean()) if replay_complete_count else np.nan,
            "top1_calendar_year_share": float(years.iloc[0]) if len(years) else np.nan,
            "top1_instrument_share": float(instruments.iloc[0]) if len(instruments) else np.nan,
            "top5_instrument_share": float(instruments.iloc[:5].sum()) if len(instruments) else np.nan,
            "top1_industry_share": float(industries.iloc[0]) if len(industries) else np.nan,
            "calendar_year_count": int(complete["entry_calendar_year"].nunique()) if replay_complete_count else 0,
            "instrument_count": int(complete["instrument_id"].nunique()) if replay_complete_count else 0,
            "industry_count": int(complete["industry_target_key"].nunique()) if replay_complete_count else 0,
        }
        rec["pool_denominator_status"] = "sufficient" if replay_complete_count >= min_complete.get(str(split), thresholds["minimum_validation_replay_complete_count"]) else "insufficient"
        rows.append(rec)
    return pd.DataFrame(rows)


def _weighted_mean(frame: pd.DataFrame, value_col: str, weight_col: str = "weight") -> float:
    vals = pd.to_numeric(frame[value_col], errors="coerce")
    weights = pd.to_numeric(frame[weight_col], errors="coerce")
    mask = vals.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        return np.nan
    return float(np.average(vals[mask], weights=weights[mask]))


def _weighted_top_share(frame: pd.DataFrame, key_col: str, weight_col: str = "weight") -> float:
    if frame.empty:
        return np.nan
    weights = frame.groupby(key_col)[weight_col].sum().sort_values(ascending=False)
    total = weights.sum()
    return _safe_div(float(weights.iloc[0]) if len(weights) else np.nan, float(total))


def _matched_baseline(replay: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    complete = replay[replay["replay_complete"].map(_to_bool)].copy()
    baseline_id = "baseline_A_r04_included_rps_episode_first_trigger"
    baseline = complete[complete["pool_id"].eq(baseline_id)].copy()
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
    panel_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for (pool_id, split), pool_part in complete.groupby(["pool_id", "split"], dropna=False, sort=False):
        pool_part = pool_part.copy()
        weights: dict[int, float] = defaultdict(float)
        assignments = 0
        matched_pool_events = 0
        if pool_id == baseline_id:
            base_part = baseline[baseline["split"].eq(split)]
            for idx in base_part.index:
                weights[int(idx)] = 1.0
            assignments = int(len(base_part))
            matched_pool_events = int(len(pool_part))
        else:
            remaining = pool_part.copy()
            for level in match_levels:
                if remaining.empty:
                    break
                matched_indices: list[int] = []
                for key, group in remaining.groupby(list(level), dropna=False):
                    key_tuple = key if isinstance(key, tuple) else (key,)
                    base_idx = baseline_groups[level].get(key_tuple)
                    if base_idx is None or len(base_idx) == 0:
                        continue
                    add = len(group) / len(base_idx)
                    for idx in base_idx:
                        weights[int(idx)] += float(add)
                    assignments += int(len(group) * len(base_idx))
                    matched_pool_events += int(len(group))
                    matched_indices.extend(group.index.tolist())
                if matched_indices:
                    remaining = remaining.drop(index=matched_indices)
        if weights:
            match = baseline.loc[list(weights.keys())].copy()
            match["weight"] = [weights[int(idx)] for idx in match.index]
        else:
            match = pd.DataFrame(columns=list(baseline.columns) + ["weight"])
        weight_sum = float(match["weight"].sum()) if not match.empty else 0.0
        weight_sq_sum = float(np.square(match["weight"]).sum()) if not match.empty else 0.0
        ess = (weight_sum * weight_sum / weight_sq_sum) if weight_sq_sum > 0 else 0.0
        status = "sufficient" if ess >= min_ess and matched_pool_events > 0 else "insufficient"
        if not match.empty:
            for idx, row in match.iterrows():
                panel_rows.append(
                    {
                        "pool_id": pool_id,
                        "split": split,
                        "baseline_pool_event_id": row["pool_event_id"],
                        "baseline_source_event_id": row.get("source_event_id", ""),
                        "weight": float(row["weight"]),
                    }
                )
        summary_rows.append(
            {
                "pool_id": pool_id,
                "split": split,
                "matched_comparator_status": status,
                "matched_comparator_count": assignments,
                "matched_comparator_unique_event_count": int(len(match)),
                "matched_comparator_effective_sample_size": ess,
                "matched_pool_event_count": matched_pool_events,
                "pool_net_return_mean": float(pool_part["net_return"].mean()) if len(pool_part) else np.nan,
                "matched_baseline_net_return_mean": _weighted_mean(match, "net_return"),
                "net_return_mean_delta_vs_matched_baseline_A": float(pool_part["net_return"].mean()) - _weighted_mean(match, "net_return") if len(pool_part) else np.nan,
                "pool_net_return_p10": _quantile(pool_part["net_return"], 0.10),
                "matched_baseline_net_return_p10": _weighted_quantile(match["net_return"], match["weight"], 0.10) if not match.empty else np.nan,
                "p10_delta_vs_matched_baseline_A": _quantile(pool_part["net_return"], 0.10) - (_weighted_quantile(match["net_return"], match["weight"], 0.10) if not match.empty else np.nan),
                "pool_loss_le_minus5_rate": float(pool_part["loss_le_minus5_flag"].mean()) if len(pool_part) else np.nan,
                "matched_baseline_loss_le_minus5_rate": _weighted_mean(match.assign(loss_numeric=match["loss_le_minus5_flag"].astype(float)) if not match.empty else match, "loss_numeric") if not match.empty else np.nan,
                "loss_le_minus5_delta_vs_matched_baseline_A": (float(pool_part["loss_le_minus5_flag"].mean()) - _weighted_mean(match.assign(loss_numeric=match["loss_le_minus5_flag"].astype(float)), "loss_numeric")) if len(pool_part) and not match.empty else np.nan,
                "pool_max_gain50_rate": float(pool_part["max_gain50_flag"].mean()) if len(pool_part) else np.nan,
                "matched_baseline_max_gain50_rate": _weighted_mean(match.assign(max_gain50_numeric=match["max_gain50_flag"].astype(float)) if not match.empty else match, "max_gain50_numeric") if not match.empty else np.nan,
                "max_gain50_rate_delta_vs_matched_baseline_A": (float(pool_part["max_gain50_flag"].mean()) - _weighted_mean(match.assign(max_gain50_numeric=match["max_gain50_flag"].astype(float)), "max_gain50_numeric")) if len(pool_part) and not match.empty else np.nan,
                "pool_top1_calendar_year_share": float(pool_part["entry_calendar_year"].value_counts(normalize=True).iloc[0]) if len(pool_part) else np.nan,
                "matched_baseline_top1_calendar_year_share": _weighted_top_share(match, "entry_calendar_year") if not match.empty else np.nan,
                "top1_calendar_year_share_delta_vs_matched_baseline_A": (float(pool_part["entry_calendar_year"].value_counts(normalize=True).iloc[0]) - _weighted_top_share(match, "entry_calendar_year")) if len(pool_part) and not match.empty else np.nan,
                "pool_top1_instrument_share": float(pool_part["instrument_id"].value_counts(normalize=True).iloc[0]) if len(pool_part) else np.nan,
                "matched_baseline_top1_instrument_share": _weighted_top_share(match, "instrument_id") if not match.empty else np.nan,
                "top1_instrument_share_delta_vs_matched_baseline_A": (float(pool_part["instrument_id"].value_counts(normalize=True).iloc[0]) - _weighted_top_share(match, "instrument_id")) if len(pool_part) and not match.empty else np.nan,
            }
        )
    return pd.DataFrame(panel_rows), pd.DataFrame(summary_rows)


def _global_delta(profile: pd.DataFrame) -> pd.DataFrame:
    baseline_id = "baseline_A_r04_included_rps_episode_first_trigger"
    base = profile[profile["pool_id"].eq(baseline_id)][
        ["split", "net_return_mean", "net_return_p10", "loss_le_minus5_rate", "max_gain50_rate"]
    ].rename(
        columns={
            "net_return_mean": "global_baseline_net_return_mean",
            "net_return_p10": "global_baseline_net_return_p10",
            "loss_le_minus5_rate": "global_baseline_loss_le_minus5_rate",
            "max_gain50_rate": "global_baseline_max_gain50_rate",
        }
    )
    out = profile.merge(base, on="split", how="left")
    out["net_return_mean_delta_vs_global_baseline_A"] = out["net_return_mean"] - out["global_baseline_net_return_mean"]
    out["p10_delta_vs_global_baseline_A"] = out["net_return_p10"] - out["global_baseline_net_return_p10"]
    out["loss_le_minus5_delta_vs_global_baseline_A"] = out["loss_le_minus5_rate"] - out["global_baseline_loss_le_minus5_rate"]
    out["max_gain50_rate_delta_vs_global_baseline_A"] = out["max_gain50_rate"] - out["global_baseline_max_gain50_rate"]
    return out[
        [
            "pool_id",
            "split",
            "net_return_mean_delta_vs_global_baseline_A",
            "p10_delta_vs_global_baseline_A",
            "loss_le_minus5_delta_vs_global_baseline_A",
            "max_gain50_rate_delta_vs_global_baseline_A",
        ]
    ]


def _zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    std = values.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return (values - values.mean()) / std


def _selection(profile: pd.DataFrame, matched: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    metrics = profile.merge(matched, on=["pool_id", "split"], how="left", suffixes=("", "_matched"))
    reg = registry[["pool_id", "pool_family_id", "adapter_id", "pool_promotability_status", "selection_stage_allowed"]]
    metrics = metrics.drop(columns=[c for c in ["pool_family_id_y", "adapter_id_y", "pool_promotability_status_y"] if c in metrics.columns], errors="ignore")
    metrics = metrics.merge(reg, on="pool_id", how="left", suffixes=("", "_registry"))
    for col in ["pool_family_id", "adapter_id", "pool_promotability_status"]:
        reg_col = f"{col}_registry"
        if reg_col in metrics.columns:
            metrics[col] = metrics[col].fillna(metrics[reg_col])
            metrics = metrics.drop(columns=[reg_col])
    thresholds = config["thresholds"]
    selectable = metrics[
        metrics["split"].eq("train")
        & metrics["adapter_id"].isin(PROMOTABLE_ADAPTERS)
        & metrics["pool_promotability_status"].eq("promotable")
        & metrics["selection_stage_allowed"].eq("train")
    ].copy()
    selectable["train_gate_pass"] = (
        selectable["replay_complete_count"].ge(thresholds["minimum_train_replay_complete_count"])
        & selectable["censored_share"].le(thresholds["max_censored_share"])
        & selectable["matched_comparator_status"].eq("sufficient")
    )
    selectable["concentration_penalty"] = np.maximum(selectable["top1_calendar_year_share"] - 0.50, 0) + np.maximum(selectable["top1_instrument_share"] - 0.05, 0)
    selectable["train_pool_quality_score"] = np.nan
    trace_rows: list[dict[str, Any]] = []
    train_selected_ids: set[str] = set()
    for family, part in selectable.groupby("pool_family_id", sort=False):
        idx = part.index
        selectable.loc[idx, "train_pool_quality_score"] = (
            _zscore(part["net_return_mean_delta_vs_matched_baseline_A"])
            - _zscore(part["loss_le_minus5_delta_vs_matched_baseline_A"])
            + _zscore(part["max_gain50_rate_delta_vs_matched_baseline_A"])
            + _zscore(part["p10_delta_vs_matched_baseline_A"])
            - part["concentration_penalty"].fillna(0)
        )
        eligible = selectable.loc[idx][selectable.loc[idx, "train_gate_pass"]]
        selected_pool = ""
        if not eligible.empty:
            selected_pool = str(eligible.sort_values(["train_pool_quality_score", "net_return_mean_delta_vs_matched_baseline_A"], ascending=False).iloc[0]["pool_id"])
            train_selected_ids.add(selected_pool)
        ranked = selectable.loc[idx].sort_values(["train_pool_quality_score", "pool_id"], ascending=[False, True])
        for rank, row in enumerate(ranked.itertuples(index=False), start=1):
            trace_rows.append(
                {
                    "selection_stage": "train_pool_selection",
                    "split_used": "train",
                    "pool_family_id": row.pool_family_id,
                    "candidate_pool_id": row.pool_id,
                    "selection_metric_name": "train_pool_quality_score",
                    "selection_metric_value": row.train_pool_quality_score,
                    "selection_rank": rank,
                    "z_reference_set_id": row.pool_family_id,
                    "z_reference_set_size": int(len(part)),
                    "selected_flag": row.pool_id == selected_pool,
                    "rejection_reason": "" if row.pool_id == selected_pool else ("failed_train_gate" if not row.train_gate_pass else "lower_train_score"),
                }
            )
    train_trace = pd.DataFrame(trace_rows)
    val = metrics[metrics["split"].eq("validation") & metrics["pool_id"].isin(train_selected_ids)].copy()
    year_limit = np.maximum(float(thresholds["concentration_top1_year_floor"]), val["matched_baseline_top1_calendar_year_share"] + float(thresholds["concentration_top1_year_relative_buffer"]))
    inst_limit = np.maximum(float(thresholds["concentration_top1_instrument_floor"]), val["matched_baseline_top1_instrument_share"] + float(thresholds["concentration_top1_instrument_relative_buffer"]))
    val["validation_gate_pass"] = (
        val["replay_complete_count"].ge(thresholds["minimum_validation_replay_complete_count"])
        & val["censored_share"].le(thresholds["max_censored_share"])
        & val["matched_comparator_status"].eq("sufficient")
        & val["net_return_mean"].gt(thresholds["validation_min_net_return_mean"])
        & val["net_return_mean_delta_vs_matched_baseline_A"].gt(0)
        & val["loss_le_minus5_delta_vs_matched_baseline_A"].lt(0)
        & val["max_gain50_rate"].ge(0.8 * val["matched_baseline_max_gain50_rate"])
        & val["max_gain50_count"].ge(thresholds["minimum_validation_max_gain50_count"])
        & val["top1_calendar_year_share"].le(year_limit)
        & val["top1_instrument_share"].le(inst_limit)
    )
    val["concentration_penalty"] = np.maximum(val["top1_calendar_year_share"] - 0.50, 0) + np.maximum(val["top1_instrument_share"] - 0.05, 0)
    val["validation_selection_score"] = (
        _zscore(val["net_return_mean_delta_vs_matched_baseline_A"])
        - _zscore(val["loss_le_minus5_delta_vs_matched_baseline_A"])
        + _zscore(val["max_gain50_rate_delta_vs_matched_baseline_A"])
        + _zscore(val["p10_delta_vs_matched_baseline_A"])
        - val["concentration_penalty"].fillna(0)
    )
    selected_pool_id = ""
    passing = val[val["validation_gate_pass"]].copy()
    if not passing.empty:
        selected = passing.sort_values(
            ["validation_selection_score", "net_return_mean_delta_vs_matched_baseline_A", "loss_le_minus5_rate", "max_gain50_rate", "pool_id"],
            ascending=[False, False, True, False, True],
        ).iloc[0]
        selected_pool_id = str(selected["pool_id"])
    val = val.sort_values(["validation_selection_score", "pool_id"], ascending=[False, True]).reset_index(drop=True)
    val["validation_selected_rank"] = np.arange(1, len(val) + 1)
    val["selected_candidate_pool_id"] = np.where(val["pool_id"].eq(selected_pool_id), selected_pool_id, "")
    val["selected_flag"] = val["pool_id"].eq(selected_pool_id)
    robustness = metrics[metrics["split"].eq("robustness") & metrics["pool_id"].eq(selected_pool_id)].copy()
    if not robustness.empty:
        year_limit_r = np.maximum(float(thresholds["concentration_top1_year_floor"]), robustness["matched_baseline_top1_calendar_year_share"] + float(thresholds["concentration_top1_year_relative_buffer"]))
        inst_limit_r = np.maximum(float(thresholds["concentration_top1_instrument_floor"]), robustness["matched_baseline_top1_instrument_share"] + float(thresholds["concentration_top1_instrument_relative_buffer"]))
        robustness["robustness_gate_pass"] = (
            robustness["replay_complete_count"].ge(thresholds["minimum_robustness_replay_complete_count"])
            & robustness["censored_share"].le(thresholds["max_censored_share"])
            & robustness["matched_comparator_status"].eq("sufficient")
            & robustness["net_return_mean"].gt(thresholds["robustness_min_net_return_mean"])
            & robustness["net_return_mean_delta_vs_matched_baseline_A"].gt(thresholds["robustness_min_net_return_mean_delta_vs_matched_baseline_A"])
            & robustness["loss_le_minus5_rate"].lt(thresholds["robustness_max_loss_le_minus5_rate"])
            & robustness["loss_le_minus5_delta_vs_matched_baseline_A"].lt(0)
            & robustness["max_gain50_rate"].ge(np.maximum(0.10, 0.8 * robustness["matched_baseline_max_gain50_rate"]))
            & robustness["max_gain50_count"].ge(thresholds["minimum_robustness_max_gain50_count"])
            & robustness["top1_calendar_year_share"].le(year_limit_r)
            & robustness["top1_instrument_share"].le(inst_limit_r)
        )
    else:
        robustness["robustness_gate_pass"] = pd.Series(dtype=bool)
    selection_panel = metrics.copy()
    selection_panel["train_selected_flag"] = selection_panel["pool_id"].isin(train_selected_ids)
    selection_panel["selected_candidate_pool_id"] = selected_pool_id
    selection_panel["final_candidate_flag"] = selection_panel["pool_id"].eq(selected_pool_id)
    return train_trace, selection_panel, val, robustness, selected_pool_id


def _final_decision(selected_pool_id: str, validation: pd.DataFrame, robustness: pd.DataFrame) -> tuple[str, str]:
    if not selected_pool_id:
        return "r04c_no_candidate_pool_passed_validation", "no train-selected pool passed validation hard gates"
    if robustness.empty or not bool(robustness.iloc[0].get("robustness_gate_pass", False)):
        return "r04c_candidate_pool_not_robust_scanner_complete", "validation-frozen selected pool failed robustness gate"
    return "r04c_candidate_pool_passed_diagnostic_only", "validation-frozen selected pool passed robustness diagnostic gates"


def _concentration_audit(profile: pd.DataFrame, matched: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    out = profile.merge(
        matched[["pool_id", "split", "matched_baseline_top1_calendar_year_share", "matched_baseline_top1_instrument_share"]],
        on=["pool_id", "split"],
        how="left",
    )
    thresholds = config["thresholds"]
    out["absolute_year_concentration_flag"] = out["top1_calendar_year_share"] > thresholds["concentration_top1_year_floor"]
    out["relative_year_concentration_flag"] = out["top1_calendar_year_share"] > np.maximum(
        thresholds["concentration_top1_year_floor"], out["matched_baseline_top1_calendar_year_share"] + thresholds["concentration_top1_year_relative_buffer"]
    )
    out["relative_instrument_concentration_flag"] = out["top1_instrument_share"] > np.maximum(
        thresholds["concentration_top1_instrument_floor"], out["matched_baseline_top1_instrument_share"] + thresholds["concentration_top1_instrument_relative_buffer"]
    )
    return out[
        [
            "pool_id",
            "split",
            "top1_calendar_year_share",
            "matched_baseline_top1_calendar_year_share",
            "absolute_year_concentration_flag",
            "relative_year_concentration_flag",
            "top1_instrument_share",
            "matched_baseline_top1_instrument_share",
            "relative_instrument_concentration_flag",
            "top5_instrument_share",
            "top1_industry_share",
        ]
    ]


def _overlap_audit(replay: pd.DataFrame) -> pd.DataFrame:
    keys = replay[["pool_id", "instrument_id", "anchor_signal_date"]].drop_duplicates().copy()
    keys["event_key"] = keys["instrument_id"].astype(str) + "|" + keys["anchor_signal_date"].map(_date)
    baseline_id = "baseline_A_r04_included_rps_episode_first_trigger"
    baseline_keys = set(keys.loc[keys["pool_id"].eq(baseline_id), "event_key"])
    pool_sets = {pool: set(part["event_key"]) for pool, part in keys.groupby("pool_id", sort=False)}
    rows: list[dict[str, Any]] = []
    for pool, event_set in pool_sets.items():
        overlap = len(event_set & baseline_keys)
        max_jaccard = 0.0
        max_pool = ""
        for other, other_set in pool_sets.items():
            if other == pool:
                continue
            union = len(event_set | other_set)
            jac = _safe_div(len(event_set & other_set), union)
            if np.isfinite(jac) and jac > max_jaccard:
                max_jaccard = float(jac)
                max_pool = other
        rows.append(
            {
                "pool_id": pool,
                "pool_event_count": len(event_set),
                "baseline_A_event_count": len(baseline_keys),
                "overlap_with_baseline_A_count": overlap,
                "overlap_with_baseline_A_share": _safe_div(overlap, len(event_set)),
                "pool_unique_event_share": 1.0 - _safe_div(overlap, len(event_set)),
                "max_pairwise_jaccard_with_other_pools": max_jaccard,
                "max_pairwise_jaccard_pool_id": max_pool,
            }
        )
    return pd.DataFrame(rows)


def _final_report(
    profile: pd.DataFrame,
    global_delta: pd.DataFrame,
    matched: pd.DataFrame,
    source_readiness: pd.DataFrame,
    registry: pd.DataFrame,
    train_trace: pd.DataFrame,
    validation: pd.DataFrame,
    robustness: pd.DataFrame,
    concentration: pd.DataFrame,
    selected_pool_id: str,
    final_decision: str,
    decision_reason: str,
    config: dict[str, Any],
) -> str:
    merged = profile.merge(global_delta, on=["pool_id", "split"], how="left").merge(matched, on=["pool_id", "split"], how="left", suffixes=("", "_matched"))
    baseline = merged[merged["pool_id"].eq("baseline_A_r04_included_rps_episode_first_trigger")]
    lines = [
        "# R04c Candidate Pool Scanner V1 诊断报告",
        "",
        "R04c is candidate-pool scanner, not hold/exit policy replay.",
        "R04c uses hold120 no-exit baseline only.",
        "Matched baseline_A is mandatory for pool promotion.",
        "Validation and robustness cannot define pool membership.",
        "Robustness is final readout only.",
        "No production entry rule is emitted by this scanner.",
        "",
        "## 结论",
        "",
        f"- final_decision: `{final_decision}`",
        f"- decision_reason: {decision_reason}",
        f"- selected_candidate_pool_id: `{selected_pool_id}`" if selected_pool_id else "- selected_candidate_pool_id: 无",
        "",
        "## baseline_A hold120 profile",
        "",
    ]
    for row in baseline.sort_values("split").itertuples(index=False):
        lines.append(
            f"- {row.split}: replay_complete={int(row.replay_complete_count):,}, net_mean={row.net_return_mean:.2%}, "
            f"p10={row.net_return_p10:.2%}, loss<=-5={row.loss_le_minus5_rate:.2%}, +50_rate={row.max_gain50_rate:.2%}"
        )
    lines.extend(["", "## Source readiness", ""])
    for row in source_readiness.itertuples(index=False):
        lines.append(f"- {row.source_id}: {row.source_readiness_status}, adapter={row.adapter_id}, default={row.source_promotability_default}")
    lines.extend(["", "## Pool promotability", ""])
    prom = registry["pool_promotability_status"].value_counts(dropna=False)
    for status, count in prom.items():
        lines.append(f"- {status}: {int(count)} pools")
    lines.extend(["", "## Train selection", ""])
    selected_train = train_trace[train_trace["selected_flag"].map(_to_bool)] if not train_trace.empty else pd.DataFrame()
    if selected_train.empty:
        lines.append("- train 没有选出 pool。")
    else:
        for row in selected_train.itertuples(index=False):
            lines.append(f"- {row.pool_family_id}: `{row.candidate_pool_id}` score={row.selection_metric_value:.4f}")
    lines.extend(["", "## Validation gates", ""])
    if validation.empty:
        lines.append("- validation 没有 train-selected pool 通过 hard gates。")
    else:
        for row in validation.itertuples(index=False):
            status = "PASS" if bool(row.validation_gate_pass) else "FAIL"
            lines.append(
                f"- {status} `{row.pool_id}`: net={row.net_return_mean:.2%}, "
                f"matched_delta={row.net_return_mean_delta_vs_matched_baseline_A:.2%}, "
                f"loss_delta={row.loss_le_minus5_delta_vs_matched_baseline_A:.2%}, "
                f"+50={row.max_gain50_rate:.2%}, selected={bool(row.selected_flag)}"
            )
    lines.extend(["", "## Robustness readout", ""])
    if robustness.empty:
        lines.append("- robustness 没有 final candidate readout，因为 validation 未冻结 selected pool。")
    else:
        row = robustness.iloc[0]
        lines.append(
            f"- selected `{row['pool_id']}`: gate_pass={bool(row['robustness_gate_pass'])}, "
            f"net={row['net_return_mean']:.2%}, matched_delta={row['net_return_mean_delta_vs_matched_baseline_A']:.2%}, "
            f"loss<=-5={row['loss_le_minus5_rate']:.2%}, +50={row['max_gain50_rate']:.2%}"
        )
    lines.extend(["", "## Matched baseline insight", ""])
    best_val = merged[merged["split"].eq("validation") & merged["pool_id"].ne("baseline_A_r04_included_rps_episode_first_trigger")].sort_values("net_return_mean_delta_vs_matched_baseline_A", ascending=False).head(10)
    for row in best_val.itertuples(index=False):
        lines.append(
            f"- `{row.pool_id}` validation matched_delta={row.net_return_mean_delta_vs_matched_baseline_A:.2%}, "
            f"p10_delta={row.p10_delta_vs_matched_baseline_A:.2%}, loss_delta={row.loss_le_minus5_delta_vs_matched_baseline_A:.2%}, "
            f"ESS={row.matched_comparator_effective_sample_size:.1f}"
        )
    lines.extend(["", "## Concentration / denominator audit", ""])
    matched_insufficient = matched["matched_comparator_status"].ne("sufficient").mean() if len(matched) else np.nan
    non_prom = registry["pool_promotability_status"].ne("promotable").mean() if len(registry) else np.nan
    abs_year = concentration["absolute_year_concentration_flag"].mean() if len(concentration) else np.nan
    rel_year = concentration["relative_year_concentration_flag"].mean() if len(concentration) else np.nan
    lines.append(f"- matched_comparator_status != sufficient 占比: {matched_insufficient:.2%}")
    lines.append(f"- pool_promotability_status != promotable 占比: {non_prom:.2%}")
    lines.append(f"- top1_calendar_year_share > 0.50 占比: {abs_year:.2%}")
    lines.append(f"- relative year concentration fail 占比: {rel_year:.2%}")
    failed_after_val = []
    if not validation.empty:
        val_pass = set(validation.loc[validation["validation_gate_pass"].map(_to_bool), "pool_id"])
        rob_fail = set()
        if not robustness.empty and not bool(robustness.iloc[0].get("robustness_gate_pass", False)):
            rob_fail.add(str(robustness.iloc[0]["pool_id"]))
        failed_after_val = sorted(val_pass & rob_fail)
    lines.append(f"- validation passed but robustness failed: {failed_after_val if failed_after_val else '无或未冻结'}")
    lines.extend(["", "## 判断", ""])
    if final_decision == "r04c_candidate_pool_passed_diagnostic_only":
        lines.append("存在一个 validation-frozen pool 在 robustness 上也通过诊断门槛，可以进入后续 R04b-style hold/exit/risk-budget replay。")
    elif selected_pool_id:
        lines.append("存在 validation 通过的候选池，但 robustness 未确认稳定性；下一步不应直接进入 exit policy 优化，应先分析失败项。")
    else:
        lines.append("当前扫描没有发现可升级到 R04b-style replay 的候选池；继续调 exit policy 的 ROI 低。")
    return "\n".join(lines) + "\n"


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for path in [cache_dir, reports_dir, manifests_dir]:
        path.mkdir(parents=True, exist_ok=True)

    upstream_r04 = _read_json(Path(config["upstream_r04"]["validation"]))
    upstream_r04b = _read_json(Path(config["upstream_r04b"]["validation"]))
    if upstream_r04.get("validation_status") != "passed" or upstream_r04b.get("validation_status") != "passed":
        final_decision = "blocked_upstream_validation_failed"
        final = pd.DataFrame([{"final_decision": final_decision, "decision_reason": "R04 or R04b upstream validation failed"}])
        write_csv(final, reports_dir / "r04c_final_decision.csv")
        result = {"final_decision": final_decision, "output_root": relpath(output_root)}
        write_json(result, manifests_dir / "r04c_candidate_pool_scanner_manifest.json")
        return result

    calendar = _load_calendar(config["price_provider"]["calendar_source_path"])
    cal_map = _calendar_map(calendar)
    print("loading full local PIT price provider", flush=True)
    price, price_source_hash = _load_full_price(config, calendar)
    price["executable_open_flag"] = (
        (price["adjusted_open"] > 0)
        & (price["volume"] > 0)
        & (price["money"] > 0)
        & (~price["suspended_or_dirty_bar"].map(_to_bool))
    )
    calendar_hash = _hash_file(topic_path(config["price_provider"]["calendar_source_path"]))
    print(f"loaded price rows={len(price):,}", flush=True)

    print("building pool registry and events", flush=True)
    source_readiness = _source_readiness(config)
    registry_rows: list[dict[str, Any]] = []
    waterfall: list[dict[str, Any]] = []
    base = _base_events_from_r04b(config)
    source_hash = _hash_file(topic_path(config["upstream_r04b"]["candidate_replay_base_panel"]))
    registry_rows.append(
        _registry_row(
            "baseline_A_r04_included_rps_episode_first_trigger",
            "control_baseline_A",
            "r04_baseline_A",
            "control_baseline_A",
            "control_baseline",
            "anchor_signal_date",
            {"r04_inclusion_status": "included", "entry_valid_r04b": True},
            config["upstream_r04b"]["candidate_replay_base_panel"],
            source_hash,
            status="control_baseline",
            selection_allowed="none",
        )
    )
    registry_rows.append(
        _registry_row(
            "baseline_A_matched_background",
            "control_background",
            "r04_background_action_time",
            "control_background",
            "control_not_replayed",
            "anchor_signal_date",
            {"background_pool": "available_for_descriptive_context_only"},
            config["upstream_r04"]["background_action_time_panel"],
            _hash_file(topic_path(config["upstream_r04"]["background_action_time_panel"])),
            status="descriptive_control_not_replayed",
            selection_allowed="none",
        )
    )
    rank_fields = _derive_rank_fields(config, price)
    r04_aux = _r04_auxiliary_events(base, rank_fields, config, registry_rows, waterfall)
    regime = pd.read_parquet(topic_path(config["upstream_r04"]["regime_join_panel"]))
    regime_lookup = _build_regime_lookup(regime)
    r02_events = _r02_family_events(config, regime_lookup, registry_rows, waterfall, cal_map)
    r03c_events = _r03c_events(config, registry_rows, waterfall)
    all_events = pd.concat([base, r04_aux, r02_events, r03c_events], ignore_index=True, sort=False)
    all_events = all_events.drop_duplicates("pool_event_id").reset_index(drop=True)
    all_events = _prepare_events(all_events, price, calendar, config)
    valid_splits = all_events["split"].isin(SPLITS)
    all_events = all_events[valid_splits].reset_index(drop=True)
    _write_parquet(all_events, cache_dir / "r04c_pool_event_panel.parquet")

    print(f"replaying hold120 no-exit for {len(all_events):,} pool events", flush=True)
    replay = _replay_events(all_events, price, config)
    _write_parquet(replay, cache_dir / "r04c_hold120_replay_panel.parquet")
    replay_complete_by_pool = replay.groupby("pool_id")["replay_complete"].sum().to_dict()
    for rec in waterfall:
        rec["after_entry_resolution_rows"] = int((all_events["pool_id"].eq(rec["pool_id"]) & all_events["entry_resolution_status"].eq("passed")).sum())
        rec["replay_complete_count"] = int(replay_complete_by_pool.get(rec["pool_id"], 0))

    profile = _profile(replay, config)
    matched_panel, matched = _matched_baseline(replay, config)
    global_delta = _global_delta(profile)
    concentration = _concentration_audit(profile, matched, config)
    overlap = _overlap_audit(replay)
    registry = pd.DataFrame(registry_rows).drop_duplicates("pool_id").reset_index(drop=True)
    leakage = registry[["pool_id", "adapter_id", "pool_promotability_status", "leakage_risk_class", "invalid_pool_reason"]].copy()
    train_trace, selection_panel, validation, robustness, selected_pool_id = _selection(profile, matched, registry, config)
    final_decision, decision_reason = _final_decision(selected_pool_id, validation, robustness)

    _write_parquet(matched_panel, cache_dir / "r04c_matched_baseline_panel.parquet")
    _write_parquet(selection_panel, cache_dir / "r04c_pool_selection_panel.parquet")
    write_csv(source_readiness, reports_dir / "r04c_source_readiness_audit.csv")
    write_csv(registry, reports_dir / "r04c_pool_registry_frozen.csv")
    write_csv(leakage, reports_dir / "r04c_pool_definition_leakage_audit.csv")
    write_csv(pd.DataFrame(waterfall), reports_dir / "r04c_pool_membership_waterfall.csv")
    write_csv(profile, reports_dir / "r04c_hold120_pool_profile.csv")
    write_csv(global_delta, reports_dir / "r04c_global_baseline_delta_summary.csv")
    write_csv(matched, reports_dir / "r04c_matched_baseline_delta_summary.csv")
    write_csv(train_trace, reports_dir / "r04c_train_pool_selection_trace.csv")
    write_csv(validation, reports_dir / "r04c_validation_gate_audit.csv")
    write_csv(robustness, reports_dir / "r04c_robustness_readout.csv")
    write_csv(concentration, reports_dir / "r04c_concentration_audit.csv")
    write_csv(overlap, reports_dir / "r04c_overlap_uniqueness_audit.csv")
    source_family = profile.groupby(["pool_source_id", "pool_family_id", "split"], as_index=False).agg(
        pool_count=("pool_id", "nunique"),
        best_net_return_mean=("net_return_mean", "max"),
        best_max_gain50_rate=("max_gain50_rate", "max"),
        min_loss_le_minus5_rate=("loss_le_minus5_rate", "min"),
    )
    write_csv(source_family, reports_dir / "r04c_source_family_comparison.csv")
    rejected = registry[registry["pool_promotability_status"].ne("promotable")].copy()
    write_csv(rejected, reports_dir / "r04c_rejected_descriptive_leads.csv")

    final_row = {
        "final_decision": final_decision,
        "selected_candidate_pool_id": selected_pool_id,
        "selected_pool_family_id": "",
        "selected_pool_source_id": "",
        "selected_adapter_id": "",
        "selected_pool_type": "",
        "validation_gate_pass": False,
        "robustness_gate_pass": False,
        "validation_selected_rank": np.nan,
        "validation_net_return_mean": np.nan,
        "robustness_net_return_mean": np.nan,
        "validation_net_return_mean_delta_vs_matched_baseline_A": np.nan,
        "robustness_net_return_mean_delta_vs_matched_baseline_A": np.nan,
        "validation_p10_delta_vs_matched_baseline_A": np.nan,
        "robustness_p10_delta_vs_matched_baseline_A": np.nan,
        "validation_loss_le_minus5_delta_vs_matched_baseline_A": np.nan,
        "robustness_loss_le_minus5_delta_vs_matched_baseline_A": np.nan,
        "validation_max_gain50_rate": np.nan,
        "robustness_max_gain50_rate": np.nan,
        "validation_top1_calendar_year_share": np.nan,
        "robustness_top1_calendar_year_share": np.nan,
        "validation_matched_baseline_top1_calendar_year_share": np.nan,
        "robustness_matched_baseline_top1_calendar_year_share": np.nan,
        "decision_reason": decision_reason,
    }
    if selected_pool_id:
        selected_reg = registry[registry["pool_id"].eq(selected_pool_id)].iloc[0]
        final_row.update(
            {
                "selected_pool_family_id": selected_reg["pool_family_id"],
                "selected_pool_source_id": selected_reg["pool_source_id"],
                "selected_adapter_id": selected_reg["adapter_id"],
                "selected_pool_type": selected_reg["pool_type"],
            }
        )
        if not validation.empty:
            val = validation[validation["pool_id"].eq(selected_pool_id)]
            if not val.empty:
                row = val.iloc[0]
                final_row.update(
                    {
                        "validation_gate_pass": bool(row["validation_gate_pass"]),
                        "validation_selected_rank": row["validation_selected_rank"],
                        "validation_net_return_mean": row["net_return_mean"],
                        "validation_net_return_mean_delta_vs_matched_baseline_A": row["net_return_mean_delta_vs_matched_baseline_A"],
                        "validation_p10_delta_vs_matched_baseline_A": row["p10_delta_vs_matched_baseline_A"],
                        "validation_loss_le_minus5_delta_vs_matched_baseline_A": row["loss_le_minus5_delta_vs_matched_baseline_A"],
                        "validation_max_gain50_rate": row["max_gain50_rate"],
                        "validation_top1_calendar_year_share": row["top1_calendar_year_share"],
                        "validation_matched_baseline_top1_calendar_year_share": row["matched_baseline_top1_calendar_year_share"],
                    }
                )
        if not robustness.empty:
            row = robustness.iloc[0]
            final_row.update(
                {
                    "robustness_gate_pass": bool(row["robustness_gate_pass"]),
                    "robustness_net_return_mean": row["net_return_mean"],
                    "robustness_net_return_mean_delta_vs_matched_baseline_A": row["net_return_mean_delta_vs_matched_baseline_A"],
                    "robustness_p10_delta_vs_matched_baseline_A": row["p10_delta_vs_matched_baseline_A"],
                    "robustness_loss_le_minus5_delta_vs_matched_baseline_A": row["loss_le_minus5_delta_vs_matched_baseline_A"],
                    "robustness_max_gain50_rate": row["max_gain50_rate"],
                    "robustness_top1_calendar_year_share": row["top1_calendar_year_share"],
                    "robustness_matched_baseline_top1_calendar_year_share": row["matched_baseline_top1_calendar_year_share"],
                }
            )
    final = pd.DataFrame([final_row])
    write_csv(final, reports_dir / "r04c_final_decision.csv")
    report_text = _final_report(profile, global_delta, matched, source_readiness, registry, train_trace, validation, robustness, concentration, selected_pool_id, final_decision, decision_reason, config)
    (reports_dir / "r04c_candidate_pool_scanner_final_report.md").write_text(report_text, encoding="utf-8")

    artifact_paths = [p for p in output_root.rglob("*") if p.is_file()]
    manifest = {
        "phase": config["phase"],
        "requirement_id": config["requirement_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config_path": relpath(topic_path(config_path)),
        "output_root": relpath(output_root),
        "final_decision": final_decision,
        "decision_reason": decision_reason,
        "selected_candidate_pool_id": selected_pool_id,
        "price_source_hash": price_source_hash,
        "calendar_source_hash": calendar_hash,
        "price_materialization_semantics": "R04b _load_price_panel qlib adjusted OHLCV materialization",
        "cost_model": config["cost_model"],
        "artifact_hashes": {relpath(path): _hash_file(path) for path in artifact_paths},
        "upstream_r04_validation_status": upstream_r04.get("validation_status"),
        "upstream_r04b_validation_status": upstream_r04b.get("validation_status"),
        "boundary_strings": config["validation"]["required_boundary_strings"],
    }
    write_json(manifest, manifests_dir / "r04c_candidate_pool_scanner_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    result = run(args.config)
    print(json.dumps({"final_decision": result.get("final_decision"), "selected_candidate_pool_id": result.get("selected_candidate_pool_id")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import beta

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03b_signal_sequence_big_winner_path_diagnostic_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
ALL_SPLITS = SPLITS + ["all"]
LABELS = ["good_path", "bad_path", "neutral_path"]
FAMILY_ORDER = [
    "momentum_rps",
    "oscillator",
    "price_trend",
    "pullback_drawdown",
    "range_breakout",
    "volatility_band",
    "volume_money",
]
PATH_COLS = [
    "signal_id",
    "family_id",
    "instrument_id",
    "signal_date",
    "split",
    "entry_date",
    "entry_price",
    "entry_valid",
    "path_complete_120d",
    "available_forward_trading_days",
    "first_minus5_offset",
    "first_close_minus5_offset",
    "hit_plus10_before_minus5",
    "max_loss_before_first_plus10",
    "max_gain_120d",
    "max_drawdown_120d",
    "close_return_t20",
    "close_return_t60",
    "close_return_t120",
    "path_quality_flag",
    "early_failure_flag",
]
CONSISTENCY_COLS = [
    "entry_date",
    "entry_price",
    "split",
    "entry_valid",
    "path_complete_120d",
    "available_forward_trading_days",
    "first_minus5_offset",
    "first_close_minus5_offset",
    "hit_plus10_before_minus5",
    "max_loss_before_first_plus10",
    "max_gain_120d",
    "max_drawdown_120d",
    "close_return_t20",
    "close_return_t60",
    "close_return_t120",
    "path_quality_flag",
    "early_failure_flag",
]


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: str | Path) -> dict[str, Any]:
    p = topic_path(Path(path))
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha1_id(*parts: Any) -> str:
    raw = "|".join("" if pd.isna(p) else str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _boolish(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _as_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else np.nan


def _ci(success: int, denominator: int, level: float) -> tuple[float, float]:
    if denominator <= 0:
        return (np.nan, np.nan)
    alpha = (1.0 - level) / 2.0
    return (
        float(beta.ppf(alpha, success + 0.5, denominator - success + 0.5)),
        float(beta.ppf(1.0 - alpha, success + 0.5, denominator - success + 0.5)),
    )


def _sample_status(denominator: int, thresholds: dict[str, int]) -> str:
    if denominator >= int(thresholds["N_min_sufficient"]):
        return "sufficient"
    if denominator >= int(thresholds["N_min_thin"]):
        return "thin_report_only"
    if denominator >= int(thresholds["N_min_too_sparse"]):
        return "too_sparse_report_only"
    return "unusable"


def _offset_bucket(offset: Any) -> str:
    if pd.isna(offset):
        return "not_reached"
    value = int(offset)
    if value <= 5:
        return "t3_t5"
    if value <= 10:
        return "t6_t10"
    if value <= 20:
        return "t11_t20"
    return "t21_t30"


def _fresh_count_bucket(count: int) -> str:
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    if count == 2:
        return "2"
    return "3plus"


def _family_key(values: list[str] | set[str]) -> str:
    vals = sorted(str(v) for v in values if str(v))
    return "|".join(vals) if vals else "none"


def _label_rows(df: pd.DataFrame) -> pd.Series:
    labels = pd.Series("neutral_path", index=df.index, dtype="object")
    invalid = ~_boolish(df["entry_valid"]) | ~_boolish(df["path_complete_120d"])
    bad = (
        _boolish(df["early_failure_flag"])
        | (_as_num(df["first_minus5_offset"]) <= 10)
        | (_as_num(df["max_loss_before_first_plus10"]) <= -0.06)
    )
    good = _boolish(df["hit_plus10_before_minus5"]) | df["path_quality_flag"].astype(str).isin(
        ["clean_continuation", "tradable_continuation"]
    )
    labels.loc[invalid] = "censored_or_invalid"
    labels.loc[~invalid & bad] = "bad_path"
    labels.loc[~invalid & ~bad & good] = "good_path"
    return labels


def _first_valid_offset(*values: Any) -> float:
    nums = [float(v) for v in values if pd.notna(v)]
    return min(nums) if nums else np.nan


def _readiness(config: dict[str, Any]) -> tuple[pd.DataFrame, bool, str]:
    checks: list[dict[str, Any]] = []

    def add(role: str, path_value: str, validation_status: str = "", row_count: Any = np.nan) -> None:
        path = topic_path(Path(path_value))
        exists = path.exists()
        status = "ready" if exists and validation_status not in {"failed", "missing"} else "blocked"
        reason = "" if status == "ready" else ("missing" if not exists else validation_status)
        checks.append(
            {
                "artifact_role": role,
                "artifact_path": path_value,
                "exists": bool(exists),
                "validation_status": validation_status,
                "row_count": row_count,
                "readiness_status": status,
                "failure_reason": reason,
            }
        )

    path_validation = config["upstream_path_query"]["validation"]
    precision_validation = config["upstream_precision"]["validation"]
    path_status = _read_json(path_validation).get("validation_status", "missing")
    precision_status = _read_json(precision_validation).get("validation_status", "missing")
    add("path_query_validation", path_validation, path_status)
    add("path_query_manifest", config["upstream_path_query"]["manifest"], "exists_only")
    add("precision_validation", precision_validation, precision_status)
    add("precision_manifest", config["upstream_precision"]["manifest"], "exists_only")
    add("precision_action_time_panel", config["upstream_precision"]["action_time_panel"], "exists_only")
    add("big_winner_manifest", config["upstream_big_winner"]["manifest"], "exists_only")
    add("big_winner_reference_events", config["upstream_big_winner"]["reference_events"], "exists_only")
    add("eligible_day_density_panel", config["upstream_big_winner"]["eligible_day_density_panel"], "exists_only")
    for item in config["frozen_families"]:
        signal_id = item["signal_id"]
        path = f"{config['upstream_path_query']['signal_dir']}/{signal_id}_120d_path.csv"
        row_count = np.nan
        p = topic_path(Path(path))
        if p.exists():
            row_count = sum(1 for _ in p.open("r", encoding="utf-8")) - 1
        add(f"path_csv_{signal_id}", path, "exists_only", row_count)

    df = pd.DataFrame(checks)
    ok = bool(
        df["exists"].all()
        and path_status == "passed"
        and precision_status == "passed"
        and df["readiness_status"].eq("ready").all()
    )
    if not ok:
        if not df["exists"].all():
            return df, False, "blocked_missing_required_input"
        return df, False, "blocked_upstream_validation_failed"
    return df, True, "ready"


def _load_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path_frames = []
    for item in config["frozen_families"]:
        signal_id = item["signal_id"]
        path = topic_path(Path(config["upstream_path_query"]["signal_dir"]) / f"{signal_id}_120d_path.csv")
        frame = pd.read_csv(path, usecols=PATH_COLS)
        frame = frame.loc[frame["signal_id"].astype(str).eq(signal_id)].copy()
        path_frames.append(frame)
    path_df = pd.concat(path_frames, ignore_index=True)
    path_df["signal_date"] = pd.to_datetime(path_df["signal_date"])
    path_df["entry_date"] = pd.to_datetime(path_df["entry_date"], errors="coerce")

    precision_cols = [
        "instrument_id",
        "trade_date",
        "split",
        "year",
        "condition_group_id",
        "family_id",
        "signal_occurs",
        "complete_h120_flag",
        "forward_close_peak_h120_return_from_close",
        "big_winner_forward_from_signal_close",
        "forward_close_peak_h120_return_from_next_open",
        "big_winner_forward_from_next_open",
    ]
    precision = pd.read_parquet(topic_path(Path(config["upstream_precision"]["action_time_panel"])), columns=precision_cols)
    precision["trade_date"] = pd.to_datetime(precision["trade_date"])
    precision = precision.loc[_boolish(precision["signal_occurs"])].copy()

    refs = pd.read_parquet(topic_path(Path(config["upstream_big_winner"]["reference_events"])))
    refs["reference_date"] = pd.to_datetime(refs["reference_date"])
    refs["profile_window_end"] = pd.to_datetime(refs["profile_window_end"])

    calendar = pd.read_parquet(
        topic_path(Path(config["upstream_big_winner"]["eligible_day_density_panel"])),
        columns=["instrument_id", "trade_date", "split"],
    )
    calendar["trade_date"] = pd.to_datetime(calendar["trade_date"])
    return path_df, precision, refs, calendar


def _condition_dictionary(config: dict[str, Any], precision: pd.DataFrame) -> dict[str, str]:
    allowed = {item["family_id"] for item in config["frozen_families"]}
    out: dict[str, str] = {}
    for family in sorted(allowed):
        vals = sorted(precision.loc[precision["family_id"].eq(family), "condition_group_id"].dropna().astype(str).unique())
        if len(vals) != 1:
            raise RuntimeError(f"condition_group_id_not_unique_for_{family}: {vals}")
        out[family] = vals[0]
    return out


def _reconcile(path_df: pd.DataFrame, precision: pd.DataFrame, condition_map: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    path_df = path_df.copy()
    path_df["condition_group_id"] = path_df["family_id"].map(condition_map)
    key_cols = ["instrument_id", "signal_date", "family_id", "condition_group_id"]
    path_keys = path_df[key_cols].drop_duplicates().rename(columns={"signal_date": "trade_date"})
    precision_keys = precision[["instrument_id", "trade_date", "family_id", "condition_group_id"]].drop_duplicates()
    merged = path_keys.merge(precision_keys, on=["instrument_id", "trade_date", "family_id", "condition_group_id"], how="outer", indicator=True)
    rows = []
    for family, condition in condition_map.items():
        part = merged.loc[merged["family_id"].eq(family)]
        rows.append(
            {
                "family_id": family,
                "condition_group_id": condition,
                "path_signal_count": int(path_keys["family_id"].eq(family).sum()),
                "precision_signal_occurs_count": int(precision_keys["family_id"].eq(family).sum()),
                "matched_signal_count": int(part["_merge"].eq("both").sum()),
                "path_only_count": int(part["_merge"].eq("left_only").sum()),
                "precision_only_count": int(part["_merge"].eq("right_only").sum()),
                "reconciliation_status": "passed"
                if not part["_merge"].isin(["left_only", "right_only"]).any()
                else "failed",
            }
        )
    audit = pd.DataFrame(rows)
    return path_df, audit, bool(audit["reconciliation_status"].eq("passed").all())


def _calendar_maps(calendar: pd.DataFrame) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for inst, g in calendar.sort_values(["instrument_id", "trade_date"]).groupby("instrument_id", sort=False):
        dates = list(g["trade_date"])
        out[str(inst)] = {
            "dates": dates,
            "date_to_idx": {d: i for i, d in enumerate(dates)},
            "split_by_date": dict(zip(g["trade_date"], g["split"])),
        }
    return out


def _date_at(cal: dict[str, Any], date: pd.Timestamp, offset: int) -> pd.Timestamp | pd.NaT:
    idx = cal["date_to_idx"].get(date)
    if idx is None:
        return pd.NaT
    target = idx + offset
    if target >= len(cal["dates"]):
        return pd.NaT
    return cal["dates"][target]


def _offset(cal: dict[str, Any], seed_date: pd.Timestamp, date: pd.Timestamp) -> float:
    seed_idx = cal["date_to_idx"].get(seed_date)
    idx = cal["date_to_idx"].get(date)
    if seed_idx is None or idx is None:
        return np.nan
    return float(idx - seed_idx)


def _same_day_events(path_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (inst, date), g in path_df.sort_values(["instrument_id", "signal_date", "family_id", "signal_id"]).groupby(
        ["instrument_id", "signal_date"], sort=False
    ):
        families = sorted(g["family_id"].astype(str).unique())
        first = g.iloc[0].to_dict()
        row = {
            "instrument_id": inst,
            "signal_date": date,
            "same_day_family_set": _family_key(families),
            "same_day_family_count": len(families),
            "same_day_bundle_key": _family_key(families),
            "seed_row_signal_id": first["signal_id"],
            "seed_row_family_id": first["family_id"],
        }
        for col in CONSISTENCY_COLS:
            nunique = g[col].nunique(dropna=False)
            if nunique > 1:
                raise RuntimeError(f"seed_same_day_inconsistent_{col}_{inst}_{date.date()}")
            row[col] = first[col]
        rows.append(row)
    return pd.DataFrame(rows)


def _build_seeds(events: pd.DataFrame, cal_maps: dict[str, dict[str, Any]], window: int) -> pd.DataFrame:
    rows = []
    for inst, g in events.sort_values(["instrument_id", "signal_date"]).groupby("instrument_id", sort=False):
        cal = cal_maps.get(str(inst))
        if not cal:
            continue
        active_end_idx = -1
        for row in g.itertuples(index=False):
            idx = cal["date_to_idx"].get(row.signal_date)
            if idx is None or idx <= active_end_idx:
                continue
            active_end_idx = idx + window
            seed_id = _sha1_id(row.instrument_id, pd.Timestamp(row.signal_date).strftime("%Y-%m-%d"), row.same_day_bundle_key)
            payload = row._asdict()
            payload.update(
                {
                    "seed_episode_id": seed_id,
                    "seed_trade_date": row.signal_date,
                    "seed_family_set": row.same_day_family_set,
                    "seed_same_day_family_count": int(row.same_day_family_count),
                    "seed_same_day_bundle_key": row.same_day_bundle_key,
                    "seed_entry_date": row.entry_date,
                    "seed_entry_price": row.entry_price,
                    "year": int(pd.Timestamp(row.signal_date).year),
                    "seed_t30_date": _date_at(cal, row.signal_date, 30),
                    "seed_t120_date": _date_at(cal, row.signal_date, 120),
                }
            )
            rows.append(payload)
    seeds = pd.DataFrame(rows)
    seeds["label"] = _label_rows(seeds)
    seeds["observable_failure_offset"] = [
        _first_valid_offset(a, b) for a, b in zip(seeds["first_minus5_offset"], seeds["first_close_minus5_offset"])
    ]
    return seeds


def _attach_big_winner_labels(seeds: pd.DataFrame, precision: pd.DataFrame) -> pd.DataFrame:
    label_cols = [
        "complete_h120_flag",
        "forward_close_peak_h120_return_from_close",
        "big_winner_forward_from_signal_close",
        "forward_close_peak_h120_return_from_next_open",
        "big_winner_forward_from_next_open",
    ]
    grouped = precision.groupby(["instrument_id", "trade_date"], sort=False)[label_cols].agg(lambda x: x.dropna().unique()[0] if len(x.dropna().unique()) else np.nan)
    nunique = precision.groupby(["instrument_id", "trade_date"], sort=False)[label_cols].nunique(dropna=False)
    if bool(nunique.gt(1).any(axis=1).any()):
        raise RuntimeError("precision_label_not_row_independent")
    labels = grouped.reset_index().rename(columns={"trade_date": "seed_trade_date"})
    out = seeds.merge(labels, on=["instrument_id", "seed_trade_date"], how="left")
    out = out.rename(
        columns={
            "complete_h120_flag": "complete_h120_close_anchor_flag",
            "forward_close_peak_h120_return_from_close": "forward_close_peak_h120_return_from_seed_close",
            "big_winner_forward_from_signal_close": "big_winner_forward_h120_close_anchor",
            "forward_close_peak_h120_return_from_next_open": "forward_close_peak_h120_return_from_seed_next_open",
            "big_winner_forward_from_next_open": "big_winner_forward_h120_next_open_anchor",
        }
    )
    return out


def _attach_reference_audit(seeds: pd.DataFrame, refs: pd.DataFrame) -> pd.DataFrame:
    by_inst = {inst: g.copy() for inst, g in refs.groupby("instrument_id", sort=False)}
    out = seeds.copy()
    vals_30 = []
    vals_120 = []
    inside = []
    for row in out.itertuples(index=False):
        g = by_inst.get(row.instrument_id)
        if g is None:
            vals_30.append(False)
            vals_120.append(False)
            inside.append(False)
            continue
        seed_date = pd.Timestamp(row.seed_trade_date)
        t30 = pd.Timestamp(row.seed_t30_date) if pd.notna(row.seed_t30_date) else seed_date
        t120 = pd.Timestamp(row.seed_t120_date) if pd.notna(row.seed_t120_date) else seed_date
        vals_30.append(bool(((g["reference_date"] >= seed_date) & (g["reference_date"] <= t30)).any()))
        vals_120.append(bool(((g["reference_date"] >= seed_date) & (g["reference_date"] <= t120)).any()))
        inside.append(bool(((g["reference_date"] <= seed_date) & (g["profile_window_end"] >= seed_date)).any()))
    out["canonical_ref_after_seed_within_30td"] = vals_30
    out["canonical_ref_after_seed_within_120td"] = vals_120
    out["seed_inside_canonical_ref_t0_t30_window"] = inside
    return out


def _build_sequence_panels(
    seeds: pd.DataFrame,
    path_df: pd.DataFrame,
    cal_maps: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, list[dict[str, Any]]]]:
    seq = config["sequence"]
    start = int(seq["sequence_window_start_offset"])
    end = int(seq["sequence_window_end_offset"])
    fresh_start = int(seq["primary_fresh_start_offset"])
    fresh_end = int(seq["primary_fresh_end_offset"])
    timeline_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    clean_steps: dict[str, list[dict[str, Any]]] = {}
    signals_by_inst = {inst: g.sort_values(["signal_date", "family_id", "signal_id"]).copy() for inst, g in path_df.groupby("instrument_id", sort=False)}

    for seed in seeds.sort_values(["instrument_id", "seed_trade_date"]).itertuples(index=False):
        cal = cal_maps.get(seed.instrument_id)
        sigs = signals_by_inst.get(seed.instrument_id)
        if cal is None or sigs is None:
            clean_steps[seed.seed_episode_id] = []
            continue
        seed_idx = cal["date_to_idx"].get(seed.seed_trade_date)
        if seed_idx is None:
            clean_steps[seed.seed_episode_id] = []
            continue
        seed_families = set(str(seed.seed_family_set).split("|"))
        cumulative = set(seed_families)
        seed_clean_steps: list[dict[str, Any]] = []
        candidate = sigs.loc[(sigs["signal_date"] > seed.seed_trade_date)].copy()
        if candidate.empty:
            clean_steps[seed.seed_episode_id] = []
            continue
        candidate["offset_from_seed"] = pd.Series(
            [_offset(cal, seed.seed_trade_date, d) for d in candidate["signal_date"]],
            index=candidate.index,
            dtype="float64",
        )
        candidate = candidate.loc[(candidate["offset_from_seed"] >= start) & (candidate["offset_from_seed"] <= end)]
        step_index = 0
        for date, g in candidate.groupby("signal_date", sort=True):
            step_index += 1
            offset = int(g["offset_from_seed"].iloc[0])
            all_families = sorted(g["family_id"].astype(str).unique())
            non_seed_new = sorted([f for f in all_families if f not in cumulative and f not in seed_families])
            available = pd.notna(seed.available_forward_trading_days) and float(seed.available_forward_trading_days) >= offset
            valid_entry = bool(str(seed.entry_valid).lower() in {"true", "1", "yes"})
            failure = seed.observable_failure_offset
            has_failure = pd.notna(failure)
            if not valid_entry or not available:
                status = "censored_before_step"
                included = False
                added = []
            elif offset < fresh_start or offset > fresh_end:
                status = "outside_primary_fresh_window"
                included = False
                added = []
            elif has_failure and offset > float(failure):
                status = "after_observable_failure"
                included = False
                added = []
            elif has_failure and offset == int(float(failure)):
                status = "ambiguous_same_offset"
                included = False
                added = []
            elif not non_seed_new:
                status = "same_family_repeat_audit_only"
                included = False
                added = []
            else:
                included = True
                added = non_seed_new
                status = "same_offset_multi_family_step" if len(added) > 1 else "fresh_distinct_family_step"
                cumulative.update(added)
                clean_step = {
                    "seed_episode_id": seed.seed_episode_id,
                    "step_offset": offset,
                    "step_signal_date": date,
                    "added_family_set": _family_key(added),
                    "added_family_count": len(added),
                    "kth_fresh_step_index": len(seed_clean_steps) + 1,
                }
                seed_clean_steps.append(clean_step)

            step_rows.append(
                {
                    "seed_episode_id": seed.seed_episode_id,
                    "sequence_step_index": step_index,
                    "step_signal_date": date,
                    "step_offset": offset,
                    "added_family_set": _family_key(added if included else non_seed_new),
                    "added_family_count": len(added if included else non_seed_new),
                    "cumulative_distinct_family_set": _family_key(cumulative),
                    "cumulative_distinct_family_count": len(cumulative),
                    "is_same_offset_multi_family_step": len(non_seed_new) > 1,
                    "step_status": status,
                    "included_in_primary_fresh_count": included,
                    "split": seed.split,
                    "instrument_id": seed.instrument_id,
                }
            )
            for sig in g.itertuples(index=False):
                timeline_rows.append(
                    {
                        "seed_episode_id": seed.seed_episode_id,
                        "instrument_id": seed.instrument_id,
                        "signal_date": sig.signal_date,
                        "offset_from_seed": offset,
                        "family_id": sig.family_id,
                        "signal_id": sig.signal_id,
                        "condition_group_id": sig.condition_group_id,
                        "step_status": status,
                        "included_in_primary_fresh_count": bool(included and sig.family_id in added),
                        "split": seed.split,
                    }
                )
        clean_steps[seed.seed_episode_id] = seed_clean_steps
    return pd.DataFrame(timeline_rows), pd.DataFrame(step_rows), clean_steps


def _build_checkpoint_panel(seeds: pd.DataFrame, clean_steps: dict[str, list[dict[str, Any]]], checkpoints: list[int]) -> pd.DataFrame:
    rows = []
    for seed in seeds.itertuples(index=False):
        steps = clean_steps.get(seed.seed_episode_id, [])
        seed_families = str(seed.seed_family_set).split("|") if pd.notna(seed.seed_family_set) else []
        for chk in checkpoints:
            valid_entry = bool(str(seed.entry_valid).lower() in {"true", "1", "yes"})
            available = pd.notna(seed.available_forward_trading_days) and float(seed.available_forward_trading_days) >= chk
            failure = seed.observable_failure_offset
            has_failure = pd.notna(failure)
            at_risk = valid_entry and available and (not has_failure or float(failure) > chk)
            clean = [s for s in steps if int(s["step_offset"]) <= chk]
            fresh_count = sum(int(s["added_family_count"]) for s in clean)
            if not valid_entry or not available:
                state = "censored_before_checkpoint"
            elif has_failure and float(failure) <= chk:
                state = "ambiguous_same_offset" if any(int(s["step_offset"]) == int(float(failure)) for s in steps) else "failed_before_checkpoint"
            elif fresh_count:
                state = "survived_with_fresh"
            else:
                state = "survived_no_fresh"
            rows.append(
                {
                    "seed_episode_id": seed.seed_episode_id,
                    "split": seed.split,
                    "instrument_id": seed.instrument_id,
                    "checkpoint": f"T+{chk}",
                    "checkpoint_offset": chk,
                    "checkpoint_state": state,
                    "fresh_distinct_family_count_before_or_at_checkpoint": fresh_count,
                    "fresh_distinct_family_count_bucket": _fresh_count_bucket(fresh_count),
                    "cumulative_distinct_family_count_before_or_at_checkpoint": len(seed_families) + fresh_count,
                    "kth_fresh_reached_before_or_at_checkpoint": len(clean),
                    "fresh_family_sequence_before_or_at_checkpoint": " -> ".join(s["added_family_set"] for s in clean) if clean else "seed_only",
                    "failed_before_checkpoint": state in {"failed_before_checkpoint", "ambiguous_same_offset"},
                    "censored_before_checkpoint": state == "censored_before_checkpoint",
                    "at_risk_at_checkpoint": at_risk,
                }
            )
    return pd.DataFrame(rows)


def _metric_row(df: pd.DataFrame, split: str, conditioning_state: str, conditioning_key: str, thresholds: dict[str, int], ci_level: float) -> dict[str, Any]:
    part = df if split == "all" else df.loc[df["split"].eq(split)]
    seed_count = int(len(part))
    bw_den = int(_boolish(part.get("complete_h120_close_anchor_flag", pd.Series(dtype=object))).sum()) if seed_count else 0
    bw_count = int((_boolish(part.get("complete_h120_close_anchor_flag", pd.Series(dtype=object))) & _boolish(part.get("big_winner_forward_h120_close_anchor", pd.Series(dtype=object)))).sum()) if seed_count else 0
    bw_lower, bw_upper = _ci(bw_count, bw_den, ci_level)
    labeled = part.loc[part["label"].isin(LABELS)] if seed_count else pd.DataFrame(columns=part.columns)
    path_den = int(len(labeled))
    good = int(labeled["label"].eq("good_path").sum()) if path_den else 0
    bad = int(labeled["label"].eq("bad_path").sum()) if path_den else 0
    neutral = int(labeled["label"].eq("neutral_path").sum()) if path_den else 0
    good_lower, good_upper = _ci(good, path_den, ci_level)
    bad_lower, bad_upper = _ci(bad, path_den, ci_level)
    denom_for_status = min(x for x in [bw_den, path_den] if x >= 0)
    return {
        "split": split,
        "year": "all",
        "conditioning_state": conditioning_state,
        "conditioning_key": conditioning_key,
        "seed_episode_count": seed_count,
        "big_winner_label_denominator": bw_den,
        "big_winner_count_close_anchor": bw_count,
        "big_winner_rate_close_anchor": _safe_div(bw_count, bw_den),
        "big_winner_rate_close_anchor_lower": bw_lower,
        "big_winner_rate_close_anchor_upper": bw_upper,
        "path_label_denominator": path_den,
        "good_count": good,
        "bad_count": bad,
        "neutral_count": neutral,
        "P_good": _safe_div(good, path_den),
        "P_bad": _safe_div(bad, path_den),
        "P_neutral": _safe_div(neutral, path_den),
        "P_good_lower": good_lower,
        "P_good_upper": good_upper,
        "P_bad_lower": bad_lower,
        "P_bad_upper": bad_upper,
        "censored_or_invalid_count": int(part["label"].eq("censored_or_invalid").sum()) if seed_count else 0,
        "failed_before_condition_count": int(part.get("failed_before_condition_flag", pd.Series(False, index=part.index)).sum()) if seed_count else 0,
        "sample_sufficiency_status": _sample_status(denom_for_status, thresholds),
    }


def _summarize_groups(df: pd.DataFrame, group_cols: list[str], thresholds: dict[str, int], ci_level: float) -> pd.DataFrame:
    rows = []
    for split in ALL_SPLITS:
        base = df if split == "all" else df.loc[df["split"].eq(split)]
        if base.empty:
            continue
        for keys, group in base.groupby(group_cols, dropna=False, sort=True):
            if not isinstance(keys, tuple):
                keys = (keys,)
            state = "|".join(f"{col}={val}" for col, val in zip(group_cols, keys))
            key = "|".join(str(v) for v in keys)
            rows.append(_metric_row(group, split, state, key, thresholds, ci_level))
    return pd.DataFrame(rows)


def _seed_summary(seeds: pd.DataFrame, clean_steps: dict[str, list[dict[str, Any]]], thresholds: dict[str, int], ci_level: float) -> pd.DataFrame:
    rows = []
    base = seeds.copy()
    base["failed_before_condition_flag"] = False
    for split in ALL_SPLITS:
        part = base if split == "all" else base.loc[base["split"].eq(split)]
        row = _metric_row(part, split, "seed_base", "seed_base", thresholds, ci_level)
        fresh = part["seed_episode_id"].map(lambda x: len(clean_steps.get(x, [])) > 0)
        failure = pd.to_numeric(part["observable_failure_offset"], errors="coerce")
        first_fresh = part["seed_episode_id"].map(lambda x: clean_steps.get(x, [{}])[0].get("step_offset", np.nan) if clean_steps.get(x) else np.nan)
        row.update(
            {
                "no_fresh_episode_count": int((~fresh).sum()),
                "fresh_episode_count": int(fresh.sum()),
                "failed_before_first_primary_fresh_count": int((failure.notna() & (first_fresh.isna() | (failure < first_fresh))).sum()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _checkpoint_summary(seeds: pd.DataFrame, checkpoint: pd.DataFrame, thresholds: dict[str, int], ci_level: float) -> pd.DataFrame:
    merged = checkpoint.merge(seeds, on=["seed_episode_id", "split", "instrument_id"], how="left")
    merged = merged.loc[merged["at_risk_at_checkpoint"].astype(bool)].copy()
    merged["failed_before_condition_flag"] = False
    return _summarize_groups(merged, ["checkpoint", "fresh_distinct_family_count_bucket"], thresholds, ci_level)


def _kth_summary(seeds: pd.DataFrame, clean_steps: dict[str, list[dict[str, Any]]], thresholds: dict[str, int], ci_level: float) -> pd.DataFrame:
    rows = []
    for seed in seeds.itertuples(index=False):
        steps = clean_steps.get(seed.seed_episode_id, [])
        failure = seed.observable_failure_offset
        for kth in [1, 2, 3, 4]:
            if len(steps) >= kth:
                step = steps[kth - 1]
                status = "reached"
                offset = int(step["step_offset"])
                key = step["added_family_set"]
                count = int(step["added_family_count"])
                pre_state = "survived_before_kth"
                failed = False
            else:
                status = "not_reached"
                offset = np.nan
                key = "not_reached"
                count = 0
                pre_state = "failed_or_no_clean_primary_fresh" if pd.notna(failure) else "survived_no_kth_fresh"
                failed = pd.notna(failure)
            payload = seed._asdict()
            payload.update(
                {
                    "kth_fresh_step_index": "4plus" if kth == 4 else str(kth),
                    "kth_fresh_status": status,
                    "kth_fresh_offset_bucket": _offset_bucket(offset),
                    "kth_fresh_added_family_key": key,
                    "kth_fresh_added_family_count": count,
                    "pre_kth_step_survival_state": pre_state,
                    "failed_before_condition_flag": failed,
                }
            )
            rows.append(payload)
    df = pd.DataFrame(rows)
    return _summarize_groups(
        df,
        ["kth_fresh_step_index", "kth_fresh_status", "kth_fresh_offset_bucket", "kth_fresh_added_family_key", "kth_fresh_added_family_count", "pre_kth_step_survival_state"],
        thresholds,
        ci_level,
    )


def _pattern_summary(seeds: pd.DataFrame, checkpoint: pd.DataFrame, clean_steps: dict[str, list[dict[str, Any]]], config: dict[str, Any], thresholds: dict[str, int], ci_level: float) -> pd.DataFrame:
    top_k = int(config["sequence"]["top_k_patterns_by_denominator"])
    pattern_rows = []
    for chk in checkpoint.itertuples(index=False):
        seed = seeds.loc[seeds["seed_episode_id"].eq(chk.seed_episode_id)].iloc[0]
        steps = [s for s in clean_steps.get(chk.seed_episode_id, []) if int(s["step_offset"]) <= int(chk.checkpoint_offset)]
        pattern = "seed:" + ("multi_family_bundle" if int(seed.seed_same_day_family_count) > 1 else str(seed.seed_family_set))
        for step in steps:
            pattern += " -> fresh:" + str(step["added_family_set"])
        pattern_rows.append({"seed_episode_id": chk.seed_episode_id, "checkpoint": chk.checkpoint, "sequence_pattern_raw": pattern, "sequence_depth": len(steps)})
    pat = pd.DataFrame(pattern_rows)
    merged = checkpoint.merge(pat, on=["seed_episode_id", "checkpoint"], how="left").merge(seeds, on=["seed_episode_id", "split", "instrument_id"], how="left")
    count = merged.groupby(["checkpoint", "sequence_pattern_raw"], sort=False).size().reset_index(name="den")
    count["rank"] = count.groupby("checkpoint")["den"].rank(method="first", ascending=False)
    keep = set(count.loc[count["rank"] <= top_k, ["checkpoint", "sequence_pattern_raw"]].itertuples(index=False, name=None))
    merged["sequence_pattern"] = [
        raw if (chk, raw) in keep else "other_sparse_patterns"
        for chk, raw in zip(merged["checkpoint"], merged["sequence_pattern_raw"])
    ]
    merged["sequence_pattern_truncated"] = merged["sequence_pattern"].eq("other_sparse_patterns")
    merged = merged.loc[merged["at_risk_at_checkpoint"].astype(bool)].copy()
    merged["failed_before_condition_flag"] = False
    return _summarize_groups(merged, ["checkpoint", "sequence_pattern", "sequence_pattern_truncated", "sequence_depth"], thresholds, ci_level)


def _offset_hazard(seeds: pd.DataFrame, clean_steps: dict[str, list[dict[str, Any]]], config: dict[str, Any]) -> pd.DataFrame:
    fresh_start = int(config["sequence"]["primary_fresh_start_offset"])
    fresh_end = int(config["sequence"]["primary_fresh_end_offset"])
    rows = []
    event_rows = []
    for seed in seeds.itertuples(index=False):
        seed_families = set(str(seed.seed_family_set).split("|"))
        for step in clean_steps.get(seed.seed_episode_id, []):
            for fam in str(step["added_family_set"]).split("|"):
                event_rows.append(
                    {
                        "seed_episode_id": seed.seed_episode_id,
                        "offset": int(step["step_offset"]),
                        "fresh_family_id": fam,
                        "kth_fresh_step_index": "4plus" if int(step["kth_fresh_step_index"]) >= 4 else str(step["kth_fresh_step_index"]),
                    }
                )
        for split in [seed.split, "all"]:
            for offset in range(fresh_start, fresh_end + 1):
                valid_entry = bool(str(seed.entry_valid).lower() in {"true", "1", "yes"})
                available = pd.notna(seed.available_forward_trading_days) and float(seed.available_forward_trading_days) >= offset
                failure = seed.observable_failure_offset
                at_risk = valid_entry and available and (pd.isna(failure) or float(failure) > offset)
                for fam in FAMILY_ORDER:
                    if fam in seed_families:
                        continue
                    rows.append(
                        {
                            "split": split,
                            "offset": offset,
                            "fresh_family_id": fam,
                            "at_risk_seed": at_risk,
                            "failed_before_offset": valid_entry and pd.notna(failure) and float(failure) <= offset,
                            "censored_before_offset": (not valid_entry) or (not available),
                        }
                    )
    risk = pd.DataFrame(rows)
    events = pd.DataFrame(event_rows)
    if events.empty:
        events = pd.DataFrame(columns=["seed_episode_id", "offset", "fresh_family_id", "kth_fresh_step_index"])
    out_rows = []
    for split in ALL_SPLITS:
        rsplit = risk.loc[risk["split"].eq(split)]
        seeds_split = seeds if split == "all" else seeds.loc[seeds["split"].eq(split)]
        events_split = events.merge(seeds_split[["seed_episode_id"]], on="seed_episode_id", how="inner")
        for (offset, fam), g in rsplit.groupby(["offset", "fresh_family_id"], sort=True):
            ev = events_split.loc[events_split["offset"].eq(offset) & events_split["fresh_family_id"].eq(fam)]
            if ev.empty:
                out_rows.append(
                    {
                        "split": split,
                        "offset": offset,
                        "fresh_family_id": fam,
                        "kth_fresh_step_index": "none",
                        "at_risk_episode_count": int(g["at_risk_seed"].sum()),
                        "fresh_event_count": 0,
                        "fresh_hazard_rate": 0.0 if int(g["at_risk_seed"].sum()) else np.nan,
                        "failed_before_offset_count": int(g["failed_before_offset"].sum()),
                        "censored_before_offset_count": int(g["censored_before_offset"].sum()),
                    }
                )
            else:
                for kth, eg in ev.groupby("kth_fresh_step_index", sort=True):
                    den = int(g["at_risk_seed"].sum())
                    out_rows.append(
                        {
                            "split": split,
                            "offset": offset,
                            "fresh_family_id": fam,
                            "kth_fresh_step_index": kth,
                            "at_risk_episode_count": den,
                            "fresh_event_count": int(len(eg)),
                            "fresh_hazard_rate": _safe_div(len(eg), den),
                            "failed_before_offset_count": int(g["failed_before_offset"].sum()),
                            "censored_before_offset_count": int(g["censored_before_offset"].sum()),
                        }
                    )
    return pd.DataFrame(out_rows)


def _survival_bias(seeds: pd.DataFrame, clean_steps: dict[str, list[dict[str, Any]]]) -> pd.DataFrame:
    rows = []
    for split in ALL_SPLITS:
        part = seeds if split == "all" else seeds.loc[seeds["split"].eq(split)]
        failure = pd.to_numeric(part["observable_failure_offset"], errors="coerce")
        with_fresh = part["seed_episode_id"].map(lambda x: len(clean_steps.get(x, [])) > 0)
        buckets = {
            "failed_before_t3": failure.notna() & (failure < 3),
            "failed_t3_to_t5": failure.between(3, 5, inclusive="both"),
            "failed_t6_to_t10": failure.between(6, 10, inclusive="both"),
            "failed_t11_to_t20": failure.between(11, 20, inclusive="both"),
            "failed_t21_to_t30": failure.between(21, 30, inclusive="both"),
            "survived_t30_no_fresh": failure.isna() & (~with_fresh),
            "survived_t30_with_fresh": failure.isna() & with_fresh,
        }
        for bucket, mask in buckets.items():
            rows.append({"split": split, "survival_bias_bucket": bucket, "seed_episode_count": int(mask.sum())})
    return pd.DataFrame(rows)


def _audit_tables(seeds: pd.DataFrame, step: pd.DataFrame, timeline: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    same_offset = step.loc[step["is_same_offset_multi_family_step"].astype(bool), [
        "split",
        "seed_episode_id",
        "instrument_id",
        "step_signal_date",
        "step_offset",
        "added_family_set",
        "added_family_count",
        "step_status",
        "included_in_primary_fresh_count",
    ]].copy()
    repeats = timeline.loc[timeline["step_status"].eq("same_family_repeat_audit_only"), [
        "split",
        "seed_episode_id",
        "instrument_id",
        "signal_date",
        "offset_from_seed",
        "family_id",
        "signal_id",
        "included_in_primary_fresh_count",
    ]].copy()
    repeats["repeat_reason"] = "family_already_seen_in_seed_or_sequence"
    bw = seeds[[
        "split",
        "seed_episode_id",
        "instrument_id",
        "seed_trade_date",
        "seed_family_set",
        "seed_condition_group_set",
        "complete_h120_close_anchor_flag",
        "big_winner_forward_h120_close_anchor",
        "big_winner_forward_h120_next_open_anchor",
        "canonical_ref_after_seed_within_30td",
        "canonical_ref_after_seed_within_120td",
    ]].copy()
    bw["label_consistency_status"] = np.where(bw["complete_h120_close_anchor_flag"].astype(bool), "complete", "incomplete_h120")
    return same_offset, repeats, bw


def _final_report(
    seeds: pd.DataFrame,
    seed_summary: pd.DataFrame,
    checkpoint_summary: pd.DataFrame,
    pattern_summary: pd.DataFrame,
    survival_bias: pd.DataFrame,
    decision: str,
) -> str:
    base = seed_summary.loc[seed_summary["split"].eq("all")].iloc[0]
    train = seed_summary.loc[seed_summary["split"].eq("train")].iloc[0]
    best = checkpoint_summary.sort_values(["big_winner_rate_close_anchor", "big_winner_label_denominator"], ascending=[False, False]).head(5)
    sparse = pattern_summary.loc[pattern_summary["sample_sufficiency_status"].ne("sufficient")].head(10)
    failed_total = int(survival_bias.loc[survival_bias["survival_bias_bucket"].str.startswith("failed"), "seed_episode_count"].sum())
    lines = [
        "# R03b 信号序列 Big-Winner 与路径诊断报告",
        "",
        f"Final decision: `{decision}`",
        "",
        "## 结论边界",
        "",
        "本诊断明确区分 big-winner labels 和 path labels。",
        "P_good / P_bad 不得解读为 P(big winner | signal)。",
        "本实验不产出 production signal。",
        "本实验不产出 position size。",
        "本实验不产出 R03 risk-budget allocation。",
        "",
        "## Seed Base Rate",
        "",
        f"- all split seed episodes: {int(base.seed_episode_count):,}",
        f"- all split big_winner_rate_close_anchor: {base.big_winner_rate_close_anchor:.4f} ({int(base.big_winner_count_close_anchor):,}/{int(base.big_winner_label_denominator):,})",
        f"- all split P_good / P_bad: {base.P_good:.4f} / {base.P_bad:.4f}",
        f"- train seed episodes: {int(train.seed_episode_count):,}",
        "",
        "## Checkpoint Fresh Count",
        "",
    ]
    if not best.empty:
        lines.append(best[["split", "conditioning_state", "seed_episode_count", "big_winner_label_denominator", "big_winner_rate_close_anchor", "P_good", "P_bad", "sample_sufficiency_status"]].to_markdown(index=False))
    lines.extend(
        [
            "",
            "## Survival Bias",
            "",
            f"- survival-bias audit 中 failed bucket 的累计计数为 {failed_total:,}。这些 episode 先触发 observable failure，不能被解释为没有后续信号支持。",
            "",
            "## Sparse Pattern",
            "",
        ]
    )
    if sparse.empty:
        lines.append("- 没有发现 sample_sufficiency_status 非 sufficient 的前排 pattern。")
    else:
        lines.append(sparse[["split", "conditioning_state", "seed_episode_count", "sample_sufficiency_status"]].to_markdown(index=False))
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "后续如果要形成候选规则，必须另开 validation protocol；本报告只能用于描述 sequence diagnostic。",
        ]
    )
    return "\n".join(lines) + "\n"


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(Path(config["output_root"]))
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for path in [cache_dir, reports_dir, manifests_dir]:
        path.mkdir(parents=True, exist_ok=True)

    readiness, ok, decision = _readiness(config)
    _write_csv(readiness, reports_dir / "r03b_input_readiness_audit.csv")
    if not ok:
        manifest = {
            "requirement_id": config["requirement_id"],
            "final_decision": decision,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(manifest, manifests_dir / "r03b_signal_sequence_big_winner_path_manifest.json")
        return manifest

    path_df, precision, refs, calendar = _load_inputs(config)
    condition_map = _condition_dictionary(config, precision)
    path_df, reconciliation, recon_ok = _reconcile(path_df, precision, condition_map)
    _write_csv(reconciliation, reports_dir / "r03b_input_reconciliation_audit.csv")
    if not recon_ok:
        manifest = {
            "requirement_id": config["requirement_id"],
            "final_decision": "blocked_input_reconciliation_failed",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(manifest, manifests_dir / "r03b_signal_sequence_big_winner_path_manifest.json")
        return manifest

    cal_maps = _calendar_maps(calendar)
    events = _same_day_events(path_df)
    seeds = _build_seeds(events, cal_maps, int(config["sequence"]["active_build_window_trading_days"]))
    seeds["seed_condition_group_set"] = seeds["seed_family_set"].map(
        lambda s: _family_key([condition_map[f] for f in str(s).split("|")])
    )
    seeds = _attach_big_winner_labels(seeds, precision)
    seeds = _attach_reference_audit(seeds, refs)
    timeline, step, clean_steps = _build_sequence_panels(seeds, path_df, cal_maps, config)
    checkpoints = [int(x) for x in config["sequence"]["checkpoints"]]
    checkpoint = _build_checkpoint_panel(seeds, clean_steps, checkpoints)

    thresholds = {k: int(v) for k, v in config["sample_sufficiency"].items()}
    ci_level = float(config["posterior"]["credible_interval_level"])
    seed_summary = _seed_summary(seeds, clean_steps, thresholds, ci_level)
    checkpoint_summary = _checkpoint_summary(seeds, checkpoint, thresholds, ci_level)
    kth_summary = _kth_summary(seeds, clean_steps, thresholds, ci_level)
    pattern_summary = _pattern_summary(seeds, checkpoint, clean_steps, config, thresholds, ci_level)
    hazard = _offset_hazard(seeds, clean_steps, config)
    survival_bias = _survival_bias(seeds, clean_steps)
    same_offset, repeats, bw_audit = _audit_tables(seeds, step, timeline)

    _write_parquet(seeds, cache_dir / "r03b_seed_episode_panel.parquet")
    _write_parquet(timeline, cache_dir / "r03b_signal_timeline_panel.parquet")
    _write_parquet(step, cache_dir / "r03b_sequence_step_panel.parquet")
    _write_parquet(checkpoint, cache_dir / "r03b_checkpoint_state_panel.parquet")
    _write_parquet(hazard, cache_dir / "r03b_offset_hazard_panel.parquet")

    _write_csv(seed_summary, reports_dir / "r03b_seed_episode_label_summary.csv")
    _write_csv(checkpoint_summary, reports_dir / "r03b_checkpoint_fresh_count_summary.csv")
    _write_csv(kth_summary, reports_dir / "r03b_kth_fresh_summary.csv")
    _write_csv(pattern_summary, reports_dir / "r03b_sequence_pattern_summary.csv")
    _write_csv(hazard, reports_dir / "r03b_offset_hazard_summary.csv")
    _write_csv(survival_bias, reports_dir / "r03b_survival_bias_audit.csv")
    _write_csv(same_offset, reports_dir / "r03b_same_offset_multi_family_audit.csv")
    _write_csv(repeats, reports_dir / "r03b_same_family_repeat_audit.csv")
    _write_csv(bw_audit, reports_dir / "r03b_big_winner_label_audit.csv")

    decision = "descriptive_sequence_diagnostic_complete"
    report = _final_report(seeds, seed_summary, checkpoint_summary, pattern_summary, survival_bias, decision)
    (reports_dir / "r03b_sequence_big_winner_path_final_report.md").write_text(report, encoding="utf-8")

    manifest = {
        "requirement_id": config["requirement_id"],
        "short_name": config["short_name"],
        "final_decision": decision,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "episode_grain": "deterministic_episode_first_trigger",
        "frozen_families": config["frozen_families"],
        "condition_group_dictionary": condition_map,
        "splits": ALL_SPLITS,
        "checkpoints": checkpoints,
        "alpha_source": config["posterior"]["alpha_source"],
        "credible_interval_level": ci_level,
        "seed_episode_count": int(len(seeds)),
        "clean_primary_fresh_step_count": int(step["included_in_primary_fresh_count"].sum()) if not step.empty else 0,
        "input_hashes": {
            "config": _hash_file(topic_path(config_path)),
            "path_query_manifest": _hash_file(topic_path(Path(config["upstream_path_query"]["manifest"]))),
            "precision_manifest": _hash_file(topic_path(Path(config["upstream_precision"]["manifest"]))),
        },
    }
    write_json(manifest, manifests_dir / "r03b_signal_sequence_big_winner_path_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    manifest = run(args.config)
    print(json.dumps({"final_decision": manifest.get("final_decision"), "seed_episode_count": manifest.get("seed_episode_count")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

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

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP4_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_1_prior_probability_diagnostic_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
PATH_COLS = [
    "signal_id",
    "signal_type",
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
    "max_loss_before_first_plus10",
    "hit_plus10_before_minus5",
    "path_quality_flag",
    "early_failure_flag",
    "close_return_t20",
    "max_gain_120d",
    "max_loss_120d",
]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_json(value: Any, n: int = 16) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:n]


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    p = topic_path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _boolish(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _safe_div(numer: float, denom: float) -> float:
    return float(numer) / float(denom) if denom else np.nan


def _as_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _bucket_numeric(value: Any, buckets: dict[str, list[int]]) -> str:
    if pd.isna(value):
        return "none"
    v = float(value)
    for name, bounds in buckets.items():
        lo, hi = bounds
        if lo <= v <= hi:
            return name
    return "none"


def load_config(config_path: Path) -> dict[str, Any]:
    return _read_yaml(config_path)


def validate_frozen(config: dict[str, Any], path_config: dict[str, Any]) -> pd.DataFrame:
    frozen = pd.DataFrame(config["frozen_families"])
    upstream = pd.DataFrame(path_config["single_signals"])
    merged = frozen.merge(upstream, on=["family_id", "signal_id", "condition_group_id"], how="left", suffixes=("", "_upstream"))
    if merged["condition_text_upstream"].isna().any():
        raise RuntimeError("frozen family set does not match upstream path-query config")
    drift = merged["condition_text"].astype(str).ne(merged["condition_text_upstream"].astype(str))
    if drift.any():
        raise RuntimeError(f"frozen condition text drift: {merged.loc[drift, 'family_id'].tolist()}")
    return frozen


def load_single_path_rows(config: dict[str, Any], path_manifest: dict[str, Any]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for item in config["frozen_families"]:
        signal_id = item["signal_id"]
        path = topic_path(path_manifest["per_signal_csv_paths"][signal_id])
        header = pd.read_csv(path, nrows=0).columns
        cols = [c for c in PATH_COLS if c in header]
        df = pd.read_csv(path, usecols=cols, low_memory=False)
        df["family_id"] = item["family_id"]
        df["signal_id"] = signal_id
        df["condition_group_id"] = item["condition_group_id"]
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["signal_date"] = pd.to_datetime(out["signal_date"])
    out["trade_date"] = out["signal_date"]
    out["year"] = out["signal_date"].dt.year.astype(int)
    out["entry_valid_bool"] = _boolish(out["entry_valid"])
    out["path_complete_bool"] = _boolish(out["path_complete_120d"])
    out["early_failure_bool"] = _boolish(out["early_failure_flag"])
    out["hit_plus10_before_minus5_bool"] = _boolish(out["hit_plus10_before_minus5"])
    out["first_minus5_offset_num"] = _as_num(out["first_minus5_offset"])
    out["first_close_minus5_offset_num"] = _as_num(out["first_close_minus5_offset"])
    out["max_loss_before_first_plus10_num"] = _as_num(out["max_loss_before_first_plus10"])
    out["close_return_t20_num"] = _as_num(out["close_return_t20"])
    out["label"] = label_rows(out)
    out["label_denominator_flag"] = out["label"].isin(["good_path", "bad_path", "neutral_path"])
    return out


def label_rows(df: pd.DataFrame) -> pd.Series:
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


def _sample_status(label_denominator_count: int, n_min: int) -> str:
    if label_denominator_count >= n_min:
        return "sufficient"
    if label_denominator_count >= max(20, n_min // 4):
        return "thin_bucket_report_only"
    if label_denominator_count > 0:
        return "too_sparse_use_fallback"
    return "unusable"


def aggregate_prior(df: pd.DataFrame, group_cols: list[str], n_min: int, extra: dict[str, Any] | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if df.empty:
        return pd.DataFrame(columns=group_cols)
    grouped = df.groupby(group_cols, dropna=False, sort=True)
    for key, g in grouped:
        if not isinstance(key, tuple):
            key = (key,)
        row = {col: val for col, val in zip(group_cols, key)}
        row_count = int(len(g))
        den = int(g["label_denominator_flag"].sum())
        good = int((g["label"].eq("good_path") & g["label_denominator_flag"]).sum())
        bad = int((g["label"].eq("bad_path") & g["label_denominator_flag"]).sum())
        neutral = int((g["label"].eq("neutral_path") & g["label_denominator_flag"]).sum())
        censored = int(g["label"].eq("censored_or_invalid").sum())
        row.update(
            {
                "row_count": row_count,
                "label_denominator_count": den,
                "good_count": good,
                "bad_count": bad,
                "neutral_count": neutral,
                "censored_or_invalid_count": censored,
                "censored_or_invalid_rate": _safe_div(censored, row_count),
                "P_good": _safe_div(good, den),
                "P_bad": _safe_div(bad, den),
                "P_neutral": _safe_div(neutral, den),
                "P_good_plus_P_bad_plus_P_neutral": _safe_div(good + bad + neutral, den),
                "EV_R_diagnostic": np.nan,
                "sample_sufficiency_status": _sample_status(den, n_min),
            }
        )
        if extra:
            row.update(extra)
        rows.append(row)
    return pd.DataFrame(rows)


def build_bundle_rows(events: pd.DataFrame) -> pd.DataFrame:
    sort_cols = ["instrument_id", "trade_date", "family_id"]
    events = events.sort_values(sort_cols).reset_index(drop=True)
    path_identity_cols = [
        "entry_date",
        "entry_price",
        "entry_valid",
        "path_complete_120d",
        "available_forward_trading_days",
        "first_minus5_offset",
        "first_close_minus5_offset",
        "max_loss_before_first_plus10",
        "hit_plus10_before_minus5",
        "path_quality_flag",
        "early_failure_flag",
        "label",
    ]
    path_identity_cols = [col for col in path_identity_cols if col in events.columns]
    rows = []
    for (instrument_id, trade_date), g in events.groupby(["instrument_id", "trade_date"], sort=True):
        fams = sorted(g["family_id"].astype(str).unique().tolist())
        inconsistent = g[path_identity_cols].astype(str).nunique(dropna=False)
        inconsistent = inconsistent[inconsistent.gt(1)]
        if not inconsistent.empty:
            raise RuntimeError(
                "same-day bundle path fields differ across families: "
                f"instrument_id={instrument_id}, trade_date={trade_date}, fields={inconsistent.index.tolist()}"
            )
        base = g.iloc[0].to_dict()
        base["same_day_bundle_key"] = "|".join(fams)
        base["bundle_family_ids"] = "|".join(fams)
        base["same_day_family_count"] = len(fams)
        base["seed_same_day_bundle_key"] = base["same_day_bundle_key"]
        base["seed_same_day_family_count"] = base["same_day_family_count"]
        rows.append(base)
    out = pd.DataFrame(rows)
    out["context_bucket_id"] = (
        "bundle="
        + out["same_day_bundle_key"].astype(str)
        + "|split="
        + out["split"].astype(str)
        + "|year="
        + out["year"].astype(str)
        + "|family_count="
        + out["same_day_family_count"].astype(str)
        + "|risk=na"
    )
    out["entry_risk_pct_bucket"] = "na"
    return out


def build_ev_r_audit(events: pd.DataFrame) -> pd.DataFrame:
    fields = ["signal_day_low", "prior_10d_low", "prior_20d_low", "entry_price", "close_return_t20"]
    rows = []
    for field in fields:
        available = field in events.columns
        rows.append(
            {
                "field_name": field,
                "required_for_ev_r": field in {"signal_day_low", "prior_10d_low", "prior_20d_low", "entry_price", "close_return_t20"},
                "source_table_or_file": "r02_path_csv" if available else "",
                "source_column": field if available else "",
                "availability_status": "available" if available else "missing",
                "missing_reason": "" if available else "not_materialized_in_r02_path_csv",
                "affected_row_count": int(len(events)),
                "usable_row_count": int(events[field].notna().sum()) if available else 0,
            }
        )
    return pd.DataFrame(rows)


def build_global_prior(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for grain, split, year in [
        ("all", "all", "all"),
        ("split", "train", "all"),
        ("split", "validation", "all"),
        ("split", "robustness", "all"),
        ("year", "all", "all"),
        ("split x year", "all", "all"),
    ]:
        rows.append(
            {
                "global_prior_row_type": grain,
                "split": split,
                "year": year,
                "global_prior_status": "unavailable_background_path_not_materialized",
                "row_count": 0,
                "label_denominator_count": 0,
                "good_count": 0,
                "bad_count": 0,
                "neutral_count": 0,
                "censored_or_invalid_count": 0,
                "P_good": np.nan,
                "P_bad": np.nan,
                "P_neutral": np.nan,
                "EV_R_diagnostic": np.nan,
                "sample_sufficiency_status": "unusable",
            }
        )
    return pd.DataFrame(rows)


def build_context_prior(bundle: pd.DataFrame, n_min: int) -> pd.DataFrame:
    out = aggregate_prior(
        bundle,
        ["context_bucket_id", "same_day_bundle_key", "split", "year", "same_day_family_count", "entry_risk_pct_bucket"],
        n_min,
    )
    if out.empty:
        return out
    out["context_bucket_definition"] = out["context_bucket_id"]
    out["context_source_fields"] = "split|year|same_day_family_count|same_day_bundle_key|entry_risk_pct_bucket"
    out["context_field_status"] = "entry_risk_pct_bucket_unavailable_missing_ev_r"
    out["fallback_level"] = np.where(out["label_denominator_count"] >= n_min, "same_day_bundle_key", "same_day_family_count")
    return out


def build_bucket_fallback(context_prior: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if context_prior.empty:
        return pd.DataFrame()
    for row in context_prior.itertuples(index=False):
        fallback_level = getattr(row, "fallback_level")
        rows.append(
            {
                "original_bucket_key": getattr(row, "context_bucket_id"),
                "original_sample_count": int(getattr(row, "label_denominator_count")),
                "fallback_level": fallback_level,
                "fallback_bucket_key": (
                    f"family_count={getattr(row, 'same_day_family_count')}|split={getattr(row, 'split')}|year={getattr(row, 'year')}"
                    if fallback_level != "same_day_bundle_key"
                    else getattr(row, "context_bucket_id")
                ),
                "fallback_sample_count": int(getattr(row, "label_denominator_count")),
                "fallback_reason": "sufficient" if fallback_level == "same_day_bundle_key" else "bucket_below_n_min",
            }
        )
    return pd.DataFrame(rows)


def _survived_at(g: pd.DataFrame, k: int) -> pd.Series:
    entry_valid = g["entry_valid_bool"].astype(bool)
    enough = _as_num(g["available_forward_trading_days"]) >= k
    fm = g["first_minus5_offset_num"]
    fcm = g["first_close_minus5_offset_num"]
    no_low = fm.isna() | (fm > k)
    no_close = fcm.isna() | (fcm > k)
    return entry_valid & enough & no_low & no_close


def build_survival_prior(bundle: pd.DataFrame, checkpoints: list[int], n_min: int) -> pd.DataFrame:
    rows = []
    group_cols = ["same_day_bundle_key", "same_day_family_count", "context_bucket_id", "split", "year"]
    for k in checkpoints:
        for key, g in bundle.groupby(group_cols, dropna=False, sort=True):
            survivor = _survived_at(g, k)
            row = {col: val for col, val in zip(group_cols, key)}
            row["checkpoint"] = f"T+{k}"
            row["survival_definition_version"] = "entry_valid_and_no_minus5_before_or_at_checkpoint_v1"
            row["pre_checkpoint_row_count"] = int(len(g))
            row["survivor_count"] = int(survivor.sum())
            row["non_survivor_count"] = int((~survivor).sum())
            row["survivor_rate"] = _safe_div(row["survivor_count"], len(g))
            for prefix, part in [("survivor", g.loc[survivor]), ("non_survivor", g.loc[~survivor])]:
                den = int(part["label_denominator_flag"].sum()) if not part.empty else 0
                good = int((part["label"].eq("good_path") & part["label_denominator_flag"]).sum()) if not part.empty else 0
                bad = int((part["label"].eq("bad_path") & part["label_denominator_flag"]).sum()) if not part.empty else 0
                neutral = int((part["label"].eq("neutral_path") & part["label_denominator_flag"]).sum()) if not part.empty else 0
                row[f"{prefix}_label_denominator_count"] = den
                row[f"{prefix}_P_good"] = _safe_div(good, den)
                row[f"{prefix}_P_bad"] = _safe_div(bad, den)
                row[f"{prefix}_P_neutral"] = _safe_div(neutral, den)
                row[f"{prefix}_EV_R_diagnostic"] = np.nan
            base_den = int(g["label_denominator_flag"].sum())
            base_good = int((g["label"].eq("good_path") & g["label_denominator_flag"]).sum())
            base_bad = int((g["label"].eq("bad_path") & g["label_denominator_flag"]).sum())
            row["survival_lift_good_vs_pre_checkpoint"] = row["survivor_P_good"] - _safe_div(base_good, base_den)
            row["survival_lift_bad_vs_pre_checkpoint"] = row["survivor_P_bad"] - _safe_div(base_bad, base_den)
            row["sample_sufficiency_status"] = _sample_status(base_den, n_min)
            rows.append(row)
    return pd.DataFrame(rows)


def build_calendar_ordinals(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["upstream_eligible_day_density"]["panel"])
    cal = pd.read_parquet(path, columns=["instrument_id", "trade_date"])
    cal["trade_date"] = pd.to_datetime(cal["trade_date"])
    cal = cal.drop_duplicates(["instrument_id", "trade_date"]).sort_values(["instrument_id", "trade_date"])
    cal["date_ordinal"] = cal.groupby("instrument_id").cumcount()
    return cal


def _failure_offset(row: pd.Series) -> float:
    vals = []
    for col in ["first_minus5_offset_num", "first_close_minus5_offset_num"]:
        v = row.get(col, np.nan)
        if pd.notna(v):
            vals.append(float(v))
    return min(vals) if vals else np.nan


def _fresh_bucket(offset: Any, config: dict[str, Any]) -> str:
    if offset in {"none", "censored"}:
        return str(offset)
    return _bucket_numeric(offset, config["fresh_evidence"]["offset_buckets"])


def _failure_bucket(offset: Any, config: dict[str, Any]) -> str:
    if offset in {"none", "censored"} or pd.isna(offset):
        return "none"
    return _bucket_numeric(offset, config["fresh_evidence"]["failure_offset_buckets"])


def _survival_state(status: str, fresh_offset: Any, failure_offset: Any) -> str:
    if status == "seed_failed_before_t3":
        return "not_survived_t3"
    if status == "seed_failed_before_fresh":
        if pd.isna(failure_offset):
            return "censored_before_checkpoint"
        if failure_offset <= 3:
            return "not_survived_t3"
        if failure_offset <= 5:
            return "not_survived_t5"
        if failure_offset <= 10:
            return "not_survived_t10"
        return "survived_t10"
    if status == "censored_before_t30":
        return "censored_before_checkpoint"
    if status == "none_within_t3_t30":
        return "survived_t10" if (pd.isna(failure_offset) or failure_offset > 10) else "not_survived_t10"
    if isinstance(fresh_offset, (int, float, np.integer, np.floating)) and not pd.isna(fresh_offset):
        if fresh_offset >= 10:
            return "survived_t10"
        if fresh_offset >= 5:
            return "survived_t5"
        return "survived_t3"
    return "censored_before_checkpoint"


def build_fresh_rows(bundle: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    cal = build_calendar_ordinals(config)
    b = bundle.merge(cal, on=["instrument_id", "trade_date"], how="left")
    if b["date_ordinal"].isna().any():
        b["date_ordinal"] = b.groupby("instrument_id")["trade_date"].rank(method="dense").astype(int) - 1
    b = b.sort_values(["instrument_id", "date_ordinal", "same_day_bundle_key"]).reset_index(drop=True)
    rows = []
    min_off = int(config["fresh_evidence"]["min_offset"])
    max_off = int(config["fresh_evidence"]["max_offset"])
    for instrument_id, g in b.groupby("instrument_id", sort=True):
        g = g.sort_values("date_ordinal").reset_index(drop=True)
        next_allowed = -math.inf
        for idx, seed in g.iterrows():
            seed_ord = int(seed["date_ordinal"])
            if seed_ord <= next_allowed:
                continue
            next_allowed = seed_ord + max_off
            seed_fams = set(str(seed["same_day_bundle_key"]).split("|"))
            failure_offset = _failure_offset(seed)
            window = g.loc[(g["date_ordinal"] >= seed_ord + min_off) & (g["date_ordinal"] <= seed_ord + max_off)].copy()
            candidates = []
            for cand in window.itertuples(index=False):
                cand_fams = set(str(cand.same_day_bundle_key).split("|"))
                new_fams = sorted(cand_fams - seed_fams)
                if new_fams:
                    candidates.append((int(cand.date_ordinal - seed_ord), cand.trade_date, new_fams[0]))
            first_cand = min(candidates, key=lambda x: (x[0], str(x[2]))) if candidates else None
            status: str
            fresh_family_id: str
            fresh_signal_date: Any
            fresh_offset: Any
            seed_pre_state: str
            post_policy: str
            fresh_vs_state = "not_applicable"
            if pd.notna(failure_offset) and failure_offset < min_off:
                status = "seed_failed_before_t3"
                fresh_family_id = "none"
                fresh_signal_date = "none"
                fresh_offset = "none"
                seed_pre_state = "failed_before_t3"
                post_policy = "include_labeled"
            elif first_cand is not None:
                cand_offset, cand_date, cand_family = first_cand
                if pd.notna(failure_offset) and failure_offset < cand_offset:
                    status = "seed_failed_before_fresh"
                    fresh_family_id = "none"
                    fresh_signal_date = "none"
                    fresh_offset = "none"
                    seed_pre_state = "failed_before_fresh"
                    post_policy = "include_labeled"
                elif pd.notna(failure_offset) and failure_offset == cand_offset:
                    status = "ambiguous_same_offset"
                    fresh_family_id = cand_family
                    fresh_signal_date = pd.Timestamp(cand_date).date().isoformat()
                    fresh_offset = cand_offset
                    seed_pre_state = "ambiguous_same_offset"
                    post_policy = "audit_only_exclude"
                    fresh_vs_state = "ambiguous_same_offset"
                else:
                    status = "found_within_t3_t30"
                    fresh_family_id = cand_family
                    fresh_signal_date = pd.Timestamp(cand_date).date().isoformat()
                    fresh_offset = cand_offset
                    seed_pre_state = "alive_before_fresh"
                    post_policy = "include_labeled"
                    if pd.isna(failure_offset):
                        fresh_vs_state = "no_observable_failure"
                    elif cand_offset < failure_offset:
                        fresh_vs_state = "before_observable_failure"
                    elif cand_offset > failure_offset:
                        fresh_vs_state = "after_observable_failure"
                    else:
                        fresh_vs_state = "ambiguous_same_offset"
            else:
                enough = pd.notna(seed.get("available_forward_trading_days")) and float(seed.get("available_forward_trading_days")) >= max_off
                if pd.notna(failure_offset) and failure_offset <= max_off:
                    status = "seed_failed_before_fresh"
                    seed_pre_state = "failed_before_fresh"
                    fresh_signal_date = "none"
                    fresh_offset = "none"
                    fresh_family_id = "none"
                    post_policy = "include_labeled"
                elif enough:
                    status = "none_within_t3_t30"
                    seed_pre_state = "no_fresh_observed"
                    fresh_signal_date = "none"
                    fresh_offset = "none"
                    fresh_family_id = "none"
                    post_policy = "include_labeled"
                else:
                    status = "censored_before_t30"
                    seed_pre_state = "censored_before_fresh"
                    fresh_signal_date = "censored"
                    fresh_offset = "censored"
                    fresh_family_id = "censored"
                    post_policy = "censored_exclude"
            row = seed.to_dict()
            row.update(
                {
                    "seed_episode_id": _hash_json([instrument_id, str(seed["trade_date"]), seed["same_day_bundle_key"]], 16),
                    "seed_trade_date": pd.Timestamp(seed["trade_date"]).date().isoformat(),
                    "seed_split": seed["split"],
                    "seed_same_day_bundle_key": seed["same_day_bundle_key"],
                    "seed_same_day_family_count": int(seed["same_day_family_count"]),
                    "seed_label": seed["label"],
                    "fresh_family_id": fresh_family_id,
                    "fresh_signal_date": fresh_signal_date,
                    "fresh_offset": fresh_offset,
                    "fresh_offset_bucket": _fresh_bucket(fresh_offset, config),
                    "seed_failure_offset": "none" if pd.isna(failure_offset) else failure_offset,
                    "seed_failure_offset_bucket": _failure_bucket(failure_offset, config),
                    "fresh_vs_observable_failure_state": fresh_vs_state,
                    "fresh_evidence_status": status,
                    "seed_pre_fresh_state": seed_pre_state,
                    "posterior_denominator_policy": post_policy,
                    "survival_checkpoint_state": _survival_state(status, fresh_offset, failure_offset),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def build_fresh_prior(fresh: pd.DataFrame, n_min: int) -> pd.DataFrame:
    group_cols = [
        "fresh_evidence_status",
        "fresh_family_id",
        "fresh_offset_bucket",
        "seed_same_day_bundle_key",
        "seed_same_day_family_count",
        "seed_pre_fresh_state",
        "survival_checkpoint_state",
        "split",
        "year",
    ]
    f = fresh.copy()
    f["label_denominator_flag"] = f["posterior_denominator_policy"].eq("include_labeled") & f["label"].isin(["good_path", "bad_path", "neutral_path"])
    rows = []
    for key, g in f.groupby(group_cols, dropna=False, sort=True):
        row = {col: val for col, val in zip(group_cols, key)}
        den = int(g["label_denominator_flag"].sum())
        good = int((g["label"].eq("good_path") & g["label_denominator_flag"]).sum())
        bad = int((g["label"].eq("bad_path") & g["label_denominator_flag"]).sum())
        neutral = int((g["label"].eq("neutral_path") & g["label_denominator_flag"]).sum())
        numeric_fresh = pd.to_numeric(g["fresh_offset"], errors="coerce")
        rate_den = int(numeric_fresh.notna().sum())
        before = int(g["fresh_vs_observable_failure_state"].eq("before_observable_failure").sum())
        without_prior = int(g["fresh_vs_observable_failure_state"].isin(["before_observable_failure", "no_observable_failure"]).sum())
        row.update(
            {
                "row_count": int(len(g)),
                "label_denominator_count": den,
                "posterior_denominator_policy": "|".join(sorted(g["posterior_denominator_policy"].astype(str).unique())),
                "P_good": _safe_div(good, den),
                "P_bad": _safe_div(bad, den),
                "P_neutral": _safe_div(neutral, den),
                "EV_R_diagnostic": np.nan,
                "fresh_before_observable_failure_rate": _safe_div(before, rate_den),
                "fresh_without_prior_observable_failure_rate": _safe_div(without_prior, rate_den),
                "median_fresh_offset": float(numeric_fresh.median()) if numeric_fresh.notna().any() else np.nan,
                "sample_sufficiency_status": _sample_status(den, n_min),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


SPLIT_STABILITY_DIMS = {
    "single_family_prior": ["family_id", "signal_id"],
    "same_day_bundle_prior": ["same_day_bundle_key", "same_day_family_count"],
    "same_day_family_count_prior": ["same_day_family_count"],
    "context_bucket_prior": ["same_day_bundle_key", "same_day_family_count", "entry_risk_pct_bucket"],
    "survival_checkpoint_prior": ["checkpoint", "same_day_bundle_key", "same_day_family_count"],
    "fresh_evidence_prior": [
        "fresh_evidence_status",
        "fresh_family_id",
        "fresh_offset_bucket",
        "seed_same_day_bundle_key",
        "seed_same_day_family_count",
        "seed_pre_fresh_state",
        "survival_checkpoint_state",
    ],
}


def _split_metric_frame(grouping_type: str, df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if grouping_type == "survival_checkpoint_prior":
        work["P_good"] = work["survivor_P_good"]
        work["P_bad"] = work["survivor_P_bad"]
        work["EV_R_diagnostic"] = work["survivor_EV_R_diagnostic"]
        work["metric_denominator_count"] = work["survivor_label_denominator_count"]
    else:
        work["metric_denominator_count"] = work.get("label_denominator_count", 0)
    return work


def _weighted_metric(g: pd.DataFrame, metric: str) -> float:
    values = pd.to_numeric(g[metric], errors="coerce")
    weights = pd.to_numeric(g["metric_denominator_count"], errors="coerce").fillna(0)
    valid = values.notna() & weights.gt(0)
    if valid.any():
        return float((values[valid] * weights[valid]).sum() / weights[valid].sum())
    return float(values.mean()) if values.notna().any() else np.nan


def build_split_stability(tables: dict[str, pd.DataFrame], n_min_split: int) -> pd.DataFrame:
    rows = []
    for grouping_type, df in tables.items():
        if df.empty or "split" not in df.columns:
            rows.append({"grouping_type": grouping_type, "grouping_key": "missing", "stability_status": "missing_split"})
            continue
        work = _split_metric_frame(grouping_type, df)
        if not {"P_good", "P_bad", "EV_R_diagnostic", "metric_denominator_count"}.issubset(work.columns):
            rows.append({"grouping_type": grouping_type, "grouping_key": "missing_metric_columns", "stability_status": "missing_split"})
            continue
        dims = [col for col in SPLIT_STABILITY_DIMS.get(grouping_type, []) if col in work.columns]
        if not dims:
            rows.append({"grouping_type": grouping_type, "grouping_key": "missing_grouping_dims", "stability_status": "missing_split"})
            continue
        for key, g in work.groupby(dims, dropna=False, sort=True):
            if not isinstance(key, tuple):
                key = (key,)
            by_split_rows = []
            for split_name, part in g.groupby("split", dropna=False, sort=True):
                by_split_rows.append(
                    {
                        "split": split_name,
                        "P_good": _weighted_metric(part, "P_good"),
                        "P_bad": _weighted_metric(part, "P_bad"),
                        "EV_R_diagnostic": _weighted_metric(part, "EV_R_diagnostic"),
                        "metric_denominator_count": pd.to_numeric(part["metric_denominator_count"], errors="coerce").fillna(0).sum(),
                    }
                )
            by_split = pd.DataFrame(by_split_rows)
            vals = {str(r["split"]): r for _, r in by_split.iterrows()}
            row = {"grouping_type": grouping_type, "grouping_key": "|".join(f"{c}={v}" for c, v in zip(dims, key))}
            split_denominators = []
            for split in SPLITS:
                r = vals.get(split, {})
                row[f"{split}_P_good"] = r.get("P_good", np.nan) if isinstance(r, dict) else r["P_good"]
                row[f"{split}_P_bad"] = r.get("P_bad", np.nan) if isinstance(r, dict) else r["P_bad"]
                row[f"{split}_EV_R_diagnostic"] = r.get("EV_R_diagnostic", np.nan) if isinstance(r, dict) else r["EV_R_diagnostic"]
                if not isinstance(r, dict):
                    split_denominators.append(float(r["metric_denominator_count"]))
            p_good_values = [row[f"{s}_P_good"] for s in SPLITS if pd.notna(row[f"{s}_P_good"])]
            p_bad_values = [row[f"{s}_P_bad"] for s in SPLITS if pd.notna(row[f"{s}_P_bad"])]
            row["max_abs_P_good_drift"] = max(p_good_values) - min(p_good_values) if len(p_good_values) > 1 else np.nan
            row["max_abs_P_bad_drift"] = max(p_bad_values) - min(p_bad_values) if len(p_bad_values) > 1 else np.nan
            if len(p_good_values) < 2:
                status = "missing_split"
            elif split_denominators and min(split_denominators) < n_min_split:
                status = "insufficient_sample"
            elif max(row["max_abs_P_good_drift"], row["max_abs_P_bad_drift"]) > 0.20:
                status = "unstable_do_not_freeze"
            else:
                status = "stable_enough_for_requirement_input"
            row["stability_status"] = status
            rows.append(row)
    return pd.DataFrame(rows)


def build_readiness(
    global_available: bool,
    ev_available: bool,
    context_prior: pd.DataFrame,
    fresh: pd.DataFrame,
    split_stability: pd.DataFrame,
) -> pd.DataFrame:
    context_ready = "ready" if not context_prior.empty and (context_prior["sample_sufficiency_status"].eq("sufficient")).any() else "limited_use_coarser_bucket"
    fresh_ready = "ready" if not fresh.empty and fresh["fresh_evidence_status"].eq("found_within_t3_t30").any() else "blocked_missing_fresh_evidence"
    split_ready = "blocked_unstable_split" if split_stability["stability_status"].eq("unstable_do_not_freeze").any() else "ready"
    global_ready = "ready" if global_available else "blocked_missing_denominator"
    ev_ready = "ready" if ev_available else "blocked_missing_ev_r"
    blocker_priority = [ev_ready, global_ready, fresh_ready, split_ready]
    blockers = [v for v in blocker_priority if v != "ready"]
    primary = blockers[0] if blockers else "ready"
    secondary = "|".join(blockers[1:]) if len(blockers) > 1 else ""
    return pd.DataFrame(
        [
            {
                "readiness_scope": "r03_direct_posterior_table_v1",
                "global_prior_ready": global_ready,
                "single_family_prior_ready": "ready",
                "same_day_bundle_prior_ready": context_ready,
                "context_bucket_prior_ready": context_ready,
                "survival_checkpoint_prior_ready": "ready",
                "fresh_evidence_prior_ready": fresh_ready,
                "ev_r_ready": ev_ready,
                "split_stability_ready": split_ready,
                "recommended_r03_bucket_grain": "same_day_bundle_context" if context_ready == "ready" else "same_day_family_count_context",
                "recommended_build_window_status": "build_window_t30_supported" if fresh_ready == "ready" else "blocked_missing_fresh_distribution",
                "primary_blocker": primary,
                "secondary_blocker": secondary,
                "required_next_action": "materialize EV_R inputs and action-time path denominator before risk-budget R03" if blockers else "draft R03 requirement",
            }
        ]
    )


def write_report(output_root: Path, tables: dict[str, pd.DataFrame], manifest: dict[str, Any]) -> None:
    reports_dir = output_root / "reports"
    readiness = tables["readiness"]
    fallback_counts = tables["bucket_fallback_audit"]["fallback_level"].value_counts().rename_axis("fallback_level").reset_index(name="bucket_count")
    context_counts = tables["context_bucket_prior"]["sample_sufficiency_status"].value_counts().rename_axis("sample_sufficiency_status").reset_index(name="bucket_count")
    survival_summary = (
        tables["survival_checkpoint_prior"]
        .groupby("checkpoint", as_index=False)
        .agg(
            pre_checkpoint_row_count=("pre_checkpoint_row_count", "sum"),
            survivor_count=("survivor_count", "sum"),
            non_survivor_count=("non_survivor_count", "sum"),
            survivor_label_denominator_count=("survivor_label_denominator_count", "sum"),
            survivor_P_good=("survivor_P_good", "mean"),
            survivor_P_bad=("survivor_P_bad", "mean"),
        )
    )
    survival_summary["survivor_rate"] = survival_summary["survivor_count"] / survival_summary["pre_checkpoint_row_count"]
    fresh_offsets = tables["fresh_evidence_offset_distribution"]
    fresh_status_counts = fresh_offsets["fresh_evidence_status"].value_counts().rename_axis("fresh_evidence_status").reset_index(name="row_count")
    numeric_fresh = pd.to_numeric(fresh_offsets["fresh_offset"], errors="coerce")
    fresh_prior_status = (
        tables["fresh_evidence_prior"]
        .groupby("fresh_evidence_status", as_index=False)
        .agg(
            row_count=("row_count", "sum"),
            label_denominator_count=("label_denominator_count", "sum"),
            P_good=("P_good", "mean"),
            P_bad=("P_bad", "mean"),
            median_fresh_offset=("median_fresh_offset", "median"),
        )
    )
    split_counts = tables["split_stability_diagnostics"]["stability_status"].value_counts().rename_axis("stability_status").reset_index(name="row_count")
    lines = [
        "# R02.1 Prior Probability Diagnostic Report",
        "",
        "This is an exploratory prior diagnostic, not an entry strategy, not a staged-build experiment, and not R03 validation.",
        "",
        "## Scope",
        "",
        "The diagnostic uses the seven frozen R02 single-family signals and R02 next-open 120D path labels.",
        "",
        "## Availability",
        "",
        f"- Global action-time prior: `{manifest['global_action_time_prior_status']}`",
        f"- EV_R status: `{manifest['ev_r_status']}`",
        f"- Fresh evidence prior: `{manifest['fresh_evidence_prior_status']}`",
        "- Risk-budget R03 launch status: insufficient until EV_R inputs and action-time denominator are materialized.",
        "",
        "## Single Family Ranking",
        "",
    ]
    single = tables["single_family_prior"]
    rank = single.groupby("family_id", as_index=False).agg({"row_count": "sum", "label_denominator_count": "sum", "P_good": "mean", "P_bad": "mean"})
    rank = rank.sort_values(["P_bad", "P_good"], ascending=[True, False]).head(10)
    lines.extend(rank.to_markdown(index=False).splitlines())
    lines.extend(["", "## Same-Day Family Count", ""])
    count = tables["same_day_family_count_prior"].groupby("same_day_family_count", as_index=False).agg(
        {"row_count": "sum", "label_denominator_count": "sum", "P_good": "mean", "P_bad": "mean"}
    )
    lines.extend(count.to_markdown(index=False).splitlines())
    lines.extend(["", "## Bundle Sparsity And Fallback", ""])
    lines.extend(fallback_counts.to_markdown(index=False).splitlines())
    lines.extend(["", "## Context Bucket Availability", ""])
    lines.extend(context_counts.to_markdown(index=False).splitlines())
    lines.extend(["", "## Survival Checkpoints", ""])
    lines.extend(survival_summary.to_markdown(index=False).splitlines())
    lines.extend(["", "## Fresh Evidence Offset Distribution", ""])
    lines.extend(fresh_status_counts.to_markdown(index=False).splitlines())
    lines.extend(["", f"Numeric fresh offset median: `{numeric_fresh.median() if numeric_fresh.notna().any() else 'NA'}`."])
    lines.extend(["", "## Fresh Evidence Posterior", ""])
    lines.extend(fresh_prior_status.to_markdown(index=False).splitlines())
    lines.extend(["", "## T+30 Plausibility", ""])
    lines.append(
        "T+30 has observable fresh-evidence coverage when found rows exist, but censored and seed-failed rows must remain in R03 controls."
    )
    lines.extend(["", "## Split Stability", ""])
    lines.extend(split_counts.to_markdown(index=False).splitlines())
    lines.extend(["", "## R03 Readiness", ""])
    lines.extend(readiness.to_markdown(index=False).splitlines())
    (reports_dir / "r02_1_prior_probability_diagnostic_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    path_config = _read_yaml(Path(config["upstream_path_query"]["config"]))
    path_manifest = _read_json(Path(config["upstream_path_query"]["manifest"]))
    precision_manifest = _read_json(Path(config["upstream_precision"]["manifest"]))
    frozen = validate_frozen(config, path_config)

    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    events = load_single_path_rows(config, path_manifest)
    bundle = build_bundle_rows(events)
    n_min = int(config["sample_sufficiency"]["n_min_bucket"])
    single_prior = aggregate_prior(events, ["family_id", "signal_id", "split", "year"], n_min)
    bundle_prior = aggregate_prior(bundle, ["same_day_bundle_key", "same_day_family_count", "split", "year"], n_min)
    bundle_prior["bundle_family_ids"] = bundle_prior["same_day_bundle_key"]
    bundle_prior["is_review_composite_bundle"] = False
    bundle_prior["review_composite_signal_id_if_any"] = ""
    count_prior = aggregate_prior(bundle, ["same_day_family_count", "split", "year"], n_min)
    context_prior = build_context_prior(bundle, n_min)
    fallback = build_bucket_fallback(context_prior)
    survival = build_survival_prior(bundle, [int(v) for v in config["survival_checkpoints"]], n_min)
    fresh_rows = build_fresh_rows(bundle, config)
    fresh_prior = build_fresh_prior(fresh_rows, n_min)
    global_prior = build_global_prior(config)
    ev_audit = build_ev_r_audit(events)
    split_stability = build_split_stability(
        {
            "single_family_prior": single_prior,
            "same_day_bundle_prior": bundle_prior,
            "same_day_family_count_prior": count_prior,
            "context_bucket_prior": context_prior,
            "survival_checkpoint_prior": survival,
            "fresh_evidence_prior": fresh_prior,
        },
        int(config["sample_sufficiency"]["n_min_split_bucket"]),
    )
    readiness = build_readiness(False, False, context_prior, fresh_rows, split_stability)

    tables = {
        "global_action_time_prior": global_prior,
        "single_family_prior": single_prior,
        "same_day_bundle_prior": bundle_prior,
        "same_day_family_count_prior": count_prior,
        "bucket_fallback_audit": fallback,
        "context_bucket_prior": context_prior,
        "survival_checkpoint_prior": survival,
        "fresh_evidence_prior": fresh_prior,
        "fresh_evidence_offset_distribution": fresh_rows[
            [
                "seed_episode_id",
                "instrument_id",
                "seed_trade_date",
                "seed_split",
                "seed_same_day_bundle_key",
                "seed_same_day_family_count",
                "seed_label",
                "fresh_family_id",
                "fresh_signal_date",
                "fresh_offset",
                "fresh_offset_bucket",
                "seed_failure_offset",
                "seed_failure_offset_bucket",
                "fresh_vs_observable_failure_state",
                "fresh_evidence_status",
                "seed_pre_fresh_state",
                "survival_checkpoint_state",
                "posterior_denominator_policy",
            ]
        ],
        "split_stability_diagnostics": split_stability,
        "r03_input_readiness": readiness,
        "ev_r_input_audit": ev_audit,
    }

    output_paths = {
        "global_action_time_prior": reports_dir / "r02_1_global_action_time_prior.csv",
        "single_family_prior": reports_dir / "r02_1_single_family_prior.csv",
        "same_day_bundle_prior": reports_dir / "r02_1_same_day_bundle_prior.csv",
        "same_day_family_count_prior": reports_dir / "r02_1_same_day_family_count_prior.csv",
        "bucket_fallback_audit": reports_dir / "r02_1_bucket_fallback_audit.csv",
        "context_bucket_prior": reports_dir / "r02_1_context_bucket_prior.csv",
        "survival_checkpoint_prior": reports_dir / "r02_1_survival_checkpoint_prior.csv",
        "fresh_evidence_prior": reports_dir / "r02_1_fresh_evidence_prior.csv",
        "fresh_evidence_offset_distribution": reports_dir / "r02_1_fresh_evidence_offset_distribution.csv",
        "split_stability_diagnostics": reports_dir / "r02_1_split_stability_diagnostics.csv",
        "r03_input_readiness": reports_dir / "r02_1_r03_input_readiness.csv",
        "ev_r_input_audit": reports_dir / "r02_1_ev_r_input_audit.csv",
    }
    for name, df in tables.items():
        _write_csv(df, output_paths[name])

    manifest = {
        "phase": config["phase"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirement_path": config["requirement_path"],
        "config_path": relpath(topic_path(config_path)),
        "config_hash": _hash_file(topic_path(config_path)),
        "output_root": config["output_root"],
        "upstream_path_query_manifest_path": config["upstream_path_query"]["manifest"],
        "upstream_path_query_manifest_hash": _hash_file(topic_path(config["upstream_path_query"]["manifest"])),
        "upstream_precision_manifest_path": config["upstream_precision"]["manifest"],
        "upstream_precision_manifest_hash": _hash_file(topic_path(config["upstream_precision"]["manifest"])),
        "frozen_family_ids": sorted(frozen["family_id"].tolist()),
        "label_definition_version": "r02_1_good_bad_neutral_v1",
        "label_priority_order": ["censored_or_invalid", "bad_path", "good_path", "neutral_path"],
        "entry_anchor": path_manifest.get("entry_anchor", "first_executable_next_open_after_signal_date"),
        "path_metric_source": "r02_family_signal_120d_path_query_v1_per_signal_csv",
        "sample_sufficiency_thresholds": config["sample_sufficiency"],
        "global_action_time_prior_status": "unavailable_background_path_not_materialized",
        "ev_r_status": "unavailable_missing_inputs",
        "ev_r_input_audit_path": relpath(output_paths["ev_r_input_audit"]),
        "context_bucket_status": "available_with_entry_risk_pct_na",
        "survival_checkpoint_status": "available",
        "fresh_evidence_prior_status": "available",
        "r03_input_readiness_path": relpath(output_paths["r03_input_readiness"]),
        "row_counts_by_table": {name: int(len(df)) for name, df in tables.items()},
        "validation_status": "not_run",
        "artifact_hash": "",
        "upstream_precision_phase": precision_manifest.get("phase"),
    }
    write_report(output_root, {**tables, "readiness": readiness}, manifest)
    manifest["artifact_hash"] = _hash_json({name: len(df) for name, df in tables.items()}, 32)
    write_json(manifest, manifests_dir / "r02_1_prior_probability_diagnostic_manifest.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EP4 R02.1 prior probability diagnostics.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    manifest = run(Path(args.config))
    print(json.dumps({"status": "completed", "output_root": manifest["output_root"], "row_counts_by_table": manifest["row_counts_by_table"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

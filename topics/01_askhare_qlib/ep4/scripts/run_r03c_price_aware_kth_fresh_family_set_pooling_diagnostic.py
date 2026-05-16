#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
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

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
ALL_SPLITS = SPLITS + ["all"]
PATH_LABELS = ["good_path", "bad_path", "neutral_path"]
FAMILY_ORDER = [
    "momentum_rps",
    "oscillator",
    "price_trend",
    "pullback_drawdown",
    "range_breakout",
    "volatility_band",
    "volume_money",
]
PATH_QUALITY_ALLOWED = {
    "clean_continuation",
    "tradable_continuation",
    "mixed",
    "transient_spike",
    "whipsaw_after_profit",
    "late_drawdown",
    "severe_drawdown",
    "early_failure",
    "incomplete",
}
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
PATH_CONSISTENCY_COLS = [
    "entry_date",
    "entry_price",
    "entry_valid",
    "path_complete_120d",
    "available_forward_trading_days",
    "max_gain_120d",
    "max_drawdown_120d",
    "close_return_t20",
    "close_return_t60",
    "close_return_t120",
    "first_minus5_offset",
    "first_close_minus5_offset",
    "hit_plus10_before_minus5",
    "max_loss_before_first_plus10",
    "path_quality_flag",
    "early_failure_flag",
]
PATH_NUMERIC_CONSISTENCY_COLS = [
    "entry_price",
    "available_forward_trading_days",
    "max_gain_120d",
    "max_drawdown_120d",
    "close_return_t20",
    "close_return_t60",
    "close_return_t120",
    "first_minus5_offset",
    "first_close_minus5_offset",
    "max_loss_before_first_plus10",
]
PRECISION_COLS = [
    "instrument_id",
    "trade_date",
    "split",
    "year",
    "close_t",
    "next_open_t1",
    "complete_h120_flag",
    "forward_close_peak_h120_return_from_close",
    "big_winner_forward_from_signal_close",
    "forward_close_peak_h120_return_from_next_open",
    "big_winner_forward_from_next_open",
    "condition_group_id",
    "family_id",
    "signal_occurs",
]
PRECISION_CONSISTENCY_COLS = [
    "close_t",
    "next_open_t1",
    "complete_h120_flag",
    "forward_close_peak_h120_return_from_close",
    "big_winner_forward_from_signal_close",
    "forward_close_peak_h120_return_from_next_open",
    "big_winner_forward_from_next_open",
]
PRECISION_NUMERIC_CONSISTENCY_COLS = [
    "close_t",
    "next_open_t1",
    "forward_close_peak_h120_return_from_close",
    "forward_close_peak_h120_return_from_next_open",
]
FRESH_PATH_RENAME = {
    "entry_date": "fresh_entry_date",
    "entry_price": "fresh_entry_price",
    "entry_valid": "fresh_entry_valid",
    "path_complete_120d": "fresh_path_complete_120d",
    "available_forward_trading_days": "fresh_available_forward_trading_days",
    "max_gain_120d": "fresh_max_gain_120d",
    "max_drawdown_120d": "fresh_max_drawdown_120d",
    "close_return_t20": "fresh_close_return_t20",
    "close_return_t60": "fresh_close_return_t60",
    "close_return_t120": "fresh_close_return_t120",
    "first_minus5_offset": "fresh_first_minus5_offset",
    "first_close_minus5_offset": "fresh_first_close_minus5_offset",
    "hit_plus10_before_minus5": "fresh_hit_plus10_before_minus5",
    "max_loss_before_first_plus10": "fresh_max_loss_before_first_plus10",
    "path_quality_flag": "fresh_path_quality_flag",
    "early_failure_flag": "fresh_early_failure_flag",
}
FRESH_PRECISION_RENAME = {
    "complete_h120_flag": "fresh_complete_h120_close_anchor_flag",
    "forward_close_peak_h120_return_from_close": "fresh_forward_close_peak_h120_return_from_signal_close",
    "big_winner_forward_from_signal_close": "fresh_big_winner_forward_h120_close_anchor",
    "forward_close_peak_h120_return_from_next_open": "fresh_forward_close_peak_h120_return_from_next_open",
    "big_winner_forward_from_next_open": "fresh_big_winner_forward_h120_next_open_anchor",
}
SUMMARY_BASE_COLS = [
    "seed_anchor_big_winner_denominator",
    "seed_anchor_big_winner_count",
    "seed_anchor_big_winner_rate",
    "fresh_anchor_big_winner_denominator",
    "fresh_anchor_big_winner_count",
    "fresh_anchor_big_winner_rate",
    "seed_path_denominator",
    "seed_P_good",
    "seed_P_bad",
    "fresh_path_denominator",
    "fresh_P_good",
    "fresh_P_bad",
    "wait_return_to_fresh_entry_p25",
    "wait_return_to_fresh_entry_p50",
    "wait_return_to_fresh_entry_p75",
    "pct_wait_up_gt_5pct",
    "pct_wait_up_gt_10pct",
    "pct_wait_up_gt_20pct",
    "sample_sufficiency_status",
]
ALLOWED_DECISIONS = {
    "descriptive_price_aware_pooling_diagnostic_complete",
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_price_reconciliation_failed",
    "blocked_denominator_unusable",
    "invalid_requirement_violation",
}


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


def _bool_scalar(value: Any) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes"}


def _boolish(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _num(value: Any) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else np.nan


def _as_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else np.nan


def _quantile(series: pd.Series, q: float) -> float:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    return float(vals.quantile(q)) if len(vals) else np.nan


def _pct(mask: pd.Series, denominator: int | None = None) -> float:
    den = int(len(mask)) if denominator is None else int(denominator)
    return _safe_div(int(mask.fillna(False).sum()), den)


def _sample_status(denominator: int, thresholds: dict[str, int]) -> str:
    if denominator >= int(thresholds["N_min_sufficient"]):
        return "sufficient"
    if denominator >= int(thresholds["N_min_thin"]):
        return "thin_report_only"
    if denominator >= int(thresholds["N_min_too_sparse"]):
        return "too_sparse_report_only"
    return "unusable"


def _family_list(value: Any) -> list[str]:
    if pd.isna(value):
        return []
    text = str(value)
    if not text or text == "none":
        return []
    return sorted([part for part in text.split("|") if part and part != "none"])


def _family_key(values: list[str] | set[str]) -> str:
    vals = sorted(str(v) for v in values if str(v) and str(v) != "none")
    return "|".join(vals) if vals else "none"


def _offset_bucket(offset: Any) -> str:
    if pd.isna(offset):
        return "not_reached"
    value = int(offset)
    if 3 <= value <= 5:
        return "t3_t5"
    if value <= 10:
        return "t6_t10"
    if value <= 20:
        return "t11_t20"
    return "t21_t30"


def _kth_bucket(kth: Any) -> str:
    if pd.isna(kth):
        return "no_fresh"
    value = int(kth)
    if value <= 3:
        return str(value)
    return "4plus"


def _wait_bucket(value: Any, seed_price: Any | None = None, fresh_price: Any | None = None) -> str:
    ret = _num(value)
    if pd.isna(ret):
        return "missing_or_invalid"
    if seed_price is not None and (pd.isna(_num(seed_price)) or _num(seed_price) <= 0):
        return "missing_or_invalid"
    if fresh_price is not None and pd.isna(_num(fresh_price)):
        return "missing_or_invalid"
    if ret <= 0:
        return "down_or_flat"
    if ret <= 0.05:
        return "up_0_5pct"
    if ret <= 0.10:
        return "up_5_10pct"
    if ret <= 0.20:
        return "up_10_20pct"
    return "up_gt_20pct"


def _added_family_count_bucket(count: Any) -> str:
    return "2plus" if pd.notna(count) and int(count) >= 2 else "1"


def _fresh_path_label(row: dict[str, Any]) -> str:
    invalid = (not _bool_scalar(row.get("fresh_entry_valid"))) or (not _bool_scalar(row.get("fresh_path_complete_120d")))
    if invalid:
        return "censored_or_invalid"
    bad = (
        _bool_scalar(row.get("fresh_early_failure_flag"))
        or (_num(row.get("fresh_first_minus5_offset")) <= 10)
        or (_num(row.get("fresh_max_loss_before_first_plus10")) <= -0.06)
    )
    if bad:
        return "bad_path"
    good = _bool_scalar(row.get("fresh_hit_plus10_before_minus5")) or str(row.get("fresh_path_quality_flag")) in {
        "clean_continuation",
        "tradable_continuation",
    }
    if good:
        return "good_path"
    return "neutral_path"


def _valid_for_consistency(values: pd.Series, numeric: bool, tol: float) -> bool:
    if numeric:
        nums = pd.to_numeric(values, errors="coerce")
        if nums.isna().all():
            return True
        vals = nums.dropna()
        return bool((vals.max() - vals.min()) <= tol)
    normalized = values.astype(object).where(pd.notna(values), "__NA__").astype(str)
    return int(normalized.nunique(dropna=False)) <= 1


def _frame_consistent(df: pd.DataFrame, cols: list[str], numeric_cols: list[str], tol: float) -> tuple[bool, list[str]]:
    bad_cols = []
    for col in cols:
        if col not in df.columns:
            bad_cols.append(col)
            continue
        if not _valid_for_consistency(df[col], col in numeric_cols, tol):
            bad_cols.append(col)
    return not bad_cols, bad_cols


def _add_validation_row(
    rows: list[dict[str, Any]],
    check_id: str,
    category: str,
    condition: bool,
    severity: str,
    failure_reason: str = "",
    affected_rows: int = 0,
    artifact_path: str = "",
) -> None:
    rows.append(
        {
            "check_id": check_id,
            "check_category": category,
            "status": "passed" if condition else "failed",
            "severity": severity,
            "failure_reason": "" if condition else failure_reason,
            "affected_rows": 0 if condition else int(affected_rows),
            "artifact_path": artifact_path,
        }
    )


def _validation_status(rows: list[dict[str, Any]]) -> str:
    df = pd.DataFrame(rows)
    if df.empty:
        return "passed"
    fatal = df["severity"].isin(["error", "fatal"]) & df["status"].eq("failed")
    return "failed" if bool(fatal.any()) else "passed"


def _readiness(config: dict[str, Any]) -> tuple[pd.DataFrame, bool, str]:
    rows: list[dict[str, Any]] = []

    def add(role: str, path_value: str, validation_status: str = "exists_only", row_count: Any = np.nan) -> None:
        path = topic_path(Path(path_value))
        exists = path.exists()
        ready = exists and validation_status not in {"failed", "missing"}
        rows.append(
            {
                "artifact_role": role,
                "artifact_path": path_value,
                "exists": bool(exists),
                "validation_status": validation_status,
                "row_count": row_count,
                "readiness_status": "ready" if ready else "blocked",
                "failure_reason": "" if ready else ("missing" if not exists else validation_status),
            }
        )

    validation_specs = [
        ("r03b_validation", config["upstream_r03b"]["validation"]),
        ("path_query_validation", config["upstream_path_query"]["validation"]),
        ("precision_validation", config["upstream_precision"]["validation"]),
    ]
    validation_statuses: dict[str, str] = {}
    for role, path in validation_specs:
        status = _read_json(path).get("validation_status", "missing")
        validation_statuses[role] = status
        add(role, path, status)

    for role, path in [
        ("r03b_manifest", config["upstream_r03b"]["manifest"]),
        ("r03b_seed_episode_panel", config["upstream_r03b"]["seed_episode_panel"]),
        ("r03b_sequence_step_panel", config["upstream_r03b"]["sequence_step_panel"]),
        ("r03b_checkpoint_state_panel", config["upstream_r03b"]["checkpoint_state_panel"]),
        ("r03b_signal_timeline_panel", config["upstream_r03b"]["signal_timeline_panel"]),
        ("r03b_checkpoint_fresh_count_summary", config["upstream_r03b"]["checkpoint_fresh_count_summary"]),
        ("r03b_kth_fresh_summary", config["upstream_r03b"]["kth_fresh_summary"]),
        ("r03b_sequence_pattern_summary", config["upstream_r03b"]["sequence_pattern_summary"]),
        ("path_query_manifest", config["upstream_path_query"]["manifest"]),
        ("precision_manifest", config["upstream_precision"]["manifest"]),
        ("precision_action_time_panel", config["upstream_precision"]["action_time_panel"]),
    ]:
        add(role, path)

    for item in config["frozen_families"]:
        signal_id = item["signal_id"]
        path = f"{config['upstream_path_query']['signal_dir']}/{signal_id}_120d_path.csv"
        row_count = np.nan
        p = topic_path(Path(path))
        if p.exists():
            row_count = sum(1 for _ in p.open("r", encoding="utf-8")) - 1
        add(f"path_csv_{signal_id}", path, "exists_only", row_count)

    df = pd.DataFrame(rows)
    if not bool(df["exists"].all()):
        return df, False, "blocked_missing_required_input"
    if any(status != "passed" for status in validation_statuses.values()):
        return df, False, "blocked_upstream_validation_failed"
    if not bool(df["readiness_status"].eq("ready").all()):
        return df, False, "blocked_missing_required_input"
    return df, True, "ready"


def _load_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    seeds = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["seed_episode_panel"])))
    step = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["sequence_step_panel"])))
    checkpoint = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["checkpoint_state_panel"])))
    timeline = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["signal_timeline_panel"])))

    for frame, cols in [
        (seeds, ["signal_date", "entry_date", "seed_trade_date", "seed_entry_date"]),
        (step, ["step_signal_date"]),
        (checkpoint, []),
        (timeline, ["signal_date"]),
    ]:
        for col in cols:
            if col in frame.columns:
                frame[col] = pd.to_datetime(frame[col], errors="coerce")

    path_frames = []
    for item in config["frozen_families"]:
        signal_id = item["signal_id"]
        path = topic_path(Path(config["upstream_path_query"]["signal_dir"]) / f"{signal_id}_120d_path.csv")
        frame = pd.read_csv(path, usecols=PATH_COLS, low_memory=False)
        frame = frame.loc[frame["signal_id"].astype(str).eq(signal_id)].copy()
        path_frames.append(frame)
    path_df = pd.concat(path_frames, ignore_index=True)
    path_df["signal_date"] = pd.to_datetime(path_df["signal_date"], errors="coerce")
    path_df["entry_date"] = pd.to_datetime(path_df["entry_date"], errors="coerce")

    precision = pd.read_parquet(topic_path(Path(config["upstream_precision"]["action_time_panel"])), columns=PRECISION_COLS)
    precision["trade_date"] = pd.to_datetime(precision["trade_date"], errors="coerce")
    precision = precision.loc[_boolish(precision["signal_occurs"])].copy()
    return seeds, step, checkpoint, timeline, path_df, precision


def _build_clean_steps(seeds: pd.DataFrame, step: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    seed_cols = [
        "seed_episode_id",
        "seed_trade_date",
        "seed_family_set",
        "seed_same_day_family_count",
        "seed_entry_date",
        "seed_entry_price",
        "observable_failure_offset",
        "complete_h120_close_anchor_flag",
        "big_winner_forward_h120_close_anchor",
        "forward_close_peak_h120_return_from_seed_close",
        "big_winner_forward_h120_next_open_anchor",
        "label",
    ]
    merged = step.merge(seeds[seed_cols], on="seed_episode_id", how="left", validate="many_to_one")
    start = int(config["sequence"]["primary_fresh_start_offset"])
    end = int(config["sequence"]["primary_fresh_end_offset"])
    failure = pd.to_numeric(merged["observable_failure_offset"], errors="coerce")
    offset = pd.to_numeric(merged["step_offset"], errors="coerce")
    mask = (
        _boolish(merged["included_in_primary_fresh_count"])
        & merged["step_status"].isin(["fresh_distinct_family_step", "same_offset_multi_family_step"])
        & offset.between(start, end, inclusive="both")
        & (failure.isna() | (offset < failure))
        & (failure.isna() | (offset != failure))
    )
    clean = merged.loc[mask].copy()
    clean = clean.sort_values(["seed_episode_id", "step_offset", "step_signal_date", "added_family_set"]).reset_index(drop=True)
    clean["kth_fresh_step_index_raw"] = clean.groupby("seed_episode_id").cumcount() + 1
    clean["kth_fresh_step_bucket"] = clean["kth_fresh_step_index_raw"].map(_kth_bucket)
    clean["kth_fresh_offset_bucket"] = clean["step_offset"].map(_offset_bucket)
    clean["added_family_count"] = pd.to_numeric(clean["added_family_count"], errors="coerce").fillna(0).astype(int)
    clean["added_family_count_bucket"] = clean["added_family_count"].map(_added_family_count_bucket)
    clean["cumulative_distinct_family_set_after_step"] = clean["cumulative_distinct_family_set"]
    clean["cumulative_distinct_family_count_after_step"] = clean["cumulative_distinct_family_count"]
    clean["is_same_offset_multi_family_step"] = _boolish(clean["is_same_offset_multi_family_step"])
    return clean


def _group_lookup(df: pd.DataFrame, key_cols: list[str]) -> dict[tuple[Any, ...], pd.DataFrame]:
    lookup: dict[tuple[Any, ...], pd.DataFrame] = {}
    for key, group in df.groupby(key_cols, sort=False, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        lookup[key] = group.copy()
    return lookup


def _first_sorted(df: pd.DataFrame, by: list[str]) -> pd.Series:
    sort_cols = [col for col in by if col in df.columns]
    return df.sort_values(sort_cols).iloc[0] if sort_cols else df.iloc[0]


def _build_fresh_panel(
    clean: pd.DataFrame,
    path_df: pd.DataFrame,
    precision: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    tol = float(config["price_reconciliation"]["numeric_consistency_tolerance"])
    threshold = float(config["price_reconciliation"]["big_winner_threshold"])
    needed_rows = []
    for row in clean[["instrument_id", "step_signal_date", "added_family_set"]].itertuples(index=False):
        for family in _family_list(row.added_family_set):
            needed_rows.append({"instrument_id": row.instrument_id, "step_signal_date": row.step_signal_date, "family_id": family})
    needed = pd.DataFrame(needed_rows).drop_duplicates()
    print(f"r03c: fresh reconciliation keys={len(needed):,}", file=sys.stderr, flush=True)
    if needed.empty:
        path_lookup = {}
        precision_lookup = {}
    else:
        needed["step_signal_date"] = pd.to_datetime(needed["step_signal_date"], errors="coerce")
        path_keys = needed.rename(columns={"step_signal_date": "signal_date"})
        precision_keys = needed.rename(columns={"step_signal_date": "trade_date"})
        path_subset = path_df.merge(path_keys, on=["instrument_id", "signal_date", "family_id"], how="inner")
        precision_subset = precision.merge(precision_keys, on=["instrument_id", "trade_date", "family_id"], how="inner")
        print(
            f"r03c: fresh reconciliation subset path={len(path_subset):,} precision={len(precision_subset):,}",
            file=sys.stderr,
            flush=True,
        )
        path_lookup = _group_lookup(path_subset, ["instrument_id", "signal_date", "family_id"])
        precision_lookup = _group_lookup(precision_subset, ["instrument_id", "trade_date", "family_id"])
        print("r03c: fresh reconciliation lookup built", file=sys.stderr, flush=True)
    rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for step_no, step in enumerate(clean.itertuples(index=False), start=1):
        if step_no % 2000 == 0:
            print(f"r03c: reconciled fresh steps {step_no:,}/{len(clean):,}", file=sys.stderr, flush=True)
        families = _family_list(step.added_family_set)
        selected_path = []
        selected_precision = []
        matched_path_count = 0
        matched_precision_count = 0
        condition_groups: set[str] = set()
        failures: list[str] = []
        precision_uniqueness = "unique"

        for family in families:
            path_key = (step.instrument_id, pd.Timestamp(step.step_signal_date), family)
            path_rows = path_lookup.get(path_key, pd.DataFrame(columns=path_df.columns))
            matched_path_count += int(len(path_rows))
            if len(path_rows) != 1:
                failures.append(f"path_row_count_{family}={len(path_rows)}")
            else:
                selected_path.append(path_rows.iloc[0])

            precision_key = (step.instrument_id, pd.Timestamp(step.step_signal_date), family)
            precision_rows = precision_lookup.get(precision_key, pd.DataFrame(columns=precision.columns))
            matched_precision_count += int(len(precision_rows))
            if precision_rows.empty:
                failures.append(f"precision_row_count_{family}=0")
            else:
                condition_groups.update(precision_rows["condition_group_id"].dropna().astype(str).tolist())
                ok, bad_cols = _frame_consistent(
                    precision_rows,
                    PRECISION_CONSISTENCY_COLS,
                    PRECISION_NUMERIC_CONSISTENCY_COLS,
                    tol,
                )
                if not ok:
                    failures.append(f"precision_duplicate_inconsistent_{family}:{','.join(bad_cols)}")
                    precision_uniqueness = "duplicate_inconsistent"
                else:
                    if len(precision_rows) > 1:
                        precision_uniqueness = "multi_condition_identical"
                    selected_precision.append(_first_sorted(precision_rows, ["condition_group_id"]))

        path_consistent = False
        entry_date_consistent = False
        entry_price_consistent = False
        precision_consistent = False
        close_consistent = False
        if selected_path:
            path_selected_df = pd.DataFrame(selected_path)
            path_consistent, bad_path_cols = _frame_consistent(
                path_selected_df,
                PATH_CONSISTENCY_COLS,
                PATH_NUMERIC_CONSISTENCY_COLS,
                tol,
            )
            entry_date_consistent, _ = _frame_consistent(path_selected_df, ["entry_date"], [], tol)
            entry_price_consistent, _ = _frame_consistent(path_selected_df, ["entry_price"], ["entry_price"], tol)
            if not path_consistent:
                failures.append(f"path_fields_inconsistent:{','.join(bad_path_cols)}")
        if selected_precision:
            precision_selected_df = pd.DataFrame(selected_precision)
            precision_consistent, bad_precision_cols = _frame_consistent(
                precision_selected_df,
                PRECISION_CONSISTENCY_COLS,
                PRECISION_NUMERIC_CONSISTENCY_COLS,
                tol,
            )
            close_consistent, _ = _frame_consistent(precision_selected_df, ["close_t"], ["close_t"], tol)
            if not precision_consistent:
                failures.append(f"precision_fields_inconsistent:{','.join(bad_precision_cols)}")

        if selected_path and selected_precision:
            path_row = _first_sorted(pd.DataFrame(selected_path), ["family_id", "signal_id"])
            precision_row = _first_sorted(pd.DataFrame(selected_precision), ["family_id", "condition_group_id"])
            payload = step._asdict()
            payload["seed_anchor_big_winner"] = payload["big_winner_forward_h120_close_anchor"]
            payload["seed_complete_h120_close_anchor_flag"] = payload["complete_h120_close_anchor_flag"]
            payload["seed_path_label"] = payload["label"]
            payload["fresh_signal_close_price"] = precision_row.get("close_t")
            payload["fresh_signal_next_open_price"] = precision_row.get("next_open_t1")
            payload["wait_return_to_fresh_signal_close"] = (
                _num(precision_row.get("close_t")) / _num(step.seed_entry_price) - 1
                if _num(step.seed_entry_price) > 0 and pd.notna(_num(precision_row.get("close_t")))
                else np.nan
            )
            for src, dst in FRESH_PRECISION_RENAME.items():
                payload[dst] = precision_row.get(src)
            for src, dst in FRESH_PATH_RENAME.items():
                payload[dst] = path_row.get(src)
            payload["wait_return_to_fresh_entry"] = (
                _num(payload["fresh_entry_price"]) / _num(step.seed_entry_price) - 1
                if _num(step.seed_entry_price) > 0 and pd.notna(_num(payload["fresh_entry_price"]))
                else np.nan
            )
            payload["wait_return_bucket"] = _wait_bucket(
                payload["wait_return_to_fresh_entry"],
                step.seed_entry_price,
                payload["fresh_entry_price"],
            )
            payload["fresh_path_label"] = _fresh_path_label(payload)
            payload["fresh_max_gain_120d_from_seed_entry_reference"] = (
                (1 + payload["wait_return_to_fresh_entry"]) * (1 + _num(payload["fresh_max_gain_120d"])) - 1
                if pd.notna(payload["wait_return_to_fresh_entry"]) and pd.notna(_num(payload["fresh_max_gain_120d"]))
                else np.nan
            )
            payload["fresh_close_return_t20_from_seed_entry_reference"] = (
                (1 + payload["wait_return_to_fresh_entry"]) * (1 + _num(payload["fresh_close_return_t20"])) - 1
                if pd.notna(payload["wait_return_to_fresh_entry"]) and pd.notna(_num(payload["fresh_close_return_t20"]))
                else np.nan
            )
            payload["wait_cost_to_remaining_max_gain_ratio"] = (
                payload["wait_return_to_fresh_entry"] / _num(payload["fresh_max_gain_120d"])
                if pd.notna(payload["wait_return_to_fresh_entry"]) and _num(payload["fresh_max_gain_120d"]) > 0
                else np.nan
            )
            quality = str(payload.get("fresh_path_quality_flag"))
            if quality not in PATH_QUALITY_ALLOWED:
                failures.append(f"path_quality_not_allowed:{quality}")
            close_checkable = _bool_scalar(payload["fresh_complete_h120_close_anchor_flag"]) and pd.notna(
                _num(payload["fresh_forward_close_peak_h120_return_from_signal_close"])
            )
            if close_checkable:
                expected = _num(payload["fresh_forward_close_peak_h120_return_from_signal_close"]) >= threshold
                if _bool_scalar(payload["fresh_big_winner_forward_h120_close_anchor"]) != expected:
                    failures.append("fresh_close_anchor_big_winner_threshold_mismatch")
            next_open_checkable = _bool_scalar(payload["fresh_complete_h120_close_anchor_flag"]) and pd.notna(
                _num(payload["fresh_forward_close_peak_h120_return_from_next_open"])
            )
            if next_open_checkable:
                expected = _num(payload["fresh_forward_close_peak_h120_return_from_next_open"]) >= threshold
                if _bool_scalar(payload["fresh_big_winner_forward_h120_next_open_anchor"]) != expected:
                    failures.append("fresh_next_open_anchor_big_winner_threshold_mismatch")
            rows.append(payload)

        audit_rows.append(
            {
                "split": step.split,
                "seed_episode_id": step.seed_episode_id,
                "instrument_id": step.instrument_id,
                "step_signal_date": step.step_signal_date,
                "step_offset": step.step_offset,
                "added_family_set": step.added_family_set,
                "added_family_count": step.added_family_count,
                "matched_path_row_count": matched_path_count,
                "matched_precision_row_count": matched_precision_count,
                "matched_precision_condition_group_count": len(condition_groups),
                "precision_condition_group_uniqueness_status": precision_uniqueness,
                "precision_label_fields_consistent": bool(precision_consistent),
                "fresh_signal_close_price_consistent": bool(close_consistent),
                "fresh_entry_date_consistent": bool(entry_date_consistent),
                "fresh_entry_price_consistent": bool(entry_price_consistent),
                "fresh_path_fields_consistent": bool(path_consistent),
                "reconciliation_status": "failed" if failures else "passed",
                "failure_reason": ";".join(failures),
            }
        )

    fresh = pd.DataFrame(rows)
    audit = pd.DataFrame(audit_rows)
    ok = bool(audit.empty or audit["reconciliation_status"].eq("passed").all())
    if not fresh.empty:
        for col in ["step_signal_date", "seed_trade_date", "seed_entry_date", "fresh_entry_date"]:
            if col in fresh.columns:
                fresh[col] = pd.to_datetime(fresh[col], errors="coerce")
    return fresh, audit, ok


def _build_checkpoint_panel(checkpoint: pd.DataFrame, seeds: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    seed_cols = [
        "seed_episode_id",
        "seed_trade_date",
        "seed_family_set",
        "seed_same_day_family_count",
        "seed_entry_date",
        "seed_entry_price",
        "observable_failure_offset",
        "complete_h120_close_anchor_flag",
        "big_winner_forward_h120_close_anchor",
        "forward_close_peak_h120_return_from_seed_close",
        "big_winner_forward_h120_next_open_anchor",
        "label",
    ]
    panel = checkpoint.merge(seeds[seed_cols], on="seed_episode_id", how="left", validate="many_to_one")
    fresh_sorted = fresh.sort_values(["seed_episode_id", "step_offset", "step_signal_date", "kth_fresh_step_index_raw"])
    fresh_by_seed = {seed_id: group.copy() for seed_id, group in fresh_sorted.groupby("seed_episode_id", sort=False)}
    rows = []
    for row in panel.itertuples(index=False):
        payload = row._asdict()
        steps = fresh_by_seed.get(row.seed_episode_id)
        prior = pd.DataFrame()
        if steps is not None:
            prior = steps.loc[pd.to_numeric(steps["step_offset"], errors="coerce") <= int(row.checkpoint_offset)]
        if prior.empty:
            payload.update(
                {
                    "fresh_family_set_before_or_at_checkpoint": "none",
                    "cumulative_family_set_before_or_at_checkpoint": row.seed_family_set,
                    "latest_clean_fresh_step_offset_before_or_at_checkpoint": np.nan,
                    "latest_clean_fresh_kth_fresh_step_bucket_before_or_at_checkpoint": "no_fresh",
                    "latest_clean_fresh_kth_fresh_offset_bucket_before_or_at_checkpoint": "no_fresh",
                    "latest_clean_fresh_entry_date_before_or_at_checkpoint": pd.NaT,
                    "latest_clean_fresh_entry_price_before_or_at_checkpoint": np.nan,
                    "latest_clean_fresh_step_signal_date_before_or_at_checkpoint": pd.NaT,
                    "wait_return_to_latest_fresh_entry_before_or_at_checkpoint": np.nan,
                    "wait_return_bucket_before_or_at_checkpoint": "no_fresh",
                }
            )
            for col in list(FRESH_PRECISION_RENAME.values()) + list(FRESH_PATH_RENAME.values()) + ["fresh_path_label"]:
                payload[col] = np.nan
        else:
            latest = prior.iloc[-1]
            families: set[str] = set()
            for value in prior["added_family_set"]:
                families.update(_family_list(value))
            payload.update(
                {
                    "fresh_family_set_before_or_at_checkpoint": _family_key(families),
                    "cumulative_family_set_before_or_at_checkpoint": latest["cumulative_distinct_family_set_after_step"],
                    "latest_clean_fresh_step_offset_before_or_at_checkpoint": latest["step_offset"],
                    "latest_clean_fresh_kth_fresh_step_bucket_before_or_at_checkpoint": latest["kth_fresh_step_bucket"],
                    "latest_clean_fresh_kth_fresh_offset_bucket_before_or_at_checkpoint": latest["kth_fresh_offset_bucket"],
                    "latest_clean_fresh_entry_date_before_or_at_checkpoint": latest["fresh_entry_date"],
                    "latest_clean_fresh_entry_price_before_or_at_checkpoint": latest["fresh_entry_price"],
                    "latest_clean_fresh_step_signal_date_before_or_at_checkpoint": latest["step_signal_date"],
                    "wait_return_to_latest_fresh_entry_before_or_at_checkpoint": latest["wait_return_to_fresh_entry"],
                    "wait_return_bucket_before_or_at_checkpoint": latest["wait_return_bucket"],
                }
            )
            for col in list(FRESH_PRECISION_RENAME.values()) + list(FRESH_PATH_RENAME.values()) + ["fresh_path_label"]:
                payload[col] = latest[col]
        payload["seed_anchor_big_winner"] = payload["big_winner_forward_h120_close_anchor"]
        payload["seed_complete_h120_close_anchor_flag"] = payload["complete_h120_close_anchor_flag"]
        payload["seed_path_label"] = payload["label"]
        payload["latest_kth_offset_key"] = (
            f"{payload['latest_clean_fresh_kth_fresh_step_bucket_before_or_at_checkpoint']}|"
            f"{payload['latest_clean_fresh_kth_fresh_offset_bucket_before_or_at_checkpoint']}"
        )
        rows.append(payload)
    out = pd.DataFrame(rows)
    for col in [
        "seed_trade_date",
        "seed_entry_date",
        "latest_clean_fresh_entry_date_before_or_at_checkpoint",
        "latest_clean_fresh_step_signal_date_before_or_at_checkpoint",
    ]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def _presence_signature(source_family_set: Any) -> str:
    families = set(_family_list(source_family_set))
    return "|".join(f"contains_{family}={1 if family in families else 0}" for family in FAMILY_ORDER)


def _build_pooling_panel(fresh: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in fresh.itertuples(index=False):
        payload = row._asdict()
        levels = [
            ("fresh_added_family_set", row.added_family_set, len(_family_list(row.added_family_set))),
            (
                "cumulative_family_set_after_step",
                row.cumulative_distinct_family_set_after_step,
                len(_family_list(row.cumulative_distinct_family_set_after_step)),
            ),
            (
                "family_presence_signature",
                _presence_signature(row.cumulative_distinct_family_set_after_step),
                len(_family_list(row.cumulative_distinct_family_set_after_step)),
            ),
        ]
        for level, key, count in levels:
            item = dict(payload)
            item.update({"pooling_level": level, "pooling_key": key, "pooling_key_family_count": count})
            rows.append(item)
    return pd.DataFrame(rows)


def _seed_metric_base(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "seed_episode_id" not in df.columns:
        return pd.DataFrame()
    return df.sort_values(["seed_episode_id"]).drop_duplicates("seed_episode_id")


def _headline_metrics(
    group: pd.DataFrame,
    thresholds: dict[str, int],
    fresh_grain: bool,
    wait_col: str,
    step_date_col: str | None = "step_signal_date",
) -> dict[str, Any]:
    seed_part = _seed_metric_base(group)
    seed_count = int(len(seed_part))
    seed_bw_den = int(_boolish(seed_part.get("complete_h120_close_anchor_flag", pd.Series(dtype=object))).sum())
    seed_bw_count = int(
        (
            _boolish(seed_part.get("complete_h120_close_anchor_flag", pd.Series(dtype=object)))
            & _boolish(seed_part.get("big_winner_forward_h120_close_anchor", pd.Series(dtype=object)))
        ).sum()
    )
    seed_labeled = seed_part.loc[seed_part.get("label", pd.Series(dtype=object)).isin(PATH_LABELS)] if seed_count else seed_part
    seed_path_den = int(len(seed_labeled))
    fresh_bw_den = int(_boolish(group.get("fresh_complete_h120_close_anchor_flag", pd.Series(dtype=object))).sum())
    fresh_bw_count = int(
        (
            _boolish(group.get("fresh_complete_h120_close_anchor_flag", pd.Series(dtype=object)))
            & _boolish(group.get("fresh_big_winner_forward_h120_close_anchor", pd.Series(dtype=object)))
        ).sum()
    )
    fresh_labeled = group.loc[group.get("fresh_path_label", pd.Series(dtype=object)).isin(PATH_LABELS)] if not group.empty else group
    fresh_path_den = int(len(fresh_labeled))
    wait = pd.to_numeric(group.get(wait_col, pd.Series(dtype=float)), errors="coerce")
    status_den = int(len(group)) if fresh_grain else seed_count
    out = {
        "fresh_step_count": int(len(group)) if fresh_grain else np.nan,
        "seed_episode_count": seed_count,
        "unique_seed_episode_count": int(group["seed_episode_id"].nunique()) if "seed_episode_id" in group.columns else 0,
        "unique_instrument_count": int(group["instrument_id"].nunique()) if "instrument_id" in group.columns else np.nan,
        "unique_step_signal_date_count": int(group[step_date_col].nunique()) if step_date_col and step_date_col in group.columns else np.nan,
        "seed_anchor_big_winner_denominator": seed_bw_den,
        "seed_anchor_big_winner_count": seed_bw_count,
        "seed_anchor_big_winner_rate": _safe_div(seed_bw_count, seed_bw_den),
        "fresh_anchor_big_winner_denominator": fresh_bw_den,
        "fresh_anchor_big_winner_count": fresh_bw_count,
        "fresh_anchor_big_winner_rate": _safe_div(fresh_bw_count, fresh_bw_den),
        "seed_path_denominator": seed_path_den,
        "seed_P_good": _safe_div(int(seed_labeled.get("label", pd.Series(dtype=object)).eq("good_path").sum()), seed_path_den),
        "seed_P_bad": _safe_div(int(seed_labeled.get("label", pd.Series(dtype=object)).eq("bad_path").sum()), seed_path_den),
        "fresh_path_denominator": fresh_path_den,
        "fresh_P_good": _safe_div(int(fresh_labeled.get("fresh_path_label", pd.Series(dtype=object)).eq("good_path").sum()), fresh_path_den),
        "fresh_P_bad": _safe_div(int(fresh_labeled.get("fresh_path_label", pd.Series(dtype=object)).eq("bad_path").sum()), fresh_path_den),
        "wait_return_to_fresh_entry_p25": _quantile(wait, 0.25),
        "wait_return_to_fresh_entry_p50": _quantile(wait, 0.50),
        "wait_return_to_fresh_entry_p75": _quantile(wait, 0.75),
        "pct_wait_up_gt_5pct": _pct(wait > 0.05, len(group)),
        "pct_wait_up_gt_10pct": _pct(wait > 0.10, len(group)),
        "pct_wait_up_gt_20pct": _pct(wait > 0.20, len(group)),
        "sample_sufficiency_status": _sample_status(status_den, thresholds),
    }
    return out


def _group_summary(
    df: pd.DataFrame,
    group_cols: list[str],
    thresholds: dict[str, int],
    fresh_grain: bool,
    wait_col: str = "wait_return_to_fresh_entry",
    step_date_col: str | None = "step_signal_date",
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in ALL_SPLITS:
        base = df if split == "all" else df.loc[df["split"].eq(split)]
        if base.empty:
            continue
        grouped = [((), base)] if not group_cols else base.groupby(group_cols, dropna=False, sort=True)
        for keys, group in grouped:
            if group_cols and not isinstance(keys, tuple):
                keys = (keys,)
            payload = {"split": split}
            if group_cols:
                payload.update(dict(zip(group_cols, keys)))
            payload.update(_headline_metrics(group, thresholds, fresh_grain, wait_col, step_date_col))
            rows.append(payload)
    return pd.DataFrame(rows)


def _wait_movement_summary(fresh: pd.DataFrame, thresholds: dict[str, int]) -> pd.DataFrame:
    rows = []
    for split in ALL_SPLITS:
        base = fresh if split == "all" else fresh.loc[fresh["split"].eq(split)]
        if base.empty:
            continue
        for keys, group in base.groupby(["kth_fresh_step_bucket", "kth_fresh_offset_bucket"], sort=True):
            kth, offset = keys
            buckets = group["wait_return_bucket"].astype(str)
            count = int(len(group))
            rows.append(
                {
                    "split": split,
                    "kth_fresh_step_bucket": kth,
                    "kth_fresh_offset_bucket": offset,
                    "fresh_step_count": count,
                    "unique_seed_episode_count": int(group["seed_episode_id"].nunique()),
                    "unique_instrument_count": int(group["instrument_id"].nunique()),
                    "unique_step_signal_date_count": int(group["step_signal_date"].nunique()),
                    "wait_return_to_fresh_signal_close_p25": _quantile(group["wait_return_to_fresh_signal_close"], 0.25),
                    "wait_return_to_fresh_signal_close_p50": _quantile(group["wait_return_to_fresh_signal_close"], 0.50),
                    "wait_return_to_fresh_signal_close_p75": _quantile(group["wait_return_to_fresh_signal_close"], 0.75),
                    "wait_return_to_fresh_entry_p25": _quantile(group["wait_return_to_fresh_entry"], 0.25),
                    "wait_return_to_fresh_entry_p50": _quantile(group["wait_return_to_fresh_entry"], 0.50),
                    "wait_return_to_fresh_entry_p75": _quantile(group["wait_return_to_fresh_entry"], 0.75),
                    "pct_wait_down_or_flat": _safe_div(int(buckets.eq("down_or_flat").sum()), count),
                    "pct_wait_up_0_5pct": _safe_div(int(buckets.eq("up_0_5pct").sum()), count),
                    "pct_wait_up_5_10pct": _safe_div(int(buckets.eq("up_5_10pct").sum()), count),
                    "pct_wait_up_10_20pct": _safe_div(int(buckets.eq("up_10_20pct").sum()), count),
                    "pct_wait_up_gt_20pct": _safe_div(int(buckets.eq("up_gt_20pct").sum()), count),
                    "sample_sufficiency_status": _sample_status(count, thresholds),
                }
            )
    return pd.DataFrame(rows)


def _kth_offset_summary(fresh: pd.DataFrame, thresholds: dict[str, int]) -> pd.DataFrame:
    summary = _group_summary(
        fresh,
        ["kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket", "added_family_count_bucket"],
        thresholds,
        fresh_grain=True,
    )
    extra_rows = []
    for split in ALL_SPLITS:
        base = fresh if split == "all" else fresh.loc[fresh["split"].eq(split)]
        if base.empty:
            continue
        group_cols = ["kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket", "added_family_count_bucket"]
        for keys, group in base.groupby(group_cols, dropna=False, sort=True):
            if not isinstance(keys, tuple):
                keys = (keys,)
            payload = {"split": split}
            payload.update(dict(zip(group_cols, keys)))
            den = int(len(group))
            payload.update(
                {
                    "fresh_close_return_t20_p50": _quantile(group["fresh_close_return_t20"], 0.50),
                    "fresh_close_return_t60_p50": _quantile(group["fresh_close_return_t60"], 0.50),
                    "fresh_close_return_t120_p50": _quantile(group["fresh_close_return_t120"], 0.50),
                    "fresh_max_gain_120d_p50": _quantile(group["fresh_max_gain_120d"], 0.50),
                    "fresh_max_drawdown_120d_p50": _quantile(group["fresh_max_drawdown_120d"], 0.50),
                    "fresh_early_failure_rate": _pct(_boolish(group["fresh_early_failure_flag"]), den),
                    "fresh_hit_plus10_before_minus5_rate": _pct(_boolish(group["fresh_hit_plus10_before_minus5"]), den),
                    "fresh_path_quality_clean_or_tradable_rate": _pct(
                        group["fresh_path_quality_flag"].isin(["clean_continuation", "tradable_continuation"]),
                        den,
                    ),
                }
            )
            extra_rows.append(payload)
    extra = pd.DataFrame(extra_rows)
    return summary.merge(extra, on=["split", "kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket", "added_family_count_bucket"], how="left")


def _family_set_summary(pooling: pd.DataFrame, thresholds: dict[str, int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    group_cols = ["pooling_level", "pooling_key", "kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket"]
    summary = _group_summary(pooling, group_cols, thresholds, fresh_grain=True)
    if summary.empty:
        return summary, pd.DataFrame()

    def extra_metrics(source: pd.DataFrame) -> pd.DataFrame:
        work = source.copy()
        work["_quality_clean_or_tradable"] = work["fresh_path_quality_flag"].isin(["clean_continuation", "tradable_continuation"])
        work["_fresh_early_failure"] = _boolish(work["fresh_early_failure_flag"])
        grouped = (
            work.groupby(["split"] + group_cols, dropna=False, sort=True)
            .agg(
                pooling_key_family_count=("pooling_key_family_count", "first"),
                _den=("seed_episode_id", "size"),
                _quality_clean_or_tradable_count=("_quality_clean_or_tradable", "sum"),
                _fresh_early_failure_count=("_fresh_early_failure", "sum"),
            )
            .reset_index()
        )
        grouped["fresh_anchor_path_quality_clean_or_tradable_rate"] = grouped.apply(
            lambda row: _safe_div(row["_quality_clean_or_tradable_count"], row["_den"]),
            axis=1,
        )
        grouped["fresh_anchor_early_failure_rate"] = grouped.apply(
            lambda row: _safe_div(row["_fresh_early_failure_count"], row["_den"]),
            axis=1,
        )
        return grouped.drop(columns=["_den", "_quality_clean_or_tradable_count", "_fresh_early_failure_count"])

    extras = pd.concat([extra_metrics(pooling), extra_metrics(pooling.assign(split="all"))], ignore_index=True)
    summary = summary.merge(extras, on=["split"] + group_cols, how="left")
    summary["split_denominator_share"] = np.nan
    for split in ALL_SPLITS:
        for level in summary.loc[summary["split"].eq(split), "pooling_level"].dropna().unique():
            mask = summary["split"].eq(split) & summary["pooling_level"].eq(level)
            total = pd.to_numeric(summary.loc[mask, "fresh_step_count"], errors="coerce").sum()
            summary.loc[mask, "split_denominator_share"] = summary.loc[mask, "fresh_step_count"].map(lambda x: _safe_div(x, total))

    stability = _family_stability_audit(summary, thresholds)
    summary = summary.merge(
        stability[group_cols + ["overall_stability_status"]].rename(columns={"overall_stability_status": "split_stability_status"}),
        on=group_cols,
        how="left",
    )
    summary["split_stability_status"] = summary["split_stability_status"].fillna("split_missing")
    return summary, stability


def _sign(value: Any) -> int:
    num = _num(value)
    if pd.isna(num) or abs(num) < 1e-12:
        return 0
    return 1 if num > 0 else -1


def _family_stability_audit(summary: pd.DataFrame, thresholds: dict[str, int]) -> pd.DataFrame:
    group_cols = ["pooling_level", "pooling_key", "kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket"]
    rows = []
    source = summary.loc[summary["split"].isin(SPLITS)].copy()
    for keys, group in source.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        payload = dict(zip(group_cols, keys))
        by_split = {row.split: row for row in group.itertuples(index=False)}
        counts = {}
        signs = []
        waits = []
        for split in SPLITS:
            row = by_split.get(split)
            count = int(row.fresh_step_count) if row is not None and pd.notna(row.fresh_step_count) else 0
            counts[split] = count
            payload[f"{split}_fresh_step_count"] = count
            payload[f"{split}_seed_anchor_big_winner_rate"] = row.seed_anchor_big_winner_rate if row is not None else np.nan
            payload[f"{split}_seed_P_good"] = row.seed_P_good if row is not None else np.nan
            payload[f"{split}_seed_P_bad"] = row.seed_P_bad if row is not None else np.nan
            payload[f"{split}_wait_return_p50"] = row.wait_return_to_fresh_entry_p50 if row is not None else np.nan
            if row is not None:
                signs.append(_sign(row.seed_P_good - row.seed_P_bad))
                waits.append(row.wait_return_to_fresh_entry_p50)
        if any(counts[s] == 0 for s in SPLITS):
            denom_status = "split_missing"
        elif any(counts[s] < int(thresholds["N_min_family_set_exact"]) for s in SPLITS):
            denom_status = "denominator_thin"
        else:
            denom_status = "stable_descriptive"
        nonzero = [s for s in signs if s != 0]
        direction_status = "direction_only" if nonzero and len(set(nonzero)) == 1 else "unstable"
        wait_vals = pd.to_numeric(pd.Series(waits), errors="coerce").dropna()
        price_status = "stable_descriptive"
        if len(wait_vals) >= 2 and float(wait_vals.max() - wait_vals.min()) > 0.10:
            price_status = "price_unstable"
        if denom_status in {"split_missing", "denominator_thin"}:
            overall = denom_status
        elif price_status == "price_unstable":
            overall = "price_unstable"
        elif direction_status == "direction_only":
            overall = "stable_descriptive"
        else:
            overall = "unstable"
        payload.update(
            {
                "denominator_stability_status": denom_status,
                "direction_stability_status": direction_status,
                "price_stability_status": price_status,
                "overall_stability_status": overall,
            }
        )
        rows.append(payload)
    return pd.DataFrame(rows)


def _seed_vs_fresh_anchor_audit(fresh: pd.DataFrame, thresholds: dict[str, int]) -> pd.DataFrame:
    summary = _group_summary(
        fresh,
        ["kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket"],
        thresholds,
        fresh_grain=True,
    )
    if summary.empty:
        return summary
    summary["seed_to_fresh_big_winner_rate_gap"] = summary["seed_anchor_big_winner_rate"] - summary["fresh_anchor_big_winner_rate"]
    summary["seed_to_fresh_P_good_gap"] = summary["seed_P_good"] - summary["fresh_P_good"]
    summary["seed_to_fresh_P_bad_gap"] = summary["seed_P_bad"] - summary["fresh_P_bad"]
    notes = []
    for row in summary.itertuples(index=False):
        seed_edge = _num(row.seed_P_good) - _num(row.seed_P_bad)
        fresh_edge = _num(row.fresh_P_good) - _num(row.fresh_P_bad)
        if row.sample_sufficiency_status == "unusable":
            notes.append("insufficient_denominator")
        elif _num(row.wait_return_to_fresh_entry_p50) > 0.10 and fresh_edge <= seed_edge:
            notes.append("price_cost_high_confirmation_only")
        elif _num(row.fresh_anchor_big_winner_rate) >= _num(row.seed_anchor_big_winner_rate) and fresh_edge >= seed_edge:
            notes.append("fresh_anchor_remaining_opportunity_stronger")
        elif _num(row.seed_anchor_big_winner_rate) > _num(row.fresh_anchor_big_winner_rate) and seed_edge > fresh_edge:
            notes.append("seed_anchor_only_stronger")
        elif _num(row.seed_anchor_big_winner_rate) >= 0.15 and _num(row.fresh_anchor_big_winner_rate) >= 0.15:
            notes.append("both_strong")
        else:
            notes.append("path_only_not_big_winner")
    summary["interpretation_note_code"] = notes
    return summary[
        [
            "split",
            "kth_fresh_step_bucket",
            "kth_fresh_offset_bucket",
            "wait_return_bucket",
            "fresh_step_count",
            "unique_seed_episode_count",
            "unique_instrument_count",
            "unique_step_signal_date_count",
            "seed_anchor_big_winner_rate",
            "fresh_anchor_big_winner_rate",
            "seed_P_good",
            "seed_P_bad",
            "fresh_P_good",
            "fresh_P_bad",
            "seed_to_fresh_big_winner_rate_gap",
            "seed_to_fresh_P_good_gap",
            "seed_to_fresh_P_bad_gap",
            "interpretation_note_code",
        ]
    ]


def _survival_price_bias_audit(seeds: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    first = fresh.sort_values(["seed_episode_id", "step_offset", "step_signal_date"]).drop_duplicates("seed_episode_id")
    first_map_offset = first.set_index("seed_episode_id")["step_offset"].to_dict()
    first_map_wait = first.set_index("seed_episode_id")["wait_return_to_fresh_entry"].to_dict()
    rows = []
    for split in ALL_SPLITS:
        part = seeds if split == "all" else seeds.loc[seeds["split"].eq(split)]
        failure = pd.to_numeric(part["observable_failure_offset"], errors="coerce")
        first_offset = part["seed_episode_id"].map(first_map_offset)
        has_fresh = first_offset.notna()
        first_wait = pd.to_numeric(part["seed_episode_id"].map(first_map_wait), errors="coerce")
        rows.append(
            {
                "split": split,
                "seed_episode_count": int(len(part)),
                "failed_before_t3": int((failure.notna() & (failure < 3)).sum()),
                "failed_t3_to_t5": int(failure.between(3, 5, inclusive="both").sum()),
                "failed_t6_to_t10": int(failure.between(6, 10, inclusive="both").sum()),
                "failed_t11_to_t20": int(failure.between(11, 20, inclusive="both").sum()),
                "failed_t21_to_t30": int(failure.between(21, 30, inclusive="both").sum()),
                "failed_before_first_clean_fresh_count": int((failure.notna() & (first_offset.isna() | (failure < first_offset))).sum()),
                "no_clean_fresh_episode_count": int((~has_fresh).sum()),
                "first_clean_fresh_episode_count": int(has_fresh.sum()),
                "survived_t30_no_fresh": int((failure.isna() & (~has_fresh)).sum()),
                "survived_t30_with_fresh": int((failure.isna() & has_fresh).sum()),
                "first_clean_fresh_wait_return_p25": _quantile(first_wait, 0.25),
                "first_clean_fresh_wait_return_p50": _quantile(first_wait, 0.50),
                "first_clean_fresh_wait_return_p75": _quantile(first_wait, 0.75),
                "first_clean_fresh_wait_up_gt_10pct_rate": _pct(first_wait > 0.10, int(has_fresh.sum())),
                "first_clean_fresh_wait_up_gt_20pct_rate": _pct(first_wait > 0.20, int(has_fresh.sum())),
            }
        )
    return pd.DataFrame(rows)


def _outcome_value(row: pd.Series, outcome_family: str) -> float:
    if outcome_family == "seed_anchor_big_winner":
        return _num(row.get("seed_anchor_big_winner_rate"))
    if outcome_family == "fresh_anchor_big_winner":
        return _num(row.get("fresh_anchor_big_winner_rate"))
    if outcome_family == "seed_path_good_bad":
        return _num(row.get("seed_P_good")) - _num(row.get("seed_P_bad"))
    if outcome_family == "fresh_path_good_bad":
        return _num(row.get("fresh_P_good")) - _num(row.get("fresh_P_bad"))
    return np.nan


def _outcome_denominator(row: pd.Series, outcome_family: str) -> int:
    if outcome_family == "seed_anchor_big_winner":
        return int(_num(row.get("seed_anchor_big_winner_denominator")) or 0)
    if outcome_family == "fresh_anchor_big_winner":
        return int(_num(row.get("fresh_anchor_big_winner_denominator")) or 0)
    if outcome_family == "seed_path_good_bad":
        return int(_num(row.get("seed_path_denominator")) or 0)
    if outcome_family == "fresh_path_good_bad":
        return int(_num(row.get("fresh_path_denominator")) or 0)
    return 0


def _explanatory_for_scheme(
    df: pd.DataFrame,
    split: str,
    scheme: str,
    group_cols: list[str],
    parent_cols: list[str],
    thresholds: dict[str, int],
    fresh_grain: bool,
    wait_col: str,
    step_date_col: str | None,
) -> list[dict[str, Any]]:
    base = df if split == "all" else df.loc[df["split"].eq(split)]
    if base.empty:
        return []
    bucket_summary = _group_summary(base.assign(split=split), group_cols, thresholds, fresh_grain, wait_col, step_date_col)
    bucket_summary = bucket_summary.loc[bucket_summary["split"].eq(split)].copy()
    parent_summary = _group_summary(base.assign(split=split), parent_cols, thresholds, fresh_grain, wait_col, step_date_col)
    parent_summary = parent_summary.loc[parent_summary["split"].eq(split)].copy()
    rows = []
    for outcome_family in ["seed_anchor_big_winner", "seed_path_good_bad", "fresh_anchor_big_winner", "fresh_path_good_bad"]:
        den_total = 0
        weighted_abs = 0.0
        max_pos = np.nan
        max_neg = np.nan
        lift_values = []
        evaluated = []
        for _, bucket in bucket_summary.iterrows():
            if parent_cols:
                parent_mask = np.ones(len(parent_summary), dtype=bool)
                for col in parent_cols:
                    parent_mask &= parent_summary[col].astype(str).eq(str(bucket[col])).to_numpy()
                parent_part = parent_summary.loc[parent_mask]
            else:
                parent_part = parent_summary
            if parent_part.empty:
                continue
            parent = parent_part.iloc[0]
            den = _outcome_denominator(bucket, outcome_family)
            value = _outcome_value(bucket, outcome_family)
            parent_value = _outcome_value(parent, outcome_family)
            if den <= 0 or pd.isna(value) or pd.isna(parent_value):
                continue
            lift = value - parent_value
            den_total += den
            weighted_abs += den * abs(lift)
            lift_values.append(lift)
            evaluated.append((den, bucket.get("sample_sufficiency_status") == "sufficient"))
        if den_total:
            max_pos = max(lift_values) if lift_values else np.nan
            max_neg = min(lift_values) if lift_values else np.nan
        price_cov = 1.0
        if "wait_bucket" in scheme:
            if wait_col in base.columns:
                price_cov = _safe_div(int(pd.to_numeric(base[wait_col], errors="coerce").notna().sum()), len(base))
            elif "wait_return_to_latest_fresh_entry_before_or_at_checkpoint" in base.columns:
                price_cov = _safe_div(
                    int(pd.to_numeric(base["wait_return_to_latest_fresh_entry_before_or_at_checkpoint"], errors="coerce").notna().sum()),
                    len(base),
                )
        rows.append(
            {
                "split": split,
                "grouping_scheme": scheme,
                "outcome_family": outcome_family,
                "evaluated_row_count": int(den_total),
                "evaluated_bucket_count": int(len(evaluated)),
                "sufficient_bucket_count": int(sum(1 for _, sufficient in evaluated if sufficient)),
                "thin_or_sparse_bucket_count": int(sum(1 for _, sufficient in evaluated if not sufficient)),
                "weighted_abs_lift_vs_parent": _safe_div(weighted_abs, den_total),
                "max_positive_lift_vs_parent": max_pos,
                "max_negative_lift_vs_parent": max_neg,
                "direction_consistent_bucket_count": int(sum(1 for lift in lift_values if lift >= 0)),
                "direction_inconsistent_bucket_count": int(sum(1 for lift in lift_values if lift < 0)),
                "price_bucket_coverage_rate": price_cov,
                "interpretation_status": "insufficient_denominator",
            }
        )
    return rows


def _grouping_explanatory_power(checkpoint: pd.DataFrame, fresh: pd.DataFrame, pooling: pd.DataFrame, thresholds: dict[str, int]) -> pd.DataFrame:
    cp = checkpoint.copy()
    cp["latest_kth_offset_key"] = (
        cp["latest_clean_fresh_kth_fresh_step_bucket_before_or_at_checkpoint"].astype(str)
        + "|"
        + cp["latest_clean_fresh_kth_fresh_offset_bucket_before_or_at_checkpoint"].astype(str)
    )
    fresh2 = fresh.copy()
    fresh2["kth_offset_key"] = fresh2["kth_fresh_step_bucket"].astype(str) + "|" + fresh2["kth_fresh_offset_bucket"].astype(str)
    rows: list[dict[str, Any]] = []
    schemes = [
        (
            cp,
            "checkpoint_fresh_count",
            ["checkpoint", "fresh_distinct_family_count_bucket"],
            ["checkpoint"],
            False,
            "wait_return_to_latest_fresh_entry_before_or_at_checkpoint",
            "latest_clean_fresh_step_signal_date_before_or_at_checkpoint",
        ),
        (
            cp,
            "checkpoint_latest_kth_offset",
            ["checkpoint", "latest_kth_offset_key"],
            ["checkpoint"],
            False,
            "wait_return_to_latest_fresh_entry_before_or_at_checkpoint",
            "latest_clean_fresh_step_signal_date_before_or_at_checkpoint",
        ),
        (
            cp,
            "checkpoint_latest_kth_offset_wait_bucket",
            ["checkpoint", "latest_kth_offset_key", "wait_return_bucket_before_or_at_checkpoint"],
            ["checkpoint", "latest_kth_offset_key"],
            False,
            "wait_return_to_latest_fresh_entry_before_or_at_checkpoint",
            "latest_clean_fresh_step_signal_date_before_or_at_checkpoint",
        ),
        (fresh2, "kth_offset", ["kth_offset_key"], [], True, "wait_return_to_fresh_entry", "step_signal_date"),
        (
            fresh2,
            "kth_offset_wait_bucket",
            ["kth_offset_key", "wait_return_bucket"],
            ["kth_offset_key"],
            True,
            "wait_return_to_fresh_entry",
            "step_signal_date",
        ),
        (pooling, "family_set_pooling", ["pooling_level", "pooling_key"], ["pooling_level"], True, "wait_return_to_fresh_entry", "step_signal_date"),
        (
            pooling,
            "family_set_pooling_wait_bucket",
            ["pooling_level", "pooling_key", "wait_return_bucket"],
            ["pooling_level", "wait_return_bucket"],
            True,
            "wait_return_to_fresh_entry",
            "step_signal_date",
        ),
    ]
    for split in ALL_SPLITS:
        for source, scheme, group_cols, parent_cols, fresh_grain, wait_col, step_date_col in schemes:
            rows.extend(
                _explanatory_for_scheme(
                    source,
                    split,
                    scheme,
                    group_cols,
                    parent_cols,
                    thresholds,
                    fresh_grain,
                    wait_col,
                    step_date_col,
                )
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    for idx, row in out.iterrows():
        if row["evaluated_row_count"] < int(thresholds["N_min_too_sparse"]) or row["evaluated_bucket_count"] == 0:
            out.at[idx, "interpretation_status"] = "insufficient_denominator"
            continue
        if row["grouping_scheme"] in {"checkpoint_latest_kth_offset", "checkpoint_latest_kth_offset_wait_bucket"}:
            base = out.loc[
                out["split"].eq(row["split"])
                & out["outcome_family"].eq(row["outcome_family"])
                & out["grouping_scheme"].eq("checkpoint_fresh_count")
            ]
            base_value = _num(base.iloc[0]["weighted_abs_lift_vs_parent"]) if not base.empty else np.nan
            value = _num(row["weighted_abs_lift_vs_parent"])
            if pd.isna(base_value) or base_value == 0:
                out.at[idx, "interpretation_status"] = "descriptive_similar_to_fresh_count"
            elif value > base_value * 1.10:
                out.at[idx, "interpretation_status"] = "descriptive_more_informative_than_fresh_count"
            elif value < base_value * 0.90:
                out.at[idx, "interpretation_status"] = "descriptive_weaker_than_fresh_count"
            else:
                out.at[idx, "interpretation_status"] = "descriptive_similar_to_fresh_count"
        else:
            out.at[idx, "interpretation_status"] = "descriptive_similar_to_fresh_count"
    return out


def _format_pct(value: Any) -> str:
    num = _num(value)
    return "NA" if pd.isna(num) else f"{num:.2%}"


def _format_num(value: Any) -> str:
    num = _num(value)
    return "NA" if pd.isna(num) else f"{num:.4f}"


def _report_table(df: pd.DataFrame, cols: list[str], max_rows: int = 8) -> str:
    if df.empty:
        return "无可报告行。"
    cols = [col for col in cols if col in df.columns]
    return df[cols].head(max_rows).to_markdown(index=False)


def _final_report(
    decision: str,
    fresh: pd.DataFrame,
    wait_summary: pd.DataFrame,
    fresh_count_summary: pd.DataFrame,
    kth_summary: pd.DataFrame,
    explanatory: pd.DataFrame,
    family_summary: pd.DataFrame,
    stability: pd.DataFrame,
    seed_fresh_audit: pd.DataFrame,
    survival: pd.DataFrame,
) -> str:
    all_wait = wait_summary.loc[wait_summary["split"].eq("all")].copy()
    first_wait = all_wait.loc[all_wait["kth_fresh_step_bucket"].eq("1")]
    high_wait = kth_summary.loc[kth_summary["split"].eq("all") & kth_summary["wait_return_bucket"].isin(["up_10_20pct", "up_gt_20pct"])]
    checkpoint_compare = explanatory.loc[
        explanatory["split"].isin(["validation", "robustness"])
        & explanatory["grouping_scheme"].isin(
            ["checkpoint_fresh_count", "checkpoint_latest_kth_offset", "checkpoint_latest_kth_offset_wait_bucket"]
        )
        & explanatory["outcome_family"].isin(["seed_anchor_big_winner", "seed_path_good_bad"])
    ].copy()
    enough_family = family_summary.loc[
        family_summary["split"].eq("all") & family_summary["sample_sufficiency_status"].eq("sufficient")
    ].sort_values(["fresh_step_count"], ascending=False)
    stable_family = stability.loc[stability.get("overall_stability_status", pd.Series(dtype=object)).isin(["stable_descriptive", "direction_only"])]
    audit_all = seed_fresh_audit.loc[seed_fresh_audit["split"].eq("all")].copy()
    survival_all = survival.loc[survival["split"].eq("all")].iloc[0] if not survival.loc[survival["split"].eq("all")].empty else None

    lines = [
        "# R03c Price-Aware Kth-Fresh 与 Family-Set Pooling 诊断报告",
        "",
        f"Final decision: `{decision}`",
        "",
        "## 硬性边界",
        "",
        "本诊断明确区分 seed-anchor big-winner、fresh-anchor big-winner 和 path labels。",
        "P_good / P_bad 不得解读为 P(big winner | signal)。",
        "fresh-anchor outcome 不能替代 seed-anchor outcome。",
        "不同 row grain 的 explanatory-power lift 不得直接比较。",
        "",
        "本实验不产出 production signal。",
        "本实验不产出 entry rule。",
        "本实验不产出 position size。",
        "本实验不产出 R03 risk-budget allocation。",
        "",
        "## 1. Fresh-count 加入价格后是否仍然成立",
        "",
        "fresh-count price-conditioned 表保留 no_fresh、missing_or_invalid 和 latest clean fresh price bucket；primary outcome 仍是 seed-anchor outcome。下面是 all split 的前排行：",
        "",
        _report_table(
            fresh_count_summary.loc[fresh_count_summary["split"].eq("all")].sort_values(
                ["checkpoint", "fresh_distinct_family_count_bucket", "wait_return_bucket_before_or_at_checkpoint"]
            ),
            [
                "checkpoint",
                "fresh_distinct_family_count_bucket",
                "wait_return_bucket_before_or_at_checkpoint",
                "seed_episode_count",
                "seed_anchor_big_winner_rate",
                "seed_P_good",
                "seed_P_bad",
                "fresh_anchor_big_winner_rate",
                "wait_return_to_fresh_entry_p50",
            ],
        ),
        "",
        "## 2. 第 k 个 fresh step 的等待价格分布",
        "",
        _report_table(
            all_wait.sort_values(["kth_fresh_step_bucket", "kth_fresh_offset_bucket"]),
            [
                "kth_fresh_step_bucket",
                "kth_fresh_offset_bucket",
                "fresh_step_count",
                "wait_return_to_fresh_entry_p25",
                "wait_return_to_fresh_entry_p50",
                "wait_return_to_fresh_entry_p75",
                "pct_wait_up_5_10pct",
                "pct_wait_up_10_20pct",
                "pct_wait_up_gt_20pct",
            ],
        ),
        "",
        "## 3. Checkpoint-aligned explanatory power",
        "",
        "下面只比较 checkpoint-aligned schemes；fresh-step grain 与 pooling grain 的 lift 不在这里直接横向比较。",
        "",
        _report_table(
            checkpoint_compare.sort_values(["split", "outcome_family", "grouping_scheme"]),
            [
                "split",
                "grouping_scheme",
                "outcome_family",
                "evaluated_row_count",
                "weighted_abs_lift_vs_parent",
                "interpretation_status",
            ],
            max_rows=18,
        ),
        "",
        "## 4. 高 wait-return 是否只是 late confirmation",
        "",
        "price bucket 已经上涨超过 10% 或 20% 的行被单独保留，不能和低 wait-cost bucket 混合解释。以下 all split 行用于观察 fresh-anchor 剩余空间：",
        "",
        _report_table(
            high_wait.sort_values(["wait_return_bucket", "fresh_step_count"], ascending=[True, False]),
            [
                "kth_fresh_step_bucket",
                "kth_fresh_offset_bucket",
                "wait_return_bucket",
                "fresh_step_count",
                "fresh_anchor_big_winner_rate",
                "fresh_P_good",
                "fresh_P_bad",
                "fresh_max_gain_120d_p50",
                "fresh_max_drawdown_120d_p50",
            ],
        ),
        "",
        "## 5. Family-set pooling denominator",
        "",
        "R03c V1 只启用 fresh_added_family_set、cumulative_family_set_after_step、family_presence_signature；不启用 family_role_set。",
        "",
        _report_table(
            enough_family,
            [
                "pooling_level",
                "pooling_key",
                "kth_fresh_step_bucket",
                "kth_fresh_offset_bucket",
                "wait_return_bucket",
                "fresh_step_count",
                "split_denominator_share",
                "seed_anchor_big_winner_rate",
                "seed_P_good",
                "seed_P_bad",
                "wait_return_to_fresh_entry_p50",
                "split_stability_status",
            ],
        ),
        "",
        "## 6. Validation / robustness 方向一致的 family-set",
        "",
        _report_table(
            stable_family.sort_values(["overall_stability_status", "train_fresh_step_count"], ascending=[True, False]),
            [
                "pooling_level",
                "pooling_key",
                "kth_fresh_step_bucket",
                "kth_fresh_offset_bucket",
                "wait_return_bucket",
                "train_fresh_step_count",
                "validation_fresh_step_count",
                "robustness_fresh_step_count",
                "direction_stability_status",
                "price_stability_status",
                "overall_stability_status",
            ],
        ),
        "",
        "## 7. Family-set 是否依赖高 wait-return",
        "",
        "family-set summary 按 wait_return_bucket 展开；如果同一 pooling_key 只在 up_10_20pct 或 up_gt_20pct 有表现，应解读为 late confirmation 风险，而不是更早可执行的 family-set rule。",
        "",
        "## 8. Seed-anchor 与 fresh-anchor 是否一致",
        "",
        "fresh-anchor label 的 horizon 从 fresh signal date 开始，不能直接替代 seed-anchor label。",
        "",
        _report_table(
            audit_all.sort_values(["kth_fresh_step_bucket", "kth_fresh_offset_bucket", "wait_return_bucket"]),
            [
                "kth_fresh_step_bucket",
                "kth_fresh_offset_bucket",
                "wait_return_bucket",
                "fresh_step_count",
                "seed_anchor_big_winner_rate",
                "fresh_anchor_big_winner_rate",
                "seed_P_good",
                "fresh_P_good",
                "interpretation_note_code",
            ],
        ),
        "",
        "## 9. 是否值得进入下一阶段",
        "",
        "本轮结果可以作为 formal validation protocol 的候选诊断输入，但不能直接冻结任何 entry timing、family-set 或 position rule。下一阶段若继续，应固定 checkpoint-aligned 对比口径，并把高 wait-return bucket 作为 late-confirmation 风险单独约束。",
        "",
        "## Survival Price Bias",
        "",
    ]
    if survival_all is not None:
        lines.extend(
            [
                f"- all split seed episodes: {int(survival_all.seed_episode_count):,}",
                f"- failed_before_first_clean_fresh_count: {int(survival_all.failed_before_first_clean_fresh_count):,}",
                f"- no_clean_fresh_episode_count: {int(survival_all.no_clean_fresh_episode_count):,}",
                f"- first clean fresh wait return p50: {_format_pct(survival_all.first_clean_fresh_wait_return_p50)}",
            ]
        )
    lines.extend(
        [
            "",
            "## Anchor Mapping 说明",
            "",
            "fresh_anchor_big_winner headline 使用 precision panel 的 close-anchor `fresh_big_winner_forward_h120_close_anchor`。",
            "fresh path headline 使用 path-query CSV 的 entry-anchored `fresh_path_label` 与 fresh path metrics。",
            "`fresh_big_winner_forward_h120_close_anchor` 与 `fresh_close_return_t20` 属于不同 price anchor，不得混成同一个可执行收益口径。",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_validation_audit(
    reports_dir: Path,
    config: dict[str, Any],
    seeds: pd.DataFrame,
    clean: pd.DataFrame,
    fresh: pd.DataFrame,
    checkpoint: pd.DataFrame,
    pooling: pd.DataFrame,
    reconciliation: pd.DataFrame,
    decision: str,
) -> pd.DataFrame:
    thresholds = {k: int(v) for k, v in config["sample_sufficiency"].items()}
    rows: list[dict[str, Any]] = []
    r03b_manifest = _read_json(config["upstream_r03b"]["manifest"])
    all_fresh = fresh
    fresh_bw_den = int(_boolish(all_fresh.get("fresh_complete_h120_close_anchor_flag", pd.Series(dtype=object))).sum())
    fresh_path_den = int(all_fresh.get("fresh_path_label", pd.Series(dtype=object)).isin(PATH_LABELS).sum())
    required_split_counts = seeds["split"].value_counts().to_dict()
    _add_validation_row(rows, "upstream_r03b_validation_passed", "input", _read_json(config["upstream_r03b"]["validation"]).get("validation_status") == "passed", "fatal", "R03b validation failed", 1, config["upstream_r03b"]["validation"])
    _add_validation_row(rows, "upstream_path_validation_passed", "input", _read_json(config["upstream_path_query"]["validation"]).get("validation_status") == "passed", "fatal", "R02 path validation failed", 1, config["upstream_path_query"]["validation"])
    _add_validation_row(rows, "upstream_precision_validation_passed", "input", _read_json(config["upstream_precision"]["validation"]).get("validation_status") == "passed", "fatal", "R02 precision validation failed", 1, config["upstream_precision"]["validation"])
    _add_validation_row(rows, "price_reconciliation_passed", "reconciliation", reconciliation["reconciliation_status"].eq("passed").all(), "fatal", "fresh step price/path reconciliation failed", int(reconciliation["reconciliation_status"].ne("passed").sum()), relpath(reports_dir / "r03c_price_reconciliation_audit.csv"))
    _add_validation_row(rows, "seed_count_matches_r03b", "denominator", len(seeds) == int(r03b_manifest.get("seed_episode_count", -1)), "fatal", "R03b seed count mismatch", abs(len(seeds) - int(r03b_manifest.get("seed_episode_count", -1))), config["upstream_r03b"]["manifest"])
    _add_validation_row(rows, "clean_primary_fresh_denominator_usable", "denominator", len(clean) >= thresholds["N_min_too_sparse"], "fatal", "all-split clean primary fresh step count below N_min_too_sparse", len(clean), relpath(reports_dir))
    _add_validation_row(rows, "fresh_anchor_big_winner_denominator_usable", "denominator", fresh_bw_den >= thresholds["N_min_too_sparse"], "fatal", "fresh-anchor big-winner denominator below N_min_too_sparse", fresh_bw_den, relpath(reports_dir))
    _add_validation_row(rows, "fresh_path_denominator_usable", "denominator", fresh_path_den >= thresholds["N_min_too_sparse"], "fatal", "fresh path denominator below N_min_too_sparse", fresh_path_den, relpath(reports_dir))
    missing_splits = [split for split in SPLITS if int(required_split_counts.get(split, 0)) == 0]
    _add_validation_row(rows, "required_splits_have_seed_episodes", "denominator", not missing_splits, "fatal", f"missing splits: {missing_splits}", len(missing_splits), relpath(reports_dir))
    _add_validation_row(rows, "fresh_panel_no_no_fresh_bucket", "schema", not fresh.get("wait_return_bucket", pd.Series(dtype=object)).eq("no_fresh").any(), "error", "no_fresh bucket appeared in fresh-step panel", int(fresh.get("wait_return_bucket", pd.Series(dtype=object)).eq("no_fresh").sum()), relpath(reports_dir / "r03c_fresh_step_price_panel.parquet"))
    _add_validation_row(rows, "checkpoint_no_fresh_retained", "schema", checkpoint["wait_return_bucket_before_or_at_checkpoint"].eq("no_fresh").any(), "error", "checkpoint no_fresh rows missing", 0, relpath(reports_dir / "r03c_checkpoint_price_state_panel.parquet"))
    _add_validation_row(rows, "family_role_set_absent", "schema", not any("family_role_set" in col for df in [fresh, checkpoint, pooling] for col in df.columns), "error", "family_role_set appeared in R03c V1 outputs", 1, relpath(reports_dir))
    _add_validation_row(rows, "family_presence_signature_source_present", "schema", "cumulative_distinct_family_set_after_step" in pooling.columns, "error", "pooling panel missing cumulative source field", 1, relpath(reports_dir / "r03c_family_set_pooling_panel.parquet"))
    _add_validation_row(rows, "decision_allowed", "manifest", decision in ALLOWED_DECISIONS, "fatal", f"unexpected decision {decision}", 1, relpath(reports_dir))
    audit = pd.DataFrame(rows)
    _write_csv(audit, reports_dir / "r03c_price_aware_pooling_validation_audit.csv")
    return audit


def _blocked_manifest(config: dict[str, Any], decision: str, reports_dir: Path, manifests_dir: Path) -> dict[str, Any]:
    manifest = {
        "requirement_id": config["requirement_id"],
        "short_name": config["short_name"],
        "final_decision": decision,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(manifest, manifests_dir / "r03c_price_aware_kth_fresh_family_set_pooling_manifest.json")
    validation = {
        "validation_status": "failed",
        "final_decision": decision,
        "failed_checks": [decision],
        "audit_path": relpath(reports_dir / "r03c_price_aware_pooling_validation_audit.csv"),
    }
    write_json(validation, manifests_dir / "r03c_price_aware_kth_fresh_family_set_pooling_validation.json")
    return manifest


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(Path(config["output_root"]))
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for path in [cache_dir, reports_dir, manifests_dir]:
        path.mkdir(parents=True, exist_ok=True)

    readiness, ok, decision = _readiness(config)
    _write_csv(readiness, reports_dir / "r03c_input_readiness_audit.csv")
    if not ok:
        _write_csv(
            pd.DataFrame(
                [
                    {
                        "check_id": decision,
                        "check_category": "input",
                        "status": "failed",
                        "severity": "fatal",
                        "failure_reason": decision,
                        "affected_rows": int(readiness["readiness_status"].ne("ready").sum()),
                        "artifact_path": relpath(reports_dir / "r03c_input_readiness_audit.csv"),
                    }
                ]
            ),
            reports_dir / "r03c_price_aware_pooling_validation_audit.csv",
        )
        return _blocked_manifest(config, decision, reports_dir, manifests_dir)

    print("r03c: loading upstream panels complete readiness", file=sys.stderr, flush=True)
    seeds, step, checkpoint_raw, timeline, path_df, precision = _load_inputs(config)
    print("r03c: inputs loaded", file=sys.stderr, flush=True)
    clean = _build_clean_steps(seeds, step, config)
    fresh, reconciliation, recon_ok = _build_fresh_panel(clean, path_df, precision, config)
    _write_csv(reconciliation, reports_dir / "r03c_price_reconciliation_audit.csv")
    if not recon_ok:
        return _blocked_manifest(config, "blocked_price_reconciliation_failed", reports_dir, manifests_dir)

    checkpoint = _build_checkpoint_panel(checkpoint_raw, seeds, fresh)
    pooling = _build_pooling_panel(fresh)
    thresholds = {k: int(v) for k, v in config["sample_sufficiency"].items()}
    print("r03c: row-level panels built", file=sys.stderr, flush=True)

    wait_summary = _wait_movement_summary(fresh, thresholds)
    fresh_count_summary = _group_summary(
        checkpoint,
        ["checkpoint", "fresh_distinct_family_count_bucket", "wait_return_bucket_before_or_at_checkpoint"],
        thresholds,
        fresh_grain=False,
        wait_col="wait_return_to_latest_fresh_entry_before_or_at_checkpoint",
        step_date_col="latest_clean_fresh_step_signal_date_before_or_at_checkpoint",
    )
    kth_summary = _kth_offset_summary(fresh, thresholds)
    family_summary, stability = _family_set_summary(pooling, thresholds)
    seed_fresh_audit = _seed_vs_fresh_anchor_audit(fresh, thresholds)
    survival = _survival_price_bias_audit(seeds, fresh)
    print("r03c: headline summaries built", file=sys.stderr, flush=True)
    explanatory = _grouping_explanatory_power(checkpoint, fresh, pooling, thresholds)
    print("r03c: explanatory comparison built", file=sys.stderr, flush=True)

    _write_parquet(fresh, cache_dir / "r03c_fresh_step_price_panel.parquet")
    _write_parquet(checkpoint, cache_dir / "r03c_checkpoint_price_state_panel.parquet")
    _write_parquet(pooling, cache_dir / "r03c_family_set_pooling_panel.parquet")
    _write_csv(wait_summary, reports_dir / "r03c_wait_price_movement_summary.csv")
    _write_csv(fresh_count_summary, reports_dir / "r03c_fresh_count_price_conditioned_summary.csv")
    _write_csv(kth_summary, reports_dir / "r03c_kth_offset_price_summary.csv")
    _write_csv(explanatory, reports_dir / "r03c_grouping_explanatory_power_comparison.csv")
    _write_csv(family_summary, reports_dir / "r03c_family_set_pooling_summary.csv")
    _write_csv(stability, reports_dir / "r03c_family_set_split_stability_audit.csv")
    _write_csv(seed_fresh_audit, reports_dir / "r03c_seed_vs_fresh_anchor_outcome_audit.csv")
    _write_csv(survival, reports_dir / "r03c_survival_price_bias_audit.csv")

    decision = "descriptive_price_aware_pooling_diagnostic_complete"
    r03b_manifest = _read_json(config["upstream_r03b"]["manifest"])
    fresh_bw_den = int(_boolish(fresh["fresh_complete_h120_close_anchor_flag"]).sum())
    fresh_path_den = int(fresh["fresh_path_label"].isin(PATH_LABELS).sum())
    if (
        len(clean) < thresholds["N_min_too_sparse"]
        or fresh_bw_den < thresholds["N_min_too_sparse"]
        or fresh_path_den < thresholds["N_min_too_sparse"]
        or len(seeds) != int(r03b_manifest.get("seed_episode_count", -1))
        or any(int(seeds["split"].value_counts().get(split, 0)) == 0 for split in SPLITS)
    ):
        decision = "blocked_denominator_unusable"

    validation_audit = _write_validation_audit(reports_dir, config, seeds, clean, fresh, checkpoint, pooling, reconciliation, decision)
    if decision == "descriptive_price_aware_pooling_diagnostic_complete" and _validation_status(validation_audit.to_dict("records")) != "passed":
        decision = "invalid_requirement_violation"

    report = _final_report(
        decision,
        fresh,
        wait_summary,
        fresh_count_summary,
        kth_summary,
        explanatory,
        family_summary,
        stability,
        seed_fresh_audit,
        survival,
    )
    (reports_dir / "r03c_price_aware_pooling_final_report.md").write_text(report, encoding="utf-8")

    manifest = {
        "requirement_id": config["requirement_id"],
        "short_name": config["short_name"],
        "final_decision": decision,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "diagnostic_status": "descriptive_only",
        "frozen_families": config["frozen_families"],
        "splits": ALL_SPLITS,
        "checkpoints": [int(x) for x in config["sequence"]["checkpoints"]],
        "alpha_source": config["posterior"]["alpha_source"],
        "credible_interval_level": float(config["posterior"]["credible_interval_level"]),
        "seed_episode_count": int(len(seeds)),
        "clean_primary_fresh_step_count": int(len(clean)),
        "fresh_anchor_big_winner_denominator": fresh_bw_den,
        "fresh_path_denominator": fresh_path_den,
        "row_grain_notes": {
            "fresh_step_price_panel": "one row per clean primary fresh step",
            "checkpoint_price_state_panel": "one row per seed_episode_id x checkpoint",
            "family_set_pooling_panel": "one row per fresh step x pooling level",
        },
        "input_hashes": {
            "config": _hash_file(topic_path(config_path)),
            "r03b_manifest": _hash_file(topic_path(Path(config["upstream_r03b"]["manifest"]))),
            "path_query_manifest": _hash_file(topic_path(Path(config["upstream_path_query"]["manifest"]))),
            "precision_manifest": _hash_file(topic_path(Path(config["upstream_precision"]["manifest"]))),
        },
        "output_files": {
            "fresh_step_price_panel": relpath(cache_dir / "r03c_fresh_step_price_panel.parquet"),
            "checkpoint_price_state_panel": relpath(cache_dir / "r03c_checkpoint_price_state_panel.parquet"),
            "family_set_pooling_panel": relpath(cache_dir / "r03c_family_set_pooling_panel.parquet"),
            "final_report": relpath(reports_dir / "r03c_price_aware_pooling_final_report.md"),
            "validation_audit": relpath(reports_dir / "r03c_price_aware_pooling_validation_audit.csv"),
        },
    }
    write_json(manifest, manifests_dir / "r03c_price_aware_kth_fresh_family_set_pooling_manifest.json")
    validation = {
        "validation_status": _validation_status(validation_audit.to_dict("records")),
        "final_decision": decision,
        "failed_checks": validation_audit.loc[validation_audit["status"].eq("failed"), "check_id"].tolist(),
        "audit_path": relpath(reports_dir / "r03c_price_aware_pooling_validation_audit.csv"),
    }
    write_json(validation, manifests_dir / "r03c_price_aware_kth_fresh_family_set_pooling_validation.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    manifest = run(args.config)
    print(
        json.dumps(
            {
                "final_decision": manifest.get("final_decision"),
                "seed_episode_count": manifest.get("seed_episode_count"),
                "clean_primary_fresh_step_count": manifest.get("clean_primary_fresh_step_count"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

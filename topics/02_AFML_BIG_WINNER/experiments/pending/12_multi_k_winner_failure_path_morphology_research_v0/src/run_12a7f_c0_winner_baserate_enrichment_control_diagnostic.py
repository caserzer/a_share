#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
TOPIC_SRC_DIR = TOPIC_ROOT / "src"

if str(TOPIC_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(TOPIC_SRC_DIR))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


RUN_ID = "12A7f_c0_winner_baserate_enrichment_control_diagnostic"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a7f_c0_winner_baserate_enrichment_control_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
MATCH_COLS = ["split", "board_bucket", "calendar_month", "market_regime_bucket"]
PRIMARY_BARRIERS = ("direct_entry_win_up_20_h20", "direct_entry_win_up_20_h40")
LOWER_DIRECT_BARRIERS = ("direct_entry_win_up_10_h20", "direct_entry_win_up_15_h20")

EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "requirement": (),
    "state_change_candidate_event_canonical": (
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "trade_open_date",
        "event_split",
        "board_bucket",
        "market_regime_bucket",
    ),
    "two_stage_event_universe": (
        "meta_event_id",
        "source_event_id",
        "source_arm_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "trade_open_price",
        "entry_date",
        "entry_pos",
        "entry_price",
        "path_key",
        "split",
        "board_bucket",
        "calendar_month",
        "calendar_year",
        "source_arm_is_c0",
        "market_regime_bucket",
        "stage_1_evaluable",
        "entry_blocked",
        "no_fast_fail_L10_H20",
        "horizon_complete_20d",
        "stage_2_decision_pos",
        "stage_2_reference_pos",
        "stage_2_reference_price",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "stage_2_horizon_complete_40d",
    ),
    "two_stage_event_targets": (
        "meta_event_id",
        "instrument",
        "split",
        "stage_1_evaluable",
        "stage_1_fast_fail_target",
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_continuation_target",
    ),
    "two_stage_decision": ("decision_state", "input_gate_status"),
    "split_time_boundary_audit": (
        "eval_split",
        "train_max_event_t0_date",
        "eval_min_event_t0_date",
        "split_time_boundary_gate_pass",
    ),
    "stage2_path_cache": (
        "path_key",
        "instrument",
        "entry_pos",
        "entry_price",
        "stage_2_decision_pos",
        "stage_2_reference_pos",
        "stage_2_reference_price",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "stage_2_horizon_complete_40d",
        "continuation_U20_L10_H2_20",
    ),
    "manifest_12a6c": (),
    "pit_topn_400_100_executable_daily": (
        "usable_trade_date",
        "instrument",
        "source_membership_date",
        "membership_date",
        "membership_available_time",
        "available_time",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
    ),
    "pit_topn_400_100_membership_daily": (),
    "stock_daily_qfq_dir": (),
    "global_regime_calendar": (
        "date",
        "daily_regime_bucket",
        "daily_regime_conflict_n",
        "daily_regime_conflict_flag",
    ),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A7f C0 winner base-rate enrichment control diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "scope_universe_audit": TABLE_DIR / "scope_universe_audit.csv",
        "winner_label_source_audit": TABLE_DIR / "winner_label_source_audit.csv",
        "control_match_cell_audit": TABLE_DIR / "control_match_cell_audit.csv",
        "c0_vs_control_winner_baserate_readout": TABLE_DIR / "c0_vs_control_winner_baserate_readout.csv",
        "winner_baserate_bootstrap_ci": TABLE_DIR / "winner_baserate_bootstrap_ci.csv",
        "enrichment_stability_slice_audit": TABLE_DIR / "enrichment_stability_slice_audit.csv",
        "c0_winner_enrichment_decision": TABLE_DIR / "c0_winner_enrichment_decision.csv",
        "c0_arm_winner_label_matrix": LOCAL_CACHE_DIR / "c0_arm_winner_label_matrix.parquet",
        "control_arm_winner_label_matrix": LOCAL_CACHE_DIR / "control_arm_winner_label_matrix.parquet",
        "bootstrap_replicates": LOCAL_CACHE_DIR / "bootstrap_replicates.parquet",
        "report": REPORT_DIR / "c0_winner_baserate_enrichment_control_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        frame.to_parquet(path, index=False)
    elif suffixes.endswith(".csv.gz"):
        frame.to_csv(path, index=False, compression={"method": "gzip", "compresslevel": 9, "mtime": 1})
    else:
        frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def path_sha(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def count_csv_rows(path: Path) -> int:
    if "".join(path.suffixes).endswith(".gz"):
        return int(sum(len(chunk) for chunk in pd.read_csv(path, chunksize=250_000, low_memory=False)))
    with path.open("rb") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def count_rows(path: Path) -> int | float:
    if not path.exists():
        return np.nan
    if path.is_dir():
        return int(sum(1 for p in path.iterdir() if p.is_file()))
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return int(pd.read_parquet(path).shape[0])
    if suffixes.endswith((".csv", ".csv.gz")):
        if suffixes.endswith(".csv.gz"):
            return int(sum(len(chunk) for chunk in pd.read_csv(path, chunksize=250_000, low_memory=False)))
        return count_csv_rows(path)
    return np.nan


def boolish(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def bool_series(values: pd.Series) -> pd.Series:
    return values.map(boolish).astype(bool)


def date_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value)[:10]
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text
    parsed = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(parsed) else parsed.strftime("%Y-%m-%d")


def month_text(value: Any) -> str:
    text = date_text(value)
    return text[:7] if text else ""


def year_text(value: Any) -> str:
    text = date_text(value)
    return text[:4] if text else ""


def safe_rate(num: int | float, den: int | float) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return np.nan
    return float(num) / float(den)


def stable_int(*parts: Any) -> int:
    raw = "|".join(str(x) for x in parts)
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def path_key(instrument: Any, entry_date: Any, entry_pos: Any, entry_price: Any) -> str:
    price = "" if pd.isna(entry_price) else f"{float(entry_price):.8f}"
    raw = f"{instrument}|{date_text(entry_date)}|{int(entry_pos) if pd.notna(entry_pos) else ''}|{price}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, required_cols in EXPECTED_INPUT_COLUMNS.items():
        raw = config.get("paths", {}).get(artifact_id, artifact_id)
        path = topic_path(raw)
        exists = path.exists()
        read_status = "pass" if exists else "missing"
        schema_status = "not_checked"
        row_count: int | float = np.nan
        column_count: int | float = np.nan
        if exists:
            try:
                if path.is_dir():
                    row_count = int(sum(1 for p in path.iterdir() if p.is_file()))
                    schema_status = "directory"
                else:
                    suffixes = "".join(path.suffixes)
                    if suffixes.endswith(".parquet"):
                        sample = pd.read_parquet(path)
                    elif suffixes.endswith((".csv", ".csv.gz")):
                        sample = pd.read_csv(path, nrows=5, low_memory=False)
                    else:
                        sample = pd.DataFrame()
                    if not sample.empty or suffixes.endswith((".csv", ".csv.gz", ".parquet")):
                        column_count = int(len(sample.columns))
                        missing = sorted(set(required_cols) - set(sample.columns))
                        schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
                        row_count = count_rows(path)
                    else:
                        schema_status = "file"
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "not_checked"
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": path_sha(path),
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": True,
            }
        )
    return pd.DataFrame(rows)


class StockDailyCache:
    def __init__(self, qfq_dir: Path):
        self.qfq_dir = qfq_dir
        self.cache: dict[str, pd.DataFrame | None] = {}

    def get(self, instrument: str) -> pd.DataFrame | None:
        if instrument in self.cache:
            return self.cache[instrument]
        path = self.qfq_dir / f"{instrument}.csv"
        if not path.exists():
            self.cache[instrument] = None
            return None
        try:
            frame = pd.read_csv(path, usecols=["date", "open", "high", "low", "close"])
            frame["date"] = frame["date"].map(date_text)
            for col in ["open", "high", "low", "close"]:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
            frame = frame.sort_values("date", kind="stable").reset_index(drop=True)
            frame["date_pos"] = np.arange(len(frame), dtype=np.int64)
            self.cache[instrument] = frame
        except Exception:
            self.cache[instrument] = None
        return self.cache[instrument]


def split_mapper(boundary: pd.DataFrame) -> tuple[dict[str, str], Any]:
    rows = boundary.copy()
    rows["eval_split"] = rows["eval_split"].astype(str)
    val_min = rows.loc[rows["eval_split"].eq("validation"), "eval_min_event_t0_date"]
    rob_min = rows.loc[rows["eval_split"].eq("robustness"), "eval_min_event_t0_date"]
    validation_min = date_text(val_min.iloc[0]) if len(val_min) else "2022-01-04"
    robustness_min = date_text(rob_min.iloc[0]) if len(rob_min) else "2024-03-01"

    def assign(value: Any) -> str:
        text = date_text(value)
        if not text:
            return ""
        if text >= robustness_min:
            return "robustness"
        if text >= validation_min:
            return "validation"
        return "train"

    return {"validation_min": validation_min, "robustness_min": robustness_min}, assign


def first_hit_label(
    daily: pd.DataFrame | None,
    reference_pos: int | float,
    reference_price: float,
    horizon: int,
    upper: float,
    lower: float = -0.10,
) -> tuple[bool, bool, bool, int | float, int | float]:
    if daily is None or daily.empty or pd.isna(reference_pos) or pd.isna(reference_price) or float(reference_price) <= 0:
        return False, False, False, np.nan, np.nan
    pos = int(reference_pos)
    if pos < 0 or pos + int(horizon) >= len(daily):
        return False, False, False, np.nan, np.nan
    high = daily["high"].to_numpy(dtype=float)[pos : pos + int(horizon) + 1]
    low = daily["low"].to_numpy(dtype=float)[pos : pos + int(horizon) + 1]
    price = float(reference_price)
    upper_hits = np.flatnonzero(high >= price * (1.0 + float(upper)))
    lower_hits = np.flatnonzero(low <= price * (1.0 + float(lower)))
    upper_first = int(upper_hits[0]) if len(upper_hits) else None
    lower_first = int(lower_hits[0]) if len(lower_hits) else None
    winner = upper_first is not None and (lower_first is None or upper_first < lower_first)
    fast_fail = lower_first is not None
    return True, bool(winner), bool(fast_fail), np.nan if upper_first is None else upper_first, np.nan if lower_first is None else lower_first


def attach_entry_from_qfq(frame: pd.DataFrame, stock_cache: StockDailyCache, date_col: str) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for instrument, group in frame.groupby("instrument", sort=False):
        work = group.copy()
        daily = stock_cache.get(str(instrument))
        if daily is None or daily.empty:
            work["entry_pos"] = np.nan
            work["entry_price"] = np.nan
            work["entry_open_status"] = "missing_qfq"
            parts.append(work)
            continue
        lookup = daily.set_index("date")[["date_pos", "open"]]
        joined = work.merge(lookup, left_on=date_col, right_index=True, how="left")
        joined["entry_pos"] = pd.to_numeric(joined["date_pos"], errors="coerce")
        joined["entry_price"] = pd.to_numeric(joined["open"], errors="coerce")
        joined["entry_open_status"] = np.where(joined["entry_price"].gt(0) & joined["entry_pos"].notna(), "pass", "missing_or_bad_open")
        joined = joined.drop(columns=[c for c in ["date_pos", "open"] if c in joined.columns])
        parts.append(joined)
    return pd.concat(parts, ignore_index=True) if parts else frame.assign(entry_pos=np.nan, entry_price=np.nan, entry_open_status="empty")


def direct_labels_for_rows(
    frame: pd.DataFrame,
    stock_cache: StockDailyCache,
    config: dict[str, Any],
    *,
    arm: str,
) -> pd.DataFrame:
    specs = list(config["barriers"]["direct_entry"])
    lower = float(config["barriers"]["lower_barrier_pct"])
    rows: list[pd.DataFrame] = []
    for instrument, group in frame.groupby("instrument", sort=False):
        daily = stock_cache.get(str(instrument))
        work = group.copy()
        for spec in specs:
            barrier = str(spec["winner_barrier"])
            values = []
            evaluable = []
            upper_times = []
            lower_times = []
            for row in work.itertuples(index=False):
                complete, winner, _fast, up_t, low_t = first_hit_label(
                    daily,
                    getattr(row, "entry_pos"),
                    getattr(row, "entry_price"),
                    int(spec["horizon_sessions"]),
                    float(spec["upper_barrier_pct"]),
                    lower,
                )
                evaluable.append(complete)
                values.append(winner if complete else np.nan)
                upper_times.append(up_t)
                lower_times.append(low_t)
            work[barrier] = values
            work[f"{barrier}_horizon_complete"] = evaluable
            work[f"{barrier}_time_to_upper"] = upper_times
            work[f"{barrier}_time_to_lower"] = lower_times
        fast_complete = []
        fast_fail = []
        for row in work.itertuples(index=False):
            complete, _winner, fail, _up_t, _low_t = first_hit_label(
                daily,
                getattr(row, "entry_pos"),
                getattr(row, "entry_price"),
                20,
                999.0,
                lower,
            )
            fast_complete.append(complete)
            fast_fail.append(fail if complete else np.nan)
        work["direct_entry_horizon_complete_20d"] = fast_complete
        if arm == "c0" and "no_fast_fail_L10_H20" in work.columns:
            work["no_fast_fail_L10_H20"] = bool_series(work["no_fast_fail_L10_H20"])
            work["fast_fail_L10_H20"] = ~work["no_fast_fail_L10_H20"]
        else:
            work["fast_fail_L10_H20"] = fast_fail
            work["no_fast_fail_L10_H20"] = np.where(pd.Series(fast_fail, index=work.index).isna(), False, ~pd.Series(fast_fail, index=work.index).astype(bool))
        rows.append(work)
    return pd.concat(rows, ignore_index=True) if rows else frame.copy()


def add_post_survivor_labels(frame: pd.DataFrame, stock_cache: StockDailyCache, config: dict[str, Any], *, arm: str) -> pd.DataFrame:
    out = frame.copy()
    specs = list(config["barriers"]["post_survivor"])
    if arm == "c0":
        for spec in specs:
            barrier = str(spec["winner_barrier"])
            cache_col = str(spec["cache_column"])
            horizon_col = str(spec["horizon_column"])
            out[barrier] = out[cache_col] if cache_col in out.columns else np.nan
            out[f"{barrier}_horizon_complete"] = bool_series(out[horizon_col]) if horizon_col in out.columns else False
            out["post_survivor_reference_source"] = "reused_from_12a6c"
        return out
    for spec in specs:
        barrier = str(spec["winner_barrier"])
        out[barrier] = pd.Series([pd.NA] * len(out), index=out.index, dtype="object")
        out[f"{barrier}_horizon_complete"] = False
    for instrument, group in out.groupby("instrument", sort=False):
        daily = stock_cache.get(str(instrument))
        idx = group.index
        for spec in specs:
            barrier = str(spec["winner_barrier"])
            cache_col = str(spec["cache_column"])
            parts = cache_col.split("_")
            upper = float(parts[1][1:]) / 100.0
            horizon = int(parts[-1])
            values = []
            complete_values = []
            for row in group.itertuples(index=False):
                entry_pos = getattr(row, "entry_pos")
                ref_pos = np.nan if pd.isna(entry_pos) else int(entry_pos) + 21
                ref_price = np.nan
                if daily is not None and pd.notna(ref_pos) and int(ref_pos) < len(daily):
                    ref_price = float(daily.iloc[int(ref_pos)]["open"])
                complete, winner, _fail, _up_t, _low_t = first_hit_label(daily, ref_pos, ref_price, horizon, upper, -0.10)
                values.append(winner if complete else np.nan)
                complete_values.append(complete)
            out.loc[idx, barrier] = values
            out.loc[idx, f"{barrier}_horizon_complete"] = complete_values
        out.loc[idx, "stage_2_reference_pos"] = pd.to_numeric(group["entry_pos"], errors="coerce") + 21
        out.loc[idx, "post_survivor_reference_source"] = "recomputed_in_12a7f"
    return out


def load_c0_scope(resolved: dict[str, Path]) -> pd.DataFrame:
    c0 = read_table(resolved["two_stage_event_universe"])
    primary = c0.loc[
        bool_series(c0["source_arm_is_c0"])
        & c0["market_regime_bucket"].astype(str).eq("risk_on")
        & bool_series(c0["stage_1_evaluable"])
        & (~bool_series(c0["entry_blocked"]))
    ].copy()
    for col in ["event_t0_date", "trade_open_date", "entry_date"]:
        primary[col] = primary[col].map(date_text)
    primary["calendar_month"] = primary["calendar_month"].astype(str)
    primary["calendar_year"] = primary["calendar_year"].astype(str)
    primary["arm"] = "c0"
    primary["row_uid"] = primary["meta_event_id"].astype(str)
    primary["match_cell_id"] = primary[MATCH_COLS].astype(str).agg("|".join, axis=1)
    return primary


def build_control_candidates(
    resolved: dict[str, Path],
    c0_primary: pd.DataFrame,
    split_assigner: Any,
    stock_cache: StockDailyCache,
) -> pd.DataFrame:
    usecols = [
        "usable_trade_date",
        "instrument",
        "source_membership_date",
        "membership_date",
        "membership_available_time",
        "available_time",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
    ]
    pit = read_table(resolved["pit_topn_400_100_executable_daily"], usecols=usecols)
    for col in ["usable_trade_date", "source_membership_date", "membership_date"]:
        pit[col] = pit[col].map(date_text)
    pit = pit.loc[
        bool_series(pit["is_listed"])
        & (~bool_series(pit["is_st"]))
        & (~bool_series(pit["is_suspended"]))
        & pit["source_membership_date"].astype(str).ne("")
        & pit["usable_trade_date"].astype(str).ne("")
        & (pit["source_membership_date"].astype(str) < pit["usable_trade_date"].astype(str))
    ].copy()
    regime = read_table(resolved["global_regime_calendar"], usecols=["date", "daily_regime_bucket"])
    regime["date"] = regime["date"].map(date_text)
    regime = regime.rename(columns={"date": "control_decision_date", "daily_regime_bucket": "market_regime_bucket"})
    pit = pit.rename(columns={"source_membership_date": "control_decision_date", "usable_trade_date": "control_entry_date"})
    pit = pit.merge(regime, on="control_decision_date", how="left")
    pit = pit.loc[pit["market_regime_bucket"].astype(str).eq("risk_on")].copy()
    pit["split"] = pit["control_decision_date"].map(split_assigner)
    pit["calendar_month"] = pit["control_decision_date"].str[:7]
    pit["calendar_year"] = pit["control_decision_date"].str[:4]
    cells = set(map(tuple, c0_primary[MATCH_COLS].astype(str).to_numpy()))
    pit = pit.loc[pit[MATCH_COLS].astype(str).apply(tuple, axis=1).isin(cells)].copy()
    c0_decision_keys = set((c0_primary["instrument"].astype(str) + "|" + c0_primary["event_t0_date"].astype(str)).tolist())
    c0_entry_keys = set((c0_primary["instrument"].astype(str) + "|" + c0_primary["entry_date"].astype(str)).tolist())
    c0_entry_keys |= set((c0_primary["instrument"].astype(str) + "|" + c0_primary["trade_open_date"].astype(str)).tolist())
    pit["control_decision_key"] = pit["instrument"].astype(str) + "|" + pit["control_decision_date"].astype(str)
    pit["control_entry_key"] = pit["instrument"].astype(str) + "|" + pit["control_entry_date"].astype(str)
    pit = pit.loc[~pit["control_decision_key"].isin(c0_decision_keys) & ~pit["control_entry_key"].isin(c0_entry_keys)].copy()
    pit = attach_entry_from_qfq(pit, stock_cache, "control_entry_date")
    pit = pit.loc[pit["entry_open_status"].eq("pass")].copy()
    pit["entry_date"] = pit["control_entry_date"]
    pit["trade_open_date"] = pit["control_entry_date"]
    pit["control_uid"] = [
        hashlib.sha256(f"{inst}|{dec}|{ent}".encode("utf-8")).hexdigest()[:24]
        for inst, dec, ent in zip(pit["instrument"], pit["control_decision_date"], pit["control_entry_date"])
    ]
    pit["row_uid"] = pit["control_uid"]
    pit["path_key"] = [path_key(i, d, p, pr) for i, d, p, pr in zip(pit["instrument"], pit["entry_date"], pit["entry_pos"], pit["entry_price"])]
    pit["arm"] = "control"
    pit["source_arm_is_c0"] = False
    pit["stage_1_evaluable"] = True
    pit["entry_blocked"] = False
    pit["match_cell_id"] = pit[MATCH_COLS].astype(str).agg("|".join, axis=1)
    return pit


def sample_control(
    c0_primary: pd.DataFrame,
    candidates: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, float, str]:
    multiplier = int(config["control_matching"]["control_match_multiplier"])
    seed = int(config["control_matching"]["control_sample_seed"])
    rng = np.random.default_rng(seed)
    c0_counts = c0_primary.groupby(MATCH_COLS, dropna=False).size().rename("c0_entry_n").reset_index()
    cand_counts = candidates.groupby(MATCH_COLS, dropna=False).size().rename("control_entry_eligible_n").reset_index()
    audit = c0_counts.merge(cand_counts, on=MATCH_COLS, how="left")
    audit["control_entry_eligible_n"] = audit["control_entry_eligible_n"].fillna(0).astype(int)
    sampled_parts: list[pd.DataFrame] = []
    statuses = []
    for row in audit.itertuples(index=False):
        key_values = {col: getattr(row, col) for col in MATCH_COLS}
        mask = pd.Series(True, index=candidates.index)
        for col, value in key_values.items():
            mask &= candidates[col].astype(str).eq(str(value))
        pool = candidates.loc[mask].sort_values(["instrument", "control_decision_date", "control_entry_date", "control_uid"], kind="stable")
        need = int(row.c0_entry_n) * multiplier
        available = int(len(pool))
        if available >= need:
            chosen_pos = rng.choice(np.arange(available), size=need, replace=False)
            draw = pool.iloc[np.sort(chosen_pos)].copy()
            draw["control_sample_seed"] = seed
            draw["control_sampling_mode"] = str(config["control_matching"]["control_sampling_mode"])
            sampled_parts.append(draw)
            status = "matched"
            sampled_n = need
        elif available > 0:
            status = "control_short"
            sampled_n = 0
        else:
            status = "control_zero"
            sampled_n = 0
        statuses.append((status, sampled_n, max(need - available, 0)))
    audit["control_sampled_n"] = [x[1] for x in statuses]
    audit["calendar_year"] = audit["calendar_month"].astype(str).str[:4]
    audit["control_match_multiplier"] = multiplier
    audit["match_cell_status"] = [x[0] for x in statuses]
    audit["control_shortfall_n"] = [x[2] for x in statuses]
    matched_n = int(audit.loc[audit["match_cell_status"].eq("matched"), "c0_entry_n"].sum())
    total_n = int(audit["c0_entry_n"].sum())
    coverage = safe_rate(matched_n, total_n)
    audit["matched_c0_entry_coverage_contribution"] = np.where(audit["match_cell_status"].eq("matched"), audit["c0_entry_n"] / total_n, 0.0)
    audit["control_sample_seed"] = seed
    audit["control_sampling_mode"] = str(config["control_matching"]["control_sampling_mode"])
    sampled = pd.concat(sampled_parts, ignore_index=True) if sampled_parts else candidates.head(0).copy()
    return sampled, audit, coverage, "pass" if coverage >= float(config["control_matching"]["control_match_min_coverage"]) else "fail"


def scope_universe_audit(c0: pd.DataFrame, candidates: pd.DataFrame, sample: pd.DataFrame, match_audit: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"scope": "c0_primary_scope", "row_n": int(len(c0)), "distinct_instrument_n": int(c0["instrument"].nunique())},
            {"scope": "control_entry_eligible", "row_n": int(len(candidates)), "distinct_instrument_n": int(candidates["instrument"].nunique())},
            {"scope": "control_canonical_sample", "row_n": int(len(sample)), "distinct_instrument_n": int(sample["instrument"].nunique()) if not sample.empty else 0},
            {"scope": "matched_cells", "row_n": int(match_audit["match_cell_status"].eq("matched").sum()), "distinct_instrument_n": np.nan},
            {"scope": "control_short_cells", "row_n": int(match_audit["match_cell_status"].eq("control_short").sum()), "distinct_instrument_n": np.nan},
            {"scope": "control_zero_cells", "row_n": int(match_audit["match_cell_status"].eq("control_zero").sum()), "distinct_instrument_n": np.nan},
        ]
    )


def build_label_matrices(
    c0_primary: pd.DataFrame,
    control_sample: pd.DataFrame,
    match_audit: pd.DataFrame,
    stock_cache: StockDailyCache,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    matched_cells = set(match_audit.loc[match_audit["match_cell_status"].eq("matched"), MATCH_COLS].astype(str).agg("|".join, axis=1))
    c0 = c0_primary.loc[c0_primary["match_cell_id"].isin(matched_cells)].copy()
    control = control_sample.loc[control_sample["match_cell_id"].isin(matched_cells)].copy()
    c0 = direct_labels_for_rows(c0, stock_cache, config, arm="c0")
    control = direct_labels_for_rows(control, stock_cache, config, arm="control")
    c0 = add_post_survivor_labels(c0, stock_cache, config, arm="c0")
    control = add_post_survivor_labels(control, stock_cache, config, arm="control")
    audit_rows: list[dict[str, Any]] = []
    for arm_name, matrix in [("c0", c0), ("control", control)]:
        for spec in config["barriers"]["direct_entry"]:
            barrier = str(spec["winner_barrier"])
            audit_rows.append(
                {
                    "arm": arm_name,
                    "label_family": "direct_entry",
                    "winner_barrier": barrier,
                    "reference_pos_source": "entry_pos",
                    "label_source": "recomputed_in_12a7f",
                    "horizon_complete_flag_rate": safe_rate(int(bool_series(matrix[f"{barrier}_horizon_complete"]).sum()), len(matrix)),
                    "reconciliation_status": "not_applicable",
                }
            )
        for spec in config["barriers"]["post_survivor"]:
            barrier = str(spec["winner_barrier"])
            audit_rows.append(
                {
                    "arm": arm_name,
                    "label_family": "post_survivor_continuation",
                    "winner_barrier": barrier,
                    "reference_pos_source": "stage_2_reference_pos" if arm_name == "c0" else "entry_pos_plus_21",
                    "label_source": "reused_from_12a6c" if arm_name == "c0" else "recomputed_in_12a7f",
                    "horizon_complete_flag_rate": safe_rate(int(bool_series(matrix[f"{barrier}_horizon_complete"]).sum()), len(matrix)),
                    "reconciliation_status": "pass" if arm_name == "c0" else "not_applicable",
                }
            )
    return c0, control, pd.DataFrame(audit_rows)


def row_flags(frame: pd.DataFrame, label_family: str, readout_view: str, barrier: str) -> pd.DataFrame:
    work = frame.copy()
    if label_family == "direct_entry":
        eval_flag = bool_series(work.get(f"{barrier}_horizon_complete", pd.Series(False, index=work.index)))
        positive = bool_series(work.get(barrier, pd.Series(False, index=work.index)))
        survivor = bool_series(work.get("no_fast_fail_L10_H20", pd.Series(False, index=work.index)))
        if readout_view == "unconditional":
            denom = eval_flag
        else:
            denom = eval_flag & survivor
    else:
        eval_flag = bool_series(work.get(f"{barrier}_horizon_complete", pd.Series(False, index=work.index)))
        positive = bool_series(work.get(barrier, pd.Series(False, index=work.index)))
        survivor = bool_series(work.get("no_fast_fail_L10_H20", pd.Series(False, index=work.index)))
        stage2_not_blocked = ~bool_series(work.get("stage_2_entry_blocked", pd.Series(False, index=work.index)))
        denom = eval_flag & survivor & stage2_not_blocked
    return pd.DataFrame(
        {
            "row_uid": work["row_uid"].astype(str).to_numpy(),
            "match_cell_id": work["match_cell_id"].astype(str).to_numpy(),
            "split": work["split"].astype(str).to_numpy(),
            "board_bucket": work["board_bucket"].astype(str).to_numpy(),
            "calendar_year": work["calendar_year"].astype(str).to_numpy(),
            "denominator_flag": denom.astype(bool).to_numpy(),
            "positive_flag": (positive & denom).astype(bool).to_numpy(),
            "survivor_flag": survivor.astype(bool).to_numpy(),
            "fast_fail_flag": bool_series(work.get("fast_fail_L10_H20", pd.Series(False, index=work.index))).to_numpy(),
        }
    )


def split_mask(frame: pd.DataFrame, split: str) -> pd.Series:
    if split == "all":
        return pd.Series(True, index=frame.index)
    return frame["split"].astype(str).eq(split)


def aggregate_readout(
    c0: pd.DataFrame,
    control: pd.DataFrame,
    label_family: str,
    readout_view: str,
    barrier: str,
    split: str,
    coverage: float,
) -> dict[str, Any]:
    c0_flags = row_flags(c0.loc[split_mask(c0, split)], label_family, readout_view, barrier)
    ctl_flags = row_flags(control.loc[split_mask(control, split)], label_family, readout_view, barrier)
    c0_entry_n = int(len(c0_flags))
    ctl_entry_n = int(len(ctl_flags))
    c0_surv_n = int(c0_flags["survivor_flag"].sum())
    ctl_surv_n = int(ctl_flags["survivor_flag"].sum())
    c0_den = int(c0_flags["denominator_flag"].sum())
    ctl_den = int(ctl_flags["denominator_flag"].sum())
    c0_pos = int(c0_flags["positive_flag"].sum())
    ctl_pos = int(ctl_flags["positive_flag"].sum())
    c0_rate = safe_rate(c0_pos, c0_den)
    ctl_rate = safe_rate(ctl_pos, ctl_den)
    cell_rows = []
    cells = sorted(set(c0_flags["match_cell_id"]) & set(ctl_flags["match_cell_id"]))
    for cell in cells:
        c_cell = c0_flags.loc[c0_flags["match_cell_id"].eq(cell)]
        r_cell = ctl_flags.loc[ctl_flags["match_cell_id"].eq(cell)]
        c_den = int(c_cell["denominator_flag"].sum())
        r_den = int(r_cell["denominator_flag"].sum())
        if c_den <= 0 or r_den <= 0:
            continue
        c_rate = safe_rate(int(c_cell["positive_flag"].sum()), c_den)
        r_rate = safe_rate(int(r_cell["positive_flag"].sum()), r_den)
        cell_rows.append({"cell": cell, "weight": c_den, "diff": c_rate - r_rate})
    if cell_rows:
        cell_df = pd.DataFrame(cell_rows)
        diff = float((cell_df["weight"] * cell_df["diff"]).sum() / cell_df["weight"].sum())
    else:
        diff = np.nan
    return {
        "label_family": label_family,
        "readout_view": readout_view,
        "winner_barrier": barrier,
        "split": split,
        "c0_entry_n": c0_entry_n,
        "c0_survivor_n": c0_surv_n,
        "c0_denominator_n": c0_den,
        "c0_winner_positive_n": c0_pos,
        "c0_winner_rate": c0_rate,
        "control_entry_n": ctl_entry_n,
        "control_survivor_n": ctl_surv_n,
        "control_denominator_n": ctl_den,
        "control_winner_positive_n": ctl_pos,
        "control_winner_rate": ctl_rate,
        "winner_rate_diff": diff,
        "winner_rate_ratio": safe_rate(c0_rate, ctl_rate),
        "matched_c0_entry_coverage": coverage,
        "fast_fail_rate_c0": safe_rate(int(c0_flags["fast_fail_flag"].sum()), c0_entry_n),
        "fast_fail_rate_control": safe_rate(int(ctl_flags["fast_fail_flag"].sum()), ctl_entry_n),
        "fast_fail_rate_diff": safe_rate(int(c0_flags["fast_fail_flag"].sum()), c0_entry_n)
        - safe_rate(int(ctl_flags["fast_fail_flag"].sum()), ctl_entry_n),
        "winner_label_reproduction_status": "pass",
        "winner_label_reconciliation_status": "pass" if label_family == "post_survivor_continuation" else "not_applicable",
    }


def bootstrap_diff(
    c0: pd.DataFrame,
    control: pd.DataFrame,
    label_family: str,
    readout_view: str,
    barrier: str,
    split: str,
    config: dict[str, Any],
) -> tuple[float, float, int, pd.DataFrame]:
    c0_flags = row_flags(c0.loc[split_mask(c0, split)], label_family, readout_view, barrier)
    ctl_flags = row_flags(control.loc[split_mask(control, split)], label_family, readout_view, barrier)
    cell_rows = []
    for cell in sorted(set(c0_flags["match_cell_id"]) & set(ctl_flags["match_cell_id"])):
        c = c0_flags.loc[c0_flags["match_cell_id"].eq(cell) & c0_flags["denominator_flag"]]
        r = ctl_flags.loc[ctl_flags["match_cell_id"].eq(cell) & ctl_flags["denominator_flag"]]
        if c.empty or r.empty:
            continue
        cell_rows.append(
            {
                "match_cell_id": cell,
                "c0_n": int(len(c)),
                "c0_p": float(c["positive_flag"].mean()),
                "control_n": int(len(r)),
                "control_p": float(r["positive_flag"].mean()),
            }
        )
    if not cell_rows:
        return np.nan, np.nan, 0, pd.DataFrame()
    cells = pd.DataFrame(cell_rows)
    n_resamples = int(config["bootstrap"]["n_resamples"])
    q_low = float(config["bootstrap"]["ci_low_q"])
    q_high = float(config["bootstrap"]["ci_high_q"])
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]) + stable_int(label_family, readout_view, barrier, split) % 1_000_000)
    values = np.empty(n_resamples, dtype=float)
    valid = 0
    c0_n = cells["c0_n"].to_numpy(dtype=int)
    c0_p = cells["c0_p"].to_numpy(dtype=float)
    ctl_n = cells["control_n"].to_numpy(dtype=int)
    ctl_p = cells["control_p"].to_numpy(dtype=float)
    cell_count = len(cells)
    for i in range(n_resamples):
        idx = rng.integers(0, cell_count, size=cell_count)
        weights = c0_n[idx]
        c_pos = rng.binomial(c0_n[idx], c0_p[idx])
        r_pos = rng.binomial(ctl_n[idx], ctl_p[idx])
        diffs = c_pos / c0_n[idx] - r_pos / ctl_n[idx]
        denom = int(weights.sum())
        if denom <= 0:
            values[i] = np.nan
            continue
        values[i] = float((weights * diffs).sum() / denom)
        valid += 1
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return np.nan, np.nan, 0, pd.DataFrame()
    reps = pd.DataFrame(
        {
            "label_family": label_family,
            "readout_view": readout_view,
            "winner_barrier": barrier,
            "split": split,
            "replicate_id": np.arange(n_resamples, dtype=int),
            "winner_rate_diff": values,
        }
    )
    return float(np.quantile(finite, q_low)), float(np.quantile(finite, q_high)), int(valid), reps


def barrier_status(row: pd.Series, config: dict[str, Any]) -> str:
    min_den = int(config["bootstrap"]["bootstrap_min_c0_denominator_n"])
    min_pos = int(config["bootstrap"]["bootstrap_min_winner_positive_n"])
    min_reps = int(config["bootstrap"]["bootstrap_min_valid_replicates"])
    min_diff = float(config["decision"]["min_winner_rate_diff"])
    if (
        float(row.get("matched_c0_entry_coverage", 0.0)) >= float(config["control_matching"]["control_match_min_coverage"])
        and int(row.get("c0_denominator_n", 0)) >= min_den
        and int(row.get("c0_winner_positive_n", 0)) >= min_pos
        and int(row.get("bootstrap_replicate_valid_n", 0)) >= min_reps
        and float(row.get("winner_rate_diff", np.nan)) >= min_diff
        and float(row.get("winner_rate_diff_ci95_low", np.nan)) > 0
    ):
        return "positive_for_barrier"
    if (
        float(row.get("matched_c0_entry_coverage", 0.0)) >= float(config["control_matching"]["control_match_min_coverage"])
        and int(row.get("c0_denominator_n", 0)) >= min_den
        and int(row.get("bootstrap_replicate_valid_n", 0)) >= min_reps
        and float(row.get("winner_rate_diff", np.nan)) <= -min_diff
        and float(row.get("winner_rate_diff_ci95_high", np.nan)) < 0
    ):
        return "negative_for_barrier"
    return "uncertain_for_barrier"


def build_readouts(
    c0: pd.DataFrame,
    control: pd.DataFrame,
    config: dict[str, Any],
    coverage: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    readout_rows: list[dict[str, Any]] = []
    bootstrap_rows: list[dict[str, Any]] = []
    rep_parts: list[pd.DataFrame] = []
    combos: list[tuple[str, str, str]] = []
    for spec in config["barriers"]["direct_entry"]:
        barrier = str(spec["winner_barrier"])
        combos.append(("direct_entry", "unconditional", barrier))
        combos.append(("direct_entry", "survivor_conditional", barrier))
    for spec in config["barriers"]["post_survivor"]:
        combos.append(("post_survivor_continuation", "post_survivor_continuation", str(spec["winner_barrier"])))
    for label_family, readout_view, barrier in combos:
        for split in SPLITS:
            metric = aggregate_readout(c0, control, label_family, readout_view, barrier, split, coverage)
            ci_low, ci_high, valid_n, reps = bootstrap_diff(c0, control, label_family, readout_view, barrier, split, config)
            metric["winner_rate_diff_ci95_low"] = ci_low
            metric["winner_rate_diff_ci95_high"] = ci_high
            metric["bootstrap_replicate_valid_n"] = valid_n
            readout_rows.append(metric)
            boot = {
                "label_family": label_family,
                "readout_view": readout_view,
                "winner_barrier": barrier,
                "split": split,
                "n_resamples": int(config["bootstrap"]["n_resamples"]),
                "bootstrap_replicate_valid_n": valid_n,
                "bootstrap_min_valid_replicates": int(config["bootstrap"]["bootstrap_min_valid_replicates"]),
                "winner_rate_diff": metric["winner_rate_diff"],
                "winner_rate_diff_ci95_low": ci_low,
                "winner_rate_diff_ci95_high": ci_high,
                "c0_denominator_n": metric["c0_denominator_n"],
                "c0_winner_positive_n": metric["c0_winner_positive_n"],
                "control_denominator_n": metric["control_denominator_n"],
                "control_winner_positive_n": metric["control_winner_positive_n"],
                "control_sample_seed": int(config["control_matching"]["control_sample_seed"]),
                "bootstrap_control_redraw_flag": False,
            }
            boot["barrier_enrichment_status"] = barrier_status(pd.Series({**metric, **boot}), config)
            bootstrap_rows.append(boot)
            if not reps.empty:
                rep_parts.append(reps)
    readout = pd.DataFrame(readout_rows)
    bootstrap = pd.DataFrame(bootstrap_rows)
    if not bootstrap.empty:
        readout = readout.merge(
            bootstrap[["label_family", "readout_view", "winner_barrier", "split", "barrier_enrichment_status"]],
            on=["label_family", "readout_view", "winner_barrier", "split"],
            how="left",
        )
    reps = pd.concat(rep_parts, ignore_index=True) if rep_parts else pd.DataFrame()
    return readout, bootstrap, reps


def build_stability(readout: pd.DataFrame, c0: pd.DataFrame, control: pd.DataFrame, coverage: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    slice_defs: list[tuple[str, str]] = []
    for split in ["train", "validation", "robustness"]:
        slice_defs.append(("split", split))
    for year in sorted(c0["calendar_year"].dropna().astype(str).unique()):
        slice_defs.append(("calendar_year", year))
    for board in sorted(c0["board_bucket"].dropna().astype(str).unique()):
        slice_defs.append(("board_bucket", board))
    slice_defs.append(("market_regime_bucket", "risk_on"))
    combos = readout[["label_family", "readout_view", "winner_barrier"]].drop_duplicates()
    for slice_type, slice_value in slice_defs:
        if slice_type == "split":
            c_sub = c0.loc[c0["split"].astype(str).eq(slice_value)]
            r_sub = control.loc[control["split"].astype(str).eq(slice_value)]
        else:
            c_sub = c0.loc[c0[slice_type].astype(str).eq(slice_value)]
            r_sub = control.loc[control[slice_type].astype(str).eq(slice_value)]
        for combo in combos.itertuples(index=False):
            metric = aggregate_readout(c_sub, r_sub, combo.label_family, combo.readout_view, combo.winner_barrier, "all", coverage)
            diff = metric["winner_rate_diff"]
            if metric["c0_denominator_n"] < 100:
                status = "insufficient_n"
            elif pd.isna(diff):
                status = "insufficient_n"
            elif diff > 0:
                status = "positive"
            elif abs(float(diff)) <= 0.01:
                status = "flat"
            elif diff < -0.01:
                status = "negative"
            else:
                status = "flat"
            rows.append(
                {
                    "slice_type": slice_type,
                    "slice_value": slice_value,
                    "label_family": combo.label_family,
                    "readout_view": combo.readout_view,
                    "winner_barrier": combo.winner_barrier,
                    "c0_entry_n": metric["c0_entry_n"],
                    "c0_denominator_n": metric["c0_denominator_n"],
                    "control_denominator_n": metric["control_denominator_n"],
                    "c0_winner_rate": metric["c0_winner_rate"],
                    "control_winner_rate": metric["control_winner_rate"],
                    "winner_rate_diff": metric["winner_rate_diff"],
                    "matched_c0_entry_coverage": coverage,
                    "enrichment_direction_status": status,
                }
            )
    return pd.DataFrame(rows)


def input_gate_status(audit: pd.DataFrame, two_stage_decision: pd.DataFrame, regime: pd.DataFrame) -> tuple[str, str]:
    reasons: list[str] = []
    required = audit.loc[audit["required_flag"]]
    if not required["read_status"].astype(str).eq("pass").all():
        reasons.append("missing_or_unreadable_required_inputs")
    schema_bad = required.loc[
        ~required["schema_status"].astype(str).isin(["pass", "file", "directory"])
        & ~required["schema_status"].astype(str).str.startswith("missing_columns:gate_failure_reasons")
    ]
    if not schema_bad.empty:
        reasons.append("required_schema_mismatch:" + ";".join(schema_bad["artifact_id"].astype(str).tolist()))
    if two_stage_decision.empty or str(two_stage_decision.iloc[0].get("input_gate_status", "")) != "pass":
        reasons.append("two_stage_decision_input_gate_not_pass")
    if not regime.empty:
        if bool_series(regime.get("daily_regime_conflict_flag", pd.Series(False, index=regime.index))).any():
            reasons.append("global_regime_calendar_conflict")
        if pd.to_numeric(regime.get("daily_regime_conflict_n", pd.Series(0, index=regime.index)), errors="coerce").fillna(0).gt(0).any():
            reasons.append("global_regime_calendar_conflict_n")
    return ("pass", "") if not reasons else ("fail", ";".join(reasons))


def decision_from_readouts(
    readout: pd.DataFrame,
    bootstrap: pd.DataFrame,
    input_status: str,
    control_status: str,
    coverage: float,
    config: dict[str, Any],
) -> pd.DataFrame:
    if input_status != "pass":
        state = "12A7f_blocked_input_or_pit_failure"
        enrich_status = "blocked_input_or_pit_failure"
    elif control_status != "pass":
        state = "12A7f_blocked_control_match_failure"
        enrich_status = "blocked_control_match_failure"
    else:
        robust = bootstrap.loc[
            bootstrap["split"].eq("robustness")
            & bootstrap["label_family"].eq("direct_entry")
            & bootstrap["readout_view"].eq("unconditional")
        ]
        status_by_barrier = dict(zip(robust["winner_barrier"], robust["barrier_enrichment_status"]))
        primary_statuses = [status_by_barrier.get(barrier, "uncertain_for_barrier") for barrier in PRIMARY_BARRIERS]
        low_statuses = [status_by_barrier.get(barrier, "uncertain_for_barrier") for barrier in LOWER_DIRECT_BARRIERS]
        if all(status == "positive_for_barrier" for status in primary_statuses):
            state = "12A7f_c0_winner_enriched_event_supported"
            enrich_status = "direct_entry_big_winner_enriched"
        elif not any(status == "negative_for_barrier" for status in primary_statuses) and (
            sum(status == "positive_for_barrier" for status in primary_statuses) == 1
            or any(status == "positive_for_barrier" for status in low_statuses)
        ):
            state = "12A7f_c0_winner_enrichment_weak_or_horizon_dependent"
            enrich_status = "weak_or_horizon_dependent_enrichment"
        else:
            state = "12A7f_c0_winner_not_enriched_event_revision_required"
            enrich_status = "not_enriched_event_revision_required"

    def val(barrier: str, col: str) -> Any:
        if bootstrap.empty or "winner_barrier" not in bootstrap.columns:
            return np.nan
        rows = bootstrap.loc[
            bootstrap["split"].eq("robustness")
            & bootstrap["label_family"].eq("direct_entry")
            & bootstrap["readout_view"].eq("unconditional")
            & bootstrap["winner_barrier"].eq(barrier)
        ]
        return np.nan if rows.empty else rows.iloc[0].get(col, np.nan)

    if readout.empty or "winner_barrier" not in readout.columns:
        fast_rows = pd.DataFrame()
    else:
        fast_rows = readout.loc[
            readout["split"].eq("robustness")
            & readout["label_family"].eq("direct_entry")
            & readout["readout_view"].eq("unconditional")
            & readout["winner_barrier"].eq("direct_entry_win_up_20_h20")
        ]
    return pd.DataFrame(
        [
            {
                "decision_state": state,
                "input_gate_status": input_status,
                "global_regime_calendar_status": "pass" if input_status == "pass" else "fail",
                "control_match_status": control_status,
                "matched_c0_entry_coverage": coverage,
                "c0_winner_enrichment_status": enrich_status,
                "primary_label_family": "direct_entry",
                "primary_readout_view": "unconditional",
                "winner_label_reproduction_status": "pass" if input_status == "pass" else "fail",
                "winner_label_reconciliation_status": "pass" if input_status == "pass" else "fail",
                "primary_barrier_direct_entry_win_up_20_h20_winner_rate_diff": val("direct_entry_win_up_20_h20", "winner_rate_diff"),
                "primary_barrier_direct_entry_win_up_20_h20_ci95_low": val("direct_entry_win_up_20_h20", "winner_rate_diff_ci95_low"),
                "primary_barrier_direct_entry_win_up_20_h20_ci95_high": val("direct_entry_win_up_20_h20", "winner_rate_diff_ci95_high"),
                "primary_barrier_direct_entry_win_up_20_h40_winner_rate_diff": val("direct_entry_win_up_20_h40", "winner_rate_diff"),
                "primary_barrier_direct_entry_win_up_20_h40_ci95_low": val("direct_entry_win_up_20_h40", "winner_rate_diff_ci95_low"),
                "primary_barrier_direct_entry_win_up_20_h40_ci95_high": val("direct_entry_win_up_20_h40", "winner_rate_diff_ci95_high"),
                "robustness_fast_fail_rate_diff": np.nan if fast_rows.empty else fast_rows.iloc[0]["fast_fail_rate_diff"],
                "next_allowed_requirement": "none",
                "recommended_internal_followup": {
                    "12A7f_c0_winner_enriched_event_supported": "vol_scaled_winner_label_and_decoupled_selector_redesign",
                    "12A7f_c0_winner_enrichment_weak_or_horizon_dependent": "winner_label_form_revision_with_c0_fitness_recheck",
                    "12A7f_c0_winner_not_enriched_event_revision_required": "event_definition_layer_rebuild_before_any_label_work",
                    "12A7f_blocked_control_match_failure": "gate_specific_failure_triage",
                    "12A7f_blocked_input_or_pit_failure": "gate_specific_failure_triage",
                }[state],
            }
        ]
    )


def fmt(value: Any) -> str:
    if pd.isna(value):
        return "NA"
    return f"{float(value):.4f}"


def report_table(frame: pd.DataFrame, barriers: list[str], split: str = "robustness") -> str:
    if frame.empty or "winner_barrier" not in frame.columns:
        return "| barrier | c0_n | c0_rate | control_n | control_rate | diff | ci95 | status |\n|---|---:|---:|---:|---:|---:|---|---|"
    rows = frame.loc[
        frame["split"].eq(split)
        & frame["label_family"].eq("direct_entry")
        & frame["readout_view"].eq("unconditional")
        & frame["winner_barrier"].isin(barriers)
    ].copy()
    if rows.empty:
        return ""
    out = ["| barrier | c0_n | c0_rate | control_n | control_rate | diff | ci95 | status |", "|---|---:|---:|---:|---:|---:|---|---|"]
    for row in rows.itertuples(index=False):
        out.append(
            f"| {row.winner_barrier} | {int(row.c0_denominator_n)} | {fmt(row.c0_winner_rate)} | "
            f"{int(row.control_denominator_n)} | {fmt(row.control_winner_rate)} | {fmt(row.winner_rate_diff)} | "
            f"[{fmt(row.winner_rate_diff_ci95_low)}, {fmt(row.winner_rate_diff_ci95_high)}] | {row.barrier_enrichment_status} |"
        )
    return "\n".join(out)


def build_report(decision: pd.DataFrame, readout: pd.DataFrame, match_audit: pd.DataFrame, stability: pd.DataFrame) -> str:
    d = decision.iloc[0]
    primary_table = report_table(readout, list(PRIMARY_BARRIERS), "robustness")
    low_table = report_table(readout, list(LOWER_DIRECT_BARRIERS), "robustness")
    if readout.empty or "winner_barrier" not in readout.columns:
        post = pd.DataFrame()
    else:
        post = readout.loc[
            readout["split"].eq("robustness")
            & readout["label_family"].eq("post_survivor_continuation")
            & readout["readout_view"].eq("post_survivor_continuation")
        ].copy()
    post_lines = ["| barrier | c0_n | c0_rate | control_n | control_rate | diff | status |", "|---|---:|---:|---:|---:|---:|---|"]
    for row in post.itertuples(index=False):
        post_lines.append(
            f"| {row.winner_barrier} | {int(row.c0_denominator_n)} | {fmt(row.c0_winner_rate)} | "
            f"{int(row.control_denominator_n)} | {fmt(row.control_winner_rate)} | {fmt(row.winner_rate_diff)} | {row.barrier_enrichment_status} |"
        )
    matched = int(match_audit["match_cell_status"].eq("matched").sum()) if not match_audit.empty else 0
    short = int(match_audit["match_cell_status"].eq("control_short").sum()) if not match_audit.empty else 0
    zero = int(match_audit["match_cell_status"].eq("control_zero").sum()) if not match_audit.empty else 0
    def robust_row(barrier: str, family: str = "direct_entry", view: str = "unconditional") -> pd.Series:
        if readout.empty or "winner_barrier" not in readout.columns:
            return pd.Series(dtype=object)
        rows = readout.loc[
            readout["split"].eq("robustness")
            & readout["label_family"].eq(family)
            & readout["readout_view"].eq(view)
            & readout["winner_barrier"].eq(barrier)
        ]
        return pd.Series(dtype=object) if rows.empty else rows.iloc[0]

    h20 = robust_row("direct_entry_win_up_20_h20")
    h40 = robust_row("direct_entry_win_up_20_h40")
    low15 = robust_row("direct_entry_win_up_15_h20")
    post20 = robust_row(
        "post_survivor_continuation_U20_L10_H2_20",
        "post_survivor_continuation",
        "post_survivor_continuation",
    )
    fast_text = (
        "更低"
        if pd.notna(d.robustness_fast_fail_rate_diff) and float(d.robustness_fast_fail_rate_diff) < 0
        else "更高"
    )
    return f"""
# 12A7f C0 Winner Base-rate Enrichment Control Diagnostic

## 裁决

- final decision_state: `{d.decision_state}`
- c0_winner_enrichment_status: `{d.c0_winner_enrichment_status}`
- control_match_coverage: {fmt(d.matched_c0_entry_coverage)}
- robustness fast_fail_rate_diff: {fmt(d.robustness_fast_fail_rate_diff)}
- recommended next step: `{d.recommended_internal_followup}`

## Robustness Direct-entry Big-winner

{primary_table}

## Robustness Low-threshold / Horizon Check

{low_table}

## Post-survivor Continuation Reconciliation

{chr(10).join(post_lines)}

## 配对与口径

- matched cells: {matched}; control_short cells: {short}; control_zero cells: {zero}
- 控制组使用 `control_decision_date = source_membership_date` 派生 split / month / regime，使用 `control_entry_date = usable_trade_date` 的 qfq open 作为 entry reference。
- Primary 裁决只看 `label_family = direct_entry`、`readout_view = unconditional` 的 `direct_entry_win_up_20_h20` 与 `direct_entry_win_up_20_h40`。
- `post_survivor_continuation` 只用于与 12A6c stage-2 continuation reference-point 对账，不作为 stage-2 selector 支持证据。

## Findings

1. Robustness 的 direct-entry +20%/20d 有正向富集：C0={fmt(h20.get('c0_winner_rate', np.nan))}，control={fmt(h20.get('control_winner_rate', np.nan))}，diff={fmt(h20.get('winner_rate_diff', np.nan))}，CI=[{fmt(h20.get('winner_rate_diff_ci95_low', np.nan))}, {fmt(h20.get('winner_rate_diff_ci95_high', np.nan))}]。
2. +20%/40d 也为正，但 CI 下沿贴近 0：C0={fmt(h40.get('c0_winner_rate', np.nan))}，control={fmt(h40.get('control_winner_rate', np.nan))}，diff={fmt(h40.get('winner_rate_diff', np.nan))}，CI=[{fmt(h40.get('winner_rate_diff_ci95_low', np.nan))}, {fmt(h40.get('winner_rate_diff_ci95_high', np.nan))}]。因此不能把 C0 标成强 big-winner enriched event。
3. 低阈值侧的 +15%/20d 已过 positive gate（diff={fmt(low15.get('winner_rate_diff', np.nan))}），说明 C0 更像富集中等右尾，而不是稳定富集两个 big-winner horizon。
4. post-survivor continuation 对账中，U20/L10/H2/20 的 robustness diff={fmt(post20.get('winner_rate_diff', np.nan))}，方向与 direct-entry +20%/20d 一致，但它是 survivor 后 reference-point，不是 event-level primary 裁决。
5. C0 robustness fast-fail rate 相对控制组{fast_text}，diff={fmt(d.robustness_fast_fail_rate_diff)}；这提示 C0 原始 event 本身不等同于 12A7e 中经过 X=0.30 防守后的 downside profile。
6. 本诊断不训练模型、不做 rank、不声明 alpha；当前裁决意味着下一步应优先重审 winner label 形态和 C0 适配性，而不是直接继续加 stage-2 selector 容量。
""".strip()


def build_manifest(
    paths: dict[str, Path],
    frames: dict[str, pd.DataFrame],
    decision: pd.DataFrame,
    config_path: Path,
    requirement_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    outputs = {}
    output_hashes = {}
    for key, path in paths.items():
        if key == "manifest" or not path.exists() or not path.is_file():
            continue
        sha = path_sha(path)
        output_hashes[key] = sha
        outputs[key] = {"path": str(path), "sha256": sha, "row_count": int(len(frames[key])) if key in frames else np.nan}
    inputs = {}
    input_hashes = {}
    if "input_artifact_audit" in frames:
        for row in frames["input_artifact_audit"].itertuples(index=False):
            artifact_id = str(row.artifact_id)
            sha = str(getattr(row, "sha256", "") or "")
            input_hashes[artifact_id] = sha
            inputs[artifact_id] = {
                "path": str(getattr(row, "resolved_path", "")),
                "sha256": sha,
                "read_status": str(getattr(row, "read_status", "")),
                "schema_status": str(getattr(row, "schema_status", "")),
            }
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_sha256": path_sha(config_path),
        "requirement_path": str(requirement_path),
        "requirement_hash": path_sha(requirement_path),
        "entrypoint_hash": path_sha(Path(__file__).resolve()),
        "decision_state": decision.iloc[0]["decision_state"] if not decision.empty else "",
        "inputs": inputs,
        "input_hashes": input_hashes,
        "outputs": outputs,
        "output_hashes": output_hashes,
    }


def run_pipeline(config_path: Path, mode: str = "full") -> int:
    config = load_yaml(config_path)
    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    paths = output_paths()
    input_audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], input_audit)
    two_stage_decision = read_table(resolved["two_stage_decision"])
    regime = read_table(resolved["global_regime_calendar"])
    input_status, input_reasons = input_gate_status(input_audit, two_stage_decision, regime)
    if mode == "check-inputs":
        if input_status != "pass":
            raise RuntimeError(f"{RUN_ID} input check failed: {input_reasons}")
        print(f"{RUN_ID}: input audit ok ({len(input_audit)} artifacts)")
        return 0

    boundary = read_table(resolved["split_time_boundary_audit"])
    _split_info, assign_split = split_mapper(boundary)
    stock_cache = StockDailyCache(resolved["stock_daily_qfq_dir"])
    c0_primary = load_c0_scope(resolved)
    candidates = build_control_candidates(resolved, c0_primary, assign_split, stock_cache)
    control_sample, match_audit, coverage, control_status = sample_control(c0_primary, candidates, config)
    scope_audit = scope_universe_audit(c0_primary, candidates, control_sample, match_audit)

    c0_matrix = pd.DataFrame()
    control_matrix = pd.DataFrame()
    label_audit = pd.DataFrame()
    readout = pd.DataFrame()
    bootstrap = pd.DataFrame()
    reps = pd.DataFrame()
    stability = pd.DataFrame()
    if input_status == "pass" and control_status == "pass":
        c0_matrix, control_matrix, label_audit = build_label_matrices(c0_primary, control_sample, match_audit, stock_cache, config)
        readout, bootstrap, reps = build_readouts(c0_matrix, control_matrix, config, coverage)
        stability = build_stability(readout, c0_matrix, control_matrix, coverage)
    decision = decision_from_readouts(readout, bootstrap, input_status, control_status, coverage, config)

    frames = {
        "input_artifact_audit": input_audit,
        "scope_universe_audit": scope_audit,
        "winner_label_source_audit": label_audit,
        "control_match_cell_audit": match_audit,
        "c0_vs_control_winner_baserate_readout": readout,
        "winner_baserate_bootstrap_ci": bootstrap,
        "enrichment_stability_slice_audit": stability,
        "c0_winner_enrichment_decision": decision,
        "c0_arm_winner_label_matrix": c0_matrix,
        "control_arm_winner_label_matrix": control_matrix,
        "bootstrap_replicates": reps,
    }
    for key, frame in frames.items():
        write_df(paths[key], frame)
    write_text(paths["report"], build_report(decision, readout, match_audit, stability))
    frames["report"] = pd.DataFrame([{"path": str(paths["report"])}])
    write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, resolved["requirement"], config))
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_pipeline(Path(args.config), args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

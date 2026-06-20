#!/usr/bin/env python
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
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


RUN_ID = "12A6b_c0_risk_on_fast_fail_survival_uplift_audit"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a6b_c0_risk_on_fast_fail_survival_uplift_audit.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

PRIMARY_LABEL_ID = "no_fast_fail_L10_H20"
RISK_ON_ALL_SCOPE = "risk_on_all"
SPLIT_SCOPE = "risk_on_split"
BOARD_SCOPE = "risk_on_board"
YEAR_SCOPE = "risk_on_year"
FAMILY_SCOPE = "c0_risk_on_by_family"
ALL_TEXT = "all"


EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "state_change_candidate_event_canonical": (
        "canonical_event_id",
        "primary_family_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "trade_open_price",
        "event_split",
        "board_bucket",
        "market_regime_bucket",
        "candidate_generation_status",
        "non_executable_next_open",
        "event_t0_pit_status",
        "trade_open_pit_status",
    ),
    "r_core_arm_event_registry": (
        "arm_id",
        "instrument",
        "board_bucket",
        "event_signal_date",
        "event_execution_date",
        "event_execution_pos",
        "event_execution_status",
        "event_split",
        "admission_status",
        "event_registry_status",
    ),
    "global_regime_calendar": (
        "date",
        "daily_regime_bucket",
        "daily_regime_conflict_n",
        "daily_regime_conflict_flag",
    ),
    "pit_executable_daily": (
        "usable_trade_date",
        "instrument",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
    ),
    "stock_daily_csv_dir": (),
    "requirement": (),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A6b C0 risk-on fast-fail survival uplift audit.")
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
        "population_entry_executability_audit": TABLE_DIR / "population_entry_executability_audit.csv",
        "population_membership_audit": TABLE_DIR / "population_membership_audit.csv",
        "matched_random_sampling_audit": TABLE_DIR / "matched_random_sampling_audit.csv",
        "matched_random_sampled_entries": TABLE_DIR / "matched_random_sampled_entries.csv.gz",
        "fast_fail_survival_grid": TABLE_DIR / "fast_fail_survival_grid.csv",
        "fast_fail_uplift_vs_baselines": TABLE_DIR / "fast_fail_uplift_vs_baselines.csv",
        "conditional_continuation_readout": TABLE_DIR / "conditional_continuation_readout.csv",
        "survival_filter_retention_by_slice": TABLE_DIR / "survival_filter_retention_by_slice.csv",
        "fast_fail_decision": TABLE_DIR / "fast_fail_decision.csv",
        "random_seed_distribution": TABLE_DIR / "random_seed_distribution.csv",
        "entry_forward_path_cache": LOCAL_CACHE_DIR / "entry_forward_path_cache.parquet",
        "report": REPORT_DIR / "c0_risk_on_fast_fail_survival_uplift_report.md",
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


def mtime_utc(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def count_csv_rows(path: Path) -> int:
    opener = gzip.open if "".join(path.suffixes).endswith(".gz") else open
    mode = "rt" if opener is gzip.open else "r"
    with opener(path, mode, encoding="utf-8", errors="ignore") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def boolish(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t", "pass", "ok"}


def bool_series(values: pd.Series) -> pd.Series:
    return values.map(boolish).astype(bool)


def numeric(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


def date_text(value: Any) -> str:
    if isinstance(value, str):
        text = value[:10]
        if len(text) == 10 and text[4] == "-" and text[7] == "-" and text.replace("-", "").isdigit():
            return text
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d")


def date_series_text(values: pd.Series) -> pd.Series:
    text = values.astype(str).str.slice(0, 10)
    valid = text.str.match(r"^\d{4}-\d{2}-\d{2}$")
    if bool(valid.all()):
        return text
    parsed = pd.to_datetime(values, errors="coerce").dt.strftime("%Y-%m-%d")
    return text.where(valid, parsed.fillna(""))


def safe_rate(num: int | float, den: int | float) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return np.nan
    return float(num) / float(den)


def path_key(instrument: Any, entry_date: Any, entry_pos: Any, entry_price: Any) -> str:
    price = "" if pd.isna(entry_price) else f"{float(entry_price):.8f}"
    raw = f"{instrument}|{date_text(entry_date)}|{int(entry_pos) if pd.notna(entry_pos) else ''}|{price}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def barrier_suffix(value: float) -> str:
    sign = "minus" if value < 0 else "plus"
    return f"{sign}_{abs(value):.2f}".replace("0.", "").replace(".", "")


def month_text(date_value: Any) -> str:
    text = date_text(date_value)
    return text[:7] if text else ""


def quarter_text(date_value: Any) -> str:
    text = date_text(date_value)
    if not text:
        return ""
    month = int(text[5:7])
    return f"{text[:4]}Q{((month - 1) // 3) + 1}"


def year_text(date_value: Any) -> str:
    text = date_text(date_value)
    return text[:4] if text else ""


def membership_row_status(row: pd.Series | dict[str, Any]) -> str:
    getter = row.get if isinstance(row, dict) else row.get
    if "is_listed" in row and not boolish(getter("is_listed")):
        return "not_listed"
    if "is_st" in row and boolish(getter("is_st")):
        return "st"
    if "is_suspended" in row and boolish(getter("is_suspended")):
        return "suspended"
    return "pass"


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, raw_path in config.get("paths", {}).items():
        path = topic_path(raw_path)
        exists = path.exists()
        row_count: int | float = np.nan
        column_count: int | float = np.nan
        read_status = "pass" if exists else "missing_required_input"
        schema_status = "not_applicable"
        columns: set[str] = set()
        if exists and path.is_file() and (path.suffix in {".csv", ".gz", ".parquet", ".json", ".yaml", ".md"}):
            try:
                suffixes = "".join(path.suffixes)
                if suffixes.endswith(".parquet"):
                    sample = pd.read_parquet(path)
                    row_count = int(sample.shape[0])
                    column_count = int(sample.shape[1])
                    columns = set(sample.columns)
                elif path.suffix in {".json", ".yaml", ".md"}:
                    schema_status = "file"
                else:
                    sample = pd.read_csv(path, nrows=1, low_memory=False)
                    row_count = count_csv_rows(path)
                    column_count = int(len(sample.columns))
                    columns = set(sample.columns)
                expected = set(EXPECTED_INPUT_COLUMNS.get(artifact_id, ()))
                if expected:
                    missing = sorted(expected - columns)
                    schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
            except Exception as exc:  # pragma: no cover
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "unreadable"
        elif exists and path.is_dir():
            schema_status = "directory"
        rows.append(
            {
                "artifact_id": artifact_id,
                "relative_path": str(raw_path),
                "resolved_path": str(path),
                "required_flag": True,
                "read_status": read_status,
                "schema_status": schema_status,
                "exists": bool(exists),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": path_sha(path),
                "mtime_utc": mtime_utc(path),
                "notes": "",
            }
        )
    return pd.DataFrame(rows)


class StockDailyCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._cache: dict[str, pd.DataFrame | None] = {}
        self.schema_failures: dict[str, str] = {}

    def get(self, instrument: str) -> pd.DataFrame | None:
        instrument = str(instrument)
        if instrument in self._cache:
            return self._cache[instrument]
        path = self.directory / f"{instrument}.csv"
        if not path.exists():
            self._cache[instrument] = None
            self.schema_failures[instrument] = "missing_price_file"
            return None
        daily = pd.read_csv(path, low_memory=False)
        required = {"date", "open", "high", "low"}
        missing = required - set(daily.columns)
        if missing:
            self._cache[instrument] = None
            self.schema_failures[instrument] = "missing_columns:" + ";".join(sorted(missing))
            return None
        daily["date"] = pd.to_datetime(daily["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        daily = daily.sort_values("date", kind="stable").reset_index(drop=True)
        for col in ("open", "high", "low", "close"):
            if col in daily.columns:
                daily[col] = pd.to_numeric(daily[col], errors="coerce")
        self._cache[instrument] = daily
        return daily


@dataclass
class RegimeCalendar:
    calendar: dict[str, str]
    status: str
    non_date_row_n: int
    conflict_date_n: int
    multi_regime_date_n: int
    raw_row_n: int


def load_global_regime_calendar(path: Path) -> RegimeCalendar:
    df = pd.read_csv(path, low_memory=False)
    required = {"date", "daily_regime_bucket", "daily_regime_conflict_n", "daily_regime_conflict_flag"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"global regime calendar missing columns: {sorted(missing)}")
    date_mask = df["date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")
    real = df.loc[date_mask].copy()
    real["date"] = real["date"].map(date_text)
    real["daily_regime_conflict_n"] = numeric(real["daily_regime_conflict_n"]).fillna(0).astype(int)
    conflict = real.loc[bool_series(real["daily_regime_conflict_flag"]) | (real["daily_regime_conflict_n"] > 0)]
    pair = real[["date", "daily_regime_bucket"]].drop_duplicates()
    multi_n = int((pair.groupby("date").size() > 1).sum())
    if not conflict.empty:
        status = "blocked_regime_conflict_date"
    elif multi_n:
        status = "blocked_multi_regime_date"
    else:
        status = "pass"
    if status != "pass":
        calendar = {}
    else:
        calendar = dict(zip(pair["date"].astype(str), pair["daily_regime_bucket"].astype(str)))
    return RegimeCalendar(
        calendar=calendar,
        status=status,
        non_date_row_n=int((~date_mask).sum()),
        conflict_date_n=int(conflict["date"].nunique()),
        multi_regime_date_n=multi_n,
        raw_row_n=int(len(df)),
    )


def assign_split_from_intervals(date_value: Any, intervals: dict[str, tuple[str, str]]) -> str:
    text = date_text(date_value)
    for split, (start, end) in intervals.items():
        if start <= text <= end:
            return split
    return ""


def build_split_intervals(c0_all: pd.DataFrame) -> dict[str, tuple[str, str]]:
    intervals: dict[str, tuple[str, str]] = {}
    for split, group in c0_all.groupby("event_split", observed=True):
        dates = group["event_t0_date"].map(date_text)
        intervals[str(split)] = (str(dates.min()), str(dates.max()))
    return intervals


def load_c0_populations(canonical: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = canonical.copy()
    non_exec = bool_series(raw["non_executable_next_open"])
    mask = (
        raw["candidate_generation_status"].astype(str).eq("supported_canonical_event")
        & (~non_exec)
        & raw["event_t0_pit_status"].astype(str).eq("pass")
        & raw["trade_open_pit_status"].astype(str).eq("pass")
        & raw["trade_open_price"].notna()
    )
    all_c0 = raw.loc[mask].copy().reset_index(drop=True)
    for col in ("event_t0_date", "trade_open_date"):
        all_c0[col] = all_c0[col].map(date_text)
    all_c0["event_t0_pos"] = numeric(all_c0["event_t0_pos"])
    all_c0["trade_open_pos"] = numeric(all_c0["trade_open_pos"])
    all_c0["trade_open_price"] = numeric(all_c0["trade_open_price"])
    risk_on = all_c0.loc[all_c0["market_regime_bucket"].astype(str).eq("risk_on")].copy().reset_index(drop=True)
    risk_on["population_id"] = "c0_risk_on"
    risk_on["baseline_role"] = "c0_candidate"
    risk_on["event_date"] = risk_on["event_t0_date"]
    risk_on["entry_date"] = risk_on["trade_open_date"]
    risk_on["entry_pos"] = risk_on["trade_open_pos"]
    risk_on["entry_price"] = risk_on["trade_open_price"]
    risk_on["split"] = risk_on["event_split"].astype(str)
    risk_on["primary_family_id"] = risk_on["primary_family_id"].astype(str)
    risk_on["calendar_month"] = risk_on["event_t0_date"].map(month_text)
    risk_on["calendar_quarter"] = risk_on["event_t0_date"].map(quarter_text)
    risk_on["calendar_year"] = risk_on["event_t0_date"].map(year_text)
    risk_on["sample_weight"] = 1.0
    risk_on["source_row_id"] = risk_on["canonical_event_id"].astype(str)
    return all_c0, risk_on


def load_pit_membership_lookup(
    path: Path,
    pairs: set[tuple[str, str]],
    *,
    chunksize: int = 500_000,
) -> dict[tuple[str, str], str]:
    if not pairs:
        return {}
    instruments = {inst for inst, _ in pairs}
    dates = {date for _, date in pairs}
    usecols = ["usable_trade_date", "instrument", "is_listed", "is_st", "is_suspended"]
    lookup: dict[tuple[str, str], str] = {}
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize, low_memory=False):
        chunk["instrument"] = chunk["instrument"].astype(str)
        chunk["usable_trade_date"] = date_series_text(chunk["usable_trade_date"])
        sub = chunk.loc[chunk["instrument"].isin(instruments) & chunk["usable_trade_date"].isin(dates)]
        if sub.empty:
            continue
        for row in sub.to_dict("records"):
            key = (str(row["instrument"]), str(row["usable_trade_date"]))
            if key not in pairs:
                continue
            status = membership_row_status(row)
            prev = lookup.get(key)
            if prev is None or prev != "pass":
                lookup[key] = "pass" if status == "pass" or prev == "pass" else status
    return lookup


def attach_entry_status(
    events: pd.DataFrame,
    stock_cache: StockDailyCache,
    pit_lookup: dict[tuple[str, str], str],
    *,
    fill_price_from_daily: bool,
) -> pd.DataFrame:
    out = events.copy()
    statuses: list[str] = []
    membership_statuses: list[str] = []
    prices: list[float] = []
    path_keys: list[str] = []
    for row in out.itertuples(index=False):
        instrument = str(row.instrument)
        entry_date = date_text(row.entry_date)
        entry_pos = getattr(row, "entry_pos")
        entry_price = getattr(row, "entry_price")
        status = "ok"
        membership_status = pit_lookup.get((instrument, entry_date), "missing")
        daily = stock_cache.get(instrument)
        if daily is None or daily.empty:
            status = "missing_price_file"
        elif not entry_date:
            status = "missing_entry_date"
        elif pd.isna(entry_pos):
            status = "missing_entry_pos"
        else:
            pos = int(entry_pos)
            if pos < 0 or pos >= len(daily):
                status = "entry_pos_out_of_range"
            elif str(daily.loc[pos, "date"]) != entry_date:
                status = "entry_date_pos_mismatch"
            elif pd.isna(daily.loc[pos, "open"]):
                status = "missing_entry_price"
            elif fill_price_from_daily or pd.isna(entry_price):
                entry_price = float(daily.loc[pos, "open"])
        if status == "ok" and (pd.isna(entry_price) or float(entry_price) <= 0):
            status = "missing_entry_price"
        if status == "ok" and membership_status != "pass":
            status = "pit_membership_missing_or_not_executable"
        prices.append(float(entry_price) if pd.notna(entry_price) else np.nan)
        statuses.append(status)
        membership_statuses.append(membership_status)
        path_keys.append(path_key(instrument, entry_date, entry_pos, entry_price) if status == "ok" else "")
    out["entry_price"] = prices
    out["entry_status"] = statuses
    out["pit_membership_status"] = membership_statuses
    out["entry_blocked"] = out["entry_status"].ne("ok")
    out["path_key"] = path_keys
    return out


def load_r_core_population(registry: pd.DataFrame, regime: RegimeCalendar) -> tuple[pd.DataFrame, dict[str, int]]:
    raw_mask = (
        registry["arm_id"].astype(str).eq("08_R_core_event_regime_gated_raw")
        & registry["event_registry_status"].astype(str).eq("available")
        & registry["admission_status"].astype(str).eq("admitted")
    )
    raw = registry.loc[raw_mask].copy()
    headline = raw.loc[
        raw["event_execution_status"].astype(str).eq("executable_next_open")
        & raw["event_execution_date"].notna()
        & raw["event_execution_pos"].notna()
    ].copy()
    headline["event_signal_date"] = headline["event_signal_date"].map(date_text)
    headline["event_execution_date"] = headline["event_execution_date"].map(date_text)
    headline["market_regime_bucket"] = headline["event_signal_date"].map(regime.calendar)
    risk_on = headline.loc[headline["market_regime_bucket"].astype(str).eq("risk_on")].copy().reset_index(drop=True)
    risk_on["population_id"] = "r_core_risk_on"
    risk_on["baseline_role"] = "r_core_benchmark"
    risk_on["event_date"] = risk_on["event_signal_date"]
    risk_on["entry_date"] = risk_on["event_execution_date"]
    risk_on["entry_pos"] = numeric(risk_on["event_execution_pos"])
    risk_on["entry_price"] = np.nan
    risk_on["split"] = risk_on["event_split"].astype(str)
    risk_on["primary_family_id"] = "not_applicable"
    risk_on["calendar_month"] = risk_on["event_signal_date"].map(month_text)
    risk_on["calendar_quarter"] = risk_on["event_signal_date"].map(quarter_text)
    risk_on["calendar_year"] = risk_on["event_signal_date"].map(year_text)
    risk_on["sample_weight"] = 1.0
    risk_on["source_row_id"] = risk_on["event_key"].astype(str)
    counts = {
        "raw_status_filter_event_n": int(len(raw)),
        "headline_executable_next_open_event_n": int(len(headline)),
        "headline_risk_on_event_n": int(len(risk_on)),
        "excluded_non_next_open_n": int(len(raw) - raw["event_execution_status"].astype(str).eq("executable_next_open").sum()),
        "excluded_missing_execution_date_or_pos_n": int(
            (
                raw["event_execution_status"].astype(str).eq("executable_next_open")
                & (raw["event_execution_date"].isna() | raw["event_execution_pos"].isna())
            ).sum()
        ),
    }
    return risk_on, counts


def add_random_entry_info(candidates: pd.DataFrame, stock_cache: StockDailyCache) -> pd.DataFrame:
    out = candidates.copy()
    entry_dates = pd.Series("", index=out.index, dtype=object)
    entry_pos = pd.Series(np.nan, index=out.index, dtype=float)
    entry_price = pd.Series(np.nan, index=out.index, dtype=float)
    entry_status = pd.Series("pending", index=out.index, dtype=object)
    for instrument, idx in out.groupby("instrument").groups.items():
        daily = stock_cache.get(str(instrument))
        if daily is None or daily.empty:
            entry_status.loc[idx] = "missing_price_file"
            continue
        dates = daily["date"].astype(str).to_numpy()
        opens = daily["open"].to_numpy(dtype=float)
        event_dates = out.loc[idx, "event_date"].astype(str).to_numpy()
        pos = np.searchsorted(dates, event_dates, side="right")
        valid = pos < len(daily)
        idx_arr = np.array(list(idx))
        if valid.any():
            valid_idx = idx_arr[valid]
            valid_pos = pos[valid]
            entry_dates.loc[valid_idx] = dates[valid_pos]
            entry_pos.loc[valid_idx] = valid_pos
            entry_price.loc[valid_idx] = opens[valid_pos]
            entry_status.loc[valid_idx] = np.where(np.isfinite(opens[valid_pos]), "ok", "missing_entry_price")
        if (~valid).any():
            entry_status.loc[idx_arr[~valid]] = "no_next_open_after_event_date"
    out["entry_date"] = entry_dates
    out["entry_pos"] = entry_pos
    out["entry_price"] = entry_price
    out["entry_status_pre_pit"] = entry_status
    return out


def load_random_candidate_pool(
    pit_path: Path,
    regime: RegimeCalendar,
    split_intervals: dict[str, tuple[str, str]],
    boards: set[str],
    exact_c0_keys: set[tuple[str, str]],
    stock_cache: StockDailyCache,
    *,
    exclude_exact_c0_keys: bool,
    chunksize: int = 500_000,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    usecols = ["usable_trade_date", "instrument", "board_bucket", "is_listed", "is_st", "is_suspended"]
    rows: list[pd.DataFrame] = []
    exact_excluded_rows: list[dict[str, Any]] = []
    for chunk in pd.read_csv(pit_path, usecols=usecols, chunksize=chunksize, low_memory=False):
        chunk["instrument"] = chunk["instrument"].astype(str)
        chunk["event_date"] = date_series_text(chunk["usable_trade_date"])
        chunk["market_regime_bucket"] = chunk["event_date"].map(regime.calendar)
        chunk["split"] = chunk["event_date"].map(lambda value: assign_split_from_intervals(value, split_intervals))
        mask = (
            chunk["split"].astype(str).ne("")
            & chunk["board_bucket"].astype(str).isin(boards)
            & chunk["market_regime_bucket"].astype(str).eq("risk_on")
            & bool_series(chunk["is_listed"])
            & (~bool_series(chunk["is_st"]))
            & (~bool_series(chunk["is_suspended"]))
        )
        sub = chunk.loc[mask].copy()
        if sub.empty:
            continue
        sub["calendar_month"] = sub["event_date"].map(month_text)
        sub["calendar_quarter"] = sub["event_date"].map(quarter_text)
        sub["calendar_year"] = sub["event_date"].map(year_text)
        exact_mask = [(str(row.instrument), str(row.event_date)) in exact_c0_keys for row in sub.itertuples(index=False)]
        sub["exact_c0_key_excluded_flag"] = exact_mask
        if exclude_exact_c0_keys:
            excluded = sub.loc[sub["exact_c0_key_excluded_flag"]]
            if not excluded.empty:
                exact_excluded_rows.append(
                    excluded.groupby(["split", "board_bucket", "calendar_month"], observed=True)
                    .size()
                    .rename("exact_c0_key_excluded_n")
                    .reset_index()
                )
            sub = sub.loc[~sub["exact_c0_key_excluded_flag"]].copy()
        rows.append(sub)
    if not rows:
        return pd.DataFrame(), pd.DataFrame()
    candidates = pd.concat(rows, ignore_index=True)
    candidates = add_random_entry_info(candidates, stock_cache)
    candidates = candidates.loc[candidates["entry_status_pre_pit"].eq("ok")].copy()
    pairs = {(str(row.instrument), str(row.entry_date)) for row in candidates.itertuples(index=False)}
    membership = load_pit_membership_lookup(pit_path, pairs)
    candidates["pit_membership_status"] = [
        membership.get((str(row.instrument), str(row.entry_date)), "missing") for row in candidates.itertuples(index=False)
    ]
    candidates = candidates.loc[candidates["pit_membership_status"].eq("pass")].copy().reset_index(drop=True)
    candidates["path_key"] = [
        path_key(row.instrument, row.entry_date, row.entry_pos, row.entry_price) for row in candidates.itertuples(index=False)
    ]
    candidates["candidate_row_id"] = np.arange(len(candidates), dtype=np.int64)
    if exact_excluded_rows:
        exact_audit = pd.concat(exact_excluded_rows, ignore_index=True)
        exact_audit = exact_audit.groupby(["split", "board_bucket", "calendar_month"], observed=True, as_index=False)[
            "exact_c0_key_excluded_n"
        ].sum()
    else:
        exact_audit = pd.DataFrame(
            columns=["split", "board_bucket", "calendar_month", "exact_c0_key_excluded_n"]
        )
    return candidates, exact_audit


def sample_random_entries(
    c0: pd.DataFrame,
    candidates: pd.DataFrame,
    exact_audit: pd.DataFrame,
    *,
    base_seed: int,
    random_seed_n: int,
    replacement_threshold: float,
    fallback_merge: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    target = (
        c0.groupby(["split", "board_bucket", "calendar_month", "calendar_quarter"], observed=True)
        .size()
        .rename("c0_cell_event_n")
        .reset_index()
    )
    cell_groups = {key: group.index.to_numpy() for key, group in candidates.groupby(["split", "board_bucket", "calendar_month"], observed=True)}
    quarter_groups = {key: group.index.to_numpy() for key, group in candidates.groupby(["split", "board_bucket", "calendar_quarter"], observed=True)}
    exact_counts = {
        (str(row.split), str(row.board_bucket), str(row.calendar_month)): int(row.exact_c0_key_excluded_n)
        for row in exact_audit.itertuples(index=False)
    }
    sampled_parts: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    draw_id = 0
    for seed_i in range(random_seed_n):
        seed = base_seed + seed_i
        rng = np.random.default_rng(seed)
        for target_row in target.itertuples(index=False):
            split = str(target_row.split)
            board = str(target_row.board_bucket)
            month = str(target_row.calendar_month)
            quarter = str(target_row.calendar_quarter)
            c0_n = int(target_row.c0_cell_event_n)
            original_idx = cell_groups.get((split, board, month), np.array([], dtype=int))
            sample_idx = original_idx
            fallback_applied = False
            fallback_rule = ""
            random_candidate_cell_n = int(len(original_idx))
            replacement_rate = 0.0 if random_candidate_cell_n >= c0_n and c0_n else 1.0 - safe_rate(random_candidate_cell_n, c0_n)
            status = "ok"
            if random_candidate_cell_n == 0:
                status = "blocked_empty_candidate_cell"
            elif replacement_rate > replacement_threshold:
                status = "degraded_high_replacement"
            if (status in {"blocked_empty_candidate_cell", "degraded_high_replacement"}) and fallback_merge:
                merged_idx = quarter_groups.get((split, board, quarter), np.array([], dtype=int))
                merged_n = int(len(merged_idx))
                merged_rate = 0.0 if merged_n >= c0_n and c0_n else 1.0 - safe_rate(merged_n, c0_n)
                if merged_n > 0:
                    sample_idx = merged_idx
                    fallback_applied = True
                    fallback_rule = "calendar_month_to_calendar_quarter"
                    status = "ok_fallback_merged" if merged_rate <= replacement_threshold else "degraded_high_replacement"
                    replacement_rate = merged_rate
                else:
                    merged_rate = np.nan
            else:
                merged_n = np.nan
                merged_rate = np.nan
            if len(sample_idx) == 0:
                audit_rows.append(
                    {
                        "seed": seed,
                        "split": split,
                        "board_bucket": board,
                        "calendar_month": month,
                        "calendar_quarter": quarter,
                        "c0_cell_event_n": c0_n,
                        "random_candidate_cell_n": random_candidate_cell_n,
                        "exact_c0_key_excluded_n": exact_counts.get((split, board, month), 0),
                        "sampled_event_n": 0,
                        "replacement_used_flag": False,
                        "replacement_rate": np.nan,
                        "fallback_merge_applied_flag": fallback_applied,
                        "fallback_merge_rule": fallback_rule,
                        "merged_random_candidate_cell_n": merged_n,
                        "merged_replacement_rate": merged_rate,
                        "cell_status": "blocked_empty_candidate_cell",
                    }
                )
                continue
            replace = len(sample_idx) < c0_n
            chosen = rng.choice(sample_idx, size=c0_n, replace=replace)
            draws = candidates.loc[chosen].copy()
            draw_count = len(draws)
            draws.insert(0, "seed", seed)
            draws.insert(1, "sample_draw_id", np.arange(draw_id, draw_id + draw_count, dtype=np.int64))
            draw_id += draw_count
            draws["c0_match_cell_id"] = f"{split}|{board}|{month}"
            draws["replacement_used_flag"] = bool(replace)
            draws["replacement_draw_index"] = np.arange(draw_count, dtype=np.int32)
            draws["sample_weight"] = 1.0
            draws["sampling_status"] = status
            draws["population_id"] = "matched_random_risk_on_seed_" + str(seed)
            draws["baseline_role"] = "matched_random"
            draws["primary_family_id"] = "not_applicable"
            sampled_parts.append(draws)
            audit_rows.append(
                {
                    "seed": seed,
                    "split": split,
                    "board_bucket": board,
                    "calendar_month": month,
                    "calendar_quarter": quarter,
                    "c0_cell_event_n": c0_n,
                    "random_candidate_cell_n": random_candidate_cell_n,
                    "exact_c0_key_excluded_n": exact_counts.get((split, board, month), 0),
                    "sampled_event_n": draw_count,
                    "replacement_used_flag": bool(replace),
                    "replacement_rate": replacement_rate,
                    "fallback_merge_applied_flag": fallback_applied,
                    "fallback_merge_rule": fallback_rule,
                    "merged_random_candidate_cell_n": merged_n,
                    "merged_replacement_rate": merged_rate,
                    "cell_status": status,
                }
            )
    sampled = pd.concat(sampled_parts, ignore_index=True) if sampled_parts else pd.DataFrame()
    audit = pd.DataFrame(audit_rows)
    if not sampled.empty:
        sampled = sampled.rename(
            columns={
                "event_date": "random_event_t0_date",
                "entry_date": "random_trade_open_date",
            }
        )
    return sampled, audit


def build_path_cache(
    events: pd.DataFrame,
    stock_cache: StockDailyCache,
    horizons: list[int],
    lowers: list[float],
    uppers: list[float],
) -> pd.DataFrame:
    unique = events.loc[events["path_key"].astype(str).ne("")].drop_duplicates("path_key").copy()
    rows: list[dict[str, Any]] = []
    max_h = max(horizons)
    for row in unique.itertuples(index=False):
        daily = stock_cache.get(str(row.instrument))
        base = {
            "path_key": str(row.path_key),
            "instrument": str(row.instrument),
            "entry_date": date_text(row.entry_date),
            "entry_pos": int(row.entry_pos) if pd.notna(row.entry_pos) else np.nan,
            "entry_price": float(row.entry_price) if pd.notna(row.entry_price) else np.nan,
            "entry_blocked": bool(getattr(row, "entry_blocked", False)),
        }
        if daily is None or daily.empty or base["entry_blocked"] or pd.isna(base["entry_pos"]) or pd.isna(base["entry_price"]):
            for horizon in horizons:
                base[f"horizon_complete_{horizon}d"] = False
                base[f"min_low_return_{horizon}d"] = np.nan
            base["max_high_return_20d"] = np.nan
            for horizon in horizons:
                for lower in lowers:
                    base[f"time_to_lower_{barrier_suffix(lower)}_{horizon}d"] = np.nan
            for upper in uppers:
                base[f"time_to_upper_{barrier_suffix(upper)}_20d"] = np.nan
            rows.append(base)
            continue
        pos = int(base["entry_pos"])
        price = float(base["entry_price"])
        high = daily["high"].to_numpy(dtype=float)
        low = daily["low"].to_numpy(dtype=float)
        if pos < 0 or pos >= len(daily):
            base["entry_blocked"] = True
        for horizon in horizons:
            complete = (not base["entry_blocked"]) and pos + horizon < len(daily)
            base[f"horizon_complete_{horizon}d"] = bool(complete)
            if complete:
                l_slice = low[pos : pos + horizon + 1]
                base[f"min_low_return_{horizon}d"] = float(np.nanmin(l_slice) / price - 1.0)
                for lower in lowers:
                    hits = np.flatnonzero(l_slice <= price * (1.0 + lower))
                    base[f"time_to_lower_{barrier_suffix(lower)}_{horizon}d"] = int(hits[0]) if len(hits) else np.nan
            else:
                base[f"min_low_return_{horizon}d"] = np.nan
                for lower in lowers:
                    base[f"time_to_lower_{barrier_suffix(lower)}_{horizon}d"] = np.nan
        if (not base["entry_blocked"]) and pos + max_h < len(daily):
            h_slice = high[pos : pos + max_h + 1]
            base["max_high_return_20d"] = float(np.nanmax(h_slice) / price - 1.0)
            for upper in uppers:
                hits = np.flatnonzero(h_slice >= price * (1.0 + upper))
                base[f"time_to_upper_{barrier_suffix(upper)}_20d"] = int(hits[0]) if len(hits) else np.nan
        else:
            base["max_high_return_20d"] = np.nan
            for upper in uppers:
                base[f"time_to_upper_{barrier_suffix(upper)}_20d"] = np.nan
        rows.append(base)
    return pd.DataFrame(rows)


def slice_specs(events: pd.DataFrame, *, include_family: bool) -> list[tuple[str, str, str, str, str, str, pd.Series]]:
    specs: list[tuple[str, str, str, str, str, str, pd.Series]] = [
        ("all", RISK_ON_ALL_SCOPE, ALL_TEXT, ALL_TEXT, ALL_TEXT, ALL_TEXT, pd.Series(True, index=events.index))
    ]
    for split in sorted(events["split"].dropna().astype(str).unique()):
        specs.append(("split", SPLIT_SCOPE, split, ALL_TEXT, ALL_TEXT, ALL_TEXT, events["split"].astype(str).eq(split)))
    for board in sorted(events["board_bucket"].dropna().astype(str).unique()):
        specs.append(("board", BOARD_SCOPE, ALL_TEXT, board, ALL_TEXT, ALL_TEXT, events["board_bucket"].astype(str).eq(board)))
    for year in sorted(events["calendar_year"].dropna().astype(str).unique()):
        if year:
            specs.append(("year", YEAR_SCOPE, ALL_TEXT, ALL_TEXT, ALL_TEXT, year, events["calendar_year"].astype(str).eq(year)))
    if include_family and "primary_family_id" in events.columns:
        for family in sorted(events["primary_family_id"].dropna().astype(str).unique()):
            specs.append(("family", FAMILY_SCOPE, ALL_TEXT, ALL_TEXT, family, ALL_TEXT, events["primary_family_id"].astype(str).eq(family)))
    return specs


def weighted_sum(mask: pd.Series, weights: pd.Series) -> float:
    return float(weights.loc[mask].sum())


def aggregate_fast_fail_grid(
    events_with_path: pd.DataFrame,
    *,
    population_id: str,
    baseline_role: str,
    horizons: list[int],
    lowers: list[float],
    include_family: bool,
    diagnostic_family: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    weights = events_with_path["sample_weight"].astype(float)
    for slice_type, scope_id, split, board, family, year, mask in slice_specs(events_with_path, include_family=include_family):
        sub = events_with_path.loc[mask].copy()
        if sub.empty:
            continue
        sub_w = weights.loc[sub.index]
        event_n = float(sub_w.sum())
        for horizon in horizons:
            complete_col = f"horizon_complete_{horizon}d"
            complete = (~sub["entry_blocked"].astype(bool)) & bool_series(sub[complete_col])
            entry_blocked = sub["entry_blocked"].astype(bool)
            censored = (~entry_blocked) & (~complete)
            for lower in lowers:
                time_col = f"time_to_lower_{barrier_suffix(lower)}_{horizon}d"
                fast_fail = complete & sub[time_col].notna()
                fast_fail_n = weighted_sum(fast_fail, sub_w)
                complete_n = weighted_sum(complete, sub_w)
                times = pd.to_numeric(sub.loc[fast_fail, time_col], errors="coerce").dropna()
                rows.append(
                    {
                        "population_id": population_id,
                        "baseline_role": baseline_role,
                        "scope_id": scope_id,
                        "slice_type": slice_type,
                        "split": split,
                        "board_bucket": board,
                        "primary_family_id": family,
                        "calendar_year": year,
                        "horizon_sessions": int(horizon),
                        "lower_barrier_pct": float(lower),
                        "event_n": event_n,
                        "entry_blocked_n": weighted_sum(entry_blocked, sub_w),
                        "censored_n": weighted_sum(censored, sub_w),
                        "complete_executable_event_n": complete_n,
                        "fast_fail_n": fast_fail_n,
                        "fast_fail_rate": safe_rate(fast_fail_n, complete_n),
                        "no_fast_fail_n": complete_n - fast_fail_n if pd.notna(complete_n) else np.nan,
                        "no_fast_fail_rate": 1.0 - safe_rate(fast_fail_n, complete_n) if complete_n else np.nan,
                        "median_time_to_fast_fail_sessions": float(times.median()) if not times.empty else np.nan,
                        "p75_time_to_fast_fail_sessions": float(times.quantile(0.75)) if not times.empty else np.nan,
                        "label_status": "ok" if complete_n >= 1 else "no_complete_executable_events",
                        "diagnostic_only_flag": bool(diagnostic_family and slice_type == "family"),
                    }
                )
    return pd.DataFrame(rows)


def quantile_random_grid(seed_grid: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "scope_id",
        "slice_type",
        "split",
        "board_bucket",
        "primary_family_id",
        "calendar_year",
        "horizon_sessions",
        "lower_barrier_pct",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in seed_grid.groupby(keys, dropna=False, observed=True):
        base = dict(zip(keys, key))
        for quantile, suffix in [(0.05, "p05"), (0.50, "p50"), (0.95, "p95")]:
            row = {
                "population_id": f"matched_random_risk_on_{suffix}",
                "baseline_role": "matched_random_distribution",
                **base,
                "event_n": float(group["event_n"].quantile(quantile)),
                "entry_blocked_n": float(group["entry_blocked_n"].quantile(quantile)),
                "censored_n": float(group["censored_n"].quantile(quantile)),
                "complete_executable_event_n": float(group["complete_executable_event_n"].quantile(quantile)),
                "fast_fail_n": float(group["fast_fail_n"].quantile(quantile)),
                "fast_fail_rate": float(group["fast_fail_rate"].quantile(quantile)),
                "no_fast_fail_n": float(group["no_fast_fail_n"].quantile(quantile)),
                "no_fast_fail_rate": float(group["no_fast_fail_rate"].quantile(quantile)),
                "median_time_to_fast_fail_sessions": float(group["median_time_to_fast_fail_sessions"].quantile(quantile)),
                "p75_time_to_fast_fail_sessions": float(group["p75_time_to_fast_fail_sessions"].quantile(quantile)),
                "label_status": "random_seed_distribution",
                "diagnostic_only_flag": bool(group["diagnostic_only_flag"].astype(bool).any()),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def aggregate_conditional(
    events_with_path: pd.DataFrame,
    *,
    population_id: str,
    baseline_role: str,
    lowers: list[float],
    uppers: list[float],
    condition_lower: float,
    condition_horizon: int,
    upper_horizon: int,
    include_family: bool,
    diagnostic_family: bool,
) -> pd.DataFrame:
    del lowers
    rows: list[dict[str, Any]] = []
    lower_col = f"time_to_lower_{barrier_suffix(condition_lower)}_{condition_horizon}d"
    complete_col = f"horizon_complete_{condition_horizon}d"
    weights = events_with_path["sample_weight"].astype(float)
    for slice_type, scope_id, split, board, family, year, mask in slice_specs(events_with_path, include_family=include_family):
        sub = events_with_path.loc[mask].copy()
        if sub.empty:
            continue
        sub_w = weights.loc[sub.index]
        complete = (~sub["entry_blocked"].astype(bool)) & bool_series(sub[complete_col])
        no_fast_fail = complete & sub[lower_col].isna()
        complete_n = weighted_sum(complete, sub_w)
        no_fast_n = weighted_sum(no_fast_fail, sub_w)
        for upper in uppers:
            upper_col = f"time_to_upper_{barrier_suffix(upper)}_{upper_horizon}d"
            upper_touch = complete & sub[upper_col].notna()
            upper_given = no_fast_fail & sub[upper_col].notna()
            upper_total_n = weighted_sum(upper_touch, sub_w)
            upper_given_n = weighted_sum(upper_given, sub_w)
            total_rate = safe_rate(upper_total_n, complete_n)
            given_rate = safe_rate(upper_given_n, no_fast_n)
            rows.append(
                {
                    "population_id": population_id,
                    "baseline_role": baseline_role,
                    "scope_id": scope_id,
                    "slice_type": slice_type,
                    "split": split,
                    "board_bucket": board,
                    "primary_family_id": family,
                    "calendar_year": year,
                    "condition_label_id": PRIMARY_LABEL_ID,
                    "condition_horizon_sessions": int(condition_horizon),
                    "condition_lower_barrier_pct": float(condition_lower),
                    "upper_horizon_sessions": int(upper_horizon),
                    "upper_barrier_pct": float(upper),
                    "complete_executable_event_n": complete_n,
                    "no_fast_fail_n": no_fast_n,
                    "upper_touch_n_total": upper_total_n,
                    "upper_touch_rate_total": total_rate,
                    "upper_touch_n_given_no_fast_fail": upper_given_n,
                    "upper_touch_rate_given_no_fast_fail": given_rate,
                    "uplift_given_no_fast_fail_vs_total": given_rate / total_rate if pd.notna(given_rate) and pd.notna(total_rate) and total_rate != 0 else np.nan,
                    "conditional_readout_status": "ok" if no_fast_n else "no_no_fast_fail_rows",
                    "diagnostic_only_flag": bool(diagnostic_family and slice_type == "family"),
                }
            )
    return pd.DataFrame(rows)


def quantile_random_conditional(seed_conditional: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "scope_id",
        "slice_type",
        "split",
        "board_bucket",
        "primary_family_id",
        "calendar_year",
        "condition_label_id",
        "condition_horizon_sessions",
        "condition_lower_barrier_pct",
        "upper_horizon_sessions",
        "upper_barrier_pct",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in seed_conditional.groupby(keys, dropna=False, observed=True):
        base = dict(zip(keys, key))
        for quantile, suffix in [(0.05, "p05"), (0.50, "p50"), (0.95, "p95")]:
            row = {
                "population_id": f"matched_random_risk_on_{suffix}",
                "baseline_role": "matched_random_distribution",
                **base,
                "complete_executable_event_n": float(group["complete_executable_event_n"].quantile(quantile)),
                "no_fast_fail_n": float(group["no_fast_fail_n"].quantile(quantile)),
                "upper_touch_n_total": float(group["upper_touch_n_total"].quantile(quantile)),
                "upper_touch_rate_total": float(group["upper_touch_rate_total"].quantile(quantile)),
                "upper_touch_n_given_no_fast_fail": float(group["upper_touch_n_given_no_fast_fail"].quantile(quantile)),
                "upper_touch_rate_given_no_fast_fail": float(group["upper_touch_rate_given_no_fast_fail"].quantile(quantile)),
                "uplift_given_no_fast_fail_vs_total": float(group["uplift_given_no_fast_fail_vs_total"].quantile(quantile)),
                "conditional_readout_status": "random_seed_distribution",
                "diagnostic_only_flag": bool(group["diagnostic_only_flag"].astype(bool).any()),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def add_conditional_baselines(conditional: pd.DataFrame) -> pd.DataFrame:
    out = conditional.copy()
    key_cols = [
        "scope_id",
        "slice_type",
        "split",
        "board_bucket",
        "primary_family_id",
        "calendar_year",
        "condition_label_id",
        "condition_horizon_sessions",
        "condition_lower_barrier_pct",
        "upper_horizon_sessions",
        "upper_barrier_pct",
    ]
    random_stats = {}
    for suffix in ("p05", "p50", "p95"):
        frame = out.loc[out["population_id"].eq(f"matched_random_risk_on_{suffix}")]
        random_stats[suffix] = frame[key_cols + ["upper_touch_rate_given_no_fast_fail"]].rename(
            columns={"upper_touch_rate_given_no_fast_fail": f"random_upper_touch_rate_given_no_fast_fail_{suffix}"}
        )
    rcore = out.loc[out["population_id"].eq("r_core_risk_on"), key_cols + ["upper_touch_rate_given_no_fast_fail"]].rename(
        columns={"upper_touch_rate_given_no_fast_fail": "r_core_upper_touch_rate_given_no_fast_fail"}
    )
    for suffix, frame in random_stats.items():
        out = out.merge(frame, on=key_cols, how="left")
    out = out.merge(rcore, on=key_cols, how="left")
    return out


def build_uplift(c0_grid: pd.DataFrame, rcore_grid: pd.DataFrame, random_quantiles: pd.DataFrame) -> pd.DataFrame:
    comparable = c0_grid.loc[c0_grid["slice_type"].isin(["all", "split", "board", "year", "family"])].copy()
    key_cols = [
        "scope_id",
        "slice_type",
        "split",
        "board_bucket",
        "primary_family_id",
        "calendar_year",
        "horizon_sessions",
        "lower_barrier_pct",
    ]
    random_cols = []
    for suffix in ("p05", "p50", "p95"):
        r = random_quantiles.loc[random_quantiles["population_id"].eq(f"matched_random_risk_on_{suffix}")]
        r = r[key_cols + ["fast_fail_rate"]].rename(columns={"fast_fail_rate": f"random_fast_fail_rate_{suffix}"})
        comparable = comparable.merge(r, on=key_cols, how="left")
        random_cols.append(f"random_fast_fail_rate_{suffix}")
    rcore = rcore_grid[key_cols + ["fast_fail_rate"]].rename(columns={"fast_fail_rate": "r_core_fast_fail_rate"})
    comparable = comparable.merge(rcore, on=key_cols, how="left")
    comparable = comparable.rename(
        columns={
            "complete_executable_event_n": "c0_complete_executable_event_n",
            "fast_fail_rate": "c0_fast_fail_rate",
        }
    )
    comparable["fast_fail_abs_delta_vs_random_p50"] = comparable["c0_fast_fail_rate"] - comparable["random_fast_fail_rate_p50"]
    comparable["fast_fail_abs_delta_vs_r_core"] = comparable["c0_fast_fail_rate"] - comparable["r_core_fast_fail_rate"]
    comparable["fast_fail_relative_reduction_vs_random_p50"] = 1.0 - comparable["c0_fast_fail_rate"] / comparable["random_fast_fail_rate_p50"]
    comparable["fast_fail_relative_reduction_vs_r_core"] = 1.0 - comparable["c0_fast_fail_rate"] / comparable["r_core_fast_fail_rate"]
    comparable["diagnostic_only_flag"] = comparable["slice_type"].eq("family")
    comparable["uplift_status"] = np.where(
        comparable["diagnostic_only_flag"],
        "diagnostic_only_family_slice",
        np.where(comparable["fast_fail_abs_delta_vs_random_p50"] < 0, "c0_lower_fast_fail_than_random_p50", "no_random_uplift"),
    )
    cols = [
        "scope_id",
        "split",
        "slice_type",
        "board_bucket",
        "primary_family_id",
        "calendar_year",
        "horizon_sessions",
        "lower_barrier_pct",
        "c0_complete_executable_event_n",
        "c0_fast_fail_rate",
        *random_cols,
        "r_core_fast_fail_rate",
        "fast_fail_abs_delta_vs_random_p50",
        "fast_fail_abs_delta_vs_r_core",
        "fast_fail_relative_reduction_vs_random_p50",
        "fast_fail_relative_reduction_vs_r_core",
        "uplift_status",
        "diagnostic_only_flag",
    ]
    return comparable[cols].copy()


def build_retention(grid: pd.DataFrame, condition_lower: float, condition_horizon: int) -> pd.DataFrame:
    sub = grid.loc[
        grid["lower_barrier_pct"].eq(float(condition_lower))
        & grid["horizon_sessions"].eq(int(condition_horizon))
    ].copy()
    sub["retention_after_no_fast_fail"] = sub["no_fast_fail_rate"]
    return sub[
        [
            "population_id",
            "scope_id",
            "slice_type",
            "split",
            "board_bucket",
            "primary_family_id",
            "calendar_year",
            "complete_executable_event_n",
            "fast_fail_n",
            "fast_fail_rate",
            "no_fast_fail_n",
            "no_fast_fail_rate",
            "retention_after_no_fast_fail",
            "diagnostic_only_flag",
        ]
    ]


def build_population_membership_audit(
    c0_all: pd.DataFrame,
    c0: pd.DataFrame,
    rcore_counts: dict[str, int],
    rcore: pd.DataFrame,
    random_candidates: pd.DataFrame,
    regime: RegimeCalendar,
    split_intervals: dict[str, tuple[str, str]],
    expected_counts: dict[str, Any],
) -> pd.DataFrame:
    split_note = ";".join(f"{k}:{v[0]}..{v[1]}" for k, v in sorted(split_intervals.items()))
    rows = [
        {
            "population_id": "c0_risk_on",
            "source_artifact_id": "state_change_candidate_event_canonical",
            "raw_event_n": int(len(c0_all)),
            "after_status_filter_event_n": int(len(c0_all)),
            "risk_on_join_date_field": "market_regime_bucket_upstream",
            "risk_on_join_status": "pass",
            "global_regime_calendar_status": regime.status,
            "non_date_calendar_row_n": regime.non_date_row_n,
            "regime_conflict_date_n": regime.conflict_date_n,
            "multi_regime_date_n": regime.multi_regime_date_n,
            "split_assignment_source": "12A2 event_split",
            "split_assignment_status": "pass",
            "entry_status_policy": "canonical_trade_open",
            "expected_event_n": int(expected_counts["c0_primary_risk_on_event_n"]),
            "actual_event_n": int(len(c0)),
            "count_drift_n": int(len(c0) - int(expected_counts["c0_primary_risk_on_event_n"])),
            "count_drift_flag": bool(len(c0) != int(expected_counts["c0_primary_risk_on_event_n"])),
            "notes": split_note,
        },
        {
            "population_id": "r_core_risk_on",
            "source_artifact_id": "r_core_arm_event_registry",
            "raw_event_n": int(expected_counts["r_core_12a3_quoted_raw_event_n"]),
            "after_status_filter_event_n": int(rcore_counts["headline_executable_next_open_event_n"]),
            "risk_on_join_date_field": "event_signal_date",
            "risk_on_join_status": "pass",
            "global_regime_calendar_status": regime.status,
            "non_date_calendar_row_n": regime.non_date_row_n,
            "regime_conflict_date_n": regime.conflict_date_n,
            "multi_regime_date_n": regime.multi_regime_date_n,
            "split_assignment_source": "r_core event_split",
            "split_assignment_status": "pass",
            "entry_status_policy": "headline_requires_executable_next_open",
            "expected_event_n": int(expected_counts["r_core_headline_executable_next_open_event_n"]),
            "actual_event_n": int(rcore_counts["headline_executable_next_open_event_n"]),
            "count_drift_n": int(rcore_counts["headline_executable_next_open_event_n"] - int(expected_counts["r_core_headline_executable_next_open_event_n"])),
            "count_drift_flag": bool(rcore_counts["headline_executable_next_open_event_n"] != int(expected_counts["r_core_headline_executable_next_open_event_n"])),
            "notes": f"risk_on_after_join={len(rcore)}; quoted_raw_minus_headline={int(expected_counts['r_core_12a3_quoted_raw_event_n']) - int(rcore_counts['headline_executable_next_open_event_n'])}",
        },
        {
            "population_id": "matched_random_risk_on",
            "source_artifact_id": "pit_executable_daily",
            "raw_event_n": np.nan,
            "after_status_filter_event_n": int(len(random_candidates)),
            "risk_on_join_date_field": "random_event_t0_date",
            "risk_on_join_status": "pass",
            "global_regime_calendar_status": regime.status,
            "non_date_calendar_row_n": regime.non_date_row_n,
            "regime_conflict_date_n": regime.conflict_date_n,
            "multi_regime_date_n": regime.multi_regime_date_n,
            "split_assignment_source": "C0 split date intervals",
            "split_assignment_status": "pass",
            "entry_status_policy": "next_open_after_random_event_t0",
            "expected_event_n": np.nan,
            "actual_event_n": int(len(random_candidates)),
            "count_drift_n": np.nan,
            "count_drift_flag": False,
            "notes": split_note,
        },
    ]
    return pd.DataFrame(rows)


def build_entry_audit(
    populations: dict[str, pd.DataFrame],
    rcore_counts: dict[str, int],
    expected_counts: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for population_id, frame in populations.items():
        event_n = int(len(frame))
        entry_blocked = frame["entry_blocked"].astype(bool) if "entry_blocked" in frame.columns else pd.Series(False, index=frame.index)
        status = frame["entry_status"].astype(str) if "entry_status" in frame.columns else pd.Series("ok", index=frame.index)
        membership = frame["pit_membership_status"].astype(str) if "pit_membership_status" in frame.columns else pd.Series("pass", index=frame.index)
        rows.append(
            {
                "population_id": population_id,
                "event_n": event_n,
                "entry_status_policy": "headline_requires_executable_next_open" if population_id == "r_core_risk_on" else "canonical_or_random_next_open",
                "executable_entry_n": int((~entry_blocked).sum()),
                "entry_blocked_n": int(entry_blocked.sum()),
                "missing_price_file_n": int(status.eq("missing_price_file").sum()),
                "missing_entry_date_n": int(status.eq("missing_entry_date").sum()),
                "missing_entry_pos_n": int(status.isin(["missing_entry_pos", "entry_pos_out_of_range"]).sum()),
                "missing_entry_price_n": int(status.eq("missing_entry_price").sum()),
                "entry_date_pos_mismatch_n": int(status.eq("entry_date_pos_mismatch").sum()),
                "pit_membership_missing_n": int(membership.eq("missing").sum()),
                "pit_membership_not_executable_n": int((membership.ne("pass") & membership.ne("missing")).sum()),
                "r_core_registry_raw_event_n": int(expected_counts["r_core_12a3_quoted_raw_event_n"]) if population_id == "r_core_risk_on" else np.nan,
                "r_core_executable_next_open_event_n": int(rcore_counts["headline_executable_next_open_event_n"]) if population_id == "r_core_risk_on" else np.nan,
                "r_core_excluded_non_next_open_n": int(expected_counts["r_core_12a3_quoted_raw_event_n"]) - int(rcore_counts["headline_executable_next_open_event_n"]) if population_id == "r_core_risk_on" else np.nan,
                "r_core_excluded_missing_execution_date_or_pos_n": int(rcore_counts["excluded_missing_execution_date_or_pos_n"]) if population_id == "r_core_risk_on" else np.nan,
                "entry_parity_gate_pass": bool(not entry_blocked.any()),
            }
        )
    return pd.DataFrame(rows)


def row_lookup(frame: pd.DataFrame, *, scope_id: str, split: str, horizon: int | None = None, lower: float | None = None, upper: float | None = None) -> pd.Series:
    mask = frame["scope_id"].eq(scope_id) & frame["split"].eq(split)
    if horizon is not None and "horizon_sessions" in frame.columns:
        mask &= frame["horizon_sessions"].eq(horizon)
    if lower is not None and "lower_barrier_pct" in frame.columns:
        mask &= frame["lower_barrier_pct"].eq(float(lower))
    if upper is not None and "upper_barrier_pct" in frame.columns:
        mask &= frame["upper_barrier_pct"].eq(float(upper))
    rows = frame.loc[mask]
    return rows.iloc[0] if not rows.empty else pd.Series(dtype=object)


def evaluate_decision(
    uplift: pd.DataFrame,
    conditional: pd.DataFrame,
    sampling_audit: pd.DataFrame,
    entry_audit: pd.DataFrame,
    membership_audit: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    gates = config["gates"]
    lower = float(config["primary_label"]["lower_barrier_pct"])
    horizon = int(config["primary_label"]["horizon_sessions"])
    train = row_lookup(uplift, scope_id=SPLIT_SCOPE, split="train", horizon=horizon, lower=lower)
    robust = row_lookup(uplift, scope_id=SPLIT_SCOPE, split="robustness", horizon=horizon, lower=lower)
    validation = row_lookup(uplift, scope_id=SPLIT_SCOPE, split="validation", horizon=horizon, lower=lower)
    reasons: list[str] = []
    c0_entry_pass = bool(
        entry_audit.loc[entry_audit["population_id"].eq("c0_risk_on"), "entry_parity_gate_pass"].astype(bool).all()
    )
    random_entry_pass = bool(
        entry_audit.loc[entry_audit["population_id"].eq("matched_random_risk_on"), "entry_parity_gate_pass"].astype(bool).all()
    )
    rcore_entry_rows = entry_audit.loc[entry_audit["population_id"].eq("r_core_risk_on")]
    rcore_executable_n = (
        int(rcore_entry_rows.iloc[0].get("executable_entry_n", gates["min_complete_executable_event_n"]))
        if not rcore_entry_rows.empty
        else 0
    )
    r_core_baseline_status = (
        "pass"
        if (not rcore_entry_rows.empty and bool(rcore_entry_rows.iloc[0]["entry_parity_gate_pass"]))
        else ("diagnostic_degraded_entry_blocked" if rcore_executable_n >= int(gates["min_complete_executable_event_n"]) else "diagnostic_unavailable")
    )
    input_gate_pass = bool(
        membership_audit["global_regime_calendar_status"].astype(str).eq("pass").all()
        and c0_entry_pass
        and random_entry_pass
        and not sampling_audit["cell_status"].astype(str).eq("blocked_empty_candidate_cell").any()
        and r_core_baseline_status != "diagnostic_unavailable"
    )
    if not input_gate_pass:
        reasons.append("input_or_baseline_gate_failed")
    if r_core_baseline_status != "pass":
        reasons.append(r_core_baseline_status)
    high_replacement_degraded = bool(sampling_audit["cell_status"].astype(str).eq("degraded_high_replacement").any())
    if high_replacement_degraded:
        reasons.append("random_high_replacement_degraded")

    def cond_rate(split: str, upper: float, column: str) -> float:
        row = row_lookup(conditional.loc[conditional["population_id"].eq("c0_risk_on")], scope_id=SPLIT_SCOPE, split=split, upper=upper)
        return float(row.get(column, np.nan)) if not row.empty else np.nan

    def cond_random(split: str, upper: float, suffix: str) -> float:
        row = row_lookup(conditional.loc[conditional["population_id"].eq("c0_risk_on")], scope_id=SPLIT_SCOPE, split=split, upper=upper)
        return float(row.get(f"random_upper_touch_rate_given_no_fast_fail_{suffix}", np.nan)) if not row.empty else np.nan

    train_upper10 = cond_rate("train", 0.10, "upper_touch_rate_given_no_fast_fail")
    train_upper15 = cond_rate("train", 0.15, "upper_touch_rate_given_no_fast_fail")
    robust_upper10 = cond_rate("robustness", 0.10, "upper_touch_rate_given_no_fast_fail")
    robust_upper15 = cond_rate("robustness", 0.15, "upper_touch_rate_given_no_fast_fail")
    val_upper10 = cond_rate("validation", 0.10, "upper_touch_rate_given_no_fast_fail")
    train_cond_pass = bool(
        (pd.notna(train_upper10) and train_upper10 >= cond_random("train", 0.10, "p50"))
        or (pd.notna(train_upper15) and train_upper15 >= cond_random("train", 0.15, "p50"))
    )
    robust_cond_pass = bool(
        (pd.notna(robust_upper10) and robust_upper10 >= cond_random("robustness", 0.10, "p05"))
        or (pd.notna(robust_upper15) and robust_upper15 >= cond_random("robustness", 0.15, "p05"))
    )
    train_pass = bool(
        train.get("c0_complete_executable_event_n", 0) >= int(gates["min_complete_executable_event_n"])
        and train.get("fast_fail_abs_delta_vs_random_p50", np.nan) <= float(gates["train_fast_fail_delta_vs_random_p50"])
        and train.get("fast_fail_abs_delta_vs_r_core", np.nan) <= float(gates["train_fast_fail_delta_vs_r_core"])
        and (1.0 - train.get("c0_fast_fail_rate", np.nan)) >= float(gates["min_no_fast_fail_rate"])
    )
    robust_pass = bool(
        robust.get("fast_fail_abs_delta_vs_random_p50", np.nan) <= float(gates["robustness_fast_fail_delta_vs_random_p50"])
        and robust.get("fast_fail_abs_delta_vs_r_core", np.nan) <= float(gates["robustness_fast_fail_delta_vs_r_core"])
        and (1.0 - robust.get("c0_fast_fail_rate", np.nan)) >= float(gates["min_no_fast_fail_rate"])
    )
    validation_conflict = bool(
        validation.get("c0_fast_fail_rate", -np.inf) > validation.get("random_fast_fail_rate_p95", np.inf)
        and pd.notna(val_upper10)
        and val_upper10 < cond_random("validation", 0.10, "p05")
    )
    if validation_conflict:
        reasons.append("validation_random_p95_conflict")
    if not train_pass:
        reasons.append("train_fast_fail_gate_failed")
    if not robust_pass:
        reasons.append("robustness_fast_fail_gate_failed")
    if not train_cond_pass or not robust_cond_pass:
        reasons.append("conditional_continuation_gate_failed")
    retention_ok = bool((1.0 - train.get("c0_fast_fail_rate", np.nan)) >= float(gates["min_no_fast_fail_rate"]))
    if not input_gate_pass:
        decision_state = "12A6b_blocked_input_or_baseline_failure"
    elif train_pass and robust_pass and train_cond_pass and robust_cond_pass and not validation_conflict and not high_replacement_degraded:
        decision_state = "12A6b_c0_fast_fail_survival_uplift_supported"
    elif train_pass and robust_pass and train_cond_pass and robust_cond_pass and high_replacement_degraded:
        decision_state = "12A6b_c0_fast_fail_survival_uplift_partial"
    elif retention_ok:
        decision_state = "12A6b_c0_fast_fail_survival_uplift_partial"
    else:
        decision_state = "12A6b_no_c0_fast_fail_survival_uplift"

    next_allowed = {
        "12A6b_c0_fast_fail_survival_uplift_supported": "requirement_12a7_c0_fast_fail_survival_meta_label_feasibility.md",
        "12A6b_c0_fast_fail_survival_uplift_partial": "requirement_12a6c_fast_fail_scope_or_threshold_revision.md",
        "12A6b_no_c0_fast_fail_survival_uplift": "stop_fast_fail_survival_meta_label_training",
        "12A6b_blocked_input_or_baseline_failure": "fix_input_or_baseline_failure_then_rerun_12A6b",
    }[decision_state]
    row = {
        "decision_state": decision_state,
        "primary_label_id": PRIMARY_LABEL_ID,
        "primary_horizon_sessions": horizon,
        "primary_lower_barrier_pct": lower,
        "c0_train_fast_fail_rate": train.get("c0_fast_fail_rate", np.nan),
        "random_train_fast_fail_rate_p50": train.get("random_fast_fail_rate_p50", np.nan),
        "r_core_train_fast_fail_rate": train.get("r_core_fast_fail_rate", np.nan),
        "c0_robustness_fast_fail_rate": robust.get("c0_fast_fail_rate", np.nan),
        "random_robustness_fast_fail_rate_p50": robust.get("random_fast_fail_rate_p50", np.nan),
        "r_core_robustness_fast_fail_rate": robust.get("r_core_fast_fail_rate", np.nan),
        "c0_validation_fast_fail_rate": validation.get("c0_fast_fail_rate", np.nan),
        "random_validation_fast_fail_rate_p50": validation.get("random_fast_fail_rate_p50", np.nan),
        "r_core_validation_fast_fail_rate": validation.get("r_core_fast_fail_rate", np.nan),
        "c0_train_no_fast_fail_rate": 1.0 - train.get("c0_fast_fail_rate", np.nan),
        "c0_robustness_no_fast_fail_rate": 1.0 - robust.get("c0_fast_fail_rate", np.nan),
        "upper10_given_no_fast_fail_train": train_upper10,
        "upper15_given_no_fast_fail_train": train_upper15,
        "random_upper10_given_no_fast_fail_train_p50": cond_random("train", 0.10, "p50"),
        "random_upper15_given_no_fast_fail_train_p50": cond_random("train", 0.15, "p50"),
        "upper10_given_no_fast_fail_robustness": robust_upper10,
        "upper15_given_no_fast_fail_robustness": robust_upper15,
        "random_upper10_given_no_fast_fail_robustness_p05": cond_random("robustness", 0.10, "p05"),
        "random_upper15_given_no_fast_fail_robustness_p05": cond_random("robustness", 0.15, "p05"),
        "gate_failure_reasons": ";".join(dict.fromkeys(reasons)),
        "next_allowed_requirement": next_allowed,
        "input_gate_pass": input_gate_pass,
        "r_core_baseline_status": r_core_baseline_status,
        "random_high_replacement_degraded": high_replacement_degraded,
        "validation_conflict": validation_conflict,
    }
    return pd.DataFrame([row])


def build_report(decision: pd.DataFrame, uplift: pd.DataFrame, conditional: pd.DataFrame, sampling_audit: pd.DataFrame) -> str:
    d = decision.iloc[0]

    def ff_line(split: str) -> str:
        row = row_lookup(uplift, scope_id=SPLIT_SCOPE, split=split, horizon=int(d["primary_horizon_sessions"]), lower=float(d["primary_lower_barrier_pct"]))
        if row.empty:
            return f"- {split}: not available"
        return (
            f"- {split}: C0 fast-fail={row['c0_fast_fail_rate']:.4f}, "
            f"random p50={row['random_fast_fail_rate_p50']:.4f}, R-core={row['r_core_fast_fail_rate']:.4f}, "
            f"delta_random={row['fast_fail_abs_delta_vs_random_p50']:.4f}, complete_n={int(row['c0_complete_executable_event_n'])}"
        )

    board_rows = uplift.loc[
        uplift["slice_type"].eq("board")
        & uplift["horizon_sessions"].eq(int(d["primary_horizon_sessions"]))
        & uplift["lower_barrier_pct"].eq(float(d["primary_lower_barrier_pct"]))
    ].sort_values("board_bucket")
    board_lines = [
        f"- {row.board_bucket}: C0={row.c0_fast_fail_rate:.4f}, random_p50={row.random_fast_fail_rate_p50:.4f}, R-core={row.r_core_fast_fail_rate:.4f}"
        for row in board_rows.itertuples(index=False)
    ]
    cond_rows = conditional.loc[
        conditional["population_id"].eq("c0_risk_on")
        & conditional["scope_id"].eq(SPLIT_SCOPE)
        & conditional["split"].isin(["train", "validation", "robustness"])
        & conditional["upper_barrier_pct"].isin([0.10, 0.15, 0.20])
    ].sort_values(["split", "upper_barrier_pct"])
    cond_lines = [
        f"- {row.split} U={row.upper_barrier_pct:.2f}: C0={row.upper_touch_rate_given_no_fast_fail:.4f}, random_p50={row.random_upper_touch_rate_given_no_fast_fail_p50:.4f}, no_fast_n={int(row.no_fast_fail_n)}"
        for row in cond_rows.itertuples(index=False)
    ]
    high_repl = sampling_audit.loc[sampling_audit["cell_status"].astype(str).eq("degraded_high_replacement")]
    high_repl_text = f"{len(high_repl)} degraded seed-cell rows" if not high_repl.empty else "no degraded high-replacement cells after fallback"
    return f"""
# 12A6b C0 Risk-on Fast-fail Survival Uplift Audit Report

## 结论

- decision: `{d['decision_state']}`
- primary label: `{d['primary_label_id']}`
- gate failures: `{d['gate_failure_reasons']}`
- next allowed requirement: `{d['next_allowed_requirement']}`

12A6b 将 12A6 的 `upper_first` survival 拆成两层：第一层只看 10d/20d 是否 fast-fail，第二层才在 no-fast-fail cohort 内读取后续 continuation。这里的结论仍是 path diagnostic，不是可成交收益策略。

## Fast-fail Uplift

{ff_line("train")}
{ff_line("validation")}
{ff_line("robustness")}

fast-fail rate 越低越好。`no_fast_fail_L10_H20` 的核心问题是 C0 是否比同 risk_on、同 split/board/month 的 random entry 更少快速失败，同时也不能比 R-core 更差。

## Board Stability

{chr(10).join(board_lines) if board_lines else "- not available"}

## Conditional Continuation

以下读数只在 `no_fast_fail_L10_H20` cohort 内统计，upper 不参与 survival 主标签：

{chr(10).join(cond_lines) if cond_lines else "- not available"}

## Random Baseline Quality

- random seed count: {sampling_audit['seed'].nunique() if 'seed' in sampling_audit else 0}
- replacement status: {high_repl_text}
- random sampling excludes exact C0 `(instrument, event_t0_date)` keys and preserves replacement duplicate draws through `matched_random_sampled_entries.csv.gz`.

## 解释

如果 C0 通过 fast-fail gate，但 conditional continuation 不强，说明 C0 更像风险过滤器，而不是直接收益命中器。如果 fast-fail 与 continuation 都相对 random/R-core 稳定，则 12A7 才有理由进入 fast-fail meta-label feasibility。
""".strip()


def build_manifest(
    paths: dict[str, Path],
    frames: dict[str, pd.DataFrame],
    decision: pd.DataFrame,
    config_path: Path,
    requirement_path: Path,
    config: dict[str, Any],
    audit: pd.DataFrame,
) -> dict[str, Any]:
    outputs = {
        key: {
            "path": str(path),
            "sha256": path_sha(path),
            "row_count": int(len(frames[key])) if key in frames else np.nan,
        }
        for key, path in paths.items()
        if key != "manifest" and path.exists() and path.is_file()
    }
    input_hashes = {
        str(row.artifact_id): str(row.sha256)
        for row in audit.itertuples(index=False)
        if isinstance(row.sha256, str) and row.sha256
    }
    cache_path = paths["entry_forward_path_cache"]
    return {
        "run_id": RUN_ID,
        "phase_id": "12A6b",
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_commit_if_available": git_revision(REPO_ROOT),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_sha256": path_sha(config_path),
        "requirement_path": str(requirement_path),
        "requirement_sha256": path_sha(requirement_path),
        "input_hashes": input_hashes,
        "output_hashes": {key: value["sha256"] for key, value in outputs.items()},
        "decision_state": decision.iloc[0]["decision_state"] if not decision.empty else "",
        "entry_forward_path_cache_row_n": int(len(frames.get("entry_forward_path_cache", pd.DataFrame()))),
        "entry_forward_path_cache_column_n": int(len(frames.get("entry_forward_path_cache", pd.DataFrame()).columns)),
        "entry_forward_path_cache_sha256_if_publishable": path_sha(cache_path),
        "path_cache_reuse_status": "generated_entry_level_path_key_cache",
        "outputs": outputs,
    }


def run_pipeline(config_path: Path, mode: str) -> int:
    config = load_yaml(config_path)
    paths = output_paths()
    audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], audit)
    read_ok = audit["read_status"].astype(str).eq("pass").all()
    schema_ok = ~audit["schema_status"].astype(str).str.startswith("missing_columns").any()
    if mode == "check-inputs":
        if not read_ok or not schema_ok:
            raise RuntimeError("12A6b input check failed")
        print(f"{RUN_ID}: input audit ok ({len(audit)} artifacts)")
        return 0
    if not read_ok or not schema_ok:
        raise RuntimeError("12A6b required inputs missing or schema mismatch")

    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    stock_cache = StockDailyCache(resolved["stock_daily_csv_dir"])
    regime = load_global_regime_calendar(resolved["global_regime_calendar"])
    canonical = read_table(resolved["state_change_candidate_event_canonical"])
    c0_all, c0 = load_c0_populations(canonical)
    split_intervals = build_split_intervals(c0_all)
    registry = read_table(resolved["r_core_arm_event_registry"])
    rcore, rcore_counts = load_r_core_population(registry, regime)

    c0_pairs = {(str(row.instrument), str(row.entry_date)) for row in c0.itertuples(index=False)}
    rcore_pairs = {(str(row.instrument), str(row.entry_date)) for row in rcore.itertuples(index=False)}
    entry_lookup = load_pit_membership_lookup(resolved["pit_executable_daily"], c0_pairs | rcore_pairs)
    c0 = attach_entry_status(c0, stock_cache, entry_lookup, fill_price_from_daily=False)
    rcore = attach_entry_status(rcore, stock_cache, entry_lookup, fill_price_from_daily=True)

    exact_c0_keys = {(str(row.instrument), str(row.event_date)) for row in c0.itertuples(index=False)}
    random_candidates, exact_audit = load_random_candidate_pool(
        resolved["pit_executable_daily"],
        regime,
        split_intervals,
        set(c0["board_bucket"].dropna().astype(str)),
        exact_c0_keys,
        stock_cache,
        exclude_exact_c0_keys=bool(config["random_baseline"]["exclude_exact_c0_keys"]),
    )
    random_sampled, sampling_audit = sample_random_entries(
        c0,
        random_candidates,
        exact_audit,
        base_seed=int(config["random_baseline"]["base_seed"]),
        random_seed_n=int(config["random_baseline"]["random_seed_n"]),
        replacement_threshold=float(config["random_baseline"]["replacement_rate_degraded_threshold"]),
        fallback_merge=bool(config["random_baseline"]["fallback_merge_calendar_month_to_quarter"]),
    )
    if not random_sampled.empty:
        random_sampled = random_sampled.rename(
            columns={
                "random_event_t0_date": "event_date",
                "random_trade_open_date": "entry_date",
            }
        )
        random_sampled["split"] = random_sampled["split"].astype(str)
        random_sampled["calendar_year"] = random_sampled["event_date"].map(year_text)
        random_sampled["entry_blocked"] = False
        random_sampled["entry_status"] = "ok"

    population_audit = build_population_membership_audit(
        c0_all,
        c0,
        rcore_counts,
        rcore,
        random_candidates,
        regime,
        split_intervals,
        config["expected_counts"],
    )
    entry_audit = build_entry_audit(
        {"c0_risk_on": c0, "r_core_risk_on": rcore, "matched_random_risk_on": random_sampled},
        rcore_counts,
        config["expected_counts"],
    )

    horizons = [int(x) for x in config["grid"]["horizon_sessions"]]
    lowers = [float(x) for x in config["grid"]["lower_barrier_pct"]]
    uppers = [float(x) for x in config["grid"]["upper_barrier_pct"]]

    all_events = pd.concat(
        [
            c0[["population_id", "baseline_role", "instrument", "event_date", "entry_date", "entry_pos", "entry_price", "split", "board_bucket", "primary_family_id", "calendar_month", "calendar_quarter", "calendar_year", "sample_weight", "source_row_id", "path_key", "entry_blocked", "entry_status"]],
            rcore[["population_id", "baseline_role", "instrument", "event_date", "entry_date", "entry_pos", "entry_price", "split", "board_bucket", "primary_family_id", "calendar_month", "calendar_quarter", "calendar_year", "sample_weight", "source_row_id", "path_key", "entry_blocked", "entry_status"]],
            random_sampled[["population_id", "baseline_role", "instrument", "event_date", "entry_date", "entry_pos", "entry_price", "split", "board_bucket", "primary_family_id", "calendar_month", "calendar_quarter", "calendar_year", "sample_weight", "candidate_row_id", "path_key", "entry_blocked", "entry_status"]].rename(columns={"candidate_row_id": "source_row_id"}),
        ],
        ignore_index=True,
    )
    path_cache = build_path_cache(all_events, stock_cache, horizons, lowers, uppers)
    write_df(paths["entry_forward_path_cache"], path_cache)
    all_events = all_events.merge(path_cache, on=["path_key", "instrument", "entry_date", "entry_pos", "entry_price", "entry_blocked"], how="left")

    c0_events = all_events.loc[all_events["population_id"].eq("c0_risk_on")].copy()
    rcore_events = all_events.loc[all_events["population_id"].eq("r_core_risk_on")].copy()
    random_events = all_events.loc[all_events["population_id"].astype(str).str.startswith("matched_random_risk_on_seed_")].copy()

    c0_grid = aggregate_fast_fail_grid(
        c0_events,
        population_id="c0_risk_on",
        baseline_role="c0_candidate",
        horizons=horizons,
        lowers=lowers,
        include_family=True,
        diagnostic_family=True,
    )
    rcore_grid = aggregate_fast_fail_grid(
        rcore_events,
        population_id="r_core_risk_on",
        baseline_role="r_core_benchmark",
        horizons=horizons,
        lowers=lowers,
        include_family=False,
        diagnostic_family=False,
    )
    random_seed_grids: list[pd.DataFrame] = []
    for population_id, seed_events in random_events.groupby("population_id", observed=True):
        random_seed_grids.append(
            aggregate_fast_fail_grid(
                seed_events,
                population_id=str(population_id),
                baseline_role="matched_random",
                horizons=horizons,
                lowers=lowers,
                include_family=False,
                diagnostic_family=False,
            )
        )
    random_seed_grid = pd.concat(random_seed_grids, ignore_index=True) if random_seed_grids else pd.DataFrame()
    random_quantiles = quantile_random_grid(random_seed_grid) if not random_seed_grid.empty else pd.DataFrame()
    fast_fail_grid = pd.concat([c0_grid, rcore_grid, random_seed_grid, random_quantiles], ignore_index=True)
    random_seed_distribution = random_seed_grid.copy()
    if not random_seed_distribution.empty:
        random_seed_distribution["seed"] = random_seed_distribution["population_id"].astype(str).str.extract(r"(\d+)$").astype(int)

    condition_lower = float(config["conditional_readout"]["condition_lower_barrier_pct"])
    condition_horizon = int(config["conditional_readout"]["condition_horizon_sessions"])
    upper_horizon = int(config["conditional_readout"]["upper_horizon_sessions"])
    c0_cond = aggregate_conditional(
        c0_events,
        population_id="c0_risk_on",
        baseline_role="c0_candidate",
        lowers=lowers,
        uppers=uppers,
        condition_lower=condition_lower,
        condition_horizon=condition_horizon,
        upper_horizon=upper_horizon,
        include_family=True,
        diagnostic_family=True,
    )
    rcore_cond = aggregate_conditional(
        rcore_events,
        population_id="r_core_risk_on",
        baseline_role="r_core_benchmark",
        lowers=lowers,
        uppers=uppers,
        condition_lower=condition_lower,
        condition_horizon=condition_horizon,
        upper_horizon=upper_horizon,
        include_family=False,
        diagnostic_family=False,
    )
    random_seed_cond_parts: list[pd.DataFrame] = []
    for population_id, seed_events in random_events.groupby("population_id", observed=True):
        random_seed_cond_parts.append(
            aggregate_conditional(
                seed_events,
                population_id=str(population_id),
                baseline_role="matched_random",
                lowers=lowers,
                uppers=uppers,
                condition_lower=condition_lower,
                condition_horizon=condition_horizon,
                upper_horizon=upper_horizon,
                include_family=False,
                diagnostic_family=False,
            )
        )
    random_seed_cond = pd.concat(random_seed_cond_parts, ignore_index=True) if random_seed_cond_parts else pd.DataFrame()
    random_cond_quantiles = quantile_random_conditional(random_seed_cond) if not random_seed_cond.empty else pd.DataFrame()
    conditional = pd.concat([c0_cond, rcore_cond, random_seed_cond, random_cond_quantiles], ignore_index=True)
    conditional = add_conditional_baselines(conditional)

    uplift = build_uplift(c0_grid, rcore_grid, random_quantiles)
    retention = build_retention(fast_fail_grid, condition_lower, condition_horizon)
    decision = evaluate_decision(uplift, conditional, sampling_audit, entry_audit, population_audit, config)
    report = build_report(decision, uplift, conditional, sampling_audit)

    sampled_output = random_sampled.rename(
        columns={
            "event_date": "random_event_t0_date",
            "entry_date": "random_trade_open_date",
        }
    )
    sampled_cols = [
        "seed",
        "sample_draw_id",
        "path_key",
        "split",
        "board_bucket",
        "calendar_month",
        "calendar_quarter",
        "random_event_t0_date",
        "random_trade_open_date",
        "instrument",
        "entry_pos",
        "entry_price",
        "c0_match_cell_id",
        "replacement_used_flag",
        "replacement_draw_index",
        "sample_weight",
        "exact_c0_key_excluded_flag",
        "sampling_status",
    ]
    sampled_output = sampled_output[[col for col in sampled_cols if col in sampled_output.columns]].copy()

    frames = {
        "input_artifact_audit": audit,
        "population_entry_executability_audit": entry_audit,
        "population_membership_audit": population_audit,
        "matched_random_sampling_audit": sampling_audit,
        "matched_random_sampled_entries": sampled_output,
        "fast_fail_survival_grid": fast_fail_grid,
        "fast_fail_uplift_vs_baselines": uplift,
        "conditional_continuation_readout": conditional,
        "survival_filter_retention_by_slice": retention,
        "fast_fail_decision": decision,
        "random_seed_distribution": random_seed_distribution,
        "entry_forward_path_cache": path_cache,
    }
    for key, frame in frames.items():
        if key in paths and key != "entry_forward_path_cache":
            write_df(paths[key], frame)
    write_text(paths["report"], report)
    frames["report"] = pd.DataFrame([{"report_path": str(paths["report"])}])
    requirement_path = resolved["requirement"]
    write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, requirement_path, config, audit))
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_pipeline(Path(args.config), args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

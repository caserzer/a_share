#!/usr/bin/env python
from __future__ import annotations

import argparse
import gzip
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


RUN_ID = "12A6_c0_local_survival_episode_audit"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a6_c0_local_survival_episode_audit.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
PRIMARY_FAMILY_IDS = ("B1", "B2", "B3", "B4", "B5", "B6", "B8")
SOURCE_SCOPE_ID = "12A2_C0_primary_canonical_union"
ALL_C0 = "all_c0"
REGIME_SCOPES = {
    "regime_risk_on": ("market_regime_bucket", "risk_on"),
    "regime_transition": ("market_regime_bucket", "transition"),
    "regime_risk_off": ("market_regime_bucket", "risk_off"),
}
BOARD_SCOPES = {
    "board_main_board": ("board_bucket", "main_board"),
    "board_chinext": ("board_bucket", "chinext"),
}
FAMILY_SCOPES = {f"primary_family_{family}": ("primary_family_id", family) for family in PRIMARY_FAMILY_IDS}
SCOPE_SPECS = {ALL_C0: ("all", "all")} | REGIME_SCOPES | BOARD_SCOPES | FAMILY_SCOPES
LATE_STAGE_NUMERIC_FEATURE_COLUMNS = (
    "ret_20d",
    "ret_60d",
    "distance_to_60d_high",
    "distance_to_120d_high",
    "distance_to_60d_low",
    "distance_to_120d_low",
    "trend_ma_20_60_spread",
    "volatility_20d",
    "volatility_60d",
)


EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "state_change_generation_decision": (
        "decision",
        "primary_canonical_event_n",
        "next_open_executable_gate_pass",
        "pit_feature_gate_pass",
    ),
    "state_change_candidate_event_canonical": (
        "canonical_event_id",
        "primary_family_id",
        "primary_variant_id",
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
    "state_change_candidate_event_instances": ("event_instance_id", "family_id", "instrument", "event_t0_date"),
    "state_change_canonicalization_spec": (),
    "state_change_density_audit": (),
    "manifest_12a2": (),
    "labels_yaml": (),
    "stock_daily_csv_dir": (),
    "pit_executable_daily": ("usable_trade_date", "instrument"),
    "episode_target_registry_06": (
        "episode_id",
        "instrument",
        "episode_low_date",
        "episode_high_date",
        "pre120_calendar_start_date",
        "split",
        "selection_rule",
    ),
    "pit_candidate_winner_registry_11a2": (
        "instrument",
        "event_t0_date",
        "analysis_regime_scope",
    ),
    "meta_label_event_targets_12a4": (
        "meta_event_id",
        "source_arm_id",
        "event_split",
        "instrument",
        "winner_120_label",
    ),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A6 C0 local survival episode audit.")
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
        "event_universe": TABLE_DIR / "c0_survival_event_universe.csv.gz",
        "forward_distribution": TABLE_DIR / "c0_forward_path_distribution.csv",
        "grid_frontier": TABLE_DIR / "c0_triple_barrier_grid_frontier.csv",
        "pre_success_mae": TABLE_DIR / "c0_pre_success_mae_distribution.csv",
        "time_to_hit_curve": TABLE_DIR / "c0_time_to_hit_curve.csv",
        "threshold_decision": TABLE_DIR / "c0_threshold_candidate_decision.csv",
        "bigwinner_enrichment": TABLE_DIR / "c0_bigwinner_enrichment_crosstab.csv",
        "late_stage": TABLE_DIR / "c0_late_stage_failure_diagnostics.csv",
        "entry_audit": TABLE_DIR / "c0_entry_executability_audit.csv",
        "same_bar_audit": TABLE_DIR / "c0_same_bar_conflict_audit.csv",
        "overlap_density": TABLE_DIR / "c0_overlap_density_audit.csv",
        "path_matrix": LOCAL_CACHE_DIR / "c0_survival_event_path_matrix.parquet",
        "report": REPORT_DIR / "c0_local_survival_episode_audit_report.md",
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
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d")


def safe_rate(num: int | float, den: int | float) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return np.nan
    return float(num) / float(den)


def membership_row_status(row: pd.Series) -> str:
    if "is_listed" in row.index and not boolish(row.get("is_listed")):
        return "not_listed"
    if "is_st" in row.index and boolish(row.get("is_st")):
        return "st"
    if "is_suspended" in row.index and boolish(row.get("is_suspended")):
        return "suspended"
    return "pass"


def load_pit_membership_lookup(
    path: Path,
    instruments: set[str],
    usable_dates: set[str],
    *,
    chunksize: int = 500_000,
) -> dict[tuple[str, str], str]:
    """Stream the large PIT membership file and retain only entry-date rows."""
    if not path.exists():
        return {}
    needed = {"usable_trade_date", "instrument", "is_listed", "is_st", "is_suspended"}
    header = pd.read_csv(path, nrows=0)
    usecols = [col for col in header.columns if col in needed]
    if not {"usable_trade_date", "instrument"}.issubset(usecols):
        return {}
    wanted_instruments = {str(x) for x in instruments if str(x)}
    wanted_dates = {date_text(x) for x in usable_dates if date_text(x)}
    lookup: dict[tuple[str, str], str] = {}
    if not wanted_instruments or not wanted_dates:
        return lookup
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize, low_memory=False):
        chunk["instrument"] = chunk["instrument"].astype(str)
        chunk["usable_trade_date"] = chunk["usable_trade_date"].map(date_text)
        filtered = chunk.loc[
            chunk["instrument"].isin(wanted_instruments) & chunk["usable_trade_date"].isin(wanted_dates)
        ]
        if filtered.empty:
            continue
        for row in filtered.itertuples(index=False):
            values = row._asdict()
            key = (str(values["instrument"]), str(values["usable_trade_date"]))
            status = membership_row_status(pd.Series(values))
            previous = lookup.get(key)
            if previous is None or previous != "pass":
                lookup[key] = "pass" if status == "pass" or previous == "pass" else status
    return lookup


def q_value(values: pd.Series, q: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return np.nan
    return float(clean.quantile(q))


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
        if exists and path.is_file() and (path.suffix in {".csv", ".gz", ".parquet", ".json", ".yaml"}):
            try:
                suffixes = "".join(path.suffixes)
                if suffixes.endswith(".parquet"):
                    sample = pd.read_parquet(path)
                    row_count = int(sample.shape[0])
                    column_count = int(sample.shape[1])
                    columns = set(sample.columns)
                elif path.suffix in {".json", ".yaml"}:
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
            except Exception as exc:  # pragma: no cover - defensive audit path
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

    def get(self, instrument: str) -> pd.DataFrame | None:
        instrument = str(instrument)
        if instrument in self._cache:
            return self._cache[instrument]
        path = self.directory / f"{instrument}.csv"
        if not path.exists():
            self._cache[instrument] = None
            return None
        daily = pd.read_csv(path, low_memory=False)
        daily["date"] = pd.to_datetime(daily["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        daily = daily.sort_values("date", kind="stable").reset_index(drop=True)
        for col in ("open", "high", "low", "close", "volume", "money", "turnover_rate"):
            daily[col] = pd.to_numeric(daily.get(col), errors="coerce")
        self._cache[instrument] = daily
        return daily


def normalize_primary_events(canonical: pd.DataFrame) -> pd.DataFrame:
    raw = canonical.copy()
    non_exec = bool_series(raw["non_executable_next_open"])
    mask = (
        raw["candidate_generation_status"].astype(str).eq("supported_canonical_event")
        & (~non_exec)
        & raw["event_t0_pit_status"].astype(str).eq("pass")
        & raw["trade_open_pit_status"].astype(str).eq("pass")
        & raw["trade_open_price"].notna()
    )
    out = raw.loc[mask].copy().reset_index(drop=True)
    out.insert(0, "event_ordinal", np.arange(len(out), dtype=np.int32))
    out.insert(1, "survival_event_id", "C0S_" + out["canonical_event_id"].astype(str))
    out["event_t0_date"] = out["event_t0_date"].map(date_text)
    out["trade_open_date"] = out["trade_open_date"].map(date_text)
    out["event_t0_pos"] = numeric(out["event_t0_pos"])
    out["trade_open_pos"] = numeric(out["trade_open_pos"])
    out["trade_open_price"] = numeric(out["trade_open_price"])
    out["primary_family_id"] = out["primary_family_id"].astype(str)
    out["primary_variant_id"] = out["primary_variant_id"].astype(str)
    out["triggered_family_variants"] = out["triggered_family_variants"].fillna("").astype(str)
    out["triggered_family_count"] = numeric(out["triggered_family_count"]).fillna(1).astype(int)
    out["source_scope_id"] = SOURCE_SCOPE_ID
    out["entry_status"] = "pending_entry_recompute"
    return out


def check_12a2_gate(decision: pd.DataFrame, event_n: int) -> tuple[bool, str]:
    if decision.empty:
        return False, "missing_12A2_decision"
    row = decision.iloc[0]
    checks = {
        "decision": str(row.get("decision", "")) == "12A2_state_change_candidate_generation_supported",
        "primary_canonical_event_n": int(row.get("primary_canonical_event_n", -1)) == event_n,
        "next_open_executable_gate_pass": boolish(row.get("next_open_executable_gate_pass", False)),
        "pit_feature_gate_pass": boolish(row.get("pit_feature_gate_pass", False)),
    }
    failed = [key for key, ok in checks.items() if not ok]
    return not failed, "pass" if not failed else ";".join(failed)


def attach_entry_audit(
    universe: pd.DataFrame,
    stock_cache: StockDailyCache,
    max_horizon: int,
    pit_membership_lookup: dict[tuple[str, str], str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = universe.copy()
    entry_statuses: list[str] = []
    membership_statuses: list[str] = []
    max_complete: list[int] = []
    price_missing = 0
    date_mismatch = 0
    pos_missing = 0
    price_missing_value = 0
    pit_membership_fail = 0
    pit_membership_missing = 0
    pit_membership_not_executable = 0
    for row in out.itertuples(index=False):
        daily = stock_cache.get(row.instrument)
        status = "ok"
        complete_sessions = -1
        membership_status = pit_membership_lookup.get((str(row.instrument), date_text(row.trade_open_date)), "missing")
        if membership_status != "pass":
            pit_membership_fail += 1
            if membership_status == "missing":
                pit_membership_missing += 1
            else:
                pit_membership_not_executable += 1
        if daily is None or daily.empty:
            status = "missing_price_file"
            price_missing += 1
        elif pd.isna(row.trade_open_pos) or pd.isna(row.trade_open_price):
            status = "missing_trade_open_pos_or_price"
            pos_missing += 1
        else:
            pos = int(row.trade_open_pos)
            if pos < 0 or pos >= len(daily):
                status = "trade_open_pos_out_of_range"
                pos_missing += 1
            elif str(daily.loc[pos, "date"]) != str(row.trade_open_date):
                status = "trade_open_date_pos_mismatch"
                date_mismatch += 1
            elif pd.isna(daily.loc[pos, "open"]) or pd.isna(row.trade_open_price):
                status = "missing_trade_open_price"
                price_missing_value += 1
            else:
                complete_sessions = int(len(daily) - 1 - pos)
                if membership_status != "pass":
                    status = "pit_membership_missing_or_not_executable"
                    complete_sessions = -1
        entry_statuses.append(status)
        membership_statuses.append(membership_status)
        max_complete.append(complete_sessions)
    out["entry_status"] = entry_statuses
    out["trade_open_pit_membership_status"] = membership_statuses
    out["max_complete_horizon_sessions"] = max_complete
    entry_blocked = out["entry_status"].ne("ok")
    audit = pd.DataFrame(
        [
            {
                "entry_status": "all",
                "event_n": int(len(out)),
                "missing_trade_open_date_n": int(out["trade_open_date"].eq("").sum()),
                "missing_trade_open_price_n": int(out["trade_open_price"].isna().sum() + price_missing_value),
                "non_executable_next_open_true_n": 0,
                "trade_open_pit_fail_n": int(out["trade_open_pit_status"].astype(str).ne("pass").sum()),
                "pit_membership_missing_n": int(pit_membership_fail),
                "pit_membership_file_missing_n": int(pit_membership_missing),
                "pit_membership_not_executable_n": int(pit_membership_not_executable),
                "entry_blocked_n": int(entry_blocked.sum()),
                "entry_parity_gate_pass": bool(not entry_blocked.any()),
                "block_reason": "" if not entry_blocked.any() else "entry_recompute_failed",
            },
            {
                "entry_status": "missing_price_file",
                "event_n": int(price_missing),
                "missing_trade_open_date_n": 0,
                "missing_trade_open_price_n": 0,
                "non_executable_next_open_true_n": 0,
                "trade_open_pit_fail_n": 0,
                "pit_membership_missing_n": 0,
                "pit_membership_file_missing_n": 0,
                "pit_membership_not_executable_n": 0,
                "entry_blocked_n": int(price_missing),
                "entry_parity_gate_pass": bool(price_missing == 0),
                "block_reason": "price data missing for required instruments" if price_missing else "",
            },
            {
                "entry_status": "trade_open_position_mismatch",
                "event_n": int(date_mismatch + pos_missing),
                "missing_trade_open_date_n": 0,
                "missing_trade_open_price_n": 0,
                "non_executable_next_open_true_n": 0,
                "trade_open_pit_fail_n": 0,
                "pit_membership_missing_n": 0,
                "pit_membership_file_missing_n": 0,
                "pit_membership_not_executable_n": 0,
                "entry_blocked_n": int(date_mismatch + pos_missing),
                "entry_parity_gate_pass": bool(date_mismatch + pos_missing == 0),
                "block_reason": "trade_open position/date mismatch" if date_mismatch + pos_missing else "",
            },
            {
                "entry_status": "missing_trade_open_price",
                "event_n": int(price_missing_value),
                "missing_trade_open_date_n": 0,
                "missing_trade_open_price_n": int(price_missing_value),
                "non_executable_next_open_true_n": 0,
                "trade_open_pit_fail_n": 0,
                "pit_membership_missing_n": 0,
                "pit_membership_file_missing_n": 0,
                "pit_membership_not_executable_n": 0,
                "entry_blocked_n": int(price_missing_value),
                "entry_parity_gate_pass": bool(price_missing_value == 0),
                "block_reason": "trade_open price missing in qfq daily file" if price_missing_value else "",
            },
            {
                "entry_status": "pit_membership_missing_or_not_executable",
                "event_n": int(pit_membership_fail),
                "missing_trade_open_date_n": 0,
                "missing_trade_open_price_n": 0,
                "non_executable_next_open_true_n": 0,
                "trade_open_pit_fail_n": 0,
                "pit_membership_missing_n": int(pit_membership_fail),
                "pit_membership_file_missing_n": int(pit_membership_missing),
                "pit_membership_not_executable_n": int(pit_membership_not_executable),
                "entry_blocked_n": int(out["entry_status"].eq("pit_membership_missing_or_not_executable").sum()),
                "entry_parity_gate_pass": bool(pit_membership_fail == 0),
                "block_reason": "trade_open PIT membership missing or not executable" if pit_membership_fail else "",
            },
        ]
    )
    return out, audit


def classify_first_hit(
    upper_day: int | None,
    lower_day: int | None,
    *,
    horizon_complete: bool = True,
    entry_blocked: bool = False,
) -> tuple[str, bool]:
    if entry_blocked:
        return "entry_blocked", False
    if not horizon_complete:
        return "censored", False
    if lower_day is not None and (upper_day is None or lower_day <= upper_day):
        return "lower_first", bool(upper_day is not None and lower_day == upper_day)
    if upper_day is not None:
        return "upper_first", False
    return "neutral", False


def compute_path_matrices(
    universe: pd.DataFrame,
    stock_cache: StockDailyCache,
    horizons: list[int],
    uppers: list[float],
    lowers: list[float],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path: dict[str, list[Any]] = {
        "event_ordinal": [],
        "horizon_sessions": [],
        "upper_barrier_pct": [],
        "lower_barrier_pct": [],
        "first_hit_status": [],
        "same_bar_conflict_flag": [],
        "time_to_upper_sessions": [],
        "time_to_lower_sessions": [],
        "upper_touch_possible_flag": [],
        "true_survivor_killed_by_lower_flag": [],
        "exit_return_proxy": [],
        "r_multiple_proxy": [],
        "mfe_h": [],
        "mae_h": [],
        "close_return_h": [],
        "horizon_complete": [],
        "entry_blocked": [],
        "pre_success_mae": [],
    }
    event_horizon: dict[str, list[Any]] = {
        "event_ordinal": [],
        "horizon_sessions": [],
        "mfe_h": [],
        "mae_h": [],
        "close_return_h": [],
        "horizon_complete": [],
        "entry_blocked": [],
    }
    upper_touch: dict[str, list[Any]] = {
        "event_ordinal": [],
        "horizon_sessions": [],
        "upper_barrier_pct": [],
        "upper_touch_possible_flag": [],
        "time_to_upper_sessions": [],
        "pre_success_mae": [],
        "horizon_complete": [],
        "entry_blocked": [],
    }

    for row in universe.itertuples(index=False):
        event_ordinal = int(row.event_ordinal)
        entry_blocked = row.entry_status != "ok"
        daily = stock_cache.get(row.instrument) if not entry_blocked else None
        entry_pos = int(row.trade_open_pos) if not entry_blocked else -1
        entry_price = float(row.trade_open_price) if not entry_blocked else np.nan
        high = daily["high"].to_numpy(dtype=float) if daily is not None else np.array([], dtype=float)
        low = daily["low"].to_numpy(dtype=float) if daily is not None else np.array([], dtype=float)
        close = daily["close"].to_numpy(dtype=float) if daily is not None else np.array([], dtype=float)
        for horizon in horizons:
            complete = (not entry_blocked) and (entry_pos + horizon < len(close))
            if complete:
                end_pos = entry_pos + horizon
                h_slice = high[entry_pos : end_pos + 1]
                l_slice = low[entry_pos : end_pos + 1]
                c_end = close[end_pos]
                mfe = float(np.nanmax(h_slice) / entry_price - 1.0)
                mae = float(np.nanmin(l_slice) / entry_price - 1.0)
                close_return = float(c_end / entry_price - 1.0)
                upper_days: dict[float, int | None] = {}
                pre_mae_by_upper: dict[float, float] = {}
                for upper in uppers:
                    hits = np.flatnonzero(h_slice >= entry_price * (1.0 + upper))
                    if len(hits):
                        hit = int(hits[0])
                        upper_days[upper] = hit
                        pre_mae_by_upper[upper] = float(np.nanmin(l_slice[: hit + 1]) / entry_price - 1.0)
                    else:
                        upper_days[upper] = None
                        pre_mae_by_upper[upper] = np.nan
                lower_days: dict[float, int | None] = {}
                for lower in lowers:
                    hits = np.flatnonzero(l_slice <= entry_price * (1.0 + lower))
                    lower_days[lower] = int(hits[0]) if len(hits) else None
            else:
                mfe = np.nan
                mae = np.nan
                close_return = np.nan
                upper_days = {upper: None for upper in uppers}
                lower_days = {lower: None for lower in lowers}
                pre_mae_by_upper = {upper: np.nan for upper in uppers}

            event_horizon["event_ordinal"].append(event_ordinal)
            event_horizon["horizon_sessions"].append(horizon)
            event_horizon["mfe_h"].append(mfe)
            event_horizon["mae_h"].append(mae)
            event_horizon["close_return_h"].append(close_return)
            event_horizon["horizon_complete"].append(bool(complete))
            event_horizon["entry_blocked"].append(bool(entry_blocked))

            for upper in uppers:
                upper_day = upper_days[upper]
                upper_touch["event_ordinal"].append(event_ordinal)
                upper_touch["horizon_sessions"].append(horizon)
                upper_touch["upper_barrier_pct"].append(upper)
                upper_touch["upper_touch_possible_flag"].append(upper_day is not None)
                upper_touch["time_to_upper_sessions"].append(np.nan if upper_day is None else upper_day)
                upper_touch["pre_success_mae"].append(pre_mae_by_upper[upper])
                upper_touch["horizon_complete"].append(bool(complete))
                upper_touch["entry_blocked"].append(bool(entry_blocked))
                for lower in lowers:
                    lower_day = lower_days[lower]
                    status, same_bar = classify_first_hit(upper_day, lower_day, horizon_complete=complete, entry_blocked=entry_blocked)
                    if status == "upper_first":
                        exit_return = upper
                    elif status == "lower_first":
                        exit_return = lower
                    elif status == "neutral":
                        exit_return = close_return
                    else:
                        exit_return = np.nan
                    killed = upper_day is not None and lower_day is not None and lower_day <= upper_day
                    path["event_ordinal"].append(event_ordinal)
                    path["horizon_sessions"].append(horizon)
                    path["upper_barrier_pct"].append(upper)
                    path["lower_barrier_pct"].append(lower)
                    path["first_hit_status"].append(status)
                    path["same_bar_conflict_flag"].append(bool(same_bar))
                    path["time_to_upper_sessions"].append(np.nan if upper_day is None else upper_day)
                    path["time_to_lower_sessions"].append(np.nan if lower_day is None else lower_day)
                    path["upper_touch_possible_flag"].append(bool(upper_day is not None))
                    path["true_survivor_killed_by_lower_flag"].append(bool(killed))
                    path["exit_return_proxy"].append(exit_return)
                    path["r_multiple_proxy"].append(exit_return / abs(lower) if pd.notna(exit_return) else np.nan)
                    path["mfe_h"].append(mfe)
                    path["mae_h"].append(mae)
                    path["close_return_h"].append(close_return)
                    path["horizon_complete"].append(bool(complete))
                    path["entry_blocked"].append(bool(entry_blocked))
                    path["pre_success_mae"].append(pre_mae_by_upper[upper])

    path_df = pd.DataFrame(path)
    event_horizon_df = pd.DataFrame(event_horizon)
    upper_touch_df = pd.DataFrame(upper_touch)
    path_df["first_hit_status"] = path_df["first_hit_status"].astype("category")
    for frame in (path_df, event_horizon_df, upper_touch_df):
        frame["horizon_sessions"] = frame["horizon_sessions"].astype(np.int16)
        frame["event_ordinal"] = frame["event_ordinal"].astype(np.int32)
    return path_df, event_horizon_df, upper_touch_df


def add_event_attrs(frame: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    idx = out["event_ordinal"].to_numpy(dtype=int)
    for col in ("event_split", "board_bucket", "market_regime_bucket", "primary_family_id", "instrument", "canonical_event_id"):
        out[col] = universe[col].to_numpy()[idx]
    return out


def scope_event_mask(universe: pd.DataFrame, scope_id: str, split: str) -> np.ndarray:
    if scope_id == ALL_C0:
        mask = np.ones(len(universe), dtype=bool)
    else:
        column, value = SCOPE_SPECS[scope_id]
        mask = universe[column].astype(str).eq(value).to_numpy()
    if split != "all":
        mask &= universe["event_split"].astype(str).eq(split).to_numpy()
    return mask


def scope_dimensions(scope_id: str) -> tuple[str, str, str]:
    if scope_id in REGIME_SCOPES:
        return "all", REGIME_SCOPES[scope_id][1], "all"
    if scope_id in BOARD_SCOPES:
        return BOARD_SCOPES[scope_id][1], "all", "all"
    if scope_id in FAMILY_SCOPES:
        return "all", "all", FAMILY_SCOPES[scope_id][1]
    return "all", "all", "all"


def prepare_path_flags(path_df: pd.DataFrame) -> pd.DataFrame:
    out = path_df.copy()
    out["complete_executable"] = (~out["entry_blocked"]) & out["horizon_complete"]
    out["censored_flag"] = (~out["entry_blocked"]) & (~out["horizon_complete"])
    out["upper_first_flag"] = out["first_hit_status"].astype(str).eq("upper_first")
    out["lower_first_flag"] = out["first_hit_status"].astype(str).eq("lower_first")
    out["neutral_flag"] = out["first_hit_status"].astype(str).eq("neutral")
    out["time_to_upper_for_median"] = out["time_to_upper_sessions"].where(out["upper_first_flag"])
    out["time_to_lower_for_median"] = out["time_to_lower_sessions"].where(out["lower_first_flag"])
    out["r_multiple_complete"] = out["r_multiple_proxy"].where(out["complete_executable"])
    out["exit_return_complete"] = out["exit_return_proxy"].where(out["complete_executable"])
    return out


def aggregate_grid_subset(subset: pd.DataFrame, scope_id: str, split: str) -> pd.DataFrame:
    if subset.empty:
        return pd.DataFrame()
    grouped = subset.groupby(["upper_barrier_pct", "lower_barrier_pct", "horizon_sessions"], observed=True)
    out = grouped.agg(
        event_n=("event_ordinal", "nunique"),
        complete_executable_event_n=("complete_executable", "sum"),
        entry_blocked_n=("entry_blocked", "sum"),
        censored_n=("censored_flag", "sum"),
        same_bar_conflict_n=("same_bar_conflict_flag", "sum"),
        upper_first_n=("upper_first_flag", "sum"),
        lower_first_n=("lower_first_flag", "sum"),
        neutral_n=("neutral_flag", "sum"),
        median_time_to_upper_sessions=("time_to_upper_for_median", "median"),
        median_time_to_lower_sessions=("time_to_lower_for_median", "median"),
        true_survivor_killed_by_lower_n=("true_survivor_killed_by_lower_flag", "sum"),
        upper_touch_possible_n=("upper_touch_possible_flag", "sum"),
        expected_r_multiple_proxy=("r_multiple_complete", "mean"),
        median_exit_return_proxy=("exit_return_complete", "median"),
    ).reset_index()
    den = out["complete_executable_event_n"].replace(0, np.nan)
    out["same_bar_conflict_rate"] = out["same_bar_conflict_n"] / den
    out["upper_first_rate"] = out["upper_first_n"] / den
    out["lower_first_rate"] = out["lower_first_n"] / den
    out["neutral_rate"] = out["neutral_n"] / den
    out["true_survivor_killed_by_lower_rate"] = (
        out["true_survivor_killed_by_lower_n"] / out["upper_touch_possible_n"].replace(0, np.nan)
    )
    median_time = pd.to_numeric(out["median_time_to_upper_sessions"], errors="coerce")
    median_time = median_time.where(median_time.notna(), out["horizon_sessions"].astype(float))
    out["time_penalized_expected_r_proxy"] = out["expected_r_multiple_proxy"] / np.sqrt(median_time + 1.0)
    board, regime, family = scope_dimensions(scope_id)
    out.insert(0, "scope_id", scope_id)
    out.insert(1, "split", split)
    out.insert(2, "board_bucket", board)
    out.insert(3, "market_regime_bucket", regime)
    out.insert(4, "primary_family_id", family)
    out = out.drop(columns=["true_survivor_killed_by_lower_n", "upper_touch_possible_n"])
    return out


def assign_selection_flags(frontier: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    out = frontier.copy()
    eligible = (
        out["scope_id"].eq(ALL_C0)
        & out["split"].eq("train")
        & (out["complete_executable_event_n"] >= int(thresholds["train_min_complete_executable_event_n"]))
        & (out["upper_first_rate"] >= float(thresholds["train_min_upper_first_rate"]))
        & (out["lower_first_rate"] <= float(thresholds["train_max_lower_first_rate"]))
        & (out["true_survivor_killed_by_lower_rate"] <= float(thresholds["train_max_true_survivor_killed_by_lower_rate"]))
        & (out["expected_r_multiple_proxy"] >= float(thresholds["train_min_expected_r_multiple_proxy"]))
        & (
            out["median_time_to_upper_sessions"]
            <= out["horizon_sessions"] * float(thresholds["train_max_median_time_to_upper_horizon_fraction"])
        )
    )
    out["selection_eligible_flag"] = eligible.fillna(False)
    out["diagnostic_only_flag"] = ~out["selection_eligible_flag"]
    out["label_status"] = np.where(out["complete_executable_event_n"] > 0, "ok", "no_complete_executable_events")
    return out


def build_grid_frontier(path_df: pd.DataFrame, universe: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    flagged = prepare_path_flags(path_df)
    rows: list[pd.DataFrame] = []
    event_ord = flagged["event_ordinal"].to_numpy(dtype=int)
    for scope_id in SCOPE_SPECS:
        for split in SPLITS:
            event_mask = scope_event_mask(universe, scope_id, split)
            subset = flagged.loc[event_mask[event_ord]]
            agg = aggregate_grid_subset(subset, scope_id, split)
            if not agg.empty:
                rows.append(agg)
    frontier = pd.concat(rows, ignore_index=True)
    return assign_selection_flags(frontier, thresholds)


def sort_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        [
            "upper_first_rate",
            "median_time_to_upper_sessions",
            "lower_first_rate",
            "true_survivor_killed_by_lower_rate",
            "upper_barrier_pct",
            "time_penalized_expected_r_proxy",
            "expected_r_multiple_proxy",
            "horizon_sessions",
        ],
        ascending=[False, True, True, True, False, False, False, True],
        kind="mergesort",
    )


def select_primary_candidate(frontier: pd.DataFrame) -> tuple[pd.Series | None, str]:
    eligible = frontier.loc[frontier["selection_eligible_flag"].astype(bool)].copy()
    if eligible.empty:
        return None, "no_viable_survival_threshold"
    return sort_candidates(eligible).iloc[0], "pass"


def select_strong_candidate(frontier: pd.DataFrame) -> tuple[pd.Series | None, str]:
    eligible = frontier.loc[frontier["selection_eligible_flag"].astype(bool) & (frontier["upper_barrier_pct"] >= 0.30)].copy()
    if eligible.empty:
        return None, "no_viable_strong_threshold"
    return sort_candidates(eligible).iloc[0], "pass"


def build_forward_distribution(event_horizon_df: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    frame = event_horizon_df.copy()
    frame["complete_executable"] = (~frame["entry_blocked"]) & frame["horizon_complete"]
    rows: list[dict[str, Any]] = []
    ords = frame["event_ordinal"].to_numpy(dtype=int)
    for scope_id in SCOPE_SPECS:
        for split in SPLITS:
            event_mask = scope_event_mask(universe, scope_id, split)
            subset = frame.loc[event_mask[ords]]
            if subset.empty:
                continue
            for horizon, hframe in subset.groupby("horizon_sessions", observed=True):
                complete = hframe.loc[hframe["complete_executable"]]
                rows.append(
                    {
                        "scope_id": scope_id,
                        "split": split,
                        "horizon_sessions": int(horizon),
                        "event_n": int(hframe["event_ordinal"].nunique()),
                        "complete_executable_event_n": int(complete["event_ordinal"].nunique()),
                        "mfe_p25": q_value(complete["mfe_h"], 0.25),
                        "mfe_p50": q_value(complete["mfe_h"], 0.50),
                        "mfe_p75": q_value(complete["mfe_h"], 0.75),
                        "mfe_p90": q_value(complete["mfe_h"], 0.90),
                        "mfe_p95": q_value(complete["mfe_h"], 0.95),
                        "mae_p25": q_value(complete["mae_h"], 0.25),
                        "mae_p50": q_value(complete["mae_h"], 0.50),
                        "mae_p75": q_value(complete["mae_h"], 0.75),
                        "mae_p90": q_value(complete["mae_h"], 0.90),
                        "mae_p95": q_value(complete["mae_h"], 0.95),
                        "close_return_p25": q_value(complete["close_return_h"], 0.25),
                        "close_return_p50": q_value(complete["close_return_h"], 0.50),
                        "close_return_p75": q_value(complete["close_return_h"], 0.75),
                        "close_return_p90": q_value(complete["close_return_h"], 0.90),
                        "close_return_p95": q_value(complete["close_return_h"], 0.95),
                    }
                )
    return pd.DataFrame(rows)


def build_pre_success_mae_distribution(
    upper_touch_df: pd.DataFrame,
    path_df: pd.DataFrame,
    universe: pd.DataFrame,
    lowers: list[float],
) -> pd.DataFrame:
    upper = upper_touch_df.copy()
    upper["upper_touch_complete"] = (
        (~upper["entry_blocked"]) & upper["horizon_complete"] & upper["upper_touch_possible_flag"]
    )
    path = prepare_path_flags(path_df)
    rows: list[dict[str, Any]] = []
    upper_ord = upper["event_ordinal"].to_numpy(dtype=int)
    path_ord = path["event_ordinal"].to_numpy(dtype=int)
    for scope_id in SCOPE_SPECS:
        for split in SPLITS:
            event_mask = scope_event_mask(universe, scope_id, split)
            usub = upper.loc[event_mask[upper_ord]]
            psub = path.loc[event_mask[path_ord]]
            killed = {}
            if not psub.empty:
                kill_group = psub.groupby(["upper_barrier_pct", "horizon_sessions", "lower_barrier_pct"], observed=True)
                for (u, h, lower), g in kill_group:
                    den = int(g["upper_touch_possible_flag"].sum())
                    killed[(float(u), int(h), float(lower))] = safe_rate(int(g["true_survivor_killed_by_lower_flag"].sum()), den)
            for (u, h), g in usub.groupby(["upper_barrier_pct", "horizon_sessions"], observed=True):
                complete = g.loc[g["upper_touch_complete"]]
                row = {
                    "scope_id": scope_id,
                    "split": split,
                    "upper_barrier_pct": float(u),
                    "horizon_sessions": int(h),
                    "upper_first_n": int(complete["event_ordinal"].nunique()),
                    "pre_success_mae_p25": q_value(complete["pre_success_mae"], 0.25),
                    "pre_success_mae_p50": q_value(complete["pre_success_mae"], 0.50),
                    "pre_success_mae_p75": q_value(complete["pre_success_mae"], 0.75),
                    "pre_success_mae_p90": q_value(complete["pre_success_mae"], 0.90),
                    "pre_success_mae_p95": q_value(complete["pre_success_mae"], 0.95),
                }
                for lower in lowers:
                    suffix = f"{abs(lower):.2f}".replace("0.", "").replace(".", "")
                    row[f"survivor_killed_by_lower_minus_{suffix}_rate"] = killed.get((float(u), int(h), float(lower)), np.nan)
                rows.append(row)
    return pd.DataFrame(rows)


def build_time_to_hit_curve(
    frontier: pd.DataFrame,
    path_df: pd.DataFrame,
    universe: pd.DataFrame,
    horizons: list[int],
    plateau_increment: float,
) -> pd.DataFrame:
    curve_cols = [
        "scope_id",
        "split",
        "upper_barrier_pct",
        "lower_barrier_pct",
        "horizon_sessions",
        "complete_executable_event_n",
        "upper_first_n",
        "upper_first_rate",
        "lower_first_n",
        "lower_first_rate",
        "median_time_to_upper_sessions",
        "median_time_to_lower_sessions",
    ]
    curve = frontier[curve_cols].copy()
    curve["p75_time_to_upper_sessions"] = np.nan
    curve["p75_time_to_lower_sessions"] = np.nan
    flagged = prepare_path_flags(path_df)
    flagged["time_to_upper_for_p75"] = flagged["time_to_upper_sessions"].where(flagged["upper_first_flag"])
    flagged["time_to_lower_for_p75"] = flagged["time_to_lower_sessions"].where(flagged["lower_first_flag"])
    ords = flagged["event_ordinal"].to_numpy(dtype=int)
    max_horizon = int(max(horizons))
    plateau_rows: list[pd.DataFrame] = []
    p75_rows: list[pd.DataFrame] = []
    for scope_id in SCOPE_SPECS:
        for split in SPLITS:
            event_mask = scope_event_mask(universe, scope_id, split)
            base_mask = event_mask & universe["entry_status"].eq("ok").to_numpy() & (
                universe["max_complete_horizon_sessions"].to_numpy() >= max_horizon
            )
            subset = flagged.loc[event_mask[ords]]
            if not subset.empty:
                p75 = subset.groupby(["upper_barrier_pct", "lower_barrier_pct", "horizon_sessions"], observed=True).agg(
                    p75_time_to_upper_sessions=("time_to_upper_for_p75", lambda s: q_value(s, 0.75)),
                    p75_time_to_lower_sessions=("time_to_lower_for_p75", lambda s: q_value(s, 0.75)),
                ).reset_index()
                p75.insert(0, "scope_id", scope_id)
                p75.insert(1, "split", split)
                p75_rows.append(p75)
            base_n = int(base_mask.sum())
            psubset = flagged.loc[base_mask[ords]]
            if psubset.empty:
                continue
            plateau = psubset.groupby(["upper_barrier_pct", "lower_barrier_pct", "horizon_sessions"], observed=True).agg(
                plateau_upper_first_n=("upper_first_flag", "sum")
            ).reset_index()
            plateau["plateau_max_horizon_sessions"] = max_horizon
            plateau["plateau_cohort_event_n"] = base_n
            plateau["plateau_upper_first_rate"] = plateau["plateau_upper_first_n"] / base_n if base_n else np.nan
            plateau.insert(0, "scope_id", scope_id)
            plateau.insert(1, "split", split)
            plateau_rows.append(plateau.drop(columns=["plateau_upper_first_n"]))
    if p75_rows:
        p75 = pd.concat(p75_rows, ignore_index=True)
        curve = curve.merge(p75, on=["scope_id", "split", "upper_barrier_pct", "lower_barrier_pct", "horizon_sessions"], how="left", suffixes=("", "_calc"))
        curve["p75_time_to_upper_sessions"] = curve["p75_time_to_upper_sessions_calc"]
        curve["p75_time_to_lower_sessions"] = curve["p75_time_to_lower_sessions_calc"]
        curve = curve.drop(columns=["p75_time_to_upper_sessions_calc", "p75_time_to_lower_sessions_calc"])
    if plateau_rows:
        plateau = pd.concat(plateau_rows, ignore_index=True)
        curve = curve.merge(plateau, on=["scope_id", "split", "upper_barrier_pct", "lower_barrier_pct", "horizon_sessions"], how="left")
    else:
        curve["plateau_max_horizon_sessions"] = max_horizon
        curve["plateau_cohort_event_n"] = 0
        curve["plateau_upper_first_rate"] = np.nan
    curve = curve.sort_values(["scope_id", "split", "upper_barrier_pct", "lower_barrier_pct", "horizon_sessions"], kind="stable")
    curve["next_horizon_incremental_upper_first_rate"] = (
        curve.groupby(["scope_id", "split", "upper_barrier_pct", "lower_barrier_pct"], observed=True)["plateau_upper_first_rate"].shift(-1)
        - curve["plateau_upper_first_rate"]
    )
    curve["horizon_plateau_flag"] = curve["next_horizon_incremental_upper_first_rate"] <= plateau_increment
    max_mask = curve["horizon_sessions"].eq(max_horizon)
    curve.loc[max_mask, "horizon_plateau_flag"] = False
    return curve


def selected_label(candidate: pd.Series | None) -> str:
    if candidate is None:
        return ""
    return (
        f"survival_U{float(candidate['upper_barrier_pct']):.2f}_"
        f"L{abs(float(candidate['lower_barrier_pct'])):.2f}_"
        f"H{int(candidate['horizon_sessions'])}"
    )


def selected_combo_rows(path_df: pd.DataFrame, candidate: pd.Series | None) -> pd.DataFrame:
    if candidate is None:
        events = path_df[["event_ordinal"]].drop_duplicates().copy()
        events["complete_executable"] = False
        events["upper_first_flag"] = False
        events["lower_first_flag"] = False
        events["neutral_flag"] = False
        events["first_hit_status"] = np.nan
        events["r_multiple_proxy"] = np.nan
        return events
    mask = (
        path_df["upper_barrier_pct"].eq(float(candidate["upper_barrier_pct"]))
        & path_df["lower_barrier_pct"].eq(float(candidate["lower_barrier_pct"]))
        & path_df["horizon_sessions"].eq(int(candidate["horizon_sessions"]))
    )
    return prepare_path_flags(path_df.loc[mask].copy())


def row_for_candidate(frontier: pd.DataFrame, candidate: pd.Series | None, split: str) -> pd.Series:
    if candidate is None:
        return pd.Series(dtype=object)
    rows = frontier.loc[
        frontier["scope_id"].eq(ALL_C0)
        & frontier["split"].eq(split)
        & frontier["upper_barrier_pct"].eq(float(candidate["upper_barrier_pct"]))
        & frontier["lower_barrier_pct"].eq(float(candidate["lower_barrier_pct"]))
        & frontier["horizon_sessions"].eq(int(candidate["horizon_sessions"]))
    ]
    return rows.iloc[0] if not rows.empty else pd.Series(dtype=object)


def selected_horizon_status(candidate: pd.Series | None, curve: pd.DataFrame, horizons: list[int]) -> str:
    if candidate is None:
        return ""
    horizon = int(candidate["horizon_sessions"])
    if horizon == max(horizons):
        return "max_horizon_reached_no_next_horizon"
    row = curve.loc[
        curve["scope_id"].eq(ALL_C0)
        & curve["split"].eq("train")
        & curve["upper_barrier_pct"].eq(float(candidate["upper_barrier_pct"]))
        & curve["lower_barrier_pct"].eq(float(candidate["lower_barrier_pct"]))
        & curve["horizon_sessions"].eq(horizon)
    ]
    if row.empty or not boolish(row.iloc[0]["horizon_plateau_flag"]):
        return "horizon_plateau_not_observed"
    return "horizon_plateau_observed"


def evaluate_threshold_decision(
    frontier: pd.DataFrame,
    curve: pd.DataFrame,
    entry_audit: pd.DataFrame,
    input_gate_pass: bool,
    thresholds: dict[str, Any],
    horizons: list[int],
) -> tuple[pd.DataFrame, pd.Series | None]:
    candidate, candidate_status = select_primary_candidate(frontier)
    strong, strong_status = select_strong_candidate(frontier)
    train = row_for_candidate(frontier, candidate, "train")
    robust = row_for_candidate(frontier, candidate, "robustness")
    validation = row_for_candidate(frontier, candidate, "validation")
    reasons: list[str] = []
    hard_failure = False
    supported_gate = False
    if not input_gate_pass:
        decision_state = "12A6_blocked_input_or_pit_failure"
        reasons.append("input_gate_failed")
    elif candidate is None:
        decision_state = "12A6_no_stable_survival_threshold"
        reasons.append("no_selected_survival_candidate")
    else:
        rel = safe_rate(robust.get("upper_first_rate", np.nan), train.get("upper_first_rate", np.nan))
        lower_delta = float(robust.get("lower_first_rate", np.nan)) - float(train.get("lower_first_rate", np.nan))
        hard_failure = bool(
            pd.isna(rel)
            or rel < float(thresholds["robustness_hard_min_upper_first_rate_relative_to_train"])
            or float(robust.get("expected_r_multiple_proxy", np.nan)) < float(thresholds["robustness_hard_min_expected_r_multiple_proxy"])
            or int(robust.get("complete_executable_event_n", 0)) < int(thresholds["robustness_hard_min_complete_executable_event_n"])
            or float(robust.get("upper_first_rate", np.nan)) < float(thresholds["robustness_hard_min_selected_upper_first_rate"])
        )
        instability = board_or_regime_instability(frontier, candidate, thresholds)
        supported_gate = bool(
            rel >= float(thresholds["robustness_min_upper_first_rate_relative_to_train"])
            and lower_delta <= float(thresholds["robustness_max_lower_first_rate_minus_train"])
            and float(robust.get("expected_r_multiple_proxy", np.nan)) >= float(thresholds["robustness_min_expected_r_multiple_proxy"])
            and not instability
        )
        if hard_failure:
            decision_state = "12A6_no_stable_survival_threshold"
            reasons.append("hard_robustness_failure")
        elif supported_gate:
            decision_state = "12A6_survival_threshold_candidates_supported"
        else:
            decision_state = "12A6_survival_threshold_candidates_partial"
            if rel < float(thresholds["robustness_min_upper_first_rate_relative_to_train"]):
                reasons.append("robustness_upper_first_rate_relative_to_train")
            if lower_delta > float(thresholds["robustness_max_lower_first_rate_minus_train"]):
                reasons.append("robustness_lower_first_rate_minus_train")
            if float(robust.get("expected_r_multiple_proxy", np.nan)) < float(thresholds["robustness_min_expected_r_multiple_proxy"]):
                reasons.append("robustness_expected_r_multiple_proxy")
            if instability:
                reasons.append("board_or_regime_instability")
    entry_gate = bool(entry_audit.iloc[0]["entry_parity_gate_pass"]) if not entry_audit.empty else False
    row = {
        "decision_state": decision_state,
        "selected_survival_candidate_label": selected_label(candidate),
        "selected_upper_barrier_pct": np.nan if candidate is None else float(candidate["upper_barrier_pct"]),
        "selected_lower_barrier_pct": np.nan if candidate is None else float(candidate["lower_barrier_pct"]),
        "selected_horizon_sessions": np.nan if candidate is None else int(candidate["horizon_sessions"]),
        "selected_horizon_status": selected_horizon_status(candidate, curve, horizons),
        "selected_train_upper_first_rate": train.get("upper_first_rate", np.nan),
        "selected_train_lower_first_rate": train.get("lower_first_rate", np.nan),
        "selected_train_expected_r_multiple_proxy": train.get("expected_r_multiple_proxy", np.nan),
        "selected_train_time_penalized_expected_r_proxy": train.get("time_penalized_expected_r_proxy", np.nan),
        "selected_robustness_upper_first_rate": robust.get("upper_first_rate", np.nan),
        "selected_robustness_lower_first_rate": robust.get("lower_first_rate", np.nan),
        "selected_robustness_expected_r_multiple_proxy": robust.get("expected_r_multiple_proxy", np.nan),
        "selected_validation_upper_first_rate": validation.get("upper_first_rate", np.nan),
        "selected_candidate_status": candidate_status,
        "strong_survival_candidate_label": selected_label(strong),
        "strong_upper_barrier_pct": np.nan if strong is None else float(strong["upper_barrier_pct"]),
        "strong_lower_barrier_pct": np.nan if strong is None else float(strong["lower_barrier_pct"]),
        "strong_horizon_sessions": np.nan if strong is None else int(strong["horizon_sessions"]),
        "strong_train_upper_first_rate": np.nan if strong is None else float(strong["upper_first_rate"]),
        "strong_robustness_upper_first_rate": row_for_candidate(frontier, strong, "robustness").get("upper_first_rate", np.nan)
        if strong is not None
        else np.nan,
        "strong_candidate_status": strong_status,
        "bigwinner_enrichment_ratio": np.nan,
        "bigwinner_enrichment_status": "pending_enrichment_table",
        "gate_failure_reasons": ";".join(reasons),
        "next_allowed_requirement": next_requirement(decision_state),
        "input_gate_pass": bool(input_gate_pass),
        "entry_parity_gate_pass": bool(entry_gate),
        "hard_robustness_failure": bool(hard_failure),
        "supported_gate_pass": bool(supported_gate),
    }
    return pd.DataFrame([row]), candidate


def board_or_regime_instability(frontier: pd.DataFrame, candidate: pd.Series, thresholds: dict[str, Any]) -> bool:
    selected = frontier.loc[
        frontier["split"].eq("robustness")
        & frontier["upper_barrier_pct"].eq(float(candidate["upper_barrier_pct"]))
        & frontier["lower_barrier_pct"].eq(float(candidate["lower_barrier_pct"]))
        & frontier["horizon_sessions"].eq(int(candidate["horizon_sessions"]))
    ]
    all_row = selected.loc[selected["scope_id"].eq(ALL_C0)]
    if all_row.empty:
        return True
    base = float(all_row.iloc[0]["upper_first_rate"])
    slice_rows = selected.loc[
        selected["scope_id"].isin([*REGIME_SCOPES.keys(), *BOARD_SCOPES.keys()])
        & (selected["event_n"] >= int(thresholds["instability_min_slice_event_n"]))
    ]
    if slice_rows.empty or pd.isna(base):
        return False
    return bool((slice_rows["upper_first_rate"] < base * float(thresholds["instability_min_slice_relative_upper_first_rate"])).any())


def next_requirement(decision_state: str) -> str:
    if decision_state == "12A6_survival_threshold_candidates_supported":
        return "requirement_12a7_c0_survival_meta_label_feasibility.md"
    if decision_state == "12A6_survival_threshold_candidates_partial":
        return "requirement_12a6b_survival_scope_or_threshold_revision.md"
    if decision_state == "12A6_no_stable_survival_threshold":
        return "stop_c0_survival_as_primary_target_keep_diagnostic_only"
    return "fix_input_or_pit_failure_then_rerun_12A6"


def build_same_bar_audit(frontier: pd.DataFrame) -> pd.DataFrame:
    return frontier[
        [
            "scope_id",
            "split",
            "upper_barrier_pct",
            "lower_barrier_pct",
            "horizon_sessions",
            "complete_executable_event_n",
            "same_bar_conflict_n",
            "same_bar_conflict_rate",
        ]
    ].assign(conflict_counted_as="lower_first")


def compute_event_density(universe: pd.DataFrame, selected_horizon: int) -> pd.DataFrame:
    out = universe[["event_ordinal", "instrument", "event_t0_pos", "trade_open_pos", "event_split"]].copy()
    out["same_instrument_prior_c0_10d"] = 0
    out["same_instrument_prior_c0_20d"] = 0
    out["same_instrument_next_c0_20d"] = 0
    out["overlap_with_other_c0_survival_window_n"] = 0
    for _, idx in out.groupby("instrument").groups.items():
        pos = out.loc[idx, "event_t0_pos"].to_numpy(dtype=float)
        order = np.argsort(pos)
        ordered_idx = np.array(list(idx))[order]
        ordered_pos = pos[order]
        starts = out.loc[ordered_idx, "trade_open_pos"].to_numpy(dtype=float)
        ends = starts + selected_horizon
        for i, original_idx in enumerate(ordered_idx):
            p = ordered_pos[i]
            out.loc[original_idx, "same_instrument_prior_c0_10d"] = int(((ordered_pos < p) & (ordered_pos >= p - 10)).sum())
            out.loc[original_idx, "same_instrument_prior_c0_20d"] = int(((ordered_pos < p) & (ordered_pos >= p - 20)).sum())
            out.loc[original_idx, "same_instrument_next_c0_20d"] = int(((ordered_pos > p) & (ordered_pos <= p + 20)).sum())
            out.loc[original_idx, "overlap_with_other_c0_survival_window_n"] = int(((starts <= ends[i]) & (ends >= starts[i])).sum() - 1)
    return out


def build_overlap_density_audit(universe: pd.DataFrame, selected_horizon: int, label: str) -> pd.DataFrame:
    density = compute_event_density(universe, selected_horizon)
    rows: list[dict[str, Any]] = []
    for scope_id in SCOPE_SPECS:
        for split in SPLITS:
            mask = scope_event_mask(universe, scope_id, split)
            sub = density.loc[mask]
            rows.append(
                {
                    "scope_id": scope_id,
                    "split": split,
                    "event_n": int(len(sub)),
                    "same_instrument_prior_c0_10d_rate": safe_rate((sub["same_instrument_prior_c0_10d"] > 0).sum(), len(sub)),
                    "same_instrument_prior_c0_20d_rate": safe_rate((sub["same_instrument_prior_c0_20d"] > 0).sum(), len(sub)),
                    "same_instrument_next_c0_20d_rate": safe_rate((sub["same_instrument_next_c0_20d"] > 0).sum(), len(sub)),
                    "overlap_with_other_c0_survival_window_mean": float(sub["overlap_with_other_c0_survival_window_n"].mean()) if not sub.empty else np.nan,
                    "overlap_with_other_c0_survival_window_p95": q_value(sub["overlap_with_other_c0_survival_window_n"], 0.95),
                    "selected_survival_candidate_label": label,
                }
            )
    return pd.DataFrame(rows)


def add_overlap_flags(universe: pd.DataFrame, reg06: pd.DataFrame, reg11: pd.DataFrame, targets12a4: pd.DataFrame) -> pd.DataFrame:
    out = universe.copy()
    for col in ("event_t0_date", "trade_open_date"):
        out[col] = out[col].map(date_text)
    out["overlap_06_low_to_high"] = False
    out["overlap_06_pre120_to_high"] = False
    reg06 = reg06.copy()
    for col in ("episode_low_date", "episode_high_date", "pre120_calendar_start_date"):
        reg06[col] = reg06[col].map(date_text)
    for ep in reg06.itertuples(index=False):
        instrument_mask = out["instrument"].astype(str).eq(str(ep.instrument))
        date = out["event_t0_date"].astype(str)
        low_to_high = instrument_mask & (date >= ep.episode_low_date) & (date <= ep.episode_high_date)
        pre120 = instrument_mask & (date >= ep.pre120_calendar_start_date) & (date <= ep.episode_high_date)
        out.loc[low_to_high, "overlap_06_low_to_high"] = True
        out.loc[pre120, "overlap_06_pre120_to_high"] = True
    reg11_pairs = {
        (str(row.instrument), date_text(row.event_t0_date))
        for row in reg11.itertuples(index=False)
        if str(getattr(row, "analysis_regime_scope", "risk_on")) == "risk_on"
    }
    out["overlap_11a2_pre120_to_high"] = [
        (str(row.instrument), str(row.event_t0_date)) in reg11_pairs for row in out.itertuples(index=False)
    ]
    if not targets12a4.empty and "meta_event_id" in targets12a4.columns:
        t = targets12a4.loc[targets12a4["source_arm_id"].astype(str).eq("C0_state_change")].copy()
        t["canonical_event_id"] = t["meta_event_id"].astype(str).str.replace("C0_", "", n=1, regex=False)
        winner_map = dict(zip(t["canonical_event_id"].astype(str), bool_series(t["winner_120_label"])))
        out["overlap_12a4_risk_on_sanity_winner_120"] = out["canonical_event_id"].astype(str).map(
            lambda value: bool(winner_map.get(value, False))
        )
    else:
        out["overlap_12a4_risk_on_sanity_winner_120"] = False
    return out


def build_enrichment_crosstab(
    universe: pd.DataFrame,
    selected_rows: pd.DataFrame,
    label: str,
) -> pd.DataFrame:
    selected = selected_rows[["event_ordinal", "complete_executable", "upper_first_flag"]].copy()
    events = universe.merge(selected, on="event_ordinal", how="left")
    events["complete_executable"] = events["complete_executable"].fillna(False).astype(bool)
    events["selected_upper_first_survival"] = events["upper_first_flag"].fillna(False).astype(bool)
    specs = [
        ("06_registry", "low_to_high", "overlap_06_low_to_high", True),
        ("06_registry", "pre120_to_high", "overlap_06_pre120_to_high", True),
        ("11a2_registry", "pre120_to_high", "overlap_11a2_pre120_to_high", True),
        ("12a4_risk_on_sanity", "risk_on_sanity_winner_120", "overlap_12a4_risk_on_sanity_winner_120", False),
    ]
    rows: list[dict[str, Any]] = []
    for source, window, flag_col, can_headline in specs:
        for split in SPLITS:
            split_mask = np.ones(len(events), dtype=bool) if split == "all" else events["event_split"].astype(str).eq(split).to_numpy()
            for scope_id in ("regime_risk_on", "all_c0"):
                headline = bool(can_headline and scope_id == "regime_risk_on")
                scope_mask = events["market_regime_bucket"].astype(str).eq("risk_on").to_numpy() if scope_id == "regime_risk_on" else np.ones(len(events), dtype=bool)
                mask = split_mask & scope_mask & events["complete_executable"].to_numpy()
                selected_mask = mask & events["selected_upper_first_survival"].to_numpy()
                selected_n = int(selected_mask.sum())
                selected_overlap = int((selected_mask & events[flag_col].to_numpy(dtype=bool)).sum())
                baseline_n = int(mask.sum())
                baseline_overlap = int((mask & events[flag_col].to_numpy(dtype=bool)).sum())
                selected_rate = safe_rate(selected_overlap, selected_n)
                baseline_rate = safe_rate(baseline_overlap, baseline_n)
                rows.append(
                    {
                        "overlap_source": source,
                        "overlap_window": window,
                        "scope_id": scope_id,
                        "split": split,
                        "registry_scope_id": "regime_risk_on",
                        "baseline_scope_id": scope_id,
                        "selected_survival_candidate_label": label,
                        "selected_upper_first_survival_event_n": selected_n,
                        "selected_upper_first_overlap_n": selected_overlap,
                        "selected_upper_first_overlap_rate": selected_rate,
                        "baseline_event_n": baseline_n,
                        "baseline_overlap_n": baseline_overlap,
                        "baseline_overlap_rate": baseline_rate,
                        "bigwinner_enrichment_ratio": selected_rate / baseline_rate if pd.notna(selected_rate) and pd.notna(baseline_rate) and baseline_rate != 0 else np.nan,
                        "enrichment_status": "undefined_zero_baseline" if baseline_rate == 0 or pd.isna(baseline_rate) else "ok",
                        "headline_enrichment_flag": headline,
                        "diagnostic_only_flag": not headline,
                    }
                )
    return pd.DataFrame(rows)


def late_stage_feature_policy_status(features: pd.DataFrame) -> str:
    missing = [col for col in LATE_STAGE_NUMERIC_FEATURE_COLUMNS if col not in features.columns]
    if missing or features.empty:
        return "diagnostic_not_comparable"
    coverage = features[list(LATE_STAGE_NUMERIC_FEATURE_COLUMNS)].notna().mean()
    if coverage.empty or float(coverage.max()) == 0.0:
        return "diagnostic_not_comparable"
    return "pass"


def late_stage_table_policy_status(late: pd.DataFrame) -> str:
    if late.empty or "late_stage_feature_policy_status" not in late.columns:
        return "diagnostic_not_comparable"
    statuses = set(late["late_stage_feature_policy_status"].dropna().astype(str))
    return "pass" if statuses == {"pass"} else "diagnostic_not_comparable"


def compute_late_stage_features(universe: pd.DataFrame, stock_cache: StockDailyCache) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    same_day_counts = universe.groupby(["instrument", "event_t0_date"])["canonical_event_id"].transform("count")
    pos_by_inst = {inst: group["event_t0_pos"].to_numpy(dtype=float) for inst, group in universe.groupby("instrument")}
    for i, row in enumerate(universe.itertuples(index=False)):
        daily = stock_cache.get(row.instrument)
        values: dict[str, Any] = {"event_ordinal": int(row.event_ordinal)}
        if daily is None or row.entry_status != "ok" or pd.isna(row.event_t0_pos):
            for col in LATE_STAGE_NUMERIC_FEATURE_COLUMNS:
                values[col] = np.nan
        else:
            pos = int(row.event_t0_pos)
            close = daily["close"].to_numpy(dtype=float)
            high = daily["high"].to_numpy(dtype=float)
            low = daily["low"].to_numpy(dtype=float)
            values["ret_20d"] = close[pos] / close[pos - 20] - 1.0 if pos >= 20 and close[pos - 20] else np.nan
            values["ret_60d"] = close[pos] / close[pos - 60] - 1.0 if pos >= 60 and close[pos - 60] else np.nan
            h60 = np.nanmax(high[max(0, pos - 59) : pos + 1])
            h120 = np.nanmax(high[max(0, pos - 119) : pos + 1])
            l60 = np.nanmin(low[max(0, pos - 59) : pos + 1])
            l120 = np.nanmin(low[max(0, pos - 119) : pos + 1])
            values["distance_to_60d_high"] = close[pos] / h60 - 1.0 if h60 else np.nan
            values["distance_to_120d_high"] = close[pos] / h120 - 1.0 if h120 else np.nan
            values["distance_to_60d_low"] = close[pos] / l60 - 1.0 if l60 else np.nan
            values["distance_to_120d_low"] = close[pos] / l120 - 1.0 if l120 else np.nan
            ema20 = pd.Series(close[: pos + 1]).ewm(span=20, adjust=False).mean().iloc[-1]
            ema60 = pd.Series(close[: pos + 1]).ewm(span=60, adjust=False).mean().iloc[-1]
            values["trend_ma_20_60_spread"] = ema20 / ema60 - 1.0 if ema60 else np.nan
            returns = pd.Series(close[: pos + 1]).pct_change()
            values["volatility_20d"] = float(returns.tail(20).std())
            values["volatility_60d"] = float(returns.tail(60).std())
        positions = pos_by_inst.get(row.instrument, np.array([], dtype=float))
        values["prior_c0_event_count_20d"] = int(((positions < row.event_t0_pos) & (positions >= row.event_t0_pos - 20)).sum())
        values["same_day_c0_event_count_all"] = int(same_day_counts.iloc[i])
        rows.append(values)
    features = pd.DataFrame(rows)
    features["near_60d_high"] = features["distance_to_60d_high"] >= -0.05
    features["near_120d_high"] = features["distance_to_120d_high"] >= -0.08
    features["extended_20d"] = features["ret_20d"] >= 0.20
    features["extended_60d"] = features["ret_60d"] >= 0.40
    features["late_stage_composite"] = features["near_60d_high"] & (features["extended_20d"] | features["extended_60d"])
    features["late_stage_feature_policy_status"] = late_stage_feature_policy_status(features)
    return features


def build_late_stage_diagnostics(
    universe: pd.DataFrame,
    features: pd.DataFrame,
    selected_rows: pd.DataFrame,
    label: str,
) -> pd.DataFrame:
    metrics = selected_rows[["event_ordinal", "first_hit_status", "upper_first_flag", "lower_first_flag", "neutral_flag", "r_multiple_proxy"]].copy()
    events = universe.merge(features, on="event_ordinal", how="left").merge(metrics, on="event_ordinal", how="left")
    rows: list[dict[str, Any]] = []
    buckets = ["near_60d_high", "near_120d_high", "extended_20d", "extended_60d", "late_stage_composite"]
    policy_status = late_stage_feature_policy_status(features)
    for bucket in buckets:
        bucket_mask = events[bucket].fillna(False).to_numpy(dtype=bool)
        for split in SPLITS:
            split_mask = np.ones(len(events), dtype=bool) if split == "all" else events["event_split"].astype(str).eq(split).to_numpy()
            for regime in ("all", "risk_on", "transition", "risk_off"):
                regime_mask = np.ones(len(events), dtype=bool) if regime == "all" else events["market_regime_bucket"].astype(str).eq(regime).to_numpy()
                mask = bucket_mask & split_mask & regime_mask
                sub = events.loc[mask]
                selected_sub = sub.loc[sub["first_hit_status"].notna()]
                selected_n = len(selected_sub)
                overlap = sub.get("overlap_06_pre120_to_high", pd.Series(False, index=sub.index)).astype(bool)
                selected_rate = safe_rate(int((selected_sub["upper_first_flag"].fillna(False).astype(bool) & overlap.loc[selected_sub.index]).sum()), int(selected_sub["upper_first_flag"].fillna(False).astype(bool).sum()))
                baseline_rate = safe_rate(int(overlap.sum()), len(sub))
                rows.append(
                    {
                        "late_stage_bucket": bucket,
                        "scope_id": ALL_C0 if regime == "all" else f"regime_{regime}",
                        "split": split,
                        "market_regime_bucket": regime,
                        "event_n": int(len(sub)),
                        "selected_survival_candidate_label": label,
                        "selected_upper_barrier_pct": np.nan,
                        "selected_lower_barrier_pct": np.nan,
                        "selected_horizon_sessions": np.nan,
                        "selected_upper_first_n": int(selected_sub["upper_first_flag"].fillna(False).astype(bool).sum()) if selected_n else 0,
                        "selected_upper_first_rate": safe_rate(int(selected_sub["upper_first_flag"].fillna(False).astype(bool).sum()) if selected_n else 0, selected_n),
                        "selected_lower_first_n": int(selected_sub["lower_first_flag"].fillna(False).astype(bool).sum()) if selected_n else 0,
                        "selected_lower_first_rate": safe_rate(int(selected_sub["lower_first_flag"].fillna(False).astype(bool).sum()) if selected_n else 0, selected_n),
                        "selected_neutral_n": int(selected_sub["neutral_flag"].fillna(False).astype(bool).sum()) if selected_n else 0,
                        "selected_neutral_rate": safe_rate(int(selected_sub["neutral_flag"].fillna(False).astype(bool).sum()) if selected_n else 0, selected_n),
                        "expected_r_multiple_proxy": float(selected_sub["r_multiple_proxy"].mean()) if selected_n else np.nan,
                        "bigwinner_enrichment_ratio": selected_rate / baseline_rate if pd.notna(selected_rate) and pd.notna(baseline_rate) and baseline_rate != 0 else np.nan,
                        "late_stage_feature_policy_status": policy_status,
                    }
                )
    return pd.DataFrame(rows)


def update_late_stage_candidate_columns(late: pd.DataFrame, candidate: pd.Series | None) -> pd.DataFrame:
    out = late.copy()
    if candidate is not None:
        out["selected_upper_barrier_pct"] = float(candidate["upper_barrier_pct"])
        out["selected_lower_barrier_pct"] = float(candidate["lower_barrier_pct"])
        out["selected_horizon_sessions"] = int(candidate["horizon_sessions"])
    return out


def update_decision_with_enrichment(decision: pd.DataFrame, enrichment: pd.DataFrame) -> pd.DataFrame:
    out = decision.copy()
    headline = enrichment.loc[
        enrichment["headline_enrichment_flag"].astype(bool)
        & enrichment["split"].eq("robustness")
        & enrichment["overlap_source"].eq("06_registry")
        & enrichment["overlap_window"].eq("pre120_to_high")
    ]
    if not headline.empty:
        out.loc[0, "bigwinner_enrichment_ratio"] = headline.iloc[0]["bigwinner_enrichment_ratio"]
        out.loc[0, "bigwinner_enrichment_status"] = headline.iloc[0]["enrichment_status"]
    else:
        out.loc[0, "bigwinner_enrichment_status"] = "not_available"
    return out


def build_report(
    decision: pd.DataFrame,
    frontier: pd.DataFrame,
    forward: pd.DataFrame,
    pre_success: pd.DataFrame,
    late: pd.DataFrame,
    enrichment: pd.DataFrame,
    entry_audit: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    all_train = frontier.loc[frontier["scope_id"].eq(ALL_C0) & frontier["split"].eq("train")]
    eligible_n = int(all_train["selection_eligible_flag"].astype(bool).sum()) if not all_train.empty else 0
    f120 = forward.loc[forward["scope_id"].eq(ALL_C0) & forward["split"].eq("all") & forward["horizon_sessions"].eq(120)]
    f120_text = "not available"
    if not f120.empty:
        row = f120.iloc[0]
        f120_text = f"MFE p50={row['mfe_p50']:.4f}, MAE p50={row['mae_p50']:.4f}, complete_n={int(row['complete_executable_event_n'])}"
    enr = enrichment.loc[enrichment["headline_enrichment_flag"].astype(bool)].head(1)
    enr_text = "not available"
    if not enr.empty:
        row = enr.iloc[0]
        enr_text = f"{row['overlap_source']} {row['overlap_window']} ratio={row['bigwinner_enrichment_ratio']:.4f}"
    selected_filter = (
        frontier["upper_barrier_pct"].eq(float(d["selected_upper_barrier_pct"]))
        & frontier["lower_barrier_pct"].eq(float(d["selected_lower_barrier_pct"]))
        & frontier["horizon_sessions"].eq(int(d["selected_horizon_sessions"]))
    )
    regime_rows = frontier.loc[
        selected_filter
        & frontier["split"].eq("robustness")
        & frontier["scope_id"].isin(["regime_risk_on", "regime_transition", "regime_risk_off"])
    ].sort_values("scope_id")
    regime_lines = []
    for row in regime_rows.itertuples(index=False):
        regime_lines.append(
            f"- `{row.scope_id}` robustness: event_n={int(row.event_n)}, "
            f"upper_first={row.upper_first_rate:.4f}, lower_first={row.lower_first_rate:.4f}, "
            f"expected_R={row.expected_r_multiple_proxy:.4f}"
        )
    pre_row = pre_success.loc[
        pre_success["scope_id"].eq(ALL_C0)
        & pre_success["split"].eq("all")
        & pre_success["upper_barrier_pct"].eq(float(d["selected_upper_barrier_pct"]))
        & pre_success["horizon_sessions"].eq(int(d["selected_horizon_sessions"]))
    ].head(1)
    pre_text = "not available"
    if not pre_row.empty:
        p = pre_row.iloc[0]
        pre_text = (
            f"pre-success MAE p50={p['pre_success_mae_p50']:.4f}, "
            f"p90={p['pre_success_mae_p90']:.4f}, "
            f"killed_by_-15={p.get('survivor_killed_by_lower_minus_15_rate', np.nan):.4f}"
        )
    late_row = late.loc[
        late["late_stage_bucket"].eq("late_stage_composite")
        & late["split"].eq("robustness")
        & late["market_regime_bucket"].eq("all")
    ].head(1)
    late_text = "not available"
    if not late_row.empty:
        l = late_row.iloc[0]
        late_text = (
            f"event_n={int(l['event_n'])}, upper_first={l['selected_upper_first_rate']:.4f}, "
            f"lower_first={l['selected_lower_first_rate']:.4f}, neutral={l['selected_neutral_rate']:.4f}"
        )
    selected_text = (
        f"train upper/lower/expected_R={d['selected_train_upper_first_rate']:.4f}/"
        f"{d['selected_train_lower_first_rate']:.4f}/{d['selected_train_expected_r_multiple_proxy']:.4f}; "
        f"robustness upper/lower/expected_R={d['selected_robustness_upper_first_rate']:.4f}/"
        f"{d['selected_robustness_lower_first_rate']:.4f}/{d['selected_robustness_expected_r_multiple_proxy']:.4f}"
    )
    return f"""
# 12A6 C0 Local Survival Episode Audit Report

## Decision

- final decision: `{d['decision_state']}`
- selected candidate: `{d['selected_survival_candidate_label']}`
- selected candidate status: `{d['selected_candidate_status']}`
- strong candidate status: `{d['strong_candidate_status']}`
- next allowed requirement: `{d['next_allowed_requirement']}`

## Denominator

- primary event universe: one row per 12A2 C0 canonical event
- source_scope_id: `{SOURCE_SCOPE_ID}` (12A6-derived output field)
- entry parity gate pass: `{entry_audit.iloc[0]['entry_parity_gate_pass']}`
- entry blocked rows: {int(entry_audit.iloc[0]['entry_blocked_n'])}
- this is event-level survival outcome, not a new big-winner registry and not an episode-collapse registry.

## Survival Grid

- eligible train all-C0 candidates: {eligible_n}
- 120-session all-C0 path summary: {f120_text}
- existing `continuation_60` remains only a comparison anchor: +20% MFE / -15% drawdown / 60 sessions.
- selected candidate train/robustness readout: {selected_text}
- strong candidate: `{d['strong_survival_candidate_label']}` with robustness upper_first={d['strong_robustness_upper_first_rate']:.4f}

## Regime Slices

{chr(10).join(regime_lines) if regime_lines else '- no regime slice rows available'}

## Pre-success MAE

- selected upper/horizon readout: {pre_text}
- lower barriers are selected from the audit grid; existing `continuation_60` does not force the 12A6 lower barrier.

## Late-stage Diagnostic

- late_stage_composite robustness readout: {late_text}
- late-stage EMA/rolling features are qfq close-observed readouts and cannot change survival labels.

## Big-winner Enrichment

- headline enrichment uses risk_on selected events against risk_on baseline.
- first headline row: {enr_text}
- all-C0 enrichment rows are diagnostic-only and cannot change the selected survival threshold.

## Caveats

- This is an event-level survival outcome audit, not a new big-winner registry.
- `expected_r_multiple_proxy` is a first-hit proxy, not tradable PnL.
- Late-stage price features use qfq close-observed daily bars and are readout-only.
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
    late_policy_status = late_stage_table_policy_status(frames.get("late_stage", pd.DataFrame()))
    return {
        "run_id": RUN_ID,
        "phase_id": "12A6",
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
        "selected_candidate_status": decision.iloc[0]["selected_candidate_status"] if not decision.empty else "",
        "strong_survival_candidate_status": decision.iloc[0]["strong_candidate_status"] if not decision.empty else "",
        "bigwinner_enrichment_status": decision.iloc[0]["bigwinner_enrichment_status"] if not decision.empty else "",
        "late_stage_feature_policy_status": late_policy_status,
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
            raise RuntimeError("12A6 input check failed")
        print(f"{RUN_ID}: input audit ok ({len(audit)} artifacts)")
        return 0
    if not read_ok or not schema_ok:
        raise RuntimeError("12A6 required inputs missing or schema mismatch")

    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    decision_12a2 = read_table(resolved["state_change_generation_decision"])
    canonical = read_table(resolved["state_change_candidate_event_canonical"])
    universe = normalize_primary_events(canonical)
    a2_ok, a2_reason = check_12a2_gate(decision_12a2, len(universe))
    duplicate_ok = not universe["canonical_event_id"].duplicated().any()
    stock_cache = StockDailyCache(resolved["stock_daily_csv_dir"])
    horizons = [int(x) for x in config["grid"]["horizon_sessions"]]
    uppers = [float(x) for x in config["grid"]["upper_barrier_pct"]]
    lowers = [float(x) for x in config["grid"]["lower_barrier_pct"]]
    pit_membership_lookup = load_pit_membership_lookup(
        resolved["pit_executable_daily"],
        set(universe["instrument"].astype(str)),
        set(universe["trade_open_date"].astype(str)),
    )
    universe, entry_audit = attach_entry_audit(universe, stock_cache, max(horizons), pit_membership_lookup)
    path_df, event_horizon_df, upper_touch_df = compute_path_matrices(universe, stock_cache, horizons, uppers, lowers)
    write_df(paths["path_matrix"], path_df)

    frontier = build_grid_frontier(path_df, universe, config["thresholds"])
    forward = build_forward_distribution(event_horizon_df, universe)
    pre_success = build_pre_success_mae_distribution(upper_touch_df, path_df, universe, lowers)
    curve = build_time_to_hit_curve(
        frontier,
        path_df,
        universe,
        horizons,
        float(config["thresholds"]["plateau_incremental_upper_first_rate_max"]),
    )
    input_gate_pass = bool(read_ok and schema_ok and a2_ok and duplicate_ok and bool(entry_audit.iloc[0]["entry_parity_gate_pass"]))
    threshold_decision, candidate = evaluate_threshold_decision(frontier, curve, entry_audit, input_gate_pass, config["thresholds"], horizons)
    combo = selected_combo_rows(path_df, candidate)
    selected_horizon = int(candidate["horizon_sessions"]) if candidate is not None else int(max(horizons))
    label = selected_label(candidate)

    reg06 = read_table(resolved["episode_target_registry_06"])
    reg11 = read_table(resolved["pit_candidate_winner_registry_11a2"])
    targets12a4 = read_table(resolved["meta_label_event_targets_12a4"])
    universe = add_overlap_flags(universe, reg06, reg11, targets12a4)
    enrichment = build_enrichment_crosstab(universe, combo, label)
    threshold_decision = update_decision_with_enrichment(threshold_decision, enrichment)
    late_features = compute_late_stage_features(universe, stock_cache)
    late = build_late_stage_diagnostics(universe, late_features, combo, label)
    late = update_late_stage_candidate_columns(late, candidate)
    overlap_density = build_overlap_density_audit(universe, selected_horizon, label)
    same_bar = build_same_bar_audit(frontier)
    report = build_report(threshold_decision, frontier, forward, pre_success, late, enrichment, entry_audit)

    event_universe_cols = [
        "survival_event_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "trade_open_price",
        "event_split",
        "board_bucket",
        "market_regime_bucket",
        "primary_family_id",
        "primary_variant_id",
        "triggered_family_variants",
        "triggered_family_count",
        "canonical_priority",
        "candidate_generation_status",
        "non_executable_next_open",
        "event_t0_pit_status",
        "trade_open_pit_status",
        "trade_open_pit_membership_status",
        "entry_status",
        "source_scope_id",
        "event_ordinal",
        "max_complete_horizon_sessions",
    ]
    event_universe = universe[event_universe_cols].copy()
    frames = {
        "input_artifact_audit": audit,
        "event_universe": event_universe,
        "forward_distribution": forward,
        "grid_frontier": frontier,
        "pre_success_mae": pre_success,
        "time_to_hit_curve": curve,
        "threshold_decision": threshold_decision,
        "bigwinner_enrichment": enrichment,
        "late_stage": late,
        "entry_audit": entry_audit,
        "same_bar_audit": same_bar,
        "overlap_density": overlap_density,
        "path_matrix": path_df,
    }
    for key, frame in frames.items():
        if key in paths and key != "path_matrix":
            write_df(paths[key], frame)
    write_text(paths["report"], report)
    frames["report"] = pd.DataFrame([{"report_path": str(paths["report"])}])
    requirement_path = resolved["requirement"]
    write_json(paths["manifest"], build_manifest(paths, frames, threshold_decision, config_path, requirement_path, config, audit))
    if not a2_ok:
        print(f"{RUN_ID}: 12A2 gate warning: {a2_reason}")
    print(f"{RUN_ID}: {threshold_decision.iloc[0]['decision_state']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_pipeline(Path(args.config), args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

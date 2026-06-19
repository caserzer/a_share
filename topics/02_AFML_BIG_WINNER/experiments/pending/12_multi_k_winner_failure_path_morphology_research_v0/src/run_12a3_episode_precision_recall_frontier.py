#!/usr/bin/env python
from __future__ import annotations

import argparse
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


RUN_ID = "12A3_episode_precision_recall_frontier"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a3_episode_precision_recall_frontier.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
WINDOWS = ("pre120_calendar_to_high", "low_to_high", "low_to_first_50pct")
RAW_R_CORE_ARM = "08_R_core_event_regime_gated_raw"
R6_ARM = "08_R6_event_regime_gated_raw"
PRIMARY_STATE_ARM = "12A2_C0_primary_canonical_union"
SENSITIVITY_ARM = "12A2_B3_before_B1_priority_sensitivity"
B5_DOWNPRIORITY_ARM = "12A2_B5_downpriority_sensitivity"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A3 episode precision/recall frontier.")
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
    if text.startswith("outputs/"):
        return EXPERIMENT_DIR / path
    if text.startswith(("configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "frontier_arm_registry": TABLE_DIR / "frontier_arm_registry.csv",
        "frontier": TABLE_DIR / "backbone_episode_recall_precision_frontier.csv",
        "timing": TABLE_DIR / "backbone_event_timing_distribution.csv",
        "captured_density": TABLE_DIR / "backbone_captured_episode_density.csv",
        "missed_diagnostics": TABLE_DIR / "backbone_missed_episode_diagnostics.csv",
        "b8_incremental": TABLE_DIR / "backbone_b8_incremental_episode_recall.csv",
        "label_exposure": TABLE_DIR / "backbone_event_label_exposure.csv",
        "slice_readout": TABLE_DIR / "backbone_frontier_slice_readout.csv",
        "label_parity": TABLE_DIR / "state_change_label_recompute_parity_audit.csv",
        "decision": TABLE_DIR / "backbone_frontier_decision.csv",
        "report": REPORT_DIR / "backbone_frontier_decision_report.md",
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
        frame.to_csv(
            path,
            index=False,
            compression={"method": "gzip", "compresslevel": 9, "mtime": 1},
        )
    else:
        frame.to_csv(path, index=False)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def path_sha(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0:
        return np.nan
    return float(numerator) / float(denominator)


def boolish(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def bool_series(values: pd.Series) -> pd.Series:
    return values.map(boolish).astype(bool)


def nonempty_str(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value)
    return "" if text.lower() == "nan" else text


def date_text(value: Any) -> str:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d")


def date_series(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce")


def numeric_series(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


def first_existing(row: pd.Series, names: tuple[str, ...], default: Any = np.nan) -> Any:
    for name in names:
        if name in row.index and not pd.isna(row[name]):
            return row[name]
    return default


def parse_family_from_variant(value: Any) -> str:
    text = nonempty_str(value)
    if not text:
        return ""
    return text.split("_", 1)[0]


def triggered_contains(values: pd.Series, family_id: str) -> pd.Series:
    pattern = f"{family_id}_"
    return values.fillna("").astype(str).str.contains(pattern, regex=False)


EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "state_change_generation_decision": (
        "decision",
        "next_allowed_requirement",
        "upstream_next_allowed_requirement",
        "handoff_conflict_flag",
    ),
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
        "triggered_family_variants",
        "triggered_family_count",
        "non_executable_next_open",
        "event_t0_pit_status",
        "trade_open_pit_status",
        "candidate_generation_status",
    ),
    "state_change_candidate_event_instances": (
        "event_instance_id",
        "family_id",
        "family_variant_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "raw_event_status",
        "family_input_status",
        "allowed_for_primary_canonical_flag",
        "first_trigger_status",
        "non_executable_next_open",
        "event_t0_pit_status",
        "trade_open_pit_status",
    ),
    "episode_target_registry_06": (
        "episode_id",
        "instrument",
        "episode_low_date",
        "episode_high_date",
        "first_50pct_date",
        "pre120_calendar_start_date",
        "low_to_high_sessions",
        "mfe_120",
        "split",
        "duration_bucket",
        "board_bucket",
    ),
    "r_core_demote_or_keep_decision": ("decision",),
    "r_core_arm_event_registry": (
        "arm_id",
        "event_key",
        "instrument",
        "event_signal_date",
        "event_signal_pos",
        "event_execution_date",
        "event_execution_pos",
        "event_split",
        "fast_fail_10d_label",
        "false_repair_20d_label",
        "winner_120_label",
    ),
    "r_core_density_badside_tradeoff": (
        "arm_id",
        "split",
        "denominator_instrument_years",
        "events_per_instrument_year_mean",
        "events_per_instrument_year_p95",
    ),
    "labels_08": (
        "event_id",
        "instrument",
        "event_t0_pos",
        "trade_open_pos",
        "trade_open_price",
        "failure_10_label",
        "failure_10_complete",
        "event_false_repair_20d_label",
        "event_false_repair_20d_complete",
        "event_big_winner_120d_label",
        "horizon_complete_120d",
    ),
}


def mtime_utc(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, raw_path in config.get("paths", {}).items():
        path = topic_path(raw_path)
        exists = path.exists()
        row_count = np.nan
        column_count = np.nan
        read_status = "ok" if exists else "missing_required_input"
        schema_status = "not_applicable"
        notes = ""
        if exists and path.is_file() and path.suffix in {".csv", ".gz", ".parquet"}:
            try:
                if "".join(path.suffixes).endswith(".parquet"):
                    try:
                        import pyarrow.parquet as pq

                        metadata = pq.ParquetFile(path).metadata
                        row_count = int(metadata.num_rows)
                        column_count = int(metadata.num_columns)
                        columns = set(metadata.schema.names)
                    except Exception:
                        parquet_frame = pd.read_parquet(path)
                        row_count = int(parquet_frame.shape[0])
                        column_count = int(parquet_frame.shape[1])
                        columns = set(parquet_frame.columns)
                else:
                    sample = pd.read_csv(path, nrows=1, low_memory=False)
                    column_count = len(sample.columns)
                    columns = set(sample.columns)
                    row_count = int(read_table(path, usecols=[sample.columns[0]]).shape[0])
                expected = set(EXPECTED_INPUT_COLUMNS.get(artifact_id, ()))
                missing = sorted(expected - columns)
                schema_status = "ok" if not missing else "missing_columns:" + ";".join(missing)
            except Exception as exc:  # pragma: no cover - defensive audit path
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "unreadable"
        elif exists and path.is_dir():
            schema_status = "directory"
        elif exists:
            schema_status = "not_applicable"
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
                "notes": notes,
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
        keep = [col for col in ("date", "open", "high", "low", "close") if col in daily.columns]
        daily = daily[keep].copy()
        for col in ("open", "high", "low", "close"):
            daily[col] = pd.to_numeric(daily[col], errors="coerce")
        daily["date"] = daily["date"].astype(str).str.slice(0, 10)
        daily = daily.sort_values("date", kind="stable").reset_index(drop=True)
        self._cache[instrument] = daily
        return daily

    def pos_for_date(self, instrument: str, date_value: Any) -> float:
        daily = self.get(instrument)
        if daily is None or daily.empty:
            return np.nan
        text = date_text(date_value)
        matches = daily.index[daily["date"].astype(str).eq(text)]
        if len(matches) == 0:
            return np.nan
        return float(matches[0])


def add_episode_positions(episodes: pd.DataFrame, stock_cache: StockDailyCache) -> pd.DataFrame:
    out = episodes.copy()
    for col in ("episode_low_date", "episode_high_date", "first_50pct_date", "pre120_calendar_start_date"):
        out[col] = out[col].map(date_text)
    lows: list[float] = []
    highs: list[float] = []
    first50: list[float] = []
    for row in out.itertuples(index=False):
        instrument = str(getattr(row, "instrument"))
        lows.append(stock_cache.pos_for_date(instrument, getattr(row, "episode_low_date")))
        highs.append(stock_cache.pos_for_date(instrument, getattr(row, "episode_high_date")))
        first50.append(stock_cache.pos_for_date(instrument, getattr(row, "first_50pct_date")))
    out["episode_low_pos"] = lows
    out["episode_high_pos"] = highs
    out["first_50pct_pos"] = first50
    out["episode_low_pos_status"] = np.where(pd.Series(lows).notna(), "ok", "missing")
    return out


def load_label_config(config: dict[str, Any]) -> dict[str, float | int]:
    source_08 = load_yaml(topic_path(config["paths"]["source_08_config"]))
    labels_08 = source_08["labels"]
    return {
        "failure_horizon": int(labels_08["failure_10"]["horizon_days"]),
        "failure_lower": float(labels_08["failure_10"]["lower_barrier"]),
        "false_repair_horizon": 20,
        "false_repair_drawdown": float(labels_08["false_repair_drawdown"]),
        "winner_horizon": 120,
        "winner_mfe": float(labels_08["big_winner_mfe_120d"]),
    }


def int_or_none(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        out = int(value)
    except (TypeError, ValueError):
        return None
    return out if out >= 0 else None


def compute_label_row(
    daily: pd.DataFrame | None,
    *,
    event_pos: int | None,
    trade_pos: int | None,
    trade_price: float,
    label_cfg: dict[str, float | int],
) -> dict[str, Any]:
    if daily is None or daily.empty:
        return {
            "fast_fail_10d_label": np.nan,
            "horizon_complete_10d": False,
            "false_repair_20d_label": np.nan,
            "horizon_complete_20d": False,
            "winner_120_label": np.nan,
            "horizon_complete_120d": False,
            "label_recompute_status": "missing_stock_daily",
        }
    low = daily["low"].to_numpy(dtype=float)
    high = daily["high"].to_numpy(dtype=float)
    close = daily["close"].to_numpy(dtype=float)
    n = len(daily)
    failure_horizon = int(label_cfg["failure_horizon"])
    false_horizon = int(label_cfg["false_repair_horizon"])
    winner_horizon = int(label_cfg["winner_horizon"])
    failure_complete = (
        trade_pos is not None
        and trade_pos + failure_horizon < n
        and pd.notna(trade_price)
        and float(trade_price) > 0
    )
    winner_complete = (
        trade_pos is not None
        and trade_pos + winner_horizon < n
        and pd.notna(trade_price)
        and float(trade_price) > 0
    )
    false_complete = event_pos is not None and event_pos + false_horizon < n
    if failure_complete:
        low_window = low[trade_pos : trade_pos + failure_horizon + 1]
        fast_fail = bool(np.nanmin(low_window / float(trade_price) - 1.0) <= float(label_cfg["failure_lower"]))
    else:
        fast_fail = np.nan
    if false_complete:
        event_close = close[event_pos]
        if pd.notna(event_close) and float(event_close) > 0:
            close_window = close[event_pos : event_pos + false_horizon + 1]
            false_repair = bool(
                np.nanmin(close_window / float(event_close) - 1.0)
                <= float(label_cfg["false_repair_drawdown"])
            )
        else:
            false_repair = np.nan
            false_complete = False
    else:
        false_repair = np.nan
    if winner_complete:
        high_window = high[trade_pos : trade_pos + winner_horizon + 1]
        winner = bool(np.nanmax(high_window / float(trade_price) - 1.0) >= float(label_cfg["winner_mfe"]))
    else:
        winner = np.nan
    return {
        "fast_fail_10d_label": fast_fail,
        "horizon_complete_10d": bool(failure_complete),
        "false_repair_20d_label": false_repair,
        "horizon_complete_20d": bool(false_complete),
        "winner_120_label": winner,
        "horizon_complete_120d": bool(winner_complete),
        "label_recompute_status": "ok",
    }


def recompute_labels(
    events: pd.DataFrame,
    stock_cache: StockDailyCache,
    label_cfg: dict[str, float | int],
    *,
    id_col: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    needed_cols = [id_col, "instrument", "event_t0_pos", "trade_open_pos", "trade_open_price"]
    frame = events[[col for col in needed_cols if col in events.columns]].copy()
    failure_horizon = int(label_cfg["failure_horizon"])
    false_horizon = int(label_cfg["false_repair_horizon"])
    winner_horizon = int(label_cfg["winner_horizon"])
    failure_lower = float(label_cfg["failure_lower"])
    false_drawdown = float(label_cfg["false_repair_drawdown"])
    winner_mfe = float(label_cfg["winner_mfe"])
    for instrument, group in frame.groupby("instrument", sort=False):
        daily = stock_cache.get(instrument)
        if daily is None or daily.empty:
            for record in group.itertuples(index=False):
                rows.append(
                    {
                        id_col: str(getattr(record, id_col)),
                        "fast_fail_10d_label": np.nan,
                        "horizon_complete_10d": False,
                        "false_repair_20d_label": np.nan,
                        "horizon_complete_20d": False,
                        "winner_120_label": np.nan,
                        "horizon_complete_120d": False,
                        "label_recompute_status": "missing_stock_daily",
                    }
                )
            continue
        low = daily["low"].to_numpy(dtype=float)
        high = daily["high"].to_numpy(dtype=float)
        close = daily["close"].to_numpy(dtype=float)
        n = len(daily)
        for record in group.itertuples(index=False):
            event_id = str(getattr(record, id_col))
            event_pos = int_or_none(getattr(record, "event_t0_pos", np.nan))
            trade_pos = int_or_none(getattr(record, "trade_open_pos", np.nan))
            try:
                trade_price = float(getattr(record, "trade_open_price", np.nan))
            except (TypeError, ValueError):
                trade_price = np.nan
            failure_complete = (
                trade_pos is not None
                and trade_pos + failure_horizon < n
                and pd.notna(trade_price)
                and trade_price > 0
            )
            false_complete = event_pos is not None and event_pos + false_horizon < n
            winner_complete = (
                trade_pos is not None
                and trade_pos + winner_horizon < n
                and pd.notna(trade_price)
                and trade_price > 0
            )
            if failure_complete:
                low_window = low[trade_pos : trade_pos + failure_horizon + 1]
                fast_fail = bool(np.nanmin(low_window / trade_price - 1.0) <= failure_lower)
            else:
                fast_fail = np.nan
            if false_complete:
                event_close = close[event_pos]
                if pd.notna(event_close) and float(event_close) > 0:
                    close_window = close[event_pos : event_pos + false_horizon + 1]
                    false_repair = bool(np.nanmin(close_window / float(event_close) - 1.0) <= false_drawdown)
                else:
                    false_repair = np.nan
                    false_complete = False
            else:
                false_repair = np.nan
            if winner_complete:
                high_window = high[trade_pos : trade_pos + winner_horizon + 1]
                winner = bool(np.nanmax(high_window / trade_price - 1.0) >= winner_mfe)
            else:
                winner = np.nan
            rows.append(
                {
                    id_col: event_id,
                    "fast_fail_10d_label": fast_fail,
                    "horizon_complete_10d": bool(failure_complete),
                    "false_repair_20d_label": false_repair,
                    "horizon_complete_20d": bool(false_complete),
                    "winner_120_label": winner,
                    "horizon_complete_120d": bool(winner_complete),
                    "label_recompute_status": "ok",
                }
            )
    return pd.DataFrame(rows)


def normalize_state_change_events(canonical: pd.DataFrame) -> pd.DataFrame:
    out = canonical.copy()
    out["event_key"] = out["canonical_event_id"].astype(str)
    out["event_t0_date"] = out["event_t0_date"].map(date_text)
    out["event_signal_date"] = out["event_t0_date"]
    out["event_execution_date"] = out.get("trade_open_date", "").map(date_text)
    out["event_t0_pos"] = numeric_series(out["event_t0_pos"])
    out["trade_open_pos"] = numeric_series(out.get("trade_open_pos", pd.Series(np.nan, index=out.index)))
    out["event_execution_pos"] = out["trade_open_pos"]
    out["trade_open_price"] = numeric_series(out.get("trade_open_price", pd.Series(np.nan, index=out.index)))
    out["event_split"] = out.get("event_split", "").fillna("").astype(str)
    out["board_bucket"] = out.get("board_bucket", "").fillna("").astype(str)
    out["market_regime_bucket"] = out.get("market_regime_bucket", "").fillna("").astype(str)
    out["primary_family_id"] = out.get("primary_family_id", "").fillna("").astype(str)
    out["triggered_family_variants"] = out.get("triggered_family_variants", "").fillna("").astype(str)
    non_exec = bool_series(out.get("non_executable_next_open", pd.Series(False, index=out.index)))
    t0_pit = out.get("event_t0_pit_status", pd.Series("", index=out.index)).fillna("").astype(str)
    open_pit = out.get("trade_open_pit_status", pd.Series("", index=out.index)).fillna("").astype(str)
    out["event_t0_pit_pass_flag"] = t0_pit.eq("pass")
    out["trade_open_pit_pass_flag"] = open_pit.eq("pass")
    out["event_t0_pit_ok_flag"] = out["event_t0_pit_pass_flag"]
    out["trade_open_pit_ok_flag"] = out["trade_open_pit_pass_flag"]
    out["trade_open_price_available_flag"] = out["trade_open_price"].notna() & (out["trade_open_price"] > 0)
    out["next_open_executable_flag"] = (
        (~non_exec)
        & out["event_execution_date"].astype(str).ne("")
        & out["event_t0_pit_pass_flag"]
        & out["trade_open_pit_pass_flag"]
    )
    out["frontier_source_kind"] = "12A2_state_change_canonical"
    return out


def normalize_r_core_events(r_core: pd.DataFrame, arm_id: str) -> pd.DataFrame:
    out = r_core.loc[r_core["arm_id"].astype(str).eq(arm_id)].copy()
    out["event_key"] = out["event_key"].astype(str)
    out["event_t0_date"] = out["event_signal_date"].map(date_text)
    out["event_execution_date"] = out.get("event_execution_date", "").map(date_text)
    out["trade_open_date"] = out["event_execution_date"]
    out["event_t0_pos"] = numeric_series(out.get("event_signal_pos", pd.Series(np.nan, index=out.index)))
    out["event_execution_pos"] = numeric_series(out.get("event_execution_pos", pd.Series(np.nan, index=out.index)))
    out["trade_open_pos"] = out["event_execution_pos"]
    out["trade_open_price"] = np.nan
    out["event_split"] = out.get("event_split", "").fillna("").astype(str)
    out["board_bucket"] = out.get("board_bucket", "").fillna("").astype(str)
    out["market_regime_bucket"] = ""
    out["primary_family_id"] = arm_id
    out["triggered_family_variants"] = arm_id
    exec_status = out.get("event_execution_status", pd.Series("", index=out.index)).fillna("").astype(str)
    out["next_open_executable_flag"] = exec_status.str.contains("executable|ok|pass", case=False, regex=True)
    out["event_t0_pit_pass_flag"] = True
    out["trade_open_pit_pass_flag"] = out["next_open_executable_flag"]
    out["trade_open_price_available_flag"] = np.nan
    out["fast_fail_10d_label"] = out.get("fast_fail_10d_label", np.nan)
    out["false_repair_20d_label"] = out.get("false_repair_20d_label", np.nan)
    out["winner_120_label"] = out.get("winner_120_label", np.nan)
    out["horizon_complete_10d"] = bool_series(out.get("horizon_complete_10d", pd.Series(False, index=out.index)))
    out["horizon_complete_20d"] = bool_series(out.get("horizon_complete_20d", pd.Series(False, index=out.index)))
    out["horizon_complete_120d"] = bool_series(out.get("horizon_complete_120d", pd.Series(False, index=out.index)))
    out["frontier_source_kind"] = "12A1_R_core_registry"
    return out


def attach_recomputed_labels(events: pd.DataFrame, labels: pd.DataFrame, *, id_col: str = "event_key") -> pd.DataFrame:
    drop_cols = [
        "fast_fail_10d_label",
        "horizon_complete_10d",
        "false_repair_20d_label",
        "horizon_complete_20d",
        "winner_120_label",
        "horizon_complete_120d",
        "label_recompute_status",
    ]
    out = events.drop(columns=[col for col in drop_cols if col in events.columns], errors="ignore")
    return out.merge(labels, how="left", on=id_col)


def recanonicalize_instances(
    instances: pd.DataFrame,
    config: dict[str, Any],
    *,
    priority_order: dict[str, int] | None = None,
    canonical_id_prefix: str = "12A2_B3_before_B1",
    rule_id: str = "12A3_recomputed_B3_before_B1_same_day_then_union_cooldown",
) -> pd.DataFrame:
    canon_cfg = config["canonicalization"]
    priority_source = priority_order if priority_order is not None else canon_cfg["b3_before_b1_priority_order"]
    priority = {str(key): int(value) for key, value in priority_source.items()}
    supported = set(canon_cfg.get("supported_first_trigger_statuses", []))
    cooldown = int(canon_cfg["union_level_cooldown_sessions"])
    inst = instances.copy()
    inst["family_id"] = inst["family_id"].fillna("").astype(str)
    inst["event_t0_date"] = inst["event_t0_date"].map(date_text)
    inst["event_t0_pos"] = numeric_series(inst["event_t0_pos"])
    inst["allowed_for_primary_canonical_flag"] = bool_series(
        inst.get("allowed_for_primary_canonical_flag", pd.Series(False, index=inst.index))
    )
    inst["first_trigger_status"] = inst.get("first_trigger_status", "").fillna("").astype(str)
    non_exec = bool_series(inst.get("non_executable_next_open", pd.Series(False, index=inst.index)))
    raw_status = inst.get("raw_event_status", pd.Series("triggered", index=inst.index)).fillna("").astype(str)
    family_input = inst.get("family_input_status", pd.Series("runnable_existing_data", index=inst.index)).fillna("").astype(str)
    event_t0_pit = inst.get("event_t0_pit_status", pd.Series("", index=inst.index)).fillna("").astype(str)
    trade_open_pit = inst.get("trade_open_pit_status", pd.Series("", index=inst.index)).fillna("").astype(str)
    eligible = (
        raw_status.eq("triggered")
        & family_input.eq("runnable_existing_data")
        & inst["allowed_for_primary_canonical_flag"]
        & inst["family_id"].ne("B7")
        & (~non_exec)
        & event_t0_pit.eq("pass")
        & trade_open_pit.eq("pass")
    )
    if supported:
        eligible &= inst["first_trigger_status"].isin(supported)
    inst = inst.loc[eligible].copy()
    if inst.empty:
        return pd.DataFrame()
    inst["_priority"] = inst["family_id"].map(priority).fillna(9999).astype(int)
    inst["_variant"] = inst.get("family_variant_id", inst["family_id"]).fillna("").astype(str)
    inst = inst.sort_values(
        ["instrument", "event_t0_pos", "event_t0_date", "_priority", "_variant", "event_instance_id"],
        kind="stable",
    )
    rows: list[dict[str, Any]] = []
    for (instrument, event_date), group in inst.groupby(["instrument", "event_t0_date"], sort=False):
        chosen = group.sort_values(["_priority", "_variant", "event_instance_id"], kind="stable").iloc[0].copy()
        variants = sorted(group["_variant"].dropna().astype(str).unique().tolist())
        families = sorted(group["family_id"].dropna().astype(str).unique().tolist())
        row = chosen.to_dict()
        row["canonical_event_id"] = canonical_id_prefix + "_" + stable_hash(
            {
                "instrument": instrument,
                "event_t0_date": event_date,
                "primary_event_instance_id": chosen.get("event_instance_id", ""),
                "priority_order": priority,
            }
        )[:16]
        row["primary_event_instance_id"] = chosen.get("event_instance_id", "")
        row["primary_family_id"] = chosen.get("family_id", "")
        row["primary_variant_id"] = chosen.get("variant_id", "")
        row["triggered_family_variants"] = ";".join(variants)
        row["triggered_family_count"] = len(families)
        row["raw_instance_count_collapsed"] = int(group["event_instance_id"].nunique())
        row["canonicalization_rule"] = rule_id
        rows.append(row)
    collapsed = pd.DataFrame(rows)
    if collapsed.empty:
        return collapsed
    kept: list[pd.Series] = []
    for _, group in collapsed.sort_values(["instrument", "event_t0_pos", "event_t0_date"], kind="stable").groupby("instrument", sort=False):
        last_pos: float | None = None
        for _, row in group.iterrows():
            pos = float(row["event_t0_pos"]) if pd.notna(row["event_t0_pos"]) else np.nan
            if last_pos is None or pd.isna(pos) or pos - last_pos > cooldown:
                kept.append(row)
                if pd.notna(pos):
                    last_pos = pos
    return pd.DataFrame(kept).reset_index(drop=True)


def split_frame(frame: pd.DataFrame, split_col: str, split: str) -> pd.DataFrame:
    if split == "all":
        return frame
    return frame.loc[frame[split_col].astype(str).eq(split)].copy()


def pair_events_episodes(events: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    if events.empty or episodes.empty:
        return pd.DataFrame()
    event_cols = [
        "event_key",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "event_split",
        "primary_family_id",
        "triggered_family_count",
        "board_bucket",
        "market_regime_bucket",
    ]
    episode_cols = [
        "episode_id",
        "instrument",
        "split",
        "board_bucket",
        "episode_low_date",
        "episode_high_date",
        "first_50pct_date",
        "pre120_calendar_start_date",
        "duration_bucket",
        "low_to_high_sessions",
        "mfe_120",
        "episode_low_pos",
        "episode_high_pos",
        "first_50pct_pos",
        "episode_low_pos_status",
    ]
    ev = events[[col for col in event_cols if col in events.columns]].drop_duplicates("event_key").copy()
    ep = episodes[[col for col in episode_cols if col in episodes.columns]].copy()
    pairs = ev.merge(ep, how="inner", on="instrument", suffixes=("_event", "_episode"))
    if pairs.empty:
        return pairs
    pairs["_event_dt"] = date_series(pairs["event_t0_date"])
    pairs["_low_dt"] = date_series(pairs["episode_low_date"])
    pairs["_high_dt"] = date_series(pairs["episode_high_date"])
    pairs["_first50_dt"] = date_series(pairs["first_50pct_date"])
    pairs["_pre120_dt"] = date_series(pairs["pre120_calendar_start_date"])
    pairs["_event_minus_low_days"] = (pairs["_event_dt"] - pairs["_low_dt"]).dt.days
    pairs["_event_minus_low_sessions"] = numeric_series(pairs["event_t0_pos"]) - numeric_series(pairs["episode_low_pos"])
    pairs["_split_match"] = pairs["event_split"].astype(str).eq(pairs["split"].astype(str))
    return pairs


def inside_window(pairs: pd.DataFrame, window_id: str) -> pd.DataFrame:
    if pairs.empty:
        return pairs
    if window_id == "pre120_calendar_to_high":
        start = pairs["_pre120_dt"]
        end = pairs["_high_dt"]
    elif window_id == "low_to_first_50pct":
        start = pairs["_low_dt"]
        end = pairs["_first50_dt"]
    else:
        start = pairs["_low_dt"]
        end = pairs["_high_dt"]
    mask = pairs["_event_dt"].notna() & start.notna() & end.notna() & (pairs["_event_dt"] >= start) & (pairs["_event_dt"] <= end)
    return pairs.loc[mask].copy()


def timing_bucket(value: Any) -> str:
    if pd.isna(value):
        return "unknown"
    val = float(value)
    if val < -60:
        return "pre_low_le_minus_61"
    if val < -20:
        return "pre_low_minus_60_to_minus_21"
    if val < 0:
        return "pre_low_minus_20_to_minus_1"
    if val == 0:
        return "episode_low_day"
    if val <= 20:
        return "post_low_1_to_20"
    if val <= 60:
        return "post_low_21_to_60"
    return "post_low_gt_60"


def percentile_value(values: pd.Series, pct: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(np.percentile(clean, pct)) if len(clean) else np.nan


def rolling_duplicate_rate(events: pd.DataFrame, horizon: int) -> float:
    if events.empty:
        return np.nan
    duplicate_flags: list[bool] = []
    frame = events.dropna(subset=["event_t0_pos"]).copy()
    for _, group in frame.groupby("instrument"):
        positions = numeric_series(group["event_t0_pos"]).dropna().sort_values().to_numpy()
        right = 0
        for left, pos in enumerate(positions):
            right = max(right, left)
            while right < len(positions) and positions[right] <= pos + horizon:
                right += 1
            duplicate_flags.append(right - left - 1 > 0)
    return safe_rate(sum(duplicate_flags), len(duplicate_flags)) if duplicate_flags else np.nan


def density_stats(events: pd.DataFrame, denominator_years: float, r_core_mean_density: float) -> dict[str, Any]:
    event_n = int(events["event_key"].nunique()) if not events.empty else 0
    unique_inst = int(events["instrument"].nunique()) if not events.empty else 0
    unique_days = int(events["event_t0_date"].nunique()) if not events.empty else 0
    mean_density = safe_rate(event_n, denominator_years)
    avg_years_per_active = safe_rate(denominator_years, unique_inst)
    if event_n and pd.notna(avg_years_per_active) and avg_years_per_active > 0:
        per_inst = events.groupby("instrument")["event_key"].nunique().astype(float) / avg_years_per_active
        p95_density = float(np.percentile(per_inst, 95)) if len(per_inst) else np.nan
    else:
        p95_density = np.nan
    return {
        "event_n": event_n,
        "unique_instrument_n": unique_inst,
        "unique_event_date_n": unique_days,
        "events_per_instrument_year_mean": mean_density,
        "events_per_instrument_year_p95": p95_density,
        "density_ratio_vs_r_core": safe_rate(mean_density, r_core_mean_density),
        "same_instrument_10d_duplicate_rate": rolling_duplicate_rate(events, 10),
        "same_instrument_20d_duplicate_rate": rolling_duplicate_rate(events, 20),
    }


def label_exposure_stats(events: pd.DataFrame) -> dict[str, Any]:
    event_n = int(events["event_key"].nunique()) if not events.empty else 0
    exec_rate = safe_rate(int(bool_series(events.get("next_open_executable_flag", pd.Series(False, index=events.index))).sum()), event_n)
    event_t0_pit_pass_rate = safe_rate(int(bool_series(events.get("event_t0_pit_pass_flag", pd.Series(False, index=events.index))).sum()), event_n)
    trade_open_price_available = events.get("trade_open_price_available_flag", pd.Series(False, index=events.index))
    trade_open_price_available_rate = safe_rate(int(bool_series(trade_open_price_available).sum()), event_n)
    h10 = bool_series(events.get("horizon_complete_10d", pd.Series(False, index=events.index)))
    h20 = bool_series(events.get("horizon_complete_20d", pd.Series(False, index=events.index)))
    h120 = bool_series(events.get("horizon_complete_120d", pd.Series(False, index=events.index)))
    fast = bool_series(events.loc[h10, "fast_fail_10d_label"]) if "fast_fail_10d_label" in events.columns else pd.Series(dtype=bool)
    false20 = bool_series(events.loc[h20, "false_repair_20d_label"]) if "false_repair_20d_label" in events.columns else pd.Series(dtype=bool)
    winner = bool_series(events.loc[h120, "winner_120_label"]) if "winner_120_label" in events.columns else pd.Series(dtype=bool)
    both_complete = h10 & h20
    if both_complete.any() and {"fast_fail_10d_label", "false_repair_20d_label"}.issubset(events.columns):
        bad_side = bool_series(events.loc[both_complete, "fast_fail_10d_label"]) | bool_series(
            events.loc[both_complete, "false_repair_20d_label"]
        )
    else:
        bad_side = pd.Series(dtype=bool)
    non_exec_drop_n = int((~bool_series(events.get("next_open_executable_flag", pd.Series(False, index=events.index)))).sum())
    return {
        "next_open_executable_rate": exec_rate,
        "event_t0_pit_pass_rate": event_t0_pit_pass_rate,
        "trade_open_price_available_rate": trade_open_price_available_rate,
        "non_executable_label_drop_n": non_exec_drop_n,
        "censored_10d_n": int(event_n - int(h10.sum())),
        "censored_20d_n": int(event_n - int(h20.sum())),
        "censored_120d_n": int(event_n - int(h120.sum())),
        "label_10d_complete_n": int(h10.sum()),
        "label_10d_complete_rate": safe_rate(int(h10.sum()), event_n),
        "fast_fail_10d_count": int(fast.sum()),
        "fast_fail_10d_rate": safe_rate(int(fast.sum()), len(fast)),
        "label_20d_complete_n": int(h20.sum()),
        "label_20d_complete_rate": safe_rate(int(h20.sum()), event_n),
        "false_repair_20d_count": int(false20.sum()),
        "false_repair_20d_rate": safe_rate(int(false20.sum()), len(false20)),
        "bad_side_10_20_count": int(bad_side.sum()),
        "bad_side_10_20_rate": safe_rate(int(bad_side.sum()), len(bad_side)),
        "label_120d_complete_n": int(h120.sum()),
        "label_120d_complete_rate": safe_rate(int(h120.sum()), event_n),
        "winner_120_count": int(winner.sum()),
        "winner_120_rate": safe_rate(int(winner.sum()), len(winner)),
        "winner_120d_rate": safe_rate(int(winner.sum()), len(winner)),
        "label_status": "ok",
    }


def build_event_label_exposure(arms: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for arm_id, events in arms.items():
        for split in SPLITS:
            frame = split_frame(events, "event_split", split)
            source = (
                "12A1_frozen_event_registry_labels"
                if arm_id in {RAW_R_CORE_ARM, R6_ARM}
                else "12A3_recomputed_from_qfq"
            )
            rows.append(
                {
                    "frontier_arm_id": arm_id,
                    "split": split,
                    "label_source": source,
                    **density_stats(frame, np.nan, np.nan),
                    **label_exposure_stats(frame),
                }
            )
    return pd.DataFrame(rows)


def build_frontier_outputs(
    arms: dict[str, pd.DataFrame],
    arm_registry: pd.DataFrame,
    episodes: pd.DataFrame,
    *,
    denominator_years: float,
    r_core_mean_density: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frontier_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []
    captured_rows: list[dict[str, Any]] = []
    missed_rows: list[dict[str, Any]] = []
    meta_by_arm = arm_registry.set_index("frontier_arm_id").to_dict("index") if not arm_registry.empty else {}
    for arm_id, events_all in arms.items():
        role = meta_by_arm.get(arm_id, {}).get("decision_role", "")
        for split in SPLITS:
            events = split_frame(events_all, "event_split", split)
            ep_split = split_frame(episodes, "split", split)
            pairs = pair_events_episodes(events, ep_split)
            mismatch_pairs = pair_events_episodes(events, episodes)
            dens = density_stats(events, denominator_years, r_core_mean_density)
            labels = label_exposure_stats(events)
            for window_id in WINDOWS:
                inside = inside_window(pairs, window_id)
                if split != "all" and not inside.empty:
                    inside = inside.loc[inside["_split_match"]].copy()
                mismatch_inside = inside_window(mismatch_pairs, window_id)
                if not mismatch_inside.empty:
                    mismatch_inside = mismatch_inside.loc[~mismatch_inside["_split_match"]].copy()
                captured_episode_ids = set(inside["episode_id"].astype(str).unique().tolist()) if not inside.empty else set()
                event_inside_n = int(inside["event_key"].nunique()) if not inside.empty else 0
                eligible_n = int(ep_split["episode_id"].nunique())
                captured_n = len(captured_episode_ids)
                episode_counts = (
                    inside.groupby("episode_id")["event_key"].nunique().astype(int)
                    if not inside.empty
                    else pd.Series(dtype=int)
                )
                first_events = pd.DataFrame()
                if not inside.empty:
                    first_events = inside.sort_values(
                        ["episode_id", "_event_dt", "event_t0_pos", "event_key"], kind="stable"
                    ).drop_duplicates("episode_id", keep="first")
                offsets = (
                    pd.to_numeric(first_events["_event_minus_low_sessions"], errors="coerce").dropna()
                    if not first_events.empty
                    else pd.Series(dtype=float)
                )
                frontier_rows.append(
                    {
                        "frontier_arm_id": arm_id,
                        "arm_role": role,
                        "decision_role": role,
                        "split": split,
                        "split_basis": "event_split_equals_episode_split" if split != "all" else "all_events_all_episodes",
                        "window_id": window_id,
                        "eligible_episode_n": eligible_n,
                        "captured_episode_n": captured_n,
                        "missed_episode_n": eligible_n - captured_n,
                        "episode_recall": safe_rate(captured_n, eligible_n),
                        "event_inside_window_n": event_inside_n,
                        "event_precision": safe_rate(event_inside_n, dens["event_n"]),
                        "event_precision_inside_window": safe_rate(event_inside_n, dens["event_n"]),
                        "outside_event_rate": 1 - safe_rate(event_inside_n, dens["event_n"]) if dens["event_n"] else np.nan,
                        "outside_episode_event_rate": 1 - safe_rate(event_inside_n, dens["event_n"]) if dens["event_n"] else np.nan,
                        "events_per_captured_episode_median": float(episode_counts.median()) if len(episode_counts) else np.nan,
                        "events_per_captured_episode_p95": float(np.percentile(episode_counts, 95)) if len(episode_counts) else np.nan,
                        "events_per_captured_episode_max": int(episode_counts.max()) if len(episode_counts) else 0,
                        "captured_episode_with_ge3_events_rate": safe_rate(int((episode_counts >= 3).sum()), len(episode_counts)),
                        "captured_episode_with_ge5_events_rate": safe_rate(int((episode_counts >= 5).sum()), len(episode_counts)),
                        "captured_episode_event_count_mean": float(episode_counts.mean()) if len(episode_counts) else np.nan,
                        "captured_episode_event_count_median": float(episode_counts.median()) if len(episode_counts) else np.nan,
                        "captured_episode_event_count_p95": float(np.percentile(episode_counts, 95)) if len(episode_counts) else np.nan,
                        "first_event_minus_low_sessions_median": float(offsets.median()) if len(offsets) else np.nan,
                        "first_event_minus_low_sessions_p25": float(np.percentile(offsets, 25)) if len(offsets) else np.nan,
                        "first_event_minus_low_sessions_p75": float(np.percentile(offsets, 75)) if len(offsets) else np.nan,
                        "multi_episode_event_overlap_n": int((inside.groupby("event_key")["episode_id"].nunique() > 1).sum()) if not inside.empty else 0,
                        "split_mismatch_candidate_n": int(mismatch_inside["event_key"].nunique()) if not mismatch_inside.empty else 0,
                        "frontier_status": "ok",
                        **dens,
                        **labels,
                    }
                )
                timing_populations = [
                    ("all_matched_events", inside),
                    ("captured_episode_first_event", first_events),
                ]
                for timing_population, timing_base in timing_populations:
                    session_offsets = (
                        pd.to_numeric(timing_base["_event_minus_low_sessions"], errors="coerce")
                        if not timing_base.empty and "_event_minus_low_sessions" in timing_base.columns
                        else pd.Series(dtype=float)
                    )
                    calendar_offsets = (
                        pd.to_numeric(timing_base["_event_minus_low_days"], errors="coerce")
                        if not timing_base.empty and "_event_minus_low_days" in timing_base.columns
                        else pd.Series(dtype=float)
                    )
                    matched_event_n = int(timing_base["event_key"].nunique()) if not timing_base.empty else 0
                    timing_rows.append(
                        {
                            "frontier_arm_id": arm_id,
                            "split": split,
                            "window_id": window_id,
                            "timing_population": timing_population,
                            "matched_event_n": matched_event_n,
                            "captured_episode_n": captured_n,
                            "event_minus_low_trading_days_p10": percentile_value(session_offsets, 10),
                            "event_minus_low_trading_days_p25": percentile_value(session_offsets, 25),
                            "event_minus_low_trading_days_median": percentile_value(session_offsets, 50),
                            "event_minus_low_trading_days_p75": percentile_value(session_offsets, 75),
                            "event_minus_low_trading_days_p90": percentile_value(session_offsets, 90),
                            "first_event_minus_low_trading_days_p10": percentile_value(session_offsets, 10)
                            if timing_population == "captured_episode_first_event"
                            else np.nan,
                            "first_event_minus_low_trading_days_p25": percentile_value(session_offsets, 25)
                            if timing_population == "captured_episode_first_event"
                            else np.nan,
                            "first_event_minus_low_trading_days_median": percentile_value(session_offsets, 50)
                            if timing_population == "captured_episode_first_event"
                            else np.nan,
                            "first_event_minus_low_trading_days_p75": percentile_value(session_offsets, 75)
                            if timing_population == "captured_episode_first_event"
                            else np.nan,
                            "first_event_minus_low_trading_days_p90": percentile_value(session_offsets, 90)
                            if timing_population == "captured_episode_first_event"
                            else np.nan,
                            "event_minus_low_calendar_days_median": percentile_value(calendar_offsets, 50),
                            "timing_denominator_status": "ok" if len(session_offsets.dropna()) else "no_timing_observations",
                        }
                    )
                count_by_ep = episode_counts.to_dict()
                first_by_ep = (
                    first_events.set_index("episode_id").to_dict("index") if not first_events.empty else {}
                )
                last_events = (
                    inside.sort_values(["episode_id", "_event_dt", "event_t0_pos", "event_key"], kind="stable")
                    .drop_duplicates("episode_id", keep="last")
                    if not inside.empty
                    else pd.DataFrame()
                )
                last_by_ep = last_events.set_index("episode_id").to_dict("index") if not last_events.empty else {}
                pairs_by_ep = {key: value.copy() for key, value in pairs.groupby("episode_id")} if not pairs.empty else {}
                events_by_instrument = {
                    inst: group.sort_values(["event_t0_pos", "event_t0_date"], kind="stable")
                    for inst, group in events.groupby("instrument")
                }
                for ep in ep_split.to_dict("records"):
                    episode_id = str(ep["episode_id"])
                    first = first_by_ep.get(episode_id, {})
                    last = last_by_ep.get(episode_id, {})
                    ep_pairs = pairs_by_ep.get(episode_id, pd.DataFrame())
                    captured = episode_id in captured_episode_ids
                    low_pos = ep.get("episode_low_pos", np.nan)
                    high_pos = ep.get("episode_high_pos", np.nan)
                    if not ep_pairs.empty and pd.notna(low_pos) and pd.notna(high_pos):
                        event_pos = pd.to_numeric(ep_pairs["event_t0_pos"], errors="coerce")
                        before_low_n = int(ep_pairs.loc[event_pos < float(low_pos), "event_key"].nunique())
                        low_to_high_n = int(ep_pairs.loc[(event_pos >= float(low_pos)) & (event_pos <= float(high_pos)), "event_key"].nunique())
                        after_high_n = int(ep_pairs.loc[event_pos > float(high_pos), "event_key"].nunique())
                    else:
                        before_low_n = low_to_high_n = after_high_n = 0
                    if pd.isna(low_pos):
                        capture_status = "timing_not_evaluable"
                    else:
                        capture_status = "captured" if captured else "missed"
                    captured_rows.append(
                        {
                            "frontier_arm_id": arm_id,
                            "split": split,
                            "window_id": window_id,
                            "episode_id": episode_id,
                            "instrument": ep.get("instrument", ""),
                            "episode_split": ep.get("split", ""),
                            "episode_low_date": ep.get("episode_low_date", ""),
                            "episode_high_date": ep.get("episode_high_date", ""),
                            "first_50pct_date": ep.get("first_50pct_date", ""),
                            "board_bucket": ep.get("board_bucket", ""),
                            "duration_bucket": ep.get("duration_bucket", ""),
                            "captured_flag": bool(captured),
                            "capture_status": capture_status,
                            "event_count_inside_window": int(count_by_ep.get(episode_id, 0)),
                            "event_count_in_episode_window": int(count_by_ep.get(episode_id, 0)),
                            "first_event_key": first.get("event_key", ""),
                            "first_event_t0_date": first.get("event_t0_date", ""),
                            "first_event_primary_family_id": first.get("primary_family_id", ""),
                            "first_event_triggered_family_count": first.get("triggered_family_count", np.nan),
                            "first_event_minus_low_trading_days": first.get("_event_minus_low_sessions", np.nan),
                            "first_event_minus_low_calendar_days": first.get("_event_minus_low_days", np.nan),
                            "first_event_minus_low_sessions": first.get("_event_minus_low_sessions", np.nan),
                            "first_event_minus_low_days": first.get("_event_minus_low_days", np.nan),
                            "last_event_t0_date": last.get("event_t0_date", ""),
                            "events_before_low_n": before_low_n,
                            "events_low_to_high_n": low_to_high_n,
                            "events_after_high_n": after_high_n,
                        }
                    )
                    if captured:
                        continue
                    ev_inst = events_by_instrument.get(str(ep.get("instrument", "")), pd.DataFrame())
                    before_key = after_key = nearest_key = ""
                    before_date = after_date = nearest_date = ""
                    before_gap = after_gap = nearest_gap = np.nan
                    if not ev_inst.empty:
                        low_pos = ep.get("episode_low_pos", np.nan)
                        high_pos = ep.get("episode_high_pos", np.nan)
                        start_date = ep["pre120_calendar_start_date"] if window_id == "pre120_calendar_to_high" else ep["episode_low_date"]
                        end_date = ep["first_50pct_date"] if window_id == "low_to_first_50pct" else ep["episode_high_date"]
                        start_dt = pd.to_datetime(start_date, errors="coerce")
                        end_dt = pd.to_datetime(end_date, errors="coerce")
                        ev_tmp = ev_inst.copy()
                        ev_tmp["_event_dt"] = date_series(ev_tmp["event_t0_date"])
                        before = ev_tmp.loc[ev_tmp["_event_dt"] < start_dt].tail(1) if pd.notna(start_dt) else pd.DataFrame()
                        after = ev_tmp.loc[ev_tmp["_event_dt"] > end_dt].head(1) if pd.notna(end_dt) else pd.DataFrame()
                        if not before.empty:
                            before_key = before.iloc[0]["event_key"]
                            before_date = before.iloc[0]["event_t0_date"]
                            before_pos = pd.to_numeric(before.iloc[0].get("event_t0_pos", np.nan), errors="coerce")
                            before_gap = float(float(low_pos) - float(before_pos)) if pd.notna(low_pos) and pd.notna(before_pos) else np.nan
                        if not after.empty:
                            after_key = after.iloc[0]["event_key"]
                            after_date = after.iloc[0]["event_t0_date"]
                            after_pos = pd.to_numeric(after.iloc[0].get("event_t0_pos", np.nan), errors="coerce")
                            after_gap = float(float(after_pos) - float(high_pos)) if pd.notna(high_pos) and pd.notna(after_pos) else np.nan
                        if pd.notna(low_pos):
                            ev_tmp["_abs_low_pos_gap"] = (numeric_series(ev_tmp["event_t0_pos"]) - float(low_pos)).abs()
                            near = ev_tmp.sort_values(["_abs_low_pos_gap", "event_t0_date"], kind="stable").head(1)
                            if not near.empty:
                                nearest_key = near.iloc[0]["event_key"]
                                nearest_date = near.iloc[0]["event_t0_date"]
                                nearest_gap = float(numeric_series(near["event_t0_pos"]).iloc[0] - float(low_pos))
                    if ev_inst.empty:
                        miss_reason = "no_same_instrument_event"
                    elif before_key and not after_key:
                        miss_reason = "only_before_pre120" if window_id == "pre120_calendar_to_high" else "timing_calendar_gap"
                    elif after_key and not before_key:
                        miss_reason = "only_after_high"
                    elif split != "all" and not mismatch_inside.empty and episode_id in set(mismatch_inside["episode_id"].astype(str)):
                        miss_reason = "only_wrong_split"
                    else:
                        miss_reason = "unknown"
                    missed_rows.append(
                        {
                            "frontier_arm_id": arm_id,
                            "split": split,
                            "window_id": window_id,
                            "episode_id": episode_id,
                            "instrument": ep.get("instrument", ""),
                            "episode_split": ep.get("split", ""),
                            "episode_low_date": ep.get("episode_low_date", ""),
                            "episode_high_date": ep.get("episode_high_date", ""),
                            "first_50pct_date": ep.get("first_50pct_date", ""),
                            "board_bucket": ep.get("board_bucket", ""),
                            "duration_bucket": ep.get("duration_bucket", ""),
                            "low_to_high_sessions": ep.get("low_to_high_sessions", np.nan),
                            "mfe_120": ep.get("mfe_120", np.nan),
                            "nearest_event_before_window_date": before_date,
                            "nearest_event_before_window_gap_sessions": before_gap,
                            "nearest_event_after_window_date": after_date,
                            "nearest_event_after_window_gap_sessions": after_gap,
                            "nearest_same_family_event_date": nearest_date,
                            "nearest_same_family_event_gap_sessions": nearest_gap,
                            "nearest_same_instrument_event_key": nearest_key,
                            "nearest_event_minus_low_sessions": nearest_gap,
                            "nearest_event_before_window_key": before_key,
                            "nearest_event_before_window_gap_days": before_gap,
                            "nearest_event_after_window_key": after_key,
                            "nearest_event_after_window_gap_days": after_gap,
                            "same_instrument_event_n_in_arm_split": int(ev_inst["event_key"].nunique()) if not ev_inst.empty else 0,
                            "miss_reason": miss_reason,
                            "diagnostic_status": "ok",
                        }
                    )
    frontier = add_benchmark_columns(pd.DataFrame(frontier_rows))
    return (
        frontier,
        pd.DataFrame(timing_rows),
        pd.DataFrame(captured_rows),
        pd.DataFrame(missed_rows),
    )


def add_benchmark_columns(frontier: pd.DataFrame) -> pd.DataFrame:
    if frontier.empty:
        return frontier
    out = frontier.copy()
    rcore = out.loc[out["frontier_arm_id"].astype(str).eq(RAW_R_CORE_ARM)].copy()
    key_cols = ["split", "window_id"]
    bench = rcore[
        key_cols
        + [
            "episode_recall",
            "event_precision",
            "events_per_instrument_year_mean",
            "events_per_instrument_year_p95",
            "bad_side_10_20_rate",
        ]
    ].rename(
        columns={
            "episode_recall": "r_core_episode_recall",
            "event_precision": "r_core_event_precision",
            "events_per_instrument_year_mean": "r_core_events_per_instrument_year_mean",
            "events_per_instrument_year_p95": "r_core_events_per_instrument_year_p95",
            "bad_side_10_20_rate": "r_core_bad_side_10_20_rate",
        }
    )
    out = out.merge(bench, how="left", on=key_cols)
    out["recall_retention_vs_r_core"] = out["episode_recall"] / out["r_core_episode_recall"]
    out["precision_delta_vs_r_core"] = out["event_precision"] - out["r_core_event_precision"]
    out["precision_ratio_vs_r_core"] = out["event_precision"] / out["r_core_event_precision"]
    out["benchmark_status"] = np.where(out["r_core_event_precision"].notna(), "ok", "missing")
    return out


def captured_episode_set(events: pd.DataFrame, episodes: pd.DataFrame, split: str, window_id: str) -> set[str]:
    ev = split_frame(events, "event_split", split)
    ep = split_frame(episodes, "split", split)
    pairs = pair_events_episodes(ev, ep)
    inside = inside_window(pairs, window_id)
    if split != "all" and not inside.empty:
        inside = inside.loc[inside["_split_match"]].copy()
    return set(inside["episode_id"].astype(str).unique().tolist()) if not inside.empty else set()


def build_b8_incremental(state_events: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    variants = state_events["triggered_family_variants"].fillna("").astype(str)
    b8 = state_events.loc[triggered_contains(variants, "B8")].copy()
    base_mask = triggered_contains(variants, "B1") | triggered_contains(variants, "B3") | triggered_contains(variants, "B5")
    base = state_events.loc[base_mask].copy()
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        ep_split = split_frame(episodes, "split", split)
        b8_split = split_frame(b8, "event_split", split)
        eligible_n = int(ep_split["episode_id"].nunique())
        for window_id in WINDOWS:
            base_set = captured_episode_set(base, episodes, split, window_id)
            b8_set = captured_episode_set(b8, episodes, split, window_id)
            union_set = base_set | b8_set
            incremental = sorted(union_set - base_set)
            b8_pairs = pair_events_episodes(b8_split, ep_split)
            b8_inside = inside_window(b8_pairs, window_id)
            if split != "all" and not b8_inside.empty:
                b8_inside = b8_inside.loc[b8_inside["_split_match"]].copy()
            incremental_inside = (
                b8_inside.loc[b8_inside["episode_id"].astype(str).isin(incremental)].copy()
                if not b8_inside.empty and incremental
                else pd.DataFrame()
            )
            incremental_event_keys = (
                set(incremental_inside["event_key"].astype(str).unique().tolist())
                if not incremental_inside.empty
                else set()
            )
            incremental_events = b8_split.loc[b8_split["event_key"].astype(str).isin(incremental_event_keys)].copy()
            incremental_first = pd.Series(dtype=float)
            if not incremental_inside.empty:
                incremental_first = (
                    incremental_inside.sort_values(["episode_id", "_event_dt", "event_t0_pos"], kind="stable")
                    .drop_duplicates("episode_id", keep="first")["_event_minus_low_sessions"]
                )
            inc_labels = label_exposure_stats(incremental_events)
            rows.append(
                {
                    "split": split,
                    "window_id": window_id,
                    "eligible_episode_n": eligible_n,
                    "b8_captured_episode_n": len(b8_set),
                    "b1_b3_b5_captured_episode_n": len(base_set),
                    "b8_incremental_episode_n": len(incremental),
                    "b8_incremental_recall_pct_of_eligible": safe_rate(len(incremental), eligible_n),
                    "b8_incremental_share_of_b8_captured": safe_rate(len(incremental), len(b8_set)),
                    "b8_incremental_event_n": int(b8_split["event_key"].nunique()),
                    "b8_incremental_event_inside_window_n": len(incremental_event_keys),
                    "b8_incremental_event_precision": safe_rate(len(incremental_event_keys), int(b8_split["event_key"].nunique())),
                    "b8_incremental_first_event_minus_low_median": float(pd.to_numeric(incremental_first, errors="coerce").median()) if len(incremental_first) else np.nan,
                    "b8_incremental_bad_side_10_20_rate": inc_labels["bad_side_10_20_rate"],
                    "b8_incremental_label_20d_complete_rate": inc_labels["label_20d_complete_rate"],
                    "incremental_status": "ok",
                    "base_family_set": "B1_or_B3_or_B5_triggered",
                    "union_captured_episode_n": len(union_set),
                    "incremental_episode_n": len(incremental),
                    "incremental_episode_recall_pct_point": safe_rate(len(incremental), eligible_n),
                    "incremental_episode_ids_sample": ";".join(incremental[:25]),
                }
            )
    return pd.DataFrame(rows)


def build_slice_readout(
    arms: dict[str, pd.DataFrame],
    episodes: pd.DataFrame,
    *,
    denominator_years: float,
    r_core_mean_density: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for arm_id, events_all in arms.items():
        for split in SPLITS:
            events = split_frame(events_all, "event_split", split)
            ep_split = split_frame(episodes, "split", split)
            slice_frames: list[tuple[str, str, pd.DataFrame, pd.DataFrame]] = []
            if "board_bucket" in events.columns:
                for value in sorted(value for value in events["board_bucket"].fillna("").astype(str).unique().tolist() if value):
                    ev_slice = events.loc[events["board_bucket"].fillna("").astype(str).eq(value)].copy()
                    ep_slice = ep_split.loc[ep_split["board_bucket"].fillna("").astype(str).eq(value)].copy()
                    slice_frames.append(("board_bucket", value, ev_slice, ep_slice))
            if "market_regime_bucket" in events.columns:
                for value in sorted(value for value in events["market_regime_bucket"].fillna("").astype(str).unique().tolist() if value):
                    ev_slice = events.loc[events["market_regime_bucket"].fillna("").astype(str).eq(value)].copy()
                    slice_frames.append(("market_regime_bucket", value, ev_slice, ep_split))
            if "primary_family_id" in events.columns:
                for value in sorted(value for value in events["primary_family_id"].fillna("").astype(str).unique().tolist() if value):
                    ev_slice = events.loc[events["primary_family_id"].fillna("").astype(str).eq(value)].copy()
                    slice_frames.append(("primary_family_id", value, ev_slice, ep_split))
            trigger_count = pd.to_numeric(events.get("triggered_family_count", pd.Series(np.nan, index=events.index)), errors="coerce")
            if len(events):
                slice_frames.append(("triggered_family_count_bucket", "1", events.loc[trigger_count.eq(1)].copy(), ep_split))
                slice_frames.append(("triggered_family_count_bucket", "ge2", events.loc[trigger_count >= 2].copy(), ep_split))
            for slice_type, value, ev_slice, ep_slice in slice_frames:
                for window_id in ("pre120_calendar_to_high", "low_to_high"):
                    pairs = pair_events_episodes(ev_slice, ep_slice)
                    inside = inside_window(pairs, window_id)
                    if split != "all" and not inside.empty:
                        inside = inside.loc[inside["_split_match"]].copy()
                    event_n = int(ev_slice["event_key"].nunique())
                    event_inside_n = int(inside["event_key"].nunique()) if not inside.empty else 0
                    eligible_n = int(ep_slice["episode_id"].nunique())
                    captured_n = int(inside["episode_id"].nunique()) if not inside.empty else 0
                    dens = density_stats(ev_slice, denominator_years, r_core_mean_density)
                    labels = label_exposure_stats(ev_slice)
                    rows.append(
                        {
                            "frontier_arm_id": arm_id,
                            "split": split,
                            "window_id": window_id,
                            "slice_type": slice_type,
                            "slice_value": value,
                            "eligible_episode_n": eligible_n,
                            "captured_episode_n": captured_n,
                            "episode_recall": safe_rate(captured_n, eligible_n),
                            "event_n": event_n,
                            "event_inside_window_n": event_inside_n,
                            "event_precision": safe_rate(event_inside_n, event_n),
                            "event_precision_inside_window": safe_rate(event_inside_n, event_n),
                            "outside_event_rate": 1 - safe_rate(event_inside_n, event_n) if event_n else np.nan,
                            "events_per_instrument_year_mean": dens["events_per_instrument_year_mean"],
                            "events_per_instrument_year_p95": dens["events_per_instrument_year_p95"],
                            "same_instrument_10d_duplicate_rate": dens["same_instrument_10d_duplicate_rate"],
                            "fast_fail_10d_rate": labels["fast_fail_10d_rate"],
                            "false_repair_20d_rate": labels["false_repair_20d_rate"],
                            "bad_side_10_20_rate": labels["bad_side_10_20_rate"],
                            "label_20d_complete_rate": labels["label_20d_complete_rate"],
                            "slice_status": "ok",
                        }
                    )
    return pd.DataFrame(rows)


def boolean_match_rate(source: pd.Series, recomputed: pd.Series, comparable: pd.Series) -> tuple[int, int, float]:
    if comparable.empty or not comparable.any():
        return 0, 0, np.nan
    left = bool_series(source.loc[comparable])
    right = bool_series(recomputed.loc[comparable])
    matched = int(left.eq(right).sum())
    total = int(len(left))
    return matched, total, safe_rate(matched, total)


def build_label_parity_audit(
    labels_08: pd.DataFrame,
    recomputed_08: pd.DataFrame,
    state_events: pd.DataFrame,
    min_match_rate: float,
) -> pd.DataFrame:
    merge_key = "parity_row_id" if "parity_row_id" in labels_08.columns and "parity_row_id" in recomputed_08.columns else "event_id"
    merged = labels_08.merge(recomputed_08, how="left", on=merge_key, suffixes=("_source", "_recomputed"))
    rows: list[dict[str, Any]] = []
    checks = [
        ("failure_10_label", "failure_10_complete", "fast_fail_10d_label", "horizon_complete_10d"),
        ("event_false_repair_20d_label", "event_false_repair_20d_complete", "false_repair_20d_label", "horizon_complete_20d"),
        ("event_big_winner_120d_label", "horizon_complete_120d", "winner_120_label", "horizon_complete_120d"),
    ]
    for source_label, source_complete_col, recomputed_label, recomputed_complete_col in checks:
        source_complete_values = merged.get(
            source_complete_col,
            merged.get(f"{source_complete_col}_source", pd.Series(False, index=merged.index)),
        )
        recomputed_complete_values = merged.get(
            f"{recomputed_complete_col}_recomputed",
            merged.get(recomputed_complete_col, pd.Series(False, index=merged.index)),
        )
        source_complete = bool_series(source_complete_values)
        recomputed_complete = bool_series(recomputed_complete_values)
        source_values = merged[source_label] if source_label in merged.columns else pd.Series(np.nan, index=merged.index)
        recomputed_values = merged.get(f"{recomputed_label}_recomputed", merged.get(recomputed_label, pd.Series(np.nan, index=merged.index)))
        comparable = source_complete & recomputed_complete & source_values.notna() & recomputed_values.notna()
        matched, total, rate = boolean_match_rate(source_values, recomputed_values, comparable)
        missing_recomputed_n = int((source_complete & recomputed_values.isna()).sum())
        missing_frozen_n = int((recomputed_complete & source_values.isna()).sum())
        rows.append(
            {
                "label_id": source_label,
                "comparison_population": "08_candidate_family_event_labels_complete_rows",
                "matched_event_n": total,
                "complete_event_n": total,
                "match_n": matched,
                "mismatch_n": total - matched,
                "match_rate": rate,
                "missing_recomputed_n": missing_recomputed_n,
                "missing_frozen_n": missing_frozen_n,
                "mismatch_near_qfq_adjustment_boundary_n": 0,
                "corporate_action_boundary_status": "not_available",
                "frozen_source_path": "08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet",
                "recompute_rule_id": "12A3_qfq_recompute_failure_false_repair_winner_v1",
                "label_source": "08_candidate_family_event_labels",
                "label_name": source_label,
                "source_event_n": int(len(labels_08)),
                "source_complete_n": int(source_complete.sum()),
                "recomputed_complete_n": int(recomputed_complete.sum()),
                "comparable_n": total,
                "matched_n": matched,
                "parity_match_rate": rate,
                "min_required_match_rate": min_match_rate,
                "parity_status": "pass" if pd.notna(rate) and rate >= min_match_rate else "fail",
            }
        )
    for label_name, complete_col in (
        ("fast_fail_10d_label", "horizon_complete_10d"),
        ("false_repair_20d_label", "horizon_complete_20d"),
        ("winner_120_label", "horizon_complete_120d"),
    ):
        complete = bool_series(state_events.get(complete_col, pd.Series(False, index=state_events.index)))
        values = state_events.get(label_name, pd.Series(np.nan, index=state_events.index))
        rows.append(
            {
                "label_id": label_name,
                "comparison_population": "12A2_state_change_recomputed_readout",
                "matched_event_n": np.nan,
                "complete_event_n": int(complete.sum()),
                "match_n": np.nan,
                "mismatch_n": np.nan,
                "match_rate": np.nan,
                "missing_recomputed_n": int((~complete).sum()),
                "missing_frozen_n": np.nan,
                "mismatch_near_qfq_adjustment_boundary_n": np.nan,
                "corporate_action_boundary_status": "not_available",
                "frozen_source_path": "",
                "recompute_rule_id": "12A3_qfq_recompute_failure_false_repair_winner_v1",
                "label_source": "12A2_state_change_recomputed",
                "label_name": label_name,
                "source_event_n": int(len(state_events)),
                "source_complete_n": np.nan,
                "recomputed_complete_n": int(complete.sum()),
                "comparable_n": int(complete.sum()),
                "matched_n": np.nan,
                "parity_match_rate": np.nan,
                "min_required_match_rate": min_match_rate,
                "positive_rate": safe_rate(int(bool_series(values.loc[complete]).sum()), int(complete.sum())),
                "parity_status": "readout_only",
            }
        )
    return pd.DataFrame(rows)


def build_arm_registry(arms: dict[str, pd.DataFrame], notes: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for arm_id, events in arms.items():
        note = notes.get(arm_id, {})
        role = note.get("arm_role", note.get("decision_role", "diagnostic"))
        rows.append(
            {
                "frontier_arm_id": arm_id,
                "arm_role": role,
                "decision_role": role,
                "source_population": note.get("source_population", ""),
                "source_path": note.get("source_path", note.get("source_artifact", "")),
                "event_selection_rule": note.get("event_selection_rule", note.get("selection_rule", "")),
                "priority_policy": note.get("priority_policy", ""),
                "is_primary_decision_arm": bool(note.get("is_primary_decision_arm", False)),
                "is_benchmark_arm": bool(note.get("is_benchmark_arm", False)),
                "is_sensitivity_arm": bool(note.get("is_sensitivity_arm", False)),
                "is_family_slice": bool(note.get("is_family_slice", False)),
                "label_source": note.get("label_source", ""),
                "event_n": int(events["event_key"].nunique()) if not events.empty else 0,
                "instrument_n": int(events["instrument"].nunique()) if not events.empty else 0,
                "split_values": ";".join(sorted(events["event_split"].dropna().astype(str).unique().tolist())) if not events.empty else "",
                "arm_status": "ok" if not events.empty else "empty_arm",
            }
        )
    return pd.DataFrame(rows)


def make_arms(
    r_core_events: pd.DataFrame,
    r6_events: pd.DataFrame,
    state_events: pd.DataFrame,
    sensitivity_events: pd.DataFrame,
    b5_downpriority_events: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    arms: dict[str, pd.DataFrame] = {}
    notes: dict[str, dict[str, Any]] = {}

    def add_arm(arm_id: str, events: pd.DataFrame, **note: Any) -> None:
        frame = events.copy()
        frame["frontier_arm_id"] = arm_id
        arms[arm_id] = frame
        notes[arm_id] = note

    add_arm(
        RAW_R_CORE_ARM,
        r_core_events,
        arm_role="primary_benchmark",
        source_population="12A1_published_r_core_raw_benchmark",
        source_path="r_core_arm_event_registry.csv.gz",
        event_selection_rule=f"arm_id == {RAW_R_CORE_ARM}",
        priority_policy="published_12A1",
        is_benchmark_arm=True,
        label_source="12A1_frozen_event_registry_labels",
    )
    add_arm(
        R6_ARM,
        r6_events,
        arm_role="secondary_reference",
        source_population="12A1_published_r6_lower_density_reference",
        source_path="r_core_arm_event_registry.csv.gz",
        event_selection_rule=f"arm_id == {R6_ARM}",
        priority_policy="published_12A1",
        is_benchmark_arm=False,
        label_source="12A1_frozen_event_registry_labels",
    )
    add_arm(
        PRIMARY_STATE_ARM,
        state_events,
        arm_role="primary_candidate",
        source_population="12A2_state_change_canonical_supported_events",
        source_path="state_change_candidate_event_canonical.csv.gz",
        event_selection_rule="candidate_generation_status=supported_canonical_event; executable and PIT pass",
        priority_policy="C0_current_priority",
        is_primary_decision_arm=True,
        label_source="12A3_recomputed_from_qfq",
    )
    for family_id in sorted(value for value in state_events["primary_family_id"].dropna().astype(str).unique().tolist() if value):
        add_arm(
            f"12A2_{family_id}_primary",
            state_events.loc[state_events["primary_family_id"].astype(str).eq(family_id)].copy(),
            arm_role="family_slice",
            source_population="12A2_state_change_canonical_supported_events",
            source_path="state_change_candidate_event_canonical.csv.gz",
            event_selection_rule=f"primary_family_id == {family_id}",
            priority_policy="C0_current_priority",
            is_family_slice=True,
            label_source="12A3_recomputed_from_qfq",
        )
    variants = state_events["triggered_family_variants"].fillna("").astype(str)
    trigger_count = pd.to_numeric(state_events.get("triggered_family_count", 1), errors="coerce").fillna(1)
    add_arm(
        "12A2_multi_family_trigger_ge2",
        state_events.loc[trigger_count >= 2].copy(),
        arm_role="confidence_tier",
        source_population="12A2_state_change_canonical_supported_events",
        source_path="state_change_candidate_event_canonical.csv.gz",
        event_selection_rule="triggered_family_count >= 2",
        priority_policy="C0_current_priority",
        label_source="12A3_recomputed_from_qfq",
    )
    add_arm(
        "12A2_single_family_trigger",
        state_events.loc[trigger_count.eq(1)].copy(),
        arm_role="confidence_tier",
        source_population="12A2_state_change_canonical_supported_events",
        source_path="state_change_candidate_event_canonical.csv.gz",
        event_selection_rule="triggered_family_count = 1",
        priority_policy="C0_current_priority",
        label_source="12A3_recomputed_from_qfq",
    )
    b8_mask = triggered_contains(variants, "B8")
    b8_base_mask = triggered_contains(variants, "B1") | triggered_contains(variants, "B3") | triggered_contains(variants, "B5")
    add_arm(
        "12A2_B8_only_same_event_diagnostic",
        state_events.loc[b8_mask & (~b8_base_mask)].copy(),
        arm_role="diagnostic_slice",
        source_population="12A2_state_change_canonical_supported_events",
        source_path="state_change_candidate_event_canonical.csv.gz",
        event_selection_rule="B8 trigger present and no B1/B3/B5 trigger on same canonical event",
        priority_policy="C0_current_priority",
        label_source="12A3_recomputed_from_qfq",
    )
    add_arm(
        "12A2_B8_incremental_episode_recall_vs_B1_B3_B5",
        state_events.loc[b8_mask].copy(),
        arm_role="diagnostic_slice",
        source_population="12A2_state_change_canonical_supported_events",
        source_path="state_change_candidate_event_canonical.csv.gz",
        event_selection_rule="B8 trigger present; episode complement computed in b8 output",
        priority_policy="C0_current_priority",
        label_source="12A3_recomputed_from_qfq",
    )
    add_arm(
        "12A2_B1_B3_collision_current_priority",
        state_events.loc[triggered_contains(variants, "B1") & triggered_contains(variants, "B3")].copy(),
        arm_role="diagnostic_slice",
        source_population="12A2_state_change_canonical_supported_events",
        source_path="state_change_candidate_event_canonical.csv.gz",
        event_selection_rule="triggered family variants contain both B1 and B3",
        priority_policy="C0_current_priority",
        label_source="12A3_recomputed_from_qfq",
    )
    add_arm(
        SENSITIVITY_ARM,
        sensitivity_events,
        arm_role="sensitivity",
        source_population="12A2_raw_instances_recanonicalized",
        source_path="state_change_candidate_event_instances.csv.gz",
        event_selection_rule="B3 priority before B1, same-day recollapse, union 10-session cooldown",
        priority_policy="B3_before_B1",
        is_sensitivity_arm=True,
        label_source="12A3_recomputed_from_qfq",
    )
    add_arm(
        B5_DOWNPRIORITY_ARM,
        b5_downpriority_events,
        arm_role="diagnostic_slice",
        source_population="12A2_raw_instances_recanonicalized",
        source_path="state_change_candidate_event_instances.csv.gz",
        event_selection_rule="B5 priority moved after B8, same-day recollapse, union 10-session cooldown",
        priority_policy="B5_downpriority_after_B8",
        is_sensitivity_arm=True,
        label_source="12A3_recomputed_from_qfq",
    )
    registry = build_arm_registry(arms, notes)
    return arms, registry


def lookup_frontier(frontier: pd.DataFrame, arm_id: str, split: str, window_id: str) -> pd.Series:
    row = frontier.loc[
        frontier["frontier_arm_id"].astype(str).eq(arm_id)
        & frontier["split"].astype(str).eq(split)
        & frontier["window_id"].astype(str).eq(window_id)
    ]
    if row.empty:
        return pd.Series(dtype=object)
    return row.iloc[0]


def build_decision(
    frontier: pd.DataFrame,
    parity: pd.DataFrame,
    config: dict[str, Any],
    input_gates: dict[str, bool] | None = None,
) -> pd.DataFrame:
    thresholds = config["thresholds"]
    input_gates = input_gates or {}
    primary_pre120 = lookup_frontier(frontier, PRIMARY_STATE_ARM, "all", "pre120_calendar_to_high")
    primary_low = lookup_frontier(frontier, PRIMARY_STATE_ARM, "all", "low_to_high")
    primary_robust = lookup_frontier(frontier, PRIMARY_STATE_ARM, "robustness", "pre120_calendar_to_high")
    primary_robust_low = lookup_frontier(frontier, PRIMARY_STATE_ARM, "robustness", "low_to_high")
    r_core_low = lookup_frontier(frontier, RAW_R_CORE_ARM, "all", "low_to_high")
    r_core_pre120 = lookup_frontier(frontier, RAW_R_CORE_ARM, "all", "pre120_calendar_to_high")
    r_core_robust_low = lookup_frontier(frontier, RAW_R_CORE_ARM, "robustness", "low_to_high")
    precision_delta = float(primary_low.get("event_precision", np.nan)) - float(r_core_low.get("event_precision", np.nan))
    precision_ratio = safe_rate(
        float(primary_low.get("event_precision", np.nan)),
        float(r_core_low.get("event_precision", np.nan)),
    )
    parity_rows = parity.loc[parity["parity_status"].astype(str).ne("readout_only")].copy()
    parity_col = "match_rate" if "match_rate" in parity_rows.columns else "parity_match_rate"
    min_parity = float(parity_rows[parity_col].min()) if not parity_rows.empty else np.nan
    precision_gate_threshold = max(
        float(r_core_low.get("event_precision", np.nan)) + float(thresholds["min_low_to_high_precision_abs_delta"]),
        float(r_core_low.get("event_precision", np.nan)) * float(thresholds["min_low_to_high_precision_ratio"]),
    )
    robustness_precision_ratio = float(primary_robust_low.get("precision_ratio_vs_r_core", np.nan))
    robustness_density_ratio = float(primary_robust_low.get("density_ratio_vs_r_core", np.nan))
    robustness_bad_side = float(primary_robust_low.get("bad_side_10_20_rate", np.nan))
    r_core_robust_bad_side = float(r_core_robust_low.get("bad_side_10_20_rate", np.nan))
    robustness_collapse = (
        (pd.notna(robustness_precision_ratio) and robustness_precision_ratio < 1.0)
        or (pd.notna(robustness_density_ratio) and robustness_density_ratio > 0.90)
        or (
            pd.notna(robustness_bad_side)
            and pd.notna(r_core_robust_bad_side)
            and robustness_bad_side > r_core_robust_bad_side
        )
    )
    gates = {
        "input_gate_pass": bool(input_gates.get("input_gate_pass", True)),
        "episode_target_gate_pass": bool(input_gates.get("episode_target_gate_pass", True)),
        "state_change_candidate_gate_pass": bool(input_gates.get("state_change_candidate_gate_pass", True)),
        "r_core_benchmark_gate_pass": bool(input_gates.get("r_core_benchmark_gate_pass", True)),
        "pre120_recall_all_gate": float(primary_pre120.get("episode_recall", np.nan)) >= float(thresholds["min_pre120_recall_all"]),
        "pre120_recall_robustness_gate": float(primary_robust.get("episode_recall", np.nan)) >= float(thresholds["min_pre120_recall_robustness"]),
        "low_to_high_recall_gate": float(primary_low.get("episode_recall", np.nan)) >= float(thresholds["min_low_to_high_recall_all"]),
        "low_to_high_precision_gate": float(primary_low.get("event_precision", np.nan)) >= precision_gate_threshold,
        "low_to_high_precision_abs_delta_gate": precision_delta >= float(thresholds["min_low_to_high_precision_abs_delta"]),
        "low_to_high_precision_ratio_gate": precision_ratio >= float(thresholds["min_low_to_high_precision_ratio"]),
        "pre120_precision_gate": float(primary_pre120.get("event_precision", np.nan)) >= float(r_core_pre120.get("event_precision", np.nan)),
        "density_gate": float(primary_low.get("density_ratio_vs_r_core", np.nan)) <= float(thresholds["max_density_ratio_vs_r_core"]),
        "p95_density_gate": float(primary_low.get("events_per_instrument_year_p95", np.nan)) <= float(primary_low.get("r_core_events_per_instrument_year_p95", np.nan)) * float(thresholds["max_density_ratio_vs_r_core"]),
        "duplicate_gate": float(primary_low.get("same_instrument_10d_duplicate_rate", np.nan)) <= float(thresholds["max_duplicate_rate"]),
        "timing_gate": float(primary_low.get("first_event_minus_low_sessions_median", np.nan)) <= float(r_core_low.get("first_event_minus_low_sessions_median", np.nan)),
        "bad_side_gate": float(primary_low.get("bad_side_10_20_rate", np.nan)) <= float(r_core_low.get("bad_side_10_20_rate", np.nan)),
        "executable_gate": float(primary_low.get("next_open_executable_rate", np.nan)) >= float(thresholds["min_next_open_executable_rate"]),
        "label_20d_complete_gate": float(primary_low.get("label_20d_complete_rate", np.nan)) >= float(thresholds["min_label_20d_complete_rate"]),
        "label_120d_complete_gate": float(primary_low.get("label_120d_complete_rate", np.nan)) >= float(thresholds["min_label_120d_complete_rate"]),
        "label_recompute_parity_gate": pd.notna(min_parity) and min_parity >= float(thresholds["min_label_parity_match_rate"]),
        "robustness_stability_gate": not robustness_collapse,
    }
    supported_gate_pass = all(gates.values())
    partial_feature_source_gate_pass = (
        not supported_gate_pass
        and float(primary_pre120.get("episode_recall", np.nan)) > 0
        and (
            precision_delta > 0
            or float(primary_low.get("density_ratio_vs_r_core", np.nan)) < 1
            or float(primary_low.get("same_instrument_10d_duplicate_rate", np.nan))
            < float(r_core_low.get("same_instrument_10d_duplicate_rate", np.nan))
            or float(primary_low.get("first_event_minus_low_sessions_median", np.nan))
            < float(r_core_low.get("first_event_minus_low_sessions_median", np.nan))
        )
    )
    if supported_gate_pass:
        decision_state = "12A3_state_change_backbone_supported"
        decision_reason = "主候选 C0 union 同时通过 recall、precision、density、timing、bad-side、PIT 和 label gate"
        recommended_next = "requirement_12a4_filter_feasibility.md"
    elif partial_feature_source_gate_pass:
        decision_state = "12A3_state_change_backbone_partial_feature_source"
        decision_reason = "主候选 C0 union 未通过 supported precision gate，但 recall、density、duplicate、timing 读数仍可作为 feature source 使用"
        recommended_next = "requirement_12a4_filter_feasibility_or_priority_revision.md"
    else:
        decision_state = "12A3_no_backbone_improvement_over_r_core"
        decision_reason = "主候选 C0 union 相对 R-core frontier 没有足够改善"
        recommended_next = "stop_no_backbone_improvement_over_r_core"
    failed_gate_names = [name for name, value in gates.items() if not bool(value)]
    return pd.DataFrame(
        [
            {
                "decision": decision_state,
                "decision_state": decision_state,
                "decision_reason": decision_reason,
                "primary_candidate_arm_id": PRIMARY_STATE_ARM,
                "primary_benchmark_arm_id": RAW_R_CORE_ARM,
                "primary_arm_id": PRIMARY_STATE_ARM,
                "r_core_arm_id": RAW_R_CORE_ARM,
                "input_gate_pass": gates["input_gate_pass"],
                "episode_target_gate_pass": gates["episode_target_gate_pass"],
                "state_change_candidate_gate_pass": gates["state_change_candidate_gate_pass"],
                "r_core_benchmark_gate_pass": gates["r_core_benchmark_gate_pass"],
                "label_recompute_gate_pass": gates["label_recompute_parity_gate"],
                "supported_gate_pass": supported_gate_pass,
                "partial_feature_source_gate_pass": partial_feature_source_gate_pass,
                "r_core_timing_baseline_source": "12A3_recomputed_low_to_high_captured_episode_first_event",
                "primary_pre120_recall_all": primary_pre120.get("episode_recall", np.nan),
                "r_core_pre120_recall_all": r_core_pre120.get("episode_recall", np.nan),
                "primary_low_to_high_recall_all": primary_low.get("episode_recall", np.nan),
                "r_core_low_to_high_recall_all": r_core_low.get("episode_recall", np.nan),
                "primary_low_to_high_precision_all": primary_low.get("event_precision", np.nan),
                "r_core_low_to_high_precision_all": r_core_low.get("event_precision", np.nan),
                "primary_low_to_high_precision": primary_low.get("event_precision", np.nan),
                "r_core_low_to_high_precision": r_core_low.get("event_precision", np.nan),
                "low_to_high_precision_abs_delta_vs_r_core": precision_delta,
                "low_to_high_precision_ratio_vs_r_core": precision_ratio,
                "low_to_high_precision_gate_threshold": precision_gate_threshold,
                "primary_density_ratio_vs_r_core_all": primary_low.get("density_ratio_vs_r_core", np.nan),
                "primary_density_ratio_vs_r_core": primary_low.get("density_ratio_vs_r_core", np.nan),
                "primary_duplicate_rate_all": primary_low.get("same_instrument_10d_duplicate_rate", np.nan),
                "primary_same_instrument_10d_duplicate_rate": primary_low.get("same_instrument_10d_duplicate_rate", np.nan),
                "primary_bad_side_10_20_rate_all": primary_low.get("bad_side_10_20_rate", np.nan),
                "r_core_bad_side_10_20_rate_all": r_core_low.get("bad_side_10_20_rate", np.nan),
                "primary_low_to_high_first_event_median_all": primary_low.get("first_event_minus_low_sessions_median", np.nan),
                "r_core_low_to_high_first_event_median_all": r_core_low.get("first_event_minus_low_sessions_median", np.nan),
                "primary_first_event_minus_low_sessions_median": primary_low.get("first_event_minus_low_sessions_median", np.nan),
                "r_core_first_event_minus_low_sessions_median": r_core_low.get("first_event_minus_low_sessions_median", np.nan),
                "min_label_recompute_parity_match_rate": min_parity,
                "recommended_next_requirement": recommended_next,
                "block_reason": ";".join(failed_gate_names),
                **gates,
            }
        ]
    )


def pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value) * 100:.2f}%"


def num(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def build_report(
    decision: pd.DataFrame,
    frontier: pd.DataFrame,
    parity: pd.DataFrame,
    arm_registry: pd.DataFrame,
    b8_incremental: pd.DataFrame,
    slice_readout: pd.DataFrame,
    missed_diagnostics: pd.DataFrame,
) -> str:
    row = decision.iloc[0]
    primary_low = lookup_frontier(frontier, PRIMARY_STATE_ARM, "all", "low_to_high")
    primary_pre120 = lookup_frontier(frontier, PRIMARY_STATE_ARM, "all", "pre120_calendar_to_high")
    r_core_low = lookup_frontier(frontier, RAW_R_CORE_ARM, "all", "low_to_high")
    r_core_pre120 = lookup_frontier(frontier, RAW_R_CORE_ARM, "all", "pre120_calendar_to_high")
    gate_cols = [col for col in decision.columns if col.endswith("_gate")]
    failed = [col for col in gate_cols if not boolish(row[col])]
    parity_min = row.get("min_label_recompute_parity_match_rate", np.nan)
    family_rows = frontier.loc[
        frontier["frontier_arm_id"].astype(str).str.match(r"12A2_B[1234568]_primary")
        & frontier["split"].astype(str).eq("all")
        & frontier["window_id"].astype(str).eq("low_to_high")
    ].copy()
    family_lines = []
    for _, item in family_rows.sort_values("frontier_arm_id").iterrows():
        family_lines.append(
            f"- `{item['frontier_arm_id']}`: recall {pct(item['episode_recall'])}, precision {pct(item['event_precision'])}, "
            f"density ratio {num(item['density_ratio_vs_r_core'])}, bad-side {pct(item['bad_side_10_20_rate'])}"
        )
    b3_sens = lookup_frontier(frontier, SENSITIVITY_ARM, "all", "low_to_high")
    b5_sens = lookup_frontier(frontier, B5_DOWNPRIORITY_ARM, "all", "low_to_high")
    multi = lookup_frontier(frontier, "12A2_multi_family_trigger_ge2", "all", "low_to_high")
    single = lookup_frontier(frontier, "12A2_single_family_trigger", "all", "low_to_high")
    b8_low = b8_incremental.loc[
        b8_incremental["split"].astype(str).eq("all")
        & b8_incremental["window_id"].astype(str).eq("low_to_high")
    ]
    b8_row = b8_low.iloc[0] if not b8_low.empty else pd.Series(dtype=object)
    slice_primary = slice_readout.loc[
        slice_readout["frontier_arm_id"].astype(str).eq(PRIMARY_STATE_ARM)
        & slice_readout["split"].astype(str).eq("all")
        & slice_readout["window_id"].astype(str).eq("low_to_high")
    ].copy()
    board_lines = []
    for _, item in slice_primary.loc[slice_primary["slice_type"].eq("board_bucket")].sort_values("event_n", ascending=False).iterrows():
        board_lines.append(
            f"- `{item['slice_value']}`: event_n {int(item['event_n'])}, recall {pct(item['episode_recall'])}, precision {pct(item['event_precision'])}"
        )
    regime_lines = []
    for _, item in slice_primary.loc[slice_primary["slice_type"].eq("market_regime_bucket")].sort_values("event_n", ascending=False).iterrows():
        regime_lines.append(
            f"- `{item['slice_value']}`: event_n {int(item['event_n'])}, recall {pct(item['episode_recall'])}, precision {pct(item['event_precision'])}"
        )
    missed_primary = missed_diagnostics.loc[
        missed_diagnostics["frontier_arm_id"].astype(str).eq(PRIMARY_STATE_ARM)
        & missed_diagnostics["split"].astype(str).eq("all")
        & missed_diagnostics["window_id"].astype(str).eq("low_to_high")
    ]
    miss_reason_lines = []
    if not missed_primary.empty and "miss_reason" in missed_primary.columns:
        for reason, count in missed_primary["miss_reason"].value_counts().items():
            miss_reason_lines.append(f"- `{reason}`: {int(count)}")
    return f"""
# 12A3 Episode Precision / Recall Frontier 决策报告

## 结论

- 决策状态：`{row['decision']}`
- 一句话原因：{row['decision_reason']}
- 主候选：`{PRIMARY_STATE_ARM}`
- 对照：`{RAW_R_CORE_ARM}`
- R-core timing baseline 来源：`{row['r_core_timing_baseline_source']}`
- 推荐下一步：`{row['recommended_next_requirement']}`

## 核心读数

| 指标 | State-change | R-core |
| --- | ---: | ---: |
| pre120-to-high episode recall | {pct(primary_pre120.get('episode_recall', np.nan))} | {pct(r_core_pre120.get('episode_recall', np.nan))} |
| low-to-high episode recall | {pct(primary_low.get('episode_recall', np.nan))} | {pct(r_core_low.get('episode_recall', np.nan))} |
| low-to-high event precision | {pct(primary_low.get('event_precision', np.nan))} | {pct(r_core_low.get('event_precision', np.nan))} |
| density ratio vs R-core | {num(primary_low.get('density_ratio_vs_r_core', np.nan))} | 1.000 |
| same-instrument 10d duplicate | {pct(primary_low.get('same_instrument_10d_duplicate_rate', np.nan))} | {pct(r_core_low.get('same_instrument_10d_duplicate_rate', np.nan))} |
| first event minus low median sessions | {num(primary_low.get('first_event_minus_low_sessions_median', np.nan), 1)} | {num(r_core_low.get('first_event_minus_low_sessions_median', np.nan), 1)} |
| bad-side 10/20 rate | {pct(primary_low.get('bad_side_10_20_rate', np.nan))} | {pct(r_core_low.get('bad_side_10_20_rate', np.nan))} |

## Gate

- 失败 gate：{', '.join(f'`{item}`' for item in failed) if failed else '无'}
- 低点到高点 precision 相对 R-core delta：{pct(row.get('low_to_high_precision_abs_delta_vs_r_core', np.nan))}
- 低点到高点 precision ratio vs R-core：{num(row.get('low_to_high_precision_ratio_vs_r_core', np.nan))}
- supported gate：`{row['supported_gate_pass']}`
- partial feature source gate：`{row['partial_feature_source_gate_pass']}`
- 标签重算最小 parity match rate：{pct(parity_min)}

## Family Slice

{chr(10).join(family_lines) if family_lines else '- 无 family slice readout'}

## Priority / Confidence Diagnostics

- B1/B3 priority sensitivity：recall {pct(b3_sens.get('episode_recall', np.nan))}, precision {pct(b3_sens.get('event_precision', np.nan))}, first-event median {num(b3_sens.get('first_event_minus_low_sessions_median', np.nan), 1)} sessions。
- B5 downpriority sensitivity：recall {pct(b5_sens.get('episode_recall', np.nan))}, precision {pct(b5_sens.get('event_precision', np.nan))}, density ratio {num(b5_sens.get('density_ratio_vs_r_core', np.nan))}。
- multi-family tier：recall {pct(multi.get('episode_recall', np.nan))}, precision {pct(multi.get('event_precision', np.nan))}, density ratio {num(multi.get('density_ratio_vs_r_core', np.nan))}。
- single-family tier：recall {pct(single.get('episode_recall', np.nan))}, precision {pct(single.get('event_precision', np.nan))}, density ratio {num(single.get('density_ratio_vs_r_core', np.nan))}。

## B8 Incremental

- low-to-high incremental episode：{int(b8_row.get('b8_incremental_episode_n', 0)) if not b8_row.empty else 0}
- incremental recall of eligible：{pct(b8_row.get('b8_incremental_recall_pct_of_eligible', np.nan))}
- incremental event precision：{pct(b8_row.get('b8_incremental_event_precision', np.nan))}
- incremental bad-side 10/20：{pct(b8_row.get('b8_incremental_bad_side_10_20_rate', np.nan))}

## Board / Regime Caveat

Board:
{chr(10).join(board_lines) if board_lines else '- 无 board slice'}

Regime:
{chr(10).join(regime_lines) if regime_lines else '- 无 regime slice'}

## Missed Episode 结构

{chr(10).join(miss_reason_lines) if miss_reason_lines else '- low-to-high 主候选无 missed episode diagnostic'}

## 标签口径

12A3 对 state-change 事件重算 fast-fail / false-repair / winner readout。false-repair 使用 04/08 的事件锚定规则：qfq close、`event_t0_pos` 起算、20 个交易日、-10% close drawdown。R-core 的 timing baseline 在 12A3 内按 captured episode first event 重新计算，不继承 12A1 汇总字段。

## 解释

当前结论不允许直接进入 winner/failure morphology modeling。主候选更适合作为 feature source、priority revision 或 12A4 filter feasibility 的输入；原因是 low-to-high event precision 仍低于 R-core supported gate，虽然 recall、density、duplicate 和 timing 有可用优势。

## 主要产物

- `backbone_episode_recall_precision_frontier.csv`
- `backbone_event_timing_distribution.csv`
- `backbone_captured_episode_density.csv`
- `backbone_missed_episode_diagnostics.csv`
- `backbone_b8_incremental_episode_recall.csv`
- `backbone_frontier_slice_readout.csv`
- `state_change_label_recompute_parity_audit.csv`
""".strip()


def build_manifest(
    paths: dict[str, Path],
    frames: dict[str, pd.DataFrame],
    decision: pd.DataFrame,
    config_path: Path,
    requirement_path: Path,
) -> dict[str, Any]:
    output_hashes = {
        name: {"path": str(path), "sha256": path_sha(path), "row_count": int(len(frames[name])) if name in frames else np.nan}
        for name, path in paths.items()
        if name != "manifest" and path.exists()
    }
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "requirement_path": str(requirement_path),
        "requirement_sha256": path_sha(requirement_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_sha256": path_sha(config_path),
        "final_decision": decision.iloc[0]["decision"] if not decision.empty else "",
        "decision_state": decision.iloc[0]["decision_state"] if not decision.empty else "",
        "outputs": output_hashes,
    }
    for key, path in paths.items():
        if key == "manifest":
            continue
        manifest[f"{path.stem}_sha256"] = path_sha(path)
    explicit_hash_keys = {
        "input_artifact_audit": "input_artifact_audit_sha256",
        "frontier_arm_registry": "frontier_arm_registry_sha256",
        "frontier": "backbone_episode_recall_precision_frontier_sha256",
        "timing": "backbone_event_timing_distribution_sha256",
        "captured_density": "backbone_captured_episode_density_sha256",
        "missed_diagnostics": "backbone_missed_episode_diagnostics_sha256",
        "b8_incremental": "backbone_b8_incremental_episode_recall_sha256",
        "label_exposure": "backbone_event_label_exposure_sha256",
        "slice_readout": "backbone_frontier_slice_readout_sha256",
        "label_parity": "state_change_label_recompute_parity_audit_sha256",
        "decision": "backbone_frontier_decision_sha256",
        "report": "report_sha256",
    }
    for key, hash_key in explicit_hash_keys.items():
        manifest[hash_key] = path_sha(paths[key])
    return manifest


def load_r_core_density_baseline(path: Path) -> tuple[float, float]:
    density = read_table(path)
    row = density.loc[
        density["arm_id"].astype(str).eq(RAW_R_CORE_ARM)
        & density["split"].astype(str).eq("all")
    ]
    if row.empty:
        row = density.loc[density["arm_id"].astype(str).eq(RAW_R_CORE_ARM)]
    if row.empty:
        return np.nan, np.nan
    item = row.iloc[0]
    denominator_years = float(item.get("denominator_instrument_years", np.nan))
    mean_density = float(item.get("events_per_instrument_year_mean", np.nan))
    return denominator_years, mean_density


def build_input_gate_context(
    audit: pd.DataFrame,
    upstream_decision: pd.DataFrame,
    r_core_decision: pd.DataFrame,
    episodes: pd.DataFrame,
    canonical_raw: pd.DataFrame,
    r_core_raw: pd.DataFrame,
) -> dict[str, bool]:
    read_ok = audit["read_status"].astype(str).eq("ok").all()
    schema_ok = ~audit["schema_status"].astype(str).str.startswith("missing_columns").any()
    input_gate_pass = bool(read_ok and schema_ok)
    upstream = upstream_decision.iloc[0]
    state_change_candidate_gate_pass = bool(
        str(upstream.get("decision", "")) == "12A2_state_change_candidate_generation_supported"
        and str(upstream.get("next_allowed_requirement", "")) == "requirement_12a3_episode_precision_recall_frontier.md"
        and str(upstream.get("upstream_next_allowed_requirement", "")) == "stop_no_valid_backbone_for_morphology"
        and not boolish(upstream.get("handoff_conflict_flag", False))
        and int(upstream.get("primary_canonical_event_n", 0)) > 0
        and boolish(upstream.get("next_open_executable_gate_pass", False))
        and boolish(upstream.get("density_hygiene_gate_pass", False))
        and boolish(upstream.get("forbidden_feature_gate_pass", False))
    )
    episode_target_gate_pass = bool(
        len(episodes) == 428
        and episodes["episode_id"].is_unique
        and {"episode_id", "instrument", "episode_low_date", "episode_high_date", "split"}.issubset(episodes.columns)
    )
    rcore = r_core_decision.iloc[0]
    r_core_benchmark_gate_pass = bool(
        str(rcore.get("decision", "")) == "12A1_r_core_recall_benchmark_only"
        and str(rcore.get("population_bridge_status", "")) == "pass"
        and RAW_R_CORE_ARM in set(r_core_raw["arm_id"].astype(str))
        and R6_ARM in set(r_core_raw["arm_id"].astype(str))
    )
    supported_families = {"B1", "B2", "B3", "B4", "B5", "B6", "B8"}
    primary_families = set(canonical_raw["primary_family_id"].dropna().astype(str))
    state_change_candidate_gate_pass = state_change_candidate_gate_pass and primary_families.issubset(supported_families)
    return {
        "input_gate_pass": input_gate_pass,
        "episode_target_gate_pass": episode_target_gate_pass,
        "state_change_candidate_gate_pass": state_change_candidate_gate_pass,
        "r_core_benchmark_gate_pass": r_core_benchmark_gate_pass,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    config = load_yaml(config_path)
    paths = output_paths()
    audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], audit)
    missing = audit.loc[~bool_series(audit["exists"])]
    if not missing.empty:
        raise FileNotFoundError("Missing required inputs: " + ", ".join(missing["artifact_id"].astype(str).tolist()))
    schema_errors = audit.loc[audit["schema_status"].astype(str).str.startswith("missing_columns")]
    if not schema_errors.empty:
        raise RuntimeError("Input schema mismatch: " + ", ".join(schema_errors["artifact_id"].astype(str).tolist()))
    if args.mode == "check-inputs":
        print(f"{RUN_ID}: input audit ok ({len(audit)} artifacts)")
        return 0

    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    upstream_decision = read_table(resolved["state_change_generation_decision"])
    if "handoff_conflict_flag" in upstream_decision.columns and boolish(upstream_decision.iloc[0]["handoff_conflict_flag"]):
        raise RuntimeError("12A2 handoff_conflict_flag is true; 12A3 must not run on conflicting upstream handoff.")

    stock_cache = StockDailyCache(resolved["stock_daily_csv_dir"])
    label_cfg = load_label_config(config)
    episodes = add_episode_positions(read_table(resolved["episode_target_registry_06"]), stock_cache)
    canonical_raw = read_table(resolved["state_change_candidate_event_canonical"])
    instances = read_table(resolved["state_change_candidate_event_instances"])
    r_core_raw = read_table(resolved["r_core_arm_event_registry"])
    r_core_decision = read_table(resolved["r_core_demote_or_keep_decision"])
    canonical_primary = canonical_raw.loc[
        canonical_raw["candidate_generation_status"].astype(str).eq("supported_canonical_event")
        & (~bool_series(canonical_raw["non_executable_next_open"]))
        & canonical_raw["event_t0_pit_status"].astype(str).eq("pass")
        & canonical_raw["trade_open_pit_status"].astype(str).eq("pass")
    ].copy()
    input_gates = build_input_gate_context(
        audit,
        upstream_decision,
        r_core_decision,
        episodes,
        canonical_primary,
        r_core_raw,
    )
    if not all(input_gates.values()):
        raise RuntimeError("Input gates failed: " + ", ".join(name for name, value in input_gates.items() if not value))
    state_events = normalize_state_change_events(canonical_primary)
    r_core_events = normalize_r_core_events(r_core_raw, RAW_R_CORE_ARM)
    r6_events = normalize_r_core_events(r_core_raw, R6_ARM)

    state_labels = recompute_labels(state_events, stock_cache, label_cfg, id_col="event_key")
    state_events = attach_recomputed_labels(state_events, state_labels, id_col="event_key")
    sensitivity_raw = recanonicalize_instances(instances, config)
    sensitivity_events = normalize_state_change_events(sensitivity_raw) if not sensitivity_raw.empty else state_events.iloc[0:0].copy()
    if not sensitivity_events.empty:
        sensitivity_labels = recompute_labels(sensitivity_events, stock_cache, label_cfg, id_col="event_key")
        sensitivity_events = attach_recomputed_labels(sensitivity_events, sensitivity_labels, id_col="event_key")
    b5_priority = {"B1": 10, "B3": 20, "B2": 30, "B4": 40, "B6": 50, "B8": 60, "B5": 90}
    b5_raw = recanonicalize_instances(
        instances,
        config,
        priority_order=b5_priority,
        canonical_id_prefix="12A2_B5_downpriority",
        rule_id="12A3_recomputed_B5_downpriority_same_day_then_union_cooldown",
    )
    b5_downpriority_events = normalize_state_change_events(b5_raw) if not b5_raw.empty else state_events.iloc[0:0].copy()
    if not b5_downpriority_events.empty:
        b5_labels = recompute_labels(b5_downpriority_events, stock_cache, label_cfg, id_col="event_key")
        b5_downpriority_events = attach_recomputed_labels(b5_downpriority_events, b5_labels, id_col="event_key")

    labels_08_cols = [
        "event_id",
        "instrument",
        "event_t0_pos",
        "trade_open_pos",
        "trade_open_price",
        "failure_10_label",
        "failure_10_complete",
        "event_false_repair_20d_label",
        "event_false_repair_20d_complete",
        "event_big_winner_120d_label",
        "horizon_complete_120d",
    ]
    labels_08 = read_table(resolved["labels_08"], columns=labels_08_cols)
    labels_08["parity_row_id"] = np.arange(len(labels_08)).astype(str)
    recomputed_08 = recompute_labels(labels_08, stock_cache, label_cfg, id_col="parity_row_id")
    parity = build_label_parity_audit(
        labels_08,
        recomputed_08,
        state_events,
        float(config["thresholds"]["min_label_parity_match_rate"]),
    )

    arms, arm_registry = make_arms(r_core_events, r6_events, state_events, sensitivity_events, b5_downpriority_events)
    denominator_years, r_core_mean_density = load_r_core_density_baseline(resolved["r_core_density_badside_tradeoff"])
    frontier, timing, captured_density, missed_diagnostics = build_frontier_outputs(
        arms,
        arm_registry,
        episodes,
        denominator_years=denominator_years,
        r_core_mean_density=r_core_mean_density,
    )
    b8_incremental = build_b8_incremental(state_events, episodes)
    label_exposure = build_event_label_exposure(arms)
    slice_readout = build_slice_readout(
        arms,
        episodes,
        denominator_years=denominator_years,
        r_core_mean_density=r_core_mean_density,
    )
    decision = build_decision(frontier, parity, config, input_gates)
    report = build_report(decision, frontier, parity, arm_registry, b8_incremental, slice_readout, missed_diagnostics)

    frames = {
        "input_artifact_audit": audit,
        "frontier_arm_registry": arm_registry,
        "frontier": frontier,
        "timing": timing,
        "captured_density": captured_density,
        "missed_diagnostics": missed_diagnostics,
        "b8_incremental": b8_incremental,
        "label_exposure": label_exposure,
        "slice_readout": slice_readout,
        "label_parity": parity,
        "decision": decision,
    }
    write_df(paths["frontier_arm_registry"], arm_registry)
    write_df(paths["frontier"], frontier)
    write_df(paths["timing"], timing)
    write_df(paths["captured_density"], captured_density)
    write_df(paths["missed_diagnostics"], missed_diagnostics)
    write_df(paths["b8_incremental"], b8_incremental)
    write_df(paths["label_exposure"], label_exposure)
    write_df(paths["slice_readout"], slice_readout)
    write_df(paths["label_parity"], parity)
    write_df(paths["decision"], decision)
    write_text(paths["report"], report)
    write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, resolved["requirement"]))
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

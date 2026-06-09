from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PENDING_DIR = EXPERIMENT_DIR.parent
PROJECT_ROOT = EXPERIMENT_DIR.parents[2]
REVERSE_PIPELINE_PATH = (
    PENDING_DIR / "02_big_winner_reverse_lifecycle_profile_v0" / "code" / "pipeline.py"
)

_SPEC = importlib.util.spec_from_file_location(
    "reverse_lifecycle_pipeline_v0", REVERSE_PIPELINE_PATH
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load reverse lifecycle pipeline from {REVERSE_PIPELINE_PATH}")
_reverse = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _reverse
_SPEC.loader.exec_module(_reverse)


MISSING_INSUFFICIENT_LOOKBACK = _reverse.MISSING_INSUFFICIENT_LOOKBACK
MISSING_EVENT_ABSENT = _reverse.MISSING_EVENT_ABSENT
MISSING_SOURCE_FIELD = _reverse.MISSING_SOURCE_FIELD
MISSING_UNIT_INCOMPATIBLE = _reverse.MISSING_UNIT_INCOMPATIBLE
MISSING_OUT_OF_COVERAGE = _reverse.MISSING_OUT_OF_COVERAGE
NOT_MISSING = _reverse.NOT_MISSING
CENSORED_INCOMPLETE_HORIZON = "censored_incomplete_horizon"
NON_EXECUTABLE_NEXT_OPEN = "non_executable_next_open"
CROSS_SPLIT_BOUNDARY_UNUSABLE = "cross_split_boundary_unusable"


SNAPSHOT_COLUMNS = [
    "close_to_ema20",
    "close_to_ema60",
    "ema20_slope_20d",
    "ema60_slope_20d",
    "return_5d",
    "return_20d",
    "return_60d",
    "amount_ratio_20d",
    "amount_ratio_60d",
    "turnover_ratio_20d",
    "derived_daily_vwap_available",
    "close_to_derived_daily_vwap",
    "vwap_reclaim_flag",
    "intraday_range_pct",
    "close_position_in_range",
    "upper_shadow_pct",
    "gap_open_pct",
    "gap_fade_flag",
    "atr_20_pct",
    "market_return_20d",
    "market_drawdown_60d",
    "market_volatility_20d",
    "market_regime_bucket",
    "benchmark_alias",
    "stock_vs_market_20d",
]


@dataclass(frozen=True)
class SplitConfig:
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    robustness_start: str
    latest_label_complete_t0_date: str


@dataclass(frozen=True)
class EventParams:
    prior_lookback_sessions: int
    seed_low_lookback_sessions: int
    anchor_search_horizon_sessions: int
    rank_jump_threshold: float
    rank_jump_window: int
    persistence_window: int
    persistence_floor: float
    persistence_coverage: float
    amount_ratio_20d_gate: float
    plus20_threshold: float
    continuation_window: int
    continuation_rank_floor: float
    continuation_rank_coverage: float
    continuation_amount_floor: float
    continuation_amount_coverage: float


@dataclass(frozen=True)
class FalseRepairParams:
    drawdown_floor: float
    insufficient_runup_floor: float


@dataclass(frozen=True)
class DensityParams:
    seed_density_window: int
    reclaim_density_window: int
    event_density_window: int


@dataclass(frozen=True)
class LabelParams:
    confirm_horizon: int
    confirm_upper: float
    confirm_lower: float
    failure_horizon: int
    failure_lower: float
    continuous_horizons: tuple[int, ...]
    near_winner_horizon: int
    near_winner_mfe_lower: float
    near_winner_mfe_upper: float


@dataclass(frozen=True)
class MatchConfig:
    max_controls_per_event: int
    match_fields: tuple[str, ...]


def parse_date(value: Any) -> pd.Timestamp:
    return _reverse.parse_date(value)


def date_str(value: Any) -> str:
    return _reverse.date_str(value)


def week_start(value: Any) -> str:
    return _reverse.week_start(value)


def safe_lift(event_rate: float, baseline_rate: float) -> float:
    return _reverse.safe_lift(event_rate, baseline_rate)


def safe_rate(success: int, total: int) -> float:
    return float(success / total) if total else np.nan


def safe_mean(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.mean()) if len(clean) else np.nan


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(cwd: str | Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(cwd),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def latest_complete_t0_date(calendar: Iterable[str], horizon_sessions: int) -> str:
    sessions = sorted(date_str(value) for value in calendar)
    if len(sessions) <= horizon_sessions:
        raise ValueError("Calendar is shorter than label horizon")
    return sessions[-horizon_sessions - 1]


def split_for_t0(value: Any, split_config: SplitConfig) -> str:
    text = date_str(value)
    if split_config.train_start <= text <= split_config.train_end:
        return "train"
    if split_config.validation_start <= text <= split_config.validation_end:
        return "validation"
    if split_config.robustness_start <= text <= split_config.latest_label_complete_t0_date:
        return "robustness"
    return "outside_split"


def validate_required_inputs(paths: dict[str, Path]) -> None:
    for name, path in paths.items():
        if name.endswith("_dir"):
            if not path.is_dir():
                raise FileNotFoundError(f"Missing required input directory {name}: {path}")
        elif not path.is_file():
            raise FileNotFoundError(f"Missing required input file {name}: {path}")


def resolve_vwap_source_policy(source_coverage_audit: pd.DataFrame) -> dict[str, Any]:
    required = {"category", "support_state", "units"}
    if not required.issubset(source_coverage_audit.columns):
        return {"compatible": False, "reason": "source_coverage_missing_required_columns"}
    indexed = source_coverage_audit.set_index("category", drop=False)
    rows = []
    for category in ["historical_raw_daily_bars", "historical_qfq_daily_bars"]:
        if category not in indexed.index:
            return {"compatible": False, "reason": f"missing_{category}"}
        row = indexed.loc[category]
        rows.append(row.iloc[0] if isinstance(row, pd.DataFrame) else row)
    raw_row, qfq_row = rows
    raw_supported = str(raw_row.get("support_state", "")) == "supported"
    qfq_supported = str(qfq_row.get("support_state", "")) == "supported"
    raw_units = str(raw_row.get("units", ""))
    qfq_units = str(qfq_row.get("units", ""))
    units_ok = (
        "volume=shares" in raw_units
        and "money=CNY" in raw_units
        and "volume=shares" in qfq_units
        and "money=CNY" in qfq_units
    )
    return {
        "compatible": bool(raw_supported and qfq_supported and units_ok),
        "reason": "raw_qfq_same_date_money_cny_volume_shares"
        if raw_supported and qfq_supported and units_ok
        else "raw_qfq_daily_or_units_not_supported",
        "raw_units": raw_units,
        "qfq_units": qfq_units,
    }


def write_dataframe(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    if path.suffix == ".parquet":
        out.to_parquet(path, index=False)
    else:
        out.to_csv(path, index=False)
    return path


def concat_or_empty(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def most_common_text(values: pd.Series) -> str:
    clean = values.dropna().astype(str)
    if clean.empty:
        return ""
    return str(clean.mode().iloc[0])


def membership_asof(membership: pd.DataFrame, date: str) -> dict[str, Any]:
    if membership.empty:
        return {}
    dates = membership["usable_trade_date"].astype(str).to_numpy()
    idx = np.searchsorted(dates, date, side="right") - 1
    if idx < 0:
        return {}
    return membership.iloc[int(idx)].to_dict()


def extract_candidate_seed_lows(
    features: pd.DataFrame,
    *,
    membership_dates: set[str],
    params: EventParams,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    low = pd.to_numeric(features["low"], errors="coerce").to_numpy()
    dates = features["date"].astype(str).to_numpy()
    window = params.seed_low_lookback_sessions
    start_pos = max(window, params.prior_lookback_sessions)
    for pos in range(start_pos, len(features)):
        current_date = str(dates[pos])
        if current_date not in membership_dates:
            continue
        current_low = low[pos]
        if not np.isfinite(current_low) or current_low <= 0:
            continue
        lookback = low[pos - window : pos + 1]
        if len(lookback) != window + 1 or not np.isfinite(lookback).all():
            continue
        if current_low != np.nanmin(lookback):
            continue
        rows.append(
            {
                "instrument": str(features.at[pos, "instrument"]),
                "candidate_seed_low_date": current_date,
                "candidate_seed_low_pos": pos,
                "qfq_low_at_seed": float(current_low),
                "missing_reason": NOT_MISSING,
            }
        )
    return pd.DataFrame(rows)


def apply_position_density(
    frame: pd.DataFrame,
    *,
    pos_col: str,
    date_col: str,
    cluster_col: str,
    stage: str,
    window: int,
    kept_col: str = "density_kept",
) -> pd.DataFrame:
    if frame.empty:
        out = frame.copy()
        out[cluster_col] = pd.Series(dtype="object")
        out[kept_col] = pd.Series(dtype="bool")
        return out
    rows: list[pd.DataFrame] = []
    for instrument, group in frame.groupby("instrument", sort=True):
        ordered = group.sort_values([pos_col, date_col]).copy()
        cluster_ids: list[str] = []
        kept: list[bool] = []
        cluster_no = -1
        seed_end: int | None = None
        for row in ordered.itertuples(index=False):
            pos = int(getattr(row, pos_col))
            if seed_end is None or pos > seed_end:
                cluster_no += 1
                seed_end = pos + window
                is_kept = True
            else:
                is_kept = False
            cluster_ids.append(f"{instrument}_{stage}_{cluster_no:05d}")
            kept.append(is_kept)
        ordered[cluster_col] = cluster_ids
        ordered[kept_col] = kept
        rows.append(ordered)
    return pd.concat(rows, ignore_index=True)


def build_reclaim_rows(
    instrument: str,
    features: pd.DataFrame,
    seed_rows: pd.DataFrame,
    *,
    params: EventParams,
    density_params: DensityParams,
) -> pd.DataFrame:
    if seed_rows.empty:
        return pd.DataFrame(
            columns=[
                "instrument",
                "candidate_seed_low_date",
                "candidate_seed_low_pos",
                "seed_cluster_id",
                "first_ema60_reclaim_date",
                "first_ema60_reclaim_pos",
                "first_ema60_reclaim_missing_reason",
                "reclaim_cluster_id",
                "density_kept",
            ]
        )
    rows: list[dict[str, Any]] = []
    for seed in seed_rows.loc[seed_rows["density_kept"]].itertuples(index=False):
        seed_pos = int(seed.candidate_seed_low_pos)
        search_end = seed_pos + params.anchor_search_horizon_sessions
        end_pos = min(search_end, len(features) - 1)
        reclaim_pos, reason = _reverse.first_moving_average_reclaim(
            features,
            start_pos=seed_pos,
            end_pos=end_pos,
            ma_column="ema60",
        )
        if reclaim_pos is None and search_end >= len(features):
            reason = MISSING_OUT_OF_COVERAGE
        rows.append(
            {
                "instrument": instrument,
                "candidate_seed_low_date": seed.candidate_seed_low_date,
                "candidate_seed_low_pos": seed_pos,
                "seed_cluster_id": seed.seed_cluster_id,
                "first_ema60_reclaim_date": str(features.at[reclaim_pos, "date"])
                if reclaim_pos is not None
                else "",
                "first_ema60_reclaim_pos": int(reclaim_pos)
                if reclaim_pos is not None
                else -1,
                "first_ema60_reclaim_missing_reason": reason,
            }
        )
    reclaim = pd.DataFrame(rows)
    present = reclaim.loc[
        reclaim["first_ema60_reclaim_missing_reason"] == NOT_MISSING
    ].copy()
    absent = reclaim.loc[
        reclaim["first_ema60_reclaim_missing_reason"] != NOT_MISSING
    ].copy()
    present = apply_position_density(
        present,
        pos_col="first_ema60_reclaim_pos",
        date_col="first_ema60_reclaim_date",
        cluster_col="reclaim_cluster_id",
        stage="reclaim",
        window=density_params.reclaim_density_window,
    )
    if not absent.empty:
        absent["reclaim_cluster_id"] = ""
        absent["density_kept"] = False
    return pd.concat([present, absent], ignore_index=True)


def false_repair_metrics_asof(
    daily: pd.DataFrame,
    *,
    reclaim_pos: int,
    t0_pos: int,
    params: FalseRepairParams,
) -> dict[str, Any]:
    reclaim_close = daily.at[reclaim_pos, "close"]
    if pd.isna(reclaim_close) or reclaim_close <= 0:
        return {
            "false_repair_observed_asof_t0": False,
            "false_repair_drawdown_trigger_date": "",
            "false_repair_10d_diagnostic": False,
            "false_repair_20d_diagnostic": False,
            "insufficient_runup_20d_diagnostic": False,
            "future_false_repair_any_diagnostic": False,
            "false_repair_missing_reason": MISSING_SOURCE_FIELD,
        }
    close = pd.to_numeric(daily["close"], errors="coerce")
    high = pd.to_numeric(daily["high"], errors="coerce")
    trigger_date = ""
    end_asof = min(t0_pos, len(daily) - 1)
    for pos in range(reclaim_pos, end_asof + 1):
        value = close.iloc[pos]
        if pd.notna(value) and value / reclaim_close - 1.0 <= params.drawdown_floor:
            trigger_date = str(daily.at[pos, "date"])
            break
    diagnostics: dict[str, Any] = {}
    missing_reason = NOT_MISSING
    for horizon in [10, 20]:
        end_pos = reclaim_pos + horizon
        if end_pos >= len(daily):
            diagnostics[f"false_repair_{horizon}d_diagnostic"] = False
            missing_reason = MISSING_OUT_OF_COVERAGE
            continue
        window_close = close.iloc[reclaim_pos : end_pos + 1]
        diagnostics[f"false_repair_{horizon}d_diagnostic"] = bool(
            ((window_close / reclaim_close - 1.0) <= params.drawdown_floor).any()
        )
    if reclaim_pos + 20 >= len(daily):
        insufficient = False
        missing_reason = MISSING_OUT_OF_COVERAGE
    else:
        runup = high.iloc[reclaim_pos : reclaim_pos + 21].max() / reclaim_close - 1.0
        insufficient = bool(pd.notna(runup) and runup < params.insufficient_runup_floor)
    diagnostics["insufficient_runup_20d_diagnostic"] = insufficient
    future_any = bool(
        diagnostics.get("false_repair_10d_diagnostic", False)
        or diagnostics.get("false_repair_20d_diagnostic", False)
        or diagnostics.get("insufficient_runup_20d_diagnostic", False)
    )
    return {
        "false_repair_observed_asof_t0": bool(trigger_date),
        "false_repair_drawdown_trigger_date": trigger_date,
        "false_repair_10d_diagnostic": bool(
            diagnostics.get("false_repair_10d_diagnostic", False)
        ),
        "false_repair_20d_diagnostic": bool(
            diagnostics.get("false_repair_20d_diagnostic", False)
        ),
        "insufficient_runup_20d_diagnostic": bool(insufficient),
        "future_false_repair_any_diagnostic": future_any,
        "false_repair_missing_reason": missing_reason,
    }


def evaluate_s3_or_baseline(
    instrument: str,
    daily: pd.DataFrame,
    reclaim_row: dict[str, Any],
    *,
    params: EventParams,
    false_params: FalseRepairParams,
    split_config: SplitConfig,
) -> dict[str, Any] | None:
    r0 = int(reclaim_row["first_ema60_reclaim_pos"])
    if r0 < 0:
        return None
    rank_jump_pos: int | None = None
    rank_end = min(len(daily) - 1, r0 + params.rank_jump_window)
    for pos in range(r0, rank_end + 1):
        value = daily.at[pos, "stock_vs_market_20d"]
        if pd.notna(value) and float(value) >= params.rank_jump_threshold:
            rank_jump_pos = pos
            break
    base = {
        "instrument": instrument,
        "candidate_seed_low_date": reclaim_row["candidate_seed_low_date"],
        "candidate_seed_low_pos": int(reclaim_row["candidate_seed_low_pos"]),
        "seed_cluster_id": reclaim_row.get("seed_cluster_id", ""),
        "anchor_date": reclaim_row["first_ema60_reclaim_date"],
        "anchor_pos": r0,
        "reclaim_cluster_id": reclaim_row.get("reclaim_cluster_id", ""),
        "rank_jump_date": "",
        "rank_jump_pos": -1,
        "rank_persistence_confirmed": False,
        "rank_persistence_coverage": np.nan,
        "event_kind": "",
        "missing_reason": "",
    }
    if rank_jump_pos is None:
        baseline_pos = r0 + params.rank_jump_window
        if baseline_pos >= len(daily):
            base.update(
                {
                    "event_kind": "baseline_candidate",
                    "baseline_failure_type": "rank_jump_failed_out_of_coverage",
                    "baseline_t0_pos": -1,
                    "baseline_t0_date": "",
                    "missing_reason": MISSING_OUT_OF_COVERAGE,
                }
            )
            return base
        base.update(
            {
                "event_kind": "baseline_candidate",
                "baseline_failure_type": "rank_jump_failed",
                "baseline_t0_pos": baseline_pos,
                "baseline_t0_date": str(daily.at[baseline_pos, "date"]),
                "missing_reason": NOT_MISSING,
            }
        )
        return base

    confirm_pos = rank_jump_pos + params.persistence_window
    base["rank_jump_pos"] = rank_jump_pos
    base["rank_jump_date"] = str(daily.at[rank_jump_pos, "date"])
    if confirm_pos >= len(daily):
        base.update(
            {
                "event_kind": "baseline_candidate",
                "baseline_failure_type": "rank_persistence_out_of_coverage",
                "baseline_t0_pos": -1,
                "baseline_t0_date": "",
                "missing_reason": MISSING_OUT_OF_COVERAGE,
            }
        )
        return base
    segment = pd.to_numeric(
        daily.loc[rank_jump_pos + 1 : confirm_pos, "stock_vs_market_20d"],
        errors="coerce",
    )
    coverage = float((segment >= params.persistence_floor).sum() / params.persistence_window)
    base["rank_persistence_coverage"] = coverage
    if coverage >= params.persistence_coverage:
        repair = false_repair_metrics_asof(
            daily,
            reclaim_pos=r0,
            t0_pos=confirm_pos,
            params=false_params,
        )
        base.update(
            {
                "event_kind": "E_S3",
                "event_t0_pos": confirm_pos,
                "event_t0_date": str(daily.at[confirm_pos, "date"]),
                "rank_persistence_confirmed": True,
                "missing_reason": NOT_MISSING,
                **repair,
            }
        )
        base["event_invalidated_false_repair"] = bool(
            base["false_repair_observed_asof_t0"]
        )
        base["split"] = split_for_t0(base["event_t0_date"], split_config)
        return base
    base.update(
        {
            "event_kind": "baseline_candidate",
            "baseline_failure_type": "rank_persistence_failed",
            "baseline_t0_pos": confirm_pos,
            "baseline_t0_date": str(daily.at[confirm_pos, "date"]),
            "missing_reason": NOT_MISSING,
        }
    )
    return base


def g_s2_passed(daily: pd.DataFrame, *, reclaim_pos: int, t0_pos: int, params: EventParams) -> bool:
    segment = daily.iloc[reclaim_pos : t0_pos + 1]
    amount_ok = bool((pd.to_numeric(segment["amount_ratio_20d"], errors="coerce") >= params.amount_ratio_20d_gate).any())
    if not amount_ok:
        return False
    vwap_ok = False
    if "qfq_daily_vwap" in daily.columns:
        vwap = daily.at[t0_pos, "qfq_daily_vwap"]
        close = daily.at[t0_pos, "close"]
        vwap_ok = bool(pd.notna(vwap) and vwap > 0 and close >= vwap)
    range_ok = bool(daily.at[t0_pos, "close_position_in_range"] >= 0.5)
    return bool(vwap_ok or range_ok)


def c_s6_confirmation(
    daily: pd.DataFrame,
    *,
    reclaim_pos: int,
    base_pos: int,
    params: EventParams,
) -> dict[str, Any]:
    base_close = daily.at[base_pos, "close"]
    if pd.isna(base_close) or base_close <= 0:
        return {"confirmed": False, "confirm_date": "", "plus20_state_date": ""}
    plus20_pos: int | None = None
    end = min(len(daily) - 1, reclaim_pos + params.anchor_search_horizon_sessions)
    for pos in range(reclaim_pos + 1, end + 1):
        value = daily.at[pos, "close"]
        if pd.notna(value) and value / base_close - 1.0 >= params.plus20_threshold:
            plus20_pos = pos
            break
    if plus20_pos is None:
        return {"confirmed": False, "confirm_date": "", "plus20_state_date": ""}
    confirm_pos = plus20_pos + params.continuation_window
    if confirm_pos >= len(daily):
        return {
            "confirmed": False,
            "confirm_date": "",
            "plus20_state_date": str(daily.at[plus20_pos, "date"]),
        }
    window = daily.iloc[plus20_pos + 1 : confirm_pos + 1]
    rank = pd.to_numeric(window["stock_vs_market_20d"], errors="coerce")
    amount = pd.to_numeric(window["amount_ratio_20d"], errors="coerce")
    rank_cov = float((rank >= params.continuation_rank_floor).sum() / params.continuation_window)
    amount_cov = float((amount >= params.continuation_amount_floor).sum() / params.continuation_window)
    confirmed = bool(
        rank_cov >= params.continuation_rank_coverage
        or amount_cov >= params.continuation_amount_coverage
    )
    return {
        "confirmed": confirmed,
        "confirm_date": str(daily.at[confirm_pos, "date"]) if confirmed else "",
        "plus20_state_date": str(daily.at[plus20_pos, "date"]),
        "rank_coverage": rank_cov,
        "amount_coverage": amount_cov,
    }


def snapshot_fields(daily: pd.DataFrame, pos: int) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for column in SNAPSHOT_COLUMNS:
        row[column] = daily.at[pos, column] if column in daily.columns else np.nan
    return row


def execution_status(
    daily: pd.DataFrame,
    *,
    t0_pos: int,
    board_bucket: str,
    is_st: bool,
) -> dict[str, Any]:
    trade_pos = t0_pos + 1
    if trade_pos >= len(daily):
        return {
            "trade_open_pos": -1,
            "trade_open_date": "",
            "trade_open_price": np.nan,
            "non_executable_next_open": True,
            "non_executable_reason": MISSING_OUT_OF_COVERAGE,
            "limit_threshold_status": MISSING_OUT_OF_COVERAGE,
        }
    row = daily.iloc[trade_pos]
    required = ["open", "high", "low", "close", "volume", "money", "factor"]
    if any(column not in row.index or pd.isna(row[column]) for column in required):
        return {
            "trade_open_pos": trade_pos,
            "trade_open_date": str(row["date"]),
            "trade_open_price": row.get("open", np.nan),
            "non_executable_next_open": True,
            "non_executable_reason": "missing_open_or_volume",
            "limit_threshold_status": "not_evaluated",
        }
    if float(row["volume"]) <= 0 or float(row["money"]) <= 0 or float(row["open"]) <= 0:
        return {
            "trade_open_pos": trade_pos,
            "trade_open_date": str(row["date"]),
            "trade_open_price": float(row["open"]) if pd.notna(row["open"]) else np.nan,
            "non_executable_next_open": True,
            "non_executable_reason": "missing_open_or_volume",
            "limit_threshold_status": "not_evaluated",
        }
    if is_st:
        threshold = 0.05
        threshold_status = "st_5pct"
    elif board_bucket == "main_board":
        threshold = 0.10
        threshold_status = "main_board_10pct"
    elif board_bucket == "chinext":
        threshold = 0.20
        threshold_status = "chinext_20pct"
    else:
        return {
            "trade_open_pos": trade_pos,
            "trade_open_date": str(row["date"]),
            "trade_open_price": float(row["open"]),
            "non_executable_next_open": True,
            "non_executable_reason": "limit_rule_unavailable",
            "limit_threshold_status": "limit_rule_unavailable",
        }
    one_price = (
        math.isclose(float(row["open"]), float(row["high"]), rel_tol=0, abs_tol=1e-8)
        and math.isclose(float(row["open"]), float(row["low"]), rel_tol=0, abs_tol=1e-8)
        and math.isclose(float(row["open"]), float(row["close"]), rel_tol=0, abs_tol=1e-8)
    )
    prev = daily.iloc[trade_pos - 1]
    raw_open = float(row["open"]) / float(row["factor"]) if float(row["factor"]) > 0 else np.nan
    prev_factor = float(prev["factor"]) if pd.notna(prev["factor"]) else np.nan
    prev_raw_close = (
        float(prev["close"]) / prev_factor if pd.notna(prev_factor) and prev_factor > 0 else np.nan
    )
    pct = raw_open / prev_raw_close - 1.0 if prev_raw_close and prev_raw_close > 0 else np.nan
    if one_price and pd.notna(pct) and abs(abs(float(pct)) - threshold) <= 0.005:
        return {
            "trade_open_pos": trade_pos,
            "trade_open_date": str(row["date"]),
            "trade_open_price": float(row["open"]),
            "non_executable_next_open": True,
            "non_executable_reason": "one_price_limit_open_proxy",
            "limit_threshold_status": threshold_status,
        }
    return {
        "trade_open_pos": trade_pos,
        "trade_open_date": str(row["date"]),
        "trade_open_price": float(row["open"]),
        "non_executable_next_open": False,
        "non_executable_reason": "",
        "limit_threshold_status": threshold_status,
    }


def barrier_label(
    daily: pd.DataFrame,
    *,
    trade_pos: int,
    trade_price: float,
    horizon: int,
    upper: float | None,
    lower: float | None,
) -> tuple[int | float, bool]:
    if trade_pos < 0 or pd.isna(trade_price) or trade_price <= 0:
        return np.nan, False
    end_pos = trade_pos + horizon
    if end_pos >= len(daily):
        return np.nan, False
    for pos in range(trade_pos, end_pos + 1):
        low_ret = daily.at[pos, "low"] / trade_price - 1.0
        high_ret = daily.at[pos, "high"] / trade_price - 1.0
        lower_hit = lower is not None and pd.notna(low_ret) and low_ret <= lower
        upper_hit = upper is not None and pd.notna(high_ret) and high_ret >= upper
        if lower_hit:
            return -1 if upper is not None else 1, True
        if upper_hit:
            return 1, True
    return 0, True


def continuous_forward(
    daily: pd.DataFrame, *, trade_pos: int, trade_price: float, horizon: int
) -> dict[str, Any]:
    if trade_pos < 0 or pd.isna(trade_price) or trade_price <= 0:
        return {
            f"forward_return_{horizon}d": np.nan,
            f"mfe_{horizon}d": np.nan,
            f"mae_{horizon}d": np.nan,
            f"horizon_complete_{horizon}d": False,
        }
    end_pos = trade_pos + horizon
    if end_pos >= len(daily):
        return {
            f"forward_return_{horizon}d": np.nan,
            f"mfe_{horizon}d": np.nan,
            f"mae_{horizon}d": np.nan,
            f"horizon_complete_{horizon}d": False,
        }
    segment = daily.iloc[trade_pos : end_pos + 1]
    return {
        f"forward_return_{horizon}d": float(daily.at[end_pos, "close"]) / trade_price - 1.0,
        f"mfe_{horizon}d": float(segment["high"].max()) / trade_price - 1.0,
        f"mae_{horizon}d": float(segment["low"].min()) / trade_price - 1.0,
        f"horizon_complete_{horizon}d": True,
    }


def label_row(
    *,
    entity_id: str,
    event_type: str,
    split: str,
    regime_bucket: str,
    daily: pd.DataFrame,
    trade: dict[str, Any],
    label_params: LabelParams,
) -> dict[str, Any]:
    base = {
        "event_id": entity_id,
        "event_type": event_type,
        "split": split,
        "regime_bucket": regime_bucket,
        "trade_open_date": trade["trade_open_date"],
        "trade_open_price": trade["trade_open_price"],
        "non_executable_next_open": bool(trade["non_executable_next_open"]),
        "non_executable_reason": trade["non_executable_reason"],
        "limit_threshold_status": trade["limit_threshold_status"],
    }
    if bool(trade["non_executable_next_open"]):
        base.update(
            {
                "confirm_20_label": np.nan,
                "confirm_20_complete": False,
                "failure_10_label": np.nan,
                "failure_10_complete": False,
            }
        )
    else:
        confirm, confirm_complete = barrier_label(
            daily,
            trade_pos=int(trade["trade_open_pos"]),
            trade_price=float(trade["trade_open_price"]),
            horizon=label_params.confirm_horizon,
            upper=label_params.confirm_upper,
            lower=label_params.confirm_lower,
        )
        failure, failure_complete = barrier_label(
            daily,
            trade_pos=int(trade["trade_open_pos"]),
            trade_price=float(trade["trade_open_price"]),
            horizon=label_params.failure_horizon,
            upper=None,
            lower=label_params.failure_lower,
        )
        base.update(
            {
                "confirm_20_label": confirm,
                "confirm_20_complete": bool(confirm_complete),
                "failure_10_label": failure,
                "failure_10_complete": bool(failure_complete),
            }
        )
    for horizon in label_params.continuous_horizons:
        if bool(trade["non_executable_next_open"]):
            continuous = {
                f"forward_return_{horizon}d": np.nan,
                f"mfe_{horizon}d": np.nan,
                f"mae_{horizon}d": np.nan,
                f"horizon_complete_{horizon}d": False,
            }
        else:
            continuous = continuous_forward(
                daily,
                trade_pos=int(trade["trade_open_pos"]),
                trade_price=float(trade["trade_open_price"]),
                horizon=horizon,
            )
        base.update(continuous)
    base["forward_return_60d_status"] = (
        NOT_MISSING if base.get("horizon_complete_60d") else CENSORED_INCOMPLETE_HORIZON
    )
    base["main_label_complete"] = bool(
        base.get("confirm_20_complete") and base.get("failure_10_complete")
    )
    return base


def near_winner_profile(
    daily: pd.DataFrame,
    *,
    trade: dict[str, Any],
    params: LabelParams,
) -> dict[str, Any]:
    if bool(trade["non_executable_next_open"]):
        return {
            "near_winner_flag": False,
            "near_winner_forward_mfe_120d": np.nan,
            "near_winner_status": NON_EXECUTABLE_NEXT_OPEN,
        }
    trade_pos = int(trade["trade_open_pos"])
    end_pos = trade_pos + params.near_winner_horizon
    if end_pos >= len(daily):
        return {
            "near_winner_flag": False,
            "near_winner_forward_mfe_120d": np.nan,
            "near_winner_status": CENSORED_INCOMPLETE_HORIZON,
        }
    price = float(trade["trade_open_price"])
    segment = daily.iloc[trade_pos : end_pos + 1]
    mfe = float(segment["high"].max()) / price - 1.0
    return {
        "near_winner_flag": bool(
            params.near_winner_mfe_lower <= mfe < params.near_winner_mfe_upper
        ),
        "near_winner_forward_mfe_120d": mfe,
        "near_winner_status": NOT_MISSING,
    }


def bucket_distance(left: Any, right: Any) -> int:
    if pd.isna(left) or pd.isna(right):
        return 1
    left_text = str(left)
    right_text = str(right)
    if left_text == right_text:
        return 0
    if left_text.startswith("q") and right_text.startswith("q"):
        try:
            return abs(int(left_text[1:]) - int(right_text[1:]))
        except ValueError:
            return 1
    return 1


def assign_match_buckets(events: pd.DataFrame, baselines: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_out = events.copy()
    base_out = baselines.copy()
    specs = {
        "market_cap_bucket": "total_market_cap_cny",
        "liquidity_bucket": "liquidity_money_20d",
        "prior_return_20d_bucket": "prior_return_20d",
        "prior_return_60d_bucket": "prior_return_60d",
        "prior_drawdown_bucket": "prior_drawdown",
        "volatility_bucket": "volatility_20d",
    }
    combined = pd.concat(
        [event_out[list(specs.values())], base_out[list(specs.values())]],
        ignore_index=True,
    )
    for bucket_col, value_col in specs.items():
        values = pd.to_numeric(combined[value_col], errors="coerce")
        labels = [f"q{i}" for i in range(1, 6)]
        try:
            binned = pd.qcut(values, q=5, labels=labels, duplicates="drop")
        except ValueError:
            binned = pd.Series(["unknown"] * len(values), dtype="object")
        binned = binned.astype("object").where(~pd.isna(binned), "unknown")
        event_out[bucket_col] = binned.iloc[: len(event_out)].to_numpy()
        base_out[bucket_col] = binned.iloc[len(event_out) :].to_numpy()
    return event_out, base_out


def match_baselines(
    events: pd.DataFrame,
    baselines: pd.DataFrame,
    *,
    family: str,
    match_config: MatchConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if events.empty:
        return pd.DataFrame(), pd.DataFrame()
    pool = baselines.loc[baselines["baseline_family"] == family].copy()
    if pool.empty:
        audit = events[["event_id", "split"]].copy()
        audit["baseline_family"] = family
        audit["matched_baseline_count"] = 0
        audit["unmatched_reason"] = "no_baseline_family_pool"
        audit["cross_split_boundary_unusable_count"] = 0
        return pd.DataFrame(), audit
    pool["_anchor_week"] = pool["anchor_date"].map(week_start)
    event_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for event in events.itertuples(index=False):
        item = event._asdict()
        week = week_start(item["anchor_date"])
        same_week = pool.loc[pool["_anchor_week"] == week].copy()
        cross_split = int((same_week["split"] != item["split"]).sum()) if not same_week.empty else 0
        candidates = same_week.loc[
            (same_week["split"] == item["split"])
            & (same_week["instrument"] != item["instrument"])
            & (same_week["market_regime_bucket"].astype(str) == str(item["market_regime_bucket"]))
        ].copy()
        if candidates.empty:
            reason = "no_same_week_same_split_regime_baseline"
            if cross_split:
                reason = CROSS_SPLIT_BOUNDARY_UNUSABLE
            audit_rows.append(
                {
                    "event_id": item["event_id"],
                    "split": item["split"],
                    "baseline_family": family,
                    "matched_baseline_count": 0,
                    "unmatched_reason": reason,
                    "cross_split_boundary_unusable_count": cross_split,
                }
            )
            continue
        event_ts = parse_date(item["anchor_date"])
        scored: list[tuple[float, pd.Series]] = []
        for _, baseline in candidates.iterrows():
            score = abs((parse_date(baseline["anchor_date"]) - event_ts).days)
            for field in match_config.match_fields:
                if field == "board_bucket":
                    score += 10 if str(baseline.get(field, "")) != str(item.get(field, "")) else 0
                else:
                    score += bucket_distance(baseline.get(field), item.get(field))
            scored.append((float(score), baseline))
        scored.sort(key=lambda pair: (pair[0], str(pair[1]["baseline_id"])))
        selected = scored[: match_config.max_controls_per_event]
        for rank, (score, baseline) in enumerate(selected, start=1):
            event_rows.append(
                {
                    "match_id": f"{item['event_id']}_{family}_{rank:02d}",
                    "event_id": item["event_id"],
                    "baseline_id": baseline["baseline_id"],
                    "baseline_family": family,
                    "split": item["split"],
                    "regime_bucket": item["market_regime_bucket"],
                    "match_distance": score,
                    "match_fields": "|".join(match_config.match_fields),
                }
            )
        audit_rows.append(
            {
                "event_id": item["event_id"],
                "split": item["split"],
                "baseline_family": family,
                "matched_baseline_count": len(selected),
                "unmatched_reason": "",
                "cross_split_boundary_unusable_count": cross_split,
            }
        )
    return pd.DataFrame(event_rows), pd.DataFrame(audit_rows)


def summarize_event_vs_baseline(
    events: pd.DataFrame,
    baselines: pd.DataFrame,
    event_labels: pd.DataFrame,
    baseline_labels: pd.DataFrame,
    matches: pd.DataFrame,
    match_audit: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if events.empty:
        return pd.DataFrame()
    event_label_map = event_labels.set_index("event_id", drop=False)
    baseline_label_map = baseline_labels.set_index("event_id", drop=False)
    regimes = ["all"] + sorted(
        value for value in events["market_regime_bucket"].dropna().astype(str).unique() if value
    )
    for event_set, event_subset in [
        ("E_S3_all", events),
        ("E_S3_and_G_S2", events.loc[events["g_s2_passed"]].copy()),
    ]:
        event_ids_all = set(event_subset["event_id"])
        for family in ["baseline_raw", "baseline_false_repair_excluded"]:
            family_matches = matches.loc[
                (matches["baseline_family"] == family)
                & (matches["event_id"].isin(event_ids_all))
            ].copy()
            family_audit = match_audit.loc[
                (match_audit["baseline_family"] == family)
                & (match_audit["event_id"].isin(event_ids_all))
            ].copy()
            for split in ["all", "train", "validation", "robustness"]:
                for regime in regimes:
                    subset_events = event_subset.copy()
                    if split != "all":
                        subset_events = subset_events.loc[subset_events["split"] == split]
                    if regime != "all":
                        subset_events = subset_events.loc[
                            subset_events["market_regime_bucket"].astype(str) == regime
                        ]
                    event_ids = set(subset_events["event_id"])
                    subset_matches = family_matches.loc[family_matches["event_id"].isin(event_ids)]
                    subset_audit = family_audit.loc[family_audit["event_id"].isin(event_ids)]
                    matched_event_ids = set(subset_matches["event_id"])
                    event_label_rows = event_label_map.loc[
                        list(matched_event_ids.intersection(event_label_map.index))
                    ] if matched_event_ids else pd.DataFrame()
                    baseline_ids = subset_matches["baseline_id"].dropna().astype(str).tolist()
                    baseline_label_rows = baseline_label_map.loc[
                        [bid for bid in baseline_ids if bid in baseline_label_map.index]
                    ] if baseline_ids else pd.DataFrame()
                    row = stats_row(
                        event_label_rows,
                        baseline_label_rows,
                        event_count=len(subset_events),
                        baseline_count=len(subset_matches),
                    )
                    row.update(
                        {
                            "event_type": event_set,
                            "baseline_family": family,
                            "baseline_t0_policy": "observed_failure_decision_date",
                            "false_repair_policy": "excluded"
                            if family == "baseline_false_repair_excluded"
                            else "raw_retained",
                            "split": split,
                            "regime_bucket": regime,
                            "baseline_match_coverage": len(matched_event_ids)
                            / len(subset_events)
                            if len(subset_events)
                            else 0.0,
                            "matched_event_count": len(matched_event_ids),
                            "unmatched_event_count": len(subset_events)
                            - len(matched_event_ids),
                            "cross_split_boundary_unusable_count": int(
                                subset_audit["cross_split_boundary_unusable_count"].sum()
                            )
                            if not subset_audit.empty
                            else 0,
                        }
                    )
                    rows.append(row)
    stats = pd.DataFrame(rows)
    if stats.empty:
        return stats
    for metric in ["confirm20_rate_lift", "failure10_rate_diff", "forward_return_20d_diff"]:
        stats[f"train_{metric}"] = np.nan
        stats[f"validation_{metric}"] = np.nan
        stats[f"robustness_{metric}"] = np.nan
    for split in ["train", "validation", "robustness"]:
        stats[f"{split}_lift"] = np.nan
    key_cols = ["event_type", "baseline_family", "regime_bucket"]
    for idx, row in stats.iterrows():
        for split in ["train", "validation", "robustness"]:
            mask = (stats["split"] == split)
            for col in key_cols:
                mask &= stats[col] == row[col]
            matched = stats.loc[mask]
            if not matched.empty:
                first = matched.iloc[0]
                stats.at[idx, f"{split}_confirm20_rate_lift"] = first["confirm20_rate_lift"]
                stats.at[idx, f"{split}_lift"] = first["confirm20_rate_lift"]
                stats.at[idx, f"{split}_failure10_rate_diff"] = first["failure10_rate_diff"]
                stats.at[idx, f"{split}_forward_return_20d_diff"] = first[
                    "forward_return_20d_diff"
                ]
        signs = []
        for split in ["train", "validation", "robustness"]:
            value = stats.at[idx, f"{split}_forward_return_20d_diff"]
            if pd.notna(value):
                signs.append(1 if value > 0 else -1 if value < 0 else 0)
        stats.at[idx, "split_stability"] = (
            "same_positive_sign_all_splits"
            if len(signs) == 3 and all(sign > 0 for sign in signs)
            else "not_stable_or_sample_blocked"
        )
        stats.at[idx, "claim_status"] = "diagnostic"
    return stats


def stats_row(
    event_labels: pd.DataFrame,
    baseline_labels: pd.DataFrame,
    *,
    event_count: int,
    baseline_count: int,
) -> dict[str, Any]:
    event_complete = complete_label_rows(event_labels)
    baseline_complete = complete_label_rows(baseline_labels)
    event_confirm = safe_rate(
        int((event_complete["confirm_20_label"] == 1).sum()) if not event_complete.empty else 0,
        len(event_complete),
    )
    baseline_confirm = safe_rate(
        int((baseline_complete["confirm_20_label"] == 1).sum()) if not baseline_complete.empty else 0,
        len(baseline_complete),
    )
    event_failure = safe_rate(
        int((event_complete["failure_10_label"] == 1).sum()) if not event_complete.empty else 0,
        len(event_complete),
    )
    baseline_failure = safe_rate(
        int((baseline_complete["failure_10_label"] == 1).sum()) if not baseline_complete.empty else 0,
        len(baseline_complete),
    )
    event_return = safe_mean(event_complete.get("forward_return_20d", pd.Series(dtype=float)))
    baseline_return = safe_mean(
        baseline_complete.get("forward_return_20d", pd.Series(dtype=float))
    )
    if "forward_return_20d" in event_complete.columns:
        forward_20 = pd.to_numeric(event_complete["forward_return_20d"], errors="coerce")
        event_pos_payoff = forward_20.loc[forward_20 > 0]
        event_neg_payoff = forward_20.loc[forward_20 < 0].abs()
    else:
        event_pos_payoff = pd.Series(dtype=float)
        event_neg_payoff = pd.Series(dtype=float)
    payoff_ratio = (
        float(event_pos_payoff.mean() / event_neg_payoff.mean())
        if len(event_pos_payoff) and len(event_neg_payoff) and event_neg_payoff.mean() > 0
        else np.nan
    )
    return {
        "event_count": event_count,
        "baseline_count": baseline_count,
        "executable_rate_denominator_count": len(event_labels),
        "executable_rate_numerator_count": int(
            (~event_labels["non_executable_next_open"]).sum()
        )
        if not event_labels.empty
        else 0,
        "event_confirm20_pos_rate": event_confirm,
        "baseline_confirm20_pos_rate": baseline_confirm,
        "confirm20_rate_lift": safe_lift(event_confirm, baseline_confirm),
        "confirm20_rate_diff": event_confirm - baseline_confirm
        if pd.notna(event_confirm) and pd.notna(baseline_confirm)
        else np.nan,
        "event_failure10_rate": event_failure,
        "baseline_failure10_rate": baseline_failure,
        "failure10_rate_diff": event_failure - baseline_failure
        if pd.notna(event_failure) and pd.notna(baseline_failure)
        else np.nan,
        "event_forward_return_20d_mean": event_return,
        "event_forward_return_20d_median": safe_median(
            event_complete.get("forward_return_20d", pd.Series(dtype=float))
        ),
        "baseline_forward_return_20d_mean": baseline_return,
        "baseline_forward_return_20d_median": safe_median(
            baseline_complete.get("forward_return_20d", pd.Series(dtype=float))
        ),
        "forward_return_20d_diff": event_return - baseline_return
        if pd.notna(event_return) and pd.notna(baseline_return)
        else np.nan,
        "event_payoff_ratio": payoff_ratio,
        "censored_count": int(
            event_labels["main_label_complete"].eq(False).sum()
        )
        if not event_labels.empty
        else 0,
        "non_executable_next_open_count": int(
            event_labels["non_executable_next_open"].sum()
        )
        if not event_labels.empty
        else 0,
    }


def complete_label_rows(labels: pd.DataFrame) -> pd.DataFrame:
    if labels.empty:
        return labels
    return labels.loc[
        (~labels["non_executable_next_open"])
        & (labels["confirm_20_complete"])
        & (labels["failure_10_complete"])
    ].copy()


def safe_median(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.median()) if len(clean) else np.nan


def ensure_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = np.nan
    return out[columns]


def write_manifest(
    *,
    manifest_path: Path,
    config: dict[str, Any],
    config_path: Path,
    input_paths: dict[str, Path],
    output_paths: dict[str, Path],
    decision: str,
    gate_summary: dict[str, Any],
    upstream_manifest: dict[str, Any],
) -> Path:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_hashes = {
        name: file_sha256(path)
        for name, path in sorted(output_paths.items())
        if Path(path).is_file()
    }
    input_hashes = {
        name: file_sha256(path)
        for name, path in sorted(input_paths.items())
        if Path(path).is_file()
    }
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "project_root": str(PROJECT_ROOT),
        "source_git_revision": git_revision(PROJECT_ROOT),
        "config_path": str(config_path.resolve()),
        "config_hash": hashlib.sha256(
            json.dumps(config, sort_keys=True, ensure_ascii=True, default=str).encode(
                "utf-8"
            )
        ).hexdigest(),
        "config_file_hash": file_sha256(config_path),
        "input_paths": {name: str(path.resolve()) for name, path in sorted(input_paths.items())},
        "input_hashes": input_hashes,
        "upstream_reverse_lifecycle_decision": upstream_manifest.get("decision"),
        "upstream_reverse_lifecycle_git_revision": upstream_manifest.get(
            "source_git_revision"
        ),
        "upstream_reverse_lifecycle_manifest_hash": input_hashes.get(
            "upstream_reverse_lifecycle_manifest_json"
        ),
        "decision": decision,
        "gate_summary": gate_summary,
        "outputs": {name: str(path.resolve()) for name, path in sorted(output_paths.items())},
        "output_hashes": output_hashes,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_event_and_baseline_rows_for_instrument(
    *,
    instrument: str,
    daily: pd.DataFrame,
    membership: pd.DataFrame,
    event_params: EventParams,
    false_params: FalseRepairParams,
    density_params: DensityParams,
    label_params: LabelParams,
    split_config: SplitConfig,
) -> dict[str, pd.DataFrame]:
    membership_dates = set(membership["usable_trade_date"].astype(str))
    seeds = extract_candidate_seed_lows(
        daily,
        membership_dates=membership_dates,
        params=event_params,
    )
    if not seeds.empty:
        seeds = apply_position_density(
            seeds,
            pos_col="candidate_seed_low_pos",
            date_col="candidate_seed_low_date",
            cluster_col="seed_cluster_id",
            stage="seed",
            window=density_params.seed_density_window,
        )
    reclaims = build_reclaim_rows(
        instrument,
        daily,
        seeds,
        params=event_params,
        density_params=density_params,
    )
    event_candidates: list[dict[str, Any]] = []
    baseline_candidates: list[dict[str, Any]] = []
    if reclaims.empty:
        return {
            "candidate_seed_pool": seeds,
            "reclaim_pool": reclaims,
            "events": pd.DataFrame(),
            "baselines": pd.DataFrame(),
        }
    reclaim_present = reclaims.loc[
        (reclaims["first_ema60_reclaim_missing_reason"] == NOT_MISSING)
        & (reclaims["density_kept"])
    ].copy()
    for reclaim in reclaim_present.to_dict("records"):
        evaluated = evaluate_s3_or_baseline(
            instrument,
            daily,
            reclaim,
            params=event_params,
            false_params=false_params,
            split_config=split_config,
        )
        if evaluated is None:
            continue
        if evaluated["event_kind"] == "E_S3":
            row = make_event_instance_row(
                daily=daily,
                membership=membership,
                evaluated=evaluated,
                event_params=event_params,
                false_params=false_params,
                label_params=label_params,
            )
            event_candidates.append(row)
        elif evaluated["event_kind"] == "baseline_candidate":
            row = make_baseline_candidate_row(
                daily=daily,
                membership=membership,
                evaluated=evaluated,
                false_params=false_params,
                label_params=label_params,
                split_config=split_config,
            )
            if row is not None:
                baseline_candidates.append(row)
    events = pd.DataFrame(event_candidates)
    baselines = pd.DataFrame(baseline_candidates)
    if not events.empty:
        events = apply_position_density(
            events,
            pos_col="event_t0_pos",
            date_col="event_t0_date",
            cluster_col="event_cluster_id",
            stage="event",
            window=density_params.event_density_window,
        )
    if not baselines.empty:
        baselines = apply_position_density(
            baselines,
            pos_col="baseline_t0_pos",
            date_col="baseline_t0_date",
            cluster_col="event_cluster_id",
            stage="baseline",
            window=density_params.event_density_window,
        )
    return {
        "candidate_seed_pool": seeds,
        "reclaim_pool": reclaims,
        "events": events,
        "baselines": baselines,
    }


def make_event_instance_row(
    *,
    daily: pd.DataFrame,
    membership: pd.DataFrame,
    evaluated: dict[str, Any],
    event_params: EventParams,
    false_params: FalseRepairParams,
    label_params: LabelParams,
) -> dict[str, Any]:
    t0_pos = int(evaluated["event_t0_pos"])
    reclaim_pos = int(evaluated["anchor_pos"])
    instrument = evaluated["instrument"]
    event_id = f"{instrument}_{evaluated['event_t0_date'].replace('-', '')}_E_S3"
    member = membership_asof(membership, evaluated["event_t0_date"])
    board_bucket = str(member.get("board_bucket", ""))
    is_st = bool(member.get("is_st", False))
    s6_reclaim = c_s6_confirmation(
        daily,
        reclaim_pos=reclaim_pos,
        base_pos=reclaim_pos,
        params=event_params,
    )
    s6_axis_low = c_s6_confirmation(
        daily,
        reclaim_pos=reclaim_pos,
        base_pos=int(evaluated["candidate_seed_low_pos"]),
        params=event_params,
    )
    trade = execution_status(
        daily,
        t0_pos=t0_pos,
        board_bucket=board_bucket,
        is_st=is_st,
    )
    near = near_winner_profile(daily, trade=trade, params=label_params)
    row = {
        "instrument": instrument,
        "event_id": event_id,
        "event_type": "E_S3",
        "event_t0_date": evaluated["event_t0_date"],
        "event_t0_pos": t0_pos,
        "trade_open_date": trade["trade_open_date"],
        "trade_open_pos": trade["trade_open_pos"],
        "trade_open_price": trade["trade_open_price"],
        "non_executable_next_open": trade["non_executable_next_open"],
        "non_executable_reason": trade["non_executable_reason"],
        "limit_threshold_status": trade["limit_threshold_status"],
        "anchor_family": "first_ema60_reclaim",
        "anchor_date": evaluated["anchor_date"],
        "anchor_pos": reclaim_pos,
        "candidate_seed_low_date": evaluated["candidate_seed_low_date"],
        "candidate_seed_low_pos": evaluated["candidate_seed_low_pos"],
        "rank_jump_date": evaluated["rank_jump_date"],
        "rank_jump_pos": evaluated["rank_jump_pos"],
        "rank_persistence_confirmed": True,
        "rank_persistence_coverage": evaluated["rank_persistence_coverage"],
        "g_s2_passed": g_s2_passed(
            daily,
            reclaim_pos=reclaim_pos,
            t0_pos=t0_pos,
            params=event_params,
        ),
        "c_s6_confirmed": bool(s6_reclaim.get("confirmed", False)),
        "c_s6_confirm_date": s6_reclaim.get("confirm_date", ""),
        "c_s6_plus20_state_date": s6_reclaim.get("plus20_state_date", ""),
        "s6_axis_low_reference_confirmed": bool(s6_axis_low.get("confirmed", False)),
        "s6_axis_low_reference_confirm_date": s6_axis_low.get("confirm_date", ""),
        "split": evaluated["split"],
        "seed_cluster_id": evaluated.get("seed_cluster_id", ""),
        "reclaim_cluster_id": evaluated.get("reclaim_cluster_id", ""),
        "density_stage": "event",
        "density_kept": True,
        "false_repair_observed_asof_t0": evaluated["false_repair_observed_asof_t0"],
        "false_repair_drawdown_trigger_date": evaluated["false_repair_drawdown_trigger_date"],
        "false_repair_10d_diagnostic": evaluated["false_repair_10d_diagnostic"],
        "false_repair_20d_diagnostic": evaluated["false_repair_20d_diagnostic"],
        "insufficient_runup_20d_diagnostic": evaluated[
            "insufficient_runup_20d_diagnostic"
        ],
        "future_false_repair_any_diagnostic": evaluated[
            "future_false_repair_any_diagnostic"
        ],
        "event_invalidated_false_repair": evaluated["event_invalidated_false_repair"],
        "board_bucket": board_bucket,
        "is_st": is_st,
        "total_market_cap_cny": member.get("total_market_cap_cny", np.nan),
        "liquidity_money_20d": daily.at[t0_pos, "money_mean_20d"],
        "prior_return_20d": daily.at[t0_pos, "return_20d"],
        "prior_return_60d": daily.at[t0_pos, "return_60d"],
        "prior_drawdown": daily.at[t0_pos, "drawdown_from_60d_high"],
        "volatility_20d": daily.at[t0_pos, "atr_20_pct"],
        "near_winner_flag": near["near_winner_flag"],
        "near_winner_forward_mfe_120d": near["near_winner_forward_mfe_120d"],
        "near_winner_status": near["near_winner_status"],
    }
    row.update(snapshot_fields(daily, t0_pos))
    return row


def make_baseline_candidate_row(
    *,
    daily: pd.DataFrame,
    membership: pd.DataFrame,
    evaluated: dict[str, Any],
    false_params: FalseRepairParams,
    label_params: LabelParams,
    split_config: SplitConfig,
) -> dict[str, Any] | None:
    if int(evaluated.get("baseline_t0_pos", -1)) < 0:
        return None
    t0_pos = int(evaluated["baseline_t0_pos"])
    reclaim_pos = int(evaluated["anchor_pos"])
    instrument = evaluated["instrument"]
    baseline_id = (
        f"{instrument}_{evaluated['baseline_t0_date'].replace('-', '')}_"
        f"{evaluated['baseline_failure_type']}"
    )
    split = split_for_t0(evaluated["baseline_t0_date"], split_config)
    if split == "outside_split":
        return None
    member = membership_asof(membership, evaluated["baseline_t0_date"])
    board_bucket = str(member.get("board_bucket", ""))
    is_st = bool(member.get("is_st", False))
    repair = false_repair_metrics_asof(
        daily,
        reclaim_pos=reclaim_pos,
        t0_pos=t0_pos,
        params=false_params,
    )
    trade = execution_status(
        daily,
        t0_pos=t0_pos,
        board_bucket=board_bucket,
        is_st=is_st,
    )
    near = near_winner_profile(daily, trade=trade, params=label_params)
    row = {
        "instrument": instrument,
        "baseline_id": baseline_id,
        "baseline_t0_policy": "observed_failure_decision_date",
        "baseline_t0_date": evaluated["baseline_t0_date"],
        "baseline_t0_pos": t0_pos,
        "baseline_failure_type": evaluated["baseline_failure_type"],
        "anchor_family": "first_ema60_reclaim",
        "anchor_date": evaluated["anchor_date"],
        "anchor_pos": reclaim_pos,
        "candidate_seed_low_date": evaluated["candidate_seed_low_date"],
        "candidate_seed_low_pos": evaluated["candidate_seed_low_pos"],
        "rank_jump_date": evaluated.get("rank_jump_date", ""),
        "rank_jump_pos": evaluated.get("rank_jump_pos", -1),
        "rank_persistence_confirmed": False,
        "rank_persistence_coverage": evaluated.get("rank_persistence_coverage", np.nan),
        "split": split,
        "seed_cluster_id": evaluated.get("seed_cluster_id", ""),
        "reclaim_cluster_id": evaluated.get("reclaim_cluster_id", ""),
        "density_stage": "baseline",
        "density_kept": True,
        "false_repair_observed_asof_baseline_t0": repair[
            "false_repair_observed_asof_t0"
        ],
        "false_repair_drawdown_trigger_date": repair["false_repair_drawdown_trigger_date"],
        "false_repair_10d_diagnostic": repair["false_repair_10d_diagnostic"],
        "false_repair_20d_diagnostic": repair["false_repair_20d_diagnostic"],
        "insufficient_runup_20d_diagnostic": repair[
            "insufficient_runup_20d_diagnostic"
        ],
        "future_false_repair_any_diagnostic": repair[
            "future_false_repair_any_diagnostic"
        ],
        "trade_open_date": trade["trade_open_date"],
        "trade_open_pos": trade["trade_open_pos"],
        "trade_open_price": trade["trade_open_price"],
        "non_executable_next_open": trade["non_executable_next_open"],
        "non_executable_reason": trade["non_executable_reason"],
        "limit_threshold_status": trade["limit_threshold_status"],
        "board_bucket": board_bucket,
        "is_st": is_st,
        "total_market_cap_cny": member.get("total_market_cap_cny", np.nan),
        "liquidity_money_20d": daily.at[t0_pos, "money_mean_20d"],
        "prior_return_20d": daily.at[t0_pos, "return_20d"],
        "prior_return_60d": daily.at[t0_pos, "return_60d"],
        "prior_drawdown": daily.at[t0_pos, "drawdown_from_60d_high"],
        "volatility_20d": daily.at[t0_pos, "atr_20_pct"],
        "near_winner_flag": near["near_winner_flag"],
        "near_winner_forward_mfe_120d": near["near_winner_forward_mfe_120d"],
        "near_winner_status": near["near_winner_status"],
    }
    row.update(snapshot_fields(daily, t0_pos))
    return row


def duplicate_baseline_families(baselines: pd.DataFrame) -> pd.DataFrame:
    if baselines.empty:
        return baselines
    raw = baselines.copy()
    raw["baseline_family"] = "baseline_raw"
    excluded = baselines.loc[
        ~baselines["false_repair_observed_asof_baseline_t0"].astype(bool)
    ].copy()
    excluded["baseline_family"] = "baseline_false_repair_excluded"
    out = pd.concat([raw, excluded], ignore_index=True)
    out["source_baseline_id"] = out["baseline_id"]
    out["baseline_id"] = out["source_baseline_id"] + "__" + out["baseline_family"]
    out["event_id"] = out["baseline_id"]
    out["event_type"] = out["baseline_family"]
    return out


def build_label_outcomes(
    events: pd.DataFrame,
    baselines: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    *,
    label_params: LabelParams,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    for row in events.itertuples(index=False):
        item = row._asdict()
        daily = daily_by_instrument[item["instrument"]]
        trade = {
            "trade_open_pos": item["trade_open_pos"],
            "trade_open_date": item["trade_open_date"],
            "trade_open_price": item["trade_open_price"],
            "non_executable_next_open": item["non_executable_next_open"],
            "non_executable_reason": item["non_executable_reason"],
            "limit_threshold_status": item.get("limit_threshold_status", ""),
        }
        event_rows.append(
            label_row(
                entity_id=item["event_id"],
                event_type="E_S3",
                split=item["split"],
                regime_bucket=item["market_regime_bucket"],
                daily=daily,
                trade=trade,
                label_params=label_params,
            )
        )
    for row in baselines.itertuples(index=False):
        item = row._asdict()
        daily = daily_by_instrument[item["instrument"]]
        trade = {
            "trade_open_pos": item["trade_open_pos"],
            "trade_open_date": item["trade_open_date"],
            "trade_open_price": item["trade_open_price"],
            "non_executable_next_open": item["non_executable_next_open"],
            "non_executable_reason": item["non_executable_reason"],
            "limit_threshold_status": item.get("limit_threshold_status", ""),
        }
        baseline_rows.append(
            label_row(
                entity_id=item["baseline_id"],
                event_type=item["baseline_family"],
                split=item["split"],
                regime_bucket=item["market_regime_bucket"],
                daily=daily,
                trade=trade,
                label_params=label_params,
            )
        )
    return pd.DataFrame(event_rows), pd.DataFrame(baseline_rows)


def build_event_aligned_panel(
    events: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    *,
    start: int = -20,
    end: int = 60,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for event in events.itertuples(index=False):
        item = event._asdict()
        daily = daily_by_instrument[item["instrument"]]
        t0_pos = int(item["event_t0_pos"])
        for relative_day in range(start, end + 1):
            pos = t0_pos + relative_day
            in_coverage = 0 <= pos < len(daily)
            row = {
                "event_id": item["event_id"],
                "instrument": item["instrument"],
                "event_t0_date": item["event_t0_date"],
                "date": str(daily.at[pos, "date"]) if in_coverage else "",
                "relative_day": relative_day,
                "split": item["split"],
                "market_regime_bucket": item["market_regime_bucket"],
            }
            for column in SNAPSHOT_COLUMNS:
                row[column] = daily.at[pos, column] if in_coverage and column in daily.columns else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def build_density_audit(
    seeds: pd.DataFrame,
    reclaims: pd.DataFrame,
    events: pd.DataFrame,
    baselines: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    specs = [
        ("seed", seeds, "candidate_seed_low_date", "density_kept"),
        ("reclaim", reclaims, "first_ema60_reclaim_date", "density_kept"),
        ("event", events, "event_t0_date", "density_kept"),
        ("baseline", baselines, "baseline_t0_date", "density_kept"),
    ]
    for stage, frame, date_col, kept_col in specs:
        if frame.empty or date_col not in frame.columns:
            rows.append(
                {
                    "density_stage": stage,
                    "split": "all",
                    "year": "all",
                    "candidate_count": 0,
                    "density_kept_count": 0,
                    "density_folded_count": 0,
                }
            )
            continue
        audit = frame.copy()
        audit["_year"] = pd.to_datetime(audit[date_col], errors="coerce").dt.year
        if "split" not in audit.columns:
            audit["split"] = "all"
        for split in ["all"] + sorted(audit["split"].dropna().astype(str).unique()):
            subset = audit if split == "all" else audit.loc[audit["split"].astype(str) == split]
            years = ["all"] + sorted(
                str(int(year)) for year in subset["_year"].dropna().unique()
            )
            for year in years:
                part = subset if year == "all" else subset.loc[subset["_year"].astype("Int64").astype(str) == year]
                rows.append(
                    {
                        "density_stage": stage,
                        "split": split,
                        "year": year,
                        "candidate_count": len(part),
                        "density_kept_count": int(part[kept_col].sum())
                        if kept_col in part
                        else len(part),
                        "density_folded_count": len(part)
                        - (
                            int(part[kept_col].sum())
                            if kept_col in part
                            else len(part)
                        ),
                    }
                )
    return pd.DataFrame(rows)


def build_false_repair_exclusion_audit(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(
            [
                {
                    "split": "all",
                    "year": "all",
                    "candidate_count_before_false_repair": 0,
                    "event_invalidated_false_repair_count": 0,
                    "candidate_count_after_false_repair": 0,
                }
            ]
        )
    frame = events.copy()
    frame["_year"] = pd.to_datetime(frame["event_t0_date"], errors="coerce").dt.year
    rows: list[dict[str, Any]] = []
    for split in ["all", "train", "validation", "robustness"]:
        subset = frame if split == "all" else frame.loc[frame["split"] == split]
        for year in ["all"] + sorted(str(int(v)) for v in subset["_year"].dropna().unique()):
            part = subset if year == "all" else subset.loc[subset["_year"].astype("Int64").astype(str) == year]
            invalid = int(part["event_invalidated_false_repair"].sum()) if not part.empty else 0
            rows.append(
                {
                    "split": split,
                    "year": year,
                    "candidate_count_before_false_repair": len(part),
                    "event_invalidated_false_repair_count": invalid,
                    "candidate_count_after_false_repair": len(part) - invalid,
                    "false_repair_10d_diagnostic_count": int(
                        part["false_repair_10d_diagnostic"].sum()
                    )
                    if not part.empty
                    else 0,
                    "false_repair_20d_diagnostic_count": int(
                        part["false_repair_20d_diagnostic"].sum()
                    )
                    if not part.empty
                    else 0,
                    "insufficient_runup_20d_diagnostic_count": int(
                        part["insufficient_runup_20d_diagnostic"].sum()
                    )
                    if not part.empty
                    else 0,
                }
            )
    return pd.DataFrame(rows)


def build_executability_audit(events: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    merged = events.merge(
        labels[["event_id", "main_label_complete"]],
        on="event_id",
        how="left",
    )
    rows: list[dict[str, Any]] = []
    merged["_year"] = pd.to_datetime(merged["event_t0_date"], errors="coerce").dt.year
    for split in ["all", "train", "validation", "robustness"]:
        subset = merged if split == "all" else merged.loc[merged["split"] == split]
        years = ["all"] + sorted(
            str(int(year)) for year in subset["_year"].dropna().unique()
        )
        for year in years:
            year_subset = (
                subset
                if year == "all"
                else subset.loc[subset["_year"].astype("Int64").astype(str) == year]
            )
            boards = ["all"] + sorted(
                year_subset["board_bucket"].dropna().astype(str).unique()
            )
            for board in boards:
                part = (
                    year_subset
                    if board == "all"
                    else year_subset.loc[
                        year_subset["board_bucket"].astype(str) == board
                    ]
                )
                denominator = len(part)
                non_exec = (
                    int(part["non_executable_next_open"].sum()) if denominator else 0
                )
                executable = denominator - non_exec
                limit_unavailable = int(
                    part.get(
                        "limit_threshold_status",
                        pd.Series(dtype="object"),
                    ).eq("limit_rule_unavailable").sum()
                )
                rows.append(
                    {
                        "split": split,
                        "year": year,
                        "board_proxy": board,
                        "executable_rate_denominator_count": denominator,
                        "executable_rate_numerator_count": executable,
                        "non_executable_next_open_count": non_exec,
                        "limit_rule_unavailable_count": limit_unavailable,
                        "executable_rate": executable / denominator
                        if denominator
                        else np.nan,
                        "main_label_complete_rate": float(
                            part.loc[
                                ~part["non_executable_next_open"],
                                "main_label_complete",
                            ].mean()
                        )
                        if executable
                        else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def build_threshold_freeze_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for section in ["event_contract", "false_repair", "density", "labels", "gates"]:
        values = config.get(section, {})
        for key, value in values.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    rows.append(
                        {
                            "section": section,
                            "parameter": f"{key}.{subkey}",
                            "value": subvalue,
                            "freeze_basis": "fixed_contract_constant",
                            "oos_used_for_selection": False,
                        }
                    )
            else:
                rows.append(
                    {
                        "section": section,
                        "parameter": key,
                        "value": value,
                        "freeze_basis": "fixed_contract_constant",
                        "oos_used_for_selection": False,
                    }
                )
    return pd.DataFrame(rows)


def build_contract_definition(config: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_type": "E_S3",
                "anchor_family": "first_ema60_reclaim",
                "shared_axis": "EMA60",
                "required_states": "ema60_reclaim -> stock_vs_market_20d rank jump -> 20d persistence",
                "forbidden_states": "false_repair_observed_asof_t0",
                "order_constraints": "rank jump after reclaim; persistence after rank jump; t0 at persistence confirmation close",
                "state_thresholds": json.dumps(
                    config["event_contract"], sort_keys=True, ensure_ascii=False
                ),
                "lookback_windows": "ema60=60; rank=20; seed_low=60; prior_lookback=250",
                "seed_density_window": config["density"]["seed_density_window"],
                "reclaim_density_window": config["density"]["reclaim_density_window"],
                "event_density_window": config["density"]["event_density_window"],
                "false_repair_rules": json.dumps(
                    config["false_repair"], sort_keys=True, ensure_ascii=False
                ),
                "t0_definition": "rank_persistence_confirmed_close",
                "trade_time_definition": "next_executable_open_after_t0",
                "label_contract": json.dumps(
                    config["labels"], sort_keys=True, ensure_ascii=False
                ),
                "threshold_freeze_basis": "train_only_fixed_v0",
                "headline_pre_registered_test": "E_S3_all_vs_baseline_false_repair_excluded_confirm_20_unconditional",
            }
        ]
    )


def build_s6_basis_transform_audit(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in ["all", "train", "validation", "robustness"]:
        subset = events if split == "all" else events.loc[events["split"] == split]
        if subset.empty:
            rows.append(
                {
                    "split": split,
                    "event_count": 0,
                    "s6_axis_low_reference_pass_rate": np.nan,
                    "s6_reclaim_close_contract_pass_rate": np.nan,
                    "s6_basis_pass_rate_delta": np.nan,
                    "s6_basis_confirm_delay_delta": np.nan,
                }
            )
            continue
        axis_rate = float(subset["s6_axis_low_reference_confirmed"].mean())
        reclaim_rate = float(subset["c_s6_confirmed"].mean())
        axis_dates = pd.to_datetime(
            subset["s6_axis_low_reference_confirm_date"].replace("", pd.NA),
            errors="coerce",
        )
        reclaim_dates = pd.to_datetime(
            subset["c_s6_confirm_date"].replace("", pd.NA), errors="coerce"
        )
        delay_delta = (reclaim_dates - axis_dates).dt.days.mean()
        rows.append(
            {
                "split": split,
                "event_count": len(subset),
                "s6_axis_low_reference_pass_rate": axis_rate,
                "s6_reclaim_close_contract_pass_rate": reclaim_rate,
                "s6_basis_pass_rate_delta": reclaim_rate - axis_rate,
                "s6_basis_confirm_delay_delta": delay_delta,
            }
        )
    return pd.DataFrame(rows)


def build_baseline_timing_audit(
    baselines: pd.DataFrame,
    baseline_labels: pd.DataFrame,
    *,
    daily_by_instrument: dict[str, pd.DataFrame] | None = None,
    event_params: EventParams | None = None,
    false_params: FalseRepairParams | None = None,
    label_params: LabelParams | None = None,
    split_config: SplitConfig | None = None,
) -> pd.DataFrame:
    if baselines.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []

    def append_policy_rows(
        *,
        policy_baselines: pd.DataFrame,
        policy_labels: pd.DataFrame,
        policy: str,
        used_for_main_claim: bool,
    ) -> None:
        labels = policy_labels.set_index("event_id", drop=False)
        for split in ["all", "train", "validation", "robustness"]:
            for family in ["baseline_raw", "baseline_false_repair_excluded"]:
                subset = policy_baselines.loc[
                    policy_baselines["baseline_family"] == family
                ]
                if split != "all":
                    subset = subset.loc[subset["split"] == split]
                label_subset = (
                    labels.loc[
                        [
                            bid
                            for bid in subset["baseline_id"].astype(str)
                            if bid in labels.index
                        ]
                    ]
                    if not subset.empty
                    else pd.DataFrame()
                )
                complete = complete_label_rows(label_subset)
                rows.append(
                    {
                        "split": split,
                        "regime_bucket": "all",
                        "baseline_family": family,
                        "baseline_t0_policy": policy,
                        "baseline_count": len(subset),
                        "median_reclaim_to_baseline_t0_days": pd.to_datetime(
                            subset["baseline_t0_date"], errors="coerce"
                        )
                        .sub(pd.to_datetime(subset["anchor_date"], errors="coerce"))
                        .dt.days.median()
                        if not subset.empty
                        else np.nan,
                        "median_reclaim_to_event_t0_days": np.nan,
                        "confirm20_rate": float(
                            (complete["confirm_20_label"] == 1).mean()
                        )
                        if not complete.empty
                        else np.nan,
                        "failure10_rate": float(
                            (complete["failure_10_label"] == 1).mean()
                        )
                        if not complete.empty
                        else np.nan,
                        "forward_return_20d_mean": safe_mean(
                            complete.get(
                                "forward_return_20d",
                                pd.Series(dtype=float),
                            )
                        ),
                        "policy_used_for_main_claim": used_for_main_claim,
                    }
                )

    append_policy_rows(
        policy_baselines=baselines,
        policy_labels=baseline_labels,
        policy="observed_failure_decision_date",
        used_for_main_claim=True,
    )

    if not all(
        value is not None
        for value in [
            daily_by_instrument,
            event_params,
            false_params,
            label_params,
            split_config,
        ]
    ):
        return pd.DataFrame(rows)

    deterministic_rows: list[dict[str, Any]] = []
    deterministic_labels: list[dict[str, Any]] = []
    assert daily_by_instrument is not None
    assert event_params is not None
    assert false_params is not None
    assert label_params is not None
    assert split_config is not None
    for row in baselines.itertuples(index=False):
        item = row._asdict()
        daily = daily_by_instrument.get(str(item["instrument"]))
        if daily is None:
            continue
        t0_pos = int(item["anchor_pos"]) + event_params.rank_jump_window + event_params.persistence_window
        if t0_pos >= len(daily):
            continue
        t0_date = str(daily.at[t0_pos, "date"])
        split = split_for_t0(t0_date, split_config)
        if split == "outside_split":
            continue
        repair = false_repair_metrics_asof(
            daily,
            reclaim_pos=int(item["anchor_pos"]),
            t0_pos=t0_pos,
            params=false_params,
        )
        if (
            item["baseline_family"] == "baseline_false_repair_excluded"
            and repair["false_repair_observed_asof_t0"]
        ):
            continue
        trade = execution_status(
            daily,
            t0_pos=t0_pos,
            board_bucket=str(item.get("board_bucket", "")),
            is_st=bool(item.get("is_st", False)),
        )
        baseline_id = f"{item['baseline_id']}__deterministic_max_horizon"
        deterministic_rows.append(
            {
                **item,
                "baseline_id": baseline_id,
                "baseline_t0_policy": "deterministic_max_horizon",
                "baseline_t0_date": t0_date,
                "baseline_t0_pos": t0_pos,
                "split": split,
                "false_repair_observed_asof_baseline_t0": repair[
                    "false_repair_observed_asof_t0"
                ],
                "trade_open_date": trade["trade_open_date"],
                "trade_open_pos": trade["trade_open_pos"],
                "trade_open_price": trade["trade_open_price"],
                "non_executable_next_open": trade["non_executable_next_open"],
                "non_executable_reason": trade["non_executable_reason"],
                "limit_threshold_status": trade["limit_threshold_status"],
            }
        )
        deterministic_labels.append(
            label_row(
                entity_id=baseline_id,
                event_type=item["baseline_family"],
                split=split,
                regime_bucket=item["market_regime_bucket"],
                daily=daily,
                trade=trade,
                label_params=label_params,
            )
        )

    deterministic_baselines = pd.DataFrame(deterministic_rows)
    deterministic_label_rows = pd.DataFrame(deterministic_labels)
    if not deterministic_baselines.empty:
        append_policy_rows(
            policy_baselines=deterministic_baselines,
            policy_labels=deterministic_label_rows,
            policy="deterministic_max_horizon",
            used_for_main_claim=False,
        )
    return pd.DataFrame(rows)


def build_baseline_false_repair_attribution_audit(
    stats: pd.DataFrame,
    baselines: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if stats.empty:
        return pd.DataFrame()
    for split in ["all", "train", "validation", "robustness"]:
        for family in ["baseline_raw", "baseline_false_repair_excluded"]:
            row = stats.loc[
                (stats["event_type"] == "E_S3_all")
                & (stats["baseline_family"] == family)
                & (stats["split"] == split)
                & (stats["regime_bucket"] == "all")
            ]
            item = row.iloc[0].to_dict() if not row.empty else {}
            baseline_subset = baselines.loc[baselines["baseline_family"] == family]
            if split != "all":
                baseline_subset = baseline_subset.loc[baseline_subset["split"] == split]
            rows.append(
                {
                    "split": split,
                    "regime_bucket": "all",
                    "baseline_family": family,
                    "event_count": item.get("event_count", 0),
                    "baseline_count": item.get("baseline_count", 0),
                    "baseline_false_repair_asof_count": int(
                        baseline_subset.get(
                            "false_repair_observed_asof_baseline_t0",
                            pd.Series(dtype=bool),
                        ).sum()
                    )
                    if not baseline_subset.empty
                    else 0,
                    "event_vs_baseline_confirm20_lift": item.get("confirm20_rate_lift", np.nan),
                    "event_vs_baseline_failure10_diff": item.get("failure10_rate_diff", np.nan),
                    "event_vs_baseline_forward_return_20d_diff": item.get(
                        "forward_return_20d_diff", np.nan
                    ),
                    "rank_persistence_independent_edge_status": "primary_headline_family"
                    if family == "baseline_false_repair_excluded"
                    else "raw_false_repair_retained_diagnostic",
                }
            )
    return pd.DataFrame(rows)


def build_oos_readouts(stats: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if stats.empty:
        return pd.DataFrame(), pd.DataFrame()
    unconditional = stats.loc[
        (stats["event_type"] == "E_S3_all")
        & (stats["baseline_family"] == "baseline_false_repair_excluded")
        & (stats["split"].isin(["validation", "robustness"]))
        & (stats["regime_bucket"] == "all")
    ].copy()
    unconditional["readout_type"] = "unconditional_oos_readout"
    regime = stats.loc[
        (stats["event_type"] == "E_S3_all")
        & (stats["baseline_family"] == "baseline_false_repair_excluded")
        & (stats["split"].isin(["validation", "robustness"]))
        & (stats["regime_bucket"] != "all")
    ].copy()
    regime["readout_type"] = "regime_conditioned_oos_readout"
    return unconditional, regime


def evaluate_decision(
    *,
    events: pd.DataFrame,
    event_labels: pd.DataFrame,
    stats: pd.DataFrame,
    gates: dict[str, Any],
    executability_audit: pd.DataFrame,
) -> dict[str, Any]:
    post_false = events.loc[
        (events["density_kept"]) & (~events["event_invalidated_false_repair"])
    ].copy()
    labels = event_labels.set_index("event_id", drop=False)
    labeled = labels.loc[
        [eid for eid in post_false["event_id"].astype(str) if eid in labels.index]
    ] if not post_false.empty else pd.DataFrame()
    complete = complete_label_rows(labeled)
    counts = {
        "total_event_count": len(complete),
        "validation_event_count": int((complete["split"] == "validation").sum())
        if not complete.empty
        else 0,
        "robustness_event_count": int((complete["split"] == "robustness").sum())
        if not complete.empty
        else 0,
    }
    exec_all = executability_audit.loc[
        (executability_audit["split"] == "all")
        & (executability_audit["board_proxy"] == "all")
    ]
    executable_rate = (
        float(exec_all.iloc[0]["executable_rate"]) if not exec_all.empty else np.nan
    )
    label_complete_rate = (
        float(exec_all.iloc[0]["main_label_complete_rate"])
        if not exec_all.empty
        else np.nan
    )
    headline = headline_stats(stats, family="baseline_false_repair_excluded", split="all")
    headline_validation = headline_stats(
        stats, family="baseline_false_repair_excluded", split="validation"
    )
    headline_robustness = headline_stats(
        stats, family="baseline_false_repair_excluded", split="robustness"
    )
    raw_headline = headline_stats(stats, family="baseline_raw", split="all")
    coverage_all = headline.get("baseline_match_coverage", 0.0)
    coverage_val = headline_validation.get("baseline_match_coverage", 0.0)
    coverage_rob = headline_robustness.get("baseline_match_coverage", 0.0)
    blocked: list[str] = []
    if counts["total_event_count"] < int(gates["min_total_event_count"]):
        blocked.append("min_total_event_count")
    if counts["validation_event_count"] < int(gates["min_validation_event_count"]):
        blocked.append("min_validation_event_count")
    if counts["robustness_event_count"] < int(gates["min_robustness_event_count"]):
        blocked.append("min_robustness_event_count")
    if pd.isna(executable_rate) or executable_rate < float(gates["min_executable_rate"]):
        blocked.append("min_executable_rate")
    if pd.isna(label_complete_rate) or label_complete_rate < float(
        gates["min_event_label_complete_rate"]
    ):
        blocked.append("min_event_label_complete_rate")
    if coverage_all < float(gates["min_baseline_match_coverage"]):
        blocked.append("min_baseline_match_coverage")
    if coverage_val < float(gates["min_validation_baseline_match_coverage"]):
        blocked.append("min_validation_baseline_match_coverage")
    if coverage_rob < float(gates["min_robustness_baseline_match_coverage"]):
        blocked.append("min_robustness_baseline_match_coverage")

    if any(reason.startswith("min_validation_event_count") for reason in blocked):
        decision = "event_contract_validation_sample_blocked"
    elif any(reason in {"min_total_event_count", "min_robustness_event_count"} for reason in blocked):
        decision = "event_contract_sample_blocked"
    elif any(reason in {"min_executable_rate", "min_event_label_complete_rate"} for reason in blocked):
        decision = "event_contract_executability_blocked"
    elif any("baseline_match_coverage" in reason for reason in blocked):
        decision = "event_contract_sample_blocked"
    else:
        headline_pass = edge_passes(headline, gates)
        validation_positive = headline_validation.get("forward_return_20d_diff", np.nan)
        robustness_positive = headline_robustness.get("forward_return_20d_diff", np.nan)
        if headline_pass and validation_positive > 0 and robustness_positive > 0:
            decision = "event_contract_supported_universal_edge"
        elif edge_passes(raw_headline, gates) and not headline_pass:
            decision = (
                "event_contract_false_repair_filter_dominant_no_rank_persistence_separation"
            )
        elif validation_positive <= 0:
            decision = "event_contract_negative_beta_not_supported"
        else:
            decision = "event_contract_no_baseline_separation"
    return {
        **counts,
        "executable_rate": executable_rate,
        "event_label_complete_rate": label_complete_rate,
        "baseline_match_coverage": coverage_all,
        "validation_baseline_match_coverage": coverage_val,
        "robustness_baseline_match_coverage": coverage_rob,
        "headline_confirm20_rate_lift": headline.get("confirm20_rate_lift", np.nan),
        "headline_confirm20_rate_diff": headline.get("confirm20_rate_diff", np.nan),
        "headline_failure10_rate_diff": headline.get("failure10_rate_diff", np.nan),
        "headline_forward_return_20d_diff": headline.get("forward_return_20d_diff", np.nan),
        "raw_headline_confirm20_rate_lift": raw_headline.get("confirm20_rate_lift", np.nan),
        "blocked_reasons": blocked,
        "decision": decision,
    }


def headline_stats(stats: pd.DataFrame, *, family: str, split: str) -> dict[str, Any]:
    if stats.empty:
        return {}
    row = stats.loc[
        (stats["event_type"] == "E_S3_all")
        & (stats["baseline_family"] == family)
        & (stats["split"] == split)
        & (stats["regime_bucket"] == "all")
    ]
    return row.iloc[0].to_dict() if not row.empty else {}


def edge_passes(row: dict[str, Any], gates: dict[str, Any]) -> bool:
    if not row:
        return False
    lift = row.get("confirm20_rate_lift", np.nan)
    diff = row.get("confirm20_rate_diff", np.nan)
    failure = row.get("failure10_rate_diff", np.nan)
    forward = row.get("forward_return_20d_diff", np.nan)
    confirm_ok = (
        (pd.notna(lift) and lift >= float(gates["confirm20_rate_lift"]))
        or (pd.notna(diff) and diff >= float(gates["confirm20_abs_diff"]))
    )
    return bool(
        confirm_ok
        and pd.notna(failure)
        and failure <= 0
        and pd.notna(forward)
        and forward > 0
    )


def build_near_winner_forward_stats(
    events: pd.DataFrame, event_labels: pd.DataFrame
) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    label_map = event_labels.set_index("event_id", drop=False)
    rows: list[dict[str, Any]] = []
    for split in ["all", "train", "validation", "robustness"]:
        subset = events if split == "all" else events.loc[events["split"] == split]
        near = subset.loc[subset["near_winner_flag"]]
        near_ids = [eid for eid in near["event_id"].astype(str) if eid in label_map.index]
        near_labels = label_map.loc[near_ids] if near_ids else pd.DataFrame()
        complete = complete_label_rows(near_labels)
        rows.append(
            {
                "comparison": "E_S3_profile_only_near_winner",
                "split": split,
                "event_count": len(subset),
                "near_winner_count": len(near),
                "future_label_used_for_profile_only": True,
                "near_winner_confirm20_pos_rate": float(
                    (complete["confirm_20_label"] == 1).mean()
                )
                if not complete.empty
                else np.nan,
                "near_winner_forward_return_20d_mean": safe_mean(
                    complete.get("forward_return_20d", pd.Series(dtype=float))
                ),
                "claim_status": "diagnostic_profile_only"
                if len(near)
                else "sample_blocked",
            }
        )
    return pd.DataFrame(rows)


def build_data_source_coverage_audit(
    *,
    input_paths: dict[str, Path],
    source_coverage_audit: pd.DataFrame,
    upstream_manifest: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, path in sorted(input_paths.items()):
        if name.endswith("_dir"):
            exists = path.is_dir()
            sha = ""
        else:
            exists = path.is_file()
            sha = file_sha256(path) if exists else ""
        rows.append(
            {
                "source_name": name,
                "path": str(path),
                "exists": exists,
                "sha256": sha,
                "support_state": "available" if exists else "missing",
                "units": "",
            }
        )
    if not source_coverage_audit.empty:
        for row in source_coverage_audit.to_dict("records"):
            rows.append(
                {
                    "source_name": row.get("category", ""),
                    "path": row.get("path", ""),
                    "exists": True,
                    "sha256": "",
                    "support_state": row.get("support_state", ""),
                    "units": row.get("units", ""),
                }
            )
    rows.append(
        {
            "source_name": "upstream_reverse_lifecycle_decision",
            "path": "",
            "exists": True,
            "sha256": "",
            "support_state": upstream_manifest.get("decision", ""),
            "units": "",
        }
    )
    return pd.DataFrame(rows)


def markdown_table(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    limit: int | None = None,
) -> list[str]:
    if frame.empty:
        return ["_none_"]
    subset = frame.loc[:, [column for column in columns if column in frame.columns]].copy()
    if limit is not None:
        subset = subset.head(limit)
    if subset.empty:
        return ["_none_"]
    lines = [
        "| " + " | ".join(subset.columns) + " |",
        "| " + " | ".join(":--" for _ in subset.columns) + " |",
    ]
    for _, row in subset.iterrows():
        lines.append(
            "| "
            + " | ".join(format_value(row[column]) for column in subset.columns)
            + " |"
        )
    return lines


def build_report(
    *,
    config: dict[str, Any],
    gate_summary: dict[str, Any],
    events: pd.DataFrame,
    baselines: pd.DataFrame,
    event_labels: pd.DataFrame,
    stats: pd.DataFrame,
    baseline_timing_audit: pd.DataFrame,
    baseline_attribution_audit: pd.DataFrame,
    false_repair_audit: pd.DataFrame,
    executability_audit: pd.DataFrame,
    threshold_audit: pd.DataFrame,
    source_audit: pd.DataFrame,
    near_winner_stats: pd.DataFrame,
    s6_audit: pd.DataFrame,
    output_paths: dict[str, Path],
) -> str:
    headline = headline_stats(
        stats, family="baseline_false_repair_excluded", split="all"
    )
    raw = headline_stats(stats, family="baseline_raw", split="all")
    source_git = git_revision(PROJECT_ROOT)
    upstream_manifest = source_audit.loc[
        source_audit["source_name"] == "upstream_reverse_lifecycle_manifest_json"
    ]
    upstream_decision = source_audit.loc[
        source_audit["source_name"] == "upstream_reverse_lifecycle_decision"
    ]
    headline_coverage = stats.loc[
        (stats["event_type"] == "E_S3_all")
        & (stats["regime_bucket"] == "all")
        & (stats["baseline_family"].isin(["baseline_raw", "baseline_false_repair_excluded"]))
    ].copy()
    timing_all = baseline_timing_audit.loc[
        baseline_timing_audit["split"] == "all"
    ].copy()
    exec_all = executability_audit.loc[
        (executability_audit["split"] == "all")
        & (executability_audit["year"] == "all")
        & (executability_audit["board_proxy"] == "all")
    ]
    threshold_summary = threshold_audit.groupby(
        ["freeze_basis", "oos_used_for_selection"], dropna=False
    ).size().reset_index(name="parameter_count")
    event_60d_count = len(event_labels)
    event_60d_censored = (
        int(event_labels["forward_return_60d_status"].eq(CENSORED_INCOMPLETE_HORIZON).sum())
        if "forward_return_60d_status" in event_labels.columns
        else 0
    )
    event_60d_complete_rate = (
        1.0 - event_60d_censored / event_60d_count if event_60d_count else np.nan
    )
    regime_count = (
        int(stats["regime_bucket"].dropna().astype(str).nunique())
        if "regime_bucket" in stats.columns
        else 0
    )
    lines = [
        "# 可观测锚点事件合约 V0 报告",
        "",
        f"最终决策：`{gate_summary['decision']}`",
        "",
        "## 合同摘要",
        "",
        "- 主事件：E_S3，EMA60 reclaim 后相对强度跳升并保持 20 个交易日。",
        "- 交易口径：t0 收盘确认，次一可成交开盘执行；本阶段只做事件标签评估，不做回测。",
        "- 唯一预注册 headline：E_S3 全集 vs baseline_false_repair_excluded 的 confirm_20 universal readout。",
        "- near-winner、G_S2、C_S6、60d 连续读数均为 secondary / diagnostic。",
        "- 行业数据状态：v0 为 unavailable，rank persistence 只使用 stock-vs-market 口径，无法排除行业 beta。",
        "",
        "## 输入与复现性",
        "",
        f"- source_git_revision: `{source_git}`",
        "- upstream_reverse_lifecycle_manifest_hash: "
        f"`{upstream_manifest.iloc[0]['sha256'] if not upstream_manifest.empty else ''}`",
        "- upstream_reverse_lifecycle_decision: "
        f"`{upstream_decision.iloc[0]['support_state'] if not upstream_decision.empty else ''}`",
        "- data_source_coverage_audit 记录全部输入路径、可用性与 hash；关键路径如下：",
        "",
        *markdown_table(
            source_audit.loc[
                source_audit["source_name"].astype(str).str.endswith(
                    ("_csv", "_json", "_parquet", "_dir")
                )
            ],
            ["source_name", "exists", "sha256", "path"],
            limit=12,
        ),
        "",
        "## 阈值冻结",
        "",
        *markdown_table(
            threshold_summary,
            ["freeze_basis", "oos_used_for_selection", "parameter_count"],
        ),
        "",
        "## Gate 摘要",
        "",
        "| metric | value |",
        "|:--|--:|",
    ]
    for key in [
        "total_event_count",
        "validation_event_count",
        "robustness_event_count",
        "executable_rate",
        "event_label_complete_rate",
        "baseline_match_coverage",
        "validation_baseline_match_coverage",
        "robustness_baseline_match_coverage",
        "headline_confirm20_rate_lift",
        "headline_confirm20_rate_diff",
        "headline_failure10_rate_diff",
        "headline_forward_return_20d_diff",
    ]:
        lines.append(f"| {key} | {format_value(gate_summary.get(key))} |")
    lines.extend(
        [
            "",
            f"blocked_reasons: `{json.dumps(gate_summary.get('blocked_reasons', []), ensure_ascii=False)}`",
            "",
            "## 关键读数",
            "",
            "| comparison | confirm20 lift | confirm20 diff | failure10 diff | forward20 diff | baseline coverage |",
            "|:--|--:|--:|--:|--:|--:|",
            (
                "| E_S3 vs baseline_false_repair_excluded | "
                f"{format_value(headline.get('confirm20_rate_lift'))} | "
                f"{format_value(headline.get('confirm20_rate_diff'))} | "
                f"{format_value(headline.get('failure10_rate_diff'))} | "
                f"{format_value(headline.get('forward_return_20d_diff'))} | "
                f"{format_value(headline.get('baseline_match_coverage'))} |"
            ),
            (
            "| E_S3 vs baseline_raw | "
            f"{format_value(raw.get('confirm20_rate_lift'))} | "
            f"{format_value(raw.get('confirm20_rate_diff'))} | "
            f"{format_value(raw.get('failure10_rate_diff'))} | "
            f"{format_value(raw.get('forward_return_20d_diff'))} | "
                f"{format_value(raw.get('baseline_match_coverage'))} |"
            ),
            "",
            "## 解释",
            "",
        ]
    )
    if gate_summary["decision"] == "event_contract_supported_universal_edge":
        lines.append(
            "E_S3 在剔除 as-of false-repair 后的 baseline 上仍保留前向优势，rank persistence 具备独立增量。"
        )
    elif gate_summary["decision"] == "event_contract_false_repair_filter_dominant_no_rank_persistence_separation":
        lines.append(
            "edge 主要来自假修复过滤，而不是 rank persistence 的独立增量；该结果不授权把 S3 升级为 universal entry。"
        )
    elif "sample_blocked" in gate_summary["decision"]:
        lines.append(
            "样本或 baseline coverage 未达到合同门槛。本结果是合法 blocked 状态，不应放宽阈值或改挑维度。"
        )
    elif gate_summary["decision"] == "event_contract_executability_blocked":
        lines.append(
            "可执行性或标签完整性未过门。本阶段不得用不可成交或截断标签补足 headline 结论。"
        )
    else:
        lines.append(
            "E_S3 未能在预注册 headline 口径下证明相对匹配基线的稳定前向分离。"
        )
    false_rate = (
        float(events["event_invalidated_false_repair"].mean()) if len(events) else np.nan
    )
    lines.extend(
        [
            "",
            "## Baseline Coverage Gate",
            "",
            *markdown_table(
                headline_coverage,
                [
                    "baseline_family",
                    "split",
                    "baseline_match_coverage",
                    "matched_event_count",
                    "unmatched_event_count",
                    "cross_split_boundary_unusable_count",
                ],
            ),
            "",
            "headline 主判定只使用 baseline_false_repair_excluded；raw family 只能作为归因诊断，不能替代 excluded coverage gate。",
            "",
            "## 执行性与 Censoring",
            "",
            *markdown_table(
                exec_all,
                [
                    "executable_rate_denominator_count",
                    "executable_rate_numerator_count",
                    "non_executable_next_open_count",
                    "limit_rule_unavailable_count",
                    "executable_rate",
                    "main_label_complete_rate",
                ],
            ),
            "",
            f"- 60d continuous readout rows: {event_60d_count}",
            f"- 60d censored_incomplete_horizon rows: {event_60d_censored}",
            f"- 60d horizon complete rate: {format_value(event_60d_complete_rate)}",
            "- 60d 连续读数不进入 confirm_20 / failure_10 主标签完整性判断。",
            "",
            "## Baseline Timing Audit",
            "",
            *markdown_table(
                timing_all,
                [
                    "baseline_family",
                    "baseline_t0_policy",
                    "baseline_count",
                    "median_reclaim_to_baseline_t0_days",
                    "confirm20_rate",
                    "failure10_rate",
                    "forward_return_20d_mean",
                    "policy_used_for_main_claim",
                ],
            ),
            "",
            "observed_failure_decision_date 是唯一主 baseline t0；deterministic_max_horizon 只用于 timing 敏感性诊断。",
            "",
            "## False-Repair Attribution",
            "",
            *markdown_table(
                baseline_attribution_audit.loc[
                    baseline_attribution_audit["split"] == "all"
                ],
                [
                    "baseline_family",
                    "baseline_false_repair_asof_count",
                    "event_vs_baseline_confirm20_lift",
                    "event_vs_baseline_failure10_diff",
                    "event_vs_baseline_forward_return_20d_diff",
                    "rank_persistence_independent_edge_status",
                ],
            ),
            "",
            "## Secondary / Diagnostic Readouts",
            "",
            *markdown_table(
                stats.loc[
                    (stats["event_type"] == "E_S3_and_G_S2")
                    & (stats["baseline_family"] == "baseline_false_repair_excluded")
                    & (stats["split"] == "all")
                    & (stats["regime_bucket"] == "all")
                ],
                [
                    "event_type",
                    "confirm20_rate_lift",
                    "failure10_rate_diff",
                    "forward_return_20d_diff",
                    "baseline_match_coverage",
                ],
            ),
            "",
            *markdown_table(
                near_winner_stats,
                [
                    "comparison",
                    "split",
                    "near_winner_count",
                    "near_winner_confirm20_pos_rate",
                    "near_winner_forward_return_20d_mean",
                    "claim_status",
                ],
            ),
            "",
            *markdown_table(
                s6_audit,
                [
                    "split",
                    "event_count",
                    "s6_axis_low_reference_pass_rate",
                    "s6_reclaim_close_contract_pass_rate",
                    "s6_basis_pass_rate_delta",
                ],
            ),
            "",
            "## 多重检验记录",
            "",
            f"- event_vs_baseline rows: {len(stats)}",
            f"- event sets: {', '.join(sorted(stats['event_type'].dropna().astype(str).unique())) if not stats.empty else ''}",
            f"- baseline families: {', '.join(sorted(stats['baseline_family'].dropna().astype(str).unique())) if not stats.empty else ''}",
            f"- split count: {stats['split'].dropna().astype(str).nunique() if not stats.empty else 0}",
            f"- regime bucket count: {regime_count}",
            "- pre-registered headline: E_S3_all / baseline_false_repair_excluded / confirm_20 / unconditional universal。",
            "- 其余 baseline_raw、failure_10、regime-conditioned、E_S3_and_G_S2、near-winner、C_S6、60d 连续读数均为 secondary / diagnostic。",
            "",
            "## 审计覆盖",
            "",
            f"- E_S3 candidate rows: {len(events)}",
            f"- baseline family rows: {len(baselines)}",
            f"- false-repair invalidation rate before final E_S3 filter: {format_value(false_rate)}",
            f"- false_repair_exclusion_audit rows: {len(false_repair_audit)}",
            f"- executability_audit rows: {len(executability_audit)}",
            "",
            "## 主要产物",
            "",
        ]
    )
    for name, path in sorted(output_paths.items()):
        if name.startswith("publishable."):
            lines.append(f"- `{name}`: `{path}`")
    lines.append("")
    return "\n".join(lines)


def format_value(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.4f}"
    return str(value)


def run_pipeline(
    config: dict[str, Any],
    *,
    config_path: Path,
    max_instruments: int | None = None,
) -> dict[str, Any]:
    paths = config["paths"]
    outputs = config["outputs"]
    table_dir = PROJECT_ROOT / outputs["publishable_tables_dir"]
    report_dir = PROJECT_ROOT / outputs["publishable_reports_dir"]
    local_cache_dir = PROJECT_ROOT / outputs["local_cache_dir"]
    large_raw_dir = PROJECT_ROOT / outputs["large_raw_dir"]
    manifest_dir = PROJECT_ROOT / outputs["manifests_dir"]
    for directory in [table_dir, report_dir, local_cache_dir, large_raw_dir, manifest_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    input_paths = {
        "stock_daily_csv_dir": PROJECT_ROOT / paths["stock_daily_csv_dir"],
        "benchmark_daily_csv": PROJECT_ROOT / paths["benchmark_daily_csv"],
        "executable_universe_csv": PROJECT_ROOT / paths["executable_universe_csv"],
        "data_prepare_run_manifest_json": PROJECT_ROOT
        / paths["data_prepare_run_manifest_json"],
        "data_prepare_source_coverage_audit_csv": PROJECT_ROOT
        / paths["data_prepare_source_coverage_audit_csv"],
        "upstream_reverse_lifecycle_manifest_json": PROJECT_ROOT
        / paths["upstream_reverse_lifecycle_manifest_json"],
        "upstream_shared_axis_sequence_dominance_csv": PROJECT_ROOT
        / paths["upstream_shared_axis_sequence_dominance_csv"],
        "upstream_big_winner_episode_reference_summary_csv": PROJECT_ROOT
        / paths["upstream_big_winner_episode_reference_summary_csv"],
        "upstream_matched_control_panel_parquet": PROJECT_ROOT
        / paths["upstream_matched_control_panel_parquet"],
        "upstream_anchor_aligned_daily_panel_parquet": PROJECT_ROOT
        / paths["upstream_anchor_aligned_daily_panel_parquet"],
    }
    validate_required_inputs(input_paths)
    upstream_manifest = json.loads(
        input_paths["upstream_reverse_lifecycle_manifest_json"].read_text(
            encoding="utf-8"
        )
    )
    if upstream_manifest.get("decision") != "reverse_lifecycle_sequence_supported_universal_dominance":
        raise RuntimeError(
            "Upstream reverse lifecycle decision is not supported universal dominance"
        )

    event_params = EventParams(**config["event_contract"])
    false_params = FalseRepairParams(**config["false_repair"])
    density_params = DensityParams(**config["density"])
    labels_cfg = config["labels"]
    label_params = LabelParams(
        confirm_horizon=int(labels_cfg["confirm_20"]["horizon_days"]),
        confirm_upper=float(labels_cfg["confirm_20"]["upper_barrier"]),
        confirm_lower=float(labels_cfg["confirm_20"]["lower_barrier"]),
        failure_horizon=int(labels_cfg["failure_10"]["horizon_days"]),
        failure_lower=float(labels_cfg["failure_10"]["lower_barrier"]),
        continuous_horizons=tuple(int(v) for v in labels_cfg["continuous_horizons"]),
        near_winner_horizon=int(labels_cfg["near_winner_horizon_days"]),
        near_winner_mfe_lower=float(labels_cfg["near_winner_mfe_lower"]),
        near_winner_mfe_upper=float(labels_cfg["near_winner_mfe_upper"]),
    )
    match_config = MatchConfig(
        max_controls_per_event=int(config["matching"]["max_controls_per_event"]),
        match_fields=tuple(config["matching"]["match_fields"]),
    )

    source_coverage = pd.read_csv(input_paths["data_prepare_source_coverage_audit_csv"])
    vwap_policy = resolve_vwap_source_policy(source_coverage)
    benchmark_daily = pd.read_csv(input_paths["benchmark_daily_csv"])
    market_features = _reverse.compute_market_features(benchmark_daily)
    calendar = (
        benchmark_daily.loc[benchmark_daily["index_alias"] == "all_a", "trade_date"]
        .dropna()
        .map(date_str)
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    split_config = SplitConfig(
        latest_label_complete_t0_date=latest_complete_t0_date(
            calendar, label_params.confirm_horizon
        ),
        **config["splits"],
    )

    universe = pd.read_csv(input_paths["executable_universe_csv"])
    universe["usable_trade_date"] = pd.to_datetime(
        universe["usable_trade_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    universe = universe.dropna(subset=["instrument", "usable_trade_date"])
    instruments = sorted(universe["instrument"].unique())
    if max_instruments is not None:
        instruments = instruments[:max_instruments]
    grouped_membership = {
        instrument: group.sort_values("usable_trade_date").reset_index(drop=True)
        for instrument, group in universe.groupby("instrument", sort=False)
    }

    daily_by_instrument: dict[str, pd.DataFrame] = {}
    seed_parts: list[pd.DataFrame] = []
    reclaim_parts: list[pd.DataFrame] = []
    event_parts: list[pd.DataFrame] = []
    baseline_parts: list[pd.DataFrame] = []
    qlib_dir = input_paths["stock_daily_csv_dir"]
    for index, instrument in enumerate(instruments, start=1):
        if index == 1 or index % 50 == 0 or index == len(instruments):
            print(f"processing {index}/{len(instruments)} {instrument}", flush=True)
        daily_path = qlib_dir / f"{instrument}.csv"
        if not daily_path.is_file():
            continue
        raw_daily = pd.read_csv(daily_path)
        raw_daily["instrument"] = instrument
        membership = grouped_membership[instrument]
        board_bucket = most_common_text(membership["board_bucket"])
        features = _reverse.compute_stock_features(
            raw_daily,
            vwap_source_units_compatible=bool(vwap_policy["compatible"]),
        )
        features["instrument"] = instrument
        features = _reverse.add_market_features(features, market_features, board_bucket)
        daily_by_instrument[instrument] = features
        built = build_event_and_baseline_rows_for_instrument(
            instrument=instrument,
            daily=features,
            membership=membership,
            event_params=event_params,
            false_params=false_params,
            density_params=density_params,
            label_params=label_params,
            split_config=split_config,
        )
        if not built["candidate_seed_pool"].empty:
            seed_parts.append(built["candidate_seed_pool"])
        if not built["reclaim_pool"].empty:
            reclaim_parts.append(built["reclaim_pool"])
        if not built["events"].empty:
            event_parts.append(built["events"])
        if not built["baselines"].empty:
            baseline_parts.append(built["baselines"])

    seeds = concat_or_empty(seed_parts)
    reclaims = concat_or_empty(reclaim_parts)
    event_candidates = concat_or_empty(event_parts)
    baseline_candidates = concat_or_empty(baseline_parts)
    if not event_candidates.empty:
        event_candidates = event_candidates.loc[
            event_candidates["split"] != "outside_split"
        ].reset_index(drop=True)
    if not baseline_candidates.empty:
        baseline_candidates = baseline_candidates.loc[
            baseline_candidates["split"] != "outside_split"
        ].reset_index(drop=True)

    final_events = event_candidates.loc[
        (event_candidates["density_kept"])
        & (~event_candidates["event_invalidated_false_repair"])
    ].copy()
    baseline_family_pool = duplicate_baseline_families(
        baseline_candidates.loc[baseline_candidates["density_kept"]].copy()
    )
    if not final_events.empty and not baseline_family_pool.empty:
        final_events, baseline_family_pool = assign_match_buckets(
            final_events, baseline_family_pool
        )

    event_labels, baseline_labels = build_label_outcomes(
        final_events,
        baseline_family_pool,
        daily_by_instrument,
        label_params=label_params,
    )
    match_parts: list[pd.DataFrame] = []
    audit_parts: list[pd.DataFrame] = []
    for family in ["baseline_raw", "baseline_false_repair_excluded"]:
        matches, audit = match_baselines(
            final_events,
            baseline_family_pool,
            family=family,
            match_config=match_config,
        )
        if not matches.empty:
            match_parts.append(matches)
        if not audit.empty:
            audit_parts.append(audit)
    matches = concat_or_empty(match_parts)
    match_audit = concat_or_empty(audit_parts)
    stats = summarize_event_vs_baseline(
        final_events,
        baseline_family_pool,
        event_labels,
        baseline_labels,
        matches,
        match_audit,
    )
    oos_unconditional, oos_regime = build_oos_readouts(stats)
    near_winner_stats = build_near_winner_forward_stats(final_events, event_labels)
    false_repair_audit = build_false_repair_exclusion_audit(event_candidates)
    density_audit = build_density_audit(
        seeds, reclaims, event_candidates, baseline_candidates
    )
    executability_audit = build_executability_audit(final_events, event_labels)
    threshold_audit = build_threshold_freeze_audit(config)
    contract_definition = build_contract_definition(config)
    s6_audit = build_s6_basis_transform_audit(final_events)
    baseline_timing_audit = build_baseline_timing_audit(
        baseline_family_pool,
        baseline_labels,
        daily_by_instrument=daily_by_instrument,
        event_params=event_params,
        false_params=false_params,
        label_params=label_params,
        split_config=split_config,
    )
    baseline_attribution_audit = build_baseline_false_repair_attribution_audit(
        stats, baseline_family_pool
    )
    source_audit = build_data_source_coverage_audit(
        input_paths=input_paths,
        source_coverage_audit=source_coverage,
        upstream_manifest=upstream_manifest,
    )
    event_aligned_panel = build_event_aligned_panel(final_events, daily_by_instrument)

    gate_summary = evaluate_decision(
        events=final_events,
        event_labels=event_labels,
        stats=stats,
        gates=config["gates"],
        executability_audit=executability_audit,
    )
    decision = gate_summary["decision"]

    output_paths: dict[str, Path] = {}
    publishable_tables = {
        "event_contract_definition": contract_definition,
        "event_instances": final_events,
        "event_label_outcomes": pd.concat(
            [event_labels, baseline_labels], ignore_index=True
        ),
        "event_vs_baseline_forward_stats": stats,
        "event_vs_near_winner_forward_stats": near_winner_stats,
        "baseline_t0_timing_audit": baseline_timing_audit,
        "baseline_false_repair_attribution_audit": baseline_attribution_audit,
        "false_repair_exclusion_audit": false_repair_audit,
        "event_density_audit": density_audit,
        "threshold_freeze_audit": threshold_audit,
        "s6_basis_transform_audit": s6_audit,
        "data_source_coverage_audit": source_audit,
        "oos_readout_unconditional": oos_unconditional,
        "oos_readout_regime_conditioned": oos_regime,
        "executability_audit": executability_audit,
    }
    for name, frame in publishable_tables.items():
        output_paths[f"publishable.tables.{name}"] = write_dataframe(
            table_dir / f"{name}.csv", frame
        )
    output_paths["local_cache.candidate_seed_pool"] = write_dataframe(
        local_cache_dir / "candidate_seed_pool.parquet", seeds
    )
    output_paths["local_cache.event_aligned_panel"] = write_dataframe(
        local_cache_dir / "event_aligned_panel.parquet", event_aligned_panel
    )
    output_paths["large_raw.baseline_event_pool"] = write_dataframe(
        large_raw_dir / "baseline_event_pool.parquet", baseline_family_pool
    )
    output_paths["large_raw.event_candidate_pool"] = write_dataframe(
        large_raw_dir / "event_candidate_pool.parquet", event_candidates
    )
    output_paths["large_raw.baseline_match_panel"] = write_dataframe(
        large_raw_dir / "baseline_match_panel.parquet", matches
    )

    report_path = report_dir / "observable_anchor_event_contract_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_text = build_report(
        config=config,
        gate_summary=gate_summary,
        events=event_candidates,
        baselines=baseline_family_pool,
        event_labels=event_labels,
        stats=stats,
        baseline_timing_audit=baseline_timing_audit,
        baseline_attribution_audit=baseline_attribution_audit,
        false_repair_audit=false_repair_audit,
        executability_audit=executability_audit,
        threshold_audit=threshold_audit,
        source_audit=source_audit,
        near_winner_stats=near_winner_stats,
        s6_audit=s6_audit,
        output_paths=output_paths,
    )
    report_path.write_text(report_text, encoding="utf-8")
    output_paths["publishable.reports.observable_anchor_event_contract_report"] = report_path

    manifest_path = manifest_dir / "run_manifest.json"
    write_manifest(
        manifest_path=manifest_path,
        config=config,
        config_path=config_path,
        input_paths=input_paths,
        output_paths=output_paths,
        decision=decision,
        gate_summary=gate_summary,
        upstream_manifest=upstream_manifest,
    )
    return {
        "decision": decision,
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
        "event_count": len(final_events),
        "baseline_count": len(baseline_family_pool),
    }

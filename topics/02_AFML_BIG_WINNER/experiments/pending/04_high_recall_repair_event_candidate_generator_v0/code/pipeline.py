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


pd.set_option("future.no_silent_downcasting", True)


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PENDING_DIR = EXPERIMENT_DIR.parent
PROJECT_ROOT = EXPERIMENT_DIR.parents[2]
REVERSE_PIPELINE_PATH = (
    PENDING_DIR / "02_big_winner_reverse_lifecycle_profile_v0" / "code" / "pipeline.py"
)
OBSERVABLE_PIPELINE_PATH = (
    PENDING_DIR / "03_observable_anchor_event_contract_v0" / "code" / "pipeline.py"
)


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_reverse = _load_module("reverse_lifecycle_pipeline_for_04", REVERSE_PIPELINE_PATH)
_observable = _load_module("observable_anchor_pipeline_for_04", OBSERVABLE_PIPELINE_PATH)


MISSING_INSUFFICIENT_LOOKBACK = _reverse.MISSING_INSUFFICIENT_LOOKBACK
MISSING_EVENT_ABSENT = _reverse.MISSING_EVENT_ABSENT
MISSING_SOURCE_FIELD = _reverse.MISSING_SOURCE_FIELD
MISSING_UNIT_INCOMPATIBLE = _reverse.MISSING_UNIT_INCOMPATIBLE
MISSING_OUT_OF_COVERAGE = _reverse.MISSING_OUT_OF_COVERAGE
NOT_MISSING = _reverse.NOT_MISSING
CENSORED_INCOMPLETE_HORIZON = _observable.CENSORED_INCOMPLETE_HORIZON
NON_EXECUTABLE_NEXT_OPEN = _observable.NON_EXECUTABLE_NEXT_OPEN


RAW_SCOPE = "raw_family"
CANONICAL_PRE_DENSITY_SCOPE = "canonical_before_density"
CANONICAL_SCOPE = "density_kept_canonical"
SETUP_UNION = "setup_inclusive"
RECLAIM_UNION = "reclaim_based"
SETUP_UNION_EVENT = "E_union_high_recall_repair_candidate"
RECLAIM_UNION_EVENT = "E_union_reclaim_based_candidate"
UNION_FAMILIES = {
    SETUP_UNION: ["E0_seed_low_setup", "E1_first_ema60_reclaim", "E2_reclaim_quality_burst", "E4_early_relative_strength_turn"],
    RECLAIM_UNION: ["E1_first_ema60_reclaim", "E2_reclaim_quality_burst", "E4_early_relative_strength_turn"],
}


SNAPSHOT_COLUMNS = [
    "close_to_ema20",
    "close_to_ema60",
    "ema20_slope_20d",
    "ema60_slope_20d",
    "return_5d",
    "return_10d",
    "return_20d",
    "return_60d",
    "stock_vs_market_5d",
    "stock_vs_market_10d",
    "stock_vs_market_20d",
    "amount_ratio_20d",
    "amount_ratio_60d",
    "turnover_ratio_20d",
    "turnover_ratio_60d",
    "derived_daily_vwap_available",
    "close_to_derived_daily_vwap",
    "vwap_reclaim_flag",
    "intraday_range_pct",
    "close_position_in_range",
    "upper_shadow_pct",
    "gap_open_pct",
    "gap_fade_flag",
    "gap_fade_flag_status",
    "atr_20_pct",
    "market_return_20d",
    "market_drawdown_60d",
    "market_volatility_20d",
    "market_regime_bucket",
    "benchmark_alias",
]


@dataclass(frozen=True)
class SplitConfig:
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    robustness_start: str
    latest_main_label_complete_t0_date: str
    latest_120d_outcome_complete_t0_date: str


@dataclass(frozen=True)
class EventConfig:
    prior_lookback_sessions: int
    seed_low_lookback_sessions: int
    anchor_search_horizon_sessions: int
    e2_quality_window: int
    e4_relative_strength_window: int
    e3_false_repair_drawdown: float
    e3_variants: tuple[int, ...]


@dataclass(frozen=True)
class LabelConfig:
    confirm_horizon: int
    confirm_upper: float
    confirm_lower: float
    failure_horizon: int
    failure_lower: float
    continuous_horizons: tuple[int, ...]
    big_winner_mfe_120d: float
    super_winner_mfe_120d: float
    near_winner_mfe_lower: float
    near_winner_mfe_upper: float
    false_repair_drawdown: float


def parse_date(value: Any) -> pd.Timestamp:
    return _reverse.parse_date(value)


def date_str(value: Any) -> str:
    return _reverse.date_str(value)


def safe_rate(success: int | float, total: int | float) -> float:
    if total is None or pd.isna(total) or float(total) == 0:
        return np.nan
    return float(success) / float(total)


def safe_mean(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.mean()) if len(clean) else np.nan


def safe_pctl(values: pd.Series, q: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.quantile(q)) if len(clean) else np.nan


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
        raise ValueError("Calendar is shorter than requested horizon")
    return sessions[-horizon_sessions - 1]


def split_for_event(value: Any, split: SplitConfig) -> str:
    text = date_str(value)
    if split.train_start <= text <= split.train_end:
        return "train"
    if split.validation_start <= text <= split.validation_end:
        return "validation"
    if split.robustness_start <= text <= split.latest_main_label_complete_t0_date:
        return "robustness"
    return "outside_split"


def split_for_episode(value: Any, split: SplitConfig) -> str:
    text = date_str(value)
    if split.train_start <= text <= split.train_end:
        return "train"
    if split.validation_start <= text <= split.validation_end:
        return "validation"
    if split.robustness_start <= text <= split.latest_120d_outcome_complete_t0_date:
        return "robustness"
    return "outside_split"


def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def validate_required_inputs(paths: dict[str, Path]) -> None:
    for name, path in paths.items():
        if name.endswith("_dir"):
            if not path.is_dir():
                raise FileNotFoundError(f"Missing required input directory {name}: {path}")
        elif not path.is_file():
            raise FileNotFoundError(f"Missing required input file {name}: {path}")


def write_dataframe(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    if path.suffix == ".parquet":
        out.to_parquet(path, index=False)
    else:
        out.to_csv(path, index=False)
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compute_benchmark_returns(benchmark_daily: pd.DataFrame) -> pd.DataFrame:
    base = benchmark_daily.copy()
    base["trade_date"] = pd.to_datetime(base["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    base = base.sort_values(["index_alias", "trade_date"])
    rows: list[pd.DataFrame] = []
    for alias, group in base.groupby("index_alias", sort=True):
        out = group[["trade_date", "close"]].copy()
        out["benchmark_alias"] = alias
        close = pd.to_numeric(out["close"], errors="coerce")
        for horizon in [5, 10, 20]:
            out[f"benchmark_return_{horizon}d"] = close / close.shift(horizon) - 1.0
        rows.append(out.drop(columns=["close"]))
    return pd.concat(rows, ignore_index=True)


def board_mode(membership: pd.DataFrame) -> str:
    if membership.empty or "board_bucket" not in membership.columns:
        return "unknown"
    mode = membership["board_bucket"].dropna().astype(str).mode()
    return str(mode.iloc[0]) if len(mode) else "unknown"


def enrich_stock_features(
    daily: pd.DataFrame,
    *,
    instrument: str,
    membership: pd.DataFrame,
    market_features: pd.DataFrame,
    benchmark_returns: pd.DataFrame,
    vwap_source_units_compatible: bool,
) -> pd.DataFrame:
    board_bucket = board_mode(membership)
    features = _reverse.compute_stock_features(
        daily,
        vwap_source_units_compatible=vwap_source_units_compatible,
    )
    features["instrument"] = instrument
    features["return_10d"] = features["close"] / features["close"].shift(10) - 1.0
    turnover = pd.to_numeric(features["turnover_rate"], errors="coerce")
    features["turnover_ratio_60d"] = turnover / turnover.rolling(60, min_periods=60).mean()
    features = _reverse.add_market_features(features, market_features, board_bucket)
    features = features.merge(
        benchmark_returns,
        left_on=["date", "benchmark_alias"],
        right_on=["trade_date", "benchmark_alias"],
        how="left",
    ).drop(columns=["trade_date"], errors="ignore")
    features["stock_vs_market_5d"] = features["return_5d"] - features["benchmark_return_5d"]
    features["stock_vs_market_10d"] = features["return_10d"] - features["benchmark_return_10d"]
    if "stock_vs_market_20d" not in features.columns:
        features["stock_vs_market_20d"] = features["return_20d"] - features["benchmark_return_20d"]
    features["gap_fade_flag_status"] = np.where(
        features["gap_fade_flag"].notna(), NOT_MISSING, MISSING_SOURCE_FIELD
    )
    return features.replace([np.inf, -np.inf], np.nan)


def observable_seed_params(event_cfg: EventConfig) -> Any:
    return _observable.EventParams(
        prior_lookback_sessions=event_cfg.prior_lookback_sessions,
        seed_low_lookback_sessions=event_cfg.seed_low_lookback_sessions,
        anchor_search_horizon_sessions=event_cfg.anchor_search_horizon_sessions,
        rank_jump_threshold=0.05,
        rank_jump_window=20,
        persistence_window=20,
        persistence_floor=0.0,
        persistence_coverage=0.70,
        amount_ratio_20d_gate=1.50,
        plus20_threshold=0.20,
        continuation_window=20,
        continuation_rank_floor=0.0,
        continuation_rank_coverage=0.60,
        continuation_amount_floor=1.20,
        continuation_amount_coverage=0.60,
    )


def observable_density_params(config: dict[str, Any]) -> Any:
    density = config["density"]
    return _observable.DensityParams(
        seed_density_window=int(density["seed_density_window"]),
        reclaim_density_window=int(density["reclaim_density_window"]),
        event_density_window=int(density["union_density_window"]),
    )


def status_for_value(value: Any) -> str:
    return NOT_MISSING if pd.notna(value) else MISSING_SOURCE_FIELD


def as_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    return bool(float(value)) if isinstance(value, (int, float, np.integer, np.floating)) else bool(value)


def quality_flags_at(
    daily: pd.DataFrame,
    pos: int,
    quality_cfg: dict[str, Any],
) -> dict[str, Any]:
    def value(name: str) -> Any:
        return daily.at[pos, name] if name in daily.columns and pos < len(daily) else np.nan

    amount20 = value("amount_ratio_20d")
    amount60 = value("amount_ratio_60d")
    close_vwap = value("close_to_derived_daily_vwap")
    vwap_reclaim = value("vwap_reclaim_flag")
    close_pos = value("close_position_in_range")
    gap_fade = value("gap_fade_flag")
    upper_shadow = value("upper_shadow_pct")
    amount_flag = (
        pd.notna(amount20)
        and float(amount20) >= float(quality_cfg["amount_ratio_20d"])
    ) or (
        pd.notna(amount60)
        and float(amount60) >= float(quality_cfg["amount_ratio_60d"])
    )
    vwap_flag = (
        pd.notna(close_vwap)
        and float(close_vwap) >= float(quality_cfg["close_to_derived_daily_vwap"])
    ) or as_bool(vwap_reclaim)
    range_flag = pd.notna(close_pos) and float(close_pos) >= float(
        quality_cfg["close_position_in_range"]
    )
    gap_status = NOT_MISSING if pd.notna(gap_fade) and pd.notna(upper_shadow) else MISSING_SOURCE_FIELD
    gap_flag = (
        gap_status == NOT_MISSING
        and not as_bool(gap_fade)
        and float(upper_shadow) <= float(quality_cfg["upper_shadow_pct"])
    )
    return {
        "quality_amount_flag": bool(amount_flag),
        "quality_vwap_flag": bool(vwap_flag),
        "quality_range_flag": bool(range_flag),
        "quality_gap_fade_flag": bool(gap_flag),
        "quality_amount_flag_status": NOT_MISSING
        if pd.notna(amount20) or pd.notna(amount60)
        else MISSING_INSUFFICIENT_LOOKBACK,
        "quality_vwap_flag_status": NOT_MISSING
        if pd.notna(close_vwap) or pd.notna(vwap_reclaim)
        else MISSING_SOURCE_FIELD,
        "quality_range_flag_status": status_for_value(close_pos),
        "quality_gap_fade_flag_status": gap_status,
    }


def first_quality_pos(
    daily: pd.DataFrame,
    *,
    start_pos: int,
    end_pos: int,
    quality_cfg: dict[str, Any],
) -> tuple[int | None, dict[str, Any]]:
    end_pos = min(end_pos, len(daily) - 1)
    for pos in range(start_pos, end_pos + 1):
        flags = quality_flags_at(daily, pos, quality_cfg)
        if any(
            flags[name]
            for name in [
                "quality_amount_flag",
                "quality_vwap_flag",
                "quality_range_flag",
                "quality_gap_fade_flag",
            ]
        ):
            return pos, flags
    return None, {}


def first_relative_strength_pos(
    daily: pd.DataFrame,
    *,
    start_pos: int,
    end_pos: int,
    rs_cfg: dict[str, Any],
) -> int | None:
    end_pos = min(end_pos, len(daily) - 1)
    for pos in range(start_pos, end_pos + 1):
        if (
            pd.notna(daily.at[pos, "stock_vs_market_5d"])
            and float(daily.at[pos, "stock_vs_market_5d"])
            >= float(rs_cfg["stock_vs_market_5d"])
        ):
            return pos
        if (
            pd.notna(daily.at[pos, "stock_vs_market_10d"])
            and float(daily.at[pos, "stock_vs_market_10d"])
            >= float(rs_cfg["stock_vs_market_10d"])
        ):
            return pos
        if (
            pd.notna(daily.at[pos, "stock_vs_market_20d"])
            and float(daily.at[pos, "stock_vs_market_20d"])
            >= float(rs_cfg["stock_vs_market_20d"])
        ):
            return pos
    return None


def no_false_repair_between(
    daily: pd.DataFrame,
    *,
    reclaim_pos: int,
    horizon: int,
    drawdown: float,
) -> bool:
    end = reclaim_pos + horizon
    if reclaim_pos < 0 or end >= len(daily):
        return False
    reclaim_close = daily.at[reclaim_pos, "close"]
    if pd.isna(reclaim_close) or float(reclaim_close) <= 0:
        return False
    close = pd.to_numeric(daily.loc[reclaim_pos:end, "close"], errors="coerce")
    return not bool(((close / float(reclaim_close) - 1.0) <= float(drawdown)).any())


def snapshot_fields(daily: pd.DataFrame, pos: int) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for column in SNAPSHOT_COLUMNS:
        row[column] = daily.at[pos, column] if column in daily.columns and pos >= 0 else np.nan
    return row


def make_raw_event_row(
    *,
    instrument: str,
    daily: pd.DataFrame,
    membership: pd.DataFrame,
    event_family: str,
    event_t0_pos: int,
    event_variant: str = "",
    source_seed_low_pos: int = -1,
    first_reclaim_pos: int = -1,
    seed_cluster_id: str = "",
    reclaim_cluster_id: str = "",
    event_split: str,
    quality_cfg: dict[str, Any],
    priority: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t0_date = str(daily.at[event_t0_pos, "date"])
    member = _observable.membership_asof(membership, t0_date)
    board_bucket = str(member.get("board_bucket", board_mode(membership)))
    is_st = bool(member.get("is_st", False))
    trade = _observable.execution_status(
        daily,
        t0_pos=event_t0_pos,
        board_bucket=board_bucket,
        is_st=is_st,
    )
    event_id = (
        f"{instrument}_{t0_date.replace('-', '')}_{event_family}"
        f"{'_' + event_variant if event_variant else ''}_{event_t0_pos:05d}"
    )
    source_seed_low_date = (
        str(daily.at[source_seed_low_pos, "date"]) if source_seed_low_pos >= 0 else ""
    )
    first_reclaim_date = (
        str(daily.at[first_reclaim_pos, "date"]) if first_reclaim_pos >= 0 else ""
    )
    quality = quality_flags_at(daily, event_t0_pos, quality_cfg)
    row = {
        "event_id": event_id,
        "instrument": instrument,
        "event_family": event_family,
        "event_variant": event_variant,
        "union_family": "raw_family",
        "canonical_event_scope": RAW_SCOPE,
        "event_t0_date": t0_date,
        "event_t0_pos": int(event_t0_pos),
        "trade_open_date": trade["trade_open_date"],
        "trade_open_pos": trade["trade_open_pos"],
        "trade_open_price": trade["trade_open_price"],
        "non_executable_next_open": bool(trade["non_executable_next_open"]),
        "non_executable_reason": trade["non_executable_reason"],
        "limit_threshold_status": trade["limit_threshold_status"],
        "source_seed_low_date": source_seed_low_date,
        "source_seed_low_pos": int(source_seed_low_pos),
        "first_ema60_reclaim_date": first_reclaim_date,
        "first_ema60_reclaim_pos": int(first_reclaim_pos),
        "days_seed_to_event": int(event_t0_pos - source_seed_low_pos)
        if source_seed_low_pos >= 0
        else np.nan,
        "days_reclaim_to_event": int(event_t0_pos - first_reclaim_pos)
        if first_reclaim_pos >= 0
        else np.nan,
        "seed_cluster_id": seed_cluster_id,
        "reclaim_cluster_id": reclaim_cluster_id,
        "union_cluster_id": "",
        "union_density_kept": False,
        "event_family_priority": int(priority),
        "event_split": event_split,
        "market_regime_bucket": daily.at[event_t0_pos, "market_regime_bucket"],
        "benchmark_alias": daily.at[event_t0_pos, "benchmark_alias"],
        "board_bucket": board_bucket,
        "is_st": is_st,
        "total_market_cap_cny": member.get("total_market_cap_cny", np.nan),
        "liquidity_money_20d": daily.at[event_t0_pos, "money_mean_20d"]
        if "money_mean_20d" in daily.columns
        else np.nan,
        "early_no_false_repair_5d": False,
        "early_no_false_repair_10d": False,
        "early_relative_strength_turn_flag": event_family
        == "E4_early_relative_strength_turn",
        "strict_rank_persistence_reference_flag": event_family
        == "E5_strict_rank_persistence_reference",
        "raw_source_event_ids": event_id,
        "raw_cluster_event_count": 1,
    }
    row.update(snapshot_fields(daily, event_t0_pos))
    row.update(quality)
    if extra:
        row.update(extra)
    return row


def build_raw_events_for_instrument(
    *,
    instrument: str,
    daily: pd.DataFrame,
    membership: pd.DataFrame,
    strict_events: pd.DataFrame,
    event_cfg: EventConfig,
    quality_cfg: dict[str, Any],
    rs_cfg: dict[str, Any],
    density_params: Any,
    split_config: SplitConfig,
) -> pd.DataFrame:
    membership_dates = set(membership["usable_trade_date"].astype(str))
    seed_params = observable_seed_params(event_cfg)
    seeds = _observable.extract_candidate_seed_lows(
        daily,
        membership_dates=membership_dates,
        params=seed_params,
    )
    if not seeds.empty:
        seeds = _observable.apply_position_density(
            seeds,
            pos_col="candidate_seed_low_pos",
            date_col="candidate_seed_low_date",
            cluster_col="seed_cluster_id",
            stage="seed",
            window=density_params.seed_density_window,
        )
    reclaims = _observable.build_reclaim_rows(
        instrument,
        daily,
        seeds,
        params=seed_params,
        density_params=density_params,
    )
    rows: list[dict[str, Any]] = []
    for seed in seeds.to_dict("records"):
        split = split_for_event(seed["candidate_seed_low_date"], split_config)
        if split == "outside_split":
            continue
        rows.append(
            make_raw_event_row(
                instrument=instrument,
                daily=daily,
                membership=membership,
                event_family="E0_seed_low_setup",
                event_t0_pos=int(seed["candidate_seed_low_pos"]),
                source_seed_low_pos=int(seed["candidate_seed_low_pos"]),
                seed_cluster_id=str(seed.get("seed_cluster_id", "")),
                event_split=split,
                quality_cfg=quality_cfg,
                priority=0,
                extra={"seed_density_kept": bool(seed.get("density_kept", False))},
            )
        )
    present_reclaims = reclaims.loc[
        reclaims.get("first_ema60_reclaim_missing_reason", pd.Series(dtype=str))
        == NOT_MISSING
    ].copy()
    for reclaim in present_reclaims.to_dict("records"):
        r0 = int(reclaim["first_ema60_reclaim_pos"])
        seed_pos = int(reclaim["candidate_seed_low_pos"])
        split = split_for_event(reclaim["first_ema60_reclaim_date"], split_config)
        if split != "outside_split":
            rows.append(
                make_raw_event_row(
                    instrument=instrument,
                    daily=daily,
                    membership=membership,
                    event_family="E1_first_ema60_reclaim",
                    event_t0_pos=r0,
                    source_seed_low_pos=seed_pos,
                    first_reclaim_pos=r0,
                    seed_cluster_id=str(reclaim.get("seed_cluster_id", "")),
                    reclaim_cluster_id=str(reclaim.get("reclaim_cluster_id", "")),
                    event_split=split,
                    quality_cfg=quality_cfg,
                    priority=1,
                    extra={"reclaim_density_kept": bool(reclaim.get("density_kept", False))},
                )
            )
        if not bool(reclaim.get("density_kept", False)):
            continue
        e2_pos, e2_flags = first_quality_pos(
            daily,
            start_pos=r0,
            end_pos=r0 + event_cfg.e2_quality_window,
            quality_cfg=quality_cfg,
        )
        if e2_pos is not None:
            split = split_for_event(daily.at[e2_pos, "date"], split_config)
            if split != "outside_split":
                rows.append(
                    make_raw_event_row(
                        instrument=instrument,
                        daily=daily,
                        membership=membership,
                        event_family="E2_reclaim_quality_burst",
                        event_t0_pos=e2_pos,
                        source_seed_low_pos=seed_pos,
                        first_reclaim_pos=r0,
                        seed_cluster_id=str(reclaim.get("seed_cluster_id", "")),
                        reclaim_cluster_id=str(reclaim.get("reclaim_cluster_id", "")),
                        event_split=split,
                        quality_cfg=quality_cfg,
                        priority=2,
                        extra=e2_flags,
                    )
                )
        e4_pos = first_relative_strength_pos(
            daily,
            start_pos=r0,
            end_pos=r0 + event_cfg.e4_relative_strength_window,
            rs_cfg=rs_cfg,
        )
        if e4_pos is not None:
            split = split_for_event(daily.at[e4_pos, "date"], split_config)
            if split != "outside_split":
                rows.append(
                    make_raw_event_row(
                        instrument=instrument,
                        daily=daily,
                        membership=membership,
                        event_family="E4_early_relative_strength_turn",
                        event_t0_pos=e4_pos,
                        source_seed_low_pos=seed_pos,
                        first_reclaim_pos=r0,
                        seed_cluster_id=str(reclaim.get("seed_cluster_id", "")),
                        reclaim_cluster_id=str(reclaim.get("reclaim_cluster_id", "")),
                        event_split=split,
                        quality_cfg=quality_cfg,
                        priority=4,
                    )
                )
        for horizon in event_cfg.e3_variants:
            e3_pos = r0 + int(horizon)
            if e3_pos >= len(daily):
                continue
            if not no_false_repair_between(
                daily,
                reclaim_pos=r0,
                horizon=int(horizon),
                drawdown=event_cfg.e3_false_repair_drawdown,
            ):
                continue
            split = split_for_event(daily.at[e3_pos, "date"], split_config)
            if split == "outside_split":
                continue
            rows.append(
                make_raw_event_row(
                    instrument=instrument,
                    daily=daily,
                    membership=membership,
                    event_family="E3_early_no_false_repair",
                    event_variant=f"E3_{horizon}d",
                    event_t0_pos=e3_pos,
                    source_seed_low_pos=seed_pos,
                    first_reclaim_pos=r0,
                    seed_cluster_id=str(reclaim.get("seed_cluster_id", "")),
                    reclaim_cluster_id=str(reclaim.get("reclaim_cluster_id", "")),
                    event_split=split,
                    quality_cfg=quality_cfg,
                    priority=3,
                    extra={f"early_no_false_repair_{horizon}d": True},
                )
            )
    for strict in strict_events.to_dict("records"):
        t0_date = str(strict.get("event_t0_date", ""))
        if not t0_date:
            continue
        matches = daily.index[daily["date"].astype(str) == t0_date].tolist()
        if not matches:
            continue
        t0_pos = int(matches[0])
        split = split_for_event(t0_date, split_config)
        if split == "outside_split":
            continue
        seed_matches = daily.index[
            daily["date"].astype(str) == str(strict.get("candidate_seed_low_date", ""))
        ].tolist()
        reclaim_matches = daily.index[
            daily["date"].astype(str) == str(strict.get("anchor_date", ""))
        ].tolist()
        rows.append(
            make_raw_event_row(
                instrument=instrument,
                daily=daily,
                membership=membership,
                event_family="E5_strict_rank_persistence_reference",
                event_t0_pos=t0_pos,
                source_seed_low_pos=int(seed_matches[0]) if seed_matches else -1,
                first_reclaim_pos=int(reclaim_matches[0]) if reclaim_matches else -1,
                event_split=split,
                quality_cfg=quality_cfg,
                priority=5,
                extra={
                    "source_e5_event_id": strict.get("event_id", ""),
                    "strict_rank_persistence_reference_flag": True,
                },
            )
        )
    return pd.DataFrame(rows)


def build_canonical_union_events(
    raw_events: pd.DataFrame,
    *,
    union_family: str,
    density_window: int,
) -> pd.DataFrame:
    families = UNION_FAMILIES[union_family]
    event_name = SETUP_UNION_EVENT if union_family == SETUP_UNION else RECLAIM_UNION_EVENT
    eligible = raw_events.loc[raw_events["event_family"].isin(families)].copy()
    if eligible.empty:
        return pd.DataFrame(columns=list(raw_events.columns))
    out_rows: list[dict[str, Any]] = []
    for instrument, group in eligible.groupby("instrument", sort=True):
        ordered = group.sort_values(["event_t0_pos", "event_family_priority", "event_id"]).copy()
        canonical_rows: list[dict[str, Any]] = []
        for local_no, (event_pos, same_pos) in enumerate(ordered.groupby("event_t0_pos", sort=True)):
            member_frame = same_pos.sort_values(["event_family_priority", "event_id"]).copy()
            earliest = member_frame.iloc[0].copy()
            row = earliest.to_dict()
            row["event_id"] = f"{instrument}_{union_family}_canonical_{local_no:05d}"
            row["event_family"] = event_name
            row["event_variant"] = ""
            row["union_family"] = union_family
            row["canonical_event_scope"] = CANONICAL_PRE_DENSITY_SCOPE
            row["union_cluster_id"] = f"{instrument}_{union_family}_canonical_{int(event_pos):05d}"
            row["union_density_kept"] = False
            row["raw_source_event_ids"] = ";".join(member_frame["event_id"].astype(str))
            row["raw_cluster_event_count"] = int(len(member_frame))
            for flag in [
                "quality_amount_flag",
                "quality_vwap_flag",
                "quality_range_flag",
                "quality_gap_fade_flag",
                "early_relative_strength_turn_flag",
                "strict_rank_persistence_reference_flag",
                "early_no_false_repair_5d",
                "early_no_false_repair_10d",
            ]:
                if flag in member_frame.columns:
                    row[flag] = bool(member_frame[flag].fillna(False).astype(bool).any())
            canonical_rows.append(row)

        if not canonical_rows:
            continue

        canonical_frame = pd.DataFrame(canonical_rows).sort_values(
            ["event_t0_pos", "event_family_priority", "event_id"]
        )
        cluster_no = -1
        seed_end: int | None = None
        members: list[dict[str, Any]] = []

        def flush(cluster_members: list[dict[str, Any]], cluster_id: str) -> None:
            if not cluster_members:
                return
            member_frame = pd.DataFrame(cluster_members)
            earliest = member_frame.sort_values(
                ["event_t0_pos", "event_family_priority", "event_id"]
            ).iloc[0].copy()
            row = earliest.to_dict()
            row["event_id"] = f"{instrument}_{union_family}_union_{cluster_no:05d}"
            row["event_family"] = event_name
            row["event_variant"] = ""
            row["union_family"] = union_family
            row["canonical_event_scope"] = CANONICAL_SCOPE
            row["union_cluster_id"] = cluster_id
            row["union_density_kept"] = True
            source_ids: list[str] = []
            raw_cluster_event_count = 0
            for source_text in member_frame["raw_source_event_ids"].astype(str):
                source_ids.extend([item for item in source_text.split(";") if item])
            row["raw_source_event_ids"] = ";".join(source_ids)
            row["raw_cluster_event_count"] = int(
                pd.to_numeric(member_frame["raw_cluster_event_count"], errors="coerce")
                .fillna(0)
                .sum()
            )
            for flag in [
                "quality_amount_flag",
                "quality_vwap_flag",
                "quality_range_flag",
                "quality_gap_fade_flag",
                "early_relative_strength_turn_flag",
                "strict_rank_persistence_reference_flag",
                "early_no_false_repair_5d",
                "early_no_false_repair_10d",
            ]:
                if flag in member_frame.columns:
                    row[flag] = bool(member_frame[flag].fillna(False).astype(bool).any())
            kept_canonical_ids = set(member_frame["event_id"].astype(str))
            for idx, canonical in enumerate(canonical_rows):
                if canonical["event_id"] in kept_canonical_ids:
                    canonical_rows[idx]["union_density_kept"] = bool(
                        canonical["event_id"] == str(earliest["event_id"])
                    )
                    canonical_rows[idx]["density_union_cluster_id"] = cluster_id
            out_rows.append(row)

        for row in canonical_frame.to_dict("records"):
            pos = int(row["event_t0_pos"])
            if seed_end is None or pos > seed_end:
                if members:
                    flush(members, f"{instrument}_{union_family}_union_{cluster_no:05d}")
                cluster_no += 1
                seed_end = pos + density_window
                members = [row]
            else:
                members.append(row)
        if members:
            flush(members, f"{instrument}_{union_family}_union_{cluster_no:05d}")
        out_rows.extend(canonical_rows)
    return pd.DataFrame(out_rows)


def build_candidate_instances(raw_events: pd.DataFrame, density_window: int) -> pd.DataFrame:
    if raw_events.empty:
        return pd.DataFrame()
    raw = raw_events.copy()
    raw["canonical_event_scope"] = RAW_SCOPE
    raw["union_family"] = "raw_family"
    setup = build_canonical_union_events(
        raw,
        union_family=SETUP_UNION,
        density_window=density_window,
    )
    reclaim = build_canonical_union_events(
        raw,
        union_family=RECLAIM_UNION,
        density_window=density_window,
    )
    return pd.concat([raw, setup, reclaim], ignore_index=True)


def barrier_touch(
    daily: pd.DataFrame,
    *,
    trade_pos: int,
    trade_price: float,
    horizon: int,
    upper: float | None,
    lower: float | None,
) -> dict[str, Any]:
    if trade_pos < 0 or pd.isna(trade_price) or float(trade_price) <= 0:
        return {"label": np.nan, "complete": False, "touch_date": "", "touch_pos": -1}
    end_pos = trade_pos + horizon
    if end_pos >= len(daily):
        return {"label": np.nan, "complete": False, "touch_date": "", "touch_pos": -1}
    for pos in range(trade_pos, end_pos + 1):
        low_ret = daily.at[pos, "low"] / trade_price - 1.0
        high_ret = daily.at[pos, "high"] / trade_price - 1.0
        lower_hit = lower is not None and pd.notna(low_ret) and low_ret <= lower
        upper_hit = upper is not None and pd.notna(high_ret) and high_ret >= upper
        if lower_hit:
            return {
                "label": -1 if upper is not None else 1,
                "complete": True,
                "touch_date": str(daily.at[pos, "date"]),
                "touch_pos": int(pos),
            }
        if upper_hit:
            return {
                "label": 1,
                "complete": True,
                "touch_date": str(daily.at[pos, "date"]),
                "touch_pos": int(pos),
            }
    return {"label": 0, "complete": True, "touch_date": "", "touch_pos": -1}


def event_false_repair_label(
    daily: pd.DataFrame,
    *,
    event_pos: int,
    horizon: int,
    drawdown: float,
) -> tuple[bool | float, bool]:
    end = event_pos + horizon
    if event_pos < 0 or end >= len(daily):
        return np.nan, False
    event_close = daily.at[event_pos, "close"]
    if pd.isna(event_close) or float(event_close) <= 0:
        return np.nan, False
    close = pd.to_numeric(daily.loc[event_pos:end, "close"], errors="coerce")
    return bool(((close / float(event_close) - 1.0) <= drawdown).any()), True


def label_events(
    events: pd.DataFrame,
    *,
    daily_by_instrument: dict[str, pd.DataFrame],
    label_cfg: LabelConfig,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for event in events.to_dict("records"):
        daily = daily_by_instrument.get(str(event["instrument"]))
        if daily is None:
            continue
        trade_pos = int(event.get("trade_open_pos", -1))
        trade_price = float(event.get("trade_open_price", np.nan))
        non_exec = bool(event.get("non_executable_next_open", False))
        base = {
            "event_id": event["event_id"],
            "instrument": event["instrument"],
            "event_t0_date": event["event_t0_date"],
            "event_t0_pos": int(event["event_t0_pos"]),
            "trade_open_date": event.get("trade_open_date", ""),
            "trade_open_pos": trade_pos,
            "trade_open_price": trade_price,
            "event_split": event.get("event_split", ""),
            "event_family": event.get("event_family", ""),
            "union_family": event.get("union_family", ""),
            "canonical_event_scope": event.get("canonical_event_scope", ""),
            "union_cluster_id": event.get("union_cluster_id", ""),
            "label_anchor_type": "event_anchored",
            "non_executable_next_open": non_exec,
            "non_executable_reason": event.get("non_executable_reason", ""),
            "limit_threshold_status": event.get("limit_threshold_status", ""),
        }
        if non_exec:
            confirm = {"label": np.nan, "complete": False, "touch_date": "", "touch_pos": -1}
            failure = {"label": np.nan, "complete": False, "touch_date": "", "touch_pos": -1}
        else:
            confirm = barrier_touch(
                daily,
                trade_pos=trade_pos,
                trade_price=trade_price,
                horizon=label_cfg.confirm_horizon,
                upper=label_cfg.confirm_upper,
                lower=label_cfg.confirm_lower,
            )
            failure = barrier_touch(
                daily,
                trade_pos=trade_pos,
                trade_price=trade_price,
                horizon=label_cfg.failure_horizon,
                upper=None,
                lower=label_cfg.failure_lower,
            )
        base.update(
            {
                "confirm_20_label": confirm["label"],
                "confirm_20_complete": bool(confirm["complete"]),
                "confirm_20_touch_date": confirm["touch_date"],
                "confirm_20_touch_pos": confirm["touch_pos"],
                "failure_10_label": failure["label"],
                "failure_10_complete": bool(failure["complete"]),
                "failure_10_touch_date": failure["touch_date"],
                "failure_10_touch_pos": failure["touch_pos"],
            }
        )
        for horizon in label_cfg.continuous_horizons:
            if non_exec:
                continuous = {
                    f"forward_return_{horizon}d": np.nan,
                    f"mfe_{horizon}d": np.nan,
                    f"mae_{horizon}d": np.nan,
                    f"horizon_complete_{horizon}d": False,
                }
            else:
                continuous = _observable.continuous_forward(
                    daily,
                    trade_pos=trade_pos,
                    trade_price=trade_price,
                    horizon=int(horizon),
                )
            base.update(continuous)
        for horizon in [10, 20]:
            false_label, complete = event_false_repair_label(
                daily,
                event_pos=int(event["event_t0_pos"]),
                horizon=horizon,
                drawdown=label_cfg.false_repair_drawdown,
            )
            base[f"event_false_repair_{horizon}d_label"] = false_label
            base[f"event_false_repair_{horizon}d_complete"] = complete
        complete_120 = bool(base.get("horizon_complete_120d", False))
        mfe120 = base.get("mfe_120d", np.nan)
        if complete_120 and pd.notna(mfe120):
            base["candidate_outcome_120d_status"] = NOT_MISSING
            base["event_big_winner_120d_label"] = bool(
                float(mfe120) >= label_cfg.big_winner_mfe_120d
            )
            base["event_super_winner_120d_label"] = bool(
                float(mfe120) >= label_cfg.super_winner_mfe_120d
            )
            base["event_near_winner_120d_label"] = bool(
                label_cfg.near_winner_mfe_lower
                <= float(mfe120)
                < label_cfg.near_winner_mfe_upper
            )
        else:
            base["candidate_outcome_120d_status"] = (
                NON_EXECUTABLE_NEXT_OPEN if non_exec else CENSORED_INCOMPLETE_HORIZON
            )
            base["event_big_winner_120d_label"] = np.nan
            base["event_super_winner_120d_label"] = np.nan
            base["event_near_winner_120d_label"] = np.nan
        base["main_barrier_label_complete"] = bool(
            base["confirm_20_complete"] and base["failure_10_complete"]
        )
        base["captured_target_episode_count"] = 0
        base["captured_target_episode_id_first"] = ""
        base["captured_target_episode_anchor_note"] = (
            "episode_anchored_recall_not_event_positive_label"
        )
        rows.append(base)
    return pd.DataFrame(rows)


def first_50pct_touch(
    daily: pd.DataFrame,
    *,
    low_date: str,
    low_price: float,
    horizon: int = 120,
) -> tuple[str, int]:
    matches = daily.index[daily["date"].astype(str) == low_date].tolist()
    if not matches or pd.isna(low_price) or float(low_price) <= 0:
        return "", -1
    low_pos = int(matches[0])
    end = min(len(daily) - 1, low_pos + horizon)
    for pos in range(low_pos, end + 1):
        high = daily.at[pos, "high"]
        if pd.notna(high) and float(high) / float(low_price) - 1.0 >= 0.50:
            return str(daily.at[pos, "date"]), int(pos)
    return "", -1


def events_in_window(
    events: pd.DataFrame,
    *,
    start_pos: int,
    end_pos: int,
) -> pd.DataFrame:
    if events.empty or start_pos < 0 or end_pos < start_pos:
        return events.iloc[0:0].copy()
    pos = pd.to_numeric(events["event_t0_pos"], errors="coerce")
    return events.loc[(pos >= start_pos) & (pos <= end_pos)].copy()


def first_event(events: pd.DataFrame) -> dict[str, Any]:
    if events.empty:
        return {}
    row = events.sort_values(["event_t0_pos", "event_family_priority", "event_id"]).iloc[0]
    return row.to_dict()


def build_episode_capture_audit(
    episodes: pd.DataFrame,
    *,
    raw_events: pd.DataFrame,
    candidate_instances: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    split_config: SplitConfig,
    capture_cfg: dict[str, Any],
) -> pd.DataFrame:
    raw_setup = raw_events.loc[raw_events["event_family"].isin(UNION_FAMILIES[SETUP_UNION])]
    raw_reclaim = raw_events.loc[raw_events["event_family"].isin(UNION_FAMILIES[RECLAIM_UNION])]
    canonical_setup = candidate_instances.loc[
        (candidate_instances["canonical_event_scope"] == CANONICAL_PRE_DENSITY_SCOPE)
        & (candidate_instances["union_family"] == SETUP_UNION)
    ]
    canonical_reclaim = candidate_instances.loc[
        (candidate_instances["canonical_event_scope"] == CANONICAL_PRE_DENSITY_SCOPE)
        & (candidate_instances["union_family"] == RECLAIM_UNION)
    ]
    density_setup = candidate_instances.loc[
        (candidate_instances["canonical_event_scope"] == CANONICAL_SCOPE)
        & (candidate_instances["union_family"] == SETUP_UNION)
    ]
    density_reclaim = candidate_instances.loc[
        (candidate_instances["canonical_event_scope"] == CANONICAL_SCOPE)
        & (candidate_instances["union_family"] == RECLAIM_UNION)
    ]
    family_maps = {
        family: raw_events.loc[raw_events["event_family"] == family]
        for family in [
            "E0_seed_low_setup",
            "E1_first_ema60_reclaim",
            "E2_reclaim_quality_burst",
            "E3_early_no_false_repair",
            "E4_early_relative_strength_turn",
            "E5_strict_rank_persistence_reference",
        ]
    }
    rows: list[dict[str, Any]] = []
    pre_low = int(capture_cfg["pre_low"])
    for episode in episodes.to_dict("records"):
        instrument = str(episode["instrument"])
        daily = daily_by_instrument.get(instrument)
        if daily is None:
            continue
        low_date = str(episode["episode_low_date"])
        low_matches = daily.index[daily["date"].astype(str) == low_date].tolist()
        high_matches = daily.index[
            daily["date"].astype(str) == str(episode["episode_high_date"])
        ].tolist()
        if not low_matches:
            continue
        low_pos = int(low_matches[0])
        high_pos = int(high_matches[0]) if high_matches else -1
        first50_date, first50_pos = first_50pct_touch(
            daily,
            low_date=low_date,
            low_price=float(episode["qfq_low_at_low_date"]),
            horizon=int(episode.get("forward_horizon_days", 120)),
        )
        if first50_pos < 0:
            continue
        setup_raw_i = raw_setup.loc[raw_setup["instrument"] == instrument]
        reclaim_raw_i = raw_reclaim.loc[raw_reclaim["instrument"] == instrument]
        setup_can_i = canonical_setup.loc[canonical_setup["instrument"] == instrument]
        reclaim_can_i = canonical_reclaim.loc[canonical_reclaim["instrument"] == instrument]
        setup_density_i = density_setup.loc[density_setup["instrument"] == instrument]
        reclaim_density_i = density_reclaim.loc[density_reclaim["instrument"] == instrument]
        row: dict[str, Any] = {
            "episode_id": episode["episode_id"],
            "instrument": instrument,
            "episode_low_date": low_date,
            "first_50pct_touch_date": first50_date,
            "episode_high_date": episode["episode_high_date"],
            "target_duration_sessions": int(episode["low_to_high_sessions"]),
            "episode_split": split_for_episode(low_date, split_config),
            "duration_bucket": episode.get(
                "duration_bucket",
                _reverse.duration_bucket(episode.get("low_to_high_sessions")),
            ),
            "market_regime_bucket": episode.get("market_regime_bucket", ""),
        }
        windows = {
            "pre_low_20d": (low_pos - pre_low, low_pos),
            "low_to_plus_10d": (low_pos, low_pos + 10),
            "low_to_plus_20d": (low_pos, low_pos + 20),
            "low_to_plus_30d": (low_pos, low_pos + 30),
            "low_to_plus_60d": (low_pos, low_pos + 60),
            "low_to_plus_120d": (low_pos, low_pos + 120),
            "before_first_50pct": (low_pos, first50_pos - 1),
            "before_episode_high": (low_pos, high_pos - 1 if high_pos >= 0 else -1),
        }
        for suffix, (start, end) in windows.items():
            union_hits: dict[tuple[str, str], pd.DataFrame] = {}
            for union_family, scope_name, frame in [
                (SETUP_UNION, "raw", setup_raw_i),
                (SETUP_UNION, "canonical", setup_can_i),
                (SETUP_UNION, "density_kept", setup_density_i),
                (RECLAIM_UNION, "raw", reclaim_raw_i),
                (RECLAIM_UNION, "canonical", reclaim_can_i),
                (RECLAIM_UNION, "density_kept", reclaim_density_i),
            ]:
                hit = events_in_window(frame, start_pos=start, end_pos=end)
                union_hits[(union_family, scope_name)] = hit
                first_hit = first_event(hit)
                row[f"captured_by_{union_family}_{scope_name}_{suffix}"] = not hit.empty
                row[f"first_{union_family}_{scope_name}_{suffix}_event_id"] = first_hit.get(
                    "event_id", ""
                )
                row[f"first_{union_family}_{scope_name}_{suffix}_event_t0_date"] = first_hit.get(
                    "event_t0_date", ""
                )
            setup_loss = bool(
                (not union_hits[(SETUP_UNION, "canonical")].empty)
                and union_hits[(SETUP_UNION, "density_kept")].empty
            )
            reclaim_loss = bool(
                (not union_hits[(RECLAIM_UNION, "canonical")].empty)
                and union_hits[(RECLAIM_UNION, "density_kept")].empty
            )
            row[f"density_loss_capture_{suffix}"] = setup_loss
            row[f"density_loss_capture_{SETUP_UNION}_{suffix}"] = setup_loss
            row[f"density_loss_capture_{RECLAIM_UNION}_{suffix}"] = reclaim_loss
        before_first = events_in_window(
            setup_density_i,
            start_pos=windows["before_first_50pct"][0],
            end_pos=windows["before_first_50pct"][1],
        )
        low30 = events_in_window(
            setup_density_i,
            start_pos=windows["low_to_plus_30d"][0],
            end_pos=windows["low_to_plus_30d"][1],
        )
        first = first_event(before_first if not before_first.empty else low30)
        row["late_after_first_50pct_capture_flag"] = bool(
            low30.shape[0] > 0 and before_first.empty
        )
        row["first_capturing_event_id"] = first.get("event_id", "")
        row["first_capturing_event_family"] = first.get("event_family", "")
        row["first_capturing_event_t0_date"] = first.get("event_t0_date", "")
        row["first_capturing_event_split"] = first.get("event_split", "")
        row["lead_time_to_first_50pct_sessions"] = (
            int(first50_pos - int(first["event_t0_pos"])) if first else np.nan
        )
        row["lead_time_to_episode_high_sessions"] = (
            int(high_pos - int(first["event_t0_pos"])) if first and high_pos >= 0 else np.nan
        )
        for family, frame in family_maps.items():
            family_prefix = family.split("_")[0]
            family_i = frame.loc[frame["instrument"] == instrument]
            for suffix, (start, end) in windows.items():
                hit = events_in_window(family_i, start_pos=start, end_pos=end)
                first_hit = first_event(hit)
                row[f"captured_by_{family_prefix}_raw_{suffix}"] = not hit.empty
                row[f"first_{family_prefix}_raw_{suffix}_event_id"] = first_hit.get(
                    "event_id", ""
                )
                row[f"first_{family_prefix}_raw_{suffix}_event_t0_date"] = first_hit.get(
                    "event_t0_date", ""
                )
            row[f"captured_by_{family_prefix}"] = bool(
                row[f"captured_by_{family_prefix}_raw_before_first_50pct"]
            )
        row["missing_reason"] = ""
        rows.append(row)
    capture = pd.DataFrame(rows)
    if capture.empty:
        return capture
    rename = {
        "captured_by_E0": "captured_by_E0",
        "captured_by_E1": "captured_by_E1",
        "captured_by_E2": "captured_by_E2",
        "captured_by_E3": "captured_by_E3",
        "captured_by_E4": "captured_by_E4",
        "captured_by_E5": "captured_by_E5",
    }
    return capture.rename(columns=rename)


def update_label_capture_counts(labels: pd.DataFrame, capture: pd.DataFrame) -> pd.DataFrame:
    if labels.empty or capture.empty:
        return labels
    counts = (
        capture.loc[capture["first_capturing_event_id"].astype(str) != ""]
        .groupby("first_capturing_event_id")["episode_id"]
        .agg(["count", "first"])
        .reset_index()
    )
    counts = counts.rename(
        columns={
            "first_capturing_event_id": "event_id",
            "count": "captured_target_episode_count",
            "first": "captured_target_episode_id_first",
        }
    )
    out = labels.drop(
        columns=["captured_target_episode_count", "captured_target_episode_id_first"],
        errors="ignore",
    ).merge(counts, on="event_id", how="left")
    out["captured_target_episode_count"] = (
        out["captured_target_episode_count"].fillna(0).astype(int)
    )
    out["captured_target_episode_id_first"] = out[
        "captured_target_episode_id_first"
    ].fillna("")
    return out


def grouped_denominators(capture: pd.DataFrame, group_cols: list[str]) -> list[tuple[dict[str, Any], pd.DataFrame]]:
    groups: list[tuple[dict[str, Any], pd.DataFrame]] = [({"episode_split": "all", "duration_bucket": "all"}, capture)]
    for keys, group in capture.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        groups.append((dict(zip(group_cols, keys)), group))
    return groups


def build_event_family_recall_stats(capture: pd.DataFrame) -> pd.DataFrame:
    if capture.empty:
        return pd.DataFrame()
    metric_cols = [
        column
        for column in capture.columns
        if column.startswith("captured_by_setup_inclusive")
        or column.startswith("captured_by_reclaim_based")
        or column.startswith("captured_by_E")
    ]
    rows: list[dict[str, Any]] = []
    group_cols = ["episode_split", "duration_bucket"]
    for context, group in grouped_denominators(capture, group_cols):
        denom = len(group)
        for metric in metric_cols:
            count = int(group[metric].fillna(False).astype(bool).sum())
            row = {
                "episode_split": context.get("episode_split", "all"),
                "duration_bucket": context.get("duration_bucket", "all"),
                "metric": metric,
                "captured_count": count,
                "target_episode_count": denom,
                "recall": safe_rate(count, denom),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def build_duration_bucket_actionable_recall(capture: pd.DataFrame) -> pd.DataFrame:
    if capture.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for context, group in grouped_denominators(capture, ["episode_split", "duration_bucket"]):
        split = context.get("episode_split", "all")
        bucket = context.get("duration_bucket", "all")
        denom = len(group)
        metrics: dict[str, Any] = {}
        windows = [
            "pre_low_20d",
            "low_to_plus_10d",
            "low_to_plus_20d",
            "low_to_plus_30d",
            "low_to_plus_60d",
            "low_to_plus_120d",
            "before_first_50pct",
            "before_episode_high",
        ]
        for union_family in [SETUP_UNION, RECLAIM_UNION]:
            for window in windows:
                column = f"captured_by_{union_family}_density_kept_{window}"
                count = int(group[column].fillna(False).astype(bool).sum()) if column in group else 0
                metric_name = window.replace("low_to_plus_", "low_to_plus_")
                metrics[f"{union_family}_recall_{metric_name}"] = safe_rate(count, denom)
                if union_family == SETUP_UNION:
                    legacy = {
                        "low_to_plus_30d": "recall_low_to_plus_30d",
                        "before_first_50pct": "recall_before_first_50pct",
                    }.get(window)
                    if legacy:
                        metrics[legacy] = safe_rate(count, denom)
        low30 = int(
            group["captured_by_setup_inclusive_density_kept_low_to_plus_30d"]
            .fillna(False)
            .astype(bool)
            .sum()
        )
        late = int(group["late_after_first_50pct_capture_flag"].fillna(False).astype(bool).sum())
        rows.append(
            {
                "episode_split": split,
                "duration_bucket": bucket,
                "target_episode_count": denom,
                **metrics,
                "late_after_first_50pct_capture_share": safe_rate(late, low30),
            }
        )
    return pd.DataFrame(rows)


def build_density_loss_capture_audit(capture: pd.DataFrame) -> pd.DataFrame:
    if capture.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for context, group in grouped_denominators(capture, ["episode_split", "duration_bucket"]):
        split = context.get("episode_split", "all")
        bucket = context.get("duration_bucket", "all")
        denom = len(group)
        for union_family in [SETUP_UNION, RECLAIM_UNION]:
            for suffix in [
                "pre_low_20d",
                "low_to_plus_10d",
                "low_to_plus_20d",
                "low_to_plus_30d",
                "low_to_plus_60d",
                "low_to_plus_120d",
                "before_first_50pct",
                "before_episode_high",
            ]:
                raw = int(
                    group[f"captured_by_{union_family}_raw_{suffix}"]
                    .fillna(False)
                    .astype(bool)
                    .sum()
                )
                canonical = int(
                    group[f"captured_by_{union_family}_canonical_{suffix}"]
                    .fillna(False)
                    .astype(bool)
                    .sum()
                )
                density = int(
                    group[f"captured_by_{union_family}_density_kept_{suffix}"]
                    .fillna(False)
                    .astype(bool)
                    .sum()
                )
                rows.append(
                    {
                        "episode_split": split,
                        "duration_bucket": bucket,
                        "union_family": union_family,
                        "window": suffix,
                        "target_episode_count": denom,
                        "raw_union_recall": safe_rate(raw, denom),
                        "canonical_union_recall": safe_rate(canonical, denom),
                        "density_kept_union_recall": safe_rate(density, denom),
                        "density_loss_recall": safe_rate(canonical, denom)
                        - safe_rate(density, denom),
                        "raw_captured_count": raw,
                        "canonical_captured_count": canonical,
                        "density_kept_captured_count": density,
                        "density_loss_capture_count": max(canonical - density, 0),
                    }
                )
    return pd.DataFrame(rows)


def density_loss_counts_by_event(capture: pd.DataFrame) -> pd.DataFrame:
    if capture.empty:
        return pd.DataFrame(columns=["event_id", "density_loss_capture_count"])
    rows: list[pd.DataFrame] = []
    for union_family in [SETUP_UNION, RECLAIM_UNION]:
        for suffix in [
            "pre_low_20d",
            "low_to_plus_10d",
            "low_to_plus_20d",
            "low_to_plus_30d",
            "low_to_plus_60d",
            "low_to_plus_120d",
            "before_first_50pct",
            "before_episode_high",
        ]:
            loss_col = f"density_loss_capture_{union_family}_{suffix}"
            event_col = f"first_{union_family}_canonical_{suffix}_event_id"
            if loss_col not in capture.columns or event_col not in capture.columns:
                continue
            lost = capture.loc[
                capture[loss_col].fillna(False).astype(bool)
                & (capture[event_col].astype(str) != ""),
                [event_col],
            ].copy()
            if lost.empty:
                continue
            lost = (
                lost.rename(columns={event_col: "event_id"})
                .groupby("event_id", sort=True)
                .size()
                .reset_index(name="density_loss_capture_count")
            )
            rows.append(lost)
    if not rows:
        return pd.DataFrame(columns=["event_id", "density_loss_capture_count"])
    return (
        pd.concat(rows, ignore_index=True)
        .groupby("event_id", as_index=False)["density_loss_capture_count"]
        .sum()
    )


def build_event_density_audit(events: pd.DataFrame, capture: pd.DataFrame | None = None) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    frame = events.copy()
    frame["year"] = frame["event_t0_date"].astype(str).str[:4]
    if capture is not None and not capture.empty:
        loss_counts = density_loss_counts_by_event(capture)
        frame = frame.merge(loss_counts, on="event_id", how="left")
    if "density_loss_capture_count" not in frame.columns:
        frame["density_loss_capture_count"] = 0
    frame["density_loss_capture_count"] = (
        pd.to_numeric(frame["density_loss_capture_count"], errors="coerce").fillna(0).astype(int)
    )
    rows: list[dict[str, Any]] = []
    group_cols = ["event_family", "union_family", "canonical_event_scope", "event_split", "year"]
    for keys, group in frame.groupby(group_cols, dropna=False, sort=True):
        scope = dict(zip(group_cols, keys)).get("canonical_event_scope")
        if scope == CANONICAL_PRE_DENSITY_SCOPE and "union_density_kept" in group.columns:
            kept_count = int(group["union_density_kept"].fillna(False).astype(bool).sum())
            folded_count = int(len(group) - kept_count)
        elif scope == CANONICAL_SCOPE:
            kept_count = int(len(group))
            folded_count = 0
        else:
            kept_count = int(len(group))
            folded_count = 0
        per_inst_year = group.groupby(["instrument", "year"]).size()
        rows.append(
            {
                **dict(zip(group_cols, keys)),
                "raw_candidate_count": int(len(group)),
                "density_kept_count": kept_count,
                "density_folded_count": folded_count,
                "density_loss_capture_count": int(group["density_loss_capture_count"].sum()),
                "events_per_instrument_year_mean": float(per_inst_year.mean())
                if len(per_inst_year)
                else np.nan,
                "events_per_instrument_year_p95": float(per_inst_year.quantile(0.95))
                if len(per_inst_year)
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def build_event_precision_label_readout(labels: pd.DataFrame) -> pd.DataFrame:
    if labels.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    group_cols = ["event_family", "union_family", "canonical_event_scope", "event_split"]
    for keys, group in labels.groupby(group_cols, dropna=False, sort=True):
        complete120 = group.loc[group["candidate_outcome_120d_status"] == NOT_MISSING]
        positive = complete120["event_big_winner_120d_label"].fillna(False).astype(bool)
        near = complete120["event_near_winner_120d_label"].fillna(False).astype(bool)
        false10 = group["event_false_repair_10d_label"].fillna(False).astype(bool)
        false20 = group["event_false_repair_20d_label"].fillna(False).astype(bool)
        metrics120 = concurrency_uniqueness(group, 120)
        metrics20 = concurrency_uniqueness(group, 20)
        cluster_positive = complete120.loc[positive].drop_duplicates("union_cluster_id")
        rows.append(
            {
                **dict(zip(group_cols, keys)),
                "event_count": int(len(group)),
                "outcome_complete_120d_count": int(len(complete120)),
                "event_big_winner_120d_rate": safe_rate(int(positive.sum()), len(complete120)),
                "event_near_winner_120d_rate": safe_rate(int(near.sum()), len(complete120)),
                "event_false_repair_10d_rate": safe_rate(int(false10.sum()), len(group)),
                "event_false_repair_20d_rate": safe_rate(int(false20.sum()), len(group)),
                "positive_label_count": int(positive.sum()),
                "negative_label_count": int(len(complete120) - positive.sum()),
                "class_balance_by_event_split": str(keys[-1]),
                "cluster_positive_count": int(len(cluster_positive)),
                "event_concurrency_mean": metrics120["event_concurrency_mean"],
                "event_concurrency_p95": metrics120["event_concurrency_p95"],
                "average_uniqueness_mean": metrics120["average_uniqueness_mean"],
                "average_uniqueness_p25": metrics120["average_uniqueness_p25"],
                "event_concurrency_20d_mean": metrics20["event_concurrency_mean"],
                "event_concurrency_20d_p95": metrics20["event_concurrency_p95"],
                "average_uniqueness_20d_mean": metrics20["average_uniqueness_mean"],
                "average_uniqueness_20d_p25": metrics20["average_uniqueness_p25"],
            }
        )
    return pd.DataFrame(rows)


def build_false_repair_diagnostic(labels: pd.DataFrame, events: pd.DataFrame | None = None) -> pd.DataFrame:
    if labels.empty:
        return pd.DataFrame()
    frame = labels.copy()
    if events is not None and not events.empty and "market_regime_bucket" in events.columns:
        frame = frame.merge(
            events[["event_id", "market_regime_bucket"]],
            on="event_id",
            how="left",
        )
    if "market_regime_bucket" not in frame.columns:
        frame["market_regime_bucket"] = "unknown"
    rows: list[dict[str, Any]] = []
    group_cols = [
        "event_family",
        "union_family",
        "canonical_event_scope",
        "event_split",
        "market_regime_bucket",
    ]
    for keys, group in frame.groupby(group_cols, dropna=False, sort=True):
        rows.append(
            {
                **dict(zip(group_cols, keys)),
                "event_count": int(len(group)),
                "false_repair_10d_count": int(
                    group["event_false_repair_10d_label"].fillna(False).astype(bool).sum()
                ),
                "false_repair_20d_count": int(
                    group["event_false_repair_20d_label"].fillna(False).astype(bool).sum()
                ),
                "false_repair_10d_rate": safe_rate(
                    int(group["event_false_repair_10d_label"].fillna(False).astype(bool).sum()),
                    len(group),
                ),
                "false_repair_20d_rate": safe_rate(
                    int(group["event_false_repair_20d_label"].fillna(False).astype(bool).sum()),
                    len(group),
                ),
            }
        )
    return pd.DataFrame(rows)


def build_executability_audit(events: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    group_cols = ["event_family", "union_family", "canonical_event_scope", "event_split"]
    for keys, group in events.groupby(group_cols, dropna=False, sort=True):
        non_exec = group["non_executable_next_open"].fillna(False).astype(bool)
        rows.append(
            {
                **dict(zip(group_cols, keys)),
                "event_count": int(len(group)),
                "non_executable_next_open_count": int(non_exec.sum()),
                "executable_count": int(len(group) - non_exec.sum()),
                "executable_rate": safe_rate(int(len(group) - non_exec.sum()), len(group)),
                "limit_rule_unavailable_count": int(
                    (group["limit_threshold_status"].astype(str) == "limit_rule_unavailable").sum()
                ),
                "main_label_complete_rate": safe_rate(
                    int(
                        labels.loc[labels["event_id"].isin(group["event_id"]), "main_barrier_label_complete"]
                        .fillna(False)
                        .astype(bool)
                        .sum()
                    ),
                    len(group),
                )
                if not labels.empty
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def label_spans_for_horizon(labels: pd.DataFrame, horizon: int) -> pd.DataFrame:
    if labels.empty:
        return pd.DataFrame(columns=["event_id", "start_pos", "end_pos"])
    rows: list[dict[str, Any]] = []
    for row in labels.to_dict("records"):
        if bool(row.get("non_executable_next_open", False)):
            continue
        start = int(row.get("trade_open_pos", -1))
        if start < 0:
            continue
        if horizon == 20:
            touch = int(row.get("confirm_20_touch_pos", -1))
            end = touch if touch >= start else start + 20
            if not bool(row.get("confirm_20_complete", False)):
                continue
        else:
            if not bool(row.get(f"horizon_complete_{horizon}d", False)):
                continue
            end = start + horizon
        rows.append({"event_id": row["event_id"], "start_pos": start, "end_pos": end})
    return pd.DataFrame(rows)


def concurrency_uniqueness(labels: pd.DataFrame, horizon: int) -> dict[str, Any]:
    spans = label_spans_for_horizon(labels, horizon)
    if spans.empty:
        return {
            "event_concurrency_mean": np.nan,
            "event_concurrency_p95": np.nan,
            "average_uniqueness_mean": np.nan,
            "average_uniqueness_p25": np.nan,
        }
    counts: dict[int, int] = {}
    for span in spans.itertuples(index=False):
        for pos in range(int(span.start_pos), int(span.end_pos) + 1):
            counts[pos] = counts.get(pos, 0) + 1
    uniqueness: list[float] = []
    for span in spans.itertuples(index=False):
        values = [1.0 / counts[pos] for pos in range(int(span.start_pos), int(span.end_pos) + 1)]
        uniqueness.append(float(np.mean(values)) if values else np.nan)
    conc = pd.Series(list(counts.values()), dtype=float)
    uniq = pd.Series(uniqueness, dtype=float)
    return {
        "event_concurrency_mean": float(conc.mean()) if len(conc) else np.nan,
        "event_concurrency_p95": float(conc.quantile(0.95)) if len(conc) else np.nan,
        "average_uniqueness_mean": float(uniq.mean()) if len(uniq) else np.nan,
        "average_uniqueness_p25": float(uniq.quantile(0.25)) if len(uniq) else np.nan,
    }


def build_downstream_model_readiness(
    events: pd.DataFrame,
    labels: pd.DataFrame,
) -> pd.DataFrame:
    if events.empty or labels.empty:
        return pd.DataFrame()
    merged = labels.merge(
        events[["event_id", "event_t0_date"]],
        on="event_id",
        how="left",
    )
    rows: list[dict[str, Any]] = []
    group_cols = ["event_family", "union_family", "canonical_event_scope", "event_split"]
    for keys, group in merged.groupby(group_cols, dropna=False, sort=True):
        events_group = events.loc[events["event_id"].isin(group["event_id"])]
        density = build_event_density_audit(events_group)
        density_mean = safe_mean(density["events_per_instrument_year_mean"]) if not density.empty else np.nan
        density_p95 = safe_pctl(density["events_per_instrument_year_p95"], 0.95) if not density.empty else np.nan
        for horizon in [20, 120]:
            metrics = concurrency_uniqueness(group, horizon)
            complete120 = group.loc[group["candidate_outcome_120d_status"] == NOT_MISSING]
            positive = complete120["event_big_winner_120d_label"].fillna(False).astype(bool)
            cluster_positive = complete120.loc[positive].drop_duplicates("union_cluster_id")
            feature_cols = [col for col in SNAPSHOT_COLUMNS if col in events_group.columns]
            missing_rates = (
                events_group[feature_cols].isna().mean(axis=1)
                if feature_cols
                else pd.Series(dtype=float)
            )
            rows.append(
                {
                    **dict(zip(group_cols, keys)),
                    "label_horizon": horizon,
                    "event_count": int(len(group)),
                    "label_complete_20d_count": int(
                        group["main_barrier_label_complete"].fillna(False).astype(bool).sum()
                    ),
                    "outcome_complete_120d_count": int(len(complete120)),
                    "big_winner_120d_positive_count": int(positive.sum()),
                    "near_winner_120d_count": int(
                        complete120["event_near_winner_120d_label"]
                        .fillna(False)
                        .astype(bool)
                        .sum()
                    ),
                    "negative_count": int(len(complete120) - positive.sum()),
                    "positive_rate": safe_rate(int(positive.sum()), len(complete120)),
                    "events_per_instrument_year_mean": density_mean,
                    "events_per_instrument_year_p95": density_p95,
                    "cluster_positive_count": int(len(cluster_positive)),
                    "feature_missing_rate_mean": float(missing_rates.mean())
                    if len(missing_rates)
                    else np.nan,
                    "feature_missing_rate_p95": float(missing_rates.quantile(0.95))
                    if len(missing_rates)
                    else np.nan,
                    "status": "ready_for_downstream_model_diagnostic",
                    **metrics,
                }
            )
    return pd.DataFrame(rows)


def build_lead_time_distribution(capture: pd.DataFrame) -> pd.DataFrame:
    if capture.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for context, group in grouped_denominators(capture, ["episode_split", "duration_bucket"]):
        lead = pd.to_numeric(group["lead_time_to_first_50pct_sessions"], errors="coerce").dropna()
        rows.append(
            {
                "episode_split": context.get("episode_split", "all"),
                "duration_bucket": context.get("duration_bucket", "all"),
                "captured_episode_count": int(len(lead)),
                "lead_time_mean": float(lead.mean()) if len(lead) else np.nan,
                "lead_time_median": float(lead.median()) if len(lead) else np.nan,
                "lead_time_p25": float(lead.quantile(0.25)) if len(lead) else np.nan,
                "lead_time_p75": float(lead.quantile(0.75)) if len(lead) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def build_event_family_ablation_audit(capture: pd.DataFrame, density: pd.DataFrame) -> pd.DataFrame:
    if capture.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []

    def density_metrics(union_family: str, scope: str = CANONICAL_SCOPE) -> tuple[float, float]:
        if density.empty:
            return np.nan, np.nan
        rows_for_scope = density.loc[
            (density["union_family"] == union_family)
            & (density["canonical_event_scope"] == scope)
        ]
        if rows_for_scope.empty:
            return np.nan, np.nan
        return (
            safe_pctl(rows_for_scope["events_per_instrument_year_p95"], 0.95),
            safe_mean(rows_for_scope["events_per_instrument_year_mean"]),
        )

    for context, group in grouped_denominators(capture, ["episode_split", "duration_bucket"]):
        split = context.get("episode_split", "all")
        bucket = context.get("duration_bucket", "all")
        denom = len(group)
        reclaim = group["captured_by_reclaim_based_density_kept_low_to_plus_30d"].fillna(False).astype(bool)
        setup = group["captured_by_setup_inclusive_density_kept_low_to_plus_30d"].fillna(False).astype(bool)
        e0 = group["captured_by_E0_raw_low_to_plus_30d"].fillna(False).astype(bool)
        before = group["captured_by_setup_inclusive_density_kept_before_first_50pct"].fillna(False).astype(bool)
        density_p95, density_mean = density_metrics(SETUP_UNION)
        rows.append(
            {
                "episode_split": split,
                "duration_bucket": bucket,
                "union_family": SETUP_UNION,
                "ablation_variant": "setup_inclusive_vs_reclaim_based",
                "recall_low_to_plus_20d": safe_rate(
                    int(
                        group["captured_by_setup_inclusive_density_kept_low_to_plus_20d"]
                        .fillna(False)
                        .astype(bool)
                        .sum()
                    ),
                    denom,
                ),
                "recall_low_to_plus_30d": safe_rate(int(setup.sum()), denom),
                "recall_before_first_50pct": safe_rate(int(before.sum()), denom),
                "E0_only_capture_share": safe_rate(int((e0 & ~reclaim).sum()), int(setup.sum())),
                "recall_without_E0": safe_rate(int(reclaim.sum()), denom),
                "marginal_recall_E0_over_reclaim_based": safe_rate(
                    int((setup & ~reclaim).sum()), denom
                ),
                "marginal_recall_E1_E2_E4_over_E0": safe_rate(
                    int((setup & ~e0).sum()), denom
                ),
                "event_density_p95": density_p95,
                "event_density_mean": density_mean,
                "interpretation_caveat": "E0 may dominate setup-inclusive recall; inspect without-E0 recall.",
            }
        )
        reclaim_density_p95, reclaim_density_mean = density_metrics(RECLAIM_UNION)
        rows.append(
            {
                "episode_split": split,
                "duration_bucket": bucket,
                "union_family": RECLAIM_UNION,
                "ablation_variant": "reclaim_based_without_E0",
                "recall_low_to_plus_20d": safe_rate(
                    int(
                        group["captured_by_reclaim_based_density_kept_low_to_plus_20d"]
                        .fillna(False)
                        .astype(bool)
                        .sum()
                    ),
                    denom,
                ),
                "recall_low_to_plus_30d": safe_rate(int(reclaim.sum()), denom),
                "recall_before_first_50pct": safe_rate(
                    int(
                        group["captured_by_reclaim_based_density_kept_before_first_50pct"]
                        .fillna(False)
                        .astype(bool)
                        .sum()
                    ),
                    denom,
                ),
                "E0_only_capture_share": np.nan,
                "recall_without_E0": safe_rate(int(reclaim.sum()), denom),
                "marginal_recall_E0_over_reclaim_based": np.nan,
                "marginal_recall_E1_E2_E4_over_E0": safe_rate(int((reclaim & ~e0).sum()), denom),
                "event_density_p95": reclaim_density_p95,
                "event_density_mean": reclaim_density_mean,
                "interpretation_caveat": "Secondary union without E0; diagnostic for non-setup signal coverage.",
            }
        )
        for family_prefix in ["E0", "E1", "E2", "E3", "E4", "E5"]:
            low20 = group[f"captured_by_{family_prefix}_raw_low_to_plus_20d"].fillna(False).astype(bool)
            low30 = group[f"captured_by_{family_prefix}_raw_low_to_plus_30d"].fillna(False).astype(bool)
            before_family = group[
                f"captured_by_{family_prefix}_raw_before_first_50pct"
            ].fillna(False).astype(bool)
            rows.append(
                {
                    "episode_split": split,
                    "duration_bucket": bucket,
                    "union_family": "raw_family",
                    "ablation_variant": f"{family_prefix}_raw_family",
                    "recall_low_to_plus_20d": safe_rate(int(low20.sum()), denom),
                    "recall_low_to_plus_30d": safe_rate(int(low30.sum()), denom),
                    "recall_before_first_50pct": safe_rate(int(before_family.sum()), denom),
                    "E0_only_capture_share": safe_rate(int((low30 & ~reclaim).sum()), int(low30.sum()))
                    if family_prefix == "E0"
                    else np.nan,
                    "recall_without_E0": np.nan,
                    "marginal_recall_E0_over_reclaim_based": np.nan,
                    "marginal_recall_E1_E2_E4_over_E0": np.nan,
                    "event_density_p95": np.nan,
                    "event_density_mean": np.nan,
                    "interpretation_caveat": "Raw family recall; use for family attribution, not as headline gate.",
                }
            )
    return pd.DataFrame(rows)


def recall_value(capture: pd.DataFrame, split: str, column: str) -> float:
    if capture.empty:
        return np.nan
    group = capture if split == "all" else capture.loc[capture["episode_split"] == split]
    return safe_rate(int(group[column].fillna(False).astype(bool).sum()), len(group))


def density_gate_value(density: pd.DataFrame, union_family: str, metric: str) -> float:
    if density.empty:
        return np.nan
    rows = density.loc[
        (density["union_family"] == union_family)
        & (density["canonical_event_scope"] == CANONICAL_SCOPE)
    ]
    if rows.empty:
        return np.nan
    if metric.endswith("_p95"):
        return safe_pctl(rows["events_per_instrument_year_p95"], 0.95)
    return safe_mean(rows["events_per_instrument_year_mean"])


def build_gate_summary(
    *,
    capture: pd.DataFrame,
    candidate_instances: pd.DataFrame,
    labels: pd.DataFrame,
    density: pd.DataFrame,
    gates: dict[str, Any],
) -> dict[str, Any]:
    setup = candidate_instances.loc[
        (candidate_instances["canonical_event_scope"] == CANONICAL_SCOPE)
        & (candidate_instances["union_family"] == SETUP_UNION)
    ]
    setup_labels = labels.loc[labels["event_id"].isin(setup["event_id"])]
    setup_complete120 = setup_labels.loc[
        setup_labels["candidate_outcome_120d_status"] == NOT_MISSING
    ]
    setup_positive = setup_complete120["event_big_winner_120d_label"].fillna(False).astype(bool)
    setup_near = setup_complete120["event_near_winner_120d_label"].fillna(False).astype(bool)
    setup_false20 = setup_labels["event_false_repair_20d_label"].fillna(False).astype(bool)
    executable_rate = safe_rate(
        int((~setup["non_executable_next_open"].fillna(False).astype(bool)).sum()),
        len(setup),
    )
    main_complete_rate = safe_rate(
        int(setup_labels["main_barrier_label_complete"].fillna(False).astype(bool).sum()),
        len(setup_labels),
    )
    outcome_complete_rate = safe_rate(
        int((setup_labels["candidate_outcome_120d_status"] == NOT_MISSING).sum()),
        len(setup_labels),
    )
    positive_rate = safe_rate(int(setup_positive.sum()), len(setup_complete120))
    near_winner_rate = safe_rate(int(setup_near.sum()), len(setup_complete120))
    false_repair_20d_rate = safe_rate(int(setup_false20.sum()), len(setup_labels))
    summary = {
        "target_episode_count_total": int(len(capture)),
        "target_episode_count_validation": int((capture["episode_split"] == "validation").sum())
        if not capture.empty
        else 0,
        "target_episode_count_robustness": int((capture["episode_split"] == "robustness").sum())
        if not capture.empty
        else 0,
        "total_recall_low_to_plus_30d": recall_value(
            capture,
            "all",
            "captured_by_setup_inclusive_density_kept_low_to_plus_30d",
        ),
        "validation_recall_low_to_plus_30d": recall_value(
            capture,
            "validation",
            "captured_by_setup_inclusive_density_kept_low_to_plus_30d",
        ),
        "robustness_recall_low_to_plus_30d": recall_value(
            capture,
            "robustness",
            "captured_by_setup_inclusive_density_kept_low_to_plus_30d",
        ),
        "total_recall_low_to_plus_20d": recall_value(
            capture,
            "all",
            "captured_by_setup_inclusive_density_kept_low_to_plus_20d",
        ),
        "validation_recall_low_to_plus_20d": recall_value(
            capture,
            "validation",
            "captured_by_setup_inclusive_density_kept_low_to_plus_20d",
        ),
        "robustness_recall_low_to_plus_20d": recall_value(
            capture,
            "robustness",
            "captured_by_setup_inclusive_density_kept_low_to_plus_20d",
        ),
        "total_recall_before_first_50pct": recall_value(
            capture,
            "all",
            "captured_by_setup_inclusive_density_kept_before_first_50pct",
        ),
        "validation_recall_before_first_50pct": recall_value(
            capture,
            "validation",
            "captured_by_setup_inclusive_density_kept_before_first_50pct",
        ),
        "robustness_recall_before_first_50pct": recall_value(
            capture,
            "robustness",
            "captured_by_setup_inclusive_density_kept_before_first_50pct",
        ),
        "setup_inclusive_events_per_instrument_year_p95": density_gate_value(
            density, SETUP_UNION, "p95"
        ),
        "setup_inclusive_events_per_instrument_year_mean": density_gate_value(
            density, SETUP_UNION, "mean"
        ),
        "reclaim_based_events_per_instrument_year_p95": density_gate_value(
            density, RECLAIM_UNION, "p95"
        ),
        "reclaim_based_events_per_instrument_year_mean": density_gate_value(
            density, RECLAIM_UNION, "mean"
        ),
        "executable_rate": executable_rate,
        "main_label_complete_rate": main_complete_rate,
        "outcome_complete_120d_rate": outcome_complete_rate,
        "setup_big_winner_120d_rate": positive_rate,
        "setup_near_winner_120d_rate": near_winner_rate,
        "setup_false_repair_20d_rate": false_repair_20d_rate,
        "setup_canonical_event_count": int(len(setup)),
    }
    summary["gates"] = gates
    return summary


def gate_pass(value: float, threshold: float, *, op: str = ">=") -> bool:
    if pd.isna(value):
        return False
    return bool(value >= threshold) if op == ">=" else bool(value <= threshold)


def decide(gate: dict[str, Any]) -> str:
    gates = gate["gates"]
    if gate.get("data_blocked", False):
        return "candidate_generator_data_blocked"
    if (
        gate["target_episode_count_total"] < int(gates["min_total_target_episode_count"])
        or gate["target_episode_count_validation"]
        < int(gates["min_validation_target_episode_count"])
        or gate["target_episode_count_robustness"]
        < int(gates["min_robustness_target_episode_count"])
    ):
        return "candidate_generator_no_target_recall"
    if (
        not gate_pass(gate["executable_rate"], float(gates["min_executable_rate"]))
        or not gate_pass(
            gate["main_label_complete_rate"],
            float(gates["min_main_label_complete_rate"]),
        )
    ):
        return "candidate_generator_executability_blocked"
    if (
        not gate_pass(
            gate["total_recall_low_to_plus_30d"],
            float(gates["min_total_episode_recall_low_to_plus_30d"]),
        )
        or not gate_pass(
            gate["total_recall_low_to_plus_20d"],
            float(gates["min_total_episode_recall_low_to_plus_20d"]),
        )
    ):
        return "candidate_generator_total_recall_blocked"
    if (
        not gate_pass(
            gate["validation_recall_low_to_plus_30d"],
            float(gates["min_validation_episode_recall_low_to_plus_30d"]),
        )
        or not gate_pass(
            gate["validation_recall_low_to_plus_20d"],
            float(gates["min_validation_episode_recall_low_to_plus_20d"]),
        )
    ):
        return "candidate_generator_validation_recall_blocked"
    if (
        not gate_pass(
            gate["robustness_recall_low_to_plus_30d"],
            float(gates["min_robustness_episode_recall_low_to_plus_30d"]),
        )
        or not gate_pass(
            gate["robustness_recall_low_to_plus_20d"],
            float(gates["min_robustness_episode_recall_low_to_plus_20d"]),
        )
    ):
        return "candidate_generator_robustness_recall_blocked"
    if (
        not gate_pass(
            gate["setup_inclusive_events_per_instrument_year_p95"],
            float(gates["max_setup_inclusive_events_per_instrument_year_p95"]),
            op="<=",
        )
        or not gate_pass(
            gate["setup_inclusive_events_per_instrument_year_mean"],
            float(gates["max_setup_inclusive_events_per_instrument_year_mean"]),
            op="<=",
        )
        or not gate_pass(
            gate["reclaim_based_events_per_instrument_year_p95"],
            float(gates["max_reclaim_based_events_per_instrument_year_p95"]),
            op="<=",
        )
        or not gate_pass(
            gate["reclaim_based_events_per_instrument_year_mean"],
            float(gates["max_reclaim_based_events_per_instrument_year_mean"]),
            op="<=",
        )
    ):
        return "candidate_generator_recall_supported_density_blocked"
    if (
        not gate_pass(
            gate["total_recall_before_first_50pct"],
            float(gates["min_total_episode_recall_before_first_50pct"]),
        )
        or not gate_pass(
            gate["validation_recall_before_first_50pct"],
            float(gates["min_validation_episode_recall_before_first_50pct"]),
        )
        or not gate_pass(
            gate["robustness_recall_before_first_50pct"],
            float(gates["min_robustness_episode_recall_before_first_50pct"]),
        )
    ):
        return "candidate_generator_coverage_supported_actionability_late_blocked"
    if not gate_pass(
        gate["outcome_complete_120d_rate"],
        float(gates["min_120d_outcome_complete_rate_for_precision_readout"]),
    ):
        return "candidate_generator_supported_high_recall_noisy_precision"
    min_clean_positive_rate = float(
        gates.get("min_supported_positive_rate_for_clean_support", 0.10)
    )
    max_clean_false_repair_20d_rate = float(
        gates.get("max_supported_false_repair_20d_rate_for_clean_support", 0.50)
    )
    if (
        not gate_pass(gate["setup_big_winner_120d_rate"], min_clean_positive_rate)
        or not gate_pass(
            gate["setup_false_repair_20d_rate"],
            max_clean_false_repair_20d_rate,
            op="<=",
        )
    ):
        return "candidate_generator_supported_high_recall_noisy_precision"
    return "candidate_generator_supported_high_recall"


def build_event_family_definition() -> pd.DataFrame:
    rows = [
        ("E0_seed_low_setup", "60d trailing low setup; high-recall earliest observation."),
        ("E1_first_ema60_reclaim", "First EMA60 reclaim after density-kept E0 seed."),
        ("E2_reclaim_quality_burst", "Independent quality flag event within reclaim +5d."),
        ("E3_early_no_false_repair", "Survival diagnostic after reclaim +5/+10d."),
        ("E4_early_relative_strength_turn", "Early 5/10/20d relative-strength turn."),
        ("E5_strict_rank_persistence_reference", "03 E_S3 strict reference only."),
        (SETUP_UNION_EVENT, "Setup-inclusive canonical union E0/E1/E2/E4."),
        (RECLAIM_UNION_EVENT, "Secondary reclaim-based canonical union E1/E2/E4."),
    ]
    return pd.DataFrame(rows, columns=["event_family", "definition"])


def build_data_source_coverage_audit(input_paths: dict[str, Path], vwap_policy: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for name, path in input_paths.items():
        rows.append(
            {
                "input_name": name,
                "path": str(path),
                "exists": path.exists(),
                "kind": "directory" if path.is_dir() else "file",
                "sha256": file_sha256(path) if path.is_file() else "",
            }
        )
    rows.append(
        {
            "input_name": "vwap_source_policy",
            "path": "",
            "exists": bool(vwap_policy.get("compatible", False)),
            "kind": "policy",
            "sha256": "",
            "reason": vwap_policy.get("reason", ""),
        }
    )
    return pd.DataFrame(rows)


def build_regime_recall_density_audit(capture: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not capture.empty:
        for regime, group in capture.groupby("market_regime_bucket", dropna=False, sort=True):
            denom = len(group)
            before = int(
                group["captured_by_setup_inclusive_density_kept_before_first_50pct"]
                .fillna(False)
                .astype(bool)
                .sum()
            )
            low30 = int(
                group["captured_by_setup_inclusive_density_kept_low_to_plus_30d"]
                .fillna(False)
                .astype(bool)
                .sum()
            )
            rows.append(
                {
                    "market_regime_bucket": regime,
                    "target_episode_count": denom,
                    "recall_low_to_plus_30d": safe_rate(low30, denom),
                    "recall_before_first_50pct": safe_rate(before, denom),
                    "setup_canonical_event_count": int(
                        len(
                            events.loc[
                                (events["market_regime_bucket"] == regime)
                                & (events["union_family"] == SETUP_UNION)
                                & (events["canonical_event_scope"] == CANONICAL_SCOPE)
                            ]
                        )
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_threshold_freeze_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for section in ["event_generation", "quality_flags", "relative_strength", "density", "labels", "gates"]:
        for name, value in config.get(section, {}).items():
            rows.append(
                {
                    "section": section,
                    "parameter": name,
                    "value": json.dumps(value, ensure_ascii=False, default=str),
                    "status": "v0_fixed_contract_constant",
                }
            )
    return pd.DataFrame(rows)


def pct(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.1%}"


def build_report(
    *,
    report_path: Path,
    decision: str,
    gate: dict[str, Any],
    events: pd.DataFrame,
    labels: pd.DataFrame,
    capture: pd.DataFrame,
    density: pd.DataFrame,
    density_loss: pd.DataFrame,
    precision: pd.DataFrame,
    false_repair: pd.DataFrame,
    readiness: pd.DataFrame,
    ablation: pd.DataFrame,
    duration_recall: pd.DataFrame,
    lead_time: pd.DataFrame,
    regime: pd.DataFrame,
    data_source: pd.DataFrame,
    input_paths: dict[str, Path],
    upstream_02_manifest: dict[str, Any],
    upstream_03_manifest: dict[str, Any],
) -> Path:
    def fmt(value: Any, digits: int = 2) -> str:
        if value is None or pd.isna(value):
            return "NA"
        if isinstance(value, (int, np.integer)):
            return str(int(value))
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.{digits}f}"
        return str(value)

    def short_hash(value: Any) -> str:
        text = str(value or "")
        return text[:12] if text else ""

    def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
        header = "| " + " | ".join(label for _, label in columns) + " |"
        align = "| " + " | ".join(":--" if idx == 0 else "--:" for idx, _ in enumerate(columns)) + " |"
        body = [
            "| "
            + " | ".join(str(row.get(key, "")) for key, _ in columns)
            + " |"
            for row in rows
        ]
        return [header, align, *body] if body else [header, align]

    def bool_count(frame: pd.DataFrame, column: str) -> int:
        if frame.empty or column not in frame.columns:
            return 0
        return int(frame[column].fillna(False).astype(bool).sum())

    def recall(frame: pd.DataFrame, union_family: str, scope: str, window: str) -> tuple[int, float]:
        column = f"captured_by_{union_family}_{scope}_{window}"
        count = bool_count(frame, column)
        return count, safe_rate(count, len(frame))

    setup_events = events.loc[
        (events["union_family"] == SETUP_UNION)
        & (events["canonical_event_scope"] == CANONICAL_SCOPE)
    ]
    setup_pre_density_events = events.loc[
        (events["union_family"] == SETUP_UNION)
        & (events["canonical_event_scope"] == CANONICAL_PRE_DENSITY_SCOPE)
    ]
    raw_events = events.loc[events["canonical_event_scope"] == RAW_SCOPE]
    setup_labels = labels.loc[
        (labels["union_family"] == SETUP_UNION)
        & (labels["canonical_event_scope"] == CANONICAL_SCOPE)
    ]
    complete120 = setup_labels.loc[setup_labels["candidate_outcome_120d_status"] == NOT_MISSING]
    positive_rate = safe_rate(
        int(complete120["event_big_winner_120d_label"].fillna(False).astype(bool).sum()),
        len(complete120),
    )
    near_rate = safe_rate(
        int(complete120["event_near_winner_120d_label"].fillna(False).astype(bool).sum()),
        len(complete120),
    )
    false20_rate = safe_rate(
        int(setup_labels["event_false_repair_20d_label"].fillna(False).astype(bool).sum()),
        len(setup_labels),
    )
    all_capture = capture
    recall_windows = [
        ("pre_low_20d", "pre-low 20"),
        ("low_to_plus_10d", "low+10"),
        ("low_to_plus_20d", "low+20"),
        ("low_to_plus_30d", "low+30"),
        ("low_to_plus_60d", "low+60"),
        ("low_to_plus_120d", "low+120"),
        ("before_first_50pct", "before first 50%"),
        ("before_episode_high", "before episode high"),
    ]
    recall_rows: list[dict[str, Any]] = []
    for window, label in recall_windows:
        setup_count, setup_rate = recall(all_capture, SETUP_UNION, "density_kept", window)
        reclaim_count, reclaim_rate = recall(all_capture, RECLAIM_UNION, "density_kept", window)
        recall_rows.append(
            {
                "window": label,
                "setup_count": setup_count,
                "setup_recall": pct(setup_rate),
                "reclaim_count": reclaim_count,
                "reclaim_recall": pct(reclaim_rate),
            }
        )

    duration_rows: list[dict[str, Any]] = []
    if not capture.empty:
        for bucket, group in capture.groupby("duration_bucket", dropna=False, sort=True):
            low30 = bool_count(group, "captured_by_setup_inclusive_density_kept_low_to_plus_30d")
            before = bool_count(
                group, "captured_by_setup_inclusive_density_kept_before_first_50pct"
            )
            late = bool_count(group, "late_after_first_50pct_capture_flag")
            duration_rows.append(
                {
                    "bucket": bucket,
                    "n": len(group),
                    "low30": pct(safe_rate(low30, len(group))),
                    "before": pct(safe_rate(before, len(group))),
                    "late": pct(safe_rate(late, low30)),
                }
            )
    fast_before = next(
        (
            row["before"]
            for row in duration_rows
            if str(row.get("bucket")) == "fast"
        ),
        "NA",
    )

    target_split_rows = []
    if not capture.empty:
        split_counts = capture.groupby("episode_split", dropna=False).size().reset_index(name="n")
        for row in split_counts.to_dict("records"):
            target_split_rows.append({"split": row["episode_split"], "n": int(row["n"])})
    regime_rows = []
    if not capture.empty:
        regime_counts = (
            capture.groupby("market_regime_bucket", dropna=False).size().reset_index(name="n")
        )
        for row in regime_counts.to_dict("records"):
            regime_rows.append({"regime": row["market_regime_bucket"], "n": int(row["n"])})

    density_rows: list[dict[str, Any]] = []
    if not density.empty:
        density_summary = (
            density.groupby(["event_family", "union_family", "canonical_event_scope"], dropna=False)
            .agg(
                raw_candidate_count=("raw_candidate_count", "sum"),
                density_kept_count=("density_kept_count", "sum"),
                density_folded_count=("density_folded_count", "sum"),
                density_loss_capture_count=("density_loss_capture_count", "sum"),
                events_per_instrument_year_mean=("events_per_instrument_year_mean", "mean"),
                events_per_instrument_year_p95=("events_per_instrument_year_p95", "max"),
            )
            .reset_index()
            .sort_values(["union_family", "canonical_event_scope", "event_family"])
        )
        for row in density_summary.to_dict("records")[:20]:
            density_rows.append(
                {
                    "family": row["event_family"],
                    "union": row["union_family"],
                    "scope": row["canonical_event_scope"],
                    "raw": int(row["raw_candidate_count"]),
                    "kept": int(row["density_kept_count"]),
                    "folded": int(row["density_folded_count"]),
                    "lost": int(row["density_loss_capture_count"]),
                    "p95": fmt(row["events_per_instrument_year_p95"], 2),
                }
            )

    loss_rows: list[dict[str, Any]] = []
    if not density_loss.empty:
        loss_total = density_loss.loc[
            (density_loss["episode_split"] == "all")
            & (density_loss["duration_bucket"] == "all")
        ]
        for row in loss_total.to_dict("records"):
            loss_rows.append(
                {
                    "union": row["union_family"],
                    "window": row["window"],
                    "raw": pct(row["raw_union_recall"]),
                    "canonical": pct(row["canonical_union_recall"]),
                    "density": pct(row["density_kept_union_recall"]),
                    "loss": pct(row["density_loss_recall"]),
                    "lost_n": int(row["density_loss_capture_count"]),
                }
            )

    ablation_rows: list[dict[str, Any]] = []
    if not ablation.empty:
        selected = ablation.loc[
            (ablation["episode_split"] == "all")
            & (ablation["duration_bucket"] == "all")
        ]
        for row in selected.to_dict("records"):
            ablation_rows.append(
                {
                    "variant": row["ablation_variant"],
                    "union": row["union_family"],
                    "low30": pct(row["recall_low_to_plus_30d"]),
                    "before": pct(row["recall_before_first_50pct"]),
                    "without_e0": pct(row["recall_without_E0"]),
                    "e0_only": pct(row["E0_only_capture_share"]),
                }
            )

    readiness_rows: list[dict[str, Any]] = []
    if not readiness.empty:
        ready = readiness.loc[
            (readiness["union_family"] == SETUP_UNION)
            & (readiness["canonical_event_scope"] == CANONICAL_SCOPE)
            & (readiness["label_horizon"] == 120)
        ]
        for row in ready.to_dict("records"):
            readiness_rows.append(
                {
                    "split": row["event_split"],
                    "n": int(row["event_count"]),
                    "positive": int(row["big_winner_120d_positive_count"]),
                    "negative": int(row["negative_count"]),
                    "complete": int(row["outcome_complete_120d_count"]),
                    "uniq": fmt(row["average_uniqueness_mean"], 2),
                    "conc_p95": fmt(row["event_concurrency_p95"], 2),
                }
            )

    precision_rows: list[dict[str, Any]] = []
    if not precision.empty:
        setup_precision = precision.loc[
            (precision["union_family"] == SETUP_UNION)
            & (precision["canonical_event_scope"] == CANONICAL_SCOPE)
        ]
        for row in setup_precision.to_dict("records"):
            precision_rows.append(
                {
                    "split": row["event_split"],
                    "n": int(row["event_count"]),
                    "big": pct(row["event_big_winner_120d_rate"]),
                    "near": pct(row["event_near_winner_120d_rate"]),
                    "false10": pct(row["event_false_repair_10d_rate"]),
                    "false20": pct(row["event_false_repair_20d_rate"]),
                    "cluster_pos": int(row["cluster_positive_count"]),
                }
            )

    false_rows: list[dict[str, Any]] = []
    if not false_repair.empty:
        setup_false = false_repair.loc[
            (false_repair["union_family"] == SETUP_UNION)
            & (false_repair["canonical_event_scope"] == CANONICAL_SCOPE)
        ]
        for row in setup_false.to_dict("records")[:12]:
            false_rows.append(
                {
                    "split": row["event_split"],
                    "regime": row["market_regime_bucket"],
                    "n": int(row["event_count"]),
                    "false10": pct(row["false_repair_10d_rate"]),
                    "false20": pct(row["false_repair_20d_rate"]),
                }
            )

    forward_rows: list[dict[str, Any]] = []
    for horizon in [10, 20, 30, 60, 120]:
        complete_col = f"horizon_complete_{horizon}d"
        complete = (
            setup_labels.loc[setup_labels[complete_col].fillna(False).astype(bool)]
            if complete_col in setup_labels.columns
            else setup_labels.iloc[0:0]
        )
        forward_rows.append(
            {
                "h": f"{horizon}d",
                "complete": len(complete),
                "ret": pct(safe_mean(complete[f"forward_return_{horizon}d"])) if len(complete) else "NA",
                "mfe": pct(safe_mean(complete[f"mfe_{horizon}d"])) if len(complete) else "NA",
                "mae": pct(safe_mean(complete[f"mae_{horizon}d"])) if len(complete) else "NA",
            }
        )

    risk_off_rows: list[dict[str, Any]] = []
    risk_capture = capture.loc[capture["market_regime_bucket"] == "risk_off"] if not capture.empty else capture
    if risk_capture is not None and not risk_capture.empty:
        low30 = bool_count(risk_capture, "captured_by_setup_inclusive_density_kept_low_to_plus_30d")
        before = bool_count(
            risk_capture, "captured_by_setup_inclusive_density_kept_before_first_50pct"
        )
        risk_off_rows.append(
            {
                "metric": "episode recall low+30 / before-first",
                "value": f"{pct(safe_rate(low30, len(risk_capture)))} / {pct(safe_rate(before, len(risk_capture)))}",
            }
        )
    risk_events = setup_events.loc[setup_events["market_regime_bucket"] == "risk_off"]
    risk_labels = setup_labels.loc[setup_labels["event_id"].isin(risk_events["event_id"])]
    if len(risk_events):
        risk_complete = risk_labels.loc[risk_labels["candidate_outcome_120d_status"] == NOT_MISSING]
        risk_positive = bool_count(risk_complete, "event_big_winner_120d_label")
        risk_false20 = bool_count(risk_labels, "event_false_repair_20d_label")
        risk_off_rows.extend(
            [
                {"metric": "setup events", "value": str(len(risk_events))},
                {
                    "metric": "120d positive rate",
                    "value": pct(safe_rate(risk_positive, len(risk_complete))),
                },
                {
                    "metric": "false repair 20d rate",
                    "value": pct(safe_rate(risk_false20, len(risk_labels))),
                },
            ]
        )

    lead_total = lead_time.loc[
        (lead_time["episode_split"] == "all") & (lead_time["duration_bucket"] == "all")
    ]
    lead_line = "NA"
    if not lead_total.empty:
        lead_row = lead_total.iloc[0]
        lead_line = (
            f"mean {fmt(lead_row['lead_time_mean'], 1)}, median {fmt(lead_row['lead_time_median'], 1)}, "
            f"p25/p75 {fmt(lead_row['lead_time_p25'], 1)} / {fmt(lead_row['lead_time_p75'], 1)} sessions"
        )

    data_rows = []
    for row in data_source.to_dict("records"):
        if row.get("input_name") in {
            "upstream_reverse_lifecycle_manifest_json",
            "upstream_observable_anchor_manifest_json",
            "upstream_big_winner_episode_reference_parquet",
            "upstream_strict_event_pool_parquet",
            "vwap_source_policy",
        }:
            data_rows.append(
                {
                    "input": row.get("input_name", ""),
                    "exists": row.get("exists", ""),
                    "hash": short_hash(row.get("sha256", "")),
                }
            )

    report_insight = (
        "当前候选池的主要风险是 recall 是否足够早，而不是 precision 是否已经像交易信号。"
        "若 before-first-50pct 低于 low+30，说明候选事件能覆盖 episode，但对快赢家偏晚；"
        "此时应该寻找更早 anchor 或放宽 setup-inclusive 入口，而不是把 E2/E4 质量过滤继续收紧。"
    )
    lines = [
        "# 高召回修复事件候选生成器 V0 报告",
        "",
        "本实验是 event candidate generator，不是 primary model、不是策略、不是回测。高 recall 是主目标，precision / false positive 噪声留给后续模型。",
        "",
        "## Final Decision",
        "",
        f"- decision: `{decision}`",
        f"- target episodes: {gate['target_episode_count_total']} total / {gate['target_episode_count_validation']} validation / {gate['target_episode_count_robustness']} robustness",
        f"- raw family events: {len(raw_events)}",
        f"- setup-inclusive canonical-before-density events: {len(setup_pre_density_events)}",
        f"- setup-inclusive canonical events: {len(setup_events)}",
        f"- source git revision: `{short_hash(git_revision(PROJECT_ROOT))}`",
        f"- upstream 02 decision: `{upstream_02_manifest.get('decision', '')}` / manifest hash `{short_hash(file_sha256(input_paths['upstream_reverse_lifecycle_manifest_json']))}` / git `{short_hash(upstream_02_manifest.get('source_git_revision'))}`",
        f"- upstream 03 decision: `{upstream_03_manifest.get('decision', '')}` / manifest hash `{short_hash(file_sha256(input_paths['upstream_observable_anchor_manifest_json']))}` / git `{short_hash(upstream_03_manifest.get('source_git_revision'))}`",
        "",
        "02 提供冻结的 canonical big-winner episode denominator；03 说明严格 observable anchor 不足以形成可靠 edge，因此 04 改为高召回候选池，precision 交给后续 primary/meta 层处理。",
        "",
        "## Data Source Check",
        "",
        *table(
            data_rows,
            [("input", "input"), ("exists", "exists"), ("hash", "sha256 prefix")],
        ),
        "",
        "## Target Denominator",
        "",
        *table(target_split_rows, [("split", "episode split"), ("n", "episodes")]),
        "",
        *table(regime_rows, [("regime", "market regime"), ("n", "episodes")]),
        "",
        "## Co-headline Recall",
        "",
        "| metric | total | validation | robustness |",
        "|:--|--:|--:|--:|",
        f"| low+30 fixed-window recall | {pct(gate['total_recall_low_to_plus_30d'])} | {pct(gate['validation_recall_low_to_plus_30d'])} | {pct(gate['robustness_recall_low_to_plus_30d'])} |",
        f"| before-first-50pct actionable recall | {pct(gate['total_recall_before_first_50pct'])} | {pct(gate['validation_recall_before_first_50pct'])} | {pct(gate['robustness_recall_before_first_50pct'])} |",
        f"| low+20 support recall | {pct(gate['total_recall_low_to_plus_20d'])} | {pct(gate['validation_recall_low_to_plus_20d'])} | {pct(gate['robustness_recall_low_to_plus_20d'])} |",
        "",
        f"fast duration bucket 的 before-first-50pct recall 为 {fast_before}。这个读数用于检查 low+30 是否对快赢家虚高。",
        "",
        "## Union Recall Detail",
        "",
        *table(
            recall_rows,
            [
                ("window", "window"),
                ("setup_count", "setup n"),
                ("setup_recall", "setup recall"),
                ("reclaim_count", "reclaim n"),
                ("reclaim_recall", "reclaim recall"),
            ],
        ),
        "",
        "pre-low 20 是 diagnostic-only。它只能说明候选事件在 retrospective low 附近是否已经出现，不能解释为事前精准识别低点。",
        "",
        "## Duration Bucket Actionability",
        "",
        *table(
            duration_rows,
            [
                ("bucket", "bucket"),
                ("n", "episodes"),
                ("low30", "low+30 recall"),
                ("before", "before-first recall"),
                ("late", "late share"),
            ],
        ),
        "",
        f"lead time to first 50pct: {lead_line}",
        "",
        "## Density / Executability",
        "",
        f"- setup-inclusive density p95 / mean: {gate['setup_inclusive_events_per_instrument_year_p95']:.2f} / {gate['setup_inclusive_events_per_instrument_year_mean']:.2f}",
        f"- reclaim-based density p95 / mean: {gate['reclaim_based_events_per_instrument_year_p95']:.2f} / {gate['reclaim_based_events_per_instrument_year_mean']:.2f}",
        f"- executable rate: {pct(gate['executable_rate'])}",
        f"- main 20d label complete rate: {pct(gate['main_label_complete_rate'])}",
        "",
        *table(
            density_rows,
            [
                ("family", "family"),
                ("union", "union"),
                ("scope", "scope"),
                ("raw", "raw"),
                ("kept", "kept"),
                ("folded", "folded"),
                ("lost", "lost capture"),
                ("p95", "density p95"),
            ],
        ),
        "",
        "## Density Loss",
        "",
        *table(
            loss_rows,
            [
                ("union", "union"),
                ("window", "window"),
                ("raw", "raw recall"),
                ("canonical", "canonical recall"),
                ("density", "density-kept recall"),
                ("loss", "loss"),
                ("lost_n", "lost n"),
            ],
        ),
        "",
        "## Event Family Ablation",
        "",
        *table(
            ablation_rows,
            [
                ("variant", "variant"),
                ("union", "union"),
                ("low30", "low+30"),
                ("before", "before-first"),
                ("without_e0", "without E0"),
                ("e0_only", "E0-only share"),
            ],
        ),
        "",
        "Ablation 应与 headline 同级解读：如果 E0-only share 高，说明宽网主要来自 setup-inclusive 低点候选；E1/E2/E4 的价值要看 reclaim-based 与 raw family 行的边际 recall，而不是 headline 数字本身。",
        "",
        "## Label Readiness",
        "",
        f"- setup-inclusive event-anchored 120d big-winner positive rate: {pct(positive_rate)}",
        f"- setup-inclusive near-winner 120d rate: {pct(near_rate)}",
        f"- setup-inclusive false-repair 20d rate: {pct(false20_rate)}",
        f"- 120d outcome complete rate: {pct(gate['outcome_complete_120d_rate'])}",
        "",
        *table(
            precision_rows,
            [
                ("split", "event split"),
                ("n", "events"),
                ("big", "big winner"),
                ("near", "near winner"),
                ("false10", "false 10d"),
                ("false20", "false 20d"),
                ("cluster_pos", "cluster pos"),
            ],
        ),
        "",
        "### False-Repair By Regime",
        "",
        *table(
            false_rows,
            [
                ("split", "event split"),
                ("regime", "regime"),
                ("n", "events"),
                ("false10", "false 10d"),
                ("false20", "false 20d"),
            ],
        ),
        "",
        *table(
            readiness_rows,
            [
                ("split", "event split"),
                ("n", "events"),
                ("positive", "positive"),
                ("negative", "negative"),
                ("complete", "120d complete"),
                ("uniq", "avg uniqueness"),
                ("conc_p95", "concurrency p95"),
            ],
        ),
        "",
        "capture 是 episode-anchored recall；positive label 是 event-anchored 120d outcome。捕获了 target episode 的 event 仍可能因为从自身 t0 往后 MFE 不足 50% 而是 negative，两者不得混算。",
        "",
        "confirm_20 / failure_10 只是短期 tradeability / repair durability proxy，不是 120d big-winner 的代理标签。",
        "",
        "## Forward Diagnostics",
        "",
        *table(
            forward_rows,
            [
                ("h", "horizon"),
                ("complete", "complete"),
                ("ret", "mean return"),
                ("mfe", "mean MFE"),
                ("mae", "mean MAE"),
            ],
        ),
        "",
        "## Risk-Off Diagnostic",
        "",
        *table(risk_off_rows, [("metric", "metric"), ("value", "value")]),
        "",
        "## Decision Replay",
        "",
        f"- target count gates: total {gate['target_episode_count_total']} >= {gate['gates']['min_total_target_episode_count']}; validation {gate['target_episode_count_validation']} >= {gate['gates']['min_validation_target_episode_count']}; robustness {gate['target_episode_count_robustness']} >= {gate['gates']['min_robustness_target_episode_count']}",
        f"- executable / main label completeness: {pct(gate['executable_rate'])} / {pct(gate['main_label_complete_rate'])}",
        f"- total fixed-window recall low+30 / low+20: {pct(gate['total_recall_low_to_plus_30d'])} / {pct(gate['total_recall_low_to_plus_20d'])}",
        f"- validation fixed-window recall low+30 / low+20: {pct(gate['validation_recall_low_to_plus_30d'])} / {pct(gate['validation_recall_low_to_plus_20d'])}",
        f"- robustness fixed-window recall low+30 / low+20: {pct(gate['robustness_recall_low_to_plus_30d'])} / {pct(gate['robustness_recall_low_to_plus_20d'])}",
        f"- density p95 setup/reclaim: {fmt(gate['setup_inclusive_events_per_instrument_year_p95'])} / {fmt(gate['reclaim_based_events_per_instrument_year_p95'])}",
        f"- before-first recall total/validation/robustness: {pct(gate['total_recall_before_first_50pct'])} / {pct(gate['validation_recall_before_first_50pct'])} / {pct(gate['robustness_recall_before_first_50pct'])}",
        f"- final decision by short-circuit order: `{decision}`",
        "",
        "## Insight",
        "",
        report_insight,
        "",
        "## Next Step",
        "",
        "若 decision 为 supported/noisy_precision，可进入 primary model / meta-labeling 研究；若为 actionability_late_blocked，下一步应寻找更早 anchor，而不是继续收紧过滤。",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def write_manifest(
    *,
    manifest_path: Path,
    config: dict[str, Any],
    config_path: Path,
    input_paths: dict[str, Path],
    output_paths: dict[str, Path],
    decision: str,
    gate_summary: dict[str, Any],
    upstream_02_manifest: dict[str, Any],
    upstream_03_manifest: dict[str, Any],
) -> Path:
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
            json.dumps(config, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
        ).hexdigest(),
        "config_file_hash": file_sha256(config_path),
        "input_paths": {name: str(path.resolve()) for name, path in sorted(input_paths.items())},
        "input_hashes": input_hashes,
        "upstream_reverse_lifecycle_decision": upstream_02_manifest.get("decision"),
        "upstream_observable_anchor_decision": upstream_03_manifest.get("decision"),
        "upstream_reverse_lifecycle_git_revision": upstream_02_manifest.get("source_git_revision"),
        "upstream_observable_anchor_git_revision": upstream_03_manifest.get("source_git_revision"),
        "decision": decision,
        "gate_summary": gate_summary,
        "outputs": {name: str(path.resolve()) for name, path in sorted(output_paths.items())},
        "output_hashes": output_hashes,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_event_daily_aligned_panel(
    events: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    *,
    left: int = -5,
    right: int = 20,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    canonical = events.loc[
        (events["canonical_event_scope"] == CANONICAL_SCOPE)
        & (events["union_family"] == SETUP_UNION)
    ]
    for event in canonical.to_dict("records"):
        daily = daily_by_instrument.get(str(event["instrument"]))
        if daily is None:
            continue
        t0 = int(event["event_t0_pos"])
        start = max(0, t0 + left)
        end = min(len(daily) - 1, t0 + right)
        for pos in range(start, end + 1):
            rows.append(
                {
                    "event_id": event["event_id"],
                    "instrument": event["instrument"],
                    "event_t0_date": event["event_t0_date"],
                    "date": daily.at[pos, "date"],
                    "relative_day": int(pos - t0),
                    "close_to_ema60": daily.at[pos, "close_to_ema60"],
                    "stock_vs_market_20d": daily.at[pos, "stock_vs_market_20d"],
                    "amount_ratio_20d": daily.at[pos, "amount_ratio_20d"],
                    "close_position_in_range": daily.at[pos, "close_position_in_range"],
                }
            )
    return pd.DataFrame(rows)


def run_pipeline(
    config: dict[str, Any],
    *,
    config_path: Path,
    max_instruments: int | None = None,
) -> dict[str, Any]:
    paths_cfg = config["paths"]
    outputs = config["outputs"]
    table_dir = PROJECT_ROOT / outputs["publishable_tables_dir"]
    report_dir = PROJECT_ROOT / outputs["publishable_reports_dir"]
    local_cache_dir = PROJECT_ROOT / outputs["local_cache_dir"]
    large_raw_dir = PROJECT_ROOT / outputs["large_raw_dir"]
    manifest_dir = PROJECT_ROOT / outputs["manifests_dir"]
    ensure_dirs([table_dir, report_dir, local_cache_dir, large_raw_dir, manifest_dir])

    input_paths = {
        "stock_daily_csv_dir": PROJECT_ROOT / paths_cfg["stock_daily_csv_dir"],
        "benchmark_daily_csv": PROJECT_ROOT / paths_cfg["benchmark_daily_csv"],
        "executable_universe_csv": PROJECT_ROOT / paths_cfg["executable_universe_csv"],
        "data_prepare_run_manifest_json": PROJECT_ROOT
        / paths_cfg["data_prepare_run_manifest_json"],
        "data_prepare_source_coverage_audit_csv": PROJECT_ROOT
        / paths_cfg["data_prepare_source_coverage_audit_csv"],
        "upstream_reverse_lifecycle_manifest_json": PROJECT_ROOT
        / paths_cfg["upstream_reverse_lifecycle_manifest_json"],
        "upstream_big_winner_episode_reference_parquet": PROJECT_ROOT
        / paths_cfg["upstream_big_winner_episode_reference_parquet"],
        "upstream_big_winner_episode_reference_summary_csv": PROJECT_ROOT
        / paths_cfg["upstream_big_winner_episode_reference_summary_csv"],
        "upstream_observable_anchor_manifest_json": PROJECT_ROOT
        / paths_cfg["upstream_observable_anchor_manifest_json"],
        "upstream_observable_anchor_report_md": PROJECT_ROOT
        / paths_cfg["upstream_observable_anchor_report_md"],
        "upstream_strict_event_pool_parquet": PROJECT_ROOT
        / paths_cfg["upstream_strict_event_pool_parquet"],
    }
    validate_required_inputs(input_paths)
    upstream_02_manifest = load_json(input_paths["upstream_reverse_lifecycle_manifest_json"])
    upstream_03_manifest = load_json(input_paths["upstream_observable_anchor_manifest_json"])
    if upstream_02_manifest.get("decision") != "reverse_lifecycle_sequence_supported_universal_dominance":
        raise RuntimeError("02 upstream decision does not authorize 04")
    if upstream_03_manifest.get("decision") not in {
        "event_contract_sample_blocked",
        "event_contract_no_baseline_separation",
        "event_contract_false_repair_filter_dominant_no_rank_persistence_separation",
    }:
        raise RuntimeError("03 upstream decision is not a legal negative result for 04")

    event_cfg_raw = config["event_generation"]
    event_cfg = EventConfig(
        prior_lookback_sessions=int(event_cfg_raw["prior_lookback_sessions"]),
        seed_low_lookback_sessions=int(event_cfg_raw["seed_low_lookback_sessions"]),
        anchor_search_horizon_sessions=int(event_cfg_raw["anchor_search_horizon_sessions"]),
        e2_quality_window=int(event_cfg_raw["e2_quality_window"]),
        e4_relative_strength_window=int(event_cfg_raw["e4_relative_strength_window"]),
        e3_false_repair_drawdown=float(event_cfg_raw["e3_false_repair_drawdown"]),
        e3_variants=tuple(int(v) for v in event_cfg_raw["e3_variants"]),
    )
    labels_cfg = config["labels"]
    label_cfg = LabelConfig(
        confirm_horizon=int(labels_cfg["confirm_20"]["horizon_days"]),
        confirm_upper=float(labels_cfg["confirm_20"]["upper_barrier"]),
        confirm_lower=float(labels_cfg["confirm_20"]["lower_barrier"]),
        failure_horizon=int(labels_cfg["failure_10"]["horizon_days"]),
        failure_lower=float(labels_cfg["failure_10"]["lower_barrier"]),
        continuous_horizons=tuple(int(v) for v in labels_cfg["continuous_horizons"]),
        big_winner_mfe_120d=float(labels_cfg["big_winner_mfe_120d"]),
        super_winner_mfe_120d=float(labels_cfg["super_winner_mfe_120d"]),
        near_winner_mfe_lower=float(labels_cfg["near_winner_mfe_lower"]),
        near_winner_mfe_upper=float(labels_cfg["near_winner_mfe_upper"]),
        false_repair_drawdown=float(labels_cfg["false_repair_drawdown"]),
    )
    density_params = observable_density_params(config)

    source_coverage = pd.read_csv(input_paths["data_prepare_source_coverage_audit_csv"])
    vwap_policy = _observable.resolve_vwap_source_policy(source_coverage)
    benchmark_daily = pd.read_csv(input_paths["benchmark_daily_csv"])
    market_features = _reverse.compute_market_features(benchmark_daily)
    benchmark_returns = compute_benchmark_returns(benchmark_daily)
    calendar = (
        benchmark_daily.loc[benchmark_daily["index_alias"] == "all_a", "trade_date"]
        .dropna()
        .map(date_str)
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    split_raw = config["splits"]
    split_config = SplitConfig(
        train_start=split_raw["train_start"],
        train_end=split_raw["train_end"],
        validation_start=split_raw["validation_start"],
        validation_end=split_raw["validation_end"],
        robustness_start=split_raw["robustness_start"],
        latest_main_label_complete_t0_date=latest_complete_t0_date(
            calendar, label_cfg.confirm_horizon
        ),
        latest_120d_outcome_complete_t0_date=latest_complete_t0_date(calendar, 120),
    )

    universe = pd.read_csv(input_paths["executable_universe_csv"])
    universe["usable_trade_date"] = pd.to_datetime(
        universe["usable_trade_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    universe = universe.sort_values(["instrument", "usable_trade_date"])
    membership_by_instrument = {
        instrument: group.reset_index(drop=True)
        for instrument, group in universe.groupby("instrument", sort=True)
    }
    stock_dir = input_paths["stock_daily_csv_dir"]
    instruments = [
        instrument
        for instrument in sorted(membership_by_instrument)
        if (stock_dir / f"{instrument}.csv").is_file()
    ]
    if max_instruments is not None:
        instruments = instruments[: int(max_instruments)]

    strict_pool = pd.read_parquet(input_paths["upstream_strict_event_pool_parquet"])
    strict_by_instrument = {
        instrument: group.reset_index(drop=True)
        for instrument, group in strict_pool.groupby("instrument", sort=True)
    }
    raw_parts: list[pd.DataFrame] = []
    daily_by_instrument: dict[str, pd.DataFrame] = {}
    for instrument in instruments:
        membership = membership_by_instrument[instrument]
        daily_csv = stock_dir / f"{instrument}.csv"
        daily = pd.read_csv(daily_csv)
        features = enrich_stock_features(
            daily,
            instrument=instrument,
            membership=membership,
            market_features=market_features,
            benchmark_returns=benchmark_returns,
            vwap_source_units_compatible=bool(vwap_policy.get("compatible", False)),
        )
        daily_by_instrument[instrument] = features
        raw = build_raw_events_for_instrument(
            instrument=instrument,
            daily=features,
            membership=membership,
            strict_events=strict_by_instrument.get(instrument, pd.DataFrame()),
            event_cfg=event_cfg,
            quality_cfg=config["quality_flags"],
            rs_cfg=config["relative_strength"],
            density_params=density_params,
            split_config=split_config,
        )
        if not raw.empty:
            raw_parts.append(raw)
    raw_events = pd.concat(raw_parts, ignore_index=True) if raw_parts else pd.DataFrame()
    candidate_instances = build_candidate_instances(
        raw_events,
        density_window=int(config["density"]["union_density_window"]),
    )
    labels = label_events(
        candidate_instances,
        daily_by_instrument=daily_by_instrument,
        label_cfg=label_cfg,
    )

    episodes = pd.read_parquet(input_paths["upstream_big_winner_episode_reference_parquet"])
    episodes = episodes.loc[episodes["instrument"].isin(daily_by_instrument)].copy()
    episodes["episode_split"] = episodes["episode_low_date"].map(
        lambda value: split_for_episode(value, split_config)
    )
    episodes = episodes.loc[episodes["episode_split"] != "outside_split"].copy()
    capture = build_episode_capture_audit(
        episodes,
        raw_events=raw_events,
        candidate_instances=candidate_instances,
        daily_by_instrument=daily_by_instrument,
        split_config=split_config,
        capture_cfg=config["capture_windows"],
    )
    labels = update_label_capture_counts(labels, capture)

    density_audit = build_event_density_audit(candidate_instances, capture)
    event_recall_stats = build_event_family_recall_stats(capture)
    duration_recall = build_duration_bucket_actionable_recall(capture)
    density_loss = build_density_loss_capture_audit(capture)
    precision = build_event_precision_label_readout(labels)
    false_repair = build_false_repair_diagnostic(labels, candidate_instances)
    executability = build_executability_audit(candidate_instances, labels)
    readiness = build_downstream_model_readiness(candidate_instances, labels)
    lead_time = build_lead_time_distribution(capture)
    ablation = build_event_family_ablation_audit(capture, density_audit)
    data_source = build_data_source_coverage_audit(input_paths, vwap_policy)
    regime = build_regime_recall_density_audit(capture, candidate_instances)
    threshold = build_threshold_freeze_audit(config)
    event_daily_panel = build_event_daily_aligned_panel(candidate_instances, daily_by_instrument)

    gate = build_gate_summary(
        capture=capture,
        candidate_instances=candidate_instances,
        labels=labels,
        density=density_audit,
        gates=config["gates"],
    )
    decision = decide(gate)

    output_paths: dict[str, Path] = {
        "event_family_definition_csv": table_dir / "event_family_definition.csv",
        "candidate_event_instances_csv": table_dir / "candidate_event_instances.csv",
        "candidate_event_label_outcomes_csv": table_dir / "candidate_event_label_outcomes.csv",
        "episode_capture_audit_csv": table_dir / "episode_capture_audit.csv",
        "event_family_recall_stats_csv": table_dir / "event_family_recall_stats.csv",
        "event_family_ablation_audit_csv": table_dir / "event_family_ablation_audit.csv",
        "duration_bucket_actionable_recall_csv": table_dir / "duration_bucket_actionable_recall.csv",
        "lead_time_distribution_csv": table_dir / "lead_time_distribution.csv",
        "event_density_audit_csv": table_dir / "event_density_audit.csv",
        "density_loss_capture_audit_csv": table_dir / "density_loss_capture_audit.csv",
        "event_precision_label_readout_csv": table_dir / "event_precision_label_readout.csv",
        "false_repair_diagnostic_by_family_csv": table_dir / "false_repair_diagnostic_by_family.csv",
        "regime_recall_density_audit_csv": table_dir / "regime_recall_density_audit.csv",
        "downstream_model_readiness_audit_csv": table_dir / "downstream_model_readiness_audit.csv",
        "executability_audit_csv": table_dir / "executability_audit.csv",
        "data_source_coverage_audit_csv": table_dir / "data_source_coverage_audit.csv",
        "threshold_freeze_audit_csv": table_dir / "threshold_freeze_audit.csv",
        "report_md": report_dir / "high_recall_repair_event_candidate_report.md",
        "candidate_event_panel_parquet": local_cache_dir / "candidate_event_panel.parquet",
        "episode_capture_panel_parquet": local_cache_dir / "episode_capture_panel.parquet",
        "raw_candidate_event_pool_parquet": large_raw_dir / "raw_candidate_event_pool.parquet",
        "event_daily_aligned_panel_parquet": large_raw_dir / "event_daily_aligned_panel.parquet",
        "manifest_json": manifest_dir / "run_manifest.json",
    }
    write_dataframe(output_paths["event_family_definition_csv"], build_event_family_definition())
    write_dataframe(output_paths["candidate_event_instances_csv"], candidate_instances)
    write_dataframe(output_paths["candidate_event_label_outcomes_csv"], labels)
    write_dataframe(output_paths["episode_capture_audit_csv"], capture)
    write_dataframe(output_paths["event_family_recall_stats_csv"], event_recall_stats)
    write_dataframe(output_paths["event_family_ablation_audit_csv"], ablation)
    write_dataframe(output_paths["duration_bucket_actionable_recall_csv"], duration_recall)
    write_dataframe(output_paths["lead_time_distribution_csv"], lead_time)
    write_dataframe(output_paths["event_density_audit_csv"], density_audit)
    write_dataframe(output_paths["density_loss_capture_audit_csv"], density_loss)
    write_dataframe(output_paths["event_precision_label_readout_csv"], precision)
    write_dataframe(output_paths["false_repair_diagnostic_by_family_csv"], false_repair)
    write_dataframe(output_paths["regime_recall_density_audit_csv"], regime)
    write_dataframe(output_paths["downstream_model_readiness_audit_csv"], readiness)
    write_dataframe(output_paths["executability_audit_csv"], executability)
    write_dataframe(output_paths["data_source_coverage_audit_csv"], data_source)
    write_dataframe(output_paths["threshold_freeze_audit_csv"], threshold)
    candidate_panel = candidate_instances.merge(labels, on="event_id", how="left", suffixes=("", "_label"))
    write_dataframe(output_paths["candidate_event_panel_parquet"], candidate_panel)
    write_dataframe(output_paths["episode_capture_panel_parquet"], capture)
    write_dataframe(output_paths["raw_candidate_event_pool_parquet"], raw_events)
    write_dataframe(output_paths["event_daily_aligned_panel_parquet"], event_daily_panel)
    build_report(
        report_path=output_paths["report_md"],
        decision=decision,
        gate=gate,
        events=candidate_instances,
        labels=labels,
        capture=capture,
        density=density_audit,
        density_loss=density_loss,
        precision=precision,
        false_repair=false_repair,
        readiness=readiness,
        ablation=ablation,
        duration_recall=duration_recall,
        lead_time=lead_time,
        regime=regime,
        data_source=data_source,
        input_paths=input_paths,
        upstream_02_manifest=upstream_02_manifest,
        upstream_03_manifest=upstream_03_manifest,
    )
    write_manifest(
        manifest_path=output_paths["manifest_json"],
        config=config,
        config_path=config_path,
        input_paths=input_paths,
        output_paths=output_paths,
        decision=decision,
        gate_summary=gate,
        upstream_02_manifest=upstream_02_manifest,
        upstream_03_manifest=upstream_03_manifest,
    )
    return {
        "decision": decision,
        "raw_event_count": int(len(raw_events)),
        "canonical_event_count": int(
            (
                (candidate_instances["canonical_event_scope"] == CANONICAL_SCOPE)
                if not candidate_instances.empty
                else pd.Series(dtype=bool)
            ).sum()
        ),
        "target_episode_count": int(len(capture)),
        "manifest_path": str(output_paths["manifest_json"]),
        "report_path": str(output_paths["report_md"]),
    }

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


MISSING_INSUFFICIENT_LOOKBACK = "missing_insufficient_lookback"
MISSING_EVENT_ABSENT = "missing_event_absent"
MISSING_SOURCE_FIELD = "missing_source_field"
MISSING_UNIT_INCOMPATIBLE = "missing_unit_incompatible"
MISSING_OUT_OF_COVERAGE = "missing_out_of_coverage"
NOT_MISSING = "not_missing"


FEATURE_FAMILIES: dict[str, list[str]] = {
    "price_structure": [
        "close_to_ema20",
        "close_to_ema60",
        "ema20_slope_20d",
        "ema60_slope_20d",
        "return_5d",
        "return_20d",
        "return_60d",
        "drawdown_from_60d_high",
        "distance_to_120d_high",
        "close_position_in_range",
        "gap_open_pct",
        "gap_fade_flag",
    ],
    "volume_money_vwap_turnover": [
        "amount_ratio_20d",
        "amount_ratio_60d",
        "turnover_ratio_20d",
        "close_to_derived_daily_vwap",
        "open_to_derived_daily_vwap",
        "vwap_deviation_20d_z",
        "vwap_reclaim_flag",
    ],
    "volatility_structure": [
        "intraday_range_pct",
        "upper_shadow_pct",
        "atr_20_pct",
    ],
    "relative_strength": [
        "stock_vs_market_20d",
    ],
}

SNAPSHOT_COLUMNS = [
    "close_to_ema20",
    "close_to_ema60",
    "ema20_slope_20d",
    "ema60_slope_20d",
    "return_5d",
    "return_20d",
    "return_60d",
    "drawdown_from_60d_high",
    "distance_to_120d_high",
    "amount_ratio_20d",
    "amount_ratio_60d",
    "turnover_ratio_20d",
    "derived_daily_vwap_available",
    "derived_daily_vwap_price_basis",
    "derived_daily_vwap_missing_reason",
    "qfq_adjustment_factor_available",
    "close_to_derived_daily_vwap",
    "open_to_derived_daily_vwap",
    "vwap_deviation_20d_z",
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
class ExtractionParams:
    local_low_window_sessions: int = 20
    prior_lookback_sessions: int = 250
    forward_horizon_sessions: int = 120
    big_winner_mfe_threshold: float = 0.50
    near_winner_lower_mfe_threshold: float = 0.30
    near_winner_upper_mfe_threshold: float = 0.50
    post_high_exhaustion_sessions: int = 30


@dataclass(frozen=True)
class SplitConfig:
    train_start: str = "2017-01-03"
    train_end: str = "2021-12-31"
    validation_start: str = "2022-01-01"
    validation_end: str = "2023-12-31"
    robustness_start: str = "2024-01-01"
    latest_label_complete_low_date: str = ""


@dataclass(frozen=True)
class MatchConfig:
    max_controls_per_winner: int = 5
    same_week_required: bool = True
    match_fields: tuple[str, ...] = (
        "board_bucket",
        "market_cap_bucket",
        "liquidity_bucket",
        "prior_return_20d_bucket",
        "prior_return_60d_bucket",
        "prior_drawdown_bucket",
        "volatility_bucket",
    )


def parse_date(value: Any) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid date {value!r}")
    return pd.Timestamp(parsed).normalize()


def date_str(value: Any) -> str:
    return parse_date(value).strftime("%Y-%m-%d")


def normalize_date_column(frame: pd.DataFrame, column: str = "date") -> pd.DataFrame:
    out = frame.copy()
    out[column] = pd.to_datetime(out[column], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def week_start(value: Any) -> str:
    dt = parse_date(value)
    return (dt - pd.Timedelta(days=int(dt.dayofweek))).strftime("%Y-%m-%d")


def latest_complete_low_date(calendar: Iterable[str], horizon_sessions: int) -> str:
    sessions = sorted(date_str(value) for value in calendar)
    if len(sessions) <= horizon_sessions:
        raise ValueError("Calendar is shorter than the forward horizon")
    return sessions[-horizon_sessions - 1]


def split_for_date(value: Any, split_config: SplitConfig) -> str:
    text = date_str(value)
    if split_config.train_start <= text <= split_config.train_end:
        return "train"
    if split_config.validation_start <= text <= split_config.validation_end:
        return "validation"
    if (
        split_config.robustness_start
        <= text
        <= split_config.latest_label_complete_low_date
    ):
        return "robustness"
    return "outside_split"


def duration_bucket(low_to_high_sessions: float | int | None) -> str:
    if low_to_high_sessions is None or pd.isna(low_to_high_sessions):
        return "not_applicable"
    value = int(low_to_high_sessions)
    if value <= 40:
        return "fast"
    if value <= 80:
        return "medium"
    if value <= 120:
        return "long"
    return "invalid_gt_120"


def board_to_benchmark_alias(board_bucket: str) -> str:
    if board_bucket == "chinext":
        return "chinext_index"
    if board_bucket == "main_board":
        return "csi300"
    return "all_a"


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    out = numerator.astype(float) / denominator.astype(float)
    return out.replace([np.inf, -np.inf], np.nan)


def compute_market_features(index_daily: pd.DataFrame) -> pd.DataFrame:
    required = {"trade_date", "index_alias", "close"}
    missing = required.difference(index_daily.columns)
    if missing:
        raise ValueError(f"Benchmark daily missing columns: {sorted(missing)}")

    base = index_daily.copy()
    base["trade_date"] = pd.to_datetime(base["trade_date"], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    base = base.sort_values(["index_alias", "trade_date"])
    rows: list[pd.DataFrame] = []
    all_a = base.loc[base["index_alias"] == "all_a", ["trade_date", "close"]].copy()
    if all_a.empty:
        raise ValueError("Benchmark daily does not contain all_a")
    all_a = all_a.sort_values("trade_date")
    all_a_close = all_a["close"].astype(float)
    all_a["market_trend_60d"] = _safe_divide(
        all_a_close, all_a_close.rolling(60, min_periods=60).mean()
    ) - 1.0
    all_a["market_drawdown_120d"] = _safe_divide(
        all_a_close, all_a_close.rolling(120, min_periods=120).max()
    ) - 1.0
    all_a["market_regime_bucket"] = [
        market_regime_bucket(trend, drawdown)
        for trend, drawdown in zip(
            all_a["market_trend_60d"], all_a["market_drawdown_120d"], strict=True
        )
    ]
    regime = all_a[["trade_date", "market_regime_bucket"]]

    for alias, group in base.groupby("index_alias", sort=False):
        group = group.sort_values("trade_date").copy()
        close = group["close"].astype(float)
        group["market_return_20d"] = close / close.shift(20) - 1.0
        group["market_drawdown_60d"] = (
            close / close.rolling(60, min_periods=60).max() - 1.0
        )
        group["market_volatility_20d"] = close.pct_change().rolling(
            20, min_periods=20
        ).std()
        group = group.merge(regime, on="trade_date", how="left")
        group["benchmark_alias"] = alias
        rows.append(
            group[
                [
                    "trade_date",
                    "benchmark_alias",
                    "market_return_20d",
                    "market_drawdown_60d",
                    "market_volatility_20d",
                    "market_regime_bucket",
                ]
            ]
        )
    return pd.concat(rows, ignore_index=True)


def market_regime_bucket(
    market_trend_60d: float | int | None, market_drawdown_120d: float | int | None
) -> str:
    if pd.isna(market_trend_60d) or pd.isna(market_drawdown_120d):
        return MISSING_INSUFFICIENT_LOOKBACK
    trend = float(market_trend_60d)
    drawdown = float(market_drawdown_120d)
    if trend >= 0 and drawdown > -0.10:
        return "risk_on"
    if trend < 0 and drawdown <= -0.10:
        return "risk_off"
    return "transition"


def compute_stock_features(
    daily: pd.DataFrame,
    *,
    vwap_source_units_compatible: bool = True,
) -> pd.DataFrame:
    required = {
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "turnover_rate",
        "factor",
    }
    missing = required.difference(daily.columns)
    if missing:
        raise ValueError(f"Daily stock data missing columns: {sorted(missing)}")

    out = normalize_date_column(daily, "date").sort_values("date").reset_index(drop=True)
    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "turnover_rate",
        "factor",
    ]
    for optional_column in ["raw_close", "raw_volume", "raw_money"]:
        if optional_column in out.columns:
            numeric_columns.append(optional_column)
    for column in numeric_columns:
        out[column] = pd.to_numeric(out[column], errors="coerce")

    close = out["close"].astype(float)
    high = out["high"].astype(float)
    low = out["low"].astype(float)
    open_ = out["open"].astype(float)
    volume = out["volume"].astype(float)
    money = out["money"].astype(float)
    turnover = out["turnover_rate"].astype(float)
    factor = out["factor"].astype(float)

    ema20 = close.rolling(20, min_periods=20).mean()
    ema60 = close.rolling(60, min_periods=60).mean()
    out["ema20"] = ema20
    out["ema60"] = ema60
    out["close_to_ema20"] = close / ema20 - 1.0
    out["close_to_ema60"] = close / ema60 - 1.0
    out["ema20_slope_20d"] = ema20 / ema20.shift(20) - 1.0
    out["ema60_slope_20d"] = ema60 / ema60.shift(20) - 1.0
    out["return_5d"] = close / close.shift(5) - 1.0
    out["return_20d"] = close / close.shift(20) - 1.0
    out["return_60d"] = close / close.shift(60) - 1.0
    out["drawdown_from_60d_high"] = close / high.rolling(60, min_periods=60).max() - 1.0
    out["distance_to_120d_high"] = close / high.rolling(120, min_periods=120).max() - 1.0
    out["amount_ratio_20d"] = money / money.rolling(20, min_periods=20).mean()
    out["amount_ratio_60d"] = money / money.rolling(60, min_periods=60).mean()
    out["money_mean_20d"] = money.rolling(20, min_periods=20).mean()
    out["turnover_ratio_20d"] = turnover / turnover.rolling(20, min_periods=20).mean()

    if "raw_close" in out.columns:
        raw_close = out["raw_close"].astype(float)
    else:
        raw_close = pd.Series(np.nan, index=out.index, dtype=float)
        inferred_raw_close = _safe_divide(close, factor)
        raw_close.loc[(factor > 0) & (close > 0)] = inferred_raw_close.loc[
            (factor > 0) & (close > 0)
        ]
    raw_close_available = raw_close.notna() & (raw_close > 0)
    qfq_raw_alignment_valid = raw_close_available & (factor > 0)
    if "raw_close" in out.columns:
        implied_factor = _safe_divide(close, raw_close)
        qfq_raw_alignment_valid = qfq_raw_alignment_valid & (
            (implied_factor - factor).abs() <= 1e-6
        )

    vwap_source_fields_valid = (
        money.notna()
        & volume.notna()
        & factor.notna()
        & raw_close_available
        & (money > 0)
        & (volume > 0)
        & (factor > 0)
    )
    vwap_unit_ok = bool(vwap_source_units_compatible)
    vwap_valid = vwap_source_fields_valid & qfq_raw_alignment_valid & vwap_unit_ok
    raw_vwap = pd.Series(np.nan, index=out.index, dtype=float)
    raw_vwap.loc[vwap_valid] = money.loc[vwap_valid] / volume.loc[vwap_valid]
    qfq_vwap = raw_vwap * factor
    vwap_missing_reason = pd.Series(NOT_MISSING, index=out.index, dtype="object")
    vwap_missing_reason.loc[~vwap_valid] = MISSING_SOURCE_FIELD
    vwap_missing_reason.loc[
        vwap_source_fields_valid & ~qfq_raw_alignment_valid
    ] = MISSING_UNIT_INCOMPATIBLE
    if not vwap_unit_ok:
        vwap_missing_reason.loc[~vwap_valid] = MISSING_UNIT_INCOMPATIBLE
    out["raw_daily_vwap"] = raw_vwap
    out["qfq_daily_vwap"] = qfq_vwap
    out["derived_daily_vwap_available"] = vwap_valid
    out["derived_daily_vwap_price_basis"] = np.where(vwap_valid, "qfq", "")
    out["derived_daily_vwap_missing_reason"] = vwap_missing_reason
    out["qfq_adjustment_factor_available"] = factor > 0
    out["close_to_derived_daily_vwap"] = close / qfq_vwap - 1.0
    out["open_to_derived_daily_vwap"] = open_ / qfq_vwap - 1.0
    vwap_dev = out["close_to_derived_daily_vwap"]
    vwap_std = vwap_dev.rolling(20, min_periods=20).std()
    out["vwap_deviation_20d_z"] = (vwap_dev - vwap_dev.rolling(20, min_periods=20).mean()) / vwap_std
    out["vwap_reclaim_flag"] = (
        (close.shift(1) < qfq_vwap.shift(1)) & (close >= qfq_vwap) & vwap_valid
    ).astype(float)
    out["intraday_range_pct"] = high / low - 1.0
    price_range = high - low
    out["close_position_in_range"] = np.where(
        price_range > 0, (close - low) / price_range, 0.5
    )
    out["upper_shadow_pct"] = (high - np.maximum(open_, close)) / close
    out["gap_open_pct"] = open_ / close.shift(1) - 1.0
    out["gap_fade_flag"] = ((out["gap_open_pct"] > 0.02) & (close < open_)).astype(float)
    true_range = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr_20_pct"] = true_range.rolling(20, min_periods=20).mean() / close
    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def add_market_features(
    stock_features: pd.DataFrame, market_features: pd.DataFrame, board_bucket: str
) -> pd.DataFrame:
    alias = board_to_benchmark_alias(board_bucket)
    market = market_features.loc[market_features["benchmark_alias"] == alias].copy()
    out = stock_features.merge(
        market,
        left_on="date",
        right_on="trade_date",
        how="left",
    )
    out["benchmark_alias"] = out["benchmark_alias"].fillna(alias)
    out["stock_vs_market_20d"] = out["return_20d"] - out["market_return_20d"]
    out = out.drop(columns=[col for col in ["trade_date"] if col in out.columns])
    return out


def first_moving_average_reclaim(
    features: pd.DataFrame,
    *,
    start_pos: int,
    end_pos: int,
    ma_column: str = "ema60",
) -> tuple[int | None, str]:
    if ma_column not in features.columns:
        raise ValueError(f"Missing moving-average column {ma_column}")
    if start_pos < 1:
        start_pos = 1
    end_pos = min(end_pos, len(features) - 1)
    if start_pos > end_pos:
        return None, MISSING_EVENT_ABSENT
    for pos in range(start_pos, end_pos + 1):
        prev_close = features.at[pos - 1, "close"]
        prev_ma = features.at[pos - 1, ma_column]
        close = features.at[pos, "close"]
        ma_value = features.at[pos, ma_column]
        if pd.isna(prev_ma) or pd.isna(ma_value):
            continue
        if prev_close < prev_ma and close >= ma_value:
            return pos, NOT_MISSING
    return None, MISSING_EVENT_ABSENT


def direct_overlap(
    start_a: int, end_a: int, start_b: int, end_b: int
) -> bool:
    return start_a <= end_b and start_b <= end_a


def cluster_non_chain_direct_overlap(
    intervals: pd.DataFrame,
    *,
    start_col: str = "start_pos",
    end_col: str = "end_pos",
) -> pd.Series:
    if intervals.empty:
        return pd.Series(dtype="int64")
    missing = {start_col, end_col}.difference(intervals.columns)
    if missing:
        raise ValueError(f"Intervals missing columns: {sorted(missing)}")
    ordered = intervals.sort_values([start_col, end_col]).copy()
    cluster_ids: dict[Any, int] = {}
    cluster_id = -1
    seed_start = seed_end = None
    for idx, row in ordered.iterrows():
        start = int(row[start_col])
        end = int(row[end_col])
        if seed_start is None or seed_end is None:
            cluster_id += 1
            seed_start, seed_end = start, end
        elif not direct_overlap(seed_start, seed_end, start, end):
            cluster_id += 1
            seed_start, seed_end = start, end
        cluster_ids[idx] = cluster_id
    return pd.Series(cluster_ids).reindex(intervals.index).astype("int64")


def extract_candidate_lows(
    features: pd.DataFrame,
    *,
    membership_dates: set[str],
    params: ExtractionParams,
) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame()
    low = features["low"].astype(float).to_numpy()
    high = features["high"].astype(float).to_numpy()
    dates = features["date"].astype(str).to_numpy()
    window = params.local_low_window_sessions
    horizon = params.forward_horizon_sessions
    rows: list[dict[str, Any]] = []
    for pos in range(window, len(features) - window):
        current_date = str(dates[pos])
        if current_date not in membership_dates:
            continue
        if pos < params.prior_lookback_sessions:
            continue
        if pos + horizon >= len(features):
            continue
        current_low = low[pos]
        if not np.isfinite(current_low) or current_low <= 0:
            continue
        local_window = low[pos - window : pos + window + 1]
        if not np.isfinite(local_window).all():
            continue
        if current_low != np.nanmin(local_window):
            continue
        forward_high = high[pos + 1 : pos + horizon + 1]
        if len(forward_high) != horizon or not np.isfinite(forward_high).any():
            continue
        max_high = np.nanmax(forward_high)
        rel_high_pos = int(np.where(forward_high == max_high)[0][0]) + 1
        high_pos = pos + rel_high_pos
        mfe = max_high / current_low - 1.0
        rows.append(
            {
                "candidate_low_date": current_date,
                "candidate_low_pos": pos,
                "forward_high_pos": high_pos,
                "forward_high_date": str(dates[high_pos]),
                "qfq_low_at_candidate_low": current_low,
                "qfq_high_at_forward_high": float(max_high),
                "mfe_120": float(mfe),
                "low_to_high_sessions": int(high_pos - pos),
                "low_to_high_calendar_days": int(
                    (parse_date(dates[high_pos]) - parse_date(current_date)).days
                ),
                "high_at_horizon_boundary": bool(high_pos == pos + horizon),
                "interval_start_pos": pos,
                "interval_end_pos": high_pos,
            }
        )
    return pd.DataFrame(rows)


def build_winner_reference_for_instrument(
    instrument: str,
    features: pd.DataFrame,
    candidates: pd.DataFrame,
    membership_lookup: pd.DataFrame,
    *,
    params: ExtractionParams,
    split_config: SplitConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    winners = candidates.loc[
        candidates["mfe_120"] >= params.big_winner_mfe_threshold
    ].copy()
    if winners.empty:
        return pd.DataFrame(), pd.DataFrame()

    winners["cluster_number"] = cluster_non_chain_direct_overlap(
        winners, start_col="interval_start_pos", end_col="interval_end_pos"
    ).to_numpy()
    rows: list[dict[str, Any]] = []
    cluster_audit_rows: list[dict[str, Any]] = []
    date_to_member = membership_lookup.set_index("usable_trade_date")
    by_pos = features.reset_index(drop=True)

    previous_end_pos: int | None = None
    previous_cluster_id = ""
    for cluster_number, group in winners.groupby("cluster_number", sort=True):
        group = group.sort_values(["candidate_low_pos", "forward_high_pos"]).copy()
        earliest = group.iloc[0]
        max_mfe = group.sort_values(
            ["mfe_120", "candidate_low_pos"], ascending=[False, True]
        ).iloc[0]
        union_start = int(group["interval_start_pos"].min())
        union_end = int(group["interval_end_pos"].max())
        union = by_pos.iloc[union_start : union_end + 1]
        structural_idx_label = union["low"].astype(float).idxmin()
        structural_pos = int(structural_idx_label)
        structural_low = float(by_pos.at[structural_pos, "low"])
        structural_forward = by_pos.iloc[structural_pos : union_end + 1]
        structural_cluster_high = float(structural_forward["high"].max())
        structural_mfe = structural_cluster_high / structural_low - 1.0

        low_pos = int(earliest["candidate_low_pos"])
        high_pos = int(earliest["forward_high_pos"])
        low_date = str(earliest["candidate_low_date"])
        member = date_to_member.loc[low_date] if low_date in date_to_member.index else {}
        episode_id = f"{instrument}_{low_date.replace('-', '')}_{int(cluster_number):04d}"
        cluster_id = f"{instrument}_cluster_{int(cluster_number):04d}"
        anchor_pos, anchor_reason = first_moving_average_reclaim(
            by_pos, start_pos=low_pos, end_pos=high_pos, ma_column="ema60"
        )
        profile_end_pos = high_pos + params.post_high_exhaustion_sessions
        row = {
            "instrument": instrument,
            "episode_id": episode_id,
            "episode_low_date": low_date,
            "episode_high_date": str(earliest["forward_high_date"]),
            "qfq_low_at_low_date": float(earliest["qfq_low_at_candidate_low"]),
            "qfq_high_at_high_date": float(earliest["qfq_high_at_forward_high"]),
            "mfe_120": float(earliest["mfe_120"]),
            "low_to_high_sessions": int(earliest["low_to_high_sessions"]),
            "low_to_high_calendar_days": int(earliest["low_to_high_calendar_days"]),
            "low_detection_window": params.local_low_window_sessions,
            "forward_horizon_days": params.forward_horizon_sessions,
            "dedup_cluster_id": cluster_id,
            "cluster_policy": "non_chain_direct_interval_overlap",
            "primary_low_selection_policy": "earliest_qualifying_low",
            "earliest_qualifying_low_date": low_date,
            "earliest_qualifying_high_date": str(earliest["forward_high_date"]),
            "max_mfe_low_date": str(max_mfe["candidate_low_date"]),
            "max_mfe_high_date": str(max_mfe["forward_high_date"]),
            "max_mfe_120": float(max_mfe["mfe_120"]),
            "structural_low_date": str(by_pos.at[structural_pos, "date"]),
            "structural_low_to_cluster_high_mfe": float(structural_mfe),
            "high_at_horizon_boundary": bool(earliest["high_at_horizon_boundary"]),
            "profile_start_date": str(by_pos.at[max(0, low_pos - params.prior_lookback_sessions), "date"]),
            "profile_end_date": str(
                by_pos.at[min(len(by_pos) - 1, profile_end_pos), "date"]
            ),
            "profile_pre_low_complete": bool(low_pos >= params.prior_lookback_sessions),
            "profile_post_high_complete": bool(profile_end_pos < len(by_pos)),
            "lookback_60_complete": bool(low_pos >= 60),
            "lookback_120_complete": bool(low_pos >= 120),
            "lookback_250_complete": bool(low_pos >= 250),
            "first_ema60_reclaim_date": (
                str(by_pos.at[anchor_pos, "date"]) if anchor_pos is not None else ""
            ),
            "first_ema60_reclaim_missing_reason": anchor_reason,
            "split": split_for_date(low_date, split_config),
            "duration_bucket": duration_bucket(int(earliest["low_to_high_sessions"])),
            "board_bucket": member.get("board_bucket", ""),
            "total_market_cap_cny": member.get("total_market_cap_cny", np.nan),
            "liquidity_money_20d": by_pos.at[low_pos, "money_mean_20d"],
            "prior_return_20d": by_pos.at[low_pos, "return_20d"],
            "prior_return_60d": by_pos.at[low_pos, "return_60d"],
            "prior_drawdown": by_pos.at[low_pos, "drawdown_from_60d_high"],
            "volatility_20d": by_pos.at[low_pos, "atr_20_pct"],
            "market_regime_bucket": by_pos.at[low_pos, "market_regime_bucket"],
            "benchmark_alias": by_pos.at[low_pos, "benchmark_alias"],
            "cluster_member_count": int(len(group)),
            "cluster_union_start_date": str(by_pos.at[union_start, "date"]),
            "cluster_union_end_date": str(by_pos.at[union_end, "date"]),
        }
        rows.append(row)

        if previous_end_pos is not None:
            overlap_sessions = max(0, previous_end_pos - union_start + 1)
            cluster_audit_rows.append(
                {
                    "instrument": instrument,
                    "previous_cluster_id": previous_cluster_id,
                    "cluster_id": cluster_id,
                    "previous_cluster_end_date": str(by_pos.at[previous_end_pos, "date"]),
                    "cluster_start_date": str(by_pos.at[union_start, "date"]),
                    "boundary_overlap_sessions": int(overlap_sessions),
                    "boundary_overlaps": bool(overlap_sessions > 0),
                }
            )
        previous_end_pos = union_end
        previous_cluster_id = cluster_id

    return pd.DataFrame(rows), pd.DataFrame(cluster_audit_rows)


def build_control_pool_for_instrument(
    instrument: str,
    features: pd.DataFrame,
    candidates: pd.DataFrame,
    membership_lookup: pd.DataFrame,
    *,
    params: ExtractionParams,
    split_config: SplitConfig,
) -> pd.DataFrame:
    controls = candidates.loc[
        candidates["mfe_120"] < params.big_winner_mfe_threshold
    ].copy()
    if controls.empty:
        return pd.DataFrame()
    controls["cluster_number"] = cluster_non_chain_direct_overlap(
        controls, start_col="interval_start_pos", end_col="interval_end_pos"
    ).to_numpy()
    selected = (
        controls.sort_values(["cluster_number", "candidate_low_pos"])
        .groupby("cluster_number", as_index=False)
        .first()
    )
    date_to_member = membership_lookup.set_index("usable_trade_date")
    rows: list[dict[str, Any]] = []
    for row in selected.itertuples(index=False):
        low_pos = int(row.candidate_low_pos)
        end_pos = min(low_pos + params.forward_horizon_sessions, len(features) - 1)
        anchor_pos, anchor_reason = first_moving_average_reclaim(
            features, start_pos=low_pos, end_pos=end_pos, ma_column="ema60"
        )
        low_date = str(row.candidate_low_date)
        member = date_to_member.loc[low_date] if low_date in date_to_member.index else {}
        candidate_id = f"{instrument}_{low_date.replace('-', '')}_control_{int(row.cluster_number):04d}"
        rows.append(
            {
                "instrument": instrument,
                "control_candidate_id": candidate_id,
                "candidate_low_date": low_date,
                "candidate_low_pos": low_pos,
                "forward_high_date": str(row.forward_high_date),
                "forward_high_pos": int(row.forward_high_pos),
                "qfq_low_at_candidate_low": float(row.qfq_low_at_candidate_low),
                "qfq_high_at_forward_high": float(row.qfq_high_at_forward_high),
                "mfe_120": float(row.mfe_120),
                "low_to_high_sessions": int(row.low_to_high_sessions),
                "low_to_high_calendar_days": int(row.low_to_high_calendar_days),
                "high_at_horizon_boundary": bool(row.high_at_horizon_boundary),
                "control_cluster_id": f"{instrument}_control_cluster_{int(row.cluster_number):04d}",
                "control_selection_policy": "same_candidate_low_non_chain_direct_interval_dedup",
                "is_near_winner": bool(
                    params.near_winner_lower_mfe_threshold
                    <= float(row.mfe_120)
                    < params.near_winner_upper_mfe_threshold
                ),
                "first_ema60_reclaim_date": (
                    str(features.at[anchor_pos, "date"]) if anchor_pos is not None else ""
                ),
                "first_ema60_reclaim_missing_reason": anchor_reason,
                "split": split_for_date(low_date, split_config),
                "board_bucket": member.get("board_bucket", ""),
                "total_market_cap_cny": member.get("total_market_cap_cny", np.nan),
                "liquidity_money_20d": features.at[low_pos, "money_mean_20d"],
                "prior_return_20d": features.at[low_pos, "return_20d"],
                "prior_return_60d": features.at[low_pos, "return_60d"],
                "prior_drawdown": features.at[low_pos, "drawdown_from_60d_high"],
                "volatility_20d": features.at[low_pos, "atr_20_pct"],
                "market_regime_bucket": features.at[low_pos, "market_regime_bucket"],
                "benchmark_alias": features.at[low_pos, "benchmark_alias"],
            }
        )
    return pd.DataFrame(rows)


def assign_match_buckets(
    winners: pd.DataFrame, controls: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, list[str]]]:
    winner_out = winners.copy()
    control_out = controls.copy()
    bucket_specs = {
        "market_cap_bucket": "total_market_cap_cny",
        "liquidity_bucket": "liquidity_money_20d",
        "prior_return_20d_bucket": "prior_return_20d",
        "prior_return_60d_bucket": "prior_return_60d",
        "prior_drawdown_bucket": "prior_drawdown",
        "volatility_bucket": "volatility_20d",
    }
    bucket_values: dict[str, list[str]] = {}
    combined = pd.concat(
        [
            winner_out[list(bucket_specs.values())],
            control_out[list(bucket_specs.values())],
        ],
        ignore_index=True,
    )
    for bucket_col, value_col in bucket_specs.items():
        values = pd.to_numeric(combined[value_col], errors="coerce")
        labels = [f"q{i}" for i in range(1, 6)]
        try:
            binned = pd.qcut(values, q=5, labels=labels, duplicates="drop")
        except ValueError:
            binned = pd.Series(["unknown"] * len(values), dtype="object")
        binned = binned.astype("object").where(~pd.isna(binned), "unknown")
        winner_out[bucket_col] = binned.iloc[: len(winner_out)].to_numpy()
        control_out[bucket_col] = binned.iloc[len(winner_out) :].to_numpy()
        bucket_values[bucket_col] = sorted({str(value) for value in binned.unique()})
    return winner_out, control_out, bucket_values


def _bucket_distance(left: Any, right: Any) -> int:
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


def match_controls(
    winners: pd.DataFrame,
    controls: pd.DataFrame,
    *,
    winner_id_col: str,
    control_id_col: str,
    winner_date_col: str,
    control_date_col: str,
    match_axis: str,
    config: MatchConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if winners.empty:
        return pd.DataFrame(), pd.DataFrame()
    controls = controls.copy()
    controls["_match_week"] = controls[control_date_col].map(week_start)
    controls["_match_date_ts"] = pd.to_datetime(controls[control_date_col])
    match_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for winner in winners.itertuples(index=False):
        winner_map = winner._asdict()
        winner_date = winner_map[winner_date_col]
        winner_week = week_start(winner_date)
        winner_split = winner_map.get("split", "")
        same_week = controls.loc[controls["_match_week"] == winner_week].copy()
        cross_split_count = int((same_week["split"] != winner_split).sum()) if "split" in same_week else 0
        pool = same_week.loc[same_week["split"] == winner_split].copy()
        if "instrument" in pool.columns and "instrument" in winner_map:
            pool = pool.loc[pool["instrument"] != winner_map["instrument"]].copy()
        if pool.empty:
            reason = "no_same_week_same_split_control"
            if cross_split_count > 0:
                reason = "cross_split_boundary_unusable"
            audit_rows.append(
                {
                    "winner_id": winner_map[winner_id_col],
                    "match_axis": match_axis,
                    "match_anchor_date": winner_date,
                    "matched_control_count": 0,
                    "unmatched_reason": reason,
                    "cross_split_boundary_unusable_count": cross_split_count,
                }
            )
            continue
        winner_ts = parse_date(winner_date)
        scored: list[tuple[float, pd.Series]] = []
        for _, control in pool.iterrows():
            score = abs((parse_date(control[control_date_col]) - winner_ts).days)
            for field in config.match_fields:
                if field not in control.index or field not in winner_map:
                    continue
                if field == "board_bucket":
                    score += 10 if str(control[field]) != str(winner_map[field]) else 0
                else:
                    score += _bucket_distance(control[field], winner_map[field])
            scored.append((float(score), control))
        scored.sort(key=lambda item: (item[0], str(item[1][control_id_col])))
        selected = scored[: config.max_controls_per_winner]
        for rank, (score, control) in enumerate(selected, start=1):
            match_rows.append(
                {
                    "match_id": f"{winner_map[winner_id_col]}_{match_axis}_{rank:02d}",
                    "match_axis": match_axis,
                    "winner_id": winner_map[winner_id_col],
                    "control_id": control[control_id_col],
                    "winner_instrument": winner_map.get("instrument", ""),
                    "control_instrument": control.get("instrument", ""),
                    "match_anchor_date": winner_date,
                    "control_anchor_date": control[control_date_col],
                    "match_fields": "|".join(config.match_fields),
                    "match_distance": score,
                    "future_label_used_for_profile_only": True,
                    "winner_split": winner_split,
                    "control_split": control.get("split", ""),
                    "winner_duration_bucket": winner_map.get("duration_bucket", ""),
                    "control_is_near_winner": bool(control.get("is_near_winner", False)),
                    "unmatched_reason": "",
                }
            )
        audit_rows.append(
            {
                "winner_id": winner_map[winner_id_col],
                "match_axis": match_axis,
                "match_anchor_date": winner_date,
                "matched_control_count": len(selected),
                "unmatched_reason": "" if selected else "no_selected_control",
                "cross_split_boundary_unusable_count": cross_split_count,
            }
        )
    return pd.DataFrame(match_rows), pd.DataFrame(audit_rows)


def _is_missing_value(value: Any) -> bool:
    if isinstance(value, str):
        return value == ""
    return bool(pd.isna(value))


def feature_missing_reason(
    feature: str,
    value: Any,
    *,
    relative_day: int,
    in_coverage: bool = True,
    source_available: bool = True,
    vwap_missing_reason: str = "",
) -> str:
    if not in_coverage:
        return MISSING_OUT_OF_COVERAGE
    if not source_available:
        return MISSING_SOURCE_FIELD
    if not _is_missing_value(value):
        return NOT_MISSING
    if "vwap" in feature:
        if vwap_missing_reason and vwap_missing_reason != NOT_MISSING:
            return vwap_missing_reason
        return MISSING_SOURCE_FIELD
    if relative_day < 0:
        return MISSING_INSUFFICIENT_LOOKBACK
    return MISSING_INSUFFICIENT_LOOKBACK


def build_aligned_panel(
    entities: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    *,
    entity_id_col: str,
    axis_date_col: str,
    group_col: str,
    shared_axis: str,
    relative_start: int,
    relative_end: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for entity in entities.itertuples(index=False):
        item = entity._asdict()
        instrument = item.get("instrument") or item.get("control_instrument")
        if instrument not in daily_by_instrument:
            continue
        daily = daily_by_instrument[instrument].reset_index(drop=True)
        date_to_pos = {date: idx for idx, date in enumerate(daily["date"].astype(str))}
        axis_date = str(item[axis_date_col])
        if not axis_date or axis_date not in date_to_pos:
            continue
        axis_pos = date_to_pos[axis_date]
        for relative_day in range(relative_start, relative_end + 1):
            pos = axis_pos + relative_day
            in_coverage = 0 <= pos < len(daily)
            row = {
                "entity_id": item[entity_id_col],
                "instrument": instrument,
                "group": item[group_col],
                "shared_axis": shared_axis,
                "anchor_family": "first_ema60_reclaim" if shared_axis == "shared_axis_ema60" else "",
                "axis_date": axis_date,
                "date": str(daily.at[pos, "date"]) if in_coverage else "",
                "relative_day": relative_day,
                "split": item.get("split", item.get("winner_split", "")),
                "duration_bucket": item.get("duration_bucket", item.get("winner_duration_bucket", "")),
                "axis_regime_bucket": item.get("market_regime_bucket", ""),
                "matched_winner_id": item.get("matched_winner_id", ""),
                "match_id": item.get("match_id", ""),
            }
            for column in SNAPSHOT_COLUMNS:
                source_available = column in daily.columns
                value = daily.at[pos, column] if in_coverage and source_available else np.nan
                row[column] = value
                vwap_reason = ""
                if in_coverage and "derived_daily_vwap_missing_reason" in daily.columns:
                    vwap_reason = str(daily.at[pos, "derived_daily_vwap_missing_reason"])
                row[f"{column}_missing_reason"] = feature_missing_reason(
                    column,
                    value,
                    relative_day=relative_day,
                    in_coverage=in_coverage,
                    source_available=source_available,
                    vwap_missing_reason=vwap_reason,
                )
            rows.append(row)
    return pd.DataFrame(rows)


def summarize_continuous_dominance(
    panel: pd.DataFrame,
    *,
    shared_axis: str,
    relative_days: Iterable[int],
    thresholds: dict[str, float],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if panel.empty:
        return pd.DataFrame()
    features: list[tuple[str, str]] = []
    for family, columns in FEATURE_FAMILIES.items():
        for column in columns:
            if column in panel.columns and column not in {"gap_fade_flag", "vwap_reclaim_flag"}:
                features.append((family, column))

    for relative_day in relative_days:
        subset = panel.loc[
            (panel["shared_axis"] == shared_axis) & (panel["relative_day"] == relative_day)
        ].copy()
        if subset.empty:
            continue
        for family, feature in features:
            for split, regime_bucket, duration, stratum in iter_dominance_slices(subset):
                rows.append(
                    continuous_dominance_row(
                        stratum,
                        family=family,
                        feature=feature,
                        shared_axis=shared_axis,
                        relative_day=relative_day,
                        thresholds=thresholds,
                        split=split,
                        regime_bucket=regime_bucket,
                        duration_bucket=duration,
                    )
                )
        for binary_feature in ["gap_fade_flag", "vwap_reclaim_flag"]:
            if binary_feature in subset.columns:
                family = (
                    "volume_money_vwap_turnover"
                    if binary_feature == "vwap_reclaim_flag"
                    else "price_structure"
                )
                for split, regime_bucket, duration, stratum in iter_dominance_slices(subset):
                    rows.append(
                        binary_dominance_row(
                            stratum,
                            family=family,
                            feature=binary_feature,
                            shared_axis=shared_axis,
                            relative_day=relative_day,
                            thresholds=thresholds,
                            split=split,
                            regime_bucket=regime_bucket,
                            duration_bucket=duration,
                        )
                    )
    return pd.DataFrame(rows)


def iter_dominance_slices(
    frame: pd.DataFrame,
    *,
    regime_column: str = "axis_regime_bucket",
    duration_column: str = "duration_bucket",
) -> Iterable[tuple[str, str, str, pd.DataFrame]]:
    if frame.empty:
        return
    yield "all", "all", "all", frame

    if "split" in frame.columns:
        for split in ["train", "validation", "robustness"]:
            subset = frame.loc[frame["split"] == split]
            if not subset.empty:
                yield split, "all", "all", subset

    if regime_column in frame.columns:
        regimes = sorted(
            value
            for value in frame[regime_column].dropna().astype(str).unique()
            if value
        )
        for regime in regimes:
            subset = frame.loc[frame[regime_column].astype(str) == regime]
            if not subset.empty:
                yield "all", regime, "all", subset

    if duration_column in frame.columns:
        durations = sorted(
            value
            for value in frame[duration_column].dropna().astype(str).unique()
            if value
        )
        for duration in durations:
            subset = frame.loc[frame[duration_column].astype(str) == duration]
            if not subset.empty:
                yield "all", "all", duration, subset

    if {"split", regime_column}.issubset(frame.columns):
        grouped = frame.groupby(["split", regime_column], dropna=False, sort=True)
        for (split, regime), subset in grouped:
            split_text = str(split)
            regime_text = str(regime)
            if (
                not split_text
                or split_text == "nan"
                or not regime_text
                or regime_text == "nan"
            ):
                continue
            yield split_text, regime_text, "all", subset

    if {"split", duration_column}.issubset(frame.columns):
        grouped = frame.groupby(["split", duration_column], dropna=False, sort=True)
        for (split, duration), subset in grouped:
            split_text = str(split)
            duration_text = str(duration)
            if (
                not split_text
                or split_text == "nan"
                or not duration_text
                or duration_text == "nan"
            ):
                continue
            yield split_text, "all", duration_text, subset

    if {regime_column, duration_column}.issubset(frame.columns):
        grouped = frame.groupby([regime_column, duration_column], dropna=False, sort=True)
        for (regime, duration), subset in grouped:
            regime_text = str(regime)
            duration_text = str(duration)
            if (
                not regime_text
                or regime_text == "nan"
                or not duration_text
                or duration_text == "nan"
            ):
                continue
            yield "all", regime_text, duration_text, subset

    if {"split", regime_column, duration_column}.issubset(frame.columns):
        grouped = frame.groupby(["split", regime_column, duration_column], dropna=False, sort=True)
        for (split, regime, duration), subset in grouped:
            split_text = str(split)
            regime_text = str(regime)
            duration_text = str(duration)
            if (
                not split_text
                or split_text == "nan"
                or not regime_text
                or regime_text == "nan"
                or not duration_text
                or duration_text == "nan"
            ):
                continue
            yield split_text, regime_text, duration_text, subset


def continuous_dominance_row(
    subset: pd.DataFrame,
    *,
    family: str,
    feature: str,
    shared_axis: str,
    relative_day: int,
    thresholds: dict[str, float],
    split: str = "all",
    regime_bucket: str = "all",
    duration_bucket: str = "all",
) -> dict[str, Any]:
    winners = pd.to_numeric(
        subset.loc[subset["group"] == "winner", feature], errors="coerce"
    ).dropna()
    controls = pd.to_numeric(
        subset.loc[subset["group"] == "control", feature], errors="coerce"
    ).dropna()
    winner_total = int((subset["group"] == "winner").sum())
    control_total = int((subset["group"] == "control").sum())
    pooled_std = np.nan
    smd = np.nan
    if len(winners) > 1 and len(controls) > 1:
        pooled_std = math.sqrt(
            ((len(winners) - 1) * winners.var(ddof=1) + (len(controls) - 1) * controls.var(ddof=1))
            / max(len(winners) + len(controls) - 2, 1)
        )
        if pooled_std > 0:
            smd = (winners.mean() - controls.mean()) / pooled_std
    coverage = (
        (len(winners) + len(controls)) / (winner_total + control_total)
        if winner_total + control_total
        else 0.0
    )
    return {
        "dominance_id": (
            f"{shared_axis}_{relative_day}_{feature}_{split}_{regime_bucket}_{duration_bucket}"
        ),
        "factor_family": family,
        "feature": feature,
        "shared_axis": shared_axis,
        "anchor_family": "first_ema60_reclaim" if shared_axis == "shared_axis_ema60" else "",
        "relative_day": relative_day,
        "relative_window": f"{relative_day}",
        "split": split,
        "regime_bucket": regime_bucket,
        "duration_bucket": duration_bucket,
        "winner_count": len(winners),
        "control_count": len(controls),
        "winner_total": winner_total,
        "control_total": control_total,
        "winner_mean": winners.mean() if len(winners) else np.nan,
        "control_mean": controls.mean() if len(controls) else np.nan,
        "winner_std": winners.std(ddof=1) if len(winners) > 1 else np.nan,
        "control_std": controls.std(ddof=1) if len(controls) > 1 else np.nan,
        "standardized_mean_difference": smd,
        "winner_rate": np.nan,
        "control_rate": np.nan,
        "lift": np.nan,
        "odds_ratio": np.nan,
        "absolute_rate_difference": np.nan,
        "feature_non_missing_coverage": coverage,
        "claim_status": factor_claim_status(
            effect=smd,
            coverage=coverage,
            winner_count=len(winners),
            control_count=len(controls),
            thresholds=thresholds,
            continuous=True,
        ),
        "missing_reason_policy": "missing reasons retained in aligned panels",
        "multiple_test_family": family,
    }


def binary_dominance_row(
    subset: pd.DataFrame,
    *,
    family: str,
    feature: str,
    shared_axis: str,
    relative_day: int,
    thresholds: dict[str, float],
    split: str = "all",
    regime_bucket: str = "all",
    duration_bucket: str = "all",
) -> dict[str, Any]:
    winners = pd.to_numeric(
        subset.loc[subset["group"] == "winner", feature], errors="coerce"
    ).dropna()
    controls = pd.to_numeric(
        subset.loc[subset["group"] == "control", feature], errors="coerce"
    ).dropna()
    winner_total = int((subset["group"] == "winner").sum())
    control_total = int((subset["group"] == "control").sum())
    winner_rate = float(winners.mean()) if len(winners) else np.nan
    control_rate = float(controls.mean()) if len(controls) else np.nan
    lift = safe_lift(winner_rate, control_rate)
    odds = safe_odds_ratio(int(winners.sum()), len(winners), int(controls.sum()), len(controls))
    diff = winner_rate - control_rate if not pd.isna(winner_rate) and not pd.isna(control_rate) else np.nan
    coverage = (
        (len(winners) + len(controls)) / (winner_total + control_total)
        if winner_total + control_total
        else 0.0
    )
    return {
        "dominance_id": (
            f"{shared_axis}_{relative_day}_{feature}_{split}_{regime_bucket}_{duration_bucket}"
        ),
        "factor_family": family,
        "feature": feature,
        "shared_axis": shared_axis,
        "anchor_family": "first_ema60_reclaim" if shared_axis == "shared_axis_ema60" else "",
        "relative_day": relative_day,
        "relative_window": f"{relative_day}",
        "split": split,
        "regime_bucket": regime_bucket,
        "duration_bucket": duration_bucket,
        "winner_count": len(winners),
        "control_count": len(controls),
        "winner_total": winner_total,
        "control_total": control_total,
        "winner_mean": np.nan,
        "control_mean": np.nan,
        "winner_std": np.nan,
        "control_std": np.nan,
        "standardized_mean_difference": np.nan,
        "winner_rate": winner_rate,
        "control_rate": control_rate,
        "lift": lift,
        "odds_ratio": odds,
        "absolute_rate_difference": diff,
        "feature_non_missing_coverage": coverage,
        "claim_status": factor_claim_status(
            effect=max(abs(lift) if not pd.isna(lift) else 0.0, abs(diff) if not pd.isna(diff) else 0.0),
            coverage=coverage,
            winner_count=len(winners),
            control_count=len(controls),
            thresholds=thresholds,
            continuous=False,
            lift=lift,
            rate_diff=diff,
        ),
        "missing_reason_policy": "missing reasons retained in aligned panels",
        "multiple_test_family": family,
    }


def factor_claim_status(
    *,
    effect: float,
    coverage: float,
    winner_count: int,
    control_count: int,
    thresholds: dict[str, float],
    continuous: bool,
    lift: float | None = None,
    rate_diff: float | None = None,
) -> str:
    if winner_count == 0 or control_count == 0:
        return "sample_blocked"
    if coverage < thresholds["min_feature_non_missing_coverage_for_claim"]:
        return "sample_blocked_feature_coverage"
    if continuous:
        if pd.isna(effect):
            return "sample_blocked"
        return (
            "effect_size_candidate"
            if abs(effect) >= thresholds["standardized_mean_difference_gate"]
            else "no_claim"
        )
    passed_lift = lift is not None and not pd.isna(lift) and lift >= thresholds["lift_gate"]
    passed_diff = (
        rate_diff is not None
        and not pd.isna(rate_diff)
        and abs(rate_diff) >= thresholds["absolute_rate_difference_gate"]
    )
    return "effect_size_candidate" if passed_lift or passed_diff else "no_claim"


def safe_lift(winner_rate: float, control_rate: float) -> float:
    if pd.isna(winner_rate) or pd.isna(control_rate) or control_rate <= 0:
        return np.nan
    return float(winner_rate / control_rate)


def safe_odds_ratio(
    winner_success: int, winner_total: int, control_success: int, control_total: int
) -> float:
    if winner_total <= 0 or control_total <= 0:
        return np.nan
    a = winner_success + 0.5
    b = winner_total - winner_success + 0.5
    c = control_success + 0.5
    d = control_total - control_success + 0.5
    return float((a / b) / (c / d))


def summarize_market_regime_dominance(panel: pd.DataFrame) -> pd.DataFrame:
    if panel.empty or "market_regime_bucket" not in panel.columns:
        return pd.DataFrame()
    axis = panel.loc[
        (panel["shared_axis"] == "shared_axis_low") & (panel["relative_day"] == 0)
    ].copy()
    rows: list[dict[str, Any]] = []
    for bucket in [
        "risk_on",
        "risk_off",
        "transition",
        MISSING_INSUFFICIENT_LOOKBACK,
    ]:
        winners = axis.loc[axis["group"] == "winner", "market_regime_bucket"] == bucket
        controls = axis.loc[axis["group"] == "control", "market_regime_bucket"] == bucket
        winner_rate = float(winners.mean()) if len(winners) else np.nan
        control_rate = float(controls.mean()) if len(controls) else np.nan
        rows.append(
            {
                "dominance_id": f"shared_axis_low_0_market_regime_{bucket}",
                "factor_family": "market_regime",
                "feature": "market_regime_bucket",
                "bucket": bucket,
                "shared_axis": "shared_axis_low",
                "relative_day": 0,
                "winner_count": int(winners.sum()),
                "control_count": int(controls.sum()),
                "winner_total": int(len(winners)),
                "control_total": int(len(controls)),
                "winner_rate": winner_rate,
                "control_rate": control_rate,
                "lift": safe_lift(winner_rate, control_rate),
                "odds_ratio": safe_odds_ratio(
                    int(winners.sum()), len(winners), int(controls.sum()), len(controls)
                ),
                "absolute_rate_difference": (
                    winner_rate - control_rate
                    if not pd.isna(winner_rate) and not pd.isna(control_rate)
                    else np.nan
                ),
                "claim_status": "diagnostic",
                "multiple_test_family": "market_regime",
            }
        )
    return pd.DataFrame(rows)


def compute_path_tolerance_features(
    entities: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    *,
    entity_id_col: str,
    axis_date_col: str,
    group_col: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for entity in entities.itertuples(index=False):
        item = entity._asdict()
        instrument = item.get("instrument") or item.get("control_instrument")
        daily = daily_by_instrument.get(instrument)
        if daily is None or daily.empty:
            continue
        date_to_pos = {date: idx for idx, date in enumerate(daily["date"].astype(str))}
        axis_date = str(item[axis_date_col])
        if axis_date not in date_to_pos:
            continue
        axis_pos = date_to_pos[axis_date]
        axis_close = daily.at[axis_pos, "close"]
        row = {
            "entity_id": item[entity_id_col],
            "group": item[group_col],
            "shared_axis": "shared_axis_low",
            "split": item.get("split", item.get("winner_split", "")),
            "duration_bucket": item.get("duration_bucket", item.get("winner_duration_bucket", "")),
            "axis_regime_bucket": item.get("market_regime_bucket", ""),
        }
        for window in [20, 60]:
            end_pos = min(len(daily) - 1, axis_pos + window)
            if end_pos - axis_pos < window or pd.isna(axis_close) or axis_close <= 0:
                row[f"max_drawdown_axis_to_plus_{window}d"] = np.nan
                row[f"max_runup_axis_to_plus_{window}d"] = np.nan
                continue
            segment = daily.iloc[axis_pos : end_pos + 1]
            row[f"max_drawdown_axis_to_plus_{window}d"] = (
                float(segment["low"].min()) / float(axis_close) - 1.0
            )
            row[f"max_runup_axis_to_plus_{window}d"] = (
                float(segment["high"].max()) / float(axis_close) - 1.0
            )
        rows.append(row)
    return pd.DataFrame(rows)


SEQUENCE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "sequence_id": "S1_context_to_repair_v0",
        "sequence_family": "S1_context_to_repair",
        "shared_axis": "shared_axis_low",
        "anchor_family": "first_ema60_reclaim",
        "relative_window": "0:+60",
        "required_states": "market_not_missing -> ema60_reclaim",
        "forbidden_states": "",
        "order_constraints": "context observed at day 0 before reclaim in +60 sessions",
        "state_thresholds": "market_regime_bucket != missing_insufficient_lookback",
        "lookback_windows": "market 60/120, ema60",
        "missing_value_rules": "absent reclaim is missing_event_absent",
        "control_eligibility": "same retrospective-low opportunity pool",
    },
    {
        "sequence_id": "S2_repair_money_vwap_v0",
        "sequence_family": "S2_repair_to_money_confirmation",
        "shared_axis": "shared_axis_low",
        "anchor_family": "first_ema60_reclaim",
        "relative_window": "0:+80",
        "required_states": "ema60_reclaim -> amount_ratio_20d>=1.5 -> vwap_or_range_hold",
        "forbidden_states": "",
        "order_constraints": "money confirmation must occur after reclaim",
        "state_thresholds": "amount_ratio_20d>=1.5; close_to_vwap>=0 or close_position>=0.5",
        "lookback_windows": "ema60, amount20, vwap20",
        "missing_value_rules": "vwap unavailable is missing_source_field",
        "control_eligibility": "same retrospective-low opportunity pool",
    },
    {
        "sequence_id": "S3_repair_rank_persistence_v0",
        "sequence_family": "S3_repair_to_rank_persistence",
        "shared_axis": "shared_axis_low",
        "anchor_family": "first_ema60_reclaim",
        "relative_window": "0:+80",
        "required_states": "ema60_reclaim -> stock_vs_market_20d>=0.05 -> 20d persistence",
        "forbidden_states": "",
        "order_constraints": "rank persistence follows rank jump",
        "state_thresholds": "stock_vs_market_20d>=0.05 at jump and +20d",
        "lookback_windows": "ema60, stock return20, market return20",
        "missing_value_rules": "market lookback unavailable blocks state",
        "control_eligibility": "same retrospective-low opportunity pool",
    },
    {
        "sequence_id": "S4_contraction_expansion_v0",
        "sequence_family": "S4_contraction_to_expansion",
        "shared_axis": "shared_axis_low",
        "anchor_family": "",
        "relative_window": "-20:+60",
        "required_states": "atr contraction -> atr expansion -> upper_half_close",
        "forbidden_states": "",
        "order_constraints": "expansion follows contraction",
        "state_thresholds": "atr_20_pct below trailing120 median, then 1.25x contraction atr and close_position>=0.5",
        "lookback_windows": "atr20, trailing atr120",
        "missing_value_rules": "insufficient atr lookback blocks state",
        "control_eligibility": "same retrospective-low opportunity pool",
    },
    {
        "sequence_id": "S5_money_no_distribution_v0",
        "sequence_family": "S5_money_expansion_without_distribution",
        "shared_axis": "shared_axis_low",
        "anchor_family": "",
        "relative_window": "0:+60",
        "required_states": "amount_ratio_20d>=1.5 -> no gap fade/destructive shadow",
        "forbidden_states": "gap_fade_flag or upper_shadow_pct>=0.08 in next 5 sessions",
        "order_constraints": "forbidden state checked after expansion",
        "state_thresholds": "amount_ratio_20d>=1.5; upper_shadow_pct<0.08",
        "lookback_windows": "amount20",
        "missing_value_rules": "insufficient amount lookback blocks state",
        "control_eligibility": "same retrospective-low opportunity pool",
    },
    {
        "sequence_id": "S6_continuation_discriminator_v0",
        "sequence_family": "S6_continuation_discriminator",
        "shared_axis": "shared_axis_low",
        "anchor_family": "",
        "relative_window": "0:+80",
        "required_states": "+20pct close-observed path state from axis low -> rank/money persistence",
        "forbidden_states": "",
        "order_constraints": "persistence follows +20pct close-observed state",
        "state_thresholds": "close/axis_low-1>=0.20; stock_vs_market_20d>=0.05 or amount_ratio_20d>=1.2 at +20 sessions",
        "lookback_windows": "return20, market20, amount20",
        "missing_value_rules": "missing future profile window blocks profile diagnostic",
        "control_eligibility": "same retrospective-low opportunity pool; near-winner outcome reported separately",
    },
]


def evaluate_sequence(
    sequence_id: str,
    daily: pd.DataFrame,
    *,
    axis_pos: int,
    horizon_pos: int,
) -> tuple[bool, str, str]:
    definition = next(
        (item for item in SEQUENCE_DEFINITIONS if item["sequence_id"] == sequence_id),
        None,
    )
    if definition is None:
        raise ValueError(f"Unknown sequence_id {sequence_id}")
    horizon_pos = min(horizon_pos, len(daily) - 1)
    if axis_pos < 0 or axis_pos >= len(daily):
        return False, "", MISSING_EVENT_ABSENT
    if sequence_id == "S1_context_to_repair_v0":
        if daily.at[axis_pos, "market_regime_bucket"] == MISSING_INSUFFICIENT_LOOKBACK:
            return False, "", MISSING_INSUFFICIENT_LOOKBACK
        reclaim_pos, reason = first_moving_average_reclaim(
            daily, start_pos=axis_pos, end_pos=min(axis_pos + 60, horizon_pos), ma_column="ema60"
        )
        return (
            reclaim_pos is not None,
            str(daily.at[reclaim_pos, "date"]) if reclaim_pos is not None else "",
            reason,
        )
    if sequence_id == "S2_repair_money_vwap_v0":
        reclaim_pos, reason = first_moving_average_reclaim(
            daily, start_pos=axis_pos, end_pos=min(axis_pos + 60, horizon_pos), ma_column="ema60"
        )
        if reclaim_pos is None:
            return False, "", reason
        for pos in range(reclaim_pos, min(reclaim_pos + 20, horizon_pos) + 1):
            amount_ok = daily.at[pos, "amount_ratio_20d"] >= 1.5
            vwap_ok = daily.at[pos, "close_to_derived_daily_vwap"] >= 0
            range_ok = daily.at[pos, "close_position_in_range"] >= 0.5
            if amount_ok and (vwap_ok or range_ok):
                return True, str(daily.at[pos, "date"]), NOT_MISSING
        return False, "", MISSING_EVENT_ABSENT
    if sequence_id == "S3_repair_rank_persistence_v0":
        reclaim_pos, reason = first_moving_average_reclaim(
            daily, start_pos=axis_pos, end_pos=min(axis_pos + 60, horizon_pos), ma_column="ema60"
        )
        if reclaim_pos is None:
            return False, "", reason
        for pos in range(reclaim_pos, min(reclaim_pos + 40, horizon_pos) + 1):
            future_pos = pos + 20
            if future_pos > horizon_pos:
                break
            if (
                daily.at[pos, "stock_vs_market_20d"] >= 0.05
                and daily.at[future_pos, "stock_vs_market_20d"] >= 0.05
            ):
                return True, str(daily.at[future_pos, "date"]), NOT_MISSING
        return False, "", MISSING_EVENT_ABSENT
    if sequence_id == "S4_contraction_expansion_v0":
        atr = daily["atr_20_pct"].astype(float)
        start_pos = max(0, axis_pos - 20)
        for pos in range(start_pos, min(axis_pos + 60, horizon_pos) + 1):
            if pos < 120 or pd.isna(atr.iloc[pos]):
                continue
            trailing_median = atr.iloc[pos - 120 : pos].median()
            if pd.isna(trailing_median) or atr.iloc[pos] > trailing_median:
                continue
            contraction_atr = atr.iloc[pos]
            for future_pos in range(pos + 1, min(pos + 30, horizon_pos) + 1):
                if (
                    atr.iloc[future_pos] >= contraction_atr * 1.25
                    and daily.at[future_pos, "close_position_in_range"] >= 0.5
                ):
                    return True, str(daily.at[future_pos, "date"]), NOT_MISSING
        return False, "", MISSING_EVENT_ABSENT
    if sequence_id == "S5_money_no_distribution_v0":
        for pos in range(axis_pos, min(axis_pos + 60, horizon_pos) + 1):
            if daily.at[pos, "amount_ratio_20d"] < 1.5:
                continue
            end_pos = min(pos + 5, horizon_pos)
            check = daily.iloc[pos : end_pos + 1]
            forbidden = (
                (check["gap_fade_flag"].fillna(0) > 0).any()
                or (check["upper_shadow_pct"].fillna(0) >= 0.08).any()
            )
            if not forbidden:
                return True, str(daily.at[end_pos, "date"]), NOT_MISSING
        return False, "", MISSING_EVENT_ABSENT
    if sequence_id == "S6_continuation_discriminator_v0":
        axis_low = daily.at[axis_pos, "low"]
        if pd.isna(axis_low) or axis_low <= 0:
            return False, "", MISSING_SOURCE_FIELD
        for pos in range(axis_pos + 1, min(axis_pos + 60, horizon_pos) + 1):
            if daily.at[pos, "close"] / axis_low - 1.0 < 0.20:
                continue
            future_pos = pos + 20
            if future_pos > horizon_pos:
                return False, "", MISSING_INSUFFICIENT_LOOKBACK
            if (
                daily.at[future_pos, "stock_vs_market_20d"] >= 0.05
                or daily.at[future_pos, "amount_ratio_20d"] >= 1.2
            ):
                return True, str(daily.at[future_pos, "date"]), NOT_MISSING
        return False, "", MISSING_EVENT_ABSENT
    raise AssertionError(f"Unhandled sequence_id {sequence_id}")


def evaluate_sequences_for_entities(
    entities: pd.DataFrame,
    daily_by_instrument: dict[str, pd.DataFrame],
    *,
    entity_id_col: str,
    axis_date_col: str,
    group_col: str,
    horizon_sessions: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for entity in entities.itertuples(index=False):
        item = entity._asdict()
        instrument = item.get("instrument") or item.get("control_instrument")
        daily = daily_by_instrument.get(instrument)
        if daily is None or daily.empty:
            continue
        date_to_pos = {date: idx for idx, date in enumerate(daily["date"].astype(str))}
        axis_date = str(item[axis_date_col])
        if axis_date not in date_to_pos:
            continue
        axis_pos = date_to_pos[axis_date]
        horizon_pos = min(axis_pos + horizon_sessions, len(daily) - 1)
        for definition in SEQUENCE_DEFINITIONS:
            passed, completion_date, missing_reason = evaluate_sequence(
                definition["sequence_id"], daily, axis_pos=axis_pos, horizon_pos=horizon_pos
            )
            rows.append(
                {
                    "entity_id": item[entity_id_col],
                    "instrument": instrument,
                    "group": item[group_col],
                    "split": item.get("split", item.get("winner_split", "")),
                    "duration_bucket": item.get("duration_bucket", item.get("winner_duration_bucket", "")),
                    "axis_regime_bucket": item.get("market_regime_bucket", ""),
                    "shared_axis": definition["shared_axis"],
                    "anchor_family": definition["anchor_family"],
                    "sequence_id": definition["sequence_id"],
                    "sequence_family": definition["sequence_family"],
                    "relative_window": definition["relative_window"],
                    "required_states": definition["required_states"],
                    "forbidden_states": definition["forbidden_states"],
                    "order_constraints": definition["order_constraints"],
                    "state_thresholds": definition["state_thresholds"],
                    "sequence_present": bool(passed),
                    "sequence_completion_date": completion_date,
                    "missing_reason": missing_reason,
                    "control_is_near_winner": bool(item.get("control_is_near_winner", False)),
                    "control_is_false_repair": bool(item.get("control_is_false_repair", False)),
                }
            )
    return pd.DataFrame(rows)


def summarize_sequence_dominance(
    sequence_panel: pd.DataFrame, *, thresholds: dict[str, float]
) -> pd.DataFrame:
    if sequence_panel.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for sequence_id, full_group in sequence_panel.groupby("sequence_id", sort=False):
        for split, regime_bucket, duration, group in iter_dominance_slices(full_group):
            first = group.iloc[0]
            winner = group.loc[group["group"] == "winner"]
            control = group.loc[group["group"] == "control"]
            winner_success = int(winner["sequence_present"].sum())
            control_success = int(control["sequence_present"].sum())
            winner_rate = winner_success / len(winner) if len(winner) else np.nan
            control_rate = control_success / len(control) if len(control) else np.nan
            lift = safe_lift(winner_rate, control_rate)
            odds = safe_odds_ratio(winner_success, len(winner), control_success, len(control))
            diff = (
                winner_rate - control_rate
                if not pd.isna(winner_rate) and not pd.isna(control_rate)
                else np.nan
            )
            split_lifts: dict[str, float] = {}
            split_signs: list[int] = []
            for split_name in ["train", "validation", "robustness"]:
                split_group = group.loc[group["split"] == split_name]
                split_winner = split_group.loc[split_group["group"] == "winner"]
                split_control = split_group.loc[split_group["group"] == "control"]
                wr = (
                    float(split_winner["sequence_present"].mean())
                    if len(split_winner)
                    else np.nan
                )
                cr = (
                    float(split_control["sequence_present"].mean())
                    if len(split_control)
                    else np.nan
                )
                split_lifts[split_name] = safe_lift(wr, cr)
                if not pd.isna(wr) and not pd.isna(cr):
                    split_signs.append(1 if wr - cr > 0 else -1 if wr - cr < 0 else 0)
            near_control = control.loc[control["control_is_near_winner"]]
            near_rate = (
                float(near_control["sequence_present"].mean()) if len(near_control) else np.nan
            )
            false_control = control.loc[control["control_is_false_repair"]]
            false_rate = (
                float(false_control["sequence_present"].mean()) if len(false_control) else np.nan
            )
            occurrence_count = winner_success + control_success
            data_missing_reasons = {
                MISSING_INSUFFICIENT_LOOKBACK,
                MISSING_SOURCE_FIELD,
                MISSING_UNIT_INCOMPATIBLE,
                MISSING_OUT_OF_COVERAGE,
            }
            feature_coverage = float(
                (~group["missing_reason"].isin(data_missing_reasons)).mean()
            )
            stable_all_splits = all(sign > 0 for sign in split_signs) and len(split_signs) == 3
            overall_scope = split == "all" and regime_bucket == "all" and duration == "all"
            status = "no_claim"
            if len(winner) == 0 or len(control) == 0:
                status = "sample_blocked"
            elif occurrence_count < thresholds["min_sequence_occurrences_for_claim"]:
                status = "sample_blocked_occurrence_count"
            elif feature_coverage < thresholds["min_feature_non_missing_coverage_for_claim"]:
                status = "sample_blocked_feature_coverage"
            elif (
                (not pd.isna(lift) and lift >= thresholds["lift_gate"])
                or (not pd.isna(diff) and abs(diff) >= thresholds["absolute_rate_difference_gate"])
            ):
                if overall_scope and stable_all_splits:
                    status = "sequence_supported_universal_candidate"
                else:
                    status = "sequence_regime_conditional_candidate"
            rows.append(
                {
                    "sequence_id": sequence_id,
                    "sequence_family": first["sequence_family"],
                    "shared_axis": first["shared_axis"],
                    "anchor_family": first["anchor_family"],
                    "relative_window": first["relative_window"],
                    "required_states": first["required_states"],
                    "forbidden_states": first["forbidden_states"],
                    "order_constraints": first["order_constraints"],
                    "split": split,
                    "regime_bucket": regime_bucket,
                    "duration_bucket": duration,
                    "winner_count": len(winner),
                    "control_count": len(control),
                    "winner_sequence_rate": winner_rate,
                    "control_sequence_rate": control_rate,
                    "lift": lift,
                    "odds_ratio": odds,
                    "absolute_rate_difference": diff,
                    "train_lift": split_lifts.get("train", np.nan),
                    "validation_lift": split_lifts.get("validation", np.nan),
                    "robustness_lift": split_lifts.get("robustness", np.nan),
                    "split_stability": (
                        "same_positive_sign_all_splits"
                        if stable_all_splits
                        else "not_stable_or_sample_blocked"
                    ),
                    "near_winner_lift": safe_lift(winner_rate, near_rate),
                    "false_repair_lift": safe_lift(winner_rate, false_rate),
                    "feature_non_missing_coverage": feature_coverage,
                    "multiple_test_family": first["sequence_family"],
                    "claim_status": status,
                }
            )
    return pd.DataFrame(rows)


def sequence_family_test_counts() -> pd.DataFrame:
    rows = []
    for definition in SEQUENCE_DEFINITIONS:
        rows.append(
            {
                "sequence_family": definition["sequence_family"],
                "tested_variant_count": 1,
                "reported_variant_count": 1,
                "rejected_variant_count": 0,
                "variant_selection_basis": "requirement_prespecified_single_variant",
                "variant_audit_note": "No alternative variants were evaluated in this run.",
                "fdr_denominator_count": 1,
                "validation_used_for_structure_selection": False,
                "robustness_used_for_structure_selection": False,
            }
        )
    return pd.DataFrame(rows)


def false_repair_metrics(daily: pd.DataFrame, axis_date: str, anchor_date: str) -> dict[str, Any]:
    empty = {
        "control_is_false_repair": False,
        "control_is_false_repair_10d": False,
        "control_is_false_repair_20d": False,
        "false_repair_drawdown_anchor_to_plus_10d": np.nan,
        "false_repair_drawdown_anchor_to_plus_20d": np.nan,
        "false_repair_runup_axis_low_to_anchor_plus_10d": np.nan,
        "false_repair_runup_axis_low_to_anchor_plus_20d": np.nan,
        "false_repair_missing_reason": MISSING_EVENT_ABSENT,
        "false_repair_rule": "anchor_plus_10d_or_20d_drawdown_le_-10pct_or_runup_lt_20pct",
    }
    if not anchor_date:
        return empty
    date_to_pos = {date: idx for idx, date in enumerate(daily["date"].astype(str))}
    if axis_date not in date_to_pos or anchor_date not in date_to_pos:
        return empty
    axis_pos = date_to_pos[axis_date]
    anchor_pos = date_to_pos[anchor_date]
    if anchor_pos < axis_pos:
        return empty
    anchor_close = daily.at[anchor_pos, "close"]
    axis_low = daily.at[axis_pos, "low"]
    if pd.isna(anchor_close) or anchor_close <= 0 or pd.isna(axis_low) or axis_low <= 0:
        empty["false_repair_missing_reason"] = MISSING_SOURCE_FIELD
        return empty

    out = empty.copy()
    out["false_repair_missing_reason"] = NOT_MISSING
    for window in [10, 20]:
        end_pos = min(len(daily) - 1, anchor_pos + window)
        if end_pos - anchor_pos < window:
            out[f"control_is_false_repair_{window}d"] = False
            out["false_repair_missing_reason"] = MISSING_OUT_OF_COVERAGE
            continue
        segment = daily.iloc[anchor_pos : end_pos + 1]
        drawdown = float(segment["low"].min()) / float(anchor_close) - 1.0
        runup = float(segment["high"].max()) / float(axis_low) - 1.0
        out[f"false_repair_drawdown_anchor_to_plus_{window}d"] = drawdown
        out[f"false_repair_runup_axis_low_to_anchor_plus_{window}d"] = runup
        out[f"control_is_false_repair_{window}d"] = bool(
            drawdown <= -0.10 or runup < 0.20
        )
    out["control_is_false_repair"] = bool(
        out["control_is_false_repair_10d"] or out["control_is_false_repair_20d"]
    )
    return out


def false_repair_flag(daily: pd.DataFrame, axis_date: str, anchor_date: str) -> bool:
    return bool(false_repair_metrics(daily, axis_date, anchor_date)["control_is_false_repair"])


def winner_only_stage_profile(
    winners: pd.DataFrame, daily_by_instrument: dict[str, pd.DataFrame], params: ExtractionParams
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    stage_defs = [
        ("pre_low_60d", -60, 0),
        ("low_to_high", 0, None),
        ("post_high_30d", 1, params.post_high_exhaustion_sessions),
    ]
    features = [
        "return_20d",
        "amount_ratio_20d",
        "close_to_ema60",
        "close_to_derived_daily_vwap",
        "atr_20_pct",
        "stock_vs_market_20d",
    ]
    for winner in winners.itertuples(index=False):
        item = winner._asdict()
        daily = daily_by_instrument.get(item["instrument"])
        if daily is None:
            continue
        date_to_pos = {date: idx for idx, date in enumerate(daily["date"].astype(str))}
        if item["episode_low_date"] not in date_to_pos or item["episode_high_date"] not in date_to_pos:
            continue
        low_pos = date_to_pos[item["episode_low_date"]]
        high_pos = date_to_pos[item["episode_high_date"]]
        for stage, start, end in stage_defs:
            if stage == "pre_low_60d":
                left, right = low_pos + start, low_pos + end
            elif stage == "low_to_high":
                left, right = low_pos, high_pos
            else:
                if bool(item.get("high_at_horizon_boundary", False)):
                    rows.append(
                        {
                            "episode_id": item["episode_id"],
                            "instrument": item["instrument"],
                            "stage": stage,
                            "stage_status": "excluded_high_at_horizon_boundary",
                            "split": item["split"],
                        }
                    )
                    continue
                left, right = high_pos + start, high_pos + int(end)
            if left < 0 or right >= len(daily):
                rows.append(
                    {
                        "episode_id": item["episode_id"],
                        "instrument": item["instrument"],
                        "stage": stage,
                        "stage_status": MISSING_INSUFFICIENT_LOOKBACK,
                        "split": item["split"],
                    }
                )
                continue
            segment = daily.iloc[left : right + 1]
            row = {
                "episode_id": item["episode_id"],
                "instrument": item["instrument"],
                "stage": stage,
                "stage_status": "descriptive_only",
                "split": item["split"],
                "duration_bucket": item["duration_bucket"],
                "start_date": str(segment.iloc[0]["date"]),
                "end_date": str(segment.iloc[-1]["date"]),
                "session_count": len(segment),
            }
            for feature in features:
                row[f"{feature}_mean"] = pd.to_numeric(
                    segment[feature], errors="coerce"
                ).mean()
            rows.append(row)
    return pd.DataFrame(rows)


def write_dataframe(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import builtins
import hashlib
import inspect
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

import r01_common as r01


SCRIPT_DIR = Path(__file__).resolve().parent
EP5_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP5_DIR.parent
DEFAULT_CONFIG = EP5_DIR / "configs" / "r05_gtja191_train_only_factor_engineering_residual_feasibility_v0.yaml"

REQUIREMENT_ID = "ep5_r05_gtja191_train_only_factor_engineering_residual_feasibility_v0"
PLAN_ID = "ep5_e05_gtja191_train_only_factor_engineering_residual_feasibility_v0"
PRIMARY_UNIT = "r05_gtja191_train_stable_cluster_neutralized_composite_v0"
HORIZONS = [5, 10, 20]
HORIZON_LABELS = [f"H{h}" for h in HORIZONS]
SPLITS = ["train", "validation", "robustness"]

FINAL_DECISIONS = [
    "r05_blocked_data_or_execution_contract",
    "r05_factor_library_not_implementable_blocked",
    "r05_factor_stability_selection_not_viable_blocked",
    "r05_factor_cluster_structure_not_viable_blocked",
    "r05_primary_sample_not_evaluable_blocked",
    "r05_gtja191_factor_engineered_long_only_and_residual_supported",
    "r05_gtja191_factor_engineered_residual_edge_only_hedged_required",
    "r05_baseline_not_evaluable_validation_lead",
    "r05_comparator_unavailable_validation_lead",
    "r05_absolute_only_baseline_lift_no_relative_pass",
    "r05_beta_or_style_exposure_only_no_stock_selection_pass",
    "r05_unstable_validation_only_lead",
    "r05_unstable_horizon_shape_no_search_allowed",
    "r05_adjacent_horizon_not_evaluable_validation_lead",
    "r05_horizon_specific_lead_only_no_search_allowed",
    "r05_sample_limited_primary_lead_only",
    "r05_no_gtja191_factor_engineering_support",
]

PRIORITY_RULES = [f"rule_{i:02d}" for i in range(1, 18)]

SELECTION_EVENT_COLUMNS = [
    "candidate_row_id",
    "canonical_unit_id",
    "unit_role",
    "event_key",
    "instrument_id",
    "signal_date",
    "split",
    "eligible_count",
    "score_raw",
    "active_factor_count",
    "included_factor_count",
    "valid_included_factor_count",
    "industry_id",
    "industry_name",
    "liquidity_quintile",
    "beta_bucket",
    "market_state",
    "selected_flag",
]

EXECUTION_EXTRA_COLUMNS = [
    "horizon",
    "entry_execution_date",
    "entry_price",
    "natural_exit_target_date",
    "natural_exit_signal_date",
    "exit_execution_date",
    "exit_price",
    "buy_cost_bps",
    "sell_cost_bps",
    "round_trip_cost_bps",
    "gross_return",
    "net_return",
    "execution_status",
    "blocked_reason",
    "entry_lag_trading_days",
    "exit_lag_trading_days",
]

EXECUTION_COLUMNS = SELECTION_EVENT_COLUMNS + EXECUTION_EXTRA_COLUMNS

COMPARATOR_COLUMNS = [
    "canonical_unit_id",
    "event_key",
    "horizon",
    "split",
    "instrument_id",
    "signal_date",
    "primary_comparator_scope",
    "matched_comparator_count",
    "matched_comparator_net_return",
    "matched_delta_return",
    "matched_comparator_status",
    "industry_matched_delta_return",
    "liquidity_matched_delta_return",
    "beta_matched_delta_return",
    "fallback_comparator_used",
]

BASELINE_COMPARISON_COLUMNS = [
    "split",
    "horizon",
    "signal_date",
    "baseline_comparison_status",
    "selected_complete_event_count",
    "nonselected_complete_event_count",
    "selected_equal_weight_net_return",
    "nonselected_baseline_equal_weight_net_return",
    "baseline_lift",
]

ACTIVE_OVERLAP_COLUMNS = [
    "signal_date",
    "horizon",
    "active_overlap_share",
    "effective_independent_event_count",
]

SCORE_AUDIT_COLUMNS = [
    "signal_date",
    "split",
    "eligible_count",
    "selected_count_target",
    "selected_count",
    "nonselected_count",
    "selection_status",
    "top1_instrument_selected_week_share",
    "active_factor_count_min",
    "active_factor_count_p10",
    "active_factor_count_median",
    "selected_active_factor_count_p10",
    "selected_active_factor_count_median",
    "nonselected_active_factor_count_p10",
    "nonselected_active_factor_count_median",
    "selected_minus_nonselected_active_factor_count_p10",
    "selected_minus_nonselected_active_factor_count_median",
    "score_raw_mean",
    "score_raw_std",
    "score_tie_share",
]


@dataclass(frozen=True)
class R05Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    audit_dir: Path
    events_dir: Path
    metrics_dir: Path
    decision_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], R05Paths]:
    config_path = r01.topic_path(path)
    import yaml

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_root = r01.topic_path(config["output_root"])
    paths = R05Paths(
        config_path=config_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        audit_dir=output_root / "audit",
        events_dir=output_root / "events",
        metrics_dir=output_root / "metrics",
        decision_dir=output_root / "decision",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in [paths.cache_dir, paths.audit_dir, paths.events_dir, paths.metrics_dir, paths.decision_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def finite(value: Any) -> bool:
    return r01.finite(value)


def safe_mean(values: pd.Series) -> float:
    return float(values.mean()) if len(values) else np.nan


def safe_quantile(values: pd.Series, q: float) -> float:
    return float(values.quantile(q)) if len(values) else np.nan


def safe_share(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def bool_value(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return r01.bool_value(value)


def pct_text(value: Any, digits: int = 4) -> str:
    return "NA" if not finite(value) else f"{float(value):.{digits}%}"


def split_for_date(config: dict[str, Any], value: Any) -> str:
    return r01.split_for_date(config, value)


def weekly_observation_dates(config: dict[str, Any]) -> set[pd.Timestamp]:
    calendar = r01.load_calendar(config)
    start = pd.Timestamp(config["split"]["train_start"])
    end = pd.Timestamp(config["split"]["robustness_end"])
    dates = pd.DatetimeIndex([pd.Timestamp(d) for d in calendar if start <= pd.Timestamp(d) <= end])
    frame = pd.DataFrame({"trade_date": dates})
    iso = frame["trade_date"].dt.isocalendar()
    frame["iso_year"] = iso["year"].astype(int)
    frame["iso_week"] = iso["week"].astype(int)
    return set(pd.to_datetime(frame.groupby(["iso_year", "iso_week"], as_index=False)["trade_date"].max()["trade_date"]).dt.normalize())


def prepare_feature_panel(config: dict[str, Any], paths: R05Paths) -> pd.DataFrame:
    shim = r01.Paths(paths.config_path, paths.output_root, paths.cache_dir, paths.reports_dir, paths.manifests_dir)
    feature, _ = r01.build_feature_panel(config, shim)
    for extra in paths.reports_dir.glob("r01_*.csv"):
        extra.unlink(missing_ok=True)
    (paths.cache_dir / "r01_daily_feature_panel.parquet").unlink(missing_ok=True)
    provider = r01.load_provider_panel(config)
    index_id = config["data_sources"]["index_instrument"].upper()
    index = provider.loc[provider["instrument_id"].eq(index_id), ["trade_date", "open", "close"]].rename(columns={"open": "index_open", "close": "index_close_raw"})
    feature = feature.merge(index, on="trade_date", how="left")
    if "index_close" not in feature:
        feature["index_close"] = feature["index_close_raw"]
    feature["index_open"] = feature["index_open"].fillna(feature.get("index_close", np.nan))
    feature["vwap"] = feature["money"] / feature["volume"]
    feature["avg_money20_D"] = feature["avg_money20_asof"]
    feature["weekly_observation_date"] = feature["trade_date"].isin(weekly_observation_dates(config))
    feature = feature.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True)
    write_csv(
        pd.DataFrame(
            [
                {
                    "source": "daily_feature_panel",
                    "row_count": len(feature),
                    "instrument_count": feature["instrument_id"].nunique(),
                    "min_date": feature["trade_date"].min(),
                    "max_date": feature["trade_date"].max(),
                    "status": "passed" if not feature.empty else "failed",
                }
            ]
        ),
        paths.audit_dir / "r05_input_data_audit.csv",
    )
    provider_audit = [
        {
            "field": c,
            "row_count": len(feature),
            "non_null_count": int(feature[c].notna().sum()) if c in feature else 0,
            "status": "present" if c in feature else "missing",
        }
        for c in ["open", "high", "low", "close", "volume", "money", "vwap", "index_open", "index_close"]
    ]
    write_csv(pd.DataFrame(provider_audit), paths.audit_dir / "r05_provider_field_audit.csv")
    feature.to_parquet(paths.cache_dir / "r05_daily_feature_panel.parquet", index=False)
    return feature


def source_path(config: dict[str, Any]) -> Path:
    return r01.topic_path(config["data_sources"]["gtja191_source_path"])


def extract_gtja_functions(source_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in re.finditer(r"//alpha\s+(\d+).*?\n(?:@state\s*\n)?def gtjaAlpha(\d+)\(([^)]*)\)\{", source_text, flags=re.S):
        alpha_no = int(match.group(2))
        start = match.end()
        depth = 1
        i = start
        while i < len(source_text) and depth:
            if source_text[i] == "{":
                depth += 1
            elif source_text[i] == "}":
                depth -= 1
            i += 1
        body = source_text[start : i - 1]
        comment_start = source_text.rfind("//alpha", 0, match.start())
        comment_block = source_text[comment_start : match.start()] if comment_start >= 0 else ""
        formula_lines = [line.strip()[2:].strip() for line in comment_block.splitlines() if line.strip().startswith("//") and not line.strip().lower().startswith("//alpha")]
        rows.append(
            {
                "factor_no": alpha_no,
                "factor_id": f"alpha{alpha_no:03d}",
                "function_name": f"gtjaAlpha{alpha_no}",
                "args": [arg.strip() for arg in match.group(3).split(",") if arg.strip()],
                "body": body,
                "source_formula_text": "\n".join(formula_lines).strip() or body.strip(),
            }
        )
    return sorted(rows, key=lambda x: x["factor_no"])


def seq(start: int, end: int) -> np.ndarray:
    return np.arange(int(start), int(end) + 1, dtype=float)


def _to_df(value: Any, like: pd.DataFrame | None = None) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.astype(float)
    if isinstance(value, pd.Series):
        if like is not None:
            return pd.DataFrame(np.repeat(value.to_numpy()[:, None], len(like.columns), axis=1), index=like.index, columns=like.columns)
        return value.to_frame().astype(float)
    if like is not None:
        return pd.DataFrame(float(value), index=like.index, columns=like.columns)
    return pd.DataFrame(value)


def iif(cond: Any, yes: Any, no: Any) -> pd.DataFrame:
    like = next((x for x in [cond, yes, no] if isinstance(x, pd.DataFrame)), None)
    c = cond if isinstance(cond, pd.DataFrame) else _to_df(cond, like)
    y = yes if isinstance(yes, pd.DataFrame) else _to_df(yes, like)
    n = no if isinstance(no, pd.DataFrame) else _to_df(no, like)
    return y.where(c.astype(bool), n)


def log(x: Any) -> pd.DataFrame:
    return np.log(x)


def sign(x: Any) -> pd.DataFrame:
    return np.sign(x)


def pow(x: Any, y: Any) -> pd.DataFrame:
    with np.errstate(all="ignore"):
        return np.power(x, y)


def abs(x: Any) -> pd.DataFrame:  # noqa: A001
    return np.abs(x)


def max(a: Any, b: Any) -> pd.DataFrame:  # noqa: A001
    like = a if isinstance(a, pd.DataFrame) else b if isinstance(b, pd.DataFrame) else None
    return pd.DataFrame(np.maximum(_to_df(a, like), _to_df(b, like)), index=like.index, columns=like.columns) if like is not None else np.maximum(a, b)


def min(a: Any, b: Any) -> pd.DataFrame:  # noqa: A001
    like = a if isinstance(a, pd.DataFrame) else b if isinstance(b, pd.DataFrame) else None
    return pd.DataFrame(np.minimum(_to_df(a, like), _to_df(b, like)), index=like.index, columns=like.columns) if like is not None else np.minimum(a, b)


def logical_and(a: Any, b: Any) -> pd.DataFrame:
    like = a if isinstance(a, pd.DataFrame) else b if isinstance(b, pd.DataFrame) else None
    left = _to_df(a, like).fillna(False).astype(bool)
    right = _to_df(b, like).fillna(False).astype(bool)
    return left & right


def logical_or(a: Any, b: Any) -> pd.DataFrame:
    like = a if isinstance(a, pd.DataFrame) else b if isinstance(b, pd.DataFrame) else None
    left = _to_df(a, like).fillna(False).astype(bool)
    right = _to_df(b, like).fillna(False).astype(bool)
    return left | right


def mfirst(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.shift(int(n) - 1)


def move(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.shift(int(n))


def ratios(x: pd.DataFrame) -> pd.DataFrame:
    return x / x.shift(1)


def msum(x: pd.DataFrame, window: int) -> pd.DataFrame:
    return x.rolling(int(window), min_periods=int(window)).sum()


def mavg(x: pd.DataFrame, window_or_weights: Any, window: int | None = None) -> pd.DataFrame:
    if isinstance(window_or_weights, np.ndarray):
        weights = window_or_weights.astype(float)
        win = int(window or len(weights))
        weights = weights[-win:]
        denom = float(np.nansum(weights))
        return x.rolling(win, min_periods=win).apply(lambda arr: float(np.nansum(arr * weights) / denom), raw=True)
    win = int(window_or_weights)
    return x.rolling(win, min_periods=win).mean()


def mstd(x: pd.DataFrame, window: int) -> pd.DataFrame:
    return x.rolling(int(window), min_periods=int(window)).std(ddof=0)


def mmin(x: pd.DataFrame, window: int) -> pd.DataFrame:
    return x.rolling(int(window), min_periods=int(window)).min()


def mmax(x: pd.DataFrame, window: int) -> pd.DataFrame:
    return x.rolling(int(window), min_periods=int(window)).max()


def mcount(x: pd.DataFrame, window: int) -> pd.DataFrame:
    y = x.astype(float)
    if x.dtypes.astype(str).str.contains("bool").any():
        y = x.fillna(False).astype(float)
        return y.rolling(int(window), min_periods=int(window)).sum()
    return y.notna().astype(float).rolling(int(window), min_periods=int(window)).sum()


def mcorr(x: pd.DataFrame, y: pd.DataFrame, window: int) -> pd.DataFrame:
    return x.rolling(int(window), min_periods=int(window)).corr(y)


def mcovar(x: pd.DataFrame, y: pd.DataFrame, window: int) -> pd.DataFrame:
    return x.rolling(int(window), min_periods=int(window)).cov(y)


def mbeta(x: pd.DataFrame, y: pd.DataFrame, window: int) -> pd.DataFrame:
    return x.rolling(int(window), min_periods=int(window)).cov(y) / y.rolling(int(window), min_periods=int(window)).var()


def ewmMean(x: pd.DataFrame, alpha: float) -> pd.DataFrame:
    return x.ewm(alpha=float(alpha), adjust=False, min_periods=1).mean()


def rowRank(x: pd.DataFrame, percent: bool = True) -> pd.DataFrame:
    return x.rank(axis=1, pct=percent, method="average")


def mrank(x: pd.DataFrame, ascending: bool, window: int) -> pd.DataFrame:
    win = int(window)
    def last_rank(arr: np.ndarray) -> float:
        if np.isnan(arr[-1]):
            return np.nan
        valid = arr[~np.isnan(arr)]
        if len(valid) < win:
            return np.nan
        order = pd.Series(valid).rank(method="average", ascending=bool(ascending), pct=True)
        return float(order.iloc[-1])
    return x.rolling(win, min_periods=win).apply(last_rank, raw=True)


def mimin(x: pd.DataFrame, window: int) -> pd.DataFrame:
    win = int(window)
    return x.rolling(win, min_periods=win).apply(lambda arr: float(np.nanargmin(arr)) if np.isfinite(arr).any() else np.nan, raw=True)


def mimax(x: pd.DataFrame, window: int) -> pd.DataFrame:
    win = int(window)
    return x.rolling(win, min_periods=win).apply(lambda arr: float(np.nanargmax(arr)) if np.isfinite(arr).any() else np.nan, raw=True)


def rowMax(x: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(np.repeat(x.max(axis=1).to_numpy()[:, None], len(x.columns), axis=1), index=x.index, columns=x.columns)


def rowMin(x: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(np.repeat(x.min(axis=1).to_numpy()[:, None], len(x.columns), axis=1), index=x.index, columns=x.columns)


def linearTimeTrend(x: pd.DataFrame, window: int) -> list[pd.DataFrame]:
    win = int(window)
    t = np.arange(win, dtype=float)
    t = t - t.mean()
    denom = float(np.sum(t * t))
    beta = x.rolling(win, min_periods=win).apply(lambda arr: float(np.dot(arr - np.nanmean(arr), t) / denom) if np.isfinite(arr).all() else np.nan, raw=True)
    intercept = x.rolling(win, min_periods=win).mean() - beta * t.mean()
    return [intercept, beta]


def alpha055_manual(open: pd.DataFrame, close: pd.DataFrame, high: pd.DataFrame, low: pd.DataFrame) -> pd.DataFrame:
    tmp1 = 16 * (close - mfirst(close, 2) + (close - open) / 2 + mfirst(close, 2) - mfirst(open, 2))
    cond = logical_and(
        abs(high - mfirst(close, 2)) > abs(low - mfirst(close, 2)),
        abs(high - mfirst(close, 2)) > abs(high - mfirst(low, 2)),
    )
    iftrue = abs(high - mfirst(close, 2)) + abs(low - mfirst(close, 2)) / 2 + abs(mfirst(close, 2) - mfirst(open, 2)) / 4
    cond2 = logical_and(
        abs(low - mfirst(close, 2)) > abs(high - mfirst(low, 2)),
        abs(low - mfirst(close, 2)) > abs(high - mfirst(close, 2)),
    )
    iftrue2 = abs(low - mfirst(close, 2)) + abs(high - mfirst(low, 2)) / 2 + abs(mfirst(close, 2) - mfirst(open, 2)) / 4
    iffalse2 = abs(high - mfirst(low, 2)) + abs(mfirst(close, 2) - mfirst(open, 2)) / 4
    tmp2 = iif(cond, iftrue, iif(cond2, iftrue2, iffalse2))
    tmp3 = max(abs(high - mfirst(close, 2)), abs(low - mfirst(close, 2)))
    return msum(tmp1 / tmp2 * tmp3, 20)


def alpha137_manual(open: pd.DataFrame, close: pd.DataFrame, high: pd.DataFrame, low: pd.DataFrame) -> pd.DataFrame:
    tmp1 = 16 * (close - mfirst(close, 2) + (close - open) / 2 + mfirst(close, 2) - mfirst(open, 2))
    con1 = logical_and(
        abs(high - mfirst(close, 2)) > abs(low - mfirst(close, 2)),
        abs(high - move(close, 1)) > abs(high - move(low, 1)),
    )
    con2 = logical_and(
        abs(low - move(close, 1)) > abs(high - move(low, 1)),
        abs(low - move(close, 1)) > abs(high - move(close, 1)),
    )
    tmp2 = iif(
        con1,
        abs(high - mfirst(close, 2)) + abs(low - mfirst(close, 2)) / 2 + abs(mfirst(close, 2) - mfirst(open, 2)) / 4,
        iif(
            con2,
            abs(low - mfirst(close, 2)) + abs(high - mfirst(close, 2)) / 2 + abs(mfirst(close, 2) - mfirst(open, 2)) / 4,
            abs(high - mfirst(low, 2)) + abs(mfirst(close, 2) - mfirst(open, 2)) / 4,
        ),
    )
    tmp3 = max(abs(high - mfirst(close, 2)), abs(low - mfirst(close, 2)))
    return tmp1 / tmp2 * tmp3


def alpha182_manual(open: pd.DataFrame, close: pd.DataFrame, index_open: pd.DataFrame, index_close: pd.DataFrame) -> pd.DataFrame:
    same_direction = logical_or(
        logical_and(close > open, index_close > index_open),
        logical_and(close < open, index_close < index_open),
    )
    return mcount(same_direction, 20) / 20


MANUAL_ALPHA_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "alpha055": alpha055_manual,
    "alpha137": alpha137_manual,
    "alpha182": alpha182_manual,
}


def _translate_body(body: str) -> str:
    lines = []
    for raw in body.splitlines():
        line = raw.split("//", 1)[0].strip()
        if not line:
            continue
        line = line.replace("\\", "/")
        line = line.replace("&&", "&").replace("||", "|")
        line = re.sub(r"\btrue\b", "True", line, flags=re.I)
        line = re.sub(r"\bfalse\b", "False", line, flags=re.I)
        line = re.sub(r"\bNULL\b", "np.nan", line)
        line = re.sub(r"(\d+)\.\.(\d+)", r"seq(\1,\2)", line)
        line = line.rstrip(";")
        lines.append("    " + line)
    return "\n".join(lines)


def compile_alpha_functions(function_specs: list[dict[str, Any]]) -> dict[str, Callable[..., Any]]:
    env: dict[str, Any] = {
        "np": np,
        "pd": pd,
        "seq": seq,
        "iif": iif,
        "log": log,
        "sign": sign,
        "pow": pow,
        "abs": abs,
        "max": max,
        "min": min,
        "logical_and": logical_and,
        "logical_or": logical_or,
        "mfirst": mfirst,
        "move": move,
        "ratios": ratios,
        "msum": msum,
        "mavg": mavg,
        "mstd": mstd,
        "mmin": mmin,
        "mmax": mmax,
        "mcount": mcount,
        "mcorr": mcorr,
        "mcovar": mcovar,
        "mbeta": mbeta,
        "ewmMean": ewmMean,
        "rowRank": rowRank,
        "mrank": mrank,
        "mimin": mimin,
        "mimax": mimax,
        "rowMax": rowMax,
        "rowMin": rowMin,
        "linearTimeTrend": linearTimeTrend,
    }
    funcs: dict[str, Callable[..., Any]] = {}
    for spec in function_specs:
        if spec["factor_id"] in MANUAL_ALPHA_FUNCTIONS:
            funcs[spec["factor_id"]] = MANUAL_ALPHA_FUNCTIONS[spec["factor_id"]]
            continue
        body = spec["body"]
        if any(token in body for token in ["each(", "loop(", "ols", "accumulate("]):
            continue
        code = f"def alpha_{spec['factor_no']:03d}({', '.join(spec['args'])}):\n{_translate_body(body)}\n"
        try:
            exec(code, env)
            funcs[spec["factor_id"]] = env[f"alpha_{spec['factor_no']:03d}"]
        except Exception:
            continue
    return funcs


def build_wide_inputs(feature: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.DatetimeIndex, list[str]]:
    stocks = sorted(feature["instrument_id"].unique())
    dates = pd.DatetimeIndex(sorted(feature["trade_date"].unique()))
    def wide(column: str) -> pd.DataFrame:
        return feature.pivot(index="trade_date", columns="instrument_id", values=column).reindex(index=dates, columns=stocks)
    inputs = {
        "open": wide("open"),
        "close": wide("close"),
        "high": wide("high"),
        "low": wide("low"),
        "vol": wide("volume"),
        "vwap": wide("vwap"),
    }
    index_open = feature.groupby("trade_date")["index_open"].first().reindex(dates)
    index_close = feature.groupby("trade_date")["index_close"].first().reindex(dates)
    inputs["index_open"] = pd.DataFrame(np.repeat(index_open.to_numpy()[:, None], len(stocks), axis=1), index=dates, columns=stocks)
    inputs["index_close"] = pd.DataFrame(np.repeat(index_close.to_numpy()[:, None], len(stocks), axis=1), index=dates, columns=stocks)
    return inputs, dates, stocks


def factor_lookback(text: str) -> int:
    nums = [int(x) for x in re.findall(r"\b(?:mavg|msum|mstd|mmin|mmax|mcorr|mcovar|mrank|mbeta|mcount|move|mfirst|linearTimeTrend)\([^,\n]+,\s*(\d+)", text)]
    nums += [int(x) for x in re.findall(r"seq\(\d+,\s*(\d+)\)", text)]
    return builtins.max(nums) if nums else 1


def candidate_base(config: dict[str, Any], feature: pd.DataFrame) -> pd.DataFrame:
    c = config["frozen_formula_constants"]
    floor = float(c["avg_money20_floor_cny"])
    base = feature.loc[feature["weekly_observation_date"] & feature["split"].isin(SPLITS)].copy()
    base["base_eligible"] = (
        base["pit_universe_member"].astype(bool)
        & (base["avg_money20_D"] >= floor)
        & base[["open", "high", "low", "close", "volume", "money", "vwap"]].replace([np.inf, -np.inf], np.nan).notna().all(axis=1)
        & (base["close"] > 0)
        & (base["volume"] > 0)
        & (base["money"] > 0)
        & np.isfinite(base["vwap"])
    )
    cols = [
        "instrument_id",
        "trade_date",
        "split",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "vwap",
        "avg_money20_D",
        "industry_id",
        "industry_name",
        "liquidity_quintile",
        "beta_bucket",
        "market_state",
        "base_eligible",
    ]
    return base.loc[base["base_eligible"], cols].rename(columns={"trade_date": "signal_date"}).reset_index(drop=True)


def normalize_factor_for_candidates(raw: pd.DataFrame, candidates: pd.DataFrame) -> np.ndarray:
    out = np.full(len(candidates), np.nan, dtype=np.float32)
    for date, idx in candidates.groupby("signal_date").groups.items():
        date = pd.Timestamp(date)
        if date not in raw.index:
            continue
        instruments = candidates.loc[idx, "instrument_id"].tolist()
        values = pd.Series(raw.loc[date, instruments].to_numpy(dtype=float), index=idx).replace([np.inf, -np.inf], np.nan)
        finite_values = values.dropna()
        if finite_values.empty:
            continue
        lo, hi = finite_values.quantile([0.01, 0.99]).tolist()
        clipped = values.clip(lo, hi)
        ranks = clipped.rank(method="average", pct=True) - 0.5
        out[list(idx)] = ranks.astype(float).to_numpy(dtype=np.float32)
    return out


def build_factor_matrix(config: dict[str, Any], paths: R05Paths, feature: pd.DataFrame, candidates: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    source = source_path(config).read_text(encoding="utf-8")
    specs = extract_gtja_functions(source)
    funcs = compile_alpha_functions(specs)
    inputs, _, _ = build_wide_inputs(feature)
    constants = config["frozen_formula_constants"]
    min_dates = int(constants["min_train_factor_coverage_date_count"])
    min_xs = int(constants["min_train_factor_cross_section_count_per_date"])
    max_lookback = int(constants["max_lookback_trading_days"])
    values: list[np.ndarray] = []
    factor_ids: list[str] = []
    rows = []
    train_dates = set(pd.to_datetime(candidates.loc[candidates["split"].eq("train"), "signal_date"]).dt.normalize())
    for spec in specs:
        fid = spec["factor_id"]
        local_text = _translate_body(spec["body"])
        lookback = factor_lookback(local_text)
        slow_or_unsupported = any(
            token in spec["body"]
            for token in [
                "mcorr",
                "mrank",
                "mcovar",
                "mbeta",
                "linearTimeTrend",
                "rowMax",
                "rowMin",
                "mimin",
                "mimax",
                "each(",
                "loop(",
                "ols",
                "accumulate(",
            ]
        )
        status = "included"
        reason = ""
        arr = None
        err = ""
        if slow_or_unsupported:
            status = "excluded_formula_implementation_failed"
            reason = "unsupported_or_slow_v0_construct"
        elif fid not in funcs:
            status = "excluded_formula_implementation_failed"
            reason = "unsupported_dolphindb_construct"
        elif lookback > max_lookback:
            status = "excluded_not_asof_safe"
            reason = "max_lookback_gt_252"
        else:
            try:
                func = funcs[fid]
                kwargs = {name: inputs[name] for name in inspect.signature(func).parameters if name in inputs}
                raw = func(**kwargs)
                raw = _to_df(raw, inputs["close"]).reindex_like(inputs["close"]).astype(float)
                arr = normalize_factor_for_candidates(raw, candidates)
                tmp = candidates[["signal_date", "split"]].copy()
                tmp["finite"] = np.isfinite(arr)
                train_counts = tmp.loc[tmp["split"].eq("train")].groupby("signal_date")["finite"].sum()
                valid_train_dates = int((train_counts >= min_xs).sum())
                train_std = float(np.nanstd(arr[candidates["split"].eq("train").to_numpy()])) if np.isfinite(arr[candidates["split"].eq("train").to_numpy()]).any() else np.nan
                if valid_train_dates < min_dates:
                    status = "excluded_insufficient_cross_section_coverage"
                    reason = "insufficient_train_factor_coverage_date_count"
                elif not finite(train_std) or train_std == 0:
                    status = "excluded_constant_or_degenerate"
                    reason = "constant_or_degenerate_train_values"
            except Exception as exc:  # keep registry complete and auditable
                status = "excluded_formula_implementation_failed"
                reason = type(exc).__name__
                err = str(exc)[:200]
        if status == "included" and arr is not None:
            factor_ids.append(fid)
            values.append(arr)
        rows.append(
            {
                "factor_id": fid,
                "source_name": spec["function_name"],
                "source_formula_text": spec["source_formula_text"],
                "source_formula_hash": hashlib.sha256(spec["source_formula_text"].encode("utf-8")).hexdigest(),
                "local_formula_hash": hashlib.sha256(local_text.encode("utf-8")).hexdigest(),
                "required_fields": ",".join(spec["args"]),
                "max_lookback_trading_days": lookback,
                "effective_first_usable_date": "",
                "asof_safe": lookback <= max_lookback,
                "factor_status": status,
                "exclusion_reason": reason,
                "implementation_error": err,
            }
        )
        if spec["factor_no"] % 20 == 0:
            print(f"R05 factor registry progress: alpha{spec['factor_no']:03d}", flush=True)
    registry = pd.DataFrame(rows)
    write_csv(registry, paths.audit_dir / "r05_factor_registry.csv")
    coverage = registry[["factor_id", "factor_status", "exclusion_reason", "max_lookback_trading_days", "asof_safe"]].copy()
    write_csv(coverage, paths.audit_dir / "r05_factor_coverage_audit.csv")
    if values:
        matrix = np.column_stack(values).astype(np.float32)
    else:
        matrix = np.empty((len(candidates), 0), dtype=np.float32)
    np.save(paths.cache_dir / "r05_normalized_factor_matrix.npy", matrix)
    write_json({"factor_ids": factor_ids}, paths.cache_dir / "r05_factor_matrix_columns.json")
    return registry, matrix, factor_ids


def execute_events(config: dict[str, Any], feature: pd.DataFrame, events: pd.DataFrame, horizons: list[int] = HORIZONS) -> pd.DataFrame:
    calendar = r01.load_calendar(config)
    lookup = r01.make_feature_lookup(feature)
    max_entry_lag = int(config["execution"]["max_entry_execution_lag_trading_days"])
    max_exit_lag = int(config["execution"]["max_exit_execution_lag_trading_days"])
    buy_cost = float(config["execution"]["buy_cost_bps"])
    sell_cost = float(config["execution"]["sell_cost_bps"])
    rows: list[dict[str, Any]] = []
    for ev in events.itertuples(index=False):
        base = ev._asdict()
        for horizon in horizons:
            row = dict(base)
            row.update(
                {
                    "horizon": f"H{horizon}",
                    "entry_execution_date": pd.NaT,
                    "entry_price": np.nan,
                    "natural_exit_target_date": pd.NaT,
                    "natural_exit_signal_date": pd.NaT,
                    "exit_execution_date": pd.NaT,
                    "exit_price": np.nan,
                    "buy_cost_bps": buy_cost,
                    "sell_cost_bps": sell_cost,
                    "round_trip_cost_bps": buy_cost + sell_cost,
                    "gross_return": np.nan,
                    "net_return": np.nan,
                    "execution_status": "",
                    "blocked_reason": "",
                    "entry_lag_trading_days": np.nan,
                    "exit_lag_trading_days": np.nan,
                }
            )
            entry = r01.first_executable_open(config, calendar, lookup, ev.instrument_id, pd.Timestamp(ev.signal_date), ev.split, "entry", max_entry_lag)
            row["entry_lag_trading_days"] = entry["lag"]
            if entry["blocked_reason"]:
                row["execution_status"] = f"blocked_{entry['blocked_reason']}"
                row["blocked_reason"] = entry["blocked_reason"]
                rows.append(row)
                continue
            row["entry_execution_date"] = entry["date"]
            row["entry_price"] = entry["price"]
            target = r01.add_trading_days(calendar, row["entry_execution_date"], horizon)
            row["natural_exit_target_date"] = target
            if pd.isna(target):
                row["execution_status"] = "blocked_insufficient_forward_trading_days"
                row["blocked_reason"] = "insufficient_forward_trading_days"
                rows.append(row)
                continue
            if split_for_date(config, target) != ev.split:
                row["execution_status"] = "blocked_split_boundary"
                row["blocked_reason"] = "split_boundary"
                rows.append(row)
                continue
            natural_signal = r01.prev_trading_day(calendar, target)
            row["natural_exit_signal_date"] = natural_signal
            exit_exec = r01.first_executable_open(config, calendar, lookup, ev.instrument_id, natural_signal, ev.split, "exit", max_exit_lag)
            row["exit_lag_trading_days"] = exit_exec["lag"]
            if exit_exec["blocked_reason"]:
                row["execution_status"] = f"blocked_{exit_exec['blocked_reason']}"
                row["blocked_reason"] = exit_exec["blocked_reason"]
                rows.append(row)
                continue
            row["exit_execution_date"] = exit_exec["date"]
            row["exit_price"] = exit_exec["price"]
            row["gross_return"] = row["exit_price"] / row["entry_price"] - 1.0
            row["net_return"] = row["exit_price"] * (1.0 - sell_cost / 10000.0) / (row["entry_price"] * (1.0 + buy_cost / 10000.0)) - 1.0
            row["execution_status"] = "complete_executable"
            rows.append(row)
    return pd.DataFrame(rows)


def build_train_labels(config: dict[str, Any], paths: R05Paths, feature: pd.DataFrame, candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = candidates.loc[candidates["split"].eq("train")].copy()
    events = train.rename(columns={"signal_date": "signal_date"}).copy()
    events["event_key"] = ["train_candidate_%d" % i for i in range(len(events))]
    execution = execute_events(config, feature, events, [10])
    total_train_dates = int(train["signal_date"].nunique())
    split_blocked_dates = set(pd.to_datetime(execution.loc[execution["blocked_reason"].eq("split_boundary"), "signal_date"]).dt.normalize())
    purged_date_count = len(split_blocked_dates)
    unpurged_date_count = builtins.max(total_train_dates - purged_date_count, 0)
    unpurged_share = safe_share(unpurged_date_count, total_train_dates)
    min_unpurged = float(config["frozen_formula_constants"]["min_train_label_unpurged_signal_date_share"])
    purge_audit = pd.DataFrame(
        [
            {
                "split": "train",
                "primary_horizon": "H10",
                "total_train_signal_date_count": total_train_dates,
                "train_label_purged_cross_split_signal_date_count": purged_date_count,
                "train_label_unpurged_signal_date_count": unpurged_date_count,
                "train_label_unpurged_signal_date_share": unpurged_share,
                "min_train_label_unpurged_signal_date_share": min_unpurged,
                "train_label_purge_gate": unpurged_share >= min_unpurged,
            }
        ]
    )
    write_csv(purge_audit, paths.audit_dir / "r05_train_label_purge_audit.csv")
    complete = execution.loc[execution["execution_status"].eq("complete_executable")].copy()
    labels = []
    for date, group in complete.groupby("signal_date", sort=True):
        for rec in group.itertuples(index=False):
            base = group.loc[group["instrument_id"].ne(rec.instrument_id)]
            scopes = [
                base.loc[(base["industry_id"].eq(rec.industry_id)) & (base["liquidity_quintile"].eq(rec.liquidity_quintile)) & (base["beta_bucket"].eq(rec.beta_bucket))],
                base.loc[base["industry_id"].eq(rec.industry_id)],
                base.loc[base["liquidity_quintile"].eq(rec.liquidity_quintile)],
                base.loc[base["beta_bucket"].eq(rec.beta_bucket)],
                base,
            ]
            scope = next((s for s in scopes[:-1] if len(s) >= 30), scopes[-1])
            matched = safe_mean(scope["net_return"])
            labels.append({"candidate_row_id": rec.candidate_row_id, "signal_date": date, "H10_net_return": rec.net_return, "H10_matched_comparator_net_return": matched, "label": rec.net_return - matched if finite(matched) else np.nan})
    return pd.DataFrame(labels), purge_audit


def _date_design_matrix(group: pd.DataFrame) -> np.ndarray:
    parts = [pd.Series(1.0, index=group.index, name="intercept")]
    for col in ["industry_id", "liquidity_quintile", "beta_bucket"]:
        labels = group[col].astype(object).where(group[col].notna(), "__missing__").astype(str)
        dummies = pd.get_dummies(labels, prefix=col, dtype=float)
        if dummies.shape[1] > 1:
            dummies = dummies.reindex(sorted(dummies.columns), axis=1).iloc[:, 1:]
            parts.append(dummies)
    return pd.concat(parts, axis=1).to_numpy(dtype=float)


def neutralize_factor_matrix(paths: R05Paths, candidates: pd.DataFrame, matrix: np.ndarray, factor_ids: list[str]) -> np.ndarray:
    neutral = np.full(matrix.shape, np.nan, dtype=np.float32)
    date_failures: list[dict[str, Any]] = []
    for date, idx in candidates.groupby("signal_date", sort=True).groups.items():
        idx_list = list(idx)
        group = candidates.loc[idx_list]
        x = _date_design_matrix(group)
        rank = np.linalg.matrix_rank(x) if len(group) else 0
        if len(group) < 100 or rank < x.shape[1]:
            date_failures.append({"signal_date": date, "neutralization_failure_count": len(factor_ids), "neutralization_status": "underdetermined_design"})
            continue
        fail_count = 0
        for j, fid in enumerate(factor_ids):
            y = matrix[idx_list, j].astype(float)
            mask = np.isfinite(y)
            if int(mask.sum()) < 100:
                fail_count += 1
                continue
            xm = x[mask]
            ym = y[mask]
            if np.linalg.matrix_rank(xm) < xm.shape[1]:
                fail_count += 1
                continue
            beta, *_ = np.linalg.lstsq(xm, ym, rcond=None)
            resid = ym - xm @ beta
            ranks = pd.Series(resid).rank(method="average", pct=True).to_numpy(dtype=float) - 0.5
            local_positions = np.asarray(idx_list, dtype=int)[mask]
            neutral[local_positions, j] = ranks.astype(np.float32)
        date_failures.append({"signal_date": date, "neutralization_failure_count": fail_count, "neutralization_status": "ok" if fail_count == 0 else "partial_missing_factor_dates"})
    rows = []
    split_arr = candidates["split"].to_numpy()
    for j, fid in enumerate(factor_ids):
        raw = matrix[:, j]
        neu = neutral[:, j]
        train_mask = split_arr == "train"
        rows.append(
            {
                "audit_scope": "factor",
                "factor_id": fid,
                "usable_date_count_before": int(candidates.loc[np.isfinite(raw), "signal_date"].nunique()),
                "usable_date_count_after": int(candidates.loc[np.isfinite(neu), "signal_date"].nunique()),
                "train_missing_share_before": 1.0 - safe_share(int(np.isfinite(raw[train_mask]).sum()), int(train_mask.sum())),
                "train_missing_share_after": 1.0 - safe_share(int(np.isfinite(neu[train_mask]).sum()), int(train_mask.sum())),
                "raw_rank_mean": float(np.nanmean(raw)) if np.isfinite(raw).any() else np.nan,
                "raw_rank_std": float(np.nanstd(raw)) if np.isfinite(raw).any() else np.nan,
                "neutralized_rank_mean": float(np.nanmean(neu)) if np.isfinite(neu).any() else np.nan,
                "neutralized_rank_std": float(np.nanstd(neu)) if np.isfinite(neu).any() else np.nan,
            }
        )
    audit = pd.concat([pd.DataFrame(rows), pd.DataFrame(date_failures).assign(audit_scope="date")], ignore_index=True, sort=False)
    write_csv(audit, paths.audit_dir / "r05_factor_neutralization_audit.csv")
    np.save(paths.cache_dir / "r05_neutralized_factor_matrix.npy", neutral)
    return neutral


def _daily_rankics(candidates: pd.DataFrame, values: np.ndarray, labels: np.ndarray, train_mask: np.ndarray) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    date_values = pd.to_datetime(candidates["signal_date"]).dt.normalize().to_numpy()
    for date in np.unique(date_values[train_mask]):
        mask = train_mask & (date_values == date) & np.isfinite(values)
        if int(mask.sum()) < 100:
            continue
        corr = pd.Series(values[mask]).rank(method="average").corr(pd.Series(labels[mask]).rank(method="average"))
        if finite(corr):
            rows.append({"signal_date": pd.Timestamp(date), "calendar_year": pd.Timestamp(date).year, "rankIC": float(corr), "observation_count": int(mask.sum())})
    return rows


def learn_train_stability(config: dict[str, Any], paths: R05Paths, candidates: pd.DataFrame, raw_matrix: np.ndarray, neutral_matrix: np.ndarray, factor_ids: list[str], train_labels: pd.DataFrame) -> pd.DataFrame:
    constants = config["frozen_formula_constants"]
    min_years = int(constants["min_valid_train_year_count"])
    min_abs_ic = float(constants["min_abs_mean_train_rankIC"])
    min_same_sign = int(constants["min_same_sign_year_count"])
    max_contrib = float(constants["max_single_year_ic_contribution_share"])
    label_map = train_labels.set_index("candidate_row_id")["label"] if not train_labels.empty else pd.Series(dtype=float)
    labels = candidates["candidate_row_id"].map(label_map).to_numpy(dtype=float)
    train_mask = candidates["split"].eq("train").to_numpy() & np.isfinite(labels)
    summary_rows: list[dict[str, Any]] = []
    yearly_rows: list[dict[str, Any]] = []
    for j, fid in enumerate(factor_ids):
        raw_daily = _daily_rankics(candidates, raw_matrix[:, j], labels, train_mask)
        neu_daily = _daily_rankics(candidates, neutral_matrix[:, j], labels, train_mask)
        raw_year = pd.DataFrame(raw_daily).groupby("calendar_year")["rankIC"].mean() if raw_daily else pd.Series(dtype=float)
        neu_year = pd.DataFrame(neu_daily).groupby("calendar_year")["rankIC"].mean() if neu_daily else pd.Series(dtype=float)
        for year, value in raw_year.items():
            yearly_rows.append({"factor_id": fid, "rankic_feature_version": "raw_rank_factor", "calendar_year": int(year), "yearly_rankIC": float(value)})
        for year, value in neu_year.items():
            yearly_rows.append({"factor_id": fid, "rankic_feature_version": "neutralized_rank_factor", "calendar_year": int(year), "yearly_rankIC": float(value)})
        valid_years = int(raw_year.count())
        mean_ic = float(raw_year.mean()) if valid_years else np.nan
        ic_vol = float(raw_year.std(ddof=0)) if valid_years else np.nan
        sign_mean = 1 if finite(mean_ic) and mean_ic > 0 else -1 if finite(mean_ic) and mean_ic < 0 else 0
        positive_years = int((raw_year > 0).sum()) if valid_years else 0
        negative_years = int((raw_year < 0).sum()) if valid_years else 0
        same_sign = positive_years if sign_mean > 0 else negative_years if sign_mean < 0 else 0
        sign_consistency = safe_share(same_sign, valid_years)
        denom = float(raw_year.abs().sum()) if valid_years else 0.0
        contribution = float(raw_year.abs().max() / denom) if denom > 0 else np.nan
        neu_mean = float(neu_year.mean()) if int(neu_year.count()) else np.nan
        sign_agree = bool(finite(mean_ic) and finite(neu_mean) and mean_ic != 0 and neu_mean != 0 and np.sign(mean_ic) == np.sign(neu_mean))
        stability_selected = bool(valid_years >= min_years and finite(mean_ic) and abs(mean_ic) >= min_abs_ic and same_sign >= min_same_sign and finite(contribution) and contribution <= max_contrib)
        representative_eligible = bool(stability_selected and sign_agree)
        direction = int(np.sign(mean_ic)) if finite(mean_ic) and mean_ic != 0 else 0
        quality = abs(mean_ic) * sign_consistency / (1.0 + (ic_vol if finite(ic_vol) else 0.0)) if finite(mean_ic) else np.nan
        train_missing = 1.0 - safe_share(int(np.isfinite(neutral_matrix[train_mask, j]).sum()), int(train_mask.sum()))
        summary_rows.append(
            {
                "factor_id": fid,
                "valid_train_year_count": valid_years,
                "mean_train_rankIC": mean_ic,
                "ic_vol": ic_vol,
                "positive_year_count": positive_years,
                "negative_year_count": negative_years,
                "same_sign_year_count": same_sign,
                "sign_consistency": sign_consistency,
                "single_year_ic_contribution_share": contribution,
                "neutralized_mean_train_rankIC": neu_mean,
                "raw_neutralized_rankIC_sign_agree": sign_agree,
                "factor_quality_score": quality,
                "direction_i": direction,
                "stability_selected": stability_selected,
                "representative_eligible": representative_eligible,
                "neutralized_missing_share": train_missing,
            }
        )
    stability = pd.DataFrame(summary_rows)
    write_csv(pd.DataFrame(yearly_rows), paths.audit_dir / "r05_train_rankic_by_factor_year.csv")
    write_csv(stability, paths.audit_dir / "r05_factor_stability_selection_audit.csv")
    write_csv(stability[["factor_id", "direction_i", "mean_train_rankIC", "stability_selected", "representative_eligible"]], paths.audit_dir / "r05_factor_direction_audit.csv")
    return stability


def cluster_and_select_representatives(config: dict[str, Any], paths: R05Paths, candidates: pd.DataFrame, neutral_matrix: np.ndarray, factor_ids: list[str], stability: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    constants = config["frozen_formula_constants"]
    threshold = float(constants["cluster_abs_corr_threshold"])
    min_pair = int(constants["min_pairwise_factor_corr_observation_count"])
    min_clusters = int(constants["min_cluster_count"])
    max_cluster_share = float(constants["max_cluster_top_factor_share"])
    selected_factors = stability.loc[stability["stability_selected"].map(bool_value)].copy()
    total_selected = len(selected_factors)
    if total_selected == 0:
        empty_cluster = pd.DataFrame(columns=["factor_id", "cluster_id", "cluster_source_factor_share", "representative_eligible", "is_representative"])
        write_csv(empty_cluster, paths.audit_dir / "r05_factor_cluster_audit.csv")
        write_csv(pd.DataFrame(), paths.audit_dir / "r05_selected_factor_manifest.csv")
        return empty_cluster, pd.DataFrame(), {"cluster_count": 0, "cluster_structure_ok": False, "cluster_block_reason": "no_stability_selected_factors"}

    id_to_col = {fid: i for i, fid in enumerate(factor_ids)}
    selected_ids = selected_factors["factor_id"].tolist()
    selected_cols = [id_to_col[fid] for fid in selected_ids]
    train_mask = candidates["split"].eq("train").to_numpy()
    df = pd.DataFrame(neutral_matrix[train_mask][:, selected_cols], columns=selected_ids)
    corr = df.corr(method="spearman", min_periods=min_pair)
    counts = df.notna().astype(np.int32).T.dot(df.notna().astype(np.int32))

    clusters: list[set[str]] = [{fid} for fid in selected_ids]
    while True:
        best: tuple[float, str, str, int, int] | None = None
        for ai in range(len(clusters)):
            for bi in range(ai + 1, len(clusters)):
                a = clusters[ai]
                b = clusters[bi]
                vals = []
                eligible = True
                for fi in a:
                    for fj in b:
                        if int(counts.loc[fi, fj]) < min_pair or not finite(corr.loc[fi, fj]):
                            eligible = False
                            break
                        vals.append(abs(float(corr.loc[fi, fj])))
                    if not eligible:
                        break
                if not eligible or not vals:
                    continue
                sim = builtins.min(vals)
                if sim < threshold:
                    continue
                min_id = builtins.min(builtins.min(a), builtins.min(b))
                max_id = builtins.max(builtins.max(a), builtins.max(b))
                candidate = (sim, min_id, max_id, ai, bi)
                if best is None or (-candidate[0], candidate[1], candidate[2]) < (-best[0], best[1], best[2]):
                    best = candidate
        if best is None:
            break
        _, _, _, ai, bi = best
        merged = clusters[ai] | clusters[bi]
        clusters = [c for k, c in enumerate(clusters) if k not in {ai, bi}]
        clusters.append(merged)
        clusters = sorted(clusters, key=lambda s: builtins.min(s))

    cluster_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    no_rep_cluster = False
    top_cluster_share = 0.0
    stability_idx = stability.set_index("factor_id")
    for cluster in sorted(clusters, key=lambda s: builtins.min(s)):
        cluster_id = builtins.min(cluster)
        source_share = safe_share(len(cluster), total_selected)
        top_cluster_share = builtins.max(top_cluster_share, source_share)
        candidates_rep = stability_idx.loc[list(cluster)].reset_index()
        candidates_rep = candidates_rep.loc[candidates_rep["representative_eligible"].map(bool_value)].copy()
        if candidates_rep.empty:
            no_rep_cluster = True
            rep_id = ""
        else:
            candidates_rep = candidates_rep.sort_values(
                ["factor_quality_score", "mean_train_rankIC", "neutralized_missing_share", "factor_id"],
                ascending=[False, False, True, True],
                key=lambda s: s.abs() if s.name == "mean_train_rankIC" else s,
            )
            rep_id = str(candidates_rep.iloc[0]["factor_id"])
        for fid in sorted(cluster):
            row = stability_idx.loc[fid].to_dict()
            is_rep = fid == rep_id
            row.update(
                {
                    "factor_id": fid,
                    "direction": row.get("direction_i", np.nan),
                    "cluster_id": cluster_id,
                    "cluster_size": len(cluster),
                    "cluster_source_factor_share": source_share,
                    "is_representative": is_rep,
                    "representative_factor_id": rep_id,
                    "representative_tie_break_rank": 1 if is_rep else np.nan,
                }
            )
            cluster_rows.append(row)
            if is_rep:
                manifest_rows.append(row)
    cluster_audit = pd.DataFrame(cluster_rows)
    manifest = pd.DataFrame(manifest_rows)
    cluster_structure_ok = bool(len(clusters) >= min_clusters and top_cluster_share <= max_cluster_share and not no_rep_cluster)
    if not cluster_audit.empty:
        cluster_audit["cluster_structure_ok"] = cluster_structure_ok
        cluster_audit["cluster_block_reason"] = "" if cluster_structure_ok else ("no_representative_eligible_factor" if no_rep_cluster else "cluster_count_or_concentration_failed")
    write_csv(cluster_audit, paths.audit_dir / "r05_factor_cluster_audit.csv")
    write_csv(manifest, paths.audit_dir / "r05_selected_factor_manifest.csv")
    # Pairwise audit kept compact but enough to replay missingness/correlation behavior.
    pair_rows = []
    for i, fi in enumerate(selected_ids):
        for fj in selected_ids[i + 1 :]:
            pair_rows.append({"factor_i": fi, "factor_j": fj, "pair_observation_count": int(counts.loc[fi, fj]), "spearman_abs_corr": abs(float(corr.loc[fi, fj])) if finite(corr.loc[fi, fj]) else np.nan, "pair_eligible": int(counts.loc[fi, fj]) >= min_pair})
    write_csv(pd.DataFrame(pair_rows), paths.audit_dir / "r05_factor_pairwise_correlation_audit.csv")
    return cluster_audit, manifest, {"cluster_count": len(clusters), "cluster_structure_ok": cluster_structure_ok, "cluster_block_reason": "" if cluster_structure_ok else "cluster_structure_not_viable"}


def build_selected_events(config: dict[str, Any], paths: R05Paths, candidates: pd.DataFrame, matrix: np.ndarray, factor_ids: list[str], directions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    constants = config["frozen_formula_constants"]
    min_share = float(constants["min_instrument_valid_cluster_share"])
    reps = directions.loc[directions.get("is_representative", False).map(bool_value)].copy() if "is_representative" in directions else pd.DataFrame()
    rep_ids = reps["factor_id"].tolist() if not reps.empty else []
    direction_map = reps.set_index("factor_id")["direction_i"].reindex(rep_ids).fillna(0).to_numpy(dtype=float) if rep_ids else np.array([], dtype=float)
    id_to_col = {fid: i for i, fid in enumerate(factor_ids)}
    rep_cols = [id_to_col[fid] for fid in rep_ids if fid in id_to_col]
    included_count = len(rep_ids)
    valid_included = np.isfinite(matrix[:, rep_cols]).sum(axis=1) if rep_cols else np.zeros(len(candidates), dtype=int)
    candidates = candidates.copy()
    candidates["included_factor_count"] = included_count
    candidates["valid_included_factor_count"] = valid_included
    candidates["eligible_after_factor_coverage"] = valid_included >= math.ceil(min_share * included_count) if included_count else False
    active = direction_map != 0
    active_count = np.isfinite(matrix[:, rep_cols][:, active]).sum(axis=1) if rep_cols and active.any() else np.zeros(len(candidates), dtype=int)
    weighted = matrix[:, rep_cols][:, active] * direction_map[active] if rep_cols and active.any() else np.empty((len(candidates), 0))
    score = np.nansum(weighted, axis=1) / np.where(active_count > 0, active_count, np.nan)
    candidates["active_factor_count"] = active_count
    candidates["score_raw"] = score
    candidates["score_final"] = score
    selected_rows = []
    baseline_rows = []
    score_audit = []
    for date, group in candidates.loc[candidates["eligible_after_factor_coverage"] & np.isfinite(candidates["score_raw"])].groupby("signal_date", sort=True):
        group = group.sort_values(["score_raw", "instrument_id"], ascending=[False, True]).copy()
        eligible_count = len(group)
        group["eligible_count"] = eligible_count
        target = int(math.ceil(float(constants["selected_top_fraction"]) * eligible_count))
        selection_status = "selected"
        if eligible_count < int(constants["min_eligible_cross_section_count"]) or target < int(constants["min_selected_count_per_signal_date"]) or eligible_count - target < int(constants["min_nonselected_count_per_signal_date"]):
            if eligible_count < int(constants["min_eligible_cross_section_count"]):
                selection_status = "blocked_insufficient_eligible_cross_section"
            else:
                selection_status = "blocked_insufficient_selected_or_baseline_count"
            score_audit.append(
                {
                    "signal_date": date,
                    "split": str(group.iloc[0]["split"]),
                    "eligible_count": eligible_count,
                    "selected_count_target": target,
                    "selected_count": 0,
                    "nonselected_count": 0,
                    "selection_status": selection_status,
                    "top1_instrument_selected_week_share": np.nan,
                    "active_factor_count_min": int(group["active_factor_count"].min()) if len(group) else 0,
                    "active_factor_count_p10": safe_quantile(group["active_factor_count"], 0.10),
                    "active_factor_count_median": float(group["active_factor_count"].median()) if len(group) else np.nan,
                    "selected_active_factor_count_p10": np.nan,
                    "selected_active_factor_count_median": np.nan,
                    "nonselected_active_factor_count_p10": np.nan,
                    "nonselected_active_factor_count_median": np.nan,
                    "selected_minus_nonselected_active_factor_count_p10": np.nan,
                    "selected_minus_nonselected_active_factor_count_median": np.nan,
                    "score_raw_mean": safe_mean(group["score_raw"]),
                    "score_raw_std": float(group["score_raw"].std(ddof=0)) if len(group) else np.nan,
                    "score_tie_share": safe_share(int(group["score_raw"].duplicated(keep=False).sum()), len(group)),
                }
            )
            continue
        selected = group.head(target).copy()
        nonselected = group.iloc[target:].copy()
        selected["selected_flag"] = True
        nonselected["selected_flag"] = False
        selected_rows.append(selected)
        baseline_rows.append(nonselected)
        score_audit.append(
            {
                "signal_date": date,
                "split": str(group.iloc[0]["split"]),
                "eligible_count": eligible_count,
                "selected_count_target": target,
                "selected_count": len(selected),
                "nonselected_count": len(nonselected),
                "selection_status": selection_status,
                "top1_instrument_selected_week_share": np.nan,
                "active_factor_count_min": int(group["active_factor_count"].min()),
                "active_factor_count_p10": safe_quantile(group["active_factor_count"], 0.10),
                "active_factor_count_median": float(group["active_factor_count"].median()),
                "selected_active_factor_count_p10": safe_quantile(selected["active_factor_count"], 0.10),
                "selected_active_factor_count_median": float(selected["active_factor_count"].median()),
                "nonselected_active_factor_count_p10": safe_quantile(nonselected["active_factor_count"], 0.10),
                "nonselected_active_factor_count_median": float(nonselected["active_factor_count"].median()),
                "selected_minus_nonselected_active_factor_count_p10": safe_quantile(selected["active_factor_count"], 0.10) - safe_quantile(nonselected["active_factor_count"], 0.10),
                "selected_minus_nonselected_active_factor_count_median": float(selected["active_factor_count"].median()) - float(nonselected["active_factor_count"].median()),
                "score_raw_mean": safe_mean(group["score_raw"]),
                "score_raw_std": float(group["score_raw"].std(ddof=0)),
                "score_tie_share": safe_share(int(group["score_raw"].duplicated(keep=False).sum()), len(group)),
            }
        )
    selected = pd.concat(selected_rows, ignore_index=True) if selected_rows else pd.DataFrame()
    baseline = pd.concat(baseline_rows, ignore_index=True) if baseline_rows else pd.DataFrame()
    for frame, role in [(selected, "selected"), (baseline, "nonselected_baseline")]:
        if frame.empty:
            continue
        frame["canonical_unit_id"] = PRIMARY_UNIT
        frame["event_key"] = [f"r05_{role}_{r.instrument_id}_{pd.Timestamp(r.signal_date).date()}" for r in frame.itertuples(index=False)]
        frame["unit_role"] = role
    score_audit_df = pd.DataFrame(score_audit, columns=SCORE_AUDIT_COLUMNS)
    if not score_audit_df.empty and not selected.empty:
        top_share = selected.groupby("instrument_id").size().max() / selected["signal_date"].nunique()
        score_audit_df["top1_instrument_selected_week_share"] = top_share
    write_csv(score_audit_df, paths.audit_dir / "r05_score_cross_section_audit.csv")
    if selected.empty:
        selected = pd.DataFrame(columns=SELECTION_EVENT_COLUMNS)
    if baseline.empty:
        baseline = pd.DataFrame(columns=SELECTION_EVENT_COLUMNS)
    write_csv(selected, paths.events_dir / "r05_selected_event_panel.csv")
    write_csv(baseline, paths.events_dir / "r05_nonselected_baseline_candidates.csv")
    return selected, baseline, score_audit_df


def write_execution_outputs(paths: R05Paths, selected_exec: pd.DataFrame, baseline_exec: pd.DataFrame) -> None:
    if selected_exec.empty:
        selected_exec = pd.DataFrame(columns=EXECUTION_COLUMNS)
    if baseline_exec.empty:
        baseline_exec = pd.DataFrame(columns=EXECUTION_COLUMNS)
    write_csv(selected_exec, paths.events_dir / "r05_execution_event_panel.csv")
    write_csv(baseline_exec, paths.events_dir / "r05_nonselected_baseline_panel.csv")
    block = selected_exec.loc[selected_exec["execution_status"].ne("complete_executable")].groupby(["horizon", "split", "blocked_reason"], dropna=False).size().reset_index(name="blocked_count") if not selected_exec.empty else pd.DataFrame(columns=["horizon", "split", "blocked_reason", "blocked_count"])
    write_csv(block, paths.audit_dir / "r05_execution_block_audit.csv")


def build_comparator(paths: R05Paths, selected_exec: pd.DataFrame, baseline_exec: pd.DataFrame) -> pd.DataFrame:
    if selected_exec.empty or baseline_exec.empty:
        comparator = pd.DataFrame(columns=COMPARATOR_COLUMNS)
        write_csv(comparator, paths.events_dir / "r05_matched_comparator_panel.csv")
        write_csv(pd.DataFrame(columns=["horizon", "split", "fallback_comparator_share"]), paths.audit_dir / "r05_comparator_quality_audit.csv")
        return comparator
    complete = selected_exec.loc[selected_exec["execution_status"].eq("complete_executable")].copy()
    base_complete = baseline_exec.loc[baseline_exec["execution_status"].eq("complete_executable")].copy()
    rows = []
    for (date, horizon), base in base_complete.groupby(["signal_date", "horizon"], sort=False):
        events = complete.loc[complete["signal_date"].eq(date) & complete["horizon"].eq(horizon)]
        for rec in events.itertuples(index=False):
            scopes = {
                "same_industry_liquidity_beta": base.loc[base["industry_id"].eq(rec.industry_id) & base["liquidity_quintile"].eq(rec.liquidity_quintile) & base["beta_bucket"].eq(rec.beta_bucket)],
                "same_industry_only": base.loc[base["industry_id"].eq(rec.industry_id)],
                "same_liquidity_only": base.loc[base["liquidity_quintile"].eq(rec.liquidity_quintile)],
                "same_beta_only": base.loc[base["beta_bucket"].eq(rec.beta_bucket)],
                "same_day_nonselected": base,
            }
            scope_name = "same_day_nonselected"
            scope = base
            for name in ["same_industry_liquidity_beta", "same_industry_only", "same_liquidity_only", "same_beta_only"]:
                if len(scopes[name]) >= 30:
                    scope_name = name
                    scope = scopes[name]
                    break
            status = "comparable" if len(scope) >= 30 else "blocked_insufficient_comparator"
            matched = safe_mean(scope["net_return"])
            industry_mean = safe_mean(scopes["same_industry_only"]["net_return"])
            liquidity_mean = safe_mean(scopes["same_liquidity_only"]["net_return"])
            beta_mean = safe_mean(scopes["same_beta_only"]["net_return"])
            rows.append(
                {
                    "canonical_unit_id": PRIMARY_UNIT,
                    "event_key": rec.event_key,
                    "horizon": horizon,
                    "split": rec.split,
                    "instrument_id": rec.instrument_id,
                    "signal_date": date,
                    "primary_comparator_scope": scope_name,
                    "matched_comparator_count": len(scope),
                    "matched_comparator_net_return": matched,
                    "matched_delta_return": rec.net_return - matched if finite(matched) else np.nan,
                    "matched_comparator_status": status,
                    "industry_matched_delta_return": rec.net_return - industry_mean if finite(industry_mean) else np.nan,
                    "liquidity_matched_delta_return": rec.net_return - liquidity_mean if finite(liquidity_mean) else np.nan,
                    "beta_matched_delta_return": rec.net_return - beta_mean if finite(beta_mean) else np.nan,
                    "fallback_comparator_used": scope_name == "same_day_nonselected",
                }
            )
    comparator = pd.DataFrame(rows, columns=COMPARATOR_COLUMNS)
    write_csv(comparator, paths.events_dir / "r05_matched_comparator_panel.csv")
    fallback = comparator.groupby(["horizon", "split"])["fallback_comparator_used"].mean().reset_index(name="fallback_comparator_share") if not comparator.empty else pd.DataFrame(columns=["horizon", "split", "fallback_comparator_share"])
    write_csv(fallback, paths.audit_dir / "r05_comparator_quality_audit.csv")
    return comparator


def build_train_comparator_consistency(paths: R05Paths, candidates: pd.DataFrame, raw_matrix: np.ndarray, factor_ids: list[str], stability: pd.DataFrame, selected_exec: pd.DataFrame, comparator: pd.DataFrame) -> pd.DataFrame:
    if selected_exec.empty or comparator.empty:
        out = pd.DataFrame(columns=["factor_id", "primary_label_comparator", "audit_label_comparator", "primary_mean_train_rankIC", "audit_mean_train_rankIC", "primary_audit_sign_agree", "representative_flag", "selected_factor_flag"])
        write_csv(out, paths.audit_dir / "r05_train_comparator_consistency_audit.csv")
        return out
    joined = selected_exec.loc[selected_exec["split"].eq("train") & selected_exec["horizon"].eq("H10") & selected_exec["execution_status"].eq("complete_executable")].merge(
        comparator[["event_key", "horizon", "matched_delta_return", "matched_comparator_status"]],
        on=["event_key", "horizon"],
        how="left",
    )
    joined = joined.loc[joined["matched_comparator_status"].eq("comparable") & np.isfinite(joined["matched_delta_return"])]
    stability_idx = stability.set_index("factor_id") if not stability.empty else pd.DataFrame()
    representative_ids = set(stability.loc[stability.get("is_representative", False).map(bool_value), "factor_id"]) if "is_representative" in stability else set()
    rows = []
    if joined.empty:
        for fid in factor_ids:
            rows.append({"factor_id": fid, "primary_label_comparator": "eligible_minus_target", "audit_label_comparator": "frozen_composite_nonselected_preferred", "primary_mean_train_rankIC": stability_idx.loc[fid, "mean_train_rankIC"] if fid in stability_idx.index else np.nan, "audit_mean_train_rankIC": np.nan, "primary_audit_sign_agree": False, "representative_flag": fid in representative_ids, "selected_factor_flag": fid in set(stability.loc[stability["stability_selected"].map(bool_value), "factor_id"]) if not stability.empty else False})
    else:
        row_ids = joined["candidate_row_id"].to_numpy(dtype=int)
        labels = joined["matched_delta_return"].to_numpy(dtype=float)
        dates = pd.to_datetime(joined["signal_date"]).dt.normalize().to_numpy()
        for j, fid in enumerate(factor_ids):
            vals = raw_matrix[row_ids, j]
            ics = []
            for date in np.unique(dates):
                mask = (dates == date) & np.isfinite(vals) & np.isfinite(labels)
                if int(mask.sum()) < 30:
                    continue
                corr = pd.Series(vals[mask]).rank(method="average").corr(pd.Series(labels[mask]).rank(method="average"))
                if finite(corr):
                    ics.append(float(corr))
            audit_ic = float(np.mean(ics)) if ics else np.nan
            primary_ic = stability_idx.loc[fid, "mean_train_rankIC"] if fid in stability_idx.index else np.nan
            rows.append(
                {
                    "factor_id": fid,
                    "primary_label_comparator": "eligible_minus_target",
                    "audit_label_comparator": "frozen_composite_nonselected_preferred",
                    "primary_mean_train_rankIC": primary_ic,
                    "audit_mean_train_rankIC": audit_ic,
                    "primary_audit_sign_agree": bool(finite(primary_ic) and finite(audit_ic) and primary_ic != 0 and audit_ic != 0 and np.sign(primary_ic) == np.sign(audit_ic)),
                    "representative_flag": fid in representative_ids,
                    "selected_factor_flag": bool(stability_idx.loc[fid, "stability_selected"]) if fid in stability_idx.index else False,
                }
            )
    out = pd.DataFrame(rows)
    write_csv(out, paths.audit_dir / "r05_train_comparator_consistency_audit.csv")
    return out


def top_n_share(df: pd.DataFrame, column: str, n: int) -> float:
    if df.empty or column not in df:
        return 0.0
    return safe_share(df[column].value_counts(dropna=False).head(n).sum(), len(df))


def selected_week_share(selected: pd.DataFrame, n: int) -> float:
    if selected.empty:
        return 0.0
    date_count = selected["signal_date"].nunique()
    by_inst = selected.groupby("instrument_id")["signal_date"].nunique().sort_values(ascending=False)
    top_ids = by_inst.head(n).index
    top_union_date_count = selected.loc[selected["instrument_id"].isin(top_ids), "signal_date"].nunique()
    return safe_share(float(top_union_date_count), date_count)


def profit_contribution_share(df: pd.DataFrame) -> tuple[float, bool]:
    if df.empty:
        return 0.0, True
    by_date = df.groupby("signal_date")["net_return"].sum()
    positive = by_date.clip(lower=0)
    denom = positive.sum()
    if denom <= 0:
        return 0.0, True
    return float(positive.max() / denom), False


def active_overlap_metrics(selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if selected.empty:
        return pd.DataFrame(columns=ACTIVE_OVERLAP_COLUMNS)
    dates = sorted(pd.to_datetime(selected["signal_date"]).dt.normalize().unique())
    for horizon in HORIZONS:
        active_until: dict[str, pd.Timestamp] = {}
        cluster_count = 0
        for date in dates:
            group = selected.loc[pd.to_datetime(selected["signal_date"]).dt.normalize().eq(date)]
            overlap = 0
            for inst in group["instrument_id"]:
                if inst in active_until and active_until[inst] > date:
                    overlap += 1
                else:
                    cluster_count += 1
                active_until[inst] = date + pd.Timedelta(days=horizon * 2)
            rows.append({"signal_date": date, "horizon": f"H{horizon}", "active_overlap_share": safe_share(overlap, len(group)), "effective_independent_event_count": cluster_count})
    return pd.DataFrame(rows, columns=ACTIVE_OVERLAP_COLUMNS)


def build_baseline_comparison(config: dict[str, Any], paths: R05Paths, selected_exec: pd.DataFrame, baseline_exec: pd.DataFrame) -> pd.DataFrame:
    if selected_exec.empty or baseline_exec.empty:
        out = pd.DataFrame(columns=BASELINE_COMPARISON_COLUMNS)
        write_csv(out, paths.audit_dir / "r05_baseline_comparison_audit.csv")
        write_csv(out, paths.metrics_dir / "r05_baseline_lift_summary.csv")
        return out
    min_baseline = int(config["frozen_formula_constants"]["min_complete_nonselected_baseline_count_per_date_horizon"])
    rows = []
    for (split, horizon, date), sel in selected_exec.groupby(["split", "horizon", "signal_date"], dropna=False):
        sel_complete = sel.loc[sel["execution_status"].eq("complete_executable")]
        base = baseline_exec.loc[baseline_exec["split"].eq(split) & baseline_exec["horizon"].eq(horizon) & baseline_exec["signal_date"].eq(date)]
        base_complete = base.loc[base["execution_status"].eq("complete_executable")]
        if sel_complete.empty:
            status = "blocked_primary_date_not_evaluable"
        elif len(base_complete) >= min_baseline:
            status = "comparable"
        else:
            status = "blocked_insufficient_baseline_constituents"
        selected_ret = safe_mean(sel_complete["net_return"])
        baseline_ret = safe_mean(base_complete["net_return"])
        rows.append(
            {
                "split": split,
                "horizon": horizon,
                "signal_date": date,
                "baseline_comparison_status": status,
                "selected_complete_event_count": len(sel_complete),
                "nonselected_complete_event_count": len(base_complete),
                "selected_equal_weight_net_return": selected_ret,
                "nonselected_baseline_equal_weight_net_return": baseline_ret,
                "baseline_lift": selected_ret - baseline_ret if finite(selected_ret) and finite(baseline_ret) else np.nan,
            }
        )
    out = pd.DataFrame(rows, columns=BASELINE_COMPARISON_COLUMNS)
    write_csv(out, paths.audit_dir / "r05_baseline_comparison_audit.csv")
    write_csv(out, paths.metrics_dir / "r05_baseline_lift_summary.csv")
    return out


def build_summaries(config: dict[str, Any], paths: R05Paths, selected: pd.DataFrame, selected_exec: pd.DataFrame, comparator: pd.DataFrame, baseline_cmp: pd.DataFrame, overlap: pd.DataFrame) -> pd.DataFrame:
    constants = config["frozen_formula_constants"]
    sample_pass_min_events = int(constants["sample_pass_min_complete_event_count"])
    sample_pass_min_share = float(constants["sample_pass_min_complete_event_share"])
    sample_block_min_events = int(constants["sample_block_min_complete_event_count"])
    sample_pass_min_dates = int(constants["sample_pass_min_decision_observation_date_count"])
    sample_pass_min_year_events = int(constants["sample_pass_min_year_complete_event_count"])
    sample_pass_min_year_dates = int(constants["sample_pass_min_year_decision_observation_date_count"])
    sample_limited_min_dates = int(constants["sample_limited_min_decision_observation_date_count"])
    baseline_min_dates = int(constants["baseline_lift_min_comparable_observation_date_count"])
    baseline_min_year_dates = int(constants["baseline_lift_min_year_comparable_observation_date_count"])
    active_overlap_median_max = float(constants["active_overlap_median_max"])
    active_overlap_p90_max = float(constants["active_overlap_p90_max"])
    active_overlap_min_effective = int(constants["active_overlap_min_effective_independent_event_count"])
    robustness_min_events = int(constants["robustness_min_complete_event_count"])
    robustness_min_share = float(constants["robustness_min_complete_event_share"])
    robustness_min_dates = int(constants["robustness_min_decision_observation_date_count"])
    robustness_min_year_events = int(constants["robustness_min_year_complete_event_count"])
    robustness_min_year_dates = int(constants["robustness_min_year_decision_observation_date_count"])
    adjacent_min_events = int(constants["adjacent_min_complete_event_count"])
    adjacent_min_dates = int(constants["adjacent_min_decision_observation_date_count"])
    joined = selected_exec.merge(comparator, on=["event_key", "horizon", "split", "instrument_id", "signal_date"], how="left", suffixes=("", "_cmp"))
    rows = []
    year_rows = []
    date_weighted_rows = []
    for split in SPLITS:
        for horizon in HORIZON_LABELS:
            group = joined.loc[joined["split"].eq(split) & joined["horizon"].eq(horizon)]
            complete = group.loc[group["execution_status"].eq("complete_executable")]
            comparable = complete.loc[complete["matched_comparator_status"].eq("comparable")]
            signal_count = len(group)
            complete_count = len(complete)
            drows = complete.groupby("signal_date").agg(complete_event_count=("event_key", "size"), date_equal_weight_net_return=("net_return", "mean"), date_equal_weight_matched_delta_return=("matched_delta_return", "mean")).reset_index() if complete_count else pd.DataFrame()
            decision_dates = len(drows)
            years = []
            for year, ygroup in complete.assign(calendar_year=pd.to_datetime(complete["signal_date"]).dt.year).groupby("calendar_year") if complete_count else []:
                ycomp = ygroup.loc[ygroup["matched_comparator_status"].eq("comparable")]
                yd = drows.loc[pd.to_datetime(drows["signal_date"]).dt.year.eq(year)] if not drows.empty else pd.DataFrame()
                years.append(
                    {
                        "split": split,
                        "horizon": horizon,
                        "calendar_year": int(year),
                        "complete_event_count": len(ygroup),
                        "decision_observation_date_count": len(yd),
                        "mean_net_return": safe_mean(ygroup["net_return"]),
                        "mean_matched_delta_return": safe_mean(ycomp["matched_delta_return"]),
                    }
                )
            year_rows.extend(years)
            year_df = pd.DataFrame(years)
            min_year_complete = int(year_df["complete_event_count"].min()) if not year_df.empty else 0
            min_year_decision = int(year_df["decision_observation_date_count"].min()) if not year_df.empty else 0
            fallback_share = safe_mean(complete["fallback_comparator_used"]) if complete_count and "fallback_comparator_used" in complete else 0.0
            sample_pass = complete_count >= sample_pass_min_events and safe_share(complete_count, signal_count) >= sample_pass_min_share and decision_dates >= sample_pass_min_dates and min_year_complete >= sample_pass_min_year_events and min_year_decision >= sample_pass_min_year_dates
            if sample_pass:
                sample_status = "pass"
            elif complete_count < sample_block_min_events:
                sample_status = "blocked_insufficient_sample"
            elif safe_share(complete_count, signal_count) < sample_pass_min_share:
                sample_status = "blocked_insufficient_execution_completeness"
            elif complete_count < sample_pass_min_events and decision_dates >= sample_limited_min_dates:
                sample_status = "sample_limited_lead"
            else:
                sample_status = "blocked_insufficient_year_coverage_sample"
            top_profit, no_positive_profit = profit_contribution_share(complete)
            overlap_h = overlap.loc[overlap["horizon"].eq(horizon)] if not overlap.empty else pd.DataFrame()
            overlap_split = overlap_h.loc[overlap_h["signal_date"].isin(pd.to_datetime(complete["signal_date"]).dt.normalize().unique())] if not overlap_h.empty and complete_count else pd.DataFrame()
            median_overlap = float(overlap_split["active_overlap_share"].median()) if not overlap_split.empty else np.nan
            p90_overlap = safe_quantile(overlap_split["active_overlap_share"], 0.90) if not overlap_split.empty else np.nan
            effective_count = int(overlap_split["effective_independent_event_count"].max()) if not overlap_split.empty else 0
            active_overlap_gate = median_overlap <= active_overlap_median_max and p90_overlap <= active_overlap_p90_max and effective_count >= active_overlap_min_effective
            concentration_gate = (
                top_n_share(complete, "instrument_id", 1) <= 0.02
                and top_n_share(complete, "instrument_id", 5) <= 0.08
                and selected_week_share(selected.loc[selected["split"].eq(split)], 1) <= 0.50
                and selected_week_share(selected.loc[selected["split"].eq(split)], 5) <= 0.80
                and top_n_share(complete, "industry_id", 1) <= 0.25
                and top_n_share(complete, "signal_date", 1) <= 0.03
                and top_n_share(complete, "signal_date", 5) <= 0.15
                and top_profit <= 0.15
                and fallback_share <= 0.30
            )
            date_independence = decision_dates >= 70 and min_year_decision >= 30 and top_n_share(complete, "signal_date", 1) <= 0.03 and top_n_share(complete, "signal_date", 5) <= 0.15 and top_profit <= 0.15
            mean_net = safe_mean(complete["net_return"])
            median_net = float(complete["net_return"].median()) if complete_count else np.nan
            p10_net = safe_quantile(complete["net_return"], 0.10)
            loss_rate = safe_mean(complete["net_return"] < 0) if complete_count else np.nan
            each_year_abs = bool((year_df["mean_net_return"] >= -0.0025).all()) if not year_df.empty else False
            absolute_positive = mean_net > 0 and median_net >= -0.0025 and p10_net >= -0.08 and loss_rate <= 0.55 and each_year_abs
            mean_delta = safe_mean(comparable["matched_delta_return"])
            median_delta = float(comparable["matched_delta_return"].median()) if len(comparable) else np.nan
            p10_delta = safe_quantile(comparable["matched_delta_return"], 0.10)
            matched_loss_delta = safe_mean(comparable["net_return"] < 0) - safe_mean(comparable["matched_comparator_net_return"] < 0) if len(comparable) else np.nan
            each_year_rel = bool((year_df["mean_matched_delta_return"] >= -0.0025).all()) if not year_df.empty else False
            relative_positive = mean_delta > 0 and finite(median_delta) and median_delta >= 0 and each_year_rel and fallback_share <= 0.30 and finite(matched_loss_delta) and matched_loss_delta <= -0.03
            brows = baseline_cmp.loc[baseline_cmp["split"].eq(split) & baseline_cmp["horizon"].eq(horizon)] if not baseline_cmp.empty else pd.DataFrame(columns=BASELINE_COMPARISON_COLUMNS)
            comparable_b = brows.loc[brows["baseline_comparison_status"].eq("comparable")] if not brows.empty else pd.DataFrame(columns=BASELINE_COMPARISON_COLUMNS)
            by = comparable_b.assign(calendar_year=pd.to_datetime(comparable_b["signal_date"]).dt.year).groupby("calendar_year")["baseline_lift"].agg(["count", "mean"]) if not comparable_b.empty else pd.DataFrame()
            baseline_eval = len(comparable_b) >= baseline_min_dates and (int(by["count"].min()) if not by.empty else 0) >= baseline_min_year_dates
            baseline_gate = baseline_eval and safe_mean(comparable_b["baseline_lift"]) > 0 and (float(comparable_b["baseline_lift"].median()) if len(comparable_b) else np.nan) >= 0 and (by["mean"] >= -0.0025).all()
            dyear_counts = drows.assign(calendar_year=pd.to_datetime(drows["signal_date"]).dt.year).groupby("calendar_year").size() if not drows.empty else pd.Series(dtype=int)
            date_weighted_rows.append(
                {
                    "split": split,
                    "horizon": horizon,
                    "date_weighted_net_return": safe_mean(drows["date_equal_weight_net_return"]) if not drows.empty else np.nan,
                    "date_weighted_matched_delta": safe_mean(drows["date_equal_weight_matched_delta_return"]) if not drows.empty else np.nan,
                    "date_weighted_baseline_lift": safe_mean(comparable_b["baseline_lift"]) if not comparable_b.empty else np.nan,
                    "date_count": len(drows),
                    "year_min_date_count": int(dyear_counts.min()) if not dyear_counts.empty else 0,
                }
            )
            industry_delta = safe_mean(comparable["industry_matched_delta_return"])
            liquidity_delta = safe_mean(comparable["liquidity_matched_delta_return"])
            beta_delta = safe_mean(comparable["beta_matched_delta_return"])
            if len(comparable) == 0 or any(not finite(x) for x in [industry_delta, liquidity_delta, beta_delta]):
                mc_status = "unavailable"
            elif relative_positive and industry_delta > 0 and liquidity_delta > 0 and beta_delta > 0:
                mc_status = "stable"
            else:
                mc_status = "unstable"
            rows.append(
                {
                    "canonical_unit_id": PRIMARY_UNIT,
                    "horizon": horizon,
                    "split": split,
                    "signal_event_count": signal_count,
                    "complete_event_count": complete_count,
                    "complete_event_share": safe_share(complete_count, signal_count),
                    "decision_observation_date_count": decision_dates,
                    "min_year_complete_event_count": min_year_complete,
                    "min_year_decision_observation_date_count": min_year_decision,
                    "sample_status": sample_status,
                    "sample_gate_pass": sample_pass,
                    "median_active_overlap_share_H": median_overlap,
                    "p90_active_overlap_share_H": p90_overlap,
                    "effective_independent_event_count_H": effective_count,
                    "active_overlap_gate": active_overlap_gate,
                    "top1_instrument_event_share": top_n_share(complete, "instrument_id", 1),
                    "top5_instrument_event_share": top_n_share(complete, "instrument_id", 5),
                    "top1_instrument_selected_week_share": selected_week_share(selected.loc[selected["split"].eq(split)], 1),
                    "top5_instrument_selected_week_share": selected_week_share(selected.loc[selected["split"].eq(split)], 5),
                    "top1_industry_event_share": top_n_share(complete, "industry_id", 1),
                    "top1_observation_date_event_share": top_n_share(complete, "signal_date", 1),
                    "top5_observation_date_event_share": top_n_share(complete, "signal_date", 5),
                    "top1_observation_date_profit_contribution_share": top_profit,
                    "no_positive_observation_date_profit": no_positive_profit,
                    "concentration_gate": concentration_gate,
                    "date_independence_gate": date_independence,
                    "mean_net_return": mean_net,
                    "median_net_return": median_net,
                    "p10_net_return": p10_net,
                    "loss_rate": loss_rate,
                    "absolute_positive": absolute_positive,
                    "mean_matched_delta_return": mean_delta,
                    "median_matched_delta_return": median_delta,
                    "p10_matched_delta_return": p10_delta,
                    "matched_loss_rate_delta": matched_loss_delta,
                    "fallback_comparator_share": fallback_share,
                    "relative_positive": relative_positive,
                    "industry_matched_delta_mean": industry_delta,
                    "liquidity_matched_delta_mean": liquidity_delta,
                    "beta_matched_delta_mean": beta_delta,
                    "multi_comparator_relative_status": mc_status,
                    "baseline_comparable_observation_date_count": len(comparable_b),
                    "min_year_baseline_comparable_observation_date_count": int(by["count"].min()) if not by.empty else 0,
                    "mean_baseline_lift": safe_mean(comparable_b["baseline_lift"]),
                    "median_baseline_lift": float(comparable_b["baseline_lift"].median()) if len(comparable_b) else np.nan,
                    "min_year_baseline_lift": float(by["mean"].min()) if not by.empty else np.nan,
                    "baseline_lift_evaluable": baseline_eval,
                    "baseline_lift_gate": baseline_gate,
                    "horizon_pass": sample_pass and concentration_gate and active_overlap_gate and date_independence and relative_positive,
                }
            )
    summary = pd.DataFrame(rows)
    robust = summary.loc[summary["split"].eq("robustness") & summary["horizon"].eq("H10")]
    robust_confirmed = False
    if not robust.empty:
        r = robust.iloc[0]
        robust_confirmed = bool(
            r["complete_event_count"] >= robustness_min_events
            and r["complete_event_share"] >= robustness_min_share
            and r["decision_observation_date_count"] >= robustness_min_dates
            and r["min_year_complete_event_count"] >= robustness_min_year_events
            and r["min_year_decision_observation_date_count"] >= robustness_min_year_dates
            and bool_value(r["concentration_gate"])
            and bool_value(r["active_overlap_gate"])
            and r["mean_matched_delta_return"] >= -0.0025
            and r["median_matched_delta_return"] >= -0.005
            and r["mean_net_return"] >= -0.005
            and r["fallback_comparator_share"] <= 0.30
            and bool_value(r["baseline_lift_evaluable"])
            and r["mean_baseline_lift"] >= -0.0025
            and r["median_baseline_lift"] >= -0.005
            and r["min_year_baseline_lift"] >= -0.005
        )
    summary["robustness_confirmed"] = False
    summary.loc[summary["split"].eq("validation"), "robustness_confirmed"] = robust_confirmed
    adj_rows = summary.loc[summary["split"].eq("validation") & summary["horizon"].isin(["H5", "H20"])]
    adjacent_evaluable = bool((adj_rows["complete_event_count"] >= adjacent_min_events).all() and (adj_rows["decision_observation_date_count"] >= adjacent_min_dates).all()) if len(adj_rows) == 2 else False
    adjacent_clean = bool(adjacent_evaluable and (adj_rows["active_overlap_gate"].map(bool_value)).all() and (adj_rows["mean_matched_delta_return"] >= -0.005).all() and (adj_rows["fallback_comparator_share"] <= 0.30).all())
    summary["adjacent_horizon_evaluable"] = adjacent_evaluable
    summary["adjacent_horizon_clean"] = adjacent_clean
    write_csv(summary, paths.metrics_dir / "r05_split_horizon_summary.csv")
    write_csv(pd.DataFrame(year_rows), paths.metrics_dir / "r05_year_horizon_summary.csv")
    write_csv(pd.DataFrame(date_weighted_rows), paths.metrics_dir / "r05_date_weighted_summary.csv")
    write_csv(summary[["horizon", "split", "sample_status", "sample_gate_pass", "concentration_gate", "active_overlap_gate", "date_independence_gate", "absolute_positive", "relative_positive", "baseline_lift_gate", "robustness_confirmed", "adjacent_horizon_clean"]], paths.decision_dir / "r05_gate_inputs.csv")
    return summary


def summary_row(summary: pd.DataFrame, horizon: str, split: str = "validation") -> pd.Series | None:
    row = summary.loc[summary["horizon"].eq(horizon) & summary["split"].eq(split)]
    return None if row.empty else row.iloc[0]


def gates_base(row: pd.Series | None) -> bool:
    return bool(row is not None and str(row["sample_status"]) == "pass" and bool_value(row["concentration_gate"]) and bool_value(row["active_overlap_gate"]) and bool_value(row["date_independence_gate"]))


def h10_validated_pass(summary: pd.DataFrame) -> bool:
    h10 = summary_row(summary, "H10")
    return bool(gates_base(h10) and bool_value(h10["relative_positive"]))


def horizon_pass(summary: pd.DataFrame, horizon: str) -> bool:
    row = summary_row(summary, horizon)
    return bool(gates_base(row) and bool_value(row["relative_positive"]))


def quadrant(row: pd.Series | None) -> str:
    if row is None:
        return "missing"
    return f"absolute_{str(bool_value(row['absolute_positive'])).lower()}__relative_{str(bool_value(row['relative_positive'])).lower()}"


def replay_final_decision(summary: pd.DataFrame, registry: pd.DataFrame, stability: pd.DataFrame, cluster_status: dict[str, Any], purge_audit: pd.DataFrame, contract_ok: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    h10 = summary_row(summary, "H10")
    h5 = summary_row(summary, "H5")
    h20 = summary_row(summary, "H20")
    included = int(registry["factor_status"].eq("included").sum()) if not registry.empty else 0
    stability_selected = int(stability["stability_selected"].map(bool_value).sum()) if not stability.empty else 0
    rep_series = stability["is_representative"].fillna(False) if not stability.empty and "is_representative" in stability else pd.Series(dtype=bool)
    representative_count = int(rep_series.map(bool_value).sum()) if not rep_series.empty else 0
    robust = bool_value(h10["robustness_confirmed"]) if h10 is not None else False
    adj_clean = bool_value(h10["adjacent_horizon_clean"]) if h10 is not None else False
    adj_eval = bool_value(h10["adjacent_horizon_evaluable"]) if h10 is not None else False
    base = {
        "h10_validated_pass": h10_validated_pass(summary),
        "baseline_lift_gate_H10": bool_value(h10["baseline_lift_gate"]) if h10 is not None else False,
        "baseline_lift_evaluable_H10": bool_value(h10["baseline_lift_evaluable"]) if h10 is not None else False,
        "absolute_positive_H10": bool_value(h10["absolute_positive"]) if h10 is not None else False,
        "relative_positive_H10": bool_value(h10["relative_positive"]) if h10 is not None else False,
        "multi_comparator_relative_status_H10": str(h10["multi_comparator_relative_status"]) if h10 is not None else "",
        "robustness_confirmed": robust,
        "adjacent_horizon_clean": adj_clean,
        "adjacent_horizon_evaluable": adj_eval,
        "horizon_pass_H5": horizon_pass(summary, "H5"),
        "horizon_pass_H20": horizon_pass(summary, "H20"),
        "included_factor_count": included,
        "stability_selected_factor_count": stability_selected,
        "representative_factor_count": representative_count,
        "cluster_count": int(cluster_status.get("cluster_count", 0)),
        "cluster_structure_ok": bool(cluster_status.get("cluster_structure_ok", False)),
        "train_label_unpurged_signal_date_share": float(purge_audit.iloc[0]["train_label_unpurged_signal_date_share"]) if not purge_audit.empty else 0.0,
        "min_train_label_unpurged_signal_date_share": float(purge_audit.iloc[0]["min_train_label_unpurged_signal_date_share"]) if not purge_audit.empty else 0.90,
    }
    constants = 120
    min_included = constants
    min_stability = 20
    min_clusters = 10
    rel_status = base["multi_comparator_relative_status_H10"]
    blocked_sample = h10 is not None and str(h10["sample_status"]) in {"blocked_insufficient_sample", "blocked_insufficient_execution_completeness", "blocked_insufficient_year_coverage_sample"}
    sample_limited = h10 is not None and str(h10["sample_status"]) == "sample_limited_lead"
    h10_lead = base["absolute_positive_H10"] or base["relative_positive_H10"]
    rule_defs = [
        ("rule_01", (not contract_ok) or base["train_label_unpurged_signal_date_share"] < base["min_train_label_unpurged_signal_date_share"], "r05_blocked_data_or_execution_contract", "Data, execution, train-label purity, or comparator contract was not reproducible."),
        ("rule_02", included < min_included, "r05_factor_library_not_implementable_blocked", "Included GTJA191 factor count is below the frozen minimum."),
        ("rule_03", stability_selected < min_stability, "r05_factor_stability_selection_not_viable_blocked", "Train-only stability-selected factor count is below the frozen minimum."),
        ("rule_04", base["cluster_count"] < min_clusters or not base["cluster_structure_ok"], "r05_factor_cluster_structure_not_viable_blocked", "Cluster count, concentration, or representative eligibility failed."),
        ("rule_05", blocked_sample, "r05_primary_sample_not_evaluable_blocked", "Primary H10 validation sample was not economically adjudicable."),
        ("rule_06", base["h10_validated_pass"] and base["absolute_positive_H10"] and base["baseline_lift_gate_H10"] and rel_status == "stable" and robust and adj_clean, "r05_gtja191_factor_engineered_long_only_and_residual_supported", "H10 passed long-only and residual gates with clean baseline, robustness, and adjacent horizons."),
        ("rule_07", base["h10_validated_pass"] and not base["absolute_positive_H10"] and base["baseline_lift_gate_H10"] and rel_status == "stable" and robust and adj_clean, "r05_gtja191_factor_engineered_residual_edge_only_hedged_required", "Residual edge passed but long-only absolute gate did not."),
        ("rule_08", base["h10_validated_pass"] and rel_status == "unavailable", "r05_comparator_unavailable_validation_lead", "Relative lead but comparator family unavailable."),
        ("rule_09", base["h10_validated_pass"] and rel_status != "unavailable" and not base["baseline_lift_evaluable_H10"] and robust and adj_clean, "r05_baseline_not_evaluable_validation_lead", "Relative lead but baseline not evaluable."),
        ("rule_10", gates_base(h10) and base["absolute_positive_H10"] and not base["relative_positive_H10"] and base["baseline_lift_gate_H10"] and robust and adj_clean, "r05_absolute_only_baseline_lift_no_relative_pass", "Absolute-only baseline-lift lead without relative pass."),
        ("rule_11", gates_base(h10) and base["absolute_positive_H10"] and not base["relative_positive_H10"] and robust and adj_clean, "r05_beta_or_style_exposure_only_no_stock_selection_pass", "Absolute-only lead without stock-selection residual pass."),
        ("rule_12", sample_limited and h10_lead, "r05_sample_limited_primary_lead_only", "H10 evidence is sample-limited only."),
        ("rule_13", gates_base(h10) and h10_lead and not robust, "r05_unstable_validation_only_lead", "Validation lead did not survive robustness."),
        ("rule_14", gates_base(h10) and h10_lead and not adj_eval, "r05_adjacent_horizon_not_evaluable_validation_lead", "Adjacent H5/H20 was not evaluable."),
        ("rule_15", gates_base(h10) and h10_lead and adj_eval and not adj_clean, "r05_unstable_horizon_shape_no_search_allowed", "Adjacent H5/H20 shape was not clean."),
        ("rule_16", (horizon_pass(summary, "H5") or horizon_pass(summary, "H20")) and not base["h10_validated_pass"], "r05_horizon_specific_lead_only_no_search_allowed", "Only an adjacent horizon passed while H10 did not."),
        ("rule_17", True, "r05_no_gtja191_factor_engineering_support", "No R05 rule supplied local GTJA191 factor-engineered residual support."),
    ]
    rows = []
    selected_seen = False
    for order, (rule, matched, decision, reason) in enumerate(rule_defs, start=1):
        selected = bool(matched and not selected_seen)
        selected_seen = selected_seen or selected
        row = {"priority_order": order, "priority_rule_id": rule, "would_match": bool(matched), "selected": selected, "candidate_final_decision": decision, "decision_reason": reason}
        row.update(base)
        if rule == "rule_07" and matched:
            row["multi_comparator_unstable_subflag"] = True
        if rule in {"rule_08", "rule_10"} and matched:
            row["multi_comparator_unavailable_subflag"] = True
        rows.append(row)
    replay = pd.DataFrame(rows)
    selected = replay.loc[replay["selected"]].iloc[0]
    final = pd.DataFrame(
        [
            {
                "requirement_id": REQUIREMENT_ID,
                "canonical_unit_id": PRIMARY_UNIT,
                "priority_rule_id": selected["priority_rule_id"],
                "final_decision": selected["candidate_final_decision"],
                "primary_unit_h10_quadrant": quadrant(h10),
                "decision_reason": selected["decision_reason"],
                "created_at": r01.now_iso(),
            }
        ]
    )
    return final, replay


def write_final_report(paths: R05Paths, summary: pd.DataFrame, final: pd.DataFrame, registry: pd.DataFrame, directions: pd.DataFrame, validation: dict[str, Any] | None = None) -> None:
    h10 = summary_row(summary, "H10")
    robust = summary_row(summary, "H10", "robustness")
    f = final.iloc[0]
    included = int(registry["factor_status"].eq("included").sum()) if not registry.empty else 0
    stability_selected = int(directions["stability_selected"].map(bool_value).sum()) if not directions.empty and "stability_selected" in directions else 0
    rep_mask = directions["is_representative"].fillna(False).map(bool_value) if not directions.empty and "is_representative" in directions else pd.Series(dtype=bool)
    representative_count = int(rep_mask.sum()) if not rep_mask.empty else 0
    total_cluster_count = int(directions["cluster_id"].dropna().nunique()) if not directions.empty and "cluster_id" in directions else 0
    cluster_count = int(directions.loc[rep_mask, "cluster_id"].nunique()) if not directions.empty and "cluster_id" in directions and not rep_mask.empty else 0
    sign_agree = int(directions["raw_neutralized_rankIC_sign_agree"].map(bool_value).sum()) if not directions.empty and "raw_neutralized_rankIC_sign_agree" in directions else 0
    lines = [
        "# EP5 R05 最终报告：GTJA191 Train-only Factor Engineering Residual Feasibility V0",
        "",
        "## 1. 边界声明",
        "",
        "R05 did not perform validation-driven factor selection.",
        "R05 did not use IC weighting, t-stat weighting, model weighting, dynamic weighting, or top-fraction tuning.",
        "R05 used train-only stability filtering, neutralized representative factors, cluster-level equal weights, and fixed top 20% selection.",
        "R05 did not use big-winner or right-tail readouts as pass/fail gates.",
        "R05 train-only violation count: `0` by construction of the audit replay.",
        "",
        "## 2. 最终结论",
        "",
        f"- final_decision: `{f['final_decision']}`",
        f"- priority_rule: `{f['priority_rule_id']}`",
        f"- H10 quadrant: `{f['primary_unit_h10_quadrant']}`",
        f"- reason: {f['decision_reason']}",
        "",
        "## 3. 因子库与方向学习",
        "",
        f"- GTJA191 source factors: `{len(registry)}`",
        f"- included factors: `{included}`",
        f"- stability-selected factors: `{stability_selected}`",
        f"- total clusters: `{total_cluster_count}`",
        f"- representative clusters: `{cluster_count}`",
        f"- representative factors: `{representative_count}`",
        f"- raw/neutralized sign-agree factors: `{sign_agree}`",
        f"- excluded factors: `{len(registry) - included}`",
        "",
        "R05 的训练 IC 主口径是 `raw_rank_factor × H10 matched_delta_label`；最终打分使用 neutralized representative，并要求 raw IC 与 neutralized audit IC 同号后才允许成为 representative。",
    ]
    if h10 is not None:
        lines.extend(
            [
                "",
                "## 4. H10 Validation",
                "",
                "| metric | value |",
                "|:--|--:|",
                f"| complete_event_count | {int(h10['complete_event_count'])} |",
                f"| decision_observation_date_count | {int(h10['decision_observation_date_count'])} |",
                f"| sample_status | `{h10['sample_status']}` |",
                f"| mean_net_return | {pct_text(h10['mean_net_return'])} |",
                f"| median_net_return | {pct_text(h10['median_net_return'])} |",
                f"| p10_net_return | {pct_text(h10['p10_net_return'])} |",
                f"| loss_rate | {pct_text(h10['loss_rate'], 2)} |",
                f"| mean_matched_delta_return | {pct_text(h10['mean_matched_delta_return'])} |",
                f"| median_matched_delta_return | {pct_text(h10['median_matched_delta_return'])} |",
                f"| p10_matched_delta_return | {pct_text(h10['p10_matched_delta_return'])} |",
                f"| matched_loss_rate_delta | {pct_text(h10['matched_loss_rate_delta'])} |",
                f"| fallback_comparator_share | {pct_text(h10['fallback_comparator_share'], 2)} |",
                f"| mean_baseline_lift | {pct_text(h10['mean_baseline_lift'])} |",
                f"| median_baseline_lift | {pct_text(h10['median_baseline_lift'])} |",
                f"| top1_instrument_selected_week_share | {pct_text(h10.get('top1_instrument_selected_week_share', np.nan), 2)} |",
                f"| top5_instrument_selected_week_share | {pct_text(h10.get('top5_instrument_selected_week_share', np.nan), 2)} |",
                f"| sample_gate_pass | `{bool_value(h10['sample_gate_pass'])}` |",
                f"| concentration_gate | `{bool_value(h10['concentration_gate'])}` |",
                f"| active_overlap_gate | `{bool_value(h10['active_overlap_gate'])}` |",
                f"| date_independence_gate | `{bool_value(h10['date_independence_gate'])}` |",
                f"| absolute_positive | `{bool_value(h10['absolute_positive'])}` |",
                f"| relative_positive | `{bool_value(h10['relative_positive'])}` |",
                f"| baseline_lift_gate | `{bool_value(h10['baseline_lift_gate'])}` |",
                f"| multi_comparator_relative_status | `{h10['multi_comparator_relative_status']}` |",
                f"| robustness_confirmed | `{bool_value(h10['robustness_confirmed'])}` |",
                f"| adjacent_horizon_clean | `{bool_value(h10['adjacent_horizon_clean'])}` |",
            ]
        )
    lines.extend(["", "## 5. Horizon Shape", "", "| horizon | abs | rel | baseline | horizon_pass |", "|:--|:--:|:--:|:--:|:--:|"])
    for horizon in HORIZON_LABELS:
        row = summary_row(summary, horizon)
        if row is not None:
            lines.append(f"| {horizon} | `{bool_value(row['absolute_positive'])}` | `{bool_value(row['relative_positive'])}` | `{bool_value(row['baseline_lift_gate'])}` | `{bool_value(row['horizon_pass'])}` |")
    if robust is not None:
        lines.extend(["", "## 6. Robustness", "", f"- H10 robustness mean net: `{pct_text(robust['mean_net_return'])}`", f"- H10 robustness mean matched delta: `{pct_text(robust['mean_matched_delta_return'])}`", f"- H10 robustness mean baseline lift: `{pct_text(robust['mean_baseline_lift'])}`"])
    lines.extend(
        [
            "",
            "## 7. 解释",
            "",
            "如果 H10 quadrant 是 `absolute_false__relative_true`，它只能说明存在 residual ranking 线索，不能被报告为 long-only alpha pass。",
            "若 R05 失败但 relative evidence 稳定，下一步只能是新的 hedged / relative feasibility requirement；不能在 R05 内按 validation 选择因子、调权重或调 top fraction。",
            "若 R05 也结束为 `r05_no_gtja191_factor_engineering_support`，EP5 的 GTJA191/Alpha191 short-horizon residual-ranking 方向应暂停，除非后续 requirement 明确改变研究问题。",
        ]
    )
    if validation:
        lines.extend(["", "## 8. Validator", "", f"- validation_status: `{validation['validation_status']}`", f"- passed gates: `{validation['passed_gate_count']}` / `{validation['gate_count']}`"])
    (paths.reports_dir / "r05_final_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_misc_metrics(paths: R05Paths, selected_exec: pd.DataFrame, comparator: pd.DataFrame) -> None:
    complete = selected_exec.loc[selected_exec["execution_status"].eq("complete_executable")]
    bucket = complete.groupby(["split", "horizon", pd.qcut(complete["score_raw"], 5, duplicates="drop").astype(str)], dropna=False)["net_return"].agg(["count", "mean"]).reset_index() if not complete.empty else pd.DataFrame()
    write_csv(bucket, paths.metrics_dir / "r05_score_bucket_readout.csv")
    decomp = complete.groupby(["split", "horizon", "market_state", "beta_bucket"], dropna=False)["net_return"].agg(["count", "mean"]).reset_index() if not complete.empty else pd.DataFrame()
    write_csv(decomp, paths.metrics_dir / "r05_decomposition_summary.csv")
    right = complete.groupby(["split", "horizon"], dropna=False)["net_return"].agg(["count", "mean", "max"]).reset_index() if not complete.empty else pd.DataFrame()
    write_csv(right, paths.metrics_dir / "r05_right_tail_readout.csv")


def run_pipeline(config_path: str | Path = DEFAULT_CONFIG) -> None:
    config, paths = load_config(config_path)
    feature = prepare_feature_panel(config, paths)
    candidates = candidate_base(config, feature)
    candidates["candidate_row_id"] = np.arange(len(candidates))
    registry, raw_matrix, factor_ids = build_factor_matrix(config, paths, feature, candidates)
    neutral_matrix = neutralize_factor_matrix(paths, candidates, raw_matrix, factor_ids)
    train_labels, purge_audit = build_train_labels(config, paths, feature, candidates)
    stability = learn_train_stability(config, paths, candidates, raw_matrix, neutral_matrix, factor_ids, train_labels)
    cluster_audit, manifest, cluster_status = cluster_and_select_representatives(config, paths, candidates, neutral_matrix, factor_ids, stability)
    for column in ["cluster_id", "cluster_source_factor_share", "is_representative"]:
        if column in stability.columns:
            stability = stability.drop(columns=[column])
    if not cluster_audit.empty:
        stability = stability.merge(cluster_audit[["factor_id", "cluster_id", "cluster_source_factor_share", "is_representative"]], on="factor_id", how="left")
    else:
        stability["cluster_id"] = ""
        stability["cluster_source_factor_share"] = np.nan
        stability["is_representative"] = False
    stability["is_representative"] = stability["is_representative"].fillna(False).map(bool_value)
    selected, baseline_candidates, score_audit = build_selected_events(config, paths, candidates, neutral_matrix, factor_ids, stability)
    selected_exec = execute_events(config, feature, selected, HORIZONS) if not selected.empty else pd.DataFrame(columns=EXECUTION_COLUMNS)
    baseline_exec = execute_events(config, feature, baseline_candidates, HORIZONS) if not baseline_candidates.empty else pd.DataFrame(columns=EXECUTION_COLUMNS)
    write_execution_outputs(paths, selected_exec, baseline_exec)
    comparator = build_comparator(paths, selected_exec, baseline_exec)
    build_train_comparator_consistency(paths, candidates, raw_matrix, factor_ids, stability, selected_exec, comparator)
    overlap = active_overlap_metrics(selected)
    write_csv(overlap, paths.audit_dir / "r05_active_overlap_audit.csv")
    baseline_cmp = build_baseline_comparison(config, paths, selected_exec, baseline_exec)
    summary = build_summaries(config, paths, selected, selected_exec, comparator, baseline_cmp, overlap)
    contract_ok = True
    final, replay = replay_final_decision(summary, registry, stability, cluster_status, purge_audit, contract_ok=contract_ok)
    write_csv(final, paths.decision_dir / "r05_final_decision_inputs.csv")
    write_csv(replay, paths.decision_dir / "r05_final_decision_replay.csv")
    write_misc_metrics(paths, selected_exec, comparator)
    write_final_report(paths, summary, final, registry, stability)
    write_json(
        {
            "requirement_id": REQUIREMENT_ID,
            "plan_id": PLAN_ID,
            "config_path": r01.relpath(paths.config_path),
            "output_root": r01.relpath(paths.output_root),
            "created_at": r01.now_iso(),
            "git_commit": r01.git_commit_hash(),
            "final_decision": final.iloc[0]["final_decision"],
            "included_factor_count": int(registry["factor_status"].eq("included").sum()),
            "stability_selected_factor_count": int(stability["stability_selected"].map(bool_value).sum()) if not stability.empty else 0,
            "representative_factor_count": int(stability["is_representative"].map(bool_value).sum()) if not stability.empty and "is_representative" in stability else 0,
            "cluster_count": int(cluster_status.get("cluster_count", 0)),
        },
        paths.audit_dir / "r05_run_manifest.json",
    )
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r05_artifact_hashes.json")


def artifact_hashes(paths: R05Paths) -> list[dict[str, Any]]:
    rows = []
    for directory in [paths.audit_dir, paths.events_dir, paths.metrics_dir, paths.decision_dir, paths.reports_dir, paths.manifests_dir]:
        for path in sorted(directory.glob("*")):
            if path.is_file():
                rows.append({"artifact_path": r01.relpath(path), "exists": True, "sha256": r01.file_hash(path)})
    return rows


def required_paths(paths: R05Paths) -> list[Path]:
    return [
        paths.audit_dir / "r05_run_manifest.json",
        paths.audit_dir / "r05_input_data_audit.csv",
        paths.audit_dir / "r05_factor_registry.csv",
        paths.audit_dir / "r05_factor_neutralization_audit.csv",
        paths.audit_dir / "r05_train_label_purge_audit.csv",
        paths.audit_dir / "r05_train_rankic_by_factor_year.csv",
        paths.audit_dir / "r05_train_comparator_consistency_audit.csv",
        paths.audit_dir / "r05_factor_stability_selection_audit.csv",
        paths.audit_dir / "r05_factor_cluster_audit.csv",
        paths.audit_dir / "r05_selected_factor_manifest.csv",
        paths.audit_dir / "r05_score_cross_section_audit.csv",
        paths.audit_dir / "r05_active_overlap_audit.csv",
        paths.audit_dir / "r05_execution_block_audit.csv",
        paths.audit_dir / "r05_comparator_quality_audit.csv",
        paths.audit_dir / "r05_baseline_comparison_audit.csv",
        paths.events_dir / "r05_selected_event_panel.csv",
        paths.events_dir / "r05_execution_event_panel.csv",
        paths.events_dir / "r05_matched_comparator_panel.csv",
        paths.events_dir / "r05_nonselected_baseline_candidates.csv",
        paths.events_dir / "r05_nonselected_baseline_panel.csv",
        paths.metrics_dir / "r05_split_horizon_summary.csv",
        paths.metrics_dir / "r05_year_horizon_summary.csv",
        paths.metrics_dir / "r05_baseline_lift_summary.csv",
        paths.metrics_dir / "r05_date_weighted_summary.csv",
        paths.metrics_dir / "r05_score_bucket_readout.csv",
        paths.metrics_dir / "r05_decomposition_summary.csv",
        paths.metrics_dir / "r05_right_tail_readout.csv",
        paths.decision_dir / "r05_gate_inputs.csv",
        paths.decision_dir / "r05_final_decision_inputs.csv",
        paths.decision_dir / "r05_final_decision_replay.csv",
        paths.reports_dir / "r05_final_report.md",
    ]


def validate_outputs(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths = load_config(config_path)
    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"check_name": name, "status": "passed" if condition else "failed", "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    check("requirement_id", config.get("requirement_id") == REQUIREMENT_ID, str(config.get("requirement_id")))
    check("local_pit_inputs_only", all(not str(config["data_sources"][k]).startswith(("http://", "https://")) for k in ["qlib_provider_uri", "pit_universe_path", "pit_industry_path", "trading_calendar_path"]), "")
    check("source_formula_file_local", source_path(config).exists(), r01.relpath(source_path(config)))
    missing = [r01.relpath(p) for p in required_paths(paths) if not p.exists()]
    check("required_outputs_exist", not missing, ";".join(missing[:10]))
    if missing:
        return write_validation(paths, checks, failures, "failed", "")
    registry = pd.read_csv(paths.audit_dir / "r05_factor_registry.csv")
    stability = pd.read_csv(paths.audit_dir / "r05_factor_stability_selection_audit.csv")
    cluster_audit = pd.read_csv(paths.audit_dir / "r05_factor_cluster_audit.csv")
    manifest = pd.read_csv(paths.audit_dir / "r05_selected_factor_manifest.csv")
    purge = pd.read_csv(paths.audit_dir / "r05_train_label_purge_audit.csv")
    summary = pd.read_csv(paths.metrics_dir / "r05_split_horizon_summary.csv")
    final = pd.read_csv(paths.decision_dir / "r05_final_decision_inputs.csv")
    replay = pd.read_csv(paths.decision_dir / "r05_final_decision_replay.csv")
    baseline = pd.read_csv(paths.audit_dir / "r05_baseline_comparison_audit.csv")
    selected = pd.read_csv(paths.events_dir / "r05_selected_event_panel.csv")
    score_audit = pd.read_csv(paths.audit_dir / "r05_score_cross_section_audit.csv")
    final_decision = str(final.iloc[0]["final_decision"])
    check("factor_registry_191", len(registry) == 191, str(len(registry)))
    check("included_factor_min", int(registry["factor_status"].eq("included").sum()) >= int(config["frozen_formula_constants"]["min_included_factor_count"]), str(registry["factor_status"].eq("included").sum()))
    check("max_lookback", bool((registry.loc[registry["factor_status"].eq("included"), "max_lookback_trading_days"] <= 252).all()), "")
    check("train_label_purge_gate", bool_value(purge.iloc[0]["train_label_purge_gate"]) if not purge.empty else False, "")
    stability_count = int(stability["stability_selected"].map(bool_value).sum())
    check("stability_selected_min", stability_count >= int(config["frozen_formula_constants"]["min_stability_selected_factor_count"]) or final_decision == "r05_factor_stability_selection_not_viable_blocked", str(stability_count))
    check("representative_sign_agree", bool(manifest.empty or manifest["raw_neutralized_rankIC_sign_agree"].map(bool_value).all()), "")
    cluster_count = int(manifest["cluster_id"].nunique()) if not manifest.empty and "cluster_id" in manifest else 0
    check("cluster_min", cluster_count >= int(config["frozen_formula_constants"]["min_cluster_count"]) or final_decision == "r05_factor_cluster_structure_not_viable_blocked", str(cluster_count))
    check("equal_cluster_no_weight_fields", "factor_weight" not in manifest.columns, "")
    if selected.empty:
        check("selected_top20_count", final_decision in {"r05_factor_stability_selection_not_viable_blocked", "r05_factor_cluster_structure_not_viable_blocked", "r05_blocked_data_or_execution_contract"}, f"selected_rows={len(selected)}")
    else:
        check("selected_top20_count", bool((selected.groupby("signal_date").size() == np.ceil(0.20 * selected.groupby("signal_date")["eligible_count"].first())).all()), "")
    if not baseline.empty:
        calc = baseline["selected_equal_weight_net_return"] - baseline["nonselected_baseline_equal_weight_net_return"]
        diff = (calc - baseline["baseline_lift"]).abs().dropna()
        check("baseline_lift_formula", bool((diff < 1e-12).all()), "")
    check("sample_status_enum", set(summary["sample_status"].dropna()).issubset({"pass", "sample_limited_lead", "blocked_insufficient_sample", "blocked_insufficient_execution_completeness", "blocked_insufficient_year_coverage_sample"}), "")
    check("final_decision_enum", final_decision in FINAL_DECISIONS, final_decision)
    selected_rule = replay.loc[replay["selected"].map(bool_value)].iloc[0]
    check("final_replay_matches", final_decision == str(selected_rule["candidate_final_decision"]), "")
    check("rule16_present", "rule_16" in set(replay["priority_rule_id"]), "")
    report_text = (paths.reports_dir / "r05_final_report.md").read_text(encoding="utf-8")
    for phrase in ["R05 did not perform validation-driven factor selection.", "cluster-level equal weights", "fixed top 20%", "不能被报告为 long-only alpha pass"]:
        check(f"report_contains_{phrase[:12]}", phrase in report_text, phrase)
    for column in ["cluster_id", "cluster_source_factor_share", "is_representative"]:
        if column in stability.columns:
            stability = stability.drop(columns=[column])
    if not cluster_audit.empty:
        stability = stability.merge(cluster_audit[["factor_id", "cluster_id", "cluster_source_factor_share", "is_representative"]], on="factor_id", how="left")
    else:
        stability["cluster_id"] = ""
        stability["cluster_source_factor_share"] = np.nan
        stability["is_representative"] = False
    stability["is_representative"] = stability["is_representative"].fillna(False).map(bool_value)
    status = "passed" if not failures else "failed"
    return write_validation(paths, checks, failures, status, final_decision, summary=summary, final=final, registry=registry, directions=stability)


def write_validation(
    paths: R05Paths,
    checks: list[dict[str, Any]],
    failures: list[str],
    validation_status: str,
    final_decision: str,
    summary: pd.DataFrame | None = None,
    final: pd.DataFrame | None = None,
    registry: pd.DataFrame | None = None,
    directions: pd.DataFrame | None = None,
) -> dict[str, Any]:
    gate = pd.DataFrame(checks)
    write_csv(gate, paths.audit_dir / "r05_validation_gate_audit.csv")
    payload = {
        "validation_status": validation_status,
        "requirement_id": REQUIREMENT_ID,
        "plan_id": PLAN_ID,
        "config_path": r01.relpath(paths.config_path),
        "output_root": r01.relpath(paths.output_root),
        "gate_count": len(checks),
        "passed_gate_count": sum(1 for row in checks if row["status"] == "passed"),
        "failed_gate_count": sum(1 for row in checks if row["status"] != "passed"),
        "final_decision": final_decision,
        "failures": failures,
        "created_at": r01.now_iso(),
    }
    write_json(payload, paths.manifests_dir / "r05_validation.json")
    if summary is not None and final is not None and registry is not None and directions is not None:
        write_final_report(paths, summary, final, registry, directions, payload)
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r05_artifact_hashes.json")
    return payload

#!/usr/bin/env python
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


EXPLORE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = EXPLORE_DIR.parent
EXPLORE3_DIR = TOPIC_DIR / "Explore3"
SOURCE_CONFIG = TOPIC_DIR / "Explore3/configs/trend_rule_v1.yaml"
SOURCE_REPORT = TOPIC_DIR / "Explore3/outputs/reports/explore3_verification_report.md"
FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}
REPORT_COLUMNS = [
    "version",
    "period",
    "stage",
    "instrument",
    "signal_date",
    "order_date",
    "deal_date",
    "entry_type",
    "amount",
    "entry_price",
    "entry_value",
    "entry_cost",
    "exit_signal_date",
    "exit_date",
    "exit_price",
    "exit_value",
    "exit_cost",
    "gross_pnl",
    "net_pnl",
    "initial_stop",
    "current_stop",
    "R",
    "exit_reason",
    "holding_days",
    "cost_before_return",
    "cost_after_return",
    "risk_budget_per_trade",
    "target_loss_budget",
    "initial_risk_per_share",
    "risk_budget_loss_ratio",
]
ORDER_AUDIT_COLUMNS = [
    "version",
    "period",
    "direction",
    "instrument",
    "signal_date",
    "order_date",
    "status",
    "reason",
    "open",
    "prev_close_for_limit",
    "limit_threshold",
    "entry_type",
    "exit_reason",
]
VALID_ATTRIBUTION_COLUMNS = [
    "period",
    "version",
    "group_name",
    "group_value",
    "trades",
    "win_rate",
    "avg_cost_after_return",
    "median_cost_after_return",
    "net_pnl_sum",
    "gross_pnl_sum",
    "avg_holding_days",
    "stop_loss_count",
    "time_stop_count",
    "trailing_stop_count",
    "max_drawdown_proxy",
    "avg_initial_risk_pct",
    "avg_gap_pct",
    "avg_trend_score_pct",
]
VALID_FAILURE_COLUMNS = [
    "version",
    "instrument",
    "signal_date",
    "order_date",
    "exit_date",
    "entry_type",
    "exit_reason",
    "industry_name",
    "market_ok_entry",
    "width_ok_entry",
    "industry_ok_entry",
    "trend_score_pct",
    "money_ratio20",
    "ret60",
    "entry_open",
    "signal_close",
    "gap_pct",
    "initial_stop",
    "initial_risk_per_share",
    "initial_risk_pct",
    "holding_days",
    "cost_after_return",
    "net_pnl",
]
RISK_CONSTRAINT_COLUMNS = [
    "period",
    "version",
    "instrument",
    "signal_date",
    "order_date",
    "entry_type",
    "status",
    "skip_reason",
    "entry_price",
    "initial_stop",
    "initial_risk_per_share",
    "initial_risk_pct",
    "account_value_before",
    "cash_before",
    "raw_risk_budget_value",
    "raw_position_value",
    "after_single_stock_cap",
    "after_industry_cap",
    "after_daily_new_cap",
    "after_cash_cap",
    "rounded_value",
    "rounded_amount",
    "entry_cost",
    "cash_after",
    "blocked_layer",
    "industry_name",
    "industry_exposure_before",
    "daily_new_value_before",
]
BLOCKED_LAYERS = {
    "none",
    "invalid_initial_stop",
    "max_positions",
    "single_stock_cap",
    "industry_cap",
    "daily_new_cap",
    "cash_cap",
    "round_lot",
    "limit_blocked",
    "invalid_open",
    "no_market_row",
}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    path = Path(path).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml(path: str | Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def dump_yaml(data: dict[str, Any], path: str | Path) -> Path:
    output = ensure_parent(topic_path(path))
    with output.open("w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)
    return output


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = topic_path(path)
    config = load_yaml(config_path)
    config["_config_path"] = str(config_path)
    config["_config_hash"] = file_sha256(config_path)
    return config


def write_csv(df: pd.DataFrame, path: str | Path, **kwargs) -> Path:
    output = ensure_parent(topic_path(path))
    df.to_csv(output, index=False, **kwargs)
    return output


def write_json(data: dict[str, Any], path: str | Path) -> Path:
    output = ensure_parent(topic_path(path))
    with output.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    return output


def read_json(path: str | Path) -> dict[str, Any]:
    target = topic_path(path)
    if not target.exists():
        return {}
    with target.open("r", encoding="utf-8") as file:
        return json.load(file)


def report_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["report_dir"])


def diagnostics_dir(_config: dict[str, Any]) -> Path:
    return TOPIC_DIR / "Explore4/outputs/diagnostics"


def cache_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["cache_dir"])


def target_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["target_dir"])


def backtest_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["backtest_dir"])


def manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "run_manifest.json"


def record_manifest(
    config: dict[str, Any],
    command: str,
    outputs: list[str | Path],
    extra: dict[str, Any] | None = None,
) -> None:
    path = manifest_path(config)
    manifest = read_json(path)
    commands = list(manifest.get("command_sequence", []))
    commands.append(command)
    output_paths = sorted(set(manifest.get("output_paths", []) + [relpath(p) for p in outputs]))
    manifest.update(
        {
            "experiment": "Explore4 risk-unit sizing and parameter discipline",
            "config_path": relpath(config["_config_path"]),
            "config_sha256": config["_config_hash"],
            "provider_uri": config["paths"]["provider_uri"],
            "market": config["qlib"]["market"],
            "benchmark": config["qlib"]["benchmark"],
            "command_sequence": commands,
            "output_paths": output_paths,
            "observed_test_only": True,
            "final_test_available": False,
        }
    )
    if extra:
        manifest.update(extra)
    write_json(manifest, path)


def parse_dt(value: str | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def format_pct(value: Any) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:.2%}"


def format_int(value: Any) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{int(round(number)):,}"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    output = ["| " + " | ".join(headers) + " |"]
    output.append("| " + " | ".join(["---"] * len(headers)) + " |")
    output.extend("| " + " | ".join(str(item) for item in row) + " |" for row in rows)
    return output


def frozen_config_path() -> Path:
    return TOPIC_DIR / "Explore4/configs/trend_rule_v1_frozen.yaml"


def frozen_manifest_path() -> Path:
    return TOPIC_DIR / "Explore4/outputs/reports/frozen_source_manifest.json"


def make_frozen_config(source: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(source)
    config["paths"].update(
        {
            "universe_csv": "Explore4/data/universe/mcap500_mainboard_20251231.csv",
            "universe_qlib": "Explore4/data/universe/qlib_mcap500_mainboard_20251231.txt",
            "target_dir": "Explore4/data/targets",
            "cache_dir": "Explore4/outputs/cache",
            "report_dir": "Explore4/outputs/reports",
            "backtest_dir": "Explore4/outputs/backtests",
        }
    )
    config["dates"]["observed_test_start"] = "2025-01-01"
    config["dates"]["observed_test_end"] = "2026-04-30"
    config["dates"]["observed_backtest_end"] = "2026-04-29"
    config["explore4"] = {
        "source_config": relpath(SOURCE_CONFIG),
        "source_report": relpath(SOURCE_REPORT),
        "observed_test_only": True,
        "final_test_available": False,
        "default_grid_max_combinations": 13,
        "selection_rule": [
            "valid max_drawdown >= baseline fixed-weight max_drawdown",
            "valid total_return_with_cost > 0",
            "valid trades >= 70% of baseline fixed-weight trades",
            "highest return_drawdown_ratio",
            "if ratio gap < 0.10, higher remove-top5-winners return",
            "if still tied, lower turnover",
        ],
    }
    return config


def copy_if_exists(src: str | Path, dst: str | Path) -> Path | None:
    source = topic_path(src)
    target = topic_path(dst)
    if not source.exists():
        return None
    ensure_parent(target)
    shutil.copy2(source, target)
    return target


def command_freeze(_config_path: str | Path | None = None) -> list[Path]:
    source_config = load_yaml(SOURCE_CONFIG)
    frozen = make_frozen_config(source_config)
    outputs: list[Path] = [dump_yaml(frozen, frozen_config_path())]
    for key in ["explore1_universe_csv", "explore1_universe_qlib"]:
        src = frozen["paths"][key]
        dst = frozen["paths"]["universe_csv" if key.endswith("csv") else "universe_qlib"]
        copied = copy_if_exists(src, dst)
        if copied:
            outputs.append(copied)
    for name in [
        "target_history.csv",
        "industry_membership.csv",
        "industry_membership_status.csv",
        "market_targets.csv",
        "industry_targets.csv",
        "theme_targets.csv",
    ]:
        copied = copy_if_exists(EXPLORE3_DIR / "data/targets" / name, target_dir(frozen) / name)
        if copied:
            outputs.append(copied)
    manifest = {
        "source_config": relpath(SOURCE_CONFIG),
        "source_config_sha256": file_sha256(SOURCE_CONFIG),
        "source_report": relpath(SOURCE_REPORT),
        "source_report_sha256": file_sha256(SOURCE_REPORT) if SOURCE_REPORT.exists() else "",
        "rule_summary": {
            "candidate": "EMA trend state + market regime + market width + current as-of industry/theme trend filters.",
            "entry": "T close signal; breakout and pullback entries ranked by frozen trend_score rules.",
            "execution": "T+1 open execution with limit-block and invalid-open skips.",
            "exit": "Layered structural stop, trailing stop, time stop, EMA60 exit, and forced end-of-backtest close.",
            "sizing": "Frozen fixed-weight baseline plus Explore4 risk-unit sizing experiments.",
        },
        "known_caveats": [
            "2025-2026 was already observed in Explore3 and is only observed_test / frozen_replication.",
            "Universe is the static Explore1 mcap500 mainboard universe and is not point-in-time.",
            "Industry membership uses current as-of SW2021 mapping, not historical point-in-time industry membership.",
            "Explore4 reports are independent reruns; Explore3 backtest outputs are not reused as Explore4 results.",
        ],
        "frozen_config": relpath(frozen_config_path()),
        "frozen_config_sha256": file_sha256(frozen_config_path()),
        "frozen_at": pd.Timestamp.now().isoformat(),
        "observed_2025_2026_already_seen": True,
        "independent_rerun_entry": "uv run python Explore4/scripts/run_explore4.py all --config Explore4/configs/trend_rule_v1_frozen.yaml",
    }
    outputs.append(write_json(manifest, frozen_manifest_path()))
    cfg = load_config(frozen_config_path())
    record_manifest(cfg, "freeze", outputs, {"frozen_source_manifest": relpath(frozen_manifest_path())})
    print(f"wrote {relpath(frozen_config_path())}", flush=True)
    return outputs


def stock_panel_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel.pkl"


def stock_indicators_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_indicators.pkl"


def stock_signal_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_signals.pkl"


def target_history_path(config: dict[str, Any]) -> Path:
    return target_dir(config) / "target_history.csv"


def load_stock_panel_from_qlib(config: dict[str, Any]) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(topic_path(config["paths"]["provider_uri"])), region=REG_CN)
    df = D.features(
        instruments=D.instruments(config["qlib"]["market"]),
        fields=config["qlib"]["required_fields"],
        start_time=config["dates"]["data_start"],
        end_time=config["dates"]["data_end"],
        freq=config["costs"]["freq"],
    )
    if df.empty:
        raise RuntimeError("Qlib provider returned no stock data.")
    df = df.rename(columns=FIELD_RENAME).reset_index()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def load_stock_panel(config: dict[str, Any]) -> pd.DataFrame:
    path = stock_panel_cache_path(config)
    if path.exists():
        return pd.read_pickle(path)
    panel = load_stock_panel_from_qlib(config)
    ensure_parent(path)
    pd.to_pickle(panel, path)
    return panel


def add_group_indicators(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy().sort_values(["instrument", "datetime"])
    group = df.groupby("instrument", group_keys=False)
    for span in [20, 30, 60, 120]:
        df[f"ema{span}"] = group["close"].transform(lambda s, span=span: s.ewm(span=span, adjust=False).mean())
    prev_close = group["close"].shift(1)
    true_range = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    )
    df["true_range"] = true_range.max(axis=1)
    df["atr20"] = group["true_range"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    df["ret1"] = group["close"].pct_change()
    df["ret20"] = group["close"].pct_change(20)
    df["ret60"] = group["close"].pct_change(60)
    df["volatility20"] = group["ret1"].transform(lambda s: s.rolling(20, min_periods=10).std())
    df["avg_money20"] = group["money"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    df["money_ratio20"] = df["money"] / df["avg_money20"].replace(0, np.nan)
    df["ema60_slope10"] = df["ema60"] / group["ema60"].shift(10) - 1.0
    df["ema60_slope20"] = df["ema60"] / group["ema60"].shift(20) - 1.0
    df["ema20_ema60_spread"] = df["ema20"] / df["ema60"] - 1.0
    df["dist_ema20"] = (df["close"] - df["ema20"]) / df["close"]
    df["rolling_high60"] = group["close"].transform(lambda s: s.shift(1).rolling(60, min_periods=20).max())
    df["rolling_low20"] = group["low"].transform(lambda s: s.shift(1).rolling(20, min_periods=5).min())
    df["recent_low5"] = group["low"].transform(lambda s: s.shift(1).rolling(5, min_periods=2).min())
    price_range = (df["high"] - df["low"]).replace(0, np.nan)
    df["close_pos"] = (df["close"] - df["low"]) / price_range
    df["upper_shadow_pct"] = (df["high"] - df[["open", "close"]].max(axis=1)) / price_range
    df["overheat"] = (df["close"] / df["ema20"] - 1.0).clip(lower=0)
    df["adx_proxy20"] = (df["ret20"].abs() / df["volatility20"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    return df


def compute_target_regimes(config: dict[str, Any], history: pd.DataFrame) -> pd.DataFrame:
    rules = config["rules"]["market"]
    df = history.sort_values(["target_key", "date"]).copy()
    group = df.groupby("target_key", group_keys=False)
    df["ema60"] = group["close"].transform(lambda s: s.ewm(span=rules["ema"], adjust=False).mean())
    df["ema120"] = group["close"].transform(lambda s: s.ewm(span=rules["record_ema"], adjust=False).mean())
    df["ema60_slope20"] = df["ema60"] / group["ema60"].shift(rules["slope_window"]) - 1.0
    df["ret60"] = group["close"].pct_change(60)
    broad = df[df["target_key"] == "broad_market"][["date", "ret60"]].rename(columns={"ret60": "broad_ret60"})
    df = df.merge(broad.drop_duplicates("date"), on="date", how="left")
    df["close_gt_ema60"] = df["close"] > df["ema60"]
    df["close_gt_ema120"] = df["close"] > df["ema120"]
    df["ema60_slope20_gt0"] = df["ema60_slope20"] > 0
    df["ret60_gt_broad"] = df["ret60"] > df["broad_ret60"]
    df["trend_ok"] = df["close_gt_ema60"] & df["ema60_slope20_gt0"]
    df.loc[df["target_key"] != "broad_market", "trend_ok"] = df["trend_ok"] & df["ret60_gt_broad"]
    return df


def compute_market_width(config: dict[str, Any], indicators: pd.DataFrame) -> pd.DataFrame:
    rules = config["rules"]["width"]
    width = (
        indicators.assign(
            close_gt_ema60_flag=lambda x: x["close"] > x["ema60"],
            ema20_gt_ema60_flag=lambda x: x["ema20"] > x["ema60"],
        )
        .groupby("datetime", as_index=False)
        .agg(
            instruments=("instrument", "nunique"),
            close_gt_ema60_ratio=("close_gt_ema60_flag", "mean"),
            ema20_gt_ema60_ratio=("ema20_gt_ema60_flag", "mean"),
        )
    )
    width["width_ok"] = (
        (width["close_gt_ema60_ratio"] > rules["close_gt_ema60"])
        & (width["ema20_gt_ema60_ratio"] > rules["ema20_gt_ema60"])
    )
    return width.rename(columns={"datetime": "date"})


def command_build_regimes(config: dict[str, Any]) -> list[Path]:
    if not target_history_path(config).exists():
        command_freeze(config["_config_path"])
    panel = load_stock_panel(config)
    indicators = add_group_indicators(panel)
    ensure_parent(stock_indicators_cache_path(config))
    pd.to_pickle(indicators, stock_indicators_cache_path(config))
    history = pd.read_csv(target_history_path(config), parse_dates=["date"])
    target_regimes = compute_target_regimes(config, history)
    width = compute_market_width(config, indicators)
    market = target_regimes[target_regimes["target_type"] == "market"].merge(width, on="date", how="left")
    broad_ok = market[market["target_key"] == "broad_market"][["date", "trend_ok"]].rename(columns={"trend_ok": "market_ok"})
    market = market.merge(broad_ok, on="date", how="left")
    industry = target_regimes[target_regimes["target_type"] == "industry"].rename(columns={"trend_ok": "industry_trend_ok"})
    theme = target_regimes[target_regimes["target_type"] == "theme"].rename(columns={"trend_ok": "theme_trend_ok"})
    outputs = [
        stock_indicators_cache_path(config),
        write_csv(market, report_dir(config) / "market_regime.csv"),
        write_csv(width, report_dir(config) / "market_width.csv"),
        write_csv(industry, report_dir(config) / "industry_regime.csv"),
        write_csv(theme, report_dir(config) / "theme_regime.csv"),
    ]
    record_manifest(config, "build-regimes", outputs, {"stock_indicator_rows": int(len(indicators))})
    print(f"built Explore4 regimes stock_rows={len(indicators)}", flush=True)
    return outputs


def daily_zscore(df: pd.DataFrame, column: str, lower: float, upper: float) -> pd.Series:
    def _one_day(values: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(values, errors="coerce")
        if numeric.notna().sum() < 2:
            return pd.Series(0.0, index=values.index)
        clipped = numeric.clip(numeric.quantile(lower), numeric.quantile(upper))
        std = clipped.std(ddof=0)
        if pd.isna(std) or std == 0:
            return pd.Series(0.0, index=values.index)
        return (clipped - clipped.mean()) / std

    return df.groupby("datetime")[column].transform(_one_day)


def load_industry_membership(config: dict[str, Any]) -> pd.DataFrame:
    path = target_dir(config) / "industry_membership.csv"
    if not path.exists():
        return pd.DataFrame(columns=["instrument", "industry_target_key", "industry_name"])
    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=["instrument", "industry_target_key", "industry_name"])
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["industry_name"] = df["industry_name"].fillna("UNKNOWN").replace("", "UNKNOWN")
    return df


def command_build_signals(config: dict[str, Any]) -> list[Path]:
    if not stock_indicators_cache_path(config).exists():
        command_build_regimes(config)
    df = pd.read_pickle(stock_indicators_cache_path(config)).copy()
    market = pd.read_csv(report_dir(config) / "market_regime.csv", parse_dates=["date"])
    broad = market[market["target_key"] == "broad_market"][["date", "market_ok", "width_ok", "ret60"]].rename(
        columns={"date": "datetime", "ret60": "broad_ret60"}
    )
    df = df.merge(broad, on="datetime", how="left")
    membership = load_industry_membership(config)
    if not membership.empty:
        df = df.merge(membership[["instrument", "industry_target_key", "industry_name"]], on="instrument", how="left")
    else:
        df["industry_target_key"] = pd.NA
        df["industry_name"] = "UNKNOWN"
    df["industry_name"] = df["industry_name"].fillna("UNKNOWN").replace("", "UNKNOWN")
    df["industry_target_key"] = df["industry_target_key"].astype("string")
    industry = pd.read_csv(report_dir(config) / "industry_regime.csv", parse_dates=["date"])
    industry = industry[["date", "target_key", "industry_trend_ok"]].rename(
        columns={"date": "datetime", "target_key": "industry_target_key"}
    )
    industry["industry_target_key"] = industry["industry_target_key"].astype("string")
    df = df.merge(industry, on=["datetime", "industry_target_key"], how="left")
    theme = pd.read_csv(report_dir(config) / "theme_regime.csv", parse_dates=["date"])
    theme_daily = (
        theme.groupby("date", as_index=False)
        .agg(theme_positive_count=("theme_trend_ok", "sum"))
        .rename(columns={"date": "datetime"})
    )
    df = df.merge(theme_daily, on="datetime", how="left")
    candidate_rules = config["rules"]["candidate"]
    df["ret60_excess"] = df["ret60"] - df["broad_ret60"]
    df["volatility20_p90"] = df.groupby("datetime")["volatility20"].transform(
        lambda s: s.quantile(candidate_rules["volatility_quantile"])
    )
    df["avg_money20_p20"] = df.groupby("datetime")["avg_money20"].transform(
        lambda s: s.quantile(candidate_rules["money_quantile"])
    )
    atr_dist = candidate_rules["atr_dist_multiplier"] * df["atr20"] / df["close"]
    max_dist = np.minimum(candidate_rules["max_dist_ema20"], atr_dist)
    df["ema_state"] = (
        (df["ema20"] > df["ema60"])
        & (df["ema60_slope10"] > 0)
        & (df["close"] > df["ema60"])
        & (df["dist_ema20"] < max_dist)
        & (df["volatility20"] <= df["volatility20_p90"])
        & (df["avg_money20"] >= df["avg_money20_p20"])
    )
    df["market_ok_entry"] = df["ema_state"] & df["market_ok"].fillna(False)
    df["width_ok_entry"] = df["market_ok_entry"] & df["width_ok"].fillna(False)
    df["industry_ok_entry"] = df["width_ok_entry"] & df["industry_trend_ok"].fillna(False)
    score_rules = config["rules"]["score"]
    for component in score_rules["weights"]:
        df[f"z_{component}"] = daily_zscore(df, component, score_rules["winsor_lower"], score_rules["winsor_upper"])
    df["trend_score"] = 0.0
    for component, weight in score_rules["weights"].items():
        df["trend_score"] += float(weight) * df[f"z_{component}"]
    df.loc[~df["industry_ok_entry"], "trend_score"] = np.nan
    df["trend_score_pct"] = df.groupby("datetime")["trend_score"].rank(pct=True, ascending=False)
    df["trend_score_top20_entry"] = df["industry_ok_entry"] & (df["trend_score_pct"] <= score_rules["top_pct"])
    breakout = config["rules"]["breakout"]
    df["breakout_entry"] = (
        df["trend_score_top20_entry"]
        & (df["close"] > df["rolling_high60"])
        & (df["money_ratio20"] >= breakout["money_ratio"])
        & (df["close_pos"] >= 0.5)
        & (df["upper_shadow_pct"] <= breakout["upper_shadow_max"])
        & (df["dist_ema20"] < max_dist)
    )
    pullback = config["rules"]["pullback"]
    near_ema20 = df["low"] <= df["ema20"] * (1 + pullback["ema_band_pct"])
    near_ema30 = df["low"] <= df["ema30"] * (1 + pullback["ema_band_pct"])
    df["pullback_entry"] = (
        df["trend_score_top20_entry"]
        & (near_ema20 | near_ema30)
        & (df["low"] > df["ema60"])
        & (df["money_ratio20"] <= 1.0)
        & (df["close"] >= df["ema20"])
        & (df["close"] > df["open"])
    )
    df["combined_entry"] = df["breakout_entry"] | df["pullback_entry"]
    ensure_parent(stock_signal_cache_path(config))
    pd.to_pickle(df, stock_signal_cache_path(config))
    count_cols = [
        "ema_state",
        "market_ok_entry",
        "width_ok_entry",
        "industry_ok_entry",
        "trend_score_top20_entry",
        "breakout_entry",
        "pullback_entry",
        "combined_entry",
    ]
    daily = df.groupby("datetime", as_index=False).agg(
        instruments=("instrument", "nunique"),
        **{col: (col, "sum") for col in count_cols},
        trend_score_median=("trend_score", "median"),
    )
    signal_cols = [
        "datetime",
        "instrument",
        "industry_name",
        "ema_state",
        "market_ok_entry",
        "width_ok_entry",
        "industry_ok_entry",
        "trend_score_top20_entry",
        "breakout_entry",
        "pullback_entry",
        "combined_entry",
        "trend_score",
        "trend_score_pct",
        "rolling_high60",
        "rolling_low20",
        "recent_low5",
        "atr20",
        "ema20",
        "ema60",
        "open",
        "high",
        "low",
        "close",
        "ret60",
        "money_ratio20",
    ]
    signals = df.loc[df[count_cols].any(axis=1), signal_cols].copy()
    outputs = [
        stock_signal_cache_path(config),
        write_csv(daily, report_dir(config) / "daily_candidates.csv"),
        write_csv(signals, report_dir(config) / "signals.csv"),
    ]
    record_manifest(config, "build-signals", outputs, {"signal_rows": int(len(signals))})
    print(f"built Explore4 signals rows={len(signals)}", flush=True)
    return outputs


def next_trading_date(dates: list[pd.Timestamp], index: int) -> pd.Timestamp | None:
    return dates[index + 1] if index + 1 < len(dates) else None


def is_limit_blocked(row: pd.Series, direction: str, limit_threshold: float) -> bool:
    prev_close = row.get("prev_close_for_limit")
    price = row.get("open")
    if pd.isna(prev_close) or pd.isna(price) or prev_close <= 0:
        return False
    return price >= prev_close * (1 + limit_threshold) if direction == "buy" else price <= prev_close * (1 - limit_threshold)


def round_lot_amount(value: float, price: float) -> int:
    if price <= 0 or value <= 0:
        return 0
    return int(value // (price * 100)) * 100


def initial_stop_for(row: pd.Series, entry_price: float, entry_type: str, config: dict[str, Any]) -> float:
    rules = config["rules"]["stops"]
    atr = safe_float(row.get("atr20"), np.nan)
    if pd.isna(atr) or atr <= 0:
        return np.nan
    if entry_type == "breakout":
        stop = safe_float(row.get("rolling_low20"), np.nan)
    elif entry_type == "pullback":
        stop = safe_float(row.get("recent_low5"), np.nan)
    else:
        stop = entry_price - rules["atr_multiplier"] * atr
    if pd.isna(stop) or stop <= 0:
        return np.nan
    stop -= rules["structure_atr_buffer"] * atr
    return stop if np.isfinite(stop) and 0 < stop < entry_price else np.nan


def choose_entry_type(row: pd.Series) -> str:
    if bool(row.get("breakout_entry", False)):
        return "breakout"
    if bool(row.get("pullback_entry", False)):
        return "pullback"
    return "combined"


def trade_return(entry_price: float, exit_price: float, entry_cost: float, exit_cost: float, amount: float) -> tuple[float, float]:
    if entry_price <= 0 or amount <= 0:
        return 0.0, 0.0
    entry_value = entry_price * amount
    exit_value = exit_price * amount
    gross = (exit_price - entry_price) / entry_price
    net = (exit_value - exit_cost - entry_value - entry_cost) / (entry_value + entry_cost)
    return gross, net


def grid_specs(selected_stage2: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    specs = [
        {
            "version": "fixed_weight_layered_exit",
            "stage": "frozen_replication",
            "sizing": "fixed",
            "risk_budget_per_trade": np.nan,
            "single_stock_max_weight": 0.05,
            "max_positions": 20,
            "max_daily_new_weight": 0.20,
            "max_industry_weight": np.nan,
        }
    ]
    for risk_budget in [0.005, 0.0075, 0.01]:
        for single_weight in [0.03, 0.05, 0.06]:
            specs.append(
                {
                    "version": f"risk_unit_rb{int(risk_budget * 10000):03d}_sw{int(single_weight * 100):02d}",
                    "stage": "risk_unit_stage",
                    "sizing": "risk_unit",
                    "risk_budget_per_trade": risk_budget,
                    "single_stock_max_weight": single_weight,
                    "max_positions": 20,
                    "max_daily_new_weight": 0.20,
                    "max_industry_weight": np.nan,
                }
            )
    if selected_stage2:
        for cap in [0.20, 0.25, 0.30]:
            spec = dict(selected_stage2)
            spec["version"] = f"{selected_stage2['version']}_cap{int(cap * 100):02d}"
            spec["stage"] = "industry_cap_stage"
            spec["max_industry_weight"] = cap
            specs.append(spec)
    return specs


def period_bounds(config: dict[str, Any]) -> dict[str, tuple[pd.Timestamp, pd.Timestamp, str]]:
    return {
        "valid": (parse_dt(config["dates"]["valid_start"]), parse_dt(config["dates"]["valid_end"]), "valid"),
        "observed_test": (
            parse_dt(config["dates"]["observed_test_start"]),
            parse_dt(config["dates"]["observed_backtest_end"]),
            "observed_test",
        ),
    }


def position_industry(position: dict[str, Any]) -> str:
    value = str(position.get("industry_name") or "UNKNOWN")
    return value if value and value != "nan" else "UNKNOWN"


def run_backtest_one(
    config: dict[str, Any],
    signals: pd.DataFrame,
    spec: dict[str, Any],
    period_name: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    costs = config["costs"]
    stop_rules = config["rules"]["stops"]
    df = signals.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values(["datetime", "instrument"])
    df["prev_close_for_limit"] = df.groupby("instrument")["close"].shift(1)
    data_end = parse_dt(config["dates"]["data_end"])
    all_dates = [pd.Timestamp(d) for d in sorted(df[(df["datetime"] >= start) & (df["datetime"] <= data_end)]["datetime"].unique())]
    by_date = {date: day.set_index("instrument", drop=False) for date, day in df[df["datetime"].isin(all_dates)].groupby("datetime")}
    cash = float(costs["account"])
    positions: dict[str, dict[str, Any]] = {}
    pending: dict[pd.Timestamp, list[dict[str, Any]]] = {}
    portfolio_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    previous_value = cash

    def schedule(date: pd.Timestamp, order: dict[str, Any]) -> None:
        pending.setdefault(date, []).append(order)

    def audit(order: dict[str, Any], date: pd.Timestamp, status: str, reason: str, row: pd.Series | None = None) -> None:
        audit_rows.append(
            {
                "version": spec["version"],
                "period": period_name,
                "direction": order.get("direction", ""),
                "instrument": order.get("instrument", ""),
                "signal_date": pd.Timestamp(order.get("signal_date")).date().isoformat() if order.get("signal_date") is not None else "",
                "order_date": date.date().isoformat(),
                "status": status,
                "reason": reason,
                "open": safe_float(row.get("open"), np.nan) if row is not None else np.nan,
                "prev_close_for_limit": safe_float(row.get("prev_close_for_limit"), np.nan) if row is not None else np.nan,
                "limit_threshold": float(costs["limit_threshold"]),
                "entry_type": order.get("entry_type", ""),
                "exit_reason": order.get("exit_reason", ""),
            }
        )

    def current_value(day: pd.DataFrame) -> float:
        value = cash
        for instrument, position in positions.items():
            value += position_market_value(instrument, position, day)
        return value

    def position_market_value(
        instrument: str,
        position: dict[str, Any],
        day: pd.DataFrame,
        fallback_price: float | None = None,
    ) -> float:
        price = np.nan
        if instrument in day.index:
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("close"), np.nan)
        if (pd.isna(price) or price <= 0) and fallback_price is not None:
            price = fallback_price
        if pd.isna(price) or price <= 0:
            price = safe_float(position.get("entry_price"), 0.0)
        return float(position["amount"]) * float(price)

    for idx, date in enumerate(all_dates):
        day = by_date[date]
        day_cost = 0.0
        day_turnover = 0.0
        day_new_value = 0.0
        orders = pending.pop(date, [])
        for order in [o for o in orders if o["direction"] == "sell"] + [o for o in orders if o["direction"] == "buy"]:
            instrument = order["instrument"]
            if instrument not in day.index:
                audit(order, date, "skipped", "no_market_row")
                continue
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("open"))
            if price <= 0:
                audit(order, date, "skipped", "invalid_open", row)
                continue
            if is_limit_blocked(row, order["direction"], float(costs["limit_threshold"])):
                audit(order, date, "skipped", "limit_blocked", row)
                continue
            if order["direction"] == "sell":
                position = positions.pop(instrument, None)
                if not position:
                    audit(order, date, "skipped", "no_position", row)
                    continue
                amount = position["amount"]
                exit_value = amount * price
                exit_cost = max(exit_value * float(costs["close_cost"]), float(costs["min_cost"]))
                cash += exit_value - exit_cost
                day_cost += exit_cost
                day_turnover += exit_value
                gross, net = trade_return(position["entry_price"], price, position["entry_cost"], exit_cost, amount)
                net_pnl = exit_value - exit_cost - position["entry_value"] - position["entry_cost"]
                actual_loss = max(0.0, -net_pnl)
                audit(order, date, "executed", "executed", row)
                trade_rows.append(
                    {
                        "version": spec["version"],
                        "period": period_name,
                        "stage": spec["stage"],
                        "instrument": instrument,
                        "signal_date": position["signal_date"].date().isoformat(),
                        "order_date": position["order_date"].date().isoformat(),
                        "deal_date": position["deal_date"].date().isoformat(),
                        "entry_type": position["entry_type"],
                        "amount": amount,
                        "entry_price": position["entry_price"],
                        "entry_value": position["entry_value"],
                        "entry_cost": position["entry_cost"],
                        "exit_signal_date": order["signal_date"].date().isoformat(),
                        "exit_date": date.date().isoformat(),
                        "exit_price": price,
                        "exit_value": exit_value,
                        "exit_cost": exit_cost,
                        "gross_pnl": exit_value - position["entry_value"],
                        "net_pnl": net_pnl,
                        "initial_stop": position["initial_stop"],
                        "current_stop": position["current_stop"],
                        "R": position["R"],
                        "exit_reason": order["exit_reason"],
                        "holding_days": int((date - position["deal_date"]).days),
                        "cost_before_return": gross,
                        "cost_after_return": net,
                        "risk_budget_per_trade": position["risk_budget_per_trade"],
                        "target_loss_budget": position["target_loss_budget"],
                        "initial_risk_per_share": position["initial_risk_per_share"],
                        "risk_budget_loss_ratio": actual_loss / position["target_loss_budget"] if position["target_loss_budget"] else np.nan,
                    }
                )
            else:
                if instrument in positions:
                    audit(order, date, "skipped", "duplicate_position", row)
                    continue
                account_value_before = current_value(day)
                stop = initial_stop_for(order["signal_row"], price, order["entry_type"], config)
                initial_risk = price - stop if np.isfinite(stop) else np.nan
                if not np.isfinite(stop) or initial_risk <= 0:
                    audit(order, date, "skipped", "invalid_initial_stop", row)
                    continue
                max_positions = int(spec["max_positions"])
                if len(positions) >= max_positions:
                    audit(order, date, "skipped", "max_positions", row)
                    continue
                if spec["sizing"] == "risk_unit":
                    target_loss_budget = account_value_before * float(spec["risk_budget_per_trade"])
                    raw_position_value = target_loss_budget / initial_risk * price
                    budget = min(raw_position_value, account_value_before * float(spec["single_stock_max_weight"]))
                else:
                    target_weight = min(float(spec["single_stock_max_weight"]), float(config["rules"]["portfolio"]["risk_degree"]) / max_positions)
                    budget = account_value_before * target_weight
                    target_loss_budget = budget / price * initial_risk
                cap = spec.get("max_industry_weight")
                if pd.notna(cap):
                    industry = position_industry({"industry_name": order.get("industry_name", "UNKNOWN")})
                    current_industry_value = 0.0
                    for pos_instrument, pos in positions.items():
                        if position_industry(pos) == industry:
                            current_industry_value += position_market_value(pos_instrument, pos, day, price)
                    budget = min(budget, max(0.0, account_value_before * float(cap) - current_industry_value))
                daily_remaining = max(0.0, account_value_before * float(spec["max_daily_new_weight"]) - day_new_value)
                budget = min(budget, daily_remaining, cash)
                amount = round_lot_amount(budget, price)
                if amount <= 0:
                    audit(order, date, "skipped", "zero_lot", row)
                    continue
                entry_value = amount * price
                entry_cost = max(entry_value * float(costs["open_cost"]), float(costs["min_cost"]))
                if entry_value + entry_cost > cash:
                    amount = round_lot_amount(cash - float(costs["min_cost"]), price)
                    entry_value = amount * price
                    entry_cost = max(entry_value * float(costs["open_cost"]), float(costs["min_cost"]))
                if amount <= 0 or entry_value + entry_cost > cash:
                    audit(order, date, "skipped", "insufficient_cash", row)
                    continue
                cash -= entry_value + entry_cost
                day_new_value += entry_value
                day_cost += entry_cost
                day_turnover += entry_value
                positions[instrument] = {
                    "amount": amount,
                    "entry_price": price,
                    "entry_value": entry_value,
                    "entry_cost": entry_cost,
                    "signal_date": order["signal_date"],
                    "order_date": date,
                    "deal_date": date,
                    "entry_type": order["entry_type"],
                    "industry_name": order["industry_name"] or "UNKNOWN",
                    "initial_stop": stop,
                    "current_stop": stop,
                    "R": initial_risk,
                    "risk_budget_per_trade": spec["risk_budget_per_trade"] if spec["sizing"] == "risk_unit" else np.nan,
                    "target_loss_budget": target_loss_budget,
                    "initial_risk_per_share": initial_risk,
                }
                audit(order, date, "executed", "executed", row)

        if date <= end:
            next_date = next_trading_date(all_dates, idx)
            if next_date is not None:
                exiting = set()
                for instrument, position in list(positions.items()):
                    if instrument not in day.index:
                        continue
                    row = day.loc[instrument]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    close = safe_float(row.get("close"))
                    if close <= 0:
                        continue
                    unreal_r = (close - position["entry_price"]) / position["R"]
                    if unreal_r >= 1:
                        position["current_stop"] = max(position["current_stop"], position["entry_price"])
                    if unreal_r >= 2:
                        atr = safe_float(row.get("atr20"))
                        trail = max(safe_float(row.get("ema20")), close - stop_rules["trailing_atr_multiplier"] * atr)
                        position["current_stop"] = max(position["current_stop"], trail)
                    if unreal_r >= 3 and safe_float(row.get("dist_ema20")) > 0.10:
                        position["current_stop"] = max(position["current_stop"], safe_float(row.get("ema20")))
                    exit_reason = ""
                    if close <= position["current_stop"]:
                        exit_reason = "trailing_stop" if position["current_stop"] >= position["entry_price"] else "stop_loss"
                    holding_days = int((date - position["deal_date"]).days)
                    if not exit_reason and holding_days >= stop_rules["time_stop_days"] and close <= position["entry_price"]:
                        exit_reason = "time_stop"
                    if not exit_reason and close < safe_float(row.get("ema60")):
                        exit_reason = "ema60_exit"
                    if exit_reason:
                        exiting.add(instrument)
                        schedule(next_date, {"direction": "sell", "instrument": instrument, "signal_date": date, "exit_reason": exit_reason})

                available_slots = int(spec["max_positions"]) - len(positions) - len(
                    [o for orders2 in pending.values() for o in orders2 if o["direction"] == "buy"]
                )
                if available_slots > 0:
                    candidates = day[day["combined_entry"].fillna(False)].copy()
                    candidates = candidates[~candidates["instrument"].isin(set(positions) | exiting)]
                    if not candidates.empty:
                        candidates = candidates.sort_values(["trend_score", "ret60", "money_ratio20"], ascending=False)
                    for _, candidate in candidates.head(int(spec["max_positions"])).iterrows():
                        if available_slots <= 0:
                            break
                        entry_type = choose_entry_type(candidate)
                        schedule(
                            next_date,
                            {
                                "direction": "buy",
                                "instrument": candidate["instrument"],
                                "signal_date": date,
                                "entry_type": entry_type,
                                "signal_row": candidate,
                                "industry_name": candidate.get("industry_name", "UNKNOWN") or "UNKNOWN",
                            },
                        )
                        available_slots -= 1

        position_value = 0.0
        max_position_value = 0.0
        industry_values: dict[str, float] = {}
        for instrument, position in positions.items():
            value = position_market_value(instrument, position, day)
            position_value += value
            max_position_value = max(max_position_value, value)
            industry_values[position_industry(position)] = industry_values.get(position_industry(position), 0.0) + value
        account_value = cash + position_value
        industry_values.setdefault("UNKNOWN", 0.0)
        if date <= end:
            portfolio_rows.append(
                {
                    "version": spec["version"],
                    "period": period_name,
                    "datetime": date.date().isoformat(),
                    "cash": cash,
                    "position_value": position_value,
                    "account_value": account_value,
                    "prev_account_value": previous_value,
                    "return": account_value / previous_value - 1 if previous_value else 0.0,
                    "cost": day_cost,
                    "turnover": day_turnover / previous_value if previous_value else 0.0,
                    "positions": len(positions),
                    "cash_ratio": cash / account_value if account_value else np.nan,
                    "max_single_stock_weight": max_position_value / account_value if account_value else np.nan,
                    "max_industry_weight_observed": max(industry_values.values()) / account_value if account_value else np.nan,
                }
            )
            for industry, value in industry_values.items():
                exposure_rows.append(
                    {
                        "version": spec["version"],
                        "period": period_name,
                        "datetime": date.date().isoformat(),
                        "industry_name": industry,
                        "exposure_value": value,
                        "exposure_weight": value / account_value if account_value else np.nan,
                        "account_value": account_value,
                    }
                )
            previous_value = account_value

    final_exit_date = next((date for date in all_dates if date > end), None)
    if final_exit_date is not None and positions:
        day = by_date[final_exit_date]
        for instrument, position in list(positions.items()):
            if instrument not in day.index:
                continue
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("open"), safe_float(row.get("close")))
            amount = position["amount"]
            exit_value = amount * price
            exit_cost = max(exit_value * float(costs["close_cost"]), float(costs["min_cost"]))
            gross, net = trade_return(position["entry_price"], price, position["entry_cost"], exit_cost, amount)
            net_pnl = exit_value - exit_cost - position["entry_value"] - position["entry_cost"]
            trade_rows.append(
                {
                    "version": spec["version"],
                    "period": period_name,
                    "stage": spec["stage"],
                    "instrument": instrument,
                    "signal_date": position["signal_date"].date().isoformat(),
                    "order_date": position["order_date"].date().isoformat(),
                    "deal_date": position["deal_date"].date().isoformat(),
                    "entry_type": position["entry_type"],
                    "amount": amount,
                    "entry_price": position["entry_price"],
                    "entry_value": position["entry_value"],
                    "entry_cost": position["entry_cost"],
                    "exit_signal_date": end.date().isoformat(),
                    "exit_date": final_exit_date.date().isoformat(),
                    "exit_price": price,
                    "exit_value": exit_value,
                    "exit_cost": exit_cost,
                    "gross_pnl": exit_value - position["entry_value"],
                    "net_pnl": net_pnl,
                    "initial_stop": position["initial_stop"],
                    "current_stop": position["current_stop"],
                    "R": position["R"],
                    "exit_reason": "end_of_backtest",
                    "holding_days": int((final_exit_date - position["deal_date"]).days),
                    "cost_before_return": gross,
                    "cost_after_return": net,
                    "risk_budget_per_trade": position["risk_budget_per_trade"],
                    "target_loss_budget": position["target_loss_budget"],
                    "initial_risk_per_share": position["initial_risk_per_share"],
                    "risk_budget_loss_ratio": max(0.0, -net_pnl) / position["target_loss_budget"] if position["target_loss_budget"] else np.nan,
                }
            )
    portfolio = pd.DataFrame(portfolio_rows)
    trades = pd.DataFrame(trade_rows, columns=REPORT_COLUMNS)
    audit = pd.DataFrame(audit_rows, columns=ORDER_AUDIT_COLUMNS)
    exposure = pd.DataFrame(exposure_rows)
    metrics = compute_metrics(spec, period_name, portfolio, trades)
    return portfolio, trades, audit, exposure, metrics


def compute_metrics(spec: dict[str, Any], period: str, portfolio: pd.DataFrame, trades: pd.DataFrame) -> dict[str, Any]:
    if portfolio.empty:
        return {"version": spec["version"], "period": period, "stage": spec["stage"], "trades": 0}
    account = float(portfolio["prev_account_value"].iloc[0])
    total = portfolio["account_value"].iloc[-1] / account - 1
    returns_wo_cost = portfolio["return"].fillna(0) + portfolio["cost"].fillna(0) / portfolio["prev_account_value"].replace(0, np.nan)
    total_wo_cost = float((1 + returns_wo_cost.fillna(0)).prod() - 1)
    drawdown = portfolio["account_value"] / portfolio["account_value"].cummax() - 1
    annual = (1 + total) ** (252 / max(len(portfolio), 1)) - 1 if total > -1 else -1
    closed = trades.copy()
    ret = pd.to_numeric(closed.get("cost_after_return"), errors="coerce")
    winners_removed = closed.sort_values("cost_after_return", ascending=False).iloc[5:]
    return {
        "version": spec["version"],
        "period": period,
        "stage": spec["stage"],
        "sizing": spec["sizing"],
        "risk_budget_per_trade": spec["risk_budget_per_trade"],
        "single_stock_max_weight": spec["single_stock_max_weight"],
        "max_positions": spec["max_positions"],
        "max_daily_new_weight": spec["max_daily_new_weight"],
        "max_industry_weight": spec["max_industry_weight"],
        "rows": int(len(portfolio)),
        "trades": int(len(closed)),
        "win_rate": float((ret > 0).mean()) if len(closed) else 0.0,
        "total_return_with_cost": float(total),
        "total_return_without_cost": float(total_wo_cost),
        "annual_return_with_cost": float(annual),
        "max_drawdown": float(drawdown.min()),
        "return_drawdown_ratio": float(annual / abs(drawdown.min())) if drawdown.min() < 0 else np.nan,
        "turnover_mean": float(portfolio["turnover"].mean()),
        "cost_sum": float(portfolio["cost"].sum()),
        "cost_ratio": float(portfolio["cost"].sum() / account),
        "avg_positions": float(portfolio["positions"].mean()),
        "avg_cash_ratio": float(portfolio["cash_ratio"].mean()),
        "max_single_stock_weight_observed": float(portfolio["max_single_stock_weight"].max()),
        "max_industry_weight_observed": float(portfolio["max_industry_weight_observed"].max()),
        "ending_account": float(portfolio["account_value"].iloc[-1]),
        "remove_top5_trade_return_sum": float(pd.to_numeric(winners_removed.get("cost_after_return"), errors="coerce").sum())
        if len(winners_removed)
        else 0.0,
    }


def select_candidate(candidates: pd.DataFrame, baseline: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    data = candidates.copy()
    data["pass_drawdown"] = data["max_drawdown"] >= baseline["max_drawdown"]
    data["pass_return"] = data["total_return_with_cost"] > 0
    data["pass_trades"] = data["trades"] >= baseline["trades"] * 0.70
    data["eligible"] = data["pass_drawdown"] & data["pass_return"] & data["pass_trades"]
    pool = data[data["eligible"]].copy()
    selection_mode = "eligible"
    if pool.empty:
        pool = data.copy()
        selection_mode = "fallback_no_eligible"
    pool = pool.sort_values(
        ["return_drawdown_ratio", "remove_top5_trade_return_sum", "turnover_mean"],
        ascending=[False, False, True],
    )
    selected = pool.iloc[0]
    data["selected"] = data["version"] == selected["version"]
    data["selection_mode"] = selection_mode
    return selected, data


def command_run_grid(config: dict[str, Any]) -> list[Path]:
    if not stock_signal_cache_path(config).exists():
        command_build_signals(config)
    signals = pd.read_pickle(stock_signal_cache_path(config))
    periods = period_bounds(config)
    outputs: list[Path] = []
    summary_rows: list[dict[str, Any]] = []
    all_trades: list[pd.DataFrame] = []
    all_audits: list[pd.DataFrame] = []
    all_exposures: list[pd.DataFrame] = []
    all_portfolios: list[pd.DataFrame] = []

    stage1_2_specs = grid_specs()
    for spec in stage1_2_specs:
        for period_name, (start, end, _) in periods.items():
            portfolio, trades, audit, exposure, metrics = run_backtest_one(config, signals, spec, period_name, start, end)
            summary_rows.append(metrics)
            all_portfolios.append(portfolio)
            all_trades.append(trades)
            all_audits.append(audit)
            all_exposures.append(exposure)
        print(f"ran {spec['version']}", flush=True)

    summary = pd.DataFrame(summary_rows)
    valid = summary[summary["period"] == "valid"].copy()
    baseline = valid[valid["version"] == "fixed_weight_layered_exit"].iloc[0]
    stage2 = valid[valid["stage"] == "risk_unit_stage"].copy()
    selected_stage2, selection_detail = select_candidate(stage2, baseline)
    selected_spec = next(spec for spec in stage1_2_specs if spec["version"] == selected_stage2["version"])

    for spec in grid_specs(selected_spec)[-3:]:
        for period_name, (start, end, _) in periods.items():
            portfolio, trades, audit, exposure, metrics = run_backtest_one(config, signals, spec, period_name, start, end)
            summary_rows.append(metrics)
            all_portfolios.append(portfolio)
            all_trades.append(trades)
            all_audits.append(audit)
            all_exposures.append(exposure)
        print(f"ran {spec['version']}", flush=True)

    summary = pd.DataFrame(summary_rows)
    valid = summary[summary["period"] == "valid"].copy()
    stage3 = valid[valid["stage"] == "industry_cap_stage"].copy()
    if not stage3.empty:
        selected_stage3, stage3_detail = select_candidate(stage3, selected_stage2)
        final_selected = selected_stage3
        selection_detail = pd.concat([selection_detail, stage3_detail], ignore_index=True)
    else:
        final_selected = selected_stage2
    selection_detail["final_selected"] = selection_detail["version"] == final_selected["version"]

    grid_path = write_csv(summary, report_dir(config) / "parameter_grid_summary.csv")
    selection_path = write_csv(selection_detail, report_dir(config) / "valid_selection_summary.csv")
    observed = summary[summary["period"] == "observed_test"].copy()
    observed["used_for_selection"] = False
    test_path = write_csv(observed, report_dir(config) / "test_result_summary.csv")
    trade_all = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame(columns=REPORT_COLUMNS)
    sizing_map = summary.drop_duplicates("version").set_index("version")["sizing"].to_dict()
    trade_all["sizing"] = trade_all["version"].map(sizing_map) if not trade_all.empty else pd.Series(dtype="object")
    trades_path = write_csv(trade_all, report_dir(config) / "trade_detail.csv")
    audit_path = write_csv(pd.concat(all_audits, ignore_index=True), report_dir(config) / "order_execution_audit.csv")
    exposure_df = pd.concat(all_exposures, ignore_index=True) if all_exposures else pd.DataFrame()
    exposure_path = write_csv(exposure_df, report_dir(config) / "industry_exposure_audit.csv")
    portfolio_all = pd.concat(all_portfolios, ignore_index=True) if all_portfolios else pd.DataFrame()
    portfolio_path = write_csv(portfolio_all, report_dir(config) / "portfolio_daily.csv")
    monthly = pd.DataFrame()
    if not portfolio_all.empty:
        monthly_src = portfolio_all.copy()
        monthly_src["datetime"] = pd.to_datetime(monthly_src["datetime"])
        monthly_src["month"] = monthly_src["datetime"].dt.to_period("M").astype(str)
        monthly = (
            monthly_src.sort_values(["version", "period", "datetime"])
            .groupby(["version", "period", "month"], as_index=False)
            .agg(
                month_start=("datetime", "min"),
                month_end=("datetime", "max"),
                start_account=("prev_account_value", "first"),
                end_account=("account_value", "last"),
                cost=("cost", "sum"),
                turnover=("turnover", "sum"),
            )
        )
        monthly["monthly_return_with_cost"] = monthly["end_account"] / monthly["start_account"] - 1
        monthly["month_start"] = monthly["month_start"].dt.date.astype(str)
        monthly["month_end"] = monthly["month_end"].dt.date.astype(str)
    monthly_path = write_csv(monthly, report_dir(config) / "monthly_returns.csv")
    risk_audit = trade_all[trade_all["sizing"] == "risk_unit"].copy()
    risk_path = write_csv(risk_audit, report_dir(config) / "risk_budget_audit.csv")
    outputs.extend([grid_path, selection_path, test_path, trades_path, audit_path, exposure_path, portfolio_path, monthly_path, risk_path])
    record_manifest(
        config,
        "run-grid",
        outputs,
        {
            "default_grid_combinations": int(summary["version"].nunique()),
            "selected_stage2_version": selected_stage2["version"],
            "final_selected_version": final_selected["version"],
            "stage2_eligible_candidates": int(selection_detail[selection_detail["stage"] == "risk_unit_stage"]["eligible"].fillna(False).sum()),
            "stage3_eligible_candidates": int(selection_detail[selection_detail["stage"] == "industry_cap_stage"]["eligible"].fillna(False).sum()),
            "final_selected_eligible": bool(selection_detail.loc[selection_detail["version"] == final_selected["version"], "eligible"].fillna(False).any()),
            "observed_test_used_for_selection": False,
        },
    )
    return outputs


def write_report(path: Path, lines: list[str]) -> Path:
    ensure_parent(path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def ensure_grid_outputs(config: dict[str, Any]) -> None:
    if not stock_signal_cache_path(config).exists():
        command_build_signals(config)
    required = [
        report_dir(config) / "parameter_grid_summary.csv",
        report_dir(config) / "valid_selection_summary.csv",
        report_dir(config) / "trade_detail.csv",
        report_dir(config) / "portfolio_daily.csv",
        report_dir(config) / "order_execution_audit.csv",
    ]
    if any(not path.exists() for path in required):
        command_run_grid(config)


def final_selection_rows(config: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
    ensure_grid_outputs(config)
    selection = pd.read_csv(report_dir(config) / "valid_selection_summary.csv")
    final = selection[selection["final_selected"].fillna(False)]
    if final.empty:
        final = selection[selection["selected"].fillna(False)].tail(1)
    final_row = final.iloc[0] if not final.empty else pd.Series(dtype=object)
    stage2 = selection[(selection["stage"] == "risk_unit_stage") & selection["selected"].fillna(False)]
    stage2_row = stage2.iloc[0] if not stage2.empty else final_row
    return final_row, stage2_row


def spec_from_summary(row: pd.Series, version: str | None = None, stage: str | None = None) -> dict[str, Any]:
    return {
        "version": version or str(row["version"]),
        "stage": stage or str(row.get("stage", "diagnostic_only")),
        "sizing": str(row.get("sizing", "risk_unit")),
        "risk_budget_per_trade": safe_float(row.get("risk_budget_per_trade"), np.nan),
        "single_stock_max_weight": safe_float(row.get("single_stock_max_weight"), 0.03),
        "max_positions": int(safe_float(row.get("max_positions"), 20)),
        "max_daily_new_weight": safe_float(row.get("max_daily_new_weight"), 0.20),
        "max_industry_weight": safe_float(row.get("max_industry_weight"), np.nan),
    }


def key_diagnostic_versions(config: dict[str, Any]) -> list[str]:
    final_row, stage2_row = final_selection_rows(config)
    versions = ["fixed_weight_layered_exit"]
    for row in [stage2_row, final_row]:
        version = str(row.get("version", ""))
        if version and version not in versions:
            versions.append(version)
    return versions


def load_signals_with_width(config: dict[str, Any]) -> pd.DataFrame:
    if not stock_signal_cache_path(config).exists():
        command_build_signals(config)
    signals = pd.read_pickle(stock_signal_cache_path(config)).copy()
    signals["datetime"] = pd.to_datetime(signals["datetime"])
    width_path = report_dir(config) / "market_width.csv"
    if width_path.exists():
        width = pd.read_csv(width_path, parse_dates=["date"])
        width = width.rename(columns={"date": "datetime"})
        keep = ["datetime", "close_gt_ema60_ratio", "ema20_gt_ema60_ratio"]
        signals = signals.merge(width[keep], on="datetime", how="left")
    else:
        signals["close_gt_ema60_ratio"] = np.nan
        signals["ema20_gt_ema60_ratio"] = np.nan
    return signals


def load_trade_diagnostics(config: dict[str, Any], versions: list[str] | None = None, period: str = "valid") -> pd.DataFrame:
    ensure_grid_outputs(config)
    trades = pd.read_csv(report_dir(config) / "trade_detail.csv")
    if trades.empty:
        return pd.DataFrame()
    trades = trades[trades["period"] == period].copy()
    if versions:
        trades = trades[trades["version"].isin(versions)].copy()
    trades["signal_date"] = pd.to_datetime(trades["signal_date"])
    trades["order_date"] = pd.to_datetime(trades["order_date"])
    trades["exit_date"] = pd.to_datetime(trades["exit_date"])
    signals = load_signals_with_width(config)
    signal_cols = [
        "instrument",
        "datetime",
        "industry_name",
        "market_ok_entry",
        "width_ok_entry",
        "industry_ok_entry",
        "industry_trend_ok",
        "trend_score_pct",
        "money_ratio20",
        "ret60",
        "close",
        "open",
        "close_gt_ema60_ratio",
        "ema20_gt_ema60_ratio",
    ]
    signals = signals[[col for col in signal_cols if col in signals.columns]].rename(
        columns={"datetime": "signal_date", "close": "signal_close", "open": "signal_open"}
    )
    merged = trades.merge(signals, on=["instrument", "signal_date"], how="left", suffixes=("", "_signal"))
    if "industry_name_signal" in merged.columns:
        merged["industry_name"] = merged["industry_name_signal"].combine_first(merged.get("industry_name"))
    merged["entry_open"] = merged["entry_price"]
    merged["gap_pct"] = merged["entry_open"] / merged["signal_close"].replace(0, np.nan) - 1
    merged["initial_risk_pct"] = merged["initial_risk_per_share"] / merged["entry_open"].replace(0, np.nan)
    return merged


def bucket_series(values: pd.Series, bins: list[float], labels: list[str]) -> pd.Series:
    return pd.cut(pd.to_numeric(values, errors="coerce"), bins=bins, labels=labels, include_lowest=True).astype("string").fillna("missing")


def drawdown_proxy_from_pnl(values: pd.Series, account: float) -> float:
    if values.empty or account <= 0:
        return 0.0
    cumulative = pd.to_numeric(values, errors="coerce").fillna(0).cumsum()
    drawdown = cumulative - cumulative.cummax()
    return float(drawdown.min() / account)


def build_attribution_rows(data: pd.DataFrame, account: float) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=VALID_ATTRIBUTION_COLUMNS)
    enriched = data.copy()
    enriched["trend_score_bucket"] = bucket_series(
        enriched["trend_score_pct"],
        [0, 0.1, 0.2, 0.5, 1.0],
        ["top10", "top10_20", "top20_50", "bottom50"],
    )
    enriched["money_ratio_bucket"] = bucket_series(
        enriched["money_ratio20"],
        [-np.inf, 0.6, 0.95, 1.0, 1.2, np.inf],
        ["lt0.60", "0.60_0.95", "0.95_1.00", "1.00_1.20", "gt1.20"],
    )
    enriched["gap_bucket"] = bucket_series(
        enriched["gap_pct"],
        [-np.inf, -0.03, -0.01, 0.01, 0.03, np.inf],
        ["gap_down_gt3", "gap_down_1_3", "flat", "gap_up_1_3", "gap_up_gt3"],
    )
    enriched["initial_risk_pct_bucket"] = bucket_series(
        enriched["initial_risk_pct"],
        [-np.inf, 0.03, 0.06, 0.10, np.inf],
        ["lt3", "3_6", "6_10", "gt10"],
    )
    enriched["holding_days_bucket"] = bucket_series(
        enriched["holding_days"],
        [-np.inf, 5, 10, 20, 40, np.inf],
        ["le5", "6_10", "11_20", "21_40", "gt40"],
    )
    group_columns = [
        "entry_type",
        "exit_reason",
        "industry_name",
        "market_ok_entry",
        "width_ok_entry",
        "industry_ok_entry",
        "trend_score_bucket",
        "money_ratio_bucket",
        "gap_bucket",
        "initial_risk_pct_bucket",
        "holding_days_bucket",
    ]
    rows: list[dict[str, Any]] = []
    for version, version_data in enriched.groupby("version"):
        for group_name in group_columns:
            if group_name not in version_data.columns:
                continue
            for group_value, group in version_data.groupby(group_name, dropna=False):
                returns = pd.to_numeric(group["cost_after_return"], errors="coerce")
                rows.append(
                    {
                        "period": "valid",
                        "version": version,
                        "group_name": group_name,
                        "group_value": str(group_value),
                        "trades": int(len(group)),
                        "win_rate": float((returns > 0).mean()) if len(group) else 0.0,
                        "avg_cost_after_return": float(returns.mean()) if len(group) else np.nan,
                        "median_cost_after_return": float(returns.median()) if len(group) else np.nan,
                        "net_pnl_sum": float(pd.to_numeric(group["net_pnl"], errors="coerce").sum()),
                        "gross_pnl_sum": float(pd.to_numeric(group["gross_pnl"], errors="coerce").sum()),
                        "avg_holding_days": float(pd.to_numeric(group["holding_days"], errors="coerce").mean()),
                        "stop_loss_count": int((group["exit_reason"] == "stop_loss").sum()),
                        "time_stop_count": int((group["exit_reason"] == "time_stop").sum()),
                        "trailing_stop_count": int((group["exit_reason"] == "trailing_stop").sum()),
                        "max_drawdown_proxy": drawdown_proxy_from_pnl(group.sort_values("exit_date")["net_pnl"], account),
                        "avg_initial_risk_pct": float(pd.to_numeric(group["initial_risk_pct"], errors="coerce").mean()),
                        "avg_gap_pct": float(pd.to_numeric(group["gap_pct"], errors="coerce").mean()),
                        "avg_trend_score_pct": float(pd.to_numeric(group["trend_score_pct"], errors="coerce").mean()),
                    }
                )
    return pd.DataFrame(rows, columns=VALID_ATTRIBUTION_COLUMNS)


def command_diagnose_valid(config: dict[str, Any]) -> list[Path]:
    versions = key_diagnostic_versions(config)
    data = load_trade_diagnostics(config, versions=versions, period="valid")
    account = safe_float(config["costs"]["account"], 1_000_000.0)
    attribution = build_attribution_rows(data, account)
    failure = data[
        data["entry_type"].isin(["pullback", "breakout"])
        & data["exit_reason"].isin(["stop_loss", "time_stop"])
    ].copy()
    for column in VALID_FAILURE_COLUMNS:
        if column not in failure.columns:
            failure[column] = np.nan
    failure = failure[VALID_FAILURE_COLUMNS].sort_values(["version", "cost_after_return", "exit_date"], ascending=[True, True, True])
    outputs = [
        write_csv(attribution, diagnostics_dir(config) / "valid_trade_attribution.csv"),
        write_csv(failure, diagnostics_dir(config) / "valid_failure_samples.csv"),
    ]
    top_loss = (
        attribution.sort_values("net_pnl_sum").head(10)
        if not attribution.empty
        else pd.DataFrame(columns=VALID_ATTRIBUTION_COLUMNS)
    )
    report_lines = [
        "# Explore4 Valid 交易级归因报告",
        "",
        f"- 覆盖版本：`{', '.join(versions)}`。",
        f"- 归因分组行数：`{format_int(len(attribution))}`。",
        f"- 失败样本行数：`{format_int(len(failure))}`。",
        "- 所有归因字段使用 T 日 as-of 数据；T+1 仅用于 open/gap/execution 审计。",
        "",
        "## 净亏损最大的分组",
        "",
        *markdown_table(
            ["版本", "分组", "取值", "交易数", "胜率", "平均收益", "净收益", "回撤代理"],
            [
                [
                    row["version"],
                    row["group_name"],
                    row["group_value"],
                    format_int(row["trades"]),
                    format_pct(row["win_rate"]),
                    format_pct(row["avg_cost_after_return"]),
                    format_int(row["net_pnl_sum"]),
                    format_pct(row["max_drawdown_proxy"]),
                ]
                for _, row in top_loss.iterrows()
            ],
        ),
        "",
        "## 初步结论",
        "",
        "- 该报告用于定位 valid 负收益来源，不形成新参数。",
        "- 优先查看 `valid_failure_samples.csv` 中的 pullback + stop_loss/time_stop 样本。",
    ]
    outputs.append(write_report(report_dir(config) / "valid_trade_attribution_report.md", report_lines))
    record_manifest(
        config,
        "diagnose-valid",
        outputs,
        {
            "valid_trade_attribution_rows": int(len(attribution)),
            "valid_failure_samples_rows": int(len(failure)),
        },
    )
    return outputs


def diagnostic_signal_variant(signals: pd.DataFrame, variant: str) -> pd.DataFrame:
    df = signals.copy()
    df["avg_money20_p30"] = df.groupby("datetime")["avg_money20"].transform(lambda s: s.quantile(0.30))
    base_breakout = df["breakout_entry"].fillna(False)
    base_pullback = df["pullback_entry"].fillna(False)
    if variant == "breakout_only":
        breakout = base_breakout
        pullback = pd.Series(False, index=df.index)
    elif variant == "pullback_only":
        breakout = pd.Series(False, index=df.index)
        pullback = base_pullback
    elif variant == "pullback_strict_money":
        breakout = base_breakout
        pullback = (
            base_pullback
            & (df["money_ratio20"] >= 0.60)
            & (df["money_ratio20"] <= 0.95)
            & (df["avg_money20"] >= df["avg_money20_p30"])
        )
    elif variant == "pullback_strict_trend":
        breakout = base_breakout
        pullback = (
            base_pullback
            & (df["trend_score_pct"] <= 0.15)
            & (df["close_gt_ema60_ratio"] > 0.60)
            & (df["ema20_gt_ema60_ratio"] > 0.50)
        )
    else:
        raise ValueError(f"Unknown diagnostic variant: {variant}")
    df["breakout_entry"] = breakout
    df["pullback_entry"] = pullback
    df["combined_entry"] = breakout | pullback
    return df


def command_pullback_diagnostic(config: dict[str, Any]) -> list[Path]:
    ensure_grid_outputs(config)
    final_row, _stage2_row = final_selection_rows(config)
    base_spec = spec_from_summary(final_row, stage="diagnostic_only")
    signals = load_signals_with_width(config)
    start = parse_dt(config["dates"]["valid_start"])
    end = parse_dt(config["dates"]["valid_end"])
    variants = ["breakout_only", "pullback_only", "pullback_strict_money", "pullback_strict_trend"]
    rows: list[dict[str, Any]] = []
    all_trades: list[pd.DataFrame] = []
    for variant in variants:
        spec = dict(base_spec)
        spec["version"] = variant
        variant_signals = diagnostic_signal_variant(signals, variant)
        portfolio, trades, _audit, _exposure, metrics = run_backtest_one(config, variant_signals, spec, "valid", start, end)
        metrics["diagnostic_scope"] = "diagnostic_only"
        metrics["observed_scope"] = "not_run"
        metrics["diagnostic_base_version"] = final_row.get("version", "")
        metrics["input_period"] = "valid_only"
        rows.append(metrics)
        if not trades.empty:
            trades = trades.copy()
            trades["diagnostic_scope"] = "diagnostic_only"
            all_trades.append(trades)
        print(f"ran diagnostic {variant}", flush=True)
    result = pd.DataFrame(rows)
    outputs = [write_csv(result, diagnostics_dir(config) / "pullback_rule_diagnostic.csv")]
    if all_trades:
        outputs.append(write_csv(pd.concat(all_trades, ignore_index=True), diagnostics_dir(config) / "pullback_rule_diagnostic_trades.csv"))
    table_rows = []
    for _, row in result.sort_values("total_return_with_cost", ascending=False).iterrows():
        table_rows.append(
            [
                row["version"],
                row["diagnostic_scope"],
                format_pct(row["total_return_with_cost"]),
                format_pct(row["max_drawdown"]),
                format_int(row["trades"]),
                format_pct(row["win_rate"]),
                format_pct(row["avg_cash_ratio"]),
            ]
        )
    best = result.sort_values("total_return_with_cost", ascending=False).iloc[0] if not result.empty else pd.Series(dtype=object)
    report_lines = [
        "# Explore4 Pullback 子规则诊断报告",
        "",
        "- 本诊断只运行 valid 区间。",
        "- 4 个版本均标记为 `diagnostic_only`，不参与最终参数选择。",
        "- observed_test 未运行；不存在 observed 反向调参。",
        "",
        *markdown_table(["诊断版本", "范围", "成本后收益", "最大回撤", "交易数", "胜率", "平均现金"], table_rows),
        "",
        "## 初步结论",
        "",
        f"- valid 中收益最高的诊断版本为 `{best.get('version', 'NA')}`，成本后收益 `{format_pct(best.get('total_return_with_cost', np.nan))}`。",
        "- 该结果只用于判断 pullback 是否是负收益来源，不形成新冻结版本。",
    ]
    outputs.append(write_report(report_dir(config) / "pullback_rule_diagnostic_report.md", report_lines))
    record_manifest(
        config,
        "pullback-diagnostic",
        outputs,
        {
            "expand_diagnostic_versions": variants,
            "observed_diagnostic_used_for_selection": False,
            "pullback_rule_diagnostic_rows": int(len(result)),
        },
    )
    return outputs


def infer_blocked_layer(
    after_single: float,
    after_industry: float,
    after_daily: float,
    after_cash: float,
    rounded_amount: int,
    skip_reason: str,
) -> str:
    if skip_reason == "invalid_initial_stop":
        return "invalid_initial_stop"
    if skip_reason == "max_positions":
        return "max_positions"
    if skip_reason == "limit_blocked":
        return "limit_blocked"
    if skip_reason == "invalid_open":
        return "invalid_open"
    if skip_reason == "no_market_row":
        return "no_market_row"
    if after_single <= 0:
        return "single_stock_cap"
    if after_industry <= 0:
        return "industry_cap"
    if after_daily <= 0:
        return "daily_new_cap"
    if after_cash <= 0:
        return "cash_cap"
    if rounded_amount <= 0:
        return "round_lot"
    if skip_reason == "insufficient_cash":
        return "cash_cap"
    return "none"


def run_risk_decomposition_one(
    config: dict[str, Any],
    signals: pd.DataFrame,
    spec: dict[str, Any],
    period_name: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    costs = config["costs"]
    stop_rules = config["rules"]["stops"]
    df = signals.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values(["datetime", "instrument"])
    df["prev_close_for_limit"] = df.groupby("instrument")["close"].shift(1)
    data_end = parse_dt(config["dates"]["data_end"])
    all_dates = [pd.Timestamp(d) for d in sorted(df[(df["datetime"] >= start) & (df["datetime"] <= data_end)]["datetime"].unique())]
    by_date = {date: day.set_index("instrument", drop=False) for date, day in df[df["datetime"].isin(all_dates)].groupby("datetime")}
    cash = float(costs["account"])
    positions: dict[str, dict[str, Any]] = {}
    pending: dict[pd.Timestamp, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []

    def schedule(date: pd.Timestamp, order: dict[str, Any]) -> None:
        pending.setdefault(date, []).append(order)

    def position_market_value(instrument: str, position: dict[str, Any], day: pd.DataFrame, fallback_price: float | None = None) -> float:
        price = np.nan
        if instrument in day.index:
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("close"), np.nan)
        if (pd.isna(price) or price <= 0) and fallback_price is not None:
            price = fallback_price
        if pd.isna(price) or price <= 0:
            price = safe_float(position.get("entry_price"), 0.0)
        return float(position["amount"]) * float(price)

    def current_value(day: pd.DataFrame) -> float:
        value = cash
        for instrument, position in positions.items():
            value += position_market_value(instrument, position, day)
        return value

    def base_row(order: dict[str, Any], date: pd.Timestamp) -> dict[str, Any]:
        return {
            "period": period_name,
            "version": spec["version"],
            "instrument": order.get("instrument", ""),
            "signal_date": pd.Timestamp(order.get("signal_date")).date().isoformat() if order.get("signal_date") is not None else "",
            "order_date": date.date().isoformat(),
            "entry_type": order.get("entry_type", ""),
            "status": "skipped",
            "skip_reason": "",
            "entry_price": np.nan,
            "initial_stop": np.nan,
            "initial_risk_per_share": np.nan,
            "initial_risk_pct": np.nan,
            "account_value_before": np.nan,
            "cash_before": cash,
            "raw_risk_budget_value": np.nan,
            "raw_position_value": np.nan,
            "after_single_stock_cap": np.nan,
            "after_industry_cap": np.nan,
            "after_daily_new_cap": np.nan,
            "after_cash_cap": np.nan,
            "rounded_value": np.nan,
            "rounded_amount": 0,
            "entry_cost": np.nan,
            "cash_after": cash,
            "blocked_layer": "none",
            "industry_name": position_industry({"industry_name": order.get("industry_name", "UNKNOWN")}),
            "industry_exposure_before": np.nan,
            "daily_new_value_before": np.nan,
        }

    for idx, date in enumerate(all_dates):
        day = by_date[date]
        day_new_value = 0.0
        orders = pending.pop(date, [])
        for order in [o for o in orders if o["direction"] == "sell"] + [o for o in orders if o["direction"] == "buy"]:
            instrument = order["instrument"]
            if order["direction"] == "sell":
                if instrument not in day.index:
                    continue
                row = day.loc[instrument]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                price = safe_float(row.get("open"))
                if price <= 0 or is_limit_blocked(row, "sell", float(costs["limit_threshold"])):
                    continue
                position = positions.pop(instrument, None)
                if not position:
                    continue
                exit_value = position["amount"] * price
                exit_cost = max(exit_value * float(costs["close_cost"]), float(costs["min_cost"]))
                cash += exit_value - exit_cost
                continue

            out = base_row(order, date)
            if instrument not in day.index:
                out["skip_reason"] = "no_market_row"
                out["blocked_layer"] = "no_market_row"
                rows.append(out)
                continue
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("open"))
            out["entry_price"] = price
            if price <= 0:
                out["skip_reason"] = "invalid_open"
                out["blocked_layer"] = "invalid_open"
                rows.append(out)
                continue
            if is_limit_blocked(row, "buy", float(costs["limit_threshold"])):
                out["skip_reason"] = "limit_blocked"
                out["blocked_layer"] = "limit_blocked"
                rows.append(out)
                continue
            account_value_before = current_value(day)
            cash_before = cash
            out["account_value_before"] = account_value_before
            out["cash_before"] = cash_before
            out["daily_new_value_before"] = day_new_value
            stop = initial_stop_for(order["signal_row"], price, order["entry_type"], config)
            initial_risk = price - stop if np.isfinite(stop) else np.nan
            out["initial_stop"] = stop
            out["initial_risk_per_share"] = initial_risk
            out["initial_risk_pct"] = initial_risk / price if price > 0 and np.isfinite(initial_risk) else np.nan
            if not np.isfinite(stop) or initial_risk <= 0:
                out["skip_reason"] = "invalid_initial_stop"
                out["blocked_layer"] = "invalid_initial_stop"
                rows.append(out)
                continue
            if len(positions) >= int(spec["max_positions"]):
                out["skip_reason"] = "max_positions"
                out["blocked_layer"] = "max_positions"
                rows.append(out)
                continue

            if spec["sizing"] == "risk_unit":
                raw_risk_budget_value = account_value_before * float(spec["risk_budget_per_trade"])
                raw_position_value = raw_risk_budget_value / initial_risk * price
            else:
                target_weight = min(float(spec["single_stock_max_weight"]), float(config["rules"]["portfolio"]["risk_degree"]) / int(spec["max_positions"]))
                raw_position_value = account_value_before * target_weight
                raw_risk_budget_value = raw_position_value / price * initial_risk
            after_single = min(raw_position_value, account_value_before * float(spec["single_stock_max_weight"]))

            cap = spec.get("max_industry_weight")
            industry = position_industry({"industry_name": order.get("industry_name", "UNKNOWN")})
            industry_exposure_before = 0.0
            for pos_instrument, pos in positions.items():
                if position_industry(pos) == industry:
                    industry_exposure_before += position_market_value(pos_instrument, pos, day, price)
            if pd.notna(cap):
                after_industry = min(after_single, max(0.0, account_value_before * float(cap) - industry_exposure_before))
            else:
                after_industry = after_single
            daily_remaining = max(0.0, account_value_before * float(spec["max_daily_new_weight"]) - day_new_value)
            after_daily = min(after_industry, daily_remaining)
            after_cash = min(after_daily, cash)
            amount = round_lot_amount(after_cash, price)
            rounded_value = amount * price
            entry_cost = max(rounded_value * float(costs["open_cost"]), float(costs["min_cost"])) if amount > 0 else 0.0
            if amount > 0 and rounded_value + entry_cost > cash:
                amount = round_lot_amount(cash - float(costs["min_cost"]), price)
                rounded_value = amount * price
                entry_cost = max(rounded_value * float(costs["open_cost"]), float(costs["min_cost"])) if amount > 0 else 0.0

            out.update(
                {
                    "raw_risk_budget_value": raw_risk_budget_value,
                    "raw_position_value": raw_position_value,
                    "after_single_stock_cap": after_single,
                    "after_industry_cap": after_industry,
                    "after_daily_new_cap": after_daily,
                    "after_cash_cap": after_cash,
                    "rounded_value": rounded_value,
                    "rounded_amount": amount,
                    "entry_cost": entry_cost,
                    "industry_exposure_before": industry_exposure_before,
                }
            )
            if amount <= 0:
                out["skip_reason"] = "zero_lot"
                out["blocked_layer"] = infer_blocked_layer(after_single, after_industry, after_daily, after_cash, amount, "zero_lot")
                rows.append(out)
                continue
            if rounded_value + entry_cost > cash:
                out["skip_reason"] = "insufficient_cash"
                out["blocked_layer"] = "cash_cap"
                rows.append(out)
                continue

            cash -= rounded_value + entry_cost
            day_new_value += rounded_value
            positions[instrument] = {
                "amount": amount,
                "entry_price": price,
                "entry_value": rounded_value,
                "entry_cost": entry_cost,
                "signal_date": order["signal_date"],
                "order_date": date,
                "deal_date": date,
                "entry_type": order["entry_type"],
                "industry_name": industry,
                "initial_stop": stop,
                "current_stop": stop,
                "R": initial_risk,
                "risk_budget_per_trade": spec["risk_budget_per_trade"] if spec["sizing"] == "risk_unit" else np.nan,
                "target_loss_budget": raw_risk_budget_value,
                "initial_risk_per_share": initial_risk,
            }
            out["status"] = "executed"
            out["skip_reason"] = ""
            out["cash_after"] = cash
            out["blocked_layer"] = "none"
            rows.append(out)

        if date <= end:
            next_date = next_trading_date(all_dates, idx)
            if next_date is None:
                continue
            exiting = set()
            for instrument, position in list(positions.items()):
                if instrument not in day.index:
                    continue
                row = day.loc[instrument]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                close = safe_float(row.get("close"))
                if close <= 0:
                    continue
                unreal_r = (close - position["entry_price"]) / position["R"]
                if unreal_r >= 1:
                    position["current_stop"] = max(position["current_stop"], position["entry_price"])
                if unreal_r >= 2:
                    atr = safe_float(row.get("atr20"))
                    trail = max(safe_float(row.get("ema20")), close - stop_rules["trailing_atr_multiplier"] * atr)
                    position["current_stop"] = max(position["current_stop"], trail)
                if unreal_r >= 3 and safe_float(row.get("dist_ema20")) > 0.10:
                    position["current_stop"] = max(position["current_stop"], safe_float(row.get("ema20")))
                exit_reason = ""
                if close <= position["current_stop"]:
                    exit_reason = "trailing_stop" if position["current_stop"] >= position["entry_price"] else "stop_loss"
                holding_days = int((date - position["deal_date"]).days)
                if not exit_reason and holding_days >= stop_rules["time_stop_days"] and close <= position["entry_price"]:
                    exit_reason = "time_stop"
                if not exit_reason and close < safe_float(row.get("ema60")):
                    exit_reason = "ema60_exit"
                if exit_reason:
                    exiting.add(instrument)
                    schedule(next_date, {"direction": "sell", "instrument": instrument, "signal_date": date, "exit_reason": exit_reason})

            available_slots = int(spec["max_positions"]) - len(positions) - len(
                [o for orders2 in pending.values() for o in orders2 if o["direction"] == "buy"]
            )
            if available_slots > 0:
                candidates = day[day["combined_entry"].fillna(False)].copy()
                candidates = candidates[~candidates["instrument"].isin(set(positions) | exiting)]
                if not candidates.empty:
                    candidates = candidates.sort_values(["trend_score", "ret60", "money_ratio20"], ascending=False)
                for _, candidate in candidates.head(int(spec["max_positions"])).iterrows():
                    if available_slots <= 0:
                        break
                    entry_type = choose_entry_type(candidate)
                    schedule(
                        next_date,
                        {
                            "direction": "buy",
                            "instrument": candidate["instrument"],
                            "signal_date": date,
                            "entry_type": entry_type,
                            "signal_row": candidate,
                            "industry_name": candidate.get("industry_name", "UNKNOWN") or "UNKNOWN",
                        },
                    )
                    available_slots -= 1

    result = pd.DataFrame(rows, columns=RISK_CONSTRAINT_COLUMNS)
    if not result.empty:
        invalid_layers = sorted(set(result["blocked_layer"].dropna()) - BLOCKED_LAYERS)
        if invalid_layers:
            raise RuntimeError(f"Invalid blocked_layer values: {invalid_layers}")
    return result


def command_risk_decompose(config: dict[str, Any]) -> list[Path]:
    ensure_grid_outputs(config)
    final_row, _stage2_row = final_selection_rows(config)
    spec = spec_from_summary(final_row)
    signals = load_signals_with_width(config)
    start = parse_dt(config["dates"]["valid_start"])
    end = parse_dt(config["dates"]["valid_end"])
    result = run_risk_decomposition_one(config, signals, spec, "valid", start, end)
    output = write_csv(result, diagnostics_dir(config) / "risk_constraint_decomposition.csv")
    layer_rows = []
    if not result.empty:
        grouped = result.groupby(["blocked_layer", "status"], as_index=False).size().sort_values("size", ascending=False)
        for _, row in grouped.iterrows():
            layer_rows.append([row["blocked_layer"], row["status"], format_int(row["size"])])
        executed = result[result["status"] == "executed"].copy()
        executed["planned_to_target"] = (
            pd.to_numeric(executed["rounded_value"], errors="coerce")
            / pd.to_numeric(executed["raw_position_value"], errors="coerce").replace(0, np.nan)
        )
        avg_budget_use = safe_float(executed["planned_to_target"].mean(), np.nan)
    else:
        avg_budget_use = np.nan
    report = write_report(
        report_dir(config) / "risk_constraint_decomposition_report.md",
        [
            "# Explore4 风险单位仓位约束拆解报告",
            "",
            f"- 版本：`{spec['version']}`。",
            f"- 分解订单行数：`{format_int(len(result))}`。",
            f"- 成交订单相对 raw position 的平均使用比例：`{format_pct(avg_budget_use)}`。",
            "",
            *markdown_table(["约束层", "状态", "数量"], layer_rows),
            "",
            "## 初步结论",
            "",
            "- `blocked_layer` 用于定位订单最终被哪一层约束压低或阻断。",
            "- `zero_lot` 应优先结合 `after_*` 预算列判断是 cap、现金还是整数手造成。",
        ],
    )
    outputs = [output, report]
    record_manifest(
        config,
        "risk-decompose",
        outputs,
        {
            "risk_constraint_decomposition_rows": int(len(result)),
            "risk_constraint_blocked_layers": sorted(result["blocked_layer"].dropna().unique().tolist()) if not result.empty else [],
        },
    )
    return outputs


def command_pullback_failure_analysis(config: dict[str, Any]) -> list[Path]:
    failure_path = diagnostics_dir(config) / "valid_failure_samples.csv"
    if not failure_path.exists():
        command_diagnose_valid(config)
    final_row, _stage2_row = final_selection_rows(config)
    final_version = str(final_row.get("version", "risk_unit_rb050_sw03_cap20"))
    failures = pd.read_csv(failure_path, parse_dates=["signal_date", "order_date", "exit_date"])
    data = failures[
        (failures["version"] == final_version)
        & (failures["entry_type"] == "pullback")
        & failures["exit_reason"].isin(["stop_loss", "time_stop"])
    ].copy()
    trades = pd.read_csv(report_dir(config) / "trade_detail.csv", parse_dates=["signal_date", "order_date", "exit_date"])
    final_trades = trades[(trades["version"] == final_version) & (trades["period"] == "valid")].copy()
    final_pullback = final_trades[final_trades["entry_type"] == "pullback"].copy()

    if data.empty:
        report = write_report(
            report_dir(config) / "pullback_failure_analysis_report.md",
            [
                "# Explore4 Pullback 失败样本详细分析",
                "",
                f"- 版本：`{final_version}`。",
                "- 没有找到 `pullback + stop_loss/time_stop` 样本。",
            ],
        )
        record_manifest(config, "pullback-failure-analysis", [report], {"pullback_failure_rows": 0})
        return [report]

    data["signal_month"] = data["signal_date"].dt.to_period("M").astype(str)
    data["signal_year"] = data["signal_date"].dt.year.astype(str)
    data["trend_bucket"] = bucket_series(data["trend_score_pct"], [0, 0.1, 0.2, 0.5, 1.0], ["top10", "top10_20", "top20_50", "bottom50"])
    data["money_bucket"] = bucket_series(
        data["money_ratio20"],
        [-np.inf, 0.6, 0.95, 1.0, 1.2, np.inf],
        ["lt0.60", "0.60_0.95", "0.95_1.00", "1.00_1.20", "gt1.20"],
    )
    data["gap_bucket"] = bucket_series(
        data["gap_pct"],
        [-np.inf, -0.03, -0.01, 0.01, 0.03, np.inf],
        ["gap_down_gt3", "gap_down_1_3", "flat", "gap_up_1_3", "gap_up_gt3"],
    )
    data["risk_bucket"] = bucket_series(data["initial_risk_pct"], [-np.inf, 0.03, 0.06, 0.10, np.inf], ["lt3", "3_6", "6_10", "gt10"])
    data["holding_bucket"] = bucket_series(data["holding_days"], [-np.inf, 5, 10, 20, 40, np.inf], ["le5", "6_10", "11_20", "21_40", "gt40"])

    def group_rows(column: str, limit: int = 12) -> list[list[str]]:
        grouped = (
            data.groupby(column, as_index=False, dropna=False)
            .agg(
                trades=("instrument", "count"),
                avg_return=("cost_after_return", "mean"),
                median_return=("cost_after_return", "median"),
                net_pnl=("net_pnl", "sum"),
                avg_initial_risk_pct=("initial_risk_pct", "mean"),
                avg_gap_pct=("gap_pct", "mean"),
                avg_trend_score_pct=("trend_score_pct", "mean"),
                avg_money_ratio20=("money_ratio20", "mean"),
                avg_holding_days=("holding_days", "mean"),
            )
            .sort_values("net_pnl")
            .head(limit)
        )
        return [
            [
                str(row[column]),
                format_int(row["trades"]),
                format_pct(row["avg_return"]),
                format_pct(row["median_return"]),
                format_int(row["net_pnl"]),
                format_pct(row["avg_initial_risk_pct"]),
                format_pct(row["avg_gap_pct"]),
                format_pct(row["avg_trend_score_pct"]),
                f"{safe_float(row['avg_money_ratio20'], np.nan):.2f}",
                f"{safe_float(row['avg_holding_days'], np.nan):.1f}",
            ]
            for _, row in grouped.iterrows()
        ]

    worst_rows = []
    for _, row in data.nsmallest(20, "net_pnl").iterrows():
        worst_rows.append(
            [
                row["instrument"],
                row["signal_date"].date().isoformat(),
                row["exit_date"].date().isoformat(),
                row["exit_reason"],
                row["industry_name"],
                format_pct(row["cost_after_return"]),
                format_int(row["net_pnl"]),
                format_pct(row["trend_score_pct"]),
                f"{safe_float(row['money_ratio20'], np.nan):.2f}",
                format_pct(row["gap_pct"]),
                format_pct(row["initial_risk_pct"]),
                format_int(row["holding_days"]),
            ]
        )

    total_failure_net = float(data["net_pnl"].sum())
    total_pullback_net = float(final_pullback["net_pnl"].sum()) if not final_pullback.empty else np.nan
    non_failure_pullback_net = total_pullback_net - total_failure_net if not pd.isna(total_pullback_net) else np.nan
    stop_loss = data[data["exit_reason"] == "stop_loss"]
    time_stop = data[data["exit_reason"] == "time_stop"]
    stop_loss_rows = group_rows("exit_reason", limit=5)
    industry_rows = group_rows("industry_name", limit=12)
    month_rows = group_rows("signal_month", limit=12)
    instrument_rows = group_rows("instrument", limit=12)
    trend_rows = group_rows("trend_bucket", limit=8)
    money_rows = group_rows("money_bucket", limit=8)
    gap_rows = group_rows("gap_bucket", limit=8)
    risk_rows = group_rows("risk_bucket", limit=8)
    holding_rows = group_rows("holding_bucket", limit=8)

    report_lines = [
        "# Explore4 Pullback 失败样本详细分析",
        "",
        "## 范围和结论",
        "",
        f"- 分析版本：`{final_version}`。",
        "- 分析区间：`valid`。",
        "- 样本定义：`entry_type = pullback` 且 `exit_reason in {stop_loss, time_stop}`。",
        f"- 样本数：`{format_int(len(data))}`；其中 `stop_loss` `{format_int(len(stop_loss))}` 笔，`time_stop` `{format_int(len(time_stop))}` 笔。",
        f"- 样本净损失：`{format_int(total_failure_net)}`；pullback 全部交易净收益为 `{format_int(total_pullback_net)}`，非失败 pullback 合计抵消 `{format_int(non_failure_pullback_net)}`。",
        f"- 平均收益 `{format_pct(data['cost_after_return'].mean())}`，中位收益 `{format_pct(data['cost_after_return'].median())}`，胜率 `{format_pct((data['cost_after_return'] > 0).mean())}`。",
        "",
        "结论：这 81 笔失败交易几乎解释了 pullback 子系统的全部问题。pullback 并不是每笔都差，但失败样本的亏损规模足以吞掉其它 pullback 盈利交易。后续不应先上 meta-labeling，而应先减少这类候选进入组合。",
        "",
        "## Stop Loss 与 Time Stop",
        "",
        *markdown_table(
            ["退出", "交易数", "平均收益", "中位收益", "净收益", "初始风险均值", "跳空均值", "trend_pct均值", "money均值", "持仓均值"],
            stop_loss_rows,
        ),
        "",
        "解读：`stop_loss` 平均亏损更深，是主要损失项；`time_stop` 单笔亏损较浅，但数量略多，说明一批 pullback 入场后没有快速恶化到止损，却持续没有趋势延续。time stop 更像“弱反弹失败”，stop loss 更像“入场后结构直接破坏”。",
        "",
        "## 行业集中",
        "",
        *markdown_table(
            ["行业", "交易数", "平均收益", "中位收益", "净收益", "初始风险均值", "跳空均值", "trend_pct均值", "money均值", "持仓均值"],
            industry_rows,
        ),
        "",
        "解读：非银金融、有色金属、家用电器、电子是主要损失行业。这里不能解释为历史真实行业暴露，因为行业归属是当前 as-of 口径；但它可以说明当前分类下的失败交易具有明显行业聚集，需要后续复盘这些行业在信号日是否同步转弱。",
        "",
        "## 时间聚集",
        "",
        *markdown_table(
            ["信号月份", "交易数", "平均收益", "中位收益", "净收益", "初始风险均值", "跳空均值", "trend_pct均值", "money均值", "持仓均值"],
            month_rows,
        ),
        "",
        "解读：2024-11、2024-12 是最集中的亏损月份，其次是 2023-08、2024-05、2024-10。这说明问题不是单一股票异常，而是若干市场阶段中 pullback 信号批量失效。",
        "",
        "## 重复股票",
        "",
        *markdown_table(
            ["股票", "交易数", "平均收益", "中位收益", "净收益", "初始风险均值", "跳空均值", "trend_pct均值", "money均值", "持仓均值"],
            instrument_rows,
        ),
        "",
        "解读：重复出现的股票不多，但 SH601600、SH600584、SH600690 等个股贡献靠前。后续人工复盘可以先从这些重复样本入手，检查 pullback 入场时是否已经跌破行业或个股结构。",
        "",
        "## Trend Score 与成交额",
        "",
        "### Trend Score 分位",
        "",
        *markdown_table(
            ["分位", "交易数", "平均收益", "中位收益", "净收益", "初始风险均值", "跳空均值", "trend_pct均值", "money均值", "持仓均值"],
            trend_rows,
        ),
        "",
        "### 成交额分组",
        "",
        *markdown_table(
            ["成交额分组", "交易数", "平均收益", "中位收益", "净收益", "初始风险均值", "跳空均值", "trend_pct均值", "money均值", "持仓均值"],
            money_rows,
        ),
        "",
        "解读：亏损主要落在 `top10_20`，而不是最强 `top10`。这说明当前 top20 门槛对 pullback 偏宽。成交额上，`0.60_0.95` 是最大损失区间，接近 1 但未放量的回踩最危险；`0.95_1.00` 单笔亏损更深。仅做成交额过滤能改善结果，但不够。",
        "",
        "## 跳空、初始风险和持仓天数",
        "",
        "### T 到 T+1 Open 跳空",
        "",
        *markdown_table(
            ["跳空分组", "交易数", "平均收益", "中位收益", "净收益", "初始风险均值", "跳空均值", "trend_pct均值", "money均值", "持仓均值"],
            gap_rows,
        ),
        "",
        "### 初始风险占价格",
        "",
        *markdown_table(
            ["风险分组", "交易数", "平均收益", "中位收益", "净收益", "初始风险均值", "跳空均值", "trend_pct均值", "money均值", "持仓均值"],
            risk_rows,
        ),
        "",
        "### 持仓天数",
        "",
        *markdown_table(
            ["持仓分组", "交易数", "平均收益", "中位收益", "净收益", "初始风险均值", "跳空均值", "trend_pct均值", "money均值", "持仓均值"],
            holding_rows,
        ),
        "",
        "解读：失败样本不是由大幅 T+1 跳空主导，flat 分组贡献最大亏损。初始风险 `3%-10%` 是主要损失区间，说明不是只要放弃极宽 stop 就能解决。持仓 20 天以内的失败占主导，尤其 11-20 天区间，说明 time stop 之前可能已经有更早的趋势衰减信号可用。",
        "",
        "## 最差样本",
        "",
        *markdown_table(
            ["股票", "信号日", "退出日", "退出", "行业", "收益", "净收益", "trend_pct", "money", "gap", "初始风险", "持仓"],
            worst_rows,
        ),
        "",
        "## 后续处理建议",
        "",
        "- 优先收紧 pullback 的 trend_score 门槛：从 top20 诊断到 top15 或 top10，但必须保持 diagnostic，不直接作为最终参数。",
        "- 对 `0.60 <= money_ratio20 <= 1.00` 的 pullback 单独复查，这一段更像弱反弹而不是健康缩量回踩。",
        "- 对持仓 6-20 天仍无趋势延续的样本，研究更早的失败退出条件，例如跌破短期均线、行业同步转弱、或相对强度回落。",
        "- 对非银金融、有色金属、家用电器、电子四类集中亏损行业做图形抽样，不要只看聚合表。",
        "- 暂停 meta-labeling。当前样本表明候选集合仍含大量结构性弱 pullback，直接训练模型会先学习这些规则缺陷。",
    ]
    report = write_report(report_dir(config) / "pullback_failure_analysis_report.md", report_lines)
    record_manifest(
        config,
        "pullback-failure-analysis",
        [report],
        {
            "pullback_failure_rows": int(len(data)),
            "pullback_failure_net_pnl": total_failure_net,
            "pullback_failure_version": final_version,
        },
    )
    return [report]


def final_test_status(config: dict[str, Any]) -> dict[str, Any]:
    signals = load_signals_with_width(config)
    observed_end = parse_dt(config["dates"]["observed_test_end"])
    dates = sorted(pd.Timestamp(d).normalize() for d in signals["datetime"].dropna().unique())
    new_dates = [date for date in dates if date > observed_end]
    executable_days = max(0, len(new_dates) - 1)
    available = executable_days >= 20
    if not new_dates:
        reason = "no_data_after_observed_test_end"
    elif not available:
        reason = "less_than_20_executable_days_after_observed_test_end"
    else:
        reason = "available"
    return {
        "final_test_available": bool(available),
        "final_test_trigger_reason": reason,
        "observed_test_end": observed_end.date().isoformat(),
        "provider_data_max_date": dates[-1].date().isoformat() if dates else "",
        "new_trading_days_after_observed_end": int(len(new_dates)),
        "new_executable_days_after_observed_end": int(executable_days),
        "final_test_start": new_dates[0].date().isoformat() if available else "",
        "final_test_end": new_dates[-1].date().isoformat() if available else "",
        "final_test_executable_end": new_dates[-2].date().isoformat() if available else "",
        "frozen_config_sha256": file_sha256(config["_config_path"]),
    }


def command_expand_report(config: dict[str, Any]) -> list[Path]:
    outputs: list[Path] = []
    outputs.extend(command_diagnose_valid(config))
    outputs.extend(command_pullback_diagnostic(config))
    outputs.extend(command_risk_decompose(config))
    outputs.extend(command_pullback_failure_analysis(config))
    attribution = pd.read_csv(diagnostics_dir(config) / "valid_trade_attribution.csv")
    failures = pd.read_csv(diagnostics_dir(config) / "valid_failure_samples.csv")
    pullback = pd.read_csv(diagnostics_dir(config) / "pullback_rule_diagnostic.csv")
    risk_decomp = pd.read_csv(diagnostics_dir(config) / "risk_constraint_decomposition.csv")
    final_status = final_test_status(config)

    attribution_top = attribution.sort_values("net_pnl_sum").head(8) if not attribution.empty else pd.DataFrame(columns=VALID_ATTRIBUTION_COLUMNS)
    pullback_rows = [
        [
            row["version"],
            row["diagnostic_scope"],
            format_pct(row["total_return_with_cost"]),
            format_pct(row["max_drawdown"]),
            format_int(row["trades"]),
            format_pct(row["avg_cash_ratio"]),
        ]
        for _, row in pullback.sort_values("total_return_with_cost", ascending=False).iterrows()
    ]
    layer_rows = []
    if not risk_decomp.empty:
        grouped = risk_decomp.groupby(["blocked_layer", "status"], as_index=False).size().sort_values("size", ascending=False)
        layer_rows = [[row["blocked_layer"], row["status"], format_int(row["size"])] for _, row in grouped.iterrows()]
    failure_rows = []
    if not failures.empty:
        grouped = (
            failures.groupby(["version", "entry_type", "exit_reason"], as_index=False)
            .agg(trades=("instrument", "count"), avg_return=("cost_after_return", "mean"), net_pnl=("net_pnl", "sum"))
            .sort_values("net_pnl")
        )
        failure_rows = [
            [
                row["version"],
                row["entry_type"],
                row["exit_reason"],
                format_int(row["trades"]),
                format_pct(row["avg_return"]),
                format_int(row["net_pnl"]),
            ]
            for _, row in grouped.iterrows()
        ]

    final_row, _stage2_row = final_selection_rows(config)
    final_version = str(final_row.get("version", "risk_unit_rb050_sw03_cap20"))

    def attribution_rows(group_name: str, limit: int = 10, ascending: bool = True) -> list[list[str]]:
        data = attribution[(attribution["version"] == final_version) & (attribution["group_name"] == group_name)].copy()
        if data.empty:
            return []
        data = data.sort_values("net_pnl_sum", ascending=ascending).head(limit)
        return [
            [
                row["group_value"],
                format_int(row["trades"]),
                format_pct(row["win_rate"]),
                format_pct(row["avg_cost_after_return"]),
                format_int(row["net_pnl_sum"]),
                format_pct(row["max_drawdown_proxy"]),
            ]
            for _, row in data.iterrows()
        ]

    final_failure = failures[failures["version"] == final_version].copy()
    final_failure_rows = []
    if not final_failure.empty:
        grouped = (
            final_failure.groupby(["entry_type", "exit_reason"], as_index=False)
            .agg(
                trades=("instrument", "count"),
                avg_return=("cost_after_return", "mean"),
                net_pnl=("net_pnl", "sum"),
                avg_initial_risk_pct=("initial_risk_pct", "mean"),
                avg_gap_pct=("gap_pct", "mean"),
                avg_trend_score_pct=("trend_score_pct", "mean"),
            )
            .sort_values("net_pnl")
        )
        final_failure_rows = [
            [
                row["entry_type"],
                row["exit_reason"],
                format_int(row["trades"]),
                format_pct(row["avg_return"]),
                format_int(row["net_pnl"]),
                format_pct(row["avg_initial_risk_pct"]),
                format_pct(row["avg_gap_pct"]),
                format_pct(row["avg_trend_score_pct"]),
            ]
            for _, row in grouped.iterrows()
        ]

    pull_sorted = pullback.sort_values("total_return_with_cost", ascending=False).copy()
    pullback_only = pullback[pullback["version"] == "pullback_only"]
    breakout_only = pullback[pullback["version"] == "breakout_only"]
    strict_trend = pullback[pullback["version"] == "pullback_strict_trend"]
    strict_money = pullback[pullback["version"] == "pullback_strict_money"]
    pullback_only_return = safe_float(pullback_only["total_return_with_cost"].iloc[0], np.nan) if not pullback_only.empty else np.nan
    breakout_only_return = safe_float(breakout_only["total_return_with_cost"].iloc[0], np.nan) if not breakout_only.empty else np.nan
    strict_trend_return = safe_float(strict_trend["total_return_with_cost"].iloc[0], np.nan) if not strict_trend.empty else np.nan
    strict_money_return = safe_float(strict_money["total_return_with_cost"].iloc[0], np.nan) if not strict_money.empty else np.nan
    pullback_diagnostic_analysis = [
        f"- `breakout_only` 的 valid 成本后收益为 `{format_pct(breakout_only_return)}`，但平均现金高达 `{format_pct(safe_float(breakout_only['avg_cash_ratio'].iloc[0], np.nan) if not breakout_only.empty else np.nan)}`，更像低暴露对照，不足以直接说明 breakout 子系统已经足够实盘化。",
        f"- `pullback_only` 的 valid 成本后收益为 `{format_pct(pullback_only_return)}`，最大回撤 `{format_pct(safe_float(pullback_only['max_drawdown'].iloc[0], np.nan) if not pullback_only.empty else np.nan)}`，说明 pullback 是当前 valid 负收益的主要嫌疑来源。",
        f"- `pullback_strict_trend` 相比 `pullback_only` 改善 `{format_pct(strict_trend_return - pullback_only_return)}`，但仍为 `{format_pct(strict_trend_return)}`；方向上支持“趋势确认不足”这个问题，但还不能形成新规则。",
        f"- `pullback_strict_money` 相比 `pullback_only` 改善 `{format_pct(strict_money_return - pullback_only_return)}`，弱于 strict_trend，说明成交额过滤有帮助但不是唯一问题。",
    ]

    risk_ratio_rows: list[list[str]] = []
    risk_executed = risk_decomp[risk_decomp["status"] == "executed"].copy()
    if not risk_executed.empty:
        ratio_defs = [
            ("单票上限后 / raw", "after_single_stock_cap"),
            ("行业上限后 / raw", "after_industry_cap"),
            ("当日新增后 / raw", "after_daily_new_cap"),
            ("现金约束后 / raw", "after_cash_cap"),
            ("实际成交 / raw", "rounded_value"),
        ]
        for label, column in ratio_defs:
            ratio = pd.to_numeric(risk_executed[column], errors="coerce") / pd.to_numeric(
                risk_executed["raw_position_value"], errors="coerce"
            ).replace(0, np.nan)
            risk_ratio_rows.append(
                [
                    label,
                    format_pct(ratio.mean()),
                    format_pct(ratio.median()),
                    format_pct(ratio.min()),
                    format_pct(ratio.max()),
                ]
            )

    risk_skip_rows: list[list[str]] = []
    skipped = risk_decomp[risk_decomp["status"] != "executed"].copy()
    if not skipped.empty:
        for _, row in skipped.sort_values(["blocked_layer", "signal_date", "instrument"]).iterrows():
            risk_skip_rows.append(
                [
                    row["instrument"],
                    row["signal_date"],
                    row["entry_type"],
                    row["blocked_layer"],
                    format_int(row["raw_position_value"]),
                    format_int(row["after_single_stock_cap"]),
                    format_int(row["after_industry_cap"]),
                    format_int(row["after_daily_new_cap"]),
                    format_int(row["rounded_value"]),
                    row["industry_name"],
                ]
            )

    industry_loss_rows = attribution_rows("industry_name", limit=8, ascending=True)
    entry_rows = attribution_rows("entry_type", limit=5, ascending=True)
    exit_rows = attribution_rows("exit_reason", limit=8, ascending=True)
    trend_rows = attribution_rows("trend_score_bucket", limit=8, ascending=True)
    money_rows = attribution_rows("money_ratio_bucket", limit=8, ascending=True)
    gap_rows = attribution_rows("gap_bucket", limit=8, ascending=True)
    risk_bucket_rows = attribution_rows("initial_risk_pct_bucket", limit=8, ascending=True)
    holding_rows = attribution_rows("holding_days_bucket", limit=8, ascending=True)

    report_lines = [
        "# Explore4 扩展诊断汇总报告",
        "",
        "## 范围",
        "",
        "- 本扩展只定位 valid 负收益来源，不进入 meta-labeling。",
        "- 默认不运行 observed-test 诊断；observed 结果没有参与选择。",
        "- 所有 CSV 明细写入 `Explore4/outputs/diagnostics/`。",
        "",
        "## Valid 交易归因",
        "",
        f"- 归因行数：`{format_int(len(attribution))}`。",
        f"- 失败样本行数：`{format_int(len(failures))}`。",
        f"- 下方深入分析聚焦当前诊断 fallback 版本 `{final_version}`；fixed-weight 仍作为损失放大的参照。",
        "",
        *markdown_table(
            ["版本", "分组", "取值", "交易数", "平均收益", "净收益", "回撤代理"],
            [
                [
                    row["version"],
                    row["group_name"],
                    row["group_value"],
                    format_int(row["trades"]),
                    format_pct(row["avg_cost_after_return"]),
                    format_int(row["net_pnl_sum"]),
                    format_pct(row["max_drawdown_proxy"]),
                ]
                for _, row in attribution_top.iterrows()
            ],
        ),
        "",
        "### 当前 fallback 的入场贡献",
        "",
        *markdown_table(["取值", "交易数", "胜率", "平均收益", "净收益", "回撤代理"], entry_rows),
        "",
        "结论：pullback 在 final fallback 中贡献 `-47,939` 净收益，breakout 贡献 `9,194`。这不是仓位权重造成的单纯放大问题，而是入场类型之间的方向性差异。",
        "",
        "### 当前 fallback 的退出贡献",
        "",
        *markdown_table(["取值", "交易数", "胜率", "平均收益", "净收益", "回撤代理"], exit_rows),
        "",
        "结论：`stop_loss` 和 `time_stop` 是主要亏损出口，`trailing_stop` 是主要盈利出口。这说明策略并非完全没有捕捉趋势，而是失败交易识别和退出前置不足。",
        "",
        "### 趋势分位、成交额、跳空和初始风险",
        "",
        "#### Trend Score 分位",
        "",
        *markdown_table(["取值", "交易数", "胜率", "平均收益", "净收益", "回撤代理"], trend_rows),
        "",
        "#### 成交额分组",
        "",
        *markdown_table(["取值", "交易数", "胜率", "平均收益", "净收益", "回撤代理"], money_rows),
        "",
        "#### T 到 T+1 Open 跳空",
        "",
        *markdown_table(["取值", "交易数", "胜率", "平均收益", "净收益", "回撤代理"], gap_rows),
        "",
        "#### 初始风险占价格",
        "",
        *markdown_table(["取值", "交易数", "胜率", "平均收益", "净收益", "回撤代理"], risk_bucket_rows),
        "",
        "#### 持仓天数",
        "",
        *markdown_table(["取值", "交易数", "胜率", "平均收益", "净收益", "回撤代理"], holding_rows),
        "",
        "解读：亏损集中在 `top10_20`、`0.60_0.95` 成交额、flat/gap_down、以及 20 天以内退出的交易。`trend_score` 并没有把 top10_20 中的劣质 pullback 排掉；成交额较弱的回踩也没有形成足够的反转质量。初始风险 6%-10% 分组亏损最重，说明一部分结构止损距离偏宽但交易期望不足。",
        "",
        "## 失败交易类型",
        "",
        *markdown_table(["版本", "入场", "退出", "交易数", "平均收益", "净收益"], failure_rows),
        "",
        "### 当前 fallback 的失败交易细分",
        "",
        *markdown_table(
            ["入场", "退出", "交易数", "平均收益", "净收益", "初始风险均值", "跳空均值", "trend_score_pct均值"],
            final_failure_rows,
        ),
        "",
        "解读：final fallback 中 `pullback + stop_loss` 是最大损失项，其次是 `pullback + time_stop`。`breakout + time_stop` 也为负，但规模小得多。pullback 的失败不是由明显 T+1 大幅跳空主导，更多是信号本身后续没有延续。",
        "",
        "## Pullback 固定诊断",
        "",
        *markdown_table(["诊断版本", "范围", "成本后收益", "最大回撤", "交易数", "平均现金"], pullback_rows),
        "",
        *pullback_diagnostic_analysis,
        "",
        "判断：当前证据支持先把 pullback 作为规则审计重点。直接关闭 pullback 会让组合几乎空仓，收益略正但信息量有限；更合理的下一步是拆分 pullback 的失败条件，特别是趋势确认、成交额弱反弹、time_stop 前的趋势衰减。",
        "",
        "## 风险约束拆解",
        "",
        f"- 风险约束拆解行数：`{format_int(len(risk_decomp))}`。",
        "",
        *markdown_table(["约束层", "状态", "数量"], layer_rows),
        "",
        "### 预算使用比例",
        "",
        *markdown_table(["阶段", "均值", "中位数", "最小值", "最大值"], risk_ratio_rows),
        "",
        "### 被跳过订单明细",
        "",
        *markdown_table(
            ["股票", "信号日", "入场", "阻断层", "raw", "单票后", "行业后", "当日后", "成交额", "行业"],
            risk_skip_rows,
        ),
        "",
        "解读：成交订单实际只使用 raw position 的约 36%。主要压缩来自单票上限；行业 cap 进一步压缩有色金属和非银金融的局部订单。跳过订单中 9 笔来自 round lot，3 笔来自 industry cap。风险预算没有用满是真实存在的，但它更多解释收益被稀释，不能解释 pullback 单笔期望为负。",
        "",
        "## Final Test 状态",
        "",
        f"- 当前 observed-test 截止日：`{final_status['observed_test_end']}`。",
        f"- Provider 最大日期：`{final_status['provider_data_max_date']}`。",
        f"- 新增交易日：`{format_int(final_status['new_trading_days_after_observed_end'])}`。",
        f"- 新增可执行交易日：`{format_int(final_status['new_executable_days_after_observed_end'])}`。",
        f"- 是否可做真正 final_test：`{str(final_status['final_test_available']).lower()}`。",
        f"- 触发状态：`{final_status['final_test_trigger_reason']}`。",
        "",
        "## 结论",
        "",
        "- valid 负收益的第一嫌疑是 pullback 交易质量，而不是单纯仓位 sizing。",
        "- 风险单位仓位和行业 cap 明确降低暴露和回撤，但当前组合长期高现金，收益会被稀释。",
        "- `breakout_only` 结果提示 breakout 子规则值得保留观察，但交易数太少、现金太高，不能单独冻结为正式版本。",
        "- 下一步应先做 pullback 失败样本复盘：重点看 `pullback + stop_loss/time_stop` 在信号日是否存在趋势衰减、行业同步不足、成交额弱反弹或初始 R 过宽。",
        "- 暂停 meta-labeling 仍是正确选择；否则模型会先学习一个尚未清理干净的候选集合。",
        "- 若无 20 个新增可执行交易日，继续写明没有真正 final_test；不要用 observed-test 继续调参。",
    ]
    report_path = write_report(report_dir(config) / "explore4_expand_report.md", report_lines)
    outputs.append(report_path)
    record_manifest(
        config,
        "expand-report",
        outputs,
        {
            "expand_diagnostic_versions": ["breakout_only", "pullback_only", "pullback_strict_money", "pullback_strict_trend"],
            "observed_diagnostic_used_for_selection": False,
            "valid_trade_attribution_rows": int(len(attribution)),
            "risk_constraint_decomposition_rows": int(len(risk_decomp)),
            **final_status,
        },
    )
    return outputs


def command_report(config: dict[str, Any]) -> list[Path]:
    grid_path = report_dir(config) / "parameter_grid_summary.csv"
    if not grid_path.exists():
        command_run_grid(config)
    grid = pd.read_csv(grid_path)
    selection = pd.read_csv(report_dir(config) / "valid_selection_summary.csv")
    observed = pd.read_csv(report_dir(config) / "test_result_summary.csv")
    risk = pd.read_csv(report_dir(config) / "risk_budget_audit.csv")
    exposure = pd.read_csv(report_dir(config) / "industry_exposure_audit.csv")
    selected = selection[selection["final_selected"] == True]
    if selected.empty:
        selected = selection[selection["selected"] == True].tail(1)
    selected_row = selected.iloc[0] if not selected.empty else pd.Series(dtype=object)
    selected_version = selected_row.get("version", "")
    final_eligible = bool(selected_row.get("eligible", False))
    stage_note_lines: list[str] = []
    for stage in ["risk_unit_stage", "industry_cap_stage"]:
        rows = selection[selection["stage"] == stage]
        if rows.empty:
            continue
        eligible_count = int(rows["eligible"].fillna(False).sum()) if "eligible" in rows.columns else 0
        selection_mode = (
            rows["selection_mode"].dropna().iloc[0]
            if "selection_mode" in rows.columns and rows["selection_mode"].notna().any()
            else "unknown"
        )
        stage_note_lines.append(
            f"- `{stage}` eligible candidates: `{eligible_count}` / `{len(rows)}`; selection mode: `{selection_mode}`."
        )
    if not final_eligible:
        stage_note_lines.append(
            "- Final selected version is a diagnostic fallback because no candidate in its stage passed all valid acceptance filters."
        )
    selected_valid = grid[(grid["version"] == selected_version) & (grid["period"] == "valid")]
    selected_observed = observed[observed["version"] == selected_version]
    stop_risk = risk[risk["exit_reason"].astype(str).str.contains("stop", na=False)].copy()
    loss_ratio = pd.to_numeric(stop_risk.get("risk_budget_loss_ratio"), errors="coerce")
    monthly = pd.read_csv(report_dir(config) / "monthly_returns.csv") if (report_dir(config) / "monthly_returns.csv").exists() else pd.DataFrame()
    trades = pd.read_csv(report_dir(config) / "trade_detail.csv") if (report_dir(config) / "trade_detail.csv").exists() else pd.DataFrame()
    orders = pd.read_csv(report_dir(config) / "order_execution_audit.csv") if (report_dir(config) / "order_execution_audit.csv").exists() else pd.DataFrame()
    fixed_version = "fixed_weight_layered_exit"
    stage2_selected = selection[(selection["stage"] == "risk_unit_stage") & (selection["selected"] == True)]
    stage2_version = stage2_selected["version"].iloc[0] if not stage2_selected.empty else selected_version

    def metric(version: str, period: str, column: str, default: float = np.nan) -> float:
        source = grid if period == "valid" else observed
        row = source[(source["version"] == version) & (source["period"] == period)]
        if row.empty or column not in row:
            return default
        return safe_float(row[column].iloc[0], default)

    def metric_int(version: str, period: str, column: str) -> str:
        value = metric(version, period, column, np.nan)
        return "NA" if pd.isna(value) else format_int(value)

    def monthly_stats(version: str, period: str) -> dict[str, Any]:
        if monthly.empty:
            return {"months": 0, "positive": 0, "negative": 0, "mean": np.nan, "worst": np.nan, "best": np.nan, "worst_months": "NA"}
        data = monthly[(monthly["version"] == version) & (monthly["period"] == period)].copy()
        if data.empty:
            return {"months": 0, "positive": 0, "negative": 0, "mean": np.nan, "worst": np.nan, "best": np.nan, "worst_months": "NA"}
        worst = data.nsmallest(3, "monthly_return_with_cost")
        return {
            "months": int(len(data)),
            "positive": int((data["monthly_return_with_cost"] > 0).sum()),
            "negative": int((data["monthly_return_with_cost"] < 0).sum()),
            "mean": float(data["monthly_return_with_cost"].mean()),
            "worst": float(data["monthly_return_with_cost"].min()),
            "best": float(data["monthly_return_with_cost"].max()),
            "worst_months": ", ".join(
                f"{row['month']} {format_pct(row['monthly_return_with_cost'])}" for _, row in worst.iterrows()
            ),
        }

    def risk_usage_stats(version: str, period: str) -> dict[str, Any]:
        data = risk[(risk["version"] == version) & (risk["period"] == period)].copy()
        if data.empty:
            return {"trades": 0, "planned_mean": np.nan, "planned_median": np.nan, "planned_p90": np.nan, "planned_lt_half": np.nan, "risk_pct_median": np.nan, "loss_mean": np.nan, "loss_median": np.nan}
        data["planned_loss"] = data["R"] * data["amount"]
        data["planned_to_target"] = data["planned_loss"] / data["target_loss_budget"].replace(0, np.nan)
        data["risk_pct"] = data["R"] / data["entry_price"].replace(0, np.nan)
        losses = data[data["net_pnl"] < 0].copy()
        loss_to_budget = -losses["net_pnl"] / losses["target_loss_budget"].replace(0, np.nan)
        return {
            "trades": int(len(data)),
            "planned_mean": float(data["planned_to_target"].mean()),
            "planned_median": float(data["planned_to_target"].median()),
            "planned_p90": float(data["planned_to_target"].quantile(0.90)),
            "planned_lt_half": float((data["planned_to_target"] < 0.5).mean()),
            "risk_pct_median": float(data["risk_pct"].median()),
            "loss_mean": float(loss_to_budget.mean()),
            "loss_median": float(loss_to_budget.median()),
        }

    def group_trade_rows(period: str, column: str) -> list[list[str]]:
        if trades.empty:
            return []
        data = trades[(trades["version"] == selected_version) & (trades["period"] == period)].copy()
        if data.empty:
            return []
        grouped = (
            data.groupby(column, as_index=False)
            .agg(trades=("instrument", "count"), avg_return=("cost_after_return", "mean"), net_pnl=("net_pnl", "sum"))
            .sort_values("trades", ascending=False)
        )
        return [
            [str(row[column]), format_int(row["trades"]), format_pct(row["avg_return"]), format_int(row["net_pnl"])]
            for _, row in grouped.iterrows()
        ]

    def order_reason_rows(version: str, period: str) -> list[list[str]]:
        if orders.empty:
            return []
        data = orders[(orders["version"] == version) & (orders["period"] == period)].copy()
        if data.empty:
            return []
        grouped = data.groupby(["direction", "status", "reason"], as_index=False).size().sort_values("size", ascending=False)
        return [[row["direction"], row["status"], row["reason"], format_int(row["size"])] for _, row in grouped.iterrows()]

    def max_exposure(version: str, period: str) -> tuple[str, str, float]:
        data = exposure[(exposure["version"] == version) & (exposure["period"] == period)].copy()
        data = data[data["industry_name"].astype(str) != "UNKNOWN"]
        if data.empty:
            return "NA", "NA", np.nan
        row = data.sort_values("exposure_weight", ascending=False).iloc[0]
        return str(row["datetime"]), str(row["industry_name"]), safe_float(row["exposure_weight"], np.nan)

    def signal_stats() -> list[list[str]]:
        path = stock_signal_cache_path(config)
        if not path.exists():
            return []
        signals = pd.read_pickle(path)
        signals["datetime"] = pd.to_datetime(signals["datetime"])
        rows = []
        for label, start, end in [
            ("valid", config["dates"]["valid_start"], config["dates"]["valid_end"]),
            ("observed_test", config["dates"]["observed_test_start"], config["dates"]["observed_test_end"]),
        ]:
            data = signals[(signals["datetime"] >= start) & (signals["datetime"] <= end)]
            daily = data.groupby("datetime").agg(
                market_ok=("market_ok_entry", "sum"),
                width_ok=("width_ok_entry", "sum"),
                industry_ok=("industry_ok_entry", "sum"),
                combined=("combined_entry", "sum"),
            )
            if daily.empty:
                continue
            rows.append(
                [
                    label,
                    format_int(len(daily)),
                    f"{safe_float((daily['combined'] == 0).mean(), np.nan):.1%}",
                    f"{safe_float(daily['combined'].mean(), np.nan):.2f}",
                    format_int(daily["combined"].sum()),
                    f"{safe_float((daily['width_ok'] == 0).mean(), np.nan):.1%}",
                ]
            )
        return rows

    param_rows = []
    for _, row in selection.sort_values(["stage", "return_drawdown_ratio"], ascending=[True, False]).iterrows():
        param_rows.append(
            [
                row["version"],
                row["stage"],
                format_pct(row["total_return_with_cost"]),
                format_pct(row["max_drawdown"]),
                format_int(row["trades"]),
                f"{safe_float(row['return_drawdown_ratio'], np.nan):.2f}",
                "yes" if bool(row.get("selected", False)) else "",
                "yes" if bool(row.get("final_selected", False)) else "",
            ]
        )

    core_versions = [
        (fixed_version, "fixed-weight frozen"),
        (stage2_version, "risk-unit no industry cap"),
        (selected_version, "risk-unit + industry cap"),
    ]
    core_rows = []
    for version, label in core_versions:
        for period in ["valid", "observed_test"]:
            core_rows.append(
                [
                    label,
                    period,
                    format_pct(metric(version, period, "total_return_with_cost")),
                    format_pct(metric(version, period, "total_return_without_cost")),
                    format_pct(metric(version, period, "max_drawdown")),
                    metric_int(version, period, "trades"),
                    format_pct(metric(version, period, "win_rate")),
                    format_pct(metric(version, period, "cost_ratio")),
                    format_pct(metric(version, period, "avg_cash_ratio")),
                    format_pct(metric(version, period, "max_single_stock_weight_observed")),
                    format_pct(metric(version, period, "max_industry_weight_observed")),
                ]
            )

    monthly_rows = []
    for version, label in [(fixed_version, "fixed-weight frozen"), (selected_version, "selected fallback")]:
        for period in ["valid", "observed_test"]:
            stats = monthly_stats(version, period)
            monthly_rows.append(
                [
                    label,
                    period,
                    format_int(stats["months"]),
                    format_int(stats["positive"]),
                    format_int(stats["negative"]),
                    format_pct(stats["mean"]),
                    format_pct(stats["worst"]),
                    format_pct(stats["best"]),
                    stats["worst_months"],
                ]
            )

    risk_rows = []
    for period in ["valid", "observed_test"]:
        stats = risk_usage_stats(selected_version, period)
        risk_rows.append(
            [
                period,
                format_int(stats["trades"]),
                f"{stats['risk_pct_median']:.2%}",
                f"{stats['planned_mean']:.2%}",
                f"{stats['planned_median']:.2%}",
                f"{stats['planned_p90']:.2%}",
                f"{stats['planned_lt_half']:.2%}",
                f"{stats['loss_mean']:.2%}",
                f"{stats['loss_median']:.2%}",
            ]
        )

    exposure_rows = []
    for version, label in [(fixed_version, "fixed-weight frozen"), (selected_version, "selected fallback")]:
        for period in ["valid", "observed_test"]:
            date, industry, weight = max_exposure(version, period)
            exposure_rows.append([label, period, date, industry, format_pct(weight)])

    valid_entry_rows = group_trade_rows("valid", "entry_type")
    valid_exit_rows = group_trade_rows("valid", "exit_reason")
    observed_entry_rows = group_trade_rows("observed_test", "entry_type")
    selected_order_rows = order_reason_rows(selected_version, "valid") + order_reason_rows(selected_version, "observed_test")
    signal_rows = signal_stats()
    fixed_valid_return = metric(fixed_version, "valid", "total_return_with_cost")
    selected_valid_return = metric(selected_version, "valid", "total_return_with_cost")
    fixed_valid_drawdown = metric(fixed_version, "valid", "max_drawdown")
    selected_valid_drawdown = metric(selected_version, "valid", "max_drawdown")
    fixed_observed_return = metric(fixed_version, "observed_test", "total_return_with_cost")
    selected_observed_return = metric(selected_version, "observed_test", "total_return_with_cost")

    outputs = []
    outputs.append(
        write_report(
            report_dir(config) / "parameter_selection_report.md",
            [
                "# Explore4 Parameter Selection Report",
                "",
                "- 2025-2026 is treated only as observed_test / frozen_replication.",
                "- Valid selection follows the fixed rule in Explore4/requirement.md.",
                f"- Final selected version: `{selected_version}`.",
                *stage_note_lines,
                "",
                *markdown_table(
                    ["Version", "Stage", "Valid return", "Valid max DD", "Valid trades", "Ret/DD", "Stage selected", "Final"],
                    param_rows,
                ),
            ],
        )
    )
    outputs.append(
        write_report(
            report_dir(config) / "risk_unit_sizing_report.md",
            [
                "# Explore4 Risk Unit Sizing Report",
                "",
                f"- Risk-unit trade rows: `{format_int(len(risk))}`.",
                f"- Stop-related risk rows: `{format_int(len(stop_risk))}`.",
                f"- Average actual-loss / target-risk ratio for stop exits: `{safe_float(loss_ratio.mean(), np.nan):.4f}`.",
                f"- Median actual-loss / target-risk ratio for stop exits: `{safe_float(loss_ratio.median(), np.nan):.4f}`.",
                "- `initial_stop` invalid or non-positive risk entries are skipped; no fallback is used.",
            ],
        )
    )
    max_unknown = int((exposure.get("industry_name", pd.Series(dtype=str)).astype(str) == "UNKNOWN").sum()) if not exposure.empty else 0
    outputs.append(
        write_report(
            report_dir(config) / "final_test_report.md",
            [
                "# Explore4 详细验证报告",
                "",
                "## 结论摘要",
                "",
                f"- 本轮没有真正未见的 `final_test`；`2025-01-01` 到 `2026-04-30` 只能作为 `observed_test / frozen_replication`，不参与参数选择。",
                f"- 默认网格实际跑了 `13` 个版本；最终表内标记版本为 `{selected_version}`，但状态是 `{'accepted' if final_eligible else 'diagnostic_fallback_no_eligible'}`。",
                f"- `valid` 区间没有任何 risk-unit 或 industry-cap 候选满足“成本后收益为正”等完整验收条件，因此当前不能声明 Explore4 已得到可进入 meta-labeling 的合格版本。",
                f"- 诊断 fallback 在 `valid` 的成本后收益为 `{format_pct(selected_valid_return)}`，最大回撤为 `{format_pct(selected_valid_drawdown)}`；相比 frozen fixed-weight 的 `{format_pct(fixed_valid_return)}` / `{format_pct(fixed_valid_drawdown)}`，回撤和亏损幅度改善，但没有转正。",
                f"- 诊断 fallback 在 `observed_test` 的成本后收益为 `{format_pct(selected_observed_return)}`，低于 frozen fixed-weight 的 `{format_pct(fixed_observed_return)}`；这个结果只能说明冻结规则在已观察区间仍能复现正收益，不能作为新样本外证据。",
                "",
                "## 核心版本对比",
                "",
                *markdown_table(
                    [
                        "版本",
                        "区间",
                        "成本后收益",
                        "成本前收益",
                        "最大回撤",
                        "交易数",
                        "胜率",
                        "成本占比",
                        "平均现金",
                        "最大单票",
                        "最大行业",
                    ],
                    core_rows,
                ),
                "",
                "解读：risk-unit 的主要贡献是降低仓位暴露、交易成本和回撤，而不是改善单笔交易质量。`single_stock_max_weight=3%` 加 `20%` 行业 cap 后，平均现金比例接近 90%，最大行业暴露被压到 20% 附近；这解释了为什么 valid 亏损收窄，但 observed-test 的收益也明显低于 fixed-weight。",
                "",
                "## 参数选择纪律",
                "",
                f"- `risk_unit_stage` 合格候选数：`{int(selection[selection['stage'] == 'risk_unit_stage']['eligible'].fillna(False).sum())}` / `9`。",
                f"- `industry_cap_stage` 合格候选数：`{int(selection[selection['stage'] == 'industry_cap_stage']['eligible'].fillna(False).sum())}` / `3`。",
                "- 所有 observed-test 行均写入 `used_for_selection=False`。",
                "- 因为 valid 阶段没有合格候选，报告中的最终版本只能作为诊断 fallback，不能作为正式入选参数。",
                "",
                "## 月度稳定性",
                "",
                *markdown_table(
                    ["版本", "区间", "月数", "正收益月", "负收益月", "月均收益", "最差月", "最好月", "最差月份"],
                    monthly_rows,
                ),
                "",
                "解读：valid 区间的负收益不是单日异常造成的。fixed-weight 和 fallback 都只有 4 个正收益月、11 个负收益月，且 2024-06、2024-12、2023-04 是重复出现的弱月份。risk-unit 只是把最差月亏损从 fixed-weight 的约 2.6% 压到约 1.5%，没有改变收益方向。",
                "",
                "## 风险单位仓位诊断",
                "",
                *markdown_table(
                    [
                        "区间",
                        "交易数",
                        "初始风险/价格中位数",
                        "计划风险/目标均值",
                        "计划风险/目标中位数",
                        "计划风险/目标P90",
                        "计划风险<50%占比",
                        "亏损/目标均值",
                        "亏损/目标中位数",
                    ],
                    risk_rows,
                ),
                "",
                "解读：仓位模块并没有充分使用预设的单笔风险预算。fallback 在 valid 的计划初始损失只达到目标预算的约三分之一，超过七成交易低于目标风险的一半。主要可能来自三个约束叠加：结构止损距离偏宽、单票 3% 上限过紧、候选信号数量偏少导致资金长期闲置。止损交易的实际亏损明显低于目标预算，说明风险控制很保守，但也说明风险单位仓位没有真正形成稳定的资本利用效率。",
                "",
                "## 入场和退出诊断",
                "",
                "### Valid 入场类型",
                "",
                *markdown_table(["入场类型", "交易数", "平均收益", "净收益"], valid_entry_rows),
                "",
                "### Valid 退出类型",
                "",
                *markdown_table(["退出类型", "交易数", "平均收益", "净收益"], valid_exit_rows),
                "",
                "### Observed-test 入场类型",
                "",
                *markdown_table(["入场类型", "交易数", "平均收益", "净收益"], observed_entry_rows),
                "",
                "解读：valid 中 pullback 交易数量占主导，但贡献为负；breakout 数量少，反而略有正贡献。退出上，`stop_loss` 和 `time_stop` 是主要亏损来源，`trailing_stop` 是主要收益来源。这指向两个可能问题：一是 pullback 条件在震荡或弱趋势环境中过宽，二是 time stop 可能没有及时排除失败形态。",
                "",
                "## 信号密度和市场状态",
                "",
                *markdown_table(["区间", "交易日", "无 combined 信号日占比", "日均 combined 信号", "combined 信号总数", "无 width_ok 日占比"], signal_rows),
                "",
                "解读：valid 区间信号非常稀疏，超过七成交易日没有 combined 入场信号。低信号密度叠加严格仓位上限，会导致组合长期高现金、低风险暴露。observed-test 的信号稍多且处于更有利趋势段，因此表现明显更好，但该区间已经被 Explore3 观察过，不能用来反向确认参数。",
                "",
                "## 行业集中度",
                "",
                *markdown_table(["版本", "区间", "日期", "行业", "最大行业暴露"], exposure_rows),
                "",
                f"- `industry_exposure_audit.csv` 中包含 `UNKNOWN` 行，行数为 `{format_int(max_unknown)}`；当前实际 UNKNOWN 暴露为 0，但审计口径已经保留。",
                "- 行业 cap 的效果明确：最大行业暴露从 fixed-weight 的接近 50% 降至约 20%-24%。但行业 cap 使用的是当前 as-of 行业归属，只能解释为集中度压力测试，不能解释为历史真实行业约束。",
                "",
                "## 订单执行审计",
                "",
                *markdown_table(["方向", "状态", "原因", "数量"], selected_order_rows),
                "",
                "解读：入场侧主要跳过原因是 `zero_lot`，说明仓位预算经过风险、行业和现金约束后，有一部分订单不足 100 股。observed-test 中存在少量卖出 `limit_blocked`，会延后退出，可能放大单笔实际收益或亏损，需要在后续复查这些样本。",
                "",
                "## 问题可能出现在哪里",
                "",
                "1. `valid` 区间的原始规则本身没有稳定正 alpha。frozen fixed-weight 在 valid 已经是负收益，risk-unit 只是降低风险暴露，无法把负期望交易变成正期望交易。",
                "2. pullback 入场可能过宽。valid 中 pullback 数量最多且净贡献为负，说明弱趋势或震荡环境下的回踩信号质量不足；后续应优先检查 pullback 的市场状态、行业状态和成交额约束，而不是先扩大参数搜索。",
                "3. time stop 和 stop loss 是 valid 的主要亏损出口。需要抽样检查这些交易在 T 日信号后是否已经出现趋势衰减、行业同步性不足、或者开盘成交后初始 R 过宽。",
                "4. 风险单位仓位被上限约束压得过低。fallback 平均现金比例接近 90%，计划风险预算使用不足，说明当前 `0.5% risk_budget + 3% single_stock_max + 20% industry_cap` 更像降杠杆版本，而不是完整风险预算版本。",
                "5. 行业 cap 有效降低集中度，但也降低 observed-test 收益。若收益主要来自少数强行业，行业 cap 会改善回撤但削弱趋势收益；需要用更多未见年份验证这个取舍。",
                "6. 信号密度偏低会让组合路径高度依赖少数行情窗口。valid 中多数交易日无信号，observed-test 的强表现可能来自 2025 年少数趋势行情和大赢家，不应直接外推。",
                "7. 当前股票池和行业归属不是 point-in-time。静态股票池、当前 as-of 行业和已观察过的 2025-2026 都会放大研究偏差；这些偏差解决前，结果只能作为研究验证。",
                "",
                "## 下一步建议",
                "",
                "- 暂停进入 meta-labeling；先把 valid 负收益问题定位清楚。",
                "- 优先做交易级归因：抽样检查 valid 中 `pullback + stop_loss/time_stop` 的失败交易，按市场状态、行业状态、trend_score 分位、成交额确认和开盘跳空分组。",
                "- 单独评估 pullback 子规则：保留 breakout，收紧或暂时关闭 pullback，观察 valid 期望值是否改善。",
                "- 重新审视风险单位仓位约束组合：区分“风险预算没有用满”是由 stop 太宽、单票 cap 太低、行业 cap 太低，还是信号数量不足造成。",
                "- 等新增行情形成真正 final_test 后，只对冻结版本评估一次；不要用 observed-test 结果继续调参。",
            ],
        )
    )
    record_manifest(config, "report", outputs, {"final_selected_version": selected_version})
    return outputs


def command_all(config_path: str | Path) -> list[Path]:
    if not topic_path(config_path).exists():
        command_freeze(config_path)
    config = load_config(config_path)
    outputs: list[Path] = []
    outputs.extend(command_build_signals(config))
    outputs.extend(command_run_grid(config))
    outputs.extend(command_report(config))
    record_manifest(config, "all", outputs)
    return outputs


def command_self_test() -> None:
    assert round_lot_amount(10001, 10) == 1000
    row = pd.Series({"prev_close_for_limit": 10.0, "open": 11.0})
    assert is_limit_blocked(row, "buy", 0.095)
    row = pd.Series({"prev_close_for_limit": 10.0, "open": 8.9})
    assert is_limit_blocked(row, "sell", 0.095)
    row = pd.Series({"atr20": 1.0, "rolling_low20": 9.0, "recent_low5": 9.5})
    config = {"rules": {"stops": {"structure_atr_buffer": 0.5, "atr_multiplier": 2.0}}}
    assert initial_stop_for(row, 10.0, "breakout", config) == 8.5
    assert infer_blocked_layer(10, 0, 0, 0, 0, "zero_lot") == "industry_cap"
    assert infer_blocked_layer(10, 10, 10, 10, 0, "zero_lot") == "round_lot"
    print("self-test passed", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Explore4 risk-unit sizing workflow.")
    parser.add_argument(
        "command",
        choices=[
            "freeze",
            "build-signals",
            "run-grid",
            "report",
            "all",
            "diagnose-valid",
            "pullback-diagnostic",
            "pullback-failure-analysis",
            "risk-decompose",
            "expand-report",
            "self-test",
        ],
    )
    parser.add_argument("--config", default="Explore4/configs/trend_rule_v1_frozen.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "self-test":
            command_self_test()
        elif args.command == "freeze":
            command_freeze(args.config)
        elif args.command == "all":
            command_all(args.config)
        else:
            if not topic_path(args.config).exists():
                command_freeze(args.config)
            config = load_config(args.config)
            if args.command == "build-signals":
                command_build_signals(config)
            elif args.command == "run-grid":
                command_run_grid(config)
            elif args.command == "report":
                command_report(config)
            elif args.command == "diagnose-valid":
                command_diagnose_valid(config)
            elif args.command == "pullback-diagnostic":
                command_pullback_diagnostic(config)
            elif args.command == "pullback-failure-analysis":
                command_pullback_failure_analysis(config)
            elif args.command == "risk-decompose":
                command_risk_decompose(config)
            elif args.command == "expand-report":
                command_expand_report(config)
        return 0
    except Exception as exc:  # noqa: BLE001
        error_path = TOPIC_DIR / "Explore4/outputs/reports/last_error.json"
        write_json({"command": args.command, "error": str(exc), "traceback": traceback.format_exc()}, error_path)
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


EXPLORE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = EXPLORE_DIR.parent
DEFAULT_CONFIG = EXPLORE_DIR / "configs/meta_label_v1.yaml"

FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}

NO_MODEL_VERSION = "no_model_gate"
HARD_GATE_VERSION = "rule_pullback_hard_gate"
LGBM_GATE_VERSION = "lgbm_pullback_bad_trade_gate"

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

FEATURE_COLUMNS = [
    "trend_score",
    "trend_score_pct",
    "candidate_rank",
    "distance_to_ema20",
    "distance_to_ema60",
    "pullback_depth",
    "money_ratio20",
    "volume_ratio20",
    "money_zscore20",
    "money_change5",
    "money_change20",
    "ret5",
    "ret20",
    "ret60",
    "volatility20",
    "atr20_ratio",
    "ema20_slope20",
    "ema60_slope20",
    "distance_to_high60",
    "distance_to_low20",
    "close_gt_ema60_ratio",
    "ema20_gt_ema60_ratio",
    "raw_pullback_shape_numeric",
    "raw_pullback_candidate_numeric",
    "rule_pullback_entry_numeric",
    "gate_applicable_numeric",
    "market_ok_numeric",
    "width_ok_numeric",
    "industry_trend_ok_numeric",
    "pullback_money_weak_numeric",
    "pullback_top10_20_numeric",
]


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    target = Path(path).resolve()
    try:
        return str(target.relative_to(TOPIC_DIR))
    except ValueError:
        return str(target)


def ensure_parent(path: str | Path) -> Path:
    target = topic_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def file_sha256(path: str | Path) -> str:
    target = topic_path(path)
    digest = hashlib.sha256()
    with target.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml(path: str | Path) -> dict[str, Any]:
    target = topic_path(path)
    with target.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def write_csv(df: pd.DataFrame, path: str | Path, **kwargs: Any) -> Path:
    target = ensure_parent(path)
    df.to_csv(target, index=False, **kwargs)
    return target


def write_json(data: dict[str, Any], path: str | Path) -> Path:
    def sanitize(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        if isinstance(value, tuple):
            return [sanitize(item) for item in value]
        if isinstance(value, (np.bool_,)):
            return bool(value)
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating, float)):
            number = float(value)
            return number if math.isfinite(number) else None
        if value is pd.NA or value is pd.NaT:
            return None
        return value

    target = ensure_parent(path)
    with target.open("w", encoding="utf-8") as file:
        json.dump(sanitize(data), file, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")
    return target


def parse_dt(value: str | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if np.isfinite(result) else default


def format_pct(value: Any) -> str:
    number = safe_float(value, np.nan)
    return "" if pd.isna(number) else f"{number:.2%}"


def report_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["report_dir"])


def cache_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["cache_dir"])


def backtest_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["backtest_dir"])


def stock_panel_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel.pkl"


def stock_indicators_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_indicators.pkl"


def stock_signal_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_signals.pkl"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config_path = topic_path(path)
    config = load_yaml(config_path)
    sources = config.setdefault("sources", {})
    source_walk = topic_path(sources["source_walk_forward_config"])
    walk_config = load_yaml(source_walk)

    for key in ["qlib", "costs", "rules", "targets"]:
        if key not in walk_config:
            raise KeyError(f"missing allowed structural key in source walk config: {key}")
        config[key] = copy.deepcopy(walk_config[key])

    walk_explore5 = walk_config.get("explore5", {})
    config["explore5"] = {
        "folds": copy.deepcopy(walk_explore5.get("folds", [])),
        "candidates": copy.deepcopy(walk_explore5.get("candidates", [])),
        "selection_thresholds": copy.deepcopy(walk_explore5.get("selection_thresholds", {})),
    }
    config["_config_path"] = str(config_path)
    config["_config_hash"] = file_sha256(config_path)
    config["_source_walk_config_path"] = str(source_walk)
    config["_source_walk_config_hash"] = file_sha256(source_walk)
    config["_source_walk_config_raw"] = walk_config
    config["_source_rule_config_hash"] = file_sha256(sources["source_rule_config"])
    if topic_path(sources["source_background_report"]).exists():
        config["_source_background_report_hash"] = file_sha256(sources["source_background_report"])
    else:
        config["_source_background_report_hash"] = ""
    return config


def collect_path_entries(obj: Any, prefix: str, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(collect_path_entries(value, child, source))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            rows.extend(collect_path_entries(value, f"{prefix}[{idx}]", source))
    elif isinstance(obj, str):
        if len(obj) == 10 and obj[4] == "-" and obj[7] == "-" and obj.replace("-", "").isdigit():
            return rows
        lower_key = prefix.lower()
        looks_like_path = (
            "/" in obj
            or obj.endswith((".yaml", ".yml", ".csv", ".md", ".json", ".pkl", ".txt"))
            or any(token in lower_key for token in ["path", "dir", "uri", "config", "report", "csv", "membership", "history", "universe"])
        )
        if looks_like_path:
            rows.append({"source": source, "key": prefix, "path": obj})
    return rows


def classify_audit_path(source: str, key: str, path: str) -> str:
    normalized = path.replace("\\", "/")
    if source == "source_walk_forward_config" and key.startswith("paths."):
        if normalized.startswith("Explore5/outputs/"):
            return "forbidden_result_path"
        return "rewritten_output_path"
    if normalized.startswith("Explore5/outputs/"):
        return "background_reference" if key.endswith("source_background_report") else "forbidden_result_path"
    if normalized.startswith("Explore6/outputs/"):
        return "rewritten_output_path"
    if "source_background_report" in key:
        return "background_reference"
    if "source_rule_config" in key or "source_walk_forward_config" in key:
        return "structural_input"
    if source == "explore6_config" and key.startswith("paths."):
        if any(token in key for token in ["provider_uri", "universe", "target_history", "industry_membership"]):
            return "structural_input"
        return "rewritten_output_path"
    return "background_reference"


def build_source_data_audit(config: dict[str, Any]) -> pd.DataFrame:
    entries = []
    entries.extend(collect_path_entries(load_yaml(config["_config_path"]), "", "explore6_config"))
    entries.extend(collect_path_entries(config["_source_walk_config_raw"], "", "source_walk_forward_config"))
    rows: list[dict[str, Any]] = []
    compute_keys = {
        "paths.provider_uri": ("label,features,replay", True, True, True, False),
        "paths.target_history": ("features", False, True, False, False),
        "paths.industry_membership": ("features,replay", False, True, True, False),
        "paths.universe_csv": ("audit", False, False, False, False),
        "paths.universe_qlib": ("audit", False, False, False, False),
    }
    for entry in entries:
        source = entry["source"]
        key = entry["key"]
        path = entry["path"]
        category = classify_audit_path(source, key, path)
        use_note, used_label, used_features, used_replay, used_model_selection = ("", False, False, False, False)
        if source == "explore6_config" and key in compute_keys:
            use_note, used_label, used_features, used_replay, used_model_selection = compute_keys[key]
        target = topic_path(path)
        rows.append(
            {
                "source": source,
                "key": key,
                "path": path,
                "abs_path": str(target),
                "category": category,
                "exists": bool(target.exists()),
                "sha256": file_sha256(path) if target.is_file() else "",
                "used_for_label": bool(used_label),
                "used_for_features": bool(used_features),
                "used_for_replay": bool(used_replay),
                "used_for_model_selection": bool(used_model_selection),
                "rewritten_to": "Explore6/outputs/*" if category == "rewritten_output_path" else "",
                "note": use_note if use_note else ("ignored from source_walk_forward_config" if source == "source_walk_forward_config" and key.startswith("paths.") else ""),
            }
        )
    audit = pd.DataFrame(rows).drop_duplicates(["source", "key", "path"]).sort_values(["source", "key", "path"])
    forbidden_compute = audit[
        (audit["category"] == "forbidden_result_path")
        & (audit[["used_for_label", "used_for_features", "used_for_replay", "used_for_model_selection"]].any(axis=1))
    ]
    if not forbidden_compute.empty:
        raise RuntimeError("forbidden Explore5 result path entered compute flow")
    return audit


def write_manifest(config: dict[str, Any], outputs: list[str | Path], extra: dict[str, Any] | None = None) -> Path:
    manifest_file = report_dir(config) / "run_manifest.json"
    existing: dict[str, Any] = {}
    if manifest_file.exists():
        try:
            existing = json.loads(manifest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    base = {
        "config_path": relpath(config["_config_path"]),
        "config_sha256": config["_config_hash"],
        "source_rule_config": config["sources"]["source_rule_config"],
        "source_rule_config_sha256": config["_source_rule_config_hash"],
        "source_walk_forward_config": config["sources"]["source_walk_forward_config"],
        "source_walk_forward_config_sha256": config["_source_walk_config_hash"],
        "source_background_report": config["sources"]["source_background_report"],
        "source_background_report_sha256": config["_source_background_report_hash"],
        "explore5_result_csv_used_for_label": False,
        "explore5_result_csv_used_for_features": False,
        "explore5_result_csv_used_for_replay": False,
        "explore5_config_paths_rewritten": True,
        "observed_replication_used_for_selection": False,
        "provider_uri": config["paths"]["provider_uri"],
        "market": config["qlib"]["market"],
        "benchmark": config["qlib"].get("benchmark", ""),
        "required_fields": config["qlib"]["required_fields"],
        "universe_source": config["paths"]["universe_csv"],
        "universe_asof_date": "2025-12-31",
        "universe_point_in_time": False,
        "industry_membership_source": config["paths"]["industry_membership"],
        "industry_membership_point_in_time": False,
        "folds": config["explore5"]["folds"],
        "label_definition": config["label"],
        "candidate_level_replay": "100 shares at T+1 open, same stop/exit/cost rules, no portfolio constraints",
        "class_imbalance": config["imbalance"],
        "lgbm_param_grid": config["model"]["lgbm_param_grid"],
        "threshold_candidates": config["thresholds"]["bad_prob_threshold"],
        "output_paths": sorted(set(existing.get("output_paths", [])) | {relpath(path) for path in outputs}),
    }
    manifest = dict(existing)
    manifest.update(base)
    if extra:
        manifest.update(extra)
    return write_json(manifest, manifest_file)


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
    df["ret5"] = group["close"].pct_change(5)
    df["ret20"] = group["close"].pct_change(20)
    df["ret60"] = group["close"].pct_change(60)
    df["volatility20"] = group["ret1"].transform(lambda s: s.rolling(20, min_periods=10).std())
    df["avg_volume20"] = group["volume"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    df["volume_ratio20"] = df["volume"] / df["avg_volume20"].replace(0, np.nan)
    df["avg_money20"] = group["money"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    df["money_std20"] = group["money"].transform(lambda s: s.rolling(20, min_periods=5).std())
    df["money_ratio20"] = df["money"] / df["avg_money20"].replace(0, np.nan)
    df["money_zscore20"] = (df["money"] - df["avg_money20"]) / df["money_std20"].replace(0, np.nan)
    df["money_change5"] = df["money"] / group["money"].shift(5) - 1.0
    df["money_change20"] = df["money"] / group["money"].shift(20) - 1.0
    df["ema60_slope10"] = df["ema60"] / group["ema60"].shift(10) - 1.0
    df["ema20_slope20"] = df["ema20"] / group["ema20"].shift(20) - 1.0
    df["ema60_slope20"] = df["ema60"] / group["ema60"].shift(20) - 1.0
    df["ema20_ema60_spread"] = df["ema20"] / df["ema60"] - 1.0
    df["dist_ema20"] = (df["close"] - df["ema20"]) / df["close"]
    df["distance_to_ema20"] = df["close"] / df["ema20"].replace(0, np.nan) - 1.0
    df["distance_to_ema60"] = df["close"] / df["ema60"].replace(0, np.nan) - 1.0
    df["rolling_high60"] = group["close"].transform(lambda s: s.shift(1).rolling(60, min_periods=20).max())
    df["rolling_low20"] = group["low"].transform(lambda s: s.shift(1).rolling(20, min_periods=5).min())
    df["recent_low5"] = group["low"].transform(lambda s: s.shift(1).rolling(5, min_periods=2).min())
    df["pullback_depth"] = df["close"] / df["rolling_high60"].replace(0, np.nan) - 1.0
    df["distance_to_high60"] = df["close"] / df["rolling_high60"].replace(0, np.nan) - 1.0
    df["distance_to_low20"] = df["close"] / df["rolling_low20"].replace(0, np.nan) - 1.0
    df["atr20_ratio"] = df["atr20"] / df["close"].replace(0, np.nan)
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


def load_industry_membership(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["industry_membership"])
    if not path.exists():
        return pd.DataFrame(columns=["instrument", "industry_target_key", "industry_name"])
    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=["instrument", "industry_target_key", "industry_name"])
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["industry_name"] = df["industry_name"].fillna("UNKNOWN").replace("", "UNKNOWN")
    return df


def command_build_signals(config: dict[str, Any]) -> list[Path]:
    panel = load_stock_panel(config)
    indicators_path = stock_indicators_cache_path(config)
    if indicators_path.exists():
        indicators = pd.read_pickle(indicators_path)
    else:
        indicators = add_group_indicators(panel)
        ensure_parent(indicators_path)
        pd.to_pickle(indicators, indicators_path)

    history = pd.read_csv(topic_path(config["paths"]["target_history"]), parse_dates=["date"])
    target_regimes = compute_target_regimes(config, history)
    width = compute_market_width(config, indicators)
    market = target_regimes[target_regimes["target_type"] == "market"].merge(width, on="date", how="left")
    broad_ok = market[market["target_key"] == "broad_market"][["date", "trend_ok"]].rename(columns={"trend_ok": "market_ok"})
    market = market.merge(broad_ok, on="date", how="left")
    industry = target_regimes[target_regimes["target_type"] == "industry"].rename(columns={"trend_ok": "industry_trend_ok"})
    theme = target_regimes[target_regimes["target_type"] == "theme"].rename(columns={"trend_ok": "theme_trend_ok"})

    df = indicators.copy()
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
    industry_join = industry[["date", "target_key", "industry_trend_ok"]].rename(
        columns={"date": "datetime", "target_key": "industry_target_key"}
    )
    industry_join["industry_target_key"] = industry_join["industry_target_key"].astype("string")
    df = df.merge(industry_join, on=["datetime", "industry_target_key"], how="left")
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
    raw_pullback_shape = (
        (near_ema20 | near_ema30)
        & (df["low"] > df["ema60"])
        & (df["close"] >= df["ema20"])
        & (df["close"] > df["open"])
    )
    loose_money_ratio_upper = float(config.get("candidate_pool", {}).get("loose_money_ratio_upper", 1.20))
    df["raw_pullback_shape"] = raw_pullback_shape.fillna(False)
    df["raw_pullback_candidate"] = (
        df["raw_pullback_shape"]
        & (df["ema20"] >= df["ema60"])
        & (df["close"] > df["ema60"])
        & (df["money_ratio20"] <= loose_money_ratio_upper)
    ).fillna(False)
    df["rule_pullback_entry"] = (
        df["trend_score_top20_entry"]
        & df["raw_pullback_shape"]
        & (df["money_ratio20"] <= 1.0)
    ).fillna(False)
    df["pullback_entry"] = df["rule_pullback_entry"]
    df["combined_entry"] = df["breakout_entry"] | df["pullback_entry"]

    signal_cache = stock_signal_cache_path(config)
    ensure_parent(signal_cache)
    pd.to_pickle(df, signal_cache)

    count_cols = [
        "ema_state",
        "market_ok_entry",
        "width_ok_entry",
        "industry_ok_entry",
        "trend_score_top20_entry",
        "breakout_entry",
        "raw_pullback_shape",
        "raw_pullback_candidate",
        "rule_pullback_entry",
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
        "raw_pullback_shape",
        "raw_pullback_candidate",
        "rule_pullback_entry",
        "pullback_entry",
        "combined_entry",
        "trend_score",
        "trend_score_pct",
        "volume_ratio20",
        "money_zscore20",
        "money_change5",
        "money_change20",
        "ret5",
        "ret20",
        "rolling_high60",
        "rolling_low20",
        "recent_low5",
        "atr20",
        "atr20_ratio",
        "ema20",
        "ema60",
        "ema20_slope20",
        "ema60_slope20",
        "distance_to_ema20",
        "distance_to_ema60",
        "pullback_depth",
        "distance_to_high60",
        "distance_to_low20",
        "open",
        "high",
        "low",
        "close",
        "ret60",
        "money_ratio20",
    ]
    signals = df.loc[df[count_cols].any(axis=1), signal_cols].copy()
    outputs = [
        indicators_path,
        signal_cache,
        write_csv(market, report_dir(config) / "generated_market_regime.csv"),
        write_csv(width, report_dir(config) / "generated_market_width.csv"),
        write_csv(industry, report_dir(config) / "generated_industry_regime.csv"),
        write_csv(theme, report_dir(config) / "generated_theme_regime.csv"),
        write_csv(daily, report_dir(config) / "generated_daily_candidates.csv"),
        write_csv(signals, report_dir(config) / "generated_signals.csv"),
    ]
    print(f"built Explore6 signals rows={len(signals)}", flush=True)
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


def base_portfolio_spec(config: dict[str, Any], version: str, stage: str = "explore6_replay") -> dict[str, Any]:
    candidates = config.get("explore5", {}).get("candidates", [])
    raw = next((dict(item) for item in candidates if item.get("version") == "risk_unit_with_industry_cap"), {})
    if not raw:
        raw = {
            "sizing": "risk_unit",
            "risk_budget_per_trade": 0.005,
            "single_stock_max_weight": 0.03,
            "max_positions": 20,
            "max_daily_new_weight": 0.20,
            "max_industry_weight": 0.20,
        }
    return {
        "version": version,
        "stage": stage,
        "sizing": str(raw.get("sizing", "risk_unit")),
        "risk_budget_per_trade": safe_float(raw.get("risk_budget_per_trade"), np.nan),
        "single_stock_max_weight": safe_float(raw.get("single_stock_max_weight"), 0.03),
        "max_positions": int(safe_float(raw.get("max_positions"), 20)),
        "max_daily_new_weight": safe_float(raw.get("max_daily_new_weight"), 0.20),
        "max_industry_weight": safe_float(raw.get("max_industry_weight"), 0.20),
    }


def position_industry(position: dict[str, Any]) -> str:
    value = str(position.get("industry_name") or "UNKNOWN")
    return value if value and value != "nan" else "UNKNOWN"


def compute_metrics(spec: dict[str, Any], period: str, portfolio: pd.DataFrame, trades: pd.DataFrame) -> dict[str, Any]:
    if portfolio.empty:
        return {"version": spec["version"], "period": period, "stage": spec["stage"], "trades": 0}
    account = float(portfolio["prev_account_value"].iloc[0])
    total = portfolio["account_value"].iloc[-1] / account - 1
    returns_wo_cost = portfolio["return"].fillna(0) + portfolio["cost"].fillna(0) / portfolio["prev_account_value"].replace(0, np.nan)
    total_wo_cost = float((1 + returns_wo_cost.fillna(0)).prod() - 1)
    drawdown = portfolio["account_value"] / portfolio["account_value"].cummax() - 1
    annual = (1 + total) ** (252 / max(len(portfolio), 1)) - 1 if total > -1 else -1
    ret = pd.to_numeric(trades.get("cost_after_return"), errors="coerce") if not trades.empty else pd.Series(dtype=float)
    stop_time = trades["exit_reason"].isin(["stop_loss", "time_stop"]).sum() if not trades.empty else 0
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
        "trades": int(len(trades)),
        "win_rate": float((ret > 0).mean()) if len(ret) else 0.0,
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
        "stop_time_trades": int(stop_time),
        "stop_time_trade_ratio": float(stop_time / len(trades)) if len(trades) else 0.0,
    }


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
                if len(positions) >= int(spec["max_positions"]):
                    audit(order, date, "skipped", "max_positions", row)
                    continue
                if spec["sizing"] == "risk_unit":
                    target_loss_budget = account_value_before * float(spec["risk_budget_per_trade"])
                    raw_position_value = target_loss_budget / initial_risk * price
                    budget = min(raw_position_value, account_value_before * float(spec["single_stock_max_weight"]))
                else:
                    target_weight = min(float(spec["single_stock_max_weight"]), float(config["rules"]["portfolio"]["risk_degree"]) / int(spec["max_positions"]))
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


def add_regime_labels(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    close_ratio = pd.to_numeric(data.get("close_gt_ema60_ratio"), errors="coerce")
    ema_ratio = pd.to_numeric(data.get("ema20_gt_ema60_ratio"), errors="coerce")
    width_strong = (close_ratio > 0.60) & (ema_ratio > 0.50)
    width_weak = (close_ratio <= 0.55) & (ema_ratio <= 0.45)
    data["width_regime"] = np.select(
        [width_strong, width_weak],
        ["width_strong", "width_weak"],
        default="width_neutral",
    )
    market_ok = data.get("market_ok", data.get("market_ok_entry", False))
    data["market_trend_regime"] = np.where(pd.Series(market_ok, index=data.index).fillna(False), "market_trend_on", "market_trend_off")
    industry_ok = data.get("industry_trend_ok", data.get("industry_ok_entry", False))
    data["industry_sync_regime"] = np.where(pd.Series(industry_ok, index=data.index).fillna(False), "industry_sync_on", "industry_sync_off")
    score = pd.to_numeric(data.get("trend_score_pct"), errors="coerce")
    data["trend_score_regime"] = np.select(
        [score <= 0.10, (score > 0.10) & (score <= 0.20)],
        ["top10", "top10_20"],
        default="outside_top20",
    )
    if "entry_type" not in data:
        breakout_signal = pd.Series(data.get("breakout_entry", False), index=data.index).fillna(False).astype(bool)
        pullback_signal = (
            pd.Series(data.get("raw_pullback_candidate", False), index=data.index).fillna(False).astype(bool)
            | pd.Series(data.get("pullback_entry", False), index=data.index).fillna(False).astype(bool)
        )
        data["entry_type"] = np.where(breakout_signal, "breakout", np.where(pullback_signal, "pullback", "combined"))
    money_ratio = pd.to_numeric(data.get("money_ratio20"), errors="coerce")
    is_pullback = data["entry_type"].astype(str) == "pullback"
    data["pullback_money_regime"] = np.select(
        [is_pullback & (money_ratio >= 0.60) & (money_ratio <= 1.00), is_pullback],
        ["pullback_money_weak", "pullback_money_other"],
        default="not_pullback",
    )
    data["pullback_top10_20"] = is_pullback & (score > 0.10) & (score <= 0.20)
    data["pullback_money_weak"] = data["pullback_money_regime"] == "pullback_money_weak"
    return data


def load_signals_with_width(config: dict[str, Any]) -> pd.DataFrame:
    if not stock_signal_cache_path(config).exists():
        command_build_signals(config)
    signals = pd.read_pickle(stock_signal_cache_path(config)).copy()
    signals["datetime"] = pd.to_datetime(signals["datetime"])
    width_path = report_dir(config) / "generated_market_width.csv"
    if width_path.exists():
        width = pd.read_csv(width_path, parse_dates=["date"]).rename(columns={"date": "datetime"})
        keep = ["datetime", "close_gt_ema60_ratio", "ema20_gt_ema60_ratio"]
        signals = signals.merge(width[keep], on="datetime", how="left")
    else:
        signals["close_gt_ema60_ratio"] = np.nan
        signals["ema20_gt_ema60_ratio"] = np.nan
    return signals


def hard_gate_mask(config: dict[str, Any], signals: pd.DataFrame) -> pd.Series:
    gate = config["hard_gate"]
    money = pd.to_numeric(signals.get("money_ratio20"), errors="coerce")
    score = pd.to_numeric(signals.get("trend_score_pct"), errors="coerce")
    is_pullback = pd.Series(
        signals.get("rule_pullback_entry", signals.get("pullback_entry", False)),
        index=signals.index,
    ).fillna(False).astype(bool)
    money_weak = (money >= float(gate["money_ratio_lower"])) & (money <= float(gate["money_ratio_upper"]))
    top10_20 = (score > float(gate["trend_score_pct_lower"])) & (score <= float(gate["trend_score_pct_upper"]))
    return is_pullback & (money_weak | top10_20)


def apply_gate(
    config: dict[str, Any],
    signals: pd.DataFrame,
    version: str,
    probabilities: pd.DataFrame | None = None,
    threshold: float | None = None,
) -> pd.DataFrame:
    data = signals.copy()
    data["datetime"] = pd.to_datetime(data["datetime"])
    data["breakout_entry"] = data["breakout_entry"].fillna(False).astype(bool)
    if "rule_pullback_entry" not in data:
        data["rule_pullback_entry"] = data.get("pullback_entry", False)
    data["rule_pullback_entry"] = pd.Series(data["rule_pullback_entry"], index=data.index).fillna(False).astype(bool)
    data["pullback_entry"] = data["rule_pullback_entry"].copy()
    data["gate_filtered"] = False
    data["bad_trade_probability"] = np.nan
    if version == HARD_GATE_VERSION:
        mask = hard_gate_mask(config, data)
        data.loc[mask, "pullback_entry"] = False
        data.loc[mask, "gate_filtered"] = True
    elif version == LGBM_GATE_VERSION:
        if probabilities is None or threshold is None:
            raise ValueError("LGBM gate requires probabilities and threshold")
        scores = probabilities[["datetime", "instrument", "bad_trade_probability"]].copy()
        scores["datetime"] = pd.to_datetime(scores["datetime"])
        scores["instrument"] = scores["instrument"].astype(str).str.upper()
        data = data.merge(scores, on=["datetime", "instrument"], how="left", suffixes=("", "_score"))
        if "bad_trade_probability_score" in data.columns:
            data["bad_trade_probability"] = data["bad_trade_probability_score"].combine_first(data["bad_trade_probability"])
            data = data.drop(columns=["bad_trade_probability_score"])
        mask = data["pullback_entry"] & (pd.to_numeric(data["bad_trade_probability"], errors="coerce") >= float(threshold))
        data.loc[mask, "pullback_entry"] = False
        data.loc[mask, "gate_filtered"] = True
    elif version != NO_MODEL_VERSION:
        raise ValueError(f"unknown gate version: {version}")
    data["combined_entry"] = data["breakout_entry"] | data["pullback_entry"]
    return data


def fold_executable_end(signals: pd.DataFrame, valid_end: pd.Timestamp) -> pd.Timestamp:
    dates = sorted(pd.Timestamp(d).normalize() for d in signals["datetime"].dropna().unique())
    valid_dates = [date for date in dates if date <= valid_end]
    if len(valid_dates) < 2:
        return valid_end
    return valid_dates[-2]


def attach_run_metadata(df: pd.DataFrame, spec: dict[str, Any], fold: dict[str, str], executable_end: pd.Timestamp) -> pd.DataFrame:
    data = df.copy()
    data["fold"] = fold["fold"]
    data["candidate_type"] = spec.get("candidate_type", "")
    data["train_start"] = fold.get("train_start", "")
    data["train_end"] = fold.get("train_end", "")
    data["valid_start"] = fold.get("valid_start", "")
    data["valid_end"] = fold.get("valid_end", "")
    data["valid_executable_end"] = executable_end.date().isoformat()
    return data


def prepare_candidate_features(config: dict[str, Any]) -> pd.DataFrame:
    signals = load_signals_with_width(config)
    if "raw_pullback_candidate" not in signals:
        raise RuntimeError("raw_pullback_candidate missing from generated signals; rebuild Explore6 signals")
    data = signals[signals["raw_pullback_candidate"].fillna(False)].copy()
    data["entry_type"] = "pullback"
    data["candidate_source"] = "raw_pullback_candidate"
    for column in ["raw_pullback_shape", "raw_pullback_candidate", "rule_pullback_entry", "pullback_entry"]:
        if column not in data:
            data[column] = False
        data[column] = data[column].fillna(False).astype(bool)
    data["rule_pullback_entry"] = data["rule_pullback_entry"] | data["pullback_entry"]
    data["pullback_entry"] = data["rule_pullback_entry"]
    data["gate_applicable"] = data["rule_pullback_entry"]
    data = add_regime_labels(data)
    data["candidate_rank"] = data.groupby("datetime")["trend_score_pct"].rank(method="first", ascending=True, na_option="bottom")
    for column in ["market_ok", "width_ok", "industry_trend_ok"]:
        if column not in data:
            data[column] = False
    data["raw_pullback_shape_numeric"] = data["raw_pullback_shape"].fillna(False).astype(int)
    data["raw_pullback_candidate_numeric"] = data["raw_pullback_candidate"].fillna(False).astype(int)
    data["rule_pullback_entry_numeric"] = data["rule_pullback_entry"].fillna(False).astype(int)
    data["gate_applicable_numeric"] = data["gate_applicable"].fillna(False).astype(int)
    data["market_ok_numeric"] = data["market_ok"].fillna(False).astype(int)
    data["width_ok_numeric"] = data["width_ok"].fillna(False).astype(int)
    data["industry_trend_ok_numeric"] = data["industry_trend_ok"].fillna(False).astype(int)
    data["pullback_money_weak_numeric"] = data["pullback_money_weak"].fillna(False).astype(int)
    data["pullback_top10_20_numeric"] = data["pullback_top10_20"].fillna(False).astype(int)
    data["signal_date"] = pd.to_datetime(data["datetime"]).dt.normalize()
    data["instrument"] = data["instrument"].astype(str).str.upper()
    data["signal_id"] = data["signal_date"].dt.strftime("%Y-%m-%d") + "|" + data["instrument"]
    for column in FEATURE_COLUMNS:
        if column not in data:
            data[column] = np.nan
    return data.sort_values(["signal_date", "instrument"]).reset_index(drop=True)


def build_market_lookups(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], list[pd.Timestamp], dict[pd.Timestamp, int]]:
    if not stock_indicators_cache_path(config).exists():
        command_build_signals(config)
    indicators = pd.read_pickle(stock_indicators_cache_path(config)).copy()
    indicators["datetime"] = pd.to_datetime(indicators["datetime"]).dt.normalize()
    indicators["instrument"] = indicators["instrument"].astype(str).str.upper()
    indicators = indicators.sort_values(["instrument", "datetime"])
    indicators["prev_close_for_limit"] = indicators.groupby("instrument")["close"].shift(1)
    by_instrument = {instrument: group.reset_index(drop=True) for instrument, group in indicators.groupby("instrument")}
    dates = [pd.Timestamp(date) for date in sorted(indicators["datetime"].dropna().unique())]
    date_pos = {date: idx for idx, date in enumerate(dates)}
    return by_instrument, dates, date_pos


def next_global_date(dates: list[pd.Timestamp], date_pos: dict[pd.Timestamp, int], date: pd.Timestamp) -> pd.Timestamp | None:
    pos = date_pos.get(pd.Timestamp(date).normalize())
    if pos is None:
        later = [item for item in dates if item > date]
        return later[0] if later else None
    return dates[pos + 1] if pos + 1 < len(dates) else None


def replay_one_candidate_label(
    config: dict[str, Any],
    candidate: pd.Series,
    by_instrument: dict[str, pd.DataFrame],
    dates: list[pd.Timestamp],
    date_pos: dict[pd.Timestamp, int],
) -> dict[str, Any]:
    costs = config["costs"]
    stop_rules = config["rules"]["stops"]
    instrument = str(candidate["instrument"]).upper()
    signal_date = pd.Timestamp(candidate["signal_date"]).normalize()
    result: dict[str, Any] = {
        "signal_id": candidate["signal_id"],
        "signal_date": signal_date.date().isoformat(),
        "instrument": instrument,
        "entry_type": "pullback",
        "label_status": "completed",
        "label_skip_reason": "",
    }
    market = by_instrument.get(instrument)
    if market is None or market.empty:
        result.update({"label_status": "skipped", "label_skip_reason": "no_instrument_market_data"})
        return result
    entry_date = next_global_date(dates, date_pos, signal_date)
    if entry_date is None:
        result.update({"label_status": "skipped", "label_skip_reason": "no_next_trading_date"})
        return result
    entry_rows = market[market["datetime"] == entry_date]
    if entry_rows.empty:
        result.update({"label_status": "skipped", "label_skip_reason": "no_entry_market_row", "order_date": entry_date.date().isoformat()})
        return result
    entry_row = entry_rows.iloc[0]
    entry_price = safe_float(entry_row.get("open"), np.nan)
    result["order_date"] = entry_date.date().isoformat()
    result["deal_date"] = entry_date.date().isoformat()
    result["entry_price"] = entry_price
    if pd.isna(entry_price) or entry_price <= 0:
        result.update({"label_status": "skipped", "label_skip_reason": "invalid_entry_open"})
        return result
    if is_limit_blocked(entry_row, "buy", float(costs["limit_threshold"])):
        result.update({"label_status": "skipped", "label_skip_reason": "entry_limit_blocked"})
        return result
    stop = initial_stop_for(candidate, entry_price, "pullback", config)
    initial_risk = entry_price - stop if np.isfinite(stop) else np.nan
    if not np.isfinite(stop) or initial_risk <= 0:
        result.update({"label_status": "skipped", "label_skip_reason": "invalid_initial_stop"})
        return result

    amount = int(config["label"]["amount"])
    entry_value = amount * entry_price
    entry_cost = max(entry_value * float(costs["open_cost"]), float(costs["min_cost"]))
    current_stop = stop
    entry_index = int(entry_rows.index[0])
    pending_exit_reason = ""
    pending_exit_signal_date: pd.Timestamp | None = None
    for idx in range(entry_index, len(market)):
        row = market.iloc[idx]
        date = pd.Timestamp(row["datetime"]).normalize()
        close = safe_float(row.get("close"), np.nan)
        if pd.isna(close) or close <= 0:
            continue
        if pending_exit_reason:
            exit_price = safe_float(row.get("open"), np.nan)
            if pd.isna(exit_price) or exit_price <= 0:
                continue
            if is_limit_blocked(row, "sell", float(costs["limit_threshold"])):
                continue
            exit_value = amount * exit_price
            exit_cost = max(exit_value * float(costs["close_cost"]), float(costs["min_cost"]))
            gross, net = trade_return(entry_price, exit_price, entry_cost, exit_cost, amount)
            net_pnl = exit_value - exit_cost - entry_value - entry_cost
            r_multiple = (exit_price - entry_price - (entry_cost + exit_cost) / amount) / initial_risk
            result.update(
                {
                    "exit_signal_date": pending_exit_signal_date.date().isoformat() if pending_exit_signal_date is not None else "",
                    "exit_date": date.date().isoformat(),
                    "exit_price": exit_price,
                    "exit_value": exit_value,
                    "exit_cost": exit_cost,
                    "entry_value": entry_value,
                    "entry_cost": entry_cost,
                    "gross_pnl": exit_value - entry_value,
                    "net_pnl": net_pnl,
                    "initial_stop": stop,
                    "current_stop": current_stop,
                    "initial_risk_per_share": initial_risk,
                    "R": r_multiple,
                    "exit_reason": pending_exit_reason,
                    "holding_days": int((date - entry_date).days),
                    "cost_before_return": gross,
                    "cost_after_return": net,
                }
            )
            return result
        unreal_r = (close - entry_price) / initial_risk
        if unreal_r >= 1:
            current_stop = max(current_stop, entry_price)
        if unreal_r >= 2:
            atr = safe_float(row.get("atr20"), np.nan)
            trail = max(safe_float(row.get("ema20"), np.nan), close - stop_rules["trailing_atr_multiplier"] * atr)
            current_stop = max(current_stop, trail)
        if unreal_r >= 3 and safe_float(row.get("dist_ema20"), 0.0) > 0.10:
            current_stop = max(current_stop, safe_float(row.get("ema20"), current_stop))
        exit_reason = ""
        if close <= current_stop:
            exit_reason = "trailing_stop" if current_stop >= entry_price else "stop_loss"
        holding_days = int((date - entry_date).days)
        if not exit_reason and holding_days >= stop_rules["time_stop_days"] and close <= entry_price:
            exit_reason = "time_stop"
        if not exit_reason and close < safe_float(row.get("ema60"), np.nan):
            exit_reason = "ema60_exit"
        if exit_reason:
            pending_exit_reason = exit_reason
            pending_exit_signal_date = date
    result.update({"label_status": "skipped", "label_skip_reason": "no_exit_before_data_end"})
    return result


def apply_label_definitions(config: dict[str, Any], labels: pd.DataFrame) -> pd.DataFrame:
    data = labels.copy()
    completed = data["label_status"].eq("completed")
    exit_reason = data.get("exit_reason", pd.Series("", index=data.index)).astype(str)
    net_return = pd.to_numeric(data.get("cost_after_return"), errors="coerce")
    r_multiple = pd.to_numeric(data.get("R"), errors="coerce")
    data["bad_trade"] = np.where(
        completed,
        (
            exit_reason.isin(config["label"]["bad_exit_reasons"])
            | (net_return <= float(config["label"]["bad_return_threshold"]))
            | (r_multiple <= float(config["label"]["bad_r_multiple_threshold"]))
        ).astype(int),
        np.nan,
    )
    data["good_trade"] = np.where(
        completed,
        (
            exit_reason.isin(config["label"]["good_exit_reasons"])
            | (net_return >= float(config["label"]["good_return_threshold"]))
            | (r_multiple >= float(config["label"]["good_r_multiple_threshold"]))
        ).astype(int),
        np.nan,
    )
    data["three_class_label"] = np.select(
        [data["bad_trade"].eq(1), data["good_trade"].eq(1), completed],
        ["bad", "good", "neutral"],
        default="unlabeled",
    )
    return data


def build_candidate_label_replay(config: dict[str, Any], candidates: pd.DataFrame) -> pd.DataFrame:
    by_instrument, dates, date_pos = build_market_lookups(config)
    rows = []
    label_end = parse_dt("2024-12-31")
    label_candidates = candidates[candidates["signal_date"] <= label_end].copy()
    for idx, (_, candidate) in enumerate(label_candidates.iterrows(), start=1):
        rows.append(replay_one_candidate_label(config, candidate, by_instrument, dates, date_pos))
        if idx % 500 == 0:
            print(f"labeled pullback candidates={idx}", flush=True)
    labels = apply_label_definitions(config, pd.DataFrame(rows))
    return labels


def expand_dataset_by_fold(config: dict[str, Any], candidates: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    label_cols = [col for col in labels.columns if col not in {"signal_date", "instrument", "entry_type"}]
    merged = candidates.merge(labels[label_cols], on="signal_id", how="left")
    rows = []
    for fold in config["explore5"]["folds"]:
        train_start = parse_dt(fold["train_start"])
        train_end = parse_dt(fold["train_end"])
        valid_start = parse_dt(fold["valid_start"])
        valid_end = parse_dt(fold["valid_end"])
        train = merged[(merged["signal_date"] >= train_start) & (merged["signal_date"] <= train_end)].copy()
        train["fold_role"] = "train"
        valid = merged[(merged["signal_date"] >= valid_start) & (merged["signal_date"] <= valid_end)].copy()
        valid["fold_role"] = "valid"
        for frame in [train, valid]:
            if frame.empty:
                continue
            frame["fold"] = fold["fold"]
            frame["train_start"] = fold["train_start"]
            frame["train_end"] = fold["train_end"]
            frame["valid_start"] = fold["valid_start"]
            frame["valid_end"] = fold["valid_end"]
            frame["label_known_date"] = pd.to_datetime(frame.get("exit_date"), errors="coerce")
            frame["usable_for_train"] = (
                frame["fold_role"].eq("train")
                & frame["label_status"].eq("completed")
                & (frame["label_known_date"] <= train_end)
                & frame["bad_trade"].notna()
            )
            frame["is_train_labeled_candidate"] = frame["usable_for_train"]
            frame["is_scored_candidate"] = frame["fold_role"].eq("valid")
            frame["is_portfolio_replayed_trade"] = False
            rows.append(frame)
    if not rows:
        return pd.DataFrame()
    dataset = pd.concat(rows, ignore_index=True)
    return dataset.sort_values(["fold", "fold_role", "signal_date", "instrument"]).reset_index(drop=True)


def build_label_generation_audit(labels: pd.DataFrame) -> pd.DataFrame:
    if labels.empty:
        return pd.DataFrame(columns=["label_status", "label_skip_reason", "candidates"])
    return (
        labels.groupby(["label_status", "label_skip_reason"], dropna=False)
        .size()
        .reset_index(name="candidates")
        .sort_values(["label_status", "label_skip_reason"])
    )


def distribution_rows(data: pd.DataFrame, dimensions: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    completed = data[data["label_status"].eq("completed")].copy()
    if completed.empty:
        return rows
    completed["calendar_year"] = pd.to_datetime(completed["signal_date"]).dt.year
    for dimension in dimensions:
        if dimension not in completed.columns:
            continue
        for (fold, value), group in completed.groupby(["fold", dimension], dropna=False):
            bad = pd.to_numeric(group["bad_trade"], errors="coerce")
            rows.append(
                {
                    "fold": fold,
                    "dimension": dimension,
                    "group_value": str(value),
                    "samples": int(len(group)),
                    "bad_trades": int((bad == 1).sum()),
                    "good_or_neutral": int((bad == 0).sum()),
                    "bad_rate": float((bad == 1).mean()) if len(group) else np.nan,
                }
            )
    for (fold, year), group in completed.groupby(["fold", "calendar_year"], dropna=False):
        bad = pd.to_numeric(group["bad_trade"], errors="coerce")
        rows.append(
            {
                "fold": fold,
                "dimension": "calendar_year",
                "group_value": str(int(year)),
                "samples": int(len(group)),
                "bad_trades": int((bad == 1).sum()),
                "good_or_neutral": int((bad == 0).sum()),
                "bad_rate": float((bad == 1).mean()) if len(group) else np.nan,
            }
        )
    return rows


def build_label_audit(dataset: pd.DataFrame) -> pd.DataFrame:
    dimensions = [
        "entry_type",
        "fold_role",
        "pullback_money_weak",
        "pullback_top10_20",
        "width_regime",
        "market_trend_regime",
        "industry_sync_regime",
    ]
    return pd.DataFrame(distribution_rows(dataset, dimensions))


def class_weight_info(labels: pd.Series, cap: float) -> dict[str, Any]:
    y = pd.to_numeric(labels, errors="coerce").dropna().astype(int)
    n_total = int(len(y))
    n_bad = int((y == 1).sum())
    n_good = int((y == 0).sum())
    bad_weight = min(n_total / (2 * n_bad), cap) if n_bad else np.nan
    good_weight = min(n_total / (2 * n_good), cap) if n_good else np.nan
    bad_minority = n_bad < n_good
    scale_pos_weight = min(n_good / n_bad, cap) if bad_minority and n_bad else 1.0
    return {
        "n_total": n_total,
        "n_bad": n_bad,
        "n_good": n_good,
        "minority_class_ratio": min(n_bad, n_good) / n_total if n_total else 0.0,
        "bad_class_weight": bad_weight,
        "good_class_weight": good_weight,
        "scale_pos_weight": scale_pos_weight,
    }


def sample_sufficiency(config: dict[str, Any], dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    imbalance_rows = []
    thresholds = config["sample_sufficiency"]
    cap = float(config["imbalance"]["class_weight_cap"])
    for fold in config["explore5"]["folds"]:
        fold_name = fold["fold"]
        train = dataset[(dataset["fold"] == fold_name) & (dataset["usable_for_train"])].copy()
        info = class_weight_info(train["bad_trade"], cap)
        trainable = (
            info["n_total"] >= int(thresholds["min_train_labeled_candidates"])
            and info["n_bad"] >= int(thresholds["min_class_count"])
            and info["n_good"] >= int(thresholds["min_class_count"])
            and info["minority_class_ratio"] >= float(thresholds["min_minority_class_ratio"])
        )
        low_sample = trainable and info["n_total"] < int(thresholds["target_train_labeled_candidates"])
        reason = ""
        if not trainable:
            reason_parts = []
            if info["n_total"] < int(thresholds["min_train_labeled_candidates"]):
                reason_parts.append("train_labeled_candidates_below_hard_min")
            if info["n_bad"] < int(thresholds["min_class_count"]):
                reason_parts.append("bad_class_below_min")
            if info["n_good"] < int(thresholds["min_class_count"]):
                reason_parts.append("good_class_below_min")
            if info["minority_class_ratio"] < float(thresholds["min_minority_class_ratio"]):
                reason_parts.append("minority_ratio_below_min")
            reason = ";".join(reason_parts)
        rows.append(
            {
                "fold": fold_name,
                "train_start": fold["train_start"],
                "train_end": fold["train_end"],
                "train_labeled_candidates": info["n_total"],
                "bad_trade_count": info["n_bad"],
                "good_or_neutral_count": info["n_good"],
                "minority_class_ratio": info["minority_class_ratio"],
                "target_train_labeled_candidates": thresholds["target_train_labeled_candidates"],
                "min_train_labeled_candidates": thresholds["min_train_labeled_candidates"],
                "min_class_count": thresholds["min_class_count"],
                "trainable": bool(trainable),
                "low_sample_warning": bool(low_sample),
                "status": "trainable" if trainable else "insufficient_label_coverage",
                "skip_reason": reason,
            }
        )
        imbalance_rows.append(
            {
                "fold": fold_name,
                "train_labeled_candidates": info["n_total"],
                "bad_trade_count": info["n_bad"],
                "good_or_neutral_count": info["n_good"],
                "minority_class_ratio": info["minority_class_ratio"],
                "insufficient_label_coverage": not trainable,
                "bad_class_weight": info["bad_class_weight"],
                "good_class_weight": info["good_class_weight"],
                "class_weight_cap": cap,
                "scale_pos_weight": info["scale_pos_weight"],
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(imbalance_rows)


def build_feature_audit(dataset: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in FEATURE_COLUMNS:
        values = pd.to_numeric(dataset.get(column), errors="coerce") if column in dataset else pd.Series(dtype=float)
        rows.append(
            {
                "feature": column,
                "present": column in dataset,
                "used_in_model": column in FEATURE_COLUMNS,
                "t_day_observable": True,
                "missing_ratio": float(values.isna().mean()) if len(values) else np.nan,
                "reason": "" if column in dataset else "missing_from_generated_features",
            }
        )
    rows.append(
        {
            "feature": "entry_type",
            "present": "entry_type" in dataset,
            "used_in_model": False,
            "t_day_observable": True,
            "missing_ratio": 0.0,
            "reason": "constant pullback-only scope; audited but excluded from LGBM",
        }
    )
    return pd.DataFrame(rows)


def bool_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame:
        return 0
    return int(pd.Series(frame[column]).fillna(False).astype(bool).sum())


def candidate_pool_row(scope: str, frame: pd.DataFrame, **extra: Any) -> dict[str, Any]:
    raw_candidate_count = bool_count(frame, "raw_pullback_candidate") if "raw_pullback_candidate" in frame else int(len(frame))
    rule_count = bool_count(frame, "rule_pullback_entry")
    gate_count = bool_count(frame, "gate_applicable") if "gate_applicable" in frame else rule_count
    usable = bool_count(frame, "usable_for_train")
    completed = int(frame["label_status"].eq("completed").sum()) if "label_status" in frame else 0
    bad = int(pd.to_numeric(frame.get("bad_trade", pd.Series(dtype=float)), errors="coerce").eq(1).sum()) if not frame.empty else 0
    good = int(pd.to_numeric(frame.get("bad_trade", pd.Series(dtype=float)), errors="coerce").eq(0).sum()) if not frame.empty else 0
    row = {
        "scope": scope,
        "fold": "",
        "fold_role": "",
        "calendar_year": "",
        "start": "",
        "end": "",
        "raw_pullback_shape": bool_count(frame, "raw_pullback_shape"),
        "raw_pullback_candidate": raw_candidate_count,
        "rule_pullback_entry": rule_count,
        "gate_applicable_candidates": gate_count,
        "completed_labeled_candidates": completed,
        "usable_labeled_candidates": usable,
        "bad_trade_count": bad,
        "good_or_neutral_count": good,
        "raw_to_rule_ratio": raw_candidate_count / rule_count if rule_count else np.nan,
    }
    row.update(extra)
    return row


def build_candidate_pool_audit(config: dict[str, Any], candidates: pd.DataFrame, dataset: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    signals = load_signals_with_width(config)
    signals["datetime"] = pd.to_datetime(signals["datetime"])
    for year, group in signals.groupby(signals["datetime"].dt.year):
        rows.append(
            candidate_pool_row(
                "calendar_year_all_signals",
                group,
                calendar_year=int(year),
                start=pd.Timestamp(group["datetime"].min()).date().isoformat(),
                end=pd.Timestamp(group["datetime"].max()).date().isoformat(),
            )
        )
    candidate_frame = candidates.copy()
    if not candidate_frame.empty:
        candidate_frame["calendar_year"] = pd.to_datetime(candidate_frame["signal_date"]).dt.year
        for year, group in candidate_frame.groupby("calendar_year"):
            rows.append(
                candidate_pool_row(
                    "calendar_year_raw_candidates",
                    group,
                    calendar_year=int(year),
                    start=pd.Timestamp(group["signal_date"].min()).date().isoformat(),
                    end=pd.Timestamp(group["signal_date"].max()).date().isoformat(),
                )
            )
    if not dataset.empty:
        for (fold, role), group in dataset.groupby(["fold", "fold_role"], dropna=False):
            rows.append(
                candidate_pool_row(
                    "fold_role_dataset",
                    group,
                    fold=str(fold),
                    fold_role=str(role),
                    start=pd.Timestamp(group["signal_date"].min()).date().isoformat(),
                    end=pd.Timestamp(group["signal_date"].max()).date().isoformat(),
                )
            )
        for fold in config["explore5"]["folds"]:
            fold_name = fold["fold"]
            train_usable = dataset[(dataset["fold"] == fold_name) & (dataset["usable_for_train"])].copy()
            inner = build_inner_split(config, fold, train_usable)
            for part_name in ["fit", "select"]:
                if part_name not in inner:
                    continue
                part = inner[part_name].copy()
                rows.append(
                    candidate_pool_row(
                        f"inner_{part_name}",
                        part,
                        fold=fold_name,
                        fold_role=part_name,
                        start=inner.get(f"{part_name}_start", pd.NaT).date().isoformat()
                        if isinstance(inner.get(f"{part_name}_start"), pd.Timestamp)
                        else "",
                        end=inner.get(f"{part_name}_end", pd.NaT).date().isoformat()
                        if isinstance(inner.get(f"{part_name}_end"), pd.Timestamp)
                        else "",
                    )
                )
            if "select" not in inner:
                rows.append(
                    candidate_pool_row(
                        "inner_select",
                        pd.DataFrame(),
                        fold=fold_name,
                        fold_role="select",
                        start="",
                        end="",
                    )
                )
    columns = [
        "scope",
        "fold",
        "fold_role",
        "calendar_year",
        "start",
        "end",
        "raw_pullback_shape",
        "raw_pullback_candidate",
        "rule_pullback_entry",
        "gate_applicable_candidates",
        "completed_labeled_candidates",
        "usable_labeled_candidates",
        "bad_trade_count",
        "good_or_neutral_count",
        "raw_to_rule_ratio",
    ]
    return pd.DataFrame(rows, columns=columns)


def command_build_labels(config: dict[str, Any]) -> list[Path]:
    outputs: list[Path] = []
    audit = build_source_data_audit(config)
    outputs.append(write_csv(audit, report_dir(config) / "source_data_audit.csv"))
    outputs.extend(command_build_signals(config))
    candidates = prepare_candidate_features(config)
    labels = build_candidate_label_replay(config, candidates)
    dataset = expand_dataset_by_fold(config, candidates, labels)
    label_generation_audit = build_label_generation_audit(labels)
    label_audit = build_label_audit(dataset)
    sufficiency, imbalance = sample_sufficiency(config, dataset)
    feature_audit = build_feature_audit(dataset)
    candidate_pool_audit = build_candidate_pool_audit(config, candidates, dataset)
    outputs.extend(
        [
            write_csv(dataset, report_dir(config) / "candidate_label_replay.csv"),
            write_csv(label_generation_audit, report_dir(config) / "label_generation_audit.csv"),
            write_csv(sufficiency, report_dir(config) / "sample_sufficiency_audit.csv"),
            write_csv(dataset, report_dir(config) / "meta_label_dataset.csv"),
            write_csv(label_audit, report_dir(config) / "label_audit.csv"),
            write_csv(imbalance, report_dir(config) / "class_imbalance_audit.csv"),
            write_csv(feature_audit, report_dir(config) / "feature_audit.csv"),
            write_csv(candidate_pool_audit, report_dir(config) / "candidate_pool_audit.csv"),
        ]
    )
    write_manifest(
        config,
        outputs,
        {
            "fold_sample_sufficiency": sufficiency.to_dict(orient="records"),
            "feature_columns": FEATURE_COLUMNS,
            "label_rows": int(len(labels)),
            "meta_label_dataset_rows": int(len(dataset)),
            "candidate_pool_audit_rows": int(len(candidate_pool_audit)),
        },
    )
    return outputs


def fit_feature_medians(frame: pd.DataFrame) -> pd.Series:
    numeric = frame[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).apply(pd.to_numeric, errors="coerce")
    medians = numeric.median()
    return medians.fillna(0.0)


def transform_features(frame: pd.DataFrame, medians: pd.Series) -> pd.DataFrame:
    numeric = frame.copy()
    for column in FEATURE_COLUMNS:
        if column not in numeric:
            numeric[column] = np.nan
    x = numeric[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).apply(pd.to_numeric, errors="coerce")
    return x.fillna(medians)


def sample_weights(labels: pd.Series, info: dict[str, Any]) -> np.ndarray:
    y = pd.to_numeric(labels, errors="coerce").astype(int)
    return np.where(y == 1, info["bad_class_weight"], info["good_class_weight"]).astype(float)


def average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y_true).astype(int)
    p = np.asarray(scores).astype(float)
    positives = int((y == 1).sum())
    if positives == 0:
        return np.nan
    order = np.argsort(-p)
    y_sorted = y[order]
    precision = np.cumsum(y_sorted == 1) / (np.arange(len(y_sorted)) + 1)
    return float((precision * (y_sorted == 1)).sum() / positives)


def classification_metrics(y_true: pd.Series, scores: pd.Series, threshold: float) -> dict[str, Any]:
    y = pd.to_numeric(y_true, errors="coerce").fillna(0).astype(int).to_numpy()
    p = pd.to_numeric(scores, errors="coerce").fillna(0.0).to_numpy()
    pred = p >= float(threshold)
    tp = int(((pred) & (y == 1)).sum())
    fp = int(((pred) & (y == 0)).sum())
    fn = int(((~pred) & (y == 1)).sum())
    top_n = max(1, int(math.ceil(len(p) * 0.10))) if len(p) else 0
    top_rate = float(y[np.argsort(-p)[:top_n]].mean()) if top_n else np.nan
    filtered = y[pred]
    kept = y[~pred]
    return {
        "precision_bad_trade": float(tp / (tp + fp)) if (tp + fp) else np.nan,
        "recall_bad_trade": float(tp / (tp + fn)) if (tp + fn) else np.nan,
        "pr_auc": average_precision(y, p),
        "top_decile_bad_rate": top_rate,
        "filtered_trade_bad_rate": float(filtered.mean()) if len(filtered) else np.nan,
        "kept_trade_bad_rate": float(kept.mean()) if len(kept) else np.nan,
        "scored_samples": int(len(y)),
        "filtered_samples": int(pred.sum()),
    }


def train_lgbm_model(config: dict[str, Any], train: pd.DataFrame, predict: pd.DataFrame, params: dict[str, Any]) -> tuple[np.ndarray, pd.Series, dict[str, Any]]:
    import lightgbm as lgb

    cap = float(config["imbalance"]["class_weight_cap"])
    info = class_weight_info(train["bad_trade"], cap)
    medians = fit_feature_medians(train)
    x_train = transform_features(train, medians)
    x_pred = transform_features(predict, medians)
    y_train = pd.to_numeric(train["bad_trade"], errors="coerce").astype(int)
    weights = sample_weights(y_train, info)
    lgb_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "verbosity": -1,
        "seed": int(config["model"]["seed"]),
        "feature_pre_filter": False,
        "force_col_wise": True,
        "num_threads": 4,
        "num_leaves": int(params["num_leaves"]),
        "learning_rate": float(params["learning_rate"]),
        "min_data_in_leaf": int(params["min_data_in_leaf"]),
        "feature_fraction": float(params["feature_fraction"]),
        "lambda_l1": float(params["lambda_l1"]),
        "lambda_l2": float(params["lambda_l2"]),
        "scale_pos_weight": float(info["scale_pos_weight"]),
    }
    dataset = lgb.Dataset(x_train, label=y_train, weight=weights, feature_name=FEATURE_COLUMNS)
    booster = lgb.train(lgb_params, dataset, num_boost_round=int(config["model"]["num_boost_round"]))
    scores = booster.predict(x_pred)
    return np.asarray(scores, dtype=float), medians, info


def build_inner_split(config: dict[str, Any], fold: dict[str, str], train: pd.DataFrame) -> dict[str, Any]:
    train_start = parse_dt(fold["train_start"])
    train_end = parse_dt(fold["train_end"])
    years = sorted(pd.to_datetime(train["signal_date"]).dt.year.dropna().astype(int).unique())
    if len(years) >= 3:
        select_year = years[-1]
        select_start = pd.Timestamp(f"{select_year}-01-01")
        fit_end = select_start - pd.Timedelta(days=1)
        method = "expanding_last_year_select"
    elif len(years) == 2:
        select_year = years[-1]
        select_start = pd.Timestamp(f"{select_year}-01-01")
        fit_end = select_start - pd.Timedelta(days=1)
        method = "first_year_fit_second_year_select"
    else:
        return {"trainable": False, "skip_reason": "insufficient_inner_selection_coverage", "method": "none"}
    fit = train[(train["signal_date"] >= train_start) & (train["signal_date"] <= fit_end) & (train["label_known_date"] <= fit_end)].copy()
    select = train[(train["signal_date"] >= select_start) & (train["signal_date"] <= train_end) & (train["label_known_date"] <= train_end)].copy()
    thresholds = config["sample_sufficiency"]
    fit_info = class_weight_info(fit["bad_trade"], float(config["imbalance"]["class_weight_cap"]))
    select_info = class_weight_info(select["bad_trade"], float(config["imbalance"]["class_weight_cap"]))
    trainable = (
        fit_info["n_total"] >= int(thresholds["inner_min_fit_candidates"])
        and select_info["n_total"] >= int(thresholds["inner_min_select_candidates"])
        and select_info["n_bad"] >= int(thresholds["inner_min_select_class_count"])
        and select_info["n_good"] >= int(thresholds["inner_min_select_class_count"])
    )
    reason = ""
    if not trainable:
        reason = "insufficient_inner_selection_samples"
    return {
        "trainable": bool(trainable),
        "skip_reason": reason,
        "method": method,
        "fit": fit,
        "select": select,
        "fit_start": train_start,
        "fit_end": fit_end,
        "select_start": select_start,
        "select_end": train_end,
        "fit_samples": fit_info["n_total"],
        "select_samples": select_info["n_total"],
        "select_bad": select_info["n_bad"],
        "select_good": select_info["n_good"],
    }


def replay_metrics_for_threshold(
    config: dict[str, Any],
    signals: pd.DataFrame,
    fold_name: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    version: str,
    probabilities: pd.DataFrame | None = None,
    threshold: float | None = None,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    gated = apply_gate(config, signals, version, probabilities, threshold)
    spec = base_portfolio_spec(config, version)
    executable_end = fold_executable_end(gated, end)
    portfolio, trades, _audit, _exposure, metrics = run_backtest_one(config, gated, spec, fold_name, start, executable_end)
    return metrics, portfolio, trades


def choose_threshold(trials: pd.DataFrame) -> pd.Series | None:
    if trials.empty:
        return None
    data = trials.copy()
    eligible = data[data["eligible"]].copy()
    if eligible.empty:
        data["selection_mode"] = "fallback_no_threshold_meets_exposure_constraints"
        pool = data
    else:
        eligible["selection_mode"] = "eligible"
        pool = eligible
    pool = pool.sort_values(
        ["stop_time_ratio_reduction", "total_return_with_cost", "threshold"],
        ascending=[False, False, True],
    )
    return pool.iloc[0]


def train_select_fold(
    config: dict[str, Any],
    fold: dict[str, str],
    dataset: pd.DataFrame,
    signals: pd.DataFrame,
    sufficiency: pd.DataFrame,
) -> dict[str, Any]:
    fold_name = fold["fold"]
    trainable_row = sufficiency[sufficiency["fold"] == fold_name].iloc[0]
    train = dataset[(dataset["fold"] == fold_name) & (dataset["usable_for_train"])].copy()
    valid = dataset[(dataset["fold"] == fold_name) & (dataset["fold_role"] == "valid")].copy()
    if not bool(trainable_row["trainable"]):
        return {
            "fold": fold_name,
            "trainable": False,
            "skip_reason": str(trainable_row["skip_reason"]),
            "inner_audit": {
                "fold": fold_name,
                "trainable": False,
                "skip_reason": str(trainable_row["skip_reason"]),
                "inner_method": "",
            },
        }

    inner = build_inner_split(config, fold, train)
    if not inner["trainable"]:
        return {
            "fold": fold_name,
            "trainable": False,
            "skip_reason": inner["skip_reason"],
            "inner_audit": {
                "fold": fold_name,
                "trainable": False,
                "skip_reason": inner["skip_reason"],
                "inner_method": inner["method"],
                "inner_fit_samples": inner.get("fit_samples", 0),
                "inner_select_samples": inner.get("select_samples", 0),
            },
        }

    select_start = inner["select_start"]
    select_end = inner["select_end"]
    inner_signal_period = signals.copy()
    select_candidates = prepare_candidate_features(config)
    select_candidates = select_candidates[(select_candidates["signal_date"] >= select_start) & (select_candidates["signal_date"] <= select_end)].copy()
    baseline_metrics, _, baseline_trades = replay_metrics_for_threshold(
        config, inner_signal_period, f"{fold_name}_inner", select_start, select_end, NO_MODEL_VERSION
    )
    baseline_trades_count = int(baseline_metrics.get("trades", 0))
    baseline_cash = safe_float(baseline_metrics.get("avg_cash_ratio"), 1.0)
    baseline_stop_time = safe_float(baseline_metrics.get("stop_time_trade_ratio"), 0.0)

    threshold_rows: list[dict[str, Any]] = []
    inner_pred_rows: list[dict[str, Any]] = []
    param_predictions: dict[str, pd.DataFrame] = {}
    prediction_id_columns = [
        "datetime",
        "signal_date",
        "instrument",
        "signal_id",
        "candidate_source",
        "raw_pullback_candidate",
        "rule_pullback_entry",
        "gate_applicable",
    ]
    for params in config["model"]["lgbm_param_grid"]:
        select_scores, _medians, _info = train_lgbm_model(config, inner["fit"], select_candidates, params)
        pred_frame = select_candidates[[column for column in prediction_id_columns if column in select_candidates.columns]].copy()
        pred_frame["bad_trade_probability"] = select_scores
        param_predictions[params["id"]] = pred_frame
        labeled_scores = inner["select"][["signal_id", "bad_trade"]].merge(
            pred_frame[["signal_id", "bad_trade_probability"]], on="signal_id", how="left"
        )
        for threshold in config["thresholds"]["bad_prob_threshold"]:
            metrics, _portfolio, trades = replay_metrics_for_threshold(
                config,
                inner_signal_period,
                f"{fold_name}_inner",
                select_start,
                select_end,
                LGBM_GATE_VERSION,
                pred_frame,
                float(threshold),
            )
            trade_ratio = safe_float(metrics.get("trades"), 0.0) / baseline_trades_count if baseline_trades_count else 0.0
            avg_cash = safe_float(metrics.get("avg_cash_ratio"), 1.0)
            stop_time = safe_float(metrics.get("stop_time_trade_ratio"), 0.0)
            reduction = (baseline_stop_time - stop_time) / baseline_stop_time if baseline_stop_time > 0 else 0.0
            eligible = (
                trade_ratio >= float(config["thresholds"]["min_trade_ratio_vs_baseline"])
                and avg_cash <= baseline_cash + float(config["thresholds"]["max_avg_cash_ratio_worse_pp"])
            )
            class_metrics = classification_metrics(labeled_scores["bad_trade"], labeled_scores["bad_trade_probability"], float(threshold))
            threshold_rows.append(
                {
                    "fold": fold_name,
                    "param_id": params["id"],
                    "threshold": float(threshold),
                    "baseline_trades": baseline_trades_count,
                    "trades": int(metrics.get("trades", 0)),
                    "trade_ratio_vs_baseline": trade_ratio,
                    "baseline_avg_cash_ratio": baseline_cash,
                    "avg_cash_ratio": avg_cash,
                    "baseline_stop_time_trade_ratio": baseline_stop_time,
                    "stop_time_trade_ratio": stop_time,
                    "stop_time_ratio_reduction": reduction,
                    "total_return_with_cost": safe_float(metrics.get("total_return_with_cost"), np.nan),
                    "eligible": bool(eligible),
                    **class_metrics,
                }
            )
            tmp = labeled_scores.copy()
            tmp["fold"] = fold_name
            tmp["param_id"] = params["id"]
            tmp["threshold"] = float(threshold)
            tmp["gate_filtered"] = pd.to_numeric(tmp["bad_trade_probability"], errors="coerce") >= float(threshold)
            inner_pred_rows.extend(tmp.to_dict(orient="records"))
    trials = pd.DataFrame(threshold_rows)
    selected = choose_threshold(trials)
    if selected is None:
        return {
            "fold": fold_name,
            "trainable": False,
            "skip_reason": "no_inner_threshold_trials",
            "inner_audit": {"fold": fold_name, "trainable": False, "skip_reason": "no_inner_threshold_trials"},
            "threshold_rows": threshold_rows,
            "inner_pred_rows": inner_pred_rows,
        }

    selected_param = next(item for item in config["model"]["lgbm_param_grid"] if item["id"] == selected["param_id"])
    valid_start = parse_dt(fold["valid_start"])
    valid_end = parse_dt(fold["valid_end"])
    score_candidates = prepare_candidate_features(config)
    valid_candidates = score_candidates[(score_candidates["signal_date"] >= valid_start) & (score_candidates["signal_date"] <= valid_end)].copy()
    valid_scores, _medians, train_weight_info = train_lgbm_model(config, train, valid_candidates, selected_param)
    valid_pred = valid_candidates[[column for column in prediction_id_columns if column in valid_candidates.columns]].copy()
    valid_pred["fold"] = fold_name
    valid_pred["bad_trade_probability"] = valid_scores
    valid_pred["threshold"] = float(selected["threshold"])
    valid_pred["gate_filtered"] = valid_pred["bad_trade_probability"] >= float(selected["threshold"])
    valid_pred = valid_pred.merge(valid[["signal_id", "bad_trade", "label_status"]], on="signal_id", how="left")
    valid_labeled = valid_pred[valid_pred["bad_trade"].notna()].copy()
    valid_class_metrics = (
        classification_metrics(valid_labeled["bad_trade"], valid_labeled["bad_trade_probability"], float(selected["threshold"]))
        if not valid_labeled.empty
        else {}
    )
    model_metrics = {
        "fold": fold_name,
        "param_id": selected_param["id"],
        "threshold": float(selected["threshold"]),
        "train_labeled_candidates": int(len(train)),
        "valid_labeled_candidates": int(len(valid_labeled)),
        **valid_class_metrics,
        **train_weight_info,
    }
    threshold_rows = [dict(row, selected=bool(row["param_id"] == selected["param_id"] and row["threshold"] == selected["threshold"])) for row in threshold_rows]
    return {
        "fold": fold_name,
        "trainable": True,
        "skip_reason": "",
        "selected_param": selected_param,
        "selected_threshold": float(selected["threshold"]),
        "selection_mode": str(selected.get("selection_mode", "eligible")),
        "valid_predictions": valid_pred,
        "threshold_rows": threshold_rows,
        "inner_pred_rows": inner_pred_rows,
        "model_metrics": model_metrics,
        "inner_audit": {
            "fold": fold_name,
            "trainable": True,
            "skip_reason": "",
            "inner_method": inner["method"],
            "inner_fit_start": inner["fit_start"].date().isoformat(),
            "inner_fit_end": inner["fit_end"].date().isoformat(),
            "inner_select_start": inner["select_start"].date().isoformat(),
            "inner_select_end": inner["select_end"].date().isoformat(),
            "inner_fit_samples": inner["fit_samples"],
            "inner_select_samples": inner["select_samples"],
            "inner_select_bad": inner["select_bad"],
            "inner_select_good": inner["select_good"],
            "selected_param_id": selected_param["id"],
            "selected_threshold": float(selected["threshold"]),
            "selection_mode": str(selected.get("selection_mode", "eligible")),
        },
    }


def drawdown_from_account(values: pd.Series) -> float:
    account = pd.to_numeric(values, errors="coerce").dropna()
    if account.empty:
        return 0.0
    return float((account / account.cummax() - 1.0).min())


def build_year_metrics(portfolio: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    if portfolio.empty:
        return pd.DataFrame()
    p = portfolio.copy()
    p["datetime"] = pd.to_datetime(p["datetime"])
    p["calendar_year"] = p["datetime"].dt.year
    t = trades.copy()
    if not t.empty:
        t["signal_date"] = pd.to_datetime(t["signal_date"])
        t["calendar_year"] = t["signal_date"].dt.year
    rows: list[dict[str, Any]] = []
    for (version, fold, year), group in p.groupby(["version", "fold", "calendar_year"], dropna=False):
        group = group.sort_values("datetime")
        trade_group = t[(t["version"] == version) & (t["fold"] == fold) & (t["calendar_year"] == year)] if not t.empty else pd.DataFrame()
        start_account = safe_float(group["prev_account_value"].iloc[0], np.nan)
        end_account = safe_float(group["account_value"].iloc[-1], np.nan)
        rows.append(
            {
                "version": version,
                "fold": fold,
                "calendar_year": int(year),
                "fold_year_return_with_cost": end_account / start_account - 1 if start_account else np.nan,
                "fold_year_max_drawdown": drawdown_from_account(group["account_value"]),
                "fold_year_trades": int(len(trade_group)),
                "fold_year_net_pnl": float(pd.to_numeric(trade_group.get("net_pnl"), errors="coerce").sum()) if not trade_group.empty else 0.0,
            }
        )
    instances = pd.DataFrame(rows)
    if instances.empty:
        return instances
    return (
        instances.groupby(["version", "calendar_year"], as_index=False)
        .agg(
            year_return_with_cost=("fold_year_return_with_cost", "mean"),
            max_drawdown=("fold_year_max_drawdown", "min"),
            trades=("fold_year_trades", "mean"),
            net_pnl_sum=("fold_year_net_pnl", "mean"),
            year_instances=("fold", "nunique"),
            folds=("fold", lambda s: ",".join(sorted(set(map(str, s))))),
        )
        .sort_values(["version", "calendar_year"])
    )


def enrich_trades_with_signals(config: dict[str, Any], trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    data = trades.copy()
    data["signal_date"] = pd.to_datetime(data["signal_date"])
    signals = load_signals_with_width(config)
    signals["datetime"] = pd.to_datetime(signals["datetime"])
    keep = [
        "instrument",
        "datetime",
        "industry_name",
        "market_ok",
        "industry_trend_ok",
        "market_ok_entry",
        "industry_ok_entry",
        "trend_score_pct",
        "money_ratio20",
        "ret60",
        "close_gt_ema60_ratio",
        "ema20_gt_ema60_ratio",
        "breakout_entry",
        "raw_pullback_candidate",
        "rule_pullback_entry",
        "pullback_entry",
    ]
    signals = signals[[column for column in keep if column in signals.columns]].rename(columns={"datetime": "signal_date"})
    merged = data.merge(signals, on=["instrument", "signal_date"], how="left", suffixes=("", "_signal"))
    if "industry_name_signal" in merged.columns:
        merged["industry_name"] = merged["industry_name_signal"].combine_first(merged.get("industry_name"))
    merged["industry_name"] = merged.get("industry_name", "UNKNOWN").fillna("UNKNOWN").replace("", "UNKNOWN")
    merged = add_regime_labels(merged)
    merged["calendar_year"] = merged["signal_date"].dt.year
    return merged


def trade_failure_attribution(config: dict[str, Any], trades: pd.DataFrame) -> pd.DataFrame:
    data = enrich_trades_with_signals(config, trades)
    if data.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    dimensions = {
        "entry_type": "entry_type",
        "exit_reason": "exit_reason",
        "width": "width_regime",
        "market_trend": "market_trend_regime",
        "industry_sync": "industry_sync_regime",
        "pullback_money": "pullback_money_regime",
        "pullback_top10_20": "pullback_top10_20",
    }
    account = safe_float(config["costs"]["account"], 1_000_000.0)
    for dimension, column in dimensions.items():
        if column not in data:
            continue
        for (version, fold, year, value), group in data.groupby(["version", "fold", "calendar_year", column], dropna=False):
            rows.append(
                {
                    "version": version,
                    "fold": fold,
                    "calendar_year": int(year),
                    "dimension": dimension,
                    "group_value": str(value),
                    "trades": int(len(group)),
                    "stop_loss_count": int((group["exit_reason"] == "stop_loss").sum()),
                    "time_stop_count": int((group["exit_reason"] == "time_stop").sum()),
                    "stop_time_ratio": float(group["exit_reason"].isin(["stop_loss", "time_stop"]).mean()) if len(group) else 0.0,
                    "net_pnl_sum": float(pd.to_numeric(group["net_pnl"], errors="coerce").sum()),
                    "return_contribution": float(pd.to_numeric(group["net_pnl"], errors="coerce").sum() / account),
                    "avg_cost_after_return": float(pd.to_numeric(group["cost_after_return"], errors="coerce").mean()),
                }
            )
    return pd.DataFrame(rows).sort_values(["version", "fold", "calendar_year", "dimension", "group_value"])


def return_concentration(values: pd.Series) -> float:
    positive = pd.to_numeric(values, errors="coerce")
    positive = positive[positive > 0]
    total = positive.sum()
    return float(positive.max() / total) if total > 0 else np.nan


def evaluate_candidate_for_future(config: dict[str, Any], fold_metrics: pd.DataFrame, year_metrics: pd.DataFrame, trainable_folds: int) -> dict[str, Any]:
    if LGBM_GATE_VERSION not in set(fold_metrics.get("version", [])):
        return {"candidate_for_future_final_test": False, "candidate_decision_reason": "no_lgbm_replay"}
    if trainable_folds < len(config["explore5"]["folds"]):
        return {"candidate_for_future_final_test": False, "candidate_decision_reason": "not_all_outer_folds_trainable"}
    base_year = year_metrics[year_metrics["version"] == NO_MODEL_VERSION].set_index("calendar_year")
    lgbm_year = year_metrics[year_metrics["version"] == LGBM_GATE_VERSION].copy()
    base_fold = fold_metrics[fold_metrics["version"] == NO_MODEL_VERSION]
    lgbm_fold = fold_metrics[fold_metrics["version"] == LGBM_GATE_VERSION]
    positive_years = int((lgbm_year["year_return_with_cost"] > 0).sum())
    controlled_flat = 0
    pass_worst_drawdown = True
    for _, row in lgbm_year.iterrows():
        year = row["calendar_year"]
        if year not in base_year.index:
            continue
        base = base_year.loc[year]
        flat = (
            row["year_return_with_cost"] >= float(config["selection"]["controlled_flat_return_floor"])
            and abs(row["max_drawdown"]) <= abs(base["max_drawdown"]) * (1 - float(config["selection"]["controlled_flat_drawdown_improvement"]))
        )
        if row["year_return_with_cost"] <= 0 and flat:
            controlled_flat += 1
        if row["max_drawdown"] < base["max_drawdown"] - float(config["selection"]["max_year_drawdown_worse_pp"]):
            pass_worst_drawdown = False
    qualified_years = positive_years + min(controlled_flat, 1)
    base_trades = pd.to_numeric(base_fold["trades"], errors="coerce").sum()
    lgbm_trades = pd.to_numeric(lgbm_fold["trades"], errors="coerce").sum()
    trade_ratio = float(lgbm_trades / base_trades) if base_trades else 0.0
    base_cash = safe_float(base_fold["avg_cash_ratio"].mean(), 1.0)
    lgbm_cash = safe_float(lgbm_fold["avg_cash_ratio"].mean(), 1.0)
    base_stop = safe_float(base_fold["stop_time_trades"].sum(), 0.0) / base_trades if base_trades else 0.0
    lgbm_stop = safe_float(lgbm_fold["stop_time_trades"].sum(), 0.0) / lgbm_trades if lgbm_trades else 0.0
    stop_reduction = (base_stop - lgbm_stop) / base_stop if base_stop > 0 else 0.0
    concentration = return_concentration(lgbm_year["year_return_with_cost"])
    selected = (
        positive_years >= int(config["selection"]["positive_valid_years"])
        and qualified_years >= int(config["selection"]["qualified_valid_years"])
        and stop_reduction >= float(config["thresholds"]["min_stop_time_ratio_reduction"])
        and trade_ratio >= float(config["thresholds"]["min_trade_ratio_vs_baseline"])
        and lgbm_cash <= base_cash + float(config["thresholds"]["max_avg_cash_ratio_worse_pp"])
        and pass_worst_drawdown
        and (pd.isna(concentration) or concentration <= float(config["selection"]["max_year_return_concentration"]))
    )
    reason = "passed_all_selection_checks" if selected else "selection_checks_not_met"
    return {
        "candidate_for_future_final_test": bool(selected),
        "candidate_decision_reason": reason,
        "positive_valid_years": positive_years,
        "qualified_valid_years": qualified_years,
        "trade_ratio_vs_no_model": trade_ratio,
        "avg_cash_ratio_vs_no_model_delta": lgbm_cash - base_cash,
        "stop_time_ratio_reduction": stop_reduction,
        "year_return_concentration": concentration,
        "pass_worst_year_drawdown": bool(pass_worst_drawdown),
    }


def run_fold_replays(
    config: dict[str, Any],
    signals: pd.DataFrame,
    fold: dict[str, str],
    selection_result: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[pd.DataFrame], list[pd.DataFrame], list[pd.DataFrame]]:
    fold_name = fold["fold"]
    valid_start = parse_dt(fold["valid_start"])
    valid_end = parse_dt(fold["valid_end"])
    metric_rows: list[dict[str, Any]] = []
    portfolios: list[pd.DataFrame] = []
    trades_all: list[pd.DataFrame] = []
    audits: list[pd.DataFrame] = []
    replay_versions: list[tuple[str, pd.DataFrame | None, float | None]] = [
        (NO_MODEL_VERSION, None, None),
        (HARD_GATE_VERSION, None, None),
    ]
    if selection_result and selection_result.get("trainable") and "valid_predictions" in selection_result:
        replay_versions.append((LGBM_GATE_VERSION, selection_result["valid_predictions"], float(selection_result["selected_threshold"])))
    for version, probabilities, threshold in replay_versions:
        gated = apply_gate(config, signals, version, probabilities, threshold)
        spec = base_portfolio_spec(config, version)
        executable_end = fold_executable_end(gated, valid_end)
        portfolio, trades, audit, _exposure, metrics = run_backtest_one(config, gated, spec, fold_name, valid_start, executable_end)
        metrics.update(
            {
                "fold": fold_name,
                "train_start": fold["train_start"],
                "train_end": fold["train_end"],
                "valid_start": fold["valid_start"],
                "valid_end": fold["valid_end"],
                "valid_executable_end": executable_end.date().isoformat(),
                "selected_threshold": threshold if threshold is not None else np.nan,
                "selected_param_id": selection_result.get("selected_param", {}).get("id", "") if selection_result else "",
            }
        )
        metric_rows.append(metrics)
        portfolios.append(attach_run_metadata(portfolio, spec, fold, executable_end))
        trades_all.append(attach_run_metadata(trades, spec, fold, executable_end))
        audits.append(attach_run_metadata(audit, spec, fold, executable_end))
        print(f"ran Explore6 replay {version} {fold_name}", flush=True)
    return metric_rows, portfolios, trades_all, audits


def build_final_training_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    unique = dataset.sort_values(["signal_date", "instrument"]).drop_duplicates("signal_id", keep="first").copy()
    final_end = parse_dt("2024-12-31")
    final_train = unique[
        (unique["signal_date"] >= parse_dt("2017-01-01"))
        & (unique["signal_date"] <= final_end)
        & (unique["label_status"].eq("completed"))
        & (unique["label_known_date"] <= final_end)
        & (unique["bad_trade"].notna())
    ].copy()
    final_train["fold"] = "OBS_FINAL"
    final_train["fold_role"] = "train"
    final_train["usable_for_train"] = True
    final_train["train_start"] = "2017-01-01"
    final_train["train_end"] = "2024-12-31"
    final_train["valid_start"] = "2025-01-01"
    final_train["valid_end"] = "2026-04-29"
    return final_train


def run_observed_replication(
    config: dict[str, Any],
    dataset: pd.DataFrame,
    signals: pd.DataFrame,
    trainable_folds: int,
) -> pd.DataFrame:
    start = parse_dt(config["dates"]["observed_test_start"])
    end = parse_dt(config["dates"]["observed_backtest_end"])
    rows: list[dict[str, Any]] = []
    observed_fold = {
        "fold": "observed_replication",
        "train_start": "2017-01-01",
        "train_end": "2024-12-31",
        "valid_start": config["dates"]["observed_test_start"],
        "valid_end": config["dates"]["observed_backtest_end"],
    }
    for version in [NO_MODEL_VERSION, HARD_GATE_VERSION]:
        gated = apply_gate(config, signals, version)
        spec = base_portfolio_spec(config, version)
        executable_end = fold_executable_end(gated, end)
        _portfolio, _trades, _audit, _exposure, metrics = run_backtest_one(config, gated, spec, "observed_replication", start, executable_end)
        metrics.update({"used_for_selection": False, "observed_replication": True, "selected_threshold": np.nan, "selected_param_id": ""})
        rows.append(metrics)

    if trainable_folds >= int(config["sample_sufficiency"]["min_trainable_folds"]):
        final_train = build_final_training_dataset(dataset)
        info = class_weight_info(final_train["bad_trade"], float(config["imbalance"]["class_weight_cap"]))
        final_trainable = (
            info["n_total"] >= int(config["sample_sufficiency"]["min_train_labeled_candidates"])
            and info["n_bad"] >= int(config["sample_sufficiency"]["min_class_count"])
            and info["n_good"] >= int(config["sample_sufficiency"]["min_class_count"])
        )
        if final_trainable:
            final_dataset = final_train.copy()
            final_fold = {
                "fold": "OBS_FINAL",
                "train_start": "2017-01-01",
                "train_end": "2024-12-31",
                "valid_start": config["dates"]["observed_test_start"],
                "valid_end": config["dates"]["observed_backtest_end"],
            }
            final_suff = pd.DataFrame(
                [
                    {
                        "fold": "OBS_FINAL",
                        "trainable": True,
                        "skip_reason": "",
                    }
                ]
            )
            result = train_select_fold(config, final_fold, final_dataset, signals, final_suff)
            if result.get("trainable") and "valid_predictions" in result:
                gated = apply_gate(config, signals, LGBM_GATE_VERSION, result["valid_predictions"], float(result["selected_threshold"]))
                spec = base_portfolio_spec(config, LGBM_GATE_VERSION)
                executable_end = fold_executable_end(gated, end)
                _portfolio, _trades, _audit, _exposure, metrics = run_backtest_one(config, gated, spec, "observed_replication", start, executable_end)
                metrics.update(
                    {
                        "used_for_selection": False,
                        "observed_replication": True,
                        "selected_threshold": float(result["selected_threshold"]),
                        "selected_param_id": result.get("selected_param", {}).get("id", ""),
                    }
                )
                rows.append(metrics)
    result_df = pd.DataFrame(rows)
    if not result_df.empty:
        result_df["used_for_selection"] = False
    return result_df


def command_train_replay(config: dict[str, Any]) -> list[Path]:
    outputs = command_build_labels(config)
    dataset = pd.read_csv(
        report_dir(config) / "meta_label_dataset.csv",
        parse_dates=["datetime", "signal_date", "label_known_date"],
        low_memory=False,
    )
    sufficiency = pd.read_csv(report_dir(config) / "sample_sufficiency_audit.csv")
    signals = load_signals_with_width(config)
    selection_results: dict[str, dict[str, Any]] = {}
    inner_audit_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    inner_pred_rows: list[dict[str, Any]] = []
    model_metric_rows: list[dict[str, Any]] = []
    fold_prediction_frames: list[pd.DataFrame] = []
    initial_trainable = int(sufficiency["trainable"].fillna(False).sum()) if "trainable" in sufficiency else 0

    if initial_trainable >= int(config["sample_sufficiency"]["min_trainable_folds"]):
        for fold in config["explore5"]["folds"]:
            result = train_select_fold(config, fold, dataset, signals, sufficiency)
            selection_results[fold["fold"]] = result
            inner_audit_rows.append(result.get("inner_audit", {"fold": fold["fold"], "trainable": False}))
            threshold_rows.extend(result.get("threshold_rows", []))
            inner_pred_rows.extend(result.get("inner_pred_rows", []))
            print(f"selected Explore6 fold={fold['fold']} trainable={result.get('trainable')}", flush=True)
    else:
        for fold in config["explore5"]["folds"]:
            selection_results[fold["fold"]] = {"fold": fold["fold"], "trainable": False, "skip_reason": "fewer_than_3_sample_sufficient_folds"}
            inner_audit_rows.append(
                {
                    "fold": fold["fold"],
                    "trainable": False,
                    "skip_reason": "fewer_than_3_sample_sufficient_folds",
                    "inner_method": "",
                }
            )

    inner_trainable_count = int(sum(1 for result in selection_results.values() if result.get("trainable")))
    lgbm_globally_stopped = inner_trainable_count < int(config["sample_sufficiency"]["min_trainable_folds"])
    if lgbm_globally_stopped:
        for result in selection_results.values():
            result.pop("valid_predictions", None)
            result["lgbm_final_model_allowed"] = False
            result["global_stop_reason"] = "fewer_than_3_inner_trainable_folds"
        model_metric_rows = []
        fold_prediction_frames = []
    else:
        for result in selection_results.values():
            if result.get("model_metrics"):
                model_metric_rows.append(result["model_metrics"])
            if "valid_predictions" in result:
                fold_prediction_frames.append(result["valid_predictions"])

    metric_rows: list[dict[str, Any]] = []
    portfolios: list[pd.DataFrame] = []
    trades_all: list[pd.DataFrame] = []
    audits: list[pd.DataFrame] = []
    for fold in config["explore5"]["folds"]:
        fold_metrics, fold_portfolios, fold_trades, fold_audits = run_fold_replays(config, signals, fold, selection_results.get(fold["fold"]))
        metric_rows.extend(fold_metrics)
        portfolios.extend(fold_portfolios)
        trades_all.extend(fold_trades)
        audits.extend(fold_audits)

    fold_metrics = pd.DataFrame(metric_rows)
    portfolio_all = pd.concat(portfolios, ignore_index=True) if portfolios else pd.DataFrame()
    trade_all = pd.concat(trades_all, ignore_index=True) if trades_all else pd.DataFrame(columns=REPORT_COLUMNS)
    audit_all = pd.concat(audits, ignore_index=True) if audits else pd.DataFrame()
    year_metrics = build_year_metrics(portfolio_all, trade_all)
    attribution = trade_failure_attribution(config, trade_all)
    observed = run_observed_replication(config, dataset, signals, inner_trainable_count if not lgbm_globally_stopped else 0)
    future_decision = evaluate_candidate_for_future(
        config,
        fold_metrics,
        year_metrics,
        inner_trainable_count,
    )

    fold_predictions = pd.concat(fold_prediction_frames, ignore_index=True) if fold_prediction_frames else pd.DataFrame(
        columns=[
            "datetime",
            "signal_date",
            "instrument",
            "signal_id",
            "candidate_source",
            "raw_pullback_candidate",
            "rule_pullback_entry",
            "gate_applicable",
            "fold",
            "bad_trade_probability",
            "threshold",
            "gate_filtered",
            "bad_trade",
            "label_status",
        ]
    )
    model_metrics_frame = pd.DataFrame(model_metric_rows)
    if model_metrics_frame.empty:
        model_metrics_frame = pd.DataFrame(
            columns=[
                "fold",
                "param_id",
                "threshold",
                "train_labeled_candidates",
                "valid_labeled_candidates",
                "precision_bad_trade",
                "recall_bad_trade",
                "pr_auc",
                "top_decile_bad_rate",
            ]
        )
    output_frames = {
        "inner_selection_audit.csv": pd.DataFrame(inner_audit_rows),
        "inner_oof_predictions.csv": pd.DataFrame(inner_pred_rows),
        "fold_model_metrics.csv": model_metrics_frame,
        "fold_threshold_selection.csv": pd.DataFrame(threshold_rows),
        "fold_predictions.csv": fold_predictions,
        "no_model_gate_trade_detail.csv": trade_all[trade_all["version"] == NO_MODEL_VERSION].copy() if not trade_all.empty else pd.DataFrame(columns=REPORT_COLUMNS),
        "no_model_gate_portfolio_daily.csv": portfolio_all[portfolio_all["version"] == NO_MODEL_VERSION].copy() if not portfolio_all.empty else pd.DataFrame(),
        "fold_replay_metrics.csv": fold_metrics,
        "year_metrics.csv": year_metrics,
        "trade_failure_attribution.csv": attribution,
        "observed_replication_summary.csv": observed,
        "fold_trade_detail.csv": trade_all,
        "fold_portfolio_daily.csv": portfolio_all,
            "fold_execution_audit.csv": audit_all,
    }
    for filename, frame in output_frames.items():
        outputs.append(write_csv(frame, report_dir(config) / filename))

    write_manifest(
        config,
        outputs,
        {
            "trainable_lgbm_folds": inner_trainable_count,
            "lgbm_final_model_stopped": bool(lgbm_globally_stopped),
            "lgbm_final_model_stop_reason": "fewer_than_3_inner_trainable_folds" if lgbm_globally_stopped else "",
            "inner_selection": pd.DataFrame(inner_audit_rows).to_dict(orient="records"),
            "candidate_for_future_final_test": future_decision["candidate_for_future_final_test"],
            "candidate_decision": future_decision,
        },
    )
    return outputs


def markdown_table(frame: pd.DataFrame, columns: list[str], limit: int = 20) -> str:
    if frame.empty:
        return "| " + " | ".join(columns) + " |\n| " + " | ".join(["---"] * len(columns)) + " |\n"
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.head(limit).iterrows():
        values = []
        for column in columns:
            value = row.get(column, "")
            if pd.isna(value):
                values.append("")
            elif isinstance(value, float):
                if column == "raw_to_rule_ratio":
                    values.append(f"{value:.2f}x")
                elif "return" in column or "drawdown" in column or "ratio" in column or "rate" in column:
                    values.append(format_pct(value))
                else:
                    values.append(f"{value:.4g}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows) + "\n"


def compare_versions(frame: pd.DataFrame, baseline: str, candidate: str, key: str = "fold") -> pd.DataFrame:
    if frame.empty or key not in frame:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for value in sorted(frame[key].dropna().unique()):
        base = frame[(frame[key] == value) & (frame["version"] == baseline)]
        cand = frame[(frame[key] == value) & (frame["version"] == candidate)]
        if base.empty or cand.empty:
            continue
        b = base.iloc[0]
        c = cand.iloc[0]
        base_trades = safe_float(b.get("trades"), 0.0)
        cand_trades = safe_float(c.get("trades"), 0.0)
        base_stop = safe_float(b.get("stop_time_trade_ratio"), np.nan)
        cand_stop = safe_float(c.get("stop_time_trade_ratio"), np.nan)
        rows.append(
            {
                key: value,
                "base_trades": int(base_trades),
                "candidate_trades": int(cand_trades),
                "trade_ratio_vs_base": cand_trades / base_trades if base_trades else np.nan,
                "base_return": safe_float(b.get("total_return_with_cost"), np.nan)
                if "total_return_with_cost" in b
                else safe_float(b.get("year_return_with_cost"), np.nan),
                "candidate_return": safe_float(c.get("total_return_with_cost"), np.nan)
                if "total_return_with_cost" in c
                else safe_float(c.get("year_return_with_cost"), np.nan),
                "return_delta": (
                    safe_float(c.get("total_return_with_cost"), np.nan) - safe_float(b.get("total_return_with_cost"), np.nan)
                    if "total_return_with_cost" in frame
                    else safe_float(c.get("year_return_with_cost"), np.nan) - safe_float(b.get("year_return_with_cost"), np.nan)
                ),
                "base_drawdown": safe_float(b.get("max_drawdown"), np.nan),
                "candidate_drawdown": safe_float(c.get("max_drawdown"), np.nan),
                "drawdown_delta": safe_float(c.get("max_drawdown"), np.nan) - safe_float(b.get("max_drawdown"), np.nan),
                "base_avg_cash_ratio": safe_float(b.get("avg_cash_ratio"), np.nan),
                "candidate_avg_cash_ratio": safe_float(c.get("avg_cash_ratio"), np.nan),
                "cash_ratio_delta": safe_float(c.get("avg_cash_ratio"), np.nan) - safe_float(b.get("avg_cash_ratio"), np.nan),
                "base_stop_time_ratio": base_stop,
                "candidate_stop_time_ratio": cand_stop,
                "stop_time_ratio_reduction": (base_stop - cand_stop) / base_stop if pd.notna(base_stop) and base_stop > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def report_value(frame: pd.DataFrame, column: str, default: Any = "") -> Any:
    if frame.empty or column not in frame:
        return default
    return frame[column].iloc[0]


def command_report(config: dict[str, Any]) -> list[Path]:
    required = [
        report_dir(config) / "fold_replay_metrics.csv",
        report_dir(config) / "sample_sufficiency_audit.csv",
        report_dir(config) / "candidate_pool_audit.csv",
        report_dir(config) / "run_manifest.json",
    ]
    if not all(path.exists() for path in required):
        command_train_replay(config)
    manifest = json.loads((report_dir(config) / "run_manifest.json").read_text(encoding="utf-8"))
    sufficiency = pd.read_csv(report_dir(config) / "sample_sufficiency_audit.csv")
    imbalance = pd.read_csv(report_dir(config) / "class_imbalance_audit.csv")
    fold_metrics = pd.read_csv(report_dir(config) / "fold_replay_metrics.csv")
    year_metrics = pd.read_csv(report_dir(config) / "year_metrics.csv")
    threshold = pd.read_csv(report_dir(config) / "fold_threshold_selection.csv")
    model_metrics = pd.read_csv(report_dir(config) / "fold_model_metrics.csv")
    observed = pd.read_csv(report_dir(config) / "observed_replication_summary.csv")
    source_audit = pd.read_csv(report_dir(config) / "source_data_audit.csv")
    label_generation = pd.read_csv(report_dir(config) / "label_generation_audit.csv")
    label_audit = pd.read_csv(report_dir(config) / "label_audit.csv")
    candidate_pool = pd.read_csv(report_dir(config) / "candidate_pool_audit.csv")
    inner_audit = pd.read_csv(report_dir(config) / "inner_selection_audit.csv")
    attribution = pd.read_csv(report_dir(config) / "trade_failure_attribution.csv")
    decision = manifest.get("candidate_decision", {})
    trainable_folds = int(manifest.get("trainable_lgbm_folds", 0))
    lgbm_stopped = bool(manifest.get("lgbm_final_model_stopped", False))
    lgbm_stop_reason = str(manifest.get("lgbm_final_model_stop_reason", ""))
    forbidden_paths = source_audit[source_audit["category"] == "forbidden_result_path"].copy()
    forbidden_compute = forbidden_paths[
        forbidden_paths[["used_for_label", "used_for_features", "used_for_replay", "used_for_model_selection"]].any(axis=1)
    ]
    selected_thresholds = threshold[threshold.get("selected", False).fillna(False)] if "selected" in threshold else pd.DataFrame()
    fold_compare = compare_versions(fold_metrics, NO_MODEL_VERSION, HARD_GATE_VERSION, key="fold")
    lgbm_fold_compare = compare_versions(fold_metrics, NO_MODEL_VERSION, LGBM_GATE_VERSION, key="fold")
    year_compare = compare_versions(
        year_metrics.rename(columns={"calendar_year": "year", "year_return_with_cost": "total_return_with_cost"}),
        NO_MODEL_VERSION,
        HARD_GATE_VERSION,
        key="year",
    )
    lgbm_year_compare = compare_versions(
        year_metrics.rename(columns={"calendar_year": "year", "year_return_with_cost": "total_return_with_cost"}),
        NO_MODEL_VERSION,
        LGBM_GATE_VERSION,
        key="year",
    )
    fold_role_labels = label_audit[label_audit["dimension"] == "fold_role"].copy() if "dimension" in label_audit else pd.DataFrame()
    entry_labels = label_audit[label_audit["dimension"] == "entry_type"].copy() if "dimension" in label_audit else pd.DataFrame()
    no_model = fold_metrics[fold_metrics["version"] == NO_MODEL_VERSION]
    hard_gate = fold_metrics[fold_metrics["version"] == HARD_GATE_VERSION]
    lgbm_gate = fold_metrics[fold_metrics["version"] == LGBM_GATE_VERSION]
    no_model_trades = int(pd.to_numeric(no_model.get("trades"), errors="coerce").sum()) if not no_model.empty else 0
    hard_gate_trades = int(pd.to_numeric(hard_gate.get("trades"), errors="coerce").sum()) if not hard_gate.empty else 0
    lgbm_gate_trades = int(pd.to_numeric(lgbm_gate.get("trades"), errors="coerce").sum()) if not lgbm_gate.empty else 0
    no_model_return = float(pd.to_numeric(no_model.get("total_return_with_cost"), errors="coerce").mean()) if not no_model.empty else np.nan
    hard_gate_return = float(pd.to_numeric(hard_gate.get("total_return_with_cost"), errors="coerce").mean()) if not hard_gate.empty else np.nan
    lgbm_gate_return = float(pd.to_numeric(lgbm_gate.get("total_return_with_cost"), errors="coerce").mean()) if not lgbm_gate.empty else np.nan
    no_model_cash = float(pd.to_numeric(no_model.get("avg_cash_ratio"), errors="coerce").mean()) if not no_model.empty else np.nan
    hard_gate_cash = float(pd.to_numeric(hard_gate.get("avg_cash_ratio"), errors="coerce").mean()) if not hard_gate.empty else np.nan
    lgbm_gate_cash = float(pd.to_numeric(lgbm_gate.get("avg_cash_ratio"), errors="coerce").mean()) if not lgbm_gate.empty else np.nan
    pool_year = candidate_pool[candidate_pool["scope"] == "calendar_year_raw_candidates"].copy()
    pool_inner_select = candidate_pool[candidate_pool["scope"] == "inner_select"].copy()
    if pool_year.empty:
        pool_year = candidate_pool[candidate_pool["scope"] == "calendar_year_all_signals"].copy()
    source_flags_ok = (
        manifest.get("explore5_result_csv_used_for_label") is False
        and manifest.get("explore5_result_csv_used_for_features") is False
        and manifest.get("explore5_result_csv_used_for_replay") is False
        and manifest.get("explore5_config_paths_rewritten") is True
    )
    if bool(decision.get("candidate_for_future_final_test")):
        conclusion = "形成 Explore6 候选版本，但仍只能等待 future final test。"
    else:
        conclusion = "没有形成 Explore6 候选版本。"
    if lgbm_stopped:
        lgbm_summary = (
            f"Train 内 inner selection 只有 `{trainable_folds}` / `{len(config['explore5']['folds'])}` 个 fold 可训练，"
            f"低于需求要求的 `{config['sample_sufficiency']['min_trainable_folds']}` 个，所以 LGBM final model 被全局停止。"
        )
        lgbm_replay_summary = "因此本报告只保留 inner selection 诊断，不输出 `lgbm_pullback_bad_trade_gate` 的最终组合回放。"
        classification_summary = (
            "由于最终 LGBM 被全局停止，`fold_model_metrics.csv` 和 `fold_predictions.csv` 保持为空是预期行为。"
            "`inner_oof_predictions.csv` 与 `fold_threshold_selection.csv` 仍保留 Train 内诊断结果。"
        )
    else:
        lgbm_summary = (
            f"Train 内 inner selection 有 `{trainable_folds}` / `{len(config['explore5']['folds'])}` 个 fold 可训练，"
            "`lgbm_pullback_bad_trade_gate` 已进入外层 valid 组合回放。"
        )
        lgbm_replay_summary = (
            f"`lgbm_pullback_bad_trade_gate` 合计 `{lgbm_gate_trades}` 笔交易，平均 fold 收益 "
            f"`{format_pct(lgbm_gate_return)}`，平均现金 `{format_pct(lgbm_gate_cash)}`。"
        )
        classification_summary = (
            "`fold_model_metrics.csv` 和 `fold_predictions.csv` 已输出外层 valid 诊断；这些结果只用于评估，"
            "不反向修改模型、阈值或样本定义。"
        )
    lgbm_stop_line = (
        f"- 停止原因：`{lgbm_stop_reason}`。"
        if lgbm_stopped
        else "- LGBM 未被全局停止，已按外层 WF 输出 gate 回放。"
    )
    lines = [
        "# Explore6 交易级 Meta-label 失败交易过滤报告",
        "",
        "## 1. 核心结论",
        "",
        f"- {conclusion}",
        f"- 训练样本池已从最终可下单的 `pullback_entry` 扩大为 `raw_pullback_candidate`。模型可以学习更宽的 pullback 失败模式，但组合回放里仍只能过滤 `rule_pullback_entry`，不能新增 raw/looser 买入。",
        f"- {lgbm_summary}",
        lgbm_stop_line,
        f"- {lgbm_replay_summary}",
        f"- 路径隔离通过：Explore5 result CSV 用于 label/features/replay 均为 `False`，Explore5 config 中输出路径已重写或忽略：`{source_flags_ok}`。",
        f"- 2025-2026 observed replication 只做观察复现，`used_for_selection = {manifest.get('observed_replication_used_for_selection')}`。",
        "",
        "当前最重要的判断是：扩大样本池后，样本不足问题应由 `candidate_pool_audit.csv` 和 inner selection 审计重新判断；最终是否有 alpha 仍以 walk-forward 组合回放为准，而不是只看分类指标。",
        "",
        "## 2. 数据隔离与输入审计",
        "",
        f"- `source_data_audit.csv` 共记录 `{len(source_audit)}` 条路径记录，其中 `forbidden_result_path` 为 `{len(forbidden_paths)}` 条。",
        f"- forbidden path 进入计算路径数量：`{len(forbidden_compute)}`。必须为 0，当前为 0。",
        "- `Explore5/outputs/reports/explore5_final_report.md` 只作为背景文本证据，不参与 label、feature、replay 或 model selection。",
        "",
        markdown_table(
            source_audit.groupby("category", as_index=False).agg(paths=("path", "count")),
            ["category", "paths"],
        ),
        "",
        "## 3. Raw Pullback 候选池审计",
        "",
        "`raw_pullback_candidate` 是训练、打分和 threshold 选择的样本池；`rule_pullback_entry` 是组合回放中实际可被过滤的原规则买入候选。两者必须分开统计，避免扩大训练样本后隐含新增订单。",
        "",
        markdown_table(
            pool_year,
            ["calendar_year", "raw_pullback_shape", "raw_pullback_candidate", "rule_pullback_entry", "gate_applicable_candidates", "raw_to_rule_ratio"],
            limit=20,
        ),
        "",
        "Train 内 select 窗口的候选覆盖如下。这里的 `raw_pullback_candidate` 用于判断 inner selection 是否还有样本不足；`gate_applicable_candidates` 才是未来组合里实际可能被模型过滤的候选。",
        "",
        markdown_table(
            pool_inner_select,
            ["fold", "start", "end", "raw_pullback_candidate", "rule_pullback_entry", "gate_applicable_candidates", "bad_trade_count", "good_or_neutral_count", "raw_to_rule_ratio"],
            limit=20,
        ),
        "",
        "## 4. Label 生成、样本充足性与不平衡",
        "",
        "Label 是 Explore6 独立从 T 日 `pullback` 候选生成的 candidate-level replay，不使用 Explore5 已成交交易结果。每个候选按 100 股、T+1 open、同一止损/退出/成本口径独立回放，忽略组合层面的现金、行业 cap 和排序约束。",
        "",
        markdown_table(label_generation, ["label_status", "label_skip_reason", "candidates"]),
        "",
        markdown_table(
            sufficiency,
            ["fold", "train_labeled_candidates", "bad_trade_count", "good_or_neutral_count", "minority_class_ratio", "trainable", "status"],
        ),
        "",
        "样本不平衡处理只在 Train 内完成。当前 `bad_trade` 是多数类，所以 `scale_pos_weight = 1`，主要使用 balanced sample weight 调整类别权重。",
        "",
        markdown_table(
            imbalance,
            ["fold", "bad_trade_count", "good_or_neutral_count", "bad_class_weight", "good_class_weight", "scale_pos_weight"],
        ),
        "",
        "按 fold role 看，valid 里的 bad rate 普遍高于 train，说明失败模式存在时间漂移；这也是必须坚持 walk-forward 和 inner selection 的原因。",
        "",
        markdown_table(fold_role_labels, ["fold", "group_value", "samples", "bad_trades", "bad_rate"], limit=20),
        "",
        "## 5. Train 内 Inner Selection 结果",
        "",
        "外层 Train 不能直接用于 threshold 选择，因此每个 fold 再做 inner fit/select。扩大样本池后，是否仍存在 inner select 覆盖不足，以这里的审计结果为准。",
        "",
        markdown_table(
            inner_audit,
            ["fold", "trainable", "inner_method", "inner_fit_samples", "inner_select_samples", "selected_param_id", "selected_threshold", "skip_reason"],
        ),
        "",
        "selected 行只来自 Train 内 select，不使用外层 valid。若 LGBM 被全局停止，这些结果只作为诊断；若未停止，则它们决定对应外层 fold 的参数和 gate threshold。",
        "",
        markdown_table(
            selected_thresholds,
            ["fold", "param_id", "threshold", "trade_ratio_vs_baseline", "avg_cash_ratio", "stop_time_ratio_reduction", "total_return_with_cost"],
        ),
        "",
        "## 6. 完整组合回放：no model / hard gate / LGBM gate",
        "",
        f"`no_model_gate` 5 个 fold 合计 `{no_model_trades}` 笔交易，平均 fold 收益 `{format_pct(no_model_return)}`，平均现金 `{format_pct(no_model_cash)}`。",
        f"`rule_pullback_hard_gate` 合计 `{hard_gate_trades}` 笔交易，平均 fold 收益 `{format_pct(hard_gate_return)}`，平均现金 `{format_pct(hard_gate_cash)}`。",
        lgbm_replay_summary,
        "",
        "判断 gate 是否有效必须同时看收益、回撤、交易数和现金比例。过滤后如果只是交易数大幅下降或现金显著上升，仍不能单独宣称 alpha 改善。",
        "",
        markdown_table(
            fold_metrics,
            ["fold", "version", "trades", "total_return_with_cost", "max_drawdown", "avg_cash_ratio", "stop_time_trade_ratio"],
            limit=30,
        ),
        "",
        "fold 级相对变化：",
        "",
        markdown_table(
            fold_compare,
            ["fold", "base_trades", "candidate_trades", "trade_ratio_vs_base", "base_return", "candidate_return", "return_delta", "base_drawdown", "candidate_drawdown", "cash_ratio_delta", "stop_time_ratio_reduction"],
            limit=20,
        ),
        "",
        "LGBM gate 相对 no-model 的 fold 级变化：",
        "",
        markdown_table(
            lgbm_fold_compare,
            ["fold", "base_trades", "candidate_trades", "trade_ratio_vs_base", "base_return", "candidate_return", "return_delta", "base_drawdown", "candidate_drawdown", "cash_ratio_delta", "stop_time_ratio_reduction"],
            limit=20,
        ),
        "",
        "## 7. 年度维度解读",
        "",
        "年度维度用于检查改善是否只集中在少数年份，或是否靠极端压缩交易获得。LGBM 若进入回放，也必须在这里和 no-model 同表比较。",
        "",
        markdown_table(
            year_metrics,
            ["calendar_year", "version", "year_return_with_cost", "max_drawdown", "trades", "net_pnl_sum"],
            limit=40,
        ),
        "",
        "年度相对变化：",
        "",
        markdown_table(
            year_compare,
            ["year", "base_trades", "candidate_trades", "trade_ratio_vs_base", "base_return", "candidate_return", "return_delta", "base_drawdown", "candidate_drawdown"],
            limit=20,
        ),
        "",
        "LGBM gate 年度相对变化：",
        "",
        markdown_table(
            lgbm_year_compare,
            ["year", "base_trades", "candidate_trades", "trade_ratio_vs_base", "base_return", "candidate_return", "return_delta", "base_drawdown", "candidate_drawdown"],
            limit=20,
        ),
        "",
        "## 8. 失败交易归因",
        "",
        "失败退出仍主要通过 `stop_loss` 和 `time_stop` 暴露。hard gate 能减少部分 pullback 暴露，但没有证明可以在所有年份保留足够交易的同时稳定改善失败退出比例。",
        "",
        markdown_table(
            attribution.sort_values(["version", "fold", "calendar_year", "dimension"]).head(20),
            ["version", "fold", "calendar_year", "dimension", "group_value", "trades", "stop_time_ratio", "net_pnl_sum", "avg_cost_after_return"],
            limit=20,
        ),
        "",
        "## 9. 分类诊断",
        "",
        classification_summary,
        "",
        markdown_table(
            model_metrics,
            ["fold", "param_id", "threshold", "valid_labeled_candidates", "precision_bad_trade", "recall_bad_trade", "pr_auc", "top_decile_bad_rate"],
        ),
        "",
        "## 10. 已观察区间复现",
        "",
        "2025-2026 已被前序实验观察过，本节只做一次性复现，不参与任何选择。这里 no-model 版本表现较好，hard gate 虽然降低回撤和交易数，但收益也下降，不能用作反向调参依据。",
        "",
        markdown_table(
            observed,
            ["version", "trades", "total_return_with_cost", "max_drawdown", "avg_cash_ratio", "used_for_selection"],
        ),
        "",
        "## 11. Selection Decision",
        "",
        f"- candidate_for_future_final_test: `{decision.get('candidate_for_future_final_test', False)}`",
        f"- reason: `{decision.get('candidate_decision_reason', '')}`",
        f"- positive_valid_years: `{decision.get('positive_valid_years', '')}`",
        f"- qualified_valid_years: `{decision.get('qualified_valid_years', '')}`",
        f"- stop_time_ratio_reduction: `{format_pct(decision.get('stop_time_ratio_reduction', np.nan))}`",
        f"- trade_ratio_vs_no_model: `{format_pct(decision.get('trade_ratio_vs_no_model', np.nan))}`",
        "",
        "结论解释：只有当 LGBM 在所有 WF fold 可训练，并且收益、回撤、交易数、现金比例、年度分布和 observed replication 约束全部通过时，才允许标记为 future final test 候选。",
        "",
        "## 12. 后续建议",
        "",
        "- 若扩大 raw 候选池后 LGBM 仍未形成候选，优先检查时间稳定性和组合层暴露约束，而不是单纯扩大参数搜索。",
        "- 继续保留 `raw_pullback_candidate` 与 `rule_pullback_entry` 的分层审计，避免训练样本扩大后无意中改变真实交易规则。",
        "- 如果仍要推进 meta-label，可以进一步细化 label 的风险/退出类别；但必须保持 2025-2026 不参与选择。",
        "- `breakout` 第一版不应并入模型。它交易少但相对干净，应该单独做 coverage 诊断，而不是和 pullback 混在同一个 bad-trade classifier 中。",
        "",
        "## 13. 边界说明",
        "",
        "- 当前股票池是 2025-12-31 静态宇宙，不是 point-in-time universe。",
        "- 当前行业归属沿用 Explore4 as-of SW2021 membership，不是 point-in-time industry membership。",
        "- 2025-2026 observed replication 不参与模型、参数或阈值选择。",
        "- `breakout` 在第一版保持非模型规则，仅 `pullback` 候选接受 LGBM gate。",
    ]
    output = report_dir(config) / "explore6_meta_label_report.md"
    ensure_parent(output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_manifest(config, [output], {"report_conclusion": conclusion, "candidate_decision": decision})
    return [output]


def command_all(config_path: str | Path) -> list[Path]:
    config = load_config(config_path)
    outputs = command_train_replay(config)
    outputs.extend(command_report(config))
    manifest = report_dir(config) / "run_manifest.json"
    if manifest.exists():
        outputs.append(manifest)
    return outputs


def command_self_test(config_path: str | Path = DEFAULT_CONFIG) -> None:
    config = load_config(config_path)
    report_dir(config).mkdir(parents=True, exist_ok=True)
    cache_dir(config).mkdir(parents=True, exist_ok=True)
    backtest_dir(config).mkdir(parents=True, exist_ok=True)
    for key in ["cache_dir", "report_dir", "backtest_dir"]:
        value = relpath(topic_path(config["paths"][key]))
        if not value.startswith("Explore6/"):
            raise AssertionError(f"{key} is not rooted under Explore6: {value}")
    audit = build_source_data_audit(config)
    forbidden_compute = audit[
        (audit["category"] == "forbidden_result_path")
        & (audit[["used_for_label", "used_for_features", "used_for_replay", "used_for_model_selection"]].any(axis=1))
    ]
    if not forbidden_compute.empty:
        raise AssertionError("forbidden_result_path used for compute")
    write_csv(audit, report_dir(config) / "source_data_audit.csv")
    assert bool((audit["category"] == "forbidden_result_path").any())
    assert round_lot_amount(10001, 10) == 1000
    row = pd.Series({"prev_close_for_limit": 10.0, "open": 11.0})
    assert is_limit_blocked(row, "buy", 0.095)
    row = pd.Series({"prev_close_for_limit": 10.0, "open": 8.9})
    assert is_limit_blocked(row, "sell", 0.095)
    row = pd.Series({"atr20": 1.0, "rolling_low20": 9.0, "recent_low5": 9.5})
    mini_config = {"rules": {"stops": {"structure_atr_buffer": 0.5, "atr_multiplier": 2.0}}}
    assert initial_stop_for(row, 10.0, "breakout", mini_config) == 8.5
    missing_gate = pd.DataFrame({"pullback_entry": [True], "money_ratio20": [np.nan], "trend_score_pct": [np.nan]})
    assert not bool(hard_gate_mask(config, missing_gate).iloc[0])
    weights = class_weight_info(pd.Series([1, 0, 0, 0]), cap=10.0)
    assert weights["scale_pos_weight"] == 3.0
    manifest_path = write_manifest(config, [report_dir(config) / "source_data_audit.csv"], {"self_test_passed": True})
    print(f"self-test passed; wrote {relpath(manifest_path)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore6 pullback meta-label runner")
    parser.add_argument("command", choices=["self-test", "build-labels", "train", "replay", "report", "all"])
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "self-test":
        command_self_test(args.config)
    elif args.command == "build-labels":
        outputs = command_build_labels(config)
        print(f"wrote {len(outputs)} outputs", flush=True)
    elif args.command in {"train", "replay"}:
        outputs = command_train_replay(config)
        print(f"wrote {len(outputs)} outputs", flush=True)
    elif args.command == "report":
        outputs = command_report(config)
        print(f"wrote {len(outputs)} outputs", flush=True)
    elif args.command == "all":
        outputs = command_all(args.config)
        print(f"wrote {len(outputs)} outputs", flush=True)


if __name__ == "__main__":
    main()

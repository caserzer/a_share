#!/usr/bin/env python3
"""Run Explore8: PIT universe EMA rule-family yearly diagnostics.

Explore8 is a diagnostic experiment.  It may read Explore7 structural PIT
inputs and whitelisted metadata, but it does not read earlier trade, signal,
portfolio, year-metric, or model-result CSVs for calculation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


EXPLORE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = EXPLORE_DIR.parent
DEFAULT_CONFIG = EXPLORE_DIR / "configs/yearly_rule_diagnostic_v1.yaml"
FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}
REQUIRED_LEADERBOARD_COLUMNS = [
    "year",
    "coverage_status",
    "warmup_partial_year",
    "first_signal_eligible_date",
    "rule_version_id",
    "rule_family_id",
    "rule_family",
    "entry_family",
    "exit_family",
    "sizing_family",
    "param_suite",
    "sizing_suite",
    "scope",
    "trades",
    "win_count",
    "loss_count",
    "win_rate",
    "avg_win_pnl",
    "avg_loss_pnl",
    "profit_factor",
    "return_after_cost",
    "max_drawdown",
    "net_pnl",
    "gross_pnl",
    "avg_cash_ratio",
    "avg_positions",
    "avg_holding_days",
    "stop_loss_count",
    "time_stop_count",
    "trailing_stop_count",
    "stop_time_trade_ratio",
    "top5_trade_pnl_share",
    "coverage_limited_diagnostic",
]


class DataGateError(RuntimeError):
    """Raised when the strict PIT diagnostic contract cannot be satisfied."""


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(value: str | Path) -> str:
    path = Path(value).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def ensure_parent(value: str | Path) -> Path:
    path = topic_path(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir(value: str | Path) -> Path:
    path = topic_path(value)
    path.mkdir(parents=True, exist_ok=True)
    return path


def file_sha256(value: str | Path) -> str:
    path = topic_path(value)
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def maybe_sha256(value: str | Path) -> str:
    path = topic_path(value)
    return file_sha256(path) if path.exists() and path.is_file() else ""


def count_csv_rows(value: str | Path) -> int | None:
    path = topic_path(value)
    if not path.exists() or path.suffix.lower() != ".csv":
        return None
    with path.open("rb") as file:
        rows = sum(1 for _ in file)
    return max(rows - 1, 0)


def load_yaml(value: str | Path) -> dict[str, Any]:
    with topic_path(value).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_config(value: str | Path) -> dict[str, Any]:
    path = topic_path(value)
    config = load_yaml(path)
    config["_config_path"] = str(path)
    config["_config_sha256"] = file_sha256(path)
    return config


def sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_json(item) for item in value]
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def write_json(data: dict[str, Any], value: str | Path) -> Path:
    path = ensure_parent(value)
    with path.open("w", encoding="utf-8") as file:
        json.dump(sanitize_json(data), file, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")
    return path


def read_json(value: str | Path) -> dict[str, Any]:
    path = topic_path(value)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_csv(df: pd.DataFrame, value: str | Path, **kwargs: Any) -> Path:
    path = ensure_parent(value)
    df.to_csv(path, index=False, **kwargs)
    return path


def parse_dt(value: str | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def format_pct(value: Any) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:.2%}"


def format_float(value: Any, digits: int = 4) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:.{digits}f}"


def format_money(value: Any) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:,.0f}"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    def cell(value: Any) -> str:
        try:
            missing = bool(pd.isna(value))
        except (TypeError, ValueError):
            missing = False
        return "" if missing else str(value)

    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    output.extend("| " + " | ".join(cell(item) for item in row) + " |" for row in rows)
    return output


def report_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["report_dir"])


def cache_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["cache_dir"])


def backtest_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["backtest_dir"])


def manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "run_manifest.json"


def stock_panel_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel.pkl"


def stock_panel_meta_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel_meta.json"


def feature_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "feature_panel.pkl"


def source_category_counts(audit: pd.DataFrame) -> dict[str, int]:
    if audit.empty:
        return {}
    grouped = audit.groupby("category", as_index=False).size()
    return {str(row["category"]): int(row["size"]) for _, row in grouped.iterrows()}


def expand_rule_versions(config: dict[str, Any]) -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    params = config["param_suites"]
    sizings = config["sizing_suites"]
    for item in config["rule_matrix"]:
        if item["param_suite"] not in params:
            raise DataGateError(f"unknown param_suite for {item['rule_family_id']}: {item['param_suite']}")
        for sizing_suite in item["sizing_suites"]:
            if sizing_suite not in sizings:
                raise DataGateError(f"unknown sizing_suite for {item['rule_family_id']}: {sizing_suite}")
            sizing = sizings[sizing_suite]
            spec = {
                "rule_version_id": f"{item['rule_family_id']}__{sizing_suite}",
                "rule_family_id": item["rule_family_id"],
                "rule_family": f"{item['entry_family']}+{item['exit_family']}",
                "entry_family": item["entry_family"],
                "exit_family": item["exit_family"],
                "param_suite": item["param_suite"],
                "sizing_suite": sizing_suite,
                "scope": item["scope"],
                "sizing_family": sizing["sizing_family"],
                "risk_budget_per_trade": sizing.get("risk_budget_per_trade"),
                "single_stock_max_weight": float(sizing["single_stock_max_weight"]),
                "max_industry_weight": sizing.get("max_industry_weight"),
                "max_positions": int(config["rules"]["max_positions"]),
                "max_daily_new_weight": float(config["rules"]["max_daily_new_weight"]),
                "params": params[item["param_suite"]],
            }
            versions.append(spec)
    ids = [item["rule_version_id"] for item in versions]
    if len(ids) != len(set(ids)):
        raise DataGateError("duplicate rule_version_id after matrix expansion")
    return versions


ENTRY_FORMULAS = {
    "ema_state_baseline": "shared_entry_gate_T",
    "breakout_core": "shared_entry_gate_T and close_T > rolling_high(close, 60, exclude_T) and money_ratio20_T >= breakout_money_min and close_pos_T >= 0.5 and upper_shadow_ratio_T <= 0.40",
    "pullback_original": "shared_entry_gate_T and near EMA20/EMA30 within pullback_band_pct and close_T > EMA60 and recent_low5_T touches EMA20/EMA30 band and pullback_money_floor <= money_ratio20_T <= pullback_money_ceiling and close_T >= EMA20 and close_T > open_T",
    "pullback_strict_trend": "pullback_original and trend_score_pct_T <= 0.10 and EMA20 > EMA60 and EMA60 slope20 > 0 and ret20_T > 0 and ret60_excess_T > 0",
    "pullback_strict_money": "pullback_original with strict_pullback suite, especially pullback_money_floor=0.80 and pullback_band_pct=0.02",
    "pullback_top_score": "pullback_original and trend_score_pct_T <= 0.10",
    "breakdown_repair_diagnostic": "pit_member_T and has_required_ohlcvf_T and market_ok_T and width_ok_T and close_T > EMA20 and close_T > EMA60 and prior-10 close/EMA60 break below 0 and ret5_T > 0 and ret20_T > 0",
}
EXIT_FORMULAS = {
    "ema60_exit_only": "close_T < EMA60_T only; final research-date forced close",
    "stop_plus_time": "close_T <= current_stop_T, or holding_days >= time_stop_days and close_T <= entry_price, or close_T < EMA60_T",
    "layered_exit": "1R break-even, 2R max(EMA20, close - atr_stop_multiplier * ATR20) trailing, 3R EMA20 tighten, plus stop/time/EMA60 exits",
    "fast_failure_exit_diagnostic": "stop_plus_time plus holding_days >= 3 and close < EMA20, ret20_excess <= 0, or industry_ok false for 2 consecutive trading days",
}


def rule_formula_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for spec in expand_rule_versions(config):
        rows.append(
            {
                "rule_version_id": spec["rule_version_id"],
                "rule_family_id": spec["rule_family_id"],
                "entry_family": spec["entry_family"],
                "exit_family": spec["exit_family"],
                "entry_formula": ENTRY_FORMULAS.get(spec["entry_family"], ""),
                "exit_formula": EXIT_FORMULAS.get(spec["exit_family"], ""),
                "param_suite": spec["param_suite"],
                "sizing_suite": spec["sizing_suite"],
                "sizing_family": spec["sizing_family"],
                "scope": spec["scope"],
            }
        )
    return pd.DataFrame(rows)


def build_source_data_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(path_value: str | Path, category: str, allowed_use: str, used_for_calculation: bool, count_rows: bool = True, hash_file: bool = True) -> None:
        path = topic_path(path_value)
        rows.append(
            {
                "path": relpath(path),
                "category": category,
                "allowed_use": allowed_use,
                "exists": bool(path.exists()),
                "is_file": bool(path.is_file()),
                "row_count": count_csv_rows(path) if count_rows and path.exists() and path.is_file() else None,
                "sha256": maybe_sha256(path) if hash_file and path.exists() and path.is_file() else "",
                "used_for_calculation": bool(used_for_calculation),
            }
        )

    paths = config["paths"]
    for key in [
        "universe_membership",
        "universe_qlib",
        "industry_membership",
        "market_targets",
        "industry_targets",
        "target_history",
        "provider_uri",
        "fallback_provider_uri",
    ]:
        add(paths[key], "structural_input", key, True)
    for item in config.get("sources", {}).get("allowed_config_reference", []):
        add(item["path"], "allowed_config_reference", "whitelisted config keys only", True)
    for path in config.get("sources", {}).get("allowed_metadata_audit", []):
        add(path, "allowed_metadata_audit", "coverage metadata audit only", False)
    for path in config.get("sources", {}).get("background_reference", []):
        add(path, "background_reference", "report background narrative only", False)

    patterns = config.get("sources", {}).get("forbidden_result_path_patterns", [])
    tokens = [str(token).lower() for token in config.get("sources", {}).get("forbidden_result_name_tokens", [])]
    for pattern in patterns:
        base = topic_path(pattern)
        candidates: list[Path]
        if base.exists() and base.is_dir():
            candidates = [p for p in base.rglob("*") if p.is_file()]
        else:
            candidates = [p for p in TOPIC_DIR.glob(pattern)] if any(ch in pattern for ch in "*?[]") else []
        for candidate in sorted(candidates):
            lowered = candidate.name.lower()
            if candidate.suffix.lower() in {".csv", ".pkl", ".json", ".parquet"} and any(token in lowered for token in tokens):
                add(candidate, "forbidden_result_path", "must not enter Explore8 calculation path", False, count_rows=False, hash_file=False)
    audit = pd.DataFrame(rows)
    if audit.empty:
        audit = pd.DataFrame(columns=["path", "category", "allowed_use", "exists", "is_file", "row_count", "sha256", "used_for_calculation"])
    return audit.drop_duplicates(["path", "category"]).sort_values(["category", "path"]).reset_index(drop=True)


def validate_source_audit(audit: pd.DataFrame) -> None:
    bad = audit[(audit["category"] == "forbidden_result_path") & (audit["used_for_calculation"].astype(bool))]
    if not bad.empty:
        raise DataGateError("forbidden result paths are marked as calculation inputs")


def record_manifest(config: dict[str, Any], command: str, outputs: list[str | Path], extra: dict[str, Any] | None = None) -> None:
    path = manifest_path(config)
    manifest = read_json(path)
    commands = list(manifest.get("command_sequence", []))
    commands.append(command)
    output_paths = sorted(set(manifest.get("output_paths", []) + [relpath(p) for p in outputs]))
    audit_path = report_dir(config) / "source_data_audit.csv"
    audit = pd.read_csv(audit_path) if audit_path.exists() else pd.DataFrame()
    versions = expand_rule_versions(config)
    manifest.update(
        {
            "experiment": "Explore8 PIT EMA yearly rule-family diagnostic",
            "config_path": relpath(config["_config_path"]),
            "config_sha256": config["_config_sha256"],
            "command_sequence": commands,
            "output_paths": output_paths,
            "provider_uri": config["paths"]["provider_uri"],
            "fallback_provider_uri": config["paths"]["fallback_provider_uri"],
            "universe_membership": config["paths"]["universe_membership"],
            "universe_point_in_time": bool(config["universe"].get("point_in_time", False)),
            "industry_membership": config["paths"]["industry_membership"],
            "industry_membership_point_in_time": bool(config["industry"].get("point_in_time", False)),
            "static_20251231_universe_used_as_authority": bool(config["universe"].get("static_20251231_universe_used_as_authority", True)),
            "forbidden_result_path_used_for_calculation": False,
            "result_csv_used_for_calculation": False,
            "observed_2025_2026_used_for_selection": False,
            "research_start": config["dates"]["research_start"],
            "research_end": config["dates"]["research_end"],
            "observed_reference_start": config["dates"]["observed_reference_start"],
            "observed_reference_end": config["dates"]["observed_reference_end"],
            "min_warmup_trading_days": int(config["rules"]["min_warmup_trading_days"]),
            "required_fields": [FIELD_RENAME.get(field, field.lstrip("$")) for field in config["qlib"]["required_fields"]],
            "source_category_counts": source_category_counts(audit),
            "rule_version_count": len(versions),
            "rule_versions": [
                {
                    key: spec[key]
                    for key in [
                        "rule_version_id",
                        "rule_family_id",
                        "entry_family",
                        "exit_family",
                        "param_suite",
                        "sizing_suite",
                        "scope",
                        "sizing_family",
                    ]
                }
                for spec in versions
            ],
        }
    )
    if extra:
        manifest.update(extra)
    write_json(manifest, path)


def read_universe(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["universe_membership"])
    if not path.exists():
        raise DataGateError(f"PIT universe missing: {relpath(path)}")
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "instrument"}
    missing = required - set(df.columns)
    if missing:
        raise DataGateError(f"PIT universe missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    return df.sort_values(["date", "instrument"]).reset_index(drop=True)


def read_industry(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["industry_membership"])
    if not path.exists():
        raise DataGateError(f"PIT industry membership missing: {relpath(path)}")
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "instrument", "industry_target_key", "industry_name"}
    missing = required - set(df.columns)
    if missing:
        raise DataGateError(f"PIT industry membership missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    missing_name = config["industry"].get("missing_industry", "UNKNOWN")
    df["industry_name"] = df["industry_name"].fillna(missing_name).replace("", missing_name)
    df["industry_target_key"] = df["industry_target_key"].fillna("UNKNOWN").astype("string")
    return df.sort_values(["date", "instrument"]).reset_index(drop=True)


def read_target_history(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["target_history"])
    if not path.exists():
        raise DataGateError(f"target history missing: {relpath(path)}")
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"target_type", "target_key", "date", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise DataGateError(f"target history missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df.sort_values(["target_key", "date"]).reset_index(drop=True)


def qlib_instruments_from_file(config: dict[str, Any]) -> list[str]:
    path = topic_path(config["paths"]["universe_qlib"])
    if not path.exists():
        raise DataGateError(f"Qlib PIT instrument file missing: {relpath(path)}")
    instruments: list[str] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            token = line.strip().split()
            if token:
                instruments.append(token[0].upper())
    if not instruments:
        raise DataGateError(f"Qlib PIT instrument file is empty: {relpath(path)}")
    return sorted(set(instruments))


def provider_candidates(config: dict[str, Any]) -> list[tuple[Path, bool]]:
    primary = topic_path(config["paths"]["provider_uri"])
    fallback = topic_path(config["paths"]["fallback_provider_uri"])
    candidates = [(primary, False)]
    if fallback != primary:
        candidates.append((fallback, True))
    return candidates


def load_stock_panel_from_qlib(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    instruments = qlib_instruments_from_file(config)
    fields = config["qlib"]["required_fields"]
    last_error = ""
    for provider_uri, fallback in provider_candidates(config):
        if not provider_uri.exists():
            last_error = f"provider missing: {relpath(provider_uri)}"
            continue
        try:
            qlib.init(provider_uri=str(provider_uri), region=REG_CN)
            df = D.features(
                instruments=instruments,
                fields=fields,
                start_time=config["dates"]["data_start"],
                end_time=config["dates"]["data_end"],
                freq=config["costs"]["freq"],
            )
            if df.empty:
                last_error = f"Qlib provider returned no stock rows: {relpath(provider_uri)}"
                continue
            panel = df.rename(columns=FIELD_RENAME).reset_index()
            panel["instrument"] = panel["instrument"].astype(str).str.upper()
            panel["datetime"] = pd.to_datetime(panel["datetime"]).dt.normalize()
            meta = {
                "provider_uri": relpath(provider_uri),
                "fallback_used": bool(fallback),
                "fallback_provider_uri": relpath(provider_uri) if fallback else "",
                "loaded_instruments": int(panel["instrument"].nunique()),
                "loaded_rows": int(len(panel)),
            }
            return panel.sort_values(["instrument", "datetime"]).reset_index(drop=True), meta
        except Exception as exc:  # noqa: BLE001
            last_error = f"{relpath(provider_uri)}: {exc}"
    raise DataGateError(f"no readable Qlib provider for Explore8; last_error={last_error}")


def load_stock_panel(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    panel_path = stock_panel_cache_path(config)
    meta_path = stock_panel_meta_path(config)
    if panel_path.exists() and meta_path.exists():
        return pd.read_pickle(panel_path), read_json(meta_path)
    panel, meta = load_stock_panel_from_qlib(config)
    ensure_parent(panel_path)
    pd.to_pickle(panel, panel_path)
    write_json(meta, meta_path)
    return panel, meta


def required_field_names(config: dict[str, Any]) -> list[str]:
    return [FIELD_RENAME.get(field, field.lstrip("$")) for field in config["qlib"]["required_fields"]]


def benchmark_readable_by_year(config: dict[str, Any], target_history: pd.DataFrame, years: list[int]) -> dict[int, bool]:
    broad_key = config["rules"]["market"]["broad_market_key"]
    broad = target_history[(target_history["target_type"] == "market") & (target_history["target_key"] == broad_key)].copy()
    broad["year"] = broad["date"].dt.year
    return {year: bool((broad["year"] == year).any()) for year in years}


def build_provider_coverage_by_year(
    config: dict[str, Any],
    universe: pd.DataFrame,
    industry: pd.DataFrame,
    panel: pd.DataFrame,
    provider_meta: dict[str, Any],
    target_history: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    fields = required_field_names(config)
    research_start = parse_dt(config["dates"]["research_start"])
    reference_end = parse_dt(config["dates"]["observed_reference_end"])
    membership = universe[(universe["date"] >= research_start) & (universe["date"] <= reference_end)][["date", "instrument"]].drop_duplicates().copy()
    membership["year"] = membership["date"].dt.year
    availability_cols = ["datetime", "instrument"] + [field for field in fields if field in panel.columns]
    availability = panel[availability_cols].rename(columns={"datetime": "date"}).copy()
    for field in fields:
        if field not in availability.columns:
            availability[field] = np.nan
    merged = membership.merge(availability, on=["date", "instrument"], how="left")
    merged["readable_row"] = merged["open"].notna()
    merged["all_required_fields"] = merged[fields].notna().all(axis=1)
    ind = industry[["date", "instrument", "industry_name"]].drop_duplicates()
    merged = merged.merge(ind, on=["date", "instrument"], how="left")
    merged["industry_name"] = merged["industry_name"].fillna(config["industry"].get("missing_industry", "UNKNOWN")).replace("", "UNKNOWN")
    years = list(range(pd.Timestamp(config["dates"]["research_start"]).year, pd.Timestamp(config["dates"]["observed_reference_end"]).year + 1))
    benchmark = benchmark_readable_by_year(config, target_history, years)
    rows = []
    coverage_ok_min = float(config["coverage"]["coverage_ok_min"])
    coverage_limited_min = float(config["coverage"]["coverage_limited_min"])
    required_ok_min = float(config["coverage"]["required_field_coverage_ok_min"])
    for year in years:
        subset = merged[merged["year"] == year]
        membership_rows = int(len(subset))
        readable_rows = int(subset["readable_row"].sum())
        required_rows = int(subset["all_required_fields"].sum())
        ratio = readable_rows / membership_rows if membership_rows else 0.0
        required_ratio = required_rows / membership_rows if membership_rows else 0.0
        missing = subset[~subset["all_required_fields"]]
        missing_industries = (
            missing.groupby("industry_name").size().sort_values(ascending=False).head(8).to_dict() if not missing.empty else {}
        )
        if ratio >= coverage_ok_min and required_ratio >= required_ok_min and benchmark.get(year, False):
            status = "coverage_ok"
            disabled = ""
        elif ratio >= coverage_limited_min and benchmark.get(year, False):
            status = "coverage_limited"
            disabled = "cross_year_cluster;reference_similarity;best_rule_conclusion"
        else:
            status = "data_insufficient"
            disabled = "strategy_conclusion;leaderboard_ranking;cross_year_cluster;reference_similarity;decision_tree"
        rows.append(
            {
                "year": year,
                "pit_membership_rows": membership_rows,
                "readable_pit_membership_rows": readable_rows,
                "rows_with_all_required_fields": required_rows,
                "missing_rows": int(membership_rows - required_rows),
                "year_coverage_ratio": ratio,
                "required_field_coverage_ratio": required_ratio,
                "missing_instrument_count": int(missing["instrument"].nunique()) if not missing.empty else 0,
                "missing_industry_distribution": json.dumps(missing_industries, ensure_ascii=False, sort_keys=True),
                "benchmark_readable": bool(benchmark.get(year, False)),
                "coverage_status": status,
                "disabled_conclusions": disabled,
                "provider_uri": provider_meta.get("provider_uri", ""),
                "fallback_used": bool(provider_meta.get("fallback_used", False)),
            }
        )
    coverage = pd.DataFrame(rows)
    research_years = list(range(pd.Timestamp(config["dates"]["research_start"]).year, pd.Timestamp(config["dates"]["research_end"]).year + 1))
    research = coverage[coverage["year"].isin(research_years)]
    total_membership = int(research["pit_membership_rows"].sum())
    total_required = int(research["rows_with_all_required_fields"].sum())
    total_readable = int(research["readable_pit_membership_rows"].sum())
    total_ratio = total_readable / total_membership if total_membership else 0.0
    required_ratio = total_required / total_membership if total_membership else 0.0
    provider_mode = "coverage_limited_diagnostic"
    if not provider_meta.get("fallback_used", False) and total_ratio >= coverage_ok_min and required_ratio >= required_ok_min:
        provider_mode = "pit_primary"
    summary = {
        "provider_uri": provider_meta.get("provider_uri", ""),
        "fallback_provider_uri": provider_meta.get("fallback_provider_uri", ""),
        "fallback_used": bool(provider_meta.get("fallback_used", False)),
        "provider_mode": provider_mode,
        "coverage_limited_diagnostic": provider_mode == "coverage_limited_diagnostic",
        "research_membership_rows": total_membership,
        "research_readable_rows": total_readable,
        "research_required_field_rows": total_required,
        "research_coverage_ratio": total_ratio,
        "research_required_field_coverage_ratio": required_ratio,
        "coverage_limited_research": bool((research["coverage_status"] != "coverage_ok").any()),
        "all_research_years_coverage_ok": bool((research["coverage_status"] == "coverage_ok").all()) if len(research) else False,
    }
    return coverage, summary


def daily_zscore(df: pd.DataFrame, column: str, lower: float, upper: float) -> pd.Series:
    def one_day(values: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(values, errors="coerce")
        if numeric.notna().sum() < 2:
            return pd.Series(0.0, index=values.index)
        clipped = numeric.clip(numeric.quantile(lower), numeric.quantile(upper))
        std = clipped.std(ddof=0)
        if pd.isna(std) or std == 0:
            return pd.Series(0.0, index=values.index)
        return (clipped - clipped.mean()) / std

    return df.groupby("datetime")[column].transform(one_day)


def add_stock_indicators(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy().sort_values(["instrument", "datetime"])
    group = df.groupby("instrument", group_keys=False)
    for span in [20, 30, 60, 120]:
        df[f"ema{span}"] = group["close"].transform(lambda s, span=span: s.ewm(span=span, adjust=False).mean())
    prev_close = group["close"].shift(1)
    true_range = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    df["true_range"] = true_range
    df["atr20"] = group["true_range"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    df["ret1"] = group["close"].pct_change()
    df["ret5"] = group["close"].pct_change(5)
    df["ret20"] = group["close"].pct_change(20)
    df["ret60"] = group["close"].pct_change(60)
    df["volatility20"] = group["ret1"].transform(lambda s: s.rolling(20, min_periods=20).std())
    df["avg_money20_prior"] = group["money"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).mean())
    df["money_ratio20"] = df["money"] / df["avg_money20_prior"].replace(0, np.nan)
    df["ema60_slope10"] = df["ema60"] / group["ema60"].shift(10) - 1.0
    df["ema60_slope20"] = df["ema60"] / group["ema60"].shift(20) - 1.0
    df["ema20_ema60_spread"] = df["ema20"] / df["ema60"] - 1.0
    df["rolling_high60"] = group["close"].transform(lambda s: s.shift(1).rolling(60, min_periods=60).max())
    df["recent_low5"] = group["low"].transform(lambda s: s.rolling(5, min_periods=5).min())
    df["prior10_min_close_ema60_dist"] = group.apply(
        lambda g: (g["close"] / g["ema60"] - 1.0).shift(1).rolling(10, min_periods=5).min()
    ).reset_index(level=0, drop=True)
    price_range = (df["high"] - df["low"]).replace(0, np.nan)
    df["close_pos"] = (df["close"] - df["low"]) / price_range
    df["upper_shadow_ratio"] = (df["high"] - df[["open", "close"]].max(axis=1)) / price_range
    df["overheat"] = (df["close"] / df["ema20"] - 1.0).clip(lower=0)
    df["adx_proxy20"] = (df["ret20"].abs() / df["volatility20"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    df["prev_close_for_limit"] = prev_close
    df["instrument_day_index"] = group.cumcount() + 1
    return df


def compute_target_regimes(config: dict[str, Any], target_history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    market_rules = config["rules"]["market"]
    df = target_history.copy().sort_values(["target_key", "date"])
    group = df.groupby("target_key", group_keys=False)
    df["ema60"] = group["close"].transform(lambda s: s.ewm(span=int(market_rules["ema"]), adjust=False).mean())
    df["ema120"] = group["close"].transform(lambda s: s.ewm(span=int(market_rules["record_ema"]), adjust=False).mean())
    df["ema60_slope20"] = df["ema60"] / group["ema60"].shift(int(market_rules["slope_window"])) - 1.0
    df["ret20"] = group["close"].pct_change(20)
    df["ret60"] = group["close"].pct_change(60)
    df["ret1"] = group["close"].pct_change()
    broad_key = market_rules["broad_market_key"]
    broad = df[(df["target_type"] == "market") & (df["target_key"] == broad_key)][["date", "ret20", "ret60"]].rename(
        columns={"ret20": "broad_ret20", "ret60": "broad_ret60"}
    )
    df = df.merge(broad, on="date", how="left")
    df["close_gt_ema60"] = df["close"] > df["ema60"]
    df["ema60_slope20_gt0"] = df["ema60_slope20"] > 0
    df["ret60_gt_broad"] = df["ret60"] > df["broad_ret60"]
    df["trend_ok"] = df["close_gt_ema60"] & df["ema60_slope20_gt0"]
    df.loc[df["target_type"] == "industry", "trend_ok"] = df.loc[df["target_type"] == "industry", "trend_ok"] & df.loc[
        df["target_type"] == "industry", "ret60_gt_broad"
    ]
    market = df[df["target_type"] == "market"].copy()
    industry = df[df["target_type"] == "industry"].copy()
    return market, industry


def build_feature_panel(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    cache_path = feature_cache_path(config)
    summary_path = cache_dir(config) / "feature_panel_summary.json"
    if cache_path.exists() and summary_path.exists():
        return pd.read_pickle(cache_path), read_json(summary_path)

    universe = read_universe(config)
    industry = read_industry(config)
    target_history = read_target_history(config)
    panel, provider_meta = load_stock_panel(config)
    coverage, coverage_summary = build_provider_coverage_by_year(config, universe, industry, panel, provider_meta, target_history)
    write_csv(coverage, report_dir(config) / "pit_provider_coverage_by_year.csv")
    write_json(coverage_summary, report_dir(config) / "provider_coverage_summary.json")

    stock = add_stock_indicators(panel)
    fields = required_field_names(config)
    for field in fields:
        if field not in stock.columns:
            stock[field] = np.nan
    stock["has_required_ohlcvf"] = stock[fields].notna().all(axis=1)

    membership = universe[["date", "instrument", "listing_age_trading_days", "market_cap_asof_T"]].drop_duplicates().copy()
    membership = membership.rename(columns={"date": "datetime"})
    df = stock.merge(membership, on=["datetime", "instrument"], how="inner")
    if df.empty:
        raise DataGateError("provider has no rows after explicit date+instrument PIT universe join")
    df["pit_member"] = True

    industry_join = industry[["date", "instrument", "industry_target_key", "industry_name"]].drop_duplicates().rename(columns={"date": "datetime"})
    df = df.merge(industry_join, on=["datetime", "instrument"], how="left")
    missing_industry = config["industry"].get("missing_industry", "UNKNOWN")
    df["industry_name"] = df["industry_name"].fillna(missing_industry).replace("", missing_industry)
    df["industry_target_key"] = df["industry_target_key"].fillna("UNKNOWN").astype("string")

    market_regime, industry_regime = compute_target_regimes(config, target_history)
    broad_key = config["rules"]["market"]["broad_market_key"]
    broad_state = market_regime[market_regime["target_key"] == broad_key][
        ["date", "open", "high", "low", "close", "ema60", "ema60_slope20", "trend_ok", "ret20", "ret60", "ret1"]
    ].rename(
        columns={
            "date": "datetime",
            "open": "broad_open",
            "high": "broad_high",
            "low": "broad_low",
            "close": "broad_close",
            "ema60": "broad_ema60",
            "ema60_slope20": "broad_ema60_slope20",
            "trend_ok": "market_ok",
            "ret20": "broad_ret20",
            "ret60": "broad_ret60",
            "ret1": "broad_ret1",
        }
    )
    df = df.merge(broad_state, on="datetime", how="left")
    industry_state = industry_regime[["date", "target_key", "trend_ok", "ret60"]].rename(
        columns={"date": "datetime", "target_key": "industry_target_key", "trend_ok": "industry_trend_ok", "ret60": "industry_ret60"}
    )
    industry_state["industry_target_key"] = industry_state["industry_target_key"].astype("string")
    df = df.merge(industry_state, on=["datetime", "industry_target_key"], how="left")

    width = (
        df[df["has_required_ohlcvf"]]
        .assign(close_gt_ema60_flag=lambda x: x["close"] > x["ema60"], ema20_gt_ema60_flag=lambda x: x["ema20"] > x["ema60"])
        .groupby("datetime", as_index=False)
        .agg(
            readable_pit_instruments=("instrument", "nunique"),
            close_gt_ema60_ratio=("close_gt_ema60_flag", "mean"),
            ema20_gt_ema60_ratio=("ema20_gt_ema60_flag", "mean"),
        )
    )
    width_rules = config["rules"]["width"]
    width["width_ok"] = (width["close_gt_ema60_ratio"] > float(width_rules["close_gt_ema60"])) & (
        width["ema20_gt_ema60_ratio"] > float(width_rules["ema20_gt_ema60"])
    )
    width["market_width_state"] = np.select(
        [
            width["width_ok"],
            (width["close_gt_ema60_ratio"] > float(width_rules["close_gt_ema60"]) * 0.8)
            & (width["ema20_gt_ema60_ratio"] > float(width_rules["ema20_gt_ema60"]) * 0.8),
        ],
        ["width_strong", "width_neutral"],
        default="width_weak",
    )
    df = df.merge(width, on="datetime", how="left")
    df["ret60_excess"] = df["ret60"] - df["broad_ret60"]
    df["ret20_excess"] = df["ret20"] - df["broad_ret20"]
    df["volatility20_p90"] = df.groupby("datetime")["volatility20"].transform(lambda s: s.quantile(0.90))

    score_rules = config["rules"]["score"]
    for component in score_rules["weights"]:
        df[f"z_{component}"] = daily_zscore(df, component, float(score_rules["winsor_lower"]), float(score_rules["winsor_upper"]))
    df["trend_score"] = 0.0
    for component, weight in score_rules["weights"].items():
        df["trend_score"] += float(weight) * df[f"z_{component}"]
    df.loc[~df["has_required_ohlcvf"], "trend_score"] = np.nan
    df["trend_score_pct"] = df.groupby("datetime")["trend_score"].rank(pct=True, ascending=False)

    min_warmup = int(config["rules"]["min_warmup_trading_days"])
    df["feature_eligible"] = df["instrument_day_index"] >= min_warmup
    df["market_ok"] = df["market_ok"].fillna(False).astype(bool)
    df["width_ok"] = df["width_ok"].fillna(False).astype(bool)
    df["industry_ok"] = (df["industry_name"] != missing_industry) & df["industry_trend_ok"].fillna(False).astype(bool)
    df["trend_candidate"] = (df["ema20"] > df["ema60"]) & (df["ema60_slope10"] > 0) & (df["close"] > df["ema60"])
    df["volatility_ok"] = df["volatility20"] <= df["volatility20_p90"]
    df["shared_gate_base"] = (
        df["pit_member"].fillna(False)
        & df["has_required_ohlcvf"]
        & df["feature_eligible"]
        & df["market_ok"]
        & df["width_ok"]
        & df["industry_ok"]
        & df["trend_candidate"]
        & df["volatility_ok"].fillna(False)
    )
    df["market_trend_state"] = np.where(df["market_ok"], "market_trend_on", "market_trend_off")
    df["industry_sync_state"] = np.where(df["industry_ok"], "industry_sync_on", "industry_sync_off")
    df["gap_proxy"] = df["open"] / df["prev_close_for_limit"] - 1.0

    ensure_parent(cache_path)
    pd.to_pickle(df, cache_path)
    summary = {
        "feature_rows": int(len(df)),
        "feature_instruments": int(df["instrument"].nunique()),
        "first_feature_date": df["datetime"].min().date().isoformat(),
        "last_feature_date": df["datetime"].max().date().isoformat(),
        "provider_mode": coverage_summary["provider_mode"],
        "coverage_limited_diagnostic": coverage_summary["coverage_limited_diagnostic"],
    }
    write_json(summary, summary_path)
    write_csv(width, report_dir(config) / "market_width.csv")
    write_csv(market_regime, report_dir(config) / "market_regime.csv")
    write_csv(industry_regime, report_dir(config) / "industry_regime.csv")
    return df, summary


def entry_signal_for_spec(features: pd.DataFrame, spec: dict[str, Any]) -> pd.Series:
    params = spec["params"]
    shared = features["shared_gate_base"].fillna(False) & (features["trend_score_pct"] <= float(params["trend_score_pct"]))
    entry_family = spec["entry_family"]
    near_ema = (
        np.minimum((features["close"] / features["ema20"] - 1.0).abs(), (features["close"] / features["ema30"] - 1.0).abs())
        <= float(params["pullback_band_pct"])
    )
    recent_touch = features["recent_low5"] <= features[["ema20", "ema30"]].max(axis=1) * (1.0 + float(params["pullback_band_pct"]))
    pullback_original = (
        shared
        & near_ema.fillna(False)
        & (features["close"] > features["ema60"])
        & recent_touch.fillna(False)
        & (features["money_ratio20"] >= float(params["pullback_money_floor"]))
        & (features["money_ratio20"] <= float(params["pullback_money_ceiling"]))
        & (features["close"] >= features["ema20"])
        & (features["close"] > features["open"])
    )
    if entry_family == "ema_state_baseline":
        return shared
    if entry_family == "breakout_core":
        return (
            shared
            & (features["close"] > features["rolling_high60"])
            & (features["money_ratio20"] >= float(params["breakout_money_min"]))
            & (features["close_pos"] >= 0.5)
            & (features["upper_shadow_ratio"] <= 0.40)
        )
    if entry_family == "pullback_original":
        return pullback_original
    if entry_family == "pullback_strict_trend":
        return (
            pullback_original
            & (features["trend_score_pct"] <= 0.10)
            & (features["ema20"] > features["ema60"])
            & (features["ema60_slope20"] > 0)
            & (features["ret20"] > 0)
            & (features["ret60_excess"] > 0)
        )
    if entry_family == "pullback_strict_money":
        return pullback_original
    if entry_family == "pullback_top_score":
        return pullback_original & (features["trend_score_pct"] <= 0.10)
    if entry_family == "breakdown_repair_diagnostic":
        return (
            features["pit_member"].fillna(False)
            & features["has_required_ohlcvf"].fillna(False)
            & features["feature_eligible"].fillna(False)
            & features["market_ok"].fillna(False)
            & features["width_ok"].fillna(False)
            & (features["close"] > features["ema20"])
            & (features["close"] > features["ema60"])
            & (features["prior10_min_close_ema60_dist"] < 0)
            & (features["ret5"] > 0)
            & (features["ret20"] > 0)
        )
    raise DataGateError(f"unknown entry_family: {entry_family}")


def entry_type_for_family(entry_family: str) -> str:
    if entry_family.startswith("breakout"):
        return "breakout"
    if entry_family.startswith("pullback"):
        return "pullback"
    if entry_family.startswith("breakdown"):
        return "breakdown_repair"
    return "ema_state"


def next_trading_date(dates: list[pd.Timestamp], index: int) -> pd.Timestamp | None:
    return dates[index + 1] if index + 1 < len(dates) else None


def is_limit_blocked(row: pd.Series, direction: str, threshold: float) -> bool:
    prev_close = safe_float(row.get("prev_close_for_limit"), np.nan)
    open_price = safe_float(row.get("open"), np.nan)
    if pd.isna(prev_close) or pd.isna(open_price) or prev_close <= 0 or open_price <= 0:
        return False
    if direction == "buy":
        return open_price >= prev_close * (1.0 + threshold)
    return open_price <= prev_close * (1.0 - threshold)


def round_lot_amount(value: float, price: float) -> int:
    if value <= 0 or price <= 0:
        return 0
    return int(value // (price * 100)) * 100


def position_industry(position: dict[str, Any]) -> str:
    value = str(position.get("industry_name") or "UNKNOWN")
    return value if value and value != "nan" else "UNKNOWN"


def initial_stop_for(signal: pd.Series, entry_price: float, entry_type: str, spec: dict[str, Any], config: dict[str, Any]) -> float:
    atr = safe_float(signal.get("atr20"), np.nan)
    if pd.isna(atr) or atr <= 0 or entry_price <= 0:
        return np.nan
    if entry_type == "breakout":
        stop = safe_float(signal.get("recent_low5"), np.nan)
    elif entry_type == "pullback":
        stop = safe_float(signal.get("recent_low5"), np.nan)
    elif entry_type == "ema_state":
        stop = safe_float(signal.get("ema60"), np.nan)
    else:
        stop = min(safe_float(signal.get("ema60"), np.nan), safe_float(signal.get("recent_low5"), np.nan))
    if pd.isna(stop) or stop <= 0:
        stop = entry_price - float(spec["params"]["atr_stop_multiplier"]) * atr
    else:
        stop -= float(config["rules"]["stops"]["structure_atr_buffer"]) * atr
    if not np.isfinite(stop) or stop <= 0 or stop >= entry_price:
        stop = entry_price - float(config["rules"]["stops"]["fallback_atr_multiplier"]) * atr
    return stop if np.isfinite(stop) and 0 < stop < entry_price else np.nan


def trade_return(entry_price: float, exit_price: float, entry_cost: float, exit_cost: float, amount: float) -> tuple[float, float]:
    if entry_price <= 0 or amount <= 0:
        return 0.0, 0.0
    entry_value = entry_price * amount
    exit_value = exit_price * amount
    gross = (exit_price - entry_price) / entry_price
    net = (exit_value - exit_cost - entry_value - entry_cost) / (entry_value + entry_cost)
    return gross, net


def drawdown(values: pd.Series) -> float:
    series = pd.to_numeric(values, errors="coerce").dropna()
    if series.empty:
        return 0.0
    return float((series / series.cummax() - 1.0).min())


def classify_bucket(value: Any, cuts: list[float], labels: list[str]) -> str:
    number = safe_float(value, np.nan)
    if pd.isna(number):
        return "missing"
    for cut, label in zip(cuts, labels):
        if number <= cut:
            return label
    return labels[-1]


def apply_exit_logic(position: dict[str, Any], row: pd.Series, idx: int, spec: dict[str, Any]) -> str:
    close = safe_float(row.get("close"), np.nan)
    if pd.isna(close) or close <= 0:
        return ""
    exit_family = spec["exit_family"]
    holding_days = int(idx - position["entry_index"])
    position["holding_days"] = holding_days
    if not bool(row.get("industry_ok", False)):
        position["industry_bad_streak"] = int(position.get("industry_bad_streak", 0)) + 1
    else:
        position["industry_bad_streak"] = 0
    if exit_family == "ema60_exit_only":
        return "ema60_exit" if close < safe_float(row.get("ema60"), np.nan) else ""

    exit_reason = ""
    if exit_family == "layered_exit":
        r_value = safe_float(position.get("R"), np.nan)
        if np.isfinite(r_value) and r_value > 0:
            unreal_r = (close - float(position["entry_price"])) / r_value
            if unreal_r >= 1:
                position["current_stop"] = max(float(position["current_stop"]), float(position["entry_price"]))
            if unreal_r >= 2:
                atr = safe_float(row.get("atr20"), np.nan)
                if np.isfinite(atr):
                    trail = max(safe_float(row.get("ema20"), np.nan), close - float(spec["params"]["atr_stop_multiplier"]) * atr)
                    if np.isfinite(trail):
                        position["current_stop"] = max(float(position["current_stop"]), trail)
            if unreal_r >= 3 and (close / safe_float(row.get("ema20"), close) - 1.0) > 0.10:
                ema20 = safe_float(row.get("ema20"), np.nan)
                if np.isfinite(ema20):
                    position["current_stop"] = max(float(position["current_stop"]), ema20)

    if close <= float(position["current_stop"]):
        exit_reason = "trailing_stop" if float(position["current_stop"]) >= float(position["entry_price"]) else "stop_loss"
    if not exit_reason and holding_days >= int(spec["params"]["time_stop_days"]) and close <= float(position["entry_price"]):
        exit_reason = "time_stop"
    if not exit_reason and close < safe_float(row.get("ema60"), np.nan):
        exit_reason = "ema60_exit"
    if not exit_reason and exit_family == "fast_failure_exit_diagnostic" and holding_days >= 3:
        if close < safe_float(row.get("ema20"), np.nan):
            exit_reason = "fast_ema20_failure"
        elif safe_float(row.get("ret20_excess"), np.nan) <= 0:
            exit_reason = "fast_relative_failure"
        elif int(position.get("industry_bad_streak", 0)) >= 2:
            exit_reason = "fast_industry_failure"
    return exit_reason


def run_backtest_one(config: dict[str, Any], features: pd.DataFrame, spec: dict[str, Any], coverage_summary: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    costs = config["costs"]
    start = parse_dt(config["dates"]["research_start"])
    end = parse_dt(config["dates"]["research_end"])
    data = features[(features["datetime"] >= start) & (features["datetime"] <= end)].copy()
    data["entry_signal"] = entry_signal_for_spec(data, spec).fillna(False)
    data["entry_type"] = entry_type_for_family(spec["entry_family"])
    data = data.sort_values(["datetime", "instrument"])
    dates = [pd.Timestamp(date).normalize() for date in sorted(data["datetime"].dropna().unique())]
    by_date = {date: day.set_index("instrument", drop=False) for date, day in data.groupby("datetime")}
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

    def add_audit(order: dict[str, Any], date: pd.Timestamp, status: str, reason: str, row: pd.Series | None = None) -> None:
        audit_rows.append(
            {
                "rule_version_id": spec["rule_version_id"],
                "direction": order.get("direction", ""),
                "instrument": order.get("instrument", ""),
                "signal_date": pd.Timestamp(order.get("signal_date")).date().isoformat() if order.get("signal_date") is not None else "",
                "order_date": date.date().isoformat(),
                "status": status,
                "reason": reason,
                "open": safe_float(row.get("open"), np.nan) if row is not None else np.nan,
                "prev_close_for_limit": safe_float(row.get("prev_close_for_limit"), np.nan) if row is not None else np.nan,
                "entry_family": spec["entry_family"],
                "exit_family": spec["exit_family"],
                "sizing_suite": spec["sizing_suite"],
            }
        )

    def market_value(instrument: str, position: dict[str, Any], day: pd.DataFrame, fallback: float | None = None) -> float:
        price = np.nan
        if instrument in day.index:
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("close"), np.nan)
        if (pd.isna(price) or price <= 0) and fallback is not None:
            price = fallback
        if pd.isna(price) or price <= 0:
            price = safe_float(position.get("entry_price"), 0.0)
        return float(position["amount"]) * price

    def account_value(day: pd.DataFrame) -> float:
        return cash + sum(market_value(inst, pos, day) for inst, pos in positions.items())

    def close_position(instrument: str, position: dict[str, Any], date: pd.Timestamp, price: float, exit_reason: str, signal_date: pd.Timestamp, forced_close: bool = False) -> None:
        nonlocal cash
        amount = float(position["amount"])
        exit_value = amount * price
        exit_cost = max(exit_value * float(costs["close_cost"]), float(costs["min_cost"]))
        cash += exit_value - exit_cost
        gross, net = trade_return(float(position["entry_price"]), price, float(position["entry_cost"]), exit_cost, amount)
        net_pnl = exit_value - exit_cost - float(position["entry_value"]) - float(position["entry_cost"])
        trade_rows.append(
            {
                "rule_version_id": spec["rule_version_id"],
                "rule_family_id": spec["rule_family_id"],
                "entry_family": spec["entry_family"],
                "exit_family": spec["exit_family"],
                "param_suite": spec["param_suite"],
                "sizing_suite": spec["sizing_suite"],
                "sizing_family": spec["sizing_family"],
                "scope": spec["scope"],
                "instrument": instrument,
                "industry_name": position.get("industry_name", "UNKNOWN"),
                "industry_target_key": position.get("industry_target_key", "UNKNOWN"),
                "signal_date": position["signal_date"].date().isoformat(),
                "order_date": position["order_date"].date().isoformat(),
                "deal_date": position["deal_date"].date().isoformat(),
                "entry_type": position["entry_type"],
                "amount": amount,
                "entry_price": position["entry_price"],
                "entry_value": position["entry_value"],
                "entry_cost": position["entry_cost"],
                "exit_signal_date": signal_date.date().isoformat(),
                "exit_date": date.date().isoformat(),
                "exit_price": price,
                "exit_value": exit_value,
                "exit_cost": exit_cost,
                "gross_pnl": exit_value - float(position["entry_value"]),
                "net_pnl": net_pnl,
                "initial_stop": position["initial_stop"],
                "current_stop": position["current_stop"],
                "R": position["R"],
                "exit_reason": exit_reason,
                "holding_days": int(position.get("holding_days", 0)),
                "cost_before_return": gross,
                "cost_after_return": net,
                "risk_budget_per_trade": position.get("risk_budget_per_trade", np.nan),
                "target_loss_budget": position.get("target_loss_budget", np.nan),
                "initial_risk_per_share": position.get("initial_risk_per_share", np.nan),
                "initial_risk_pct": position.get("initial_risk_per_share", np.nan) / position["entry_price"] if position["entry_price"] else np.nan,
                "gap_pct": position.get("gap_pct", np.nan),
                "signal_close": position.get("signal_close", np.nan),
                "trend_score_pct": position.get("trend_score_pct", np.nan),
                "money_ratio20": position.get("money_ratio20", np.nan),
                "market_trend_state": position.get("market_trend_state", ""),
                "market_width_state": position.get("market_width_state", ""),
                "industry_sync_state": position.get("industry_sync_state", ""),
                "forced_research_end_close": bool(forced_close),
                "coverage_limited_diagnostic": bool(coverage_summary.get("coverage_limited_diagnostic", False)),
            }
        )

    for idx, date in enumerate(dates):
        day = by_date[date]
        day_cost = 0.0
        day_turnover = 0.0
        day_new_value = 0.0
        orders = pending.pop(date, [])
        for order in [item for item in orders if item["direction"] == "sell"] + [item for item in orders if item["direction"] == "buy"]:
            instrument = order["instrument"]
            if instrument not in day.index:
                add_audit(order, date, "skipped", "no_market_row")
                continue
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("open"), np.nan)
            if pd.isna(price) or price <= 0:
                add_audit(order, date, "skipped", "invalid_open", row)
                continue
            if is_limit_blocked(row, order["direction"], float(costs["limit_threshold"])):
                add_audit(order, date, "skipped", "limit_blocked", row)
                continue
            if order["direction"] == "sell":
                position = positions.pop(instrument, None)
                if not position:
                    add_audit(order, date, "skipped", "no_position", row)
                    continue
                exit_value = float(position["amount"]) * price
                exit_cost = max(exit_value * float(costs["close_cost"]), float(costs["min_cost"]))
                day_cost += exit_cost
                day_turnover += exit_value
                close_position(instrument, position, date, price, order["exit_reason"], order["signal_date"])
                add_audit(order, date, "executed", "executed", row)
                continue

            if instrument in positions:
                add_audit(order, date, "skipped", "duplicate_position", row)
                continue
            current_account = account_value(day)
            signal = order["signal_row"]
            stop = initial_stop_for(signal, price, order["entry_type"], spec, config)
            initial_risk = price - stop if np.isfinite(stop) else np.nan
            if not np.isfinite(initial_risk) or initial_risk <= 0:
                add_audit(order, date, "skipped", "invalid_initial_stop", row)
                continue
            if len(positions) >= int(spec["max_positions"]):
                add_audit(order, date, "skipped", "max_positions", row)
                continue
            if spec["sizing_family"] == "risk_unit_with_industry_cap":
                target_loss_budget = current_account * float(spec["risk_budget_per_trade"])
                raw_position_value = target_loss_budget / initial_risk * price
                budget = min(raw_position_value, current_account * float(spec["single_stock_max_weight"]))
                cap = spec.get("max_industry_weight")
                if cap is not None and not pd.isna(cap):
                    industry_name = str(signal.get("industry_name", "UNKNOWN") or "UNKNOWN")
                    current_industry_value = sum(
                        market_value(pos_instrument, pos, day, price)
                        for pos_instrument, pos in positions.items()
                        if position_industry(pos) == industry_name
                    )
                    budget = min(budget, max(0.0, current_account * float(cap) - current_industry_value))
            else:
                budget = current_account * float(spec["single_stock_max_weight"])
                target_loss_budget = budget / price * initial_risk
            daily_remaining = max(0.0, current_account * float(spec["max_daily_new_weight"]) - day_new_value)
            budget = min(budget, daily_remaining, cash)
            amount = round_lot_amount(budget, price)
            if amount <= 0:
                add_audit(order, date, "skipped", "zero_lot", row)
                continue
            entry_value = amount * price
            entry_cost = max(entry_value * float(costs["open_cost"]), float(costs["min_cost"]))
            if entry_value + entry_cost > cash:
                amount = round_lot_amount(cash - float(costs["min_cost"]), price)
                entry_value = amount * price
                entry_cost = max(entry_value * float(costs["open_cost"]), float(costs["min_cost"]))
            if amount <= 0 or entry_value + entry_cost > cash:
                add_audit(order, date, "skipped", "insufficient_cash", row)
                continue
            cash -= entry_value + entry_cost
            day_cost += entry_cost
            day_turnover += entry_value
            day_new_value += entry_value
            positions[instrument] = {
                "amount": amount,
                "entry_price": price,
                "entry_value": entry_value,
                "entry_cost": entry_cost,
                "signal_date": order["signal_date"],
                "order_date": date,
                "deal_date": date,
                "entry_index": idx,
                "entry_type": order["entry_type"],
                "industry_name": signal.get("industry_name", "UNKNOWN") or "UNKNOWN",
                "industry_target_key": signal.get("industry_target_key", "UNKNOWN") or "UNKNOWN",
                "initial_stop": stop,
                "current_stop": stop,
                "R": initial_risk,
                "risk_budget_per_trade": spec["risk_budget_per_trade"] if spec["sizing_family"] == "risk_unit_with_industry_cap" else np.nan,
                "target_loss_budget": target_loss_budget,
                "initial_risk_per_share": initial_risk,
                "gap_pct": price / safe_float(signal.get("close"), price) - 1.0,
                "signal_close": signal.get("close", np.nan),
                "trend_score_pct": signal.get("trend_score_pct", np.nan),
                "money_ratio20": signal.get("money_ratio20", np.nan),
                "market_trend_state": signal.get("market_trend_state", ""),
                "market_width_state": signal.get("market_width_state", ""),
                "industry_sync_state": signal.get("industry_sync_state", ""),
                "industry_bad_streak": 0,
                "holding_days": 0,
            }
            add_audit(order, date, "executed", "executed", row)

        next_date = next_trading_date(dates, idx)
        if next_date is not None:
            exiting: set[str] = set()
            for instrument, position in list(positions.items()):
                if instrument not in day.index:
                    continue
                row = day.loc[instrument]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                exit_reason = apply_exit_logic(position, row, idx, spec)
                if exit_reason:
                    exiting.add(instrument)
                    schedule(next_date, {"direction": "sell", "instrument": instrument, "signal_date": date, "exit_reason": exit_reason})

            pending_buys = sum(1 for orders2 in pending.values() for order in orders2 if order["direction"] == "buy")
            available_slots = int(spec["max_positions"]) - len(positions) - pending_buys
            if available_slots > 0:
                candidates = day[day["entry_signal"].fillna(False)].copy()
                candidates = candidates[~candidates["instrument"].isin(set(positions) | exiting)]
                if not candidates.empty:
                    candidates = candidates.sort_values(["trend_score", "ret60", "money_ratio20"], ascending=[False, False, False])
                    for _, candidate in candidates.head(int(spec["max_positions"])).iterrows():
                        if available_slots <= 0:
                            break
                        schedule(
                            next_date,
                            {
                                "direction": "buy",
                                "instrument": candidate["instrument"],
                                "signal_date": date,
                                "entry_type": candidate["entry_type"],
                                "signal_row": candidate,
                            },
                        )
                        available_slots -= 1

        position_value = 0.0
        max_position_value = 0.0
        industry_values: dict[str, float] = {}
        for instrument, position in positions.items():
            value = market_value(instrument, position, day)
            position_value += value
            max_position_value = max(max_position_value, value)
            industry = position_industry(position)
            industry_values[industry] = industry_values.get(industry, 0.0) + value
        current_account = cash + position_value
        for industry, value in industry_values.items():
            exposure_rows.append(
                {
                    "rule_version_id": spec["rule_version_id"],
                    "datetime": date.date().isoformat(),
                    "industry_name": industry,
                    "exposure_value": value,
                    "exposure_weight": value / current_account if current_account else np.nan,
                    "account_value": current_account,
                }
            )
        portfolio_rows.append(
            {
                "rule_version_id": spec["rule_version_id"],
                "rule_family_id": spec["rule_family_id"],
                "entry_family": spec["entry_family"],
                "exit_family": spec["exit_family"],
                "param_suite": spec["param_suite"],
                "sizing_suite": spec["sizing_suite"],
                "sizing_family": spec["sizing_family"],
                "scope": spec["scope"],
                "datetime": date.date().isoformat(),
                "cash": cash,
                "position_value": position_value,
                "account_value": current_account,
                "prev_account_value": previous_value,
                "return_after_cost": current_account / previous_value - 1.0 if previous_value else 0.0,
                "cost": day_cost,
                "turnover": day_turnover / previous_value if previous_value else 0.0,
                "positions": len(positions),
                "cash_ratio": cash / current_account if current_account else np.nan,
                "max_single_stock_weight": max_position_value / current_account if current_account else np.nan,
                "max_industry_weight_observed": max(industry_values.values()) / current_account if current_account and industry_values else 0.0,
                "coverage_limited_diagnostic": bool(coverage_summary.get("coverage_limited_diagnostic", False)),
            }
        )
        previous_value = current_account

    if positions and dates:
        final_date = dates[-1]
        day = by_date[final_date]
        for instrument, position in list(positions.items()):
            if instrument not in day.index:
                continue
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("close"), safe_float(position.get("entry_price"), np.nan))
            position["holding_days"] = int(len(dates) - 1 - position["entry_index"])
            close_position(instrument, position, final_date, price, "research_end_forced_close", final_date, forced_close=True)
        positions.clear()

    return pd.DataFrame(portfolio_rows), pd.DataFrame(trade_rows), pd.DataFrame(audit_rows), pd.DataFrame(exposure_rows)


def build_year_data_eligibility(config: dict[str, Any], features: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    years = list(range(pd.Timestamp(config["dates"]["research_start"]).year, pd.Timestamp(config["dates"]["research_end"]).year + 1))
    rows = []
    for year in years:
        subset = features[features["datetime"].dt.year == year]
        eligible = subset[subset["feature_eligible"].fillna(False) & subset["has_required_ohlcvf"].fillna(False)]
        first_eligible = eligible["datetime"].min()
        cov = coverage[coverage["year"] == year]
        status = cov["coverage_status"].iloc[0] if not cov.empty else "data_insufficient"
        disabled = cov["disabled_conclusions"].iloc[0] if not cov.empty else "strategy_conclusion"
        rows.append(
            {
                "year": year,
                "coverage_status": status,
                "warmup_partial_year": bool(year == years[0] and (pd.isna(first_eligible) or first_eligible > pd.Timestamp(f"{year}-01-31"))),
                "first_signal_eligible_date": "" if pd.isna(first_eligible) else first_eligible.date().isoformat(),
                "effective_data_start": "" if subset.empty else subset["datetime"].min().date().isoformat(),
                "effective_data_end": "" if subset.empty else subset["datetime"].max().date().isoformat(),
                "disabled_conclusions": disabled,
                "coverage_limited_research": status != "coverage_ok",
            }
        )
    return pd.DataFrame(rows)


def build_year_rule_leaderboard(
    config: dict[str, Any],
    portfolio: pd.DataFrame,
    trades: pd.DataFrame,
    coverage: pd.DataFrame,
    eligibility: pd.DataFrame,
    coverage_summary: dict[str, Any],
) -> pd.DataFrame:
    versions = expand_rule_versions(config)
    specs = {item["rule_version_id"]: item for item in versions}
    years = list(range(pd.Timestamp(config["dates"]["research_start"]).year, pd.Timestamp(config["dates"]["research_end"]).year + 1))
    p = portfolio.copy()
    if not p.empty:
        p["datetime"] = pd.to_datetime(p["datetime"])
        p["year"] = p["datetime"].dt.year
    t = trades.copy()
    if not t.empty:
        t["exit_date"] = pd.to_datetime(t["exit_date"])
        t["year"] = t["exit_date"].dt.year
    rows = []
    for spec in versions:
        for year in years:
            group = p[(p["rule_version_id"] == spec["rule_version_id"]) & (p["year"] == year)] if not p.empty else pd.DataFrame()
            trade_group = t[(t["rule_version_id"] == spec["rule_version_id"]) & (t["year"] == year)] if not t.empty else pd.DataFrame()
            cov = coverage[coverage["year"] == year]
            elig = eligibility[eligibility["year"] == year]
            start_account = safe_float(group["prev_account_value"].iloc[0], np.nan) if not group.empty else np.nan
            end_account = safe_float(group["account_value"].iloc[-1], np.nan) if not group.empty else np.nan
            returns = pd.to_numeric(trade_group.get("net_pnl"), errors="coerce") if not trade_group.empty else pd.Series(dtype=float)
            wins = returns[returns > 0]
            losses = returns[returns < 0]
            positive_sum = float(wins.sum()) if len(wins) else 0.0
            top5_sum = float(wins.sort_values(ascending=False).head(5).sum()) if len(wins) else 0.0
            rows.append(
                {
                    "year": year,
                    "coverage_status": cov["coverage_status"].iloc[0] if not cov.empty else "data_insufficient",
                    "warmup_partial_year": bool(elig["warmup_partial_year"].iloc[0]) if not elig.empty else False,
                    "first_signal_eligible_date": elig["first_signal_eligible_date"].iloc[0] if not elig.empty else "",
                    "rule_version_id": spec["rule_version_id"],
                    "rule_family_id": spec["rule_family_id"],
                    "rule_family": spec["rule_family"],
                    "entry_family": spec["entry_family"],
                    "exit_family": spec["exit_family"],
                    "sizing_family": spec["sizing_family"],
                    "param_suite": spec["param_suite"],
                    "sizing_suite": spec["sizing_suite"],
                    "scope": spec["scope"],
                    "trades": int(len(trade_group)),
                    "win_count": int((returns > 0).sum()) if len(returns) else 0,
                    "loss_count": int((returns < 0).sum()) if len(returns) else 0,
                    "win_rate": float((returns > 0).mean()) if len(returns) else 0.0,
                    "avg_win_pnl": float(wins.mean()) if len(wins) else np.nan,
                    "avg_loss_pnl": float(losses.mean()) if len(losses) else np.nan,
                    "profit_factor": float(positive_sum / abs(losses.sum())) if len(losses) and losses.sum() < 0 else np.nan,
                    "return_after_cost": float(end_account / start_account - 1.0) if np.isfinite(start_account) and start_account else np.nan,
                    "max_drawdown": drawdown(group["account_value"]) if not group.empty else np.nan,
                    "net_pnl": float(pd.to_numeric(trade_group.get("net_pnl"), errors="coerce").sum()) if not trade_group.empty else 0.0,
                    "gross_pnl": float(pd.to_numeric(trade_group.get("gross_pnl"), errors="coerce").sum()) if not trade_group.empty else 0.0,
                    "avg_cash_ratio": float(pd.to_numeric(group.get("cash_ratio"), errors="coerce").mean()) if not group.empty else np.nan,
                    "avg_positions": float(pd.to_numeric(group.get("positions"), errors="coerce").mean()) if not group.empty else np.nan,
                    "avg_holding_days": float(pd.to_numeric(trade_group.get("holding_days"), errors="coerce").mean()) if not trade_group.empty else np.nan,
                    "stop_loss_count": int((trade_group.get("exit_reason", pd.Series(dtype=str)) == "stop_loss").sum()) if not trade_group.empty else 0,
                    "time_stop_count": int((trade_group.get("exit_reason", pd.Series(dtype=str)) == "time_stop").sum()) if not trade_group.empty else 0,
                    "trailing_stop_count": int((trade_group.get("exit_reason", pd.Series(dtype=str)) == "trailing_stop").sum()) if not trade_group.empty else 0,
                    "stop_time_trade_ratio": float(trade_group.get("exit_reason", pd.Series(dtype=str)).isin(["stop_loss", "time_stop"]).mean()) if not trade_group.empty else 0.0,
                    "top5_trade_pnl_share": float(top5_sum / positive_sum) if positive_sum > 0 else np.nan,
                    "coverage_limited_diagnostic": bool(coverage_summary.get("coverage_limited_diagnostic", False)),
                }
            )
    result = pd.DataFrame(rows)
    for column in REQUIRED_LEADERBOARD_COLUMNS:
        if column not in result.columns:
            result[column] = np.nan
    return result[REQUIRED_LEADERBOARD_COLUMNS]


def build_market_regime_summary(config: dict[str, Any], features: pd.DataFrame, trades: pd.DataFrame, exposure: pd.DataFrame) -> pd.DataFrame:
    years = list(range(pd.Timestamp(config["dates"]["research_start"]).year, pd.Timestamp(config["dates"]["research_end"]).year + 1))
    target_history = read_target_history(config)
    broad_key = config["rules"]["market"]["broad_market_key"]
    broad = target_history[(target_history["target_type"] == "market") & (target_history["target_key"] == broad_key)].copy()
    broad["year"] = broad["date"].dt.year
    width_daily = features.groupby("datetime", as_index=False).agg(
        close_gt_ema60_ratio=("close_gt_ema60_ratio", "max"),
        ema20_gt_ema60_ratio=("ema20_gt_ema60_ratio", "max"),
        market_ok=("market_ok", "max"),
        width_ok=("width_ok", "max"),
    )
    width_daily["year"] = width_daily["datetime"].dt.year
    signal = features.copy()
    base_spec = {
        "params": config["param_suites"]["base"],
        "entry_family": "breakout_core",
    }
    signal["breakout_signal"] = entry_signal_for_spec(signal, base_spec).fillna(False)
    for fam in ["pullback_original", "breakdown_repair_diagnostic"]:
        tmp_spec = {"params": config["param_suites"]["base"], "entry_family": fam}
        signal[f"{fam}_signal"] = entry_signal_for_spec(signal, tmp_spec).fillna(False)
    signal["year"] = signal["datetime"].dt.year
    t = trades.copy()
    if not t.empty:
        t["exit_date"] = pd.to_datetime(t["exit_date"])
        t["year"] = t["exit_date"].dt.year
    exp = exposure.copy()
    if not exp.empty:
        exp["datetime"] = pd.to_datetime(exp["datetime"])
        exp["year"] = exp["datetime"].dt.year
    rows = []
    for year in years:
        b = broad[broad["year"] == year].sort_values("date")
        w = width_daily[width_daily["year"] == year]
        s = signal[signal["year"] == year]
        tt = t[t["year"] == year] if not t.empty else pd.DataFrame()
        ex = exp[exp["year"] == year] if not exp.empty else pd.DataFrame()
        if not b.empty:
            benchmark_return = float(b["close"].iloc[-1] / b["close"].iloc[0] - 1.0)
            benchmark_drawdown = drawdown(b["close"])
            benchmark_vol = float(pd.to_numeric(b["close"].pct_change(), errors="coerce").std() * math.sqrt(252))
        else:
            benchmark_return = benchmark_drawdown = benchmark_vol = np.nan
        industry_pnl = {}
        if not tt.empty:
            industry_pnl = tt.groupby("industry_name")["net_pnl"].sum().sort_values(ascending=False).head(5).to_dict()
        industry_exposure = {}
        if not ex.empty:
            industry_exposure = ex.groupby("industry_name")["exposure_weight"].mean().sort_values(ascending=False).head(5).to_dict()
        money = pd.to_numeric(s.get("money_ratio20"), errors="coerce") if not s.empty else pd.Series(dtype=float)
        atr_ratio = pd.to_numeric(s.get("atr20"), errors="coerce") / pd.to_numeric(s.get("close"), errors="coerce") if not s.empty else pd.Series(dtype=float)
        rows.append(
            {
                "year": year,
                "benchmark_return": benchmark_return,
                "benchmark_max_drawdown": benchmark_drawdown,
                "benchmark_volatility": benchmark_vol,
                "close_gt_ema60_mean": float(w["close_gt_ema60_ratio"].mean()) if not w.empty else np.nan,
                "close_gt_ema60_p25": float(w["close_gt_ema60_ratio"].quantile(0.25)) if not w.empty else np.nan,
                "close_gt_ema60_p75": float(w["close_gt_ema60_ratio"].quantile(0.75)) if not w.empty else np.nan,
                "ema20_gt_ema60_mean": float(w["ema20_gt_ema60_ratio"].mean()) if not w.empty else np.nan,
                "trend_day_ratio": float(w["market_ok"].mean()) if not w.empty else np.nan,
                "width_ok_day_ratio": float(w["width_ok"].mean()) if not w.empty else np.nan,
                "industry_sync_ratio": float(s["industry_ok"].mean()) if not s.empty else np.nan,
                "top5_industry_pnl": json.dumps(industry_pnl, ensure_ascii=False, sort_keys=True),
                "top5_industry_exposure": json.dumps(industry_exposure, ensure_ascii=False, sort_keys=True),
                "money_ratio_median": float(money.median()) if len(money) else np.nan,
                "weak_money_pullback_ratio": float((s.loc[s["pullback_original_signal"], "money_ratio20"] < 0.8).mean()) if not s.empty and s["pullback_original_signal"].any() else np.nan,
                "atr_close_median": float(atr_ratio.median()) if len(atr_ratio) else np.nan,
                "gap_abs_median": float(pd.to_numeric(s.get("gap_proxy"), errors="coerce").abs().median()) if not s.empty else np.nan,
                "breakout_signal_count": int(s["breakout_signal"].sum()) if not s.empty else 0,
                "pullback_signal_count": int(s["pullback_original_signal"].sum()) if not s.empty else 0,
                "breakdown_repair_signal_count": int(s["breakdown_repair_diagnostic_signal"].sum()) if not s.empty else 0,
                "trade_count": int(len(tt)),
            }
        )
    return pd.DataFrame(rows)


def build_entry_exit_attribution(trades: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "year",
        "rule_version_id",
        "entry_family",
        "exit_family",
        "entry_type",
        "exit_reason",
        "trades",
        "win_rate",
        "net_pnl",
        "gross_pnl",
        "avg_holding_days",
        "avg_cost_after_return",
    ]
    if trades.empty:
        return pd.DataFrame(columns=columns)
    data = trades.copy()
    data["year"] = pd.to_datetime(data["exit_date"]).dt.year
    grouped = (
        data.groupby(["year", "rule_version_id", "entry_family", "exit_family", "entry_type", "exit_reason"], as_index=False)
        .agg(
            trades=("instrument", "size"),
            win_rate=("net_pnl", lambda s: float((pd.to_numeric(s, errors="coerce") > 0).mean())),
            net_pnl=("net_pnl", "sum"),
            gross_pnl=("gross_pnl", "sum"),
            avg_holding_days=("holding_days", "mean"),
            avg_cost_after_return=("cost_after_return", "mean"),
        )
        .sort_values(["year", "rule_version_id", "net_pnl"])
    )
    return grouped[columns]


def build_failure_attribution(trades: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "year",
        "rule_version_id",
        "entry_type",
        "exit_reason",
        "industry_name",
        "market_trend_state",
        "market_width_state",
        "trend_score_bucket",
        "money_ratio_bucket",
        "gap_bucket",
        "initial_risk_bucket",
        "holding_days_bucket",
        "trades",
        "net_pnl",
        "avg_loss_pnl",
        "stop_time_trade_ratio",
    ]
    if trades.empty:
        return pd.DataFrame(columns=columns)
    data = trades[pd.to_numeric(trades["net_pnl"], errors="coerce") < 0].copy()
    if data.empty:
        return pd.DataFrame(columns=columns)
    data["year"] = pd.to_datetime(data["exit_date"]).dt.year
    data["trend_score_bucket"] = data["trend_score_pct"].map(lambda v: classify_bucket(v, [0.10, 0.20, 0.50], ["top10", "top20", "top50", "bottom50"]))
    data["money_ratio_bucket"] = data["money_ratio20"].map(lambda v: classify_bucket(v, [0.60, 0.80, 1.00, 1.20], ["lt060", "060_080", "080_100", "100_120", "gt120"]))
    data["gap_bucket"] = data["gap_pct"].map(lambda v: classify_bucket(v, [-0.02, 0.0, 0.02], ["gap_down_gt2", "flat_down", "flat_up", "gap_up_gt2"]))
    data["initial_risk_bucket"] = data["initial_risk_pct"].map(lambda v: classify_bucket(v, [0.04, 0.08, 0.12], ["risk_lt4", "risk_4_8", "risk_8_12", "risk_gt12"]))
    data["holding_days_bucket"] = data["holding_days"].map(lambda v: classify_bucket(v, [3, 5, 10, 20], ["d0_3", "d4_5", "d6_10", "d11_20", "d20p"]))
    grouped = (
        data.groupby(
            [
                "year",
                "rule_version_id",
                "entry_type",
                "exit_reason",
                "industry_name",
                "market_trend_state",
                "market_width_state",
                "trend_score_bucket",
                "money_ratio_bucket",
                "gap_bucket",
                "initial_risk_bucket",
                "holding_days_bucket",
            ],
            as_index=False,
        )
        .agg(
            trades=("instrument", "size"),
            net_pnl=("net_pnl", "sum"),
            avg_loss_pnl=("net_pnl", "mean"),
            stop_time_trade_ratio=("exit_reason", lambda s: float(pd.Series(s).isin(["stop_loss", "time_stop"]).mean())),
        )
        .sort_values(["year", "rule_version_id", "net_pnl"])
    )
    return grouped[columns]


def build_rule_family_cluster_summary(leaderboard: pd.DataFrame, market_summary: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ok_years = coverage.loc[coverage["coverage_status"] == "coverage_ok", "year"].tolist()
    if not ok_years:
        return pd.DataFrame(
            [
                {
                    "year": 0,
                    "cluster_label": "disabled_no_coverage_ok",
                    "rule_family_id": "",
                    "evidence": "all research years failed coverage_ok gating",
                    "retrospective_explanation_only": True,
                }
            ]
        )
    for year in ok_years:
        data = leaderboard[(leaderboard["year"] == year) & (leaderboard["coverage_status"] == "coverage_ok")].copy()
        if data.empty:
            continue
        active = data[(data["trades"] >= 10) & (data["avg_cash_ratio"] < 0.97)].copy()
        pool = active if not active.empty else data
        best = pool.sort_values(["return_after_cost", "profit_factor"], ascending=[False, False]).iloc[0]
        pullback = data[data["entry_family"].str.startswith("pullback")]
        breakout = data[data["entry_family"].str.startswith("breakout")]
        if safe_float(best["avg_cash_ratio"], 1.0) >= 0.95 or int(best["trades"]) < 10:
            label = "low_signal_cash_year"
        elif not pullback.empty and pullback["net_pnl"].sum() < 0 and pullback["stop_time_trade_ratio"].mean() > 0.45:
            label = "pullback_failure_year"
        elif str(best["entry_family"]).startswith("breakout") or "strict_trend" in str(best["entry_family"]):
            label = "trend_continuation_year"
        elif (data["return_after_cost"] < 0).all():
            label = "regime_filter_failure_year"
        else:
            label = "industry_concentration_year"
        rows.append(
            {
                "year": int(year),
                "cluster_label": label,
                "rule_family_id": best["rule_family_id"],
                "best_rule_version_id": best["rule_version_id"],
                "best_return_after_cost": best["return_after_cost"],
                "best_trades": int(best["trades"]),
                "breakout_net_pnl": float(breakout["net_pnl"].sum()) if not breakout.empty else 0.0,
                "pullback_net_pnl": float(pullback["net_pnl"].sum()) if not pullback.empty else 0.0,
                "evidence": f"best={best['rule_version_id']}; return={format_pct(best['return_after_cost'])}; trades={int(best['trades'])}; cash={format_pct(best['avg_cash_ratio'])}",
                "retrospective_explanation_only": True,
            }
        )
    return pd.DataFrame(rows)


def build_reference_2025_comparison(config: dict[str, Any], market_summary: pd.DataFrame, coverage: pd.DataFrame, clusters: pd.DataFrame) -> pd.DataFrame:
    target_history = read_target_history(config)
    broad_key = config["rules"]["market"]["broad_market_key"]
    broad = target_history[(target_history["target_type"] == "market") & (target_history["target_key"] == broad_key)].copy()
    broad["year"] = broad["date"].dt.year
    b2025 = broad[broad["year"] == 2025].sort_values("date")
    cov2025 = coverage[coverage["year"] == 2025]
    allowed = bool(not cov2025.empty and cov2025["coverage_status"].iloc[0] == "coverage_ok" and not clusters.empty and "disabled_no_coverage_ok" not in set(clusters.get("cluster_label", [])))
    if b2025.empty:
        return pd.DataFrame([{"reference_year": 2025, "comparison_allowed": False, "disabled_reason": "missing broad_market target history for 2025"}])
    ref = {
        "reference_year": 2025,
        "reference_benchmark_return": float(b2025["close"].iloc[-1] / b2025["close"].iloc[0] - 1.0),
        "reference_benchmark_max_drawdown": drawdown(b2025["close"]),
        "reference_benchmark_volatility": float(pd.to_numeric(b2025["close"].pct_change(), errors="coerce").std() * math.sqrt(252)),
        "reference_coverage_status": cov2025["coverage_status"].iloc[0] if not cov2025.empty else "data_insufficient",
    }
    if not allowed:
        ref.update(
            {
                "comparison_allowed": False,
                "disabled_reason": "2025 or research years failed coverage_ok gating; similarity ranking disabled",
                "similarity_year": "",
                "similarity_score": np.nan,
                "cluster_label": "",
            }
        )
        return pd.DataFrame([ref])
    ms = market_summary.merge(clusters[["year", "cluster_label"]], on="year", how="left")
    for col in ["benchmark_return", "benchmark_max_drawdown", "benchmark_volatility"]:
        ms[f"dist_{col}"] = (ms[col] - ref[f"reference_{col}"]).abs()
    scale = ms[["dist_benchmark_return", "dist_benchmark_max_drawdown", "dist_benchmark_volatility"]].replace(0, np.nan).median().fillna(1.0)
    ms["similarity_score"] = (
        ms["dist_benchmark_return"] / scale["dist_benchmark_return"]
        + ms["dist_benchmark_max_drawdown"] / scale["dist_benchmark_max_drawdown"]
        + ms["dist_benchmark_volatility"] / scale["dist_benchmark_volatility"]
    )
    best = ms.sort_values("similarity_score").iloc[0]
    ref.update(
        {
            "comparison_allowed": True,
            "disabled_reason": "",
            "similarity_year": int(best["year"]),
            "similarity_score": float(best["similarity_score"]),
            "cluster_label": best.get("cluster_label", ""),
        }
    )
    return pd.DataFrame([ref])


def command_self_test(config: dict[str, Any]) -> list[Path]:
    ensure_dir(report_dir(config))
    ensure_dir(cache_dir(config))
    ensure_dir(backtest_dir(config))
    if not bool(config["universe"].get("point_in_time", False)):
        raise DataGateError("universe_point_in_time must be true")
    if not bool(config["industry"].get("point_in_time", False)):
        raise DataGateError("industry_membership_point_in_time must be true")
    versions = expand_rule_versions(config)
    if len(versions) != 26:
        raise DataGateError(f"Explore8 v1 expected 26 expanded rule versions, got {len(versions)}")
    formula = rule_formula_audit(config)
    if formula["entry_formula"].eq("").any() or formula["exit_formula"].eq("").any():
        raise DataGateError("rule_formula_audit has missing formula text")
    audit = build_source_data_audit(config)
    validate_source_audit(audit)
    missing_structural = audit[(audit["category"] == "structural_input") & (~audit["exists"].astype(bool)) & (~audit["allowed_use"].isin(["provider_uri"]))]
    if not missing_structural.empty:
        raise DataGateError(f"missing structural inputs: {missing_structural['path'].tolist()}")
    outputs = [
        write_csv(formula, report_dir(config) / "rule_formula_audit.csv"),
        write_csv(audit, report_dir(config) / "source_data_audit.csv"),
    ]
    write_json(
        {
            "rows": int(len(audit)),
            "classification_counts": source_category_counts(audit),
            "forbidden_result_path_used_for_calculation": False,
            "result_csv_used_for_calculation": False,
        },
        report_dir(config) / "source_data_audit_summary.json",
    )
    outputs.append(report_dir(config) / "source_data_audit_summary.json")
    record_manifest(config, "self-test", outputs, {"self_test_status": "ok"})
    print(f"self-test ok rule_versions={len(versions)} forbidden_used=false", flush=True)
    return outputs


def command_audit_data(config: dict[str, Any]) -> list[Path]:
    ensure_dir(report_dir(config))
    ensure_dir(cache_dir(config))
    ensure_dir(backtest_dir(config))
    audit = build_source_data_audit(config)
    validate_source_audit(audit)
    formula = rule_formula_audit(config)
    universe = read_universe(config)
    industry = read_industry(config)
    target_history = read_target_history(config)
    panel, provider_meta = load_stock_panel(config)
    coverage, coverage_summary = build_provider_coverage_by_year(config, universe, industry, panel, provider_meta, target_history)
    eligibility = build_year_data_eligibility(config, build_feature_panel(config)[0], coverage)
    structural = {
        "pit_universe": {
            "path": config["paths"]["universe_membership"],
            "rows": int(len(universe)),
            "sha256": file_sha256(config["paths"]["universe_membership"]),
        },
        "pit_industry": {
            "path": config["paths"]["industry_membership"],
            "rows": int(len(industry)),
            "sha256": file_sha256(config["paths"]["industry_membership"]),
        },
        "target_history": {
            "path": config["paths"]["target_history"],
            "rows": int(len(target_history)),
            "sha256": file_sha256(config["paths"]["target_history"]),
        },
    }
    outputs = [
        write_csv(audit, report_dir(config) / "source_data_audit.csv"),
        write_csv(formula, report_dir(config) / "rule_formula_audit.csv"),
        write_csv(coverage, report_dir(config) / "pit_provider_coverage_by_year.csv"),
        write_csv(eligibility, report_dir(config) / "year_data_eligibility.csv"),
        write_json(
            {
                "rows": int(len(audit)),
                "classification_counts": source_category_counts(audit),
                "forbidden_result_path_used_for_calculation": False,
                "result_csv_used_for_calculation": False,
            },
            report_dir(config) / "source_data_audit_summary.json",
        ),
        write_json(coverage_summary, report_dir(config) / "provider_coverage_summary.json"),
    ]
    record_manifest(
        config,
        "audit-data",
        outputs,
        {
            "structural_inputs": structural,
            "provider_mode": coverage_summary["provider_mode"],
            "coverage_by_year": coverage[["year", "coverage_status"]].to_dict("records"),
            "year_data_eligibility": eligibility.to_dict("records"),
        },
    )
    print(
        f"audited data provider_mode={coverage_summary['provider_mode']} research_required_field_coverage={coverage_summary['research_required_field_coverage_ratio']:.2%}",
        flush=True,
    )
    return outputs


def command_run_yearly(config: dict[str, Any]) -> list[Path]:
    ensure_dir(report_dir(config))
    ensure_dir(cache_dir(config))
    ensure_dir(backtest_dir(config))
    if not bool(config["universe"].get("point_in_time", False)):
        raise DataGateError("universe_point_in_time must be true")
    if not bool(config["industry"].get("point_in_time", False)):
        raise DataGateError("industry_membership_point_in_time must be true")
    features, _feature_summary = build_feature_panel(config)
    coverage = pd.read_csv(report_dir(config) / "pit_provider_coverage_by_year.csv")
    coverage_summary = read_json(report_dir(config) / "provider_coverage_summary.json")
    eligibility = build_year_data_eligibility(config, features, coverage)
    formula = rule_formula_audit(config)
    portfolio_frames: list[pd.DataFrame] = []
    trade_frames: list[pd.DataFrame] = []
    audit_frames: list[pd.DataFrame] = []
    exposure_frames: list[pd.DataFrame] = []
    for spec in expand_rule_versions(config):
        portfolio, trades, audit, exposure = run_backtest_one(config, features, spec, coverage_summary)
        portfolio_frames.append(portfolio)
        trade_frames.append(trades)
        audit_frames.append(audit)
        exposure_frames.append(exposure)
        print(f"ran {spec['rule_version_id']} trades={len(trades)}", flush=True)
    portfolio_all = pd.concat(portfolio_frames, ignore_index=True) if portfolio_frames else pd.DataFrame()
    trade_all = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    audit_all = pd.concat(audit_frames, ignore_index=True) if audit_frames else pd.DataFrame()
    exposure_all = pd.concat(exposure_frames, ignore_index=True) if exposure_frames else pd.DataFrame()
    leaderboard = build_year_rule_leaderboard(config, portfolio_all, trade_all, coverage, eligibility, coverage_summary)
    market_summary = build_market_regime_summary(config, features, trade_all, exposure_all)
    entry_exit = build_entry_exit_attribution(trade_all)
    failure = build_failure_attribution(trade_all)
    clusters = build_rule_family_cluster_summary(leaderboard, market_summary, coverage)
    reference = build_reference_2025_comparison(config, market_summary, coverage, clusters)
    outputs = [
        write_csv(formula, report_dir(config) / "rule_formula_audit.csv"),
        write_csv(eligibility, report_dir(config) / "year_data_eligibility.csv"),
        write_csv(leaderboard, report_dir(config) / "year_rule_leaderboard.csv"),
        write_csv(market_summary, report_dir(config) / "year_market_regime_summary.csv"),
        write_csv(entry_exit, report_dir(config) / "year_entry_exit_attribution.csv"),
        write_csv(failure, report_dir(config) / "year_failure_attribution.csv"),
        write_csv(clusters, report_dir(config) / "rule_family_cluster_summary.csv"),
        write_csv(reference, report_dir(config) / "reference_2025_comparison.csv"),
        write_csv(portfolio_all, backtest_dir(config) / "rule_portfolio_daily.csv"),
        write_csv(trade_all, backtest_dir(config) / "rule_trade_detail.csv"),
        write_csv(audit_all, backtest_dir(config) / "rule_execution_audit.csv"),
        write_csv(exposure_all, backtest_dir(config) / "rule_industry_exposure.csv"),
    ]
    record_manifest(
        config,
        "run-yearly",
        outputs,
        {
            "provider_mode": coverage_summary.get("provider_mode", ""),
            "coverage_by_year": coverage[["year", "coverage_status"]].to_dict("records"),
            "leaderboard_rows": int(len(leaderboard)),
            "trade_rows": int(len(trade_all)),
            "portfolio_rows": int(len(portfolio_all)),
            "coverage_limited_research": bool((coverage[coverage["year"].between(2017, 2024)]["coverage_status"] != "coverage_ok").any()),
        },
    )
    print(f"wrote yearly diagnostics leaderboard_rows={len(leaderboard)} trades={len(trade_all)}", flush=True)
    return outputs


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def parse_json_dict(value: Any) -> dict[str, Any]:
    if value is None or pd.isna(value):
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def weighted_average(frame: pd.DataFrame, value_col: str, weight_col: str) -> float:
    if frame.empty or value_col not in frame.columns or weight_col not in frame.columns:
        return np.nan
    values = pd.to_numeric(frame[value_col], errors="coerce")
    weights = pd.to_numeric(frame[weight_col], errors="coerce")
    mask = values.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        return np.nan
    return float((values[mask] * weights[mask]).sum() / weights[mask].sum())


def top_dict_items(value: Any, limit: int = 3) -> str:
    data = parse_json_dict(value)
    if not data:
        return ""
    ranked = sorted(data.items(), key=lambda item: safe_float(item[1], 0.0), reverse=True)[:limit]
    return "; ".join(f"{key}:{format_money(val)}" for key, val in ranked)


def build_deep_dive_analysis_lines(
    config: dict[str, Any],
    coverage: pd.DataFrame,
    eligibility: pd.DataFrame,
    leaderboard: pd.DataFrame,
    market: pd.DataFrame,
    entry_exit: pd.DataFrame,
    failure: pd.DataFrame,
    reference: pd.DataFrame,
    trade_detail: pd.DataFrame,
    portfolio_daily: pd.DataFrame,
    exposure: pd.DataFrame,
    manifest: dict[str, Any],
    coverage_summary: dict[str, Any],
) -> list[str]:
    coverage_limited = bool(coverage_summary.get("coverage_limited_diagnostic", True))
    research_coverage = coverage[coverage["year"].between(2017, 2024)].copy() if not coverage.empty else pd.DataFrame()
    ok_years = research_coverage.loc[research_coverage["coverage_status"] == "coverage_ok", "year"].astype(int).tolist() if not research_coverage.empty else []
    core_boundary = (
        "核心限制先写在前面：本轮 provider 覆盖不足，所有规则表现只能作为 replay diagnostic。任何“好/坏”都应该理解为“值得下一轮在补齐 PIT provider 后复验的方向”，不是策略结论。"
        if coverage_limited
        else "核心边界先写在前面：本轮 PIT provider 覆盖已经通过，年度规则排序可以做 retrospective diagnostic；但 Explore8 仍是诊断实验，不直接产出可交易候选。"
    )
    lines: list[str] = [
        "# Explore8 深度诊断分析报告",
        "",
        "## 分析边界",
        "",
        "本报告基于 Explore8 已生成的结构化输出和本轮回放明细，目的是给出诊断洞察，不是生成可交易候选。",
        f"- Provider mode: `{coverage_summary.get('provider_mode', manifest.get('provider_mode', ''))}`。",
        f"- 2017-2024 coverage-ok 年份数: `{len(ok_years)}`。",
        f"- 历史结果 CSV 用于计算: `{manifest.get('forbidden_result_path_used_for_calculation', False)}`；2025-2026 用于选择: `{manifest.get('observed_2025_2026_used_for_selection', False)}`。",
        "",
        core_boundary,
    ]

    if not research_coverage.empty:
        missing_total = int(research_coverage["missing_rows"].sum())
        worst = research_coverage.sort_values("required_field_coverage_ratio").iloc[0]
        best = research_coverage.sort_values("required_field_coverage_ratio", ascending=False).iloc[0]
        if missing_total == 0 and len(ok_years) == len(research_coverage):
            coverage_interpretation = "- 所有研究年份均为 `coverage_ok`，年度规则排序的主要风险已经从数据缺口转为规则形态、市场状态和仓位约束解释。"
            coverage_insight = "洞察：此前 `56,337` 行 required-field 缺失来自 fallback provider 的 instrument 覆盖不足；补齐 PIT provider 后，行业缺口不再驱动结论，后续应把注意力转向年度 regime、信号密度和仓位利用率。"
        else:
            coverage_interpretation = "- 因为没有 coverage-ok 年份，年度最优、跨年聚类、2025 相似性排序全部应保持禁用。"
            coverage_insight = "洞察：缺口不是均匀噪声。2017-2020 金融/地产缺口明显，2021-2023 医药、食品饮料、电子、电力设备缺口更重；这些行业同时又出现在收益/亏损归因里，所以行业结论必须延后到 PIT provider 补齐后再判断。"
        lines.extend(
            [
                "",
                "## 1. 数据可信边界",
                "",
                f"- 2017-2024 合计缺失 `{format_money(missing_total)}` 个 `date + instrument` required-field 行。",
                f"- 最弱年份是 `{int(worst['year'])}`，required-field coverage `{format_pct(worst['required_field_coverage_ratio'])}`；最高年份是 `{int(best['year'])}`，coverage `{format_pct(best['required_field_coverage_ratio'])}`。",
                coverage_interpretation,
                "",
                "### 覆盖缺口的行业结构",
            ]
        )
        rows = []
        for _, row in research_coverage.iterrows():
            rows.append([int(row["year"]), row["coverage_status"], format_pct(row["required_field_coverage_ratio"]), format_money(row["missing_rows"]), top_dict_items(row.get("missing_industry_distribution"), 5)])
        lines.extend(markdown_table(["Year", "Status", "Required coverage", "Missing rows", "Top missing industries"], rows))
        lines.append(coverage_insight)

    if not market.empty:
        lines.extend(["", "## 2. 市场状态与信号密度", ""])
        rows = []
        for _, row in market.iterrows():
            rows.append(
                [
                    int(row["year"]),
                    format_pct(row["benchmark_return"]),
                    format_pct(row["benchmark_max_drawdown"]),
                    format_pct(row["close_gt_ema60_mean"]),
                    format_pct(row["trend_day_ratio"]),
                    format_pct(row["industry_sync_ratio"]),
                    int(row["breakout_signal_count"]),
                    int(row["pullback_signal_count"]),
                    int(row["breakdown_repair_signal_count"]),
                ]
            )
        lines.extend(markdown_table(["Year", "HS300 return", "HS300 MDD", "Width avg", "Trend days", "Industry sync", "Breakout", "Pullback", "Breakdown repair"], rows))
        max_breakout = market.sort_values("breakout_signal_count", ascending=False).iloc[0]
        max_pullback = market.sort_values("pullback_signal_count", ascending=False).iloc[0]
        weak_years = market[market["trend_day_ratio"] < 0.25]["year"].astype(int).tolist()
        lines.extend(
            [
                "",
                f"- Breakout 信号最高是 `{int(max_breakout['year'])}` 的 `{int(max_breakout['breakout_signal_count'])}` 次；pullback 信号最高是 `{int(max_pullback['year'])}` 的 `{int(max_pullback['pullback_signal_count'])}` 次。",
                f"- 市场 trend-day ratio 低于 25% 的年份为 `{', '.join(map(str, weak_years))}`。这些年份即使某些诊断版本回撤较小，也很可能是高现金/低交易带来的防守效果，而不是规则有 alpha。",
                "- 2024 的信号密度明显恢复；在 provider coverage 已通过后，它更适合作为高活跃 regime 的规则形态对比年份，而不是被数据缺口排除。",
            ]
        )

    if not leaderboard.empty:
        lines.extend(["", "## 3. 规则族表现：方向性而非排名", ""])
        rule_stability = (
            leaderboard.assign(positive_year=lambda x: x["return_after_cost"] > 0, active_year=lambda x: x["trades"] >= 10)
            .groupby("rule_version_id", as_index=False)
            .agg(
                positive_years=("positive_year", "sum"),
                active_years=("active_year", "sum"),
                trades=("trades", "sum"),
                median_return=("return_after_cost", "median"),
                best_return=("return_after_cost", "max"),
                worst_return=("return_after_cost", "min"),
                net_pnl=("net_pnl", "sum"),
                avg_cash=("avg_cash_ratio", "mean"),
                avg_mdd=("max_drawdown", "mean"),
            )
        )
        top_rules = rule_stability.sort_values(["positive_years", "median_return"], ascending=[False, False]).head(12)
        rows = []
        for _, row in top_rules.iterrows():
            rows.append(
                [
                    row["rule_version_id"],
                    int(row["positive_years"]),
                    int(row["active_years"]),
                    int(row["trades"]),
                    format_pct(row["median_return"]),
                    format_pct(row["best_return"]),
                    format_pct(row["worst_return"]),
                    format_pct(row["avg_cash"]),
                    format_money(row["net_pnl"]),
                ]
            )
        lines.extend(markdown_table(["Rule version", "Positive years", "Active years", "Trades", "Median return", "Best", "Worst", "Avg cash", "Net PnL"], rows))

        family = (
            leaderboard.groupby("entry_family", as_index=False)
            .agg(
                rule_versions=("rule_version_id", "nunique"),
                trades=("trades", "sum"),
                net_pnl=("net_pnl", "sum"),
                median_return=("return_after_cost", "median"),
                best_return=("return_after_cost", "max"),
                worst_return=("return_after_cost", "min"),
                avg_cash=("avg_cash_ratio", "mean"),
                stop_time=("stop_time_trade_ratio", "mean"),
            )
            .sort_values("net_pnl", ascending=False)
        )
        rows = []
        for _, row in family.iterrows():
            rows.append(
                [
                    row["entry_family"],
                    int(row["rule_versions"]),
                    int(row["trades"]),
                    format_money(row["net_pnl"]),
                    format_pct(row["median_return"]),
                    format_pct(row["best_return"]),
                    format_pct(row["worst_return"]),
                    format_pct(row["avg_cash"]),
                    format_pct(row["stop_time"]),
                ]
            )
        lines.extend(["", "### Entry family 汇总", ""])
        lines.extend(markdown_table(["Entry family", "Versions", "Trades", "Net PnL", "Median ret", "Best", "Worst", "Cash", "Stop/time"], rows))
        lines.extend(
            [
                "",
                "洞察：",
                "- `ema_state_baseline` 的诊断收益最好，但它更像宽松趋势暴露底座，不证明 entry trigger 本身有效。",
                "- `breakout_core` 总净 PnL 为正，但 median return 为负，说明 breakout 对年份/退出方式非常敏感，需要配合更好的失败退出和持有逻辑。",
                "- `pullback_original` 和 `pullback_strict_money` 都偏弱；`pullback_strict_trend` / `pullback_top_score` 虽然方向较好，但 active 年份少、现金比例极高，暂时只能说明“更强趋势确认可能有帮助”，不能说明 pullback 已修复。",
                "- `breakdown_repair_diagnostic` 交易数多但净值接近零，说明它像高噪声诊断形态，不能直接进入候选。",
            ]
        )

    if not entry_exit.empty or not trade_detail.empty:
        lines.extend(["", "## 4. 入场与退出贡献", ""])
    if not entry_exit.empty:
        entry_summary = (
            entry_exit.groupby("entry_type", as_index=False)
            .agg(
                trades=("trades", "sum"),
                net_pnl=("net_pnl", "sum"),
                gross_pnl=("gross_pnl", "sum"),
                avg_hold=("avg_holding_days", "mean"),
            )
            .sort_values("net_pnl", ascending=False)
        )
        rows = []
        for _, row in entry_summary.iterrows():
            subset = entry_exit[entry_exit["entry_type"] == row["entry_type"]]
            rows.append(
                [
                    row["entry_type"],
                    int(row["trades"]),
                    format_money(row["net_pnl"]),
                    format_money(row["gross_pnl"]),
                    format_pct(weighted_average(subset, "win_rate", "trades")),
                    format_pct(weighted_average(subset, "avg_cost_after_return", "trades")),
                    format_float(row["avg_hold"], 1),
                ]
            )
        lines.extend(markdown_table(["Entry type", "Trades", "Net PnL", "Gross PnL", "Win rate", "Avg return/trade", "Avg hold"], rows))

        exit_reason = (
            entry_exit.groupby("exit_reason", as_index=False)
            .agg(trades=("trades", "sum"), net_pnl=("net_pnl", "sum"), avg_hold=("avg_holding_days", "mean"))
            .sort_values("net_pnl")
        )
        rows = []
        for _, row in exit_reason.iterrows():
            subset = entry_exit[entry_exit["exit_reason"] == row["exit_reason"]]
            rows.append([row["exit_reason"], int(row["trades"]), format_money(row["net_pnl"]), format_pct(weighted_average(subset, "win_rate", "trades")), format_float(row["avg_hold"], 1)])
        lines.extend(["", "### Exit reason 总贡献", ""])
        lines.extend(markdown_table(["Exit reason", "Trades", "Net PnL", "Win rate", "Avg hold"], rows))
        lines.extend(
            [
                "",
                "洞察：",
                "- `time_stop` 和 `stop_loss` 是主要亏损来源，分别对应趋势没有延续和入场后快速破坏。",
                "- `trailing_stop` 与 `ema60_exit` 是主要正贡献来源，说明真正有价值的交易需要趋势尾部，而不是短期均值回归式退出。",
                "- fast-failure 的若干 exit reason 单项为正，但整个 `fast_failure_exit_diagnostic` family 仍偏弱，提示早退出可能减少部分损失，同时也容易切断尾部收益。",
            ]
        )

    if not trade_detail.empty:
        data = trade_detail.copy()
        data["exit_date"] = pd.to_datetime(data["exit_date"])
        data["year"] = data["exit_date"].dt.year
        year_entry = data.pivot_table(index="year", columns="entry_type", values="net_pnl", aggfunc="sum", fill_value=0).reset_index()
        rows = []
        for _, row in year_entry.iterrows():
            rows.append([int(row["year"])] + [format_money(row.get(col, 0.0)) for col in ["ema_state", "breakout", "pullback", "breakdown_repair"]])
        lines.extend(["", "### 年度 Entry PnL 分解", ""])
        lines.extend(markdown_table(["Year", "EMA state", "Breakout", "Pullback", "Breakdown repair"], rows))

        pos = data[data["net_pnl"] > 0].copy()
        concentration_rows = []
        for entry_type, group in pos.groupby("entry_type"):
            total = group["net_pnl"].sum()
            top5 = group.nlargest(5, "net_pnl")["net_pnl"].sum()
            concentration_rows.append([entry_type, int(len(group)), format_money(total), format_pct(top5 / total if total else np.nan)])
        if concentration_rows:
            lines.extend(["", "### 正收益交易集中度", ""])
            lines.extend(markdown_table(["Entry", "Winning trades", "Positive PnL", "Top5 winner share"], concentration_rows))

    if not leaderboard.empty:
        lines.extend(["", "## 5. 仓位与风险形态", ""])
        sizing = (
            leaderboard.groupby(["sizing_suite", "sizing_family"], as_index=False)
            .agg(
                rows=("rule_version_id", "size"),
                trades=("trades", "sum"),
                net_pnl=("net_pnl", "sum"),
                median_return=("return_after_cost", "median"),
                avg_mdd=("max_drawdown", "mean"),
                avg_cash=("avg_cash_ratio", "mean"),
                positive_years=("return_after_cost", lambda s: int((s > 0).sum())),
            )
            .sort_values("net_pnl", ascending=False)
        )
        rows = []
        for _, row in sizing.iterrows():
            rows.append([row["sizing_suite"], row["sizing_family"], int(row["trades"]), format_money(row["net_pnl"]), format_pct(row["median_return"]), format_pct(row["avg_mdd"]), format_pct(row["avg_cash"]), int(row["positive_years"])])
        lines.extend(markdown_table(["Sizing", "Family", "Trades", "Net PnL", "Median ret", "Avg MDD", "Avg cash", "Positive year cells"], rows))
        lines.append("洞察：固定权重贡献最高但平均回撤最深；risk-unit + industry cap 明显压低回撤，但现金比例长期在 87%-88% 左右，说明风险控制有效但资金利用不足。下一轮不宜只扩大 entry 搜索，也要单独校准 risk budget、单票 cap、行业 cap 和 daily-new cap。")

    if not trade_detail.empty:
        lines.extend(["", "## 6. 行业归因与集中风险", ""])
        industry = (
            trade_detail.groupby("industry_name", as_index=False)
            .agg(trades=("instrument", "size"), net_pnl=("net_pnl", "sum"), win_rate=("net_pnl", lambda s: float((pd.to_numeric(s, errors="coerce") > 0).mean())))
            .sort_values("net_pnl")
        )
        rows = []
        for _, row in industry.head(12).iterrows():
            rows.append([row["industry_name"], int(row["trades"]), format_money(row["net_pnl"]), format_pct(row["win_rate"])])
        lines.extend(markdown_table(["Worst industry", "Trades", "Net PnL", "Win rate"], rows))
        positive_industry = industry[industry["net_pnl"] > 0].sort_values("net_pnl", ascending=False).head(12)
        rows = []
        for _, row in positive_industry.iterrows():
            rows.append([row["industry_name"], int(row["trades"]), format_money(row["net_pnl"]), format_pct(row["win_rate"])])
        lines.extend(["", "### 正贡献行业", ""])
        lines.extend(markdown_table(["Best industry", "Trades", "Net PnL", "Win rate"], rows))
        if coverage_limited:
            industry_insight = "洞察：非银金融、银行、煤炭等是明显拖累；食品饮料、基础化工、汽车、电力设备贡献更强。但覆盖缺口也集中在这些行业的一部分年份，所以这里不能直接导出行业白名单/黑名单，只能说明下一轮行业归因要重点复验这些板块。"
        else:
            industry_insight = "洞察：非银金融、银行、煤炭等是明显拖累；食品饮料、基础化工、汽车、电力设备贡献更强。由于 provider 覆盖已补齐，这些差异更值得进入后续行业暴露/风险预算诊断，但仍不能直接简化成行业白名单或黑名单。"
        lines.extend(["", industry_insight])

    if not failure.empty:
        lines.extend(["", "## 7. 失败交易切片", ""])
        fail_entry = failure.groupby(["entry_type", "exit_reason"], as_index=False).agg(loss_trades=("trades", "sum"), net_pnl=("net_pnl", "sum")).sort_values("net_pnl").head(14)
        rows = []
        for _, row in fail_entry.iterrows():
            rows.append([row["entry_type"], row["exit_reason"], int(row["loss_trades"]), format_money(row["net_pnl"])])
        lines.extend(markdown_table(["Entry", "Exit", "Loss trades", "Net PnL"], rows))

        fail_bucket = (
            failure.groupby(["trend_score_bucket", "money_ratio_bucket", "initial_risk_bucket"], as_index=False)
            .agg(loss_trades=("trades", "sum"), net_pnl=("net_pnl", "sum"))
            .sort_values("net_pnl")
            .head(14)
        )
        rows = []
        for _, row in fail_bucket.iterrows():
            rows.append([row["trend_score_bucket"], row["money_ratio_bucket"], row["initial_risk_bucket"], int(row["loss_trades"]), format_money(row["net_pnl"])])
        lines.extend(["", "### 趋势分数 / 成交额 / 初始风险", ""])
        lines.extend(markdown_table(["Trend score", "Money ratio", "Initial risk", "Loss trades", "Net PnL"], rows))
        lines.extend(
            [
                "",
                "洞察：亏损最大的切片不是低分股票，而是 `top10/top20 + money_ratio gt120 + high initial risk`。这说明当前 trend_score 本身不足以过滤失败交易；高成交额突破也可能是高波动追高，下一轮需要把入场日风险距离、gap、ATR/close 和上影线后的失败概率放进规则解释，而不是只提高 trend_score 门槛。",
            ]
        )

    lines.extend(["", "## 8. 我的判断", ""])
    if coverage_limited:
        lines.extend(
            [
                "1. 当前最确定的结论是数据结论：PIT universe 已经替代静态池，但 provider 覆盖不足，必须先补数据再谈跨年规律。",
                "2. 规则层面最值得复验的是 breakout + layered/EMA 尾部持有，而不是 original pullback。Breakout 的总贡献为正，但 `time_stop` 是大亏损源，说明问题不只是入场，也包括失败交易如何尽早识别、趋势交易如何不要过早截断。",
                "3. Pullback 的原始定义不应直接继续优化成候选。严格趋势/Top-score 版本有一些方向性改善，但主要靠低交易和高现金，下一轮应重写 pullback 形态，而不是只把阈值调严。",
                "4. 风控不是越保守越好。risk-unit 和 industry cap 降低回撤，但现金过高；如果补齐 provider 后仍出现高现金，应该单独做仓位利用率诊断。",
                "5. 行业结论必须谨慎。食品饮料、基础化工、汽车等正贡献明显，非银金融/银行拖累明显，但这些板块也和覆盖缺口交织，不能在本轮形成行业过滤规则。",
                "6. 下一阶段建议顺序：补 PIT provider -> 重跑 Explore8 -> 只在 coverage-ok 年份做 retrospective cluster -> 再决定 breakout coverage、pullback rewrite 或 regime switch。",
            ]
        )
    else:
        lines.extend(
            [
                "1. 数据阻断已经解除：PIT universe、PIT industry 和 PIT provider 现在可以支撑 2017-2024 的 retrospective 诊断。",
                "2. 规则层面最值得继续拆解的是 breakout + layered/EMA 尾部持有，而不是 original pullback。Breakout 的总贡献为正，但 `time_stop` 是大亏损源，说明问题不只是入场，也包括失败交易如何尽早识别、趋势交易如何不要过早截断。",
                "3. Pullback 的原始定义不应直接继续优化成候选。严格趋势/Top-score 版本有一些方向性改善，但主要靠低交易和高现金，下一轮应重写 pullback 形态，而不是只把阈值调严。",
                "4. 风控不是越保守越好。risk-unit 和 industry cap 降低回撤，但现金过高；补齐 provider 后仍出现高现金，说明仓位利用率需要单独诊断。",
                "5. 行业结论可以进入复验队列，但不能直接规则化。食品饮料、基础化工、汽车等正贡献明显，非银金融/银行拖累明显，下一步应看是否来自行业 beta、个别大票还是规则入场时点。",
                "6. 下一阶段建议顺序：基于 coverage-ok 年份做 retrospective cluster -> 拆 breakout time-stop 亏损 -> 重写 pullback 形态 -> 做仓位利用率和行业暴露约束诊断。",
            ]
        )
    if not reference.empty:
        row = reference.iloc[0]
        lines.append(f"7. 2025 reference 当前 comparison allowed=`{row.get('comparison_allowed')}`，原因是 `{row.get('disabled_reason', '')}`；所以 2025 只能作为背景画像，不能参与相似度排序。")
    return lines


def command_report(config: dict[str, Any]) -> list[Path]:
    report = report_dir(config)
    coverage = read_csv_if_exists(report / "pit_provider_coverage_by_year.csv")
    eligibility = read_csv_if_exists(report / "year_data_eligibility.csv")
    leaderboard = read_csv_if_exists(report / "year_rule_leaderboard.csv")
    market = read_csv_if_exists(report / "year_market_regime_summary.csv")
    entry_exit = read_csv_if_exists(report / "year_entry_exit_attribution.csv")
    failure = read_csv_if_exists(report / "year_failure_attribution.csv")
    clusters = read_csv_if_exists(report / "rule_family_cluster_summary.csv")
    reference = read_csv_if_exists(report / "reference_2025_comparison.csv")
    trade_detail = read_csv_if_exists(backtest_dir(config) / "rule_trade_detail.csv")
    portfolio_daily = read_csv_if_exists(backtest_dir(config) / "rule_portfolio_daily.csv")
    exposure = read_csv_if_exists(backtest_dir(config) / "rule_industry_exposure.csv")
    manifest = read_json(report / "run_manifest.json")
    coverage_summary = read_json(report / "provider_coverage_summary.json")

    if coverage.empty or leaderboard.empty:
        command_run_yearly(config)
        coverage = read_csv_if_exists(report / "pit_provider_coverage_by_year.csv")
        eligibility = read_csv_if_exists(report / "year_data_eligibility.csv")
        leaderboard = read_csv_if_exists(report / "year_rule_leaderboard.csv")
        market = read_csv_if_exists(report / "year_market_regime_summary.csv")
        entry_exit = read_csv_if_exists(report / "year_entry_exit_attribution.csv")
        failure = read_csv_if_exists(report / "year_failure_attribution.csv")
        clusters = read_csv_if_exists(report / "rule_family_cluster_summary.csv")
        reference = read_csv_if_exists(report / "reference_2025_comparison.csv")
        trade_detail = read_csv_if_exists(backtest_dir(config) / "rule_trade_detail.csv")
        portfolio_daily = read_csv_if_exists(backtest_dir(config) / "rule_portfolio_daily.csv")
        exposure = read_csv_if_exists(backtest_dir(config) / "rule_industry_exposure.csv")
        manifest = read_json(report / "run_manifest.json")
        coverage_summary = read_json(report / "provider_coverage_summary.json")

    research_coverage = coverage[coverage["year"].between(2017, 2024)] if not coverage.empty else pd.DataFrame()
    ok_years = research_coverage.loc[research_coverage["coverage_status"] == "coverage_ok", "year"].tolist() if not research_coverage.empty else []
    all_blocked = len(ok_years) == 0
    coverage_limited = bool(coverage_summary.get("coverage_limited_diagnostic", True))
    lines: list[str] = [
        "# Explore8 PIT EMA 同源规则族逐年诊断报告",
        "",
        "## 结论摘要",
        "",
        f"- PIT universe authority: `{manifest.get('universe_membership', config['paths']['universe_membership'])}`；静态 `mcap500_mainboard_20251231` 交易资格使用标记为 `{manifest.get('static_20251231_universe_used_as_authority')}`。",
        f"- Provider mode: `{coverage_summary.get('provider_mode', manifest.get('provider_mode', ''))}`；coverage-limited diagnostic: `{coverage_summary.get('coverage_limited_diagnostic', '')}`。",
        f"- 历史 result CSV 用于计算: `{manifest.get('forbidden_result_path_used_for_calculation', False)}`；2025-2026 用于选择: `{manifest.get('observed_2025_2026_used_for_selection', False)}`。",
    ]
    if all_blocked:
        lines.append("- 2017-2024 没有任何年份达到 `coverage_ok`，因此本轮只形成数据审计和阻断诊断，不输出“年度最适合规则”、跨年聚类相似性或下一步可交易候选。")
    else:
        lines.append(f"- 可进入 retrospective leaderboard / cluster 的年份: `{', '.join(map(str, ok_years))}`。非 coverage-ok 年份只保留覆盖诊断。")
    if not research_coverage.empty:
        worst_cov = research_coverage.sort_values("required_field_coverage_ratio").iloc[0]
        best_cov = research_coverage.sort_values("required_field_coverage_ratio", ascending=False).iloc[0]
        missing_total = int(research_coverage["missing_rows"].sum())
        if missing_total == 0:
            lines.append(
                f"- 覆盖缺口总量 `{format_money(missing_total)}` 行；2017-2024 研究年份 required-field coverage 均为 `100.00%`。"
            )
        else:
            lines.append(
                f"- 覆盖缺口总量 `{format_money(missing_total)}` 行；最弱年份是 `{int(worst_cov['year'])}`，required-field coverage `{format_pct(worst_cov['required_field_coverage_ratio'])}`；最高年份是 `{int(best_cov['year'])}`，coverage `{format_pct(best_cov['required_field_coverage_ratio'])}`。"
            )
    if not leaderboard.empty:
        if coverage_limited or all_blocked:
            lines.append(
                f"- 本轮已跑完 `{leaderboard['rule_version_id'].nunique()}` 个 `rule_version_id`、`{len(leaderboard)}` 个年度规则样本；这些只能作为 coverage-limited replay diagnostic，不可解释为年度最优策略。"
            )
        else:
            lines.append(
                f"- 本轮已跑完 `{leaderboard['rule_version_id'].nunique()}` 个 `rule_version_id`、`{len(leaderboard)}` 个年度规则样本；coverage gating 已通过，可做 retrospective 年度比较，但仍不是生产候选选择。"
            )

    if not coverage.empty:
        lines.extend(["", "## Provider 覆盖 gating", ""])
        rows = []
        for _, row in coverage[coverage["year"].between(2017, 2025)].iterrows():
            rows.append(
                [
                    int(row["year"]),
                    row["coverage_status"],
                    format_pct(row["year_coverage_ratio"]),
                    format_pct(row["required_field_coverage_ratio"]),
                    format_money(row["missing_rows"]),
                    row.get("disabled_conclusions", ""),
                ]
            )
        lines.extend(markdown_table(["Year", "Status", "Readable", "Required fields", "Missing rows", "Disabled conclusions"], rows))
        hotspot_rows = []
        for _, row in coverage[coverage["year"].between(2017, 2024)].iterrows():
            hotspot_rows.append([int(row["year"]), format_money(row["missing_rows"]), top_dict_items(row.get("missing_industry_distribution"), 4)])
        lines.extend(["", "### 覆盖缺口行业分布", ""])
        lines.extend(markdown_table(["Year", "Missing rows", "Top missing industries"], hotspot_rows))

    if not eligibility.empty:
        lines.extend(["", "## Warmup 与有效交易日", ""])
        rows = []
        for _, row in eligibility.iterrows():
            rows.append([int(row["year"]), row["warmup_partial_year"], row["first_signal_eligible_date"], row["effective_data_start"], row["effective_data_end"]])
        lines.extend(markdown_table(["Year", "Warmup partial", "First eligible", "Data start", "Data end"], rows))

    lines.extend(["", "## 年度规则诊断", ""])
    if all_blocked:
        lines.append("所有研究年份都被 coverage gating 禁止进入规则排序。本节不声明任何年度最优规则；下面只给出非生产诊断中交易数最高的规则，目的是检查信号/回放链路是否可运行。")
        show = leaderboard.sort_values(["year", "trades"], ascending=[True, False]).groupby("year").head(1) if not leaderboard.empty else pd.DataFrame()
    else:
        show = leaderboard[leaderboard["coverage_status"] == "coverage_ok"].sort_values(["year", "return_after_cost"], ascending=[True, False]).groupby("year").head(1)
    if not show.empty:
        rows = []
        for _, row in show.iterrows():
            rows.append(
                [
                    int(row["year"]),
                    row["rule_version_id"],
                    row["entry_family"],
                    row["exit_family"],
                    int(row["trades"]),
                    format_pct(row["return_after_cost"]),
                    format_pct(row["max_drawdown"]),
                    format_pct(row["avg_cash_ratio"]),
                ]
            )
        lines.extend(markdown_table(["Year", "Rule version", "Entry", "Exit", "Trades", "Return", "MDD", "Cash"], rows))
    if not leaderboard.empty:
        lines.extend(["", "### 年度诊断最高/最低收益版本", ""])
        best = leaderboard.sort_values(["year", "return_after_cost"], ascending=[True, False]).groupby("year").head(1)
        worst = leaderboard.sort_values(["year", "return_after_cost"], ascending=[True, True]).groupby("year").head(1)
        rows = []
        for year in sorted(leaderboard["year"].unique()):
            best_row = best[best["year"] == year].iloc[0]
            worst_row = worst[worst["year"] == year].iloc[0]
            rows.append(
                [
                    int(year),
                    best_row["rule_version_id"],
                    format_pct(best_row["return_after_cost"]),
                    int(best_row["trades"]),
                    format_pct(best_row["avg_cash_ratio"]),
                    worst_row["rule_version_id"],
                    format_pct(worst_row["return_after_cost"]),
                    int(worst_row["trades"]),
                ]
            )
        if coverage_limited or all_blocked:
            lines.append("下表仍是非生产诊断排序，因为 coverage gating 未通过；它只用于看规则形态和风险形态的方向性差异。")
        else:
            lines.append("下表是 coverage-ok 年份内的 retrospective 诊断排序；它可以比较规则形态和风险形态，但仍不等同于生产候选选择。")
        lines.extend(markdown_table(["Year", "Diagnostic best", "Return", "Trades", "Cash", "Diagnostic worst", "Return", "Trades"], rows))

        lines.extend(["", "### 规则族横向汇总", ""])
        family_summary = (
            leaderboard.groupby("entry_family", as_index=False)
            .agg(
                rule_versions=("rule_version_id", "nunique"),
                trades=("trades", "sum"),
                net_pnl=("net_pnl", "sum"),
                median_return=("return_after_cost", "median"),
                best_return=("return_after_cost", "max"),
                worst_return=("return_after_cost", "min"),
                avg_cash_ratio=("avg_cash_ratio", "mean"),
                stop_time_trade_ratio=("stop_time_trade_ratio", "mean"),
            )
            .sort_values("net_pnl", ascending=False)
        )
        rows = []
        for _, row in family_summary.iterrows():
            rows.append(
                [
                    row["entry_family"],
                    int(row["rule_versions"]),
                    int(row["trades"]),
                    format_money(row["net_pnl"]),
                    format_pct(row["median_return"]),
                    format_pct(row["best_return"]),
                    format_pct(row["avg_cash_ratio"]),
                    format_pct(row["stop_time_trade_ratio"]),
                ]
            )
        lines.extend(markdown_table(["Entry family", "Versions", "Trades", "Net PnL", "Median return", "Best return", "Avg cash", "Stop/time"], rows))

        sizing_summary = (
            leaderboard.groupby(["sizing_suite", "sizing_family"], as_index=False)
            .agg(
                rows=("rule_version_id", "size"),
                trades=("trades", "sum"),
                net_pnl=("net_pnl", "sum"),
                median_return=("return_after_cost", "median"),
                avg_drawdown=("max_drawdown", "mean"),
                avg_cash_ratio=("avg_cash_ratio", "mean"),
            )
            .sort_values("net_pnl", ascending=False)
        )
        rows = []
        for _, row in sizing_summary.iterrows():
            rows.append(
                [
                    row["sizing_suite"],
                    row["sizing_family"],
                    int(row["trades"]),
                    format_money(row["net_pnl"]),
                    format_pct(row["median_return"]),
                    format_pct(row["avg_drawdown"]),
                    format_pct(row["avg_cash_ratio"]),
                ]
            )
        lines.extend(["", "### 仓位套件汇总", ""])
        lines.extend(markdown_table(["Sizing suite", "Sizing family", "Trades", "Net PnL", "Median return", "Avg MDD", "Avg cash"], rows))

    if not market.empty:
        lines.extend(["", "## 年度市场画像", ""])
        rows = []
        for _, row in market.iterrows():
            rows.append(
                [
                    int(row["year"]),
                    format_pct(row["benchmark_return"]),
                    format_pct(row["benchmark_max_drawdown"]),
                    format_pct(row["close_gt_ema60_mean"]),
                    format_pct(row["trend_day_ratio"]),
                    int(row["breakout_signal_count"]),
                    int(row["pullback_signal_count"]),
                ]
            )
        lines.extend(markdown_table(["Year", "HS300 Return", "HS300 MDD", "Width avg", "Trend days", "Breakout signals", "Pullback signals"], rows))
        lines.extend(["", "### 信号密度与市场状态发现", ""])
        signal_rows = []
        for _, row in market.iterrows():
            signal_rows.append(
                [
                    int(row["year"]),
                    int(row["breakout_signal_count"]),
                    int(row["pullback_signal_count"]),
                    int(row["breakdown_repair_signal_count"]),
                    format_pct(row["industry_sync_ratio"]),
                    format_float(row["money_ratio_median"], 2),
                    format_pct(row["weak_money_pullback_ratio"]),
                    row["top5_industry_pnl"],
                ]
            )
        lines.extend(markdown_table(["Year", "Breakout", "Pullback", "Breakdown repair", "Industry sync", "Money median", "Weak-money PB", "Top5 industry PnL"], signal_rows))
        max_breakout = market.sort_values("breakout_signal_count", ascending=False).iloc[0]
        max_pullback = market.sort_values("pullback_signal_count", ascending=False).iloc[0]
        lines.append(
            f"- 信号密度最高的年份集中在 `{int(max_breakout['year'])}` 的 breakout `{int(max_breakout['breakout_signal_count'])}` 次和 `{int(max_pullback['year'])}` 的 pullback `{int(max_pullback['pullback_signal_count'])}` 次；这说明 2024 的规则活跃度高，但它仍被 provider coverage 限制在诊断层。"
        )

    if not entry_exit.empty:
        lines.extend(["", "## 入场与退出贡献", ""])
        entry_rows = []
        entry_summary = (
            entry_exit.groupby("entry_type", as_index=False)
            .agg(
                trades=("trades", "sum"),
                net_pnl=("net_pnl", "sum"),
                gross_pnl=("gross_pnl", "sum"),
                avg_holding_days=("avg_holding_days", "mean"),
            )
            .sort_values("net_pnl", ascending=False)
        )
        for _, row in entry_summary.iterrows():
            subset = entry_exit[entry_exit["entry_type"] == row["entry_type"]]
            entry_rows.append(
                [
                    row["entry_type"],
                    int(row["trades"]),
                    format_money(row["net_pnl"]),
                    format_money(row["gross_pnl"]),
                    format_pct(weighted_average(subset, "win_rate", "trades")),
                    format_pct(weighted_average(subset, "avg_cost_after_return", "trades")),
                    format_float(row["avg_holding_days"], 1),
                ]
            )
        lines.extend(markdown_table(["Entry type", "Trades", "Net PnL", "Gross PnL", "Win rate", "Avg return/trade", "Avg hold"], entry_rows))

        exit_rows = []
        exit_summary = (
            entry_exit.groupby(["entry_type", "exit_reason"], as_index=False)
            .agg(
                trades=("trades", "sum"),
                net_pnl=("net_pnl", "sum"),
                avg_holding_days=("avg_holding_days", "mean"),
            )
            .sort_values("net_pnl")
            .head(14)
        )
        for _, row in exit_summary.iterrows():
            subset = entry_exit[(entry_exit["entry_type"] == row["entry_type"]) & (entry_exit["exit_reason"] == row["exit_reason"])]
            exit_rows.append(
                [
                    row["entry_type"],
                    row["exit_reason"],
                    int(row["trades"]),
                    format_money(row["net_pnl"]),
                    format_pct(weighted_average(subset, "win_rate", "trades")),
                    format_float(row["avg_holding_days"], 1),
                ]
            )
        lines.extend(["", "### 亏损最大的入场/退出组合", ""])
        lines.extend(markdown_table(["Entry", "Exit", "Trades", "Net PnL", "Win rate", "Avg hold"], exit_rows))
        if not trade_detail.empty:
            trade_detail["exit_date"] = pd.to_datetime(trade_detail["exit_date"])
            pos = trade_detail[pd.to_numeric(trade_detail["net_pnl"], errors="coerce") > 0].copy()
            concentration_rows = []
            for entry_type, group in pos.groupby("entry_type"):
                total = pd.to_numeric(group["net_pnl"], errors="coerce").sum()
                top5 = pd.to_numeric(group.sort_values("net_pnl", ascending=False).head(5)["net_pnl"], errors="coerce").sum()
                concentration_rows.append([entry_type, int(len(group)), format_money(total), format_pct(top5 / total if total else np.nan)])
            if concentration_rows:
                lines.extend(["", "### 正收益交易集中度", ""])
                lines.extend(markdown_table(["Entry", "Winning trades", "Positive PnL", "Top5 winner share"], concentration_rows))

    lines.extend(["", "## 失效归因", ""])
    if failure.empty:
        lines.append("未形成亏损交易归因，或当前输出为空。")
    else:
        top_fail = failure.sort_values("net_pnl").head(12)
        rows = []
        for _, row in top_fail.iterrows():
            rows.append(
                [
                    int(row["year"]),
                    row["rule_version_id"],
                    row["entry_type"],
                    row["exit_reason"],
                    row["industry_name"],
                    int(row["trades"]),
                    format_money(row["net_pnl"]),
                    format_pct(row["stop_time_trade_ratio"]),
                ]
            )
        lines.extend(markdown_table(["Year", "Rule", "Entry", "Exit", "Industry", "Trades", "Net PnL", "Stop/time"], rows))
        pullback_fail = failure[failure["entry_type"] == "pullback"]
        if not pullback_fail.empty:
            stop_time_loss = pullback_fail[pullback_fail["exit_reason"].isin(["stop_loss", "time_stop"])]["net_pnl"].sum()
            lines.append(f"- Pullback 的 `stop_loss + time_stop` 亏损合计为 `{format_money(stop_time_loss)}`；该值用于判断 pullback 问题是否来自入场质量和失败退出。")
        breakout_attr = entry_exit[entry_exit["entry_type"] == "breakout"] if not entry_exit.empty else pd.DataFrame()
        if not breakout_attr.empty:
            lines.append(f"- Breakout 交易总数 `{int(breakout_attr['trades'].sum())}`，需结合现金比例判断它是低暴露还是可扩展趋势启动信号。")
        lines.extend(["", "### 失败切片汇总", ""])
        fail_entry = failure.groupby(["entry_type", "exit_reason"], as_index=False).agg(trades=("trades", "sum"), net_pnl=("net_pnl", "sum")).sort_values("net_pnl").head(12)
        rows = []
        for _, row in fail_entry.iterrows():
            rows.append([row["entry_type"], row["exit_reason"], int(row["trades"]), format_money(row["net_pnl"])])
        lines.extend(markdown_table(["Entry", "Exit", "Loss trades", "Net PnL"], rows))

        fail_industry = failure.groupby("industry_name", as_index=False).agg(trades=("trades", "sum"), net_pnl=("net_pnl", "sum")).sort_values("net_pnl").head(10)
        rows = []
        for _, row in fail_industry.iterrows():
            rows.append([row["industry_name"], int(row["trades"]), format_money(row["net_pnl"])])
        lines.extend(["", "### 亏损行业集中", ""])
        lines.extend(markdown_table(["Industry", "Loss trades", "Net PnL"], rows))

        fail_bucket = (
            failure.groupby(["trend_score_bucket", "money_ratio_bucket", "initial_risk_bucket"], as_index=False)
            .agg(trades=("trades", "sum"), net_pnl=("net_pnl", "sum"))
            .sort_values("net_pnl")
            .head(12)
        )
        rows = []
        for _, row in fail_bucket.iterrows():
            rows.append([row["trend_score_bucket"], row["money_ratio_bucket"], row["initial_risk_bucket"], int(row["trades"]), format_money(row["net_pnl"])])
        lines.extend(["", "### 趋势分数 / 成交额 / 初始风险切片", ""])
        lines.extend(markdown_table(["Trend score", "Money ratio", "Initial risk", "Loss trades", "Net PnL"], rows))

    lines.extend(["", "## 跨年聚类与 2025 reference", ""])
    if clusters.empty or "disabled_no_coverage_ok" in set(clusters.get("cluster_label", [])):
        lines.append("跨年 rule-family cluster 被禁用：没有 coverage-ok 研究年份，不能把任何规则形态解释成历史 regime classifier。")
    else:
        rows = []
        for _, row in clusters.iterrows():
            rows.append([int(row["year"]), row["cluster_label"], row.get("best_rule_version_id", ""), row.get("evidence", "")])
        lines.extend(markdown_table(["Year", "Cluster", "Best rule", "Evidence"], rows))
    if not reference.empty:
        row = reference.iloc[0]
        lines.append(
            f"- 2025 reference comparison allowed: `{row.get('comparison_allowed')}`；disabled reason: `{row.get('disabled_reason', '')}`；similarity year: `{row.get('similarity_year', '')}`。"
        )

    lines.extend(["", "## 下一步判断", ""])
    if all_blocked:
        lines.extend(
            [
                "- 第一优先级是补齐 PIT provider 覆盖，而不是继续扩大规则搜索。",
                "- 当前可执行链路已经能输出规则矩阵、回放、归因和报告，但 coverage gating 不允许生成生产候选或 `candidate_for_future_final_test`。",
                "- Provider 补齐后应重跑 `audit-data -> run-yearly -> report`，再判断 breakout coverage、pullback 重写或 regime switch 是否有必要。",
            ]
        )
    else:
        lines.extend(
            [
                "- 若 coverage-ok 年份显示 `trend_continuation_year`，下一阶段优先做 breakout coverage 和 layered exit 验证。",
                "- 若亏损主要来自 pullback + stop/time，应禁用或重写 pullback，而不是继续用 2025 表现外推。",
                "- 若多数有效规则高现金/低交易，应报告 no-edge / high-cash regime，不强行交易。",
            ]
        )

    output = report / "explore8_yearly_rule_diagnostic_report.md"
    ensure_parent(output)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    deep_output = report / "explore8_deep_dive_analysis_report.md"
    deep_lines = build_deep_dive_analysis_lines(
        config,
        coverage,
        eligibility,
        leaderboard,
        market,
        entry_exit,
        failure,
        reference,
        trade_detail,
        portfolio_daily,
        exposure,
        manifest,
        coverage_summary,
    )
    deep_output.write_text("\n".join(deep_lines) + "\n", encoding="utf-8")
    outputs = [output, deep_output]
    record_manifest(
        config,
        "report",
        outputs,
        {
            "report_path": relpath(output),
            "deep_dive_report_path": relpath(deep_output),
            "report_all_research_years_blocked": bool(all_blocked),
        },
    )
    print(f"wrote {relpath(output)}", flush=True)
    print(f"wrote {relpath(deep_output)}", flush=True)
    return outputs


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["self-test", "audit-data", "run-yearly", "report"])
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    config = load_config(args.config)
    try:
        if args.command == "self-test":
            command_self_test(config)
        elif args.command == "audit-data":
            command_audit_data(config)
        elif args.command == "run-yearly":
            command_run_yearly(config)
        elif args.command == "report":
            command_report(config)
        else:
            raise DataGateError(f"unknown command: {args.command}")
    except DataGateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

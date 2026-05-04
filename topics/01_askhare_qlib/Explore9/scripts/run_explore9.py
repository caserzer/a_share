#!/usr/bin/env python3
"""Run Explore9 P0 broad discovery.

Explore9 is a discovery phase.  It rebuilds labels and primitive profiles from
PIT structural inputs and the Qlib provider, while treating Explore8 outputs as
background/schema references only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


EXPLORE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = EXPLORE_DIR.parent
DEFAULT_CONFIG = EXPLORE_DIR / "configs/broad_discovery_p0.yaml"
FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}
REQUIRED_P0_REPORTS = [
    "source_data_audit.csv",
    "source_data_audit_summary.json",
    "provider_coverage_audit.csv",
    "label_coverage_audit.csv",
    "run_manifest.json",
    "stock_day_label_panel_summary.csv",
    "episode_lifecycle_labels.csv",
    "label_distribution_by_year.csv",
    "label_distribution_by_industry.csv",
    "observed_reference_label_audit.csv",
    "primitive_feature_dictionary.csv",
    "primitive_feature_coverage.csv",
    "primitive_univariate_lift.csv",
    "primitive_pairwise_lift.csv",
    "primitive_year_stability.csv",
    "primitive_industry_stability.csv",
    "preliminary_discovery_leads.csv",
    "p0_scope_completion_audit.csv",
    "explore9_broad_discovery_report.md",
]
DEFERRED_P1_OUTPUTS = [
    "hypothesis_discovery_leaderboard.csv",
    "hypothesis_year_breakdown.csv",
    "hypothesis_industry_breakdown.csv",
    "hypothesis_lifecycle_stage_breakdown.csv",
    "hypothesis_failure_modes.csv",
    "hold_condition_analysis.csv",
    "early_exit_replacement_hypotheses.csv",
    "post_20pct_continuation_analysis.csv",
    "post_30pct_continuation_analysis.csv",
]
DEFERRED_P2_OUTPUTS = [
    "price_shape_cluster_summary.csv",
    "money_shape_cluster_summary.csv",
    "joint_shape_cluster_summary.csv",
    "shape_cluster_examples.csv",
]


class DataGateError(RuntimeError):
    """Raised when the strict PIT discovery contract cannot be satisfied."""


@dataclass(frozen=True)
class PrimitiveSpec:
    feature_name: str
    feature_family: str
    column: str
    value_type: str
    min_history_trading_days: int
    lookback_window: str
    requires_benchmark_history: bool = False
    requires_industry_history: bool = False
    p0_enabled: bool = True
    direction_hint: str = "high"


@dataclass(frozen=True)
class PairwiseSpec:
    lead_id: str
    lead_name: str
    feature_family: str
    first_feature: str
    first_bins: tuple[str, ...]
    second_feature: str
    second_bins: tuple[str, ...]
    observable_state_stage: str
    direction: str
    recommended_next_phase: str


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
    if isinstance(value, Path):
        return relpath(value)
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


def read_csv_if_exists(value: str | Path) -> pd.DataFrame:
    path = topic_path(value)
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def parse_dt(value: str | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def iso_date(value: Any) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).date().isoformat()


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def safe_div(numerator: Any, denominator: Any) -> float:
    den = safe_float(denominator, 0.0)
    if den == 0 or pd.isna(den):
        return np.nan
    return safe_float(numerator, 0.0) / den


def format_pct(value: Any) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:.2%}"


def format_float(value: Any, digits: int = 3) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:.{digits}f}"


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


def manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "run_manifest.json"


def stock_panel_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel.pkl"


def stock_panel_meta_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel_meta.json"


def label_panel_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_day_label_panel.parquet"


def source_category_counts(audit: pd.DataFrame) -> dict[str, int]:
    if audit.empty:
        return {}
    grouped = audit.groupby("category", as_index=False).size()
    return {str(row["category"]): int(row["size"]) for _, row in grouped.iterrows()}


def required_field_names(config: dict[str, Any]) -> list[str]:
    return [FIELD_RENAME.get(field, field.lstrip("$")) for field in config["qlib"]["required_fields"]]


def research_years(config: dict[str, Any]) -> list[int]:
    start = parse_dt(config["dates"]["research_start"]).year
    end = parse_dt(config["dates"]["research_end"]).year
    return list(range(start, end + 1))


def record_manifest(config: dict[str, Any], command: str, outputs: list[str | Path], extra: dict[str, Any] | None = None) -> None:
    path = manifest_path(config)
    manifest = read_json(path)
    commands = list(manifest.get("command_sequence", []))
    commands.append(command)
    output_paths = sorted(set(manifest.get("output_paths", []) + [relpath(p) for p in outputs]))
    audit_path = report_dir(config) / "source_data_audit.csv"
    audit = pd.read_csv(audit_path) if audit_path.exists() else pd.DataFrame()
    manifest.update(
        {
            "experiment": "Explore9 P0 broad discovery",
            "phase": "P0",
            "config_path": relpath(config["_config_path"]),
            "config_sha256": config["_config_sha256"],
            "command_sequence": commands,
            "output_paths": output_paths,
            "provider_uri": config["paths"]["provider_uri"],
            "fallback_provider_uri": config["paths"]["fallback_provider_uri"],
            "universe_membership": config["paths"]["universe_membership"],
            "industry_membership": config["paths"]["industry_membership"],
            "point_in_time_universe": bool(config["universe"].get("point_in_time", False)),
            "point_in_time_industry": bool(config["industry"].get("point_in_time", False)),
            "price_adjustment_mode": config["qlib"]["price_adjustment_mode"],
            "required_fields": required_field_names(config),
            "research_start": config["dates"]["research_start"],
            "research_end": config["dates"]["research_end"],
            "observed_reference_start": config["dates"]["observed_reference_start"],
            "observed_reference_end": config["dates"]["observed_reference_end"],
            "source_category_counts": source_category_counts(audit),
            "explore8_profile_csv_used_for_label": False,
            "explore8_profile_csv_used_for_signal": False,
            "explore8_profile_csv_used_for_selection": False,
            "historical_trade_results_used_for_labeling": False,
            "historical_trade_results_used_for_signal": False,
            "historical_trade_results_used_for_selection": False,
            "observed_reference_used_for_selection": False,
            "p1_outputs_status": {name: "deferred_to_p1" for name in DEFERRED_P1_OUTPUTS},
            "p2_outputs_status": {name: "deferred_to_p2" for name in DEFERRED_P2_OUTPUTS},
        }
    )
    if label_panel_path(config).exists():
        panel_path = label_panel_path(config)
        panel_meta = read_json(cache_dir(config) / "stock_day_label_panel_meta.json")
        manifest["stock_day_label_panel"] = {
            "path": relpath(panel_path),
            "format": "parquet",
            "file_size_bytes": panel_path.stat().st_size,
            **panel_meta,
        }
    if extra:
        manifest.update(extra)
    write_json(manifest, path)


def build_source_data_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(path_value: str | Path, category: str, allowed_use: str, used_for_calculation: bool, count_rows: bool = True) -> None:
        path = topic_path(path_value)
        rows.append(
            {
                "path": relpath(path),
                "category": category,
                "allowed_use": allowed_use,
                "exists": bool(path.exists()),
                "is_file": bool(path.is_file()),
                "row_count": count_csv_rows(path) if count_rows and path.exists() and path.is_file() else None,
                "sha256": maybe_sha256(path) if path.exists() and path.is_file() else "",
                "used_for_calculation": bool(used_for_calculation),
            }
        )

    for key in [
        "provider_uri",
        "fallback_provider_uri",
        "universe_membership",
        "universe_qlib",
        "industry_membership",
        "market_targets",
        "industry_targets",
        "target_history",
    ]:
        add(config["paths"][key], "structural_input", key, True, count_rows=key.endswith(("membership", "targets", "history")))
    for path in config.get("sources", {}).get("background_reference", []):
        add(path, "background_reference", "background narrative only", False)
    for path in config.get("sources", {}).get("schema_reference", []):
        add(path, "schema_reference_audit_only", "schema/audit reference only", False)

    patterns = config.get("sources", {}).get("forbidden_result_path_patterns", [])
    tokens = [str(token).lower() for token in config.get("sources", {}).get("forbidden_result_name_tokens", [])]
    for pattern in patterns:
        base = topic_path(pattern)
        candidates: list[Path] = []
        if base.exists() and base.is_dir():
            candidates = [p for p in base.rglob("*") if p.is_file()]
        elif any(ch in pattern for ch in "*?[]"):
            candidates = [p for p in TOPIC_DIR.glob(pattern) if p.is_file()]
        for candidate in sorted(candidates):
            lowered = candidate.name.lower()
            if candidate.suffix.lower() in {".csv", ".pkl", ".json", ".parquet"} and any(token in lowered for token in tokens):
                add(candidate, "forbidden_result_path", "must not enter Explore9 calculation path", False, count_rows=False)
    audit = pd.DataFrame(rows)
    if audit.empty:
        audit = pd.DataFrame(columns=["path", "category", "allowed_use", "exists", "is_file", "row_count", "sha256", "used_for_calculation"])
    return audit.drop_duplicates(["path", "category"]).sort_values(["category", "path"]).reset_index(drop=True)


def validate_source_audit(audit: pd.DataFrame) -> None:
    missing = audit[(audit["category"] == "structural_input") & (~audit["exists"].astype(bool))]
    if not missing.empty:
        raise DataGateError(f"missing structural inputs: {missing['path'].tolist()}")
    forbidden = audit[(audit["category"] == "forbidden_result_path") & (audit["used_for_calculation"].astype(bool))]
    if not forbidden.empty:
        raise DataGateError("forbidden result paths are marked as calculation inputs")


def read_universe(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["universe_membership"])
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "instrument", "listing_age_trading_days", "market_cap_asof_T"}
    missing = required - set(df.columns)
    if missing:
        raise DataGateError(f"PIT universe missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    if "name" not in df.columns:
        df["name"] = ""
    return df.sort_values(["date", "instrument"]).reset_index(drop=True)


def read_industry(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["industry_membership"])
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
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"target_type", "target_key", "date", "open", "high", "low", "close", "money"}
    missing = required - set(df.columns)
    if missing:
        raise DataGateError(f"target history missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["target_key"] = df["target_key"].astype("string")
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
                freq=config["qlib"].get("freq", "day"),
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
    raise DataGateError(f"no readable Qlib provider for Explore9; last_error={last_error}")


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


def build_provider_coverage_audit(
    config: dict[str, Any],
    universe: pd.DataFrame,
    industry: pd.DataFrame,
    panel: pd.DataFrame,
    provider_meta: dict[str, Any],
    target_history: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    fields = required_field_names(config)
    research_start = parse_dt(config["dates"]["research_start"])
    observed_end = parse_dt(config["dates"]["observed_reference_end"])
    membership = universe[(universe["date"] >= research_start) & (universe["date"] <= observed_end)][["date", "instrument"]].drop_duplicates()
    membership["year"] = membership["date"].dt.year
    availability = panel[["datetime", "instrument"] + [field for field in fields if field in panel.columns]].rename(columns={"datetime": "date"}).copy()
    for field in fields:
        if field not in availability.columns:
            availability[field] = np.nan
    merged = membership.merge(availability, on=["date", "instrument"], how="left")
    merged["readable_row"] = merged["open"].notna()
    merged["all_required_fields"] = merged[fields].notna().all(axis=1)
    ind = industry[["date", "instrument", "industry_name"]].drop_duplicates()
    merged = merged.merge(ind, on=["date", "instrument"], how="left")
    merged["industry_name"] = merged["industry_name"].fillna(config["industry"].get("missing_industry", "UNKNOWN")).replace("", "UNKNOWN")
    broad_key = config["qlib"]["broad_market_key"]
    broad = target_history[(target_history["target_type"] == "market") & (target_history["target_key"] == broad_key)].copy()
    benchmark_years = set(pd.to_datetime(broad["date"]).dt.year.astype(int).tolist())

    rows: list[dict[str, Any]] = []
    coverage_ok_min = float(config["coverage"]["coverage_ok_min"])
    coverage_limited_min = float(config["coverage"]["coverage_limited_min"])
    required_ok_min = float(config["coverage"]["required_field_coverage_ok_min"])
    for year, subset in merged.groupby("year", sort=True):
        membership_rows = int(len(subset))
        readable_rows = int(subset["readable_row"].sum())
        required_rows = int(subset["all_required_fields"].sum())
        ratio = readable_rows / membership_rows if membership_rows else 0.0
        required_ratio = required_rows / membership_rows if membership_rows else 0.0
        missing = subset[~subset["all_required_fields"]]
        if ratio >= coverage_ok_min and required_ratio >= required_ok_min and int(year) in benchmark_years:
            status = "coverage_ok"
            conclusion_permission = "full_p0_discovery"
        elif ratio >= coverage_limited_min and int(year) in benchmark_years:
            status = "coverage_limited"
            conclusion_permission = "diagnostic_only_limited"
        else:
            status = "data_insufficient"
            conclusion_permission = "no_year_conclusion"
        rows.append(
            {
                "year": int(year),
                "pit_membership_rows": membership_rows,
                "readable_pit_membership_rows": readable_rows,
                "rows_with_all_required_fields": required_rows,
                "missing_required_rows": int(membership_rows - required_rows),
                "readable_coverage_ratio": ratio,
                "required_field_coverage_ratio": required_ratio,
                "missing_instrument_count": int(missing["instrument"].nunique()) if not missing.empty else 0,
                "missing_top_industries": json.dumps(missing.groupby("industry_name").size().sort_values(ascending=False).head(8).to_dict(), ensure_ascii=False),
                "benchmark_readable": bool(int(year) in benchmark_years),
                "coverage_status": status,
                "conclusion_permission": conclusion_permission,
                "provider_uri": provider_meta.get("provider_uri", ""),
                "fallback_used": bool(provider_meta.get("fallback_used", False)),
            }
        )
    audit = pd.DataFrame(rows)
    research = audit[audit["year"].isin(research_years(config))]
    total_membership = int(research["pit_membership_rows"].sum()) if not research.empty else 0
    total_required = int(research["rows_with_all_required_fields"].sum()) if not research.empty else 0
    summary = {
        "provider_uri": provider_meta.get("provider_uri", ""),
        "fallback_used": bool(provider_meta.get("fallback_used", False)),
        "research_membership_rows": total_membership,
        "research_required_field_rows": total_required,
        "research_required_field_coverage_ratio": total_required / total_membership if total_membership else 0.0,
        "coverage_limited_research": bool((research["coverage_status"] != "coverage_ok").any()) if not research.empty else True,
        "all_research_years_coverage_ok": bool((research["coverage_status"] == "coverage_ok").all()) if not research.empty else False,
    }
    return audit, summary


def future_rolling_max(series: pd.Series, horizon: int) -> pd.Series:
    rev = series.iloc[::-1]
    return rev.shift(1).rolling(horizon, min_periods=1).max().iloc[::-1].reindex(series.index)


def target_feature_frame(target_history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = target_history.copy().sort_values(["target_key", "date"])
    group = df.groupby("target_key", group_keys=False)
    for window in [20, 60, 120]:
        df[f"target_ret{window}"] = group["close"].pct_change(window)
    df["target_ret1"] = group["close"].pct_change()
    df["target_ema60"] = group["close"].transform(lambda s: s.ewm(span=60, adjust=False).mean())
    df["target_ema120"] = group["close"].transform(lambda s: s.ewm(span=120, adjust=False).mean())
    df["target_ema60_slope20"] = df["target_ema60"] / group["target_ema60"].shift(20) - 1.0
    df["target_volatility20"] = group["target_ret1"].transform(lambda s: s.rolling(20, min_periods=20).std())
    df["target_drawdown120"] = df["close"] / group["close"].transform(lambda s: s.rolling(120, min_periods=20).max()) - 1.0
    market = df[df["target_type"] == "market"].copy()
    industry = df[df["target_type"] == "industry"].copy()
    return market, industry


def consecutive_true_by_group(df: pd.DataFrame, flag_col: str, out_col: str) -> pd.DataFrame:
    values = np.zeros(len(df), dtype=np.int32)
    for _instrument, idx in df.groupby("instrument", sort=False).groups.items():
        flags = df.loc[idx, flag_col].fillna(False).to_numpy(dtype=bool)
        count = 0
        out = []
        for flag in flags:
            count = count + 1 if flag else 0
            out.append(count)
        values[df.index.get_indexer(idx)] = out
    df[out_col] = values
    return df


def add_stock_features(
    config: dict[str, Any],
    panel: pd.DataFrame,
    universe: pd.DataFrame,
    industry: pd.DataFrame,
    target_history: pd.DataFrame,
) -> pd.DataFrame:
    fields = required_field_names(config)
    stock = panel.copy().sort_values(["instrument", "datetime"]).reset_index(drop=True)
    for field in fields:
        if field not in stock.columns:
            stock[field] = np.nan
    group = stock.groupby("instrument", group_keys=False)
    prev_close = group["close"].shift(1)
    stock["prev_close"] = prev_close
    stock["ret1"] = group["close"].pct_change()
    for window in [3, 5, 10, 20, 60, 120]:
        stock[f"ret{window}"] = group["close"].pct_change(window)
    for span in [20, 30, 60, 120]:
        stock[f"ema{span}"] = group["close"].transform(lambda s, span=span: s.ewm(span=span, adjust=False).mean())
    true_range = pd.concat(
        [stock["high"] - stock["low"], (stock["high"] - prev_close).abs(), (stock["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    stock["true_range"] = true_range
    for window in [10, 20, 60]:
        stock[f"volatility{window}"] = group["ret1"].transform(lambda s, window=window: s.rolling(window, min_periods=window).std())
    stock["atr20"] = group["true_range"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    stock["atr20_pct"] = stock["atr20"] / stock["close"].replace(0, np.nan)
    stock["amplitude"] = (stock["high"] - stock["low"]) / prev_close.replace(0, np.nan)
    stock["amplitude20"] = group["amplitude"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    for window in [20, 60, 120, 240]:
        high_col = f"high{window}"
        low_col = f"low{window}"
        stock[high_col] = group["high"].transform(lambda s, window=window: s.rolling(window, min_periods=window).max())
        stock[low_col] = group["low"].transform(lambda s, window=window: s.rolling(window, min_periods=window).min())
        stock[f"dist_high{window}"] = stock["close"] / stock[high_col].replace(0, np.nan) - 1.0
        stock[f"dist_low{window}"] = stock["close"] / stock[low_col].replace(0, np.nan) - 1.0
    for window in [5, 20, 60]:
        prior = group["money"].transform(lambda s, window=window: s.shift(1).rolling(window, min_periods=window).mean())
        stock[f"avg_money{window}_prior"] = prior
        stock[f"money_ratio{window}"] = stock["money"] / prior.replace(0, np.nan)
    stock["money_regime_shift60"] = stock["avg_money20_prior"] / stock["avg_money60_prior"].replace(0, np.nan)
    stock["gap_pct"] = stock["open"] / prev_close.replace(0, np.nan) - 1.0
    stock["limit_up_like"] = ((stock["close"] / prev_close.replace(0, np.nan) - 1.0) >= 0.095) | (stock["gap_pct"] >= 0.095)
    rolling_high10 = group["high"].transform(lambda s: s.rolling(10, min_periods=10).max())
    rolling_low10 = group["low"].transform(lambda s: s.rolling(10, min_periods=10).min())
    stock["range10_pct"] = rolling_high10 / rolling_low10.replace(0, np.nan) - 1.0
    stock["narrow_range10"] = stock["range10_pct"] <= 0.08
    stock["range_expansion20"] = stock["amplitude20"] / group["amplitude20"].shift(20).replace(0, np.nan) - 1.0
    for window in [60, 120, 240]:
        stock[f"drawdown_from_high{window}"] = stock["close"] / stock[f"high{window}"].replace(0, np.nan) - 1.0
        stock[f"repair_from_low{window}"] = stock["close"] / stock[f"low{window}"].replace(0, np.nan) - 1.0
    stock["ema60_reclaim_flag"] = (stock["close"] > stock["ema60"]) & (prev_close <= group["ema60"].shift(1))
    stock["trend_speed20"] = stock["ret20"] / 20.0
    stock["close_above_ema60"] = stock["close"] > stock["ema60"]
    stock = consecutive_true_by_group(stock, "close_above_ema60", "trend_age_close_above_ema60")
    stock["instrument_day_index"] = stock.groupby("instrument").cumcount() + 1
    stock["available_history_trading_days"] = stock["instrument_day_index"] - 1
    stock["provider_required_fields_ok"] = stock[fields].notna().all(axis=1)

    membership_cols = ["date", "instrument", "name", "listing_age_trading_days", "market_cap_asof_T"]
    membership = universe[membership_cols].drop_duplicates().rename(columns={"date": "datetime"})
    df = stock.merge(membership, on=["datetime", "instrument"], how="inner")
    if df.empty:
        raise DataGateError("provider has no rows after explicit date+instrument PIT universe join")
    df["pit_member"] = True
    industry_join = industry[["date", "instrument", "industry_target_key", "industry_name"]].drop_duplicates().rename(columns={"date": "datetime"})
    df = df.merge(industry_join, on=["datetime", "instrument"], how="left")
    missing_industry = config["industry"].get("missing_industry", "UNKNOWN")
    df["industry_name"] = df["industry_name"].fillna(missing_industry).replace("", missing_industry)
    df["industry_target_key"] = df["industry_target_key"].fillna("UNKNOWN").astype("string")

    market, industry_targets = target_feature_frame(target_history)
    broad_key = config["qlib"]["broad_market_key"]
    broad = market[market["target_key"] == broad_key][
        [
            "date",
            "target_ret20",
            "target_ret60",
            "target_ret120",
            "target_ema60_slope20",
            "target_volatility20",
            "target_drawdown120",
            "close",
            "target_ema60",
        ]
    ].rename(
        columns={
            "date": "datetime",
            "target_ret20": "benchmark_ret20",
            "target_ret60": "benchmark_ret60",
            "target_ret120": "benchmark_ret120",
            "target_ema60_slope20": "benchmark_ema60_slope20",
            "target_volatility20": "benchmark_volatility20",
            "target_drawdown120": "benchmark_drawdown120",
            "close": "benchmark_close",
            "target_ema60": "benchmark_ema60",
        }
    )
    df = df.merge(broad, on="datetime", how="left")
    for window in [20, 60, 120]:
        df[f"relative_ret{window}_vs_benchmark"] = df[f"ret{window}"] - df[f"benchmark_ret{window}"]

    ind_target = industry_targets[["date", "target_key", "target_ret20", "target_ret60", "target_ret120"]].rename(
        columns={
            "date": "datetime",
            "target_key": "industry_target_key",
            "target_ret20": "industry_target_ret20",
            "target_ret60": "industry_target_ret60",
            "target_ret120": "industry_target_ret120",
        }
    )
    ind_target["industry_target_key"] = ind_target["industry_target_key"].astype("string")
    df = df.merge(ind_target, on=["datetime", "industry_target_key"], how="left")
    for window in [20, 60]:
        df[f"relative_ret{window}_vs_industry"] = df[f"ret{window}"] - df[f"industry_target_ret{window}"]

    df["ret20_universe_pctile"] = df.groupby("datetime")["ret20"].rank(pct=True)
    df["ret20_industry_pctile"] = df.groupby(["datetime", "industry_name"])["ret20"].rank(pct=True)
    df["money_universe_pctile"] = df.groupby("datetime")["money"].rank(pct=True)
    df["money_industry_pctile"] = df.groupby(["datetime", "industry_name"])["money"].rank(pct=True)
    df["volatility20_universe_pctile"] = df.groupby("datetime")["volatility20"].rank(pct=True)

    width = (
        df[df["provider_required_fields_ok"]]
        .assign(close_gt_ema60_flag=lambda x: x["close"] > x["ema60"], ema20_gt_ema60_flag=lambda x: x["ema20"] > x["ema60"])
        .groupby("datetime", as_index=False)
        .agg(
            readable_pit_instruments=("instrument", "nunique"),
            close_gt_ema60_ratio=("close_gt_ema60_flag", "mean"),
            ema20_gt_ema60_ratio=("ema20_gt_ema60_flag", "mean"),
        )
    )
    width["market_width_state"] = np.select(
        [width["close_gt_ema60_ratio"] >= 0.60, width["close_gt_ema60_ratio"] >= 0.40],
        ["width_strong", "width_neutral"],
        default="width_weak",
    )
    df = df.merge(width, on="datetime", how="left")
    industry_width = (
        df[df["provider_required_fields_ok"]]
        .assign(close_gt_ema60_flag=lambda x: x["close"] > x["ema60"])
        .groupby(["datetime", "industry_name"], as_index=False)
        .agg(industry_member_count=("instrument", "nunique"), industry_close_gt_ema60_ratio=("close_gt_ema60_flag", "mean"))
    )
    industry_width["industry_width_state"] = np.select(
        [industry_width["industry_close_gt_ema60_ratio"] >= 0.60, industry_width["industry_close_gt_ema60_ratio"] >= 0.40],
        ["industry_width_strong", "industry_width_neutral"],
        default="industry_width_weak",
    )
    df = df.merge(industry_width, on=["datetime", "industry_name"], how="left")
    df["market_regime_state"] = np.select(
        [
            (df["benchmark_close"] > df["benchmark_ema60"]) & (df["benchmark_ema60_slope20"] > 0),
            df["benchmark_drawdown120"] <= -0.10,
        ],
        ["market_trend_on", "market_drawdown"],
        default="market_choppy",
    )
    df["industry_regime_state"] = np.select(
        [
            (df["industry_target_ret60"] > df["benchmark_ret60"]) & (df["industry_width_state"] == "industry_width_strong"),
            df["industry_target_ret60"] < df["benchmark_ret60"],
        ],
        ["industry_sync_on", "industry_lagging"],
        default="industry_mixed",
    )
    df["market_cap_bucket"] = pd.cut(
        df["market_cap_asof_T"],
        bins=[-np.inf, 8e10, 1.5e11, 3e11, np.inf],
        labels=["cap_50_80b", "cap_80_150b", "cap_150_300b", "cap_300b_plus"],
    ).astype("string").fillna("missing")
    df["listing_age_bucket"] = pd.cut(
        df["listing_age_trading_days"],
        bins=[-np.inf, 250, 750, 1500, np.inf],
        labels=["listing_young", "listing_mid", "listing_mature", "listing_old"],
    ).astype("string").fillna("missing")
    df["trend_speed_bucket"] = pd.cut(
        df["ret20"],
        bins=[-np.inf, 0.00, 0.10, 0.25, np.inf],
        labels=["speed_negative", "speed_slow", "speed_mid", "speed_fast"],
    ).astype("string").fillna("missing")
    df["post_20pct_from_recent_low"] = df["repair_from_low120"] >= 0.20
    df["post_30pct_from_recent_low"] = df["repair_from_low120"] >= 0.30
    df["observable_state_stage"] = observable_stage(df)
    df["feature_eligible"] = (df["available_history_trading_days"] >= 20) & df["provider_required_fields_ok"]
    df["feature_missing_reason"] = np.select(
        [
            ~df["provider_required_fields_ok"],
            df["available_history_trading_days"] < 20,
        ],
        ["provider_required_fields_missing", "insufficient_minimum_history"],
        default="",
    )
    first_eligible = (
        df[df["feature_eligible"]]
        .groupby("instrument", as_index=False)["datetime"]
        .min()
        .rename(columns={"datetime": "first_feature_eligible_date"})
    )
    df = df.merge(first_eligible, on="instrument", how="left")
    df["year"] = df["datetime"].dt.year
    df["instrument_year"] = df["instrument"] + "_" + df["year"].astype(str)
    return df.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def observable_stage(df: pd.DataFrame) -> pd.Series:
    conditions = [
        (df["repair_from_low240"] >= 0.80) & (df["trend_age_close_above_ema60"] >= 80),
        df["repair_from_low120"] >= 0.30,
        df["repair_from_low120"] >= 0.20,
        (df["ret20_universe_pctile"] >= 0.80) & (df["relative_ret20_vs_benchmark"] > 0),
        (df["repair_from_low120"] >= 0.10) & (df["drawdown_from_high120"] <= -0.15),
        (df["range10_pct"] <= 0.08) & (df["drawdown_from_high120"] <= -0.20),
        (df["close"] < df["ema60"]) & (df["ret60"] < 0),
    ]
    choices = [
        "observable_late_acceleration_risk",
        "observable_30pct_from_recent_low",
        "observable_20pct_from_recent_low",
        "observable_relative_strength_leading",
        "observable_repairing",
        "observable_base_building",
        "observable_downtrend",
    ]
    return pd.Series(np.select(conditions, choices, default="observable_trend_extension"), index=df.index, dtype="string")


def add_loop_forward_fields(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    time_horizon = int(config["labels"]["time_to_max_horizon"])
    out_time_50_high = np.full(len(df), np.nan)
    out_time_100_high = np.full(len(df), np.nan)
    out_time_50_close = np.full(len(df), np.nan)
    out_time_100_close = np.full(len(df), np.nan)
    out_first_50_high = np.full(len(df), None, dtype=object)
    out_first_100_high = np.full(len(df), None, dtype=object)
    dd_before_60 = np.full(len(df), np.nan)
    dd_before_120 = np.full(len(df), np.nan)
    dd_horizon_60 = np.full(len(df), np.nan)
    dd_horizon_120 = np.full(len(df), np.nan)
    future_episode_key = np.full(len(df), None, dtype=object)

    for instrument, group in df.groupby("instrument", sort=False):
        idx = group.index.to_numpy()
        close = group["close"].to_numpy(dtype=float)
        high = group["high"].to_numpy(dtype=float)
        low = group["low"].to_numpy(dtype=float)
        dates = pd.to_datetime(group["datetime"]).dt.date.astype(str).to_numpy()
        n = len(group)
        for pos in range(n):
            base = close[pos]
            if not np.isfinite(base) or base <= 0:
                continue
            end_max = min(n, pos + time_horizon + 1)
            if pos + 1 >= end_max:
                continue
            future_high = high[pos + 1 : end_max]
            future_close = close[pos + 1 : end_max]
            high50 = np.flatnonzero(future_high >= base * 1.5)
            high100 = np.flatnonzero(future_high >= base * 2.0)
            close50 = np.flatnonzero(future_close >= base * 1.5)
            close100 = np.flatnonzero(future_close >= base * 2.0)
            row_index = idx[pos]
            if len(high50):
                first = int(high50[0]) + 1
                out_time_50_high[row_index] = first
                out_first_50_high[row_index] = dates[pos + first]
                future_episode_key[row_index] = f"{instrument}_{dates[pos + first]}"
            if len(high100):
                first = int(high100[0]) + 1
                out_time_100_high[row_index] = first
                out_first_100_high[row_index] = dates[pos + first]
            if len(close50):
                out_time_50_close[row_index] = int(close50[0]) + 1
            if len(close100):
                out_time_100_close[row_index] = int(close100[0]) + 1
            for horizon, dd_all, dd_before in [(60, dd_horizon_60, dd_before_60), (120, dd_horizon_120, dd_before_120)]:
                end_h = min(n, pos + horizon + 1)
                if end_h <= pos + 1:
                    continue
                lows = low[pos + 1 : end_h]
                if len(lows) and np.isfinite(lows).any():
                    dd_all[row_index] = np.nanmin(lows / base - 1.0)
                highs_h = high[pos + 1 : end_h]
                hit = np.flatnonzero(highs_h >= base * 1.5)
                if len(hit):
                    hit_end = pos + 1 + int(hit[0]) + 1
                    lows_before = low[pos + 1 : hit_end]
                    if len(lows_before) and np.isfinite(lows_before).any():
                        dd_before[row_index] = np.nanmin(lows_before / base - 1.0)

    df["future_time_to_50pct_high_gain"] = out_time_50_high
    df["future_time_to_100pct_high_gain"] = out_time_100_high
    df["future_time_to_50pct_close_gain"] = out_time_50_close
    df["future_time_to_100pct_close_gain"] = out_time_100_close
    df["future_first_50pct_high_gain_date"] = out_first_50_high
    df["future_first_100pct_high_gain_date"] = out_first_100_high
    df["future_50pct_episode_key_240d"] = future_episode_key
    df["future_max_drawdown_before_gain_60d"] = dd_before_60
    df["future_max_drawdown_before_gain_120d"] = dd_before_120
    df["future_max_drawdown_in_horizon_60d"] = dd_horizon_60
    df["future_max_drawdown_in_horizon_120d"] = dd_horizon_120
    return df


def add_forward_labels(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    df = df.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    group = df.groupby("instrument", group_keys=False)
    horizons = [int(h) for h in config["labels"]["horizons"]]
    for horizon in horizons:
        future_high = group["high"].transform(lambda s, horizon=horizon: future_rolling_max(s, horizon))
        future_close = group["close"].transform(lambda s, horizon=horizon: future_rolling_max(s, horizon))
        df[f"future_max_high_gain_{horizon}d"] = future_high / df["close"].replace(0, np.nan) - 1.0
        df[f"future_max_close_gain_{horizon}d"] = future_close / df["close"].replace(0, np.nan) - 1.0
        df[f"horizon_end_date_{horizon}d"] = group["datetime"].shift(-horizon)
        remaining = group.cumcount(ascending=False)
        df[f"label_horizon_truncated_{horizon}d"] = remaining < horizon
        horizon_end = pd.to_datetime(df[f"horizon_end_date_{horizon}d"])
        research_end = parse_dt(config["dates"]["research_end"])
        df[f"observed_reference_overlap_{horizon}d"] = (df["datetime"] <= research_end) & (horizon_end > research_end)
        df[f"is_future_50pct_high_{horizon}d"] = df[f"future_max_high_gain_{horizon}d"] >= 0.50
        df[f"is_future_100pct_high_{horizon}d"] = df[f"future_max_high_gain_{horizon}d"] >= 1.00
        df[f"is_future_50pct_close_{horizon}d"] = df[f"future_max_close_gain_{horizon}d"] >= 0.50
        df[f"is_future_100pct_close_{horizon}d"] = df[f"future_max_close_gain_{horizon}d"] >= 1.00
    df["intraday_50pct_not_close_confirmed_120d"] = df["is_future_50pct_high_120d"] & ~df["is_future_50pct_close_120d"]
    df["intraday_50pct_not_close_confirmed_240d"] = df["is_future_50pct_high_240d"] & ~df["is_future_50pct_close_240d"]
    df = add_loop_forward_fields(df, config)
    df["label_horizon_truncated"] = df["label_horizon_truncated_240d"]
    df["observed_reference_overlap"] = df["observed_reference_overlap_240d"]
    df["observed_reference_sample"] = df["datetime"] >= parse_dt(config["dates"]["observed_reference_start"])
    return df


def build_episode_lifecycle_labels(config: dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
    threshold = float(config["labels"]["episode_threshold"])
    research_start = parse_dt(config["dates"]["research_start"])
    research_end = parse_dt(config["dates"]["research_end"])
    observed_end = parse_dt(config["dates"]["observed_reference_end"])
    rows: list[dict[str, Any]] = []

    def best_episode(group: pd.DataFrame, year: int, scope: str) -> dict[str, Any] | None:
        group = group.sort_values("datetime").reset_index(drop=True)
        if len(group) < 2:
            return None
        lows = group["low"].to_numpy(dtype=float)
        highs = group["high"].to_numpy(dtype=float)
        closes = group["close"].to_numpy(dtype=float)
        best_gain = -np.inf
        best_low_pos = -1
        best_high_pos = -1
        for pos in range(len(group) - 1):
            if not np.isfinite(lows[pos]) or lows[pos] <= 0:
                continue
            future_highs = highs[pos + 1 :]
            if not len(future_highs) or not np.isfinite(future_highs).any():
                continue
            rel_pos = int(np.nanargmax(future_highs))
            gain = future_highs[rel_pos] / lows[pos] - 1.0
            if gain > best_gain:
                best_gain = float(gain)
                best_low_pos = pos
                best_high_pos = pos + 1 + rel_pos
        if best_gain < threshold or best_low_pos < 0 or best_high_pos < 0:
            return None
        low_date = group.loc[best_low_pos, "datetime"]
        high_date = group.loc[best_high_pos, "datetime"]
        base_low = lows[best_low_pos]
        episode_id = f"{scope}_{group.loc[best_low_pos, 'instrument']}_{iso_date(low_date)}_{iso_date(high_date)}"
        future_close = closes[best_high_pos] / base_low - 1.0 if np.isfinite(closes[best_high_pos]) else np.nan
        first_dates: dict[str, str] = {}
        for pct in [0.20, 0.30, 0.50, 1.00, 2.00]:
            hits = np.flatnonzero(highs[best_low_pos + 1 : best_high_pos + 1] >= base_low * (1.0 + pct))
            first_dates[f"first_intraday_{int(pct * 100)}pct_date"] = (
                iso_date(group.loc[best_low_pos + 1 + int(hits[0]), "datetime"]) if len(hits) else ""
            )
        return {
            "episode_id": episode_id,
            "episode_scope": scope,
            "year": int(year),
            "instrument": group.loc[best_low_pos, "instrument"],
            "name": group.loc[best_low_pos, "name"],
            "industry_name": group.loc[best_low_pos, "industry_name"],
            "low_date": iso_date(low_date),
            "high_date": iso_date(high_date),
            "duration_trading_days": int(best_high_pos - best_low_pos),
            "low_price": float(base_low),
            "high_price": float(highs[best_high_pos]),
            "forward_gain_intraday": best_gain,
            "forward_gain_close_confirmed": future_close,
            "observed_reference_overlap": bool(high_date > research_end),
            "truncated_by_year_boundary": bool(scope == "in_year_episode" and low_date.year != high_date.year),
            "retrospective_lifecycle_stage": "trend_extension",
            **first_dates,
        }

    research = df[(df["datetime"] >= research_start) & (df["datetime"] <= research_end) & df["provider_required_fields_ok"]].copy()
    for (year, instrument), group in research.groupby(["year", "instrument"], sort=True):
        episode = best_episode(group, int(year), "in_year_episode")
        if episode is not None:
            rows.append(episode)

    continuous = df[(df["datetime"] >= research_start) & (df["datetime"] <= observed_end) & df["provider_required_fields_ok"]].copy()
    for instrument, group in continuous.groupby("instrument", sort=True):
        episode = best_episode(group, 0, "cross_year_episode")
        if episode is not None:
            low_date = parse_dt(episode["low_date"])
            high_date = parse_dt(episode["high_date"])
            if low_date.year != high_date.year and low_date <= research_end:
                episode["year"] = int(low_date.year)
                episode["truncated_by_year_boundary"] = True
                rows.append(episode)

    columns = [
        "episode_id",
        "episode_scope",
        "year",
        "instrument",
        "name",
        "industry_name",
        "low_date",
        "high_date",
        "duration_trading_days",
        "low_price",
        "high_price",
        "forward_gain_intraday",
        "forward_gain_close_confirmed",
        "observed_reference_overlap",
        "truncated_by_year_boundary",
        "retrospective_lifecycle_stage",
        "first_intraday_20pct_date",
        "first_intraday_30pct_date",
        "first_intraday_50pct_date",
        "first_intraday_100pct_date",
        "first_intraday_200pct_date",
    ]
    return pd.DataFrame(rows, columns=columns)


def attach_retrospective_stage(df: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    df["retrospective_lifecycle_stage"] = ""
    if episodes.empty:
        return df
    in_year = episodes[episodes["episode_scope"] == "in_year_episode"].copy()
    episode_map = {(row.instrument, int(row.year)): row for row in in_year.itertuples(index=False)}
    stages = np.full(len(df), "", dtype=object)
    for (instrument, year), group in df.groupby(["instrument", "year"], sort=False):
        event = episode_map.get((instrument, int(year)))
        if event is None:
            continue
        low_date = parse_dt(event.low_date)
        high_date = parse_dt(event.high_date)
        low_price = safe_float(event.low_price, np.nan)
        idx = group.index.to_numpy()
        dates = pd.to_datetime(group["datetime"])
        gains = group["close"] / low_price - 1.0 if np.isfinite(low_price) and low_price > 0 else pd.Series(np.nan, index=group.index)
        stage = np.select(
            [
                dates < low_date,
                (dates >= low_date) & (gains < 0.20),
                (gains >= 0.20) & (gains < 0.30),
                (gains >= 0.30) & (dates < high_date),
                dates == high_date,
                dates > high_date,
            ],
            ["pre_repair", "early_repair", "confirmed_20pct", "confirmed_30pct", "trend_extension", "post_peak"],
            default="late_trend",
        )
        stages[idx] = stage
    df["retrospective_lifecycle_stage"] = stages
    return df


def build_label_coverage_audit(config: dict[str, Any], df: pd.DataFrame, provider_coverage: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    research_mask = (df["datetime"] >= parse_dt(config["dates"]["research_start"])) & (df["datetime"] <= parse_dt(config["dates"]["research_end"]))
    for horizon in [int(h) for h in config["labels"]["horizons"]]:
        subset = df[research_mask]
        rows.append(
            {
                "horizon": f"{horizon}d",
                "research_stock_day_rows": int(len(subset)),
                "horizon_valid_rows": int((~subset[f"label_horizon_truncated_{horizon}d"]).sum()),
                "label_horizon_truncated_rows": int(subset[f"label_horizon_truncated_{horizon}d"].sum()),
                "observed_reference_overlap_rows": int(subset[f"observed_reference_overlap_{horizon}d"].sum()),
                "provider_required_fields_ok_rows": int(subset["provider_required_fields_ok"].sum()),
                "future_50pct_high_positive_rows": int(subset[f"is_future_50pct_high_{horizon}d"].sum()),
                "future_100pct_high_positive_rows": int(subset[f"is_future_100pct_high_{horizon}d"].sum()),
                "future_50pct_close_positive_rows": int(subset[f"is_future_50pct_close_{horizon}d"].sum()),
                "future_100pct_close_positive_rows": int(subset[f"is_future_100pct_close_{horizon}d"].sum()),
            }
        )
    coverage = pd.DataFrame(rows)
    if not provider_coverage.empty:
        coverage["provider_coverage_limited_research"] = bool(
            (provider_coverage[provider_coverage["year"].isin(research_years(config))]["coverage_status"] != "coverage_ok").any()
        )
    return coverage


def build_label_summaries(config: dict[str, Any], df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    research_start = parse_dt(config["dates"]["research_start"])
    research_end = parse_dt(config["dates"]["research_end"])
    observed_start = parse_dt(config["dates"]["observed_reference_start"])
    observed_end = parse_dt(config["dates"]["observed_reference_end"])
    research = df[(df["datetime"] >= research_start) & (df["datetime"] <= research_end)]
    summary = pd.DataFrame(
        [
            {
                "row_count": int(len(df)),
                "research_row_count": int(len(research)),
                "instrument_count": int(df["instrument"].nunique()),
                "research_instrument_count": int(research["instrument"].nunique()),
                "first_date": iso_date(df["datetime"].min()),
                "last_date": iso_date(df["datetime"].max()),
                "required_fields_ok_ratio": float(df["provider_required_fields_ok"].mean()) if len(df) else 0.0,
                "feature_eligible_ratio": float(df["feature_eligible"].mean()) if len(df) else 0.0,
                "price_adjustment_mode": config["qlib"]["price_adjustment_mode"],
            }
        ]
    )
    by_year_rows = []
    for year, group in research.groupby("year", sort=True):
        by_year_rows.append(
            {
                "year": int(year),
                "stock_day_count": int(len(group)),
                "instrument_count": int(group["instrument"].nunique()),
                "future_50pct_high_120d_rate": float(group["is_future_50pct_high_120d"].mean()) if len(group) else np.nan,
                "future_100pct_high_240d_rate": float(group["is_future_100pct_high_240d"].mean()) if len(group) else np.nan,
                "horizon_120d_observed_reference_overlap_rate": float(group["observed_reference_overlap_120d"].mean()) if len(group) else np.nan,
                "horizon_240d_observed_reference_overlap_rate": float(group["observed_reference_overlap_240d"].mean()) if len(group) else np.nan,
            }
        )
    by_year = pd.DataFrame(by_year_rows)
    by_industry = (
        research.groupby("industry_name", as_index=False)
        .agg(
            stock_day_count=("instrument", "size"),
            instrument_count=("instrument", "nunique"),
            future_50pct_high_120d_rate=("is_future_50pct_high_120d", "mean"),
            future_100pct_high_240d_rate=("is_future_100pct_high_240d", "mean"),
        )
        .sort_values("stock_day_count", ascending=False)
    )
    observed = df[(df["datetime"] >= observed_start) & (df["datetime"] <= observed_end)]
    observed_audit = pd.DataFrame(
        [
            {
                "observed_reference_start": config["dates"]["observed_reference_start"],
                "observed_reference_end": config["dates"]["observed_reference_end"],
                "observed_reference_stock_day_rows": int(len(observed)),
                "observed_reference_instrument_count": int(observed["instrument"].nunique()) if len(observed) else 0,
                "used_for_selection": False,
                "used_for_feature_threshold_selection": False,
                "used_for_model_selection": False,
            }
        ]
    )
    return summary, by_year, by_industry, observed_audit


def primitive_specs() -> list[PrimitiveSpec]:
    specs = [
        PrimitiveSpec("ret3", "price_state", "ret3", "continuous", 3, "3d"),
        PrimitiveSpec("ret5", "price_state", "ret5", "continuous", 5, "5d"),
        PrimitiveSpec("ret10", "price_state", "ret10", "continuous", 10, "10d"),
        PrimitiveSpec("ret20", "price_state", "ret20", "continuous", 20, "20d"),
        PrimitiveSpec("ret60", "price_state", "ret60", "continuous", 60, "60d"),
        PrimitiveSpec("ret120", "price_state", "ret120", "continuous", 120, "120d"),
        PrimitiveSpec("dist_high20", "price_state", "dist_high20", "continuous", 20, "20d", direction_hint="low"),
        PrimitiveSpec("dist_high60", "price_state", "dist_high60", "continuous", 60, "60d", direction_hint="low"),
        PrimitiveSpec("dist_high120", "price_state", "dist_high120", "continuous", 120, "120d", direction_hint="low"),
        PrimitiveSpec("dist_low20", "price_state", "dist_low20", "continuous", 20, "20d"),
        PrimitiveSpec("dist_low60", "price_state", "dist_low60", "continuous", 60, "60d"),
        PrimitiveSpec("dist_low120", "price_state", "dist_low120", "continuous", 120, "120d"),
        PrimitiveSpec("gap_pct", "price_state", "gap_pct", "continuous", 1, "1d"),
        PrimitiveSpec("limit_up_like", "price_state", "limit_up_like", "boolean", 1, "1d"),
        PrimitiveSpec("relative_ret20_vs_benchmark", "relative_strength", "relative_ret20_vs_benchmark", "continuous", 20, "20d", True),
        PrimitiveSpec("relative_ret60_vs_benchmark", "relative_strength", "relative_ret60_vs_benchmark", "continuous", 60, "60d", True),
        PrimitiveSpec("relative_ret120_vs_benchmark", "relative_strength", "relative_ret120_vs_benchmark", "continuous", 120, "120d", True),
        PrimitiveSpec("relative_ret20_vs_industry", "relative_strength", "relative_ret20_vs_industry", "continuous", 20, "20d", False, True),
        PrimitiveSpec("relative_ret60_vs_industry", "relative_strength", "relative_ret60_vs_industry", "continuous", 60, "60d", False, True),
        PrimitiveSpec("ret20_universe_pctile", "relative_strength", "ret20_universe_pctile", "continuous", 20, "20d"),
        PrimitiveSpec("ret20_industry_pctile", "relative_strength", "ret20_industry_pctile", "continuous", 20, "20d", False, True),
        PrimitiveSpec("money_ratio5", "money_liquidity", "money_ratio5", "continuous", 5, "5d"),
        PrimitiveSpec("money_ratio20", "money_liquidity", "money_ratio20", "continuous", 20, "20d"),
        PrimitiveSpec("money_ratio60", "money_liquidity", "money_ratio60", "continuous", 60, "60d"),
        PrimitiveSpec("money_universe_pctile", "money_liquidity", "money_universe_pctile", "continuous", 1, "daily_cross_section"),
        PrimitiveSpec("money_industry_pctile", "money_liquidity", "money_industry_pctile", "continuous", 1, "daily_industry_cross_section", False, True),
        PrimitiveSpec("money_regime_shift60", "money_liquidity", "money_regime_shift60", "continuous", 60, "60d"),
        PrimitiveSpec("volatility10", "volatility_compression_expansion", "volatility10", "continuous", 10, "10d", direction_hint="low"),
        PrimitiveSpec("volatility20", "volatility_compression_expansion", "volatility20", "continuous", 20, "20d", direction_hint="low"),
        PrimitiveSpec("volatility60", "volatility_compression_expansion", "volatility60", "continuous", 60, "60d", direction_hint="low"),
        PrimitiveSpec("atr20_pct", "volatility_compression_expansion", "atr20_pct", "continuous", 20, "20d", direction_hint="low"),
        PrimitiveSpec("amplitude20", "volatility_compression_expansion", "amplitude20", "continuous", 20, "20d", direction_hint="low"),
        PrimitiveSpec("narrow_range10", "volatility_compression_expansion", "narrow_range10", "boolean", 10, "10d"),
        PrimitiveSpec("range_expansion20", "volatility_compression_expansion", "range_expansion20", "continuous", 40, "20d_vs_prior20d"),
        PrimitiveSpec("drawdown_from_high60", "drawdown_repair_base", "drawdown_from_high60", "continuous", 60, "60d", direction_hint="low"),
        PrimitiveSpec("drawdown_from_high120", "drawdown_repair_base", "drawdown_from_high120", "continuous", 120, "120d", direction_hint="low"),
        PrimitiveSpec("drawdown_from_high240", "drawdown_repair_base", "drawdown_from_high240", "continuous", 240, "240d", direction_hint="low"),
        PrimitiveSpec("repair_from_low60", "drawdown_repair_base", "repair_from_low60", "continuous", 60, "60d"),
        PrimitiveSpec("repair_from_low120", "drawdown_repair_base", "repair_from_low120", "continuous", 120, "120d"),
        PrimitiveSpec("repair_from_low240", "drawdown_repair_base", "repair_from_low240", "continuous", 240, "240d"),
        PrimitiveSpec("ema60_reclaim_flag", "drawdown_repair_base", "ema60_reclaim_flag", "boolean", 60, "60d"),
        PrimitiveSpec("trend_age_close_above_ema60", "trend_age_stage", "trend_age_close_above_ema60", "continuous", 60, "state_age"),
        PrimitiveSpec("trend_speed20", "trend_age_stage", "trend_speed20", "continuous", 20, "20d"),
        PrimitiveSpec("market_width_state", "market_industry_regime", "market_width_state", "categorical", 60, "market_width"),
        PrimitiveSpec("industry_width_state", "market_industry_regime", "industry_width_state", "categorical", 60, "industry_width", False, True),
        PrimitiveSpec("market_regime_state", "market_industry_regime", "market_regime_state", "categorical", 120, "benchmark_state", True),
        PrimitiveSpec("industry_regime_state", "market_industry_regime", "industry_regime_state", "categorical", 60, "industry_state", True, True),
        PrimitiveSpec("market_cap_bucket", "industry_style_layer", "market_cap_bucket", "categorical", 1, "asof_T_market_cap"),
        PrimitiveSpec("listing_age_bucket", "industry_style_layer", "listing_age_bucket", "categorical", 1, "asof_T_listing_age"),
        PrimitiveSpec("trend_speed_bucket", "industry_style_layer", "trend_speed_bucket", "categorical", 20, "20d"),
        PrimitiveSpec("observable_state_stage", "lifecycle_observable_stage", "observable_state_stage", "categorical", 20, "observable_state"),
        PrimitiveSpec("post_20pct_from_recent_low", "lifecycle_observable_stage", "post_20pct_from_recent_low", "boolean", 120, "120d"),
        PrimitiveSpec("post_30pct_from_recent_low", "lifecycle_observable_stage", "post_30pct_from_recent_low", "boolean", 120, "120d"),
        PrimitiveSpec("price_shape_cluster_registry", "shape_sequence_fragment", "ret20", "registry_only", 120, "deferred_p2", p0_enabled=False),
        PrimitiveSpec("cross_section_money_anomaly", "cross_section_anomaly_leadership", "money_universe_pctile", "continuous", 20, "daily_cross_section"),
        PrimitiveSpec("cross_section_return_anomaly", "cross_section_anomaly_leadership", "ret20_universe_pctile", "continuous", 20, "daily_cross_section"),
    ]
    return specs


def feature_dictionary() -> pd.DataFrame:
    rows = []
    for spec in primitive_specs():
        if not spec.p0_enabled:
            rule = "registry_only_deferred_to_p2"
            warmup = "deferred_to_p2"
        else:
            rule = f"available_history_trading_days >= {spec.min_history_trading_days} and provider_required_fields_ok and value_not_missing"
            warmup = "mark_warmup_partial_year_and_exclude_from_primitive_lift_denominator"
        rows.append(
            {
                "feature_name": spec.feature_name,
                "feature_family": spec.feature_family,
                "source_column": spec.column,
                "value_type": spec.value_type,
                "min_history_trading_days": int(spec.min_history_trading_days),
                "lookback_window": spec.lookback_window,
                "requires_benchmark_history": bool(spec.requires_benchmark_history),
                "requires_industry_history": bool(spec.requires_industry_history),
                "feature_eligible_rule": rule,
                "warmup_partial_year_handling": warmup,
                "p0_enabled": bool(spec.p0_enabled),
                "direction_hint": spec.direction_hint,
            }
        )
    return pd.DataFrame(rows)


def primitive_bin(df: pd.DataFrame, spec: PrimitiveSpec, config: dict[str, Any]) -> pd.Series:
    series = df[spec.column] if spec.column in df.columns else pd.Series(np.nan, index=df.index)
    if spec.value_type == "boolean":
        return pd.Series(np.where(series.fillna(False).astype(bool), "true", "false"), index=df.index, dtype="string")
    if spec.value_type == "categorical":
        return series.astype("string").fillna("missing")
    if spec.value_type == "registry_only":
        return pd.Series("deferred", index=df.index, dtype="string")
    pct = df.groupby("year")[spec.column].rank(pct=True) if spec.column in df.columns else pd.Series(np.nan, index=df.index)
    cuts = [float(x) for x in config["primitives"]["quantile_cuts"]]
    labels = ["p0_10", "p10_20", "p20_40", "p40_60", "p60_80", "p80_90", "p90_100"]
    bins = pd.Series("missing", index=df.index, dtype="object")
    previous = 0.0
    for cut, label in zip(cuts, labels):
        mask = (pct > previous) & (pct <= cut)
        bins.loc[mask] = label
        previous = cut
    bins.loc[pct > cuts[-1]] = labels[-1]
    return bins.astype("string")


def primitive_eligible(df: pd.DataFrame, spec: PrimitiveSpec) -> pd.Series:
    if not spec.p0_enabled or spec.column not in df.columns:
        return pd.Series(False, index=df.index)
    eligible = (
        df["pit_member"].fillna(False).astype(bool)
        & df["provider_required_fields_ok"].fillna(False).astype(bool)
        & (df["available_history_trading_days"] >= spec.min_history_trading_days)
        & df[spec.column].notna()
    )
    if spec.value_type == "categorical":
        eligible &= df[spec.column].astype("string").fillna("missing") != "missing"
    if spec.requires_benchmark_history:
        eligible &= df["benchmark_ret20"].notna()
    if spec.requires_industry_history:
        eligible &= df["industry_name"].fillna("UNKNOWN") != "UNKNOWN"
    return eligible


def baseline_mask(df: pd.DataFrame, eligible: pd.Series, horizon: int, config: dict[str, Any]) -> pd.Series:
    return (
        eligible.fillna(False)
        & (df["datetime"] >= parse_dt(config["dates"]["research_start"]))
        & (df["datetime"] <= parse_dt(config["dates"]["research_end"]))
        & ~df[f"label_horizon_truncated_{horizon}d"].fillna(True)
        & ~df[f"observed_reference_overlap_{horizon}d"].fillna(True)
        & df["pit_member"].fillna(False).astype(bool)
        & df["provider_required_fields_ok"].fillna(False).astype(bool)
    )


def summarize_condition(
    df: pd.DataFrame,
    condition: pd.Series,
    base_condition: pd.Series,
    positive_col: str,
    horizon: int,
    label_name: str,
    lead_id: str,
    lead_name: str,
    feature_family: str,
    formula_or_bin: str,
    direction: str,
    observable_state_stage: str,
    recommended_next_phase: str,
    baseline_scope: str = "same_year_same_horizon_horizon_valid_pit_stock_days",
) -> dict[str, Any]:
    base_mask = base_condition.fillna(False).astype(bool)
    lead_mask = (condition & base_mask).fillna(False).astype(bool)
    positive_mask = df[positive_col].fillna(False).astype(bool)
    lead_positive_mask = lead_mask & positive_mask
    base_positive_mask = base_mask & positive_mask
    base_count = int(base_mask.sum())
    lead_count = int(lead_mask.sum())
    positive_count = int(lead_positive_mask.sum())
    base_positive_count = int(base_positive_mask.sum())
    baseline_rate = safe_div(base_positive_count, base_count)
    lead_rate = safe_div(positive_count, lead_count)
    global_mask = (
        (df["datetime"] >= df["datetime"].min())
        & (df["datetime"] <= parse_dt("2024-12-31"))
        & ~df[f"label_horizon_truncated_{horizon}d"].fillna(True)
        & ~df[f"observed_reference_overlap_{horizon}d"].fillna(True)
        & df["provider_required_fields_ok"].fillna(False).astype(bool)
    )
    global_rate = safe_div(df.loc[global_mask, positive_col].sum(), global_mask.sum())
    lead_instrument = df.loc[lead_mask, "instrument"]
    positive_instrument = df.loc[lead_positive_mask, "instrument"]
    lead_instrument_year = df.loc[lead_mask, "instrument_year"]
    positive_instrument_year_series = df.loc[lead_positive_mask, "instrument_year"]
    base_instrument_year = df.loc[base_mask, "instrument_year"]
    base_positive_instrument_year_series = df.loc[base_positive_mask, "instrument_year"]
    instrument_year_denom = lead_instrument_year.nunique()
    positive_instrument_year = positive_instrument_year_series.nunique()
    base_instrument_year_denom = base_instrument_year.nunique()
    base_positive_instrument_year = base_positive_instrument_year_series.nunique()
    episode_col = "future_50pct_episode_key_240d"
    unique_episode_count = instrument_year_denom
    positive_unique_episode_count = df.loc[lead_positive_mask, episode_col].dropna().nunique() if episode_col in df.columns else 0
    base_unique_episode_count = base_instrument_year_denom
    base_positive_unique_episode_count = df.loc[base_positive_mask, episode_col].dropna().nunique() if episode_col in df.columns else 0
    episode_rate = safe_div(positive_unique_episode_count, unique_episode_count)
    base_episode_rate = safe_div(base_positive_unique_episode_count, base_unique_episode_count)
    instrument_year_rate = safe_div(positive_instrument_year, instrument_year_denom)
    base_instrument_year_rate = safe_div(base_positive_instrument_year, base_instrument_year_denom)
    yearly_positive_lifts = 0
    lead_years = df.loc[lead_mask, "year"].dropna().unique()
    for year in lead_years:
        year_lead_mask = lead_mask & (df["year"] == year)
        year_base_mask = base_mask & (df["year"] == year)
        if year_lead_mask.any() and year_base_mask.any():
            if safe_div(df.loc[year_lead_mask, positive_col].sum(), year_lead_mask.sum()) > safe_div(df.loc[year_base_mask, positive_col].sum(), year_base_mask.sum()):
                yearly_positive_lifts += 1
    industry_counts = df.loc[lead_mask, "industry_name"].value_counts(dropna=False)
    top1 = safe_div(industry_counts.iloc[0], lead_count) if len(industry_counts) else np.nan
    duplicate_limit = 5.0
    duplicate_risk = bool(positive_count > duplicate_limit * max(positive_unique_episode_count, 1))
    sparse_bin = bool(lead_count < 100)
    if lead_count == 0:
        failure = "empty_lead_sample"
    elif pd.isna(lead_rate) or lead_rate <= baseline_rate:
        failure = "lift_not_above_baseline"
    elif df.loc[lead_mask, "year"].nunique() < 3:
        failure = "insufficient_distinct_years"
    elif top1 > 0.50:
        failure = "single_industry_concentration"
    else:
        failure = ""
    drawdown_col = "future_max_drawdown_before_gain_120d" if horizon >= 120 else "future_max_drawdown_before_gain_60d"
    return {
        "lead_id": lead_id,
        "lead_name": lead_name,
        "feature_family": feature_family,
        "observable_state_stage": observable_state_stage,
        "formula_or_bin": formula_or_bin,
        "direction": direction,
        "horizon": f"{horizon}d",
        "positive_label": label_name,
        "baseline_scope": baseline_scope,
        "baseline_sample_count": int(base_count),
        "baseline_positive_rate": baseline_rate,
        "lead_positive_rate": lead_rate,
        "lift_vs_baseline": safe_div(lead_rate, baseline_rate),
        "global_lift": safe_div(lead_rate, global_rate),
        "industry_relative_lift": np.nan,
        "stock_day_count": int(lead_count),
        "unique_instrument_count": int(lead_instrument.nunique()),
        "unique_instrument_year_count": int(instrument_year_denom),
        "unique_episode_count": int(unique_episode_count),
        "positive_stock_day_count": int(positive_count),
        "positive_unique_instrument_count": int(positive_instrument.nunique()),
        "positive_unique_instrument_year_count": int(positive_instrument_year),
        "positive_unique_episode_count": int(positive_unique_episode_count),
        "lead_future_50pct_precision": float(df.loc[lead_mask, "is_future_50pct_high_120d"].mean()) if lead_count else np.nan,
        "lead_future_100pct_precision": float(df.loc[lead_mask, "is_future_100pct_high_240d"].mean()) if lead_count else np.nan,
        "episode_dedup_lift": safe_div(episode_rate, base_episode_rate),
        "instrument_year_dedup_lift": safe_div(instrument_year_rate, base_instrument_year_rate),
        "year_positive_lift_count": int(yearly_positive_lifts),
        "distinct_year_count": int(df.loc[lead_mask, "year"].nunique()),
        "distinct_industry_count": int(df.loc[lead_mask, "industry_name"].nunique()),
        "industry_concentration_top1": top1,
        "avg_lead_time_to_50pct": float(df.loc[lead_positive_mask, "future_time_to_50pct_high_gain"].mean()) if positive_count else np.nan,
        "median_lead_time_to_50pct": float(df.loc[lead_positive_mask, "future_time_to_50pct_high_gain"].median()) if positive_count else np.nan,
        "avg_future_max_gain": float(df.loc[lead_mask, f"future_max_high_gain_{horizon}d"].mean()) if lead_count else np.nan,
        "avg_future_drawdown_before_gain": float(df.loc[lead_positive_mask, drawdown_col].mean()) if positive_count and drawdown_col in df.columns else np.nan,
        "turnover_proxy": float(df.loc[lead_mask, "money"].median()) if lead_count else np.nan,
        "market_regime_dependency": df.loc[lead_mask, "market_regime_state"].value_counts(normalize=True).idxmax() if lead_count else "",
        "industry_regime_dependency": df.loc[lead_mask, "industry_regime_state"].value_counts(normalize=True).idxmax() if lead_count else "",
        "label_horizon_truncated_rate": float(df.loc[condition.fillna(False), f"label_horizon_truncated_{horizon}d"].mean()) if condition.any() else np.nan,
        "observed_reference_overlap_rate": float(df.loc[condition.fillna(False), f"observed_reference_overlap_{horizon}d"].mean()) if condition.any() else np.nan,
        "duplicate_positive_risk": duplicate_risk,
        "sparse_bin": sparse_bin,
        "failure_reason": failure,
        "recommended_next_phase": recommended_next_phase if not failure else "drop",
    }


def pairwise_specs() -> list[PairwiseSpec]:
    return [
        PairwiseSpec("pair_price_money", "20日强收益 + 成交放大", "price_money", "ret20", ("p80_90", "p90_100"), "money_ratio20", ("p80_90", "p90_100"), "observable_relative_strength_leading", "high_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_rs_market", "相对强度领先 + 弱市场", "relative_strength_regime", "relative_ret60_vs_benchmark", ("p80_90", "p90_100"), "market_regime_state", ("market_drawdown", "market_choppy"), "observable_relative_strength_leading", "high_regime", "p1_hypothesis_refine"),
        PairwiseSpec("pair_stock_lead_industry", "个股强于行业 + 行业未同步", "stock_industry_lead", "relative_ret20_vs_industry", ("p80_90", "p90_100"), "industry_regime_state", ("industry_lagging", "industry_mixed"), "observable_relative_strength_leading", "high_regime", "p1_hypothesis_refine"),
        PairwiseSpec("pair_vol_money", "低波压缩 + 放量扩张", "volatility_money", "volatility20", ("p0_10", "p10_20"), "money_ratio20", ("p80_90", "p90_100"), "observable_base_building", "low_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_repair_rs", "回撤修复 + 相对强", "repair_relative_strength", "repair_from_low120", ("p60_80", "p80_90", "p90_100"), "relative_ret20_vs_benchmark", ("p80_90", "p90_100"), "observable_repairing", "high_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_rank_industry", "全市场强排名 + 行业强宽度", "rank_industry_sync", "ret20_universe_pctile", ("p80_90", "p90_100"), "industry_width_state", ("industry_width_strong",), "observable_relative_strength_leading", "high_regime", "p1_hypothesis_refine"),
        PairwiseSpec("pair_money_near_high", "成交 regime shift + 接近新高", "money_near_high", "money_regime_shift60", ("p80_90", "p90_100"), "dist_high60", ("p80_90", "p90_100"), "observable_trend_extension", "high_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_narrow_expand", "窄幅整理 + 振幅扩张", "compression_expansion", "narrow_range10", ("true",), "range_expansion20", ("p80_90", "p90_100"), "observable_base_building", "true_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_stage_market", "可观察修复阶段 + 市场非强", "lifecycle_regime", "observable_state_stage", ("observable_repairing", "observable_relative_strength_leading"), "market_regime_state", ("market_choppy", "market_drawdown"), "observable_repairing", "stage_regime", "p1_hypothesis_refine"),
        PairwiseSpec("pair_hold_rs", "已涨20% + 仍然相对强", "continuation_hold", "post_20pct_from_recent_low", ("true",), "relative_ret20_vs_benchmark", ("p80_90", "p90_100"), "observable_20pct_from_recent_low", "true_high", "p1_hold_exit_refine"),
    ]


def build_stability_rows(
    config: dict[str, Any],
    df: pd.DataFrame,
    univariate: pd.DataFrame,
    specs: list[PrimitiveSpec],
    bins: dict[str, pd.Series],
    elig: dict[str, pd.Series],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    year_rows: list[dict[str, Any]] = []
    industry_rows: list[dict[str, Any]] = []
    if univariate.empty:
        return pd.DataFrame(), pd.DataFrame()
    target = univariate[univariate["positive_label"] == "future_50pct_high_120d"].copy()
    if target.empty:
        return pd.DataFrame(), pd.DataFrame()
    spec_by_name = {spec.feature_name: spec for spec in specs}
    best_rows = (
        target.sort_values(["feature_name", "lift_vs_baseline", "stock_day_count"], ascending=[True, False, False])
        .groupby("feature_name", as_index=False)
        .head(1)
    )
    horizon = 120
    positive_col = "is_future_50pct_high_120d"
    for _, selected in best_rows.iterrows():
        feature_name = str(selected["feature_name"])
        bin_value = str(selected["bin_value"])
        spec = spec_by_name.get(feature_name)
        if spec is None:
            continue
        eligible = elig[feature_name]
        condition = eligible & (bins[feature_name] == bin_value)
        base = baseline_mask(df, eligible, horizon, config)
        lead_mask = (condition & base).fillna(False).astype(bool)
        base_mask = base.fillna(False).astype(bool)
        for year in sorted(df.loc[lead_mask, "year"].dropna().unique()):
            year_lead_mask = lead_mask & (df["year"] == year)
            year_base_mask = base_mask & (df["year"] == year)
            year_rows.append(
                {
                    "feature_name": feature_name,
                    "bin_value": bin_value,
                    "horizon": "120d",
                    "positive_label": "future_50pct_high_120d",
                    "year": int(year),
                    "stock_day_count": int(year_lead_mask.sum()),
                    "positive_rate": float(df.loc[year_lead_mask, positive_col].mean()) if year_lead_mask.any() else np.nan,
                    "year_baseline_positive_rate": float(df.loc[year_base_mask, positive_col].mean()) if year_base_mask.any() else np.nan,
                    "lift_vs_year_baseline": safe_div(df.loc[year_lead_mask, positive_col].mean(), df.loc[year_base_mask, positive_col].mean())
                    if year_lead_mask.any() and year_base_mask.any()
                    else np.nan,
                }
            )
        for industry_name in sorted(df.loc[lead_mask, "industry_name"].dropna().astype(str).unique()):
            industry_lead_mask = lead_mask & (df["industry_name"].astype(str) == industry_name)
            industry_base_mask = base_mask & (df["industry_name"].astype(str) == industry_name)
            industry_rows.append(
                {
                    "feature_name": feature_name,
                    "bin_value": bin_value,
                    "horizon": "120d",
                    "positive_label": "future_50pct_high_120d",
                    "industry_name": industry_name,
                    "stock_day_count": int(industry_lead_mask.sum()),
                    "positive_rate": float(df.loc[industry_lead_mask, positive_col].mean()) if industry_lead_mask.any() else np.nan,
                    "industry_baseline_positive_rate": float(df.loc[industry_base_mask, positive_col].mean()) if industry_base_mask.any() else np.nan,
                    "lift_vs_industry_baseline": safe_div(df.loc[industry_lead_mask, positive_col].mean(), df.loc[industry_base_mask, positive_col].mean())
                    if industry_lead_mask.any() and industry_base_mask.any()
                    else np.nan,
                }
            )
    return pd.DataFrame(year_rows), pd.DataFrame(industry_rows)


def build_primitive_outputs(config: dict[str, Any], df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dictionary = feature_dictionary()
    specs = [spec for spec in primitive_specs() if spec.p0_enabled]
    bins: dict[str, pd.Series] = {}
    elig: dict[str, pd.Series] = {}
    for spec in specs:
        bins[spec.feature_name] = primitive_bin(df, spec, config)
        elig[spec.feature_name] = primitive_eligible(df, spec)
        df[f"bin__{spec.feature_name}"] = bins[spec.feature_name]

    coverage_rows = []
    for spec in primitive_specs():
        if not spec.p0_enabled:
            coverage_rows.append(
                {
                    "feature_name": spec.feature_name,
                    "feature_family": spec.feature_family,
                    "p0_enabled": False,
                    "eligible_rows": 0,
                    "ineligible_rows": 0,
                    "missing_value_rows": 0,
                    "insufficient_history_rows": 0,
                    "warmup_partial_year": False,
                    "warmup_partial_year_rows": 0,
                    "first_feature_eligible_date": "",
                    "coverage_note": "deferred_to_p2",
                }
            )
            continue
        eligible = elig[spec.feature_name]
        insufficient = df["available_history_trading_days"] < spec.min_history_trading_days
        warmup = insufficient & (df["year"] == parse_dt(config["dates"]["research_start"]).year)
        coverage_rows.append(
            {
                "feature_name": spec.feature_name,
                "feature_family": spec.feature_family,
                "p0_enabled": True,
                "eligible_rows": int(eligible.sum()),
                "ineligible_rows": int((~eligible).sum()),
                "missing_value_rows": int(df[spec.column].isna().sum()) if spec.column in df.columns else len(df),
                "insufficient_history_rows": int(insufficient.sum()),
                "warmup_partial_year": bool(warmup.any()),
                "warmup_partial_year_rows": int(warmup.sum()),
                "first_feature_eligible_date": iso_date(df.loc[eligible, "datetime"].min()) if eligible.any() else "",
                "coverage_note": "",
            }
        )
    feature_coverage = pd.DataFrame(coverage_rows)

    univariate_rows: list[dict[str, Any]] = []
    lead_candidates: list[dict[str, Any]] = []
    labels = [
        (120, "is_future_50pct_high_120d", "future_50pct_high_120d"),
        (240, "is_future_100pct_high_240d", "future_100pct_high_240d"),
    ]
    for spec in specs:
        eligible = elig[spec.feature_name]
        if not eligible.any():
            continue
        for bin_value in sorted(pd.Series(bins[spec.feature_name]).dropna().unique()):
            if bin_value == "missing":
                continue
            condition = eligible & (bins[spec.feature_name] == bin_value)
            for horizon, positive_col, label_name in labels:
                base = baseline_mask(df, eligible, horizon, config)
                next_phase = (
                    "p1_hold_exit_refine"
                    if spec.feature_name in {"post_20pct_from_recent_low", "post_30pct_from_recent_low"}
                    else "p1_hypothesis_refine"
                )
                row = summarize_condition(
                    df,
                    condition,
                    base,
                    positive_col,
                    horizon,
                    label_name,
                    f"uni_{spec.feature_name}_{bin_value}",
                    spec.feature_name,
                    spec.feature_family,
                    f"{spec.feature_name} == {bin_value}",
                    spec.direction_hint,
                    "mixed_observable_state",
                    next_phase,
                )
                row["feature_name"] = spec.feature_name
                row["bin_value"] = bin_value
                row["lead_type"] = "univariate_primitive"
                univariate_rows.append(row)
                if horizon == 120 and label_name == "future_50pct_high_120d":
                    lead_candidates.append(row.copy())

    pairwise_rows: list[dict[str, Any]] = []
    for pair in pairwise_specs():
        if pair.first_feature not in bins or pair.second_feature not in bins:
            continue
        eligible = elig[pair.first_feature] & elig[pair.second_feature]
        condition = eligible & bins[pair.first_feature].isin(pair.first_bins) & bins[pair.second_feature].isin(pair.second_bins)
        for horizon, positive_col, label_name in labels:
            base = baseline_mask(df, eligible, horizon, config)
            row = summarize_condition(
                df,
                condition,
                base,
                positive_col,
                horizon,
                label_name,
                pair.lead_id,
                pair.lead_name,
                pair.feature_family,
                f"{pair.first_feature} in {list(pair.first_bins)} and {pair.second_feature} in {list(pair.second_bins)}",
                pair.direction,
                pair.observable_state_stage,
                pair.recommended_next_phase,
            )
            row["first_feature"] = pair.first_feature
            row["second_feature"] = pair.second_feature
            row["lead_type"] = "pairwise_primitive"
            pairwise_rows.append(row)
            if horizon == 120 and label_name == "future_50pct_high_120d":
                lead_candidates.append(row.copy())

    univariate = pd.DataFrame(univariate_rows)
    pairwise = pd.DataFrame(pairwise_rows)
    year_stability, industry_stability = build_stability_rows(config, df, univariate, specs, bins, elig)
    leads = select_preliminary_leads(pd.DataFrame(lead_candidates), config)
    completion = build_p0_completion_audit(dictionary, univariate, pairwise, leads)
    return dictionary, feature_coverage, univariate, pairwise, year_stability, industry_stability, leads, completion


def select_preliminary_leads(candidates: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    required_cols = [
        "lead_id",
        "lead_name",
        "feature_family",
        "observable_state_stage",
        "formula_or_bin",
        "direction",
        "horizon",
        "baseline_scope",
        "stock_day_count",
        "unique_instrument_count",
        "unique_instrument_year_count",
        "unique_episode_count",
        "positive_stock_day_count",
        "positive_unique_instrument_year_count",
        "positive_unique_episode_count",
        "baseline_positive_rate",
        "lead_future_50pct_precision",
        "lead_future_100pct_precision",
        "lift_vs_baseline",
        "episode_dedup_lift",
        "instrument_year_dedup_lift",
        "year_positive_lift_count",
        "distinct_year_count",
        "distinct_industry_count",
        "industry_concentration_top1",
        "avg_lead_time_to_50pct",
        "median_lead_time_to_50pct",
        "avg_future_max_gain",
        "avg_future_drawdown_before_gain",
        "label_horizon_truncated_rate",
        "observed_reference_overlap_rate",
        "duplicate_positive_risk",
        "sparse_bin",
        "failure_reason",
        "recommended_next_phase",
    ]
    if candidates.empty:
        return pd.DataFrame(columns=required_cols)
    df = candidates.copy()
    min_samples = int(config["primitives"]["min_lead_samples"])
    score_cfg = config["primitives"]["lead_score"]
    df["candidate_ok"] = (
        (df["stock_day_count"] >= min_samples)
        & (df["lift_vs_baseline"] > 1.0)
        & (df["distinct_year_count"] >= 3)
        & (df["industry_concentration_top1"].fillna(1.0) <= 0.60)
    )
    df["score"] = (
        df["lift_vs_baseline"].fillna(0) * float(score_cfg["lift_weight"])
        + np.log1p(df["stock_day_count"].fillna(0)) * float(score_cfg["sample_log_weight"])
        + df["distinct_year_count"].fillna(0) * float(score_cfg["year_weight"])
        - df["industry_concentration_top1"].fillna(1.0) * float(score_cfg["industry_penalty"])
    )
    ranked = df.sort_values(["candidate_ok", "score"], ascending=[False, False]).copy()

    selected_rows: list[pd.Series] = []

    def add_matching(mask: pd.Series, count: int) -> None:
        nonlocal selected_rows
        existing = {str(row["lead_id"]) for row in selected_rows}
        candidate_ids = set(ranked.loc[mask, "lead_id"].astype(str))
        already_matching = sum(str(row["lead_id"]) in candidate_ids for row in selected_rows)
        needed = max(0, count - already_matching)
        if needed == 0:
            return
        added = 0
        for _, row in ranked[mask].iterrows():
            if str(row["lead_id"]) in existing:
                continue
            selected_rows.append(row)
            existing.add(str(row["lead_id"]))
            added += 1
            if added >= needed:
                break

    non_ema_mask = ~ranked["feature_family"].astype(str).str.contains("ema|breakout|pullback", case=False, regex=True)
    rs_mask = ranked["feature_family"].astype(str).str.contains(
        "relative_strength|relative_strength_regime|stock_industry_lead|rank_industry_sync|repair_relative_strength",
        case=False,
        regex=True,
    )
    money_vol_mask = ranked["feature_family"].astype(str).str.contains("money|volatility|compression", case=False, regex=True)
    hold_mask = (
        ranked["recommended_next_phase"].eq("p1_hold_exit_refine")
        | ranked["lead_id"].astype(str).str.contains("post_20|post_30|pair_hold", case=False, regex=True)
    )
    add_matching(non_ema_mask & ranked["candidate_ok"], 3)
    add_matching(rs_mask & ranked["candidate_ok"], 2)
    add_matching(money_vol_mask & ranked["candidate_ok"], 2)
    add_matching(hold_mask & ranked["candidate_ok"], 1)
    existing = {str(row["lead_id"]) for row in selected_rows}
    for _, row in ranked.iterrows():
        if str(row["lead_id"]) in existing:
            continue
        selected_rows.append(row)
        existing.add(str(row["lead_id"]))
        if len(selected_rows) >= 8:
            break
    result = pd.DataFrame(selected_rows)
    if result.empty:
        result = ranked.head(5).copy()
    result = result.head(max(5, min(8, len(result)))).copy()
    result["lead_rank"] = range(1, len(result) + 1)
    for column in required_cols:
        if column not in result.columns:
            result[column] = np.nan
    return result[["lead_rank"] + required_cols]


def build_p0_completion_audit(dictionary: pd.DataFrame, univariate: pd.DataFrame, pairwise: pd.DataFrame, leads: pd.DataFrame) -> pd.DataFrame:
    enabled = dictionary[dictionary["p0_enabled"].astype(bool)]
    family_count = int(dictionary["feature_family"].nunique())
    univariate_count = int(enabled["feature_name"].nunique())
    pairwise_count = int(pairwise["lead_id"].nunique()) if not pairwise.empty else 0
    lead_count = int(len(leads))
    non_ema_leads = int((~leads["feature_family"].astype(str).str.contains("ema|breakout|pullback", case=False, regex=True)).sum()) if not leads.empty else 0
    rs_leads = (
        int(
            leads["feature_family"]
            .astype(str)
            .str.contains(
                "relative_strength|relative_strength_regime|stock_industry_lead|rank_industry_sync|repair_relative_strength",
                case=False,
                regex=True,
            )
            .sum()
        )
        if not leads.empty
        else 0
    )
    money_vol_leads = int(leads["feature_family"].astype(str).str.contains("money|volatility|compression", case=False, regex=True).sum()) if not leads.empty else 0
    hold_leads = (
        int(
            (
                leads["recommended_next_phase"].eq("p1_hold_exit_refine")
                | leads["lead_id"].astype(str).str.contains("post_20|post_30|pair_hold", case=False, regex=True)
            ).sum()
        )
        if not leads.empty
        else 0
    )
    broad_met = (
        family_count >= 10
        and univariate_count >= 30
        and pairwise_count >= 10
        and lead_count >= 5
        and non_ema_leads >= 3
        and rs_leads >= 2
        and money_vol_leads >= 2
        and hold_leads >= 1
    )
    rows = [
        ("registry_feature_family_count", family_count, 10, family_count >= 10, ""),
        ("p0_univariate_primitive_count", univariate_count, 30, univariate_count >= 30, ""),
        ("p0_pairwise_combo_count", pairwise_count, 10, pairwise_count >= 10, ""),
        ("preliminary_discovery_lead_count", lead_count, 5, lead_count >= 5, ""),
        ("non_ema_breakout_pullback_lead_count", non_ema_leads, 3, non_ema_leads >= 3, ""),
        ("relative_strength_or_industry_lead_count", rs_leads, 2, rs_leads >= 2, ""),
        ("money_or_volatility_lead_count", money_vol_leads, 2, money_vol_leads >= 2, ""),
        ("continuation_or_hold_lead_count", hold_leads, 1, hold_leads >= 1, ""),
        ("broad_discovery_p0_minimum_coverage_met", int(broad_met), 1, broad_met, "" if broad_met else "minimum coverage requirement not fully met"),
    ]
    return pd.DataFrame(rows, columns=["check_name", "actual_value", "required_value", "passed", "failure_reason"])


def command_self_test(config: dict[str, Any]) -> list[Path]:
    ensure_dir(report_dir(config))
    ensure_dir(cache_dir(config))
    if not bool(config["universe"].get("point_in_time", False)):
        raise DataGateError("point_in_time universe must be true")
    if not bool(config["industry"].get("point_in_time", False)):
        raise DataGateError("point_in_time industry membership must be true")
    if config["qlib"].get("price_adjustment_mode") != "provider_ohlc_already_adjusted":
        raise DataGateError("Explore9 requires provider_ohlc_already_adjusted price mode")
    audit = build_source_data_audit(config)
    validate_source_audit(audit)
    summary = {
        "structural_input_count": int((audit["category"] == "structural_input").sum()),
        "background_reference_count": int((audit["category"] == "background_reference").sum()),
        "schema_reference_count": int((audit["category"] == "schema_reference_audit_only").sum()),
        "forbidden_result_path_count": int((audit["category"] == "forbidden_result_path").sum()),
        "forbidden_result_path_used_for_calculation": False,
        "explore8_reference_use": "background_schema_audit_only",
    }
    outputs = [
        write_csv(audit, report_dir(config) / "source_data_audit.csv"),
        write_json(summary, report_dir(config) / "source_data_audit_summary.json"),
    ]
    record_manifest(config, "self-test", outputs, {"self_test_passed": True})
    print(f"self-test passed structural_inputs={summary['structural_input_count']}", flush=True)
    return outputs


def command_build_labels(config: dict[str, Any]) -> list[Path]:
    command_self_test(config)
    universe = read_universe(config)
    industry = read_industry(config)
    target_history = read_target_history(config)
    panel, provider_meta = load_stock_panel(config)
    coverage, coverage_summary = build_provider_coverage_audit(config, universe, industry, panel, provider_meta, target_history)
    features = add_stock_features(config, panel, universe, industry, target_history)
    labels = add_forward_labels(features, config)
    episodes = build_episode_lifecycle_labels(config, labels)
    labels = attach_retrospective_stage(labels, episodes)
    label_coverage = build_label_coverage_audit(config, labels, coverage)
    summary, by_year, by_industry, observed_audit = build_label_summaries(config, labels)
    panel_path = label_panel_path(config)
    ensure_parent(panel_path)
    labels.to_parquet(panel_path, index=False)
    meta = {
        "row_count": int(len(labels)),
        "column_count": int(len(labels.columns)),
        "instrument_count": int(labels["instrument"].nunique()),
        "first_date": iso_date(labels["datetime"].min()),
        "last_date": iso_date(labels["datetime"].max()),
    }
    write_json(meta, cache_dir(config) / "stock_day_label_panel_meta.json")
    outputs = [
        write_csv(coverage, report_dir(config) / "provider_coverage_audit.csv"),
        write_json(coverage_summary, report_dir(config) / "provider_coverage_audit_summary.json"),
        write_csv(label_coverage, report_dir(config) / "label_coverage_audit.csv"),
        write_csv(summary, report_dir(config) / "stock_day_label_panel_summary.csv"),
        write_csv(episodes, report_dir(config) / "episode_lifecycle_labels.csv"),
        write_csv(by_year, report_dir(config) / "label_distribution_by_year.csv"),
        write_csv(by_industry, report_dir(config) / "label_distribution_by_industry.csv"),
        write_csv(observed_audit, report_dir(config) / "observed_reference_label_audit.csv"),
        panel_path,
    ]
    record_manifest(
        config,
        "build-labels",
        outputs,
        {
            "provider_coverage_limited_research": coverage_summary["coverage_limited_research"],
            "stock_day_label_rows": int(len(labels)),
            "episode_lifecycle_rows": int(len(episodes)),
            "labels_used_for_trading_signal": False,
            "future_labels_used_as_features": False,
        },
    )
    print(f"built labels rows={len(labels)} episodes={len(episodes)}", flush=True)
    return outputs


def command_profile_primitives(config: dict[str, Any]) -> list[Path]:
    if not label_panel_path(config).exists():
        command_build_labels(config)
    df = pd.read_parquet(label_panel_path(config))
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.normalize()
    if "first_feature_eligible_date" in df.columns:
        df["first_feature_eligible_date"] = pd.to_datetime(df["first_feature_eligible_date"], errors="coerce")
    outputs_tuple = build_primitive_outputs(config, df)
    dictionary, coverage, univariate, pairwise, year_stability, industry_stability, leads, completion = outputs_tuple
    outputs = [
        write_csv(dictionary, report_dir(config) / "primitive_feature_dictionary.csv"),
        write_csv(coverage, report_dir(config) / "primitive_feature_coverage.csv"),
        write_csv(univariate, report_dir(config) / "primitive_univariate_lift.csv"),
        write_csv(pairwise, report_dir(config) / "primitive_pairwise_lift.csv"),
        write_csv(year_stability, report_dir(config) / "primitive_year_stability.csv"),
        write_csv(industry_stability, report_dir(config) / "primitive_industry_stability.csv"),
        write_csv(leads, report_dir(config) / "preliminary_discovery_leads.csv"),
        write_csv(completion, report_dir(config) / "p0_scope_completion_audit.csv"),
    ]
    broad_met = bool(completion.loc[completion["check_name"] == "broad_discovery_p0_minimum_coverage_met", "passed"].iloc[0]) if not completion.empty else False
    record_manifest(
        config,
        "profile-primitives",
        outputs,
        {
            "p0_univariate_primitive_count": int(dictionary[dictionary["p0_enabled"].astype(bool)]["feature_name"].nunique()),
            "p0_pairwise_combo_count": int(pairwise["lead_id"].nunique()) if not pairwise.empty else 0,
            "preliminary_discovery_lead_count": int(len(leads)),
            "broad_discovery_p0_minimum_coverage_met": broad_met,
            "formal_hypothesis_generated": False,
            "strategy_backtest_generated": False,
        },
    )
    print(f"profiled primitives univariate_rows={len(univariate)} pairwise_rows={len(pairwise)} leads={len(leads)}", flush=True)
    return outputs


def command_explore9_report(config: dict[str, Any]) -> list[Path]:
    required = [
        "provider_coverage_audit.csv",
        "label_coverage_audit.csv",
        "label_distribution_by_year.csv",
        "primitive_feature_dictionary.csv",
        "primitive_feature_coverage.csv",
        "primitive_univariate_lift.csv",
        "primitive_pairwise_lift.csv",
        "preliminary_discovery_leads.csv",
        "p0_scope_completion_audit.csv",
    ]
    if any(not (report_dir(config) / name).exists() for name in required):
        command_profile_primitives(config)
    report_path = report_dir(config) / "explore9_broad_discovery_report.md"
    coverage = read_csv_if_exists(report_dir(config) / "provider_coverage_audit.csv")
    label_coverage = read_csv_if_exists(report_dir(config) / "label_coverage_audit.csv")
    by_year = read_csv_if_exists(report_dir(config) / "label_distribution_by_year.csv")
    dictionary = read_csv_if_exists(report_dir(config) / "primitive_feature_dictionary.csv")
    feature_coverage = read_csv_if_exists(report_dir(config) / "primitive_feature_coverage.csv")
    univariate = read_csv_if_exists(report_dir(config) / "primitive_univariate_lift.csv")
    pairwise = read_csv_if_exists(report_dir(config) / "primitive_pairwise_lift.csv")
    leads = read_csv_if_exists(report_dir(config) / "preliminary_discovery_leads.csv")
    completion = read_csv_if_exists(report_dir(config) / "p0_scope_completion_audit.csv")
    manifest = read_json(manifest_path(config))
    broad_met = False
    if not completion.empty:
        row = completion[completion["check_name"] == "broad_discovery_p0_minimum_coverage_met"]
        broad_met = bool(row["passed"].iloc[0]) if not row.empty else False

    lines: list[str] = []
    lines.append("# Explore9 P0 大涨股早期结构广度探索报告")
    lines.append("")
    lines.append("## 结论摘要")
    lines.append("")
    lines.append(f"- `broad_discovery_p0_minimum_coverage_met = {str(broad_met).lower()}`。")
    lines.append("- Explore9 P0 只做 broad discovery：没有生成 formal hypothesis，没有做策略回测，也没有输出 frozen strategy。")
    lines.append("- Explore8 输出仅作为背景和 schema/audit reference；本轮标签、episode、原语和 lift 均从 PIT universe 与 provider 行情独立重算。")
    if not leads.empty:
        good = leads[leads["failure_reason"].fillna("") == ""]
        lines.append(f"- 初步线索共输出 `{len(leads)}` 条，其中无失败标记 `{len(good)}` 条；这些线索只能进入 P1/P2 细化，不代表可交易规则。")
    lines.append("")
    lines.append("## 数据覆盖与标签质量")
    lines.append("")
    if not coverage.empty:
        table_rows = []
        for _, row in coverage[coverage["year"].isin(research_years(config))].iterrows():
            table_rows.append(
                [
                    int(row["year"]),
                    row["coverage_status"],
                    format_pct(row["required_field_coverage_ratio"]),
                    int(row["pit_membership_rows"]),
                    int(row["rows_with_all_required_fields"]),
                ]
            )
        lines.extend(markdown_table(["年份", "覆盖状态", "必需字段覆盖率", "PIT样本", "可读样本"], table_rows[:12]))
        lines.append("")
    if not label_coverage.empty:
        table_rows = []
        for _, row in label_coverage.iterrows():
            table_rows.append(
                [
                    row["horizon"],
                    int(row["research_stock_day_rows"]),
                    int(row["horizon_valid_rows"]),
                    int(row["observed_reference_overlap_rows"]),
                    int(row["future_50pct_high_positive_rows"]),
                    int(row["future_100pct_high_positive_rows"]),
                ]
            )
        lines.extend(markdown_table(["Horizon", "研究样本", "有效样本", "跨入2025-2026", "50% high+", "100% high+"], table_rows))
        lines.append("")
    if not by_year.empty:
        lines.append("年度标签分布显示 2017-2024 内存在足够多的 forward winner 样本，但 120/240 日窗口在 2024 年会自然跨入 observed reference，因此主 lift 已排除这些 overlap 样本。")
        table_rows = []
        for _, row in by_year.iterrows():
            table_rows.append(
                [
                    int(row["year"]),
                    int(row["stock_day_count"]),
                    format_pct(row["future_50pct_high_120d_rate"]),
                    format_pct(row["future_100pct_high_240d_rate"]),
                    format_pct(row["horizon_240d_observed_reference_overlap_rate"]),
                ]
            )
        lines.extend(markdown_table(["年份", "样本", "120d 50% high", "240d 100% high", "240d overlap"], table_rows))
        lines.append("")
    lines.append("## Explore8 发现到 Explore9 问题的转换")
    lines.append("")
    lines.append("- Explore8 证明既有 EMA / breakout / pullback 规则主要问题是 `no_signal` 和 `late_signal`，所以 Explore9 不继续做局部参数搜索。")
    lines.append("- P0 将问题改写为：哪些 T 日可观察的价格、成交、相对强度、波动、行业与生命周期状态，在未来 120/240 日 winner 标签上有可复核 lift。")
    lines.append("- `low_date`、未来高点和未来收益只用于标签与 retrospective lifecycle，不进入 T 日 primitive 或 lead 公式。")
    lines.append("")
    lines.append("## 原语覆盖与稳定性")
    lines.append("")
    family_count = int(dictionary["feature_family"].nunique()) if not dictionary.empty else 0
    enabled_count = int(dictionary[dictionary["p0_enabled"].astype(bool)]["feature_name"].nunique()) if not dictionary.empty else 0
    pair_count = int(pairwise["lead_id"].nunique()) if not pairwise.empty else 0
    lines.append(f"- registry 覆盖 `{family_count}` 类 feature family，P0 启用 `{enabled_count}` 个单变量原语，双变量组合 `{pair_count}` 个。")
    if not feature_coverage.empty:
        warmup_limited = feature_coverage[feature_coverage["warmup_partial_year"].fillna(False).astype(bool)]
        lines.append(f"- warmup 受限原语 `{len(warmup_limited)}` 个；2017 年长窗口结论需要按 coverage audit 降级理解。")
    if not univariate.empty:
        top_uni = univariate[(univariate["positive_label"] == "future_50pct_high_120d") & (univariate["stock_day_count"] >= 200)].sort_values("lift_vs_baseline", ascending=False).head(10)
        table_rows = []
        for _, row in top_uni.iterrows():
            table_rows.append(
                [
                    row["lead_name"],
                    row["formula_or_bin"],
                    int(row["stock_day_count"]),
                    format_pct(row["lead_positive_rate"]),
                    format_float(row["lift_vs_baseline"]),
                    int(row["distinct_year_count"]),
                    format_pct(row["industry_concentration_top1"]),
                ]
            )
        lines.extend(markdown_table(["原语", "分箱", "样本", "命中率", "lift", "年份", "行业Top1"], table_rows))
        lines.append("")
    if not pairwise.empty:
        top_pair = pairwise[(pairwise["positive_label"] == "future_50pct_high_120d")].sort_values("lift_vs_baseline", ascending=False).head(10)
        table_rows = []
        for _, row in top_pair.iterrows():
            table_rows.append(
                [
                    row["lead_name"],
                    int(row["stock_day_count"]),
                    format_pct(row["lead_positive_rate"]),
                    format_float(row["lift_vs_baseline"]),
                    int(row["distinct_year_count"]),
                    row["recommended_next_phase"],
                ]
            )
        lines.extend(markdown_table(["双变量线索", "样本", "命中率", "lift", "年份", "建议"], table_rows))
        lines.append("")
    lines.append("## Preliminary Discovery Leads")
    lines.append("")
    if leads.empty:
        lines.append("未发现足够稳定的早期结构，下一阶段不应进入 P1 hypothesis 细化或策略回测，应继续数据画像或扩大数据维度。")
    else:
        table_rows = []
        for _, row in leads.iterrows():
            table_rows.append(
                [
                    int(row["lead_rank"]),
                    row["lead_name"],
                    row["feature_family"],
                    int(row["stock_day_count"]),
                    format_float(row["lift_vs_baseline"]),
                    int(row["distinct_year_count"]),
                    format_pct(row["industry_concentration_top1"]),
                    row["recommended_next_phase"],
                    row["failure_reason"] if isinstance(row["failure_reason"], str) else "",
                ]
            )
        lines.extend(markdown_table(["Rank", "线索", "family", "样本", "lift", "年份", "行业Top1", "下一步", "失败原因"], table_rows))
        lines.append("")
        lines.append("- 非 EMA / 非 breakout / 非 pullback 的线索优先进入 P1，因为它们更符合 Explore8 暴露出的早期发现缺口。")
        lines.append("- 相对强度、行业不同步下的个股领先、成交 regime shift 和波动压缩扩张，是 P0 中最值得继续审计的方向。")
        lines.append("- continuation / hold 线索只说明已有 20% 修复后的延展概率值得分析，不构成退出规则替代。")
    lines.append("")
    lines.append("## 淘汰与降级方向")
    lines.append("")
    if not univariate.empty:
        weak = univariate[(univariate["positive_label"] == "future_50pct_high_120d") & (univariate["stock_day_count"] >= 200) & (univariate["lift_vs_baseline"] <= 1.0)]
        weak_families = ", ".join(sorted(weak["feature_family"].dropna().astype(str).unique())[:8])
        lines.append(f"- 样本足够但 lift 不高于 baseline 的方向不会进入 P1；当前涉及 family：{weak_families or 'NA'}。")
    lines.append("- 单一年份或单一行业贡献过高的线索只保留为 diagnostic，不作为 general hypothesis。")
    lines.append("- observed reference overlap 样本不进入主选择，所以 2025-2026 只能用于后续复核，不参与阈值和 family 选择。")
    lines.append("")
    lines.append("## P1 / P2 建议")
    lines.append("")
    if broad_met and not leads.empty and (leads["failure_reason"].fillna("") == "").any():
        lines.append("- 具备进入 P1 hypothesis refine 的基础，但 P1 必须重新固定 human-readable formula、年度 breakdown 和 failure modes。")
        lines.append("- P2 shape clustering 仍应等待 P1 明确要解释的窗口和样本，不应直接抢先变成策略搜索。")
    else:
        lines.append("- P0 最低覆盖或稳定线索不足，暂不建议进入策略回测；应先补足数据覆盖、warmup 或 primitive family。")
    lines.append("")
    lines.append("## Manifest 纪律")
    lines.append("")
    manifest_flags = [
        "explore8_profile_csv_used_for_label",
        "explore8_profile_csv_used_for_signal",
        "explore8_profile_csv_used_for_selection",
        "historical_trade_results_used_for_labeling",
        "historical_trade_results_used_for_signal",
        "observed_reference_used_for_selection",
    ]
    for flag in manifest_flags:
        lines.append(f"- `{flag} = {str(bool(manifest.get(flag, False))).lower()}`")
    lines.append("")
    lines.append("Explore10 只能作为远期路径记录；是否进入回测必须等待 P1/P2 完成后重新评估。")
    ensure_parent(report_path)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs = [report_path]
    record_manifest(config, "explore9-report", outputs, {"report_generated": True, "broad_discovery_p0_minimum_coverage_met": broad_met})
    print(f"wrote report {relpath(report_path)}", flush=True)
    return outputs


def command_all(config: dict[str, Any]) -> list[Path]:
    outputs: list[Path] = []
    outputs.extend(command_build_labels(config))
    outputs.extend(command_profile_primitives(config))
    outputs.extend(command_explore9_report(config))
    return outputs


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["self-test", "build-labels", "profile-primitives", "explore9-report", "all"],
        help="Explore9 command to run",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to Explore9 YAML config")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    config = load_config(args.config)
    try:
        if args.command == "self-test":
            command_self_test(config)
        elif args.command == "build-labels":
            command_build_labels(config)
        elif args.command == "profile-primitives":
            command_profile_primitives(config)
        elif args.command == "explore9-report":
            command_explore9_report(config)
        elif args.command == "all":
            command_all(config)
        else:
            raise DataGateError(f"unknown command: {args.command}")
    except DataGateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

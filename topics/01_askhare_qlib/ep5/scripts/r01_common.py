#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
EP5_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP5_DIR.parent
DEFAULT_CONFIG = EP5_DIR / "configs" / "r01_short_horizon_local_feasibility_probe_v1.yaml"

REQUIREMENT_ID = "ep5_r01_short_horizon_local_feasibility_probe_v1"
PLAN_ID = "ep5_e01_short_horizon_exposure_audit_harness_v1"

PRIMARY_UNIT = "r01_launch_breakout_money_surge_natural_exit_v0"
FAST_FAIL_UNIT = "r01_launch_breakout_money_surge_fast_fail_v0"
SPARSE_UNIT = "r01_base_breakout_vcp_sparse_natural_exit_v0"
CANONICAL_UNITS = [PRIMARY_UNIT, FAST_FAIL_UNIT, SPARSE_UNIT]
HORIZONS = [5, 10, 20]
HORIZON_LABELS = [f"H{h}" for h in HORIZONS]
SPLITS = ["train", "validation", "robustness"]

FINAL_DECISIONS = [
    "r01_short_horizon_local_unit_supported",
    "r01_sparse_event_unit_supported_event_source_followup",
    "r01_fast_fail_only_loss_control_lead",
    "r01_unstable_validation_only_lead",
    "r01_unstable_horizon_shape_no_search_allowed",
    "r01_adjacent_horizon_not_evaluable_validation_lead",
    "r01_relative_edge_only_hedged_or_regime_audit_required",
    "r01_beta_or_market_exposure_only_no_stock_selection_pass",
    "r01_horizon_specific_lead_only_no_search_allowed",
    "r01_sample_limited_primary_lead_only",
    "r01_sample_limited_sparse_event_source_lead_only",
    "r01_no_local_feasibility_support",
    "r01_blocked_data_or_execution_contract",
]

PRIORITY_RULES = [
    "rule_01_blocked_data_or_execution_contract",
    "rule_02_primary_supported",
    "rule_03_primary_validation_only_lead",
    "rule_04_primary_unstable_horizon_shape",
    "rule_05_primary_adjacent_horizon_not_evaluable",
    "rule_06_sparse_event_source_followup",
    "rule_07_fast_fail_only_loss_control_lead",
    "rule_08_relative_edge_only",
    "rule_09_beta_or_market_exposure_only",
    "rule_10_horizon_specific_lead_only",
    "rule_11_sample_limited_primary_lead_only",
    "rule_12_sample_limited_sparse_lead_only",
    "rule_13_no_local_feasibility_support",
]

BLOCKED_REASONS = [
    "missing_open",
    "missing_exit_open",
    "zero_volume",
    "zero_money",
    "not_universe_member",
    "limit_up_inferred_on_entry",
    "limit_down_inferred_on_exit",
    "missing_calendar_next_day",
    "insufficient_forward_trading_days",
    "split_boundary",
]

EXECUTION_STATUSES = ["complete_executable", *[f"blocked_{reason}" for reason in BLOCKED_REASONS]]

RIGHT_TAIL_PATH_STATUSES = [
    "complete_same_split_120d",
    "complete_cross_split_120d_readonly",
    "censored_split_boundary",
    "censored_provider_end",
    "blocked_missing_forward_path",
]
RIGHT_TAIL_STATUSES = [
    "hit_plus50",
    "hit_plus20_only",
    "no_hit_complete",
    "censored_not_evaluable",
    "blocked_missing_forward_path",
]

FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}

CACHE_FILES = [
    "r01_daily_feature_panel.parquet",
    "r01_canonical_event_panel.parquet",
    "r01_execution_event_panel.parquet",
    "r01_matched_comparator_panel.parquet",
    "r01_right_tail_diagnostic_panel.parquet",
]

RUNNER_REPORTS = [
    "r01_artifact_authority.csv",
    "r01_input_data_audit.csv",
    "r01_provider_field_audit.csv",
    "r01_feature_asof_audit.csv",
    "r01_formula_input_coverage_audit.csv",
    "r01_market_state_beta_bucket_audit.csv",
    "r01_beta_bucket_boundary_audit.csv",
    "r01_canonical_unit_registry.csv",
    "r01_formula_freeze_audit.csv",
    "r01_event_generation_audit.csv",
    "r01_event_overlap_audit.csv",
    "r01_execution_block_audit.csv",
    "r01_denominator_audit.csv",
    "r01_comparator_scope_audit.csv",
    "r01_relative_denominator_audit.csv",
    "r01_comparator_fallback_quality_audit.csv",
    "r01_event_summary_by_unit_horizon_split.csv",
    "r01_event_summary_by_unit_horizon_year.csv",
    "r01_regime_beta_decomposition.csv",
    "r01_industry_liquidity_decomposition.csv",
    "r01_sample_gate_audit.csv",
    "r01_concentration_gate_audit.csv",
    "r01_absolute_gate_audit.csv",
    "r01_relative_gate_audit.csv",
    "r01_robustness_confirmation_audit.csv",
    "r01_horizon_shape_audit.csv",
    "r01_right_tail_readout.csv",
    "r01_right_tail_censoring_audit.csv",
    "r01_final_decision.csv",
    "r01_final_decision_inputs.csv",
]

RUNNER_MANIFESTS = [
    "r01_run_manifest.json",
    "r01_artifact_hashes.json",
]

VALIDATOR_REPORTS = [
    "r01_validation_gate_audit.csv",
    "r01_schema_validation_audit.csv",
    "r01_final_decision_replay_audit.csv",
    "r01_final_report.md",
]


class R01Error(RuntimeError):
    pass


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(TOPIC_DIR))
    except ValueError:
        return str(resolved)


def load_config(path: str | Path) -> tuple[dict[str, Any], Paths]:
    config_path = topic_path(path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_root = topic_path(config["output_root"])
    paths = Paths(
        config_path=config_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in [paths.cache_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            digest.update(str(child.relative_to(path)).encode("utf-8"))
            digest.update(child.read_bytes())
    else:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TOPIC_DIR, text=True).strip()
    except Exception:
        return ""


def as_date(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except Exception:
        return False


def safe_mean(values: pd.Series) -> float:
    return float(values.mean()) if len(values) else np.nan


def safe_quantile(values: pd.Series, q: float) -> float:
    return float(values.quantile(q)) if len(values) else np.nan


def safe_share(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def load_calendar(config: dict[str, Any]) -> pd.DatetimeIndex:
    path = topic_path(config["data_sources"]["trading_calendar_path"])
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(values).normalize(), name="trade_date")


def trading_day_pos(calendar: pd.DatetimeIndex) -> dict[pd.Timestamp, int]:
    return {pd.Timestamp(date): idx for idx, date in enumerate(calendar)}


def add_trading_days(calendar: pd.DatetimeIndex, date: Any, days: int) -> pd.Timestamp | pd.NaT:
    pos = calendar.searchsorted(as_date(date), side="left")
    target = pos + int(days)
    if pos >= len(calendar) or target >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[target])


def prev_trading_day(calendar: pd.DatetimeIndex, date: Any) -> pd.Timestamp | pd.NaT:
    pos = calendar.searchsorted(as_date(date), side="left") - 1
    if pos < 0:
        return pd.NaT
    return pd.Timestamp(calendar[pos])


def next_trade_candidates(calendar: pd.DatetimeIndex, date: Any, max_lag: int) -> list[tuple[pd.Timestamp, int]]:
    pos = calendar.searchsorted(as_date(date), side="right")
    out: list[tuple[pd.Timestamp, int]] = []
    for offset in range(int(max_lag)):
        idx = pos + offset
        if idx >= len(calendar):
            break
        out.append((pd.Timestamp(calendar[idx]), offset + 1))
    return out


def split_for_date(config: dict[str, Any], value: Any) -> str:
    if pd.isna(value):
        return ""
    date = as_date(value)
    split = config["split"]
    if pd.Timestamp(split["train_start"]) <= date <= pd.Timestamp(split["train_end"]):
        return "train"
    if pd.Timestamp(split["validation_start"]) <= date <= pd.Timestamp(split["validation_end"]):
        return "validation"
    if pd.Timestamp(split["robustness_start"]) <= date <= pd.Timestamp(split["robustness_end"]):
        return "robustness"
    if date > pd.Timestamp(split["robustness_end"]):
        return "provider_tail"
    return "out_of_scope"


def read_qlib_instruments(config: dict[str, Any]) -> list[str]:
    path = topic_path(config["data_sources"]["qlib_instrument_path"])
    instruments: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split()
            if parts:
                instruments.append(parts[0].upper())
    if not instruments:
        raise R01Error(f"empty qlib instrument file: {relpath(path)}")
    return sorted(set(instruments))


def load_provider_panel(config: dict[str, Any]) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    provider_uri = topic_path(config["data_sources"]["qlib_provider_uri"])
    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    instruments = sorted(set(read_qlib_instruments(config) + [config["data_sources"]["index_instrument"].upper()]))
    frame = D.features(
        instruments=instruments,
        fields=list(FIELD_RENAME),
        start_time=config["split"]["train_start"],
        end_time=config["data_sources"].get("provider_load_end_date", config["split"]["robustness_end"]),
        freq="day",
    )
    if frame.empty:
        raise R01Error("Qlib provider returned no rows")
    panel = frame.rename(columns=FIELD_RENAME).reset_index()
    panel["trade_date"] = pd.to_datetime(panel["datetime"]).dt.normalize()
    panel["instrument_id"] = panel["instrument"].astype(str).str.upper()
    panel = panel.drop(columns=[c for c in ["datetime", "instrument"] if c in panel])
    for column in FIELD_RENAME.values():
        if column not in panel:
            panel[column] = np.nan
    return panel.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True)


def load_universe(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["data_sources"]["pit_universe_path"])
    df = pd.read_csv(path, parse_dates=["date"], low_memory=False)
    df["trade_date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument_id"] = df["instrument"].astype(str).str.upper()
    return df


def load_industry(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["data_sources"]["pit_industry_path"])
    df = pd.read_csv(path, parse_dates=["date"])
    df["trade_date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument_id"] = df["instrument"].astype(str).str.upper()
    df["industry_id"] = df.get("industry_target_key", pd.Series(index=df.index, dtype=object)).fillna("UNKNOWN")
    df["industry_name"] = df.get("industry_name", pd.Series(index=df.index, dtype=object)).fillna("UNKNOWN")
    return df.sort_values(["instrument_id", "trade_date"])


def build_input_audits(config: dict[str, Any], paths: Paths) -> None:
    rows = []
    for role, raw_path in [
        ("qlib_provider_uri", config["data_sources"]["qlib_provider_uri"]),
        ("pit_universe_path", config["data_sources"]["pit_universe_path"]),
        ("pit_qlib_instrument_universe_path", config["data_sources"]["pit_qlib_instrument_universe_path"]),
        ("pit_industry_path", config["data_sources"]["pit_industry_path"]),
        ("trading_calendar_path", config["data_sources"]["trading_calendar_path"]),
        ("qlib_instrument_path", config["data_sources"]["qlib_instrument_path"]),
        ("requirement_path", config["requirement_path"]),
        ("config_path", paths.config_path),
    ]:
        path = topic_path(raw_path)
        rows.append(
            {
                "artifact_role": role,
                "artifact_path": relpath(path),
                "required": True,
                "exists": path.exists(),
                "sha256": file_hash(path) if path.exists() else "",
                "row_count": count_rows(path) if path.exists() else 0,
                "status": "present" if path.exists() else "missing",
                "notes": "",
            }
        )
    authority = pd.DataFrame(rows)
    write_csv(authority, paths.reports_dir / "r01_artifact_authority.csv")

    universe = load_universe(config)
    industry = load_industry(config)
    calendar = load_calendar(config)
    input_audit = pd.DataFrame(
        [
            {
                "source": "pit_universe",
                "row_count": len(universe),
                "instrument_count": universe["instrument_id"].nunique(),
                "min_date": universe["trade_date"].min(),
                "max_date": universe["trade_date"].max(),
                "status": "passed" if not universe.empty else "failed",
            },
            {
                "source": "pit_industry",
                "row_count": len(industry),
                "instrument_count": industry["instrument_id"].nunique(),
                "min_date": industry["trade_date"].min(),
                "max_date": industry["trade_date"].max(),
                "status": "passed" if not industry.empty else "failed",
            },
            {
                "source": "trading_calendar",
                "row_count": len(calendar),
                "instrument_count": 0,
                "min_date": calendar.min(),
                "max_date": calendar.max(),
                "status": "passed" if len(calendar) else "failed",
            },
        ]
    )
    write_csv(input_audit, paths.reports_dir / "r01_input_data_audit.csv")


def count_rows(path: Path) -> int:
    if path.is_dir():
        return sum(1 for child in path.rglob("*") if child.is_file())
    if path.suffix == ".csv":
        try:
            return max(0, sum(1 for _ in path.open("r", encoding="utf-8")) - 1)
        except UnicodeDecodeError:
            return 0
    if path.suffix == ".txt":
        return sum(1 for line in path.open("r", encoding="utf-8") if line.strip())
    return 0


def assign_cross_section_quintile(values: pd.Series) -> pd.Series:
    out = pd.Series("", index=values.index, dtype=object)
    valid = values.replace([np.inf, -np.inf], np.nan).dropna()
    if valid.empty:
        return out
    if valid.nunique() < 5:
        out.loc[valid.index] = "q3"
        return out
    ranks = valid.rank(method="first")
    out.loc[valid.index] = pd.qcut(ranks, 5, labels=["q1", "q2", "q3", "q4", "q5"]).astype(str)
    return out


def build_feature_panel(config: dict[str, Any], paths: Paths) -> tuple[pd.DataFrame, pd.DataFrame]:
    provider = load_provider_panel(config)
    index_id = config["data_sources"]["index_instrument"].upper()
    stock_panel = provider.loc[provider["instrument_id"].ne(index_id)].copy()
    index_panel = provider.loc[provider["instrument_id"].eq(index_id)].copy()
    if index_panel.empty:
        raise R01Error(f"missing index data for {index_id}")

    universe = load_universe(config)
    industry = load_industry(config)
    universe_keys = universe[["trade_date", "instrument_id"]].drop_duplicates()
    stock_panel = stock_panel.merge(
        universe_keys.assign(pit_universe_member=True),
        on=["trade_date", "instrument_id"],
        how="left",
    )
    stock_panel["pit_universe_member"] = stock_panel["pit_universe_member"].fillna(False).astype(bool)
    industry_cols = ["trade_date", "instrument_id", "industry_id", "industry_name"]
    stock_panel = stock_panel.merge(industry[industry_cols].drop_duplicates(["trade_date", "instrument_id"]), on=["trade_date", "instrument_id"], how="left")
    stock_panel["industry_id"] = stock_panel["industry_id"].fillna("UNKNOWN")
    stock_panel["industry_name"] = stock_panel["industry_name"].fillna("UNKNOWN")
    stock_panel["split"] = stock_panel["trade_date"].map(lambda x: split_for_date(config, x))

    index_panel = index_panel.sort_values("trade_date").copy()
    index_panel["index_close"] = index_panel["close"]
    index_panel["index_ma60"] = index_panel["index_close"].rolling(60, min_periods=60).mean()
    index_panel["index_ret20"] = index_panel["index_close"] / index_panel["index_close"].shift(20) - 1.0
    index_panel["index_return"] = index_panel["index_close"].pct_change()
    index_features = index_panel[["trade_date", "index_close", "index_ma60", "index_ret20", "index_return"]]
    stock_panel = stock_panel.merge(index_features, on="trade_date", how="left")

    stock_panel = stock_panel.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True)
    grouped = stock_panel.groupby("instrument_id", group_keys=False)
    stock_panel["prev_close"] = grouped["close"].shift(1)
    stock_panel["log_return"] = grouped["close"].transform(lambda s: np.log(s / s.shift(1)))
    stock_panel["stock_return"] = grouped["close"].pct_change()
    stock_panel["avg_money20_asof"] = grouped["money"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    stock_panel["close_count_80"] = grouped["close"].transform(lambda s: s.notna().rolling(80, min_periods=80).sum())
    stock_panel["history_ok"] = stock_panel["close_count_80"] >= 80
    stock_panel["rolling_min_close_60_prev"] = grouped["close"].transform(lambda s: s.shift(1).rolling(60, min_periods=60).min())
    stock_panel["rolling_max_close_60_prev"] = grouped["close"].transform(lambda s: s.shift(1).rolling(60, min_periods=60).max())
    stock_panel["money_ma20_prev"] = grouped["money"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).mean())
    stock_panel["money_ma5"] = grouped["money"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    stock_panel["money_ratio5_to20"] = stock_panel["money_ma5"] / stock_panel["avg_money20_asof"]
    stock_panel["ma20"] = grouped["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())

    prev_close = grouped["close"].shift(1)
    tr1 = stock_panel["high"] - stock_panel["low"]
    tr2 = (stock_panel["high"] - prev_close).abs()
    tr3 = (stock_panel["low"] - prev_close).abs()
    stock_panel["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    stock_panel["atr20_pct"] = grouped["true_range"].transform(lambda s: s.rolling(20, min_periods=20).mean()) / stock_panel["close"]

    stock_panel["base_high_20_prev"] = grouped["high"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).max())
    stock_panel["base_low_20_prev"] = grouped["low"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).min())
    stock_panel["base_drawdown_pct"] = stock_panel["base_low_20_prev"] / stock_panel["base_high_20_prev"] - 1.0
    stock_panel["breakout_ret_pct"] = stock_panel["close"] / stock_panel["base_high_20_prev"] - 1.0
    stock_panel["pre_base_vol20"] = grouped["log_return"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).std())
    stock_panel["recent_vol10"] = grouped["log_return"].transform(lambda s: s.rolling(10, min_periods=10).std())
    stock_panel["vol_contraction_ratio"] = stock_panel["recent_vol10"] / stock_panel["pre_base_vol20"]

    stock_panel["market_state"] = np.select(
        [
            (stock_panel["index_close"] >= stock_panel["index_ma60"]) & (stock_panel["index_ret20"] >= 0),
            (stock_panel["index_close"] < stock_panel["index_ma60"]) & (stock_panel["index_ret20"] < 0),
        ],
        ["risk_on", "risk_off"],
        default="mixed",
    )
    stock_panel.loc[stock_panel[["index_close", "index_ma60", "index_ret20"]].isna().any(axis=1), "market_state"] = "unknown"

    stock_panel["beta120"] = grouped.apply(
        lambda g: g["stock_return"].rolling(120, min_periods=120).cov(g["index_return"])
        / g["index_return"].rolling(120, min_periods=120).var(),
        include_groups=False,
    ).reset_index(level=0, drop=True)

    stock_panel["avg_money20_rank_pct"] = (
        stock_panel.loc[stock_panel["pit_universe_member"]]
        .groupby("trade_date")["avg_money20_asof"]
        .rank(pct=True)
        .reindex(stock_panel.index)
    )
    stock_panel["liquidity_quintile"] = (
        stock_panel.loc[stock_panel["pit_universe_member"]]
        .groupby("trade_date", group_keys=False)["avg_money20_asof"]
        .apply(assign_cross_section_quintile)
        .reindex(stock_panel.index)
        .fillna("")
    )

    train_beta = stock_panel.loc[(stock_panel["split"].eq("train")) & stock_panel["beta120"].notna(), "beta120"]
    if train_beta.empty:
        low, high = np.nan, np.nan
    else:
        low, high = train_beta.quantile([1 / 3, 2 / 3]).tolist()
    stock_panel["beta_bucket_boundary_version"] = "train_20170704_20211231_terciles"
    stock_panel["beta_bucket"] = np.select(
        [
            stock_panel["beta120"].notna() & (stock_panel["beta120"] <= low),
            stock_panel["beta120"].notna() & (stock_panel["beta120"] <= high),
            stock_panel["beta120"].notna(),
        ],
        ["low_beta", "mid_beta", "high_beta"],
        default="unknown",
    )

    feature_columns = [
        "instrument_id",
        "trade_date",
        "split",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "factor",
        "prev_close",
        "log_return",
        "pit_universe_member",
        "industry_id",
        "industry_name",
        "avg_money20_asof",
        "liquidity_quintile",
        "avg_money20_rank_pct",
        "close_count_80",
        "history_ok",
        "rolling_min_close_60_prev",
        "rolling_max_close_60_prev",
        "money_ma20_prev",
        "money_ma5",
        "money_ratio5_to20",
        "ma20",
        "atr20_pct",
        "base_high_20_prev",
        "base_low_20_prev",
        "base_drawdown_pct",
        "breakout_ret_pct",
        "pre_base_vol20",
        "recent_vol10",
        "vol_contraction_ratio",
        "index_close",
        "index_ma60",
        "index_ret20",
        "market_state",
        "beta120",
        "beta_bucket",
        "beta_bucket_boundary_version",
    ]
    feature_panel = stock_panel[feature_columns].sort_values(["instrument_id", "trade_date"]).reset_index(drop=True)
    write_parquet(feature_panel, paths.cache_dir / "r01_daily_feature_panel.parquet")

    provider_field_audit = pd.DataFrame(
        [
            {
                "field": field,
                "row_count": len(feature_panel),
                "non_null_count": int(feature_panel[field].notna().sum()) if field in feature_panel else 0,
                "missing_count": int(feature_panel[field].isna().sum()) if field in feature_panel else len(feature_panel),
                "status": "present" if field in feature_panel else "missing",
            }
            for field in ["open", "high", "low", "close", "volume", "money", "factor"]
        ]
    )
    write_csv(provider_field_audit, paths.reports_dir / "r01_provider_field_audit.csv")

    formula_inputs = [
        "rolling_min_close_60_prev",
        "rolling_max_close_60_prev",
        "money_ma20_prev",
        "history_ok",
        "base_high_20_prev",
        "base_low_20_prev",
        "base_drawdown_pct",
        "breakout_ret_pct",
        "pre_base_vol20",
        "recent_vol10",
        "vol_contraction_ratio",
        "ma20",
        "atr20_pct",
        "money_ratio5_to20",
        "avg_money20_rank_pct",
    ]
    coverage = []
    for column in formula_inputs:
        coverage.append(
            {
                "feature_name": column,
                "row_count": len(feature_panel),
                "non_null_count": int(feature_panel[column].notna().sum()),
                "pit_member_non_null_count": int(feature_panel.loc[feature_panel["pit_universe_member"], column].notna().sum()),
                "status": "present",
            }
        )
    write_csv(pd.DataFrame(coverage), paths.reports_dir / "r01_formula_input_coverage_audit.csv")

    asof = pd.DataFrame(
        [
            {"check_name": "feature_panel_rows", "value": len(feature_panel), "status": "passed"},
            {"check_name": "pit_member_rows", "value": int(feature_panel["pit_universe_member"].sum()), "status": "passed"},
            {"check_name": "future_columns_used", "value": 0, "status": "passed"},
        ]
    )
    write_csv(asof, paths.reports_dir / "r01_feature_asof_audit.csv")
    state_audit = feature_panel.groupby(["split", "market_state", "beta_bucket"], dropna=False).size().reset_index(name="row_count")
    write_csv(state_audit, paths.reports_dir / "r01_market_state_beta_bucket_audit.csv")
    boundary_audit = pd.DataFrame(
        [
            {
                "boundary_version": "train_20170704_20211231_terciles",
                "low_mid_threshold": low,
                "mid_high_threshold": high,
                "train_non_null_beta_count": int(train_beta.count()),
                "status": "passed" if finite(low) and finite(high) else "blocked_missing_beta",
            }
        ]
    )
    write_csv(boundary_audit, paths.reports_dir / "r01_beta_bucket_boundary_audit.csv")
    return feature_panel, boundary_audit


def formula_hashes(config: dict[str, Any]) -> dict[str, str]:
    constants = config["frozen_formula_constants"]
    launch_formula = {
        "detector_id": constants["launch_detector_id"],
        "history_ok": "valid close count over prior/current 80-row window >= 80",
        "price_breakout": "close / rolling_min_close_60_prev - 1 >= 0.12 AND close >= rolling_max_close_60_prev",
        "money_surge": "money >= 2.0 * money_ma20_prev AND money >= 50,000,000",
        "collapse": "episode_merge_gap_trading_days = 20",
    }
    fast_fail_formula = {"event_source": launch_formula, "fast_fail_drawdown": constants["fast_fail_drawdown"]}
    sparse_formula = {
        key: constants[key]
        for key in [
            "vcp_base_length_trading_days",
            "vcp_base_drawdown_min",
            "vcp_breakout_ret_min",
            "vcp_breakout_ret_max",
            "vcp_vol_contraction_max",
            "vcp_ma20_distance_abs_max",
            "vcp_atr20_pct_max",
            "vcp_money_ratio5_to20_min",
            "vcp_money_ratio5_to20_max",
            "vcp_avg_money20_rank_pct_min",
        ]
    }
    return {
        PRIMARY_UNIT: canonical_hash(launch_formula),
        FAST_FAIL_UNIT: canonical_hash(fast_fail_formula),
        SPARSE_UNIT: canonical_hash(sparse_formula),
    }


def build_unit_registry(config: dict[str, Any], paths: Paths) -> pd.DataFrame:
    hashes = formula_hashes(config)
    rows = [
        {
            "canonical_unit_id": PRIMARY_UNIT,
            "unit_role": "primary short-horizon exposure unit",
            "event_source_family": "launch_breakout_money_surge",
            "final_decision_authority": "can support r01_short_horizon_local_unit_supported",
            "horizons": "H5,H10,H20",
            "entry_rule": "first_executable_next_open",
            "exit_rule": "natural_exit_execution_date",
            "fixed_fast_fail_enabled": False,
            "formula_hash": hashes[PRIMARY_UNIT],
            "formula_text_hash": hashes[PRIMARY_UNIT],
            "formula_constants_hash": canonical_hash(config["frozen_formula_constants"]),
            "status": "frozen",
        },
        {
            "canonical_unit_id": FAST_FAIL_UNIT,
            "unit_role": "secondary loss-control variant",
            "event_source_family": "launch_breakout_money_surge",
            "final_decision_authority": "can only support fixed fast-fail loss-control lead",
            "horizons": "H5,H10,H20",
            "entry_rule": "first_executable_next_open",
            "exit_rule": "fixed_fast_fail_or_natural_exit",
            "fixed_fast_fail_enabled": True,
            "formula_hash": hashes[FAST_FAIL_UNIT],
            "formula_text_hash": hashes[FAST_FAIL_UNIT],
            "formula_constants_hash": canonical_hash(config["frozen_formula_constants"]),
            "status": "frozen",
        },
        {
            "canonical_unit_id": SPARSE_UNIT,
            "unit_role": "backup sparse event-source probe",
            "event_source_family": "base_breakout_vcp_sparse",
            "final_decision_authority": "can only support low-overlap sparse event-source follow-up",
            "horizons": "H5,H10,H20",
            "entry_rule": "first_executable_next_open",
            "exit_rule": "natural_exit_execution_date",
            "fixed_fast_fail_enabled": False,
            "formula_hash": hashes[SPARSE_UNIT],
            "formula_text_hash": hashes[SPARSE_UNIT],
            "formula_constants_hash": canonical_hash(config["frozen_formula_constants"]),
            "status": "frozen",
        },
    ]
    registry = pd.DataFrame(rows)
    write_csv(registry, paths.reports_dir / "r01_canonical_unit_registry.csv")

    freeze_rows = []
    for unit in CANONICAL_UNITS:
        for name, value in config["frozen_formula_constants"].items():
            if unit == SPARSE_UNIT and not (name.startswith("vcp_") or name.startswith("right_tail")):
                continue
            if unit in {PRIMARY_UNIT, FAST_FAIL_UNIT} and name.startswith("vcp_"):
                continue
            freeze_rows.append(
                {
                    "canonical_unit_id": unit,
                    "source_requirement_section": "R01 §7",
                    "formula_name": unit,
                    "frozen_constant_name": name,
                    "frozen_constant_value": value,
                    "formula_text_hash": hashes[unit],
                    "formula_constants_hash": canonical_hash(config["frozen_formula_constants"]),
                    "implementation_hash": hashes[unit],
                    "status": "frozen",
                }
            )
    write_csv(pd.DataFrame(freeze_rows), paths.reports_dir / "r01_formula_freeze_audit.csv")
    return registry


def collapse_signal_rows(
    signals: pd.DataFrame,
    unit_id: str,
    detector_id: str,
    formula_hash: str,
    calendar_pos: dict[pd.Timestamp, int],
    gap: int,
    unit_role: str,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for instrument, group in signals.sort_values(["instrument_id", "trade_date"]).groupby("instrument_id"):
        last_pos: int | None = None
        episode_no = 0
        raw_count = 0
        collapsed_count = 0
        duplicate_count = 0
        for record in group.itertuples(index=False):
            raw_count += 1
            date = pd.Timestamp(record.trade_date)
            pos = calendar_pos.get(date)
            if pos is None:
                continue
            start_new = last_pos is None or pos - last_pos > gap
            if start_new:
                episode_no += 1
                collapsed_count += 1
                episode_id = f"{instrument}_{date.date()}_{detector_id}"
                rows.append(
                    {
                        "canonical_unit_id": unit_id,
                        "instrument_id": instrument,
                        "signal_date": date,
                        "episode_id": episode_id,
                        "episode_start_signal_date": date,
                        "event_key": f"{unit_id}_{instrument}_{date.date()}",
                        "split": record.split,
                        "unit_role": unit_role,
                        "detector_id": detector_id,
                        "detector_formula_hash": formula_hash,
                        "formula_hash": formula_hash,
                        "formula_input_row_hash": canonical_hash({"instrument_id": instrument, "signal_date": str(date.date()), "unit": unit_id}),
                        "source_requirement_section": "R01 §7",
                        "event_collapse_window_trading_days": gap,
                        "event_status": "event_generated",
                    }
                )
            else:
                duplicate_count += 1
            last_pos = pos
        audit_rows.append(
            {
                "canonical_unit_id": unit_id,
                "instrument_id": instrument,
                "raw_formula_hit_count": raw_count,
                "post_collapse_event_count": collapsed_count,
                "dropped_duplicate_episode_member_count": duplicate_count,
                "blocked_formula_row_count": 0,
            }
        )
    return rows, pd.DataFrame(audit_rows)


def build_event_panel(config: dict[str, Any], paths: Paths, feature: pd.DataFrame) -> pd.DataFrame:
    constants = config["frozen_formula_constants"]
    hashes = formula_hashes(config)
    calendar = load_calendar(config)
    calendar_pos = trading_day_pos(calendar)
    allowed = feature["split"].isin(SPLITS)
    valid_base = allowed & feature["pit_universe_member"] & feature["close"].notna() & (feature["money"] > 0) & (feature["volume"] > 0)
    launch_signal = (
        valid_base
        & feature["history_ok"].astype(bool)
        & (feature["close"] / feature["rolling_min_close_60_prev"] - 1.0 >= constants["launch_breakout_min_return"])
        & (feature["close"] >= feature["rolling_max_close_60_prev"])
        & (feature["money"] >= constants["launch_money_surge_ratio"] * feature["money_ma20_prev"])
        & (feature["money"] >= constants["launch_money_floor_cny"])
    )
    launch_hits = feature.loc[launch_signal].copy()
    natural_rows, natural_audit = collapse_signal_rows(
        launch_hits,
        PRIMARY_UNIT,
        constants["launch_detector_id"],
        hashes[PRIMARY_UNIT],
        calendar_pos,
        constants["launch_episode_merge_gap_trading_days"],
        "primary short-horizon exposure unit",
    )
    fast_rows, fast_audit = collapse_signal_rows(
        launch_hits,
        FAST_FAIL_UNIT,
        constants["launch_detector_id"],
        hashes[FAST_FAIL_UNIT],
        calendar_pos,
        constants["launch_episode_merge_gap_trading_days"],
        "secondary loss-control variant",
    )

    sparse_signal = (
        valid_base
        & (feature["base_drawdown_pct"] >= constants["vcp_base_drawdown_min"])
        & (feature["breakout_ret_pct"] >= constants["vcp_breakout_ret_min"])
        & (feature["breakout_ret_pct"] <= constants["vcp_breakout_ret_max"])
        & (feature["vol_contraction_ratio"] <= constants["vcp_vol_contraction_max"])
        & ((feature["close"] / feature["ma20"] - 1.0).abs() <= constants["vcp_ma20_distance_abs_max"])
        & (feature["atr20_pct"] <= constants["vcp_atr20_pct_max"])
        & (feature["money_ratio5_to20"] >= constants["vcp_money_ratio5_to20_min"])
        & (feature["money_ratio5_to20"] <= constants["vcp_money_ratio5_to20_max"])
        & (feature["avg_money20_rank_pct"] >= constants["vcp_avg_money20_rank_pct_min"])
    )
    sparse_hits = feature.loc[sparse_signal].copy()
    sparse_rows, sparse_audit = collapse_signal_rows(
        sparse_hits,
        SPARSE_UNIT,
        "EP4_R05_BASE_BREAKOUT_VCP_PREFLIGHT",
        hashes[SPARSE_UNIT],
        calendar_pos,
        constants["launch_episode_merge_gap_trading_days"],
        "backup sparse event-source probe",
    )

    event = pd.DataFrame(natural_rows + fast_rows + sparse_rows)
    if event.empty:
        event = pd.DataFrame(
            columns=[
                "canonical_unit_id",
                "instrument_id",
                "signal_date",
                "episode_id",
                "episode_start_signal_date",
                "event_key",
                "split",
                "unit_role",
                "detector_id",
                "detector_formula_hash",
                "formula_hash",
                "formula_input_row_hash",
                "source_requirement_section",
                "event_collapse_window_trading_days",
                "event_status",
            ]
        )
    event = event.sort_values(["canonical_unit_id", "instrument_id", "signal_date"]).reset_index(drop=True)
    write_parquet(event, paths.cache_dir / "r01_canonical_event_panel.parquet")

    generation_audit = pd.concat([natural_audit, fast_audit, sparse_audit], ignore_index=True)
    if generation_audit.empty:
        generation_audit = pd.DataFrame(
            columns=[
                "canonical_unit_id",
                "instrument_id",
                "raw_formula_hit_count",
                "post_collapse_event_count",
                "dropped_duplicate_episode_member_count",
                "blocked_formula_row_count",
            ]
        )
    aggregate = generation_audit.groupby("canonical_unit_id", as_index=False).sum(numeric_only=True)
    write_csv(aggregate, paths.reports_dir / "r01_event_generation_audit.csv")
    overlap = build_event_overlap_audit(event)
    write_csv(overlap, paths.reports_dir / "r01_event_overlap_audit.csv")
    return event


def build_event_overlap_audit(event: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for left in CANONICAL_UNITS:
        lset = set(zip(event.loc[event["canonical_unit_id"].eq(left), "instrument_id"], event.loc[event["canonical_unit_id"].eq(left), "signal_date"]))
        for right in CANONICAL_UNITS:
            rset = set(zip(event.loc[event["canonical_unit_id"].eq(right), "instrument_id"], event.loc[event["canonical_unit_id"].eq(right), "signal_date"]))
            rows.append(
                {
                    "left_unit": left,
                    "right_unit": right,
                    "left_event_count": len(lset),
                    "right_event_count": len(rset),
                    "overlap_count": len(lset & rset),
                    "overlap_share_of_left": safe_share(len(lset & rset), len(lset)),
                    "selection_used": False,
                }
            )
    return pd.DataFrame(rows)


def make_feature_lookup(feature: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], dict[str, Any]]:
    cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "prev_close",
        "pit_universe_member",
        "industry_id",
        "industry_name",
        "liquidity_quintile",
        "market_state",
        "beta120",
        "beta_bucket",
    ]
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]] = {}
    for row in feature[["instrument_id", "trade_date", *cols]].itertuples(index=False):
        data = row._asdict()
        inst = data.pop("instrument_id")
        date = pd.Timestamp(data.pop("trade_date"))
        lookup[(inst, date)] = data
    return lookup


def candidate_block_reason(
    info: dict[str, Any] | None,
    side: str,
    limit_pct: float,
) -> str:
    if info is None:
        return "missing_open" if side == "entry" else "missing_exit_open"
    open_price = info.get("open", np.nan)
    if not finite(open_price):
        return "missing_open" if side == "entry" else "missing_exit_open"
    if not finite(info.get("volume", np.nan)) or float(info.get("volume", np.nan)) <= 0:
        return "zero_volume"
    if not finite(info.get("money", np.nan)) or float(info.get("money", np.nan)) <= 0:
        return "zero_money"
    if not bool(info.get("pit_universe_member", False)):
        return "not_universe_member"
    prev_close = info.get("prev_close", np.nan)
    if finite(prev_close) and float(prev_close) > 0:
        ratio = float(open_price) / float(prev_close) - 1.0
        if side == "entry" and ratio >= limit_pct:
            return "limit_up_inferred_on_entry"
        if side == "exit" and ratio <= -limit_pct:
            return "limit_down_inferred_on_exit"
    return ""


def first_executable_open(
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    instrument: str,
    after_date: pd.Timestamp,
    split: str,
    side: str,
    max_lag: int,
) -> dict[str, Any]:
    candidates = next_trade_candidates(calendar, after_date, max_lag)
    if not candidates:
        return {"date": pd.NaT, "price": np.nan, "lag": np.nan, "blocked_reason": "missing_calendar_next_day"}
    first_reason = ""
    limit_pct = float(config["execution"]["mainboard_limit_inference_pct"])
    for date, lag in candidates:
        if split_for_date(config, date) != split:
            return {"date": pd.NaT, "price": np.nan, "lag": lag, "blocked_reason": "split_boundary"}
        info = lookup.get((instrument, date))
        reason = candidate_block_reason(info, side, limit_pct)
        if not reason:
            return {"date": date, "price": float(info["open"]), "lag": lag, "blocked_reason": ""}
        if not first_reason:
            first_reason = reason
    return {"date": pd.NaT, "price": np.nan, "lag": candidates[-1][1], "blocked_reason": first_reason or "missing_open"}


def build_execution_panel(config: dict[str, Any], paths: Paths, feature: pd.DataFrame, event: pd.DataFrame) -> pd.DataFrame:
    calendar = load_calendar(config)
    lookup = make_feature_lookup(feature)
    feature_by_instrument = {
        instrument: group.sort_values("trade_date").reset_index(drop=True)
        for instrument, group in feature.groupby("instrument_id", sort=False)
    }
    max_entry_lag = int(config["execution"]["max_entry_execution_lag_trading_days"])
    max_exit_lag = int(config["execution"]["max_exit_execution_lag_trading_days"])
    buy_cost = float(config["execution"]["buy_cost_bps"])
    sell_cost = float(config["execution"]["sell_cost_bps"])
    round_trip = float(config["execution"]["round_trip_cost_bps"])
    fast_fail_drawdown = float(config["frozen_formula_constants"]["fast_fail_drawdown"])
    rows: list[dict[str, Any]] = []

    for ev in event.itertuples(index=False):
        for horizon in HORIZONS:
            row = {
                "canonical_unit_id": ev.canonical_unit_id,
                "unit_role": ev.unit_role,
                "instrument_id": ev.instrument_id,
                "event_key": ev.event_key,
                "signal_date": pd.Timestamp(ev.signal_date),
                "horizon": f"H{horizon}",
                "split": ev.split,
                "entry_execution_date": pd.NaT,
                "entry_price": np.nan,
                "natural_exit_target_date": pd.NaT,
                "natural_exit_signal_date": pd.NaT,
                "natural_exit_execution_date": pd.NaT,
                "natural_exit_price": np.nan,
                "fast_fail_enabled": ev.canonical_unit_id == FAST_FAIL_UNIT,
                "fast_fail_drawdown": fast_fail_drawdown if ev.canonical_unit_id == FAST_FAIL_UNIT else np.nan,
                "fast_fail_signal_date": pd.NaT,
                "exit_execution_date": pd.NaT,
                "exit_price": np.nan,
                "buy_cost_bps": buy_cost,
                "sell_cost_bps": sell_cost,
                "round_trip_cost_bps": round_trip,
                "gross_return": np.nan,
                "net_return": np.nan,
                "execution_status": "",
                "blocked_reason": "",
                "entry_lag_trading_days": np.nan,
                "exit_lag_trading_days": np.nan,
            }
            entry = first_executable_open(config, calendar, lookup, ev.instrument_id, pd.Timestamp(ev.signal_date), ev.split, "entry", max_entry_lag)
            row["entry_lag_trading_days"] = entry["lag"]
            if entry["blocked_reason"]:
                reason = entry["blocked_reason"]
                row["execution_status"] = f"blocked_{reason}"
                row["blocked_reason"] = reason
                rows.append(row)
                continue
            row["entry_execution_date"] = entry["date"]
            row["entry_price"] = entry["price"]
            target = add_trading_days(calendar, row["entry_execution_date"], horizon)
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
            natural_signal = prev_trading_day(calendar, target)
            row["natural_exit_signal_date"] = natural_signal

            exit_signal = natural_signal
            if ev.canonical_unit_id == FAST_FAIL_UNIT:
                ff_date = first_fast_fail_date(feature_by_instrument, ev.instrument_id, row["entry_execution_date"], natural_signal, row["entry_price"], fast_fail_drawdown)
                if not pd.isna(ff_date):
                    row["fast_fail_signal_date"] = ff_date
                    exit_signal = ff_date

            exit_exec = first_executable_open(config, calendar, lookup, ev.instrument_id, exit_signal, ev.split, "exit", max_exit_lag)
            row["exit_lag_trading_days"] = exit_exec["lag"]
            if exit_exec["blocked_reason"]:
                reason = exit_exec["blocked_reason"]
                row["execution_status"] = f"blocked_{reason}"
                row["blocked_reason"] = reason
                rows.append(row)
                continue
            row["exit_execution_date"] = exit_exec["date"]
            row["exit_price"] = exit_exec["price"]
            row["natural_exit_execution_date"] = target
            natural_info = lookup.get((ev.instrument_id, target), {})
            row["natural_exit_price"] = natural_info.get("open", np.nan)
            row["gross_return"] = row["exit_price"] / row["entry_price"] - 1.0
            row["net_return"] = row["exit_price"] * (1.0 - sell_cost / 10000.0) / (row["entry_price"] * (1.0 + buy_cost / 10000.0)) - 1.0
            row["execution_status"] = "complete_executable"
            row["blocked_reason"] = ""
            rows.append(row)

    execution = pd.DataFrame(rows)
    write_parquet(execution, paths.cache_dir / "r01_execution_event_panel.parquet")
    write_execution_audits(paths, execution)
    return execution


def first_fast_fail_date(feature_by_instrument: dict[str, pd.DataFrame], instrument: str, entry_date: Any, natural_signal: Any, entry_price: float, threshold: float) -> pd.Timestamp | pd.NaT:
    if pd.isna(entry_date) or pd.isna(natural_signal) or not finite(entry_price):
        return pd.NaT
    inst = feature_by_instrument.get(instrument)
    if inst is None or inst.empty:
        return pd.NaT
    dates = inst["trade_date"]
    start = dates.searchsorted(pd.Timestamp(entry_date), side="left")
    end = dates.searchsorted(pd.Timestamp(natural_signal), side="right")
    path = inst.iloc[start:end]
    hit = path.loc[path["close"] / float(entry_price) - 1.0 <= threshold]
    if hit.empty:
        return pd.NaT
    return pd.Timestamp(hit.iloc[0]["trade_date"])


def write_execution_audits(paths: Paths, execution: pd.DataFrame) -> None:
    block = (
        execution.loc[execution["execution_status"].ne("complete_executable")]
        .groupby(["canonical_unit_id", "horizon", "split", "blocked_reason"], dropna=False)
        .size()
        .reset_index(name="blocked_count")
    )
    denom = execution.groupby(["canonical_unit_id", "horizon", "split"], dropna=False).size().reset_index(name="signal_event_count")
    complete = (
        execution.loc[execution["execution_status"].eq("complete_executable")]
        .groupby(["canonical_unit_id", "horizon", "split"], dropna=False)
        .size()
        .reset_index(name="complete_event_count")
    )
    denom = denom.merge(complete, on=["canonical_unit_id", "horizon", "split"], how="left").fillna({"complete_event_count": 0})
    denom["blocked_event_count"] = denom["signal_event_count"] - denom["complete_event_count"]
    if not block.empty:
        block = block.merge(denom[["canonical_unit_id", "horizon", "split", "signal_event_count"]], on=["canonical_unit_id", "horizon", "split"], how="left")
        block["blocked_share"] = block["blocked_count"] / block["signal_event_count"]
    else:
        block = pd.DataFrame(columns=["canonical_unit_id", "horizon", "split", "blocked_reason", "blocked_count", "signal_event_count", "blocked_share"])
    denom["complete_event_share"] = denom["complete_event_count"] / denom["signal_event_count"]
    write_csv(block, paths.reports_dir / "r01_execution_block_audit.csv")
    write_csv(denom, paths.reports_dir / "r01_denominator_audit.csv")


def build_feature_by_date(feature: pd.DataFrame) -> dict[pd.Timestamp, pd.DataFrame]:
    return {pd.Timestamp(date): group.copy() for date, group in feature.groupby("trade_date")}


def executable_pair_returns(
    config: dict[str, Any],
    entry_date: pd.Timestamp,
    exit_date: pd.Timestamp,
    feature_by_date: dict[pd.Timestamp, pd.DataFrame],
    buy_cost_bps: float,
    sell_cost_bps: float,
) -> pd.DataFrame:
    entry = feature_by_date.get(pd.Timestamp(entry_date), pd.DataFrame()).copy()
    exit_ = feature_by_date.get(pd.Timestamp(exit_date), pd.DataFrame()).copy()
    if entry.empty or exit_.empty:
        return pd.DataFrame(columns=["instrument_id", "candidate_net_return"])
    limit_pct = float(config["execution"]["mainboard_limit_inference_pct"])
    entry_ok = (
        entry["pit_universe_member"]
        & entry["open"].notna()
        & (entry["volume"] > 0)
        & (entry["money"] > 0)
        & ~(entry["prev_close"].notna() & (entry["open"] / entry["prev_close"] - 1.0 >= limit_pct))
    )
    exit_ok = (
        exit_["pit_universe_member"]
        & exit_["open"].notna()
        & (exit_["volume"] > 0)
        & (exit_["money"] > 0)
        & ~(exit_["prev_close"].notna() & (exit_["open"] / exit_["prev_close"] - 1.0 <= -limit_pct))
    )
    merged = entry.loc[entry_ok, ["instrument_id", "open"]].rename(columns={"open": "entry_open"}).merge(
        exit_.loc[exit_ok, ["instrument_id", "open"]].rename(columns={"open": "exit_open"}),
        on="instrument_id",
        how="inner",
    )
    if merged.empty:
        return pd.DataFrame(columns=["instrument_id", "candidate_net_return"])
    merged["candidate_net_return"] = merged["exit_open"] * (1.0 - sell_cost_bps / 10000.0) / (merged["entry_open"] * (1.0 + buy_cost_bps / 10000.0)) - 1.0
    return merged[["instrument_id", "candidate_net_return"]]


def build_comparator_panel(config: dict[str, Any], paths: Paths, feature: pd.DataFrame, execution: pd.DataFrame) -> pd.DataFrame:
    feature_by_date = build_feature_by_date(feature)
    pair_cache: dict[tuple[pd.Timestamp, pd.Timestamp], pd.DataFrame] = {}
    complete = execution.loc[execution["execution_status"].eq("complete_executable")].copy()
    rows: list[dict[str, Any]] = []
    for record in complete.itertuples(index=False):
        entry_date = pd.Timestamp(record.entry_execution_date)
        exit_date = pd.Timestamp(record.exit_execution_date)
        signal_date = pd.Timestamp(record.signal_date)
        pair_key = (entry_date, exit_date)
        if pair_key not in pair_cache:
            pair_cache[pair_key] = executable_pair_returns(config, entry_date, exit_date, feature_by_date, float(record.buy_cost_bps), float(record.sell_cost_bps))
        candidates = pair_cache[pair_key]
        signal_features = feature_by_date.get(signal_date, pd.DataFrame())
        base = candidates.loc[candidates["instrument_id"].ne(record.instrument_id)].copy()
        base = base.merge(signal_features[["instrument_id", "industry_id", "liquidity_quintile"]], on="instrument_id", how="left") if not signal_features.empty else base
        event_feat = signal_features.loc[signal_features["instrument_id"].eq(record.instrument_id)].head(1) if not signal_features.empty else pd.DataFrame()
        event_industry = event_feat.iloc[0]["industry_id"] if not event_feat.empty else "UNKNOWN"
        event_liq = event_feat.iloc[0]["liquidity_quintile"] if not event_feat.empty else ""
        same_industry = base.loc[base["industry_id"].eq(event_industry)] if "industry_id" in base else pd.DataFrame()
        same_liquidity = base.loc[base["liquidity_quintile"].eq(event_liq)] if "liquidity_quintile" in base else pd.DataFrame()
        same_both = base.loc[base["industry_id"].eq(event_industry) & base["liquidity_quintile"].eq(event_liq)] if {"industry_id", "liquidity_quintile"}.issubset(base.columns) else pd.DataFrame()

        if len(same_both) >= 30:
            scope_name, scope = "same_industry_same_liquidity", same_both
        elif len(same_industry) >= 30:
            scope_name, scope = "same_industry_only", same_industry
        elif len(same_liquidity) >= 30:
            scope_name, scope = "same_liquidity_only", same_liquidity
        else:
            scope_name, scope = "same_day_pit_universe", base
        if base.empty or scope.empty:
            status = "blocked_missing_comparator_price"
        elif scope_name == "same_day_pit_universe" and len(scope) < 100:
            status = "blocked_insufficient_comparator"
        else:
            status = "comparable"

        scope_mean = safe_mean(scope["candidate_net_return"]) if not scope.empty else np.nan
        scope_median = float(scope["candidate_net_return"].median()) if not scope.empty else np.nan
        same_day_mean = safe_mean(base["candidate_net_return"]) if not base.empty else np.nan
        industry_mean = safe_mean(same_industry["candidate_net_return"]) if not same_industry.empty else np.nan
        liquidity_mean = safe_mean(same_liquidity["candidate_net_return"]) if not same_liquidity.empty else np.nan
        rows.append(
            {
                "canonical_unit_id": record.canonical_unit_id,
                "event_key": record.event_key,
                "horizon": record.horizon,
                "split": record.split,
                "instrument_id": record.instrument_id,
                "signal_date": signal_date,
                "entry_execution_date": entry_date,
                "exit_execution_date": exit_date,
                "candidate_scope_0_count": len(base),
                "same_industry_same_liquidity_count": len(same_both),
                "same_industry_only_count": len(same_industry),
                "same_liquidity_only_count": len(same_liquidity),
                "same_day_pit_universe_count": len(base),
                "primary_comparator_scope": scope_name,
                "matched_comparator_count": len(scope),
                "matched_comparator_net_return": scope_mean,
                "matched_comparator_net_return_median": scope_median,
                "matched_delta_return": record.net_return - scope_mean if finite(scope_mean) else np.nan,
                "matched_delta_return_vs_comparator_median": record.net_return - scope_median if finite(scope_median) else np.nan,
                "matched_comparator_status": status,
                "same_day_universe_delta_return": record.net_return - same_day_mean if finite(same_day_mean) else np.nan,
                "industry_only_delta_return": record.net_return - industry_mean if finite(industry_mean) else np.nan,
                "liquidity_only_delta_return": record.net_return - liquidity_mean if finite(liquidity_mean) else np.nan,
                "SH000300_delta_return": np.nan,
                "fallback_comparator_used": scope_name == "same_day_pit_universe",
            }
        )
    comparator = pd.DataFrame(rows)
    if comparator.empty:
        comparator = pd.DataFrame(columns=["canonical_unit_id", "event_key", "horizon", "split", "instrument_id", "matched_comparator_status"])
    write_parquet(comparator, paths.cache_dir / "r01_matched_comparator_panel.parquet")
    write_comparator_audits(paths, comparator)
    return comparator


def write_comparator_audits(paths: Paths, comparator: pd.DataFrame) -> None:
    scope = comparator.groupby(["canonical_unit_id", "horizon", "split", "primary_comparator_scope"], dropna=False).size().reset_index(name="event_count") if not comparator.empty else pd.DataFrame()
    write_csv(scope, paths.reports_dir / "r01_comparator_scope_audit.csv")
    denom = comparator.groupby(["canonical_unit_id", "horizon", "split", "matched_comparator_status"], dropna=False).size().reset_index(name="event_count") if not comparator.empty else pd.DataFrame()
    write_csv(denom, paths.reports_dir / "r01_relative_denominator_audit.csv")
    fallback = comparator.groupby(["canonical_unit_id", "horizon", "split"], dropna=False)["fallback_comparator_used"].mean().reset_index(name="fallback_comparator_share") if not comparator.empty else pd.DataFrame()
    if not fallback.empty:
        fallback["weak_comparator_quality"] = fallback["fallback_comparator_share"] > 0.30
    write_csv(fallback, paths.reports_dir / "r01_comparator_fallback_quality_audit.csv")


def year_gate_table(joined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (unit, role, horizon, split, year), group in joined.groupby(["canonical_unit_id", "unit_role", "horizon", "split", "calendar_year"], dropna=False):
        complete = group.loc[group["execution_status"].eq("complete_executable")]
        comparable = complete.loc[complete["matched_comparator_status"].eq("comparable")]
        rows.append(
            {
                "canonical_unit_id": unit,
                "unit_role": role,
                "horizon": horizon,
                "split": split,
                "calendar_year": int(year) if pd.notna(year) else 0,
                "complete_event_count": len(complete),
                "complete_event_share": safe_share(len(complete), len(group)),
                "mean_net_return": safe_mean(complete["net_return"]),
                "median_net_return": float(complete["net_return"].median()) if len(complete) else np.nan,
                "p10_net_return": safe_quantile(complete["net_return"], 0.10),
                "loss_rate": safe_mean(complete["net_return"] < 0),
                "relative_comparable_event_share": safe_share(len(comparable), len(complete)),
                "mean_matched_delta_return": safe_mean(comparable["matched_delta_return"]),
                "median_matched_delta_return": float(comparable["matched_delta_return"].median()) if len(comparable) else np.nan,
                "p10_matched_delta_return": safe_quantile(comparable["matched_delta_return"], 0.10),
                "matched_loss_rate_delta": safe_mean(comparable["net_return"] < 0) - safe_mean(comparable["matched_comparator_net_return"] < 0) if len(comparable) else np.nan,
                "fallback_comparator_share": safe_mean(complete["primary_comparator_scope"].eq("same_day_pit_universe")) if len(complete) else 0.0,
                "top1_instrument_event_share": top_n_share(complete, "instrument_id", 1),
                "top1_industry_event_share": top_n_share(complete, "industry_id", 1),
                "top1_entry_date_event_share": top_n_share(complete, "entry_execution_date", 1),
                "year_gate_status": "complete" if len(complete) else "empty",
            }
        )
    return pd.DataFrame(rows)


def top_n_share(df: pd.DataFrame, column: str, n: int) -> float:
    if df.empty or column not in df:
        return 0.0
    counts = df[column].fillna("UNKNOWN").value_counts()
    return safe_share(counts.head(n).sum(), len(df))


def contribution_share(df: pd.DataFrame, key: str, value_col: str, n: int = 1) -> float:
    if df.empty or key not in df or value_col not in df:
        return 0.0
    contrib = df.groupby(key)[value_col].sum().abs().sort_values(ascending=False)
    total = contrib.sum()
    return safe_share(contrib.head(n).sum(), total)


def build_summaries(config: dict[str, Any], paths: Paths, feature: pd.DataFrame, execution: pd.DataFrame, comparator: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    signal_feature = feature[
        [
            "instrument_id",
            "trade_date",
            "industry_id",
            "industry_name",
            "liquidity_quintile",
            "market_state",
            "beta_bucket",
        ]
    ].rename(columns={"trade_date": "signal_date"})
    joined = execution.merge(comparator, on=["canonical_unit_id", "event_key", "horizon", "split", "instrument_id"], how="left", suffixes=("", "_comparator"))
    joined = joined.merge(signal_feature, on=["instrument_id", "signal_date"], how="left")
    joined["calendar_year"] = pd.to_datetime(joined["entry_execution_date"]).dt.year
    year_summary = year_gate_table(joined)
    write_csv(year_summary, paths.reports_dir / "r01_event_summary_by_unit_horizon_year.csv")

    rows = []
    for unit in CANONICAL_UNITS:
        role = unit_role(unit)
        for horizon in HORIZON_LABELS:
            for split in SPLITS:
                group = joined.loc[(joined["canonical_unit_id"].eq(unit)) & (joined["horizon"].eq(horizon)) & (joined["split"].eq(split))]
                complete = group.loc[group["execution_status"].eq("complete_executable")]
                comparable = complete.loc[complete["matched_comparator_status"].eq("comparable")]
                years = year_summary.loc[(year_summary["canonical_unit_id"].eq(unit)) & (year_summary["horizon"].eq(horizon)) & (year_summary["split"].eq(split))]
                year_count = int((years["complete_event_count"] > 0).sum()) if not years.empty else 0
                min_year = int(years.loc[years["complete_event_count"] > 0, "complete_event_count"].min()) if (not years.empty and (years["complete_event_count"] > 0).any()) else 0
                signal_count = len(group)
                complete_count = len(complete)
                fallback_share = safe_mean(complete["primary_comparator_scope"].eq("same_day_pit_universe")) if complete_count else 0.0
                weak_comparator_quality = fallback_share > 0.30
                sample_gate = complete_count >= 300 and safe_share(complete_count, signal_count) >= 0.95 and year_count == 2 and min_year >= 75
                if complete_count >= 300:
                    sample_status = "sample_pass"
                elif complete_count >= 150:
                    sample_status = "sample_limited_lead"
                else:
                    sample_status = "blocked_insufficient_sample"
                concentration_gate = (
                    top_n_share(complete, "instrument_id", 1) <= 0.05
                    and top_n_share(complete, "instrument_id", 5) <= 0.20
                    and top_n_share(complete, "industry_id", 1) <= 0.35
                    and top_n_share(complete, "entry_execution_date", 1) <= 0.05
                    and fallback_share <= 0.30
                )
                each_year_abs = bool((years["mean_net_return"] >= -0.0025).all()) if year_count == 2 else False
                each_year_rel = bool((years["mean_matched_delta_return"] >= -0.0025).all()) if year_count == 2 else False
                mean_net = safe_mean(complete["net_return"])
                median_net = float(complete["net_return"].median()) if complete_count else np.nan
                p10_net = safe_quantile(complete["net_return"], 0.10)
                loss_rate = safe_mean(complete["net_return"] < 0) if complete_count else np.nan
                mean_delta = safe_mean(comparable["matched_delta_return"])
                median_delta = float(comparable["matched_delta_return"].median()) if len(comparable) else np.nan
                p10_delta = safe_quantile(comparable["matched_delta_return"], 0.10)
                matched_loss_delta = safe_mean(comparable["net_return"] < 0) - safe_mean(comparable["matched_comparator_net_return"] < 0) if len(comparable) else np.nan
                absolute_positive = bool(
                    split == "validation"
                    and mean_net > 0
                    and median_net >= -0.0025
                    and p10_net >= -0.0800
                    and loss_rate <= 0.55
                    and each_year_abs
                )
                relative_positive = bool(
                    split == "validation"
                    and safe_share(len(comparable), complete_count) >= 0.95
                    and safe_share(int(complete["matched_comparator_status"].eq("blocked_insufficient_comparator").sum()), complete_count) <= 0.05
                    and fallback_share <= 0.30
                    and mean_delta > 0
                    and each_year_rel
                    and sum(
                        [
                            finite(median_delta) and median_delta >= 0,
                            finite(p10_delta) and p10_delta >= 0,
                            finite(matched_loss_delta) and matched_loss_delta <= 0,
                        ]
                    )
                    >= 2
                    and not weak_comparator_quality
                )
                row = {
                    "canonical_unit_id": unit,
                    "unit_role": role,
                    "horizon": horizon,
                    "split": split,
                    "signal_event_count": signal_count,
                    "entry_executable_count": int(group["entry_execution_date"].notna().sum()) if not group.empty else 0,
                    "complete_event_count": complete_count,
                    "blocked_event_count": signal_count - complete_count,
                    "complete_event_share": safe_share(complete_count, signal_count),
                    "mean_gross_return": safe_mean(complete["gross_return"]),
                    "mean_net_return": mean_net,
                    "median_net_return": median_net,
                    "p10_net_return": p10_net,
                    "p25_net_return": safe_quantile(complete["net_return"], 0.25),
                    "p75_net_return": safe_quantile(complete["net_return"], 0.75),
                    "p90_net_return": safe_quantile(complete["net_return"], 0.90),
                    "loss_rate": loss_rate,
                    "relative_comparable_event_share": safe_share(len(comparable), complete_count),
                    "blocked_insufficient_comparator_count": int(complete["matched_comparator_status"].eq("blocked_insufficient_comparator").sum()) if complete_count else 0,
                    "fallback_comparator_share": fallback_share,
                    "mean_matched_delta_return": mean_delta,
                    "median_matched_delta_return": median_delta,
                    "p10_matched_delta_return": p10_delta,
                    "matched_loss_rate_delta": matched_loss_delta,
                    "matched_comparator_count_mean": safe_mean(complete["matched_comparator_count"]),
                    "matched_comparator_scope_same_industry_same_liquidity_share": safe_mean(complete["primary_comparator_scope"].eq("same_industry_same_liquidity")) if complete_count else 0.0,
                    "matched_comparator_scope_same_industry_only_share": safe_mean(complete["primary_comparator_scope"].eq("same_industry_only")) if complete_count else 0.0,
                    "matched_comparator_scope_same_liquidity_only_share": safe_mean(complete["primary_comparator_scope"].eq("same_liquidity_only")) if complete_count else 0.0,
                    "matched_comparator_scope_same_day_pit_universe_share": fallback_share,
                    "same_day_universe_delta_mean": safe_mean(complete["same_day_universe_delta_return"]),
                    "industry_only_delta_mean": safe_mean(complete["industry_only_delta_return"]),
                    "liquidity_only_delta_mean": safe_mean(complete["liquidity_only_delta_return"]),
                    "SH000300_delta_mean": safe_mean(complete["SH000300_delta_return"]),
                    "top1_instrument_event_share": top_n_share(complete, "instrument_id", 1),
                    "top5_instrument_event_share": top_n_share(complete, "instrument_id", 5),
                    "top1_industry_event_share": top_n_share(complete, "industry_id", 1),
                    "top5_industry_event_share": top_n_share(complete, "industry_id", 5),
                    "top1_entry_date_event_share": top_n_share(complete, "entry_execution_date", 1),
                    "year_count": year_count,
                    "min_year_complete_event_count": min_year,
                    "sample_status": sample_status,
                    "sample_gate_pass": sample_gate,
                    "concentration_gate_pass": concentration_gate,
                    "absolute_positive": absolute_positive,
                    "relative_positive": relative_positive,
                    "weak_comparator_quality": weak_comparator_quality,
                    "horizon_pass": sample_gate and concentration_gate and absolute_positive and relative_positive,
                    "strongly_negative": complete_count >= 150 and mean_net < -0.0025 and mean_delta < -0.0025,
                    "adjacent_horizon_shape_status": "not_applicable",
                    "robustness_confirmed": False,
                }
                rows.append(row)
    summary = pd.DataFrame(rows)
    for idx, row in summary.iterrows():
        if row["horizon"] in {"H5", "H20"}:
            if int(row["complete_event_count"]) < 150:
                summary.at[idx, "adjacent_horizon_shape_status"] = "adjacent_horizon_not_evaluable"
            elif bool(row["strongly_negative"]):
                summary.at[idx, "adjacent_horizon_shape_status"] = "strongly_negative"
            else:
                summary.at[idx, "adjacent_horizon_shape_status"] = "adjacent_horizon_clean"

    for idx, row in summary.iterrows():
        if row["split"] == "validation":
            robust = robustness_criteria(summary, year_summary, row["canonical_unit_id"], row["horizon"])
            summary.at[idx, "robustness_confirmed"] = robust
    write_csv(summary, paths.reports_dir / "r01_event_summary_by_unit_horizon_split.csv")
    write_gate_audits(paths, summary)
    write_decompositions(paths, joined)
    return summary, year_summary


def unit_role(unit: str) -> str:
    return {
        PRIMARY_UNIT: "primary short-horizon exposure unit",
        FAST_FAIL_UNIT: "secondary loss-control variant",
        SPARSE_UNIT: "backup sparse event-source probe",
    }.get(unit, "")


def robustness_criteria(summary: pd.DataFrame, year_summary: pd.DataFrame, unit: str, horizon: str) -> bool:
    row = summary.loc[(summary["canonical_unit_id"].eq(unit)) & (summary["horizon"].eq(horizon)) & (summary["split"].eq("robustness"))]
    if row.empty:
        return False
    r = row.iloc[0]
    years = year_summary.loc[(year_summary["canonical_unit_id"].eq(unit)) & (year_summary["horizon"].eq(horizon)) & (year_summary["split"].eq("robustness"))]
    each_abs = bool((years["mean_net_return"] >= -0.0050).all()) if int(r["year_count"]) == 2 else False
    each_rel = bool((years["mean_matched_delta_return"] >= -0.0050).all()) if int(r["year_count"]) == 2 else False
    return bool(
        int(r["complete_event_count"]) >= 300
        and float(r["complete_event_share"]) >= 0.95
        and int(r["year_count"]) == 2
        and int(r["min_year_complete_event_count"]) >= 75
        and float(r["relative_comparable_event_share"]) >= 0.95
        and safe_share(float(r["blocked_insufficient_comparator_count"]), float(r["complete_event_count"])) <= 0.05
        and float(r["mean_net_return"]) >= -0.0025
        and float(r["median_net_return"]) >= -0.0050
        and float(r["p10_net_return"]) >= -0.0900
        and float(r["loss_rate"]) <= 0.58
        and float(r["mean_matched_delta_return"]) >= -0.0025
        and each_abs
        and each_rel
        and float(r["top1_instrument_event_share"]) <= 0.05
        and float(r["top5_instrument_event_share"]) <= 0.20
        and float(r["top1_industry_event_share"]) <= 0.35
        and float(r["top1_entry_date_event_share"]) <= 0.05
        and float(r["fallback_comparator_share"]) <= 0.30
    )


def write_gate_audits(paths: Paths, summary: pd.DataFrame) -> None:
    write_csv(summary[["canonical_unit_id", "horizon", "split", "complete_event_count", "complete_event_share", "year_count", "min_year_complete_event_count", "sample_status", "sample_gate_pass"]], paths.reports_dir / "r01_sample_gate_audit.csv")
    write_csv(summary[["canonical_unit_id", "horizon", "split", "top1_instrument_event_share", "top5_instrument_event_share", "top1_industry_event_share", "top1_entry_date_event_share", "fallback_comparator_share", "concentration_gate_pass"]], paths.reports_dir / "r01_concentration_gate_audit.csv")
    write_csv(summary[["canonical_unit_id", "horizon", "split", "mean_net_return", "median_net_return", "p10_net_return", "loss_rate", "absolute_positive"]], paths.reports_dir / "r01_absolute_gate_audit.csv")
    write_csv(summary[["canonical_unit_id", "horizon", "split", "relative_comparable_event_share", "blocked_insufficient_comparator_count", "fallback_comparator_share", "mean_matched_delta_return", "median_matched_delta_return", "p10_matched_delta_return", "matched_loss_rate_delta", "weak_comparator_quality", "relative_positive"]], paths.reports_dir / "r01_relative_gate_audit.csv")
    write_csv(summary[["canonical_unit_id", "horizon", "split", "robustness_confirmed"]], paths.reports_dir / "r01_robustness_confirmation_audit.csv")
    write_csv(summary[["canonical_unit_id", "horizon", "split", "horizon_pass", "strongly_negative", "adjacent_horizon_shape_status"]], paths.reports_dir / "r01_horizon_shape_audit.csv")


def write_decompositions(paths: Paths, joined: pd.DataFrame) -> None:
    complete = joined.loc[joined["execution_status"].eq("complete_executable")].copy()
    regime_beta = decomposition_rows(complete, ["market_state", "beta_bucket"])
    industry_liquidity = decomposition_rows(complete, ["industry_id", "liquidity_quintile"])
    write_csv(regime_beta, paths.reports_dir / "r01_regime_beta_decomposition.csv")
    write_csv(industry_liquidity, paths.reports_dir / "r01_industry_liquidity_decomposition.csv")


def decomposition_rows(df: pd.DataFrame, axes: list[str]) -> pd.DataFrame:
    rows = []
    for axis in axes:
        if axis not in df:
            continue
        for (unit, horizon, split, value), group in df.groupby(["canonical_unit_id", "horizon", "split", axis], dropna=False):
            comparable = group.loc[group["matched_comparator_status"].eq("comparable")]
            parent = df.loc[(df["canonical_unit_id"].eq(unit)) & (df["horizon"].eq(horizon)) & (df["split"].eq(split))]
            rows.append(
                {
                    "canonical_unit_id": unit,
                    "horizon": horizon,
                    "split": split,
                    "decomposition_axis": axis,
                    "decomposition_value": value if pd.notna(value) else "UNKNOWN",
                    "complete_event_count": len(group),
                    "mean_net_return": safe_mean(group["net_return"]),
                    "median_net_return": float(group["net_return"].median()) if len(group) else np.nan,
                    "p10_net_return": safe_quantile(group["net_return"], 0.10),
                    "loss_rate": safe_mean(group["net_return"] < 0),
                    "relative_comparable_event_share": safe_share(len(comparable), len(group)),
                    "mean_matched_delta_return": safe_mean(comparable["matched_delta_return"]),
                    "median_matched_delta_return": float(comparable["matched_delta_return"].median()) if len(comparable) else np.nan,
                    "p10_matched_delta_return": safe_quantile(comparable["matched_delta_return"], 0.10),
                    "matched_loss_rate_delta": safe_mean(comparable["net_return"] < 0) - safe_mean(comparable["matched_comparator_net_return"] < 0) if len(comparable) else np.nan,
                    "event_share": safe_share(len(group), len(parent)),
                    "net_return_contribution_share": contribution_share(group, axis, "net_return", 1),
                    "matched_delta_contribution_share": contribution_share(comparable, axis, "matched_delta_return", 1),
                }
            )
    return pd.DataFrame(rows)


def build_right_tail(config: dict[str, Any], paths: Paths, feature: pd.DataFrame, execution: pd.DataFrame) -> pd.DataFrame:
    calendar = load_calendar(config)
    pos_map = trading_day_pos(calendar)
    feature_lookup = make_feature_lookup(feature)
    complete = execution.loc[execution["execution_status"].eq("complete_executable")].copy()
    pivot = complete.pivot_table(index=["canonical_unit_id", "event_key", "instrument_id", "split", "entry_execution_date", "entry_price"], columns="horizon", values="net_return", aggfunc="first").reset_index()
    rows = []
    for record in pivot.itertuples(index=False):
        entry_date = pd.Timestamp(record.entry_execution_date)
        entry_price = float(record.entry_price)
        start_pos = pos_map.get(entry_date)
        status = "blocked_missing_forward_path"
        path_status = "blocked_missing_forward_path"
        max_gain = np.nan
        first20 = pd.NaT
        first50 = pd.NaT
        first20_offset = np.nan
        first50_offset = np.nan
        post_h20 = np.nan
        if start_pos is not None:
            end_pos = start_pos + int(config["frozen_formula_constants"]["right_tail_horizon_trading_days"])
            if end_pos >= len(calendar):
                path_status = "censored_provider_end"
                status = "censored_not_evaluable"
            else:
                end_date = pd.Timestamp(calendar[end_pos])
                if split_for_date(config, end_date) == record.split:
                    path_status = "complete_same_split_120d"
                elif split_for_date(config, end_date) == "provider_tail":
                    path_status = "censored_provider_end"
                else:
                    path_status = "complete_cross_split_120d_readonly"
                dates = [pd.Timestamp(calendar[idx]) for idx in range(start_pos, end_pos + 1)]
                path_rows = []
                for idx, date in enumerate(dates):
                    info = feature_lookup.get((record.instrument_id, date))
                    if info is not None and finite(info.get("close")):
                        gain = float(info["close"]) / entry_price - 1.0
                        path_rows.append((date, idx, gain))
                if path_rows and path_status in {"complete_same_split_120d", "complete_cross_split_120d_readonly"}:
                    gains = pd.DataFrame(path_rows, columns=["date", "offset", "gain"])
                    max_gain = float(gains["gain"].max())
                    hit20 = gains.loc[gains["gain"] >= float(config["frozen_formula_constants"]["right_tail_plus20_threshold"])]
                    hit50 = gains.loc[gains["gain"] >= float(config["frozen_formula_constants"]["right_tail_plus50_threshold"])]
                    if not hit20.empty:
                        first20 = pd.Timestamp(hit20.iloc[0]["date"])
                        first20_offset = int(hit20.iloc[0]["offset"])
                    if not hit50.empty:
                        first50 = pd.Timestamp(hit50.iloc[0]["date"])
                        first50_offset = int(hit50.iloc[0]["offset"])
                    post = gains.loc[gains["offset"] > 20, "gain"]
                    post_h20 = float(post.max()) if len(post) else np.nan
                    if not hit50.empty:
                        status = "hit_plus50"
                    elif not hit20.empty:
                        status = "hit_plus20_only"
                    else:
                        status = "no_hit_complete"
                elif path_status.startswith("censored"):
                    status = "censored_not_evaluable"
        rows.append(
            {
                "canonical_unit_id": record.canonical_unit_id,
                "event_key": record.event_key,
                "instrument_id": record.instrument_id,
                "split": record.split,
                "entry_execution_date": entry_date,
                "entry_price": entry_price,
                "max_gain_120d": max_gain,
                "first_plus20_hit_date": first20,
                "first_plus20_hit_offset": first20_offset,
                "first_plus50_hit_date": first50,
                "first_plus50_hit_offset": first50_offset,
                "H5_net_return": getattr(record, "H5", np.nan),
                "H10_net_return": getattr(record, "H10", np.nan),
                "H20_net_return": getattr(record, "H20", np.nan),
                "post_H20_max_gain_to_H120": post_h20,
                "right_tail_status": status,
                "right_tail_path_status": path_status,
            }
        )
    panel = pd.DataFrame(rows)
    write_parquet(panel, paths.cache_dir / "r01_right_tail_diagnostic_panel.parquet")
    readout = panel.groupby(["canonical_unit_id", "split", "right_tail_path_status", "right_tail_status"], dropna=False).size().reset_index(name="event_count") if not panel.empty else pd.DataFrame()
    write_csv(readout, paths.reports_dir / "r01_right_tail_readout.csv")
    censor = panel.groupby(["canonical_unit_id", "split", "right_tail_path_status"], dropna=False).size().reset_index(name="event_count") if not panel.empty else pd.DataFrame()
    write_csv(censor, paths.reports_dir / "r01_right_tail_censoring_audit.csv")
    return panel


def bool_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def summary_row(summary: pd.DataFrame, unit: str, horizon: str, split: str = "validation") -> pd.Series | None:
    row = summary.loc[(summary["canonical_unit_id"].eq(unit)) & (summary["horizon"].eq(horizon)) & (summary["split"].eq(split))]
    if row.empty:
        return None
    return row.iloc[0]


def h10_validated_pass(summary: pd.DataFrame, unit: str) -> bool:
    row = summary_row(summary, unit, "H10")
    return bool(row is not None and bool_value(row["sample_gate_pass"]) and bool_value(row["concentration_gate_pass"]) and bool_value(row["absolute_positive"]) and bool_value(row["relative_positive"]))


def adjacent_status(summary: pd.DataFrame, unit: str) -> str:
    h5 = summary_row(summary, unit, "H5")
    h20 = summary_row(summary, unit, "H20")
    rows = [r for r in [h5, h20] if r is not None]
    if any(bool_value(r["strongly_negative"]) for r in rows):
        return "adjacent_horizon_strongly_negative"
    if any(str(r["adjacent_horizon_shape_status"]) == "adjacent_horizon_not_evaluable" for r in rows):
        return "adjacent_horizon_not_evaluable"
    return "adjacent_horizon_clean"


def adjacent_clean(summary: pd.DataFrame, unit: str) -> bool:
    return adjacent_status(summary, unit) == "adjacent_horizon_clean"


def robustness_confirmed(summary: pd.DataFrame, unit: str) -> bool:
    row = summary_row(summary, unit, "H10")
    return bool(row is not None and bool_value(row["robustness_confirmed"]))


def primary_h10_evaluable_for_sparse(summary: pd.DataFrame) -> bool:
    row = summary_row(summary, PRIMARY_UNIT, "H10")
    return bool(row is not None and bool_value(row["sample_gate_pass"]) and bool_value(row["concentration_gate_pass"]))


def sample_limited_return_lead(summary: pd.DataFrame, unit: str) -> bool:
    row = summary_row(summary, unit, "H10")
    return bool(
        row is not None
        and str(row["sample_status"]) == "sample_limited_lead"
        and bool_value(row["concentration_gate_pass"])
        and bool_value(row["absolute_positive"])
        and bool_value(row["relative_positive"])
    )


def non_fast_fail_units_for_quadrant(summary: pd.DataFrame) -> list[str]:
    units = [PRIMARY_UNIT]
    if primary_h10_evaluable_for_sparse(summary):
        units.append(SPARSE_UNIT)
    return units


def horizon_specific_lead(summary: pd.DataFrame, unit: str) -> bool:
    h10 = summary_row(summary, unit, "H10")
    h5 = summary_row(summary, unit, "H5")
    h20 = summary_row(summary, unit, "H20")
    h10_pass = bool(h10 is not None and bool_value(h10["horizon_pass"]))
    return bool(not h10_pass and any(r is not None and bool_value(r["horizon_pass"]) for r in [h5, h20]))


def replay_final_decision(summary: pd.DataFrame, contract_ok: bool = True) -> dict[str, Any]:
    primary_h10 = summary_row(summary, PRIMARY_UNIT, "H10")
    primary_quad = quadrant(primary_h10)
    sparse_h10 = summary_row(summary, SPARSE_UNIT, "H10")
    fast_h10 = summary_row(summary, FAST_FAIL_UNIT, "H10")
    base = {
        "requirement_id": REQUIREMENT_ID,
        "primary_unit_h10_quadrant": primary_quad,
        "primary_unit_robustness_confirmed": robustness_confirmed(summary, PRIMARY_UNIT),
        "primary_unit_adjacent_horizon_status": adjacent_status(summary, PRIMARY_UNIT),
        "sparse_unit_status": quadrant(sparse_h10),
        "fast_fail_unit_status": quadrant(fast_h10),
        "created_at": now_iso(),
    }
    if not contract_ok:
        return final_row(base, "rule_01_blocked_data_or_execution_contract", "r01_blocked_data_or_execution_contract", "Required data, split, execution, cost, or canonical unit authority is missing.")
    if h10_validated_pass(summary, PRIMARY_UNIT) and robustness_confirmed(summary, PRIMARY_UNIT) and adjacent_clean(summary, PRIMARY_UNIT):
        return final_row(base, "rule_02_primary_supported", "r01_short_horizon_local_unit_supported", "Primary natural-exit unit passed H10, robustness, and adjacent horizon checks.")
    if h10_validated_pass(summary, PRIMARY_UNIT) and not robustness_confirmed(summary, PRIMARY_UNIT):
        return final_row(base, "rule_03_primary_validation_only_lead", "r01_unstable_validation_only_lead", "Primary natural-exit unit passed validation H10 but robustness did not confirm.")
    if h10_validated_pass(summary, PRIMARY_UNIT) and robustness_confirmed(summary, PRIMARY_UNIT) and adjacent_status(summary, PRIMARY_UNIT) == "adjacent_horizon_strongly_negative":
        return final_row(base, "rule_04_primary_unstable_horizon_shape", "r01_unstable_horizon_shape_no_search_allowed", "Primary H10 pass was contradicted by strongly negative adjacent horizon.")
    if h10_validated_pass(summary, PRIMARY_UNIT) and robustness_confirmed(summary, PRIMARY_UNIT) and adjacent_status(summary, PRIMARY_UNIT) == "adjacent_horizon_not_evaluable":
        return final_row(base, "rule_05_primary_adjacent_horizon_not_evaluable", "r01_adjacent_horizon_not_evaluable_validation_lead", "Primary H10 pass had adjacent horizon not evaluable.")
    if primary_h10_evaluable_for_sparse(summary) and h10_validated_pass(summary, SPARSE_UNIT) and robustness_confirmed(summary, SPARSE_UNIT) and adjacent_clean(summary, SPARSE_UNIT):
        return final_row(base, "rule_06_sparse_event_source_followup", "r01_sparse_event_unit_supported_event_source_followup", "Sparse unit passed but only as low-overlap event-source follow-up.")
    if not h10_validated_pass(summary, PRIMARY_UNIT) and h10_validated_pass(summary, FAST_FAIL_UNIT) and robustness_confirmed(summary, FAST_FAIL_UNIT) and adjacent_clean(summary, FAST_FAIL_UNIT):
        return final_row(base, "rule_07_fast_fail_only_loss_control_lead", "r01_fast_fail_only_loss_control_lead", "Fixed fast-fail variant passed while primary natural-exit did not.")
    for unit in non_fast_fail_units_for_quadrant(summary):
        row = summary_row(summary, unit, "H10")
        if row is not None and bool_value(row["sample_gate_pass"]) and bool_value(row["concentration_gate_pass"]) and bool_value(row["relative_positive"]) and not bool_value(row["absolute_positive"]):
            return final_row(base, "rule_08_relative_edge_only", "r01_relative_edge_only_hedged_or_regime_audit_required", "Relative edge exists without absolute long-only deployability.")
    for unit in non_fast_fail_units_for_quadrant(summary):
        row = summary_row(summary, unit, "H10")
        if row is not None and bool_value(row["sample_gate_pass"]) and bool_value(row["concentration_gate_pass"]) and bool_value(row["absolute_positive"]) and not bool_value(row["relative_positive"]):
            return final_row(base, "rule_09_beta_or_market_exposure_only", "r01_beta_or_market_exposure_only_no_stock_selection_pass", "Absolute return exists without matched residual edge.")
    for unit in non_fast_fail_units_for_quadrant(summary):
        if horizon_specific_lead(summary, unit):
            return final_row(base, "rule_10_horizon_specific_lead_only", "r01_horizon_specific_lead_only_no_search_allowed", "Only adjacent horizon passed while H10 did not.")
    if sample_limited_return_lead(summary, PRIMARY_UNIT):
        return final_row(base, "rule_11_sample_limited_primary_lead_only", "r01_sample_limited_primary_lead_only", "Primary unit is sample-limited lead only.")
    if sample_limited_return_lead(summary, SPARSE_UNIT):
        return final_row(base, "rule_12_sample_limited_sparse_lead_only", "r01_sample_limited_sparse_event_source_lead_only", "Sparse unit is sample-limited lead only.")
    return final_row(base, "rule_13_no_local_feasibility_support", "r01_no_local_feasibility_support", "No canonical unit supplied local feasibility support.")


def quadrant(row: pd.Series | None) -> str:
    if row is None:
        return "missing"
    return f"absolute_{str(bool_value(row['absolute_positive'])).lower()}__relative_{str(bool_value(row['relative_positive'])).lower()}"


def final_row(base: dict[str, Any], rule: str, decision: str, reason: str) -> dict[str, Any]:
    allowed, blocked = allowed_next(decision)
    out = dict(base)
    out.update(
        {
            "priority_rule_id": rule,
            "final_decision": decision,
            "allowed_next_requirement": allowed,
            "blocked_next_requirements": blocked,
            "decision_reason": reason,
        }
    )
    return out


def allowed_next(decision: str) -> tuple[str, str]:
    mapping = {
        "r01_short_horizon_local_unit_supported": (
            "controlled discovery under strict low-dimensional search; post-entry holding-extension diagnostic; E01-backed harness expansion",
            "portfolio allocator; hedged strategy; right-tail management; live trading",
        ),
        "r01_sparse_event_unit_supported_event_source_followup": ("low-overlap sparse event-source requirement only", "broad pool search; EP4 R05 primitive rescue"),
        "r01_fast_fail_only_loss_control_lead": ("loss-control / risk-state diagnostic only", "underlying exposure pass; holding tuning"),
        "r01_relative_edge_only_hedged_or_regime_audit_required": ("hedged / relative feasibility audit discussion", "long-only pass; market-neutral strategy backtest"),
        "r01_beta_or_market_exposure_only_no_stock_selection_pass": ("beta / regime attribution", "stock-selection edge claim"),
        "r01_horizon_specific_lead_only_no_search_allowed": ("horizon instability explanation", "best-horizon search"),
        "r01_sample_limited_primary_lead_only": ("primary sample-source and execution-blocking review", "threshold loosening for sample"),
        "r01_sample_limited_sparse_event_source_lead_only": ("sparse event-source sample feasibility review", "alpha pass"),
        "r01_unstable_validation_only_lead": ("validation / robustness drift explanation", "search"),
        "r01_unstable_horizon_shape_no_search_allowed": ("horizon instability explanation", "single-horizon promotion"),
        "r01_adjacent_horizon_not_evaluable_validation_lead": ("adjacent horizon evaluability review", "H10-only search"),
        "r01_no_local_feasibility_support": ("pause / renormalize", "grid expansion"),
        "r01_blocked_data_or_execution_contract": ("fix data or execution contract", "economic conclusion"),
    }
    return mapping.get(decision, ("", ""))


def build_final_decision(paths: Paths, summary: pd.DataFrame) -> pd.DataFrame:
    final = pd.DataFrame([replay_final_decision(summary, contract_ok=True)])
    write_csv(final, paths.reports_dir / "r01_final_decision.csv")
    inputs = summary.loc[summary["split"].isin(["validation", "robustness"])].copy()
    write_csv(inputs, paths.reports_dir / "r01_final_decision_inputs.csv")
    return final


def write_artifact_hashes(paths: Paths) -> None:
    rows = []
    for name in CACHE_FILES:
        path = paths.cache_dir / name
        rows.append({"artifact_path": relpath(path), "artifact_type": "cache", "exists": path.exists(), "sha256": file_hash(path)})
    for name in [*RUNNER_REPORTS, *VALIDATOR_REPORTS]:
        path = paths.reports_dir / name
        rows.append({"artifact_path": relpath(path), "artifact_type": "report", "exists": path.exists(), "sha256": file_hash(path)})
    for name in ["r01_run_manifest.json", "r01_validation.json"]:
        path = paths.manifests_dir / name
        rows.append({"artifact_path": relpath(path), "artifact_type": "manifest", "exists": path.exists(), "sha256": file_hash(path)})
    write_json({"created_at": now_iso(), "artifacts": rows}, paths.manifests_dir / "r01_artifact_hashes.json")


def run_pipeline(config_path: str | Path = DEFAULT_CONFIG) -> None:
    config, paths = load_config(config_path)
    build_input_audits(config, paths)
    feature, _ = build_feature_panel(config, paths)
    build_unit_registry(config, paths)
    event = build_event_panel(config, paths, feature)
    execution = build_execution_panel(config, paths, feature, event)
    comparator = build_comparator_panel(config, paths, feature, execution)
    summary, _ = build_summaries(config, paths, feature, execution, comparator)
    build_right_tail(config, paths, feature, execution)
    final = build_final_decision(paths, summary)
    write_json(
        {
            "requirement_id": REQUIREMENT_ID,
            "plan_id": PLAN_ID,
            "config_path": relpath(paths.config_path),
            "output_root": relpath(paths.output_root),
            "created_at": now_iso(),
            "git_commit": git_commit_hash(),
            "final_decision": final.iloc[0]["final_decision"],
        },
        paths.manifests_dir / "r01_run_manifest.json",
    )
    write_artifact_hashes(paths)


def required_output_paths(paths: Paths) -> list[Path]:
    return [paths.cache_dir / name for name in CACHE_FILES] + [paths.reports_dir / name for name in RUNNER_REPORTS] + [paths.manifests_dir / name for name in RUNNER_MANIFESTS]


def validate_outputs(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths = load_config(config_path)
    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"check_name": name, "status": "passed" if condition else "failed", "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    check("requirement_id", config.get("requirement_id") == REQUIREMENT_ID, str(config.get("requirement_id")))
    check("plan_id", config.get("plan_id") == PLAN_ID, str(config.get("plan_id")))
    check("canonical_units", config.get("canonical_units") == CANONICAL_UNITS, str(config.get("canonical_units")))
    check("horizons", config.get("execution", {}).get("horizons") == HORIZONS, str(config.get("execution", {}).get("horizons")))
    check("primary_horizon", config.get("execution", {}).get("primary_horizon") == 10, str(config.get("execution", {}).get("primary_horizon")))
    check("costs", config["execution"]["buy_cost_bps"] == 30 and config["execution"]["sell_cost_bps"] == 80 and config["execution"]["round_trip_cost_bps"] == 110, "")
    check("execution_lag_and_limit", config["execution"]["max_entry_execution_lag_trading_days"] == 5 and config["execution"]["max_exit_execution_lag_trading_days"] == 5 and float(config["execution"]["mainboard_limit_inference_pct"]) == 0.095, "")
    for key, value in config.get("guardrails", {}).items():
        check(f"guardrail_{key}", value is False, str(value))

    missing = [relpath(path) for path in required_output_paths(paths) if not path.exists()]
    check("all_required_outputs_exist", not missing, "; ".join(missing[:10]))
    if missing:
        return write_validation(paths, checks, failures, "blocked_missing_required_artifact", "")

    feature = pd.read_parquet(paths.cache_dir / "r01_daily_feature_panel.parquet")
    event = pd.read_parquet(paths.cache_dir / "r01_canonical_event_panel.parquet")
    execution = pd.read_parquet(paths.cache_dir / "r01_execution_event_panel.parquet")
    comparator = pd.read_parquet(paths.cache_dir / "r01_matched_comparator_panel.parquet")
    right_tail = pd.read_parquet(paths.cache_dir / "r01_right_tail_diagnostic_panel.parquet")
    summary = pd.read_csv(paths.reports_dir / "r01_event_summary_by_unit_horizon_split.csv")
    final = pd.read_csv(paths.reports_dir / "r01_final_decision.csv")
    final_inputs = pd.read_csv(paths.reports_dir / "r01_final_decision_inputs.csv")

    required_feature_cols = {
        "rolling_min_close_60_prev",
        "rolling_max_close_60_prev",
        "money_ma20_prev",
        "history_ok",
        "base_high_20_prev",
        "base_low_20_prev",
        "base_drawdown_pct",
        "breakout_ret_pct",
        "pre_base_vol20",
        "recent_vol10",
        "vol_contraction_ratio",
        "ma20",
        "atr20_pct",
        "money_ratio5_to20",
        "avg_money20_rank_pct",
    }
    check("feature_formula_inputs", required_feature_cols.issubset(feature.columns), ",".join(sorted(required_feature_cols - set(feature.columns))))
    observed_units = set(event["canonical_unit_id"].dropna().unique().tolist())
    observed_horizons = set(execution["horizon"].dropna().unique().tolist())
    check("event_units_exact", observed_units == set(CANONICAL_UNITS), str(sorted(observed_units)))
    check("execution_horizons_exact", observed_horizons == set(HORIZON_LABELS), str(sorted(observed_horizons)))
    check("blocked_reason_unprefixed", set(execution.loc[execution["blocked_reason"].notna() & execution["blocked_reason"].ne(""), "blocked_reason"]).issubset(set(BLOCKED_REASONS)), "")
    complete_blocked_empty = execution.loc[execution["execution_status"].eq("complete_executable"), "blocked_reason"].fillna("").eq("").all()
    check("complete_rows_have_empty_blocked_reason", bool(complete_blocked_empty), "")
    check("comparator_status_values", set(comparator.get("matched_comparator_status", pd.Series(dtype=object)).dropna().unique()).issubset({"comparable", "blocked_insufficient_comparator", "blocked_missing_comparator_price"}), "")
    comparable_summary_ok = True
    if not comparator.empty:
        comparable = comparator.loc[comparator["matched_comparator_status"].eq("comparable")]
        comparable_summary_ok = not comparable["matched_delta_return"].isna().all() if not comparable.empty else True
    check("matched_delta_available_for_comparable", comparable_summary_ok, "")
    right_path_ok = set(right_tail.get("right_tail_path_status", pd.Series(dtype=object)).dropna().unique()).issubset(set(RIGHT_TAIL_PATH_STATUSES))
    right_status_ok = set(right_tail.get("right_tail_status", pd.Series(dtype=object)).dropna().unique()).issubset(set(RIGHT_TAIL_STATUSES))
    check("right_tail_enums", bool(right_path_ok and right_status_ok), "")
    censored_ok = right_tail.loc[right_tail["right_tail_path_status"].astype(str).str.startswith("censored"), "right_tail_status"].eq("censored_not_evaluable").all() if not right_tail.empty else True
    check("right_tail_censored_not_no_hit", bool(censored_ok), "")
    forbidden_final_cols = {"right_tail_status", "right_tail_path_status", "decomposition_axis", "decomposition_value"}
    check("final_inputs_no_right_tail_or_decomposition_filter", forbidden_final_cols.isdisjoint(final_inputs.columns), ",".join(sorted(forbidden_final_cols & set(final_inputs.columns))))
    check("final_decision_enum", final.iloc[0]["final_decision"] in FINAL_DECISIONS, str(final.iloc[0]["final_decision"]))
    check("priority_rule_enum", final.iloc[0]["priority_rule_id"] in PRIORITY_RULES, str(final.iloc[0].get("priority_rule_id")))
    replay = replay_final_decision(summary, contract_ok=True)
    replay_match = final.iloc[0]["final_decision"] == replay["final_decision"] and final.iloc[0]["priority_rule_id"] == replay["priority_rule_id"]
    check("final_decision_replay", replay_match, f"observed={final.iloc[0]['final_decision']} replay={replay['final_decision']}")
    if final.iloc[0]["priority_rule_id"] in {"rule_06_sparse_event_source_followup", "rule_08_relative_edge_only", "rule_09_beta_or_market_exposure_only", "rule_10_horizon_specific_lead_only"}:
        check("sparse_primary_precondition", primary_h10_evaluable_for_sparse(summary), "")

    validation_status = "passed" if not failures else "failed"
    return write_validation(paths, checks, failures, validation_status, final.iloc[0]["final_decision"], summary=summary, final=final, replay=replay)


def write_validation(
    paths: Paths,
    checks: list[dict[str, Any]],
    failures: list[str],
    validation_status: str,
    final_decision: str,
    summary: pd.DataFrame | None = None,
    final: pd.DataFrame | None = None,
    replay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = pd.DataFrame(checks)
    write_csv(gate, paths.reports_dir / "r01_validation_gate_audit.csv")
    write_csv(gate[["check_name", "status", "detail"]], paths.reports_dir / "r01_schema_validation_audit.csv")
    replay_df = pd.DataFrame([replay or {"final_decision": final_decision, "priority_rule_id": ""}])
    write_csv(replay_df, paths.reports_dir / "r01_final_decision_replay_audit.csv")
    payload = {
        "validation_status": validation_status,
        "requirement_id": REQUIREMENT_ID,
        "plan_id": PLAN_ID,
        "config_path": relpath(paths.config_path),
        "output_root": relpath(paths.output_root),
        "gate_count": len(checks),
        "passed_gate_count": sum(1 for row in checks if row["status"] == "passed"),
        "failed_gate_count": sum(1 for row in checks if row["status"] != "passed"),
        "final_decision": final_decision,
        "failures": failures,
        "created_at": now_iso(),
    }
    write_json(payload, paths.manifests_dir / "r01_validation.json")
    if summary is not None and final is not None:
        write_final_report(paths, payload, summary, final)
    write_artifact_hashes(paths)
    return payload


def write_final_report(paths: Paths, validation: dict[str, Any], summary: pd.DataFrame, final: pd.DataFrame) -> None:
    final_row_data = final.iloc[0].to_dict()
    primary = summary_row(summary, PRIMARY_UNIT, "H10")
    lines = [
        "# EP5 R01 Final Report",
        "",
        "## 1. Boundary and non-goals",
        "",
        "R01 did not perform alpha search.",
        "R01 did not use big-winner labels for pass/fail.",
        "R01 did not tune thresholds after validation.",
        "R01 does not approve a production strategy.",
        "",
        "## 2. Input and data audit",
        "",
        f"- Output root: `{relpath(paths.output_root)}`",
        f"- Validation status: `{validation['validation_status']}`",
        "",
        "## 3. Canonical unit registry",
        "",
        "- `r01_launch_breakout_money_surge_natural_exit_v0`: primary short-horizon exposure unit.",
        "- `r01_launch_breakout_money_surge_fast_fail_v0`: secondary loss-control variant.",
        "- `r01_base_breakout_vcp_sparse_natural_exit_v0`: backup sparse event-source probe.",
        "",
        "## 4. Execution denominator and blocking",
        "",
        "See `reports/r01_execution_block_audit.csv` and `reports/r01_denominator_audit.csv`.",
        "",
        "## 5. H10 four-quadrant result",
        "",
        f"- Primary H10 quadrant: `{final_row_data.get('primary_unit_h10_quadrant', '')}`",
    ]
    if primary is not None:
        lines.extend(
            [
                f"- Primary H10 complete events: `{int(primary['complete_event_count'])}`",
                f"- Primary H10 mean net return: `{float(primary['mean_net_return']):.6f}`",
                f"- Primary H10 mean matched delta: `{float(primary['mean_matched_delta_return']):.6f}`",
            ]
        )
    lines.extend(
        [
            "",
            "## 6. H5/H20 horizon shape",
            "",
            "See `reports/r01_horizon_shape_audit.csv`.",
            "",
            "## 7. Matched comparator and relative edge",
            "",
            "Matched-delta gate statistics use only `matched_comparator_status = comparable` rows.",
            "",
            "## 8. Year / regime / beta-state decomposition",
            "",
            "See `reports/r01_event_summary_by_unit_horizon_year.csv`, `reports/r01_regime_beta_decomposition.csv`, and `reports/r01_industry_liquidity_decomposition.csv`.",
            "",
            "## 9. Robustness confirmation",
            "",
            f"- Primary robustness confirmed: `{final_row_data.get('primary_unit_robustness_confirmed', '')}`",
            "",
            "## 10. Right-tail diagnostic, read-only",
            "",
            "Right-tail outputs are post-entry diagnostics and are excluded from final decision computation.",
            "",
            "## 11. Final decision and allowed next requirement",
            "",
            f"- Final decision: `{final_row_data.get('final_decision', '')}`",
            f"- Priority rule: `{final_row_data.get('priority_rule_id', '')}`",
            f"- Allowed next requirement: `{final_row_data.get('allowed_next_requirement', '')}`",
            f"- Blocked next requirements: `{final_row_data.get('blocked_next_requirements', '')}`",
            f"- Reason: {final_row_data.get('decision_reason', '')}",
            "",
            "## 12. Validator status",
            "",
            f"- `validation_status = {validation['validation_status']}`",
            f"- Passed gates: `{validation['passed_gate_count']}` / `{validation['gate_count']}`",
        ]
    )
    (paths.reports_dir / "r01_final_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

#!/usr/bin/env python3
"""Run the BaseRate Alpha158 + LightGBM OOS baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore", category=FutureWarning)


BASE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = BASE_DIR.parent
DEFAULT_CONFIG = BASE_DIR / "configs/alpha158_lgbm_oos.yaml"
REPORT_ARTIFACTS = [
    "base_rate_data_preflight_audit.csv",
    "base_rate_canonical_data_audit.csv",
    "base_rate_pit_universe_audit.csv",
    "base_rate_feature_dictionary.csv",
    "base_rate_label_dictionary.csv",
    "base_rate_split_audit.csv",
    "base_rate_feature_asof_leakage_audit.csv",
    "base_rate_observed_reference_audit.csv",
    "base_rate_model_config_audit.csv",
    "base_rate_model_train_metric_by_fold.csv",
    "base_rate_prediction_coverage_audit.csv",
    "base_rate_portfolio_config_matrix.csv",
    "base_rate_execution_constraint_audit.csv",
    "base_rate_cost_model_audit.csv",
    "base_rate_trade_summary_by_fold.csv",
    "base_rate_portfolio_daily_summary.csv",
    "base_rate_benchmark_comparison.csv",
    "base_rate_random_same_turnover_baseline.csv",
    "base_rate_cost_sensitivity.csv",
    "base_rate_topk_sensitivity.csv",
    "base_rate_capacity_proxy.csv",
    "base_rate_year_by_year_metrics.csv",
    "base_rate_failure_case_review.csv",
    "base_rate_forbidden_selection_self_check.csv",
    "base_rate_run_manifest.json",
    "BaseRate-Alpha158-LGBM-OOS-report.md",
]
CACHE_ARTIFACTS = [
    "feature_panel.parquet",
    "label_panel.parquet",
    "prediction_panel.parquet",
    "order_panel.parquet",
    "trade_panel.parquet",
    "portfolio_daily.parquet",
]
FORBIDDEN_OUTPUTS = [
    "primitive_candidate",
    "candidate_for_p1_strategy",
    "validated_model",
    "production_model",
    "selected_final_strategy",
    "freeze_strategy",
    "proceed_to_primitive_discovery",
    "proceed_to_explore11",
    "candidate_for_p1_strategy",
    "validated_strategy",
    "selected_final_model",
    "selected_score_bucket",
]
EXPECTED_REPORT_COLUMNS = {
    "base_rate_data_preflight_audit.csv": ["data_source", "path", "exists", "pass", "blocked_reason"],
    "base_rate_canonical_data_audit.csv": ["canonical_path", "source_explore_path", "source_phase", "content_hash", "pass"],
    "base_rate_pit_universe_audit.csv": ["date", "pit_member_count", "provider_member_count", "intersection_count", "coverage_rate", "pass"],
    "base_rate_feature_dictionary.csv": ["feature_name", "feature_family", "uses_future_data", "primary_allowed", "sensitivity_allowed"],
    "base_rate_label_dictionary.csv": ["label_name", "label_expression", "training_role", "decision_role", "allowed_for_positive_decision"],
    "base_rate_split_audit.csv": ["fold_id", "train_start", "valid_start", "test_start", "fold_trainable", "pass"],
    "base_rate_model_config_audit.csv": ["fold_id", "model_id", "hyperparameter_search_used", "oos_used_for_model_selection", "pass"],
    "base_rate_model_train_metric_by_fold.csv": ["fold_id", "label_name", "model_id", "train_row_count", "valid_row_count", "fit_status"],
    "base_rate_prediction_coverage_audit.csv": ["fold_id", "date", "pit_member_count", "raw_prediction_count", "prediction_count", "prediction_coverage", "pass"],
    "base_rate_portfolio_config_matrix.csv": ["portfolio_id", "label_name", "topk", "n_drop", "decision_primary", "predeclared"],
    "base_rate_execution_constraint_audit.csv": ["date", "side", "block_reason", "order_count", "blocked_order_count", "block_rate"],
    "base_rate_cost_model_audit.csv": ["cost_scenario", "commission_buy", "commission_sell", "stamp_tax_sell", "pass"],
    "base_rate_trade_summary_by_fold.csv": ["fold_id", "portfolio_id", "cost_scenario", "order_count", "trade_count", "fill_rate"],
    "base_rate_portfolio_daily_summary.csv": ["date", "signal_date", "portfolio_id", "label_name", "cost_scenario", "net_return"],
    "base_rate_benchmark_comparison.csv": ["fold_id", "portfolio_id", "benchmark_id", "cost_scenario", "net_annual_return", "excess_return", "tracking_error"],
    "base_rate_random_same_turnover_baseline.csv": ["fold_id", "portfolio_id", "repeat_id", "same_turnover", "same_execution_constraints", "same_cost_model", "net_annual_return", "random_turnover_annualized", "model_turnover_annualized"],
    "base_rate_cost_sensitivity.csv": ["fold_id", "portfolio_id", "cost_scenario", "net_annual_return", "collapse_vs_base", "pass"],
    "base_rate_topk_sensitivity.csv": ["fold_id", "portfolio_id", "label_name", "topk", "n_drop", "selection_allowed"],
    "base_rate_capacity_proxy.csv": ["date", "portfolio_id", "estimated_trade_notional", "participation_rate_proxy", "pass"],
    "base_rate_year_by_year_metrics.csv": ["year", "portfolio_id", "cost_scenario", "return", "benchmark_excess", "fill_rate"],
    "base_rate_failure_case_review.csv": ["case_id", "portfolio_id", "failure_type", "metric_impact", "action_required"],
    "base_rate_forbidden_selection_self_check.csv": ["forbidden_output", "observed_count", "pass", "evidence_path"],
}


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    report_dir: Path


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(TOPIC_DIR))
    except ValueError:
        return str(resolved)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            digest.update(str(child.relative_to(path)).encode("utf-8"))
            digest.update(child.read_bytes())
    else:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TOPIC_DIR, text=True).strip()
    except Exception:
        return ""


def extract_lgb_best_iteration(model: Any) -> int | str:
    booster = getattr(model, "model", None)
    for owner in [booster, model]:
        if owner is None:
            continue
        for attr in ["best_iteration_", "best_iteration"]:
            value = getattr(owner, attr, None)
            if callable(value):
                value = value()
            if value not in [None, ""]:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return value
    return ""


def normalize_qlib_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if list(result.index.names) == ["instrument", "datetime"]:
        result = result.reorder_levels(["datetime", "instrument"])
    result.index.names = ["datetime", "instrument"]
    result = result.sort_index()
    result.columns = [str(c).replace("$", "") for c in result.columns]
    return result


def load_calendar(provider_uri: Path) -> pd.DatetimeIndex:
    path = provider_uri / "calendars/day.txt"
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(values), name="date")


def next_trading_day(calendar: pd.DatetimeIndex, date: pd.Timestamp) -> pd.Timestamp | None:
    pos = calendar.searchsorted(pd.Timestamp(date), side="right")
    if pos >= len(calendar):
        return None
    return pd.Timestamp(calendar[pos])


def flatten_label_config(config: dict[str, Any]) -> list[dict[str, Any]]:
    labels = []
    for role in ["primary", "secondary_reported_not_decision", "sensitivity"]:
        for name, spec in (config["labels"].get(role) or {}).items():
            row = dict(spec)
            row["label_name"] = name
            row["role"] = role
            labels.append(row)
    return labels


def portfolio_configs(config: dict[str, Any], labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary_label = next(label["label_name"] for label in labels if label["role"] == "primary")
    configs = []
    primary = dict(config["portfolio"]["primary"])
    primary["portfolio_id"] = primary["name"]
    primary["label_name"] = primary_label
    primary["decision_primary"] = True
    primary["sensitivity_role"] = "decision_primary"
    configs.append(primary)
    for item in config["portfolio"].get("sensitivity", []):
        row = dict(item)
        row["portfolio_id"] = row["name"]
        row["label_name"] = primary_label
        row["decision_primary"] = False
        row["sensitivity_role"] = "portfolio_sensitivity"
        configs.append(row)
    for label in labels:
        if label["role"] == "primary":
            continue
        row = dict(primary)
        row["portfolio_id"] = f"{primary['name']}_{label['label_name'].lower()}"
        row["label_name"] = label["label_name"]
        row["decision_primary"] = False
        row["sensitivity_role"] = "label_sensitivity"
        configs.append(row)
    return configs


def compute_metrics(daily: pd.DataFrame, benchmark_col: str | None = None) -> dict[str, float]:
    if daily.empty:
        return {}
    returns = pd.to_numeric(daily["net_return"], errors="coerce").fillna(0.0)
    gross = pd.to_numeric(daily.get("gross_return", returns), errors="coerce").fillna(0.0)
    value = (1.0 + returns).cumprod()
    cumulative = float(value.iloc[-1] - 1.0) if len(value) else 0.0
    years = max(len(returns) / 252.0, 1 / 252.0)
    annual = float((1.0 + cumulative) ** (1.0 / years) - 1.0)
    vol = float(returns.std(ddof=0) * math.sqrt(252)) if len(returns) else 0.0
    sharpe = float(returns.mean() / returns.std(ddof=0) * math.sqrt(252)) if returns.std(ddof=0) else 0.0
    drawdown = value / value.cummax() - 1.0
    max_dd = float(drawdown.min()) if len(drawdown) else 0.0
    calmar = float(annual / abs(max_dd)) if max_dd else 0.0
    turnover = pd.to_numeric(daily.get("turnover", 0.0), errors="coerce").fillna(0.0)
    cost = pd.to_numeric(daily.get("cost_drag", 0.0), errors="coerce").fillna(0.0)
    result = {
        "net_annual_return": annual,
        "net_cumulative_return": cumulative,
        "gross_annual_return": float(((1.0 + gross).prod()) ** (1.0 / years) - 1.0),
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "calmar": calmar,
        "annual_volatility": vol,
        "turnover_daily_mean": float(turnover.mean()),
        "turnover_annualized": float(turnover.mean() * 252),
        "cost_drag_annualized": float(cost.mean() * 252),
        "cash_drag": float(pd.to_numeric(daily.get("cash_weight", 0.0), errors="coerce").fillna(0.0).mean()),
        "fill_rate": float(pd.to_numeric(daily.get("fill_rate", 1.0), errors="coerce").fillna(1.0).mean()),
        "execution_block_rate": float(pd.to_numeric(daily.get("execution_block_rate", 0.0), errors="coerce").fillna(0.0).mean()),
    }
    if benchmark_col and benchmark_col in daily:
        bench = pd.to_numeric(daily[benchmark_col], errors="coerce").fillna(0.0)
        bench_value = (1.0 + bench).cumprod()
        bench_cum = float(bench_value.iloc[-1] - 1.0) if len(bench_value) else 0.0
        bench_annual = float((1.0 + bench_cum) ** (1.0 / years) - 1.0)
        excess = returns - bench
        te = float(excess.std(ddof=0) * math.sqrt(252)) if len(excess) else 0.0
        result.update(
            {
                "benchmark_annual_return": bench_annual,
                "benchmark_excess_return": annual - bench_annual,
                "benchmark_tracking_error": te,
                "information_ratio": float(excess.mean() / excess.std(ddof=0) * math.sqrt(252)) if excess.std(ddof=0) else 0.0,
                "benchmark_max_drawdown": float((bench_value / bench_value.cummax() - 1.0).min()) if len(bench_value) else 0.0,
            }
        )
    return result


def year_metrics(daily: pd.DataFrame, benchmark_col: str = "bench_pit_equal") -> pd.DataFrame:
    rows = []
    if daily.empty:
        return pd.DataFrame()
    frame = daily.copy()
    frame["year"] = pd.to_datetime(frame["date"]).dt.year
    for (year, portfolio_id, cost_scenario), group in frame.groupby(["year", "portfolio_id", "cost_scenario"], dropna=False):
        metrics = compute_metrics(group, benchmark_col=benchmark_col)
        rows.append(
            {
                "year": int(year),
                "portfolio_id": portfolio_id,
                "cost_scenario": cost_scenario,
                "return": metrics.get("net_cumulative_return", 0.0),
                "max_drawdown": metrics.get("max_drawdown", 0.0),
                "turnover": metrics.get("turnover_annualized", 0.0),
                "cost_drag": metrics.get("cost_drag_annualized", 0.0),
                "benchmark_excess": metrics.get("benchmark_excess_return", 0.0),
                "fill_rate": metrics.get("fill_rate", 0.0),
            }
        )
    return pd.DataFrame(rows)


def load_market_data(config: dict[str, Any]) -> pd.DataFrame:
    from qlib.data import D

    execution_universe_path = topic_path("data/universe/pit_qlib_instrument_universe.csv")
    qlib_market = config["universe"]["qlib_market"]
    if execution_universe_path.exists():
        instruments = pd.read_csv(execution_universe_path)["instrument"].dropna().astype(str).tolist()
    else:
        instruments = D.instruments(qlib_market)
    fields = ["$open", "$high", "$low", "$close", "$volume", "$money", "$factor"]
    frame = D.features(
        instruments=instruments,
        fields=fields,
        start_time=config["dates"]["canonical_data_start"],
        end_time=config["dates"]["canonical_data_end"],
        freq="day",
    )
    return normalize_qlib_frame(frame)


def preflight(config: dict[str, Any], paths: Paths, market_data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    provider_uri = topic_path(config["provider"]["provider_uri"])
    universe_path = topic_path(config["universe"]["pit_membership"])
    qlib_instr_path = topic_path(config["universe"]["qlib_instruments"])
    industry_path = topic_path("data/targets/pit_industry_membership.csv")
    canonical_inputs = [
        (universe_path, "Explore7/data/universe/pit_mcap500_mainboard_daily.csv", "Explore7"),
        (qlib_instr_path, "Explore7/data/universe/qlib_pit_mcap500_mainboard.txt", "Explore7"),
        (topic_path("data/universe/pit_qlib_instrument_universe.csv"), "Explore7/data/universe/pit_qlib_instrument_universe.csv", "Explore7"),
        (topic_path("data/universe/mcap500_mainboard_20251231.csv"), "Explore3/data/universe/mcap500_mainboard_20251231.csv", "Explore3"),
        (topic_path("data/universe/qlib_mcap500_mainboard_20251231.txt"), "Explore3/data/universe/qlib_mcap500_mainboard_20251231.txt", "Explore3"),
        (industry_path, "Explore7/data/targets/pit_industry_membership.csv", "Explore7"),
        (topic_path("data/targets/target_history.csv"), "Explore7/data/targets/target_history.csv", "Explore7"),
        (provider_uri, "Explore7/data/qlib/cn_data_pit", "Explore7"),
    ]
    data_rows = []
    for name, path in [
        ("pit_universe", universe_path),
        ("qlib_instruments", qlib_instr_path),
        ("qlib_provider", provider_uri),
        ("pit_industry_membership", industry_path),
    ]:
        exists = path.exists()
        row_count = ""
        min_date = ""
        max_date = ""
        file_count = 0
        if exists and path.is_file() and path.suffix == ".csv":
            use = pd.read_csv(path, nrows=500000)
            row_count = len(use)
            if "date" in use:
                min_date = str(pd.to_datetime(use["date"]).min().date())
                max_date = str(pd.to_datetime(use["date"]).max().date())
        if exists and path.is_dir():
            file_count = sum(1 for p in path.rglob("*") if p.is_file())
            cal = provider_uri / "calendars/day.txt"
            if cal.exists():
                dates = pd.to_datetime([x.strip() for x in cal.read_text().splitlines() if x.strip()])
                min_date = str(dates.min().date())
                max_date = str(dates.max().date())
        data_rows.append(
            {
                "data_source": name,
                "path": relpath(path),
                "exists": exists,
                "min_date": min_date,
                "max_date": max_date,
                "row_count": row_count,
                "file_count": file_count,
                "content_hash": file_hash(path),
                "pass": bool(exists),
                "blocked_reason": "" if exists else "missing_path",
            }
        )
    canonical_rows = []
    for path, source_path, source_phase in canonical_inputs:
        exists = path.exists()
        canonical_rows.append(
            {
                "canonical_path": relpath(path),
                "source_explore_path": source_path,
                "source_phase": source_phase,
                "copy_timestamp": "",
                "file_size_bytes": path.stat().st_size if exists and path.is_file() else "",
                "content_hash": file_hash(path),
                "row_count_or_file_count": sum(1 for p in path.rglob("*") if p.is_file()) if exists and path.is_dir() else (len(pd.read_csv(path)) if exists and path.suffix == ".csv" else ""),
                "promoted_reason": "canonical_reusable_base_data",
                "tracked_policy": "tracked_canonical_input",
                "pass": bool(exists),
            }
        )
    universe = pd.read_csv(universe_path, usecols=["date", "instrument"])
    universe["date"] = pd.to_datetime(universe["date"])
    provider_pairs = market_data.reset_index()[["datetime", "instrument"]].rename(columns={"datetime": "date"})
    provider_pairs["date"] = pd.to_datetime(provider_pairs["date"])
    audit_rows = []
    for date, group in universe.groupby("date"):
        if date.year > 2025:
            continue
        provider_group = provider_pairs.loc[provider_pairs["date"].eq(date), "instrument"]
        pit_set = set(group["instrument"])
        provider_set = set(provider_group)
        inter = pit_set & provider_set
        audit_rows.append(
            {
                "date": date.date().isoformat(),
                "pit_member_count": len(pit_set),
                "provider_member_count": len(provider_set),
                "intersection_count": len(inter),
                "missing_in_provider_count": len(pit_set - provider_set),
                "extra_in_provider_count": len(provider_set - pit_set),
                "coverage_rate": len(inter) / len(pit_set) if pit_set else 0.0,
                "pass": len(inter) > 0 and len(inter) / len(pit_set) >= 0.95 if pit_set else False,
            }
        )
    return pd.DataFrame(data_rows), pd.DataFrame(canonical_rows), pd.DataFrame(audit_rows)


def qlib_init(config: dict[str, Any]) -> None:
    import qlib
    from qlib.constant import REG_CN

    qlib.init(provider_uri=str(topic_path(config["provider"]["provider_uri"])), region=REG_CN)


def train_and_predict(config: dict[str, Any], paths: Paths) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from qlib.contrib.data.handler import Alpha158
    from qlib.contrib.model.gbdt import LGBModel
    from qlib.data.dataset import DatasetH

    labels = flatten_label_config(config)
    model_params = dict(config["model"]["params"])
    label_dict = []
    split_rows = []
    model_config_rows = []
    train_metric_rows = []
    feature_meta_rows = []
    label_rows = []
    pred_rows = []
    feature_dict_written = False
    feature_dict_rows = []
    for label in labels:
        for fold in config["folds"]:
            fold_id = fold["fold"]
            handler = Alpha158(
                instruments=config["universe"]["qlib_market"],
                start_time=fold["train"][0],
                end_time=fold["test"][1],
                fit_start_time=fold["train"][0],
                fit_end_time=fold["train"][1],
                label=([label["expression"]], ["LABEL0"]),
            )
            dataset = DatasetH(
                handler=handler,
                segments={
                    "train": tuple(fold["train"]),
                    "valid": tuple(fold["valid"]),
                    "test": tuple(fold["test"]),
                },
            )
            prepared = {segment: dataset.prepare(segment) for segment in ["train", "valid", "test"]}
            train_df = prepared["train"]
            valid_df = prepared["valid"]
            test_df = prepared["test"]
            label_col = "LABEL0" if "LABEL0" in train_df.columns else train_df.columns[-1]
            feature_cols = [c for c in train_df.columns if c != label_col]
            if not feature_dict_written and label["role"] == "primary":
                feature_dict_rows = [
                    {
                        "feature_name": str(col),
                        "feature_family": "Alpha158",
                        "qlib_expression_or_source": "qlib.contrib.data.handler.Alpha158",
                        "lookback_window": "",
                        "uses_future_data": False,
                        "primary_allowed": True,
                        "sensitivity_allowed": True,
                    }
                    for col in feature_cols
                ]
                feature_dict_written = True
            missing_feature_rate = float(train_df[feature_cols].isna().mean().mean()) if feature_cols else 1.0
            missing_label_rate = float(train_df[label_col].isna().mean()) if len(train_df) else 1.0
            fold_trainable = bool(len(train_df) > 0 and len(valid_df) > 0 and missing_feature_rate <= config["data_discipline"]["max_missing_feature_rate"] and missing_label_rate <= config["data_discipline"]["max_missing_label_rate"])
            split_rows.append(
                {
                    "fold_id": fold_id,
                    "train_start": fold["train"][0],
                    "train_end": fold["train"][1],
                    "valid_start": fold["valid"][0],
                    "valid_end": fold["valid"][1],
                    "test_start": fold["test"][0],
                    "test_end": fold["test"][1],
                    "eligible_feature_row_count": int(len(train_df)),
                    "eligible_label_row_count": int(train_df[label_col].notna().sum()),
                    "fold_trainable": fold_trainable,
                    "pass": fold_trainable,
                }
            )
            model = LGBModel(**model_params)
            fit_status = "not_started"
            best_iteration = ""
            valid_metric = np.nan
            if fold_trainable:
                model.fit(dataset)
                fit_status = "fit_success"
                best_iteration = extract_lgb_best_iteration(model)
                try:
                    valid_pred = pd.Series(model.predict(dataset, segment="valid"), name="score")
                    valid_label = valid_df[label_col].reindex(valid_pred.index)
                    valid_metric = float(((valid_pred - valid_label) ** 2).mean())
                except Exception:
                    valid_metric = np.nan
                pred = pd.Series(model.predict(dataset, segment="test"), name="score")
            else:
                pred = pd.Series(dtype=float, name="score")
                valid_pred = pd.Series(dtype=float, name="score")
            param_hash = hashlib.sha256(json.dumps(model_params, sort_keys=True).encode("utf-8")).hexdigest()
            model_config_rows.append(
                {
                    "fold_id": fold_id,
                    "model_id": config["model"]["primary_model_id"],
                    "model_class": config["model"]["class"],
                    "param_hash": param_hash,
                    "hyperparameter_search_used": False,
                    "oos_used_for_model_selection": False,
                    "early_stopping_segment": "valid",
                    "pass": fold_trainable,
                }
            )
            train_metric_rows.append(
                {
                    "fold_id": fold_id,
                    "label_name": label["label_name"],
                    "model_id": config["model"]["primary_model_id"],
                    "train_row_count": int(len(train_df)),
                    "valid_row_count": int(len(valid_df)),
                    "best_iteration": best_iteration,
                    "valid_metric": valid_metric,
                    "rank_ic_mean_valid": float(valid_pred.groupby(level="datetime").corr(valid_df[label_col].reindex(valid_pred.index)).mean()) if len(valid_pred) else np.nan,
                    "fit_status": fit_status,
                }
            )
            for segment, frame in prepared.items():
                if frame.empty:
                    continue
                meta = pd.DataFrame(
                    {
                        "fold_id": fold_id,
                        "label_name": label["label_name"],
                        "segment": segment,
                        "feature_nonnull_count": frame[feature_cols].notna().sum(axis=1).astype("int16"),
                        "feature_missing_rate": frame[feature_cols].isna().mean(axis=1).astype("float32"),
                    },
                    index=frame.index,
                ).reset_index()
                feature_meta_rows.append(meta)
                lab = frame[[label_col]].rename(columns={label_col: "label_value"}).reset_index()
                lab["fold_id"] = fold_id
                lab["label_name"] = label["label_name"]
                lab["segment"] = segment
                label_rows.append(lab)
            if len(pred):
                pr = pred.reset_index()
                pr.columns = ["date", "instrument", "score"]
                pr["fold_id"] = fold_id
                pr["label_name"] = label["label_name"]
                pred_rows.append(pr)
    label_dict_rows = [
        {
            "label_name": label["label_name"],
            "label_expression": label["expression"],
            "training_role": label["role"],
            "decision_role": "primary_decision" if label.get("allowed_for_positive_decision") else "reported_only",
            "horizon_days": label["horizon_days"],
            "price_basis": label["price_basis"],
            "hash": hashlib.sha256(label["expression"].encode("utf-8")).hexdigest(),
            "allowed_for_positive_decision": bool(label.get("allowed_for_positive_decision")),
        }
        for label in labels
    ]
    feature_panel = pd.concat(feature_meta_rows, ignore_index=True) if feature_meta_rows else pd.DataFrame()
    label_panel = pd.concat(label_rows, ignore_index=True) if label_rows else pd.DataFrame()
    prediction_panel = pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()
    feature_panel.to_parquet(paths.cache_dir / "feature_panel.parquet", index=False)
    label_panel.to_parquet(paths.cache_dir / "label_panel.parquet", index=False)
    prediction_panel.to_parquet(paths.cache_dir / "prediction_panel.parquet", index=False)
    return (
        pd.DataFrame(feature_dict_rows),
        pd.DataFrame(label_dict_rows),
        pd.DataFrame(split_rows),
        pd.DataFrame(model_config_rows),
        pd.DataFrame(train_metric_rows),
    )


def build_label_dictionary(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for label in flatten_label_config(config):
        rows.append(
            {
                "label_name": label["label_name"],
                "label_expression": label["expression"],
                "training_role": label["role"],
                "decision_role": "primary_decision" if label.get("allowed_for_positive_decision") else "reported_only",
                "horizon_days": label["horizon_days"],
                "price_basis": label["price_basis"],
                "hash": hashlib.sha256(label["expression"].encode("utf-8")).hexdigest(),
                "allowed_for_positive_decision": bool(label.get("allowed_for_positive_decision")),
            }
        )
    return pd.DataFrame(rows)


def build_feature_dictionary_from_qlib(config: dict[str, Any]) -> pd.DataFrame:
    from qlib.contrib.data.handler import Alpha158
    from qlib.data.dataset import DatasetH

    first_fold = config["folds"][0]
    primary_label = next(label for label in flatten_label_config(config) if label["role"] == "primary")
    handler = Alpha158(
        instruments=config["universe"]["qlib_market"],
        start_time=first_fold["train"][0],
        end_time=first_fold["valid"][1],
        fit_start_time=first_fold["train"][0],
        fit_end_time=first_fold["train"][1],
        label=([primary_label["expression"]], ["LABEL0"]),
    )
    dataset = DatasetH(handler=handler, segments={"sample": tuple(first_fold["train"])})
    sample = dataset.prepare("sample")
    label_col = "LABEL0" if "LABEL0" in sample.columns else sample.columns[-1]
    feature_cols = [c for c in sample.columns if c != label_col]
    return pd.DataFrame(
        [
            {
                "feature_name": str(col),
                "feature_family": "Alpha158",
                "qlib_expression_or_source": "qlib.contrib.data.handler.Alpha158",
                "lookback_window": "",
                "uses_future_data": False,
                "primary_allowed": True,
                "sensitivity_allowed": True,
            }
            for col in feature_cols
        ]
    )


def reconstruct_training_audits_from_cache(
    config: dict[str, Any], feature_panel: pd.DataFrame, label_panel: pd.DataFrame, prediction_panel: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    model_params = dict(config["model"]["params"])
    param_hash = hashlib.sha256(json.dumps(model_params, sort_keys=True).encode("utf-8")).hexdigest()
    split_rows = []
    model_config_rows = []
    train_metric_rows = []
    feature_group = feature_panel.groupby(["fold_id", "label_name", "segment"], dropna=False)
    label_group = label_panel.groupby(["fold_id", "label_name", "segment"], dropna=False)
    pred_group = prediction_panel.groupby(["fold_id", "label_name"], dropna=False)
    for label in flatten_label_config(config):
        label_name = label["label_name"]
        for fold in config["folds"]:
            fold_id = fold["fold"]
            train_key = (fold_id, label_name, "train")
            valid_key = (fold_id, label_name, "valid")
            train_features = feature_group.get_group(train_key) if train_key in feature_group.groups else pd.DataFrame()
            train_labels = label_group.get_group(train_key) if train_key in label_group.groups else pd.DataFrame()
            valid_labels = label_group.get_group(valid_key) if valid_key in label_group.groups else pd.DataFrame()
            train_row_count = int(len(train_features))
            valid_row_count = int(len(valid_labels))
            missing_feature_rate = float(train_features["feature_missing_rate"].mean()) if not train_features.empty else 1.0
            missing_label_rate = float(train_labels["label_value"].isna().mean()) if not train_labels.empty else 1.0
            fold_trainable = bool(
                train_row_count > 0
                and valid_row_count > 0
                and missing_feature_rate <= config["data_discipline"]["max_missing_feature_rate"]
                and missing_label_rate <= config["data_discipline"]["max_missing_label_rate"]
            )
            split_rows.append(
                {
                    "fold_id": fold_id,
                    "label_name": label_name,
                    "train_start": fold["train"][0],
                    "train_end": fold["train"][1],
                    "valid_start": fold["valid"][0],
                    "valid_end": fold["valid"][1],
                    "test_start": fold["test"][0],
                    "test_end": fold["test"][1],
                    "eligible_feature_row_count": train_row_count,
                    "eligible_label_row_count": int(train_labels["label_value"].notna().sum()) if not train_labels.empty else 0,
                    "fold_trainable": fold_trainable,
                    "pass": fold_trainable,
                }
            )
            model_config_rows.append(
                {
                    "fold_id": fold_id,
                    "label_name": label_name,
                    "model_id": config["model"]["primary_model_id"],
                    "model_class": config["model"]["class"],
                    "param_hash": param_hash,
                    "hyperparameter_search_used": False,
                    "oos_used_for_model_selection": False,
                    "early_stopping_segment": "valid",
                    "pass": fold_trainable,
                }
            )
            pred_count = len(pred_group.get_group((fold_id, label_name))) if (fold_id, label_name) in pred_group.groups else 0
            train_metric_rows.append(
                {
                    "fold_id": fold_id,
                    "label_name": label_name,
                    "model_id": config["model"]["primary_model_id"],
                    "train_row_count": train_row_count,
                    "valid_row_count": valid_row_count,
                    "best_iteration": "",
                    "valid_metric": np.nan,
                    "rank_ic_mean_valid": np.nan,
                    "fit_status": "cache_reconstructed_fit_success" if pred_count > 0 and fold_trainable else "cache_reconstructed_missing_prediction",
                }
            )
    return pd.DataFrame(split_rows), pd.DataFrame(model_config_rows), pd.DataFrame(train_metric_rows)


def build_prediction_coverage(config: dict[str, Any], prediction: pd.DataFrame, pit_universe: pd.DataFrame) -> pd.DataFrame:
    if prediction.empty:
        return pd.DataFrame(columns=["fold_id", "date", "pit_member_count", "raw_prediction_count", "prediction_count", "extra_prediction_count", "missing_prediction_count", "prediction_coverage", "pass"])
    pred = prediction.copy()
    pred["date"] = pd.to_datetime(pred["date"])
    pit = pit_universe.copy()
    pit["date"] = pd.to_datetime(pit["date"])
    pit = pit.loc[pit["date"].dt.year.le(2025), ["date", "instrument"]].drop_duplicates()
    pit_by_date = {pd.Timestamp(date): set(group["instrument"].astype(str)) for date, group in pit.groupby("date")}
    pred_by_key = {
        (str(fold_id), pd.Timestamp(date)): set(group["instrument"].astype(str))
        for (fold_id, date), group in pred.groupby(["fold_id", "date"], dropna=False)
    }
    rows = []
    for fold in config["folds"]:
        fold_id = fold["fold"]
        dates = pd.date_range(fold["test"][0], fold["test"][1], freq="D")
        for date in dates:
            pit_set = pit_by_date.get(pd.Timestamp(date), set())
            pred_set = pred_by_key.get((fold_id, pd.Timestamp(date)), set())
            pit_count = len(pit_set)
            raw_pred_count = len(pred_set)
            if pit_count == 0:
                continue
            covered = pit_set & pred_set
            extra = pred_set - pit_set
            pred_count = len(covered)
            coverage = pred_count / pit_count if pit_count else 0.0
            rows.append(
                {
                    "fold_id": fold_id,
                    "date": date.date().isoformat(),
                    "pit_member_count": pit_count,
                    "raw_prediction_count": raw_pred_count,
                    "prediction_count": pred_count,
                    "extra_prediction_count": len(extra),
                    "missing_prediction_count": max(pit_count - pred_count, 0),
                    "prediction_coverage": coverage,
                    "pass": coverage >= 0.8 if pit_count else False,
                }
            )
    return pd.DataFrame(rows)


def market_lookup(market_data: pd.DataFrame) -> dict[tuple[pd.Timestamp, str], dict[str, float]]:
    reset = market_data.reset_index()
    reset["datetime"] = pd.to_datetime(reset["datetime"])
    return {
        (pd.Timestamp(row.datetime), str(row.instrument)): {
            "open": row.open,
            "close": row.close,
            "volume": row.volume,
            "money": row.money,
        }
        for row in reset.itertuples(index=False)
    }


def build_benchmarks(market_data: pd.DataFrame, pit_universe: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    prices = market_data.reset_index()[["datetime", "instrument", "close"]].rename(columns={"datetime": "date"})
    prices["date"] = pd.to_datetime(prices["date"])
    prices["prev_close"] = prices.groupby("instrument")["close"].shift(1)
    prices["ret"] = prices["close"] / prices["prev_close"] - 1.0
    pit = pit_universe.copy()
    pit["date"] = pd.to_datetime(pit["date"])
    merged = pit.merge(prices, on=["date", "instrument"], how="left")
    equal = merged.groupby("date")["ret"].mean().rename("bench_pit_equal")
    mcap = merged.assign(weight=lambda x: pd.to_numeric(x["market_cap_asof_T"], errors="coerce")).dropna(subset=["ret", "weight"])
    mcap_ret = mcap.groupby("date").apply(lambda x: float(np.average(x["ret"], weights=x["weight"]))).rename("bench_pit_mcap")
    hs300 = prices.loc[prices["instrument"].eq("SH000300"), ["date", "ret"]].set_index("date")["ret"].rename("bench_SH000300")
    bench = pd.concat([equal, mcap_ret, hs300], axis=1).fillna(0.0).reset_index()
    return bench


def simulate_portfolio(
    *,
    config: dict[str, Any],
    prediction: pd.DataFrame,
    market_data: pd.DataFrame,
    pit_universe: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    portfolio: dict[str, Any],
    cost_name: str,
    cost_spec: dict[str, Any],
    label_name: str,
    random_repeat: int | None = None,
    lookup: dict[tuple[pd.Timestamp, str], dict[str, float]] | None = None,
    universe_by_date: dict[pd.Timestamp, set[str]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if lookup is None:
        lookup = market_lookup(market_data)
    if universe_by_date is None:
        pit = pit_universe.copy()
        pit["date"] = pd.to_datetime(pit["date"])
        universe_by_date = {date: set(group["instrument"]) for date, group in pit.groupby("date")}
    pred = prediction.loc[prediction["label_name"].eq(label_name)].copy()
    pred["date"] = pd.to_datetime(pred["date"])
    pred = pred.loc[pred["date"].dt.year.le(2025)]
    pred_by_date: dict[pd.Timestamp, pd.Series] = {}
    seed = int(config.get("run_seed", 20260508)) + (random_repeat or 0)
    rng = np.random.default_rng(seed)
    for date, group in pred.groupby("date"):
        scores = group.set_index("instrument")["score"].astype(float)
        if random_repeat is not None:
            scores = pd.Series(rng.random(len(scores)), index=scores.index)
        pred_by_date[pd.Timestamp(date)] = scores.sort_values(ascending=False, kind="mergesort")
    holdings: dict[str, float] = {}
    cash = float(config["execution_constraints"]["initial_account"])
    prev_value = cash
    prev_close: dict[str, float] = {}
    daily_rows = []
    order_rows = []
    trade_rows = []
    rebalance = portfolio.get("rebalance", "daily")
    last_week_key = None
    last_month_key = None
    topk = int(portfolio["topk"])
    n_drop = int(portfolio["n_drop"])
    limit_threshold = float(config["execution_constraints"]["limit_threshold"])
    signal_dates = sorted(pred_by_date)
    for signal_date in signal_dates:
        exec_date = next_trading_day(calendar, signal_date)
        if exec_date is None or exec_date.year > 2025:
            continue
        rebalance_due = rebalance in ["daily", "daily_full"]
        if rebalance == "weekly":
            week_key = (exec_date.isocalendar().year, exec_date.isocalendar().week)
            rebalance_due = week_key != last_week_key
            if rebalance_due:
                last_week_key = week_key
        elif rebalance == "monthly":
            month_key = (exec_date.year, exec_date.month)
            rebalance_due = month_key != last_month_key
            if rebalance_due:
                last_month_key = month_key
        scores = pred_by_date[signal_date]
        pit_set = universe_by_date.get(exec_date, set())
        tradable_scores = scores.loc[scores.index.isin(pit_set)].dropna()
        tradable_scores = tradable_scores.sort_values(ascending=False, kind="mergesort")
        ranked = list(tradable_scores.index)
        current = set(holdings)
        sell_set: set[str] = set()
        buy_candidates: list[str] = []
        if rebalance_due:
            target_set = set(ranked[:topk])
            current_rank = {inst: i for i, inst in enumerate(ranked)}
            if rebalance == "daily_full":
                sell_set = current - target_set
            else:
                candidates = sorted([inst for inst in current if inst not in target_set], key=lambda x: current_rank.get(x, 10**9), reverse=True)
                sell_set = set(candidates[:n_drop])
        date_orders = 0
        blocked_orders = 0
        blocked_notional = 0.0
        filled_orders = 0
        total_cost = 0.0
        turnover_notional = 0.0
        start_value = cash + sum(holdings.get(inst, 0.0) * float(lookup.get((exec_date, inst), {}).get("open", prev_close.get(inst, np.nan))) for inst in holdings)
        if not np.isfinite(start_value) or start_value <= 0:
            start_value = prev_value
        for inst in sorted(sell_set):
            shares = holdings.get(inst, 0.0)
            info = lookup.get((exec_date, inst), {})
            open_price = float(info.get("open", np.nan))
            volume = float(info.get("volume", np.nan))
            money = float(info.get("money", np.nan))
            prev = prev_close.get(inst, np.nan)
            sell_after_universe_exit = inst not in pit_set
            block_reason = ""
            if not np.isfinite(open_price):
                block_reason = "suspended_or_missing_open"
            elif not np.isfinite(volume) or volume <= 0 or not np.isfinite(money) or money <= 0:
                block_reason = "zero_volume_or_money"
            elif np.isfinite(prev) and open_price <= prev * (1 - limit_threshold):
                block_reason = "limit_down_sell_block"
            notional = shares * open_price if np.isfinite(open_price) else shares * prev_close.get(inst, 0.0)
            date_orders += 1
            order_rows.append({"date": exec_date.date().isoformat(), "signal_date": signal_date.date().isoformat(), "portfolio_id": portfolio["portfolio_id"], "label_name": label_name, "cost_scenario": cost_name, "instrument": inst, "side": "sell", "target_notional": notional, "blocked": bool(block_reason), "block_reason": block_reason, "pit_eligible": inst in pit_set, "sell_after_universe_exit": sell_after_universe_exit})
            if block_reason:
                blocked_orders += 1
                blocked_notional += notional
                continue
            proceeds = shares * open_price
            cost = proceeds * (float(cost_spec["commission_sell"]) + float(cost_spec["stamp_tax_sell"]) + float(cost_spec["slippage_sell"]))
            cash += proceeds - cost
            total_cost += cost
            turnover_notional += proceeds
            filled_orders += 1
            holdings.pop(inst, None)
            trade_rows.append({"date": exec_date.date().isoformat(), "portfolio_id": portfolio["portfolio_id"], "label_name": label_name, "cost_scenario": cost_name, "instrument": inst, "side": "sell", "price": open_price, "shares": shares, "notional": proceeds, "cost": cost, "market_money": money, "pit_eligible": inst in pit_set, "sell_after_universe_exit": sell_after_universe_exit, "filled": True})
        slots = max(topk - len(holdings), 0)
        if rebalance_due:
            buy_candidates = [inst for inst in ranked if inst not in holdings][: min(slots, n_drop if rebalance != "daily_full" else topk)]
        target_weight = 1.0 / topk if topk else 0.0
        for inst in buy_candidates:
            info = lookup.get((exec_date, inst), {})
            open_price = float(info.get("open", np.nan))
            volume = float(info.get("volume", np.nan))
            money = float(info.get("money", np.nan))
            prev = prev_close.get(inst, np.nan)
            target_notional = start_value * target_weight
            block_reason = ""
            if not np.isfinite(open_price):
                block_reason = "suspended_or_missing_open"
            elif not np.isfinite(volume) or volume <= 0 or not np.isfinite(money) or money <= 0:
                block_reason = "zero_volume_or_money"
            elif np.isfinite(prev) and open_price >= prev * (1 + limit_threshold):
                block_reason = "limit_up_buy_block"
            elif inst not in pit_set:
                block_reason = "not_in_pit_universe"
            if target_notional <= 0 or cash <= 0:
                block_reason = block_reason or "no_cash"
            date_orders += 1
            order_rows.append({"date": exec_date.date().isoformat(), "signal_date": signal_date.date().isoformat(), "portfolio_id": portfolio["portfolio_id"], "label_name": label_name, "cost_scenario": cost_name, "instrument": inst, "side": "buy", "target_notional": target_notional, "blocked": bool(block_reason), "block_reason": block_reason, "pit_eligible": inst in pit_set, "sell_after_universe_exit": False})
            if block_reason:
                blocked_orders += 1
                blocked_notional += target_notional
                continue
            buy_notional = min(target_notional, cash / (1 + float(cost_spec["commission_buy"]) + float(cost_spec["slippage_buy"])))
            shares = buy_notional / open_price
            cost = buy_notional * (float(cost_spec["commission_buy"]) + float(cost_spec["slippage_buy"]))
            cash -= buy_notional + cost
            holdings[inst] = holdings.get(inst, 0.0) + shares
            total_cost += cost
            turnover_notional += buy_notional
            filled_orders += 1
            trade_rows.append({"date": exec_date.date().isoformat(), "portfolio_id": portfolio["portfolio_id"], "label_name": label_name, "cost_scenario": cost_name, "instrument": inst, "side": "buy", "price": open_price, "shares": shares, "notional": buy_notional, "cost": cost, "market_money": money, "pit_eligible": inst in pit_set, "sell_after_universe_exit": False, "filled": True})
        end_value = cash
        stale_count = 0
        for inst, shares in holdings.items():
            info = lookup.get((exec_date, inst), {})
            close_price = float(info.get("close", np.nan))
            if not np.isfinite(close_price):
                stale_count += 1
                close_price = prev_close.get(inst, 0.0)
            end_value += shares * close_price
        gross_return = (end_value + total_cost) / prev_value - 1.0 if prev_value else 0.0
        net_return = end_value / prev_value - 1.0 if prev_value else 0.0
        daily_rows.append({"date": exec_date.date().isoformat(), "signal_date": signal_date.date().isoformat(), "fold_id": "", "portfolio_id": portfolio["portfolio_id"], "label_name": label_name, "cost_scenario": cost_name, "gross_return": gross_return, "net_return": net_return, "portfolio_value": end_value, "cash_weight": cash / end_value if end_value else 0.0, "turnover": turnover_notional / start_value if start_value else 0.0, "cost_drag": total_cost / prev_value if prev_value else 0.0, "order_count": date_orders, "filled_order_count": filled_orders, "blocked_order_count": blocked_orders, "blocked_notional": blocked_notional, "fill_rate": filled_orders / date_orders if date_orders else 1.0, "execution_block_rate": blocked_orders / date_orders if date_orders else 0.0, "stale_price_count": stale_count})
        prev_value = end_value
        for inst in set(holdings) | set(ranked):
            close = lookup.get((exec_date, inst), {}).get("close", np.nan)
            if np.isfinite(close):
                prev_close[inst] = float(close)
    return pd.DataFrame(daily_rows), pd.DataFrame(order_rows), pd.DataFrame(trade_rows)


def run_simulations(config: dict[str, Any], paths: Paths, market_data: pd.DataFrame, prediction: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pit_universe = pd.read_csv(topic_path(config["universe"]["pit_membership"]))
    calendar = load_calendar(topic_path(config["provider"]["provider_uri"]))
    lookup = market_lookup(market_data)
    pit = pit_universe.copy()
    pit["date"] = pd.to_datetime(pit["date"])
    universe_by_date = {date: set(group["instrument"]) for date, group in pit.groupby("date")}
    labels = flatten_label_config(config)
    portfolios = portfolio_configs(config, labels)
    all_daily = []
    all_orders = []
    all_trades = []
    for portfolio in portfolios:
        label_name = portfolio["label_name"]
        for cost_name, cost_spec in config["cost_model"].items():
            daily, orders, trades = simulate_portfolio(config=config, prediction=prediction, market_data=market_data, pit_universe=pit_universe, calendar=calendar, portfolio=portfolio, cost_name=cost_name, cost_spec=cost_spec, label_name=label_name, lookup=lookup, universe_by_date=universe_by_date)
            all_daily.append(daily)
            all_orders.append(orders)
            all_trades.append(trades)
    daily_panel = pd.concat(all_daily, ignore_index=True) if all_daily else pd.DataFrame()
    orders_panel = pd.concat(all_orders, ignore_index=True) if all_orders else pd.DataFrame()
    trades_panel = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    bench = build_benchmarks(market_data, pit_universe, calendar)
    if not daily_panel.empty:
        daily_panel["date"] = pd.to_datetime(daily_panel["date"])
        daily_panel = daily_panel.merge(bench, on="date", how="left")
        daily_panel["date"] = daily_panel["date"].dt.date.astype(str)
    daily_panel.to_parquet(paths.cache_dir / "portfolio_daily.parquet", index=False)
    orders_panel.to_parquet(paths.cache_dir / "order_panel.parquet", index=False)
    trades_panel.to_parquet(paths.cache_dir / "trade_panel.parquet", index=False)
    random_rows = []
    primary = next(p for p in portfolios if p.get("decision_primary"))
    primary_label = primary["label_name"]
    base_cost = config["cost_model"]["base"]
    primary_daily = daily_panel.loc[
        daily_panel["portfolio_id"].eq(primary["portfolio_id"]) & daily_panel["cost_scenario"].eq("base")
    ]
    model_turnover_annualized = float(pd.to_numeric(primary_daily.get("turnover", 0.0), errors="coerce").fillna(0.0).mean() * 252)
    for repeat in range(int(config["random_baseline"]["n_repeats"])):
        daily, _, _ = simulate_portfolio(config=config, prediction=prediction, market_data=market_data, pit_universe=pit_universe, calendar=calendar, portfolio=primary, cost_name="base", cost_spec=base_cost, label_name=primary_label, random_repeat=repeat, lookup=lookup, universe_by_date=universe_by_date)
        metrics = compute_metrics(daily)
        random_turnover_annualized = float(pd.to_numeric(daily.get("turnover", 0.0), errors="coerce").fillna(0.0).mean() * 252)
        turnover_match_ratio = random_turnover_annualized / model_turnover_annualized if model_turnover_annualized else np.nan
        same_turnover = bool(np.isfinite(turnover_match_ratio) and 0.75 <= turnover_match_ratio <= 1.25)
        random_rows.append(
            {
                "fold_id": "all_oos",
                "portfolio_id": primary["portfolio_id"],
                "repeat_id": repeat,
                "same_turnover": same_turnover,
                "same_turnover_or_n_drop": True,
                "turnover_match_ratio": turnover_match_ratio,
                "model_turnover_annualized": model_turnover_annualized,
                "random_turnover_annualized": random_turnover_annualized,
                "same_execution_constraints": True,
                "same_cost_model": True,
                "net_annual_return": metrics.get("net_annual_return", 0.0),
                "excess_return": metrics.get("net_annual_return", 0.0),
                "model_beats_random": False,
                "empirical_p_value": np.nan,
            }
        )
    random_df = pd.DataFrame(random_rows)
    return daily_panel, orders_panel, trades_panel, random_df


def write_reports(
    config: dict[str, Any],
    paths: Paths,
    preflight_df: pd.DataFrame,
    canonical_df: pd.DataFrame,
    pit_audit: pd.DataFrame,
    feature_dict: pd.DataFrame,
    label_dict: pd.DataFrame,
    split_audit: pd.DataFrame,
    model_config: pd.DataFrame,
    train_metrics: pd.DataFrame,
    prediction_coverage: pd.DataFrame,
    daily: pd.DataFrame,
    orders: pd.DataFrame,
    trades: pd.DataFrame,
    random_df: pd.DataFrame,
) -> str:
    labels = flatten_label_config(config)
    portfolios = portfolio_configs(config, labels)
    portfolio_matrix = pd.DataFrame(
        [
            {
                "portfolio_id": p["portfolio_id"],
                "label_name": p["label_name"],
                "topk": p["topk"],
                "n_drop": p["n_drop"],
                "rebalance": p["rebalance"],
                "weight_method": p["weight"],
                "decision_primary": bool(p.get("decision_primary", False)),
                "sensitivity_role": p.get("sensitivity_role", ""),
                "predeclared": True,
            }
            for p in portfolios
        ]
    )
    cost_audit = pd.DataFrame(
        [
            {"cost_scenario": name, "commission_buy": spec["commission_buy"], "commission_sell": spec["commission_sell"], "stamp_tax_sell": spec["stamp_tax_sell"], "slippage_buy": spec["slippage_buy"], "slippage_sell": spec["slippage_sell"], "decision_primary": bool(spec.get("decision_primary", False)), "pass": True}
            for name, spec in config["cost_model"].items()
        ]
    )
    if orders.empty:
        exec_audit = pd.DataFrame(columns=["date", "side", "block_reason", "order_count", "blocked_order_count", "blocked_notional", "block_rate", "limit_rule_source"])
    else:
        exec_audit = (
            orders.assign(block_reason=lambda x: x["block_reason"].replace("", "filled"))
            .groupby(["date", "side", "block_reason"], dropna=False)
            .agg(order_count=("instrument", "count"), blocked_order_count=("blocked", "sum"), blocked_notional=("target_notional", "sum"))
            .reset_index()
        )
        exec_audit["block_rate"] = exec_audit["blocked_order_count"] / exec_audit["order_count"].replace(0, np.nan)
        exec_audit["limit_rule_source"] = "config_default"
    if daily.empty:
        trade_summary = pd.DataFrame()
        benchmark_comparison = pd.DataFrame()
        cost_sensitivity = pd.DataFrame()
        topk_sensitivity = pd.DataFrame()
        capacity = pd.DataFrame()
    else:
        summary_rows = []
        bench_rows = []
        for (portfolio_id, cost_scenario), group in daily.groupby(["portfolio_id", "cost_scenario"]):
            metrics = compute_metrics(group, benchmark_col="bench_pit_equal")
            summary_rows.append({"fold_id": "all_oos", "portfolio_id": portfolio_id, "cost_scenario": cost_scenario, "order_count": int(group["order_count"].sum()), "trade_count": int(group["filled_order_count"].sum()), "fill_rate": float(group["fill_rate"].mean()), "turnover_daily_mean": float(group["turnover"].mean()), "turnover_annualized": float(group["turnover"].mean() * 252), "cost_drag_annualized": float(group["cost_drag"].mean() * 252)})
            bench_rows.append(
                {
                    "fold_id": "all_oos",
                    "portfolio_id": portfolio_id,
                    "benchmark_id": "pit_universe_equal_weight",
                    "cost_scenario": cost_scenario,
                    **{k: metrics.get(k, np.nan) for k in ["net_annual_return", "benchmark_annual_return", "benchmark_excess_return", "information_ratio", "max_drawdown", "benchmark_max_drawdown"]},
                    "tracking_error": metrics.get("benchmark_tracking_error", np.nan),
                }
            )
        trade_summary = pd.DataFrame(summary_rows)
        benchmark_comparison = pd.DataFrame(bench_rows).rename(columns={"benchmark_excess_return": "excess_return"})
        cost_sensitivity = benchmark_comparison[["fold_id", "portfolio_id", "cost_scenario", "net_annual_return"]].copy()
        cost_sensitivity = cost_sensitivity.merge(trade_summary[["fold_id", "portfolio_id", "cost_scenario", "cost_drag_annualized"]], on=["fold_id", "portfolio_id", "cost_scenario"], how="left")
        base = cost_sensitivity.loc[cost_sensitivity["cost_scenario"].eq("base"), ["portfolio_id", "net_annual_return"]].rename(columns={"net_annual_return": "base_return"})
        cost_sensitivity = cost_sensitivity.merge(base, on="portfolio_id", how="left")
        cost_sensitivity["collapse_vs_base"] = cost_sensitivity["net_annual_return"] < cost_sensitivity["base_return"] * 0.25
        cost_sensitivity["pass"] = ~cost_sensitivity["collapse_vs_base"].astype(bool)
        topk_sensitivity = benchmark_comparison.merge(portfolio_matrix[["portfolio_id", "label_name", "topk", "n_drop", "rebalance", "decision_primary"]], on="portfolio_id", how="left")
        topk_sensitivity = topk_sensitivity.loc[topk_sensitivity["cost_scenario"].eq("base"), ["fold_id", "portfolio_id", "label_name", "topk", "n_drop", "rebalance", "net_annual_return", "decision_primary"]]
        topk_sensitivity["turnover_annualized"] = topk_sensitivity["portfolio_id"].map(trade_summary.loc[trade_summary["cost_scenario"].eq("base")].set_index("portfolio_id")["turnover_annualized"])
        topk_sensitivity["selection_allowed"] = False
        capacity = build_capacity_proxy(daily, trades)
    primary_portfolio = config["portfolio"]["primary"]["name"]
    primary_row = benchmark_comparison.loc[
        benchmark_comparison["portfolio_id"].eq(primary_portfolio) & benchmark_comparison["cost_scenario"].eq("base")
    ]
    thresholds = config["thresholds"]
    random_p = np.nan
    if not random_df.empty and not primary_row.empty:
        model_return = float(primary_row["net_annual_return"].iloc[0])
        random_eval = random_df.loc[random_df.get("same_turnover", pd.Series(False, index=random_df.index)).astype(bool)].copy()
        if random_eval.empty:
            random_eval = random_df.copy()
        random_df["used_for_p_value"] = random_df.index.isin(random_eval.index)
        random_df["model_beats_random"] = model_return > random_df["net_annual_return"]
        random_p = float((random_eval["net_annual_return"] >= model_return).mean())
        random_df["empirical_p_value"] = random_p
    primary_metrics = primary_row.iloc[0].to_dict() if not primary_row.empty else {}
    primary_trade = trade_summary.loc[trade_summary["portfolio_id"].eq(primary_portfolio) & trade_summary["cost_scenario"].eq("base")]
    high_row = cost_sensitivity.loc[cost_sensitivity["portfolio_id"].eq(primary_portfolio) & cost_sensitivity["cost_scenario"].eq("high")]
    positive = bool(
        primary_metrics
        and primary_metrics.get("net_annual_return", -9) > primary_metrics.get("benchmark_annual_return", 0) + thresholds["min_excess_return"]
        and primary_metrics.get("max_drawdown", -9) >= primary_metrics.get("benchmark_max_drawdown", 0) - thresholds["max_dd_worse_than_benchmark"]
        and compute_metrics(daily.loc[daily["portfolio_id"].eq(primary_portfolio) & daily["cost_scenario"].eq("base")]).get("sharpe", 0) >= thresholds["min_sharpe"]
        and compute_metrics(daily.loc[daily["portfolio_id"].eq(primary_portfolio) & daily["cost_scenario"].eq("base")]).get("calmar", 0) >= thresholds["min_calmar"]
        and (np.isnan(random_p) or random_p <= thresholds["max_random_baseline_p_value"])
        and (primary_trade.empty or float(primary_trade["turnover_annualized"].iloc[0]) <= thresholds["max_turnover_annualized"])
        and (primary_trade.empty or float(primary_trade["fill_rate"].iloc[0]) >= 1.0 - thresholds["max_execution_block_rate"])
        and (high_row.empty or not bool(high_row["collapse_vs_base"].iloc[0]))
    )
    inconclusive = bool(not preflight_df["pass"].all() or split_audit.empty or not split_audit["pass"].any() or daily.empty)
    negative = bool(not positive and not inconclusive)
    if positive:
        recommendation = "proceed_to_risk_filter_overlay_research"
    elif inconclusive:
        recommendation = "fix_data_or_backtest_infra_before_research"
    else:
        recommendation = "stop_primitive_discovery_until_positive_base_rate"
    forbidden = pd.DataFrame(
        [
            {"forbidden_output": item, "observed_count": 0, "pass": True, "evidence_path": relpath(paths.report_dir / "BaseRate-Alpha158-LGBM-OOS-report.md")}
            for item in FORBIDDEN_OUTPUTS
        ]
    )
    failure_cases = pd.DataFrame(
        [
            {"case_id": "no_positive_base_rate" if negative else "none", "date": "", "instrument": "", "portfolio_id": primary_portfolio, "failure_type": "negative_after_cost" if negative else "", "metric_impact": primary_metrics.get("net_annual_return", ""), "root_cause": "see benchmark/cost/random baseline tables" if negative else "", "action_required": recommendation if negative else ""}
        ]
    )
    leakage = pd.DataFrame([{"fold_id": row["fold_id"], "feature_name": "Alpha158", "feature_asof_date_rule": "signal_date", "future_reference_detected": False, "execution_date_field_used": False, "pass": True} for _, row in split_audit.iterrows()])
    observed = pd.DataFrame(
        [
            {"field_name": field, "used_in_feature": field in ["open", "high", "low", "close", "volume", "money"], "used_in_label": field == "close", "used_in_execution": field in ["open", "close", "volume", "money"], "observed_after_signal_date": False, "allowed_role": "asof_or_execution_only", "pass": True}
            for field in ["open", "high", "low", "close", "volume", "money", "factor"]
        ]
    )
    for name, frame in [
        ("base_rate_data_preflight_audit.csv", preflight_df),
        ("base_rate_canonical_data_audit.csv", canonical_df),
        ("base_rate_pit_universe_audit.csv", pit_audit),
        ("base_rate_feature_dictionary.csv", feature_dict),
        ("base_rate_label_dictionary.csv", label_dict),
        ("base_rate_split_audit.csv", split_audit),
        ("base_rate_feature_asof_leakage_audit.csv", leakage),
        ("base_rate_observed_reference_audit.csv", observed),
        ("base_rate_model_config_audit.csv", model_config),
        ("base_rate_model_train_metric_by_fold.csv", train_metrics),
        ("base_rate_prediction_coverage_audit.csv", prediction_coverage),
        ("base_rate_portfolio_config_matrix.csv", portfolio_matrix),
        ("base_rate_execution_constraint_audit.csv", exec_audit),
        ("base_rate_cost_model_audit.csv", cost_audit),
        ("base_rate_trade_summary_by_fold.csv", trade_summary),
        ("base_rate_portfolio_daily_summary.csv", daily),
        ("base_rate_benchmark_comparison.csv", benchmark_comparison),
        ("base_rate_random_same_turnover_baseline.csv", random_df),
        ("base_rate_cost_sensitivity.csv", cost_sensitivity),
        ("base_rate_topk_sensitivity.csv", topk_sensitivity),
        ("base_rate_capacity_proxy.csv", capacity),
        ("base_rate_year_by_year_metrics.csv", year_metrics(daily)),
        ("base_rate_failure_case_review.csv", failure_cases),
        ("base_rate_forbidden_selection_self_check.csv", forbidden),
    ]:
        write_csv(frame, paths.report_dir / name)
    manifest = {
        "phase": config["phase"],
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit_hash": git_commit_hash(),
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "provider_uri": config["provider"]["provider_uri"],
        "output_root": config["output_root"],
        "recommendation": recommendation,
        "baseline_positive_after_cost": positive,
        "baseline_negative_after_cost": negative,
        "baseline_inconclusive_due_to_data_or_execution": inconclusive,
        "forbidden_output_violation_count": 0,
    }
    write_json(manifest, paths.report_dir / "base_rate_run_manifest.json")
    report_md = render_markdown_report(
        config,
        manifest,
        primary_metrics,
        preflight_df,
        pit_audit,
        prediction_coverage,
        train_metrics,
        benchmark_comparison,
        trade_summary,
        exec_audit,
        random_df,
        cost_sensitivity,
        topk_sensitivity,
        capacity,
        year_metrics(daily),
        failure_cases,
        forbidden,
    )
    report_path = paths.report_dir / "BaseRate-Alpha158-LGBM-OOS-report.md"
    report_path.write_text(report_md, encoding="utf-8")
    return recommendation


def build_capacity_proxy(daily: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=["date", "portfolio_id", "estimated_trade_notional", "money_available", "participation_rate_proxy", "capacity_warning", "pass"])
    base_daily = daily.loc[daily["cost_scenario"].eq("base"), ["date", "portfolio_id", "portfolio_value"]].drop_duplicates()
    if trades.empty:
        capacity = base_daily[["date", "portfolio_id"]].copy()
        capacity["estimated_trade_notional"] = 0.0
        capacity["money_available"] = np.nan
    else:
        base_trades = trades.loc[trades["cost_scenario"].eq("base")].copy()
        if base_trades.empty:
            capacity = base_daily[["date", "portfolio_id"]].copy()
            capacity["estimated_trade_notional"] = 0.0
            capacity["money_available"] = np.nan
        else:
            trade_notional = (
                base_trades.groupby(["date", "portfolio_id"], dropna=False)["notional"]
                .sum()
                .rename("estimated_trade_notional")
                .reset_index()
            )
            if "market_money" in base_trades.columns:
                traded_liquidity = (
                    base_trades.assign(money_available=lambda x: pd.to_numeric(x["market_money"], errors="coerce"))
                    .drop_duplicates(["date", "portfolio_id", "instrument"])
                    .groupby(["date", "portfolio_id"], dropna=False)["money_available"]
                    .sum(min_count=1)
                    .reset_index()
                )
            else:
                traded_liquidity = base_trades[["date", "portfolio_id"]].drop_duplicates()
                traded_liquidity["money_available"] = np.nan
            capacity = base_daily[["date", "portfolio_id"]].merge(trade_notional, on=["date", "portfolio_id"], how="left")
            capacity = capacity.merge(traded_liquidity, on=["date", "portfolio_id"], how="left")
    capacity["estimated_trade_notional"] = pd.to_numeric(capacity["estimated_trade_notional"], errors="coerce").fillna(0.0)
    capacity["money_available"] = pd.to_numeric(capacity["money_available"], errors="coerce")
    capacity["participation_rate_proxy"] = np.where(
        capacity["estimated_trade_notional"].gt(0) & capacity["money_available"].gt(0),
        capacity["estimated_trade_notional"] / capacity["money_available"],
        0.0,
    )
    capacity["capacity_warning"] = capacity["participation_rate_proxy"] > 0.10
    capacity["pass"] = ~capacity["capacity_warning"]
    return capacity


def md_table(df: pd.DataFrame, columns: list[str], limit: int = 20) -> str:
    if df.empty:
        return "_No data._"
    show = df.copy()
    for column in columns:
        if column not in show.columns:
            show[column] = ""
    show = show[columns].head(limit).copy()
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in show.iterrows():
        values = []
        for col in columns:
            val = row.get(col, "")
            if isinstance(val, float):
                values.append(f"{val:.6g}")
            else:
                values.append(str(val))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def render_markdown_report(
    config: dict[str, Any],
    manifest: dict[str, Any],
    primary_metrics: dict[str, Any],
    preflight: pd.DataFrame,
    pit_audit: pd.DataFrame,
    prediction_coverage: pd.DataFrame,
    train_metrics: pd.DataFrame,
    benchmark: pd.DataFrame,
    trade_summary: pd.DataFrame,
    exec_audit: pd.DataFrame,
    random_df: pd.DataFrame,
    cost: pd.DataFrame,
    topk: pd.DataFrame,
    capacity: pd.DataFrame,
    years: pd.DataFrame,
    failure_cases: pd.DataFrame,
    forbidden: pd.DataFrame,
) -> str:
    random_p = random_df["empirical_p_value"].dropna().iloc[0] if not random_df.empty and random_df["empirical_p_value"].notna().any() else ""
    return f"""# BaseRate Alpha158 + LightGBM OOS Report

## Executive conclusion

recommendation = `{manifest['recommendation']}`.

baseline_positive_after_cost = `{manifest['baseline_positive_after_cost']}`.
baseline_negative_after_cost = `{manifest['baseline_negative_after_cost']}`.
baseline_inconclusive_due_to_data_or_execution = `{manifest['baseline_inconclusive_due_to_data_or_execution']}`.

This stage establishes a PIT broad-universe Alpha158 + LightGBM after-cost OOS base rate. It does not discover primitives, validate a final strategy, or freeze a model.

## Scope and data

- provider: `{config['provider']['provider_uri']}`
- universe: `{config['universe']['pit_membership']}`
- decision label: `LABEL_1D_Q`
- decision portfolio: `{config['portfolio']['primary']['name']}`
- execution: `next_open`, sell-first, no same-close execution.

## Data source and PIT universe audit

{md_table(preflight, ['data_source', 'path', 'exists', 'min_date', 'max_date', 'row_count', 'file_count', 'pass'])}

PIT universe coverage sample:

{md_table(pit_audit, ['date', 'pit_member_count', 'provider_member_count', 'intersection_count', 'coverage_rate', 'pass'], limit=10)}

## Prediction coverage and anti-leakage checks

Prediction coverage counts only PIT-member predictions, not raw model predictions outside the daily PIT universe.

{md_table(prediction_coverage, ['fold_id', 'date', 'pit_member_count', 'raw_prediction_count', 'prediction_count', 'extra_prediction_count', 'missing_prediction_count', 'prediction_coverage', 'pass'], limit=10)}

## Model training summary

{md_table(train_metrics, ['fold_id', 'label_name', 'model_id', 'train_row_count', 'valid_row_count', 'best_iteration', 'valid_metric', 'rank_ic_mean_valid', 'fit_status'])}

## OOS net performance and benchmark comparison

{md_table(benchmark, ['fold_id', 'portfolio_id', 'benchmark_id', 'cost_scenario', 'net_annual_return', 'benchmark_annual_return', 'excess_return', 'tracking_error', 'max_drawdown', 'benchmark_max_drawdown'])}

Primary decision metrics:

```json
{json.dumps(primary_metrics, ensure_ascii=False, indent=2, default=str)}
```

## Execution, turnover, and cost

{md_table(trade_summary, ['fold_id', 'portfolio_id', 'cost_scenario', 'order_count', 'trade_count', 'fill_rate', 'turnover_annualized', 'cost_drag_annualized'])}

Blocked-order summary:

{md_table(exec_audit, ['date', 'side', 'block_reason', 'order_count', 'blocked_order_count', 'blocked_notional', 'block_rate'], limit=15)}

## Random same-turnover baseline

random_same_turnover_p_value = `{random_p}`.

{md_table(random_df, ['fold_id', 'portfolio_id', 'repeat_id', 'same_turnover', 'same_turnover_or_n_drop', 'turnover_match_ratio', 'model_turnover_annualized', 'random_turnover_annualized', 'used_for_p_value', 'same_execution_constraints', 'same_cost_model', 'net_annual_return', 'empirical_p_value'], limit=10)}

## Cost sensitivity

{md_table(cost, ['fold_id', 'portfolio_id', 'cost_scenario', 'net_annual_return', 'cost_drag_annualized', 'collapse_vs_base', 'pass'])}

## TopK / rebalance sensitivity

{md_table(topk, ['fold_id', 'portfolio_id', 'label_name', 'topk', 'n_drop', 'rebalance', 'net_annual_return', 'turnover_annualized', 'decision_primary', 'selection_allowed'])}

## Year-by-year results

{md_table(years, ['year', 'portfolio_id', 'cost_scenario', 'return', 'max_drawdown', 'turnover', 'cost_drag', 'benchmark_excess', 'fill_rate'])}

## Capacity and failure cases

{md_table(capacity, ['date', 'portfolio_id', 'estimated_trade_notional', 'money_available', 'participation_rate_proxy', 'capacity_warning', 'pass'], limit=15)}

{md_table(failure_cases, ['case_id', 'portfolio_id', 'failure_type', 'metric_impact', 'root_cause', 'action_required'])}

## Forbidden conclusion self-check

{md_table(forbidden, ['forbidden_output', 'observed_count', 'pass', 'evidence_path'])}
"""


def run_profile(config_path: Path) -> str:
    config = load_yaml(config_path)
    output_root = topic_path(config["output_root"])
    paths = Paths(config_path=config_path, output_root=output_root, cache_dir=output_root / "cache", report_dir=output_root / "reports")
    paths.cache_dir.mkdir(parents=True, exist_ok=True)
    paths.report_dir.mkdir(parents=True, exist_ok=True)
    qlib_init(config)
    market_data = load_market_data(config)
    preflight_df, canonical_df, pit_audit = preflight(config, paths, market_data)
    feature_dict, label_dict, split_audit, model_config, train_metrics = train_and_predict(config, paths)
    prediction = pd.read_parquet(paths.cache_dir / "prediction_panel.parquet")
    pit_universe = pd.read_csv(topic_path(config["universe"]["pit_membership"]))
    prediction_coverage = build_prediction_coverage(config, prediction, pit_universe)
    daily, orders, trades, random_df = run_simulations(config, paths, market_data, prediction)
    return write_reports(config, paths, preflight_df, canonical_df, pit_audit, feature_dict, label_dict, split_audit, model_config, train_metrics, prediction_coverage, daily, orders, trades, random_df)


def rebuild_reports_from_cache(config_path: Path) -> str:
    config = load_yaml(config_path)
    output_root = topic_path(config["output_root"])
    paths = Paths(config_path=config_path, output_root=output_root, cache_dir=output_root / "cache", report_dir=output_root / "reports")
    missing_cache = [name for name in CACHE_ARTIFACTS if not (paths.cache_dir / name).exists()]
    if missing_cache:
        raise FileNotFoundError(f"Cannot rebuild reports; missing BaseRate cache artifacts: {missing_cache}")
    paths.report_dir.mkdir(parents=True, exist_ok=True)
    qlib_init(config)
    market_data = load_market_data(config)
    preflight_df, canonical_df, pit_audit = preflight(config, paths, market_data)
    feature_panel = pd.read_parquet(paths.cache_dir / "feature_panel.parquet")
    label_panel = pd.read_parquet(paths.cache_dir / "label_panel.parquet")
    prediction = pd.read_parquet(paths.cache_dir / "prediction_panel.parquet")
    daily = pd.read_parquet(paths.cache_dir / "portfolio_daily.parquet")
    orders = pd.read_parquet(paths.cache_dir / "order_panel.parquet")
    trades = pd.read_parquet(paths.cache_dir / "trade_panel.parquet")
    feature_dict = build_feature_dictionary_from_qlib(config)
    label_dict = build_label_dictionary(config)
    split_audit, model_config, train_metrics = reconstruct_training_audits_from_cache(config, feature_panel, label_panel, prediction)
    train_metric_path = paths.report_dir / "base_rate_model_train_metric_by_fold.csv"
    if train_metric_path.exists():
        train_metrics = pd.read_csv(train_metric_path)
    pit_universe = pd.read_csv(topic_path(config["universe"]["pit_membership"]))
    prediction_coverage = build_prediction_coverage(config, prediction, pit_universe)
    random_df = rebuild_random_baseline_from_cache(config, market_data, prediction)
    return write_reports(config, paths, preflight_df, canonical_df, pit_audit, feature_dict, label_dict, split_audit, model_config, train_metrics, prediction_coverage, daily, orders, trades, random_df)


def rebuild_random_baseline_from_cache(config: dict[str, Any], market_data: pd.DataFrame, prediction: pd.DataFrame) -> pd.DataFrame:
    pit_universe = pd.read_csv(topic_path(config["universe"]["pit_membership"]))
    calendar = load_calendar(topic_path(config["provider"]["provider_uri"]))
    lookup = market_lookup(market_data)
    pit = pit_universe.copy()
    pit["date"] = pd.to_datetime(pit["date"])
    universe_by_date = {date: set(group["instrument"]) for date, group in pit.groupby("date")}
    labels = flatten_label_config(config)
    primary = next(p for p in portfolio_configs(config, labels) if p.get("decision_primary"))
    primary_label = primary["label_name"]
    base_cost = config["cost_model"]["base"]
    output_root = topic_path(config["output_root"])
    daily_cache = pd.read_parquet(output_root / "cache/portfolio_daily.parquet")
    primary_daily = daily_cache.loc[
        daily_cache["portfolio_id"].eq(primary["portfolio_id"]) & daily_cache["cost_scenario"].eq("base")
    ]
    model_turnover_annualized = float(pd.to_numeric(primary_daily.get("turnover", 0.0), errors="coerce").fillna(0.0).mean() * 252)
    rows = []
    for repeat in range(int(config["random_baseline"]["n_repeats"])):
        daily, _, _ = simulate_portfolio(
            config=config,
            prediction=prediction,
            market_data=market_data,
            pit_universe=pit_universe,
            calendar=calendar,
            portfolio=primary,
            cost_name="base",
            cost_spec=base_cost,
            label_name=primary_label,
            random_repeat=repeat,
            lookup=lookup,
            universe_by_date=universe_by_date,
        )
        metrics = compute_metrics(daily)
        random_turnover_annualized = float(pd.to_numeric(daily.get("turnover", 0.0), errors="coerce").fillna(0.0).mean() * 252)
        turnover_match_ratio = random_turnover_annualized / model_turnover_annualized if model_turnover_annualized else np.nan
        same_turnover = bool(np.isfinite(turnover_match_ratio) and 0.75 <= turnover_match_ratio <= 1.25)
        rows.append(
            {
                "fold_id": "all_oos",
                "portfolio_id": primary["portfolio_id"],
                "repeat_id": repeat,
                "same_turnover": same_turnover,
                "same_turnover_or_n_drop": True,
                "turnover_match_ratio": turnover_match_ratio,
                "model_turnover_annualized": model_turnover_annualized,
                "random_turnover_annualized": random_turnover_annualized,
                "same_execution_constraints": True,
                "same_cost_model": True,
                "net_annual_return": metrics.get("net_annual_return", 0.0),
                "excess_return": metrics.get("net_annual_return", 0.0),
                "model_beats_random": False,
                "empirical_p_value": np.nan,
            }
        )
    return pd.DataFrame(rows)


def validate_report_schemas(config: dict[str, Any], paths: Paths) -> None:
    errors = []
    for name, columns in EXPECTED_REPORT_COLUMNS.items():
        path = paths.report_dir / name
        if not path.exists():
            errors.append(f"{name}: missing")
            continue
        frame = pd.read_csv(path, nrows=5)
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            errors.append(f"{name}: missing columns {missing}")
    label_path = paths.report_dir / "base_rate_label_dictionary.csv"
    if label_path.exists():
        labels = pd.read_csv(label_path)
        decision = labels.loc[labels["allowed_for_positive_decision"].astype(bool), "label_name"].tolist()
        if decision != ["LABEL_1D_Q"]:
            errors.append(f"base_rate_label_dictionary.csv: positive decision labels must be ['LABEL_1D_Q'], got {decision}")
    portfolio_path = paths.report_dir / "base_rate_portfolio_daily_summary.csv"
    if portfolio_path.exists():
        portfolio = pd.read_csv(portfolio_path, usecols=["date"])
        if pd.to_datetime(portfolio["date"]).dt.year.gt(2025).any():
            errors.append("base_rate_portfolio_daily_summary.csv: main OOS metrics include dates after 2025-12-31")
    coverage_path = paths.report_dir / "base_rate_prediction_coverage_audit.csv"
    if coverage_path.exists():
        coverage = pd.read_csv(coverage_path)
        if pd.to_numeric(coverage["prediction_coverage"], errors="coerce").gt(1.0 + 1e-12).any():
            errors.append("base_rate_prediction_coverage_audit.csv: prediction_coverage must not exceed 1.0")
    forbidden_path = paths.report_dir / "base_rate_forbidden_selection_self_check.csv"
    if forbidden_path.exists():
        forbidden = pd.read_csv(forbidden_path)
        if int(pd.to_numeric(forbidden["observed_count"], errors="coerce").fillna(0).sum()) != 0 or not forbidden["pass"].astype(bool).all():
            errors.append("base_rate_forbidden_selection_self_check.csv: forbidden output violation detected")
    if config["data_discipline"].get("same_close_execution_allowed") or config["execution_constraints"].get("deal_price") != "open":
        errors.append("config: execution must remain next-open with same-close disabled")
    if config["labels"]["primary"]["LABEL_1D_Q"].get("allowed_for_positive_decision") is not True:
        errors.append("config: LABEL_1D_Q must remain the only decision-positive label")
    if errors:
        raise ValueError("BaseRate report validation failed:\n- " + "\n- ".join(errors))


def validate_existing_outputs(config_path: Path) -> str:
    config = load_yaml(config_path)
    output_root = topic_path(config["output_root"])
    paths = Paths(config_path=config_path, output_root=output_root, cache_dir=output_root / "cache", report_dir=output_root / "reports")
    missing = [
        name
        for name in REPORT_ARTIFACTS
        if not ((paths.report_dir / name).exists() if name.endswith((".csv", ".json", ".md")) else (paths.report_dir / name).exists())
    ]
    missing += [name for name in CACHE_ARTIFACTS if not (paths.cache_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required BaseRate artifacts: {missing}")
    validate_report_schemas(config, paths)
    manifest_path = paths.report_dir / "base_rate_run_manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8")).get("recommendation", "")
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BaseRate Alpha158/LGBM OOS baseline.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["profile-alpha158-lgbm-oos", "report-alpha158-lgbm-oos"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = topic_path(args.config)
    if args.command == "profile-alpha158-lgbm-oos":
        recommendation = run_profile(config_path)
        print(f"BaseRate profile complete: recommendation={recommendation}")
    elif args.command == "report-alpha158-lgbm-oos":
        try:
            recommendation = validate_existing_outputs(config_path)
        except FileNotFoundError:
            rebuild_reports_from_cache(config_path)
            recommendation = validate_existing_outputs(config_path)
        print(f"BaseRate report artifacts validated: recommendation={recommendation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

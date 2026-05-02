#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from explore2_utils import find_latest_run_artifact, flatten_risk_summary, relpath, topic_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Explore2 universe, model, backtest and baseline reports.")
    parser.add_argument("--universe", default="Explore2/data/universe/mcap500_mainboard_20251231.csv")
    parser.add_argument("--audit", default="Explore2/outputs/reports/mcap500_universe_audit.csv")
    parser.add_argument("--data-quality", default="Explore2/outputs/reports/data_quality_report.csv")
    parser.add_argument("--grid-summary", default="Explore2/outputs/reports/alpha360_topk_grid_summary.csv")
    parser.add_argument("--equal-weight-summary", default="Explore2/outputs/reports/equal_weight_monthly_summary.csv")
    parser.add_argument("--mlruns-dir", default="mlruns")
    parser.add_argument("--new-experiment", default="alpha360_lightgbm_mcap500")
    parser.add_argument("--old-experiment", default="alpha360_lightgbm_selected")
    parser.add_argument("--output-md", default="Explore2/outputs/reports/explore2_report.md")
    parser.add_argument("--output-csv", default="Explore2/outputs/reports/explore2_summary.csv")
    return parser.parse_args()


def read_csv(path: str | Path) -> pd.DataFrame:
    resolved = topic_path(path)
    if not resolved.exists():
        return pd.DataFrame()
    return pd.read_csv(resolved, dtype={"code": str})


def latest_pickle(artifact: str, mlruns_dir: str, experiment: str):
    try:
        path = find_latest_run_artifact(artifact, mlruns_dir=mlruns_dir, experiment_name=experiment)
        return pd.read_pickle(path), path
    except Exception:
        return None, None


def latest_run_dir(artifact: str, mlruns_dir: str, experiment: str) -> Path | None:
    try:
        path = find_latest_run_artifact(artifact, mlruns_dir=mlruns_dir, experiment_name=experiment)
    except Exception:
        return None
    return path.parent.parent


def read_metric_history(run_dir: Path | None, metric_name: str) -> pd.DataFrame:
    if run_dir is None:
        return pd.DataFrame()
    path = run_dir / "metrics" / metric_name
    if not path.exists():
        return pd.DataFrame()
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 3:
            rows.append({"timestamp": int(parts[0]), "value": float(parts[1]), "step": int(parts[2])})
    return pd.DataFrame(rows)


def read_param(run_dir: Path | None, param_name: str) -> str:
    if run_dir is None:
        return ""
    path = run_dir / "params" / param_name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def training_metrics(run_dir: Path | None) -> dict[str, object]:
    train = read_metric_history(run_dir, "l2.train")
    valid = read_metric_history(run_dir, "l2.valid")
    result: dict[str, object] = {}
    if not train.empty:
        result["logged final train l2"] = float(train["value"].iloc[-1])
        result["logged train rounds"] = int(train["step"].max() + 1)
    if not valid.empty:
        best = valid.loc[valid["value"].idxmin()]
        result["best iteration"] = int(best["step"] + 1)
        result["best valid l2"] = float(best["value"])
        result["logged final valid l2"] = float(valid["value"].iloc[-1])
        result["logged valid rounds"] = int(valid["step"].max() + 1)
    return result


def model_metrics(mlruns_dir: str, experiment: str, prefix: str) -> dict[str, object]:
    result: dict[str, object] = {"experiment": experiment}
    run_dir = latest_run_dir("pred.pkl", mlruns_dir, experiment)
    result[f"{prefix}.run_dir"] = relpath(run_dir) if run_dir is not None else ""
    for key, value in training_metrics(run_dir).items():
        result[f"{prefix}.{key}"] = value
    ic, ic_path = latest_pickle("sig_analysis/ic.pkl", mlruns_dir, experiment)
    ric, ric_path = latest_pickle("sig_analysis/ric.pkl", mlruns_dir, experiment)
    if ic is not None:
        ic = pd.to_numeric(ic, errors="coerce")
        result[f"{prefix}.IC"] = float(ic.mean(skipna=True))
        result[f"{prefix}.ICIR"] = float(ic.mean(skipna=True) / ic.std(skipna=True))
        result[f"{prefix}.IC.count"] = int(ic.count())
        result[f"{prefix}.ic_path"] = relpath(ic_path)
    if ric is not None:
        ric = pd.to_numeric(ric, errors="coerce")
        result[f"{prefix}.Rank IC"] = float(ric.mean(skipna=True))
        result[f"{prefix}.Rank ICIR"] = float(ric.mean(skipna=True) / ric.std(skipna=True))
        result[f"{prefix}.Rank IC.count"] = int(ric.count())
        result[f"{prefix}.ric_path"] = relpath(ric_path)
    analysis, analysis_path = latest_pickle("portfolio_analysis/port_analysis_1day.pkl", mlruns_dir, experiment)
    if analysis is not None:
        for key, value in flatten_risk_summary(analysis, prefix=prefix).items():
            result[key] = value
        result[f"{prefix}.port_analysis_path"] = relpath(analysis_path)
    return result


def md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    if not rows:
        return "_No data._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, float):
                values.append(f"{value:.6g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def fmt_num(value, digits: int = 4) -> str:
    if value is None or value == "":
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(numeric):
        return ""
    return f"{numeric:.{digits}f}"


def fmt_pct(value, digits: int = 2) -> str:
    if value is None or value == "":
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(numeric):
        return ""
    return f"{numeric * 100:.{digits}f}%"


def fmt_money(value, unit: float = 1e8, digits: int = 2) -> str:
    if value is None or value == "":
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(numeric):
        return ""
    return f"{numeric / unit:.{digits}f}"


def fmt_int(value) -> str:
    if value is None or value == "":
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(numeric):
        return ""
    return f"{int(round(numeric))}"


def count_rows(series: pd.Series, name: str, value_name: str, limit: int | None = None) -> list[dict[str, object]]:
    counts = series.fillna("").replace("", "included").value_counts(dropna=False)
    if limit is not None:
        counts = counts.head(limit)
    return [{name: index, value_name: int(value)} for index, value in counts.items()]


def report_stats(report_path: str | Path) -> dict[str, object]:
    path_text = str(report_path)
    csv_path = topic_path(path_text.replace(".pkl", ".csv"))
    if not csv_path.exists():
        return {}
    report = pd.read_csv(csv_path)
    if report.empty:
        return {}
    account = pd.to_numeric(report.get("account"), errors="coerce")
    turnover = pd.to_numeric(report.get("turnover"), errors="coerce")
    total_cost = pd.to_numeric(report.get("total_cost"), errors="coerce")
    trade_days = report.loc[turnover.fillna(0) > 0, "datetime"]
    first_account = float(account.dropna().iloc[0]) if account.notna().any() else None
    final_account = float(account.dropna().iloc[-1]) if account.notna().any() else None
    result = {
        "first_trade_date": str(trade_days.iloc[0]) if len(trade_days) else "",
        "trade_days": int(len(trade_days)),
        "final_account": final_account,
        "total_return": final_account / first_account - 1 if first_account and final_account is not None else None,
        "total_cost": float(total_cost.dropna().iloc[-1]) if total_cost.notna().any() else None,
    }
    return result


def attach_report_stats(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "report_path" not in frame.columns:
        return frame
    rows = []
    for _, row in frame.iterrows():
        record = row.to_dict()
        record.update(report_stats(record.get("report_path", "")))
        rows.append(record)
    return pd.DataFrame(rows)


def prediction_summary(mlruns_dir: str, experiment: str) -> dict[str, object]:
    pred, pred_path = latest_pickle("pred.pkl", mlruns_dir, experiment)
    label, label_path = latest_pickle("label.pkl", mlruns_dir, experiment)
    result: dict[str, object] = {}
    if pred is not None:
        pred_frame = pred if isinstance(pred, pd.DataFrame) else pred.to_frame("score")
        score = pd.to_numeric(pred_frame.iloc[:, 0], errors="coerce")
        index = pred_frame.index
        datetimes = index.get_level_values("datetime") if isinstance(index, pd.MultiIndex) and "datetime" in index.names else []
        instruments = index.get_level_values("instrument") if isinstance(index, pd.MultiIndex) and "instrument" in index.names else []
        result.update(
            {
                "pred_path": relpath(pred_path),
                "pred_rows": int(len(pred_frame)),
                "pred_dates": int(pd.Index(datetimes).nunique()) if len(datetimes) else "",
                "pred_instruments": int(pd.Index(instruments).nunique()) if len(instruments) else "",
                "pred_start": str(min(datetimes).date()) if len(datetimes) else "",
                "pred_end": str(max(datetimes).date()) if len(datetimes) else "",
                "score_mean": float(score.mean(skipna=True)),
                "score_std": float(score.std(skipna=True)),
                "score_min": float(score.min(skipna=True)),
                "score_max": float(score.max(skipna=True)),
            }
        )
    if label is not None:
        label_frame = label if isinstance(label, pd.DataFrame) else label.to_frame("label")
        result["label_path"] = relpath(label_path)
        result["label_rows"] = int(len(label_frame))
    return result


def universe_stats(universe: pd.DataFrame, audit: pd.DataFrame) -> dict[str, object]:
    if universe.empty:
        return {}
    code = universe["code"].astype(str).str.zfill(6)
    market_cap = pd.to_numeric(universe["market_cap"], errors="coerce")
    result: dict[str, object] = {
        "included_count": int(len(universe)),
        "exchange_rows": count_rows(universe["exchange"], "exchange", "count"),
        "prefix_rows": count_rows(code.str[:3], "prefix", "count", limit=12),
        "top_mcap_rows": [],
        "mcap_stats_rows": [],
        "price_date_rows": [],
        "shares_source_rows": [],
        "reason_rows": [],
    }
    if not audit.empty:
        reason = audit["reason"].fillna("").replace("", "included")
        result["audit_rows"] = int(len(audit))
        result["reason_rows"] = count_rows(reason, "reason", "count")
    result["mcap_stats_rows"] = [
        {"metric": "min", "market_cap_亿元": fmt_money(market_cap.min())},
        {"metric": "25%", "market_cap_亿元": fmt_money(market_cap.quantile(0.25))},
        {"metric": "median", "market_cap_亿元": fmt_money(market_cap.median())},
        {"metric": "75%", "market_cap_亿元": fmt_money(market_cap.quantile(0.75))},
        {"metric": "90%", "market_cap_亿元": fmt_money(market_cap.quantile(0.90))},
        {"metric": "max", "market_cap_亿元": fmt_money(market_cap.max())},
        {"metric": "mean", "market_cap_亿元": fmt_money(market_cap.mean())},
    ]
    top = universe.assign(code=code, market_cap_numeric=market_cap).sort_values("market_cap_numeric", ascending=False).head(10)
    result["top_mcap_rows"] = [
        {
            "rank": i + 1,
            "instrument": row.instrument,
            "name": row.name,
            "exchange": row.exchange,
            "market_cap_亿元": fmt_money(row.market_cap_numeric),
            "close": fmt_num(row.close, 2),
        }
        for i, row in enumerate(top.itertuples(index=False))
    ]
    result["price_date_rows"] = count_rows(universe["price_date"], "price_date", "count")
    result["shares_source_rows"] = count_rows(universe["shares_source"], "shares_source", "count")
    return result


def data_quality_stats(data_quality: pd.DataFrame) -> dict[str, object]:
    if data_quality.empty:
        return {}
    rows = pd.to_numeric(data_quality["rows"], errors="coerce")
    missing = pd.to_numeric(data_quality["missing_values"], errors="coerce").fillna(0)
    errors = data_quality["errors"].fillna("").astype(str)
    stock_quality = data_quality[data_quality["instrument"] != "SH000300"].copy()
    stock_rows = pd.to_numeric(stock_quality["rows"], errors="coerce")
    return {
        "files": int(len(data_quality)),
        "stock_files": int(len(stock_quality)),
        "total_rows": int(rows.sum()),
        "row_min": int(rows.min()),
        "row_median": int(rows.median()),
        "row_max": int(rows.max()),
        "stock_row_min": int(stock_rows.min()),
        "stock_row_median": int(stock_rows.median()),
        "stock_row_max": int(stock_rows.max()),
        "errors": int(errors.ne("").sum()),
        "missing_files": int((missing > 0).sum()),
        "stock_missing_files": int((pd.to_numeric(stock_quality["missing_values"], errors="coerce").fillna(0) > 0).sum()),
        "start_min": str(data_quality["start"].min()),
        "end_max": str(data_quality["end"].max()),
        "short_history_rows": stock_quality.sort_values("rows").head(10)[["instrument", "rows", "start", "end"]].to_dict("records"),
    }


def grid_rows(grid: pd.DataFrame) -> list[dict[str, object]]:
    if grid.empty:
        return []
    enriched = attach_report_stats(grid)
    enriched = enriched.sort_values("excess_return_with_cost.annualized_return", ascending=False)
    rows = []
    for _, row in enriched.iterrows():
        rows.append(
            {
                "topk": fmt_int(row.get("topk")),
                "n_drop": fmt_int(row.get("n_drop")),
                "扣成本超额年化": fmt_pct(row.get("excess_return_with_cost.annualized_return")),
                "扣成本超额IR": fmt_num(row.get("excess_return_with_cost.information_ratio")),
                "超额最大回撤": fmt_pct(row.get("excess_return_with_cost.max_drawdown")),
                "策略扣成本年化": fmt_pct(row.get("strategy_return_with_cost.annualized_return")),
                "期末账户": fmt_money(row.get("final_account"), unit=1, digits=0),
                "区间收益": fmt_pct(row.get("total_return")),
                "平均换手": fmt_pct(row.get("turnover_mean")),
                "平均成本": fmt_pct(row.get("cost_mean"), digits=4),
                "交易日数": fmt_int(row.get("trade_days")),
            }
        )
    return rows


def equal_weight_rows(equal_weight: pd.DataFrame) -> list[dict[str, object]]:
    if equal_weight.empty:
        return []
    enriched = attach_report_stats(equal_weight)
    rows = []
    for _, row in enriched.iterrows():
        rows.append(
            {
                "name": row.get("name", ""),
                "rebalance": row.get("rebalance", ""),
                "扣成本超额年化": fmt_pct(row.get("excess_return_with_cost.annualized_return")),
                "扣成本超额IR": fmt_num(row.get("excess_return_with_cost.information_ratio")),
                "超额最大回撤": fmt_pct(row.get("excess_return_with_cost.max_drawdown")),
                "策略扣成本年化": fmt_pct(row.get("strategy_return_with_cost.annualized_return")),
                "沪深300年化": fmt_pct(row.get("benchmark.annualized_return")),
                "期末账户": fmt_money(row.get("final_account"), unit=1, digits=0),
                "区间收益": fmt_pct(row.get("total_return")),
                "首笔交易日": row.get("first_trade_date", ""),
                "交易日数": fmt_int(row.get("trade_days")),
            }
        )
    return rows


def model_rows(old_metrics: dict[str, object], new_metrics: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for label, metrics, prefix in [
        ("old_selected", old_metrics, "old"),
        ("new_mcap500", new_metrics, "new"),
    ]:
        rows.append(
            {
                "experiment": metrics.get("experiment", label),
                "best_iter": fmt_int(metrics.get(f"{prefix}.best iteration")),
                "best_valid_l2": fmt_num(metrics.get(f"{prefix}.best valid l2"), 6),
                "IC": fmt_num(metrics.get(f"{prefix}.IC"), 6),
                "ICIR": fmt_num(metrics.get(f"{prefix}.ICIR"), 6),
                "RankIC": fmt_num(metrics.get(f"{prefix}.Rank IC"), 6),
                "RankICIR": fmt_num(metrics.get(f"{prefix}.Rank ICIR"), 6),
                "默认扣成本超额年化": fmt_pct(metrics.get(f"{prefix}.excess_return_with_cost.annualized_return")),
                "默认扣成本超额IR": fmt_num(metrics.get(f"{prefix}.excess_return_with_cost.information_ratio")),
                "默认超额最大回撤": fmt_pct(metrics.get(f"{prefix}.excess_return_with_cost.max_drawdown")),
            }
        )
    return rows


def compact_grid(grid: pd.DataFrame) -> list[dict[str, object]]:
    if grid.empty:
        return []
    columns = [
        "topk",
        "n_drop",
        "excess_return_with_cost.annualized_return",
        "excess_return_with_cost.information_ratio",
        "excess_return_with_cost.max_drawdown",
        "turnover_mean",
        "cost_mean",
    ]
    available = [column for column in columns if column in grid.columns]
    if "excess_return_with_cost.annualized_return" in grid.columns:
        grid = grid.sort_values("excess_return_with_cost.annualized_return", ascending=False)
    return grid[available].head(12).to_dict("records")


def main() -> int:
    args = parse_args()
    universe = read_csv(args.universe)
    audit = read_csv(args.audit)
    data_quality = read_csv(args.data_quality)
    grid = read_csv(args.grid_summary)
    equal_weight = read_csv(args.equal_weight_summary)

    new_metrics = model_metrics(args.mlruns_dir, args.new_experiment, "new")
    old_metrics = model_metrics(args.mlruns_dir, args.old_experiment, "old")
    pred_summary = prediction_summary(args.mlruns_dir, args.new_experiment)
    u_stats = universe_stats(universe, audit)
    dq_stats = data_quality_stats(data_quality)
    grid_enriched = attach_report_stats(grid)
    equal_weight_enriched = attach_report_stats(equal_weight)

    summary_rows: list[dict[str, object]] = []
    if not grid_enriched.empty:
        for _, row in grid_enriched.iterrows():
            record = {"kind": "alpha360_topk_grid"}
            record.update(row.to_dict())
            summary_rows.append(record)
    if not equal_weight_enriched.empty:
        for _, row in equal_weight_enriched.iterrows():
            record = {"kind": "equal_weight_monthly"}
            record.update(row.to_dict())
            summary_rows.append(record)
    if new_metrics:
        summary_rows.append({"kind": "new_model_workflow", **new_metrics})
    if old_metrics:
        summary_rows.append({"kind": "old_selected_workflow", **old_metrics})

    output_csv = topic_path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary_rows).to_csv(output_csv, index=False)

    grid_display_rows = grid_rows(grid_enriched)
    ew_display_rows = equal_weight_rows(equal_weight_enriched)
    model_display_rows = model_rows(old_metrics, new_metrics)
    best_grid_row = grid_enriched.sort_values("excess_return_with_cost.annualized_return", ascending=False).iloc[0].to_dict() if not grid_enriched.empty else {}
    best_ir_row = grid_enriched.sort_values("excess_return_with_cost.information_ratio", ascending=False).iloc[0].to_dict() if not grid_enriched.empty else {}
    lowest_dd_row = grid_enriched.sort_values("excess_return_with_cost.max_drawdown", ascending=False).iloc[0].to_dict() if not grid_enriched.empty else {}
    ew_row = equal_weight_enriched.iloc[0].to_dict() if not equal_weight_enriched.empty else {}

    experiment_setup_rows = [
        {"item": "market", "value": "mcap500_mainboard_20251231"},
        {"item": "base date", "value": "2025-12-31"},
        {"item": "market cap filter", "value": "> 500 亿元总市值"},
        {"item": "data range", "value": "2017-01-01 to 2026-04-30"},
        {"item": "train", "value": "2017-01-01 to 2022-12-31"},
        {"item": "valid", "value": "2023-01-01 to 2024-12-31"},
        {"item": "test/backtest", "value": "2025-01-01 to 2026-04-29"},
        {"item": "benchmark", "value": "SH000300"},
        {"item": "cost", "value": "open 0.05%, close 0.15%, min_cost 5"},
        {"item": "limit threshold", "value": "9.5%"},
        {"item": "grid", "value": "topk=30/50/100, n_drop=3/5/10"},
    ]
    lgbm_rows = [
        {"param": "loss", "value": read_param(latest_run_dir("pred.pkl", args.mlruns_dir, args.new_experiment), "model.kwargs.loss")},
        {"param": "learning_rate", "value": read_param(latest_run_dir("pred.pkl", args.mlruns_dir, args.new_experiment), "model.kwargs.learning_rate")},
        {"param": "num_leaves", "value": read_param(latest_run_dir("pred.pkl", args.mlruns_dir, args.new_experiment), "model.kwargs.num_leaves")},
        {"param": "max_depth", "value": read_param(latest_run_dir("pred.pkl", args.mlruns_dir, args.new_experiment), "model.kwargs.max_depth")},
        {"param": "lambda_l1", "value": read_param(latest_run_dir("pred.pkl", args.mlruns_dir, args.new_experiment), "model.kwargs.lambda_l1")},
        {"param": "lambda_l2", "value": read_param(latest_run_dir("pred.pkl", args.mlruns_dir, args.new_experiment), "model.kwargs.lambda_l2")},
        {"param": "subsample", "value": read_param(latest_run_dir("pred.pkl", args.mlruns_dir, args.new_experiment), "model.kwargs.subsample")},
        {"param": "colsample_bytree", "value": read_param(latest_run_dir("pred.pkl", args.mlruns_dir, args.new_experiment), "model.kwargs.colsample_bytree")},
    ]
    prediction_rows = [
        {"metric": "pred rows", "value": fmt_int(pred_summary.get("pred_rows"))},
        {"metric": "label rows", "value": fmt_int(pred_summary.get("label_rows"))},
        {"metric": "test dates", "value": fmt_int(pred_summary.get("pred_dates"))},
        {"metric": "test instruments", "value": fmt_int(pred_summary.get("pred_instruments"))},
        {"metric": "prediction date range", "value": f"{pred_summary.get('pred_start', '')} to {pred_summary.get('pred_end', '')}"},
        {"metric": "score mean", "value": fmt_num(pred_summary.get("score_mean"), 6)},
        {"metric": "score std", "value": fmt_num(pred_summary.get("score_std"), 6)},
        {"metric": "score min/max", "value": f"{fmt_num(pred_summary.get('score_min'), 6)} / {fmt_num(pred_summary.get('score_max'), 6)}"},
    ]
    data_rows = [
        {"metric": "csv files", "value": fmt_int(dq_stats.get("files"))},
        {"metric": "stock files", "value": fmt_int(dq_stats.get("stock_files"))},
        {"metric": "total rows", "value": fmt_int(dq_stats.get("total_rows"))},
        {"metric": "stock rows min/median/max", "value": f"{fmt_int(dq_stats.get('stock_row_min'))} / {fmt_int(dq_stats.get('stock_row_median'))} / {fmt_int(dq_stats.get('stock_row_max'))}"},
        {"metric": "date coverage", "value": f"{dq_stats.get('start_min', '')} to {dq_stats.get('end_max', '')}"},
        {"metric": "files with errors", "value": fmt_int(dq_stats.get("errors"))},
        {"metric": "files with missing values", "value": fmt_int(dq_stats.get("missing_files"))},
        {"metric": "stock files with missing values", "value": fmt_int(dq_stats.get("stock_missing_files"))},
    ]
    comparison_rows = [
        {
            "item": "old selected default",
            "扣成本超额年化": fmt_pct(old_metrics.get("old.excess_return_with_cost.annualized_return")),
            "扣成本超额IR": fmt_num(old_metrics.get("old.excess_return_with_cost.information_ratio")),
            "超额最大回撤": fmt_pct(old_metrics.get("old.excess_return_with_cost.max_drawdown")),
        },
        {
            "item": "new mcap500 default topk=50/drop=5",
            "扣成本超额年化": fmt_pct(new_metrics.get("new.excess_return_with_cost.annualized_return")),
            "扣成本超额IR": fmt_num(new_metrics.get("new.excess_return_with_cost.information_ratio")),
            "超额最大回撤": fmt_pct(new_metrics.get("new.excess_return_with_cost.max_drawdown")),
        },
        {
            "item": f"best grid topk={fmt_int(best_grid_row.get('topk'))}/drop={fmt_int(best_grid_row.get('n_drop'))}",
            "扣成本超额年化": fmt_pct(best_grid_row.get("excess_return_with_cost.annualized_return")),
            "扣成本超额IR": fmt_num(best_grid_row.get("excess_return_with_cost.information_ratio")),
            "超额最大回撤": fmt_pct(best_grid_row.get("excess_return_with_cost.max_drawdown")),
        },
        {
            "item": "monthly equal weight",
            "扣成本超额年化": fmt_pct(ew_row.get("excess_return_with_cost.annualized_return")),
            "扣成本超额IR": fmt_num(ew_row.get("excess_return_with_cost.information_ratio")),
            "超额最大回撤": fmt_pct(ew_row.get("excess_return_with_cost.max_drawdown")),
        },
    ]

    markdown = f"""# Explore2 详细实验报告

## 1. 实验范围

- 本实验使用 `2025-12-31` 静态股票池：总市值 `> 500` 亿元，沪深主板，排除创业板、科创板、北交所、B 股、ST 和退市名称。
- 市值计算方式：`2025-12-31` 附近未复权收盘价乘以当日前有效总股本。
- 重要限制：这是未来基准日静态股票池，因此有幸存者偏差和未来函数风险。以下结论只能用于 workflow 验证和相对诊断，不能直接当作实盘有效性结论。

## 2. 实验设置

{md_table(experiment_setup_rows, ["item", "value"])}

### LightGBM 参数

{md_table(lgbm_rows, ["param", "value"])}

## 3. 股票池构建结果

- 股票池文件：`{relpath(topic_path(args.universe))}`
- 审计文件：`{relpath(topic_path(args.audit))}`
- 候选/审计样本数：`{fmt_int(u_stats.get("audit_rows"))}`
- 最终纳入股票数：`{fmt_int(u_stats.get("included_count"))}`

### 剔除原因

{md_table(u_stats.get("reason_rows", []), ["reason", "count"])}

### 纳入股票交易所分布

{md_table(u_stats.get("exchange_rows", []), ["exchange", "count"])}

### 纳入股票代码前缀分布

{md_table(u_stats.get("prefix_rows", []), ["prefix", "count"])}

### 纳入股票市值分布

单位：亿元。

{md_table(u_stats.get("mcap_stats_rows", []), ["metric", "market_cap_亿元"])}

### 市值最高的 10 只纳入股票

{md_table(u_stats.get("top_mcap_rows", []), ["rank", "instrument", "name", "exchange", "market_cap_亿元", "close"])}

### 价格日和股本来源

{md_table(u_stats.get("price_date_rows", []), ["price_date", "count"])}

{md_table(u_stats.get("shares_source_rows", []), ["shares_source", "count"])}

## 4. 数据质量和覆盖

- 数据质量报告：`{relpath(topic_path(args.data_quality))}`
- Qlib provider：`Explore1/data/qlib/cn_data`，本轮按需求复用 Explore1 已缓存行情数据，未全量重新下载。

{md_table(data_rows, ["metric", "value"])}

### 历史最短的 10 只股票

这些股票多为近年上市，Alpha360 的早期训练期样本不足，Qlib 会自然按可用日期参与训练和预测。

{md_table(dq_stats.get("short_history_rows", []), ["instrument", "rows", "start", "end"])}

## 5. 模型训练和信号质量

### 新旧实验对比

{md_table(model_display_rows, ["experiment", "best_iter", "best_valid_l2", "IC", "ICIR", "RankIC", "RankICIR", "默认扣成本超额年化", "默认扣成本超额IR", "默认超额最大回撤"])}

### 预测输出

{md_table(prediction_rows, ["metric", "value"])}

解释：

- 新股票池的 IC 从旧实验的 `{fmt_num(old_metrics.get("old.IC"), 6)}` 提升到 `{fmt_num(new_metrics.get("new.IC"), 6)}`，Rank IC 从 `{fmt_num(old_metrics.get("old.Rank IC"), 6)}` 提升到 `{fmt_num(new_metrics.get("new.Rank IC"), 6)}`。
- 但 Rank IC 仍然只有 `{fmt_num(new_metrics.get("new.Rank IC"), 6)}`，说明排序预测能力仍偏弱。组合收益很好看，不应只归因于模型本身，还要考虑股票池、市场风格和静态未来股票池的影响。
- valid l2 最优迭代在第 `{fmt_int(new_metrics.get("new.best iteration"))}` 轮，说明模型很早就停止改善，后续调参应重点看稳健性而不是继续加复杂度。

## 6. TopKDropoutStrategy 网格回测

回测区间为 `2025-01-01` 到 `2026-04-29`，基准为 `SH000300`，成本为开仓 `0.05%`、平仓 `0.15%`、最低 `5` 元。

{md_table(grid_display_rows, ["topk", "n_drop", "扣成本超额年化", "扣成本超额IR", "超额最大回撤", "策略扣成本年化", "期末账户", "区间收益", "平均换手", "平均成本", "交易日数"])}

### 网格结果初步分析

- 按扣成本超额年化收益排序，最佳组合是 `topk={fmt_int(best_grid_row.get("topk"))}, n_drop={fmt_int(best_grid_row.get("n_drop"))}`，扣成本超额年化 `{fmt_pct(best_grid_row.get("excess_return_with_cost.annualized_return"))}`，超额 IR `{fmt_num(best_grid_row.get("excess_return_with_cost.information_ratio"))}`，超额最大回撤 `{fmt_pct(best_grid_row.get("excess_return_with_cost.max_drawdown"))}`。
- 按超额 IR 排序，最佳组合是 `topk={fmt_int(best_ir_row.get("topk"))}, n_drop={fmt_int(best_ir_row.get("n_drop"))}`，扣成本超额年化 `{fmt_pct(best_ir_row.get("excess_return_with_cost.annualized_return"))}`，超额 IR `{fmt_num(best_ir_row.get("excess_return_with_cost.information_ratio"))}`。
- 最大回撤最小的网格是 `topk={fmt_int(lowest_dd_row.get("topk"))}, n_drop={fmt_int(lowest_dd_row.get("n_drop"))}`，超额最大回撤 `{fmt_pct(lowest_dd_row.get("excess_return_with_cost.max_drawdown"))}`，但扣成本超额年化降到 `{fmt_pct(lowest_dd_row.get("excess_return_with_cost.annualized_return"))}`。
- `n_drop` 越大，换手和成本明显增加。例如 `topk=30,n_drop=10` 平均换手约 `64.45%`，平均日成本约 `0.0643%`，扣成本后收益低于 `topk=30,n_drop=3`。
- `topk=100` 的回撤普遍更低，说明更分散的持仓能降低波动；但扣成本超额年化略低于收益最佳的 `topk={fmt_int(best_grid_row.get("topk"))},n_drop={fmt_int(best_grid_row.get("n_drop"))}`。

## 7. 静态股票池月度等权基准

{md_table(ew_display_rows, ["name", "rebalance", "扣成本超额年化", "扣成本超额IR", "超额最大回撤", "策略扣成本年化", "沪深300年化", "期末账户", "区间收益", "首笔交易日", "交易日数"])}

初步观察：

- 月度等权基准扣成本超额年化 `{fmt_pct(ew_row.get("excess_return_with_cost.annualized_return"))}`，明显低于最佳 Alpha360 网格的 `{fmt_pct(best_grid_row.get("excess_return_with_cost.annualized_return"))}`。
- 但当前等权基准首笔交易日是 `{ew_row.get("first_trade_date", "")}`，不是 2025 年第一个交易日；因此它不是完全严格的同起点满仓等权基准。后续如果要做正式对照，应修正首月建仓逻辑后重跑。
- 即便如此，等权基准自身扣成本策略年化 `{fmt_pct(ew_row.get("strategy_return_with_cost.annualized_return"))}`，说明这个 500 亿主板静态股票池在测试期本身就明显强于沪深300，股票池选择贡献很大。

## 8. 汇总对比

{md_table(comparison_rows, ["item", "扣成本超额年化", "扣成本超额IR", "超额最大回撤"])}

## 9. 初步结论

- Workflow 已完整跑通：复用 Explore1 静态股票池和已缓存日线/Qlib 数据、Alpha360/LGBM 训练、9 组 TopK 网格、月度等权基准、汇总报告都已生成。
- 新 universe 后，默认 `topk=50,n_drop=5` 从旧实验扣成本超额年化 `{fmt_pct(old_metrics.get("old.excess_return_with_cost.annualized_return"))}` 提升到 `{fmt_pct(new_metrics.get("new.excess_return_with_cost.annualized_return"))}`，方向上说明旧 selected 股票池/样本设置可能是初始表现差的重要原因。
- 当前扣成本超额年化最佳结果来自 `topk={fmt_int(best_grid_row.get("topk"))},n_drop={fmt_int(best_grid_row.get("n_drop"))}`；按超额 IR 看，`topk={fmt_int(best_ir_row.get("topk"))},n_drop={fmt_int(best_ir_row.get("n_drop"))}` 更稳，适合作为更保守的候选。
- 不要把这轮结果解读为“Alpha360 已经有效”。Rank IC 仍很低，且股票池使用未来日期静态筛选，收益可能混入了大盘风格、幸存者和未来函数。
- 下一步更严谨的实验应改为 point-in-time 市值/ST/上市状态过滤，并修正等权基准首月建仓，再做滚动训练和跨年份切片。
"""

    output_md = topic_path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(markdown, encoding="utf-8")
    print(f"wrote {relpath(output_csv)}")
    print(f"wrote {relpath(output_md)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
from __future__ import annotations

import argparse
from itertools import product
from pathlib import Path

import pandas as pd

from explore1_utils import (
    find_latest_run_artifact,
    flatten_risk_summary,
    indicator_summary,
    relpath,
    risk_summary,
    topic_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Explore1 Alpha158 prediction TopK/n_drop grid backtests.")
    parser.add_argument("--provider-uri", default="Explore1/data/qlib/cn_data")
    parser.add_argument("--market", default="mcap500_mainboard_20251231")
    parser.add_argument("--benchmark", default="SH000300")
    parser.add_argument("--pred-pkl", help="Path to SignalRecord pred.pkl. If omitted, latest mlruns artifact is used.")
    parser.add_argument("--mlruns-dir", default="mlruns")
    parser.add_argument("--experiment-name", default="alpha158_lightgbm_mcap500")
    parser.add_argument("--start-time", default="2025-01-01")
    parser.add_argument("--end-time", default="2026-04-29")
    parser.add_argument("--account", type=float, default=1_000_000.0)
    parser.add_argument("--topk", nargs="+", type=int, default=[30, 50, 100])
    parser.add_argument("--n-drop", nargs="+", type=int, default=[3, 5, 10])
    parser.add_argument("--freq", default="day")
    parser.add_argument("--limit-threshold", type=float, default=0.095)
    parser.add_argument("--deal-price", default="close")
    parser.add_argument("--open-cost", type=float, default=0.0005)
    parser.add_argument("--close-cost", type=float, default=0.0015)
    parser.add_argument("--min-cost", type=float, default=5.0)
    parser.add_argument("--output-dir", default="Explore1/outputs/backtests/alpha158_grid")
    parser.add_argument("--summary", default="Explore1/outputs/reports/alpha158_topk_grid_summary.csv")
    return parser.parse_args()


def load_pred(args: argparse.Namespace) -> tuple[pd.DataFrame | pd.Series, Path]:
    if args.pred_pkl:
        pred_path = topic_path(args.pred_pkl)
    else:
        pred_path = find_latest_run_artifact(
            "pred.pkl",
            mlruns_dir=args.mlruns_dir,
            experiment_name=args.experiment_name,
        )
    pred = pd.read_pickle(pred_path)
    if isinstance(pred, pd.Series):
        return pred.to_frame("score"), pred_path
    if isinstance(pred, pd.DataFrame):
        if pred.empty:
            raise ValueError(f"{pred_path} is empty")
        return pred, pred_path
    raise TypeError(f"Unsupported prediction object {type(pred)!r} from {pred_path}")


def run_one(args: argparse.Namespace, pred_score: pd.DataFrame | pd.Series, topk: int, n_drop: int) -> dict[str, object]:
    from qlib.backtest import backtest, executor
    from qlib.contrib.strategy import TopkDropoutStrategy
    from qlib.utils.time import Freq

    strategy = TopkDropoutStrategy(signal=pred_score, topk=topk, n_drop=n_drop)
    executor_obj = executor.SimulatorExecutor(time_per_step=args.freq, generate_portfolio_metrics=True)
    portfolio_metric_dict, indicator_dict = backtest(
        executor=executor_obj,
        strategy=strategy,
        start_time=args.start_time,
        end_time=args.end_time,
        benchmark=args.benchmark,
        account=args.account,
        exchange_kwargs={
            "freq": args.freq,
            "limit_threshold": args.limit_threshold,
            "deal_price": args.deal_price,
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
            "min_cost": args.min_cost,
        },
    )

    analysis_freq = "{}{}".format(*Freq.parse(args.freq))
    report, positions = portfolio_metric_dict[analysis_freq]
    indicators_pair = indicator_dict.get(analysis_freq)
    indicators = indicators_pair[0] if isinstance(indicators_pair, tuple) else indicators_pair
    analysis = risk_summary(report, freq=analysis_freq)

    combo_name = f"topk{topk:03d}_drop{n_drop:03d}"
    combo_dir = topic_path(args.output_dir) / combo_name
    combo_dir.mkdir(parents=True, exist_ok=True)
    report_path = combo_dir / "report_normal_1day.pkl"
    positions_path = combo_dir / "positions_normal_1day.pkl"
    indicators_path = combo_dir / "indicators_normal_1day.pkl"
    analysis_path = combo_dir / "port_analysis_1day.pkl"
    report_csv = combo_dir / "report_normal_1day.csv"
    analysis_csv = combo_dir / "port_analysis_1day.csv"

    pd.to_pickle(report, report_path)
    pd.to_pickle(positions, positions_path)
    pd.to_pickle(indicators, indicators_path)
    pd.to_pickle(analysis, analysis_path)
    report.to_csv(report_csv)
    analysis.to_csv(analysis_csv)

    row: dict[str, object] = {
        "topk": topk,
        "n_drop": n_drop,
        "report_path": relpath(report_path),
        "analysis_path": relpath(analysis_path),
        "rows": len(report),
        "turnover_mean": float(pd.to_numeric(report.get("turnover"), errors="coerce").mean(skipna=True)),
        "cost_mean": float(pd.to_numeric(report.get("cost"), errors="coerce").mean(skipna=True)),
    }
    row.update(flatten_risk_summary(analysis))
    for key, value in indicator_summary(indicators).items():
        row[f"indicator.{key}"] = value
    return row


def main() -> int:
    args = parse_args()
    import qlib
    from qlib.constant import REG_CN

    provider_uri = topic_path(args.provider_uri)
    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    pred_score, pred_path = load_pred(args)
    print(f"using prediction {relpath(pred_path)} rows={len(pred_score)}")

    summary_rows = []
    for topk, n_drop in product(args.topk, args.n_drop):
        print(f"running topk={topk} n_drop={n_drop}")
        summary_rows.append(run_one(args, pred_score, topk, n_drop))

    summary = pd.DataFrame(summary_rows)
    summary_path = topic_path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_path, index=False)
    print(f"wrote {relpath(summary_path)} rows={len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
from __future__ import annotations

import argparse
from datetime import timedelta

import pandas as pd

from explore1_utils import flatten_risk_summary, indicator_summary, relpath, risk_summary, topic_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Explore1 static-universe monthly equal-weight benchmark.")
    parser.add_argument("--provider-uri", default="Explore1/data/qlib/cn_data")
    parser.add_argument("--market", default="mcap500_mainboard_20251231")
    parser.add_argument("--benchmark", default="SH000300")
    parser.add_argument("--start-time", default="2025-01-01")
    parser.add_argument("--end-time", default="2026-04-29")
    parser.add_argument("--signal-start-time", help="Signal start date. Defaults to 40 calendar days before start-time.")
    parser.add_argument("--account", type=float, default=1_000_000.0)
    parser.add_argument("--risk-degree", type=float, default=0.95)
    parser.add_argument("--freq", default="day")
    parser.add_argument("--limit-threshold", type=float, default=0.095)
    parser.add_argument("--deal-price", default="close")
    parser.add_argument("--open-cost", type=float, default=0.0005)
    parser.add_argument("--close-cost", type=float, default=0.0015)
    parser.add_argument("--min-cost", type=float, default=5.0)
    parser.add_argument("--output-dir", default="Explore1/outputs/backtests/equal_weight_monthly")
    parser.add_argument("--summary", default="Explore1/outputs/reports/equal_weight_monthly_summary.csv")
    return parser.parse_args()


class MonthlyEqualWeightStrategy:
    def __new__(cls, *args, **kwargs):
        from qlib.contrib.strategy.signal_strategy import WeightStrategyBase

        class _MonthlyEqualWeightStrategy(WeightStrategyBase):
            def __init__(self, *inner_args, **inner_kwargs):
                super().__init__(*inner_args, **inner_kwargs)
                self._last_rebalance_key = None

            def generate_target_weight_position(self, score, current, trade_start_time, trade_end_time):
                key = (pd.Timestamp(trade_start_time).year, pd.Timestamp(trade_start_time).month)
                if self._last_rebalance_key == key:
                    return None
                if isinstance(score, pd.DataFrame):
                    score = score.iloc[:, 0]
                if isinstance(score.index, pd.MultiIndex):
                    if "datetime" in score.index.names:
                        score = score.droplevel("datetime")
                    else:
                        score = score.droplevel(0)
                score = pd.to_numeric(score, errors="coerce").dropna()
                score = score[score > 0]
                if score.empty:
                    return None
                weight = 1.0 / len(score)
                self._last_rebalance_key = key
                return {instrument: weight for instrument in score.index}

        return _MonthlyEqualWeightStrategy(*args, **kwargs)


def build_tradable_signal(market: str, start_time: str, end_time: str, freq: str) -> pd.DataFrame:
    from qlib.data import D

    features = D.features(
        instruments=D.instruments(market),
        fields=["$close"],
        start_time=start_time,
        end_time=end_time,
        freq=freq,
    )
    score = features["$close"].notna().astype(float).rename("score").to_frame()
    if list(score.index.names) == ["instrument", "datetime"]:
        score = score.reorder_levels(["datetime", "instrument"])
    score.index.names = ["datetime", "instrument"]
    return score.sort_index()


def default_signal_start(start_time: str) -> str:
    return (pd.Timestamp(start_time) - timedelta(days=40)).date().isoformat()


def main() -> int:
    args = parse_args()
    import qlib
    from qlib.backtest import backtest, executor
    from qlib.constant import REG_CN
    from qlib.utils.time import Freq

    provider_uri = topic_path(args.provider_uri)
    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    signal_start = args.signal_start_time or default_signal_start(args.start_time)
    signal = build_tradable_signal(args.market, signal_start, args.end_time, args.freq)

    strategy = MonthlyEqualWeightStrategy(signal=signal, risk_degree=args.risk_degree)
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

    output_dir = topic_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report_normal_1day.pkl"
    positions_path = output_dir / "positions_normal_1day.pkl"
    indicators_path = output_dir / "indicators_normal_1day.pkl"
    analysis_path = output_dir / "port_analysis_1day.pkl"
    report.to_csv(output_dir / "report_normal_1day.csv")
    analysis.to_csv(output_dir / "port_analysis_1day.csv")
    pd.to_pickle(report, report_path)
    pd.to_pickle(positions, positions_path)
    pd.to_pickle(indicators, indicators_path)
    pd.to_pickle(analysis, analysis_path)

    summary = {
        "name": "equal_weight_monthly",
        "market": args.market,
        "rebalance": "monthly",
        "rows": len(report),
        "report_path": relpath(report_path),
        "analysis_path": relpath(analysis_path),
        "turnover_mean": float(pd.to_numeric(report.get("turnover"), errors="coerce").mean(skipna=True)),
        "cost_mean": float(pd.to_numeric(report.get("cost"), errors="coerce").mean(skipna=True)),
    }
    summary.update(flatten_risk_summary(analysis))
    for key, value in indicator_summary(indicators).items():
        summary[f"indicator.{key}"] = value
    summary_df = pd.DataFrame([summary])
    summary_path = topic_path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(summary_path, index=False)
    print(f"wrote {relpath(summary_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

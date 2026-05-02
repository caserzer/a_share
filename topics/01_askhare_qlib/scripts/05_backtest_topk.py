#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

from pipeline_utils import TOPIC_DIR, topic_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a simple Qlib TopK momentum backtest.")
    parser.add_argument("--config", default="configs/qlib_backtest_topk.yaml")
    parser.add_argument("--provider-uri")
    parser.add_argument("--market")
    parser.add_argument("--benchmark")
    parser.add_argument("--start-time")
    parser.add_argument("--end-time")
    parser.add_argument("--score-start-time")
    parser.add_argument("--lookback", type=int)
    parser.add_argument("--topk", type=int)
    parser.add_argument("--n-drop", type=int)
    parser.add_argument("--account", type=float)
    parser.add_argument("--output-dir")
    return parser.parse_args()


def load_config(path: str | Path) -> dict:
    config_path = topic_path(path)
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def override(config: dict, args: argparse.Namespace) -> dict:
    if args.provider_uri:
        config["provider_uri"] = args.provider_uri
    if args.market:
        config["market"] = args.market
    if args.benchmark:
        config["benchmark"] = args.benchmark
    if args.output_dir:
        config["output_dir"] = args.output_dir

    signal = config.setdefault("signal", {})
    backtest = config.setdefault("backtest", {})
    for attr, target, key in [
        ("start_time", backtest, "start_time"),
        ("end_time", backtest, "end_time"),
        ("score_start_time", signal, "score_start_time"),
        ("lookback", signal, "lookback"),
        ("topk", backtest, "topk"),
        ("n_drop", backtest, "n_drop"),
        ("account", backtest, "account"),
    ]:
        value = getattr(args, attr)
        if value is not None:
            target[key] = value
    return config


def build_momentum_signal(instruments: str, start_time: str, end_time: str, score_start_time: str, lookback: int, freq: str):
    from qlib.data import D

    instrument_set = D.instruments(instruments) if isinstance(instruments, str) else instruments
    features = D.features(
        instruments=instrument_set,
        fields=["$close"],
        start_time=score_start_time,
        end_time=end_time,
        freq=freq,
    )
    close = features["$close"].unstack("instrument")
    score = close.div(close.shift(lookback)).sub(1.0)
    score = score.loc[pd.Timestamp(start_time) : pd.Timestamp(end_time)]
    stacked = score.stack(dropna=True).rename("score").to_frame()
    stacked.index.names = ["datetime", "instrument"]
    return stacked.sort_index()


def main() -> int:
    args = parse_args()
    config = override(load_config(args.config), args)

    import qlib
    from qlib.backtest import backtest, executor
    from qlib.constant import REG_CN
    from qlib.contrib.strategy import TopkDropoutStrategy
    from qlib.utils.time import Freq

    provider_uri = topic_path(config["provider_uri"])
    qlib.init(provider_uri=str(provider_uri), region=REG_CN)

    freq = config.get("freq", "day")
    signal_config = config["signal"]
    backtest_config = config["backtest"]
    pred_score = build_momentum_signal(
        instruments=config["market"],
        start_time=backtest_config["start_time"],
        end_time=backtest_config["end_time"],
        score_start_time=signal_config.get("score_start_time", "2017-01-01"),
        lookback=int(signal_config.get("lookback", 20)),
        freq=freq,
    )

    strategy = TopkDropoutStrategy(
        signal=pred_score,
        topk=int(backtest_config.get("topk", 30)),
        n_drop=int(backtest_config.get("n_drop", 3)),
    )
    executor_obj = executor.SimulatorExecutor(time_per_step=freq, generate_portfolio_metrics=True)
    portfolio_metric_dict, indicator_dict = backtest(
        executor=executor_obj,
        strategy=strategy,
        start_time=backtest_config["start_time"],
        end_time=backtest_config["end_time"],
        benchmark=config["benchmark"],
        account=float(backtest_config.get("account", 1000000)),
        exchange_kwargs={
            "freq": freq,
            "limit_threshold": backtest_config.get("limit_threshold", 0.095),
            "deal_price": backtest_config.get("deal_price", "close"),
            "open_cost": backtest_config.get("open_cost", 0.0005),
            "close_cost": backtest_config.get("close_cost", 0.0015),
            "min_cost": backtest_config.get("min_cost", 5),
        },
    )

    analysis_freq = "{}{}".format(*Freq.parse(freq))
    report, positions = portfolio_metric_dict.get(analysis_freq)

    output_dir = topic_path(config.get("output_dir", "outputs/backtests"))
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "topk_portfolio_metrics.csv"
    positions_path = output_dir / "topk_positions.pkl"
    indicators_path = output_dir / "topk_indicators.pkl"

    report.to_csv(report_path)
    pd.to_pickle(positions, positions_path)
    pd.to_pickle(indicator_dict, indicators_path)

    print(f"wrote {report_path.relative_to(TOPIC_DIR)}")
    print(f"wrote {positions_path.relative_to(TOPIC_DIR)}")
    print(f"wrote {indicators_path.relative_to(TOPIC_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

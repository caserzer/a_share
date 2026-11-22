"""Observe what happened after frozen weak-market signals. Future market returns only group outcomes."""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from prepare import MAIN, OUT, PRIVATE


def run():
    signal = pd.read_csv(OUT / "signals.csv", parse_dates=["signal_date", "entry_date", "exit_date"])
    market = pd.read_parquet(PRIVATE / "market.parquet").open
    frame = signal.loc[signal.event_status.eq("OK")].copy()
    frame["csi300"] = frame.exit_date.map(market) / frame.entry_date.map(market) - 1
    assert frame.csi300.notna().all()
    frame["forward_market"] = np.select([frame.csi300.lt(0), frame.csi300.gt(0)], ["down", "up"], default="flat")
    frame["sample"] = np.select([frame.phase.eq("warmup"), frame.exit_date.le(MAIN)], ["warmup", "primary"], default="later")
    frame["d10_minus_csi300"] = frame.d10 - frame.csi300
    frame["red_minus_csi300"] = frame.red - frame.csi300
    np.testing.assert_allclose(frame.d10_minus_csi300 - frame.red_minus_csi300, frame.gap, rtol=0, atol=1e-12)
    weak = frame.loc[frame.trend20.lt(0)]
    rows = pd.concat([weak, weak.assign(forward_market="all")])
    rows.groupby(["sample", "forward_market"]).agg(
        periods=("gap", "size"), market_mean=("csi300", "mean"), d10_mean=("d10", "mean"),
        red_mean=("red", "mean"), gap_mean=("gap", "mean"), d10_wins=("label", "sum"),
        stock_excess=("d10_minus_csi300", "mean"), red_excess=("red_minus_csi300", "mean")
    ).to_csv(HERE / "weak_periods.csv")
    primary = frame.loc[frame["sample"].eq("primary")].copy()
    primary["weight_third"] = pd.qcut(primary.allocation, 3, labels=["low", "middle", "high"])
    primary.groupby("weight_third", observed=True).agg(periods=("gap", "size"), d10_wins=("label", "sum"),
        d10_weight=("allocation", "mean"), d10_minus_red=("gap", "mean")).to_csv(HERE / "weight_groups.csv")
    frame[["signal_date","entry_date","exit_date","sample","trend20","forward_market","csi300","d10","red","gap","allocation"]].to_csv(HERE / "observations.csv",index=False)


if __name__ == "__main__":
    run()

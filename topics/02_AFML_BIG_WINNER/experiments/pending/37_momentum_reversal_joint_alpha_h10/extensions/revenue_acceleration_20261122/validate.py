"""Rebuild the linked quarterly values, match eligibility, and baseline independently."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from prepare import D, RANK, PRIVATE, MAIN, SCORE, FIELDS, sha, dump


def raw_events(panel, calendar):
    sources = pd.read_csv(D / "raw_sources.csv").set_index("instrument")
    for row in sources.itertuples():
        assert sha(row.path) == row.sha256, row.path
    unique = panel[panel.usable].drop_duplicates(["instrument", "known_date"])
    for name, states in unique.groupby("instrument"):
        raw = pd.read_parquet(sources.at[name, "path"], columns=[
            "REPORT_DATE", "NOTICE_DATE", "UPDATE_DATE", "TOTALOPERATEREVE"])
        raw.index = pd.to_datetime(raw.REPORT_DATE).dt.to_period("Q")
        raw = raw.loc[~raw.index.duplicated(keep=False)]
        rev = raw.TOTALOPERATEREVE.astype(float)
        timestamps = raw[["NOTICE_DATE", "UPDATE_DATE"]].apply(pd.to_datetime)
        for row in states.itertuples():
            period = pd.Period(row.period, freq="Q")
            deps = set()
            quarterly = {}
            for q in (period, period-1, period-4, period-5):
                deps.add(q)
                quarterly[q] = rev.at[q]
                if q.quarter > 1:
                    deps.add(q-1)
                    quarterly[q] -= rev.at[q-1]
            current = quarterly[period] / quarterly[period-4] - 1
            previous = quarterly[period-1] / quarterly[period-5] - 1
            np.testing.assert_allclose([current, previous, current-previous],
                [row.growth, row.previous_growth, row.acceleration], atol=1e-12, rtol=0)
            dates = timestamps.loc[sorted(deps)]
            assert dates.notna().all().all()
            latest = dates.max().max()
            assert row.available_date == latest
            assert calendar[calendar.searchsorted(latest, side="right")] == row.known_date
    return len(unique)


def check_matches(panel):
    lookup = panel.set_index(["signal_date", "instrument"])
    pairs = pd.read_csv(D / "pairs.csv", parse_dates=["signal_date"])
    singles = pd.concat([pairs[["signal_date", side]].rename(columns={side: "instrument"})
                         for side in ["positive", "negative"]])
    assert not singles.duplicated().any()
    scale = panel.groupby("signal_date")[FIELDS].std(ddof=0)
    expected = panel.base.copy()
    expected.index = lookup.index
    for row in pairs.itertuples():
        a = lookup.loc[(row.signal_date, row.positive)]
        b = lookup.loc[(row.signal_date, row.negative)]
        assert a.usable and b.usable and a.acceleration > 0 > b.acceleration
        assert a.industry == b.industry == row.industry and row.industry != "UNKNOWN"
        assert a[SCORE+"_d"] == b[SCORE+"_d"] == row.decile
        gap = (a[FIELDS].astype(float) - b[FIELDS].astype(float)) / scale.loc[row.signal_date]
        assert (gap.abs().to_numpy() <= np.array([.25, .5, .5]) + 1e-12).all()
        if row.decile == 10:
            expected.at[(row.signal_date, row.positive)] *= 1.5
            expected.at[(row.signal_date, row.negative)] *= .5
    np.testing.assert_allclose(expected, lookup.tilt, atol=1e-14, rtol=0)
    return len(pairs)


def run():
    for name, checksum in json.loads((D/"inputs.json").read_text()).items():
        assert sha(name) == checksum, name
    for name, checksum in json.loads((D/"selection.json").read_text()).items():
        assert sha(D/name) == checksum, name
    calendar = pd.read_parquet(PRIVATE/"market.parquet").index
    panel = pd.read_parquet(D/"panel.parquet")
    events = raw_events(panel, calendar)
    pairs = check_matches(panel)
    keys = ["scope", "mode", "cost", "date"]
    base = pd.read_parquet(D/"daily.parquet").query("model=='base'").set_index(keys).sort_index()
    old = pd.read_parquet(RANK/"results/daily.parquet").query("model=='base'").set_index(keys).sort_index()
    pd.testing.assert_frame_equal(base, old, check_exact=True)
    accounts = pd.read_csv(D/"accounts.csv")
    ref = json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"]
    index = pd.DataFrame(ref["items"],columns=ref["fields"]).set_index("trade_date").close.astype(float)
    close_ratio = index["20250303"] / index["20210108"]
    comparison = []
    for r in accounts.query("scope=='primary' and mode=='flat' and cost=='main'").itertuples():
        benchmark = close_ratio ** (252/r.days) - 1
        portfolio = r.closing_nav ** (252/r.days) - 1
        comparison.append(dict(model=r.model, index_close_cagr=benchmark,
                               portfolio_close_cagr=portfolio, excess_cagr=portfolio-benchmark))
    pd.DataFrame(comparison).to_csv(D/"benchmark.csv", index=False)
    dump(D/"validation.json", dict(verified_source_files=len(pd.read_csv(D/"raw_sources.csv")),
         reconstructed_linked_events=events, verified_pairs=pairs, exact_baseline_daily_rows=len(base),
         max_ledger_error=accounts.ledger_error.max(), input_and_selection_hashes_verified=True))


if __name__ == "__main__":
    run()

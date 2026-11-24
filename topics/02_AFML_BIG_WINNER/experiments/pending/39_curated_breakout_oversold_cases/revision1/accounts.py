"""Run the frozen EP38 execution rules on the EP39 corrected local decisions."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pandas as pd

REV = Path(__file__).resolve().parent
EP39 = REV.parent
sys.path.insert(0, str(EP39 / "training"))
import accounts_replay as engine

OUT = REV / "results/accounts"
PLAN = REV / "results/decisions/planned.parquet"
PANEL = EP39 / "results/panel.parquet"
KEY = ["pool", "signal_date", "instrument"]
BOOK = ["pool", "scope", "series", "segment", "cost", "model"]
SEEDS = [39, 139, 239, 339, 439]
ARMS = {"full", "natural", "hard", "legacy_local", *(f"random_{s}" for s in SEEDS), *(f"shuffle_{s}" for s in SEEDS)}


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def check_plan(planned, panel):
    assert set(planned.model) == ARMS
    assert not panel.duplicated(KEY).any() and not planned.duplicated(KEY + ["model"]).any()
    assert len(planned) == len(panel) * len(ARMS)
    plans = planned.set_index(KEY + ["model"]).score.unstack("model")
    baseline = panel.set_index(KEY, verify_integrity=True).sort_index()
    assert plans.index.equals(baseline.index) and np.isfinite(plans).all().all()
    np.testing.assert_allclose(plans.full, baseline.score, atol=1e-10, rtol=0)
    return {"stock_dates": len(panel), "planned_rows": len(planned), "arms": sorted(ARMS),
            "max_baseline_score_error": float((plans.full-baseline.score).abs().max())}


def verify_books(windows, daily, orders, summaries):
    assert not windows.duplicated(BOOK + ["signal_date"]).any()
    assert not daily.duplicated(BOOK + ["date"]).any()
    assert not orders.duplicated(BOOK + ["idx", "instrument"]).any()
    assert set(windows.cost) == set(engine.COSTS)
    np.testing.assert_allclose(windows.net + windows.fee, windows.gross, rtol=0, atol=1e-11)
    expected_fee = orders.cost.map(engine.COSTS) * np.where(
        orders.net_amount > 0, .001*orders.net_amount, -.002*orders.net_amount)
    np.testing.assert_allclose(orders.fee, expected_fee, atol=1e-12, rtol=0)
    group = BOOK + ["idx"]
    confirmed = orders.assign(buy=orders.net_amount.clip(lower=0),
                             sell=-orders.net_amount.clip(upper=0)).groupby(group).agg(
                                    buy=("buy", "sum"), sell=("sell", "sum"), fees=("fee", "sum"))
    days = daily.set_index(group, verify_integrity=True)
    assert confirmed.index.isin(days.index).all()
    amounts = days[["buy", "sell", "fees"]].sort_index()
    np.testing.assert_allclose(confirmed.reindex(amounts.index, fill_value=0), amounts, atol=1e-9, rtol=0)
    common = windows[windows.series.eq("common")]
    segments = []
    for (pool, scope, seg), part in common.groupby(["pool", "scope", "segment"]):
        n = part.signal_date.nunique()
        assert len(part) == n * len(engine.COSTS) * len(ARMS)
        assert part.groupby(["cost","model"]).signal_date.nunique().eq(n).all()
        assert part.groupby("signal_date").size().eq(len(engine.COSTS)*len(ARMS)).all()
        segments.append(dict(pool=pool, scope=scope, segment=int(seg), n=int(n),
                             first=str(part.entry_date.min().date()), last=str(part.exit_date.max().date())))
    cashflow = daily.sort_values(BOOK + ["date"])
    cumulative = (cashflow.sell - cashflow.buy - cashflow.fees).groupby([cashflow[c] for c in BOOK]).cumsum()
    np.testing.assert_allclose(1+cumulative, cashflow.cash, atol=1e-9, rtol=0)
    finals = windows.assign(growth=1+windows.net).groupby(BOOK).growth.prod()
    published = summaries.set_index(BOOK, verify_integrity=True).nav.reindex(finals.index)
    np.testing.assert_allclose(finals, published, atol=1e-9, rtol=0)
    return dict(common_segments=segments, windows=len(windows), daily_rows=len(daily),
                net_orders=len(orders), account_segments=len(summaries))


def verify_archived_restart(daily):
    archive = pd.read_parquet(engine.EP38 / "results/wide_daily.parquet",
                              filters=[("model", "=", "transfer"), ("scope", "=", "primary_restart")])
    stable = daily[(daily.pool == "CSI800") & (daily.model == "full") &
                   (daily.scope == "primary") & (daily.series == "common")]
    results=[]
    for seg, part in stable.groupby("segment"):
        # A fresh non-overlapping segment can be compared before its own terminal
        # liquidation only if its opening day is identical to the archived restart.
        if part.date.min() != archive.date.min():
            continue
        end = part.date.max()
        ref = archive[archive.date <= end]
        comp = part.merge(ref, on=["date", "cost"], validate="1:1", suffixes=("", "_archive"))
        if end != archive.date.max():
            comp = comp[comp.date < end]
        for c in ["nav", "cash", "buy", "sell", "fees"]:
            np.testing.assert_allclose(comp[c], comp[c+"_archive"], atol=1e-9, rtol=0)
        results.append(dict(segment=int(seg), first=str(comp.date.min().date()),
                            last=str(comp.date.max().date()), days=int(comp.date.nunique()),
                            max_abs_nav_error=float((comp.nav-comp.nav_archive).abs().max())))
    return results


def positions_at_entry(pool, planned, windows, orders, daily, swaps):
    """Reconcile each changed name's pre- and post-trade open value with its net order."""
    market, actions = engine.make_market(pool)
    open_marks = market.marks["flat"][0]
    relevant = swaps[swaps.pool.eq(pool)]
    needed = pd.concat([relevant[["signal_date", "model", c]].rename(columns={c: "instrument"})
                        for c in ("outgoing", "incoming")], ignore_index=True)
    needed = pd.concat([needed, needed.assign(model="full")], ignore_index=True).drop_duplicates()
    requested = {k: t.instrument.to_numpy() for k,t in needed.groupby(["model","signal_date"])}
    snapshots = []
    for name, scores in planned[planned.pool.eq(pool)].groupby("model"):
        replay = engine.Replay(market, actions, scores)
        w = windows[(windows.pool==pool) & (windows.model==name)]
        for (scope, segment), g in w.groupby(["scope", "segment"]):
            first = int(np.searchsorted(replay.entries, g.entry_idx.min()))
            stop = first + len(g)
            books = {}
            replay.execute(first, stop, "base", books=books)
            mask = lambda f: (f.pool==pool) & (f.model==name) & (f.scope==scope) & (f.segment==segment)
            ledger = orders.loc[mask(orders)]
            fills = {i: (market.symbols.get_indexer(z.instrument), z.net_amount.to_numpy()) for i,z in ledger.groupby("idx")}
            balance = daily.loc[mask(daily)].set_index("idx")
            for row in g.itertuples():
                i = row.entry_idx
                if (name,row.signal_date) not in requested:
                    continue
                u, cash, _ = books[int(np.searchsorted(replay.entries,i))]
                assert np.isfinite(open_marks[i, u>0]).all()
                values = u * np.nan_to_num(open_marks[i])
                nav0 = values.sum() + cash
                # The actual net order for a delivered predecessor is reported in its successor.
                for old, new, listing in actions:
                    if i >= listing:
                        values[new] += values[old]
                        values[old] = 0
                flow = np.zeros(market.n)
                if i in fills:
                    idx, amount = fills[i]
                    flow[idx] = amount
                np.testing.assert_allclose(values.sum()+flow.sum()+balance.at[i,"cash"],
                                           nav0-balance.at[i,"fees"], atol=1e-9, rtol=0)
                assert (values+flow).min() >= -1e-9
                names = requested[name,row.signal_date]
                idx = market.symbols.get_indexer(names)
                assert idx.min() >= 0
                snapshots.append(pd.DataFrame(dict(pool=pool, scope=scope, segment=segment,
                    signal_date=row.signal_date, entry_date=row.entry_date, model=name, instrument=names,
                    pre_weight=values[idx]/nav0, order_weight=flow[idx]/nav0,
                    post_weight=(values[idx]+flow[idx])/nav0, pretrade_nav=nav0,
                    net_amount=flow[idx])))
    return pd.concat(snapshots, ignore_index=True)


def actual_orders(planned, frames, swaps):
    standard = {k: frames[k][frames[k].series.eq("common") & frames[k].cost.eq("base")]
                for k in ["windows", "orders", "daily"]}
    stocks = pd.concat([positions_at_entry(pool, planned, **standard, swaps=swaps)
                        for pool in ["CSI300", "CSI800"]], ignore_index=True)
    segments = standard["windows"].query("model=='full'")[["pool","scope","signal_date","segment","entry_date"]]
    joined = swaps.merge(segments, on=["pool","scope","signal_date"], validate="m:1")
    key = ["pool","scope","segment","signal_date","entry_date"]
    quantities = ["pre_weight","order_weight","post_weight","pretrade_nav","net_amount"]
    for role in ["outgoing", "incoming"]:
        for account in ["full", "revised"]:
            src = stocks if account=="revised" else stocks[stocks.model.eq("full")]
            match = [*key, role] + (["model"] if account=="revised" else [])
            suffix = role+"_"+account+"_"
            src = src.rename(columns={"instrument":role, **{v:suffix+v for v in quantities}})
            joined = joined.merge(src[match+[suffix+v for v in quantities]], on=match, validate="m:1", how="left")
            assert joined[suffix+"pretrade_nav"].notna().all()
    threshold = 1e-10
    joined["replacement_bought"] = joined.incoming_revised_order_weight > threshold
    joined["replacement_already_held"] = joined.incoming_revised_pre_weight > threshold
    joined["replacement_held_after"] = joined.incoming_revised_post_weight > threshold
    joined["outgoing_actually_sold"] = joined.outgoing_revised_order_weight < -threshold
    joined["outgoing_still_held"] = joined.outgoing_revised_post_weight > threshold
    joined["baseline_held_outgoing"] = joined.outgoing_full_post_weight > threshold
    flags = ["replacement_bought", "replacement_already_held", "replacement_held_after",
             "outgoing_actually_sold", "outgoing_still_held", "baseline_held_outgoing"]
    summary = joined.groupby(["pool","scope","model"]).agg(
        swaps=("slot","size"), **{k:(k,"sum") for k in flags}).reset_index()
    return joined, summary


def main():
    planned = pd.read_parquet(PLAN, columns=KEY + ["model", "score"])
    panel = pd.read_parquet(PANEL, columns=KEY + ["score", "selected", "scope", "in_legacy300", "breakout", "oversold"])
    audit = check_plan(planned, panel)
    engine.OUT = OUT
    out = {k: [] for k in ["targets", "orders", "windows", "daily", "summary", "gaps"]}
    for pool in ["CSI300", "CSI800"]:
        engine.replay_pool(pool, planned[planned.pool.eq(pool)], panel[panel.pool.eq(pool)], out)
    frames = {k: pd.concat(out.pop(k), ignore_index=True) for k in ["targets", "orders", "windows", "daily"]}
    summaries = pd.DataFrame(out["summary"])
    gaps = pd.DataFrame(out["gaps"], columns=["pool", "scope", "series", "segment", "model", "cost",
                                             "requested_start", "requested_exit", "date", "reason", "symbols", "idx"])
    targets = frames["targets"]
    full = targets.loc[targets.model.eq("full"), KEY].set_index(KEY).sort_index()
    expected = panel.loc[panel.selected, KEY].set_index(KEY).sort_index()
    pd.testing.assert_index_equal(full.index, expected.index)
    counts = targets.groupby(["pool", "signal_date", "model"]).size().unstack()
    assert counts.eq(counts.full, axis=0).all().all()
    capital = targets.groupby(["pool", "signal_date", "model"]).weight.sum()
    np.testing.assert_allclose(capital, 1.0, atol=1e-12, rtol=0)
    parity = {p: engine.check_parity(frames["daily"], frames["windows"], p) for p in ["CSI300","CSI800"]}
    parity["archived_restart"] = verify_archived_restart(frames["daily"])
    parity["scores_sha256"] = sha(PLAN)
    parity["baseline_plan"] = audit
    parity["baseline_targets"] = len(full)
    parity["ledger_checks"] = verify_books(frames["windows"],frames["daily"],frames["orders"],summaries)
    swaps_path = REV / "results/decisions/swaps.parquet"
    realized, counts = actual_orders(planned, frames, pd.read_parquet(swaps_path))
    parity["swaps_sha256"] = sha(swaps_path)
    parity["linked_standard_cost_swaps"] = len(realized)
    for name, data in frames.items():
        data.to_parquet(OUT / (name+".parquet"), index=False)
    summaries.to_csv(OUT / "account_summary.csv", index=False)
    gaps.to_csv(OUT / "gaps.csv", index=False)
    realized.to_parquet(OUT / "decision_orders.parquet", index=False)
    counts.to_csv(OUT / "decision_orders_summary.csv", index=False)
    parity["sha256"] = {p.name: sha(p) for p in [OUT / (k+".parquet") for k in frames] +
                       [OUT/"account_summary.csv", OUT/"gaps.csv", OUT/"decision_orders.parquet",
                        OUT/"decision_orders_summary.csv", Path(__file__), Path(engine.__file__)]}
    (OUT / "parity.json").write_text(json.dumps(parity, indent=2)+"\n")
    print(json.dumps(parity["ledger_checks"],ensure_ascii=False),flush=True)


if __name__ == "__main__":
    main()


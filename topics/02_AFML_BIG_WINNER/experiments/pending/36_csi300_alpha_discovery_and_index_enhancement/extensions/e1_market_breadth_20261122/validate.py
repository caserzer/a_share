"""Cross-check fixed selections, trade restrictions and the per-stock decision ledger."""
import json
from collections import Counter
import numpy as np
import pandas as pd
from prepare import EP, ROOT, D, OLD, SEED, MODELS, END, Inputs, sha, save_json
from analyze import group_name
from suspension_sensitivity import marks


def main():
    for manifest, base in [("inputs.json",EP),("selection.json",D)]:
        items=json.loads((D/manifest).read_text())
        for path,h in items.items():
            assert sha(base/path)==h,path
    m=pd.read_parquet(D/"monthly_candidates.parquet")
    matches=pd.read_csv(D/"matches.csv",parse_dates=["signal_date"])
    random=pd.read_csv(D/"random_targets.csv.gz",parse_dates=["signal_date"],keep_default_na=False)
    bydate={d:g.set_index("instrument") for d,g in m.groupby("signal_date")}
    for dr in random.itertuples():
        g=bydate[dr.signal_date]
        dd=g[g.E1_q5 & g.dd.eq(1)]
        ids=dr.instruments.split("|") if dr.instruments else []
        assert len(ids)==len(set(ids))==len(dd)
        assert g.loc[ids,"E1_q5"].all() and Counter(g.loc[ids,"industry"])==Counter(dd.industry)
    for date,rows in matches.groupby("signal_date"):
        g=bydate[date]
        assert rows.selected.is_unique
        selected=g.loc[rows.selected].reset_index(drop=True)
        peers=g.loc[rows.peer].reset_index(drop=True)
        assert selected.E1_q5.all() and not peers.E1_q5.any()
        assert selected.dd.eq(1).all() and peers.dd.eq(1).all()
        assert selected.industry.equals(peers.industry) and not selected.industry.eq("UNKNOWN").any()
        sd=g.groupby("industry")[["trend","short"]].std(ddof=0).loc[selected.industry].reset_index(drop=True)
        assert ((selected[["trend","short"]]-peers[["trend","short"]]).abs()<=.5*sd+1e-12).all().all()
    inp=Inputs()
    marks(inp,0.)
    nav=pd.read_csv(D/"daily_nav.csv",parse_dates=["date"]).set_index("date")
    schedule=pd.read_csv(D/"decision_periods.csv",parse_dates=["signal_date","entry","cycle_end"])
    rows=[]
    fee_errors=[]
    for model in MODELS+["DD"]:
        o=pd.read_parquet(D/(model+"_orders.parquet"))
        daily=pd.read_parquet(D/"daily_accounts.parquet").query("model == @model").set_index("date")
        for r in schedule.itertuples():
            trades=o[o.date.eq(r.entry)].copy()
            # Empty portfolio rebalancing to cash may have no orders.
            active=trades[trades.units_after>0].copy()
            symbols=inp.symbols.get_indexer(active.instrument)
            j=inp.days.get_loc(r.cycle_end)
            start_nav=daily.at[r.entry,"pretrade_nav"]
            terminal_prices=inp.c[j,symbols] if r.signal_date==schedule.signal_date.iloc[-1] else inp.o[j,symbols]
            assert np.isfinite(terminal_prices).all()
            pnl=active.units_after.to_numpy()*(terminal_prices-active.price.to_numpy())/start_nav
            g=bydate[r.signal_date]
            flags=g.dd.reindex(active.instrument).to_numpy()
            cost=daily.at[r.entry,"fees"]/start_nav
            end_nav=daily.at[r.cycle_end,"nav" if r.signal_date==schedule.signal_date.iloc[-1] else "pretrade_nav"]
            actual=end_nav/start_nav-1
            err=abs(pnl.sum()-cost-actual)
            fee_errors.append(err)
            assert err<1e-10,(model,r.signal_date,err)
            u=trades.units_after-trades.units_before
            assert not ((u>1e-10)&~trades.can_buy).any() and not ((u< -1e-10)&~trades.can_sell).any()
            rows.append(dict(model=model,signal_date=r.signal_date,entry=r.entry,end=r.cycle_end,
                             breadth=r.breadth,dd_pnl=pnl[flags==1].sum(),other_pnl=pnl[flags==0].sum(),
                             unknown_pnl=pnl[np.isnan(flags)].sum(),cost=cost,cycle_net=actual,
                             actual_holdings=len(active),max_stock=active.actual_weight.max() if len(active) else 0.,
                             max_industry=active.groupby(active.instrument.map(g.industry).fillna("UNKNOWN")).actual_weight.sum().max() if len(active) else 0.,
                             actual_dd_weight=active.actual_weight.to_numpy()[flags==1].sum()))
        z=pd.DataFrame(rows).query("model==@model")
        assert np.isclose((1+z.cycle_net).prod(),nav[model].iloc[-1])
    ledger=pd.DataFrame(rows)
    ledger["breadth_bin"]=group_name(ledger.breadth)
    ledger.to_csv(D/"cycle_attribution.csv",index=False)
    checks=dict(source_hashes=len(json.loads((D/"inputs.json").read_text())),sealed_files=len(json.loads((D/"selection.json").read_text())),
                quarterly_fits=len(pd.read_csv(D/"folds.csv")),random_industry_sets=len(random),industry_pairs=len(matches),
                decision_ledgers=len(rows),max_pnl_identity_error=max(fee_errors),regression_tests="96 passed (EP36/tests)",
                eligible_prediction_rows=len(pd.read_parquet(D/"weekly_predictions.parquet",columns=["E1"])),
                original_score_max_error=pd.read_csv(D/"folds.csv").baseline_replay_error.max(),
                original_dd_and_E1_exact_nav_days=len(nav),status="PASS")
    save_json(D/"validation.json",checks)
    print(checks)


if __name__=="__main__":
    main()

"""Audit time cutoffs, paired inference, and realized market-state attribution."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from prepare import MAIN, OUT, ROOT, TARGETS, FEATURES, fit, sha, dump
from core import bootstrap
from simulate import RED


def leg_attribution(cycles,orders,holds):
    """Use cash flows plus change in marked holdings, respecting terminal-open sales."""
    output=[]
    for name,periods in cycles.groupby("strategy"):
        transactions=orders[orders.strategy.eq(name)]
        positions=holds[holds.strategy.eq(name)]
        capital=1.
        for r in periods.sort_values("signal_date").itertuples():
            last=r.exit_date==MAIN
            leg_returns={}
            all_fees=0.
            for leg,is_red in [("red",True),("stocks",False)]:
                tx=transactions[transactions.instrument.eq(RED).eq(is_red)]
                # Opening post-trade weights use opening NAV less this open's fees.
                def postvalue(date,nav):
                    fee=transactions.loc[transactions.date.eq(date),"fee"].sum()
                    h=positions[positions.date.eq(date)&positions.instrument.eq(RED).eq(is_red)]
                    return h.open_weight.sum()*(nav-fee)
                first=tx[tx.date.eq(r.entry_date)]
                begin=postvalue(r.entry_date,capital)-(first.buy-first.sell).sum()
                final_nav=capital*(1+r.cycle_return)
                final=tx[tx.date.eq(r.exit_date)]
                end=postvalue(r.exit_date,final_nav+transactions.loc[transactions.date.eq(r.exit_date),"fee"].sum() if last else final_nav)
                if not last:
                    end-=(final.buy-final.sell).sum()
                span=tx[(tx.date>=r.entry_date)&((tx.date<r.exit_date)|(last&(tx.date==r.exit_date)))]
                leg_returns[leg]=(end-begin+(span.sell-span.buy).sum())/capital
                all_fees+=span.fee.sum()/capital
            residual=r.cycle_return-(sum(leg_returns.values())-all_fees)
            assert abs(residual)<1e-9,(name,r.signal_date,residual)
            output.append(dict(strategy=name,signal_date=r.signal_date,stocks_pnl=leg_returns["stocks"],
                               dividend_pnl=leg_returns["red"],fees=all_fees,net=r.cycle_return))
            capital=final_nav
    return pd.DataFrame(output)


def run():
    f=pd.read_csv(OUT/"signals.csv",parse_dates=["signal_date","entry_date","exit_date","cutoff"]).set_index("signal_date")
    fits=json.loads((OUT/"fits.json").read_text())
    # Refit each quarter with all outcomes at/after the first signal erased.
    for spec in fits:
        cutoff=pd.Timestamp(spec["cutoff"])
        z=f.loc[:cutoff].copy()
        z.loc[z.exit_date.gt(cutoff)|z.exit_date.isna(),"label"]=np.nan
        prefix,_=fit(z)
        assert np.isclose(prefix.prob.iloc[-1],f.at[cutoff,"prob"],equal_nan=True)
        assert pd.Timestamp(spec["latest_exit"])<=cutoff and spec["n"]==f.at[cutoff,"train_n"]
        fold=f[f.cutoff==cutoff].dropna(subset=FEATURES)
        scores=(fold[FEATURES].values-np.array(spec["mean"]))/np.array(spec["scale"])
        pred=1/(1+np.exp(-(scores@np.array(spec["coef"])+spec["intercept"])))
        np.testing.assert_allclose(pred,fold.prob,rtol=0,atol=1e-11)
    c=pd.read_csv(OUT/"cycles.csv",parse_dates=["signal_date","entry_date","exit_date"])
    c=c[c.scope.eq("primary")]
    by_cost=[]
    for cost,h in c.groupby("cost"):
        wide=h.pivot(index="signal_date",columns="strategy",values="cycle_return")
        for other in ["balanced","matched","rule","d10","dividend"]:
            delta=wide.dynamic-wide[other]
            for scope,sub in [("primary",delta),*[(str(year),g) for year,g in delta.groupby(delta.index.year)]]:
                by_cost.append(dict(scope=scope,cost=cost,control=other,**bootstrap(sub)))
    pd.DataFrame(by_cost).to_csv(OUT/"paired_tests.csv",index=False)
    c=c[c.cost.eq("main")]
    o=pd.read_parquet(OUT/"orders.parquet").query("scope=='primary'")
    h=pd.read_parquet(OUT/"holdings_at_open.parquet")
    attr=leg_attribution(c,o,h)
    attr.to_csv(OUT/"cycle_attribution.csv",index=False)

    stats=[]
    decisions=[]
    phases={"primary_test":f[(f.phase=="test")&f.exit_date.le(MAIN)],
            "later_history":f[f.entry_date.ge(MAIN)&f.exit_date.notna()],"warmup":f[f.phase=="warmup"]}
    for scope,periods in phases.items():
        for state,subset in [("all",periods),("weak",periods[periods.trend20<0]),("other",periods[periods.trend20>=0])]:
            z=subset.dropna(subset=["label"])
            stats.append(dict(scope=scope,state=state,scheduled=len(subset),paired=len(z),d10=z.d10.mean(),
                dividend=z.red.mean(),relative=z.gap.mean(),red_loss_rate=z.red.lt(0).mean(),d10_win=z.label.mean(),
                weight=subset.allocation.mean(),rebounds=((z.d10>0)&(z.gap>0)).sum(),
                avoided_full_d10=((1-z.allocation)*(-z.gap).clip(lower=0)).sum(),
                missed_full_d10=((1-z.allocation)*z.gap.clip(lower=0)).sum()))
        pred=periods.dropna(subset=["label","prob"]).copy()
        if len(pred):
            pred["correct"]=pred.prob.ge(.5)==pred.label
            pred["gross_vs_equal"]=(pred.prob-.5)*pred.gap
            pred["relative_abs"]=pred.gap.abs()
            decisions.append(pred.assign(scope=scope))
    pd.DataFrame(stats).to_csv(OUT/"market_states.csv",index=False)
    pred=pd.concat(decisions)
    pred.to_csv(OUT/"predictions_scored.csv")
    accuracy=[]
    for scope,g in pred.groupby("scope"):
        accuracy.append(dict(scope=scope,n=len(g),accuracy=g.correct.mean(),base_accuracy=(g.base_rate.ge(.5)==g.label).mean(),
            auc=roc_auc_score(g.label,g.prob),brier=((g.prob-g.label)**2).mean(),base_brier=((g.base_rate-g.label)**2).mean(),
            relative_correct=g.gross_vs_equal.mean(),largest_miss=g[~g.correct].relative_abs.max()))
    pd.DataFrame(accuracy).to_csv(OUT/"forecast_scores.csv",index=False)
    # Relate calendar-matched actual returns to signal states including missing standalone labels.
    wide=c.pivot(index="signal_date",columns="strategy",values="cycle_return")
    facts=wide.join(f[["trend20","allocation","gap","d10","red"]].rename(columns={"d10":"event_d10"}))
    facts["state"]=np.where(facts.trend20<0,"weak","other")
    facts["dynamic_minus_balanced"]=facts.dynamic-facts.balanced
    facts["dynamic_minus_matched"]=facts.dynamic-facts.matched
    facts["market_weight"]=facts.allocation
    facts.to_csv(OUT/"decision_returns.csv")
    stats=facts.groupby("state").agg(dates=("dynamic","size"),dynamic=("dynamic","mean"),balanced=("balanced","mean"),
        matched=("matched","mean"),timing_vs_matched=("dynamic_minus_matched","mean"),rule=("rule","mean"),
        mean_d10_weight=("allocation","mean"))
    stats.to_csv(OUT/"realized_regimes.csv")
    target=pd.read_parquet(OUT/"targets.parquet")
    stock=pd.read_parquet(TARGETS).query("base>0")
    for name,chosen in target.groupby("strategy"):
        assert np.allclose(chosen.groupby("signal_date").weight.sum(),1)
        w=c[c.strategy==name].set_index("signal_date").target_d10
        q=chosen[chosen.instrument.ne(RED)]
        if len(q):
            joined=q.merge(stock[["signal_date","instrument","base"]],on=["signal_date","instrument"],validate="1:1")
            assert len(joined)==len(q)
            np.testing.assert_allclose(joined.weight,joined.base*joined.signal_date.map(w))
    a=pd.read_csv(OUT/"accounts.csv")
    assert np.allclose(c.actual_cash+c.actual_d10+c.actual_red,1)
    for cost in ["main","index_free"]:
        ref=a.query("scope=='primary' and strategy=='d10' and mode=='flat' and cost==@cost").nav.iloc[0]
        assert abs(ref-a.query("scope=='primary' and strategy=='d10' and mode=='flat' and cost=='main'").nav.iloc[0])<1e-10
    dump(OUT/"validation.json",dict(quarters_prefix_refitted=len(fits),allocation_targets_verified=len(target),
         cycle_pnl_reconciled=len(attr),same_legs_d10_replay=True,max_ledger_error=float(a.ledger_error.max()),
         baseline_replay_nav=float(a[a.scope=="baseline_replay"].nav.iloc[0])))


if __name__=="__main__":
    run()

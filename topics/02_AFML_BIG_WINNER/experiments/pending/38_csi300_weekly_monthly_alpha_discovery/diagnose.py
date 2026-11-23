"""Reconcile marked positions and attribute calendar-month paired returns."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE/"results"
EP = HERE.parent/"37_momentum_reversal_joint_alpha_h10"
sys.path.insert(0,str(EP/"code"))
from core import PRIVATE, sha, dump
R, E = "RANK_MSE_78", "E1_78"
w = pd.read_csv(OUT/"windows.csv",parse_dates=["signal_date","stop"])
a = pd.read_csv(OUT/"accounts.csv")
t = pd.read_parquet(OUT/"targets.parquet")
nav = pd.read_parquet(OUT/"daily.parquet").query("scope!='whole' and cost=='base'")
orders = pd.read_parquet(OUT/"orders.parquet").query("scope!='whole' and cost=='base'")
marks = pd.read_csv(OUT/"suspension_marks.csv",parse_dates=["date"]).query("mode=='flat'")
close = pd.read_parquet(PRIVATE/"qfq_close.parquet")
op = pd.read_parquet(PRIVATE/"qfq_open.parquet")
for r in marks.itertuples():
    close.at[r.date,r.instrument] = r.mark
    if pd.isna(op.at[r.date,r.instrument]):
        op.at[r.date,r.instrument] = r.mark

weights = []
files = sorted((PRIVATE/"weights").glob("????-??.json"))
for f in files:
    raw = json.loads(f.read_text()).get("data")
    if raw and raw["items"]:
        weights.append(pd.DataFrame(raw["items"],columns=raw["fields"]))
idxw = pd.concat(weights).drop_duplicates()
idxw["instrument"] = idxw.con_code.str[-2:]+idxw.con_code.str[:6]
idxw = idxw.pivot(index="trade_date",columns="instrument",values="weight").sort_index()
rng = np.random.default_rng(3810)
def ci(values):
    n = len(values)
    starts = rng.integers(0,n,(10000,(n+2)//3))
    ix = ((starts[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]
    return np.quantile(values[ix].mean(axis=1),[.05/6,1-.05/6])

monthly, trades, stats, exposure, positions = [], [], [], [], []
for scope in ["primary","later"]:
    pnl, active, closes = {}, {}, {}
    for model in t.model.unique():
        d = nav[(nav.scope==scope)&(nav.model==model)].set_index("date")
        o = orders[(orders.scope==scope)&(orders.model==model)].copy()
        o["units"] = (o.buy-o.sell)/o.price
        def matrix(column):
            return o.pivot(index="date",columns="instrument",values=column).reindex(index=d.index,columns=close.columns).fillna(0.)
        u = matrix("units").cumsum()
        u = u.mask(u.abs()<1e-12,0.)
        mark = close.loc[d.index].copy()
        if a.query("scope==@scope and model==@model and cost=='base'").valuation_complete.iloc[0]:
            mark.iloc[-1] = op.loc[d.index[-1]]
        value = (u*mark).mask(u==0,0.)
        assert not value.isna().any().any()
        np.testing.assert_allclose(value.sum(axis=1)+d.cash,d.nav,atol=1e-9)
        profit = value-value.shift().fillna(0.)+matrix("sell")-matrix("buy")-matrix("fee")
        prior = d.nav.shift().fillna(1.)
        np.testing.assert_allclose(profit.sum(axis=1),d.nav-prior,atol=1e-9)
        month = d.index.to_period("M")
        pnl[model] = profit.groupby(month).sum().div(prior.groupby(month).first(),axis=0)
        closes[model] = d.nav
        opening = (u*op.loc[d.index]).mask(u==0,0.)
        opening["cash"] = d.cash
        active[model] = opening.div(opening.sum(axis=1,skipna=False),axis=0)
        holdings = u.where(u>0).stack().rename("units").to_frame()
        holdings["marked_value"] = value.stack().reindex(holdings.index)
        positions.append(holdings.reset_index().set_axis(["date","instrument","units","marked_value"],axis=1).assign(scope=scope,model=model))
    for model in t.model.unique():
        s = w.query("scope==@scope and model==@model and cost=='base'").copy()
        mon = pnl[model].sum(axis=1)
        for ref in [R,E]:
            contrib = pnl[model]-pnl[ref]
            delta = contrib.sum(axis=1)
            monthly.extend(dict(scope=scope,model=model,reference=ref,month=str(k),net=mon[k],paired=v) for k,v in delta.items())
            if model not in [R,E]:
                z = contrib.stack().rename("delta").reset_index()
                z.columns=["month","instrument","delta"]
                trades.append(z.loc[z.delta.abs()>1e-13].assign(model=model,reference=ref,scope=scope))
        dates = pd.DatetimeIndex(t[t.signal_date.isin(s.signal_date)].entry_date.unique()).sort_values()
        cap = (active[model].loc[dates]-active[R].loc[dates]).abs().sum(axis=1,min_count=1)/2
        metrics = []
        for date in s.signal_date:
            h = t[(t.signal_date==date)&(t.model==model)]
            b = t[(t.signal_date==date)&(t.model==R)]
            ind = lambda g:g.groupby(g.industry.fillna("?")).weight.sum()
            iw = idxw.loc[:date.strftime("%Y%m%d")].iloc[-1]
            metrics.append(dict(scope=scope,model=model,signal_date=date,
                target_changed=1-len(set(h.instrument)&set(b.instrument))/len(b),
                open_active=cap.loc[h.entry_date.iloc[0]],
                industry_active=ind(h).sub(ind(b),fill_value=0).abs().sum()/2,
                index_weight_pct=h.instrument.map(iw).mean(),size_coverage=h.instrument.map(iw).notna().mean()))
        exposure.extend(metrics)
        diff = s["open_delta_"+R].to_numpy()
        interval = ci(diff)
        md = mon-pnl[R].sum(axis=1)
        other = w.query("scope==@scope and model==@model")
        stat = dict(scope=scope,model=model,n=len(s),paired=diff.mean(),low=interval[0],high=interval[1],
                    vs_e1=s["open_delta_"+E].mean(),excess=s.open_excess_proxy.mean(),tracking_error=s.open_excess_proxy.std()*np.sqrt(252/10),
                    ex_best3_month=md.drop(md.nlargest(3).index).mean(),trigger=sum(x["target_changed"]>0 for x in metrics),
                    **{k:np.mean([x[k] for x in metrics]) for k in ["target_changed","open_active","industry_active","index_weight_pct","size_coverage"]},
                    fees=s.fees.mean(),two_way_turnover=s.turnover.mean())
        for cost in ["double","zero"]:
            stat[cost] = other.loc[other.cost.eq(cost),"open_delta_"+R].mean()
        stats.append(stat)
pd.DataFrame(stats).to_csv(OUT/"summary.csv",index=False)
pd.DataFrame(exposure).to_csv(OUT/"exposure.csv",index=False)
pd.DataFrame(monthly).to_csv(OUT/"months.csv",index=False)
pd.concat(trades).to_parquet(OUT/"stock_month.parquet",index=False)
pd.concat(positions).to_parquet(OUT/"holdings.parquet",index=False)
expected = pd.read_csv(EP/"extensions/intraday_reversal_20261122/results/accounts.csv").query("model==@R and scope=='primary' and cost=='main' and style=='net' and mode=='flat'").cagr.iloc[0]
actual = a.query("model==@R and scope=='primary' and cost=='base'").cagr.iloc[0]
assert abs(actual-expected)<1e-12
for row in a.query("scope!='whole'").itertuples():
    z=w[(w.scope==row.scope)&(w.model==row.model)&(w.cost==row.cost)]
    if row.valuation_complete:
        assert len(z)==(100 if row.scope=="primary" else 39)
        assert z.open_net.notna().all() and abs((1+z.open_net).prod()-row.nav)<1e-10
        assert abs((1+z.net).prod()-row.nav)<1e-10
dump(OUT/"verification.json",dict(primary_replay_abs_error=abs(actual-expected),daily_position_and_profit_reconciled=True,
      rule_hash=sha(HERE/"replay.py"),diagnostics_hash=sha(Path(__file__)),weight_files={f.name:sha(f) for f in files}))

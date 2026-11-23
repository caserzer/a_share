"""Run from any directory with the EP36 private archive and EP37 frozen scores."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EP = HERE.parent / "37_momentum_reversal_joint_alpha_h10"
EXT = EP / "extensions/intraday_reversal_20261122"
sys.path[:0] = [str(EP / "code"), str(EXT)]
from core import PRIVATE, assign_deciles, sha, dump
import accounts
from execution import net_account

OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
accounts.OUT = OUT
RANK, E1, MIX, SECTOR = "RANK_MSE_78", "E1_78", "blend", "sector_blend"
LOW = "sector_lowvol"
MODELS = [RANK, E1, MIX, SECTOR, LOW]
split = pd.Timestamp("2025-03-03")
scorefile = EXT / "results/scores.parquet"
assert sha(scorefile) == json.loads((EXT/"results/selection.json").read_text())["scores.parquet"]
indexfile = PRIVATE / "net_excess_20261116/H00300.CSI.json"
inputs = [scorefile, indexfile, EXT/"execution.py", EP/"code/accounts.py", EP/"code/core.py",
          HERE/"PROTOCOL.md", Path(__file__)] + [PRIVATE/(s+".parquet") for s in
          ["industry","qfq_close","qfq_open","open","daily_members","opening_trade_status_v2","limits/daily","suspensions/daily"]]
dump(OUT/"inputs.json", {str(p.relative_to(HERE.parents[4])): sha(p) for p in inputs})
p = pd.read_parquet(scorefile).dropna(subset=["exit_date"]).copy()
assert not p.duplicated(["signal_date","instrument"]).any() and p[[RANK,E1]].notna().all().all()
industry = pd.read_parquet(PRIVATE/"industry.parquet")
industry["instrument"] = industry.ts_code.str[-2:] + industry.ts_code.str[:6]
close = pd.read_parquet(PRIVATE/"qfq_close.parquet")
vol = close.pct_change(fill_method=None).rolling(20).std()
targets = []
for date, g in p.groupby("signal_date"):
    key = date.strftime("%Y%m%d")
    active = industry[industry.in_date.le(key) & (industry.out_date.isna() | industry.out_date.gt(key))]
    mapping = active[["instrument","l1_name"]].drop_duplicates()
    mapping = mapping[~mapping.instrument.duplicated(False)].set_index("instrument").l1_name
    g = g.assign(industry=g.instrument.map(mapping), blend=g[[E1,RANK]].rank(pct=True).mean(axis=1))
    g = g.sort_values(["blend","instrument"])
    rank = g[g[RANK+"_d"].eq(10)]
    g["vol20"] = g.instrument.map(vol.loc[date])
    g["quality_vol"] = (g[RANK].rank(pct=True) + g.vol20.rank(pct=True,ascending=False).fillna(.5))/2
    pool = g[g[RANK+"_d"]>=9].sort_values(["quality_vol","instrument"])
    low_parts = [rank[rank.industry.isna()]]
    parts = [rank[rank.industry.isna()]]
    for sector, n in rank.industry.value_counts().items():
        low_parts.append(pool[pool.industry.eq(sector)].tail(n))
        parts.append(g[g.industry.eq(sector)].tail(n))
    for model, t in zip(MODELS,[rank,g[g[E1+"_d"].eq(10)],g.tail(len(rank)),pd.concat(parts),pd.concat(low_parts)]):
        assert len(t)==len(rank) and not t.instrument.duplicated().any()
        if model in [SECTOR,LOW]:
            assert t.industry.fillna("?").value_counts().to_dict()==rank.industry.fillna("?").value_counts().to_dict()
        targets.append(t.assign(model=model,weight=1/len(t)))
targets = pd.concat(targets,ignore_index=True)
targets.to_parquet(OUT/"targets.parquet",index=False)
m = accounts.Market()
raw = json.loads(indexfile.read_text())["data"]
tr = pd.DataFrame(raw["items"],columns=raw["fields"])
tr = tr.set_index(pd.to_datetime(tr.trade_date)).close
windows, daily, orders, summary, events, stocks = [], [], [], [], [], []
for model,t in targets.groupby("model"):
    for date,g in t.groupby("signal_date"):
        r,h = accounts.event(m,g,.001,.002)
        events.append(dict(model=model,signal_date=date,**r))
        stocks.append(h.assign(model=model,signal_date=date))
    for scope,g in [("primary",t[t.exit_date<=split]),("later",t[t.entry_date>=split]),("whole",t)]:
        end = int(g.exit_idx.max())
        for cost, bf, sf in [("base",.001,.002),("double",.002,.004),("zero",0.,0.)]:
            nav,o,status = net_account(m,g,end,"flat",bf,sf)
            meta = dict(model=model,scope=scope,cost=cost)
            nav = nav.set_index("date")
            daily.append(nav.reset_index().assign(**meta))
            orders.append(o.assign(**meta))
            enddate = nav.index[-1]
            # Boundary at close preceding each rebalance. First entry starts with cash,
            # terminal day uses post-execution open NAV per the shared engine.
            # Before a rebalance the held units are yesterday's post-trade units.
            # Actual order flows also cover delayed exits between rebalances.
            changes = o.assign(units=(o.buy-o.sell)/o.price).pivot(index="date",columns="instrument",values="units")
            held = changes.reindex(index=nav.index,columns=m.symbols).fillna(0.).cumsum().shift().fillna(0.)
            held = held.mask(held.abs()<1e-12,0.)
            prices = pd.DataFrame(m.marks["flat"][0][m.days.get_indexer(nav.index)],index=nav.index,columns=m.symbols)
            marked = (held*prices).mask(held==0,0.)
            before = marked.sum(axis=1,skipna=False)+nav.cash.shift().fillna(1.)
            last = 1.
            for d,b in g.groupby("signal_date"):
                e,x = int(b.entry_idx.iloc[0]), int(b.exit_idx.iloc[0])
                terminal = x==end
                stop = m.days[x if terminal else x-1]
                if stop>enddate:
                    break
                v = nav.loc[stop,"nav"]
                seg = nav.loc[m.days[e]:stop]
                # Index close proxy uses last pre-entry close, and terminal date close.
                bench = tr.loc[stop]/tr.loc[m.days[e-1]]-1
                xday = m.days[x]
                open_end = v if terminal else before.get(xday,np.nan)
                open_ret = open_end/before.loc[m.days[e]]-1
                index_open_proxy = tr.loc[xday]/tr.loc[m.days[e]]-1
                windows.append(dict(**meta,signal_date=d,stop=stop,net=v/last-1,index_return=bench,
                                    open_net=open_ret,index_entry_exit_close=index_open_proxy,
                                    open_excess_proxy=open_ret-index_open_proxy,
                                    fees=seg.fees.sum()/last,turnover=(seg.buy+seg.sell).sum()/last))
                last = v
            v = nav.nav.to_numpy()
            complete = status["valuation_complete"]
            idxret = tr.loc[enddate]/tr.loc[m.days[int(g.entry_idx.min())]]
            n = end-int(g.entry_idx.min())
            summary.append(dict(**meta,**status,start=nav.index[0],end=enddate,nav=v[-1],
                                cagr=v[-1]**(252/n)-1 if complete else np.nan,
                                index_cagr=idxret**(252/n)-1 if complete else np.nan,
                                mdd=(v/np.maximum.accumulate(np.r_[1.,v])[1:]-1).min()))
pd.DataFrame(events).to_csv(OUT/"events.csv",index=False)
pd.concat(stocks).to_parquet(OUT/"event_trades.parquet",index=False)
pd.DataFrame(summary).to_csv(OUT/"accounts.csv",index=False)
pd.concat(daily).to_parquet(OUT/"daily.parquet",index=False)
pd.concat(orders).to_parquet(OUT/"orders.parquet",index=False)
w = pd.DataFrame(windows)
for ref in [E1,RANK]:
    w = w.merge(w[w.model.eq(ref)][["scope","cost","signal_date","net"]].rename(columns={"net":ref}),on=["scope","cost","signal_date"],how="left",validate="m:1")
    w["delta_"+ref] = w.net-w[ref]
    keys = ["scope","cost","signal_date"]
    ref_open = w[w.model.eq(ref)].set_index(keys).open_net
    w["open_delta_"+ref] = w.open_net - ref_open.reindex(pd.MultiIndex.from_frame(w[keys])).to_numpy()
w["excess"] = w.net-w.index_return
w.to_csv(OUT/"windows.csv",index=False)

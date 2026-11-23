from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import EP,R,E,PRIVATE,split,accounts
from execution import net_account
from core import assign_deciles,sha,dump
OLD=EP/"extensions/original78_rankic_20261118"
sys.path[:0]=[str(OLD),str(PRIVATE.parent/"src")]
from model import predict
from features import compute
OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
fields=["qfq_close","qfq_open","qfq_high","qfq_low","volume","money","turnover_rate","daily_members"]
raw=[pd.read_parquet(PRIVATE/(f+".parquet")) for f in fields]
days=raw[0].index;sym=raw[0].columns
feat=compute(*raw,pd.read_parquet(PRIVATE/"market.parquet").close)
del raw
cols=pd.read_csv(OLD/"outputs/original_78_features.csv").feature.to_list()
pf=EP/"outputs/local_cache/predictions.parquet"
p=pd.read_parquet(pf,columns=["scheme","offset","signal_date","entry_date","exit_date","entry_idx","exit_idx","instrument"])
p=p[p.scheme.eq("expanding")].copy()
i=days.get_indexer(p.signal_date);j=sym.get_indexer(p.instrument)
assert min(i)>=0 and min(j)>=0
for c in cols:p[c]=feat.pop(c).to_numpy()[i,j]
del feat
p=p[p[cols].notna().mean(axis=1)>=.8].copy()
fits=[]
for q,g in p.groupby(p.signal_date.dt.to_period("Q")):
    for ref in [R,E]:
        f=OLD/"local_cache/models"/(str(q)+"_"+ref+".json")
        fits.append(f);p.loc[g.index,ref]=predict(g[cols],json.loads(f.read_text()))
orig=pd.read_parquet(EP/"extensions/intraday_reversal_20261122/results/scores.parquet")
test=p[p.offset==0].merge(orig,on=["signal_date","instrument"],validate="1:1",suffixes=("","_saved"))
assert len(test)==len(orig)==sum(p.offset==0)
for ref in [R,E]:np.testing.assert_allclose(test[ref],test[ref+"_saved"],atol=1e-10,rtol=0)
p=p.drop(columns=cols)
p.to_parquet(OUT/"point_in_time_scores.parquet",index=False)
ind=pd.read_parquet(PRIVATE/"industry.parquet");ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
catalog=ROOT.parent/"34_industry_price_observation_radar/handoff/v3_candidates_20261016"
hist={};files=[]
for name in ["early_model","momentum"]:
    files.extend(sorted((catalog/name/"periods").glob("*.csv")))
    dirs=pd.concat(pd.read_csv(f,usecols=["date","era","industry_code","industry_name","event_kind"]) for f in sorted((catalog/name/"periods").glob("*.csv")))
    hist[name]={pd.Timestamp(d):g for d,g in dirs.groupby("date")}
targets=[];notes=[]
for (phase,date),g in p.dropna(subset=["exit_date"]).groupby(["offset","signal_date"]):
    k=date.strftime("%Y%m%d")
    active=ind[ind.in_date.le(k)&(ind.out_date.isna()|ind.out_date.gt(k))]
    lookup=active[["instrument","l1_name","l3_code","l3_name"]].drop_duplicates()
    g=g.merge(lookup[~lookup.instrument.duplicated(False)],on="instrument",how="left",validate="1:1")
    for ref in [R,E]:
        g[ref+"_d"]=assign_deciles(g,ref)
        h=g[g[ref+"_d"]==10]
        targets.append(h.assign(model=ref,weight=1/len(h)))
    top=g[g[R+"_d"]==10]
    for name,history in hist.items():
        week=max(d for d in history if d<date); table=history[week]
        compatible=table.era.eq("SW2021").all() and (date-week).days<=10
        act=table[table.event_kind.isin(["NEW","UPDATE"])]
        allowed=set(zip(act.industry_code,act.industry_name)) if compatible else set()
        known=set(zip(table.industry_code,table.industry_name)) if compatible else set()
        codes=list(zip(g.l3_code,g.l3_name))
        g["observed"]=[x in allowed for x in codes];g["known"]=[x in known for x in codes]
        swaps=[]
        for sector,old in g[(g[R+"_d"]==10)&~g.observed&g.known].groupby("l1_name"):
            new=g[(g[R+"_d"]==9)&g.observed&g.l1_name.eq(sector)]
            for (_,a),(_,b) in zip(old.sort_values(R).iterrows(),new.sort_values(R,ascending=False).iterrows()):
                swaps.append((a[R]-b[R],a.instrument,b.instrument))
        chosen=set(top.instrument)
        actual=sorted(swaps)[:len(top)//5]
        for loss,old,new in actual:chosen.remove(old);chosen.add(new)
        h=g[g.instrument.isin(chosen)]
        targets.append(h.assign(model=name,weight=1/len(h)))
        notes.append(dict(offset=phase,signal_date=date,model=name,n=len(h),swaps=len(actual)))
t=pd.concat(targets)
prev=pd.read_parquet(HERE.parent/"16_industry_pool/results/targets.parquet")
ids=["signal_date","instrument","model"]
assert set(t[t.offset==0][ids].itertuples(index=False,name=None))==set(prev[ids].itertuples(index=False,name=None))
t=t[t.offset.eq(5)&((t.exit_date<=split)|(t.entry_date>=split))&(t.exit_date<=pd.Timestamp("2026-10-12"))]
t.to_parquet(OUT/"targets.parquet",index=False)
pd.DataFrame(notes).to_csv(OUT/"swaps.csv",index=False)
dump(OUT/"selection.json",dict(original_score_and_target_parity=True,hashes={str(f.relative_to(ROOT.parent)):sha(f) for f in [HERE/"PROTOCOL.md",Path(__file__),pf,OUT/"targets.parquet",*fits,*files]}))
m=accounts.Market();w=[];months=[];ac=[];orders=[]
idxraw=json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"]
bench=pd.DataFrame(idxraw["items"],columns=idxraw["fields"]);tr=bench.set_index(pd.to_datetime(bench.trade_date)).close
for (model,late),g in t.groupby(["model",t.entry_date>=split]):
    end=int(g.exit_idx.max());scope="later" if late else "primary"
    for cost,bf,sf in [("base",.001,.002),("double",.002,.004),("zero",0.,0.)]:
        d,o,st=net_account(m,g,end,"flat",bf,sf)
        meta=dict(model=model,scope=scope,cost=cost)
        d=d.set_index("date")
        idx=m.days.get_indexer(d.index)
        o["units"]=(o.buy-o.sell)/o.price
        def mat(col):
            return o.pivot(index="date",columns="instrument",values=col).reindex(index=d.index,columns=m.symbols).fillna(0.)
        u=mat("units").cumsum();u=u.mask(u.abs()<1e-12,0.)
        op=pd.DataFrame(m.marks["flat"][0][idx],index=d.index,columns=m.symbols)
        cm=pd.DataFrame(m.marks["flat"][1][idx],index=d.index,columns=m.symbols)
        if st["valuation_complete"]:cm.iloc[-1]=op.iloc[-1]
        value=(u*cm).mask(u==0,0.)
        assert value.notna().all().all()
        np.testing.assert_allclose(value.sum(axis=1)+d.cash,d.nav,atol=1e-9)
        prev=u.shift().fillna(0.)
        pre=(prev*op).mask(prev==0,0.).sum(axis=1,skipna=False)+d.cash.shift().fillna(1.)
        if cost=="base":
            orders.append(o.assign(**meta))
            profit=value-value.shift().fillna(0.)+mat("sell")-mat("buy")-mat("fee")
            per=d.index.to_period("M")
            pn=profit.groupby(per).sum().div(d.nav.shift().fillna(1.).groupby(per).first(),axis=0)
            months.append(pn.stack().loc[lambda v:v!=0].rename("pnl").reset_index().set_axis(["month","instrument","pnl"],axis=1).assign(**meta))
        for dt,h in g.groupby("signal_date"):
            entry,exit=h.entry_date.iloc[0],h.exit_date.iloc[0]
            if exit>d.index[-1]:continue
            v=d.nav.iloc[-1] if exit==m.days[end] else pre.at[exit]
            w.append(dict(**meta,signal_date=dt,net=v/pre.at[entry]-1,index=tr.at[exit]/tr.at[entry]-1))
        ac.append(dict(**meta,**st,end=d.index[-1],nav=d.nav.iloc[-1],mdd=(d.nav/np.maximum.accumulate(np.r_[1.,d.nav])[1:]-1).min(),
                    cagr=d.nav.iloc[-1]**(252/(end-idx[0]))-1 if st["valuation_complete"] else np.nan))
w=pd.DataFrame(w);keys=["scope","cost","signal_date"]
for ref in [R,E]:
    rr=w[w.model==ref].set_index(keys).net
    w["vs_"+ref]=w.net-rr.reindex(pd.MultiIndex.from_frame(w[keys])).to_numpy()
w.to_csv(OUT/"windows.csv",index=False)
pd.DataFrame(ac).to_csv(OUT/"accounts.csv",index=False)
pd.concat(orders).to_parquet(OUT/"orders.parquet",index=False)
mo=pd.concat(months);mo.to_parquet(OUT/"stock_month.parquet",index=False)
mon=mo.groupby(["scope","model","month"]).pnl.sum().reset_index()
mon["delta"]=mon.pnl-mon[mon.model==R].set_index(["scope","month"]).pnl.reindex(pd.MultiIndex.from_frame(mon[["scope","month"]])).to_numpy()
mon.to_csv(OUT/"months.csv",index=False)
print((w.groupby(["scope","model","cost"])["vs_"+R].mean().unstack()*1e4).round(2))

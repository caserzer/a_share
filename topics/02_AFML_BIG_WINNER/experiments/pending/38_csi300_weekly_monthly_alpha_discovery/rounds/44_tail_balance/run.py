from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
prev=here.parent/"38_all_phases"
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"21_dual_support"),str(prev)]
from evaluate import R,E,PRIVATE,accounts,split
from ship_action import replay_with_ship_action
from core import sha,dump
out=here/"results";out.mkdir(exist_ok=True);accounts.OUT=out
m=accounts.Market()
scorefile=prev/"results/scores.parquet";targetfile=prev/"results/targets.parquet";indfile=PRIVATE/"industry.parquet"
universe=pd.read_parquet(scorefile,columns=["signal_date","instrument","entry_idx","exit_idx"])
frozen=here.parent/"43_tail_targets/results/scores.parquet"
scores=pd.read_parquet(frozen)
indices=m.symbols.get_indexer(universe.instrument)
y=m.o[universe.exit_idx.to_numpy(),indices]/m.o[universe.entry_idx.to_numpy(),indices]-1
universe["realized"]=np.where(np.isfinite(y),y,np.nan)
grp=universe.groupby("signal_date").realized
universe["pct"]=grp.rank()/(grp.transform("count")+1)
scores=scores.merge(universe[["signal_date","instrument","pct"]],on=["signal_date","instrument"],validate="1:1")
base=pd.read_parquet(targetfile).query("model in [@R,@E]")
ind=pd.read_parquet(indfile);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
ranked=base[base.model==R].merge(scores,on=["signal_date","instrument"],validate="1:1")
variants={"direction":"direction","quiet":"quiet"}
parts=[base];events=[];audit=[]
for day,h in ranked.groupby("signal_date"):
    d=day.strftime("%Y%m%d")
    a=ind[ind.in_date.le(d)&(ind.out_date.isna()|ind.out_date.gt(d))][["instrument","l1_name"]].drop_duplicates()
    sector=h.instrument.map(a[~a.instrument.duplicated(False)].set_index("instrument").l1_name)
    # Rank sums and differences in integer half-ranks avoid artificial tie breaks.
    ar=h.avoid_left.groupby(sector).rank()
    sr=h.seek_right.groupby(sector).rank()
    h=h.assign(direction=ar+sr,quiet=ar-sr)
    e=int(h.entry_idx.iloc[0]);x=e+10
    j=m.symbols.get_indexer(h.instrument);ok=m.buy[e,j]&m.sell[x,j]&np.isfinite(m.o[e,j])&np.isfinite(m.o[x,j])
    ret=np.divide(m.o[x,j],m.o[e,j])-1
    for name,ref in variants.items():
        groups=h.groupby(sector)[ref];n=groups.transform("count")
        factor=(.5+(groups.rank()-1)/(n-1)).where(n>1,1)
        z=h.assign(weight=h.weight*factor,model=name)
        assert np.isclose(z.weight.sum(),1)
        np.testing.assert_allclose(z.weight.groupby(sector,dropna=False).sum(),h.weight.groupby(sector,dropna=False).sum())
        change=z.weight-h.weight;changed=change.abs().gt(1e-12).to_numpy()
        good=ok[changed].all()
        events.append(dict(model=name,phase=int(h.phase.iloc[0]),scope="later" if h.entry_date.iloc[0]>=split else "primary",
            signal_date=day,active=change.abs().sum()/2,complete=good,tail_priced=bool(h.pct[changed].notna().all()),
            left_change=float(change@h.pct.le(.1)) if h.pct[changed].notna().all() else np.nan,
            right_change=float(change@h.pct.ge(.9)) if h.pct[changed].notna().all() else np.nan,gross=float(change.to_numpy()[changed]@ret[changed]) if good else np.nan))
        parts.append(z.drop(columns="pct").assign(industry=sector))
t=pd.concat(parts,ignore_index=True)
t.to_parquet(out/"targets.parquet",index=False)
events=pd.DataFrame(events);events.to_csv(out/"events.csv",index=False)
rows=[];monthly=[]
inputs=[frozen,scorefile,targetfile,indfile,here/"PROTOCOL.md",Path(__file__),prev/"ship_action.py"]
for phase,g in t.groupby("phase"):
    dest=out/str(phase);dest.mkdir(exist_ok=True);accounts.OUT=dest
    replay_with_ship_action(g,dest)
    w=pd.read_csv(dest/"windows.csv");mo=pd.read_csv(dest/"months.csv")
    a=pd.read_csv(dest/"accounts.csv").set_index(["scope","cost","model"])
    assert a.valuation_complete.all()
    np.testing.assert_allclose((1+w.net).groupby([w.scope,w.cost,w.model]).prod().sort_index(),a.nav.sort_index(),atol=1e-10)
    before=prev/f"results/{phase}/windows.csv";inputs.append(before)
    old=pd.read_csv(before).query("model in [@R,@E]")
    keys=["scope","cost","signal_date","model"]
    pd.testing.assert_series_equal(w[w.model.isin([R,E])].set_index(keys).net.sort_index(),old.set_index(keys).net.sort_index(),rtol=0,atol=1e-12)
    single_file=here.parent/f"43_tail_targets/results/{phase}/windows.csv"
    inputs.append(single_file)
    single=pd.read_csv(single_file).query('model=="avoid_left" and cost=="base"')
    for scope,sub in w.groupby("scope"):
        v=sub.pivot(index="signal_date",columns=["cost","model"],values="net")
        ev=events.query('phase==@phase and scope==@scope and model=="direction"')
        seg=g[(g.entry_date>=split)==(scope=="later")]
        q=mo[(mo.scope==scope)&(mo.model=="direction")].copy()
        q=q[(q.month>str(seg.entry_date.min().to_period("M")))&(q.month<str(seg.exit_date.max().to_period("M")))]
        monthly.append(q.assign(phase=phase))
        rows.append(dict(phase=phase,scope=scope,n=len(v),left_pp=ev.left_change.mean()*100,right_pp=ev.right_change.mean()*100,active=ev.active.mean(),events=ev.complete.sum(),gross=ev.gross.mean()*1e4,
            vs_single=(v["base","direction"]-single[single.scope==scope].set_index("signal_date").net).mean()*1e4,
            vs_alt=(v["base","direction"]-v["base","quiet"]).mean()*1e4,
            vs_E=(v["base","direction"]-v["base",E]).mean()*1e4,
            **{cost:(v[cost,"direction"]-v[cost,R]).mean()*1e4 for cost in ["base","double","zero"]}))
    print("verified",phase,flush=True)
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False)
mon=pd.concat(monthly);mon.to_csv(out/"months.csv",index=False)
final=[]
for scope,g in s.groupby("scope"):
    v=mon[mon.scope==scope].pivot(index="month",columns="phase",values="delta").dropna().mean(axis=1)*1e4
    n=len(v);ix=np.random.default_rng(3842).integers(n,size=(10000,(n+2)//3))
    ix=((ix[:,:,None]+np.arange(3))%n).reshape(len(ix),-1)[:,:n]
    lo,hi=np.quantile(v.to_numpy()[ix].mean(axis=1),[.025,.975])
    final.append(dict(scope=scope,phases_positive=(g.base>0).sum(),left_pp=g.left_pp.mean(),right_pp=g.right_pp.mean(),active=g.active.mean(),gross=g.gross.mean(),base=g.base.mean(),double=g.double.mean(),zero=g.zero.mean(),vs_single=g.vs_single.mean(),vs_alt=g.vs_alt.mean(),vs_E=g.vs_E.mean(),month=v.mean(),ex3=v.drop(v.nlargest(3).index).mean(),lo=lo,hi=hi))
stats=pd.DataFrame(final);stats.to_csv(out/"aggregate.csv",index=False);print(stats.round(3).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*inputs,out/"summary.csv",out/"aggregate.csv",out/"events.csv",out/"targets.parquet"]})

from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,PRIVATE,split
from core import sha,dump
out=here/"results";r=here.parent
fs=r/"57_recent_industry_labels/results/scores.parquet";ft=r/"66_transfer_tails/results/targets.parquet";fb=r/"64_mature_group_switch/results/targets.parquet"
cfile=PRIVATE/"qfq_close.parquet";ofile=PRIVATE/"qfq_open.parquet"
scores=pd.read_parquet(fs,columns=["signal_date","instrument","entry_date","exit_date","phase",R])
op=pd.read_parquet(ofile);c=pd.read_parquet(cfile)
r5=c/c.shift(5)-1;r55=c.shift(5)/c.shift(60)-1
base=pd.concat([pd.read_parquet(ft).query('model=="avoid"'),pd.read_parquet(fb).query('model=="passive"')])
w=base.pivot(index=["signal_date","instrument"],columns="model",values="weight").fillna(0)
files=sorted((PRIVATE/"weights").glob("????-??.json"));parts=[]
for f in files:
    raw=json.loads(f.read_text()).get("data")
    if raw and raw["items"]:parts.append(pd.DataFrame(raw["items"],columns=raw["fields"]))
v=pd.concat(parts).drop_duplicates();v["date"]=pd.to_datetime(v.trade_date);v["instrument"]=v.con_code.str[-2:]+v.con_code.str[:6]
sn={dt:h.set_index("instrument").weight for dt,h in v.groupby("date") if 99<=h.weight.sum()<=101};dates=pd.DatetimeIndex(sorted(sn))
rows=[];coverage=[]
for day,h in scores.groupby("signal_date"):
    entry=h.entry_date.iloc[0];end=h.exit_date.iloc[0];phase=h.phase.iloc[0];scope=str(day.year) if day.year<2021 else ("later" if entry>=split else "primary")
    z=w.loc[day].copy();z["iw"]=sn[dates[dates.searchsorted(day)-1]].reindex(z.index)
    assert z.iw.notna().all()
    z=z.reset_index().sort_values(["iw","instrument"]).set_index("instrument");z["bucket"]=np.arange(len(z))*5//len(z)
    z["p5"]=r5.loc[day,z.index];z["p55"]=r55.loc[day,z.index];z["ret"]=op.loc[end,z.index]/op.loc[entry,z.index]-1
    known=z[["p5","p55","ret"]].apply(np.isfinite).all(axis=1).all()
    med=z.groupby("bucket")[["p5","p55"]].transform("median")
    z["state"]=np.where(z.p55.ge(med.p55),"强","弱")+z.p5.ge(med.p5).map({True:"强",False:"弱"})
    z["low"]=z.avoid.eq(0);z["delta"]=z.avoid-z.passive
    peers=z[~z.low].groupby(["bucket","state"]).ret.mean()
    z["peer"]=peers.reindex(pd.MultiIndex.from_frame(z[["bucket","state"]])).to_numpy()
    ok=known and z.peer.notna().all();meta=dict(scope=scope,phase=phase,day=day)
    coverage.append(dict(**meta,complete=ok,quotes=known,matched=z.peer.notna().all()))
    if not ok:continue
    z["mix"]=z.delta*z.peer;z["within"]=z.delta*(z.ret-z.peer)
    z["budget"]=z.passive*z.low
    p=z.groupby("state")[["budget","mix","within"]].sum().reindex(["强强","强弱","弱强","弱弱"],fill_value=0.)
    np.testing.assert_allclose((p.mix+p.within).sum(),z.delta.dot(z.ret),atol=1e-12)
    rows.append(p.reset_index().assign(**meta))
d=pd.concat(rows);cov=pd.DataFrame(coverage)
d.to_parquet(out/"state_days.parquet",index=False);cov.to_csv(out/"coverage.csv",index=False)
s=d.groupby(["scope","state","phase"])[["budget","mix","within"]].mean().groupby(level=[0,1]).mean()
s.budget*=100;s[["mix","within"]]*=1e4;s.to_csv(out/"summary.csv");print(s.round(2))
dump(out/"receipt.json",{str(f):sha(f) for f in [fs,ft,fb,cfile,ofile,*files,here/"PROTOCOL.md",Path(__file__),out/"state_days.parquet",out/"coverage.csv",out/"summary.csv"]})

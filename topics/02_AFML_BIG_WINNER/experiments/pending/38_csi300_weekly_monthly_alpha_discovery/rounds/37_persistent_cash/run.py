from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"21_dual_support")]
from evaluate import R,E,accounts,split
from account import replay
from execution import net_account
from core import sha,dump
out=here/"results";out.mkdir(exist_ok=True);accounts.OUT=out
m=accounts.Market()
inputs=[Path(__file__),here/"PROTOCOL.md"]
rows=[]
for phase in [0,5]:
    source=here.parent/"36_cash_yield_change/results"/str(phase)
    path=source/"targets.parquet";oldwin=source/"windows.csv"
    inputs.extend([path,oldwin])
    dest=out/str(phase);dest.mkdir(exist_ok=True);accounts.OUT=dest
    t=pd.read_parquet(path)
    t=t[t.model!="change"].copy()
    keys=["signal_date","instrument"]
    h=t[t.model=="cash_residual"].copy().set_index(keys)
    prior=t[t.model=="old"].set_index(keys).reindex(h.index)
    base=t[t.model==R].set_index(keys).reindex(h.index)
    assert prior.weight.notna().all() and base.weight.notna().all()
    blend=h.copy();blend["weight"]=(h.weight+prior.weight)/2;blend["model"]="blend_weights"
    avg=(h.cash_residual+h.old)/2
    group=avg.groupby([h.index.get_level_values("signal_date"),h.sector])
    n=group.transform("count")
    tilt=(.5+(group.rank()-1)/(n-1)).where(n.gt(1),1.)
    smooth=h.copy();smooth["weight"]=base.weight*tilt;smooth["model"]="smooth_scores"
    assert np.allclose(smooth.weight.groupby(level=0).sum(),1)
    for series in [blend.weight,smooth.weight]:
        g=[h.index.get_level_values("signal_date"),h.sector.fillna("UNKNOWN")]
        np.testing.assert_allclose(series.groupby(g).sum(),base.weight.groupby(g).sum())
    t=pd.concat([t,blend.reset_index(),smooth.reset_index()])
    t.to_parquet(dest/"targets.parquet",index=False)
    replay(t,dest)
    w=pd.read_csv(dest/"windows.csv")
    old=pd.read_csv(oldwin)
    pooled=w.merge(old,on=["scope","cost","signal_date","model"],validate="1:1")
    assert len(pooled)==len(old[old.model!="change"])
    np.testing.assert_allclose(pooled.net_x,pooled.net_y,atol=1e-12)
    for (model,late),g in t.groupby(["model",t.entry_date>=split]):
        scope="later" if late else "primary"
        n=g.signal_date.nunique()
        daily,_,st=net_account(m,g,int(g.exit_idx.max()),"flat",.001,.002)
        assert st["valuation_complete"]
        comp=w[(w.scope==scope)&(w.cost=="base")].pivot(index="signal_date",columns="model",values="net")
        turnover=(daily.buy+daily.sell).sum()/daily.nav.mean()/n
        rows.append(dict(phase=phase,scope=scope,model=model,windows=n,turnover=turnover,
            vs_rank=(comp[model]-comp[R]).mean()*1e4,vs_current=(comp[model]-comp.cash_residual).mean()*1e4,
            vs_blend=(comp[model]-comp.blend_weights).mean()*1e4))
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False)
print(s[s.model.isin(["cash_residual","smooth_scores","blend_weights"])].round(3).to_string(index=False))
checks=[]
for phase in [0,5]:
    dest=out/str(phase)
    w=pd.read_csv(dest/"windows.csv")
    mo=pd.read_csv(dest/"months.csv")
    for scope in ["primary","later"]:
        g=s[(s.scope==scope)&(s.phase==phase)].set_index("model")
        x=g.loc["smooth_scores"]
        sub=w[(w.scope==scope)&(w.model=="smooth_scores")]
        v=sub[sub.cost=="base"]["vs_"+R].to_numpy()
        n=len(v)
        starts=np.random.default_rng(3837).integers(n,size=(10000,(n+2)//3))
        ix=((starts[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]
        lo,hi=np.quantile(v[ix].mean(axis=1)*1e4,[.025/47,1-.025/47])
        md=mo[(mo.model=="smooth_scores")&(mo.scope==scope)].delta
        checks.append(dict(phase=phase,scope=scope,net=x.vs_rank,vs_current=x.vs_current,vs_blend=x.vs_blend,
            turnover_delta_pp=(x.turnover-g.at["cash_residual","turnover"])*100,
            double=sub[sub.cost=="double"]["vs_"+R].mean()*1e4,ex3=md.drop(md.nlargest(3).index).mean()*1e4,
            lower=lo,upper=hi))
pd.DataFrame(checks).to_csv(out/"robustness.csv",index=False)
dump(out/"receipt.json",{str(f):sha(f) for f in [*inputs,out/"summary.csv",out/"robustness.csv"]})

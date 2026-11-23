from pathlib import Path
import sys
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"02_adaptive_revision"),str(HERE.parent/"21_dual_support")]
from evaluate import R,E,split,accounts
from account import replay
from core import sha,dump,assign_deciles
OUT=HERE/"results";OUT.mkdir(exist_ok=True)
sf=HERE.parent/"17_calendar_challenge/results/point_in_time_scores.parquet"
scores=pd.read_parquet(sf)
summary=[];edits=[];inputs=[sf]
for phase,fold in [(0,"16_industry_pool"),(5,"17_calendar_challenge")]:
    orig=HERE.parent/fold/"results"
    inputs.extend([orig/"targets.parquet",orig/"windows.csv"])
    base=pd.read_parquet(orig/"targets.parquet").query("model in [@R,@E]")
    dest=OUT/str(phase);dest.mkdir(exist_ok=True)
    parts=[base]
    for (model,late),t in base.groupby(["model",base.entry_date>=split]):
        prev=set()
        for date,h in t.groupby("signal_date",sort=True):
            g=scores[(scores.offset==phase)&(scores.signal_date==date)].copy()
            dec=assign_deciles(g,model)
            ordered=g.sort_values([model,"instrument"],ascending=False)
            assert set(g.loc[dec==10,"instrument"])==set(h.instrument)
            top20=set(g.loc[dec>=9,"instrument"])
            keep=ordered[ordered.instrument.isin(prev&top20)].head(len(h))
            new=ordered[~ordered.instrument.isin(keep.instrument)].head(len(h)-len(keep))
            chosen=pd.concat([keep,new])
            assert len(chosen)==len(h) and chosen.instrument.is_unique
            prev=set(chosen.instrument)
            parts.append(chosen.assign(model="buffer_"+model,weight=1/len(h)))
            edits.append(dict(phase=phase,scope="later" if late else "primary",model=model,date=date,
                kept=len(keep),changed=len(prev-set(h.instrument))/len(h)))
    targets=pd.concat(parts,ignore_index=True)
    targets.to_parquet(dest/"targets.parquet",index=False)
    accounts.OUT=dest;replay(targets,dest)
    w=pd.read_csv(dest/"windows.csv");m=pd.read_csv(dest/"months.csv")
    old=pd.read_csv(orig/"windows.csv")
    for ref in [R,E]:
        check=w[w.model==ref].merge(old[old.model==ref],on=["cost","scope","signal_date"],validate="1:1")
        assert len(check)==len(old[old.model==ref])
        np.testing.assert_allclose(check.net_x,check.net_y,atol=1e-12)
        for scope,g in w.groupby("scope"):
            panel=g.pivot(index="signal_date",columns=["model","cost"],values="net")
            diff=panel["buffer_"+ref]-panel[ref]
            mm=m[m.scope==scope].pivot(index="month",columns="model",values="pnl")
            dm=mm["buffer_"+ref]-mm[ref]
            n=len(diff);starts=np.random.default_rng(3823).integers(n,size=(10000,(n+2)//3))
            ix=((starts[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]
            lo,hi=np.quantile(diff.base.to_numpy()[ix].mean(axis=1),[.025/32,1-.025/32])
            touched=pd.DataFrame(edits).query("phase==@phase and scope==@scope and model==@ref").changed
            summary.append(dict(phase=phase,scope=scope,model=ref,n=n,changed_weight=touched.mean(),
                base_bp=diff.base.mean()*1e4,zero_bp=diff.zero.mean()*1e4,double_bp=diff.double.mean()*1e4,
                cost_path_bp=(diff.base-diff.zero).mean()*1e4,lo_bp=lo*1e4,hi_bp=hi*1e4,
                ex3_month_bp=dm.drop(dm.nlargest(3).index).mean()*1e4))
z=pd.DataFrame(summary);z.to_csv(OUT/"summary.csv",index=False);print(z.round(3).to_string(index=False))
pd.DataFrame(edits).to_csv(OUT/"weights.csv",index=False)
dump(OUT/"receipt.json",{str(f):sha(f) for f in [*inputs,HERE/"PROTOCOL.md",Path(__file__),HERE.parent/"21_dual_support/account.py",OUT/"summary.csv"]})

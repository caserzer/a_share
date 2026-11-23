from pathlib import Path
import sys
import pandas as pd
import numpy as np

here=Path(__file__).resolve().parent
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"21_dual_support")]
from evaluate import R,E,accounts
from unittest.mock import patch
from account import replay
sys.path.insert(0,str(here.parent/"06_midwindow_refresh"))
from scheduled_execution import net_account
from core import sha,dump

out=here/"results"
out.mkdir(exist_ok=True)
accounts.OUT=out
days=accounts.Market().days
summary=[]
windows=[]
inputs=[Path(__file__),here/"PROTOCOL.md"]
for phase,folder in [(0,"16_industry_pool"),(5,"17_calendar_challenge")]:
    dest=out/str(phase)
    dest.mkdir(exist_ok=True)
    source=here.parent/folder/"results"
    inputs.extend([source/"targets.parquet",source/"windows.csv"])
    original=pd.read_parquet(source/"targets.parquet")
    calendar=original.drop_duplicates("signal_date").set_index("signal_date")
    parent={}
    plans=[]
    for model,first,second in [(R,R,R),(E,E,E),("first_week","early_model",R),("both_weeks","early_model","early_model")]:
        for half,selection in enumerate([first,second]):
            t=original[original.model==selection].copy()
            t["original_signal_date"]=t.signal_date
            assert (t.exit_idx-t.entry_idx==10).all()
            t["entry_idx"]+=5*half
            t["exit_idx"]=t.entry_idx+5
            t["signal_date"]=days[t.entry_idx-1]
            t["entry_date"]=days[t.entry_idx]
            t["exit_date"]=days[t.exit_idx]
            t["model"]=model
            parent.update(zip(t.signal_date,t.original_signal_date))
            plans.append(t)
    t=pd.concat(plans,ignore_index=True)
    t.to_parquet(dest/"targets.parquet",index=False)
    accounts.OUT=dest
    assert (t.exit_idx-t.entry_idx==5).all()
    with patch("account.net_account",net_account):
        replay(t,dest)
    short=pd.read_csv(dest/"windows.csv",parse_dates=["signal_date"])
    short["original"]=short.signal_date.map(parent)
    by=["scope","cost","original","model"]
    counts=short.groupby(by).size()
    assert (counts==2).all() and short.original.nunique()==len(calendar)
    net=(1+short.net).groupby([short[k] for k in by]).prod().sub(1).unstack()
    ref=pd.read_csv(source/"windows.csv",parse_dates=["signal_date"]).rename(columns={"signal_date":"original"})
    aligned=ref.pivot(index=by[:3],columns="model",values="net").reindex(net.index)
    assert aligned.notna().all().all()
    for label in ["early_model",R,E]:
        net["original_"+label]=aligned[label]
    idx=ref[ref.model==R].set_index(by[:3])["index"].reindex(net.index)
    net["index"]=idx
    windows.append(net.reset_index().assign(phase=phase))
    for (scope,cost),g in net.groupby(level=["scope","cost"]):
        rec=dict(phase=phase,scope=scope,cost=cost,n=len(g))
        for col in [R,E,"both_weeks","original_early_model","original_"+R,"index"]:
            rec[col]=(g.first_week-g[col]).mean()*1e4
        summary.append(rec)
pd.concat(windows).to_csv(out/"paired.csv",index=False)
s=pd.DataFrame(summary)
s.to_csv(out/"summary.csv",index=False)
print(s[s.cost=="base"].round(2).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*inputs,out/"summary.csv",out/"paired.csv"]})

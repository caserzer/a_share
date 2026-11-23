from pathlib import Path
import sys
from unittest.mock import patch
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
prev=here.parent/"38_all_phases"
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"21_dual_support"),str(here.parent/"06_midwindow_refresh"),str(prev)]
from evaluate import R,E,accounts
from account import replay
import ship_action
from scheduled_execution import net_account
from core import sha,dump
out=here/"results";out.mkdir(exist_ok=True);accounts.OUT=out
days=accounts.Market().days
src=prev/"results/targets.parquet"
t=pd.read_parquet(src)
rows=[];windows=[];inputs=[src,here/"PROTOCOL.md",Path(__file__),prev/"ship_action.py"]
for phase,g in t.groupby("phase"):
    d=out/str(phase);d.mkdir(exist_ok=True);accounts.OUT=d
    parts=[];parent={}
    for name,first,second in [(R,R,R),(E,E,E),("both","early_model","early_model"),("delayed",R,"early_model")]:
        for half,stockset in enumerate([first,second]):
            h=g[g.model==stockset].copy()
            h["decision_date"]=h.signal_date
            h["model"]=name
            h["entry_idx"]+=5*half;h["exit_idx"]=h.entry_idx+5
            h["signal_date"]=days[h.entry_idx-1];h["entry_date"]=days[h.entry_idx];h["exit_date"]=days[h.exit_idx]
            parent.update(zip(h.signal_date,h.decision_date))
            parts.append(h)
    targets=pd.concat(parts)
    targets.to_parquet(d/"targets.parquet",index=False)
    with patch("account.net_account",net_account),patch.object(ship_action,"net_account",net_account):
        ship_action.replay_with_ship_action(targets,d)
    a=pd.read_csv(d/"accounts.csv").set_index(["scope","cost","model"])
    assert a.valuation_complete.all()
    w=pd.read_csv(d/"windows.csv",parse_dates=["signal_date"])
    w["decision_date"]=w.signal_date.map(parent)
    grouped=w.groupby(["scope","cost","decision_date","model"])
    assert grouped.size().eq(2).all()
    v=grouped.net.agg(lambda x:(1+x).prod()-1).unstack()
    np.testing.assert_allclose(((1+v).groupby(level=["scope","cost"]).prod().stack()).sort_index(),a.nav.sort_index(),atol=1e-10)
    oldfile=prev/f"results/{phase}/windows.csv";inputs.append(oldfile)
    original=pd.read_csv(oldfile,parse_dates=["signal_date"]).rename(columns={"signal_date":"decision_date"}).set_index(["scope","cost","decision_date","model"])
    for ref in ["early_model",R]:
        v["original_"+ref]=original.net.xs(ref,level="model").reindex(v.index)
    assert v.notna().all().all()
    windows.append(v.reset_index().assign(phase=phase))
    for (scope,cost),z in v.groupby(level=["scope","cost"]):
        rec=dict(phase=phase,scope=scope,cost=cost,n=len(z))
        for ref in [R,E,"both","original_early_model","original_"+R]:
            rec[ref]=(z.delayed-z[ref]).mean()*1e4
        rows.append(rec)
    print("verified",phase,flush=True)
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False)
pd.concat(windows).to_csv(out/"paired.csv",index=False)
print(s[~s.phase.isin([0,5])].groupby(["scope","cost"])[[R,"both","original_early_model","original_"+R]].mean().round(3))
dump(out/"receipt.json",{str(f):sha(f) for f in [*inputs,out/"summary.csv",out/"paired.csv"]})

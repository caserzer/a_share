from pathlib import Path
import sys
import pandas as pd
import numpy as np

here=Path(__file__).resolve().parent
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"21_dual_support")]
from evaluate import R,E,accounts,split
from account import replay
from core import dump,sha
from ship_action import replay_with_ship_action
out=here/"results";path=out/"targets.parquet"
t=pd.read_parquet(path)
summary=[];monthly=[];inputs=[path,Path(__file__),here/"PROTOCOL.md",here/"ship_action.py",out/"selection_receipt.json"]
for phase,g in t.groupby("phase"):
    dest=out/str(phase);dest.mkdir(exist_ok=True);accounts.OUT=dest
    replay(g,dest)
    accounts_table=pd.read_csv(dest/"accounts.csv").set_index(["model","scope","cost"])
    w=pd.read_csv(dest/"windows.csv")
    if not accounts_table.valuation_complete.all():
        incomplete=accounts_table[~accounts_table.valuation_complete]
        assert incomplete.failure.str.contains("SH601989").all()
        incomplete.to_csv(dest/"uncorrected_break.csv")
        replay_with_ship_action(g,dest)
        accounts_table=pd.read_csv(dest/"accounts.csv").set_index(["model","scope","cost"])
        w=pd.read_csv(dest/"windows.csv")
        assert accounts_table.valuation_complete.all()
    nav=(1+w.net).groupby([w.model,w.scope,w.cost]).prod()
    np.testing.assert_allclose(nav.sort_index(),accounts_table.nav.sort_index(),atol=1e-10)
    if phase in (0,5):
        folder="16_industry_pool" if phase==0 else "17_calendar_challenge"
        orig=here.parent/folder/"results/windows.csv";inputs.append(orig)
        keys=["model","scope","cost","signal_date"]
        pd.testing.assert_series_equal(w.set_index(keys).net.sort_index(),pd.read_csv(orig).set_index(keys).net.sort_index(),atol=1e-12,rtol=0)
    mon=pd.read_csv(dest/"months.csv")
    for scope,h in w.groupby("scope"):
        seg=g[(g.entry_date>=split)==(scope=="later")]
        n=seg.signal_date.nunique()
        assert len(h)==n*12
        series=h.pivot(index="signal_date",columns=["model","cost"],values="net")
        candidate=series["early_model","base"]
        q=mon[(mon.model=="early_model")&(mon.scope==scope)].copy()
        q=q[(q.month>str(seg.entry_date.min().to_period("M")))&(q.month<str(seg.exit_date.max().to_period("M")))]
        monthly.append(q.assign(phase=phase))
        a=accounts_table.loc[("early_model",scope,"base")]
        rec=dict(phase=phase,scope=scope,n=n,cagr=a.cagr,mdd=a.mdd,
            vs_E=(candidate-series[E,"base"]).mean()*1e4,
            vs_momentum=(candidate-series["momentum","base"]).mean()*1e4,
            vs_index=(candidate.to_numpy()-h[(h.model=="early_model")&(h.cost=="base")].sort_values("signal_date")["index"].to_numpy()).mean()*1e4)
        for cost in ["base","double","zero"]:
            rec[cost]=(series["early_model",cost]-series[R,cost]).mean()*1e4
        summary.append(rec)
    print("verified phase",phase,flush=True)
s=pd.DataFrame(summary);s.to_csv(out/"summary.csv",index=False)
monthly=pd.concat(monthly);monthly.to_csv(out/"monthly_complete.csv",index=False)
aggregate=[];aligned=[]
for scope,g in s[~s.phase.isin([0,5])].groupby("scope"):
    m=monthly[(monthly.scope==scope)&monthly.phase.isin(g.phase)].pivot(index="month",columns="phase",values="delta").dropna()
    assert m.shape[1]==8
    v=m.mean(axis=1)*1e4
    aligned.append(v.rename("bp").reset_index().assign(scope=scope))
    rng=np.random.default_rng(3838);n=len(v)
    starts=rng.integers(n,size=(20000,(n+2)//3))
    ix=((starts[:,:,None]+np.arange(3))%n).reshape(len(starts),-1)[:,:n]
    lo,hi=np.quantile(v.to_numpy()[ix].mean(axis=1),[.025,.975])
    aggregate.append(dict(scope=scope,phases=len(g),positive=int(g.base.gt(0).sum()),mean_bp=g.base.mean(),double_bp=g.double.mean(),zero_bp=g.zero.mean(),
        vs_E=g.vs_E.mean(),vs_index=g.vs_index.mean(),vs_momentum=g.vs_momentum.mean(),months=n,monthly_bp=v.mean(),
        low=lo,high=hi,ex3_monthly_bp=v.drop(v.nlargest(3).index).mean(),top3=",".join(v.nlargest(3).index)))
a=pd.DataFrame(aggregate);a.to_csv(out/"aggregate.csv",index=False);pd.concat(aligned).to_csv(out/"aligned_months.csv",index=False)
dump(out/"verification.json",dict(phase_0_5_target_score_and_account_parity=True,all_phases_nav_compound=True,
    hashes={str(f):sha(f) for f in [*inputs,out/"summary.csv",out/"monthly_complete.csv",out/"aggregate.csv",out/"aligned_months.csv"]}))
print(a.round(3).to_string(index=False))

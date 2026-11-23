from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent;out=here/"results";scope=sys.argv[1]
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"64_mature_group_switch")]
from evaluate import PRIVATE,split,accounts,R,E
from account import setup,replay as original
from engine import replay
from core import sha,dump
accounts.OUT=out
if scope.startswith("2018"):
    mode="half_archive" if scope=="2018_half" else "flat_archive";m=accounts.Market();actions=[]
    early=here.parent/"71_2018_concentration/results"
    for e in pd.read_parquet(early/mode/"suspensions.parquet").itertuples():
        j=m.symbols.get_loc(e.instrument);start=m.days.get_loc(e.start);end=m.days.get_loc(e.resume)
        for mat in m.marks["flat"]:mat[start+20:end,j]=e.last_close*(.5 if scope=="2018_half" else 1.)
    for e in pd.read_csv(early/(mode+"_prices.csv")).itertuples():m.marks["flat"][1][m.days.get_loc(e.date),m.symbols.get_loc(e.instrument)]=e.adjusted_mark
else:m,actions=setup("half" if scope=="2020_half" else "flat")
r1=here.parent/"81_margin_subindustry/results";r2=here.parent/"72_passive_weighting/results"
parts=[]
baseline="--baseline" in sys.argv
paths=[("stock_weight",r1/"targets.parquet"),("drift_group",r2/"targets.parquet")]
if baseline:
    source=here.parent/"71_2018_concentration/results/baseline.parquet" if scope.startswith("2018") else here.parent/("51_earlier_replication/results/targets.parquet" if scope[:1]=="2" else "50_training_support/results/targets.parquet")
    paths=[(name,source) for name in [R,E]]
for model,path in paths:
    g=pd.read_parquet(path,filters=[("model","=",model)])
    if "year" not in g:g["year"]=g.signal_date.dt.year
    g=g[g.year.eq(int(scope[:4]))] if scope[:1]=="2" else g[(g.year>=2021)&(g.entry_date.ge(split)==(scope=="later"))]
    parts.append(g)
bench=pd.read_parquet(PRIVATE/"market.parquet").close
if scope in ["primary","later"]:
    import json
    b=json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"];v=pd.DataFrame(b["items"],columns=b["fields"]);bench=v.set_index(pd.to_datetime(v.trade_date)).close
windows=[];monthly=[];accounts_rows=[]
for (phase,model),g in pd.concat(parts).groupby(["phase","model"]):
    p=g.drop_duplicates("entry_idx").sort_values("entry_idx")
    for offset in range(2):
        selected=p.iloc[offset:];selected=selected.iloc[:2*(len(selected)//2)]
        assert len(selected)>0 and np.array_equal(selected.exit_idx.to_numpy()[:-1],selected.entry_idx.to_numpy()[1:])
        plan=g[g.entry_idx.isin(selected.entry_idx)]
        starts=selected.iloc[::2];ends=selected.iloc[1::2];second_exit=dict(zip(starts.entry_idx,ends.exit_idx))
        long=plan[plan.entry_idx.isin(starts.entry_idx)].copy();long["exit_idx"]=long.entry_idx.map(second_exit);long["exit_date"]=m.days[long.exit_idx]
        for clock,h in [(10,plan),(20,long)]:
            for cost,bf,sf in [("base",.001,.002),("zero",0.,0.),("double",.002,.004)]:
                w,d,fail=replay(m,actions,h,bf,sf);assert fail is None
                if clock==10 and cost=="base" and offset==0:
                    av,ad,af=original(m,actions,h,bf,sf);assert af is None
                    np.testing.assert_allclose(d.nav,ad.nav,atol=1e-12,rtol=0)
                meta=dict(scope=scope,phase=phase,offset=offset,model=model,clock=clock,cost=cost)
                returns=w.net.to_numpy() if clock==20 else (1+w.net.to_numpy()).reshape(-1,2).prod(axis=1)-1
                np.testing.assert_allclose((1+returns).prod(),d.nav.iloc[-1],atol=1e-10)
                eff=bench.loc[ends.exit_date].to_numpy()/bench.loc[starts.entry_date].to_numpy()-1
                windows.append(pd.DataFrame(dict(signal_date=starts.signal_date.to_numpy(),net=returns,benchmark=eff,**meta)))
                accounts_rows.append(dict(**meta,nav=d.nav.iloc[-1],mdd=(d.nav/d.nav.cummax().clip(lower=1)-1).min(),turnover=w.traded.mean()*(20/clock),fee=w.fee.mean()*(20/clock)))
                if cost=="base":
                    b=(1+d.nav.pct_change().fillna(d.nav.iloc[0]-1)).groupby(d.date.dt.to_period("M")).prod().iloc[1:-1]-1
                    monthly.append(b.rename("net").rename_axis("month").reset_index().assign(**meta))
for data,file in [(pd.concat(windows),"windows"),(pd.concat(monthly),"months"),(pd.DataFrame(accounts_rows),"accounts")]:data.to_parquet(out/(scope+("_baseline_" if baseline else "_")+file+".parquet"),index=False)

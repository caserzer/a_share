from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent;out=here/"results";scope=sys.argv[1]
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"64_mature_group_switch")]
from evaluate import PRIVATE,split,accounts,R,E
from account import setup
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location("variable_expiry_engine",here.parent/"82_monthly_peer_margin/engine.py")
engine=module_from_spec(spec);spec.loader.exec_module(engine)
replay=engine.replay
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
src=here.parent/"98_d10_frequency/results/targets.parquet"
t=pd.read_parquet(src,filters=[("model","in",["original","overlay"])])
t=t[t.year.eq(int(scope[:4]))] if scope[:1]=="2" else t[(t.year>=2021)&(t.entry_date.ge(split)==(scope=="later"))]
windows=[];daily=[];status=[]
for phase,g in t.groupby("phase"):
    a=g[g.model=="original"].sort_values(["entry_idx","instrument"])
    b=g[g.model=="overlay"].sort_values(["entry_idx","instrument"])
    assert np.array_equal(a[["entry_idx","instrument"]],b[["entry_idx","instrument"]])
    assert (a.exit_idx-a.entry_idx).eq(10).all()
    dates=a.drop_duplicates("entry_idx").signal_date.to_numpy()
    for name,first,second in [("first",b,a),("second",a,b),("both",b,b),("neutral",a,a)]:
        h1=first.assign(exit_idx=first.entry_idx+5,exit_date=m.days[first.entry_idx+5])
        h2=second.assign(entry_idx=second.entry_idx+5,entry_date=m.days[second.entry_idx+5])
        plan=pd.concat([h1,h2]).sort_values(["entry_idx","instrument"])
        for cost,bf,sf in [("base",.001,.002),("zero",0.,0.),("double",.002,.004)]:
            w,nav,fail=replay(m,actions,plan,bf,sf)
            assert fail is None,(phase,name,cost,fail)
            assert np.array_equal(w.signal_date.to_numpy(),np.repeat(dates,2))
            half=w.net.to_numpy().reshape(-1,2)
            factor=1+half[:,0]
            fee=w.fee.to_numpy().reshape(-1,2)
            turnover=w.traded.to_numpy().reshape(-1,2)
            agg=pd.DataFrame(dict(signal_date=dates,net=(1+half).prod(axis=1)-1,first_net=half[:,0],second_net=half[:,1],fee=fee[:,0]+factor*fee[:,1],traded=turnover[:,0]+factor*turnover[:,1]))
            meta=dict(scope=scope,phase=phase,model=name,cost=cost)
            np.testing.assert_allclose((1+agg.net).prod(),nav.nav.iloc[-1],atol=1e-10)
            windows.append(agg.assign(**meta))
            if cost=="base":daily.append(nav.assign(**meta))
            status.append(dict(**meta,failure=fail,end=nav.date.iloc[-1],nav=nav.nav.iloc[-1]))
pd.concat(windows).to_parquet(out/(scope+"_windows.parquet"),index=False)
pd.concat(daily).to_parquet(out/(scope+"_daily.parquet"),index=False)
pd.DataFrame(status).to_csv(out/(scope+"_accounts.csv"),index=False)

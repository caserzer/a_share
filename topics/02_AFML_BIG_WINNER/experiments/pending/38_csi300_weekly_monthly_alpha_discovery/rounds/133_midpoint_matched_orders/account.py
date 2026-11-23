from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent;out=here/"results";scope=sys.argv[1]
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"64_mature_group_switch")]
from evaluate import PRIVATE,split,accounts,R,E
from account import setup
from importlib.util import spec_from_file_location,module_from_spec
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
src=here.parent/"128_rank_crossing/results/targets.parquet"
t=pd.read_parquet(src,filters=[("model","in",["original","unconfirmed"])])
t=t[t.year.eq(int(scope[:4]))] if scope[:1]=="2" else t[(t.year>=2021)&(t.entry_date.ge(split)==(scope=="later"))]
signals=pd.read_parquet(out/"allocations.parquet")
windows=[];daily=[];status=[];audit=[]
for phase,g in t.groupby("phase"):
    original=g[g.model=="original"]; retained=g[g.model=="unconfirmed"]
    q=signals[(signals.phase==phase)&signals.entry_idx.isin(original.entry_idx)]
    for name,plan in [("original",original),("reverse",retained),("uniform",retained),("adaptive",retained)]:
        moves={}
        if name!="original":
            z=q[q[name]>0]
            for mid,group in z.groupby("mid_idx"):
                moves[mid]=(m.symbols.get_indexer(group.leaver),m.symbols.get_indexer(group.entrant),group[name].to_numpy(dtype=float))
        for cost,bf,sf in [("base",.001,.002),("zero",0.,0.),("double",.002,.004)]:
            w,nav,fail,counts=replay(m,actions,plan,bf,sf,moves)
            assert fail is None,(phase,name,cost,fail)
            meta=dict(scope=scope,phase=phase,model=name,cost=cost)
            windows.append(w.assign(**meta))
            if cost=="base":
                daily.append(nav.assign(**meta))
                audit.extend(dict(mid_idx=i,planned=n,filled=k,**meta) for i,n,k in counts)
            status.append(dict(**meta,failure=fail,end=nav.date.iloc[-1],nav=nav.nav.iloc[-1]))
pd.concat(windows).to_parquet(out/(scope+"_windows.parquet"),index=False)
pd.concat(daily).to_parquet(out/(scope+"_daily.parquet"),index=False)
pd.DataFrame(status).to_csv(out/(scope+"_accounts.csv"),index=False)
pd.DataFrame(audit).to_csv(out/(scope+"_fills.csv"),index=False)

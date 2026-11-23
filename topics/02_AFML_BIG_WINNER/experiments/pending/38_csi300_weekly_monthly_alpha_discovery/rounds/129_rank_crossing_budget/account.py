from pathlib import Path
from importlib.util import module_from_spec,spec_from_file_location
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
src=here.parent/"64_mature_group_switch/account.py"
spec=spec_from_file_location("group_engine",src);engine=module_from_spec(spec);spec.loader.exec_module(engine)
out=here/"results";scope=sys.argv[1]
if not scope.startswith("2018"):
    engine.run_scope(scope,out)
else:
    engine.accounts.OUT=out;m=engine.accounts.Market()
    early=here.parent/"71_2018_concentration/results"
    mode="half_archive" if scope=="2018_half" else "flat_archive"
    for event in pd.read_parquet(early/mode/"suspensions.parquet").itertuples():
        j=m.symbols.get_loc(event.instrument);a=m.days.get_loc(event.start);b=m.days.get_loc(event.resume)
        assert b-a==event.days and not (m.buy[a:b,j]|m.sell[a:b,j]).any()
        for mat in m.marks["flat"]:
            assert np.isnan(mat[a+20:b,j]).all()
            mat[a+20:b,j]=event.last_close*(.5 if scope=="2018_half" else 1.)
    for v in pd.read_csv(early/(mode+"_prices.csv")).itertuples():
        j=m.symbols.get_loc(v.instrument);i=m.days.get_loc(v.date)
        assert np.isnan(m.marks["flat"][1][i,j])
        m.marks["flat"][1][i,j]=v.adjusted_mark
    t=pd.read_parquet(out/"targets.parquet",filters=[("year","=",2018)])
    windows=[];daily=[];status=[]
    for (phase,name),g in t.groupby(["phase","model"]):
        for cost,bf,sf in [("base",.001,.002),("zero",0.,0.),("double",.002,.004)]:
            w,d,fail=engine.replay(m,[],g,bf,sf);assert fail is None
            meta=dict(scope=scope,phase=phase,model=name,cost=cost)
            windows.append(w.assign(**meta))
            if cost=="base":daily.append(d.assign(**meta))
            status.append(dict(**meta,end=d.date.iloc[-1],nav=d.nav.iloc[-1],failure=fail))
    pd.concat(windows).to_parquet(out/(scope+"_windows.parquet"),index=False)
    pd.concat(daily).to_parquet(out/(scope+"_daily.parquet"),index=False)
    pd.DataFrame(status).to_csv(out/(scope+"_accounts.csv"),index=False)

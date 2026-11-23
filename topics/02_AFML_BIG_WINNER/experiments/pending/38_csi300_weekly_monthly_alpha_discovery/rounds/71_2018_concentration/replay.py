from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"64_mature_group_switch")]
from evaluate import accounts,PRIVATE
from account import replay
from core import dump,sha
out=here/"results";accounts.OUT=out
mode=sys.argv[1]
m=accounts.Market();target=out/"targets.parquet";t=pd.read_parquet(target)
sf=PRIVATE/"suspensions/daily.parquet";log=pd.read_parquet(sf).query('suspend_type=="S"')
log=log[log.suspend_timing.isna()|log.suspend_timing.eq("")].copy();log["date"]=pd.to_datetime(log.trade_date)
halts={k:set(v.date) for k,v in log.groupby("ts_code")}
evidence=[]
for j,name in enumerate(m.symbols):
    bad=~np.isfinite(m.c[:,j]);indices=np.flatnonzero(np.diff(np.r_[False,bad,False]))
    for start,end in indices.reshape(-1,2):
        if start==0 or end==len(bad) or end-start<=20:continue
        if m.days[start].year>2018 or m.days[end].year<2018:continue
        days=m.days[start:end];symbol=name[2:]+"."+name[:2]
        if not set(days)<=halts.get(symbol,set()):continue
        if np.isfinite(m.o[start:end,j]).any() or (m.buy[start:end,j]|m.sell[start:end,j]).any():continue
        if not np.isfinite(m.o[end,j]) or not np.isfinite(m.c[start-1,j]):continue
        evidence.append(dict(instrument=name,start=days[0],end=days[-1],resume=m.days[end],days=len(days),last_close=m.c[start-1,j]))
        if mode!="original":
            for mat in m.marks["flat"]:
                assert np.isnan(mat[start+20:end,j]).all()
                mat[start+20:end,j]=m.c[start-1,j]*(.5 if mode.startswith("half") else 1.)
sources=[]
if mode.endswith(("_archive","_csv")):
    root=next(p for p in here.parents if (p/"topics/01_askhare_qlib").is_dir())
    csv=root/"topics/01_askhare_qlib/Explore7/data/raw/akshare/day/raw/SH600297.csv"
    archive=here.parents[2]/"28_literature_guided_tail_risk/outputs/local_cache/recovered_prices/SH600297_raw.parquet"
    sources=[csv,archive]
    first=pd.read_csv(csv,index_col="日期",parse_dates=True)
    second=pd.read_parquet(archive);second.index=pd.to_datetime(second.date)
    symbol="SH600297";j=m.symbols.get_loc(symbol);events=[]
    known={k:pd.read_parquet(PRIVATE/(k+".parquet"),columns=[symbol])[symbol] for k in ["open","high","low","qfq_high","qfq_low"]}
    for day in pd.to_datetime(["2018-04-25","2018-06-22"]):
        idx=m.days.get_loc(day);a=first.loc[day];b=second.loc[day]
        np.testing.assert_allclose(a[["开盘","最高","最低"]].astype(float),b[["open","high","low"]].astype(float))
        np.testing.assert_allclose([b.open,b.high,b.low],[known[k].loc[day] for k in ["open","high","low"]])
        factor=m.o[idx,j]/b.open
        np.testing.assert_allclose([factor*b.high,factor*b.low],[known[k].loc[day] for k in ["qfq_high","qfq_low"]],rtol=1e-8)
        assert np.isnan(m.marks["flat"][1][idx,j]) and b.low<=b.close<=b.high
        raw_close=a["收盘"] if mode.endswith("_csv") else b.close
        assert b.low<=raw_close<=b.high
        mark=raw_close*factor;m.marks["flat"][1][idx,j]=mark
        events.append(dict(date=day,instrument=symbol,csv_close=a["收盘"],archive_close=b.close,raw_close=raw_close,adjusted_mark=mark))
    pd.DataFrame(events).to_csv(out/(mode+"_prices.csv"),index=False)
rows=[];daily=[];status=[];bench=pd.read_parquet(PRIVATE/"market.parquet").close
for (phase,name),g in t.groupby(["phase","model"]):
    for cost,bf,fee in [("base",.001,.002),("zero",0,0),("double",.002,.004)]:
        w,d,fail=replay(m,[],g,bf,fee)
        plans=g.drop_duplicates("signal_date").set_index("signal_date");plans["benchmark"]=bench.loc[plans.exit_date].to_numpy()/bench.loc[plans.entry_date].to_numpy()-1
        attrs=dict(phase=phase,model=name,cost=cost)
        if not w.empty:rows.append(w.join(plans.benchmark,on="signal_date").assign(**attrs))
        if cost=="base":daily.append(d.assign(**attrs))
        status.append(dict(**attrs,complete=fail is None,end=d.date.iloc[-1],nav=d.nav.iloc[-1],failure=str(fail)))
dest=out/mode;dest.mkdir(exist_ok=True)
for data,file in [(pd.concat(rows),"windows"),(pd.concat(daily),"daily"),(pd.DataFrame(status),"accounts"),(pd.DataFrame(evidence),"suspensions")]:
    data.to_parquet(dest/(file+".parquet"),index=False)
print(mode,pd.DataFrame(status).failure.value_counts().head(8).to_dict())
dump(dest/"receipt.json",{str(f):sha(f) for f in [target,sf,*sources,here/"PROTOCOL.md",here.parent/"64_mature_group_switch/account.py",Path(accounts.__file__),Path(__file__),*[PRIVATE/(k+".parquet") for k in ["market","daily_members","qfq_open","qfq_close","open","opening_trade_status_v2","limits/daily"]],*sorted(dest.glob("*.parquet"))]})

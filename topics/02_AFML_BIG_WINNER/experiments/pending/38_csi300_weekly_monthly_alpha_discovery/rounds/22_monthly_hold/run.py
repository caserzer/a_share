from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE.parent/"02_adaptive_revision"),str(HERE.parent/"06_midwindow_refresh")]
from evaluate import R,E,accounts,PRIVATE,split
from scheduled_execution import net_account
from core import dump,sha
OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
m=accounts.Market()
idx=json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"]
b=pd.DataFrame(idx["items"],columns=idx["fields"]);tr=b.set_index(pd.to_datetime(b.trade_date)).close
windows=[];summary=[];months=[];targets=[];orders=[];inputs=[]
for phase,folder in [(0,"16_industry_pool"),(5,"17_calendar_challenge")]:
    path=HERE.parent/folder/"results/targets.parquet";inputs.append(path)
    t=pd.read_parquet(path).query("model in [@R,@E]")
    for (ref,late),g in t.groupby(["model",t.entry_date>=split]):
        scope="later" if late else "primary"
        cal=g.drop_duplicates("signal_date").sort_values("signal_date")
        cal=cal.iloc[:len(cal)//2*2]
        assert np.all(cal.entry_idx.to_numpy()[1:]==cal.exit_idx.to_numpy()[:-1])
        blocks=list(zip(cal.iloc[::2].itertuples(),cal.iloc[1::2].itertuples()))
        end=int(cal.exit_idx.max())
        keep=g[g.signal_date.isin(cal.iloc[::2].signal_date)].copy()
        keep["exit_idx"]+=10;keep["exit_date"]=m.days[keep.exit_idx]
        for horizon,plan in [(20,keep),(10,g[g.signal_date.isin(cal.signal_date)])]:
            meta=dict(phase=phase,scope=scope,model=ref,horizon=horizon)
            targets.append(plan.assign(**meta))
            for cost,bf,sf in [("base",.001,.002),("double",.002,.004),("zero",0.,0.)]:
                d,o,status=net_account(m,plan,end,"flat",bf,sf)
                d=d.set_index("date");ii=m.days.get_indexer(d.index)
                info=meta|dict(cost=cost)
                o["units"]=(o.buy-o.sell)/o.price
                units=o.pivot(index="date",columns="instrument",values="units").reindex(index=d.index,columns=m.symbols).fillna(0.).cumsum()
                units=units.mask(units.abs()<1e-12,0)
                op=pd.DataFrame(m.marks["flat"][0][ii],index=d.index,columns=m.symbols)
                cm=pd.DataFrame(m.marks["flat"][1][ii],index=d.index,columns=m.symbols)
                if status["valuation_complete"]:cm.iloc[-1]=op.iloc[-1]
                val=(units*cm).mask(units==0,0)
                assert val.notna().all().all()
                np.testing.assert_allclose(val.sum(axis=1)+d.cash,d.nav,atol=1e-9)
                yesterday=units.shift().fillna(0)
                pre=(yesterday*op).mask(yesterday==0,0).sum(axis=1,skipna=False)+d.cash.shift().fillna(1)
                rets=[]
                for a,b in blocks:
                    if b.exit_date>d.index[-1]:continue
                    last=d.nav.iloc[-1] if b.exit_idx==end else pre.at[b.exit_date]
                    ret=last/pre.at[a.entry_date]-1;rets.append(ret)
                    windows.append(info|dict(date=a.signal_date,middle=b.entry_date,exit=b.exit_date,net=ret,
                             first10=pre.at[b.entry_date]/pre.at[a.entry_date]-1,second10=last/pre.at[b.entry_date]-1,
                             index=tr.at[b.exit_date]/tr.at[a.entry_date]-1))
                if status["valuation_complete"]:assert abs(np.prod(1+np.array(rets))-d.nav.iloc[-1])<1e-9
                if cost=="base":
                    orders.append(o.assign(**info))
                    for k,v in d.nav.pct_change().fillna(d.nav.iloc[0]-1).groupby(d.index.to_period("M")):
                        months.append(info|dict(month=str(k),net=(1+v).prod()-1))
                summary.append(info|dict(**status,n=len(rets),nav=d.nav.iloc[-1],mdd=(d.nav/np.maximum.accumulate(np.r_[1.,d.nav])[1:]-1).min(),
                     turnover=((d.buy+d.sell)/d.nav.shift().fillna(1)).sum()))
w=pd.DataFrame(windows);keys=["phase","scope","model","cost","date"]
z=w[w.horizon==20].merge(w[w.horizon==10],on=keys,suffixes=("_hold","_refresh"),validate="1:1")
z["delta"]=z.net_hold-z.net_refresh;z["excess"]=z.net_hold-z.index_hold
mth=pd.DataFrame(months)
mon=mth.pivot(index=["phase","scope","model","month"],columns="horizon",values="net")
mon["delta"]=mon[20]-mon[10]
rows=[]
for (phase,scope,model),g in z.groupby(["phase","scope","model"]):
    b=g[g.cost=="base"];q=b.delta.to_numpy();n=len(q)
    starts=np.random.default_rng(38).integers(n,size=(10000,(n+2)//3))
    ix=((starts[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]
    ci=np.quantile(q[ix].mean(axis=1),[.025/30,1-.025/30])
    mm=mon.loc[(phase,scope,model),"delta"]
    rows.append(dict(phase=phase,scope=scope,model=model,n=n,net_bp=q.mean()*1e4,lo_bp=ci[0]*1e4,hi_bp=ci[1]*1e4,
        zero_bp=g[g.cost=="zero"].delta.mean()*1e4,double_bp=g[g.cost=="double"].delta.mean()*1e4,
        ex3_month_bp=mm.drop(mm.nlargest(3).index).mean()*1e4,vs_index_bp=b.excess.mean()*1e4))
s=pd.DataFrame(rows);print(s.round(2).to_string(index=False))
s.to_csv(OUT/"summary.csv",index=False);z.to_csv(OUT/"windows.csv",index=False)
mon.to_csv(OUT/"months.csv");pd.DataFrame(summary).to_csv(OUT/"accounts.csv",index=False)
pd.concat(orders).to_parquet(OUT/"orders.parquet",index=False)
pd.concat(targets).to_parquet(OUT/"targets.parquet",index=False)
dump(OUT/"receipt.json",{str(f):sha(f) for f in [*inputs,HERE/"PROTOCOL.md",Path(__file__),OUT/"summary.csv"]})

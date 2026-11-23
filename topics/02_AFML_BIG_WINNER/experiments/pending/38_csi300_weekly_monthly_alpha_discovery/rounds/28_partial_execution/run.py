from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];OUT=HERE/"results";OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import R,E,PRIVATE,accounts,split
from core import sha,dump
from execution import net_account as legacy

accounts.OUT=OUT;m=accounts.Market()
old,new=m.symbols.get_indexer(["SH600837","SH601211"])
assert min(old,new)>=0
d=m.days;start=d.get_loc("2025-03-04");listing=d.get_loc("2025-03-17")
raw_open=pd.read_parquet(PRIVATE/"open.parquet");raw_close=pd.read_parquet(PRIVATE/"close.parquet")
old_raw=raw_close.iloc[:start,old].dropna().iloc[-1] if raw_close.columns.equals(m.symbols) else raw_close["SH600837"].iloc[:start].dropna().iloc[-1]
last=raw_close["SH600837"].iloc[:start].last_valid_index()
old_factor=m.c[d.get_loc(last),old]/old_raw
rate=.62*old_factor*raw_open.at[d[listing],"SH601211"]/m.o[listing,new]
action=dict(listing=listing,old=old,new=new,units_per_old=rate,old_factor=old_factor)
om,cm=m.marks["flat"]
assert not m.buy[start:listing,old].any() and not m.sell[start:listing,old].any()
for name in ["claim","last_close"]:
    o,c=om.copy(),cm.copy()
    for mat,raw in [(o,raw_open),(c,raw_close)]:
        mat[start:listing,old]=raw["SH601211"].iloc[start:listing].to_numpy()*old_factor*.62 if name=="claim" else old_raw*old_factor
        assert np.isfinite(mat[start:listing,old]).all()
    m.marks[name]=(o,c)
path=HERE.parent/"16_industry_pool/results/targets.parquet";targets=pd.read_parquet(path)
b=json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"]
idx=pd.DataFrame(b["items"],columns=b["fields"]);tr=idx.set_index(pd.to_datetime(idx.trade_date)).close
moneyfile=PRIVATE/"money.parquet"
adv=pd.read_parquet(moneyfile).reindex(index=m.days,columns=m.symbols).rolling(20).mean().shift().to_numpy()
ref=HERE.parent/"26_merger_continuity/results"
gold=pd.read_parquet(ref/"daily.parquet")
oldw=pd.read_csv(ref/"windows.csv",parse_dates=["signal_date"])
from accounts import buy_amounts
BF,SF=.001,.002

def account(g,capital,unknown):
    plans={k:z for k,z in g.groupby("entry_idx")}
    s=min(plans);last=int(g.exit_idx.max())
    om,cm=m.marks["claim"]
    u=np.zeros(m.n);pending=np.zeros(m.n);cash=1.
    records=[];fills=[];bound={}
    for i in range(s,last+1):
        if i==listing:
            for vector in [u,pending]:
                vector[new]+=vector[old]*rate;vector[old]=0.
        if i in plans or i==last:
            pending=u.copy()
        pre=np.nan
        buy=sell=fee=short_buy=short_sell=0.
        if pending.any() or i in plans or i==last:
            held=u>0
            if not np.isfinite(om[i,held]).all():
                raise ValueError(("unknown held open",m.days[i],m.symbols[held&~np.isfinite(om[i])].tolist()))
            px=np.nan_to_num(om[i]);pre=cash+np.dot(u,px)
            sales=pending*px*m.sell[i]
            purchase=np.zeros(m.n)
            if i in plans:
                h=plans[i];w=np.zeros(m.n);w[m.symbols.get_indexer(h.instrument)]=h.weight
                locked=(u>0)&(sales==0)
                purchase=buy_amounts(w*m.buy[i]*m.members[i-1]*~locked,cash+sales.sum()*(1-SF),np.dot(u[locked],px[locked]),BF)
                bound[i]=pre
            overlap=np.minimum(sales,purchase)
            want_buy=purchase-overlap;want_sell=sales-overlap
            known=np.isfinite(adv[i])&(adv[i]>0)
            lim=np.full(m.n,np.inf) if capital==0 else np.where(known,.01*adv[i]/capital,0. if unknown=="block" else np.inf)
            sb=np.minimum(want_sell,lim);bb=np.minimum(want_buy,lim)
            available=cash+sb.sum()*(1-SF)
            if bb.sum()*(1+BF)>available:
                bb*=max(0.,available)/(bb.sum()*(1+BF))
            buy=bb.sum();sell=sb.sum();fee=buy*BF+sell*SF
            short_buy=(want_buy-bb).sum();short_sell=(want_sell-sb).sum()
            trade=(bb+sb)>0
            assert np.all((bb+sb)<=lim+1e-12)
            for j in np.flatnonzero(trade):
                fills.append((m.days[i],m.symbols[j],bb[j],sb[j],px[j],lim[j]))
            cash+=sell-buy-fee
            assert cash>=-1e-10
            if abs(cash)<1e-12:cash=0.
            # Overlap is retained for a new cycle; only the unsold excess remains due.
            delta=np.divide(sb+overlap,px,out=np.zeros(m.n),where=px>0)
            pending=np.maximum(0.,pending-delta);pending[pending<1e-14]=0.
            u+=np.divide(bb-sb,px,out=np.zeros(m.n),where=px>0)
            assert u.min()>=-1e-12
            u[u<1e-14]=0.
            np.testing.assert_array_less(pending,u+1e-12)
            assert abs(cash+np.dot(u,px)-(pre-fee))<1e-9
        mark=om[i] if i==last else cm[i]
        held=u>0
        assert np.isfinite(mark[held]).all()
        nav=cash+np.dot(u[held],mark[held])
        records.append(dict(date=m.days[i],nav=nav,cash=cash,buy=buy,sell=sell,fees=fee,unfilled_buy=short_buy,unfilled_sell=short_sell))
    df=pd.DataFrame(records);bound[last]=df.nav.iloc[-1]
    returns=[dict(signal_date=h.signal_date,entry_date=h.entry_date,net=bound[h.exit_idx]/bound[h.entry_idx]-1) for h in g.drop_duplicates("signal_date").itertuples()]
    assert abs(np.prod([1+a["net"] for a in returns])-nav)<1e-9
    return df,pd.DataFrame(returns),pd.DataFrame(fills,columns=["date","instrument","buy","sell","price","limit"])

windows=[];summaries=[];orders=[];daily=[]
for model,g in targets.groupby("model"):
    for capital,missing in [(0,"unlimited")]+[(k,v) for k in [1e6,1e7,1e8,1e9] for v in ["block","allow"]]:
        z,w,o=account(g,capital,missing)
        meta=dict(model=model,capital=capital,missing=missing)
        if capital==0:
            expected=gold[gold.model==model].set_index("date")
            for col in ["nav","cash","buy","sell","fees"]:
                np.testing.assert_allclose(z.set_index("date")[col],expected[col],atol=1e-11,rtol=0)
        orders.append(o.assign(**meta));daily.append(z.assign(**meta));windows.append(w.assign(**meta))
        summaries.append(dict(**meta,cagr=z.nav.iloc[-1]**(252/(len(z)-1))-1,nav=z.nav.iloc[-1],
          mdd=(z.nav/np.maximum.accumulate(np.r_[1.,z.nav])[1:]-1).min(),cash_fraction=(z.cash/z.nav).mean(),
          buy_short_days=(z.unfilled_buy>1e-10).sum(),sell_short_days=(z.unfilled_sell>1e-10).sum()))
w=pd.concat(windows);keys=["capital","missing","signal_date"]
for refname in [R,E]:
    r=w[w.model==refname].set_index(keys).net
    w["delta_"+refname]=w.net-r.reindex(pd.MultiIndex.from_frame(w[keys])).to_numpy()
w.to_csv(OUT/"windows.csv",index=False)
pd.concat(orders).to_parquet(OUT/"orders.parquet",index=False)
df=pd.concat(daily);df.to_parquet(OUT/"daily.parquet",index=False)
a=pd.DataFrame(summaries);a.to_csv(OUT/"accounts.csv",index=False)
out=[]
for (k,v),g in w[w.model=="early_model"].groupby(["capital","missing"]):
    q=df[(df.capital==k)&(df.missing==v)].pivot(index="date",columns="model",values="nav")
    mo=q.groupby(q.index.to_period("M")).last()/q.shift().fillna(1.).groupby(q.index.to_period("M")).first()-1
    delta=mo.early_model-mo[R]
    diff=g["delta_"+R]
    early=g.entry_date<split
    assert early.sum()==100 and (~early).sum()==39
    ix=np.random.default_rng(3828).integers(len(g),size=(10000,(len(g)+2)//3))
    ix=((ix[:,:,None]+np.arange(3))%len(g)).reshape(10000,-1)[:,:len(g)]
    lo,hi=np.quantile(diff.to_numpy()[ix].mean(axis=1)*1e4,[.025,.975])
    out.append(dict(late_bp=diff[~early].mean()*1e4,lower_bp=lo,upper_bp=hi,capital=k,missing=v,mean_bp=g["delta_"+R].mean()*1e4,primary_bp=g[early]["delta_"+R].mean()*1e4,
        ex3_month_bp=delta.drop(delta.nlargest(3).index).mean()*1e4))
result=pd.DataFrame(out);result.to_csv(OUT/"comparison.csv",index=False)
print(result.round(3).to_string(index=False))
dump(OUT/"verification.json",dict(unlimited_daily_parity=True,all_windows_reconcile=True,cash_and_volume_checked=True,
        hashes={str(f):sha(f) for f in [moneyfile,path,HERE/"PROTOCOL.md",Path(__file__),OUT/"accounts.csv",OUT/"windows.csv"]}))

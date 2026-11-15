"""Monthly portfolios of frozen predictions; gap-aware costs and equal controls."""
from common import *
import pandas as pd
from portfolio_r04 import path_for, turnover
K=['era','level','cohort','horizon']

def run():
 out=ROOT/'outputs/r212';out.mkdir(exist_ok=True)
 source=ROOT/'outputs/r212/mapped_predictions.parquet';prices=ROOT/'outputs/r212/combined_prices.parquet';market=CACHE/'forecast_v5/CSI_ALL.parquet'
 p=pd.read_parquet(source);p=p[p.task.eq('return')]
 d=pd.read_parquet(prices);b=pd.read_parquet(market).close;cal=pd.DatetimeIndex(b.index)
 d['day_i']=cal.get_indexer(d.date);assert d.day_i.ge(0).all()
 lookup={k:g.set_index('date').sort_index() for k,g in d.groupby(KEY)}
 ends=pd.Series(cal,index=cal).groupby(cal.to_period('M')).max();ends=ends[[x.end_time.normalize()<=cal.max() for x in ends.index]]
 schedule={x:cal[cal.get_loc(x)+1] for x in ends if cal.get_loc(x)+1<len(cal)}
 origins=sorted(schedule);nxt=dict(zip(origins[:-1],origins[1:]));intervals=[];holdings=[];daily=[];summaries=[];path_cache={}
 for key,group in p.groupby(K):
  ident=dict(zip(K,key));era,level,cohort,h=key
  dates=[x for x in origins if x in nxt and group.date.min()<=x<=group.date.max() and not (era=='SW2014' and schedule[nxt[x]]>pd.Timestamp('2021-11-30')) and not (era=='SW2021' and schedule[x]<pd.Timestamp('2022-01-01'))]
  for method in ['base','state','interaction','momentum','equal']:
   drift={};broken=False;returns=[];good=[];missing=0
   for origin in dates:
    entry=schedule[origin];end=schedule[nxt[origin]];days=cal[(cal>=entry)&(cal<=end)]
    g=group[group.date.eq(origin)&group.method.eq('base' if method=='equal' else method)]
    rec=dict(ident,method=method,origin=origin,entry=entry,exit=end,universe=len(g),post_gap=broken)
    if g.empty:
     intervals.append(dict(rec,status='missing_prediction'));broken=True;drift={};missing+=1;continue
    chosen=g.sort_values('industry_code') if method=='equal' else g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(max(1,int(np.ceil(.2*len(g)))))
    names=chosen.industry_code.tolist();target={x:1/len(names) for x in names};paths=[];bad=[]
    for c in names:
     pk=(era,level,c,entry,end)
     if pk not in path_cache:path_cache[pk]=path_for(lookup[(era,level,c)],days) if (era,level,c) in lookup else None
     path=path_cache[pk]
     if path is None:bad.append(c)
     else:paths.append(path)
     holdings.append(dict(ident,method=method,origin=origin,industry_code=c,weight=target[c]))
    if bad:
     intervals.append(dict(rec,status='missing_selected_path',missing_codes=';'.join(bad),selected=len(names)));broken=True;drift={};missing+=1;continue
    a=np.column_stack(paths);wealth=a.mean(axis=1);t=turnover(target,drift)
    # Independent shares calculation of endpoint wealth and drift.
    end_values={c:target[c]*a[-1,j] for j,c in enumerate(names)}
    assert np.isclose(sum(end_values.values()),wealth[-1],atol=1e-12)
    drift={c:v/wealth[-1] for c,v in end_values.items()};assert np.isclose(sum(drift.values()),1.)
    rec.update(status='valid',selected=len(names),turnover=t,gross=wealth[-1]-1,net20=(1-.002*t)*wealth[-1]-1,net50=(1-.005*t)*wealth[-1]-1,benchmark=b.loc[end]/b.loc[entry]-1)
    intervals.append(rec);good.append(rec)
    returns.append(dict(date=entry,gross=0.,net20=-.002*t,net50=-.005*t,benchmark=0.))
    for j in range(1,len(days)):
     rr=wealth[j]/wealth[j-1]-1;returns.append(dict(date=days[j],gross=rr,net20=rr,net50=rr,benchmark=b.loc[days[j]]/b.loc[days[j-1]]-1))
   base=dict(ident,method=method,scheduled=len(dates),valid=len(good),missing=missing,whole_path_valid=bool(good) and not broken)
   if not good:
    summaries.append(base);continue
   returns.append(dict(date=good[-1]['exit'],gross=0.,net20=-.002,net50=-.005,benchmark=0.))
   rr=pd.DataFrame(returns).groupby('date')[['gross','net20','net50','benchmark']].agg(lambda x:(1+x).prod()-1)
   rr=rr.reset_index();daily.append(rr.assign(**ident,method=method,whole_path_valid=not broken))
   for cost in ['gross','net20','net50']:
    result=dict(base,cost=cost,mean_interval_return=np.mean([x[cost] for x in good]),mean_turnover=np.mean([x['turnover'] for x in good]))
    if not broken:
     w=(1+rr[cost]).cumprod();yrs=(rr.date.max()-rr.date.min()).days/365.25
     result.update(total_return=w.iloc[-1]-1,cagr=w.iloc[-1]**(1/yrs)-1,drawdown=(w/w.cummax().clip(lower=1)-1).min(),vol=rr[cost].std()*np.sqrt(252),beta=rr[cost].cov(rr.benchmark)/rr.benchmark.var())
     # Reconcile daily compounding against interval fees and final liquidation.
     rate={'gross':0.,'net20':.002,'net50':.005}[cost]
     expected=np.prod([1+x[cost] for x in good])*(1-rate)
     assert np.isclose(w.iloc[-1],expected,rtol=1e-11)
    summaries.append(result)
 intervals=pd.DataFrame(intervals);intervals.to_csv(out/'intervals.csv',index=False)
 pd.DataFrame(holdings).to_parquet(out/'holdings.parquet',index=False)
 pd.concat(daily,ignore_index=True).to_parquet(out/'daily_returns.parquet',index=False)
 pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
 pairs=[]
 for key,g in intervals.groupby(K):
  for method in ['state','interaction']:
   for control in ['base','momentum','equal']:
    q=g[g.method.eq(method)].merge(g[g.method.eq(control)],on=K+['origin'],suffixes=('_new','_control'),validate='one_to_one')
    assert len(q)==len(g[g.method.eq(method)])
    valid=q.status_new.eq('valid')&q.status_control.eq('valid');v=q[valid]
    rec=dict(zip(K,key),method=method,control=control,scheduled=len(q),matched=int(valid.sum()),both_whole=bool(valid.all()))
    for c in ['gross','net20','net50','turnover']:rec['delta_'+c]=(v[c+'_new']-v[c+'_control']).mean()
    pairs.append(rec)
 pd.DataFrame(pairs).to_csv(out/'paired_summary.csv',index=False)
 inputs=[source,prices,market,ROOT/'protocols/r212.json',Path(__file__),ROOT/'src/portfolio_r04.py',ROOT/'src/common.py']
 files=['intervals.csv','holdings.parquet','daily_returns.parquet','summary.csv','paired_summary.csv']
 js(out/'verification.json',dict(status='PASS',scope='Frozen selections, exact paths, drift-weight sums, independent endpoint sum, interval/daily wealth reconciliation; no execution certification',inputs={str(x):sha(x) for x in inputs},outputs={x:sha(out/x) for x in files},intervals=len(intervals),valid=int(intervals.status.eq('valid').sum()),adoption=False))
 print('intervals',len(intervals),'valid',sum(intervals.status.eq('valid')),'paired',len(pairs))
if __name__=='__main__':run()

import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'p60';O.mkdir(exist_ok=True);assert not (O/'receipt.json').exists()
f=R/'p30/evaluated.parquet';mf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet');tf=R/'p30/training_panel.parquet'
q=pd.read_parquet(f);ids=['era','industry_code','date'];nav=pd.read_parquet(tf,columns=ids+['nav']);q=q.merge(nav,on=ids,validate='one_to_one');m=pd.read_parquet(mf).close.sort_index();q['market126']=q.date.map(m/m.shift(126)-1);assert q.market126.notna().all();q['gate']=q.market126.gt(0);axis=pd.DatetimeIndex(sorted(q.date.unique()));key=['era','industry_code','block'];q=q.sort_values(key+['date']).reset_index(drop=True)
rows=[];annual=[];timing=[];events=[];daily=[]
def ratio_ci(s,n):
 rng=np.random.default_rng(3309);vals=[];s=s.reindex(axis,fill_value=0).to_numpy();n=n.reindex(axis,fill_value=0).to_numpy();N=len(axis)
 for _ in range(500):
  ix=((rng.integers(0,N,size=int(np.ceil(N/26)))[:,None]+np.arange(26))%N).ravel()[:N]
  if n[ix].sum():vals.append(s[ix].sum()/n[ix].sum())
 return np.quantile(vals,[.025,.975])
for method in ['rebuilt','momentum']:
 prev=q.groupby(key)[method].shift();cont=q.week_i.sub(q.groupby(key).week_i.shift()).eq(1)
 oldedge=q[method]&prev.eq(False)&cont;assert np.array_equal(oldedge,q[method+'_edge'])
 # Track start of each observed base selection episode, retaining left censoring.
 starts={};delays={};known={}
 for _,g in q.groupby(key):
  start=None;start_known=False;last=None
  for i,r in g.iterrows():
   if r[method]:
    if last is None or r.week_i-last.week_i!=1 or not last[method]:start=r;start_known=last is not None and r.week_i-last.week_i==1 and not last[method]
    delays[i]=(r.day_i-start.day_i,r.nav/start.nav-1);known[i]=start_known
   else:start=None
   last=r
 for variant in ['base','gated']:
  selected=q[method] if variant=='base' else q[method]&q.gate
  previous=selected.groupby([q[c] for c in key]).shift();edge=selected&previous.eq(False)&cont;boundary=selected&~cont
  gate_only=edge&prev.eq(True) if variant=='gated' else pd.Series(False,index=q.index)
  for i in q.index[edge]:
   delay,move=delays[i];timing.append(dict(method=method,variant=variant,date=q.loc[i,'date'],industry_code=q.loc[i,'industry_code'],base_start_known=known[i],delay_sessions=delay,nav_change_since_base_start=move,gate_opening_entry=bool(gate_only.loc[i])))
  for h in [63,126,252]:
   label=f'new_win{h}';base=q.groupby('date')[label].mean();z=q[edge&q[label].notna()].copy();z['uplift']=z[label]-z.date.map(base);s=z.groupby('date').uplift.sum();n=z.groupby('date').size();lo,hi=ratio_ci(s,n)
   coverage=q.loc[selected,label].sum()/q[label].sum();lost=q.loc[q[method]&~selected,label].sum()
   rows.append(dict(method=method,variant=variant,horizon=h,total_events=int(edge.sum()),known=len(z),unknown=int(edge.sum())-len(z),boundary=int(boundary.sum()),win=z[label].mean(),uplift=z.uplift.mean(),lo=lo,hi=hi,success_week_coverage=coverage,excluded_success_weeks=float(lost),gate_opening_events=int(gate_only.sum()),empty_dates=int((selected.groupby(q.date).sum()==0).sum())))
   for year,g in z.groupby(z.date.dt.year):annual.append(dict(method=method,variant=variant,horizon=h,year=year,known=len(g),win=g[label].mean(),uplift=g.uplift.mean()))
   for date in axis:daily.append(dict(method=method,variant=variant,horizon=h,date=date,event_count=int(n.get(date,0)),uplift_sum=float(s.get(date,0))))
  e=q.loc[edge,ids+['week_i']].copy();e['method']=method;e['variant']=variant;events.append(e)
a=pd.DataFrame(rows);a.to_csv(O/'summary.csv',index=False);pd.DataFrame(annual).to_csv(O/'annual.csv',index=False);pd.DataFrame(timing).to_csv(O/'timing.csv',index=False);pd.DataFrame(daily).to_csv(O/'daily.csv',index=False);pd.concat(events).to_csv(O/'events.csv',index=False)
q[['date','market126','gate']].drop_duplicates().sort_values('date').to_csv(O/'market_gate.csv',index=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=[f,mf,tf,R/'P60_fixed_market_gate_plan.md',Path(__file__)]
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',original_edges_reproduced=True,axis_dates=len(axis),inputs={str(p):sha(p) for p in inputs},outputs={p.name:sha(p) for p in O.glob('*.csv')}),indent=2)+'\n');print(a.query('horizon==126').to_string(index=False));t=pd.DataFrame(timing);print(t[t.base_start_known].groupby(['method','variant'])[['delay_sessions','nav_change_since_base_start']].median().to_string());print(t[(t.variant=='gated') & t.gate_opening_entry & t.base_start_known][['delay_sessions','nav_change_since_base_start']].describe().to_string())

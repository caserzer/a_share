from common import *
import pandas as pd
from financing_components_model_r262 import METHODS
out=ROOT/'outputs/r270';a=pd.read_parquet(out/'snapshot/predictions.parquet');b=pd.read_parquet(out/'signal/predictions.parquet');keys=KEY+['date','task','horizon','year','method','variant'];z=a.merge(b,on=keys,suffixes=('_snapshot','_signal'),validate='one_to_one');assert len(z)==len(a)==len(b);assert np.allclose(z.y_snapshot,z.y_signal,equal_nan=True);assert z.maturity_snapshot.equals(z.maturity_signal)
control=z[z.method.isin(['FS','FSE'])];assert np.array_equal(control.prediction_snapshot,control.prediction_signal)
rows=[]
for k,g in z.groupby(['era','level','task','horizon','method','variant','date']):
 v=g.dropna(subset=['y_signal']);delta=(v.prediction_signal-v.y_signal)**2-(v.prediction_snapshot-v.y_snapshot)**2;rows.append(dict(zip(['era','level','task','horizon','method','variant','date'],k),brier_improvement=delta.mean(),known=len(v)))
d=pd.DataFrame(rows);d.to_csv(out/'date_comparisons.csv',index=False);summary=[]
for era,level in [('SW2014','L2'),('SW2014','L3'),('SW2021','L1'),('SW2021','L2'),('SW2021','L3')]:
 for task in ['onset','reversal']:
  for h in [20,60]:
   for method in METHODS:
    for variant in ['base','state','interaction']:
     ident=dict(era=era,level=level,task=task,horizon=h,method=method,variant=variant);v=d.copy()
     for k,val in ident.items():v=v[v[k].eq(val)]
     if v.empty:summary.append(dict(ident,status='no_fit',period='all'));continue
     for period,g in [('all',v)]+[(str(y),gg) for y,gg in v.groupby(v.date.dt.year)]:summary.append(dict(ident,status='descriptive_only',period=period,dates=len(g),brier_improvement=g.brier_improvement.mean()))
s=pd.DataFrame(summary);s.to_csv(out/'clock_summary.csv',index=False);assert len(s[s.period.eq('all')])==360
# Independent per-date comparison against the already generated component metrics.
ma=pd.read_csv(out/'snapshot/date_metrics.csv',parse_dates=['date']).set_index(['era','level','task','horizon','method','variant','date']);mb=pd.read_csv(out/'signal/date_metrics.csv',parse_dates=['date']).set_index(ma.index.names);dd=d.set_index(ma.index.names);assert np.allclose(dd.brier_improvement,mb.brier-ma.brier,atol=1e-12,equal_nan=True)
js(out/'comparison_verification.json',dict(status='PASS',paired_predictions=len(z),control_predictions=len(control),date_groups=len(d),planned_comparisons=360,scope='Exact paired sample, labels, maturity, unchanged control predictions and row-error versus stored date Brier comparison',adoption=False));print('PAIRED',len(z),len(d))

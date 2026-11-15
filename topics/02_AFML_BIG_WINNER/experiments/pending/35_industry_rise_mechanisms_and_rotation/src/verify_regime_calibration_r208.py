from common import *
import pandas as pd
from regime_calibration_r208 import IDS
out=ROOT/'outputs/r208';s=pd.read_csv(out/'calibration.csv',keep_default_na=False);maximum=0.;checks=0
for rnd in [196,199,200]:
 p=pd.read_parquet(ROOT/f'outputs/r{rnd}/predictions.parquet');p=p[p.task.isin(['onset','reversal'])].copy()
 for col in IDS:
  if col not in p:p[col]='not_applicable'
 for key,g in p.groupby(IDS+['variant'],dropna=False):
  match=s['round'].eq(rnd)
  for col,val in zip(IDS+['variant'],key):match &= s[col].astype(str).eq(str(val))
  for _,r in s[match].iterrows():
   a=g if r.scope=='all' else g[g.year.astype(str).eq(str(r.scope_value))] if r.scope=='year' else g[g.regime.eq(r.scope_value)]
   q=a.dropna(subset=['y']).copy();q['brier_check']=(q.prediction-q.y)**2;q['bias_check']=q.prediction-q.y;pr=q.prediction.clip(1e-12,1-1e-12);q['logloss_check']=-q.y*np.log(pr)-(1-q.y)*np.log1p(-pr)
   for metric in ['brier','bias','logloss']:
    actual=q.groupby('date')[metric+'_check'].mean().mean();err=abs(actual-float(r[metric]));maximum=max(maximum,err);assert err<1e-12;checks+=1
   assert q.date.nunique()==r.dates and len(q)==r.known
b=pd.read_csv(out/'reliability_bins.csv');keys=['round']+IDS+['variant','scope','scope_value'];b['contribution']=b.weight*(b.probability-b.event_rate).abs();ece=b.groupby(keys,dropna=False).contribution.sum().reset_index(name='check');merged=s.merge(ece,on=keys,validate='one_to_one');assert len(merged)==len(s);assert np.max(abs(merged.ece-merged.check))<1e-12
js(out/'independent_verification.json',dict(status='PASS',metric_checks=checks,max_error=maximum,ece_groups=len(merged),method='Independent equal-date aggregation of frozen prediction losses; reliability-bin ECE reconstruction',script_sha256=sha(Path(__file__))))
print('PASS',checks,maximum)

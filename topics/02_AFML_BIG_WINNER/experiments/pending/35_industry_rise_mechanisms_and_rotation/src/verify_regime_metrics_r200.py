"""Recompute all dated scores and all-period paired means from saved predictions."""
from common import *
import pandas as pd
from scipy.stats import spearmanr

def run():
 out=ROOT/'outputs/r200';p=pd.read_parquet(out/'predictions.parquet');d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);keys=['family','era','level','method','task','horizon','year','date','regime','variant'];lookup={k:g for k,g in p.groupby(keys)};err=0.
 for row in d.to_dict('records'):
  g=lookup[tuple(row[k] for k in keys)];v=g[g.y.notna()];loss=-sum((r.prediction-r.y)**2 for r in v.itertuples())/len(v) if len(v) else np.nan
  utility=spearmanr(v.prediction,v.y).statistic if row['task'] in ['return','catchup'] and len(v)>=20 and v.prediction.nunique()>1 and v.y.nunique()>1 else np.nan if row['task'] in ['return','catchup'] else loss
  for a,b in [(loss,row['negative_mse']),(utility,row['utility'])]:
   assert np.isclose(a,b,atol=1e-12,equal_nan=True)
   if pd.notna(a):err=max(err,abs(a-b))
 s=pd.read_csv(out/'paired_comparisons.csv');count=0
 for row in s[s.period.eq('all')].to_dict('records'):
  q=d.copy()
  for k in ['family','era','level','task','horizon']:q=q[q[k]==row[k]]
  a,av=row['first'].split('/');b,bv=row['second'].split('/');metric='negative_mse' if row['metric']=='mse_reduction' else 'utility'
  x=q[q.method.eq(a)&q.variant.eq(av)][['date',metric]];y=q[q.method.eq(b)&q.variant.eq(bv)][['date',metric]];z=x.merge(y,on='date',suffixes=('_a','_b'),validate='one_to_one').dropna();delta=z[metric+'_a']-z[metric+'_b'];assert len(z)==row['dates'] and np.isclose(delta.mean(),row['delta'],atol=1e-12,equal_nan=True);count+=1
 js(out/'metric_verification.json',dict(status='PASS',date_metrics=len(d),all_period_comparisons=count,max_error=err,scope='all date metrics and all-period paired comparisons; subgroup means not independently recomputed',code_sha256=sha(__file__),comparisons_sha256=sha(out/'paired_comparisons.csv')))
 print(len(d),count,err)
if __name__=='__main__':run()

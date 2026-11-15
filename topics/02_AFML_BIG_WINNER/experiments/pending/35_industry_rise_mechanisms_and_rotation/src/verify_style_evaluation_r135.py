"""Independently reproduce date metrics and calendar covariance intervals."""
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r135';counts={}
 for family in ['r55','r56']:
  d=out/f'evaluation/outputs/{family}';p=pd.read_parquet(d/'predictions.parquet');keys=['era','level','horizon']+(['task'] if family=='r56' else [])+['method','date'];m=pd.read_csv(d/('metrics_by_date.csv' if family=='r55' else 'date_metrics.csv'),parse_dates=['date']);look=m.set_index(keys)
  for key,g in p.groupby(keys):
   q=g.dropna(subset=['target' if family=='r55' else 'y']);r=look.loc[key]
   if family=='r55':
    assert r.complete==len(q) and r.origins==len(g);assert np.isclose(r.mse,((q.prediction-q.target)**2).mean(),equal_nan=True)
    ic=q.prediction.rank().corr(q.target.rank()) if len(q)>=5 and q.prediction.nunique()>1 and q.target.nunique()>1 else np.nan;assert np.isclose(r.ic,ic,equal_nan=True)
   else:assert r.n==len(q) and np.isclose(r.brier,((q.prediction-q.y)**2).mean(),equal_nan=True) and np.isclose(r.baseline,((q.training_mean-q.y)**2).mean(),equal_nan=True)
  paired=pd.read_csv(d/'paired_by_date.csv',parse_dates=['date']);incs=pd.read_csv(d/'increments.csv');pairkeys=['era','level','horizon','comparison']+(['metric'] if family=='r55' else ['task']);value='delta' if family=='r55' else 'brier_reduction'
  for r in incs.to_dict('records'):
   mask=np.ones(len(paired),bool)
   for k in pairkeys:mask &= paired[k].eq(r[k])
   z=paired[mask].dropna(subset=[value]);v=z[value].to_numpy();u=v-v.mean();t=z.date.dt.to_period('M').astype('int64').to_numpy();lag=3 if r['horizon']==20 else 6;k=np.maximum(1-np.abs(t[:,None]-t[None,:])/(lag+1),0);se=np.sqrt(max(u@k@u,0))/len(v);c=2.5758293035489004 if family=='r55' else 2.807033768343811;lo=v.mean()-c*se;hi=v.mean()+c*se
   assert r['months']==len(v);assert np.isclose(r['mean' if family=='r55' else 'brier_reduction'],v.mean());assert np.isclose(r['low99' if family=='r55' else 'low995'],lo);assert np.isclose(r['high99' if family=='r55' else 'high995'],hi)
   # Derive paired deltas directly from independently verified metrics.
   gm=m.copy()
   for col in ['era','level','horizon']+(['task'] if family=='r56' else []):gm=gm[gm[col].eq(r[col])]
   methods={'diffusion_with_size':('FSD','FS'),'diffusion_with_market_controls':('FSMD','FSM'),'market_controls_without_diffusion':('FSM','FS')};a,b=methods[r['comparison']];wide=gm.pivot(index='date',columns='method',values=r['metric'] if family=='r55' else 'brier');expected=wide[a]-wide[b] if family=='r55' else wide[b]-wide[a];assert np.allclose(z[value],expected.loc[z.date],equal_nan=True)
   if family=='r56':assert r['result']==('historical_support' if r['horizon']==20 and len(v)>=24 and lo>0 else 'not_established' if r['horizon']==20 else 'secondary_descriptive')
  if family=='r55':
   for r in json.loads((d/'stability_decisions.json').read_text()):
    z=paired.copy()
    for k in pairkeys:z=z[z[k].eq(r[k])]
    yearly=z.groupby(z.date.dt.year).delta.mean().dropna();assert r['years']==len(yearly) and r['positive_years']==int(yearly.gt(0).sum());assert r['stable_support']==bool(r['months']>=24 and len(yearly)>=3 and yearly.gt(0).all() and r['low99']>0)
  counts[family]=dict(date_metrics=len(m),intervals=len(incs))
 js(out/'evaluation_verification.json',dict(status='PASS',counts=counts,verifier_sha256=sha(__file__)))
 print('METRICS PASS',counts,flush=True)
if __name__=='__main__':run()

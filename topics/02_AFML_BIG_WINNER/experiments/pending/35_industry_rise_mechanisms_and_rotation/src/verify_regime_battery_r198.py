"""Independent paired-loss and original classification gate verification."""
from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r198';p=pd.read_parquet(out/'predictions.parquet');metrics=pd.read_csv(out/'metrics.csv');count=0;maxerr=0.
 for m in metrics.to_dict('records'):
  z=p.copy()
  for k in KEY+['horizon']:z=z[z[k]==m[k]]
  if m['period'].startswith('year:'):z=z[z.year.eq(int(m['period'][5:]))]
  if m['period'].startswith('state:'):z=z[z.regime.eq(m['period'][6:])]
  a,v=m['first'].split('/');b,w=m['second'].split('/');a=z[z.method.eq(a)&z.variant.eq(v)];b=z[z.method.eq(b)&z.variant.eq(w)]
  q=a.merge(b,on=KEY+['date','horizon'],suffixes=('_a','_b'),validate='one_to_one');assert np.allclose(q.target_a,q.target_b,equal_nan=True);q=q[q.target_a.notna()]
  mse=sum((r.prediction_b-r.target_b)**2-(r.prediction_a-r.target_a)**2 for r in q.itertuples())/len(q) if len(q) else np.nan
  mae=sum(abs(r.prediction_b-r.target_b)-abs(r.prediction_a-r.target_a) for r in q.itertuples())/len(q) if len(q) else np.nan
  assert len(q)==m['n'] and q.year_a.nunique()==m['years']
  assert np.isclose(mse,m['mse_improvement'],atol=1e-14,equal_nan=True) and np.isclose(mae,m['mae_improvement'],atol=1e-14,equal_nan=True)
  if len(q):maxerr=max(maxerr,abs(mse-m['mse_improvement']),abs(mae-m['mae_improvement']))
  count+=1
 old=json.loads((ROOT/'outputs/r140/evaluation/outputs/r65/fold_ledger.json').read_text());new=json.loads((out/'classification_ledger.json').read_text());keys=KEY+['task','horizon','year'];lookup={tuple(r[k] for k in keys):r for r in old};limits=json.loads((ROOT/'protocols/r65.json').read_text())['gates']
 assert len(old)==len(new)
 for row in new:
  previous=lookup[tuple(row[k] for k in keys)]
  for k in limits:assert previous[k]==row[k]
  assert row['failed_gates']==previous['failed_gates']
 js(out/'independent_verification.json',dict(status='PASS',metric_rows=count,metric_max_error=maxerr,original_classification_gate_rows=len(new),code_sha256=sha(__file__),predictions_sha256=sha(out/'predictions.parquet'),metrics_sha256=sha(out/'metrics.csv')))
 print(count,maxerr,len(new))
if __name__=='__main__':run()

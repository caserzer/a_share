"""Independent centered normal-equation replay of the fixed battery pilot."""
import pandas as pd
from common import *
from battery_pilot_r53 import panel

def run():
 out=ROOT/'outputs/r53';receipt=json.loads((out/'receipt.json').read_text())
 for path,digest in receipt['inputs'].items():assert sha(Path(path))==digest
 p=panel();pred=pd.DataFrame(json.loads((out/'predictions.json').read_text()));params=json.loads((out/'model_parameters.json').read_text());maximum=0.;n=0
 for item in params:
  g=p.copy()
  for k in KEY:g=g[g[k].eq(item[k])]
  h=item['horizon'];boundary=pd.Timestamp(item['year'],1,1);tr=g[(g.date<boundary)&(g[f'maturity{h}']<boundary)].dropna(subset=[f'excess{h}']);te=g[g.date.dt.year.eq(item['year'])];cols=item['columns']
  assert len(tr)>=24 and len(tr)==item['train_n'];assert pd.to_datetime(tr.growth_available_at).le(tr.date).all()
  raw=tr[cols].to_numpy(float);mu=raw.mean(axis=0);scale=raw.std(axis=0);scale[scale==0]=1;x=(raw-mu)/scale;y=tr[f'excess{h}'].to_numpy(float);coef=np.linalg.solve(x.T@x+10*np.eye(x.shape[1]),x.T@(y-y.mean()));estimate=((te[cols].to_numpy(float)-mu)/scale)@coef+y.mean()
  q=pred[(pred.method==item['method'])&(pred.year==item['year'])&(pred.horizon==h)]
  for k in KEY:q=q[q[k].eq(item[k])]
  q=q.sort_values('date');assert list(q.date)==[v.isoformat() for v in te.date];error=float(np.max(np.abs(q.prediction.to_numpy()-estimate)));maximum=max(maximum,error);assert error<1e-10
  assert np.allclose(q.mean_prediction,y.mean()) and np.allclose(q.target,te[f'excess{h}'],equal_nan=True);n+=len(q)
 metrics=json.loads((out/'metrics.json').read_text())
 for m in metrics:
  q=pred[pred.horizon.eq(m['horizon'])]
  for k in KEY:q=q[q[k].eq(m[k])]
  if m['period']!='all':q=q[q.year.eq(int(m['period']))]
  a=q[q.method.eq('FS')].dropna(subset=['target']).sort_values('date');b=q[q.method.eq('FSB')].dropna(subset=['target']).sort_values('date');assert list(a.date)==list(b.date) and len(a)==m['n']
  for name,z in [('FS',a),('FSB',b)]:assert abs(sum((r.target-r.prediction)**2 for r in z.itertuples())/len(z)-m['mse_'+name])<1e-12
  assert m['stability_sample_gate']==(len(a)>=24 and a.year.nunique()>=3)
 assert maximum<1e-12
 js(out/'verification.json',dict(status='PASS',prediction_rows_checked=n,max_normal_equation_error_upper_bound=1e-12,metrics_checked=len(metrics),train_maturity_checked=True,scope='algebra, targets, same-cohort metrics and temporal separation; actual floating-point residual printed per run, stable bound used for receipt; not source first-release authenticity or prospective validation'))
 print('R53 VERIFIED',n,'predictions, max error',maximum)

if __name__=='__main__':run()

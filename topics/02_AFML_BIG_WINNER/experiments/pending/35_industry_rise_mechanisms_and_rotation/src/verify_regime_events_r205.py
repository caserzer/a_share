from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r205';p=pd.read_parquet(out/'predictions.parquet');keys=['family','era','level','target_type','horizon','year','method','variant'];groups={k:g for k,g in p.groupby(keys)};panels={f:pd.read_parquet(out/f'{f}_panel.parquet').set_index('event_id') for f in p.family.unique()};maximum=0.;count=0
 for m in json.loads((out/'models.json').read_text()):
  q=groups[tuple(m[k] for k in keys)];z=panels[m['family']].loc[q.event_id];x=(z[m['columns']].to_numpy()-m['mean'])/m['scale'];u=np.array([[float(s==t) for t in ['down_high','up_low','up_high']] for s in z.regime]);a=x
  if m['variant']!='base':a=np.column_stack([x,u])
  if m['variant']=='interaction':a=np.column_stack([a,*[x*u[:,j,None] for j in range(3)]])
  pred=a@np.array(m['coef'])+m['intercept'];err=float(np.max(abs(pred-q.prediction.to_numpy())));assert err<1e-12;maximum=max(maximum,err);count+=len(q);assert np.allclose(z[m['target_type']+str(m['horizon'])],q.y,equal_nan=True)
 assert count==len(p)
 d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);k=['family','era','level','target_type','horizon','method','variant','date','regime'];lookup={key:g for key,g in p.groupby(k)}
 for row in d.to_dict('records'):
  z=lookup[tuple(row[c] for c in k)];v=z[z.y.notna()];mse=sum((x.prediction-x.y)**2 for x in v.itertuples())/len(v) if len(v) else np.nan;assert np.isclose(mse,row['mse'],atol=1e-12,equal_nan=True)
 js(out/'independent_verification.json',dict(status='PASS',rows=count,max_error=maximum,date_metrics=len(d),scope='all saved parameter predictions, target identities and dated MSE',code_sha256=sha(__file__)));print(count,maximum,len(d))
if __name__=='__main__':run()

import pandas as pd
from common import *
from margin_models_r46 import panel,METHODS

def run():
 out=ROOT/'outputs/r46';receipt=json.loads((out/'receipt.json').read_text());p=panel();pred=pd.read_parquet(out/'predictions.parquet');parameters=json.loads((out/'model_parameters.json').read_text());maximum=0.;checked=0
 for path,h in receipt['inputs'].items():assert sha(Path(path))==h
 assert sha(out/'predictions.parquet')==receipt['prediction_sha256']
 for item in parameters:
  g=p[p.era.eq(item['era'])&p.level.eq(item['level'])];h=item['horizon'];boundary=pd.Timestamp(item['year'],1,1);tr=g[g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(item['year'])];assert len(tr)>=300 and tr.date.nunique()>=18
  cols=item['columns'];rank=g.groupby('date')[cols].rank(method='average');count=g.groupby('date')[cols].transform('count');rank=(rank-.5)/count-.5
  raw=rank.loc[tr.index].to_numpy();mu=raw.mean(axis=0);sd=raw.std(axis=0);sd[sd==0]=1;x=(raw-mu)/sd;y=tr[f'excess{h}'].to_numpy();counts=tr.groupby('date').date.transform('size').to_numpy();w=len(tr)/tr.date.nunique()/counts;xm=np.average(x,axis=0,weights=w);ym=np.average(y,weights=w);xc=x-xm
  beta=np.linalg.solve(xc.T@(xc*w[:,None])+10*np.eye(len(cols)),xc.T@(w*(y-ym)));forecast=((rank.loc[te.index].to_numpy()-mu)/sd-xm)@beta+ym
  z=pred[pred.era.eq(item['era'])&pred.level.eq(item['level'])&pred.horizon.eq(h)&pred.year.eq(item['year'])&pred.method.eq(item['method'])]
  assert list(zip(z.date,z.industry_code))==list(zip(te.date,te.industry_code));err=float(np.max(np.abs(forecast-z.prediction.to_numpy())));maximum=max(maximum,err);assert err<1e-12;assert np.allclose(z.target,te[f'excess{h}'],equal_nan=True);checked+=len(z)
 metrics=pd.read_parquet(out/'metrics_by_date.parquet')
 for x in metrics.to_dict('records'):
  z=pred
  for k in ['era','level','horizon','method','date']:z=z[z[k].eq(x[k])]
  z=z.dropna(subset=['target']);assert len(z)==x['n'];assert np.isclose(np.mean((z.prediction-z.target)**2),x['mse'],equal_nan=True)
  if len(z)>=5 and z.prediction.nunique()>1 and z.target.nunique()>1:assert abs(np.corrcoef(z.prediction.rank(),z.target.rank())[0,1]-x['ic'])<1e-12
 for item in json.loads((out/'increments.json').read_text()):
  m=metrics[metrics.era.eq(item['era'])&metrics.level.eq(item['level'])&metrics.horizon.eq(item['horizon'])];w=m.pivot(index='date',columns='method',values='ic');z=(w.FSE-w.FS).dropna();n=len(z);u=z.to_numpy()-z.mean();months=z.index.to_period('M').astype('int64').to_numpy();v=float(u@u);lag=3 if item['horizon']==20 else 6
  for i in range(n):
   for j in range(i):
    delta=months[i]-months[j]
    if 1<=delta<=lag:v+=2*(1-delta/(lag+1))*u[i]*u[j]
  se=np.sqrt(max(v,0))/n;assert abs(item['low99']-(z.mean()-2.5758293035489004*se))<1e-12;assert abs(item['high99']-(z.mean()+2.5758293035489004*se))<1e-12
 js(out/'verification.json',dict(status='PASS',prediction_rows=checked,max_error_upper_bound=1e-12,metrics_checked=len(metrics),calendar_HAC_intervals_checked=4,scope='independent normal equations and paired metric arithmetic; not forward validation'))
 print('R46 VERIFIED',checked,'predictions, max residual',maximum)

if __name__=='__main__':run()

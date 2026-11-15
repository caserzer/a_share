import pandas as pd
from scipy.special import expit
from common import *
from style_models_r55 import base_panel,METHODS
from train_r02 import target

def run():
 out=ROOT/'outputs/r56';base=base_panel();p=pd.read_parquet(out/'predictions.parquet');folds=pd.read_csv(out/'fold_ledger.csv');models=json.loads((out/'model_parameters.json').read_text());error=0;rows=0;checked=0
 receipt=json.loads((out/'run_receipt.json').read_text())
 for field,path in [('protocol_sha256',ROOT/'protocols/r56.json'),('panel_sha256',ROOT/'data/monthly_panel.parquet'),('code_sha256',ROOT/'src/classifiers_style_r56.py'),('common_sha256',ROOT/'src/common.py'),('prediction_sha256',out/'predictions.parquet')]:assert receipt[field]==sha(path)
 for row in folds.itertuples():
  g=base[base.era.eq(row.era)&base.level.eq(row.level)];y,eligible=target(g,row.task,row.horizon);g=g[eligible].copy();g['y']=y[eligible];h=row.horizon;start=pd.Timestamp(row.year,1,1);calstart=pd.Timestamp(row.year-1,7,1)
  tr=g[g.date.lt(calstart)&g[f'maturity{h}'].lt(calstart)&g.y.notna()];ca=g[g.date.ge(calstart)&g.date.lt(start)&g[f'maturity{h}'].lt(start)&g.y.notna()];te=g[g.date.dt.year.eq(row.year)]
  ready=len(tr)>=300 and tr.date.nunique()>=18 and tr.y.value_counts().reindex([0.,1.],fill_value=0).min()>=30 and len(ca)>=100 and ca.date.nunique()>=4 and ca.y.value_counts().reindex([0.,1.],fill_value=0).min()>=10
  assert ready==(row.status=='fit');assert len(tr)==row.n_fit and len(ca)==row.n_cal and len(te)==row.n_test
  actual=p[p.era.eq(row.era)&p.level.eq(row.level)&p.task.eq(row.task)&p.horizon.eq(h)&p.year.eq(row.year)]
  if not ready:assert actual.empty
  else:
   assert set(actual.method)==set(METHODS)
   for method,z in actual.groupby('method'):
    assert set(z.row_id)==set(te.index);assert np.allclose(z.y,te.loc[z.row_id,'y'],equal_nan=True)
  checked+=1
 for m in models:
  g=base[base.era.eq(m['era'])&base.level.eq(m['level'])];r=g.groupby('date')[m['columns']].transform(lambda x:(x.rank()-.5)/len(x)-.5)
  q=p[p.era.eq(m['era'])&p.level.eq(m['level'])&p.task.eq(m['task'])&p.horizon.eq(m['horizon'])&p.year.eq(m['year'])&p.method.eq(m['method'])]
  x=(r.loc[q.row_id].to_numpy()-np.array(m['scaler_mean']))/np.array(m['scaler_scale']);score=x@np.array(m['coefficient']).reshape(-1)+np.array(m['intercept']).ravel()[0]
  replay=expit(score*np.array(m['calibration_coefficient']).ravel()[0]+np.array(m['calibration_intercept']).ravel()[0]);error=max(error,float(np.abs(replay-q.prediction).max()));assert np.allclose(expit(score),q.raw_prediction);rows+=len(q)
 assert rows==len(p) and error<1e-12
 d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);look=d.set_index(['era','level','task','horizon','method','date'])
 for key,z in p.groupby(['era','level','task','horizon','method','date']):
  q=z.dropna(subset=['y']);v=look.loc[key];assert v.n==len(q) and np.isclose(v.brier,((q.prediction-q.y)**2).mean(),equal_nan=True)
 paired=pd.read_csv(out/'paired_by_date.csv',parse_dates=['date']);incs=pd.read_csv(out/'increments.csv')
 for row in incs.itertuples():
  z=paired[paired.era.eq(row.era)&paired.level.eq(row.level)&paired.task.eq(row.task)&paired.horizon.eq(row.horizon)&paired.comparison.eq(row.comparison)].dropna();v=z.brier_reduction.to_numpy();u=v-v.mean();t=z.date.dt.to_period('M').astype('int64').to_numpy();lag=3 if row.horizon==20 else 6;k=np.maximum(1-np.abs(t[:,None]-t[None,:])/(lag+1),0);se=np.sqrt(max(u@k@u,0))/len(v)
  assert len(v)==row.months and np.isclose(v.mean(),row.brier_reduction) and np.isclose(row.low995,v.mean()-2.807033768343811*se) and np.isclose(row.high995,v.mean()+2.807033768343811*se)
 paths=[ROOT/'data/r54_market_controls.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',ROOT/'src/train_r02.py',ROOT/'src/style_models_r55.py',ROOT/'src/classifiers_style_r56.py',ROOT/'src/evaluate_classifiers_r56.py',ROOT/'protocols/r56.json']
 js(out/'verification.json',dict(status='PASS',folds_checked=checked,prediction_rows=rows,max_replay_error=error,reads={str(x):sha(x) for x in paths},checks=['all fit/skip counts and class/calibration gates','four methods same test identities/labels','no uncalibrated fallback','all stored logistic and Platt predictions','all date Brier scores','all calendar covariance intervals']))
 print('R56 VERIFIED',rows,'folds',checked,'error',error)
if __name__=='__main__':run()

"""Reconstruct saved regime predictions separately from sklearn inference."""
from common import *
import pandas as pd
from scipy.special import expit
from refit_r131 import prepare

def run():
 out=ROOT/'outputs/r196';proof=json.loads((out/'verification.json').read_text())
 for p,h in proof['inputs'].items():assert sha(ROOT/p)==h
 for p,h in proof['outputs'].items():assert sha(out/p)==h
 states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime
 panels={}
 for family,path in [('core','outputs/r130/monthly_panel.parquet'),('l1','data/l1_monthly_panel.parquet')]:
  a=pd.read_parquet(ROOT/path);a['log_members']=np.log(a.members.where(a.members.gt(0)));panels[family]=a
 pred=pd.read_parquet(out/'predictions.parquet');keys=['family','era','level','cohort','method','task','horizon','year','objective','variant'];groups={k:g for k,g in pred.groupby(keys)};cache={};checked=0;maxerr=0.
 for m in json.loads((out/'models.json').read_text()):
  key=tuple(m[k] for k in keys);g=groups[key];prepkey=tuple(m[k] for k in ['family','era','level','cohort','task','horizon'])
  if prepkey not in cache:cache[prepkey]=prepare(panels[m['family']],m['era'],m['level'],m['cohort'],m['task'],m['horizon'])
  q,ranks=cache[prepkey];te=q[q.date.dt.year.eq(m['year'])&q.date.map(states).notna()];state=te.date.map(states)
  x=(ranks.loc[te.index,m['columns']].to_numpy()-np.asarray(m['scaler_mean']))/np.asarray(m['scaler_scale'])
  u=np.array([[float(s==v) for v in ['down_high','up_low','up_high']] for s in state])
  if m['variant']=='state':x=np.concatenate([x,u],axis=1)
  elif m['variant']=='interaction':x=np.concatenate([x,u,x*u[:,0,None],x*u[:,1,None],x*u[:,2,None]],axis=1)
  score=x@np.asarray(m['coefficient']).ravel()+np.asarray(m['intercept']).item()
  if m['task']!='return':score=expit(score*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item())
  a=te[KEY+['date','y']].copy();a['check']=score;a=a.merge(g,on=KEY+['date'],validate='one_to_one',suffixes=('_new','_saved'));assert len(a)==len(te)==len(g);assert np.allclose(a.y_new,a.y_saved,equal_nan=True)
  error=float(np.max(np.abs(a.check-a.prediction)));assert error<1e-12;maxerr=max(maxerr,error);checked+=len(a)
 assert checked==len(pred)
 js(out/'independent_verification.json',dict(status='PASS',scope='All saved parameters and state designs independently reconstruct predictions and target identities; not nonlinear optimizer certification',rows=checked,max_prediction_error=maxerr,code_sha256=sha(__file__),receipt_sha256=sha(out/'verification.json')))
 print('PASS',checked,maxerr)
if __name__=='__main__':run()

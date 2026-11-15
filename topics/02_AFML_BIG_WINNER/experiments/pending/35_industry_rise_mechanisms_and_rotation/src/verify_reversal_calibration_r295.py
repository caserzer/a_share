"""Independent weighted logistic objective, maturity and probability evaluation."""
from common import *
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

def run():
 out=ROOT/'outputs/r295';c=pd.read_parquet(out/'calibration_rows.parquet');p=pd.read_parquet(out/'predictions.parquet');folds=json.loads((out/'folds.json').read_text());summary=pd.read_csv(out/'summary.csv');checks=[]
 for f in folds:
  if f['status']!='fit':continue
  mask=lambda d:d.era.eq(f['era'])&d.level.eq(f['level'])&d.year.eq(f['year'])&d.variant.eq(f['variant'])
  ca=c[mask(c)];te=p[mask(p)];boundary=pd.Timestamp(f['year'],1,1);start=pd.Timestamp(f['year']-1,7,1)
  assert ca.date.ge(start).all() and ca.date.lt(boundary).all() and ca.maturity20.lt(boundary).all() and pd.Timestamp(f['fit_max_maturity'])<start
  assert len(ca)>=100 and ca.date.dt.to_period('M').nunique()>=4 and ca.y.value_counts().min()>=10
  totals=ca.groupby('date').weight.sum();assert np.allclose(totals, f['monthly_n_cal']/len(totals)) and np.isclose(ca.weight.sum(),f['monthly_n_cal'])
  x=np.column_stack([ca.linear,np.ones(len(ca))]);y=ca.y.to_numpy();w=ca.weight.to_numpy()
  def objective(b):
   z=x@b;return float(np.sum(w*(np.logaddexp(0,z)-y*z))+.5*b[0]**2)
  def gradient(b):return x.T@(w*(expit(x@b)-y))+np.array([b[0],0.])
  opt=minimize(objective,np.zeros(2),jac=gradient,method='BFGS',options={'gtol':1e-8,'maxiter':2000});saved=np.array([f['coefficient'],f['intercept']]);gap=objective(saved)-objective(opt.x)
  # Numerical replication tolerance only, never a scientific acceptance threshold.
  normalized_gradient=float(np.max(np.abs(gradient(saved)))/w.sum());assert normalized_gradient<2e-4 and gap>=-1e-7 and gap/max(1,w.sum())<1e-6
  pred=expit(te.linear*saved[0]+saved[1]);assert np.allclose(pred,te.daily_probability,atol=1e-14)
  error=float(np.max(np.abs(expit(te.linear*opt.x[0]+opt.x[1])-pred)))
  independent_p=expit(te.linear*opt.x[0]+opt.x[1]);brier_shift=pd.DataFrame({'date':te.date,'delta':(independent_p-te.y)**2-(pred-te.y)**2}).groupby('date').delta.mean().mean()
  checks.append(dict(era=f['era'],level=f['level'],year=f['year'],variant=f['variant'],normalized_gradient=normalized_gradient,objective_gap=gap,date_equal_brier_optimizer_shift=float(brier_shift),independent_probability_max_difference=error,optimizer_message=str(opt.message)))
  valid=te[te.y.notna()]
  for method in ['monthly','daily']:
   prob=valid[method+'_probability'].to_numpy();target=valid.y.to_numpy();a=pd.DataFrame({'date':valid.date,'brier':(prob-target)**2,'logloss':-target*np.log(np.clip(prob,1e-15,1-1e-15))-(1-target)*np.log(np.clip(1-prob,1e-15,1-1e-15)),'gap':prob-target});means=a.groupby('date').mean().mean();row=summary[mask(summary)&summary.method.eq(method)].iloc[0]
   for key in means.index:assert np.isclose(means[key],row[key],atol=1e-12)
 # Identical outcome population for all three variants, including unknown outcomes.
 for _,g in p.groupby(['era','level','year']):
  base=g[g.variant.eq('base')].set_index(KEY+['date'])[['y','maturity20']].sort_index()
  for v in ['state','interaction']:pd.testing.assert_frame_equal(base,g[g.variant.eq(v)].set_index(KEY+['date'])[['y','maturity20']].sort_index())
 old=pd.read_parquet(ROOT/'outputs/r286/scores.parquet');old=old[old.eligible]
 joined=p.merge(old[KEY+['date','variant','year','score','y']],on=KEY+['date','variant','year'],suffixes=('','_old'),how='outer',indicator=True,validate='one_to_one')
 assert joined._merge.eq('both').all() and np.allclose(joined.monthly_probability,joined.score,atol=1e-10)
 assert ((joined.y==joined.y_old)|(joined.y.isna()&joined.y_old.isna())).all()
 receipt=json.loads((out/'receipt.json').read_text())
 for name,h in receipt['inputs'].items():assert sha(ROOT/name)==h
 assert sha(CACHE/'forecast_v5/CSI_ALL.parquet')==receipt['market_sha256']
 assert sha(ROOT/'protocols/r295.json')==receipt['protocol_sha256'] and sha(ROOT/'src/daily_reversal_calibration_r295.py')==receipt['code_sha256']
 js(out/'output_hashes.json',{name:sha(out/name) for name in ['folds.json','predictions.parquet','calibration_rows.parquet','summary.csv','bins.json']})
 js(out/'optimizer_checks.json',checks);js(out/'independent_verification.json',dict(status='PASS',folds=len(checks),predictions=len(p),calibration_rows=len(c),max_optimizer_probability_difference=max(x['independent_probability_max_difference'] for x in checks),scope='Maturity/weights, independent optimization on saved linear scores, exact prediction and date-equal metrics; upstream features covered by frozen replay, not rederived here',adoption=False))
 print('VERIFIED',len(checks),len(p),max(x['independent_probability_max_difference'] for x in checks))
if __name__=='__main__':run()

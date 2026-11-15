from common import *
import pandas as pd
import re,math

def run():
 o=ROOT/'outputs/r281';p=pd.read_parquet(o/'panel.parquet');pred=pd.read_parquet(o/'predictions.parquet');models=json.loads((o/'models.json').read_text());checks=0;err=0.
 old=pd.read_parquet(ROOT/'outputs/r277/predictions.parquet');keys=KEY+['date','horizon','year','method','variant'];paired=pred[pred.method.isin(old.method.unique())].merge(old,on=keys,validate='one_to_one',suffixes=('_new','_old'));assert len(paired)==len(old)==756;assert np.max(abs(paired.prediction_new-paired.prediction_old))<1e-14
 assert json.loads((o/'fold_ledger.json').read_text())==json.loads((ROOT/'outputs/r277/fold_ledger.json').read_text())
 import math
 for _,r in p.iterrows():
  angle=2*math.pi*(int(r.economic_month[-2:])-1)/12;assert abs(r.annual_sin-math.sin(angle))<1e-14 and abs(r.annual_cos-math.cos(angle))<1e-14
 basiserr=0.;basisrows=0
 for m in [x for x in models if x['method']=='DR']:
  q=p[p.date.dt.year.eq(m['year'])&p.export_eligible].copy()
  for k in KEY:q=q[q[k]==m[k]]
  width=len(m['columns']);coeff=np.array(m['coef']);mu=np.array(m['mean']);sd=np.array(m['scale']);dindex=m['columns'].index('log_installation');rindex=m['columns'].index('export_log_ratio')
  for _,row in q.iterrows():
   flags=np.array([float(row.regime==s) for s in ['down_high','up_low','up_high']]);weights=coeff[:width].copy();intercept=m['intercept']
   if m['variant']!='base':intercept+=flags@coeff[width:width+3]
   if m['variant']=='interaction':
    for j,flag in enumerate(flags):weights+=flag*coeff[width+3+j*width:width+3+(j+1)*width]
   raw=weights/sd;intercept-=np.dot(raw,mu);other=[i for i in range(width) if i not in [dindex,rindex]]
   value=intercept+sum(raw[i]*row[m['columns'][i]] for i in other)+(raw[dindex]-raw[rindex])*row.log_installation+raw[rindex]*row.log_export
   saved=pred[(pred.date==row.date)&(pred.method=='DR')&(pred.variant==m['variant'])&(pred.horizon==m['horizon'])]
   for k in KEY:saved=saved[saved[k]==m[k]]
   assert len(saved)==1;e=abs(value-saved.prediction.iloc[0]);assert e<1e-12;basiserr=max(basiserr,e);basisrows+=1
 for m in models:
  g=p.copy()
  for k in KEY:g=g[g[k]==m[k]]
  b=pd.Timestamp(m['year'],1,1);h=m['horizon'];tr=g[g.export_eligible & g.date.lt(b)&g[f'maturity{h}'].lt(b)&g[f'excess{h}'].notna()];te=g[g.export_eligible & g.date.dt.year.eq(m['year'])];assert len(tr)==m['train_n'] and tr.date.nunique()>=24
  vals=tr[m['columns']].to_numpy();mu=vals.mean(axis=0);sd=vals.std(axis=0);sd[sd==0]=1;assert np.max(abs(mu-m['mean']))<1e-12;assert np.max(abs(sd-m['scale']))<1e-12
  def design(frame):
   out=[]
   for _,r in frame.iterrows():
    z=(r[m['columns']].to_numpy(float)-mu)/sd;flags=[float(r.regime==s) for s in ['down_high','up_low','up_high']];a=[1.]+list(z)
    if m['variant']!='base':a+=flags
    if m['variant']=='interaction':a+=[f*v for f in flags for v in z]
    out.append(a)
   return np.array(out)
  x=design(tr);xt=design(te);coef=np.linalg.solve(x.T@x+np.diag([0]+[10]*(x.shape[1]-1)),x.T@tr[f'excess{h}'].to_numpy());actual=pred.copy()
  for k in KEY+['horizon','year','method','variant']:actual=actual[actual[k]==m[k]]
  actual=actual.set_index('date').loc[te.date];e=float(max(abs(xt@coef-actual.prediction.to_numpy())));assert e<1e-10;err=max(err,e)
 for r in pd.read_csv(o/'metrics.csv').to_dict('records'):
  g=pred.copy()
  for k in KEY+['horizon']:g=g[g[k]==r[k]]
  if r['period'].startswith('year:'):g=g[g.year==int(r['period'][5:])]
  if r['period'].startswith('state:'):g=g[g.regime==r['period'][6:]]
  a,v=r['first'].split('/');b,w=r['second'].split('/');aa=g[(g.method==a)&(g.variant==v)].set_index('date');bb=g[(g.method==b)&(g.variant==w)].set_index('date');z=aa.join(bb[['prediction']],rsuffix='_control').dropna(subset=['target']);assert len(z)==r['n']
  if len(z):assert abs(((z.prediction_control-z.target)**2-(z.prediction-z.target)**2).mean()-r['mse_improvement'])<1e-12
 receipt=json.loads((o/'receipt.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(ROOT/f)==h
 for f,h in receipt['outputs'].items():assert sha(o/f)==h
 js(o/'independent_verification.json',dict(status='PASS',original_predictions_unchanged=len(paired),basis_conversion_rows=basisrows,basis_conversion_error=basiserr,models_reconstructed=len(models),predictions=len(pred),max_error=err,scope='Exact prior controls and folds; independent training scaling, design, normal equations, paired MSE; DR raw coefficient basis conversion. Not causality or future certification'))
 print('PASS',len(models),len(pred),err)
if __name__=='__main__':run()

from common import *
import pandas as pd
from scipy.special import expit
from scipy.stats import rankdata

def run():
 out=ROOT/'outputs/r263';p=pd.read_parquet(ROOT/'outputs/r262/panel.parquet');ledger=json.loads((out/'fold_ledger.json').read_text());models=json.loads((out/'models.json').read_text());pred=pd.read_parquet(out/'predictions.parquet');checked=0;err=0.
 def split(era,level,task,h,year):
  g=p[p.era.eq(era)&p.level.eq(level)].copy()
  if task=='onset':
   g['y']=((g[f'return{h}']>=(.05 if h==20 else .10))&(g[f'excess{h}']>=(.03 if h==20 else .05))).astype(float).where(g[f'excess{h}'].notna());ok=g.past_excess20<=0
  else:
   g['y']=(g[f'rel_trough{h}']<=(-.08 if h==20 else -.12)).astype(float).where(g[f'excess{h}'].notna()&g[f'rel_trough{h}'].notna());ok=(g.past_excess60>0)&(g.mom60>0)
  q=g[ok];cut=pd.Timestamp(year-1,7,1);start=pd.Timestamp(year,1,1);tr=q[q.date.lt(cut)&q[f'maturity{h}'].lt(cut)&q.y.notna()];ca=q[q.date.ge(cut)&q.date.lt(start)&q[f'maturity{h}'].lt(start)&q.y.notna()];te=q[q.date.dt.year.eq(year)];return g,tr,ca,te
 for f in ledger:
  g,tr,ca,te=split(f['era'],f['level'],f['task'],f['horizon'],f['year']);tc=[int(tr.y.eq(x).sum()) for x in [0,1]];cc=[int(ca.y.eq(x).sum()) for x in [0,1]];fail=[]
  if len(tr)<300 or tr.date.nunique()<18:fail.append('train_history')
  if min(tc)<30:fail.append('train_classes')
  if len(ca)<100 or ca.date.nunique()<4 or min(cc)<10:fail.append('calibration')
  assert f['failures']==fail and f['fit_classes']==tc and f['cal_classes']==cc and f['test_rows']==len(te)
 for m in models:
  g,tr,ca,te=split(m['era'],m['level'],m['task'],m['horizon'],m['year']);cols=m['columns'];r=pd.DataFrame(index=g.index,columns=cols,dtype=float)
  for _,z in g.groupby('date'):
   for c in cols:r.loc[z.index,c]=(rankdata(z[c])-.5)/len(z)-.5
  mean=r.loc[tr.index].mean().to_numpy();scale=r.loc[tr.index].std(ddof=0).to_numpy();scale=np.where(scale==0,1,scale);assert np.allclose(mean,m['mean']) and np.allclose(scale,m['scale'])
  x=(r.loc[te.index].to_numpy()-mean)/scale;u=np.column_stack([te.regime.eq(s).to_numpy(float) for s in ['down_high','up_low','up_high']]);parts=[x]
  if m['variant']!='base':parts.append(u)
  if m['variant']=='interaction':parts.extend(x*u[:,j,None] for j in range(3))
  score=np.column_stack(parts)@np.array(m['coef'])+m['intercept'];probs=expit(m['cal_coef']*score+m['cal_intercept']);mask=np.ones(len(pred),bool)
  for k in ['era','level','task','horizon','year','method','variant']:mask&=pred[k].eq(m[k]).to_numpy()
  z=pred[mask].set_index(KEY+['date']).loc[te.set_index(KEY+['date']).index];assert np.allclose(z.y,te.y,equal_nan=True);e=float(np.max(np.abs(z.prediction-probs)));assert e<1e-12;err=max(err,e);checked+=len(z)
 d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);groups=['era','level','task','horizon','method','variant','date'];lookup=d.set_index(groups)
 for k,z in pred.groupby(groups):
  v=z[z.y.notna()];assert np.isclose(((v.prediction-v.y)**2).mean(),lookup.loc[k,'brier'],equal_nan=True)
 js(out/'independent_verification.json',dict(status='PASS',folds=len(ledger),models=len(models),prediction_checks=checked,max_error=err,scope='Independent labels, eligibility, maturity splits, gates, scipy ranks, saved-coefficient probabilities and Brier; optimizer optimality and economic value not certified',adoption=False));print('VERIFIED',len(models),checked,err)
if __name__=='__main__':run()

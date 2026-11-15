from common import *
import pandas as pd
from scipy.stats import rankdata,spearmanr,norm

def run():
 import sys
 out=ROOT/'outputs/r269'/sys.argv[1];p=pd.read_parquet(out/'panel.parquet');pred=pd.read_parquet(out/'predictions.parquet');models=json.loads((out/'models.json').read_text());folds=json.loads((out/'fold_ledger.json').read_text());maxerr=0.;checks=0
 for f in folds:
  g=p[p.era.eq(f['era'])&p.level.eq(f['level'])];boundary=pd.Timestamp(f['year'],1,1);tr=g[g.date.lt(boundary)&g[f"maturity{f['horizon']}"].lt(boundary)&g[f"excess{f['horizon']}"].notna()];assert len(tr)==f['train_rows'] and tr.date.nunique()==f['train_dates'];assert (f['status']=='fit')==(len(tr)>=300 and tr.date.nunique()>=18)
 for m in models:
  h=m['horizon'];g=p[p.era.eq(m['era'])&p.level.eq(m['level'])];boundary=pd.Timestamp(m['year'],1,1);tr=g[g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(m['year'])];cols=m['columns'];ranks=pd.DataFrame(index=g.index,columns=cols,dtype=float)
  for _,z in g.groupby('date'):
   for col in cols:ranks.loc[z.index,col]=(rankdata(z[col])-.5)/len(z)-.5
  mean=ranks.loc[tr.index].mean().to_numpy();scale=ranks.loc[tr.index].std(ddof=0).to_numpy();scale=np.where(scale==0,1,scale);assert np.allclose(mean,m['mean']) and np.allclose(scale,m['scale'])
  def design(frame):
   x=(ranks.loc[frame.index].to_numpy()-mean)/scale;u=np.column_stack([frame.regime.eq(s).to_numpy(float) for s in ['down_high','up_low','up_high']]);parts=[np.ones((len(frame),1)),x]
   if m['variant']!='base':parts.append(u)
   if m['variant']=='interaction':parts.extend([x*u[:,j,None] for j in range(3)])
   return np.column_stack(parts)
  x=design(tr);xx=design(te);w=len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size').to_numpy());pen=np.eye(x.shape[1])*10;pen[0,0]=0;coef=np.linalg.solve(x.T@(w[:,None]*x)+pen,x.T@(w*tr[f'excess{h}'].to_numpy()));forecast=xx@coef
  z=pred[pred.era.eq(m['era'])&pred.level.eq(m['level'])&pred.year.eq(m['year'])&pred.horizon.eq(h)&pred.method.eq(m['method'])&pred.variant.eq(m['variant'])].set_index(KEY+['date']).loc[te.set_index(KEY+['date']).index];err=float(np.max(np.abs(forecast-z.prediction)));assert err<1e-10;maxerr=max(maxerr,err);checks+=len(z)
 metrics=pd.read_parquet(out/'metrics.parquet').set_index(['era','level','horizon','variant','method','date'])
 for k,g in pred.groupby(['era','level','horizon','variant','method','date']):
  v=g[g.target.notna()];ic=spearmanr(v.prediction,v.target).statistic if len(v)>=5 and v.prediction.nunique()>1 and v.target.nunique()>1 else np.nan;row=metrics.loc[k];assert np.isclose(ic,row.ic,equal_nan=True) and np.isclose(np.mean((v.prediction-v.target)**2),row.mse,equal_nan=True)
 dates=pd.read_parquet(out/'paired_dates.parquet');summary=pd.read_csv(out/'summary.csv');assert len(summary)==120
 for row in summary.itertuples():
  if row.status=='no_fit':continue
  g=dates[(dates.era==row.era)&(dates.level==row.level)&(dates.horizon==row.horizon)&(dates.variant==row.variant)&(dates.comparison==row.comparison)].sort_values('date');n=len(g);assert n==row.months
  if n<2:continue
  u=g.ic_delta.to_numpy()-g.ic_delta.mean();months=g.date.dt.to_period('M').astype('int64').to_numpy();lag=3 if row.horizon==20 else 6;var=sum(u*u)
  for i in range(n):
   for j in range(i):
    distance=months[i]-months[j]
    if 0<distance<=lag:var+=2*(1-distance/(lag+1))*u[i]*u[j]
  se=np.sqrt(max(var,0))/n;bounds=g.ic_delta.mean()+np.array([-1,1])*norm.ppf(1-.05/840)*se;assert np.allclose(bounds,[row.low_family,row.high_family],atol=1e-12)
 js(out/'independent_verification.json',dict(status='PASS',folds=len(folds),models=len(models),normal_equation_prediction_checks=checks,max_prediction_error=maxerr,metric_groups=len(metrics),planned_comparisons=120,scope='Independent ranks, weighted normal equations, gates, Spearman and calendar pair-loop intervals; not forecasting certification',adoption=False));print('VERIFIED',len(models),checks,maxerr)
if __name__=='__main__':run()

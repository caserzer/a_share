"""Preregistered small time-series pilot, separated from cross-sectional models."""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from common import *
from train_r02 import F

def panel():
 coverage=pd.DataFrame(json.loads((ROOT/'outputs/r52/signal_coverage.json').read_text()));coverage['date']=pd.to_datetime(coverage.date)
 p=pd.read_parquet(ROOT/'data/monthly_panel.parquet');p['log_members']=np.log(p.members)
 p=p.merge(coverage[KEY+['date','economic_month','log_yoy','growth_available_at']],on=KEY+['date'],how='inner',validate='one_to_one')
 p=p.merge(pd.read_parquet(ROOT/'data/r30_size_control.parquet',columns=KEY+['date','size_control']),on=KEY+['date'],how='left',validate='one_to_one')
 return p[p.price_ready].dropna(subset=F+['size_control','log_yoy']).sort_values(KEY+['date'])

def run():
 out=ROOT/'outputs/r53';out.mkdir(exist_ok=True);p=panel();protocol=json.loads((ROOT/'protocols/r53.json').read_text());methods={k:v for k,v in protocol['methods'].items() if k!='mean'};preds=[];folds=[];params=[]
 for identity,g in p.groupby(KEY):
  for h in [20,60]:
   for year in sorted(g.date.dt.year.unique()):
    boundary=pd.Timestamp(int(year),1,1);tr=g[g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(year)]
    ready=tr.date.nunique()>=protocol['minimum_train_months'];rec=dict(zip(KEY,identity));rec.update(horizon=h,year=int(year),train_n=len(tr),test_n=len(te),max_train_maturity=str(tr[f'maturity{h}'].max()),status='fit' if ready else 'skip')
    folds.append(rec)
    if not ready:continue
    assert (pd.to_datetime(tr.growth_available_at)<=tr.date).all()
    for name,cols in methods.items():
     scaler=StandardScaler().fit(tr[cols]);model=Ridge(alpha=10).fit(scaler.transform(tr[cols]),tr[f'excess{h}']);est=model.predict(scaler.transform(te[cols]))
     params.append(dict(**rec,method=name,columns=cols,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_)))
     for (_,x),value in zip(te.iterrows(),est):
      preds.append(dict(**dict(zip(KEY,identity)),horizon=h,year=int(year),date=x.date.isoformat(),maturity=str(x[f'maturity{h}']),economic_month=x.economic_month,method=name,prediction=float(value),target=float(x[f'excess{h}']) if pd.notna(x[f'excess{h}']) else None,mean_prediction=float(tr[f'excess{h}'].mean())))
 js(out/'fold_ledger.json',folds);js(out/'model_parameters.json',params);js(out/'predictions.json',preds)
 results=[];df=pd.DataFrame(preds)
 for (era,level,code,h),g in df.groupby(KEY+['horizon']):
  a=g[g.method.eq('FS')].set_index('date');b=g[g.method.eq('FSB')].set_index('date');assert a.index.equals(b.index);valid=a.target.notna();a=a[valid];b=b[valid]
  for label,dates in [('all',a.index)]+[(str(y),a.index[a.year.eq(y)]) for y in sorted(a.year.unique())]:
   x=a.loc[dates];y=b.loc[dates];n=len(x)
   mse_fs=float(((x.target-x.prediction)**2).mean());mse_fsb=float(((y.target-y.prediction)**2).mean())
   results.append(dict(era=era,level=level,industry_code=code,horizon=int(h),period=label,n=n,years=int(x.year.nunique()),mse_FS=mse_fs,mse_FSB=mse_fsb,mse_mean=float(((x.target-x.mean_prediction)**2).mean()),mae_FS=float((x.target-x.prediction).abs().mean()),mae_FSB=float((y.target-y.prediction).abs().mean()),mse_improvement=mse_fs-mse_fsb,stability_sample_gate=bool(n>=24 and x.year.nunique()>=3),inference='descriptive historical pilot; no independent forward validation'))
 js(out/'metrics.json',results)
 paths=[ROOT/'protocols/r53.json',ROOT/'outputs/r52/signal_coverage.json',ROOT/'outputs/r51/frozen_monthly_series.json',ROOT/'data/monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',Path(__file__),ROOT/'src/train_r02.py']
 js(out/'receipt.json',dict(inputs={str(x):sha(x) for x in paths},fits=sum(x['status']=='fit' for x in folds),skips=sum(x['status']=='skip' for x in folds),prediction_rows=len(preds),overall_goal='active'))
 print(json.dumps([x for x in results if x['period']=='all'],ensure_ascii=False))

if __name__=='__main__':run()

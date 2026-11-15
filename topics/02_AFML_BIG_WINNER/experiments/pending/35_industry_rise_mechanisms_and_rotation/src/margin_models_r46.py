import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from common import *
from train_r02 import F,sample_weights
from evaluate_size_r31 import interval

METHODS={'FS':F+['size_control'],'FSE':F+['size_control','financing_intensity']}
def panel():
 p=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet'),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')],ignore_index=True);p['log_members']=np.log(p.members)
 for path,cols in [('data/r30_size_control.parquet',['size_control']),('data/r45_financing_intensity.parquet',['financing_intensity'])]:p=p.merge(pd.read_parquet(ROOT/path,columns=KEY+['date']+cols),on=KEY+['date'],how='left',validate='one_to_one')
 return p[p.price_ready].dropna(subset=METHODS['FSE'])

def run():
 out=ROOT/'outputs/r46';out.mkdir(exist_ok=True);p=panel();folds=[];params=[];preds=[]
 for (era,level),g in p.groupby(['era','level']):
  rank=g.groupby('date')[METHODS['FSE']].transform(centered_rank)
  for h in [20,60]:
   for year in sorted(g.date.dt.year.unique()):
    boundary=pd.Timestamp(int(year),1,1);tr=g[g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(year)];ready=len(tr)>=300 and tr.date.nunique()>=18
    rec=dict(era=era,level=level,horizon=h,year=int(year),train_rows=len(tr),train_months=tr.date.nunique(),test_rows=len(te),status='fit' if ready else 'skip');folds.append(rec)
    if not ready:continue
    for name,cols in METHODS.items():
     scaler=StandardScaler().fit(rank.loc[tr.index,cols]);model=Ridge(alpha=10).fit(scaler.transform(rank.loc[tr.index,cols]),tr[f'excess{h}'],sample_weight=sample_weights(tr))
     q=te[KEY+['date',f'excess{h}',f'maturity{h}']].rename(columns={f'excess{h}':'target',f'maturity{h}':'maturity'}).copy();q['prediction']=model.predict(scaler.transform(rank.loc[te.index,cols]));q['method']=name;q['horizon']=h;q['year']=int(year);preds.append(q)
     params.append(dict(**rec,method=name,columns=cols,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_)))
 pred=pd.concat(preds,ignore_index=True);pred.to_parquet(out/'predictions.parquet',index=False);js(out/'fold_ledger.json',folds);js(out/'model_parameters.json',params)
 metrics=[]
 for key,g in pred.groupby(['era','level','horizon','method','date']):
  q=g.dropna(subset=['target']);ic=q.prediction.corr(q.target,method='spearman') if len(q)>=5 and q.prediction.nunique()>1 and q.target.nunique()>1 else np.nan
  metrics.append(dict(zip(['era','level','horizon','method','date'],key),n=len(q),mse=float(((q.prediction-q.target)**2).mean()),ic=ic))
 m=pd.DataFrame(metrics);m.to_parquet(out/'metrics_by_date.parquet',index=False);results=[];annual=[]
 for key,g in m.groupby(['era','level','horizon']):
  w=g.pivot(index='date',columns='method',values=['ic','mse']);ic=w['ic']['FSE']-w['ic']['FS'];improvement=w['mse']['FS']-w['mse']['FSE'];lo,hi=interval(ic,3 if key[2]==20 else 6);years=ic.dropna().groupby(ic.dropna().index.year).mean()
  results.append(dict(zip(['era','level','horizon'],key),ic_months=int(ic.count()),ic_increment=float(ic.mean()),low99=float(lo),high99=float(hi),mse_improvement=float(improvement.mean()),years=len(years),positive_years=int(years.gt(0).sum()),historical_support=bool(ic.count()>=24 and len(years)>=3 and years.gt(0).all() and lo>0)))
  for year,z in ic.groupby(ic.index.year):annual.append(dict(zip(['era','level','horizon'],key),year=int(year),ic_months=int(z.count()),ic_increment=float(z.mean())))
 js(out/'increments.json',results);js(out/'annual_increments.json',annual)
 paths=[ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',ROOT/'data/r45_financing_intensity.parquet',ROOT/'protocols/r46.json',ROOT/'src/train_r02.py',ROOT/'src/evaluate_size_r31.py',Path(__file__)]
 js(out/'receipt.json',dict(inputs={str(x):sha(x) for x in paths},fits=sum(x['status']=='fit' for x in folds),skips=sum(x['status']=='skip' for x in folds),prediction_rows=len(pred),prediction_sha256=sha(out/'predictions.parquet')))
 print(json.dumps(clean(results),ensure_ascii=False))

if __name__=='__main__':run()

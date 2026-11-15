import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from common import *
from train_r02 import F,sample_weights

METHODS={'F':F,'FD':F+['breadth21','breadth63'],'FS':F+['size_control'],'FDS':F+['breadth21','breadth63','size_control']}
def base_panel():
 p=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet'),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')],ignore_index=True);p['log_members']=np.log(p.members)
 p=p.merge(pd.read_parquet(ROOT/'data/r30_size_control.parquet')[KEY+['date','size_control']],on=KEY+['date'],how='left',validate='one_to_one')
 return p[p.price_ready].dropna(subset=METHODS['FDS'])
def run():
 out=ROOT/'outputs/r31';out.mkdir(exist_ok=True);p=base_panel();preds=[];params=[];folds=[]
 for (era,level),g in p.groupby(['era','level']):
  ranks=g.groupby('date')[METHODS['FDS']].transform(centered_rank)
  for h in [20,60]:
   for year in range(2020,2027):
    boundary=pd.Timestamp(year,1,1);tr=g[g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(year)]
    if te.empty:continue
    ready=len(tr)>=300 and tr.date.nunique()>=18
    rec=dict(era=era,level=level,horizon=h,year=year,train_rows=len(tr),train_months=tr.date.nunique(),test_rows=len(te),max_maturity=tr[f'maturity{h}'].max())
    folds.append(dict(rec,status='fit' if ready else 'skip'))
    if not ready:continue
    for method,cols in METHODS.items():
     scaler=StandardScaler().fit(ranks.loc[tr.index,cols]);model=Ridge(alpha=10).fit(scaler.transform(ranks.loc[tr.index,cols]),tr[f'excess{h}'],sample_weight=sample_weights(tr))
     q=te[KEY+['date',f'excess{h}',f'maturity{h}']].rename(columns={f'excess{h}':'target',f'maturity{h}':'maturity'}).copy();q['row_id']=te.index;q['prediction']=model.predict(scaler.transform(ranks.loc[te.index,cols]));q['method']=method;q['horizon']=h;q['year']=year;preds.append(q)
     params.append(dict(rec,method=method,columns=cols,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_)))
  print('R31 fitted',era,level,flush=True)
 pred=pd.concat(preds,ignore_index=True);pred.to_parquet(out/'predictions.parquet',index=False);pd.DataFrame(folds).to_csv(out/'fold_ledger.csv',index=False);js(out/'model_parameters.json',params)
 paths=[ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',ROOT/'protocols/r31.json',Path(__file__),ROOT/'src/common.py',ROOT/'src/train_r02.py']
 js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},prediction_sha256=sha(out/'predictions.parquet'),rows=len(pred),fits=sum(x['status']=='fit' for x in folds),skips=sum(x['status']=='skip' for x in folds)))
if __name__=='__main__':run()

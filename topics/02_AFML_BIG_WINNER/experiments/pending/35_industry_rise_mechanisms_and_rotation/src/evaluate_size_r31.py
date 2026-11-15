import pandas as pd
from common import *

def interval(z,lag):
 z=z.dropna().sort_index();n=len(z)
 if n<2:return np.nan,np.nan
 periods=pd.DatetimeIndex(z.index).to_period('M').astype('int64');u=pd.Series(z.to_numpy()-z.mean(),index=periods);v=float((u*u).sum())
 for k in range(1,lag+1):
  previous=u.reindex(u.index-k).to_numpy();v+=2*(1-k/(lag+1))*float(np.nansum(u.to_numpy()*previous))
 se=np.sqrt(max(v,0))/n;return z.mean()-2.5758293035489004*se,z.mean()+2.5758293035489004*se

def run():
 out=ROOT/'outputs/r31';p=pd.read_parquet(out/'predictions.parquet');metrics=[]
 keys=['era','level','horizon','method','date']
 for key,g in p.groupby(keys):
  q=g.dropna(subset=['target']);ic=q.prediction.corr(q.target,method='spearman') if len(q)>=5 and q.prediction.nunique()>1 and q.target.nunique()>1 else np.nan
  metrics.append(dict(zip(keys,key),origins=len(g),complete=len(q),mse=((q.prediction-q.target)**2).mean(),ic=ic))
 m=pd.DataFrame(metrics);m.to_csv(out/'metrics_by_date.csv',index=False)
 m.groupby(keys[:-1]).agg(months=('mse','count'),ic_months=('ic','count'),mse=('mse','mean'),ic=('ic','mean')).to_csv(out/'summary.csv')
 m.assign(year=m.date.dt.year).groupby(keys[:-1]+['year']).agg(months=('mse','count'),mse=('mse','mean'),ic=('ic','mean')).to_csv(out/'annual.csv')
 increments=[];annual=[];series=[]
 for key,g in m.groupby(['era','level','horizon']):
  w=g.pivot(index='date',columns='method',values=['mse','ic'])
  for name,a,b in [('diffusion_without_size','FD','F'),('diffusion_with_size','FDS','FS'),('size_without_diffusion','FS','F')]:
   for metric in ['mse','ic']:
    d=w[metric][a]-w[metric][b];lo,hi=interval(d,3 if key[2]==20 else 6)
    increments.append(dict(zip(['era','level','horizon'],key),comparison=name,metric=metric,months=int(d.count()),mean=d.mean(),low99=lo,high99=hi))
    for date,value in d.items():series.append(dict(zip(['era','level','horizon'],key),comparison=name,metric=metric,date=date,delta=value))
    for year,z in d.groupby(d.index.year):annual.append(dict(zip(['era','level','horizon'],key),comparison=name,metric=metric,year=year,months=int(z.count()),mean=z.mean()))
 pd.DataFrame(increments).to_csv(out/'increments.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual_increments.csv',index=False);pd.DataFrame(series).to_csv(out/'paired_by_date.csv',index=False)
 print(pd.DataFrame(increments).query("comparison=='diffusion_with_size' and horizon==20").to_string(index=False))
if __name__=='__main__':run()

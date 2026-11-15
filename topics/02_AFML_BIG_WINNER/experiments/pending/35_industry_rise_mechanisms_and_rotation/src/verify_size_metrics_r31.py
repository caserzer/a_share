import sys
from pathlib import Path
r=Path('/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation');sys.path.insert(0,str(r/'src'))
import pandas as pd
from common import *
out=r/'outputs/r31';p=pd.read_parquet(out/'predictions.parquet');m=pd.read_csv(out/'metrics_by_date.csv',parse_dates=['date']);keys=['era','level','horizon','method','date'];look=m.set_index(keys)
for key,g in p.groupby(keys):
 q=g.dropna(subset=['target']);row=look.loc[key];assert row.complete==len(q) and row.origins==len(g)
 mse=np.mean(np.square(q.prediction-q.target));ic=q.prediction.rank().corr(q.target.rank()) if len(q)>=5 and q.prediction.nunique()>1 and q.target.nunique()>1 else np.nan
 assert np.isclose(row.mse,mse,equal_nan=True) and np.isclose(row.ic,ic,equal_nan=True)
incs=pd.read_csv(out/'increments.csv');d=pd.read_csv(out/'paired_by_date.csv',parse_dates=['date'])
for row in incs.itertuples():
 z=d[d.era.eq(row.era)&d.level.eq(row.level)&d.horizon.eq(row.horizon)&d.comparison.eq(row.comparison)&d.metric.eq(row.metric)].dropna(subset=['delta']);v=z.delta.to_numpy();u=v-v.mean();t=z.date.dt.to_period('M').astype('int64').to_numpy();lag=3 if row.horizon==20 else 6;k=np.maximum(1-np.abs(t[:,None]-t[None,:])/(lag+1),0);se=np.sqrt(max(u@k@u,0))/len(v)
 assert row.months==len(v) and np.isclose(row.mean,v.mean()) and np.isclose(row.low99,v.mean()-2.5758293035489004*se) and np.isclose(row.high99,v.mean()+2.5758293035489004*se)
js(out/'metrics_verification.json',dict(status='PASS',metric_rows=len(m),intervals=len(incs),method='independent rank correlation and explicit calendar Bartlett covariance matrix'))
print('METRICS VERIFIED',len(m),len(incs))

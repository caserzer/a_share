"""Close the L1 continuation coverage omission under the original R10 rules."""
import pandas as pd
from common import *
from followup_r10 import path_metrics

def run():
 out=ROOT/'outputs/r168';ap=ROOT/'outputs/r159/evaluation/outputs/r09/alerts.parquet';dp=ROOT/'data/l1_daily.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet'
 a=pd.read_parquet(ap);d=pd.read_parquet(dp);market=pd.read_parquet(bp).close
 paths=pd.concat([path_metrics(g,market) for _,g in d.groupby(KEY+['block'])],ignore_index=True)
 z=a[KEY+['date','strategy','score','y','return20','excess20']].merge(paths,on=KEY+['date'],how='left',suffixes=('_r159',''),validate='many_to_one');assert len(z)==1813
 for name in ['return20','excess20']:assert np.allclose(z[name],z[name+'_r159'],equal_nan=True)
 assert np.allclose(z.y,z.success20,equal_nan=True)
 z.to_parquet(out/'followup.parquet',index=False);rows=[];continuation=[]
 for year,v in [(0,z)]+[(int(y),g) for y,g in z.groupby(z.date.dt.year)]:
  for strategy,g in v.groupby('strategy'):
   for h in [5,20,60]:
    q=g.dropna(subset=[f'return{h}',f'excess{h}'])
    rows.append(dict(year=year,strategy=strategy,horizon=h,alerts=len(g),complete=len(q),unknown=len(g)-len(q),absolute_mean=q[f'return{h}'].mean(),excess_mean=q[f'excess{h}'].mean(),mean_drawdown=q[f'drawdown{h}'].mean(),positive_absolute=q[f'return{h}'].gt(0).mean()))
   for cohort,w in [('all',g),('success20',g[g.success20.eq(1)]),('not_success20',g[g.success20.eq(0)])]:
    q=w.dropna(subset=['continuation_excess20_60'])
    continuation.append(dict(year=year,strategy=strategy,cohort=cohort,selected=len(w),complete=len(q),unknown=len(w)-len(q),absolute_increment=q.continuation20_60.mean(),relative_increment=q.continuation_excess20_60.mean(),positive_relative=q.continuation_excess20_60.gt(0).mean(),breadth_change20=q.breadth_change20.mean()))
 pd.DataFrame(rows).to_csv(out/'followup_summary.csv',index=False);c=pd.DataFrame(continuation);c.to_csv(out/'continuation.csv',index=False)
 js(out/'receipt.json',dict(status='PASS',alerts=len(z),reads={str(p):sha(p) for p in [ap,dp,bp,ROOT/'src/followup_r10.py',ROOT/'protocols/r10.json',ROOT/'protocols/r168.json',Path(__file__)]},calibrated=False,adoption=False,conditional_success_known_after20=True))
 print(c[c.year.eq(0)].to_string(index=False))
if __name__=='__main__':run()

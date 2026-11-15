"""Close the L1 continuation coverage omission under the original R10 rules."""
import pandas as pd
from common import *
from followup_r10 import path_metrics

def run():
 out=ROOT/'outputs/r170';ap=ROOT/'outputs/r160/alerts.parquet';dp=ROOT/'data/l1_daily.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet'
 a=pd.read_parquet(ap);d=pd.read_parquet(dp);market=pd.read_parquet(bp).close
 paths=pd.concat([path_metrics(g,market) for _,g in d.groupby(KEY+['block'])],ignore_index=True)
 z=a[KEY+['date','method','strategy','score','y','return20','excess20']].merge(paths,on=KEY+['date'],how='left',suffixes=('_r159',''),validate='many_to_one');assert len(z)==5474
 for name in ['return20','excess20']:assert np.allclose(z[name],z[name+'_r159'],equal_nan=True)
 assert np.allclose(z.y,z.success20,equal_nan=True)
 z.to_parquet(out/'followup.parquet',index=False);rows=[];continuation=[]
 for year,v in [(0,z)]+[(int(y),g) for y,g in z.groupby(z.date.dt.year)]:
  for (method,strategy),g in v.groupby(['method','strategy']):
   for h in [5,20,60]:
    q=g.dropna(subset=[f'return{h}',f'excess{h}'])
    rows.append(dict(year=year,method=method,strategy=strategy,horizon=h,alerts=len(g),complete=len(q),unknown=len(g)-len(q),absolute_mean=q[f'return{h}'].mean(),excess_mean=q[f'excess{h}'].mean(),mean_drawdown=q[f'drawdown{h}'].mean(),positive_absolute=q[f'return{h}'].gt(0).mean()))
   for cohort,w in [('all',g),('success20',g[g.success20.eq(1)]),('not_success20',g[g.success20.eq(0)])]:
    q=w.dropna(subset=['continuation_excess20_60'])
    continuation.append(dict(year=year,method=method,strategy=strategy,cohort=cohort,selected=len(w),complete=len(q),unknown=len(w)-len(q),absolute_increment=q.continuation20_60.mean(),relative_increment=q.continuation_excess20_60.mean(),positive_relative=q.continuation_excess20_60.gt(0).mean(),breadth_change20=q.breadth_change20.mean()))
 pd.DataFrame(rows).to_csv(out/'followup_summary.csv',index=False);c=pd.DataFrame(continuation);c.to_csv(out/'continuation.csv',index=False)
 # Same frozen raw model selections must reproduce the prior dedicated L1 result.
 prior=pd.read_parquet(ROOT/'outputs/r168/followup.parquet');keys=KEY+['date','strategy']
 now=z[z.method.eq('raw_logit')].drop(columns='method')
 pd.testing.assert_frame_equal(now.sort_values(keys).reset_index(drop=True),prior.sort_values(keys).reset_index(drop=True))
 date_rows=[]
 for (method,strategy,date),g in z.groupby(['method','strategy','date']):
  for cohort,w in [('all',g),('success20',g[g.success20.eq(1)]),('not_success20',g[g.success20.eq(0)])]:
   q=w.dropna(subset=['continuation_excess20_60']);date_rows.append(dict(method=method,strategy=strategy,date=date,cohort=cohort,selected=len(w),complete=len(q),unknown=len(w)-len(q),relative_increment=q.continuation_excess20_60.mean()))
 dm=pd.DataFrame(date_rows);dm.to_csv(out/'date_metrics.csv',index=False);pairs=[]
 for year,v in [(0,dm)]+[(int(y),g) for y,g in dm.groupby(dm.date.dt.year)]:
  for (strategy,cohort),g in v.groupby(['strategy','cohort']):
   for baseline in ['F','momentum']:
    a=g[g.method.eq('raw_logit')];b=g[g.method.eq(baseline)];pair=a.merge(b,on='date',how='outer',suffixes=('_model','_baseline'),validate='one_to_one');q=pair.dropna(subset=['relative_increment_model','relative_increment_baseline'])
    pairs.append(dict(year=year,strategy=strategy,cohort=cohort,baseline=baseline,model_dates=len(a),baseline_dates=len(b),union_dates=len(pair),joint_alert_dates=int(pair.method_model.notna().mul(pair.method_baseline.notna()).sum()),one_sided_dates=int((pair.method_model.isna()|pair.method_baseline.isna()).sum()),joint_incomplete_dates=int((pair.method_model.notna()&pair.method_baseline.notna()).sum())-len(q),matched_complete_dates=len(q),excluded_dates=len(pair)-len(q),model_mean=q.relative_increment_model.mean(),baseline_mean=q.relative_increment_baseline.mean(),delta=(q.relative_increment_model-q.relative_increment_baseline).mean()))
 pd.DataFrame(pairs).to_csv(out/'date_comparisons.csv',index=False)
 js(out/'receipt.json',dict(status='PASS',alerts=len(z),reads={str(p):sha(p) for p in [ap,dp,bp,ROOT/'outputs/r168/followup.parquet',ROOT/'outputs/r160/verification.json',ROOT/'src/followup_r10.py',ROOT/'protocols/r10.json',ROOT/'protocols/r170.json',Path(__file__)]},calibrated=False,adoption=False,conditional_success_known_after20=True))
 print(c[c.year.eq(0)].to_string(index=False))
if __name__=='__main__':run()

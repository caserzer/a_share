"""Independent inference, selection and interval-hit checks for daily replay."""
from common import *
import pandas as pd
from scipy.stats import rankdata

def run():
 out=ROOT/'outputs/r253';s=pd.read_parquet(out/'scores.parquet');a=pd.read_parquet(out/'alerts.parquet');h=pd.read_parquet(out/'event_hits.parquet')
 original=pd.read_parquet(ROOT/'outputs/r155/evaluation/data/r09_daily_scores.parquet')
 models=[m for m in json.loads((ROOT/'outputs/r196/models.json').read_text()) if m['family']=='core' and m['cohort']=='F' and m['method']=='F' and m['task']=='onset' and m['horizon']==20]
 cols=models[0]['columns'];ranks=pd.DataFrame(index=original.index,columns=cols,dtype=float)
 for _,g in original.groupby(['era','level','date']):
  for c in cols:ranks.loc[g.index,c]=(rankdata(g[c],method='average')-.5)/len(g)-.5
 errors=[]
 for m in models:
  g=original[original.era.eq(m['era'])&original.level.eq(m['level'])&original.year.eq(m['year'])]
  z=s[s.variant.eq(m['variant'])&s.era.eq(m['era'])&s.level.eq(m['level'])&s.year.eq(m['year'])].set_index(KEY+['date']).loc[g.set_index(KEY+['date']).index]
  x=(ranks.loc[g.index,cols].to_numpy()-m['scaler_mean'])/m['scaler_scale'];coef=np.array(m['coefficient']).ravel();p=x@coef[:len(cols)]+np.array(m['intercept']).item()
  if m['variant']!='base':
   for j,state in enumerate(['down_high','up_low','up_high']):
    mask=z.regime.eq(state).to_numpy();p+=mask*coef[len(cols)+j]
    if m['variant']=='interaction':p+=mask*(x@coef[len(cols)+3+j*len(cols):len(cols)+3+(j+1)*len(cols)])
  p=1/(1+np.exp(-(p*np.array(m['calibration_coefficient']).item()+np.array(m['calibration_intercept']).item())))
  error=float(np.max(np.abs(p-z.score.to_numpy())));assert error<1e-12;errors.append(error)
 # Independently select by positional ranks; then greedy session suppression.
 keys=KEY+['date'];selection_checks=0
 for variant,g in s[s.eligible].groupby('variant'):
  ordered=g.sort_values(['era','level','date','score','industry_code'],ascending=[True,True,True,False,True]);grp=ordered.groupby(['era','level','date']);chosen=ordered[grp.cumcount()<np.ceil(.2*grp.score.transform('size'))]
  got=a[a.variant.eq(variant)&a.strategy.eq('daily')];assert set(map(tuple,chosen[keys].to_numpy()))==set(map(tuple,got[keys].to_numpy()))
  keep=[]
  for _,f in chosen.groupby(KEY):
   prev=None
   for row in f.sort_values('date').itertuples():
    if prev is None or row.day_i-prev>20:keep.append((row.era,row.level,row.industry_code,row.date));prev=row.day_i
  got=a[a.variant.eq(variant)&a.strategy.eq('daily_cooldown20')];assert set(keep)==set(map(tuple,got[keys].to_numpy()));selection_checks+=len(chosen)+len(keep)
 # Independently require the final observed trading date of each completed month.
 cal=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index
 months={}
 for day in cal:
  if day.to_period('M').end_time.normalize()<=cal.max():months[day.to_period('M')]=day
 for variant in ['base','state','interaction']:
  daily=a[a.variant.eq(variant)&a.strategy.eq('daily')]
  expected_monthly=daily[daily.date.isin(list(months.values()))]
  actual_monthly=a[a.variant.eq(variant)&a.strategy.eq('monthly')]
  assert set(map(tuple,expected_monthly[keys].to_numpy()))==set(map(tuple,actual_monthly[keys].to_numpy()))
 # Reconstruct all event hits using sorted date arrays and search bounds.
 lookup={k:np.sort(g.day_i.to_numpy()) for k,g in a.groupby(['variant','strategy']+KEY+['block'])}
 for row in h.itertuples():
  days=lookup.get((row.variant,row.strategy,row.era,row.level,row.industry_code,row.block),np.array([],dtype=int))
  lo=np.searchsorted(days,row.day_i-20);hi=np.searchsorted(days,row.day_i)
  hit=bool(row.evaluable) and hi>lo;assert row.hit==hit
  assert (row.lead_sessions==row.day_i-days[lo]) if hit else pd.isna(row.lead_sessions)
 expected=pd.read_csv(ROOT/'outputs/r155/evaluation/outputs/r09/confirmation_events.csv',parse_dates=['date'])
 for _,g in h.groupby(['variant','strategy']):
  assert set(map(tuple,g[keys+['block','evaluable']].to_numpy()))==set(map(tuple,expected[keys+['block','evaluable']].to_numpy()))
 summary=pd.read_csv(out/'summary.csv');metric_checks=0
 for row in summary.itertuples():
  aa=a[a.variant.eq(row.variant)&a.strategy.eq(row.strategy)&a.era.eq(row.era)&a.level.eq(row.level)]
  hh=h[h.variant.eq(row.variant)&h.strategy.eq(row.strategy)&h.era.eq(row.era)&h.level.eq(row.level)&h.evaluable]
  assert len(aa)==row.alerts and len(hh)==row.events and hh.hit.sum()==row.hit_events
  assert np.isclose(aa.y.mean(),row.fixed_horizon_precision) and np.isclose(hh.hit.mean(),row.process_recall)
  metric_checks+=5
 js(out/'independent_verification.json',dict(status='PASS',prediction_rows=len(s),max_prediction_error=max(errors),selection_checks=selection_checks,event_hit_checks=len(h),summary_metric_checks=metric_checks,unchanged_event_catalogue=True,scope='Frozen inference and descriptive event evaluation; no daily probability recertification',adoption=False))
 print('VERIFIED',len(s),len(h),max(errors))
if __name__=='__main__':run()

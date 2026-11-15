from common import *
import pandas as pd
from itertools import combinations

def run():
 out=ROOT/'outputs/r255';a=pd.read_parquet(ROOT/'outputs/r253/alerts.parquet');a=a[a.strategy.eq('daily_cooldown20')];c=pd.read_csv(out/'date_capacity.csv',parse_dates=['date']);z=pd.read_parquet(out/'alert_assignment.parquet');h=pd.read_parquet(out/'event_expectations.parquet')
 raw={k:g for k,g in a.groupby(['era','level','date','variant'])};expected={};checks=0
 for row in c.itertuples():
  groups=[raw.get((row.era,row.level,row.date,v),pd.DataFrame()) for v in ['base',row.comparison]];k=min(map(len,groups));assert k==row.K
  for side,g in zip(['base',row.comparison],groups):
   ordered=[] if g.empty else sorted(g.itertuples(),key=lambda x:(-x.score,x.industry_code))
   for i,x in enumerate(ordered):expected[(row.comparison,side,row.era,row.level,x.industry_code,row.date)]=(i<k,k/len(g))
  checks+=1
 for row in z.itertuples():
  keep,q=expected[(row.comparison,row.variant,row.era,row.level,row.industry_code,row.date)];assert keep==row.retained and q==row.q
 assert len(expected)==len(z)
 # At most one alert per event window, so exact inclusion expectation is K/N.
 lookup={k:g for k,g in a.groupby(['variant']+KEY+['block'])}
 events=pd.read_csv(ROOT/'outputs/r155/evaluation/outputs/r09/confirmation_events.csv',parse_dates=['date']).set_index(KEY+['block','date'])
 for row in h.itertuples():
  event=events.loc[(row.era,row.level,row.industry_code,row.block,row.date)];g=lookup.get((row.side,row.era,row.level,row.industry_code,row.block));window=[] if g is None else [x for x in g.itertuples() if event.day_i-20<=x.day_i<event.day_i]
  assert len(window)<=1 and row.evaluable==event.evaluable
  val=None if not event.evaluable else 0.;keep=False
  if event.evaluable and window:
   x=window[0];keep,val=expected[(row.comparison,row.side,row.era,row.level,row.industry_code,x.date)]
  assert row.retained_hit==keep
  assert pd.isna(row.expected_hit) if val is None else np.isclose(val,row.expected_hit)
 summary=pd.read_csv(out/'summary.csv')
 for row in summary.itertuples():
  mask=lambda f: f.era.eq(row.era)&f.level.eq(row.level)&f.comparison.eq(row.comparison)
  aa=z[mask(z)&z.variant.eq(row.side)];hh=h[mask(h)&h.side.eq(row.side)];cc=c[mask(c)]
  if row.scope=='annual':aa=aa[aa.date.dt.year.eq(row.year)];hh=hh[hh.date.dt.year.eq(row.year)];cc=cc[cc.date.dt.year.eq(row.year)]
  hh=hh[hh.evaluable];kept=aa[aa.retained]
  values={'retained_alerts':len(kept),'events':len(hh),'retained_hits':hh.retained_hit.sum(),'expected_hits':hh.expected_hit.sum(),'recall':hh.retained_hit.mean(),'expected_recall':hh.expected_hit.mean(),'precision':kept.y.mean(),'unknown':kept.y.isna().sum(),'zero_capacity_dates':cc.K.eq(0).sum()}
  for name,val in values.items():assert np.isclose(val,getattr(row,name),equal_nan=True),name
 # Exhaustively verify uniform K-of-N inclusion, including K=0/N.
 fixtures=0
 for n in range(1,8):
  for k in range(n+1):
   subsets=list(combinations(range(n),k))
   for i in range(n):assert np.isclose(sum(i in subset for subset in subsets)/len(subsets),k/n)
   fixtures+=1
 js(out/'independent_verification.json',dict(status='PASS',date_capacity_checks=checks,assignment_checks=len(z),event_window_checks=len(h),summary_groups=len(summary),enumerated_random_fixtures=fixtures,scope='Exact frozen-output diagnostic; not causal identification or strategy validation',adoption=False))
 print('VERIFIED',checks,len(z),len(h),fixtures)
if __name__=='__main__':run()

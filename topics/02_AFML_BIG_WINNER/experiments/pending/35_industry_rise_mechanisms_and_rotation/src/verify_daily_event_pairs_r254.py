"""Rebuild paired detection directly from alert dates, not stored R253 hit flags."""
from common import *
import pandas as pd
from collections import Counter

def run():
 out=ROOT/'outputs/r254';p=pd.read_parquet(out/'paired_events.parquet');a=pd.read_parquet(ROOT/'outputs/r253/alerts.parquet');summary=pd.read_csv(out/'summary.csv')
 dates={k:np.sort(g.day_i.to_numpy()) for k,g in a.groupby(['variant','strategy']+KEY+['block'])};checks=0;records=[]
 for e in p.itertuples():
  leads=[]
  for variant in [e.variant,'base']:
   seq=dates.get((variant,e.strategy,e.era,e.level,e.industry_code,e.block),np.array([],dtype=int))
   match=seq[(seq>=e.day_i-20)&(seq<e.day_i)]
   leads.append(int(e.day_i-match[0]) if e.evaluable and len(match) else None)
  found=[v is not None for v in leads]
  cell=('shared' if all(found) else 'new' if found[0] else 'lost' if found[1] else 'neither') if e.evaluable else 'left_censored'
  assert cell==e.cell and found==[e.hit,e.hit_base]
  delta=leads[0]-leads[1] if all(found) else None
  assert (e.paired_lead==delta) if delta is not None else pd.isna(e.paired_lead)
  records.append(dict(era=e.era,level=e.level,strategy=e.strategy,variant=e.variant,event_year=e.date.year,cell=cell,delta=delta));checks+=1
 rebuilt=pd.DataFrame(records)
 for row in summary.itertuples():
  g=rebuilt[rebuilt.era.eq(row.era)&rebuilt.level.eq(row.level)&rebuilt.strategy.eq(row.strategy)&rebuilt.variant.eq(row.variant)]
  if row.scope=='annual':g=g[g.event_year.eq(row.event_year)]
  c=Counter(g.cell)
  for name in ['shared','new','lost','neither']:assert c[name]==getattr(row,name)
  assert c['left_censored']==row.left_censored and len(g)-c['left_censored']==row.events
  d=g[g.cell.eq('shared')].delta
  assert (d>0).sum()==row.earlier and (d==0).sum()==row.same and (d<0).sum()==row.later
  for expected,actual in [(d.median(),row.median_paired_lead),(d.mean(),row.mean_paired_lead),((c['new']-c['lost'])/row.events if row.events else np.nan,row.recall_delta)]:assert np.isclose(expected,actual,equal_nan=True)
 js(out/'independent_verification.json',dict(status='PASS',direct_alert_pair_reconstructions=checks,summary_groups=len(summary),scope='Direct frozen-alert matching and descriptive summary; not significance or causal certification',adoption=False))
 print('VERIFIED',checks,len(summary))
if __name__=='__main__':run()

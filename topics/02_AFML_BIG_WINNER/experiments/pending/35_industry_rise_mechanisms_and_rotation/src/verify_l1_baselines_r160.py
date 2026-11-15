"""Independently verify all baseline selections, cooldown states and event hits."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r160';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 s=pd.read_parquet(out/'candidate_scores.parquet');original=pd.read_parquet(ROOT/'outputs/r159/evaluation/data/r09_daily_scores.parquet');pd.testing.assert_frame_equal(s[original.columns],original);a=pd.read_parquet(out/'alerts.parquet');hits=pd.read_parquet(out/'event_hits.parquet');summary=pd.read_csv(out/'summary.csv');calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);monthends=set()
 for month in calendar.to_period('M').unique():
  if month.end_time.normalize()<=calendar.max():monthends.add(calendar[calendar.to_period('M')==month].max())
 checked=0
 for _,g in s.groupby('date'):
  rr=g[['mom20','mom60','vol20','dd60']].rank(method='average');rr=(rr-.5)/len(g)-.5;assert np.allclose(g.F,((rr.mom20+rr.mom60)/2-rr.vol20+rr.dd60)/3);assert np.allclose(g.momentum,rr.mom60)
 for method in ['raw_logit','F','momentum']:
  selected=[]
  for _,g in s[s.eligible].groupby('date'):
   records=g.to_dict('records');order=sorted(records,key=lambda x:(-x[method],x['industry_code']));selected.extend((x['industry_code'],x['date'],x['day_i']) for x in order[:int(np.ceil(.2*len(records)))])
  selected.sort(key=lambda x:(x[1],x[0]));last={};cool=[]
  for code,date,day in selected:
   if code not in last or day-last[code]>20:cool.append((code,date));last[code]=day
  expect={'daily':{(x[0],x[1]) for x in selected},'monthly':{(x[0],x[1]) for x in selected if x[1] in monthends},'daily_cooldown20':set(cool)}
  for strategy,expected in expect.items():
   g=a[a.method.eq(method)&a.strategy.eq(strategy)];assert set(zip(g.industry_code,g.date))==expected;checked+=len(g)
 for row in hits.itertuples():
  q=a[a.method.eq(row.method)&a.strategy.eq(row.strategy)&a.industry_code.eq(row.industry_code)&a.block.eq(row.block)&a.day_i.ge(row.day_i-20)&a.day_i.lt(row.day_i)];hit=bool(row.evaluable and len(q));assert row.hit==hit
  if hit:assert row.lead==row.day_i-q.day_i.min()
  else:assert pd.isna(row.lead)
 for row in summary.itertuples():
  g=a[a.method.eq(row.method)&a.strategy.eq(row.strategy)];h=hits[hits.method.eq(row.method)&hits.strategy.eq(row.strategy)]
  if row.year:g=g[g.date.dt.year.eq(row.year)];h=h[h.date.dt.year.eq(row.year)]
  v=h[h.evaluable];assert row.known_successes==g.y.sum() and np.isclose(row.precision_lower,g.y.sum()/len(g)) and np.isclose(row.precision_upper,(g.y.sum()+g.y.isna().sum())/len(g));assert len(g)==row.alerts and int(g.y.notna().sum())==row.mature and int(g.y.isna().sum())==row.unknown;assert len(v)==row.events and int(v.hit.sum())==row.hit_events;assert np.isclose(g.y.mean(),row.precision) and np.isclose(v.hit.mean(),row.recall);assert np.isclose(v.loc[v.hit,'lead'].median(),row.median_lead,equal_nan=True)
 js(out/'verification.json',dict(status='PASS',candidate_rows=len(s),all_alert_selections_checked=checked,event_hits_checked=len(hits),summary_groups=len(summary),scope='independent ranks, all top lists, sequential cooldown, strict prior same-block hits, unknown outcomes and group metrics',verifier_sha256=sha(Path(__file__))))
 print('R160 VERIFIED',len(s),checked,len(hits))
if __name__=='__main__':run()

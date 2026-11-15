from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r258';a=pd.read_parquet(out/'alerts.parquet');h=pd.read_parquet(out/'event_hits.parquet');p=pd.read_parquet(ROOT/'outputs/r256/predictions.parquet');scores=pd.read_parquet(ROOT/'outputs/r253/scores.parquet');p=p.merge(scores[KEY+['date','variant','day_i']],on=KEY+['date','variant'],validate='one_to_one');folds=json.loads((ROOT/'outputs/r256/folds.json').read_text());lookup={(f['era'],f['level'],f['year'],f['variant']):f for f in folds};calendar=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index;ends={}
 for day in calendar:
  if day.to_period('M').end_time.normalize()<=calendar.max():ends[day.to_period('M')]=day
 ak=KEY+['date'];n=0
 for variant in ['base','state','interaction']:
  for version in ['monthly','daily']:
   chosen=[]
   for (era,level,date),g in p[p.variant.eq(variant)].groupby(['era','level','date']):
    f=lookup[(era,level,date.year,variant)];slope=f['coefficient'] if version=='daily' else f['base_model']['calibration_coefficient'][0][0]
    # Positive/negative affine sigmoid preserves/reverses linear order exactly.
    ordered=sorted(g.itertuples(),key=lambda r:(-np.sign(slope)*r.linear,r.industry_code));chosen.extend(ordered[:int(np.ceil(.2*len(g)))])
   full={(r.era,r.level,r.industry_code,r.date) for r in chosen};month={key for key in full if key[3] in ends.values()};kept=set();last={}
   for r in sorted(chosen,key=lambda r:(r.date,r.industry_code)):
    k=(r.era,r.level,r.industry_code)
    if k not in last or r.day_i-last[k]>20:kept.add(k+(r.date,));last[k]=r.day_i
   for strategy,expected in [('daily',full),('monthly',month),('daily_cooldown20',kept)]:
    got=a[a.variant.eq(variant)&a.version.eq(version)&a.strategy.eq(strategy)];assert expected==set(map(tuple,got[ak].to_numpy()));n+=len(got)
 dates={k:np.sort(g.day_i.to_numpy()) for k,g in a.groupby(['variant','version','strategy']+KEY+['block'])}
 for row in h.itertuples():
  seq=dates.get((row.variant,row.version,row.strategy,row.era,row.level,row.industry_code,row.block),np.array([],dtype=int));lo=seq.searchsorted(row.day_i-20);hi=seq.searchsorted(row.day_i);hit=bool(row.evaluable) and hi>lo;assert hit==row.hit
  assert row.lead_sessions==row.day_i-seq[lo] if hit else pd.isna(row.lead_sessions)
 summary=pd.read_csv(out/'summary.csv')
 for row in summary.itertuples():
  mask=lambda f:f.era.eq(row.era)&f.level.eq(row.level)&f.variant.eq(row.variant)&f.version.eq(row.version)&f.strategy.eq(row.strategy)
  aa=a[mask(a)];hh=h[mask(h)]
  if row.scope=='annual':aa=aa[aa.date.dt.year.eq(row.year)];hh=hh[hh.date.dt.year.eq(row.year)]
  vv=hh[hh.evaluable];assert len(aa)==row.alerts and len(vv)==row.events and vv.hit.sum()==row.hit_events
  assert np.isclose(aa.y.mean(),row.precision,equal_nan=True) and np.isclose(vv.hit.mean(),row.recall,equal_nan=True)
  assert aa.y.isna().sum()==row.unknown
 js(out/'independent_verification.json',dict(status='PASS',alert_selection_checks=n,event_matches=len(h),summary_groups=len(summary),scope='Independent linear-slope order, cooldown, date interval hits and summary; not predictive certification',adoption=False));print('VERIFIED',n,len(h),len(summary))
if __name__=='__main__':run()

import pandas as pd
from common import *
from monitor_extensions_r63 import attach

def run():
 out=ROOT/'outputs/r63';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 for p,h in rec['outputs'].items():assert sha(out/p)==h
 d=pd.read_parquet(out/'evidence_matrix.parquet');base=pd.read_csv(ROOT/'outputs/r25/monitor/evidence_matrix.csv');pd.testing.assert_frame_equal(d[base.columns].fillna(np.nan),base.fillna(np.nan))
 assert len(d)==3066 and not d.duplicated(KEY+['asof','clock']).any()
 f=pd.read_parquet(ROOT/'data/r45_financing_intensity.parquet');b=json.loads((ROOT/'outputs/r60/frozen_monthly_series.json').read_text())
 checks=0
 for x in d.drop_duplicates(KEY+['asof']).to_dict('records'):
  date=pd.Timestamp(x['asof']);subset=f[f.date.le(date)]
  for k in KEY:subset=subset[subset[k].eq(x[k])]
  if len(subset):
   latest=subset.loc[subset.date.idxmax()];assert pd.Timestamp(x['financing_date'])==latest.date
   assert x['financing_status']=='older_snapshot_not_current' and pd.isna(x['financing_current_value'])
   assert (pd.isna(latest.financing_intensity) and pd.isna(x['financing_last_value'])) or x['financing_last_value']==latest.financing_intensity
  else:assert x['financing_status']=='missing_snapshot'
  if x['battery_month'] is not None:
   eligible=[y for y in b if pd.Timestamp(y['available_at'])<=date];y=max(eligible,key=lambda y:y['month']);assert x['battery_month']==y['month'] and x['battery_gwh']==y['value_gwh']
  checks+=1
 # Adversarial source order / future and missing latest growth: no stale backfill.
 sample=base[(base.level=='L2')&(base.industry_code=='801737.SI')].head(1).copy();sample['asof']='2026-09-30'
 fake=pd.DataFrame([dict(month='2026-07',available_at='2026-08-10',growth_available_at='2026-08-10',log_yoy=.2,value_gwh=1,raw_sha256='a'),dict(month='2026-08',available_at='2026-09-10',growth_available_at=None,log_yoy=None,value_gwh=2,raw_sha256='b'),dict(month='2026-09',available_at='2026-10-10',growth_available_at='2026-10-10',log_yoy=.3,value_gwh=3,raw_sha256='c')])
 test=attach(sample,fake,f).iloc[0];assert test.battery_month=='2026-08' and pd.isna(test.battery_log_yoy) and test.battery_status=='latest_observation_yoy_unknown'
 delta=pd.read_parquet(out/'changes.parquet');assert len(delta)==1533 and not delta.financing_source_advanced.any()
 expected=[]
 for x in d.to_dict('records'):
  if x['battery_month'] is None:continue
  y=next(z for z in b if z['month']==x['battery_month'])
  assert pd.Timestamp(y['growth_available_at'])<=pd.Timestamp(x['asof'])
  assert abs(x['battery_log_yoy']-y['log_yoy'])<1e-12
  expected.append(x)
 assert len(expected)==12 and delta.battery_yoy_change.notna().sum()==6
 old=pd.read_parquet(ROOT/'outputs/r50/evidence_matrix.parquet')
 # Full version comparison: only the previously missing September growth/status changes.
 unchanged=[c for c in old.columns if c not in ['battery_log_yoy','battery_status']]
 pd.testing.assert_frame_equal(old[unchanged],d[unchanged])
 changes=[]
 for a,z in zip(old.to_dict('records'),d.to_dict('records')):
  if a['battery_status']!=z['battery_status']:
   assert a['battery_status']=='latest_observation_yoy_unknown'
   assert z['battery_status']=='historical_proxy_yoy_available'
   assert z['asof']=='2026-10-21' and pd.isna(a['battery_log_yoy'])
   changes.append({k:z[k] for k in KEY+['clock','asof','battery_month','battery_log_yoy']})
 assert len(changes)==6
 js(out/'source_changes.json',changes)
 assert not {'excess20','excess60','return20','return60'} & set(d.columns)
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());assert current['selected']['complete_battery_historical_monitor']['sha256']==sha(out/'evidence_matrix.parquet')
 js(out/'verification.json',dict(status='PASS',unchanged_base_rows=len(base),direct_identity_date_checks=checks,adversarial_future_and_missing_growth=True,no_prediction_promotion=True))
 print('R63 VERIFIED',checks,'industry/date joins and unchanged base')
if __name__=='__main__':run()

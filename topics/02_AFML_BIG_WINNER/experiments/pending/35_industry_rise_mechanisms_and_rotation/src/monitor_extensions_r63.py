"""Frozen historical observations, kept separate from predictive claims."""
import pandas as pd
from common import *

SCOPE={('SW2021','L2','801737.SI'),('SW2021','L3','857371.SI')}
def attach(base, battery, financing):
 b=battery.copy();b['available_at']=pd.to_datetime(b.available_at);b['growth_available_at']=pd.to_datetime(b.growth_available_at)
 f=financing.copy();f['date']=pd.to_datetime(f.date)
 records=[]
 for row in base.to_dict('records'):
  key=tuple(row[k] for k in KEY);date=pd.Timestamp(row['asof'])
  rec=dict(battery_status='outside_registered_scope',battery_month=None,battery_available_at=None,battery_gwh=None,battery_log_yoy=None,battery_raw_sha256=None,battery_age_days=None,
   financing_status='missing_snapshot',financing_date=None,financing_snapshot_date=None,financing_age_days=None,financing_last_value=None,financing_current_value=None,financing_coverage=None,financing_ready=None)
  if key in SCOPE:
   eligible=b[b.available_at.le(date)].sort_values('month')
   rec['battery_status']='no_available_observation'
   if len(eligible):
    x=eligible.iloc[-1];known=pd.notna(x.log_yoy) and pd.notna(x.growth_available_at) and x.growth_available_at<=date
    rec.update(battery_status='historical_proxy_yoy_available' if known else 'latest_observation_yoy_unknown',battery_month=x.month,battery_available_at=x.available_at,battery_gwh=x.value_gwh,battery_log_yoy=x.log_yoy if known else np.nan,battery_raw_sha256=x.raw_sha256,battery_age_days=(date-x.available_at).days)
  g=f[f.date.le(date)]
  for k,v in zip(KEY,key):g=g[g[k].eq(v)]
  if len(g):
   x=g.sort_values('date').iloc[-1];current=x.date==date;ready=bool(x.ready)
   rec.update(financing_status=('historical_proxy_available' if ready else 'insufficient_coverage') if current else 'older_snapshot_not_current',financing_date=x.date,financing_snapshot_date=x.snapshot_date,financing_age_days=(date-x.date).days,financing_last_value=x.financing_intensity,financing_current_value=x.financing_intensity if current and ready else np.nan,financing_coverage=x.coverage,financing_ready=ready)
  rec.update(extension_scope='historical_proxy_not_acquisition_gated',extension_prediction_status='no_stable_primary_increment_established',extension_next_update='manual_after_new_local_source_version')
  records.append(rec)
 return pd.concat([base.reset_index(drop=True),pd.DataFrame(records)],axis=1)

def run():
 out=ROOT/'outputs/r63';out.mkdir(exist_ok=True)
 paths=[ROOT/'outputs/r25/monitor/evidence_matrix.csv',ROOT/'outputs/r60/frozen_monthly_series.json',ROOT/'data/r45_financing_intensity.parquet',ROOT/'protocols/r63.json',Path(__file__)]
 base=pd.read_csv(paths[0]);b=pd.DataFrame(json.loads(paths[1].read_text()));f=pd.read_parquet(paths[2]);d=attach(base,b,f);d.to_parquet(out/'evidence_matrix.parquet',index=False)
 counts=d.groupby(['asof','level','battery_status','financing_status'],dropna=False).size().reset_index(name='rows');js(out/'coverage.json',counts.to_dict('records'))
 dates=sorted(d['asof'].unique());cols=KEY+['clock','asof','battery_month','battery_log_yoy','financing_date','financing_last_value','financing_status']
 delta=d[d['asof'].eq(dates[0])][cols].merge(d[d['asof'].eq(dates[1])][cols],on=KEY+['clock'],suffixes=('_old','_new'),validate='one_to_one')
 delta['financing_source_advanced']=delta.financing_date_new.gt(delta.financing_date_old);delta['battery_yoy_change']=delta.battery_log_yoy_new-delta.battery_log_yoy_old;delta['interpretation']='historical_observation_change_not_stage_or_forecast';delta.to_parquet(out/'changes.parquet',index=False)
 js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},rows=len(d),changes=len(delta),outputs={p.name:sha(p) for p in [out/'evidence_matrix.parquet',out/'changes.parquet',out/'coverage.json']},status='historical_only_no_rank_change'))
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());current['selected']['complete_battery_historical_monitor']=dict(path='outputs/r63/evidence_matrix.parquet',sha256=sha(out/'evidence_matrix.parquet'));js(ROOT/'outputs/current_sources.json',current)
 print(counts.to_string(index=False))
if __name__=='__main__':run()

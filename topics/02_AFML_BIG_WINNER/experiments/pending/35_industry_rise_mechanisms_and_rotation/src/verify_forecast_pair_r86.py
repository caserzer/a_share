import statistics
from collections import Counter
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r86';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 f=pd.read_parquet(ROOT/'data/r24_source_exclusion_overlay.parquet');values={(x.infoCode,x.fiscal_year):x.value for x in f.itertuples() if x.basis=='profit_cny'};reports=pd.read_parquet(ROOT/'outputs/r85/report_roster.parquet');roster={}
 for x in reports.itertuples():roster.setdefault((x.stock_code,x.broker),[]).append((x.publication_proxy_date,x.infoCode))
 old={(x['stock_code'],x['fiscal_year'],x['broker']):x for x in json.loads((ROOT/'outputs/r85/broker_snapshots.json').read_text())};rows=json.loads((out/'broker_pairs.json').read_text());seen=set();group={}
 for x in rows:
  key=(x['stock_code'],x['fiscal_year'],x['broker']);assert key in old and key not in seen;seen.add(key);end=old[key];assert x['december_status']==end['status'] and x['december_forecast']==end['forecast_profit_cny']
  cutoff=pd.Timestamp(key[1],6,30);q=[v for v in roster.get((key[0],key[2]),[]) if v[0]<cutoff];status='no_report_before_cutoff';value=None;ids=[]
  if q:
   last=max(v[0] for v in q);age=(cutoff-last).days;ids=sorted(v[1] for v in q if v[0]==last);vv=[values.get((i,key[1]),np.nan) for i in ids]
   status='stale' if age>180 else 'latest_report_unknown' if any(not np.isfinite(v) for v in vv) else 'same_day_conflict' if len(set(vv))!=1 else 'valid'
   if status=='valid':value=float(vv[0])
   assert pd.Timestamp(x['june_latest_publication'])==last and x['june_age_days']==age
  assert x['june_status']==status and x['june_forecast']==value and x['june_latest_report_ids']==ids and x['paired']==(status=='valid' and end['status']=='valid')
  group.setdefault(key[:2],[]).append(x)
 assert seen==set(old)
 actual={(x['stock_code'],x['fiscal_year']):x for x in json.loads((ROOT/'outputs/r84/annual_actual_candidates.json').read_text())};companies=json.loads((out/'company_pairs.json').read_text());assert len(companies)==len(actual)
 for x in companies:
  key=(x['stock_code'],x['fiscal_year']);g=group.get(key,[]);paired=[v for v in g if v['paired']];assert x['paired_brokers']==len(paired) and x['paired_broker_ids']==sorted(v['broker'] for v in paired)
  assert x['brokers']==len(g) and x['june_valid']==sum(v['june_status']=='valid' for v in g) and x['december_valid']==sum(v['december_status']=='valid' for v in g)
  real=actual[key]['actual_profit_cny'];assert x['actual_profit_cny']==real
  errors=[];predictions=[]
  for prefix in ['june','december']:
   prediction=statistics.median(v[prefix+'_forecast'] for v in paired) if paired else None;predictions.append(prediction);assert x[prefix+'_forecast']==prediction
   error=(prediction-real)/(abs(prediction)+abs(real)) if prediction is not None and abs(prediction)+abs(real)>0 else None;errors.append(error)
   assert x[prefix+'_error'] is None if error is None else np.isclose(x[prefix+'_error'],error)
  change=abs(errors[1])-abs(errors[0]) if None not in errors else None;assert x['absolute_error_change'] is None if change is None else np.isclose(x['absolute_error_change'],change)
  direction=None if predictions[0] is None else 'up' if predictions[1]>predictions[0] else 'down' if predictions[1]<predictions[0] else 'unchanged';assert x['revision_direction']==direction
 for s in json.loads((out/'summary.json').read_text()):
  q=[x for x in companies if x['fiscal_year']==s['fiscal_year'] and x['absolute_error_change'] is not None and (s['stratum']=='all' or x['revision_direction']==s['stratum'])];assert len(q)==s['company_years']
  for k,field,absolute in [('june_mean_absolute_error','june_error',True),('december_mean_absolute_error','december_error',True),('mean_absolute_error_change','absolute_error_change',False)]:
   v=statistics.mean(abs(x[field]) if absolute else x[field] for x in q) if q else None;assert s[k] is None if v is None else np.isclose(s[k],v)
  assert s['improved']==sum(x['absolute_error_change']<-1e-12 for x in q) and s['worsened']==sum(x['absolute_error_change']>1e-12 for x in q) and s['unchanged_error']==sum(abs(x['absolute_error_change'])<=1e-12 for x in q)
 matrix={(x['june_status'],x['december_status']):x['rows'] for x in json.loads((out/'coverage_matrix.json').read_text())};assert matrix==dict(Counter((x['june_status'],x['december_status']) for x in rows))
 c=json.loads((out/'coverage.json').read_text());assert c==dict(broker_rows=len(rows),paired_brokers=sum(x['paired'] for x in rows),company_years=len(companies),paired_company_years=sum(x['paired_brokers']>0 for x in companies),evaluable_company_years=sum(x['absolute_error_change'] is not None for x in companies),june_known_lost_by_december=sum(x['june_status']=='valid' and x['december_status']!='valid' for x in rows),december_known_without_june=sum(x['june_status']!='valid' and x['december_status']=='valid' for x in rows))
 js(out/'verification.json',dict(status='PASS',broker_rows=len(rows),company_years=len(companies),scope='all June selections, frozen December selections, paired-company medians, errors, 24 summaries and coverage transitions',receipt_sha256=sha(out/'receipt.json'),verifier_sha256=sha(Path(__file__))))
 print('R86 VERIFIED',len(rows),len(companies))
if __name__=='__main__':run()

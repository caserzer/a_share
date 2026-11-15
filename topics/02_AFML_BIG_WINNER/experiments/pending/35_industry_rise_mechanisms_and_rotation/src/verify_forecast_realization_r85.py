import statistics,math
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r85';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 xp=next(Path(p) for p in rec['reads'] if p.endswith('/validated_extractions.parquet'));mp=next(Path(p) for p in rec['reads'] if p.endswith('/selected_reports.parquet'))
 extraction=pd.read_parquet(xp);meta=pd.read_parquet(mp).set_index('infoCode');bybroker={};expected_reports=[]
 for x in extraction.itertuples():
  broker=meta.loc[x.infoCode,'orgCode'];dates=[pd.to_datetime(x.publishDate),pd.to_datetime(x.available_date)];date=max(d for d in dates if pd.notna(d));expected_reports.append(dict(infoCode=x.infoCode,stock_code=x.stockCode,broker=broker,publication_proxy_date=date))
  if pd.notna(broker):bybroker.setdefault((x.stockCode,broker),[]).append((date,x.infoCode))
 pd.testing.assert_frame_equal(pd.DataFrame(expected_reports),pd.read_parquet(out/'report_roster.parquet'))
 f=pd.read_parquet(ROOT/'data/r24_source_exclusion_overlay.parquet');forecasts={(x.infoCode,x.fiscal_year):x.value for x in f.itertuples() if x.basis=='profit_cny'}
 prior=pd.read_parquet(ROOT/'outputs/r84/forecast_join.parquet');keys=set(prior.dropna(subset=['broker'])[['stock_code','fiscal_year','broker']].itertuples(index=False,name=None));brokers=json.loads((out/'broker_snapshots.json').read_text());seen=set();groups={}
 for x in brokers:
  key=(x['stock_code'],x['fiscal_year'],x['broker']);assert key in keys and key not in seen;seen.add(key);cutoff=pd.Timestamp(key[1],12,31);eligible=[v for v in bybroker.get((key[0],key[2]),[]) if v[0]<cutoff];status='no_report_before_cutoff';prediction=None;ids=[]
  if eligible:
   last=max(v[0] for v in eligible);ids=sorted(v[1] for v in eligible if v[0]==last);age=(cutoff-last).days;vv=[forecasts.get((i,key[1]),np.nan) for i in ids]
   status='stale' if age>180 else 'latest_report_unknown' if any(not np.isfinite(v) for v in vv) else 'same_day_conflict' if len(set(vv))!=1 else 'valid'
   if status=='valid':prediction=float(vv[0])
   assert pd.Timestamp(x['latest_publication'])==last and x['age_days']==age
  assert x['status']==status and x['forecast_profit_cny']==prediction and x['latest_report_ids']==ids
  groups.setdefault(key[:2],[]).append(x)
 assert seen==keys
 actual={(x['stock_code'],x['fiscal_year']):x for x in json.loads((ROOT/'outputs/r84/annual_actual_candidates.json').read_text())};companies=json.loads((out/'company_years.json').read_text());assert len(companies)==len(actual)
 for x in companies:
  key=(x['stock_code'],x['fiscal_year']);g=groups.get(key,[]);good=[v['forecast_profit_cny'] for v in g if v['status']=='valid'];prediction=statistics.median(good) if good else None;real=actual[key]['actual_profit_cny'];error=(prediction-real)/(abs(prediction)+abs(real)) if prediction is not None and abs(prediction)+abs(real)>0 else None
  assert x['forecast_profit_cny']==prediction and x['actual_profit_cny']==real and x['brokers']==len(g) and x['known_brokers']==len(good)
  assert x['all_brokers_known']==(len(g)>0 and len(g)==len(good)) and x['actual_updated_after_notice']==actual[key]['update_after_notice']
  if error is None:assert x['error'] is None
  else:
   assert np.isclose(x['error'],error) and np.isclose(x['absolute_error'],abs(error)) and -1<=error<=1
   assert x['overestimated']==(prediction>real) and x['sign_mismatch']==(np.sign(prediction)!=np.sign(real))
 for s in json.loads((out/'summary.json').read_text()):
  q=[x for x in companies if x['fiscal_year']==s['fiscal_year']];label=s['stratum']
  if label=='all_brokers_known':q=[x for x in q if x['all_brokers_known']]
  if label=='partial_brokers':q=[x for x in q if not x['all_brokers_known']]
  if label=='actual_updated':q=[x for x in q if x['actual_updated_after_notice']]
  if label=='actual_not_later_updated':q=[x for x in q if not x['actual_updated_after_notice']]
  valid=[x for x in q if x['error'] is not None];assert s['company_years']==len(q) and s['evaluable']==len(valid)
  funcs={'mean_symmetric_error':lambda:statistics.mean(x['error'] for x in valid),'median_symmetric_error':lambda:statistics.median(x['error'] for x in valid),'mean_absolute_symmetric_error':lambda:statistics.mean(x['absolute_error'] for x in valid),'overestimated_share':lambda:sum(x['overestimated'] for x in valid)/len(valid),'sign_mismatch_share':lambda:sum(x['sign_mismatch'] for x in valid)/len(valid)}
  for k,fn in funcs.items():assert s[k] is None if not valid else np.isclose(s[k],fn())
 coverage=json.loads((out/'coverage.json').read_text())
 from collections import Counter
 assert coverage['broker_snapshots']==len(brokers) and coverage['broker_status_counts']==dict(Counter(x['status'] for x in brokers))
 assert coverage['company_years']==len(companies) and coverage['evaluable']==sum(x['error'] is not None for x in companies)
 assert coverage['all_brokers_known']==sum(x['all_brokers_known'] for x in companies) and coverage['no_known_brokers']==sum(x['known_brokers']==0 for x in companies)
 js(out/'verification.json',dict(status='PASS',broker_snapshots=len(brokers),company_years=len(companies),scope='full source roster, all latest-report selections, all company aggregation and 30 summaries independently recomputed',verifier_sha256=sha(Path(__file__)),receipt_sha256=sha(out/'receipt.json')))
 print('R85 VERIFIED',len(brokers),len(companies))
if __name__=='__main__':run()

"""Version-aware local coverage for two unused accounting mechanism proxies."""
import pandas as pd
from common import *
FIELDS={'cashflow_vip':'c_pay_acq_const_fiolta','fina_indicator_vip':'invturn_days'}
def run():
 out=ROOT/'outputs/r67';out.mkdir(exist_ok=True);source=ROOT/'data/financial_archive_all_market.parquet';raw=pd.read_parquet(source);protocol=json.loads((ROOT/'protocols/r67.json').read_text());date=pd.Timestamp(protocol['asof']);facts=[];coverage=[]
 for api,field in FIELDS.items():
  allrows=raw[raw.api.eq(api)].copy();allrows['numeric_value']=pd.to_numeric(allrows[field],errors='coerce')
  g=allrows[allrows.timing_valid & allrows.proxy_available_date.le(date)]
  for (issuer,period),part in g.groupby(['ts_code','end_date']):
   latest=part.proxy_available_date.max();s=part[part.proxy_available_date.eq(latest)];distinct=s.numeric_value.nunique(dropna=False);conflict=distinct>1;v=float(s.numeric_value.iloc[0]) if not conflict and pd.notna(s.numeric_value.iloc[0]) else None
   status='conflicting_latest_values' if conflict else 'missing_value' if v is None else 'invalid_sign' if (v<0 if api=='cashflow_vip' else v<=0) else 'numeric_available'
   facts.append(dict(ts_code=issuer,end_date=period,api=api,field=field,proxy_available_date=latest,value=v,status=status,report_types=sorted(s.report_type.dropna().astype(str).unique()),source_refs=s[['query_id','source_row','source_page_sha256']].to_dict('records'),archive_available_at=s.archived_available_at.max(),strict_pit=False))
  coverage.append(dict(api=api,field=field,raw_rows=len(allrows),cutoff_rows=len(g),issuers=g.ts_code.nunique(),periods=sorted(str(x.date()) for x in g.end_date.unique()),archive_only_after_cutoff=int((allrows.archived_available_at>date.tz_localize('Asia/Shanghai')).sum())))
 js(out/'selected_facts.json',facts);pairs=[]
 lookup={(x['api'],x['ts_code'],pd.Timestamp(x['end_date'])):x for x in facts}
 for x in facts:
  period=pd.Timestamp(x['end_date'])
  if period.year!=2026:continue
  prior=lookup.get((x['api'],x['ts_code'],period-pd.DateOffset(years=1)))
  usable=x['status']=='numeric_available' and prior is not None and prior['status']=='numeric_available'
  pairs.append(dict(ts_code=x['ts_code'],field=x['field'],end_date=period,current_value=x['value'],prior_value=prior['value'] if prior else None,current_status=x['status'],prior_status=prior['status'] if prior else 'missing_period',eligible=usable,available_at=max(x['proxy_available_date'],prior['proxy_available_date']) if prior else None))
 js(out/'same_period_pairs.json',pairs);js(out/'coverage.json',coverage)
 summary=[]
 for field in FIELDS.values():
  for period in sorted({str(pd.Timestamp(x['end_date']).date()) for x in pairs}):
   q=[x for x in pairs if x['field']==field and str(pd.Timestamp(x['end_date']).date())==period]
   summary.append(dict(field=field,period=period,pairs=len(q),eligible=sum(x['eligible'] for x in q),current_conflicts=sum(x['current_status']=='conflicting_latest_values' for x in q),prior_conflicts=sum(x['prior_status']=='conflicting_latest_values' for x in q)))
 js(out/'summary.json',summary);js(out/'receipt.json',dict(reads={str(p):sha(p) for p in [source,ROOT/'protocols/r67.json',ROOT/'outputs/r03/archive_receipt.json',Path(__file__)]},selected_facts=len(facts),pairs=len(pairs),no_outcomes_read=True,strict_pit=False))
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':run()

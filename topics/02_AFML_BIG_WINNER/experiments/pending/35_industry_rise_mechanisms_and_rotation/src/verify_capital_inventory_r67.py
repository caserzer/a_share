"""Check selected values against archived response bytes and independent grouping."""
import zipfile
import pandas as pd
from common import *
from supplement_financials import SOURCE

def run():
 out=ROOT/'outputs/r67';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 rs=json.loads((SOURCE/'query_receipts.json').read_text());lookup={}
 with zipfile.ZipFile(SOURCE/'inputs/provider_responses.zip') as z:
  for r in rs:
   if r['api'] not in ['cashflow_vip','fina_indicator_vip']:continue
   payload=z.read(r['archived_response']);assert hashlib.sha256(payload).hexdigest()==r['raw_sha256'];obj=json.loads(payload)
   for i,row in enumerate(obj['data']['items']):lookup[(r['query_id'],i)]=dict(zip(obj['data']['fields'],row))
 raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');cut=pd.Timestamp(json.loads((ROOT/'protocols/r67.json').read_text())['asof']);group={}
 for x in raw.to_dict('records'):
  if x['api'] not in ['cashflow_vip','fina_indicator_vip'] or not x['timing_valid'] or pd.isna(x['proxy_available_date']) or x['proxy_available_date']>cut:continue
  group.setdefault((x['api'],x['ts_code'],str(x['end_date'].date())),[]).append(x)
 facts=json.loads((out/'selected_facts.json').read_text());assert len(facts)==len(group);checked=0
 for x in facts:
  q=group[(x['api'],x['ts_code'],str(pd.Timestamp(x['end_date']).date()))];latest=max(y['proxy_available_date'] for y in q);q=[y for y in q if y['proxy_available_date']==latest]
  assert latest==pd.Timestamp(x['proxy_available_date'])
  assert {(y['query_id'],y['source_row']) for y in q}=={(y['query_id'],y['source_row']) for y in x['source_refs']}
  values=[]
  for y in q:
   z=lookup[(y['query_id'],y['source_row'])];assert z['ts_code']==x['ts_code'];v=z.get(x['field']);values.append(None if v is None else float(v));checked+=1
  distinct=set(values);v=values[0] if len(distinct)==1 else None
  assert x['value']==v
  status='conflicting_latest_values' if len(distinct)>1 else 'missing_value' if v is None else 'invalid_sign' if (v<0 if x['api']=='cashflow_vip' else v<=0) else 'numeric_available'
  assert status==x['status']
 by={(x['field'],x['ts_code'],pd.Timestamp(x['end_date'])):x for x in facts};pairs=json.loads((out/'same_period_pairs.json').read_text())
 for x in pairs:
  key=(x['field'],x['ts_code']);d=pd.Timestamp(x['end_date']);a=by[(*key,d)];b=by.get((*key,d-pd.DateOffset(years=1)))
  assert x['eligible']==bool(a['status']=='numeric_available' and b and b['status']=='numeric_available')
  assert x['current_value']==a['value'] and x['prior_value']==(b['value'] if b else None)
 js(out/'verification.json',dict(status='PASS',selected_facts=len(facts),raw_source_rows_checked=checked,pairs_checked=len(pairs),first_release_certified=False,no_predictive_conclusion=True))
 print('R67 VERIFIED',len(facts),'facts',len(pairs),'pairs')
if __name__=='__main__':run()

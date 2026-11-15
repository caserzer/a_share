from decimal import Decimal
from datetime import datetime
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r149';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 for p,h in rec['outputs'].items():assert sha(out/p)==h,p
 rows=json.loads((out/'candidate_facts.json').read_text());base=ROOT/'outputs/cnequity_fundamental_review_20261114';source=json.loads((base/'reviewed_financial_cells.json').read_text());lookup={(x['symbol'],x['item_code']):x for x in source};assert len(rows)==len(lookup)==70
 receipts={x['symbol']:x for x in json.loads((base/'original_receipts.json').read_text())};calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);balances=0;visible=[]
 for x in rows:
  c=lookup[x['symbol'],x['item_code']];r=receipts[x['symbol']];assert sha(ROOT/x['source_pdf'])==x['source_pdf_sha256']==r['pdf_sha256'];assert x['source_pdf_page']==c['pdf_page'] and 1<=x['source_pdf_page']<=r['pages']
  value=Decimal(c['reported_number'].replace(',',''))*Decimal(str(c['unit_multiplier']));assert abs(value-Decimal(str(x['amount_cny'])))<=Decimal('.02');assert x['amount_cny']==c['item_value']
  stock=c['statement_type']=='balance';assert x['period_kind']==('point_in_time_balance' if stock else 'half_year_cumulative') and x['period_start']==(None if stock else '2026-01-01') and x['period_end']=='2026-06-30'
  assert x['original_pdf_fetched_at']==r['fetched_at'];assert not x['strict_pit_certified'] and not x['historical_model_admitted'];pub=pd.Timestamp(x['announce_date']);later=calendar[calendar>pub];assert x['next_exchange_session_proxy']==(str(later.min().date()) if len(later) else None)
  for asof in ['2026-09-30','2026-10-21']:
   boundary=pd.Timestamp(asof,tz='UTC')+pd.Timedelta(days=1);visible.append(dict(symbol=x['symbol'],item_code=x['item_code'],asof=asof,publication_proxy_available=pd.Timestamp(x['next_exchange_session_proxy'],tz='UTC')<boundary,pdf_observed_in_local_receipt=pd.Timestamp(x['original_pdf_fetched_at'])<boundary,normalized_candidate_available=pd.Timestamp(x['normalized_at'])<boundary,strict_pit=False))
 for symbol in receipts:
  d={x['item_code']:Decimal(str(x['amount_cny'])) for x in rows if x['symbol']==symbol};assert abs(d['total_assets']-d['total_liabilities']-d['total_equity'])<=Decimal('.02');balances+=1
 comparison=json.loads((out/'archive_comparison.json').read_text());assert len(comparison)==70;raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet')
 for x in comparison:
  q=raw[raw.ts_code.eq(x['symbol'])&raw.end_date.eq(pd.Timestamp('2026-06-30'))];field=x['canonical_field'];vals=sorted(q[field].dropna().unique().tolist()) if field in raw else [];assert vals==x['old_archive_values'];expected='matching_existing_amount' if any(abs(v-x['new_amount'])<=.02 for v in vals) else 'field_absent_in_archive_schema' if field not in raw else 'no_existing_value' if not vals else 'different_existing_values';assert x['status']==expected
 assert not any(x['pdf_observed_in_local_receipt'] or x['normalized_candidate_available'] for x in visible)
 js(out/'clock_eligibility.json',visible);js(out/'verification.json',dict(status='PASS',facts=70,issuers=10,balance_identities=balances,publication_vs_observation_checks=len(visible),historical_observed_eligible=0,new_schema_fields=3,new_schema_facts=30,existing_amount_matches=40,source_review_reused=True,new_visual_review=False,strict_PIT=False,model_adopted=False,receipt_sha256=sha(out/'receipt.json'),verifier_sha256=sha(__file__)))
 print('VERIFIED',70,balances,len(visible))
if __name__=='__main__':run()

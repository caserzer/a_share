from common import *
import pandas as pd
import zipfile
from decimal import Decimal

def run():
 out=ROOT/'outputs/r249';source=Path('/home/xiaolv/code/golden_loop_artifacts/a_share_market_radar/reports/fixed_industry_pool/20261010-data-v1');raw=pd.read_parquet(out/'raw_case_rows.parquet');receipts={x['query_id']:x for x in json.loads((source/'query_receipts.json').read_text())};calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);parsed=[];count=0
 with zipfile.ZipFile(source/'inputs/provider_responses.zip') as z:
  for query,g in raw.groupby('query_id'):
   rec=receipts[query];payload=z.read(rec['archived_response']);assert hashlib.sha256(payload).hexdigest()==rec['raw_sha256'];obj=json.loads(payload,parse_float=Decimal);fields=obj['data']['fields']
   for r in g.to_dict('records'):
    x=dict(zip(fields,obj['data']['items'][r['source_row']]));assert x['ts_code']==r['ts_code'] and pd.Timestamp(x['end_date'])==r['end_date'];v=Decimal(str(x['c_pay_acq_const_fiolta']));assert v==Decimal(str(r['c_pay_acq_const_fiolta']));dates=[pd.to_datetime(x.get(k),format='%Y%m%d',errors='coerce') for k in ['ann_date','f_ann_date']];dates=[a for a in dates if pd.notna(a)];effective=max(dates) if dates else pd.NaT;valid=pd.notna(effective) and effective>=r['end_date'];proxy=calendar[calendar.searchsorted(effective,side='right')] if valid and calendar.searchsorted(effective,side='right')<len(calendar) else pd.NaT
    assert bool(r['timing_valid'])==bool(valid);assert pd.isna(proxy) and pd.isna(r['proxy_available_date']) or proxy==r['proxy_available_date'];assert pd.Timestamp(rec['retrieved_at'])==r['archived_available_at'];parsed.append(dict(ts_code=x['ts_code'],period=str(r['end_date'].date()),value=v,proxy=proxy,valid=valid));count+=1
 selected=pd.read_parquet(ROOT/'outputs/r247/quarter_fields.parquet');selected=selected[selected['asof'].eq('2026-09-30')&selected.q2_status.eq('nonmonotone_capex_cumulative')];assert set(raw.ts_code)==set(selected.ts_code) and len(selected)==154
 lineage=json.loads((out/'period_lineage.json').read_text());assert len(lineage)==616;cut=pd.Timestamp('2026-09-30');values={}
 for r in lineage:
  eligible=[x for x in parsed if x['ts_code']==r['ts_code'] and x['period']==r['period'] and x['valid'] and x['proxy']<=cut];last=max(x['proxy'] for x in eligible);latest=[x for x in eligible if x['proxy']==last];unique={x['value'] for x in latest};assert len(unique)==1;v=next(iter(unique));assert v==Decimal(r['selected_value']) and last==pd.Timestamp(r['selected_proxy_date']);assert len(eligible)==r['eligible_rows'] and len(latest)==r['latest_rows'];assert len({x['value'] for x in eligible})==r['distinct_amounts'];values[(r['ts_code'],r['period'])]=(v,last)
 expected={}
 for issuer in set(raw.ts_code):
  for year in [2025,2026]:
   a,ac=values[(issuer,f'{year}-03-31')];b,bc=values[(issuer,f'{year}-06-30')]
   if b<a:expected[(issuer,year)]=(a,b,b-a,ac>bc)
 actual=json.loads((out/'negative_years.json').read_text());assert {(x['ts_code'],x['year']) for x in actual}==set(expected)
 for x in actual:
  a,b,delta,later=expected[(x['ts_code'],x['year'])];assert Decimal(x['q1'])==a and Decimal(x['h1'])==b and Decimal(x['derived_q2'])==delta and x['q1_clock_later']==later;assert not x['any_local_amount_variation'] and not x['any_eligible_local_nonnegative_pair']
 summary=json.loads((out/'summary.json').read_text());assert summary['raw_rows']==count and summary['negative_issuer_years']==len(expected) and summary['negative_2025']==sum(y==2025 for _,y in expected) and summary['negative_2026']==sum(y==2026 for _,y in expected)
 receipt=json.loads((out/'verification.json').read_text())
 for p,h in receipt['inputs'].items():assert sha(Path(p))==h
 for p,h in receipt['outputs'].items():assert sha(out/p)==h
 js(out/'independent_verification.json',dict(status='PASS',raw_zip_decimal_and_clock_rows=count,issuer_period_selection_checks=len(lineage),negative_issuer_year_checks=len(actual),code_sha256=sha(Path(__file__)),additional_inputs={str(CACHE/'forecast_v5/CSI_ALL.parquet'):sha(CACHE/'forecast_v5/CSI_ALL.parquet')},adoption=False));print('PASS',count,len(lineage),len(actual))
if __name__=='__main__':run()

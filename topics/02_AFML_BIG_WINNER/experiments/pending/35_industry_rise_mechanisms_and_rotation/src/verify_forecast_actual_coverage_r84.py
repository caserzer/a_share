import pandas as pd
from collections import Counter
from common import *
def run():
 out=ROOT/'outputs/r84';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 f=pd.read_parquet(ROOT/'data/r24_source_exclusion_overlay.parquet');records=[]
 for x in f.itertuples():
  if x.basis=='profit_cny' and 2020<=x.fiscal_year<=2025 and x.publication_proxy_date<=pd.Timestamp(x.fiscal_year,12,31):records.append(x.Index)
 expected=f.loc[records].reset_index(drop=True);joined=pd.read_parquet(out/'forecast_join.parquet');pd.testing.assert_frame_equal(expected,joined[f.columns].reset_index(drop=True))
 candidates=json.loads((out/'annual_actual_candidates.json').read_text());assert len(candidates)==len(expected[['stock_code','fiscal_year']].drop_duplicates());lookup={};cache={}
 for x in candidates:
  key=(x['stock_code'],x['fiscal_year']);assert key not in lookup;lookup[key]=x
  files=sorted(Path(rec['source_snapshot']).glob(f'{key[0]}.*.parquet'));assert len(files)==x['partition_count'];q=[]
  for p in files:
   assert str(p) in rec['reads']
   if p not in cache:cache[p]=pd.read_parquet(p)
   for index,z in cache[p].iterrows():
    if pd.Timestamp(z.REPORT_DATE)==pd.Timestamp(key[1],12,31):q.append((str(p),index,z))
  assert {(z['source_path'],z['source_row']) for z in x['source_rows']}=={(p,i) for p,i,z in q}
  status='no_local_company_partition' if not files else 'annual_period_absent' if not q else 'candidate';value=None
  if q:
   vals=[pd.to_numeric(z.PARENTNETPROFIT,errors='coerce') for p,i,z in q]
   if any(z.REPORT_TYPE!='年报' or z.CURRENCY!='CNY' for p,i,z in q):status='basis_mismatch'
   elif any(not np.isfinite(v) for v in vals):status='annual_value_missing'
   elif len(set(vals))!=1:status='annual_value_conflict'
   else:value=float(vals[0])
  assert x['status']==status and x['actual_profit_cny']==value
  assert x['update_after_notice']==any(pd.to_datetime(z.UPDATE_DATE,errors='coerce')>pd.to_datetime(z.NOTICE_DATE,errors='coerce') for p,i,z in q)
 for x in joined.itertuples():
  v=lookup[x.stock_code,x.fiscal_year];assert x.status==v['status']
  assert pd.isna(x.actual_profit_cny) if v['actual_profit_cny'] is None else x.actual_profit_cny==v['actual_profit_cny']
 s=json.loads((out/'summary.json').read_text());assert s['eligible_forecast_rows']==len(expected) and s['finite_forecast_rows']==int(np.isfinite(expected.value).sum())
 assert s['company_years']==len(lookup) and s['companies']==expected.stock_code.nunique()
 assert s['status_company_years']==dict(Counter(x['status'] for x in candidates)) and s['status_forecast_rows']==joined.status.value_counts().to_dict()
 assert s['actual_candidate_company_years']==sum(x['status']=='candidate' for x in candidates)
 assert s['candidate_updated_after_notice']==sum(x['status']=='candidate' and x['update_after_notice'] for x in candidates)
 js(out/'verification.json',dict(status='PASS',forecast_rows=len(joined),company_years=len(lookup),scope='all forecast eligibility, all annual candidate rows and source partitions independently checked',receipt_sha256=sha(out/'receipt.json'),verifier_sha256=sha(Path(__file__))))
 print('R84 VERIFIED',len(joined),len(lookup))
if __name__=='__main__':run()

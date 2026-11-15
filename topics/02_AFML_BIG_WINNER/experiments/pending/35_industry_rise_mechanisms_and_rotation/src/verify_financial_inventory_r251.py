from common import *
import pandas as pd
import pyarrow.parquet as pq
from collections import Counter

def run():
 out=ROOT/'outputs/r251';inventory=json.loads((out/'file_inventory.json').read_text());discovered=json.loads((out/'discovered_paths.json').read_text());assert [x['path'] for x in inventory]==discovered
 prior=json.loads((ROOT/'outputs/r115/receipt.json').read_text());old={Path(p).name:h for p,h in prior['reads'].items() if '/proxy/financials/' in p};numeric=[x for x in inventory if x['classification']=='numeric_financial_candidate'];proxy=[x for x in numeric if x['matches_R115_same_name']];others=[x for x in numeric if not x['matches_R115_same_name']];hashcounts=Counter();roots=Counter();unique={}
 for r in proxy:
  p=Path(r['path']);h=sha(p);assert h==r['sha256']==old[p.name];hashcounts[h]+=1;roots[str(p.parent)]+=1;schema=pq.ParquetFile(p).schema.names;assert not any(x in schema for x in ['c_pay_acq_const_fiolta','n_cashflow_act']);unique.setdefault(h,p)
 assert len(unique)==len(old)==1647 and set(hashcounts.values())=={3}
 published=json.loads((out/'unique_financial_content.json').read_text());byhash={x['sha256']:x for x in published};quarter3_rows=0;quarter3_issuers=0;periods=set()
 for h,p in unique.items():
  d=pd.read_parquet(p,columns=['REPORT_DATE','PARENTNETPROFIT','NOTICE_DATE','UPDATE_DATE']);dates=pd.to_datetime(d.REPORT_DATE,errors='coerce');actual={str(x.date()) for x in dates.dropna()};assert actual==set(byhash[h]['periods']) and len(d)==byhash[h]['rows'];assert int(d.PARENTNETPROFIT.notna().sum())==byhash[h]['nonmissing_targets']['PARENTNETPROFIT'];periods|=actual;has=dates.eq('2026-09-30');quarter3_rows+=int(has.sum());quarter3_issuers+=int(has.any())
 # Inspect all discovered receipt containers; assert their shape is understood.
 refs=[];shapes={}
 for r in inventory:
  if r['classification']!='query_receipts':continue
  data=json.loads(Path(r['path']).read_text());shapes[r['path']]=type(data).__name__
  containers=[('root',data)] if isinstance(data,list) else [(k,v) for k,v in data.items() if isinstance(v,list)]
  for role,records in containers:
   for x in records:
    if isinstance(x,dict) and x.get('api') in ['cashflow_vip','income_vip','fina_indicator_vip']:refs.append((r['path'],role,x.get('api'),x.get('query_id'),str((x.get('params') or {}).get('period')),x.get('retrieved_at'),x.get('raw_sha256')))
 actual=json.loads((out/'financial_query_receipts.json').read_text());assert Counter(refs)==Counter((x['path'],x['container_role'],x['api'],x['query_id'],str(x['period']),x['retrieved_at'],x['raw_sha256']) for x in actual)
 summary=json.loads((out/'summary.json').read_text());assert summary['discovered_paths']==len(inventory) and summary['numeric_files']==len(numeric) and summary['unique_numeric_contents']==len(unique)+len(others)
 raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');csv_checks=[]
 for item in others:
  path=Path(item['path']);assert path.suffix=='.csv';d=pd.read_csv(path,float_precision='round_trip',dtype={x:str for x in ['ts_code','report_type','comp_type','update_flag']});api='cashflow_vip' if 'c_pay_acq_const_fiolta' in d else 'income_vip';period=pd.to_datetime(d.end_date.astype(str));assert period.nunique()==1;baseline=raw[raw.api.eq(api)&raw.end_date.eq(period.iloc[0])]
  target=['n_cashflow_act','c_pay_acq_const_fiolta'] if api=='cashflow_vip' else ['n_income_attr_p'];cols=['ts_code','report_type','comp_type','update_flag']+target
  def records(frame):
   return Counter(tuple(None if pd.isna(v) else v for v in row) for row in frame[cols].itertuples(index=False,name=None))
  assert not (records(d)-records(baseline));periods.add(str(period.iloc[0].date()));csv_checks.append(dict(path=str(path),sha256=sha(path),api=api,period=str(period.iloc[0].date()),rows=len(d),subset_of_existing_R03=True,baseline_rows=len(baseline),new_value_rows=0))
 assert summary['unique_report_periods']==sorted(periods);js(out/'csv_existing_archive_checks.json',csv_checks)
 receipt=json.loads((out/'verification.json').read_text())
 for p,h in receipt['inputs'].items():assert sha(Path(p))==h
 for p,h in receipt['outputs'].items():assert sha(out/p)==h
 js(out/'independent_verification.json',dict(status='PASS',proxy_source_hash_checks=len(proxy),unique_proxy_contents=len(unique),proxy_copies_per_content=3,csv_rows_verified=sum(x['rows'] for x in csv_checks),csv_files=len(csv_checks),source_directories=dict(roots),quarter3_2026_rows=quarter3_rows,quarter3_2026_issuer_files=quarter3_issuers,receipt_container_shapes=shapes,financial_receipts=len(refs),new_numeric_economic_observations_relative_existing_R115_R03=0,code_sha256=sha(Path(__file__)),adoption=False));print('PASS',len(proxy),len(unique),len(csv_checks),'existing Q3',quarter3_rows,quarter3_issuers)
if __name__=='__main__':run()

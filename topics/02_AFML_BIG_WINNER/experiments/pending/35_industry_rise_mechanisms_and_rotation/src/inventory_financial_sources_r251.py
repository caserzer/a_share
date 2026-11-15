from common import *
import pandas as pd
import pyarrow.parquet as pq
from collections import Counter
TARGETS=['PARENTNETPROFIT','n_income_attr_p','c_pay_acq_const_fiolta','n_cashflow_act']
DATECOLS=['REPORT_DATE','end_date','NOTICE_DATE','UPDATE_DATE','proxy_available_date','archived_available_at']
def run():
 out=ROOT/'outputs/r251';paths=[Path(p) for p in json.loads((out/'discovered_paths.json').read_text())];prior=json.loads((ROOT/'outputs/r115/receipt.json').read_text());old=prior.get('reads',{});oldhashes={p:h for p,h in old.items() if '/proxy/financials/' in p};byname={Path(p).name:h for p,h in oldhashes.items()};rows=[];financial=[];receipt_rows=[];seen={};failures=[]
 for path in paths:
  r=dict(path=str(path),suffix=path.suffix)
  try:
   if path.suffix in ['.parquet','.csv']:
    if path.suffix=='.parquet':meta=pq.ParquetFile(path);cols=meta.schema.names;r['rows']=meta.metadata.num_rows
    else:cols=pd.read_csv(path,nrows=0).columns.tolist();r['rows']=None
    targets=[x for x in TARGETS if x in cols];r['target_fields']=targets;r['classification']='numeric_financial_candidate' if targets else 'announcement_index' if 'announcement' in cols else 'derived_or_other_schema'
    if targets:
     digest=sha(path);r['sha256']=digest;r['matches_R115_same_name']=digest==byname.get(path.name);r['unique_content_first_path']=seen.setdefault(digest,str(path));r['has_recorded_archive_clock']='archived_available_at' in cols
     if seen[digest]==str(path):
      use=[x for x in DATECOLS+TARGETS if x in cols];d=pd.read_parquet(path,columns=use) if path.suffix=='.parquet' else pd.read_csv(path,usecols=use);period='REPORT_DATE' if 'REPORT_DATE' in d else 'end_date' if 'end_date' in d else None;periods=pd.to_datetime(d[period].astype(str),errors='coerce') if period else pd.Series(dtype='datetime64[ns]');rec=dict(path=str(path),sha256=digest,rows=len(d),target_fields=targets,period_field=period,min_period=str(periods.min()),max_period=str(periods.max()),periods=sorted(str(x.date()) for x in periods.dropna().unique()),nonmissing_targets={c:int(d[c].notna().sum()) for c in targets},recorded_archive_clock='archived_available_at' in d,clock_ranges={c:dict(min=str(pd.to_datetime(d[c],errors='coerce').min()),max=str(pd.to_datetime(d[c],errors='coerce').max())) for c in ['NOTICE_DATE','UPDATE_DATE','archived_available_at'] if c in d});financial.append(rec)
   elif path.name.endswith('query_receipts.json'):
    data=json.loads(path.read_text());r['classification']='query_receipts';r['sha256']=sha(path)
    containers=[('root',data)] if isinstance(data,list) else [(k,v) for k,v in data.items() if isinstance(v,list)]
    r['receipt_container_roles']=[k for k,_ in containers]
    for role,records in containers:
     for x in records:
      if isinstance(x,dict) and x.get('api') in ['cashflow_vip','income_vip','fina_indicator_vip']:receipt_rows.append(dict(path=str(path),container_role=role,api=x.get('api'),query_id=x.get('query_id'),period=(x.get('params') or {}).get('period'),retrieved_at=x.get('retrieved_at'),raw_sha256=x.get('raw_sha256'),rows=x.get('rows')))
   elif path.suffix=='.zip':r['classification']='response_archive';r['sha256']=sha(path)
   else:r['classification']='other'
  except Exception as exc:r['classification']='inspection_error';r['error']=type(exc).__name__+': '+str(exc);failures.append(r.copy())
  rows.append(r)
 js(out/'file_inventory.json',rows);js(out/'unique_financial_content.json',financial);js(out/'financial_query_receipts.json',receipt_rows);js(out/'inspection_failures.json',failures)
 numeric=[x for x in rows if x['classification']=='numeric_financial_candidate'];summary=dict(discovered_paths=len(rows),classifications=dict(Counter(x['classification'] for x in rows)),numeric_files=len(numeric),unique_numeric_contents=len(financial),same_name_R115_hash_matches=sum(x['matches_R115_same_name'] for x in numeric),R115_financial_files=len(oldhashes),unique_report_periods=sorted(set(p for x in financial for p in x['periods'])),latest_numeric_period=max((x['max_period'] for x in financial),default=None),numeric_files_with_capex=sum('c_pay_acq_const_fiolta' in x['target_fields'] for x in numeric),numeric_files_with_total_ocf=sum('n_cashflow_act' in x['target_fields'] for x in numeric),financial_receipt_rows=len(receipt_rows),financial_receipt_periods=sorted(set(str(x['period']) for x in receipt_rows)),inspection_errors=len(failures),new_models=0,scope='Bounded filename/schema inventory, not proof of no undiscovered source')
 js(out/'summary.json',summary);js(out/'verification.json',dict(status='PASS' if not failures else 'PARTIAL_INSPECTION',inputs={str(p):sha(p) for p in [ROOT/'protocols/r251.json',out/'discovered_paths.json',ROOT/'outputs/r115/receipt.json',Path(__file__)]},outputs={p.name:sha(p) for p in out.iterdir() if p.suffix=='.json' and p.name!='verification.json'},adoption=False));print({k:v for k,v in summary.items() if k!='unique_report_periods'})
if __name__=='__main__':run()

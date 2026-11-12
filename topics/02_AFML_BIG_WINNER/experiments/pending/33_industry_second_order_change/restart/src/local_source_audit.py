import sys,json,collections
from pathlib import Path
import pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p27';OUT.mkdir(exist_ok=True)
base=Path('/home/xiaolv/.cache/a_share');missingfile=EP/'restart/p23/missing_reasons.csv';assign=base/'ep32/extension_v2/products/assignments.parquet';missing=pd.read_csv(missingfile,parse_dates=['date'])[['instrument','date']].drop_duplicates();j=pd.read_parquet(assign);lookup=j[['instrument','security_id']].drop_duplicates();api=[];sources=[]
for root in [base/'ep32/industry_v1',base/'ep32/extension_v2/sources',base/'ep32/source_probe']:
 for f in root.glob('*.json'):
  if 'receipt' not in f.name:continue
  try:data=json.loads(f.read_text())
  except (ValueError,OSError):continue
  api.append(dict(path=str(f),api=str(data.get('api',data.get('endpoint','UNSPECIFIED'))) if isinstance(data,dict) else 'BATCH_RECEIPT',sha256=sha(f)))
pd.DataFrame(api).to_csv(OUT/'industry_source_receipts.csv',index=False)
identityfile=EP.parent/'32_industry_rotation_cycle_observation/extensions/v4_adaptive_6_18_months/outputs/audits/inputs.json';release=Path(json.loads(identityfile.read_text())['price_release'])
roots={'legacy_prices':base/'ep30_d2/prices','backfill_prices':base/'ep30_d2/backfill_v2/normalized/prices','current_qfq':base/'ep30_d2/pit_v5/normalized/prices_qfq','release_qfq':release/'normalized/prices_qfq'}
rows=[];reads={};cache={}
for _,r in missing.iterrows():
 for sid in lookup.loc[lookup.instrument.eq(r.instrument),'security_id']:
  for name,root in roots.items():
   f=root/f'{sid}.parquet';record=dict(instrument=r.instrument,date=r.date,security_id=sid,source=name,path=str(f),file_exists=f.exists(),date_rows=0)
   if f.exists():
    if f not in cache:cache[f]=pd.read_parquet(f);reads[str(f)]=sha(f)
    a=cache[f];key=next((c for c in ['date','trade_date'] if c in a),None)
    if key:
     date=pd.to_datetime(a[key],errors='coerce');z=a[date.eq(r.date)];record['date_rows']=len(z);record['min_date']=str(date.min());record['max_date']=str(date.max())
     if len(z):record['matching_fields']=z[[c for c in ['close','qfq_close','close_conflict','vendor_trade_status','execution_reason','factor_chain_id'] if c in z]].to_json(orient='records',force_ascii=False)
   rows.append(record)
a=pd.DataFrame(rows);a.to_csv(OUT/'missing_date_source_checks.csv',index=False)
# Inspect candidate files that might look like an industry quote series.
examples=[base/'ep32/industry_v1/L1.parquet',next((base/'ep30_d2/proxy/industry').glob('*.parquet')),base/'ep32/extension_v2/sources/000985.CSI.parquet']
for f in examples:
 if f.exists():
  b=pd.read_parquet(f);sources.append(dict(path=str(f),columns=list(b.columns),rows=len(b),sha256=sha(f)))
(OUT/'candidate_schemas.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
(OUT/'receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [missingfile,assign,identityfile,Path(__file__),EP/'restart/P27_local_source_audit_plan.md']},price_reads=reads,unique_missing_dates=len(missing),checked_rows=len(a),found_date_rows=int(a.date_rows.sum()),read_only=True),indent=2)+'\n')
print(pd.DataFrame(api).api.value_counts().to_string());print(a.groupby('source').agg(checks=('source','size'),files=('file_exists','sum'),matched=('date_rows','sum')).to_string());print(json.dumps(sources,ensure_ascii=False)[:1200])

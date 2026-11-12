"""Read-only inventory of documented price sources and discoverable chain/calendar candidates."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import pyarrow.parquet as pq
from audit_local_inputs import EP, PRIOR, CACHE, sha

def inspect(item):
    path, role = item
    try:
        pf=pq.ParquetFile(path)
        names=pf.schema.names
        col=next((x for x in ['date','trade_date','session'] if x in names),None)
        if col is None:return dict(path=str(path),role=role,status='NO_DATE_COLUMN',rows=pf.metadata.num_rows)
        # Read only the actual date column; never infer data freshness from mtime.
        values=pq.read_table(path,columns=[col]).column(col).to_pandas()
        if col=='trade_date':values=pd.to_datetime(values.astype(str),format='%Y%m%d',errors='coerce')
        else:values=pd.to_datetime(values,errors='coerce')
        return dict(path=str(path),role=role,status='READ_DATE_COLUMN',rows=len(values),date_column=col,
            first=str(values.min()),last=str(values.max()),after_frozen_cutoff=int(values.gt(pd.Timestamp('2026-10-21')).sum()),missing_dates=int(values.isna().sum()))
    except Exception as exc:
        return dict(path=str(path),role=role,status='READ_ERROR',error=str(exc)[:300])

def main():
    out=EP/'outputs/local_confirmation_range_20261112';out.mkdir(exist_ok=False)
    audit=EP.parent/'32_industry_rotation_cycle_observation/extensions/v4_adaptive_6_18_months/outputs/audits/inputs.json'
    doc=json.loads(audit.read_text());release=Path(doc['price_release'])
    paths={release/k:'REGISTERED_PRICE_PARTITION' for k in doc['V2_input_identity']['price_files'] if 'prices' in k and k.endswith('.parquet')}
    paths[PRIOR/'daily_industries.parquet']='CURRENT_INDUSTRY_CHAIN'
    paths[CACHE/'forecast_v5/CSI_ALL.parquet']='CURRENT_MARKET'
    base=CACHE.parent
    for f in base.rglob('*.parquet'):
        if f.name in ['daily_industries.parquet','calendar.parquet','sessions.parquet']:
            paths.setdefault(f,'DISCOVERED_CHAIN_OR_CALENDAR')
    with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(inspect,sorted(paths.items(),key=lambda x:str(x[0]))))
    pd.DataFrame(rows).to_csv(out/'source_dates.csv',index=False)
    good=[r for r in rows if r['status']=='READ_DATE_COLUMN'];fresh=[r for r in good if r['after_frozen_cutoff']>0]
    summary=dict(paths_inspected=len(rows),registered_price_partitions=sum(r['role']=='REGISTERED_PRICE_PARTITION' for r in rows),status_counts=pd.Series([r['status'] for r in rows]).value_counts().to_dict(),sources_after_cutoff=fresh,cutoff='2026-10-21',limits='Documented registered price partitions and cache-discovered calendars/chains only. Calendar dates alone do not prove price availability. Not an exhaustive search of every local service or data directory.')
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps({'inputs':{str(audit):sha(audit),str(Path(__file__)):sha(Path(__file__)),str(EP/'protocols/local_confirmation_audit/plan.md'):sha(EP/'protocols/local_confirmation_audit/plan.md')},'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()}},indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()

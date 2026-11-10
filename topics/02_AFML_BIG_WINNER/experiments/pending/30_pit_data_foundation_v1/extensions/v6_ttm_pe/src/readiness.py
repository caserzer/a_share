"""Coverage only: no labels, future returns, model fitting or outcome selection."""
import json
import numpy as np
import pandas as pd
from pe_common import CACHE, OUT, sha, write_json, utc_now
from prepare_pe import BUILD

WINDOWS=(21,42,63,126,252,504,756)

def valid_window(panel, window):
    positive=panel.where(np.isfinite(panel) & panel.gt(0))
    return positive.rolling(window+1,min_periods=window+1).count().eq(window+1)

def main():
    dates=pd.DatetimeIndex(pd.read_parquet(BUILD/'inputs/calendar.parquet').date)
    parts=[pd.read_parquet(p,columns=['date','security_id','pe_ttm'])
           for p in sorted((BUILD/'normalized/eastmoney').glob('*.parquet'))]
    f=pd.concat(parts,ignore_index=True)
    f=f[f.security_id.notna()]
    if f.duplicated(['date','security_id']).any():
        raise ValueError('Duplicate PE observations')
    panel=f.pivot(index='date',columns='security_id',values='pe_ttm').reindex(dates)
    del f,parts
    assignments=CACHE.parents[1]/'ep32/extension_v2/products/assignments.parquet'
    # Deliberately never read the forward-return fields stored in the same artifact.
    a=pd.read_parquet(assignments,columns=['date','security_id','era','level','industry_code'])
    a=a.drop_duplicates(['era','level','industry_code','date','security_id']).copy()
    row=panel.index.get_indexer(pd.to_datetime(a.date))
    col=panel.columns.get_indexer(a.security_id)
    supported=(row>=0)&(col>=0)
    a['positive_pe']=False
    a.loc[supported,'positive_pe']=np.isfinite(panel.to_numpy()[row[supported],col[supported]])
    metrics=[]
    for window in WINDOWS:
        valid=valid_window(panel,window)
        name=f'continuous_positive_{window}'
        a[name]=False
        a.loc[supported,name]=valid.to_numpy()[row[supported],col[supported]]
        for year,g in valid.groupby(valid.index.year):
            metrics.append(dict(year=int(year),window=window,eligible_stock_days=int(g.to_numpy().sum())))
        del valid
    cols=['positive_pe']+[f'continuous_positive_{w}' for w in WINDOWS]
    a['members']=1
    grouped=a.groupby(['era','level','industry_code','date'],as_index=False)[['members']+cols].sum()
    grouped.to_csv(OUT/'ep32_industry_monthly_coverage.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    a['year']=pd.to_datetime(a.date).dt.year
    summary=a.groupby(['year','level'],as_index=False)[['members']+cols].sum()
    for col in cols:
        summary[col+'_coverage']=summary[col]/summary.members
    summary.to_csv(OUT/'ep32_coverage_summary.csv',index=False)
    pd.DataFrame(metrics).to_csv(OUT/'window_coverage_yearly.csv',index=False)
    write_json(OUT/'readiness_receipt.json',dict(at=utc_now(),provider='eastmoney',windows=WINDOWS,
        source_assignment_sha256=sha(assignments),source_assignment=str(assignments),
        assignment_rows=len(a),calendar_sessions=len(panel),securities=len(panel.columns),
        strict_window='all w+1 consecutive calendar sessions have finite positive PE',
        no_forward_fields_read=True,no_model_or_outcome_analysis=True))
    print(summary[summary.year.between(2021,2024)].to_string(index=False),flush=True)

if __name__=='__main__':main()

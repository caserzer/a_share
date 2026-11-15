"""Locate omitted portfolio paths without modifying selections or filling outcomes."""
import pandas as pd
from common import *


def run():
    intervals=pd.read_csv(ROOT/'outputs/r04/intervals.csv',parse_dates=['origin','entry','exit'])
    d=pd.read_parquet(CACHE/'forecast_v5/daily_industries.parquet')
    days=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
    rows=[]
    for r in intervals[intervals.status.eq('missing_selected_path')].itertuples():
        required=days[(days>=r.entry)&(days<=r.exit)]
        for code in r.missing_codes.split(';'):
            g=d[d.era.eq(r.era)&d.level.eq(r.level)&d.industry_code.eq(code)].set_index('date').reindex(required)
            missing=g.nav.isna();breaks=g.block.dropna().nunique()>1
            rows.append(dict(era=r.era,level=r.level,method=r.method,origin=r.origin,entry=r.entry,exit=r.exit,industry_code=code,
                missing_days=int(missing.sum()),required_days=len(required),multiple_blocks=breaks,
                first_missing=required[missing][0] if missing.any() else pd.NaT,last_missing=required[missing][-1] if missing.any() else pd.NaT,
                min_observed_members=g.members.min(),min_observed_coverage=g.coverage.min(),
                status='needs_constituent_level_quality_audit; no fill or replacement'))
    result=pd.DataFrame(rows);result.to_csv(ROOT/'outputs/r04/missing_path_audit.csv',index=False)
    js(ROOT/'outputs/r04/missing_path_receipt.json',dict(code_sha256=sha(__file__),input_sha256=sha(ROOT/'outputs/r04/intervals.csv'),
        failed_portfolio_intervals=int(intervals.status.eq('missing_selected_path').sum()),failed_selections=len(result),
        unique_industries=result[KEY].drop_duplicates().shape[0],next='inspect raw constituents and missing/conflicting chains in precisely these intervals'))
    print('GAP AUDIT',len(result),'failed selections;',result[KEY].drop_duplicates().shape[0],'industry identities')

if __name__=='__main__':run()

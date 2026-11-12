"""Check fixed identities, price-supported confirmation, and input receipts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
out=EP/'outputs/r00_v2_enhancement03_recovery';old=EP/'outputs/r00_v2_enhancement03'
a=pd.read_parquet(old/'children.parquet');b=pd.read_parquet(out/'children.parquet')
fields=['parent_id','start_i','end_i','prior_slope','after_slope','delta','positive_knots','start_date','end_date']
pd.testing.assert_frame_equal(a[fields],b[fields])
pd.testing.assert_frame_equal(pd.read_parquet(old/'parent_fits.parquet'),pd.read_parquet(out/'parent_fits.parquet'))
assert b.child_id.is_unique
assert b.loc[a.status.eq('PATH_SUPPORTED'),'status'].eq('PATH_SUPPORTED').all()
pd.testing.assert_series_equal(a.loc[a.status.eq('PATH_SUPPORTED'),'confirm_date'],b.loc[a.status.eq('PATH_SUPPORTED'),'confirm_date'])
parents=pd.read_parquet(EP/'outputs/r00_v2_path_probe03_symmetric_calendar_corrected/processes.parquet').set_index('process_id')
raw=pd.read_parquet(PRIOR/'daily_industries.parquet',columns=['era','industry_code','block','date','nav'])
raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['week']=raw.date.dt.to_period('W-SUN');raw['y']=np.log(raw.nav)
groups={k:g for k,g in raw.groupby(['era','industry_code','block'])}
for row in b.itertuples():
    p=parents.loc[row.parent_id];g=groups[(p.era,p.industry_code,p.block)]
    w=g[g.date.between(p.reference_week_start,p.end_date)].groupby('week').agg(y=('y','median'),end=('date','max'))
    z=w.y.to_numpy();first=None
    for i in range(row.start_i+4,row.end_i+1):
        if all(float(z[j])>float(z[row.start_i]) for j in range(i-3,i+1)):
            first=i;break
    assert (first is not None)==(row.status=='PATH_SUPPORTED')
    if first is not None:assert row.confirm_date==str(w.end.iloc[first].date())
    elif row.end_unknown:assert row.status=='RIGHT_UNKNOWN'
    else:assert row.status=='NOT_RETAINED'
    assert row.start_i>=4 and row.end_i>=row.start_i+4
    assert row.end_date<=p.end_date and row.start_date>=p.start_date
    assert z[row.start_i]>=z[row.start_i-4]-1e-12
for _,g in b.groupby('parent_id'):
    g=g.sort_values('start_i')
    assert (g.start_i.iloc[1:].to_numpy()>g.end_i.iloc[:-1].to_numpy()).all()
receipt=json.loads((out/'receipt.json').read_text())
for path,h in receipt['inputs'].items():assert sha(Path(path))==h
for name,h in receipt['artifacts'].items():assert sha(out/name)==h
trans=pd.crosstab(a.status,b.status)
result=dict(children_checked=len(b),fits_unchanged=True,identities_unchanged=True,
            prior_supported_and_confirmation_dates_preserved=True,
            new_supported=int((~a.status.eq('PATH_SUPPORTED')&b.status.eq('PATH_SUPPORTED')).sum()),
            counts=b.status.value_counts().to_dict(),checks=['independent earliest 4-week support','all children within parents',
            'nonoverlapping children','closed unsupported versus open unknown','all input and output hashes'],
            script_sha256=sha(Path(__file__)))
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');trans.to_csv(out/'status_bridge.csv')
print(json.dumps(result,indent=2));print(trans.to_string())

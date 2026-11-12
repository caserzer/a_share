"""Independent output checks for the retained calendar-corrected prototype."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
out=EP/'outputs/r00_v2_path_probe03_symmetric_calendar_corrected'
r=pd.read_parquet(out/'processes.parquet');w=pd.read_parquet(out/'weekly_evaluation_states.parquet')
raw=pd.read_parquet(PRIOR/'daily_industries.parquet',columns=['era','industry_code','block','date','nav'])
raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['week']=raw.date.dt.to_period('W-SUN');raw['y']=np.log(raw.nav)
groups={key:g.groupby('week').agg(y=('y','median'),end=('date','max')) for key,g in raw.groupby(['era','industry_code','block'])}
assert r.process_id.is_unique
assert not w.duplicated(['era','industry_code','block','week']).any()
assert r[r.status.eq('RIGHT_UNKNOWN')].right_open.all()
assert r[r.status.eq('CONFIRMED')].confirm_date.notna().all()
for _,g in r.groupby(['era','industry_code','block','complete_week_run']):
    g=g.sort_values('start_date')
    assert (g.start_date.iloc[1:].to_numpy()>g.end_date.iloc[:-1].to_numpy()).all()
for p in r.itertuples():
    g=groups[(p.era,p.industry_code,p.block)]
    idx={str(d.date()):i for i,d in enumerate(g.end)}
    a=idx[p.start_date];b=idx[p.end_date];z=g.y.to_numpy();base=z[a]
    eps=max(.002,2*np.median(np.abs(np.diff(z[a-8:a+1]))))
    assert np.isclose(eps,p.epsilon,atol=1e-12)
    assert z[idx[p.visible_date]]-base>=eps-1e-12
    if p.status=='CONFIRMED':
        c=idx[p.confirm_date]
        assert c-a>=4 and (z[c-3:c+1]>base).all() and z[c]-base>=eps-1e-12
    if not p.right_open:
        d=idx[p.breach_date]
        assert d==b+1 and max(z[a:d+1])-z[d]>=eps-1e-12
assert w[w.week.eq('2026-10-19/2026-10-25')].state.eq('PARTIAL_WEEK_UNKNOWN').all()
receipt=json.loads((out/'receipt.json').read_text())
for f,h in receipt['inputs'].items():assert sha(Path(f))==h,f
for f,h in receipt['artifacts'].items():assert sha(out/f)==h,f
result=dict(processes_checked=len(r),weekly_rows_checked=len(w),
 checks=['unique process and weekly keys','nonoverlapping parent intervals per complete run',
 'independently recomputed all epsilon scales','all confirmation four-week conditions',
 'all recorded breach inequalities','terminal incomplete week never confirms',
 'all input and artifact hashes verified'],script_sha256=sha(Path(__file__)))
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

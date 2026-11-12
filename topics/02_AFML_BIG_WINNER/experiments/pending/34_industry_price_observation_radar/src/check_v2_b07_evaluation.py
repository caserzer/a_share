"""Cross-check actual frozen events, credited identities and coverage unions."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
out=EP/'outputs/v2_b07/evaluation_parent_child';receipt=json.loads((out/'receipt.json').read_text())
for f,h in receipt['inputs'].items():assert sha(Path(f))==h,f
for f,h in receipt['artifacts'].items():assert sha(out/f)==h,f
raw=pd.read_parquet(PRIOR/'daily_industries.parquet',columns=['era','industry_code','block','date','nav'])
raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['y']=np.log(raw.nav);raw['week']=raw.date.dt.to_period('W-SUN').astype(str)
bases=raw.groupby(['era','industry_code','block','week']).y.median().map(np.exp).to_dict()
prices={(r.era,r.industry_code,int(r.block),str(r.date.date())):r.nav for r in raw.itertuples()}
p=pd.read_parquet(EP/'outputs/r00_v2_path_probe03_symmetric_calendar_corrected/processes.parquet').set_index('process_id')
c=pd.read_parquet(EP/'outputs/r00_v2_enhancement03_recovery/children.parquet').set_index('child_id')
summ=pd.read_csv(out/'all_run_summary.csv');nnew=nevents=ncredits=0
for run in summ.itertuples():
    root=out/'runs'/run.run_id
    ev=pd.read_parquet(EP/'outputs'/run.run_id/'events.parquet').set_index('event_id')
    le=pd.read_parquet(root/'event_quality.parquet');pc=pd.read_parquet(root/'parent_coverage.parquet');cc=pd.read_parquet(root/'child_coverage.parquet')
    assert le.run_id.eq(run.run_id).all() and le.event_id.is_unique
    assert set(le.event_id)==set(ev[ev.kind.isin(['NEW','UPDATE'])].index)
    good=le[le.status.eq('COVERED')].sort_values(['date','event_id'])
    assert good.primary_id.is_unique
    ph=good.groupby('parent_id',sort=False).head(1)
    ch=good[good.primary_type.eq('CHILD')]
    assert set(pc.loc[pc.covered,'process_id'])==set(ph.parent_id)
    assert set(cc.loc[cc.covered,'process_id'])==set(ch.primary_id)
    parentindex=pc.set_index('process_id');childindex=cc.set_index('process_id')
    for row in ph.itertuples():
        z=parentindex.loc[row.parent_id];assert z.first_date==row.date and z.source==row.kind
    for row in ch.itertuples():
        z=childindex.loc[row.primary_id];assert z.first_date==row.date and z.source==row.kind
    for row in good.itertuples():
        src=ev.loc[row.event_id];assert src.positive_evidence and str(src.date.date())==row.date
        if row.primary_type=='CHILD':
            z=c.loc[row.primary_id];assert src.enhancement_evidence and z.status=='PATH_SUPPORTED'
        else:
            z=p.loc[row.primary_id];assert z.status=='CONFIRMED' and not z.left_context_unknown
        assert z.start_date<=row.date<=z.end_date
        nav=prices[(src.era,src.industry_code,int(src.block),row.date)]
        base=bases[(src.era,src.industry_code,int(src.block),str(pd.Timestamp(z.start_date).to_period('W-SUN')))]
        assert nav>base
    new=le[le.kind.eq('NEW')];u=new.status.str.contains('UNKNOWN');e=new.status.eq('COVERED')
    assert len(new)==run.new_total and int(e.sum())==run.new_effective and int(u.sum())==run.new_unknown
    assert int(pc.covered.sum())==run.parent_covered and int(cc.covered.sum())==run.child_covered
    assert int(pc.timing.eq('TIMELY').sum()+pc.timing.eq('LATE').sum())==run.parent_covered
    nnew+=len(new);nevents+=len(le);ncredits+=len(good)
result=dict(runs=len(summ),event_rows_checked=nevents,new_rows_checked=nnew,primary_credits_checked=ncredits,
    checks=['all original and output hashes','exact event-key conservation','one primary credit per process',
    'parent union independently rebuilt from primary credits','child coverage independently rebuilt',
    'all credited events original positive/enhancement evidence and actual price alignment',
    'all denominator/count/unknown reconciliations'],script_sha256=sha(Path(__file__)))
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

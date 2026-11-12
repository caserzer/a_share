"""Separate post-alert outcome ledger; does not modify coverage or quality."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    out=EP/'outputs/v2_b01/followup'
    if out.exists():raise FileExistsError('Preserve outcomes')
    out.mkdir()
    source=PRIOR/'daily_industries.parquet';eventfile=EP/'outputs/v2_b01/events.parquet'
    qfile=EP/'outputs/v2_b01/evaluation/event_quality.parquet'
    original_quality_hash=sha(qfile)
    raw=pd.read_parquet(source,columns=['date','day_i','era','industry_code','block','nav','relative_nav'])
    groups={k:g.set_index('date') for k,g in raw.groupby(['era','industry_code'])}
    last=raw.day_i.max();events=pd.read_parquet(eventfile);rows=[];prefix_checks=0
    for e in events[events.kind.eq('NEW')].itertuples():
        g=groups[(e.era,e.industry_code)];origin=g.loc[e.date];day=int(origin.day_i)
        # Independently recompute past features using only a truncated price chain.
        for h in (5,20):
            prefix=g[g.day_i.between(day-h,day)]
            assert len(prefix)==h+1 and prefix.block.eq(origin.block).all()
            actual=prefix.sort_values('day_i').nav.iloc[-1]/prefix.sort_values('day_i').nav.iloc[0]-1
            assert np.isclose(actual,getattr(e,f'r{h}'));prefix_checks+=1
        for h in (20,60):
            path=g[g.day_i.between(day,day+h)].sort_values('day_i')
            valid=len(path)==h+1 and path.nav.gt(0).all() and path.block.eq(origin.block).all()
            status='MATURE' if valid else 'IMMATURE' if day+h>last else 'DATA_OR_CLASSIFICATION_GAP'
            rel=path.relative_nav
            rows.append(dict(event_id=e.event_id,horizon=h,status=status,
                absolute_return=float(path.nav.iloc[-1]/path.nav.iloc[0]-1) if valid else None,
                relative_return=float(rel.iloc[-1]/rel.iloc[0]-1) if valid and rel.notna().all() and rel.gt(0).all() else None))
    r=pd.DataFrame(rows);r.to_parquet(out/'new_followup.parquet',index=False)
    summary={}
    for h,g in r.groupby('horizon'):
        mature=g[g.status.eq('MATURE')]
        summary[int(h)]=dict(status=g.status.value_counts().to_dict(),
            absolute_median=float(mature.absolute_return.median()),
            absolute_positive_fraction=float(mature.absolute_return.gt(0).mean()),
            relative_known=int(mature.relative_return.notna().sum()),
            relative_median=float(mature.relative_return.median()))
    assert sha(qfile)==original_quality_hash
    (out/'summary.json').write_text(json.dumps(dict(scope='Post-alert descriptive outcomes only',
        prefix_feature_checks=prefix_checks,outcomes=summary),indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [source,eventfile,qfile,Path(__file__)]},
        artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print((out/'summary.json').read_text())


if __name__=='__main__':main()

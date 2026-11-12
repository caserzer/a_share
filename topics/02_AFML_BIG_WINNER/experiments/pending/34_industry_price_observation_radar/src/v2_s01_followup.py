"""Post-alert price paths, separate from process discovery accounting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha


def main():
    root=EP/'outputs/v2_s01';out=root/'followup'
    if out.exists():raise FileExistsError('Preserve descriptive paths')
    out.mkdir()
    source=PRIOR/'daily_industries.parquet';marketfile=CACHE/'forecast_v5/CSI_ALL.parquet'
    paths=[source,marketfile,EP/'protocols/v2_s01/followup_plan.md',Path(__file__)]
    raw=pd.read_parquet(source,columns=['date','day_i','era','industry_code','block','nav']);market=pd.read_parquet(marketfile).close
    groups={k:g.set_index('day_i').sort_index() for k,g in raw.groupby(['era','industry_code'])}
    dateidx=raw[['date','day_i']].drop_duplicates().set_index('date').day_i.to_dict();last=int(raw.day_i.max())
    records=[]
    for arm in ['A','B']:
        evfile=root/arm/'events.parquet';qfile=root/'evaluation_parent_child/runs/v2_s01'/arm/'event_quality.parquet'
        paths.extend([evfile,qfile]);quality_before=sha(qfile);ev=pd.read_parquet(evfile)
        for row in ev[ev.kind.eq('NEW')].itertuples():
            day=int(dateidx[row.date]);g=groups[(row.era,row.industry_code)]
            for h in [20,60,63,126,252]:
                part=g.reindex(range(day,day+h+1))
                valid=part.nav.gt(0).all() and part.block.eq(row.block).all()
                status='MATURE' if valid else 'IMMATURE' if day+h>last else 'DATA_OR_CLASSIFICATION_GAP'
                rel=market.reindex(pd.DatetimeIndex(part.date))
                relative_known=valid and rel.notna().all() and rel.gt(0).all()
                nav=part.nav.to_numpy()
                records.append(dict(arm=arm,event_id=row.event_id,date=str(row.date.date()),era=row.era,industry_code=row.industry_code,
                    horizon=h,status=status,absolute_return=float(nav[-1]/nav[0]-1) if valid else None,
                    max_drawdown=float((nav/np.maximum.accumulate(nav)-1).min()) if valid else None,
                    relative_return=float((nav[-1]/nav[0])/(rel.iloc[-1]/rel.iloc[0])-1) if relative_known else None))
        assert sha(qfile)==quality_before
    r=pd.DataFrame(records);r.to_parquet(out/'all_new_paths.parquet',index=False)
    summary=[]
    for (arm,h),g in r.groupby(['arm','horizon']):
        m=g[g.status.eq('MATURE')]
        summary.append(dict(arm=arm,horizon=int(h),total=len(g),mature=len(m),immature=int(g.status.eq('IMMATURE').sum()),
            gap=int(g.status.eq('DATA_OR_CLASSIFICATION_GAP').sum()),absolute_median=float(m.absolute_return.median()),
            positive_fraction=float(m.absolute_return.gt(0).mean()),drawdown_median=float(m.max_drawdown.median()),
            relative_known=int(m.relative_return.notna().sum()),relative_median=float(m.relative_return.median())))
    pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
    (out/'receipt.json').write_text(json.dumps(dict(scope='Post-alert descriptions, no label or signal changes',inputs={str(p):sha(p) for p in paths},
        artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')
    print(pd.DataFrame(summary).to_string(index=False))


if __name__=='__main__':main()

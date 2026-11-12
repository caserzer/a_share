"""One fixed real-price observation-window diagnostic; no signals ranked."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    out=EP/'outputs/r00_v2_window_probe01'
    if out.exists():raise FileExistsError('Do not overwrite first run')
    out.mkdir()
    source=PRIOR/'daily_industries.parquet'
    candidates=EP/'outputs/r00_v2_label_probe02/persistence/candidate_diagnostic.parquet'
    plan=EP/'protocols/r00_v2/window_probe01/plan.md'
    receipt=json.loads((PRIOR/'receipt.json').read_text())
    calendar=Path(next(x for x in receipt['inputs'] if x.endswith('/calendar.parquet')))
    inputs={str(f):sha(f) for f in [source,candidates,plan,calendar,Path(__file__)]}
    raw=pd.read_parquet(source,columns=['date','day_i','era','industry_code','block','nav'])
    groups={k:g.sort_values('day_i').reset_index(drop=True) for k,g in raw[raw.nav.notna()&raw.nav.gt(0)&raw.block.notna()].groupby(['era','industry_code','block'])}
    cal=pd.read_parquet(calendar).sort_values('date')
    reviews=pd.DatetimeIndex(cal.groupby(cal.date.dt.to_period('W-SUN')).date.max())
    results=[]
    for row in pd.read_parquet(candidates).to_dict('records'):
        g=groups[(row['era'],row['industry_code'],row['block'])]
        r5=g.nav/g.nav.shift(5)-1
        part=g[g.date.between(row['start_date'],row['end_date'])]
        base=part.nav.iloc[0]
        visible=part.index[(part.nav>=base)&r5.loc[part.index].gt(0)]
        first=int(visible[0]) if len(visible) else None
        end=int(part.index[-1]); breach=None; restart=False
        if first is not None:
            peak=float(g.nav.iloc[first])
            for i in range(first,end+1):
                price=float(g.nav.iloc[i]);peak=max(peak,price)
                tolerance=max(.03,(peak/base-1)/2)
                if 1-price/peak>=tolerance:
                    breach=i;break
            stop=breach-1 if breach is not None else end
            if breach is not None:
                post=g.iloc[breach+1:end+1]
                restart=bool(((post.nav>=base)&r5.loc[post.index].gt(0)).any())
            opportunities=reviews[(reviews>=g.date.iloc[first])&(reviews<=g.date.iloc[stop])] if stop>=first else []
        else:
            stop=None;opportunities=[]
        def dt(i):return g.date.iloc[i].strftime('%Y-%m-%d') if i is not None else None
        results.append(dict(segment_id=row['segment_id'],family_id=row['family_id'],
            era=row['era'],industry_code=row['industry_code'],kind=row['kind'],
            label_status=row['diagnostic_status'],end_boundary=row['end_boundary'],
            stage_start=row['start_date'],stage_end=row['end_date'],visible_start=dt(first),
            useful_end=dt(stop),interruption=dt(breach),restart_within_stage=restart,
            review_opportunities=len(opportunities),
            timely_last_review=opportunities[min(1,len(opportunities)-1)].strftime('%Y-%m-%d') if len(opportunities) else None))
    r=pd.DataFrame(results);r.to_parquet(out/'windows.parquet',index=False)
    retained=r[r.label_status.eq('RETAINED')]
    summary=dict(scope='W01 fixed window diagnostic; not method performance',candidates=len(r),
        label_retained=len(retained),retained_no_visible=int(retained.visible_start.isna().sum()),
        retained_no_review=int(retained.review_opportunities.eq(0).sum()),
        retained_interrupted=int(retained.interruption.notna().sum()),
        retained_restarted=int(retained.restart_within_stage.sum()),
        retained_terminal_unknown=int(retained.end_boundary.sum()),
        retained_opportunities=retained.review_opportunities.quantile([0,.1,.5,.9,1]).to_dict())
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    cases=json.loads((EP/'outputs/r00_v2_cases/batch01/selected_cases.json').read_text())
    cross=[]
    for c in cases:
        q=r[r.era.eq(c['era'])&r.industry_code.eq(c['industry_code'])&r.stage_start.le(c['cutoff'])&r.stage_end.ge(c['cutoff'])]
        for z in q.to_dict('records') or [None]:
            cross.append(dict(case_id=c['case_id'],industry=c['industry_name'],cutoff=c['cutoff'],
                segment=None if z is None else z['segment_id'],label_status=None if z is None else z['label_status'],
                visible_start=None if z is None else z['visible_start'],useful_end=None if z is None else z['useful_end'],
                interruption=None if z is None else z['interruption'],restart=None if z is None else z['restart_within_stage']))
    pd.DataFrame(cross).to_csv(out/'fixed_case_crosswalk.csv',index=False)
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2));print(pd.DataFrame(cross).to_string(index=False))


if __name__=='__main__':main()

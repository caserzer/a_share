"""Recoverable observable phases, evaluated separately from process qualification."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def windows(prices, r5):
    result=[];start=None;base=peak=None
    for i,price in enumerate(prices):
        if start is None:
            if np.isfinite(r5[i]) and r5[i]>0:
                start=i;base=peak=price
        else:
            peak=max(peak,price)
            if 1-price/peak>=max(.03,(peak/base-1)/2):
                result.append((start,i-1,i));start=None
    if start is not None:result.append((start,len(prices)-1,None))
    return result


def main():
    out=EP/'outputs/r00_v2_window_recovery'
    if out.exists():raise FileExistsError('Preserve first run')
    out.mkdir()
    source=PRIOR/'daily_industries.parquet'
    candidates=EP/'outputs/r00_v2_label_probe02/persistence/candidate_diagnostic.parquet'
    plan=EP/'protocols/r00_v2/window_probe01/recovery_plan.md'
    rec=json.loads((PRIOR/'receipt.json').read_text())
    calendar=Path(next(x for x in rec['inputs'] if x.endswith('/calendar.parquet')))
    inputs={str(f):sha(f) for f in [source,candidates,plan,calendar,Path(__file__)]}
    raw=pd.read_parquet(source,columns=['date','era','industry_code','block','nav'])
    groups={k:g.sort_values('date').reset_index(drop=True) for k,g in raw[raw.nav.notna()&raw.nav.gt(0)&raw.block.notna()].groupby(['era','industry_code','block'])}
    cal=pd.read_parquet(calendar);reviews=pd.DatetimeIndex(cal.groupby(cal.date.dt.to_period('W-SUN')).date.max())
    spans=[];rows=[]
    for row in pd.read_parquet(candidates).to_dict('records'):
        g=groups[(row['era'],row['industry_code'],row['block'])].copy()
        g['r5']=g.nav/g.nav.shift(5)-1
        part=g[g.date.between(row['start_date'],row['end_date'])].reset_index(drop=True)
        ww=windows(part.nav.to_numpy(),part.r5.to_numpy());count=0;active=0
        for n,(start,end,breach) in enumerate(ww):
            rr=reviews[(reviews>=part.date.iloc[start])&(reviews<=part.date.iloc[end])]
            count+=len(rr);active+=end-start+1
            spans.append(dict(segment_id=row['segment_id'],subwindow=n+1,
                era=row['era'],industry_code=row['industry_code'],
                start=part.date.iloc[start].strftime('%Y-%m-%d'),end=part.date.iloc[end].strftime('%Y-%m-%d'),
                interrupted=breach is not None,reviews=len(rr)))
        after_first=reviews[reviews>=part.date.iloc[ww[0][0]]] if ww else []
        rows.append(dict(segment_id=row['segment_id'],label_status=row['diagnostic_status'],
            era=row['era'],industry_code=row['industry_code'],kind=row['kind'],
            windows=len(ww),review_opportunities=count,active_days=active,total_days=len(part),
            timely_reference_end=after_first[1].strftime('%Y-%m-%d') if len(after_first)>1 else None))
    r=pd.DataFrame(rows);w=pd.DataFrame(spans)
    r.to_parquet(out/'process_window_audit.parquet',index=False);w.to_parquet(out/'windows.parquet',index=False)
    kept=r[r.label_status.eq('RETAINED')]
    summary=dict(scope='Recoverable-window diagnostic only; not final process validation',
        candidates=len(r),retained=len(kept),retained_no_reviews=int(kept.review_opportunities.eq(0).sum()),
        retained_multiple_windows=int(kept.windows.gt(1).sum()),retained_windows=int(kept.windows.sum()),
        window_count_quantiles=kept.windows.quantile([.1,.5,.9,1]).to_dict(),
        reviews_quantiles=kept.review_opportunities.quantile([.1,.5,.9,1]).to_dict())
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    checks=[]
    # An interruption is recorded; subsequent recovery does not erase it.
    ww=windows(np.array([100,101,96,97,99,102.]),np.ones(6)*.01)
    assert ww==[(0,1,2),(3,5,None)];checks.append('interrupt_then_recover')
    assert windows(np.array([100,100,100.]),np.array([np.nan,0,0]))==[];checks.append('no_evidence_no_window')
    assert windows(np.array([100,101,102.]),np.ones(3)*.01)==[(0,2,None)];checks.append('uninterrupted_single_window')
    (out/'checks.json').write_text(json.dumps(checks))
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()

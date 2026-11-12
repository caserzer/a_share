"""Preregistered offline segmentation, strictly evaluation-side only."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha


def fit_segments(y):
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n < 4:
        return []
    dd = np.diff(y, n=2)
    noise = max(.002, np.median(np.abs(dd-np.median(dd))) / (.67448975*np.sqrt(6)))
    penalty = 3*np.log(n)*noise**2
    t = np.arange(n, dtype=float)
    sums = [np.r_[0., np.cumsum(v)] for v in (t, y, t*t, t*y, y*y)]
    cost = np.full(n+1, np.inf); cost[0] = 0
    previous = np.full(n+1, -1, dtype=int)
    slopes, intercepts = {}, {}
    for end in range(4, n+1):
        starts = np.arange(end-3)
        count = end-starts
        st, sy, stt, sty, syy = [a[end]-a[starts] for a in sums]
        denom = stt-st*st/count
        slope = (sty-st*sy/count)/denom
        intercept = (sy-slope*st)/count
        rss = np.maximum(0., syy-sy*sy/count-slope*(sty-st*sy/count))
        choices = cost[starts]+rss+penalty
        k = int(np.argmin(choices)); start = int(starts[k])
        cost[end], previous[end] = choices[k], start
        slopes[end], intercepts[end] = slope[k], intercept[k]
    result, end = [], n
    while end:
        start = int(previous[end])
        result.append(dict(start=start, stop=end, slope=float(slopes[end]),
                           intercept=float(intercepts[end]), noise=float(noise),
                           penalty=float(penalty)))
        end = start
    return list(reversed(result))


def classify(y, segments):
    previous, family, prior_up = None, 0, False
    for s in segments:
        i,j,b = s['start'],s['stop'],s['slope']
        up = b >= .002 and y[j-1] > y[i]
        if up and not prior_up:
            family += 1
        kind = ('NON_RISING' if not up else 'LEFT_UNKNOWN' if previous is None
                else 'WARMING' if previous <= .001
                else 'HEATING' if b-previous >= .002 else 'CONTINUATION')
        s.update(kind=kind, family=family if up else None, previous_slope=previous,
                 up=bool(up))
        previous, prior_up = b, up
    return segments


def synthetic_checks():
    t=np.arange(80)
    paths = {'flat': np.zeros(80),
             'warming': np.r_[-.005*np.arange(40), -.195+.003*np.arange(40)],
             'heating': np.r_[.003*np.arange(40), .117+.009*np.arange(40)],
             'pulse': np.where(t==40,.15,0.),
             'steady_up': .003*t,
             'slowing_decline': np.r_[-.009*np.arange(40),-.351-.002*np.arange(40)]}
    rng=np.random.default_rng(0)
    records=[]
    for name,y in paths.items():
        for perturb in (False,True):
            z=y+(rng.normal(0,.001,len(y)) if perturb else 0)
            ss=classify(z,fit_segments(z))
            kinds=[s['kind'] for s in ss]
            expected = ('WARMING' in kinds if name=='warming' else
                        'HEATING' in kinds if name=='heating' else
                        not any(k in ('WARMING','HEATING') for k in kinds))
            records.append(dict(path=name,perturbed=perturb,kinds=kinds,
                                business_expectation_met=bool(expected),segments=ss))
    return records


def main():
    out=EP/'outputs/r00_v2_label_probe02'
    if out.exists(): raise FileExistsError('Preserve first run')
    out.mkdir()
    source=PRIOR/'daily_industries.parquet'; catalog=EP/'outputs/r01/weekly_catalog.parquet'
    plan=EP/'protocols/r00_v2/label_probe02/plan.md'
    receipt=json.loads((PRIOR/'receipt.json').read_text())
    calendar=Path(next(x for x in receipt['inputs'] if x.endswith('/calendar.parquet')))
    inputs={str(f):sha(f) for f in [source,catalog,plan,calendar,Path(__file__)]}
    (out/'started.json').write_text(json.dumps(inputs,indent=2))
    checks=synthetic_checks()
    (out/'synthetic_checks.json').write_text(json.dumps(checks,indent=2))
    raw=pd.read_parquet(source,columns=['date','day_i','era','industry_code','industry_name','block','nav'])
    cal=pd.read_parquet(calendar);cal['week']=pd.to_datetime(cal.date).dt.to_period('W-SUN').astype(str)
    expected=cal.groupby('week').size().to_dict()
    cat=pd.read_parquet(catalog,columns=['era','industry_code','industry_name']).drop_duplicates(['era','industry_code'])
    records=[];audit=[]
    valid=raw.nav.notna()&raw.nav.gt(0)&raw.block.notna()
    for (era,code,block),g in raw[valid].groupby(['era','industry_code','block']):
        g=g.sort_values('day_i').copy()
        assert np.all(np.diff(g.day_i)==1)
        g['week']=g.date.dt.to_period('W-SUN').astype(str);g['y']=np.log(g.nav)
        w=g.groupby('week',sort=True).agg(y=('y','median'),start=('date','min'),
               end=('date','max'),count=('date','size')).reset_index()
        w['partial']=w['count']!=w.week.map(expected)
        y=w.y.to_numpy(); ss=classify(y,fit_segments(y))
        audit.append(dict(era=era,industry_code=code,block=int(block),weeks=len(w),
                          rows=len(g),partial_weeks=int(w.partial.sum()),segments=len(ss)))
        for k,s in enumerate(ss):
            i,j=s['start'],s['stop'];z=y[i:j]
            days=g[g.date.between(w.start.iloc[i],w.end.iloc[j-1])]
            daily=days.y.to_numpy(); dd=float(np.expm1((daily-np.maximum.accumulate(daily)).min()))
            jump=None if k==0 else float((s['intercept']+s['slope']*i)-
                   (ss[k-1]['intercept']+ss[k-1]['slope']*i))
            records.append(dict(**s,segment_id=f'L02-{len(records)+1:06d}',era=era,
                industry_code=code,industry_name=g.industry_name.iloc[0],block=int(block),
                family_id=f'{era}:{code}:{block}:{s["family"]}' if s['family'] else None,
                start_date=w.start.iloc[i].strftime('%Y-%m-%d'),
                end_date=w.end.iloc[j-1].strftime('%Y-%m-%d'),weeks=j-i,
                partial_weeks=int(w.partial.iloc[i:j].sum()),
                end_boundary=bool(j==len(w)),actual_gain=float(np.expm1(z[-1]-z[0])),
                fitted_gain=float(np.expm1(s['slope']*(j-i-1))),
                max_daily_drawdown=dd,positive_week_fraction=float((np.diff(z)>0).mean()),
                fitted_boundary_jump=jump))
    r=pd.DataFrame(records);b=pd.DataFrame(audit)
    r.to_parquet(out/'segments.parquet',index=False);b.to_parquet(out/'blocks.parquet',index=False)
    candidates=r[r.kind.isin(['WARMING','HEATING'])]
    candidates.to_parquet(out/'candidates.parquet',index=False)
    directory=cat.merge(b.groupby(['era','industry_code']).agg(valid_rows=('rows','sum'),
                    weekly_points=('weeks','sum'),segments=('segments','sum')).reset_index(),how='left')
    directory.to_parquet(out/'directory.parquet',index=False)
    r.assign(year=r.start_date.str[:4]).groupby(['era','year','kind']).size().rename('count').reset_index().to_csv(out/'strata.csv',index=False)
    summary=dict(scope='L02 offline label feasibility; not final labels or method results',
        directory=len(cat),no_valid_price=int(directory.valid_rows.isna().sum()),
        valid_rows=int(valid.sum()),invalid_rows=int((~valid).sum()),blocks=len(b),
        short_blocks=int(b.weeks.lt(4).sum()),short_block_rows=int(b.loc[b.weeks.lt(4),'rows'].sum()),
        segments=len(r),kind=r.kind.value_counts().to_dict(),candidates=len(candidates),
        partial_candidates=int(candidates.partial_weeks.gt(0).sum()),
        terminal_candidates=int(candidates.end_boundary.sum()),
        candidate_families=int(candidates.family_id.nunique()),
        actual_gain_quantiles=candidates.actual_gain.quantile([.1,.5,.9]).to_dict(),
        drawdown_quantiles=candidates.max_daily_drawdown.quantile([.1,.5,.9]).to_dict(),
        duration_quantiles=candidates.weeks.quantile([.1,.5,.9]).to_dict(),
        positive_week_fraction_quantiles=candidates.positive_week_fraction.quantile([.1,.5,.9]).to_dict(),
        synthetic_checks_met=sum(c['business_expectation_met'] for c in checks),synthetic_checks_total=len(checks))
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

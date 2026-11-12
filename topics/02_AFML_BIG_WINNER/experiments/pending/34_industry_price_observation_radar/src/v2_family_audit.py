"""Event-independent audit of whether fitted families are business identities."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha
from v2_label_probe02_persistence import retained


def main():
    out = EP/'outputs/r00_v2_family_audit'
    if out.exists():
        raise FileExistsError('Preserve first audit')
    paths = [EP/'outputs/r00_v2_label_probe02/segments.parquet',
             PRIOR/'daily_industries.parquet',
             EP/'protocols/r00_v2/family_audit/plan.md',
             EP/'src/v2_label_probe02_persistence.py', Path(__file__)]
    hashes = {str(p):sha(p) for p in paths}
    st = pd.read_parquet(paths[0]).sort_values(['era','industry_code','block','start_date'])
    keys = ['era','industry_code','block']
    st['previous_kind'] = st.groupby(keys).kind.shift()
    st['previous_segment'] = st.groupby(keys).segment_id.shift()
    raw = pd.read_parquet(paths[1], columns=keys+['date','day_i','nav'])
    raw = raw[raw.nav.gt(0)&raw.block.notna()].copy()
    raw['week'] = raw.date.dt.to_period('W-SUN')
    groups = {k:g.sort_values('day_i') for k,g in raw.groupby(keys)}
    rows=[]; orphans=[]
    for fid, stages in st[st.family_id.notna()].groupby('family_id', sort=True):
        stages=stages.sort_values('start_date'); first=stages.iloc[0]; last=stages.iloc[-1]
        g=groups[tuple(first[k] for k in keys)]
        g=g[g.date.between(first.start_date,last.end_date)].copy()
        assert np.all(np.diff(g.day_i)==1)
        z=np.log(g.nav.to_numpy()); baseline=z[0]; below=z<baseline
        # An initial starting observation is not a return below the base.
        entries=below & ~np.r_[False,below[:-1]]
        w=g.groupby('week').nav.apply(lambda x: np.median(np.log(x))).to_numpy()
        part=[]
        for r in stages.itertuples():
            p=g[g.date.between(r.start_date,r.end_date)]
            v=p.groupby('week').nav.apply(lambda x:np.median(np.log(x))).to_numpy()
            part.append(retained(v))
        row=dict(family_id=fid, era=first.era, industry_code=first.industry_code,
                 industry_name=first.industry_name,block=int(first.block),
                 start=first.start_date,end=last.end_date,stages=len(stages),
                 segment_ids='|'.join(stages.segment_id),kinds='|'.join(stages.kind),
                 first_kind=first.kind,previous_kind=first.previous_kind,
                 previous_slope=None if pd.isna(first.previous_slope) else float(first.previous_slope),
                 left_unknown=first.kind=='LEFT_UNKNOWN',partial_weeks=int(stages.partial_weeks.sum()),
                 right_boundary=bool(last.end_boundary),days=len(g),weeks=len(w),
                 whole_retained=retained(w),any_stage_retained=any(part),all_stages_retained=all(part),
                 stage_retained_count=sum(part),below_start_days=int(below.sum()),
                 below_start_entries=int(entries.sum()),
                 max_daily_drawdown=float(np.expm1((z-np.maximum.accumulate(z)).min())),
                 final_gain=float(np.expm1(z[-1]-z[0])))
        rows.append(row)
        # A continuation at the start of an up family has no prior up family member.
        if first.kind=='CONTINUATION':
            orphans.append(dict(**row,previous_segment=first.previous_segment))
    f=pd.DataFrame(rows);o=pd.DataFrame(orphans)
    multi=f[f.stages.gt(1)]
    result=dict(scope='Event-independent identity diagnostic, not replacement labels or method evaluation',
                families=len(f),stages=int(f.stages.sum()),multiple_stage_families=len(multi),
                first_kind=f.first_kind.value_counts().to_dict(),orphan_first_continuation=len(o),
                orphan_previous_kind=o.previous_kind.value_counts(dropna=False).to_dict(),
                left_unknown=int(f.left_unknown.sum()),partial_family=int(f.partial_weeks.gt(0).sum()),
                right_boundary=int(f.right_boundary.sum()),
                multi_whole_retained=int(multi.whole_retained.sum()),
                multi_whole_fails_any_stage_passes=int((~multi.whole_retained & multi.any_stage_retained).sum()),
                multi_whole_passes_some_stage_fails=int((multi.whole_retained & ~multi.all_stages_retained).sum()),
                multi_below_start=int(multi.below_start_days.gt(0).sum()),
                multi_drawdown_quantiles=multi.max_daily_drawdown.quantile([.1,.5,.9]).to_dict(),
                multi_days_quantiles=multi.days.quantile([.1,.5,.9]).to_dict())
    assert len(f)==st.family_id.nunique()
    assert int(f.stages.sum())==int(st.family_id.notna().sum())
    assert o.previous_kind.eq('NON_RISING').all()
    out.mkdir()
    f.to_parquet(out/'all_families.parquet',index=False)
    o.to_csv(out/'orphan_continuations.csv',index=False)
    f.assign(year=f.start.str[:4]).groupby(['era','year']).agg(
        families=('family_id','size'),stages=('stages','sum'),
        left_unknown=('left_unknown','sum'),right_boundary=('right_boundary','sum'),
        whole_retained=('whole_retained','sum')).to_csv(out/'annual.csv')
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=hashes,
        checks=['all up stages accounted for once','all families accounted for','daily paths contiguous',
                'all orphan continuations preceded by NON_RISING'],
        artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

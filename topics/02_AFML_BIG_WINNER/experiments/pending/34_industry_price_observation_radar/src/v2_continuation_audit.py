"""Audit whether a fitted boundary wrongly terminates a business process."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/ep34-mpl-cache')
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from audit_local_inputs import EP,PRIOR,sha
from v2_window_recovery import windows


def main():
    out=EP/'outputs/r00_v2_continuation_audit'
    if out.exists():raise FileExistsError('Preserve audit')
    out.mkdir()
    paths=[EP/'outputs/r00_v2_label_probe02/segments.parquet',
           EP/'outputs/r00_v2_label_probe02/persistence/candidate_diagnostic.parquet',
           EP/'outputs/v2_b01/events.parquet',EP/'outputs/v2_b01/evaluation/event_quality.parquet',
           EP/'outputs/v2_b01/evaluation/process_coverage.parquet',PRIOR/'daily_industries.parquet',
           EP/'protocols/r00_v2/continuation_audit/plan.md',EP/'src/v2_window_recovery.py',Path(__file__)]
    inputs={str(f):sha(f) for f in paths}
    st=pd.read_parquet(paths[0]);cand=pd.read_parquet(paths[1]).set_index('segment_id')
    ev=pd.read_parquet(paths[2]);quality=pd.read_parquet(paths[3]);coverage=pd.read_parquet(paths[4]).set_index('process')
    raw=pd.read_parquet(paths[5],columns=['date','day_i','era','industry_code','industry_name','block','nav'])
    groups={k:g.sort_values('day_i').reset_index(drop=True) for k,g in raw[raw.nav.notna()&raw.nav.gt(0)&raw.block.notna()].groupby(['era','industry_code','block'])}
    mapping=[];last_end={}
    for key,g in st.groupby(['era','industry_code','block']):
        parent=None;family=None
        for r in g.sort_values('start_date').itertuples():
            if r.family_id!=family:parent=None
            family=r.family_id
            if r.kind in ('WARMING','HEATING'):parent=r.segment_id;last_end[parent]=r.end_date
            if r.kind=='CONTINUATION':
                status=('NO_ACTIONABLE_PREDECESSOR' if parent is None else
                        'QUALIFIED_PREDECESSOR' if parent in coverage.index else 'UNQUALIFIED_OR_UNKNOWN_PREDECESSOR')
                mapping.append(dict(segment=r.segment_id,parent=parent,status=status,era=r.era,industry_code=r.industry_code,
                    block=r.block,start=r.start_date,end=r.end_date,partial=r.partial_weeks>0,terminal=r.end_boundary))
                if parent is not None:last_end[parent]=r.end_date
    mp=pd.DataFrame(mapping);mp.to_parquet(out/'all_continuations.parquet',index=False)
    stidx=st.set_index('segment_id');lookup=mp.set_index('segment').to_dict('index');cache={};records=[]
    q=quality[quality.kind.eq('NEW')&quality.process.isin(lookup)].merge(ev,on='event_id',suffixes=('_quality','_event'),validate='one_to_one')
    for r in q.to_dict('records'):
        m=lookup[r['process']];pid=m['parent'];date=pd.Timestamp(r['date_event']);active=False;prior=False;positive=False
        if pid is not None and pid in coverage.index:
            parent=stidx.loc[pid];key=(parent.era,parent.industry_code,parent.block)
            if pid not in cache:
                g=groups[key].copy();g['r5']=g.nav/g.nav.shift(5)-1
                part=g[g.date.between(parent.start_date,last_end[pid])].reset_index(drop=True)
                cache[pid]=[(part.date.iloc[a],part.date.iloc[b]) for a,b,_ in windows(part.nav.to_numpy(),part.r5.to_numpy())]
            active=any(a<=date<=b for a,b in cache[pid]);cov=coverage.loc[pid]
            prior=bool(cov.covered and pd.Timestamp(cov.first_date)<date)
            positive=bool(r['positive_evidence'] and (parent.kind!='HEATING' or r['enhancement_evidence']))
        status=(m['status'] if pid is None or pid not in coverage.index else
                'CONTINUATION_BOUNDARY_UNKNOWN' if m['partial'] or m['terminal'] else
                'NO_CORRESPONDING_PRICE_EVIDENCE' if not positive else
                'OUTSIDE_ACTIVE_WINDOW' if not active else
                'ALREADY_COVERED_PREDECESSOR' if prior else 'POTENTIAL_LATE_FIRST_COVERAGE')
        records.append(dict(event_id=r['event_id'],date=date.strftime('%Y-%m-%d'),era=m['era'],industry_code=m['industry_code'],
            segment=r['process'],parent=pid,original_status=r['status'],audit_status=status,
            prior_covered=prior,active=active,evidence=positive))
    events=pd.DataFrame(records);events.to_parquet(out/'all_continuation_new_events.parquet',index=False)
    selected=events.sort_values(['date','event_id']).groupby(['era','audit_status'],sort=True).head(1).sort_values(['era','audit_status'])
    selected.to_csv(out/'selected_cases.csv',index=False)
    font='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc';font_manager.fontManager.addfont(font)
    plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();plt.rcParams['axes.unicode_minus']=False
    for era,cases in selected.groupby('era'):
        fig,axes=plt.subplots(len(cases),1,figsize=(13,3.2*len(cases)),squeeze=False)
        for ax,r in zip(axes.flat,cases.itertuples()):
            seg=stidx.loc[r.segment];parent=stidx.loc[r.parent] if r.parent is not None else seg
            g=groups[(seg.era,seg.industry_code,seg.block)]
            lo=pd.Timestamp(parent.start_date)-pd.Timedelta(days=35);hi=pd.Timestamp(seg.end_date)+pd.Timedelta(days=20)
            v=g[g.date.between(lo,hi)];ax.plot(v.date,v.nav/v.nav.iloc[0]*100,color='#333')
            ax.axvspan(pd.Timestamp(parent.start_date),pd.Timestamp(parent.end_date),alpha=.15,color='#4477aa',label='前驱阶段')
            ax.axvspan(pd.Timestamp(seg.start_date),pd.Timestamp(seg.end_date),alpha=.15,color='#33aa66',label='延续阶段')
            ax.axvline(pd.Timestamp(r.date),color='#cc3344',label='NEW提示')
            ax.set_title(f'{r.event_id} {g.industry_name.iloc[0]} {r.date}\n{r.audit_status}');ax.legend(loc='best');ax.grid(alpha=.2)
        fig.tight_layout();fig.savefig(out/f'cases_{era}.png',dpi=110);plt.close(fig)
    summary=dict(scope='Semantic audit only; no replacement performance metrics',continuations=len(mp),
        predecessor_status=mp.status.value_counts().to_dict(),new_events=len(events),original_status=events.original_status.value_counts().to_dict(),
        audit_status=events.audit_status.value_counts().to_dict(),potential_parent_processes=int(events.loc[events.audit_status.eq('POTENTIAL_LATE_FIRST_COVERAGE'),'parent'].nunique()),
        selected_cases=len(selected))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2));print(selected.to_string(index=False))


if __name__=='__main__':main()

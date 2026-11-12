"""Full-catalog offline v0.2 semantic proposal. No signal evaluation."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, sha
from process_identity_v02 import candidate_metrics, segment


def main():
    source=EP/'outputs/r00_coverage/evaluation_coverage.parquet'
    q=pd.read_parquet(source).sort_values(['era','industry_code','date']).reset_index(drop=True)
    support=q[['era','industry_code','date','status']].copy()
    support['support']='MISSING_PRICE'
    support.loc[q.no_price_identity,'support']='NO_PRICE_IDENTITY'
    metrics,phases,assignments=[],[],[]
    for (era,code,block),g in q[q.nav.notna()].groupby(['era','industry_code','block'],sort=True):
        g=g.sort_values('date'); assert np.all(np.diff(g.day_i)==1)
        original=g.index.to_numpy(); g=g.reset_index(drop=True)
        last=g.date.iloc[-1]
        reason='CLASSIFICATION_BOUNDARY' if era=='SW2014' and last==pd.Timestamp('2021-11-30') else ('RIGHT_CENSORED' if last==q.date.max() else 'INTERNAL_PRICE_BREAK')
        support.loc[original,'support']='EVALUABLE'
        support.loc[original[:60],'support']='LEFT_BLOCK_WINDOW'
        support.loc[original[max(0,len(g)-60):],'support']='TAIL_'+reason
        if len(g)<121: support.loc[original,'support']='SHORT_BLOCK_BOTH_BOUNDARIES'
        m=candidate_metrics(g.nav.to_numpy())
        if m.empty: continue
        assert len(m)==max(0,len(g)-120)
        m['era'],m['industry_code'],m['block']=era,code,int(block)
        m['date']=g.date.iloc[m.position].to_numpy()
        m['day_i']=g.day_i.iloc[m.position].to_numpy()
        proxy=(g.stale_members.gt(0)|g.boundary_proxy.eq(True)).to_numpy()
        m['proxy_in_121']=[bool(proxy[i-60:i+61].any()) for i in m.position]
        p,a=segment(g.nav.to_numpy(),m,reason)
        prefix=f'v0.2|{era}|{code}|{int(block)}'
        if not p.empty:
            p['era'],p['industry_code'],p['block']=era,code,int(block)
            p['process_id']=[prefix+'|phase|'+str(i) for i in p.phase]
            p['parent_id']=[prefix+'|parent|'+str(i) for i in p.parent]
            p['start_date']=g.date.iloc[p.start].to_numpy();p['end_date']=g.date.iloc[p.end].to_numpy()
            p['start_day_i']=g.day_i.iloc[p.start].to_numpy();p['end_day_i']=g.day_i.iloc[p.end].to_numpy()
            p['duration']=p.end-p.start
            p['proxy_in_evaluation']=[bool(proxy[i-60:i+61].any()) for i in p.start]
            # Start is the earliest supported candidate, not proof the true process was not left-censored.
            p['start_at_first_evaluable_day']=p.start.eq(60)
            mapping=p.set_index('phase').process_id
            a['process_id']=a.phase.map(mapping)
            a['era'],a['industry_code'],a['block']=era,code,int(block)
            a['date']=g.date.iloc[a.position].to_numpy()
            assert len(a)==int(m.valid.sum())
            phases.append(p);assignments.append(a)
        metrics.append(m)
    m=pd.concat(metrics,ignore_index=True);p=pd.concat(phases,ignore_index=True);a=pd.concat(assignments,ignore_index=True)
    assert support.support.eq('EVALUABLE').sum()==len(m)
    assert len(a)==m.valid.sum()
    assert p.process_id.is_unique and not m.duplicated(['era','industry_code','date']).any()
    for _,g in p.groupby(['era','industry_code','block']):
        g=g.sort_values('start'); assert (g.start.iloc[1:].to_numpy()>g.end.iloc[:-1].to_numpy()).all()
    out=EP/'outputs/r00_process_draft_v02';out.mkdir(parents=True,exist_ok=True)
    for name,frame in [('date_support',support),('candidate_metrics',m),('processes',p),('candidate_assignments',a)]: frame.to_parquet(out/f'{name}.parquet',index=False)
    inputs=[source,Path(__file__),EP/'src/process_identity_v02.py',EP/'rounds/R00_process_identity_v02.md',EP/'rounds/R00_process_definition_draft.md']
    result=dict(status='DRAFT_IDENTITY_NOT_FROZEN',inputs={str(f):sha(f) for f in inputs},
                support=support.support.value_counts().to_dict(),candidate_days=int(m.valid.sum()),
                phases=len(p),parents=int(p.parent_id.nunique()),kinds=p.kind.value_counts().to_dict(),
                ends=p.end_reason.value_counts().to_dict(),censored_phases=int(p.right_censored.sum()),
                first_evaluable_start=int(p.start_at_first_evaluable_day.sum()),
                assignment=a.disposition.value_counts().to_dict(),duration=p.duration.describe(percentiles=[.5,.9,.95,.99]).to_dict(),
                annual=[dict(era=era,year=int(year),kind=kind,phases=len(g),parents=int(g.parent_id.nunique())) for (era,year,kind),g in p.groupby(['era',p.start_date.dt.year,'kind'])],
                artifacts={f.name:sha(f) for f in sorted(out.glob('*.parquet'))})
    (out/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['support','candidate_days','phases','parents','kinds','ends','first_evaluable_start']},ensure_ascii=False))


if __name__=='__main__':main()

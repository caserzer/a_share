import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha
from price_process_v03 import price_processes
from endpoint_contract import assess


def main():
    candidatefile=EP/'outputs/r00_process_draft_v02/candidate_metrics.parquet'
    source=PRIOR/'daily_industries.parquet'
    m=pd.read_parquet(candidatefile);d=pd.read_parquet(source)
    candidates={k:g for k,g in m.groupby(['era','industry_code','block'])}
    processes=[];assignments=[];checks=0
    for (era,code,block),g in d[d.nav.notna()].groupby(['era','industry_code','block'],sort=True):
        g=g.sort_values('date').reset_index(drop=True)
        assert np.all(np.diff(g.day_i)==1)
        c=candidates.get((era,code,block))
        if c is None or not c.valid.any():continue
        end_reason='CLASSIFICATION_BOUNDARY' if era=='SW2014' and g.date.iloc[-1]==pd.Timestamp('2021-11-30') else ('RIGHT_CENSORED' if g.date.iloc[-1]==d.date.max() else 'INTERNAL_PRICE_BREAK')
        p,a=price_processes(g.nav.to_numpy(),c,end_reason)
        prefix=f'v0.3|{era}|{code}|{int(block)}'
        p['process_id']=[prefix+'|process|'+str(i) for i in p.process]
        p['family_id']=[prefix+'|family|'+str(i) for i in p.family]
        mapping=p.set_index('process').process_id
        p['predecessor_id']=p.predecessor.map(mapping)
        p['era'],p['industry_code'],p['block']=era,code,int(block)
        for name,col in [('start_date','start'),('end_date','end'),('evidence_end_date','evidence_end')]:
            p[name]=g.date.iloc[p[col].astype(int)].to_numpy()
        p['start_day_i']=g.day_i.iloc[p.start].to_numpy();p['end_day_i']=g.day_i.iloc[p.end].to_numpy()
        p['left_origin_uncertain']=p.start.eq(60)
        p['duration']=p.end-p.start
        for r in p.itertuples():
            outcome=assess(g.nav.iloc[r.start:].to_numpy(),int(r.end-r.start),r.end_reason,r.left_origin_uncertain)
            assert outcome['status']=='WITHIN_PHASE_CONFIRMED'
            # Independently scan the original price block for the first breach.
            base=float(g.nav.iloc[r.start]);peak=base;expected=None
            for i in range(int(r.start)+1,len(g)):
                v=float(g.nav.iloc[i]);peak=max(peak,v)
                if v/base-1<-.05 or v/peak-1<-.12:
                    expected=i;break
            if expected is None:assert r.right_censored and r.end==len(g)-1
            else:assert not r.right_censored and r.end==expected-1
            checks+=1
        a['process_id']=a.process.map(mapping)
        a['era'],a['industry_code'],a['block']=era,code,int(block)
        a['date']=g.date.iloc[a.position].to_numpy()
        assert len(a)==int(c.valid.sum())
        processes.append(p);assignments.append(a)
    p=pd.concat(processes,ignore_index=True);a=pd.concat(assignments,ignore_index=True)
    assert p.process_id.is_unique and len(a)==int(m.valid.sum())
    assert (p.evidence_end<=p.end).all()
    out=EP/'outputs/r00_price_process_v03';out.mkdir(exist_ok=True)
    p.to_parquet(out/'processes.parquet',index=False);a.to_parquet(out/'candidate_assignments.parquet',index=False)
    result=dict(status='STRUCTURAL_INVARIANTS_PASS_REAL_CASE_REVIEW_PENDING',processes=len(p),
                families=int(p.family_id.nunique()),kinds=p.kind.value_counts().to_dict(),
                ends=p.end_reason.value_counts().to_dict(),left_origin_uncertain=int(p.left_origin_uncertain.sum()),
                candidate_days=len(a),independent_endpoint_checks=checks,evidence_beyond_endpoint=0,
                duration=p.duration.describe(percentiles=[.5,.9,.95,.99]).to_dict(),
                assignment=a.disposition.value_counts().to_dict(),
                annual=[dict(era=era,year=int(year),kind=kind,count=len(g)) for (era,year,kind),g in p.groupby(['era',p.start_date.dt.year,'kind'])],
                inputs={str(f):sha(f) for f in [candidatefile,source,Path(__file__),EP/'src/price_process_v03.py',EP/'rounds/R00_price_process_v03.md']},
                artifacts={f.name:sha(f) for f in sorted(out.glob('*.parquet'))})
    (out/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['processes','families','kinds','ends','left_origin_uncertain','candidate_days','duration']},ensure_ascii=False))


if __name__=='__main__':main()

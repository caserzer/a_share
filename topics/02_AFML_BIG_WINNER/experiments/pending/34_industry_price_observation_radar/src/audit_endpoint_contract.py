import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha
from endpoint_contract import assess


def main():
    source=EP/'outputs/r00_process_draft_v02/processes.parquet'
    raw=PRIOR/'daily_industries.parquet'
    p=pd.read_parquet(source);d=pd.read_parquet(raw)
    groups={k:g.sort_values('date').reset_index(drop=True) for k,g in d[d.nav.notna()].groupby(['era','industry_code','block'])}
    rows=[];checks=0
    for r in p.itertuples():
        g=groups[(r.era,r.industry_code,r.block)]
        prices=g.nav.iloc[int(r.start):].to_numpy(copy=True)
        endpoint=int(r.end-r.start)
        result=assess(prices,endpoint,r.end_reason,r.start_at_first_evaluable_day)
        for value in [1e-9,1e12]:
            # Include an artificial continuation even if the physical block ends here.
            altered=np.r_[prices,np.repeat(value,100)]
            altered[result['evidence_end']+1:]=value
            assert assess(altered,endpoint,r.end_reason,r.start_at_first_evaluable_day)==result
            checks+=1
        rows.append(dict(process_id=r.process_id,parent_id=r.parent_id,era=r.era,industry_code=r.industry_code,
                         start_date=r.start_date,end_date=r.end_date,kind=r.kind,end_reason=r.end_reason,
                         **result))
    f=pd.DataFrame(rows);assert len(f)==len(p) and f.process_id.is_unique
    out=EP/'outputs/r00_endpoint_contract';out.mkdir(exist_ok=True)
    f.to_parquet(out/'all_phase_outcomes.parquet',index=False)
    sources=[source,raw,EP/'rounds/R00_endpoint_contract.md',EP/'src/endpoint_contract.py',Path(__file__)]
    result=dict(status='EVIDENCE_OWNERSHIP_CHECKED_IDENTITY_STILL_UNRESOLVED',
                phases=len(f),outcomes=f.status.value_counts().to_dict(),suffix_mutations_checked=checks,
                left_origin_cross_tab=f.groupby(['status','left_origin_uncertain']).size().reset_index(name='count').to_dict('records'),
                inputs={str(x):sha(x) for x in sources},output_sha256=sha(out/'all_phase_outcomes.parquet'))
    (out/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['phases','outcomes','suffix_mutations_checked','left_origin_cross_tab']},ensure_ascii=False))


if __name__=='__main__':main()

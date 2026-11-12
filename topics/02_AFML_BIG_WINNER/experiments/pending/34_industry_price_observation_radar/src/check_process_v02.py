"""Independent all-parent stopping audit and unchanged-path-condition reconciliation."""
import json
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha


def main():
    out=EP/'outputs/r00_process_draft_v02'
    m=pd.read_parquet(out/'candidate_metrics.parquet')
    p=pd.read_parquet(out/'processes.parquet')
    old=pd.read_parquet(EP/'outputs/r00_process_draft_v01/anchors.parquet')
    joined=old.merge(m,on=['era','industry_code','date'],suffixes=('_old','_new'),validate='one_to_one')
    assert len(joined)==len(old)
    fields=['pre60','pre20','gain20','gain60','gain20_max','retained_days','worst_from_start','max_drawdown']
    for col in fields: assert np.allclose(joined[col+'_old'],joined[col+'_new'],atol=1e-12)
    assert joined.kind_old.eq(joined.kind_new).all()
    assert joined.status.eq('VALID_CANDIDATE').eq(joined.valid).all()
    d=pd.read_parquet(PRIOR/'daily_industries.parquet')
    groups={k:g.sort_values('date').reset_index(drop=True) for k,g in d[d.nav.notna()].groupby(['era','industry_code','block'])}
    parents=0;splits=0
    for _,f in p.groupby('parent_id'):
        f=f.sort_values('start');first=f.iloc[0];last=f.iloc[-1]
        raw=groups[(first.era,first.industry_code,first.block)]
        peak=float(raw.nav.iloc[first.start]);high=int(first.start);stop=None
        for i in range(int(first.start)+1,len(raw)):
            price=float(raw.nav.iloc[i])
            if price>peak: peak=price;high=i
            reason='DRAWDOWN8' if price/peak-1<=-.08 else ('PAUSE20' if i-high>=20 else None)
            if reason: stop=(i,reason);break
        if stop is None:
            assert last.end==len(raw)-1 and last.right_censored
        else:
            assert (last.end,last.end_reason)==stop and not last.right_censored
        for previous,current in zip(f.iloc[:-1].itertuples(),f.iloc[1:].itertuples()):
            assert current.kind=='HEATING' and current.start-previous.start>=20
            assert current.reference_gain20-previous.reference_gain20>=.03
            assert previous.end==current.start-1 and previous.end_reason=='NEW_HEATING_PHASE'
            splits+=1
        parents+=1
    # Every reported phase starts on a qualifying date; not a renamed arbitrary interval.
    check=p.merge(
        m[['era','industry_code','date','valid','kind']],left_on=['era','industry_code','start_date'],
        right_on=['era','industry_code','date'],validate='one_to_one',suffixes=('_phase','_candidate'))
    assert len(check)==len(p) and check.valid.all() and check.kind_phase.eq(check.kind_candidate).all()
    result=dict(status='PASS_ARITHMETIC_AND_IDENTITY_NOT_SEMANTIC_ACCEPTANCE',unchanged_v01_anchors=len(joined),
                parents_checked=parents,phase_splits_checked=splits,qualifying_phase_starts=len(check),
                inputs={f.name:sha(f) for f in [out/'candidate_metrics.parquet',out/'processes.parquet']})
    (out/'independent_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()

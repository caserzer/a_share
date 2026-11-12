"""Local five-day participation, independent of signals and labels."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha
from member_breadth_math import member_arrays,breadth_counts


def main():
    out=EP/'outputs/v2_b04_features'
    if out.exists():raise FileExistsError('Preserve features')
    out.mkdir()
    receiptfile=PRIOR/'receipt.json';receipt=json.loads(receiptfile.read_text())
    afile=CACHE/'extension_v2/products/assignments.parquet'
    calendarfile=Path(next(x for x in receipt['inputs'] if x.endswith('/calendar.parquet')))
    catfile=EP/'outputs/r01/weekly_catalog.parquet';plan=EP/'protocols/v2_b04/plan.md'
    inputs={str(f):sha(f) for f in [receiptfile,afile,calendarfile,catfile,plan,EP/'src/member_breadth_math.py',Path(__file__)]}
    assert sha(afile)==receipt['inputs'][str(afile)]
    assert sha(calendarfile)==receipt['inputs'][str(calendarfile)]
    (out/'started.json').write_text(json.dumps(inputs,indent=2))
    a=pd.read_parquet(afile,columns=['month','date','security_id','industry_code','unresolved','level','era']);a=a[a.level.eq('L3')]
    cal=pd.DatetimeIndex(pd.read_parquet(calendarfile).date).sort_values()
    ids=sorted(a.security_id.unique());idmap={s:i for i,s in enumerate(ids)};paths={Path(f).stem:Path(f) for f in receipt['price_reads']}
    valid=np.zeros((len(cal),len(ids)),bool);up=np.zeros_like(valid);checks=0
    for i,sid in enumerate(ids):
        file=paths[sid];assert sha(file)==receipt['price_reads'][str(file)]
        raw=pd.read_parquet(file,columns=['date','qfq_close','close_conflict','factor_chain_id'])
        valid[:,i],up[:,i]=member_arrays(raw,cal,5)
        if i%500==0:
            for end in (1000,1800):
                vv,uu=member_arrays(raw[raw.date<=cal[end-1]],cal[:end],5)
                assert np.array_equal(vv,valid[:end,i]) and np.array_equal(uu,up[:end,i]);checks+=1
        if (i+1)%1000==0:print(f'Price partitions verified {i+1}/{len(ids)}',flush=True)
    cohorts={(era,str(month),code):(np.array([idmap[s] for s in g.security_id]),int(g.unresolved.max()),g.date.max()) for (era,month,code),g in a.groupby(['era','month','industry_code'])}
    c=pd.read_parquet(catfile,columns=['date','era','industry_code']);c.date=pd.to_datetime(c.date);rows=[]
    for r in c.itertuples():
        cohort=cohorts.get((r.era,str(r.date.to_period('M')-1),r.industry_code));z=dict(date=r.date,era=r.era,industry_code=r.industry_code)
        if cohort is None:z.update(supported=False,membership_status='UNKNOWN_PRIOR_MONTH')
        else:
            si,u,anchor=cohort;assert anchor<r.date;day=cal.get_loc(r.date)
            z.update(breadth_counts(len(si)+u,int(valid[day,si].sum()),int(up[day,si].sum()),5,.8));z['membership_status']='HISTORICAL_PROXY'
        rows.append(z)
    f=pd.DataFrame(rows);f.to_parquet(out/'features.parquet',index=False)
    # Independent direct-window verification, not the rolling run-count function.
    samples=f[f.valid_members.notna()].groupby(['era','supported'],group_keys=False).sample(n=5,random_state=3404);member_checks=0
    for r in samples.itertuples():
        members=a[a.era.eq(r.era)&a.industry_code.eq(r.industry_code)&a.month.astype(str).eq(str(r.date.to_period('M')-1))]
        day=cal.get_loc(r.date);ix=cal[max(0,day-5):day+1];n=ups=0
        for sid in members.security_id:
            v=pd.read_parquet(paths[sid],columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date').reindex(ix)
            good=len(v)==6 and v.qfq_close.notna().all() and np.isfinite(v.qfq_close).all() and v.qfq_close.gt(0).all() and v.close_conflict.eq(False).all() and v.factor_chain_id.notna().all() and v.factor_chain_id.nunique()==1
            n+=int(good);ups+=int(good and v.qfq_close.iloc[-1]>v.qfq_close.iloc[0]);member_checks+=1
        assert n==r.valid_members and ups==r.up_members
    summary=dict(scope='Five-day local participation only; historical proxy',rows=len(f),supported=int(f.supported.sum()),unsupported=int((~f.supported).sum()),
                 missing_membership=int(f.membership_status.eq('UNKNOWN_PRIOR_MONTH').sum()),price_partitions=len(ids),prefix_checks=checks,direct_industry_weeks=len(samples),direct_member_windows=member_checks)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()

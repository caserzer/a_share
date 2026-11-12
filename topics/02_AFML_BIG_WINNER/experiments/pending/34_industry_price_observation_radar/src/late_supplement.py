"""Supplementary late attribution; immutable primary ownership takes precedence."""
import numpy as np


def neighborhood_known(days,prices,blocks,day,asof):
    if asof-day<65:return False
    days=np.asarray(days);take=(days>=day-120)&(days<=day+65)
    v=np.asarray(prices,float)[take];b=np.asarray(blocks,float)[take]
    return bool(np.array_equal(days[take],np.arange(day-120,day+66)) and len(v)>0
                and np.isfinite(v).all() and (v>0).all() and np.isfinite(b).all() and (b==b[0]).all())


def match_late(processes,alerts,primary_claims):
    processes=list(processes);alerts=list(alerts);claimed=dict(primary_claims)
    ids={p.process_id for p in processes}
    if len(ids)!=len(processes) or not set(claimed)<=ids:raise ValueError('invalid process registry or primary claim')
    new=[a for a in alerts if a.is_new]
    if len({a.alert_id for a in new})!=len(new):raise ValueError('duplicate new alert')
    if set(a.alert_id for a in new)&set(claimed.values()):raise ValueError('primary alert cannot be reassigned')
    records=[]
    for a in sorted(alerts,key=lambda a:(a.day,a.alert_id,not a.is_new)):
        r=dict(alert_id=a.alert_id,day=a.day,process_id=None,late_credit=False,denominator=False)
        if not a.is_new:r['outcome']='UPDATE';records.append(r);continue
        candidates=[p for p in processes if p.identity==a.identity and 11<=a.day-p.origin<=60]
        p=min(candidates,key=lambda p:(abs(a.day-p.origin),p.origin,p.process_id)) if candidates else None
        known=a.label_coverage_known and a.post_valid is not None
        if p is None:r['outcome']='UNMATCHED_FAILURE' if known else 'UNKNOWN'
        else:
            r['process_id']=p.process_id;known=known and p.known and not p.left_origin_uncertain
            if p.process_id in claimed:
                r['first_alert_id']=claimed[p.process_id]
                r['outcome']='DUPLICATE' if known else 'UNKNOWN_DUPLICATE'
            else:
                claimed[p.process_id]=a.alert_id
                r['late_credit']=bool(known and a.post_valid)
                r['outcome']='SUCCESS' if r['late_credit'] else 'FIRST_FAILURE' if known else 'UNKNOWN'
        r['denominator']=bool(known)
        if a.evaluation_status=='IMMATURE':
            r['outcome']='IMMATURE_DUPLICATE' if 'DUPLICATE' in r['outcome'] else 'IMMATURE';r['denominator']=False;r['late_credit']=False
        records.append(r)
    credited=[r['process_id'] for r in records if r['late_credit']]
    assert len(credited)==len(set(credited)) and not set(credited)&set(primary_claims)
    return records

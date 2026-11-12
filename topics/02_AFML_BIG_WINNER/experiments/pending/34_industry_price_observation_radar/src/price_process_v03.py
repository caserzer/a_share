"""Future-defined price processes with independent, non-truncating evidence."""
import numpy as np
import pandas as pd


def price_processes(prices, candidates, boundary_reason='RIGHT_CENSORED'):
    p=np.asarray(prices,dtype=float)
    if not np.isfinite(p).all() or not (p>0).all():
        raise ValueError('complete positive price block required')
    proposals={int(r.position):r for r in candidates.itertuples() if r.valid}
    records=[];assignments=[];active=[];family=-1
    for i,price in enumerate(p):
        remaining=[]
        for obj in active:
            obj['peak']=max(obj['peak'],price)
            reason='ORIGIN_FLOOR_BREACH' if price/obj['base']-1 < -.05 else ('DRAWDOWN_BREACH' if price/obj['peak']-1 < -.12 else None)
            if reason:
                obj.update(end=i-1,breach_day=i,end_reason=reason,right_censored=False)
                assert obj['end']>=obj['evidence_end'],'candidate evidence contradicts its natural endpoint'
            else:remaining.append(obj)
        active=remaining
        if i not in proposals:continue
        r=proposals[i]
        prior=max(active,key=lambda x:x['start']) if active else None
        new_enhancement=prior is not None and r.kind=='HEATING' and i-prior['start']>=20 and r.gain20-prior['reference_gain20']>=.03
        if prior is None or new_enhancement:
            if prior is None:family+=1
            obj=dict(process=len(records),family=family if prior is None else prior['family'],
                     predecessor=None if prior is None else prior['process'],start=i,evidence_end=i+60,
                     end=None,breach_day=None,end_reason=None,right_censored=None,kind=r.kind,
                     reference_gain20=float(r.gain20),base=float(price),peak=float(price))
            records.append(obj);active.append(obj)
            disposition='NEW_FAMILY' if prior is None else 'NEW_ENHANCEMENT'
        else:
            obj=prior;disposition='SAME_PROCESS'
        assignments.append(dict(position=i,process=obj['process'],disposition=disposition))
    for obj in active:
        obj.update(end=len(p)-1,end_reason=boundary_reason,right_censored=True)
        assert obj['end']>=obj['evidence_end']
    return pd.DataFrame(records),pd.DataFrame(assignments)

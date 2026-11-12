"""No outcomes or future-field access in member validity, bounds, or ranking."""
import numpy as np
import pandas as pd


def member_arrays(frame,calendar,lookback=20):
    allowed={'date','qfq_close','close_conflict','factor_chain_id'}
    if set(frame.columns)!=allowed:raise ValueError('price-only projection required')
    if frame.date.duplicated().any():raise ValueError('duplicate stock date')
    x=frame.set_index('date').reindex(calendar)
    valid=x.qfq_close.notna()&np.isfinite(x.qfq_close)&x.qfq_close.gt(0)&x.close_conflict.eq(False)&x.factor_chain_id.notna()
    reset=~valid|~valid.shift(fill_value=False)|~x.factor_chain_id.eq(x.factor_chain_id.shift())
    idx=np.arange(len(x));last=np.maximum.accumulate(np.where(reset,idx,-1))
    supported=valid.to_numpy() & (idx-last+1>=lookback+1)
    up=supported & x.qfq_close.gt(x.qfq_close.shift(lookback)).to_numpy()
    return supported,up


def breadth_counts(total,valid,up,min_members=5,min_coverage=.8):
    if not 0<=up<=valid<=total or total<=0:raise ValueError('invalid counts')
    supported=valid>=min_members and valid/total>=min_coverage
    return dict(total_members=total,valid_members=valid,up_members=up,unknown_members=total-valid,
                coverage=valid/total,breadth=up/valid if valid else None,
                breadth_lower=up/total,breadth_upper=(up+total-valid)/total,supported=supported)


def score_candidates(frame,weight=.5):
    if frame[['r20','breadth']].isna().any().any():raise ValueError('unknown score input')
    x=frame.copy();x['score_A']=x.r20.rank(method='average',pct=True)
    x['breadth_rank']=x.breadth.rank(method='average',pct=True)
    x['score_B']=(1-weight)*x.score_A+weight*x.breadth_rank
    return x

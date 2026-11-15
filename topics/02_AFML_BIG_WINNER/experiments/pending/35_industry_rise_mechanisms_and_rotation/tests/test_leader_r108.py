import numpy as np
import pandas as pd
import pytest
from leader_feature_r108 import prepare_members,aggregate

def fixture(n=8):
    records=[]
    for month,date,multiple in [('2026-01','2026-01-30',1.),('2026-02','2026-02-27',1.1),('2026-03','2026-03-31',2.)]:
        for i in range(n):records.append(dict(month=pd.Period(month),date=pd.Timestamp(date),security_id=str(i),qfq_close=(i+1)*multiple,close_chain='chain',raw_close=i+1,total_shares=100.,share_effective_date=pd.Timestamp('2025-01-01'),cap=(i+1)*100.,listed=True))
    stocks=pd.DataFrame(records);members=pd.DataFrame([dict(month=pd.Period('2026-01'),era='SW2021',level='L2',industry_code='TEST',security_id=str(i),unresolved=0) for i in range(n)])
    grid=pd.DataFrame([dict(era='SW2021',level='L2',industry_code='TEST',date=pd.Timestamp('2026-02-27'))]);calendar=pd.to_datetime(['2026-01-30','2026-02-27','2026-03-31'])
    return stocks,members,grid,calendar

def test_prior_rank_future_and_current_cap_isolation():
    s,m,g,c=fixture();a=prepare_members(s,m,g,c);ra,rank=aggregate(a)
    s.loc[s.month.gt(pd.Period('2026-01')),'cap']=999999.
    s.loc[s.month.eq(pd.Period('2026-03')),'qfq_close']=.0001
    b=prepare_members(s,m,g,c);rb,rankb=aggregate(b)
    assert ra==rb;pd.testing.assert_series_equal(rank,rankb)
    assert a.loc[rank.le(3),'security_id'].tolist()==['5','6','7']
    assert np.isclose(ra['leader_spread'],0)

def test_unknown_rank_and_chain_coverage():
    s,m,g,c=fixture();s.loc[s.month.eq(pd.Period('2026-01'))&s.security_id.eq('0'),'cap']=np.nan
    a=prepare_members(s,m,g,c);r,rank=aggregate(a);assert r['status']=='incomplete_prior_cap' and rank.isna().all() and pd.isna(r['leader_spread'])
    s,m,g,c=fixture();s.loc[s.month.eq(pd.Period('2026-02'))&s.security_id.eq('7'),'close_chain']='changed'
    r,_=aggregate(prepare_members(s,m,g,c));assert r['status']=='leader_return_missing' and pd.isna(r['leader_spread'])
    s,m,g,c=fixture();s.loc[s.month.eq(pd.Period('2026-02'))&s.security_id.eq('0'),'qfq_close']=np.nan
    r,_=aggregate(prepare_members(s,m,g,c));assert r['status']=='historical_feature_available' and not r['strict_complete'] and r['follower_known']==4

def test_duplicate_and_missing_month():
    s,m,g,c=fixture()
    with pytest.raises(ValueError,match='duplicate stock'):prepare_members(pd.concat([s,s.iloc[:1]]),m,g,c)
    with pytest.raises(ValueError,match='duplicate membership'):prepare_members(s,pd.concat([m,m.iloc[:1]]),g,c)
    s=s[s.month.ne(pd.Period('2026-02'))];a=prepare_members(s,m,g,c)
    assert a.past_return.isna().all() and a.return_status.eq('missing_exact_endpoint').all()

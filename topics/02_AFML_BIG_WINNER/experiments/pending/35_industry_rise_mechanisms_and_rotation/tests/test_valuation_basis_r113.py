import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from valuation_basis_r113 import calculate

def fixture():
    dates=pd.to_datetime(['2026-01-30','2026-02-27','2026-03-31'])
    s=pd.DataFrame(dict(security_id=['s']*3,month=dates.to_period('M'),date=dates,raw_close=[100.,50.,55.],vendor_pe_ttm=[10.,10.,11.],cap=[10000.,10000.,11000.],total_shares=[100.,200.,200.],share_effective_date=pd.to_datetime(['2025-01-01']*3),listed=[True]*3,qfq_close=[50.,50.,55.],close_chain=['c']*3))
    return s,pd.Series(dates,index=dates.to_period('M'))

def test_split_does_not_mean_total_earnings_decline():
    s,c=fixture();p=calculate(s,c);r=p.iloc[1]
    assert np.isclose(r.log_implied_eps,-np.log(2)) and np.isclose(r.log_implied_total,0)
    assert np.isclose(r.log_qfq,0) and np.isclose(r.adjustment_wedge,np.log(2))
    assert r.implied_direction_disagreement and r.shares_changed

def test_distribution_wedge_not_raw_earnings_growth():
    s,c=fixture();s.loc[1,['raw_close','vendor_pe_ttm','total_shares','cap']]=[90.,9.,100.,9000.]
    r=calculate(s,c).iloc[1]
    assert np.isclose(r.log_implied_eps,0) and np.isclose(r.log_implied_total,0)
    assert np.isclose(r.log_qfq,0) and r.adjustment_changed and not r.shares_changed

def test_invalid_pe_chain_missing_month_and_share_clock():
    s,c=fixture();s.loc[1,'close_chain']='break';p=calculate(s,c);assert p.iloc[1].status=='raw_identity_ready' and not p.iloc[1].adjusted_basis_ready
    s,c=fixture();s.loc[1,'vendor_pe_ttm']=-10;p=calculate(s,c);assert p.iloc[1].status=='nonpositive_or_missing_pe' and pd.isna(p.iloc[1].log_raw)
    s,c=fixture();p=calculate(s.drop(index=1),c);assert p.iloc[-1].status=='missing_exact_completed_month'
    s,c=fixture();s.loc[1,'share_effective_date']=pd.Timestamp('2027-01-01');p=calculate(s,c);assert not p.iloc[1].total_basis_ready and p.iloc[1].adjusted_basis_ready

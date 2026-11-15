import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import numpy as np
import pytest
from common import KEY
from evidence_monitor_r21 import assemble,changes


def inputs():
 o=pd.DataFrame(dict(era=['SW2021']*2,level=['L3']*2,industry_code=['a','b'],asof=pd.Timestamp('2026-09-30'),price_ready=[True,False],price_score=[0.,np.nan],price_rank=[1.,np.nan],mom20=[.1,np.nan],mom60=[.2,np.nan],vol20=[.1,np.nan],dd60=[-.05,np.nan],breadth21=[.7,np.nan],breadth63=[.6,np.nan]))
 e=pd.DataFrame(dict(era=['SW2021']*2,level=['L3']*2,industry_code=['a','a'],date=pd.to_datetime(['2026-08-31','2026-10-01']),fiscal_year=2027,known=10,members=10,coverage=1.,eligible=True,full_factor=[.1,.9]))
 v=pd.DataFrame(columns=KEY+['date','pe_rank504','pe_rank504_coverage','pe_positive_fraction','turn_rank504']);v['date']=pd.to_datetime(v['date'])
 m=o[KEY+['asof']].assign(clock='publication_proxy',facts=[2,0],observed_issuers=[1,0],all_member_proxy_sample_fraction=[.1,np.nan],evidence_state=['selected_issuer_facts_only','membership_unknown'])
 return o,e,v,m


def test_future_expectation_excluded_and_older_snapshot_explicit():
 o,e,v,m=inputs();r=assemble(o,e,v,m,'2026-09-30','publication_proxy')
 a=r.iloc[0];b=r.iloc[1]
 assert a.expectation_full_factor==.1 and a.expectation_age_days==30
 assert a.expectation_status=='older_snapshot_not_current'
 assert b.expectation_status=='missing_snapshot' and pd.isna(b.price_rank)
 assert r.economic_stage.eq('not_established').all()
 assert r.dual_crowding_status.eq('unknown_not_inferred_from_turnover').all()
 assert r[['momentum_contribution','volatility_contribution','drawdown_contribution']].iloc[0].sum()==0


def test_changes_preserve_missing_and_reject_clock_mixing():
 o,e,v,m=inputs();a=assemble(o,e,v,m,'2026-09-30','publication_proxy');b=a.copy();b['asof']=pd.Timestamp('2026-10-21');b.loc[0,'price_ready']=False;b.loc[0,'price_rank']=np.nan
 d=changes(a,b)
 assert d.iloc[0].readiness_lost and pd.isna(d.iloc[0].rank_change)
 b['clock']='ep35_acquisition'
 with pytest.raises(ValueError,match='clock mismatch'):changes(a,b)


def test_missing_mechanism_identity_and_duplicate_dates_rejected():
 o,e,v,m=inputs()
 with pytest.raises(ValueError,match='catalogue mismatch'):assemble(o,e,v,m.iloc[:1],'2026-09-30','publication_proxy')
 e=pd.concat([e,e])
 with pytest.raises(ValueError,match='duplicate expectation'):assemble(o,e,v,m,'2026-09-30','publication_proxy')

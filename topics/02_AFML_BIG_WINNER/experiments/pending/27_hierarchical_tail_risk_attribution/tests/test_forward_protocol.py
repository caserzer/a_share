import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from forward import valid_origin,check_confirmation_gate,check_prepared
from core import C


def test_no_future_or_late_archive():
    calendar=pd.bdate_range('2026-10-01','2027-06-30')
    with pytest.raises(AssertionError):valid_origin('2026-10-30','2026-10-20 17:00',calendar)
    with pytest.raises(AssertionError):valid_origin('2026-10-30','2026-11-02 17:00',calendar)


def test_month_end_and_post_close_required():
    calendar=pd.bdate_range('2026-10-01','2027-06-30')
    with pytest.raises(AssertionError):valid_origin('2026-10-29','2026-10-29 17:00',calendar)
    with pytest.raises(AssertionError):valid_origin('2026-10-30','2026-10-30 15:00',calendar)
    assert valid_origin('2026-10-30','2026-10-30 17:00',calendar)==pd.Timestamp('2026-10-30')


def test_event_and_power_gates_cannot_be_replaced_by_36_months_alone():
    assert not check_confirmation_gate(35,400,24,.001)['ready']
    assert not check_confirmation_gate(36,299,24,.001)['ready']
    assert not check_confirmation_gate(36,400,23,.001)['ready']
    assert not check_confirmation_gate(36,400,24,.003)['ready']
    assert check_confirmation_gate(36,400,24,.001)['ready']
    assert not check_confirmation_gate(40,400,24,.001)['ready']


def test_forward_prepared_panel_refuses_future_labels_and_industry_backfill():
    cols=set(C['eligibility_features']+sum([C[k] for k in ['risk_features','market_features','industry_features','valuation_features','financial_features']],[]))
    f=pd.DataFrame({c:[1.] for c in cols});f['industry_id']='legacy:C26';f['industry_sector']='C';f['instrument']='SZ000001';f['date']=pd.Timestamp('2026-10-30')
    f['financial_available_date']=pd.Timestamp('2026-10-29');f['yield_observation_date']=pd.Timestamp('2026-10-29');f['industry_published']=pd.Timestamp('2026-09-30');f['y_6']=np.nan
    assert len(check_prepared(f,pd.Timestamp('2026-10-30'))[1])==1
    bad=f.copy();bad.y_6=-.3
    with pytest.raises(AssertionError):check_prepared(bad,pd.Timestamp('2026-10-30'))
    bad=f.copy();bad.industry_published=pd.Timestamp('2026-11-01')
    with pytest.raises(AssertionError):check_prepared(bad,pd.Timestamp('2026-10-30'))
    bad=f.copy();bad.financial_available_date=pd.NaT
    with pytest.raises(AssertionError):check_prepared(bad,pd.Timestamp('2026-10-30'))

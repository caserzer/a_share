import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from prospective import validate_date,confirmation_gate,future_features


def test_forecast_rejects_future_date_and_late_archive():
    cal=pd.bdate_range('2026-10-01','2027-06-30')
    with pytest.raises(AssertionError):validate_date('2026-10-30','2026-10-20 17:00',cal)
    with pytest.raises(AssertionError):validate_date('2026-10-30','2026-11-02 17:00',cal)


def test_forecast_requires_after_close_and_actual_month_last_session():
    cal=pd.bdate_range('2026-10-01','2027-06-30')
    with pytest.raises(AssertionError):validate_date('2026-10-30','2026-10-30 15:00',cal)
    with pytest.raises(AssertionError):validate_date('2026-10-29','2026-10-29 17:00',cal)
    assert validate_date('2026-10-30','2026-10-30 17:00',cal)==pd.Timestamp('2026-10-30')


def test_truncated_calendar_cannot_fake_month_end():
    with pytest.raises(AssertionError):validate_date('2026-10-29','2026-10-29 17:00',pd.bdate_range('2026-10-01','2026-10-29'))


def monthly(n=36,delta=.001):
    dates=pd.date_range('2026-10-31',periods=n,freq='ME')
    return pd.concat([pd.DataFrame(dict(date=dates,model='M_R',brier=.14)),pd.DataFrame(dict(date=dates,model='M_VF',brier=.14+delta))],ignore_index=True)


def test_confirmation_requires_time_events_and_event_months():
    assert not confirmation_gate(monthly(35),400,25)['ready']
    assert not confirmation_gate(monthly(),299,25)['ready']
    assert not confirmation_gate(monthly(),400,23)['ready']


def test_confirmation_not_selected_by_favorable_effect_sign():
    assert confirmation_gate(monthly(delta=.005),400,25)['ready']
    assert confirmation_gate(monthly(delta=-.005),400,25)['ready']


def test_confirmation_requires_consecutive_origins():
    m=monthly(37);removed=m.date.unique()[8];m=m[m.date!=removed]
    with pytest.raises(AssertionError):confirmation_gate(m,400,25)


def test_confirmation_fixed_gate_and_power_not_just_36_months():
    assert not confirmation_gate(monthly(40),400,25)['ready']
    m=monthly();m.loc[m.model.eq('M_VF'),'brier']=.14+np.tile([-.1,.1],18)
    assert not confirmation_gate(m,400,25)['ready']


def test_future_features_use_only_current_or_past_row_information():
    f=pd.DataFrame(dict(date=pd.to_datetime(['2026-10-30']*2),financial_report_date=pd.to_datetime(['2025-06-30']*2),turnover21=[.1,.3],vol63=[.2,.4],market_vol63=[.1,.1],credit_spread_3y=[.5,.5],y_6=[np.nan,np.nan]))
    result=future_features(f)
    np.testing.assert_allclose(result.state_turnover,[.2,.2]);np.testing.assert_allclose(result.vol_x_market_vol,[.02,.04])
    assert result.y_6.isna().all() and (result.financial_age_days>0).all()

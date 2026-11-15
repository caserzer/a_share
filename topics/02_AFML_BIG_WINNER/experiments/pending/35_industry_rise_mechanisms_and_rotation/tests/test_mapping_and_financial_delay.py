import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from stock_mapping_r06 import weighted_path
from financial_delay_r07 import company_at


def test_fixed_shares_and_drift_are_not_daily_rebalanced():
    prices=np.array([[10.,20.],[20.,20.],[10.,40.]])
    nav,drift=weighted_path(prices,[.25,.75])
    assert np.allclose(nav,[1.,1.25,1.75])
    assert np.allclose(drift,[.25/1.75,1.5/1.75])


def test_any_missing_stock_is_not_dropped_or_filled():
    assert weighted_path([[10,20],[11,np.nan]],[.5,.5]) is None
    assert weighted_path([[10,20],[11,0]],[.5,.5]) is None


def test_financial_cutoff_excludes_later_report_and_handles_negative_base():
    raw=pd.DataFrame({'api':['fina_indicator_vip']*2,'ts_code':['000001.SZ']*2,
        'end_date':pd.to_datetime(['2025-03-31','2026-03-31']),
        'proxy_available_date':pd.to_datetime(['2025-04-30','2026-04-30']),
        'profit_dedt':[-100.,100.],'grossprofit_margin':[10.,12.]})
    assert company_at(raw,pd.Timestamp('2026-04-29')).empty
    result=company_at(raw,pd.Timestamp('2026-04-30'))
    assert result.dedt_change.iloc[0]==1
    assert result.margin_delta.iloc[0]==2
    assert result.profit_sign_regime.iloc[0]=='loss_to_profit'


def test_zero_financial_denominator_stays_missing():
    raw=pd.DataFrame({'api':['fina_indicator_vip']*2,'ts_code':['000001.SZ']*2,
        'end_date':pd.to_datetime(['2025-03-31','2026-03-31']),
        'proxy_available_date':pd.to_datetime(['2025-04-30','2026-04-30']),
        'profit_dedt':[0.,0.],'grossprofit_margin':[10.,12.]})
    assert company_at(raw,pd.Timestamp('2026-04-30')).dedt_change.isna().all()


def test_unknown_stock_exposure_is_not_renormalized():
    from stock_mark_audit import summarize_marks
    frame=pd.DataFrame({'weight':[.8,.2],'endpoint_usable':[True,False],
        'full_path_usable':[True,False],'endpoint_return':[.1,np.nan]})
    r=summarize_marks(frame)
    assert np.isclose(r['known_weighted_return_contribution'],.08)
    assert np.isclose(r['conditional_loss_floor'],-.12)
    assert np.isnan(r['conditional_endpoint_return'])
    assert r['finite_upper_bound'] is False


def test_cooldown_suppresses_without_refilling_and_separates_industries():
    from process_replay_r09 import cooldown_alerts
    frame=pd.DataFrame({'era':['SW2021']*5,'level':['L3']*5,'industry_code':['a','a','a','a','b'],
        'date':pd.to_datetime(['2026-01-01','2026-01-02','2026-01-03','2026-01-04','2026-01-02']),
        'day_i':[0,1,20,21,1]})
    kept=cooldown_alerts(frame)
    assert sorted(kept.index)==[0,3,4]

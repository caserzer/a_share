import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from build_panel import price_features, delayed_labels
from common import centered_rank


def fixture():
    dates=pd.bdate_range('2020-01-01',periods=150)
    return pd.DataFrame({'date':dates,'nav':np.exp(np.arange(150)*.001)}),pd.Series(np.exp(np.arange(150)*.0003),index=dates)


def test_features_invariant_to_future_price_changes():
    g,b=fixture(); baseline=price_features(g)
    altered=g.copy();altered.loc[100:,'nav']*=100
    other=price_features(altered)
    pd.testing.assert_frame_equal(baseline.loc[:99],other.loc[:99])


def test_delayed_returns_and_label_maturity():
    g,b=fixture();r=delayed_labels(price_features(g),b)
    assert np.isclose(r.return20.iloc[70],g.nav.iloc[91]/g.nav.iloc[71]-1)
    assert r.maturity20.iloc[70]==g.date.iloc[91]
    assert r.entry_date.iloc[70]==g.date.iloc[71]
    assert r.return60.iloc[-61:].isna().all()


def test_future_trough_uses_entry_not_signal_and_all_future_sessions():
    g,b=fixture();g.loc[80,'nav']=.5
    r=delayed_labels(price_features(g),b)
    expected=min((g.nav/b.to_numpy()).iloc[72:92])/(g.nav.iloc[71]/b.iloc[71])-1
    assert np.isclose(r.rel_trough20.iloc[70],expected)


def test_segment_break_prevents_cross_gap_targets():
    g,b=fixture()
    a=delayed_labels(price_features(g.iloc[:75]),b)
    assert a.return20.iloc[-21:].isna().all()
    nxt=price_features(g.iloc[80:])
    assert nxt.mom60.iloc[:60].isna().all()


def test_rank_missing_not_zero_and_ties_centered():
    r=centered_rank(pd.Series([1.,1.,3.,np.nan]))
    assert np.isnan(r.iloc[3]) and r.iloc[0]==r.iloc[1]
    assert abs(r.mean())<1e-15


def test_training_labels_mature_before_fit_and_calibration_cutoffs():
    from train_r02 import train_masks
    d=pd.DataFrame({'date':pd.to_datetime(['2022-05-31','2022-06-30','2022-07-29','2022-12-30','2023-01-31']),
        'maturity60':pd.to_datetime(['2022-08-25','2022-09-26','2022-10-25','2023-03-27','2023-04-28']), 'y':[0.,1.,0.,1.,0.]})
    fit,cal,test=train_masks(d,2023,60,'onset')
    assert not fit.any() # even May label was not mature at July calibration start
    assert cal.tolist()==[False,False,True,False,False]
    assert test.tolist()==[False,False,False,False,True]


def test_immature_binary_targets_remain_missing():
    from train_r02 import target
    g,b=fixture();d=delayed_labels(price_features(g),b)
    for task in ['onset','reversal']:
        y,_=target(d,task,60)
        assert y.iloc[-61:].isna().all()


def test_financial_conflicts_are_not_arbitrarily_selected():
    from supplement_financials import asof_values
    d=pd.DataFrame({'api':['fina_indicator_vip']*4,'ts_code':['000001.SZ']*4,
        'end_date':pd.to_datetime(['2025-03-31']*4),
        'proxy_available_date':pd.to_datetime(['2025-04-21','2025-05-06','2025-05-06','2025-06-02']),
        'profit_dedt':[1.,2.,3.,9.]})
    assert asof_values(d,pd.Timestamp('2025-04-30'),'profit_dedt').value.iloc[0]==1
    assert pd.isna(asof_values(d,pd.Timestamp('2025-05-31'),'profit_dedt').value.iloc[0])
    assert asof_values(d,pd.Timestamp('2025-06-03'),'profit_dedt').value.iloc[0]==9


def test_announcement_next_session_and_calendar_tail():
    from supplement_financials import next_session
    cal=pd.bdate_range('2026-01-01',periods=5)
    actual=next_session(pd.to_datetime(['2026-01-02',None,'2026-01-08']),cal)
    assert actual.iloc[0]==pd.Timestamp('2026-01-05')
    assert pd.isna(actual.iloc[1]) and pd.isna(actual.iloc[2])


def test_turnover_counts_drift_and_both_sides():
    from portfolio_r04 import turnover
    assert turnover({'a':.5,'b':.5},{})==1
    assert np.isclose(turnover({'a':.5,'b':.5},{'a':.6,'b':.4}),.2)
    assert turnover({'c':1},{'a':1})==2


def test_portfolio_does_not_bridge_missing_or_reset_segments():
    from portfolio_r04 import path_for
    dates=pd.bdate_range('2026-01-01',periods=4)
    g=pd.DataFrame({'nav':[1.,1.1,1.2,1.3],'day_i':[1,2,3,4],'block':[1,1,1,1]},index=dates)
    assert np.allclose(path_for(g,dates),[1,1.1,1.2,1.3])
    assert path_for(g.drop(dates[1]),dates) is None
    g.loc[dates[2]:,'block']=2
    assert path_for(g,dates) is None

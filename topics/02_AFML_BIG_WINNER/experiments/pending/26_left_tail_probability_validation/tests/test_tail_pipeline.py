import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from core import event_labels,coherence,point_metrics,risk_flags,weights,shuffle_within_month,train_test,ci,paired
from portfolio import execute_rebalance,selection,simulate


def test_strict_event_boundary_and_missing():
    y=event_labels([-.20001,-.2,-.19999,np.nan],-.2)
    np.testing.assert_allclose(y[:3],[1,0,0]);assert np.isnan(y[-1])


def test_auxiliary_coherence_preserves_primary_exactly():
    a,b,c=coherence(np.array([.1,.7]),np.array([.2,.5]),np.array([.4,.3]))
    np.testing.assert_array_equal(b,[.2,.5]);assert (a>=b).all() and (b>=c).all()


def test_brier_decomposition_and_constant_auc_ap():
    result=point_metrics([.3]*4,[-.4,.1,.2,.3],-.2)
    assert result['brier']==pytest.approx((.7**2+3*.3**2)/4)
    assert result['brier']==pytest.approx(result['common_brier']+result['relative_brier'])
    assert result['auc']==.5 and result['pr_auc']==.25


def test_risk_flags_ignore_future_labels_and_stable_ties():
    stocks=np.array(['A','B','C','D','E']);p=np.ones(5)
    first=risk_flags(p,stocks,.2);second=risk_flags(p[::-1],stocks[::-1],.2)
    np.testing.assert_array_equal(first,second[::-1]);assert first.sum()==1


def test_warning_groups_defined_before_missing_outcome_filter():
    p=[.9,.8,.1,.05];flags={'20':risk_flags(p,['A','B','C','D'],.2)}
    result=point_metrics(p,[np.nan,-.4,.1,.2],-.2,flags)
    assert result['warning_rows20']==0 and np.isnan(result['precision20'])
    assert result['rows']==3


def test_monthly_weights_not_stock_counts():
    frame=pd.DataFrame(dict(date=[1,1,2,2,2]))
    w=weights(frame);assert np.isclose(w[:2].sum(),w[2:].sum()) and np.isclose(w.mean(),1)


def test_negative_control_preserves_every_month_all_thresholds_and_missing():
    f=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31']*6+['2020-02-29']*6),y_6=[-.5,-.25,-.15,.1,.4,np.nan]*2))
    a=shuffle_within_month(f)
    np.testing.assert_array_equal(a.y_6.isna(),f.y_6.isna())
    for t in [-.1,-.2,-.3]:
        before=f.assign(y=event_labels(f.y_6,t)).groupby('date').y.sum()
        after=a.assign(y=event_labels(a.y_6,t)).groupby('date').y.sum()
        pd.testing.assert_series_equal(before,after)
    pd.testing.assert_frame_equal(a,shuffle_within_month(f))


def test_maturity_strict_quarter_cutoff_not_prediction_day():
    p=pd.DataFrame(dict(date=pd.to_datetime(['2019-12-31','2020-01-31','2020-03-31','2020-04-30']),end_6=pd.to_datetime(['2020-03-31','2020-04-01','2020-09-30',None]),y_6=[-.3,-.1,.2,np.nan]))
    train,test=train_test(p,pd.Period('2020Q2'))
    assert len(train)==1 and len(test)==1 and test.y_6.isna().all()


def test_pairing_fails_on_different_calendar():
    a=pd.DataFrame(dict(date=[1,2],brier=[.1,.2]));b=pd.DataFrame(dict(date=[2,1],brier=[.1,.3]))
    np.testing.assert_allclose(paired(a,b,'brier'),[-.2,.1])
    with pytest.raises(AssertionError):paired(a,b.iloc[:1],'brier')


def test_bootstrap_keeps_missing_auc_calendar_and_constant_difference():
    out=ci([-.01]*12,6);assert out['months']==12 and out['high95']<0
    gap=ci([0.,np.nan,0.,np.nan,0.],6);assert gap['months']==5 and gap['defined_months']==3
    assert gap['low95']==0 and gap['high95']==0


def test_rebalance_cash_conservation_and_costs():
    h,c,traded,fee=execute_rebalance(np.zeros(2),1.,np.array([2.,4.]),np.array([2.,4.]),np.array([.5,.5]),.01)
    assert c>=0 and h.min()>0
    assert np.dot(h,[2.,4.])+c+fee==pytest.approx(1.)
    assert fee==pytest.approx(traded*.01)


def test_missing_quote_never_trades_or_silently_writes_off_holding():
    h,c,traded,fee=execute_rebalance(np.array([.5,0.]),0.,np.array([np.nan,4.]),np.array([2.,4.]),np.array([0.,1.]),.01)
    np.testing.assert_array_equal(h,[.5,0.]);assert c==traded==fee==0


def test_all_filter_strategies_match_counts_without_outcome_selection():
    f=pd.DataFrame(dict(board=np.tile([0,1],30),log_cap=np.linspace(20,26,60),vol63=np.tile(np.linspace(.1,.5,20),3),instrument=[f'S{i}' for i in range(60)],p_r=np.linspace(.01,.8,60),p_vf=np.linspace(.8,.01,60)))
    g,chosen=selection(f)
    assert len(set(m.sum() for m in chosen.values()))==1
    counts=[g.loc[m].groupby('stratum').size() for m in chosen.values()]
    pd.testing.assert_series_equal(counts[0],counts[1]);pd.testing.assert_series_equal(counts[0],counts[2])


def test_daily_nav_counts_first_transaction_cost_and_stale_exposure():
    dates=pd.to_datetime(['2020-01-02','2020-01-03','2020-01-06']);prices=pd.DataFrame({'A':[1.,np.nan,.8]},index=dates)
    f=simulate(prices,dates,{dates[0]:np.array([1.])},.01)
    assert f.nav.iloc[0]==pytest.approx(1/1.01)
    assert f.stale_value_fraction.iloc[1]==pytest.approx(1.)
    assert f.nav.iloc[2]==pytest.approx(.8/1.01)
    assert f.drawdown.iloc[0]<0

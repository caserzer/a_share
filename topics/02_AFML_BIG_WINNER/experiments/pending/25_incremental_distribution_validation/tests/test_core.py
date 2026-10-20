import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from core import crps, score, cohort_distance, paired, bootstrap_means, interval, month_weights, train_test


def test_crps_matches_pairwise_energy_formula():
    rng=np.random.default_rng(1)
    a=rng.normal(size=(13,17));y=rng.normal(size=13)
    expected=np.abs(a-y[:,None]).mean(axis=1)-.5*np.abs(a[:,:,None]-a[:,None,:]).mean(axis=(1,2))
    np.testing.assert_allclose(crps(a,y),expected,atol=1e-14)


def test_crps_degenerate_atom():
    np.testing.assert_allclose(crps([[.2,.2],[.1,.1]],[.5,-.3]),[.3,.4])


def test_missing_labels_do_not_become_negative_events():
    result=score(np.zeros((2,200)),[np.nan,0])
    assert result.loc[0,['crps','brier','tail_brier','pit','cover05','observed_up']].isna().all()
    assert result.p_up.notna().all()


def test_pit_midpoint_for_ties_and_strict_events():
    r=score(np.array([[-.2,0.,0.,.4]]),[0])
    assert r.pit.iloc[0]==.5
    assert r.p_up.iloc[0]==.25
    assert r.p_tail.iloc[0]==0


def test_cohort_distance_equals_cdf_integral():
    atoms=np.array([[0.,1.],[2.,3.]])
    y=np.array([.5,2.5])
    support=np.unique(np.r_[atoms.reshape(-1),y]);mid=(support[:-1]+support[1:])/2
    integral=sum((np.mean(atoms<=x)-np.mean(y<=x))**2*(hi-lo) for x,lo,hi in zip(mid,support[:-1],support[1:]))
    assert cohort_distance(atoms,y)==pytest.approx(integral)
    assert cohort_distance(atoms,atoms.reshape(-1))==pytest.approx(0)


def test_paired_keys_fail_closed():
    a=pd.DataFrame(dict(date=[1,2],crps=[.1,.2]))
    b=pd.DataFrame(dict(date=[2,1],crps=[.3,.1]))
    np.testing.assert_allclose(paired(a,b,'crps'),[0,-.1])
    with pytest.raises(AssertionError):paired(a,b.iloc[:1],'crps')


def test_bootstrap_month_constant_and_determinism():
    a=bootstrap_means([-.01]*30,6,reps=500)
    np.testing.assert_allclose(a,-.01)
    np.testing.assert_array_equal(bootstrap_means(range(20),6,reps=500),bootstrap_means(range(20),6,reps=500))
    ci=interval([-.01]*30,6)
    assert ci['high95']<0 and ci['months']==30 and ci['approximate_blocks']==5


def test_training_month_weights_not_stock_count():
    train=pd.DataFrame(dict(date=[1,1,2,2,2,2]))
    w=month_weights(train)
    assert np.isclose(w[:2].sum(),w[2:].sum())
    assert np.isclose(w.mean(),1)


def test_maturity_strict_and_missing_outcomes_retained_in_test():
    p=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31','2020-02-29','2020-03-31','2020-04-30']),
        end_1=pd.to_datetime(['2020-02-29','2020-04-01','2020-04-30',None]),y_1=[.1,.2,.3,np.nan]))
    train,test=train_test(p,pd.Timestamp('2020-04-01'),1,pd.Period('2020Q2'))
    assert len(train)==1 and len(test)==1 and test.y_1.isna().all()


def test_horizon_overlap_uses_months_not_stocks():
    x=np.repeat(np.linspace(-.03,.03,12),100)
    months=pd.Series(x).groupby(np.repeat(np.arange(12),100)).mean()
    ci=interval(months,6)
    assert ci['months']==12 and ci['approximate_blocks']==2

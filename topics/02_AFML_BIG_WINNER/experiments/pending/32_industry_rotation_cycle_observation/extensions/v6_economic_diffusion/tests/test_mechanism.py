import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from features6 import window_returns,avg
from statistics6 import block_summary,bh
from mechanism6 import regression


def test_past_stock_returns_ignore_appended_future():
    p=np.arange(1,81,dtype=float);c=np.array(['a']*80);v=np.ones(80)
    a=window_returns(p,c,v,np.array([10]),np.array([31]))
    p[32:]*=100
    np.testing.assert_equal(a,window_returns(p,c,v,np.array([10]),np.array([31])))


def test_nontrading_endpoints_are_unknown():
    p=np.arange(1,81,dtype=float);c=np.array(['a']*80);v=np.ones(80);v[31]=0
    assert np.isnan(window_returns(p,c,v,np.array([10]),np.array([31]))[0])


def test_changed_price_chain_blocks_return():
    p=np.arange(1,81,dtype=float);c=np.array(['a']*80);c[31]='b';v=np.ones(80)
    assert np.isnan(window_returns(p,c,v,np.array([10]),np.array([31]))[0])


def test_no_future_price_is_zero_filled():
    p=np.arange(1,81,dtype=float);c=np.array(['a']*80);v=np.ones(80)
    assert np.isnan(window_returns(p,c,v,np.array([70]),np.array([91]))[0])


def test_all_three_leaders_required_but_peer_coverage_explicit():
    assert np.isnan(avg(np.array([[.1,.2,np.nan]]),all_required=True)[0])
    assert np.isfinite(avg(np.array([[.1,.2,.3,.4,np.nan]]))[0])


def test_bootstrap_preserves_direction_and_bh_accounts_for_family():
    result=block_summary(np.linspace(.1,.2,30));assert result['ci_low']>0 and result['p_one_sided']<.05
    q=bh([.001,.03,.4]);assert np.all(q>=np.array([.001,.03,.4])) and q[0]<=q[1]<=q[2]


def test_planted_leading_relation_recovered_without_future_predictor():
    rng=np.random.default_rng(3);n=300
    lead=rng.normal(0,.1,n);peer=rng.normal(0,.1,n)
    g=pd.DataFrame(dict(leader21=lead,peer21=peer,peer63=rng.normal(0,.2,n),leader63=rng.normal(0,.2,n),
        other_leader21=rng.normal(0,.1,n),risk126=rng.uniform(.06,.12,n),market21=rng.normal(0,.02,n),
        log_members=rng.uniform(2,4,n),peer_y=.6*lead+rng.normal(0,.02,n),leader_y=rng.normal(0,.1,n)))
    a=regression(g,'forward');b=regression(g,'other_industry')
    assert a['positive_slope']>.4 and a['positive_slope']>b['positive_slope']

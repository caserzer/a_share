from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from onset_replay import describe_features,observation


def fixture(n=140):
    days=pd.bdate_range('2020-01-01',periods=n)
    g=pd.DataFrame({'date':days,'nav':np.exp(np.sin(np.arange(n)/19)*.1),
                    'day_i':np.arange(n),'breadth21':.5+.2*np.sin(np.arange(n)/13),
                    'volume_ratio':1.,'coverage':1.,'members':10,'block':1})
    return g,pd.Series(np.linspace(100,105,n),index=days)


def test_descriptions_are_prefix_invariant():
    g,m=fixture();a=describe_features(g,m)
    cut=90;b=describe_features(g.iloc[:cut],m.iloc[:cut])
    cols=['rate5','rate20','rate60','rate_change','new_low_count10','breadth_change5','breadth_change20']
    pd.testing.assert_frame_equal(a.iloc[:cut][cols],b[cols])
    g.loc[cut:,'nav']*=100
    c=describe_features(g,m)
    pd.testing.assert_frame_equal(a.iloc[:cut][cols],c.iloc[:cut][cols])


def test_gap_cannot_be_silently_bridged():
    g,m=fixture()
    with pytest.raises(AssertionError):describe_features(g.drop(index=50),m)


def test_partial_and_missing_are_not_negative_evidence():
    g,m=fixture()
    o=observation(g.iloc[:4],m,g.date.iloc[3])
    assert o['data_status']=='PARTIAL' and o['rate20'] is None and o['rate_change'] is None
    o=observation(g.iloc[:4],m,g.date.iloc[5])
    assert o['data_status']=='MISSING' and 'rate20' not in o

from onset_panel import process,valid_window,METHODS


def weekly_fixture():
    n=40
    g=pd.DataFrame({'date':pd.date_range('2021-01-01',periods=n,freq='W-FRI'),
                    'week_i':np.arange(n),'x':np.r_[np.linspace(.1,0,11),np.linspace(.001,.15,29)],
                    'era':'TEST','industry_code':'TEST','industry_name':'TEST','block':1,
                    'sample_case':False,'eligible':True,'rate20':-.01,'rate60':-.01,
                    'rate_change':.001,'rate5':.002,'breadth21':.4,'market_breadth_up_fraction':.5})
    for method in METHODS:g[method]=False
    g.loc[10,'slowdown']=True;g.loc[10,'pressure_easing']=True
    g.loc[14:,'rate20']=.01;g.loc[14:,'breadth21']=.6;g.loc[14:,'broad_confirmation']=True
    return g


def test_prompt_identity_does_not_depend_on_future_outcome():
    a=weekly_fixture();e,_,_=process(a)
    b=a.copy();b.loc[20:,'x']-=10;b.loc[20:,'rate20']=-1
    f,_,_=process(b)
    keys=['method','date','week_i','position']
    ea=pd.DataFrame(e);fa=pd.DataFrame(f)
    pd.testing.assert_frame_equal(ea[ea.week_i<20][keys].reset_index(drop=True),fa[fa.week_i<20][keys].reset_index(drop=True))


def test_no_full_followup_means_unknown_not_failure():
    g=weekly_fixture().iloc[:14];e,r,_=process(g)
    p=next(x for x in e if x['method']=='pressure_easing')
    assert p['development']=='UNKNOWN' and not p['followup_known']
    assert all(x['position']+8<len(g) for x in r)
    broken=weekly_fixture().drop(index=15).reset_index(drop=True)
    assert not valid_window(broken,10,1,8)

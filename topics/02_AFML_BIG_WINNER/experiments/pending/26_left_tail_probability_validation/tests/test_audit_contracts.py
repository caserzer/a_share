import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from portfolio import selection
from core import point_metrics


def test_filter_selection_cannot_change_when_future_returns_are_replaced():
    rng=np.random.default_rng(92);n=180
    frame=pd.DataFrame(dict(board=np.tile([0,1],n//2),log_cap=rng.normal(size=n),vol63=rng.uniform(.1,.5,n),instrument=[f'S{i}' for i in range(n)],p_r=rng.uniform(0,1,n),p_vf=rng.uniform(0,1,n),actual=rng.normal(size=n)))
    _,a=selection(frame);frame.actual=-frame.actual*100;_,b=selection(frame)
    for key in a:np.testing.assert_array_equal(a[key],b[key])


def test_probability_ranking_and_calibration_are_different_properties():
    y=np.array([-.4,-.3,.1,.2,.3,.4]);a=point_metrics([.8,.7,.3,.2,.1,.05],y,-.2);b=point_metrics([.99,.98,.97,.96,.95,.94],y,-.2)
    assert a['auc']==b['auc']==1.
    assert a['brier']<b['brier']


def test_fpr_is_false_positives_over_all_non_events():
    result=point_metrics([.9,.8,.2,.1],[-.4,.2,.3,.4],-.2,{'20':np.array([True,True,False,False])})
    assert result['recall20']==1.
    assert result['fpr20']==1/3
    assert result['precision20']==.5

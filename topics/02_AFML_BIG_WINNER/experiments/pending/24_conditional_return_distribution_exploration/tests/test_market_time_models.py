import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from run_direct_probability import classes, weighted_stats


def test_training_requires_mature_labels_and_calendar_origin_window():
    date=pd.Timestamp('2024-01-31')
    p=pd.DataFrame(dict(date=pd.to_datetime(['2020-12-31','2021-01-29','2023-07-31','2023-08-31']),
        y_6=[.1,.2,.3,.4], end_6=pd.to_datetime(['2021-06-30','2021-07-29','2024-01-31','2024-02-29'])))
    got=select_training(p,6,date,36)
    assert list(got.index)==[1]


def test_month_weights_remove_stock_count_and_follow_half_life():
    date=pd.Timestamp('2024-01-31')
    p=pd.DataFrame(dict(date=pd.to_datetime(['2021-01-29','2021-01-29','2023-01-31'])))
    balanced=observation_weights(p,date,True,None)
    np.testing.assert_allclose(balanced[:2].sum(),balanced[2])
    decay=observation_weights(p,date,True,24)
    np.testing.assert_allclose(decay[:2].sum()/decay[2],.5)
    np.testing.assert_allclose(decay.mean(),1)
    np.testing.assert_array_equal(observation_weights(p,date,False,None),np.ones(3))


def test_weighted_class_distribution_stays_coherent_and_reflects_weights():
    y=np.array([-.3,-.1,-.02,0.,.02,.1,.3,.9]); labels=classes(y)
    probabilities=np.array([[0,0,0,0,0,0,1.],[.1,.1,.1,.1,.1,.1,.4]])
    old=weighted_class_distribution(y,labels,probabilities,np.ones(len(y)))
    weights=np.ones(len(y)); weights[-1]=100
    a,w=weighted_class_distribution(y,labels,probabilities,weights)
    assert (np.diff(a,axis=1)>=0).all()
    np.testing.assert_allclose(w.sum(axis=1),1)
    assert (a[0]*w[0]).sum()>(old[0][0]*old[1][0]).sum()
    scores=weighted_stats(a,w,np.array([.3,0.]))
    np.testing.assert_allclose(scores[['p_up','p_down','p_zero']].sum(axis=1),1)

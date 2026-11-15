import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from v3_m01_prepare import target_at, feature_group, FEATURES_CHANGE


def test_future_tail_cannot_change_target():
    y=np.r_[-.01*np.arange(16),-.15+.006*np.arange(1,40)]
    for t in range(8,len(y)-8):
        changed=y.copy();changed[t+9:]=100
        assert target_at(y,t)==target_at(changed,t)
    assert any(target_at(y,t)[0]==1 for t in range(8,len(y)-8))


def test_immature_not_negative_and_pulse_not_positive():
    y=np.r_[-.01*np.arange(16),-.1,-.2,np.full(20,-.2)]
    assert target_at(y,len(y)-8)[0] is None
    assert target_at(y,7)[0] is None
    assert target_at(y,16)[0]!=1


def test_features_ignore_future_and_cross_chain():
    d=pd.DataFrame({'day_i':np.arange(100),'nav':100+np.arange(100),'block':1})
    full=feature_group(d)
    pd.testing.assert_frame_equal(full.iloc[:70],feature_group(d.iloc[:70]))
    d.loc[60:,'block']=2
    assert feature_group(d).loc[60:99,FEATURES_CHANGE].isna().all().all()


def test_late_strength_is_not_early_training_positive():
    y=np.r_[-.01*np.arange(16),-.15+.02*np.arange(1,45)]
    assert target_at(y,30)[0]==0
    assert target_at(y,30)[1]=='CONFIRMED_BUT_NOT_EARLY_ALIGNED'

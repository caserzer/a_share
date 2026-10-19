import numpy as np
import pandas as pd
import pytest
from scaled_horizon_models import risk_scale,normalized_return,restore_atoms,normalize_training
from run_direct_probability import classes
from shared_horizon_models import stack_training


def test_annualized_horizon_units_and_round_trip():
    np.testing.assert_allclose(risk_scale(.3,[1,3,6,12]),.3*np.sqrt(np.array([1,3,6,12])/12))
    y=np.array([-.7,-.1,0,.1,2.]);v=np.array([.1,.2,.3,.4,.8]);h=np.array([1,3,6,3,1])
    u=normalized_return(y,v,h)
    np.testing.assert_allclose(restore_atoms(u[:,None],v,h).ravel(),y,atol=1e-14)


def test_zero_sign_and_scaled_class_boundaries():
    u=np.array([-.21,-.2,-.051,-.05,-.001,0,.001,.049,.05,.199,.2])
    np.testing.assert_array_equal(classes(u),[0,1,1,2,2,3,4,4,5,5,6])
    a=restore_atoms(u,[.1,1.2],6)
    np.testing.assert_array_equal(np.sign(a),np.tile(np.sign(u),(2,1)))
    assert (a[:,5]==0).all() and (np.diff(a,axis=1)>=0).all() and (a>=-1).all()


def test_normalization_uses_origin_risk_and_only_mature_labels():
    p=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31','2020-02-28']),instrument=['A','B'],vol63=[.2,.8],
        y_1=[.1,.9],end_1=pd.to_datetime(['2020-02-28','2020-04-01'])))
    date=pd.Timestamp('2020-03-01');train=normalize_training(stack_training(p,date,[1],['vol63']))
    assert len(train)==1
    assert train.normalized_label.iloc[0]==pytest.approx(np.log1p(.1)/(.2*np.sqrt(1/12))/10)
    p.loc[1,['y_1','vol63']]=[-.99,100]
    pd.testing.assert_frame_equal(train,normalize_training(stack_training(p,date,[1],['vol63'])))


def test_invalid_data_fails_instead_of_filtering_and_floor_is_numeric():
    for v in [0,-1,np.nan]:
        with pytest.raises(ValueError):risk_scale(v,1)
    for y in [-1,-2,np.nan]:
        with pytest.raises(ValueError):normalized_return(y,.2,1)
    assert risk_scale(.0001,12)==pytest.approx(.001)

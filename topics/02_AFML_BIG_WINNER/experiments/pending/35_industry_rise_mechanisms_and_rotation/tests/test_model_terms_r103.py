import numpy as np
import pytest
from scipy.special import expit
from model_terms_r103 import decompose

def model(task='onset'):
    return dict(task=task,columns=['a','b'],scaler_mean=[.1,-.1],scaler_scale=[.2,.4],coefficient=[[2.,-3.]],intercept=[.7],calibration_coefficient=[[-2.]],calibration_intercept=[.3])

def test_negative_calibration_slope_and_baseline():
    m=model();z,c,base,terms,baseline,total,p=decompose([.3,.3],m)
    np.testing.assert_allclose(z,[1.,1.]);np.testing.assert_allclose(base,[2.,-3.]);np.testing.assert_allclose(terms,[-4.,6.])
    assert np.isclose(baseline,-1.1) and np.isclose(total,.9) and np.isclose(p,expit(.9))
    *_,baseline,total,p=decompose(m['scaler_mean'],m)
    assert np.isclose(total,baseline) and np.isclose(p,expit(baseline))

def test_regression_and_uncalibrated():
    m=model('return');*_,baseline,total,p=decompose([.3,.3],m)
    assert np.isclose(baseline,.7) and np.isclose(total,-.3) and p==total
    m=model();m['calibration_coefficient']=None
    with pytest.raises(ValueError,match='uncalibrated'):decompose([.3,.3],m)

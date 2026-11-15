import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from pe_ttm_agreement_r118 import measures

def test_negative_and_opposite_sign_distances():
    r=measures([-100.,100.,100.],[-100.,-100.,-200.])
    np.testing.assert_allclose(r['symmetric_distance'],[0,2,2]);assert r['sign_agreement'].tolist()==[True,False,False]
    np.testing.assert_allclose(r['absolute_cny_distance'],[0,200,300]);assert np.isnan(r['abs_log_magnitude_ratio'][1:]).all()

def test_zero_and_scale_invariance():
    r=measures([0.,1.,101.],[0.,0.,100.]);assert r['symmetric_distance'][0]==0 and r['symmetric_distance'][1]==2
    assert np.isnan(r['signed_relative'][:2]).all() and r['within_1pct'][2]
    a=measures([101.],[100.]);b=measures([101e6],[100e6]);np.testing.assert_allclose(a['symmetric_distance'],b['symmetric_distance'])

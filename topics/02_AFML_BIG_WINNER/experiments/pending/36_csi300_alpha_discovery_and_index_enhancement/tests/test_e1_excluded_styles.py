import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from e1_excluded_styles import match_styles,baseline_scores,STYLECOLS

def test_matching_all_constraints_and_cap():
 z=np.array([[-1.,0],[1.,0],[0.,1.]])
 w,info=match_styles(z,np.array([0.,0.]),.4,.2)
 assert info['status']=='MATCHED'
 assert np.max(abs(z.T@w/.4))<=.2500001 and w.max()<=.20000001
 assert np.isclose(w.sum(),.4)

def test_no_relaxation_of_impossible_style():
 w,info=match_styles(np.array([[2.,2.],[3.,3.]]),np.zeros(2),.4,.2)
 assert w is None and info['status']=='INFEASIBLE'

def test_peer_capacity_not_ignored():
 w,info=match_styles(np.zeros((1,13)),np.zeros(13),.4,.2)
 assert w is None and info['status']=='INSUFFICIENT_PEER_CAPACITY'

def test_baselines_ignore_future_labels_and_original_score():
 g=pd.DataFrame({s:[1.,2.,3.] for s in STYLECOLS},index=['A','B','C'])
 a=baseline_scores(g);g['h10']=[10,-10,5];g['E1']=[-99,99,3]
 pd.testing.assert_frame_equal(a,baseline_scores(g))
 assert a.REV.idxmax()=='A' and a.HIGHVOL.idxmax()=='C'

def test_affine_rescaling_preserves_style_ranks():
 g=pd.DataFrame({s:[1.,4.,2.] for s in STYLECOLS})
 pd.testing.assert_frame_equal(baseline_scores(g),baseline_scores(g*10+7))

def test_unsupported_inference_is_missing_not_zero():
 from e1_mechanism import bootstrap
 s=pd.Series(np.nan,index=pd.date_range('2021-01-01',periods=50,freq='MS'))
 result=bootstrap(s,'M',3)
 assert result['n']==0 and np.isnan(result['mean']) and np.isnan(result['p'])

def test_planned_holm_family_not_shrunk_for_unsupported_tests():
 from e1_engineered_ablation import holm
 p=holm([.02,np.nan,.3,np.nan])
 np.testing.assert_allclose(p[[0,2]],[.08,.9])
 assert np.isnan(p[[1,3]]).all()

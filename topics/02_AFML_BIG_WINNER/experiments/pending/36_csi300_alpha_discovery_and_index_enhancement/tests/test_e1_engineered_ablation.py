import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from e1_engineered_ablation import factorial,contrast,holm,CONTRASTS

def test_factorial_score_interaction_is_zero_but_group_effect_preserved():
 r=np.random.default_rng(3);y,p,v=r.normal(size=(3,80));s=factorial(y,p,v)
 np.testing.assert_allclose(contrast(pd.DataFrame(s),CONTRASTS['interaction']),0,atol=1e-12)
 np.testing.assert_allclose(contrast(pd.DataFrame(s),CONTRASTS['position']),p,atol=1e-12)
 np.testing.assert_allclose(contrast(pd.DataFrame(s),CONTRASTS['risk']),v,atol=1e-12)

def test_missing_leg_not_zero_filled():
 p=pd.DataFrame({'BOTH':[1.,1.],'NONE':[np.nan,.3]})
 assert np.isnan(contrast(p,CONTRASTS['joint']).iloc[0])
 assert contrast(p,CONTRASTS['joint']).iloc[1]==.7

def test_holm_preserves_original_order():
 np.testing.assert_allclose(holm([.04,.01,.03]),[.06,.03,.06])

def test_ablation_no_input_mutation():
 y=np.array([1.,2.]);old=y.copy();s=factorial(y,y*.2,y*.3);s['BOTH'][0]=3
 np.testing.assert_array_equal(y,old)

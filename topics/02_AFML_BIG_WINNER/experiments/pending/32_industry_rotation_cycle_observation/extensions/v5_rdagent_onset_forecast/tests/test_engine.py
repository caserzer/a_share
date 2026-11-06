import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from common import FEATURES
from engine import validate_spec,compile_features,BASELINES


def test_future_outcome_fields_cannot_be_selected():
    s=dict(BASELINES['logistic']);s['features']=['mom21','y']
    with pytest.raises(AssertionError):validate_spec(s)


def test_engineered_feature_cannot_reference_outcomes_or_dates():
    for name in ['y','label_available_at','date','industry_code','peak_date']:
        s=dict(BASELINES['logistic']);s['engineered']=[dict(name='leak',op='sub',left=name,right=0)]
        with pytest.raises(AssertionError):validate_spec(s)


def test_appending_future_rows_does_not_change_compiled_features():
    f=pd.DataFrame({c:np.arange(6,dtype=float) for c in FEATURES})
    s=dict(BASELINES['logistic']);s['engineered']=[dict(name='acceleration',op='sub',left='mom21',right='mom63')]
    s['features']=['acceleration','dd63']
    pd.testing.assert_frame_equal(compile_features(f,s).iloc[:3],compile_features(f.iloc[:3],s))


def test_target_mutation_does_not_change_features():
    f=pd.DataFrame({c:[1.,2.] for c in FEATURES});f['y']=[0,1]
    a=compile_features(f,BASELINES['logistic']);f['y']=[1,0]
    pd.testing.assert_frame_equal(a,compile_features(f,BASELINES['logistic']))

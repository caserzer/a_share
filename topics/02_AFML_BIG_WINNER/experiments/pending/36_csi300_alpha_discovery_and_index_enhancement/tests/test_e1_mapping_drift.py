import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from e1_mapping_drift import split_change,demean

def test_exact_symmetric_mapping_closure():
 rng=np.random.default_rng(13);x=rng.normal(size=(100,13));a,b,c,d=rng.normal(size=(4,13))
 total,model,data=split_change(a,b,c,d,x)
 np.testing.assert_allclose(model+data,total,atol=1e-12)
 assert abs(model@total+data@total-total@total)<1e-10

def test_unchanged_model_has_zero_model_allocation():
 rng=np.random.default_rng(2);x=rng.normal(size=(30,5));a,b=rng.normal(size=(2,5))
 total,model,data=split_change(a,a,b,b,x)
 np.testing.assert_allclose(model,0,atol=1e-12);np.testing.assert_allclose(total,data)

def test_unchanged_data_has_zero_data_allocation():
 rng=np.random.default_rng(3);x=rng.normal(size=(30,5));a,b=rng.normal(size=(2,5))
 total,model,data=split_change(a,b,a,b,x)
 np.testing.assert_allclose(data,0,atol=1e-12);np.testing.assert_allclose(total,model)

def test_group_centering_linear_and_no_input_mutation():
 a=np.arange(20.).reshape(10,2);old=a.copy();ind=np.array(['A']*4+['B']*6)
 centered=demean(a,ind)
 np.testing.assert_allclose(centered[:4].mean(axis=0),0,atol=1e-12)
 np.testing.assert_allclose(centered[4:].mean(axis=0),0,atol=1e-12)
 np.testing.assert_array_equal(a,old)
 np.testing.assert_allclose(demean(a[:,0]+a[:,1],ind),centered.sum(axis=1))

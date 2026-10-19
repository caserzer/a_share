import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from regularized_information import WeightedRankDesign,month_weights,probabilities


def test_weighted_ties_missing_and_outside_training_support():
    train=pd.DataFrame({'x':[1.,1.,3.,np.nan],'empty':[np.nan]*4})
    design=WeightedRankDesign().fit(train,np.array([1.,1.,2.,9.]))
    test=pd.DataFrame({'x':[0.,1.,2.,3.,4.,np.nan],'empty':[np.nan,1,2,3,4,5]})
    z=design.transform(test)
    np.testing.assert_allclose(z[:,0],[-1,-.5,0,.5,1,0])
    np.testing.assert_array_equal(z[:,1],[0,0,0,0,0,1])
    np.testing.assert_array_equal(z[:,2],0)
    np.testing.assert_array_equal(z[:,3],[1,0,0,0,0,0])


def test_future_batch_cannot_change_a_prediction_transform():
    train=pd.DataFrame({'x':[1.,2.,3.],'industry_id':['a','a','b']})
    design=WeightedRankDesign().fit(train,np.ones(3))
    first=pd.DataFrame({'x':[2.5],'industry_id':['new']})
    more=pd.concat([first,pd.DataFrame({'x':[1e20,np.nan],'industry_id':['future','a']})],ignore_index=True)
    np.testing.assert_array_equal(design.transform(first),design.transform(more)[:1])
    np.testing.assert_array_equal(design.transform(first)[0,2:],0)
    assert design.names==['x','x__missing','industry_id=a','industry_id=b']


def test_month_replication_does_not_increase_training_weight_or_change_ranks():
    train=pd.DataFrame({'date':['a','a','b'],'x':[1.,2.,4.]})
    repeated=pd.concat([train,train[train.date.eq('a')]],ignore_index=True)
    w=month_weights(train);v=month_weights(repeated)
    assert w.sum()==v.sum()==2
    one=WeightedRankDesign().fit(train[['x']],w).transform(train[['x']])
    two=WeightedRankDesign().fit(repeated[['x']],v).transform(train[['x']])
    np.testing.assert_array_equal(one,two)


def test_probability_reconstruction_respects_class_order_and_softmax_shift():
    x=np.array([[1.,-1.],[0.,2.]])
    coef=np.array([[1.,0.],[0.,1.],[-1.,0.]])
    labels=np.array([4,0,3]);intercept=np.array([0.,.1,-.1])
    p=probabilities(x,coef,intercept,labels)
    np.testing.assert_allclose(p.sum(axis=1),1)
    np.testing.assert_allclose(p,probabilities(x,coef,intercept+100,labels))
    assert p[0,4]>p[0,0] and (p[:,[1,2,5,6]]==0).all()

import sys
from pathlib import Path
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from conditional_forests import training_impute, forest_weights, local_class_distribution
from run_direct_probability import classes, weighted_stats


def test_imputation_cannot_use_future_values_and_keeps_all_missing_columns():
    train=np.array([[1.,np.nan],[3.,np.nan],[np.nan,np.nan]])
    tx,qx,med=training_impute(train,[[1000.,np.nan],[np.nan,2000.]])
    np.testing.assert_array_equal(med,[2,0])
    np.testing.assert_array_equal(tx[2],[2,0,1,1])
    np.testing.assert_array_equal(qx[1],[2,2000,1,0])


@pytest.mark.parametrize('bootstrap',[False,True])
def test_leaf_distribution_matches_classifier_with_unequal_month_weights(bootstrap):
    rng=np.random.default_rng(24); x=rng.normal(size=(160,3)); y=np.resize([-.4,-.1,-.02,0,.02,.1,.4],160)
    weights=np.linspace(.1,8,160); labels=classes(y)
    cls=RandomForestClassifier if bootstrap else ExtraTreesClassifier
    model=cls(n_estimators=5,max_depth=3,min_samples_leaf=8,bootstrap=bootstrap,random_state=24).fit(x,labels,sample_weight=weights)
    query=x[:9]; w=forest_weights(model,x,query,weights); p=model.predict_proba(query)
    a,aw=local_class_distribution(y,w,p)
    np.testing.assert_allclose(w@np.eye(7)[labels],p,atol=1e-12)
    stats=weighted_stats(a,aw,y[:9]);np.testing.assert_allclose(stats.p_up,p[:,4:].sum(axis=1))
    if bootstrap:
        wrong=np.zeros_like(p)
        for tree,sampled in zip(model.estimators_,model.estimators_samples_):
            train_leaf=tree.apply(x);query_leaf=tree.apply(query)
            counts=np.bincount(sampled,minlength=len(x))*weights
            for i,leaf in enumerate(query_leaf):
                wt=counts*(train_leaf==leaf);wrong[i]+=np.bincount(labels,weights=wt,minlength=7)/wt.sum()/5
        assert np.max(np.abs(wrong-p))>1e-3  # Double weighting would be a real error.


def test_local_magnitudes_change_without_changing_class_masses():
    y=np.array([-.4,-.25,.22,.8]); w=np.array([[.45,.05,.45,.05],[.05,.45,.05,.45]])
    p=np.array([[.5,0,0,0,0,0,.5]]*2);a,aw=local_class_distribution(y,w,p)
    assert not np.allclose(a[0],a[1])
    stats=weighted_stats(a,aw,[.1,.1]);np.testing.assert_allclose(stats.p_up,.5)
    np.testing.assert_allclose(stats.p_down,.5)
    assert stats.crps.iloc[0]!=stats.crps.iloc[1]


def test_invalid_empirical_weights_are_rejected():
    with pytest.raises(ValueError): local_class_distribution([.1], [[-1]], [[0,0,0,0,0,1,0]])
    with pytest.raises(ValueError): training_impute([[np.inf]],[[1.]])

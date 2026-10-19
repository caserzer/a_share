import numpy as np
import pytest
from neural_probability_models import PARAMS,fit_network,forward


def test_fixed_budget_weighted_model_rebuilds_from_parameters():
    rng=np.random.default_rng(24);x=rng.normal(size=(140,5));labels=np.tile(np.arange(7),20);weights=np.linspace(.5,1.5,140)
    params={**PARAMS,'batch_size':32}
    model,count=fit_network(x,labels,weights,params);assert model.n_iter_==60 and count==1
    q=rng.normal(size=(10,5));p=forward(q,model.coefs_,model.intercepts_,model.classes_)
    np.testing.assert_allclose(p,model.predict_proba(q),atol=1e-12,rtol=1e-12)
    assert p.shape==(10,7)


def test_forward_preserves_class_order_and_large_logits_are_finite():
    x=np.zeros((2,3));coefs=[np.zeros((3,32)),np.zeros((32,16)),np.zeros((16,7))]
    intercepts=[np.zeros(32),np.zeros(16),np.array([1000,999,998,997,996,995,994])]
    labels=np.array([6,5,4,3,2,1,0]);p=forward(x,coefs,intercepts,labels)
    assert (p.argmax(axis=1)==6).all();np.testing.assert_allclose(p.sum(axis=1),1)


def test_missing_classes_or_invalid_weights_are_rejected():
    with pytest.raises(ValueError):fit_network(np.zeros((7,2)),np.arange(7),[1,1,1,0,1,1,1])
    with pytest.raises(ValueError):fit_network(np.zeros((6,2)),np.arange(6),np.ones(6))

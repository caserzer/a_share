import numpy as np
from neural_probability_models import PARAMS,fit_network


def test_alpha_and_weight_common_scaling_preserves_fit():
    rng=np.random.default_rng(24);x=rng.normal(size=(140,5));y=np.tile(np.arange(7),20);w=np.linspace(.5,1.5,140)
    a,_=fit_network(x,y,w,{**PARAMS,'alpha':16.,'batch_size':32})
    b,_=fit_network(x,y,w*4,{**PARAMS,'alpha':64.,'batch_size':32})
    for u,v in zip(a.coefs_+a.intercepts_,b.coefs_+b.intercepts_):np.testing.assert_allclose(u,v,atol=1e-12,rtol=1e-12)
    np.testing.assert_allclose(a.loss_curve_,b.loss_curve_,atol=1e-12,rtol=1e-12)


def test_stronger_alpha_reduces_parameter_norm_on_fixed_noise():
    rng=np.random.default_rng(24);x=rng.normal(size=(140,5));y=np.tile(np.arange(7),20);w=np.ones(140)
    norms=[]
    for alpha in [1.,16.,64.]:
        model,_=fit_network(x,y,w,{**PARAMS,'alpha':alpha,'batch_size':32})
        norms.append(sum(np.sum(v*v) for v in model.coefs_))
    assert norms[0]>norms[1]>norms[2]

import numpy as np
import pytest
from scipy.special import expit,softmax
from cohort_probability_anchor import sign_anchor,bin_anchor,replace_weights,class_mass


def sample():
    r=np.random.default_rng(24)
    return r.dirichlet(np.ones(7),50),r.dirichlet(np.arange(1,8),50)


def test_sign_anchor_matches_known_cohort_preserves_zero_and_conditional_rank():
    p,b=sample();q,shift,target,_,residual=sign_anchor(p,b)
    up=p[:,4:].sum(axis=1);down=p[:,:3].sum(axis=1);nu=q[:,4:].sum(axis=1);nd=q[:,:3].sum(axis=1)
    np.testing.assert_array_equal(p[:,3],q[:,3]);np.testing.assert_allclose(nu/(nu+nd),expit(np.log(up/down)+shift[0]))
    np.testing.assert_array_equal(np.argsort(up/down),np.argsort(nu/nd))
    np.testing.assert_allclose(q[:,:3]/nd[:,None],p[:,:3]/down[:,None]);assert residual<1e-10
    np.testing.assert_allclose(nu.sum()/(nu+nd).sum(),b[:,4:].sum()/(b[:,:3].sum()+b[:,4:].sum()))


def test_bins_match_targets_and_preserve_cross_stock_pairwise_odds_including_zero_target():
    p,b=sample();b[:,3]=0;b/=b.sum(axis=1,keepdims=True)
    q,factors,target,_,residual=bin_anchor(p,b)
    np.testing.assert_allclose(q.mean(axis=0),target,atol=1e-10);assert (q[:,3]==0).all() and residual<1e-10
    np.testing.assert_allclose(q,softmax(np.log(p)+factors,axis=1),atol=1e-12)
    for a,c in [(0,6),(1,4),(2,5)]:
        delta=np.log(q[:,a]/q[:,c])-np.log(p[:,a]/p[:,c]);np.testing.assert_allclose(delta,delta[0],atol=1e-12)


def test_identity_anchors_preserve_distribution():
    p,_=sample()
    for function in [sign_anchor,bin_anchor]:
        q,_,_,steps,residual=function(p,p);np.testing.assert_allclose(q,p,atol=1e-12);assert steps==0 and residual<1e-12


def test_atom_reweighting_preserves_within_class_shape():
    p,b=sample();atoms=np.tile(np.repeat([-.3,-.1,-.02,0,.02,.1,.3],2),(len(p),1));w=np.repeat(p/2,2,axis=1)
    q,*_=bin_anchor(p,b);updated=replace_weights(atoms,w,p,q)
    np.testing.assert_allclose(class_mass(atoms,updated),q);np.testing.assert_allclose(updated[:,::2],updated[:,1::2])


def test_invalid_or_infeasible_support_is_rejected():
    p,b=sample()
    with pytest.raises(ValueError):sign_anchor(p[:-1],b)
    with pytest.raises(ValueError):bin_anchor(p*2,b)
    p[:,0]=0;p/=p.sum(axis=1,keepdims=True)
    with pytest.raises(ValueError):bin_anchor(p,b)
    p[:,:3]=0;p/=p.sum(axis=1,keepdims=True)
    with pytest.raises(ValueError):sign_anchor(p,b)

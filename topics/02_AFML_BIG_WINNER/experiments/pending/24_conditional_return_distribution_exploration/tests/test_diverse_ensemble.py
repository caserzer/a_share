import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from diverse_ensemble import cdf_distance,mixed_crps,mixture_quadratic,fit_joint_mixture,sign_transform,fit_sign_stack,replace_sign_mass,PENALTY
from probability_recalibration import monthly_weights,calibration_history
from run_prequential_search import combine_distributions
from run_direct_probability import weighted_stats
from run_four_horizons import BIN_NAMES


def sample():
    y=np.tile([-.1,0,.1],8);dates=np.repeat(pd.to_datetime(['2020-01-01','2020-02-01']),[6,18])
    a=np.tile([-.3,-.1,0,.1,.3],(len(y),1))
    bad=np.tile([.1,.2,.1,.4,.2],(len(y),1));good=np.full_like(bad,.05)
    good[np.arange(len(y)),np.tile([1,2,3],8)]=.8
    distributions=[(a,bad),(a,good)];stats=[weighted_stats(*d,y) for d in distributions]
    sign=np.stack([s[['p_down','p_zero','p_up']].to_numpy() for s in stats],axis=1)
    p5=np.stack([s[['p_'+n for n in BIN_NAMES]].to_numpy() for s in stats],axis=1)
    crps=np.column_stack([s.crps for s in stats]);distance=np.zeros((len(y),2,2))
    distance[:,0,1]=distance[:,1,0]=cdf_distance(*distributions[0],*distributions[1])
    return y,dates,distributions,sign,p5,crps,distance


def test_exact_cdf_integral_and_crps_mixture_identity():
    y,dates,ds,sign,p5,c,d=sample();alpha=np.array([.23,.77])
    direct=weighted_stats(*combine_distributions(ds,alpha),y)
    np.testing.assert_allclose(mixed_crps(c,d,alpha),direct.crps,atol=1e-14)
    np.testing.assert_allclose(cdf_distance(np.array([[0.]]),np.ones((1,1)),np.array([[2.]]),np.ones((1,1))),2)
    np.testing.assert_allclose(cdf_distance(*ds[0],*ds[0]),0,atol=1e-30)


def test_joint_quadratic_equals_direct_normalized_scores_and_finds_better_source():
    y,dates,ds,sign,p5,c,d=sample();q,l,scales=mixture_quadratic(sign,p5,c,d,y,dates)
    weight=monthly_weights(dates);prior=np.ones(2)/2;alpha=np.array([.2,.8])
    def direct(x):
        s=weighted_stats(*combine_distributions(ds,x),y)
        return np.mean((s[['brier','multiclass_brier','crps']].to_numpy().T@weight)/scales)+PENALTY*np.square(x-prior).sum()
    np.testing.assert_allclose(direct(alpha)-direct(prior),(alpha@q@alpha+l@alpha)-(prior@q@prior+l@prior),atol=1e-14)
    fitted,_=fit_joint_mixture(sign,p5,c,d,y,dates)
    assert fitted[1]>.9 and direct(fitted)<direct(prior)


def test_normalization_uses_supplied_frozen_baseline_scores():
    y,dates,ds,sign,p5,c,d=sample();frozen=np.tile([.2,.7,.12],(len(y),1))
    _,_,scales=mixture_quadratic(sign,p5,c,d,y,dates,baseline_scores=frozen)
    np.testing.assert_allclose(scales,[.2,.7,.12],atol=1e-14)


def test_sign_identity_and_mass_replacement_preserve_conditional_shape():
    y,dates,ds,sign,*_=sample();target=sign_transform(sign,np.zeros(9))
    np.testing.assert_allclose(target,sign.mean(axis=1))
    a,w=combine_distributions(ds,[.5,.5]);new=np.tile([.2,.3,.5],(len(a),1))
    _,updated=replace_sign_mass(a,w,new);stats=weighted_stats(a,updated,y)
    np.testing.assert_allclose(stats[['p_down','p_zero','p_up']],new)
    for k,mask in enumerate([a<0,a==0,a>0]):
        ratio=np.divide(updated,w,out=np.zeros_like(w),where=w>0)
        for row in range(len(w)):assert np.ptp(ratio[row,mask[row]& (w[row]>0)])<1e-12
    pars,info=fit_sign_stack(sign,y,dates);assert info['penalized_loss']<=info['identity_loss']
    np.testing.assert_allclose(sign_transform(sign,pars).sum(axis=1),1)


def test_unmatured_and_same_date_outcomes_cannot_enter_training():
    frame=pd.DataFrame({'date':pd.to_datetime(['2020-01-01','2020-02-01','2020-03-01']),
        'label_end':pd.to_datetime(['2020-02-01','2020-03-01','2020-04-01']),'actual':[.1,-.2,.3]})
    before=calibration_history(frame,pd.Timestamp('2020-03-01'))
    frame.loc[1:,'actual']=[100.,-100.]
    pd.testing.assert_frame_equal(before,calibration_history(frame,pd.Timestamp('2020-03-01')))
    assert list(before.index)==[0]


def test_no_invented_sign_support_and_no_unobserved_labels():
    with pytest.raises(ValueError):replace_sign_mass(np.array([[-.1,.1]]),np.array([[.5,.5]]),np.array([[.4,.2,.4]]))
    y,dates,ds,sign,p5,c,d=sample();y[0]=np.nan
    with pytest.raises(ValueError):fit_sign_stack(sign,y,dates)
    with pytest.raises(ValueError):fit_joint_mixture(sign,p5,c,d,y,dates)

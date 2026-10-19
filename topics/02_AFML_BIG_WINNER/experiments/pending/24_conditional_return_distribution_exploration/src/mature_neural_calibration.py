"""Chronological calibration of frozen OOS neural forecasts."""
import numpy as np
from scipy.special import expit
from scipy.optimize import brentq
from probability_recalibration import calibration_history,monthly_weights,class_probabilities,fit_calibrator,transform,IDENTITY,PENALTY
from cohort_probability_anchor import validate
from run_direct_probability import classes

WINDOW=36
MIN_MONTHS=12
BOUND=2.


def history_for(predictions,date,mode):
    if mode not in ['sign','bins']:raise ValueError(mode)
    history=calibration_history(predictions,date,WINDOW).copy()
    if mode=='sign':history=history[history.actual.ne(0)]
    return history


def sign_transform(p,shift):
    p=validate(p);up=p[:,4:].sum(axis=1);down=p[:,:3].sum(axis=1);mass=up+down
    if (up<=0).any() or (down<=0).any() or not np.isfinite(shift):raise ValueError('Finite intercept and positive sign support required')
    newup=mass*expit(np.log(up)-np.log(down)+shift);q=p.copy()
    q[:,:3]*=((mass-newup)/down)[:,None];q[:,4:]*=(newup/up)[:,None]
    return validate(q)


def fit_sign(p,labels,dates):
    p=validate(p);y=np.asarray(labels,float);w=monthly_weights(dates)
    if y.shape!=(len(p),) or len(w)!=len(p) or not np.isin(y,[0.,1.]).all():raise ValueError('Binary calibration labels required')
    up=p[:,4:].sum(axis=1);down=p[:,:3].sum(axis=1)
    if (up<=0).any() or (down<=0).any():raise ValueError('Positive sign support required')
    logits=np.log(up)-np.log(down)
    derivative=lambda b:float(np.dot(w,expit(logits+b)-y)+2*PENALTY*b)
    objective=lambda b:float(np.dot(w,np.logaddexp(0,logits+b)-y*(logits+b))+PENALTY*b*b)
    if derivative(-BOUND)>=0:b=-BOUND;steps=0
    elif derivative(BOUND)<=0:b=BOUND;steps=0
    else:
        b,fit=brentq(derivative,-BOUND,BOUND,xtol=1e-12,maxiter=200,full_output=True)
        if not fit.converged:raise RuntimeError('Sign calibration failed')
        steps=fit.iterations
    assert objective(b)<=objective(0.)+1e-10
    return np.array([b]),dict(iterations=int(steps),penalized_loss=objective(b),identity_penalized_loss=objective(0.),gradient=derivative(b))


def apply(p,parameters,mode):
    if mode=='sign':return sign_transform(p,float(parameters[0]))
    if mode=='bins':return transform(p,parameters)
    raise ValueError(mode)


def fit_history(history,mode):
    active=history.date.nunique()>=MIN_MONTHS
    if not active:
        return np.array([0.]) if mode=='sign' else IDENTITY.copy(),False,dict(iterations=0,penalized_loss=np.nan,identity_penalized_loss=np.nan)
    p=class_probabilities(history)
    if mode=='sign':parameters,info=fit_sign(p,history.actual.gt(0).to_numpy(),history.date)
    elif mode=='bins':parameters,info=fit_calibrator(p,classes(history.actual.to_numpy()),history.date)
    else:raise ValueError(mode)
    return parameters,True,info

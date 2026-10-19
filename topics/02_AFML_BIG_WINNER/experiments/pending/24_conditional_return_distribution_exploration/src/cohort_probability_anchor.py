"""Contemporaneous known-prior anchoring; functions accept probabilities only."""
import numpy as np
from scipy.optimize import brentq
from scipy.special import expit,softmax
from run_direct_probability import classes,weighted_stats

TOL=1e-10
MAX_ITER=10000


def validate(p):
    p=np.asarray(p,float)
    if p.ndim!=2 or p.shape[1]!=7 or not len(p) or not np.isfinite(p).all() or (p<0).any():
        raise ValueError('Finite nonnegative seven-class probabilities required')
    if not np.allclose(p.sum(axis=1),1,atol=1e-12,rtol=1e-12):raise ValueError('Rows must sum to one')
    return p


def class_mass(atoms,weights):
    labels=classes(atoms)
    p=np.column_stack([(weights*(labels==k)).sum(axis=1) for k in range(7)])
    return validate(p)


def sign_anchor(p,baseline):
    p=validate(p);baseline=validate(baseline)
    if len(p)!=len(baseline):raise ValueError('Same cohort required')
    up=p[:,4:].sum(axis=1);down=p[:,:3].sum(axis=1);mass=up+down
    bu=baseline[:,4:].sum();bd=baseline[:,:3].sum()
    if (up<=0).any() or (down<=0).any() or bu<=0 or bd<=0:raise ValueError('Positive sign support required')
    target=bu/(bu+bd);logodds=np.log(up)-np.log(down)
    fun=lambda b:float(np.dot(mass,expit(logodds+b))/mass.sum()-target)
    if abs(fun(0.))<=1e-14:shift=0.;iterations=0
    else:
        shift,fit=brentq(fun,-100.,100.,xtol=1e-12,maxiter=200,full_output=True)
        if not fit.converged:raise RuntimeError('Sign anchoring failed')
        iterations=fit.iterations
    newup=mass*expit(logodds+shift);newdown=mass-newup;q=p.copy()
    q[:,:3]*=(newdown/down)[:,None];q[:,4:]*=(newup/up)[:,None]
    residual=abs(q[:,4:].sum()/mass.sum()-target)
    if residual>TOL:raise RuntimeError('Sign target residual exceeds tolerance')
    return validate(q),np.array([shift]),np.array([target]),int(iterations),float(residual)


def bin_anchor(p,baseline):
    p=validate(p);baseline=validate(baseline)
    if len(p)!=len(baseline):raise ValueError('Same cohort required')
    target=baseline.mean(axis=0);active=target>0
    if (p[:,active]<=0).any():raise ValueError('Positive support for every active target class required')
    logs=np.log(p[:,active]);theta=np.zeros(active.sum());q=np.zeros_like(p)
    for iteration in range(MAX_ITER+1):
        q[:,active]=softmax(logs+theta,axis=1);average=q.mean(axis=0)
        residual=float(np.max(np.abs(average-target)))
        if residual<=TOL:
            factors=np.full(7,-np.inf);factors[active]=theta
            return validate(q),factors,target,iteration,residual
        theta+=np.log(target[active])-np.log(average[active]);theta-=theta.mean()
    raise RuntimeError('Seven-class anchoring did not converge')


def anchor(p,baseline,mode):
    if mode=='sign':return sign_anchor(p,baseline)
    if mode=='bins':return bin_anchor(p,baseline)
    raise ValueError(mode)


def replace_weights(atoms,weights,p,target):
    labels=classes(atoms);p=validate(p);target=validate(target)
    if (p<=0).any():raise ValueError('Positive source support required')
    np.testing.assert_allclose(class_mass(atoms,weights),p,atol=1e-12,rtol=1e-12)
    updated=weights*np.take_along_axis(target/p,labels,axis=1)
    np.testing.assert_allclose(updated.sum(axis=1),1,atol=1e-12)
    np.testing.assert_allclose(class_mass(atoms,updated),target,atol=1e-12,rtol=1e-12)
    return updated


def score(prior,atoms,weights,p,target):
    updated=replace_weights(atoms,weights,p,target)
    result=weighted_stats(atoms,updated,prior.actual)
    result['p_down']=target[:,:3].sum(axis=1);result['p_zero']=target[:,3];result['p_up']=target[:,4:].sum(axis=1)
    result['brier']=np.where(prior.actual.notna(),(result.p_up-prior.actual.gt(0))**2,np.nan)
    return result

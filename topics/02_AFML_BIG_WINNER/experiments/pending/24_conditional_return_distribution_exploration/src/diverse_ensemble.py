"""Exact finite-CDF mixing objective and regularized sign-offset stacking."""
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp,softmax
from probability_recalibration import monthly_weights
from run_four_horizons import BINS

PENALTY=.01


def cdf_distance(a,w,b,v):
    """Integral of squared CDF difference, per query, including unequal supports."""
    x=np.concatenate([a,b],axis=1);jumps=np.concatenate([w,-v],axis=1)
    if not np.isfinite(x).all() or not np.isfinite(jumps).all():raise ValueError('Nonfinite distribution')
    if (w<0).any() or (v<0).any():raise ValueError('Negative probability')
    np.testing.assert_allclose(w.sum(axis=1),1,atol=1e-12);np.testing.assert_allclose(v.sum(axis=1),1,atol=1e-12)
    order=np.argsort(x,axis=1,kind='stable');x=np.take_along_axis(x,order,axis=1)
    cdf=np.take_along_axis(jumps,order,axis=1).cumsum(axis=1)
    return (np.square(cdf[:,:-1])*np.diff(x,axis=1)).sum(axis=1)


def mixed_crps(component_scores,distances,coefficients):
    return component_scores@coefficients-.5*np.einsum('i,nij,j->n',coefficients,distances,coefficients)


def mixture_quadratic(sign,p5,scores,distances,y,dates,baseline_scores=None):
    weights=monthly_weights(dates);y=np.asarray(y);up=(y>0).astype(float)
    target=np.eye(5)[np.searchsorted(BINS,y,side='right')]
    pu=sign[:,:,2];m=pu.shape[1];prior=np.full(m,1/m)
    scales=np.array([np.dot(weights,(pu[:,0]-up)**2),np.dot(weights,((p5[:,0]-target)**2).sum(axis=1)),np.dot(weights,scores[:,0])])
    if baseline_scores is not None:scales=np.asarray(baseline_scores).T@weights
    if not np.isfinite(scales).all() or (scales<=1e-8).any():raise ValueError('Invalid mature baseline scale')
    q1=np.einsum('ni,nj,n->ij',pu,pu,weights);l1=-2*np.einsum('ni,n,n->i',pu,up,weights)
    q5=np.einsum('nic,njc,n->ij',p5,p5,weights);l5=-2*np.einsum('nic,nc,n->i',p5,target,weights)
    q=(q1/scales[0]+q5/scales[1]-.5*np.einsum('nij,n->ij',distances,weights)/scales[2])/3+PENALTY*np.eye(m)
    linear=(l1/scales[0]+l5/scales[1]+np.einsum('ni,n->i',scores,weights)/scales[2])/3-2*PENALTY*prior
    return q,linear,scales


def fit_joint_mixture(sign,p5,scores,distances,y,dates,baseline_scores=None):
    y=np.asarray(y,dtype=float)
    if not np.isfinite(y).all():raise ValueError('Unobserved labels in training')
    q,linear,scales=mixture_quadratic(sign,p5,scores,distances,y,dates,baseline_scores);m=len(linear);prior=np.full(m,1/m)
    def objective(c):return float(c@q@c+linear@c),2*q@c+linear
    fit=minimize(objective,prior,jac=True,method='SLSQP',bounds=[(0,1)]*m,
        constraints=[dict(type='eq',fun=lambda c:c.sum()-1,jac=lambda c:np.ones(m))],options=dict(maxiter=500,ftol=1e-12))
    if not fit.success:raise RuntimeError(f'Joint mixture failed: {fit.message}')
    c=np.maximum(fit.x,0);c/=c.sum()
    assert objective(c)[0]<=objective(prior)[0]+1e-8
    return c,dict(iterations=int(fit.nit),objective_without_constant=objective(c)[0],uniform_objective_without_constant=objective(prior)[0],
                  brier_scale=scales[0],five_bin_scale=scales[1],crps_scale=scales[2])


def sign_design(sign):
    sign=np.asarray(sign,dtype=float)
    if not np.isfinite(sign).all() or (sign<0).any():raise ValueError('Invalid sign probabilities')
    np.testing.assert_allclose(sign.sum(axis=2),1,atol=1e-12)
    scores=np.clip(np.log(np.clip(sign[:,:,2],1e-8,1))-np.log(np.clip(sign[:,:,0],1e-8,1)),-6,6)
    pooled=sign.mean(axis=1)
    if (pooled<=0).any():raise ValueError('Uniform distribution lacks a sign; no invented support')
    return np.column_stack([np.ones(len(sign)),scores]),np.log(pooled)


def sign_transform(sign,parameters):
    x,offset=sign_design(sign)
    return softmax(offset+x@np.asarray(parameters).reshape(x.shape[1],3),axis=1)


def fit_sign_stack(sign,y,dates):
    y=np.asarray(y,dtype=float)
    if not np.isfinite(y).all():raise ValueError('Unobserved labels in training')
    x,offset=sign_design(sign);weights=monthly_weights(dates);labels=np.where(y<0,0,np.where(y==0,1,2));target=np.eye(3)[labels]
    def objective(pars):
        matrix=pars.reshape(x.shape[1],3);logits=offset+x@matrix
        loss=np.dot(weights,logsumexp(logits,axis=1)-logits[np.arange(len(y)),labels])+PENALTY*np.dot(pars,pars)
        gradient=x.T@((softmax(logits,axis=1)-target)*weights[:,None])+2*PENALTY*matrix
        return float(loss),gradient.ravel()
    identity=np.zeros(x.shape[1]*3)
    fit=minimize(objective,identity,jac=True,method='L-BFGS-B',bounds=[(-1.5,1.5)]*3+[(-2,2)]*(len(identity)-3),
                 options=dict(maxiter=500,ftol=1e-12,gtol=1e-7))
    if not fit.success:raise RuntimeError(f'Sign stacking failed: {fit.message}')
    assert fit.fun<=objective(identity)[0]+1e-8
    return fit.x,dict(iterations=int(fit.nit),penalized_loss=float(fit.fun),identity_loss=objective(identity)[0])


def replace_sign_mass(atoms,weights,target):
    if not np.isfinite(target).all() or (target<0).any():raise ValueError('Invalid target mass')
    labels=np.where(atoms<0,0,np.where(atoms==0,1,2))
    mass=np.column_stack([(weights*(labels==k)).sum(axis=1) for k in range(3)])
    if (mass<=0).any():raise ValueError('Missing sign support')
    np.testing.assert_allclose(target.sum(axis=1),1,atol=1e-12)
    updated=weights/np.take_along_axis(mass,labels,axis=1)*np.take_along_axis(target,labels,axis=1)
    np.testing.assert_allclose(updated.sum(axis=1),1,atol=1e-12)
    return atoms,updated

"""Long-only constrained proxy targets and explicit-fee synthetic qfq-unit ledger."""
import sys
import numpy as np
from scipy import sparse
from common import PRIVATE
sys.path.insert(0,str(PRIVATE/'vendor'))
import osqp

def rank_target(scores,b,active=.1):
 ok=np.isfinite(scores);z=np.zeros(len(b))
 if ok.sum()>1:
  from scipy.stats import rankdata
  r=rankdata(scores[ok],method='average');z[ok]=r-r.mean()
 if np.abs(z).sum()>1e-12:return b+2*active*z/np.abs(z).sum()
 return b.copy()

def project(q,b,current,buy,sell,member,industry,initial=False):
 n=len(b);m=n+1;q=np.r_[q,0.];b=np.r_[b,0.];current=np.asarray(current)
 def solve(relax):
  lo=np.zeros(m);hi=np.ones(m)
  if not relax:
   lo[:n]=np.maximum(0,b[:n]-.005);hi[:n]=b[:n]+.005
  hi[:n][~member]=0
  # Trade constraints override membership/active caps, so legacy shares are retained.
  lo[:n][~sell]=np.maximum(lo[:n][~sell],current[:n][~sell]);hi[:n][~sell]=np.maximum(hi[:n][~sell],current[:n][~sell])
  hi[:n][~buy]=np.minimum(hi[:n][~buy],current[:n][~buy]);lo[:n][~buy]=np.minimum(lo[:n][~buy],current[:n][~buy])
  A=[sparse.hstack([sparse.eye(m),sparse.csc_matrix((m,m))]),sparse.csc_matrix(np.r_[np.ones(m),np.zeros(m)][None,:])];lower=[lo,np.array([1.])];upper=[hi,np.array([1.])]
  if not relax:
   for g in sorted(set(industry)):
    row=np.r_[(industry==g).astype(float),0.];base=row@b
    A.append(sparse.csc_matrix(np.r_[row,np.zeros(m)][None,:]));lower.append(np.array([base-.02]));upper.append(np.array([base+.02]))
  eye=sparse.eye(m)
  A.extend([sparse.hstack([-eye,eye]),sparse.hstack([eye,eye])]);lower.extend([-current,current]);upper.extend([np.full(m,np.inf),np.full(m,np.inf)])
  if not initial and not relax:
   A.append(sparse.csc_matrix(np.r_[np.zeros(m),np.ones(m)][None,:]));lower.append(np.array([-np.inf]));upper.append(np.array([.4]))
  solver=osqp.OSQP();solver.setup(P=sparse.diags(np.r_[np.full(m,2.),np.zeros(m)],format='csc'),q=np.r_[-2*q,np.zeros(m)],A=sparse.vstack(A,format='csc'),l=np.concatenate(lower),u=np.concatenate(upper),verbose=False,eps_abs=1e-8,eps_rel=1e-8,max_iter=10000,polishing=True)
  r=solver.solve()
  if r.info.status_val not in (1,2):return None,r.info.status
  w=r.x[:m]
  if np.min(w)<-1e-6 or abs(w.sum()-1)>1e-6:return None,'numerical_failure'
  # Numerical cleanup only, bounded at solver tolerance.
  w=np.maximum(w,0);w/=w.sum();return w,r.info.status
 w,status=solve(False);relaxed=False
 if w is None:w,status=solve(True);relaxed=True
 if w is None:return current.copy(),dict(solver=status,relaxed=True,no_order=True)
 return w,dict(solver=status,relaxed=relaxed,no_order=False,active_share=.5*np.abs(w-b).sum(),stock_deviation=float(np.max(np.abs(w[:n]-b[:n]))),target_turnover=.5*np.abs(w-current).sum())

def trade(units,cash,prices,target,buy,sell,buyfee,sellfee):
 held=units>1e-14
 if np.any(held & (~np.isfinite(prices)|(prices<=0))):raise ValueError('HELD_OPEN_VALUATION_UNKNOWN')
 value=np.where(held,units*np.nan_to_num(prices),0.);nav=cash+value.sum()
 delta=target[:-1]*nav-value
 sells=np.where(sell,np.maximum(-delta,0),0.);sells=np.minimum(sells,value)
 cash+=sells.sum()*(1-sellfee)
 buys=np.where(buy,np.maximum(delta,0),0.);cost=buys.sum()*(1+buyfee)
 if cost>cash and cost>0:buys*=cash/cost
 cash-=buys.sum()*(1+buyfee)
 change=np.divide(buys-sells,prices,out=np.zeros(len(units)),where=np.isfinite(prices)&(prices>0));new=units+change
 assert cash>=-1e-9 and new.min()>=-1e-9
 fees=buys.sum()*buyfee+sells.sum()*sellfee
 return np.maximum(new,0),max(cash,0),dict(buy=buys.sum()/nav,sell=sells.sum()/nav,fees=fees,pretrade_nav=nav,unfilled_buy=np.where(~buy,np.maximum(delta,0),0).sum()/nav,unfilled_sell=np.where(~sell,np.maximum(-delta,0),0).sum()/nav)

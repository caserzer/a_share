"""Accounting identities and state boundaries, independent of outcome significance."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import unittest
import numpy as np
from e1_timing_mechanism import state
from e1_return_attribution import log_link,wealth_scale
from portfolio import trade

class TimingTests(unittest.TestCase):
 def test_four_states_zero_missing(self):
  self.assertEqual(state([.2,.2,-.2,-.2,0,np.nan],[ -.1,.1,-.1,.1,.1,.1]).tolist(),['UP_DOWN','UP_UP','DOWN_DOWN','DOWN_UP','ZERO','UNKNOWN'])
 def test_sign_nonoverlap(self):
  # A positive 60-day return can coexist with a negative nonoverlapping trend.
  old,minus5,now=100.,90.,110.
  self.assertEqual(state([minus5/old-1],[now/minus5-1])[0],'DOWN_UP')
 def test_fee_accounting_and_no_borrowing(self):
  u=np.array([1.,1.,0.]);px=np.array([10.,20.,30.]);target=np.array([0.,.1,.9,0.])
  full,c,_=trade(u,0.,px,target,np.ones(3,bool),np.ones(3,bool),.001,.002)
  dq=full-u;cash=0.;x=u.copy()
  for mask in [dq<0,dq>0]:
   value=dq[mask]*px[mask];cash-=value.sum()+np.maximum(value,0).sum()*.001+np.maximum(-value,0).sum()*.002;x[mask]+=dq[mask]
   self.assertGreaterEqual(cash,-1e-10)
  np.testing.assert_allclose(x,full);self.assertAlmostEqual(c,cash)
 def test_segment_identity_with_cost(self):
  weight=.3;p0,pd,px=10.,12.,11.;bf=.001
  u0=weight/p0/(1+bf);ud=weight/pd/(1+bf)
  early=u0*(pd-p0)-u0*p0*bf;shared=(u0-ud)*(px-pd);delayed_fee=ud*pd*bf
  gap=(u0*(px-p0)-u0*p0*bf)-(ud*(px-pd)-ud*pd*bf)
  self.assertAlmostEqual(gap,early+shared+delayed_fee)
 def test_log_contribution_closure(self):
  p=np.array([.1,-.2,.03]);b=np.array([-.1,.1,0.]);lp=log_link(p,b)*(p-b)
  pp=np.prod(1+p);bb=np.prod(1+b)
  self.assertAlmostEqual(lp.sum()*wealth_scale(pp,bb),100*(pp-bb))

if __name__=='__main__':unittest.main()

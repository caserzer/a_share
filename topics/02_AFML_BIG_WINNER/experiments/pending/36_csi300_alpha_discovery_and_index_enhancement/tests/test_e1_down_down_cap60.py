import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from e1_down_down_cap60 import cap_trade,CAP
class Cap60Tests(unittest.TestCase):
 def test_cash_reserve_and_post_fee_limit(self):
  target=np.array([CAP,CAP,1-2*CAP]);px=np.array([10.,20.]);u,c,i,_,w=cap_trade(np.zeros(2),1.,px,target,np.ones(2,bool),np.ones(2,bool))
  np.testing.assert_allclose(w,np.array([CAP,CAP]),atol=1e-12)
  self.assertAlmostEqual(c/(c+u@px),1-2*CAP,places=12)
  self.assertAlmostEqual(c+u@px+i['fees'],1.,places=12)
 def test_zero_selection_liquidates(self):
  u,c,i,_,w=cap_trade(np.array([.05]),.5,np.array([10.]),np.array([0.,1.]),np.ones(1,bool),np.ones(1,bool))
  self.assertEqual(u[0],0);self.assertAlmostEqual(c,.999);self.assertEqual(w[0],0)
 def test_blocked_legacy_not_fabricated_sale(self):
  u,c,i,_,w=cap_trade(np.array([.05,0.]),.5,np.array([10.,10.]),np.array([0.,CAP,1-CAP]),np.ones(2,bool),np.array([False,True]))
  self.assertEqual(u[0],.05);self.assertGreater(w[0],CAP);self.assertLessEqual(w[1],CAP+1e-12);self.assertGreater(c,0)
 def test_blocked_buy_keeps_cash(self):
  u,c,_,_,w=cap_trade(np.zeros(1),1.,np.array([10.]),np.array([CAP,1-CAP]),np.array([False]),np.array([True]))
  self.assertEqual(c,1.);self.assertEqual(u[0],0)
if __name__=='__main__':unittest.main()

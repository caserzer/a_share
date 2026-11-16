import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np,pytest
from portfolio import trade,rank_target,project

def test_cash_fee_and_blocked_order():
 u,c,r=trade(np.zeros(2),1.,np.array([2.,4.]),np.array([.5,.5,0.]),np.array([True,False]),np.ones(2,bool),.001,.002)
 assert u[1]==0 and c>0 and r['unfilled_buy']==.5
 assert abs(c+(u*np.array([2.,4.])).sum()+r['fees']-1)<1e-12
 u2,c2,r2=trade(u,c,np.array([3.,4.]),np.array([0.,1.,0.]),np.ones(2,bool),np.array([False,True]),.001,.002)
 assert u2[0]==u[0] and r2['unfilled_sell']>0

def test_missing_held_price_is_not_carried():
 with pytest.raises(ValueError,match='VALUATION_UNKNOWN'):trade(np.array([1.]),0.,np.array([np.nan]),np.array([1.,0.]),np.ones(1,bool),np.ones(1,bool),0,0)

def test_equal_scores_and_unscored_neutral():
 b=np.ones(4)/4;np.testing.assert_allclose(rank_target(np.ones(4),b),b)
 q=rank_target(np.array([1.,2.,3.,np.nan]),b);assert q[3]==b[3];assert abs(q.sum()-1)<1e-12

def test_projection_turnover_and_legacy():
 n=30;b=np.ones(n)/n;old=np.r_[b,0.];buy=np.ones(n,bool);sell=buy.copy();member=buy.copy();member[0]=False;sell[0]=False
 q=rank_target(np.arange(n),b);w,r=project(q,b,old,buy,sell,member,np.array(['one']*n))
 assert abs(w.sum()-1)<1e-7 and w.min()>=0;assert abs(w[0]-old[0])<1e-6
 assert .5*np.abs(w-old).sum()<=.200001

def test_initial_build_cost_scales_buys():
 u,c,r=trade(np.zeros(1),1.,np.ones(1),np.array([1.,0.]),np.ones(1,bool),np.ones(1,bool),.01,.02)
 assert abs(u[0]-1/1.01)<1e-12;assert c<1e-12

def test_opening_state_excludes_later_intraday_information():
 from execution_status import opening_suspension
 assert opening_suspension(None) is True
 assert opening_suspension('09:30-10:00') is True
 assert opening_suspension('09:31-10:01') is False
 assert opening_suspension('13:00-15:00') is False
 assert opening_suspension('unparsed') is None

def test_full_liquidation_leaves_no_dust():
 u=np.array([.123456789]);price=np.array([7.23456789]);target=np.array([0.,1.])
 v,c,r=trade(u,0.,price,target,np.ones(1,bool),np.ones(1,bool),0,.002)
 assert v[0]==0

def test_off_universe_buy_gate_even_if_solver_returns_dust(monkeypatch):
 import pandas as pd
 from types import SimpleNamespace
 import backtest
 days=pd.bdate_range('2021-01-01',periods=3);symbols=pd.Index(['a','b','c']);member=np.array([True,True,False]);b=np.array([.5,.5,0.]);ones=np.ones(3,bool)
 inp=SimpleNamespace(days=days,symbols=symbols,n=3,o=np.ones((3,3)),c=np.ones((3,3)),raw=np.ones((3,3)))
 inp.context=lambda si,ei:(member,b,'RECONSTRUCTED_PROXY',days[0],np.array(['x']*3),ones,ones,ones)
 monkeypatch.setattr(backtest,'project',lambda *a,**k:(np.array([.5,.5-1e-12,1e-12,0.]),{}))
 scores=pd.DataFrame({'signal_date':[days[0]]*3,'instrument':symbols,'score':[1.,2.,np.nan]})
 daily,orders,holds,fail=backtest.run_account(inp,scores,'B','zero','weekly','E2','expanding')
 assert not fail
 assert all(o['units_after']==0 for o in orders if o['instrument']=='c')
 assert all(h[1]!='c' for h in holds)

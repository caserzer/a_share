import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from alpha_economics import matched_selection,event_path,run_account,date_schedule,topk

class Fixture:
 def __init__(self):
  self.n=2;self.days=pd.bdate_range('2021-01-01',periods=30);self.symbols=np.array(['A','B'])
  self.o=np.repeat((1+np.arange(30)*.01)[:,None],2,axis=1);self.c=self.o.copy();self.block_exit=False;self.block_entry=False
 def context(self,si,ei):
  buy=np.array([not self.block_entry,True]);sell=np.array([not(self.block_exit and ei==11),True])
  return np.ones(2,bool),None,None,None,np.array(['I','I']),buy,sell,np.ones(2,bool)


def test_equal_cardinality_and_frozen_risk_bounds():
 rng=np.random.default_rng(2026);n=60;k=12
 z=rng.normal(size=(n,4));ind=np.column_stack([np.arange(n)%2==0,np.arange(n)%2==1]).astype(float)
 base=np.zeros(n);base[:k]=1
 result,info=matched_selection(rng.normal(size=n),z,ind,base,k)
 assert result is not None
 assert result.sum()==k
 assert np.max(np.abs(z.T@(result-base)/k))<=.25+1e-7
 assert np.max(np.abs(ind.T@(result-base)/k))<=.02+1e-7


def test_event_endpoints_and_entry_fee_only_once():
 inp=Fixture();rows,path=event_path(inp,0,np.array([1.,0.,0.]),.001,.002)
 units=1/(inp.o[1,0]*1.001)
 assert rows[0]['exit_date']==inp.days[6]
 assert rows[1]['exit_date']==inp.days[11]
 assert rows[2]['exit_date']==inp.days[21]
 assert path[0]['mark']==pytest.approx(1/1.001)
 assert rows[1]['net_return']==pytest.approx(units*inp.o[11,0]*.998-1)
 assert (path[5]['mark']-1)+(path[10]['mark']-path[5]['mark'])+(path[20]['mark']-path[10]['mark'])==pytest.approx(path[20]['mark']-1)


def test_unsellable_endpoint_is_not_assumed_exit():
 inp=Fixture();inp.block_exit=True
 rows,path=event_path(inp,0,np.array([1.,0.,0.]),.001,.002)
 assert np.isnan(rows[1]['net_return']) and rows[1]['reason']=='EXIT_NOT_FULLY_TRADEABLE'
 assert rows[1]['unsold_weight']==pytest.approx(1.)
 assert np.isfinite(path[10]['mark'])


def test_unbuyable_target_stays_cash_without_replacement():
 inp=Fixture();inp.block_entry=True
 rows,path=event_path(inp,0,np.array([1.,0.,0.]),.001,.002)
 assert rows[1]['net_return']==0 and rows[1]['unfilled_buy']==1
 assert rows[1]['actual_holdings']==0


def test_unknown_held_price_stops_account():
 inp=Fixture();inp.c[8,0]=np.nan
 daily,orders,fail=run_account(inp,{inp.days[0]:np.array([1.,0.,0.])},[inp.days[0]],(.001,.002))
 assert daily.date.iloc[-1]==inp.days[7]
 assert fail[0]['reason']=='HELD_CLOSE_VALUATION_UNKNOWN'


def test_biweekly_uses_calendar_not_observed_row_number():
 dates=pd.to_datetime(['2021-01-08','2021-01-22','2021-01-29','2021-02-05'])
 assert list(date_schedule(dates,'2w'))==list(dates[[0,1,3]])
 assert list(date_schedule(dates,'1m'))==list(dates[[0,3]])


def test_rank_ties_deterministic():
 assert list(topk(np.zeros(4),2,['D','B','A','C']))==[3,0]

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from q5_entry_matched_controls import buckets,allocation

def test_matched_budget_preserves_industry_without_buying_held_names():
    budget=np.array([30.,0.,0.,20.,0.]);eligible=np.array([True,True,False,True,True]);industry=np.array(['A','A','A','B','B'])
    got=allocation(budget,eligible,industry)
    assert np.allclose(got,[15.,15.,0.,10.,10.]) and got.sum()==budget.sum()
    market=allocation(budget,eligible);assert np.allclose(market,[12.5,12.5,0,12.5,12.5])

def test_price_buckets_keep_unknown_and_singletons_explicit():
    industry=np.array(['A','A','A','A','A','B']);past=np.array([.2,.1,np.nan,.3,.1,.7]);eligible=np.ones(6,bool);symbols=np.array(['A','B','C','D','E','F'])
    keys=buckets(industry,past,eligible,symbols)
    assert keys[2]=='A|UNKNOWN_RETURN' and keys[5]=='B|Q0'
    assert keys[1]=='A|Q0' and keys[4]=='A|Q1'
    budget=np.array([0.,0.,10.,0.,0.,20.]);got=allocation(budget,eligible,keys)
    assert np.allclose(got,budget)


def test_disjoint_peer_match_keeps_unmatched_group_unchanged():
    from q5_entry_disjoint_controls import disjoint_allocation
    budget=np.array([10.,0.,20.,5.,0.]);groups=np.array(['A','A','B','C','C'])
    got,matched=disjoint_allocation(budget,groups)
    assert np.allclose(got,[0.,10.,20.,0.,5.])
    assert np.array_equal(matched,[True,False,False,True,False])
    assert got.sum()==budget.sum() and not (got[matched]>0).any()

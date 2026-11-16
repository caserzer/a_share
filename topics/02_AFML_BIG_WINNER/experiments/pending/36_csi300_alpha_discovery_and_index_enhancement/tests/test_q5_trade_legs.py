import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from q5_trade_leg_investigation import triplet

def test_losing_old_and_winning_new_are_separate_additive_legs():
    states,_=triplet(np.array([1.,0.]),0.,np.array([100.,100.]),np.array([0.,1.,0.]),np.ones(2,bool),np.ones(2,bool),0.,0.)
    nav={k:c+u@np.array([90.,110.]) for k,(u,c) in states.items()}
    assert np.isclose(nav['H'],90) and np.isclose(nav['S'],100) and np.isclose(nav['F'],110)
    assert np.isclose(nav['S']-nav['H'],10) and np.isclose(nav['F']-nav['S'],10)

def test_sells_only_holds_real_cash_and_respects_untradeable_old():
    states,_=triplet(np.array([1.,0.]),0.,np.array([100.,100.]),np.array([0.,1.,0.]),np.ones(2,bool),np.array([False,True]),.001,.002)
    for u,c in states.values():assert np.allclose(u,[1.,0.]) and c==0
    states,_=triplet(np.array([1.,0.]),0.,np.array([100.,100.]),np.array([0.,1.,0.]),np.ones(2,bool),np.ones(2,bool),.001,.002)
    assert np.allclose(states['S'][0],[0.,0.]) and np.isclose(states['S'][1],99.8)
    assert states['F'][1]>=0 and np.isclose(states['F'][0][1],99.8/100.1)

import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from e1_four_state_odds import stats

def test_payoff_is_conditional_mean_ratio_and_zero_in_denominator():
    s=stats([.04,.02,-.01,0.])
    assert s['months']==4 and s['wins']==2 and s['losses']==1 and s['zeros']==1
    assert s['win_rate']==.5
    assert np.isclose(s['payoff_ratio'],3.)
    assert np.isclose(s['mean_return'],s['wins']/s['months']*s['mean_win']-s['losses']/s['months']*s['mean_loss'])

def test_all_cash_does_not_invent_payoff():
    s=stats([0.,0.])
    assert s['win_rate']==0 and s['zeros']==2
    assert np.isnan(s['payoff_ratio'])

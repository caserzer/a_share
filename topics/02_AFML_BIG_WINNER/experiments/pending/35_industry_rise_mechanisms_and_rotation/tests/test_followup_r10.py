import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from followup_r10 import path_metrics,exit_economics

def test_next_close_path_drawdown_and_unknown_tail():
    dates=pd.date_range('2020-01-01',periods=8)
    g=pd.DataFrame(dict(era='test',level='L3',industry_code='a',block=0,date=dates,
        day_i=range(8),nav=[999,100,120,110,105,115,110,121],breadth21=.5))
    result=path_metrics(g,pd.Series(100.,index=dates))
    assert np.isclose(result.return5.iloc[0],.1)
    assert np.isclose(result.drawdown5.iloc[0],-.125)
    assert result.min_from_entry5.iloc[0]==0
    assert result.entry_date.iloc[0]==dates[1]
    assert result.maturity5.iloc[0]==dates[6]
    assert result.return5.iloc[2:].isna().all()
    assert result.return20.isna().all()

def test_relative_outperformance_does_not_avoid_absolute_loss():
    cash,market=exit_economics(-.1,-.2,0)
    assert np.isclose(cash,.1)
    assert np.isclose(market,-.1)

def test_switching_cost_can_reverse_small_relative_advantage():
    cash,market=exit_economics(.1,.101,.002)
    assert cash<0 and market<0

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from experiment9 import add_context
from context9 import ADDED


def test_future_market_and_peer_prices_do_not_change_historical_context(monkeypatch):
    days=pd.bdate_range('2020-01-01',periods=120)
    prices=pd.DataFrame({'close':100*np.exp(np.sin(np.arange(120)/20)*.2)},index=days)
    base=pd.DataFrame({'date':[days[60]]*2,'level':['L2']*2,'benchmark':['CSI300']*2,'threshold':[.1]*2,
        'candidate_low_date':[days[40],days[50]],'state_direction':[1,-1],'state_eligible':[1,1],
        'excess21':[.1,-.02],'excess63':[.2,-.1],'breadth21':[.8,.3]})
    monkeypatch.setattr(pd,'read_parquet',lambda path:prices)
    before=add_context(base)
    prices.loc[days[61]:,'close']*=100
    extra=base.copy();extra['date']=days[90];extra['excess21']=[200,-100]
    after=add_context(pd.concat([base,extra],ignore_index=True)).iloc[:2]
    pd.testing.assert_frame_equal(before[ADDED],after[ADDED])


def test_current_peer_information_is_grouped_by_date_and_level(monkeypatch):
    days=pd.bdate_range('2020-01-01',periods=90)
    monkeypatch.setattr(pd,'read_parquet',lambda path:pd.DataFrame({'close':np.linspace(100,110,90)},index=days))
    x=pd.DataFrame({'date':[days[60]]*4,'level':['L2','L2','L3','L3'],'benchmark':['CSI300']*4,'threshold':[.1]*4,
        'candidate_low_date':[days[40]]*4,'state_direction':[1,1,-1,-1],'state_eligible':[1,1,0,0],
        'excess21':[.1,.2,-.1,-.2],'excess63':[.1,.2,-.1,-.2],'breadth21':[.8,.9,.2,.3]})
    r=add_context(x)
    assert r.loc[r.level.eq('L2'),'cross_up'].eq(1).all()
    assert r.loc[r.level.eq('L3'),'cross_up'].eq(0).all()

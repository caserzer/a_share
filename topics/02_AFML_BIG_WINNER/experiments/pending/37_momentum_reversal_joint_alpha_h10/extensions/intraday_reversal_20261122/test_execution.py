from types import SimpleNamespace
import pandas as pd
import numpy as np
import pytest

from prepare import EP  # activates EP37's frozen engine import path
from accounts import account
from execution import net_account


@pytest.mark.parametrize("renew,blocked,rate",[(True,False,.001),(False,False,.001),(True,True,.001),(True,False,0.)])
def test_same_open_rollover(renew,blocked,rate):
    days=pd.bdate_range("2020-01-01",periods=22)
    prices=np.ones((22,2))
    market=SimpleNamespace(days=days,symbols=pd.Index(["A","B"]),n=2,o=prices,
                           buy=prices.astype(bool),sell=prices.astype(bool),members=prices.astype(bool),marks={"flat":(prices,prices)})
    if blocked:
        market.sell[11,0]=False
    plans=pd.DataFrame(dict(entry_idx=[1,11],instrument=["A","A" if renew else "B"],weight=[1.,1.]))
    d,orders,info=net_account(market,plans,21,"flat",rate,rate*2)
    f,_,_,_=account(market,plans,21,"flat",rate,rate*2,"full",False)
    assert info["terminal_liquidated"] and info["valuation_complete"]
    if not renew or blocked or not rate:
        assert np.allclose(d.nav,pd.DataFrame(f).nav)
    else:
        assert d.nav.iloc[-1]>f[-1]["nav"] and orders.overlap.sum()>0
    if blocked:
        assert not orders.date.eq(days[11]).any() and orders.loc[orders.date.eq(days[12]),"sell"].sum()>0
    assert (orders.buy*orders.sell).sum()==0

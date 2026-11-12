"""Past-only price evidence. No process registry, future labels or signal edits."""
import numpy as np
import pandas as pd


def trailing_evidence(group, market):
    g=group.sort_index();v=pd.to_numeric(g.nav,errors='coerce');b=g.block
    valid=np.isfinite(v)&v.gt(0)&b.notna();result=pd.DataFrame(index=g.index)
    for h in [5,20,60]:
        supported=valid.astype(int).rolling(h+1,min_periods=h+1).sum().eq(h+1)&b.eq(b.shift(h))
        supported &= b.rolling(h+1,min_periods=h+1).min().eq(b.rolling(h+1,min_periods=h+1).max())
        supported &= pd.Series(g.index,index=g.index).sub(pd.Series(g.index,index=g.index).shift(h)).eq(h)
        absolute=(v/v.shift(h)-1).where(supported)
        m=market.reindex(g.index);mv=np.isfinite(m)&m.gt(0)
        ms=mv.astype(int).rolling(h+1,min_periods=h+1).sum().eq(h+1)
        market_return=(m/m.shift(h)-1).where(ms)
        result[f'absolute_return_{h}']=absolute
        result[f'market_return_{h}']=market_return
        result[f'excess_return_{h}']=absolute-market_return
    result['current_price_known']=valid
    return result


def entry_evidence(group,market,entry_day,day):
    if entry_day is None:return None,None,None,'NO_OBSERVATION_ID'
    if entry_day>day:raise ValueError('entry must not be in future')
    g=group.reindex(range(entry_day,day+1));v=pd.to_numeric(g.nav,errors='coerce')
    if not (np.isfinite(v).all() and v.gt(0).all() and g.block.notna().all() and g.block.nunique()==1):
        return None,None,None,'UNKNOWN_PRICE_PATH'
    absolute=float(v.iloc[-1]/v.iloc[0]-1);m=market.reindex(g.index)
    if not (np.isfinite(m).all() and m.gt(0).all()):return absolute,None,None,'UNKNOWN_MARKET_PATH'
    mr=float(m.iloc[-1]/m.iloc[0]-1)
    return absolute,mr,absolute-mr,'KNOWN_HISTORICAL_PROXY'

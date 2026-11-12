"""Only historical price projections are accepted; no evaluation-table imports."""
import numpy as np
import pandas as pd

PRICE_COLUMNS=['era','industry_code','date','day_i','nav','block','status','stale_members','boundary_proxy']


def features(price_rows):
    if set(price_rows.columns)!=set(PRICE_COLUMNS):
        raise ValueError('price-only input schema required; reject extra/future fields')
    if price_rows.duplicated(['era','industry_code','date']).any():raise ValueError('duplicate input identity/date')
    parts=[]
    for _,g in price_rows.groupby(['era','industry_code'],sort=True):
        g=g.sort_values('date').copy()
        valid=g.nav.notna()&g.nav.gt(0)
        eligible=valid.rolling(61,min_periods=61).sum().eq(61)&g.block.notna()&g.block.eq(g.block.shift(60))&g.day_i.sub(g.day_i.shift(60)).eq(60)
        score=(g.nav/g.nav.shift(20)-1).where(eligible)
        z=g[['era','industry_code','date','day_i','status']].rename(columns={'status':'price_status'}).copy()
        z['eligible']=eligible.fillna(False);z['score']=score
        z['history_proxy']=(g.stale_members.gt(0)|g.boundary_proxy.eq(True)).rolling(61,min_periods=61).max().where(eligible)
        z['input_asof']=z.date
        parts.append(z)
    return pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=['era','industry_code','date','day_i','price_status','eligible','score','history_proxy','input_asof'])


def complete_week_reviews(calendar_dates,asof_date):
    dates=pd.DatetimeIndex(calendar_dates).sort_values().unique()
    periods=dates.to_period('W-SUN')
    complete=periods.end_time.normalize()<pd.Timestamp(asof_date).normalize()
    table=pd.DataFrame({'date':dates[complete],'week':periods[complete]})
    return pd.DatetimeIndex(table.groupby('week').date.max())

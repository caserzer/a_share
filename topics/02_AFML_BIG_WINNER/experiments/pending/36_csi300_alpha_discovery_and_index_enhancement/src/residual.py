"""EP20 market-only sequential residual formula, fixed-month endpoints on EP30 qfq proxy."""
import numpy as np,pandas as pd

def monthly_residual_score(close,market):
 ends=pd.Series(close.index,index=close.index).groupby(close.index.to_period('M')).max()
 # Require complete calendar month; final midmonth observations are never month endpoints.
 if close.index[-1].day<close.index[-1].days_in_month-3:ends=ends.iloc[:-1]
 c=close.reindex(ends);m=market.reindex(ends);r=c.pct_change(fill_method=None);mr=m.pct_change(fill_method=None);res=r*np.nan
 for j in range(36,len(r)):
  x=mr.iloc[j-36:j].to_numpy(float);ys=r.iloc[j-36:j].to_numpy(float);now=r.iloc[j].to_numpy(float)
  if not np.isfinite(x).all() or not np.isfinite(mr.iloc[j]) or x.std()<1e-12:continue
  good=np.isfinite(ys).all(axis=0)&np.isfinite(now)
  if good.any():
   beta,_,rank,_=np.linalg.lstsq(np.c_[np.ones(36),x],ys[:,good],rcond=1e-12)
   if rank==2:res.iloc[j,np.where(good)[0]]=now[good]-np.array([1.,mr.iloc[j]])@beta
 score=res.shift(1).rolling(11).mean()/res.shift(1).rolling(11).std(ddof=1)
 return score.reindex(close.index,method='ffill')

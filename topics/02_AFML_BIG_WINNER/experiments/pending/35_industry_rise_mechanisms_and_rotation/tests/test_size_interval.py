import numpy as np
import pandas as pd
from evaluate_size_r31 import interval

def test_hac_uses_calendar_gaps():
 dates=pd.to_datetime(['2020-01-31','2020-02-29','2020-05-31','2020-06-30']);v=np.array([1.,-2.,3.,0.]);u=v-v.mean();t=dates.to_period('M').astype('int64').to_numpy();lag=3
 kernel=np.maximum(1-np.abs(t[:,None]-t[None,:])/(lag+1),0)
 se=np.sqrt(u@kernel@u)/len(v);expected=(v.mean()-2.5758293035489004*se,v.mean()+2.5758293035489004*se)
 assert np.allclose(interval(pd.Series(v,index=dates),lag),expected)

def test_hac_constant_and_missing():
 s=pd.Series([2.,np.nan,2.],index=pd.date_range('2020-01-31',periods=3,freq='ME'))
 assert interval(s,3)==(2.,2.)
 assert np.isnan(interval(s.iloc[:1],3)).all()

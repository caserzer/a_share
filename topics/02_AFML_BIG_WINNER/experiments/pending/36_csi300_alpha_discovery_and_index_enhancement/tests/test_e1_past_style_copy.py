import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np,pandas as pd,pytest
from e1_past_style_copy import features_only,fit_history,STYLES

def frame():
 rng=np.random.default_rng(31);parts=[]
 for date in pd.date_range('2020-01-03',periods=40,freq='W-FRI'):
  g=pd.DataFrame({'signal_date':date,'instrument':[f'S{i:03}' for i in range(100)],'industry':['A']*50+['B']*50})
  for c in STYLES:g[c]=rng.normal(size=100)
  g['E1']=2*g.mom5-g.vol20+rng.normal(size=100)*.1;parts.append(g)
 return pd.concat(parts,ignore_index=True)

def test_future_and_current_teacher_cannot_change_fit():
 a=frame();cut=pd.Timestamp('2020-07-01');coef,r=fit_history(a,cut);b=a.copy();b.loc[b.signal_date>=cut,'E1']=-1e9
 altered,_=fit_history(b,cut);np.testing.assert_array_equal(coef,altered);assert pd.Timestamp(r['train_end'])<cut

def test_prediction_rejects_teacher_and_returns():
 a=frame().iloc[:100]
 with pytest.raises(AssertionError):features_only(a[STYLES+['industry','E1']])
 with pytest.raises(AssertionError):features_only(a[STYLES+['industry']].assign(h10=.5))

def test_warmup_and_industry_demeaning():
 a=frame();coef,r=fit_history(a,pd.Timestamp('2020-04-01'));assert coef is None and r['status']=='WARMUP'
 x=features_only(a.iloc[:100][STYLES+['industry']]);assert np.max(abs(x[:50].mean(axis=0)))<1e-12 and np.max(abs(x[50:].mean(axis=0)))<1e-12

def test_locked_prediction_needs_no_future_teacher():
 a=frame();coef,r=fit_history(a,pd.Timestamp('2020-07-01'));g=a[a.signal_date==a.signal_date.max()]
 before=features_only(g[STYLES+['industry']])@coef
 g=g.drop(columns='E1');np.testing.assert_array_equal(before,features_only(g[STYLES+['industry']])@coef)

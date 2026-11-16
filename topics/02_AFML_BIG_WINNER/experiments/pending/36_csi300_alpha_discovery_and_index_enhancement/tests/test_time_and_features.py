import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np,pandas as pd
from features import compute
from common import signal_days,zscore
from train import split_fit,TrainTransform,predict_only

def sample():
 rng=np.random.default_rng(17);days=pd.bdate_range('2019-01-01',periods=130);cols=[str(i) for i in range(110)]
 c=pd.DataFrame(np.exp(rng.normal(0,.01,(130,110)).cumsum(0))*10,index=days,columns=cols)
 v=c*100;member=c.notna();return c,v,member

def test_prefix_and_reanchor():
 c,v,member=sample()
 def calc(c,v,member):return compute(c,c*.99,c*1.02,c*.98,v,v*10,v*.001,member,c.mean(axis=1))
 full=calc(c,v,member);prefix=calc(c.iloc[:100],v.iloc[:100],member.iloc[:100]);scaled=calc(c*7,v,member)
 for k in full:
  np.testing.assert_allclose(full[k].iloc[:100],prefix[k],atol=1e-10,equal_nan=True)
  np.testing.assert_allclose(full[k],scaled[k],atol=1e-9,equal_nan=True)

def test_calendar_endpoint_not_next_observation():
 days=pd.bdate_range('2020-12-25',periods=20);o=pd.Series(np.arange(20)+10.,index=days);o.iloc[1]=np.nan
 y=o.shift(-11)/o.shift(-1)-1
 assert pd.isna(y.iloc[0]);assert y.iloc[2]==o.iloc[13]/o.iloc[3]-1
 assert days[11]-days[1]>pd.Timedelta(days=10)

def test_quarter_signal_and_maturity_purge():
 dates=pd.bdate_range('2017-01-01','2021-03-31');f=pd.DataFrame({'signal_date':dates})
 f['entry_date']=f.signal_date+pd.offsets.BDay(1);f['h10_mature']=f.signal_date+pd.offsets.BDay(11);f['target_z']=1.;f['score_eligible']=True
 cutoff=pd.Timestamp('2020-12-31 23:59:59');m,tr,va=split_fit(f,cutoff,'expanding')
 assert m.h10_mature.max()<=cutoff;assert tr.h10_mature.max()<va.entry_date.min()
 assert pd.Timestamp('2020-12-31').to_period('Q')==pd.Period('2020Q4')
 assert pd.Timestamp('2021-01-04').to_period('Q')==pd.Period('2021Q1')

def test_train_transform_and_xs():
 x=pd.DataFrame({'a':[1.,2.,np.nan],'b':[0.,0.,0.]});t=TrainTransform().fit(x);med=t.median.copy();t.transform(pd.DataFrame({'a':[1e9],'b':[np.nan]}));np.testing.assert_equal(med,t.median)
 assert zscore(pd.Series([1.]*101)).isna().all();assert zscore(pd.Series(range(99))).isna().all()

def test_incomplete_terminal_week():
 d=pd.bdate_range('2026-10-01','2026-10-21');assert signal_days(d)[-1]==pd.Timestamp('2026-10-16')

def test_monthly_residual_future_prefix_and_missing():
 from residual import monthly_residual_score
 rng=np.random.default_rng(42);days=pd.bdate_range('2017-01-01','2023-12-29');c=pd.DataFrame(np.exp(rng.normal(0,.02,(len(days),2)).cumsum(0)),index=days)
 m=pd.Series(np.exp(rng.normal(0,.01,len(days)).cumsum()),index=days)
 full=monthly_residual_score(c,m);prefix=monthly_residual_score(c.loc[:'2022-06-15'],m.loc[:'2022-06-15'])
 np.testing.assert_allclose(full.loc[prefix.index],prefix,equal_nan=True)
 assert full.loc[:'2020-12-31'].isna().all().all()
 assert full.loc['2022'].notna().any().all()

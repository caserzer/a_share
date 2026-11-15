import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import pytest
from common import KEY
from task_monitor_r22 import build,PCOLS,FCOLS


def fixture():
 c=pd.DataFrame([dict(era='SW2021',level='L3',industry_code='a',industry_name='A')])
 p=pd.DataFrame([dict(era='SW2021',level='L3',industry_code='a',cohort='F',method='F',task='return',horizon=20,date=pd.Timestamp('2026-09-30'),year=2026,prediction=.03)],columns=PCOLS)
 f=pd.DataFrame([dict(era='SW2021',level='L3',cohort='F',task='return',horizon=20,year=2026,status='fit',reason='')])
 model=dict(era='SW2021',level='L3',cohort='F',method='F',task='return',horizon=20,year=2026,fit_max_maturity='2025-12-30')
 panel=pd.DataFrame(columns=FCOLS);panel['date']=pd.to_datetime(panel['date'])
 return c,p,f,[model],panel


def test_no_stale_current_output_and_complete_task_grid():
 c,p,f,m,panel=fixture();d,q=build(c,p,f,m,panel,['2026-10-21'])
 assert len(d)==12 and d.prediction.isna().all()
 row=d[(d.method=='F')&(d.task=='return')&(d.horizon==20)].iloc[0]
 assert row.last_prediction==.03 and row.last_prediction_age_days==21
 assert row.status=='no_exact_date_feature_snapshot' and q.empty


def test_regression_never_probability_and_future_predictions_excluded():
 c,p,f,m,panel=fixture();row={x:0.1 for x in FCOLS};row.update(c.iloc[0].to_dict());row.update(date=pd.Timestamp('2026-09-30'),price_ready=True,members=10)
 panel=pd.DataFrame([row]);d,_=build(c,p,f,m,panel,['2026-09-30'])
 a=d[(d.method=='F')&(d.task=='return')&(d.horizon==20)].iloc[0]
 assert a.prediction==.03 and a.calibration_status=='not_applicable_regression'
 p['date']=pd.Timestamp('2026-10-21')
 with pytest.raises(ValueError,match='missing formal'):build(c,p,f,m,panel,['2026-09-30'])


def test_duplicate_predictions_rejected_and_unknown_identity_quarantined():
 c,p,f,m,panel=fixture()
 with pytest.raises(ValueError,match='duplicate prediction'):build(c,pd.concat([p,p]),f,m,panel,['2026-09-30'])
 p['industry_code']='unlisted';d,q=build(c,p,f,m,panel,['2026-09-30'])
 assert len(q)==1 and d.prediction.isna().all()

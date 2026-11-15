import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import numpy as np
from ttm_monthly_r116 import choose

def fixture():
    return pd.DataFrame(dict(report_period=pd.to_datetime(['2024-12-31','2025-03-31']),status=['valid_components','valid_components'],ttm_profit=[100.,110.],notice_report_available_at=pd.to_datetime(['2025-03-20','2025-04-30']),notice_available_at=pd.to_datetime(['2025-03-20','2025-05-06'])))
def test_latest_component_lag_never_falls_back():
    e=fixture();r=choose(e,pd.Timestamp('2025-04-30'),'notice');assert r['report_period']==pd.Timestamp('2025-03-31') and r['status']=='latest_components_not_yet_available' and np.isnan(r['ttm_profit'])
    assert choose(e,pd.Timestamp('2025-05-06'),'notice')['ttm_profit']==110
    e.loc[1,'status']='invalid_or_missing_component';r=choose(e,pd.Timestamp('2025-05-30'),'notice');assert r['status']=='latest_components_invalid' and np.isnan(r['ttm_profit'])
def test_visibility_and_report_period_priority():
    e=fixture();assert choose(e,pd.Timestamp('2025-03-19'),'notice')['status']=='no_visible_report'
    assert choose(e,pd.Timestamp('2025-04-29'),'notice')['ttm_profit']==100
    e.loc[0,'notice_report_available_at']=pd.Timestamp('2025-06-01')
    assert choose(e,pd.Timestamp('2025-06-30'),'notice')['report_period']==pd.Timestamp('2025-03-31')

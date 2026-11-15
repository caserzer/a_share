import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from ttm_components_r115 import candidate

def fixture():
    groups={}
    for period,typ,value,notice,update in [('2024-06-30','中报',40,'2024-08-20','2025-09-01'),('2024-12-31','年报',100,'2025-03-20','2025-03-20'),('2025-06-30','中报',-20,'2025-08-29','2025-08-29')]:
        groups[pd.Timestamp(period)]=pd.DataFrame([dict(REPORT_TYPE=typ,CURRENCY='CNY',PARENTNETPROFIT=value,NOTICE_DATE=notice,UPDATE_DATE=update,row_id=period)])
    return groups,pd.bdate_range('2024-01-01','2025-12-31')
def test_ttm_negative_ytd_is_valid_and_two_clocks():
    g,c=fixture();r=candidate('X',pd.Timestamp('2025-06-30'),g,c)
    assert r['ttm_profit']==40 and r['notice_available_at']==pd.Timestamp('2025-09-01') and r['update_available_at']==pd.Timestamp('2025-09-02')
    g[pd.Timestamp('2025-06-30')]['PARENTNETPROFIT']=-120
    assert candidate('X',pd.Timestamp('2025-06-30'),g,c)['ttm_profit']==-60

def test_missing_conflict_and_annual_not_annualized():
    g,c=fixture();assert candidate('X',pd.Timestamp('2024-12-31'),g,c)['ttm_profit']==100
    g.pop(pd.Timestamp('2024-06-30'));r=candidate('X',pd.Timestamp('2025-06-30'),g,c);assert np.isnan(r['ttm_profit']) and 'missing_period' in r['component_statuses']
    g,c=fixture();f=g[pd.Timestamp('2025-06-30')];g[pd.Timestamp('2025-06-30')]=pd.concat([f,f.assign(PARENTNETPROFIT=-21)])
    r=candidate('X',pd.Timestamp('2025-06-30'),g,c);assert np.isnan(r['ttm_profit']) and 'conflicting_values' in r['component_statuses']

def test_missing_clock_does_not_certify_timing():
    g,c=fixture();g[pd.Timestamp('2025-06-30')]['UPDATE_DATE']=None;r=candidate('X',pd.Timestamp('2025-06-30'),g,c)
    assert r['ttm_profit']==40 and pd.notna(r['notice_available_at']) and pd.isna(r['update_available_at'])
    g[pd.Timestamp('2025-06-30')]['NOTICE_DATE']='2025-01-01';r=candidate('X',pd.Timestamp('2025-06-30'),g,c);assert pd.isna(r['notice_available_at'])

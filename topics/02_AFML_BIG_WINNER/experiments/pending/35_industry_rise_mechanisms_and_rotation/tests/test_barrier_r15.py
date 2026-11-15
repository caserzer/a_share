import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import numpy as np
from barrier_sensitivity_r15 import monthly_from_history

def history(values):
    return pd.DataFrame({'publication_proxy_date':pd.to_datetime(['2025-01-01','2025-02-01','2025-03-01']),'value':values})

def test_latest_missing_report_invalidates_old_carried_revision():
    h=history([100,110,np.nan])
    before=monthly_from_history(h,pd.Timestamp('2025-03-01'))
    assert before['status']=='valid' and np.isclose(before['revision'],10/210)
    after=monthly_from_history(h,pd.Timestamp('2025-03-02'))
    assert after['status']=='unknown_current_or_prior' and np.isnan(after['revision'])

def test_unknown_predecessor_not_replaced_by_older_valid():
    assert monthly_from_history(history([100,np.nan,130]),pd.Timestamp('2025-03-02'))['status']=='unknown_current_or_prior'

def test_future_values_do_not_change_past_monthly_revision():
    h=history([100,110,130]);date=pd.Timestamp('2025-02-20')
    before=monthly_from_history(h,date);h.loc[2,'value']=-999
    assert monthly_from_history(h,date)==before

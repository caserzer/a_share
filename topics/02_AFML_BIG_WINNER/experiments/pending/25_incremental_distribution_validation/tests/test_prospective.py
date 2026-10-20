import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from core import CONFIG
from prospective import validate_future_panel


def frame():
    d={c:[1.] for c in CONFIG['eligibility_features']}
    d.update(date=pd.to_datetime(['2026-10-30']),instrument=['SZ300001'],financial_available_date=pd.to_datetime(['2026-10-29']))
    for h in CONFIG['horizons']:d[f'y_{h}']=[np.nan]
    return pd.DataFrame(d)


def test_prospective_refuses_future_dates():
    with pytest.raises(AssertionError):validate_future_panel(frame(),'2026-10-30','2026-10-20')


def test_prospective_refuses_late_archives():
    with pytest.raises(AssertionError):validate_future_panel(frame(),'2026-10-30','2026-11-01')


def test_prospective_refuses_known_outcomes():
    p=frame();p['y_6']=.1
    with pytest.raises(AssertionError):validate_future_panel(p,'2026-10-30','2026-10-30')


def test_prospective_requires_strict_financial_availability():
    p=frame();p.financial_available_date=pd.Timestamp('2026-10-30')
    with pytest.raises(AssertionError):validate_future_panel(p,'2026-10-30','2026-10-30')


def test_prospective_accepts_unlabeled_point_in_time_frame():
    assert len(validate_future_panel(frame(),'2026-10-30','2026-10-30'))==1


def test_confirmation_requires_36_consecutive_mature_origins():
    from confirm_prospective import require_confirmation_origins
    with pytest.raises(AssertionError):require_confirmation_origins(pd.date_range('2026-10-31',periods=35,freq='ME'))
    dates=pd.date_range('2026-10-31',periods=37,freq='ME')
    assert len(require_confirmation_origins(dates))==36
    with pytest.raises(AssertionError):require_confirmation_origins(dates.delete(10))

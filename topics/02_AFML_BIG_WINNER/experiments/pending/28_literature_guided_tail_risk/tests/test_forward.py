from pathlib import Path
import sys
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from forward import valid_origin


def test_future_prediction_rejects_backdating_and_future_dates():
    calendar=pd.to_datetime(['2026-10-29','2026-10-30','2026-11-02'])
    for now in ['2026-10-20 17:00','2026-10-31 17:00','2026-10-30 15:00']:
        with pytest.raises(AssertionError):valid_origin('2026-10-30',now,calendar)


def test_real_month_end_after_close_allowed():
    c=pd.to_datetime(['2026-10-29','2026-10-30','2026-11-02'])
    assert valid_origin('2026-10-30','2026-10-30 16:01',c)==pd.Timestamp('2026-10-30')


def test_non_month_end_rejected():
    c=pd.to_datetime(['2026-10-30','2026-11-02','2026-11-30','2026-12-01'])
    with pytest.raises(AssertionError):valid_origin('2026-11-02','2026-11-02 17:00',c)

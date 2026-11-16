import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
from q5_rebalance_sensitivity import scheduled_dates

def test_biweekly_keeps_calendar_phase_after_holiday_week():
    dates=pd.to_datetime(['2021-01-08','2021-01-15','2021-01-22','2021-02-05','2021-02-10','2021-02-19'])
    got=scheduled_dates(dates,'2w')
    assert list(got)==list(pd.to_datetime(['2021-01-08','2021-01-22','2021-02-05','2021-02-19']))

def test_monthly_is_natural_month_first_signal_not_four_weeks():
    dates=pd.to_datetime(['2021-01-08','2021-01-15','2021-01-22','2021-01-29','2021-02-05','2021-02-10','2021-02-19','2021-02-26','2021-03-05','2021-04-02','2021-04-09','2021-05-07'])
    got=scheduled_dates(dates,'1m')
    assert list(got)==list(pd.to_datetime(['2021-01-08','2021-02-05','2021-03-05','2021-04-02','2021-05-07']))

def test_append_future_dates_does_not_change_prior_schedule_and_start_shared():
    dates=pd.date_range('2021-01-08','2022-03-01',freq='W-FRI');prefix=dates[:18]
    for freq in ['1w','2w','1m']:
        full=scheduled_dates(dates,freq);old=scheduled_dates(prefix,freq)
        assert full[0]==dates[0]
        assert list(full[full<=prefix[-1]])==list(old)

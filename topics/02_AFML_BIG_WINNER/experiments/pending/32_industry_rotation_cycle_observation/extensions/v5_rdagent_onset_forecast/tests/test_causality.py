import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import numpy as np
from labels import label_one
from data import frequency_dates
from common import load_turns


def stage(start, confirm, end_confirm=None, positive=False, status='CONFIRMED'):
    return dict(start_date=pd.Timestamp(start),start_confirmed_at=pd.Timestamp(confirm),
        end_confirmed_at=pd.Timestamp(end_confirm) if end_confirm else pd.NaT,
        qualified_CSI300=positive,status=status,left_censored=False,phase_id=start)


def test_absence_is_unknown_not_negative():
    x=label_one(pd.Timestamp('2020-01-01'),pd.Timestamp('2020-02-01'),[],pd.Timestamp('2021-01-01'),'CSI300')
    assert np.isnan(x[0]) and x[3]=='NO_LATER_CONFIRMED_TROUGH'


def test_negative_waits_for_later_trough_confirmation():
    s=[stage('2020-03-01','2020-04-01','2020-06-01')]
    x=label_one(pd.Timestamp('2020-01-01'),pd.Timestamp('2020-02-01'),s,pd.Timestamp('2021-01-01'),'CSI300')
    assert x[0]==0 and x[1]==pd.Timestamp('2020-04-01')


def test_positive_waits_for_final_outcome_not_start_confirmation():
    s=[stage('2020-01-15','2020-02-01','2020-12-01',True)]
    x=label_one(pd.Timestamp('2020-01-01'),pd.Timestamp('2020-02-01'),s,pd.Timestamp('2021-01-01'),'CSI300')
    assert x[0]==1 and x[1]==pd.Timestamp('2020-12-01')


def test_open_window_cannot_become_negative():
    s=[stage('2020-01-15','2020-02-01',status='OPEN')]
    x=label_one(pd.Timestamp('2020-01-01'),pd.Timestamp('2020-02-01'),s,pd.Timestamp('2021-01-01'),'CSI300')
    assert np.isnan(x[0])


def test_gap_crossing_is_unknown():
    s=[stage('2020-03-01','2020-04-01','2020-06-01')]
    x=label_one(pd.Timestamp('2020-01-01'),pd.Timestamp('2020-02-01'),s,pd.Timestamp('2020-01-20'),'CSI300')
    assert np.isnan(x[0])


def test_partial_week_month_not_reported_as_complete():
    d=pd.bdate_range('2017-01-02','2017-02-15');s=frequency_dates(d)
    assert s['W'].max()==pd.Timestamp('2017-02-10')
    assert s['M'].max()==pd.Timestamp('2017-01-31')
    assert set(s['BW']).issubset(set(s['W']))
    assert pd.Timestamp('2017-01-06') in s['BW']


def test_confirmed_turns_do_not_change_on_future_append():
    p=np.array([100,80,85,100,120,100,80,100,130,100,80,100.])
    fn=load_turns();full=fn(p,.15)
    for n in range(3,len(p)):
        a=[x for x in fn(p[:n],.15) if x['status']=='CONFIRMED']
        b=[x for x in full if x['status']=='CONFIRMED' and x['end_confirm_i']<n]
        assert a==b


def test_early_recognition_does_not_count_future_onset_as_current():
    t=pd.Timestamp('2020-04-01')
    s=[stage('2020-05-01','2020-06-01','2021-01-01',True)]
    x=label_one(t-pd.DateOffset(months=3),t,s,pd.Timestamp('2021-06-01'),'CSI300')
    assert x[0]==0 and x[1]==pd.Timestamp('2020-06-01')


def test_early_recognition_still_requires_future_final_confirmation():
    t=pd.Timestamp('2020-04-01')
    s=[stage('2020-02-01','2020-03-01','2021-01-01',True)]
    x=label_one(t-pd.DateOffset(months=3),t,s,pd.Timestamp('2021-06-01'),'CSI300')
    assert x[0]==1 and x[1]==pd.Timestamp('2021-01-01')

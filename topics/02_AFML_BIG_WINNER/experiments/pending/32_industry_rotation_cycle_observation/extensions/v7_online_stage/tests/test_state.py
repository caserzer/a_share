import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from state7 import trace
from common import load_turns


def test_every_prefix_is_identical_after_future_append():
    rng=np.random.default_rng(7);p=100*np.exp(np.cumsum(rng.normal(0,.04,250)))
    days=pd.bdate_range('2020-01-01',periods=len(p));full=trace(p,days,.15)
    for n in [1,2,40,101,180,249]:pd.testing.assert_frame_equal(trace(p[:n],days[:n],.15),full.iloc[:n].reset_index(drop=True))


def test_confirmed_start_matches_original_turn_algorithm():
    rng=np.random.default_rng(32);p=100*np.exp(np.cumsum(rng.normal(0,.05,1000)))
    days=pd.bdate_range('2018-01-01',periods=len(p))
    for threshold in [.1,.15,.2]:
        s=trace(p,days,threshold)
        for event in load_turns()(p,threshold):
            q=event['start_confirm_i']
            assert s.iloc[q].candidate_low_date==days[event['start_i']]
            assert s.iloc[q].state_left==int(event['left_censored'])
            end=event['end_confirm_i'] or len(p)
            assert s.iloc[q:end].candidate_low_date.eq(days[event['start_i']]).all()


def test_calendar_month_boundary_is_exclusive():
    days=pd.to_datetime(['2020-01-01','2020-01-02','2020-01-03','2020-04-02','2020-04-03'])
    s=trace([100,80,90,91,92],days,.1)
    assert s.iloc[2].state_eligible==1
    assert s.iloc[3].state_eligible==0


def test_left_censored_rally_is_not_eligible():
    s=trace([100,105,115,120],pd.date_range('2020-01-01',periods=4),.1)
    assert s.state_eligible.eq(0).all()


def test_new_low_resets_only_when_observed():
    s=trace([100,80,85,75,84],pd.date_range('2020-01-01',periods=5),.1)
    assert s.candidate_low_date.iloc[2]==pd.Timestamp('2020-01-02')
    assert s.candidate_low_date.iloc[3]==pd.Timestamp('2020-01-04')
    assert s.candidate_low_date.iloc[4]==pd.Timestamp('2020-01-04')

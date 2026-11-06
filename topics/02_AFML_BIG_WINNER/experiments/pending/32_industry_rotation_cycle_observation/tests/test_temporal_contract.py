from pathlib import Path
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from observe import active_members, leading_runs, path_stats, shares_asof


def test_future_share_change_cannot_change_prior_rank_input():
    original = pd.DataFrame(dict(effective_date=pd.to_datetime(['2022-01-01']),
                                 total_shares=[100.], known_at=[pd.NaT]))
    future = pd.concat([original, pd.DataFrame(dict(effective_date=pd.to_datetime(['2023-01-01']),
                          total_shares=[10000.], known_at=[pd.NaT]))], ignore_index=True)
    dates = pd.DatetimeIndex(['2022-12-30'])
    assert shares_asof(original, dates).total_shares.iloc[0] == shares_asof(future, dates).total_shares.iloc[0] == 100.


def test_conflicting_latest_shares_do_not_revert_to_old_known_value():
    f = pd.DataFrame(dict(effective_date=pd.to_datetime(['2022-01-01', '2022-06-01', '2022-06-01']),
                          total_shares=[100., 150., 200.], known_at=[pd.NaT] * 3))
    assert pd.isna(shares_asof(f, pd.DatetimeIndex(['2022-12-30'])).total_shares.iloc[0])


def test_missing_past_shares_never_backward_fills():
    f = pd.DataFrame(dict(effective_date=pd.to_datetime(['2023-01-01']), total_shares=[100.], known_at=[pd.NaT]))
    assert pd.isna(shares_asof(f, pd.DatetimeIndex(['2022-12-30'])).total_shares.iloc[0])


def test_removed_member_is_historically_present_and_future_one_absent():
    f = pd.DataFrame(dict(in_date=pd.to_datetime(['2020-01-01', '2023-01-01']),
                          out_date=pd.to_datetime(['2023-01-01', None]), stock=['removed', 'future']))
    assert active_members(f, pd.Timestamp('2022-12-30')).stock.tolist() == ['removed']
    assert active_members(f, pd.Timestamp('2023-01-01')).empty


def test_invalid_month_breaks_and_censors_both_price_leading_runs():
    f = pd.DataFrame(dict(level=['L2'] * 5, industry_code=['a'] * 5, industry_name=['A'] * 5,
                          month=pd.period_range('2022-01', periods=5, freq='M'), leader12=[0., 1., np.nan, 1., 0.]))
    r = leading_runs(f, 12)
    assert [x['months'] for x in r] == [1, 1]
    assert r[0]['right_censored'] and r[1]['left_censored']


def test_terminal_gain_is_not_uninterrupted_monthly_uptrend():
    stats = path_stats([.2, -.1, .3, .25])
    assert stats['positive_run'] == 2
    assert stats['monthly_up_run'] == 1
    assert np.isclose(stats['max_drawdown'], -.25)


def test_missing_path_never_claims_continuous_duration():
    stats = path_stats([.2, np.nan, .4])
    assert all(pd.isna(x) for x in stats.values())

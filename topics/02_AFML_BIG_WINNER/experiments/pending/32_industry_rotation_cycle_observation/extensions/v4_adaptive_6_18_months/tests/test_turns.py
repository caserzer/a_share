from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from turns import upswings, duration_class


def test_confirmation_is_later_than_hindsight_peak():
    rows = upswings([100, 70, 80, 100, 90, 79], .2)
    assert len(rows) == 1
    r = rows[0]
    assert (r['start_i'], r['start_confirm_i'], r['peak_i'], r['end_confirm_i']) == (1, 3, 3, 5)
    assert r['status'] == 'CONFIRMED' and not r['left_censored']


def test_more_than_18_months_is_never_split_or_truncated():
    prices = [100, 70] + list(np.linspace(90, 220, 31)) + [150]
    rows = upswings(prices, .2)
    assert len(rows) == 1
    assert rows[0]['peak_i'] - rows[0]['start_i'] == 31
    assert duration_class(31) == 'LONG_GT18'


def test_duration_bounds_inclusive():
    assert duration_class(5) == 'SHORT_LT6'
    assert duration_class(6) == 'IN_RANGE_6_18'
    assert duration_class(18) == 'IN_RANGE_6_18'
    assert duration_class(19) == 'LONG_GT18'


def test_initial_swing_is_left_censored_and_open_swing_not_claimed_complete():
    a = upswings([100, 120, 140, 105], .2)[0]
    assert a['left_censored'] and a['status'] == 'CONFIRMED'
    b = upswings([100, 70, 90, 120, 110], .2)[0]
    assert b['status'] == 'OPEN' and b['right_censored'] and b['end_confirm_i'] is None
    assert b['peak_i'] == 3 and b['evaluation_i'] == 4


def test_missing_return_block_cannot_be_filled_inside_turn_detector():
    with pytest.raises(ValueError):
        upswings([100, np.nan, 150], .15)


def test_future_data_cannot_rewrite_an_already_confirmed_swing():
    past = [100, 70, 90, 120, 90]
    first = upswings(past, .2)[0]
    extended = upswings(past + [80, 110, 140, 90], .2)
    assert extended[0] == first


def test_equal_highs_do_not_extend_the_duration():
    r = upswings([100, 70, 90, 120, 120, 90], .2)[0]
    assert r['peak_i'] == 3

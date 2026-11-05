from admit_folds import full_months_available


def test_nine_days_short_is_blocked_despite_approximate_fit_precheck():
    assert not full_months_available('2018-01-12','2020-01-03')
    assert full_months_available('2018-01-12','2020-01-12')

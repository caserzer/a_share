import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from build_eps_panel import forecast_features


def row():
    return dict(date=pd.Timestamp('2021-02-26'),available_date='2020-10-29',status='parsed',
        forecasts='{"2020": 36.93, "2021": 49.61, "2022": 60.66}',profit_forecasts='{}',
        eps_conflict=False,profit_conflict=False)


def test_explicit_fiscal_year_rolls_with_decision_year():
    r=row();out=forecast_features(r)
    np.testing.assert_allclose(out['eps_log_growth'],np.log(60.66/49.61))
    r['date']=pd.Timestamp('2020-11-30');out=forecast_features(r)
    np.testing.assert_allclose(out['eps_log_growth'],np.log(49.61/36.93))


def test_same_day_future_conflict_and_expired_are_unavailable():
    for change in [{'available_date':'2021-02-26'},{'available_date':'2021-02-27'},
                   {'available_date':'2020-01-01'},{'eps_conflict':True},{'status':'empty_original_body'}]:
        r={**row(),**change};out=forecast_features(r)
        assert not out['eps_pair_available'] and not out['earnings_pair_available']


def test_profit_growth_is_not_relabelled_eps_and_losses_not_forced_positive():
    r=row();r['forecasts']='{}';r['profit_forecasts']='{"2021": 100000000, "2022": 150000000}'
    out=forecast_features(r)
    assert not out['eps_pair_available'] and out['forecast_basis_profit']==1
    np.testing.assert_allclose(out['earnings_log_growth'],np.log(1.5))
    r['forecasts']='{"2021": 1, "2022": -0.5}'
    out=forecast_features(r)
    assert out['eps_pair_available'] and not out['earnings_positive']
    assert out['forecast_next_loss']==1 and out['forecast_basis_profit']==0
    assert np.isnan(out['eps_log_growth'])

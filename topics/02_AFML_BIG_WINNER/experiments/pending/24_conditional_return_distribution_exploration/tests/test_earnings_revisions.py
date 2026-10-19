import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from build_earnings_revisions import revision_for_row


def report(code, when, observed, values, broker='A', stock='600000'):
    return dict(infoCode=code, available_date=pd.Timestamp(when), first_observed_at=pd.Timestamp(observed),
        stockCode=stock, orgCode=broker, forecasts=json.dumps(values), profit_forecasts='{}')


def test_revision_uses_same_years_broker_and_stock():
    row=dict(date=pd.Timestamp('2024-06-03'), earnings_positive=True, forecast_basis_profit=0)
    current=report('new','2024-05-10','2024-06-03',{2024:2,2025:3})
    old=report('old','2024-02-01','2024-03-01',{2024:1,2025:1.2})
    got=revision_for_row(row,current,[old])
    assert got['revision_available']
    np.testing.assert_allclose(got['growth_revision'],np.log(1.5/1.2))
    assert not revision_for_row(row,current,[dict(old,orgCode='B')])['revision_available']
    assert not revision_for_row(row,current,[dict(old,stockCode='600001')])['revision_available']
    old['forecasts']=json.dumps({2023:1,2024:1.2})
    assert not revision_for_row(row,current,[old])['revision_available']


def test_revision_requires_previous_observation_and_publication():
    row=dict(date=pd.Timestamp('2024-06-03'), earnings_positive=True, forecast_basis_profit=0)
    current=report('new','2024-05-10','2024-06-03',{2024:2,2025:3})
    old=report('old','2024-02-01','2024-03-01',{2024:1,2025:1.2})
    for bad in [dict(old,first_observed_at=row['date']),dict(old,available_date=current['available_date']),
                dict(old,available_date=pd.Timestamp('2023-01-01'))]:
        assert not revision_for_row(row,current,[bad])['revision_available']
    assert not revision_for_row(row,dict(current,available_date=row['date']),[old])['revision_available']


def test_growth_revision_is_invariant_to_share_unit_and_rejects_losses():
    row=dict(date=pd.Timestamp('2024-06-03'), earnings_positive=True, forecast_basis_profit=0)
    current=report('new','2024-05-10','2024-06-03',{2024:2,2025:3})
    old=report('old','2024-02-01','2024-03-01',{2024:10,2025:12})
    np.testing.assert_allclose(revision_for_row(row,current,[old])['growth_revision'],np.log(1.5/1.2))
    assert not revision_for_row(dict(row,earnings_positive=False),current,[old])['revision_available']
    assert not revision_for_row(row,current,[dict(old,forecasts=json.dumps({2024:-1,2025:2}))])['revision_available']


def test_profit_and_eps_bases_are_not_mixed():
    row=dict(date=pd.Timestamp('2024-06-03'), earnings_positive=True, forecast_basis_profit=1)
    current=report('new','2024-05-10','2024-06-03',{})
    current['profit_forecasts']=json.dumps({2024:2e8,2025:3e8})
    old=report('old','2024-02-01','2024-03-01',{2024:1,2025:1.2})
    assert not revision_for_row(row,current,[old])['revision_available']
    old['profit_forecasts']=json.dumps({2024:1e8,2025:1.2e8})
    assert revision_for_row(row,current,[old])['revision_available']

import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from run_four_horizons import calendar_targets, probability_stats, BIN_NAMES


def test_calendar_months_and_holiday_roll():
    calendar = pd.DatetimeIndex(['2024-02-29', '2024-04-30', '2024-07-31', '2025-02-03'])
    dates = pd.DatetimeIndex(['2024-01-31'])
    for months, expected in [(1, '2024-02-29'), (3, '2024-04-30'), (6, '2024-07-31'), (12, '2025-02-03')]:
        _, end = calendar_targets(dates, months, calendar)
        assert end.iloc[0] == pd.Timestamp(expected)
    _, end = calendar_targets(dates, 24, calendar)
    assert pd.isna(end.iloc[0])


def test_probability_boundaries_and_missing_labels():
    atoms = np.tile(np.array([-.3, -.2, -.05, 0., .05, .2, .3]), (2, 1))
    result = probability_stats(atoms, np.array([0., np.nan]))
    probs = result[[f'p_{n}' for n in BIN_NAMES]].to_numpy()
    np.testing.assert_allclose(probs.sum(axis=1), 1)
    np.testing.assert_allclose(probs[0], np.array([1, 1, 2, 1, 2])/7)
    np.testing.assert_allclose(result[['p_up','p_down','p_zero']].sum(axis=1), 1)
    assert np.isnan(result.loc[1, 'multiclass_brier'])
    assert np.isnan(result.loc[1, 'brier'])
    expected = ((probs[0] - np.array([0,0,1,0,0]))**2).sum()
    assert result.loc[0, 'multiclass_brier'] == expected


def test_calendar_labels_match_independent_daily_source():
    from prepare_panel import DATA, OUT
    path = OUT / 'local_cache/four_horizon_panel.parquet'
    assert path.exists(), 'build four-horizon panel before integration checks'
    panel = pd.read_parquet(path)
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(DATA/'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    sample = panel.sample(12, random_state=24)
    for _, row in sample.iterrows():
        bars = pd.read_csv(DATA/f'raw/akshare/day/qfq/{row.instrument}.csv',parse_dates=['date']).set_index('date')
        for h in [1,3,6,12]:
            target = row.date + pd.DateOffset(months=h)
            eligible = calendar[calendar>=target]
            if len(eligible)==0:
                assert pd.isna(row[f'end_{h}']) and pd.isna(row[f'y_{h}'])
            else:
                end = eligible[0]
                assert row[f'end_{h}']==end
                if row.date in bars.index and end in bars.index:
                    expected=bars.loc[end,'close']/bars.loc[row.date,'close']-1
                    assert np.isclose(row[f'y_{h}'], expected, equal_nan=True)


def test_pit_recalibration_identity_and_coherence():
    from calibrate_four_horizons import recalibrated_atoms
    from run_holdout import GRID
    atoms=np.tile(np.linspace(-.5,.5,200),(3,1))
    # Identity shrinkage leaves the distribution unchanged.
    np.testing.assert_allclose(recalibrated_atoms(atoms, np.linspace(0,1,100),shrink=0),atoms,atol=1e-14)
    calibrated=recalibrated_atoms(atoms,np.full(100,.8))
    assert (np.diff(calibrated,axis=1)>=0).all()
    assert calibrated.min()>=atoms.min() and calibrated.max()<=atoms.max()
    stats=probability_stats(calibrated,np.zeros(3))
    np.testing.assert_allclose(stats[[f'p_{n}' for n in BIN_NAMES]].sum(axis=1),1)


def test_weighted_distribution_matches_pairwise_crps_and_classes():
    from run_direct_probability import weighted_stats, classes
    atoms=np.array([[-.3,-.2,-.05,0,.05,.2,.3]])
    weights=np.array([[.1,.1,.1,.2,.1,.1,.3]])
    y=np.array([.06])
    stats=weighted_stats(atoms,weights,y)
    pair=np.abs(atoms[0,:,None]-atoms[0,None,:])
    expected=(weights*np.abs(atoms-y[:,None])).sum()-.5*(weights[0,:,None]*weights[0,None,:]*pair).sum()
    np.testing.assert_allclose(stats.crps,expected)
    np.testing.assert_allclose(stats.p_up,.5)
    np.testing.assert_allclose(stats.p_down,.3)
    np.testing.assert_allclose(stats.p_zero,.2)
    np.testing.assert_allclose(stats[[f'p_{n}' for n in BIN_NAMES]].sum(axis=1),1)
    np.testing.assert_array_equal(classes(atoms[0]),[0,1,2,3,5,6,6])
    assert weighted_stats(atoms,weights,np.array([np.nan])).brier.isna().all()

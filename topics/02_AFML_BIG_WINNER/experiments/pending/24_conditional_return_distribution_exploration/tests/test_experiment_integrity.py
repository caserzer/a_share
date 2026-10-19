"""Independent checks for label alignment and training-time leakage."""
from pathlib import Path
import numpy as np
import pandas as pd

EP = Path(__file__).resolve().parents[1]
DATA = EP.parents[2] / 'data'


def test_labels_against_source_prices():
    panel = pd.read_parquet(EP / 'outputs/local_cache/monthly_panel.parquet')
    sample = panel.dropna(subset=['return126', 'return252']).sample(12, random_state=93)
    for _, row in sample.iterrows():
        source = pd.read_csv(DATA / f'raw/akshare/day/qfq/{row.instrument}.csv').set_index('date')
        entry = source.loc[row.entry_date.strftime('%Y-%m-%d'), 'open']
        for h in (126, 252):
            close = source.loc[row[f'label_end{h}'].strftime('%Y-%m-%d'), 'close']
            assert np.isclose(close / entry - 1, row[f'return{h}'])


def test_training_and_calibration_only_use_mature_labels():
    fits = pd.read_csv(EP / 'outputs/r01_price_pilot/fit_audit.csv')
    for _, row in fits.iterrows():
        assert pd.Timestamp(row.train_last_label) < pd.Period(row.quarter, freq='Q').start_time
    audit = pd.read_csv(EP / 'outputs/r02_calibration_probe/calibration_audit.csv')
    assert (pd.to_datetime(audit.last_mature_label) < pd.to_datetime(audit.date)).all()
    assert (audit.calibration_months >= 6).all()


def test_comparisons_have_identical_targets_and_holdout_not_scored():
    for folder in ['r01_price_pilot', 'r02_calibration_probe', 'r03_information_probe', 'r04_peer_probe']:
        pred = pd.read_parquet(EP / f'outputs/{folder}/predictions.parquet')
        assert pred.date.max() < pd.Timestamp('2024-01-01')
        assert not pred.duplicated(['horizon', 'date', 'instrument', 'model']).any()
        for _, g in pred.groupby('horizon'):
            counts = g.groupby(['date', 'instrument']).model.nunique()
            assert (counts == g.model.nunique()).all()
        q = pred[['q05', 'q10', 'q25', 'q50', 'q75', 'q90', 'q95']].to_numpy()
        assert np.isfinite(q).all()
        assert (np.diff(q, axis=1) >= 0).all()


def test_enriched_information_dates_and_source_values():
    p = pd.read_parquet(EP / 'outputs/local_cache/enriched_panel.parquet')
    f = p.dropna(subset=['financial_available_date'])
    assert (f.financial_available_date < f.date).all()
    assert (f.financial_report_date <= f.financial_available_date).all()
    y = p.dropna(subset=['yield_observation_date'])
    assert (y.yield_observation_date < y.date).all()
    assert ((y.date - y.yield_observation_date).dt.days <= 7).all()
    for _, row in f.sample(12, random_state=27).iterrows():
        source = pd.read_parquet(EP / f'outputs/local_cache/public_financials/{row.instrument[2:]}.{row.instrument[:2]}.parquet')
        report = source[pd.to_datetime(source.REPORT_DATE) == row.financial_report_date]
        assert not report.empty
        assert (pd.to_datetime(report.NOTICE_DATE) < row.date).any()
        assert (pd.to_datetime(report.UPDATE_DATE) < row.date).any()

import sys
from pathlib import Path
import numpy as np
import pandas as pd

EP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EP / 'src'))
from run_holdout import distribution_stats
from run_portfolio_probe import capped_weights, simulate
from run_price_pilot import TECH
from check_total_returns import reinvested_index


def test_finite_crps_against_pairwise_definition():
    atoms = np.array([[-.2, .1, .5], [-.2, .1, .5]])
    stats = distribution_stats(atoms, [.15, np.nan])
    expected = np.abs(atoms[0]-.15).mean() - .5*np.abs(atoms[0, :, None]-atoms[0]).mean()
    assert np.isclose(stats.crps.iloc[0], expected)
    assert np.isclose(stats.p_up.iloc[0], 2/3)
    assert stats.loc[1, ['crps', 'brier', 'pit', 'below_q05', 'coverage90']].isna().all()


def test_caps_and_all_zero_fallback():
    for raw in [np.zeros(20), np.r_[1e6, np.ones(19)], np.ones(20)]:
        w = capped_weights(raw)
        assert np.isclose(w.sum(), 1)
        assert (w <= .1+1e-12).all() and (w >= 0).all()


def test_reinvestment_and_ex_date_entry_entitlement():
    dates=pd.date_range('2024-01-01',periods=3)
    close=pd.Series([100.,90.,99.],index=dates)
    cash=pd.Series([0.,10.,0.],index=dates)
    shares=pd.Series(0.,index=dates)
    index=reinvested_index(close,cash,shares)
    assert np.allclose(index,[1.,1.,1.1])
    # A new purchase at ex-date open 90 receives only price movement thereafter.
    assert np.isclose(index.iloc[2]/index.iloc[1]*close.iloc[1]/90-1,.1)
    split_index=reinvested_index(pd.Series([100.,50.,55.],index=dates),pd.Series(0.,index=dates),pd.Series([0.,1.,0.],index=dates))
    assert np.allclose(split_index,[1.,1.,1.1])


def test_blocked_sale_retains_position_and_cash_conservation():
    dates = pd.date_range('2024-01-01', periods=4)
    op = np.array([[100.], [100.], [80.], [81.]])
    market = {'open': op, 'close': op, 'mark': op, 'raw_open': op,
              'reference': np.array([[100.], [100.], [100.], [80.]]),
              'prior_volume': np.full((4, 1), 1e9)}
    schedule = {dates[0]: np.array([1.]), dates[1]: np.array([0.])}
    daily, orders, summary = simulate(dates, market, schedule, .001, initial_cash=1000.)
    assert orders.iloc[1].blocked_sells == 1
    assert daily.iloc[1].holdings == 1
    assert daily.cash.min() >= 0
    assert np.isclose(daily.nav.iloc[0], 1000/1.001)
    assert np.isclose(daily.nav.iloc[-1], 1000/1.001*.81)


def test_holdout_population_is_not_selected_by_future_outcomes():
    panel = pd.read_parquet(EP / 'outputs/local_cache/enriched_panel.parquet')
    panel['board'] = panel.instrument.str.startswith('SZ30').astype(int)
    expected = panel[panel.date >= '2024-01-01'].dropna(subset=TECH + ['earnings_yield', 'book_yield'])
    keys = set(zip(expected.date, expected.instrument))
    predictions = pd.read_parquet(EP / 'outputs/r05_holdout/predictions.parquet')
    for _, g in predictions.groupby(['horizon', 'model']):
        assert set(zip(g.date, g.instrument)) == keys
        assert not g.duplicated(['date', 'instrument']).any()
    fits = pd.read_csv(EP / 'outputs/r05_holdout/fit_audit.csv')
    for r in fits.itertuples():
        assert pd.Timestamp(r.last_mature_label) < pd.Period(r.quarter, freq='Q').start_time
    assert predictions.loc[~predictions.mature, 'crps'].isna().all()


def test_excess_labels_subtract_realized_benchmark_only_in_target():
    panel = pd.read_parquet(EP / 'outputs/local_cache/enriched_panel.parquet').set_index(['date','instrument'])
    p = pd.read_parquet(EP / 'outputs/r08_excess_probe/predictions.parquet')
    sample = p.dropna(subset=['actual']).sample(20,random_state=28)
    for r in sample.itertuples():
        source = panel.loc[(r.date,r.instrument)]
        assert np.isclose(r.actual,source[f'return{r.horizon}']-source[f'benchmark{r.horizon}'])
    fits = pd.read_csv(EP / 'outputs/r08_excess_probe/fit_audit.csv')
    for r in fits.itertuples():
        assert pd.Timestamp(r.last_mature_label) < pd.Period(r.quarter,freq='Q').start_time


def test_portfolio_reports_reconcile_to_retained_nav():
    nav = pd.read_parquet(EP / 'outputs/r06_portfolio_probe/daily_nav.parquet')
    summary = pd.read_csv(EP / 'outputs/r06_portfolio_probe/summary.csv')
    assert (nav.cash >= 0).all() and (nav.nav > 0).all()
    assert (nav.gross <= 1+1e-10).all()
    for r in summary.itertuples():
        g = nav[(nav.model==r.model) & (nav['style']==r.style) & (nav.fee==r.fee)].sort_values('date')
        assert np.isclose(r.total_return,g.nav.iloc[-1]/1e6-1)
        wealth = np.r_[1e6,g.nav.to_numpy()]
        assert np.isclose(r.max_drawdown,(wealth/np.maximum.accumulate(wealth)-1).min())
        assert np.isclose(r.cost_fraction_initial,g.cost.sum()/1e6)
    left=nav[(nav.model=='peers_risk_size') & (nav['style']=='all_equal')].sort_values(['fee','date'])
    right=nav[(nav.model=='peers_valuation') & (nav['style']=='all_equal')].sort_values(['fee','date'])
    assert np.allclose(left.nav,right.nav)


def test_incomplete_corporate_action_windows_are_not_called_reconstructed():
    labels=pd.read_parquet(EP/'outputs/local_cache/reinvested_labels.parquet')
    assert labels.loc[labels.status!='ok','reinvested_return'].isna().all()
    assert np.isfinite(labels.loc[labels.status=='ok','reinvested_return']).all()
    bad=labels[(labels.instrument=='SZ300110') & (labels.date==pd.Timestamp('2017-03-31')) & (labels.horizon==126)]
    assert len(bad)==1 and bad.iloc[0].status=='unexplained_adjustment_event'

"""Outcome-free feasibility check for contemporaneous, backward-return peers."""
import hashlib
import json
import numpy as np
import pandas as pd
from prepare_panel import DATA
from build_improvement_features import FEATURE_PANEL
from build_price_volume_features import EVENTS
from run_distribution_shape_models import DEST

DATES = pd.to_datetime(['2019-06-28', '2021-01-29', '2024-01-31', '2026-04-30'])
PROBE = DEST/'next_peer_probe'


def peer_features(history, current, limit=20, minimum=10):
    """Members known at this decision; no label input or persistent industry IDs."""
    assert history.columns.is_unique and current.index.is_unique
    assert set(history.columns) == set(current.index)
    # Remove the same-date median return of the known current membership.
    residual = history.sub(history.median(axis=1), axis=0)
    corr = residual.corr(min_periods=126)
    np.fill_diagonal(corr.values, np.nan)
    rows = []
    for stock in sorted(current.index):
        eligible = corr[stock].dropna().sort_values(ascending=False, kind='stable')
        selected = eligible[eligible > .2].head(limit)
        assert stock not in selected.index
        record = dict(instrument=stock, neighbors=len(selected), available=len(selected) >= minimum,
            mean_peer_correlation=float(selected.mean()) if len(selected) else np.nan,
            peer_instruments=';'.join(selected.index))
        for n in [21, 63, 126]:
            values = current.loc[selected.index, f'mom{n}'].dropna()
            record[f'peer_mom{n}'] = float(values.mean()) if len(values) >= minimum else np.nan
            record[f'relative_peer_mom{n}'] = current.loc[stock, f'mom{n}']-record[f'peer_mom{n}']
            record[f'peer_support{n}'] = len(values)
        rows.append(record)
    return pd.DataFrame(rows).set_index('instrument')


def run():
    PROBE.mkdir(parents=True, exist_ok=True)
    columns = ['date', 'instrument', 'mom21', 'mom63', 'mom126', 'common_eligible']
    source = pd.read_parquet(FEATURE_PANEL, columns=columns)
    assert not any(c.startswith('y_') or 'label' in c or 'end_' in c for c in source)
    members = source[source.date.isin(DATES)]
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(DATA/'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    calendar = calendar[calendar <= DATES.max()]
    events = pd.read_csv(EVENTS, parse_dates=['date'])
    returns = {}; receipts = []; close_series = {}
    for stock in sorted(members.instrument.unique()):
        path = DATA/f'raw/akshare/day/qfq/{stock}.csv'
        raw = pd.read_csv(path, parse_dates=['date']).set_index('date').close
        assert raw.index.is_unique
        close = raw.reindex(calendar).where(lambda x: x > 0)
        r = close.pct_change(fill_method=None)
        bad = events.loc[events.instrument.eq(stock), 'date']
        r.loc[r.index.isin(bad)] = np.nan
        returns[stock] = r; close_series[stock] = close
        receipts.append(dict(instrument=stock, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    daily = pd.DataFrame(returns)
    output = []; summary = []
    for date, group in members.groupby('date', sort=True):
        current = group.set_index('instrument').sort_index()
        history = daily.loc[:date, current.index].tail(252)
        assert len(history) == 252 and history.index.max() <= date
        features = peer_features(history, current)
        # Re-read only the historical prefix of each series: appended future bars
        # cannot enter the formation period or its residual-return normalization.
        prefix_returns = {}
        for stock in current.index:
            r = close_series[stock].loc[:date].pct_change(fill_method=None)
            bad = events.loc[events.instrument.eq(stock) & events.date.le(date), 'date']
            r.loc[r.index.isin(bad)] = np.nan
            prefix_returns[stock] = r.tail(252)
        rebuilt = peer_features(pd.DataFrame(prefix_returns), current)
        pd.testing.assert_frame_equal(features, rebuilt)
        eligible = features.loc[current.index[current.common_eligible]]
        overlap = {}
        for n in [21, 63, 126]:
            overlap[f'peer_vs_own_mom{n}_spearman'] = float(features[f'peer_mom{n}'].corr(current[f'mom{n}'], method='spearman'))
        summary.append(dict(date=str(date.date()), historical_members=len(current), original_eligible=len(eligible),
            eligible_with_10_peers=int(eligible.available.sum()),
            eligible_with_all_peer_momenta=int(eligible[['peer_mom21','peer_mom63','peer_mom126']].notna().all(axis=1).sum()),
            median_neighbor_count=float(eligible.neighbors.median()),
            median_selected_correlation=float(eligible.mean_peer_correlation.median()), **overlap))
        output.append(features.reset_index().assign(date=date))
    pd.concat(output, ignore_index=True).to_parquet(PROBE/'four_date_features.parquet', index=False)
    pd.DataFrame(receipts).to_csv(PROBE/'source_receipts.csv', index=False)
    result = dict(status='feasibility_only_no_forecasts_or_outcome_scores', dates=summary,
        membership_sha256=hashlib.sha256(FEATURE_PANEL.read_bytes()).hexdigest(),
        events_sha256=hashlib.sha256(EVENTS.read_bytes()).hexdigest(), source_files=len(receipts),
        historical_prefix_reconstruction_passed=True,
        method='Current historical 500-member universe; past 252 daily simple returns with at least 126 paired observations; subtract per-day median of those members; up to 20 peers with correlation >0.2, at least 10 for momentum aggregates; self excluded.',
        limitations='Current historical membership used for its past correlation window; not official industry membership. Known price anomalies masked, historical price/universe revision bias remains. No predictive value established; no new candidate counted.')
    (PROBE/'audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    run()

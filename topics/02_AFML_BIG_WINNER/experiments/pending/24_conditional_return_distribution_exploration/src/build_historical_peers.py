"""R25 price-linkage peers formed using only then-known membership and bars."""
import hashlib
import json
import numpy as np
import pandas as pd
from prepare_panel import DATA, OUT, EP
from build_improvement_features import FEATURE_PANEL as MEMBERS_PANEL
from build_price_volume_features import PANEL as BASE_PANEL, EVENTS, DEST as BASE_SOURCE
from probe_lagged_peer_information import peer_features

DEST = OUT/'r25_historical_peers'
PANEL = OUT/'local_cache/historical_peer_panel.parquet'
MEMBERSHIPS = OUT/'local_cache/r25_peer_memberships.parquet'
FIELDS = ['peer_mom21', 'peer_mom63', 'peer_mom126', 'mean_peer_correlation', 'neighbors', 'available']
PEER0 = [f'linked0_{c}' for c in FIELDS]
PEER63 = [f'linked63_{c}' for c in FIELDS]


def formation_history(daily, date, stocks, gap):
    if gap not in [0, 63]:
        raise ValueError('Formation gaps are predefined at 0 and 63 sessions')
    past = daily.loc[:pd.Timestamp(date), stocks]
    return (past.iloc[:-gap] if gap else past).tail(252)


def build():
    DEST.mkdir(exist_ok=True)
    base = pd.read_parquet(BASE_PANEL)
    audit = json.loads((BASE_SOURCE/'feature_audit.json').read_text())
    assert hashlib.sha256(BASE_PANEL.read_bytes()).hexdigest() == audit['feature_sha256']
    columns = ['date', 'instrument', 'mom21', 'mom63', 'mom126', 'common_eligible']
    members = pd.read_parquet(MEMBERS_PANEL, columns=columns)
    assert not any(c.startswith('y_') or 'label' in c or 'end_' in c for c in columns)
    assert members.groupby('date').size().eq(500).all()
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(DATA/'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    calendar = calendar[calendar <= members.date.max()]
    events = pd.read_csv(EVENTS, parse_dates=['date'])
    series = {}; receipts = []
    for stock in sorted(members.instrument.unique()):
        path = DATA/f'raw/akshare/day/qfq/{stock}.csv'
        close = pd.read_csv(path, parse_dates=['date']).set_index('date').close
        assert close.index.is_unique
        close = close.reindex(calendar).where(lambda x: x > 0)
        r = close.pct_change(fill_method=None)
        r.loc[r.index.isin(events.loc[events.instrument.eq(stock), 'date'])] = np.nan
        series[stock] = r
        receipts.append(dict(instrument=stock, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    daily = pd.DataFrame(series); pieces = []; membership_rows = []; diagnostics = []
    for date, group in members.groupby('date', sort=True):
        current = group.set_index('instrument').sort_index()
        features = []
        for gap in [0, 63]:
            history = formation_history(daily, date, current.index, gap)
            f = peer_features(history, current)
            features.append(f[FIELDS].rename(columns=lambda c: f'linked{gap}_{c}'))
            last = history.index.max() if len(history) else pd.NaT
            membership_rows.append(f[['neighbors', 'peer_instruments']].reset_index().assign(date=date, gap=gap, formation_end=last))
            eligible = f.loc[current.index[current.common_eligible]]
            diagnostics.append(dict(date=str(date.date()), gap=gap, formation_days=len(history), formation_end=str(last),
                historical_members=len(current), eligible=len(eligible), available=int(eligible.available.sum()),
                complete_momenta=int(eligible[['peer_mom21', 'peer_mom63', 'peer_mom126']].notna().all(axis=1).sum()),
                median_neighbors=float(eligible.neighbors.median()) if len(eligible) else np.nan))
        both = pd.concat(features, axis=1).reset_index().assign(date=date)
        pieces.append(both)
        print(str(date.date()), 'peer windows complete', flush=True)
    added = pd.concat(pieces, ignore_index=True)
    result = base.merge(added, on=['date', 'instrument'], how='left', validate='one_to_one')
    assert len(result) == len(base) and not result.duplicated(['date', 'instrument']).any()
    pd.testing.assert_frame_equal(result[base.columns], base.reset_index(drop=True))
    result.to_parquet(PANEL, index=False)
    pd.concat(membership_rows, ignore_index=True).to_parquet(MEMBERSHIPS, index=False)
    pd.DataFrame(receipts).to_csv(DEST/'source_receipts.csv', index=False)
    pd.DataFrame(diagnostics).to_csv(DEST/'formation_audit.csv', index=False)
    test = result[result.date.ge('2021-01-01')]; assert len(test) == 27600
    summary = dict(original_rows=len(base), prediction_rows=len(test), historical_months=members.date.nunique(),
        historical_member_stocks=len(receipts), feature_sha256=hashlib.sha256(PANEL.read_bytes()).hexdigest(),
        base_sha256=hashlib.sha256(BASE_PANEL.read_bytes()).hexdigest(), members_sha256=hashlib.sha256(MEMBERS_PANEL.read_bytes()).hexdigest(),
        events_sha256=hashlib.sha256(EVENTS.read_bytes()).hexdigest(), membership_cache_sha256=hashlib.sha256(MEMBERSHIPS.read_bytes()).hexdigest(),
        plan_sha256=hashlib.sha256((EP/'notes/r25_historical_peers.md').read_bytes()).hexdigest(),
        test_missing_by_feature=test[PEER0+PEER63].isna().sum().to_dict(),
        test_available_by_gap={str(g): int(test[f'linked{g}_available'].sum()) for g in [0, 63]},
        new_inputs='No outcomes loaded for peer formation; original labels unchanged. Missing peers/price momentum stay NaN; observed peer counts and availability retained.',
        formation='Current historical 500 members, past at most 252 sessions, at least 126 valid paired returns. Same-day median removed. Top20 correlation>0.2, self excluded, at least10 peers for aggregate momentum. Gap63 ends formation before the most recent63 sessions.',
        limitations='Price-linkage neighborhood is not an official industry. Current known membership is applied to its past correlation window. Original selection/price-revision issues remain; no prediction improvement established by data coverage.')
    (DEST/'feature_audit.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    build()

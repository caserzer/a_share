"""R25 independently verify dates/membership, then rebuild real past prefixes."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import DATA, EP
from build_historical_peers import DEST, PANEL, MEMBERSHIPS, BASE_PANEL, MEMBERS_PANEL, EVENTS, FIELDS, PEER0, PEER63, formation_history
from probe_lagged_peer_information import peer_features


def run():
    fa = json.loads((DEST/'feature_audit.json').read_text())
    for path, key in [(PANEL, 'feature_sha256'), (BASE_PANEL, 'base_sha256'),
                      (MEMBERS_PANEL, 'members_sha256'), (EVENTS, 'events_sha256'),
                      (MEMBERSHIPS, 'membership_cache_sha256'), (EP/'notes/r25_historical_peers.md', 'plan_sha256')]:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == fa[key]
    receipts = pd.read_csv(DEST/'source_receipts.csv')
    assert len(receipts) == fa['historical_member_stocks'] and not receipts.instrument.duplicated().any()
    for r in receipts.itertuples():
        assert hashlib.sha256(Path(r.path).read_bytes()).hexdigest() == r.sha256
    base = pd.read_parquet(BASE_PANEL); panel = pd.read_parquet(PANEL)
    pd.testing.assert_frame_equal(panel[base.columns], base)
    assert panel[panel.date.ge('2021-01-01')].shape[0] == 27600
    members = pd.read_parquet(MEMBERS_PANEL, columns=['date', 'instrument', 'mom21', 'mom63', 'mom126'])
    selections = pd.read_parquet(MEMBERSHIPS)
    assert len(selections) == len(members)*2 and not selections.duplicated(['date', 'instrument', 'gap']).any()
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(DATA/'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    relations = 0
    for (date, gap), group in selections.groupby(['date', 'gap']):
        allowed = set(members[members.date.eq(date)].instrument)
        assert set(group.instrument) == allowed and len(group) == 500
        endpoint = calendar.get_indexer([date])[0]-gap
        assert calendar.get_indexer([date])[0] >= 0
        if endpoint < 0:
            assert group.formation_end.isna().all()
        else:
            assert group.formation_end.eq(calendar[endpoint]).all()
        for r in group.itertuples():
            neighbors = r.peer_instruments.split(';') if r.peer_instruments else []
            assert len(neighbors) == len(set(neighbors)) == r.neighbors <= 20
            assert r.instrument not in neighbors and set(neighbors) <= allowed
            relations += len(neighbors)
    events = pd.read_csv(EVENTS, parse_dates=['date']); prefix_checks = []
    for date in pd.to_datetime(['2019-06-28', '2021-01-29', '2024-01-31', '2026-04-30']):
        current = members[members.date.eq(date)].set_index('instrument').sort_index()
        past_calendar = calendar[calendar <= date]; series = {}
        for stock in current.index:
            raw = pd.read_csv(DATA/f'raw/akshare/day/qfq/{stock}.csv', parse_dates=['date']).set_index('date').close
            close = raw.loc[:date].reindex(past_calendar).where(lambda x: x > 0)
            r = close.pct_change(fill_method=None)
            r.loc[r.index.isin(events.loc[events.instrument.eq(stock) & events.date.le(date), 'date'])] = np.nan
            series[stock] = r
        daily = pd.DataFrame(series); saved = panel[panel.date.eq(date)].set_index('instrument')
        assert len(saved) > 0
        for gap in [0, 63]:
            f = peer_features(formation_history(daily, date, current.index, gap), current)
            np.testing.assert_allclose(saved[[f'linked{gap}_{c}' for c in FIELDS]].astype(float),
                f.loc[saved.index, FIELDS].astype(float), equal_nan=True, atol=1e-12)
            stored = selections[selections.date.eq(date) & selections.gap.eq(gap)].set_index('instrument')
            pd.testing.assert_series_equal(stored.peer_instruments.sort_index(), f.peer_instruments.sort_index())
            prefix_checks.append(dict(date=str(date.date()), gap=gap, original_stock_dates=len(saved), historical_members=len(current)))
    result = dict(technical_feature_integrity_passed=True, feature_sha256=fa['feature_sha256'],
        source_files_checked=len(receipts), membership_rows_checked=len(selections), directed_peer_relations_checked=relations,
        original_fields_and_labels_unchanged=True, no_self_or_future_members=True, all_formation_endpoints_verified=True,
        real_prefix_checks=prefix_checks, goal_achieved=False,
        note='Feature availability and temporal checks only; no forecast performance is claimed.')
    (DEST/'feature_integrity_audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    run()

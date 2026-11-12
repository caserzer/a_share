"""All primary-pool NEW events, descriptive fixed-horizon returns only."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP, CACHE, sha


def main():
    root = EP / 'outputs/evaluation_versions/e02_20261021'
    version = json.loads((root / 'version.json').read_text())
    events_path = next(Path(p) for p in version['observation_event_paths'] if Path(p).parent.name == 'A')
    source = Path(version['raw_path'])
    market_path = CACHE / 'forecast_v5/CSI_ALL.parquet'
    cutoff = pd.Timestamp(version['source_data_cutoff'])
    out = EP / 'outputs/post_entry_20_60_90_180_20261112'
    if out.exists():
        raise FileExistsError(out)
    receipt = json.loads((root / 'receipt.json').read_text())
    for path in [source, events_path]:
        assert sha(path) == receipt['inputs'][str(path)], path
    raw = pd.read_parquet(source, columns=['date', 'day_i', 'era', 'industry_code', 'block', 'nav'])
    raw = raw[raw.date.le(cutoff)]
    market = pd.read_parquet(market_path).close.loc[:cutoff]
    events = pd.read_parquet(events_path)
    events = events[events.kind.eq('NEW') & events.date.le(cutoff)]
    assert len(events) == 1459 and events.event_id.is_unique
    groups = {k: g.set_index('day_i').sort_index() for k, g in raw.groupby(['era', 'industry_code'])}
    dateidx = raw[['date', 'day_i']].drop_duplicates().set_index('date').day_i.to_dict()
    last = int(raw.day_i.max())
    rows = []
    for e in events.itertuples():
        start = int(dateidx[e.date])
        g = groups[e.era, e.industry_code]
        for h in [20, 60, 90, 180]:
            p = g.reindex(range(start, start + h + 1))
            valid = p.nav.gt(0).all() and p.block.eq(e.block).all()
            status = 'MATURE' if valid else 'IMMATURE' if start + h > last else 'DATA_OR_CLASSIFICATION_GAP'
            m = market.reindex(pd.DatetimeIndex(p.date))
            mk = valid and m.notna().all() and m.gt(0).all()
            absolute = float(p.nav.iloc[-1] / p.nav.iloc[0] - 1) if valid else None
            benchmark = float(m.iloc[-1] / m.iloc[0] - 1) if mk else None
            rows.append(dict(event_id=e.event_id, era=e.era, industry_code=e.industry_code,
                entry_date=e.date, horizon=h, end_date=p.date.iloc[-1], status=status,
                absolute_return=absolute, benchmark_return=benchmark,
                excess_return=absolute - benchmark if mk else None,
                relative_return=(1 + absolute)/(1 + benchmark)-1 if mk else None))
    paths = pd.DataFrame(rows)
    old = pd.read_parquet(EP / 'outputs/followup_versions/s04_20261021/all_new_paths.parquet')
    old = old[old.arm.eq('A') & old.horizon.isin([20, 60])]
    key = ['event_id', 'horizon']
    for col in ['status', 'absolute_return', 'relative_return']:
        pd.testing.assert_series_equal(paths[paths.horizon.isin([20, 60])].set_index(key)[col].sort_index(), old.set_index(key)[col].sort_index(), check_names=False)
    summary = []
    for h, g in paths.groupby('horizon'):
        row = dict(horizon=int(h), total=len(g), mature=int(g.status.eq('MATURE').sum()),
            immature=int(g.status.eq('IMMATURE').sum()), gap=int(g.status.eq('DATA_OR_CLASSIFICATION_GAP').sum()),
            relative_known=int(g.excess_return.notna().sum()))
        for col in ['absolute_return', 'excess_return', 'relative_return']:
            row[col + '_mean'] = float(g[col].mean())
            row[col + '_median'] = float(g[col].median())
        assert row['total'] == row['mature'] + row['immature'] + row['gap']
        summary.append(row)
    out.mkdir()
    paths.to_parquet(out / 'all_entries.parquet', index=False)
    pd.DataFrame(summary).to_csv(out / 'summary.csv', index=False)
    inputs = [source, market_path, events_path, root / 'version.json', Path(__file__)]
    (out / 'receipt.json').write_text(json.dumps(dict(
        cutoff=str(cutoff.date()), scope='All 1459 primary A NEW events, equal weight per entry, entry close to horizon close, regardless of exit; full same-chain path required; no fee deduction.',
        benchmark='CSI_ALL; excess_return = industry_return - market_return; relative_return = (1+industry_return)/(1+market_return)-1',
        checks='20/60 all-event statuses and absolute/relative returns exactly match existing frozen followup',
        inputs={str(p): sha(p) for p in inputs}, artifacts={p.name: sha(p) for p in out.iterdir()}), ensure_ascii=False, indent=2)+'\n')
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == '__main__':
    main()

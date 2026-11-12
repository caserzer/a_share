"""Full local catalog/date coverage; future fields are evaluation-only."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP, PRIOR, CACHE, sha


def main():
    oldfile = CACHE / 'extension_v2/sources/L3_SW2014.json'
    raw = json.loads(oldfile.read_text())
    assert raw['code'] == 0
    old = pd.DataFrame(raw['data']['items'], columns=raw['data']['fields'])
    old = old[['index_code', 'industry_name']].rename(columns={'index_code': 'industry_code'})
    old['era'] = 'SW2014'
    newfile = CACHE / 'industry_v1/L3.parquet'
    new = pd.read_parquet(newfile)[['index_code', 'industry_name']].rename(columns={'index_code': 'industry_code'})
    new['era'] = 'SW2021'
    assignments = CACHE / 'extension_v2/products/assignments.parquet'
    a = pd.read_parquet(assignments, columns=['era', 'level', 'industry_code', 'industry_name'])
    a = a[a.level.eq('L3')][['era', 'industry_code', 'industry_name']]
    catalog = pd.concat([old, new, a]).drop_duplicates(['era', 'industry_code'])
    daily = PRIOR / 'daily_industries.parquet'
    d = pd.read_parquet(daily)
    receipt = json.loads((PRIOR / 'receipt.json').read_text())
    calendar = next(Path(p) for p in receipt['inputs'] if p.endswith('/calendar.parquet'))
    days = pd.DatetimeIndex(pd.read_parquet(calendar).date).sort_values()
    assert days.is_unique
    assert not d.duplicated(['era', 'industry_code', 'date']).any()
    parts, summaries = [], []
    # Research-era boundaries from EP32 core.month_era; not official effective dates.
    for era, start, end in [('SW2014', '2017-01-01', '2021-11-30'), ('SW2021', '2022-01-01', str(days.max().date()))]:
        era_days = days[(days >= start) & (days <= end)]
        codes = catalog[catalog.era.eq(era)]
        for r in codes.itertuples():
            src = d[d.era.eq(era) & d.industry_code.eq(r.industry_code)]
            g = src.set_index('date').reindex(era_days)
            g.index.name = 'date'
            g['era'], g['industry_code'], g['industry_name'] = era, r.industry_code, r.industry_name
            g['day_i'] = days.get_indexer(era_days)
            g['source_row'] = g.index.isin(src.date)
            g['status'] = g.status.fillna('NO_LOCAL_PRICE_ROW')
            g['no_price_identity'] = src.empty
            for h in [20, 60]:
                cross = g.day_i + h > days.get_indexer([era_days.max()])[0] if era == 'SW2014' else pd.Series(False, index=g.index)
                immature = g.day_i + h >= len(days)
                same = (g.nav.notna() & g.block.notna() & g.block.eq(g.block.shift(-h))).fillna(False)
                state = pd.Series('INTERNAL_MISSING_PATH', index=g.index)
                state.loc[same] = 'VALUED_PATH'
                state.loc[immature] = 'RIGHT_CENSORED'
                state.loc[cross] = 'CLASSIFICATION_BOUNDARY'
                if src.empty:
                    state[:] = 'NO_PRICE_IDENTITY'
                g[f'eval_path_status{h}'] = state
                g[f'eval_cross_classification{h}'] = cross
                g[f'eval_right_censored{h}'] = immature
                assert not (same & (cross | immature)).any()
            g['history60'] = (g.nav.notna() & g.block.notna() & g.block.eq(g.block.shift(60))).fillna(False)
            parts.append(g.reset_index())
        summaries.append(dict(era=era, catalog=len(codes), sessions=len(era_days), expected_rows=len(codes)*len(era_days)))
    q = pd.concat(parts, ignore_index=True)
    assert len(q) == sum(s['expected_rows'] for s in summaries)
    assert not q.duplicated(['era', 'industry_code', 'date']).any()
    assert q.source_row.sum() == len(d)
    # Calendar transition gets its own ledger, not assigned arbitrarily to either taxonomy.
    transition = days[(days >= '2021-12-01') & (days <= '2021-12-31')]
    out = EP / 'outputs/r00_coverage'
    out.mkdir(parents=True, exist_ok=True)
    q.to_parquet(out / 'evaluation_coverage.parquet', index=False)
    catalog.to_json(out / 'catalog.json', orient='records', force_ascii=False, indent=2)
    stats = []
    for (era, year), g in q.groupby(['era', q.date.dt.year]):
        stats.append(dict(era=era, year=int(year), rows=len(g), source_rows=int(g.source_row.sum()),
                          nav_rows=int(g.nav.notna().sum()),
                          path_status={str(h): g[f'eval_path_status{h}'].value_counts().to_dict() for h in [20, 60]}))
    sources = [oldfile, newfile, assignments, daily, calendar, Path(__file__)]
    result = dict(status='COVERAGE_LEDGER_BUILT_NOT_LABEL_PROTOCOL', eras=summaries,
                  inputs={str(p): sha(p) for p in sources},
                  artifacts={p.name: sha(p) for p in [out/'evaluation_coverage.parquet',out/'catalog.json']},
                  source_rows=len(d), added_missing_rows=int((~q.source_row).sum()),
                  transition_dates=[str(x.date()) for x in transition], annual=stats,
                  limitations=['Catalog snapshots do not certify historical active membership or PIT',
                               'Future eval fields must never enter online signals',
                               'Era dates follow existing local research policy, not official effective-date proof',
                               '20/60 windows are support diagnostics, not approved labels'])
    (out / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['eras','source_rows','added_missing_rows']}, ensure_ascii=False))


if __name__ == '__main__':
    main()

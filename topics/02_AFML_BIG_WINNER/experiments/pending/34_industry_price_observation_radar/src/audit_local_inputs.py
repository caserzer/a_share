"""Read-only source audit; no signal scores, return labels or experiments."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

EP = Path(__file__).resolve().parents[1]
PRIOR = EP.parent / '33_industry_second_order_change/restart/p29'
CACHE = Path('/home/xiaolv/.cache/a_share/ep32')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    receipt = json.loads((PRIOR / 'receipt.json').read_text())
    calendar = next(Path(p) for p in receipt['inputs'] if p.endswith('/calendar.parquet'))
    paths = [PRIOR / 'daily_industries.parquet', CACHE / 'industry_v1/L3.parquet',
             CACHE / 'extension_v2/products/assignments.parquet', calendar]
    hashes = {str(p): sha(p) for p in paths}
    # Verify reusable upstream identity inputs without treating an old PASS as new proof.
    for p in paths[2:]:
        assert hashes[str(p)] == receipt['inputs'][str(p)], p
    d = pd.read_parquet(paths[0]).sort_values(['era', 'industry_code', 'date'])
    a = pd.read_parquet(paths[2], columns=['era', 'level', 'industry_code', 'industry_name'])
    a = a[a.level.eq('L3')][['era', 'industry_code', 'industry_name']].drop_duplicates(['era', 'industry_code'])
    r = pd.read_parquet(paths[1], columns=['index_code', 'industry_name']).rename(columns={'index_code': 'industry_code'})
    r['era'] = 'SW2021'
    catalog = pd.concat([r, a]).drop_duplicates(['era', 'industry_code'])
    assert not d.duplicated(['era', 'industry_code', 'date']).any()
    assert d.level.eq('L3').all()
    days = pd.DatetimeIndex(pd.read_parquet(calendar).date).sort_values()
    assert days.is_unique
    assert (days.get_indexer(d.date) == d.day_i.to_numpy()).all()
    assert d.nav.dropna().gt(0).all()
    assert d.loc[d.nav.notna(), 'block'].notna().all()
    assert set(map(tuple, d[['era', 'industry_code']].drop_duplicates().values)) <= set(map(tuple, catalog[['era', 'industry_code']].values))
    parts = []
    for _, g in d.groupby(['era', 'industry_code'], sort=True):
        g = g.copy()
        for _, b in g[g.nav.notna()].groupby('block'):
            assert np.all(np.diff(b.day_i) == 1)
        g['valued'] = g.nav.notna()
        g['proxy'] = g.valued & (g.stale_members.gt(0) | g.boundary_proxy)
        g['history60'] = (g.valued & g.block.eq(g.block.shift(60)) & g.day_i.sub(g.day_i.shift(60)).eq(60)).fillna(False)
        for h in [20, 60]:
            g[f'path{h}'] = (g.valued & g.block.eq(g.block.shift(-h)) & g.day_i.shift(-h).sub(g.day_i).eq(h)).fillna(False)
            g[f'right_censored{h}'] = g.day_i + h >= len(days)
            g[f'mature_missing{h}'] = ~g[f'right_censored{h}'] & ~g[f'path{h}']
            g[f'joint_support{h}'] = g.history60 & g[f'path{h}']
        parts.append(g)
    q = pd.concat(parts)
    metrics = ['valued', 'proxy', 'history60'] + [f'{m}{h}' for h in [20, 60] for m in ['path', 'right_censored', 'mature_missing', 'joint_support']]
    industries = []
    groups = {k: g for k, g in q.groupby(['era', 'industry_code'])}
    for row in catalog.sort_values(['era', 'industry_code']).itertuples():
        g = groups.get((row.era, row.industry_code))
        item = dict(era=row.era, industry_code=row.industry_code, industry_name=row.industry_name,
                    rows=0 if g is None else len(g), status='NO_LOCAL_PRICE_ROWS' if g is None else 'LOCAL_PRICE_ROWS')
        if g is not None:
            item.update(first=str(g.date.min().date()), last=str(g.date.max().date()),
                        counts={c: int(g[c].sum()) for c in metrics})
        industries.append(item)
    annual = []
    for (era, year), g in q.groupby(['era', q.date.dt.year]):
        annual.append(dict(era=era, year=int(year), rows=len(g), industries=int(g.industry_code.nunique()),
                           counts={c: int(g[c].sum()) for c in metrics}))
    for h in [20, 60]:
        assert (q[f'path{h}'].astype(int) + q[f'right_censored{h}'].astype(int) + q[f'mature_missing{h}'].astype(int)).eq(1).all()
    out = EP / 'outputs/r00_input_audit'
    out.mkdir(parents=True, exist_ok=True)
    result = dict(status='INPUT_STRUCTURE_CHECKED_NOT_PROTOCOL_VALIDATED',
                  inputs=hashes, script_sha256=sha(Path(__file__)),
                  plan_sha256=sha(EP / 'rounds/R00_plan.md'),
                  limits=['SW2014 catalog is local membership union, not certified complete historical catalog',
                          'SW2021 snapshot plus membership union is not contemporaneous active status',
                          'Daily table rows are not full catalog-date grid; absent dates remain unknown',
                          '20/60 windows are structural diagnostics only; no process counts or labels yet',
                          'Proxy NAV is not official index or certified PIT; no raw stock price re-audit here'],
                  rows=len(q), status_counts={str(k): int(v) for k, v in q.status.value_counts().items()},
                  catalog_by_era={str(k): int(v) for k, v in catalog.groupby('era').size().items()},
                  annual=annual, industries=industries)
    (out / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'rows', 'catalog_by_era', 'status_counts']}, ensure_ascii=False))
    print('no_price_rows', [i['industry_code'] for i in industries if i['rows'] == 0])


if __name__ == '__main__':
    main()

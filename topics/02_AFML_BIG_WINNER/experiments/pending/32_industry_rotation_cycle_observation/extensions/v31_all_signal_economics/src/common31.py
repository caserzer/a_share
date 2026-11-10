from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT.parent
OUT = ROOT / 'outputs'
CACHE = Path('/home/xiaolv/.cache/a_share/ep32/economics_v31')
OLD = CACHE.parent / 'forecast_v5'
KEY = ['era', 'level', 'industry_code', 'block']
TASK = ['frequency', 'threshold', 'benchmark', 'level']
START = pd.Timestamp('2021-01-01')
END = pd.Timestamp('2024-09-30')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def js(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(clean(value), ensure_ascii=False, indent=2,
                                   allow_nan=False, default=str) + '\n')


def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    refs = {}
    for root in [EXT.parent] + sorted(EXT.glob('v*')):
        if root == ROOT or root.name.startswith(('v32_', 'v33_')):
            continue
        manifest = root / 'outputs/manifest.json'
        if not manifest.exists():
            continue
        m = json.loads(manifest.read_text())
        for f in m['files']:
            p = root / f['path']
            assert sha(p) == f['sha256'], p
            refs[str(p)] = f['sha256']
        refs[str(manifest)] = sha(manifest)
    js(OUT / 'predecessors.json', refs)
    js(OUT / 'freeze.json', dict(plan_sha256=sha(ROOT / 'research_plan.md'),
        source_hashes={str(p): sha(p) for p in sorted((ROOT / 'src').glob('*.py'))},
        strict_PIT='BLOCKED_DATA', quality='Historical-proxy', independent_holdout=False))
    return refs


def finish(checks):
    refs = json.loads((OUT / 'predecessors.json').read_text())
    assert all(sha(p) == h for p, h in refs.items())
    checks.append('all predecessors unchanged')
    js(OUT / 'validation.json', dict(status='PASS', checks_count=len(checks), checks=checks))
    files = [dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size)
             for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts]
    js(OUT / 'manifest.json', dict(files=files, file_count=len(files)))


def md(frame):
    return '|' + '|'.join(map(str, frame.columns)) + '|\n|' + '|'.join(['---'] * len(frame.columns)) + '|\n' + '\n'.join(
        '|' + '|'.join(str(x) for x in row) + '|' for row in frame.itertuples(index=False, name=None)) + '\n'


def episode_starts(frame, calendar):
    """Causal six-calendar-month lockout, independent of realized outcomes."""
    flags = pd.Series(False, index=frame.index)
    for _, group in frame.groupby(KEY):
        release = pd.Timestamp.min
        for index, row in group.sort_values(['date', 'row_id']).iterrows():
            if row.date < release:
                continue
            flags.loc[index] = True
            entry_index = calendar.searchsorted(row.date, side='right')
            if entry_index >= len(calendar):
                release = pd.Timestamp.max
            else:
                target = calendar[entry_index] + pd.DateOffset(months=6)
                end_index = calendar.searchsorted(target)
                release = calendar[end_index] if end_index < len(calendar) else pd.Timestamp.max
    return flags


def top_k(frame, scores, counts, eligible=None):
    values = pd.Series(scores, index=frame.index).copy()
    if eligible is not None:
        values.loc[~eligible] = np.nan
    ranks = values.groupby([frame.date, frame.level]).rank(method='first', ascending=False)
    return ranks.le(counts)


def block_interval(dates, values, seed=32, blocks=12, repeats=1000):
    """Monthly moving block bootstrap; all industry observations kept together."""
    g = pd.DataFrame({'month': pd.DatetimeIndex(dates).to_period('M'), 'value': np.asarray(values)})
    grouped = g.groupby('month').value.agg(['sum', 'count'])
    if grouped.empty:
        return dict(estimate=np.nan, lower=np.nan, upper=np.nan, months=0)
    index = pd.period_range(grouped.index.min(), grouped.index.max(), freq='M')
    a = grouped.reindex(index, fill_value=0).to_numpy(float)
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(repeats):
        starts = rng.integers(0, len(a), size=int(np.ceil(len(a) / blocks)))
        ids = np.concatenate([(s + np.arange(blocks)) % len(a) for s in starts])[:len(a)]
        sums = a[ids].sum(axis=0)
        if sums[1] > 0:
            values.append(sums[0] / sums[1])
    return dict(estimate=float(a[:, 0].sum() / a[:, 1].sum()),
                lower=float(np.quantile(values, .025)), upper=float(np.quantile(values, .975)), months=len(a))

"""Read-only source audit and monthly exploratory price-proxy panel.

Run with the topic's .venv/bin/python. No forward fills or terminal-loss imputation.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

EP = Path(__file__).resolve().parents[1]
TOPIC = EP.parents[2]
DATA = TOPIC / 'data'
OUT = EP / 'outputs'


def build():
    (OUT / 'local_cache').mkdir(parents=True, exist_ok=True)
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(
        DATA / 'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    # Exclude an incomplete final calendar month.
    monthends = pd.Series(calendar, index=calendar).groupby(calendar.to_period('M')).last()
    monthends = pd.DatetimeIndex(monthends[monthends.dt.to_period('M') < calendar[-1].to_period('M')])
    membership_path = DATA / 'processed/universe/pit_topn_400_100_membership_daily.csv'
    members = pd.read_csv(membership_path, usecols=[
        'membership_date', 'instrument', 'total_market_cap_cny', 'board_bucket', 'status_source'])
    members['date'] = pd.to_datetime(members.pop('membership_date'))
    members = members[members.date.isin(monthends)].copy()
    index = pd.read_csv(DATA / 'processed/index/benchmark_indices_daily.csv')
    index = index[index.index_alias == 'csi300'].set_index('date')
    index.index = pd.to_datetime(index.index)
    bench = index.close.reindex(calendar)
    market = pd.DataFrame(index=calendar)
    market['market_mom126'] = bench / bench.shift(126) - 1
    market['market_vol63'] = bench.pct_change(fill_method=None).rolling(63).std() * np.sqrt(252)
    coverage, pieces = [], []
    for instrument, m in members.groupby('instrument', sort=True):
        path = DATA / f'raw/akshare/day/qfq/{instrument}.csv'
        if not path.exists():
            coverage.append({'instrument': instrument, 'status': 'missing_file'})
            continue
        bars = pd.read_csv(path, parse_dates=['date']).set_index('date').sort_index()
        duplicates = int(bars.index.duplicated().sum())
        if duplicates:
            raise ValueError(f'Duplicate dates: {instrument}')
        coverage.append({'instrument': instrument, 'status': 'read', 'start': str(bars.index.min().date()),
                         'end': str(bars.index.max().date()), 'rows': len(bars),
                         'nonpositive_close': int((bars.close <= 0).sum()), 'duplicate_dates': duplicates})
        b = bars.reindex(calendar)
        close = b.close.where(b.close > 0)
        ret = close.pct_change(fill_method=None)
        f = pd.DataFrame(index=calendar)
        for n in (21, 63, 126, 252):
            f[f'mom{n}'] = close / close.shift(n) - 1
        for n in (21, 63):
            f[f'vol{n}'] = ret.rolling(n).std() * np.sqrt(252)
        f['turnover21'] = b.turnover_rate.rolling(21).mean()
        f['log_money21'] = np.log1p(b.money.clip(lower=0).rolling(21).mean())
        f['drawdown252'] = close / close.rolling(252).max() - 1
        f['history_count252'] = close.notna().rolling(252).sum()
        for h in (126, 252):
            # Decision at month-end close, entry next session open, horizon end close.
            f[f'return{h}'] = close.shift(-h) / b.open.shift(-1).where(b.open.shift(-1) > 0) - 1
            f[f'label_end{h}'] = pd.Series(calendar, index=calendar).shift(-h)
            f[f'benchmark{h}'] = bench.shift(-h) / index.open.reindex(calendar).shift(-1) - 1
        f['entry_date'] = pd.Series(calendar, index=calendar).shift(-1)
        f = f.join(market).reindex(pd.DatetimeIndex(m.date))
        f.index.name = 'date'
        f = f.reset_index().merge(m, on='date', validate='one_to_one')
        pieces.append(f)
    panel = pd.concat(pieces, ignore_index=True).sort_values(['date', 'instrument'])
    panel['log_cap'] = np.log(panel.total_market_cap_cny.where(panel.total_market_cap_cny > 0))
    assert not panel.duplicated(['date', 'instrument']).any()
    assert (panel.entry_date > panel.date).all()
    panel.to_parquet(OUT / 'local_cache/monthly_panel.parquet', index=False)
    pd.DataFrame(coverage).to_csv(OUT / 'price_coverage.csv', index=False)
    missing = []
    for year, g in panel.groupby(panel.date.dt.year):
        for col in ['mom252', 'vol63', 'turnover21', 'return126', 'return252']:
            missing.append({'year': year, 'field': col, 'rows': len(g), 'missing': int(g[col].isna().sum())})
    pd.DataFrame(missing).to_csv(OUT / 'missing_by_year.csv', index=False)
    audit = {
        'calendar_start': str(calendar[0].date()), 'calendar_end': str(calendar[-1].date()),
        'panel_rows': len(panel), 'instruments': panel.instrument.nunique(), 'months': panel.date.nunique(),
        'last_month': str(panel.date.max().date()),
        'mature_126_rows': int(panel.return126.notna().sum()),
        'mature_252_rows': int(panel.return252.notna().sum()),
        'status_sources': sorted(panel.status_source.dropna().unique().tolist()),
        'return_semantics': 'qfq price proxy; next open to horizon close; NOT verified total return',
        'universe_semantics': 'existing top400 main/top100 chinext; lifetime ST exclusion bias unresolved',
        'missing_endpoint_policy': 'retained as missing; not assumed zero or total loss',
        'coverage_scope': 'existing universe instruments only, not all historical A-shares',
    }
    (OUT / 'data_audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    build()

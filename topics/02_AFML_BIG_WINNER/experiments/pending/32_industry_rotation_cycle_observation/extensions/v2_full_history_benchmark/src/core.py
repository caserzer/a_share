"""Full-calendar, version-separated EP32 observation and benchmark arithmetic."""
from pathlib import Path
from datetime import datetime, timezone
import sys
import json
import gzip
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

EP = Path(__file__).resolve().parents[1]
OLD = EP.parents[1]
sys.path.insert(0, str(OLD / 'src'))
import observe as v1

OUT = EP / 'outputs'
CACHE = Path.home() / '.cache/a_share/ep32/extension_v2/products'
SOURCES = CACHE.parent / 'sources'
BENCHMARKS = ['CSI300', 'CSI_ALL', 'ALL_A_EW_PROXY']


def write_json(path, value):
    v1.write_json(path, value)


def csv(name, frame):
    path = OUT / (name + '.csv')
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator='\n')


def detail(name, frame):
    CACHE.mkdir(parents=True, exist_ok=True)
    private = CACHE / (name + '.csv')
    frame.to_csv(private, index=False, lineterminator='\n')
    public = OUT / 'details' / (name + '.csv.gz')
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_bytes(gzip.compress(private.read_bytes(), mtime=0))


def build_panel():
    CACHE.mkdir(parents=True, exist_ok=True)
    r5, r2 = v1.Release('pit_v5'), v1.Release('backfill_v2')
    inv = r5.read('inputs/normalized/securities.parquet')
    old = r2.read('normalized/securities.parquet')
    cont = r5.read('inputs/normalized/code_intervals.parquet')
    bse = r5.read('inputs/inputs/baseline/normalized/code_intervals.parquet')
    days = pd.DatetimeIndex(r5.read('inputs/inputs/baseline/normalized/calendar.parquet').date).sort_values()
    last = days.max().to_period('M') - 1
    monthly = pd.DataFrame({'date': days, 'month': days.to_period('M')}).groupby('month').date.max()
    monthly = monthly[monthly.index <= last]
    months = monthly.index
    ends = pd.DatetimeIndex(monthly.values)
    nexts = pd.DatetimeIndex([days[days.searchsorted(d, side='right')] for d in ends])
    aliases = {}
    for row in inv.itertuples():
        names = {row.instrument, row.metadata_instrument_v3}
        names.update(cont.loc[cont.security_id.eq(row.security_id), 'instrument'])
        names.update(bse.loc[bse.security_id.eq(row.security_id), 'historical_instrument'])
        for name in names:
            if pd.notna(name):
                aliases.setdefault(name, set()).add(row.security_id)
    unique = {k: next(iter(v)) for k, v in aliases.items() if len(v) == 1}
    old_ids = {}
    for row in old.itertuples():
        if row.instrument in unique:
            old_ids.setdefault(unique[row.instrument], []).append(row.security_id)
    frames, coverage = [], []
    share_rows = share_known = 0
    columns = ['date', 'close', 'qfq_close', 'qfq_open', 'close_conflict', 'open_conflict',
               'factor_chain_id', 'volume', 'vendor_trade_status']
    for i, row in enumerate(inv.itertuples()):
        name = f'normalized/prices_qfq/{row.security_id}.parquet'
        if name not in r5.files:
            continue
        schema = set(pq.read_schema(r5.root / name).names)
        bars = r5.read(name, columns=[c for c in columns if c in schema]).set_index('date').sort_index()
        if 'vendor_trade_status' not in bars:
            bars['vendor_trade_status'] = None
        assert not bars.index.duplicated().any()
        c, op = bars.reindex(ends), bars.reindex(nexts)
        f = pd.DataFrame(dict(month=months, date=ends, entry_date=nexts, security_id=row.security_id,
            instrument=row.instrument, name=row.name, raw_close=c.close.values,
            qfq_close=c.qfq_close.values, close_chain=c.factor_chain_id.values,
            entry_open=op.qfq_open.values, entry_chain=op.factor_chain_id.values))
        for numeric in ['raw_close', 'qfq_close', 'entry_open']:
            f[numeric] = pd.to_numeric(f[numeric], errors='raise').astype(float)
        close_good = c.close_conflict.eq(False).values & np.isfinite(f.qfq_close) & f.qfq_close.gt(0)
        raw_good = c.close_conflict.eq(False).values & np.isfinite(f.raw_close) & f.raw_close.gt(0)
        f.loc[~close_good, 'qfq_close'] = np.nan
        f.loc[~raw_good, 'raw_close'] = np.nan
        open_good = (op.open_conflict.eq(False).values & op.volume.gt(0).values &
            (op.vendor_trade_status.astype(str).isin(['1', '1.0']) | op.vendor_trade_status.isna()).values &
            np.isfinite(f.entry_open) & f.entry_open.gt(0))
        f.loc[~open_good, 'entry_open'] = np.nan
        pieces = []
        for sid in old_ids.get(row.security_id, []):
            part = f'normalized/shares/{sid}.parquet'
            if part in r2.files:
                pieces.append(r2.read(part))
        shares = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
        share_rows += len(shares)
        if len(shares):
            share_known += int(shares.known_at.notna().sum())
        s = v1.shares_asof(shares, ends)
        f['total_shares'] = s.total_shares.to_numpy()
        f['share_effective_date'] = s.get('effective_date', pd.Series(pd.NaT, index=s.index)).to_numpy()
        f['cap'] = f.raw_close * f.total_shares
        listing = row.bse_listing_proxy if row.exchange == 'BJ' else row.listing_date
        f['listed'] = (ends >= listing) & (pd.isna(row.delist_date) | (ends < row.delist_date)) & (not row.identity_date_conflict)
        f['next_return'] = f.qfq_close.shift(-1) / f.qfq_close - 1
        f.loc[f.close_chain.ne(f.close_chain.shift(-1)), 'next_return'] = np.nan
        frames.append(f)
        coverage.append(dict(security_id=row.security_id, months=len(f), eligible=int(f.listed.sum()),
                             cap_available=int((f.listed & f.cap.notna()).sum())))
        if (i + 1) % 1000 == 0:
            print('V2 verified price/share inputs', i + 1, '/', len(inv), flush=True)
    panel = pd.concat(frames, ignore_index=True)
    panel.to_parquet(CACHE / 'panel.parquet', index=False)
    write_json(CACHE / 'aliases.json', unique)
    csv('audits/security_coverage', pd.DataFrame(coverage))
    source = dict(status='PASS', price_release=str(r5.root), price_manifest_sha256=v1.sha(r5.manifest),
                  share_release=str(r2.root), shares_manifest_sha256=v1.sha(r2.manifest),
                  price_files=r5.reads, share_files=r2.reads,
                  first_session=str(days.min().date()), last_session=str(days.max().date()),
                  first_month=str(months.min()), last_complete_month=str(last), months=len(months),
                  source_share_rows=share_rows, known_at_share_rows=share_known,
                  panel_sha256=v1.sha(CACHE / 'panel.parquet'), strict_PIT='BLOCKED_DATA', quality='Historical-proxy')
    write_json(OUT / 'audits/inputs.json', source)
    return panel, unique, source


def load_members(aliases):
    meta = json.loads((SOURCES / 'manifest.json').read_text())
    assert v1.sha(SOURCES / 'legacy_members.parquet') == meta['legacy_members_sha256']
    for r in meta['receipts']:
        assert v1.sha(r['path']) == r['sha256']
    old = pd.read_parquet(SOURCES / 'legacy_members.parquet').rename(columns={
        'con_code': 'ts_code', 'index_code': 'industry_code'})
    old['era'] = 'SW2014'
    newroot = CACHE.parents[1] / 'industry_v1'
    newmeta = json.loads((newroot / 'manifest.json').read_text())
    assert v1.sha(newroot / 'members.parquet') == newmeta['membership_sha256']
    for r in newmeta['raw_receipts']:
        assert v1.sha(r['path']) == r['sha256']
    new = pd.read_parquet(newroot / 'members.parquet')
    chunks = []
    for level, prefix in [('L2', 'l2'), ('L3', 'l3')]:
        f = new[['ts_code', 'in_date', 'out_date', prefix + '_code', prefix + '_name']].rename(
            columns={prefix + '_code': 'industry_code', prefix + '_name': 'industry_name'})
        f = f.assign(level=level, era='SW2021')
        chunks.append(f)
    m = pd.concat([old[['ts_code', 'in_date', 'out_date', 'industry_code', 'industry_name', 'level', 'era']]] + chunks, ignore_index=True)
    m = m.drop_duplicates()
    m['instrument'] = m.ts_code.str[-2:] + m.ts_code.str[:6]
    m['security_id'] = m.instrument.map(aliases)
    m['in_date'] = pd.to_datetime(m.in_date, format='%Y%m%d', errors='raise')
    m['out_date'] = pd.to_datetime(m.out_date, format='%Y%m%d', errors='coerce')
    assert not (m.out_date < m.in_date).any()
    return m


def assign(panel, members):
    chunks, audit = [], []
    for month, p in panel.groupby('month', sort=True):
        era = era_for_month(month)
        if era is None:
            audit.append(dict(month=str(month), era='TRANSITION_GAP', level='ALL', eligible=int(p.listed.sum()),
                              assigned=0, industries=0, ambiguous=0, unresolved=0))
            continue
        active = v1.active_members(members[members.era.eq(era)], p.date.iloc[0])
        for level in ['L2', 'L3']:
            f = active[active.level.eq(level)][['security_id', 'industry_code', 'industry_name']].drop_duplicates()
            counts = f[f.security_id.notna()].groupby('security_id').industry_code.nunique()
            bad = set(counts[counts.gt(1)].index)
            unknown = f[f.security_id.isna() | f.security_id.isin(bad)].groupby('industry_code').size()
            known = f[f.security_id.notna() & ~f.security_id.isin(bad)].drop_duplicates('security_id')
            g = p[p.listed].merge(known, on='security_id', how='inner', validate='one_to_one')
            g['unresolved'] = g.industry_code.map(unknown).fillna(0).astype(int)
            g['level'] = level
            g['era'] = era
            chunks.append(g)
            audit.append(dict(month=str(month), era=era, level=level, eligible=int(p.listed.sum()),
                assigned=len(g), industries=g.industry_code.nunique(), ambiguous=len(bad),
                unresolved=int(f.security_id.isna().sum())))
    joined = pd.concat(chunks, ignore_index=True)
    joined.to_parquet(CACHE / 'assignments.parquet', index=False)
    csv('audits/membership_by_month', pd.DataFrame(audit))
    return joined


def era_for_month(month):
    month = pd.Period(month, freq='M')
    return 'SW2014' if month <= pd.Period('2021-11') else 'SW2021' if month >= pd.Period('2022-01') else None


def benchmark_data(panel):
    months = sorted(panel.month.unique())
    dates = panel.groupby('month').agg(date=('date', 'first'), entry_date=('entry_date', 'first'))
    px = panel.pivot(index='security_id', columns='month', values='qfq_close')
    ch = panel.pivot(index='security_id', columns='month', values='close_chain')
    future, history, rows = {}, {}, []
    for name, code in [('CSI300', '000300.SH'), ('CSI_ALL', '000985.CSI')]:
        f = pd.read_parquet(SOURCES / (code + '.parquet')).set_index('date').sort_index()
        close = f.reindex(dates.date).close.to_numpy(float)
        op = f.reindex(dates.entry_date).open.to_numpy(float)
        for i, month in enumerate(months):
            hist = close[i + 1] / close[i] - 1 if i + 1 < len(months) else np.nan
            history[(name, month)] = hist
            target = pd.period_range(month + 1, month + 12, freq='M')
            values = pd.Series(close, index=months).reindex(target).to_numpy(float) / op[i] - 1
            future[(name, month)] = (values, np.isfinite(values).astype(float))
            rows.append(dict(benchmark=name, month=str(month), origin_date=str(dates.loc[month, 'date'].date()),
                             entry_date=str(dates.loc[month, 'entry_date'].date()), origin_close=close[i],
                             entry_open=op[i], next_month_close_return=hist))
    for month, eligible in panel[panel.listed].groupby('month'):
        ids = eligible.security_id.tolist()
        entry = eligible.entry_open.to_numpy(float)
        ec = eligible.entry_chain.to_numpy()
        target = pd.period_range(month + 1, month + 12, freq='M')
        closes = px.reindex(index=ids, columns=target).to_numpy(float)
        chains = ch.reindex(index=ids, columns=target).to_numpy()
        valid = (chains == ec[:, None]) & np.isfinite(entry[:, None]) & (entry[:, None] > 0)
        rets = np.where(valid, closes / entry[:, None] - 1, np.nan)
        count = np.isfinite(rets).sum(axis=0)
        mean = np.divide(np.nansum(rets, axis=0), count, out=np.full(12, np.nan), where=count > 0)
        future[('ALL_A_EW_PROXY', month)] = (mean, count / len(ids))
        history[('ALL_A_EW_PROXY', month)] = eligible.next_return.mean()
        rows.append(dict(benchmark='ALL_A_EW_PROXY', month=str(month), origin_date=str(dates.loc[month, 'date'].date()),
                         entry_date=str(dates.loc[month, 'entry_date'].date()), origin_close=None,
                         entry_open=None, next_month_close_return=eligible.next_return.mean()))
    csv('audits/benchmark_dates', pd.DataFrame(rows))
    return history, future


def states(joined, panel, benchmark_history):
    keys = ['era', 'level', 'industry_code', 'industry_name', 'month']
    origin = joined.groupby(keys, sort=True).agg(members=('security_id', 'size'),
        rankable=('cap', 'count'), unresolved=('unresolved', 'max'), return_count=('next_return', 'count'),
        next_return=('next_return', 'mean')).reset_index()
    origin['rank_complete'] = origin.members.eq(origin.rankable) & origin.unresolved.eq(0)
    origin['return_coverage'] = origin.return_count / (origin.members + origin.unresolved)
    series = origin.copy()
    series['month'] = series.month + 1
    series = series[series.apply(lambda r: era_for_month(r.month) == r.era, axis=1)]
    series = series[series.month.le(panel.month.max())]
    series.loc[series.members.lt(5) | series.return_coverage.lt(.8), 'next_return'] = np.nan
    frames, run_rows = [], []
    for (era, level, code), g in series.groupby(['era', 'level', 'industry_code']):
        g = g.sort_values('month').set_index('month')
        allowed = [m for m in sorted(panel.month.unique()) if era_for_month(m) == era]
        g = g.reindex(allowed)
        industry_log = np.log1p(g.next_return).rolling(12, min_periods=12).sum()
        for benchmark in BENCHMARKS:
            bench = pd.Series([benchmark_history.get((benchmark, m - 1), np.nan) for m in g.index], index=g.index)
            bench_log = np.log1p(bench).rolling(12, min_periods=12).sum()
            frames.append(pd.DataFrame(dict(era=era, level=level, industry_code=code,
                industry_name=next(x for x in g.industry_name if pd.notna(x)), month=g.index,
                benchmark=benchmark, industry_trailing12=np.expm1(industry_log.to_numpy()),
                benchmark_trailing12=np.expm1(bench_log.to_numpy()),
                trailing_excess=(np.expm1(industry_log) - np.expm1(bench_log)).to_numpy())))
    state = pd.concat(frames, ignore_index=True)
    group = ['era', 'level', 'month', 'benchmark']
    rank = state.groupby(group).trailing_excess.rank(pct=True, method='average')
    count = state.groupby(group).trailing_excess.transform('count')
    state['leader'] = ((rank > .75) & state.trailing_excess.gt(0)).astype(float).where(count.ge(10) & rank.notna())
    state['rank_percentile'] = rank
    state = state.sort_values(['era', 'level', 'industry_code', 'benchmark', 'month'])
    by = state.groupby(['era', 'level', 'industry_code', 'benchmark'])
    state['entry_event'] = state.leader.eq(1) & by.leader.shift(1).eq(0) & by.month.shift(1).eq(state.month - 1)
    # Explicitly calculate runs independently within each taxonomy and benchmark.
    for (era, benchmark), g in state.groupby(['era', 'benchmark']):
        tmp = g.rename(columns={'leader': 'leader12'})
        for r in v1.leading_runs(tmp, 12):
            r.update(era=era, benchmark=benchmark)
            run_rows.append(r)
    joined_origin = origin.merge(pd.DataFrame({'benchmark': BENCHMARKS}), how='cross').merge(
        state, on=['era', 'level', 'industry_code', 'industry_name', 'month', 'benchmark'],
        how='left', validate='one_to_one')
    joined_origin['entry_event'] = joined_origin.entry_event.eq(True)
    runs = pd.DataFrame(run_rows)
    detail('industry_states', state)
    csv('metrics/leading_runs', runs)
    return joined_origin, state, runs


def prefix_length(positive):
    n = 0
    for v in positive:
        if not v:
            break
        n += 1
    return n


def score(joined, origins, panel, futures):
    px = panel.pivot(index='security_id', columns='month', values='qfq_close')
    ch = panel.pivot(index='security_id', columns='month', values='close_chain')
    outcomes, paths = [], []
    metadata = origins.set_index(['era', 'level', 'industry_code', 'month', 'benchmark'])
    last = panel.month.max()
    for i, (key, g) in enumerate(joined.groupby(['era', 'level', 'industry_code', 'month'], sort=True)):
        era, level, code, month = key
        if len(g) < 5 or not g.cap.notna().all() or not g.unresolved.eq(0).all():
            continue
        g = g.sort_values(['cap', 'security_id'], ascending=[False, True])
        ids = g.security_id.tolist()
        target = pd.period_range(month + 1, month + 12, freq='M')
        close = px.reindex(index=ids, columns=target).to_numpy(float)
        chains = ch.reindex(index=ids, columns=target).to_numpy()
        entry = g.entry_open.to_numpy(float)
        ec = g.entry_chain.to_numpy()
        valid = (chains == ec[:, None]) & np.isfinite(entry[:, None]) & (entry[:, None] > 0)
        ret = np.where(valid, close / entry[:, None] - 1, np.nan)
        known_count = np.isfinite(ret).sum(axis=0)
        industry = np.divide(np.nansum(ret, axis=0), known_count, out=np.full(12, np.nan), where=known_count > 0)
        industry_coverage = known_count / (len(ids) + int(g.unresolved.max()))
        industry[industry_coverage < .8] = np.nan
        top = ret[:3]
        portfolio = top.mean(axis=0)  # any unknown constituent keeps the mean unknown
        for benchmark in BENCHMARKS:
            r = metadata.loc[(era, level, code, month, benchmark)]
            bench, bench_coverage = futures[(benchmark, month)]
            excess = top - bench[None, :]
            complete_path = np.isfinite(excess).all(axis=0)
            for h in [9, 12]:
                terminal = top[:, h - 1]
                known = np.isfinite(terminal)
                bm = bench[h - 1]
                bm_known = bool(np.isfinite(bm))
                complete = bool(known.all() and bm_known)
                path_complete = bool(complete_path[:h].all())
                joint = (excess[:, :h] > 0).all(axis=0) if path_complete else None
                mature = month + h <= last
                outcomes.append(dict(era=era, level=level, industry_code=code,
                    industry_name=g.industry_name.iloc[0], month=str(month), horizon=h,
                    benchmark=benchmark, members=len(g), entry_event=bool(r.entry_event),
                    leader=r.leader if pd.notna(r.leader) else None,
                    top3=';'.join(g.head(3).instrument), display_names_current=';'.join(g.head(3)['name']),
                    mature=mature, complete=complete, path_complete=path_complete,
                    known_stocks=int(known.sum()), benchmark_known=bm_known,
                    status='KNOWN_INFERRED' if complete else 'UNKNOWN' if mature else 'CENSORED',
                    mean_return=float(portfolio[h - 1]) if known.all() else None,
                    worst_return=float(terminal.min()) if known.all() else None,
                    benchmark_return=float(bm) if bm_known else None,
                    stock1_return=float(terminal[0]) if known[0] else None,
                    stock2_return=float(terminal[1]) if known[1] else None,
                    stock3_return=float(terminal[2]) if known[2] else None,
                    stock1_excess=float(terminal[0] - bm) if known[0] and bm_known else None,
                    stock2_excess=float(terminal[1] - bm) if known[1] and bm_known else None,
                    stock3_excess=float(terminal[2] - bm) if known[2] and bm_known else None,
                    benchmark_coverage=float(bench_coverage[h - 1]),
                    portfolio_excess=float(portfolio[h - 1] - bm) if complete else None,
                    worst_excess=float(terminal.min() - bm) if complete else None,
                    all_beat=bool((terminal > bm).all()) if complete else None,
                    all_positive=bool((terminal > 0).all()) if known.all() else None,
                    any_known_fail_beat=bool(bm_known and (terminal[known] <= bm).any()),
                    industry_return=float(industry[h - 1]) if np.isfinite(industry[h - 1]) else None,
                    industry_excess=float(industry[h - 1] - bm) if np.isfinite(industry[h - 1]) and bm_known else None,
                    industry_coverage=float(industry_coverage[h - 1]),
                    joint_excess_run=v1.longest_true(joint) if path_complete else None,
                    joint_excess_from_first=prefix_length(joint) if path_complete else None,
                    joint_positive_run=v1.longest_true((top[:, :h] > 0).all(axis=0)) if np.isfinite(top[:, :h]).all() else None))
            if r.entry_event:
                for j in range(3):
                    for h in range(12):
                        paths.append(dict(era=era, level=level, industry_code=code, industry_name=g.industry_name.iloc[0],
                            month=str(month), benchmark=benchmark, instrument=g.iloc[j].instrument,
                            current_name=g.iloc[j]['name'], rank=j + 1, horizon_month=h + 1,
                            endpoint=str(month + h + 1), stock_return=top[j, h],
                            benchmark_return=bench[h], excess=excess[j, h]))
        if (i + 1) % 4000 == 0:
            print('V2 scored origins', i + 1, flush=True)
    outcome = pd.DataFrame(outcomes)
    path = pd.DataFrame(paths)
    detail('top3_outcomes', outcome)
    detail('entry_stock_paths', path)
    return outcome, path

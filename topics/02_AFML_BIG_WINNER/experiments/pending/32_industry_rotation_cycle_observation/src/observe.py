"""EP32 first observation, with explicit historical-proxy and missing-data gates."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

EP = Path(__file__).resolve().parents[1]
PRE = EP.parent / '30_pit_data_foundation_v1'
OUT = EP / 'outputs'
CACHE = Path.home() / '.cache/a_share/ep32/observation_v1'
IND = CACHE.parent / 'industry_v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str, allow_nan=False) + '\n')


def csv(name, frame):
    target = OUT / (name + '.csv')
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False, lineterminator='\n')


class Release:
    def __init__(self, version):
        p = PRE / 'outputs' / version / 'release.json'
        self.root = Path(json.loads(p.read_text())['path'])
        self.manifest = self.root / 'FULL_MANIFEST.json'
        complete = json.loads((self.root / 'COMPLETE.json').read_text())
        assert sha(self.manifest) == complete['full_manifest_sha256']
        self.files = {r['relative_path']: r for r in json.loads(self.manifest.read_text())}
        self.reads = {}

    def read(self, name, columns=None):
        p = self.root / name
        r = self.files[name]
        assert p.stat().st_size == r['bytes'] and sha(p) == r['sha256'], name
        self.reads[name] = r['sha256']
        return pd.read_parquet(p, columns=columns)


def shares_asof(frame, dates):
    """Effective-date proxy only. Conflicting latest assertions remain missing."""
    if frame.empty:
        return pd.DataFrame({'date': dates, 'total_shares': np.nan, 'share_known_at': pd.NaT})
    f = frame.copy()
    f['effective_date'] = pd.to_datetime(f.effective_date)
    f['known_at'] = pd.to_datetime(f.get('known_at', pd.NaT), utc=True).dt.tz_localize(None)
    grouped = f.groupby('effective_date', sort=True)
    summary = grouped.agg(total_shares=('total_shares', 'first'),
                          assertions=('total_shares', 'nunique'), share_known_at=('known_at', 'max'))
    summary.loc[summary.assertions.ne(1) | summary.total_shares.le(0), 'total_shares'] = np.nan
    if 'total_shares_conflict' in f:
        conflict = grouped.total_shares_conflict.any()
        summary.loc[conflict, 'total_shares'] = np.nan
    summary = summary.reset_index()
    return pd.merge_asof(pd.DataFrame({'date': dates}), summary, left_on='date',
                         right_on='effective_date', direction='backward')


def longest_true(values):
    best = run = 0
    for value in values:
        run = run + 1 if pd.notna(value) and bool(value) else 0
        best = max(best, run)
    return best


def path_stats(path):
    """No interpolation. Missing paths have no claimed continuous duration."""
    p = np.asarray(path, dtype=float)
    if not np.isfinite(p).all():
        return dict(positive_run=np.nan, monthly_up_run=np.nan, max_drawdown=np.nan)
    wealth = np.r_[1., 1. + p]
    return dict(positive_run=longest_true(p > 0),
                monthly_up_run=longest_true(np.diff(wealth) > 0),
                max_drawdown=float(np.min(wealth / np.maximum.accumulate(wealth) - 1)))


def active_members(members, day):
    # Exact boundaries are excluded because provider interval time-of-day is unknown.
    return members[members.in_date.lt(day) & (members.out_date.isna() | members.out_date.gt(day))].copy()


def leading_runs(frame, window):
    """Invalid/missing months break runs; both edge censoring flags survive."""
    rows = []
    for (level, code), g in frame.groupby(['level', 'industry_code']):
        g = g.sort_values('month').set_index('month')
        grid = pd.period_range(g.index.min(), g.index.max(), freq='M')
        s = g.reindex(grid)[f'leader{window}']
        for start in range(len(s)):
            if s.iloc[start] != 1 or (start and s.iloc[start - 1] == 1):
                continue
            end = start
            while end + 1 < len(s) and s.iloc[end + 1] == 1:
                end += 1
            rows.append(dict(level=level, industry_code=code,
                             industry_name=g.industry_name.iloc[0], window=window,
                             start=str(grid[start]), end=str(grid[end]), months=end - start + 1,
                             left_censored=start == 0 or pd.isna(s.iloc[start - 1]),
                             right_censored=end == len(s) - 1 or pd.isna(s.iloc[end + 1])))
    return rows


def load_panel():
    CACHE.mkdir(parents=True, exist_ok=True)
    r5, r2 = Release('pit_v5'), Release('backfill_v2')
    inventory = r5.read('inputs/normalized/securities.parquet')
    inventory2 = r2.read('normalized/securities.parquet')
    continuous = r5.read('inputs/normalized/code_intervals.parquet')
    bse = r5.read('inputs/inputs/baseline/normalized/code_intervals.parquet')
    days = pd.DatetimeIndex(r5.read('inputs/inputs/baseline/normalized/calendar.parquet').date).sort_values()
    # Conservative: exclude the terminal partial month and every month before 2022.
    last_period = days.max().to_period('M') - 1
    monthly = pd.DataFrame({'date': days, 'month': days.to_period('M')}).groupby('month').date.max()
    monthly = monthly[(monthly.index >= pd.Period('2022-01')) & (monthly.index <= last_period)]
    months = monthly.index
    ends = pd.DatetimeIndex(monthly.values)
    nexts = pd.DatetimeIndex([days[days.searchsorted(d, side='right')] for d in ends])
    aliases = {}
    for row in inventory.itertuples():
        names = {row.instrument, row.metadata_instrument_v3}
        names.update(continuous.loc[continuous.security_id.eq(row.security_id), 'instrument'])
        names.update(bse.loc[bse.security_id.eq(row.security_id), 'historical_instrument'])
        for name in names:
            if pd.notna(name):
                aliases.setdefault(name, set()).add(row.security_id)
    unique = {k: next(iter(v)) for k, v in aliases.items() if len(v) == 1}
    old_sid_map = {}
    for row in inventory2.itertuples():
        if row.instrument in unique:
            old_sid_map.setdefault(unique[row.instrument], []).append(row.security_id)
    frames, audit = [], []
    source_known = source_rows = 0
    cols = ['date', 'close', 'qfq_close', 'qfq_open', 'close_conflict', 'open_conflict',
            'factor_chain_id', 'volume', 'vendor_trade_status']
    for i, row in enumerate(inventory.itertuples()):
        name = f'normalized/prices_qfq/{row.security_id}.parquet'
        if name not in r5.files:
            audit.append(dict(security_id=row.security_id, price_partition=False))
            continue
        present = set(pq.read_schema(r5.root / name).names)
        bars = r5.read(name, columns=[c for c in cols if c in present])
        if 'vendor_trade_status' not in bars:
            bars['vendor_trade_status'] = None
        bars = bars.set_index('date').sort_index()
        assert not bars.index.duplicated().any()
        close = bars.reindex(ends)
        op = bars.reindex(nexts)
        f = pd.DataFrame(dict(month=months, date=ends, entry_date=nexts, security_id=row.security_id,
                              instrument=row.instrument, name=row.name,
                              raw_close=close.close.values, qfq_close=close.qfq_close.values,
                              close_chain=close.factor_chain_id.values,
                              entry_open=op.qfq_open.values, entry_chain=op.factor_chain_id.values))
        bad_close = close.close_conflict.fillna(True).astype(bool).values | ~np.isfinite(f.qfq_close) | f.qfq_close.le(0)
        f.loc[bad_close, 'qfq_close'] = np.nan
        f.loc[close.close_conflict.fillna(True).astype(bool).values | f.raw_close.le(0), 'raw_close'] = np.nan
        good_entry = (op.open_conflict.eq(False).values & op.volume.gt(0).values &
                      (op.vendor_trade_status.astype(str).isin(['1', '1.0']) | op.vendor_trade_status.isna()).values &
                      np.isfinite(f.entry_open) & f.entry_open.gt(0))
        f.loc[~good_entry, 'entry_open'] = np.nan
        source = []
        for old_sid in old_sid_map.get(row.security_id, []):
            part = f'normalized/shares/{old_sid}.parquet'
            if part in r2.files:
                source.append(r2.read(part))
        shares = pd.concat(source, ignore_index=True) if source else pd.DataFrame()
        source_rows += len(shares)
        if len(shares):
            source_known += int(shares.known_at.notna().sum())
        s = shares_asof(shares, ends)
        f['total_shares'] = s.total_shares.values
        f['share_known_at'] = s.share_known_at.values
        f['cap'] = f.raw_close * f.total_shares
        f['listed'] = (ends >= (row.bse_listing_proxy if row.exchange == 'BJ' else row.listing_date))
        f['listed'] &= pd.isna(row.delist_date) | (ends < row.delist_date)
        f['listed'] &= not row.identity_date_conflict
        # A next-month outcome uses the exact calendar endpoint and same adjustment chain.
        f['next_return'] = f.qfq_close.shift(-1) / f.qfq_close - 1
        f.loc[f.close_chain.ne(f.close_chain.shift(-1)), 'next_return'] = np.nan
        frames.append(f)
        audit.append(dict(security_id=row.security_id, price_partition=True,
                          month_rows=len(f), visible_months=int(f.listed.sum()),
                          entry_status_unknown_months=int(op.vendor_trade_status.isna().sum()),
                          cap_available_months=int((f.listed & f.cap.notna()).sum())))
        if (i + 1) % 700 == 0:
            print('Verified monthly panel', i + 1, '/', len(inventory), flush=True)
    panel = pd.concat(frames, ignore_index=True)
    panel.to_parquet(CACHE / 'panel.parquet', index=False)
    csv('audits/security_coverage', pd.DataFrame(audit))
    source = dict(price_release=str(r5.root), price_manifest_sha256=sha(r5.manifest),
                  shares_release=str(r2.root), shares_manifest_sha256=sha(r2.manifest),
                  source_share_rows=source_rows, source_share_rows_with_known_at=source_known,
                  price_files=r5.reads, shares_files=r2.reads,
                  calendar_last_day=str(days.max().date()), complete_month_cutoff=str(months[-1]),
                  months=len(months), inventory_identities=len(inventory),
                  strict_PIT='BLOCKED_DATA', quality='Historical-proxy', private_panel=str(CACHE / 'panel.parquet'))
    write_json(OUT / 'audits/input_verification.json', source)
    write_json(CACHE / 'identity_map.json', unique)
    print('Panel ready:', len(panel), 'security months', flush=True)
    return panel, unique, source


def assignments(panel, aliases):
    meta = json.loads((IND / 'manifest.json').read_text())
    assert sha(IND / 'members.parquet') == meta['membership_sha256']
    for r in meta['raw_receipts']:
        assert sha(r['path']) == r['sha256']
    m = pd.read_parquet(IND / 'members.parquet')
    m['instrument'] = m.ts_code.str[-2:] + m.ts_code.str[:6]
    m['security_id'] = m.instrument.map(aliases)
    m['in_date'] = pd.to_datetime(m.in_date, format='%Y%m%d', errors='raise')
    m['out_date'] = pd.to_datetime(m.out_date, format='%Y%m%d', errors='coerce')
    chunks, audit = [], []
    for month, p in panel.groupby('month', sort=True):
        date = p.date.iloc[0]
        active = active_members(m, date)
        for level in ['L2', 'L3']:
            n = 'l2' if level == 'L2' else 'l3'
            f = active[['security_id', n + '_code', n + '_name']].rename(
                columns={n + '_code': 'industry_code', n + '_name': 'industry_name'}).drop_duplicates()
            # Multiple classifications for one stable identity are not arbitrarily resolved.
            known = f[f.security_id.notna()]
            ambiguous = known.groupby('security_id').industry_code.nunique().gt(1)
            bad = set(ambiguous[ambiguous].index)
            unknown = f[f.security_id.isna() | f.security_id.isin(bad)].groupby('industry_code').size()
            f = f[f.security_id.notna() & ~f.security_id.isin(bad)].drop_duplicates('security_id')
            joined = p[p.listed].merge(f, on='security_id', how='inner', validate='one_to_one')
            joined['level'] = level
            joined['unresolved_members'] = joined.industry_code.map(unknown).fillna(0).astype(int)
            chunks.append(joined)
            audit.append(dict(month=str(month), level=level, eligible_identities=int(p.listed.sum()),
                              active_source_rows=len(active), assigned=len(joined),
                              ambiguous_identities=len(bad), unmapped_source_rows=int(active.security_id.isna().sum()),
                              industries=joined.industry_code.nunique()))
    joined = pd.concat(chunks, ignore_index=True)
    joined.to_parquet(CACHE / 'assignments.parquet', index=False)
    csv('audits/monthly_membership', pd.DataFrame(audit))
    return joined


def industry_series(joined, panel):
    origin = joined.groupby(['level', 'industry_code', 'industry_name', 'month'], sort=True).agg(
        members=('security_id', 'size'), rankable=('cap', 'count'),
        unresolved=('unresolved_members', 'max'),
        return_count=('next_return', 'count'), next_return=('next_return', 'mean')).reset_index()
    origin['rank_complete'] = origin.members.eq(origin.rankable) & origin.unresolved.eq(0)
    origin['return_coverage'] = origin.return_count / (origin.members + origin.unresolved)
    market = panel[panel.listed].groupby('month').next_return.mean()
    origin['market_next_return'] = origin.month.map(market)
    # The row labelled month t contains the realized return of the previous month's members.
    series = origin.copy()
    series['month'] = series.month + 1
    series = series[series.month.le(origin.month.max())]
    series.loc[series.members.lt(5) | series.return_coverage.lt(.8), 'next_return'] = np.nan
    for window in [1, 6, 12]:
        out = []
        for (level, code), g in series.groupby(['level', 'industry_code']):
            g = g.sort_values('month').set_index('month')
            g = g.reindex(pd.period_range(origin.month.min(), origin.month.max(), freq='M'))
            x = np.log1p(g.next_return) - np.log1p(g.market_next_return)
            out.append(pd.DataFrame(dict(level=level, industry_code=code, month=g.index,
                                         value=x.rolling(window, min_periods=window).sum().values)))
        values = pd.concat(out, ignore_index=True)
        series = series.merge(values.rename(columns={'value': f'strength{window}'}),
                              on=['level', 'industry_code', 'month'], how='left', validate='one_to_one')
        count = series.groupby(['level', 'month'])[f'strength{window}'].transform('count')
        rank = series.groupby(['level', 'month'])[f'strength{window}'].rank(pct=True, method='average')
        series[f'leader{window}'] = (rank > .75).astype(float).where(count.ge(10) & rank.notna())
    # Signals attach by observation month, never by the next outcome month.
    signal = series[['level', 'industry_code', 'month', 'leader1', 'leader6', 'leader12', 'strength12']]
    origin = origin.merge(signal, on=['level', 'industry_code', 'month'], how='left', validate='one_to_one')
    origin = origin.sort_values(['level', 'industry_code', 'month'])
    prior = origin.groupby(['level', 'industry_code']).leader12.shift(1)
    prior_month = origin.groupby(['level', 'industry_code']).month.shift(1)
    origin['entry_event'] = origin.leader12.eq(1) & prior.eq(0) & prior_month.eq(origin.month - 1)
    csv('metrics/industry_months', origin)
    csv('metrics/industry_price_series', series)
    runs = pd.DataFrame([r for window in [1, 6, 12] for r in leading_runs(series, window)])
    csv('metrics/leading_runs', runs)
    return origin, series, runs


def outcomes(joined, origin, panel):
    months = sorted(panel.month.unique())
    px = panel.pivot(index='security_id', columns='month', values='qfq_close')
    chains = panel.pivot(index='security_id', columns='month', values='close_chain')
    lookup = panel.set_index(['security_id', 'month'])
    market_paths = {}
    for month, eligible in panel[panel.listed].groupby('month'):
        ids = eligible.security_id.tolist()
        ep = eligible.entry_open.to_numpy(float)
        chain = eligible.entry_chain.to_numpy()
        target = pd.period_range(month + 1, month + 12, freq='M')
        close = px.reindex(index=ids, columns=target).to_numpy(float)
        ch = chains.reindex(index=ids, columns=target).to_numpy()
        good = (ch == chain[:, None]) & np.isfinite(ep[:, None]) & (ep[:, None] > 0)
        returns = np.where(good, close / ep[:, None] - 1, np.nan)
        count = np.isfinite(returns).sum(axis=0)
        mean = np.divide(np.nansum(returns, axis=0), count,
                         out=np.full(12, np.nan), where=count > 0)
        market_paths[month] = (mean, count / len(ids))
    results, paths = [], []
    grouped = joined.groupby(['level', 'industry_code', 'month'], sort=False)
    for i, r in enumerate(origin.itertuples()):
        if r.members < 3:
            continue
        g = grouped.get_group((r.level, r.industry_code, r.month)).copy()
        # Do not call an incomplete observed rank the industry top three.
        if not r.rank_complete:
            continue
        top = g.sort_values(['cap', 'security_id'], ascending=[False, True]).head(3)
        sids = top.security_id.tolist()
        all_sids = g.security_id.tolist()
        entry = lookup.loc[[(s, r.month) for s in all_sids]]
        ep = entry.entry_open.to_numpy(float)
        ec = entry.entry_chain.to_numpy()
        target_months = pd.period_range(r.month + 1, r.month + 12, freq='M')
        available = [m for m in target_months if m in months]
        values = np.full((len(all_sids), 12), np.nan)
        if available:
            close = px.reindex(index=all_sids, columns=available).to_numpy(float)
            ch = chains.reindex(index=all_sids, columns=available).to_numpy()
            valid = (ch == ec[:, None]) & np.isfinite(ep[:, None]) & (ep[:, None] > 0)
            values[:, :len(available)] = np.where(valid, close / ep[:, None] - 1, np.nan)
        inds = [all_sids.index(s) for s in sids]
        top_path = values[inds]
        for horizon in [9, 12]:
            terminal = top_path[:, horizon - 1]
            known = np.isfinite(terminal)
            mature = r.month + horizon <= months[-1]
            complete = bool(known.all())
            portfolio_path = top_path[:, :horizon].mean(axis=0) if np.isfinite(top_path[:, :horizon]).all() else np.full(horizon, np.nan)
            stats = path_stats(portfolio_path)
            market, market_coverage = market_paths[r.month]
            relative = (1 + portfolio_path) / (1 + market[:horizon]) - 1
            stats['relative_positive_run'] = (longest_true(relative > 0)
                                               if np.isfinite(relative).all() else np.nan)
            stats['joint_positive_run'] = (longest_true((top_path[:, :horizon] > 0).all(axis=0))
                                            if np.isfinite(top_path[:, :horizon]).all() else np.nan)
            all_terminal = values[:, horizon - 1]
            other = np.delete(all_terminal, inds)
            result = dict(level=r.level, industry_code=r.industry_code, industry_name=r.industry_name,
                          month=str(r.month), horizon=horizon, members=r.members,
                          entry_event=bool(r.entry_event), leader=r.leader12 if pd.notna(r.leader12) else None,
                          top3=';'.join(top.instrument), display_names_current=';'.join(top['name']),
                          mature=mature, known_stocks=int(known.sum()), complete=complete,
                          status='KNOWN_INFERRED' if complete else 'UNKNOWN' if mature else 'CENSORED',
                          mean_return=float(terminal.mean()) if complete else None,
                          worst_return=float(terminal.min()) if complete else None,
                          all_positive=bool((terminal > 0).all()) if complete else None,
                          any_known_nonpositive=bool((terminal[known] <= 0).any()),
                          industry_return=float(np.nanmean(all_terminal)) if np.isfinite(all_terminal).any() else None,
                          other_return=float(np.nanmean(other)) if np.isfinite(other).any() else None,
                          market_return=float(market[horizon - 1]) if np.isfinite(market[horizon - 1]) else None,
                          market_coverage=float(market_coverage[horizon - 1]),
                          benchmark_valid=int(np.isfinite(all_terminal).sum()),
                          **stats)
            results.append(result)
        if r.entry_event:
            for j, s in enumerate(sids):
                for h in range(12):
                    paths.append(dict(level=r.level, industry_code=r.industry_code, industry_name=r.industry_name,
                                      month=str(r.month), security_id=s, instrument=top.iloc[j].instrument,
                                      rank=j + 1, horizon_month=h + 1, endpoint=str(r.month + h + 1),
                                      price_return=top_path[j, h], cap_at_origin=top.iloc[j].cap,
                                      market_return=market_paths[r.month][0][h]))
        if (i + 1) % 1500 == 0:
            print('Outcome origins', i + 1, '/', len(origin), flush=True)
    result = pd.DataFrame(results)
    csv('metrics/top3_outcomes', result)
    csv('metrics/entry_stock_paths', pd.DataFrame(paths))
    return result


def main():
    write_json(OUT / 'audits/run_start.json', dict(
        status='working', started_at=datetime.now(timezone.utc).isoformat(),
        plan_sha256=sha(EP / 'research_plan.md'), goal_sha256=sha(EP / 'GOAL.md'),
        code_sha256=sha(Path(__file__)), no_predecessor_writes=True,
        levels=['L2', 'L3'], descriptive_only=True))
    panel, aliases, source = load_panel()
    joined = assignments(panel, aliases)
    origin, series, runs = industry_series(joined, panel)
    result = outcomes(joined, origin, panel)
    from report import build_report
    build_report(origin, series, runs, result, source)
    files = [dict(path=str(p.relative_to(EP)), sha256=sha(p), bytes=p.stat().st_size)
             for p in sorted(EP.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
             and '.pytest_cache' not in p.parts and p != OUT / 'manifest.json']
    write_json(OUT / 'manifest.json', dict(status='validated_working_result',
        finished_at=datetime.now(timezone.utc).isoformat(), files=files,
        quality='Historical-proxy', strict_PIT='BLOCKED_DATA', sealed=False,
        no_confirmatory_inference=True, no_trading_authorization=True))
    print('EP32 observation complete', flush=True)


if __name__ == '__main__':
    main()

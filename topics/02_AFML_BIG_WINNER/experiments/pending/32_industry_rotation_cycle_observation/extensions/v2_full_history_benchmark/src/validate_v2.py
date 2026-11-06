"""Validate full-history membership, exact benchmark dates, and all excess returns."""
from pathlib import Path
import json
import gzip
import re
import subprocess
import numpy as np
import pandas as pd
import core as c


def main():
    checks = []

    def check(name, value, **details):
        checks.append(dict(name=name, passed=bool(value), **details))
        if not value:
            c.write_json(c.OUT / 'audits/validation_latest_failed.json', dict(status='FAIL', checks=checks))
            raise AssertionError(name)

    panel = pd.read_parquet(c.CACHE / 'panel.parquet')
    joined = pd.read_parquet(c.CACHE / 'assignments.parquet')
    result = pd.read_csv(c.OUT / 'details/top3_outcomes.csv.gz')
    states = pd.read_csv(c.OUT / 'details/industry_states.csv.gz')
    source = json.loads((c.OUT / 'audits/inputs.json').read_text())
    check('full_117_months_from_2017_PIT_calendar_start',
          panel.month.min() == pd.Period('2017-01') and panel.month.max() == pd.Period('2026-09') and
          panel.month.nunique() == 117 and source['first_session'] == '2017-01-03')
    check('panel_unique_identity_month', not panel.duplicated(['security_id', 'month']).any())
    check('no_future_shares_for_market_cap', panel.loc[panel.cap.notna(), 'share_effective_date'].notna().all() and
          panel.loc[panel.cap.notna(), 'share_effective_date'].le(panel.loc[panel.cap.notna(), 'date']).all())
    check('market_cap_uses_raw_not_adjusted_price', np.allclose(panel.cap, panel.raw_close * panel.total_shares, equal_nan=True))
    check('unknown_known_at_not_upgraded', source['known_at_share_rows'] == 0 and source['strict_PIT'] == 'BLOCKED_DATA')
    check('taxonomy_never_backcast_or_spliced', all(c.era_for_month(m) == e for m, e in
          joined[['month', 'era']].drop_duplicates().itertuples(index=False, name=None)))
    check('transition_month_has_no_industry_assignments', not joined.month.eq(pd.Period('2021-12')).any())
    check('membership_unique_per_level', not joined.duplicated(['month', 'level', 'security_id']).any())
    aliases = json.loads((c.CACHE / 'aliases.json').read_text())
    members = c.load_members(aliases)
    member_failures = 0
    for (month, era, level), g in joined.groupby(['month', 'era', 'level']):
        day = g.date.iloc[0]
        allowed = c.v1.active_members(members[members.era.eq(era) & members.level.eq(level)], day)
        keys = set(zip(allowed.security_id, allowed.industry_code))
        member_failures += sum((s, code) not in keys for s, code in zip(g.security_id, g.industry_code))
    check('every_assignment_has_active_historical_interval', member_failures == 0, rows=len(joined))
    r5 = c.v1.Release('pit_v5')
    days = pd.DatetimeIndex(r5.read('inputs/inputs/baseline/normalized/calendar.parquet').date).sort_values()
    dates = panel.groupby('month').agg(date=('date', 'first'), entry_date=('entry_date', 'first'))
    expected_entry = [days[days.searchsorted(x, side='right')] for x in dates.date]
    check('all_entries_use_next_market_session', np.array_equal(dates.entry_date.to_numpy(), np.array(expected_entry, dtype='datetime64[ns]')))
    # Reconstruct every published origin ranking from the independent assignment table.
    ranks = {}
    for key, g in joined.groupby(['era', 'level', 'industry_code', 'month'], sort=False):
        if len(g) >= 5 and g.cap.notna().all() and g.unresolved.eq(0).all():
            ranks[(key[0], key[1], key[2], str(key[3]))] = ';'.join(
                g.sort_values(['cap', 'security_id'], ascending=[False, True]).head(3).instrument)
    published = result[['era', 'level', 'industry_code', 'month', 'top3']].drop_duplicates()
    check('every_top3_is_origin_market_cap_rank', all(r.top3 == ranks[(r.era, r.level, r.industry_code, r.month)]
          for r in published.itertuples()), unique_origins=len(published))
    # Vectorized independent recomputation of all three terminal price returns.
    pindex = panel.set_index(['instrument', 'month'])
    origin_month = pd.PeriodIndex(result.month, freq='M')
    terminal_month = origin_month + result.horizon.to_numpy(int)
    instruments = result.top3.str.split(';', expand=True)
    returns = []
    for rank in range(3):
        start = pd.MultiIndex.from_arrays([instruments[rank], origin_month])
        end = pd.MultiIndex.from_arrays([instruments[rank], terminal_month])
        op = pindex.entry_open.reindex(start).to_numpy(float)
        close = pindex.qfq_close.reindex(end).to_numpy(float)
        a = pindex.entry_chain.reindex(start).to_numpy()
        b = pindex.close_chain.reindex(end).to_numpy()
        returns.append(np.where(a == b, close / op - 1, np.nan))
    returns = np.asarray(returns)
    for rank in range(3):
        check('stock_' + str(rank + 1) + '_return_and_excess',
              np.allclose(returns[rank], result[f'stock{rank + 1}_return'], equal_nan=True) and
              np.allclose(returns[rank] - result.benchmark_return.to_numpy(float),
                          result[f'stock{rank + 1}_excess'], equal_nan=True))
    complete_stocks = np.isfinite(returns).all(axis=0)
    average = returns.mean(axis=0)
    worst = returns.min(axis=0)
    check('all_terminal_stock_returns_recomputed',
          np.allclose(average, result.mean_return, equal_nan=True, rtol=1e-10, atol=1e-10) and
          np.allclose(worst, result.worst_return, equal_nan=True, rtol=1e-10, atol=1e-10), rows=len(result))
    # Recompute actual index returns using raw date-keyed open and close, not report columns.
    for name, code in [('CSI300', '000300.SH'), ('CSI_ALL', '000985.CSI')]:
        raw = pd.read_parquet(c.SOURCES / (code + '.parquet')).set_index('date')
        check(name + '_nonempty_full_calendar_positive_prices', len(raw) == len(days) and
              set(raw.index) == set(days) and raw.ts_code.eq(code).all() and
              raw[['open', 'close']].gt(0).all().all(), sessions=len(raw))
        mask = result.benchmark.eq(name).to_numpy()
        mo = origin_month[mask]
        target = terminal_month[mask]
        entry_dates = dates.entry_date.reindex(mo).to_numpy()
        exit_dates = dates.date.reindex(target).to_numpy()
        expected = raw.close.reindex(exit_dates).to_numpy(float) / raw.open.reindex(entry_dates).to_numpy(float) - 1
        check(name + '_all_returns_same_entry_exit_dates', np.allclose(expected,
            result.loc[mask, 'benchmark_return'], equal_nan=True, rtol=1e-10, atol=1e-10), rows=int(mask.sum()))
    expected_excess = average - result.benchmark_return.to_numpy(float)
    check('all_excess_is_cumulative_return_difference', np.allclose(expected_excess,
          result.portfolio_excess, equal_nan=True, rtol=1e-10, atol=1e-10))
    k = result.complete.to_numpy(bool)
    check('all_three_beat_not_confused_with_average', np.array_equal(
        (returns[:, k] > result.loc[k, 'benchmark_return'].to_numpy()[None, :]).all(axis=0),
        result.loc[k, 'all_beat'].to_numpy(bool)))
    previous = c.CACHE.parent / 'attempt01_top3_outcomes.csv.gz'
    if previous.exists():
        old = pd.read_csv(previous)
        keys = ['era', 'level', 'industry_code', 'month', 'benchmark', 'horizon']
        keep = ['CSI300', 'ALL_A_EW_PROXY']
        a = old[old.benchmark.isin(keep)].set_index(keys).sort_index()
        b = result[result.benchmark.isin(keep)].set_index(keys).sort_index()
        pd.testing.assert_frame_equal(a, b[a.columns], check_dtype=False, rtol=1e-12, atol=1e-12)
        check('CSI300_and_EW_unchanged_after_index_identifier_fix', True, rows=len(a))
    check('missing_and_censored_not_market_zero',
          result.loc[~result.complete, ['portfolio_excess', 'all_beat']].isna().all().all() and
          result.loc[~result.mature, 'status'].eq('CENSORED').all())
    check('path_unknown_not_a_failed_duration',
          result.loc[~result.path_complete, ['joint_excess_run', 'joint_excess_from_first']].isna().all().all())
    check('every_leader_also_beat_benchmark_in_past', states.loc[states.leader.eq(1), 'trailing_excess'].gt(0).all())
    # Numeric prefix replay with future outcomes removed, and no output writes.
    history, futures = c.benchmark_data(panel)
    for cutoff in [pd.Period('2020-12'), pd.Period('2024-12')]:
        p = panel[panel.month.le(cutoff)].copy()
        j = joined[joined.month.le(cutoff)].copy()
        p.loc[p.month.eq(cutoff), 'next_return'] = np.nan
        j.loc[j.month.eq(cutoff), 'next_return'] = np.nan
        old_detail, old_csv = c.detail, c.csv
        c.detail = c.csv = lambda *a: None
        try:
            _, prefix, _ = c.states(j, p, history)
        finally:
            c.detail, c.csv = old_detail, old_csv
        keys = ['era', 'level', 'industry_code', 'benchmark', 'month']
        baseline = states.copy()
        baseline['month'] = pd.PeriodIndex(baseline.month, freq='M')
        baseline = baseline[baseline.month.le(cutoff)].set_index(keys)
        prefix = prefix.set_index(keys)
        idx = baseline.index.union(prefix.index)
        a, b = baseline.reindex(idx), prefix.reindex(idx)
        check('prefix_' + str(cutoff), all(np.allclose(a[f], b[f], equal_nan=True, atol=1e-10)
            for f in ['leader', 'trailing_excess']) and a.entry_event.fillna(False).equals(b.entry_event.fillna(False)))
    # Independent all-A equal-weight check for fixed-origin buy-and-hold universe.
    for month in [pd.Period('2018-06'), pd.Period('2020-03'), pd.Period('2024-09')]:
        origin = panel[panel.month.eq(month) & panel.listed].set_index('security_id')
        for h in [9, 12]:
            end = panel[panel.month.eq(month + h)].set_index('security_id').reindex(origin.index)
            values = (end.qfq_close / origin.entry_open - 1).where(end.close_chain.eq(origin.entry_chain))
            expected = values.mean()
            check('EW_same_fixed_universe_' + str(month) + '_' + str(h),
                  np.isclose(expected, futures[('ALL_A_EW_PROXY', month)][0][h - 1]))
    count = 0
    for root_key, files_key in [('price_release', 'price_files'), ('share_release', 'share_files')]:
        root = Path(source[root_key])
        for name, digest in source[files_key].items():
            if c.v1.sha(root / name) != digest:
                raise AssertionError('Changed prior input: ' + name)
            count += 1
    check('all_consumed_EP30_bytes_unchanged', True, files=count)
    saved = json.loads((c.OUT / 'audits/v1_baseline.json').read_text())
    check('V1_manifest_and_every_artifact_unchanged',
          c.v1.sha(c.OLD / 'outputs/manifest.json') == saved['manifest_sha256'] and
          all(c.v1.sha(c.OLD / r['path']) == r['sha256'] for r in saved['files']), files=len(saved['files']))
    check('older_tracked_files_unchanged', subprocess.run(['git', 'diff', '--quiet'], cwd=c.OLD.parents[4]).returncode == 0)
    for public in (c.OUT / 'details').glob('*.csv.gz'):
        private = c.CACHE / public.name[:-3]
        check('gzip_exact_' + public.stem, gzip.decompress(public.read_bytes()) == private.read_bytes())
    strict = pd.read_csv(c.OUT / 'screens/industry_and_all_three_beat.csv')
    check('all_screened_rows_meet_claimed_excess_conditions', strict.mature.all() and strict.complete.all() and
          strict.industry_excess.gt(0).all() and strict.portfolio_excess.gt(0).all() and strict.all_beat.eq(True).all())
    missing, links = [], 0
    for p in c.EP.rglob('*.md'):
        if 'attempts' in p.relative_to(c.EP).parts:
            continue  # Byte snapshots retain relative links in their original directory context.
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', p.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            links += 1
            if not (p.parent / target.split('#')[0]).exists():
                missing.append((str(p), target))
    check('all_report_links_exist', not missing, links=links, missing=missing)
    tests = subprocess.run([str(c.OLD.parents[2] / '.venv/bin/python'), '-m', 'pytest', '-q',
        str(c.OLD / 'tests'), str(c.EP / 'tests')], capture_output=True, text=True)
    check('temporal_and_benchmark_tests', tests.returncode == 0, output=tests.stdout.strip())
    c.write_json(c.OUT / 'audits/validation.json', dict(status='PASS', checks=checks,
        validates='data_lineage_timing_arithmetic_not_prediction_or_business_cycle'))
    files = [dict(path=str(p.relative_to(c.EP)), bytes=p.stat().st_size, sha256=c.v1.sha(p))
        for p in sorted(c.EP.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and
        '.pytest_cache' not in p.parts and p != c.OUT / 'manifest.json']
    c.write_json(c.OUT / 'manifest.json', dict(status='validated_working_result', files=files,
        quality='Historical-proxy', strict_PIT='BLOCKED_DATA', sealed=False))
    print('V2 validation PASS:', len(checks), 'checks;', count, 'prior data files verified')


if __name__ == '__main__':
    main()

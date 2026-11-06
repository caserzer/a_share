"""Independently check the interval audit and keep V1/V2 unchanged."""
from pathlib import Path
import json
import re
import subprocess
import numpy as np
import pandas as pd
import review as r


def main():
    checks = []

    def check(name, valid, **details):
        checks.append(dict(name=name, passed=bool(valid), **details))
        if not valid:
            r.js('audits/validation_failed', dict(status='FAIL', checks=checks))
            raise AssertionError(name)

    baseline = json.loads((r.OUT / 'audits/predecessors.json').read_text())
    for name, root in [('V1', r.OLD), ('V2', r.V2)]:
        old = baseline[name]
        check(name + '_all_bytes_unchanged', r.v2.v1.sha(root / 'outputs/manifest.json') == old['manifest_sha256'] and
              all(r.v2.v1.sha(root / f['path']) == f['sha256'] for f in old['files']), files=len(old['files']))
    identity = json.loads((r.OUT / 'audits/input_identity.json').read_text())
    check('V2_panel_not_modified', r.v2.v1.sha(r.v2.CACHE / 'panel.parquet') == identity['V2_panel_sha256'])
    check('V2_members_not_modified', r.v2.v1.sha(r.v2.CACHE / 'assignments.parquet') == identity['assignment_sha256'])
    root = Path(identity['price_release'])
    check('all_consumed_raw_partitions_unchanged', all(r.v2.v1.sha(root / name) == digest
          for name, digest in identity['consumed_raw_files'].items()), files=len(identity['consumed_raw_files']))
    sources = json.loads((r.OUT / 'audits/halt_sources.json').read_text())
    check('all_original_notice_PDF_hashes', all(r.v2.v1.sha(x['path']) == x['sha256'] for x in sources), documents=len(sources))
    panel = pd.read_parquet(r.v2.CACHE / 'panel.parquet')
    joined = pd.read_parquet(r.v2.CACHE / 'assignments.parquet')
    sectors = pd.read_csv(r.OUT / 'fixed_window/all_industries.csv')
    stocks = pd.read_csv(r.OUT / 'fixed_window/focus_top3_stocks.csv')
    valuations = pd.read_csv(r.OUT / 'audits/valuation_diagnostics.csv')
    origins = joined[joined.month.eq(r.ORIGIN)]
    expected = origins.groupby(['level', 'industry_code']).size()
    expected = set(expected[expected.ge(5)].index)
    actual = set(sectors[['level', 'industry_code']].itertuples(index=False, name=None))
    check('all_eligible_industries_in_fixed_window_query', actual == expected, industries=len(expected))
    check('same_requested_dates_for_every_benchmark', sectors.entry_date.eq('2025-07-01').all() and
          sectors.end_date.eq('2026-06-30').all())
    check('incomplete_cap_does_not_drop_sector_observation',
          (sectors.missing_cap_members.gt(0) & sectors.sector_observable & sectors.sector_excess.notna()).any())
    # Every stock-level number uses exact original entry and terminal quotes.
    quotes = panel.set_index(['instrument', 'month'])
    endpoint = panel.groupby('month').agg(date=('date', 'first'), entry_date=('entry_date', 'first'))
    for code, name in [('000300.SH', 'CSI300'), ('000985.CSI', 'CSI_ALL')]:
        index = pd.read_parquet(r.v2.SOURCES / (code + '.parquet')).set_index('date')
        expected_index = index.loc[pd.Timestamp('2026-06-30'), 'close'] / index.loc[pd.Timestamp('2025-07-01'), 'open'] - 1
        check(name + '_same_day_index_return', np.allclose(sectors.loc[sectors.benchmark.eq(name), 'benchmark_return'], expected_index))
    failures = []
    for x in stocks.itertuples():
        a, b = quotes.loc[(x.instrument, r.ORIGIN)], quotes.loc[(x.instrument, r.END)]
        value = b.qfq_close / a.entry_open - 1
        if a.entry_chain != b.close_chain or not np.isclose(value, x.return_value):
            failures.append(x.instrument)
        if not np.isclose(value - x.benchmark_return, x.excess):
            failures.append(x.instrument + ':excess')
    check('all_focus_stock_returns_and_excess_recomputed', not failures, rows=len(stocks), failures=failures)
    # Recompute all industry endpoints without the ranking diagnostic.
    industry_failures = []
    for x in sectors.itertuples():
        g = origins[origins.level.eq(x.level) & origins.industry_code.eq(x.industry_code)]
        entry = g.entry_open.to_numpy(float)
        end = panel[panel.month.eq(r.END)].set_index('security_id').reindex(g.security_id)
        val = end.qfq_close.to_numpy(float) / entry - 1
        same = end.close_chain.to_numpy() == g.entry_chain.to_numpy()
        val[~same] = np.nan
        count = np.isfinite(val).sum()
        cov = count / (len(g) + int(g.unresolved.max()))
        mean = float(np.nanmean(val)) if count and cov >= .8 else np.nan
        if not np.isclose(mean, x.sector_return, equal_nan=True) or not np.isclose(cov, x.return_coverage):
            industry_failures.append((x.level, x.industry_code))
    check('all_sector_returns_independent_of_rank_gate', not industry_failures,
          rows=len(sectors), failures=industry_failures[:10])
    check('documented_marks_are_past_valuation_only',
          not valuations.entry_price_imputed.any() and valuations.mark_used_only_for_rank.all() and
          (pd.to_datetime(valuations.valuation_date) <= pd.to_datetime(valuations.origin_date)).all())
    # No halt last-price mark may leak into the source's missing executable entry.
    target = valuations[valuations.instrument.eq('SH688313') & valuations.month.eq('2025-06')].iloc[0]
    original = quotes.loc[('SH688313', r.ORIGIN)]
    check('halt_diagnostic_does_not_invent_trade', pd.isna(original.raw_close) and pd.isna(original.entry_open) and
          pd.isna(target.entry_open_unchanged) and target.diagnostic_cap > 0)
    optical = sectors[sectors.industry_code.eq('851024.SI') & sectors.benchmark.eq('CSI300')].iloc[0]
    check('optical_rank_gap_and_supported_diagnostic_both_visible',
          not optical.strict_rank_complete and optical.diagnostic_rank_complete and
          optical.observed_top3 == 'SZ300308;SZ000063;SZ300502')
    check('industry_outperformance_not_confused_with_three_joint_success',
          optical.sector_excess > 0 and optical.candidate_mean_excess > 0 and
          optical.candidate_worst_excess < 0 and not optical.candidate_all_beat)
    semiconductor = sectors[sectors.industry_code.eq('801081.SI') & sectors.benchmark.eq('CSI300')].iloc[0]
    prior = pd.read_csv(r.V2 / 'outputs/details/top3_outcomes.csv.gz')
    old = prior[prior.industry_code.eq('801081.SI') & prior.month.eq('2025-06') & prior.horizon.eq(12) & prior.benchmark.eq('CSI300')].iloc[0]
    check('semiconductor_window_already_present_in_V2_detail',
          np.isclose(semiconductor.candidate_mean_excess, old.portfolio_excess) and not old.entry_event)
    gates = pd.read_csv(r.OUT / 'audits/focus_filter_trace.csv')
    january = gates[gates.industry_code.eq('801081.SI') & gates.month.eq('2025-01') & gates.benchmark.eq('CSI300')].iloc[0]
    check('january_semiconductor_entry_lost_to_nonleader_cap_gap',
          january.entry_event and not january.rank_complete and not january.scored_in_V2)
    tail = pd.read_csv(r.OUT / 'audits/all_open_leading_runs.csv')
    comm = tail[tail.industry_code.eq('801102.SI') & tail.benchmark.eq('CSI300')].iloc[0]
    net = tail[tail.industry_code.eq('851024.SI') & tail.benchmark.eq('CSI300')].iloc[0]
    check('open_and_over18_month_runs_retained', comm.months == 24 and net.months == 17 and
          comm.right_censored and net.right_censored)
    example = pd.read_csv(r.OUT / 'fixed_window/optical_illustrative_stocks.csv')
    check('optical_examples_not_relabelled_industry_top3', example.is_industry_top3.eq(False).all())
    missing, links = [], 0
    for p in r.EP.rglob('*.md'):
        for x in re.findall(r'\[[^\]]*\]\(([^)]+)\)', p.read_text()):
            if '://' in x or x.startswith('#'):
                continue
            links += 1
            if not (p.parent / x.split('#')[0]).exists():
                missing.append((str(p), x))
    check('all_local_report_links_valid', not missing, links=links, missing=missing)
    py = str(r.OLD.parents[2] / '.venv/bin/python')
    test = subprocess.run([py, '-m', 'pytest', '-q', str(r.EP / 'tests')], capture_output=True, text=True)
    check('valuation_temporal_tests', test.returncode == 0, output=test.stdout.strip())
    check('tracked_predecessors_unchanged', subprocess.run(['git', 'diff', '--quiet'], cwd=r.OLD.parents[4]).returncode == 0)
    r.js('audits/validation', dict(status='PASS', checks=checks, validates='review_and_fixed_window_not_prediction'))
    files = [dict(path=str(p.relative_to(r.EP)), bytes=p.stat().st_size, sha256=r.v2.v1.sha(p)) for p in sorted(r.EP.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p != r.OUT / 'manifest.json']
    r.js('manifest', dict(status='validated_working_review', files=files, sealed=False,
        strict_PIT='BLOCKED_DATA', no_V2_result_rewrite=True))
    print('Review validation PASS:', len(checks), 'checks;', len(expected), 'fixed-window industries')


if __name__ == '__main__':
    main()

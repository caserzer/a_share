"""Independent post-run checks of timing, fixed rankings, missingness and inputs."""
from pathlib import Path
import json
import subprocess
import numpy as np
import pandas as pd

import observe as o


def main():
    checks = []

    def check(name, condition, **detail):
        checks.append(dict(name=name, passed=bool(condition), **detail))
        if not condition:
            raise AssertionError(name)

    panel = pd.read_parquet(o.CACHE / 'panel.parquet')
    joined = pd.read_parquet(o.CACHE / 'assignments.parquet')
    origin = pd.read_csv(o.OUT / 'metrics/industry_months.csv')
    result = pd.read_csv(o.OUT / 'metrics/top3_outcomes.csv.gz')
    source = json.loads((o.OUT / 'audits/input_verification.json').read_text())
    check('panel_unique_stable_identity_month', not panel.duplicated(['security_id', 'month']).any())
    check('no_2021_taxonomy_backcast_before_2022', panel.month.min() == pd.Period('2022-01'))
    check('raw_price_times_effective_shares', np.allclose(panel.cap, panel.raw_close * panel.total_shares,
                                                       equal_nan=True))
    check('strict_PIT_not_upgraded', source['strict_PIT'] == 'BLOCKED_DATA' and
          source['source_share_rows_with_known_at'] == 0)
    check('next_calendar_session_not_later_stock_resumption', panel.groupby('month').entry_date.nunique().max() == 1)
    check('no_forward_endpoints_filled', result.loc[~result.mature, 'mean_return'].isna().all() and
          result.loc[~result.mature, 'status'].eq('CENSORED').all())
    check('unknown_joint_outcome_not_false_or_zero', result.loc[~result.complete, ['all_positive', 'mean_return', 'worst_return']].isna().all().all())
    import gzip
    check('compressed_public_detail_matches_private_original',
          gzip.decompress((o.OUT / 'metrics/top3_outcomes.csv.gz').read_bytes()) ==
          (o.CACHE / 'top3_outcomes.csv').read_bytes())
    # All published top-three identities must match a complete origin snapshot rank.
    expected = {}
    for key, g in joined.groupby(['level', 'industry_code', 'month']):
        if len(g) >= 3 and g.cap.notna().all() and g.unresolved_members.eq(0).all():
            expected[(key[0], key[1], str(key[2]))] = ';'.join(
                g.sort_values(['cap', 'security_id'], ascending=[False, True]).head(3).instrument)
    all_ranked = all(r.top3 == expected[(r.level, r.industry_code, r.month)] for r in result.itertuples())
    check('all_published_top3_fixed_by_origin_market_cap', all_ranked, rows=len(result))
    # Prefix replay: erase future outcomes, rerun only the state construction in memory.
    cutoff = pd.Period('2024-12')
    prefix_panel = panel[panel.month.le(cutoff)].copy()
    prefix_joined = joined[joined.month.le(cutoff)].copy()
    prefix_panel.loc[prefix_panel.month.eq(cutoff), 'next_return'] = np.nan
    prefix_joined.loc[prefix_joined.month.eq(cutoff), 'next_return'] = np.nan
    old_csv = o.csv
    o.csv = lambda *args: None
    try:
        po, _, _ = o.industry_series(prefix_joined, prefix_panel)
    finally:
        o.csv = old_csv
    original = origin.copy()
    original['month'] = pd.PeriodIndex(original.month, freq='M')
    key = ['level', 'industry_code', 'month']
    a = po.set_index(key).sort_index()
    b = original[original.month.le(cutoff)].set_index(key).sort_index()
    for field in ['leader1', 'leader6', 'leader12', 'strength12']:
        check('prefix_' + field, np.allclose(a[field], b[field], equal_nan=True, atol=1e-12))
    check('prefix_entry_events', a.entry_event.equals(b.entry_event))
    # Return arithmetic checked without using the outcome-builder function.
    px = panel.set_index(['instrument', 'month'])
    bad = []
    for row in result.itertuples():
        m = pd.Period(row.month)
        if not row.complete:
            continue
        vals = []
        for instrument in row.top3.split(';'):
            start = px.loc[(instrument, m)]
            end = px.loc[(instrument, m + row.horizon)]
            if start.entry_chain != end.close_chain:
                bad.append((row.month, instrument, 'chain'))
            vals.append(end.qfq_close / start.entry_open - 1)
        if not np.isclose(np.mean(vals), row.mean_return, rtol=1e-10, atol=1e-10):
            bad.append((row.month, row.industry_code, 'mean'))
        if bool(np.all(np.array(vals) > 0)) != row.all_positive:
            bad.append((row.month, row.industry_code, 'joint'))
    check('all_known_terminal_price_returns_recomputed', not bad,
          known_rows=int(result.complete.sum()), mismatches=bad[:10])
    count = 0
    for root_key, files_key in [('price_release', 'price_files'), ('shares_release', 'shares_files')]:
        root = Path(source[root_key])
        for name, expected_hash in source[files_key].items():
            if o.sha(root / name) != expected_hash:
                raise AssertionError('Changed input: ' + name)
            count += 1
    check('all_consumed_EP30_input_bytes_unchanged', True, files=count)
    legacy = o.EP.parent / '31_price_volume_hypotheses_oos_walk_forward'
    for name in ['publication', 'hypothesis_reports_v1']:
        records = json.loads((legacy / 'outputs/manifests' / (name + '.json')).read_text())['files']
        check('EP31_' + name + '_unchanged', all(o.sha(legacy / r['path']) == r['sha256'] for r in records), files=len(records))
    check('tracked_predecessors_unchanged', subprocess.run(['git', 'diff', '--quiet'], cwd=o.EP.parents[4]).returncode == 0)
    # A test run is captured as a receipt and does not substitute for empirical evidence.
    test = subprocess.run([str(o.EP.parents[2] / '.venv/bin/python'), '-m', 'pytest', '-q', str(o.EP / 'tests')],
                          capture_output=True, text=True)
    check('temporal_contract_tests', test.returncode == 0, output=test.stdout.strip())
    o.write_json(o.OUT / 'audits/validation.json', dict(status='PASS', checks=checks,
                 claims_validated='arithmetic_and_temporal_contract_not_economic_hypothesis'))
    # Record the unsuccessful anonymous official-file route as source-search evidence.
    probe = o.CACHE.parent / 'source_probe/receipts.json'
    if probe.exists():
        o.write_json(o.OUT / 'audits/source_search.json', dict(
            rejected_official_xls_probes=json.loads(probe.read_text()),
            selected_source='Tushare index_classify + index_member_all, verified TLS, existing permission',
            official_documentation='https://tushare.pro/document/2?doc_id=335',
            current_membership_only_sources_not_admitted=True,
            remaining_gap='effective intervals do not establish original known_at or revision history'))
    # Rebuild the working manifest after validation, keeping the original run-start receipt.
    files = [dict(path=str(p.relative_to(o.EP)), sha256=o.sha(p), bytes=p.stat().st_size)
             for p in sorted(o.EP.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
             and '.pytest_cache' not in p.parts and p != o.OUT / 'manifest.json']
    o.write_json(o.OUT / 'manifest.json', dict(status='validated_working_result', files=files,
        quality='Historical-proxy', strict_PIT='BLOCKED_DATA', sealed=False,
        no_confirmatory_inference=True, no_trading_authorization=True))
    print('Validation PASS:', len(checks), 'checks;', count, 'consumed input files')


if __name__ == '__main__':
    main()

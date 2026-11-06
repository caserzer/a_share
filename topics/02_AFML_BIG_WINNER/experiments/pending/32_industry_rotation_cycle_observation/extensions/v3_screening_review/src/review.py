"""Audit screening losses and query a user-specified window across all industries.

No V1/V2 data or rules are modified. Documented suspension marks affect only
an explicitly separate valuation diagnostic, never observed prices or entries.
"""
from pathlib import Path
from datetime import datetime, timezone
import sys
import json
import gzip
import numpy as np
import pandas as pd

EP = Path(__file__).resolve().parents[1]
OLD = EP.parents[1]
V2 = EP.parent / 'v2_full_history_benchmark'
sys.path.insert(0, str(V2 / 'src'))
import core as v2

OUT = EP / 'outputs'
CACHE = Path.home() / '.cache/a_share/ep32/review_v3'
ORIGIN = pd.Period('2025-06')
END = pd.Period('2026-06')
HALTS = {
    'SH688313': dict(start='2025-06-30', resume='2025-07-11', published='2025-06-28'),
    'SH688720': dict(start='2025-01-24', resume='2025-02-17', published='2025-01-24'),
}
FOCUS = ['801081.SI', '801102.SI', '850818.SI', '851024.SI']


def csv(name, frame):
    p = OUT / (name + '.csv')
    p.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(p, index=False, lineterminator='\n')


def js(name, value):
    v2.write_json(OUT / (name + '.json'), value)


def diagnostic_cap(row, origin_date, bars, evidence=HALTS):
    """A known halt can supply a stale valuation mark, never an executable price."""
    if pd.notna(row.cap):
        return row.cap, 'EXACT_ORIGIN_CLOSE', pd.Timestamp(origin_date)
    proof = evidence.get(row.instrument)
    if proof is None or pd.isna(row.total_shares) or row.total_shares <= 0:
        return np.nan, 'UNKNOWN_NO_APPROVED_VALUATION_EVIDENCE', pd.NaT
    date = pd.Timestamp(origin_date)
    if not (pd.Timestamp(proof['published']) < date and pd.Timestamp(proof['start']) <= date < pd.Timestamp(proof['resume'])):
        return np.nan, 'OUTSIDE_DOCUMENTED_HALT', pd.NaT
    valid = bars[bars.date.le(date) & bars.close_conflict.eq(False)]
    valid = valid[pd.to_numeric(valid.close).gt(0)].sort_values('date')
    if valid.empty:
        return np.nan, 'NO_PRIOR_VALID_MARK', pd.NaT
    last = valid.iloc[-1]
    return float(last.close) * row.total_shares, 'DOCUMENTED_HALT_LAST_TRADE_MARK_ONLY', last.date


def performance(panel, members, month, horizon=12, matrices=None):
    """Frozen members, exact market-next-day entry, no backfill of any price."""
    months = pd.period_range(month + 1, month + horizon, freq='M')
    if matrices is None:
        px = panel.pivot(index='security_id', columns='month', values='qfq_close')
        chain = panel.pivot(index='security_id', columns='month', values='close_chain')
    else:
        px, chain = matrices
    ids = members.security_id.tolist()
    terminal = px.reindex(index=ids, columns=months).to_numpy(float)
    links = chain.reindex(index=ids, columns=months).to_numpy()
    entry = members.entry_open.to_numpy(float)
    ec = members.entry_chain.to_numpy()
    valid = (links == ec[:, None]) & np.isfinite(entry[:, None]) & (entry[:, None] > 0)
    return np.where(valid, terminal / entry[:, None] - 1, np.nan)


def benchmark_paths(panel):
    dates = panel.groupby('month').agg(date=('date', 'first'), entry_date=('entry_date', 'first'))
    result = {}
    for name, code in [('CSI300', '000300.SH'), ('CSI_ALL', '000985.CSI')]:
        f = pd.read_parquet(v2.SOURCES / (code + '.parquet')).set_index('date')
        entry_date = dates.loc[ORIGIN, 'entry_date']
        endpoints = dates.date.reindex(pd.period_range(ORIGIN + 1, END, freq='M'))
        values = f.close.reindex(endpoints).to_numpy(float) / float(f.loc[entry_date, 'open']) - 1
        result[name] = dict(values=values, entry_date=entry_date, end_date=endpoints.iloc[-1])
    return result


def path_metrics(values, benchmark):
    if not np.isfinite(values).all() or not np.isfinite(benchmark).all():
        return None, None
    joint = (values > benchmark[None, :]).all(axis=0)
    return v2.v1.longest_true(joint), v2.prefix_length(joint)


def run():
    CACHE.mkdir(parents=True, exist_ok=True)
    # Preserve predecessor identity before reading or generating new evidence.
    baseline = {}
    for name, root in [('V1', OLD), ('V2', V2)]:
        m = json.loads((root / 'outputs/manifest.json').read_text())
        assert all(v2.v1.sha(root / r['path']) == r['sha256'] for r in m['files'])
        baseline[name] = dict(manifest_sha256=v2.v1.sha(root / 'outputs/manifest.json'), files=m['files'])
    js('audits/predecessors', baseline)
    js('audits/run_start', dict(status='working', started_at=datetime.now(timezone.utc).isoformat(),
        plan_sha256=v2.v1.sha(EP / 'research_plan.md'), code_sha256=v2.v1.sha(Path(__file__)),
        window='2025-07-01 open to 2026-06-30 close', exploratory_review=True))
    source = json.loads((V2 / 'outputs/audits/inputs.json').read_text())
    assert v2.v1.sha(v2.CACHE / 'panel.parquet') == source['panel_sha256']
    panel = pd.read_parquet(v2.CACHE / 'panel.parquet')
    matrices = (panel.pivot(index='security_id', columns='month', values='qfq_close'),
                panel.pivot(index='security_id', columns='month', values='close_chain'))
    joined = pd.read_parquet(v2.CACHE / 'assignments.parquet')
    origins = pd.read_csv(V2 / 'outputs/details/origin_states.csv.gz')
    outcomes = pd.read_csv(V2 / 'outputs/details/top3_outcomes.csv.gz')
    runs = pd.read_csv(V2 / 'outputs/metrics/leading_runs.csv')
    release = v2.v1.Release('pit_v5')
    inventory = release.read('inputs/normalized/securities.parquet')
    raw = {}
    valuation_rows = []
    for instrument in HALTS:
        sid = inventory[inventory.instrument.eq(instrument)].security_id.iloc[0]
        raw[instrument] = release.read(f'normalized/prices_qfq/{sid}.parquet')
    # Exact origin caps remain untouched. Only a separate diagnostic mark changes.
    patches = {}
    for month in [pd.Period('2025-01'), ORIGIN]:
        p = panel[panel.month.eq(month) & panel.instrument.isin(HALTS)].copy()
        for row in p.itertuples():
            cap, status, date = diagnostic_cap(row, row.date, raw[row.instrument])
            patches[(row.instrument, month)] = (cap, status, date)
            valuation_rows.append(dict(instrument=row.instrument, month=str(month), origin_date=str(row.date.date()),
                strict_raw_close=row.raw_close, strict_cap=row.cap, diagnostic_cap=cap,
                diagnostic_status=status, valuation_date=str(date.date()) if pd.notna(date) else None,
                share_count=row.total_shares, entry_open_unchanged=row.entry_open,
                entry_price_imputed=False, mark_used_only_for_rank=True))
    csv('audits/valuation_diagnostics', pd.DataFrame(valuation_rows))
    benchmarks = benchmark_paths(panel)
    sector_rows, stock_rows, missing_rows, path_rows = [], [], [], []
    for (level, code), g in joined[joined.month.eq(ORIGIN)].groupby(['level', 'industry_code'], sort=True):
        if len(g) < 5:
            continue
        g = g.copy()
        g['diagnostic_cap'] = g.cap
        for idx, r in g[g.cap.isna()].iterrows():
            patch = patches.get((r.instrument, ORIGIN))
            if patch:
                g.loc[idx, 'diagnostic_cap'] = patch[0]
            missing_rows.append(dict(level=level, industry_code=code, industry_name=r.industry_name,
                instrument=r.instrument, name=r['name'], raw_close=r.raw_close, total_shares=r.total_shares,
                reason='NO_EXACT_ORIGIN_CLOSE' if pd.isna(r.raw_close) else 'NO_EFFECTIVE_SHARES',
                reviewed_halt=r.instrument in HALTS, diagnostic_cap=patch[0] if patch else None))
        strict_rank = g.cap.notna().all() and g.unresolved.eq(0).all()
        diagnostic_rank = g.diagnostic_cap.notna().all() and g.unresolved.eq(0).all()
        ordered = g.sort_values(['diagnostic_cap', 'security_id'], ascending=[False, True])
        candidates = ordered.head(3)
        # Missing non-reviewed caps do not become a certified top three.
        ids = g.security_id.tolist()
        candidate_indices = [ids.index(s) for s in candidates.security_id]
        returns = performance(panel, g, ORIGIN, matrices=matrices)
        top = returns[candidate_indices]
        count = np.isfinite(returns[:, -1]).sum()
        coverage = count / (len(g) + int(g.unresolved.max()))
        industry = np.nanmean(returns[:, -1]) if count and coverage >= .8 else np.nan
        for benchmark, bm in benchmarks.items():
            target = bm['values'][-1]
            known_top = np.isfinite(top[:, -1]).all()
            joint, prefix = path_metrics(top, bm['values'])
            sector_rows.append(dict(level=level, industry_code=code, industry_name=g.industry_name.iloc[0],
                origin=str(ORIGIN), entry_date=str(bm['entry_date'].date()), end_date=str(bm['end_date'].date()),
                benchmark=benchmark, members=len(g), known_return_members=int(count), return_coverage=coverage,
                missing_cap_members=int(g.cap.isna().sum()), unresolved=int(g.unresolved.max()),
                sector_observable=bool(coverage >= .8), sector_return=industry,
                benchmark_return=target, sector_excess=industry - target,
                strict_rank_complete=bool(strict_rank), diagnostic_rank_complete=bool(diagnostic_rank),
                ranking_status='EXACT_ORIGIN_INPUT_COMPLETE' if strict_rank else
                    'DOCUMENTED_HALT_VALUATION_DIAGNOSTIC_ONLY' if diagnostic_rank else 'UNVERIFIED_MISSING_CAP',
                observed_top3=';'.join(candidates.instrument), current_names=';'.join(candidates['name']),
                candidate_mean_return=top[:, -1].mean() if known_top else None,
                candidate_mean_excess=top[:, -1].mean() - target if known_top else None,
                candidate_worst_excess=top[:, -1].min() - target if known_top else None,
                candidate_all_beat=bool((top[:, -1] > target).all()) if known_top else None,
                candidate_joint_excess_run=joint, candidate_joint_from_first=prefix))
            if code in FOCUS:
                for rank, (j, r) in enumerate(zip(candidate_indices, candidates.itertuples()), start=1):
                    stock_rows.append(dict(level=level, industry_code=code, industry_name=r.industry_name,
                        benchmark=benchmark, instrument=r.instrument, current_name=r.name, rank=rank,
                        return_value=top[rank - 1, -1], benchmark_return=target,
                        excess=top[rank - 1, -1] - target,
                        rank_complete_strict=bool(strict_rank), rank_complete_diagnostic=bool(diagnostic_rank)))
                    for h in range(12):
                        path_rows.append(dict(industry_code=code, benchmark=benchmark, instrument=r.instrument,
                            rank=rank, month=str(ORIGIN + h + 1), return_value=top[rank - 1, h],
                            benchmark_return=bm['values'][h], excess=top[rank - 1, h] - bm['values'][h]))
    sectors = pd.DataFrame(sector_rows)
    csv('fixed_window/all_industries', sectors)
    csv('fixed_window/focus_top3_stocks', pd.DataFrame(stock_rows))
    csv('fixed_window/focus_monthly_paths', pd.DataFrame(path_rows))
    csv('fixed_window/missing_cap_members', pd.DataFrame(missing_rows))
    # Illustrative optical names are not relabelled as a historical industry top three.
    examples = panel[panel.month.eq(ORIGIN) & panel.instrument.isin(['SZ300308', 'SZ300502', 'SZ300394'])].sort_values('instrument')
    example_returns = performance(panel, examples, ORIGIN, matrices=matrices)
    example_rows = []
    for bm, values in benchmarks.items():
        for i, r in enumerate(examples.itertuples()):
            example_rows.append(dict(instrument=r.instrument, current_name=r.name, benchmark=bm,
                return_value=example_returns[i, -1], benchmark_return=values['values'][-1],
                excess=example_returns[i, -1] - values['values'][-1],
                is_industry_top3=False, selection='POST_HOC_ILLUSTRATIVE_NAMES_NOT_A_UNIVERSE'))
    csv('fixed_window/optical_illustrative_stocks', pd.DataFrame(example_rows))
    # Full funnel trace, preserving each independent exclusion reason.
    gates = []
    focus_origins = origins[origins.industry_code.isin(FOCUS) & origins.month.ge('2025-01') & origins.month.le('2026-06') & origins.benchmark.isin(benchmarks)]
    result_lookup = outcomes.set_index(['era', 'level', 'industry_code', 'month', 'benchmark', 'horizon'])
    for r in focus_origins.itertuples():
        key = (r.era, r.level, r.industry_code, r.month, r.benchmark, 12)
        o = result_lookup.loc[key] if key in result_lookup.index else None
        segments = runs[runs.era.eq(r.era) & runs.level.eq(r.level) & runs.industry_code.eq(r.industry_code) &
                        runs.benchmark.eq(r.benchmark) & runs.start.eq(r.month)]
        reasons = []
        if r.leader != 1:
            reasons.append('NOT_TOP_QUARTILE_EXCESS_LEADER')
        if not r.entry_event:
            reasons.append('NOT_A_NEW_ENTRY_EVENT')
        if not r.rank_complete:
            reasons.append('INDUSTRY_DROPPED_FOR_MEMBER_CAP_GAP')
        if o is not None:
            if not o.mature:
                reasons.append('FORWARD_HORIZON_CENSORED')
            elif not o.complete:
                reasons.append('TOP3_OR_BENCHMARK_ENDPOINT_UNKNOWN')
            elif not o.all_beat:
                reasons.append('NOT_ALL_THREE_BEAT_BENCHMARK')
        if not segments.empty:
            s = segments.iloc[0]
            if s.right_censored:
                reasons.append('LEADING_RUN_STILL_OPEN')
            if s.months > 18:
                reasons.append('LEADING_RUN_LONGER_THAN_18')
            if s.months < 12:
                reasons.append('RANK_BASED_RUN_SHORTER_THAN_12')
        gates.append(dict(era=r.era, level=r.level, industry_code=r.industry_code, industry_name=r.industry_name,
            month=r.month, benchmark=r.benchmark, members=r.members, rankable=r.rankable,
            rank_complete=r.rank_complete, prior_12m_excess=r.trailing_excess,
            rank_percentile=r.rank_percentile, leader=r.leader, entry_event=r.entry_event,
            scored_in_V2=o is not None, mature=o.mature if o is not None else None,
            original_portfolio_excess=o.portfolio_excess if o is not None else None,
            original_all_beat=o.all_beat if o is not None else None, exclusions=';'.join(reasons)))
    csv('audits/focus_filter_trace', pd.DataFrame(gates))
    global_coverage = origins.groupby(['era', 'level', 'benchmark']).agg(
        industry_months=('month', 'size'), entry_events=('entry_event', 'sum'),
        complete_rank=('rank_complete', 'sum')).reset_index()
    lost = origins[origins.entry_event & ~origins.rank_complete].groupby(['era', 'level', 'benchmark']).size()
    global_coverage['entry_events_blocked_by_cap'] = [int(lost.get((r.era, r.level, r.benchmark), 0)) for r in global_coverage.itertuples()]
    csv('audits/global_rank_attrition', global_coverage)
    tail = runs[runs.end.eq(str(panel.month.max())) & runs.right_censored].copy()
    tail['observed_duration_is_lower_bound'] = True
    tail['excluded_from_completed_12_18'] = True
    csv('audits/all_open_leading_runs', tail)
    # Diagnose the two historical rank blocks without changing the old results.
    ranks = []
    for code, month in [('801081.SI', pd.Period('2025-01')), ('851024.SI', ORIGIN)]:
        g = joined[joined.industry_code.eq(code) & joined.month.eq(month)].copy()
        g['diagnostic_cap'] = g.cap
        for idx, r in g[g.cap.isna()].iterrows():
            val = patches.get((r.instrument, month))
            if val:
                g.loc[idx, 'diagnostic_cap'] = val[0]
        t = g.sort_values(['diagnostic_cap', 'security_id'], ascending=[False, True]).head(3)
        ret = performance(panel, t, month, matrices=matrices)
        # Cross-checking a recovered ranking is independent of rerouting the V2 sample.
        for bm, provider in [('CSI300', '000300.SH'), ('CSI_ALL', '000985.CSI')]:
            f = pd.read_parquet(v2.SOURCES / (provider + '.parquet')).set_index('date')
            dates = panel.groupby('month').agg(date=('date', 'first'), entry_date=('entry_date', 'first'))
            bmret = float(f.loc[dates.loc[month + 12, 'date'], 'close'] / f.loc[dates.loc[month, 'entry_date'], 'open'] - 1)
            ranks.append(dict(industry_code=code, industry_name=g.industry_name.iloc[0], month=str(month), benchmark=bm,
                strict_rank_complete=bool(g.cap.notna().all()), diagnostic_rank_complete=bool(g.diagnostic_cap.notna().all()),
                diagnostic_top3=';'.join(t.instrument), current_names=';'.join(t['name']),
                diagnostic_portfolio_excess=float(ret[:, -1].mean() - bmret),
                diagnostic_worst_excess=float(ret[:, -1].min() - bmret),
                not_added_to_V2_statistics=True))
    csv('audits/recovered_rank_examples', pd.DataFrame(ranks))
    js('audits/input_identity', dict(V2_panel_sha256=source['panel_sha256'],
        assignment_sha256=v2.v1.sha(v2.CACHE / 'assignments.parquet'),
        consumed_raw_files=release.reads, price_release=str(release.root),
        no_parent_writes=True, no_trade_price_imputation=True, strict_PIT='BLOCKED_DATA'))
    from report_review import build
    build(sectors, pd.DataFrame(stock_rows), pd.DataFrame(example_rows), pd.DataFrame(gates), tail, pd.DataFrame(ranks))
    print('Review complete:', len(sectors), 'industry/benchmark rows; validation pending')


if __name__ == '__main__':
    run()

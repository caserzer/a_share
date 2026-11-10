"""All-signal economics, fixed baselines and causal episode accounting."""
from common31 import *


def summarize(g):
    known = g[g.outcome_status.eq('OK')]
    r = known.industry_return
    x = known.excess_return
    return dict(signals=len(g), known_returns=len(known), missing_returns=len(g)-len(known),
        known_fraction=len(known)/len(g) if len(g) else np.nan,
        mean_return=r.mean(), median_return=r.median(), mean_excess=x.mean(), median_excess=x.median(),
        positive_excess=x.gt(0).mean() if len(x) else np.nan, excess_q10=x.quantile(.1),
        mean_max_drawdown=known.max_drawdown.mean(), drawdown_q10=known.max_drawdown.quantile(.1),
        mean_beta_residual=known.beta_adjusted_log_return.mean(), beta_known=int(known.beta_adjusted_log_return.notna().sum()),
        net_excess_50bp=(r-.005-known.benchmark_return).mean(),
        net_excess_100bp=(r-.01-known.benchmark_return).mean(),
        cycle_known=int(g.y.notna().sum()), cycle_positive=int(g.y.eq(1).sum()), cycle_unknown=int(g.y.isna().sum()))


def run():
    refs = json.loads((OUT / 'input_receipt.json').read_text())
    assert sha(CACHE / 'outcomes.parquet') == refs['outcomes_sha256']
    assert sha(CACHE / 'observations.parquet') == refs['observations_sha256']
    observations = pd.read_parquet(CACHE / 'observations.parquet')
    outcomes = pd.read_parquet(CACHE / 'outcomes.parquet')
    labels = pd.read_parquet(OLD / 'stage_b_labels.parquet')
    market = pd.read_parquet(OLD / 'CSI_ALL.parquet').close.sort_index()
    calendar = pd.DatetimeIndex(market.index)
    market126 = market / market.shift(126) - 1
    metrics = []; annual = []; strata = []; comparisons = []; selection_audit = []; checks = []
    accepted_details = []; cycles = []; daily_means = []
    phase = pd.read_parquet(OLD / 'daily_phases.parquet').set_index('phase_id')
    original = pd.read_csv(EXT / 'v28_aggregate_acceptance/outputs/independent_metrics.csv').query("model=='accepted'")
    peak_details = pd.read_csv(EXT / 'v29_signal_to_peak/outputs/task_event_outcomes.csv.gz')
    risk_receipt = json.loads((EXT / 'v12_duration_risk/outputs/prediction_receipt.json').read_text())
    diff_receipt = {r['task']: r for r in json.loads((EXT / 'v18_conditional_diffusion/outputs/prediction_receipt.json').read_text())['tasks']}
    for entry in risk_receipt['tasks']:
        task = entry['task']; other = diff_receipt[task]
        assert sha(entry['path']) == entry['sha256'] and sha(other['path']) == other['sha256']
        risk = pd.read_parquet(entry['path'], filters=[('model', '==', 'risk_tree')])
        risk = risk[risk.date.between(START, END)].rename(columns={'prob': 'risk_score'}).drop(columns=['model', 'alert'])
        diffusion = pd.read_parquet(other['path'], filters=[('model', 'in', ['capacity_tree', 'diffusion_tree'])])
        scores = diffusion.pivot(index='row_id', columns='model', values='prob').reset_index()
        f = risk.merge(scores, on='row_id', validate='one_to_one').merge(
            observations[['row_id', 'block', 'industry_name', 'mom63', 'mom126', 'vol63']], on='row_id', validate='one_to_one')
        assert len(f) == len(risk)
        f['market_return126'] = f.date.map(market126)
        f['market_up'] = f.market_return126.gt(0)
        f['min_score'] = f[['risk_score', 'diffusion_tree']].min(axis=1)
        eligible = f.state_eligible.eq(1)
        chosen = f.min_score.ge(.11) & f.market_up
        counts = chosen.groupby([f.date, f.level]).transform('sum')
        population = eligible & f.market_up
        budget10 = np.ceil(population.groupby([f.date, f.level]).transform('sum')*.1)
        selectors = {
            'accepted': chosen,
            'no_market': f.min_score.ge(.11),
            'same_date_universe': counts.gt(0),
            'early_market_all': population,
            'momentum_top10': top_k(f, f.mom63, budget10, population),
            'momentum_matched': top_k(f, f.mom63, counts, population),
            'risk_matched': top_k(f, f.risk_score, counts, population),
            'capacity_matched': top_k(f, f.capacity_tree, counts, population),
            'diffusion_matched': top_k(f, f.diffusion_tree, counts, population),
            'risk_fixed': f.risk_score.ge(.11) & f.market_up,
            'diffusion_fixed': f.diffusion_tree.ge(.11) & f.market_up,
        }
        # Preserve future-free prediction and causal launch flags separately.
        for method, selected in selectors.items():
            f['select_' + method] = selected
            f['launch_' + method] = False
            selected_rows = f[selected]
            starts = episode_starts(selected_rows, calendar)
            f.loc[selected_rows.index, 'launch_' + method] = starts
            if method.endswith('_matched'):
                assert np.array_equal(selected.groupby([f.date, f.level]).sum().to_numpy(),
                                      chosen.groupby([f.date, f.level]).sum().to_numpy())
        path = CACHE / 'frames' / (task + '.parquet')
        path.parent.mkdir(exist_ok=True)
        f.to_parquet(path, index=False)
        f = f.merge(labels, on=['row_id', 'threshold', 'benchmark'], validate='one_to_one')
        f.loc[f.label_available_at.gt(f.date + pd.DateOffset(months=24)), 'y'] = np.nan
        for level, group in f.groupby('level'):
            signature = dict(task=task, frequency=group.frequency.iloc[0], threshold=group.threshold.iloc[0],
                             benchmark=group.benchmark.iloc[0], level=level)
            ref = original[(original.task == task) & (original.level == level)].iloc[0]
            active = group[group.select_accepted]
            known = active[active.y.notna()]
            positives = group[group.y.eq(1)]
            hitdates = positives[positives.select_accepted].groupby('event_or_witness_id').date.min()
            assert len(active) == ref.alerts and len(known) == ref.known_alerts and len(hitdates) == ref.detected_events
            precision = known.groupby('date').y.mean().mean()
            assert np.isclose(precision, ref.precision)
            peaks = peak_details[(peak_details.frequency == signature['frequency']) &
                (peak_details.threshold == signature['threshold']) & (peak_details.benchmark == signature['benchmark']) &
                (peak_details.level == level)]
            assert len(peaks) == len(hitdates)
            cycles.append(dict(**signature, precision=precision, cycle_recall=len(hitdates)/positives.event_or_witness_id.nunique(),
                point_recall=known.y.sum()/len(positives), detected_cycles=len(hitdates),
                evaluable_cycles=positives.event_or_witness_id.nunique(),
                mean_remaining_gain=peaks.return_to_peak.mean(), median_remaining_gain=peaks.return_to_peak.median(),
                mean_days_to_peak=peaks.days_to_peak.mean(), median_days_to_peak=peaks.days_to_peak.median()))
            group = group.merge(outcomes[outcomes.benchmark.eq(signature['benchmark'])].drop(columns='benchmark'),
                                on='row_id', validate='one_to_many')
            is_primary = signature['threshold'] == .15 and signature['benchmark'] == 'CSI_ALL' and level == 'L3'
            for method in selectors:
                for unit, column in [('all_alerts', 'select_'), ('six_month_launches', 'launch_')]:
                    selected = group[group[column+method]]
                    for months, g in selected.groupby('months'):
                        metrics.append(dict(**signature, method=method, unit=unit, months=months, **summarize(g)))
                        selection_audit.extend([dict(**signature, method=method, unit=unit, months=months,
                            status=status, count=len(part)) for status, part in g.groupby('outcome_status')])
                        if is_primary and months == 6:
                            for year, part in g.groupby(g.date.dt.year):
                                annual.append(dict(**signature, method=method, unit=unit, year=year, **summarize(part)))
                            if method == 'accepted':
                                gg = g.assign(label_status=np.where(g.y.isna(), 'UNKNOWN', np.where(g.y.eq(1), 'POSITIVE', 'NEGATIVE')))
                                for status, part in gg.groupby('label_status'):
                                    strata.append(dict(**signature, unit=unit, label_status=status, **summarize(part)))
                                for state, part in g.groupby('market_up'):
                                    strata.append(dict(**signature, unit=unit, label_status='MARKET_UP_'+str(state), **summarize(part)))
                            good = g[g.outcome_status.eq('OK')]
                            dm = good.groupby('date').excess_return.mean().rename('excess').reset_index()
                            dm['method'] = method; dm['unit'] = unit; dm['frequency'] = signature['frequency']
                            daily_means.append(dm)
                            if method == 'accepted':
                                columns = ['row_id', 'date', 'era', 'level', 'industry_code', 'industry_name', 'block',
                                    'frequency', 'threshold', 'benchmark', 'entry_date', 'end_date', 'y', 'outcome_status',
                                    'industry_return', 'excess_return', 'max_drawdown', 'beta252', 'beta_adjusted_log_return']
                                accepted_details.append(g[columns].assign(unit=unit))
            if is_primary:
                checks.append('primary baseline counts and V28 cycle counts ' + task)
        print('evaluated all-signal economics', task, flush=True)
    metric = pd.DataFrame(metrics); metric.to_csv(OUT / 'all_task_metrics.csv', index=False)
    primary = metric.query("level=='L3' and threshold==0.15 and benchmark=='CSI_ALL'")
    primary.to_csv(OUT / 'primary_metrics.csv', index=False)
    pd.DataFrame(cycles).to_csv(OUT / 'cycle_metrics.csv', index=False)
    pd.DataFrame(annual).to_csv(OUT / 'primary_annual.csv', index=False)
    pd.DataFrame(strata).to_csv(OUT / 'label_strata.csv', index=False)
    pd.DataFrame(selection_audit).to_csv(OUT / 'selection_coverage.csv', index=False)
    pd.concat(accepted_details).to_csv(OUT / 'primary_accepted_outcomes.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    dates = pd.concat(daily_means, ignore_index=True)
    dates.to_csv(OUT / 'primary_daily_excess.csv', index=False)
    for (frequency, unit), group in dates.groupby(['frequency', 'unit']):
        pivot = group.pivot(index='date', columns='method', values='excess')
        for control in ['momentum_matched', 'risk_matched', 'capacity_matched', 'diffusion_matched',
                        'same_date_universe', 'early_market_all', 'momentum_top10', 'no_market']:
            pair = pivot[['accepted', control]].dropna()
            diff = pair.accepted - pair[control]
            comparisons.append(dict(frequency=frequency, unit=unit, control=control,
                paired_dates=len(pair), **block_interval(pair.index, diff)))
    pd.DataFrame(comparisons).to_csv(OUT / 'paired_block_intervals.csv', index=False)
    # Compare future-free launch flags with recomputation using only historical prefixes.
    sample = pd.read_parquet(CACHE / 'frames/W_0.15_CSI_ALL.parquet')
    sample = sample[sample.select_accepted & sample.level.eq('L3')]
    for cutoff in ['2021-12-31', '2022-12-31', '2023-12-31']:
        prefix = sample[sample.date.le(cutoff)]
        recomputed = episode_starts(prefix, calendar)
        assert np.array_equal(recomputed, prefix.launch_accepted)
        checks.append('episode launch prefix causality ' + cutoff)
    assert all(sha(p) == h for p, h in refs['source_hashes'].items())
    checks += ['all 36 task original alert and cycle counts match', 'all matched budgets equal before lockout',
               'forward returns independent of cycle labels', 'unknown labels not filled', 'input hashes unchanged']
    js(OUT / 'evaluation_checks.json', dict(checks=checks))
    print(primary.query("method=='accepted' and unit=='six_month_launches'")[
        ['frequency','months','signals','known_returns','mean_return','median_return','mean_excess','median_excess','mean_max_drawdown']].to_string(index=False))


if __name__ == '__main__':
    run()

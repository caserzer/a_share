"""EP33 transparent historical-proxy experiments. No fitting or network access."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

EP = Path(__file__).resolve().parents[1]
SOURCE = Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5')
KEY = ['era', 'level', 'industry_code', 'block']
HORIZONS = (63, 126, 252)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def features(g, market):
    g = g.sort_values('date').copy()
    assert g.day_i.diff().dropna().eq(1).all()
    x = np.log(g.nav.to_numpy() / market.reindex(g.date).to_numpy())
    x = pd.Series(x, index=g.index)
    g['velocity'] = x - x.shift(21)
    g['acceleration'] = g.velocity - g.velocity.shift(21)
    g['persistence'] = g.acceleration.gt(0).astype(float).rolling(10, min_periods=10).mean()
    g['breadth_change'] = g.breadth21 - g.breadth21.shift(21)
    g['breadth_acceleration'] = g.breadth_change - g.breadth_change.shift(21)
    g['vol63'] = np.log(g.nav).diff().rolling(63).std()
    g['prior63'] = x - x.shift(63)
    return g


def outcomes(g, market):
    g = g.copy()
    p = g.nav.to_numpy()
    m = market.reindex(g.date).to_numpy()
    for h in HORIZONS:
        ret = np.full(len(g), np.nan)
        excess = ret.copy()
        adverse = ret.copy()
        end = np.full(len(g), np.datetime64('NaT'), dtype='datetime64[ns]')
        for i in range(len(g) - h - 1):
            entry, stop = i + 1, i + 1 + h
            ret[i] = p[stop] / p[entry] - 1
            excess[i] = ret[i] - (m[stop] / m[entry] - 1)
            adverse[i] = np.min(p[entry:stop+1]) / p[entry] - 1
            end[i] = g.date.iloc[stop].to_datetime64()
        g[f'return{h}'], g[f'excess{h}'], g[f'adverse{h}'] = ret, excess, adverse
        g[f'end{h}'] = end
    return g


def build_panel():
    daily_path = SOURCE / 'daily_industries.parquet'
    d = pd.read_parquet(daily_path)
    audit_path = EP.parent / '32_industry_rotation_cycle_observation/extensions/v5_rdagent_onset_forecast/outputs/daily_input_audit.json'
    original = json.loads(audit_path.read_text())
    assert digest(daily_path) == original['daily_sha256'], 'EP32 source hash mismatch'
    market = pd.read_parquet(SOURCE / 'CSI_ALL.parquet').close.sort_index()
    dates = pd.Series(market.index, index=market.index)
    weeks = dates.groupby(dates.index.to_period('W-FRI')).max()
    weeks = weeks[[p.end_time.normalize() <= market.index.max() for p in weeks.index]]
    chunks = []
    for _, g in d[d.level.eq('L3')].groupby(KEY, sort=True):
        f = features(g, market)
        f = outcomes(f, market)
        chunks.append(f[f.date.isin(weeks) & f.date.ge('2021-01-01')])
    panel = pd.concat(chunks, ignore_index=True)
    assert not panel.duplicated(['era', 'industry_code', 'date']).any()
    assert panel.membership_asof.le(panel.date).all()
    return panel, market, [daily_path, SOURCE / 'CSI_ALL.parquet', audit_path]


def select(panel, round_id='r01'):
    chosen, coverage = [], []
    for date, all_rows in panel.groupby('date', sort=True):
        valid = all_rows.acceleration.notna() & all_rows.coverage.ge(.8) & all_rows.members.ge(5)
        base = all_rows[valid]
        coverage.append({'date': date, 'observed_rows': len(all_rows), 'eligible': len(base),
                         'missing_or_ineligible': int((~valid).sum()),
                         'known126': int(base.excess126.notna().sum())})
        pools = {'all': base,
                 'decelerating_decline': base[base.velocity.lt(0) & base.acceleration.gt(0)],
                 'accelerating_improvement': base[base.velocity.ge(0) & base.acceleration.gt(0)]}
        for name, pool in pools.items():
            k = min(10, len(pool))
            for score in ['velocity', 'acceleration']:
                s = pool.sort_values([score, 'industry_code'], ascending=[False, True]).head(k).copy()
                s['pool'], s['strategy'], s['rank'], s['pool_n'] = name, score, np.arange(1, k+1), len(pool)
                chosen.append(s)
    return pd.concat(chosen, ignore_index=True), pd.DataFrame(coverage)


def block_interval(monthly, seed=33):
    a = np.asarray(monthly, float)
    a = a[np.isfinite(a)]
    if len(a) < 12:
        return [None, None]
    rng = np.random.default_rng(seed)
    width = 6
    starts = rng.integers(0, len(a), size=(2000, int(np.ceil(len(a)/width))))
    ix = (starts[..., None] + np.arange(width)) % len(a)
    samples = a[ix.reshape(2000, -1)[:, :len(a)]].mean(axis=1)
    return list(np.quantile(samples, [.025, .975]))


def summarize(selected, out):
    daily, summaries = [], []
    for (pool, strategy, date), g in selected.groupby(['pool', 'strategy', 'date']):
        row = dict(pool=pool, strategy=strategy, date=date, selected=len(g))
        for h in HORIZONS:
            known = g[f'excess{h}'].notna()
            row[f'known{h}'] = int(known.sum())
            for metric in ['return', 'excess', 'adverse']:
                row[f'{metric}{h}'] = g.loc[known, f'{metric}{h}'].mean()
            row[f'complete{h}'] = bool(known.all())
        daily.append(row)
    daily = pd.DataFrame(daily)
    daily.to_csv(out / 'date_metrics.csv', index=False)
    for (pool, strategy), g in daily.groupby(['pool', 'strategy']):
        for h in HORIZONS:
            summaries.append(dict(pool=pool, strategy=strategy, horizon=h,
                                  dates=len(g), selected=int(g.selected.sum()),
                                  known=int(g[f'known{h}'].sum()),
                                  complete_dates=int(g[f'complete{h}'].sum()),
                                  mean_excess_known_dates=g[f'excess{h}'].mean(),
                                  mean_return_known_dates=g[f'return{h}'].mean(),
                                  mean_adverse_known_dates=g[f'adverse{h}'].mean()))
    pd.DataFrame(summaries).to_csv(out / 'summary.csv', index=False)
    paired, annual = [], []
    for pool, g in daily.groupby('pool'):
        for h in HORIZONS:
            a = g[g.strategy.eq('acceleration')].set_index('date')
            v = g[g.strategy.eq('velocity')].set_index('date')
            common = a.index.intersection(v.index)
            mask = a.loc[common, f'complete{h}'] & v.loc[common, f'complete{h}']
            ix = common[mask]
            delta = a.loc[ix, f'excess{h}'] - v.loc[ix, f'excess{h}']
            monthly = delta.groupby(delta.index.to_period('M')).mean()
            ci = block_interval(monthly)
            paired.append(dict(pool=pool, horizon=h, common_complete_dates=len(ix),
                               months=len(monthly), mean_delta_month_equal=monthly.mean(),
                               ci_low=ci[0], ci_high=ci[1],
                               acceleration_excess=a.loc[ix, f'excess{h}'].mean(),
                               velocity_excess=v.loc[ix, f'excess{h}'].mean()))
            for year, y in delta.groupby(delta.index.year):
                annual.append(dict(pool=pool, horizon=h, year=year, dates=len(y), delta=y.mean()))
    pd.DataFrame(paired).to_csv(out / 'paired.csv', index=False)
    pd.DataFrame(annual).to_csv(out / 'annual.csv', index=False)
    return paired


def verify(panel, market):
    d = pd.read_parquet(SOURCE / 'daily_industries.parquet')
    tested = 0
    for _, g in d[d.level.eq('L3')].groupby(KEY):
        if len(g) < 200:
            continue
        g = g.sort_values('date')
        cut = len(g)//2
        full = features(g, market)
        truncated = features(g.iloc[:cut], market.loc[:g.date.iloc[cut-1]])
        cols = ['velocity', 'acceleration', 'persistence', 'breadth_change', 'breadth_acceleration']
        pd.testing.assert_frame_equal(full.iloc[:cut][cols], truncated[cols])
        changed = g.copy()
        changed.loc[changed.index[cut:], 'nav'] *= 100
        pd.testing.assert_frame_equal(full.iloc[:cut][cols], features(changed, market).iloc[:cut][cols])
        tested += 1
        if tested == 20:
            break
    assert tested == 20
    known = panel[panel.end126.notna()].head(30)
    for _, r in known.iterrows():
        g = d[(d.era == r.era) & (d.level == r.level) & (d.industry_code == r.industry_code) & (d.block == r.block)].sort_values('date')
        i = np.flatnonzero(g.date.eq(r.date))[0]
        assert g.date.iloc[i+127] == r.end126
        expected = g.nav.iloc[i+127]/g.nav.iloc[i+1]-1 - (market.loc[r.end126]/market.loc[g.date.iloc[i+1]]-1)
        assert np.isclose(expected, r.excess126)
    return {'truncation_and_future_perturbation_groups': tested, 'independent_endpoint_checks': len(known),
            'membership_asof_check': True, 'continuous_block_and_unique_identity_checks': True,
            'limits': 'Derived-feature checks do not certify source PIT or economic significance.'}


def main():
    out = EP / 'outputs/r01'
    out.mkdir(parents=True, exist_ok=True)
    panel, market, sources = build_panel()
    selected, coverage = select(panel)
    # Derived panel stays outside public tables; no raw provider data copied to repository.
    panel.to_parquet('/tmp/ep33_r01_panel.parquet', index=False)
    selected.to_csv(out / 'selected.csv.gz', index=False)
    coverage.to_csv(out / 'coverage.csv', index=False)
    paired = summarize(selected, out)
    checks = verify(panel, market)
    receipt = {'round_id': 'r01', 'quality': 'Historical-proxy', 'data_end': str(market.index.max()),
               'panel_rows': len(panel), 'checks': checks,
               'inputs': {str(p): digest(p) for p in sources + [EP/'rounds/r01_plan.md', Path(__file__)]}}
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False)+'\n')
    print(pd.DataFrame(paired).to_string(index=False))
    print(json.dumps(checks))


if __name__ == '__main__':
    main()

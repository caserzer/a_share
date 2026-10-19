"""R16: combine frozen candidate distributions using matured OOS history only."""
import json
import numpy as np
import pandas as pd
from diagnose_prediction_target import DEST
from run_four_horizons import OUT
from run_direct_probability import weighted_stats

FOLDER = DEST / 'prequential'
METRICS = ['brier', 'multiclass_brier', 'crps', 'accuracy']


def mature_history(predictions, date, window=36):
    history = predictions[(predictions.date < date) &
                          (predictions.label_end < date) & predictions.actual.notna()].copy()
    dates = sorted(history.date.unique())[-window:]
    return history[history.date.isin(dates)]


def choose_weights(history, names, min_months=12):
    """Fixed rule, no fitting on current or not-yet-matured prediction outcomes."""
    base = np.array([float(name == 'B') for name in names])
    if history.date.nunique() < min_months:
        return base, 'B'
    h = history.copy()
    h['accuracy'] = np.where(h.actual != 0, (h.p_up > h.p_down) == (h.actual > 0), np.nan)
    monthly = h.groupby(['date', 'model'])[METRICS].mean()
    scores = monthly.groupby('model').mean().reindex(names)
    losses = scores.copy()
    losses['accuracy'] = 1 - scores.accuracy
    ratios = losses / losses.loc['B'].clip(lower=1e-8)
    if ratios.isna().any().any():
        raise ValueError('Unequal candidate history')
    objective = ratios.mean(axis=1).to_numpy()
    raw = np.exp(-10 * (objective - objective.min()))
    mix = .5 * base + .5 * raw / raw.sum()
    worst = ratios.max(axis=1)
    eligible = worst[worst < .99]
    gate = eligible.idxmin() if len(eligible) else 'B'
    return mix, gate


def calibrate_equal_atoms(history, width, min_months=12):
    """50% identity plus monthly-equal empirical PIT CDF, with exact endpoints."""
    if history.date.nunique() < min_months:
        return np.full(width, 1 / width)
    history = history.dropna(subset=['pit'])
    count = history.groupby('date').pit.transform('size').to_numpy()
    mass = 1 / count / history.date.nunique()
    order = np.argsort(history.pit.to_numpy())
    pits = history.pit.to_numpy()[order]
    cumulative = np.r_[0., mass[order].cumsum()]
    grid = np.arange(width + 1) / width
    cdf = cumulative[np.searchsorted(pits, grid, side='right')]
    cdf[0], cdf[-1] = 0., 1.
    adjusted = .5 * grid + .5 * cdf
    return np.diff(adjusted)


def combine_distributions(distributions, coefficients):
    active = [(a, w, c) for (a, w), c in zip(distributions, coefficients) if c > 0]
    atoms = np.concatenate([a for a, _, _ in active], axis=1)
    weights = np.concatenate([w * c for _, w, c in active], axis=1)
    order = np.argsort(atoms, axis=1, kind='stable')
    atoms = np.take_along_axis(atoms, order, axis=1)
    weights = np.take_along_axis(weights, order, axis=1)
    weights /= weights.sum(axis=1, keepdims=True)
    return atoms, weights


def load_distribution(cache, h, date, name, keys):
    stem = f'{h}_{date.date()}'
    saved_keys = pd.read_parquet(cache / f'{stem}_keys.parquet')
    pd.testing.assert_frame_equal(saved_keys.reset_index(drop=True), keys.reset_index(drop=True))
    with np.load(cache / f'{stem}_{name}.npz') as payload:
        atoms = payload['atoms'].astype(float)
        weights = (payload['weights'].astype(float) if 'weights' in payload
                   else np.full_like(atoms, 1 / atoms.shape[1]))
    weights /= weights.sum(axis=1, keepdims=True)
    return atoms, weights


def run():
    FOLDER.mkdir(exist_ok=True)
    baseline_dir = OUT / 'r15_three_factor_ablation'
    folders = [baseline_dir, DEST / 'round1', DEST / 'market_residual']
    caches = [OUT / 'local_cache/r15_distributions', OUT / 'local_cache/r16_round1_distributions',
              OUT / 'local_cache/r16_market_residual']
    audits = []
    weights_log = []
    for h in [1, 3, 6]:
        inputs = []
        cache_for = {}
        for folder, cache in zip(folders, caches):
            data = pd.read_parquet(folder / f'predictions_{h}m.parquet')
            if folder == baseline_dir:
                data = data[data.model == 'B']
            inputs.append(data)
            cache_for.update({name: cache for name in data.model.unique()})
        predictions = pd.concat(inputs, ignore_index=True)
        names = ['B'] + sorted(set(predictions.model) - {'B'})
        rows = []
        for date, test in inputs[0].groupby('date', sort=True):
            test = test.reset_index(drop=True)
            keys = test[['date', 'instrument']]
            hist = mature_history(predictions, date)
            mix, gate = choose_weights(hist, names)
            distributions = [load_distribution(cache_for[n], h, date, n, keys) for n in names]
            uniform = np.ones(len(names)) / len(names)
            methods = {'uniform_mixture': combine_distributions(distributions, uniform),
                       'prequential_mixture': combine_distributions(distributions, mix),
                       'prequential_gate': distributions[names.index(gate)]}
            market_name = 'market_empirical_residual'
            atoms, _ = distributions[names.index(market_name)]
            calweights = calibrate_equal_atoms(hist[hist.model == market_name], atoms.shape[1])
            methods['market_empirical_pit'] = (atoms, np.tile(calweights, (len(atoms), 1)))
            for name, (atoms, weights) in methods.items():
                r = test[['date', 'instrument', 'label_end', 'target_date', 'actual']].copy()
                r = pd.concat([r, weighted_stats(atoms, weights, r.actual)], axis=1)
                r['months'], r['model'] = h, name
                rows.append(r)
            audits.append(dict(months=h, date=str(date.date()), history_months=hist.date.nunique(),
                               latest_history_label=str(hist.label_end.max()), gate_model=gate,
                               predicted_rows=len(test)))
            for n, w in zip(names, mix):
                weights_log.append(dict(months=h, date=str(date.date()), component=n, weight=w))
            assert hist.empty or hist.label_end.max() < date
            print(h, date.date(), hist.date.nunique(), gate, flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(FOLDER / f'predictions_{h}m.parquet', index=False)
    pd.DataFrame(audits).to_csv(FOLDER / 'fit_audit.csv', index=False)
    pd.DataFrame(weights_log).to_csv(FOLDER / 'mixture_weights.csv', index=False)
    (FOLDER / 'spec.json').write_text(json.dumps(dict(
        history_window_months=36, minimum_history_months=12, mixing_base_weight=.5,
        softmax_temperature_inverse=10, selection_metrics=METRICS,
        gate='all four historical loss ratios below .99; minimize worst ratio; otherwise B',
        calibration='month-equal PIT CDF with 50 percent identity shrinkage',
        future_outcomes='strictly excluded from all weight and calibration decisions',
        evidence='retrospective repeated exploration, not a new independent holdout',
        distributions='exact weighted mixtures; cached atoms are float32 then evaluated in float64'
    ), indent=2) + '\n')


if __name__ == '__main__':
    run()

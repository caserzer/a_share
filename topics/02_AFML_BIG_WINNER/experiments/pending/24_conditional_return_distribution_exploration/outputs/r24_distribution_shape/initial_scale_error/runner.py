"""R24: current-information quantile distributions and past-known risk scaling."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from prepare_panel import EP, OUT
from build_price_volume_features import PANEL, ACTIVITY, PATH, DEST as SOURCE
from run_price_volume_models import CONTROL
from run_market_time_models import select_training, observation_weights
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import weighted_stats

DEST = OUT/'r24_distribution_shape'
CACHE = OUT/'local_cache/r24_quantile_distributions'
ALPHAS = (np.arange(25)+.5)/25
GRID = (np.arange(200)+.5)/200
FITS = {
    'quantile_control': (CONTROL, False),
    'quantile_scaled': (CONTROL, True),
    'quantile_paths': (CONTROL+ACTIVITY+PATH, False),
}
MODELS = {f'{name}_{suffix}': (name, fraction) for name in FITS
          for suffix, fraction in [('mixed', .5), ('unmixed', 1.)]}
REFERENCES = {'r23_class_control': 'activity_means_depth4',
              'r23_class_paths': 'activity_and_paths_depth4'}


def risk_scale(volatility, months):
    """Only decision-date backward-looking vol63; positive numerical floor."""
    v = np.asarray(volatility, dtype=float)
    if not np.isfinite(v).all() or (v < 0).any():
        raise ValueError('Risk scaling requires finite nonnegative historical volatility')
    return np.maximum(v, .001)*np.sqrt(21*months)


def training_target(returns, scale=None):
    y = np.asarray(returns, dtype=float)
    if not np.isfinite(y).all() or (y <= -1).any():
        raise ValueError('Mature simple returns must be finite and greater than -1')
    return y if scale is None else np.log1p(y)/scale


def quantile_atoms(raw, scale=None):
    """Rearrange crossings; interpolate fixed quantile grid with constant tails."""
    q = np.asarray(raw, dtype=float)
    if q.ndim != 2 or q.shape[1] != len(ALPHAS) or not np.isfinite(q).all():
        raise ValueError('Finite raw quantiles with the predefined grid are required')
    atoms = np.stack([np.interp(GRID, ALPHAS, row) for row in np.sort(q, axis=1)])
    if scale is not None:
        s = np.asarray(scale, dtype=float)
        if s.shape != (len(q),) or not np.isfinite(s).all() or (s <= 0).any():
            raise ValueError('One positive finite past-known scale is required per row')
        atoms = np.expm1(atoms*s[:, None])
    else:
        atoms = np.maximum(atoms, -1.)
    if not np.isfinite(atoms).all():
        raise ValueError('Nonfinite reconstructed distribution')
    return atoms, np.full_like(atoms, 1/len(GRID))


def run():
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    panel = pd.read_parquet(PANEL)
    source_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    feature_audit = json.loads((SOURCE/'feature_audit.json').read_text())
    assert source_audit['technical_integrity_passed']
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == feature_audit['feature_sha256']
    spec = dict(fits={k: dict(features=v[0], log_risk_scaled=v[1]) for k, v in FITS.items()},
        models=MODELS, references=REFERENCES, alphas=ALPHAS.tolist(), grid=GRID.tolist(),
        iterations=200, depth=4, learning_rate=.03, l2_leaf_reg=50, random_seed=24,
        monthly_equal_weights=True, min_training_rows=1000, min_training_months=18,
        feature_sha256=feature_audit['feature_sha256'], source_receipts=source_audit['receipts'],
        note_sha256=hashlib.sha256((EP/'notes/r24_distribution_shape.md').read_bytes()).hexdigest(),
        representation='25 evenly spaced midpoint quantiles; sort crossings, interpolate to 200 midpoint atoms, constant endpoint tails; raw simple-return atoms floored at -1',
        scaling='log1p(mature return) / (max(decision vol63,0.001)*sqrt(21*h)); inverse at query historical vol; labels and target dates unchanged',
        precedent='R10 already tested quarterly unweighted quantile trees with older inputs; this is a monthly, month-weighted current-panel comparison, not a new invention',
        evidence='Six predefined candidates, original frozen B and complete stock/date population; no selection or early stopping on future test outcomes',
        documentation='https://catboost.ai/docs/en/concepts/loss-functions-regression#MultiQuantile')
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    audits = []
    for h in [1, 3, 6]:
        source_path = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in source_audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == receipt['sha256']
        source = pd.read_parquet(source_path)
        rows = [source[source.model.eq(old)].assign(model=name) for name, old in REFERENCES.items()]
        base = pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'); base = base[base.model.eq('B')]
        for date, test in panel[panel.date.ge('2021-01-01')].groupby('date', sort=True):
            test = test.reset_index(drop=True)
            train = select_training(panel, h, date, None)
            weights = observation_weights(train, date, True, None)
            active = len(train) >= 1000 and train.date.nunique() >= 18
            template = base[base.date.eq(date)].reset_index(drop=True)
            keys = test[['date', 'instrument']]
            pd.testing.assert_frame_equal(template[['date', 'instrument']], keys)
            keys.to_parquet(CACHE/f'{h}_{date.date()}_keys.parquet', index=False)
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', keys)
            for name, (cols, scaled) in FITS.items():
                raw = None
                if active:
                    train_scale = risk_scale(train.vol63, h) if scaled else None
                    test_scale = risk_scale(test.vol63, h) if scaled else None
                    target = training_target(train[f'y_{h}'], train_scale)
                    model = CatBoostRegressor(loss_function='MultiQuantile:alpha='+','.join(map(str, ALPHAS)),
                        iterations=200, depth=4, learning_rate=.03, l2_leaf_reg=50, random_seed=24,
                        thread_count=4, verbose=False, allow_writing_files=False)
                    model.fit(train[cols].astype(float), target, sample_weight=weights)
                    raw = model.predict(test[cols].astype(float))
                    a, w = quantile_atoms(raw, test_scale)
                    np.savez_compressed(CACHE/f'{h}_{date.date()}_{name}.npz', raw_quantiles=raw,
                        query_scale=np.ones(len(test)) if test_scale is None else test_scale)
                for suffix, fraction in [('mixed', .5), ('unmixed', 1.)]:
                    prediction = template.copy(); prediction['model'] = f'{name}_{suffix}'
                    if active:
                        aa, ww = combine_distributions([(ba, bw), (a, w)], [1-fraction, fraction]) if fraction < 1 else (a, w)
                        stats = weighted_stats(aa, ww, template.actual); prediction[stats.columns] = stats.to_numpy()
                    rows.append(prediction)
                audits.append(dict(months=h, date=str(date.date()), fit=name, training_rows=len(train),
                    training_months=train.date.nunique(), last_training_label=str(train[f'end_{h}'].max()),
                    total_weight=float(weights.sum()), test_rows=len(test), adjusted_rows=len(test) if active else 0,
                    crossing_fraction=float((np.diff(raw, axis=1)<0).any(axis=1).mean()) if raw is not None else np.nan))
            print(h, date.date(), 'finished', flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv', index=False)


if __name__ == '__main__':
    run()

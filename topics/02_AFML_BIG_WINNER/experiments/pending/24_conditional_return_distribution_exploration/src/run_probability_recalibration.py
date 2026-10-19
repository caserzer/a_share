"""R22 recalibration and convex mixing of frozen R21 distributions."""
import hashlib
import json
import numpy as np
import pandas as pd
from prepare_panel import OUT
from run_market_time_models import DEST as SOURCE, CACHE as SOURCE_CACHE
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import classes, weighted_stats
from probability_recalibration import class_probabilities, calibration_history, fit_calibrator, transform, replace_class_mass, fit_mixture, PENALTY

DEST = OUT/'r22_probability_recalibration'
STREAMS = dict(month='market_month_balanced', decay='market_decay24_unmixed')
CALIBRATORS = dict(month_calibration_expanding=('month', None), month_calibration_recent24=('month', 24),
    decay_calibration_expanding=('decay', None), decay_calibration_recent24=('decay', 24))
MIXTURES = ['uniform_frozen_mix', 'learned_frozen_mix']
REFERENCE = dict(month='r21_month_reference', decay='r21_decay_reference')
MIN_MONTHS = 12


def source_distributions(horizon, date, keys):
    base = load_distribution(OUT/'local_cache/r15_distributions', horizon, date, 'B', keys)
    result = dict(B=base); backups = {}; receipts = []
    stored_keys = pd.read_parquet(SOURCE_CACHE/f'{horizon}_{date.date()}_keys.parquet')
    pd.testing.assert_frame_equal(stored_keys, keys)
    for stream, model in STREAMS.items():
        name = 'market_decay24' if stream == 'decay' else model
        path = SOURCE_CACHE/f'{horizon}_{date.date()}_{name}.npz'
        with np.load(path) as payload:
            q = payload['class_atoms']; p = payload['probabilities']
        atoms = np.broadcast_to(q, (len(keys), len(q)))
        distribution = (atoms, np.repeat(p/32, 32, axis=1))
        result[stream] = distribution if stream == 'decay' else combine_distributions([base, distribution], [.5, .5])
        backups[stream] = q
        receipts.append(dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return result, backups, receipts


def run():
    DEST.mkdir(exist_ok=True)
    source_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    spec = dict(calibrators=CALIBRATORS, mixtures=MIXTURES, streams=STREAMS, references=REFERENCE,
        source_receipts=source_audit['receipts'], minimum_mature_origin_months=MIN_MONTHS,
        calibration='positive shared log-probability scale plus seven intercepts; month-equal multinomial log loss',
        scale_bounds=[.25, 4], intercept_bounds=[-2, 2], probability_floor=1e-6, penalty=PENALTY,
        penalty_prior='identity calibration; mixture coefficients centered on original B',
        recent_history='last 24 available matured origin months; every included label_end strictly before prediction date',
        conditional_distribution='preserve within-class source mass; if class absent use already trained class atoms, never current outcomes',
        mixture='B plus month-balanced stream plus unmixed-decay stream; nonnegative simplex weights, 7-class Brier objective',
        burn_in='calibrators exact original stream; learned mixture exact B; uniform mixture always fixed thirds',
        evidence='six fixed new candidates, two unchanged references; repeated retrospective exploration, not independent validation')
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    audits = []; parameters = []; mix_log = []; receipts = []
    for h in [1, 3, 6]:
        path = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in source_audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt['sha256']
        original = pd.read_parquet(path)
        base = pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'); base = base[base.model.eq('B')]
        frames = dict(B=base, **{key: original[original.model.eq(model)].copy() for key, model in STREAMS.items()})
        lookups = {key: frame.set_index(['date', 'instrument']) for key, frame in frames.items()}
        results = [frame.assign(model=REFERENCE[key]) for key, frame in frames.items() if key != 'B']
        for date, template in base.groupby('date', sort=True):
            template = template.reset_index(drop=True); keys = template[['date', 'instrument']]
            distributions, backups, current_receipts = source_distributions(h, date, keys); receipts.extend(current_receipts)
            current = {key: frame[frame.date.eq(date)].reset_index(drop=True) for key, frame in frames.items()}
            for key in STREAMS:
                pd.testing.assert_frame_equal(current[key][['date', 'instrument']], keys)
                a, w = distributions[key]; c = classes(a)
                np.testing.assert_allclose(np.column_stack([(w*(c == k)).sum(axis=1) for k in range(7)]), class_probabilities(current[key]), atol=1e-10)
            fitted = {}
            for name, (stream, window) in CALIBRATORS.items():
                history = calibration_history(base, date, window)
                months = history.date.nunique(); active = months >= MIN_MONTHS
                prediction = current[stream].copy(); prediction['model'] = name
                if active:
                    key = (stream, tuple(history.index))
                    if key not in fitted:
                        index = pd.MultiIndex.from_frame(history[['date', 'instrument']])
                        p = class_probabilities(lookups[stream].loc[index])
                        fitted[key] = fit_calibrator(p, classes(history.actual.to_numpy()), history.date)
                    pars, fit_info = fitted[key]
                    target = transform(class_probabilities(current[stream]), pars)
                    a, w = replace_class_mass(*distributions[stream], target, backups[stream])
                    stats = weighted_stats(a, w, prediction.actual); prediction[stats.columns] = stats.to_numpy()
                    parameters.append(dict(months=h, date=str(date.date()), model=name, scale=float(pars[0]),
                        **{f'intercept_{k}': float(pars[k+1]) for k in range(7)}, **fit_info))
                results.append(prediction)
                audits.append(dict(months=h, date=str(date.date()), model=name, source=stream, window=window,
                    history_rows=len(history), history_months=months, first_origin=str(history.date.min()),
                    latest_history_label=str(history.label_end.max()), active=active, test_rows=len(template)))
            history = calibration_history(base, date, 24); active = history.date.nunique() >= MIN_MONTHS
            coefficients = np.array([1., 0., 0.])
            if active:
                index = pd.MultiIndex.from_frame(history[['date', 'instrument']])
                probabilities = np.stack([class_probabilities(lookups[k].loc[index]) for k in ['B', 'month', 'decay']], axis=1)
                coefficients = fit_mixture(probabilities, classes(history.actual.to_numpy()), history.date)
            for name, values in [('uniform_frozen_mix', np.ones(3)/3), ('learned_frozen_mix', coefficients)]:
                prediction = template.copy(); prediction['model'] = name
                if name == 'uniform_frozen_mix' or active:
                    a, w = combine_distributions([distributions[k] for k in ['B', 'month', 'decay']], values)
                    stats = weighted_stats(a, w, prediction.actual); prediction[stats.columns] = stats.to_numpy()
                results.append(prediction)
                mix_log.append(dict(months=h, date=str(date.date()), model=name, B=float(values[0]),
                    month=float(values[1]), decay=float(values[2])))
                learned = name == 'learned_frozen_mix'
                audits.append(dict(months=h, date=str(date.date()), model=name, source='mixture', window=24 if learned else None,
                    history_rows=len(history) if learned else 0, history_months=history.date.nunique() if learned else 0,
                    first_origin=str(history.date.min()) if learned else 'NaT',
                    latest_history_label=str(history.label_end.max()) if learned else 'NaT',
                    active=active if learned else True, test_rows=len(template)))
            print(h, date.date(), 'mature_months', history.date.nunique(), flush=True)
        pd.concat(results, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv', index=False)
        pd.DataFrame(parameters).to_csv(DEST/'calibration_parameters.csv', index=False)
        pd.DataFrame(mix_log).to_csv(DEST/'mixture_weights.csv', index=False)
        pd.DataFrame(receipts).drop_duplicates('path').to_csv(DEST/'input_cache_receipts.csv', index=False)


if __name__ == '__main__':
    run()

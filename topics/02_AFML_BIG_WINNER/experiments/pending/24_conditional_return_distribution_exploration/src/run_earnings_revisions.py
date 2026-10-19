"""R20 matched classifier ablations and full-population revision models."""
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from prepare_panel import OUT
from build_earnings_revisions import PANEL, DEST, SOURCE
from run_eps_ablation import CLASS_COLS
from run_improvement_round1 import class_distribution
from run_direct_probability import classes, weighted_stats
from run_prequential_search import load_distribution, combine_distributions

META_COLS = CLASS_COLS[:6] + ['forecast_age_days', 'forecast_basis_profit']
REVISION_COLS = ['revision_available', 'growth_revision', 'revision_gap_days']
ALL_META = META_COLS + ['earnings_pair_available']
ALL_EARNINGS = CLASS_COLS + ['earnings_pair_available']
MODELS = {
    'matched_without_earnings': ('matched', META_COLS, .5),
    'matched_with_revisions': ('matched', CLASS_COLS + REVISION_COLS, .5),
    'all_without_earnings': ('all', ALL_META, .5),
    'all_with_earnings': ('all', ALL_EARNINGS, .5),
    'all_with_revisions': ('all', ALL_EARNINGS + REVISION_COLS, .5),
    'all_with_revisions_unmixed': ('all', ALL_EARNINGS + REVISION_COLS, 1.),
}
REFERENCE = 'r19_earnings_reference'


def run():
    DEST.mkdir(exist_ok=True)
    panel = pd.read_parquet(PANEL); panel = panel[panel.common_eligible]
    source_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    ref_fit = pd.read_csv(SOURCE/'fit_audit.csv')
    ref_fit = ref_fit[ref_fit.model.eq('earnings_forecast_classes')].copy(); ref_fit['model'] = REFERENCE
    audits = ref_fit.to_dict('records')
    spec = dict(models={k: dict(population=v[0], features=v[1], candidate_weight=v[2]) for k, v in MODELS.items()},
        reference=REFERENCE, reference_receipts=source_audit['receipts'],
        architecture=dict(iterations=100, depth=2, learning_rate=.03, l2_leaf_reg=20, random_seed=24),
        population='Original 27600 stock-date rows, 1/3/6 calendar months, frozen R15 B',
        revisions='same-broker, same-fiscal-year growth revision; history must already have been observed at an earlier decision',
        fallback='Matched variants exact B outside earnings coverage or below 1000 mature training rows; all variants keep missing predictors',
        status='fixed before evaluation; repeated retrospective exploration, not independent validation')
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    for h in [1, 3, 6]:
        receipt = next(r for r in source_audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        ref_path = SOURCE/f'predictions_{h}m.parquet'
        assert hashlib.sha256(ref_path.read_bytes()).hexdigest() == receipt['sha256']
        ref = pd.read_parquet(ref_path); ref = ref[ref.model.eq('earnings_forecast_classes')].copy(); ref['model'] = REFERENCE
        results = [ref]
        baseline = pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet')
        baseline = baseline[baseline.model.eq('B')]
        for date, test in panel[panel.date >= '2021-01-01'].groupby('date', sort=True):
            test = test.reset_index(drop=True)
            mature = panel[panel[f'y_{h}'].notna() & (panel[f'end_{h}'] < date)]
            base = baseline[baseline.date.eq(date)].reset_index(drop=True)
            pd.testing.assert_frame_equal(base[['date', 'instrument']], test[['date', 'instrument']])
            b_atoms, b_weights = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', test[['date', 'instrument']])
            fitted = {}
            for name, (population, cols, candidate_weight) in MODELS.items():
                train = mature[mature.earnings_pair_available] if population == 'matched' else mature
                mask = test.earnings_pair_available.to_numpy() if population == 'matched' else np.ones(len(test), dtype=bool)
                prediction = base.copy(); prediction['model'] = name
                active = len(train) >= 1000 and mask.any()
                if active:
                    key = (population, tuple(cols))
                    if key not in fitted:
                        y = train[f'y_{h}'].to_numpy(); labels = classes(y)
                        model = CatBoostClassifier(loss_function='MultiClass', iterations=100, depth=2,
                            learning_rate=.03, l2_leaf_reg=20, random_seed=24, thread_count=4,
                            verbose=False, allow_writing_files=False)
                        model.fit(train[cols].astype(float), labels)
                        probabilities = np.zeros((int(mask.sum()), 7))
                        probabilities[:, model.classes_.astype(int)] = model.predict_proba(test.loc[mask, cols].astype(float))
                        fitted[key] = class_distribution(y, labels, probabilities)
                    a, w = fitted[key]
                    if candidate_weight < 1:
                        a, w = combine_distributions([(b_atoms[mask], b_weights[mask]), (a, w)], [1-candidate_weight, candidate_weight])
                    stats = weighted_stats(a, w, prediction.loc[mask, 'actual'])
                    prediction.loc[mask, stats.columns] = stats.to_numpy()
                results.append(prediction)
                audits.append(dict(months=h, date=str(date.date()), model=name, training_rows=len(train),
                    last_training_label=str(train[f'end_{h}'].max()), test_rows=len(test),
                    adjusted_rows=int(mask.sum()) if active else 0))
            print(h, date.date(), 'mature', len(mature), 'revision_queries', int(test.revision_available.sum()), flush=True)
        pd.concat(results, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv', index=False)


if __name__ == '__main__':
    run()

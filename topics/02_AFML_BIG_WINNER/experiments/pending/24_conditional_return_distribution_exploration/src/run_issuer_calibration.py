"""R39 fixed stock-specific shrinkage on two frozen full-population priors."""
import json
import numpy as np
import pandas as pd
from prepare_panel import EP, OUT
from build_margin_information import digest
from recover_baseline_precision import RECOVERED
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import weighted_stats
from run_four_horizons import probability_stats
from run_joint_information import frame_digest
from issuer_calibration import add_buckets, estimate, score

DEST = OUT/'r39_issuer_calibration'
CACHE = OUT/'local_cache/r39_issuer_calibration'
PANEL = OUT/'local_cache/historical_peer_panel.parquet'
PLAN = EP/'notes/r39_issuer_calibration.md'
REFERENCE = OUT/'r31_financial_quality'
MODELS = {f'{prior}_{mode}': (prior, mode) for prior in ['base', 'extra'] for mode in ['sign', 'bins']}


def priors(h, date, base, reference, keys):
    template = base[base.date.eq(date)].reset_index(drop=True)
    old = reference[reference.date.eq(date)].reset_index(drop=True)
    for frame in [template, old]:
        pd.testing.assert_frame_equal(frame[['date', 'instrument']], keys)
    ba, bw = load_distribution(RECOVERED, h, date, 'B', keys)
    bs = probability_stats(ba, template.actual)
    np.testing.assert_allclose(bs, template[bs.columns], atol=1e-12, rtol=1e-12, equal_nan=True)
    path = OUT/f'local_cache/r31_class_distributions/{h}_{date.date()}_extra_reference.npz'
    keypath = path.parent/f'{h}_{date.date()}_keys.parquet'
    pd.testing.assert_frame_equal(pd.read_parquet(keypath), keys)
    with np.load(path) as payload:
        a = np.tile(payload['class_atoms'], (len(keys), 1))
        w = np.repeat(payload['probabilities']/32, 32, axis=1)
    aa, ww = combine_distributions([(ba, bw), (a, w)], [.5, .5])
    es = weighted_stats(aa, ww, old.actual)
    np.testing.assert_allclose(es, old[es.columns], atol=1e-12, rtol=1e-12, equal_nan=True)
    assert np.array_equal(es.p_up.gt(es.p_down), old.p_up.gt(old.p_down))
    paths = [path, keypath, RECOVERED/f'{h}_{date.date()}_B.npz', RECOVERED/f'{h}_{date.date()}_keys.parquet']
    receipts = [dict(path=str(p), sha256=digest(p)) for p in paths]
    return {'base': (template, ba, bw), 'extra': (old, aa, ww)}, receipts


def run():
    DEST.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    assert not (DEST/'spec.json').exists(), 'Do not overwrite a started frozen experiment'
    audit = json.loads((REFERENCE/'research_integrity_audit.json').read_text())
    assert audit['technical_integrity_passed']
    spec = dict(models=MODELS, panel_sha256=digest(PANEL), plan_sha256=digest(PLAN),
        shrinkage='20 * horizon monthly pseudo-observations; uniform per class', min_peers=10,
        reference_receipts=audit['receipts'], original_candidates_completed=131)
    (DEST/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    panel = add_buckets(pd.read_parquet(PANEL)); fits=[]; sources=[]
    for h in [1, 3, 6]:
        bp = OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet'
        rp = REFERENCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in audit['receipts'] if r['path'].endswith(rp.name))
        assert digest(rp) == receipt['sha256']
        sources.extend([dict(path=str(p), sha256=digest(p)) for p in [bp, rp]])
        base = pd.read_parquet(bp); base = base[base.model.eq('B')]
        ref = pd.read_parquet(rp); ref = ref[ref.model.eq('extra_reference')]
        rows = [base.assign(model='base_reference'), ref]
        for date, test in panel[panel.date.ge('2021-01-01')].groupby('date', sort=True):
            test = test.reset_index(drop=True); keys = test[['date', 'instrument']]
            stem = f'{h}_{date.date()}'
            keys.to_parquet(CACHE/f'{stem}_keys.parquet', index=False)
            distributions, receipts = priors(h, date, base, ref, keys); sources.extend(receipts)
            for mode in ['sign', 'bins']:
                factors, history, details = estimate(panel, h, date, test.instrument, mode)
                path = CACHE/f'{stem}_{mode}.npz'
                np.savez_compressed(path, factors=factors, history=history)
                fits.append(dict(months=h, date=str(date.date()), mode=mode, **details,
                    cache_sha256=digest(path), keys_sha256=frame_digest(keys)))
                for prior in ['base', 'extra']:
                    template, a, w = distributions[prior]
                    result = score(template, a, w, factors, history, mode)
                    pred = template.copy(); pred['model'] = f'{prior}_{mode}'
                    pred[result.columns] = result.to_numpy(); rows.append(pred)
            print(h, date.date(), 'finished', flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet', index=False)
        pd.DataFrame(fits).to_csv(DEST/'fit_audit.csv', index=False)
        (DEST/'source_receipts.json').write_text(json.dumps(sources, indent=2)+'\n')


if __name__ == '__main__':
    run()

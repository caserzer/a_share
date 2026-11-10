"""Fixed date/industry permutation of diffusion variables, matched capacity."""
from pathlib import Path
import json
import sys
import hashlib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT.parent
sys.path.insert(0, str(EXT / 'v31_all_signal_economics/src'))
from common31 import sha, js, OLD
OUT = ROOT / 'outputs'
CACHE = OLD.parent / 'mechanism_v32'
IDENTITY = ['era', 'level', 'industry_code', 'date', 'threshold', 'benchmark']


def shuffle(frame, added):
    """Group-derived seeds ensure extending future data cannot change past shuffles."""
    result = frame.copy()
    for key, group in frame.groupby(['date', 'era', 'level', 'threshold', 'benchmark'], sort=True):
        ids = group.sort_values('industry_code').index
        seed = int(hashlib.sha256(('32:' + str(key)).encode()).hexdigest()[:8], 16)
        order = np.random.default_rng(seed).permutation(len(ids))
        result.loc[ids, added] = frame.loc[ids, added].to_numpy()[order]
    return result


def run():
    OUT.mkdir(parents=True, exist_ok=True); CACHE.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((EXT / 'v18_conditional_diffusion/outputs/frozen_candidates.json').read_text())
    receipt = json.loads((EXT / 'v18_conditional_diffusion/outputs/prediction_receipt.json').read_text())
    feature_path = OLD.parent / 'diffusion_v18/features.parquet'
    assert sha(feature_path) == receipt['features_sha256']
    g = pd.read_parquet(feature_path)
    g = g[g.date.lt('2024-10-01')].reset_index(drop=True)
    observations = pd.read_parquet(OLD / 'features.parquet')
    labels = pd.read_parquet(OLD / 'stage_b_labels.parquet')
    lab = observations[['row_id','era','level','industry_code','date']].merge(labels,on='row_id',validate='one_to_many')
    lab = lab[IDENTITY + ['y','label_available_at']].drop_duplicates(IDENTITY)
    g = g.merge(lab, on=IDENTITY, validate='one_to_one')
    added = cfg['added']; features = cfg['base_features'] + added
    js(OUT / 'negative_control_freeze.json', dict(plan_sha256=sha(EXT / 'v31_all_signal_economics/research_plan.md'),
        code_sha256=sha(__file__), input_sha256=sha(feature_path), params=cfg['params'], seed=32,
        permutation='within date/era/level/threshold/benchmark joint diffusion vector; group-derived seed',
        iterations=1, inference='single falsification control; not a permutation p value'))
    shuffled = shuffle(g, added)
    cutoff = pd.Timestamp('2021-01-01')
    prefix = shuffle(g[g.date.lt(cutoff)], added)
    assert np.array_equal(prefix[added].to_numpy(), shuffled.loc[prefix.index,added].to_numpy(), equal_nan=True)
    original_scores = pd.read_parquet(OLD.parent / 'diffusion_v18/scores.parquet')
    rows = []; folds = []
    for q in pd.date_range('2021-01-01', '2024-07-01', freq='QS'):
        train_mask = g.state_eligible.eq(1) & g.date.lt(q) & g.label_available_at.lt(q) & g.y.notna()
        test_mask = g.date.ge(q) & g.date.lt(q+pd.DateOffset(months=3))
        train = shuffled[train_mask]; test = shuffled[test_mask]
        if test.empty:
            folds.append(dict(quarter=str(q.date()), training=len(train), test=0,
                              status='NO_OBSERVATIONS_CLASSIFICATION_GAP'))
            continue
        assert train.label_available_at.max() < q
        weights = 1 / train.groupby(['date','level']).date.transform('size').to_numpy(float)
        weights /= weights.mean()
        model = LGBMClassifier(**cfg['params'])
        model.fit(train[features], train.y, sample_weight=weights)
        r = test[IDENTITY].copy(); eligible = test.state_eligible.eq(1)
        r['shuffled_diffusion'] = 0.
        if eligible.any():
            r.loc[eligible,'shuffled_diffusion'] = np.clip(model.predict_proba(test.loc[eligible,features])[:,1],1e-6,1-1e-6)
        # One exact original-model replay validates training identity, parameters and weights.
        if q == pd.Timestamp('2021-01-01'):
            base_train = g[train_mask]; base_test = g[test_mask]
            original_model = LGBMClassifier(**cfg['params'])
            original_model.fit(base_train[features], base_train.y, sample_weight=weights)
            predictions = np.zeros(len(base_test)); predictions[eligible.to_numpy()] = np.clip(
                original_model.predict_proba(base_test.loc[eligible,features])[:,1],1e-6,1-1e-6)
            old = base_test[IDENTITY].merge(original_scores[IDENTITY+['diffusion_tree']], on=IDENTITY,validate='one_to_one')
            assert np.allclose(predictions, old.diffusion_tree, atol=1e-12, rtol=1e-12)
        rows.append(r)
        folds.append(dict(quarter=str(q.date()), training=len(train), latest_label=str(train.label_available_at.max()),
                          test=len(test), positives=int(train.y.sum())))
        print('fixed diffusion negative control', q.date(), 'train', len(train), flush=True)
    scores = pd.concat(rows,ignore_index=True)
    scores.to_parquet(CACHE / 'shuffled_scores.parquet',index=False)
    js(OUT / 'negative_control_receipt.json',dict(folds=folds, rows=len(scores),
        scores_sha256=sha(CACHE / 'shuffled_scores.parquet'), original_q1_replay='PASS', permutation_prefix='PASS'))


if __name__ == '__main__':
    run()

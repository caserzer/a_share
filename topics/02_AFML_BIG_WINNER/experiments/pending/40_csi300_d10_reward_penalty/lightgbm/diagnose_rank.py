"""Compare the 20- and 80-tree checkpoints of the 23 saved rank models."""
import json

import lightgbm as lgb
import numpy as np
import pandas as pd

from fit_trees import COLS, KEY, OUT, outer, prepare


def by_signal_date(frame, predictions):
    sample = frame[['signal_date', 'h10']].assign(score=predictions).dropna()
    labels = sample.groupby('signal_date').h10
    sample['target'] = labels.rank() / (1 + labels.transform('count')) - .5
    sample['squared_error'] = (sample.score - sample.target) ** 2
    ranks = sample.groupby('signal_date')[['score', 'target']].rank()
    correlations = ranks.groupby(sample.signal_date).corr().xs('score', level=1)
    return sample.groupby('signal_date').squared_error.mean().to_frame().join(
        correlations.target.rename('rankic'))


def main():
    data = prepare()
    rankings = pd.read_parquet(OUT/'rankings.parquet', filters=[('arm', '=', 'tree_rank')])
    test = outer().merge(rankings[KEY+['h10','scope','score']], on=KEY, validate='1:1')
    assert len(test) == len(rankings)
    rows = []
    for fold, group in test.groupby('fold'):
        cutoff = pd.Period(fold).start_time
        training = data[(data.signal_date < cutoff) & (data.h10_mature < cutoff)]
        folder = OUT/'models'/fold
        model = lgb.Booster(model_file=str(folder/'tree_rank.txt'))
        medians = pd.Series(json.loads((folder/'medians.json').read_text()))
        for scope, frame in [('train', training), *group.groupby('scope')]:
            features = frame[COLS].fillna(medians)
            for trees in (20, 80):
                score = model.predict(features, num_iteration=trees, num_threads=2)
                if scope != 'train' and trees == 80:
                    np.testing.assert_allclose(score, frame.score, rtol=0, atol=1e-12)
                dates = by_signal_date(frame, score)
                rows.append(dict(fold=fold, scope=scope, trees=trees, dates=len(dates),
                                 mse=dates.squared_error.mean(), rankic=dates.rankic.mean()))
    folds = pd.DataFrame(rows)
    folds.to_csv(OUT/'rank_checkpoint_folds.csv', index=False)
    for (scope, trees), g in folds.groupby(['scope','trees']):
        # Training windows overlap. Give each fold equal weight there and each date
        # equal weight in the disjoint outer windows.
        weights = None if scope == 'train' else g.dates
        print(scope, trees, np.average(g.rankic, weights=weights),
              np.average(g.mse, weights=weights))
    w = pd.read_parquet(OUT/'windows.parquet', filters=[('cost','=','base')])
    for scope, g in w.groupby('scope'):
        net = g.pivot(index='entry_idx', columns='arm', values='net')
        print(scope, 'tree wins', (net.tree_rank > net.baseline).sum(), '/', len(net))


if __name__ == '__main__':
    main()

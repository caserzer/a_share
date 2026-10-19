"""Mature, leave-one-out issuer probability deviations with fixed shrinkage."""
import numpy as np
import pandas as pd
from run_direct_probability import classes, weighted_stats
from run_market_time_models import select_training


def add_buckets(panel):
    result = panel.copy()
    if result.duplicated(['date', 'instrument']).any():
        raise ValueError('One observation per issuer and origin required')
    for column in ['vol63', 'log_cap']:
        rank = result.groupby('date')[column].rank(method='average', pct=True)
        result[column+'_bucket'] = np.floor(4*rank).clip(upper=3).fillna(-1).astype(int)
    return result


def peer_probabilities(train, horizon, mode):
    """The subject's realized label never enters its own peer distribution."""
    d = train.copy()
    if mode == 'sign':
        d = d[d[f'y_{horizon}'].ne(0)].copy()
        labels = d[f'y_{horizon}'].gt(0).astype(int).to_numpy(); k = 2
    elif mode == 'bins':
        labels = classes(d[f'y_{horizon}']); k = 7
    else:
        raise ValueError(mode)
    observed = np.eye(k)[labels]
    counts = pd.DataFrame(observed, index=d.index, columns=[f'c{i}' for i in range(k)])
    keys = [d.date, d.vol63_bucket, d.log_cap_bucket]
    group_sum = counts.groupby(keys).transform('sum').to_numpy()-observed
    group_n = d.groupby(['date', 'vol63_bucket', 'log_cap_bucket']).instrument.transform('size').to_numpy()-1
    all_sum = counts.groupby(d.date).transform('sum').to_numpy()-observed
    all_n = d.groupby('date').instrument.transform('size').to_numpy()-1
    if len(d) and (all_n < 1).any():
        raise ValueError('At least one other mature same-month issuer required')
    fallback = group_n < 10
    numerator = np.where(fallback[:, None], all_sum, group_sum)
    denominator = np.where(fallback, all_n, group_n)
    expected = numerator/denominator[:, None]
    return d, observed, expected, fallback


def estimate(panel, horizon, date, instruments, mode):
    train = select_training(panel, horizon, date, None)
    d, observed, expected, fallback = peer_probabilities(train, horizon, mode)
    k = observed.shape[1]
    observed_counts = pd.DataFrame(observed, index=d.instrument).groupby(level=0).sum()
    expected_counts = pd.DataFrame(expected, index=d.instrument).groupby(level=0).sum()
    o = observed_counts.reindex(instruments).fillna(0).to_numpy()
    e = expected_counts.reindex(instruments).fillna(0).to_numpy()
    factor = (o + 20*horizon/k)/(e + 20*horizon/k)
    history = o.sum(axis=1).astype(int)
    assert np.isfinite(factor).all() and (factor > 0).all()
    return factor, history, dict(training_rows=len(train), calibration_rows=len(d),
        training_months=train.date.nunique(), last_training_label=str(train[f'end_{horizon}'].max()),
        peer_fallback_rows=int(fallback.sum()), stocks_with_history=int((history > 0).sum()),
        test_rows=len(instruments))


def calibrate_weights(atoms, weights, factors, mode):
    if mode == 'bins':
        index = classes(atoms)
        adjusted = weights*np.take_along_axis(factors, index, axis=1)
        adjusted /= adjusted.sum(axis=1, keepdims=True)
    elif mode == 'sign':
        index = (atoms > 0).astype(int)
        adjusted = weights*np.take_along_axis(factors, index, axis=1)
        nonzero = atoms != 0
        old_mass = (weights*nonzero).sum(axis=1, keepdims=True)
        new_mass = (adjusted*nonzero).sum(axis=1, keepdims=True)
        scale = np.divide(old_mass, new_mass, out=np.ones_like(old_mass), where=new_mass > 0)
        adjusted = np.where(nonzero, adjusted*scale, weights)
    else:
        raise ValueError(mode)
    np.testing.assert_allclose(adjusted.sum(axis=1), 1, atol=1e-12)
    return adjusted


def score(prior, atoms, weights, factors, history, mode):
    adjusted = calibrate_weights(atoms, weights, factors, mode)
    result = weighted_stats(atoms, adjusted, prior.actual)
    if mode == 'sign':
        # Analytic sign marginal preserves the original zero mass and exact ties.
        signs = prior[['p_down', 'p_up']].to_numpy()*factors
        total = signs.sum(axis=1, keepdims=True)
        mass = 1-prior.p_zero.to_numpy()[:, None]
        signs = np.divide(signs*mass, total, out=np.zeros_like(signs), where=total > 0)
        np.testing.assert_allclose(result[['p_down', 'p_up']], signs, atol=1e-12)
        result[['p_down', 'p_up']] = signs
        result['p_zero'] = prior.p_zero.to_numpy()
        result['brier'] = np.where(prior.actual.notna(), (result.p_up-prior.actual.gt(0))**2, np.nan)
    identity = (history == 0) | (factors == 1).all(axis=1)
    result.loc[identity, :] = prior.loc[identity, result.columns].to_numpy()
    return result

"""Conditional empirical distributions from sklearn 1.9 weighted forests."""
import numpy as np
import sklearn
from run_direct_probability import classes


def training_impute(train, test):
    """Train-only medians, deterministic all-missing fallback and all indicators."""
    train = np.asarray(train, dtype=float); test = np.asarray(test, dtype=float)
    if train.ndim != 2 or test.ndim != 2 or train.shape[1] != test.shape[1]:
        raise ValueError('Feature shapes differ')
    if np.isinf(train).any() or np.isinf(test).any():
        raise ValueError('Infinite input')
    medians = np.array([np.median(c[np.isfinite(c)]) if np.isfinite(c).any() else 0. for c in train.T])
    def transform(x):
        missing = np.isnan(x)
        return np.column_stack([np.where(missing, medians, x), missing.astype(float)]).astype(np.float32)
    return transform(train), transform(test), medians


def forest_weights(model, train_x, test_x, sample_weight):
    if not sklearn.__version__.startswith('1.9.'):
        raise RuntimeError('Revalidate weighted-bootstrap semantics for this sklearn version')
    sample_weight = np.asarray(sample_weight, dtype=float)
    if len(sample_weight) != len(train_x) or not np.isfinite(sample_weight).all() or (sample_weight <= 0).any():
        raise ValueError('Invalid training weights')
    train_leaves = model.apply(train_x); test_leaves = model.apply(test_x)
    result = np.zeros((len(test_x), len(train_x)), dtype=float)
    samples = model.estimators_samples_
    for j, tree in enumerate(model.estimators_):
        effective = np.bincount(samples[j], minlength=len(train_x)).astype(float) if model.bootstrap else sample_weight
        leaf = train_leaves[:, j]
        for node in np.unique(test_leaves[:, j]):
            source = np.flatnonzero((leaf == node) & (effective > 0))
            query = np.flatnonzero(test_leaves[:, j] == node)
            assert len(source) > 0
            local = effective[source]/effective[source].sum()/len(model.estimators_)
            result[np.ix_(query, source)] += local
    np.testing.assert_allclose(result.sum(axis=1), 1, atol=1e-12)
    return result


def local_class_distribution(y, weights, probabilities):
    y = np.asarray(y, dtype=float); weights = np.asarray(weights, dtype=float)
    probabilities = np.asarray(probabilities, dtype=float)
    if not np.isfinite(y).all() or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError('Invalid empirical distribution')
    if weights.shape != (len(probabilities), len(y)) or probabilities.shape[1] != 7:
        raise ValueError('Distribution shapes differ')
    np.testing.assert_allclose(weights.sum(axis=1), 1, atol=1e-12)
    labels = classes(y); grid = (np.arange(32)+.5)/32
    atoms = np.tile(np.repeat([-.3,-.1,-.025,0.,.025,.1,.3],32), (len(weights),1))
    mass = np.column_stack([weights[:, labels == k].sum(axis=1) for k in range(7)])
    np.testing.assert_allclose(mass, probabilities, atol=1e-12, rtol=1e-12)
    for k in range(7):
        indices = np.flatnonzero(labels == k); indices = indices[np.argsort(y[indices], kind='stable')]
        values = y[indices]
        for row in range(len(weights)):
            w = weights[row, indices]; mask = w > 0
            if mask.any():
                v = values[mask]; w = w[mask]
                centers = (np.cumsum(w)-.5*w)/w.sum()
                atoms[row, k*32:(k+1)*32] = np.interp(grid, centers, v)
    np.testing.assert_array_equal(classes(atoms), np.tile(np.repeat(np.arange(7),32), (len(atoms),1)))
    return atoms, np.repeat(probabilities/32,32,axis=1)

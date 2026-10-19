"""Ordered and normalized proper-score split targets; coherent leaf masses."""
import numpy as np
from run_direct_probability import classes


def loss_targets(y, weights, kind):
    y = np.asarray(y, float); w = np.asarray(weights, float)
    if y.ndim != 1 or w.shape != y.shape or not np.isfinite(y).all() or not np.isfinite(w).all() or (w <= 0).any():
        raise ValueError('Finite mature labels and positive matching weights required')
    w = w/w.sum()
    if kind == 'ordinal':
        targets = (classes(y)[:, None] <= np.arange(6)).astype(float)
        return targets, dict(grid=np.array([]), widths=np.array([]), denominators=np.array([]), scales=np.ones(6))
    if kind != 'joint': raise ValueError(kind)
    order = np.argsort(y, kind='stable'); sy = y[order]; sw = w[order]
    centers = sw.cumsum()-.5*sw
    edges = np.unique(np.interp(np.linspace(0, 1, 33), centers, sy))
    widths = np.diff(edges); grid = .5*(edges[:-1]+edges[1:])
    up = (y > 0).astype(float)[:, None]
    five = np.eye(5)[np.searchsorted([-.2, -.05, .05, .2], y, side='right')]
    cumulative = (y[:, None] <= grid).astype(float)
    p = w@up; q = w@five; c = w@cumulative
    denominators = np.maximum([float((p*(1-p)).sum()), float((q*(1-q)).sum()), float((widths*c*(1-c)).sum())], 1e-8)
    scales = np.r_[np.sqrt(1/denominators[0]), np.repeat(np.sqrt(1/denominators[1]), 5), np.sqrt(widths/denominators[2])]
    targets = np.column_stack([up, five, cumulative])*scales
    return targets, dict(grid=grid, widths=widths, denominators=denominators, scales=scales)


def leaf_means(train_leaves, test_leaves, values, weights):
    """No bootstrap: each leaf uses the original month-balanced row weights."""
    tr = np.asarray(train_leaves); te = np.asarray(test_leaves)
    v = np.asarray(values, float); w = np.asarray(weights, float)
    if tr.ndim != 2 or te.ndim != 2 or tr.shape[1] != te.shape[1] or len(v) != len(tr) or w.shape != (len(tr),):
        raise ValueError('Mismatched forest shapes')
    out = np.zeros((len(te), v.shape[1]))
    for j in range(tr.shape[1]):
        n = max(tr[:, j].max(), te[:, j].max())+1
        mass = np.bincount(tr[:, j], weights=w, minlength=n)
        if (mass[te[:, j]] <= 0).any(): raise ValueError('Unobserved test leaf')
        for k in range(v.shape[1]):
            sums = np.bincount(tr[:, j], weights=w*v[:, k], minlength=n)
            out[:, k] += sums[te[:, j]]/mass[te[:, j]]
    return out/tr.shape[1]


def leaf_probabilities(train_leaves, test_leaves, y, weights):
    p = leaf_means(train_leaves, test_leaves, np.eye(7)[classes(y)], weights)
    assert np.isfinite(p).all() and (p >= 0).all()
    np.testing.assert_allclose(p.sum(axis=1), 1, atol=1e-12)
    return p

"""Coherent sign-first probabilities without changing the direction decision rule."""
import numpy as np


def validate_probabilities(values, columns):
    p = np.asarray(values, dtype=float)
    if p.ndim != 2 or p.shape[1] != columns or not np.isfinite(p).all() or (p < 0).any():
        raise ValueError('Finite nonnegative probability rows required')
    if not np.allclose(p.sum(axis=1), 1., rtol=0, atol=1e-10):
        raise ValueError('Probability rows must sum to one')
    return p


def sign_classes(y):
    values = np.asarray(y, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('Only observed mature labels may train sign models')
    return np.where(values < 0, 0, np.where(values == 0, 1, 2))


def conditional_magnitudes(flat, prior):
    """Preserve each sign's old three-bin proportions; train-only fallback."""
    p = validate_probabilities(flat, 7)
    empirical = validate_probabilities(np.asarray(prior, dtype=float).reshape(1, 7), 7)[0]
    results = []
    for ix in [slice(0, 3), slice(4, 7)]:
        source = p[:, ix]; mass = source.sum(axis=1, keepdims=True)
        fallback = empirical[ix]
        fallback = fallback/fallback.sum() if fallback.sum() > 0 else np.full(3, 1/3)
        conditional = np.tile(fallback, (len(p), 1))
        np.divide(source, mass, out=conditional, where=mass > 0)
        results.append(conditional)
    return tuple(results)


def assemble_classes(sign, negative, positive):
    """Sign order: down, zero, up; return original seven disjoint bins."""
    s = validate_probabilities(sign, 3)
    neg = validate_probabilities(negative, 3); pos = validate_probabilities(positive, 3)
    if len(s) != len(neg) or len(s) != len(pos):
        raise ValueError('All predictions must share query rows')
    p = np.column_stack([s[:, :1]*neg, s[:, 1], s[:, 2:3]*pos])
    return validate_probabilities(p, 7)


def stable_sign_scores(stats, sign, baseline_sign, candidate_fraction, actual):
    """Same sign head gives exactly the same direction under both magnitude fits.

    This is the analytic marginal of the already-combined atom distribution, not
    a different decision threshold. Avoid different floating-point reductions
    accidentally breaking exact sign ties across magnitude variants.
    """
    s = validate_probabilities(sign, 3); b = validate_probabilities(baseline_sign, 3)
    if len(s) != len(b) or not 0 <= candidate_fraction <= 1:
        raise ValueError('Invalid matched mixture')
    marginal = (1-candidate_fraction)*b+candidate_fraction*s
    result = stats.copy()
    result[['p_down', 'p_zero', 'p_up']] = marginal
    y = np.asarray(actual, dtype=float)
    result['brier'] = np.where(np.isfinite(y), (marginal[:, 2]-(y > 0))**2, np.nan)
    return result

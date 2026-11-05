"""BH correction and a stationary time-block bootstrap with shared row draws."""
import numpy as np


def bh(pvalues):
    p = np.asarray(pvalues, float)
    result = np.full(len(p), np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    order = valid[np.argsort(p[valid])]
    if len(order):
        adjusted = p[order]*len(order)/np.arange(1, len(order)+1)
        result[order] = np.minimum(1, np.minimum.accumulate(adjusted[::-1])[::-1])
    return result


def stationary_indices(n, replicates=1999, mean_block=6, seed=310021):
    rng = np.random.default_rng(seed)
    draws = np.empty((replicates, n), dtype=int)
    if not n:
        return draws
    draws[:, 0] = rng.integers(n, size=replicates)
    for k in range(1, n):
        restart = rng.random(replicates) < 1/mean_block
        draws[:, k] = np.where(restart, rng.integers(n, size=replicates), (draws[:, k-1]+1) % n)
    return draws


def infer_effect(months, direction=1, ratio=False):
    """Monthly inputs retain all same-date stocks; ratios resample both moments."""
    if ratio:
        a = months[["numerator", "denominator"]].dropna().to_numpy(float)
    else:
        a = months[["loss_gain"]].dropna().to_numpy(float)
    n = len(a)
    if n < 2:
        return dict(estimate=None, ci_low=None, ci_high=None, p_one_sided=None, months=n)
    draws = stationary_indices(n)
    if ratio:
        observed = a[:, 0].mean() / max(a[:, 1].mean(), 1e-15)
        sample = a[draws].mean(axis=1)
        boot = sample[:, 0] / np.maximum(sample[:, 1], 1e-15)
    else:
        observed = a[:, 0].mean()
        boot = a[draws, 0].mean(axis=1)
    if n < 12:
        return dict(estimate=float(observed), ci_low=None, ci_high=None, p_one_sided=None, months=n,
                    inference_status="INSUFFICIENT_TEMPORAL_BLOCKS")
    low, high = np.quantile(boot, [0.025, 0.975])
    # Center the empirical bootstrap under H0 for a preregistered one-sided test.
    null = direction*(boot-observed)
    p = (1+np.sum(null >= direction*observed))/(len(boot)+1)
    return dict(estimate=float(observed), ci_low=float(low), ci_high=float(high), p_one_sided=float(p), months=n,
                inference_status="TIME_BLOCK_BOOTSTRAP")

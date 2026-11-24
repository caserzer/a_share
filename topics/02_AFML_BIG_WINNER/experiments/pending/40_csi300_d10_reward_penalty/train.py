"""Quarterly EP40 fits. Run with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1."""
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import minimize
from scipy.special import expit

HERE = Path(__file__).resolve().parent
OUT = HERE / 'results'
TRACK = next(HERE.parent.glob('38_*')) / 'three_track'
sys.path.insert(0, str(TRACK))
from shared import OLD, PRIVATE, BASE, COLS, KEY, outer, ridge, predict

ARMS = ['baseline', 'penalty', 'reward', 'both', 'double_reward', 'graded', 'magnitude']


def prepare():
    features = pd.read_parquet(PRIVATE/'features.parquet', columns=KEY+['score_eligible', *COLS])
    labels = pd.read_parquet(PRIVATE/'labels.parquet', columns=KEY+['h10', 'target_z', 'h10_mature'])
    data = features.merge(labels, on=KEY, validate='1:1').query('score_eligible and target_z == target_z')
    data = data.sort_values(['signal_date', 'h10', 'instrument']).copy()
    groups = data.groupby('signal_date')
    size = groups.h10.transform('size')
    data['decile'] = 1 + 10 * groups.cumcount() // size
    data['target_rank'] = groups.h10.rank() / (size+1) - .5
    data['above_median'] = data.h10 - groups.h10.transform('median')
    return data


def utility_scores(scores, utility, starts, size):
    """Derivative through both daily standardization and implicit top-k threshold."""
    ids = np.repeat(np.arange(len(size)), size)
    def total(v):
        return np.add.reduceat(v, starts)
    centered = scores - (total(scores)/size)[ids]
    sd = np.sqrt(total(centered**2)/size)
    assert sd.min() > 1e-10
    z = centered / sd[ids]
    seats = size//10
    lo = np.minimum.reduceat(z, starts)-5
    hi = np.maximum.reduceat(z, starts)+5
    h = np.clip(np.full(len(size), 1.2), lo, hi)
    for _ in range(55):
        p = expit((z-h[ids])/.1)
        dp = p*(1-p)/.1
        err = total(p)-seats
        if np.max(abs(err)) < 1e-9:
            break
        hi = np.where(err < 0, h, hi)
        lo = np.where(err > 0, h, lo)
        proposal = h + err / np.maximum(total(dp), 1e-12)
        h = np.where(abs(err)<1e-10, h, np.where((lo<proposal)&(proposal<hi), proposal, (lo+hi)/2))
    else:
        raise ArithmeticError('top-k threshold root')
    loss = np.mean(total(p*utility)/seats)
    dz = dp*(utility-(total(dp*utility)/total(dp))[ids])/(len(size)*seats[ids])
    ds = (dz-(total(dz)/size)[ids]-z*(total(dz*z)/size)[ids])/sd[ids]
    return loss, ds


def fit_quarter(quarter):
    q = pd.Period(quarter)
    fit = DATA[(DATA.signal_date<q.start_time)&(DATA.h10_mature<q.start_time)]
    outer_rows = OUTER[OUTER.signal_date.dt.to_period('Q') == q]
    assert len(fit) == REF.loc[quarter, 'train_rows']
    model = ridge(fit, COLS, 'target_rank')
    base = np.array(model['coef'])
    v = fit[COLS].to_numpy()
    x = np.ascontiguousarray((np.where(np.isnan(v), model['median'], v)-model['mean'])/model['sd'])
    xmean = x.mean(axis=0)
    x -= xmean
    y = fit.target_rank.to_numpy()
    # Profile the unpenalized intercept. In Ridge-whitened coordinates the exact
    # increase in regularized MSE above its minimum is the squared step norm.
    lower = cholesky((x.T@x+10*np.eye(len(base)))/len(x), lower=True)
    transform = solve_triangular(lower.T, np.eye(len(base)), lower=False)
    wx = np.ascontiguousarray(x@transform)
    base_scores = x@base
    size = fit.groupby('signal_date').size().to_numpy()
    starts = np.r_[0, np.cumsum(size)[:-1]]
    dec = fit.decile.to_numpy()
    bad = (dec<=5).astype(float)
    win = (dec==10).astype(float)
    graded = np.choose(np.clip(dec-7, 0, 3), [0., .25, .5, 1.])
    cap = np.quantile(fit.above_median[dec==10], .95)
    mag = np.minimum(fit.above_median.to_numpy(), cap)*win
    def daily_mean(v):
        return np.mean(np.add.reduceat(v, starts)/size)
    gs, ms = daily_mean(win)/daily_mean(graded), daily_mean(win)/daily_mean(mag)
    utilities = [0*win, bad, -win, bad-win, bad-2*win, bad-gs*graded, bad-ms*mag]
    scored = outer_rows[KEY+['entry_idx','exit_idx','vol20']].copy()
    audits, models = [], {}
    for arm, util in zip(ARMS, utilities):
        def objective(step):
            u, grad = utility_scores(base_scores+wx@step, util, starts, size)
            return step@step+.02*u, 2*step+.02*(grad@wx)
        initial = np.zeros(len(base))
        res = minimize(objective, initial, jac=True, method='L-BFGS-B',
                       options={'maxiter':40, 'ftol':1e-11, 'gtol':1e-6})
        coef = base+transform@res.x
        trained = dict(model, coef=coef.tolist(), intercept=float(y.mean()-xmean@coef))
        scored[arm] = predict(outer_rows[COLS], trained)
        models[arm] = trained
        audits.append(dict(quarter=quarter, arm=arm, rows=len(fit), dates=len(size),
                           latest_maturity=fit.h10_mature.max(), first_signal=outer_rows.signal_date.min(),
                           magnitude_cap=cap, graded_scale=gs, magnitude_scale=ms, iterations=res.nit,
                           status=res.message, gradient_inf=max(abs(res.jac)), loss_change=res.fun-objective(initial)[0]))
    check = scored.merge(FROZEN, on=KEY, validate='1:1')
    assert len(check)==len(scored)
    np.testing.assert_allclose(check.baseline, check[BASE], atol=1e-10, rtol=0)
    (OUT/'models'/f'{quarter}.json').write_text(json.dumps(models))
    print(quarter, max(a['iterations'] for a in audits), flush=True)
    return scored, audits


if __name__ == '__main__':
    (OUT/'models').mkdir(parents=True, exist_ok=True)
    DATA = prepare()
    OUTER = outer()
    FROZEN = pd.read_parquet(OLD/'local_cache/predictions.parquet', columns=KEY+[BASE])
    REF = pd.read_csv(OLD/'outputs/folds.csv').query('model==@BASE').set_index('fold')
    quarters = sorted(OUTER.signal_date.dt.to_period('Q').astype(str).unique())
    with ProcessPoolExecutor(6, mp_context=multiprocessing.get_context('fork')) as pool:
        fits = list(pool.map(fit_quarter, quarters))
    pd.concat([s for s,_ in fits]).sort_values(KEY).to_parquet(OUT/'scores.parquet', index=False)
    pd.DataFrame([a for _, rows in fits for a in rows]).to_csv(OUT/'folds.csv', index=False)

"""EP25 finite distributions and month-clustered inference. No EP24 writes."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.neighbors import NearestNeighbors

EP = Path(__file__).resolve().parents[1]
TOPIC = EP.parents[2]
CONFIG = json.loads((EP / 'config.json').read_text())
OLD = EP.parent / CONFIG['source_episode']
OUT = EP / 'outputs'
CACHE = OUT / 'local_cache'
GRID = (np.arange(CONFIG['atoms']) + .5) / CONFIG['atoms']
QS = [.05, .10, .50, .90, .95]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str, allow_nan=False) + '\n')


def load_panel():
    p = pd.read_parquet(OLD / CONFIG['panel'])
    assert not p.duplicated(['date', 'instrument']).any()
    return p.dropna(subset=CONFIG['eligibility_features']).copy()


def train_test(panel, cutoff, h, period=None):
    train = panel[(panel.date < cutoff) & (panel[f'end_{h}'] < cutoff) & panel[f'y_{h}'].notna()].copy()
    test = panel[panel.date.dt.to_period('Q') == period].copy() if period is not None else panel[panel.date == cutoff].copy()
    if len(train):
        assert train[f'end_{h}'].max() < cutoff
        assert train.date.max() < cutoff
    return train, test.reset_index(drop=True)


def month_weights(train):
    w = 1 / train.groupby('date').date.transform('size').to_numpy(float)
    return w / w.mean()


def features(name):
    return CONFIG['risk_features'] + [c for g in CONFIG['candidates'][name] for c in CONFIG[g + '_features']]


def fit_model(train, h, name):
    model = CatBoostRegressor(loss_function='MultiQuantile:alpha=' + ','.join(map(str, CONFIG['alphas'])), **CONFIG['catboost'])
    model.fit(train[features(name)], train[f'y_{h}'], sample_weight=month_weights(train))
    return model


def predict_atoms(model, frame, name):
    raw = model.predict(frame[features(name)])
    atoms = np.maximum(np.stack([np.interp(GRID, CONFIG['alphas'], q) for q in np.sort(raw, axis=1)]), -1.)
    return atoms, float((np.diff(raw, axis=1) < 0).any(axis=1).mean())


def baselines(train, test, h):
    y = train[f'y_{h}'].to_numpy()
    global_q = np.quantile(y, GRID)
    cols = CONFIG['risk_features']
    median = train[cols].median().fillna(0)
    scale = (train[cols].quantile(.75) - train[cols].quantile(.25)).replace(0, 1).fillna(1)
    x = ((train[cols].fillna(median) - median) / scale).clip(-5, 5)
    z = ((test[cols].fillna(median) - median) / scale).clip(-5, 5)
    idx = NearestNeighbors(n_neighbors=min(1000, len(train)), n_jobs=2).fit(x).kneighbors(z, return_distance=False)
    return {'B0': np.tile(global_q, (len(test), 1)), 'B1': .75 * np.quantile(y[idx], GRID, axis=1).T + .25 * global_q}


def crps(atoms, actual):
    s = np.sort(np.asarray(atoms, float), axis=1)
    y = np.asarray(actual, float)
    n = s.shape[1]
    return np.abs(s - y[:, None]).mean(axis=1) - (s * (2*np.arange(1, n+1)-n-1)).sum(axis=1)/n**2


def score(atoms, actual):
    s, y = np.sort(np.asarray(atoms), axis=1), np.asarray(actual, float)
    q = np.quantile(s, QS, axis=1).T
    p, tail = (s > 0).mean(axis=1), (s < CONFIG['tail_threshold']).mean(axis=1)
    up, loss = (y > 0).astype(float), (y < CONFIG['tail_threshold']).astype(float)
    result = dict(crps=crps(s,y), mean=s.mean(axis=1), p_up=p, p_tail=tail,
        brier=(p-up)**2, tail_brier=(tail-loss)**2, tail_error=tail-loss,
        tail_absolute_error=np.abs(tail-loss), observed_up=up, observed_tail=loss,
        direction=((p > .5) == (y > 0)).astype(float),
        pit=((s < y[:,None]).mean(axis=1)+(s <= y[:,None]).mean(axis=1))/2,
        coverage90=((y >= q[:,0]) & (y <= q[:,-1])).astype(float))
    for j, a in enumerate(QS):
        result[f'q{int(a*100):02}'] = q[:, j]
        result[f'cover{int(a*100):02}'] = (y <= q[:,j]).astype(float)
    # Mean-centered relative CRPS is an ex post mechanism diagnostic only.
    if np.isfinite(y).any():
        obs = np.isfinite(y)
        centered = s[obs] - s[obs].mean()
        relative = np.full(len(y), np.nan)
        relative[obs] = crps(centered, y[obs] - y[obs].mean())
        result['relative_crps'] = relative
    else:
        result['relative_crps'] = np.full(len(y), np.nan)
    metrics = ['crps','brier','tail_brier','tail_error','tail_absolute_error','observed_up','observed_tail','direction','pit','coverage90'] + [f'cover{int(a*100):02}' for a in QS]
    for c in metrics:
        result[c][~np.isfinite(y)] = np.nan
    return pd.DataFrame(result)


def cohort_distance(atoms, actual):
    """Integral squared CDF distance from mixture prediction to realized cohort CDF."""
    y = np.sort(np.asarray(actual, float))
    y = y[np.isfinite(y)]
    s = np.sort(np.asarray(atoms).reshape(-1))
    n = len(s)
    prefix = np.r_[0., np.cumsum(s)]
    k = np.searchsorted(s, y, side='right')
    cross = (y*k-prefix[k]+prefix[-1]-prefix[k]-y*(n-k))/n
    pred_half_distance = np.dot(s, 2*np.arange(1,n+1)-n-1)/n**2
    obs_half_distance = np.dot(y, 2*np.arange(1,len(y)+1)-len(y)-1)/len(y)**2
    return float(cross.mean() - pred_half_distance - obs_half_distance)


def bootstrap_means(values, block, reps=None, seed=None):
    v = np.asarray(values, float)
    assert len(v) and np.isfinite(v).all()
    rng = np.random.default_rng(CONFIG['bootstrap']['seed'] if seed is None else seed)
    r = CONFIG['bootstrap']['replicates'] if reps is None else reps
    idx = rng.integers(len(v), size=r)
    sums = v[idx].copy()
    for _ in range(1, len(v)):
        restart = rng.random(r) < 1 / block
        idx = np.where(restart, rng.integers(len(v), size=r), (idx + 1) % len(v))
        sums += v[idx]
    return sums / len(v)


def interval(values, h, block=None):
    v = np.asarray(values, float)
    block = max(6,h) if block is None else block
    draws = bootstrap_means(v, block)
    lo, hi = np.quantile(draws, [.025,.975])
    slo, shi = np.quantile(draws, [.00625,.99375])
    return dict(delta=float(v.mean()), low95=float(lo), high95=float(hi), low_family=float(slo), high_family=float(shi),
        months=len(v), mean_block=block, approximate_blocks=len(v)/block,
        detectable_80pct_effect_approx=float((1.96+.84)*draws.std(ddof=1)))


def paired(left, right, metric, keys=('date',)):
    a = left[list(keys)+[metric]].merge(right[list(keys)+[metric]], on=list(keys), suffixes=('_a','_b'), validate='one_to_one', how='outer', indicator=True)
    assert a._merge.eq('both').all(), 'paired keys differ'
    return a.sort_values(list(keys))[metric+'_a'].to_numpy()-a.sort_values(list(keys))[metric+'_b'].to_numpy()

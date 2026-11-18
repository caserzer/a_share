"""Original EP36 input transform; simple linear differentiable Spearman model."""
import numpy as np
import pandas as pd
import torch
from scipy.stats import rankdata
from sklearn.linear_model import Ridge


class Transform:
    def fit(self, frame):
        a = frame.to_numpy(float)
        self.median = np.nan_to_num(np.nanmedian(a, axis=0), nan=0.)
        a = np.where(np.isnan(a), self.median, a)
        self.mean = a.mean(axis=0)
        self.sd = a.std(axis=0)
        self.sd[self.sd < 1e-12] = 1.
        return self

    def transform(self, frame):
        a = frame.to_numpy(float)
        return (np.where(np.isnan(a), self.median, a) - self.mean) / self.sd

    def record(self):
        return {k: getattr(self, k).tolist() for k in ['median', 'mean', 'sd']}


def ridge(frame, columns, target='target_z'):
    t = Transform().fit(frame[columns])
    m = Ridge(alpha=10.).fit(t.transform(frame[columns]), frame[target].to_numpy(float))
    return dict(columns=columns, **t.record(), coef=m.coef_.tolist(), intercept=float(m.intercept_))


def predict(frame, m):
    assert not {'h10', 'target_z', 'target_rank'}.intersection(frame.columns), 'Labels passed to prediction'
    a = frame[m['columns']].to_numpy(float)
    x = (np.where(np.isnan(a), m['median'], a) - m['mean']) / m['sd']
    return x @ np.asarray(m['coef']) + m['intercept']


def date_rankic(frame, scores):
    values = []
    for indices in frame.groupby('signal_date', sort=True).indices.values():
        a = np.asarray(scores)[indices]; b = frame.h10.to_numpy()[indices]
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() < 3 or np.std(a[ok]) < 1e-12 or np.std(b[ok]) < 1e-12:
            values.append(np.nan)
        else:
            values.append(np.corrcoef(rankdata(a[ok]), rankdata(b[ok]))[0, 1])
    return np.array(values)


def soft_rankic(scores, targets, mask, temperature=.1):
    """Padded rows never enter ranks, moments or targets; average date equally."""
    count = mask.sum(1, keepdim=True)
    centered = (scores - (scores * mask).sum(1, keepdim=True) / count) * mask
    sd = torch.sqrt((centered.square().sum(1, keepdim=True) / count).clamp_min(1e-24))
    z = centered / sd
    ranks = (torch.sigmoid((z[:, :, None] - z[:, None, :]) / temperature) * mask[:, None, :]).sum(2)
    ranks = (ranks - (ranks * mask).sum(1, keepdim=True) / count) * mask
    y = (targets - (targets * mask).sum(1, keepdim=True) / count) * mask
    denom = torch.linalg.vector_norm(ranks, dim=1) * torch.linalg.vector_norm(y, dim=1)
    return (ranks * y).sum(1) / denom.clamp_min(1e-24)


def packed(frame, m):
    a = frame[m['columns']].to_numpy(float)
    x = (np.where(np.isnan(a), m['median'], a) - m['mean']) / m['sd']
    groups = list(frame.groupby('signal_date', sort=True).indices.values())
    n = max(map(len, groups)); d = len(groups)
    xp = np.zeros((d, n, x.shape[1])); yp = np.zeros((d, n)); mask = np.zeros((d, n))
    for i, ix in enumerate(groups):
        xp[i, :len(ix)] = x[ix]
        yp[i, :len(ix)] = rankdata(frame.h10.to_numpy()[ix])
        mask[i, :len(ix)] = 1.
    return tuple(torch.tensor(a, dtype=torch.float64) for a in [xp, yp, mask])


def train_rankic(frame, columns, cfg, steps=None, validation=None):
    torch.set_num_threads(cfg['torch_threads'])
    torch.manual_seed(cfg['seed'])
    initial = ridge(frame, columns)
    xp, yp, mask = packed(frame, initial)
    w0 = np.array(initial['coef']); w0 /= np.linalg.norm(w0)
    w = torch.nn.Parameter(torch.tensor(w0, dtype=torch.float64))
    opt = torch.optim.Adam([w], lr=cfg['lr'])
    rng = np.random.default_rng(cfg['seed']); order = np.array([], dtype=int); cursor = 0
    max_steps = cfg['max_steps'] if steps is None else steps
    checkpoints = set([0, *cfg['selection_steps']]) if validation is not None else {max_steps}
    results = []; models = {}
    def snapshot(step, batch_ic=None):
        m = {**initial, 'coef': w.detach().numpy().tolist(), 'intercept': 0., 'trained_steps': step}
        row = dict(step=step, last_batch_soft_rankic=batch_ic)
        if validation is not None:
            s = predict(validation.drop(columns=['h10', 'target_z', 'target_rank']), m)
            ic = date_rankic(validation, s)
            assert np.isfinite(ic).all(), 'Validation dates differ across candidate checkpoints'
            row.update(validation_mean_rankic=float(ic.mean()), validation_dates=len(ic))
        results.append(row); models[step] = m
    if 0 in checkpoints: snapshot(0)
    for step in range(1, max_steps + 1):
        if cursor >= len(order): order = rng.permutation(len(xp)); cursor = 0
        ix = order[cursor:cursor + cfg['batch_dates']]; cursor += len(ix)
        opt.zero_grad()
        ic = soft_rankic(xp[ix] @ w, yp[ix], mask[ix], cfg['temperature'])
        loss = -ic.mean(); assert torch.isfinite(loss)
        loss.backward(); assert torch.isfinite(w.grad).all()
        opt.step()
        with torch.no_grad(): w.div_(torch.linalg.vector_norm(w))
        if step in checkpoints: snapshot(step, float(ic.mean().detach()))
    if validation is not None:
        best = max((r for r in results if r['step'] in cfg['selection_steps']),
                   key=lambda r: (r['validation_mean_rankic'], -r['step']))['step']
    else: best = max_steps
    return models[best], results, best

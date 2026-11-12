"""Offline label proposals; future-dependent and forbidden as online features."""
import numpy as np
import pandas as pd


def candidate_metrics(prices):
    p = np.asarray(prices, dtype=float)
    if len(p) < 121:
        return pd.DataFrame()
    w = np.lib.stride_tricks.sliding_window_view(p, 121)
    idx = np.arange(60, len(p)-60)
    ok = np.isfinite(w).all(axis=1) & (w > 0).all(axis=1)
    w, idx = w[ok], idx[ok]
    if not len(idx):
        return pd.DataFrame()
    base = w[:, 60]
    f = w[:, 61:]/base[:, None]-1
    pre60 = base/w[:, 0]-1
    pre20 = base/w[:, 40]-1
    weak = (pre60 <= 0) | (base/w[:, :61].max(axis=1)-1 <= -.10)
    gain20 = f[:, 19]
    kind = np.where(weak, 'WARMING', np.where(gain20-pre20 >= .03, 'HEATING', 'ORDINARY_CONTINUATION'))
    dd = (w[:, 60:]/np.maximum.accumulate(w[:, 60:], axis=1)-1).min(axis=1)
    amp = f[:, :20].max(axis=1) >= .08
    persist = (f[:, 59] >= .05) & ((f >= .02).sum(axis=1) >= 40) & (f.min(axis=1) >= -.05) & (dd >= -.12)
    valid = amp & persist & (kind != 'ORDINARY_CONTINUATION')
    return pd.DataFrame(dict(position=idx, kind=kind, valid=valid, amplitude=amp, persistence=persist,
                             pre60=pre60, pre20=pre20, gain20=gain20, gain60=f[:, 59],
                             gain20_max=f[:, :20].max(axis=1), retained_days=(f >= .02).sum(axis=1),
                             worst_from_start=f.min(axis=1), max_drawdown=dd))


def segment(prices, candidates, boundary_reason='RIGHT_CENSORED'):
    """Operate on one complete positive, consecutive price block only."""
    p = np.asarray(prices, dtype=float)
    if not np.isfinite(p).all() or not (p > 0).all():
        raise ValueError('segment requires a complete positive price block')
    rows = {int(r.position): r for r in candidates.itertuples() if r.valid}
    phases, assignments = [], []
    active = None
    parent = -1
    peak = None
    high_day = None
    for i, price in enumerate(p):
        if active is not None:
            if price > peak:
                peak, high_day = price, i
            reason = 'DRAWDOWN8' if price/peak-1 <= -.08 else ('PAUSE20' if i-high_day >= 20 else None)
            if reason:
                active.update(end=i, end_reason=reason, right_censored=False)
                active = None
                if i in rows:
                    assignments.append(dict(position=i, phase=None, disposition='RESET_DAY_EXCLUDED'))
                continue
        if i not in rows:
            continue
        r = rows[i]
        if active is None:
            parent += 1
            peak, high_day = price, i
            active = dict(phase=len(phases), parent=parent, start=i, end=None, kind=r.kind,
                          reference_gain20=r.gain20, end_reason=None, right_censored=None)
            phases.append(active)
            disposition = 'NEW_PARENT'
        elif r.kind == 'HEATING' and i-active['start'] >= 20 and r.gain20-active['reference_gain20'] >= .03:
            active.update(end=i-1, end_reason='NEW_HEATING_PHASE', right_censored=False)
            active = dict(phase=len(phases), parent=parent, start=i, end=None, kind=r.kind,
                          reference_gain20=r.gain20, end_reason=None, right_censored=None)
            phases.append(active)
            disposition = 'NEW_HEATING_PHASE'
        else:
            disposition = 'SAME_PHASE'
        assignments.append(dict(position=i, phase=active['phase'], disposition=disposition))
    if active is not None:
        active.update(end=len(p)-1, end_reason=boundary_reason, right_censored=True)
    return pd.DataFrame(phases), pd.DataFrame(assignments)

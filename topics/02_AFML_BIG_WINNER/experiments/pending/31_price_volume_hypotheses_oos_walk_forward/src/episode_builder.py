"""Episode cooling uses only the past selected event, measured in market days."""
import numpy as np
import pandas as pd


def cooling_mask(trigger, cooling=20):
    trigger = np.asarray(trigger, dtype=bool)
    keep = np.zeros(len(trigger), dtype=bool)
    last = -cooling
    for j in np.flatnonzero(trigger):
        if j - last >= cooling:
            keep[j] = True
            last = j
    return keep


def observation_masks(features, eligible):
    d = pd.DatetimeIndex(features.date)
    # Market calendar ends early on holidays, so select last actually recorded day.
    periods = d.to_period("W-FRI")
    weekly = pd.Series(d, index=d).groupby(periods).transform("max").to_numpy() == d.to_numpy()
    weekly &= periods.end_time.normalize() <= d[-1]
    h10 = eligible & features.observed & features.warmup & features.relative_turnover.gt(1)
    h11 = eligible & features.observed & features.breakout
    return dict(weekly=weekly & eligible, h10_event=np.asarray(h10), h11_event=np.asarray(h11),
                h10_episode=cooling_mask(h10), h11_episode=cooling_mask(h11))

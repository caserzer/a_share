"""Natural low-to-high swings. Duration bounds never affect turning points."""
import numpy as np


def upswings(prices, threshold):
    p = np.asarray(prices, dtype=float)
    if len(p) < 2:
        return []
    if not np.isfinite(p).all() or not (p > 0).all() or not 0 < threshold < 1:
        raise ValueError('requires one finite positive-price block and a valid threshold')
    direction = 0
    low = high = 0
    start = confirmed_start = None
    left = True
    rows = []
    for i in range(1, len(p)):
        if direction == 0:
            if p[i] < p[low]:
                low = i
            if p[i] > p[high]:
                high = i
            if p[i] / p[low] - 1 >= threshold - 1e-12:
                direction = 1
                start, confirmed_start, high, left = low, i, i, True
            elif 1 - p[i] / p[high] >= threshold - 1e-12:
                direction, low = -1, i
        elif direction == -1:
            if p[i] < p[low]:
                low = i
            if p[i] / p[low] - 1 >= threshold - 1e-12:
                direction = 1
                start, confirmed_start, high, left = low, i, i, False
        else:
            # Equal highs retain the earliest peak; no duration extension by ties.
            if p[i] > p[high]:
                high = i
            if 1 - p[i] / p[high] >= threshold - 1e-12:
                rows.append(dict(start_i=start, peak_i=high, evaluation_i=high,
                    start_confirm_i=confirmed_start, end_confirm_i=i,
                    status='CONFIRMED', left_censored=left, right_censored=False))
                direction, low = -1, i
    if direction == 1:
        rows.append(dict(start_i=start, peak_i=high, evaluation_i=len(p) - 1,
            start_confirm_i=confirmed_start, end_confirm_i=None,
            status='OPEN', left_censored=left, right_censored=True))
    return rows


def duration_class(months):
    if months < 6:
        return 'SHORT_LT6'
    if months <= 18:
        return 'IN_RANGE_6_18'
    return 'LONG_GT18'

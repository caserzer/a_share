"""Audit evidence ownership. Does not choose origins, identities or signals."""
import numpy as np


def assess(prices_from_origin, phase_end, end_reason, left_origin_uncertain=False):
    prices = np.asarray(prices_from_origin, dtype=float)
    used_end = min(int(phase_end), 60)
    if used_end < 0:
        raise ValueError('negative endpoint')
    v = prices[:used_end+1]
    if len(v) != used_end+1 or not np.isfinite(v).all() or not (v > 0).all():
        return dict(status='UNKNOWN_CENSORED', evidence_end=used_end,
                    left_origin_uncertain=bool(left_origin_uncertain), missing_path=True)
    future=v[1:]/v[0]-1
    dd=float(np.min(v/np.maximum.accumulate(v)-1))
    amplitude=float(np.max(future[:20])) if len(future) else None
    retained=int(np.sum(future>=.02))
    terminal=float(v[-1]/v[0]-1)
    worst=float(np.min(future)) if len(future) else None
    if used_end<60:
        if end_reason in ['DRAWDOWN8','PAUSE20']:
            status='OBSERVED_END_BEFORE_CONFIRMATION'
        elif end_reason=='NEW_HEATING_PHASE':
            status='SUPERSEDED_BEFORE_CONFIRMATION'
        elif end_reason in ['RIGHT_CENSORED','CLASSIFICATION_BOUNDARY','INTERNAL_PRICE_BREAK']:
            status='UNKNOWN_CENSORED'
        else:
            raise ValueError('unrecognized early endpoint')
    else:
        valid=amplitude>=.08 and terminal>=.05 and retained>=40 and worst>=-.05 and dd>=-.12
        status='WITHIN_PHASE_CONFIRMED' if valid else 'WITHIN_PHASE_FAILED'
    return dict(status=status,evidence_end=used_end,left_origin_uncertain=bool(left_origin_uncertain),
                missing_path=False,amplitude_within_evidence=amplitude,retained_days_within_evidence=retained,
                return_at_evidence_end=terminal,worst_from_origin=worst,max_drawdown=dd)

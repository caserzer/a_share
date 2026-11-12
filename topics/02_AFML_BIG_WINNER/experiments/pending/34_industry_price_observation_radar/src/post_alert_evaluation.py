"""Registered post-alert evidence and maturity; never a signal generator."""
import json
from pathlib import Path
import numpy as np


def registered_rules():
    root=Path(__file__).resolve().parents[1]
    return json.loads((root/'configs/evaluation_registration.json').read_text())['researcher_registered_not_user_confirmed']


def post_alert_result(day_indices, prices, blocks, alert_day, asof_day, *, process_end=None,
                      process_end_observed=False, rules=None):
    c=registered_rules() if rules is None else rules
    if asof_day-alert_day<c['uniform_alert_label_delay_sessions']:
        return dict(status='IMMATURE',post_valid=None)
    horizon=c['post_alert_horizon'];end=alert_day+horizon
    observed_early_end=process_end is not None and process_end<end and process_end_observed
    # A witnessed breach needs evidence through its breach day, not prices after that failure.
    if observed_early_end:end=max(alert_day,int(process_end)+1)
    take=(np.asarray(day_indices)>=alert_day)&(np.asarray(day_indices)<=end)
    days=np.asarray(day_indices)[take];v=np.asarray(prices,dtype=float)[take];b=np.asarray(blocks,dtype=float)[take]
    if len(days)!=end-alert_day+1 or not np.array_equal(days,np.arange(alert_day,end+1)):
        return dict(status='UNKNOWN_MISSING_DATES',post_valid=None)
    if not np.isfinite(v).all() or not (v>0).all() or not np.isfinite(b).all() or not (b==b[0]).all():
        return dict(status='UNKNOWN_PRICE_PATH',post_valid=None)
    if observed_early_end:
        return dict(status='PROCESS_ENDED',post_valid=False)
    if process_end is not None and process_end<end:
        return dict(status='PROCESS_ENDED' if process_end_observed else 'UNKNOWN_PROCESS_CENSORED',
                    post_valid=False if process_end_observed else None)
    f=v[1:]/v[0]-1
    metrics=dict(peak_return=float(f[:c['post_alert_peak_horizon']].max()),terminal_return=float(f[-1]),
                 retained_days=int((f>=c['post_alert_retained_min_return']).sum()),
                 floor_return=float(f.min()),max_drawdown=float((v/np.maximum.accumulate(v)-1).min()))
    conditions=dict(peak=metrics['peak_return']>=c['post_alert_peak_min_return'],
                    terminal=metrics['terminal_return']>=c['post_alert_terminal_min_return'],
                    retained=metrics['retained_days']>=c['post_alert_retained_min_days'],
                    floor=metrics['floor_return']>=c['post_alert_floor_return'],
                    drawdown=metrics['max_drawdown']>=-c['post_alert_max_drawdown'])
    valid=all(conditions.values())
    return dict(status='POST_VALID' if valid else 'POST_FAILED',post_valid=valid,**metrics,
                failed_conditions=[k for k,v in conditions.items() if not v])


def label_neighborhood_known(day_indices,prices,blocks,alert_day,asof_day):
    """All origins that could match a timely alert must have evaluable paths."""
    c=registered_rules();before,after=c['timely_window_trading_days']
    if asof_day-alert_day<c['uniform_alert_label_delay_sessions']:return False
    # origin in [alert-after, alert-before], with 60-session prior/forward support.
    lo=alert_day-after-60;hi=alert_day-before+60
    t=np.asarray(day_indices);take=(t>=lo)&(t<=hi)
    v=np.asarray(prices,dtype=float)[take];b=np.asarray(blocks,dtype=float)[take]
    return bool(np.array_equal(t[take],np.arange(lo,hi+1)) and np.isfinite(v).all() and (v>0).all()
                and np.isfinite(b).all() and len(b)>0 and (b==b[0]).all())


def process_recall_mature(origin,asof_day):
    return asof_day-origin>=registered_rules()['uniform_process_recall_delay_sessions']

"""Fixed-prior individual event rates; no flexible single-stock ML."""
from scipy.stats import beta
from common import *


def local_probability(history,p_global,weak=False):
    if history is None or not len(history):return dict(probability=float(p_global),lower=0.,upper=1.,reason='no_history_global_fallback')
    n=len(history)/C['overlap_discount'];events=history.event.sum()/C['overlap_discount']
    a=C['local']['weak_alpha'] if weak else C['local']['prior_alpha']
    b=C['local']['weak_beta'] if weak else C['local']['prior_beta']
    lo,hi=beta.ppf([.025,.975],a+events,b+n-events)
    return dict(probability=float((a+events)/(a+b+n)),lower=float(lo),upper=float(hi),reason='weak_Jeffreys_diagnostic' if weak else 'fixed_Beta_1_4')

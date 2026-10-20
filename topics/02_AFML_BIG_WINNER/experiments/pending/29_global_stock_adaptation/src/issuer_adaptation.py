"""Bounded issuer offsets and training-only temporal-covariance shrinkage."""
from common import *


def offset_map(offset,y,w,sd,cap=1.):
    offset=np.asarray(offset,float);y=np.asarray(y,float);w=np.asarray(w,float)
    assert len(y)==len(offset)==len(w) and np.isfinite(offset).all() and np.isfinite(y).all() and (w>0).all()
    if sd<=0:return dict(estimate=0.,sd=np.nan,information=0.,shrinkage=0.,iterations=0)
    precision=1/(sd*sd);b=0.
    for iteration in range(30):
        q=expit(offset+b);score=np.sum(w*(y-q))-precision*b;info=np.sum(w*q*(1-q))
        new=float(np.clip(b+score/(info+precision),-cap,cap))
        if abs(new-b)<1e-10:b=new;break
        b=new
    q=expit(offset+b);info=float(np.sum(w*q*(1-q)))
    return dict(estimate=b,sd=float(1/np.sqrt(info+precision)),information=info,shrinkage=info/(info+precision),iterations=iteration+1)


def common_offsets(history,column):
    result=pd.Series(index=history.index,dtype=float)
    for date,g in history.groupby('date',sort=True):
        # Nuisance intercept estimated only from already mature OOS errors.
        z=logodds(g[column]);y=g.event.to_numpy();a=0.
        for _ in range(30):
            p=expit(z+a);new=float(np.clip(a+np.sum(y-p)/max(np.sum(p*(1-p)),1e-10),-8,8))
            if abs(a-new)<1e-10:a=new;break
            a=new
        result.loc[g.index]=z+a
    return result


def nonoverlap_count(g,event=None):
    if not len(g):return 0
    z=g if event is None else g[g.event.eq(event)]
    last=pd.Timestamp.min;count=0
    for row in z.sort_values(['label_end','date']).itertuples():
        if row.date>last:count+=1;last=row.label_end
    return count


def merged_event_stages(g):
    z=g[g.event.eq(1)].sort_values('date');end=pd.Timestamp.min;stages=0
    for row in z.itertuples():
        if row.date>end:stages+=1
        end=max(end,row.label_end)
    return stages


def temporal_scores(g,offset_col):
    if g.date.nunique()<C['individual']['tau_minimum_months']:return None
    first=g.date.min();last=g.date.max();span=(last.to_period('M')-first.to_period('M')).n+1
    first_end=first+pd.DateOffset(months=span//3);last_start=last-pd.DateOffset(months=span//3)
    a=g[g.date<first_end];b=g[g.date>last_start]
    if len(a)<4 or len(b)<4 or a.label_end.max()>=b.date.min():return None
    values=[]
    for z in [a,b]:
        q=expit(z[offset_col]);info=float(np.sum(q*(1-q)))
        if info<.1:return None
        values.append(float(np.clip(np.sum(z.event-q)/info,-C['individual']['tau_score_cap'],C['individual']['tau_score_cap'])))
    return tuple(values)


def estimate_tau(histories,offset_col):
    pairs=[temporal_scores(g,offset_col) for g in histories.values()]
    pairs=np.array([x for x in pairs if x is not None])
    if len(pairs)<C['individual']['tau_minimum_issuers']:return dict(tau=0.,issuers=len(pairs),covariance=None,reason='too_few_training_issuers')
    covariance=float(np.cov(pairs.T,ddof=1)[0,1]);tau=float(np.sqrt(np.clip(covariance,0,C['individual']['tau_sd_maximum']**2)))
    return dict(tau=tau,issuers=len(pairs),covariance=covariance,reason='positive_part_temporal_covariance')


def issuer_fit(g,offset_col,tau):
    if g is None or not len(g):
        return dict(b=0.,posterior_sd=np.nan,shrinkage=0.,reason='no_mature_history',months=0,events=0,effective_months=0.,nonoverlap_labels=0,nonoverlap_events=0,nonoverlap_nonevents=0,event_stages=0,temporal_first=np.nan,temporal_last=np.nan)
    stats=dict(months=g.date.nunique(),events=int(g.event.sum()),effective_months=len(g)/C['overlap_discount'],
        nonoverlap_labels=nonoverlap_count(g),nonoverlap_events=nonoverlap_count(g,1),nonoverlap_nonevents=nonoverlap_count(g,0),event_stages=merged_event_stages(g))
    scores=temporal_scores(g,offset_col);stats.update(temporal_first=scores[0] if scores else np.nan,temporal_last=scores[1] if scores else np.nan)
    reason='adapted'
    if stats['months']<C['individual']['minimum_months']:reason='short_history'
    elif stats['nonoverlap_events']<C['individual']['minimum_nonoverlap_events']:reason='few_independent_event_windows'
    elif stats['nonoverlap_nonevents']<C['individual']['minimum_nonoverlap_nonevents']:reason='few_non_event_windows'
    elif scores is None or scores[0]*scores[1]<=0:reason='unstable_or_unavailable_temporal_direction'
    elif tau<=0:reason='zero_persistent_variance_in_training'
    if reason!='adapted':return dict(b=0.,posterior_sd=np.nan,shrinkage=0.,reason=reason,**stats)
    result=offset_map(g[offset_col],g.event,np.full(len(g),1/C['overlap_discount']),tau,C['individual']['maximum_logit_shift'])
    return dict(b=result['estimate'],posterior_sd=result['sd'],shrinkage=result['shrinkage'],reason=reason,**stats)

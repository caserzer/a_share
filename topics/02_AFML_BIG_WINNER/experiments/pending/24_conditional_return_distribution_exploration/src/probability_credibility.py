"""Dated probability evidence; lack of detected error is not proof of calibration."""
import numpy as np
import pandas as pd
from run_four_horizons import DEST, BINS, BIN_NAMES


def event_outcome(actual,event):
    if event=='up':return (actual>0).astype(float)
    if event=='down':return (actual<0).astype(float)
    if event=='zero':return (actual==0).astype(float)
    return (np.searchsorted(BINS,actual,side='right')==BIN_NAMES.index(event)).astype(float)


def event_evidence(data,event,probability,horizon,asof):
    g=data[(data.label_end<pd.Timestamp(asof)) & (data.date<pd.Timestamp(asof))].copy()
    col=f'p_{event}'
    bucket=min(9,int(np.floor(probability*10)))
    g=g[np.floor(g[col]*10).clip(upper=9)==bucket]
    valid=g.actual.notna()
    scored=g[valid].copy()
    counts=dict(mature_rows=len(g),observed_rows=len(scored),missing_outcomes=int((~valid).sum()),prediction_months=scored.date.nunique())
    result=dict(event=event,predicted_probability=float(probability),probability_bin=[bucket/10,(bucket+1)/10],**counts)
    if not len(scored):return dict(**result,status='insufficient_evidence')
    observed=event_outcome(scored.actual.to_numpy(),event)
    scored['observed']=observed
    permonth=scored.groupby('date').agg(n=(col,'size'),p=(col,'sum'),o=('observed','sum'))
    # Keep absent-bin months in the calendar so time blocks do not bridge long gaps.
    allmonths=pd.date_range(data.date.min().to_period('M').start_time,pd.Timestamp(asof),freq='MS')
    permonth.index=permonth.index.to_period('M').to_timestamp()
    permonth=permonth.reindex(allmonths,fill_value=0)
    block=max(6,horizon); n=len(permonth)
    rng=np.random.default_rng(24)
    starts=rng.integers(0,n,size=(2000,int(np.ceil(n/block))))
    idx=((starts[:,:,None]+np.arange(block))%n).reshape(2000,-1)[:,:n]
    den=permonth.n.to_numpy()[idx].sum(axis=1)
    dif=(permonth.o-permonth.p).to_numpy()[idx].sum(axis=1)
    ok=den>0
    lo,hi=np.quantile(dif[ok]/den[ok],[.025,.975])
    result.update(historical_predicted=float(scored[col].mean()),historical_observed=float(observed.mean()),
        gap95=[float(lo),float(hi)],block_months=block,
        missing_outcome_frequency_bounds=[float(observed.sum()/len(g)),float((observed.sum()+(~valid).sum())/len(g))])
    enough=len(scored)>=200 and scored.date.nunique()>=max(12,2*horizon)
    result['status']='insufficient_evidence' if not enough else ('miscalibrated' if lo>0 or hi<0 else 'not_rejected_not_proven')
    return result


def assess(model,horizon,probabilities,asof):
    allrows=pd.read_parquet(DEST/f'predictions_{horizon}m.parquet')
    data=allrows[allrows.model==model].copy()
    events=['up','down','zero',*BIN_NAMES]
    evidence=[event_evidence(data,e,probabilities[f'p_{e}'],horizon,asof) for e in events]
    mature=allrows[(allrows.label_end<pd.Timestamp(asof))&allrows.actual.notna()]
    monthly=mature.groupby(['date','model'])[['brier','multiclass_brier','crps']].mean()
    differences={}
    for metric in ['brier','multiclass_brier','crps']:
        wide=monthly[metric].unstack('model')
        delta=(wide[model]-wide.expanding_empirical).dropna().to_numpy()
        block=max(6,horizon);rng=np.random.default_rng(24);n=len(delta)
        starts=rng.integers(0,n,size=(2000,int(np.ceil(n/block))))
        idx=((starts[:,:,None]+np.arange(block))%n).reshape(2000,-1)[:,:n]
        lo,hi=np.quantile(delta[idx].mean(axis=1),[.025,.975])
        differences[metric]=dict(mean_difference=float(delta.mean()),difference95=[float(lo),float(hi)],
            better_than_history_supported=bool(hi<0),months=n,block_months=block)
    return dict(status='not_established_as_trustworthy',events=evidence,baseline_comparison=differences,
        meaning='Population-bin retrospective evidence, not an individual-stock accuracy guarantee. Failing to reject calibration error does not prove correctness.',
        evidence_asof=str(pd.Timestamp(asof).date()),selection='only outcomes ending strictly before evidence_asof',
        limitations=['Exploratory multiple-model comparisons, not a new independent holdout',
                    'Historical universe selection bias and price-proxy labels remain',
                    'Insufficient coverage of a probability bin prevents a credibility claim'])

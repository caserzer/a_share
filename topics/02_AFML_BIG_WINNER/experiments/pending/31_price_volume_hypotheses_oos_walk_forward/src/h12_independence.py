"""Pre-specified H12 independence from H01/H02, on an identical eligible panel."""
import json
import pickle

import numpy as np
import pandas as pd

from baselines import HypothesisTransform, Ridge
from common import OUT, cache, config, sha, utc_now, write_json
from evaluate import quarter_complete, score_frame
from ep30_adapter import EP30Adapter
from hypothesis_tests import summarize
from walk_forward import cohort, load_features, load_outcomes, predict_pair, target_frame, training_mask


def main():
    features=cohort(load_features(),'H12')
    features=features.loc[features[['atr','mavd','trend_decay']].notna().all(axis=1)].copy()
    frame=target_frame(features,load_outcomes(20),'H12','adjusted_return')
    folds=json.loads((OUT/'manifests/H12_folds.json').read_text())['folds']
    root=cache()/'H12_independence';root.mkdir(exist_ok=True)
    receipts=[];corr=[]
    for r in folds:
        train=frame.loc[training_mask(frame,r['fit_cutoff'],r['scheme'])]
        test=features.loc[features.date.dt.to_period('Q').astype(str).eq(r['fold'])]
        t=HypothesisTransform().fit(train);a=t.apply(train,'H12');factor='trend_decay'
        controls=t.controls('H12')+['atr','mavd']
        model=dict(transform=t,controls=controls,factor=factor,
                   base=Ridge().fit(a[controls],a.y,a.date,r['alpha']),
                   augmented=Ridge().fit(a[controls+[factor]],a.y,a.date,r['alpha']),
                   factor_model=Ridge().fit(a[controls],a[factor],a.date,r['alpha']),
                   factor_scale=max(float(a[factor].std()),1e-12),sort_low=float(a[factor].quantile(.1)),sort_high=float(a[factor].quantile(.9)))
        p=predict_pair(model,test,'H12');p['scheme'],p['fold']=r['scheme'],r['fold']
        name=r['scheme']+'_'+r['fold'];pp=root/(name+'.parquet');mp=root/(name+'.pkl')
        if pp.exists():raise RuntimeError('frozen H12 sensitivity exists')
        p.to_parquet(pp,index=False);mp.write_bytes(pickle.dumps(model,protocol=5))
        c=a[['atr','mavd','trend_decay']].corr()
        corr.append(dict(scheme=r['scheme'],fold=r['fold'],train_rows=len(a),corr_H12_H01=float(c.loc['trend_decay','atr']),corr_H12_H02=float(c.loc['trend_decay','mavd']),corr_H01_H02=float(c.loc['atr','mavd'])))
        receipts.append(dict(scheme=r['scheme'],fold=r['fold'],fit_cutoff=r['fit_cutoff'],train_start=str(train.date.min()),train_end=str(train.date.max()),
                             max_maturity=str(train.mature_at.max()),alpha=r['alpha'],prediction_path=str(pp),sha256=sha(pp),model_path=str(mp),model_sha256=sha(mp),rows=len(p)))
    pd.DataFrame(corr).to_csv(OUT/'audits/H12_train_collinearity.csv',index=False)
    write_json(OUT/'manifests/H12_independence.json',dict(folds=receipts,frozen_at=utc_now(),comparison='controls+H01+H02 vs controls+H01+H02+H12',selection='primary_alpha_fixed_no_outer_selection',secondary_not_in_primary_FDR=True))


def evaluate():
    d=json.loads((OUT/'manifests/H12_independence.json').read_text());a=EP30Adapter();y=load_outcomes(20);pieces=[]
    for r in d['folds']:
        if sha(r['prediction_path'])!=r['sha256']:raise ValueError('H12 sensitivity changed')
        if quarter_complete(r['fold'],20,a.days):pieces.append(score_frame(pd.read_parquet(r['prediction_path']),y,'H12',config()['primary']['H12']))
    f=pd.concat(pieces,ignore_index=True);rows=[]
    for scheme,g in f.groupby('scheme'):
        r,_=summarize(g,config()['primary']['H12']);rows.append(dict(scheme=scheme,comparison='H12_after_H01_H02',**r))
    pd.DataFrame(rows).to_csv(OUT/'metrics/H12_after_H01_H02.csv',index=False)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--evaluate',action='store_true')
    evaluate() if p.parse_args().evaluate else main()

"""Preregistered H02 volume -> turnover reconstruction, using fixed primary alpha."""
import json
import pickle

import pandas as pd

from common import OUT, cache, config, sha, utc_now, write_json
from evaluate import quarter_complete, score_frame
from ep30_adapter import EP30Adapter
from hypothesis_tests import summarize
from walk_forward import cohort, fit_pair, load_features, load_outcomes, predict_pair, training_mask, append_lagged_features


def main():
    features = cohort(append_lagged_features(load_features()), "H02")
    # Keep the original factor's denominator, with alternate applicability explicit.
    features = features.loc[features.mavd.notna() & features.mavd_turnover.notna()].copy()
    features["mavd"] = features.mavd_turnover
    outcomes = load_outcomes(60)
    frame = features.merge(outcomes[['date','security_id','value','mature_at']], on=['date','security_id'], validate='one_to_one')
    frame['y'] = frame.value
    folds = json.loads((OUT/'manifests/H02_folds.json').read_text())['folds']
    root = cache()/'H02_turnover_sensitivity'
    root.mkdir(exist_ok=True)
    receipts=[]
    for r in folds:
        train = frame.loc[training_mask(frame, r['fit_cutoff'], r['scheme'])]
        test = features.loc[features.date.dt.to_period('Q').astype(str).eq(r['fold'])]
        model = fit_pair(train,'H02','mavd',r['alpha'])
        pred = predict_pair(model,test,'H02')
        pred['scheme'],pred['fold']=r['scheme'],r['fold']
        name=r['scheme']+'_'+r['fold']
        p=root/(name+'.parquet');mp=root/(name+'.pkl')
        if p.exists(): raise RuntimeError('immutable sensitivity fold exists')
        pred.to_parquet(p,index=False);mp.write_bytes(pickle.dumps(model,protocol=5))
        receipts.append(dict(scheme=r['scheme'],fold=r['fold'],prediction_path=str(p),sha256=sha(p),model_path=str(mp),model_sha256=sha(mp),rows=len(pred)))
    write_json(OUT/'manifests/H02_turnover_sensitivity.json',dict(folds=receipts,frozen_at=utc_now(),selection='primary_fold_alpha_only_no_outer_selection'))


def evaluate():
    manifest=json.loads((OUT/'manifests/H02_turnover_sensitivity.json').read_text())
    pieces=[];days=EP30Adapter().days;outcomes=load_outcomes(60);spec=config()['primary']['H02']
    for r in manifest['folds']:
        if sha(r['prediction_path']) != r['sha256']: raise ValueError('sensitivity changed')
        p=pd.read_parquet(r['prediction_path'])
        if quarter_complete(r['fold'],60,days): pieces.append(score_frame(p,outcomes,'H02',spec))
    f=pd.concat(pieces,ignore_index=True);rows=[]
    for scheme,g in f.groupby('scheme'):
        r,_=summarize(g,spec);rows.append(dict(scheme=scheme,factor='turnover_MA21_MA200',**r))
    pd.DataFrame(rows).to_csv(OUT/'metrics/H02_turnover_sensitivity.csv',index=False)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--evaluate',action='store_true')
    evaluate() if p.parse_args().evaluate else main()

"""No-factor, equal-date historical-mean forecast on each primary model's panel."""
import json

import numpy as np
import pandas as pd

from baselines import prediction_loss
from common import OUT, cache, config, sha, utc_now, write_json
from evaluate import quarter_complete, score_frame
from ep30_adapter import EP30Adapter
from walk_forward import cohort, load_features, load_outcomes, target_frame, training_mask


def main():
    features=load_features();outcomes={h:load_outcomes(h) for h in [20,60]};receipts=[]
    root=cache()/'constant_baseline';root.mkdir(exist_ok=True)
    for h,spec in config()['primary'].items():
        if h=='H09':continue
        f=cohort(features,h)
        valid=(f.relative_turnover.notna()&f.eff.notna()) if h=='H10' else f[spec['feature']].notna()
        frame=target_frame(f.loc[valid],outcomes[spec['horizon']],h,spec['endpoint'])
        for r in json.loads((OUT/f'manifests/{h}_folds.json').read_text())['folds']:
            train=frame.loc[training_mask(frame,r['fit_cutoff'],r['scheme'])]
            value=float(train.groupby('date').y.mean().mean())
            p=pd.read_parquet(r['predictions_path'],columns=['date','security_id','scheme','fold'])
            p['constant_baseline']=value
            path=root/(h+'_'+r['scheme']+'_'+r['fold']+'.parquet')
            if path.exists():raise RuntimeError('constant predictions already frozen')
            p.to_parquet(path,index=False)
            receipts.append(dict(hypothesis=h,scheme=r['scheme'],fold=r['fold'],constant=value,fit_cutoff=r['fit_cutoff'],
                                 max_train_mature_at=str(train.mature_at.max()),prediction_path=str(path),sha256=sha(path)))
        print('constant frozen',h,flush=True)
    write_json(OUT/'manifests/constant_baseline.json',dict(folds=receipts,frozen_at=utc_now(),definition='equal-date training mean of mature endpoint only; no features'))


def evaluate():
    d=json.loads((OUT/'manifests/constant_baseline.json').read_text());ys={h:load_outcomes(h) for h in [20,60]};days=EP30Adapter().days;rows=[]
    for r in d['folds']:
        h=r['hypothesis'];spec=config()['primary'][h]
        if not quarter_complete(r['fold'],spec['horizon'],days):continue
        if sha(r['prediction_path'])!=r['sha256']:raise ValueError('constant forecast changed')
        p=pd.read_parquet(r['prediction_path']);f=p.merge(ys[spec['horizon']],on=['date','security_id'],validate='one_to_one')
        target=np.log(f.future_variance+1e-12) if h=='H07' else f.value.lt(-.1).astype(float).where(f.value.notna()) if h=='H10' else f.value
        loss=prediction_loss(target,f.constant_baseline,spec['endpoint']);valid=target.notna()
        daily=pd.Series(np.asarray(loss)[np.asarray(valid)],index=f.loc[valid,'date']).groupby(level=0).mean()
        rows.append(dict(hypothesis=h,scheme=r['scheme'],fold=r['fold'],rows=int(valid.sum()),dates=len(daily),constant=r['constant'],loss_mean=float(daily.mean())))
    pd.DataFrame(rows).to_csv(OUT/'metrics/constant_baseline.csv',index=False)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--evaluate',action='store_true')
    evaluate() if p.parse_args().evaluate else main()

"""Required fixed HAR, candle-component and price-only-breakout ablations."""
import json
import pickle

import numpy as np
import pandas as pd

from baselines import CONTROLS, HypothesisTransform, Ridge, prediction_loss
from common import OUT, cache, config, sha, utc_now, write_json
from evaluate import quarter_complete
from ep30_adapter import EP30Adapter
from walk_forward import cohort, load_features, load_outcomes, target_frame, training_mask


def main():
    full=load_features();outcome=load_outcomes(20);receipts=[]
    root=cache()/'auxiliary_baselines';root.mkdir(exist_ok=True)
    for h in ['H10','H11','H07']:
        spec=config()['primary'][h];features=cohort(full,h)
        valid=(features.relative_turnover.notna()&features.eff.notna()) if h=='H10' else features[spec['feature']].notna()
        features=features.loc[valid].copy();frame=target_frame(features,outcome,h,spec['endpoint'])
        indexes=json.loads((OUT/f'manifests/{h}_folds.json').read_text())['folds']
        for r in indexes:
            train=frame.loc[training_mask(frame,r['fit_cutoff'],r['scheme'])]
            test=features.loc[features.date.dt.to_period('Q').astype(str).eq(r['fold'])]
            t=HypothesisTransform().fit(train);a=t.apply(train,h);v=t.apply(test,h)
            designs={'controls_only':CONTROLS,'high_turnover_only':CONTROLS+['high_turnover'],'low_eff_only':CONTROLS+['low_eff']} if h=='H10' else {'price_breakout_only':['breakthrough_strength','mom20','mom60']} if h=='H11' else {'HAR_like_log_variance':['log_rv5','log_rv20','log_rv60']}
            if h=='H07':
                for n in [5,20,60]:
                    a['log_rv'+str(n)]=np.log(a['rv'+str(n)]+1e-12);v['log_rv'+str(n)]=np.log(v['rv'+str(n)]+1e-12)
            p=v[['date','security_id']].copy();models={}
            for name,cols in designs.items():
                model=Ridge().fit(a[cols],a.y,a.date,r['alpha']);models[name]=model
                p[name]=model.predict(v[cols])
            if h=='H07':p['historical_rv20']=np.log(v.rv20+1e-12)
            p['scheme'],p['fold']=r['scheme'],r['fold']
            name=h+'_'+r['scheme']+'_'+r['fold'];pp=root/(name+'.parquet');mp=root/(name+'.pkl')
            if pp.exists():raise RuntimeError('auxiliary predictions already frozen')
            p.to_parquet(pp,index=False);mp.write_bytes(pickle.dumps(dict(transform=t,models=models),protocol=5))
            receipts.append(dict(hypothesis=h,scheme=r['scheme'],fold=r['fold'],fit_cutoff=r['fit_cutoff'],
                                 max_train_mature_at=str(train.mature_at.max()),prediction_path=str(pp),sha256=sha(pp),model_path=str(mp),model_sha256=sha(mp)))
        print('auxiliary frozen',h,flush=True)
    write_json(OUT/'manifests/auxiliary_baselines.json',dict(folds=receipts,frozen_at=utc_now(),alpha='primary_inner_selected_fixed',secondary_descriptive_only=True))


def evaluate():
    indexes=json.loads((OUT/'manifests/auxiliary_baselines.json').read_text())['folds'];y=load_outcomes(20);days=EP30Adapter().days
    results=[]
    for r in indexes:
        if not quarter_complete(r['fold'],20,days):continue
        if sha(r['prediction_path'])!=r['sha256']:raise ValueError('auxiliary changed')
        p=pd.read_parquet(r['prediction_path']);f=p.merge(y,on=['date','security_id'],validate='one_to_one')
        h=r['hypothesis'];spec=config()['primary'][h]
        target=np.log(f.future_variance+1e-12) if h=='H07' else f.value.lt(-.1).astype(float).where(f.value.notna()) if h=='H10' else f.value
        for col in p.columns:
            if col in ['date','security_id','scheme','fold']:continue
            loss=prediction_loss(target,f[col],spec['endpoint'])
            valid=target.notna()&f[col].notna()
            daily=pd.Series(np.asarray(loss)[np.asarray(valid)],index=f.loc[valid,'date']).groupby(level=0).mean()
            results.append(dict(hypothesis=h,scheme=r['scheme'],fold=r['fold'],baseline=col,rows=int(valid.sum()),dates=len(daily),loss_mean=float(daily.mean())))
    pd.DataFrame(results).to_csv(OUT/'metrics/required_baseline_ablations.csv',index=False)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--evaluate',action='store_true')
    evaluate() if p.parse_args().evaluate else main()

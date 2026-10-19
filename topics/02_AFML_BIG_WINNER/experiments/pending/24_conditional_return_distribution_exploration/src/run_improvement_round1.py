"""R16 first candidates: normalized returns, richer peers and shallow direct probabilities."""
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from catboost import CatBoostClassifier
from build_improvement_features import FEATURE_PANEL
from diagnose_prediction_target import DEST
from run_four_horizons import OUT,GRID,TECH,probability_stats
from run_direct_probability import classes,weighted_stats
from enrich_panel import VALUATION,FINANCIAL,CREDIT
CANDIDATES=DEST/'round1'
CACHE=OUT/'local_cache/r16_round1_distributions'
NEW_STOCK=['reversal5','reversal10','beta63','beta252','idio_vol63','skew63','downvol63','up_fraction21','ma20_distance','relative_mom21','relative_mom63','relative_mom126']
MARKET=[f'{index}_{f}' for index in ['csi300','all_a'] for f in ['mom5','mom21','mom63','mom126','mom252','vol21','vol63','ma20','drawdown252']]


def normalize_features(train,test,cols):
    median=train[cols].median().fillna(0)
    scale=(train[cols].quantile(.75)-train[cols].quantile(.25)).replace(0,1).fillna(1)
    return ((train[cols].fillna(median)-median)/scale).clip(-5,5),((test[cols].fillna(median)-median)/scale).clip(-5,5)


def class_distribution(y,c,prob):
    placeholders=[-.3,-.1,-.025,0,.025,.1,.3]
    q=[]
    for k in range(7):
        v=y[c==k];q.append(np.quantile(v,(np.arange(32)+.5)/32) if len(v) else np.full(32,placeholders[k]))
    return np.tile(np.concatenate(q),(len(prob),1)),np.repeat(prob/32,32,axis=1)


def run():
    CANDIDATES.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    panel=pd.read_parquet(FEATURE_PANEL);panel=panel[panel.common_eligible]
    cols=list(dict.fromkeys(TECH+VALUATION+FINANCIAL+CREDIT+['forward_log_anchor12']+NEW_STOCK+MARKET))
    assert not any('label' in c or c.startswith('y_') or c.startswith('end_') for c in cols)
    peercols=['vol63','log_cap','relative_mom21','relative_mom63','reversal5','csi300_mom21','csi300_mom126','csi300_vol63']
    audits=[]
    for h in [1,3,6]:
        rows=[]
        for date,test in panel[panel.date>='2021-01-01'].groupby('date',sort=True):
            test=test.reset_index(drop=True)
            train=panel[(panel[f'end_{h}']<date)&panel[f'y_{h}'].notna()&(panel.date<date)]
            y=train[f'y_{h}'].to_numpy();globalq=np.quantile(y,GRID)
            x,z=normalize_features(train,test,peercols)
            ix=NearestNeighbors(n_neighbors=min(1000,len(train)),n_jobs=1).fit(x).kneighbors(z,return_distance=False)
            rich=.75*np.quantile(y[ix],GRID,axis=1).T+.25*globalq
            scale_train=train.vol63.clip(.05,2).to_numpy()*np.sqrt(h/12)
            scale_test=test.vol63.clip(.05,2).to_numpy()*np.sqrt(h/12)
            normalized=np.log1p(y)/scale_train
            pooled=np.quantile(normalized,GRID)
            norm_global=np.expm1(scale_test[:,None]*pooled)
            norm_peers=np.expm1(scale_test[:,None]*(.75*np.quantile(normalized[ix],GRID,axis=1).T+.25*pooled))
            predictions={'richer_peers':(rich,None),'vol_normalized_global':(norm_global,None),'vol_normalized_peers':(norm_peers,None)}
            c=classes(y)
            classifier=CatBoostClassifier(loss_function='MultiClass',iterations=100,depth=2,learning_rate=.03,l2_leaf_reg=20,
                random_seed=24,thread_count=4,verbose=False,allow_writing_files=False)
            classifier.fit(train[cols],c)
            prob=np.zeros((len(test),7));prob[:,classifier.classes_.astype(int)]=classifier.predict_proba(test[cols])
            prior=np.bincount(c,minlength=7)/len(c)
            predictions['shallow_classes']=class_distribution(y,c,prob)
            predictions['shallow_classes_shrunk']=class_distribution(y,c,.5*prob+.5*prior)
            stamp=str(date.date());test[['date','instrument']].to_parquet(CACHE/f'{h}_{stamp}_keys.parquet',index=False)
            for name,(atoms,weights) in predictions.items():
                r=test[['date','instrument',f'end_{h}',f'target_{h}',f'y_{h}']].rename(columns={f'end_{h}':'label_end',f'target_{h}':'target_date',f'y_{h}':'actual'})
                stats=probability_stats(atoms,r.actual) if weights is None else weighted_stats(atoms,weights,r.actual)
                r=pd.concat([r,stats],axis=1);r['months']=h;r['model']=name;rows.append(r)
                payload={'atoms':atoms.astype(np.float32)}
                if weights is not None:payload['weights']=weights.astype(np.float32)
                np.savez_compressed(CACHE/f'{h}_{stamp}_{name}.npz',**payload)
            audits.append(dict(months=h,date=stamp,training_rows=len(train),test_rows=len(test),last_training_label=str(train[f'end_{h}'].max().date())))
            print(h,stamp,len(train),len(test),flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(CANDIDATES/f'predictions_{h}m.parquet',index=False)
    pd.DataFrame(audits).to_csv(CANDIDATES/'fit_audit.csv',index=False)
    (CANDIDATES/'spec.json').write_text(json.dumps(dict(features=cols,horizons=[1,3,6],cutoff='2026-05-29',common_population='R15',selection='fixed candidates; no best-month or outcome-based filtering'),indent=2)+'\n')


if __name__=='__main__':run()

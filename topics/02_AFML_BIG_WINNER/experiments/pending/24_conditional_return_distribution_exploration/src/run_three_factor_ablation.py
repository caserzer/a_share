"""R15: all 2^3 feature groups, identical samples and monthly maturity-safe fits."""
import hashlib
import itertools
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from build_three_factor_panel import DEST,PANEL,BASE,GROUPS
from run_four_horizons import OUT,EP,GRID,probability_stats
VARIANTS={'B'+''.join(g):list(g) for n in range(4) for g in itertools.combinations('CPF',n)}
CACHE=OUT/'local_cache/r15_distributions'


def scaled_features(train,test):
    columns=BASE+[c for cols in GROUPS.values() for c in cols]
    median=train[columns].median();scale=(train[columns].quantile(.75)-train[columns].quantile(.25)).replace(0,1)
    x=((train[columns]-median)/scale).clip(-5,5);z=((test[columns]-median)/scale).clip(-5,5)
    x.loc[:,GROUPS['C']]/=np.sqrt(2);z.loc[:,GROUPS['C']]/=np.sqrt(2)
    return x,z


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    panel=pd.read_parquet(PANEL);panel=panel[panel.common_eligible].copy()
    audits=[]
    for h in [1,3,6]:
        rows=[]
        for date,test in panel[panel.date>='2021-01-01'].groupby('date',sort=True):
            test=test.reset_index(drop=True)
            train=panel[(panel[f'end_{h}']<date)&panel[f'y_{h}'].notna()&(panel.date<date)]
            assert train[f'end_{h}'].max()<date
            y=train[f'y_{h}'].to_numpy();globalq=np.quantile(y,GRID)
            x,z=scaled_features(train,test)
            preds={'historical':np.tile(globalq,(len(test),1))}
            for name,groups in VARIANTS.items():
                cols=BASE+[c for g in groups for c in GROUPS[g]]
                idx=NearestNeighbors(n_neighbors=min(1000,len(train)),n_jobs=1).fit(x[cols]).kneighbors(z[cols],return_distance=False)
                preds[name]=.75*np.quantile(y[idx],GRID,axis=1).T+.25*globalq
            stamp=str(date.date());keys=test[['date','instrument']]
            keys.to_parquet(CACHE/f'{h}_{stamp}_keys.parquet',index=False)
            for name,atoms in preds.items():
                r=test[['date','instrument',f'end_{h}',f'target_{h}',f'y_{h}']].rename(columns={f'end_{h}':'label_end',f'target_{h}':'target_date',f'y_{h}':'actual'})
                r=pd.concat([r,probability_stats(atoms,r.actual)],axis=1)
                r['months']=h;r['model']=name;rows.append(r)
                np.savez_compressed(CACHE/f'{h}_{stamp}_{name}.npz',atoms=atoms.astype(np.float32))
            trainkeys=train[['date','instrument']].sort_values(['date','instrument']).to_csv(index=False).encode()
            audits.append(dict(months=h,date=stamp,training_rows=len(train),prediction_rows=len(test),last_training_label=str(train[f'end_{h}'].max().date()),
                train_key_sha256=hashlib.sha256(trainkeys).hexdigest(),test_key_sha256=hashlib.sha256(keys.to_csv(index=False).encode()).hexdigest(),
                mature_prediction_rows=int(test[f'end_{h}'].notna().sum()),missing_mature_outcomes=int((test[f'end_{h}'].notna()&test[f'y_{h}'].isna()).sum())))
            print(h,stamp,'train',len(train),'test',len(test),'variants',len(preds),flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
    pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv',index=False)
    (DEST/'run_spec.json').write_text(json.dumps(dict(horizons=[1,3,6],variants=VARIANTS,groups=GROUPS,
        plan_sha256=hashlib.sha256((EP/'notes/r15_three_factor_ablation.md').read_bytes()).hexdigest(),
        panel_sha256=hashlib.sha256(PANEL.read_bytes()).hexdigest(),neighbors=1000,quantile_shrinkage=.25,
        information='features available at decision date; train labels end strictly before prediction date',
        evidence='retrospective ablation; no new holdout',cutoff='2026-05-29'),indent=2)+'\n')


if __name__=='__main__':run()

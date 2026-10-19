"""R14A: monthly-origin walk-forward, expanding versus rolling risk/size distributions."""
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from run_four_horizons import OUT, EP, TECH, GRID, probability_stats
DEST=OUT/'r14_monthly_walk_forward'
CACHE=OUT/'local_cache/r14_distributions'


def train_at(panel,horizon,date,window=None):
    train=panel[(panel[f'end_{horizon}']<date)&panel[f'y_{horizon}'].notna() & (panel.date<date)]
    if window:train=train[train.date>=date-pd.DateOffset(months=window)]
    return train


def predict_risk(train,test,h):
    cols=['vol63','log_cap'];y=train[f'y_{h}'].to_numpy()
    q=np.quantile(y,GRID)
    median=train[cols].median();scale=(train[cols].quantile(.75)-train[cols].quantile(.25)).replace(0,1)
    x=((train[cols]-median)/scale).clip(-5,5);z=((test[cols]-median)/scale).clip(-5,5)
    ix=NearestNeighbors(n_neighbors=min(1000,len(train)),n_jobs=1).fit(x).kneighbors(z,return_distance=False)
    return .75*np.quantile(y[ix],GRID,axis=1).T+.25*q,q


def run():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    panel=pd.read_parquet(OUT/'local_cache/four_horizon_panel.parquet').dropna(subset=TECH+['earnings_yield','book_yield'])
    audits=[]
    for h in [1,3,6]:
        results=[];coverage=[]
        for date,test in panel[panel.date>='2021-01-01'].groupby('date',sort=True):
            test=test.reset_index(drop=True)
            train=train_at(panel,h,date);recent=train_at(panel,h,date,36)
            peer,glob=predict_risk(train,test,h);roll,rglob=predict_risk(recent,test,h)
            pred={'expanding_empirical':np.tile(glob,(len(test),1)),
                'recent36_empirical':np.tile(rglob,(len(test),1)),
                'peers_risk_size':peer,'peers_risk_size_36m':roll}
            stamp=str(date.date())
            test[['date','instrument']].to_parquet(CACHE/f'{h}_{stamp}_keys.parquet',index=False)
            for name,atoms in pred.items():
                r=test[['date','instrument',f'end_{h}',f'target_{h}',f'y_{h}']].rename(columns={f'end_{h}':'label_end',f'target_{h}':'target_date',f'y_{h}':'actual'})
                r=pd.concat([r,probability_stats(atoms,r.actual)],axis=1)
                r['model']=name;r['months']=h;results.append(r)
                np.savez_compressed(CACHE/f'{h}_{stamp}_{name}.npz',atoms=atoms.astype(np.float32))
            for name,tr in [('expanding',train),('rolling36',recent)]:
                assert tr[f'end_{h}'].max()<date and tr.date.max()<date
                audits.append(dict(months=h,date=stamp,window=name,training_rows=len(tr),first_training_origin=str(tr.date.min().date()),last_training_label=str(tr[f'end_{h}'].max().date()),predicted_rows=len(test)))
            mature=test[f'end_{h}'].notna()
            coverage.append(dict(months=h,date=stamp,predicted=len(test),mature=int(mature.sum()),missing_outcomes=int((mature & test[f'y_{h}'].isna()).sum())))
            print(h,stamp,len(train),len(recent),flush=True)
        pd.concat(results,ignore_index=True).to_parquet(DEST/f'predictions_{h}m.parquet',index=False)
        pd.DataFrame(coverage).to_csv(DEST/f'coverage_{h}m.csv',index=False)
    pd.DataFrame(audits).to_csv(DEST/'fit_audit.csv',index=False)
    (DEST/'run_spec.json').write_text(json.dumps(dict(horizons=[1,3,6],plan_sha256=hashlib.sha256((EP/'notes/r14_walk_forward.md').read_bytes()).hexdigest(),cutoff='2026-05-29',refit='each prediction date; labels end strictly before date',evidence='retrospective monthly walk-forward',rolling_window_origin_months=36),indent=2)+'\n')


if __name__=='__main__':run()

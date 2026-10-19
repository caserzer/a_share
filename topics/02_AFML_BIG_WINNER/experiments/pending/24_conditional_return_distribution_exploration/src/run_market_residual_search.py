"""R16 second family: forecast market and stock-specific components separately.

All market and residual training labels mature before prediction date.
"""
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from prepare_panel import DATA
from build_improvement_features import FEATURE_PANEL
from diagnose_prediction_target import DEST
from run_four_horizons import OUT,GRID,calendar_targets,probability_stats
from run_improvement_round1 import normalize_features
FOLDER=DEST/'market_residual'
CACHE=OUT/'local_cache/r16_market_residual'
Q=(np.arange(25)+.5)/25


def combine_components(market_atoms,residual_atoms,beta,residual_scale):
    log_samples=beta[:,None,None]*market_atoms[None,:,None]+residual_scale[:,None,None]*residual_atoms[:,None,:]
    samples=np.expm1(log_samples.reshape(len(beta),-1))
    return np.quantile(samples,GRID,axis=1).T


def run():
    FOLDER.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    panel=pd.read_parquet(FEATURE_PANEL);panel=panel[panel.common_eligible]
    features=pd.read_parquet(OUT/'local_cache/improvement_market_features.parquet')
    calendar=pd.DatetimeIndex(features.index)
    indices=pd.read_csv(DATA/'processed/index/benchmark_indices_daily.csv',parse_dates=['date'])
    close=indices[indices.index_alias=='csi300'].set_index('date').close.reindex(calendar)
    market_cols=['csi300_mom21','csi300_mom63','csi300_mom126','csi300_vol63','all_a_mom21','all_a_mom63']
    stock_cols=['log_cap','vol63','relative_mom21','relative_mom126','pe_percentile']
    audits=[]
    for h in [1,3,6]:
        _,end=calendar_targets(calendar,h,calendar)
        market=features.copy();market['date']=calendar
        market['label_end']=end.to_numpy()
        market['log_return']=np.log(close.reindex(pd.DatetimeIndex(end)).to_numpy()/close.to_numpy())
        market['scale']=market.csi300_vol63.clip(.03,1)*np.sqrt(h/12)
        market=market.dropna(subset=market_cols)
        rows=[]
        for date,test in panel[panel.date>='2021-01-01'].groupby('date',sort=True):
            test=test.reset_index(drop=True)
            train=panel[(panel[f'end_{h}']<date)&panel[f'y_{h}'].notna()&panel[f'market_label_{h}'].notna()]
            mtrain=market[(market.label_end<date)&market.log_return.notna()]
            current=market.loc[[date]]
            beta_train=train.beta252.fillna(1).clip(0,2).to_numpy();beta_test=test.beta252.fillna(1).clip(0,2).to_numpy()
            train_scale=train.idio_vol63.fillna(train.vol63).clip(.03,2).to_numpy()*np.sqrt(h/12)
            test_scale=test.idio_vol63.fillna(test.vol63).clip(.03,2).to_numpy()*np.sqrt(h/12)
            residual=(np.log1p(train[f'y_{h}'].to_numpy())-beta_train*np.log1p(train[f'market_label_{h}'].to_numpy()))/train_scale
            x,z=normalize_features(train,test,stock_cols)
            ix=NearestNeighbors(n_neighbors=min(1000,len(train)),n_jobs=1).fit(x).kneighbors(z,return_distance=False)
            residual_q=.75*np.quantile(residual[ix],Q,axis=1).T+.25*np.quantile(residual,Q)
            mx,mz=normalize_features(mtrain,current,market_cols)
            midx=NearestNeighbors(n_neighbors=min(252,len(mtrain)),n_jobs=1).fit(mx).kneighbors(mz,return_distance=False)[0]
            standardized=(mtrain.log_return/mtrain.scale).to_numpy()
            today_scale=float(current.scale.iloc[0]);glob=np.quantile(standardized,Q)*today_scale
            conditional=(.5*np.quantile(standardized[midx],Q)+.5*np.quantile(standardized,Q))*today_scale
            drift=.25*np.log1p(float(current.csi300_mom63.iloc[0]))*h/3
            momentum=glob-glob.mean()+drift
            methods={'market_empirical_residual':glob,'market_state_residual':conditional,'market_momentum_residual':momentum}
            test[['date','instrument']].to_parquet(CACHE/f'{h}_{date.date()}_keys.parquet',index=False)
            for name,market_atoms in methods.items():
                atoms=combine_components(market_atoms,residual_q,beta_test,test_scale)
                r=test[['date','instrument',f'end_{h}',f'target_{h}',f'y_{h}']].rename(columns={f'end_{h}':'label_end',f'target_{h}':'target_date',f'y_{h}':'actual'})
                r=pd.concat([r,probability_stats(atoms,r.actual)],axis=1);r['model']=name;r['months']=h;rows.append(r)
                np.savez_compressed(CACHE/f'{h}_{date.date()}_{name}.npz',atoms=atoms.astype(np.float32))
            assert train[f'end_{h}'].max()<date and mtrain.label_end.max()<date
            audits.append(dict(months=h,date=str(date.date()),stock_training_rows=len(train),market_training_rows=len(mtrain),
                last_stock_label=str(train[f'end_{h}'].max().date()),last_market_label=str(mtrain.label_end.max().date()),predicted_rows=len(test)))
            print(h,str(date.date()),len(train),len(mtrain),flush=True)
        pd.concat(rows,ignore_index=True).to_parquet(FOLDER/f'predictions_{h}m.parquet',index=False)
    pd.DataFrame(audits).to_csv(FOLDER/'fit_audit.csv',index=False)
    (FOLDER/'spec.json').write_text(json.dumps(dict(market_features=market_cols,stock_features=stock_cols,
        assumptions='log return = clipped trailing beta * market log return + independent scaled residual; 25x25 atoms compressed to 200',
        market_knn_days=252,stock_knn_rows=1000,market_state_shrinkage=.5,momentum_drift_coefficient=.25),indent=2)+'\n')


if __name__=='__main__':run()

from common_inputs import *
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from model import Transform

def fit(q):
    cutoff=pd.Period(q).start_time
    d=DATA[(DATA.signal_date<cutoff)&(DATA.h10_mature<cutoff)]
    g=TEST[TEST.fold==q]
    result=g[KEY].copy()
    groups={'T69':[c for c in COLS if c.startswith('market_')],
        'no_dd':[c for c in COLS if c.startswith(('dd','pos'))],
        'no_amp':[c for c in COLS if c.startswith(('amp','vol')) and not c.startswith('volume')],
        'no_path':[c for c in COLS if c.startswith(('ret_lag','xsret_lag'))],
        'F10':[], 'leaf100':[], 'l2_5':[]}
    audit=[]
    for arm,drop in groups.items():
        cols=[c for c in COLS if c not in drop]
        med=d[cols].median().fillna(0)
        y=d.target_z if arm=='F10' else d.target_rank
        ds=lgb.Dataset(d[cols].fillna(med),label=y,free_raw_data=False)
        params=dict(PARAMS,num_threads=2)
        if arm=='leaf100': params['min_data_in_leaf']=100
        if arm=='l2_5':params['lambda_l2']=5
        warm=lgb.train(dict(params,objective='regression'),ds,num_boost_round=20)
        yy=y.to_numpy()
        def grad(p,ds):return 2*(p-yy),np.full(len(p),2.)
        tree=lgb.train(dict(params,objective=grad),ds,num_boost_round=60,init_model=warm)
        result[arm]=tree.predict(g[cols].fillna(med),num_threads=2)
        if arm=='T69':result['R69']=predict(g[cols],ridge(d,cols,'target_rank'))
    model_dir=PRIVATE/'models'/'expanding'
    files=sorted(model_dir.glob(q+'_E2_seed*.txt'))
    assert len(files)==3
    result['F00']=np.mean([lgb.Booster(model_file=str(f)).predict(g[COLS],num_threads=2) for f in files],axis=0)
    valid=d.signal_date.ge(cutoff-pd.Timedelta(nanoseconds=1)-pd.DateOffset(months=6))
    inner=(~valid)&(d.h10_mature<d.loc[valid,'entry_date'].min())
    cfg=json.loads((PRIVATE.parent/'configs/protocol.json').read_text())
    params=dict(cfg['lightgbm'],n_jobs=2)
    early=params.pop('early_stopping_rounds')
    preds=[]
    for seed in cfg['seeds']:
        model=lgb.LGBMRegressor(**params,random_state=seed)
        model.fit(d.loc[inner,COLS],d.target_rank[inner],eval_set=[(d.loc[valid,COLS],d.target_rank[valid])],callbacks=[lgb.early_stopping(early,verbose=False)])
        rounds=model.best_iteration_
        model=lgb.LGBMRegressor(**dict(params,n_estimators=rounds),random_state=seed)
        model.fit(d[COLS],d.target_rank)
        preds.append(model.predict(g[COLS]))
        audit.append(dict(fold=q,seed=seed,rounds=rounds,rows=len(d),last_maturity=d.h10_mature.max(),first_signal=g.signal_date.min(),market_vol_cut=d.groupby('signal_date').market_vol20.first().median()))
    result['F01']=np.mean(preds,axis=0)
    train=d[COLS+['target_rank']].copy()
    test=g[COLS].copy()
    for c in ['vol20','amp20','mom5','dd60']:
        for i,knot in enumerate(train[c].quantile([1/3,2/3]).values):
            for f in [train,test]:f[f'{c}_hinge{i}']=(f[c]-knot).clip(lower=0)
    for arm in ['G1','G2']:
        if arm=='G2':
            for a,b in [('market_vol20','vol20'),('market_mom20','mom5'),('market_dd60','dd60')]:
                tr=Transform().fit(train[[a,b]])
                for f in [train,test]:f[a+'_'+b]=tr.transform(f[[a,b]]).prod(axis=1)
        result[arm]=predict(test,ridge(train,list(test.columns),'target_rank'))
    result.to_parquet(DEST/'folds'/(q+'.parquet'),index=False)
    pd.DataFrame(audit).to_csv(DEST/'folds'/(q+'.csv'),index=False)
    print(q,flush=True)

if __name__=='__main__':
    (DEST/'folds').mkdir(exist_ok=True)
    DATA=prepare().sort_values(KEY).merge(pd.read_parquet(PRIVATE/'labels.parquet',columns=KEY+['entry_date']),on=KEY,validate='1:1')
    TEST=outer()
    with ProcessPoolExecutor(5,mp_context=get_context('fork')) as pool:list(pool.map(fit,sorted(TEST.fold.unique())))

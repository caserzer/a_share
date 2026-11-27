from ep43lib import *
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import json
def one(q):
    dest=O/'models';dest.mkdir(exist_ok=True)
    path=dest/(str(q)+'.parquet')
    sets=[]
    for pool in [300,800]:
        wide=pool==800
        x=read_features(q,wide)
        ref=refs[wide]
        x=ref[ref.signal_date.dt.to_period('Q')==q].merge(x,on=KEY,validate='1:1')
        results=x[KEY].copy()
        train=trains[wide];train=train[train.mature<q.start_time]
        cc=[c for c in COL if not c.startswith('market_')];keep=[c for c in cc if c not in CFG['directions']['B']['remove']]
        t=train.dropna(subset=['ytotal'])
        for name in ['intra','over','total']:
            results[name]=ci.predict(x[COL],ci.ridge(t,COL,'y'+name))
        results['R']=x.refit_R if wide else x.R
        base=ci.predict(x[COL],ci.ridge(train,COL,'target_rank'))
        assert np.max(abs(base-results.R))<1e-8,(q,pool,np.max(abs(base-results.R)))
        for name,cols,depth,study,y in [('T69',cc,-1,train,'target_rank'),('T69d',cc,3,train,'target_rank'),('T60',keep,-1,train,'target_rank'),('T60d',keep,3,train,'target_rank'),('treeover',COL,-1,t,'yover')]:
            med=study[cols].median().fillna(0)
            tree=ci.lgb.train(dict(ci.PARAMS,objective='regression',max_depth=depth,num_threads=2),ci.lgb.Dataset(study[cols].fillna(med),label=study[y]),num_boost_round=80)
            results[name]=tree.predict(x[cols].fillna(med),num_threads=2)
            if not wide and name=='T60d':transfer=(tree,med,cols)
        if wide:
            tree,med,cols=transfer
            results['transferT']=tree.predict(x[cols].fillna(med),num_threads=2)
            results['transferR']=x.transfer_R
        results['pool']=pool
        sets.append(results)
        audit=dict(quarter=str(q),pool=pool,train=len(train),common=len(t),max_maturity=str(t.mature.max()),scores=len(x),R_error=float(np.max(abs(base-results.R))))
        (dest/f'{q}_{pool}.json').write_text(json.dumps(audit))
    pd.concat(sets).to_parquet(path,index=False)
    print(q,flush=True)
if __name__=='__main__':
    trains={};refs={}
    for wide in [False,True]:
        f,err=market_labels(weekly(wide),wide)
        f[KEY+['intra','over','total','mature','yintra','yover','ytotal']].to_parquet(O/f'labels_{800 if wide else 300}.parquet',index=False)
        print(wide,len(f),err,flush=True);trains[wide]=f;refs[wide]=frozen(wide)
    with ProcessPoolExecutor(3,mp_context=mp.get_context('fork')) as ex:
        list(ex.map(one,[q for q in pd.period_range('2019Q1','2026Q3',freq='Q') if not (O/'models'/f'{q}.parquet').exists()]))

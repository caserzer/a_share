"""Shuffle only mature training outcomes among stocks on each date; preserve dates and features."""
from accounts_followup import *
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from model import date_rankic

def trial(seed):
    random=np.random.default_rng(20261125+seed)
    data=DATA.copy()
    data['shuffled']=data.groupby('signal_date').target_rank.transform(lambda x:random.permutation(x))
    parts=[]
    for q,g in TEST.groupby('fold'):
        d=data[data.h10_mature<pd.Period(q).start_time]
        med=d[COLS].median().fillna(0);y=d.shuffled.to_numpy()
        train=lgb.Dataset(d[COLS].fillna(med),label=y,free_raw_data=False)
        warm=lgb.train(dict(PARAMS,objective='regression'),train,num_boost_round=20)
        def grad(p,_):return 2*(p-y),np.full(len(p),2.)
        tree=lgb.train(dict(PARAMS,objective=grad),train,num_boost_round=60,init_model=warm)
        parts.append(g[KEY+['entry_idx']].assign(score=tree.predict(g[COLS].fillna(med),num_threads=2)))
    s=pd.concat(parts).sort_values(KEY).merge(ledger.labels(),on=KEY,how='left',validate='1:1')
    rows=[];returns=[]
    for later,g in s.groupby(s.signal_date>=pd.Timestamp('2025-02-28')):
        scope='later' if later else 'primary';plan={}
        for date,d in g.groupby('signal_date'):
            ic=d.score.corr(d.h10,'spearman');rows.append((scope,seed,date,ic))
            pick=d.sort_values(['score','instrument']).tail(len(d)//10)
            plan[d.entry_idx.iloc[0]]=M.symbols.get_indexer(pick.instrument)
        w,_,_,_=replay(M,ACT,plan,10,1,False)
        returns.extend((scope,seed,*v) for v in w)
    return rows,returns
if __name__=='__main__':
    DATA=prepare().sort_values(KEY)
    TEST=outer()
    ledger.accounts.OUT=DEST
    M,ACT=ledger.setup('flat')
    with ProcessPoolExecutor(4,mp_context=get_context('fork')) as pool:results=list(pool.map(trial,range(1,9)))
    for j,(name,cols) in enumerate([('ic','scope seed date rankic'),('windows','scope seed entry_idx net fee turnover')]):
        pd.DataFrame([r for z in results for r in z[j]],columns=cols.split()).to_parquet(DEST/('placebo_'+name+'.parquet'),index=False)

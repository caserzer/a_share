"""Verify V1 with explicit gap-through-prior-low and drying turnover definitions."""
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from fit import metrics,PARAM
from ep41inputs import *
import lightgbm as lgb
import json

def fit(q):
    cut=q.start_time
    test=D[(Q==q)&D.weekly]
    train=D[D.weekly&D.m10.lt(cut)].dropna(subset=['event'])
    if test.empty or train.empty:return pd.DataFrame()
    tr=OOF[OOF.signal_date.dt.to_period('Q')==q]
    if tr.empty:return pd.DataFrame()
    test=test.loc[test.index.intersection(tr.index)]
    tree=lgb.train(dict(PARAM,objective='binary',boost_from_average=True),lgb.Dataset(train[cols],label=train.event),num_boost_round=80)
    return pd.DataFrame({'specific_tail':tree.predict(test[cols],num_threads=1)},index=test.index)

if __name__=='__main__':
    D=pd.read_parquet(CACHE/'panel.parquet')
    c=read('qfq_close');o=read('qfq_open');l=read('qfq_low');amt=read('money')
    i=c.index.get_indexer(D.signal_date);j=c.columns.get_indexer(D.instrument)
    D['gap_break20']=((o/l.rolling(20).min().shift()-1).clip(upper=0)).to_numpy()[i,j]
    D['down_surge']=(amt/amt.rolling(20).mean().shift()).where(c<c.shift(),0).to_numpy()[i,j]
    D['liquidity_dry']=(amt.rolling(5).mean()/amt.rolling(20).mean()).to_numpy()[i,j]
    cols=COLS+['ncskew20','duvol20','gap_break20','down_surge','liquidity_dry']
    raw=pd.read_parquet(OUT/'weekly_oof.parquet')
    OOF=D[KEY].reset_index().merge(raw,on=KEY,validate='1:1').set_index('index')
    Q=D.signal_date.dt.to_period('Q')
    with ProcessPoolExecutor(3,mp_context=get_context('fork')) as pool:OOF=OOF.join(pd.concat(pool.map(fit,sorted(Q.unique()))),validate='1:1')
    rows=[]
    for q in sorted(Q[D.outer].unique()):
        v=OOF[OOF.in_core&OOF.m10.lt(q.start_time)].dropna(subset=['event','specific_tail'])
        scores={arm:metrics(v,arm) for arm in ['specific_tail','inc','history']}
        a,b,c=scores['specific_tail'],scores['inc'],scores['history']
        passed=a[0]>=.55 and a[0]>b[0] and a[1]<min(b[1],c[1]) and a[2]<b[2] and v.event.value_counts().min()>=20 and v.groupby('event').signal_date.nunique().min()>=4
        rows.append((str(q),len(v),v.event.sum(),*a,*b,*c,passed))
    OOF.to_parquet(OUT/'veto_specific_oof.parquet',index=False)
    pd.DataFrame(rows,columns='quarter rows events tail_auc tail_brier tail_ece baseline_auc baseline_brier baseline_ece hist_auc hist_brier hist_ece gate'.split()).to_csv(OUT/'veto_specific_gates.csv',index=False)

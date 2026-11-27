from pathlib import Path
import os
import sys

for env in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[env]='1'
import numpy as np
import pandas as pd
import lightgbm as lgb

HERE=Path(__file__).resolve().parent
EP42=HERE.parent
EP41=next(EP42.parent.glob('41_*'))
sys.path.insert(0,str(EP41/'models'))
from ep41inputs import ep, COLS, STOCK, KEY, CACHE, SEG
from fit import fit_tree, PARAM

RES=HERE/'results'
MODELS=RES/'models'
MODELS.mkdir(parents=True,exist_ok=True)
SCORES=EP41/'p2/results/scores.parquet'
WORK=Path('/tmp/ep42_scale_input')
WORK.mkdir(exist_ok=True)
PANEL=CACHE/'panel.parquet'

def data(columns):
    required=list(dict.fromkeys(KEY+['entry_idx','weekly','outer','m10','y10']+list(columns)))
    source=PANEL
    if not source.exists():
        import prepare_inputs as prepare
        prepare.CACHE=WORK/'rebuilt_ep41'
        prepare.OUT=prepare.CACHE/'audit'
        prepare.OUT.mkdir(parents=True,exist_ok=True)
        source=prepare.CACHE/'panel.parquet'
        if not source.exists():prepare.main()
    return pd.read_parquet(source,columns=required).sort_values(KEY).reset_index(drop=True)

def outer_folds(frame):
    qs=frame.signal_date.dt.to_period('Q')
    for q in sorted(qs[frame.outer].unique()):
        cut=q.start_time
        train=frame.loc[frame.weekly & frame.m10.lt(cut) & frame.y10.notna()]
        test=frame.loc[frame.outer & qs.eq(q)]
        assert train.m10.max()<cut<=test.signal_date.min()
        yield q,train,test

def mse_tree(x,y,rounds=80,depth=None):
    cfg=dict(PARAM,objective='regression')
    if depth is not None: cfg['max_depth']=depth
    return lgb.train(cfg,lgb.Dataset(x,label=y),num_boost_round=rounds)

def early_rounds(train,cols,q,depth):
    cut=q.start_time
    val=train[train.signal_date.ge(cut-pd.DateOffset(months=6))]
    tr=train[train.m10.lt(val.signal_date.min())]
    med=tr[cols].median().fillna(0.)
    tree=mse_tree(tr[cols].fillna(med),tr.y10,80,depth)
    leaf=tree.predict(val[cols].fillna(med),pred_leaf=True,num_threads=1)
    pred=np.zeros(len(val))
    losses=[]
    for k in range(leaf.shape[1]):
        pred+=np.asarray([tree.get_leaf_output(k,j) for j in range(leaf[:,k].max()+1)])[leaf[:,k]]
        losses.append(np.mean((val.y10-pred)**2))
    best=int(np.argmin(losses)+1)
    return best,(str(q),depth or -1,len(tr),str(tr.m10.max().date()),len(val),str(val.signal_date.min().date()),best,min(losses))

def atomic_parquet(df,path):
    temp=path.with_suffix('.part')
    df.to_parquet(temp,index=False,compression='zstd')
    temp.replace(path)

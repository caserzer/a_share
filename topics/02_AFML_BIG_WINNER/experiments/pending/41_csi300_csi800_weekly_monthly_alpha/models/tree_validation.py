"""Purged inner-validation curves for the prespecified residual tree variants."""
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from ep41inputs import *
from fit import fit_tree, unique_cols
import json

def path_metrics(tree,x,y,r,days):
    leaf=tree.predict(x,pred_leaf=True,num_threads=1)
    pred=np.zeros(len(x));out=[]
    for k in range(tree.num_trees()):
        ids=leaf[:,k];values=np.array([tree.get_leaf_output(k,i) for i in range(ids.max()+1)])
        pred+=values[ids]
        if k+1 not in [20,80] and k!=tree.num_trees()-1:continue
        # Report daily true-D10 purity and the average forward target rank of the forecast top decile.
        g=pd.DataFrame(dict(date=days.to_numpy(),y=y.to_numpy(),score=r.to_numpy()+pred))
        rank=g.groupby('date').score.rank(ascending=False,method='first');size=g.groupby('date').score.transform('size')
        head=g.loc[rank<=size//10]
        out.append((k+1,float(np.mean((g.y-g.score)**2)),float(head.y.mean()),float((head.y>.4).mean())))
    return out

def run(q):
    train=D[D.weekly&D.m10.lt(q.start_time)&D.y10.notna()&D.R_oof.notna()]
    valid=train[train.signal_date.ge(q.start_time-pd.DateOffset(months=6))]
    inner=train[train.m10<valid.signal_date.min()+pd.Timedelta(days=1)]
    outer=D[(D.signal_date.dt.to_period('Q')==q)&D.outer&D.y10.notna()]
    assert len(inner.index.intersection(valid.index))==0
    rows=[]
    for variant in ['original','depth3','08','unique','unique08','stop']:
        cfg={}
        if '08' in variant:cfg['feature_fraction']=.8
        if variant=='depth3':cfg['max_depth']=3
        x=RANK.loc[inner.index]
        if 'unique' in variant:x=x[unique_cols(x)[0]]
        med=x.median().fillna(0)
        audit=json.loads((OUT/(str(q)+'_fold.json')).read_text())
        rounds=audit['trees']['M3_stop']['n'] if variant=='stop' else 80
        tree=fit_tree(x.fillna(med),inner.y10-inner.R_oof,cfg,rounds)
        for sample,frame,base in [('training',inner,'R_oof'),('purged_validation',valid,'R_oof')]:
            val=path_metrics(tree,RANK.loc[frame.index,x.columns].fillna(med),frame.y10,frame[base],frame.signal_date)
            rows.extend((str(q),variant,sample,*v) for v in val)
        # Outer curves must use the actual expanding outer fit, including the validation rows.
        full=RANK.loc[train.index]
        if 'unique' in variant:full=full[unique_cols(full)[0]]
        med=full.median().fillna(0)
        outer_tree=fit_tree(full.fillna(med),train.y10-train.R_oof,cfg,rounds)
        val=path_metrics(outer_tree,RANK.loc[outer.index,full.columns].fillna(med),outer.y10,outer.R,outer.signal_date)
        rows.extend((str(q),variant,'outer',*v) for v in val)
    return rows
if __name__=='__main__':
    D=pd.read_parquet(CACHE/'panel.parquet',columns=KEY+['weekly','outer','m10','y10','R'])
    Q=D.signal_date.dt.to_period('Q')
    RANK=pd.read_parquet(CACHE/'global.parquet')
    D=D.merge(pd.read_parquet(OUT/'weekly_oof.parquet',columns=KEY+['R_oof']),on=KEY,how='left',validate='1:1')
    with ProcessPoolExecutor(3,mp_context=get_context('fork')) as pool:
        rows=[v for result in pool.map(run,sorted(Q[D.outer].unique())) for v in result]
    pd.DataFrame(rows,columns='quarter variant sample rounds mse top_target_mean true_d10_fraction'.split()).to_csv(OUT/'m3_learning_curves.csv',index=False)

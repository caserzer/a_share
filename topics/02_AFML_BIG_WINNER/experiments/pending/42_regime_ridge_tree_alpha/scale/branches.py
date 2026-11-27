"""Actual LightGBM node path counts and switches for S1. Missing ancestors tracked explicitly."""
from scale_common import *
import pyarrow as pa
import pyarrow.parquet as pq

def path_index(tree):
    nodes=[];leaves={}
    def walk(node,trail,features):
        if 'split_index' not in node:
            leaves[node.get('leaf_index',0)]=trail
            return
        n=node['split_index'];j=node['split_feature']
        nodes.append((n,j,tuple(set(features+(j,))),node['threshold']))
        walk(node['left_child'],trail+[(n,1)],features+(j,))
        walk(node['right_child'],trail+[(n,0)],features+(j,))
    walk(tree,[],())
    path=np.full((len(leaves),len(nodes)),-1,np.int8)
    for leaf,trail in leaves.items():
        for node,side in trail:path[leaf,node]=side
    return nodes,path

def run_set(name,raw,train,q,tree,med,train_leaves,dumps,writer,stats,reference,coverage):
    raw=raw.sort_values(KEY).reset_index(drop=True)
    dates=pd.DatetimeIndex(sorted(raw.signal_date.unique()))
    day=dates.get_indexer(raw.signal_date)
    sym=pd.Categorical(raw.instrument)
    grid=np.full((len(dates)+1,len(sym.categories)),-1,int)
    row=np.arange(len(raw))
    grid[day,sym.codes]=row
    prev=grid[day-1,sym.codes]
    missing=raw[STOCK].isna().to_numpy()
    valid=raw.observed.to_numpy() if 'observed' in raw else np.ones(len(raw),bool)
    x=raw[STOCK].fillna(med)
    leaves=tree.predict(x,pred_leaf=True,num_threads=1)
    for t,d in enumerate(dates):
        rows=day==t
        coverage.append((str(q),name,d,int(rows.sum()),int(valid[rows].sum()),int(raw.eligible[rows].sum()) if 'eligible' in raw else int(rows.sum())))
    sums=np.zeros((2,len(dates),4))
    for k,dump in enumerate(dumps):
        nodes,path=path_index(dump['tree_structure'])
        if not len(nodes):continue
        original=path[train_leaves[:,k],:]
        n_train=(original>=0).sum(axis=0);l_train=(original==1).sum(axis=0)
        ref=l_train/n_train
        w=n_train/len(train)
        sides=path[leaves[:,k],:]
        n_nodes=len(nodes)
        counts=np.empty((len(dates),n_nodes,8),np.int32)
        feature=[]; threshold=[]
        for n,j,anc,thr in sorted(nodes):
            good=(sides[:,n]>=0)&valid
            is_left=sides[:,n]==1
            known=good.copy()
            for f in anc:known &= ~missing[:,f]
            previous=prev.clip(min=0)
            common=(prev>=0)&valid[previous] & good & (sides[previous,n]>=0)
            switched=common & (sides[previous,n]!=sides[:,n])
            prevknown=common & known
            for f in anc:prevknown &= ~missing[previous,f]
            measures=[good,is_left & good,known,is_left & known,common,switched,prevknown,switched & prevknown]
            for jcol,flag in enumerate(measures):
                counts[:,n,jcol]=np.bincount(day[flag],minlength=len(dates))
            feature.append(STOCK[j]);threshold.append(thr)
        n=len(dates)*n_nodes
        flat=counts.reshape(n,8)
        tbl=pd.DataFrame({'quarter':str(q),'cohort':name,'signal_date':np.repeat(dates,n_nodes),
                          'tree':np.full(n,k,np.int16),'node':np.tile(np.arange(n_nodes,dtype=np.int16),len(dates)),
                          'feature':np.tile(feature,len(dates)), 'threshold':np.tile(threshold,len(dates)),
                          'training_visits':np.tile(n_train,len(dates)), 'training_left':np.tile(l_train,len(dates))})
        for i,field in enumerate('visits left clean_visits clean_left common switched clean_common clean_switched'.split()):
            tbl[field]=flat[:,i]
        writer.append(pa.Table.from_pandas(tbl,preserve_index=False))
        # The clean cohort uses its own conditional training reference,
        # not the reference inflated by median-filled paths.
        for slot,(a,b) in enumerate([(0,1),(2,3)]):
            visits=counts[:,:,a];left=counts[:,:,b]
            ref0,w0=(ref,w) if slot==0 else reference[k]
            present=(visits>0)&np.isfinite(ref0)[None,:]
            weights=present*w0
            frac=np.divide(left,visits,out=np.zeros_like(visits,dtype=float),where=visits>0)
            sums[slot,:,0]+=(weights*abs(frac-np.nan_to_num(ref0))).sum(axis=1)
            sums[slot,:,1]+=weights.sum(axis=1)
            sums[slot,:,2]+=counts[:,:,4+slot*2].sum(axis=1)
            sums[slot,:,3]+=counts[:,:,5+slot*2].sum(axis=1)
    for i,kind in enumerate(['all','observed_paths']):
        for dt,(num,den,com,sw) in zip(dates,sums[i]):
            stats.append((str(q),name,kind,dt,num/den if den else np.nan,den,com,sw,sw/com if com else np.nan))
    del leaves

class Writer:
    def __init__(self,path):self.path=path;self.handle=None
    def append(self,table):
        if self.handle is None:self.handle=pq.ParquetWriter(self.path,table.schema,compression='zstd')
        self.handle.write_table(table)
    def close(self):
        if self.handle:self.handle.close()

def main():
    frame=data(STOCK)
    stats=[];coverage=[]
    reference_records=[]
    for q,train,test in outer_folds(frame):
        med=train[STOCK].median().fillna(0.)
        file=MODELS/f'{q}_raw.txt'
        tree=lgb.Booster(model_file=str(file)) if file.exists() else fit_tree(train[STOCK].fillna(med),train.y10)
        fixed=pd.read_parquet(WORK/'fixed_cohort.parquet',filters=[('signal_date','>=',q.start_time),('signal_date','<=',q.end_time)])
        dumps=tree.dump_model()['tree_info']
        train_leaves=tree.predict(train[STOCK].fillna(med),pred_leaf=True,num_threads=1)
        tr_missing=train[STOCK].isna().to_numpy()
        reference=[]
        for k,dump in enumerate(dumps):
            nodes,path=path_index(dump['tree_structure'])
            side=path[train_leaves[:,k],:]
            rs=np.full(len(nodes),np.nan);ws=np.zeros(len(nodes))
            for n,j,anc,thr in nodes:
                known=side[:,n]>=0
                for f in anc:known &= ~tr_missing[:,f]
                ws[n]=known.mean()
                if known.any():rs[n]=np.mean(side[known,n]==1)
                reference_records.append((str(q),k,n,int(known.sum()),int((known & (side[:,n]==1)).sum()),len(train)))
            reference.append((rs,ws))
        writer=Writer(RES/f'S1_nodes_{q}.parquet')
        for name,raw in [('eligible',test),('fixed',fixed)]:
            run_set(name,raw,train,q,tree,med,train_leaves,dumps,writer,stats,reference,coverage)
        writer.close()
        print(q,'branches',flush=True)
    stats=pd.DataFrame(stats,columns='fold cohort path signal_date structure observed_training_weight same_parent transitions switch_fraction'.split())
    z=pd.read_parquet(EP42/'state/results/states.parquet')[['signal_date','Z1']]
    stats=stats.merge(z,on='signal_date',validate='m:1')
    atomic_parquet(stats,RES/'S1_daily.parquet')
    pd.DataFrame(coverage,columns='fold cohort signal_date slots quotes eligible'.split()).to_csv(RES/'S1_coverage.csv',index=False)
    atomic_parquet(pd.DataFrame(reference_records,columns='fold tree node clean_training_visits clean_training_left training_rows'.split()),RES/'S1_clean_reference.parquet')
if __name__=='__main__':main()

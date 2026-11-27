"""Allocate S1 structural distance and unsupported training weight to real split features."""
from scale_common import *
def main():
    pieces=[];ref=pd.read_parquet(RES/'S1_clean_reference.parquet')
    for file in sorted(RES.glob('S1_nodes_*.parquet')):
        x=pd.read_parquet(file,columns='quarter cohort signal_date tree node feature training_visits training_left visits left clean_visits clean_left'.split())
        r=ref[ref.fold.eq(x.quarter.iloc[0])][['tree','node','training_rows','clean_training_visits','clean_training_left']]
        x=x.merge(r,on=['tree','node'],validate='m:1')
        for kind,train,left,n,actual in [('all','training_visits','training_left','visits','left'),('observed_paths','clean_training_visits','clean_training_left','clean_visits','clean_left')]:
            w=x[train]/x.training_rows
            x['observable_weight']=np.where(x[n]>0,w,0)
            x['unobserved_weight']=w-x.observable_weight
            x['deviation']=x.observable_weight*abs(x[actual]/x[n].where(x[n]>0)-x[left]/x[train].where(x[train]>0))
            g=x.groupby(['quarter','signal_date','cohort','feature'])[['observable_weight','unobserved_weight','deviation']].sum().reset_index()
            pieces.append(g.assign(path=kind))
    a=pd.concat(pieces,ignore_index=True);atomic_parquet(a,RES/'S1_features.parquet')
if __name__=='__main__':main()

"""Independent paired inference. Never carry a monthly block across a valuation gap."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent

def infer(pairs):
    rng=np.random.default_rng(4101)
    draws=[];counts=[];rows=[]
    for segment,g in pairs.sort_values('month').groupby('segment',sort=False):
        months=pd.PeriodIndex(g.month,freq='M')
        assert months.is_unique and np.all(np.diff(months.asi8)==1)
        values=g.bp.to_numpy()
        n=len(values)
        starts=rng.integers(0,n-2,(10000,(n+2)//3))
        ix=(starts[:,:,None]+np.arange(3)).reshape(10000,-1)[:,:n]
        sims=values[ix].mean(axis=1)
        draws.append(sims);counts.append(n)
        rows.append(dict(segment=segment,months=n,estimate=values.mean(),low=np.quantile(sims,.025),high=np.quantile(sims,.975),exclude_best3=np.sort(values)[:-3].mean()))
    b=np.average(draws,axis=0,weights=counts);point=pairs.bp.mean()
    rows.append(dict(segment='all',months=sum(counts),estimate=point,low=np.quantile(b,.025),high=np.quantile(b,.975),
        centered_null_p=(1+np.sum(b-point>=point))/(1+len(b)),
        percentile_tail_p=(1+np.sum(b<=0))/(1+len(b))))
    return pd.DataFrame(rows)

def holm(arr):
    order=np.argsort(arr); adj=np.empty(len(arr))
    adj[order]=np.minimum(1,np.maximum.accumulate(np.asarray(arr)[order]*np.arange(len(arr),0,-1)))
    return adj

def main():
    first=pd.read_csv(ROOT/'p1/results/monthly_pair.csv')
    p1=first.assign(bp=first.net*1e4)
    p2=pd.read_csv(ROOT/'p2/results/full_months.csv').query("mul==1 and arm in ['tree','rank']").pivot(index=['scope','month'],columns='arm',values='net').reset_index()
    p2=p2.rename(columns={'scope':'segment'}).assign(bp=(p2.tree-p2['rank'])*1e4)
    assert list(p1.groupby('segment').size())==[28,20,18]
    assert p2.groupby('segment').size().to_dict()=={'primary':49,'later':18}
    rows=pd.concat([infer(p1).assign(test='P1'),infer(p2).assign(test='P2')],ignore_index=True)
    table=rows.segment.eq('all')
    for col in ['centered_null_p','percentile_tail_p']:rows.loc[table,'holm_'+col]=holm(rows.loc[table,col].to_numpy())
    rows.to_csv(ROOT/'primary_inference.csv',index=False)
    print(rows.round(5).to_string(index=False))
if __name__=='__main__':main()

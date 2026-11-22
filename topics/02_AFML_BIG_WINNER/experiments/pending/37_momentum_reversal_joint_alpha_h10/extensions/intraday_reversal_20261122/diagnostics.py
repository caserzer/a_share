"""Descriptive follow-up: within pre-existing medium-up/down pullbacks, residual association."""
import numpy as np
import pandas as pd
from prepare import D, EP, OLD, PRIVATE, MAIN, END, KEY
from core import bootstrap


def main():
    p=pd.read_parquet(D/"scores.parquet")
    labels=pd.read_parquet(EP/"outputs/local_cache/labels.parquet",columns=KEY+["offset","h10"])
    p=p.merge(labels[labels.offset==0],on=KEY,validate="1:1")
    close=pd.read_parquet(PRIVATE/"qfq_close.parquet")
    v=close.to_numpy()
    i=close.index.get_indexer(p.signal_date)
    j=close.columns.get_indexer(p.instrument)
    p["trend"]=v[i-5,j]/v[i-60,j]-1
    p["short"]=v[i,j]/v[i-5,j]-1
    rows=[]
    base=p[p.exit_date.le(END) & p.short.lt(0)]
    for date,g in base.groupby("signal_date"):
        for label,select in [("medium_up",g.trend>0),("medium_down",g.trend<0)]:
            x=g.loc[select,["trend","short","RANK_MSE_78","split5","h10"]].dropna()
            correlation=np.nan
            if len(x)>=20:
                ranks=x.rank().to_numpy()
                controls=np.column_stack([np.ones(len(x)),ranks[:,:3]])
                residual=ranks[:,3:]-controls@np.linalg.lstsq(controls,ranks[:,3:],rcond=None)[0]
                if (residual.std(axis=0)>1e-8).all():
                    correlation=np.corrcoef(residual.T)[0,1]
            rows.append(dict(signal_date=date,exit_date=g.exit_date.iloc[0],state=label,n=len(x),partial_rank_corr=correlation))
    r=pd.DataFrame(rows)
    r.to_csv(D/"pullback_associations.csv",index=False)
    dates=p[p.exit_date.le(END)][["signal_date","exit_date","entry_date"]].drop_duplicates().sort_values("signal_date")
    stats=[]
    for name,sub in [("primary",dates[dates.exit_date<=MAIN]),("later",dates[dates.entry_date>=MAIN])]:
        for label,g in r.groupby("state"):
            vals=sub.merge(g[g.state==label],on=["signal_date","exit_date"],how="left")
            stats.append(dict(scope=name,state=label,**bootstrap(vals.partial_rank_corr)))
    pd.DataFrame(stats).to_csv(D/"pullback_summary.csv",index=False)
    print(pd.DataFrame(stats).to_string(index=False))


if __name__=="__main__":
    main()

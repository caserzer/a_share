"""Evaluate frozen rankings using original H10 calendar, costs and stock eligibility."""
import json
import numpy as np
import pandas as pd
from prepare import D, OLD, EP, PRIVATE, KEY, MODELS, MAIN, END, sha, dump, assign_deciles
from core import rankcorr, clean
import accounts
from execution import net_account


def cohort(m,g):
    if g.empty:
        return dict(net=np.nan,n=0,reason="EMPTY",flagged=np.nan,entry=np.nan)
    r,_=accounts.event(m,g.assign(weight=1/len(g)),.001,.002)
    ok=r["any_entry"] and r["complete_exit"]
    return dict(net=r["net_return"] if ok else np.nan,n=len(g),entry=r["entry_weight"],flagged=g.flagged.mean(),
                reason="OK" if ok else ("BLOCKED_EXIT" if not r["complete_exit"] else "NO_ENTRY"))


def panel_eval(p,m):
    labels=pd.read_parquet(EP/"outputs/local_cache/labels.parquet",columns=KEY+["offset","h10"])
    z=p.merge(labels[labels.offset==0].drop(columns="offset"),on=KEY,validate="1:1")
    z=z[z.exit_date.le(END)]
    prev=None
    deciles,events,groups,holdings,ics=[],[],[],[],[]
    for date,g in z.groupby("signal_date"):
        meta=dict(signal_date=date,entry_date=g.entry_date.iloc[0],exit_date=g.exit_date.iloc[0])
        tops={}
        for model in MODELS:
            for scope,t in [("all",g),("clean",g[~g.flagged])]:
                dec=t[model+"_d"] if scope=="all" else assign_deciles(t,model)
                ics.append(meta|dict(model=model,sample=scope,rank_ic=rankcorr(t[model],t.h10),known=t.h10.count(),eligible=len(t)))
                for k,part in t.groupby(dec):
                    deciles.append(meta|dict(model=model,sample=scope,decile=k,selected=len(part),known=part.h10.count(),gross=part.h10.mean()))
                    if k==10 or (model=="RANK_MSE_78" and scope=="all" and k in [1,2,9]):
                        events.append(meta|dict(model=model,sample=scope,decile=k)|cohort(m,part))
            tops[model]=set(g.loc[g[model+"_d"]==10,"instrument"])
        # Previous targets are frozen before this signal. Those no longer eligible still
        # get the actual entry membership and buy gate, rather than being silently omitted.
        current=tops["RANK_MSE_78"]
        plans={}
        if prev is not None:
            plans.update(new=current-prev,stay=current&prev,out=prev-current)
        for model,base in [("split","RANK_MSE_78"),("joint","split"),("joint_vs_base","RANK_MSE_78")]:
            new=tops["joint" if model=="joint_vs_base" else model]
            plans[model+"_in"]=new-tops[base]
            plans[model+"_out"]=tops[base]-new
        for name,names in plans.items():
            h=g.set_index("instrument").reindex(sorted(names)).reset_index()
            # Unknown diagnostics for departed names stay unavailable.
            for col in ["entry_idx","exit_idx"]:
                h[col]=g[col].iloc[0]
            r=cohort(m,h)
            groups.append(meta|dict(cohort=name)|r)
            holdings.extend(meta|dict(cohort=name,instrument=s) for s in sorted(names))
        prev=current
    for name,records in [("deciles",deciles),("events",events),("cohorts",groups),("cohort_holdings",holdings),("rankic",ics)]:
        pd.DataFrame(records).to_csv(D/(name+".csv.gz" if name=="cohort_holdings" else name+".csv"),index=False)


def continuous(p,m):
    summary,details,net_orders,receipts=[],[],[],[]
    for model in MODELS:
        t=p[p[model+"_d"]==10].copy()
        t["weight"]=1/t.groupby("signal_date").instrument.transform("size")
        for scope,stop in [("primary",MAIN),("extended",END)]:
            end=m.days.get_loc(stop)
            for mode,bf,sf,cost in [("flat",.001,.002,"main"),("flat",0.,0.,"zero"),("strict",.001,.002,"main")]:
                for style in (["full","net"] if model=="RANK_MSE_78" else ["full"]):
                    key="_".join([model,scope,mode,cost,style])
                    if style=="net":
                        df,o,info=net_account(m,t,end,mode,bf,sf)
                        if mode=="flat" and cost=="main":
                            net_orders.append(o.assign(scope=scope))
                    else:
                        daily,orders,_,info=accounts.account(m,t,end,mode,bf,sf,key,False)
                        df=pd.DataFrame(daily)
                        if model=="RANK_MSE_78" and mode=="flat" and cost=="main":
                            pd.DataFrame(orders).to_parquet(D/("baseline_orders_"+scope+".parquet"),index=False)
                    receipts.append(dict(key=key,status=info))
                    meta=dict(model=model,scope=scope,mode=mode,cost=cost,style=style)
                    details.append(df[["date","nav","cash","fees","buy","sell"]].assign(**meta))
                    v=df.nav.to_numpy()
                    summary.append(meta|dict(start=df.date.iloc[0],end=df.date.iloc[-1],complete=info["valuation_complete"],
                                      liquidated=info["terminal_liquidated"],terminal_nav=v[-1],fees=df.fees.sum(),
                                      cagr=v[-1]**(252/(end-m.days.get_loc(df.date.iloc[0])))-1 if info["valuation_complete"] else np.nan,
                                      mdd=(v/np.maximum.accumulate(np.r_[1.,v])[1:]-1).min()))
    pd.DataFrame(summary).to_csv(D/"accounts.csv",index=False)
    pd.concat(details,ignore_index=True).to_parquet(D/"nav.parquet",index=False)
    pd.concat(net_orders,ignore_index=True).to_parquet(D/"net_orders.parquet",index=False)
    dump(D/"account_receipts.json",clean(receipts))


def main():
    for f,h in json.loads((D/"selection.json").read_text()).items():
        assert sha(D/f)==h
    accounts.OUT=D
    m=accounts.Market()
    p=pd.read_parquet(D/"scores.parquet")
    panel_eval(p,m)
    continuous(p,m)
    print("Economics complete",flush=True)


if __name__=="__main__":
    main()

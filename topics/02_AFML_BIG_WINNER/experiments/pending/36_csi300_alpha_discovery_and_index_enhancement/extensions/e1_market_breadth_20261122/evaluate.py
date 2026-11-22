"""Use sealed targets for H10 pairs, continuous accounts and concentration controls."""
import json
import numpy as np
import pandas as pd
from prepare import D, ROOT, EP, PRIVATE, OLD, MODELS, PRIMARY, END, KEY, SEED, sha, save_json, Inputs
from suspension_sensitivity import marks
from alpha_economics import run_account
from e1_return_attribution import benchmark
from portfolio import trade

FEES = (.001, .002)


def target(inp, names):
    v = np.zeros(inp.n+1)
    if len(names):
        indices = inp.symbols.get_indexer(names)
        assert min(indices)>=0
        np.add.at(v, indices, 1/len(names))
    v[-1]=max(0.,1-v[:-1].sum())
    return v


def h10(inp, i, names):
    if not len(names):
        return np.nan, "EMPTY", 0.
    j=i+10
    if j>=len(inp.days) or inp.days[j]>END:
        return np.nan, "IMMATURE", np.nan
    member,_,_,_,_,buy,sell,_=inp.context(i-1,i)
    u,c,info=trade(np.zeros(inp.n),1.,inp.o[i],target(inp,names),buy&member,sell,*FEES)
    held=u>0
    if not held.any():
        return np.nan,"NO_ENTRY",0.
    if not np.isfinite(inp.c[i:j,held]).all() or not np.isfinite(inp.o[j,held]).all():
        return np.nan,"UNKNOWN_VALUATION",info["buy"]
    sell=inp.context(j-1,j)[6]
    if not sell[held].all():
        return np.nan,"BLOCKED_EXIT",info["buy"]
    return c+(u[held]*inp.o[j,held]).sum()*(1-FEES[1])-1,"OK",info["buy"]


def account_summary(nav):
    vals=nav.to_numpy()
    draw=vals/np.maximum.accumulate(np.r_[1.,vals])[1:]-1
    return dict(days=len(vals),end=nav.index[-1],cumulative=vals[-1]-1,cagr=vals[-1]**(252/len(vals))-1,
                max_drawdown=draw.min())


def evaluate():
    for name,digest in json.loads((D/"selection.json").read_text()).items():
        assert sha(D/name)==digest,name
    inp=Inputs()
    marks(inp,0.)
    m=pd.read_parquet(D/"monthly_candidates.parquet")
    match=pd.read_csv(D/"matches.csv",parse_dates=["signal_date"])
    random=pd.read_csv(D/"random_targets.csv.gz",parse_dates=["signal_date"],keep_default_na=False)
    s=pd.read_csv(D/"schedule.csv",parse_dates=["signal_date"]).set_index("signal_date")
    maps={name:{} for name in MODELS+["DD"]}
    events, switches, info=[],[],[]
    for date,g in m.groupby("signal_date"):
        i=inp.days.get_loc(date)+1
        groups={name:g.loc[g[name+"_q5"],"instrument"].tolist() for name in MODELS}
        dd=g.loc[g.E1_q5 & g.dd.eq(1),"instrument"].tolist()
        groups["DD"]=dd
        for name,names in groups.items():
            maps[name][date]=target(inp,names)
        pairs=match[match.signal_date==date]
        legs={"match_dd":pairs.selected.tolist(),"match_control":pairs.peer.tolist(),"dd":dd,
              "other":g.loc[g.E1_q5 & g.dd.eq(0),"instrument"].tolist()}
        for new,old in [("flag","E1"),("interaction","flag")]:
            for leg,a,b in [("in",new,old),("out",old,new)]:
                names=sorted(set(groups[a])-set(groups[b]))
                legs[new+"_"+leg]=names
                switches.extend(dict(signal_date=date,comparison=new,side=leg,instrument=n) for n in names)
        row=dict(signal_date=date,entry=inp.days[i],exit=inp.days[i+10] if i+10<len(inp.days) else pd.NaT,
                 matched=len(pairs),unique_peers=pairs.peer.nunique(),matched_dd_share=len(pairs)/len(dd) if dd else np.nan,
                 matched_q5_budget=len(pairs)/len(groups["E1"]))
        for name,names in legs.items():
            ret,reason,filled=h10(inp,i,names)
            row[name]=ret
            row[name+"_reason"]=reason
            row[name+"_deployed"]=filled
            row[name+"_n"]=len(names)
        for col,a,b in [("A","match_dd","match_control"),("B","dd","other"),
                        ("flag_switch","flag_in","flag_out"),("interaction_switch","interaction_in","interaction_out")]:
            row[col]=row[a]-row[b]
        events.append(row)
    monthly=s.join(pd.DataFrame(events).set_index("signal_date"),validate="1:1")
    monthly.to_csv(D/"monthly.csv")
    pd.DataFrame(switches).to_csv(D/"switches.csv",index=False)
    navs={}
    details=[]
    for name,mapping in maps.items():
        daily,orders,fail=run_account(inp,mapping,sorted(mapping),FEES,end=END)
        details.append(daily.assign(model=name))
        navs[name]=daily.set_index("date").nav
        orders.to_parquet(D/(name+"_orders.parquet"),index=False)
        info.append(dict(model=name,days=len(daily),failures=fail))
        flow=(orders.units_after-orders.units_before)*orders.price
        orderfees=(flow.clip(lower=0)*FEES[0]-flow.clip(upper=0)*FEES[1]).groupby(orders.date).sum()
        assert np.allclose(daily.set_index("date").fees.loc[orderfees.index],orderfees)
        assert daily.cash_weight.min() >= -1e-10
        if name in ["DD","E1"]:
            old=pd.read_csv(OLD/(name+"_daily.csv"),parse_dates=["date"]).set_index("date").nav
            assert old.index.equals(navs[name].index) and np.allclose(old,navs[name],atol=1e-11,rtol=0)
    save_json(D/"account_receipts.json",info)
    pd.concat(details).to_parquet(D/"daily_accounts.parquet",index=False)
    nav=pd.concat(navs,axis=1)
    nav["H00300"]=benchmark(nav.index)
    nav.to_csv(D/"daily_nav.csv")
    metrics=[]
    periods=[]
    last_common=nav[MODELS].dropna().index.max()
    for end,name in [(PRIMARY,"primary"),(END,"full")]:
        panel=nav.loc[:min(end,last_common)].dropna()
        for model,values in panel.items():
            stats=account_summary(values)
            metrics.append(dict(scope=name,model=model,planned_end=end,**stats,
                                cagr_minus_index=stats["cagr"]-account_summary(panel.H00300)["cagr"]))
        rets=panel.pct_change()
        rets.iloc[0]=panel.iloc[0]-1
        for freq in ["M","Y"]:
            compounded=(1+rets).groupby(rets.index.to_period(freq)).prod()-1
            periods.extend(compounded.assign(period=compounded.index.astype(str),frequency=freq,scope=name).to_dict("records"))
    pd.DataFrame(metrics).to_csv(D/"accounts.csv",index=False)
    pd.DataFrame(periods).to_csv(D/"account_periods.csv",index=False)
    draws=[]
    random_nav={}
    for n,g in random.groupby("draw"):
        mapping={r.signal_date:target(inp,r.instruments.split("|") if r.instruments else []) for r in g.itertuples()}
        daily,_,fail=run_account(inp,mapping,sorted(mapping),FEES,end=END,keep_orders=False)
        v=daily.set_index("date").nav
        random_nav[n]=v
        for end,scope in [(PRIMARY,"primary"),(END,"full")]:
            draws.append(dict(draw=n,scope=scope,complete=v.index[-1]>=end,
                              stop_reason=fail[0]["reason"] if fail and v.index[-1]<end else "",**account_summary(v.loc[:end])))
    pd.concat(random_nav,axis=1).to_parquet(D/"random_nav.parquet")
    pd.DataFrame(draws).to_csv(D/"random_accounts.csv",index=False)
    # Official label availability is used only for evaluation, never for target selection.
    pred=pd.read_parquet(D/"weekly_predictions.parquet")
    labels=pd.read_parquet(PRIVATE/"labels.parquet",columns=KEY+["h10","h10_mature"])
    p=pred.merge(labels,on=KEY,validate="1:1")
    rows=[]
    for date,g in p.groupby("signal_date"):
        known=g.dropna(subset=["h10"])
        values=known[MODELS+["h10"]].rank().corr().h10 if len(known)>=100 else {}
        rows.append(dict(signal_date=date,maturity=g.h10_mature.max(),n=len(known),
                         **{m:values.get(m,np.nan) for m in MODELS}))
    pd.DataFrame(rows).to_csv(D/"weekly_ic.csv",index=False)
    print("Evaluated pairs, accounts, 100 placebo paths and weekly RankIC",flush=True)


if __name__=="__main__":
    evaluate()

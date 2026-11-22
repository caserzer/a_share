"""Paired calendar-block inference and auditable descriptive tables."""
import json

import numpy as np
import pandas as pd
from prepare import ROOT, D, EP, MODELS, PRIMARY, END, SEED, sha, save_json


def blocks(n, width):
    rng=np.random.default_rng(SEED)
    starts=rng.integers(n,size=(4000,(n+width-1)//width))
    return ((starts[:,:,None]+np.arange(width))%n).reshape(4000,-1)[:,:n]


def estimate(a, predictors):
    a=a[np.isfinite(a).all(axis=1)]
    if not predictors:
        return a[:,0].mean() if len(a) else np.nan
    if len(a)<max(6,2*(1+len(predictors))):
        return np.nan
    x=np.column_stack([np.ones(len(a)),a[:,1:]])
    if np.linalg.matrix_rank(x)<x.shape[1]:
        return np.nan
    return np.linalg.lstsq(x,a[:,0],rcond=None)[0][1]*.1


def inference(f,y,predictors,block=3):
    a=f[[y]+predictors].to_numpy(dtype=float)
    val=estimate(a,predictors)
    valid=np.isfinite(a).all(axis=1)
    row=dict(n=int(valid.sum()),calendar=len(a),estimate=val,low=np.nan,high=np.nan,p=np.nan)
    if valid.sum()<6 or not np.isfinite(val):
        return row
    ix=blocks(len(a),block)
    if not predictors:
        samples=a[ix,0]
        counts=np.isfinite(samples).sum(axis=1)
        boot=np.nansum(samples,axis=1)[counts>0]/counts[counts>0]
    else:
        boot=np.array([estimate(a[i],predictors) for i in ix])
        boot=boot[np.isfinite(boot)]
    if len(boot):
        row.update(low=np.quantile(boot,.025),high=np.quantile(boot,.975),
                   p=(1+sum(abs(boot-val)>=abs(val)))/(1+len(boot)))
    return row


def group_name(values):
    return pd.cut(values,[-np.inf,.2,.4,np.inf],right=False,labels=["<20%","20%-<40%",">=40%"])


def run():
    monthly=pd.read_csv(D/"monthly.csv",parse_dates=["signal_date","entry","exit"])
    accts=pd.read_parquet(D/"daily_accounts.parquet")
    nav=accts.pivot(index="date", columns="model", values="nav")
    # Each decision interval begins before its own fees and ends before next entry fees.
    for name in MODELS:
        daily=accts[accts.model.eq(name)].set_index("date")
        pre=daily.pretrade_nav.reindex(monthly.entry)
        monthly[name+"_cycle"]=pre.shift(-1).to_numpy()/pre.to_numpy()-1
        ends=monthly.entry.shift(-1)
        last=monthly.index[-1]
        if daily.index[-1]==END:
            monthly.loc[last,name+"_cycle"]=daily.nav.iloc[-1]/pre.iloc[-1]-1
    monthly["cycle_end"]=ends.fillna(END)
    monthly["interaction_minus_flag_cycle"]=monthly.interaction_cycle-monthly.flag_cycle
    monthly["breadth_bin"]=group_name(monthly.breadth)
    monthly.to_csv(D/"decision_periods.csv",index=False)
    ic=pd.read_csv(D/"weekly_ic.csv",parse_dates=["maturity"])
    account=pd.read_csv(D/"accounts.csv",parse_dates=["end"])
    draw=pd.read_csv(D/"random_accounts.csv")
    rand=pd.read_parquet(D/"random_nav.parquet")
    periods=pd.read_csv(D/"account_periods.csv")
    coeffs,averages,bins,placebo,stats,stability=[],[],[],[],[],[]
    for start,end,scope in [(pd.Timestamp.min,PRIMARY,"primary"),(pd.Timestamp.min,END,"full"),(PRIMARY,END,"later")]:
        f=monthly[(monthly.exit<=end)&(monthly.entry>start)].copy()
        cycle=monthly[(monthly.cycle_end<=end)&(monthly.entry>start)].copy()
        for outcome in ["A","B"]:
            for controls in [["breadth"],["breadth_ex_q5"],["breadth","q5_share","dd_max_industry"]]:
                coeffs.append(dict(scope=scope,outcome=outcome,spec="+".join(controls),**inference(f,outcome,controls)))
            valid=f.dropna(subset=[outcome])
            for _,r in valid.iterrows():
                stats_loo=estimate(f.loc[f.signal_date.ne(r.signal_date),[outcome,"breadth"]].to_numpy(),["breadth"])
                stability.append(dict(scope=scope,outcome=outcome,omitted_date=r.signal_date,slope=stats_loo))
        for outcome in ["A","B","interaction_switch","flag_switch"]:
            averages.append(dict(scope=scope,stat=outcome,**inference(f,outcome,[])))
        for label,sub in f.groupby("breadth_bin",observed=False):
            cc=cycle[cycle.breadth_bin==label]
            bins.append(dict(scope=scope,bin=label,decisions=len(sub),A_n=sub.A.count(),A=sub.A.mean(),
                             B_n=sub.B.count(),B=sub.B.mean(),mean_count=sub["count"].mean(),
                             switch_n=sub.interaction_switch.count(),switch=sub.interaction_switch.mean(),
                             cycle_n=cc.interaction_minus_flag_cycle.count(),cycle=cc.interaction_minus_flag_cycle.mean()))
        valid_ic=ic[ic.maturity.le(end)&pd.to_datetime(ic.signal_date).gt(start)].copy()
        valid_ic["ic_gain"]=valid_ic.interaction-valid_ic.flag
        averages.append(dict(scope=scope,stat="weekly_ic_gain",**inference(valid_ic,"ic_gain",[],block=6)))
        stats.extend(dict(scope=scope,model=m,n=valid_ic[m].count(),mean_ic=valid_ic[m].mean()) for m in MODELS)
        averages.append(dict(scope=scope,stat="cycle_interaction_minus_flag",**inference(cycle,"interaction_minus_flag_cycle",[])))
        if scope=="later":
            continue
        common_end=account.loc[account.scope.eq(scope),"end"].min()
        calendar_month=periods[(periods.scope==scope)&(periods.frequency=="M")].copy()
        calendar_month["net_gain"]=calendar_month.interaction-calendar_month.flag
        averages.append(dict(scope=scope,stat="calendar_month_interaction_minus_flag",**inference(calendar_month,"net_gain",[])))
        actual=account[(account.scope==scope)&(account.model=="DD")].iloc[0]
        for metric in ["cumulative","max_drawdown"]:
            complete=draw[(draw.scope==scope)&draw.complete][metric]
            placebo.append(dict(scope=scope,metric=metric,actual=actual[metric],complete=len(complete),
                                p05=complete.quantile(.05),median=complete.median(),p95=complete.quantile(.95),
                                at_or_below=(complete<=actual[metric]).sum(),end=end))
        # Include all 100 paths on their common endpoint for a censoring sensitivity.
        all_days=rand.loc[:end].dropna()
        v=all_days.iloc[-1]-1
        dd=nav.DD.loc[all_days.index[-1]]-1
        placebo.append(dict(scope=scope,metric="cumulative_all_common",actual=dd,complete=len(v),p05=v.quantile(.05),
                            median=v.median(),p95=v.quantile(.95),at_or_below=sum(v<=dd),end=all_days.index[-1]))
    slopes=pd.DataFrame(coeffs)
    primary=slopes[(slopes.scope=="primary")&(slopes.spec=="breadth")].sort_values("p")
    assert len(primary)==2
    adjusted=np.maximum.accumulate(primary.p.to_numpy()*[2,1]).clip(0,1)
    slopes.loc[primary.index,"holm_p"]=adjusted
    for name,table in [("slopes",slopes),("paired_means",averages),("breadth_bands",bins),("placebo",placebo),
                       ("ic_summary",stats),("leave_one_out",stability)]:
        pd.DataFrame(table).to_csv(D/(name+".csv"),index=False)
    print(slopes[slopes.scope=="primary"].to_string(index=False))
    print(pd.DataFrame(placebo).to_string(index=False))
    print(account[["scope","model","cagr","max_drawdown","end"]].to_string(index=False))


if __name__=="__main__":
    run()

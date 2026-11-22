"""Verify sealed inputs, baseline replay, per-pair eligibility and benchmark alignment."""
import json
import numpy as np
import pandas as pd
from select_targets import D, PREV, PRIVATE, MAIN, END, SCORE, sha, dump


def main():
    for name,h in json.loads((D/"inputs.json").read_text()).items():
        assert sha(name)==h,name
    for name,h in json.loads((D/"selection.json").read_text()).items():
        assert sha(D/name)==h,name
    p=pd.read_parquet(D/"ranks_targets.parquet").set_index(["signal_date","instrument"])
    matches=pd.read_csv(D/"matches.csv",parse_dates=["signal_date"])
    assert not matches.duplicated(["signal_date","entrant"]).any() and not matches.duplicated(["signal_date","stayer"]).any()
    for r in matches.itertuples():
        a=p.loc[r.signal_date,r.entrant]
        b=p.loc[r.signal_date,r.stayer]
        assert a.industry==b.industry==r.industry and a.role=="enter" and b.role=="stay"
        assert a.prev_d<10 and b.prev_d==10 and abs(a.tilt/a.base-1.5)<1e-11 and abs(b.tilt/b.base-.5)<1e-11
        assert abs(r.score_gap_sd)<=.25+1e-12 and max(abs(r.mom5_gap_sd),abs(r.mom20_gap_sd))<=.5+1e-12
    windows=pd.read_csv(D/"windows.csv",parse_dates=["signal_date","entry_date","exit_date"])
    old=pd.read_csv(PREV/"results/primary_100_windows.csv",parse_dates=["signal_date"])
    primary=windows[windows.exit_date.le(MAIN)].copy()
    assert np.allclose(primary.prior_comparison,old.new_minus_out,equal_nan=True,rtol=0,atol=1e-12)
    ledger=pd.read_parquet(D/"daily.parquet").query("model=='base'")
    old_nav=pd.read_parquet(PREV/"results/nav.parquet").query("model=='RANK_MSE_78' and style=='net'")
    max_nav=0.
    for k,g in ledger.groupby(["scope","mode","cost"]):
        ref=old_nav[(old_nav.scope==k[0])&(old_nav["mode"]==k[1])&(old_nav.cost==k[2])]
        assert np.array_equal(ref.date,g.date)
        err=np.max(abs(ref.nav.to_numpy()-g.nav.to_numpy()))
        assert err<1e-11
        max_nav=max(max_nav,err)
    a=pd.read_csv(D/"accounts.csv")
    ref=json.loads((PRIVATE/"net_excess_20261116/H00300.CSI.json").read_text())["data"]
    idx=pd.DataFrame(ref["items"],columns=ref["fields"]).set_index("trade_date")
    ratio=float(idx.loc["20250303","close"])/float(idx.loc["20210108","close"])
    price=pd.read_parquet(PRIVATE/"market.parquet").open
    price_ratio=price.loc[MAIN]/price.loc["2021-01-11"]
    rows=[]
    for r in a.query("scope=='primary' and mode=='flat' and cost=='main'").itertuples():
        rows.append(dict(model=r.model,close_return=r.closing_nav-1,total_index_cagr=ratio**(252/r.days)-1,
                         cagr_difference=r.closing_nav**(252/r.days)-ratio**(252/r.days),price_index_open_cagr=price_ratio**(252/(r.days-1))-1))
    pd.DataFrame(rows).to_csv(D/"benchmark.csv",index=False)
    sensitivity=[]
    for scope,g in [("primary",primary),("later",windows[windows.entry_date.ge(MAIN)&windows.exit_date.le(END)])]:
        m=g.dropna(subset=["matched_gap"])
        for name,sub in [("all",m),("one_pair",m[m.pairs==1]),("multiple_pairs",m[m.pairs>1])]:
            sensitivity.append(dict(scope=scope,group=name,dates=len(sub),pairs=sub.pairs.sum(),mean=sub.matched_gap.mean(),
                                    median=sub.matched_gap.median(),win_rate=(sub.matched_gap>0).mean(),
                                    pair_weighted_mean=np.average(sub.matched_gap,weights=sub.pairs) if len(sub) else np.nan))
    pd.DataFrame(sensitivity).to_csv(D/"support_sensitivity.csv",index=False)
    dump(D/"validation.json",dict(input_hashes_verified=True,selection_hashes_verified=True,old_new_minus_exit_100_dates_replayed=True,
         old_nav_branches=ledger.groupby(["scope","mode","cost"]).ngroups,max_baseline_error=max_nav,
         total_pairs_verified=len(matches),maximum_cash_nav_reconstruction_error=a.ledger_error.max(),
         fully_mature_windows=int(windows.exit_date.le(END).sum()),primary_windows=len(primary)))


if __name__=="__main__":
    main()

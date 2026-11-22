"""Apply the precommitted matches; reuse the exact previous round's net ledger code."""
import json
import numpy as np
import pandas as pd
from prepare import ROOT,D,RANK,EP,PRIVATE,MAIN,END,SCORE,sha,dump,clean
from importlib.util import spec_from_file_location, module_from_spec

spec=spec_from_file_location("rank_change_accounts",RANK/"evaluate.py")
previous=module_from_spec(spec)
spec.loader.exec_module(previous)
import accounts
from core import bootstrap,holm


def run():
    for f,h in json.loads((D/"selection.json").read_text()).items():
        assert sha(D/f)==h
    previous.D=D
    accounts.OUT=D
    m=accounts.Market()
    p=pd.read_parquet(D/"panel.parquet")
    cal=p[["signal_date","entry_date","exit_date"]].drop_duplicates().sort_values("signal_date")
    pairs=pd.read_csv(D/"pairs.csv",parse_dates=["signal_date"])
    rec=[]
    subsets=["all","top20","top10","fresh","stale","pullback"]
    for date,g in p[p.exit_date.le(END)].groupby("signal_date"):
        matched=pairs[pairs.signal_date.eq(date)]
        row=dict(signal_date=date)
        for tag,sub in zip(subsets,[matched,matched[matched.decile>=9],matched[matched.decile==10],
                               matched[matched.fresh],matched[matched.stale],matched[matched.pullback]]):
            row[tag+"_pairs"]=len(sub)
            for sign in ["positive","negative"]:
                basket=g[g.instrument.isin(sub[sign])]
                assert len(basket)==len(sub)
                stats=previous.leg(m,basket)
                row.update({tag+"_"+sign+"_"+k:v for k,v in stats.items()})
            row[tag+"_gap"]=row[tag+"_positive_net"]-row[tag+"_negative_net"]
        row["shifted_budget"]=(g.tilt-g.base).abs().sum()/2
        rec.append(row)
    frame=cal.merge(pd.DataFrame(rec),on="signal_date",how="left",validate="1:1")
    frame["account_gap"]=frame.signal_date.map(previous.continuous(p,m,cal))
    frame.to_csv(D/"windows.csv",index=False)
    rows=[]
    groups=[("primary",frame[frame.exit_date.le(MAIN)]),("later",frame[frame.entry_date.ge(MAIN)&frame.exit_date.le(END)]),
            ("all",frame[frame.exit_date.le(END)])]
    groups += [(str(y),g) for y,g in frame[frame.exit_date.le(END)].groupby(frame.signal_date.dt.year)]
    for scope,h in groups:
        for metric in [tag+"_gap" for tag in subsets]+(["account_gap"] if scope=="primary" else []):
            rows.append(dict(scope=scope,metric=metric,**bootstrap(h[metric].to_numpy())))
    tests=pd.DataFrame(rows)
    fam=tests.scope.eq("primary")&tests.metric.isin(["all_gap","account_gap"])
    tests.loc[fam,"holm_p"]=holm(tests.loc[fam,"p"])
    tests.to_csv(D/"tests.csv",index=False)
    print(tests[fam].to_string(index=False))


if __name__=="__main__":
    run()

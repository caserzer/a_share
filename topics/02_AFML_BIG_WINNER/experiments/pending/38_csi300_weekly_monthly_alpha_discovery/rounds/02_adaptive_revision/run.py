"""Replay the second EP38 iteration with only information known at signal close."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EP = ROOT.parent/"37_momentum_reversal_joint_alpha_h10"
EXT = EP/"extensions/intraday_reversal_20261122"
sys.path[:0] = [str(EP/"code"),str(EXT)]
import accounts
from core import PRIVATE, sha, dump
from execution import net_account
OUT = HERE/"results"
OUT.mkdir(exist_ok=True)
accounts.OUT = OUT
R,E = "RANK_MSE_78","E1_78"
base = pd.read_parquet(ROOT/"results/targets.parquet").query("model in [@R,@E]")
events = pd.read_csv(ROOT/"results/events.csv",parse_dates=["signal_date"])
returns = events.pivot(index="signal_date",columns="model",values="net_return")
cal = base.drop_duplicates("signal_date").set_index("signal_date").sort_index()
edge = returns[E]-returns[R]
source = ROOT.parent/"35_industry_rise_mechanisms_and_rotation/data/r11_analyst_forecasts.parquet"
reports = pd.read_parquet(source).query("basis=='profit_cny'").copy()
keys = ["stock_code","broker","fiscal_year","publication_proxy_date"]
# Drop ambiguous same-date estimates, retaining the date as an unknown predecessor.
est = reports.groupby(keys).value.agg(["min","max"]).reset_index().sort_values(keys)
est["value"] = est["min"].where(est["min"]==est["max"])
for col in ["publication_proxy_date","value"]:
    est["prev_"+col] = est.groupby(keys[:-1])[col].shift()
est["revision"] = est.value/est.prev_value-1
est = est.loc[(est.value>0)&(est.prev_value>0)&((est.publication_proxy_date-est.prev_publication_proxy_date).dt.days<=365)]
targets=[]; decisions=[]; snapshots=[]
for date,g in base.groupby("signal_date"):
    rank = g[g.model==R].copy()
    orig = g[g.model==E].copy()
    old = edge[cal.exit_date.le(date)].dropna().tail(6)
    switch = len(old)==6 and old.mean()>0
    obs = est[(est.publication_proxy_date<date)&(est.publication_proxy_date>=date-pd.Timedelta(days=60))&est.fiscal_year.isin([date.year,date.year+1])]
    obs = obs.sort_values(["publication_proxy_date","fiscal_year"],ascending=[True,False]).drop_duplicates(["stock_code","broker"],keep="last")
    signal = obs.groupby("stock_code").revision.median()
    revisions = rank.instrument.str[2:].map(signal)
    snapshots.append(obs.assign(signal_date=date))
    for model,flag in [("revision",revisions.lt(0)),("coverage",revisions.notna())]:
        t=rank.copy()
        if flag.any() and not flag.all():
            freed=t.loc[flag,"weight"].sum()/2
            t.loc[flag,"weight"]*=.5
            t.loc[~flag,"weight"]+=freed/(~flag).sum()
        targets.append(t.assign(model=model))
    targets.extend([rank,orig,(orig if switch else rank).assign(model="adaptive")])
    decisions.append(dict(signal_date=date,switch=switch,edge_forecast=old.mean() if len(old)==6 else np.nan,
        last_label_exit=cal.loc[old.index,"exit_date"].max(),covered=revisions.notna().sum(),negative=revisions.lt(0).sum(),
        eligible=len(rank),subsequent_event_edge=edge.get(date,np.nan)))
t=pd.concat(targets,ignore_index=True)
assert np.allclose(t.groupby(["signal_date","model"]).weight.sum(),1)
dec=pd.DataFrame(decisions)
assert (dec.dropna(subset=["last_label_exit"]).last_label_exit<=dec.dropna(subset=["last_label_exit"]).signal_date).all()
t.to_parquet(OUT/"targets.parquet",index=False)
pd.concat(snapshots).to_parquet(OUT/"revision_sources.parquet",index=False)
dec.to_csv(OUT/"decisions.csv",index=False)
dump(OUT/"selection.json",{str(p.relative_to(ROOT.parent)):sha(p) for p in [source,ROOT/"results/targets.parquet",ROOT/"results/events.csv",HERE/"PROTOCOL.md",Path(__file__),OUT/"targets.parquet"]})

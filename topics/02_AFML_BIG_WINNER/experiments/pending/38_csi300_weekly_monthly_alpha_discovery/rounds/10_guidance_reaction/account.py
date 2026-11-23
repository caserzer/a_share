from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import evaluate,PRIVATE,EP,R,E
from core import sha,dump
OUT=HERE/"results/account";OUT.mkdir(parents=True,exist_ok=True)
src=ROOT.parent/"24_conditional_return_distribution_exploration/outputs/r37_exchange_guidance"
universe=set(pd.read_csv(src/"stock_coverage.csv").instrument)
# Only date, identifier and the reaction already observed at that close enter selection.
ev=pd.read_csv(HERE/"results/matched_events.csv",usecols=["signal_date","stock","relative"],parse_dates=["signal_date"])
base=pd.read_parquet(ROOT/"results/targets.parquet").query("model in [@R,@E]")
scores=pd.read_parquet(EP/"extensions/intraday_reversal_20261122/results/scores.parquet").dropna(subset=["exit_date"])
days=pd.read_parquet(PRIVATE/"qfq_close.parquet",columns=[]).index
industry=pd.read_parquet(PRIVATE/"industry.parquet")
industry["instrument"]=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
parts=[base];swaps=[]
for date,g in scores.groupby("signal_date"):
    key=date.strftime("%Y%m%d");i=days.get_loc(date)
    active=industry[industry.in_date.le(key)&(industry.out_date.isna()|industry.out_date.gt(key))]
    lookup=active[["instrument","l1_name"]].drop_duplicates()
    lookup=lookup[~lookup.instrument.duplicated(False)].set_index("instrument").l1_name
    obs=ev[(ev.signal_date>=days[i-9])&(ev.signal_date<=date)].sort_values("signal_date").drop_duplicates("stock",keep="last")
    g=g.set_index("instrument").copy()
    g["sector"]=lookup.reindex(g.index)
    g["reaction"]=np.sign(obs.set_index("stock").relative.reindex(g.index)).fillna(0)
    g["pct"]=g[R].rank(pct=True)
    held=g[g[R+"_d"]==10]
    pool=g[g[R+"_d"].eq(9)&g.index.isin(universe)]
    proposals=[]
    if date<=pd.Timestamp("2026-04-30"):
        for sector,h in held[held.index.isin(universe)].groupby("sector"):
            h=h.sort_values(["reaction","pct"],kind="stable")
            new=pool[pool.sector==sector].sort_values(["reaction","pct"],ascending=False,kind="stable")
            for (stock,old),(incoming,nxt) in zip(h.iterrows(),new.iterrows()):
                gap=nxt.reaction-old.reaction
                if gap<=0:break
                proposals.append(dict(signal_date=date,sector=sector,old=stock,new=incoming,gap=gap,old_sign=old.reaction,
                                      new_sign=nxt.reaction,rank_loss=old.pct-nxt.pct,weight=1/len(held)))
    chosen=set(held.index)
    for pair in sorted(proposals,key=lambda x:(-x["gap"],x["rank_loss"],x["new"]))[:len(held)//5]:
        chosen.remove(pair["old"]);chosen.add(pair["new"]);swaps.append(pair)
    target=g.loc[sorted(chosen)]
    assert target.sector.value_counts().to_dict()==held.sector.value_counts().to_dict()
    parts.append(target.reset_index().assign(model="guidance",weight=1/len(held)))
pd.concat(parts,ignore_index=True).to_parquet(OUT/"targets.parquet",index=False)
pd.DataFrame(swaps).to_csv(OUT/"swaps.csv",index=False)
dump(OUT/"selection.json",{str(f):sha(f) for f in [HERE/"ACCOUNT_PROTOCOL.md",Path(__file__),HERE/"results/matched_events.csv",OUT/"targets.parquet",src/"stock_coverage.csv"]})
evaluate(OUT,21)

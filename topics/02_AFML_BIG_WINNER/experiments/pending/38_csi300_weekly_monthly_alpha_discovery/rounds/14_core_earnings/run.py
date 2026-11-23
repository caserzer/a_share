from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import EP,R,E,PRIVATE,evaluate
from core import sha,dump
OUT=HERE/"results";OUT.mkdir(exist_ok=True)
src=ROOT.parent/"24_conditional_return_distribution_exploration/outputs/local_cache/public_financials"
sf=EP/"extensions/intraday_reversal_20261122/results/scores.parquet"
base=pd.read_parquet(ROOT/"results/targets.parquet").query("model in [@R,@E]")
p=pd.read_parquet(sf).dropna(subset=["exit_date"])
fin=[];hashes={}
cols=["REPORT_DATE","NOTICE_DATE","UPDATE_DATE","DJD_DEDUCTDPNP_YOY","SECUCODE"]
for sym in sorted(set(p.instrument)):
    f=src/(sym[2:]+"."+sym[:2]+".parquet")
    if not f.is_file():continue
    import pyarrow.parquet as pq
    if not set(cols).issubset(pq.ParquetFile(f).schema.names):continue
    a=pd.read_parquet(f,columns=cols);hashes[f.name]=sha(f)
    assert set(a.SECUCODE.dropna())<=set([f.stem])
    for c in cols[:3]:a[c]=pd.to_datetime(a[c],errors="coerce")
    a["growth"]=pd.to_numeric(a.DJD_DEDUCTDPNP_YOY,errors="coerce")
    a=a.dropna(subset=cols[:3])
    a["available"]=a[["NOTICE_DATE","UPDATE_DATE"]].max(axis=1)
    a=a[a.REPORT_DATE<=a.NOTICE_DATE].copy()
    a["growth"]=a.growth.where(np.isfinite(a.growth))
    fin.append(a.assign(instrument=sym))
facts=pd.concat(fin,ignore_index=True)
industry=pd.read_parquet(PRIVATE/"industry.parquet")
industry["instrument"]=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
targets=[base];coverage=[];audit=[]
for date,g in p.groupby("signal_date"):
    q=facts[(facts.available<date)&(facts.REPORT_DATE>=date-pd.Timedelta(days=300))]
    q=q.sort_values(["instrument","REPORT_DATE","available"])
    dup=q.duplicated(["instrument","REPORT_DATE","available"],keep=False)
    q.loc[dup,"growth"]=np.nan
    q=q.drop_duplicates(["instrument","REPORT_DATE"],keep="last").copy()
    q["quarter"]=q.REPORT_DATE.dt.to_period("Q").astype("int64")
    prev=q.groupby("instrument")
    q["change"]=(q.growth-prev.growth.shift()).where(q.quarter-prev.quarter.shift()==1)
    q["prior_available"]=prev.available.shift()
    q=q.drop_duplicates("instrument",keep="last")
    q=q[(q.NOTICE_DATE>=date-pd.Timedelta(days=120))&(q.REPORT_DATE>=date-pd.Timedelta(days=180))&q.change.notna()]
    key=date.strftime("%Y%m%d")
    a=industry[industry.in_date.le(key)&(industry.out_date.isna()|industry.out_date.gt(key))]
    lookup=a[["instrument","l1_name"]].drop_duplicates()
    g=g.merge(q[["instrument","growth","change","available","prior_available","REPORT_DATE"]],on="instrument",how="left",validate="1:1")
    g["industry"]=g.instrument.map(lookup[~lookup.instrument.duplicated(False)].set_index("instrument").l1_name)
    g["pct"]=g[R].rank(pct=True)
    top=g[g[R+"_d"]==10]
    pool=g[g[R+"_d"]>=9].copy()
    for signal in ["change","growth"]:
        group=g.groupby("industry")[signal]
        n=group.transform("count")
        centered=((group.rank() - 1)/(n-1)-.5).where(n>=3)
        g[signal+"_adj"]=centered
        pool["order"]=pool.pct+.1*centered.loc[pool.index].fillna(0)
        pieces=[top[top.industry.isna()]]
        for sector,k in top.industry.value_counts().items():
            pieces.append(pool[pool.industry==sector].sort_values(["order","instrument"]).tail(k))
        h=pd.concat(pieces)
        targets.append(h.assign(model="earnings_"+signal,weight=1/len(h)))
    coverage.append(dict(date=date,n=len(g),known=g.change_adj.count(),top_known=g.loc[top.index,"change_adj"].count(),top=len(top)))
    audit.append(g[["signal_date","instrument","industry","REPORT_DATE","available","prior_available","growth","change","growth_adj","change_adj"]])
pd.concat(audit).to_parquet(OUT/"signals.parquet",index=False)
pd.DataFrame(coverage).to_csv(OUT/"coverage.csv",index=False)
pd.concat(targets).to_parquet(OUT/"targets.parquet",index=False)
dump(OUT/"selection.json",dict(financial_hashes=hashes,inputs={str(f):sha(f) for f in [sf,HERE/"PROTOCOL.md",Path(__file__),OUT/"targets.parquet",OUT/"signals.parquet"]}))
evaluate(OUT,24)

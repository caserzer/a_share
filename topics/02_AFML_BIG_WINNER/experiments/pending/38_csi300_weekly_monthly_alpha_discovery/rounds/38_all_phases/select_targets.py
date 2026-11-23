from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent
root=here.parents[1]
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(root/"forward/industry_pool_v1")]
from evaluate import R,E,EP,PRIVATE,split
from core import sha,dump
from capture import select,ANCHOR,METHODS
old=EP/"extensions/original78_rankic_20261118"
sys.path[:0]=[str(old),str(PRIVATE.parent/"src")]
from features import compute
from model import predict

out=here/"results";out.mkdir(exist_ok=True)
fields=["qfq_close","qfq_open","qfq_high","qfq_low","volume","money","turnover_rate","daily_members"]
paths=[PRIVATE/(key+".parquet") for key in fields]
raw=[pd.read_parquet(p) for p in paths]
c=raw[0];days=c.index
market=PRIVATE/"market.parquet"
features=compute(*raw,pd.read_parquet(market).close)
warm=(c.gt(0)&np.isfinite(c)).rolling(61).sum().eq(61)
eligible=raw[-1]&warm&(c.shift(5)/c.shift(60)).ne(1)&(c/c.shift(5)).ne(1)
del raw
colsfile=old/"outputs/original_78_features.csv"
cols=pd.read_csv(colsfile).feature.tolist()
foldfile=old/"outputs/folds.csv"
folds=pd.read_csv(foldfile).set_index(["fold","model"])
models={}
indfile=PRIVATE/"industry.parquet"
ind=pd.read_parquet(indfile);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
hist={};inputs=[*paths,market,colsfile,foldfile,indfile,root/"forward/industry_pool_v1/capture.py",here/"PROTOCOL.md",Path(__file__)]
for method in METHODS:
    folder=root.parent/"34_industry_price_observation_radar/handoff/v3_candidates_20261016"/method/"periods"
    hist[method]={}
    for f in sorted(folder.glob("*.csv")):
        hist[method][pd.Timestamp(f.stem)]=pd.read_csv(f,usecols=["date","era","industry_code","industry_name","event_kind","candidate_version"])
        inputs.append(f)
saved_scores=here.parent/"17_calendar_challenge/results/point_in_time_scores.parquet"
reference=pd.read_parquet(saved_scores).set_index(["signal_date","instrument"])
inputs.append(saved_scores)
start=days.get_loc(ANCHOR);end=days.get_loc("2026-10-12")
holdings=[];audit=[];scores=[]
for i in range(start,end-10):
    day=days[i];entry=days[i+1];exitday=days[i+11]
    if entry<split<exitday:continue
    phase=(i-start)%10;quarter=str(day.to_period("Q"))
    names=eligible.columns[eligible.iloc[i]]
    f=pd.DataFrame({k:features[k].iloc[i].reindex(names) for k in cols})
    f=f.loc[f.notna().mean(axis=1)>=.8]
    g=pd.DataFrame(index=f.index)
    for ref in (R,E):
        key=(quarter,ref)
        if key not in models:
            path=old/"local_cache/models"/(quarter+"_"+ref+".json")
            row=folds.loc[key]
            assert sha(path)==row.model_sha256 and pd.Timestamp(row.max_label_maturity)<day
            models[key]=json.loads(path.read_text());inputs.append(path)
        g[ref]=predict(f,models[key])
    g.index.name="instrument"
    if phase in (0,5):
        expected=reference.loc[day,[R,E]].sort_index()
        pd.testing.assert_index_equal(g.sort_index().index,expected.index)
        np.testing.assert_allclose(g.sort_index(),expected,atol=1e-10,rtol=0)
    meta=dict(phase=phase,signal_date=day,entry_idx=i+1,exit_idx=i+11,entry_date=entry,exit_date=exitday)
    g=g.reset_index();scores.append(g.assign(**meta))
    tabs={}
    for method in METHODS:
        week=max(w for w in hist[method] if w<day)
        tabs[method]=(week,hist[method][week])
    picked,notes=select(g,ind,tabs,day)
    for method,positions in picked.items():
        holdings.extend(dict(**meta,model=method,instrument=k,weight=v) for k,v in positions.items())
    for method,data in notes.items():
        audit.append(dict(**meta,model=method,week=data["week"],compatible=data["compatible"],swaps=len(data["swaps"])))
t=pd.DataFrame(holdings)
for phase,folder in [(0,"16_industry_pool"),(5,"17_calendar_challenge")]:
    path=here.parent/folder/"results/targets.parquet";inputs.append(path)
    ids=["signal_date","instrument","model"]
    before=pd.read_parquet(path).set_index(ids).weight.sort_index()
    after=t[t.phase==phase].set_index(ids).weight.sort_index()
    pd.testing.assert_series_equal(before,after)
t.to_parquet(out/"targets.parquet",index=False)
pd.concat(scores).to_parquet(out/"scores.parquet",index=False)
pd.DataFrame(audit).to_csv(out/"coverage.csv",index=False)
dump(out/"selection_receipt.json",{str(f):sha(f) for f in [*inputs,out/"targets.parquet",out/"scores.parquet",out/"coverage.csv"]})
print(t.groupby("phase").signal_date.nunique(),flush=True)

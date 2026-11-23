"""Capture a shadow target before entry. Input scores are the complete EP37 eligible cross section."""
from pathlib import Path
from datetime import datetime,time
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import os
import tempfile
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PENDING=ROOT.parent
R,E="RANK_MSE_78","E1_78"
METHODS=("early_model","momentum")
ANCHOR=pd.Timestamp("2021-01-08")
TZ=ZoneInfo("Asia/Shanghai")
def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def select(scores,industry,catalogs,day):
    g=scores[["instrument",R,E]].copy().reset_index(drop=True)
    if len(g)<100 or g.instrument.duplicated().any() or not np.isfinite(g[[R,E]]).all().all():
        raise ValueError("Invalid eligible score cross section")
    tops={}
    for name in (E,R):
        order=g.sort_values([name,"instrument"],kind="stable").index
        g.loc[order,"decile"]=np.floor(10*np.arange(len(g))/len(g))+1
        tops[name]=set(g.loc[g.decile==10,"instrument"])
    key=day.strftime("%Y%m%d")
    a=industry[industry.in_date.le(key)&(industry.out_date.isna()|industry.out_date.gt(key))]
    mapping=a[["instrument","l1_name","l3_code","l3_name"]].drop_duplicates()
    g=g.merge(mapping[~mapping.instrument.duplicated(False)],on="instrument",how="left",validate="1:1")
    pairs=list(zip(g.l3_code,g.l3_name));audit={}
    for method in METHODS:
        week,tab=catalogs[method]
        if week>=day or tab.empty or tab.industry_code.duplicated().any() or not pd.to_datetime(tab.date).eq(week).all():
            raise ValueError("Invalid catalog date or industry identity")
        if not tab.candidate_version.eq("EP34-V3-CANDIDATE-"+method+"-20261112").all():
            raise ValueError("Unexpected catalog version")
        compatible=tab.era.eq("SW2021").all() and (day-week).days<=10
        obs=tab[tab.event_kind.isin(["NEW","UPDATE"])]
        if len(obs)>20:raise ValueError("Unexpected active pool size")
        allow=set(zip(obs.industry_code,obs.industry_name)) if compatible else set()
        known=set(zip(tab.industry_code,tab.industry_name)) if compatible else set()
        in_pool=np.array([p in allow for p in pairs])
        mapped=np.array([p in known for p in pairs])
        swaps=[]
        for sector,h in g[(g.decile==10)&~in_pool&mapped].groupby("l1_name"):
            entrants=g[(g.decile==9)&in_pool&g.l1_name.eq(sector)]
            for old,new in zip(h.sort_values(R).itertuples(),entrants.sort_values(R,ascending=False).itertuples()):
                swaps.append((getattr(old,R)-getattr(new,R),old.instrument,new.instrument))
        selected=tops[R].copy()
        chosen=sorted(swaps)[:len(selected)//5]
        for _,old,new in chosen:
            selected.remove(old);selected.add(new)
        tops[method]=selected
        audit[method]=dict(week=str(week.date()),compatible=bool(compatible),swaps=[(old,new) for _,old,new in chosen])
    targets={name:{stock:1/len(stocks) for stock in sorted(stocks)} for name,stocks in tops.items()}
    return targets,audit

def timing(day,calendar,now):
    dates=pd.DatetimeIndex(calendar)
    if not dates.is_monotonic_increasing or dates.has_duplicates:raise ValueError("Invalid trading calendar")
    i=dates.get_loc(day);phase=(i-dates.get_loc(ANCHOR))%10
    if phase not in (0,5) or i+1>=len(dates):raise ValueError("Off schedule or missing next entry date")
    entry=dates[i+1]
    if not datetime.combine(day.date(),time(15),TZ)<=now<datetime.combine(entry.date(),time(9,30),TZ):
        raise ValueError("Outside pre-entry capture window")
    return phase,entry

def write_once(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as tmp:
        name=Path(tmp.name)
        try:
            tmp.write(payload);tmp.flush();os.fsync(tmp.fileno())
            os.link(name,path)
        finally:name.unlink(missing_ok=True)

def capture(args):
    day=pd.Timestamp(args.signal_date)
    freeze=HERE/"freeze.json";spec=json.loads(freeze.read_text())
    if day<pd.Timestamp(spec["registration_date"]):raise ValueError("Before rule registration")
    for rel,h in spec["sha256"].items():
        if digest(ROOT/rel)!=h:raise ValueError("Frozen rule changed: "+rel)
    paths={k:getattr(args,k) for k in ["scores","industry","calendar"]}
    for method in METHODS:
        options=[(pd.Timestamp(p.stem),p) for p in (args.catalog/method/"periods").glob("????-??-??.csv")]
        _,paths[method]=max((d,p) for d,p in options if d<day)
    hashes={k:digest(p) for k,p in paths.items()}
    cal=pd.to_datetime(pd.read_csv(paths["calendar"],header=None).iloc[:,0])
    archived=PENDING/"36_csi300_alpha_discovery_and_index_enhancement/private/qfq_close.parquet"
    reference=pd.read_parquet(archived,columns=[]).index
    prefix=pd.DatetimeIndex(cal[(cal>=ANCHOR)&(cal<=reference[-1])])
    if not prefix.equals(reference[reference>=ANCHOR]):
        raise ValueError("Trading calendar disagrees with historical phase anchor")
    timing(day,cal,datetime.now(TZ))
    g=pd.read_parquet(paths["scores"],columns=["signal_date","instrument",R,E])
    g=g[pd.to_datetime(g.signal_date)==day]
    a=pd.read_parquet(paths["industry"]);a["instrument"]=a.ts_code.str[-2:]+a.ts_code.str[:6]
    tabs={k:(pd.Timestamp(paths[k].stem),pd.read_csv(paths[k])) for k in METHODS}
    targets,audit=select(g,a,tabs,day)
    if not all(a["compatible"] for a in audit.values()):
        raise ValueError("No current compatible industry catalog for this observation")
    if any(digest(p)!=hashes[k] for k,p in paths.items()):raise ValueError("Input changed during capture")
    now=datetime.now(TZ);phase,entry=timing(day,cal,now)
    record=dict(signal_date=str(day.date()),created_at=now.isoformat(),entry=str(entry.date()),phase=int(phase),
                freeze_sha256=digest(freeze),implementation_sha256=digest(Path(__file__)),eligible=len(g),
                inputs={k:dict(path=str(p.resolve()),sha256=hashes[k]) for k,p in paths.items()},targets=targets,audit=audit)
    output=HERE/"predictions"/(str(day.date())+".json")
    write_once(output,json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False).encode())
    print(output)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signal-date",required=True)
    for key in ("scores","industry","calendar","catalog"):parser.add_argument("--"+key,type=Path,required=True)
    capture(parser.parse_args())

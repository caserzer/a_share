"""Rebuild both historical phases without writing or backdating a prediction."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime
import pandas as pd
from capture import HERE,ROOT,PENDING,METHODS,select,timing,write_once,TZ,digest

def main():
    snap=PENDING/"34_industry_price_observation_radar/handoff/v3_candidates_20261016"
    sf=ROOT/"rounds/17_calendar_challenge/results/point_in_time_scores.parquet"
    scores=pd.read_parquet(sf)
    private=PENDING/"36_csi300_alpha_discovery_and_index_enhancement/private"
    ind=pd.read_parquet(private/"industry.parquet")
    ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
    catalogs={}
    for method in METHODS:
        catalogs[method]={pd.Timestamp(p.stem):pd.read_csv(p) for p in (snap/method/"periods").glob("*.csv")}
    count=holdings=0
    for phase,folder in [(0,"16_industry_pool"),(5,"17_calendar_challenge")]:
        targets=pd.read_parquet(ROOT/"rounds"/folder/"results/targets.parquet")
        for d,h in targets.groupby("signal_date"):
            tabs={}
            for method,history in catalogs.items():
                week=max(w for w in history if w<d)
                tabs[method]=(week,history[week])
            result,_=select(scores[(scores.signal_date==d)&(scores.offset==phase)],ind,tabs,d)
            expected={name:g.set_index("instrument").weight.to_dict() for name,g in h.groupby("model")}
            assert result==expected
            count+=1;holdings+=len(h)
    cal=pd.read_parquet(private/"qfq_close.parquet",columns=[]).index
    sample=pd.Timestamp("2021-01-08")
    assert timing(sample,cal,datetime(2021,1,8,16,tzinfo=TZ))[0]==0
    for invalid in [datetime(2021,1,8,14,tzinfo=TZ),datetime(2021,1,11,9,30,tzinfo=TZ)]:
        try:timing(sample,cal,invalid)
        except ValueError:pass
        else:raise AssertionError("accepted invalid capture time")
    with TemporaryDirectory() as td:
        dest=Path(td)/"one.json";write_once(dest,b"one")
        try:write_once(dest,b"two")
        except FileExistsError:pass
        else:raise AssertionError("overwrote capture")
        assert dest.read_bytes()==b"one"
    report=dict(historical_phase_dates=count,matched_stock_weights=holdings,all_four_portfolios_exact=True,
        latest_archived_score_by_phase={str(k):str(d.date()) for k,d in scores.groupby("offset").signal_date.max().items()},
        latest_catalog={k:str(max(h).date()) for k,h in catalogs.items()},calendar_end=str(cal.max().date()),
        registration_date=json.loads((HERE/"freeze.json").read_text())["registration_date"],
        existing_forward_receipts=len(list((HERE/"predictions").glob("*.json"))),capture_sha256=digest(HERE/"capture.py"))
    (HERE/"capture_verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(report)
if __name__=="__main__":main()

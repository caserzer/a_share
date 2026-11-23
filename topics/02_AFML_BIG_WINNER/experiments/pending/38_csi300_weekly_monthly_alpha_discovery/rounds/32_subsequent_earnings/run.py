from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parents[2]/"37_momentum_reversal_joint_alpha_h10/code"))
from core import sha,dump
out=here/"results";out.mkdir(exist_ok=True)
src=here.parents[2]/"24_conditional_return_distribution_exploration/outputs/local_cache/public_financials"
ep=here.parent/"31_earnings_attribution/results/events.csv"
pairs=pd.read_csv(ep,parse_dates=["signal_date"])
pairs["quarter"]=pairs.signal_date.dt.to_period("Q")
fields=["SECUCODE","NOTICE_DATE","UPDATE_DATE","REPORT_DATE","DJD_DEDUCTDPNP_YOY"]
hashes={};results=[]
for stock in sorted(set(pairs.incoming)|set(pairs.control.dropna())):
    f=src/(stock[2:]+"."+stock[:2]+".parquet")
    if not f.exists():continue
    import pyarrow.parquet as pq
    if not set(fields).issubset(pq.ParquetFile(f).schema.names):continue
    hashes[f.name]=sha(f)
    a=pd.read_parquet(f,columns=fields)
    assert a.SECUCODE.dropna().eq(f.stem).all()
    for c in fields[1:4]:a[c]=pd.to_datetime(a[c],errors="coerce")
    a["growth"]=pd.to_numeric(a[fields[-1]],errors="coerce")
    a=a.dropna(subset=fields[1:4])
    a=a[(a.REPORT_DATE<=a.NOTICE_DATE)&a.REPORT_DATE.dt.is_quarter_end&np.isfinite(a.growth)]
    for date,g in a.groupby("REPORT_DATE"):
        # Conflicting values across archived rows do not define a unique final label.
        if g.growth.nunique()!=1:continue
        results.append(dict(stock=stock,quarter=date.to_period("Q"),growth=g.growth.iloc[0],notice=g.NOTICE_DATE.min(),updated=g.UPDATE_DATE.max()))
facts=pd.DataFrame(results)
prev=facts.copy();prev.quarter+=1
facts=facts.merge(prev,on=["stock","quarter"],suffixes=("","_prior"),validate="1:1")
facts["acceleration"]=facts.growth-facts.growth_prior
z=pairs.rename(columns={c:"known_at_signal_"+c for c in pairs if c.startswith(("incoming_","control_"))}).copy()
for side in ["incoming","control"]:
    z=z.merge(facts.rename(columns={"stock":side,**{c:side+"_"+c for c in facts if c not in ["stock","quarter"]}}),on=[side,"quarter"],how="left",validate="many_to_one")
known=z.incoming_notice.gt(z.signal_date)&z.control_notice.gt(z.signal_date)
z["gap"]=(z.incoming_acceleration-z.control_acceleration).where(known)
z["win"]=((z.gap>0).astype(float)+.5*z.gap.eq(0)).where(z.gap.notna())
z.to_csv(out/"labeled_events.csv",index=False)
q=z.dropna(subset=["win"])
q.groupby(["phase","scope","quarter"]).agg(pairs=("win","size"),win_rate=("win","mean"),median_gap=("gap","median")).to_csv(out/"quarter.csv")
rows=[]
for (phase,scope),g in z.groupby(["phase","scope"]):
    k=g.dropna(subset=["win"]);u=k.drop_duplicates(["quarter","incoming","control"])
    ok=k[k.status=="ok"]
    legs={}
    for label,h in [("win",ok[ok.gap>0]),("other",ok[ok.gap<=0])]:
        legs[label+"_n"]=len(h);legs[label+"_pair_bp"]=h.spread.mean()*1e4
    rows.append(dict(phase=phase,scope=scope,swaps=len(g),matched=g.control.count(),labeled=len(k),quarters=k.quarter.nunique(),
        n_unique=len(u),win_rate=k.win.mean(),unique_rate=u.win.mean(),median_gap_pp=k.gap.median(),**legs))
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False)
assert len(z)==len(pairs) and not z.duplicated(["phase","signal_date","incoming"]).any()
dump(out/"receipt.json",dict(financial_hashes=hashes,inputs={str(f):sha(f) for f in [ep,here/"PROTOCOL.md",Path(__file__),out/"labeled_events.csv",out/"summary.csv",out/"quarter.csv"]}))
print(s.round(3).to_string(index=False))

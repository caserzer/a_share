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
for f in sorted(src.glob("*.parquet")):
    code,exchange=f.stem.split(".")
    stock=exchange+code
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
from core import PRIVATE
indfile=PRIVATE/"industry.parquet"
industry=pd.read_parquet(indfile)
industry["instrument"]=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
events=[]
for date,g in pairs.groupby("signal_date"):
    datekey=date.strftime("%Y%m%d");quarter=date.to_period("Q")
    active=industry[industry.in_date.le(datekey)&(industry.out_date.isna()|industry.out_date.gt(datekey))]
    mapping=active[["instrument","l3_code","l3_name"]].dropna().drop_duplicates()
    mapping=mapping[~mapping.instrument.duplicated(False)].set_index("instrument")
    values=facts[(facts.quarter==quarter)&(facts.notice>date)].set_index("stock").acceleration
    mapping["value"]=values.reindex(mapping.index)
    for row in g.itertuples():
        rec=dict(phase=row.phase,scope=row.scope,signal_date=date,quarter=quarter,incoming=row.incoming,control=row.control)
        for side in ["incoming","control"]:
            stock=rec[side]
            if stock not in mapping.index:continue
            sector=mapping.loc[stock]
            peers=mapping[(mapping.l3_code==sector.l3_code)&(mapping.l3_name==sector.l3_name)&~mapping.index.isin([row.incoming,row.control])]
            rec[side+"_sector"]=str(sector.l3_code)+" "+sector.l3_name
            rec[side+"_n"]=len(peers);rec[side+"_valid"]=peers.value.count()
            rec[side+"_median"]=peers.value.median() if peers.value.count()>=3 else np.nan
        events.append(rec)
z=pd.DataFrame(events)
assert len(z)==len(pairs)
z["gap"]=z.incoming_median-z.control_median
z.to_csv(out/"events.csv",index=False)
q=z.dropna(subset=["gap"])
assert (q.incoming_sector!=q.control_sector).all()
unique=q.groupby(["phase","scope","quarter","incoming_sector","control_sector"]).gap.median().reset_index()
unique.to_csv(out/"industry_pairs.csv",index=False)
rows=[]
for (phase,scope),g in z.groupby(["phase","scope"]):
    k=g.dropna(subset=["gap"])
    u=unique[(unique.phase==phase)&(unique.scope==scope)]
    rows.append(dict(phase=phase,scope=scope,matched=g.control.count(),events=len(k),quarter_industry_pairs=len(u),quarters=u.quarter.nunique(),
        rate=((u.gap>0)+0.5*(u.gap==0)).mean(),median_gap_pp=u.gap.median(),
        median_incoming_coverage=(k.incoming_valid/k.incoming_n).median(),median_control_coverage=(k.control_valid/k.control_n).median()))
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False)
dump(out/"receipt.json",dict(financial_hashes=hashes,inputs={str(f):sha(f) for f in [indfile,ep,here/"PROTOCOL.md",Path(__file__),out/"summary.csv",out/"events.csv",out/"industry_pairs.csv"]}))
print(s.round(3).to_string(index=False))

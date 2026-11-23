from pathlib import Path
import sys
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];OUT=HERE/"results";OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import EP,R,E,accounts,PRIVATE
from core import sha,dump,assign_deciles
accounts.OUT=OUT;m=accounts.Market()
sf=HERE.parent/"17_calendar_challenge/results/point_in_time_scores.parquet"
p=pd.read_parquet(sf)
swapfile=HERE.parent/"18_industry_attribution/results/swaps.csv"
sw=pd.read_csv(swapfile,parse_dates=["signal_date"])
src=ROOT.parent/"34_industry_price_observation_radar/handoff/v3_candidates_20261016/early_model/periods"
files=sorted(src.glob("*.csv"))
cat=pd.concat(pd.read_csv(f,usecols=["date","industry_code","industry_name","state"]) for f in files)
cat["date"]=pd.to_datetime(cat.date);history={d:g for d,g in cat.groupby("date")}
ind=pd.read_parquet(PRIVATE/"industry.parquet");ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]

close=pd.read_parquet(PRIVATE/"qfq_close.parquet")
momentum=close/close.shift(20)-1
money=pd.read_parquet(PRIVATE/"money.parquet")
adv=money.where(money>0).rolling(20).mean()
events=[]
features=[R,E,"momentum","adv"]
for (phase,d),g in sw.groupby(["phase","signal_date"]):
    s=p[(p.offset==phase)&(p.signal_date==d)].copy()
    s["dec"]=assign_deciles(s,R)
    s["momentum"]=s.instrument.map(momentum.loc[d])
    s["adv"]=s.instrument.map(adv.loc[d])
    s[features]=s[features].rank(pct=True)
    s=s.set_index("instrument")
    k=d.strftime("%Y%m%d")
    active=ind[ind.in_date.le(k)&(ind.out_date.isna()|ind.out_date.gt(k))][["instrument","l1_name","l3_code","l3_name"]].drop_duplicates()
    s=s.join(active[~active.instrument.duplicated(False)].set_index("instrument"))
    week=max(i for i in history if i<d);tab=history[week]
    allowed=set(zip(tab.industry_code,tab.industry_name));off=tab[~tab.state.isin(["NEW","TRACKING"])]
    # DATA_INSUFFICIENT is not a supported alternative industry observation.
    off=off[off.state.ne("DATA_INSUFFICIENT")]
    outside=set(zip(off.industry_code,off.industry_name));eligible=[k in outside for k in zip(s.l3_code,s.l3_name)]
    choices=s[s.dec.eq(9)&np.asarray(eligible)].copy()
    for row in g.sort_values("incoming").itertuples():
        h=s.loc[row.incoming]
        pool=choices[choices.l1_name.eq(h.l1_name)].dropna(subset=features)
        meta=dict(phase=phase,scope=row.scope,signal_date=d,incoming=row.incoming,outgoing=row.outgoing,weight=row.weight)
        if pool.empty or h[features].isna().any():events.append(meta|dict(status="no_control"));continue
        dist=((pool[features]-h[features].astype(float))**2).sum(axis=1)
        name=dist.sort_index().sort_values(kind="stable").index[0]
        choices=choices.drop(index=name)
        j=m.symbols.get_indexer([row.incoming,name]);e=int(h.entry_idx);x=int(h.exit_idx)
        ok=(m.buy[e,j]&m.sell[x,j]).all()
        returns=(1-.002)/(1+.001)*m.o[x,j]/m.o[e,j]-1
        if not ok:returns[:]=np.nan
        events.append(meta|dict(status="ok" if ok else "blocked",control=name,distance=dist[name]**.5,
            selected=returns[0],alternative=returns[1],specific=row.weight*(returns[0]-returns[1]),
            **{"gap_"+k:float(h[k]-pool.at[name,k]) for k in features}))

z=pd.DataFrame(events)
src=ROOT.parent/"24_conditional_return_distribution_exploration/outputs/local_cache/public_financials"
fin=[];hashes={}
cols=["REPORT_DATE","NOTICE_DATE","UPDATE_DATE","DJD_DEDUCTDPNP_YOY","SECUCODE"]
for sym in sorted(set(z.incoming)|set(z.control.dropna())):
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

parts=[]
for date,g in z.groupby("signal_date"):
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

    fields=["instrument","REPORT_DATE","available","prior_available","growth","change"]
    for key in ["incoming","control"]:
        g=g.merge(q[fields].add_prefix(key+"_"),left_on=key,right_on=key+"_instrument",how="left",validate="many_to_one")
    parts.append(g)
z=pd.concat(parts,ignore_index=True)
same=z.incoming_REPORT_DATE.eq(z.control_REPORT_DATE)&z.incoming_change.notna()&z.control_change.notna()
z["earnings_gap"]=(z.incoming_change-z.control_change).where(same)
z["bucket"]=np.select([z.earnings_gap.gt(0),z.earnings_gap.le(0)],["stronger","other"],default="unknown")
z["spread"]=z.selected-z.alternative
assert len(z)==len(sw) and not z.dropna(subset=["control"]).duplicated(["phase","signal_date","control"]).any()
reference=HERE.parent/"14_core_earnings/results/signals.parquet"
prior=pd.read_parquet(reference).set_index(["signal_date","instrument"])
for key in ["incoming","control"]:
    orig=z[(z.phase==0)&z[key].notna()]
    ix=pd.MultiIndex.from_frame(orig[["signal_date",key]])
    assert ix.isin(prior.index).all()
    np.testing.assert_allclose(orig[key+"_change"],prior.change.reindex(ix),equal_nan=True)
z.to_csv(OUT/"events.csv",index=False)
calfile=HERE.parent/"18_industry_attribution/results/active_capital.csv"
cal=pd.read_csv(calfile)
rows=[]; buckets=[]
for (phase,scope),g in z.groupby(["phase","scope"]):
    n=len(cal[(cal.phase==phase)&(cal.scope==scope)])
    known=g.dropna(subset=["earnings_gap"])
    meta=dict(phase=phase,scope=scope)
    rows.append(dict(**meta,periods=n,swaps=len(g),matched=g.control.count(),incoming_known=g.incoming_change.count(),control_known=g.control_change.count(),
        comparable=len(known),comparable_dates=known.signal_date.nunique(),stronger=(known.earnings_gap>0).sum(),ties=(known.earnings_gap==0).sum(),
        win_rate=((known.earnings_gap>0).astype(float)+.5*(known.earnings_gap==0)).mean(),overall_bp=g.specific.sum()/n*1e4,
        **{"abs_gap_"+k:g["gap_"+k].abs().mean() for k in features}))
    for label in ["stronger","other","unknown"]:
        h=g[g.bucket==label];ok=h[h.status=="ok"]
        buckets.append(dict(**meta,bucket=label,events=len(h),priced=len(ok),dates=ok.signal_date.nunique(),
            pair_bp=ok.spread.mean()*1e4,weight_coverage=ok.weight.sum()/g.weight.sum(),contribution_bp=ok.specific.sum()/n*1e4))
summary=pd.DataFrame(rows);summary.to_csv(OUT/"summary.csv",index=False)
b=pd.DataFrame(buckets);b.to_csv(OUT/"buckets.csv",index=False)
np.testing.assert_allclose(b.groupby(["phase","scope"]).contribution_bp.sum(),summary.set_index(["phase","scope"]).overall_bp)
dump(OUT/"receipt.json",dict(financial_hashes=hashes,inputs={str(f):sha(f) for f in [sf,swapfile,reference,calfile,PRIVATE/"money.parquet",PRIVATE/"qfq_close.parquet",PRIVATE/"industry.parquet",*files,Path(__file__),HERE/"PROTOCOL.md",OUT/"events.csv",OUT/"buckets.csv",OUT/"summary.csv"]}))
print(summary.round(3).to_string(index=False))
print(b.round(3).to_string(index=False))

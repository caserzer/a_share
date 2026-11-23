from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE.parent/"02_adaptive_revision"),str(HERE.parent/"21_dual_support")]
from evaluate import R,E,accounts,PRIVATE
from account import replay
from core import sha,dump
OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
m=accounts.Market();days=m.days
cp=PRIVATE/"qfq_close.parquet";ip=PRIVATE/"industry.parquet"
moneyfile=PRIVATE/"money.parquet"
money=pd.read_parquet(moneyfile).rolling(20).sum()
ret=np.log(pd.read_parquet(cp)).diff();mom=ret.rolling(20).sum();vol=ret.rolling(20).std()
ep24=ROOT.parent/"24_conditional_return_distribution_exploration"
marginfile=ep24/"outputs/local_cache/r27_margin_snapshots/normalized_detail.parquet"
audit=ep24/"outputs/r27_margin_information/feature_audit.json"
assert sha(marginfile)==json.loads(audit.read_text())["normalized_detail_sha256"]
margin=pd.read_parquet(marginfile)
assert not margin.duplicated(["date","instrument"]).any()
balance=margin.pivot(index="date",columns="instrument",values="financing").sort_index()
snap=margin[["date","snapshot_date"]].drop_duplicates().set_index("date").snapshot_date
assert snap.index.is_unique
changes=balance.diff()
gap=balance.index.to_period("M").astype(int)
changes.loc[np.r_[True,np.diff(gap)!=1]]=np.nan
ind=pd.read_parquet(ip);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
coverage=[]
def signals(i):
    day=days[i];key=day.strftime("%Y%m%d")
    a=ind[ind.in_date.le(key)&(ind.out_date.isna()|ind.out_date.gt(key))][["instrument","l1_name"]].drop_duplicates()
    sector=a[~a.instrument.duplicated(False)].set_index("instrument").l1_name
    stocks=m.symbols[m.members[i]]
    j=balance.index.searchsorted(day,side="right")-1
    origin=balance.index[j] if j>=0 else pd.NaT
    f=pd.DataFrame(index=stocks,columns=["raw","momentum","vol","sector","residual"])
    if j>0 and (day-origin).days<=31:
        sd=snap.loc[origin]
        assert days.get_loc(origin)-days.get_loc(sd)==2
        denom=money.loc[sd,stocks]
        f=pd.DataFrame(dict(raw=changes.iloc[j].reindex(stocks)/denom.where(denom>0),momentum=mom.loc[sd,stocks],vol=vol.loc[sd,stocks],sector=sector.reindex(stocks))).dropna()
        if len(f)>=100:
            x=np.column_stack([pd.get_dummies(f.sector).astype(float),f[["momentum","vol"]].rank(pct=True)])
            y=f.raw.rank(pct=True).to_numpy()
            f["residual"]=y-x@np.linalg.lstsq(x,y,rcond=None)[0]
        else:f["residual"]=np.nan
    coverage.append(dict(date=day,origin=origin,members=len(stocks),valid=f.residual.count()))
    return f.dropna()
first=days.get_loc(pd.Timestamp("2021-01-08"))
early=[]
for i in range(first%10,first,10):
    if i<20 or days[i+11]>=pd.Timestamp("2021-01-01"):continue
    g=signals(i).dropna()
    if len(g)<100:continue
    j=m.symbols.get_indexer(g.index);ok=m.buy[i+1,j]&m.sell[i+11,j]
    r=m.o[i+11,j[ok]]/m.o[i+1,j[ok]]-1
    h=g.loc[ok].assign(realized=r)
    early.append(dict(date=days[i],eligible=len(g),priced=len(h),rho=h.residual.corr(h.realized,method="spearman"),
                      raw_rho=h.raw.corr(h.realized,method="spearman")))
pd.DataFrame(early).to_csv(OUT/"early.csv",index=False)
print(pd.DataFrame(early)[["rho","raw_rho"]].mean())
rows=[];weights=[];inputs=[cp,ip,marginfile,audit,moneyfile,PRIVATE/"daily_members.parquet"]
for phase,folder in [(0,"16_industry_pool"),(5,"17_calendar_challenge")]:
    path=HERE.parent/folder/"results/targets.parquet";inputs.append(path)
    dest=OUT/str(phase);dest.mkdir(exist_ok=True)
    t=pd.read_parquet(path).query("model in [@R,@E]").copy();parts=[t]
    for dt,b in t[t.model==R].groupby("signal_date"):
        factors=signals(days.get_loc(dt))
        h=b.set_index("instrument").join(factors[["sector","raw","residual"]])
        for col in ["residual","raw"]:
            z=h.copy();known=z[col].notna()
            grp=z.loc[known].groupby("sector")[col]
            n=grp.transform("size")
            factor=(1.5-(grp.rank()-1)/(n-1)).where(n>1,1.)
            z.loc[known,"weight"]*=factor
            assert np.isclose(z.weight.sum(),1) and np.allclose(z.groupby("sector",dropna=False).weight.sum(),h.groupby("sector",dropna=False).weight.sum())
            weights.append(dict(phase=phase,date=dt,model=col,active=(z.weight-h.weight).abs().sum()/2))
            parts.append(z.reset_index().assign(model=col))
    targets=pd.concat(parts,ignore_index=True)
    targets.to_parquet(dest/"targets.parquet",index=False)
    accounts.OUT=dest;replay(targets,dest)
    w=pd.read_csv(dest/"windows.csv");mo=pd.read_csv(dest/"months.csv")
    old=pd.read_csv(path.parent/"windows.csv")
    for ref in [E,R]:
        merge=w[w.model==ref].merge(old[old.model==ref],on=["cost","scope","signal_date"],validate="1:1")
        assert len(merge)==len(old[old.model==ref])
        np.testing.assert_allclose(merge.net_x,merge.net_y,atol=1e-12)
    for (model,scope),g in w[w.model.isin(["residual","raw"])].groupby(["model","scope"]):
        v=g[g.cost=="base"]["vs_"+R].to_numpy()
        q=g.groupby("cost")["vs_"+R].mean()*1e4
        md=mo[(mo.model==model)&(mo.scope==scope)].delta
        n=len(v);starts=np.random.default_rng(3824).integers(n,size=(10000,(n+2)//3))
        ix=((starts[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]
        lo,hi=np.quantile(v[ix].mean(axis=1),[.025/36,1-.025/36])*1e4
        rows.append(dict(phase=phase,model=model,scope=scope,n=n,base=q.base,double=q.double,zero=q.zero,lo=lo,hi=hi,ex3_month=md.drop(md.nlargest(3).index).mean()*1e4))
s=pd.DataFrame(rows);s.to_csv(OUT/"summary.csv",index=False);print(s.round(2).to_string(index=False))
pd.DataFrame(weights).to_csv(OUT/"weights.csv",index=False)
pd.DataFrame(coverage).drop_duplicates().to_csv(OUT/"coverage.csv",index=False)
dump(OUT/"receipt.json",{str(f):sha(f) for f in [*inputs,Path(__file__),HERE/"PROTOCOL.md",OUT/"summary.csv",OUT/"early.csv"]})

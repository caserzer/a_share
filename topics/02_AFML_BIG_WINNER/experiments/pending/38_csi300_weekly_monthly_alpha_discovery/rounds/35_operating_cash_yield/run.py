from pathlib import Path
import sys
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
src=ROOT.parent/"24_conditional_return_distribution_exploration/outputs/local_cache/public_valuation"
fields=["TRADE_DATE","SECUCODE","PE_TTM","PCF_OCF_TTM","TOTAL_MARKET_CAP"]
parts=[];hashes={}
universe=m.symbols[m.members.any(axis=0)]
for symbol in universe:
    f=src/(symbol[2:]+".parquet")
    if not f.exists():continue
    a=pd.read_parquet(f,columns=fields)
    assert a.SECUCODE.dropna().eq(symbol[2:]+"."+symbol[:2]).all()
    a["date"]=pd.to_datetime(a.TRADE_DATE)
    a=a[~a.date.duplicated(False)].copy()
    a["instrument"]=symbol
    hashes[f.name]=sha(f)
    parts.append(a)
values=pd.concat(parts).set_index(["date","instrument"]).sort_index()
coverage=[]
ind=pd.read_parquet(ip);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
def signals(i):
    day=days[i];asof=days[i-1];key=day.strftime("%Y%m%d")
    a=ind[ind.in_date.le(key)&(ind.out_date.isna()|ind.out_date.gt(key))][["instrument","l1_name"]].drop_duplicates()
    sector=a[~a.instrument.duplicated(False)].set_index("instrument").l1_name
    stocks=m.symbols[m.members[i]]
    frame=values.loc[asof].reindex(stocks) if asof in values.index.levels[0] else pd.DataFrame(index=stocks,columns=fields[2:],dtype=float)
    f=pd.DataFrame(index=stocks)
    for basis,col in [("earnings","PE_TTM"),("cash","PCF_OCF_TTM")]:
        v=pd.to_numeric(frame[col],errors="coerce")
        f[basis]=1/v.where(v.ne(0)&np.isfinite(v))
    size=pd.to_numeric(frame.TOTAL_MARKET_CAP,errors="coerce")
    f["size"]=size.where((size>0)&np.isfinite(size))
    f["sector"]=sector.reindex(stocks)
    f=f.dropna()
    f=f[~f.sector.isin(["银行","非银金融"])]
    f=f[f.groupby("sector").cash.transform("size")>=3].copy()
    coverage.append(dict(date=day,valuation_date=asof,universe=len(stocks),raw_eligible=len(f),negative_cash=int(f.cash.lt(0).sum()),negative_earnings=int(f.earnings.lt(0).sum())))
    if len(f)<100:return f.iloc[:0].assign(cash_residual=np.nan)
    x=np.column_stack([pd.get_dummies(f.sector).astype(float),f[["earnings","size"]].rank(pct=True)])
    y=f.cash.rank(pct=True).to_numpy()
    f["cash_residual"]=y-x@np.linalg.lstsq(x,y,rcond=None)[0]
    return f
first=days.get_loc(pd.Timestamp("2021-01-08"))
early=[]
for i in range(first%10,first,10):
    if i<20 or days[i+11]>=pd.Timestamp("2021-01-01"):continue
    g=signals(i).dropna()
    if len(g)<3:continue
    j=m.symbols.get_indexer(g.index);ok=m.buy[i+1,j]&m.sell[i+11,j]
    r=m.o[i+11,j[ok]]/m.o[i+1,j[ok]]-1
    h=g.loc[ok].assign(realized=r)
    early.append(dict(date=days[i],eligible=len(g),priced=len(h),rho=h.cash_residual.corr(h.realized,method="spearman"),
                      earnings_rho=h.earnings.corr(h.realized,method="spearman")))
pd.DataFrame(early).to_csv(OUT/"early.csv",index=False)
print(pd.DataFrame(early)[["rho","earnings_rho"]].mean())
rows=[];weights=[];inputs=[ip,PRIVATE/"daily_members.parquet"]
for phase,folder in [(0,"16_industry_pool"),(5,"17_calendar_challenge")]:
    path=HERE.parent/folder/"results/targets.parquet";inputs.append(path)
    dest=OUT/str(phase);dest.mkdir(exist_ok=True)
    t=pd.read_parquet(path).query("model in [@R,@E]").copy();parts=[t]
    for dt,b in t[t.model==R].groupby("signal_date"):
        factors=signals(days.get_loc(dt))
        h=b.set_index("instrument").join(factors[["sector","earnings","cash_residual"]])
        for col in ["cash_residual","earnings"]:
            z=h.copy();known=z[col].notna()
            grp=z.loc[known].groupby("sector")[col]
            n=grp.transform("size")
            factor=(.5+(grp.rank()-1)/(n-1)).where(n>1,1.)
            z.loc[known,"weight"]*=factor
            assert np.isclose(z.weight.sum(),1) and np.allclose(z.groupby("sector",dropna=False).weight.sum(),h.groupby("sector",dropna=False).weight.sum())
            weights.append(dict(phase=phase,date=dt,model=col,known=int(known.sum()),positive=int((z[col]>0).sum()),active=(z.weight-h.weight).abs().sum()/2))
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
    for (model,scope),g in w[w.model.isin(["cash_residual","earnings"])].groupby(["model","scope"]):
        v=g[g.cost=="base"]["vs_"+R].to_numpy()
        q=g.groupby("cost")["vs_"+R].mean()*1e4
        md=mo[(mo.model==model)&(mo.scope==scope)].delta
        n=len(v);starts=np.random.default_rng(3824).integers(n,size=(10000,(n+2)//3))
        ix=((starts[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]
        lo,hi=np.quantile(v[ix].mean(axis=1),[.025/42,1-.025/42])*1e4
        basis=w[(w.model=="earnings")&(w.scope==scope)&(w.cost=="base")].set_index("signal_date").net
        aligned=g[g.cost=="base"].set_index("signal_date")
        gap=(aligned.net-basis).mean()*1e4
        rows.append(dict(vs_earnings_bp=gap,phase=phase,model=model,scope=scope,n=n,base=q.base,double=q.double,zero=q.zero,lo=lo,hi=hi,ex3_month=md.drop(md.nlargest(3).index).mean()*1e4))
s=pd.DataFrame(rows);s.to_csv(OUT/"summary.csv",index=False);print(s.round(2).to_string(index=False))
pd.DataFrame(weights).to_csv(OUT/"weights.csv",index=False)
pd.DataFrame(coverage).drop_duplicates().to_csv(OUT/"coverage.csv",index=False)
dump(OUT/"financial_hashes.json",hashes)
dump(OUT/"receipt.json",{str(f):sha(f) for f in [*inputs,OUT/"financial_hashes.json",OUT/"coverage.csv",Path(__file__),HERE/"PROTOCOL.md",OUT/"summary.csv",OUT/"early.csv"]})

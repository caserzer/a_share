from pathlib import Path
import sys,re,json
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
root=here.parents[1]
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,accounts,split
from core import dump,sha
out=here/"results";out.mkdir(exist_ok=True);accounts.OUT=out
m=accounts.Market();days=m.days
cache=root.parent/"24_conditional_return_distribution_exploration/outputs"
src=cache/"local_cache/corporate_actions"
actions=src/"RPT_SHAREBONUS_DET_all.parquet";rights=src/"RPT_IPO_ALLOTMENT_all.parquet";receipt=cache/"corporate_action_fetch_audit.json"
a=pd.read_parquet(actions).drop_duplicates()
a["ex"]=pd.to_datetime(a.EX_DIVIDEND_DATE);a["notice"]=pd.to_datetime(a.NOTICE_DATE)
audit=json.loads(receipt.read_text())[0]
assert audit["reported_count"]==audit["rows"]==len(pd.read_parquet(actions)) and a.ex.max()==pd.Timestamp('2026-05-29')
right=pd.read_parquet(rights)
code=pd.Series(m.symbols,index=m.symbols.str[2:]);assert code.index.is_unique
a["stock"]=a.SECURITY_CODE.map(code)
known=a[a.notice.le(a.ex)&a.stock.notna()].groupby("ex").stock.agg(set).to_dict()
rk=right.assign(stock=right.SECURITY_CODE.map(code),ex=pd.to_datetime(right.EX_DIVIDEND_DATE)).groupby("ex").stock.agg(set).to_dict()
a=a[a.stock.notna()&a.notice.lt(a.ex)&a.ASSIGN_PROGRESS.eq("实施分配")].copy()
a=a[~a.duplicated(["ex","stock"],False)&pd.to_numeric(a.PRETAX_BONUS_RMB,errors="coerce").gt(0)
    &a.BONUS_IT_RATIO.fillna(0).eq(0)&a.IMPL_PLAN_PROFILE.fillna("").str.match(r"^10派")]
indfile=PRIVATE/"industry.parquet";industry=pd.read_parquet(indfile);industry["instrument"]=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
opfile=PRIVATE/"open.parquet";clfile=PRIVATE/"close.parquet";qfile=PRIVATE/"qfq_close.parquet"
rawopen=pd.read_parquet(opfile);rawclose=pd.read_parquet(clfile)
intra=(rawclose/rawopen-1).replace([np.inf,-np.inf],np.nan)
q=pd.read_parquet(qfile);r=np.log(q).diff()
mom=r.rolling(20).sum().shift();vol=r.rolling(20).std().shift()
features=["intra","mom","vol"]
oldfile=here.parent/"47_ex_dividend/results/events.csv"
old=pd.read_csv(oldfile,parse_dates=["day","entry","exit"])
old=old[old.group.eq("weak")&old.scope.ne("boundary")]
rows=[]
for day,g in old.groupby("day"):
    i=days.get_loc(day);e=i+1;x=i+11;members=m.symbols[m.members[i]]
    key=day.strftime("%Y%m%d")
    active=industry[industry.in_date.le(key)&(industry.out_date.isna()|industry.out_date.gt(key))][["instrument","l1_name"]].drop_duplicates()
    sector=active[~active.instrument.duplicated(False)].set_index("instrument").l1_name
    f=pd.DataFrame(dict(intra=intra.loc[day,members],mom=mom.loc[day,members],vol=vol.loc[day,members],sector=sector.reindex(members))).dropna()
    pct=f[features].rank(pct=True)
    outside=f[~f.index.isin(known.get(day,set())|rk.get(day,set()))]
    for ev in g.itertuples():
        stock=ev.stock;target=f.at[stock,"intra"]
        peers=outside[outside.sector.eq(f.at[stock,"sector"])].sort_index()
        dist=(pct.loc[peers.index]-pct.loc[stock]).pow(2).sum(axis=1)
        candidates=[(dist[k],k,k,1.) for k in peers.index[peers.intra.eq(target)]]
        for low in peers.index[peers.intra.lt(target)]:
            for high in peers.index[peers.intra.gt(target)]:
                w=(peers.at[high,"intra"]-target)/(peers.at[high,"intra"]-peers.at[low,"intra"])
                candidates.append((w*dist[low]+(1-w)*dist[high],low,high,w))
        rec=dict(scope=ev.scope,day=day,stock=stock,original=ev.control)
        if not candidates:
            rows.append(dict(**rec,status="outside_support"));continue
        _,low,high,w=min(candidates)
        assert 0<=w<=1 and abs(w*peers.at[low,"intra"]+(1-w)*peers.at[high,"intra"]-target)<1e-12
        rec.update(low=low,high=high,low_weight=w,abs_mom_gap=abs(w*pct.at[low,"mom"]+(1-w)*pct.at[high,"mom"]-pct.at[stock,"mom"]),
                   abs_vol_gap=abs(w*pct.at[low,"vol"]+(1-w)*pct.at[high,"vol"]-pct.at[stock,"vol"]))
        j=m.symbols.get_indexer([stock,ev.control,low,high])
        if not (m.buy[e,j]&m.sell[x,j]&np.isfinite(m.o[e,j])&np.isfinite(m.o[x,j])).all():
            rows.append(dict(**rec,status="unpriced"));continue
        rr=(1-.002)/(1+.001)*m.o[x,j]/m.o[e,j]-1
        new=rr[0]-w*rr[2]-(1-w)*rr[3]
        assert abs(rr[0]-rr[1]-ev.pair)<1e-10
        rows.append(dict(**rec,status="ok",old=rr[0]-rr[1],new=new))
z=pd.DataFrame(rows);assert len(z)==len(old);z.to_csv(out/"events.csv",index=False)
summary=[]
for scope,g in z.groupby("scope"):
    h=g[g.status.eq("ok")]
    d=h.groupby("day")[["old","new"]].mean()*1e4
    totals=d.new.groupby(d.index.to_period("M")).sum()
    used=pd.concat([h[["day","stock","low"]].rename(columns={"low":"control"}),h[["day","stock","high"]].rename(columns={"high":"control"})]).drop_duplicates()
    summary.append(dict(scope=scope,eligible=len(g),outside=g.status.eq("outside_support").sum(),unpriced=g.status.eq("unpriced").sum(),priced=len(h),dates=len(d),
                        old_bp=d.old.mean(),new_bp=d.new.mean(),ex3_bp=d[~d.index.to_period("M").isin(totals.nlargest(3).index)].new.mean(),
                        shared_control_assignments=used.duplicated(["day","control"],False).sum(),assignments=len(used),
                        abs_mom_gap=h.abs_mom_gap.mean(),abs_vol_gap=h.abs_vol_gap.mean()))
s=pd.DataFrame(summary);s.to_csv(out/"summary.csv",index=False);print(s.round(3).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [oldfile,actions,rights,receipt,indfile,opfile,clfile,qfile,PRIVATE/"daily_members.parquet",Path(__file__),here/"PROTOCOL.md",out/"events.csv",out/"summary.csv"]})

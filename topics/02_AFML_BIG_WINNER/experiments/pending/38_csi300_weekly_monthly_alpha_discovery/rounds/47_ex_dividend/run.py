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
rows=[]
for day,g in a.groupby("ex"):
    if day not in days:continue
    i=days.get_loc(day)
    if i+11>=len(days):continue
    members=m.symbols[m.members[i]];g=g[g.stock.isin(members)].sort_values("stock")
    if g.empty:continue
    key=day.strftime("%Y%m%d")
    active=industry[industry.in_date.le(key)&(industry.out_date.isna()|industry.out_date.gt(key))][["instrument","l1_name"]].drop_duplicates()
    sector=active[~active.instrument.duplicated(False)].set_index("instrument").l1_name
    f=pd.DataFrame(dict(intra=intra.loc[day,members],mom=mom.loc[day,members],vol=vol.loc[day,members],sector=sector.reindex(members))).dropna()
    pct=f[features].rank(pct=True)
    outside=f[~f.index.isin(known.get(day,set())|rk.get(day,set()))]
    used=set();e=i+1;x=i+11
    scope="early" if days[x]<pd.Timestamp("2021-01-01") else "primary" if days[e]>=pd.Timestamp("2021-01-11") and days[x]<=split else "later" if days[e]>=split else "boundary"
    for ev in g.itertuples():
        stock=ev.stock
        rec=dict(scope=scope,day=day,stock=stock,notice=ev.notice,entry=days[e],exit=days[x])
        if stock not in f.index or stock in rk.get(day,set()):
            rows.append(dict(**rec,status="ineligible"));continue
        peers=outside[outside.sector.eq(f.at[stock,"sector"])]
        available=peers[~peers.index.isin(used)]
        if len(peers)<3 or available.empty:
            rows.append(dict(**rec,status="no_control"));continue
        diff=pct.loc[available.index]-pct.loc[stock]
        control=diff.pow(2).sum(axis=1).sort_index().sort_values(kind="stable").index[0]
        used.add(control)
        relative=f.at[stock,"intra"]-peers.intra.median()
        rec.update(control=control,relative=relative,group="weak" if relative<0 else "other",
            intra_gap=f.at[stock,"intra"]-f.at[control,"intra"],**{"pct_gap_"+k:diff.at[control,k] for k in features})
        j=m.symbols.get_indexer([stock,control])
        if not (m.buy[e,j]&m.sell[x,j]&np.isfinite(m.o[e,j])&np.isfinite(m.o[x,j])).all():
            rows.append(dict(**rec,status="unpriced"));continue
        ret=(1-.002)/(1+.001)*m.o[x,j]/m.o[e,j]-1
        rows.append(dict(**rec,status="ok",event_net=ret[0],control_net=ret[1],pair=ret[0]-ret[1]))
z=pd.DataFrame(rows);z.to_csv(out/"events.csv",index=False)
assert not z.dropna(subset=["control"]).duplicated(["day","control"]).any()
rows=[]
for (scope,group),g in z[z.scope.ne("boundary")&z.group.notna()].groupby(["scope","group"]):
    h=g[g.status.eq("ok")];d=h.groupby("day").pair.mean()*1e4
    monthly=d.groupby(d.index.to_period("M")).sum();best=monthly.nlargest(3).index
    rows.append(dict(scope=scope,group=group,matched=len(g),priced=len(h),dates=len(d),stocks=h.stock.nunique(),pair_bp=d.mean(),
        ex3_bp=d[~d.index.to_period("M").isin(best)].mean(),after_extra30_bp=d.mean()-30,abs_intra_gap_bp=h.intra_gap.abs().mean()*1e4,
        event_bp=h.groupby("day").event_net.mean().mean()*1e4,control_bp=h.groupby("day").control_net.mean().mean()*1e4))
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False);print(s.round(2).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [actions,rights,receipt,indfile,opfile,clfile,qfile,PRIVATE/"daily_members.parquet",Path(__file__),here/"PROTOCOL.md",out/"events.csv",out/"summary.csv"]})

from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,accounts
from core import dump,sha
accounts.OUT=out
m=accounts.Market()
days=m.days
files=[PRIVATE/(name+".parquet") for name in ["industry","daily_members","qfq_close","qfq_open","opening_trade_status_v2","open","limits/daily"]]
industry=pd.read_parquet(files[0])
industry["instrument"]=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
jan=len(sys.argv)>1 and sys.argv[1]=="january"
source=(here.parent/"95_announced_unlock/results") if jan else out
docs=pd.read_csv(source/"documents.csv",parse_dates=["known","unlock"])
if (source/"manual.csv").exists():
    edits=pd.read_csv(source/"manual.csv",dtype={"id":str})
    for change in edits.itertuples():
        hit=docs.announcementId.astype(str).eq(change.id)
        assert hit.sum()==1
        docs.loc[hit,"status"]=change.status
        docs.loc[hit,"unlock"]=pd.to_datetime(change.unlock)
    files.append(source/"manual.csv")
dated=docs[docs.status.isin(["unique","manual"])].sort_values(["known","announcementId"])
prospective=dated[dated.unlock.ge(dated.known)&~dated.title.str.contains("更正|补充|取消|撤销|延期")]
events=prospective.drop_duplicates(["instrument","unlock"])
weights_file=here.parent/"72_passive_weighting/results/targets.parquet"
weights=pd.read_parquet(weights_file,filters=[("model","=","drift_group")]).set_index(["signal_date","instrument"]).weight
files.append(weights_file)
rows=[]
for e in events.itertuples():
    i=days.searchsorted(e.known,side="right")-1
    start=i+1
    listing=days.get_indexer([e.unlock])[0]
    record=dict(issuer=e.instrument,document=e.announcementId,notice=e.known,unlock=e.unlock,signal=days[i],year=e.known.year)
    j=m.symbols.get_loc(e.instrument)
    stamp=days[i].strftime("%Y%m%d")
    v=industry[industry.in_date.le(stamp)&(industry.out_date.isna()|industry.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
    sector=v[~v.instrument.duplicated(False)].set_index("instrument").l1_name
    returns=pd.Series(m.c[i]/m.c[i-20]-1,index=m.symbols)
    blocked=set(dated.loc[(dated.known<=e.known)&(dated.unlock>=days[i]),"instrument"])
    blocked.add(e.instrument)
    peers=returns[m.members[i]&np.isfinite(returns)&~returns.index.isin(blocked)&sector.reindex(m.symbols).eq(sector.get(e.instrument))]
    peer=None if peers.empty or not np.isfinite(returns.iloc[j]) else (peers-returns.iloc[j]).abs().sort_index().idxmin()
    for label,a,b in [("after",listing,listing+10)]:
        row=dict(**record,window=label,peer=peer)
        if listing<0 or b>=len(days) or a<start or b<=a:row["status"]="no_window"
        elif peer is None:row["status"]="no_peer"
        else:
            k=m.symbols.get_loc(peer)
            q=m.o[[a,b]][:,[j,k]]
            row.update(entry=days[a],exit=days[b],sessions=b-a,ret20_gap=abs(returns[peer]-returns.iloc[j]),
                       budget=.5*min(weights.get((days[i],s),np.nan) for s in [peer,e.instrument]) if all((days[i],s) in weights.index for s in [peer,e.instrument]) else np.nan)
            can=m.buy[a,j] and m.sell[a,k] and m.sell[b,j] and m.buy[b,k] and m.members[a-1,j] and m.members[a-1,k]
            if not np.isfinite(q).all() or not (q>0).all() or not can:row["status"]="unexecutable"
            else:
                stock,other=q[1]/q[0]
                gross=stock-other
                fee=.003+.002*stock+.001*other
                row.update(status="ok",stock_return=stock-1,peer_return=other-1,gross=gross,fee=fee,net=gross-fee)
        rows.append(row)
prefix="january_" if jan else ""
w=pd.DataFrame(rows)
w.to_csv(out/(prefix+"windows.csv"),index=False)
w["scope"]=np.select([w.year<=2020,w.year<=2025],["2018-20","2021-25"],default="2026")
summary=[]
for (scope,label),g in w.groupby(["scope","window"]):
    valid=g[g.status.eq("ok")]
    by_date=valid.groupby("entry")[["gross","net"]].mean()*10000
    summary.append(dict(scope=scope,window=label,events=len(g),ok=len(valid),dates=len(by_date),mean_sessions=valid.sessions.mean(),gross_bp=by_date.gross.mean(),net_bp=by_date.net.mean(),ex_best3_bp=by_date.net.sort_values().iloc[:-3].mean(),positive_dates=int(by_date.net.gt(0).sum()),median_budget=valid.budget.median(),budget_observations=valid.budget.count()))
pd.DataFrame(summary).to_csv(out/(prefix+"summary.csv"),index=False)
files.extend(source/"pdf"/(str(r.announcementId)+".pdf") for r in docs.itertuples() if pd.notna(r.sha256))
dump(out/(prefix+"receipt.json"),{str(f):sha(f) for f in [*files,Path(__file__),here/"extract.py",here/"PROTOCOL.md",source/"catalog_receipt.json",source/"documents.csv",out/(prefix+"windows.csv"),out/(prefix+"summary.csv")]})

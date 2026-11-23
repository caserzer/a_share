from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import accounts,PRIVATE
from core import sha,dump
OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
m=accounts.Market();days=m.days
src=HERE.parent/"10_guidance_reaction/results/matched_events.csv"
e=pd.read_csv(src,usecols=["signal_date","stock","control","relative"],parse_dates=["signal_date"])
e=e[e.relative.lt(0)&e.control.notna()].copy()
files=sorted((PRIVATE/"weights").glob("????-??.json"))
wt=[]
for f in files:
    raw=json.loads(f.read_text()).get("data")
    if raw and raw["items"]:wt.append(pd.DataFrame(raw["items"],columns=raw["fields"]))
wt=pd.concat(wt).drop_duplicates()
wt["stock"]=wt.con_code.str[-2:]+wt.con_code.str[:6];wt["date"]=pd.to_datetime(wt.trade_date)
matrix=wt.pivot(index="date",columns="stock",values="weight").sort_index()/100
book={};records=[];usage=[]
for d,h in e.groupby("signal_date"):
    i=days.get_loc(d)+1
    # Release before reuse only if both legs have executable opening gates.
    for stock,(budget,rec) in list(book.items()):
        if i>=rec["due"] and rec["exit_i"]<=i:del book[stock]
    remaining=.05-sum(v[0] for v in book.values())
    latest=matrix.index.searchsorted(d,side="left")-1
    pending=[]
    for ev in h.itertuples():
        rec=dict(signal_date=d,stock=ev.stock,peer=ev.control,entry=days[i])
        j,k=m.symbols.get_indexer([ev.stock,ev.control])
        if latest<0 or (d-matrix.index[latest]).days>60:
            rec["status"]="no_fresh_weight"
        elif ev.stock in book:rec["status"]="source_in_use"
        elif not (m.members[i-1,j] and m.members[i-1,k] and m.sell[i,j] and m.buy[i,k]):rec["status"]="entry_blocked"
        else:
            w=matrix.iloc[latest].get(ev.stock,np.nan)
            if np.isfinite(w) and w>0:
                pending.append((rec,w/2,j,k));continue
            rec["status"]="no_weight"
        records.append(rec)
    total=sum(z[1] for z in pending)
    for rec,requested,j,k in pending:
        budget=requested*min(1,max(0,remaining)/total)
        if budget<=1e-12:
            records.append(rec|dict(status="budget_full"));continue
        due=i+10
        x=due
        while x<len(days) and not (m.buy[x,j] and m.sell[x,k]):x+=1
        rec.update(requested=requested,budget=budget,weight_date=matrix.index[latest],due=due,exit_i=x,status="open" if x==len(days) else "closed")
        if x<len(days):
            own=m.o[x,j]/m.o[i,j];other=m.o[x,k]/m.o[i,k]
            rec.update(exit_date=days[x],delay=x-due)
            for name,bf,sf in [("base",.001,.002),("double",.002,.004),("zero",0,0)]:
                rec[name]=budget*((1-sf)**2/(1+bf)*other-(1+bf)*own)
        book[rec["stock"]]=(budget,rec)
        records.append(rec)
    deployed=sum(z[0] for z in book.values())
    assert deployed<=.05+1e-12
    usage.append(dict(date=days[i],deployed=deployed))
z=pd.DataFrame(records)
z["scope"]=np.select([z.exit_date.lt("2021-01-01"),z.signal_date.lt("2021-01-01"),z.exit_date.le("2025-03-03"),z.signal_date.lt("2025-03-03")],["early","boundary","primary","boundary"],default="later")
z.to_csv(OUT/"events.csv",index=False);pd.DataFrame(usage).to_csv(OUT/"budget.csv",index=False)
c=z[z.status=="closed"].copy();c["month"]=c.exit_date.dt.to_period("M")
mo=c.groupby(["scope","month"])[["budget","base","double","zero"]].sum().reset_index()
mo.to_csv(OUT/"realized_months.csv",index=False)
s=c.groupby("scope").agg(n=("budget","size"),dates=("signal_date","nunique"),budget=("budget","sum"),base=("base","sum"),double=("double","sum"),zero=("zero","sum"))
s["per_deployed"]=s.base/s.budget
s["ex3"]=mo.groupby("scope").base.apply(lambda x:x.drop(x.nlargest(3).index).sum())
s.to_csv(OUT/"summary.csv");print(s.round(6))
dump(OUT/"receipt.json",dict(open_events=int(z.status.eq("open").sum()),max_book=max(u["deployed"] for u in usage),
   hashes={str(f):sha(f) for f in [src,HERE/"PROTOCOL.md",Path(__file__),OUT/"events.csv",*files]}))

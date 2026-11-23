from pathlib import Path
from decimal import Decimal
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results";prev=here.parent/"79_filing_pair/results"
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"64_mature_group_switch")]
from evaluate import PRIVATE,accounts
from core import dump,sha
from account import replay
day=pd.Timestamp("2019-05-06");asof=pd.Timestamp("2019-04-30")
datafiles=[prev/"source_values.csv",out/"source_values.csv"]
v=pd.concat([pd.read_csv(f,dtype={"current":str,"prior":str}) for f in datafiles]);files=[*datafiles,here/"extract.py",here/"fetch.py",here/"PROTOCOL.md",Path(__file__),out/"sources.csv",*sorted((out/"originals").glob("*.pdf")),prev/"receipt.json"]
rows=[]
for stock,g in v.groupby("instrument"):
    assert pd.to_datetime(g.notice).max()<=asof
    vals={}
    for field,h in g.groupby("field"):
        a,q=h.set_index("period").loc[["2018FY","2019Q1"]].itertuples()
        vals[field]=Decimal(a.current)+Decimal(q.current)-Decimal(q.prior)
    f=here.parents[2]/"24_conditional_return_distribution_exploration/outputs/local_cache/public_valuation"/(stock[2:]+".parquet");files.append(f)
    d=pd.read_parquet(f);x=d[pd.to_datetime(d.TRADE_DATE)==asof];assert len(x)==1
    p=float(x.PS_TTM.iloc[0]/x.PE_TTM.iloc[0]);r=float(vals["parent_profit"]/vals["total_revenue"])
    rows.append(dict(instrument=stock,**vals,reported=r,proxy=p,difference_bp=(p-r)*1e4))
z=pd.DataFrame(rows).set_index("instrument")
basefile=here.parent/"72_passive_weighting/results/targets.parquet";marginfile=here.parent/"75_profitability/results/targets.parquet";files.extend([basefile,marginfile])
base=pd.read_parquet(basefile,filters=[("model","=","drift_group"),("signal_date","=",day)]).set_index("instrument")
snap=pd.read_parquet(basefile,filters=[("model","=","snapshot"),("signal_date","=",day)]).sort_values(["weight","instrument"])
snap["bucket"]=np.arange(len(snap))*5//len(snap)
ip=PRIVATE/"industry.parquet";files.append(ip);ind=pd.read_parquet(ip);stamp=day.strftime("%Y%m%d")
m=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["ts_code","l1_name"]].drop_duplicates()
m=m[~m.ts_code.duplicated(False)];mp=m.set_index(m.ts_code.str[-2:]+m.ts_code.str[:6]).l1_name
members=snap.loc[(snap.bucket==4)&snap.instrument.map(mp).eq("食品饮料"),"instrument"]
assert set(members)==set(z.index)
margin=pd.read_parquet(marginfile,filters=[("model","=","margin"),("signal_date","=",day)]).set_index("instrument")
z["base_weight"]=base.loc[z.index].weight
z["proxy_weight"]=margin.loc[z.index].weight
s=z.reported.rank();budget=z.base_weight.sum()
raw=z.base_weight*(.5+(s-1)/(len(z)-1))
d=raw*budget/raw.sum()-z.base_weight
scale=(z.proxy_weight-z.base_weight).abs().sum()/d.abs().sum()
assert 0<scale<=1+1e-12
z["filing_weight"]=z.base_weight+scale*d
for k in ["reported","proxy"]:z[k+"_rank"]=z[k].rank(ascending=False)
z=z.sort_values("reported_rank");z.to_csv(out/"ranks.csv")
accounts.OUT=out;market=accounts.Market()
sample=base.iloc[0];j=market.symbols.get_indexer(z.index);i=int(sample.entry_idx);x=int(sample.exit_idx)
assert min(j)>=0
z["entry_buyable"]=market.buy[i,j]&market.members[i-1,j]
z["exit_sellable"]=market.sell[x,j]
z["h10_open_return"]=market.o[x,j]/market.o[i,j]-1
z["gross_contribution_bp"]=(z.filing_weight-z.base_weight)*z.h10_open_return*1e4
z.to_csv(out/"ranks.csv")
acc=[];hold=[]
for name,w in [("baseline",z.base_weight),("proxy",z.proxy_weight),("filing",z.filing_weight)]:
    t=base.copy();t.loc[w.index,"weight"]=w;t=t.reset_index().assign(model=name);hold.append(t)
    assert abs(t.weight.sum()-1)<1e-12
    for cost,bf,sf in [("base",.001,.002),("zero",0.,0.),("double",.002,.004)]:
        win,ledger,fail=replay(market,[],t,bf,sf);assert fail is None and len(win)==1
        acc.append(dict(model=name,cost=cost,net=win.net.iloc[0],fees=win.fee.iloc[0],entry=t.entry_date.iloc[0],exit=t.exit_date.iloc[0]))
a=pd.DataFrame(acc);a.to_csv(out/"accounts.csv",index=False);pd.concat(hold).to_parquet(out/"targets.parquet",index=False)
print(z.round(6));print(a)
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,here.parent/"64_mature_group_switch/account.py",Path(accounts.__file__),*[PRIVATE/(k+".parquet") for k in ["qfq_open","qfq_close","open","limits/daily","opening_trade_status_v2","daily_members","suspensions/daily"]],out/"accounts.csv",out/"ranks.csv",out/"targets.parquet"]})

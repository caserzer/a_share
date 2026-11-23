"""Reconcile actual one-way fees and turnover to netted fills, measured per H10 budget."""
from pathlib import Path
import sys
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import accounts,split,R,E
from execution import net_account
from core import sha,dump
out=HERE/"results";accounts.OUT=out
m=accounts.Market();rows=[]
for phase in [0,5]:
    dest=out/str(phase);t=pd.read_parquet(dest/"targets.parquet")
    for (model,late),g in t.groupby(["model",t.entry_date>=split]):
        end=int(g.exit_idx.max());d,o,status=net_account(m,g,end,"flat",.001,.002)
        assert status["valuation_complete"]
        d=d.set_index("date")
        by=o.groupby("date")[["sell","buy","fee"]].sum().reindex(d.index,fill_value=0.)
        np.testing.assert_allclose(by.fee,d.fees,atol=1e-12)
        u=o.assign(quantity=(o.buy-o.sell)/o.price).pivot(index="date",columns="instrument",values="quantity").reindex(index=d.index,columns=m.symbols).fillna(0.).cumsum().shift().fillna(0.)
        u=u.mask(u.abs()<1e-12,0)
        op=pd.DataFrame(m.marks["flat"][0][m.days.get_indexer(d.index)],index=d.index,columns=m.symbols)
        pre=(u*op).mask(u==0,0.).sum(axis=1,skipna=False)+d.cash.shift().fillna(1.)
        for h in g.drop_duplicates("entry_date").itertuples():
            seg=by[(by.index>=h.entry_date)&((by.index<h.exit_date)|((h.exit_idx==end)&(by.index==h.exit_date)))]
            rows.append(dict(phase=phase,scope="later" if late else "primary",model=model,date=h.signal_date,
                 turnover=(seg.buy+seg.sell).sum()/pre.at[h.entry_date],fees_bp=1e4*seg.fee.sum()/pre.at[h.entry_date]))
z=pd.DataFrame(rows);z.to_csv(out/"fees.csv",index=False)
s=z.groupby(["phase","scope","model"])[["turnover","fees_bp"]].mean().reset_index()
print(s.round(3).to_string(index=False))
s.to_csv(out/"fees_summary.csv",index=False)
dump(out/"fees_receipt.json",{str(f):sha(f) for f in [Path(__file__),out/"fees.csv",out/"fees_summary.csv"]})

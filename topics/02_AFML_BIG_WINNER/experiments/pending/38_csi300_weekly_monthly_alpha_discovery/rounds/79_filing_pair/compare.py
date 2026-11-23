from pathlib import Path
import pandas as pd,sys
from decimal import Decimal
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import dump,sha
s=out/"source_values.csv";v=pd.read_csv(s,dtype={"current":str,"prior":str});selected=pd.read_csv(out/"selected.csv")
c=PRIVATE/"qfq_close.parquet";days=pd.read_parquet(c,columns=[]).index
files=[s,c,out/"selected.csv",out/"selection_receipt.json",Path(__file__),here/"extract.py",out/"sources.csv"]
rows=[]
for stock,g in v.groupby("instrument"):
    ttm={};signal=pd.Timestamp(selected.set_index("instrument").loc[stock,"signal_date"]);cut=days[days.get_loc(signal)-1]
    assert pd.to_datetime(g.notice).max()<=cut
    for field,h in g.groupby("field"):
        a,q=h.set_index("period").loc[["2018FY","2019Q1"]].itertuples()
        ttm[field]=Decimal(a.current)+Decimal(q.current)-Decimal(q.prior)
    f=here.parents[2]/"24_conditional_return_distribution_exploration/outputs/local_cache/public_valuation"/(stock[2:]+".parquet")
    d=pd.read_parquet(f);z=d[pd.to_datetime(d.TRADE_DATE)==cut];assert len(z)==1
    proxy=float(z.PS_TTM.iloc[0]/z.PE_TTM.iloc[0]);reported=float(ttm["parent_profit"]/ttm["total_revenue"])
    rows.append(dict(instrument=stock,signal=signal,valuation_day=cut,**ttm,reported=reported,proxy=proxy,difference_bp=(proxy-reported)*1e4))
    files.append(f)
r=pd.DataFrame(rows);r.to_csv(out/"comparison.csv",index=False);print(r.to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,*sorted((out/"originals").glob("*.pdf")),out/"comparison.csv"]})

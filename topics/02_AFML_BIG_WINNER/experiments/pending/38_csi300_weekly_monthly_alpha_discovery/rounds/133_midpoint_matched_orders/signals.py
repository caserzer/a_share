from pathlib import Path
import sys
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump

src=here.parent/"132_crossing_midpoint_orders/results/signals.parquet"
q=pd.read_parquet(src).dropna(subset=["fresh_median","fresh_last"]).sort_values(["mid_idx","fresh_median","entrant"])
q["adaptive"]=q.switch.astype(float)
groups=q.groupby("mid_idx")
q["uniform"]=groups.adaptive.transform("mean")
q["reverse"]=groups.cumcount().lt(groups.adaptive.transform("sum")).astype(float)
assert np.allclose(groups.reverse.sum(),groups.adaptive.sum())
for rule in ["uniform","reverse"]:
    np.testing.assert_allclose((q[rule]*q.weight).groupby(q.mid_idx).sum(),(q.adaptive*q.weight).groupby(q.mid_idx).sum(),atol=1e-12)
q.to_parquet(out/"allocations.parquet",index=False)
dump(out/"signal_receipt.json",{str(f):sha(f) for f in [src,here/"PROTOCOL.md",Path(__file__),out/"allocations.parquet"]})

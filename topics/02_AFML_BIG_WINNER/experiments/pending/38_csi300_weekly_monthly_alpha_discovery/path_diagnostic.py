"""Describe the timing of model disagreement on the frozen signal-date universe."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE = Path(__file__).resolve().parent
EP = HERE.parent/"37_momentum_reversal_joint_alpha_h10"
sys.path.insert(0,str(EP/"code"))
from core import PRIVATE
op = pd.read_parquet(PRIVATE/"qfq_open.parquet")
scores = pd.read_parquet(EP/"extensions/intraday_reversal_20261122/results/scores.parquet").dropna(subset=["exit_date"])
rows = []
for date,g in scores.groupby("signal_date"):
    e = g.entry_idx.iloc[0]
    rank = g.RANK_MSE_78_d.eq(10)
    orig = g.E1_78_d.eq(10)
    for group,mask in [("both",rank&orig),("rank_only",rank&~orig),("e1_only",orig&~rank),("neither",~(orig|rank))]:
        names = g.loc[mask,"instrument"]
        for lo,hi in [(0,5),(5,10),(10,20)]:
            ret = op.iloc[e+hi][names]/op.iloc[e+lo][names]-1 if e+hi<len(op) else pd.Series(np.nan,index=names)
            rows.append(dict(signal_date=date,scope="primary" if g.exit_date.iloc[0]<=pd.Timestamp("2025-03-03") else "later",
                             group=group,start_day=lo,end_day=hi,selected=len(names),priced=ret.count(),gross=ret.mean()))
pd.DataFrame(rows).to_csv(HERE/"results/disagreement_paths.csv",index=False)

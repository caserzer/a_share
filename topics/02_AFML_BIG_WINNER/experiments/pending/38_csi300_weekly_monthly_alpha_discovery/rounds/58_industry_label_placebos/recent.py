from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
prev=here.parent/"38_all_phases"
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"21_dual_support"),str(prev)]
from ship_action import replay_with_ship_action
from evaluate import accounts
out=here/"results"
t=pd.read_parquet(out/"targets.parquet")
for phase,g in t[t.year>=2021].groupby("phase"):
    d=out/str(phase);d.mkdir(exist_ok=True);accounts.OUT=d
    replay_with_ship_action(g,d)
    a=pd.read_csv(d/"accounts.csv").set_index(["scope","cost","model"])
    assert a.valuation_complete.all()
    w=pd.read_csv(d/"windows.csv")
    np.testing.assert_allclose((1+w.net).groupby([w.scope,w.cost,w.model]).prod().sort_index(),a.nav.sort_index(),atol=1e-10)
    print(phase,flush=True)

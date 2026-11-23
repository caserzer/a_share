from pathlib import Path
import sys
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump

out=here/"results"
source=out/"quarter_records.parquet"
signals=out/"signals.parquet"
raw=pd.read_parquet(source)
h=pd.read_parquet(signals)
checks=0
for day in h.groupby(h.signal_date.dt.to_period("Q")).signal_date.min():
    # A date-prefix rebuild does not rely on the transaction-time join used to generate signals.
    known=raw[raw.notice<day].sort_values("period")
    histories={k:g.set_index("period") for k,g in known.groupby("code")}
    for row in h[h.signal_date==day].itertuples():
        history=histories.get(row.instrument[2:])
        expected=np.nan
        if history is not None:
            last=history.index[-1]
            periods=pd.date_range(end=last,periods=3,freq="QE")
            counts=history["count"].reindex(periods)
            if counts.notna().all() and (day-last).days<=180:
                expected=-np.log(counts.iloc[-1]/counts.iloc[-2])
                np.testing.assert_allclose(row.previous,-np.log(counts.iloc[-2]/counts.iloc[0]))
        applied=row.recent if np.isfinite(row.previous) else np.nan
        assert np.isclose(applied,expected,equal_nan=True), (day,row.instrument,applied,expected)
        checks+=1
dump(out/"prefix_check_receipt.json",{"checked":checks,"hashes":{str(f):sha(f) for f in [source,signals,Path(__file__)]}})
print(checks)

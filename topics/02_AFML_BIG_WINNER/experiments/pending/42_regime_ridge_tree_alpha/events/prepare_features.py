"""Rebuild each whole CSI800 test cross-section and verify the frozen Ridge predictions."""
from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
SRC=next(BASE.glob('40_*/lightgbm/followup/csi800_69'))
sys.path.insert(0,str(SRC))
import scores as original
OUT=HERE/'results'/'features'
def main():
    OUT.mkdir(exist_ok=True)
    f=original.build().sort_values(original.KEY)
    s=pd.read_parquet(SRC/'results/scores.parquet').sort_values(original.KEY)
    pd.testing.assert_frame_equal(f[original.KEY].reset_index(drop=True),s[original.KEY].reset_index(drop=True))
    f['R']=s.refit_R.to_numpy()
    receipts=[]
    for q,g in f.groupby(f.signal_date.dt.to_period('Q')):
        cfg=json.loads((SRC/'results/models/refit'/str(q)/'ridge.json').read_text())
        r=original.predict(g[original.COLS],cfg)
        err=np.abs(r-g.R).max()
        assert err<1e-10
        g.to_parquet(OUT/(str(q)+'.parquet'),compression='zstd',index=False)
        receipts.append({'quarter':str(q),'rows':len(g),'max_parity_error':err})
    pd.DataFrame(receipts).to_csv(OUT/'parity.csv',index=False)
if __name__=='__main__':main()

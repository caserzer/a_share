from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import R,E,PRIVATE,evaluate
from core import sha,dump
OUT=HERE/"results"
OUT.mkdir(exist_ok=True)
targets_file=ROOT/"results/targets.parquet"
cp=PRIVATE/"qfq_close.parquet"
tp=PRIVATE/"turnover_rate.parquet"
close=pd.read_parquet(cp)
turn=pd.read_parquet(tp).reindex_like(close)
def premium(prices,rate):
    surviving=np.vstack([np.cumprod((1-rate[1:])[::-1],axis=0)[::-1],np.ones(rate.shape[1])])
    weights=rate*surviving
    with np.errstate(invalid="ignore",divide="ignore"):
        return np.log(prices[-1]*weights.sum(axis=0)/(prices*weights).sum(axis=0))
def tilt(g,signal):
    t=g.copy()
    valid=signal.dropna()
    if len(valid)>1:
        factor=(valid.rank(method="average")-1)/(len(valid)-1)+.5
        t.loc[valid.index,"weight"]*=factor
    assert np.isclose(t.weight.sum(),1)
    return t

def main():
    base=pd.read_parquet(targets_file).query("model in [@E,@R]")
    portfolios=[base];signals=[]
    for date,g in base[base.model==R].groupby("signal_date"):
        i=close.index.get_loc(date)
        px=close.iloc[i-119:i+1][g.instrument].to_numpy()
        rate=turn.iloc[i-119:i+1][g.instrument].clip(0,1).to_numpy()
        real=premium(px,rate)
        fixed=premium(px,np.broadcast_to(rate.mean(axis=0),rate.shape))
        for name,values in [("volume_location",real-fixed),("actual_cost",real),("constant_cost",fixed)]:
            f=pd.Series(values,index=g.index).replace([np.inf,-np.inf],np.nan)
            portfolios.append(tilt(g,f).assign(model=name))
            signals.append(g[["signal_date","instrument"]].assign(signal=f,model=name))
    pd.concat(portfolios).to_parquet(OUT/"targets.parquet",index=False)
    pd.concat(signals).to_parquet(OUT/"signals.parquet",index=False)
    dump(OUT/"selection.json",{str(p.relative_to(ROOT.parent)):sha(p) for p in [tp,cp,targets_file,HERE/"PROTOCOL.md",Path(__file__),OUT/"targets.parquet",HERE.parent/"02_adaptive_revision/evaluate.py"]})
    evaluate(OUT,9)
if __name__=="__main__":
    main()

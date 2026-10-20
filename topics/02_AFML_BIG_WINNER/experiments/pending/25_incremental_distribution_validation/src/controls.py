"""Fixed-seed synthetic positive and shuffled-label negative controls."""
import numpy as np
import pandas as pd
from core import *


def main():
    rng=np.random.default_rng(2500)
    months=120; stocks=40
    dates=np.repeat(pd.date_range('2000-01-31',periods=months,freq='ME'),stocks)
    signal=rng.choice([-1.,1.],size=len(dates))
    y=.22*signal+rng.normal(0,.07,len(signal))
    frame=pd.DataFrame(dict(date=dates,vol63=signal,log_cap=rng.normal(size=len(signal)),y_6=y))
    train=frame.iloc[:60*stocks].copy();test=frame.iloc[60*stocks:].copy()
    outputs=[];detail=[]
    for name in ['positive_known_signal','negative_shuffled_labels']:
        tr=train.copy();te=test.copy()
        if name.startswith('negative'):
            tr['y_6']=rng.permutation(tr.y_6.to_numpy());te['y_6']=rng.permutation(te.y_6.to_numpy())
        model=fit_model(tr,6,'M_R');a,_=predict_atoms(model,te,'M_R')
        base=np.tile(np.quantile(tr.y_6,GRID),(len(te),1))
        s=score(a,te.y_6);b=score(base,te.y_6)
        monthly=pd.DataFrame(dict(date=te.date,delta=s.crps.to_numpy()-b.crps.to_numpy())).groupby('date').delta.mean()
        ci=interval(monthly.to_numpy(),6)
        passed=ci['high95']<-.02 if name.startswith('positive') else ci['low95']>-.005
        outputs.append(dict(control=name,passed=bool(passed),model_crps=float(s.crps.mean()),baseline_crps=float(b.crps.mean()),**ci))
        detail.extend(dict(control=name,date=str(date.date()),delta=float(value)) for date,value in monthly.items())
    write_json(OUT/'controls.json',dict(controls=outputs,all_passed=all(r['passed'] for r in outputs),
        interpretation='pipeline controls on synthetic data only; not market evidence',negative_test='no spurious CRPS improvement >=0.005; no guarantee all random permutations pass'))
    pd.DataFrame(detail).to_csv(OUT/'control_monthly_scores.csv',index=False)
    print(outputs,flush=True)
    assert all(r['passed'] for r in outputs)

if __name__=='__main__':main()

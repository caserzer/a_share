"""Recompute per-date utilities and fixed-block interval decisions from predictions."""
import pandas as pd
from scipy.stats import spearmanr
from common import *


def interval(values,alpha):
    v=np.asarray(values,float);v=v[np.isfinite(v)];n=len(v)
    if n<12:return np.array([np.nan,np.nan])
    starts=np.random.default_rng(3501).integers(n,size=(2000,(n+5)//6))
    draws=np.stack([((starts+offset)%n) for offset in range(6)],axis=-1).reshape(2000,-1)[:,:n]
    return np.quantile(v[draws].mean(axis=1),[alpha/2,1-alpha/2])


def run():
    out=ROOT/'outputs/r131';receipt=json.loads((out/'evaluation_summary.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h,p
    for p,h in receipt['evaluation_files'].items():assert sha(out/p)==h,p
    dest=out/'evaluation/outputs/r02';d=pd.read_parquet(out/'predictions.parquet');metrics=pd.read_csv(dest/'date_metrics.csv',parse_dates=['date']);groups=['era','level','cohort','method','task','horizon'];index=metrics.set_index(groups+['date']);checks=0
    for key,g in d.groupby(groups+['date']):
        row=index.loc[key];valid=g[g.y.notna()];assert row.n_signal==len(g) and row.n_mature==len(valid)
        if key[4]=='return':value=spearmanr(valid.prediction,valid.y).statistic if len(valid)>=20 and valid.prediction.nunique()>1 else np.nan
        else:value=-float(((valid.prediction-valid.y)**2).mean()) if len(valid) else np.nan
        assert np.isclose(value,row.utility,rtol=1e-12,atol=1e-12,equal_nan=True)
        k=max(1,int(np.ceil(len(g)/5)));assert row.alerts_signal==k
        if key[4]=='return':
            top=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(k);value=top.excess.mean() if top.y.notna().all() else np.nan
            assert np.isclose(value,row.top_excess,rtol=1e-12,atol=1e-12,equal_nan=True)
        checks+=1
    inc=pd.read_csv(dest/'paired_increments.csv');keys=['era','level','cohort','task','horizon']
    for row in inc.to_dict('records'):
        g=metrics
        for k in keys:g=g[g[k].eq(row[k])]
        wide=g.pivot(index='date',columns='method',values='utility').dropna();x=wide[row['cohort']]-wide.F;assert len(x)==row['months']
        assert np.isclose(x.mean(),row['increment'],atol=1e-12,rtol=1e-12,equal_nan=True)
        for alpha,lo,hi in [(.05,'ci95_low','ci95_high'),(.05/48,'adjusted_low','adjusted_high')]:assert np.allclose(interval(x,alpha),[row[lo],row[hi]],atol=1e-12,rtol=1e-12,equal_nan=True)
        expected='historical_increment_supported' if row['horizon']==20 and len(x)>=24 and row['adjusted_low']>0 else 'not_established' if row['horizon']==20 else 'secondary_descriptive';assert row['result']==expected
    old=pd.read_csv(ROOT/'outputs/r02/paired_increments.csv');pair=old.merge(inc,on=keys,suffixes=('_old','_new'),validate='one_to_one');p=pair[pair.horizon.eq(20)];n=int(p.result_old.ne(p.result_new).sum());assert n==len(receipt['primary_conclusion_changes'])
    js(out/'evaluation_verification.json',dict(status='PASS',date_metrics_checked=checks,paired_intervals_checked=len(inc),primary_conclusion_changes=n,scope='Original IC/Brier utilities, fixed alert rule and interval decisions; historical research only'))
    print('PASS',checks,len(inc),n)

if __name__=='__main__':run()

"""Paired date-level utility and calendar-gap-preserving uncertainty."""
import pandas as pd
from scipy.stats import norm
from common import *
G=['era','level','cohort','task','horizon']

def interval(g,lag):
    q=g.dropna(subset=['delta']);n=len(q)
    if n<2:return [np.nan]*5
    x=q.delta.to_numpy();u=x-x.mean();months=q.date.dt.to_period('M').astype('int64').to_numpy()
    covariance=float(u@u)
    for step in range(1,lag+1):
        pairs=(months[:,None]-months[None,:])==step
        covariance+=2*(1-step/(lag+1))*float((u[:,None]*u[None,:])[pairs].sum())
    se=np.sqrt(max(covariance,0))/n;z=norm.ppf(1-.05/120)
    return [se,x.mean()-1.96*se,x.mean()+1.96*se,x.mean()-z*se,x.mean()+z*se]

def run():
    out=ROOT/'outputs/r106';p=pd.read_parquet(out/'paired_predictions.parquet');rows=[]
    for key,g in p.groupby(G+['date']):
        v=g[g.y.notna()];n=len(v);k=max(1,int(np.ceil(len(g)*.2)))
        old=set(g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(k).industry_code)
        new=set(g.sort_values(['unique_prediction','industry_code'],ascending=[False,True]).head(k).industry_code)
        r=dict(zip(G+['date'],key),n_signal=len(g),n_mature=n,selected=k,shared_selected=len(old&new),baseline_utility=np.nan,unique_utility=np.nan,delta=np.nan,logloss_reduction=np.nan,frozen_calibration_brier_reduction=np.nan)
        if key[3]=='return':
            if n>=20 and v.prediction.nunique()>1 and v.unique_prediction.nunique()>1:
                r.update(baseline_utility=v.prediction.corr(v.y,method='spearman'),unique_utility=v.unique_prediction.corr(v.y,method='spearman'))
        elif n:
            old_brier=float(((v.prediction-v.y)**2).mean());new_brier=float(((v.unique_prediction-v.y)**2).mean())
            def loss(values):
                a=np.clip(values,1e-15,1-1e-15);return -(v.y*np.log(a)+(1-v.y)*np.log(1-a)).mean()
            r.update(baseline_utility=-old_brier,unique_utility=-new_brier,logloss_reduction=loss(v.prediction)-loss(v.unique_prediction),frozen_calibration_brier_reduction=old_brier-float(((v.unique_frozen_calibration_prediction-v.y)**2).mean()))
        r['delta']=r['unique_utility']-r['baseline_utility'];rows.append(r)
    dates=pd.DataFrame(rows);dates.to_csv(out/'paired_date_metrics.csv',index=False);annual=[];summary=[]
    for key,g in dates.assign(year=dates.date.dt.year).groupby(G+['year']):
        annual.append(dict(zip(G+['year'],key),months=int(g.delta.notna().sum()),mean_delta=g.delta.mean(),mean_logloss_reduction=g.logloss_reduction.mean(),selected=int(g.selected.sum()),shared_selected=int(g.shared_selected.sum())))
    for key,g in dates.groupby(G):
        lag=3 if key[-1]==20 else 6;se,lo,hi,alo,ahi=interval(g,lag)
        yearly=g.assign(year=g.date.dt.year).groupby('year').delta.mean().dropna()
        summary.append(dict(zip(G,key),metric='IC_improvement' if key[3]=='return' else 'Brier_reduction',months=int(g.delta.notna().sum()),mean_delta=g.delta.mean(),standard_error=se,low95=lo,high95=hi,family60_low=alo,family60_high=ahi,positive_years=int(yearly.gt(0).sum()),evaluated_years=len(yearly),mean_logloss_reduction=g.logloss_reduction.mean(),mean_frozen_calibration_brier_reduction=g.frozen_calibration_brier_reduction.mean(),selected=int(g.selected.sum()),shared_selected=int(g.shared_selected.sum()),status='historical_descriptive_not_adopted'))
    pd.DataFrame(annual).to_csv(out/'annual_metrics.csv',index=False);pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
    js(out/'evaluation_receipt.json',dict(prediction_sha256=sha(out/'paired_predictions.parquet'),code_sha256=sha(__file__),date_rows=len(dates),comparison_groups=len(summary),family_size=60,outputs={n:sha(out/n) for n in ['paired_date_metrics.csv','annual_metrics.csv','summary.csv']}))
    print(pd.DataFrame(summary)[G+['months','mean_delta','family60_low','family60_high']].to_string(index=False))

if __name__=='__main__':run()

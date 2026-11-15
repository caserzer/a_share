import pandas as pd
from sklearn.metrics import roc_auc_score,average_precision_score
from common import *
from evaluate_r01 import bootstrap

def run():
    out=ROOT/'outputs/r16';d=pd.read_parquet(out/'raw_predictions.parquet');date_rows=[];bins=[]
    keys=['cohort','method','task','horizon']
    for key,g in d.groupby(keys+['date']):
        top=g.sort_values(['raw_score','industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(g))));v=g[g.y.notna()];selected=top[top.y.notna()]
        date_rows.append(dict(zip(keys+['date'],key),origins=len(g),known=len(v),unknown=len(g)-len(v),alerts=len(top),known_alerts=len(selected),
            brier=((v.raw_score-v.y)**2).mean(),baseline_brier=((v.training_mean-v.y)**2).mean(),precision=selected.y.mean(),recall=selected.y.sum()/v.y.sum() if v.y.sum()>0 else np.nan))
    dates=pd.DataFrame(date_rows);dates.to_csv(out/'raw_date_metrics.csv',index=False)
    dates.assign(year=dates.date.dt.year).groupby(keys+['year']).agg(months=('brier','count'),brier=('brier','mean'),baseline_brier=('baseline_brier','mean'),alerts_per_month=('alerts','mean'),precision=('precision','mean'),recall=('recall','mean')).to_csv(out/'raw_annual.csv')
    for key,g in d[d.y.notna()].groupby(keys):
        g=g.assign(bin=np.minimum((g.raw_score*10).astype(int),9))
        for bucket,z in g.groupby('bin'):bins.append(dict(zip(keys,key),bin=bucket,rows=len(z),score=z.raw_score.mean(),rate=z.y.mean()))
    pd.DataFrame(bins).to_csv(out/'raw_reliability.csv',index=False)
    increments=[]
    for key,g in dates[dates.cohort=='FD'].groupby(['task','horizon']):
        paired=g.pivot(index='date',columns='method',values='brier').dropna();delta=paired.F-paired.FD;lo,hi=bootstrap(delta,.05/3)
        increments.append(dict(task=key[0],horizon=key[1],months=len(delta),brier_reduction=delta.mean(),adjusted_low=lo,adjusted_high=hi,status='uncalibrated_diagnostic_not_acceptance'))
    pd.DataFrame(increments).to_csv(out/'raw_paired_increments.csv',index=False)
if __name__=='__main__':run()

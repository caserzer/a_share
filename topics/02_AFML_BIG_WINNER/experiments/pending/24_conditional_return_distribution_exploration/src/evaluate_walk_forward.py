"""R14A: monthly paired probability scores and robust time-block uncertainty."""
import numpy as np
import pandas as pd
from run_monthly_walk_forward import DEST
from run_four_horizons import OUT,BINS,BIN_NAMES
from evaluate_four_horizons import block_interval
METRICS=['brier','multiclass_brier','crps','below_q05','coverage90']


def evaluate():
    d=pd.concat([pd.read_parquet(DEST/f'predictions_{h}m.parquet') for h in [1,3,6]],ignore_index=True)
    s=d[d.actual.notna()].copy()
    m=s.groupby(['months','date','model'])[METRICS].mean().reset_index()
    m.to_csv(DEST/'monthly_scores.csv',index=False)
    m.groupby(['months','model'])[METRICS].mean().to_csv(DEST/'summary.csv')
    m.groupby(['months','model',m.date.dt.year])[METRICS].mean().to_csv(DEST/'annual_scores.csv')
    m['phase']=np.where(m.date<'2024-01-01','2021_2023','2024_plus')
    m.groupby(['months','phase','model'])[METRICS].mean().to_csv(DEST/'phase_scores.csv')
    comparisons=[]
    for h in [1,3,6]:
        for phase,selection in [('all',m.months==h),('2021_2023',(m.months==h)&(m.phase=='2021_2023')),('2024_plus',(m.months==h)&(m.phase=='2024_plus'))]:
            for metric in ['brier','multiclass_brier','crps']:
                wide=m[selection].pivot(index='date',columns='model',values=metric)
                for baseline in ['expanding_empirical','recent36_empirical']:
                    for model in ['peers_risk_size','peers_risk_size_36m']:
                        delta=(wide[model]-wide[baseline]).dropna()
                        for block in [6,12]:
                            lo,hi=block_interval(delta,block)
                            comparisons.append(dict(months=h,phase=phase,model=model,baseline=baseline,metric=metric,block_months=block,difference=delta.mean(),lower95=lo,upper95=hi,origin_months=len(delta)))
    pd.DataFrame(comparisons).to_csv(DEST/'baseline_comparisons.csv',index=False)
    calibration=[]
    for (h,model),g in s.groupby(['months','model']):
        labels=np.searchsorted(BINS,g.actual,side='right')
        for event in ['up','down',*BIN_NAMES]:
            observed=(g.actual>0).astype(float) if event=='up' else ((g.actual<0).astype(float) if event=='down' else (labels==BIN_NAMES.index(event)).astype(float))
            z=g.assign(observed=observed,bucket=np.floor(g[f'p_{event}']*10).clip(upper=9))
            for bucket,b in z.groupby('bucket'):
                calibration.append(dict(months=h,model=model,event=event,bin=int(bucket),rows=len(b),origin_months=b.date.nunique(),predicted=b[f'p_{event}'].mean(),observed=b.observed.mean()))
    pd.DataFrame(calibration).to_csv(DEST/'probability_calibration.csv',index=False)
    quarterly=[]
    for h in [1,3,6]:
        old=pd.read_parquet(OUT/f'r10_four_horizons/predictions_{h}m.parquet')
        old=old[(old.model=='peers_risk_size')&old.actual.notna()]
        new=s[(s.months==h)&(s.model=='peers_risk_size')]
        joined=new.merge(old,on=['date','instrument'],suffixes=('_monthly','_quarterly'),validate='one_to_one')
        np.testing.assert_allclose(joined.actual_monthly,joined.actual_quarterly)
        for metric in ['brier','multiclass_brier','crps']:
            delta=(joined[f'{metric}_monthly']-joined[f'{metric}_quarterly']).groupby(joined.date).mean()
            for block in [6,12]:
                lo,hi=block_interval(delta,block)
                quarterly.append(dict(months=h,metric=metric,difference=delta.mean(),lower95=lo,upper95=hi,block_months=block,origin_months=len(delta),rows=len(joined)))
    pd.DataFrame(quarterly).to_csv(DEST/'monthly_vs_quarterly.csv',index=False)
    print(m.groupby(['months','model'])[METRICS].mean().to_string())


if __name__=='__main__':evaluate()

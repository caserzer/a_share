"""R15: paired factorial effects, period stability, and full probability calibration."""
import numpy as np
import pandas as pd
from build_three_factor_panel import DEST
from run_three_factor_ablation import VARIANTS
from run_four_horizons import BINS,BIN_NAMES
from evaluate_four_horizons import block_interval
METRICS=['brier','multiclass_brier','crps','below_q05','coverage90']


def factorial_edges():
    reverse={frozenset(groups):name for name,groups in VARIANTS.items()}
    edges=[]
    for factor in 'CPF':
        for name,groups in VARIANTS.items():
            if factor not in groups:
                edges.append(dict(factor=factor,background=name,without=name,with_model=reverse[frozenset([*groups,factor])]))
    return edges


def evaluate():
    d=pd.concat([pd.read_parquet(DEST/f'predictions_{h}m.parquet') for h in [1,3,6]],ignore_index=True)
    s=d[d.actual.notna()].copy()
    m=s.groupby(['months','date','model'])[METRICS].mean().reset_index()
    m['phase']=np.where(m.date<'2024-01-01','2021_2023','2024_plus')
    m.to_csv(DEST/'monthly_scores.csv',index=False)
    m.groupby(['months','model'])[METRICS].mean().to_csv(DEST/'summary.csv')
    m.groupby(['months','phase','model'])[METRICS].mean().to_csv(DEST/'phase_scores.csv')
    m.groupby(['months','model',m.date.dt.year])[METRICS].mean().to_csv(DEST/'annual_scores.csv')
    effects=[];contrasts=[]
    for h in [1,3,6]:
        for phase in ['all','2021_2023','2024_plus']:
            selection=(m.months==h)&((m.phase==phase) if phase!='all' else True)
            for metric in ['brier','multiclass_brier','crps']:
                w=m[selection].pivot(index='date',columns='model',values=metric)
                for edge in factorial_edges():
                    delta=(w[edge['with_model']]-w[edge['without']]).dropna()
                    for block in [6,12]:
                        lo,hi=block_interval(delta,block)
                        effects.append(dict(months=h,phase=phase,metric=metric,block_months=block,**edge,
                            difference=delta.mean(),lower95=lo,upper95=hi,origin_months=len(delta)))
                for model in VARIANTS:
                    for baseline in ['B','historical']:
                        if model==baseline:continue
                        delta=(w[model]-w[baseline]).dropna()
                        for block in [6,12]:
                            lo,hi=block_interval(delta,block)
                            contrasts.append(dict(months=h,phase=phase,metric=metric,block_months=block,model=model,baseline=baseline,
                                difference=delta.mean(),lower95=lo,upper95=hi,origin_months=len(delta)))
    pd.DataFrame(effects).to_csv(DEST/'factor_effects.csv',index=False)
    pd.DataFrame(contrasts).to_csv(DEST/'baseline_comparisons.csv',index=False)
    reliability=[]
    for (h,model),g in s.groupby(['months','model']):
        classes=np.searchsorted(BINS,g.actual,side='right')
        for event in ['up','down',*BIN_NAMES]:
            obs=(g.actual>0).astype(float) if event=='up' else ((g.actual<0).astype(float) if event=='down' else (classes==BIN_NAMES.index(event)).astype(float))
            z=g.assign(observed=obs,bucket=np.floor(g[f'p_{event}']*10).clip(upper=9))
            for bucket,b in z.groupby('bucket'):
                reliability.append(dict(months=h,model=model,event=event,bin=int(bucket),rows=len(b),origin_months=b.date.nunique(),
                    predicted=b[f'p_{event}'].mean(),observed=b.observed.mean()))
    pd.DataFrame(reliability).to_csv(DEST/'probability_calibration.csv',index=False)
    print(m.groupby(['months','model'])[METRICS].mean().round(6).to_string())


if __name__=='__main__':evaluate()

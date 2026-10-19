"""Coverage-only optimistic ceiling for models that leave uncovered forecasts at B.

Uses realized outcomes for a mathematical diagnostic, never as a forecast.
"""
import numpy as np
import pandas as pd
from prepare_panel import OUT
from build_analyst_features import PANEL
from fetch_historical_reports import DEST


def run():
    features=pd.read_parquet(PANEL,columns=['date','instrument','analyst_available','target_available'])
    rows=[]
    for h in [1,3,6]:
        base=pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{h}m.parquet')
        base=base[(base.model=='B')&base.actual.notna()].merge(features,on=['date','instrument'],validate='one_to_one')
        base['accuracy']=np.where(base.actual!=0,(base.p_up>base.p_down)==(base.actual>0),np.nan)
        for coverage in ['analyst_available','target_available']:
            for metric in ['brier','multiclass_brier','crps','accuracy']:
                d=base[['date',metric,coverage]].copy()
                if metric=='accuracy':
                    d['oracle']=np.where(d[coverage]&d[metric].notna(),1,d[metric])
                else:
                    d['oracle']=np.where(d[coverage],0,d[metric])
                m=d.groupby('date')[[metric,'oracle']].mean().mean()
                ceiling=m['oracle']/m[metric]-1 if metric=='accuracy' else 1-m['oracle']/m[metric]
                rows.append(dict(months=h,coverage=coverage,metric=metric,relative_improvement_ceiling=ceiling,
                    twenty_percent_possible_under_ceiling=bool(ceiling>=.2),
                    warning='ORACLE COVERAGE BOUND ONLY: perfect outcomes on covered rows, unchanged B elsewhere; not a prediction'))
    pd.DataFrame(rows).to_csv(DEST/'coverage_ceiling_oracle_only.csv',index=False)
    print(pd.DataFrame(rows).drop(columns=['warning']).to_string(index=False))


if __name__=='__main__':run()

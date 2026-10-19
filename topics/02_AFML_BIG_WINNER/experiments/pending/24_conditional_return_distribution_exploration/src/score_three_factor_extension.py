"""R15 posthoc new-label sensitivity. Labels were already examined in R14."""
import numpy as np
import pandas as pd
from build_three_factor_panel import DEST,OUT
from run_three_factor_ablation import CACHE
from run_four_horizons import BIN_NAMES,BINS,probability_stats
from evaluate_three_factor_ablation import factorial_edges


def run():
    dest=DEST/'newly_matured_sensitivity';dest.mkdir(exist_ok=True)
    labels=pd.read_parquet(OUT/'r14_newly_matured/new_labels.parquet')
    results=[]
    for h in [1,3,6]:
        predictions=pd.read_parquet(DEST/f'predictions_{h}m.parquet')
        selected=predictions.merge(labels[labels.months==h],on=['date','instrument','months'],suffixes=('_old',''),validate='many_to_one')
        assert selected.actual_old.isna().all()
        for (model,date),g in selected.groupby(['model','date']):
            stamp=str(date.date())
            keys=pd.read_parquet(CACHE/f'{h}_{stamp}_keys.parquet')
            ix=pd.MultiIndex.from_frame(keys).get_indexer(pd.MultiIndex.from_frame(g[['date','instrument']]))
            assert (ix>=0).all()
            atoms=np.load(CACHE/f'{h}_{stamp}_{model}.npz')['atoms'][ix]
            base=g[['date','instrument','months','model','actual','label_end','target_date','status']].reset_index(drop=True)
            stats=probability_stats(atoms,base.actual)
            for c in ['p_up','p_down','p_zero',*[f'p_{n}' for n in BIN_NAMES],'q05','q50','q95']:stats[c]=g[c].to_numpy()
            y=base.actual.to_numpy();stats['brier']=(stats.p_up.to_numpy()-(y>0))**2
            probs=stats[[f'p_{n}' for n in BIN_NAMES]].to_numpy()
            stats['multiclass_brier']=((probs-np.eye(5)[np.searchsorted(BINS,y,side='right')])**2).sum(axis=1)
            stats['below_q05']=(y<stats.q05.to_numpy()).astype(float)
            stats['coverage90']=((y>=stats.q05.to_numpy())&(y<=stats.q95.to_numpy())).astype(float)
            stats.loc[~np.isfinite(y),['brier','multiclass_brier','below_q05','coverage90']]=np.nan
            results.append(pd.concat([base,stats],axis=1))
    d=pd.concat(results,ignore_index=True);d.to_parquet(dest/'scored_predictions.parquet',index=False)
    summaries=[]
    metrics=['brier','multiclass_brier','crps','below_q05','coverage90']
    for scope,status in [('stable_source',['valid']),('including_source_uncertainty',['valid','source_unstable'])]:
        z=d[d.status.isin(status)]
        m=z.groupby(['months','date','model'])[metrics].mean().reset_index();m['scope']=scope;summaries.append(m)
    monthly=pd.concat(summaries,ignore_index=True);monthly.to_csv(dest/'monthly_scores.csv',index=False)
    summary=monthly.groupby(['scope','months','model'])[metrics].mean();summary.to_csv(dest/'summary.csv')
    d[d.model=='B'].groupby(['months','date','status']).size().rename('rows').to_csv(dest/'coverage.csv')
    effects=[]
    for h in [1,3,6]:
        for metric in ['brier','multiclass_brier','crps']:
            w=monthly[(monthly.months==h)&(monthly.scope=='stable_source')].pivot(index='date',columns='model',values=metric)
            for edge in factorial_edges():
                delta=w[edge['with_model']]-w[edge['without']]
                effects.append(dict(months=h,metric=metric,**edge,difference=delta.mean(),origin_months=len(delta),evidence='posthoc, previously examined labels, too few origins for stable inference'))
    pd.DataFrame(effects).to_csv(dest/'factor_effects.csv',index=False)
    print(summary.loc['stable_source'].round(6).to_string())


if __name__=='__main__':run()

import numpy as np,pandas as pd
from scipy.stats import spearmanr
from common import *
from evaluate_ranking import predictions,block_ci

def main():
 y=pd.read_parquet(PRIVATE/'labels.parquet');source=pd.read_csv(EP.parent/'30_pit_data_foundation_v1/outputs/pit_v5/legacy_qfq_comparison.csv');bad=set(source.loc[source.within_legacy_rounding_tolerance<source.rows,'instrument']);summary=[];detail=[]
 for scheme in ['expanding','rolling36']:
  p,_=predictions(scheme);p=p.loc[p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])];wide=p.pivot(index=['signal_date','instrument'],columns='model_id',values='score').reset_index().merge(y[['signal_date','instrument','h10']],on=['signal_date','instrument'],validate='one_to_one')
  for model in ['E0-MOM','E0-REV','E0-RES','E0-MIX','E1','E2','E3']:
   rows=[]
   for date,g in wide.groupby('signal_date'):
    full=g.dropna(subset=[model,'h10']);clean=full.loc[~full.instrument.isin(bad)];value=spearmanr(clean[model],clean.h10).statistic if len(clean)>=100 and clean[model].nunique()>1 else np.nan
    rows.append(dict(scheme=scheme,comparison=model+'_exclude_disputed_qfq',signal_date=date,observations=len(clean),removed=len(full)-len(clean),rank_ic=value))
   r=pd.DataFrame(rows);lo,hi=block_ci(r.rank_ic);summary.append(dict(scheme=scheme,comparison=model+'_exclude_disputed_qfq',mean_rank_ic=r.rank_ic.mean(),ci_low=lo,ci_high=hi,weeks=r.rank_ic.count(),removed_rows=int(r.removed.sum())));detail.extend(rows)
  for model,control in [('E2',v) for v in ['E0-MOM','E0-REV','E0-RES','E0-MIX','E1','E3']]+[('E3','E1')]:
   rows=[]
   for date,g in wide.groupby('signal_date'):
    g=g.dropna(subset=[model,control,'h10']);value=np.nan
    if len(g)>=100 and g[model].nunique()>1 and g[control].nunique()>1:value=spearmanr(g[model],g.h10).statistic-spearmanr(g[control],g.h10).statistic
    rows.append(dict(scheme=scheme,comparison=model+'_minus_'+control+'_same_securities',signal_date=date,observations=len(g),rank_ic=value))
   r=pd.DataFrame(rows);lo,hi=block_ci(r.rank_ic);summary.append(dict(scheme=scheme,comparison=model+'_minus_'+control+'_same_securities',mean_rank_ic=r.rank_ic.mean(),ci_low=lo,ci_high=hi,weeks=r.rank_ic.count()));detail.extend(rows)
 pd.DataFrame(summary).to_csv(OUT/'sensitivity/ranking_paired_source_summary.csv',index=False);pd.DataFrame(detail).to_csv(OUT/'sensitivity/ranking_paired_source_weekly.csv',index=False)
 save_json(OUT/'sensitivity/provider_disagreement.json',dict(source_sha256=sha(EP.parent/'30_pit_data_foundation_v1/outputs/pit_v5/legacy_qfq_comparison.csv'),excluded_instruments=sorted(bad&set(y.instrument)),selection='pre-existing source comparison; no outcome-based choice'))
if __name__=='__main__':main()

"""Post-delivery Pearson IC diagnostic; no retraining or change to sealed results."""
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from common import EP, OUT, PRIVATE, save_json, sha
from evaluate_ranking import predictions

def main():
 dest=OUT/'diagnostics/ic_20261116';dest.mkdir(parents=True,exist_ok=True)
 labels=pd.read_parquet(PRIVATE/'labels.parquet',columns=['signal_date','instrument','h10'])
 rows=[];summaries=[];consumers={}
 for scheme in ['expanding','rolling36']:
  p,consumers[scheme]=predictions(scheme)
  p=p.loc[p.model_id.isin(['E1','E2','E3']) & p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])]
  f=p.merge(labels,on=['signal_date','instrument'],validate='many_to_one')
  for (model,date),g in f.groupby(['model_id','signal_date']):
   g=g.dropna(subset=['score','h10'])
   if len(g)<100 or g.score.nunique()<2 or g.h10.nunique()<2:continue
   rows.append(dict(scheme=scheme,model=model,signal_date=date,n=len(g),pearson_ic=pearsonr(g.score,g.h10).statistic,rank_ic=spearmanr(g.score,g.h10).statistic))
  detail=pd.DataFrame(rows);detail=detail.loc[detail.scheme.eq(scheme)]
  old=pd.read_csv(OUT/'path_a'/f'{scheme}_ranking_summary.csv');old=old.loc[old.horizon.eq('h10')&old.seed.isin(['fixed','equal_seed_ensemble'])].set_index('model')
  weekly=pd.read_csv(OUT/'path_a'/f'{scheme}_ranking_weekly.csv')
  for model,g in detail.groupby('model'):
   assert abs(g.rank_ic.mean()-old.loc[model,'mean_rank_ic'])<1e-12
   w=weekly.loc[weekly.model.eq(model)&weekly.horizon.eq('h10')&weekly.seed.isin(['fixed','equal_seed_ensemble'])]
   summaries.append(dict(scheme=scheme,model=model,evaluable_weeks=len(g),mean_pearson_ic=g.pearson_ic.mean(),mean_rank_ic=g.rank_ic.mean(),mean_h10_q5_minus_q1=old.loc[model,'mean_q5_q1'],spread_evaluable_weeks=int(w.q5_q1.notna().sum()),certified_net_annual_alpha=None,alpha_status='UNAVAILABLE_INCOMPLETE_ACCOUNT_AND_BENCHMARK'))
 pd.DataFrame(rows).to_csv(dest/'weekly_ic.csv',index=False)
 result=pd.DataFrame(summaries);result.to_csv(dest/'summary.csv',index=False)
 save_json(dest/'manifest.json',dict(post_delivery_diagnostic=True,retraining=False,horizon='H10 fixed market-calendar open endpoints',aggregation='equal-weight mean across weekly cross-sectional correlations',alpha='Q5-Q1 is gross grouping diagnostic, not risk-adjusted alpha or net annual benchmark excess',prediction_consumption=consumers,labels_sha256=sha(PRIVATE/'labels.parquet'),script_sha256=sha(EP/'src/diagnose_ic.py'),summary_sha256=sha(dest/'summary.csv'),weekly_sha256=sha(dest/'weekly_ic.csv')))
 print(result.to_string(index=False))
if __name__=='__main__':main()

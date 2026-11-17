"""Post-result measurement audit, no changed strategies or primary results."""
from e1_past_style_copy import *
def main():
 verify();verify('selection_complete');verify('analysis_complete')
 data=pd.read_parquet(L/'labeled_scores.parquet');targets=pd.read_parquet(L/'targets.parquet');old=pd.read_parquet(PRIVATE/'e1_style_channels_20261117/targets.parquet');checks=[];rows=[];monthly=[];drift=[]
 for date,g in targets.groupby('signal_date'):
  for st,reference in [('COPY','COPY'),('I','I')]:
   a=g[g.strategy==st].set_index('instrument').weight.sort_index();b=old[(old.signal_date==date)&(old.strategy==reference)].set_index('instrument').weight.sort_index();ok=a.index.equals(b.index) and np.allclose(a,b);assert ok;checks.append(dict(check=str(date)+st+' identical old target',passed=True))
 # Industry Spearman first, then stock-count-weighted average at each signal.
 for date,g in data.groupby('signal_date'):
  for st in ['Q','LOCK','COPY','I']:
   score_corr=[];ret_corr=[];ns=[];nr=[]
   for industry,a in g.groupby('industry'):
    rho=rankcorr(a[st],a.I)
    if np.isfinite(rho):score_corr.append(rho);ns.append(len(a))
    known=a[a.h10.notna()&(a.h10_mature<=END)]
    if len(known)>=3:
     rho=rankcorr(known[st],known.h10)
     if np.isfinite(rho):ret_corr.append(rho);nr.append(len(known))
   rows.append(dict(signal_date=date,strategy=st,industry_score_correlation=np.average(score_corr,weights=ns) if ns else np.nan,industry_H10_IC=np.average(ret_corr,weights=nr) if nr else np.nan,known_stocks=sum(nr)))
  x=features_only(g[STYLES+['industry']]);t=g.rename(columns={'I':'E1'});y=teacher_target(t);oracle=np.linalg.lstsq(x,y,rcond=1e-12)[0]
  for j,col in enumerate(STYLES):drift.append(dict(signal_date=date,style=col,same_date_teacher_coefficient=float(oracle[j])))
 write(pd.DataFrame(rows),'within_industry_audit.csv');write(pd.DataFrame(drift),'same_date_coefficient_diagnostic.csv')
 frame=pd.DataFrame(rows);stats=[]
 for st,g in frame.groupby('strategy'):
  for metric in ['industry_score_correlation','industry_H10_IC']:stats.append(dict(strategy=st,metric=metric,**bootstrap(g.set_index('signal_date')[metric],'W-FRI',13)))
 write(pd.DataFrame(stats),'within_industry_statistics.csv')
 save_json(D/'measurement_audit.json',dict(status='PASS',checks=checks,count=len(checks),timing='post-result diagnostic, no selection or headline-statistic change',same_day_copy_identity='same within-industry target as prior COPY; raw score offsets differ due to industry demeaning',files=record([D/'within_industry_audit.csv',D/'within_industry_statistics.csv',D/'same_date_coefficient_diagnostic.csv',Path(__file__)])))
 print(pd.DataFrame(stats).to_string(index=False))
if __name__=='__main__':main()

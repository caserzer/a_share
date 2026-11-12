import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,ID,calendar_dates,block_ci
OUT=EP/'restart/p07';OUT.mkdir(exist_ok=True)
source=EP/'outputs/r11/coverage30/evaluation_panel.parquet';predfile=EP/'restart/p05/predictions.parquet'
seal=json.loads((EP/'restart/p05/prediction_seal.json').read_text());assert sha(predfile)==seal['artifacts']['predictions.parquet']
l=pd.read_parquet(source);l=l[l.price_eligible];q=pd.read_parquet(predfile);q=q[q.model.eq('B')]
rows=[]
for date,g in q.groupby('date'):
 hist=l[l.win126.notna()&l.end126.lt(date)];bydate=hist.groupby('date').win126.mean().sort_index();recent=bydate.tail(26)
 rows.append(dict(date=date,raw_mean=g.raw_score.mean(),history_expanding=bydate.mean() if len(bydate)>=26 else np.nan,history_recent26=recent.mean() if len(recent)==26 else np.nan,history_dates=len(bydate),history_rows=len(hist),recent_dates=len(recent),latest_history_date=hist.date.max(),latest_label_end=hist.end126.max()))
d=pd.DataFrame(rows);d.to_csv(OUT/'sealed_date_predictions.csv',index=False)
inputs=[source,predfile,EP/'restart/p05/prediction_seal.json',Path(__file__),EP/'restart/P07_date_level_plan.md']
(OUT/'prediction_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in inputs},predictions_sha256=sha(OUT/'sealed_date_predictions.csv')),indent=2)+'\n')
e=q.merge(l[ID+['win126']],on=ID,validate='one_to_one');truth=e.groupby('date').win126.mean();known=e[e.win126.notna()];knownmean=known.groupby('date').raw_score.mean()
d['actual']=d.date.map(truth);d['known_subset_score_mean']=d.date.map(knownmean);d['known_fraction']=d.date.map(e.groupby('date').win126.count()/e.groupby('date').size())
dates=calendar_dates();dates=dates[dates>=d.date.min()];metrics=[];annual=[];comparisons=[]
for name in ['raw_mean','history_expanding','history_recent26']:
 x=d.dropna(subset=['actual',name]);err=x[name]-x.actual
 metrics.append(dict(method=name,dates=len(x),mse=np.mean(err**2),mae=err.abs().mean(),bias=err.mean(),correlation=x[name].corr(x.actual)))
 for year,g in x.groupby(x.date.dt.year):annual.append(dict(method=name,year=int(year),dates=len(g),prediction=g[name].mean(),actual=g.actual.mean(),mse=((g[name]-g.actual)**2).mean()))
 if name!='raw_mean':
  improve=((x.raw_mean-x.actual)**2-(x[name]-x.actual)**2);v=pd.Series(improve.to_numpy(),index=x.date).reindex(dates);lo,hi=block_ci(v,26);comparisons.append(dict(method=name,raw_mse_minus_method_mse=v.mean(),lo=lo,hi=hi))
# Exact decomposition on known observations; no future-rate-adjusted score or admission.
decomp=[]
for date,g in known.groupby('date'):
 a=g.raw_score.to_numpy();y=g.win126.to_numpy();between=(a.mean()-y.mean())**2;within=np.mean(((a-a.mean())-(y-y.mean()))**2);total=np.mean((a-y)**2);assert np.isclose(total,between+within)
 decomp.append(dict(date=date,total=total,date_mean_error=between,centered_error=within,known_vs_all_score_mean=a.mean()-float(d.loc[d.date.eq(date),'raw_mean'].iloc[0])))
b=pd.DataFrame(decomp);b.to_csv(OUT/'brier_decomposition.csv',index=False)
entryfile=EP/'restart/p06/evaluated.parquet';event=pd.read_parquet(entryfile);event['date_score_mean']=event.date.map(d.set_index('date').raw_mean);event['centered_score']=event.raw_score-event.date_score_mean;event['actual_date_base']=event.date.map(truth)
evrows=[]
for policy in ['top20','raw_gate']:
 z=event[event[policy+'_edge']&event.win126.notna()]
 for year,g in z.groupby(z.date.dt.year):evrows.append(dict(policy=policy,year=int(year),events=len(g),score=g.raw_score.mean(),date_score=g.date_score_mean.mean(),centered_score=g.centered_score.mean(),actual_base=g.actual_date_base.mean(),win_rate=g.win126.mean()))
pd.DataFrame(evrows).to_csv(OUT/'event_components.csv',index=False);d.to_csv(OUT/'date_evaluation.csv',index=False);pd.DataFrame(metrics).to_csv(OUT/'metrics.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False);pd.DataFrame(comparisons).to_csv(OUT/'comparisons.csv',index=False)
print(pd.DataFrame(metrics).to_string(index=False));print(pd.DataFrame(comparisons).to_string(index=False));print(pd.DataFrame(annual).to_string(index=False));print('Brier components',b[['total','date_mean_error','centered_error']].mean().to_dict())

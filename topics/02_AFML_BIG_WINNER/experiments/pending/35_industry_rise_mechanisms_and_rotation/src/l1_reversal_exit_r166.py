"""Fixed L1 raw reversal exit evaluation; no model or threshold selection."""
import pandas as pd
from common import *
from followup_r10 import path_metrics,exit_economics

def run():
 out=ROOT/'outputs/r166'
 pp=ROOT/'outputs/r16/raw_predictions.parquet';dp=ROOT/'data/l1_daily.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet'
 p=pd.read_parquet(pp);p=p[p.cohort.eq('F')&p.method.eq('F')&p.task.eq('reversal')].copy()
 assert len(p)==91 and set(p.horizon)=={60} and set(p.year)=={2026} and not p.calibration_eligible.any()
 d=pd.read_parquet(dp);market=pd.read_parquet(bp).close
 paths=pd.concat([path_metrics(g,market) for _,g in d.groupby(KEY+['block'])],ignore_index=True)
 p=p.merge(paths,on=KEY+['date'],how='left',validate='one_to_one')
 assert np.allclose(p.excess,p.excess60,equal_nan=True)
 p['alert']=False
 for _,g in p.groupby('date'):
  idx=g.sort_values(['raw_score','industry_code'],ascending=[False,True]).head(int(np.ceil(len(g)*.2))).index;p.loc[idx,'alert']=True
 p.to_parquet(out/'followup.parquet',index=False)
 rows=[];dates=[]
 for cohort,v in [('all_trending',p),('risk_alert',p[p.alert]),('not_alert',p[~p.alert])]:
  for cost in [0,.002,.005]:
   for date,z in v.groupby('date'):
    q=z.dropna(subset=['return60','market60']);cash,switch=exit_economics(q.return60,q.market60,cost)
    dates.append(dict(cohort=cohort,date=date,cost=cost,origins=len(z),complete=len(q),unknown=len(z)-len(q),cash_improvement=cash.mean(),market_improvement=switch.mean(),wrong_exit_absolute=q.return60.gt(0).mean(),wrong_exit_relative=q.excess60.gt(0).mean(),risk_precision=q.y.mean(),mean_drawdown=q.drawdown60.mean(),missed_positive=q.return60.clip(lower=0).mean(),avoided_negative=(-q.return60.clip(upper=0)).mean()))
   q=v.dropna(subset=['return60','market60']);cash,switch=exit_economics(q.return60,q.market60,cost)
   rows.append(dict(cohort=cohort,cost=cost,origins=len(v),complete=len(q),unknown=len(v)-len(q),cash_improvement=cash.mean(),market_improvement=switch.mean(),wrong_exit_absolute=q.return60.gt(0).mean(),risk_precision=q.y.mean()))
 dates=pd.DataFrame(dates);dates.to_csv(out/'date_metrics.csv',index=False);pd.DataFrame(rows).to_csv(out/'row_summary.csv',index=False)
 metrics=['cash_improvement','market_improvement','wrong_exit_absolute','wrong_exit_relative','risk_precision','mean_drawdown','missed_positive','avoided_negative']
 summary=dates.groupby(['cohort','cost'])[metrics].mean();summary['months']=dates.groupby(['cohort','cost']).cash_improvement.count();summary.to_csv(out/'date_summary.csv')
 js(out/'receipt.json',dict(status='PASS',reads={str(x):sha(x) for x in [pp,dp,bp,ROOT/'outputs/r16/raw_parameters.json',ROOT/'protocols/r166.json',ROOT/'protocols/r10.json',ROOT/'src/followup_r10.py',Path(__file__)]},calibrated=False,adoption=False,origins=len(p),alerts=int(p.alert.sum())))
 print(summary.to_string())
if __name__=='__main__':run()

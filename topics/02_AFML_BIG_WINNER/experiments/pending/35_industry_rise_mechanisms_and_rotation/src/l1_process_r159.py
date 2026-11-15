"""Frozen uncalibrated L1 raw-score process replay, never a probability adoption."""
import shutil
import pandas as pd
import process_replay_r09,verify_process
from common import *

def run():
 out=ROOT/'outputs/r159';root=out/'evaluation';cache=root/'cache';out.mkdir(parents=True,exist_ok=True)
 sources={'cache/forecast_v5/daily_industries.parquet':ROOT/'data/l1_daily.parquet','cache/forecast_v5/CSI_ALL.parquet':CACHE/'forecast_v5/CSI_ALL.parquet','protocols/r09.json':ROOT/'protocols/r09.json','src/build_panel.py':ROOT/'src/build_panel.py','src/train_r02.py':ROOT/'src/train_r02.py'}
 for rel,p in sources.items():
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 mp=ROOT/'outputs/r16/raw_parameters.json';pp=ROOT/'outputs/r16/raw_predictions.parquet';models=json.loads(mp.read_text());models=[x for x in models if x['cohort']=='F' and x['method']=='F' and x['task']=='onset' and x['horizon']==20];assert len(models)==2 and {x['year'] for x in models}=={2025,2026}
 adapted=[dict(m,era='SW2021',level='L1',coefficient=m['coef'],calibration_coefficient=[[1.]],calibration_intercept=[0.],score_type='uncalibrated_logit',identity_link_not_fitted_calibration=True) for m in models];(root/'outputs/r02').mkdir(parents=True,exist_ok=True);js(root/'outputs/r02/model_parameters.json',adapted)
 p=pd.read_parquet(pp);p=p[p.cohort.eq('F')&p.method.eq('F')&p.task.eq('onset')&p.horizon.eq(20)].rename(columns={'raw_score':'prediction'});p.to_parquet(root/'outputs/r02/predictions.parquet',index=False)
 (root/'data').mkdir(exist_ok=True);(root/'outputs/r09').mkdir(exist_ok=True)
 for mod in [process_replay_r09,verify_process]:mod.ROOT=root;mod.CACHE=cache;mod.run()
 alerts=pd.read_parquet(root/'outputs/r09/alerts.parquet');hits=pd.read_csv(root/'outputs/r09/event_hits.csv',parse_dates=['date']);rows=[]
 for (strategy,year),g in alerts.groupby(['strategy',alerts.date.dt.year]):
  h=hits[hits.strategy.eq(strategy)&hits.date.dt.year.eq(year)];v=h[h.evaluable];known=g[g.y.notna()];rows.append(dict(strategy=strategy,year=int(year),alerts=len(g),mature=len(known),unknown=int(g.y.isna().sum()),precision=known.y.mean(),events=len(v),left_censored=int((~h.evaluable).sum()),hit_events=int(v.hit.sum()),recall=v.hit.mean(),median_lead=v.loc[v.hit,'lead_sessions'].median(),score_type='uncalibrated_logit'))
 pd.DataFrame(rows).to_csv(out/'annual_process.csv',index=False)
 js(out/'receipt.json',dict(status='PASS',models=len(models),monthly_raw_score_rows=len(p),reads={str(p):sha(p) for p in list(sources.values())+[mp,pp,ROOT/'protocols/r159.json',Path(__file__),ROOT/'src/process_replay_r09.py',ROOT/'src/verify_process.py']},calibrated=False,identity_link_not_fitted=True,scope='L1 raw-score historical price-event replay; no predictive adoption'))
 print(pd.DataFrame(rows).to_string(index=False))
if __name__=='__main__':run()

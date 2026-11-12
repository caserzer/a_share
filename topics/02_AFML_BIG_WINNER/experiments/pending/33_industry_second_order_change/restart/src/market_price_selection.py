import json,sys
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha,calendar_dates
from probability_pool import block_interval
OUT=EP/'restart/p08';OUT.mkdir(exist_ok=True)
source=EP/'restart/p06/selected_features.parquet';s=json.loads((EP/'restart/p06/selection_seal.json').read_text());assert sha(source)==s['features_sha256']
p=pd.read_parquet(source);market=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet');close=pd.read_parquet(market).close.sort_index();p['market126']=p.date.map(close/close.shift(126)-1)
cont=p.week_i.sub(p.groupby(KEY).week_i.shift()).eq(1)
for name,condition in [('UP',p.market126.gt(0)),('NONUP',p.market126.le(0))]:
 p[name]=p.top20&condition;p[name+'_original_edge']=p.top20_edge&condition
 p[name+'_edge']=p[name]&p.groupby(KEY)[name].shift().eq(False)&cont
 p[name+'_boundary']=p[name]&~cont
 p[name+'_market_trigger']=p[name+'_edge']&p.groupby(KEY).top20.shift().eq(True)
 p[name+'_cooldown']=False
 for _,g in p[p[name+'_edge']].groupby(KEY):
  last=-100000
  for i,r in g.iterrows():
   if r.day_i-last>=126:p.loc[i,name+'_cooldown']=True;last=r.day_i
p.to_parquet(OUT/'selected_features.parquet',index=False)
(OUT/'selection_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [source,market,Path(__file__),EP/'restart/P08_market_price_plan.md',EP/'configs/pool_metric_v1.json']},features_sha256=sha(OUT/'selected_features.parquet')),indent=2)+'\n')
labels=EP/'outputs/r09/evaluation_panel.parquet';l=pd.read_parquet(labels);p=p.merge(l[ID+[f'{c}{h}' for h in [63,126,252] for c in ['win','status']]],on=ID,validate='one_to_one')
dates=calendar_dates();dates=dates[dates>=p.date.min()];rows=[];annual=[]
for m in ['UP','NONUP']:
 for unit in ['original_edge','edge','cooldown']:
  z=p[p[m+'_'+unit]]
  for h in [63,126,252]:
   col=f'win{h}';k=z[z[col].notna()].copy();base=p.groupby('date')[col].mean();k['delta']=k[col]-k.date.map(base);lo,hi=block_interval(k,dates,26 if h==126 else round(h/5))
   rows.append(dict(market=m,unit=unit,horizon=h,total=len(z),known=len(k),unknown=len(z)-len(k),win_rate=k[col].mean(),uplift=k.delta.mean(),lo=lo,hi=hi,state_success_week_coverage=p.loc[p[m],col].sum()/p[col].sum(),market_trigger_fraction=z[m+'_market_trigger'].mean(),median_age_days=z.state_age.median()*90,median_drawup=z.state_drawup.median(),empty_week_fraction=1-p.loc[p[m],'date'].nunique()/len(dates),mean_events_per_week=len(z)/len(dates),mean_raw_score=k.raw_score.mean()))
   for year,g in k.groupby(k.date.dt.year):annual.append(dict(market=m,unit=unit,horizon=h,year=int(year),known=len(g),win_rate=g[col].mean(),uplift=g.delta.mean()))
p.to_parquet(OUT/'evaluated.parquet',index=False);pd.DataFrame(rows).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False)
print(pd.DataFrame(rows).query('horizon==126').to_string(index=False));print(pd.DataFrame(annual).query('horizon==126 and unit=="edge"').to_string(index=False))

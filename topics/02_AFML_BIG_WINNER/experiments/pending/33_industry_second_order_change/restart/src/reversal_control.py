import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha,calendar_dates,block_ci
from probability_pool import block_interval
OUT=EP/'restart/p09';OUT.mkdir(exist_ok=True)
source=EP/'restart/p08/selected_features.parquet';seal=json.loads((EP/'restart/p08/selection_seal.json').read_text());assert sha(source)==seal['features_sha256']
p=pd.read_parquet(source).sort_values(KEY+['date']).reset_index(drop=True);assert p.rate60.notna().all()
cont=p.week_i.sub(p.groupby(KEY).week_i.shift()).eq(1);names=[];composition=[]
for regime in ['UP','NONUP']:
 k=p.groupby('date')[regime].transform('sum')
 for policy,score,ascending in [('price_tree','raw_score',False),('reversal60','rate60',True),('momentum60','rate60',False)]:
  name=regime+'_'+policy;names.append(name);a=p.sort_values(['date',score,'era','industry_code'],ascending=[True,ascending,True,True]);p[name]=False;p.loc[a.index,name]=a.groupby('date').cumcount().lt(k.loc[a.index]);assert p.groupby('date')[name].sum().equals(p.groupby('date')[regime].sum())
  p[name+'_edge']=p[name]&p.groupby(KEY)[name].shift().eq(False)&cont;p[name+'_cooldown']=False
  for _,g in p[p[name+'_edge']].groupby(KEY):
   last=-100000
   for i,r in g.iterrows():
    if r.day_i-last>=126:p.loc[i,name+'_cooldown']=True;last=r.day_i
  z=p[p[name]];composition.append(dict(regime=regime,policy=policy,selected=len(z),median_rate60=z.rate60.median(),tree_overlap_fraction=(z[regime]).mean(),median_age_days=z.state_age.median()*90,median_drawup=z.state_drawup.median()))
p.to_parquet(OUT/'selected_features.parquet',index=False);pd.DataFrame(composition).to_csv(OUT/'composition.csv',index=False)
(OUT/'selection_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [source,Path(__file__),EP/'restart/P09_reversal_control_plan.md']},features_sha256=sha(OUT/'selected_features.parquet')),indent=2)+'\n')
l=pd.read_parquet(EP/'outputs/r09/evaluation_panel.parquet');p=p.merge(l[ID+[f'win{h}' for h in [63,126,252]]],on=ID,validate='one_to_one');dates=calendar_dates();dates=dates[dates>=p.date.min()];rows=[];annual=[];daily=[];pairs=[]
for name in names:
 for unit,flag in [('state',name),('edge',name+'_edge'),('cooldown',name+'_cooldown')]:
  z=p[p[flag]]
  for h in [63,126,252]:
   col=f'win{h}';known=z[z[col].notna()].copy();base=p.groupby('date')[col].mean();known['delta']=known[col]-known.date.map(base);lo,hi=block_interval(known,dates,26 if h==126 else round(h/5));rate=z.groupby('date')[col].mean()
   rows.append(dict(method=name,unit=unit,horizon=h,total=len(z),known=len(known),win_rate=known[col].mean(),date_win_rate=rate.mean(),uplift=known.delta.mean(),lo=lo,hi=hi,state_success_week_coverage=z[col].sum()/p[col].sum() if unit=='state' else np.nan))
   for year,g in known.groupby(known.date.dt.year):annual.append(dict(method=name,unit=unit,horizon=h,year=int(year),known=len(g),win_rate=g[col].mean(),uplift=g.delta.mean()))
   if unit=='state':
    for date,v in rate.items():daily.append(dict(method=name,horizon=h,date=date,win_rate=v))
for regime in ['UP','NONUP']:
 for h in [63,126,252]:
  col=f'win{h}';a=p[p[regime+'_price_tree']].groupby('date')[col].mean();events=p[p[regime+'_price_tree_edge']];count=events.groupby('date').size()
  for policy,ascending in [('reversal60',True),('momentum60',False)]:
   b=p[p[regime+'_'+policy]].groupby('date')[col].mean();v=(a-b).reindex(dates);lo,hi=block_ci(v,26 if h==126 else round(h/5));pairs.append(dict(regime=regime,control=policy,unit='state_date_equal',horizon=h,delta=v.mean(),lo=lo,hi=hi,dates=v.notna().sum()))
   ranked=p.sort_values(['date','rate60','industry_code'],ascending=[True,ascending,True]);control=ranked[ranked.groupby('date').cumcount().lt(ranked.date.map(count).fillna(0))];ref=control.groupby('date')[col].mean();k=events[events[col].notna()].copy();k['delta']=k[col]-k.date.map(ref);lo,hi=block_interval(k,dates,26 if h==126 else round(h/5));pairs.append(dict(regime=regime,control=policy,unit='tree_edge_matched_capacity',horizon=h,delta=k.delta.mean(),lo=lo,hi=hi,dates=k.date.nunique()))
p.to_parquet(OUT/'evaluated.parquet',index=False);pd.DataFrame(rows).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False);pd.DataFrame(pairs).to_csv(OUT/'paired_comparisons.csv',index=False)
print(pd.DataFrame(rows).query('horizon==126 and unit!="state"').to_string(index=False));print(pd.DataFrame(pairs).query('horizon==126').to_string(index=False))

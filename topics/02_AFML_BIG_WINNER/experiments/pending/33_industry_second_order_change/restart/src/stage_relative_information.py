import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha,calendar_dates,block_ci
from probability_pool import block_interval
OUT=EP/'restart/p03';OUT.mkdir(exist_ok=True)
receipt=EP.parent/'32_industry_rotation_cycle_observation/extensions/v7_online_stage/outputs/state_receipt.json'
r=json.loads(receipt.read_text());assert sha(r['path'])==r['sha256']
s=pd.read_parquet(r['path']);s=s[s.level.eq('L3')&s.threshold.eq(.15)]
cols=['candidate_low_date','state_direction','state_age','state_drawup','state_eligible','state_market_CSI_ALL']
# Frequency-specific row IDs must not create duplicate observations.
assert s.groupby(ID)[cols].nunique(dropna=False).le(1).all().all()
s=s[ID+cols].drop_duplicates(ID)
pfile=EP/'restart/p01/feature_panel.parquet';p=pd.read_parquet(pfile).reset_index(drop=True);p=p[p.eligible].copy()
p=p.drop(columns=[c for c in p if c.startswith(('h1_','h2_'))]);p=p.merge(s,on=ID,how='left',validate='one_to_one')
p['early']=p.state_eligible.eq(1);p['relative_up']=p.state_drawup.sub(p.state_market_CSI_ALL).gt(0)
assert p.loc[p.early,'state_direction'].isin([-1,1]).all()
methods=[]
for direction,label in [(-1,'unconfirmed'),(1,'confirmed')]:
 for relative,name in [(False,'lag'),(True,'lead')]:
  m=label+'_'+name;methods.append(m);p[m]=p.early&p.state_direction.eq(direction)&p.relative_up.eq(relative)
assert p[methods].sum(axis=1).eq(p.early.astype(int)).all()
market=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet');close=pd.read_parquet(market).close.sort_index();cal=pd.DatetimeIndex(close.index)
p['market_up']=p.date.map(close/close.shift(126)-1).gt(0)
p=p.sort_values(KEY+['date']).reset_index(drop=True)
for m in methods:
 p['entry_'+m]=False
 for _,g in p[p[m]].groupby(KEY):
  release=pd.Timestamp.min
  for i,row in g.iterrows():
   if row.date<release:continue
   p.loc[i,'entry_'+m]=True;j=cal.searchsorted(row.date,side='right')+126;release=cal[j] if j<len(cal) else pd.Timestamp.max
p.groupby(p.date.dt.year).agg(rows=('date','size'),state_known=('state_eligible','count'),early=('early','sum'),**{m:(m,'sum') for m in methods}).to_csv(OUT/'feasibility.csv')
p.to_parquet(OUT/'selected_features.parquet',index=False)
(OUT/'selection_seal.json').write_text(json.dumps({'inputs':{str(f):sha(f) for f in [Path(r['path']),receipt,pfile,market,Path(__file__),EP/'restart/P03_stage_relative_plan.md']},'features_sha256':sha(OUT/'selected_features.parquet')},indent=2)+'\n')
l=pd.read_parquet(EP/'outputs/r09/evaluation_panel.parquet');p=p.merge(l[ID+[f'{x}{h}' for h in [63,126,252] for x in ['win','status']]],on=ID,how='left',validate='one_to_one')
dates=calendar_dates();rows=[];annual=[];pairs=[]
for m in methods:
 for unit,mask in [('state',p[m]),('entry',p['entry_'+m])]:
  z=p[mask]
  for h in [63,126,252]:
   col=f'win{h}';k=z[z[col].notna()].copy();base=p.groupby('date')[col].mean();early=p[p.early].groupby('date')[col].mean();k['delta']=k[col]-k.date.map(base);lo,hi=block_interval(k,dates,26 if h==126 else round(h/5))
   rows.append(dict(method=m,unit=unit,horizon=h,total=len(z),known=len(k),win_rate=k[col].mean(),uplift=k.delta.mean(),lo=lo,hi=hi,early_delta=(k[col]-k.date.map(early)).mean(),state_success_week_coverage=z[col].sum()/p[col].sum() if unit=='state' else np.nan,median_age_days=z.state_age.median()*90,median_drawup=z.state_drawup.median(),median_prior63=np.expm1(z.abs63).median()))
   for (year,up),g in k.groupby([k.date.dt.year,'market_up']):annual.append(dict(method=m,unit=unit,horizon=h,year=int(year),market_up=bool(up),known=len(g),win_rate=g[col].mean(),uplift=g.delta.mean()))
comparisons=[('relative_unconfirmed','unconfirmed_lead','unconfirmed_lag'),('relative_confirmed','confirmed_lead','confirmed_lag'),('confirmation_lead','confirmed_lead','unconfirmed_lead'),('confirmation_lag','confirmed_lag','unconfirmed_lag')]
for name,left,right in comparisons:
 for h in [63,126,252]:
  col=f'win{h}';a=p[p[left]].groupby('date')[col].agg(['size','count','mean']);b=p[p[right]].groupby('date')[col].agg(['size','count','mean']);v=a.join(b,lsuffix='_l',rsuffix='_r',how='inner');v=v[v.size_l.ge(5)&v.size_r.ge(5)];delta=(v.mean_l-v.mean_r).reindex(dates);lo,hi=block_ci(delta,26 if h==126 else round(h/5))
  pairs.append(dict(comparison=name,horizon=h,paired_dates=delta.notna().sum(),delta=delta.mean(),lo=lo,hi=hi));delta.rename('delta').to_csv(OUT/f'{name}_{h}.csv')
pd.DataFrame(rows).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual_market.csv',index=False);pd.DataFrame(pairs).to_csv(OUT/'paired_summary.csv',index=False);p.to_parquet(OUT/'evaluated_panel.parquet',index=False)
print(pd.DataFrame(rows).query('horizon==126 and unit=="entry"').to_string(index=False));print(pd.DataFrame(pairs).query('horizon==126').to_string(index=False))

import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha,calendar_dates,block_ci
OUT=EP/'restart/p17';OUT.mkdir(exist_ok=True)
assert not (OUT/'selection_seal.json').exists(),'sealed'
pfile=EP/'outputs/r11/coverage30/evaluation_panel.parquet'
sfile=EP/'restart/p11/selected_features.parquet'
f=pd.read_parquet(pfile);f=f[f.price_eligible]
q=pd.read_parquet(sfile)
q=q.merge(f[ID+['rate60']],on=ID,validate='one_to_one')
cache=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5')
mfile=cache/'CSI_ALL.parquet';rawfile=cache/'daily_industries.parquet'
m=pd.read_parquet(mfile).close.sort_index();cal=pd.DatetimeIndex(m.index)
q['market21']=q.date.map(m/m.shift(21)-1)
assert np.allclose(q.market126,q.date.map(m/m.shift(126)-1),equal_nan=True)
q['regime']=pd.Series(np.where(q.market126.gt(0),'UP','NONUP'),index=q.index)+'_'+pd.Series(np.where(q.market21.gt(0),'RISING','FALLING'),index=q.index)
for name,asc in [('momentum',False),('reversal',True)]:
 a=q.sort_values(['date','rate60','era','industry_code'],ascending=[True,asc,True,True]);q[name]=False
 q.loc[a.index,name]=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2))
q.to_parquet(OUT/'selected_features.parquet',index=False)
inputs=[pfile,sfile,mfile,rawfile,Path(__file__),EP/'restart/P17_regime_diagnostic_plan.md']
(OUT/'selection_seal.json').write_text(json.dumps({'inputs':{str(x):sha(x) for x in inputs},'selection':sha(OUT/'selected_features.parquet')},indent=2)+'\n')
d=pd.read_parquet(rawfile);d=d[d.level.eq('L3')];parts=[]
for _,g in d.groupby(KEY,sort=True):
 g=g.sort_values('date').copy();assert np.all(np.diff(cal.get_indexer(g.date))==1)
 b=g.date.map(m)
 for h in [63,126,252]:
  r=g.nav.shift(-h-1)/g.nav.shift(-1)-1;mr=b.shift(-h-1)/b.shift(-1)-1
  end=g.date.shift(-h-1);known=end.notna()
  g[f'end{h}']=end;g[f'return{h}']=r;g[f'market_return{h}']=mr
  g[f'absolute{h}']=r.gt(0).astype(float).where(known)
  g[f'relative{h}']=r.gt(mr).astype(float).where(known)
  g[f'joint{h}']=(r.gt(0)&r.gt(mr)).astype(float).where(known)
 parts.append(g[ID+[c for h in [63,126,252] for c in [f'end{h}',f'return{h}',f'market_return{h}',f'absolute{h}',f'relative{h}',f'joint{h}']]])
z=pd.concat(parts,ignore_index=True);q=q.merge(z,on=ID,validate='one_to_one')
a=q.merge(f[ID+['win126','end126']],on=ID,suffixes=('','_old'),validate='one_to_one')
assert np.allclose(a.joint126,a.win126,equal_nan=True)
assert (a.end126.eq(a.end126_old)|(a.end126.isna()&a.end126_old.isna())).all()
for name in ['momentum','reversal']:
 assert q.groupby('date')[name].sum().equals(q.groupby('date').top20.sum())
q.to_parquet(OUT/'evaluated.parquet',index=False)
rows=[]
for date,g in q.groupby('date'):
 for name,sel in [('all',pd.Series(True,index=g.index)),('tree',g.top20),('momentum',g.momentum),('reversal',g.reversal)]:
  b=g[sel]
  for h in [63,126,252]:
   k=b[b[f'joint{h}'].notna()]
   rows.append(dict(date=date,year=date.year,regime=g.regime.iloc[0],method=name,horizon=h,rows=len(b),known=len(k),absolute=k[f'absolute{h}'].mean(),relative=k[f'relative{h}'].mean(),joint=k[f'joint{h}'].mean(),fail_absolute=1-k[f'absolute{h}'].mean(),fail_relative_after_positive=(k[f'absolute{h}']-k[f'joint{h}']).mean(),future_market=k[f'market_return{h}'].mean()))
r=pd.DataFrame(rows);r.to_csv(OUT/'daily.csv',index=False)
cols=['absolute','relative','joint','fail_absolute','fail_relative_after_positive','future_market']
annual=r.groupby(['year','regime','method','horizon']).agg(dates=('date','size'),mature_dates=('joint','count'),known=('known','sum'),**{c:(c,'mean') for c in cols});annual.to_csv(OUT/'annual.csv')
r.assign(broad=r.regime.str.split('_').str[0]).groupby(['year','broad','method','horizon'])[cols].mean().to_csv(OUT/'annual_broad.csv')
dates=calendar_dates();dates=dates[dates>=q.date.min()];comp=[]
for (regime,h),g in r.groupby(['regime','horizon']):
 p=g.pivot(index='date',columns='method',values='joint')
 for method in ['tree','momentum','reversal']:
  v=(p[method]-p['all']).reindex(dates);lo,hi=block_ci(v,26)
  comp.append(dict(regime=regime,horizon=h,method=method,mature_dates=int(v.notna().sum()),uplift=v.mean(),lo=lo,hi=hi,win=p[method].mean(),base=p['all'].mean()))
pd.DataFrame(comp).to_csv(OUT/'comparisons.csv',index=False)
# Independent point checks use positional raw prices rather than shifted labels.
for _,row in q.sample(60,random_state=3317).iterrows():
 g=d[(d.era==row.era)&(d.industry_code==row.industry_code)&(d.block==row.block)].sort_values('date').reset_index(drop=True)
 i=int(g.index[g.date.eq(row.date)][0]);j=int(cal.get_loc(row.date))
 assert np.isclose(row.market21,m.iloc[j]/m.iloc[j-21]-1)
 for h in [63,126,252]:
  if i+h+1>=len(g):assert pd.isna(row[f'joint{h}']);continue
  er=g.nav.iloc[i+h+1]/g.nav.iloc[i+1]-1;br=m.loc[g.date.iloc[i+h+1]]/m.loc[g.date.iloc[i+1]]-1
  assert np.isclose(row[f'return{h}'],er) and row[f'joint{h}']==float(er>0 and er>br)
k=r.dropna(subset=['joint']);assert np.allclose(k.joint+k.fail_absolute+k.fail_relative_after_positive,1)
seal=json.loads((OUT/'selection_seal.json').read_text());assert sha(OUT/'selected_features.parquet')==seal['selection']
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',aligned126_rows=len(a),raw_path_checks=60,horizons=3,capacity_equal=True,failure_partition=True,selection_seal=True),indent=2)+'\n')
print(annual.reset_index().query('horizon==126 and method=="tree"').to_string(index=False))
print(pd.DataFrame(comp).query('horizon==126 and method=="tree"').to_string(index=False))

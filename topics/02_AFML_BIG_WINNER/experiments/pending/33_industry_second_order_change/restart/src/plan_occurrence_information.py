import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,sha,calendar_dates,block_ci
OUT=EP/'restart/p16';OUT.mkdir(exist_ok=True)
efile=EP/'restart/p15/occurrence_ledger.parquet';receipt=json.loads((EP/'restart/p15/receipt.json').read_text());assert sha(efile)==receipt['occurrence_sha256']
e=pd.read_parquet(efile);e=e[e.kind.eq('distribution_plan')];mfile=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet');cal=pd.DatetimeIndex(pd.read_parquet(mfile).index)
first=e[e.known_date.notna()].groupby('instrument').known_date.min();left=e[e.calendar_status.eq('LEFT_CENSORED')].instrument.unique();first=first.reindex(first.index.union(left));first.loc[left]=cal[0]
lookup={stock:np.sort(g.known_date.dropna().to_numpy(dtype='datetime64[ns]')) for stock,g in e.groupby('instrument')}
afile=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet');a=pd.read_parquet(afile,columns=['month','era','level','industry_code','instrument','unresolved']);a=a[a.level.eq('L3')].drop_duplicates(['month','era','industry_code','instrument'])
pfile=EP/'restart/p11/selected_features.parquet';p=pd.read_parquet(pfile);rows=[]
for date,base in p.groupby('date'):
 lo=cal[cal.get_loc(date)-20];c=a[a.month.eq(date.to_period('M')-1)].copy();c['prior_seen']=c.instrument.map(first).lt(lo)
 has={stock:np.searchsorted(v,date.to_datetime64(),side='right')>np.searchsorted(v,lo.to_datetime64(),side='left') for stock,v in lookup.items()};c['recent']=c.prior_seen&c.instrument.map(has).eq(True)
 g=c.groupby(['era','industry_code']).agg(resolved=('instrument','nunique'),unresolved=('unresolved','max'),covered=('prior_seen','sum'),recent=('recent','sum')).reset_index();g['denominator']=g.resolved+g.unresolved
 z=base[ID+['top20','raw_score']].merge(g,on=['era','industry_code'],how='left',validate='many_to_one');z['window_begin']=lo;z['comparable']=z.top20&z.covered.ge(3)&z.covered.div(z.denominator).ge(.3);z['observed_recent']=z.comparable&z.recent.gt(0);z['no_recent_record']=z.comparable&z.recent.eq(0);rows.append(z)
p=pd.concat(rows,ignore_index=True);p['cell']=-1
for date,g in p[p.comparable].groupby('date'):
 size=g.sort_values(['denominator','industry_code']);sizebin=pd.Series(np.arange(len(g))>=len(g)/2,index=size.index).reindex(g.index).astype(int)
 score=g.sort_values(['raw_score','industry_code']);scorebin=pd.Series(np.arange(len(g))>=len(g)/2,index=score.index).reindex(g.index).astype(int);p.loc[g.index,'cell']=sizebin*2+scorebin
p.to_parquet(OUT/'selected_features.parquet',index=False)
(OUT/'selection_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [efile,afile,mfile,pfile,Path(__file__),EP/'restart/P16_plan_occurrence_plan.md']},features_sha256=sha(OUT/'selected_features.parquet')),indent=2)+'\n')
l=pd.read_parquet(EP/'outputs/r09/evaluation_panel.parquet');p=p.merge(l[ID+[f'win{h}' for h in [63,126,252]]],on=ID,validate='one_to_one');dates=calendar_dates();dates=dates[dates>=p.date.min()];summary=[];annual=[];coverage=[]
for name in ['top20','comparable','observed_recent','no_recent_record']:
 g=p[p[name]]
 for h in [63,126,252]:
  col=f'win{h}';coverage.append(dict(group=name,horizon=h,rows=len(g),known=g[col].notna().sum(),win_rate=g[col].mean(),success_week_coverage=g[col].sum()/p[col].sum()))
for h in [63,126,252]:
 col=f'win{h}'
 for matched in [False,True]:
  groupcols=['date','cell'] if matched else ['date'];a=p[p.comparable].groupby(groupcols+['observed_recent'])[col].agg(['size','count','mean']).unstack('observed_recent');valid=a[('size',True)].ge(3)&a[('size',False)].ge(3);v=(a[('mean',True)]-a[('mean',False)]).where(valid)
  if matched:v=v.groupby('date').mean()
  v=v.reindex(dates);lo,hi=block_ci(v,26 if h==126 else round(h/5));name='size_score_cells' if matched else 'same_date';summary.append(dict(comparison=name,horizon=h,dates=v.notna().sum(),delta=v.mean(),lo=lo,hi=hi));v.to_csv(OUT/f'{name}_{h}.csv')
  for year,g in v.groupby(v.index.year):annual.append(dict(comparison=name,horizon=h,year=int(year),dates=g.notna().sum(),delta=g.mean()))
p.to_parquet(OUT/'evaluated.parquet',index=False);pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False);pd.DataFrame(summary).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False)
print(pd.DataFrame(coverage).query('horizon==126').to_string(index=False));print(pd.DataFrame(summary).to_string(index=False));print(pd.DataFrame(annual).query('horizon==126').to_string(index=False))

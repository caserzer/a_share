import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha,calendar_dates,block_ci
OUT=EP/'restart/p20';OUT.mkdir(exist_ok=True);assert not (OUT/'selection_seal.json').exists(),'sealed'
cache=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5');raw=cache/'daily_industries.parquet';mf=cache/'CSI_ALL.parquet';sf=EP/'restart/p11/selected_features.parquet';of=EP/'restart/p17/evaluated.parquet';af=EP/'restart/p03/selected_features.parquet'
m=pd.read_parquet(mf).close.sort_index();mr=np.log(m).diff();d=pd.read_parquet(raw);d=d[d.level.eq('L3')];chunks=[]
for _,g in d.groupby(KEY):
 g=g.sort_values('date').copy();r=np.log(g.nav).diff();b=g.date.map(mr)
 g['beta']=r.rolling(126).cov(b).div(b.rolling(126).var()).shift(60)
 i60=np.log(g.nav/g.nav.shift(60));m60=np.log(g.date.map(m)/g.date.map(m).shift(60));g['relative60']=i60-m60;g['adjusted60']=i60-g.beta*m60
 chunks.append(g[ID+['beta','relative60','adjusted60']])
p=pd.read_parquet(sf);q=p.merge(pd.concat(chunks,ignore_index=True),on=ID,validate='one_to_one');q['available']=np.isfinite(q[['beta','relative60','adjusted60']]).all(axis=1)
q.groupby(q.date.dt.year).agg(rows=('date','size'),available=('available','sum')).to_csv(OUT/'coverage.csv');q=q[q.available].copy()
methods={'adjusted':('adjusted60',False),'momentum':('relative60',False),'low_beta':('beta',True),'tree':('raw_score',False)}
for name,(col,asc) in methods.items():
 a=q.sort_values(['date',col,'era','industry_code'],ascending=[True,asc,True,True]);q[name]=False;q.loc[a.index,name]=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2))
q=q.sort_values(KEY+['date']);group=q.groupby(KEY)
for name in methods:
 previous=group[name].shift();continuous=q.week_i.sub(group.week_i.shift()).eq(1);q[name+'_edge']=q[name]&previous.eq(False)&continuous;q[name+'_boundary']=q[name]&(~continuous|previous.isna())
q.to_parquet(OUT/'selected_features.parquet',index=False)
(OUT/'selection_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [raw,mf,sf,Path(__file__),EP/'restart/P20_market_exposure_plan.md']},selection=sha(OUT/'selected_features.parquet')),indent=2)+'\n')
o=pd.read_parquet(of);q=q.merge(o[ID+[f'joint{h}' for h in [63,126,252]]],on=ID,validate='one_to_one');age=pd.read_parquet(af);q=q.merge(age[ID+['state_age','state_drawup']],on=ID,how='left',validate='one_to_one');q.to_parquet(OUT/'evaluated.parquet',index=False)
rows=[];daily=[];early=[]
for method in methods:
 sel=q[q[method]];early.append(dict(method=method,rows=len(sel),stage_known=int(sel.state_age.notna().sum()),median_age_days=sel.state_age.median()*90,median_drawup=sel.state_drawup.median()))
 for h in [63,126,252]:
  col=f'joint{h}';base=q.groupby('date')[col].mean();total=q[col].sum()
  for date,g in sel.groupby('date'):daily.append(dict(date=date,year=date.year,method=method,horizon=h,win=g[col].mean(),base=base.loc[date],uplift=g[col].mean()-base.loc[date],known=g[col].notna().sum(),selected=len(g)))
  for unit in ['state','edge','boundary']:
   z=sel if unit=='state' else q[q[method+'_'+unit]]
   for year,g in [('ALL',z)]+list(z.groupby(z.date.dt.year)):
    rows.append(dict(method=method,horizon=h,unit=unit,year=str(year),rows=len(g),known=int(g[col].notna().sum()),win=g[col].mean(),uplift=(g[col]-g.date.map(base)).mean(),success_week_coverage=g[col].sum()/total if unit=='state' and year=='ALL' else np.nan))
a=pd.DataFrame(daily);a.to_csv(OUT/'daily.csv',index=False);a.groupby(['year','method','horizon'])[['win','base','uplift']].mean().to_csv(OUT/'annual.csv');pd.DataFrame(rows).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(early).to_csv(OUT/'early.csv',index=False)
axis=calendar_dates();axis=axis[(axis>=q.date.min())&(axis<=q.date.max())];comp=[]
for h,g in a.groupby('horizon'):
 v=g.pivot(index='date',columns='method',values='win').reindex(axis)
 for control in ['momentum','low_beta','tree']:
  delta=v.adjusted-v[control];lo,hi=block_ci(delta,26);comp.append(dict(horizon=h,control=control,dates=int(delta.notna().sum()),delta=delta.mean(),lo=lo,hi=hi))
pd.DataFrame(comp).to_csv(OUT/'comparisons.csv',index=False)
# Direct non-overlapping raw-window covariance check.
for _,row in q.sample(40,random_state=3320).iterrows():
 g=d[(d.era==row.era)&(d.industry_code==row.industry_code)&(d.block==row.block)].sort_values('date').reset_index(drop=True);i=int(g.index[g.date.eq(row.date)][0]);r=np.log(g.nav).diff();b=g.date.map(mr);ri=r.iloc[i-185:i-59].to_numpy();bi=b.iloc[i-185:i-59].to_numpy();beta=np.cov(ri,bi,ddof=1)[0,1]/np.var(bi,ddof=1);assert len(ri)==126 and np.isclose(beta,row.beta)
 adj=np.log(g.nav.iloc[i]/g.nav.iloc[i-60])-beta*np.log(m.loc[row.date]/m.loc[g.date.iloc[i-60]]);assert np.isclose(adj,row.adjusted60)
for method in methods:assert q.groupby('date')[method].sum().equals(q.groupby('date').momentum.sum())
assert sha(OUT/'selected_features.parquet')==json.loads((OUT/'selection_seal.json').read_text())['selection']
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',raw_disjoint_window_checks=40,same_capacity=True,selection_sealed=True,outcomes_sha256=sha(of),stage_sha256=sha(af)),indent=2)+'\n')
print(pd.DataFrame(comp).query('horizon==126').to_string(index=False));print(a[a.horizon.eq(126)].groupby(['year','method'])[['win','uplift']].mean().to_string());print(pd.DataFrame(early).to_string(index=False))

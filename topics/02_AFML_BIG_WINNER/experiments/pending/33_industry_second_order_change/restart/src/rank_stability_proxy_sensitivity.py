from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'p56/proxy_sensitivity';O.mkdir(exist_ok=True)
assert not (O/'receipt.json').exists()
f=R/'p30/training_panel.parquet';cols=['date','era','industry_code','level','block','eligible','rate5','history_proxy60']
p=pd.read_parquet(f,columns=cols);p=p[p.eligible & p.history_proxy60.eq(0) & p.rate5.notna()]
s=pd.read_csv(R/'p55/daily.csv',parse_dates=['date','previous_date']);s=s[s.status.eq('OK')&s.date.ge('2023-01-01')]
rows=[]
for _,v in s.iterrows():
 a=p[p.date.eq(v.previous_date)&p.era.eq(v.era)&p.level.eq(v.level)]
 b=p[p.date.eq(v.date)&p.era.eq(v.era)&p.level.eq(v.level)]
 c=a.merge(b,on=['era','industry_code','level','block'],suffixes=('_a','_b'),validate='one_to_one')
 rho=c.rate5_a.corr(c.rate5_b,method='spearman') if len(c)>=30 else np.nan
 rows.append(dict(date=v.date,common_original=v.common,common_clean=len(c),rho_original=v.rho,rho_clean=rho))
e=pd.DataFrame(rows);e.to_csv(O/'environment.csv',index=False)
q=pd.read_csv(R/'p56/joined.csv',parse_dates=['date']).drop(columns='rho').merge(e,on='date',how='left',validate='many_to_one')
axis=pd.DatetimeIndex(sorted(q.date.unique()));assert len(axis)==194
out=[];annual=[]
def slope(a,controlled):
 a=a[np.isfinite(a).all(axis=1)]
 if len(a)<8:return np.nan
 x=np.column_stack([np.ones(len(a)),a[:,1:] if controlled else a[:,1:2]])
 if np.linalg.matrix_rank(x)<x.shape[1]:return np.nan
 return np.linalg.lstsq(x,a[:,0],rcond=None)[0][1]*10
for (h,m),g in q.groupby(['horizon','method']):
 for variant in ['original','clean']:
  g=g.copy();g['rho']=g['rho_'+variant].where(g.rho_clean.notna());z=g.set_index('date').reindex(axis)
  for yr,t in z.groupby(z.index.year):
   a=t[['uplift','rho','market21','market126']].to_numpy(float)
   annual.append(dict(horizon=h,method=m,variant=variant,year=yr,dates=int(np.isfinite(a).all(axis=1).sum()),slope_pp=slope(a,False)))
  a=z[['uplift','rho','market21','market126']].to_numpy(float);n=len(a)
  for control in [False,True]:
   rng=np.random.default_rng(3309);v=[]
   for _ in range(500):
    ix=((rng.integers(0,n,size=int(np.ceil(n/26)))[:,None]+np.arange(26))%n).ravel()[:n];v.append(slope(a[ix],control))
   lo,hi=np.nanquantile(v,[.025,.975]);out.append(dict(horizon=h,method=m,variant=variant,controlled=control,dates=int(np.isfinite(a).all(axis=1).sum()),slope_pp=slope(a,control),lo=lo,hi=hi))
r=pd.DataFrame(out);r.to_csv(O/'summary.csv',index=False);pd.DataFrame(annual).to_csv(O/'annual.csv',index=False)
old=pd.read_csv(R/'p56/summary.csv');checks=0
if e.rho_clean.notna().all():
 for _,v in r[r.variant.eq('original')].iterrows():
  w=old[(old.horizon==v.horizon)&(old.method==v.method)&(old.controlled==v.controlled)].iloc[0]
  for c in ['dates','slope_pp','lo','hi']:assert np.isclose(v[c],w[c]);checks+=1
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
inputs=[f,R/'p55/daily.csv',R/'p56/joined.csv',R/'p56/summary.csv',R/'p56/proxy_sensitivity_plan.md',Path(__file__)]
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',original_statistic_checks=checks,source_columns=cols,inputs={str(x):sha(x) for x in inputs},outputs={x.name:sha(x) for x in O.glob('*.csv')}),indent=2)+'\n')
print(e[['common_original','common_clean','rho_clean']].describe().to_string());print(r.query('horizon==126').to_string(index=False));print(r.query('method=="momentum" and variant=="clean"').to_string(index=False))

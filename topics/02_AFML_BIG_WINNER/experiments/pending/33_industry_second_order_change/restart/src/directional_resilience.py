import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p37';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
nf=EP/'restart/p29/daily_industries.parquet';pf=EP/'restart/p30/training_panel.parquet';mf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet')
d=pd.read_parquet(nf,columns=['era','industry_code','date','day_i','block','nav']);m=pd.read_parquet(mf).close.sort_index();mr=np.log(m).diff();ids=['era','industry_code','date']
p=pd.read_parquet(pf,columns=ids+['eligible','rate60','history_proxy60']);p=p[p.eligible].copy();parts=[];groups={}
for key,g in d[d.nav.notna()].groupby(['era','industry_code','block']):
 g=g.sort_values('date').copy();r=np.log(g.nav).diff();x=g.date.map(mr);roll=lambda s:s.rolling(60,min_periods=60)
 # Series alignment uses the retained source row indices.
 er=roll(r).mean();ex=roll(x).mean();vx=roll(x*x).mean()-ex*ex;cov=roll(r*x).mean()-er*ex
 beta=cov/vx;alpha=er-beta*ex
 nd=roll(x.lt(0).astype(float)).sum();nu=roll(x.gt(0).astype(float)).sum()
 dr=roll(r.where(x.lt(0),0)).sum()/nd;ur=roll(r.where(x.gt(0),0)).sum()/nu
 dx=roll(x.where(x.lt(0),0)).sum()/nd;ux=roll(x.where(x.gt(0),0)).sum()/nu
 asym=(dr-ur)-beta*(dx-ux)
 residual_var=(roll(r*r).mean()-er*er)-cov*cov/vx
 valid=roll(r).count().eq(60)&nd.ge(15)&nu.ge(15)&vx.gt(0)&g.day_i.diff(60).eq(60)
 g['beta60']=beta.where(valid);g['residual_vol60']=np.sqrt(residual_var.clip(lower=0)).where(valid);g['resilience']=asym.where(valid);g['down_days']=nd;g['up_days']=nu
 parts.append(g[ids+['beta60','residual_vol60','resilience','down_days','up_days']]);groups[key]=g
f=pd.concat(parts,ignore_index=True);q=p.merge(f,on=ids,how='left',validate='one_to_one');q['supported']=q.resilience.notna();q.to_parquet(OUT/'features.parquet',index=False)
q.groupby(q.date.dt.year).agg(rows=('date','size'),supported=('supported','sum'),proxy=('history_proxy60','sum')).to_csv(OUT/'coverage.csv')
q.loc[q.supported,['rate60','beta60','residual_vol60','resilience']].corr().to_csv(OUT/'correlations.csv')
q.loc[q.supported,['resilience','beta60','down_days','up_days']].describe().to_csv(OUT/'distribution.csv')
# Independently reconstruct the last 61 levels with market calendar positions.
lookup=d.set_index(ids);checks=0
for _,a in q[q.supported].sample(120,random_state=3337).iterrows():
 row=lookup.loc[(a.era,a.industry_code,a.date)];g=groups[(a.era,a.industry_code,row.block)];w=g[g.date.le(a.date)].tail(61);assert len(w)==61 and w.day_i.diff().iloc[1:].eq(1).all()
 y=np.diff(np.log(w.nav.to_numpy()));x=mr.reindex(w.date).to_numpy()[1:];X=np.column_stack([np.ones(60),x]);coef=np.linalg.lstsq(X,y,rcond=None)[0];e=y-X@coef
 assert np.isclose(coef[1],a.beta60,atol=1e-9);assert np.isclose(e[x<0].mean()-e[x>0].mean(),a.resilience,atol=1e-10);assert np.isclose(np.sqrt(np.mean(e*e)),a.residual_vol60,atol=1e-10)
 checks+=1
inputs=[nf,pf,mf,Path(__file__),EP/'restart/P37_directional_resilience_plan.md']
(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',direct_ols_checks=checks,no_future_labels_read=True,inputs={str(x):sha(x) for x in inputs},artifacts={x.name:sha(x) for x in OUT.iterdir() if x.is_file()}),indent=2)+'\n')
print(pd.read_csv(OUT/'coverage.csv').to_string(index=False));print(pd.read_csv(OUT/'distribution.csv').to_string(index=False))

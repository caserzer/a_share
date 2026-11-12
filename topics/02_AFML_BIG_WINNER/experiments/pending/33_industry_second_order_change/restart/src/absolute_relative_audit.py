import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'p62';O.mkdir(exist_ok=True);assert not (O/'receipt.json').exists()
pf=R/'p30/training_panel.parquet';df=R/'p29/daily_industries.parquet';mf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet');sf=R/'p30/evaluated.parquet';ids=['era','industry_code','date']
p=pd.read_parquet(pf,columns=ids+['eligible','rate5','rate20','rate60']);p=p[p.eligible];m=pd.read_parquet(mf).close.sort_index();d=pd.read_parquet(df,columns=ids+['block','nav']);pieces=[]
for _,g in d[d.nav.notna()].groupby(['era','industry_code','block']):
 g=g.sort_values('date').copy()
 for h in [5,20,60]:g[f'direct{h}']=np.log(g.nav/g.nav.shift(h))*5/h
 pieces.append(g[ids+[f'direct{h}' for h in [5,20,60]]])
p=p.merge(pd.concat(pieces),on=ids,validate='one_to_one');checks=0;rankchecks=0
for h in [5,20,60]:
 p[f'market_rate{h}']=p.date.map(np.log(m/m.shift(h))*5/h);p[f'absolute{h}']=p[f'rate{h}']+p[f'market_rate{h}'];assert p[[f'absolute{h}',f'direct{h}']].notna().all().all();assert np.allclose(p[f'absolute{h}'],p[f'direct{h}'],atol=1e-12,rtol=1e-10);checks+=len(p)
 # Verify pairwise ordering identity algebraically by centered values; avoids float tie artifacts.
 a=p[f'absolute{h}']-p.groupby('date')[f'absolute{h}'].transform('mean');b=p[f'rate{h}']-p.groupby('date')[f'rate{h}'].transform('mean');assert np.allclose(a,b,atol=1e-12,rtol=1e-10);rankchecks+=p.date.nunique()
p.to_parquet(O/'features.parquet',index=False)
s=pd.read_parquet(sf,columns=ids+['rebuilt','momentum']);q=p[p.date.ge('2023-01-01')].merge(s,on=ids,how='left',validate='one_to_one');assert q[['rebuilt','momentum']].notna().all().all();rows=[]
for h in [5,20,60]:
 for universe in ['all','rebuilt','momentum']:
  g=q if universe=='all' else q[q[universe]]
  for year,t in g.groupby(g.date.dt.year):
   relative=t[f'rate{h}'].gt(0);absolute=t[f'absolute{h}'].gt(0);rows.append(dict(horizon=h,universe=universe,year=year,rows=len(t),relative_positive=int(relative.sum()),relative_positive_absolute_nonpositive=int((relative&~absolute).sum()),fraction_of_relative_positive=float((relative&~absolute).sum()/relative.sum()) if relative.sum() else np.nan,absolute_positive_fraction=float(absolute.mean())))
a=pd.DataFrame(rows);a.to_csv(O/'annual.csv',index=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=[pf,df,mf,sf,R/'P62_absolute_relative_audit_plan.md',Path(__file__)]
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',future_label_columns_read=False,price_identity_row_checks=checks,date_centering_checks=rankchecks,inputs={str(p):sha(p) for p in inputs},outputs={p.name:sha(p) for p in O.iterdir() if p.is_file()}),indent=2)+'\n');print(a.query('horizon==60').to_string(index=False))

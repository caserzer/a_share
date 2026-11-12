import json,sys
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p29';receipt=json.loads((OUT/'receipt.json').read_text())
for path,value in receipt['inputs'].items():assert sha(Path(path))==value
for name,value in receipt['artifacts'].items():assert sha(OUT/name)==value
ids=['era','industry_code','date'];d=pd.read_parquet(OUT/'daily_industries.parquet');strict=pd.read_parquet(EP/'restart/p24/daily_industries.parquet');a=d.merge(strict[ids+['relative_nav']],on=ids,suffixes=('','_strict'),validate='one_to_one');both=a.relative_nav.notna()&a.relative_nav_strict.notna();assert np.allclose(a.loc[both,'relative_nav'],a.loc[both,'relative_nav_strict'],atol=1e-12)
checks=0
for _,g in d.groupby(['era','industry_code']):
 g=g.sort_values('date');prev=g.stale_members.shift().gt(0);consecutive=g.day_i.diff().eq(1);first=g.date.dt.to_period('M').ne(g.date.shift().dt.to_period('M'));prevvalid=g.nav.shift().notna();expected=prev&consecutive&first&prevvalid;assert np.array_equal(expected,g.boundary_proxy);checks+=len(g)
w=pd.read_parquet(OUT/'weekly_path_support.parquet');groups={k:g.set_index('day_i') for k,g in d.groupby(['era','industry_code'])};qc=0
for _,r in w.sample(120,random_state=3329).iterrows():
 g=groups[(r.era,r.industry_code)];i=int(r.day_i)
 for h in [63,126,252]:
  b=g.reindex(range(i,i+h+2));valid=b.nav.notna().all() and b.block.nunique(dropna=False)==1;assert valid==bool(r[f'path{h}'])
  if valid:
   assert bool(r[f'path_proxy{h}'])==bool((b.stale_members.gt(0)|b.boundary_proxy).any());assert bool(r[f'entry_stale{h}'])==bool(b.stale_members.iloc[1]>0);assert bool(r[f'end_stale{h}'])==bool(b.stale_members.iloc[-1]>0)
  else:assert pd.isna(r[f'path_proxy{h}'])
  qc+=1
rows=[]
for year,g in w.groupby(w.date.dt.year):
 for h in [63,126,252]:
  e=g[g.history60];valid=e[e[f'path{h}']];endstale=valid[f'entry_stale{h}'].eq(True)|valid[f'end_stale{h}'].eq(True);proxy=valid[f'path_proxy{h}'].eq(1)
  rows.append(dict(year=int(year),horizon=h,catalog=len(g),history60=len(e),history_proxy=int(e.history_proxy60.eq(1).sum()),valued_path=len(valid),path_all_observed=int((~proxy).sum()),internal_proxy_endpoints_observed=int((proxy&~endstale).sum()),endpoint_stale=int(endstale.sum()),calendar_immature=int((~e[f'calendar_mature{h}']).sum()),mature_hard_unknown=int((e[f'calendar_mature{h}']&~e[f'path{h}']).sum())))
pd.DataFrame(rows).to_csv(OUT/'quality_support.csv',index=False)
stats=dict(status='PASS',same_relative_nav_rows=int(both.sum()),strict_observed_proxy_unknown=int((a.relative_nav_strict.notna()&a.relative_nav.isna()).sum()),boundary_checks=checks,independent_window_checks=qc,stale_nav_days=int((d.nav.notna()&d.stale_members.gt(0)).sum()),proxy_boundaries=int(d.boundary_proxy.sum()),max_stale_days=int(d.max_stale_days.max()),checker_sha256=sha(Path(__file__)))
(OUT/'independent_validation.json').write_text(json.dumps(stats,indent=2)+'\n');print(json.dumps(stats));print(pd.DataFrame(rows).query('year>=2023 and horizon==126').to_string(index=False))

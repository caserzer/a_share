import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p24';receipt=json.loads((OUT/'receipt.json').read_text())
for path,value in receipt['inputs'].items():assert sha(Path(path))==value
for name,value in receipt['artifacts'].items():assert sha(OUT/name)==value
n=pd.read_parquet(OUT/'daily_industries.parquet');old=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet');old=old[old.level.eq('L3')];audit=pd.read_csv(OUT/'month_audit.csv');complete=audit[audit.complete&audit.eligible][['era','industry_code','month']];n['month']=n.date.dt.strftime('%Y-%m');old['month']=old.date.dt.strftime('%Y-%m')
a=n[n.status.ne('ORIGIN')].merge(complete,on=['era','industry_code','month'],validate='many_to_one');a=a.merge(old[['era','industry_code','date','nav']],on=['era','industry_code','date'],suffixes=('_new','_old'),how='left',validate='one_to_one');assert a.nav_old.notna().all();g=a.sort_values('date').groupby(['era','industry_code','month']);nr=a.nav_new/g.nav_new.transform('first');or_=a.nav_old/g.nav_old.transform('first');assert np.allclose(nr,or_,atol=1e-10,rtol=1e-10)
w=pd.read_parquet(OUT/'weekly_path_support.parquet');groups={k:g.set_index('day_i').sort_index() for k,g in n.groupby(['era','industry_code'])};paths=0
for _,row in w.sample(200,random_state=3324).iterrows():
 g=groups[(row.era,row.industry_code)];day=int(row.day_i)
 for h in [60,63,126,252]:
  lo,hi=(day-60,day) if h==60 else (day,day+h+1);b=g.reindex(range(lo,hi+1));good=b.nav.notna().all() and b.block.nunique(dropna=False)==1
  if h==60:good=good and row.status!='ORIGIN'
  assert bool(good)==bool(row.history60 if h==60 else row[f'path{h}']);paths+=1
rows=[]
for year,g in w.groupby(w.date.dt.year):
 for h in [63,126,252]:
  rows.append(dict(year=int(year),horizon=h,catalog_rows=len(g),eligible=int(g.history60.sum()),eligible_known_path=int((g.history60&g[f'path{h}']).sum()),eligible_calendar_immature=int((g.history60&~g[f'calendar_mature{h}']).sum()),eligible_mature_missing_path=int((g.history60&g[f'calendar_mature{h}']&~g[f'path{h}']).sum())))
pd.DataFrame(rows).to_csv(OUT/'eligible_path_support.csv',index=False)
# Explicit absent/unknown catalog status is retained and no block crosses an unknown day.
assert n.loc[n.nav.isna(),'block'].isna().all()
for _,g in n.groupby(['era','industry_code']):
 b=g.sort_values('date');valid=b.nav.notna();same=b.block.eq(b.block.shift()).fillna(False);assert not (same&(~valid|~valid.shift(fill_value=False))).any()
(OUT/'independent_validation.json').write_text(json.dumps(dict(status='PASS',complete_month_rows_compared=len(a),complete_months=len(complete),raw_calendar_path_checks=paths,unknown_blocks_preserved=True,all_saved_inputs_and_artifacts_verified=True,checker_sha256=sha(Path(__file__))),indent=2)+'\n')
print(pd.DataFrame(rows).query('horizon==126').to_string(index=False));print('complete compared',len(a),len(complete))
t=pd.read_csv(OUT/'eligibility_transition.csv');print(t[t.date.ge(2023)].groupby(['old_eligible','history60']).rows.sum().to_string())

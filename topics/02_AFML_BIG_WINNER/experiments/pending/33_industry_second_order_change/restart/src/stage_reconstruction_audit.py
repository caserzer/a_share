import ast,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];EP=R.parent;O=R/'p57';O.mkdir(exist_ok=True)
assert not (O/'receipt.json').exists()
src=EP.parent/'32_industry_rotation_cycle_observation/extensions/v7_online_stage/src/state7.py'
tree=ast.parse(src.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='trace');env={'np':np,'pd':pd};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(src),'exec'),env);trace=env['trace']
f=R/'p29/daily_industries.parquet';wfile=R/'p30/training_panel.parquet';oldfile=Path('/home/xiaolv/.cache/a_share/ep32/online_v7/state_features.parquet')
w=pd.read_parquet(wfile,columns=['era','industry_code','date','block','eligible']);w=w[w.eligible]
d=pd.read_parquet(f,columns=['era','industry_code','level','block','date','nav']);d=d[d.level.eq('L3') & d.nav.notna() & d.block.notna()]
ids=['era','industry_code','date'];groups={k:g for k,g in w.groupby(['era','industry_code','block'])};rows=[];checks=0
for key,g in d.groupby(['era','industry_code','block']):
 if key not in groups:continue
 g=g.sort_values('date');t=trace(g.nav,g.date,.15)
 if checks<20 and len(g)>100:
  a=trace(g.nav.iloc[:100],g.date.iloc[:100],.15);pd.testing.assert_frame_equal(a,t.iloc[:100].reset_index(drop=True))
  b=trace(g.nav*7,g.date,.15);pd.testing.assert_frame_equal(b,t,check_exact=False,rtol=1e-9,atol=1e-9);checks+=1
 for c,v in zip(['era','industry_code','block'],key):t[c]=v
 rows.append(t.merge(groups[key][ids],on=ids,validate='one_to_one'))
s=pd.concat(rows,ignore_index=True);assert len(s)==len(w);assert not s.duplicated(ids).any();s.to_parquet(O/'rebuilt_states.parquet',index=False)
old=pd.read_parquet(oldfile);old=old[old.level.eq('L3') & old.threshold.eq(.15)]
features=['state_direction','state_left','state_age','state_confirm_age','state_drawup','state_drawdown','state_previous_decline','state_eligible','candidate_low_date']
old=old[ids+['block']+features].drop_duplicates();assert not old.duplicated(ids).any()
z=s.merge(old,on=ids,how='left',suffixes=('_new','_old'),indicator=True,validate='one_to_one');z.to_parquet(O/'comparison.parquet',index=False)
res=[]
for year,g in z.groupby(z.date.dt.year):
 known=g[g['_merge'].eq('both')]
 for c in features:
  a=known[c+'_new'];b=known[c+'_old'];valid=a.notna()&b.notna()
  if c=='candidate_low_date':different=a[valid].ne(b[valid]);delta=np.nan
  else:different=~np.isclose(a[valid].astype(float),b[valid].astype(float),rtol=1e-8,atol=1e-8);delta=(a[valid]-b[valid]).abs().median()
  res.append(dict(year=year,feature=c,eligible_rows=len(g),old_matched=len(known),known=int(valid.sum()),different=int(np.sum(different)),different_fraction=float(np.mean(different)) if len(different) else np.nan,median_abs_delta=delta))
a=pd.DataFrame(res);a.to_csv(O/'annual.csv',index=False)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
inputs=[src,f,wfile,oldfile,R/'P57_stage_reconstruction_audit_plan.md',Path(__file__)]
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',future_labels_read=False,eligible_rows=len(w),rebuilt_rows=len(s),prefix_checks=checks,scale_checks=checks,inputs={str(p):sha(p) for p in inputs},outputs={p.name:sha(p) for p in O.iterdir() if p.is_file()}),indent=2)+'\n')
print(a[a.year.ge(2023)&a.feature.isin(['state_direction','candidate_low_date','state_eligible','state_age'])].to_string(index=False))

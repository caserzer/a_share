import ast,json,sys
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,ID,KEY,calendar_dates,block_ci
OUT=EP/'restart/p03';seal=json.loads((OUT/'selection_seal.json').read_text())
assert all(sha(f)==s for f,s in seal['inputs'].items());assert sha(OUT/'selected_features.parquet')==seal['features_sha256']
f=pd.read_parquet(OUT/'selected_features.parquet');p=pd.read_parquet(OUT/'evaluated_panel.parquet');pd.testing.assert_frame_equal(f[ID],p[ID]);assert not any(c.startswith(('win','status')) for c in f)
# Run only the existing pure trace definition, without state7 build side effects.
source=EP.parent/'32_industry_rotation_cycle_observation/extensions/v7_online_stage/src/state7.py'
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='trace');ns={'np':np,'pd':pd};exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
d=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet');d=d[d.level.eq('L3')];groups={k:g.sort_values('date') for k,g in d.groupby(KEY)}
for _,row in p[p.state_eligible.notna()].sample(60,random_state=3303).iterrows():
 g=groups[tuple(row[k] for k in KEY)];g=g[g.date.le(row.date)];x=ns['trace'](g.nav,g.date,.15).iloc[-1]
 for c in ['state_direction','state_age','state_drawup','state_eligible']:assert np.isclose(row[c],x[c]),(row.date,c)
 assert row.candidate_low_date==x.candidate_low_date
summ=pd.read_csv(OUT/'summary.csv');cal=pd.DatetimeIndex(pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet').index)
for _,r in summ.iterrows():
 z=p[p[r.method if r.unit=='state' else 'entry_'+r.method]];col=f'win{r.horizon}';assert len(z)==r.total;assert z[col].notna().sum()==r.known;assert np.isclose(z[col].mean(),r.win_rate)
 if r.unit=='entry':
  for _,g in z.groupby(KEY):
   ix=cal.get_indexer(g.sort_values('date').date);assert (np.diff(ix)>=127).all()
# Pre-specified period and annual diagnostics, plus age composition of the primary contrast.
rows=[];dates=calendar_dates()
for file in sorted(OUT.glob('*_126.csv')):
 v=pd.read_csv(file,index_col=0,parse_dates=[0]).delta
 for year,g in v.groupby(v.index.year):rows.append(dict(comparison=file.stem,period=str(year),dates=g.notna().sum(),delta=g.mean()))
 for name,mask in [('old_common',v.index<=pd.Timestamp('2024-09-30')),('later_seen',v.index>pd.Timestamp('2024-09-30'))]:
  g=v[mask];lo,hi=block_ci(g,26);rows.append(dict(comparison=file.stem,period=name,dates=g.notna().sum(),delta=g.mean(),lo=lo,hi=hi))
pd.DataFrame(rows).to_csv(OUT/'paired_periods.csv',index=False)
composition=[]
for m in summ.method.unique():
 g=p[p[m]];composition.append(dict(method=m,rows=len(g),zero_age_fraction=g.state_age.eq(0).mean(),median_age_days=g.state_age.median()*90,median_drawup=g.state_drawup.median()))
pd.DataFrame(composition).to_csv(OUT/'state_composition.csv',index=False)
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',state_prefix_checks=60,summary_checks=len(summ),cooldown_verified=True,selection_seal_verified=True,trace_source_sha256=sha(source),efficacy_established=False),indent=2)+'\n')
print(pd.DataFrame(rows).query('comparison=="relative_unconfirmed_126"').to_string(index=False));print(pd.DataFrame(composition).to_string(index=False))

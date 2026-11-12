import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha
OUT=EP/'restart/p09';s=json.loads((OUT/'selection_seal.json').read_text());assert all(sha(f)==h for f,h in s['inputs'].items());assert sha(OUT/'selected_features.parquet')==s['features_sha256']
p=pd.read_parquet(OUT/'selected_features.parquet');e=pd.read_parquet(OUT/'evaluated.parquet');pd.testing.assert_frame_equal(p[ID],e[ID]);assert not any(c.startswith(('win','status')) for c in p)
checks=0
for regime in ['UP','NONUP']:
 assert p[regime+'_price_tree'].equals(p[regime])
 for policy,ascending in [('reversal60',True),('momentum60',False)]:
  name=regime+'_'+policy
  for date,g in p.groupby('date'):
   k=int(g[regime].sum());expected=set(g.sort_values(['rate60','era','industry_code'],ascending=[ascending,True,True]).head(k).index);assert set(g[g[name]].index)==expected;checks+=1
 for policy in ['price_tree','reversal60','momentum60']:
  name=regime+'_'+policy
  for _,g in p.groupby(KEY):
   prev=None;last=None
   for _,r in g.sort_values('date').iterrows():
    edge=bool(prev is not None and r.week_i-prev.week_i==1 and r[name] and not prev[name]);cool=edge and (last is None or r.day_i-last>=126)
    assert edge==r[name+'_edge'] and cool==r[name+'_cooldown']
    if cool:last=r.day_i
    prev=r
for _,r in pd.read_csv(OUT/'summary.csv').iterrows():
 flag=r.method if r.unit=='state' else r.method+'_'+r.unit;z=e[e[flag]];col=f'win{r.horizon}';assert len(z)==r.total and z[col].notna().sum()==r.known;assert np.isclose(z[col].mean(),r.win_rate)
# Verify actual rate60 formula against raw price endpoints (definition erratum).
d=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet');d=d[d.level.eq('L3')];groups={k:g.sort_values('date').set_index('date') for k,g in d.groupby(KEY)};m=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet').close
for _,r in p.sample(30,random_state=3309).iterrows():
 g=groups[tuple(r[k] for k in KEY)];i=g.index.get_loc(r.date);assert i>=60;old=g.index[i-60];value=(np.log(g.nav.iloc[i]/m.loc[r.date])-np.log(g.nav.iloc[i-60]/m.loc[old]))*5/60;assert np.isclose(value,r.rate60)
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',capacity_ranking_checks=checks,summary_checks=54,sequential_events_verified=True,raw_rate60_checks=30,definition_erratum_sha256=sha(EP/'restart/P09_definition_erratum.md'),seals_verified=True,efficacy_established=False),indent=2)+'\n')
print('PASS',checks,'capacity/rank checks, 54 summaries, 30 raw rate60 checks')
print(pd.read_csv(OUT/'composition.csv').to_string(index=False));print(pd.read_csv(OUT/'annual.csv').query('horizon==126 and unit=="edge" and method.str.startswith("NONUP")').to_string(index=False))

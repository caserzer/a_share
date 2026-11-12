import json,sys
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,ID,KEY
OUT=EP/'restart/p08';s=json.loads((OUT/'selection_seal.json').read_text());assert all(sha(f)==h for f,h in s['inputs'].items());assert sha(OUT/'selected_features.parquet')==s['features_sha256']
p=pd.read_parquet(OUT/'selected_features.parquet');e=pd.read_parquet(OUT/'evaluated.parquet');pd.testing.assert_frame_equal(p[ID],e[ID]);assert not any(c.startswith(('win','status')) for c in p)
c=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet').close.sort_index()
for date,g in p.groupby('date'):
 i=c.index.get_loc(date);assert np.allclose(g.market126,c.iloc[i]/c.iloc[i-126]-1)
assert ((p.UP|p.NONUP)==p.top20).all() and not (p.UP&p.NONUP).any()
assert ((p.UP_original_edge|p.NONUP_original_edge)==p.top20_edge).all()
for m in ['UP','NONUP']:
 for _,g in p.groupby(KEY):
  prev=None;last=None
  for _,r in g.sort_values('date').iterrows():
   continuous=prev is not None and r.week_i-prev.week_i==1;edge=bool(r[m] and continuous and not prev[m]);cool=edge and (last is None or r.day_i-last>=126)
   assert edge==r[m+'_edge'] and cool==r[m+'_cooldown']
   assert bool(edge and prev.top20)==r[m+'_market_trigger']
   if cool:last=r.day_i
   prev=r
for _,r in pd.read_csv(OUT/'summary.csv').iterrows():
 z=e[e[r.market+'_'+r.unit]];col=f'win{r.horizon}';assert len(z)==r.total and z[col].notna().sum()==r.known;assert np.isclose(z[col].mean(),r.win_rate)
coverage=[]
for m in ['UP','NONUP']:
 for year,g in e.groupby(e.date.dt.year):coverage.append(dict(market=m,year=int(year),all_dates=g.date.nunique(),selected_dates=g.loc[g[m],'date'].nunique(),selected_weeks=int(g[m].sum()),known_selected=int(g.loc[g[m],'win126'].notna().sum()),successful_selected=g.loc[g[m],'win126'].sum(),all_successes=g.win126.sum()))
pd.DataFrame(coverage).to_csv(OUT/'annual_coverage.csv',index=False)
repeat=[]
for m in ['UP','NONUP']:
 for unit in ['edge','cooldown']:
  z=e[e[m+'_'+unit]];repeat.append(dict(market=m,unit=unit,total=len(z),same_low_repeats=int(z.duplicated(KEY+['candidate_low_date']).sum()),early_fraction=z.state_eligible.eq(1).mean()))
pd.DataFrame(repeat).to_csv(OUT/'repeat_diagnostic.csv',index=False)
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',market_dates=p.date.nunique(),summary_checks=18,sequential_event_flags_verified=True,partitions_reconciled=True,seals_verified=True,efficacy_established=False),indent=2)+'\n')
print(pd.DataFrame(coverage).to_string(index=False));print(pd.DataFrame(repeat).to_string(index=False))

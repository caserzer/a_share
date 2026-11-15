"""Independent observation/episode/capacity and hindsight-separation audit."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,sha
from v3_candidate_delivery import CANDIDATES
root=EP/'handoff/v3_candidates_20261016';replay=EP/'outputs/v3_m06_replay';checks=[];refs=0
rec=json.loads((root/'receipt.json').read_text())
for f,h in rec['inputs'].items():assert sha(Path(f))==h;refs+=1
for f,h in rec['artifacts'].items():assert sha(root/f)==h;refs+=1
support=pd.read_csv(root/'calendar_coverage.csv',parse_dates=['date']);supported=support[support.state.eq('SUPPORTED_DIRECTORY')].set_index('date').directory_count
for name,arm in CANDIDATES.items():
 f=pd.read_parquet(root/name/'all_period_catalog.parquet');le=pd.read_parquet(root/name/'event_history.parquet');ev=pd.read_parquet(replay/f'solo_{arm}_COMPETE/events.parquet');cat=pd.read_parquet(replay/f'solo_{arm}_COMPETE/catalog_states.parquet')
 assert set(le.event_id)==set(ev.event_id) and le.event_id.is_unique
 pd.testing.assert_frame_equal(f[cat.columns],cat,check_dtype=False)
 sizes=f.groupby('date').size();pd.testing.assert_series_equal(sizes.astype(float),supported,check_names=False)
 assert f.observation_id.notna().eq(f.state.isin(['NEW','TRACKING','EXIT'])).all()
 assert (pd.to_datetime(le.first_alert)<=le.date).all()
 assert set(le.loc[le.event_kind.eq('NEW'),'observation_id'])==set(le.loc[le.event_kind.eq('NEW'),'event_id'])
 source=ev.set_index('event_id');active={};prior={};maxpool=0
 for date,g in le.groupby('date',sort=True):
  n=0
  for r in g.itertuples():
   k=(r.era,r.industry_code)
   if r.event_kind=='NEW':
    assert k not in active and r.previous_observation_id==prior.get(k)
    active[k]=r.observation_id;n+=1
   assert active[k]==r.observation_id
   if r.event_kind=='EXIT':prior[k]=active.pop(k)
   assert source.loc[r.event_id,'kind']==r.event_kind
  assert n<=5 and len(active)<=20;maxpool=max(maxpool,len(active))
  entries=f[f.date.eq(date)&f.state.isin(['NEW','TRACKING'])]
  assert set(zip(entries.era,entries.industry_code))==set(active)
 if arm=='BALANCED':np.testing.assert_allclose(f.score,(f.coverage_rank_pct+f.early_rank_pct)/2,equal_nan=True)
 else:np.testing.assert_allclose(f.score,f.r20,equal_nan=True)
 assert not any('target' in c or 'label' in c or 'process_id' in c for c in f.columns)
 w=pd.read_csv(root/name/'weekly_workload.csv');unknown=w[w.directory_status.ne('SUPPORTED_DIRECTORY')];assert len(unknown)==5 and unknown['NEW'].isna().all()
 latest=pd.read_csv(root/name/'latest_full_directory.csv');assert len(latest)==347 and latest.date.nunique()==1
 checks.append(dict(candidate=name,rows=len(f),periods=len(sizes),events=len(le),max_pool=maxpool,new=int(le.event_kind.eq('NEW').sum()),latest_full_directory=len(latest)))
result=dict(result='PASS_OBSERVATION_DELIVERY_NOT_BUSINESS_ACCEPTANCE',hash_references=refs,checks=checks,unknown_calendar_weeks=5)
(root/'delivery_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

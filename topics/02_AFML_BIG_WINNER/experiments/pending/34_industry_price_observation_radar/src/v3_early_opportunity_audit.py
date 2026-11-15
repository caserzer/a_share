"""Retrospective early-window funnel, never used as signal input."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha

out=EP/'outputs/v3_early_opportunity_audit'
assert not out.exists();out.mkdir()
evalroot=EP/'outputs/evaluation_versions/v3_m04_e02b';trace_root=EP/'outputs/v3_m04_decisions'
version=json.loads((evalroot/'version.json').read_text());calpath=Path(version['calendar_path']);cal=pd.read_parquet(calpath);cal['week']=cal.date.dt.to_period('W-SUN');reviews=cal.groupby('week').date.max()
if cal.date.max().weekday()<4:reviews=reviews.iloc[:-1]
reviews=reviews.to_numpy()
parents_path=EP/'outputs/v2_s12_full_directory_duration/processes.parquet';parents=pd.read_parquet(parents_path).set_index('process_id')
wpath=EP/'outputs/v2_s12_full_directory_duration/boundary_audit/weekly_evaluation_states.parquet';states=pd.read_parquet(wpath,columns=['era','industry_code','block','week','process_id'])
rawpath=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawpath,columns=['date','era','industry_code','block','nav']);raw=raw[raw.nav.gt(0)&raw.block.notna()];raw['week']=raw.date.dt.to_period('W-SUN').astype(str);raw['ln']=np.log(raw.nav)
med=raw.groupby(['era','industry_code','block','week']).ln.median().to_dict()
def deadline(date):
 j=np.searchsorted(reviews,np.datetime64(date));return pd.Timestamp(reviews[min(j+1,len(reviews)-1)])
inputs=[Path(__file__),parents_path,wpath,rawpath,calpath,evalroot/'receipt.json',trace_root/'receipt.json'];records=[]
for file in sorted(trace_root.glob('solo_*_online_decisions.parquet')):
 run=file.name.removesuffix('_online_decisions.parquet');inputs.append(file)
 trace=pd.read_parquet(file);start=trace.date.min();trace['week']=trace.date.dt.to_period('W-SUN').astype(str)
 trace=trace.merge(states,on=['era','industry_code','block','week'],how='left',validate='one_to_one');groups={pid:g for pid,g in trace.groupby('process_id')}
 pcpath=evalroot/'runs'/run/'parent_coverage.parquet';inputs.append(pcpath);pc=pd.read_parquet(pcpath)
 assert len(pc)==4540
 for r in pc.itertuples():
  p=parents.loc[r.process_id];end=deadline(p.visible_date);base=float(np.exp(med[p.era,p.industry_code,p.block,str(pd.Timestamp(p.start_date).to_period('W-SUN'))]))
  g=groups.get(r.process_id,trace.iloc[:0]);g=g[g.date.le(end)]
  known=g[g.known_support];pos=known[known.r5.gt(0)&known.nav.gt(base)]
  admissible=pos[pos.eligible];available=admissible[~admissible.cooldown];top=available[available.candidate_rank.le(5)]
  actual=pos[pos.actual_kind.isin(['NEW','UPDATE'])]
  assert (not actual.empty)==(r.timing=='TIMELY'),(run,r.process_id)
  if r.timing=='TIMELY':stage='TIMELY_CAPTURED'
  elif end<start:stage='WINDOW_BEFORE_EVALUATION'
  elif g.empty:stage='NO_DIRECTORY_REVIEW_IN_WINDOW'
  elif known.empty:stage='NO_FEATURE_SUPPORT_IN_WINDOW'
  elif pos.empty:stage='NO_POSITIVE_ALIGNMENT_IN_WINDOW'
  elif admissible.empty:stage='ADMISSION_GATE_ALL_POSITIVE_ROWS'
  elif available.empty:stage='COOLDOWN_ALL_ADMISSIBLE_ROWS'
  elif top.empty:stage='NEVER_TOP5_WHEN_AVAILABLE'
  else:
   assert top.candidate_rank.gt(top.free_slots).all()
   stage='TOP5_BLOCKED_BY_POOL_CAPACITY'
  records.append(dict(run_id=run,process_id=r.process_id,stage=stage,final_outcome='TIMELY' if r.timing=='TIMELY' else 'LATE' if r.covered else 'MISSED',start=p.start_date,deadline=str(end.date()),left_scope=pd.Timestamp(p.start_date)<start,review_rows=len(g),supported_rows=len(known),positive_rows=len(pos),admissible_rows=len(admissible),available_rows=len(available),top5_rows=len(top),first_positive=None if pos.empty else str(pos.date.min().date())))
 print('Early window audited',run,flush=True)
x=pd.DataFrame(records);x.to_parquet(out/'all_parent_windows.parquet',index=False)
x.groupby(['run_id','stage','final_outcome']).size().rename('processes').to_csv(out/'stage_outcomes.csv')
summary=x.groupby(['run_id','stage']).size().unstack(fill_value=0);assert summary.sum(axis=1).eq(4540).all();summary.to_csv(out/'stage_totals.csv')
(out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in inputs},artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()},scope='Seven standalone pools, all 4540 parent processes each. Staged retrospective description, not causal effects or feasible simultaneous capture. No new fit or changed pool.'),indent=2)+'\n')
print(summary.to_string())

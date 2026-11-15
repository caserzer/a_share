"""Independent dataframe priority reconstruction and complete outcome transitions."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha

root=EP/'outputs/v3_m06_replay';evaluation=EP/'outputs/evaluation_versions/v3_m06';out=EP/'outputs/v3_m06_audit'
assert not out.exists();out.mkdir();refs=0
for directory in [root,evaluation]:
 r=json.loads((directory/'receipt.json').read_text())
 for f,h in r['inputs'].items():assert sha(Path(f))==h;refs+=1
 for f,h in r['artifacts'].items():assert sha(directory/f)==h;refs+=1
scorepath=root/'signal_catalog.parquet';c=pd.read_parquet(scorepath)
inv=pd.read_csv(root/'run_inventory.csv');summaries=[];pair={}
for run in inv.itertuples():
 ev=pd.read_parquet(root/run.run_id/'events.parquet');trace=pd.read_parquet(root/run.run_id/'decisions.parquet').set_index('date');events={d:g for d,g in ev.groupby('date')};pool=set();exits={};replacement_count=0
 assert ev.event_id.is_unique and not ev.duplicated(['date','era','industry_code']).any()
 for date,g in c.groupby('date'):
  e=events.get(date,ev.iloc[:0]);week=int(g.week.iloc[0]);forced=e[e.kind.eq('EXIT')&e.reason.ne('LOWER_CURRENT_PRIORITY')];competitive=e[e.reason.eq('LOWER_CURRENT_PRIORITY')]
  keyset=lambda z:set(zip(z.era,z.industry_code))
  gone=keyset(forced);assert gone<=pool;pool-=gone
  for k in gone:exits[k]=week
  orig=run.arm.startswith('ORIGINAL20');column='eligible_original' if orig else 'eligible';score='score_'+run.arm.removesuffix('_COMPETE')
  g=g.copy();g['key']=list(zip(g.era,g.industry_code));g['held']=g.key.isin(pool);g['cool']=g.key.map(lambda k:week-exits.get(k,-100)<4)
  candidate=g[g[column]&~g.held&~g.cool]
  held=g[g.held];combined=pd.concat([held,candidate]);combined=combined.assign(priority_group=~combined[column],priority_score=combined[score].where(combined[column],0)).sort_values(['priority_group','priority_score','industry_code'],ascending=[True,False,True])
  ranked=candidate.sort_values([score,'industry_code'],ascending=[False,True]);free=20-len(pool)
  if run.arm.endswith('COMPETE'):ranked=ranked[ranked.key.isin(combined.head(20).key)];capacity=min(run.quota,len(ranked))
  else:capacity=min(run.quota,len(ranked),free)
  d=trace.loc[date];new=keyset(e[e.kind.eq('NEW')]);q=len(new)
  assert new==set(ranked.head(q).key) and q<=capacity and d.own_capacity==capacity
  if run.mode=='solo':assert q==capacity
  n=max(0,q-free);losers=list(combined[combined.held].key)[-n:] if n else []
  assert keyset(competitive)==set(losers) and len(competitive)==n
  pool-=set(losers)
  for k in losers:exits[k]=week
  assert keyset(e[e.kind.eq('UPDATE')])==pool
  pool|=new;assert len(pool)<=20 and q<=run.quota
  replacement_count+=n
 if run.mode=='paired':
  q=ev[ev.kind.eq('NEW')].groupby('date').size().reindex(sorted(c.date.unique()),fill_value=0).tolist()
  if run.quota in pair:assert pair[run.quota]==q
  else:pair[run.quota]=q
 assert replacement_count==run.replacements
 pc=pd.read_parquet(evaluation/'runs'/run.run_id/'parent_coverage.parquet');cc=pd.read_parquet(evaluation/'runs'/run.run_id/'child_coverage.parquet');quality=pd.read_parquet(evaluation/'runs'/run.run_id/'event_quality.parquet')
 assert len(pc)==4540 and len(cc)==458 and pc.process_id.is_unique and cc.process_id.is_unique
 assert quality[quality.status.eq('COVERED')].primary_id.is_unique
 summaries.append(dict(run_id=run.run_id,events=len(ev),replacements=replacement_count))
 print('M06 independent audit',run.run_id,flush=True)
transitions=[]
for prefix in ['q1_d0_','q3_d0_','q5_d0_','solo_']:
 for a,b in [('BALANCED_COMPETE','BROAD20_COMPETE'),('BROAD20_COMPETE','ORIGINAL20_COMPETE'),('BALANCED_COMPETE','ORIGINAL20_COMPETE')]:
  for kind in ['parent','child']:
   x=pd.read_parquet(evaluation/'runs'/(prefix+a)/(kind+'_coverage.parquet')).set_index('process_id');y=pd.read_parquet(evaluation/'runs'/(prefix+b)/(kind+'_coverage.parquet')).set_index('process_id');assert set(x.index)==set(y.index)
   for pid,r in x.iterrows():
    s=y.loc[pid];category='BOTH' if r.covered and s.covered else 'COMPETE_ONLY' if r.covered else 'CONTROL_ONLY' if s.covered else 'NEITHER'
    transitions.append(dict(comparison=prefix+a+' minus '+prefix+b,kind=kind,process_id=pid,transition=category,compete_timing=r.timing,control_timing=s.timing,compete_date=r.first_date,control_date=s.first_date,compete_source=r.source,control_source=s.source))
pd.DataFrame(transitions).to_parquet(out/'all_process_transitions.parquet',index=False)
pd.DataFrame(transitions).groupby(['comparison','kind','transition']).size().rename('processes').to_csv(out/'transition_counts.csv')
pd.DataFrame(summaries).to_csv(out/'run_checks.csv',index=False)
inputs=[root/'receipt.json',evaluation/'receipt.json',scorepath,Path(__file__)]
(out/'receipt.json').write_text(json.dumps(dict(result='PASS_CAUSAL_POOL_ACCOUNTING_NOT_BUSINESS_ACCEPTANCE',hash_references=refs,runs=len(inv),inputs={str(p):sha(p) for p in inputs},artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')

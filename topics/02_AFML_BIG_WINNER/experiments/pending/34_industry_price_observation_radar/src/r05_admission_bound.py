"""Prerequisite bound for admission ablation; no predictions are generated."""
import json,math
import networkx as nx
import pandas as pd
from audit_local_inputs import EP,sha
from post_alert_evaluation import registered_rules

out=EP/'outputs/r05_feasibility';out.mkdir(exist_ok=True)
if (out/'result.json').exists():raise FileExistsError('already audited')
gfile=EP/'outputs/r02/common_catalog.parquet';g=pd.read_parquet(gfile,columns=['era','industry_code','date','eligible','r20','delta20'])
g['candidate_id']=g.era+'|'+g.industry_code+'|'+g.date.dt.strftime('%Y-%m-%d')
g['week']=g.era+'|'+g.date.dt.to_period('W-SUN').astype(str)
g['B']=g.eligible&g.delta20.gt(0);g['A']=g.B&g.r20.gt(0)
w=g.groupby('week')[['A','B']].sum();w['common_cap']=w[['A','B']].min(axis=1).clip(upper=5)
efile=EP/'outputs/d02/nearest_valid_edges.parquet';e=pd.read_parquet(efile).merge(g[['candidate_id','A','B']],on='candidate_id',validate='many_to_one')
results={};allocations=[];certificates={}
for arm in ['A','B']:
 for burden in ['independent_cap5','common_static_cap']:
  name=arm+'_'+burden;subset=e[e[arm]];graph=nx.DiGraph();graph.add_nodes_from(['S','T'])
  for r in subset.itertuples():
   cap=5 if burden=='independent_cap5' else int(w.loc[r.week,'common_cap'])
   graph.add_edge('S','W'+r.week,capacity=cap);graph.add_edge('W'+r.week,'C'+r.candidate_id,capacity=1)
   graph.add_edge('C'+r.candidate_id,'P'+r.process_id,capacity=1);graph.add_edge('P'+r.process_id,'T',capacity=1)
  value,flow=nx.maximum_flow(graph,'S','T');cut,(left,right)=nx.minimum_cut(graph,'S','T');assert value==cut
  crossing=[dict(source=u,target=v,capacity=d['capacity']) for u,v,d in graph.edges(data=True) if u in left and v in right]
  assert sum(x['capacity'] for x in crossing)==value
  selected=[]
  for r in subset.itertuples():
   if flow['C'+r.candidate_id].get('P'+r.process_id,0):selected.append(dict(scenario=name,candidate_id=r.candidate_id,process_id=r.process_id,week=r.week))
  f=pd.DataFrame(selected);assert len(f)==value and f.candidate_id.is_unique and f.process_id.is_unique
  counts=f.groupby('week').size();caps=counts.index.map(lambda k:5 if burden=='independent_cap5' else int(w.loc[k,'common_cap']));assert (counts.to_numpy()<=caps).all()
  allocations.extend(selected);certificates[name]=dict(source_side=sorted(left),sink_side=sorted(right),crossing_edges=crossing,capacity=int(cut))
  results[name]=dict(candidate_rows=int(g[arm].sum()),valid_edges=len(subset),reachable_processes=int(subset.process_id.nunique()),maximum_hits=int(value),recall_upper=value/2411)
c=registered_rules();target=math.ceil(2411*c['timely_process_recall_target'])
status='STOP_ADMISSION_DRAFT_BEFORE_SIGNAL_EXPERIMENT' if results['B_independent_cap5']['maximum_hits']<target else 'COMMON_BURDEN_DESIGN_INFEASIBLE' if results['B_common_static_cap']['maximum_hits']<target else 'BOUND_NOT_EXCLUDING_NEXT_COMPARISON'
g.to_parquet(out/'candidate_support.parquet',index=False);w.reset_index().to_parquet(out/'weekly_cap_bounds.parquet',index=False)
pd.DataFrame(allocations).to_parquet(out/'oracle_allocations.parquet',index=False)
(out/'cut_certificates.json').write_text(json.dumps(certificates,indent=2)+'\n')
files=[gfile,efile,EP/'rounds/R05_admission_feasibility_plan.md',EP/'src/r05_admission_bound.py',EP/'configs/evaluation_registration.json']
r=dict(status=status,known_process_denominator=2411,target_hits=target,results=results,rule='Only past-only r20/delta20 determine eligibility; future paths used solely for optimistic bound',inputs={str(f):sha(f) for f in files})
(out/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='inputs'},ensure_ascii=False))

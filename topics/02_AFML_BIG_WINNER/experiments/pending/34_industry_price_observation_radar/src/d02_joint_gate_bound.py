"""Oracle-only necessary feasibility conditions, not attainable predictions."""
import json,math
import numpy as np
import pandas as pd
import networkx as nx
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
from audit_local_inputs import EP,sha
from post_alert_evaluation import registered_rules

out=EP/'outputs/d02';out.mkdir(exist_ok=True)
if (out/'result.json').exists():raise FileExistsError('already evaluated')
pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet';allp=pd.read_parquet(pfile)
p=allp[allp.mature&~allp.left_origin_uncertain].copy();p['year']=p.start_date.dt.year.astype(str)
regimefile=EP/'outputs/r01/process_strata.parquet';regime=pd.read_parquet(regimefile,columns=['process_id','market_regime'])
p=p.merge(regime,on='process_id',validate='one_to_one');pm=p.set_index('process_id')
efile=EP/'outputs/d01/valid_edges.parquet';edges=pd.read_parquet(efile);edges=edges[edges.all_price_eligible].copy()
groups={k:g for k,g in allp.groupby(['era','industry_code'])};nearest={}
for row in edges.itertuples():
 if row.candidate_id not in nearest:
  era,code,_=row.candidate_id.split('|');g=groups[(era,code)];g=g[g.start_day_i.between(row.day-10,row.day+5)].copy()
  g['distance']=(g.start_day_i-row.day).abs();g=g.sort_values(['distance','start_day_i','process_id'])
  nearest[row.candidate_id]=g.iloc[0].process_id
keep=edges.candidate_id.map(nearest).eq(edges.process_id);removed=int((~keep).sum());edges=edges[keep].reset_index(drop=True)
edges.to_parquet(out/'nearest_valid_edges.parquet',index=False)
c=registered_rules();gates=[('ALL','ALL',set(p.process_id),math.ceil(len(p)*c['timely_process_recall_target']))]
for dim,gate in [('kind','type'),('year','year'),('market_regime','regime')]:
 for key,g in p.groupby(dim):
  supported=len(g)>=c[gate+'_minimum_processes'] and key!='UNKNOWN'
  gates.append((dim,str(key),set(g.process_id),math.ceil(len(g)*c[gate+'_recall_floor']) if supported else None))
rows=[]
for dim,key,ids,minimum in gates:
 e=edges[edges.process_id.isin(ids)];graph=nx.DiGraph();graph.add_nodes_from(['S','T'])
 for r in e.itertuples():
  graph.add_edge('S','W'+r.week,capacity=5);graph.add_edge('W'+r.week,'C'+r.candidate_id,capacity=1)
  graph.add_edge('C'+r.candidate_id,'P'+r.process_id,capacity=1);graph.add_edge('P'+r.process_id,'T',capacity=1)
 value,_=nx.maximum_flow(graph,'S','T');cut,_=nx.minimum_cut(graph,'S','T');assert value==cut
 rows.append(dict(dimension=dim,stratum=key,processes=len(ids),required_hits=minimum,maximum_hits=int(value),recall_upper=value/len(ids),individually_impossible=minimum is not None and value<minimum))
# Capacity and uniqueness rows plus joint lower-bound rows.
constraints=[];lower=[];upper=[]
for column,cap in [('week',5),('candidate_id',1),('process_id',1)]:
 for _,g in edges.groupby(column):constraints.append(g.index.to_numpy());lower.append(0);upper.append(cap)
for dim,key,ids,minimum in gates:
 if minimum is not None:constraints.append(edges.index[edges.process_id.isin(ids)].to_numpy());lower.append(minimum);upper.append(np.inf)
m=lil_matrix((len(constraints),len(edges)),dtype=float)
for i,indices in enumerate(constraints):m[i,indices]=1
m=m.tocsr()
sol=milp(-np.ones(len(edges)),integrality=np.ones(len(edges)),bounds=Bounds(0,1),constraints=LinearConstraint(m,np.array(lower),np.array(upper)),options={'time_limit':30})
witness=None
if sol.x is not None:
 x=np.rint(sol.x);assert np.max(np.abs(sol.x-x))<1e-6
 observed=m@x;assert (observed>=np.array(lower)-1e-7).all() and (observed<=np.array(upper)+1e-7).all()
 chosen=edges[x.astype(bool)].copy();chosen.to_parquet(out/'joint_oracle_allocation.parquet',index=False)
 witness=dict(hits=len(chosen),recall=len(chosen)/len(p),all_capacity_and_lower_bounds_verified=True,alert_weeks=int(chosen.week.nunique()))
status='ORACLE_FEASIBLE_NOT_METHOD_VALIDATED' if witness is not None else 'PROVEN_INFEASIBLE_RELAXATION' if sol.status==2 else 'UNRESOLVED_SOLVER'
files=[pfile,regimefile,efile,EP/'rounds/D02_joint_gate_bound_plan.md',EP/'src/d02_joint_gate_bound.py',EP/'configs/evaluation_registration.json']
result=dict(status=status,removed_non_nearest_edges=removed,remaining_edges=len(edges),individual_bounds=rows,solver_status=int(sol.status),solver_message=sol.message,witness=witness,
 relaxations=['uses future success','no operational pool or cooldown','no failure ownership','precision and confidence gates not proven','minimum sample and weeks gates not imposed'],inputs={str(f):sha(f) for f in files})
(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='inputs'},ensure_ascii=False))

"""Independent arithmetic edge check and explicit cut/flow certificates."""
import json
import numpy as np
import pandas as pd
import networkx as nx
from audit_local_inputs import EP,PRIOR,sha

out=EP/'outputs/d01';result=json.loads((out/'result.json').read_text())
a=pd.read_parquet(out/'all_window_pairs.parquet');edges=pd.read_parquet(out/'valid_edges.parquet');alloc=pd.read_parquet(out/'oracle_allocations.parquet')
p=pd.read_parquet(EP/'outputs/r00_metric_denominators/full_process_registry.parquet').set_index('process_id')
raw=pd.read_parquet(PRIOR/'daily_industries.parquet');groups={k:g.set_index('day_i') for k,g in raw.groupby(['era','industry_code'])};asof=int(raw.day_i.max())
for r in a.itertuples():
 proc=p.loc[r.process_id];g=groups[(proc.era,proc.industry_code)];v=g.reindex(range(r.day-70,r.day+66))
 known=asof-r.day>=65 and v.nav.notna().all() and np.isfinite(v.nav).all() and v.nav.gt(0).all() and v.block.notna().all() and v.block.nunique()==1
 expected=False
 if known and proc.end_day_i>=r.day+60:
  path=g.reindex(range(r.day,r.day+61)).nav.to_numpy();future=path[1:]/path[0]-1
  expected=bool(future[:20].max()>=.08 and future[-1]>=.05 and (future>=.02).sum()>=40 and future.min()>=-.05 and (path/np.maximum.accumulate(path)-1).min()>=-.12)
 assert bool(r.valid)==expected,(r.candidate_id,r.process_id)
certificates={}
for scope,stats in result['results'].items():
 g=nx.DiGraph();g.add_nodes_from(['SOURCE','SINK'])
 for r in edges[edges[scope]].itertuples():
  g.add_edge('SOURCE','W|'+r.week,capacity=5);g.add_edge('W|'+r.week,'C|'+r.candidate_id,capacity=1)
  g.add_edge('C|'+r.candidate_id,'P|'+r.process_id,capacity=1);g.add_edge('P|'+r.process_id,'SINK',capacity=1)
 value,(left,right)=nx.minimum_cut(g,'SOURCE','SINK')
 crossing=[dict(source=u,target=v,capacity=d['capacity']) for u,v,d in g.edges(data=True) if u in left and v in right]
 assert sum(x['capacity'] for x in crossing)==stats['max_flow']==value
 chosen=alloc[alloc.scope.eq(scope)]
 assert len(chosen)==value and chosen.candidate_id.is_unique and chosen.process_id.is_unique and chosen.groupby('week').size().max()<=5
 validset=set(zip(edges.loc[edges[scope],'candidate_id'],edges.loc[edges[scope],'process_id']))
 assert set(zip(chosen.candidate_id,chosen.process_id))<=validset
 certificates[scope]=dict(cut_capacity=int(value),source_side=sorted(left),sink_side=sorted(right),crossing_edges=crossing,feasible_allocation_count=len(chosen))
(out/'cut_certificates.json').write_text(json.dumps(certificates,indent=2)+'\n')
(out/'independent_check.json').write_text(json.dumps(dict(all_window_pairs_checked=len(a),valid_edges_checked=len(edges),all_arithmetic_matches=True,cut_certificates_verified=5,script_sha256=sha(EP/'src/check_d01_bound.py')),indent=2)+'\n')
print('all pairs and five explicit cut/flow certificates verified',len(a))

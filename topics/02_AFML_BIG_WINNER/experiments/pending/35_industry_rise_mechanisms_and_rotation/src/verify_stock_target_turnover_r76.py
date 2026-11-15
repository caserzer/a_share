import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r76';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 hold=pd.read_parquet(ROOT/'outputs/r17/holdings.parquet');m=pd.read_parquet(ROOT/'data/l1_assignments.parquet');positions=pd.read_parquet(out/'nominal_positions.parquet');source={(mo,code):g for (mo,code),g in m.groupby(['month','industry_code'])};vectors={};unknowns={};industries={}
 for (method,date),g in hold.groupby(['method','origin']):
  vector={};u=0
  for x in g.to_dict('records'):
   q=source.get((date.to_period('M'),x['industry_code']));ids=set() if q is None else set(q.security_id);den=len(ids)+(int(q.unresolved.max()) if ids else 0)
   if not den:u+=x['weight'];continue
   per=x['weight']/den;u+=x['weight']-per*len(ids)
   for sid in ids:vector[sid]=vector.get(sid,0)+per
  actual=positions[positions.method.eq(method)&positions.origin.eq(date)].set_index('security_id').weight.to_dict();assert vector.keys()==actual.keys() and all(abs(vector[k]-actual[k])<1e-14 for k in vector);vectors[(method,date)]=vector;unknowns[(method,date)]=u;industries[(method,date)]=g.set_index('industry_code').weight.to_dict();assert abs(sum(vector.values())+u-1)<1e-12
 rows=json.loads((out/'transitions.json').read_text())
 for x in rows:
  ka=(x['method'],pd.Timestamp(x['prior_origin']));kb=(x['method'],pd.Timestamp(x['origin']));a=vectors[ka];b=vectors[kb];d=sum(abs(a.get(k,0)-b.get(k,0)) for k in a.keys()|b.keys());u=unknowns[ka]+unknowns[kb];assert abs(d-x['known_stock_distance'])<1e-12;assert abs(max(0,d-u)-x['stock_distance_lower'])<1e-12 and abs(min(2,d+u)-x['stock_distance_upper'])<1e-12
  ia=industries[ka];ib=industries[kb];assert abs(sum(abs(ia.get(k,0)-ib.get(k,0)) for k in ia.keys()|ib.keys())-x['industry_target_distance'])<1e-12
  assert x['new_known_names']==len(b.keys()-a.keys()) and x['removed_known_names']==len(a.keys()-b.keys());assert x['consecutive_month']==(kb[1].to_period('M')==ka[1].to_period('M')+1)
 for x in json.loads((out/'summary.json').read_text()):
  q=[z for z in rows if z['method']==x['method'] and z['consecutive_month']];assert len(q)==x['adjacent_transitions'];assert sum(z['stock_distance_lower']>z['industry_target_distance']+1e-12 for z in q)==x['stock_lower_exceeds_industry_target'];assert sum(z['industry_target_distance']<1e-12 and z['stock_distance_lower']>1e-12 for z in q)==x['unchanged_industry_but_stock_lower_positive']
  for a,b in [('mean_industry_target_distance','industry_target_distance'),('mean_stock_lower','stock_distance_lower'),('mean_stock_upper','stock_distance_upper')]:assert abs(x[a]-sum(z[b] for z in q)/len(q))<1e-12
 js(out/'verification.json',dict(status='PASS',targets=len(vectors),stock_positions=len(positions),transitions=len(rows),source_selection_and_bounds_checked=True,realized_turnover_or_fee_claim=False));print('R76 VERIFIED',len(vectors),len(positions),len(rows))
if __name__=='__main__':run()

import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r76';out.mkdir(exist_ok=True);hp=ROOT/'outputs/r17/holdings.parquet';mp=ROOT/'data/l1_assignments.parquet';hold=pd.read_parquet(hp);members=pd.read_parquet(mp);lookup={k:g for k,g in members.groupby(['month','industry_code'])};positions=[];targets=[];meta={}
 for (method,date),g in hold.groupby(['method','origin']):
  weights={};unknown=0.;missing=[]
  for x in g.itertuples():
   m=lookup.get((date.to_period('M'),x.industry_code));ids=[] if m is None else sorted(m.security_id.unique());u=int(m.unresolved.max()) if ids else 0;den=len(ids)+u
   if not den:unknown+=x.weight;missing.append(x.industry_code);continue
   unknown+=x.weight*u/den
   for sid in ids:weights[sid]=weights.get(sid,0)+x.weight/den
  assert np.isclose(sum(weights.values())+unknown,1)
  for sid,w in sorted(weights.items()):positions.append(dict(method=method,origin=date,security_id=sid,weight=w))
  targets.append(dict(method=method,origin=date,known_weight=sum(weights.values()),unknown_weight=unknown,known_members=len(weights),missing_industries=missing));meta[(method,date)]=(weights,unknown,g.set_index('industry_code').weight.to_dict())
 rows=[]
 for method,g in hold.groupby('method'):
  dates=sorted(g.origin.unique())
  for before,after in zip(dates[:-1],dates[1:]):
   a,u,ia=meta[(method,before)];b,v,ib=meta[(method,after)];distance=sum(abs(b.get(k,0)-a.get(k,0)) for k in set(a)|set(b));industry=sum(abs(ib.get(k,0)-ia.get(k,0)) for k in set(ia)|set(ib));rows.append(dict(method=method,prior_origin=before,origin=after,consecutive_month=after.to_period('M')==before.to_period('M')+1,industry_target_distance=industry,known_stock_distance=distance,stock_distance_lower=max(0.,distance-u-v),stock_distance_upper=min(2.,distance+u+v),prior_unknown=u,current_unknown=v,new_known_names=len(set(b)-set(a)),removed_known_names=len(set(a)-set(b)),interpretation='target-to-target structural diagnostic, not executed turnover'))
 pd.DataFrame(positions).to_parquet(out/'nominal_positions.parquet',index=False);js(out/'target_coverage.json',targets);js(out/'transitions.json',rows);summary=[]
 for method in sorted(hold.method.unique()):
  q=[x for x in rows if x['method']==method and x['consecutive_month']];summary.append(dict(method=method,adjacent_transitions=len(q),gaps=sum(x['method']==method and not x['consecutive_month'] for x in rows),mean_industry_target_distance=float(np.mean([x['industry_target_distance'] for x in q])),mean_stock_lower=float(np.mean([x['stock_distance_lower'] for x in q])),mean_stock_upper=float(np.mean([x['stock_distance_upper'] for x in q])),stock_lower_exceeds_industry_target=sum(x['stock_distance_lower']>x['industry_target_distance']+1e-12 for x in q),unchanged_industry_but_stock_lower_positive=sum(x['industry_target_distance']<1e-12 and x['stock_distance_lower']>1e-12 for x in q)))
 js(out/'summary.json',summary);js(out/'receipt.json',dict(reads={str(p):sha(p) for p in [hp,mp,ROOT/'protocols/r76.json',Path(__file__)]},targets=len(targets),transitions=len(rows),positions=len(positions),r17_unchanged=True));print(pd.DataFrame(summary).to_string(index=False))
if __name__=='__main__':run()

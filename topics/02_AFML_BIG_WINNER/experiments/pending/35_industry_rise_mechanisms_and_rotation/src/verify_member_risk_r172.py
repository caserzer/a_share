"""Rebuild nominal member allocation and target changes from independent joins."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r172';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 m=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=KEY+['month','date','security_id','unresolved']);m=m[m.level.eq('L2')];ml={k:g for k,g in m.groupby(KEY+['month'])}
 pos=pd.read_parquet(out/'nominal_positions.parquet');keys=['variant','era','level','method','origin'];pl={k:g.set_index('security_id').weight for k,g in pos.groupby(keys)};c=pd.read_csv(out/'concentration.csv',parse_dates=['origin','membership_max_date']).set_index(keys);links=pd.read_csv(out/'industry_links.csv',parse_dates=['origin']).set_index(keys+['industry_code']);expected={};industries={};seen=set();seenlinks=set()
 for variant,n in [('top10',169),('top20',137)]:
  h=pd.read_parquet(ROOT/f'outputs/r{n}/evaluation/outputs/r04/holdings.parquet');h=h[h.level.eq('L2')]
  for key,g in h.groupby(['era','level','method','origin']):
   identity=(variant,*key);seen.add(identity);era,level,method,date=key;pieces=[];unknown=0.;count=0;missing=0;maxdate=pd.NaT
   for row in g.itertuples():
    lk=(*identity,row.industry_code);seenlinks.add(lk);link=links.loc[lk];q=ml.get((era,level,row.industry_code,date.to_period('M')))
    if q is None or not q.date.le(date).all():
     unknown+=row.weight;missing+=1;assert link.status=='missing_or_future_snapshot' and np.isclose(link.unknown_weight,row.weight);continue
    ids=set(q.security_id);u=int(q.unresolved.max());den=len(ids)+u;pieces.extend((sid,row.weight/den) for sid in ids);count+=len(ids);unknown+=row.weight*u/den;maxdate=q.date.max() if pd.isna(maxdate) else max(maxdate,q.date.max())
    assert (link.known,link.unresolved,link.denominator)==(len(ids),u,den);assert np.isclose(link.unknown_weight,row.weight*u/den)
   result=pd.DataFrame(pieces,columns=['security_id','weight']).groupby('security_id').weight.sum();actual=pl.get(identity,pd.Series(dtype=float));assert set(result.index)==set(actual.index);assert np.allclose(result.sort_index(),actual.sort_index(),atol=1e-12)
   known=result.sum();largest=result.max() if len(result) else 0.;hhi=(result**2).sum();row=c.loc[identity];assert row.known_stocks==len(result) and row.duplicate_member_entries==count-len(result) and row.missing_industries==missing;assert row.membership_max_date==maxdate or (pd.isna(row.membership_max_date) and pd.isna(maxdate))
   values=dict(known_weight=known,unknown_weight=unknown,known_max_weight=largest,known_hhi=hhi,total_hhi_lower=hhi,total_hhi_upper=min(1,hhi+2*largest*unknown+unknown**2),max_weight_upper=min(1,largest+unknown))
   for name,value in values.items():assert np.isclose(row[name],value,atol=1e-12),(identity,name)
   assert np.isclose(known+unknown,1);expected[identity]=(result.to_dict(),unknown);industries[identity]=dict(zip(g.industry_code,g.weight))
 assert seen==set(c.index) and seenlinks==set(links.index) and set(pl)<=seen
 t=pd.read_csv(out/'target_transitions.csv',parse_dates=['origin','prior_origin']);seentrans=set()
 for row in t.to_dict('records'):
  base=(row['variant'],row['era'],row['level'],row['method']);a,u=expected[(*base,row['prior_origin'])];b,v=expected[(*base,row['origin'])];ia=industries[(*base,row['prior_origin'])];ib=industries[(*base,row['origin'])];seentrans.add((*base,row['prior_origin'],row['origin']))
  dist=sum(abs(b.get(x,0)-a.get(x,0)) for x in set(a)|set(b));idist=sum(abs(ib.get(x,0)-ia.get(x,0)) for x in set(ia)|set(ib))
  for name,value in dict(industry_target_distance=idist,known_stock_distance=dist,stock_distance_lower=max(0,dist-u-v),stock_distance_upper=min(2,dist+u+v),prior_unknown=u,current_unknown=v,new_known_names=len(set(b)-set(a)),removed_known_names=len(set(a)-set(b))).items():assert np.isclose(row[name],value)
  assert row['consecutive_month']==(row['origin'].to_period('M')==row['prior_origin'].to_period('M')+1)
 alltrans=set()
 for base,g in c.reset_index().groupby(keys[:-1]):
  dates=sorted(g.origin);alltrans.update((*base,a,b) for a,b in zip(dates[:-1],dates[1:]))
 assert alltrans==seentrans
 for row in pd.read_csv(out/'summary.csv').to_dict('records'):
  g=c.reset_index();g=g[g.variant.eq(row['variant'])&g.era.eq(row['era'])&g.method.eq(row['method'])];q=t[t.variant.eq(row['variant'])&t.era.eq(row['era'])&t.method.eq(row['method'])&t.consecutive_month]
  values=dict(origins=len(g),mean_known_stocks=g.known_stocks.mean(),max_unknown_weight=g.unknown_weight.max(),mean_known_hhi=g.known_hhi.mean(),mean_known_max_weight=g.known_max_weight.mean(),max_known_max_weight=g.known_max_weight.max(),duplicate_entries=g.duplicate_member_entries.sum(),adjacent_transitions=len(q),mean_industry_distance=q.industry_target_distance.mean(),mean_stock_lower=q.stock_distance_lower.mean(),mean_stock_upper=q.stock_distance_upper.mean(),stock_lower_exceeds_industry=q.stock_distance_lower.gt(q.industry_target_distance+1e-12).sum())
  for name,value in values.items():assert np.isclose(row[name],value,equal_nan=True)
 js(out/'verification.json',dict(status='PASS',origins=len(c),positions=len(pos),industry_links=len(links),transitions=len(t),no_unknown_renormalization=True,no_future_member_snapshot=True,actual_holdings_certified=False,adoption=False))
 print('PASS R172',len(c),len(pos),len(t))
if __name__=='__main__':run()

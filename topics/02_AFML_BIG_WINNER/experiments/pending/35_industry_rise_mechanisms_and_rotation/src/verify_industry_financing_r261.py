from common import *
import pandas as pd
from statistics import median

def run():
 out=ROOT/'outputs/r261';d=pd.read_parquet(out/'industry_pairs.parquet');links=pd.read_parquet(out/'common_company_links.parquet');p=pd.read_parquet(ROOT/'outputs/r260/pairs.parquet');cols=KEY+['month','instrument','security_id'];m=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)])
 member={k:set(zip(g.instrument,g.security_id)) for k,g in m.groupby(KEY+['month'])}
 pair={};validsets={}
 for x in p[p.complete].itertuples():
  k=(x.previous_date,x.current_date);pair[k+(x.instrument,)]=x;validsets.setdefault(k,set()).add((x.instrument,x.security_id_current))
 native=pd.read_parquet(ROOT/'outputs/r143/evaluation/data/r45_financing_intensity.parquet').set_index(KEY+['date'])
 saved={k:set(zip(g.instrument,g.security_id)) for k,g in links.groupby(KEY+['previous_date','current_date'])};qualified=0;maxerr=0.
 for x in d.itertuples():
  key=(x.era,x.level,x.industry_code);dates=(x.previous_date,x.current_date);old=member.get(key+(x.previous_date.to_period('M')-1,),set());new=member.get(key+(x.current_date.to_period('M')-1,),set());expected=old&new&validsets.get(dates,set());actual=saved.get(key+dates,set());assert expected==actual
  assert len(old)==x.members_previous and len(new)==x.members_current and len(old&new)==x.common_members and len(expected)==x.complete_common
  assert len(new-old)==x.entered_members and len(old-new)==x.exited_members
  present=all(key+(date,) in native.index for date in dates);assert present==x.native_rows_present
  for side,date in [('previous',x.previous_date),('current',x.current_date)]:
   if key+(date,) in native.index:
    orig=native.loc[key+(date,)];assert orig.members==getattr(x,'members_'+side) and orig.ready==getattr(x,'native_ready_'+side);assert np.isclose(orig.financing_intensity,getattr(x,'native_'+side),equal_nan=True)
  gate=x.native_rows_present and len(expected)>=5 and len(expected)/len(old)>=.8 and len(expected)/len(new)>=.8
  assert gate==x.qualified
  if not gate:
   assert all(pd.isna(getattr(x,c)) for c in ['f00','f10','f01','f11','balance_component','cap_component','common_change']);continue
  vals=[pair[dates+(instrument,)] for instrument,sid in expected];f={}
  for i in [0,1]:
   for j in [0,1]:
    numerator='previous' if i==0 else 'current';denominator='previous' if j==0 else 'current';f[i,j]=median([getattr(z,'financing_'+numerator)/(getattr(z,'raw_close_'+denominator)*getattr(z,'total_shares_'+denominator)) for z in vals]);assert np.isclose(f[i,j],getattr(x,f'f{i}{j}'),atol=1e-14)
  # Average the two permutation paths separately, not median component summation.
  b1=f[1,0]-f[0,0];b2=f[1,1]-f[0,1];c1=f[0,1]-f[0,0];c2=f[1,1]-f[1,0]
  assert np.isclose((b1+b2)/2,x.balance_component,atol=1e-14) and np.isclose((c1+c2)/2,x.cap_component,atol=1e-14)
  err=abs(x.balance_component+x.cap_component-x.common_change);maxerr=max(maxerr,err);assert err<1e-12;qualified+=1
 summary=pd.read_csv(out/'summary.csv')
 for x in summary.itertuples():
  g=d[d.era.eq(x.era)&d.level.eq(x.level)];v=g[g.qualified];up=v[v.common_change.gt(0)];assert len(g)==x.candidates and len(v)==x.qualified and len(up)==x.up and up.balance_component.le(0).sum()==x.up_balance_nonpositive
 js(out/'independent_verification.json',dict(status='PASS',industry_rows=len(d),company_links=len(links),qualified_median_decompositions=qualified,max_identity_error=maxerr,scope='Exact common members and all gates; independent median endpoint permutations. No causal/forecast certification',adoption=False));print('VERIFIED',len(d),len(links),qualified)
if __name__=='__main__':run()

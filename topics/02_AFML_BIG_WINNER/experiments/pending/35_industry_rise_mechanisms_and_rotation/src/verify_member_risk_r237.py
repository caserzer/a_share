from common import *
import pandas as pd
from regime_member_risk_r237 import IDS

def run():
 out=ROOT/'outputs/r237';l=pd.read_parquet(out/'industry_links.parquet');c=pd.read_csv(out/'concentration.csv',parse_dates=['origin']);pairs=pd.read_csv(out/'paired_overlap.csv',parse_dates=['origin']);keys=['source_round']+IDS;lookup={k:g for k,g in l.groupby(keys)};records={tuple(row[k] for k in keys):row for row in c.to_dict('records')};count=0
 for key,g in lookup.items():
  row=records[key];known=0.;unknown=0.;hhi=0.;largest=0.;stocks=0
  for item in g.itertuples():
   if item.status=='missing_or_future':unknown+=item.weight;continue
   assert item.snapshot_date<=item.origin and item.unresolved_members>=0;unit=item.weight/item.denominator;stocks+=item.known_members;known+=unit*item.known_members;unknown+=unit*item.unresolved_members;hhi+=unit*unit*item.known_members;largest=max(largest,unit)
  for metric,value in [('known_weight',known),('unknown_weight',unknown),('known_hhi',hhi),('known_max_weight',largest),('known_stocks',stocks),('hhi_upper',min(1,hhi+2*largest*unknown+unknown**2))]:assert np.isclose(row[metric],value,atol=1e-11);count+=1
 for row in pairs[pairs.status.eq('paired')].to_dict('records'):
  base=tuple(row[k] for k in ['source_round']+IDS[:4]);a=lookup[base+(row['method'],row['origin'])].set_index('industry_code');b=lookup[base+(row['control'],row['origin'])].set_index('industry_code');v=0.
  for code in set(a.index)&set(b.index):
   aa=a.loc[code];bb=b.loc[code]
   if aa.status=='nominal_snapshot':v+=aa.known_members*min(aa.weight/aa.denominator,bb.weight/bb.denominator)
  assert np.isclose(v,row['known_overlap_lower'],atol=1e-11)
 # Verify each distinct nominal source link against original member snapshots, independently of summary math.
 cols=KEY+['month','date','security_id','unresolved'];m=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)]);source={k:g for k,g in m.groupby(KEY+['month'])};unique=l.drop_duplicates(KEY+['origin']);checked=0
 for row in unique.to_dict('records'):
  g=source.get(tuple(row[k] for k in KEY)+(row['origin'].to_period('M'),));valid=g is not None and g.date.le(row['origin']).all();assert valid==(row['status']=='nominal_snapshot')
  if valid:assert len(g)==row['known_members'] and g.unresolved.iloc[0]==row['unresolved_members']
  checked+=1
 js(out/'independent_verification.json',dict(status='PASS',target_portfolios=len(c),concentration_values=count,paired_dates=int(pairs.status.eq('paired').sum()),unique_member_links=checked,scope='Every target mass/HHI bound and paired known overlap; every unique source member link',code_sha256=sha(__file__)));print(len(c),count,checked)
if __name__=='__main__':run()

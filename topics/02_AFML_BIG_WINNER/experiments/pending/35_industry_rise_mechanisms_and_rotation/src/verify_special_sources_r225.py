from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r225';raw=pd.read_parquet(out/'paired_dates.parquet');checked=0;maximum=0.
 for rnd in [213,218,219]:
  q=raw[raw['round'].eq(str(rnd))]
  if rnd==219:
   source=pd.read_parquet(ROOT/'outputs/r219/paired_dates.parquet');keys=['family','era','level','target_type','horizon','kind','first','second','date','metric']
  else:
   source=pd.read_csv(ROOT/'outputs/r213/intervals.csv',parse_dates=['date']) if rnd==213 else pd.read_parquet(ROOT/'outputs/r218/decisions.parquet')
   if rnd==218:source['family']='battery'
   keys=['family','era','level']+(['industry_code','horizon'] if rnd==218 else [])+['method','variant','date']
  lookup={tuple(str(row[k]) for k in keys):row for row in source.to_dict('records')};assert len(lookup)==len(source)
  for row in q.to_dict('records'):
   row['date']=pd.Timestamp(row['date'])
   if rnd==219:
    row.update(first=row['first_method']+'_'+row['first_variant'],second=row['second_method']+'_'+row['second_variant']);expected=lookup[tuple(str(row[k]) for k in keys)]['delta']
   else:
    legs=[]
    for side in ['first','second']:
     item=dict(row,method=row[side+'_method'],variant=row[side+'_variant']);legs.append(lookup[tuple(str(item[k]) for k in keys)])
    expected=legs[0][row['metric']]-legs[1][row['metric']] if all(x['status']=='valid' for x in legs) else np.nan
   assert np.isclose(row['delta'],expected,atol=1e-12,equal_nan=True)
   if np.isfinite(expected):maximum=max(maximum,abs(row['delta']-expected))
   checked+=1
 js(out/'independent_source_verification.json',dict(status='PASS',rows=checked,max_error=maximum,scope='Each frozen source date and both original decisions; event source already same-event paired in R219',code_sha256=sha(__file__)))
 print(checked,maximum)
if __name__=='__main__':run()

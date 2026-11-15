from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r226';p=pd.read_parquet(out/'paired_dates.parquet');checked=0;maximum=0.
 keys=['source_round','family','era','level','cohort','horizon','objective','cost','date','method','variant']
 for rnd in [220,221]:
  d=pd.read_csv(ROOT/f'outputs/r{rnd}/date_metrics.csv',parse_dates=['date']);lookup={tuple(str(row[k]) for k in keys):row for row in d.to_dict('records')};assert len(lookup)==len(d)
  for row in p[p['round'].eq(str(rnd))].to_dict('records'):
   a,b=row['method'].split('-minus-');v=row['comparison'].split('_')[-1]
   def get(method,variant):
    q=dict(row,method=method,variant=variant);return lookup[tuple(str(q[k]) for k in keys)][row['metric']]
   expected=get(a,v)-get(b,v)
   if row['comparison'].startswith('increment_change_'):expected-=get(a,'base')-get(b,'base')
   assert np.isclose(row['delta'],expected,atol=1e-12,equal_nan=True)
   if np.isfinite(expected):maximum=max(maximum,abs(row['delta']-expected))
   checked+=1
 js(out/'independent_source_verification.json',dict(status='PASS',rows=checked,max_error=maximum,scope='All two-leg mechanism and four-leg increment-change source values',code_sha256=sha(__file__)))
 print(checked,maximum)
if __name__=='__main__':run()

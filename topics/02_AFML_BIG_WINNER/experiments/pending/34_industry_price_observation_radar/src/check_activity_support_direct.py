import sys,json
import numpy as np
import pandas as pd
from pathlib import Path
p=Path(__file__).resolve().parents[1];sys.path.insert(0,str(p/'src'))
from audit_local_inputs import EP,PRIOR,CACHE
r=json.loads((PRIOR/'receipt.json').read_text());paths={Path(x).stem:Path(x) for x in r['price_reads']}
cal=pd.DatetimeIndex(pd.read_parquet(next(x for x in r['inputs'] if x.endswith('/calendar.parquet'))).date).sort_values()
a=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=['era','level','month','industry_code','security_id','unresolved']);a=a[a.level.eq('L3')]
w=pd.read_parquet(EP/'outputs/activity_feasibility/weekly_support.parquet');available=w[w.membership_known&w.price_eligible].sort_values(['date','era','industry_code']);sample=available.iloc[np.linspace(0,len(available)-1,20,dtype=int)];members=0
for row in sample.itertuples():
 cohort=a[a.era.eq(row.era)&a.industry_code.eq(row.industry_code)&a.month.eq(row.date.to_period('M')-1)];counts={f:0 for f in ['volume','money','turnover_rate']};end=cal.get_loc(row.date);days=cal[max(0,end-83):end+1]
 for sid in cohort.security_id:
  x=pd.read_parquet(paths[sid],columns=['date',*counts,*[f+'_conflict' for f in counts]]).set_index('date').reindex(days);members+=1
  for f in counts:
   v=pd.to_numeric(x[f],errors='coerce')
   valid=len(x)==84 and np.isfinite(v).all() and v.ge(0).all() and x[f+'_conflict'].eq(False).all() and v.iloc[:63].sum()>0
   counts[f]+=int(valid)
 for f,n in counts.items():assert n==getattr(row,f+'_known_members'),(row.date,f,n)
(EP/'outputs/activity_feasibility/direct_check.json').write_text(json.dumps({'weeks_checked':20,'member_windows_checked':members,'fields_per_window':3,'all_counts_match':True},indent=2)+'\n')

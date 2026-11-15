"""EPS-only aggregation; preserves R28 coverage without reusing common-profit medians."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r29';out.mkdir(exist_ok=True)
 cols=['month']+KEY+['security_id','instrument']
 paths=[CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'data/r28_common_coverage.parquet',ROOT/'protocols/r29.json',Path(__file__)]
 members=pd.concat([pd.read_parquet(p,columns=cols) for p in paths[:2]],ignore_index=True);members['stock_code']=members.instrument.str[2:]
 reference=pd.read_parquet(paths[2]);receipts=[]
 for variant in ['raw_proxy','share_context_guard']:
  path=ROOT/f'data/r28_{variant}_eps_monthly.parquet';paths.append(path)
  m=pd.read_parquet(path);m=m[m.status.eq('valid')];rows=[]
  for date in sorted(reference.date.unique()):
   date=pd.Timestamp(date);mem=members[members.month.eq(date.to_period('M')-1)]
   for offset in [0,1]:
    company=m[m.date.eq(date)&m.fiscal_year.eq(date.year+offset)].groupby('stock_code').revision.median()
    q=mem.join(company,on='stock_code').groupby(KEY).agg(members=('security_id','size'),known=('revision','count'),covered_member_median=('revision','median')).reset_index()
    q['date']=date;q['fy_offset']=offset;q['coverage']=q.known/q.members;q['eligible']=q.known.ge(5)&q.coverage.ge(.8);rows.append(q)
  cov=pd.concat(rows,ignore_index=True)
  check=cov.merge(reference[reference.variant.eq(variant)],on=KEY+['date','fy_offset'],validate='one_to_one',suffixes=('','_r28'))
  assert len(check)==len(cov) and check.members.eq(check.members_r28).all() and check.known.eq(check.eps_known).all() and check.eligible.eq(check.eps_strict).all()
  dest=ROOT/f'data/r29_{variant}_coverage.parquet';cov.to_parquet(dest,index=False);receipts.append(dict(variant=variant,rows=len(cov),sha256=sha(dest)))
 js(out/'data_receipt.json',dict(reads={str(p):sha(p) for p in paths},outputs=receipts,status='PASS'))
 print(receipts,flush=True)
if __name__=='__main__':run()

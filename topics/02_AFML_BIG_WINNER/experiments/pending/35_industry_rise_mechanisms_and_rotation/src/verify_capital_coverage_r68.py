import re
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r68';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 pairs=json.loads((ROOT/'outputs/r67/same_period_pairs.json').read_text());lookup={};bad=[]
 for x in pairs:
  match=re.fullmatch(r'(\d{6})\.(SH|SZ|BJ)',x['ts_code'])
  if not match:bad.append(x);continue
  lookup[(match[2]+match[1],str(pd.Timestamp(x['end_date']).date()),x['field'])]=x
 quarantine=json.loads((out/'identity_quarantine.json').read_text());assert len(bad)==len(quarantine)==2
 members=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet'),pd.read_parquet(ROOT/'data/l1_assignments.parquet')],ignore_index=True);members=members[members.era.eq('SW2021')&members.month.eq(pd.Period('2026-08'))];group={k:g for k,g in members.groupby(KEY)}
 rows=json.loads((out/'industry_coverage.json').read_text());checked=0
 for x in rows:
  g=group.get(tuple(x[k] for k in KEY),pd.DataFrame());n=len(g);den=n+(int(g.unresolved.max()) if n else 0);known=0;missing=0;cc=0;pc=0
  for instrument in g.instrument if n else []:
   z=lookup.get((instrument,x['period'],x['field']));checked+=1
   if z is None:missing+=1;continue
   known+=int(z['eligible']);cc+=int(z['current_status']=='conflicting_latest_values');pc+=int(z['prior_status']=='conflicting_latest_values')
  assert (n,den,known,missing,cc,pc)==(x['resolved_members'],x['denominator'],x['known'],x['no_pair'],x['current_conflicts'],x['prior_conflicts'])
  assert x['coverage_gate']==bool(known>=5 and den and known/den>=.8)
  assert x['coverage']==(known/den if den else None)
 links=pd.read_parquet(out/'member_links.parquet');assert len(links)==checked==rec['links']
 assert not set(['excess20','excess60','return20','return60']) & set(links.columns)
 for s in json.loads((out/'summary.json').read_text()):
  q=[x for x in rows if all(x[k]==s[k] for k in ['level','period','field'])];assert len(q)==s['industries'] and sum(x['coverage_gate'] for x in q)==s['passing']
 js(out/'verification.json',dict(status='PASS',industry_rows=len(rows),membership_checks=checked,quarantined_pair_rows=len(bad),no_outcomes=True,scope='identity and coverage; not sector mechanism eligibility'))
 print('R68 VERIFIED',len(rows),'coverage rows',checked,'membership checks')
if __name__=='__main__':run()

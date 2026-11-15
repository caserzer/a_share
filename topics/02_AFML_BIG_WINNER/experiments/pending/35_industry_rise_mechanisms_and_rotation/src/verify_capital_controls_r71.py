import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r71';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 d=pd.read_parquet(ROOT/'outputs/r70/member_evidence.parquet');records=d[d.joint_profit_known].to_dict('records');groups={}
 for x in records:groups.setdefault(tuple(x[k] for k in KEY)+ (x['audit_period'],),[]).append(x)
 cov={tuple(x[k] for k in KEY)+ (x['period'],):x for x in json.loads((ROOT/'outputs/r70/industry_evidence.json').read_text())}
 def counts(q,outcome):
  n=[0,0];ev=[0,0]
  for x in q:
   i=0 if x['capex_current']>x['capex_prior'] else 1;n[i]+=1
   if outcome=='both_improve':yes=x['ocf_current']>x['ocf_prior'] and x['profit_current']>x['profit_prior']
   else:yes=x['ocf_current']<x['ocf_prior'] and x['profit_current']<x['profit_prior']
   ev[i]+=int(yes)
  return n,ev
 rows=json.loads((out/'industry_contrasts.json').read_text());assert len(rows)==len(cov)*2
 for x in rows:
  key=tuple(x[k] for k in KEY)+(x['period'],);n,ev=counts(groups.get(key,[]),x['outcome']);assert n==[x['n_up'],x['n_other']] and ev==[x['events_up'],x['events_other']]
  reasons=[]
  if not cov[key]['coverage_gate']:reasons.append('R70_coverage_gate')
  if n[0]<5:reasons.append('increase_group_lt5')
  if n[1]<5:reasons.append('nonincrease_group_lt5')
  assert x['reasons']==reasons and x['eligible']==(not reasons)
  for i,k in enumerate(['rate_up','rate_other']):assert x[k]==(ev[i]/n[i] if n[i] else None)
 summaries=json.loads((out/'summary.json').read_text())
 for s in summaries:
  q=[x for x in records if x['level']==s['level'] and x['audit_period']==s['period']];n,ev=counts(q,s['outcome']);assert n==[s['n_up'],s['n_other']]
  assert ev[0]/n[0]==s['pooled_up'] and ev[1]/n[1]==s['pooled_other']
  e=[x for x in rows if all(x[k]==s[k] for k in ['level','period','outcome']) and x['eligible']];total=sum(x['n_up']+x['n_other'] for x in e);assert total==s['eligible_members'] and len(e)==s['eligible_industries']
  a=sum((x['n_up']+x['n_other'])*x['events_up']/x['n_up'] for x in e)/total;b=sum((x['n_up']+x['n_other'])*x['events_other']/x['n_other'] for x in e)/total
  assert abs(a-s['standardized_up'])<1e-12 and abs(b-s['standardized_other'])<1e-12 and abs(a-b-s['standardized_difference'])<1e-12
  assert abs(sum(x['rate_up']-x['rate_other'] for x in e)/len(e)-s['equal_industry_difference'])<1e-12
  for side in ['up','other']:assert sum(x['events_'+side] for x in e)/sum(x['n_'+side] for x in e)==s['eligible_pooled_'+side]
 js(out/'verification.json',dict(status='PASS',industry_contrasts=len(rows),summary_contrasts=len(summaries),raw_value_signs_and_common_weights_checked=True));print('R71 VERIFIED',len(rows),len(summaries))
if __name__=='__main__':run()

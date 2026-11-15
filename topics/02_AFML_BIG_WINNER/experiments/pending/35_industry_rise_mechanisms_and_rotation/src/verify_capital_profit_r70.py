import zipfile
import pandas as pd
from common import *
from supplement_financials import SOURCE

def run():
 out=ROOT/'outputs/r70';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 lookup={}
 with zipfile.ZipFile(SOURCE/'inputs/provider_responses.zip') as z:
  for r in json.loads((SOURCE/'query_receipts.json').read_text()):
   if r['api']!='income_vip':continue
   payload=z.read(r['archived_response']);assert hashlib.sha256(payload).hexdigest()==r['raw_sha256'];obj=json.loads(payload)
   for i,v in enumerate(obj['data']['items']):lookup[(r['query_id'],i)]=dict(zip(obj['data']['fields'],v))
 raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');raw=raw[raw.api.eq('income_vip')&raw.timing_valid&raw.proxy_available_date.le(pd.Timestamp('2026-09-30'))];groups={k:g for k,g in raw.groupby(['ts_code','end_date'])};facts=json.loads((out/'profit_facts.json').read_text());by={}
 for x in facts:
  q=groups[(x['ts_code'],pd.Timestamp(x['end_date']))];q=q[q.proxy_available_date.eq(q.proxy_available_date.max())];assert {(z['query_id'],z['source_row']) for z in x['source_refs']}==set(zip(q.query_id,q.source_row));values=set();compatible=True
  for ref in x['source_refs']:
   z=lookup[(ref['query_id'],ref['source_row'])];assert z['ts_code']==x['ts_code'];v=z['n_income_attr_p'];values.add(None if v is None else float(v));compatible &= str(z['report_type'])=='1' and str(z['comp_type'])=='1'
  value=next(iter(values)) if len(values)==1 else None;status='conflict' if len(values)>1 else 'missing' if value is None else 'incompatible_statement_type' if not compatible else 'available';assert value==x['value'] and status==x['status'];by[(x['ts_code'],pd.Timestamp(x['end_date']))]=x
 d=pd.read_parquet(out/'member_evidence.parquet');base=pd.read_parquet(ROOT/'outputs/r69/member_evidence.parquet');pd.testing.assert_frame_equal(d[base.columns],base)
 m=pd.read_parquet(ROOT/'data/l1_assignments.parquet');m=m[m.month.eq(pd.Period('2026-08'))].set_index('security_id')
 for x in d.to_dict('records'):
  parent=m.loc[x['security_id'],'industry_code'] if x['security_id'] in m.index else None;scope='identity_unknown' if parent is None else 'financial_excluded' if parent in ['801780.SI','801790.SI'] else 'nonfinancial_accounting';assert scope==x['mechanism_scope']
  issuer=x['instrument'][2:]+'.'+x['instrument'][:2];date=pd.Timestamp(x['audit_period']);a=by.get((issuer,date));b=by.get((issuer,date-pd.DateOffset(years=1)));known=bool(scope=='nonfinancial_accounting' and x['known'] and a and b and a['status']==b['status']=='available');assert known==x['joint_profit_known']
  if known:
   assert x['profit_up']==(a['value']>b['value']) and x['profit_down']==(a['value']<b['value']) and x['profit_flat']==(a['value']==b['value']) and x['profit_negative']==(a['value']<0)
 def verify_counts(x,q):
  valid=q[q.joint_profit_known];up=valid[valid.capex_up.eq(True)];assert len(valid)==x['joint_known'] and len(up)==x['capex_up']
  cats={'both_improve':('ocf_up','profit_up'),'both_decline':('ocf_down','profit_down'),'cash_down_profit_up':('ocf_down','profit_up'),'cash_up_profit_down':('ocf_up','profit_down')}
  for k,(a,b) in cats.items():assert sum(bool(z[a]) and bool(z[b]) for z in up.to_dict('records'))==x[k]
  assert int((up.ocf_flat.eq(True)|up.profit_flat.eq(True)).sum())==x['either_flat'];assert sum(x[k] for k in list(cats)+['either_flat'])==len(up)
 rows=json.loads((out/'industry_evidence.json').read_text())
 for x in rows:
  q=d[d.audit_period.eq(x['period'])]
  for k in KEY:q=q[q[k].eq(x[k])]
  verify_counts(x,q);assert x['coverage_gate']==bool(x['joint_known']>=5 and x['denominator'] and x['joint_known']/x['denominator']>=.8)
 for x in json.loads((out/'summary.json').read_text()):verify_counts(x,d[d.audit_period.eq(x['period'])&d.level.eq(x['level'])])
 js(out/'verification.json',dict(status='PASS',profit_facts=len(facts),member_rows=len(d),industry_rows=len(rows),raw_values_types_mapping_and_partitions_checked=True,no_causal_or_predictive_claim=True));print('R70 VERIFIED',len(facts),len(d),len(rows))
if __name__=='__main__':run()

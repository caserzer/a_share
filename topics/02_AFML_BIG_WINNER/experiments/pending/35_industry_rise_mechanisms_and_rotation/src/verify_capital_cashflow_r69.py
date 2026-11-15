import zipfile
import pandas as pd
from common import *
from supplement_financials import SOURCE

def run():
 out=ROOT/'outputs/r69';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 lookup={}
 with zipfile.ZipFile(SOURCE/'inputs/provider_responses.zip') as z:
  for r in json.loads((SOURCE/'query_receipts.json').read_text()):
   if r['api']!='cashflow_vip':continue
   payload=z.read(r['archived_response']);assert hashlib.sha256(payload).hexdigest()==r['raw_sha256'];obj=json.loads(payload)
   for i,row in enumerate(obj['data']['items']):lookup[(r['query_id'],i)]=dict(zip(obj['data']['fields'],row))
 cash=json.loads((out/'cashflow_facts.json').read_text());by={}
 for x in cash:
  vals=set()
  for ref in x['source_refs']:
   raw=lookup[(ref['query_id'],ref['source_row'])];assert raw['ts_code']==x['ts_code'];v=raw.get('n_cashflow_act');vals.add(None if v is None else float(v))
  expected=next(iter(vals)) if len(vals)==1 else None;assert expected==x['ocf'];assert x['status']==('conflict' if len(vals)>1 else 'missing' if expected is None else 'available');by[(x['ts_code'],pd.Timestamp(x['end_date']))]=x
 base=pd.read_parquet(ROOT/'outputs/r68/member_links.parquet');base=base[base.audit_field.eq('c_pay_acq_const_fiolta')].set_index(KEY+['security_id','audit_period']);d=pd.read_parquet(out/'member_evidence.parquet');assert len(base)==len(d)
 for x in d.to_dict('records'):
  z=base.loc[tuple(x[k] for k in KEY+['security_id','audit_period'])];issuer=x['instrument'][2:]+'.'+x['instrument'][:2];period=pd.Timestamp(x['audit_period']);a=by.get((issuer,period));b=by.get((issuer,period-pd.DateOffset(years=1)));known=bool(z.eligible==True and a and b and a['status']==b['status']=='available');assert known==x['known']
  if known:
   expected={'capex_up':z.current_value>z.prior_value,'ocf_up':a['ocf']>b['ocf'],'ocf_down':a['ocf']<b['ocf'],'ocf_flat':a['ocf']==b['ocf'],'ocf_negative':a['ocf']<0,'cash_spending_gap':a['ocf']<z.current_value}
   for k,v in expected.items():assert x[k]==v
 rows=json.loads((out/'industry_evidence.json').read_text())
 for x in rows:
  g=d[d.audit_period.eq(x['period'])]
  for k in KEY:g=g[g[k].eq(x[k])]
  q=g[g.known];up=q[q.capex_up.eq(True)];assert len(q)==x['joint_known'] and len(up)==x['capex_up']
  for label in ['up','down','flat']:assert int(up['ocf_'+label].eq(True).sum())==x['capex_up_ocf_'+label]
  assert x['coverage_gate']==bool(len(q)>=5 and x['denominator'] and len(q)/x['denominator']>=.8)
  assert int(q.ocf_negative.eq(True).sum())==x['negative_ocf'] and int(q.cash_spending_gap.eq(True).sum())==x['cash_spending_gap']
 for x in json.loads((out/'summary.json').read_text()):
  q=d[d.level.eq(x['level'])&d.audit_period.eq(x['period'])&d.known];u=q[q.capex_up.eq(True)];assert len(q)==x['joint_known'] and len(u)==x['capex_up']
  for label in ['up','down','flat']:assert int(u['ocf_'+label].eq(True).sum())==x['up_ocf_'+label]
 js(out/'verification.json',dict(status='PASS',cashflow_facts=len(cash),member_rows=len(d),industry_rows=len(rows),raw_bytes_and_categories_checked=True,causal_or_predictive_evidence=False));print('R69 VERIFIED',len(cash),len(d),len(rows))
if __name__=='__main__':run()

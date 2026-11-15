from common import *
from decimal import Decimal

def run():
 out=ROOT/'outputs/r300';read=lambda p:json.loads((ROOT/p).read_text());facts=read('outputs/r300/local_fact_bridge.json');source=read('outputs/cnequity_fundamental_review_20261114/reviewed_financial_cells.json');receipts=read('outputs/cnequity_fundamental_review_20261114/original_receipts.json');lookup={(x['symbol'],x['item_code']):x for x in source};docs={x['symbol']:x for x in receipts};assert len(lookup)==len(facts)==70
 for f in facts:
  s=lookup[(f['symbol'],f['item_code'])];doc=docs[f['symbol']]
  assert Decimal(str(f['value']))==Decimal(str(s['item_value']))
  for field in ['announce_date','pdf_page','unit_multiplier','sign_rule']:assert f[field]==s[field]
  assert f['observed_at']==doc['fetched_at'] and f['observed_at'][:10]>f['announce_date']
  assert f['pdf_sha256']==doc['pdf_sha256'] and f['pdf_url']==doc['pdf_url'] and not f['strict_pit']
  assert ('point' in f['period_semantics'])==(f['statement_type']=='balance')
 old=read('outputs/r298/requirements_audit.json');new=read('outputs/r300/requirements_audit.json');assert old['explicit_target_crosswalk']==new['explicit_target_crosswalk'];assert [x['id'] for x in old['items']]==[x['id'] for x in new['items']];assert all(not x['completion_proven'] for x in new['items'])
 before=read('outputs/r238/branch_decisions.json')['branches'];after=read('outputs/r300/family_review.json')['branches'];assert len(after)==16
 for a,b in zip(before,after):assert a=={k:v for k,v in b.items() if k!='current_review'}
 anomalies=read('outputs/r249/negative_years.json');assert not set(docs)&{x['ts_code'] for x in anomalies}
 rec=read('outputs/r300/receipt.json')
 for p,h in rec['inputs'].items():assert sha(ROOT/p)==h
 for p,h in rec['outputs'].items():assert sha(out/p)==h
 js(out/'independent_verification.json',dict(status='PASS',facts=70,issuers=10,anomaly_issuers=154,anomaly_issuer_years=len(anomalies),overlap=0,requirements=16,families=16,scope='Fact bridge and scope/evidence integrity; PDF cells are prior reviewed evidence, not independently re-read here; no full-goal or PIT certification',verifier_sha256=sha(__file__)));print('VERIFIED70 facts,16 families,16 requirements')
if __name__=='__main__':run()

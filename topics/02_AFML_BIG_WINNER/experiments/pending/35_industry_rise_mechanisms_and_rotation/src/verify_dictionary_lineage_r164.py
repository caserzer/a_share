"""Check exact preservation, full definition coverage and all current evidence hashes."""
from common import *

def run():
 out=ROOT/'outputs/r164';base=json.loads((out/'original_dictionary.json').read_text());d=json.loads((out/'factor_dictionary.json').read_text());mapping=json.loads((ROOT/'protocols/r164.json').read_text())['mappings'];assert len(base)==len(d['items'])==28;assert d['original_dictionary_sha256']==sha(out/'original_dictionary.json');required=['theory','formula','direction','applicable_industries','economic_date','publication_date','available_at','frequency','source','historical_revisions','aggregation','missing_rule','failure_condition'];refs=0
 for i,x in enumerate(d['items']):
  assert x['original_definition']==base[i] and x['original_index']==i and x['factor']==base[i]['factor'];assert all(k in x['original_definition'] for k in required);assert x['predictive_adoption'] is False and x['strict_pit_certified'] is False;m=mapping[x['factor']];assert x['current_status']==m['status'] and x['current_interpretation']==m['interpretation'];assert [r['path'] for r in x['current_evidence']]==m['evidence']
  for r in x['current_evidence']:assert sha(ROOT/r['path'])==r['sha256'] and (ROOT/r['path']).stat().st_size==r['bytes'];refs+=1
 pending={x['factor'] for x in d['items'] if x['current_status']=='price_repair_followup_pending'};assert pending=={'dedt_change','margin_delta'}
 js(out/'verification.json',dict(status='PASS',definitions=28,preserved_original_fields=True,source_reference_checks=refs,pending_distinct_financial_factors=sorted(pending),predictive_adoptions=0,verifier_sha256=sha(Path(__file__))))
 print('R164 VERIFIED',28,refs)
if __name__=='__main__':run()

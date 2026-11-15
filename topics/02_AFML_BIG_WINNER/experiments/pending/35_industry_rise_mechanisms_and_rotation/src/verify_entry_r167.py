"""Verify default resolution, historical preservation and unchanged factor definitions."""
from common import *
from research_entry_r139 import load

def run():
 out=ROOT/'outputs/r167';pointer=dict(path='outputs/r167/release.json',sha256=sha(out/'release.json'));m=load(manifest_item=pointer);assert m['revision']=='R167';p=json.loads((ROOT/'protocols/r167.json').read_text());old=load(manifest_item=m['previous_release'])
 assert set(m['routes'])==set(old['routes'])|set(p['routes'])|{'versioned_factor_dictionary'}
 for k,v in old['routes'].items():assert m['routes'][k]==v
 for k in set(m['routes'])-set(old['routes']):
  item=load(key=k,manifest_item=pointer);assert not item['predictive_adoption'] and not item['strict_pit'] and not item['production_enabled']
  if k in p['routes']:assert (item['path'],item['verification']['path'],item['interpretation'])==tuple(p['routes'][k])
 d=json.loads((out/'factor_dictionary.json').read_text());before=json.loads((ROOT/'outputs/r164/factor_dictionary.json').read_text());assert len(d['items'])==28
 for a,b in zip(d['items'],before['items']):
  assert a['original_definition']==b['original_definition']
  if a['factor'] in p['dictionary_update']:assert a['current_status']=='price_repair_verified_short_sample'
  else:assert a==b
  for ref in a['current_evidence']:assert sha(ROOT/ref['path'])==ref['sha256'] and (ROOT/ref['path']).stat().st_size==ref['bytes']
 assert m['unreviewed_legacy_routes']==old['unreviewed_legacy_routes']
 for n in [139,148,157]:
  rel=f'outputs/r{n}/release.json';assert load(manifest_item=dict(path=rel,sha256=sha(ROOT/rel)))['revision']==f'R{n}'
 js(out/'verification.json',dict(status='PASS',routes=len(m['routes']),original_definitions_preserved=28,financial_statuses_updated=2,legacy_source_slots_preserved=len(m['unreviewed_legacy_routes']),historical_entries=[139,148,157],predictive_adoptions=0))
 print('R167 VERIFIED',len(m['routes']))
if __name__=='__main__':run()

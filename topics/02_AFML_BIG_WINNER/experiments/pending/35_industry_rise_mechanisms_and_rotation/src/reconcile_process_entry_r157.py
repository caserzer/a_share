"""Expose repaired process evidence without promoting predictive adoption."""
from common import *
from research_entry_r139 import load,ENTRY

def run():
 out=ROOT/'outputs/r157';protocol=json.loads((ROOT/'protocols/r157.json').read_text());prior=json.loads((out/'prior_current_sources.json').read_text());seal=json.loads((out/'prior_progress_manifest.json').read_text());hashes={x['path']:x['sha256'] for x in seal['files']}
 base_item=dict(path='outputs/r148/release.json',sha256=sha(ROOT/'outputs/r148/release.json'));base=load(manifest_item=base_item);routes=dict(base['routes']);assert routes==json.loads((out/'prior_verified_routes.json').read_text())
 for item in routes.values():
  for part in [item,item['verification']]:assert part['sha256']==hashes[part['path']],part['path']
 for key,(path,proof,boundary) in protocol['routes'].items():
  assert key not in routes
  for p in [path,proof]:assert sha(ROOT/p)==hashes[p],p
  assert json.loads((ROOT/proof).read_text())['status']=='PASS'
  routes[key]=dict(path=path,sha256=hashes[path],verification=dict(path=proof,sha256=hashes[proof]),scope='verified repaired historical evidence',interpretation=boundary,predictive_adoption=False,strict_pit=False,production_enabled=False)
 release=dict(base,revision='R157',routes=routes,previous_release=base_item,source_snapshot_sha256=sha(out/'prior_progress_manifest.json'),next='Audit remaining original-only evidence and update full requirement coverage; preserve negative branches and missing PIT or prospective evidence.')
 js(out/'release.json',release);cur=json.loads((ROOT/'outputs/current_sources.json').read_text());assert set(cur['selected'])==set(prior['selected'])
 for key,item in prior['selected'].items():
  if key!=ENTRY:assert cur['selected'][key]['path']==item['path'] and cur['selected'][key]['sha256']==sha(ROOT/item['path'])
 cur['selected'][ENTRY]=dict(path='outputs/r157/release.json',sha256=sha(out/'release.json'));js(ROOT/'outputs/current_sources.json',cur);load()
 js(out/'receipt.json',dict(status='PASS',routes=len(routes),added_evidence_routes=len(protocol['routes']),legacy_slots_preserved=len(cur['selected'])-1,protocol_sha256=sha(ROOT/'protocols/r157.json'),code_sha256=sha(Path(__file__)),predictive_adoptions=0))
 print('R157 ENTRY',len(routes))
if __name__=='__main__':run()

"""Add only R147-sealed verified branch artifacts to the corrected research release."""
from common import *
from research_entry_r139 import ENTRY,load

def run():
 out=ROOT/'outputs/r148';protocol=json.loads((ROOT/'protocols/r148.json').read_text());seal=json.loads((out/'prior_progress_manifest.json').read_text());hashes={x['path']:x['sha256'] for x in seal['files']};prior=json.loads((out/'prior_current_sources.json').read_text());base=json.loads((ROOT/'outputs/r139/release.json').read_text());routes=dict(base['routes']);cur=json.loads((ROOT/'outputs/current_sources.json').read_text());legacy={k:v for k,v in cur['selected'].items() if k!=ENTRY}
 for k,v in prior['selected'].items():
  if k!=ENTRY:assert legacy[k]['path']==v['path'] and legacy[k]['sha256']==sha(ROOT/v['path']),k
 for name,(path,proof) in protocol['routes'].items():
  for p in [path,proof]:assert sha(ROOT/p)==hashes[p],p
  assert json.loads((ROOT/proof).read_text())['status']=='PASS'
  routes[name]=dict(path=path,sha256=hashes[path],verification=dict(path=proof,sha256=hashes[proof]),supersedes=base['routes'].get(name,prior['selected'].get(name)),scope='verified repaired historical evidence; adoption is not predictive acceptance')
 untouched={k:dict(**v,review_status='retained_original_route_not_adopted_in_corrected_entry') for k,v in legacy.items() if k not in routes}
 release=dict(revision='R148',quality='Historical-proxy',overall_status='active_not_complete',monitor_dates=base['monitor_dates'],routes=routes,unreviewed_legacy_routes=untouched,legacy_registry_refreshes=base['legacy_registry_refreshes'],source_snapshot_sha256=sha(out/'prior_progress_manifest.json'),previous_release=dict(path='outputs/r139/release.json',sha256=sha(ROOT/'outputs/r139/release.json')),next='Audit remaining original-only evidence and new local data availability against the five questions and three tasks; preserve stopped branches and do not search thresholds without grounds.')
 js(out/'release.json',release);cur['selected'][ENTRY]=dict(path='outputs/r148/release.json',sha256=sha(out/'release.json'));js(ROOT/'outputs/current_sources.json',cur);load()
 js(out/'receipt.json',dict(status='PASS',routes=len(routes),new_or_replaced_routes=len(protocol['routes']),preserved_legacy_slots=len(legacy),original_only_routes=len(untouched),release_sha256=sha(out/'release.json'),protocol_sha256=sha(ROOT/'protocols/r148.json'),code_sha256=sha(__file__),resolver_sha256=sha(ROOT/'src/research_entry_r139.py')))
 print('R148 ENTRY',len(routes),len(untouched))
if __name__=='__main__':run()

"""Versioned current entry and financial lineage refresh, without model adoption."""
from common import *
from research_entry_r139 import load,ENTRY

def run():
 out=ROOT/'outputs/r167';protocol=json.loads((ROOT/'protocols/r167.json').read_text())
 hashes={x['path']:x['sha256'] for x in json.loads((out/'prior_progress_manifest.json').read_text())['files']}
 base=load(manifest_item=dict(path='outputs/r157/release.json',sha256=sha(ROOT/'outputs/r157/release.json')))
 prior=json.loads((out/'prior_release.json').read_text());assert base['routes']==prior['routes']
 for item in base['routes'].values():
  for x in [item,item['verification']]:assert sha(ROOT/x['path'])==hashes[x['path']]
 dictionary=json.loads((ROOT/'outputs/r164/factor_dictionary.json').read_text());dictionary['revision']='R167'
 for item in dictionary['items']:
  if item['factor'] in protocol['dictionary_update']:
   item['current_status']='price_repair_verified_short_sample'
   item['current_interpretation']='R165重跑R03/R07结果不变；短样本和真实归档时钟缺口保留，未采用。'
   item['current_evidence']=[dict(path=p,sha256=sha(ROOT/p),bytes=(ROOT/p).stat().st_size) for p in ['outputs/r165/comparison.json','outputs/r165/verification.json']]
 js(out/'factor_dictionary.json',dictionary)
 original=json.loads((ROOT/'outputs/r164/factor_dictionary.json').read_text())
 assert [x['original_definition'] for x in dictionary['items']]==[x['original_definition'] for x in original['items']]
 for item in dictionary['items']:
  for x in item['current_evidence']:assert sha(ROOT/x['path'])==x['sha256']
 js(out/'dictionary_verification.json',dict(status='PASS',definitions=28,original_definitions_preserved=True,updated_factors=protocol['dictionary_update'],predictive_adoptions=0))
 routes=dict(base['routes'])
 for key,(path,proof,boundary) in protocol['routes'].items():
  assert key not in routes
  for p in [path,proof]:assert sha(ROOT/p)==hashes[p],p
  assert json.loads((ROOT/proof).read_text())['status']=='PASS'
  routes[key]=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),scope='verified historical evidence',interpretation=boundary,predictive_adoption=False,strict_pit=False,production_enabled=False)
 path='outputs/r167/factor_dictionary.json';proof='outputs/r167/dictionary_verification.json'
 routes['versioned_factor_dictionary']=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),scope='28 original definitions with current evidence',interpretation='financial_repair_closed_predictive_evidence_insufficient',predictive_adoption=False,strict_pit=False,production_enabled=False)
 release=dict(base,revision='R167',routes=routes,previous_release=dict(path='outputs/r157/release.json',sha256=sha(ROOT/'outputs/r157/release.json')),source_snapshot_sha256=sha(out/'prior_progress_manifest.json'),next='Audit full requirements against this unified evidence; distinguish completed experiments from unresolved data and prospective validation.')
 js(out/'release.json',release);cur=json.loads((ROOT/'outputs/current_sources.json').read_text());cur['selected'][ENTRY]=dict(path='outputs/r167/release.json',sha256=sha(out/'release.json'));js(ROOT/'outputs/current_sources.json',cur);load()
 js(out/'receipt.json',dict(status='PASS',routes=len(routes),new_routes=len(routes)-len(base['routes']),prior_routes_preserved=len(base['routes']),predictive_adoptions=0,protocol_sha256=sha(ROOT/'protocols/r167.json')))
 print('R167 ENTRY',len(routes))
if __name__=='__main__':run()

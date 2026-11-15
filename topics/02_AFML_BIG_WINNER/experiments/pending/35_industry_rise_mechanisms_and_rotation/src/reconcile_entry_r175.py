"""Current evidence release with refreshed, explicitly incomplete requirements."""
from common import *
from research_entry_r139 import load,ENTRY

def run():
 out=ROOT/'outputs/r175';protocol=json.loads((ROOT/'protocols/r175.json').read_text());prior=json.loads((out/'prior_release.json').read_text());hashes={x['path']:x['sha256'] for x in json.loads((out/'prior_progress_manifest.json').read_text())['files']};base=load(manifest_item=dict(path='outputs/r167/release.json',sha256=sha(ROOT/'outputs/r167/release.json')));assert base['routes']==prior['routes'];routes=dict(base['routes'])
 for v in routes.values():
  for x in [v,v['verification']]:assert sha(ROOT/x['path'])==hashes[x['path']]
 for key,(path,proof,boundary) in protocol['routes'].items():
  assert key not in routes
  for p in [path,proof]:assert sha(ROOT/p)==hashes[p]
  assert json.loads((ROOT/proof).read_text())['status']=='PASS'
  routes[key]=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),scope='verified historical evidence',interpretation=boundary,predictive_adoption=False,strict_pit=False,production_enabled=False)
 audit=json.loads((ROOT/'outputs/r168/requirements_audit.json').read_text());audit['revision']='R175';audit['scope']='Current requirement crosswalk; all completion claims remain unproven'
 for item in audit['items']:
  if item['id'] in protocol['requirement_updates']:
   change=protocol['requirement_updates'][item['id']];item.update({k:v for k,v in change.items() if k!='routes'});item['evidence']=[dict(route=k,path=routes[k]['path'],sha256=routes[k]['sha256']) for k in change['routes']]
  for ref in item['evidence']:assert sha(ROOT/ref['path'])==ref['sha256']
 audit['next_local']=[dict(priority=1,task='Exact failed stock/date/field and bounded local alternative-source audit',basis='R174 retains every failed stock interval but source restoration needs exact missing dates and field causes',inputs=['outputs/r174/stock_interval_audit.parquet','outputs/r174/receipt.json'],boundary='Read existing local sources only; no external procurement/download or permissive missing-value substitution')];audit['full_completion_proven']=False
 js(out/'requirements_audit.json',audit);js(out/'audit_verification.json',dict(status='PASS',requirements=len(audit['items']),updated_requirements=len(protocol['requirement_updates']),completion_proven=0,scope='evidence lineage and refreshed interpretation; not scientific validation by metadata'))
 path='outputs/r175/requirements_audit.json';proof='outputs/r175/audit_verification.json';routes['current_requirements_audit']=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),scope='current incomplete requirement status',interpretation='experiments_completed_do_not_certify_capability',predictive_adoption=False,strict_pit=False,production_enabled=False)
 release=dict(base,revision='R175',routes=routes,previous_release=dict(path='outputs/r167/release.json',sha256=sha(ROOT/'outputs/r167/release.json')),source_snapshot_sha256=sha(out/'prior_progress_manifest.json'),next='Audit precise failed stock dates/fields and bounded local source alternatives; do not repeat frozen experiments or infer trading permissions.')
 js(out/'release.json',release);cur=json.loads((ROOT/'outputs/current_sources.json').read_text());cur['selected'][ENTRY]=dict(path='outputs/r175/release.json',sha256=sha(out/'release.json'));js(ROOT/'outputs/current_sources.json',cur);load();js(out/'receipt.json',dict(status='PASS',routes=len(routes),prior_routes=len(base['routes']),new_routes=len(routes)-len(base['routes']),predictive_adoptions=0,protocol_sha256=sha(ROOT/'protocols/r175.json')));print('R175 ENTRY',len(routes))
if __name__=='__main__':run()

"""Verify adopted paths, sealed lineage and preserved legacy routes."""
from common import *
from research_entry_r139 import load as load_checked,ENTRY

def load(key=None):
 return load_checked(key=key,manifest_item=dict(path='outputs/r139/release.json',sha256=sha(ROOT/'outputs/r139/release.json')))
from reconcile_repair_r139 import ROUTES

def run():
 out=ROOT/'outputs/r139';m=load();prior=json.loads((out/'prior_current_sources.json').read_text());cur=json.loads((ROOT/'outputs/current_sources.json').read_text());assert set(cur['selected'])==set(prior['selected'])|{ENTRY}
 for k,v in prior['selected'].items():
  assert cur['selected'][k]['path']==v['path'],k
  assert cur['selected'][k]['sha256']==sha(ROOT/v['path']),k
  if cur['selected'][k]!=v:assert m['legacy_registry_refreshes'][k]==dict(before=v,after=cur['selected'][k])
 assert set(m['routes'])==set(ROUTES);seal=json.loads((out/'prior_progress_manifest.json').read_text());hashes={x['path']:x['sha256'] for x in seal['files']}
 for k,(path,proof) in ROUTES.items():
  x=load(key=k);assert x['path']==path and x['sha256']==hashes[path];assert x['verification']==dict(path=proof,sha256=hashes[proof]);assert x['supersedes']==prior['selected'].get(k)
 expected=set(prior['selected'])-set(ROUTES);assert set(m['unreviewed_legacy_routes'])==expected
 for k in expected:
  x=m['unreviewed_legacy_routes'][k];assert x['path']==prior['selected'][k]['path'] and x['sha256']==cur['selected'][k]['sha256'];assert x['review_status']=='retained_historical_not_revalidated_by_basket_repair'
 assert load(key='integrated_historical_task_evidence')['path']=='outputs/r138/task_evidence.parquet';assert load(key='three_task_price_models')['path']=='outputs/r131/model_parameters.json'
 req=json.loads((ROOT/'outputs/r124/requirements_evidence.json').read_text());assert len(req['items'])==16 and not any(x['completion_proven'] for x in req['items'])
 js(out/'verification.json',dict(status='PASS',adopted_routes=len(ROUTES),preserved_legacy_routes=len(prior['selected']),unreviewed_routes=len(expected),overall_requirements_unproved=16,release_sha256=sha(out/'release.json'),verifier_sha256=sha(__file__)))
 print('ENTRY VERIFIED',len(ROUTES),len(expected),flush=True)
if __name__=='__main__':run()

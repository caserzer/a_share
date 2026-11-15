from common import *
from research_entry_r139 import load,ENTRY

def run():
 out=ROOT/'outputs/r148';manifest_item=dict(path='outputs/r148/release.json',sha256=sha(out/'release.json'));m=load(manifest_item=manifest_item);assert m['revision']=='R148';protocol=json.loads((ROOT/'protocols/r148.json').read_text());old=json.loads((ROOT/'outputs/r139/release.json').read_text());prior=json.loads((out/'prior_current_sources.json').read_text());current=json.loads((ROOT/'outputs/current_sources.json').read_text());seal=json.loads((out/'prior_progress_manifest.json').read_text());hashes={x['path']:x['sha256'] for x in seal['files']}
 assert set(m['routes'])==set(old['routes'])|set(protocol['routes']);assert set(current['selected'])==set(prior['selected'])
 for k,v in prior['selected'].items():
  if k!=ENTRY:assert current['selected'][k]['path']==v['path'] and current['selected'][k]['sha256']==sha(ROOT/v['path'])
 for name,item in m['routes'].items():
  if name in protocol['routes']:
   path,proof=protocol['routes'][name];assert item['path']==path and item['sha256']==hashes[path];assert item['verification']==dict(path=proof,sha256=hashes[proof]);assert load(key=name,manifest_item=manifest_item)==dict(item,quality='Historical-proxy',overall_status='active_not_complete')
  else:assert item==old['routes'][name]
 original=set(current['selected'])-{ENTRY}-set(m['routes']);assert set(m['unreviewed_legacy_routes'])==original
 assert load(key='integrated_historical_task_evidence',manifest_item=manifest_item)['path']=='outputs/r147/task_evidence.parquet'
 historical=load(manifest_item=dict(path='outputs/r139/release.json',sha256=sha(ROOT/'outputs/r139/release.json')));assert historical['routes']['integrated_historical_task_evidence']['path']=='outputs/r138/task_evidence.parquet'
 req=json.loads((ROOT/'outputs/r124/requirements_evidence.json').read_text());assert len(req['items'])==16 and not any(x['completion_proven'] for x in req['items'])
 js(out/'verification.json',dict(status='PASS',routes=len(m['routes']),original_slots_preserved=len(prior['selected'])-1,original_only_routes=len(original),monitor='outputs/r147/task_evidence.parquet',historical_entry_resolves=True,overall_requirements_unproved=16,release_sha256=sha(out/'release.json'),verifier_sha256=sha(__file__)))
 print('VERIFIED R148',len(m['routes']),len(original))
if __name__=='__main__':run()

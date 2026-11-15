from common import *
def run():
 out=ROOT/'outputs/r100';r=json.loads((out/'receipt.json').read_text());assert sha(r['objective_path'])==r['objective_sha256'] and sha(ROOT/'outputs/r92/requirements_evidence.json')==r['prior_requirements_sha256'] and sha(ROOT/'src/audit_stage_r100.py')==r['code_sha256'];a=json.loads((out/'requirements_evidence.json').read_text());prior=json.loads((ROOT/'outputs/r92/requirements_evidence.json').read_text());assert [x['requirement'] for x in a['items']]==[x['requirement'] for x in prior['items']] and len(a['items'])==16 and not any(x['completion_proven'] for x in a['items']);assert a['overall_status']=='active_not_complete'
 for x in a['items']:
  assert x['unresolved']
  for e in x['evidence']:assert e['exists'] and sha(ROOT/e['path'])==e['sha256']
 gap=json.loads((out/'executable_gap.json').read_text());assert gap['status']=='executable_local_engineering_gap' and gap['next_action'] and gap['not_proven_by_this_action']
 for e in gap['owning_evidence']:assert sha(ROOT/e['path'])==e['sha256']
 full=json.loads((out/'full_verify_receipt.json').read_text());assert full['action']=='verify' and full['status']=='PASS' and full['entry_sha256']==sha(out/'verified_run_local.py');assert 'verify_calibration_uncertainty_r99' in full['scripts'] and 'verify_calibrated_alerts_r98' in full['scripts'];assert '66 passed' in (out/'test_receipt.txt').read_text()
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())['selected']['latest_stage_requirements_audit'];assert current['path'] in ['outputs/r100/requirements_evidence.json','outputs/r107/requirements_evidence.json','outputs/r112/requirements_evidence.json','outputs/r119/requirements_evidence.json','outputs/r124/requirements_evidence.json'];assert current['sha256']==sha(ROOT/current['path'])
 js(out/'verification.json',dict(status='PASS',requirements=16,completion_proven=0,full_verify_scripts=len(full['scripts']),full_verify_entry_sha256=full['entry_sha256'],scope='original objective and prior requirement preservation, actual evidence hashes, inspected owning code, archived full verification and test receipt; not predictive or overall completion proof',verifier_sha256=sha(Path(__file__))));print('R100 VERIFIED:16 incomplete requirements; full suite archived')
if __name__=='__main__':run()

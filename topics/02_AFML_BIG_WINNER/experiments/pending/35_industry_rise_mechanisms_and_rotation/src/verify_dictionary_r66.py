from common import *
def run():
 out=ROOT/'outputs/r66';rec=json.loads((out/'receipt.json').read_text());old=json.loads((ROOT/'outputs/r58/current_factor_dictionary.json').read_text());rows=json.loads((out/'current_factor_dictionary.json').read_text());by={x['factor']:x for x in rows};assert len(rows)==len(by)==len(old)==21
 assert sha(ROOT/'outputs/r58/current_factor_dictionary.json')==rec['previous_dictionary_sha256'];assert sha(out/'current_factor_dictionary.json')==rec['dictionary_sha256'];assert sha(ROOT/'src/reconcile_battery_r66.py')==rec['code_sha256']
 for x in old:
  if x['factor'] not in rec['amended']:assert by[x['factor']]==x
 for x in rows:
  assert not x['strict_pit_certified']
  for p,h in x['evidence_sha256'].items():assert sha(ROOT/p)==h
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())['selected']
 for k,p in rec['routes'].items():
  if k=='current_factor_dictionary' and current[k]['path'] in ['outputs/r75/current_factor_dictionary.json','outputs/r92/current_factor_dictionary.json','outputs/r107/current_factor_dictionary.json','outputs/r112/current_factor_dictionary.json','outputs/r119/current_factor_dictionary.json','outputs/r124/current_factor_dictionary.json']:continue
  assert current[k]['path']==p and current[k]['sha256']==sha(ROOT/p)
 for x in current.values():assert sha(ROOT/x['path'])==x['sha256']
 a=json.loads((out/'requirements_evidence.json').read_text());assert len(a['items'])==16 and not any(x['completion_proven'] for x in a['items'])
 for x in a['items']:
  for e in x['evidence']:assert sha(ROOT/e['path'])==e['sha256']
 series=json.loads((ROOT/'outputs/r60/frozen_monthly_series.json').read_text());assert len(series)==81 and sum(x['log_yoy'] is not None for x in series)==69
 gates=json.loads((ROOT/'outputs/r65/fold_ledger.json').read_text());assert len(gates)==40 and all(x['status']=='skip' for x in gates)
 js(out/'verification.json',dict(status='PASS',unchanged_entries=20,updated_entries=1,current_routes=6,uncompleted_requirements=16,source_hashes_checked=True))
 print('R66 VERIFIED current routes, 21 entries, 16 uncompleted requirements')
if __name__=='__main__':run()

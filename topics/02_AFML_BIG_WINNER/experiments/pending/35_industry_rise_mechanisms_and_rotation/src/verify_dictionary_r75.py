from common import *
def run():
 out=ROOT/'outputs/r75';rec=json.loads((out/'receipt.json').read_text());rows=json.loads((out/'current_factor_dictionary.json').read_text());old=json.loads((ROOT/'outputs/r66/current_factor_dictionary.json').read_text());assert rows[:21]==old and len(rows)==24 and len({x['factor'] for x in rows})==24;assert sha(ROOT/'outputs/r66/current_factor_dictionary.json')==rec['previous_dictionary_sha256'] and sha(out/'current_factor_dictionary.json')==rec['dictionary_sha256'];assert sha(ROOT/'src/reconcile_accounting_r75.py')==rec['code_sha256']
 for x in rows:
  assert not x['strict_pit_certified']
  for k in ['theory','formula','direction','applicable_industries','economic_date','publication_date','available_at','frequency','source','historical_revisions','aggregation','missing_rule','failure_condition']:assert x[k]
  for p,h in x['evidence_sha256'].items():assert sha(ROOT/p)==h
 for x in rows[21:]:assert x['implemented']=='historical_accounting_evidence_not_predictive_factor'
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())['selected']
 for k,p in rec['routes'].items():
  if k in ['current_factor_dictionary','current_requirements_evidence'] and current[k]['path'] in [p.replace('/r75/','/r92/'),p.replace('/r75/','/r107/'),p.replace('/r75/','/r112/'),p.replace('/r75/','/r119/'),p.replace('/r75/','/r124/')]:continue
  assert current[k]['path']==p and current[k]['sha256']==sha(ROOT/p)
 for x in current.values():assert sha(ROOT/x['path'])==x['sha256']
 a=json.loads((out/'requirements_evidence.json').read_text());assert len(a['items'])==16 and not any(x['completion_proven'] for x in a['items'])
 for x in a['items']:
  for e in x['evidence']:assert sha(ROOT/e['path'])==e['sha256']
 js(out/'verification.json',dict(status='PASS',unchanged_entries=21,new_accounting_entries=3,requirements_uncompleted=16,active_routes=len(rec['routes'])));print('R75 VERIFIED24 entries and16 uncompleted requirements')
if __name__=='__main__':run()

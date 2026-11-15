from common import *
def run():
 out=ROOT/'outputs/r58';rec=json.loads((out/'receipt.json').read_text());rows=json.loads((out/'current_factor_dictionary.json').read_text());old=json.loads((ROOT/'outputs/r49/current_factor_dictionary.json').read_text());by={x['factor']:x for x in rows}
 assert len(rows)==len(by)==21 and len(old)==19
 assert sha(out/'current_factor_dictionary.json')==rec['dictionary_sha256'] and sha(ROOT/'outputs/r49/current_factor_dictionary.json')==rec['previous_sha256']
 for x in old:
  if x['factor'] not in rec['amended_prior_factors']:assert x==by[x['factor']]
 for x in rows:
  assert not x['strict_pit_certified']
  for key in ['theory','formula','direction','applicable_industries','economic_date','publication_date','available_at','frequency','source','historical_revisions','aggregation','missing_rule','failure_condition']:assert x[key]
  for path,h in x['evidence_sha256'].items():assert sha(ROOT/path)==h
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());assert current['selected']['current_factor_dictionary']['path'] in ['outputs/r58/current_factor_dictionary.json','outputs/r66/current_factor_dictionary.json','outputs/r75/current_factor_dictionary.json','outputs/r92/current_factor_dictionary.json','outputs/r107/current_factor_dictionary.json','outputs/r112/current_factor_dictionary.json','outputs/r119/current_factor_dictionary.json','outputs/r124/current_factor_dictionary.json']
 for x in current['selected'].values():assert sha(ROOT/x['path'])==x['sha256']
 audit=json.loads((out/'requirements_evidence.json').read_text());assert len(audit['items'])==16 and all(not x['completion_proven'] for x in audit['items'])
 for x in audit['items']:
  for ref in x['evidence']:assert sha(ROOT/ref['path'])==ref['sha256']
 js(out/'verification.json',dict(status='PASS',factors=21,prior_unchanged=16,prior_explicitly_amended=3,new_controls=2,requirements_uncompleted=16,selected_hashes_checked=len(current['selected'])))
 print('R58 VERIFIED 21 factors and source routing')
if __name__=='__main__':run()

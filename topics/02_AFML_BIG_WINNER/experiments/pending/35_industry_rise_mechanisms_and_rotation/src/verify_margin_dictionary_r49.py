from common import *

def run():
 out=ROOT/'outputs/r49';rows=json.loads((out/'current_factor_dictionary.json').read_text());old=json.loads((ROOT/'outputs/r43/current_factor_dictionary.json').read_text());assert rows[:-1]==old and len(rows)==19
 for row in rows:
  assert row['strict_pit_certified'] is False
  for ref,h in row['evidence_sha256'].items():assert sha(ROOT/ref)==h
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());assert current['selected']['current_factor_dictionary']['path'] in ['outputs/r49/current_factor_dictionary.json','outputs/r58/current_factor_dictionary.json','outputs/r66/current_factor_dictionary.json','outputs/r75/current_factor_dictionary.json','outputs/r92/current_factor_dictionary.json','outputs/r107/current_factor_dictionary.json','outputs/r112/current_factor_dictionary.json','outputs/r119/current_factor_dictionary.json','outputs/r124/current_factor_dictionary.json']
 for item in current['selected'].values():assert sha(ROOT/item['path'])==item['sha256']
 audit=json.loads((out/'requirements_evidence.json').read_text());assert len(audit['items'])==16
 for item in audit['items']:
  assert not item['completion_proven']
  for ref in item['evidence']:assert sha(ROOT/ref['path'])==ref['sha256']
 js(out/'verification.json',dict(status='PASS',entries=19,unchanged_prior_entries=18,requirements_uncompleted=16,no_prediction_or_PIT_promotion=True))
 print('R49 VERIFIED 19 factors; all goal requirements still unproven')

if __name__=='__main__':run()

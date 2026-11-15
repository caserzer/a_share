from common import *

def run():
 out=ROOT/'outputs/r43';rows=json.loads((out/'current_factor_dictionary.json').read_text());old=json.loads((ROOT/'outputs/r34/current_factor_dictionary.json').read_text());receipt=json.loads((out/'receipt.json').read_text());assert rows[:-1]==old and len(rows)==18
 assert receipt['dictionary_sha256']==sha(out/'current_factor_dictionary.json') and receipt['previous_dictionary_sha256']==sha(ROOT/'outputs/r34/current_factor_dictionary.json')
 assert len({(x['module'],x['factor']) for x in rows})==18 and set(x['module'] for x in rows)==set('ABCDEFGH')
 for row in rows:
  assert not row['strict_pit_certified']
  for ref,digest in row['evidence_sha256'].items():assert sha(ROOT/ref)==digest
 metrics=json.loads((ROOT/'outputs/r41/metrics.json').read_text());assert not any(x['stability_sample_gate'] for x in metrics)
 gates=json.loads((ROOT/'outputs/r42/classifier_gates.json').read_text());assert len(gates)==40 and not any(x['qualified'] for x in gates)
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())
 for item in current['selected'].values():assert sha(ROOT/item['path'])==item['sha256']
 assert current['selected']['current_factor_dictionary']['path'] in ['outputs/r43/current_factor_dictionary.json','outputs/r49/current_factor_dictionary.json','outputs/r58/current_factor_dictionary.json','outputs/r66/current_factor_dictionary.json','outputs/r75/current_factor_dictionary.json','outputs/r92/current_factor_dictionary.json','outputs/r107/current_factor_dictionary.json','outputs/r112/current_factor_dictionary.json','outputs/r119/current_factor_dictionary.json','outputs/r124/current_factor_dictionary.json']
 audit=json.loads((out/'requirements_evidence.json').read_text());assert len(audit['items'])==16 and not any(x['completion_proven'] for x in audit['items'])
 for item in audit['items']:
  for ref in item['evidence']:assert (ROOT/ref['path']).is_file() and sha(ROOT/ref['path'])==ref['sha256']
 js(out/'verification.json',dict(status='PASS',entries=18,previous_entries_unchanged=17,requirements_uncompleted=16,selected_sources_checked=len(current['selected']),no_PIT_or_prediction_promotion=True))
 print('R43 VERIFIED 18 factors; 16 requirements remain unproven')

if __name__=='__main__':run()

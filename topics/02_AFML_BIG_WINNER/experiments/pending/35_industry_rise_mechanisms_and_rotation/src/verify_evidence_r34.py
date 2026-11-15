from common import *

def run():
 out=ROOT/'outputs/r34';rows=json.loads((out/'current_factor_dictionary.json').read_text());by={x['factor']:x for x in rows};receipt=json.loads((out/'receipt.json').read_text())
 assert len(rows)==17 and len(by)==17 and set(x['module'] for x in rows)==set('ABCDEFGH')
 assert receipt['dictionary_sha256']==sha(out/'current_factor_dictionary.json') and receipt['previous_dictionary_sha256']==sha(ROOT/'outputs/r23/current_factor_dictionary.json')
 assert by['fixed_fy_eps_revision']['implemented']=='historical_proxy_tested_partial_coverage' and by['typical_member_log_market_cap']['implemented']=='historical_proxy_control'
 for row in rows:
  assert row['strict_pit_certified'] is False
  for ref,digest in row['evidence_sha256'].items():assert sha(ROOT/ref)==digest
 pointer=json.loads((ROOT/'outputs/current_sources.json').read_text())['selected']['current_factor_dictionary'];assert sha(ROOT/pointer['path'])==pointer['sha256']
 audit=json.loads((out/'requirements_evidence.json').read_text());assert audit['overall_status']=='active_not_complete'
 for item in audit['items']:
  assert not item['completion_proven']
  for ref in item['evidence']:assert ref['exists'] and sha(ROOT/ref['path'])==ref['sha256']
 print('R34 VERIFIED 17 factors and',len(audit['items']),'uncompleted requirements')
if __name__=='__main__':run()

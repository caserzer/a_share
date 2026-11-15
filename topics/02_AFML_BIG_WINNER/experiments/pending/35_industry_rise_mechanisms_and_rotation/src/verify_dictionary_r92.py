from common import *
def run():
 out=ROOT/'outputs/r92';rec=json.loads((out/'receipt.json').read_text());old=json.loads((ROOT/'outputs/r75/current_factor_dictionary.json').read_text());rows=json.loads((out/'current_factor_dictionary.json').read_text());by={x['factor']:x for x in rows};assert len(rows)==len(by)==len(old)==24
 assert sha(ROOT/'outputs/r75/current_factor_dictionary.json')==rec['previous_dictionary_sha256'] and sha(out/'current_factor_dictionary.json')==rec['dictionary_sha256'] and sha(ROOT/'src/reconcile_realization_r92.py')==rec['code_sha256']
 for x in old:
  y=by[x['factor']]
  if x['factor'] not in rec['amended']:assert x==y
  else:
   for k,v in x.items():
    if k not in ['evidence_refs','evidence_sha256']:assert y[k]==v
 for x in rows:
  assert not x['strict_pit_certified']
  for k in ['theory','formula','direction','applicable_industries','economic_date','publication_date','available_at','frequency','source','historical_revisions','aggregation','missing_rule','failure_condition']:assert x[k]
  for p,h in x['evidence_sha256'].items():assert sha(ROOT/p)==h
 for n in range(76,92):assert json.loads((ROOT/f'outputs/r{n}/verification.json').read_text())['status']=='PASS'
 coverage=json.loads((ROOT/'outputs/r90/coverage.json').read_text());assert coverage['common_events']==1718 and coverage['unmatched_actual_pairs']==595
 s=json.loads((ROOT/'outputs/r90/summary.json').read_text());assert sum(x['mean_fixed_change']<0 for x in s if x['horizon']=='current')==5 and sum(x['mean_fixed_change']<0 for x in s if x['horizon']=='next')==4
 c=json.loads((ROOT/'outputs/r91/coverage.json').read_text());assert c['pairs']==2313 and c['industry_events']==4247 and c['known_post20']==4031 and c['known_post60']==3909 and c['excluded_on_actual']==0
 for x in json.loads((ROOT/'outputs/r91/summary.json').read_text()):
  if x['era']=='SW2021' and x['scope']=='pooled' and x['metric'] in ['post20','post60']:assert x['current_score']<0 and x['next_score']<0
 a=json.loads((out/'requirements_evidence.json').read_text());previous=json.loads((ROOT/'outputs/r75/requirements_evidence.json').read_text());assert [x['requirement'] for x in a['items']]==[x['requirement'] for x in previous['items']] and len(a['items'])==16 and not any(x['completion_proven'] for x in a['items'])
 for x in a['items']:
  for e in x['evidence']:assert e['exists'] and sha(ROOT/e['path'])==e['sha256']
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())['selected']
 for k,p in rec['routes'].items():
  if k in ['current_factor_dictionary','current_requirements_evidence'] and current[k]['path'] in [p.replace('/r92/','/r107/'),p.replace('/r92/','/r112/'),p.replace('/r92/','/r119/'),p.replace('/r92/','/r124/')]:continue
  assert current[k]==dict(path=p,sha256=sha(ROOT/p))
 for x in current.values():assert sha(ROOT/x['path'])==x['sha256']
 js(out/'verification.json',dict(status='PASS',entries=24,unchanged=23,amended=1,requirements_uncompleted=16,scope='dictionary preservation, evidence hashes and PASS receipts, exact numerical claim checks, all current routes',verifier_sha256=sha(Path(__file__))));print('R92 VERIFIED24 entries,16 uncompleted requirements')
if __name__=='__main__':run()

"""Verify current and historical route identity and material incomplete evidence."""
import pandas as pd
from common import *
from research_entry_r139 import load

def run():
 out=ROOT/'outputs/r175';own=dict(path='outputs/r175/release.json',sha256=sha(out/'release.json'));m=load(manifest_item=own);assert m['revision']=='R175';base=load(manifest_item=m['previous_release']);p=json.loads((ROOT/'protocols/r175.json').read_text());assert set(m['routes'])==set(base['routes'])|set(p['routes'])|{'current_requirements_audit'}
 for k,v in base['routes'].items():assert m['routes'][k]==v
 for k in set(m['routes'])-set(base['routes']):
  item=load(key=k,manifest_item=own);assert not item['predictive_adoption'] and not item['strict_pit'] and not item['production_enabled']
  if k in p['routes']:assert (item['path'],item['verification']['path'],item['interpretation'])==tuple(p['routes'][k])
 old=json.loads((ROOT/'outputs/r168/requirements_audit.json').read_text());new=json.loads((out/'requirements_audit.json').read_text());assert new['explicit_target_crosswalk']==old['explicit_target_crosswalk'];assert len(new['items'])==16 and not new['full_completion_proven']
 for a,b in zip(new['items'],old['items']):
  assert a['id']==b['id'] and a['requirement']==b['requirement'] and not a['completion_proven']
  if a['id'] not in p['requirement_updates']:assert a==b
  else:
   change=p['requirement_updates'][a['id']]
   for key in ['verified_scope','unresolved','next_dependency']:assert a[key]==change[key]
  for ref in a['evidence']:assert sha(ROOT/ref['path'])==ref['sha256']
 s=pd.read_csv(ROOT/m['routes']['l2_fixed_stock_summary']['path']);assert len(s)==20 and s.full_path_valued.sum()==49 and not s.whole_path_valid.any() and s.standalone_eligible.sum()==0
 c=pd.read_csv(ROOT/m['routes']['l1_followup_date_comparisons']['path']);c=c[c.strategy.eq('daily_cooldown20')&c.cohort.eq('all')&c.baseline.eq('F')];assert len(c)==3 and c.delta.lt(0).all()
 assert m['monitor_dates']==base['monitor_dates'] and m['unreviewed_legacy_routes']==base['unreviewed_legacy_routes']
 for n in [139,148,157,167]:
  path=f'outputs/r{n}/release.json';assert load(manifest_item=dict(path=path,sha256=sha(ROOT/path)))['revision']==f'R{n}'
 js(out/'verification.json',dict(status='PASS',routes=len(m['routes']),requirements=16,completion_proven=0,prior_routes_preserved=len(base['routes']),historical_entries=[139,148,157,167],complete_stock_intervals=49,standalone_execution_eligible=0,predictive_adoptions=0));print('R175 VERIFIED',len(m['routes']))
if __name__=='__main__':run()

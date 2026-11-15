"""Verify the default and historical entries and all interpretation boundaries."""
from common import *
from research_entry_r139 import load,ENTRY

def run():
 out=ROOT/'outputs/r157';pointer=dict(path='outputs/r157/release.json',sha256=sha(out/'release.json'));m=load(manifest_item=pointer);assert m['revision']=='R157';protocol=json.loads((ROOT/'protocols/r157.json').read_text());base=load(manifest_item=m['previous_release']);assert base['revision']=='R148';assert set(m['routes'])==set(base['routes'])|set(protocol['routes'])
 for key,item in base['routes'].items():assert m['routes'][key]==item
 for key,(path,proof,boundary) in protocol['routes'].items():
  item=load(key=key,manifest_item=pointer);assert item['path']==path and item['verification']['path']==proof and item['interpretation']==boundary
  assert item['predictive_adoption'] is False and item['strict_pit'] is False and item['production_enabled'] is False
 assert m['unreviewed_legacy_routes']==base['unreviewed_legacy_routes'];assert m['monitor_dates']==base['monitor_dates']
 for rev in [139,148]:
  p=ROOT/f'outputs/r{rev}/release.json';old=load(manifest_item=dict(path=str(p.relative_to(ROOT)),sha256=sha(p)));assert old['revision']==f'R{rev}'
 u=json.loads((ROOT/protocol['routes']['daily_calibration_uncertainty'][0]).read_text());recent=[x for x in u if x['era']=='SW2021'];assert len(recent)==4 and all(x['low_family']<0<x['high_family'] for x in recent)
 import pandas as pd
 d=pd.read_csv(ROOT/protocol['routes']['reversal_exit_economics'][0]);d=d[d.cohort.eq('risk_alert')&d.cost.eq(.002)];assert len(d)==4 and d.cash_improvement.lt(0).all() and d.market_improvement.lt(0).all()
 js(out/'verification.json',dict(status='PASS',routes=len(m['routes']),new_evidence_routes=len(protocol['routes']),original_only_routes=len(m['unreviewed_legacy_routes']),historical_entries_verified=[139,148],predictive_adoptions=0,recent_calibration_groups_inconclusive=4,negative_exit_groups=4,release_sha256=sha(out/'release.json'),verifier_sha256=sha(Path(__file__))))
 print('R157 VERIFIED',len(m['routes']))
if __name__=='__main__':run()

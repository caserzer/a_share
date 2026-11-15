"""Verify current routing without treating verified failure evidence as adoption."""
import pandas as pd
from common import *
from research_entry_r139 import load


def run():
    out=ROOT/'outputs/r183';m=load();assert m['revision']=='R183';base=load(manifest_item=m['previous_release']);p=json.loads((ROOT/'protocols/r183.json').read_text())
    assert set(m['routes'])==set(base['routes'])|set(p['routes'])|{'requirements_audit_r175'}
    for k,v in base['routes'].items():assert m['routes']['requirements_audit_r175' if k=='current_requirements_audit' else k]==v
    for k,values in p['routes'].items():
        item=load(key=k);assert [item['path'],item['verification']['path'],item['interpretation']]==values
        assert not any(item[x] for x in ['predictive_adoption','strict_pit','production_enabled'])
    assert 'FAILED_INPUT_CLOCK' in m['routes']['failed_update_replay']['interpretation']
    clock=json.loads((ROOT/m['routes']['update_clock_failure']['path']).read_text());assert clock['status']=='INPUT_CLOCK_FAILURE_CONFIRMED'
    assert [x['future_known_prefix_rows'] for x in clock['summary']]==[78,79]
    snaps=json.loads((ROOT/m['routes']['clock_safe_observation_runs']['path']).read_text());assert [x['excluded_future_known'] for x in snaps]==[78,79,0]
    assert all(x['observed_membership_dates']==x['present_l2_l3'] for x in snaps)
    ev=pd.read_parquet(ROOT/m['routes']['clock_safe_evaluation']['path']);assert len(ev)==4088 and ev.evaluation_kind.eq('historical_replay').all()
    audit=json.loads((out/'requirements_audit.json').read_text());old=json.loads((ROOT/'outputs/r175/requirements_audit.json').read_text())
    assert audit['explicit_target_crosswalk']==old['explicit_target_crosswalk'] and len(audit['items'])==16 and not audit['full_completion_proven']
    for a,b in zip(audit['items'],old['items']):
        assert a['id']==b['id'] and a['requirement']==b['requirement'] and not a['completion_proven']
        if a['id'] not in p['requirement_updates']:assert a==b
        for ref in a['evidence']:assert sha(ROOT/ref['path'])==ref['sha256']
    assert m['monitor_dates']==base['monitor_dates'] and m['unreviewed_legacy_routes']==base['unreviewed_legacy_routes']
    for n in [139,148,157,167,175]:
        path=f'outputs/r{n}/release.json';assert load(manifest_item=dict(path=path,sha256=sha(ROOT/path)))['revision']==f'R{n}'
    js(out/'verification.json',dict(status='PASS',routes=len(m['routes']),requirements=16,completion_proven=0,predictive_adoptions=0,failed_revision_explicit=True,historical_entries=[139,148,157,167,175]));print('R183 VERIFIED',len(m['routes']))


if __name__=='__main__':run()

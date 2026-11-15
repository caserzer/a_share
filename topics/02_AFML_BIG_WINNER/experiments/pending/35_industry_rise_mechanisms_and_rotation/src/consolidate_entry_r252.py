"""Consolidate existing research evidence; validate before changing local pointer."""
from copy import deepcopy
from common import ROOT, js, sha, json
from research_entry_r139 import load, checked, ENTRY

OUT = ROOT / 'outputs/r252'

def walk_refs(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and 'sha256' in value:
            checked(ROOT, value)
            yield value['path']
        for child in value.values():
            yield from walk_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_refs(child)

def run():
    protocol = json.loads((ROOT / 'protocols/r252.json').read_text())
    prior_pointer = json.loads((OUT / 'prior_current_sources.json').read_text())
    old = load(manifest_item=prior_pointer['selected'][ENTRY])
    assert old['revision'] == 'R183'
    routes = deepcopy(old['routes'])
    routes['requirements_audit_r183'] = routes.pop('current_requirements_audit')
    refs = []
    for name, (path, proof) in protocol['routes'].items():
        assert name not in routes
        assert json.loads((ROOT / proof).read_text())['status'] == 'PASS'
        refs.extend(walk_refs(json.loads((ROOT / path).read_text())))
        routes[name] = dict(path=path, sha256=sha(ROOT / path),
            verification=dict(path=proof, sha256=sha(ROOT / proof)),
            scope='historical research evidence; verification is not predictive certification',
            predictive_adoption=False, strict_pit=False, production_enabled=False)
    branches = json.loads((ROOT / 'outputs/r238/branch_decisions.json').read_text())['branches']
    assert len(branches) == 16 and all(x['adoption'] is False for x in branches)
    audit = json.loads((ROOT / 'outputs/r250/requirements_audit.json').read_text())
    refs.extend(walk_refs(audit))
    audit['revision'] = 'R252'
    audit['next_local'] = [{'priority': 1, 'task': protocol['next'],
        'basis': 'R02 retains daily regime applicability as unresolved; inspect existing R155 daily fitted models before deciding whether a missing comparison is executable.'}]
    audit['source_inventory_update'] = dict(path='outputs/r251/summary.json', sha256=sha(ROOT / 'outputs/r251/summary.json'),
        conclusion='Bounded local inventory found no new numerical observations; do not repeat identical source scans.')
    audit['items'][-1]['verified_scope'] += ' R251 inventory and R252 unified local entry retained; original scope unchanged.'
    assert len(audit['items']) == 16 and not any(x['completion_proven'] for x in audit['items'])
    js(OUT / 'requirements_audit.json', audit)
    js(OUT / 'audit_verification.json', dict(status='PASS', requirements=16, completion_proven=0,
        checked_reference_count=len(refs), meaning='reference integrity, not semantic completion'))
    routes['current_requirements_audit'] = dict(path='outputs/r252/requirements_audit.json', sha256=sha(OUT / 'requirements_audit.json'),
        verification=dict(path='outputs/r252/audit_verification.json',sha256=sha(OUT / 'audit_verification.json')))
    release = dict(old, revision='R252', routes=routes, previous_release=prior_pointer['selected'][ENTRY],
        next=protocol['next'], research_extensions={
            'all_model_decisions':'regime_branch_decisions', 'operating_evidence':'operating_quarter_entry',
            'archive_cli':'src/research_archive_cli_r239.py', 'operating_cli':'src/operating_reader_r250.py',
            'scope':'Explicit-date historical readers; no live update, scheduling or production enabled'})
    js(OUT / 'release.json', release)
    candidate = dict(path='outputs/r252/release.json', sha256=sha(OUT / 'release.json'))
    loaded = load(manifest_item=candidate)
    for key, item in old['routes'].items():
        assert loaded['routes']['requirements_audit_r183' if key == 'current_requirements_audit' else key] == item
    new_pointer = deepcopy(prior_pointer)
    new_pointer['selected'][ENTRY] = candidate
    current = json.loads((ROOT / 'outputs/current_sources.json').read_text())
    assert current in (prior_pointer, new_pointer), 'concurrent pointer change'
    js(ROOT / 'outputs/current_sources.json', new_pointer)
    assert load() == loaded
    js(OUT / 'verification.json', dict(status='PASS', prior_routes=len(old['routes']), current_routes=len(routes),
        added_evidence_routes=len(protocol['routes']), historical_audit_preserved=True, nested_hash_checks=len(refs),
        all_families=16, adopted_families=0, source_pointer_changes=[ENTRY], whole_goal_complete=False))
    print('R252 verified:', len(routes), 'routes;', len(refs), 'nested reference checks')

if __name__ == '__main__':
    run()

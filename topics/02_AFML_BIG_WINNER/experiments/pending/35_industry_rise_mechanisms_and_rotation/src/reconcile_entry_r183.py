"""Current research entry preserving failed and repaired update evidence."""
import pandas as pd
from common import *
from research_entry_r139 import load,ENTRY


def run():
    out=ROOT/'outputs/r183';p=json.loads((ROOT/'protocols/r183.json').read_text())
    base=load(manifest_item=dict(path='outputs/r175/release.json',sha256=sha(ROOT/'outputs/r175/release.json')))
    prior=json.loads((out/'prior_release.json').read_text())
    # Maintenance refreshes legacy registry metadata, never verified evidence routes.
    assert set(base)==set(prior)
    for k in base:
        if k not in ['unreviewed_legacy_routes','legacy_registry_refreshes','previous_release']:assert base[k]==prior[k],k
    hashes={x['path']:x['sha256'] for x in json.loads((out/'prior_progress_manifest.json').read_text())['files']}
    clock=json.loads((ROOT/'outputs/r180/clock_audit.json').read_text())
    for path,h in clock['reads'].items():assert sha(path)==h
    bad=pd.read_parquet(ROOT/'outputs/r180/future_known_rows.parquet')
    assert len(bad)==157 and bad.known_at.gt(bad['asof']).all() and bad.date.le(bad['asof']).all()
    assert clock['status']=='INPUT_CLOCK_FAILURE_CONFIRMED'
    js(out/'clock_verification.json',dict(status='PASS',meaning='failure evidence verified, not successful input qualification',future_known_rows=157,failed_revision='R179',repair_revisions=['R181','R182']))
    routes=dict(base['routes']);routes['requirements_audit_r175']=routes.pop('current_requirements_audit')
    for k,(path,proof,boundary) in p['routes'].items():
        assert k not in routes and sha(ROOT/path)==hashes[path]
        if not proof.startswith('outputs/r183/'):assert sha(ROOT/proof)==hashes[proof]
        assert json.loads((ROOT/proof).read_text())['status']=='PASS'
        routes[k]=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),scope='verified historical evidence including documented failures',interpretation=boundary,predictive_adoption=False,strict_pit=False,production_enabled=False)
    audit=json.loads((ROOT/'outputs/r175/requirements_audit.json').read_text());audit['revision']='R183';audit['next_local']=p['next_local'];audit['full_completion_proven']=False
    for item in audit['items']:
        if item['id'] in p['requirement_updates']:
            change=p['requirement_updates'][item['id']];item.update({k:v for k,v in change.items() if k!='routes'})
            item['evidence']=[dict(route=k,path=routes[k]['path'],sha256=routes[k]['sha256']) for k in change['routes']]
        assert not item['completion_proven']
        for ref in item['evidence']:assert sha(ROOT/ref['path'])==ref['sha256']
    js(out/'requirements_audit.json',audit);js(out/'audit_verification.json',dict(status='PASS',requirements=16,completion_proven=0,scope='lineage audit; no scientific success inferred'))
    path='outputs/r183/requirements_audit.json';proof='outputs/r183/audit_verification.json'
    routes['current_requirements_audit']=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),scope='current incomplete requirement status',interpretation='all requirements still unproven for overall completion',predictive_adoption=False,strict_pit=False,production_enabled=False)
    release=dict(base,revision='R183',routes=routes,previous_release=dict(path='outputs/r175/release.json',sha256=sha(ROOT/'outputs/r175/release.json')),source_snapshot_sha256=sha(out/'prior_progress_manifest.json'),next=p['next_local'][0]['task'])
    js(out/'release.json',release);cur=json.loads((ROOT/'outputs/current_sources.json').read_text());cur['selected'][ENTRY]=dict(path='outputs/r183/release.json',sha256=sha(out/'release.json'));js(ROOT/'outputs/current_sources.json',cur);load()
    js(out/'receipt.json',dict(status='PASS',routes=len(routes),prior_routes=len(base['routes']),new_evidence_routes=len(p['routes']),failed_revision_retained='R179',predictive_adoptions=0));print('R183 ENTRY',len(routes))


if __name__=='__main__':run()

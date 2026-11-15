"""Check immutable prior definitions, incomplete requirements and bounded sources."""
from common import *
def run():
    out=ROOT/'outputs/r124';rec=json.loads((out/'receipt.json').read_text())
    assert rec['code_sha256']==sha(ROOT/'src/reconcile_financial_r124.py') and rec['protocol_sha256']==sha(ROOT/'protocols/r124.json')
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    old=json.loads((ROOT/'outputs/r119/current_factor_dictionary.json').read_text());new=json.loads((out/'current_factor_dictionary.json').read_text())
    assert new[:27]==old and len(new)==len({x['factor'] for x in new})==28
    assert rec['prior_dictionary_sha256']==sha(ROOT/'outputs/r119/current_factor_dictionary.json')
    x=new[-1];assert x['factor']=='consecutive_reported_ttm_bounded_change' and not x['strict_pit_certified']
    for k in ['theory','formula','direction','applicable_industries','economic_date','publication_date','available_at','frequency','source','historical_revisions','aggregation','missing_rule','failure_condition','conclusion']:assert x[k]
    for x in new:
        for p,h in x['evidence_sha256'].items():assert sha(ROOT/p)==h
    before=json.loads((ROOT/'outputs/r119/requirements_evidence.json').read_text());after=json.loads((out/'requirements_evidence.json').read_text())
    assert rec['prior_requirements_sha256']==sha(ROOT/'outputs/r119/requirements_evidence.json')
    assert len(after['items'])==16 and [x['requirement'] for x in before['items']]==[x['requirement'] for x in after['items']]
    for a,b in zip(before['items'],after['items']):
        assert not b['completion_proven'] and all(e in b['evidence'] for e in a['evidence'])
        for e in b['evidence']:assert e['exists'] and sha(ROOT/e['path'])==e['sha256']
    branch=json.loads((out/'branch_evidence.json').read_text())
    assert branch['status']=='stopped_parameter_search_not_adopted' and not branch['strict_pit'] and not branch['clock_selected']
    assert set(branch['refs'])=={f'outputs/r{x}/verification.json' for x in range(120,124)}
    for p,h in branch['refs'].items():assert h==sha(ROOT/p) and branch['results'][p]==json.loads((ROOT/p).read_text())
    assert branch['results']['outputs/r122/verification.json']['support_groups']==branch['results']['outputs/r123/verification.json']['support_groups']==0
    audit=json.loads((out/'source_audit.json').read_text())
    assert audit['status']=='bounded_inventory_not_ready_for_prediction'
    for x in audit['candidates']:
        assert any(Path(x['path']).is_relative_to(Path(root)) for root in audit['roots'])
        assert Path(x['path']).stat().st_size==x['bytes'] and sha(x['path'])==x['sha256']
    assert audit['structured_filename_candidates']==[x['path'] for x in audit['candidates'] if Path(x['path']).suffix in ['.csv','.parquet','.json','.sqlite','.db']]
    assert sha(audit['producer']['path'])==audit['producer']['sha256']
    cur=json.loads((ROOT/'outputs/current_sources.json').read_text())['selected']
    for k,p in rec['routes'].items():assert cur[k]==dict(path=p,sha256=sha(ROOT/p))
    for x in cur.values():assert sha(ROOT/x['path'])==x['sha256']
    js(out/'verification.json',dict(status='PASS',preserved_entries=27,entries=28,requirements=16,completed=0,candidate_source_files=len(audit['candidates']),structured_filename_candidates=len(audit['structured_filename_candidates']),source_ready=False))
    print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()

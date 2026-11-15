"""Verify evidence preservation, diagnostic scope and source routing independently."""
from common import *
def run():
    out=ROOT/'outputs/r119';r=json.loads((out/'receipt.json').read_text())
    for name,h in r['outputs'].items():assert sha(out/name)==h
    assert r['code_sha256']==sha(ROOT/'src/reconcile_valuation_r119.py') and r['protocol_sha256']==sha(ROOT/'protocols/r119.json')
    old=json.loads((ROOT/'outputs/r112/current_factor_dictionary.json').read_text());new=json.loads((out/'current_factor_dictionary.json').read_text())
    assert new[:25]==old and len(new)==len({x['factor'] for x in new})==27
    assert r['prior_dictionary_sha256']==sha(ROOT/'outputs/r112/current_factor_dictionary.json')
    assert [x['factor'] for x in new[-2:]]==['price_pe_implied_earnings_decomposition','reported_ttm_vs_pe_implied_profit_diagnostic']
    for x in new:
        for p,h in x['evidence_sha256'].items():assert sha(ROOT/p)==h
    for x in new[-2:]:
        assert not x['strict_pit_certified'] and x['implemented']=='historical_diagnostic_verified'
        for k in ['theory','formula','direction','applicable_industries','economic_date','publication_date','available_at','frequency','source','historical_revisions','aggregation','missing_rule','failure_condition','conclusion']:assert x[k]
    oldreq=json.loads((ROOT/'outputs/r112/requirements_evidence.json').read_text());req=json.loads((out/'requirements_evidence.json').read_text())
    assert r['prior_requirements_sha256']==sha(ROOT/'outputs/r112/requirements_evidence.json')
    assert len(req['items'])==16 and [x['requirement'] for x in oldreq['items']]==[x['requirement'] for x in req['items']]
    for a,b in zip(oldreq['items'],req['items']):
        assert not b['completion_proven'] and all(e in b['evidence'] for e in a['evidence'])
        for e in b['evidence']:assert e['exists'] and sha(ROOT/e['path'])==e['sha256']
    branch=json.loads((out/'branch_evidence.json').read_text())
    assert not any(branch[k] for k in ['strict_pit','clock_selected','matching_filter_for_prediction'])
    assert set(branch['refs'])=={f'outputs/r{x}/verification.json' for x in range(113,119)}
    for p,h in branch['refs'].items():
        assert h==sha(ROOT/p) and branch['results'][p]==json.loads((ROOT/p).read_text()) and branch['results'][p]['status']=='PASS'
    a=branch['results']['outputs/r118/verification.json']
    assert a['common_pairs']==a['same_period_pairs']+a['different_period_pairs']==93530 and a['same_period_values_identical']
    current=json.loads((ROOT/'outputs/current_sources.json').read_text())['selected']
    for k,p in r['routes'].items():
        if k in ['current_factor_dictionary','current_requirements_evidence','latest_stage_requirements_audit'] and current[k]['path']==p.replace('/r119/','/r124/'):continue
        assert current[k]==dict(path=p,sha256=sha(ROOT/p))
    for x in current.values():assert x['sha256']==sha(ROOT/x['path'])
    js(out/'verification.json',dict(status='PASS',preserved_entries=25,diagnostics_added=2,entries=27,requirements=16,completed=0,source_rounds=list(range(113,119)),strict_pit=False,predictive_promotion=False))
    print('PASS 27 definitions,16 incomplete requirements,6 diagnostic rounds')
if __name__=='__main__':run()

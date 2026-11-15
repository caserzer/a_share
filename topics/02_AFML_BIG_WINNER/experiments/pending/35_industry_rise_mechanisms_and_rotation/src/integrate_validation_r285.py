from common import *
from copy import deepcopy
from research_entry_r139 import load,ENTRY

def run():
    out=ROOT/'outputs/r285';out.mkdir(exist_ok=True)
    snapshot=out/'prior_current_sources.json'
    if not snapshot.exists():snapshot.write_bytes((ROOT/'outputs/current_sources.json').read_bytes())
    prior=json.loads(snapshot.read_text());base=load(manifest_item=prior['selected'][ENTRY]);assert base['revision']=='R279'
    routes=deepcopy(base['routes']);routes['requirements_audit_r279']=routes.pop('current_requirements_audit');refs=[]
    for rnd in range(280,285):
        path=f'outputs/r{rnd}/'+('current_status.json' if rnd==282 else 'summary.json')
        proof=f'outputs/r{rnd}/'+('verification.json' if rnd==282 else 'independent_verification.json')
        assert json.loads((ROOT/proof).read_text())['status']=='PASS'
        item=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),strict_pit=False,predictive_adoption=False,production_enabled=False)
        routes[f'battery_validation_r{rnd}']=item;refs.append(item)
    protocol=json.loads((ROOT/'protocols/r285.json').read_text())
    decision=dict(adoption=False,models_refit=0,independent_prospective=0,stop_parameter_search=True,scope='Battery extension; all16 original model families retained',source_revision='Monthly total and chemistry conflicts unresolved; annual compatibility does not certify truth',evidence=refs)
    js(out/'branch_decision.json',decision)
    remaining=json.loads((ROOT/'outputs/r279/remaining_work.json').read_text())
    remaining['completed_since_prior']=['R280 all81 installation body checks','R281 fixed seasonal control','R282 frozen validation contract','R283 missing label coverage','R284 monthly and annual version comparison']
    remaining['next_local']=dict(task=protocol['next'],scope='Existing local core reversal parameters, price features and event definitions; eligibility audit before new replay',acceptance='Identify exact eligible folds, trend/event rules and missing daily inputs; no invented economic reversal label or retrospective tuning')
    remaining['stopped_local_searches']+=['Battery seasonal harmonic/phase selection','Repeated synonym searches for same installation discrepancy']
    remaining['external_dependencies'].append(dict(item='Battery revision explanation and independent mature labels',evidence='reports/r284_battery_vintage_resolution.md',condition='Identifiable release/revision evidence or actual new observations; no inferred replacement'))
    js(out/'remaining_work.json',remaining)
    audit=json.loads((ROOT/'outputs/r279/requirements_audit.json').read_text());audit['revision']='R285';audit['next_local']=[remaining['next_local']]
    for item in audit['items']:
        if item['id'] in ['R01','R10','R11','R12','R14','R16']:
            item.setdefault('latest_extension_evidence',[]).extend(refs)
            item['verified_scope']+=' R280–R284已补齐正文、季节性、冻结约定、缺标签和跨版本月度/累计核验；无稳定增量认证。'
        item['unresolved']=item['unresolved'].replace('原装车量尚待修正正文逐条核验。','81月装车量已对应正文；2025-12月度总量及分项与去年值不相容、修订原因未明。')
    assert len(audit['items'])==16 and all(not x['completion_proven'] for x in audit['items'])
    js(out/'requirements_audit.json',audit)
    js(out/'integration_proof.json',dict(status='PASS',scope='Index integrity only; not predictive or full-goal certification',original_families=16,requirements=16))
    proof=dict(path='outputs/r285/integration_proof.json',sha256=sha(out/'integration_proof.json'))
    for name,path in [('battery_validation_report','reports/r285_battery_validation_delivery.md'),('battery_validation_decision','outputs/r285/branch_decision.json'),('current_requirements_audit','outputs/r285/requirements_audit.json'),('remaining_work_r285','outputs/r285/remaining_work.json'),('battery_validation_contract','protocols/r282.json')]:
        routes[name]=dict(path=path,sha256=sha(ROOT/path),verification=proof,strict_pit=False,predictive_adoption=False,production_enabled=False)
    release=dict(base,revision='R285',routes=routes,previous_release=prior['selected'][ENTRY],next=protocol['next'],research_extensions=dict(base['research_extensions'],battery_validation='battery_validation_decision'))
    js(out/'release.json',release);pointer=dict(path='outputs/r285/release.json',sha256=sha(out/'release.json'));candidate=load(manifest_item=pointer)
    for k,v in base['routes'].items():assert candidate['routes']['requirements_audit_r279' if k=='current_requirements_audit' else k]==v
    assert candidate['monitor_dates']==base['monitor_dates']
    new=deepcopy(prior);new['selected'][ENTRY]=pointer
    assert json.loads((ROOT/'outputs/current_sources.json').read_text()) in (prior,new)
    js(ROOT/'outputs/current_sources.json',new);assert load()==candidate
    js(out/'verification.json',dict(status='PASS',routes=len(routes),preserved_routes=len(base['routes']),adoption=False,monitor_dates_unchanged=True))
    print('R285 INTEGRATED',len(routes))
if __name__=='__main__':run()

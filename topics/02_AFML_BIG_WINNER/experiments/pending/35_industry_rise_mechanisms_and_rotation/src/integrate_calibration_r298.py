from common import *
from copy import deepcopy
from research_entry_r139 import load,ENTRY

def run():
    out=ROOT/'outputs/r298';out.mkdir(exist_ok=True)
    snapshot=out/'prior_current_sources.json'
    if not snapshot.exists():snapshot.write_bytes((ROOT/'outputs/current_sources.json').read_bytes())
    prior=json.loads(snapshot.read_text());base=load(manifest_item=prior['selected'][ENTRY]);assert base['revision']=='R294'
    routes=deepcopy(base['routes']);routes['requirements_audit_r294']=routes.pop('current_requirements_audit');refs=[]
    for rnd in range(295,298):
        path=f'outputs/r{rnd}/'+('summary.csv' if rnd==296 else 'summary.json');proof=f'outputs/r{rnd}/independent_verification.json'
        assert json.loads((ROOT/proof).read_text())['status']=='PASS'
        item=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),strict_pit=False,predictive_adoption=False,production_enabled=False)
        routes[f'reversal_calibration_r{rnd}']=item;refs.append(item)
    protocol=json.loads((ROOT/'protocols/r298.json').read_text())
    js(out/'branch_decision.json',dict(adoption=False,models_refit=0,independent_prospective=0,stop_parameter_search=True,scope='Core F/F reversal20 daily and month-end; all16 families retained',evidence=refs,interpretation='Calibration changes probabilities, not original ranked alerts; no stable regime increment'))
    remaining=json.loads((ROOT/'outputs/r294/remaining_work.json').read_text())
    remaining['completed_since_prior']=[f'R{i} reversal calibration/uncertainty/action equivalence' for i in range(295,298)]
    remaining['next_local']=dict(task=protocol['next'],scope='Exact-date frozen reversal probability comparison with explicit retrospective boundaries',acceptance='No future outcome fields, explicit source hashes and calibration frequency, missing dates remain unavailable')
    remaining['stopped_local_searches'].append('Reversal exit capacity/risk metric/weight search to rescue historical results')
    js(out/'remaining_work.json',remaining)
    audit=json.loads((ROOT/'outputs/r294/requirements_audit.json').read_text());audit['revision']='R298';audit['next_local']=[remaining['next_local']]
    for item in audit['items']:
        if item['id'] in ['R04','R05','R11','R14','R16']:
            item.setdefault('latest_extension_evidence',[]).extend(refs)
            item['verified_scope']+=' R295—R297反转日频校准、时间块不确定性与实际名单等价已完成；无稳定regime增量认证。'
        if item['id']=='R04':item['unresolved']='核心反转日频去重提前量未获统一改善；日频校准已比较，14项regime对base无明确改善，提示不变；局部改善不能外推稳定校准。价格过程不同于经济反转，独立未来及真实执行未认证。'
    assert len(audit['items'])==16 and all(not x['completion_proven'] for x in audit['items']);js(out/'requirements_audit.json',audit)
    js(out/'integration_proof.json',dict(status='PASS',scope='Index integrity only, not full-goal or predictive certification',original_families=16,requirements=16))
    proof=dict(path='outputs/r298/integration_proof.json',sha256=sha(out/'integration_proof.json'))
    for name,path in [('reversal_calibration_report','reports/r298_calibration_delivery.md'),('reversal_calibration_decision','outputs/r298/branch_decision.json'),('current_requirements_audit','outputs/r298/requirements_audit.json'),('remaining_work_r298','outputs/r298/remaining_work.json'),('probability_use_contract','outputs/r298/probability_use_contract.json')]:
        routes[name]=dict(path=path,sha256=sha(ROOT/path),verification=proof,strict_pit=False,predictive_adoption=False,production_enabled=False)
    release=dict(base,revision='R298',routes=routes,previous_release=prior['selected'][ENTRY],next=protocol['next'],research_extensions=dict(base['research_extensions'],reversal_calibration='reversal_calibration_decision'))
    js(out/'release.json',release);pointer=dict(path='outputs/r298/release.json',sha256=sha(out/'release.json'));candidate=load(manifest_item=pointer)
    for k,v in base['routes'].items():assert candidate['routes']['requirements_audit_r294' if k=='current_requirements_audit' else k]==v
    assert candidate['monitor_dates']==base['monitor_dates']
    new=deepcopy(prior);new['selected'][ENTRY]=pointer
    assert json.loads((ROOT/'outputs/current_sources.json').read_text()) in (prior,new)
    js(ROOT/'outputs/current_sources.json',new);assert load()==candidate
    js(out/'verification.json',dict(status='PASS',routes=len(routes),preserved_routes=len(base['routes']),adoption=False,monitor_dates_unchanged=True,script_sha256=sha(Path(__file__)),protocol_sha256=sha(ROOT/'protocols/r298.json')))
    print('R298 INTEGRATED',len(routes))
if __name__=='__main__':run()

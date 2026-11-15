from copy import deepcopy
from common import *
from research_entry_r139 import load,ENTRY

def run():
 out=ROOT/'outputs/r259';protocol=json.loads((ROOT/'protocols/r259.json').read_text());prior=json.loads((out/'prior_current_sources.json').read_text());base=load(manifest_item=prior['selected'][ENTRY]);assert base['revision']=='R252'
 routes=deepcopy(base['routes']);routes['requirements_audit_r252']=routes.pop('current_requirements_audit');refs=[]
 for round in protocol['rounds']:
  path=f'outputs/r{round}/summary.csv';proof=f'outputs/r{round}/independent_verification.json';assert json.loads((ROOT/proof).read_text())['status']=='PASS'
  routes[f'daily_extension_r{round}']=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),scope=protocol['scope'],predictive_adoption=False,strict_pit=False,production_enabled=False)
  refs.append(dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof))))
 decision=dict(family='core_three_tasks',subscope='F cohort/F method/onset20/L2-L3 daily application',rounds=protocol['rounds'],adoption=False,stop_unsupported_parameter_search=True,conclusions=['Same-event median lead gain zero in four pooled groups','Recent interaction recall advantage not retained under date-level matched workload','No daily-calibrated regime vs daily-calibrated base lower-error family interval; four higher-error comparisons','Recent calibrated alert lists unchanged; two old-classification slope flips evaluated'],boundaries=['Historical-proxy, repeatedly studied history','Not economic onset or causal certification','Not all16 families validated at daily frequency','No new execution or independent prospective evidence'],reopen=['Independent new mature period under frozen protocol','Concrete source or implementation defect','Necessary omitted comparison grounded in original requirements'],evidence=refs)
 js(out/'daily_branch_decision.json',decision)
 audit=json.loads((ROOT/'outputs/r252/requirements_audit.json').read_text());audit['revision']='R259';audit['next_local']=[dict(priority=1,task=protocol['next'],boundary='No blanket frequency expansion, no external collection beyond existing explicit scope')]
 for item in audit['items']:
  if item['id'] in ['R02','R11','R14','R16']:
   item['latest_extension_evidence']+=refs
   item['verified_scope']+=' R253–R258补齐core F/F onset20二三级每日冻结重放、同事件提前量、同日工作量、日频校准和行动复核。'
  if item['id']=='R02':item['unresolved']='已补齐上述特定日频应用；价格事件非经济启动，独立前瞻未完成，不能外推到全部机制或期限。'
  if item['id']=='R16':item['unresolved']='停止无依据每日/regime参数搜索；按完整目标核查有依据的遗漏比较，保留未来样本和时点限制。'
 assert len(audit['items'])==16 and not any(x['completion_proven'] for x in audit['items']) and audit['explicit_target_crosswalk']==json.loads((ROOT/'outputs/r252/requirements_audit.json').read_text())['explicit_target_crosswalk']
 js(out/'requirements_audit.json',audit)
 js(out/'integration_proof.json',dict(status='PASS',meaning='Evidence integration and scope preservation; not statistical certification',prior_routes=len(base['routes']),new_rounds=6,families=16,requirements=16,adoptions=0))
 for name,file in [('daily_branch_decision','daily_branch_decision.json'),('current_requirements_audit','requirements_audit.json')]:routes[name]=dict(path=f'outputs/r259/{file}',sha256=sha(out/file),verification=dict(path='outputs/r259/integration_proof.json',sha256=sha(out/'integration_proof.json')),predictive_adoption=False,production_enabled=False,strict_pit=False)
 release=dict(base,revision='R259',routes=routes,previous_release=prior['selected'][ENTRY],next=protocol['next'],research_extensions=dict(base['research_extensions'],daily_application='daily_branch_decision'))
 js(out/'release.json',release);pointer=dict(path='outputs/r259/release.json',sha256=sha(out/'release.json'));candidate=load(manifest_item=pointer)
 for name,value in base['routes'].items():assert candidate['routes']['requirements_audit_r252' if name=='current_requirements_audit' else name]==value
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());new=deepcopy(prior);new['selected'][ENTRY]=pointer;assert current in (prior,new);js(ROOT/'outputs/current_sources.json',new);assert load()==candidate
 js(out/'verification.json',dict(status='PASS',routes=len(routes),prior_routes_preserved=len(base['routes']),new_evidence_rounds=6,scope_preserved=True,adoption=False));print('R259',len(routes),'routes')
if __name__=='__main__':run()

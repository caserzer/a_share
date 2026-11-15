from common import *
from copy import deepcopy
from research_entry_r139 import load,ENTRY

def run():
 out=ROOT/'outputs/r266';prior=json.loads((out/'prior_current_sources.json').read_text());base=load(manifest_item=prior['selected'][ENTRY]);assert base['revision']=='R259';protocol=json.loads((ROOT/'protocols/r266.json').read_text());routes=deepcopy(base['routes']);routes['requirements_audit_r259']=routes.pop('current_requirements_audit');refs=[]
 for rnd in range(260,266):
  file='summary.json' if rnd==260 else 'summary.csv';path=f'outputs/r{rnd}/{file}';proof=f'outputs/r{rnd}/independent_verification.json';assert json.loads((ROOT/proof).read_text())['status']=='PASS';item=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),predictive_adoption=False,strict_pit=False,production_enabled=False);routes[f'financing_extension_r{rnd}']=item;refs.append(item)
 shared=dict(family='financing',type='EP35_extension',frequency='monthly',theory='Distinguish financing balance from valuation denominator',direction='Balance increase is a candidate demand proxy; predictive sign not certified',industry_scope='SW2014 L2/L3; SW2021 L1/L2/L3 subject to qualification',economic_date='Balance snapshot signal date minus 2 trading sessions; cap at signal date',publication_date='Original first-release timestamp not established',available_time='Historical-proxy signal-date construction; strict PIT false',revision='No complete first-release revision chain',source=['outputs/r260/pairs.parquet','outputs/r261/industry_pairs.parquet'],aggregation='Median on fixed positive complete common companies',missing_rule='Both original industry endpoints present; >=5 and >=80% of each endpoint membership; else null',failure='Nonpositive B/P/S, identity or date mismatch, missing members, insufficient history; no zero fill',strict_pit=False,adoption=False)
 factors=[]
 for name,formula in [('balance_component','0.5*((f10-f00)+(f11-f01))'),('cap_component','0.5*((f01-f00)+(f11-f10))')]:factors.append(dict(shared,id=name,formula=formula,notation='fij = median(B_i / (P_j*S_j)) on identical common company cohort'))
 js(out/'factor_dictionary.json',dict(revision='R266',definitions=factors,evidence=refs,boundary='Algebra attribution is not causal flow; native/common difference not pure membership effect'))
 decision=dict(family='financing',adoption=False,stop_unsupported_search=True,rounds=list(range(260,266)),conclusions=['Intensity can rise with nonincreasing balance','No stable return increment in qualified comparisons','Classifier local Brier/label improvements do not establish exit value','All frozen versions below hold on observed paths and below uniform selection on complete dates'],reopen=['Independent mature new period','Concrete source/implementation defect','Grounded omitted comparison'],next=protocol['next'],evidence=refs)
 js(out/'branch_decision.json',decision);audit=json.loads((ROOT/'outputs/r259/requirements_audit.json').read_text());audit['revision']='R266';audit['next_local']=[dict(priority=1,task=protocol['next'],boundary='Local exact-date coverage first; retain original 16 families and no adoption')]
 for x in audit['items']:
  if x['id'] in ['R01','R04','R08','R11','R13','R14','R16']:
   x.setdefault('latest_extension_evidence',[]).extend(refs);x['verified_scope']+=' R260–R265融资分母替代解释、共同公司拆解、三任务资格、regime对照、退出与随机参照已补齐；时钟差及短历史保留。'
 assert len(audit['items'])==16 and not any(x['completion_proven'] for x in audit['items']);js(out/'requirements_audit.json',audit)
 js(out/'integration_proof.json',dict(status='PASS',scope='Local routes and definitions integration; not predictive certification',families=16,requirements=16,adoption=False))
 proof=dict(path='outputs/r266/integration_proof.json',sha256=sha(out/'integration_proof.json'))
 for name,path in [('financing_factor_dictionary','outputs/r266/factor_dictionary.json'),('financing_branch_decision','outputs/r266/branch_decision.json'),('financing_mechanism_report','reports/r266_financing_mechanism_delivery.md'),('current_requirements_audit','outputs/r266/requirements_audit.json')]:routes[name]=dict(path=path,sha256=sha(ROOT/path),verification=proof,predictive_adoption=False,strict_pit=False,production_enabled=False)
 release=dict(base,revision='R266',routes=routes,previous_release=prior['selected'][ENTRY],next=protocol['next'],research_extensions=dict(base['research_extensions'],financing_components='financing_branch_decision'));js(out/'release.json',release);pointer=dict(path='outputs/r266/release.json',sha256=sha(out/'release.json'));candidate=load(manifest_item=pointer)
 for k,v in base['routes'].items():assert candidate['routes']['requirements_audit_r259' if k=='current_requirements_audit' else k]==v
 assert audit['explicit_target_crosswalk']==json.loads((ROOT/'outputs/r259/requirements_audit.json').read_text())['explicit_target_crosswalk']
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());new=deepcopy(prior);new['selected'][ENTRY]=pointer;assert current in (prior,new);js(ROOT/'outputs/current_sources.json',new);assert load()==candidate
 js(out/'verification.json',dict(status='PASS',routes=len(routes),old_routes_preserved=len(base['routes']),families=16,requirements=16,adoption=False));print('R266',len(routes))
if __name__=='__main__':run()

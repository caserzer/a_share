from common import *
import pandas as pd
CONFIG={
 'core_three_tasks':([196,207,208,210,220,221,222,223],'核心三任务','退出较原模型少亏，启动无普遍改善；多数退出仍不及持有'),
 'l1_three_tasks':([196,207,208,210,220,221,222,223],'一级三任务','保留训练/校准失败，不能把原始未校准模型冒充regime概率模型'),
 'rank_target':([196,207,210,223],'收益排名目标','排序局部改善不形成普遍成本后优势'),
 'market_style':([199,208,209,211,220,221,222,223],'市场与风格','交互多数增加换手，基准和时期敏感'),
 'battery':([198,209,218],'装车量单行业','20日决策正负混合，未胜始终行业，区间重叠不可拼净值'),
 'eps_expectations':([197,209,215,223],'固定年度EPS','局部胜过交互价格模型，但仍落后原始价格基线'),
 'size_diffusion':([199,208,209,211,220,221,222,223],'规模与扩散','局部正差受共同完整样本和回撤限制'),
 'financing':([199,208,209,211,220,221,222,223],'融资机制','反转局部线索不代表配置稳定增益'),
 'profit_events':([205,209,219],'利润预期事件','交互下新增预期修正的20日行动增量十组全负'),
 'leader_catchup':([200,208,209,212,213,220,221,222,223],'龙头与追赶','龙头交互组合偏弱；追赶原股票两侧仅261/1526区间完整'),
 'financial_dual_clock':([201,209,214,223],'财务双时钟','窄公告母体交互自身改善，财务相对控制仍负'),
 'capital_accounting':([206],'资本会计','仅六期观察，训练资格不足；未虚构模型'),
 'macro_interaction':([202,209,217,223],'宏观交互','45/75日滞后和时期敏感；自身改善未稳定胜价格F'),
 'profit_expectations':([197,209,215,223],'固定年度利润预期','八期局部正收益线索，未达稳定条件'),
 'early_financial':([203],'早期财务','仅六期观察，训练资格不足；保留状态诊断'),
 'fixed_factor_rank':([204,207,216,223],'固定因子排序','相对弱校准base改善不能替代原始fixed对照')}
for family in ['core_three_tasks','market_style','size_diffusion','financing','leader_catchup']:
 CONFIG[family][0].extend([226,227,228,229])
for family in ['battery','profit_events','leader_catchup']:
 CONFIG[family][0].append(225)
def run():
 out=ROOT/'outputs/r230';out.mkdir(exist_ok=True);source=ROOT/'outputs/r195/experiment_registry.json';reg=json.loads(source.read_text());assert set(CONFIG)=={r['family'] for r in reg['families']};hashes={};checks=[];receipts=[]
 def digest(path):
  key=str(path)
  if key not in hashes:hashes[key]=sha(path)
  return hashes[key]
 for rnd in range(195,230):
  directory=ROOT/f'outputs/r{rnd}'
  for path in sorted(directory.glob('*.json')):
   if path.name=='receipt_inventory.json':continue
   if not any(x in path.name for x in ['verification','receipt','audit']):continue
   data=json.loads(path.read_text());receipts.append(dict(round=rnd,path=str(path.relative_to(ROOT)),sha256=digest(path),declared_status=data.get('status'),scope=data.get('scope',data.get('method','see receipt'))))
   for role in ['inputs','reads','outputs']:
    values=data.get(role,{})
    if not isinstance(values,dict):continue
    for name,expected in values.items():
     if not isinstance(expected,str) or len(expected)!=64:checks.append(dict(receipt=str(path.relative_to(ROOT)),role=role,reference=name,status='unrecognized_hash_schema'));continue
     ref=Path(name)
     if not ref.is_absolute():ref=(ROOT/ref) if name.startswith(('outputs/','data/','src/','protocols/')) else path.parent/ref
     actual=digest(ref) if ref.is_file() else None;checks.append(dict(receipt=str(path.relative_to(ROOT)),role=role,reference=name,resolved=str(ref),expected=expected,actual=actual,status='match' if actual==expected else 'missing' if actual is None else 'mismatch'))
 for row in reg['families']:
  for item in row['inputs']+[dict(path=row['regime_evidence'],sha256=row['regime_evidence_sha256'])]:
   path=ROOT/item['path'];actual=digest(path) if path.is_file() else None;checks.append(dict(receipt='R195_registry/'+row['family'],role='lineage',reference=item['path'],resolved=str(path),expected=item['sha256'],actual=actual,status='match' if actual==item['sha256'] else 'missing' if actual is None else 'mismatch'))
 pd.DataFrame(checks).to_csv(out/'hash_audit.csv',index=False);js(out/'receipt_inventory.json',receipts);families=[]
 for original in reg['families']:
  f=original['family'];rounds,title,conclusion=CONFIG[f];evidence=[]
  for rnd in rounds:
   entries=[x for x in receipts if x['round']==rnd];assert entries
   evidence.extend(entries)
  diagnostic=f in ['capital_accounting','early_financial'];families.append(dict(family=f,name=title,original_status=original['status'],coverage='state_diagnostic_training_history_insufficient' if diagnostic else 'frozen_fit_and_applicable_economic_evaluation_performed',evidence_rounds=rounds,evidence=evidence,conclusion=conclusion,adoption=False,full_evaluation_complete=False,limitations=['Historical-proxy remains','No execution or prospective certification']+(['No trained regime model; six observation periods'] if diagnostic else ['Qualification failures and path gaps remain','Separate process/lead-time and family-specific stability boundaries remain'])))
 js(out/'family_catalog.json',dict(scope=reg['scope'],source_registry_sha256=digest(source),families=families,first_pass_scope_covered=True,full_evaluation_complete=False,adoption=False,default_release_unchanged='R183 with R184 replay; this audit does not publish or deploy'))
 # Snapshot actual summary counts rather than transcribe report prose.
 snapshots={}
 for rnd in [207,208,209,222,223]:
  path=ROOT/f'outputs/r{rnd}/verification.json';snapshots[str(rnd)]=dict(receipt_sha256=digest(path),receipt=json.loads(path.read_text()))
 js(out/'summary_evidence.json',snapshots)
 bad=[x for x in checks if x['status']!='match'];js(out/'verification.json',dict(status='PASS' if not bad else 'REVIEW_REQUIRED',families=len(families),fit_or_qualification_families=14,short_history_diagnostic_families=2,receipt_count=len(receipts),hash_checks=len(checks),hash_matches=len(checks)-len(bad),issues=bad,distinct_hashed_files=len(hashes),scope='Declared hash dictionaries and R195 lineage only; does not replace semantic verifiers, certify arbitrary self-hash fields or complete whole EP35',adoption=False,inputs={str(source):digest(source),str(ROOT/'protocols/r230.json'):digest(ROOT/'protocols/r230.json'),str(Path(__file__)):digest(Path(__file__))},outputs={x:sha(out/x) for x in ['hash_audit.csv','receipt_inventory.json','family_catalog.json','summary_evidence.json']}));print('families',len(families),'receipts',len(receipts),'checks',len(checks),'issues',len(bad));print(json.dumps(bad[:12],ensure_ascii=False,indent=2))
if __name__=='__main__':run()

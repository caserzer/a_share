from common import *
CONFIG={
 'core_three_tasks':([210,221,223,227,228,229,236,237],'不统一采用','反转标签召回局部改善，但退出价值、启动过程和成本后排序未统一改善','独立成熟样本且保留原标签/成本；状态校准支持单独证明'),
 'l1_three_tasks':([196,224,232,233],'收益分支不采用；分类证据不足','实际regime输出只有收益，旧未校准一级分类不能替代','新增成熟训练及校准样本满足原门槛'),
 'rank_target':([196,210,223,236,237],'不采用','排名目标局部改进没有普遍成本后优势，名义集中风险仍在','保留原收益/排名基准的独立时间验证'),
 'market_style':([199,211,226,236,237],'不采用','交互与风格控制效果分化，部分下跌日改善不能替代全日收益','新样本下相同控制/成本与方向风险复核'),
 'battery':([198,218,225],'证据不足，不采用','单行业20日正负混合，历史不足以验证稳定，分类资格未过','原行业连续变量及标签继续成熟，不降低分类门槛'),
 'eps_expectations':([197,215,223],'不采用','胜交互价格控制不代表胜原价格基准，部分覆盖限制保留','固定预测年度和首次修订链更完整，独立样本对原价格基线'),
 'size_diffusion':([199,211,226,236,237],'不采用','局部机制差异存在，持续成本/风险优势未证明','同母体原价格/规模控制与新时期检验'),
 'financing':([199,211,226,232],'证据不足，不采用','窄历史分支与状态校准缺口，不能外推全行业','连续时点一致融资数据及更多成熟年，原资格不变'),
 'profit_events':([205,219,225],'不采用','事件机制交互增量偏弱，合格时间区间未确立稳定优势','原事件时钟和独立修订证据，新样本及同事件控制'),
 'leader_catchup':([200,212,213,225,226,236,237],'不采用，保留局部风险线索','龙头反转局部改善；追赶完整成员路径少，组合收益与集中度约束仍在','同原成员完整股票路径及独立时期，保留两侧成本'),
 'financial_dual_clock':([201,214,223,237],'证据不足，不采用','窄公告母体相对自身改善，财务相对控制仍未建立价值','公告/更新双时钟与全行业覆盖及更长成熟样本'),
 'capital_accounting':([206,232],'无合格模型，保留机制诊断','六期历史不足，不能以零或拟合代理制造结果','原18月等训练条件满足且会计口径可追溯'),
 'macro_interaction':([202,217,223,234],'不采用','45/75日时钟和时期敏感，不能挑较优时钟宣传','首发宏观时钟与独立时期，保留两个代理时钟对照'),
 'profit_expectations':([197,215,223],'保留观察线索，不采用','八期局部正收益不足以证明稳定独立增量','固定年度预期继续成熟并扩展覆盖，对原价格基准验证'),
 'early_financial':([203,232],'无合格模型，保留诊断','六期观察不能训练年度历史门槛模型','更多前期成熟财务观察及原时点证据'),
 'fixed_factor_rank':([204,216,223,237],'不采用','相对弱校准base改善不能替代原fixed；集中下降也不等于收益增量','原规则为主基准，新时期验证，不优化持仓数')}
def run():
 out=ROOT/'outputs/r238';out.mkdir(exist_ok=True);registry=json.loads((ROOT/'outputs/r195/experiment_registry.json').read_text());assert set(CONFIG)=={x['family'] for x in registry['families']};decisions=[];checks=[]
 for name,(rounds,decision,reason,reopen) in CONFIG.items():
  evidence=[]
  for rnd in rounds:
   p=ROOT/f'outputs/r{rnd}/verification.json';assert p.is_file();data=json.loads(p.read_text());assert data['status']=='PASS';evidence.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
   for role in ['inputs','outputs','reads']:
    for ref,digest in data.get(role,{}).items():
     if not isinstance(digest,str) or len(digest)!=64:continue
     path=Path(ref)
     if not path.is_absolute():path=ROOT/path if ref.startswith(('outputs/','src/','data/','protocols/')) else p.parent/path
     assert sha(path)==digest;checks.append(dict(receipt=str(p.relative_to(ROOT)),reference=ref,sha256=digest))
  decisions.append(dict(family=name,decision=decision,reason=reason,reopen_evidence=reopen,adoption=False,stop_unsupported_parameter_search=True,evidence=evidence))
 js(out/'branch_decisions.json',dict(scope='All16 families; decisions are evidence assessments, not proof true effect is zero',branches=decisions,whole_goal_complete=False))
 prior=json.loads((ROOT/'outputs/r230/requirements_audit.json').read_text());prior['revision']='R238';prior['status']='active_not_complete';prior['full_completion_proven']=False
 for item in prior['items']:
  additions=[]
  if item['id']=='R13':item['verified_scope']+=' R231独立regime字典扩展已交付，原字典未改。';item['unresolved']='原69项完整定义、未覆盖经济变量及首次发布修订证据仍不足。';additions=[231]
  if item['id']=='R14':item['verified_scope']+=' R232–R235全分支资格/实际模型关联与明确日期读取样例完成。';additions=[232,233,234,235]
  if item['id']=='R15':item['verified_scope']+=' R231状态CLI及R235全16类历史样例已实现。';item['unresolved']='全模型读取仍是单日期固定脚本，需可复用显式日期入口和前后变化/遗漏对照；真实增量数据、前瞻和生产未完成。';item['next_dependency']='local_engineering_and_data';additions=[231,235]
  if item['id']=='R05':item['verified_scope']+=' R236方向风险、R237成员名义集中与重叠已补齐。';additions=[236,237]
  item['latest_extension_evidence']=[dict(path=f'outputs/r{n}/verification.json',sha256=sha(ROOT/f'outputs/r{n}/verification.json')) for n in additions]
 prior['next_local']=[dict(priority=1,task='Reusable explicit-date research archive view and two-date change/omission comparison',basis='Goal monitoring requires historical changes; R235 fixed-date snapshot is insufficient',boundary='Existing local frozen sources only; distinguish retrospective evidence from as-of data; no refit, scheduler or deployment')];js(out/'requirements_audit.json',prior)
 js(out/'verification.json',dict(status='PASS',families=len(decisions),requirements=len(prior['items']),declared_source_hash_checks=len(checks),scope='Exact original family coverage and cited receipt/source integrity; not independent statistical proof',inputs={str(ROOT/'outputs/r230/requirements_audit.json'):sha(ROOT/'outputs/r230/requirements_audit.json'),str(ROOT/'outputs/r195/experiment_registry.json'):sha(ROOT/'outputs/r195/experiment_registry.json'),str(ROOT/'protocols/r238.json'):sha(ROOT/'protocols/r238.json'),str(Path(__file__)):sha(__file__)},outputs={f:sha(out/f) for f in ['branch_decisions.json','requirements_audit.json']},adoption=False));print(len(decisions),len(checks))
if __name__=='__main__':run()

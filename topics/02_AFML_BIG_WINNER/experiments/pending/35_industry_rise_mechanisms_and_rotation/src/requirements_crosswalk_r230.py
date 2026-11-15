from pathlib import Path
import json,hashlib
r=Path('/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation');o=r/'outputs/r230'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((r/'outputs/r183/requirements_audit.json').read_text());checks=[]
for item in old['items']:
 for e in item['evidence']:
  actual=sha(r/e['path']);assert actual==e['sha256'];checks.append({'path':e['path'],'sha256':actual})
updates={
'R01':([209,225,226],'同状态机制增量和行动时间资格已补齐；没有独立因果认证。','经济变量首发/修订链、非价格持续性与未使用样本仍不足。'),
'R02':([221,227],'全部可用regime启动模型的行动与月度价格过程已评价。','月度参考事件目录不等于所有经济启动；日频regime及独立前瞻未认证。'),
'R03':([228],'提示后5/20/60日及20至60日新增表现已重建，收益/回撤取舍保留。','产业及盈利兑现持续性未知；条件成功不能在提示时获知。'),
'R04':([220,226,229],'退出成本、机制增量及原起点回撤首次越阈时间已评价。','起点标签非去重反转过程；更早提示及真实退出收益未证实。'),
'R05':([223,225],'组合与特殊区间经济价值分别评价；无统一稳定采用证据。','指数/篮子到可投资映射、价格缺口与冲击许可仍不足。'),
'R06':([196,224],'16类全范围登记；一级实际输出为收益，分类资格失败保留。','不能用二三级分类或一级未校准旧模型替代缺失的合格regime分类。'),
'R07':([216],'固定排序regime保持原规则对照，未假称原文完整复现。','方正完整原文、69项及双拥挤精确定义仍未核验。'),
'R08':([216,223],'固定分数与原始fixed对照及成本/时间资格已检验。','稳定独立增量尚未建立；不继续无依据参数搜索。'),
'R09':([215,219,225],'EPS/利润预期及事件的收益行动与稳定性已适配评价。','窄母体、八期利润预期及首发修订历史限制保留。'),
'R10':([218,225],'装车量原行业选择行动与稳定性资格已评价。','分类训练资格不足，连续其它产业变量仍缺。'),
'R11':([224,226,227,228,229],'原冻结三任务覆盖、分类行动、过程与持续性证据可索引。','一级/60日分类缺失及前瞻未完成；不以旧数据重跑冒充新样本。'),
'R12':([224,230],'全范围目录与本轮显式哈希审计，旧需求证据原样核查。','来源可追溯不等于严格PIT，缺失首次发布链未补齐。'),
'R13':([195],'regime定义已有冻结协议，但原28项字典尚无独立regime扩展交付。','需将趋势/波动状态、可知时点、编码及适用边界写入版本化扩展字典。'),
'R14':([224,230],'全部16类实验范围及新增行动/过程结果统一索引。','受资格限制的分支仍无拟合，稳定成本后可执行价值未证明。'),
'R15':([184,230],'R184本地显式截点历史重放入口已完成并核验；修正R183旧待办。','regime研究监控字段尚未接到版本化本地交付；增量源及前瞻监控未认证。'),
'R16':([230],'新增失败、协议、结果、核验、报告与当前索引留存。','继续有依据的交付工程与明确数据缺口；无须逐轮重复征求授权。')}
for item in old['items']:
 rounds,scope,gap=updates[item['id']];item['prior_verified_scope']=item['verified_scope'];item['verified_scope']=scope;item['unresolved']=gap;item['completion_proven']=False;item['regime_evidence']=[]
 for n in rounds:
  path=r/f'outputs/r{n}/verification.json'
  if not path.exists():
   candidates=sorted((r/f'outputs/r{n}').glob('*receipt*.json'));path=candidates[0] if candidates else r/f'protocols/r{n}.json'
  assert path.is_file();item['regime_evidence'].append({'path':str(path.relative_to(r)),'sha256':sha(path)})
old.update(revision='R230',status='active_not_complete',full_completion_proven=False,scope='Full16 prior requirements preserved, updated with regime evidence; integrity checks are not semantic completeness',next_local=[{'priority':1,'task':'Versioned regime factor dictionary extension and machine-readable monitoring contract','reason':'R195 freezes model state but original dictionary and monitored fields need explicit lifecycle/known_at/unknown boundaries','boundary':'local research only; no scheduler/deployment or automatic model adoption'}])
old['explicit_target_crosswalk']={'five_questions':['R01','R02','R03','R04','R05'],'three_tasks':{'onset':['R02','R11'],'relative_return':['R05','R08','R11','R14'],'reversal':['R04','R11']},'three_priorities':['R08','R09','R10'],'four_deliverables':{'factor_dictionary':['R13'],'industry_dataset':['R12'],'model_framework':['R11','R14'],'monitoring_delivery':['R15']}}
(o/'requirements_audit.json').write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n');(o/'prior_requirements_hash_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
rem={'goal_complete':False,'completed_evaluation_work':[{'id':'event_action_stability','evidence':'R225'},{'id':'classifier_mechanism_action','evidence':'R226'},{'id':'monthly_price_process','evidence':'R227'},{'id':'onset_path_persistence','evidence':'R228'},{'id':'origin_relative_breach_timing','evidence':'R229'}],'local_executable':['Versioned regime dictionary extension','Read-only research monitoring contract with source dates, state support, missingness and adoption boundary'],'not_certified':['Independent economic phases and causal attribution','Unique reversal processes / daily regime early warning','Untouched prospective validation','Strict PIT and missing upstream series','Tradable portfolios and production monitoring']};(o/'remaining_work.json').write_text(json.dumps(rem,ensure_ascii=False,indent=2)+'\n')
print('prior evidence',len(checks),'requirements',len(old['items']))

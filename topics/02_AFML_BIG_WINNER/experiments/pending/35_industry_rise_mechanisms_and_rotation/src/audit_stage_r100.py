"""Stage audit: evidence routing and explicit unresolved work, never automatic completion."""
import copy
from common import *
UPDATES={
 '何时启动：领先与及时性':('R97—R99日频校准、固定提示及时间区块评价完成；近期四折误差区间跨零，2021召回/提前量/负担有取舍，未采纳新版本。经济启动与真正前瞻仍未证明。',list(range(97,100))),
 '上涨持续性':('R93—R96联接提示前经营期、保留当前/旧期和未知；共同日期仅少量、事前价格不平衡，不建立持续性增量。R90兑现不等于价格领先。',list(range(93,97))),
 '三类任务冻结协议和时序验证':('三任务冻结与原月历误差评价存在；R97—R99仅补启动日频校准，不能外推收益与反转。跨层级稳定增量、可靠校准及独立前瞻仍缺。',[97,98,99]),
 '多模型完整结果与消融成本交付':('冻结预测及局部消融有完整结果，最新校准不自动替换。仍缺已证明的全目标增量、可交易成本风险和独立期归因。',[97,98,99]),
 '行业监控与更新流程':('R93已按精确键联接12264任务记录，R94分开最新已观察期与当前季度。R18仅版本化价格分数，R22读取已有预测；三任务模型/输入/推断共同封存的更新流程仍未实现，可在现有本地源上继续。',[93,94]),
 '数据可追溯与PIT补充':('R93—R99已核验时钟、原值保留、成熟标签和冻结模型；历史代理不是首次发布PIT，既有源修订/身份/交易缺口保留。',list(range(93,100))),
 '失败尝试及持续研究记录':('R93—R99全部尝试及核验修正已记录；短财报比较和校准变体搜索分支收束。研究日志继续，整体目标未完成。',list(range(93,100)))
}
def run():
 out=ROOT/'outputs/r100';out.mkdir(exist_ok=True);prior=ROOT/'outputs/r92/requirements_evidence.json';a=copy.deepcopy(json.loads(prior.read_text()));evidence=[]
 for x in a['items']:
  x['completion_proven']=False
  if x['requirement'] in UPDATES:
   message,rounds=UPDATES[x['requirement']];x['unresolved_at_R92']=x['unresolved'];x['unresolved']=message
   known={e['path'] for e in x['evidence']}
   for n in rounds:
    p=f'outputs/r{n}/verification.json';assert json.loads((ROOT/p).read_text())['status']=='PASS'
    if p not in known:x['evidence'].append(dict(path=p,exists=True,sha256=sha(ROOT/p)))
  for e in x['evidence']:assert sha(ROOT/e['path'])==e['sha256']
 a['overall_status']='active_not_complete';a['interpretation']='R100 stage audit; no overall requirement proven by artifact existence or a green test alone';js(out/'requirements_evidence.json',a)
 paths=[ROOT/'src/versioned_observations.py',ROOT/'src/task_monitor_r22.py',ROOT/'src/integrated_monitor_r93.py',ROOT/'src/disclosed_period_r94.py'];gap=dict(id='versioned_three_task_inference',status='executable_local_engineering_gap',owning_evidence=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in paths],finding='R18 snapshots price_score/rank only; R22 reads stored prediction tables; R93/R94 join evidence but do not bind model, feature snapshot and new inference in a versioned bundle',next_action='Register an immutable three-task historical inference bundle using frozen models and exact-date source snapshots; independently reproduce original formal outputs and reject absent/stale/uncalibrated inputs; no network or deployment',not_proven_by_this_action='predictive value, full update source acquisition, strictPIT, future calibration or executable investment returns');js(out/'executable_gap.json',gap)
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());current['selected']['latest_stage_requirements_audit']=dict(path='outputs/r100/requirements_evidence.json',sha256=sha(out/'requirements_evidence.json'));js(ROOT/'outputs/current_sources.json',current)
 objective=Path('/home/xiaolv/.codex/attachments/fee38065-f5c6-49e0-9ab4-ae5d818c0c23/goal-objective.md');js(out/'receipt.json',dict(objective_path=str(objective),objective_sha256=sha(objective),prior_requirements_sha256=sha(prior),code_sha256=sha(Path(__file__)),requirements=16,completed_requirements=0,next_gap=gap['id'],audit_scope='stage evidence reconciliation; not a full completion certificate'));print('R100 stage audit:16 incomplete requirements; concrete local inference gap')
if __name__=='__main__':run()

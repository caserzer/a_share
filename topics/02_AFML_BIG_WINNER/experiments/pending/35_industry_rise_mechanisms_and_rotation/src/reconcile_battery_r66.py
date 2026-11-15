"""Promote reviewed R60-R65 evidence while retaining previous versions."""
import copy
from common import *
ROUTES={'current_factor_dictionary':'outputs/r66/current_factor_dictionary.json','latest_battery_series':'outputs/r60/frozen_monthly_series.json','latest_battery_return_pilot':'outputs/r64/metrics.json','battery_source_completion_pilot':'outputs/r62/metrics.json','latest_battery_classification_gates':'outputs/r65/fold_ledger.json','complete_battery_historical_monitor':'outputs/r63/evidence_matrix.parquet'}
REFS=['outputs/r60/verification.json','outputs/r61/verification.json','outputs/r62/verification.json','outputs/r62/impact_verification.json','outputs/r63/verification.json','outputs/r64/verification.json','outputs/r64/cohort_audit.json','outputs/r65/verification.json']
def run():
 out=ROOT/'outputs/r66';out.mkdir(exist_ok=True);source=ROOT/'outputs/r58/current_factor_dictionary.json';rows=copy.deepcopy(json.loads(source.read_text()))
 b=next(x for x in rows if x['factor']=='china_power_battery_installation_log_yoy')
 b.update(economic_date='2020-01至2026-09完整81月；69个同比',source='R38授权原文字节，R60人工复核完整月度网格；旧R40/R51保留',conclusion='R62补数后主20日二/三级均未改善；R64加入市场Beta/特异波动后仍未建立主期限增量。20日各20月、60日各18月，仅2年。R65分类40折均未满足训练校准门槛，属证据不足而非分类无效。',dictionary_origin='R38-R65',monitor_scope='R63重放两个历史截面，6行同比由未知变可得；不改变排名、阶段、概率或配置，无生产部署',strict_pit_certified=False)
 b['evidence_refs']+=REFS;b['evidence_sha256']={p:sha(ROOT/p) for p in b['evidence_refs']};js(out/'current_factor_dictionary.json',rows)
 a=copy.deepcopy(json.loads((ROOT/'outputs/r58/requirements_evidence.json').read_text()))
 for x in a['items']:
  x['completion_proven']=False
  if x['requirement'] in ['产业领先变量优先实验','数据可追溯与PIT补充','行业监控与更新流程','三类任务冻结协议和时序验证']:
   x['status_at_R58']=x['status'];x['unresolved_at_R58']=x['unresolved']
   x['evidence'] += [dict(path=p,exists=True,sha256=sha(ROOT/p)) for p in REFS]
  if x['requirement']=='产业领先变量优先实验':x.update(status='complete_battery_grid_fixed_controls_tested_classification_insufficient',unresolved='81月/69同比已补齐；收益未建立稳定增量，分类40折不足。仍缺其它产业机制、利润价差库存供给链、首发修订和独立前瞻；不得调参制造通过。')
  if x['requirement']=='行业监控与更新流程':x['unresolved']='R63完整装车量接入冻结历史监控；实时来源、完整阶段识别和前瞻验证未完成。'
  if x['requirement']=='数据可追溯与PIT补充':x['battery_progress']='R60原文日期和引用逐条核验，保守可用代理；不是首次发布链认证。R59 ETF仅16观测/6产品且缺行业映射，不足连续资金因子。'
  if x['requirement']=='三类任务冻结协议和时序验证':x['battery_progress']='R64收益受控试验完成；R65独立启动/反转门槛审计完成，未训练概率；不将收益结论外推。'
 a['interpretation']='R66 current routing and research evidence, all16 overall requirements remain unproven';js(out/'requirements_evidence.json',a)
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())
 for key,path in ROUTES.items():current['selected'][key]=dict(path=path,sha256=sha(ROOT/path))
 current['pending']='Battery grid complete for authorized interval, no stable primary increment; classification insufficient. Other industrial mechanisms, original report definitions, first release revisions, full styles, tradability and forward validation remain open.';js(ROOT/'outputs/current_sources.json',current)
 js(out/'receipt.json',dict(previous_dictionary_sha256=sha(source),dictionary_sha256=sha(out/'current_factor_dictionary.json'),entries=len(rows),amended=['china_power_battery_installation_log_yoy'],routes=ROUTES,code_sha256=sha(__file__),status='active_not_complete'))
 print('R66 reconciled',len(rows),'entries; six current routes')
if __name__=='__main__':run()

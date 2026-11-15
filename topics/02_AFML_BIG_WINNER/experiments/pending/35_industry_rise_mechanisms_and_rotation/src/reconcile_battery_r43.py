"""Version the current evidence dictionary after the battery pilot; no promotion."""
import copy
from common import *

def run():
 out=ROOT/'outputs/r43';out.mkdir(exist_ok=True);source=ROOT/'outputs/r34/current_factor_dictionary.json';rows=copy.deepcopy(json.loads(source.read_text()));b=copy.deepcopy(next(x for x in rows if x['factor']=='industry_spread_inventory'))
 b.update(factor='china_power_battery_installation_log_yoy',theory='国内动力电池装车量代理已兑现需求；量增须通过价格、成本和供给条件才能转为利润',formula='log(V_m/V_(m-12)); V为原文国内动力电池当月总装车量GWh',direction='机制预期正向，模型允许反证；不预设上下游同号',applicable_industries='仅SW2021二级电池801737.SI与三级锂电池857371.SI，分别研究',economic_date='月度经济所属期2020-01至2026-09，R40覆盖68个月',publication_date='原文页面显示日期或经核元数据；转载日非联盟首发认证',available_at='分子分母页日较晚者的下一日00:00；信号日不早于该时间；经济月份年龄<=2月',frequency='月',source='R38授权公开原文字节归档；R40冻结68个月/48个同比',historical_revisions='首发及修订链未认证，当前下载转载页面为Historical-proxy',aggregation='全国总装车量；不汇总企业份额反推；同一变量映射两个行业但不合并计独立样本',missing_rule='两期任一缺失即同比未知；无可得或过时变量不入同样本比较',failure_condition='低基数、降价、产能过剩、库存、出口与国内口径差异、利润转化失败、价格已提前反映',replication_status='EP35产业扩展；非方正原69因子复现',horizon='主20日/次60日；分类沿原框架资格不满足',dictionary_origin='R38-R42',implemented='historical_proxy_tested_partial_coverage',conclusion='R41主20日无稳定增量：二级微改、三级恶化且均不如均值；次60日有限，全部稳定性样本门槛未达。R42分类40折不合原框架门槛，非分类无效证明',mechanism_status='需求代理假说；未证明因果、利润传导或独立前瞻预测',monitor_scope='仅本地研究输入与历史试验，未接入生产排名或阶段概率',strict_pit_certified=False,evidence_refs=['protocols/r40.json','outputs/r40/verification.json','protocols/r41.json','outputs/r41/metrics.json','outputs/r41/verification.json','protocols/r42.json','outputs/r42/classifier_gates.json','outputs/r42/verification.json','reports/R42_装车量先后关系与分类资格.md'])
 b['evidence_sha256']={ref:sha(ROOT/ref) for ref in b['evidence_refs']};rows.append(b);js(out/'current_factor_dictionary.json',rows)
 audit=copy.deepcopy(json.loads((ROOT/'outputs/r34/requirements_evidence.json').read_text()))
 notes={
 '产业领先变量优先实验':('R40连续部分序列及R41收益试验已执行；R42关联/分类资格已审计，尚无稳定主期限增量',['outputs/r40/verification.json','outputs/r41/verification.json','outputs/r42/verification.json']),
 '经济假说与完整因子字典交付':('新增装车量同比第18条；不改变价差/订单/库存因子的缺失状态',['outputs/r43/current_factor_dictionary.json']),
 '何时启动：领先与及时性':('产业子样本启动正例少，原跨行业校准框架结构不适用；未输出产业概率',['outputs/r42/class_prevalence.json','outputs/r42/classifier_gates.json']),
 '何时结束：风险和错误退出':('产业子样本反转原校准门槛未满足，不能用收益试验代替',['outputs/r42/classifier_gates.json']),
 '数据可追溯与PIT补充':('授权采集、源文哈希与独立冻结序列已补充；首发修订尚未认证',['outputs/r40/coverage_summary.json']),
 }
 for item in audit['items']:
  if item['requirement'] in notes:
   note,refs=notes[item['requirement']];item['latest_progress']=note
   item['evidence'] += [dict(path=ref,exists=True,sha256=sha(ROOT/ref)) for ref in refs]
  item['completion_proven']=False
 audit['interpretation']='R43 updates partial battery research evidence; existing unresolved scope remains; no whole-goal completion or PIT promotion';js(out/'requirements_evidence.json',audit)
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());current['selected']['current_factor_dictionary']=dict(path='outputs/r43/current_factor_dictionary.json',sha256=sha(out/'current_factor_dictionary.json'));current['selected']['battery_partial_series']=dict(path='outputs/r40/frozen_monthly_series.json',sha256=sha(ROOT/'outputs/r40/frozen_monthly_series.json'));current['selected']['battery_return_pilot']=dict(path='outputs/r41/metrics.json',sha256=sha(ROOT/'outputs/r41/metrics.json'));current['pending']='R40-R42 battery partial-series pilot completed without stable primary-horizon increment; industry classification calibration design, first-release revisions, other industry mechanisms, complete styles, investability and prospective validation remain open';js(ROOT/'outputs/current_sources.json',current)
 js(out/'receipt.json',dict(previous_dictionary_sha256=sha(source),dictionary_sha256=sha(out/'current_factor_dictionary.json'),entries=len(rows),new_factors=1,strict_pit_promotions=0,code_sha256=sha(__file__),overall_status='active_not_complete'))
 print('R43 reconciled',len(rows),'factors; overall goal remains active')

if __name__=='__main__':run()

"""Current research dictionary and evidence routing after R50-R57."""
import copy
from common import *

def run():
 out=ROOT/'outputs/r58';out.mkdir(exist_ok=True);source=ROOT/'outputs/r49/current_factor_dictionary.json';rows=copy.deepcopy(json.loads(source.read_text()));by={x['factor']:x for x in rows}
 battery=by['china_power_battery_installation_log_yoy'];battery.update(economic_date='月度所属期2020-01至2026-09，R51覆盖69个月',source='R38授权原文字节；R51独立冻结69月/50同比，R40旧68月保留',conclusion='R53固定重跑主20日二级微改善/三级恶化、均不如均值，16日期/2年仍不足稳定性；R42分类资格结论保留',dictionary_origin='R38-R53',monitor_scope='R50历史监控采用R40冻结版；R51/R53新数据试验另列，未替换生产排名')
 battery['evidence_refs']+=['outputs/r51/verification.json','outputs/r52/verification.json','outputs/r53/verification.json','outputs/r53/impact_verification.json','outputs/r53/metrics.json']
 breadth=by['breadth21/breadth63'];breadth.update(conclusion='R55加入规模/Beta/残差波动后主20日五组IC区间全跨0；R56八组分类增量区间跨0；R57固定退出不如持有；停止无依据参数搜索',mechanism_status='价格参与范围；不等同因果经济扩散',dictionary_origin='R01-R57')
 breadth['evidence_refs']+=['outputs/r55/verification.json','outputs/r55/metrics_verification.json','outputs/r56/verification.json','outputs/r57/verification.json']
 finance=by['industry_financing_balance_intensity'];finance['monitor_scope']='R50历史监控只显示最后观测及陈旧状态，当前因子不前填；无生产接入';finance['evidence_refs']+=['outputs/r50/verification.json']
 template=by['typical_member_log_market_cap']
 for factor,formula,theory in [('market_beta126','cov(r行业,r市场)/var(r市场)，126配对单交易日收益、含截距OLS','控制共同市场敏感度，不预设正向收益'),('residual_vol126','sqrt((var(r行业)-cov(r行业,r市场)^2/var(r市场))*252)，ddof1','控制市场无法解释的波动，非风险预警概率')]:
  row=copy.deepcopy(template);row.update(factor=factor,theory=theory,formula=formula,direction='共同控制变量，无固定配置方向',applicable_industries='SW2014/SW2021各层级单独，以同一区段127连续市场日价格可得为限',economic_date='截至信号日收盘的126日收益',publication_date='收盘价格；重建NAV/成分首发修订未认证',available_at='信号收盘可计算，后续标签次日收盘入场；历史代理',frequency='月末采样',source='冻结industry daily NAV和CSI_ALL，R54构造',historical_revisions='继承历史成分及复权/NAV重建边界，无完整首次版本',aggregation='行业收益对市场收益滚动OLS；模型同日同层共同样本秩、训练标准化',missing_rule='需127连续市场交易日、同block、正行业价与正市场方差；无填充',failure_condition='成员修订/断档/短历史/结构变化；不能替代价值成长盈利流动性全风格',implemented='historical_proxy_control',conclusion='R54构造核验；R55-R57作为共同控制，无独立因果或稳定配置能力声明',mechanism_status='必要替代解释控制',replication_status='EP35市场暴露控制，非原69项完整复现',dictionary_origin='R54-R57',monitor_scope='研究模型输入，未改价格排名或生产监控',strict_pit_certified=False,evidence_refs=['protocols/r54.json','outputs/r54/verification.json','protocols/r55.json','outputs/r55/verification.json','protocols/r56.json','outputs/r56/verification.json','protocols/r57.json','outputs/r57/verification.json']);rows.append(row)
 for x in rows:x['evidence_sha256']={ref:sha(ROOT/ref) for ref in x['evidence_refs']}
 js(out/'current_factor_dictionary.json',rows)
 audit=copy.deepcopy(json.loads((ROOT/'outputs/r49/requirements_evidence.json').read_text()))
 for item in audit['items']:
  item['completion_proven']=False
  item['status_at_R49']=item['status'];item['remaining_at_R49']=item['unresolved']
  if item['requirement']=='产业领先变量优先实验':
   item.update(status='partial_battery_series_and_fixed_pilot_tested',unresolved='R51补至69月/50同比；R53固定收益试验仍无稳定主期限增量。仍缺其它产业机制、价差库存供给链、单行业分类校准设计及首发修订；不是等待本轮采集授权。')
  if item['requirement']=='经济假说与完整因子字典交付':item.update(status='21_entry_dictionary_with_partial_controls',unresolved='现行21条；完整69项定义、其它模块可比序列与独立验证仍缺')
  if item['requirement']=='行业监控与更新流程':item['unresolved']='R50历史监控已连接冻结产业/融资与陈旧状态；R51与R53新版本另列。仍缺完整阶段识别、实时新来源更新及前瞻验证。'
  if item['requirement'] in ['基准因子增量优先实验','何时启动：领先与及时性','何时结束：风险和错误退出','多模型完整结果与消融成本交付','经济假说与完整因子字典交付']:
   item['market_control_progress']='R54-R57市场Beta/残差波动与三任务、固定退出完成；稳定增量未建立，仍非完整风格'
   item['evidence'] += [dict(path=ref,exists=True,sha256=sha(ROOT/ref)) for ref in ['outputs/r54/verification.json','outputs/r55/metrics_verification.json','outputs/r56/verification.json','outputs/r57/verification.json']]
 audit['interpretation']='R58 current evidence; historical statuses retained separately; all16 overall requirements unproven';js(out/'requirements_evidence.json',audit)
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())
 for key,path in {'current_factor_dictionary':'outputs/r58/current_factor_dictionary.json','latest_battery_series':'outputs/r51/frozen_monthly_series.json','latest_battery_return_pilot':'outputs/r53/metrics.json','market_exposure_controls':'data/r54_market_controls.parquet','market_control_return_metrics':'outputs/r55/increments.csv','market_control_classifier_metrics':'outputs/r56/increments.csv','market_control_exit_metrics':'outputs/r57/summary.csv'}.items():current['selected'][key]=dict(path=path,sha256=sha(ROOT/path))
 current['pending']='Partial market controls and battery/financing experiments tested without stable primary increment; other industry mechanisms, ETF/fund allocations, complete style controls, original first releases/revisions, tradability and prospective validation remain open';js(ROOT/'outputs/current_sources.json',current)
 js(out/'receipt.json',dict(previous_sha256=sha(source),dictionary_sha256=sha(out/'current_factor_dictionary.json'),entries=len(rows),amended_prior_factors=['breadth21/breadth63','china_power_battery_installation_log_yoy','industry_financing_balance_intensity'],new_factors=['market_beta126','residual_vol126'],code_sha256=sha(__file__),status='active_not_complete'))
 print('R58 reconciled',len(rows),'factors')
if __name__=='__main__':run()

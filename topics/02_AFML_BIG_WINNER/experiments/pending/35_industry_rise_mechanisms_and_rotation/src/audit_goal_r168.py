from pathlib import Path
import json,hashlib
from common import ROOT
r=ROOT
old=json.loads((r/'outputs/r124/requirements_evidence.json').read_text());old=old.get('requirements',old.get('items'))
release=json.loads((r/'outputs/r167/release.json').read_text());routes=release['routes']
rows=[
(['macro_repair_comparison','leader_repair_evidence','financial_repair_evidence','capital_repair_evidence'],'已执行宏观、龙头、财务与资本代理固定对照；无可靠机制认证。','连续价差/库存/产能和首次发布修订证据仍缺；相关与预测不证明因果。','data_and_prospective'),
(['daily_process_summary','daily_calibration_uncertainty','l1_process_uncertainty'],'二三级日频及一级原始启动过程已评价；稳定增量未证实。','经济启动及独立前瞻未知，一级原校准门槛未通过。','prospective'),
(['alert_followup_summary','conditional_continuation'],'二三级跟踪已修复；本轮补齐一级5/20/60跟踪及条件延续。','需同母体原基准的一级延续对照，条件成功不能作当时预测。','local_comparison'),
(['market_control_exit_metrics','reversal_exit_economics','l1_raw_reversal_exits'],'二三级退出和一级60日原始风险退出已评价。','一级仅6成熟月且未校准；实际退出成交及独立样本未知。','data_and_prospective'),
(['synthetic_portfolio_summary'],'修复版合成组合完成；完整实股路径仍不足。','需成交、停牌/退市、成本冲击、完整相关及风格风险证据；不能拼完整实盘曲线。','data'),
(['three_task_prediction_evaluation','l1_raw_onset_process','l1_raw_reversal_exits'],'一级、二级、三级分别有历史任务记录；一级原始与校准结果分开。','一级校准和跨年风险稳定性不足；不能互相外推。','prospective'),
(['fixed_rank_evaluation'],'已记录官方摘要与现有代理差异，完整69项原文定义未确认。','二级前10简化基准为可执行遗漏；完整五类、双拥挤、开盘源仍缺。','local_comparison_and_data'),
(['fixed_rank_evaluation','market_control_return_metrics'],'固定价格及控制对照已修复；无稳定增量。','先补有依据的二级前10对应比较，不继续参数与模型搜索。','local_comparison'),
(['expectation_repair_evidence','event_repair_evidence','profit_expectation_repair','forecast_horizon_price_comparison'],'EPS、利润预期、固定年度与兑现价格比较已修复。','有限覆盖和源语义/修订时点不足，不证明普遍领先。','data_and_prospective'),
(['battery_source_completion_pilot','latest_battery_classification_gates'],'81月装车量和69同比来源已齐；收益对照无稳定增量，分类门槛不足。','仍缺其它产业连续变量和修订首发链；不降低样本门槛。','data_and_prospective'),
(['three_task_price_models','three_task_prediction_evaluation','l1_onset_calibration_gates'],'三任务有独立定义及时间验证；未通过的折和校准门槛保留。','成熟样本、全市场独立验证与未使用时期不足。','prospective'),
(['corrected_daily_baskets','corrected_monthly_panel','financing_industry_factor'],'身份/区块/成员/价格已修复；来源与哈希可核对。','历史归档与首次发布不完整；ETF16条快照10区间中0条流量合格。','data'),
(['versioned_factor_dictionary'],'28项原定义与时点/缺失/反证保存，两项财务修复状态更新。','不是28个有效因子；原69项完整定义和候选变量仍有限。','data'),
(['three_task_prediction_evaluation','market_control_return_metrics','market_control_classifier_metrics','synthetic_portfolio_summary'],'各任务与控制消融、成本失败已保留，可重跑。','真实可执行成本和独立样本能力未成立；本地必要遗漏仍需补。','local_comparison_and_data'),
(['versioned_historical_inference','three_task_model_explanations','integrated_historical_task_evidence'],'历史511行业网格、12264任务状态与解释可读取，入口R167。','仅历史快照与本地重放；新行情上游更新和前瞻未证实，生产需另行授权。','engineering_and_data'),
(['early_financial_repair','l1_raw_reversal_exits'],'持续日志保留失败与修复，本轮增加目标审计与一级延续。','记录存在不表示整体完成；下一项先二级前10简化基准。','ongoing')]
items=[]
for i,(keys,done,gap,kind) in enumerate(rows):
 refs=[]
 for k in keys:
  v=routes[k];p=r/v['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'];refs.append(dict(route=k,path=v['path'],sha256=v['sha256']))
 items.append(dict(id=f'R{i+1:02}',requirement=old[i]['requirement'],verified_scope=done,unresolved=gap,next_dependency=kind,completion_proven=False,evidence=refs))
extras=['outputs/r168/verification.json','outputs/r168/continuation.csv','outputs/r125/verification.json','outputs/r126/verification.json','reports/方正来源核对.md','protocols/r17.json','outputs/r160/alerts.parquet']
audit=dict(revision='R168',status='active_not_complete',goal_sha256=hashlib.sha256(Path('/home/xiaolv/.codex/attachments/fee38065-f5c6-49e0-9ab4-ae5d818c0c23/goal-objective.md').read_bytes()).hexdigest(),scope='Requirements crosswalk plus actual local omission experiment; no full completion certification',items=items,explicit_target_crosswalk=dict(five_questions=['R01','R02','R03','R04','R05'],three_tasks=['R02','R04','R10','R14'],three_priorities=['R08','R09','R10'],four_deliverables=['R12','R13','R14','R15']),extra_evidence=[dict(path=p,sha256=hashlib.sha256((r/p).read_bytes()).hexdigest()) for p in extras],next_local=[dict(priority=1,task='L2 top10 simplified reference comparator',basis='Goal section6 specifies L2 top10; protocol inventory contains L1 top6 but no L2 top10',inputs=['outputs/r130/monthly_panel.parquet','outputs/r129/daily_2026-10-21.parquet'],boundary='Only existing factor combinations and next-close synthetic convention; no original69factor replication or open execution claim'),dict(priority=2,task='L1 continuation same-population baselines',basis='R168 descriptive followup needs existing R160 F and momentum comparison',inputs=['outputs/r160/alerts.parquet','data/l1_daily.parquet'],boundary='Reuse original rules; no new tuning')],full_completion_proven=False)
(r/'outputs/r168/requirements_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
for item in items:
 for ref in item['evidence']:assert hashlib.sha256((r/ref['path']).read_bytes()).hexdigest()==ref['sha256']
print('AUDIT',len(items),'requirements; locally executable gaps recorded')
md=['# R168 目标审计与一级持续性遗漏补齐','', '## 目标审计','', '以当前R167入口逐项核对，保留16项既有要求作为交叉索引；这不是16项同质统计检验，也不把所有未证明项都视为数据阻塞。五个核心问题对应R01—R05；三任务对应R02/R04/R10/R14；优先实验对应R08—R10；四类交付对应R12—R15。详细证据路径及哈希见`outputs/r168/requirements_audit.json`。','', '| 要求 | 已验证范围 | 仍未完成 |','|---|---|---|']
for x in items:md.append(f"| {x['id']} {x['requirement']} | {x['verified_scope']} | {x['unresolved']} |")
md+=['','八个模块仍按目录处理：宏观PMI/M2、产业电池与有限会计、财务/预期/融资、量价/估值/扩散均有代理证据；ETF持仓与完整资金流不足，连续价差、库存、产能也不足。六类理论是可反驳假说，不因代理回归或模型分项已算而获得因果认证。六阶段仍为分维度研究概念，不输出互斥总和100%的阶段概率。预先登记、时点、覆盖、成本、多重检验和未知处理沿用各原协议。','', '## 本轮实际补做的最小实验','', '现有R156跟踪报告只含L2/L3，而R159已有1813条L1提示。本轮使用全部提示，沿用R10的下一收盘入点、同连续区块、5/20/60日收益/相对收益/回撤及20至60日延续定义。年度和合计分别报告；未校准Logit评分不称概率。没有增加模型、窗口、成功阈值或成本搜索。','', '| 提示规则 | 总提示 | 60日完整 | 60日未知 | 20至60日平均相对增量 |','|---|---:|---:|---:|---:|','| 每日 | 1527 | 1443 | 84 | 0.34% |','| 冷却20日 | 210 | 192 | 18 | −0.29% |','| 每月 | 76 | 69 | 7 | 0.35% |','', '冷却规则的2025年相对延续为0.37%，2026年为−1.16%。20日先成功的40条完整冷却提示，后续相对增量为−0.36%；仅2026年9条完整成功提示为−2.82%。不能由先成功推断持续有效，也不能把先成功条件当作原信号时已知信息。成功和未成功子集不包含20日结果未知的提示，故两子集数量之和不必等于全部。','', '独立验证重建4463条去重后完整期限路径，并重算27行跟踪汇总和27行条件延续的分母及指标；1813条提示的原20日目标完全一致。证据在`outputs/r168/followup.parquet`、`followup_summary.csv`、`continuation.csv`及`verification.json`。','', '## 如何解释与继续','', '这是价格提示后的描述性路径，不证明经济变量领先、独立信息或经济机制。原20日提示先于未来路径，但条件延续已用20日结果筛选；重复与重叠提示相关，年度差异明显，未知不补零。未加入新独立前瞻样本，不宣称有配置价值。','', '审计确认下一项优先可执行工作是二级前10简化参考基准：目标明确要求，现有协议只定位到一级前6，对应修复价格和月度面板均已存在。须先冻结已有因子组合、与动量/等权同母体比较、次日收盘及缺失成本边界；不能称为69因子完整复现。随后可用R160已冻结F与动量提示作一级持续性同母体对照。原文定义、首次发布修订、执行路径和未来样本仍属未完成项；生产部署不因研究目标自动授权。','', '本轮有实际遗漏补做和新缺口证据，整体保持active_not_complete；未触发全部路径受阻条件。']
(r/'reports/r168_goal_audit_and_l1_followup.md').write_text('\n'.join(md)+'\n')

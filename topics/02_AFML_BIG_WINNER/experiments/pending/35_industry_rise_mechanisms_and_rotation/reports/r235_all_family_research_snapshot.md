# R235 全16类历史研究读取样例

本轮将市场状态、原资格档案、实际同日期输出与研究结论合并，固定截点2026-09-30。它是事后研究档案阅读样例，不证明整份报告在当时已可获得，也不是当前实时市场信号或自动采用策略。

## 覆盖

全部16类保留，11类有精确日期输出，3类当日无输出，2类因训练历史不足无拟合模型。不用最近历史值补齐。输出共104082行、1028个原模型范围；这些行跨变体/任务重复引用行业，不能当成独立机会。

| 类别 | 当日输出行 | 状态 |
| --- | ---: | --- |
| core_three_tasks | 16950 | historical_exact_date_records |
| l1_three_tasks | 558 | historical_exact_date_records |
| rank_target | 12270 | historical_exact_date_records |
| market_style | 14388 | historical_exact_date_records |
| battery | 48 | historical_exact_date_records |
| eps_expectations | 0 | no_exact_date_output |
| size_diffusion | 14388 | historical_exact_date_records |
| financing | 0 | no_exact_date_output |
| profit_events | 0 | no_exact_date_output |
| leader_catchup | 19194 | historical_exact_date_records |
| financial_dual_clock | 504 | historical_exact_date_records |
| capital_accounting | 0 | no_fitted_model_history_insufficient |
| macro_interaction | 7470 | historical_exact_date_records |
| profit_expectations | 72 | historical_exact_date_records |
| early_financial | 0 | no_fitted_model_history_insufficient |
| fixed_factor_rank | 18240 | historical_exact_date_records |

EPS预期、融资及利润事件当日无记录，不能仅据此猜成数据损坏或模型训练失败；它们有其它历史输出。早期财务和资本会计则保留明确的原训练历史不足。两类原因分开。

## 如何阅读

[完整研究样例](../outputs/r235/snapshot.json)包含当日收盘状态、事件前一收盘状态、各分支当日覆盖、原资格和已记录研究结论。[同日期分数及显示排名](../outputs/r235/historical_score_view.parquet)仅列原模型分组内的分数和排名，不合并不同目标、方法、期限、行业层级或变体，不新增提示名单。

分类输出标为总体校准模型分数、非已认证状态概率；反转高分代表更高风险，不是更值得买入。固定因子模型的排名沿原修复口径sign(slope)乘原分数，fixed原规则用原分数，避免浮点近似系数影响排序。排名并列用平均位次，仅作显示，不替代原策略的排序破同分规则。

记录不暴露未来目标、成熟日期或收益标签。资格统计、模型研究结论属于事后证据区，不作为当时已知信息。已知市场状态不代表各模型在该状态均校准可靠，也不说明经济阶段已确认。

## 验证

独立读取源文件，对所有104082行显示分数、排名和组内数量逐一复算；确认全部16类、同日过滤、R196核心/一级/排名分区不重不漏，未来标签字段未输出。独立核验首次错误地以整个共享源文件检查融资缺输出，触发断言；修正为融资与EPS各自子母体后通过，原样例未改数据。失败留存。

本轮交付的是可审计研究阅读视图，未加入实时模型调用、调度、生产或交易。默认机器研究发布仍R183，历史重放仍R184。统一加入regime尚无稳定增量支持。

## 后续

此阶段状态字典、资格、实际模型和历史读取链已完成局部工程闭环。下一项回到整体目标需求：更新R230之后的交付映射，区分已解决的研究读取工程与仍依赖数据、前瞻的限制，检查是否还有必要的本地机制/风险比较，避免把工程核验轮数当作新的模型有效性证据。整体目标未完成。

# 阶段A：未来1个月内启动

原生RD-Agent完成30轮，取得30份可评分候选反馈。内验证选中 `rd_29`，配置在外层评分前冻结。

|频率|基准正例率|Brier相对先验改善|前10%候选命中率|命中率提升倍数|验收|
|---|---|---|---|---|---|
|双周|3.08%|-0.32%|3.48%|1.04|未通过|
|月|2.79%|+0.00%|3.18%|1.03|未通过|
|周|2.87%|-0.44%|3.30%|1.08|未通过|

表中先按观察日等权、再按行业层级/转折阈值/基准任务等权汇总。“Brier相对先验改善”为1减模型误差/先验误差，正数才是改善；前10%候选在全部可预测行业中先排名，再仅用已成熟标签评分，未知不能当负例。提升倍数是各任务比值的均值，未必等于两列平均命中率直接相除。

实际门槛逐基准、逐阈值判断：同时胜过先验、逻辑回归、静态树模型，命中率提升至少2倍，并有至少两个可评分年份持续改善；两基准均满足、至少两个转折阈值通过，才算该频率通过。因此汇总均值为正也不能自动通过。

[逐频率阈值基准指标](../outputs/stage_a/frequency_metrics.csv)；[年度指标](../outputs/stage_a/annual_metrics.csv)；[完整门槛裁决](../outputs/stage_a/verdict.json)；[样本与未成熟告警](../outputs/stage_a/outer_coverage.csv)。

[误报原因分解](../outputs/stage_a/false_alert_diagnostics.csv)：本任务的0仅表示没有命中“6—18个月且跑赢”的目标，不能解释成行业没有上涨。后续上涨且跑赢但短于6月或长于18月的告警单独列示；长行情仍不拆分。

[事件去重与提前天数](../outputs/stage_a/event_detection.csv)：同一景气段被连续多次预测只记一次。阶段B的负提前天数表示启动后的识别滞后，不是提前预测。

[同一观察日期比较](../outputs/stage_a/identical_origin_metrics.csv)、[共同日期清单](../outputs/stage_a/identical_origin_audit.json)；只用周、双周、月度实际发行日交集，样本较少，不用频率更密冒充独立证据更多。

[市场月份成块重抽样](../outputs/stage_a/month_block_uncertainty.csv)为等月诊断区间，没有将同日多个行业或重叠标签当作独立样本，也没有声称对30轮搜索完成独立统计确认。

[最后可用日期的全行业研究分数](../outputs/stage_a/last_available_research_scores.csv)明确标注各自预测日期，不能称作2026年11月实时信号，也没有经过独立概率校准确认。

[冻结配置](../outputs/stage_a/frozen_selection.json)、[30轮逐项假设与结果](../outputs/stage_a/round_inventory.csv)、[预测先落盘凭证](../outputs/stage_a/prediction_receipt.json)、[RD-Agent原生循环凭证](../outputs/stage_a/run_complete.json)。

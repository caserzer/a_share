# EP26 完成审计

科学目标允许正面、负面、证据不足；研究完成不要求模型胜基线。历史证据与独立确认分开。

| Goal要求 | 实际交付及证据 |
| --- | --- |
| 主事件/收益冻结及EP25核对 | tail_event_definition.md、config.json、preregistration.json；严格−20%，6日历月前复权收盘代理，完全沿用原池与标签 |
| 股票池、财报、估值、退市缺价时点审计 | data_audit.md；56,000条标签重新核对；source_receipts.csv、outcome_coverage.csv、missing_brier_bounds.csv；未解风险不伪装修复 |
| 456天财报年龄独立分析 | financial_age_audit.csv、conditional_scores.csv；<=365天成熟样本仅769行/2月，不能泛化为最新财报效果 |
| B0/B1/EP25 M_R及有限候选 | B0、B1、D_R（EP25 M_R）及原D_V/F/VF；5个直接分类候选×3阈值×22季度=330拟合，fit_audit.json；原B1/D_* p20和Brier完全匹配 |
| 预测概率/时间/版本/可用性/基准差异 | local_cache逐季度和合并Parquet，checkpoint和delivery_manifest哈希；完整概率与模型本地保留，不伪称GitHub上传 |
| Brier/相对改善/95%配对区间及功效 | baseline_comparison.md、paired_intervals.csv、statistical_power.json；主要差+0.000537，区间跨0；L6/L12及多比较边界保留 |
| ROC/AP/富集/召回/FPR | tail_risk_ranking.md；risk_deciles.csv、monthly_scores.csv；逐月指标与pooled区分，非普通accuracy |
| 概率校准/可靠性/分年与状态 | probability_calibration.md；calibration.csv含每桶行数/事件/覆盖月数/偏差区间；不把总体偏差抵消称校准 |
| 同算法五项消融及单个状态交互 | factor_ablation.md；相同行、容量、权重，无新增搜索，区分共同与个股分项 |
| 年份/状态/跨阶段/单月驱动 | conditional_monthly_scores.csv、conditional_scores.csv、phase_intervals.csv、leave_out_robustness.csv |
| 正负控制及关键计算测试 | controls.json；二元真值恢复与真实月内置乱；EP25原控制保留。pytest.txt与validation.json提供实际测试及330模型重放证据 |
| 风险过滤辅助、仓位持股/风险暴露/成本机会 | portfolio_risk_test.md、portfolio_summary.csv、exposures、industry_attribution及ES/事件暴露区间；保留陈旧报价和行业非中性限制，不能凭辅助回测宣布成功 |
| 前瞻窗口、事件数与功效 | validation_protocol.md、prospective.py、prospective_protocol_lock.json；36/48/60固定门槛、300事件/24事件月/0.002功效；尚无真实前瞻样本，不声称独立确认 |
| 六项结论问题和停止规则 | final_conclusion.md逐一回答；固定候选全部完成后停止，不改阈值、基线、模型或选年 |
| 独立目录、代码/报告/测试/复现提交GitHub | 本EP26目录与README；仅此目录及原字节EP25依赖纳入提交。最后必须检查实际push及远端HEAD，不能用manifest或本地提交代替GitHub发布证据；远端回执在最终会话交付 |
| 旧研究保存 | prior_episodes_preservation.json与validation.json核验1191项原EP24/EP25文件哈希，原双20%结论不改 |

十份规定研究文档齐备；环境、脚本、测试、逐月评分、统计区间、实验日志、数据/模型/预测哈希齐备。现有数据限制已记录并限制结论，未以缺少独立样本为由虚构确认性成功。GitHub发布是研究材料交付的最后执行门槛，必须以远端状态验证后才关闭Goal。

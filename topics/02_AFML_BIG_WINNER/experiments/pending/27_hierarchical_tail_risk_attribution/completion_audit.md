# EP27 完成审计

2026-10-20；按原Goal的十项DoD逐项验收，科学正结果不是完成门槛。所有已注册候选及消融到此停止，没有追加模型搜索。

| DoD | 已完成工作与可核查证据 |
| --- | --- |
| 1. 时点、股票池、左尾标签审计 | data_integrity_audit.md；p0_audit.json；7995条source_receipts；ST/退市覆盖普查、缺失上下界及公司行动收益敏感性。228只退市缺价、原始财报/估值版本等保留为未解决限制，没有冒称修复。 |
| 2. 三层贡献分别报告 | market_risk_decomposition.md、industry_risk_decomposition.md、idiosyncratic_risk_report.md；真实时点模型增量、概率结构与事后Oracle分别保存。 |
| 3. 同算法/人群估值财务消融 | valuation_financial_ablation.md；四期限、六候选、22季度，共528次基础拟合。p1_gate先完成比较，再进入P2。 |
| 4. 主Delta与区间 | paired_intervals.csv：6月Full−RMI Brier −0.003479，L6的95%区间[−0.005859,−0.001289]；L12及四项检验族区间另列，其他期限不替代主检验。 |
| 5. 同行业/风险匹配 | conditional_group_audit.csv保留所有排除原因；行业约40%、风险格约7.2%可评价覆盖。matched_pairs.csv及matched_intervals.csv保留934个已知对及风险差区间。 |
| 6. 跨年/状态校准 | conditional_calibration.md；384条滚动校准记录，108次预热回退、276次有效拟合。global/state均未改善主模型Brier，失败结果完整保留。 |
| 7. 控制与主要指标核验 | controls.json全部通过；validation.json重放528个模型、947072行预测及1888条月度指标，并重建条件AUC、误差会计与校准参数。pytest.txt：22项通过。 |
| 8. 经济辅助实验 | portfolio_tail_risk_test.md；S0/S1/S2同目标行业权重、风险格持股数及总仓位；10/30bp双成本、容量约束、ES/回撤/机会成本。未确认新增经济价值。 |
| 9. 偏差披露 | 数据审计及statistical_validation.md：旧测试区间反复使用、收益重叠、市场共同冲击、功效、选择偏差和外部数据依赖，均未升级为独立确认。 |
| 10. 分级结论 | final_conclusion.md回答六个问题，区分历史有限支持、本轮不支持和证据不足；全A稳定校准及组合尾部优势尚未确认。 |

原EP24/25/26共1304项文件哈希逐一验证未改；另核对198项继承基准/模型文件与原已发表检查点一致。双20%原结论不变。

研究方案、配置、P0面板及核心计算代码在2026-10-20T09:26:30.930645+00:00先于EP27评分冻结。报告、补充诊断、前瞻工具及完整重建器属于后续交付支持代码，由supporting_code_manifest.json单列，不追溯冒称预注册。未来协议由prospective_protocol_lock.json单独冻结；没有生成事后伪前瞻预测，也没有部署自动任务。

delivery_manifest.json逐项列出应提交文件与本地缓存的SHA256和字节数，自身不自引用。完整模型、逐条预测、持仓等缓存仅在本地保留，不能声称全部上传或只克隆Git即可精确复现。Git提交及远端分支回执需在发布时另行核对；本文与清单本身不预先认证尚未发生的推送。

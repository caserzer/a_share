# EP25 完成核对

交付完成与科学命题成立分开。主要结果：不支持本轮估值/陈旧财报信息带来稳定完整分布优势；独立确认仍证据不足。

| Definition of Done | 状态 | 可复核证据 |
| --- | --- | --- |
| 数据与历史时点审计、未解问题 | 完成 | data_audit.md；outputs/data_audit.json、input_receipts.json |
| 所有预注册模型和基线 | 完成，无未运行候选 | 4候选×4期限×22季度=352次拟合；B0/B1复算；fit_audit.json |
| 每个可评价期限完整样本外评分 | 完成，模型时间隔离、证据等级为历史探索 | 1/3/6/12月分别63/62/59/52个可评分起点；monthly_scores.csv；缺失另列outcome_coverage.csv |
| CRPS差异、置信区间、校准与尾部 | 完成 | baseline_comparison.md、calibration_report.md；paired_intervals.csv、三张PNG |
| 正控制、置乱负控制、关键计算测试 | 完成 | controls.json；pytest.txt为16 passed；validation.json全710304条重算及16个序列化模型精确重放 |
| 同样本消融与跨阶段稳健性 | 完成 | factor_ablation.md；phase_intervals.csv、annual_scores.csv、leave_out_robustness.csv |
| 支持/不支持/证据不足区分 | 完成 | final_conclusion.md；局部尾部与1月算法改善不等于估值/财报稳定增量 |
| 独立目录的代码、配置、记录、复现说明 | 完成 | 本EP25目录；config.json、requirements.txt、README.md、preregistration.json、delivery_manifest.json |
| 保留EP24及双20%结论 | 完成 | ep24_preservation_before.json的1040项哈希全部未变；无EP24写入操作 |
| 无独立新样本时建立前瞻流程 | 完成工具与流程，尚无前瞻样本 | prospective.py、confirm_prospective.py与拒绝规则测试；README说明外部来源审计、36月门槛、无定时任务 |
| 遵守停止规则 | 完成 | 四候选后停止，无新模型、选年、放宽门槛或改基线 |

outputs/local_cache约934MB按既有规则忽略；完整原子/模型/预测保留本地，有收据哈希。没有创建Git提交或推送。delivery_manifest.json区分可评审交付与本地缓存，克隆Git不包含全部输入与预测。

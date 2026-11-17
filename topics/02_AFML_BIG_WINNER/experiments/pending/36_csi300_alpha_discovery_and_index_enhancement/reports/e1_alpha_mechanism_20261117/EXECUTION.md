# 实验执行记录与验收

本轮用户授权为“执行方案”。原方案和设计配置保持原样，执行状态以本报告为准。

1. G0/G1：核对数据、原季度模型、执行引擎及标签，冻结输入与代码；78项特征分组固定。既有结果已见，新机制结果当时未算。
2. G2：不读取标签，生成状态、样本排除、592个约束解、匹配和14000个随机尝试记录；原24季度分数复放一致，封存名单及哈希。
3. G3：封存统计脚本后计算标签、固定事件与9条独立连续账户。原标签与本轮毛收益逐行核对；事件净收益独立处理可交易性。
4. G4：主族三项均INCONCLUSIVE；原账本状态贡献逐日对齐。新E1扩展期估值未知按原规则停账，不补值。
5. G5：形成前瞻登记和功效限制，真实未来观察、数据刷新与模型出分仍未完成；没有部署和自动调度。

分析首次运行在市场状态字符串格式化处遇到NumPy兼容错误。原脚本、登记与已生成结果保存在attempt1；修复版本改用np.char.add，实际风险估值使用与账户相同的停牌标记。修复时已见主结果，这一点已登记。没有改分数、阈值、样本、标签、主统计或成本；三个主检验的点估计、区间及p值与修复前完全一致。

[首次分析登记](../../outputs/diagnostics/e1_alpha_mechanism_20261117/analysis_registration.json) · [修复版本登记](../../outputs/diagnostics/e1_alpha_mechanism_20261117/analysis_registration_v2.json) · [初始封存](../../outputs/diagnostics/e1_alpha_mechanism_20261117/freeze.json) · [无标签名单封存](../../outputs/diagnostics/e1_alpha_mechanism_20261117/selection_complete.json) · [收益计算封存](../../outputs/diagnostics/e1_alpha_mechanism_20261117/evaluation_complete.json) · [分析完成](../../outputs/diagnostics/e1_alpha_mechanism_20261117/analysis_complete.json)。

955项验证包括全目标风险与行业名额、原标签一致性、原分数复放、仅历史截断的窗口核对、未清算事件不生成净收益、账本逐日加总及修复前后主结果一致。51项测试通过，只有既有OSQP未来默认值弃用提示。验证范围是本实现的口径一致性，不等于严格PIT或因果认证。

可复现入口依次为src/e1_mechanism.py的freeze/prepare/evaluate，src/e1_mechanism_analyze_v2.py的analyze，src/e1_mechanism_validate.py和src/e1_mechanism_report.py。已有freeze/selection/evaluation完成凭据时拒绝重复覆盖；重新运行须使用新目录与版本。旧源数据、预测和报告未改，未提交、推送、部署或发送消息。

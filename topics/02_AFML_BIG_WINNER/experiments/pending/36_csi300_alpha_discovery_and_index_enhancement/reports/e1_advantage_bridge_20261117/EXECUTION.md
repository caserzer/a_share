# 执行合同与验收

本轮授权为执行原账户优势消失的逐层拆解及被排除持仓审计。先冻结代码和输入，再封存无标签目标，最后独立重放8条账户并计算描述性归因。原预测、旧报告和旧账户均未修改。

- 主链O→U→K→I→F；O为原账户，F为上一轮受约束E1。两端逐日净值精确复放，所有账户主区间1001日、无失败。
- U保留原每期58—60只数量，K缩为ceil(C样本数/5)，I按C内行业比例分配名额。其余选股均使用原E1分数；同分按代码升序。
- F复用已封存目标；逆序KF去掉行业名额限制而保持相同13风格参考、0.25标准差容差、2秒求解上限及1%解差。UI用于调换行业和持仓数顺序。
- X仅删除被排除股票，原目标权重不放大，剩余现金不取利息。执行器仍独立处理涨跌停、停牌与旧仓出售限制。
- 所有每日期目标、成交和每日实际持仓完整保存；私有目录private/e1_advantage_bridge_20261117/targets.parquet、orders和holdings可用于逐股追溯。公开收益、贡献和覆盖明细位于outputs/diagnostics/e1_advantage_bridge_20261117。
- 统计只作65交易日块配对描述，不进行主假说检验或事后多重显著性宣告。行业/风格顺序交互明确保留。

35项账本与两端复放检查、1316项目标及逐日持仓检查通过，54项测试通过；仅既有OSQP弃用提示。没有新训练、调参、提交、推送或部署。真实前瞻、严格PIT和容量认证均未因此完成。

[冻结配置](../../configs/e1_advantage_bridge_20261117.json) · [输入及代码哈希](../../outputs/diagnostics/e1_advantage_bridge_20261117/freeze.json) · [无标签名单封存](../../outputs/diagnostics/e1_advantage_bridge_20261117/selection_complete.json) · [账户凭据](../../outputs/diagnostics/e1_advantage_bridge_20261117/accounts_complete.json) · [分析完成](../../outputs/diagnostics/e1_advantage_bridge_20261117/analysis_complete.json) · [账本验证](../../outputs/diagnostics/e1_advantage_bridge_20261117/validation.json) · [目标和持仓验证](../../outputs/diagnostics/e1_advantage_bridge_20261117/target_holdings_validation.json)。

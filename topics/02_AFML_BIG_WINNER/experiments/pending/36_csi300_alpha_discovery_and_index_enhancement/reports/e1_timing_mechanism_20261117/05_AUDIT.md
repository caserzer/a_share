# 覆盖、修订与验证

主结论使用 evaluation_v2。原始首轮输出不覆盖。

1. 原旧phase2日历在2021年1月以第一信号共同初始化。独立事件需要真实第二周信号，因此v2把2021-01-11改为2021-01-18；连续账户仍精确保持旧历史定义。amendment.json记录源文件和修订日历哈希。
2. 常量结果的条件相关必须NA，防止浮点残差被误当相关；该数值校验并入v2。
3. 连续路径首版遇到numpy字符串拼接错误，在生成结果前失败；保留原源码，v2只修拼接。随后增加早晚分段与单列费用，事先封存各分析源码并标记已经看过前一步结果；不声称这些扩展是历史未见确认检验。
4. 固定事件H10净收益：立即47/50有效，延迟48/50有效，共同46/50；失败为退出受阻。等H5/H10/H20共同42个月。共同退出H5多在延迟入场前，只有4个月，区间NA。
5. 价格状态未知、精确零、无匹配、残差不可评分均单列。全13严格匹配零支持；行业+价格匹配约15.18%预算，仍是部分识别。
6. 日历/年龄/市场反弹没有被随机分离；归因能够回答“哪些头寸、哪些日子贡献”，不能单凭历史收益回答资金流或行为原因。

## 验证

最终审计15266项PASS，覆盖原账户净值、股票/费用损益、现金、全体状态加总、事件状态分解、成交门槛、无负现金、完整计划行数、原动作重放、连续账户AA/BB重放、桥接终值闭合和输入哈希。

独立单元测试5项：四组/缺失/零边界、非重叠趋势定义、动作链融资、早/共同段含费恒等式、对数链接终值闭合。未新增训练或更改预测。

复现顺序：e1_timing_mechanism.py freeze/prepare/ledger；修订回执后e1_timing_mechanism_evaluate_v2.py events/actions/residuals/analyze；supplement_v2.py supplement；path_bridge_v2.py bridge；path_segments_v2.py bridge；本报告脚本。已有freeze/selection不能重新冻结，需新run目录，不能覆盖原结果。

输出索引：[01_original_state.csv](../../outputs/diagnostics/e1_timing_mechanism_20261117/evaluation_v2/01_original_state.csv)、[02_state_timing.csv](../../outputs/diagnostics/e1_timing_mechanism_20261117/evaluation_v2/02_state_timing.csv)、[03_actions_state.csv](../../outputs/diagnostics/e1_timing_mechanism_20261117/evaluation_v2/03_actions_state.csv)、[04_residual_association.csv](../../outputs/diagnostics/e1_timing_mechanism_20261117/evaluation_v2/04_residual_association.csv)、[05_coverage.csv](../../outputs/diagnostics/e1_timing_mechanism_20261117/evaluation_v2/05_coverage.csv)；所有明细在同目录及private/e1_timing_mechanism_20261117。原始状态/同行成员/目标selection.json封存，final_validation.json与delivery.json分别存验证和交付哈希。

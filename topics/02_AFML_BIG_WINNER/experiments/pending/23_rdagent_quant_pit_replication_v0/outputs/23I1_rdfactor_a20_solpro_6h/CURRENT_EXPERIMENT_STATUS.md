# EP23 第二阶段当前实验状态

状态时间：2026-07-28（Asia/Shanghai）

## 结论

按用户指令，A20 正式 RD-Agent 因子进化已在 Loop 38 完成 checkpoint 后终止。原计划为 6 小时，停止时完成了 39 个完整循环（索引 0–38）；Loop 39 只进入假设生成，没有形成完整结果，已从统计中排除。

本次结果是“可审计的部分正式搜索”，不是完成的 23I 分支，更不是论文复刻闭环。A20 五种子匹配确认、A157 分支、23J–23M 均未运行。

## 搜索状态

| 项目 | 当前值 |
|---|---:|
| 完整循环 | 39 |
| 有效结果循环 | 39 |
| Agent 接受 / 拒绝循环 | 2 / 37 |
| 生成 / 最终实现成功因子 | 44 / 44 |
| Agent 暂定接受因子 | 4 |
| 完整 checkpoint | 39 / 39 |
| 原始决策与 checkpoint 一致 | 39 / 39 |
| 记录到的输入 token 事件 | 266 |
| 记录到的输入 token 合计 | 843,385 |
| 输出 token | Provider 日志不可得 |

## Agent 暂定接受链

Loop 1 接受：

1. `Overnight_Gap_1D`
2. `Close_Location_Value_1D`
3. `Close_Momentum_20D`

该状态的单次反馈窗口指标为：

| IC | RankIC | 扣费年化收益 | 最大回撤 |
|---:|---:|---:|---:|
| 0.019438 | 0.015161 | 0.082583 | -0.059941 |

Loop 38 又接受：

4. `Exponentially_Weighted_Lagged_VolumeReturn_Correlation_20D`

Loop 38 的候选单次反馈窗口指标为：

| IC | RankIC | 扣费年化收益 | 最大回撤 |
|---:|---:|---:|---:|
| 0.012764 | 0.007787 | 0.109713 | -0.069593 |

这个接受存在重要风险边界：相对此前 SOTA，扣费年化收益提高约 32.9%，但 IC 下降约 34.3%，最大回撤更深；反馈还缺少 turnover。RD-Agent 因“扣费年化收益改善即可替换”的内部规则接受了它，但它没有通过 EP23 预注册的五种子、跨 2022/2023、冗余与集中度确认。因此这里只称为 **Agent 暂定接受**，不能称为已验证新因子。

## 成本

| 项目 | 美元 |
|---|---:|
| 本次正式 A20 起点累计 usage | 6.232372 |
| 终止时累计 usage | 110.147268 |
| 本次正式 A20 usage 差分 | 103.914896 |
| 另行保存、已排除的 schema 无效运行 | 1.907913 |

OpenRouter key 没有硬额度上限。上述正式费用采用 provider key usage 起止差分；本地 LiteLLM 无法可靠提供该新模型的逐请求费用和输出 token。

## 审计与异常

- 人为终止退出码为 130；`run_manifest.json` 因此正确标记为 `raw_run_failed_or_incomplete`。
- 39/39 个完成循环均有五步 checkpoint；39/39 个原始 LLM 决策与 checkpoint 一致。
- Loop 29 有两个候选首次误用 Fixed-format HDF5 的列选择，critic 自动修复后均成功执行；没有主流程崩溃或 API 重试风暴。
- RD-Agent 适配器 diff 哈希仍为 `80c471ae3ba64f7465972652d419691bdc609f8ada12c946e39ef59cc051ba11`。
- 输出目录秘密扫描通过；报告与审计产物不包含 OpenRouter key 或代理地址。
- 23I 的 Agent 选择未读取 2024–2026；但 23H 已生成该区间的描述性指标，因此整个 Phase 2 的 historical test 已标记为 `design_contaminated_historical_real_market_evidence`，不能再视为 untouched final test。

## 阶段进度

| 阶段 | 状态 |
|---|---|
| 23G 因子库预检 | 完成 |
| 23H 静态因子库基准 | 完成；A20 被选为进化起点 |
| 23I A20 正式进化 | 人为终止；部分正式轨迹已审计，未独立确认 |
| 23I A157 正式进化 | 未开始 |
| 23J 进化动力学 | 未开始 |
| 23K 模型进化 | 未开始 |
| 23L 执行与 big-winner bridge | 未开始 |
| 23M 联合调度器 | 未开始 |
| 第二阶段最终报告 | 未生成 |

## 恢复边界

若未来恢复，不能把本目录直接标为 6 小时正式完成。安全做法是保留本目录为中止证据，另开新的正式 A20 run，或明确将本次 39 循环定义为缩短版探索；随后再执行五种子 2022 feedback、2023 independent confirmation，只有通过后才可冻结 retained library 并进入 A157/23J。

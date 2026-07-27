# EP23 23C3 Corrected RD-Agent Evolution Loop 0

## 裁决

```text
baseline = Alpha20 + close_momentum_20d + volume_surprise_20d
accepted_joint_candidate = reversal_5d + volatility_20d + intraday_range_1d
rdagent_replace_best = yes
local_research_decision = joint promotion only; marginal attribution required
evidence = design_contaminated_historical_real_market_evidence
```

修正后的单轮 RD-Agent factor evolution 有效完成。固定核心库没有被候选因子
覆盖，baseline 与 candidate 使用完全相同的 Qlib 配置、split、LightGBM、
`RobustZScoreNorm + Fillna`、Top50/drop5 和交易费用。

## 可比结果

| metric | fixed-core baseline | corrected candidate | delta |
|---|---:|---:|---:|
| IC | 0.008419 | 0.013214 | +0.004795 |
| Rank IC | 0.005548 | 0.011929 | +0.006381 |
| excess return with cost ARR | -6.1473% | 3.9312% | +10.0785 pp |
| excess return with cost IR | -0.837241 | 0.472865 | +1.310105 |
| excess return with cost MDD | -23.1698% | -19.1925% | +3.9773 pp |
| excess return without cost ARR | -1.4083% | 8.6849% | +10.0932 pp |

RD-Agent 的替换准则以含成本超额年化改善为主，因此本轮给出
`Replace Best Result = yes`。本地研究裁决只允许把三个新增因子视作一个联合
候选包；本轮没有识别它们各自的边际贡献。

## 候选处置

| Agent proposal | disposition | reason |
|---|---|---|
| `momentum_20d` | deduplicated | 与固定 `close_momentum_20d` 数值完全一致 |
| `volume_surprise_20d` | rejected by name guard | 与固定核心同名但公式不同，SOTA-first |
| `reversal_5d` | entered joint candidate | 新增因子 |
| `volatility_20d` | entered joint candidate | 新增因子 |
| `intraday_range_1d` | entered joint candidate | 新增因子 |

最终 factor parquet 为 `464,577 × 5`，索引
`(datetime, instrument)` 唯一，日期覆盖 `2017-04-05` 至 `2026-05-27`。
列顺序为：

1. `close_momentum_20d`
2. `volume_surprise_20d`
3. `reversal_5d`
4. `volatility_20d`
5. `intraday_range_1d`

## 配置修复审计

首次原始执行中，新旧 `volume_surprise_20d` 同名；旧 runner 在最终合并时
保留最后一列，使 Agent 的“含当日均值、非 log”变体覆盖了固定核心。该原始
结果的含成本超额 ARR 为 `3.0270%`，但它不是 SOTA 上的严格增量实验，因此
只保留为配置混杂诊断，不参与晋级。

runner 随后增加两层保护：

- 相关性去重前拒绝所有与 SOTA 同名的新列；
- 最终重复列保护改为保留 SOTA-first 的第一列。

修正后 baseline 与 candidate 的 Qlib 配置 SHA256 均为
`7f90fd786f7e4c9208767192b8d38237ff1070062afc103290ea78e9eb518665`；
最终 factor parquet SHA256 为
`042e554782ae56050a980848ce3016eace26f6e7e572bb364ffe7a85047a738e`。
OpenRouter key 对正式日志、复核日志和最终 workspace 的扫描命中数均为 0。

## 与 23C2 的关系

23C2 的 `20.0202% / 22.4856%` 是五 seed、两条 label lane 的策略绝对净年化
中位数；本报告的 `3.9312%` 是 RD-Agent/Qlib 单次运行的相对沪深 300
含成本超额年化。两者分母、seed 聚合和指标语义不同，不比较绝对数值。

23C2 已发现 reversal 在给定 momentum + volume 后通常有负贡献。本轮新增
`reversal_5d` 的窗口和实现与 23C2 不完全相同，且与 volatility/range 联合
进入，因此当前结果不能推翻 23C2 的边际归因。下一步必须对
`reversal_5d`、`volatility_20d`、`intraday_range_1d` 做 matched-seed
single-addition/leave-one-out 消融，再决定最终 factor library。

## 解释边界

- historical test 已被用于设计与修复，证据等级是
  `design_contaminated_historical_real_market_evidence`，不构成 true OOS。
- 这是论文 R&D-Factor loop 的 PIT-universe 项目适配，不是论文数值的精确复刻。
- LiteLLM 尚无 `openrouter/openai/gpt-5.6-sol` 价格映射，因此本轮成本统计
  不可用；模型与 embedding 调用均已实际成功。
- Agent 原反馈建立在配置混杂的原始矩阵上；正式研究裁决以修正后的独立复核
  数值为准。

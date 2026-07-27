# EP23 23C4 New Factor Marginal Attribution

## 裁决

```text
core = close_momentum_20d + volume_surprise_20d
new_batch = reversal_5d + volatility_20d + intraday_range_1d
design = five-seed single-addition + leave-one-out
evidence = design_contaminated_historical_real_market_evidence
claim_ceiling = posthoc_marginal_attribution_diagnostic
```

本阶段不再调用 LLM；它冻结 23C3 生成的因子实现，沿用 23C2 的 Alpha20、
双 label lane、LightGBM、train-only normalization、Top50/drop5 和费用，
只改变三个新增因子的组合。

## 五 seed 中位数

| variant | PAPER IC | PAPER net ARR | executable IC | executable net ARR |
|---|---:|---:|---:|---:|
| core | 0.009225 | 20.0202% | 0.012860 | 22.4856% |
| core_plus_reversal | 0.011340 | 19.8392% | 0.013529 | 24.3382% |
| core_plus_volatility | 0.011299 | 20.8526% | 0.014906 | 23.6241% |
| core_plus_intraday_range | 0.011013 | 19.7245% | 0.014604 | 24.3183% |
| core_plus_reversal_volatility | 0.011883 | 15.9016% | 0.013910 | 18.6941% |
| core_plus_reversal_intraday_range | 0.011341 | 14.1723% | 0.013531 | 18.7711% |
| core_plus_volatility_intraday_range | 0.011329 | 17.8337% | 0.014284 | 20.8936% |
| core_plus_all_three | 0.007917 | 14.6799% | 0.011195 | 15.3342% |

## Matched-seed marginal contrasts

| contrast | PAPER positive seeds | paired median ΔARR | executable positive seeds | paired median ΔARR |
|---|---:|---:|---:|---:|
| reversal_given_core | 3/5 | +1.1944% | 2/5 | -1.1937% |
| volatility_given_core | 4/5 | +3.7914% | 4/5 | +1.7181% |
| intraday_range_given_core | 4/5 | +4.2390% | 4/5 | +3.2853% |
| all_three_given_core | 1/5 | -5.7597% | 1/5 | -7.5726% |
| reversal_volatility_given_core | 3/5 | +0.6118% | 2/5 | -2.5820% |
| reversal_intraday_range_given_core | 2/5 | -3.3977% | 2/5 | -5.8390% |
| volatility_intraday_range_given_core | 3/5 | +2.9140% | 2/5 | -0.1601% |
| reversal_given_core_and_other_two | 1/5 | -3.1538% | 1/5 | -5.5594% |
| volatility_given_core_and_other_two | 2/5 | -2.3620% | 1/5 | -3.4369% |
| intraday_range_given_core_and_other_two | 2/5 | -0.1121% | 1/5 | -4.9907% |
| intraday_range_vs_volatility | 2/5 | -0.6423% | 2/5 | -0.9819% |

## 因子级裁决

single-addition gate 要求因子相对核心的 validation IC、historical-test IC 和
historical-test ARR 在 PAPER 与 executable 两条 lane 中 paired median 均为正，
且至少覆盖 3/5 seed。leave-one-out 用作交互压力测试，不在全量包已经有害时
反向否决单因子。

| factor | single-addition | library action | core PAPER ΔARR | core executable ΔARR | LOO PAPER ΔARR | LOO executable ΔARR |
|---|---|---|---:|---:|---:|---:|
| reversal_5d | reject | reject | +1.1944% | -1.1937% | -3.1538% | -5.5594% |
| volatility_20d | individually_supported | retain_primary | +3.7914% | +1.7181% | -2.3620% | -3.4369% |
| intraday_range_1d | individually_supported | supported_alternative_not_combined | +4.2390% | +3.2853% | -0.1121% | -4.9907% |

- 最终保留：`volatility_20d`。
- 有单因子证据但与入选因子不兼容：
  `intraday_range_1d`。
- 有单因子证据但直接比较无法唯一选择：
  `none`。
- 拒绝：`reversal_5d`。

当 volatility 与 range 均通过 single-addition gate、但二者联合未通过双 lane
gate 时，使用相同 seed 直接比较两者；PAPER validation IC 是首要选择信号，
historical-test 两条 ARR lane 只检查方向一致性。

## 复现审计

- 23C3 与 23C2 核心因子数值：`passed`，
  common rows `464577`，最大绝对差
  `0.000e+00`。
- 23C4 core 与 23C2 `plus_momentum_volume` 指标：
  `passed`，最大绝对差
  `1.791e-07`。

## 解释边界

- 该实验由 23C3 historical-test 联合结果触发，只是 post-hoc attribution，
  不产生新的 true OOS 证据。
- positive seed count 基于相同 seed 的配对差值；paired median 不是两个独立
  中位数之差。
- 23C3 的 Qlib 单次含成本超额 ARR 与本报告五 seed 策略绝对净 ARR 语义不同，
  不能直接比较数值。
- 本阶段不计入论文 Agent LLM 搜索预算。

运行耗时：`63.39` 秒。

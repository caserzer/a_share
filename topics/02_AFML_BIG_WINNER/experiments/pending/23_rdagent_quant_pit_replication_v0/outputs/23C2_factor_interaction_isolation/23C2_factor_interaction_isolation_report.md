# EP23 23C2 Factor Interaction Isolation

## 裁决

```text
core = close_momentum_20d + volume_surprise_20d
comparison = add reversal / add close-location / add both
seeds = 5 matched seeds
evidence = design_contaminated_historical_real_market_evidence
claim_ceiling = posthoc_factor_interaction_diagnostic
```

本阶段沿用 23C1 的统一 preprocessing、split、LightGBM、Top50/drop5 和费用，
只改变四个 RD-Agent 因子的组合方式。

## 五 seed 中位数

| variant | PAPER IC | PAPER net ARR | executable IC | executable net ARR |
|---|---:|---:|---:|---:|
| alpha20 | 0.007892 | 13.1308% | 0.008477 | 14.8394% |
| plus_momentum | 0.009726 | 18.1484% | 0.014694 | 19.4197% |
| plus_volume | 0.008331 | 14.8464% | 0.013496 | 16.3233% |
| plus_momentum_volume | 0.009225 | 20.0202% | 0.012860 | 22.4856% |
| plus_core_reversal | 0.011662 | 15.4268% | 0.014009 | 18.7118% |
| plus_core_close_location | 0.007803 | 17.1176% | 0.015986 | 21.9498% |
| plus_all_four | 0.006669 | 17.1438% | 0.014082 | 21.1382% |

核心二因子组合的 PAPER / executable 净 ARR 分别为 `20.0202%` /
`22.4856%`。

## Matched-seed interaction contrasts

| contrast | PAPER positive seeds | paired median ΔARR | executable positive seeds | paired median ΔARR |
|---|---:|---:|---:|---:|
| volume_given_momentum | 3/5 | +2.4897% | 3/5 | +5.0153% |
| momentum_given_volume | 4/5 | +4.8508% | 4/5 | +3.9801% |
| reversal_given_core | 2/5 | -3.7551% | 2/5 | -2.3212% |
| close_location_given_core | 2/5 | -2.9026% | 1/5 | -3.6875% |
| both_weak_factors_given_core | 2/5 | -1.7014% | 1/5 | -2.4411% |
| close_location_given_core_reversal | 3/5 | +2.0537% | 2/5 | -0.1198% |
| reversal_given_core_close_location | 3/5 | +0.0262% | 2/5 | -0.8117% |

四因子相对核心二因子组合的 paired median ΔARR 为 PAPER
`-1.7014%`、executable `-2.4411%`。

## 研究裁决

- `momentum + volume` 是本轮最佳组合，PAPER / executable 净 ARR 中位数为
  `20.0202%` / `22.4856%`。
- volume 在给定 momentum 后的收益增量为正，但只覆盖 3/5 seed；momentum
  在给定 volume 后覆盖 4/5 seed。因此 momentum 是核心，volume 是较弱的条件增量。
- reversal 或 close-location 单独加入核心组合时，两条 lane 的 paired median
  ARR 都下降；同时加入也下降。因此 23C1 的“可能存在弱因子交互”假设被否定。
- 下一轮 factor library 只保留 momentum + volume；不保留 reversal 与
  close-location。

canonical feature-order 复现审计：
`passed`，最大指标绝对偏差
`1.808e-07`。

## 解释边界

- 这些组合由 23C1 historical-test readout 驱动，属于 post-hoc interaction
  diagnostic，不能用于新的 true OOS 主张。
- `positive seeds` 使用相同 seed 的成对差值；中位数不是两个独立中位数之差。
- 只有当弱单因子在给定核心组合后仍稳定改善，才有理由把它解释为条件贡献；
  单看四因子全量组最好不足以证明每个因子都应晋级。
- 本阶段不调用 LLM，也不计入论文 agent 搜索预算。

运行耗时：`55.05` 秒。

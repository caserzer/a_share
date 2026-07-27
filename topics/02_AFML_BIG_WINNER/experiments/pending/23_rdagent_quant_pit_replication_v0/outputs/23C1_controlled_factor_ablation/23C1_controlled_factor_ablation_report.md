# EP23 23C1 Controlled Factor Ablation

## 裁决

```text
preprocessing = matched train-only robust z-score + fill-zero
seeds = 5 matched seeds
variants = Alpha20 + 4 single-factor additions + all-four addition
evidence = design_contaminated_historical_real_market_evidence
claim_ceiling = controlled_factor_attribution_diagnostic
```

23C 原始 RD-Agent loop 存在 preprocessing 漂移，本阶段在统一数据、split、
LightGBM、train-only normalization、组合规则和费用下重新进行归因。

## 五 seed 中位数

| variant | PAPER IC | ΔIC | PAPER net ARR | ΔARR | executable net ARR | ΔARR |
|---|---:|---:|---:|---:|---:|---:|
| plus_close_momentum_20d | 0.009726 | +0.001834 | 18.1484% | +5.0175% | 19.4197% | +4.5803% |
| plus_close_reversal_5d | 0.010603 | +0.002710 | 12.0782% | -1.0526% | 13.1094% | -1.7299% |
| plus_daily_close_location_value | 0.004115 | -0.003777 | 7.3513% | -5.7796% | 10.0895% | -4.7499% |
| plus_volume_surprise_20d | 0.008331 | +0.000439 | 14.8464% | +1.7156% | 16.3233% | +1.4839% |
| plus_all_four | 0.006669 | -0.001223 | 17.1438% | +4.0129% | 21.1382% | +6.2988% |

两条标签 lane 的净 ARR 均优于 Alpha20 的变体：
`plus_close_momentum_20d, plus_volume_surprise_20d, plus_all_four`。

以 executable bridge 净 ARR 增量排序，当前最佳变体为 `plus_all_four`。这仍是被反复
观察过的 historical test，只用于定位首轮组合改善的来源，不构成 true OOS 晋级。

## Matched-seed stability

| variant | PAPER positive seeds | paired median ΔARR | executable positive seeds | paired median ΔARR |
|---|---:|---:|---:|---:|
| plus_close_momentum_20d | 4/5 | +2.3008% | 4/5 | +3.6870% |
| plus_close_reversal_5d | 2/5 | -4.0232% | 2/5 | -3.1613% |
| plus_daily_close_location_value | 2/5 | -5.2048% | 1/5 | -4.7499% |
| plus_volume_surprise_20d | 4/5 | +1.7156% | 4/5 | +2.2914% |
| plus_all_four | 4/5 | +3.2394% | 5/5 | +4.9241% |

## 下一项研究决策

- `close_momentum_20d` 是最明确的单因子贡献者：两条 lane 的 ARR 和 IC 均改善，
  收益改善在两条 lane 都覆盖 4/5 seed。
- `volume_surprise_20d` 是次级贡献者：两条 lane 收益均改善 4/5 seed，但
  PAPER IC 的稳定性弱于 momentum。
- `close_reversal_5d` 出现“IC 上升、组合收益下降”，不能仅凭 IC 纳入。
- `daily_close_location_value` 单独加入时明显拖累，不应单独晋级。
- 四因子联合的 executable ARR 最好且 5/5 seed 改善，说明可能存在交互项；
  下一实验应固定测试 `momentum + volume`、再分别加入 reversal/close-location，
  判断联合改善是否需要两个单独表现较差的因子。

## 解释边界

- 所有变体使用相同的五个 seed；主表报告跨 seed 中位数，不按 historical test
  选择 seed。
- 每个变体的 normalization 都只在 train split 拟合，然后应用于 validation 和
  historical test。
- 最低因子有限值覆盖率为 `94.4446%`；缺失值在 train-only robust
  normalization 后按既定 baseline 规则填零。
- 单因子结果用于归因，`plus_all_four` 用于检查组合交互，不将消融数量包装成
  agent 搜索预算。

运行耗时：`50.05` 秒。

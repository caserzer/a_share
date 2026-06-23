# 13A3 压缩修复态成本敏感性与 full-native 可行性诊断报告

## 1. 裁决

本轮裁决：

```text
decision_state = 13A3_selected_composite_state_not_supported
selected_state_id = repair_range_participation_core_30
next_allowed_requirement = none
sequence_mining_authorized = False
effect_interpretation = total_native_effect_only
distribution_vs_state_edge_disentanglement_required = True
```

Gate 结果：

| gate | status |
|---|---|
| input_gate_status | pass |
| upstream_13a_lineage_gate_status | pass |
| upstream_13a2_lineage_gate_status | pass |
| cost_sensitivity_gate_status | pass |
| composite_readout_gate_status | pass |
| badside_gate_status | pass |
| utility_gate_status | fail |
| denominator_drift_gate_status | pass |
| morphology_independent_evidence_gate_status | fail |

结论不是“压缩修复态完全没有信号”。相反，13A3 看到的是：winner uplift 在 full-native frame 中持续为正，bad-side 相对 compression base 也没有放大；但这个读数无法转化为可授权的下一步，因为 selected state 在 validation split 的 self utility 即使 0bps 也为负，并且 robustness split 无法证明它优于 broad morphology / drawdown baseline。

因此本轮不授权 13B，不建议基于该 state 进入 sequence mining。

## 2. Lineage 与 cache 可证明性

本轮新增的可证明性审计全部通过：

| audit | pass | fail |
|---|---:|---:|
| label_lineage_audit | 14 | 0 |
| cost_buffer_lineage_audit | 3 | 0 |
| row_level_cache_audit | 19 | 0 |

关键 lineage 结论：

- 13A / 13A2 selected label 均为 `vol20d_kup2p0_kdn1p0_H20`。
- `vol_reference_id = volatility_20d`、`horizon_sessions = 20`、`k_up = 2.0`、`k_dn = 1.0` 均一致。
- 12A7g requirement 中可证明 `same_bar_priority = lower_first`。
- 13A cost buffer 来自 `thresholds.cost_buffer_bps = 100`，13A2 cost buffer 来自 `cost_buffer.default_return = 0.01`，两者与 13A3 reference cost `0.01` 一致。
- `native_panel`、`directional_filter_matrix`、`native_token_matrix` 的 `row_id` 覆盖一致，均为 431,239 行；`compression_base_panel` 为 111,299 行，且是 native rows 的子集。
- required composite states 的 membership 均为 compression base 子集，`filter true outside base = 0`。

这意味着本轮 block 不是输入、label、cost lineage 或 cache drift 导致，而是 readout gate 本身的结果。

## 3. Cost sensitivity：100bps 不是唯一杀手

### 3.1 全 13A2 candidate grid

13A2 全 candidate grid 共 162 个 filter。13A3 对它们做 cost scan 后得到：

| source_phase | status | n |
|---|---:|---:|
| 13A2_filter | no_economic_amplitude | 148 |
| 13A2_filter | cost_fragile_0bps_only | 9 |
| 13A2_filter | cost_fragile_25bps_only | 4 |
| 13A2_filter | cost_viable_50bps | 1 |
| 13A2_filter | cost_robust_100bps | 0 |

这说明“13A2 死于 100bps cost buffer”只解释了一小部分现象。即使把 cost 降到 0bps，大多数方向 filter 也无法在 validation 与 robustness 两个 split 中同时转正；真正达到 50bps 的只有 1 个，达到 100bps 的没有。

### 3.2 13A3 composite shortlist

13A3 的 6 个预注册 composite state 中，只有 `repair_ret60_volume_suspect_30` 达到 25bps；没有任何 state 达到 50bps 或 100bps：

| state_id | both validation/robustness first positive cost | at 50bps | at 100bps | status |
|---|---:|---:|---:|---|
| repair_range_participation_core_30 |  | False | False | no_economic_amplitude |
| repair_sma_participation_core_30 |  | False | False | no_economic_amplitude |
| repair_close_position_participation_core_30 |  | False | False | no_economic_amplitude |
| repair_range_participation_broad_40 |  | False | False | no_economic_amplitude |
| repair_ret60_volume_suspect_30 | 25bps | False | False | cost_fragile_25bps_only |
| repair_drawdown_amount_suspect_30 |  | False | False | no_economic_amplitude |

这条证据非常关键：如果问题只是 100bps 过严，应该看到多个 state 在 25bps/50bps 下稳定转正；实际只有一个 morphology-suspect state 在 25bps 转正，且仍不足以授权 13A4。

## 4. Full-native readout：winner uplift 存在，但同时伴随左尾抬升

Train-selected state 是 `repair_range_participation_core_30`，即：

```text
volatility_20d bottom 20%
+ distance_from_20d_low top 30%
+ turnover_zscore_20d top 30%
```

Selected state 的 full-native readout：

| split | treated_n | positive_n | coverage | captured_positive | winner_rate | native_winner_rate | winner_diff | lower_first | native_lower_first | lower_uplift | fast_fail | native_fast_fail | fast_fail_uplift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 6,232 | 1,926 | 2.87% | 6.12% | 30.91% | 14.52% | 16.39pp | 40.47% | 34.46% | 6.01pp | 11.30% | 8.33% | 2.96pp |
| validation | 2,627 | 542 | 4.28% | 9.22% | 20.63% | 9.59% | 11.04pp | 44.42% | 39.93% | 4.49pp | 10.09% | 7.85% | 2.24pp |
| robustness | 4,813 | 1,121 | 3.68% | 6.29% | 23.29% | 13.64% | 9.65pp | 33.76% | 26.96% | 6.80pp | 10.70% | 6.73% | 3.97pp |

这张表给出两个同时成立的事实：

1. Winner uplift 很强：validation +11.04pp，robustness +9.65pp。
2. 相对 full-native baseline，lower-first 与 fast-fail 也同步抬升：validation lower-first +4.49pp、fast-fail +2.24pp；robustness lower-first +6.80pp、fast-fail +3.97pp。

因此，full-native readout 支持“压缩修复态是一个高事件强度状态”，但不支持“它天然是单边 winner state”。它仍然带有 13A/13A2 反复出现的双尾特征。

所有 6 个 composite state 在 validation/robustness 的 winner 与 left-tail 读数如下：

| state_id | split | treated_n | coverage | winner_rate | winner_diff | lower_first | lower_uplift | fast_fail | fast_fail_uplift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| repair_range_participation_core_30 | validation | 2,627 | 4.28% | 20.63% | 11.04pp | 44.42% | 4.49pp | 10.09% | 2.24pp |
| repair_range_participation_core_30 | robustness | 4,813 | 3.68% | 23.29% | 9.65pp | 33.76% | 6.80pp | 10.70% | 3.97pp |
| repair_sma_participation_core_30 | validation | 2,950 | 4.81% | 21.12% | 11.53pp | 43.93% | 4.00pp | 10.24% | 2.39pp |
| repair_sma_participation_core_30 | robustness | 5,839 | 4.47% | 23.84% | 10.20pp | 33.89% | 6.93pp | 10.89% | 4.16pp |
| repair_close_position_participation_core_30 | validation | 2,985 | 4.87% | 21.04% | 11.45pp | 44.22% | 4.29pp | 10.22% | 2.37pp |
| repair_close_position_participation_core_30 | robustness | 5,814 | 4.45% | 23.87% | 10.24pp | 33.73% | 6.77pp | 10.58% | 3.84pp |
| repair_range_participation_broad_40 | validation | 4,265 | 6.96% | 19.48% | 9.89pp | 45.58% | 5.65pp | 10.69% | 2.84pp |
| repair_range_participation_broad_40 | robustness | 8,236 | 6.31% | 22.94% | 9.30pp | 33.37% | 6.40pp | 10.77% | 4.04pp |
| repair_ret60_volume_suspect_30 | validation | 3,345 | 5.46% | 23.41% | 13.82pp | 37.97% | -1.96pp | 9.66% | 1.81pp |
| repair_ret60_volume_suspect_30 | robustness | 7,123 | 5.45% | 22.28% | 8.64pp | 35.17% | 8.21pp | 11.40% | 4.67pp |
| repair_drawdown_amount_suspect_30 | validation | 2,840 | 4.63% | 19.01% | 9.42pp | 43.77% | 3.84pp | 10.42% | 2.57pp |
| repair_drawdown_amount_suspect_30 | robustness | 5,356 | 4.10% | 25.35% | 11.72pp | 33.40% | 6.44pp | 13.44% | 6.71pp |

共同模式很清楚：所有 state 的 winner_diff 都为正，但多数 state 的 lower-first / fast-fail 也高于 native baseline。唯一在 validation lower-first 低于 native 的是 `repair_ret60_volume_suspect_30`，但它在 robustness 中 lower-first 又高出 8.21pp，且只在 25bps 下脆弱转正。

## 5. Bad-side / utility：相对 compression base 好转，但 self utility 不够

Bad-side primary gate 使用 `vs_compression_base`，不是 `vs_native`。原因是 13A3 的 state 本身继承了 compression base；primary bad-side 问题是“repair state 是否降低 compression base 的左尾风险”。

Selected state 在 validation/robustness 下：

| split | cost | upper_first | lower_first | fast_fail | lower_uplift_vs_compression_base | fast_fail_uplift_vs_compression_base | utility_per_entry | utility_total_indexed | margin_vs_native | margin_vs_compression_base | badside | utility |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| validation | 0bps | 20.63% | 44.42% | 10.09% | -3.77pp | -2.95pp | -18.10bp | -0.78bp | 176.86bp | 34.03bp | pass | fail |
| validation | 25bps | 20.63% | 44.42% | 10.09% | -3.77pp | -2.95pp | -43.10bp | -1.85bp | 200.79bp | 41.60bp | pass | fail |
| validation | 50bps | 20.63% | 44.42% | 10.09% | -3.77pp | -2.95pp | -68.10bp | -2.92bp | 224.72bp | 49.16bp | pass | fail |
| validation | 75bps | 20.63% | 44.42% | 10.09% | -3.77pp | -2.95pp | -93.10bp | -3.99bp | 248.64bp | 56.72bp | pass | fail |
| validation | 100bps | 20.63% | 44.42% | 10.09% | -3.77pp | -2.95pp | -118.10bp | -5.06bp | 272.57bp | 64.28bp | pass | fail |
| robustness | 0bps | 23.29% | 33.76% | 10.70% | -0.73pp | 0.05pp | 74.44bp | 2.74bp | -0.01bp | -6.34bp | pass | fail |
| robustness | 25bps | 23.29% | 33.76% | 10.70% | -0.73pp | 0.05pp | 49.44bp | 1.82bp | 24.07bp | 1.69bp | pass | pass |
| robustness | 50bps | 23.29% | 33.76% | 10.70% | -0.73pp | 0.05pp | 24.44bp | 0.90bp | 48.15bp | 9.72bp | pass | pass |
| robustness | 75bps | 23.29% | 33.76% | 10.70% | -0.73pp | 0.05pp | -0.56bp | -0.02bp | 72.22bp | 17.75bp | pass | fail |
| robustness | 100bps | 23.29% | 33.76% | 10.70% | -0.73pp | 0.05pp | -25.56bp | -0.94bp | 96.30bp | 25.78bp | pass | fail |

这个表说明：

- Bad-side 是过的：validation 相对 compression base 的 lower-first 降 3.77pp、fast-fail 降 2.95pp；robustness lower-first 降 0.73pp、fast-fail 仅高 0.05pp，仍低于 1pp 容差。
- Utility 没过：validation 的 `utility_proxy_per_entry` 在 0bps 已经是 -18.10bp，说明不是 100bps cost 单独压死；它在无 cost 下也没有正 per-entry 经济幅度。
- Robustness 比 validation 好，但不稳定：robustness 在 25/50bps per-entry 为正，75/100bps 转负；validation 全 cost tier 皆负。

因此，13A3 的 blocking point 不是 bad-side，而是 utility amplitude 不足。

## 6. Morphology independent evidence：robustness 仍输给 broad drawdown morphology

Selected state 的 morphology anchor 在 validation/robustness 都指向 `max_drawdown_20d`。这意味着 13A3 的 repair state 虽然表面上是“压缩 + 位置不弱 + 参与恢复”，但在 out-of-sample 稳健段里仍与 broad drawdown / reversal morphology 同向。

Selected state 在 route cost tier 下：

| split | cost | top_anchor | state_auc | broad_auc | auc_margin | utility_margin_vs_broad | utility_margin_vs_compression_base | independent_evidence |
|---|---:|---|---:|---:|---:|---:|---:|---|
| validation | 50bps | max_drawdown_20d | 0.5273 | 0.6073 | -0.0800 | 3.10bp | 49.16bp | pass |
| validation | 100bps | max_drawdown_20d | 0.5273 | 0.6073 | -0.0800 | 2.60bp | 64.28bp | pass |
| robustness | 50bps | max_drawdown_20d | 0.5151 | 0.5907 | -0.0756 | -6.82bp | 9.72bp | morphology_rediscovery_without_independent_utility |
| robustness | 100bps | max_drawdown_20d | 0.5151 | 0.5907 | -0.0756 | -4.52bp | 25.78bp | morphology_rediscovery_without_independent_utility |

关键点：

- AUC 从来没有赢过 broad morphology baseline：validation AUC margin = -0.0800，robustness AUC margin = -0.0756。
- Validation 的 utility margin vs broad 为正，但 robustness 转负：50bps 为 -6.82bp，100bps 为 -4.52bp。
- vs compression base 的 margin 为正，不足以通过 morphology gate；requirement 要求同时优于 broad morphology 与 compression base。

所以 13A3 没有证明 selected repair state 是独立于 broad drawdown/reversal 的新发现。它更像是 broad morphology 的一个可解释子状态，而不是可直接进入 sequence mining 的独立 event state。

## 7. Denominator drift：没有 extreme fail，但存在分布解释风险

Selected state 没有触发 `fail_extreme_drift`，因此 denominator drift gate = pass。但 caveat 很明显：

| split | axis | bucket | treated_n | treated_share | native_share | complement_share | treated-native | treated-complement | status |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| train | year | 2019 | 6,232 | 0.423 | 0.235 | 0.230 | 0.188 | 0.194 | caveat_relative_drift |
| train | year | 2021 | 6,232 | 0.194 | 0.353 | 0.357 | -0.158 | -0.163 | caveat_relative_drift |
| train | liquidity | median_ratio | 6,232 | 0.466 | 1.000 | 0.457 | -0.534 | 0.009 | caveat_relative_drift |
| validation | year | 2022 | 2,627 | 0.219 | 0.379 | 0.386 | -0.160 | -0.167 | caveat_relative_drift |
| validation | year | 2023 | 2,627 | 0.781 | 0.621 | 0.614 | 0.160 | 0.167 | caveat_relative_drift |
| train/validation/robustness | regime | risk_on | all | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | regime_single_bucket_caveat |

解释：

- Calendar drift 不小：train 明显偏 2019，validation 明显偏 2023。
- Liquidity drift 显示 selected state 的 `money_median_20d` 中位数约为 native 的 46.6%，虽然没有达到 extreme fail，但它不是一个与 native denominator 完全同分布的状态。
- Regime 只有 `risk_on`，本轮没有跨 regime 独立证据。

这进一步强化了 requirement 中的限制：即使 13A3 有 positive readout，也只能解释为 `total_native_effect`，不能解释为已经证明 `pure_conditional_state_edge`。

## 8. Findings

### Finding 1: 信号方向存在，但不是可部署 edge

6 个 composite state 在 validation/robustness 的 winner_diff 全部为正，范围大约为 +8.64pp 到 +13.82pp。这说明 13A2 报告里“compression 内方向信号存在”的判断没有错。

但 winner_diff 不是最终授权条件。13A3 要求同时满足 bad-side、utility、morphology independent evidence。最终失败发生在 utility 与 morphology，不是 winner readout。

### Finding 2: 100bps cost buffer 不是主因

Selected state 在 validation split 的 `utility_proxy_per_entry`：

```text
0bps   = -18.10bp
25bps  = -43.10bp
50bps  = -68.10bp
75bps  = -93.10bp
100bps = -118.10bp
```

由于 0bps 已经为负，降低 cost 不能救 selected state。全 13A2 grid 中也只有 1/162 个 candidate 达到 50bps，0/162 达到 100bps。结论应是“多数方向/修复信号经济幅度不足”，而不是“100bps 参数过严导致误杀”。

### Finding 3: Bad-side 相对 compression base 是改善的

Selected state 的 bad-side primary gate 通过，这一点很重要。Validation 相对 compression base：

```text
lower_first_uplift_vs_compression_base = -3.77pp
fast_fail_uplift_vs_compression_base   = -2.95pp
```

Robustness：

```text
lower_first_uplift_vs_compression_base = -0.73pp
fast_fail_uplift_vs_compression_base   = +0.05pp
```

这说明 “repair” 这个词不是空的：在 compression cohort 内，它确实降低了部分左尾风险。但降低 compression left-tail 不等于 full-native winner edge 可部署，因为它仍然没有足够 per-entry utility，也没有独立于 broad morphology。

### Finding 4: Morphology rediscovery 是更硬的 blocker

Robustness split 下，selected state 对 broad morphology 的 utility margin 为负：

```text
50bps:  utility_margin_vs_broad = -6.82bp
100bps: utility_margin_vs_broad = -4.52bp
```

同时 broad morphology AUC 明显更高：

```text
state_auc = 0.5151
broad_morphology_baseline_auc = 0.5907
auc_margin = -0.0756
```

因此，即使 selected state 在 compression base 上有改善，也没有证明它优于 broad drawdown/reversal morphology。这个失败模式与 13A 的核心教训一致：看起来更精细的事件定义，仍可能只是 broad morphology 的换皮。

### Finding 5: 13A3 不应开启 13B

13A3 的正面证据是：

- full-native winner uplift 稳定为正；
- bad-side 相对 compression base pass；
- lineage/cache/cost 可证明性全部 pass。

13A3 的负面证据是：

- selected state validation 0bps self utility 已为负；
- required composite shortlist 中没有任何 state 达到 50bps/100bps 双 split self utility；
- robustness morphology independent evidence fail；
- denominator drift 存在 calendar/liquidity caveat；
- regime 只有 risk_on，缺少跨 regime 证据。

这些证据合在一起，不支持进入 sequence mining。

## 9. Research insight

13A3 把 13A2 的失败进一步拆开了：

```text
13A2: 方向信号存在，但 compression-control matched control 装不下。
13A3: 把它改成 full-native composite state 后，winner uplift 仍存在；
      但经济幅度不足，并且 robustness 上输给 broad drawdown morphology。
```

这说明下一步不应该继续在 compression repair state 上做更复杂的 sequence mining。复杂化很可能只会把 broad morphology 的 timing 切得更细，而不是发现新的独立 event edge。

更合理的研究方向有两个：

1. 如果继续 winner discovery，必须先做 confirmatory-style 的 denominator-balanced / morphology-orthogonal preflight，而不是直接 13B。
2. 如果目标是 practical insight，应把 compression repair state 转为 defense / participation 研究对象：它更像“高事件强度状态下左尾可部分缓解的子群”，而不是“可直接买入的 winner event”。

当前 requirement 的正式裁决是 `next_allowed_requirement = none`。因此，除非新建一份专门的 confirmatory / morphology-orthogonal requirement，否则 Episode 13 的 winner discovery branch 应暂时停止在 13A3。

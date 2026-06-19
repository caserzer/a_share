# 12A4 State-change Meta-label Filter Feasibility 决策报告

## 1. 决策

最终状态：

```text
12A4_meta_label_partial_feature_source
```

12A4 没有把 state-change C0 升级为 timing selector。它更适合继续作为低密度、低重复、PIT 可执行的特征源，而不是独立择时信号。

核心原因是：最强 primary model 确实把 robustness top bucket precision 从 C0 base 的 7.94% 提到 11.86%，但没有通过 supported gate。真正卡住的是 `lift_vs_c0`，对应 binding-implied precision 为 13.90%；当前 11.86% 还差 2.04 pct。与此同时，top bucket bad-side 从 C0 baseline 的 28.12% 升到 40.59%，说明 precision uplift 不是免费得到的。

## 2. Risk-on 同口径 baseline

12A4 已把 primary scope 限定在 `market_regime_bucket = risk_on`。R-core 也按 08 feature panel 的真实 risk_on scope 过滤，而不是按 `risk_on_transition_union` 文本推断。过滤后，R-core risk_on universe 为 30,790 行；另有 17,124 行 transition R-core 事件被排除。

| source | split | event_n | low_to_high_n | precision | pre120 precision | episode recall | dup 10d | bad-side | winner 120d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C0 | all | 15,113 | 1,015 | 6.72% | 6.58% | 93.93% | 5.86% | 34.03% | 16.65% |
| C0 | train | 8,303 | 602 | 7.25% | 6.01% | 95.56% | 6.37% | 38.46% | 17.05% |
| C0 | validation | 2,151 | 43 | 2.00% | 1.86% | 86.36% | 3.95% | 29.75% | 6.42% |
| C0 | robustness | 4,659 | 370 | 7.94% | 9.77% | 92.82% | 5.80% | 28.12% | 20.65% |
| R-core | all | 30,790 | 2,152 | 6.99% | 7.24% | 93.69% | 54.43% | 37.38% | 17.21% |
| R-core | train | 16,603 | 1,283 | 7.73% | 6.84% | 98.22% | 55.97% | 42.03% | 17.91% |
| R-core | validation | 4,457 | 75 | 1.68% | 1.79% | 90.91% | 47.23% | 31.43% | 6.69% |
| R-core | robustness | 9,730 | 794 | 8.16% | 10.42% | 88.40% | 54.68% | 32.17% | 20.86% |

关键读数：

- C0 robustness precision 为 7.94%，R-core 为 8.16%。在同口径 risk_on 内，C0 不赢 raw precision。
- C0 的优势在 density hygiene：robustness same-instrument 10d duplicate 为 5.80%，R-core 为 54.68%。这说明 C0 更干净，但不是更准。
- validation 段 base rate 病态偏低：C0 只有 43 个正样本、precision 2.00%；R-core 也只有 1.68%。因此 validation 不能用于选 threshold，只能作为 readout。

## 3. Validation threshold health

Validation health 没通过：

| metric | value |
|---|---:|
| train event_n / positive_n | 8,303 / 602 |
| train base precision | 7.25% |
| validation event_n / positive_n | 2,151 / 43 |
| validation base precision | 2.00% |
| validation event gate | pass |
| validation positive gate | fail |
| validation base-rate health gate | fail |
| threshold source | `train_internal_cv` |

这个结果是健康的 fail-safe。validation 不是正常低一点，而是比 train 低约 72%。如果在 validation 上选 top bucket，阈值会被个位数到十几个 positive 主导，结论没有稳定性。

## 4. Primary model frontier

Primary models 只使用 C0 risk_on rows；R-core rows 只用于 baseline、prior interaction feature 和 readout。所有模型的 threshold 均来自 train reference percentile。

Robustness top bucket：

| model | bucket | event_n | positive_n | precision | episode recall | bad-side | lift vs C0 | lift vs R-core | lift vs best non-model |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| shallow tree depth-3 | top10 | 1,535 | 182 | 11.86% | 61.88% | 40.59% | 1.493x | 1.453x | 1.072x |
| shallow tree depth-3 | top20 | 1,535 | 182 | 11.86% | 61.88% | 40.59% | 1.493x | 1.453x | 1.072x |
| scorecard | top10 | 758 | 87 | 11.48% | 32.04% | 51.98% | 1.445x | 1.407x | 1.038x |
| scorecard | top20 | 1,254 | 126 | 10.05% | 43.09% | 47.53% | 1.265x | 1.231x | 0.908x |
| logistic L1 | top20 | 4,155 | 354 | 8.52% | 88.40% | 27.08% | 1.073x | 1.044x | 0.770x |
| logistic L2 | top20 | 4,187 | 355 | 8.48% | 88.95% | 27.13% | 1.068x | 1.039x | 0.766x |

Shallow tree 是最强 primary model，但 top10 和 top20 选中同一批 1,535 个事件。这是 depth-3 tree score 离散导致的 threshold tie expansion，不是一个真正更尖锐的 top10 分层。因此 top10 precision 11.86% 仍低于 supported gate 的 12.00%。

Validation readout 进一步说明不能过度解释模型：

- shallow tree validation top20 precision 为 2.76%，只捕获 12 个 positive；
- scorecard validation top20 precision 为 2.93%，只捕获 8 个 positive；
- logistic validation top20 precision 约 1.81%-1.86%，低于 C0 validation base rate 2.00%。

结论：primary model 有风险分层能力，但稳定性证据主要来自 robustness，validation 段只能证明该 split 不适合选阈值。

## 5. Supported gate 缺口

| gate | required | realized | binding-implied precision | pass |
|---|---:|---:|---:|---|
| top20 abs precision | 10.00% | 11.86% | 10.00% | pass |
| top10 abs precision | 12.00% | 11.86% | 12.00% | fail |
| lift vs R-core | 1.50x | 1.453x | 12.24% | fail |
| lift vs C0 | 1.75x | 1.493x | 13.90% | fail |
| lift vs best non-model | 1.20x | 1.072x | 13.27% | fail |

最严格的约束是 `lift_vs_c0`。因为 C0 robustness base precision 为 7.94%，1.75x 要求 top20 precision 达到 13.90%。当前 top20 为 11.86%，不是微小舍入误差，而是模型分层上限和 gate 之间仍有明显距离。

## 6. Non-model baseline

Non-model frontier 显示，primary model 的大部分 uplift 可以被简单排序规则解释。

Robustness top20：

| non-model frontier | score feature | event_n | positive_n | precision | episode recall | bad-side | lift vs C0 | lift vs R-core |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| density only | same_day_c0_event_count_all | 1,139 | 126 | 11.06% | 50.83% | 31.17% | 1.393x | 1.356x |
| freshness decay only | freshness_decay_tau_20 | 1,012 | 104 | 10.28% | 44.20% | 28.26% | 1.294x | 1.259x |
| R-core interaction only | prior_r_core_event_count_20d | 989 | 101 | 10.21% | 38.67% | 30.64% | 1.286x | 1.251x |
| volume acceleration/decay | volume_slope_accel_5_15d | 895 | 83 | 9.27% | 39.78% | 30.39% | 1.168x | 1.136x |
| entropy disorder | return_sign_entropy_20d | 1,614 | 122 | 7.56% | 43.09% | 33.02% | 0.952x | 0.926x |
| path/rank | momentum_percentile_20d | 1,013 | 73 | 7.21% | 28.73% | 43.63% | 0.907x | 0.883x |
| family only | family_prior_train_badside_rate | 1,131 | 71 | 6.28% | 34.81% | 31.30% | 0.790x | 0.769x |

主要 insight：

- 最强 non-model 是 density，而不是 family、entropy 或 volume。
- freshness 和 R-core prior interaction 有真实增量，但强度不够。
- primary shallow tree top20 11.86% 只比 density-only 11.06% 高 0.79 pct，lift vs best non-model 只有 1.072x，低于 1.20x gate。
- 这意味着 meta-label model 目前更多是在组合 density / freshness / R-core crowding，而不是发现一个稳定的新择时维度。

## 7. Bad-side tradeoff

Precision uplift 明显伴随 bad-side 上升：

| population | precision | bad-side |
|---|---:|---:|
| C0 robustness baseline | 7.94% | 28.12% |
| R-core robustness baseline | 8.16% | 32.17% |
| density-only top20 | 11.06% | 31.17% |
| shallow tree top20 | 11.86% | 40.59% |
| scorecard top20 | 10.05% | 47.53% |
| LightGBM top20 | 12.14% | 37.80% |

这条 tradeoff 很关键：模型不是简单把坏事件过滤掉，而是更倾向选择更拥挤、更活跃、更剧烈的状态。这样的状态更容易落入 low_to_high window，也更容易暴露在 fast-fail / false-repair 侧。因此 12A4 不能只看 precision uplift；bad-side 是当前不支持升级为 timing selector 的重要原因。

## 8. Active-state carry-forward readout

Active-state carry-forward 只作为 missed episode 诊断，不作为 t0 precision uplift。

Robustness diagnostic：

| horizon | event_n | carried_inside_n | diagnostic carry precision |
|---:|---:|---:|---:|
| 5 | 4,659 | 375 | 8.05% |
| 10 | 4,659 | 391 | 8.39% |
| 20 | 4,659 | 422 | 9.06% |
| 40 | 4,659 | 514 | 11.03% |
| 60 | 4,659 | 596 | 12.79% |

读数随 horizon 单调上升，这是定义上预期的结果：窗口拉长，事件 active interval 更容易覆盖 episode。它支持“missed episode 前序 state-change 没有完全失效”的解释，但不能说明 t0 当天 precision 变高。

## 9. Entropy 与 volume acceleration

Feature dictionary 共 96 个 feature，其中 89 个允许 primary model 使用。按 group：

| feature group | feature_n | allowed_n | diagnostic_n |
|---|---:|---:|---:|
| event native | 24 | 24 | 0 |
| pre-event path | 16 | 16 | 0 |
| volume acceleration/decay | 12 | 11 | 1 |
| r-core interaction | 11 | 9 | 2 |
| entropy path disorder | 10 | 8 | 2 |
| risk-on market context | 8 | 8 | 0 |
| freshness decay | 5 | 5 | 0 |
| failure history | 5 | 5 | 0 |
| density crowding | 3 | 3 | 0 |
| population audit | 2 | 0 | 2 |

Entropy audit：

- `gaussian_return_entropy_20d` 和 `gaussian_return_entropy_60d` 与 volatility 完全冗余，`max_abs_redundancy_corr = 1.0000`，已降级 diagnostic-only。
- 非 Gaussian 的 sign / transition / range entropy 没有被 redundancy audit 拦截，但 non-model entropy top20 precision 只有 7.56%，低于 C0 和 R-core base。
- 结论：entropy 可以保留为 path disorder 描述变量，但当前不是 precision uplift 的来源。

Volume audit：

- `volume_zscore_20d` 与 turnover/volatility 冗余，robustness `max_abs_redundancy_corr = 0.9792`，已降级 diagnostic-only。
- `log_volume_accel_*`、`volume_z_accel_*`、`turnover_z_accel_*`、slope acceleration 等大多通过 redundancy audit，且使用 train-frozen winsorization cutoffs。
- 但 volume acceleration/decay non-model top20 precision 只有 9.27%，弱于 density、freshness 和 R-core interaction。
- 结论：volume acceleration 是有用的二级状态变量，但不是 12A4 的主导过滤器。

## 10. LightGBM challenger

LightGBM 作为 diagnostic-only challenger 已评估，不能触发 12A4 supported。

Robustness：

| bucket | event_n | positive_n | precision | episode recall | bad-side | lift vs C0 | lift vs R-core | lift vs best non-model |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| top10 | 850 | 116 | 13.65% | 44.20% | 41.18% | 1.718x | 1.672x | 1.234x |
| top20 | 1,590 | 193 | 12.14% | 61.33% | 37.80% | 1.528x | 1.487x | 1.097x |

LightGBM top10 达到 13.65%，说明低容量 primary model 可能漏掉了一些非线性交互。但 top20 仍低于 `lift_vs_c0 = 1.75x` 的 implied 13.90%，也低于 `lift_vs_best_non_model = 1.20x` 所需的 13.27%。更重要的是，bad-side 仍为 37.80%，显著高于 C0 baseline。

因此 LightGBM 的结论不是“可以支持 state-change timing selector”，而是：如果后续进入 12A5，应把 nonlinear interaction 当作 morphology feature modeling 的候选，而不是在 12A4 直接放行。

## 11. Findings

1. C0 在 risk_on 内不赢 raw precision，但赢 density hygiene。
   C0 robustness precision 7.94%，R-core 8.16%；但 C0 10d duplicate 只有 5.80%，R-core 是 54.68%。这说明 C0 是更干净的事件源，不是更强的裸择时源。

2. Meta-labeling 有 uplift，但未突破 supported gate。
   Shallow tree top20 precision 11.86%，相对 C0 lift 1.493x，相对 R-core lift 1.453x。方向正确，但仍低于 1.75x / 1.50x supported 要求。

3. 当前 uplift 主要来自 density / freshness / R-core crowding。
   Density-only top20 已达 11.06%，freshness 10.28%，R-core interaction 10.21%。Primary model 只是在这些简单信号上再提高 0.79 pct，增量不足。

4. Precision 提升伴随 bad-side 上升。
   C0 baseline bad-side 28.12%，shallow tree top20 为 40.59%，LightGBM top20 为 37.80%。这更像“选择更活跃/更拥挤的高波动状态”，不是纯粹过滤坏事件。

5. Validation split 不能承担 threshold selection。
   validation 只有 43 个 C0 positive，base precision 2.00%，与 train / robustness 差距过大。12A4 使用 train internal CV 是必要的防噪声设计。

6. Entropy 与 volume acceleration 的角色应降级。
   Entropy 非冗余但没有 standalone uplift；volume acceleration 非冗余但 uplift 弱于 density/freshness/R-core interaction。它们可以保留为 12A5 feature，但不应成为 12A4 决策主线。

## 12. Insight 与后续建议

12A4 的最重要结论不是“模型完全无效”，而是：

```text
state-change 事件是干净的状态特征源，
但在 risk_on 内作为 timing selector 的 precision 上限仍接近 base-rate / density-crowding frontier。
```

如果继续推进，不建议再做“换一组 state-change event definition”或“继续调 family priority”。12A3/12A4 已经显示，事件定义层面的改动很难突破 precision base rate。更合理的下一步是 12A5 morphology feature modeling，但必须改变目标：

- 不把 12A5 目标设为“证明 state-change 本身可择时”；
- 把目标设为“在 state-change + density/freshness/R-core interaction 之后，是否存在可稳定降低 bad-side 的 observed morphology filter”；
- 重点观察 top bucket bad-side 是否回落，而不是只追求 precision 从 11.9% 到 12%-13%；
- LightGBM 可以作为 nonlinear search readout，但 supported 决策仍应要求低容量模型或稳定 scorecard 复现。

当前建议：

```text
stop_state_change_as_timing_signal_keep_feature_source
```

如果进入 12A5，研究标题应更接近：

```text
12A5_state_change_morphology_badside_reduction_feasibility
```

而不是继续叫 filter feasibility。下一阶段真正要解决的不是“能不能多抓到 low_to_high”，而是“能不能在不显著牺牲 recall 的情况下，把 12A4 top bucket 的 bad-side 从 40% 附近压回 C0 baseline 附近”。

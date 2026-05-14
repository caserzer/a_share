# R03a 概率型 Survival-Step 可行性研究报告

## 结论摘要

本实验的最终结论是：`blocked_no_stable_candidate_bucket`。

这不是校验失败，也不是 survival 结构无效。相反，数据清楚显示：**survival checkpoint 是一个很强的观察结构**，尤其是 T+10 后，候选 episode 的 `P_good` 明显提高，`P_bad` 明显下降。但是，R03a 试图进一步冻结一个 probability posterior bucket 作为 staged step-up 候选时，所有候选都没有通过 train 侧样本、置信区间和 baseline_3 对比门槛。因此，本轮不能产出可执行 candidate、不能进入 EV_R sizing、不能给出 1R 或 production signal。

关键判断：

- `baseline_3_probe_survival_step_up` 相比 T0 entry/probe-only，在 train、validation、robustness 三段都显著改善 `P_good` 和 `P_bad`。
- 进一步加 probability gate 后，确实能看到一些高 edge 小 bucket，但 denominator 太小，不能冻结。
- denominator 足够大的 bucket 又没有稳定超过 baseline_3。
- `fresh evidence`、`same-day bundle`、`context bucket` 在 R03a 中只允许描述性分析，不允许作为 gate。
- R03a 的研究价值是确认 survival-step 的方向值得保留，但否定了当前版本的 probability-bucket 冻结条件。

## 实验边界

R03a 是 probability-only feasibility audit，不是 EV_R sizing 实验。报告中的 R 标签只作为固定 exposure schedule label，不代表已经验证的仓位规模。

边界状态：

| 项目 | 状态 | 含义 |
|---|---|---|
| final_decision | `blocked_no_stable_candidate_bucket` | 没有可冻结 candidate |
| validation_status | `passed` | 输出结构和约束检查通过 |
| risk_budget_status | `probability_only_ev_r_blocked` | 不能做 EV_R / sizing |
| ev_r_status | `blocked_missing_ev_r` | 缺少 EV_R 输入 |
| background_denominator_status | `blocked_missing_denominator` | 不能构造 market-wide background baseline |
| split_stability_status | `partial_only` | 只能做 partial diagnostic |
| train candidate rows | `180` | candidate grid 已物化 |
| train eligible rows | `0` | 没有候选通过 gate |

本次报告更新只基于已生成的结构化输出文件，不改变脚本、配置或实验代码。

## 数据与校验状态

输入 readiness 全部满足：16 个 required input 全部存在，其中 2 个带 validation 的输入均为 `passed`，其余为 `not_applicable`。

输出校验状态：

| 检查项 | 结果 |
|---|---:|
| validation audit checks | 72 |
| passed checks | 72 |
| failed checks | 0 |
| required output files | 全部存在 |
| final decision allowed | passed |
| forbidden report language absent | passed |

主要输出文件：

- `r03a_t0_episode_prior.csv`
- `r03a_survival_same_grain_lift.csv`
- `r03a_candidate_grid_train_selection.csv`
- `r03a_baseline_comparison.csv`
- `r03a_validation_robustness_readonly.csv`
- `r03a_descriptive_bundle_context_prior.csv`
- `r03a_fresh_evidence_descriptive_audit.csv`
- `r03a_null_result_audit.csv`

## T0 Prior

T0 episode prior 的全局样本为 8,609 个有效 label denominator，整体 `P_good=0.356`，`P_bad=0.613`。这说明未经过 survival checkpoint 的原始触发 episode，本身仍然是 bad-heavy 状态。

| grouping | denominator | P_good | P_bad | P_good_lower | P_bad_upper | status |
|---|---:|---:|---:|---:|---:|---|
| all | 8,609 | 0.356 | 0.613 | 0.348 | 0.622 | sufficient |
| train | 4,270 | 0.342 | 0.630 | 0.330 | 0.642 | sufficient |
| validation | 2,216 | 0.329 | 0.634 | 0.313 | 0.651 | sufficient |
| robustness | 2,123 | 0.414 | 0.557 | 0.396 | 0.575 | sufficient |

按年份看，T0 prior 波动很大：

| year | denominator | P_good | P_bad | 备注 |
|---:|---:|---:|---:|---|
| 2018 | 851 | 0.235 | 0.744 | bad-heavy 明显 |
| 2021 | 784 | 0.265 | 0.703 | bad-heavy 明显 |
| 2022 | 1,419 | 0.303 | 0.658 | bad-heavy |
| 2025 | 750 | 0.465 | 0.493 | 明显好于历史多数年份 |

这个波动解释了为什么 R03a 不能只看 pooled edge。即使全局 prior 可计算，冻结 candidate 仍需要 train 内稳定性和 denominator 约束。

按 seed family 的 T0 prior：

| seed family | denominator | P_good | P_bad | status |
|---|---:|---:|---:|---|
| multi_family_bundle | 5,376 | 0.352 | 0.621 | sufficient |
| range_breakout | 1,832 | 0.376 | 0.574 | sufficient |
| volume_money | 459 | 0.377 | 0.593 | sufficient |
| pullback_drawdown | 372 | 0.315 | 0.677 | sufficient |
| volatility_band | 191 | 0.387 | 0.581 | thin_bucket_report_only |
| price_trend | 189 | 0.323 | 0.672 | thin_bucket_report_only |
| momentum_rps | 163 | 0.337 | 0.656 | thin_bucket_report_only |
| oscillator | 27 | 0.333 | 0.630 | too_sparse_use_fallback |

研究含义：R03a 的起点并不是一个天然高胜率池，而是一个需要通过 observable survival 过滤的高噪声、高 bad-rate episode 池。

## Same-Grain Survival Lift

全局 survival lift 是本实验最强的正向发现。

| checkpoint | pre episodes | survivors | survivor rate | survivor denominator | survivor P_good | survivor P_bad | P_good lift vs T0 | P_bad lift vs T0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| T+3 | 11,003 | 8,944 | 0.813 | 7,028 | 0.437 | 0.526 | +0.080 | -0.087 |
| T+5 | 11,003 | 8,037 | 0.730 | 6,317 | 0.486 | 0.473 | +0.129 | -0.140 |
| T+10 | 11,003 | 6,560 | 0.596 | 5,149 | 0.596 | 0.353 | +0.239 | -0.260 |

解释：

- survival 时间越长，episode 池越小，但质量显著提高。
- T+10 的 `P_good=0.596`，已经从 T0 的 bad-heavy 状态切换到 good-favored 状态。
- T+10 的 `P_bad=0.353`，相对 T0 下降 26.0 个百分点。
- 这不是一个微弱信号，而是 survival 条件本身带来的大幅 posterior shift。

按 family 看，T+10 的 lift 也大多为正，但样本可信度差异很大：

| family | pre episodes | T+10 survivors | survivor denom | survivor P_good | survivor P_bad | P_good lift | P_bad lift |
|---|---:|---:|---:|---:|---:|---:|---:|
| price_trend | 235 | 111 | 88 | 0.693 | 0.295 | +0.370 | -0.377 |
| pullback_drawdown | 449 | 209 | 175 | 0.669 | 0.314 | +0.354 | -0.363 |
| momentum_rps | 195 | 96 | 81 | 0.679 | 0.309 | +0.342 | -0.348 |
| multi_family_bundle | 6,948 | 3,957 | 3,084 | 0.613 | 0.339 | +0.261 | -0.282 |
| volume_money | 590 | 382 | 294 | 0.588 | 0.364 | +0.212 | -0.229 |
| volatility_band | 238 | 157 | 125 | 0.592 | 0.360 | +0.205 | -0.221 |
| range_breakout | 2,316 | 1,622 | 1,281 | 0.538 | 0.391 | +0.162 | -0.183 |
| oscillator | 32 | 26 | 21 | 0.429 | 0.524 | +0.095 | -0.106 |

研究含义：

- survival-step 的主结论由 global 和 multi_family_bundle 支撑最强，因为 denominator 足够大。
- price_trend、pullback_drawdown、momentum_rps 的 lift 看起来更强，但 denominator 较小，置信区间更宽，不能直接升格为独立 gate。
- oscillator 样本过薄，不应作为方向性结论来源。

## Baseline 对比

Baseline 1 和 Baseline 2 的 path metrics 完全一致是预期行为，因为 EV_R blocked，`full_1r_at_t0` 和 `0.25R probe` 在本实验里只是 exposure label，不改变 episode path denominator。

核心比较应看 Baseline 3：`probe_survival_step_up`。

| split | scenario | denominator | P_good | P_bad | P_good_lower | P_bad_upper | drawdown severity p90 | max gain p75 | early failure |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | baseline_1_t0_full_entry | 4,270 | 0.342 | 0.630 | 0.330 | 0.642 | 0.443 | 0.356 | 0.442 |
| train | baseline_3_probe_survival_step_up | 2,444 | 0.597 | 0.353 | 0.581 | 0.369 | 0.418 | 0.388 | 0.000 |
| validation | baseline_1_t0_full_entry | 2,216 | 0.329 | 0.634 | 0.313 | 0.651 | 0.417 | 0.236 | 0.420 |
| validation | baseline_3_probe_survival_step_up | 1,257 | 0.580 | 0.356 | 0.557 | 0.378 | 0.379 | 0.262 | 0.000 |
| robustness | baseline_1_t0_full_entry | 2,123 | 0.414 | 0.557 | 0.396 | 0.575 | 0.343 | 0.361 | 0.311 |
| robustness | baseline_3_probe_survival_step_up | 1,448 | 0.607 | 0.351 | 0.586 | 0.372 | 0.330 | 0.382 | 0.000 |

Baseline 3 相对 Baseline 1 的变化：

| split | denominator change | P_good change | P_bad change | drawdown severity change | max gain p75 change |
|---|---:|---:|---:|---:|---:|
| train | -1,826 | +0.255 | -0.277 | -0.025 | +0.032 |
| validation | -959 | +0.251 | -0.279 | -0.038 | +0.026 |
| robustness | -675 | +0.193 | -0.206 | -0.012 | +0.021 |

研究含义：

- Baseline 3 在三个 split 都提高了 good probability，并降低 bad probability。
- improvement 不是只发生在 train，validation 和 robustness 也成立。
- survival-step 没有明显牺牲 upside，`max_gain_120d_p75` 在三个 split 中反而高于 T0 baseline。
- drawdown severity p90 在三个 split 中均低于 T0 baseline。
- 因此，**survival-step 作为观察结构是通过了方向性检验的**。

但这仍然不是 candidate pass，因为 R03a 的目标不是证明 baseline_3，而是证明“在 baseline_3 之上，是否还能冻结一个 probability posterior bucket”。这个目标没有通过。

## Candidate Grid 结果

Candidate grid 共 180 行，train eligible 为 0。

| selection_reason | count |
|---|---:|
| failed_thresholds_vs_baseline_3 | 118 |
| blocked_insufficient_denominator | 62 |

按 checkpoint：

| checkpoint | blocked_insufficient_denominator | failed_thresholds_vs_baseline_3 |
|---|---:|---:|
| T+3 | 32 | 28 |
| T+5 | 24 | 36 |
| T+10 | 6 | 54 |

按 fallback grain：

| fallback grain | blocked_insufficient_denominator | failed_thresholds_vs_baseline_3 |
|---|---:|---:|
| seed_primary_family_id | 50 | 85 |
| seed_type | 12 | 33 |

这个分布非常关键：

- 有较大 denominator 的候选主要失败于 `failed_thresholds_vs_baseline_3`。
- 看起来 edge 最大的候选主要失败于 `blocked_insufficient_denominator`。
- 这说明问题不是 grid 没覆盖到信号，而是 probability gate 目前把强 edge 压缩到了不可冻结的小样本 bucket。

Top edge 候选如下：

| scope | checkpoint | threshold | fallback | oof denom | baseline_3 denom | oof P_good | oof P_bad | P_good lower | P_bad upper | edge vs baseline_3 | reason |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| seed_same_day_family_count=1 | T+5 | 0.00 | seed_primary_family_id | 57 | 1,132 | 0.684 | 0.298 | 0.572 | 0.401 | +0.209 | blocked_insufficient_denominator |
| seed_same_day_family_count=1 | T+5 | -0.05 | seed_primary_family_id | 57 | 1,132 | 0.684 | 0.298 | 0.572 | 0.401 | +0.209 | blocked_insufficient_denominator |
| seed_type=single_family_seed | T+5 | 0.00 | seed_primary_family_id | 57 | 1,132 | 0.684 | 0.298 | 0.572 | 0.401 | +0.209 | blocked_insufficient_denominator |
| seed_type=single_family_seed | T+5 | -0.05 | seed_primary_family_id | 57 | 1,132 | 0.684 | 0.298 | 0.572 | 0.401 | +0.209 | blocked_insufficient_denominator |
| all | T+5 | 0.00 | seed_primary_family_id | 57 | 3,067 | 0.684 | 0.298 | 0.572 | 0.401 | +0.179 | blocked_insufficient_denominator |
| seed_type=single_family_seed | T+3 | -0.10 | seed_primary_family_id | 63 | 1,253 | 0.619 | 0.365 | 0.511 | 0.465 | +0.178 | blocked_insufficient_denominator |
| seed_same_day_family_count=1 | T+10 | 0.15 | seed_primary_family_id | 143 | 921 | 0.720 | 0.266 | 0.653 | 0.329 | +0.142 | blocked_insufficient_denominator |

这些行的表面信号很强，但 train OOF denominator 只有 57、63、143，不能满足冻结候选所需的 denominator/stability 约束。尤其是 denominator=57 的 T+5 bucket，虽然 `P_good=0.684`、`P_bad=0.298`，但太容易是 bucket selection noise。

大 denominator 候选的结果相反：

| scope | checkpoint | fallback | oof denom | oof P_good | oof P_bad | edge vs baseline_3 | upside capture | reason |
|---|---|---|---:|---:|---:|---:|---:|---|
| all | T+3 | seed_type | 3,411 | 0.428 | 0.536 | -0.028 | 1.000 | failed_thresholds_vs_baseline_3 |
| all | T+3 | seed_primary_family_id | 3,402 | 0.428 | 0.536 | -0.028 | 0.999 | failed_thresholds_vs_baseline_3 |
| all | T+3 | seed_primary_family_id | 3,280 | 0.429 | 0.534 | -0.025 | 1.009 | failed_thresholds_vs_baseline_3 |
| all | T+3 | seed_type | 3,157 | 0.426 | 0.538 | -0.033 | 0.993 | failed_thresholds_vs_baseline_3 |

研究含义：

- 如果 gate 放宽到足够大样本，candidate 基本退化为 baseline_3 或弱于 baseline_3。
- 如果 gate 收紧到高 edge，样本数不足，不能冻结。
- 当前 probability posterior bucket 没有证明能在 baseline_3 之上提供稳定增量。

## Null Result Audit

Null audit 共 19 条条件，其中 1 条触发：

| null condition | triggered | required conclusion |
|---|---|---|
| candidate_eligibility_threshold_smaller_than_ci_halfwidth | true | no incremental staged-posterior edge over survival step-up |

这条触发的含义是：candidate eligibility 的阈值幅度小于置信区间半宽代理，增量 edge 不足以和估计噪声区分。结合 candidate grid 的结果，本轮不能把 probability gate 的细分差异解释为稳定 alpha。

其余 null 条件未触发，包括：

- baseline_1_2_path_metric_mismatch 未触发。
- denominator_gate_not_applied 未触发。
- candidate_train_scoring_used_in_sample_posterior 未触发。
- candidate_grid_multiplicity_excessive 未触发。
- fresh evidence gate misuse 未触发。

这说明 blocked 不是由实现违约造成，而是由实验结果本身造成。

## Bundle / Context 描述性结果

`r03a_descriptive_bundle_context_prior.csv` 共 1,814 行，其中 `same_day_bundle_key` 和 `context_bucket_id` 各 907 行。

样本状态：

| status | count |
|---|---:|
| too_sparse_use_fallback | 1,256 |
| thin_bucket_report_only | 314 |
| sufficient | 210 |
| unusable | 34 |

R03a gate 状态：

| r03a_gate_status | count |
|---|---:|
| too_sparse_use_fallback | 1,256 |
| thin_report_only | 314 |
| sufficient_and_stable | 200 |
| unusable | 34 |
| unstable_do_not_freeze | 10 |

使用边界：

| field | result |
|---|---:|
| primary_gate_allowed=True | 0 |
| fallback_grain_allowed=True | 200 |
| used_by_candidate=True | 0 |
| context risk bucket unavailable | 907 |

研究含义：

- same-day bundle 和 context bucket 在 R03a 中没有作为 primary gate 使用，这是正确的。
- 即使有 200 行 `sufficient_and_stable`，也没有被 candidate 使用，因为 requirement 限定了这些字段只能 descriptive/fallback-only。
- context bucket 的 `entry_risk_pct_bucket` 全部不可用，原因是 EV_R 缺失，所以不能把 context 解释为 risk-aware gate。

部分高 `P_good` 的 bundle/context 行：

| bundle/context | split/year | denominator | P_good | P_bad | status |
|---|---|---:|---:|---:|---|
| oscillator\|range_breakout\|volatility_band\|volume_money | validation/2023 | 106 | 0.642 | 0.302 | thin_report_only |
| range_breakout\|volatility_band | validation/2023 | 172 | 0.570 | 0.355 | thin_report_only |
| oscillator\|range_breakout\|volume_money | robustness/2025 | 120 | 0.533 | 0.417 | thin_report_only |
| range_breakout | train/2017 | 331 | 0.532 | 0.438 | sufficient_and_stable |
| oscillator\|range_breakout | validation/2023 | 218 | 0.518 | 0.417 | sufficient_and_stable |

这些行适合作为后续研究线索，但不能在 R03a 中升级为 gate。原因有三点：

- 很多高 `P_good` 行只是 thin report，不满足冻结要求。
- split/year context 可能反映局部 regime，而不是稳定规则。
- EV_R 缺失导致 risk context 不完整。

## Fresh Evidence 描述性结果

Fresh evidence audit 共 18 行，全部 `gate_use_allowed=False`。

状态分布：

| fresh_evidence_status | count |
|---|---:|
| found_within_t3_t30 | 6 |
| ambiguous_same_offset | 5 |
| seed_failed_before_fresh | 4 |
| censored_before_t30 | 1 |
| none_within_t3_t30 | 1 |
| seed_failed_before_t3 | 1 |

Offset 分布：

| fresh_offset_bucket | count |
|---|---:|
| none | 6 |
| T3_T5 | 4 |
| T6_T10 | 4 |
| T11_T20 | 2 |
| censored | 1 |
| T21_T30 | 1 |

有 denominator 的描述性行：

| status | offset | conditioning | denominator | P_good | P_bad | fresh_before_failure_rate |
|---|---|---|---:|---:|---:|---:|
| found_within_t3_t30 | T3_T5 | survived_t3 | 3,092 | 0.569 | 0.403 | 0.705 |
| found_within_t3_t30 | T6_T10 | survived_t5 | 839 | 0.563 | 0.372 | 0.706 |
| found_within_t3_t30 | T11_T20 | survived_t10 | 546 | 0.584 | 0.341 | 0.630 |
| found_within_t3_t30 | T3_T5 | survived_t5 | 296 | 0.625 | 0.328 | 0.615 |
| none_within_t3_t30 | none | survived_t10 | 216 | 0.620 | 0.329 | NA |
| found_within_t3_t30 | T6_T10 | survived_t10 | 142 | 0.599 | 0.345 | 0.627 |
| found_within_t3_t30 | T21_T30 | survived_t10 | 117 | 0.607 | 0.282 | 0.519 |
| seed_failed_before_fresh | none | survived_t10 | 520 | 0.081 | 0.848 | NA |

研究含义：

- fresh evidence 看起来有 sequencing 信息，但它不是 R03a 的合法 gate。
- `seed_failed_before_fresh` 的 bad-heavy 特征非常明显，尤其 `not_survived_t3/t5/t10` 行是 `P_bad=1.000`，这本质上是 survival failure 的标签后果，不应被当作独立 fresh gate。
- `found_within_t3_t30` 行的 `P_good` 多在 0.56 到 0.63，但必须通过独立 sequence/hazard diagnostic 才能判断它是增量信号、幸存者偏差，还是 survival checkpoint 的同义重复。

## 研究发现

### 1. Survival-step 是当前最可靠的结构

T+10 survival 把全局 episode 从 `P_good=0.356 / P_bad=0.613` 移动到 `P_good=0.596 / P_bad=0.353`。这个变化在 train、validation、robustness 的 baseline_3 对比中都能看到。

这说明“先 probe，等 observable survival，再 step-up”的方向，比“在 T0 直接 full entry”更符合当前数据。

### 2. Probability bucket 没有证明增量可冻结

R03a 的核心失败点不是没有找到高 edge，而是高 edge 不能跨过 denominator 和置信区间门槛。最好的 T+5/T+10 bucket 只有 57 到 143 个 OOF denominator，不足以作为稳定规则。

这意味着当前 posterior score 更适合做 ranking/diagnostic，而不是直接做 gate。

### 3. Baseline_3 已经吃掉了大部分可解释收益

大 denominator candidate 接近 baseline_3 时，edge 变成负值或不足。说明 survival-step 本身已经是主要信号来源，后验 bucket 的可解释增量很小。

如果继续沿 probability bucket 方向推进，需要引入更强的特征、更多 episode、或更粗粒度的可稳定分组，而不是继续调 threshold。

### 4. Fresh evidence 有研究价值，但不能在 R03a 中使用

fresh evidence 的 offset 与 conditioning 确实显示出序列结构，特别是 T3_T5、T6_T10、T11_T20 的 `found_within_t3_t30` 行。但这些结果已按 survival state conditioning，不能直接解释为独立因果或独立 gate。

下一步如果研究 fresh evidence，应单独做 sequence/hazard diagnostic，明确：

- fresh evidence 发生在 failure 之前还是之后。
- 它是否在同一 survival checkpoint 条件下仍有增量。
- 它是否只是 survival 的代理变量。

### 5. EV_R 缺失是进入 sizing 的硬 blocker

R03a 只能比较 probability。即使 survival-step 在 probability 上明显更好，也不能推导出 risk budget。原因是：

- 没有 EV_R。
- 没有 action-time denominator。
- context risk bucket 不可用。
- exposure label 不是 validated size。

所以本报告不能给出 1R sizing，也不能声明 production signal。

## 对后续实验的建议

### 建议继续保留 survival-step

R03a 的数据支持继续使用 survival checkpoint，尤其是 T+10。后续实验可以把 baseline_3 作为更强的默认比较对象，而不是继续只和 T0 baseline 比。

### 不建议继续调 R03a probability threshold

当前失败不是 threshold 网格太窄，而是“高 edge 小样本”和“大样本低增量”的结构性矛盾。继续在 validation 上调 threshold 容易变成过拟合。

### R03b 如果目标是 sizing，需要先补 EV_R

如果目标仍是 risk-budget allocation，下一步应先补齐：

- action-time EV_R。
- action-time denominator。
- risk bucket 可用性。
- survival-step 后的实际可执行价格与风险定义。

没有这些输入，任何 1R/0.5R 结论都只能是 label，不是仓位建议。

### 如果目标是信号顺序，应单独开 fresh-sequence / hazard diagnostic

fresh evidence 的描述性结果值得追，但不应该塞进 R03a 的 probability gate。更合理的后续问题是：

- fresh evidence 在 T+3、T+5、T+10 条件下是否仍有增量。
- fresh evidence 是否提前于 observable failure。
- fresh evidence 是否能解释 survival 到 T+10 之后仍然分化的路径。

## Final Decision

Final decision: `blocked_no_stable_candidate_bucket`.

`blocked_no_stable_candidate_bucket`

本实验支持的结论：

- survival-step 是有效的观察结构。
- baseline_3 显著优于 T0 entry/probe-only。
- R03a 输出和约束校验通过。

本实验不支持的结论：

- 不支持冻结 probability posterior bucket。
- 不支持 `r03a_probability_feasibility_passed`。
- 不支持 1R sizing。
- 不支持 EV_R allocation。
- 不支持 production signal。

最直接的下一步是二选一：

1. 如果目标是仓位与 risk budget，先实现 EV_R/action-time denominator 后再做 R03b。
2. 如果目标是解释 survival 过程，单独做 fresh-sequence / hazard diagnostic。

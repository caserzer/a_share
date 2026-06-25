# 14C Cohort Rank Monotonicity Stress Diagnostic Report

## 结论摘要

14C 的裁决为 `14C_stress_cohort_rank_monotonicity_not_supported`，`next_allowed_requirement = none`。本诊断不授权 winner entry、meta-labeling、bet sizing 或生产策略。

核心原因不是输入失败，也不是 primary C3 样本量不足；输入门、primary power gate 和 search-accounting gate 均通过。真正的阻断点在于 validation stress 上的 C3 rank 虽然呈现 bad-side suppression 点估计，但不满足 bootstrap 稳健性，同时 winner 与 50bps utility 没有同向改善。

关键证据如下：

| 项目 | 结果 |
|:--|:--|
| 14A 上游裁决 | `14A_diagnostic_cohort_signal_only_no_utility` |
| 14A 选择 arm | `F4_board_relative_strength_rank_jump__ret60_jump3 / C3 / top20pct / 50bps` |
| 14C 输入门 | pass |
| 14C primary C3 power gate | pass |
| 14C stress bad-side gate | fail |
| 14C stress utility gate | fail |
| 14C stress winner gate | fail |
| C1-C6 一致性读数 | `badside_only_broad_support` |
| search-accounting gate | pass |

## 14A 失败背景

14A 已经把 F4/C3/top20pct 推到 cohort-normalized operating arm，但它没有获得可交易授权。14A 的 decision table 显示：

| 字段 | 值 |
|:--|:--|
| decision_state | `14A_diagnostic_cohort_signal_only_no_utility` |
| next_allowed_requirement | `none` |
| selected_raw_event_arm_id | `F4_board_relative_strength_rank_jump__ret60_jump3` |
| selected_cohort_arm_id | `C3` |
| selected_rank_cutoff_id | `top20pct` |
| primary_cost_tier_bps | 50 |
| primary_failure_reason | `cohort_signal_no_same_event_utility` |
| gate_failure | `same_event_utility_50bps_failed` |
| cohort_transport_gate_status | fail |
| same_event_utility_50bps_gate_status | fail |
| morphology_rediscovery_gate_status | fail |
| validation_stress_gate_status | fail |

14A 的 validation stress audit 也已经暴露了问题：C3 top20pct 在 stress split 的 utility 为 -0.003724，winner opportunity retained 只有 0.039474，bad-side exposure 为 0.223684；C3 top10pct utility 仍为 -0.001978，winner retained 0.032609，bad-side exposure 0.228261。换句话说，14A 不是“没有任何结构”，而是结构不能转化为 validation stress 下的正 utility。

14C 因此只做一个更窄的问题：C3 cohort rank 在 stress 下是否至少保留单调的 bad-side suppression，足以把后续路线降级到 defense / participation overlay。14C 不重新挑 entry arm，不修复 F2/F5/F6，也不把 raw-intensity 读数提升为新信号。

## 输入与审计完整性

14C 对 14A publishable lineage 和 local cache 做了直接文件校验，而不是只信 14A manifest。三个 row-level cache 均直接读取、计算 sha256、检查 schema 并通过：

| artifact_role | row_count | column_count | schema_status | local_cache_lineage_status |
|:--|--:|--:|:--|:--|
| pit_cohort_normalized_event_panel | 25776 | 42 | pass | pass |
| sparse_event_panel | 66881 | 35 | pass | pass |
| state_change_feature_panel | 408715 | 122 | pass | pass |

rank-cutoff canonicalization 也通过。14A 原始 cohort panel 有 25776 行，按 `(raw_event_arm_id, event_id, cohort_arm_id)` 去掉 top10pct/top20pct 双计后得到 12888 个 canonical event；15 个 invariant 字段全部 `duplicate_consistency_status = pass`，没有 mismatch group。

feature enrichment 使用 `(row_id, instrument, reference_date)` join，canonical rows 12888/12888 全部匹配，缺失率 0；`board_bucket`、`calendar_year`、`reference_date`、`split_bucket` 的 overlap conflict 均为 0。volatility/liquidity decile 采用 `shifted_0_9_to_1_10` adapter，说明上游 decile 编码按 0-9 存储，14C 已统一到 1-10 后再分 bucket。

## Primary C3 Rank-IC

Primary 分析固定继承 14A 的 selected arm：`F4_board_relative_strength_rank_jump__ret60_jump3 / C3 / top20pct / 50bps`。rank-IC 使用 continuous `cohort_percentile_rank`，不使用 `selected_event_flag` 或 `skipped_event_flag`。

| split | denominator | finite_rank_n | coverage | rank_ic_winner | rank_ic_fast_fail | rank_ic_utility_50bps | rank_ic_status |
|:--|--:|--:|--:|--:|--:|--:|:--|
| train | 1061 | 1004 | 0.946277 | -0.008450 | -0.012803 | -0.006232 | pass |
| validation | 553 | 553 | 1.000000 | -0.112225 | -0.040867 | -0.015397 | pass |
| robustness | 534 | 534 | 1.000000 | 0.205799 | -0.073176 | 0.119305 | pass |

读法：

- `rank_ic_fast_fail < 0` 是好方向，表示 rank 越高，fast_fail 越低。C3 在 train、validation、robustness 三段都是负值，bad-side suppression 方向稳定。
- `rank_ic_winner > 0` 和 `rank_ic_utility_50bps > 0` 才是 entry 方向。validation 上两者分别为 -0.112225 与 -0.015397，方向错误。
- robustness 上 winner/utility 都转正，但 14C 的授权门槛必须以 validation stress 为主，不能用 robustness 替代 validation。

因此，C3 在 validation 的主要含义是“高 rank 可能减少坏边”，不是“高 rank 能提高胜率或收益”。

## Bootstrap 不确定性

14C 使用 `instrument_year` cluster bootstrap，seed = 1403001，bootstrap_n = 500。bad-side defense authorization 要求 validation 的 `rank_ic_fast_fail_ci_high < 0`，不能只看点估计。

| split | bootstrap_status | fast_fail CI low | fast_fail CI high | utility CI low | utility CI high | top-bottom fast_fail delta CI high | top-bottom utility delta CI high |
|:--|:--|--:|--:|--:|--:|--:|--:|
| train | pass | -0.063673 | 0.035645 | -0.061228 | 0.051731 | 0.052206 | 0.034746 |
| validation | pass | -0.115536 | 0.023598 | -0.080995 | 0.062112 | 0.040122 | 0.022191 |
| robustness | pass | -0.150463 | -0.003472 | 0.042601 | 0.195118 | 0.022572 | 0.072362 |

validation 的 `rank_ic_fast_fail = -0.040867` 看起来支持 bad-side suppression，但 bootstrap CI 上界为 0.023598，跨过 0。这个结果不能支撑 defense overlay confirmatory requirement。robustness 的 fast_fail CI 不跨 0，但它不能覆盖 validation 的不确定性。

## Bucket Monotonicity

Primary C3 的 quintile bucket 显示了同样结构：validation 的 Q5 比 Q1 有更低 fast_fail，但 winner 和 utility 没有改善。

| split | bucket | event_n | winner_rate | fast_fail_rate | utility_mean_50bps | Q5-Q1 winner delta | Q5-Q1 fast_fail delta | Q5-Q1 utility delta |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|
| train | Q1 | 220 | 0.172727 | 0.272727 | 0.010892 | 0.004040 | -0.015152 | 0.008178 |
| train | Q5 | 198 | 0.176768 | 0.257576 | 0.019070 | 0.004040 | -0.015152 | 0.008178 |
| validation | Q1 | 68 | 0.161765 | 0.294118 | -0.009050 | -0.122291 | -0.070433 | -0.004498 |
| validation | Q5 | 152 | 0.039474 | 0.223684 | -0.013548 | -0.122291 | -0.070433 | -0.004498 |
| robustness | Q1 | 121 | 0.140496 | 0.206612 | 0.003456 | 0.210855 | -0.053458 | 0.039916 |
| robustness | Q5 | 111 | 0.351351 | 0.153153 | 0.043372 | 0.210855 | -0.053458 | 0.039916 |

validation 的 Q5-Q1 fast_fail delta = -0.070433，是这次诊断中最清楚的正向证据。但 Q5-Q1 winner delta = -0.122291，utility delta = -0.004498，说明“少输”没有转化成“更容易赢”或“更高 after-cost utility”。这就是 14C 没有授权 defense overlay 的核心：bad-side 点估计存在，但不够稳健；entry 证据更是反向。

## Finite Rank Coverage

coverage 本身不是阻断项。validation 与 robustness 都是 100% finite rank；train 覆盖率为 0.946277，超过 power gate，但 57 个 drop 全部集中在 2018 年早期历史。

| split | calendar_year | denominator | finite_rank_n | dropped_total_n | insufficient_cohort_drop_n | drop_rate | status |
|:--|--:|--:|--:|--:|--:|--:|:--|
| train | 2018 | 130 | 73 | 57 | 57 | 0.438462 | train_early_history_concentration |
| train | 2019 | 354 | 354 | 0 | 0 | 0.000000 | pass |
| train | 2020 | 247 | 247 | 0 | 0 | 0.000000 | pass |
| train | 2021 | 330 | 330 | 0 | 0 | 0.000000 | pass |
| validation | 2022 | 267 | 267 | 0 | 0 | 0.000000 | no_drops |
| validation | 2023 | 286 | 286 | 0 | 0 | 0.000000 | no_drops |
| robustness | 2024 | 262 | 262 | 0 | 0 | 0.000000 | no_drops |
| robustness | 2025 | 272 | 272 | 0 | 0 | 0.000000 | no_drops |

这意味着 C3 的 validation/robustness 结论不受 finite-rank 缺失影响；但 train 的早期样本确实有 selection bias，train rank-IC 不应被解释为全历史无偏估计。

## C1-C6 Cohort Dimension 一致性

14C 还检查 C1-C6 是否说明 C3 只是局部偶然。validation 上的读数如下：

| cohort | event_n | finite_rank_n | rank_ic_winner | rank_ic_fast_fail | rank_ic_utility_50bps | winner sign | fast_fail sign | utility sign |
|:--|--:|--:|--:|--:|--:|:--|:--|:--|
| C1 | 553 | 553 | -0.017565 | 0.009962 | -0.072061 | fail | fail | fail |
| C2 | 553 | 553 | -0.024511 | 0.010382 | -0.069718 | fail | fail | fail |
| C3 | 553 | 553 | -0.112225 | -0.040867 | -0.015397 | fail | pass | fail |
| C4 | 553 | 553 | -0.037629 | -0.014497 | -0.017363 | fail | pass | fail |
| C5 | 553 | 354 | 0.051025 | -0.024326 | -0.003569 | pass | pass | fail |
| C6 | 553 | 359 | 0.040194 | -0.025840 | 0.016446 | pass | pass | pass |

横向观察：

- C1/C2 明显不支持：fast_fail rank-IC 为正，utility 为负。
- C3/C4 支持 bad-side suppression，但 winner/utility 不支持。
- C5/C6 在 winner 和 bad-side 上更好，C6 甚至 utility 为正，但 C5/C6 finite rank 只有 354/359，且它们不是 14A 冻结的 primary arm，14C 只能把它们记为 diagnostic readout，不能事后替换 C3。

因此 `cohort_dimension_consistency_status = badside_only_broad_support` 是合理的：bad-side 方向在 C3-C6 有一定横向扩散，但 utility/winner 不是广泛成立，且 primary C3 的 validation bootstrap 不过关。

validation bucket 层面也显示 C5/C6 比 C3 更像 defense filter，但仍不能在 14C 中升级：

| cohort | Q1 event_n | Q5 event_n | Q5-Q1 fast_fail delta | Q5-Q1 utility delta | status |
|:--|--:|--:|--:|--:|:--|
| C3 | 68 | 152 | -0.070433 | -0.004498 | fail_expected_signs |
| C4 | 78 | 143 | -0.020979 | -0.002063 | fail_expected_signs |
| C5 | 80 | 64 | -0.068750 | 0.007896 | pass_expected_signs |
| C6 | 81 | 73 | -0.067478 | 0.004375 | pass_expected_signs |

这个发现可以作为后续人工讨论线索：C5/C6 可能比 C3 更接近 defense overlay 的归一化口径。但按 14C 搜索约束，它不能触发 `next_allowed_requirement`。

## Stress Failure Mode

stress 维度揭示：C3 rank 的问题不是全局失效，而是分区间不稳定。

| stress_dimension | stress_bucket | event_n | rank_ic_fast_fail | rank_ic_utility_50bps | Q5-Q1 fast_fail delta | Q5-Q1 utility delta | failure_mode |
|:--|:--|--:|--:|--:|--:|--:|:--|
| market_regime_bucket | risk_on | 553 | -0.040867 | -0.015397 | -0.070433 | -0.004498 | badside_monotonic_utility_not_monotonic |
| board_bucket | chinext | 109 | -0.015909 | 0.036127 | -0.071429 | -0.019237 | both_monotonic |
| board_bucket | main_board | 444 | -0.051021 | -0.020187 | -0.068100 | -0.001358 | badside_monotonic_utility_not_monotonic |
| volatility_bucket | high | 315 | -0.096859 | 0.050646 | -0.110823 | 0.008009 | both_monotonic |
| volatility_bucket | low | 101 | 0.061445 | -0.114917 | -0.047059 | -0.009785 | neither_monotonic |
| volatility_bucket | mid | 137 | 0.045063 | -0.011068 | 0.116667 | -0.015249 | neither_monotonic |
| liquidity_bucket | high | 223 | -0.155620 | 0.016235 | -0.245238 | 0.008726 | both_monotonic |
| liquidity_bucket | low | 158 | -0.047805 | -0.020546 | -0.127451 | -0.024863 | badside_monotonic_utility_not_monotonic |
| liquidity_bucket | mid | 172 | 0.118622 | -0.015313 | 0.182065 | 0.008062 | neither_monotonic |
| calendar_year | 2022 | 267 | -0.040552 | -0.047156 | -0.094253 | 0.003142 | badside_monotonic_utility_not_monotonic |
| calendar_year | 2023 | 286 | -0.011375 | -0.001358 | -0.023482 | -0.009576 | badside_monotonic_utility_not_monotonic |

failure mode 计数：

| failure_mode | bucket_n |
|:--|--:|
| badside_monotonic_utility_not_monotonic | 5 |
| both_monotonic | 3 |
| neither_monotonic | 3 |

insight：

- high volatility 与 high liquidity 是 C3 最像有效 defense signal 的区域：fast_fail rank-IC 分别为 -0.096859 和 -0.155620，utility rank-IC 也为正。
- low/mid volatility 与 mid liquidity 明显破坏单调性，尤其 mid liquidity 的 fast_fail rank-IC = 0.118622、Q5-Q1 fast_fail delta = 0.182065，是反向风险。
- 年份层面 2022/2023 都是 badside-only：坏边下降有迹象，但 utility 不同步。说明 14A 的 stress utility failure 不是单一年份噪声。

这支持一个更细的解释：C3 rank 不是完全无信息，而是“regime-conditional bad-side filter”。但 14C 当前没有授权做 regime-conditioned selector；在现有 requirement 下，分区间发现只能作为诊断，不是新策略。

## All-Family Raw Intensity Readout

all-family raw-intensity 是 secondary evidence，只能读 raw `event_intensity_score` 的单调性，不能为 density-excluded family 发明 C1-C6 cohort rank，也不能触发 `next_allowed_requirement`。

validation 上 bad-side 方向最强的 raw-intensity readout：

| raw_event_arm_id | event_n | rank_ic_winner | rank_ic_fast_fail | rank_ic_utility_50bps | Q5-Q1 fast_fail delta | Q5-Q1 utility delta |
|:--|--:|--:|--:|--:|--:|--:|
| F4_board_relative_strength_rank_jump__ret60_jump2 | 715 | -0.056538 | -0.166498 | 0.042836 | -0.216783 | 0.021873 |
| F3_controlled_damage_first_reclaim__damage60 | 770 | 0.011767 | -0.134507 | -0.080330 | -0.188312 | 0.002883 |
| F4_board_relative_strength_rank_jump__ret20_jump2 | 791 | -0.068501 | -0.113659 | -0.036938 | -0.101266 | -0.006864 |
| F2_compression_to_directional_expansion__ratio1p5 | 546 | 0.064076 | -0.111804 | 0.062729 | -0.165138 | 0.016315 |
| F6_low_volatility_range_expansion_first_trigger__ratio1p5 | 535 | 0.056392 | -0.097696 | 0.052337 | -0.149533 | 0.014865 |
| F5_participation_ignition_with_price_control__window60_ratio2p0 | 1061 | 0.010632 | -0.078206 | -0.014221 | -0.099057 | -0.003515 |
| F4_board_relative_strength_rank_jump__ret20_jump3 | 688 | -0.056765 | -0.075112 | -0.010600 | -0.130435 | 0.009116 |
| F5_participation_ignition_with_price_control__window20_ratio1p5 | 1584 | 0.038161 | -0.066812 | 0.034434 | -0.091483 | 0.010432 |

其中 F4 ret60_jump2、F2 ratio1p5、F6 ratio1p5、F5 window20_ratio1p5 同时满足 raw fast_fail 下降与 raw utility 为正，看起来比 primary C3 更有吸引力。但这些是 raw-intensity 诊断，不是 cohort-normalized transport 后的 confirmatory evidence。尤其 F2/F5/F6 在 14A 中受到 density / duplicate / morphology 边界约束，14C 不能把它们恢复成 entry thesis。

正确用法是：这些读数可以解释“为什么 14A 里有些 family 不是彻底无信号”，但不能绕过 14A/14C 的稀疏化、transport 和 search-accounting 约束。

## Findings

1. C3 的唯一稳定信息是 bad-side suppression，而不是 winner entry。train、validation、robustness 的 `rank_ic_fast_fail` 均为负；但 validation 的 winner 与 utility 均为负，bucket 结果也显示 Q5 比 Q1 的 winner rate 更低。

2. bad-side signal 没有达到 defense overlay 的稳健授权标准。validation fast_fail rank-IC 点估计为 -0.040867，但 bootstrap CI high = 0.023598，跨过 0；这阻断了 `requirement_14d_defense_overlay_confirmatory.md`。

3. C1-C6 横向读数支持“badside-only broad support”，但不是 utility/winner broad support。C3-C6 多数 cohort arm 的 fast_fail 方向较好，C5/C6 在 validation 上更像可用 filter；但 C5/C6 不是 frozen primary arm，且 finite rank 更少，不能事后替换。

4. stress failure 不是均匀的。high volatility / high liquidity 区间更接近有效 defense signal；low/mid volatility 与 mid liquidity 会破坏甚至反转 fast_fail 单调性。这说明单一 cohort rank 在 stress 下不具备全局稳定排序能力。

5. raw-intensity 读数提示 F2/F5/F6 可能存在未被当前 sparse-event 稀疏化机制保留下来的机会，但这是另一个问题。14C 没有授权 raw-event-only 14B，也没有授权 event uniqueness redesign 作为正式 next requirement。

## Insight 与后续研究含义

14C 对当前 thesis 的判定是关闭而不是推进：在 frozen 14A primary arm 上，cohort rank 不能证明 validation stress 下的可迁移单调性。它最多说明“某些 rank 维度可以减少坏边”，但该证据没有强到可以进入 defense overlay confirmatory。

若后续继续研究，应避免把 C3 top bucket 当作 entry signal。更合理的研究假设有两个，但都需要新 requirement 重新定义边界：

- defense 方向：只研究 bad-side filter，并且必须显式加入 bootstrap/cluster 稳健性、regime 分层、full-denominator portfolio utility。14C 当前没有给出自动授权，因为 validation CI 跨 0。
- uniqueness 方向：若要救 F2/F5/F6，应先研究 event de-duplication / uniqueness / dynamic cooldown，而不是直接用 raw-intensity 做 entry。14C 的 all-family 读数只说明“值得解释”，不说明“可交易”。

本报告的正式结论仍然是：`next_allowed_requirement = none`。14C 不授权 winner-entry、meta-labeling、bet sizing 或生产策略；所有 raw-intensity 与 C1-C6 secondary readout 均为诊断证据，不得被解释成 deployable alpha。

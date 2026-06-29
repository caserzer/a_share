# 16E-postmortem Continuation Utility Failure Decomposition Report

## 1. 裁决摘要

`decision_state = 16E_postmortem_mainline_closed_no_path_supported`；`next_allowed_requirement = none`；`selected_path_id = none`；`continuation_as_action_mainline_closed = true`。

本 postmortem 不计算新 return、不计算新 cost、不计算新 drawdown、不 refit model、不改 threshold、不新增 action semantics；它只读取 16E 的 `utility_panel.parquet` 与 publishable readouts 做分组、分位、比率、Spearman 与 boolean gate。它也不授权 entry、exit、holding、chained simulation、portfolio backtest、deployment、production signal 或 live trading。

核心结论：

1. 16E 的 not_supported 被复验为有效：primary 50bps return utility gate fail，drawdown avoidance gate pass，delay stress gate fail，context utility gate fail。
2. 失败不是因为六格算术或 lineage 错：22 个输入 artifact 读取/模式检查通过；1,812 条 panel replay 全部通过；`continued_*` 三格 incremental sum 为 0；no-new-computation gate pass。
3. 厚尾错配确实存在：defended_positive 的 upside 明显高于 all_positive，robustness mean ratio = 1.3127，q75 ratio = 1.3966。
4. 但 directionality gate 失败：train Spearman = 0.9030，robustness Spearman = 0.0303；robustness 被判定为 non-monotone，而不是 weak-but-usable。
5. 因 directionality gate 是 A/B/C 的前置门，路径 A、B、C 全部不授权；`none` 被选中。

## 2. 16E Not-supported 复验

16E-postmortem 不是重读报告文字，而是复验 16E decision、manifest、hard gates、authorization booleans 与 16D threshold lineage。

| item | value |
| --- | --- |
| upstream_16e_decision_state | 16E_utility_diagnostic_not_supported |
| upstream_16e_next_allowed_requirement | none |
| upstream_16e_utility_interpretation | drawdown_reduction_only_return_not_supported |
| primary_policy_id | defense_bottom_30pct_continuation_score_v1 |
| primary_action_semantics_id | full_avoidance_cash_h20_close_to_close_v1 |
| primary_round_trip_defense_cost_bps | 50 |
| threshold_value | 0.457071 |
| primary_return_utility_gate | fail |
| drawdown_avoidance_gate | pass |
| delay_stress_gate | fail |
| context_power_gate | pass |
| context_utility_gate | fail |
| six_cell_reconciliation_gate | pass |
| search_accounting_gate | pass |
| upstream_16e_authorization_gate | pass |

16E primary 50bps full-denominator utility 仍为负：

| split | labelable_step_n | defended_step_n | sum_incremental | mean_incremental | mean_drawdown_avoided | defended_positive_sum | defended_negative_sum | return_gate | drawdown_gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| train | 20,245 | 5,584 | -46.892550 | -0.002316 | 0.025833 | -331.207522 | 242.167136 | fail | pass |
| robustness | 2,496 | 486 | -13.800725 | -0.005529 | 0.017731 | -32.499665 | 15.693211 | fail | pass |
| validation | 664 | 183 | -3.858970 | -0.005812 | 0.025309 | -13.214871 | 8.321611 | fail | pass |

解释：drawdown avoidance 是真实的，但它不能抵消 defended_positive 的 upside sacrifice。robustness 下每个 labelable step 平均损失 -55.29 bps，而 defended_negative 的 drawdown avoided mean 仍有 16.40%。这就是 16E 的核心矛盾：risk 信息存在，return utility 不成立。

## 3. Lineage 与 No-new-computation 审计

| audit | result |
| --- | --- |
| input_artifact_audit row_n | 22 |
| panel_aggregate_replay row_n | 1,812 |
| panel replay fail_n | 0 |
| max split incremental replay abs_diff | 2.84e-14 |
| max six-cell replay abs_diff | 2.84e-14 |
| no_new_forward_return_computed | true |
| no_new_cost_computed | true |
| no_new_drawdown_computed | true |
| no_model_refit | true |
| no_threshold_change | true |
| no_action_semantics_added | true |
| no_new_computation_gate | pass |

列血缘固定如下：

| derived metric | source columns | transform | status |
| --- | --- | --- | --- |
| split_bucket_normalization | `cluster_split_bucket` | column_rename | pass |
| score_passthrough | `score,model_id,policy_id,threshold_value` | pass_through | pass |
| split_incremental_replay | `incremental_net_return_h20`, `full_denominator_sum_incremental_return` | groupby_sum | pass |
| six_cell_bidirectional_replay | `cell_id`, `incremental_net_return_h20`, `continue_return_h20`, `policy_net_return_h20`, `drawdown_avoided_abs` | groupby_sum | pass |
| score_bucket_monotonicity | `score`, `continue_return_h20`, `continue_max_drawdown_h20`, `label_class` | quantile_bucket_spearman | pass |

这里最关键的审计点是：postmortem 显式把 panel 的 `cluster_split_bucket` 规范化为 report/readout 口径的 `split_bucket`，并显式对账 `sum(panel.incremental_net_return_h20) over (split_bucket,cost_bps) == utility_by_split_readout.full_denominator_sum_incremental_return`。这避免了把 schema mismatch 隐藏成实现里的硬编码映射。

## 4. PM-Q1: 失败的六格算术归因

Primary 50bps 下，net utility 的构成如下：

| split | net_utility_total | defended_positive_oppcost | defended_negative_gain | defended_neutral_gain | oppcost / negative_gain | oppcost / (negative+neutral gain) | continued_negative_residual_loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | -46.892550 | 331.207522 | 242.167136 | 42.147836 | 1.3677 | 1.1649 | 279.257036 |
| robustness | -13.800725 | 32.499665 | 15.693211 | 3.005729 | 2.0709 | 1.7380 | 33.661775 |
| validation | -3.858970 | 13.214871 | 8.321611 | 1.034291 | 1.5880 | 1.4125 | 11.137834 |

Identity checks:

| split | attribution_identity_status | continued_incremental_zero_status | six_cell_bidirectional_replay_status |
| --- | --- | --- | --- |
| train | pass | pass | pass |
| robustness | pass | pass | pass |
| validation | pass | pass | pass |

发现：

1. 训练集看起来只差一口气，但不是无害失败：positive opportunity cost = 331.21，已经超过 defended_negative + defended_neutral 的合计收益 284.31，比例 1.1649。
2. robustness 的失败更硬：positive opportunity cost = 32.50，是 defended_negative gain 15.69 的 2.07 倍，是 negative+neutral 合计收益 18.70 的 1.74 倍。
3. continued_negative_residual_loss 不是 incremental identity 的一部分，因为 continue 行 incremental 按 16E 语义为 0；但它衡量未防住的 negative loss mass。robustness residual loss = 33.66，是 net loss 绝对值 13.80 的 2.44 倍，说明 bottom-30% defend 没有覆盖足够多的 negative tail。

洞察：16E 的 full avoidance action 同时犯两个错，一边错防高 upside positive，一边漏掉大量 continued negative。它不是单纯“防得太多”或“防得太少”，而是 score-to-action 映射在 robustness 上不能稳定排序 utility。

## 5. PM-Q2: 厚尾错配存在，但不能单独授权路径 A

defended_positive 的 upside 分布显著高于 all_positive：

| split | population | row_n | upside_mean | upside_q50 | upside_q75 | upside_q90 | mean_ratio | q75_ratio | q90 >= all_q75 | thick_tail_mismatch |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| train | all_positive | 10,078 | 0.113537 | 0.075857 | 0.147046 | 0.249434 |  |  |  |  |
| train | defended_positive | 2,190 | 0.146236 | 0.101312 | 0.178874 | 0.333454 | 1.2880 | 1.2164 | true | true |
| robustness | all_positive | 1,346 | 0.119363 | 0.083928 | 0.157513 | 0.272587 |  |  |  |  |
| robustness | defended_positive | 201 | 0.156690 | 0.122034 | 0.219986 | 0.345558 | 1.3127 | 1.3966 | true | true |
| validation | all_positive | 325 | 0.135438 | 0.089643 | 0.178999 | 0.296551 |  |  |  |  |
| validation | defended_positive | 77 | 0.166622 | 0.097432 | 0.240761 | 0.336443 | 1.2302 | 1.3450 | true | true |

发现：

1. 厚尾错配在 train、robustness、validation 三个 split 都成立。robustness 下 defended_positive q75 = 21.999%，而 all_positive q75 = 15.751%；defended_positive q90 = 34.556%，也高于 all_positive q75。
2. 这支持“0/1 continuation label 对高 upside positive 惩罚不足”的机制解释：模型把一些上涨厚尾 positive 排到低 score，被 bottom-30% policy 防掉。
3. 但 requirement 把 directionality_gate 放在路径 A/B/C 前面。厚尾错配只能说明“存在一种损失机制”，不能证明 score 在 robustness 上有可用于重设 objective 的稳定方向性。

结论：PM-Q2 支持 classify-then-bolt-on mismatch 的局部机制，但不足以推翻主裁决。路径 A 仍不授权，因为 robustness directionality 和 candidate-region efficiency 都不通过。

## 6. PM-Q3: Score bucket 单调性是主阻塞

十分位按 `score` 从低到高排列。train 与 robustness 的形态完全不同：

| split | Spearman | monotone_increasing | non_monotone | inverted | robustness_unstable_caveat |
| --- | ---: | --- | --- | --- | --- |
| train | 0.903030 | true | false | false | false |
| robustness | 0.030303 | false | true | false | false |
| validation | 0.054545 | false | true | false | false |

关键 decile 截面：

| split | decile | row_n | positive_n | negative_n | neutral_n | base_rate_positive | mean_continue_return_h20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 1 | 2,025 | 662 | 1,078 | 285 | 0.380460 | -0.009554 |
| train | 3 | 2,025 | 893 | 636 | 496 | 0.584042 | 0.013489 |
| train | 10 | 2,025 | 1,231 | 181 | 613 | 0.871813 | 0.033712 |
| robustness | 1 | 250 | 92 | 124 | 34 | 0.425926 | 0.015835 |
| robustness | 3 | 249 | 138 | 59 | 52 | 0.700508 | 0.051686 |
| robustness | 5 | 249 | 139 | 47 | 63 | 0.747312 | 0.056383 |
| robustness | 10 | 250 | 155 | 23 | 72 | 0.870787 | 0.032262 |

完整 robustness decile 的 mean continue return 形态：

| decile | row_n | base_rate_positive | mean_continue_return_h20 |
| ---: | ---: | ---: | ---: |
| 1 | 250 | 0.425926 | 0.015835 |
| 2 | 250 | 0.593750 | 0.028537 |
| 3 | 249 | 0.700508 | 0.051686 |
| 4 | 250 | 0.704301 | 0.045478 |
| 5 | 249 | 0.747312 | 0.056383 |
| 6 | 250 | 0.758427 | 0.029904 |
| 7 | 249 | 0.815029 | 0.032479 |
| 8 | 250 | 0.815217 | 0.029869 |
| 9 | 249 | 0.829670 | 0.026453 |
| 10 | 250 | 0.870787 | 0.032262 |

发现：

1. train 是可解释的：D1 mean return = -0.955%，D10 = 3.371%，Spearman = 0.9030。训练集里 score 高低确实对应 continuation return 的方向。
2. robustness 不是“略弱单调”，而是非单调：D5 mean return = 5.638%，高于 D10 的 3.226%；D6 到 D10 没有继续改善，Spearman 只有 0.0303。
3. robustness 的 base_rate_positive 仍然从 D1 的 42.59% 升到 D10 的 87.08%。这很重要：score 仍有二元分类信息，但二元 positive rate 的排序没有稳定转化为 realized return / utility 排序。
4. `robustness_monotonicity_unstable_caveat = false`，因为 Spearman 没有落在 [0.3, 0.6) 的“方向性可能不足功效”区间，而是接近 0。报告应把它解释为明确非单调，而不是功效不足的轻微 caveat。

洞察：16D score 在 train 上学到了“survival/positive probability”，但 robustness 上 high score 并不等于 higher h20 payoff。AFML 决策上，这种信号不能作为 continuation action 的直接控制变量；最多说明原分类目标与 payoff objective 之间存在断裂。

## 7. PM-Q4: Candidate defend region 的 efficiency 不稳

候选 defend region 固定为低 score 的 D1-D3。要求是 train 和 robustness 都至少有一个非低功效 candidate decile 的 `loss_avoidance_efficiency > 1.0`。

| split | decile | defended_negative_n | defended_positive_n | avoided_loss_abs | sacrificed_upside_abs | efficiency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 1 | 1,078 | 662 | 136.153414 | 114.468946 | 1.189435 |
| train | 2 | 712 | 865 | 82.897805 | 118.228304 | 0.701167 |
| train | 3 | 509 | 663 | 58.270634 | 87.560273 | 0.665492 |
| robustness | 1 | 124 | 92 | 13.007399 | 14.845474 | 0.876186 |
| robustness | 2 | 72 | 109 | 7.505972 | 16.649191 | 0.450831 |
| robustness | 3 | 0 | 0 | 0.000000 | 0.000000 | NaN |
| validation | 1 | 34 | 23 | 4.210230 | 5.342828 | 0.788015 |
| validation | 2 | 25 | 35 | 2.255146 | 5.010963 | 0.450042 |
| validation | 3 | 22 | 19 | 2.900252 | 2.476080 | 1.171308 |

发现：

1. train D1 有局部可行性，efficiency = 1.1894，但 D2 和 D3 已经跌到 0.7012 / 0.6655。
2. robustness 没有任何 candidate decile efficiency > 1.0。D1 = 0.8762，D2 = 0.4508，D3 没有 defended rows。
3. validation D3 = 1.1713 只是 stress readout，不能用于 path selection；并且 validation 样本只有 664 labelable rows，不足以推翻 robustness gate。

洞察：更窄的 threshold 在 train 上可能看似能改善，但 robustness 不确认。路径 A 要求“方向性 + 厚尾错配 + candidate efficiency 可改善”同时成立；这里只有厚尾错配成立，另外两个关键条件失败。

## 8. PM-Q5: Drawdown 残值不足以授权 risk-budget overlay

PM-Q5 只读 16E 既有 `drawdown_avoided_abs` 与 `continue_return_h20`，没有计算 partial-exposure utility。

| split | defended_negative_n | defended_negative_drawdown_median | defended_negative_drawdown_mean | defended_positive_return_median | defended_positive_return_mean | drawdown_to_upside_median_ratio | partial_exposure_feasibility_hint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | 2,299 | 0.152148 | 0.166858 | 0.101312 | 0.146236 | 1.501775 | false |
| robustness | 196 | 0.151841 | 0.164024 | 0.122034 | 0.156690 | 1.244249 | false |
| validation | 81 | 0.144999 | 0.158338 | 0.097432 | 0.166622 | 1.488202 | false |

发现：

1. defended_negative drawdown median 很深：train 15.21%，robustness 15.18%。这解释了为什么 16E 的 drawdown avoidance gate 能通过。
2. 但 defended_positive return median 也不低：train 10.13%，robustness 12.20%，均高于预注册的 8% 上限。
3. robustness 的 drawdown/upside median ratio = 1.2442，低于 1.50 cutoff。

结论：drawdown 信息真实，但不足以在本 postmortem 中给 path B 一个 feasibility hint。risk-budget overlay 如果未来要做，必须从新的 requirement 重新定义 utility 和 exposure，不应由本报告偷渡授权。

## 9. Context 与 delay 读数

16E 原始 context readout 显示，非 known-failed context 也不能救回 utility：

| split | context | labelable_step_n | defended_step_n | sum_incremental | mean_incremental | return_gate | drawdown_gate | context_status |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| train | non_known_failed_context | 4,791 | 1,286 | -31.779915 | -0.006633 | fail | pass | fail |
| robustness | non_known_failed_context | 1,195 | 206 | -6.713821 | -0.005618 | fail | pass | fail |
| validation | non_known_failed_context | 65 | 16 | -1.976284 | -0.030404 | fail | pass | stress_readout |

Delay stress 也没有改变裁决方向：

| split | primary_close_to_close_mean_incremental | delay_stress_mean_incremental |
| --- | ---: | ---: |
| train | -0.002316 | -0.002544 |
| robustness | -0.005529 | -0.005086 |
| validation | -0.005812 | -0.006278 |

解释：即使不把 known-failed context 当成唯一失败来源，non-known-failed context 的 primary utility 仍为负。delay stress 也不是主因，因为 primary 本身已经为负。

## 10. Path Support

| path | requirement | path_supported | reason |
| --- | --- | --- | --- |
| A | requirement_16d_prime_utility_weighted_continuation_objective.md | false | 厚尾错配成立，但 directionality gate fail，且 robustness candidate efficiency 不支持 |
| B | requirement_16e_overlay_risk_budget_continuation_readout.md | false | drawdown gate pass，但 directionality gate fail，partial_exposure_feasibility_hint = false |
| C | requirement_16d_meta_continuation_participation_filter.md | false | C 也要求 directionality gate pass；当前 robustness non-monotone |
| none | none | true | directionality failed or no preregistered path supported |

Search accounting：

| item | value |
| --- | --- |
| primary_policy_id | defense_bottom_30pct_continuation_score_v1 |
| threshold_value | 0.457071 |
| no_model_refit | true |
| no_threshold_change | true |
| no_new_action_semantics | true |
| path_priority_A_gt_B_gt_C_preregistered | true |
| validation_used_for_path_selection | false |
| robustness_used_as_confirmatory_path_gate | true |
| robustness_used_for_threshold_tuning | false |
| search_accounting_gate | pass |

## 11. Findings And Insight

### Finding 1: 16E 失败的直接算术原因是 upside sacrifice 超过 avoided loss

Robustness 下 defended_positive opportunity cost = 32.50，而 defended_negative gain = 15.69，defended_neutral gain = 3.01。即使把 negative 与 neutral 的正向 incremental 合并，合计 18.70 仍显著低于 32.50。这个结构解释了为什么 drawdown avoided 很漂亮但 full-denominator return utility 仍失败。

### Finding 2: 厚尾错配是真实机制，但不是可授权路径

Robustness defended_positive mean upside = 15.67%，高于 all_positive 的 11.94%；defended_positive q75 = 22.00%，高于 all_positive q75 = 15.75%。这说明 bottom-30% score 确实错防了不少高 upside positive。问题在于：这个机制只解释了损失来源，不能证明 score 在 robustness 上能稳定排序 payoff。

### Finding 3: 分类能力没有稳定转化成 utility 方向性

Robustness base positive rate 从 D1 的 42.59% 升到 D10 的 87.08%，说明 16D score 不是无信息。但 mean continue return 不随 score 单调上升：D5 = 5.64%，D10 = 3.23%，Spearman = 0.0303。AFML 上这意味着分类 label 的 survival/positive 概率与 payoff magnitude 分离，直接把分类 score 接到 action 上会产生 unstable utility。

### Finding 4: 训练集局部可修复迹象不能通过 robustness confirmatory split

Train D1 efficiency = 1.1894，似乎支持更窄 defend region；但 robustness D1 = 0.8762，D2 = 0.4508，D3 没有 defended rows。这个模式不支持“把 threshold 缩窄即可修复”的结论。若在此处授权路径 A，会把训练集局部形态误当成可迁移的 utility rule。

### Finding 5: Drawdown 信息应降级为诊断，不应升级为 overlay 授权

Defended_negative 的 drawdown median 在 train/robustness 都约 15%，说明风险侧信息不是噪声。但 defended_positive 的 median return 也很高，robustness 为 12.20%，且 drawdown/upside median ratio 只有 1.2442。当前证据不支持 path B；任何 partial exposure 或 risk budget overlay 都需要新 requirement 重新定义 utility，不能由本 postmortem 推导。

## 12. AFML 决策含义

本轮最重要的结论是：`continuation_survival_h20_no_deep_drawdown` 可以产生分类区分，但不足以作为 continuation-as-action 的主线信号。它在 train 上有方向性，在 robustness 上失去 payoff 单调性；因此不能推进 16F chained action transition freeze，也不应把 16D/16E 的 action 解释成 exit、holding、risk overlay 或 deployment policy。

更合适的处理是关闭当前 continuation-as-action mainline，并回到 topic 级 research direction：

1. 若继续研究 continuation，需要先重新定义目标函数，使 label 直接面向 payoff severity 或 utility，而不是仅面向 survival/positive 0/1。
2. 若保留当前 score，只能把它视为 context diagnostic 或弱 meta feature，不能作为独立 action gate。
3. 下一步不应写 16F；也不应直接写 A/B/C requirement，除非有新的研究方向先解释 robustness payoff non-monotonicity。

最终裁决保持：`next_allowed_requirement = none`。

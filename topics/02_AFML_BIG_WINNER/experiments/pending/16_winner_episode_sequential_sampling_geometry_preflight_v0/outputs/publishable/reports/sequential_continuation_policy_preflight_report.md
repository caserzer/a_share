# 16D Sequential Continuation Policy Preflight Report

## 1. 单行裁决

`decision_state = 16D_policy_preflight_ready_for_utility_diagnostic`；`next_allowed_requirement = requirement_16e_sequential_continuation_utility_diagnostic.md`。

16D 只是 counterfactual label-action preflight：把 16C 的 continuation score 变成 train-frozen 的 defend-vs-continue 标签动作，并检查它是否在抽样、context、neutral、search accounting 上可审计。它不授权 entry、exit、holding、deployment、return backtest 或 cost model。

## 2. 核心发现

| finding | evidence | implication |
| --- | --- | --- |
| 16D 可以进入 16E utility diagnostic | 全部 hard gate 为 `pass`，primary policy 为 `defense_bottom_30pct_continuation_score_v1` | 下一步只能评估 utility/return/cost/execution，不能把 16D 当交易策略 |
| primary defense rule 有真实的 negative capture | train 捕获 2,299/4,884 = 47.07% negative；robustness 捕获 196/526 = 37.26%；validation 捕获 81/180 = 45.00% | score 不只是排序噪声，能把一部分 deep-drawdown continuation risk 集中到低分桶 |
| robustness 上阈值迁移更保守 | train defense rate 30.00%，robustness defense rate 21.21%，validation defense rate 31.29% | train 分位数阈值没有在 robustness 上机械地防守 30%，说明 OOS score 分布更偏高；这是 caveat，但不是 fail |
| defense precision lift 跨 split 为正 | train +18.57pp，robustness +21.27pp，validation +15.62pp | 被防守的 binary steps 中 negative 密度显著高于 split base rate |
| positive sacrifice 可控但不小 | train sacrifice 21.73%，robustness 14.93%，validation 23.69% | 16E 必须用 utility 检验“少踩 negative”是否足以抵消“错防 positive” |
| signal 不只来自 known-failed morphology | non-known-failed context: train 3,765 binary / 1,097 negative / lift +18.13pp；robustness 907 binary / 224 negative / lift +25.30pp | 16D 通过 context-independence gate，但 validation non-known-failed 只有 53 binary rows，只能作 stress caveat |
| neutral population 很大，必须保留 caveat | neutral 占 labelable steps：train 26.10%，robustness 25.00%，validation 23.95% | neutral 不进入 threshold fit 和 binary confusion；16E 不得把 neutral 偷换成 negative 或 positive |

## 3. 口径说明

16D 的 target 仍来自 16B 的 `continuation_survival_h20_no_deep_drawdown`。`positive` 表示 h20 continuation survival；`negative` 表示 h20 内 deep drawdown；`neutral` 表示既非 positive 也非 negative。Threshold fitting 和 binary confusion 只使用 `positive + negative`，neutral rows 只在 threshold freeze 后进入 action coverage/readout。

Primary policy 固定为 train binary score bottom 30%：`defend if primary_score <= 0.457071`。这里的 `defend` 只是标签动作，不是 exit，不含价格收益、交易成本、滑点、成交约束或组合权重。

## 4. 16C Authorization Replay

| authorization_status | upstream_decision_state | upstream_next_allowed_requirement | train_binary_step_n | train_positive_n | train_negative_n | robustness_binary_step_n | robustness_positive_n | robustness_negative_n | robustness_roc_auc |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pass | 16C_sequential_continuation_separability_ready_for_policy_preflight | requirement_16d_sequential_continuation_policy_preflight.md | 14,962 | 10,078 | 4,884 | 1,872 | 1,346 | 526 | 0.672220 |

Finding：16D 没有从报告文本继承授权，而是复验 16C publishable decision/audit/manifest。16C 的 ready 裁决、h20/up50 label counts、primary model、CV AUC、robustness AUC、authorization booleans 均可复验，因此 16D 有权进入 policy preflight。

## 5. Score And Context Rebuild Lineage

| item | value |
| --- | ---: |
| rebuilt feature row n | 23,405 |
| rebuilt feature step key n | 23,405 |
| policy action panel row n | 93,620 |
| policy grid n | 4 |
| score row key match | exact |
| optional 16C score cache max abs diff | 0.000000 |
| replayed train AUC | 0.680264 |
| replayed robustness AUC | 0.672220 |
| replayed validation AUC | 0.610632 |
| source 16C train AUC | 0.680264 |
| source 16C robustness AUC | 0.672220 |
| source 16C validation AUC | 0.610632 |
| score orientation gate | pass |
| score rebuild lineage gate | pass |

| context rebuild source | joined_step_n | joined_cluster_n | missing_context_step_n | hard_context_projection_coverage | late_rescue_context_step_n | known_failed_context_any_step_n | non_known_failed_context_step_n | gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 16d_rebuilt_from_15b_membership_taxonomy_rules_and_16b_labels | 23,405 | 897 | 0 | 1.000000 | 11,533 | 17,354 | 6,051 | pass |

Insight：16D 重新从 16B labels、qfq/PIT universe 和 16C contract 构建 t0 feature/score panel；16C cache 只用于 exact replay。Known-failed context 也不是从报告读数复制，而是从 15B membership/taxonomy rule 和 16B label panel 重建。`joined_step_n = 23,405` 与 16D labelable steps 完全一致，context projection 没有 missing row。

## 6. Train-only Threshold Freeze

| policy_id | threshold_quantile | threshold_value | train_score_n | train_binary_score_n | neutral_rows_excluded_from_fit | validation_used_for_threshold | robustness_used_for_threshold |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| defense_bottom_10pct_continuation_score_v1 | 0.100000 | 0.300773 | 20,245 | 14,962 | true | false | false |
| defense_bottom_20pct_continuation_score_v1 | 0.200000 | 0.397638 | 20,245 | 14,962 | true | false | false |
| defense_bottom_30pct_continuation_score_v1 | 0.300000 | 0.457071 | 20,245 | 14,962 | true | false | false |
| defense_bottom_40pct_continuation_score_v1 | 0.400000 | 0.501480 | 20,245 | 14,962 | true | false | false |

Finding：所有阈值只来自 train binary primary-model score rows。Validation 和 robustness 没有参与阈值选择；四个 grid points 是 preregistered frontier readout，primary 固定为 bottom 30%，不是事后挑出来的最优点。

## 7. Primary Policy Confusion

| split_bucket | binary_step_n | positive_n | negative_n | defended_binary_step_n | defended_positive_n | defended_negative_n | binary_negative_base_rate | defense_rate | defense_negative_capture_rate | positive_sacrifice_rate | defense_precision | precision_lift | continue_negative_leakage_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 14,962 | 10,078 | 4,884 | 4,489 | 2,190 | 2,299 | 0.326427 | 0.300027 | 0.470721 | 0.217305 | 0.512141 | 0.185714 | 0.529279 |
| robustness | 1,872 | 1,346 | 526 | 397 | 201 | 196 | 0.280983 | 0.212073 | 0.372624 | 0.149331 | 0.493703 | 0.212720 | 0.627376 |
| validation | 505 | 325 | 180 | 158 | 77 | 81 | 0.356436 | 0.312871 | 0.450000 | 0.236923 | 0.512658 | 0.156223 | 0.550000 |

Finding：primary bottom-30% defense rule 在 train 上防守 4,489 个 binary steps，其中 2,299 个是 negative，defense precision 为 51.21%，高于 train base negative rate 32.64%。Robustness 上防守更少，只防守 397 个 binary steps，但 precision 仍为 49.37%，高于 robustness base negative rate 28.10%。

Insight：这是一个可用来进入 utility diagnostic 的“风险集中”现象，但不是交易结论。Train 上仍有 2,585 个 negative 被 continue，negative leakage = 52.93%；robustness 上 leakage 更高，为 62.74%。所以 16D 证明的是 low-score bucket 更危险，不是证明当前 defend action 已经经济最优。

## 8. Tradeoff Frontier

| split_bucket | defense_quantile | threshold_value | defense_rate | negative_capture_rate | positive_sacrifice_rate | defense_precision | precision_lift | negative_leakage_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 0.10 | 0.300773 | 0.100053 | 0.192670 | 0.055170 | 0.628591 | 0.302164 | 0.807330 |
| robustness | 0.10 | 0.300773 | 0.106303 | 0.224335 | 0.060178 | 0.592965 | 0.311982 | 0.775665 |
| validation | 0.10 | 0.300773 | 0.124752 | 0.205556 | 0.080000 | 0.587302 | 0.230866 | 0.794444 |
| train | 0.20 | 0.397638 | 0.200040 | 0.338862 | 0.132764 | 0.552957 | 0.226530 | 0.661138 |
| robustness | 0.20 | 0.397638 | 0.161859 | 0.315589 | 0.101783 | 0.547855 | 0.266872 | 0.684411 |
| validation | 0.20 | 0.397638 | 0.259406 | 0.372222 | 0.196923 | 0.511450 | 0.155015 | 0.627778 |
| train | 0.30 | 0.457071 | 0.300027 | 0.470721 | 0.217305 | 0.512141 | 0.185714 | 0.529279 |
| robustness | 0.30 | 0.457071 | 0.212073 | 0.372624 | 0.149331 | 0.493703 | 0.212720 | 0.627376 |
| validation | 0.30 | 0.457071 | 0.312871 | 0.450000 | 0.236923 | 0.512658 | 0.156223 | 0.550000 |
| train | 0.40 | 0.501480 | 0.400013 | 0.573301 | 0.316035 | 0.467836 | 0.141409 | 0.426699 |
| robustness | 0.40 | 0.501480 | 0.258547 | 0.431559 | 0.190936 | 0.469008 | 0.188025 | 0.568441 |
| validation | 0.40 | 0.501480 | 0.384158 | 0.527778 | 0.304615 | 0.489691 | 0.133255 | 0.472222 |

Finding：frontier 单调性健康：从 10% 到 40%，negative capture 上升，positive sacrifice 也同步上升；全部 split 的 precision 均高于自身 base negative rate。10% 桶最“纯”，但漏掉大多数 negative；40% 桶 capture 更高，但 positive sacrifice 明显变重。30% 是需求预注册的折中点，不是从 validation/robustness 中调出来的。

Insight：robustness 的 defense rate 在 20/30/40% 桶都低于 train 对应分位数，说明 train-frozen score 阈值迁移到 robustness 后更保守。这个现象对 preflight 是可接受的，因为 hard gate 看的是 capture、sacrifice、precision lift，而不是强制每个 split 都防守同一比例；但 16E 必须把它作为 capacity/coverage caveat 处理。

## 9. Known-failed Context Stratification

| split_bucket | context_stratum | binary_step_n | binary_share_in_split | negative_n | defended_binary_step_n | defended_negative_n | negative_base_rate | defense_rate | negative_capture_rate | positive_sacrifice_rate | defense_precision | precision_lift | status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | all_steps | 14,962 | 1.000000 | 4,884 | 4,489 | 2,299 | 0.326427 | 0.300027 | 0.470721 | 0.217305 | 0.512141 | 0.185714 | readout |
| train | late_rescue_context | 7,603 | 0.508154 | 2,537 | 2,307 | 1,194 | 0.333684 | 0.303433 | 0.470635 | 0.219700 | 0.517555 | 0.183871 | readout |
| train | non_late_rescue_context | 7,359 | 0.491846 | 2,347 | 2,182 | 1,105 | 0.318929 | 0.296508 | 0.470814 | 0.214884 | 0.506416 | 0.187487 | readout |
| train | known_failed_context_any | 11,197 | 0.748363 | 3,787 | 3,408 | 1,788 | 0.338216 | 0.304367 | 0.472142 | 0.218623 | 0.524648 | 0.186432 | readout |
| train | non_known_failed_context | 3,765 | 0.251637 | 1,097 | 1,081 | 511 | 0.291368 | 0.287118 | 0.465816 | 0.213643 | 0.472710 | 0.181343 | pass |
| robustness | all_steps | 1,872 | 1.000000 | 526 | 397 | 196 | 0.280983 | 0.212073 | 0.372624 | 0.149331 | 0.493703 | 0.212720 | readout |
| robustness | late_rescue_context | 319 | 0.170406 | 105 | 64 | 34 | 0.329154 | 0.200627 | 0.323810 | 0.140187 | 0.531250 | 0.202096 | readout |
| robustness | non_late_rescue_context | 1,553 | 0.829594 | 421 | 333 | 162 | 0.271088 | 0.214424 | 0.384798 | 0.151060 | 0.486486 | 0.215398 | readout |
| robustness | known_failed_context_any | 965 | 0.515491 | 302 | 231 | 113 | 0.312953 | 0.239378 | 0.374172 | 0.177979 | 0.489177 | 0.176224 | readout |
| robustness | non_known_failed_context | 907 | 0.484509 | 224 | 166 | 83 | 0.246968 | 0.183021 | 0.370536 | 0.121523 | 0.500000 | 0.253032 | pass |
| validation | all_steps | 505 | 1.000000 | 180 | 158 | 81 | 0.356436 | 0.312871 | 0.450000 | 0.236923 | 0.512658 | 0.156223 | readout |
| validation | late_rescue_context | 368 | 0.728713 | 146 | 122 | 67 | 0.396739 | 0.331522 | 0.458904 | 0.247748 | 0.549180 | 0.152441 | readout |
| validation | non_late_rescue_context | 137 | 0.271287 | 34 | 36 | 14 | 0.248175 | 0.262774 | 0.411765 | 0.213592 | 0.388889 | 0.140714 | readout |
| validation | known_failed_context_any | 452 | 0.895050 | 172 | 146 | 77 | 0.380531 | 0.323009 | 0.447674 | 0.246429 | 0.527397 | 0.146866 | readout |
| validation | non_known_failed_context | 53 | 0.104950 | 8 | 12 | 4 | 0.150943 | 0.226415 | 0.500000 | 0.177778 | 0.333333 | 0.182390 | stress_readout |

Finding：known-failed exposure 很高，尤其 validation 中 `known_failed_context_any` 占 89.51% binary steps，train 也占 74.84%。这说明 16D 仍处在 15B morphology 的阴影里，不能声称已经获得独立交易规则。

关键通过点在 non-known-failed context：train 有 3,765 个 binary steps、1,097 个 negative，defended negative = 511，precision lift = +18.13pp；robustness 有 907 个 binary steps、224 个 negative，defended negative = 83，precision lift = +25.30pp。也就是说，即使剔除 known-failed context，low-score bucket 仍然集中 negative。Validation non-known-failed 只有 53 个 binary steps 和 8 个 negative，不能作为 hard evidence，只能作为 stress readout。

Insight：16D 的结论不是“late-rescue 已被解决”，而是“policy score 在非 known-failed 语境中也有 defend-vs-continue 的可用分层”。这足以进入 16E，但 16E 必须继续把 known-failed exposure 作为 caveat 或分层 utility readout。

## 10. Neutral Handling

| split_bucket | labelable_step_n | binary_step_n | neutral_step_n | neutral_rate | neutral_defended_n | neutral_continued_n | neutral_defense_rate | neutral_handling_gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | 20,245 | 14,962 | 5,283 | 0.260953 | 1,095 | 4,188 | 0.207269 | pass |
| robustness | 2,496 | 1,872 | 624 | 0.250000 | 89 | 535 | 0.142628 | pass |
| validation | 664 | 505 | 159 | 0.239458 | 25 | 134 | 0.157233 | pass |

Finding：neutral rows 规模不小：train 5,283、robustness 624、validation 159，约占 labelable population 的四分之一。它们没有被映射成 negative，也没有参与 threshold fitting 或 binary confusion。

Insight：neutral defense rate 低于对应 split 的 binary defense rate，说明 policy 没有把 ambiguous rows 大量扫进 defense bucket。但 neutral 在 16E 中仍必须单独处理，因为 utility 评估如果把 neutral 简化成无成本 continue 或无收益 defend，都会扭曲实际 tradeoff。

## 11. Stability And Search Accounting

| split_bucket | grid_point_n | negative_capture_monotonic_status | positive_sacrifice_monotonic_status | defense_precision_above_base_grid_n | stability_status |
| --- | ---: | --- | --- | ---: | --- |
| train | 4 | pass | pass | 4 | pass |
| robustness | 4 | pass | pass | 4 | pass |
| validation | 4 | pass | pass | 4 | pass |

| search_family | primary_policy_id | policy_grid_pre_registered | validation_used_for_policy_selection | robustness_used_for_policy_selection | return_metric_used_for_selection | cost_metric_used_for_selection | search_accounting_gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sequential_continuation_policy_preflight | defense_bottom_30pct_continuation_score_v1 | true | false | false | false | false | pass |

Finding：frontier monotonicity 和 precision-above-base checks 均通过；没有 validation/robustness threshold selection，没有 return/cost metric selection，也没有 model family、feature selection 或 hyperparameter grid search。

Insight：这保持了 16D 的证据边界：它只是用 train-only frozen score threshold 证明 label-action split 可审计。任何关于收益、成本、滑点、成交、退出规则、仓位规模的判断都被推迟到 16E。

## 12. 16E Handoff

16D ready 的含义是：可以设计 `requirement_16e_sequential_continuation_utility_diagnostic.md`，评估 defend-vs-continue 是否在 utility 层面值得继续。16E 至少要继承以下约束：

- 不允许把 16D policy 解释成 entry 或完整 exit policy。
- 保持 h20/up50、non-overlap sampling、train-only preprocessing、train-frozen threshold。
- 正式计入 positive sacrifice、continued negative leakage、neutral handling、known-failed context exposure。
- 首次允许 utility/return/cost/execution 诊断时，必须重新定义可审计的边界和 fail-closed gate。

最终结论：16D 支持进入 16E utility diagnostic，但仍不授权任何真实或模拟交易部署。

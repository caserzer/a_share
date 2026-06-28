# 15B Winner Path Shape Taxonomy Diagnostic

## 1. 单行裁决

15B 的裁决状态为 `15B_no_stable_path_shape_taxonomy`。所有 hard audit gates 都通过，但 taxonomy 没有达到“稳定可用于后续 label revision”的要求。本实验仍只做 winner realized path shape taxonomy，不授权 signal search、entry、model 或 label deployment。

| item | value |
|---|---:|
| decision_state | `15B_no_stable_path_shape_taxonomy` |
| next_allowed_requirement | `none` |
| eligible_train_episode_cluster_n | 919 |
| material_path_type_n | 4 |
| largest_path_type_share_train | 0.335147 |
| unclassified_share_train | 0.344940 |
| validation_material_path_type_n | 1 |
| robustness_material_path_type_n | 2 |
| representative_taxonomy_disagreement_share | 0.726525 |
| representative_disagreement_support_gate | `False` |
| validation_material_path_type_support_gate | `False` |
| robustness_material_path_type_support_gate | `True` |
| stability_extreme_failure | `True` |
| entropy_incrementality_status | `incremental_shape_descriptor` |
| tradable_shape_share | 0.302503 |

Finding：15B 能把 realized winner path 分成若干可解释形态，但当前分类更像 descriptive taxonomy，而不是可稳定承接到 15C/16 系列的 label-design 基础。最大的阻断不是输入质量，也不是 qfq path 缺失，而是 cluster 内 anchor-defined paths 的异质性过高：`representative_taxonomy_disagreement_share = 0.726525`。

## 2. 本次重跑后的关键定义变化

本报告使用重跑后的 15B 定义：`long_duration` 不再使用绝对 `time_to_threshold_sessions >= q_time_to_threshold_75`，而使用：

```text
time_to_threshold_available_forward_share
  = time_to_threshold_sessions / available_forward_sessions

long_duration
  = time_to_threshold_available_forward_share
    >= q_time_to_threshold_available_forward_share_75
```

这一步保留 train-only frozen quantile 原则，但避免 validation / robustness 这种短压力测试窗在绝对 session gate 下结构性不可达。新的 train-only frozen threshold 为：

| feature_id | quantile_name | value | fit_population_n |
|---|---|---:|---:|
| time_to_threshold_available_forward_share | q_time_to_threshold_available_forward_share_75 | 0.316288 | 660 |

Insight：这不是用 validation / robustness 重调规则，而是把 duration 特征改成“在可观测机会窗中多晚才触达”。因此 robustness 上 `late_rescue_winner` 从之前的机械 0 恢复为可评估状态。

## 3. 输入与 Lineage Gate

15B 读取 15A row-level path-defined label cache，并以 `(instrument, reference_date, row_id, threshold_id)` 作为 source key。输入审计结果：

| gate | status |
|---|---|
| input_artifact_gate | pass |
| upstream_lineage_gate | pass |
| price_path_completeness_gate | pass |
| path_defined_label_adapter_gate | pass |
| path_defined_label_rebuild_gate | pass |
| episode_cluster_gate | pass |
| train_rule_fit_gate | pass |
| search_accounting_gate | pass |

15A cache 规模为 `1,226,145` rows。`up50pct` 的 path-winner anchor 数为 train `130,087`、validation `27,875`、robustness `53,089`。15B 的 qfq path completeness audit 覆盖 `1,449` instruments，缺失 qfq 或 hit_pos 越界均未触发 fail。

## 4. Denominator 与 Split 口径

15B 的 primary diagnostic unit 是 `winner_episode_cluster`，不是 anchor row。Train-only rule fitting 使用：

```text
threshold_id = up50pct
cluster_split_bucket = train
no member/calendar split overlap
primary_representative = medoid_anchor
```

Medoid scaler fit population 为 `57,524` 条 anchor paths；taxonomy quantile fit population 为 `660` 个 train single-split episode clusters。报告中的 split readout 使用 representative row 的 `split_bucket`，用于观察 train / validation / robustness 分布；跨 split clusters 保留为 caveat，不进入 train-only rule fitting。

Selected threshold `up50pct` 的 cluster split 结构如下：

| cluster_split_bucket | episode_cluster_n |
|---|---:|
| train | 667 |
| cross_split | 529 |
| robustness | 218 |
| validation | 45 |

跨 split 压力不小：`touches_multiple_split_buckets = 411`，`touches_multiple_calendar_split_buckets = 496`，其中 train-validation boundary overlap 为 `312`，validation-robustness boundary overlap 为 `369`。

## 5. Frozen Taxonomy Quantiles

| feature_id | quantile_name | value | used_by_predicate |
|---|---|---:|---|
| path_efficiency | q_efficiency_30 | 0.048829 | True |
| path_efficiency | q_efficiency_50 | 0.118516 | False |
| path_efficiency | q_efficiency_70 | 0.186829 | True |
| max_drawdown_before_hit_abs | q_max_drawdown_abs_30 | 0.181424 | True |
| max_drawdown_before_hit_abs | q_max_drawdown_abs_50 | 0.248702 | False |
| max_drawdown_before_hit_abs | q_max_drawdown_abs_70 | 0.383700 | True |
| underwater_days_share | q_underwater_share_50 | 0.902457 | True |
| underwater_days_share | q_underwater_share_70 | 0.965785 | True |
| directional_entropy_5state | q_entropy_30 | 0.933117 | False |
| directional_entropy_5state | q_entropy_50 | 0.958066 | False |
| directional_entropy_5state | q_entropy_70 | 0.973269 | True |
| trend_line_r2 | q_trend_r2_50 | 0.381878 | True |
| trend_line_r2 | q_trend_r2_70 | 0.599550 | True |
| top1_positive_gain_share | q_top1_gain_share_70 | 0.077400 | True |
| top1_positive_gain_share | q_top1_gain_share_85 | 0.116046 | True |
| top3_positive_gain_share | q_top3_gain_share_70 | 0.207103 | True |
| top3_positive_gain_share | q_top3_gain_share_85 | 0.315747 | True |
| large_up_day_count | q_large_up_day_count_70 | 6.000000 | True |
| time_to_threshold_available_forward_share | q_time_to_threshold_available_forward_share_75 | 0.316288 | True |
| pullback_5pct_count | q_pullback_5pct_count_50 | 3.000000 | True |
| pullback_5pct_count | q_pullback_5pct_count_70 | 4.000000 | True |

未被 predicate 使用的 median quantile 仍写入 audit，用于证明规则没有隐式引用。

## 6. Selected Threshold Path Type Readout

### 6.1 Train

| path_type | episode_cluster_n | share | winner_anchor_n |
|---|---:|---:|---:|
| unclassified_mixed_path | 308 | 0.335147 | 47,691 |
| late_rescue_winner | 264 | 0.287269 | 27,535 |
| stair_step_winner | 155 | 0.168662 | 37,158 |
| smooth_trend_winner | 111 | 0.120783 | 5,617 |
| jump_repricing_winner | 46 | 0.050054 | 1,875 |
| choppy_reversal_winner | 14 | 0.015234 | 465 |
| slow_grind_winner | 12 | 0.013058 | 5,486 |
| unclassified_short_path | 9 | 0.009793 | 40 |

Train 上没有单一 path type 垄断，最大类 `unclassified_mixed_path` 为 `33.51%`，低于 `0.75` 上限。但未分类仍高达 `34.49%`，说明 deterministic rule 仍遗漏了大量混合路径。

### 6.2 Validation

| path_type | episode_cluster_n | share | winner_anchor_n |
|---|---:|---:|---:|
| late_rescue_winner | 66 | 0.404908 | 12,764 |
| unclassified_mixed_path | 37 | 0.226994 | 5,270 |
| slow_grind_winner | 31 | 0.190184 | 8,076 |
| smooth_trend_winner | 13 | 0.079755 | 218 |
| jump_repricing_winner | 11 | 0.067485 | 899 |
| stair_step_winner | 4 | 0.024540 | 1,202 |
| unclassified_short_path | 1 | 0.006135 | 2 |

Validation 只有一个 material path type 通过支持门，`validation_material_path_type_n = 1`，因此不能证明 taxonomy 在压力测试集上有足够多样、稳定的形态覆盖。

### 6.3 Robustness

| path_type | episode_cluster_n | share | winner_anchor_n |
|---|---:|---:|---:|
| unclassified_mixed_path | 148 | 0.392573 | 23,287 |
| slow_grind_winner | 111 | 0.294430 | 25,682 |
| smooth_trend_winner | 39 | 0.103448 | 1,759 |
| jump_repricing_winner | 33 | 0.087533 | 2,061 |
| late_rescue_winner | 30 | 0.079576 | 3,406 |
| unclassified_short_path | 11 | 0.029178 | 12 |
| stair_step_winner | 5 | 0.013263 | 546 |

Robustness 上 `late_rescue_winner` 不再为 0：representative split readout 为 `30` clusters / `3,406` anchors；single-split cluster readout 为 `19` clusters / `1,177` anchors。之前全 0 是绝对 duration gate 的窗口长度伪影，不应被解释为 morphology 在 robustness 消失。

## 7. Cluster-Split Sanity Readout

以下表来自 taxonomy assignment panel，用于确认 split 口径差异。它不是 train-only rule fitting denominator，而是检查 path type 是否在 single-split 与 cross-split cluster 中一致可达。

| cluster_split_bucket | total_clusters | late_rescue | slow_grind | smooth_trend | stair_step | jump_repricing | unclassified_mixed |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 667 | 164 | 0 | 106 | 111 | 42 | 224 |
| validation | 45 | 13 | 0 | 11 | 1 | 7 | 12 |
| robustness | 218 | 19 | 46 | 36 | 2 | 27 | 77 |
| cross_split | 529 | 164 | 108 | 10 | 50 | 14 | 180 |

Normalized duration 后，`predicate_long_duration` 在 robustness single-split cluster 中命中 `138 / 218`，`late_rescue` 命中 `19 / 218`。这证明修正后的 duration gate 不是将 robustness 机械推入 late-rescue，而是只在同时满足 severe drawdown / high underwater / low efficiency 时分类。

## 8. Train Path Shape Median Profiles

| path_type | duration_share_median | time_to_sessions_median | path_efficiency_median | max_drawdown_abs_median | underwater_share_median | entropy_median | trend_r2_median | top3_gain_share_median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| jump_repricing_winner | 0.036537 | 45.5 | 0.283135 | 0.147608 | 0.770284 | 0.936160 | 0.463403 | 0.363572 |
| late_rescue_winner | 0.719042 | 1,014.0 | 0.023301 | 0.529256 | 0.986262 | 0.953495 | 0.119457 | 0.037918 |
| slow_grind_winner | 0.538817 | 697.0 | 0.071808 | 0.160308 | 0.944104 | 0.976095 | 0.609749 | 0.051225 |
| smooth_trend_winner | 0.021062 | 30.0 | 0.387946 | 0.099354 | 0.592593 | 0.924117 | 0.784075 | 0.373742 |
| stair_step_winner | 0.110143 | 157.0 | 0.120978 | 0.207803 | 0.887967 | 0.969552 | 0.569544 | 0.138609 |
| unclassified_mixed_path | 0.124784 | 187.5 | 0.103767 | 0.277466 | 0.926829 | 0.962305 | 0.202375 | 0.134446 |

Interpretation：

- `late_rescue_winner` 是最清晰的失败/补救型路径：duration share 中位数 `0.719`，绝对耗时中位数 `1,014` sessions，drawdown 中位数 `52.93%`，水下时间占比 `98.63%`，path efficiency 只有 `0.0233`。
- `smooth_trend_winner` 是最“干净”的趋势类：duration share `0.0211`，drawdown `9.94%`，trend R2 `0.7841`，path efficiency `0.3879`。
- `jump_repricing_winner` 的 top3 positive gain share 中位数 `0.3636`，确实捕捉到收益集中，而不是仅仅捕捉快涨。
- `unclassified_mixed_path` 的 drawdown、underwater、trend 都处在中间区域，说明它不是单纯垃圾桶，而是多个机制混合后的残差桶。

## 9. Threshold Sensitivity

| threshold | split | total_clusters | late_rescue | unclassified_mixed | stair_step | smooth_trend | jump_repricing | slow_grind |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| up50pct | train | 919 | 264 | 308 | 155 | 111 | 46 | 12 |
| up50pct | validation | 163 | 66 | 37 | 4 | 13 | 11 | 31 |
| up50pct | robustness | 377 | 30 | 148 | 5 | 39 | 33 | 111 |
| up100pct | train | 607 | 244 | 100 | 177 | 38 | 7 | 39 |
| up100pct | validation | 82 | 32 | 8 | 5 | 5 | 1 | 31 |
| up100pct | robustness | 155 | 17 | 33 | 1 | 8 | 4 | 92 |
| up150pct | train | 421 | 188 | 51 | 131 | 14 | 3 | 34 |
| up150pct | validation | 55 | 27 | 4 | 0 | 3 | 0 | 21 |
| up150pct | robustness | 88 | 11 | 8 | 0 | 1 | 4 | 64 |

Threshold insight：阈值越高，`late_rescue_winner` 和 `stair_step_winner` 在 train 中更占主导，`smooth_trend_winner` 迅速变少。Robustness 则更偏向 `slow_grind_winner` 和 `unclassified_mixed_path`。这说明 path-shape taxonomy 对 threshold 有解释力，但它还不是稳定 label family。

## 10. Entropy Incrementality

Entropy 没有与任何主 feature 出现绝对 Spearman 相关 `>= 0.80`，因此当前状态是 `incremental_shape_descriptor`。

| feature_pair | train_corr | validation_corr | robustness_corr | redundancy_flag |
|---|---:|---:|---:|---|
| entropy::time_to_threshold_sessions | 0.106807 | 0.203441 | 0.313438 | False |
| entropy::time_to_threshold_available_forward_share | 0.110699 | 0.246072 | 0.247959 | False |
| entropy::path_efficiency | -0.098412 | -0.214879 | -0.246787 | False |
| entropy::max_drawdown_before_hit_abs | 0.063939 | 0.185227 | 0.117941 | False |
| entropy::underwater_days_share | 0.061919 | 0.162876 | 0.214005 | False |
| entropy::top3_positive_gain_share | -0.115073 | -0.211299 | -0.281509 | False |
| entropy::trend_line_r2 | -0.048507 | -0.139253 | -0.081118 | False |
| entropy::realized_volatility_to_hit | -0.152886 | -0.139586 | -0.240327 | False |
| entry-vol entropy::realized-vol entropy | 0.290559 | NaN | NaN | False |

Entropy ablation 也支持“增量但非主导”的判断：`up50pct` train 中有 `30 / 919 = 3.26%` assignments 被 entropy 改变；validation 为 `4 / 163 = 2.45%`；robustness 为 `5 / 377 = 1.33%`。这不足以单独构成 label，但能帮助区分 choppy / trend / mixed path。

## 11. Wick-Hit 与 Close Path 风险

15B 的 hit detection 继承 15A high-based first passage，而 path-shape features 用 qfq close segment。因此必须确认 wick-hit-only 没有污染某个 path type。

Selected threshold train 总体 `wick_hit_only_share` 为 `0.5299`。按 path type 看：

| path_type | wick_hit_only_share_by_path_type |
|---|---:|
| jump_repricing_winner | 0.630435 |
| smooth_trend_winner | 0.603604 |
| stair_step_winner | 0.548387 |
| late_rescue_winner | 0.522727 |
| choppy_reversal_winner | 0.500000 |
| unclassified_mixed_path | 0.493506 |
| slow_grind_winner | 0.416667 |
| unclassified_short_path | 0.444444 |

Finding：wick-hit-only 并没有集中污染 `choppy_reversal_winner` 或 `late_rescue_winner`。相反，jump/smooth 的 wick share 更高，说明 high-based hit 与 close-based path shape 的差异需要保留为 caveat，但不是当前 blocked 的主因。

## 12. Cluster 内异质性是主阻断

| metric | p25 | median | p75 | max |
|---|---:|---:|---:|---:|
| cluster_anchor_n | 15.000000 | 63.000000 | 217.500000 | 871 |
| cluster_distinct_path_type_n | 2.000000 | 3.000000 | 5.000000 | 8 |
| cluster_internal_path_type_entropy | 0.147322 | 0.667179 | 0.812535 | 1.000000 |
| cluster_dominant_path_type_share | 0.496377 | 0.666667 | 0.976744 | 1.000000 |

Representative disagreement 为 `1,060 / 1,459 = 0.726525`。这意味着多数 episode cluster 内，不同 anchor-defined opportunity path 会落入不同 path type。单个 medoid representative 虽然能给 cluster 一个可重复分类，但不能充分代表该 cluster 内所有 anchor 的交易机会形态。

AFML interpretation：这是一种 sample construction 问题。一个 winner episode 不是天然等于一个单一可交易 label state；同一上涨 episode 内的早期 anchor、突破前 anchor、回撤后 anchor 面临不同 continuation 问题。15B 的 taxonomy 能描述 realized path family，但还不能直接决定下一步 label。

## 13. Split 稳定性

| item | value |
|---|---:|
| js_divergence_train_validation_path_type_distribution | 0.094898 |
| js_divergence_train_robustness_path_type_distribution | 0.161923 |
| representative_taxonomy_disagreement_share | 0.726525 |
| cluster_internal_path_type_entropy_median | 0.601405 |
| cluster_internal_path_type_entropy_p75 | 0.794907 |
| cluster_dominant_path_type_share_median | 0.761905 |
| cluster_dominant_path_type_share_p25 | 0.535831 |
| slow_fast_path_type_composition_delta | 0.426494 |
| threshold_sensitivity_path_type_rank_stability | 0.766481 |
| taxonomy_stability_status | pass |
| stability_extreme_failure | True |

Split divergence 本身不极端，train-validation `0.0949`、train-robustness `0.1619` 都没有显示灾难性漂移。但 representative disagreement、slow/fast composition delta 和 validation material support 共同阻断了 taxonomy escalation。

## 14. Findings

1. 15B 的输入链路是可信的。所有 required input、qfq bounds、adapter rebuild、search accounting 都 pass，当前 blocked 不是数据读取失败。
2. Normalized duration 修复了 robustness `late_rescue_winner = 0` 的伪影。新结果显示 robustness 确实存在 late-rescue-like paths，但占比低于 train/validation。
3. Train path types 有解释力，但未分类残差仍大。`unclassified_mixed_path = 33.51%`，接近 `unclassified_share_train = 34.49%`。
4. Validation 是薄弱点。Validation 只有 `1` 个 material path type，不能证明 taxonomy 在压力测试集上有足够稳定的 path-family support。
5. 最大阻断是 cluster 内 anchor heterogeneity。`representative_taxonomy_disagreement_share = 72.65%` 表明“一个 episode cluster 一个 path type”的压缩过强。
6. Entropy 是增量 descriptor，不是 label。它与 duration、drawdown、efficiency、gain concentration 的相关性都不高，但 ablation 只改变少量 assignment。
7. Wick-hit-only 风险需要保留，但不是主阻断。它没有集中污染 choppy 或 late-rescue family。

## 15. Insight And Next Step

15B 的结果不支持把 `winner_episode_cluster` 直接升级成稳定 taxonomy label。更合理的方向是把 15B 当作 morphology diagnostic，而不是 label-authorizing step。

下一步如果继续推进，应避免再问“这个 episode 是什么 path type”，而应转成“在一个 winner episode 内，某个 non-overlapping step 是否还有 continuation value”。这正是 16A/16B 的方向：先审 sampling geometry，再设计 continuation label，并且用 known-failed morphology overlap 检查新 label 是否只是复刻 late-rescue / jump / choppy 失败家族。

当前 15B 不授权：

```text
label_deployment_authorized = False
signal_search_authorized = False
model_training_authorized = False
entry_policy_authorized = False
next_allowed_requirement = none
```

结论：15B 已经提供有用的 realized path-shape map，但它不是稳定的 primary label taxonomy。它的价值在于为 16 系列提供 caveat、known-failed family 定义和 readout baseline，而不是单独打开 separability search。

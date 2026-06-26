# 需求：15B Winner Path Shape Taxonomy Diagnostic

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/15_path_defined_winner_episode_label_v0
SOURCE_EP14_ROOT = TOPIC_ROOT/experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0
SOURCE_EP13_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
SOURCE_EP12_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 以 `SOURCE_EP14_ROOT/`、`SOURCE_EP13_ROOT/`、`SOURCE_EP12_ROOT/` 表达的路径必须先解析到对应 episode root，再写入 `input_artifact_audit.csv`。
5. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
6. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、universe membership 不可证明、price path completeness 不可证明、episode clustering 不可证明、taxonomy rule provenance 不可证明时 fail closed。
7. 不得从报告文本、图像、人工讨论文本、聚合 readout 或未来标签反推出逐行 universe、episode membership、label、split 边界、entry 价格或 decision point。

## 1. 实验身份

```text
experiment_id = 15_path_defined_winner_episode_label_v0
phase_id = 15B
run_id = 15B_winner_path_shape_taxonomy_diagnostic
status = draft_ready_for_review
expected_entrypoint = src/run_15b_winner_path_shape_taxonomy_diagnostic.py
expected_config = configs/config_15b_winner_path_shape_taxonomy_diagnostic.yaml
expected_test_file = tests/test_15b_winner_path_shape_taxonomy_diagnostic.py
source_plan = EXPERIMENT_ROOT/research_plan.md
upstream_requirement_15a = EXPERIMENT_ROOT/requirement_15a_winner_episode_label_censoring_diagnostic.md
```

15B 是 Episode 15 在 15A 之后插入的 label-form diagnostic。它取代原计划中直接进入 `path-defined winner separability diagnostic` 的下一步。原因是 15A 已证明 fixed-horizon label 存在 material right-censoring，但也暴露出更底层的问题：

```text
path_winner 只说明未来是否达到涨幅阈值，
不说明这段上涨是顺滑趋势、阶梯趋势、跳涨重估、曲折反转，还是长时间磨出来的 late rescue。
```

15B 的目标不是预测 winner，也不是寻找 entry。15B 只回答一个更前置的 label 定义问题：

```text
在把 path-defined winner 用于任何 separability / feature / model / signal 之前，
能否先把 winner 的 realized path shape 分成稳定、可解释、episode 去重后的若干类型？
```

15B 不得产生任何交易、仓位、alpha、entry、meta-labeling、模型或 label 部署授权。即使 15B 找到稳定 path type，也只能授权后续新建：

```text
requirement_15c_path_shape_label_separability_diagnostic.md
```

## 2. 背景判断

15A 的正向发现是：fixed-120d label 会系统性漏掉慢速 path-defined winners。15A 的负向发现是：slow winner 与已知失败的 t0-close compression / drawdown-reversal morphology 仍有重叠，不足以直接授权 separability 或 signal search。

更关键的是，15A 的 anchor overlap density 说明大量 winner anchor rows 是同一段上涨路径的不同切片：

```text
up50pct train:
  winner_anchor_n = 130087
  approx_cluster_n = 1040
  median_rows_per_cluster = 64
  p90_rows_per_cluster = 340.50
```

因此，继续用 anchor row 直接定义 winner 会有两个问题：

1. 同一段 market episode 被连续 anchor 重复计数，导致有效样本独立性被高估。
2. `fast` / `slow` 只描述达标时间，不描述上涨路径形态；真正需要先解决的是 path shape taxonomy。

AFML 决策口径：

```text
label horizon error != tradable morphology
path_winner outcome != winner path type
winner path type != t0-predictable alpha
```

15B 只处理第二层：`path_winner outcome -> winner path type`。

### 2.1 相对 15A `next_allowed_requirement = none` 的重新授权论证

15A 报告的最终裁决是 `15A_material_censoring_but_slow_winner_overlaps_known_failed_morphology`，并据此输出：

```text
next_allowed_requirement = none
label_deployment_authorized = False
signal_search_authorized = False
```

表面上这把 15B 关在门外。15B 的启动依据必须显式论证清楚，否则违反本 topic 的 fail-closed 纪律。论证如下：

```text
1. 15A 真正被证实的是 material right-censoring：
   input / upstream_lineage / universe_membership / price_path_completeness /
   label_rebuild / censoring_isolation / winner_set_difference / search_accounting
   八个 gate 全部 pass，share_beyond_120d 在 train/validation/robustness 均显著为正。
   这一发现成立，是 label 定义层面的风险暴露，不被 15B 推翻。

2. 15A 用于否定 "slow winner 形态独立性" 的方法是 t0-close 截面状态：
   compression_state  = vol_compression_20d_60d <= train q20
   drawdown_reversal_state = max_drawdown_20d <= train q20
   这两者只描述 entry 时点的横截面快照，结构上无法描述 entry 之后
   realized forward path 的形状（efficiency / drawdown path / monotonicity /
   entropy / gain concentration）。

3. 因此 15A 的 slow_winner_morphology_distinct = overlaps_known_failed_morphology
   是 "用错误的形态定义得到的否定"，它否定的是 "slow winner 的 t0 截面状态与已失败形态可分"，
   而不是 "slow winner 的 realized path shape 与已失败形态可分"。
   前者的否定不能传递为后者的否定。

4. 15B 的启动依据 = 15A 已证实的 censoring（label 定义风险），
   而不是 15A 未授权的 separability。15B 不复活 15A 未授权的 entry / signal / model；
   它只在 label 定义层把 "winner outcome" 细化为 "winner path type"。
```

据此，15B 的 `next_allowed_requirement` 来源不是 15A 的授权字段（15B 在 §5.2 明确不继承它们），而是上述对 15A 方法局限的论证。该论证必须在 15B report 第 2 节复述，并在 `search_accounting_audit.csv` 中以
`startup_authorization_basis = 15A_material_censoring_finding_not_15A_morphology_verdict` 记录。

## 3. 核心问题

15B 回答以下问题：

```text
Q1. 能否从 15A 的 path-defined winner lineage 出发，构造 episode 去重后的 winner path sample，
    避免把同一段上涨路径的连续 anchor rows 当成独立 episode？

Q2. 在 selected threshold = up50pct 下，winner 的 realized path 是否能按形态分成稳定类别，
    而不只是按 time-to-threshold 分成 fast / slow？

Q3. entropy 是否提供独立的 path-shape 信息，还是仅仅是 duration、volatility、drawdown、
    top-k gain concentration 的换名？

Q4. 各类 path type 在 train / validation / robustness 上是否有可解释的 base rate、
    duration、drawdown、efficiency、entropy、gain concentration 差异？

Q5. 哪些 path type 可以成为后续 separability diagnostic 的候选 label primitive？
    哪些 path type 只能作为 descriptive readout，不应进入后续预测任务？
```

必须输出一个单一裁决：

```text
decision_state
```

## 4. Scope Boundary

15B 允许做：

```text
1. 复用 15A / 14A / 13A native opportunity universe lineage 与 split boundary；
2. 从 raw qfq bars 重建 path-defined winner interval；
3. 对 path winner intervals 做 transitive overlap clustering，构造 episode-level diagnostic unit；
4. 在 forward realized path 上计算 shape descriptors，包括 efficiency、drawdown、pullback、
   entropy、trend linearity、gain concentration、time-to-threshold；
5. 用 train-only 分位数冻结 deterministic path-type taxonomy；
6. 将冻结 taxonomy 应用到 validation / robustness / all，做 readout-only stability 检查；
7. 对 entropy 做 incrementality diagnostic，防止把 entropy 当成单独 winner 定义；
8. 输出确定性 next-research decision map。
```

15B 明确不是：

```text
signal search
t0 feature search
separability test
event mining
sequence mining
meta-labeling
model training
entry / exit / holding policy
cost model
portfolio backtest
label deployment authorization
```

15B 可以使用未来 price path 来描述已发生的 winner path shape，因为这是 label diagnostic；但任何与后续 prediction / entry 有关的字段都必须标记为 out of scope。

## 5. 继承边界

### 5.1 允许继承

15B 继承 15A 的以下定义：

```text
anchor_record_unit = instrument x reference_date
label_record_unit = instrument x reference_date x threshold_id
reference_date = PIT executable row date
reference_pos = qfq daily position at reference_date
entry_anchor = next executable open
selected_threshold_id = up50pct
selected_threshold_return = 0.50
threshold_sensitivity_grid = {up50pct, up100pct, up150pct}
split boundary from 12A7g / 13A / 14A
universe definition from PIT topn 400/100 executable membership
censored rows are never confirmed negatives
```

15B 必须读取以下 15A artifacts：

```text
EXPERIMENT_ROOT/outputs/publishable/tables/15A_winner_episode_label_censoring_diagnostic/winner_episode_label_censoring_decision.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15A_winner_episode_label_censoring_diagnostic/winner_set_difference_readout.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15A_winner_episode_label_censoring_diagnostic/time_to_threshold_distribution_readout.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15A_winner_episode_label_censoring_diagnostic/episode_overlap_density_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15A_winner_episode_label_censoring_diagnostic/search_accounting_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15A_winner_episode_label_censoring_diagnostic/upstream_lineage_audit.csv
```

15B 可以使用 15A / 14A / 13A local cache 作为加速输入与对照：

```text
EXPERIMENT_ROOT/outputs/local_cache/15A_winner_episode_label_censoring_diagnostic/path_defined_label_panel.parquet
SOURCE_EP14_ROOT/outputs/local_cache/14A_full_native_sparse_state_change_event_utility_preflight/native_rebuild_panel.parquet
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_universe_panel.parquet
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_label_panel.parquet
```

如果 15A row-level path-defined label cache 不存在，15B runner 必须从 15A requirement 的 frozen formula、raw PIT universe 与 qfq bars 重建。不得从 15A 聚合 tables 反推逐行 labels。

#### 5.1.1 15A row-level adapter freeze

15B 若读取 15A row-level cache，必须使用以下 adapter，而不是重新猜字段名：

```text
source_row_key = (instrument, reference_date, row_id, threshold_id)

15B.source_path_winner          <- 15A.path_winner
15B.source_is_censored          <- 15A.is_censored
15B.winner_interval_start_pos   <- 15A.entry_pos
15B.winner_interval_start_date  <- 15A.entry_date
15B.winner_interval_start_price <- 15A.entry_price
15B.winner_interval_end_pos     <- 15A.episode_threshold_pos
15B.time_to_threshold_sessions  <- 15A.time_to_threshold_sessions
15B.first_threshold_hit_pos     <- 15A.episode_threshold_pos
15B.first_threshold_hit_date    <- qfq trading date at episode_threshold_pos
15B.entry_volatility_20d        <- 15A.volatility_20d
15B.fast_winner_flag            <- 15A.fast_winner_flag
15B.slow_winner_flag            <- 15A.slow_winner_flag
```

`first_threshold_hit_date` 不存在于 15A cache，必须从 qfq bar index 用 `episode_threshold_pos` 重建。若 `episode_threshold_pos` 超出该 instrument qfq bars、为 NaN、或与 `path_winner = true` 不一致，`path_defined_label_rebuild_gate` 必须 fail closed。

15B 必须输出 adapter audit 字段：

```text
source_row_key
adapter_source_path
adapter_required_columns_present
adapter_hit_pos_rebuild_status
adapter_row_count
adapter_duplicate_source_row_key_n
adapter_status
```

### 5.2 不得继承为结论

15B 不得把以下 15A 结论直接当成 15B 结论：

```text
slow_winner_morphology_distinct_status
known_failed_morphology_overlap_status
next_allowed_requirement
label_deployment_authorized
signal_search_authorized
```

15A 的这些字段只能作为背景与 fail-closed guard。15B 必须基于 realized path shape 自己产生裁决。

## 6. Primary Unit 与 Episode Clustering

15B 的 primary diagnostic unit 是：

```text
primary_count_unit = winner_episode_cluster
```

不是 anchor row。

Anchor-level rows 仍可输出，但只能作为 secondary readout：

```text
secondary_count_unit = winner_anchor_row
secondary_role = audit_only_anchor_density_not_primary_denominator
```

### 6.1 Anchor winner interval

对每个 `path_winner = true` 的 label row，构造：

```text
winner_interval_start_pos = entry_pos
winner_interval_end_pos = first_threshold_hit_pos
winner_interval_start_date = entry_date
winner_interval_end_date = first_threshold_hit_date
time_to_threshold_sessions = winner_interval_end_pos - winner_interval_start_pos
```

`path_winner = false` 或 `is_censored = true` 的 rows 不进入 primary taxonomy，只能进入 censoring / non-hit readout。

### 6.2 Transitive overlap cluster

在每个 `(instrument, threshold_id)` 内，对全部 winner intervals 做 transitive overlap merge。不得先按 `split_bucket` 切分后再聚类，因为那会把跨 split 的同一段上涨 episode 人工拆开。

```text
interval_i overlaps interval_j iff
  interval_i.start_pos <= interval_j.end_pos
  and interval_j.start_pos <= interval_i.end_pos

cluster = connected component under interval overlap graph
```

必须使用 union-find 或等价的 deterministic connected-component algorithm。不得只做相邻 row greedy merge，除非能证明结果等价于 transitive closure。

Cluster id 必须 deterministic：

```text
episode_cluster_id =
  threshold_id + "::" + instrument + "::" + zero_padded_cluster_ordinal_by_cluster_start_pos
```

Cluster ordering 使用：

```text
cluster_start_pos asc, cluster_end_pos asc, min(row_id) asc
```

### 6.3 Cluster representative policy

15B 必须先对 cluster 内每个 winner anchor 计算 anchor-level path shape metrics，再选择代表 anchor。不得用尚未定义的 representative segment 反过来选择 medoid。

每个 cluster 必须输出三个 deterministic representative anchor：

```text
earliest_anchor = cluster 内 entry_pos 最小的 anchor
shortest_duration_anchor = cluster 内 time_to_threshold_sessions 最小的 anchor
medoid_anchor = anchor-level shape vector 标准化后距离 cluster median vector 最近的 anchor
```

Primary taxonomy 使用：

```text
primary_representative = medoid_anchor
```

原因：`earliest_anchor` 容易把上涨前漫长等待期算入 path shape；`shortest_duration_anchor` 容易偏向突破尾端；`medoid_anchor` 更接近该 cluster 内 anchor-defined opportunity paths 的中心形态。

Medoid selection pipeline 冻结为：

```text
1. 对每个 path_winner anchor 计算 anchor_path_shape_feature_panel：
   anchor_segment_start_pos = entry_pos
   anchor_segment_end_pos = episode_threshold_pos
   anchor_segment_price_basis = qfq close

2. 使用 medoid_feature_set：
   path_efficiency
   max_drawdown_before_hit_abs
   underwater_days_share
   directional_entropy_5state
   trend_line_r2
   top1_positive_gain_share
   top3_positive_gain_share
   log_time_to_threshold

3. medoid_feature_scaler 只在 selected_threshold_id 的 train、single-split、
   non-cross-calendar-span anchor paths 上拟合：
   center = train median
   scale = train IQR
   if IQR = 0 then scale = 1
   missing values are imputed to train median and missing flags are retained

4. 对每个 cluster 内 anchor，计算 standardized feature vector。
   cluster_median_vector = median standardized vector over anchors in the cluster。
   medoid_distance = Euclidean distance to cluster_median_vector。

5. tie breaker:
   medoid_distance asc
   time_to_threshold_sessions asc
   entry_pos asc
   row_id asc as string
```

`path_shape_taxonomy_rule_audit.csv` 必须记录 medoid feature scaler 的 center、scale、missing-imputation policy 与 train fit population。

#### 6.3.1 Execution DAG freeze

15B 的 path-shape taxonomy 必须按以下 DAG 执行，禁止调换顺序：

```text
1. Build source anchor label panel
   input = 15A row-level cache or raw rebuild
   output = path_defined_label_adapter_audit.csv + path_defined_label_rebuild_audit.csv

2. Build winner intervals and global episode clusters
   input = path_winner anchors only
   output = winner_episode_cluster_membership_audit.csv + split_overlap_audit.csv

3. Compute anchor-level path shape metrics for every path_winner anchor
   input = qfq close path from anchor.entry_pos through anchor.episode_threshold_pos
   output = anchor_path_shape_feature_panel.parquet

4. Fit medoid_feature_scaler on anchor-level train eligible paths
   fit population = selected_threshold_id, cluster_split_bucket = train,
                    no member/calendar split overlap, valid anchor segment
   output = medoid scaler rows in path_shape_taxonomy_rule_audit.csv

5. Select earliest / shortest / medoid representative anchors for each cluster
   input = anchor-level metrics + medoid_feature_scaler
   output = representative_anchor_audit.csv

6. Compute episode-level path shape metrics from medoid representatives
   input = medoid anchor segment
   output = episode_path_shape_feature_panel.parquet

7. Fit taxonomy quantiles on episode-level medoid train eligible clusters
   fit population = taxonomy_fit_population in §9
   output = taxonomy quantile rows in path_shape_taxonomy_rule_audit.csv

8. Assign path type with frozen taxonomy rules
   apply the same taxonomy rule to:
     a. episode-level medoid metrics
     b. anchor-level metrics
   output = taxonomy_assignment_panel.parquet

9. Compute cluster internal path-type heterogeneity
   input = anchor-level assignments under the same frozen taxonomy rules
   output = representative_anchor_audit.csv + taxonomy_stability_gate.csv
```

This DAG resolves the dependency order:

```text
anchor metrics -> medoid selection -> episode metrics -> taxonomy quantiles
-> episode assignment + anchor assignment -> cluster internal heterogeneity
```

Anchor-level path type is therefore a **diagnostic reassignment using frozen episode-level taxonomy rules**. It is not used to fit taxonomy quantiles and must never alter the medoid-selected episode-level primary denominator.

同时必须输出代表选择审计：

```text
representative_anchor_audit.csv
```

记录 earliest / shortest / medoid 三种代表的 path metrics 差异。如果三者 taxonomy 不一致，cluster 标记：

```text
representative_taxonomy_disagreement = true
```

并进入 stability readout。

除了上述三代表分歧外，`representative_anchor_audit.csv` 还必须记录整个 cluster 内**全体**
path_winner anchor 的 path type 分歧度，避免 medoid 单一代表掩盖 cluster 内异质性：

```text
cluster_anchor_n = cluster 内 path_winner anchor 数
cluster_distinct_path_type_n = cluster 内 anchor-level path type 的不同取值数
cluster_internal_path_type_entropy =
  -sum(p_type * ln(p_type)) / ln(max(cluster_distinct_path_type_n, 2))
cluster_dominant_path_type_share = cluster 内占比最高的 anchor-level path type 的占比
```

`cluster_internal_path_type_entropy` 与 `cluster_dominant_path_type_share` 的分布必须进入
§12.3 stability readout。若大量 cluster 内部 path type 高度分歧（dominant share 低、internal entropy 高），
说明 "用 medoid 代表整段 episode" 本身不稳，报告必须在结论中明确这一限制。该 readout 只报告、不自动 hard block。

### 6.4 Split leakage guard

由于 long winner interval 可能跨越日历 split 边界，15B 必须输出：

```text
split_overlap_audit.csv
```

字段至少包括：

```text
instrument
threshold_id
episode_cluster_id
cluster_split_bucket
cluster_member_split_bucket_set
cluster_calendar_span_split_bucket_set
cluster_start_date
cluster_end_date
touches_multiple_split_buckets
touches_multiple_calendar_split_buckets
train_validation_boundary_overlap
validation_robustness_boundary_overlap
split_overlap_status
```

定义：

```text
cluster_member_split_bucket_set = split buckets of member anchor rows
cluster_calendar_span_split_bucket_set = split buckets touched by calendar dates from cluster_start_date through cluster_end_date
touches_multiple_split_buckets = len(cluster_member_split_bucket_set) > 1
touches_multiple_calendar_split_buckets = len(cluster_calendar_span_split_bucket_set) > 1

cluster_split_bucket =
  train / validation / robustness if both split sets contain exactly that same single bucket
  cross_split otherwise
```

Train-only taxonomy thresholds 只能用 `cluster_split_bucket = train` 且 `touches_multiple_split_buckets = false` 且 `touches_multiple_calendar_split_buckets = false` 的 clusters 拟合。跨 split clusters 可以保留 readout，但不得影响 rule fitting。

## 7. Path Segment 与价格口径

### 7.1 Hit detection

Threshold hit 继承 15A：

```text
hit_detection_price_basis = qfq high
first_threshold_hit_pos = first pos where high_return_from_entry >= threshold_return
```

### 7.2 Shape descriptor price basis

Path shape descriptors 使用。下列公式中的 `segment_start_pos` / `segment_end_pos` 指当前正在计算的 path segment；对 anchor-level panel 使用 anchor segment，对 episode-level panel 使用 medoid episode segment：

```text
shape_price_basis = qfq close
anchor_metric_segment_start_pos = anchor.entry_pos
anchor_metric_segment_end_pos = anchor.first_threshold_hit_pos
episode_metric_segment_start_pos = medoid_anchor.entry_pos
episode_metric_segment_end_pos = medoid_anchor.first_threshold_hit_pos
segment_inclusive = true
segment_sessions = segment_end_pos - segment_start_pos + 1
return_observation_n = max(segment_sessions - 1, 0)
```

Label hit detection 使用 next-open entry price 与 qfq high；path shape 描述使用 qfq close path。二者不得互相替代：

```text
label_return_reference_price = entry_price
shape_close_start = qfq close at segment_start_pos
shape_close_end = qfq close at segment_end_pos
entry_gap_return = shape_close_start / entry_price - 1
net_log_return = log(shape_close_end / shape_close_start)
```

如果 high-based hit 当日从未 close above threshold，需要标记：

```text
wick_hit_only = true
close_return_at_hit < threshold_return
close_return_at_hit = qfq close at first_threshold_hit_pos / entry_price - 1
```

`wick_hit_only` 不自动排除，但必须进入 taxonomy rule audit 与 readout。

`wick_hit_only` 路径有一个特定污染风险：hit 用 qfq high，而 path shape 用 qfq close；当 high 触及阈值
但当日 close 远低于阈值时，`net_log_return = log(close_end / close_start)` 会被人为压低，导致
`path_efficiency` 被压向 0，把一段其实涨势不错（仅收盘回落）的路径误判为 low_efficiency → choppy。
因此必须强制输出：

```text
wick_hit_only_share_by_path_type   写入 path_shape_taxonomy_readout.csv
wick_hit_only_share_in_choppy_reversal_winner
wick_hit_only_share_in_low_efficiency_predicate_hits
```

报告必须显式确认 `wick_hit_only` 路径没有系统性集中污染 `choppy_reversal_winner` / low_efficiency 判定。
若 `wick_hit_only_share_in_choppy_reversal_winner` 明显高于其在全体 winner 中的占比，报告必须把
`choppy_reversal_winner` 的占比结论降级为存疑，并建议后续将 wick_hit 路径单独隔离重测。

### 7.3 Minimum segment length

Primary path shape metrics 要求：

```text
min_segment_sessions_for_shape = 10
```

低于该长度的 winner clusters 标记为：

```text
path_shape_quality = too_short_for_stable_shape
```

并只能进入 `jump_repricing_winner` 或 `unclassified_short_path`，不得进入 `smooth_trend_winner` / `stair_step_winner` / `slow_grind_winner`。

## 8. Path Shape Features

15B 至少计算以下 feature families。所有公式必须写入：

```text
path_shape_feature_definition_audit.csv
```

每个 feature 必须在 `path_shape_feature_definition_audit.csv` 中标记其角色：

```text
feature_role in {
  taxonomy_rule_input,        # 进入 §9 predicate 的特征
  medoid_input,               # 进入 §6.3 medoid_feature_set 的特征
  descriptive_readout_only    # 只进 path_shape_metric_distribution_readout.csv，不影响分类
}
```

以下特征明确为 `descriptive_readout_only`，仅进入 distribution readout，不得进入任何 taxonomy
predicate、也不进入 medoid_feature_set：

```text
entry_underwater_days_share
pullback_10pct_count
median_recovery_sessions
positive_day_share
ma20_hold_share
large_up_day_share
directional_entropy_5state_realized
realized_volatility_to_hit
```

一个特征可同时是 `taxonomy_rule_input` 与 `medoid_input`；但 `descriptive_readout_only` 与前两者互斥。
`feature_role` 与 §9 predicate 实际引用必须一致，否则 `train_rule_fit_status` fail closed。

### 8.1 Efficiency

```text
daily_log_return_t = log(close_t / close_{t-1})
net_log_return = log(close_end / close_start)
total_variation = sum(abs(daily_log_return_t))
path_efficiency = abs(net_log_return) / total_variation
```

若 `total_variation = 0`，`path_efficiency = NaN`，并标记 `zero_variation_path = true`。

### 8.2 Drawdown and underwater path

```text
max_drawdown_before_hit = min(close_t / running_max_close_t - 1)
underwater_days_share = mean(close_t < running_max_close_t)
entry_underwater_days_share = mean(close_t < close_start)
```

必须同时输出 drawdown depth 与 drawdown persistence，避免只看最大回撤。

### 8.3 Pullback structure

```text
pullback_5pct_count = number of running-peak-to-trough drawdowns <= -5%
pullback_10pct_count = number of running-peak-to-trough drawdowns <= -10%
median_recovery_sessions = median sessions from pullback trough back to prior running peak
```

Pullback 事件必须按 running peak / trough state machine 计算，不得用 rolling-window drawdown 简化替代。

### 8.4 Entropy

Primary entropy 使用 entry-vol-scaled daily return states：

```text
z_t = daily_log_return_t / entry_volatility_20d

state_t =
  large_down if z_t <= -1.0
  small_down if -1.0 < z_t < -0.25
  flat       if -0.25 <= z_t <= 0.25
  small_up   if 0.25 < z_t < 1.0
  large_up   if z_t >= 1.0

directional_entropy_5state = -sum(p_state * ln(p_state)) / ln(5)
```

若 `entry_volatility_20d` 缺失或为 0，runner 必须使用 fallback：

```text
fallback_volatility = realized std of daily_log_return_t over segment
entropy_volatility_source = realized_segment_fallback
```

并在 audit 中标记。若 fallback 也不可用，entropy 为 NaN，不能 fail open。

Primary entropy 用 entry 时点的 `entry_volatility_20d` 缩放整段日收益。对慢牛 / 长路径，entry 时波动率
与路径后期波动率可能差异很大，导致 z_t 分箱在路径后段失真。为量化这一口径风险，必须额外计算一个
**诊断对照**（不替换 primary，不参与 taxonomy rule）：

```text
directional_entropy_5state_realized =
  与 directional_entropy_5state 同公式，但用整段 realized std 缩放：
  z_realized_t = daily_log_return_t / realized_volatility_to_hit
entropy_scaling_variant_corr =
  Spearman corr(directional_entropy_5state, directional_entropy_5state_realized)
```

`entropy_scaling_variant_corr` 必须进入 `entropy_incrementality_readout.csv`。若两者相关性低，
说明 entry-vol 缩放对长路径不稳健，报告必须明确 entropy 口径对长路径的局限。Primary taxonomy
仍只使用 `directional_entropy_5state`（entry-vol 缩放），realized 变体仅作 readout。

Entropy 的角色冻结为：

```text
entropy_role = path_shape_descriptor_not_standalone_label
```

15B 不得把低 entropy 或高 entropy 单独定义为 winner type。Entropy 必须与 efficiency、drawdown、gain concentration 同时使用。

### 8.5 Trend linearity

```text
trend_line_r2 = OLS R^2 of log(close_t) on session_index
positive_day_share = mean(daily_log_return_t > 0)
ma20_hold_share = mean(close_t >= trailing_ma20_close_t)
```

`ma20_hold_share` 可以使用 segment 前 20 个交易日的历史 close 来初始化；若历史不足，标记 missing，不得前向填充。

### 8.6 Gain concentration

```text
positive_gain_sum = sum(max(daily_log_return_t, 0))
top1_positive_gain_share = max(max(daily_log_return_t, 0)) / positive_gain_sum
top3_positive_gain_share = sum(top 3 max(daily_log_return_t, 0)) / positive_gain_sum
large_up_day_count = count(simple_return_t >= 0.095)
large_up_day_share = large_up_day_count / segment_sessions
```

这些字段用于区分 `smooth_trend_winner` 与 `jump_repricing_winner`。不得用大阳线数量直接替代完整 path shape。

### 8.7 Duration

```text
time_to_threshold_sessions
log_time_to_threshold = log1p(time_to_threshold_sessions)
```

Duration 只能作为辅助轴。15B 的 primary taxonomy 不得退化成 fast / slow 二分。

### 8.8 Realized volatility to hit

```text
realized_volatility_to_hit = sample std of daily_log_return_t over segment
realized_volatility_observation_n = return_observation_n
```

若 `return_observation_n < 2`，`realized_volatility_to_hit = NaN`，并标记 `insufficient_return_observation_for_realized_volatility = true`。

## 9. Train-Only Taxonomy Rule

15B 使用 deterministic rule taxonomy。所有阈值必须仅从 train split 的 eligible winner episode clusters 拟合：

```text
taxonomy_fit_population =
  threshold_id = selected_threshold_id
  cluster_split_bucket = train
  touches_multiple_split_buckets = false
  touches_multiple_calendar_split_buckets = false
  path_shape_quality != too_short_for_stable_shape
  primary_representative = medoid_anchor
```

§6.3 的 `medoid_feature_scaler` 与本节的 taxonomy quantile 是两个不同阶段：

```text
medoid_feature_scaler_fit_population = anchor-level train eligible paths before medoid selection
taxonomy_quantile_fit_population = episode-level medoid train eligible clusters after medoid selection
```

二者不要求 row count 相等，也不得强行相等。`path_shape_taxonomy_rule_audit.csv` 必须分别记录：

```text
medoid_scaler_fit_population_n
taxonomy_quantile_fit_population_n
medoid_scaler_fit_unit = anchor_path
taxonomy_quantile_fit_unit = winner_episode_cluster
taxonomy_fit_population_order_status = pass
```

若 quantile 先于 medoid selection 拟合，或 anchor-level assignments 反向影响 medoid-selected primary denominator，
`train_rule_fit_status` 必须 fail closed。

Train 拟合后，所有 quantile thresholds 写入：

```text
path_shape_taxonomy_rule_audit.csv
```

Validation / robustness 只能应用冻结规则，不得修改 rule、quantile 或 class precedence。

### 9.1 Required train quantiles

至少冻结以下 quantiles：

```text
q_efficiency_30 / 50 / 70
q_max_drawdown_abs_30 / 50 / 70
q_underwater_share_50 / 70
q_entropy_30 / 50 / 70
q_trend_r2_50 / 70
q_top1_gain_share_70 / 85
q_top3_gain_share_70 / 85
q_large_up_day_count_70
q_time_to_threshold_75
q_pullback_5pct_count_50 / 70
```

收紧 `high_gain_concentration` 后，`large_up_day_share` 不再进入任何 predicate，因此不冻结
`q_large_up_day_share_70`；`large_up_day_share` 降级为 `descriptive_readout_only`（见 §8）。
`time_to_threshold` 只有 `q_time_to_threshold_75` 被 `long_duration` 使用，故不冻结
`q_time_to_threshold_50`（其唯一引用方 `medium_or_long_duration` 已在 §9.3 移除）。

Drawdown quantile 必须按 absolute drawdown severity 处理，避免 `-0.30` 与 `-0.05` 的方向混淆。

`path_shape_taxonomy_rule_audit.csv` 必须对每个冻结 quantile 标记它是否被任一 predicate 实际引用
（`quantile_used_by_predicate = true/false`）。未被任何 predicate 使用的冻结 quantile 必须显式列出，
避免 over-specification 制造 "看起来很严谨但实际无用" 的假象。未使用 quantile 不导致 fail，仅 readout。

### 9.2 Primary path types

Primary taxonomy 至少包含以下 class：

```text
smooth_trend_winner
stair_step_winner
jump_repricing_winner
choppy_reversal_winner
slow_grind_winner
late_rescue_winner
unclassified_short_path
unclassified_mixed_path
```

### 9.3 Boolean predicate vocabulary

所有 high / medium / low 必须由 train-only quantiles 展开成布尔表达式。不得在代码里保留人工直觉词。

Missing policy 冻结为：

```text
hard_required_for_all =
  source_row_key
  threshold_id
  episode_cluster_id
  segment_start_pos
  segment_end_pos
  segment_sessions
  entry_price
  shape_close_start
  shape_close_end

class_specific_required_features =
  jump_repricing_winner:
    top1_positive_gain_share, top3_positive_gain_share, large_up_day_count
  unclassified_short_path:
    segment_sessions
  late_rescue_winner:
    time_to_threshold_sessions, max_drawdown_before_hit, underwater_days_share, path_efficiency
  smooth_trend_winner:
    path_efficiency, max_drawdown_before_hit, underwater_days_share,
    top1_positive_gain_share, top3_positive_gain_share, trend_line_r2, directional_entropy_5state
  slow_grind_winner:
    time_to_threshold_sessions, path_efficiency, max_drawdown_before_hit,
    underwater_days_share, top1_positive_gain_share, top3_positive_gain_share, trend_line_r2
  stair_step_winner:
    path_efficiency, pullback_5pct_count, max_drawdown_before_hit,
    underwater_days_share, top1_positive_gain_share, top3_positive_gain_share, trend_line_r2
  choppy_reversal_winner:
    path_efficiency, directional_entropy_5state, max_drawdown_before_hit,
    underwater_days_share, pullback_5pct_count
```

Rules:

```text
1. Missing any hard_required_for_all field => data_quality_blocked.
2. Missing a class-specific feature makes only that class predicate false.
3. too_short_path does not require entropy, trend_line_r2, realized_volatility_to_hit,
   pullback recovery, or any feature whose stable estimation requires a longer segment.
4. For too_short_path, jump_repricing_winner may still fire if gain concentration fields are available.
5. Missing class-specific fields must be recorded in path_type_missing_feature_flags.
```

```text
drawdown_abs = abs(max_drawdown_before_hit)

too_short_path =
  segment_sessions < min_segment_sessions_for_shape

high_efficiency =
  path_efficiency >= q_efficiency_70

medium_or_high_efficiency =
  path_efficiency >= q_efficiency_30

low_efficiency =
  path_efficiency <= q_efficiency_30

mild_drawdown =
  drawdown_abs <= q_max_drawdown_abs_30

severe_drawdown =
  drawdown_abs >= q_max_drawdown_abs_70

low_underwater =
  underwater_days_share <= q_underwater_share_50

high_underwater =
  underwater_days_share >= q_underwater_share_70

low_entropy =
  directional_entropy_5state <= q_entropy_30

not_high_entropy =
  directional_entropy_5state <= q_entropy_70

high_entropy =
  directional_entropy_5state >= q_entropy_70

high_trend_linearity =
  trend_line_r2 >= q_trend_r2_70

acceptable_trend_linearity =
  trend_line_r2 >= q_trend_r2_50

high_gain_concentration =
  top1_positive_gain_share >= q_top1_gain_share_85
  or top3_positive_gain_share >= q_top3_gain_share_85
  or (
       large_up_day_count >= max(2, q_large_up_day_count_70)
       and top3_positive_gain_share >= q_top3_gain_share_70
     )

low_or_medium_gain_concentration =
  top1_positive_gain_share <= q_top1_gain_share_70
  and top3_positive_gain_share <= q_top3_gain_share_70

smooth_overrides_jump =
  high_efficiency
  and mild_drawdown
  and high_trend_linearity
  and not_high_entropy

long_duration =
  time_to_threshold_sessions >= q_time_to_threshold_75

some_pullbacks =
  pullback_5pct_count >= q_pullback_5pct_count_50

many_pullbacks =
  pullback_5pct_count >= q_pullback_5pct_count_70

data_quality_blocked =
  any hard_required_for_all field is missing
  or path_shape_quality in {invalid_price_path, invalid_segment_bounds}
```

`q_max_drawdown_abs_*` 是对 `drawdown_abs` 的 train quantile，不是对负数 drawdown 原值直接取方向不明的分位数。

### 9.4 Deterministic class predicates

Primary taxonomy 必须用以下 predicates 和 precedence 复现。每个 predicate 命中状态都必须进入 `path_type_conflict_flags`，最终 class 由 precedence 决定。
若某个 predicate 的 class-specific required feature 缺失，该 predicate 视为 false，并在
`path_type_missing_feature_flags` 中记录；不得因此自动触发 `data_quality_blocked`，除非缺的是
`hard_required_for_all`。

```text
jump_repricing_winner if
  high_gain_concentration
  and not smooth_overrides_jump

unclassified_short_path if
  too_short_path
  and not (high_gain_concentration and not smooth_overrides_jump)

late_rescue_winner if
  long_duration
  and (severe_drawdown or high_underwater or low_efficiency)

smooth_trend_winner if
  high_efficiency
  and mild_drawdown
  and low_underwater
  and low_or_medium_gain_concentration
  and high_trend_linearity
  and not_high_entropy

slow_grind_winner if
  long_duration
  and medium_or_high_efficiency
  and not severe_drawdown
  and not high_underwater
  and low_or_medium_gain_concentration
  and acceptable_trend_linearity

stair_step_winner if
  medium_or_high_efficiency
  and some_pullbacks
  and not severe_drawdown
  and not high_underwater
  and low_or_medium_gain_concentration
  and acceptable_trend_linearity

choppy_reversal_winner if
  low_efficiency
  and high_entropy
  and (severe_drawdown or high_underwater or many_pullbacks)

unclassified_mixed_path if
  none of the above non-blocked predicates is selected by precedence
```

### 9.5 Rule precedence

Class precedence 冻结为：

```text
1. data_quality_blocked
2. jump_repricing_winner
3. unclassified_short_path
4. late_rescue_winner
5. smooth_trend_winner
6. slow_grind_winner
7. stair_step_winner
8. choppy_reversal_winner
9. unclassified_mixed_path
```

原因：

1. 数据质量先隔离，避免缺字段被默认归类。
2. jump repricing 优先，因为收益集中度会污染 efficiency / entropy，且短路径若明显由跳涨完成，应进入 jump 而不是 short unknown。
   但 A 股 10% 涨停结构会让一段健康强趋势天然包含若干大涨日，单纯计数会把平滑趋势误吸进 jump。
   因此 `high_gain_concentration` 的 large-up-day 分支必须同时满足 `top3_positive_gain_share >= q70`
   （前三日确实贡献了大部分涨幅）才成立，且引入 `smooth_overrides_jump` 闸门：
   当路径同时满足 high_efficiency + mild_drawdown + high_trend_linearity + not_high_entropy 时，
   即使集中度高也跳过 jump，交由后续 smooth_trend predicate 捕获。
   这避免系统性低估 smooth_trend_winner、夸大 jump_repricing_winner。
3. 极短但不 jump 的路径再隔离，避免短样本伪装成 smooth。
4. late rescue 优先于 slow grind，因为长时间但深回撤的路径不应被误判为健康慢牛。
5. smooth / slow / stair / choppy 再按健康度与趋势结构细分。

`smooth_overrides_jump` 的命中状态必须进入 `path_type_conflict_flags`，并在
`path_shape_taxonomy_readout.csv` 中单独报告被该闸门从 jump 改判为 smooth 的 episode_cluster_n，
便于审计该例外的影响规模。

所有 class assignment 必须输出：

```text
path_type_assignment_reason
path_type_conflict_flags
path_type_missing_feature_flags
```

## 10. Entropy Incrementality Diagnostic

15B 必须单独输出：

```text
entropy_incrementality_readout.csv
```

至少包含：

```text
feature_pair
spearman_corr_train
spearman_corr_validation
spearman_corr_robustness
redundancy_flag_abs_corr_ge_0p80
```

必须检查 entropy 与以下字段的相关性：

```text
time_to_threshold_sessions
path_efficiency
max_drawdown_before_hit_abs
underwater_days_share
top1_positive_gain_share
top3_positive_gain_share
trend_line_r2
realized_volatility_to_hit
```

还必须输出 no-entropy taxonomy ablation：

```text
taxonomy_without_entropy_assignment
taxonomy_with_entropy_assignment
assignment_changed_by_entropy
entropy_incremental_class_share_delta
```

如果 entropy 的主要作用只是复制 duration / drawdown / concentration，则 decision 必须标记：

```text
entropy_incrementality_status = redundant_readout_only
```

否则标记：

```text
entropy_incrementality_status = incremental_shape_descriptor
```

无论哪种状态，entropy 都不得单独授权 label deployment。

## 11. Required Outputs

### 11.1 Publishable tables

必须输出到：

```text
outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/
```

Required tables：

```text
input_artifact_audit.csv
upstream_lineage_audit.csv
price_path_completeness_audit.csv
path_defined_label_adapter_audit.csv
path_defined_label_rebuild_audit.csv
winner_episode_cluster_membership_audit.csv
split_overlap_audit.csv
representative_anchor_audit.csv
path_shape_feature_definition_audit.csv
path_shape_metric_distribution_readout.csv
path_shape_taxonomy_rule_audit.csv
path_shape_taxonomy_readout.csv
path_shape_by_split_readout.csv
path_shape_by_threshold_sensitivity_readout.csv
slow_fast_by_path_type_readout.csv
entropy_incrementality_readout.csv
taxonomy_without_entropy_ablation_readout.csv
taxonomy_stability_gate.csv
winner_path_shape_taxonomy_decision.csv
search_accounting_audit.csv
```

### 11.1.1 Minimum required table fields

以下新增 readout 必须进入 publishable tables，不能只写进 report 或 local cache。

`representative_anchor_audit.csv` 至少包含：

```text
threshold_id
episode_cluster_id
cluster_anchor_n
earliest_anchor_row_id
shortest_duration_anchor_row_id
medoid_anchor_row_id
earliest_anchor_path_type
shortest_duration_anchor_path_type
medoid_anchor_path_type
representative_taxonomy_disagreement
cluster_distinct_path_type_n
cluster_internal_path_type_entropy
cluster_dominant_path_type
cluster_dominant_path_type_share
```

`path_shape_taxonomy_readout.csv` 至少包含：

```text
split_bucket
threshold_id
path_type
episode_cluster_n
episode_cluster_share
winner_anchor_n
wick_hit_only_n
wick_hit_only_share
wick_hit_only_share_by_path_type
wick_hit_only_share_in_choppy_reversal_winner
wick_hit_only_share_in_low_efficiency_predicate_hits
smooth_overrides_jump_episode_cluster_n
smooth_overrides_jump_share
path_type_missing_feature_flag_n
```

`taxonomy_stability_gate.csv` 至少包含：

```text
js_divergence_train_validation_path_type_distribution
js_divergence_train_robustness_path_type_distribution
representative_taxonomy_disagreement_share
cluster_internal_path_type_entropy_median
cluster_internal_path_type_entropy_p75
cluster_dominant_path_type_share_median
cluster_dominant_path_type_share_p25
tradable_shape_share
stability_extreme_failure
taxonomy_stability_status
```

`search_accounting_audit.csv` 至少包含：

```text
startup_authorization_basis
manual_research_plan_override
selected_threshold_id
threshold_selection_source
taxonomy_fit_split
validation_usage
robustness_usage
taxonomy_rule_type
unsupervised_clustering_usage
entropy_usage
entry_search_authorized
signal_search_authorized
model_training_authorized
search_accounting_status
```

### 11.2 Local cache

Row-level panels 可以输出到：

```text
outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/
```

Allowed local cache：

```text
anchor_path_shape_feature_panel.parquet
winner_episode_cluster_panel.parquet
episode_path_shape_feature_panel.parquet
taxonomy_assignment_panel.parquet
```

Local cache 不能替代 publishable audit。所有 publishable tables 必须能解释 local cache 的 schema、row count、hash、lineage。

### 11.3 Report

必须输出：

```text
outputs/publishable/reports/winner_path_shape_taxonomy_diagnostic_report.md
```

Report 必须用中文写，至少包含：

1. 单行裁决；
2. 为什么 15B 插入在 separability 之前；
3. 15A `next_allowed_requirement = none` 下为何允许 15B label-form diagnostic 的 override 论证；
4. anchor-row winner 与 episode-cluster winner 的区别；
5. path shape feature 定义解释；
6. entropy 的作用与限制；
7. train-only taxonomy rule；
8. path type base rate 与跨 split 稳定性；
9. 哪些 path type 可作为后续 separability 候选；
10. 哪些 path type 只能作为 descriptive / readout-only；
11. 为什么本实验仍不授权 signal search、entry、model 或 label deployment。

## 12. Decision Gates

### 12.1 Hard fail gates

以下任一失败，decision 必须为：

```text
15B_blocked_input_or_lineage_failure
```

Hard fail conditions：

```text
input_artifact_gate != pass
upstream_lineage_gate != pass
price_path_completeness_gate != pass
path_defined_label_adapter_gate != pass
path_defined_label_rebuild_gate != pass
episode_cluster_gate != pass
train_rule_fit_gate != pass
search_accounting_gate != pass
```

Gate source 冻结为：

```text
input_artifact_gate              <- input_artifact_audit.csv.input_gate_status
upstream_lineage_gate            <- upstream_lineage_audit.csv.lineage_status
price_path_completeness_gate     <- price_path_completeness_audit.csv.price_path_status
path_defined_label_adapter_gate  <- path_defined_label_adapter_audit.csv.adapter_status
path_defined_label_rebuild_gate  <- path_defined_label_rebuild_audit.csv.rebuild_status
episode_cluster_gate             <- winner_episode_cluster_membership_audit.csv.episode_cluster_status
train_rule_fit_gate              <- path_shape_taxonomy_rule_audit.csv.train_rule_fit_status
search_accounting_gate           <- search_accounting_audit.csv.search_accounting_status
```

若某个 audit 表为空、缺少 status 字段、或 status 字段不在 allowlist 中，相关 gate 必须 fail closed。

### 12.2 Taxonomy support gates

若 hard fail gates 全部通过，则评估：

```text
eligible_train_episode_cluster_n >= 200
material_path_type_n >= 3
largest_path_type_share_train <= 0.75
unclassified_share_train <= 0.35
representative_taxonomy_disagreement_share <= 0.35
validation_material_path_type_n >= 2
robustness_material_path_type_n >= 2
```

`material_path_type_n` 定义：

```text
path type share >= 0.05
and path type episode_cluster_n >= 50 in train
```

### 12.3 Stability readout

必须输出但不自动 hard block：

```text
js_divergence_train_validation_path_type_distribution
js_divergence_train_robustness_path_type_distribution
entropy_incrementality_status
slow_fast_path_type_composition_delta
threshold_sensitivity_path_type_rank_stability
tradable_shape_share
```

若 stability 极差，decision 可降级为：

```text
15B_path_shape_taxonomy_promising_but_unstable
```

Stability 极差定义为：

```text
js_divergence_train_validation_path_type_distribution > 0.30
or js_divergence_train_robustness_path_type_distribution > 0.30
or representative_taxonomy_disagreement_share > 0.50
```

`tradable_shape_share` 定义为可持有捕获型形态在 train eligible episode cluster 中的占比：

```text
tradable_shape_share =
  (smooth_trend_winner + slow_grind_winner + stair_step_winner) episode_cluster_n
  / eligible_train_episode_cluster_n
```

该字段用于区分两种 "taxonomy 可分" 的局面：一种是确实分出了可交易的顺畅形态；另一种是
taxonomy 虽稳定，但绝大多数 winner 落在 `choppy_reversal_winner` / `late_rescue_winner` /
`jump_repricing_winner` 等难以持有捕获的形态，可交易的顺畅 winner 极稀疏。后一种局面即使技术上
进入 `supported_for_label_revision`，报告也必须在结论中明确指出 tradable shape 稀疏，提醒 15C
不应高估顺畅 winner 的可用样本量。`tradable_shape_share` 只报告、不改变 decision 枚举。

## 13. Decision Map

最终裁决只能取以下枚举之一：

```text
15B_path_shape_taxonomy_supported_for_label_revision
15B_path_shape_taxonomy_promising_but_unstable
15B_path_shape_taxonomy_inconclusive_too_sparse
15B_no_stable_path_shape_taxonomy
15B_blocked_input_or_lineage_failure
```

Decision map：

```text
if any hard fail:
  decision_state = 15B_blocked_input_or_lineage_failure
  next_allowed_requirement = none

elif eligible_train_episode_cluster_n < 200:
  decision_state = 15B_path_shape_taxonomy_inconclusive_too_sparse
  next_allowed_requirement = none

elif material_path_type_n < 3 or largest_path_type_share_train > 0.75 or unclassified_share_train > 0.35:
  decision_state = 15B_no_stable_path_shape_taxonomy
  next_allowed_requirement = none

elif stability_extreme_failure:
  decision_state = 15B_path_shape_taxonomy_promising_but_unstable
  next_allowed_requirement = none

else:
  decision_state = 15B_path_shape_taxonomy_supported_for_label_revision
  next_allowed_requirement = requirement_15c_path_shape_label_separability_diagnostic.md
```

Regardless of decision:

```text
label_deployment_authorized = False
signal_search_authorized = False
model_training_authorized = False
entry_policy_authorized = False
```

## 14. Search Accounting

15B 必须输出 `search_accounting_audit.csv`，冻结：

```text
startup_authorization_basis = 15A_material_censoring_finding_not_15A_morphology_verdict
manual_research_plan_override = true
selected_threshold_id = up50pct
threshold_selection_source = inherited_from_15A_lowest_pre_registered_material_censoring_threshold
taxonomy_fit_split = train
validation_usage = readout_only
robustness_usage = readout_only
taxonomy_rule_type = deterministic_train_quantile_rule
unsupervised_clustering_usage = prohibited_for_primary_decision
entropy_usage = descriptor_not_standalone_label
entry_search_authorized = false
signal_search_authorized = false
model_training_authorized = false
search_accounting_status = pass iff all authorization/search-accounting fields match this frozen block; fail otherwise
```

如果 runner 增加任何 unsupervised clustering，如 k-means / hierarchical clustering，只能作为 appendix readout，并必须标记：

```text
unsupervised_result_role = exploratory_readout_not_primary_decision
```

不得用 unsupervised result 选择 primary taxonomy。

## 15. Tests

必须至少覆盖以下测试：

```text
test_transitive_interval_merge_not_greedy_adjacent_only
test_global_cluster_not_split_local_cluster
test_15a_path_defined_label_adapter_maps_episode_threshold_pos
test_censored_rows_excluded_from_primary_taxonomy
test_execution_dag_assigns_anchor_types_only_after_episode_quantile_fit
test_train_only_quantiles_do_not_use_validation_or_robustness
test_path_efficiency_handles_zero_total_variation_fail_closed
test_entropy_5state_formula_and_zero_vol_fallback
test_short_path_missing_entropy_does_not_data_quality_block
test_jump_repricing_precedence_over_smooth_trend
test_smooth_path_with_few_limit_up_days_not_misclassified_as_jump
test_large_up_day_count_alone_without_top3_concentration_does_not_trigger_jump
test_smooth_overrides_jump_routes_high_efficiency_path_to_smooth_trend
test_short_jump_path_classified_as_jump_not_short_unknown
test_late_rescue_precedence_over_slow_grind
test_short_path_cannot_be_smooth_trend
test_representative_anchor_medoid_is_deterministic
test_split_overlap_clusters_excluded_from_rule_fit
test_hard_fail_gate_sources_exist_and_fail_closed_when_missing
test_search_accounting_records_startup_authorization_override
test_decision_map_never_authorizes_signal_or_label_deployment
```

Synthetic paths must include at least:

```text
smooth monotonic up path
smooth up path containing a few limit-up days but low top3 gain concentration (must stay smooth_trend)
stair-step up path with recoverable pullbacks
jump-dominated path (single/few days dominate total gain, high top3 concentration)
choppy high-entropy path
late rescue path with deep drawdown before hit
wick-hit-only path where high touches threshold but close stays well below
censored non-hit path
```

## 16. Implementation Notes

1. 所有 percentage return 字段必须明确 simple return 还是 log return。
2. 所有 entropy 字段必须明确状态划分、归一化底数、volatility source。
3. 所有 train quantile thresholds 必须写入 publishable audit，不能只保存在内存或 local cache。
4. 所有 class assignment 必须可由 `path_shape_taxonomy_rule_audit.csv` 与 feature panel 复现。
5. Report 中不得把 `winner_episode_cluster_n` 与 `winner_anchor_row_n` 混用。
6. Report 中不得把 entropy 解释为“上涨顺畅度”的唯一指标；顺畅度必须同时参考 efficiency、drawdown、trend linearity、gain concentration。
7. 若 taxonomy 不能稳定分出 path type，结论必须明确承认：当前 path-defined winner 仍不适合作为后续预测标签。
8. `high_gain_concentration` 的 large-up-day 分支必须与 `top3_positive_gain_share >= q70` 联合判定，
   且 `smooth_overrides_jump` 闸门必须实现，避免 A 股涨停结构把平滑趋势误判为 jump。
9. hit detection 用 qfq high、path shape 用 qfq close 的口径差异必须在 wick_hit_only 路径上单独审计，
   不得让 close 回落人为压低的 path_efficiency 系统性污染 choppy_reversal_winner 判定。
10. `tradable_shape_share` 必须报告；taxonomy 可分但顺畅形态稀疏时，结论不得暗示顺畅 winner 样本充足。

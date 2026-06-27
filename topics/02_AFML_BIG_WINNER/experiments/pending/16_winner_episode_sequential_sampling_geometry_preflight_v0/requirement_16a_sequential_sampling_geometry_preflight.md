# 需求：16A Winner Episode Sequential Sampling Geometry Preflight

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0
SOURCE_EP15_ROOT = TOPIC_ROOT/experiments/pending/15_path_defined_winner_episode_label_v0
SOURCE_EP14_ROOT = TOPIC_ROOT/experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0
SOURCE_EP13_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 以 `SOURCE_EP15_ROOT/`、`SOURCE_EP14_ROOT/`、`SOURCE_EP13_ROOT/` 表达的路径必须先解析到对应 episode root，再写入 `input_artifact_audit.csv`。
5. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
6. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、universe membership 不可证明、price path completeness 不可证明、episode clustering 不可证明、effective-sample provenance 不可证明、horizon grid provenance 不可证明时 fail closed。
7. 不得从报告文本、图像、人工讨论文本、聚合 readout 或未来标签反推出逐行 universe、episode membership、label、split 边界、entry 价格或 decision point。

## 1. 实验身份

```text
experiment_id = 16_winner_episode_sequential_sampling_geometry_preflight_v0
phase_id = 16A
run_id = 16A_sequential_sampling_geometry_preflight
status = draft_ready_for_review
expected_entrypoint = src/run_16a_sequential_sampling_geometry_preflight.py
expected_config = configs/config_16a_sequential_sampling_geometry_preflight.yaml
expected_test_file = tests/test_16a_sequential_sampling_geometry_preflight.py
source_plan = EXPERIMENT_ROOT/research_plan.md
upstream_requirement_15a = SOURCE_EP15_ROOT/requirement_15a_winner_episode_label_censoring_diagnostic.md
upstream_requirement_15b = SOURCE_EP15_ROOT/requirement_15b_winner_path_shape_taxonomy_diagnostic.md
upstream_requirement_15c = SOURCE_EP15_ROOT/requirement_15c_winner_entry_phase_and_mixture_taxonomy_diagnostic.md
upstream_requirement_15c2 = SOURCE_EP15_ROOT/requirement_15c2_winner_shape_membership_diagnostic.md
```

16A 是 Episode 16 的第一个 phase，也是从 Episode 15 的 label diagnostic 转向 **序贯 / 续航范式** 的桥接诊断。它**不**定义 entry、exit、holding、cost、收益或任何 alpha；它只解决一个被 Episode 15 反复暴露、但从未被独立验证的前置问题：

```text
序贯范式应该用什么统计单元、什么短窗 horizon、什么 cluster 去重，
才能得到不被高估的有效独立样本几何？
```

16A 不得产生任何交易、仓位、entry、exit、holding、cost model、模型、separability 或 label 部署授权。即使 16A 给出干净的采样几何，也只能授权后续新建：

```text
requirement_16b_sequential_continuation_label_design_diagnostic.md
```

## 2. 背景判断：为什么必须先做采样几何，而不是直接做序贯标签

### 2.1 Episode 15 的累积证据

15A→15C2 系统性地排除了两条路，并指向序贯范式：

```text
15A: fixed-120d label 对慢速 path-defined winner 存在 material right-censoring（真实）。
15B: 用整段 winner_episode_cluster 硬分类 path shape -> 统计单元太粗，
     representative disagreement = 0.7320。
15C: 把 cluster 按 entry-phase 切分 -> 只有 outcome-relative（事后位置）通过 real-over-random，
     PIT-observable phase 三个 split 都没过；coverage 不足。
15C2: 用 soft membership 放弃硬分类 -> 形态是连续谱，且 cluster-blocked baseline 否定 sharpness：
     winner 形态不独立于 episode cluster 的重复采样结构。
```

三个收敛结论：

```text
1. winner 形态不是固有离散类别，而是 "entry position within realized episode" 的连续函数。
2. entry position 在 t0 不可知，因此 "t0 给整段路径贴形态标签" 是错误的提法。
3. anchor 数严重高估了有效独立样本量（15C2 episode_cluster_blocked_shuffle 的
   random sharp share 0.1566 高于真实 0.1479，sharpness 不独立于 cluster 重复）。
```

### 2.2 序贯范式的提法（仅作背景，本实验不实现）

序贯 / 续航范式的设想（来自 research_plan 15E）：

```text
t0 不预测终局形态，只在持有过程中一段一段地判断 "下一小段是否值得继续参与"，
用短 horizon survival / continuation label 链式叠加，让市场用后续 path 持续淘汰输家。
```

16A 不实现这个范式。16A 只回答：如果将来要这样做，**采样几何的真相是什么**——否则序贯实验会重蹈 anchor 高估样本量的覆辙。

### 2.3 16A 的唯一使命

```text
钉死三件事，全部纯诊断、不碰收益：
1. 有效独立样本几何：anchor 数 vs episode cluster 数 vs 时间去重后的独立 step 数的真实比例；
2. 短窗 horizon 网格：在 winner episode 内部，多长的 forward window 才是 "下一小段" 的合理候选；
3. cluster 去重 / 重叠会计：序贯 step 之间的时间重叠程度，以及它对有效样本的折减。
```

## 3. 相对 15C2 `next_allowed_requirement = none` 的重新授权论证

15C2 输出 `next_allowed_requirement = none`，且明确 winner 形态不是可部署离散 taxonomy。16A 的启动依据必须显式论证：

```text
1. 15C2 否定的是 "winner 形态作为独立离散 taxonomy / t0-predictable label"，
   它没有否定 "序贯范式所需的采样几何"。15C2 反而正向证明了
   "有效样本被 cluster 重复结构主导"，这恰是 16A 必须量化的对象。

2. 16A 不复活 15B/15C/15C2 的硬分类、entry-phase t0 feature、soft taxonomy；
   它只在 sampling-geometry 层把 "anchor 当独立样本" 这个隐含假设拿出来证伪或量化。

3. 16A 不实现序贯 entry/exit/收益；它是序贯范式的前置 sampling preflight，
   类似 14A 之于 sparse event utility：先证明采样地基，再谈下游。

4. 16A 的启动依据 = Episode 15 累积证实的 "anchor 不是独立样本单元 + 形态是 entry-position 函数"，
   而不是任何已被否定的形态分类或 t0 可预测性。
```

该论证必须在 16A report 复述，并在 `search_accounting_audit.csv` 以
`startup_authorization_basis = ep15_effective_sample_and_position_dependence_not_shape_taxonomy` 记录。

## 4. 核心问题

16A 回答以下问题：

```text
Q1. 在 selected_threshold_id = up50pct 下，winner 的 anchor 数、winner_episode_cluster 数、
    以及按时间去重后的独立 step 数，三者真实比例是多少？anchor 高估了多少倍有效样本？

Q2. 在 winner episode 内部，forward 短窗 horizon（候选网格 {5, 8, 13, 15, 20} sessions）
    下，连续 step 之间的 forward-window 时间重叠程度如何？哪个 horizon 在
    "覆盖率" 与 "step 间重叠折减" 之间是合理候选？

Q3. 用 episode-cluster-blocked 与 time-block（非重叠 step）两种去重方案，
    有效独立样本数（effective sample size）相对 anchor 数折减多少？
    这个折减在 train / validation / robustness 上是否稳定？

Q4. 三档阈值 {up50, up100, up150} 下，采样几何如何变化？高阈值 episode 更长，
    是否意味着 step 数更多但 step 间重叠更严重？

Q5. 序贯范式可用的 sampling 单元与 horizon 候选是什么？哪些只能作为 readout，不能作为 16B 的采样地基？
```

必须输出一个单一裁决：

```text
decision_state
```

## 5. Scope Boundary

16A 允许做：

```text
1. 复用 15A/15B/15C 的 winner episode cluster lineage、split boundary、path-defined label、
   cluster interval（cluster_start_pos / cluster_end_pos）；
2. 统计 anchor 数 vs episode cluster 数 vs 时间去重 step 数的比例；
3. 在 winner episode interval 内构造非重叠 / 重叠 forward 短窗 step，量化 step 间时间重叠；
4. 计算 effective sample size（基于 step 间重叠的折减估计）；
5. 按 split、threshold 输出采样几何 readout；
6. 输出确定性 next-research decision map。
```

16A 明确不是：

```text
sequential label 定义
continuation / survival label 计算
forward return / 收益 / cost 计算
entry / exit / holding policy
signal search
t0 feature search
separability test
model training
portfolio backtest
label deployment authorization
```

16A 可以使用 winner episode interval 的时间结构（含未来 cluster interval）来量化采样几何，因为这是 sampling preflight；但**不得**计算任何 forward return / 收益，也不得把任何 step 升级为可交易 entry。

## 6. 继承边界

### 6.1 允许继承

16A 继承 Episode 15 的以下定义：

```text
anchor_record_unit = instrument x reference_date
label_record_unit = instrument x reference_date x threshold_id
selected_threshold_id = up50pct
threshold_sensitivity_grid = {up50pct, up100pct, up150pct}
split boundary from 12A7g / 13A / 14A
censored rows are never confirmed negatives
winner_episode_cluster 定义与 transitive overlap clustering（继承 15B §6.2）
cluster interval 字段 cluster_start_pos / cluster_end_pos（继承 15B membership audit）
eligible / cross_split 隔离纪律（继承 15C §7.1）
```

16A 必须读取以下上游 artifacts：

```text
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/winner_episode_cluster_membership_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/split_overlap_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15A_winner_episode_label_censoring_diagnostic/price_path_completeness_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/price_path_completeness_audit.csv
SOURCE_EP15_ROOT/configs/config_15b_winner_path_shape_taxonomy_diagnostic.yaml
SOURCE_EP15_ROOT/outputs/publishable/tables/15C2_winner_soft_shape_membership_diagnostic/winner_soft_shape_membership_decision.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15C2_winner_soft_shape_membership_diagnostic/membership_vs_random_baseline_readout.csv
```

15A / 15B 的 `price_path_completeness_audit.csv` 必须作为 publishable lineage 输入进入
`input_artifact_audit.csv`。16A 不得只因为 15B membership audit 中存在 `entry_pos` /
`cluster_start_pos` / `cluster_end_pos` 就默许 price path 完整；若任一 price path audit 缺失、
`price_path_status` 不在 allowlist，或无法证明 qfq trading session pos 与上游一致，
`price_path_completeness_gate` fail closed。

`price_path_status` allowlist = {pass}。

16A 可以使用以下 local cache 作为加速输入；local cache 不能绕过 publishable audit：

```text
SOURCE_EP15_ROOT/outputs/local_cache/15A_winner_episode_label_censoring_diagnostic/path_defined_label_panel.parquet
SOURCE_EP15_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/winner_episode_cluster_panel.parquet
```

如果 winner episode cluster cache 不存在或 schema 不匹配，16A 只允许重建 **15B cluster interval**，
不允许重建 15A path-defined label。重建输入必须是
`SOURCE_EP15_ROOT/outputs/local_cache/15A_winner_episode_label_censoring_diagnostic/path_defined_label_panel.parquet`；
若该 path-defined label panel 不存在、schema 不匹配或不能证明来自 15A publishable lineage，
`cluster_interval_rebuild_gate` fail closed。

重建规则必须冻结为 15B §6.2：

```text
rebuild_population =
  path_winner == true
  and is_censored == false

rebuild_group_key = (instrument, threshold_id)
rebuild_interval = [entry_pos, episode_threshold_pos]
interval_i overlaps interval_j iff
  interval_i.start_pos <= interval_j.end_pos
  and interval_j.start_pos <= interval_i.end_pos
cluster = connected component under transitive interval overlap graph
cluster_id = threshold_id + "::" + instrument + "::" + zero_padded_cluster_ordinal_by_cluster_start_pos
```

15B config `config_15b_winner_path_shape_taxonomy_diagnostic.yaml` 必须作为 rebuild lineage 输入，
用于冻结 upstream cache path、selected threshold 与 threshold sensitivity grid；transitive overlap rule
本身以 15B requirement §6.2 为 authority。若 winner episode cluster cache 可用且 schema 通过，
`cluster_interval_rebuild_audit.csv.rebuild_status = not_required_pass`。

### 6.1.1 Cluster interval adapter freeze

```text
source_row_key = (instrument, reference_date, row_id, threshold_id)

16A.episode_cluster_id        <- 15B.episode_cluster_id
16A.cluster_split_bucket      <- 15B.cluster_split_bucket
16A.cluster_start_pos         <- 15B.winner_episode_cluster_membership_audit.cluster_start_pos
16A.cluster_end_pos           <- 15B.winner_episode_cluster_membership_audit.cluster_end_pos
16A.anchor_entry_pos          <- 15B.entry_pos  # 不得使用 reference_pos / episode_start_pos / winner_interval_start_pos
16A.anchor_hit_pos            <- 15B.episode_threshold_pos
16A.time_to_threshold_sessions<- 15B.time_to_threshold_sessions
16A.path_winner               <- 15A.path_winner
16A.is_censored               <- 15A.is_censored
16A.available_forward_sessions<- 15B.available_forward_sessions
```

`path_winner` / `is_censored` 必须来自 15A / 15B membership audit，不得来自 taxonomy 形态表。16A 必须输出：

```text
cluster_interval_adapter_audit.csv
字段：source_row_key, adapter_source_path, adapter_required_columns_present,
      adapter_cluster_interval_present, adapter_row_count,
      adapter_duplicate_source_row_key_n, anchor_entry_pos_source_field,
      missing_entry_pos_n, missing_episode_threshold_pos_n,
      hit_pos_relation_mismatch_n, entry_pos_interval_violation_n,
      entry_hit_interval_violation_n, missing_available_forward_sessions_n,
      adapter_status
```

若 `cluster_start_pos`/`cluster_end_pos` 缺失、`source_row_key` 非唯一、`episode_threshold_pos`
缺失、`episode_threshold_pos != entry_pos + time_to_threshold_sessions`，或 cluster interval 不满足
`cluster_start_pos <= anchor_entry_pos <= anchor_hit_pos <= cluster_end_pos`，
`cluster_interval_adapter_gate` fail closed。

16A 必须显式记录 `anchor_entry_pos_source_field = entry_pos`。若实现使用
`reference_pos`、`episode_start_pos` 或 `winner_interval_start_pos` 替代 `entry_pos`，
`cluster_interval_adapter_gate` fail closed。

`cluster_interval_rebuild_audit.csv` 至少包含：

```text
rebuild_trigger
rebuild_source_path
rebuild_source_sha256
rebuild_config_path
rebuild_config_sha256
rebuild_rule_authority = upstream_requirement_15b_section_6_2
rebuild_population_predicate
rebuild_group_key
rebuild_interval_start_field = entry_pos
rebuild_interval_end_field = episode_threshold_pos
rebuild_overlap_predicate
rebuild_connected_component_algorithm
rebuilt_episode_cluster_n
rebuilt_membership_row_n
rebuild_status
blocking_reason
```

### 6.2 不得继承为结论

16A 不得把以下上游结论直接当成 16A 结论：

```text
15C2.decision_state
15C.decision_state
15B.decision_state
任何形态 taxonomy / soft membership / entry-phase 结论
label_deployment_authorized
signal_search_authorized
separability_search_authorized
```

这些只能作为背景与 fail-closed guard。16A 必须基于采样几何自己产生裁决。

## 7. Primary Unit 与 Eligible Population

```text
primary_diagnostic_unit = sampling_geometry_step (见 §8)
secondary_unit = winner_episode_cluster
audit_only_unit = winner_anchor (用于证明 anchor 高估，不作为有效样本)
```

Eligible population 冻结（沿用 15C §7.1 纪律）：

```text
eligible_episode_cluster =
  threshold_id == selected_threshold_id（primary）或 threshold_sensitivity_grid（sensitivity）
  and cluster_split_bucket in {train, validation, robustness}
  and touches_multiple_split_buckets == false
  and touches_multiple_calendar_split_buckets == false
  and cluster_start_pos / cluster_end_pos 可证明
  and 至少包含一个 path_winner == true 且 is_censored == false 的 anchor

cross_split 或 split-boundary touching cluster 只进入 appendix readout，不进入 primary 几何统计。
若 split-overlap 字段缺失或不可证明，eligible gate fail closed。
```

## 8. Sampling Geometry 定义

### 8.1 Episode interval

每个 eligible episode cluster 的 sequential interval 冻结为：

```text
episode_interval = [cluster_start_pos, cluster_end_pos]（inclusive，单位 = qfq trading session pos）
episode_length_sessions = cluster_end_pos - cluster_start_pos + 1
```

每个 eligible cluster 的 interval 必须落在可观测 qfq session 范围内：

```text
cluster_start_pos >= 0
cluster_end_pos < qfq_row_n
for every eligible anchor in cluster:
  cluster_end_pos - anchor_entry_pos + 1 <= available_forward_sessions
```

这里的 `available_forward_sessions` 是从该 anchor 的 `entry_pos` 到 qfq 文件末尾的可用 session 数，
不得误写成 `cluster_end_pos - cluster_start_pos + 1 <= available_forward_sessions` 的逐 anchor
校验；后者只对 cluster earliest-entry anchor 近似成立。若上述可观测范围不可证明，
`price_path_completeness_gate` fail closed。

### 8.2 短窗 horizon 网格（预注册冻结）

```text
horizon_grid_sessions = {5, 8, 13, 15, 20}
primary_horizon_sessions = 20
```

对每个 horizon h，在 episode_interval 内构造两套 step：

```text
non_overlapping_step(h):
  从 cluster_start_pos 起，每 h 个 session 切一个非重叠 step，
  最后一段不足 h 的标记为 partial_tail_step。
  step_n_nonoverlap(h) = ceil(episode_length_sessions / h)
  full_horizon_nonoverlap_step_n(h) = floor(episode_length_sessions / h)
  partial_tail_step_n(h) = 1 if episode_length_sessions % h != 0 else 0
  labelable_step_n_for_future_16B(h) = full_horizon_nonoverlap_step_n(h)

overlapping_step(h):
  以 stride = 1 session 滑动的 forward window，每个 step 覆盖 [p, p+h-1]，
  p 从 cluster_start_pos 到 cluster_end_pos - h + 1。
  step_n_overlap(h) = max(episode_length_sessions - h + 1, 0)
```

`non_overlapping_step` 是 16A 的 primary geometry readout；其中不足 h 的 partial tail 只能作为
coverage / tail readout，不得作为未来 16B 的完整 continuation labelable step。
`overlapping_step` 只用于量化 anchor 式重叠采样的折减。

### 8.3 Anchor-to-step 映射（量化 anchor 高估）

```text
对每个 episode cluster：
  anchor_n_in_cluster = path_winner & not censored anchors in cluster
  nonoverlap_step_n(h) = §8.2 定义
  labelable_step_n_for_future_16B(h) = §8.2 定义
  anchor_overcount_ratio(h) = anchor_n_in_cluster / max(nonoverlap_step_n(h), 1)
  anchor_to_labelable_step_ratio(h) = anchor_n_in_cluster / max(labelable_step_n_for_future_16B(h), 1)

聚合公式：
  anchor_overcount_ratio_anchor_weighted(h) =
    sum(anchor_n_in_cluster) / max(sum(nonoverlap_step_n(h)), 1)
  anchor_to_labelable_step_ratio_anchor_weighted(h) =
    sum(anchor_n_in_cluster) / max(sum(labelable_step_n_for_future_16B(h)), 1)
```

`anchor_overcount_ratio` 直接量化 "用 anchor 当独立样本" 相对 "非重叠短窗 step" 高估了多少倍。
`anchor_to_labelable_step_ratio` 单独服务于未来 16B 的完整 horizon labelability 判断。

### 8.4 Effective sample size

step 之间的 forward-window 时间重叠会折减有效样本。采用 AFML 风格的平均唯一度 (average uniqueness) 近似：

```text
对 overlapping_step(h) 集合：
  对每个 session pos p，concurrency(p) = 覆盖 p 的 step 数
  uniqueness(step_i) = mean over p in step_i of (1 / concurrency(p))
  average_uniqueness(h) = mean over steps of uniqueness(step_i)
  effective_sample_size_overlap(h) = step_n_overlap(h) * average_uniqueness(h)

对 non_overlapping_step(h)：
  average_uniqueness_nonoverlap = 1（按定义非重叠）
  effective_sample_size_nonoverlap(h) = full_horizon_nonoverlap_step_n(h)
  partial_tail_step 不进入 effective_sample_size_nonoverlap，只进入 coverage / tail readout

对 episode_cluster_blocked：
  effective_sample_size_episode_cluster_blocked = episode_cluster_n
  episode_cluster_to_anchor_ratio = episode_cluster_n / max(anchor_n, 1)
  time_block_to_anchor_ratio(h) = effective_sample_size_nonoverlap(h) / max(anchor_n, 1)
  effective_to_anchor_ratio(h) = time_block_to_anchor_ratio(h)
```

所有 concurrency / uniqueness 计算只在同一 instrument 内进行，跨 instrument 的 step 视为独立。
`effective_sample_size_episode_cluster_blocked` 不随 horizon 改变，但必须随每个 horizon 输出一行，
用于同表比较 episode-cluster-blocked 与 time-block 两种去重方案。

### 8.5 Episode cluster non-overlap audit（同一标的同一 threshold）

```text
15B 使用 transitive overlap clustering。理论上，同一 threshold_id、同一 instrument 下的
winner episode cluster interval 不应相互重叠。

16A 必须在 `episode_cluster_non_overlap_audit.csv` 中审计：
  same_threshold_instrument_overlap_pair_n
  max_same_threshold_instrument_concurrency
  overlap_example_episode_cluster_ids

若 same_threshold_instrument_overlap_pair_n > 0，说明 15B cluster interval lineage 不可用，
episode_cluster_non_overlap_gate fail closed。

不同 threshold_id 之间的 interval overlap 只作为 threshold sensitivity readout，不折减
selected_threshold_id primary effective sample。
```

## 9. Required Outputs

### 9.1 Publishable tables

输出到：

```text
outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/
```

Required tables：

```text
input_artifact_audit.csv
upstream_lineage_audit.csv
price_path_completeness_audit.csv
cluster_interval_adapter_audit.csv
cluster_interval_rebuild_audit.csv
sampling_unit_count_readout.csv
horizon_grid_step_readout.csv
anchor_overcount_readout.csv
effective_sample_size_readout.csv
episode_cluster_non_overlap_audit.csv
geometry_by_split_readout.csv
geometry_by_threshold_sensitivity_readout.csv
sampling_geometry_decision.csv
search_accounting_audit.csv
```

### 9.1.1 关键表最小字段

`price_path_completeness_audit.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
instrument
episode_cluster_id
anchor_n
qfq_row_n
cluster_start_pos
cluster_end_pos
available_forward_sessions_min
cluster_start_out_of_bounds_n
cluster_end_out_of_bounds_n
cluster_end_beyond_anchor_available_forward_sessions_n
price_path_status
blocking_reason
```

`sampling_unit_count_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
anchor_n
episode_cluster_n
nonoverlap_step_n_at_primary_horizon
full_horizon_nonoverlap_step_n_at_primary_horizon
partial_tail_step_n_at_primary_horizon
anchor_to_episode_ratio
anchor_to_nonoverlap_step_ratio_primary_horizon
anchor_to_full_horizon_step_ratio_primary_horizon
unit_count_status
```

`horizon_grid_step_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
horizon_sessions
episode_cluster_n
median_episode_length_sessions
step_n_nonoverlap
full_horizon_nonoverlap_step_n
partial_tail_step_n
labelable_step_n_for_future_16B
step_n_overlap
partial_tail_step_share
coverage_share
horizon_status
```

`anchor_overcount_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
horizon_sessions
anchor_overcount_ratio_median
anchor_overcount_ratio_p90
anchor_overcount_ratio_anchor_weighted
anchor_to_labelable_step_ratio_anchor_weighted
overcount_status
```

`effective_sample_size_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
horizon_sessions
episode_cluster_n
step_n_overlap
average_uniqueness
average_uniqueness_nonoverlap
full_horizon_nonoverlap_step_n
effective_sample_size_overlap
effective_sample_size_nonoverlap
effective_sample_size_episode_cluster_blocked
partial_tail_step_n
effective_to_anchor_ratio
episode_cluster_to_anchor_ratio
time_block_to_anchor_ratio
effective_sample_status
```

`episode_cluster_non_overlap_audit.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
instrument_n
episode_cluster_n
same_threshold_instrument_overlap_pair_n
max_same_threshold_instrument_concurrency
overlap_example_episode_cluster_ids
concurrency_status
```

`sampling_geometry_decision.csv` 至少包含：

```text
decision_state
next_allowed_requirement
selected_threshold_id
primary_horizon_sessions
anchor_n_train
episode_cluster_n_train
episode_cluster_n_validation
episode_cluster_n_robustness
nonoverlap_step_n_train_primary_horizon
full_horizon_nonoverlap_step_n_train_primary_horizon
partial_tail_step_n_train_primary_horizon
effective_sample_size_train_primary_horizon
effective_to_anchor_ratio_train
split_stability_evaluable
min_split_episode_cluster_n
stability_not_evaluable_reason
recommended_sampling_unit
recommended_horizon_candidate_set
geometry_stable_across_splits
label_deployment_authorized
signal_search_authorized
separability_search_authorized
```

`search_accounting_audit.csv` 至少包含：

```text
startup_authorization_basis
manual_research_plan_override
selected_threshold_id
threshold_selection_source
geometry_fit_split = none_descriptive_only
validation_usage
robustness_usage
horizon_grid_sessions
forward_return_computed = false
entry_search_authorized
signal_search_authorized
model_training_authorized
separability_search_authorized
sequential_label_authorized
search_accounting_status
```

### 9.2 Local cache

```text
outputs/local_cache/16A_sequential_sampling_geometry_preflight/
```

Allowed：

```text
episode_interval_panel.parquet
step_geometry_panel.parquet
```

Local cache 不能替代 publishable audit。

### 9.3 Report

输出到：

```text
outputs/publishable/reports/sequential_sampling_geometry_preflight_report.md
```

Report 必须用中文写，至少包含：

```text
1. 单行裁决；
2. 为什么 16A 在 15C2 none 后仍可启动（override 论证），以及它与 Episode 15 形态线的边界（只做采样几何，不做形态/收益）；
3. anchor 数 vs episode cluster 数 vs 非重叠 step 数的真实比例，anchor 高估倍数；
4. horizon grid 下的 step 数、覆盖率、partial tail；
5. effective sample size 与 average uniqueness，effective-to-anchor ratio；
6. 同 threshold / instrument 的 episode cluster non-overlap audit，以及是否触发 lineage fail-closed；
7. episode-cluster-blocked 与 time-block 两种去重方案下的 effective sample 对 anchor 的折减；
8. 三档阈值下采样几何变化，强调不可外推；
9. split stability 是否可评估；若 validation / robustness cluster 数不足，必须说明 sparse split caveat；
   若 train 的 `median_episode_length_sessions < primary_horizon_sessions`，必须说明 primary horizon
   下 full-horizon labelable step 可能稀疏，`effective_sample_nontrivial` 失败属于预注册 horizon
   的预期结果而不是实现错误；
10. 推荐的序贯采样单元与 horizon 候选集；
11. 为什么本实验仍不授权 sequential label、entry、model、separability 或 label deployment。
```

## 10. Decision Gates 与 Decision Map

### 10.1 Hard fail gates

任一失败，decision = `16A_blocked_input_or_lineage_failure`：

```text
input_artifact_gate            <- input_artifact_audit.csv.input_gate_status
upstream_lineage_gate          <- upstream_lineage_audit.csv.lineage_status
price_path_completeness_gate   <- price_path_completeness_audit.csv.price_path_status
cluster_interval_adapter_gate  <- cluster_interval_adapter_audit.csv.adapter_status
cluster_interval_rebuild_gate  <- cluster_interval_rebuild_audit.csv.rebuild_status
episode_cluster_non_overlap_gate <- episode_cluster_non_overlap_audit.csv.concurrency_status
geometry_consistency_gate      <- effective_sample_size_readout.csv.effective_sample_status
search_accounting_gate         <- search_accounting_audit.csv.search_accounting_status
```

若某 audit 表为空、缺 status、或 status 不在 allowlist，相关 gate fail closed。
`price_path_completeness_gate` allowlist = {pass}。
`cluster_interval_rebuild_gate` allowlist = {pass, not_required_pass}。
`episode_cluster_non_overlap_gate` allowlist = {pass_no_same_threshold_overlap}。
`geometry_consistency_gate` fail 当：effective_sample_size_overlap > step_n_overlap、
effective_sample_size_nonoverlap > full_horizon_nonoverlap_step_n、average_uniqueness 不在 [0,1]、
average_uniqueness_nonoverlap != 1、或 step count 与 episode_length_sessions / horizon_sessions
推导不一致。

### 10.2 Support gates（primary：selected_threshold_id = up50pct，cluster_split_bucket = train）

```text
sufficient_episode_clusters:
  episode_cluster_n_train >= 200

minimum_split_support_for_stability_gate:
  min(episode_cluster_n_train, episode_cluster_n_validation, episode_cluster_n_robustness) >= 100
  若任一 split 低于 100，geometry_stable_across_splits 不可评估；
  decision 进入 16A_sampling_geometry_inconclusive_too_sparse，而不是
  16A_sampling_geometry_unstable_across_splits。

anchor_overcount_demonstrated:
  anchor_to_nonoverlap_step_ratio_primary_horizon > 1.5
  （证明 anchor 确实高估有效样本，这是 16A 的核心正向发现）

effective_sample_nontrivial:
  effective_sample_size_train_primary_horizon >= 200

geometry_stable_across_splits:
  effective_to_anchor_ratio 在 train / validation / robustness 的 absolute range <= 0.20
  absolute range = max(split_effective_to_anchor_ratio) - min(split_effective_to_anchor_ratio)
  仅当 minimum_split_support_for_stability_gate 通过后才计算；否则 split stability 不可评估。
```

primary_horizon_sessions 预注册冻结为 20（中位 episode 内的合理 "下一小段" 候选）；
{5, 8, 13, 15} 作为 sensitivity readout，不改变 primary decision。

### 10.3 Decision Map

最终裁决只能取以下枚举之一：

```text
16A_sampling_geometry_ready_for_sequential_label_design
16A_sampling_geometry_overcount_confirmed_but_effective_sample_too_small
16A_sampling_geometry_overcount_not_demonstrated
16A_sampling_geometry_unstable_across_splits
16A_sampling_geometry_inconclusive_too_sparse
16A_blocked_input_or_lineage_failure
```

Decision map：

```text
if any hard fail:
  decision_state = 16A_blocked_input_or_lineage_failure
  next_allowed_requirement = none

elif not sufficient_episode_clusters:
  decision_state = 16A_sampling_geometry_inconclusive_too_sparse
  next_allowed_requirement = none

elif not minimum_split_support_for_stability_gate:
  decision_state = 16A_sampling_geometry_inconclusive_too_sparse
  next_allowed_requirement = none

elif not geometry_stable_across_splits:
  decision_state = 16A_sampling_geometry_unstable_across_splits
  next_allowed_requirement = none

elif anchor_overcount_demonstrated and not effective_sample_nontrivial:
  decision_state = 16A_sampling_geometry_overcount_confirmed_but_effective_sample_too_small
  next_allowed_requirement = none

elif anchor_overcount_demonstrated and effective_sample_nontrivial:
  decision_state = 16A_sampling_geometry_ready_for_sequential_label_design
  next_allowed_requirement = requirement_16b_sequential_continuation_label_design_diagnostic.md

else:
  decision_state = 16A_sampling_geometry_overcount_not_demonstrated
  next_allowed_requirement = none
```

Regardless of decision：

```text
label_deployment_authorized = False
signal_search_authorized = False
model_training_authorized = False
entry_policy_authorized = False
separability_search_authorized = False
sequential_label_authorized = False
```

注意：即使 decision = `16A_sampling_geometry_ready_for_sequential_label_design`，16A 只授权 16B
**设计** 序贯 continuation label diagnostic，不授权任何 entry / 收益 / 模型。16B 仍须重新冻结
label / horizon / 去重结构并独立论证。

## 11. Search Accounting

```text
startup_authorization_basis = ep15_effective_sample_and_position_dependence_not_shape_taxonomy
manual_research_plan_override = true
selected_threshold_id = up50pct
threshold_selection_source = inherited_from_15A_lowest_pre_registered_material_censoring_threshold
geometry_fit_split = none_descriptive_only
validation_usage = readout_only
robustness_usage = readout_only
horizon_grid_sessions = {5, 8, 13, 15, 20}
primary_horizon_sessions = 20
forward_return_computed = false
entry_search_authorized = false
signal_search_authorized = false
model_training_authorized = false
separability_search_authorized = false
sequential_label_authorized = false
search_accounting_status = pass iff all authorization/search-accounting fields match this frozen block; fail otherwise
```

## 12. Tests

必须至少覆盖：

```text
test_cluster_interval_adapter_uses_membership_audit_for_path_winner_and_censored
test_cluster_interval_adapter_uses_episode_threshold_pos_as_anchor_hit_pos
test_cluster_interval_adapter_fails_when_interval_inconsistent_with_entry_hit_pos
test_cluster_interval_adapter_reports_hit_pos_relation_and_interval_violation_counts
test_cluster_rebuild_uses_15a_path_defined_label_panel_and_15b_section_6_2_rule
test_cluster_rebuild_not_required_when_cache_schema_passes
test_price_path_audit_required_and_fail_closed_when_missing_or_nonpass
test_episode_interval_within_price_path_observable_range
test_cluster_end_beyond_anchor_available_forward_sessions_fails_closed
test_eligible_excludes_cross_split_and_censored
test_eligible_requires_split_overlap_flags_false
test_horizon_grid_frozen_at_5_8_13_15_20
test_nonoverlapping_step_count_matches_ceil_episode_length_over_horizon
test_full_horizon_labelable_step_count_uses_floor_episode_length_over_horizon
test_overlapping_step_count_matches_episode_length_minus_horizon_plus_one
test_partial_tail_step_flagged_not_dropped_silently
test_anchor_overcount_ratio_uses_nonoverlap_step_denominator
test_anchor_to_labelable_step_ratio_uses_full_horizon_denominator
test_anchor_weighted_overcount_ratio_uses_sum_anchor_over_sum_step
test_effective_sample_readout_contains_full_horizon_fields_for_gate
test_effective_sample_readout_compares_episode_cluster_blocked_and_time_block
test_decision_records_validation_and_robustness_cluster_counts_for_stability_gate
test_average_uniqueness_in_zero_one_and_concurrency_within_instrument_only
test_effective_sample_size_never_exceeds_step_count
test_same_threshold_instrument_episode_overlap_fails_closed
test_forward_return_not_computed_anywhere
test_threshold_sensitivity_does_not_change_primary_decision
test_primary_horizon_frozen_at_20_and_5_8_13_15_are_sensitivity_only
test_sparse_validation_split_makes_stability_not_evaluable_not_unstable
test_geometry_stable_requires_effective_to_anchor_ratio_absolute_range_within_0p20
test_primary_horizon_longer_than_median_episode_length_reported_as_expected_sparsity
test_hard_fail_gate_sources_exist_and_fail_closed_when_missing
test_geometry_consistency_gate_rejects_impossible_values
test_decision_map_handles_overcount_not_demonstrated_without_confirmed_wording
test_search_accounting_records_startup_authorization_override
test_decision_map_never_authorizes_sequential_label_or_entry_or_separability
test_ready_decision_only_authorizes_16b_design_not_entry
```

Synthetic fixtures 至少包含：

```text
single long episode where anchor_n >> nonoverlap_step_n (overcount demonstrated)
two overlapping same-threshold episodes of same instrument (cluster lineage fail closed)
short episode shorter than primary horizon (partial tail only)
cross_split cluster that must be excluded from primary geometry
censored / non-winner anchors that must be excluded
cluster whose cluster_end_pos exceeds qfq_row_n or anchor available_forward_sessions
horizon grid {5, 8, 13, 15, 20} producing different step counts and uniqueness
```

## 13. Implementation Notes

```text
1. 16A 绝不计算 forward return / 收益 / cost；它只量化采样几何（计数、覆盖、重叠、唯一度）。
2. anchor 只作为 audit-only 单元用于证明高估，不作为有效样本；primary 单元是非重叠短窗 step。
3. concurrency / uniqueness 只在同一 instrument 内计算；跨 instrument step 视为独立。
4. 同 threshold / instrument 的 episode cluster interval 若相互重叠，说明 15B transitive clustering lineage 失效，必须 fail closed；不同 threshold 间重叠只做 sensitivity readout。
5. horizon grid（{5,8,13,15,20}，primary=20）、selected_threshold_id 全部预注册冻结，写入 audit。
6. cross_split / split-boundary touching cluster 只能 readout，不进入 primary 几何。
7. 三档阈值分开报告，不得把 up50 的采样几何外推到 up100 / up150。
8. 即使采样几何干净，decision 也只授权 16B 设计诊断，不授权 sequential label / entry / 收益 / 模型。
9. report 必须明确：16A 是序贯范式的采样地基诊断，回答 "有效独立样本几何是什么"，不回答 "下一小段是否盈利"。
```

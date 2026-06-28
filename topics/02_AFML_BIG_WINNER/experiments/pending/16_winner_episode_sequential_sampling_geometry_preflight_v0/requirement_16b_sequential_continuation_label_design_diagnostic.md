# 需求：16B Sequential Continuation Label Design Diagnostic

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0
SOURCE_EP16_ROOT = EXPERIMENT_ROOT
SOURCE_EP15_ROOT = TOPIC_ROOT/experiments/pending/15_path_defined_winner_episode_label_v0
SOURCE_EP14_ROOT = TOPIC_ROOT/experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0
SOURCE_EP13_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 以 `SOURCE_EP16_ROOT/`、`SOURCE_EP15_ROOT/`、`SOURCE_EP14_ROOT/`、`SOURCE_EP13_ROOT/` 表达的路径必须先解析到对应 root，再写入 `input_artifact_audit.csv`。
5. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
6. 必需输入缺失、schema 不匹配、16A ready 裁决不可证明、采样单元 lineage 不可证明、horizon lineage 不可证明、price path completeness 不可证明、split/stress 口径不可证明、search accounting 不可证明时 fail closed。
7. 不得从报告文本、图像、人工讨论文本、聚合 readout 或未来 16C/16D 设想反推出逐行 sampling step、continuation label、split boundary、entry 价格或 feature。

## 1. 实验身份

```text
experiment_id = 16_winner_episode_sequential_sampling_geometry_preflight_v0
phase_id = 16B
run_id = 16B_sequential_continuation_label_design_diagnostic
status = draft_ready_for_review
expected_entrypoint = src/run_16b_sequential_continuation_label_design_diagnostic.py
expected_config = configs/config_16b_sequential_continuation_label_design_diagnostic.yaml
expected_test_file = tests/test_16b_sequential_continuation_label_design_diagnostic.py
source_plan = EXPERIMENT_ROOT/research_plan.md
upstream_requirement_16a = SOURCE_EP16_ROOT/requirement_16a_sequential_sampling_geometry_preflight.md
upstream_report_16a = SOURCE_EP16_ROOT/outputs/publishable/reports/sequential_sampling_geometry_preflight_report.md
```

16B 是 Episode 16 的第二个 phase。它只在 16A 裁决为：

```text
16A_sampling_geometry_ready_for_sequential_label_design
```

时允许启动。16B 的使命是基于 16A 钉死的 sampling geometry，设计并审计短窗 continuation / survival label 的形态是否可用。

16B 仍然不是：

```text
entry / exit / holding policy
交易收益 / cost / portfolio backtest
t0 feature search
separability test
model training
signal deployment
label deployment
```

16B 最多只能授权后续新建：

```text
requirement_16c_sequential_continuation_separability_diagnostic.md
```

## 2. 16A 授权与边界

16B 必须继承 16A 的以下冻结结论：

```text
selected_threshold_id = up50pct
primary_horizon_sessions = 20
horizon_sensitivity_grid = {5, 8, 13, 15}
sampling_unit = non_overlapping_time_blocked_sampling_geometry_step
stability_gate_split_buckets = {train, robustness}
stress_test_split_buckets = {validation}
validation_usage = stress_test_readout_only
partial_tail_step_usage = tail_readout_only
```

16A 的关键数值必须在 16B 的 input lineage 中复验：

```text
anchor_n_train = 57524
episode_cluster_n_train = 667
episode_cluster_n_validation = 45
episode_cluster_n_robustness = 218
nonoverlap_step_n_train_primary_horizon = 20871
full_horizon_nonoverlap_step_n_train_primary_horizon = 20245
partial_tail_step_n_train_primary_horizon = 626
effective_sample_size_train_primary_horizon = 20245
anchor_overcount_ratio_train_primary_horizon = 2.756169
effective_to_anchor_ratio_abs_range = 0.131094
```

`effective_to_anchor_ratio_abs_range` 必须使用 16A `sampling_geometry_decision.csv` 的真实字段名，不得在实现中要求不存在的 `_train_robustness` 后缀字段；若实现需要语义别名，只能在 `upstream_16a_authorization_audit.csv` 中显式记录为派生别名。

若 16A decision、next_allowed_requirement、primary horizon、sampling unit、validation stress 口径或 gate status 与上述不一致，`upstream_16a_authorization_gate` fail closed。

16B 不得把 16A ready 解释成 label deployment 授权。16A 只说明采样地基足够干净，可以设计并审计 continuation label。

## 3. 核心问题

16B 回答以下问题：

```text
Q1. 在 16A 的 non-overlapping h20 step 上，如何定义一个短窗 continuation / survival label，
    使其不是 anchor winner label、不是整段 path shape taxonomy、也不是 t0 entry signal？

Q2. continuation label 在 train / robustness 上是否有非平凡 base rate 和足够去重后样本量？
    validation 作为 stress-test readout 是否暴露稀疏或口径风险？

Q3. label population 是否大量暴露在已知失败 episode context 中，例如 compression /
    drawdown-reversal / badside rebound？cluster-level context exposure 只能生成 caveat；
    只有未来 step-local morphology audit 才能把“失败形态换名”作为 hard fail。

Q4. horizon sensitivity {5, 8, 13, 15, 20} 下，label base rate、effective sample、
    split stability 与 known-failed overlap 是否稳定？primary decision 仍只能由 h20 决定。

Q5. 若 label design 通过，16C 应当检验哪一个 label id，使用哪些 denominator 和 split discipline？
```

必须输出单一裁决：

```text
decision_state
```

## 4. Scope Boundary

16B 允许做：

```text
1. 复用 16A 的 eligible episode interval、non-overlap step、full-horizon labelable step、split/stress 口径；
2. 基于 step 内部及 step 后继关系构造 continuation / survival label；
3. 输出 label base rate、positive/negative/neutral/tail counts、去重后 effective sample；
4. 按 train / robustness / validation stress / threshold sensitivity 输出 label readout；
5. 审计 label 对 known-failed episode context 的 exposure，并明确该 readout 不是 step-local morphology gate；
6. 输出确定性 next-research decision map。
```

16B 明确不是：

```text
entry policy
exit policy
holding policy
收益 / forward return / alpha / cost / backtest
t0 feature search
separability search
model training
portfolio construction
label deployment authorization
```

16B 可以使用 winner episode interval 内部的未来 path 结构定义 label，因为这是 label-form diagnostic；但不得把任一步解释成可交易 entry，也不得计算交易收益或 cost。

## 5. Required Inputs

16B 必须读取以下 16A artifacts：

```text
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/input_artifact_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/upstream_lineage_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/price_path_completeness_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/cluster_interval_adapter_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/cluster_interval_rebuild_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/sampling_unit_count_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/horizon_grid_step_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/effective_sample_size_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/episode_cluster_non_overlap_audit.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/geometry_by_split_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/geometry_by_threshold_sensitivity_readout.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/sampling_geometry_decision.csv
SOURCE_EP16_ROOT/outputs/publishable/tables/16A_sequential_sampling_geometry_preflight/search_accounting_audit.csv
SOURCE_EP16_ROOT/outputs/local_cache/16A_sequential_sampling_geometry_preflight/episode_interval_panel.parquet
SOURCE_EP16_ROOT/outputs/local_cache/16A_sequential_sampling_geometry_preflight/step_geometry_panel.parquet
```

16B 必须读取以下 Episode 15 lineage artifacts：

```text
SOURCE_EP15_ROOT/configs/config_15b_winner_path_shape_taxonomy_diagnostic.yaml
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/winner_episode_cluster_membership_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/split_overlap_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_defined_label_adapter_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_taxonomy_rule_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/representative_anchor_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15A_winner_episode_label_censoring_diagnostic/price_path_completeness_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/price_path_completeness_audit.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15C2_winner_soft_shape_membership_diagnostic/winner_soft_shape_membership_decision.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15C2_winner_soft_shape_membership_diagnostic/anchor_soft_membership_panel.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15C2_winner_soft_shape_membership_diagnostic/known_failed_morphology_overlap_readout.csv
SOURCE_EP15_ROOT/outputs/publishable/tables/15C2_winner_soft_shape_membership_diagnostic/shape_membership_rule_audit.csv
```

16B 必须显式读取 raw qfq close price source，不能只依赖 price-path audit：

```text
stock_daily_qfq_dir = data/raw/akshare/day/qfq
required qfq file = stock_daily_qfq_dir/{instrument}.csv
required qfq columns = {date, close}
qfq row order = qfq trading session pos used by 15A / 15B / 16A
```

若任一 labelable step 涉及的 instrument qfq 文件缺失、`date` / `close` 缺失、row order 不能与 15A/15B `qfq_row_n` 对齐、`close` 非有限或 `close <= 0`，`qfq_price_source_gate` fail closed。

16B primary known-failed hard guard 必须读取 15B row-level taxonomy cache；15C2 soft-membership cache 只作为补充 readout / caveat 来源，不得因覆盖不足单独阻断 primary decision：

```text
required_primary_hard_projection:
  SOURCE_EP15_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/taxonomy_assignment_panel.parquet

optional_soft_overlap_context:
  SOURCE_EP15_ROOT/outputs/local_cache/15C2_winner_soft_shape_membership_diagnostic/anchor_soft_membership_panel.parquet
```

若 15B row-level taxonomy cache 缺失或无法与 publishable 15B audits 对齐，`known_failed_overlap_evaluability_gate = fail_not_evaluable`，decision 不能授权 16C。

若 15C2 soft-membership cache 缺失、schema 不完整或 cluster-level soft coverage `< 0.95`，必须输出 `soft_overlap_partial_coverage_caveat`，但不得设置 `known_failed_overlap_evaluability_gate` fail，也不得阻断 16C 授权。

14A state overlap 只能使用当前存在的 publishable aggregate readout 作为 context appendix：

```text
SOURCE_EP14_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/morphology_rediscovery_audit.csv
SOURCE_EP14_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/sparse_event_raw_readout.csv
```

这些 14A artifacts 在 `input_artifact_audit.csv.required_flag` 中必须标记为 `optional_appendix`。它们若无法 row-level join 到 16B step，不得进入 primary `known_failed_overlap_gate`，也不得单独 fail closed；只能写入 appendix/readout caveat。

## 6. 采样单元继承

16B 的 primary row unit 冻结为：

```text
primary_label_unit = continuation_label_step
source_sampling_unit = 16A.non_overlapping_time_blocked_sampling_geometry_step
primary_horizon_sessions = 20
primary_threshold_id = up50pct
primary_split_gate = train + robustness
validation_usage = stress_test_readout_only
```

16B 不得使用 anchor row 作为 primary independent sample。anchor 只能作为 lineage / denominator 对照。

16B 的 labelable population：

```text
labelable_step =
  16B materialized step where:
    threshold_id in {up50pct, up100pct, up150pct}
    cluster_split_bucket in {train, validation, robustness}
    eligible_episode_cluster == true
    horizon_sessions in {5, 8, 13, 15, 20}
    full_horizon_nonoverlap_step == true
    partial_tail_step == false
```

primary labelable population 进一步限定：

```text
threshold_id == up50pct
horizon_sessions == 20
cluster_split_bucket in {train, robustness}
```

validation rows 必须输出 readout，但不能进入 primary stability gate。

### 6.1 Step Materialization Rule

16A 的 `step_geometry_panel.parquet` 是 cluster/horizon aggregate panel，不是逐 step panel。16B 必须从 16A `episode_interval_panel.parquet` 重新 materialize row-level non-overlap steps，并用 16A aggregate readout 复核数量。

对每个 eligible episode cluster 和每个 `horizon_sessions = h`：

```text
episode_length_sessions = cluster_end_pos - cluster_start_pos + 1
full_horizon_step_n = floor(episode_length_sessions / h)
partial_tail_step_n = 1 if episode_length_sessions % h != 0 else 0

for step_index in [0, full_horizon_step_n - 1]:
  step_start_pos = cluster_start_pos + step_index * h
  step_end_pos = step_start_pos + h - 1
  step_id = threshold_id || instrument || episode_cluster_id || h || step_index
```

Required invariants：

```text
step_start_pos >= cluster_start_pos
step_end_pos <= cluster_end_pos
step_end_pos - step_start_pos + 1 == horizon_sessions
step_start_pos >= 0
step_end_pos < qfq_row_n
row count by threshold_id / cluster_split_bucket / horizon_sessions
  == 16A horizon_grid_step_readout.labelable_step_n_for_future_16B
row count by threshold_id / instrument / episode_cluster_id / horizon_sessions
  == floor(episode_length_sessions / horizon_sessions)
partial tail rows are not materialized as labelable steps
```

每个 threshold_id / cluster_split_bucket / horizon_sessions cell 都由上方通用 invariant
`row count ... == labelable_step_n_for_future_16B` 覆盖。primary cell 额外硬钉以下数值等式，
不替代通用 invariant，只是对 primary 路径的冗余强校验：

```text
primary h20 up50 train materialized step total == 20245
primary h20 up50 train nonoverlap_step_n_from_16A - materialized step total
  == 20871 - 20245 == 626 == partial_tail_step_n_from_16A
```

若任一 invariant 失败，`step_materialization_gate` fail closed。

## 7. Continuation Label 定义

16B 预注册三类 label，并以第一类为 primary：

```text
primary_label_id = continuation_survival_h20_no_deep_drawdown
secondary_label_id = continuation_progress_h20_positive_path
stress_label_id = continuation_survival_h20_no_episode_break
```

### 7.1 Primary label: continuation_survival_h20_no_deep_drawdown

对每个 full-horizon non-overlap step：

```text
step_window = [step_start_pos, step_end_pos] inclusive
step_start_price = qfq close at step_start_pos
max_drawdown_from_step_start =
  min(qfq close[p] / step_start_price - 1 for p in step_window)
step_end_price = qfq close at step_end_pos
step_end_price_ratio_minus_one_for_label_rule = step_end_price / step_start_price - 1
```

Primary continuation label：

```text
continuation_positive = (
  max_drawdown_from_step_start > -0.10
  and step_end_price_ratio_minus_one_for_label_rule >= 0
)
continuation_negative = (
  max_drawdown_from_step_start <= -0.10
)
continuation_neutral = not continuation_positive and not continuation_negative
```

解释：

```text
positive = 下一小段没有深回撤，且到窗口末端至少没有跌破 step 起点；
negative = 下一小段发生超过 10% 的 close-to-close drawdown；
neutral = 没有深回撤，但窗口末端未能保持非负。
```

这里的 `step_end_price_ratio_minus_one_for_label_rule` 只能作为 label construction statistic，不得解释为 forward return、交易收益、alpha 或 backtest return，也不得输出到任何收益/策略类表。

### 7.2 Secondary label: continuation_progress_h20_positive_path

```text
continuation_progress_positive = (
  step_end_price_ratio_minus_one_for_label_rule > 0
  and max_drawdown_from_step_start > -0.10
)
```

该 label 用于检查 primary label 是否过于宽松；不得改变 primary decision。

Secondary label 的 readout 仅作 narrative / 对照用途：它会进入 §8 base-rate readout，
但不进入 §12 任何 support gate，也不出现在 §11 `sequential_continuation_label_decision.csv`
的任何裁决字段。实现不得让 secondary label 影响 `decision_state` 或任何 `*_authorized` 标志。

### 7.3 Stress label: continuation_survival_h20_no_episode_break

```text
continuation_survival_positive = (
  step_end_pos <= cluster_end_pos
  and step is full-horizon non-overlap
)
```

该 label 只用于 sanity/stress readout。由于 16A 的 full-horizon step 已在 episode interval 内生成，该 label 预期 base rate 接近 1；若不接近，说明 step generation lineage 异常。

机器判定阈值：

```text
step_generation_lineage_sane = continuation_survival_positive_rate >= 0.999
```

若该 sanity 阈值不满足，`step_materialization_gate` fail closed。

## 8. Base Rate、Denominator 与 Effective Sample

所有 label readout 必须同时输出：

```text
labelable_step_n
positive_step_n
negative_step_n
neutral_step_n
positive_rate
negative_rate
neutral_rate
effective_sample_size_nonoverlap
positive_effective_sample_size
negative_effective_sample_size
episode_cluster_n
anchor_n_reference_only
```

其中：

```text
positive_rate = positive_step_n / labelable_step_n
negative_rate = negative_step_n / labelable_step_n
neutral_rate = neutral_step_n / labelable_step_n
positive_effective_sample_size = positive_step_n
negative_effective_sample_size = negative_step_n
```

因为 primary unit 是 non-overlap full-horizon step，16B primary effective sample 等于 full-horizon labelable step count。任何 anchor-weighted base rate 只能作为 appendix readout。

## 9. Known-failed Episode-context Exposure

16B 必须检查 primary label population 是否大量暴露在已知失败 episode context 中。至少审计以下 cluster-level context exposure：

```text
15B path_type in {
  choppy_reversal_winner,
  late_rescue_winner,
  jump_repricing_winner,
  unclassified_mixed_path
}

15C2 high soft membership to failed / unstable prototypes as appendix / caveat only

14A aggregate morphology/state context as appendix only
```

`known_failed_family` 名称必须先经过枚举校验：

```text
required_15b_known_failed_path_types = {
  choppy_reversal_winner,
  late_rescue_winner,
  jump_repricing_winner,
  unclassified_mixed_path
}

required_15b_known_failed_path_types
  subset_of taxonomy_assignment_panel.path_type.unique()
```

若枚举校验失败，`known_failed_overlap_evaluability_gate = fail_unknown_known_failed_family_enum`。不得把全量 join miss 解释为 `failed_family_positive_share = 0`。

family 取值校验之外，primary hard projection 所需 15B 列名也必须在评分前存在性校验（N3）。15C2 schema 只在 soft-overlap appendix 可用时校验，校验失败只产生 caveat，不进入 hard fail。

```text
15B taxonomy_assignment_panel.parquet 硬列名:
  hard_path_type_source_column = path_type            # 15B panel 用 path_type，不是 hard_path_type_15b
  required_15b_panel_columns = {source_row_key, threshold_id, episode_cluster_id, path_type, assignment_unit}
  anchor 行筛选: assignment_unit == "anchor_path"      # episode_cluster 行不得当作 anchor

15C2 anchor_soft_membership_panel.parquet soft-overlap appendix 列名:
  hard_path_type_source_column = hard_path_type_15b    # 15C2 panel 把 path_type 重命名为 hard_path_type_15b
  optional_15c2_panel_columns = {source_row_key, threshold_id, hard_path_type_15b}
  soft membership 列形如 membership_{family}, 至少包含:
    membership_smooth_trend_winner, membership_stair_step_winner,
    membership_jump_repricing_winner, membership_choppy_reversal_winner,
    membership_slow_grind_winner, membership_late_rescue_winner

required_15b_panel_columns subset_of taxonomy_assignment_panel.columns
if 15C2 soft-overlap appendix is attempted:
  optional_15c2_panel_columns subset_of anchor_soft_membership_panel.columns
  所用 membership_{family} 列必须存在于 anchor_soft_membership_panel.columns
```

若 15B 所需列名缺失，`known_failed_overlap_evaluability_gate = fail_missing_known_failed_projection_column`，不得进入 join 才暴露。若 15C2 soft-overlap appendix 所需列名缺失，只输出 `soft_overlap_schema_caveat`，不得影响 primary hard gate。

Known-failed projection 在 16B 中只能回答 episode-context exposure，不能回答 step-local morphology rediscovery。15B 的 `path_type` 是 episode/cluster realized full-path descriptor，包含总时长、水下时间、全路径 efficiency、最终 rescue 等全路径属性；把该 descriptor 投影到 cluster 内每个 h20 step，只能说明该 step 位于某个 known-failed episode context 内，不能说明该 h20 step 自身就是 known-failed morphology。

因此 projection 必须按 step-level denominator 输出 readout，但不得把 cluster-level descriptor 投影后的高占比作为 primary hard fail。投影规则冻结为：

```text
1. 用 15B membership audit 取得每个 16A episode_cluster_id 的 anchor source_row_key 集合。
2. 回填 anchor-level hard path type:
   - primary hard projection 只能使用 15B taxonomy_assignment_panel；
   - 取 assignment_unit == "anchor_path" 行的 path_type；
   join key = (source_row_key, threshold_id)。
3. 对每个 threshold_id / instrument / episode_cluster_id / known_failed_family 计算：
   cluster_failed_anchor_share = failed_family_anchor_n / joined_anchor_n
4. 一个 materialized step 继承其 episode_cluster_id 的 cluster_failed_anchor_share 作为 context descriptor；
   known_failed_step_flag = cluster_failed_anchor_share >= 0.50。
5. 15C2 soft membership 只输出 appendix / caveat：
   soft_membership_high_threshold = 0.30；
   family_anchor_positive = membership_{family} >= 0.30；
   cluster_soft_failed_anchor_share = soft_failed_family_anchor_n / soft_joined_anchor_n；
   soft_overlap_coverage = soft_joined_anchor_n / cluster_anchor_n。
6. anchor share 只用于生成 cluster context descriptor，不得把 anchors 当作 primary independent sample；
   readout denominator 必须仍是 materialized step count。
7. 若 failed_family_positive_share 很高但 share_delta <= 0，解释为 duration-weighted context exposure；
   不得声称 continuation label step-local rediscovered known-failed morphology。
```

若某 cluster 的 15B hard projection joined anchor coverage `< 0.95`，该 cluster 的 known-failed projection status 为 `insufficient_15b_hard_projection_coverage`，`known_failed_overlap_evaluability_gate` fail closed。

若某 cluster 的 15C2 soft-overlap coverage `< 0.95`，该 cluster 的 soft-overlap status 为 `soft_overlap_partial_coverage_caveat`；该 caveat 必须进入 `known_failed_overlap_readout.csv` 和 report，但不得改变 `known_failed_overlap_gate` 或 `known_failed_overlap_evaluability_gate`。

Overlap readout 必须输出：

```text
label_id
known_failed_family
overlap_source
split_bucket
positive_step_n
failed_family_positive_step_n
failed_family_positive_share
all_step_failed_family_share
share_delta
hard_projection_coverage
soft_overlap_coverage
soft_overlap_status
overlap_status
```

Gate 与 caveat：

```text
known_failed_overlap_gate pass iff
  15B hard projection is evaluable
  and primary train hard_15b_taxonomy readout is non-empty
  and hard_projection_coverage >= 0.95 for every required cluster

known_failed_context_exposure_caveat = true iff
  for primary label in train:
    max(failed_family_positive_share) > 0.50
    or max(share_delta) > 0.20
```

`known_failed_context_exposure_caveat` 只写入 decision row、readout 和 report caveat，不参与 §13 decision branch。只有未来新增 step-local morphology audit，并在每个 h20 step 自身重算 local duration / drawdown / underwater / efficiency 等特征后，才允许把 known-failed morphology rediscovery 作为 hard fail。

若 15B row-level known-failed overlap artifact 缺失或无法对齐到 step / anchor lineage，`known_failed_overlap_evaluability_gate = fail_not_evaluable`，decision 不能授权 16C。15C2 soft-overlap artifact 缺失、覆盖不足或 schema 不完整只生成 caveat。

## 10. Required Outputs

输出到：

```text
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/
```

Required tables：

```text
input_artifact_audit.csv
upstream_16a_authorization_audit.csv
step_lineage_adapter_audit.csv
step_materialization_audit.csv
qfq_price_source_audit.csv
price_path_completeness_audit.csv
label_rule_definition_audit.csv
continuation_label_panel_readout.csv
continuation_label_base_rate_readout.csv
continuation_label_by_split_readout.csv
continuation_label_by_horizon_sensitivity_readout.csv
continuation_label_by_threshold_sensitivity_readout.csv
known_failed_overlap_readout.csv
validation_stress_readout.csv
effective_sample_label_support_readout.csv
sequential_continuation_label_decision.csv
search_accounting_audit.csv
```

Local cache：

```text
outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/continuation_label_step_panel.parquet
outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/materialized_step_panel.parquet
outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/known_failed_overlap_panel.parquet
```

Report：

```text
outputs/publishable/reports/sequential_continuation_label_design_diagnostic_report.md
```

## 11. 关键表最小字段

`upstream_16a_authorization_audit.csv` 至少包含：

```text
upstream_decision_state
upstream_next_allowed_requirement
selected_threshold_id
primary_horizon_sessions
sampling_unit
stability_gate_split_buckets
stress_test_split_buckets
nonoverlap_step_n_train_primary_horizon
full_horizon_nonoverlap_step_n_train_primary_horizon
partial_tail_step_n_train_primary_horizon
anchor_overcount_ratio_train_primary_horizon
effective_sample_size_train_primary_horizon
effective_to_anchor_ratio_abs_range
geometry_stable_across_splits
all_16a_hard_gates_passed
authorization_status
blocking_reason
```

`label_rule_definition_audit.csv` 至少包含：

```text
label_id
label_role
horizon_sessions
step_price_field
drawdown_threshold
step_end_price_ratio_threshold
positive_predicate
negative_predicate
neutral_predicate
tail_step_usage
rule_status
```

`step_lineage_adapter_audit.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
horizon_sessions
source_episode_cluster_n
materialized_step_n
expected_labelable_step_n_from_16a
step_count_delta_vs_16a
duplicate_step_id_n
bad_step_bounds_n
partial_tail_materialized_n
adapter_status
blocking_reason
```

`qfq_price_source_audit.csv` 至少包含：

```text
instrument
qfq_path
qfq_row_n
required_by_labelable_step_n
missing_qfq_file_flag
missing_required_columns
nonfinite_close_n
nonpositive_close_n
step_bounds_out_of_qfq_n
qfq_price_source_status
blocking_reason
```

`price_path_completeness_audit.csv` 至少包含：

```text
instrument
qfq_row_n
upstream_15a_price_path_status
upstream_15b_price_path_status
qfq_price_source_status
required_labelable_step_n
max_step_end_pos
step_bounds_out_of_qfq_n
price_path_status
blocking_reason
```

`continuation_label_panel_readout.csv` 至少包含：

```text
step_id
label_id
threshold_id
cluster_split_bucket
instrument
episode_cluster_id
horizon_sessions
step_index
step_start_pos
step_end_pos
step_start_date
step_end_date
step_start_qfq_close
step_end_qfq_close
max_drawdown_from_step_start
step_end_price_ratio_minus_one_for_label_rule
continuation_positive
continuation_negative
continuation_neutral
label_rule_status
```

`continuation_label_base_rate_readout.csv` 至少包含：

```text
label_id
threshold_id
cluster_split_bucket
horizon_sessions
labelable_step_n
positive_step_n
negative_step_n
neutral_step_n
positive_rate
negative_rate
neutral_rate
effective_sample_size_nonoverlap
positive_effective_sample_size
negative_effective_sample_size
episode_cluster_n
anchor_n_reference_only
base_rate_status
```

`known_failed_overlap_readout.csv` 至少包含：

```text
label_id
known_failed_family
overlap_source
cluster_split_bucket
positive_step_n
failed_family_positive_step_n
failed_family_positive_share
all_step_failed_family_share
share_delta
hard_projection_coverage
soft_overlap_coverage
soft_overlap_status
overlap_status
blocking_reason
```

`sequential_continuation_label_decision.csv` 至少包含：

```text
decision_state
next_allowed_requirement
primary_label_id
selected_threshold_id
primary_horizon_sessions
labelable_step_n_train
positive_rate_train
negative_rate_train
positive_effective_sample_size_train
negative_effective_sample_size_train
labelable_step_n_robustness
positive_rate_robustness
negative_rate_robustness
negative_effective_sample_size_robustness
base_rate_nontrivial
effective_sample_sufficient
base_rate_stable_train_robustness
validation_stress_evaluable
step_generation_lineage_sane
soft_overlap_partial_coverage_caveat
step_materialization_gate
qfq_price_source_gate
known_failed_overlap_gate
known_failed_overlap_evaluability_gate
label_deployment_authorized
signal_search_authorized
model_training_authorized
entry_policy_authorized
separability_search_authorized
```

## 12. Decision Gates

Hard fail gates：

```text
input_artifact_gate
upstream_16a_authorization_gate
step_lineage_adapter_gate
label_rule_definition_gate
step_materialization_gate
qfq_price_source_gate
price_path_completeness_gate
known_failed_overlap_evaluability_gate
search_accounting_gate
```

Support gates（primary label, up50pct, h20, train + robustness）：

```text
base_rate_nontrivial:
  0.20 <= positive_rate_train <= 0.80
  and 0.05 <= negative_rate_train <= 0.60

effective_sample_sufficient:
  positive_effective_sample_size_train >= 500
  and negative_effective_sample_size_train >= 200
  and labelable_step_n_train >= 2000
  and negative_effective_sample_size_robustness >= 50
  # 地板 50 依据: 16A up50/robustness/h20 labelable_step_n = 2496;
  # 以 base_rate_nontrivial 的 negative_rate 下限 0.05 计, robustness 期望 negative ≈ 125,
  # 50 ≈ robustness h20 总步数 × negative_rate 下限的保守地板, 留约 2.5× 余量,
  # 用于防止 train/robustness 稳定性判定建立在个位数 negative step 上。

base_rate_stable_train_robustness:
  abs(positive_rate_train - positive_rate_robustness) <= 0.15
  and abs(negative_rate_train - negative_rate_robustness) <= 0.15

validation_stress_evaluable:
  validation labelable_step_n >= 100
  若 validation < 100，不阻断 primary decision，但必须输出 stress caveat。
  该字段只写入 decision row 和 report caveat，不参与 §13 decision branch。

soft_overlap_partial_coverage_caveat:
  any 15C2 soft-overlap cluster has soft_overlap_coverage < 0.95
  该字段只写入 decision row 和 report caveat，不参与 §13 decision branch。

known_failed_overlap_gate:
  pass iff §9 的 15B hard taxonomy projection 可评估且 primary train readout 非空。
  高 failed_family_positive_share 或 share_delta 只设置
  known_failed_context_exposure_caveat，不阻断 primary decision。

known_failed_context_exposure_caveat:
  true iff primary train cluster-level context projection 超过第 9 节 caveat 阈值。
  该字段表示 h20 step population 对 known-failed episode context 的 exposure，
  不得解释成 step-local known-failed morphology rediscovery。
```

若 primary negative label 因 `max_drawdown_from_step_start <= -0.10` 在 winner episode 内部过稀，导致 `negative_effective_sample_size_train` 或 `negative_effective_sample_size_robustness` 不足，这是合法的 `16B_continuation_label_effective_sample_too_small` 结局，不是实现 bug。任何调整 drawdown 阈值都必须进入新的后续 requirement 或显式 retry requirement，不得在本次 16B 运行中根据结果重调。

## 13. Decision Map

最终裁决只能取以下枚举之一：

```text
16B_continuation_label_ready_for_separability_diagnostic
16B_continuation_label_blocked_by_input_or_lineage_failure
16B_continuation_label_base_rate_degenerate
16B_continuation_label_effective_sample_too_small
16B_continuation_label_unstable_train_robustness
```

Decision map：

```text
if any hard fail:
  decision_state = 16B_continuation_label_blocked_by_input_or_lineage_failure
  next_allowed_requirement = none

elif not base_rate_nontrivial:
  decision_state = 16B_continuation_label_base_rate_degenerate
  next_allowed_requirement = none

elif not effective_sample_sufficient:
  decision_state = 16B_continuation_label_effective_sample_too_small
  next_allowed_requirement = none

elif not base_rate_stable_train_robustness:
  decision_state = 16B_continuation_label_unstable_train_robustness
  next_allowed_requirement = none

else:
  decision_state = 16B_continuation_label_ready_for_separability_diagnostic
  next_allowed_requirement = requirement_16c_sequential_continuation_separability_diagnostic.md
```

`validation_stress_evaluable`、`soft_overlap_partial_coverage_caveat` 与 `known_failed_context_exposure_caveat` 不参与上述分支，只作为 caveat 字段落表。若 validation 样本不足、15C2 soft-overlap 覆盖不足，或 cluster-level known-failed context exposure 较高，但其他 primary gates 通过，仍可 ready；report 必须明确这些 caveat。

Regardless of decision：

```text
label_deployment_authorized = false
signal_search_authorized = false
model_training_authorized = false
entry_policy_authorized = false
separability_search_authorized = false
```

若 decision ready，只授权 16C 做 separability diagnostic，不授权 entry / 收益 / 模型 / 部署。

## 14. Search Accounting

```text
startup_authorization_basis = 16A_sampling_geometry_ready_for_sequential_label_design
selected_threshold_id = up50pct
primary_label_id = continuation_survival_h20_no_deep_drawdown
primary_horizon_sessions = 20
horizon_sensitivity_grid = {5, 8, 13, 15}
sampling_unit = non_overlapping_time_blocked_sampling_geometry_step
validation_usage = stress_test_readout_only
geometry_fit_split = none_label_design_only
forward_return_computed_for_trading = false
step_materialization_source = 16A_episode_interval_panel_formula
qfq_price_source = data/raw/akshare/day/qfq
entry_search_authorized = false
signal_search_authorized = false
model_training_authorized = false
separability_search_authorized = false
label_deployment_authorized = false
```

`search_accounting_status = pass` iff all fields match this frozen block; otherwise fail closed。

## 15. Tests

必须至少覆盖：

```text
test_16a_authorization_requires_ready_decision_and_named_16b_next_requirement
test_16a_authorization_requires_all_hard_gates_pass
test_sampling_unit_inherits_nonoverlap_full_horizon_steps_only
test_step_materialization_rebuilds_row_level_steps_from_episode_intervals
test_step_materialization_counts_match_16a_horizon_grid_readout
test_16a_step_geometry_panel_is_not_treated_as_row_level_step_source
test_partial_tail_steps_are_excluded_from_labelable_population
test_qfq_price_source_is_required_for_label_construction
test_qfq_missing_bad_close_or_bounds_fail_closed
test_validation_is_stress_readout_and_not_primary_gate
test_primary_horizon_frozen_at_20
test_horizon_5_8_13_15_are_sensitivity_only
test_label_rule_primary_uses_drawdown_and_nonnegative_end_condition
test_primary_label_negative_uses_deep_drawdown_threshold
test_primary_label_neutral_is_neither_positive_nor_negative
test_label_base_rates_use_step_denominator_not_anchor_denominator
test_effective_sample_support_uses_nonoverlap_full_step_counts
test_effective_sample_support_requires_robustness_negative_sample_floor
test_train_robustness_stability_uses_absolute_base_rate_deltas
test_validation_sparse_adds_caveat_without_blocking_primary_decision
test_known_failed_context_exposure_caveat_does_not_block_ready_decision
test_known_failed_overlap_missing_artifact_fails_closed
test_known_failed_family_names_must_match_15b_path_type_enum
test_known_failed_projection_required_columns_must_exist_before_scoring
test_primary_known_failed_projection_uses_15b_path_type_only
test_15c2_soft_membership_partial_coverage_adds_caveat_without_hard_fail
test_secondary_label_does_not_enter_any_gate_or_decision_field
test_known_failed_projection_uses_cluster_descriptor_and_step_denominator
test_cluster_descriptor_projection_is_not_step_local_morphology_gate
test_15b_hard_projection_low_anchor_coverage_fails_closed
test_14a_aggregate_context_cannot_drive_primary_overlap_gate
test_stress_label_generation_lineage_sanity_threshold
test_threshold_sensitivity_does_not_change_primary_decision
test_no_entry_exit_holding_cost_or_portfolio_columns_are_emitted
test_search_accounting_never_authorizes_signal_model_or_deployment
test_ready_decision_only_authorizes_16c_separability_diagnostic
```

Synthetic fixtures 至少包含：

```text
one long episode with multiple h20 steps and mixed positive/negative/neutral labels
one partial-tail step that must be excluded
one validation-only sparse stress slice
one robustness split with base-rate drift beyond threshold
one robustness split with negative_effective_sample_size below 50
one known-failed context exposure panel that produces a non-blocking caveat
one missing known-failed artifact case that fails closed
one known-failed family enum mismatch case that fails closed before overlap scoring
one known-failed projection panel missing a required column that fails closed before scoring
one 15C2 soft membership partial coverage case that produces caveat without hard fail
one threshold sensitivity case where up100/up150 differs but primary up50 decision is unchanged
```

## 16. Implementation Notes

```text
1. 16B 只设计和审计 continuation label，不寻找 t0 features。
2. 任何 price movement statistic 只能用于 label construction，不得写成 trading return、alpha 或收益。
3. primary denominator 必须是 non-overlap full-horizon step，不是 anchor。
4. validation 是 stress-test readout，不进入 train/robustness primary stability gate。
5. known-failed overlap 是 hard guard；无法评估时 fail closed。
6. 即使 16B ready，也只授权 16C separability diagnostic。
7. 16C 若启动，必须复用 16A/16B 的 effective-sample 去重，不得用 step row count 高估功效。
```

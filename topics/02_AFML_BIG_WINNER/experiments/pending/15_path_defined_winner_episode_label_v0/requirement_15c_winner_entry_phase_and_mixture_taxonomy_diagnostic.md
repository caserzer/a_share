# 需求：15C Winner Entry Phase and Mixture Taxonomy Diagnostic

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/15_path_defined_winner_episode_label_v0
SOURCE_EP14_ROOT = TOPIC_ROOT/experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0
SOURCE_EP13_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 以 `SOURCE_EP14_ROOT/`、`SOURCE_EP13_ROOT/` 表达的路径必须先解析到对应 episode root，再写入 `input_artifact_audit.csv`。
5. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
6. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、universe membership 不可证明、price path completeness 不可证明、episode clustering 不可证明、entry-phase provenance 不可证明、PIT/outcome phase 分类不可证明、mixture rule provenance 不可证明时 fail closed。
7. 不得从报告文本、图像、人工讨论文本、聚合 readout 或未来标签反推出逐行 universe、episode membership、label、split 边界、entry 价格、entry-phase 或 decision point。

## 1. 实验身份

```text
experiment_id = 15_path_defined_winner_episode_label_v0
phase_id = 15C
run_id = 15C_winner_entry_phase_and_mixture_taxonomy_diagnostic
status = draft_ready_for_review
expected_entrypoint = src/run_15c_winner_entry_phase_and_mixture_taxonomy_diagnostic.py
expected_config = configs/config_15c_winner_entry_phase_and_mixture_taxonomy_diagnostic.yaml
expected_test_file = tests/test_15c_winner_entry_phase_and_mixture_taxonomy_diagnostic.py
source_plan = EXPERIMENT_ROOT/research_plan.md
upstream_requirement_15a = EXPERIMENT_ROOT/requirement_15a_winner_episode_label_censoring_diagnostic.md
upstream_requirement_15b = EXPERIMENT_ROOT/requirement_15b_winner_path_shape_taxonomy_diagnostic.md
```

15C 是 Episode 15 在 15B 之后插入的 label-form diagnostic。它**取代**研究计划里原本设想的 `15C_path_shape_label_separability_diagnostic`。原因是 15B 的裁决为 `15B_no_stable_path_shape_taxonomy`，其最关键的失败信号不是 quantile 阈值不准，而是 **统计单元太粗**：

```text
同一个 winner_episode_cluster 内部，不同 entry anchor 的 realized path type 经常不同。
representative_taxonomy_disagreement_share = 0.7320。
1459 个 up50 cluster 中，只有 339 个是单一 path type；约 76.8% 含 2 个以上 path type，
约 61.9% 含 3 个以上；cluster_internal_path_type_entropy median = 0.6744、p75 = 0.8070。
```

15C 的目标**不是**预测 winner，也**不是**寻找 entry，也**不是** separability。15C 只回答一个更前置的 label-form 问题：

```text
如果把 winner 从 binary outcome 拆成
  outcome 层（是否达到 +50/+100/+150）
  + threshold 层（三档阈值分开，不外推）
  + entry-phase 层（同一段行情，从不同 entry phase 进入的路径体验不同）
  + path-quality 层（在 entry-phase 子段上重算的形态质量），
那么 entry-phase 切分能否显著降低 cluster 内部的 path-type 异质性，
并产生覆盖率更高、跨 split 更稳定、且明显优于随机切分基线的 mixture taxonomy？
```

15C 不得产生任何交易、仓位、alpha、entry、meta-labeling、模型、separability 测试或 label 部署授权。即使 15C 通过，也只能授权后续新建：

```text
requirement_15d_capture_friendly_winner_separability_diagnostic.md
```

## 2. 背景判断与四层框架

### 2.1 15B 留下的结构性问题

15B 已经证明 realized path shape 不是随机噪音（smooth / late_rescue / stair_step / choppy 的指标中位数符合经济直觉），但同时证明：

```text
1. winner_episode_cluster 这个统计单元内部本身就是混合形态，medoid 单点代表不充分；
2. aggregate path-type 分布跨 split 表面稳定（JS divergence 极低），但 micro-level 单元高度分歧；
3. 阈值越高，late_rescue / stair_step 占比越高、smooth 占比越低，up50 形态不能外推到 up100 / up150；
4. tradable shape share 只有 30.25%、smooth_trend 只有 12.08%，直接做预测标签会把 label noise 灌进模型。
```

因此 15C 不在 15B 的 quantile rule 上做微调，而是**改变统计单元的粒度**。

### 2.2 四层框架（冻结）

15C 把 winner 显式拆成四层，且层与层之间的依赖顺序冻结，不得调换：

```text
Layer 1 Outcome:
  path_defined_winner = 是否最终达到阈值（继承 15A path_winner）。
  只回答 outcome，不回答路径质量、不回答可预测性。

Layer 2 Threshold:
  up50pct / up100pct / up150pct 必须分开处理与报告。
  不得把任一阈值的 entry-phase / path-quality 结构外推到其它阈值。

Layer 3 Entry-phase:
  不再用单一 earliest / shortest / medoid 代表整个 cluster。
  把 cluster 内 path_winner anchor 按 entry phase 切分，
  使同一段大行情可以同时包含不同 entry phase 的不同路径体验。

Layer 4 Path-quality:
  在 entry-phase 切分之后，对每个 (phase, anchor) 子段重算形态质量，
  再在 cluster 层做 mixture taxonomy。
  不得先对整段 / medoid 算 quality 再按 phase 分组。
```

### 2.3 不可违反的因果顺序（本实验的核心纪律）

15B 的 bug 是：先对整段 / medoid 算 path-quality，再发现 anchor 之间不一致。15C 必须反过来：

```text
path-quality 不是 episode 的属性，而是 (entry_phase x anchor) 的属性。

entry_phase 决定了 "从哪开始看这段路径"
  -> 不同 entry_phase 对应不同 path segment
  -> path-quality 只能在该 segment 上定义与计算。
```

因此 path-quality 必须在 entry-phase 切分之后、在每个 anchor 自己的 segment（`entry_pos -> first_threshold_hit_pos`）上计算，绝不允许用整段或单一 medoid segment 反推 anchor 的 path-quality。15C 复用 15B 已计算的 **anchor-level** path shape（每个 anchor 在自己 segment 上的形态），不复用 15B 的 **episode-level / medoid** path shape 作为 path-quality 来源。

## 3. 相对 15B `next_allowed_requirement = none` 的重新授权论证

15B 的裁决为 `15B_no_stable_path_shape_taxonomy`，输出：

```text
next_allowed_requirement = none
label_deployment_authorized = False
signal_search_authorized = False
```

15C 的启动依据必须显式论证，否则违反本 topic 的 fail-closed 纪律：

```text
1. 15B 真正被证实的不是 "path shape 不可分"，而是 "winner_episode_cluster 单元太粗，
   medoid 单点代表无法刻画 cluster 内部的混合形态"。
   15B 所有 hard gate（input/lineage/price_path/adapter/rebuild/episode_cluster/
   train_rule_fit/search_accounting）均 pass，失败发生在 taxonomy support / stability 层，
   且最强失败信号是 representative_taxonomy_disagreement_share = 0.7320。

2. 15B 报告第 10 节的 insight 明确指向 "把 cluster 切成更细的 entry-zone / phase"。
   15C 正是把该 insight 结构化为可证伪实验，而不是在被否定的 medoid 单元上重试。

3. 15B 否定的是 "用 cluster-medoid 单元能稳定分出 path type"，
   不是 "用 entry-phase 子单元能稳定分出 path type"。
   前者的否定不能传递为后者的否定。

4. 15C 的启动依据 = 15B 已证实的 unit-granularity 不足（label-form 问题），
   而不是 15B 未授权的 separability。15C 不复活 15B 未授权的 entry / signal / model；
   它只在 label 定义层把统计单元从 cluster 细化到 (entry_phase x anchor)。
```

该论证必须在 15C report 中复述，并在 `search_accounting_audit.csv` 以
`startup_authorization_basis = 15B_unit_granularity_insufficiency_not_15B_separability_block` 记录。

## 4. 核心问题

15C 回答以下问题：

```text
Q1. 把 cluster 内 path_winner anchor 按 entry phase 切分后，
    cluster 内部的 path-type 异质性（representative_disagreement / internal_entropy）
    是否相对 15B 的 cluster-medoid 单元显著下降？

Q2. entry-phase 切分带来的 dominant-share 上升，是否显著优于
    "把同一 cluster 的 anchor 随机切成同样大小子段" 的随机切分基线？
    即：异质性下降是真实结构，还是仅仅因为子段样本变小的统计假象？

Q3. PIT-observable entry-phase 与 outcome-relative entry-phase 哪一种更能降低异质性？
    两者对 dominant-share / coverage / cross-split stability 的影响如何并列对比？

Q4. mixture taxonomy（cluster 输出 path-type 分布向量 + dominant_type + dominant_share +
    internal_entropy，只有 dominant_share 足够高才贴单一 subtype，否则 mixed_episode_winner）
    能否同时：降低 unclassified / mixed share、提升单一 subtype 覆盖率、
    在 train / validation / robustness 都形成 material path-quality groups？

Q5. 哪些 (threshold, entry_phase, path_quality) 组合可以成为后续 separability 的候选 label primitive？
    哪些只能作为 descriptive readout？
```

必须输出一个单一裁决：

```text
decision_state
```

## 5. Scope Boundary

15C 允许做：

```text
1. 复用 15A / 15B / 14A / 13A 的 universe lineage、split boundary、path-defined label、
   winner episode cluster 与 anchor-level path shape feature panel；
2. 在每个 anchor 上同时计算 PIT-observable entry-phase 与 outcome-relative entry-phase；
3. 在 entry-phase 子段上引用 anchor-level path-quality（来自 15B anchor 面板，或按 15B 冻结公式重建）；
4. 在 cluster 层做 mixture taxonomy（分布向量 / dominant / internal entropy）；
5. 用 train-only 分位数与冻结规则做 deterministic mixture taxonomy；
6. 构造随机切分基线（random equal-size sub-segment）作为异质性下降的对照；
7. 将冻结规则应用到 validation / robustness / all，做 readout-only stability 检查；
8. 输出确定性 next-research decision map。
```

15C 明确不是：

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

15C 可以使用未来 price path 来描述已发生的 winner path（label diagnostic 允许）；但任何与后续 prediction / entry 有关的字段都必须标记为 out of scope，且 outcome-relative entry-phase 永远不得被升级为 t0 feature（见 §7.3）。

## 6. 继承边界

### 6.1 允许继承

15C 继承 15A / 15B 的以下定义：

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
winner_episode_cluster 定义与 transitive overlap clustering（继承 15B §6.2）
anchor-level path shape feature 定义（继承 15B §8）
```

15C 必须读取以下上游 artifacts：

```text
EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/winner_path_shape_taxonomy_decision.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_taxonomy_rule_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/winner_episode_cluster_membership_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/representative_anchor_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/split_overlap_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/search_accounting_audit.csv
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_universe_panel.parquet
```

15C 可以使用 15A / 15B local cache 作为加速输入与对照，但 local cache 不能绕过 publishable audit。`taxonomy_assignment_panel.parquet`
是 anchor-level `path_type` 的首选来源；若不存在或 schema 不匹配，runner 必须用
`anchor_path_shape_feature_panel.parquet + path_shape_taxonomy_rule_audit.csv` 复现 15B frozen path type。

```text
EXPERIMENT_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/anchor_path_shape_feature_panel.parquet
EXPERIMENT_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/winner_episode_cluster_panel.parquet
EXPERIMENT_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/taxonomy_assignment_panel.parquet
EXPERIMENT_ROOT/outputs/local_cache/15A_winner_episode_label_censoring_diagnostic/path_defined_label_panel.parquet
```

PIT-observable entry-phase 所需的 t0-close morphology 字段来自 13A `add_daily_features`，只能使用 `reference_pos` 及之前的数据：

```text
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_universe_panel.parquet
所需字段（PIT-observable，t0 可见）：
  distance_to_60d_high, distance_to_20d_high, distance_to_20d_low,
  ret_20d, ret_60d, trend_ma_20_60_spread, rebound_from_20d_low,
  vol_compression_20d_60d, volatility_20d
```

如果 15B anchor-level path shape cache 不存在或 schema 不匹配，15C runner 必须按 15B §8 冻结公式从 raw qfq bars 重建 anchor segment 上的 path-quality，不得从 15B 聚合表反推逐行 path-quality。

### 6.1.1 15B anchor-level adapter freeze

15C 若读取 15B anchor cache，必须使用以下 adapter，不得重新猜字段名。`anchor_path_type` 来源优先级冻结为：

```text
  priority 1:
  EXPERIMENT_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/taxonomy_assignment_panel.parquet
  required columns:
    source_row_key, instrument, reference_date, row_id, split_bucket, threshold_id,
    episode_cluster_id, cluster_split_bucket, entry_pos, first_threshold_hit_pos,
    time_to_threshold_sessions, path_efficiency, max_drawdown_before_hit,
    max_drawdown_before_hit_abs, underwater_days_share, directional_entropy_5state, trend_line_r2,
    top1_positive_gain_share, top3_positive_gain_share, log_time_to_threshold,
    path_type, path_shape_quality, wick_hit_only

priority 2:
  EXPERIMENT_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/anchor_path_shape_feature_panel.parquet
  + EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_taxonomy_rule_audit.csv
  required action:
    apply 15B frozen deterministic rule exactly to reproduce path_type.

priority 3:
  rebuild anchor path shape from qfq bars using 15B frozen formulas, then apply 15B frozen deterministic rule.
```

无论使用哪种来源，runner 必须再与 `winner_episode_cluster_membership_audit.csv`
按 `source_row_key` 或 `(instrument, reference_date, row_id, threshold_id)` 回填 cluster interval 字段：

```text
cluster_start_pos
cluster_end_pos
touches_multiple_split_buckets
touches_multiple_calendar_split_buckets
```

最终 adapter 字段映射冻结为：

```text
source_row_key = (instrument, reference_date, row_id, threshold_id)

15C.anchor_path_efficiency          <- 15B.path_efficiency
15C.anchor_max_drawdown_before_hit  <- 15B.max_drawdown_before_hit
15C.anchor_max_drawdown_abs         <- 15B.max_drawdown_before_hit_abs
15C.anchor_underwater_days_share    <- 15B.underwater_days_share
15C.anchor_directional_entropy      <- 15B.directional_entropy_5state
15C.anchor_trend_line_r2            <- 15B.trend_line_r2
15C.anchor_top1_gain_share          <- 15B.top1_positive_gain_share
15C.anchor_top3_gain_share          <- 15B.top3_positive_gain_share
15C.anchor_large_up_day_count       <- 15B.large_up_day_count
15C.anchor_pullback_5pct_count      <- 15B.pullback_5pct_count
15C.anchor_time_to_threshold        <- 15B.time_to_threshold_sessions
15C.anchor_log_time_to_threshold    <- 15B.log_time_to_threshold
15C.anchor_segment_sessions         <- 15B.segment_sessions
15C.anchor_path_type                <- 15B.taxonomy_assignment_panel.path_type
15C.anchor_wick_hit_only            <- 15B.wick_hit_only
15C.episode_cluster_id              <- 15B.episode_cluster_id
15C.cluster_split_bucket            <- 15B.cluster_split_bucket
15C.cluster_start_pos               <- 15B.winner_episode_cluster_membership_audit.cluster_start_pos
15C.cluster_end_pos                 <- 15B.winner_episode_cluster_membership_audit.cluster_end_pos
```

`anchor_path_type` 必须沿用 15B 冻结的 deterministic taxonomy rule（含 precedence、smooth_overrides_jump、missing policy），不得在 15C 重新定义 path-quality predicate。15C 只新增 entry-phase 切分与 cluster-level mixture 聚合。若 adapter 必需字段缺失、`source_row_key` 非唯一、cluster interval 不能回填、或 `anchor_path_type` 不可由 15B rule audit 复现，`path_quality_adapter_gate` 必须 fail closed。

15C 必须输出 adapter audit：

```text
source_row_key
adapter_source_path
adapter_source_priority
adapter_required_columns_present
adapter_anchor_path_type_reproducible
adapter_cluster_interval_backfilled
adapter_row_count
adapter_duplicate_source_row_key_n
adapter_status
```

若 priority 1 或 priority 2 成功，`path_quality_rebuild_audit.csv` 仍必须输出一行：

```text
rebuild_attempted = false
rebuild_status = not_required_pass
rebuild_skip_reason = adapter_or_rule_reproduction_passed
```

若需要 priority 3 重建，则 `rebuild_status` 只能为 `pass` 或 `fail`。Hard gate allowlist：

```text
path_quality_adapter_audit.adapter_status in {pass}
path_quality_rebuild_audit.rebuild_status in {pass, not_required_pass}
```

15B medoid representative 所需 feature 与 scaler 来源冻结如下；15C 不得从 code introspection 动态猜测：

```text
MEDOID_FEATURES_15B =
  path_efficiency
  max_drawdown_before_hit_abs
  underwater_days_share
  directional_entropy_5state
  trend_line_r2
  top1_positive_gain_share
  top3_positive_gain_share
  log_time_to_threshold

medoid_scaler_source =
  path_shape_taxonomy_rule_audit.csv rows where rule_type == medoid_scaler

medoid_scaler_missing_policy =
  missing feature values are filled with the scaler center for that feature,
  matching 15B standardized_matrix behavior.
```

### 6.2 不得继承为结论

15C 不得把以下上游结论直接当成 15C 结论：

```text
15B.decision_state
15B.next_allowed_requirement
15B.tradable_shape_share
15B.representative_taxonomy_disagreement_share
15A.next_allowed_requirement
label_deployment_authorized
signal_search_authorized
```

这些字段只能作为背景与 fail-closed guard。15C 必须基于 entry-phase 子单元的 mixture taxonomy 自己产生裁决。

## 7. Entry Phase 定义

### 7.1 Primary unit 与 phase 切分对象

15C 的 primary diagnostic unit 是：

```text
primary_count_unit = winner_episode_cluster
secondary_count_unit = (episode_cluster_id, entry_phase, anchor)
```

但与 15B 不同，cluster 的 subtype 不再由单一 medoid 决定，而由 cluster 内 anchor 经 entry-phase 切分后的 path-type 分布决定（见 §8 mixture）。

`path_winner = false` 或 `is_censored = true` 的 row 不进入 entry-phase / mixture taxonomy，只进入 censoring / non-hit readout。

Primary fit / gate population 冻结为：

```text
eligible_primary_anchor =
  path_winner == true
  and is_censored == false
  and cluster_split_bucket in {train, validation, robustness}
  and touches_multiple_split_buckets == false
  and touches_multiple_calendar_split_buckets == false
  and path_shape_quality == pass

train_rule_fit_population = eligible_primary_anchor where cluster_split_bucket == train
validation_gate_population = eligible_primary_anchor where cluster_split_bucket == validation
robustness_gate_population = eligible_primary_anchor where cluster_split_bucket == robustness

primary_support_gate_population =
  eligible_primary_anchor
  where threshold_id == selected_threshold_id

primary_improvement_population =
  primary_support_gate_population
  where cluster_split_bucket == train

primary_confirmation_population =
  primary_support_gate_population
  where cluster_split_bucket in {validation, robustness}
```

`cluster_split_bucket = cross_split` 或任何 split-boundary touching cluster 只能进入
`cross_split_readout` / report appendix，不得参与 train quantile、entry-phase rule fit、
random baseline primary metric、support gate 或 decision。若 runner 把 cross-split rows
混入 primary gate，`entry_phase_rule_fit_gate` 必须 fail closed。

`up100pct` / `up150pct` 必须完整输出 threshold sensitivity readout，但不得触发 primary
support decision 或 15D authorization。若非 selected threshold 指标改变 primary decision，
`search_accounting_gate` 必须 fail closed。

### 7.2 两种 entry-phase 口径必须并列计算

15C 必须对每个 path_winner anchor 同时计算两套 entry-phase 标签，并列对比：

```text
entry_phase_pit       基于 PIT-observable t0-close 状态（entry 当天及之前可见）
entry_phase_outcome   基于 anchor 在所属 cluster interval 中的相对位置（事后量）
```

两套都进入 readout 与 gate；但只有 PIT-observable scheme 能授权 15D。Outcome-relative scheme
即使显著改善，也只能产生 descriptive / label-form insight，不能单独触发
`15C_entry_phase_mixture_supported_for_separability`。

### 7.3 PIT-observable entry-phase（可升级为后续 feature）

PIT-observable phase 只使用 `reference_pos` 及之前可见的 13A morphology 字段，train-only 分位数冻结切点。字段 missing 或非 finite 时，该 anchor 的 `entry_phase_pit = undetermined_pit`，并在 `entry_phase_rule_audit.csv` 记录 missing count。

```text
entry_phase_pit in {
  early_base_pit
  mid_trend_pit
  breakout_pit
  late_chase_pit
  undetermined_pit
}
```

PIT phase predicate 必须由 train-only quantiles 展开成布尔表达式（与 15B §9 同纪律），写入 `entry_phase_rule_audit.csv`。所有 PIT phase 仅使用 t0 可见字段，因此 **可在后续 15D 升级为 t0 feature**。

冻结所需 train quantiles（至少）：

```text
q_ret60d_30 / 50 / 70
q_distance_to_60d_high_70 / 90
q_distance_to_20d_low_30 / 70
q_trend_ma_20_60_spread_50
```

冻结 PIT predicate 与优先级：

```text
predicate_late_chase_pit =
  ret_60d >= q_ret60d_70
  and distance_to_20d_low >= q_distance_to_20d_low_70

predicate_breakout_pit =
  distance_to_60d_high >= q_distance_to_60d_high_90
  and not predicate_late_chase_pit

predicate_early_base_pit =
  ret_60d <= q_ret60d_30
  and distance_to_20d_low <= q_distance_to_20d_low_30
  and distance_to_60d_high < q_distance_to_60d_high_70

predicate_mid_trend_pit =
  ret_60d > q_ret60d_50
  and trend_ma_20_60_spread >= q_trend_ma_20_60_spread_50
  and distance_to_60d_high < q_distance_to_60d_high_90
  and not predicate_late_chase_pit
  and not predicate_breakout_pit

priority:
  1. late_chase_pit
  2. breakout_pit
  3. early_base_pit
  4. mid_trend_pit
  5. undetermined_pit
```

若多个 predicate 同时为 true，按 priority 取第一个，并把所有命中的 predicate 写入
`entry_phase_rule_audit.csv` 的 conflict flag。`undetermined_pit` 不得被算作
single-subtype coverage，也不得成为 15D candidate phase。

### 7.4 Outcome-relative entry-phase（永远只能是 diagnostic descriptor）

Outcome-relative phase 使用 anchor 在所属 cluster interval 的相对位置，属于事后量：

```text
cluster_progress = (anchor.entry_pos - cluster_start_pos) / max(cluster_end_pos - cluster_start_pos, 1)

entry_phase_outcome in {
  early_cluster_entry      cluster_progress <= 0.25
  mid_cluster_entry        0.25 < cluster_progress <= 0.60
  breakout_cluster_entry   0.60 < cluster_progress <= 0.80
  late_cluster_entry       cluster_progress > 0.80
}
```

`entry_phase_outcome` 因为使用了 cluster interval（含未来信息），**永远不得升级为 t0 feature**，只能作为 label-form diagnostic descriptor。15C 必须在 `entry_phase_rule_audit.csv` 标记：

```text
entry_phase_pit.upgradeable_to_t0_feature = true
entry_phase_outcome.upgradeable_to_t0_feature = false
```

若 runner 将 outcome-relative phase 写入任何 "feature candidate" 输出，`entry_phase_provenance_gate` 必须 fail closed。

## 8. Mixture Taxonomy

### 8.1 Sub-segment path-quality

对每个 (episode_cluster_id, entry_phase, anchor)，path-quality = 该 anchor 自己 segment 上的 `anchor_path_type`（来自 §6.1.1 adapter，沿用 15B 冻结 rule）。15C 不重新定义 path-quality predicate。

path-quality 取值沿用 15B：

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

### 8.2 Phase-conditioned cluster mixture vector

对每个 cluster，按每种 entry-phase 口径分别计算 phase-conditioned mixture：

```text
对 (episode_cluster_id, phase_scheme, entry_phase_value):
  anchor_n
  path_type_distribution_vector   各 path-quality 的占比向量
  dominant_path_type
  dominant_share
  distinct_path_type_n
  internal_entropy = -sum(p_type * ln(p_type)) / ln(max(distinct_type_n, 2))
  subgroup_earliest_anchor_path_type
  subgroup_shortest_duration_anchor_path_type
  subgroup_medoid_anchor_path_type
  subgroup_representative_disagreement
```

`phase_scheme in {pit, outcome}`。

Subgroup representative disagreement 沿用 15B 的 representative 思路，但在每个 phase subgroup 内重算：

```text
subgroup_earliest_anchor = subgroup anchor with min(entry_pos, row_id)
subgroup_shortest_duration_anchor = subgroup anchor with min(time_to_threshold_sessions, entry_pos, row_id)
subgroup_medoid_anchor = subgroup medoid on 15B MEDOID_FEATURES using 15B medoid scaler

subgroup_representative_disagreement =
  len(unique({
    subgroup_earliest_anchor.path_type,
    subgroup_shortest_duration_anchor.path_type,
    subgroup_medoid_anchor.path_type
  })) > 1
```

`representative_disagreement_share_phased` 定义为 eligible phase subgroup 的 anchor-weighted
`subgroup_representative_disagreement` share。为了避免与 15B cluster-level baseline 权重不一致，
15C 必须在同一个 `primary_improvement_population` 上重算 baseline 与 phased 两套权重：

```text
baseline_representative_disagreement_share_anchor_weighted =
  15B representative disagreement mapped back to all eligible anchors,
  then averaged with anchor weight = 1.

phased_representative_disagreement_share_anchor_weighted =
  subgroup_representative_disagreement mapped back to all eligible anchors
  inside eligible phase subgroups, then averaged with anchor weight = 1.

disagreement_reduction_anchor_weighted =
  baseline_representative_disagreement_share_anchor_weighted
  - phased_representative_disagreement_share_anchor_weighted
```

Cluster-weighted baseline / phased disagreement 可以输出为 appendix readout，但 primary support gate
只能使用 anchor-weighted version。若 baseline 与 phased 使用不同 denominator 或不同权重，
`mixture_rule_fit_gate` 必须 fail closed。

### 8.3 Subtype 贴标规则

只有当某 (cluster, phase_scheme, entry_phase_value) 子组的 dominant_share 足够高，才允许贴单一 subtype：

```text
dominant_share_threshold = 0.70   （train-only 冻结，预注册，不得用 val/robustness 事后改）
min_phase_subgroup_anchor_n = 10   （预注册，小于该值只进入 sparse readout）

if anchor_n < min_phase_subgroup_anchor_n:
    subtype = sparse_phase_subgroup
elif dominant_share >= dominant_share_threshold and dominant_path_type not in unclassified_*:
    subtype = dominant_path_type
else:
    subtype = mixed_episode_winner
```

`dominant_share_threshold` 与 `min_phase_subgroup_anchor_n` 必须写入 `mixture_rule_audit.csv`。15C 必须同时输出 `0.75` 的敏感性读数，但 primary 用 `0.70`。`sparse_phase_subgroup` 不得算作 single subtype coverage；在 coverage denominator 中按 residual / unresolved 处理，并单独输出 sparse share。

### 8.4 Cluster-level 汇总

每个 cluster 在每种 phase_scheme 下，汇总其所有 entry_phase 子组的 subtype，输出：

```text
cluster_subtype_set                 cluster 内出现的 subtype 集合
cluster_phase_resolved              是否存在至少一个非 mixed 的 phase 子组
cluster_single_subtype_after_phase  cluster 内非 mixed subtype 是否唯一
cluster_residual_mixed_share        仍为 mixed_episode_winner 的 anchor 占比
```

## 9. 随机切分对照基线（核心防伪）

entry-phase 切分会减少每个子组的 anchor 数，dominant_share 可能仅因样本变小而机械上升。15C 必须构造随机切分基线，证明异质性下降是真实结构而非样本变小假象。

### 9.1 基线构造

```text
对每个 cluster，在每种 phase_scheme 下：
  记录该 scheme 真实切出的各 entry_phase 子组 anchor_n 序列 = size_profile。
  random baseline：把同一 cluster 的 anchor 随机置换后，按相同 size_profile 切成同样大小的子组。
  random_seed = 冻结常数（写入 mixture_rule_audit.csv），重复 random_repeat_n = 20 次取均值。
```

随机切分只打乱 anchor → 子组的分配，不改变 cluster 成员、不改变 anchor 的 path-quality。

### 9.2 对照指标

```text
eligible_for_random_metric =
  phase subgroup anchor_n >= min_phase_subgroup_anchor_n
  and cluster_split_bucket in {train, validation, robustness}
  and not cross_split

subgroup_weight = anchor_n

mean_dominant_share_phase        anchor-weighted mean dominant_share over eligible subgroups
mean_dominant_share_random       anchor-weighted mean dominant_share over eligible random subgroups
dominant_share_uplift_vs_random  = mean_dominant_share_phase - mean_dominant_share_random

mean_internal_entropy_phase
mean_internal_entropy_random
internal_entropy_reduction_vs_random = mean_internal_entropy_random - mean_internal_entropy_phase

sparse_phase_subgroup_share      anchor share excluded because anchor_n < min_phase_subgroup_anchor_n
```

不得使用 subgroup 等权平均作为 primary metric；subgroup 等权只能作为 appendix readout。

输出到：

```text
phase_split_vs_random_baseline_readout.csv
```

### 9.3 真实性判据

phase 切分只有在显著优于随机切分时才算 "真实降低异质性"：

```text
phase_split_is_real(pit / outcome) =
  dominant_share_uplift_vs_random >= 0.10
  and internal_entropy_reduction_vs_random >= 0.10
```

该判据进入 §12 support gate。若两种 phase_scheme 都不满足 `phase_split_is_real`，则 entry-phase 切分被判定为无效，decision 不得为 supported。

## 10. Required Outputs

### 10.1 Publishable tables

输出到：

```text
outputs/publishable/tables/15C_winner_entry_phase_and_mixture_taxonomy_diagnostic/
```

Required tables：

```text
input_artifact_audit.csv
upstream_lineage_audit.csv
price_path_completeness_audit.csv
path_quality_adapter_audit.csv
path_quality_rebuild_audit.csv
entry_phase_rule_audit.csv
entry_phase_assignment_readout.csv
phase_conditioned_mixture_readout.csv
mixture_rule_audit.csv
cluster_subtype_readout.csv
phase_split_vs_random_baseline_readout.csv
disagreement_before_after_phase_readout.csv
coverage_before_after_phase_readout.csv
mixture_by_split_readout.csv
mixture_by_threshold_sensitivity_readout.csv
pit_vs_outcome_phase_comparison_readout.csv
mixture_stability_gate.csv
winner_entry_phase_mixture_decision.csv
search_accounting_audit.csv
```

### 10.1.1 关键表最小字段

`path_quality_rebuild_audit.csv` 至少包含：

```text
rebuild_attempted
rebuild_status
rebuild_skip_reason
rebuild_formula_source = 15B_frozen_path_shape_formula
rebuild_row_count
rebuild_duplicate_source_row_key_n
rebuild_required_columns_present
```

`entry_phase_rule_audit.csv` 至少包含：

```text
phase_scheme
rule_id
fit_split = train
fit_population_filter
fit_population_n
feature_id
quantile_name
quantile_value
predicate_expression
predicate_priority
missing_feature_count
conflict_policy
upgradeable_to_t0_feature
cross_split_excluded_from_fit
entry_phase_rule_fit_status
entry_phase_provenance_status
```

`entry_phase_assignment_readout.csv` 至少包含：

```text
source_row_key
threshold_id
instrument
reference_date
row_id
split_bucket
cluster_split_bucket
episode_cluster_id
entry_pos
cluster_start_pos
cluster_end_pos
entry_phase_pit
entry_phase_pit_predicate_hits
entry_phase_pit_missing_feature_flag
entry_phase_outcome
cluster_progress
entry_phase_pit_upgradeable_to_t0_feature
entry_phase_outcome_upgradeable_to_t0_feature
phase_assignment_status
primary_gate_eligible
```

`phase_conditioned_mixture_readout.csv` 至少包含：

```text
threshold_id
split_bucket
phase_scheme
entry_phase_value
episode_cluster_id
anchor_n
eligible_phase_subgroup
sparse_phase_subgroup
distinct_path_type_n
path_type_distribution_vector
dominant_path_type
dominant_share
internal_entropy
subgroup_earliest_anchor_path_type
subgroup_shortest_duration_anchor_path_type
subgroup_medoid_anchor_path_type
subgroup_representative_disagreement
subtype_0p70
subtype_0p75
subtype_assignment_status
```

`mixture_rule_audit.csv` 至少包含：

```text
dominant_share_threshold_primary
dominant_share_threshold_sensitivity
min_phase_subgroup_anchor_n
subgroup_weighting = anchor_weighted
unclassified_policy
sparse_policy
random_baseline_seed
random_baseline_repeat_n
cross_split_excluded_from_primary_gate
mixture_rule_fit_status
```

`cluster_subtype_readout.csv` 至少包含：

```text
threshold_id
split_bucket
phase_scheme
episode_cluster_id
cluster_anchor_n
cluster_subtype_set
cluster_phase_resolved
cluster_single_subtype_after_phase
cluster_residual_mixed_share
cluster_sparse_phase_anchor_share
cluster_outcome_only_descriptor_flag
```

`disagreement_before_after_phase_readout.csv` 至少包含：

```text
threshold_id
split_bucket
phase_scheme
primary_support_gate_threshold
primary_improvement_split
baseline_unit = cluster_medoid_15b
phased_unit = cluster_phase_subgroup_15c
representative_disagreement_share_baseline
representative_disagreement_share_phased
representative_disagreement_share_baseline_anchor_weighted
representative_disagreement_share_phased_anchor_weighted
internal_entropy_median_baseline
internal_entropy_median_phased
internal_entropy_p75_baseline
internal_entropy_p75_phased
disagreement_reduction
disagreement_reduction_anchor_weighted
eligible_phase_subgroup_n
sparse_phase_subgroup_share
subgroup_weighting = anchor_weighted
baseline_source = 15B_representative_anchor_audit
primary_gate_metric = anchor_weighted
```

`coverage_before_after_phase_readout.csv` 至少包含：

```text
threshold_id
split_bucket
phase_scheme
primary_support_gate_threshold
baseline_unclassified_or_mixed_share
single_subtype_coverage
mixed_share
sparse_phase_subgroup_share
capture_friendly_subtype_share
coverage_improvement
coverage_denominator = eligible_primary_anchor
```

`phase_split_vs_random_baseline_readout.csv` 至少包含：

```text
threshold_id
split_bucket
phase_scheme
primary_support_gate_threshold
random_baseline_seed
random_baseline_repeat_n
min_phase_subgroup_anchor_n
subgroup_weighting
eligible_phase_subgroup_n
mean_dominant_share_phase
mean_dominant_share_random
dominant_share_uplift_vs_random
mean_internal_entropy_phase
mean_internal_entropy_random
internal_entropy_reduction_vs_random
sparse_phase_subgroup_share
phase_split_is_real
random_baseline_status
```

`pit_vs_outcome_phase_comparison_readout.csv` 至少包含：

```text
threshold_id
metric
pit_value
outcome_value
better_scheme
pit_can_authorize_15d
outcome_can_authorize_15d = false
```

`mixture_stability_gate.csv` 至少包含：

```text
threshold_id
phase_scheme
primary_support_gate_threshold
eligible_train_phase_subgroup_n
single_subtype_coverage_train
mixed_share_train
material_subtype_n_train
material_subtype_n_validation
material_subtype_n_robustness
js_divergence_train_validation_subtype
js_divergence_train_robustness_subtype
phase_split_is_real
dominant_share_uplift_vs_random
internal_entropy_reduction_vs_random
sparse_phase_subgroup_share_train
pit_scheme_supported_for_15d
outcome_scheme_descriptive_supported
primary_gate_population_id
mixture_stability_status
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
validation_robustness_usage_detail
entry_phase_pit_upgradeable_to_t0_feature
entry_phase_outcome_upgradeable_to_t0_feature
random_baseline_seed
random_baseline_repeat_n
dominant_share_threshold
min_phase_subgroup_anchor_n
pit_scheme_required_for_15d
outcome_phase_can_authorize_15d
entry_search_authorized
signal_search_authorized
model_training_authorized
separability_search_authorized
search_accounting_status
```

### 10.2 Local cache

```text
outputs/local_cache/15C_winner_entry_phase_and_mixture_taxonomy_diagnostic/
```

Allowed：

```text
anchor_entry_phase_panel.parquet
phase_conditioned_mixture_panel.parquet
random_baseline_panel.parquet
```

Local cache 不能替代 publishable audit。

### 10.3 Report

输出到：

```text
outputs/publishable/reports/winner_entry_phase_mixture_taxonomy_diagnostic_report.md
```

Report 必须用中文写，至少包含：

```text
1. 单行裁决；
2. 为什么 15C 在 15B no-stable / next_allowed_requirement = none 后仍可启动（override 论证）；
3. 四层框架（outcome / threshold / entry-phase / path-quality）与不可违反的因果顺序；
4. PIT-observable 与 outcome-relative 两套 entry-phase 的定义、可升级性差异；
5. entry-phase 切分前后的 representative disagreement 与 internal entropy 对比；
6. 随机切分对照基线结果，以及异质性下降是否真实；
7. mixture taxonomy（dominant_share >= 0.70）下的 single-subtype coverage 与 mixed share；
8. 三档阈值各自的 mixture composition，强调不可外推；
9. 哪些 PIT-observable (threshold, phase, subtype) 组合可作为后续 15D separability 候选；
10. 哪些只能作为 descriptive / readout-only；
11. 为什么本实验仍不授权 signal search、entry、model、separability 或 label deployment。
```

## 11. Decision Gates

### 11.1 Hard fail gates

任一失败，decision 必须为：

```text
15C_blocked_input_or_lineage_failure
```

Hard fail conditions 与 gate source：

```text
input_artifact_gate            <- input_artifact_audit.csv.input_gate_status
upstream_lineage_gate          <- upstream_lineage_audit.csv.lineage_status
price_path_completeness_gate   <- price_path_completeness_audit.csv.price_path_status
path_quality_adapter_gate      <- path_quality_adapter_audit.csv.adapter_status
path_quality_rebuild_gate      <- path_quality_rebuild_audit.csv.rebuild_status
entry_phase_rule_fit_gate      <- entry_phase_rule_audit.csv.entry_phase_rule_fit_status
entry_phase_provenance_gate    <- entry_phase_rule_audit.csv.entry_phase_provenance_status
mixture_rule_fit_gate          <- mixture_rule_audit.csv.mixture_rule_fit_status
random_baseline_gate           <- phase_split_vs_random_baseline_readout.csv.random_baseline_status
search_accounting_gate         <- search_accounting_audit.csv.search_accounting_status
```

若某 audit 表为空、缺 status 字段、或 status 不在 allowlist 中，相关 gate 必须 fail closed。`entry_phase_provenance_gate` 在 outcome-relative phase 被写入任何 feature candidate 输出时必须 fail。

### 11.2 Support gates

若 hard fail gates 全部通过，分别对 PIT 与 outcome 两种 phase_scheme 评估；所有指标必须按
`threshold_id x split_bucket x phase_scheme` 输出。Primary support decision 只使用：

```text
threshold_id == selected_threshold_id
primary_improvement_split = train
primary_gate_metric = anchor_weighted
```

Validation / robustness 只能作为 no-fit support confirmation：冻结 train 规则后应用，不参与
quantile fit、threshold selection、dominant_share_threshold selection 或 phase_scheme selection。
只有 PIT scheme 可授权 15D。

```text
phase_scheme_real(scheme):
  phase_split_is_real(scheme, threshold_id = selected_threshold_id, split = train) == true

disagreement_materially_reduced(scheme):
  representative_disagreement_share_phased_anchor_weighted(
    scheme, threshold_id = selected_threshold_id, split = train
  ) <= 0.50
  and disagreement_reduction_anchor_weighted(
    scheme, threshold_id = selected_threshold_id, split = train
  ) >= 0.15
  （相对 15B baseline 0.7320 的实质下降）

coverage_improved(scheme):
  single_subtype_coverage_train(scheme, threshold_id = selected_threshold_id) >= 0.50
  and mixed_share_train(scheme, threshold_id = selected_threshold_id) <= 0.45
  and sparse_phase_subgroup_share_train(scheme, threshold_id = selected_threshold_id) <= 0.25

validation_robustness_material_confirmation(scheme):
  material_subtype_n_train(scheme, threshold_id = selected_threshold_id) >= 3
  and material_subtype_n_validation(scheme, threshold_id = selected_threshold_id) >= 2
  and material_subtype_n_robustness(scheme, threshold_id = selected_threshold_id) >= 2

scheme_supported(scheme):
  phase_scheme_real(scheme)
  and disagreement_materially_reduced(scheme)
  and coverage_improved(scheme)
  and validation_robustness_material_confirmation(scheme)

pit_scheme_supported_for_15d:
  scheme_supported(pit) == true

outcome_scheme_descriptive_supported:
  scheme_supported(outcome) == true
  and scheme_supported(pit) == false
```

`material_subtype` 按 split-specific denominator 定义，不得用 train 的绝对数量替代 validation / robustness：

```text
subtype_anchor_share_in_split >= 0.05
and subtype_phase_subgroup_n_in_split >= split_material_min_phase_subgroup_n
and threshold_id == selected_threshold_id for primary support gates

split_material_min_phase_subgroup_n:
  train = 50
  validation = 20
  robustness = 20
```

Outcome scheme 的 support 只能说明事后 entry-zone 切分有解释力。若只有 outcome scheme 通过，
decision 不得为 `15C_entry_phase_mixture_supported_for_separability`。

### 11.3 Stability readout（输出但不自动 hard block）

```text
js_divergence_train_validation_subtype
js_divergence_train_robustness_subtype
pit_vs_outcome_phase_better_scheme
dominant_share_threshold_sensitivity_0p70_vs_0p75
threshold_sensitivity_subtype_rank_stability
```

## 12. Decision Map

最终裁决只能取以下枚举之一：

```text
15C_entry_phase_mixture_supported_for_separability
15C_outcome_phase_only_descriptive_improvement
15C_entry_phase_reduces_heterogeneity_but_coverage_insufficient
15C_entry_phase_no_real_improvement_over_random
15C_inconclusive_too_sparse
15C_blocked_input_or_lineage_failure
```

Decision map 用到的 per-scheme 派生变量定义（与 `mixture_stability_gate.csv` 同源）：

```text
eligible_train_phase_subgroup_n_pit =
  mixture_stability_gate.csv.eligible_train_phase_subgroup_n
  where phase_scheme == pit and threshold_id == selected_threshold_id

eligible_train_phase_subgroup_n_outcome =
  mixture_stability_gate.csv.eligible_train_phase_subgroup_n
  where phase_scheme == outcome and threshold_id == selected_threshold_id
```

`mixture_stability_gate.csv.eligible_train_phase_subgroup_n` 始终按 `phase_scheme` 行取值（per-scheme），
不是跨 scheme 汇总。decision map 中所有 `_pit` / `_outcome` 后缀变量都按对应 phase_scheme 行解析。

Decision map：

```text
if any hard fail:
  decision_state = 15C_blocked_input_or_lineage_failure
  next_allowed_requirement = none

elif eligible_train_phase_subgroup_n_pit < 200 and eligible_train_phase_subgroup_n_outcome < 200:
  decision_state = 15C_inconclusive_too_sparse
  next_allowed_requirement = none

elif not any(phase_scheme_real(scheme) for scheme in {pit, outcome}):
  decision_state = 15C_entry_phase_no_real_improvement_over_random
  next_allowed_requirement = none

elif pit_scheme_supported_for_15d:
  decision_state = 15C_entry_phase_mixture_supported_for_separability
  next_allowed_requirement = requirement_15d_capture_friendly_winner_separability_diagnostic.md

elif outcome_scheme_descriptive_supported:
  decision_state = 15C_outcome_phase_only_descriptive_improvement
  next_allowed_requirement = none

else:
  # 至少一个 scheme phase_split_is_real（已通过上面的 no_real_improvement 分支），
  # 但既不满足 PIT full support，也不满足 outcome-only descriptive support。
  # 含义：phase 切分相对随机基线是真实的，但 disagreement / coverage / material
  # 完整 support 未达标。此分支无需再判 not(...)，因为前序分支已穷尽 supported 情形。
  decision_state = 15C_entry_phase_reduces_heterogeneity_but_coverage_insufficient
  next_allowed_requirement = none
```

Regardless of decision：

```text
label_deployment_authorized = False
signal_search_authorized = False
model_training_authorized = False
entry_policy_authorized = False
separability_search_authorized = False
```

若 decision 为 `15C_entry_phase_mixture_supported_for_separability`，必须同时满足
`pit_scheme_supported_for_15d = true`。15D 仍只是 separability 诊断，且只能对
**PIT-observable** entry-phase + capture-friendly subtype（smooth_trend / stair_step / slow_grind）
做 t0 可分性，不得使用 outcome-relative phase 作为 feature。若只有 outcome scheme 通过，
结论必须明确为 descriptive improvement，不得创建 15D。

## 13. Search Accounting

15C 必须输出 `search_accounting_audit.csv`，冻结：

```text
startup_authorization_basis = 15B_unit_granularity_insufficiency_not_15B_separability_block
manual_research_plan_override = true
selected_threshold_id = up50pct
threshold_selection_source = inherited_from_15A_lowest_pre_registered_material_censoring_threshold
taxonomy_fit_split = train
validation_usage = support_gate_no_fit
robustness_usage = support_gate_no_fit
validation_robustness_usage_detail = frozen_train_rules_applied_for_material_confirmation_only
entry_phase_pit_upgradeable_to_t0_feature = true
entry_phase_outcome_upgradeable_to_t0_feature = false
random_baseline_seed = <frozen constant>
random_baseline_repeat_n = 20
dominant_share_threshold = 0.70
min_phase_subgroup_anchor_n = 10
subgroup_weighting = anchor_weighted
pit_scheme_required_for_15d = true
outcome_phase_can_authorize_15d = false
entry_search_authorized = false
signal_search_authorized = false
model_training_authorized = false
separability_search_authorized = false
search_accounting_status = pass iff all authorization/search-accounting fields match this frozen block; fail otherwise
```

如果 runner 增加任何 unsupervised clustering（k-means / hierarchical / GMM），只能作为 appendix readout，并标记：

```text
unsupervised_result_role = exploratory_readout_not_primary_decision
```

不得用 unsupervised result 选择 primary entry-phase 或 primary subtype。

## 14. Tests

必须至少覆盖：

```text
test_path_quality_computed_on_anchor_segment_not_cluster_medoid
test_path_quality_adapter_uses_taxonomy_assignment_panel_before_rebuild
test_path_quality_adapter_reproduces_15b_anchor_path_type
test_path_quality_adapter_backfills_cluster_interval_from_membership_audit
test_path_quality_rebuild_not_required_status_passes_when_adapter_passes
test_subgroup_medoid_uses_frozen_15b_medoid_features_and_scaler
test_pit_phase_uses_only_reference_pos_and_earlier_fields
test_pit_phase_predicate_priority_and_missing_policy
test_outcome_phase_flagged_not_upgradeable_and_blocks_if_used_as_feature
test_both_phase_schemes_computed_and_compared
test_cross_split_clusters_excluded_from_primary_fit_and_gates
test_phased_representative_disagreement_uses_subgroup_earliest_shortest_medoid
test_disagreement_baseline_and_phased_metrics_use_same_anchor_weighted_denominator
test_random_baseline_only_permutes_anchor_to_subgroup_not_membership_or_quality
test_random_baseline_seed_frozen_and_deterministic
test_random_baseline_primary_metrics_are_anchor_weighted_not_subgroup_equal_weighted
test_dominant_share_threshold_0p70_assigns_single_subtype_else_mixed
test_sparse_phase_subgroups_do_not_count_as_single_subtype_coverage
test_phase_split_is_real_requires_uplift_over_random
test_train_only_quantiles_do_not_use_validation_or_robustness
test_censored_rows_excluded_from_phase_and_mixture
test_primary_support_gate_uses_selected_threshold_train_improvement_only
test_validation_and_robustness_are_support_gate_no_fit_confirmations
test_hard_fail_gate_sources_exist_and_fail_closed_when_missing
test_search_accounting_records_startup_authorization_override
test_decision_map_never_authorizes_signal_separability_or_label_deployment
test_outcome_only_support_maps_to_descriptive_improvement_not_15d
test_supported_decision_only_allows_pit_phase_capture_friendly_subtype_to_15d
```

Synthetic fixtures 至少包含：

```text
single cluster whose anchors split cleanly into early late_rescue + later smooth_trend by phase
single cluster that stays mixed regardless of phase scheme (random baseline must match phased)
PIT phase fixture where breakout/late_chase separable from base by t0 fields only
outcome phase fixture verifying cluster_progress cutoffs
censored / non-hit rows that must be excluded
```

## 15. Implementation Notes

```text
1. path-quality 必须在 anchor segment（entry_pos -> first_threshold_hit_pos）上取，沿用 15B 冻结 rule，不重定义。
2. entry-phase 必须在 path-quality 聚合之前确定，因果顺序：entry_phase -> sub-segment path-quality -> cluster mixture。
3. PIT phase 只用 reference_pos 及之前字段；outcome phase 用 cluster interval，永不升级为 feature。
4. 随机切分基线只打乱 anchor->子组分配，保留 cluster 成员与 anchor path-quality 不变；primary metric 必须 anchor-weighted。
5. dominant_share 阈值（0.70 primary，0.75 sensitivity）与 min_phase_subgroup_anchor_n = 10 预注册，写入 mixture_rule_audit.csv。
6. cross_split / split-boundary touching cluster 只能做 readout，不得进入 primary fit / gate / decision。
7. 三档阈值分开报告，不得把 up50 的 phase/subtype 结构外推到 up100 / up150。
8. report 不得把 entry_phase_outcome 描述为可预测信号；它只是 label-form descriptor。
9. 只有 PIT scheme 通过 full support gates 才能授权 15D；outcome-only 改善必须落为 descriptive improvement。
10. 若 phase 切分不显著优于随机基线，结论必须明确：winner 应保持为 outcome label，path shape 仅作 post-hoc descriptor。
```

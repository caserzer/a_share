# 需求：12A5A Bad-side Decoupling Feasibility Probe

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 每个被读取的输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status。
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明时 fail closed；不得从报告文本或聚合表反推出事件、标签或特征。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A5A
run_id = 12A5A_badside_decoupling_feasibility_probe
status = spec_draft_pending_review
expected_entrypoint = src/run_12a5a_badside_decoupling_feasibility_probe.py
expected_config = configs/config_12a5a_badside_decoupling_feasibility_probe.yaml
expected_test_file = tests/test_12a5a_badside_decoupling_feasibility_probe.py
```

12A5A 是 12A5 的第一阶段 probe，不是建模阶段。它只回答一个前置问题：

```text
在 12A4 已经物化的 high-uplift risk_on bucket 内，
bad-side 是否在现有 PIT feature 空间里可以与 clean winner 解耦，
即能否在不把 precision 打回 base rate 的前提下，用一个低容量 rejector 显著降低 bad-side。
```

只有 12A5A 证明可解耦，才允许进入 12A5B 完整 morphology bad-side reduction modeling。否则停止 state-change timing 方向，只保留 C0 作为 feature source。

## 2. 上游冻结事实

12A5A 承接以下已发布事实：

```text
12A1 decision = 12A1_r_core_recall_benchmark_only
12A2 decision = 12A2_state_change_candidate_generation_supported
12A3 decision = 12A3_state_change_backbone_partial_feature_source
12A4 decision = 12A4_meta_label_partial_feature_source
```

12A4 关键 robustness top20 读数（risk_on, low_to_high）：

```text
C0 baseline            precision = 7.94%   bad_side = 28.12%
density-only           precision = 11.06%  bad_side = 31.17%
freshness-only         precision = 10.28%  bad_side = 28.26%
R-core interaction     precision = 10.21%  bad_side = 30.64%
shallow tree           precision = 11.86%  bad_side = 40.59%
LightGBM               precision = 12.14%  bad_side = 37.80%
```

12A4 的含义：

```text
precision 越往上推，bad-side 越容易被一起推上去。
density / freshness 已经给出“较高 precision + 较低 bad-side”的简单 frontier；
模型把 precision 从 11.06% 推到 11.86%，但 bad-side 从 31.17% 推到 40.59%。
12A4 没有证明 precision 与 bad-side 可解耦，因此不得直接进入完整 morphology modeling。
```

12A5A 不得把上述 12A4 数值当成 frozen 分母直接复用。所有 bucket、precision、bad-side、分解计数必须用 12A4 官方 bucket 口径在 12A5A 内重算并审计；12A4 数值只作 sanity cross-check，不作 ground truth。

## 3. 核心研究问题

12A5A 只回答三个问题，按顺序作为内部 gate：

1. **bad-side composition**：在每个 selected bucket 内，bad-side 是 fast-fail 主导、false-repair 主导，还是 overlap 主导？
   如果 fast-fail-only 主导，说明是入场时点太激进，morphology 很可能救不了；
   如果 false-repair / overlap 主导，才有形态过滤的理论着力点。
2. **separability**：clean low_to_high winner 与 bad-side 事件在当前 PIT feature 上是否可分？
   至少检验 density / freshness / shallow-tree / LightGBM top20 bucket 内部的单变量与低容量 separability。
3. **rejector feasibility**：是否存在低容量 rejector，能在不把 precision 打回 base rate 的前提下显著降低 bad-side？
   这是 rejector，不是 selector：先取 12A4 high-uplift bucket，再剔除高 bad-side 形态。

## 4. 非目标

12A5A 明确不做：

- 不训练新的 selector，不重新做 12A4 的 precision uplift 搜索；
- 不修改 12A2 family、12A3 frontier、12A4 feature / model / bucket 主口径；
- 不引入新的事件定义、新的 family、新的 regime scope；
- 不训练高容量黑箱作为 primary rejector（LightGBM 仅 challenger）；
- 不做 policy replay、仓位、entry / exit、交易成本或资金曲线；
- 不声明可交易 alpha；
- 不使用 episode low / high / first_50pct / MFE / future return 生成 rejector feature；
- 不用 bad-side / winner / target / inside-window 标签作为 rejector 的输入特征；
- 不用 robustness 结果回头挑选更好看的 feature / threshold / rejector；
- 不把 12A4 数值当成无需重算的 frozen 分母。

## 5. 必需输入

### 5.1 12A4 frontier 与 bucket 输入

必需输入：

```text
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_decision.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_event_universe.csv.gz
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_event_targets.csv.gz
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_score_bucket_frontier.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/non_model_filter_frontier.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_model_card.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/lightgbm_challenger_score_bucket_frontier.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/lightgbm_challenger_model_card.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/risk_on_r_core_baseline.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_feature_dictionary.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/validation_threshold_health.csv
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/supported_gate_feasibility_selfcheck.csv
outputs/local_cache/12A4_state_change_meta_label_filter_feasibility/meta_label_event_feature_matrix.parquet
configs/config_12a4_state_change_meta_label_filter_feasibility.yaml
outputs/manifests/12A4_state_change_meta_label_filter_feasibility_manifest.json
```

12A4 gate：

```text
meta_label_decision.decision_state in [
  12A4_meta_label_partial_feature_source,
  12A4_meta_label_supported,
  12A4_nonlinear_candidate_requires_12A5_validation
]
threshold_selection_source = train_internal_cv
```

若 12A4 decision 为 `12A4_no_meta_label_uplift` 或 `12A4_blocked_input_or_pit_failure`，12A5A 必须 fail closed：没有值得解耦的 high-uplift bucket。

若 12A4 decision 为 `12A4_meta_label_supported` 或 `12A4_nonlinear_candidate_requires_12A5_validation`，12A5A 仍可运行，但必须在 report 中记录“probe 是在更强的 12A4 结论下进行”，并以 12A4 实际 decision 为准。

### 5.2 PIT 特征与标签输入

12A5A 的 rejector feature 必须复用 12A4 已物化、已审计的 PIT feature matrix，不得新造特征口径。

必需约束：

```text
rejector feature 只能来自 meta_label_feature_dictionary.csv 中
  allowed_for_primary_model = true
  and diagnostic_only = false
  and feature_status = available
  and pit_status = pass
  and forbidden_name_pattern_flag = false
的 feature_name 列表，并且这些 feature_name 必须存在于
  meta_label_event_feature_matrix.parquet；
不得使用 12A4 标记为 diagnostic-only / redundant / sparse / all_null 的 feature；
不得使用 active-state carry-forward diagnostic feature、future R-core diagnostic feature；
不得使用任何 target / label / inside-window 字段作为 feature。
```

bad-side / winner / inside-window 标签只能来自：

```text
meta_label_event_targets.csv.gz
  fast_fail_10d_label
  false_repair_20d_label
  bad_side_10_20_label
  winner_120_label
  target_low_to_high_inside
  label_10d_complete
  label_20d_complete
  label_120d_complete
```

label completeness 必须显式参与分母；incomplete horizon 不得静默当作 negative。

事件级 join contract：

```text
primary universe:
  meta_label_event_universe.source_arm_is_c0 = true
  and meta_label_event_universe.market_regime_bucket = risk_on

join key:
  meta_event_id

required joins:
  universe inner join targets on meta_event_id
  universe inner join feature_matrix on meta_event_id

hard checks:
  meta_event_id 在 universe / targets / feature_matrix 内各自唯一；
  event_split 在 universe / targets / feature_matrix 三处一致；
  join 后 row_count 等于 primary universe row_count；
  所有 selected pool membership 只能从 join 后 C0 risk_on universe 派生；
  R-core rows 只能作为 12A4 baseline / interaction feature 的上游来源，
    不得进入 12A5A primary rejector population。
```

必需输出 `event_feature_join_audit.csv`，字段：

```text
input_table
row_count
unique_meta_event_id_n
duplicate_meta_event_id_n
primary_universe_row_count
joined_row_count
missing_in_universe_n
missing_in_targets_n
missing_in_feature_matrix_n
event_split_mismatch_n
allowed_feature_dictionary_n
allowed_feature_matrix_column_n
missing_allowed_feature_column_n
unexpected_label_or_target_feature_column_n
event_feature_join_gate_pass
feature_dictionary_parity_gate_pass
join_status
```

`event_feature_join_gate_pass = false` 或 `feature_dictionary_parity_gate_pass = false` 时，12A5A 必须 blocked。

## 6. Selected bucket 口径

12A5A 必须在 12A4 官方 bucket 口径下重建 selected pool，不得用 robustness 自身分位近似。

### 6.1 必需 selected pool

每个 selected pool 是 risk_on C0 事件在某个 12A4 scoring 下的 top20 bucket：

| pool_id | 来源 | bucket |
| --- | --- | --- |
| `density_only_top20` | 12A4 density-only frontier | top20 |
| `freshness_only_top20` | 12A4 freshness-decay frontier | top20 |
| `r_core_interaction_top20` | 12A4 R-core interaction frontier | top20 |
| `shallow_tree_top20` | 12A4 shallow tree primary model | top20 |
| `lightgbm_top20` | 12A4 LightGBM challenger | top20 |

LightGBM 处理规则：

```text
if lightgbm_challenger_model_card.lightgbm_challenger_status != evaluated:
  lightgbm_top20 pool_status = skipped_dependency_or_upstream_unavailable
  lightgbm_top20 不进入 decision gate，只进入 skipped audit row
```

bucket 重建规则：

```text
deterministic pool（density / freshness / r_core_interaction）：
  12A4 non_model_filter_frontier.csv 是聚合表，不含 threshold 列；
  因此 deterministic pool 不存在可“复用”的 published threshold，
  必须从 meta_label_event_feature_matrix 自行重算 train 分位阈值：
    higher_is_selected -> train quantile 0.80，选 score >= 阈值
    lower_is_selected  -> train quantile 0.20，选 score <= 阈值
  阈值只在 train 上计算，再原样应用到 robustness / validation，
  不得用 validation / robustness 自身分位重新切。

refit pool（shallow_tree / lightgbm）：
  使用 12A4 score_bucket frontier 的 train_reference_top20_threshold；
  阈值同样只来自 train，不得用其它 split 重切。

tie 处理（所有 pool 一致，必须与 12A4 一致）：
  纳入等于阈值的全部事件（>= 或 <=）；
  整数型 score（如 same_day_c0_event_count_all）会因 tie 纳入
  使 top20 实际占比超过名义 20%（例如 density top20 实际约 24%）。

cross-check：
  重建后的 pool 必须对 12A4 published bucket frontier 做 cross-check；
  对齐目标是 published event_n / inside_n（绝对一致），
  不是名义 20% * pool_n；
  precision / bad-side rate 浮点容忍 1e-9；
  判定按下方 deterministic / refit pool 规则执行，并记录在 bucket_reconstruction_audit.csv。
```

由于 12A4 publishable frontier 是聚合表，不含 event-level membership，12A5A 必须显式记录 bucket 重建方法：

```text
density_only_top20:
  reconstruction_method = deterministic_score_from_feature_matrix
  score_feature = same_day_c0_event_count_all
  score_direction = lower_is_selected
  train_quantile = 0.20

freshness_only_top20:
  reconstruction_method = deterministic_score_from_feature_matrix
  score_feature = freshness_decay_tau_20
  score_direction = higher_is_selected
  train_quantile = 0.80

r_core_interaction_top20:
  reconstruction_method = deterministic_score_from_feature_matrix
  score_feature = prior_r_core_event_count_20d
  score_direction = higher_is_selected
  train_quantile = 0.80

shallow_tree_top20:
  reconstruction_method = refit_12A4_primary_model_from_feature_matrix
  required_crosscheck = meta_label_model_card.feature_list_hash
  model_params = configs/config_12a4_state_change_meta_label_filter_feasibility.yaml

lightgbm_top20:
  reconstruction_method = refit_12A4_lightgbm_challenger_from_feature_matrix
  required_crosscheck = lightgbm_challenger_model_card.feature_group_importance
  model_params = configs/config_12a4_state_change_meta_label_filter_feasibility.yaml
```

对 deterministic pools，`event_n`、`inside_n` 必须与 published frontier 的 `event_n` / `event_inside_window_n` 绝对一致（不是名义 20% * pool_n）；precision / bad-side rate 使用浮点容忍 `1e-9`。由于 12A4 `non_model_filter_frontier.csv` 只发布 `bad_side_10_20_rate`、不发布 `bad_side_n`，12A5A 不得把反推的 `published_bad_side_n_derived = round(published_bad_side_rate * published_event_n)` 当作 hard gate；它只能作为 audit 读数。

对 refit pools，必须满足：

```text
feature_list_hash / feature_group_importance 与 12A4 model card 一致；
train_reference_top20_threshold 与 12A4 published frontier 一致；
reconstructed_event_n / inside_n 与 12A4 published frontier 一致；
reconstructed_precision / bad_side_rate 与 12A4 published frontier 一致（1e-9 容忍）；
bad_side_n 只有在上游 published frontier 明确提供 count 列时才参与 hard gate；
```

如果 refit pool 因依赖版本或随机性无法精确重建，则该 pool `reconstruction_status = refit_membership_mismatch`，不得进入 decision gate，只能 diagnostic。

主分析 split 为 `robustness`；`train` 用于冻结 rejector 与阈值；`validation` 仅作 readout（12A4 已证明 validation risk_on 为病态薄片，positive_n = 43、base precision = 2.00%）。

### 6.2 bucket reconstruction audit

必需输出 `bucket_reconstruction_audit.csv`，字段：

```text
pool_id
split
pool_status
reconstruction_method
score_feature
score_direction
train_quantile
train_reference_top20_threshold
nominal_top20_event_n
reconstructed_event_n
reconstructed_inside_n
reconstructed_bad_side_n
reconstructed_precision
reconstructed_bad_side_rate
reconstructed_membership_hash
published_event_n
published_inside_n
published_bad_side_n
published_bad_side_n_derived
published_precision
published_bad_side_rate
event_n_match
inside_n_match
bad_side_n_hard_gate_applied
bad_side_n_match
tie_expansion_n
precision_abs_diff
bad_side_rate_abs_diff
reconstruction_status
skip_reason
```

`event_n_match` / `inside_n_match` 必须以 published frontier 的 event_n / inside_n 为对齐目标；`nominal_top20_event_n`（= round(0.20 * pool_n)）只作记录，不作判定基准。`tie_expansion_n = reconstructed_event_n - nominal_top20_event_n`，用于显式量化整数 score 的 tie 溢出。

任一 `reconstruction_status != ok` 时，对应 pool 不得进入 decoupling 决策，只能作 diagnostic。

## 7. 第 1 步：bad-side composition

每个 selected pool x split 必须输出 bad-side 分解。

### 7.1 输出

必需输出 `badside_composition_decomposition.csv`，字段：

```text
pool_id
split
event_n
label_20d_complete_n
inside_window_n
precision
bad_side_n
bad_side_rate
fast_fail_n
false_repair_n
both_n
fast_fail_only_n
false_repair_only_n
fast_fail_only_share_of_bad
false_repair_only_share_of_bad
overlap_share_of_bad
dominant_component
composition_status
```

分解规则：

```text
bad_side_n = count(fast_fail_10d_label OR false_repair_20d_label, both horizons complete)
both_n = count(fast_fail_10d_label AND false_repair_20d_label)
fast_fail_only_n = fast_fail_n - both_n
false_repair_only_n = false_repair_n - both_n

dominant_component:
  fast_fail_dominant     if fast_fail_only_share_of_bad >= 0.50
  false_repair_dominant  if false_repair_only_share_of_bad >= 0.50
  overlap_dominant       if overlap_share_of_bad >= 0.50
  mixed                  otherwise
```

incomplete horizon 必须从分母剔除并单独计数，不得当作 negative。

### 7.2 composition gate

```text
composition_actionable = true if for the primary decision pool:
  dominant_component in (false_repair_dominant, overlap_dominant, mixed)
  and fast_fail_only_share_of_bad < 0.50
```

若 primary decision pool 是 fast-fail-only 主导（`fast_fail_only_share_of_bad >= 0.50`），12A5A 最终状态不得高于 `12A5A_no_decoupling_stop_keep_feature_source`：morphology 无法修复入场时点过激的 fast-fail。

primary decision pool 默认取 `shallow_tree_top20`（12A4 最强 allowed primary model 的 bucket，robustness bad-side 约 40.6%，是最该被解耦的难 bucket）。若 `shallow_tree_top20` reconstruction 失败（`reconstruction_status = refit_membership_mismatch`），按 `density_only_top20`（robustness bad-side 约 31.2%）兜底。

发生 fallback 时必须显式记录“问题难度变化”，避免把“能否救 40.6% 难 bucket”悄悄偷换成“能否把 31.2% 再压一点”：

```text
primary_pool_is_fallback = true
fallback_from_pool_id = shallow_tree_top20
fallback_to_pool_id = density_only_top20
fallback_from_pool_bad_side_rate = <shallow_tree_top20 robustness bad_side_rate>
fallback_to_pool_bad_side_rate = <density_only_top20 robustness bad_side_rate>
```

即便 `shallow_tree_top20` 因 membership 无法 bit-exact 重建而不能作 decision pool，§7 composition 与 §8 separability 仍必须把 `shallow_tree_top20`（近似重建）作为 diagnostic 目标输出，在 report 中明确回答“40.6% 难 bucket 是否可解耦”，不得因 membership 对不齐而完全略过该 bucket 的结论。

### 7.3 label completeness audit

必需输出 `label_completeness_audit.csv`，字段：

```text
pool_id
split
event_n
label_10d_complete_n
label_20d_complete_n
label_120d_complete_n
label_10d_complete_rate
label_20d_complete_rate
label_120d_complete_rate
label_completeness_gate_pass
```

gate：

```text
label_completeness_gate_pass = true if:
  label_20d_complete_rate >= 0.95
  and label_120d_complete_rate >= 0.95 for clean_winner separability pools
```

若 primary decision pool 的 label completeness gate 未通过，12A5A 必须 blocked。

## 8. 第 2 步：separability

每个 selected pool 必须检验 clean winner 与 bad-side 的可分性。

### 8.1 两类定义

```text
clean_winner_event:
  target_low_to_high_inside = true
  winner_120_label = true
  bad_side_10_20_label = false
  label_20d_complete = true
  label_120d_complete = true

bad_side_event:
  bad_side_10_20_label = true
  label_20d_complete = true
```

只在 label-complete 子集上做 separability；incomplete horizon 排除并计数。`clean_winner_event` 是 primary separability positive class，用于回答 winner 与 bad-side 是否可解耦。

12A5A 还必须输出 diagnostic-only 的 `clean_capture_event` separability：

```text
clean_capture_event:
  target_low_to_high_inside = true
  bad_side_10_20_label = false
  label_20d_complete = true
```

`clean_capture_event` 只用于解释 precision / bad-side tradeoff，不得替代 `clean_winner_event` 触发 supported gate。

### 8.2 单变量 separability

对每个 allowed PIT feature，输出 clean_winner vs bad_side 的单变量判别力。

必需输出 `badside_separability_univariate.csv`，字段：

```text
pool_id
split
feature_name
feature_group
clean_winner_n
bad_side_n
auc
auc_direction
abs_auc_minus_0p5
ks_statistic
coverage_rate
separability_status
```

规则：

```text
auc 必须按 clean_winner = positive、bad_side = negative 计算；
coverage_rate < 0.80 的 feature 标记 sparse，不进入 top-feature 排序；
PIT 纪律不变：feature 必须是 t0 close 可得，禁止任何 future / label 派生列。
```

### 8.3 低容量 separability

必需输出 `badside_separability_lowcapacity.csv`，至少包含：

```text
pool_id
split
method            # logistic_l2 | shallow_tree_depth_2 | scorecard_quantile
fit_split
eval_split
clean_winner_n
bad_side_n
auc
auc_ci_low
auc_ci_high
auc_ci_method
average_precision
top_decile_clean_winner_rate
bottom_decile_clean_winner_rate
separability_status
```

拟合只能用 `train`；评估在 `robustness`；阈值/分箱在 robustness 前冻结。`auc_ci_low` / `auc_ci_high` 必须用 bootstrap（默认 1000 次重采样，seed 固定）在 eval split 上计算；`clean_winner_event` 正样本极薄（C0 risk_on 量级约 40-50），点估计 AUC 方差大，必须报告 CI 以免薄样本噪声直接决定结论。

### 8.4 separability gate

separability 必须先通过正样本充分性 guard，再评估 AUC：

```text
clean_winner_sufficient = true if clean_winner_n >= 30 on the eval (robustness) split
if clean_winner_sufficient = false:
  separability_status = insufficient_positive
  该 pool 不能单独触发 supported gate（只能 diagnostic / partial 解释）
```

```text
separable = true if for the primary decision pool on robustness:
  clean_winner_sufficient = true
  and best_lowcapacity_auc >= 0.60
  and best_lowcapacity_auc_ci_low >= 0.55
  and at least one allowed feature has abs_auc_minus_0p5 >= 0.10 with coverage_rate >= 0.80
```

若 separability 完全失败（clean_winner_n < 30，或 best AUC < 0.60，或 CI 下界 < 0.55，或无单变量 abs_auc_minus_0p5 >= 0.10），12A5A 最终状态不得高于 `12A5A_no_decoupling_stop_keep_feature_source`。

separability 必须显式报告分离信号来自哪些 feature group。特别提示：12A4 的 `same_day_c0_event_count_all` 真实方向是“同日同票事件越少、precision 越高”，即 selected 的是低拥挤 / 孤立事件，并非高拥挤；该 isolation 维度与波动率不是同一维度，可能提供与 precision 不同向的解耦信号，实现时应单独关注“低拥挤 + 低波动”是否能同时成立。若分离信号几乎全部来自 `volatility_*` / `distance_to_*_low` / `rebound_from_*_low` 这类直接波动率/位置变量，report 必须标注“分离信号可能与 precision 同向耦合”，并要求 rejector 步骤验证其是否在降 bad-side 的同时打掉 precision。

## 9. 第 3 步：rejector feasibility

rejector 在 selected pool 内部运行：保留高 score，剔除高 bad-side 形态。

### 9.1 rejector 约束

```text
rejector 是 reject-classifier，primary fit labels 定义为：
  reject_positive = bad_side_event
  reject_negative = clean_winner_event
allowed rejector：
  logistic_regression_l2
  logistic_regression_l1
  shallow_decision_tree_max_depth_3
  scorecard_quantile_binning
challenger（diagnostic-only，不得单独决定 supported）：
  lightgbm_rejector_depth_3
fit population = primary decision pool 内 split = train 的 C0 risk_on 事件
primary label population = bad_side_event union clean_winner_event
  （其它 label-complete non-bad / outside-window neutral 事件从 primary fit 排除）
threshold selection = train internal CV（validation 病态，禁止用 validation/robustness 选阈值）
final evaluation = robustness，阈值在 robustness 前冻结
```

rejector feature 只能用 §5.2 allowed PIT feature；不得使用 bad_side / winner / target / inside-window 标签，也不得使用 12A4 score 本身作为 rejector 的输入特征（避免循环）。

primary rejector 的训练充分性 guard：

```text
train_clean_winner_n >= 30
train_bad_side_n >= 100
cv_n_splits = 3 stratified folds
cv_fold_min_clean_winner_n >= 8
cv_fold_min_bad_side_n >= 30
```

若 primary decision pool 不满足训练充分性，12A5A 必须 blocked，`block_reason = insufficient_training_class_sample`；不得用 diagnostic `bad_side_vs_all_non_bad` 结果替代 primary gate。

必需输出 `badside_rejector_training_audit.csv`，字段：

```text
pool_id
rejector_id
label_policy
fit_split
train_event_n
train_clean_winner_n
train_bad_side_n
train_neutral_excluded_n
cv_n_splits
cv_fold_min_clean_winner_n
cv_fold_min_bad_side_n
train_class_sufficiency_gate_pass
training_status
```

必须同时输出 diagnostic fit：

```text
diagnostic_label_policy = bad_side_vs_all_non_bad
reject_positive = bad_side_event
reject_negative = label_20d_complete and bad_side_10_20_label = false
allowed_for_decision_gate = false
```

原因：如果把所有 non-bad-side 都当作 negative，rejector 可能只学会保留 outside-window neutral 事件，从而降低 bad-side 但稀释 precision。12A5A 的 primary gate 必须基于 `bad_side_event` vs `clean_winner_event`。

### 9.2 rejector frontier

rejector 给每个事件一个 reject score；按 reject 比例扫描，输出保留池指标。

reject score 方向必须固定：

```text
reject_score_higher_is_worse = true
reject_fraction = 剔除 reject_score 最高的 fraction 事件
retained pool = selected pool - rejected high-risk tail
```

若某模型天然输出的是 clean-winner probability，必须转换为 `reject_score = 1 - clean_winner_probability`，并在 frontier 中记录 score 方向；不得让不同 rejector 的 score 方向各自解释。

必需输出 `badside_rejector_frontier.csv`，字段：

```text
pool_id
rejector_id
rejector_family
label_policy
allowed_for_decision_gate
reject_score_direction
split
reject_fraction
retained_event_n
retained_inside_n
retained_precision
retained_bad_side_rate
retained_fast_fail_rate
retained_false_repair_rate
retained_episode_recall_low_to_high
retained_winner_120_rate
bad_side_reduction_vs_pool
precision_delta_vs_pool
episode_recall_delta_vs_pool
retained_precision_vs_c0_baseline_ratio
frontier_status
```

参考分母：

```text
pool_bad_side_rate = §7 重算的 selected pool bad_side_rate
pool_precision = §6 重算的 selected pool precision
C0_risk_on_robustness_baseline_precision = §5.1 / 12A4 risk_on baseline 重算值
C0_risk_on_train_baseline_precision = §5.1 / 12A4 risk_on baseline train split 重算值
```

### 9.3 decoupling 判定点

对每个 pool x rejector，必须定位“最佳解耦工作点”：工作点只能由 train internal CV 选择，robustness 只读出 frozen workpoint。不得在 robustness 上选择 reject_fraction。

选择规则：

```text
candidate_reject_fraction_grid = [0.05, 0.10, 0.15, 0.20, 0.30, 0.40]
fit_split = train
selection_split = train_internal_cv
eval_split = robustness

chosen_reject_fraction =
  among train-CV candidate workpoints satisfying train-CV retained precision / event_n guards,
  choose the smallest retained_bad_side_rate;
  tie-break by higher retained_precision, then lower reject_fraction.

train-CV candidate workpoint guard:
  train_cv_retained_event_n >= 500
  train_cv_retained_precision >= max(C0_risk_on_train_baseline_precision, 0.0839)
```

`badside_rejector_frontier.csv` 可以输出 robustness 全网格 readout，但 `badside_decoupling_workpoint.csv` 和 decision gate 只能使用 train-CV 选出的 frozen reject_fraction。

必需输出 `badside_decoupling_workpoint.csv`，字段：

```text
pool_id
rejector_id
rejector_family
label_policy
workpoint_allowed_for_decision_gate
reject_score_direction
chosen_reject_fraction
chosen_reject_fraction_source
fit_split
selection_split
eval_split
train_cv_retained_event_n
train_cv_retained_precision
train_cv_candidate_gate_pass
retained_event_n
retained_precision
retained_bad_side_rate
pool_bad_side_rate
bad_side_reduction_abs
bad_side_reduction_rel
precision_delta_vs_pool
retained_episode_recall_low_to_high
retained_precision_minus_c0_baseline
train_class_sufficiency_gate_pass
workpoint_meets_supported
workpoint_meets_partial
workpoint_status
```

## 10. 决策 gate

12A5A 的解耦 gate 基于 robustness、primary decision pool、最佳工作点。

### 10.1 Supported gate

输出 `12A5A_badside_decoupling_supported` 需要同时满足：

```text
composition_actionable = true
separable = true
primary_pool_is_fallback = false
event_feature_join_gate_pass = true
feature_dictionary_parity_gate_pass = true
bucket_reconstruction_status = ok (primary decision pool)
rejector_family in (logistic_regression_l2, logistic_regression_l1,
                    shallow_decision_tree_max_depth_3, scorecard_quantile_binning)
label_policy = bad_side_vs_clean_winner
workpoint_allowed_for_decision_gate = true
chosen_reject_fraction_source = train_internal_cv
train_cv_candidate_gate_pass = true

# 工作点（robustness, primary decision pool, 最佳工作点）：
retained_precision >= 0.10
bad_side_reduction_abs >= 0.05
retained_bad_side_rate <= 0.33
retained_precision >= C0_risk_on_robustness_baseline_precision + 0.02
retained_event_n >= 500
retained_episode_recall_low_to_high >= 0.35

threshold_freeze_gate_pass = true
train_class_sufficiency_gate_pass = true
feature_pit_gate_pass = true
label_completeness_gate_pass = true
```

直白含义：先证明能把 shallow tree / LightGBM 这种 38%-41% bad-side 的 bucket 压到 33% 附近，而且 precision 不掉回 8%-9% base rate，episode recall 不塌。

### 10.2 Partial gate

输出 `12A5A_badside_decoupling_partial` 的条件：

```text
composition_actionable = true
and separable = true
and event_feature_join_gate_pass = true
and feature_dictionary_parity_gate_pass = true
and bucket_reconstruction_status = ok (primary decision pool)
and label_policy = bad_side_vs_clean_winner
and workpoint_allowed_for_decision_gate = true
and chosen_reject_fraction_source = train_internal_cv
and train_cv_candidate_gate_pass = true
and train_class_sufficiency_gate_pass = true
and retained_precision >= max(C0_risk_on_robustness_baseline_precision + 0.005, 0.09)
and precision_delta_vs_pool >= -0.01
and bad_side_reduction_abs >= 0.03
and label_completeness_gate_pass = true
and (
  (bad_side_reduction_abs < 0.05)
  or (retained_precision >= 0.0839 and retained_precision < 0.10)
  or (bad_side_reduction_abs >= 0.05 and retained_episode_recall_low_to_high < 0.35)
)
```

partial 表示有解耦信号但不足以独立支撑 timing rejector；report 必须明确下一步是 feature 扩展、还是受限的 12A5B 条件建模。

### 10.3 No-decoupling gate

输出 `12A5A_no_decoupling_stop_keep_feature_source` 的条件：

```text
fast_fail_only_share_of_bad >= 0.50 on primary decision pool
or separable = false
or best rejector workpoint bad_side_reduction_abs < 0.03
or every rejector that reduces bad_side pushes retained_precision below
   C0_risk_on_robustness_baseline_precision
```

该状态意味着 precision 与 bad-side 在现有 PIT feature 空间不可解耦：停止 state-change timing 方向，只保留 C0 作为 feature source，不进入 12A5B。

### 10.4 Blocked gate

```text
12A5A_blocked_input_or_pit_failure
```

输入缺失、12A4 gate 不满足、event / feature join 失败、bucket reconstruction 全部失败、PIT / label completeness 阻断、primary rejector 训练样本不足时输出。

### 10.5 决策优先级

```text
1. 12A5A_blocked_input_or_pit_failure
2. 12A5A_badside_decoupling_supported
3. 12A5A_badside_decoupling_partial
4. 12A5A_no_decoupling_stop_keep_feature_source
```

## 11. 必需输出

所有 publishable tables 写入：

```text
outputs/publishable/tables/12A5A_badside_decoupling_feasibility_probe/
```

必需文件：

```text
input_artifact_audit.csv
event_feature_join_audit.csv
bucket_reconstruction_audit.csv
label_completeness_audit.csv
badside_composition_decomposition.csv
badside_separability_univariate.csv
badside_separability_lowcapacity.csv
badside_rejector_training_audit.csv
badside_rejector_frontier.csv
badside_decoupling_workpoint.csv
badside_decoupling_decision.csv
```

challenger / 局部产物（local-cache，除非足够小）：

```text
outputs/local_cache/12A5A_badside_decoupling_feasibility_probe/rejector_artifacts/
```

必需报告：

```text
outputs/publishable/reports/badside_decoupling_feasibility_probe_report.md
```

必需 manifest：

```text
outputs/manifests/12A5A_badside_decoupling_feasibility_probe_manifest.json
```

### 11.1 `badside_decoupling_decision.csv`

必需字段：

```text
decision
decision_state
decision_reason
primary_decision_pool_id
primary_rejector_id
workpoint_label_policy
workpoint_reject_score_direction
workpoint_chosen_reject_fraction_source
workpoint_fit_split
workpoint_selection_split
workpoint_eval_split
workpoint_train_cv_retained_event_n
workpoint_train_cv_retained_precision
workpoint_train_cv_candidate_gate_pass
input_gate_pass
upstream_12a4_gate_pass
event_feature_join_gate_pass
feature_dictionary_parity_gate_pass
bucket_reconstruction_gate_pass
primary_pool_is_fallback
fallback_from_pool_id
fallback_to_pool_id
fallback_from_pool_bad_side_rate
fallback_to_pool_bad_side_rate
composition_actionable
dominant_component
separable
clean_winner_n
clean_winner_sufficient
best_lowcapacity_auc
best_lowcapacity_auc_ci_low
workpoint_reject_fraction
workpoint_retained_precision
workpoint_retained_bad_side_rate
workpoint_bad_side_reduction_abs
workpoint_precision_delta_vs_pool
workpoint_retained_episode_recall
workpoint_allowed_for_decision_gate
c0_risk_on_robustness_baseline_precision
supported_gate_pass
partial_gate_pass
threshold_freeze_gate_pass
train_class_sufficiency_gate_pass
feature_pit_gate_pass
label_completeness_gate_pass
recommended_next_requirement
block_reason
```

`recommended_next_requirement` 取值：

```text
12A5B_state_change_morphology_badside_reduction_modeling   # supported
12A5B_conditional_badside_reduction_modeling               # partial
stop_state_change_as_timing_signal_keep_feature_source     # no decoupling
```

## 12. 报告要求

`badside_decoupling_feasibility_probe_report.md` 必须用中文写清：

1. 最终 decision 与一句话原因。
2. event / target / feature matrix 的 join audit 是否通过；selected pool 在 12A4 官方 bucket 口径下重算的 precision / bad-side，与 12A4 published 值的 cross-check 是否一致。
3. bad-side 分解：fast-fail / false-repair / overlap 各自占比，dominant_component，是否有形态着力点。
4. clean winner 与 bad-side 的 separability：最强单变量与低容量 AUC（含 bootstrap CI 下界）、`clean_winner_n` 是否 >= 30（薄样本 guard）、分离信号来自哪些 feature group，是否主要来自波动率/位置变量。若 `same_day_c0_event_count_all` 贡献分离力，必须说明它是“低拥挤 / 孤立事件”维度而非高拥挤。
5. rejector 训练样本是否充分、reject score 方向是否一致、最佳工作点：保留 precision、bad-side 下降幅度、保留 episode recall，是否过/未过 supported gate。
6. precision 与 bad-side 是否真的可解耦，还是降 bad-side 必然打掉 precision。
7. 如果 primary decision pool 发生从 `shallow_tree_top20` 到 `density_only_top20` 的 fallback，必须明确说明解耦结论针对的是 40.6% 难 bucket 还是 31.2% 的较干净 bucket，不得隐短问题难度；fallback 情况不得判 supported。
8. 是否进入 12A5B，进入哪种 12A5B（完整 / 受限条件建模），还是 stop 只保留 feature source。

报告不得只给 AUC；必须以 bad-side reduction / retained precision / retained recall / PIT coverage 为主。

## 13. 测试要求

`tests/test_12a5a_badside_decoupling_feasibility_probe.py` 至少覆盖：

```text
test_required_inputs_exist_and_schema
test_event_feature_join_uses_meta_event_id_and_scope_c0_risk_on_only
test_feature_dictionary_allowed_columns_match_feature_matrix
test_12a4_partial_or_stronger_decision_gate_required
test_bucket_reconstruction_uses_train_frozen_cutoffs_not_robustness_quantile
test_deterministic_pool_recomputes_train_quantile_threshold_no_published_threshold_dependency
test_bucket_reconstruction_crosschecks_published_event_n_not_nominal_20pct
test_badside_count_is_not_hard_gate_when_upstream_only_publishes_rate
test_shallow_tree_fallback_records_pool_badside_difficulty_change
test_fallback_primary_pool_cannot_set_supported_decision_state
test_lightgbm_pool_skips_cleanly_when_dependency_or_upstream_status_unavailable
test_badside_composition_excludes_incomplete_horizon
test_badside_composition_overlap_counted_once
test_fast_fail_dominant_blocks_supported_and_partial
test_clean_winner_requires_low_to_high_winner120_and_not_badside
test_separability_requires_clean_winner_n_at_least_30_else_insufficient_positive
test_separability_gate_requires_auc_point_and_ci_lower_bound
test_separability_only_on_label_complete_subset
test_separability_features_are_allowed_pit_only_no_label_columns
test_primary_rejector_fit_uses_badside_vs_clean_winner_not_all_nonbad
test_primary_rejector_requires_train_class_sufficiency
test_rejector_does_not_use_score_or_label_as_feature
test_reject_score_higher_is_worse_and_rejects_high_score_tail
test_rejector_thresholds_are_train_cv_only_validation_is_readout
test_workpoint_train_cv_candidate_guard_enforced
test_workpoint_is_selected_by_train_cv_and_robustness_is_readout_only
test_lightgbm_rejector_cannot_set_supported_decision_state
test_decision_state_in_allowed_set_and_precedence
test_required_outputs_and_manifest_hashes
```

Forbidden feature name patterns（不得出现在 rejector feature 列）：

```text
episode_low
episode_high
first_50pct
mfe
future
target_
label_
winner_
fast_fail_
false_repair_
bad_side_
event_minus_low
inside_window
score
```

这些字段可以出现在 target / evaluation / report outputs，但不得作为 rejector 的输入特征。

## 14. Manifest

`outputs/manifests/12A5A_badside_decoupling_feasibility_probe_manifest.json` 必须记录：

```text
run_id
requirement_path
requirement_sha256
config_path
config_sha256
input_artifact_audit_sha256
event_feature_join_audit_sha256
bucket_reconstruction_audit_sha256
label_completeness_audit_sha256
badside_composition_decomposition_sha256
badside_separability_univariate_sha256
badside_separability_lowcapacity_sha256
badside_rejector_training_audit_sha256
badside_rejector_frontier_sha256
badside_decoupling_workpoint_sha256
badside_decoupling_decision_sha256
report_sha256
final_decision
created_at_utc
```

## 15. Final decision states

12A5A 最终只允许以下状态：

```text
12A5A_badside_decoupling_supported
12A5A_badside_decoupling_partial
12A5A_no_decoupling_stop_keep_feature_source
12A5A_blocked_input_or_pit_failure
```

解释：

- `12A5A_badside_decoupling_supported`：在现有 PIT feature 空间内，低容量 rejector 能显著降低 bad-side 且不把 precision 打回 base rate，可进入 12A5B 完整 morphology bad-side reduction modeling。
- `12A5A_badside_decoupling_partial`：有解耦信号但不足以独立支撑 rejector，需 feature 扩展或受限条件建模。
- `12A5A_no_decoupling_stop_keep_feature_source`：bad-side 与 precision 在现有特征空间不可解耦（fast-fail 主导或不可分），停止 state-change timing 方向，只保留 C0 作为 feature source。
- `12A5A_blocked_input_or_pit_failure`：输入、schema、上游 gate、PIT 或 label completeness 阻断。

## 16. 完成定义

12A5A 完成条件：

```text
all required gates evaluated
all required output tables written
manifest written with hashes
Chinese decision report written
final decision in allowed states
recommended_next_requirement set
```

如果最终不是 `12A5A_badside_decoupling_supported`，report 必须明确停止原因或降级路径；不得只输出数值表而不解释是否进入 12A5B。

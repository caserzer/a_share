# 需求：15C2 Winner Soft Shape Membership Diagnostic

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
6. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、universe membership 不可证明、price path completeness 不可证明、episode clustering 不可证明、prototype provenance 不可证明、membership rule provenance 不可证明时 fail closed。
7. 不得从报告文本、图像、人工讨论文本、聚合 readout 或未来标签反推出逐行 universe、episode membership、label、split 边界、entry 价格或 decision point。

## 1. 实验身份

```text
experiment_id = 15_path_defined_winner_episode_label_v0
phase_id = 15C2
run_id = 15C2_winner_soft_shape_membership_diagnostic
status = draft_revised_after_second_review
expected_entrypoint = src/run_15c2_winner_soft_shape_membership_diagnostic.py
expected_config = configs/config_15c2_winner_soft_shape_membership_diagnostic.yaml
expected_test_file = tests/test_15c2_winner_soft_shape_membership_diagnostic.py
source_plan = EXPERIMENT_ROOT/research_plan.md
upstream_requirement_15b = EXPERIMENT_ROOT/requirement_15b_winner_path_shape_taxonomy_diagnostic.md
upstream_requirement_15c = EXPERIMENT_ROOT/requirement_15c_winner_entry_phase_and_mixture_taxonomy_diagnostic.md
```

15C2 是 Episode 15 在 15C 之后插入的 **纯 descriptive label-form diagnostic**。它**不取代** 15C，也**不顺延为** 15D；它是 15C 的姐妹诊断，回答一个被 15C / 15B 的硬分类口径压住的问题。

### 1.1 与 15C 的目标区分（本实验存在的全部理由）

15B / 15C 的形态分类有两个隐含约束被混在了一起：

```text
约束 A：必须把 winner 硬分到单一 path type（dominant_share >= 0.70 否则 mixed）。
约束 B：最终要服务 t0 separability，因此形态切分轴偏向可升级为 t0 feature。
```

15C 的裁决 `15C_entry_phase_reduces_heterogeneity_but_coverage_insufficient` 同时受这两个约束拖累：

```text
1. PIT scheme 没过 real-over-random —— 这是约束 B（t0 可知性）失败，不是 "形态不可区分" 失败。
2. coverage 不足（up50 train PIT single coverage 0.1188、mixed share 0.8223）——
   这大量是约束 A（硬阈值把边界样本打成 mixed）造成的，不代表这些 episode 没有形态。
3. 但 15C 的 outcome scheme 已经通过 real-over-random（train uplift 0.1133、robustness 0.1135），
   证明 winner path 的形态异质性是真实结构，只是被 entry-zone（事后位置）解释。
```

15C2 显式**解除这两个约束**：

```text
1. 解除约束 A：不再硬分类，每个 winner anchor / episode 输出一个 K 维 morphology prototype
   软隶属度向量（默认 K=6），并单独输出 residual / low-confidence / hard-mixed readout。
2. 解除约束 B：本实验不要求形态在 t0 可知、不服务 separability，纯粹回答 "winner 形态能否被区分"。
```

15C2 不得产生任何交易、仓位、alpha、entry、meta-labeling、模型、separability 测试、t0 feature 或 label 部署授权。15C2 的唯一产物是一个 **descriptive winner shape taxonomy（软隶属度图谱）**。即使 15C2 证明形态高度可分，也不直接授权 separability；任何后续 separability 必须重新立项并独立论证 t0 可知性。

## 2. 背景判断

### 2.1 15C 留下的可分性证据

15C 已经用 outcome-relative entry-phase 通过 real-over-random，证明：

```text
winner path 形态异质性是真实结构，不是样本噪音。
```

但 15C 用 dominant_share 硬阈值衡量 "分得好不好"，导致大量 "70% smooth + 30% stair" 这类边界 episode 被打成 mixed，coverage 被人为压低。15C2 的判断是：

```text
mixed != 无形态。
mixed 在硬分类下常常是 "两类之间"，而软隶属度恰好能保留这一信息。
```

### 2.2 为什么用规则距离软化（method A），而不是无监督聚类

15C2 复用 15B 已审定的 path type 经济定义与 train-only 冻结阈值，但只把 6 个
morphology path type 构造成 prototype；`mixed` / `unclassified` 保留为 residual readout，
不进入 membership 维度。方法上只把 "hard cut" 换成 "到每个 morphology 原型中心的软距离 + softmax"。原因：

```text
1. 6 个 morphology 原型（smooth_trend / stair_step / jump_repricing / choppy_reversal /
   slow_grind / late_rescue）已经过 15B 审核，有明确经济含义；
   15B 的 mixed / unclassified 是硬分类残差，不是独立上涨形态原型。
2. 规则距离软化是 deterministic、train-only 可冻结、可复现的，符合本 topic fail-closed 纪律；
3. 无监督聚类（GMM / fuzzy c-means）的成分边界不可预注册，只能作为 appendix 对照，
   不得作为 primary 隶属度来源。
```

## 3. 相对 15C `next_allowed_requirement = none` 的重新授权论证

15C 输出 `next_allowed_requirement = none`，原因是 coverage 不足且 PIT 未过 random baseline。15C2 的启动依据必须显式论证：

```text
1. 15C 真正被证实的不是 "形态不可区分"，而是 "硬分类 + t0 可知约束下，
   形态切分不足以支撑 separability"。15C 的 outcome scheme 已通过 real-over-random，
   说明形态异质性是真实结构。

2. 15C 的 coverage gate 与 PIT real-over-random gate 都绑定了 "服务 separability" 这一下游目标；
   15C2 显式放弃该下游目标，只做 descriptive 软隶属度，因此 15C 的 none 裁决
   （针对 separability authorization）不构成对 descriptive 软分类诊断的阻断。

3. 15C2 不复活任何 t0 feature / separability / entry / model；
   它只在 label 描述层把 "硬 path type" 换成 "软 path-type 隶属度向量"。

4. 15C2 的启动依据 = 15C 已证实的 "形态结构真实存在但被硬阈值压成 mixed"，
   而不是 15C 未授权的 separability。
```

该论证必须在 15C2 report 复述，并在 `search_accounting_audit.csv` 以
`startup_authorization_basis = 15C_real_structure_compressed_by_hard_cut_not_15C_separability_block` 记录。

## 4. 核心问题

15C2 回答以下问题：

```text
Q1. 把 15B 的硬分类换成 6 个 morphology prototype 的软隶属度向量后，
    winner episode 的形态隶属是否 "尖锐"（集中在少数 path type），
    而不是几乎均匀分布在所有原型上？

Q2. 软隶属度的 "尖锐 episode 占比" 是否显著高于多重防伪基线？
    即：尖锐性是真实形态结构，还是 softmax / 维度天然制造的假尖锐？

Q3. 哪些 path-type pair 在隶属度上高度共现（例如 smooth<->stair、late_rescue<->choppy）？
    这揭示了硬分类里被丢进 mixed 的真实形态连续谱。

Q4. 各 path-type 的软隶属质量（soft mass）在 train / validation / robustness 上是否稳定，
    在三档阈值上如何变化，并且是否沿 15C outcome-relative entry phase 呈现可解释结构？

Q5. 软隶属原型是否只是 compression / drawdown-reversal 已知失败形态的换名？
    （防伪 gate，必须独立通过。）
```

必须输出一个单一裁决：

```text
decision_state
```

## 5. Scope Boundary

15C2 允许做：

```text
1. 复用 15A / 15B / 15C / 14A / 13A 的 universe lineage、split boundary、path-defined label、
   winner episode cluster 与 anchor-level path shape feature panel；
2. 复用 15B 的 6 个 morphology path type 经济定义与 train-only 冻结阈值，
   构造每类 path-type 原型中心；
3. 计算每个 winner anchor / episode 到各 morphology 原型的标准化距离，
   softmax 成 K 维隶属度向量（默认 K=6）；
4. 计算隶属熵、尖锐度、path-type pair 共现；
5. 构造随机 / permutation / blocked baseline 检验尖锐性是否真实；
6. 对软隶属原型做与已知失败形态（compression / drawdown-reversal）的重叠诊断；
7. 按 split、threshold、15C outcome-relative entry phase 输出 descriptive winner shape
   membership 图谱与稳定性 readout。
```

15C2 明确不是：

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
任何把软隶属度升级为 t0 feature 的操作
```

15C2 可以使用未来 price path 来描述已发生的 winner path 形态（label diagnostic 允许）；软隶属度向量只是 label-form descriptor，永远不得升级为 t0 feature。

## 6. 继承边界

### 6.1 允许继承

15C2 继承 15A / 15B / 15C 的以下定义：

```text
anchor_record_unit = instrument x reference_date
label_record_unit = instrument x reference_date x threshold_id
selected_threshold_id = up50pct
threshold_sensitivity_grid = {up50pct, up100pct, up150pct}
split boundary from 12A7g / 13A / 14A
censored rows are never confirmed negatives
winner_episode_cluster 定义与 transitive overlap clustering（继承 15B §6.2）
6 个 morphology path type 定义、mixed/unclassified residual 语义与 train-only 冻结阈值
（继承 15B §9）
anchor-level path shape feature 定义（继承 15B §8）
primary diagnostic unit policy（继承 15C §7.1 的 eligible / cross_split 隔离）
```

15C2 必须读取以下上游 artifacts：

```text
EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_taxonomy_rule_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/winner_episode_cluster_membership_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/split_overlap_audit.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15C_winner_entry_phase_and_mixture_taxonomy_diagnostic/winner_entry_phase_mixture_decision.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15C_winner_entry_phase_and_mixture_taxonomy_diagnostic/entry_phase_assignment_readout.csv
EXPERIMENT_ROOT/outputs/publishable/tables/15C_winner_entry_phase_and_mixture_taxonomy_diagnostic/search_accounting_audit.csv
```

15C2 可以使用以下 local cache 作为加速输入；local cache 不能绕过 publishable audit。`taxonomy_assignment_panel.parquet` 是 anchor-level 形态特征与硬 path type 的首选来源：

```text
EXPERIMENT_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/anchor_path_shape_feature_panel.parquet
EXPERIMENT_ROOT/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/taxonomy_assignment_panel.parquet
```

如果 15B anchor-level path shape cache 不存在或 schema 不匹配，15C2 runner 必须按 15B §8 冻结公式从 raw qfq bars 重建 anchor segment 上的形态特征，不得从 15B 聚合表反推逐行特征。

### 6.1.1 Authoritative join graph 与字段来源

15C2 的 authoritative row key 是 `source_row_key`。所有输入 join 必须满足一对一或多对一可证明，不得 silent duplicate：

```text
base_eligibility_source =
  15B winner_episode_cluster_membership_audit.csv
  required fields:
    source_row_key, threshold_id, episode_cluster_id,
    path_winner, is_censored, cluster_split_bucket,
    touches_multiple_split_buckets, touches_multiple_calendar_split_buckets,
    max_drawdown_20d, vol_compression_20d_60d

shape_feature_source =
  15B taxonomy_assignment_panel.parquet
  required fields:
    source_row_key, threshold_id, episode_cluster_id,
    path_shape_quality, path_type, SHAPE_FEATURES_15C2

entry_phase_source =
  15C entry_phase_assignment_readout.csv
  required fields:
    source_row_key, threshold_id, episode_cluster_id,
    entry_phase_pit, entry_phase_outcome,
    phase_assignment_status, primary_gate_eligible
```

Join order is fixed:

```text
1. Start from base_eligibility_source.
2. Inner join shape_feature_source on source_row_key and threshold_id.
3. Left join entry_phase_source on source_row_key and threshold_id for descriptive phase stratification only.
4. Fail closed if any required source has duplicate (source_row_key, threshold_id), missing join key, or incompatible episode_cluster_id.
```

`taxonomy_assignment_panel.parquet` does not have to contain `path_winner` / `is_censored` / failed-morphology fields;
those fields must come from `winner_episode_cluster_membership_audit.csv`. Output tables must use upstream field name
`episode_cluster_id`; no alternative cluster-id alias is allowed.

### 6.1.2 形态特征 adapter freeze

15C2 复用以下 15B anchor-level 形态特征（命名沿用 15B，不得重新猜字段名）：

```text
SHAPE_FEATURES_15C2 =
  path_efficiency
  max_drawdown_before_hit_abs
  underwater_days_share
  directional_entropy_5state
  trend_line_r2
  top1_positive_gain_share
  top3_positive_gain_share
  pullback_5pct_count
  log_time_to_threshold
```

这些特征必须与 15B `path_shape_taxonomy_rule_audit.csv` 中的 train quantile 同源，且只能在 anchor 自己 segment（`entry_pos -> first_threshold_hit_pos`）上取。15C2 必须输出：

```text
shape_feature_adapter_audit.csv
字段：source_row_key, adapter_source_path, adapter_source_priority,
      adapter_required_columns_present, adapter_hard_path_type_reproducible,
      adapter_row_count, adapter_duplicate_source_row_key_n, adapter_status
```

`adapter_hard_path_type_reproducible` 必须确认 15C2 用 15B 冻结 rule 复现的硬 path type 与 15B `taxonomy_assignment_panel.path_type` 完全一致；不一致则 `shape_feature_adapter_gate` fail closed。软隶属度必须与硬 path type 同源同特征，否则二者不可比。

### 6.2 不得继承为结论

15C2 不得把以下上游结论直接当成 15C2 结论：

```text
15C.decision_state
15C.next_allowed_requirement
15B.decision_state
15B.tradable_shape_share
label_deployment_authorized
signal_search_authorized
separability_search_authorized
```

这些只能作为背景与 fail-closed guard。15C2 必须基于软隶属度自己产生裁决。

## 7. Primary Unit 与 Eligible Population

```text
primary_count_unit = winner_anchor (anchor-level soft membership)
secondary_count_unit = winner_episode_cluster (anchor-weighted aggregation)
```

软隶属度 primary 在 anchor 层计算，再 anchor-weighted 聚合到 episode 层做 readout。

Eligible / fit population 冻结（沿用 15C §7.1 纪律）：

```text
eligible_primary_anchor =
  path_winner == true
  and is_censored == false
  and cluster_split_bucket in {train, validation, robustness}
  and touches_multiple_split_buckets == false
  and touches_multiple_calendar_split_buckets == false
  and path_shape_quality == pass

prototype_fit_population =
  eligible_primary_anchor
  where threshold_id == selected_threshold_id and cluster_split_bucket == train

primary_readout_population = eligible_primary_anchor where threshold_id == selected_threshold_id
validation_population = primary_readout_population where cluster_split_bucket == validation
robustness_population = primary_readout_population where cluster_split_bucket == robustness
```

`cluster_split_bucket = cross_split` 或任何 split-boundary touching cluster 只能进入 appendix readout，不得参与原型拟合、scaler 拟合、防伪基线 primary metric 或 decision。`too_short_for_stable_shape` 的 anchor（继承 15B `path_shape_quality`）只能进入 short-path readout，不进入 primary 软隶属。

`up100pct` / `up150pct` 必须输出 sensitivity readout，但不得改变 primary decision；若改变，`search_accounting_gate` fail closed。
Threshold sensitivity 使用 up50 train 冻结的 scaler、prototype center、temperature 和 distance residual 阈值，
直接投影到 up100 / up150 eligible anchors；不得为 up100 / up150 重新拟合 scaler 或 prototype。
如需 threshold-specific refit，只能作为 appendix，字段 `threshold_refit_role = exploratory_readout_not_primary_decision`，
不得进入 support gates 或 decision map。

## 8. Soft Shape Membership

### 8.1 特征标准化（train-only 冻结）

```text
shape_feature_scaler 只在 prototype_fit_population 上拟合：
  center = train median
  scale = train IQR
  if IQR == 0 then scale = 1
  missing values imputed to train median, missing flag retained

standardized_x = (x - center) / scale，对每个 SHAPE_FEATURES_15C2 维度。
```

scaler 的 center / scale / missing policy 必须写入 `shape_membership_rule_audit.csv`。

### 8.2 原型中心（train-only 冻结）

每个 path type 的原型中心 = 该 type 在 train 硬分类下命中 anchor 的标准化特征中位向量：

```text
对 prototype_type in {
  smooth_trend_winner, stair_step_winner, jump_repricing_winner,
  choppy_reversal_winner, slow_grind_winner, late_rescue_winner
}:
  prototype_center[prototype_type] =
    median standardized_x over prototype_fit_population
    where 15B hard path_type == prototype_type

unclassified_short_path 与 unclassified_mixed_path 不构造原型中心，
不参与软隶属度向量（见 §8.3）；它们只进入硬分类对照与 residual readout。
```

若某 prototype_type 在 train 硬分类下命中 anchor 数 `< min_prototype_anchor_n = 50`，该原型标记 `prototype_underpopulated = true`，仍构造中心但必须在 readout 显著标注；若 `< 20`，该原型不参与软隶属，维度降为剩余原型数，并在 audit 记录 `prototype_dropped = true`。所有原型命中数、是否 underpopulated / dropped 必须写入 `shape_membership_rule_audit.csv`。

### 8.3 软隶属度向量

```text
membership_prototype_set = 实际参与的 prototype（默认 6 个 morphology 原型，去掉 dropped）
K = len(membership_prototype_set)

distance[k] = Euclidean distance(standardized_x_anchor, prototype_center[k])

membership[k] = softmax(-distance[k] / temperature)
  = exp(-distance[k] / temperature) / sum_j exp(-distance[j] / temperature)

temperature（预注册冻结）= 1.0   （primary）
temperature 敏感性读数 = {0.5, 2.0}
```

`membership` 是一个 K 维（默认 6 维）向量，sum = 1。`temperature` 必须写入 audit。软隶属度只用 morphology 原型；`unclassified_*` 不进入软隶属（它们本就是 "无 dominant 形态" 的硬分类残差，纳入软隶属会自我指涉）。

缺失特征已在 §8.1 imputed 到 train median；若某 anchor 的 SHAPE_FEATURES_15C2 缺失比例 `> 0.30`，该 anchor 标记 `membership_low_confidence = true`，进入 low-confidence readout，不进入 primary sharpness 统计。

### 8.3.1 原型距离质量与 residual 判定

softmax 必然把每个 anchor 的 membership 归一到 sum=1，因此必须单独判断 anchor 是否真的靠近某个原型：

```text
top1_prototype = argmax_k membership[k]
top1_distance = min_k distance[k]

top1_distance_percentile =
  percentile rank of top1_distance relative to train anchors whose 15B hard path_type == top1_prototype

out_of_prototype_residual =
  top1_distance_percentile >= out_of_prototype_distance_percentile_threshold

out_of_prototype_distance_percentile_threshold（预注册冻结）= 0.95
```

`out_of_prototype_residual = true` 的 anchor 仍保留 membership vector 作为 descriptive readout，
但不得计入 primary sharpness numerator。其存在说明该 anchor 离所有已注册 morphology prototype 都远，
不能因为 softmax top1 较高就被解释为某个清晰 winner 形态。

### 8.4 隶属熵与尖锐度

```text
membership_entropy = -sum(membership[k] * ln(membership[k])) / ln(K)
top1_membership = max(membership)
top2_membership_gap = top1_membership - second_largest(membership)

sharp_episode(anchor) =
  membership_entropy <= sharpness_entropy_threshold
  and top1_membership >= sharpness_top1_threshold
  and membership_low_confidence == false
  and out_of_prototype_residual == false

sharpness_entropy_threshold（预注册冻结）= 0.60
sharpness_top1_threshold（预注册冻结）= 0.50
```

`sharp_episode` 是 anchor-level 判定；episode-level sharp share = anchor-weighted mean。

### 8.5 Temperature stability

temperature 只是 softmax 的尺度参数，不应改变 "winner 形态是否可分" 的定性裁决。因此必须检验
primary temperature = 1.0 与 sensitivity temperature {0.5, 2.0} 下的裁决是否一致。

```text
对 temperature in {0.5, 1.0, 2.0}（均用同一组冻结 scaler / prototype_center）：
  在 selected_threshold_id、cluster_split_bucket = train 上，
  重算 sharp_share、membership_entropy、并按 §13.3 决策图重跑得到
  decision_state_under_temperature。
  decision_matches_primary(temperature) =
    decision_state_under_temperature == decision_state_under_primary_temperature

temperature_stability_status = pass
  iff decision_matches_primary(0.5) == true
  and decision_matches_primary(2.0) == true
否则 temperature_stability_status = fail。
```

数值漂移（sharp_share / entropy 随 temperature 变化）允许且预期；只要裁决类别不翻转即 pass。
`temperature_stability_status` 写入 `temperature_sensitivity_readout.csv`（聚合行）与
`membership_stability_gate.csv`。它是 §13.2 `temperature_stable` support gate 的唯一来源。

## 9. 防伪基线（核心防伪）

softmax 在低温下天然制造尖锐隶属；相关特征也会天然制造低熵结构。
因此 15C2 必须证明真实数据的尖锐 episode 占比不是 softmax 几何、feature covariance、
prototype label 偶然性或 cluster duplication 造成的伪影。

### 9.1 基线构造

```text
baseline_variant = column_shuffle_joint_break（primary）：
  对 prototype_fit_population 的标准化特征矩阵，
  逐特征列独立 shuffle（破坏 feature 之间的联合结构，但保留每个特征的边缘分布）。
  用同一组冻结 prototype_center、scaler、temperature 计算随机 anchor 的软隶属度。

baseline_variant = hard_label_permutation_refit（primary confirmation）：
  保留标准化特征矩阵与 feature covariance，随机 permute 15B hard path_type，
  重新拟合 prototype_center，再计算同一批真实 anchor 的 membership。
  该基线检验 prototype label 与形态特征之间的对应关系是否真实。

baseline_variant = episode_cluster_blocked_shuffle（secondary confirmation）：
  在 winner_episode_cluster block 内或等大小 cluster block 间 shuffle 特征行，
  尽量保留 cluster 重复结构，检验 cluster duplication 是否制造虚假尖锐性。

random_seed（冻结常数，写入 shape_membership_rule_audit.csv）。
random_repeat_n = 20，取均值。
```

`column_shuffle_joint_break` 不改变原型中心、scaler、temperature、softmax 公式；
`hard_label_permutation_refit` 允许原型中心随 permuted labels 重新拟合；
`episode_cluster_blocked_shuffle` 不得改变 split / threshold / censoring / eligibility。

### 9.2 对照指标

```text
sharp_share_real         真实数据 sharp_episode 的 anchor-weighted share
sharp_share_random       随机基线 sharp_episode 的 anchor-weighted share
sharp_share_uplift        = sharp_share_real - sharp_share_random

mean_membership_entropy_real
mean_membership_entropy_random
membership_entropy_reduction = mean_membership_entropy_random - mean_membership_entropy_real
```

输出到：

```text
membership_vs_random_baseline_readout.csv
```

### 9.3 真实性判据

```text
membership_sharpness_is_real =
  column_shuffle_joint_break.sharp_share_uplift >= 0.10
  and column_shuffle_joint_break.membership_entropy_reduction >= 0.10
  and hard_label_permutation_refit.sharp_share_uplift >= 0.05
  and hard_label_permutation_refit.membership_entropy_reduction >= 0.05
  and episode_cluster_blocked_shuffle.sharp_share_uplift >= 0.00
```

若不满足，软隶属尖锐性被判定为 softmax 假象，winner 形态不可分。

## 10. Path-Type 共现谱

硬分类丢进 mixed 的 episode，其软隶属揭示了真实的形态连续谱。15C2 必须输出 path-type pair 共现：

```text
对每个 anchor，取 top2 membership 的两个 prototype = (typeA, typeB)，typeA<typeB 排序。
co_occurrence[(typeA, typeB)] = anchor-weighted share over primary_readout_population

输出到 path_type_co_occurrence_readout.csv，字段至少：
  threshold_id, cluster_split_bucket, type_pair, anchor_share,
  mean_top2_membership_gap, is_bridge_pair
is_bridge_pair = anchor_share >= 0.05 and mean_top2_membership_gap <= 0.20
```

`is_bridge_pair = true` 的 pair 表示一批 episode 真实处于两类形态之间（不是无形态），这是 15C2 相对硬分类的核心增量信息。
bridge pair 是 continuous-spectrum 证据，不是所有 positive decision 的必要条件：
如果形态非常离散，bridge pair 可以很少；如果形态连续，bridge pair 应成为主要解释对象。

## 11. 防伪：与已知失败形态重叠

15C2 必须独立通过形态防伪 gate（沿用 topic 反复强调的纪律）：

```text
对每个 prototype_type，计算其高隶属 anchor（membership[type] >= 0.50）
与已知失败形态状态的重叠：
  compression_state        = vol_compression_20d_60d <= train q20
  drawdown_reversal_state  = max_drawdown_20d <= train q20

上述字段必须来自 `base_eligibility_source = 15B winner_episode_cluster_membership_audit.csv`
中的 anchor-level 13A native morphology 字段；若字段缺失、口径不可证明或 q20 fit population
不是 selected_threshold_id train eligible anchors，则 known_failed_morphology_overlap_status fail closed。

baseline_state_share =
  same split / threshold 的 eligible primary anchors 中 state == true 的 anchor-weighted share

输出 known_failed_morphology_overlap_readout.csv，字段至少：
  prototype_type, cluster_split_bucket, state,
  high_membership_anchor_n, high_membership_state_share,
  baseline_state_share, share_delta, overlap_status, overlap_source_status

overlap_status = rediscovered_known_failure
  if high_membership_anchor_n >= 50
  and high_membership_state_share - baseline_state_share >= overlap_tolerance
overlap_status = independent_of_known_failure
  if high_membership_anchor_n >= 50
  and high_membership_state_share - baseline_state_share < overlap_tolerance
overlap_status = inconclusive_too_sparse
  if high_membership_anchor_n < 50
overlap_tolerance（预注册冻结）= 0.05
```

若 capture-friendly 原型（smooth_trend / stair_step / slow_grind）全部被判 `rediscovered_known_failure`，则即使 sharpness 真实，decision 也必须降级（见 §13），不得宣称发现了独立于已失败形态的新表面。

## 12. Required Outputs

### 12.1 Publishable tables

输出到：

```text
outputs/publishable/tables/15C2_winner_soft_shape_membership_diagnostic/
```

Required tables：

```text
input_artifact_audit.csv
upstream_lineage_audit.csv
price_path_completeness_audit.csv
shape_feature_adapter_audit.csv
shape_feature_rebuild_audit.csv
shape_membership_rule_audit.csv
prototype_fit_quality_readout.csv
prototype_bootstrap_stability_readout.csv
anchor_soft_membership_panel.csv
episode_cluster_soft_membership_mixture_readout.csv
soft_membership_distribution_readout.csv
sharpness_readout.csv
membership_vs_random_baseline_readout.csv
path_type_co_occurrence_readout.csv
known_failed_morphology_overlap_readout.csv
membership_by_split_readout.csv
membership_by_threshold_sensitivity_readout.csv
membership_by_entry_phase_readout.csv
temperature_sensitivity_readout.csv
membership_stability_gate.csv
winner_soft_shape_membership_decision.csv
search_accounting_audit.csv
```

### 12.1.1 关键表最小字段

`shape_membership_rule_audit.csv` 至少包含：

```text
prototype_type
prototype_center_vector
prototype_train_anchor_n
prototype_underpopulated
prototype_dropped
scaler_center_vector
scaler_scale_vector
scaler_missing_policy
temperature_primary
temperature_sensitivity_set
sharpness_entropy_threshold
sharpness_top1_threshold
min_prototype_anchor_n
out_of_prototype_distance_percentile_threshold
random_baseline_seed = 20260626
random_baseline_repeat_n
baseline_variant_set
membership_prototype_set
membership_rule_fit_status
```

`prototype_fit_quality_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
prototype_type
prototype_train_anchor_n
prototype_underpopulated
prototype_dropped
median_top1_distance_for_hard_type
p90_top1_distance_for_hard_type
p95_top1_distance_for_hard_type
prototype_fit_quality_status
```

`prototype_bootstrap_stability_readout.csv` 至少包含：

```text
threshold_id
prototype_type
bootstrap_repeat_n
center_coordinate_median_shift
center_coordinate_p90_shift
top1_assignment_agreement_mean
prototype_stability_status
```

`anchor_soft_membership_panel.csv` 至少包含：

```text
source_row_key
threshold_id
cluster_split_bucket
episode_cluster_id
hard_path_type_15b
top1_prototype
top1_membership
top2_prototype
top2_membership
top2_membership_gap
membership_entropy
top1_distance
top1_distance_percentile
out_of_prototype_residual
membership_low_confidence
sharp_episode
membership_smooth_trend_winner
membership_stair_step_winner
membership_jump_repricing_winner
membership_choppy_reversal_winner
membership_slow_grind_winner
membership_late_rescue_winner
```

`episode_cluster_soft_membership_mixture_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
episode_cluster_id
cluster_anchor_n
cluster_mean_membership_vector
cluster_top1_prototype
cluster_top2_prototype
cluster_membership_entropy
cluster_within_membership_dispersion
cluster_sharp_anchor_share
cluster_out_of_prototype_residual_share
```

`sharpness_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
anchor_n
sharp_share
mean_membership_entropy
mean_top1_membership
mean_top2_membership_gap
out_of_prototype_residual_share
low_confidence_share
short_path_excluded_share
```

`membership_vs_random_baseline_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
baseline_variant
sharp_share_real
sharp_share_random
sharp_share_uplift
mean_membership_entropy_real
mean_membership_entropy_random
membership_entropy_reduction
membership_sharpness_is_real
random_baseline_status
```

`membership_by_entry_phase_readout.csv` 至少包含（长格式：runner 必须把 15C
`entry_phase_assignment_readout.csv` 的 `entry_phase_pit` / `entry_phase_outcome` 两列 melt 成
`(phase_scheme, entry_phase)` 长格式，每个 anchor 出现两行，分别对应 pit 与 outcome）：

```text
threshold_id
cluster_split_bucket
phase_scheme  # pit / outcome（来自 15C 两列 melt，不是新计算）
entry_phase
phase_stratification_role = descriptive_only_not_t0_feature
anchor_n
mean_membership_vector
top1_prototype_by_soft_mass
sharp_share
mean_membership_entropy
out_of_prototype_residual_share
```

本表无论 `phase_scheme = pit` 还是 `outcome`，都只是对 soft membership 做 descriptive 分层，
不改变 15C2 的核心结论 `soft_membership_upgradeable_to_t0_feature = false`。15C 已证明 PIT phase
没过 random baseline，因此本表的 pit 分层**不得**被 report 解读为 "15C2 找到了可升级为 t0 feature 的
PIT 结构"；它只回答 "已发生的 winner 形态在不同 entry phase 上分布如何"。`phase_stratification_role`
必须恒为 `descriptive_only_not_t0_feature`，否则 `search_accounting_gate` fail closed。

`soft_membership_distribution_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
prototype_type
anchor_n
soft_mass_mean
high_membership_share_50
high_membership_share_70
top1_share
hard_path_type_share_15b
distribution_status
```

`membership_by_split_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
anchor_n
mean_membership_vector
sharp_share
mean_membership_entropy
mean_top1_membership
out_of_prototype_residual_share
low_confidence_share
split_stability_status
```

`membership_by_threshold_sensitivity_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
anchor_n
frozen_up50_projection
threshold_refit_role
mean_membership_vector
top1_prototype_by_soft_mass
sharp_share
mean_membership_entropy
out_of_prototype_residual_share
threshold_sensitivity_status
```

`temperature_sensitivity_readout.csv` 至少包含：

```text
threshold_id
cluster_split_bucket
temperature
anchor_n
sharp_share
mean_membership_entropy
mean_top1_membership
decision_state_under_temperature
decision_matches_primary
temperature_sensitivity_status
```

`membership_stability_gate.csv` 至少包含：

```text
selected_threshold_id
prototype_fit_population_anchor_n
primary_cluster_split_bucket
validation_cluster_split_bucket
robustness_cluster_split_bucket
split_stability_status
threshold_sensitivity_status
temperature_stability_status
membership_stability_status
stability_gate_status
```

`prototype_fit_population_anchor_n` 是 §13.3 decision map 第一个 sparse 分支引用的量，
等于 `prototype_fit_population`（selected_threshold_id、train、eligible）的 anchor 行数，必须可审计。

`winner_soft_shape_membership_decision.csv` 至少包含：

```text
decision_state
next_allowed_requirement
selected_threshold_id
prototype_fit_population_anchor_n
sharp_share_train
sharp_share_uplift_train
membership_sharpness_is_real_train
bridge_pair_n
discrete_shape_taxonomy_supported
continuous_shape_spectrum_supported
capture_friendly_prototype_soft_mass_train
capture_friendly_all_rediscovered_known_failure
out_of_prototype_residual_share_train
low_confidence_share_train
temperature_stability_status
label_deployment_authorized
signal_search_authorized
model_training_authorized
entry_policy_authorized
separability_search_authorized
soft_membership_upgradeable_to_t0_feature
```

`search_accounting_audit.csv` 至少包含：

```text
startup_authorization_basis
manual_research_plan_override
selected_threshold_id
threshold_selection_source
prototype_fit_split
validation_usage
robustness_usage
membership_method = rule_distance_softmax
unsupervised_method_role
temperature_primary
random_baseline_seed = 20260626
random_baseline_repeat_n
baseline_variant_set
soft_membership_upgradeable_to_t0_feature = false
entry_search_authorized
signal_search_authorized
model_training_authorized
separability_search_authorized
prototype_role
outcome_entry_phase_role
search_accounting_status
```

### 12.2 Local cache

```text
outputs/local_cache/15C2_winner_soft_shape_membership_diagnostic/
```

Allowed：

```text
anchor_soft_membership_panel.parquet
random_baseline_membership_panel.parquet
```

Local cache 不能替代 publishable audit。

### 12.3 Report

输出到：

```text
outputs/publishable/reports/winner_soft_shape_membership_diagnostic_report.md
```

Report 必须用中文写，至少包含：

```text
1. 单行裁决；
2. 为什么 15C2 在 15C none 后仍可启动（override 论证），以及它与 15C 的目标区分（放弃硬分类 + 放弃 t0 可知）；
3. 软隶属度方法（规则距离软化 + softmax）与 train-only 冻结原型；
4. prototype fit quality、top1 distance、out-of-prototype residual 与 low-confidence 占比；
5. 隶属熵 / 尖锐度分布，以及尖锐性是否显著优于多重防伪基线；
6. 15C outcome-relative entry phase 下的 soft membership 分层结构；
7. path-type 共现谱（哪些 episode 真实处于两类形态之间）；
8. 各 prototype 的软隶属质量与跨 split 稳定性；
9. 三档阈值的软隶属 composition，强调不可外推；
10. 防伪结果：capture-friendly 原型是否只是 compression / drawdown-reversal 换名；
11. winner 形态图谱结论：winner 到底有几种可区分的上涨形态、各占多少软质量；
12. 为什么本实验仍不授权 signal search、entry、model、separability、t0 feature 或 label deployment。
```

## 13. Decision Gates 与 Decision Map

### 13.1 Hard fail gates

任一失败，decision = `15C2_blocked_input_or_lineage_failure`：

```text
input_artifact_gate          <- input_artifact_audit.csv.input_gate_status
upstream_lineage_gate        <- upstream_lineage_audit.csv.lineage_status
price_path_completeness_gate <- price_path_completeness_audit.csv.price_path_status
shape_feature_adapter_gate   <- shape_feature_adapter_audit.csv.adapter_status
shape_feature_rebuild_gate   <- shape_feature_rebuild_audit.csv.rebuild_status
membership_rule_fit_gate     <- shape_membership_rule_audit.csv.membership_rule_fit_status
random_baseline_gate         <- membership_vs_random_baseline_readout.csv.random_baseline_status
prototype_fit_quality_gate   <- prototype_fit_quality_readout.csv.prototype_fit_quality_status
prototype_stability_gate     <- prototype_bootstrap_stability_readout.csv.prototype_stability_status
known_failed_overlap_gate    <- known_failed_morphology_overlap_readout.csv.overlap_source_status
search_accounting_gate       <- search_accounting_audit.csv.search_accounting_status
```

若某 audit 表为空、缺 status、或 status 不在 allowlist，相关 gate fail closed。
`shape_feature_rebuild_gate` allowlist = {pass, not_required_pass}（priority 1/2 成功时为 not_required_pass）。

多行 status 表的 gate aggregation 规则固定如下：

```text
input_artifact_gate:
  all required artifacts have read_status == pass and schema_status == pass

upstream_lineage_gate / price_path_completeness_gate / shape_feature_adapter_gate:
  all rows have status in {pass, not_required_pass}

membership_rule_fit_gate:
  all prototype rows and the global scaler / temperature / seed row have membership_rule_fit_status == pass

random_baseline_gate:
  for selected_threshold_id and cluster_split_bucket == train,
  all required baseline_variant rows in baseline_variant_set have random_baseline_status == pass

prototype_fit_quality_gate:
  all non-dropped prototype rows for selected_threshold_id have prototype_fit_quality_status == pass

prototype_stability_gate:
  all non-dropped prototype rows for selected_threshold_id have prototype_stability_status == pass

known_failed_overlap_gate:
  all capture-friendly prototype x state rows for selected_threshold_id and cluster_split_bucket == train
  have overlap_source_status == pass

search_accounting_gate:
  exactly one global row has search_accounting_status == pass and all authorization fields equal false
```

### 13.2 Support gates（primary：selected_threshold_id = up50pct，cluster_split_bucket = train，anchor-weighted）

```text
sharpness_real:
  membership_sharpness_is_real(train) == true

material_sharp_share:
  sharp_share_train >= 0.35

prototype_population_ok:
  >= 4 prototype 满足 prototype_underpopulated == false

residual_share_ok:
  out_of_prototype_residual_share_train <= 0.25

low_confidence_share_ok:
  low_confidence_share_train <= 0.25

temperature_stable:
  temperature_stability_status == pass

bridge_information_present（continuous-spectrum readout，不是 discrete taxonomy 的必需门槛）:
  bridge_pair_n >= 1

morphology_not_all_rediscovered:
  not capture_friendly_all_rediscovered_known_failure
```

Validation / robustness 只做 frozen-rule confirmation（应用冻结 scaler / prototype / temperature），不参与拟合或阈值选择。

### 13.3 Decision Map

最终裁决只能取以下枚举之一：

```text
15C2_winner_shape_discrete_descriptive_taxonomy
15C2_winner_shape_continuous_spectrum_descriptive_taxonomy
15C2_winner_shape_real_but_not_material
15C2_winner_shape_real_but_overlaps_known_failure
15C2_winner_shape_not_real_over_baselines
15C2_winner_shape_inconclusive_too_sparse_or_unstable
15C2_blocked_input_or_lineage_failure
```

Decision map：

```text
if any hard fail:
  decision_state = 15C2_blocked_input_or_lineage_failure
  next_allowed_requirement = none

elif prototype_fit_population_anchor_n < 200
     or not prototype_population_ok
     or not residual_share_ok
     or not low_confidence_share_ok
     or not temperature_stable:
  decision_state = 15C2_winner_shape_inconclusive_too_sparse_or_unstable
  next_allowed_requirement = none

elif not sharpness_real:
  decision_state = 15C2_winner_shape_not_real_over_baselines
  next_allowed_requirement = none

elif not morphology_not_all_rediscovered:
  decision_state = 15C2_winner_shape_real_but_overlaps_known_failure
  next_allowed_requirement = none

elif material_sharp_share:
  decision_state = 15C2_winner_shape_discrete_descriptive_taxonomy
  next_allowed_requirement = none

elif bridge_information_present:
  decision_state = 15C2_winner_shape_continuous_spectrum_descriptive_taxonomy
  next_allowed_requirement = none

else:
  decision_state = 15C2_winner_shape_real_but_not_material
  next_allowed_requirement = none
```

Regardless of decision：

```text
label_deployment_authorized = False
signal_search_authorized = False
model_training_authorized = False
entry_policy_authorized = False
separability_search_authorized = False
soft_membership_upgradeable_to_t0_feature = False
```

注意：即使 decision = `15C2_winner_shape_discrete_descriptive_taxonomy`（最强正面结论），
`next_allowed_requirement` 仍为 `none`。15C2 是 descriptive 终点；它产出 winner 形态图谱作为研究资产，
但任何 separability / t0 prediction 必须独立重新立项并自行论证 t0 可知性，不由 15C2 授权。

## 14. Search Accounting

```text
startup_authorization_basis = 15C_real_structure_compressed_by_hard_cut_not_15C_separability_block
manual_research_plan_override = true
selected_threshold_id = up50pct
threshold_selection_source = inherited_from_15A_lowest_pre_registered_material_censoring_threshold
prototype_fit_split = train
validation_usage = frozen_rule_confirmation_no_fit
robustness_usage = frozen_rule_confirmation_no_fit
membership_method = rule_distance_softmax
unsupervised_method_role = exploratory_appendix_not_primary_decision
temperature_primary = 1.0
random_baseline_seed = 20260626
random_baseline_repeat_n = 20
baseline_variant_set = {
  column_shuffle_joint_break,
  hard_label_permutation_refit,
  episode_cluster_blocked_shuffle
}
prototype_role = seeded_morphology_prototypes_not_unsupervised_clusters
outcome_entry_phase_role = descriptive_stratification_not_t0_feature
soft_membership_upgradeable_to_t0_feature = false
entry_search_authorized = false
signal_search_authorized = false
model_training_authorized = false
separability_search_authorized = false
search_accounting_status = pass iff all authorization/search-accounting fields match this frozen block; fail otherwise
```

如果 runner 增加 GMM / fuzzy c-means 等无监督软聚类，只能作为 appendix readout，标记
`unsupervised_result_role = exploratory_readout_not_primary_decision`，不得用其选择 primary 隶属度或 prototype。

## 15. Tests

必须至少覆盖：

```text
test_shape_features_taken_on_anchor_segment_not_episode_medoid
test_authoritative_join_graph_uses_cluster_membership_for_eligibility
test_taxonomy_cache_not_required_to_contain_path_winner_or_is_censored
test_output_schema_uses_episode_cluster_id_only
test_shape_feature_adapter_reproduces_15b_hard_path_type
test_prototype_centers_fit_on_train_only_selected_threshold
test_scaler_fit_on_train_only_and_missing_imputed_to_center
test_membership_is_softmax_over_morphology_prototypes_only_excludes_unclassified
test_membership_vector_sums_to_one
test_underpopulated_prototype_flagged_and_dropped_below_20
test_temperature_primary_frozen_and_sensitivity_readout_only
test_sharpness_uses_frozen_entropy_and_top1_thresholds
test_random_baseline_shuffles_feature_columns_independently_not_membership
test_label_permutation_baseline_refits_prototypes_preserves_feature_covariance
test_cluster_blocked_shuffle_baseline_preserves_cluster_duplication_structure
test_random_baseline_seed_frozen_and_deterministic
test_random_baseline_seed_equals_20260626
test_sharpness_real_requires_uplift_over_all_primary_baselines
test_top1_distance_percentile_flags_out_of_prototype_residual
test_out_of_prototype_residual_excluded_from_sharpness_numerator
test_bridge_pair_detection_top2_membership_gap
test_bridge_pair_not_required_for_discrete_descriptive_decision
test_known_failed_morphology_overlap_gate_uses_positive_delta_direction
test_known_failed_overlap_source_fields_are_anchor_level_and_train_q20
test_outcome_entry_phase_stratification_is_descriptive_only
test_anchor_soft_membership_panel_contains_membership_vector_and_distance_fields
test_episode_cluster_membership_mixture_aggregates_anchor_memberships
test_temperature_stability_status_pass_iff_all_sensitivity_decisions_match_primary
test_temperature_instability_downgrades_decision
test_membership_by_entry_phase_is_melt_of_15c_pit_and_outcome_columns
test_entry_phase_stratification_role_is_descriptive_only_not_t0_feature
test_low_confidence_share_downgrades_to_inconclusive
test_cross_split_and_short_path_excluded_from_primary
test_validation_robustness_are_frozen_rule_confirmation_no_fit
test_censored_rows_excluded
test_hard_fail_gate_sources_exist_and_fail_closed_when_missing
test_multirow_hard_fail_gate_requires_all_required_rows_pass
test_known_failed_overlap_source_status_is_hard_fail_gate
test_search_accounting_records_startup_authorization_override
test_decision_map_never_authorizes_separability_or_t0_feature
test_supported_descriptive_decision_still_next_allowed_none
```

Synthetic fixtures 至少包含：

```text
anchor clearly closest to smooth_trend prototype (sharp, low entropy)
anchor equidistant between smooth_trend and stair_step (bridge pair, high entropy)
anchor with >30% missing shape features (low_confidence, excluded from sharpness)
random-shuffled feature matrix producing near-uniform membership (sharpness must fail real-over-random)
label-permuted prototype fixture where covariance remains but prototype labels are meaningless
out-of-prototype anchor far from all centers but with high softmax top1 due to relative distance
outcome-phase fixture where membership differs by entry phase but remains non-upgradeable to t0 feature
capture-friendly prototype anchors overlapping compression_state (overlap gate triggers)
censored / short-path rows that must be excluded
```

## 16. Implementation Notes

```text
1. 软隶属度必须与硬 path type 同源同特征（同 15B anchor segment、同 SHAPE_FEATURES_15C2、同 train scaler），否则二者不可比。
2. 软隶属只用 6 个 morphology 原型；unclassified_short_path / unclassified_mixed_path 不进入软隶属维度。
3. temperature（1.0 primary，{0.5, 2.0} sensitivity）、sharpness 阈值、min_prototype_anchor_n、random_seed 全部预注册冻结，写入 audit。
4. 防伪基线必须至少包含 column-shuffle、hard-label permutation refit、cluster-blocked shuffle；
   不得只用单一随机基线宣称形态真实。
5. cross_split / split-boundary touching cluster 与 too_short_for_stable_shape anchor 只能 readout，不进入 primary。
6. 三档阈值分开报告，不得把 up50 的软隶属结构外推到 up100 / up150。
7. 防伪 gate 独立：capture-friendly 原型若全部只是 compression / drawdown-reversal 换名，结论必须降级。
8. 即使形态高度可分，decision 也是 descriptive 终点，next_allowed_requirement = none；不授权 separability / t0 feature。
9. report 必须明确：软隶属度是 label-form descriptor，回答 "winner 形态能否区分"，不回答 "t0 能否预测"。
10. 15C outcome-relative entry phase 只能用于 membership 分层解释，不得升级为 t0 feature。
```

# 需求：10D Winner-Safe False-Repair Rejector

## 0. 路径基准

本 requirement 同时引用 repo-root 路径与实验目录相对路径，必须按以下规则解析：

1. `REPO_ROOT` 是当前 Git repository root。
2. `TOPIC_ROOT` 是 `topics/02_AFML_BIG_WINNER`。
3. `EXPERIMENT_ROOT` 是 `TOPIC_ROOT/experiments/pending/10_riskon_layered_rejector_system_v0`。
4. 以 `topics/` 开头的路径一律按 repo-root-relative 解析。
5. 以 `../` 开头的路径一律按 `EXPERIMENT_ROOT` 相对路径解析。
6. 其他相对路径，包括 `outputs/`、`configs/`、`src/`、`tests/`，一律按 `EXPERIMENT_ROOT` 相对路径解析。
7. manifest 必须记录 resolved absolute path、relative path、file size、mtime UTC 与 content hash。

## 1. 目标

10D 是对 10C `10C_false_repair_feature_source_supported` 结论的直接后继。10C 已经证明 09B feature source 对 false-repair / exposure 方向有信息（`full / keep_9000` 在 train 上 false-repair capture lift `+7.80pp`、exposure lift `+6.90pp`），但**没有任何 operating point 是 winner-safe**：最佳候选 train E1-missed retention 只有 `84.34%`，且在 validation 上掉到 `57.81%`。

10D 回答一个更窄的问题：

```text
在 10A 冻结后的 post-dedup R-core population 上，
能否把 false-repair signal 重构成一个 winner-safe rejector，
使得 survived false-repair capture 相对 random 仍为正，
同时 winner / E1-missed winner retention 在 validation 与 robustness 上同时过 floor。
```

10D 不降低 10C 的 retention floor。降 floor 已被 10C OOS 证据证伪：train 上“差 0.66pp”在 validation 上放大成 27pp 级别的 injury。

10D 用两条 track 回答上面的问题，但只有 Track A 能产出 supported 结论：

```text
Track A  = winner-safe relabel rejector（主路径，可 supported）
Track B  = two-stage winner/E1 protection layer（诊断对照，永不 supported）
Gate-0   = entanglement separability diagnostic（前置闸门，决定 A / B 是否有可行性）
```

10D 的最终正向结论必须同时满足：

1. Gate-0 证明“被拒 winner/E1”与“被拒 non-winner false-repair”在 09B t0 特征空间上**可分**；
2. Track A 在 train 上有 train-only constrained utility，且 winner / E1-missed retention 在 **validation 与 robustness 同时** 过 floor；
3. survived false-repair capture 相对 random 在判定 split 上仍为正；
4. 与 10B selected gate 叠加后净 readout 仍可解释，不把 10B 已拒行重复记为 10D 增量。

如果 Gate-0 判定 entangled（不可分），10D 不得输出 rejector-supported；最高只能 `10D_winner_safe_false_repair_feature_source_supported`，并把结论导向更 winner-safe 的 false-repair label 工程，而不是在现有 label 上继续叠层。

Feature scope boundary：10D **只检验当前 09B 冻结 feature bank** 是否足以把 false-repair signal 改造成 winner-safe rejector。10D 不得临时构造、补齐或回填未登记到 09B `feature_contract.csv` 的 VWAP / money-flow / leader-rank / rank-persistence 等新特征。若 Gate-0 或 Track A 失败，10D 报告必须把结论导向 09B feature extension / winner-safe label 工程，而不是在 10D 内绕过 feature contract。

## 2. 当前冻结上游结论

10D 必须继承以下 10A / 10B / 10C 冻结状态，不得在本阶段回改。

| upstream | frozen value | 10D implication |
|---|---|---|
| 10A decision | `10A_density_population_source_caveated_frozen` | 10D 正向结论只能是 source-caveated supported |
| 10A default population | `10A__same_instrument_cooldown_10d` | 唯一 supported fit / threshold / gate population |
| input denominator | `risk_on_r_core_horizon_complete` | 用于 09B feature / weight join |
| output denominator | `post_dedup_risk_on_r_core` | 用于 10D 输出与下游消费 |
| 10B decision | `10B_fast_fail_structural_gate_source_caveated_supported` | Layer 1 cascade 输入 |
| 10B selected gate | 读自 10B manifest `selected_capacity_id` / `selected_threshold_id` | cascade overlap attribution，不作为 10D feature |
| 10C decision | `10C_false_repair_feature_source_supported` | 提供 false-repair score 与 best candidate provenance |
| 10C best candidate | `full / keep_9000`，reject 10.00% | Gate-0 / Track B 的参照 operating point |
| 10C block reason | `no_train_supported_capacity`（E1 retention floor 未过） | 10D 必须解决的问题 |

默认 population split counts 冻结如下，implementation 必须在 input audit 中逐项核对（与 10C `§2` 一致）：

| split | admitted | false_repair+ | winner | E1_missed_winner | bridge_winner |
|---|---:|---:|---:|---:|---:|
| `train` | 8,318 | 3,025 | 1,491 | 811 | 1,009 |
| `validation` | 2,514 | 709 | 161 | 64 | 111 |
| `robustness` | 4,970 | 1,299 | 995 | 482 | 675 |

10C `full / keep_9000` 参照读数（来自 10C report，用于 Gate-0 / Track B 锚定）：

| split | rejected_n | E1_missed_retention | winner_retention |
|---|---:|---:|---:|
| `train` | 832 | 84.34% | 89.60% |
| `validation` | 252 | 57.81% | 75.78% |
| `robustness` | 497 | 79.05% | 87.14% |

09C 与 10C 的 score / AUC / threshold 只能作为 diagnostic prior，不得作为 10D supported model、supported threshold 或 supported uplift 证据。

## 3. 非目标

10D 明确不做：

1. 不降低 winner / E1-missed / bridge retention floor（沿用 10C 的 `0.8500`）。
2. 不把任何 20d / 120d outcome 字段当作 predictor，包括 `mfe_20d`、`confirm_20_label`、`winner_120`、`E1_missed_winner_flag`、`frozen_false_repair_20d_label`、`selected_cost_bad_10_20_target`、任何 horizon-complete flag、任何 08 membership / bridge readout、任何 09C / 10B / 10C score / rank / rejected flag。
3. 不在 validation / robustness 上选择 threshold、capacity、model、feature set、ablation 或 utility 权重。
4. 不调 10A density / cooldown / cap / family / mechanism 规则。
5. 不补齐 R2 amount / volume，不重建 09B feature matrix，不临时生成未登记到 09B `feature_contract.csv` 的新 predictor。
6. 不把 Track B（protection layer）的 train 改善当作支持证据；Track B 成功标准只在 validation + robustness 上判定。
7. 不声称 production-ready、entry-candidate 或 non-caveated supported。
8. 不把 E1 baseline 当作主 uplift comparator。

## 4. Required Inputs

### 4.1 10A inputs

| artifact | required | usage |
|---|---|---|
| `outputs/manifests/10A_density_rule_system_manifest.json` | yes | source caveat、input hash、population provenance |
| `outputs/publishable/tables/10A_density_rule_system/post_dedup_population_contract.csv` | yes | default population contract |
| `outputs/publishable/tables/10A_density_rule_system/post_dedup_false_repair_power_audit.csv` | yes | capacity power gate、`e1_missed_proxy_status` |
| `outputs/publishable/tables/10A_density_rule_system/power_audit_config.csv` | yes | capacity grid、random baseline seed、retention floor |
| `outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet` | yes | row-level target、split、winner、E1、join keys |

10D supported scope 必须过滤：

```text
population_id = 10A__same_instrument_cooldown_10d
rule_arm_id = same_instrument_cooldown_10d
input_denominator_id = risk_on_r_core_horizon_complete
denominator_id = post_dedup_risk_on_r_core
readout_only_flag = false
admission_status = admitted
```

如果 `post_dedup_event_bindings.parquet` 缺少 `frozen_false_repair_20d_label`、`winner_120`、`E1_missed_winner_flag`、`e1_missed_proxy_flag`、`split`、`input_event_key` 或 `feature_matrix_join_key`，10D 必须 `10D_winner_safe_false_repair_input_blocked`。

### 4.2 09B inputs

| artifact | required | usage |
|---|---|---|
| `../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09B_feature_foundation_ablation_manifest.json` | yes | upstream hash / caveat |
| `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/feature_matrix.parquet` | yes | t0 feature matrix |
| `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09B_feature_foundation/feature_contract.csv` | yes | feature eligibility（`allowed_for_09C_flag`、`t0_visible_flag`、`feature_dtype`、`feature_family`、`label_mechanism_overlap_type`） |
| `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet` | yes | `cost_bad_10_20_20d` sample weight、exposure interval |

09B feature matrix 的 split 列名是 `event_split`。10D 内部统一别名为 `split`，但 `split` 的 authoritative source 必须来自 10A binding；implementation 必须 assert `10A binding.split == 09B feature_matrix.event_split`。09B weights 没有 split 列，禁止从 weights 推断 split。

### 4.3 08 readout inputs（只读，禁止做 predictor）

| artifact | required | usage |
|---|---|---|
| `../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet` | yes | MFE / confirm_20 / false-repair label consistency readout |
| `../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet` | yes | bridge retention / E1 membership coverage readout |

08 label parquet 必须至少提供：

```text
event_id
confirm_20_label
confirm_20_complete
mfe_20d
horizon_complete_20d
horizon_complete_120d
event_false_repair_20d_label
event_big_winner_120d_label
label_scope
```

Track A target censoring 的 `horizon_complete_20d` / `horizon_complete_120d` authoritative source 是 08 label join 后的字段；10A binding 只提供 frozen target / winner flags，不承诺 horizon completeness 列。

08 membership parquet 必须至少提供：`canonical_event_id`、`target_episode_id`、`bridge_positive_denominator_included`、`membership_basis`。如果 membership 部分缺失，bridge retention 必须显式输出 missing-coverage rows，并把 bridge gate 降级为 non-binding readout。

### 4.4 10B cascade inputs

| artifact | required for supported cascade | usage |
|---|---|---|
| `outputs/manifests/10B_fast_fail_structural_gate_manifest.json` | yes | selected 10B gate provenance（authoritative） |
| `outputs/local_cache/10B_fast_fail_structural_gate/post_dedup_fast_fail_scores.parquet` | yes | selected fast-fail rejection flags |

10B selected gate **必须**从 10B manifest 读取，不得在 10D 内硬编码 capacity。字段来源冻结为：

```text
selected_model_id        = manifest.selected_model_id
selected_population_id   = manifest.selected_population_id
selected_denominator_id  = manifest.selected_denominator_id
selected_capacity_id     = manifest.selected_capacity_id
selected_threshold_id    = manifest.selected_threshold_id
selected_ablation_id     = manifest.selected_operating_point.ablation_id
selected_reject_fraction = manifest.selected_operating_point.reject_fraction
```

当前 10B manifest 顶层 `selected_ablation_id` 可能为空，implementation 必须使用 `selected_operating_point.ablation_id`；若该字段缺失，则 10B selected gate 记为 `10B_selected_gate_incomplete`，只能输出 standalone diagnostics，不得输出 rejector-supported。

10D 必须按 manifest selected values 过滤 10B scores，并 assert 过滤后 `(input_event_key, sample_id, selected_target_id, binding_canonical_event_id, split)` 唯一；left join 到 10D supported score rows 后零行丢失、无重复、`candidate_rejected_flag` 非空布尔。如果 10B manifest 表示 supported 或 source-caveated supported 但 scores 缺失 / hash mismatch / selected capacity 在 scores 中找不到，10D 可输出 standalone diagnostics，但不得输出 rejector-supported。

### 4.5 10C diagnostic / prior inputs

| artifact | required | usage |
|---|---|---|
| `outputs/manifests/10C_false_repair_rejector_manifest.json` | yes | 10C provenance、`r2_source_policy`、config hash |
| `outputs/local_cache/10C_false_repair_rejector/post_dedup_false_repair_scores.parquet` | yes | 10C `full / keep_9000` candidate score 与 rejected flag，用于 Gate-0 / Track B |
| `outputs/publishable/reports/10C_false_repair_rejector_report.md` | yes | narrative comparison |

10C scores 只用于 Gate-0 separability 集合构造与 Track B protection layer 的参照 operating point。10C score、rank、rejected flag 严禁作为 10D Track A 的 predictor。10D 必须从 10C scores 过滤：

```text
model_id = regularized_logistic_false_repair_20d_l2_v1
ablation_id = full
capacity_id = keep_9000
threshold_id = keep_9000
population_id = 10A__same_instrument_cooldown_10d
denominator_id = post_dedup_risk_on_r_core
```

如果 10C scores 缺失或 `full / keep_9000` 行不存在，Gate-0 与 Track B 标 `input_blocked`，但 Track A 仍可独立运行。

## 5. Join Contract

### 5.1 Binding canonical event id

10A binding does not require a standalone `canonical_event_id` column. 10D must derive it from `input_event_key`, the only field 10A contracts as a pipe-delimited string（10A `§2.1`）：

```text
binding_canonical_event_id = split(input_event_key, "|")[3]
```

并 assert：

```text
input_event_key has exactly 4 pipe-delimited components
split(input_event_key, "|")[0] == sample_id
split(input_event_key, "|")[1] == selected_target_id
split(input_event_key, "|")[2] == input_denominator_id
binding_canonical_event_id is non-null
```

禁止从 `feature_matrix_join_key` 取 canonical id，因为 10A 只把 `input_event_key` 契约成 pipe 字符串。`input_event_key` 是唯一 post-dedup row key，必须带到每张输出表。

### 5.2 Feature / weight / label / membership / cascade joins

10D 复用 10C 的 join 契约，全部以 `binding_canonical_event_id` 对齐上游 canonical id：

1. **feature join**：`(sample_id, selected_target_id, input_denominator_id, binding_canonical_event_id)` 对 09B feature_matrix `(sample_id, selected_target_id, denominator_id, canonical_event_id)`，要求 one-to-one、零 supported-scope 行丢失、`10A split == 09B event_split`。
2. **weight join**：同 key 对 09B `sample_uniqueness_weights`，`filter weight_horizon_id=cost_bad_10_20_20d, weight_status=complete`；缺失 / 非正 `final_sample_weight` 在 supported scope 内是 input-blocking。
3. **08 label join**：`binding_canonical_event_id == labels.event_id`，`label_scope=all_new_candidate_union` 优先去重；`event_false_repair_20d_label` 与 10A `frozen_false_repair_20d_label` 在 `horizon_complete_20d=true` 行不一致率 > 0.5% 为 input-blocking；`event_big_winner_120d_label` 与 10A `winner_120` 在 `horizon_complete_120d=true` 行不一致率 > 0.5% 为 input-blocking；`horizon_complete_20d` / `horizon_complete_120d` 必须从该 join 携带到 Track A target censoring。
4. **08 membership join**：`binding_canonical_event_id == membership.canonical_event_id`，row-level 聚合 `bridge_positive_flag = any(bridge_positive_denominator_included)`；无 membership 行单独计数，不当 bridge negative。
5. **10B cascade join**：`(input_event_key, sample_id, selected_target_id, binding_canonical_event_id, split)`，按 10B manifest selected gate 过滤，过滤后 key 唯一；join 到 10D score rows 后零行丢失、无重复。
6. **10C score join**：`(input_event_key, split)`，按 `§4.5` 过滤到 `full / keep_9000`，零行丢失、无重复。

### 5.3 10A power-audit join

对每个 10D `(split, capacity_id, threshold_id)` 行，join 10A false-repair power audit，assert 唯一匹配。10A power audit 只作为 frozen population / capacity / random baseline / base false-repair power sanity，不替代 10D 的 `false_repair_non_winner` target power gate。

参与 Track A supported selection 的行必须同时满足：

```text
10A false_repair_ml_supported_gate_allowed == true
10D recomputed false_repair_non_winner_n >= min_positive_count
10D recomputed winner_n >= min_winner_count
```

若 10A `e1_missed_proxy_status=episode_membership_proxy_input_blocked`，该行强制 diagnostic-only。

## 6. Gate-0 Entanglement Separability Diagnostic（前置闸门）

Gate-0 必须在 Track A / Track B 之前运行，并决定 10D 是否有 winner-safe 可行性。Gate-0 不训练 rejector，不打 supported 分，只回答“被拒 winner/E1 与被拒 non-winner false-repair 在 t0 特征空间是否可分”。

### 6.1 Injury / clean 集合构造

以 10C `full / keep_9000` rejected 行为基准，per split 构造两类标签：

```text
rejected_set(split) = 10C full/keep_9000 rows where candidate_rejected_flag == true

injury_row =
    rejected_set 中 (winner_120 == true OR E1_missed_winner_flag == true)

clean_kill_row =
    rejected_set 中 false_repair_non_winner_flag == true
        and winner_120 == false
        and E1_missed_winner_flag == false
```

`winner_120` / `E1_missed_winner_flag` / `false_repair_non_winner_flag` 在此**只用于构造诊断标签，不作为特征**。同时属于两类或都不属于的 rejected 行（例如 false-repair 为 false 的 winner、或 horizon-incomplete 行）单独计入 `gate0_ambiguous_n`，不进入可分性训练。

### 6.2 Separability 模型与判据

```text
gate0_model_id     = regularized_logistic_gate0_injury_vs_clean_l2_v1
gate0_ablation_id  = full
features           = 09B t0-visible eligible features（同 §7.3 full feature set 禁用清单）
estimator          = sklearn.linear_model.LogisticRegression(penalty=l2, C=1.0, solver=liblinear, max_iter=1000, random_state=20260615)
fit_split          = train only（train injury vs train clean_kill）
preprocessing      = train median impute + train median/IQR scale，val/rob 不 refit
score              = predict_proba(injury)
readout            = train / validation / robustness 各自 rejected_set 上的 ROC-AUC
```

Gate-0 默认只用 `full` feature set 判断可分性，不跑 `no_label_mechanism_overlap` ablation。若未来加入 Gate-0 ablation，必须新增 `gate0_ablation_id` 配置和输出列，不得改变本版默认判据。

Power gate（每个判定 split）：

```text
gate0_split_evaluable =
    injury_n >= 30 and clean_kill_n >= 30
```

可分性判据（预先冻结，写入 config）：

```text
gate0_separable =
    gate0 validation AUC >= gate0_auc_floor
    and gate0 robustness AUC >= gate0_auc_floor
    and both splits gate0_split_evaluable == true

default gate0_auc_floor = 0.6000
```

`gate0_separable` 只看 validation 与 robustness。train AUC 仅作 readout，因为 protection 在 train 上几乎必然可分（train 已接近过 floor），train 改善无信息量。

### 6.3 Gate-0 对决策的约束

```text
if any judging split not gate0_split_evaluable:
    gate0_status = insufficient_power
    10D 最高只能 10D_winner_safe_false_repair_feature_source_supported

if gate0_separable == false:
    gate0_status = entangled_not_separable
    10D 最高只能 10D_winner_safe_false_repair_feature_source_supported
    报告必须明确：在当前 09B frozen feature bank 下，false-repair label 与 winner-like behavior 结构共享，
    protection layer 与 relabel 都不足以 winner-safe，下一步应做 09B feature extension 或 winner-safe label 工程

if gate0_separable == true:
    gate0_status = separable
    Track A / Track B 允许尝试 supported / diagnostic 结论
```

Gate-0 永远不单独产出 supported 结论；它只设上限。

## 7. Track A：Winner-Safe Relabel Rejector（主路径）

### 7.1 Target relabel 与 censoring 政策

Track A 不再训练 `frozen_false_repair_20d_label`，改训练 winner-safe target：

```text
target_component   = false_repair_non_winner
target_label_column = false_repair_non_winner_flag
false_repair_non_winner_flag = (frozen_false_repair_20d_label == true) and (winner_120 == false)
positive = true
```

字段来源冻结为：

```text
frozen_false_repair_20d_label = 10A binding
winner_120                   = 10A binding
E1_missed_winner_flag         = 10A binding
horizon_complete_20d          = 08 label join
horizon_complete_120d         = 08 label join
```

Censoring 硬约束：`false_repair_non_winner_flag` 的 negative 含义依赖 `winner_120`，而 `winner_120` 只在 `horizon_complete_120d == true` 时有效。Track A 训练样本资格：

```text
target_evaluable =
    horizon_complete_20d == true        # frozen_false_repair_20d_label 完整
    and horizon_complete_120d == true   # winner_120 完整

train fit rows = supported scope and target_evaluable == true
```

`horizon_complete_120d == false` 的行不得作为 training positive / negative；它们必须计入 `target_censored_n` 并在 report 中单独说明。打分（scoring / ranking / reject）仍在全部 supported admitted 行上进行，但所有 winner-safe 指标的分母只用 `target_evaluable` 或对应 readout 的非空子集，禁止把 censored 行静默当 0。

对于 `target_evaluable == false` 的行，implementation 可以输出 `false_repair_non_winner_flag` 作为 readout 派生值，但不得把它计入训练正/负类、capture 分母、winner-safe selection gate 或 supported 判据。

如果 `target_evaluable` 行数低于 supported scope 的 60%，Track A 必须降级 diagnostic 并在 report 中报告 censoring 严重度。

### 7.2 可选 E1-missed cost weight

Track A 允许（默认开启）对 E1-missed winner 加显式训练 cost weight，把 winner 保护焊进 loss，而不是事后救：

```text
e1_protect_enabled = true   # config 可关

sample_weight_final =
    final_sample_weight (09B cost_bad_10_20_20d)
    * (1 + e1_protect_lambda * 1[E1_missed_winner_flag == true and winner_120 == true])

default e1_protect_lambda = 1.0
```

`E1_missed_winner_flag` 在此仅作为 **training label 派生的样本权重**，不是 feature，符合监督学习对 label 的使用边界。该权重依赖 episode membership proxy：若 10A `e1_missed_proxy_status == episode_membership_proxy_input_blocked`，必须 `e1_protect_enabled=false` 并在 manifest 记录降级。`e1_protect_lambda`、`e1_protect_enabled` 必须入 config 与 manifest hash。

### 7.3 Feature eligibility 与 model

Eligible features 是 09B `feature_matrix.parquet` 中 `feature_contract.csv` 满足以下条件的数值列：

```text
allowed_for_09C_flag = true
t0_visible_flag = true
feature_dtype is numeric (float64/float32/int64/int32/bool)
```

以下列或族即使存在也禁止作 predictor（与 10C `§7.1` 一致并扩展）：

```text
sample_id / selected_target_id / denominator_id / canonical_event_id / instrument
event_t0_date / event_split / feature_as_of_date
任何 label / outcome / horizon-complete 列
任何 08 membership / E1 / winner / false-repair / fast-fail readout 列
mfe_20d / confirm_20_label / confirm_20_complete
任何 09C / 10B / 10C score / rank / rejected flag
final_sample_weight / sample_weight_final
active_interval_start / active_interval_end / active_interval_calendar_day_n
```

Default supported model：

```text
model_id = regularized_logistic_false_repair_non_winner_l2_v1
library = sklearn.linear_model.LogisticRegression
penalty = l2, solver = liblinear, C = 1.0, max_iter = 1000
random_state = 20260615, fit_intercept = true, class_weight = null
preprocessing = train-only median impute + train median/IQR scale（IQR==0 drop feature）
sample_weight = sample_weight_final（§7.2）
```

Ablation：`full` 与 `no_label_mechanism_overlap`（drop `label_mechanism_overlap_type` 非 none/null 的行）。只有 `full` 默认可被选为 supported candidate，除非 `no_label_mechanism_overlap` 同时有更高 train constrained utility 且过全部 safety gate。

## 8. Track B：Two-Stage Winner/E1 Protection Layer（诊断对照，永不 supported）

Track B 是对“保留 10C `full / keep_9000` 的 false-repair/exposure signal，再加一层 winner/E1 protection 把高风险 rejected 行拉回”的显式诊断实现。Track B 永远不产出 supported 结论，只产出 diagnostic readout 与 trade-off 曲线。

### 8.1 结构

```text
stage_1 (frozen) = 10C full/keep_9000 candidate_rejected_flag（不在 10D 重选）
stage_2 protection = t0-visible winner/E1 protection model
    target = protect_flag (winner_120 == true OR E1_missed_winner_flag == true)
    features = 09B t0-visible eligible features（同 §7.3 禁用清单）
    estimator = L2 logistic（同 §7.3 超参）
    fit_split = train only（仅在 stage_1 rejected_set 上拟合）
rescue rule:
    rescued_flag = stage_1 rejected and protection_score >= protect_threshold
    final_rejected_flag = stage_1 rejected and not rescued_flag
```

`protect_threshold` 只能在 **train** 的 rejected_set 上按预声明 rescue-fraction grid 冻结，validation / robustness 只能 readout / block。protection 的 target（`protect_flag`）严禁泄漏到 feature 侧。

### 8.2 Train-only threshold selection

对每个 `rescue_fraction`：

```text
train_stage1_rejected_n = count(train rows where stage_1 rejected)
rescue_n = ceil(train_stage1_rejected_n * rescue_fraction)
protect_threshold = 第 rescue_n 个 train stage_1 rejected 行的 protection_score
tie-break = protection_score desc, input_event_key asc
rescued_flag = stage_1 rejected and rank_by_protection <= rescue_n
```

Track B selected diagnostic operating point 只能用 train 选择：

```text
eligible_train_rescue =
    winner_retention >= winner_retention_floor
    and e1_missed_retention >= e1_missed_retention_floor
    and survived_capture_lift_vs_random > 0

if any eligible_train_rescue:
    selected rescue_fraction = max survived_capture_lift_vs_random
        tie-break lower rescue_fraction
else:
    selected rescue_fraction = min total_injury_excess
        tie-break higher survived_capture_lift_vs_random, lower rescue_fraction
```

其中：

```text
total_injury_excess =
    max(0, winner_retention_floor - winner_retention)
    + max(0, e1_missed_retention_floor - e1_missed_retention)
```

Track B selected operating point 仍然只是 diagnostic；validation / robustness 的 `trackB_net_ok` 不参与选择，只参与 readout。

### 8.3 Random baseline discipline

Track B random baseline 必须使用 10C `full / keep_9000` 的 `random_baseline_rejected_flag` 作为 `random_stage1_rejected_flag`，并对 random stage-1 rejected rows 应用同一个 `protection_score` 与 `protect_threshold`：

```text
random_rescued_flag = random_stage1_rejected_flag and protection_score >= protect_threshold
random_final_rejected_flag = random_stage1_rejected_flag and not random_rescued_flag
random_survived_capture_rate =
    count(random_final_rejected_flag and false_repair_non_winner_flag) / false_repair_non_winner_n
```

Track B `survived_capture_lift_vs_random` 必须用 candidate final rejected capture rate 减该 random survived capture rate。禁止把未经过同一 protection rule 的 random baseline 用作 comparator。

### 8.4 判定纪律

Track B 成功标准**只在 validation 与 robustness 上判定**，train 不参与判定：

```text
trackB_net_ok =
    survived_false_repair_capture_vs_random > 0 on validation AND robustness
    and winner_retention >= winner_retention_floor on validation AND robustness
    and e1_missed_retention >= e1_missed_retention_floor on validation AND robustness
```

其中 survived capture 是 rescue 之后仍被拒的 false-repair positive 相对 random baseline 的 lift。Track B 即使 `trackB_net_ok == true` 也只记为 diagnostic 证据，用于决定是否值得把同一套 winner-safe 约束折叠进 Track A 的单模型 target；它本身不能让 10D 变成 supported。

## 9. Capacity Grid 与 Baselines

Track A capacity grid 继承 10A `power_audit_config.csv` 的 `false_repair_20d_component`（`keep_8000 / keep_8250 / keep_8500 / keep_8750 / keep_9000`）。每个 split / capacity：

```text
reject_n = ceil(split_sample_n * reject_fraction)
candidate_rank = row_number over (candidate_score desc, input_event_key asc)
candidate_rejected_flag = candidate_rank <= reject_n
```

Random baseline 必须用 10A config 的 `random_seed=20260615` 与 `random_tie_break_key=sha256(input_event_key + "|" + capacity_id + "|" + random_seed)`，按 `(random_key asc, input_event_key asc)` 排序拒前 `reject_n`。

false-repair 无 rule baseline：`rule_baseline_id=none`、`rule_baseline_status=not_applicable`，禁止臆造 false-repair rule baseline。

## 10. Train-Only Selection Utility（Track A）

10D 复用 10C 的 two-stage utility，但 winner-safe 指标改用 `false_repair_non_winner` target 与 winner-safe 分母。

### 10.1 Per split-capacity 指标

对每个 `(model_id, ablation_id, split, capacity_id)` 计算（分母为 0 时指标为 null，且该 split 不能支持正向结论）：

```text
false_repair_non_winner_capture_rate =
    candidate_rejected_false_repair_non_winner_n / false_repair_non_winner_n
random_false_repair_non_winner_capture_rate =
    random_rejected_false_repair_non_winner_n / false_repair_non_winner_n
false_repair_non_winner_capture_lift_vs_random =
    false_repair_non_winner_capture_rate - random_false_repair_non_winner_capture_rate

winner_retention = 1 - candidate_rejected_winner_n / winner_n
e1_missed_retention = 1 - candidate_rejected_e1_missed_winner_n / e1_missed_winner_n
bridge_retention = 1 - candidate_rejected_bridge_winner_n / bridge_winner_n

false_repair_non_winner_exposure_days_reduction (同 10C §9.2，但分母用 false_repair_non_winner)
exposure_days_lift_vs_random
```

### 10.2 Stage-1 选择 utility（train only）

```text
winner_injury_excess     = max(0, (1 - winner_retention) - wrong_kill_rate_cap)
e1_missed_injury_excess  = max(0, (1 - e1_missed_retention) - e1_missed_wrong_kill_rate_cap)
bridge_injury_excess     = max(0, (1 - bridge_retention) - bridge_wrong_kill_rate_cap)

train_selection_utility =
    false_repair_capture_weight * false_repair_non_winner_capture_lift_vs_random
    + exposure_days_reduction_weight * exposure_days_lift_vs_random
    - winner_injury_excess_weight * winner_injury_excess
    - e1_missed_injury_excess_weight * e1_missed_injury_excess
    - bridge_injury_excess_weight * bridge_injury_excess
```

### 10.3 Stage-2 post-selection blocker（train-only CV）

```text
threshold_instability_excess =
    max(0, train_cv_selected_reject_fraction_std - train_cv_selected_reject_fraction_std_cap)
selected_train_constrained_utility =
    selected_train_selection_utility - threshold_instability_weight * threshold_instability_excess
```

train CV 用 5 折、按 `event_t0_date` 排序、20 日 embargo（同 10C `§10`）。`train_cv_selected_reject_fraction_std` 与 OOS spread 是 post-selection blocker，禁止进入 Stage-1 选择。

### 10.4 Supported selection gate（Track A）

一个 train 行只有全部满足才可被选：

```text
false_repair_ml_supported_gate_allowed == true (10A power audit)
false_repair_non_winner_n >= 300       # recomputed by 10D on target_evaluable rows
winner_n >= 100                        # recomputed by 10D on target_evaluable rows
target_evaluable_share >= 0.60
winner_retention >= winner_retention_floor
e1_missed_retention >= e1_missed_retention_floor
bridge_retention >= bridge_retention_floor when bridge_gate_binding_flag == true
false_repair_non_winner_capture_lift_vs_random > 0
exposure_days_lift_vs_random >= 0
train_selection_utility > 0
```

通过的 train 行按 `max train_selection_utility` 选择，tie-break：`lower (1-winner_retention)`，`higher false_repair_non_winner_capture_lift_vs_random`，`lower reject_fraction`，`capacity_id asc`，`ablation_id asc`，`model_id asc`。

## 11. OOS 与净判据（决定 supported / diagnostic）

validation / robustness 不支持正向结论，只能 block。这是 10D 区别于 10C 的核心收紧：**winner / E1 retention 必须在 validation 与 robustness 同时过 floor**，不接受“train 过、OOS 不过”。

### 11.1 OOS severe-reversal block

selected gate 必须 block rejector-supported 如果任一 OOS split：

```text
false_repair_non_winner_capture_lift_vs_random < -0.0200
or winner_retention < winner_retention_floor
or e1_missed_retention < e1_missed_retention_floor when e1_missed_winner_n >= power_min
or bridge_retention < 0.8000 when bridge_gate_binding_flag == true
```

`power_min` 默认 100；若某 OOS split 的 `e1_missed_winner_n < power_min`，该 split 的 E1 retention 仅 readout，不单独 block，但必须在 report 中显式标 low-power。OOS block 后最终 decision 按 §17 判断：若 Track A 仍有正 train signal，最高可为 `10D_winner_safe_false_repair_feature_source_supported`；否则为 diagnostic-only。

### 11.2 净 supported 判据

10D 正向 rejector-supported 额外要求（同时成立）：

```text
gate0_status == separable
selected Track A row passes §10.4
winner_retention >= winner_retention_floor on validation AND robustness
e1_missed_retention >= e1_missed_retention_floor on validation AND robustness
        (each judging split with e1_missed_winner_n >= power_min)
false_repair_non_winner_capture_lift_vs_random > 0 on validation AND robustness
oos_rejected_fraction_spread <= oos_rejected_fraction_spread_cap
selected_train_constrained_utility > 0
cascade net criteria (§12) pass on train
```

任何一条不成立则最高 `feature_source_supported`（若 Track A 有正 train signal 但 OOS / cascade / gate0 阻断）或 `diagnostic_only`。

## 12. Cascade With 10B

10D 必须按 10B manifest selected gate 输出 overlap-deduplicated cascade attribution（buckets：`both_rejected` / `fast_fail_only_rejected` / `false_repair_non_winner_only_rejected` / `accepted_by_cascade`）。净指标必须对同一 10A default pre-cascade population 计算。

10D 正向 supported 额外要求（train 上）：

```text
cascade_false_repair_non_winner_incremental_to_10b_n > 0
cascade_false_repair_non_winner_exposure_days_reduction > 0
cascade_winner_retention >= winner_retention_floor
cascade_e1_missed_retention >= e1_missed_retention_floor
```

如果 10B input 缺失 / stale / 不可 join，10D 仍可发布 standalone 表，但 decision 只能 diagnostic-only 或 feature-source-supported。

## 13. Rescue-vs-Capture Trade-off Curve

无论 Track A 还是 Track B，10D 必须输出“救回 winner/E1 的同时吐回多少 false-repair capture”的 trade-off 曲线，作为 winner-safe 可行性的核心证据。

`outputs/publishable/tables/10D_winner_safe_false_repair_rejector/rescue_capture_tradeoff.csv` 必须包含：

```text
track_id                      # trackA_relabel | trackB_protection
ablation_id
split
operating_point_id            # capacity_id (Track A) | rescue_fraction (Track B)
selected_flag
protection_threshold          # Track B only; Track A blank
rejected_n
rescued_n
survived_false_repair_non_winner_n
survived_false_repair_non_winner_capture_rate
random_rejected_n
random_rescued_n
random_survived_false_repair_non_winner_n
random_survived_capture_rate
survived_capture_lift_vs_random
winner_rescued_n
e1_missed_winner_rescued_n
winner_retention
e1_missed_retention
capture_giveback_vs_no_rescue   # 相对不 rescue 的 capture 损失
selection_basis                 # train_selected_by_survived_lift | train_selected_by_min_injury_excess | not_selected
net_ok_flag                     # Track B 仅 validation/robustness 行有意义；Track A 为 selected gate OOS readout
```

曲线必须同时给出 train（readout）与 validation / robustness（判定）三段，并在 report 中明确：判定只看 validation + robustness。

## 14. R2 Source Handling

R2 处理冻结为 `r2_source_policy = separate_family_budget_cooldown`（继承 10A / 10C）。10D 不补 amount / volume，不重建 09B feature matrix，不回写 10A / 10B / 10C。`r2_source_policy`、10A population hash、09B feature matrix hash、10B selected gate hash、10C config hash 必须写入 10D manifest。若检测到 R2 处理会改变 feature rows 或 supported population membership，10D 必须 input-blocked。

## 15. Required Outputs

所有 publishable 表必须 UTF-8 CSV、稳定列序、确定性排序。

```text
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/input_artifact_audit.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/gate0_entanglement_separability.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/model_registry.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/trackA_power_gate_readout.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/trackA_threshold_frontier.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/winner_retention_audit.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/exposure_efficiency_readout.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/mfe_confirm_relation_readout.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/trackB_protection_readout.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/rescue_capture_tradeoff.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/train_only_threshold_instability.csv
outputs/publishable/tables/10D_winner_safe_false_repair_rejector/cascade_overlap_attribution.csv
outputs/local_cache/10D_winner_safe_false_repair_rejector/post_dedup_winner_safe_scores.parquet
outputs/manifests/10D_winner_safe_false_repair_rejector_manifest.json
outputs/publishable/reports/10D_winner_safe_false_repair_rejector_report.md
```

### 15.1 `gate0_entanglement_separability.csv`

Required columns：

```text
model_id
ablation_id
split
injury_n
clean_kill_n
gate0_ambiguous_n
gate0_split_evaluable
gate0_auc
gate0_auc_floor
gate0_separable
gate0_status
```

### 15.2 `trackA_power_gate_readout.csv`

Required columns：

```text
model_id
ablation_id
population_id
denominator_id
split
capacity_id
threshold_id
sample_n
target_evaluable_n
target_evaluable_share
target_censored_n
false_repair_non_winner_n
winner_n
e1_missed_winner_n
bridge_winner_n
reject_n
reject_fraction_actual
candidate_rejected_false_repair_non_winner_n
candidate_rejected_winner_n
candidate_rejected_e1_missed_winner_n
candidate_rejected_bridge_winner_n
random_rejected_false_repair_non_winner_n
random_rejected_winner_n
false_repair_non_winner_capture_rate
random_false_repair_non_winner_capture_rate
false_repair_non_winner_capture_lift_vs_random
candidate_precision
winner_retention
wrong_kill_rate
e1_missed_retention
e1_missed_wrong_kill_rate
bridge_retention
bridge_wrong_kill_rate
bridge_gate_binding_flag
false_repair_non_winner_exposure_days_reduction
random_false_repair_non_winner_exposure_days_reduction
exposure_days_lift_vs_random
train_selection_utility
supported_row_flag
row_block_reason
```

### 15.3 `trackA_threshold_frontier.csv`

Required columns：

```text
model_id
ablation_id
capacity_id
threshold_id
selected_flag
selection_rank
target_evaluable_share
target_censored_n
train_selection_utility
selected_train_constrained_utility
train_false_repair_non_winner_capture_lift_vs_random
train_exposure_days_lift_vs_random
train_winner_retention
train_e1_missed_retention
validation_false_repair_non_winner_capture_lift_vs_random
validation_winner_retention
validation_e1_missed_retention
robustness_false_repair_non_winner_capture_lift_vs_random
robustness_winner_retention
robustness_e1_missed_retention
oos_rejected_fraction_spread
train_cv_selected_reject_fraction_std
net_supported_flag
decision_block_reason
```

`selected_train_constrained_utility` 与 `net_supported_flag` 只对 selected 行非空。

### 15.4 `trackB_protection_readout.csv`

Required columns：

```text
model_id
ablation_id
split
rescue_fraction
selected_flag
protection_threshold
stage1_rejected_n
rescued_n
final_rejected_n
false_repair_non_winner_n
survived_false_repair_non_winner_n
survived_false_repair_non_winner_capture_rate
random_stage1_rejected_n
random_rescued_n
random_final_rejected_n
random_survived_false_repair_non_winner_n
random_survived_capture_rate
survived_capture_lift_vs_random
capture_giveback_vs_no_rescue
winner_n
winner_rescued_n
candidate_rejected_winner_n_after_rescue
winner_retention
e1_missed_winner_n
e1_missed_winner_rescued_n
candidate_rejected_e1_missed_winner_n_after_rescue
e1_missed_retention
bridge_retention
total_injury_excess
selection_basis
net_ok_flag
row_block_reason
```

### 15.5 `post_dedup_winner_safe_scores.parquet`

Required columns（至少）：

```text
track_id
model_id
ablation_id
capacity_id
threshold_id
reject_fraction
population_id
denominator_id
split
input_event_key
sample_id
selected_target_id
binding_canonical_event_id
instrument
event_t0_date
admitted_event_id
frozen_false_repair_20d_label
winner_120
E1_missed_winner_flag
false_repair_non_winner_flag
target_evaluable
horizon_complete_20d
horizon_complete_120d
final_sample_weight
sample_weight_final
candidate_score
candidate_rank
random_baseline_rank
candidate_rejected_flag
random_baseline_rejected_flag
stage1_rejected_flag
protection_score
rescued_flag
final_rejected_flag
random_stage1_rejected_flag
random_rescued_flag
random_final_rejected_flag
fast_fail_rejected_flag
cascade_bucket
```

其余表（`input_artifact_audit`、`model_registry`、`winner_retention_audit`、`exposure_efficiency_readout`、`mfe_confirm_relation_readout`、`train_only_threshold_instability`、`cascade_overlap_attribution`）复用 10C 同名表的列契约，并按 10D target（`false_repair_non_winner`）替换对应分子/分母列名。若复用列名会产生歧义，必须优先使用本 requirement 中显式列名。

### 15.6 Manifest

Manifest 必须包含：

```text
decision
source_caveated
gate0_status
gate0_ablation_id
selected_track
selected_population_id
selected_denominator_id
selected_model_id
selected_ablation_id
selected_capacity_id
selected_threshold_id
selected_train_selection_utility
selected_train_constrained_utility
selected_rescue_fraction
selected_protection_threshold
trackB_selection_basis
trackB_net_ok
cascade_selected_10b_model_id
cascade_selected_10b_ablation_id
cascade_selected_10b_capacity_id
cascade_selected_10b_threshold_id
e1_protect_enabled
e1_protect_lambda
input_hashes
config_hash
feature_contract_hash
upstream_10a_population_hash
upstream_10b_selected_gate_hash
upstream_10c_config_hash
publishable_table_hashes
local_cache_hashes
input_failures
decision_block_reasons
```

Report 必须为中文，含数据表、findings、insight，并明确 10D 属于 supported / source-caveated supported / feature-source-supported / diagnostic-only / input-blocked 的哪一种，以及 Gate-0 的可分性结论与下一步建议。

## 16. Config Contract

Implementation 必须创建 `configs/config_10d.yaml`，最少包含：

```yaml
run:
  experiment_id: 10D_winner_safe_false_repair_rejector
  random_seed: 20260615
  selected_population_id: 10A__same_instrument_cooldown_10d
  selected_rule_arm_id: same_instrument_cooldown_10d
  input_denominator_id: risk_on_r_core_horizon_complete
  denominator_id: post_dedup_risk_on_r_core
  target_component: false_repair_non_winner
  target_label_column: false_repair_non_winner_flag
  weight_horizon_id: cost_bad_10_20_20d
  r2_source_policy: separate_family_budget_cooldown

model:
  model_id: regularized_logistic_false_repair_non_winner_l2_v1
  solver: liblinear
  penalty: l2
  C: 1.0
  max_iter: 1000
  random_state: 20260615

e1_protection:
  e1_protect_enabled: true
  e1_protect_lambda: 1.0

gate0:
  model_id: regularized_logistic_gate0_injury_vs_clean_l2_v1
  ablation_id: full
  gate0_auc_floor: 0.6000
  min_injury_n: 30
  min_clean_kill_n: 30

capacity_grid:
  keep_8000: 0.200
  keep_8250: 0.175
  keep_8500: 0.150
  keep_8750: 0.125
  keep_9000: 0.100

trackB:
  enabled: true
  reference_10c_model_id: regularized_logistic_false_repair_20d_l2_v1
  reference_10c_ablation_id: full
  reference_10c_capacity_id: keep_9000
  reference_10c_threshold_id: keep_9000
  rescue_fraction_grid: [0.05, 0.10, 0.15, 0.20, 0.25]
  selection_rule: train_max_survived_capture_lift_after_retention_floor_else_min_injury_excess

cascade:
  require_10b_for_supported_decision: true
  read_10b_selected_gate_from_manifest: true
  expected_10b_model_id: regularized_logistic_fast_fail_10d_l2_v1
  expected_10b_ablation_id: full
  expected_10b_capacity_id: keep_9400
  expected_10b_threshold_id: keep_9400
  expected_10b_reject_fraction: 0.0600

utility:
  false_repair_capture_weight: 1.0
  exposure_days_reduction_weight: 0.5
  winner_injury_excess_weight: 10.0
  e1_missed_injury_excess_weight: 5.0
  bridge_injury_excess_weight: 2.0
  threshold_instability_weight: 1.0
  wrong_kill_rate_cap: 0.1500
  e1_missed_wrong_kill_rate_cap: 0.1500
  bridge_wrong_kill_rate_cap: 0.1500
  winner_retention_floor: 0.8500
  e1_missed_retention_floor: 0.8500
  bridge_retention_floor: 0.8500
  oos_rejected_fraction_spread_cap: 0.1500
  train_cv_selected_reject_fraction_std_cap: 0.0500
  oos_power_min: 100

target_censoring:
  min_target_evaluable_share: 0.60
```

`expected_10b_capacity_id` 仅作 sanity 校验；authoritative selected gate 必须从 10B manifest 读取，不一致即 fail-closed。修改任一 config 值必须产生新的 manifest hash 与 report note。

## 17. Decision States

10D decision 必须恰为以下之一：

```text
10D_winner_safe_false_repair_rejector_supported
10D_winner_safe_false_repair_rejector_source_caveated_supported
10D_winner_safe_false_repair_feature_source_supported
10D_winner_safe_false_repair_diagnostic_only
10D_winner_safe_false_repair_input_blocked
```

State rules：

| decision | condition |
|---|---|
| `..._rejector_supported` | Gate-0 separable 且 Track A 过 §10.4 与 §11/§12 全部净判据，且 upstream source caveat 为 false |
| `..._rejector_source_caveated_supported` | 同上但任一 upstream source caveat 为 true（当前 10A/10B/10C 均带 caveat，故任何正向 rejector 结论只能是此项） |
| `..._feature_source_supported` | Track A 有正 train false-repair-non-winner / exposure signal，但 rejector-supported 被 gate0 entangled、OOS retention、cascade、threshold instability 或 target power 阻断 |
| `..._diagnostic_only` | 输入可读、表可产出，但无任何 row 能支持 rejector 结论 |
| `..._input_blocked` | 必需 artifact 缺失、schema mismatch、join loss、label mismatch 超容忍、leakage 检出，或 supported-scope weights / features 不可用 |

当前 10A / 10B / 10C 均带 source caveat，因此任何正向 rejector 结论必须是 `10D_winner_safe_false_repair_rejector_source_caveated_supported`；non-caveated supported 在 upstream caveat 清除并由 manifest 证明前禁止。Source caveat **不作为 blocker**，只决定 supported 结论落入 caveated 还是 non-caveated 状态。

## 18. Determinism 与 Validation

Implementation 必须确定性：固定 `PYTHONHASHSEED` 或无 hash-order 依赖；所有 seed 固定 `20260615`；rank / tie-break / CSV 输出前稳定排序；publishable 表无 wall-clock 时间戳；manifest `generated_at` 允许但排除在 table hash 之外。

Validation 命令：

```bash
python topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/src/run_10d_winner_safe_false_repair_rejector.py
```

最少 validation 断言：

1. input audit 对必需 artifact 无 failure；
2. supported-scope row count == 15,802，split counts 与 §2 一致；
3. feature / weight join 零行丢失、零重复；
4. 设计矩阵中无任何 forbidden feature（含 mfe / confirm / winner / E1 / false-repair label / 任何 score）；
5. train-only preprocessing 未在 validation / robustness refit；
6. Gate-0 injury/clean 标签仅用于诊断，不出现在任何 feature 矩阵；
7. Track A target `false_repair_non_winner_flag` 的 negative 仅在 `horizon_complete_120d == true` 行成立；censored 行不计入 positive/negative；
8. 10B cascade selected gate 来自 10B manifest 而非硬编码；
9. Track B 判定字段只在 validation + robustness 上生效；
10. 每张 publishable 表 hash 均在 manifest 中。

## 19. Implementation Notes

推荐实现位置：`src/run_10d_winner_safe_false_repair_rejector.py`，内部模块可复用 10C 的 `experiment_paths.py` / `io_contracts.py` / `modeling.py` / `metrics.py` / `reporting.py`。模块名是建议，不是契约；publishable artifact 名、schema、state machine、target label、joins、config hash 才是契约。

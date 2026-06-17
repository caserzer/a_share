# 需求：11B Archetype Protected Retention Readout

## 0. 本需求要回答的问题

11A1 在完整候选分母上证明：8 个预注册 t0 proxy family **没有一个**能在稳健 payoff-risk 上通过 acceptance gate（`screen_empty`）。11A2 进一步证明：winner 与 failure proxy 在 t0 纠缠，但在 t0 后第 3 个交易日出现可观测、非幸存者偏差、非 late 的早期路径解耦（`separation_detected_tradable`）。

这两条结论都不能回答下面这个**对称的、独立的**问题：

> 10C false-repair 模型的 `keep_9000` **diagnostic reference slice**，在不重训、不平移的前提下，是否**系统性地、过度地把 big winner（右尾保护对象）一起 reject 掉**了？换句话说，该 reference slice 在压制 false_repair 的同时，对 winner 子群的 retention 是否显著低于对非 winner 的 retention，并且这种差异是否强到不能用样本噪声解释？

> **关键前置事实（运行前必须承认）**：当前 10C manifest 的 `decision = 10C_false_repair_feature_source_supported`，`decision_block_reasons = ["no_train_supported_capacity"]`，`selected_capacity_id = null`，`selected_threshold_id = null`，`selected_cascade_status = blocked`，`source_caveated = true`。也就是说 **10C 没有一个被选中、被部署的 rejector 工作点**；`keep_9000` 在 `false_repair_threshold_frontier.csv` 里是 `selected_flag = false`、`decision_block_reason = not_selected` 的 frontier 诊断行。因此 11B **不是**「审计一个已部署 frozen rejector 工作点的非歧视性」，而是「在 `keep_9000` diagnostic reference slice 上度量 winner 相对非 winner 的 retention 非歧视性」。11B 的任何结论都只描述该 reference slice，**不构成对任何已部署 rejector 工作点的背书或授权**。

11B 只回答这个**非歧视（non-discrimination）retention** 问题，且只做 readout：

- 它**不**计算策略 EV、不输出 entry/exit/sizing、不放宽或重训 10C、不修改 10A/10B/10C/10D/11A1/11A2 的任何产物。
- 它**不**是 proxy acceptance gate（那是 11A1，已 `screen_empty`）。11A1 的 proxy 接受门与 11B 的 protected retention 门是两个不同的判据，必须彻底分离，不得混用（避免把 failure rate 与 retention ratio 写串台的 category error）。
- 它**不**宣称 10C 存在已部署 frozen rejector 工作点；它只在 `keep_9000` diagnostic reference slice 上读 retention。
- 它的唯一产物是「10C `keep_9000` reference slice 对 winner 子群是否非歧视」的统计读数，以及在欠功率时的预注册「搁置」结论。

本轮范围固定为 `analysis_regime_bucket == risk_on`，沿用 11A1/11A2 的 strict PIT evaluated denominator（`risk_on ∩ PIT-valid`，4,665 evaluated rows）。`risk_off`、`transition` 只作 out-of-scope 计数，不进入任何 retention 判定。

> 框架定位：本需求实现 `next_step_discussion.md` §6 Step 3 的 `11B_archetype_protected_retention_readout`（rejector 非歧视约束：relative retention + power floor + CI），是 11C 的三个上游依赖之一（11A1 / 11A2 / 11B）。

## 1. 实验名称与状态

- experiment_id: `11_archetype_proxy_validation_system_v0`
- primary_run_id: `11B_archetype_protected_retention_readout`
- parent_experiment_id: `10_riskon_layered_rejector_system_v0`
- upstream_run_id: `11A1_archetype_proxy_robust_payoff_risk_audit`, `11A2_post_t0_archetype_path_divergence_diagnostic`
- status: `spec_frozen_pending_run`
- expected_entrypoint: `src/run_11b_archetype_protected_retention_readout.py`
- expected_config: `configs/config_11b_archetype_protected_retention_readout.yaml`
- expected_test_file: `tests/test_archetype_protected_retention_readout.py`

## 2. 核心原则

### 2.1 retention 的角色

10C 是一个 false_repair 模型，但**当前没有被选中的工作点**（见 §0 manifest 事实）。11B 取 10C `keep_9000` **diagnostic reference slice** 物化的 reject 决策当作**已冻结的外生诊断输入**，只测量它对不同子群的 retention（= 未被 reject 的比例），并回答 retention 是否对 winner 子群非歧视。

- protected subgroup（被保护对象）：本轮的一等保护对象是 `winner_120` 右尾类。它是 outcome label，只用于**审计** reference slice 是否伤害 winner，不作为 rejector 特征、不作为 entry 信号。允许用 outcome label 做非歧视审计，与 11A1 用 `winner_120` 度量 payoff 是同一性质。
- reject decision：来自 10C `keep_9000` diagnostic reference slice，11B 不重训、不重选阈值、不平移工作点、不把该 slice 解释成已部署 rejector。

### 2.2 为什么 protected subgroup 不是 proxy，也不是 early-path state

- 11A1 `screen_empty`：没有任何 t0 proxy 通过 acceptance gate，因此本轮**不存在**「proxy 定义的 protected subgroup」。11B 的 primary protected subgroup 只能是 `winner_120` outcome 类本身，不得用任何未通过 11A1 的 proxy 反向定义保护子群。
- 11A2 `separation_detected_tradable`：早期路径解耦发生在 t0 之后（K\*=3），是 post-t0 信息，**不能**定义 t0 rejector 工作点上的 carve-out。因此 11A2 的 early-path state 不进入 11B 的 retention 子群定义；它只在 §13 作为 11C 的待验证结构留存。
- 结论：11B 的 gate-eligible 保护子群只有 `winner_120`（outcome label，audit-only）。t0-visible archetype seed flags 仅作 readout-only 子群（§5.2），不单独决定 final status。

### 2.3 11B 不做的事

- 不输出交易策略、仓位、组合收益、手续费后策略 EV。
- 不重训、不微调、不平移 10C 模型；不放宽 10C 的 reject 决策或 retention 底线。
- 不把 `keep_9000` reference slice 宣称成已部署 / 已选中的 rejector 工作点；不据此给任何 rejector 工作点背书。
- 不把 retention 读数翻译成「应该放行某些 winner」的指令；任何 carve-out 都属于 11C 的范畴。
- 不用 `winner_120`、`mfe_*`、`mae_*`、`forward_return_*` 或任何未来路径构造 rejector 特征（rejector 已冻结，本轮不构造特征）。
- 不修改 10A/10B/10C/10D/11A1/11A2 的输入、输出或既有结论。
- 不比较或解释 `risk_off`、`transition` 下的 retention；这些只作 out-of-scope count。
- 不把 11A1 proxy gate 与 11B retention gate 混为一个判据。

### 2.4 三条必须预注册的诚实条款（运行前写死）

11B 的主要失败模式是「欠功率被读成非歧视通过」与「rejector 设计意图（压 false_repair）被误读成对 winner 的歧视」。运行前必须冻结：

1. **欠功率搁置条款（power floor）**：PIT-valid evaluated denominator 下 winner 子群很小（全样本约 446，train 约 151，validation 约 16）。任一 split 的 winner 子群若 `winner_n < retention_min_winner_n`（默认 60）或 `unique_winner_instrument_n < retention_min_winner_instrument_n`（默认 30），该 split 标 `retention_underpowered`，**不得**在该 split 给出 `non_discriminatory` 或 `discriminatory` 结论。若 train 与 robustness 同时欠功率，则整轮 final status 为 `retention_inconclusive_underpowered`，**不得**通过降低 power floor「救活」结论。validation 几乎必然欠功率，只作 readout，不得驱动 final status。

2. **非歧视判据单轴条款（single-axis）**：11B 的 gate 只允许由 retention（winner 相对非 winner 的 retention 比）决定，**不得**混入 false_repair capture、EV、failure exposure、exposure-day 等任何 11A1/11C 的量。10C `keep_9000` reference slice 压制 false_repair 是它的设计目的，不构成对 winner 的歧视；只有当 winner retention 显著低于非 winner retention 时才判歧视。

3. **scope 一致条款（denominator parity）**：11B 的 retention 判定分母必须与 11A1/11A2 的 `risk_on ∩ PIT-valid` evaluated denominator 逐行对账一致（4,665 evaluated rows）。同时必须在 10C 实际工作的 pre-PIT risk_on R-core scope 上重算 winner_retention，与 10C 已发布 frontier 对账（cross-check），证明 reject 决策被正确还原。denominator drift 超阈时 ceiling 到 `retention_statistics_incomplete`。

### 2.5 本轮 regime scope

- primary evaluated denominator 必须满足 11A1 同款条件：10A post-dedup R-core primary denominator → `analysis_regime_bucket == risk_on` → strict PIT inner join（`is_listed=true ∧ is_st=false ∧ is_suspended=false`）。
- 非 `risk_on` / PIT-invalid 行只进入 scope 审计表，不进入 retention 判定。
- 本轮不得把 `risk_on` 结论外推到 `risk_off` / `transition` / 非 PIT universe。

## 3. 上游输入

### 3.1 讨论与需求输入（解释来源，非可变数据）

- `../10_riskon_layered_rejector_system_v0/next_step_discussion.md`
- `requirement_11a1_archetype_proxy_robust_payoff_risk_audit.md`
- `requirement_11a2_post_t0_archetype_path_divergence_diagnostic.md`
- `outputs/publishable/reports/11A1_archetype_proxy_robust_payoff_risk_audit_report.md`
- `outputs/publishable/reports/11A2_post_t0_archetype_path_divergence_diagnostic_report.md`

runner 必须在 `input_artifact_audit.csv` 记录 path、sha256、mtime。

### 3.2 11A1 / 11A2 frozen scope 对账输入（必需）

11B 必须复现 11A1 的 evaluated denominator，并与 11A1 / 11A2 已发布的 scope 审计表对账，确保三轮分母一致：

- `outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/risk_on_scope_filter_audit.csv`
- `outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/pit_universe_scope_filter_audit.csv`
- `outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/acceptance_summary.csv`
- `outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/scope_reconciliation_vs_11a1.csv`
- `outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/outcome_class_count_audit.csv`

若 11A1 的 local_cache evaluated denominator（如 `proxy_scored_denominator.parquet`）存在，优先直接消费其 frozen evaluated rows，并对账 row count；否则按 §4 从相同上游 contract 重建。11A2 `early_path_feature_matrix.parquet` 是 K/cohort 展开矩阵，不得直接当作 11B row-level evaluated denominator；只有在过滤到唯一 PIT-valid evaluated rows 且能证明 row identity 与 11A1/10A composite key 一一对应时，才可作为辅助对账输入。

### 3.3 10A / 09B / 08 / 09A 上游 contract（必需）

与 11A1 §3.2–§3.5 完全相同的输入集合，用于重建 evaluated denominator、regime 回填、horizon 完整性与 `winner_120` 标签：

- 10A：`10A_density_rule_system_manifest.json`、`post_dedup_event_bindings.parquet`、`post_dedup_population_contract.csv`
- 09B：`feature_contract.csv`、`feature_matrix.parquet`、`sample_uniqueness_weights.parquet`
- 08：`candidate_family_event_labels.parquet`、`run_manifest.json`
- 09A：`selected_label_event_bindings.parquet`、`topics/02_AFML_BIG_WINNER/configs/labels.yaml`

primary denominator 固定取值与 11A1 §3.2 一致：

| 字段 | 固定取值 |
| --- | --- |
| `population_id` | `10A__same_instrument_cooldown_10d` |
| `denominator_id` | `post_dedup_risk_on_r_core` |
| `admission_status` | `admitted` |
| `readout_only_flag` | `false` |

regime 回填规则与 11A1 §3.5 一致：

```text
analysis_regime_bucket =
  coalesce_non_empty(
    09A.episode_regime_bucket,
    10A.event_regime_bucket,
    09A.event_regime_bucket
  )
```

`winner_120` 标签需 `horizon_complete_120d == true`；horizon 不完整的样本进入 `class_unresolved`，只计数、不进入 retention 判定。

### 3.4 10C reference-slice reject decision（必需，本轮唯一的 reject 来源）

必需输入：

- `../10_riskon_layered_rejector_system_v0/outputs/manifests/10C_false_repair_rejector_manifest.json`
- `../10_riskon_layered_rejector_system_v0/outputs/local_cache/10C_false_repair_rejector/post_dedup_false_repair_scores.parquet`
- `../10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10C_false_repair_rejector/false_repair_threshold_frontier.csv`
- `../10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10C_false_repair_rejector/winner_retention_audit.csv`

#### 3.4.1 slice mode 选择（运行前冻结）

runner 必须先读 10C manifest，按下列规则确定 `rejector_slice_mode`，并写入 `rejector_decision_reconstruction_audit.csv`：

```text
if manifest.selected_capacity_id is not null
   and manifest.selected_threshold_id is not null
   and manifest.selected_cascade_status == "supported":
     rejector_slice_mode = selected_gate
     使用 manifest selected (capacity_id, threshold_id)
else:
     rejector_slice_mode = keep_9000_reference_slice   # 当前 10C 的实际状态
     使用下表固定 reference slice
```

当前 10C manifest 为 `selected_capacity_id = null`、`selected_cascade_status = blocked`、`decision = 10C_false_repair_feature_source_supported`，因此 **本轮预期 `rejector_slice_mode = keep_9000_reference_slice`**。该模式下所有 retention 结论只描述 `keep_9000` diagnostic reference slice，不得叙述为对已部署 rejector 的审计。

reference slice 固定取值（`keep_9000_reference_slice` 模式）：

| 字段 | 固定取值 |
| --- | --- |
| `model_id` | `regularized_logistic_false_repair_20d_l2_v1` |
| `ablation_id` | `full` |
| `capacity_id` | `keep_9000` |
| `threshold_id` | `keep_9000` |
| `population_id` | `10A__same_instrument_cooldown_10d` |
| `denominator_id` | `post_dedup_risk_on_r_core` |

注：`keep_9000` 在 `false_repair_threshold_frontier.csv` 中 `selected_flag = false`、`decision_block_reason = not_selected`。11B 明确把它当作 diagnostic reference slice，runner 必须在审计中记录 `slice_selected_flag = false`、`slice_decision_block_reason = not_selected`，并禁止 report 使用「已部署 / 已选中 rejector 工作点」措辞。

#### 3.4.2 row-level join key（运行前冻结，防止误 join）

10C `post_dedup_false_repair_scores.parquet` 含多 `(model_id, ablation_id, capacity_id, threshold_id)` 行。runner 必须先按 §3.4.1 的 slice 字段组过滤，过滤后再按下列 **composite key** join 到 11B evaluated denominator，**禁止**使用 `(instrument, event_t0_date)` 作为主 join：

```text
reject_join_key = sample_id | selected_target_id | denominator_id | input_event_key
```

`input_event_key` / `binding_canonical_event_id` 的来源与 fallback 优先级沿用 11A1 §4.1。10C score cache 的物化 scope 是 10A primary denominator before regime filter（当前约 15,802 行），11B 的 rejector-operating scope 是 `risk_on` pre-PIT R-core（当前约 11,293 行），primary scope 是 `risk_on ∩ strict PIT-valid`（当前约 4,665 行）。因此 join 审计必须分三层，不得要求 10C slice 过滤后行数直接等于 `risk_on_pre_pit_row_n` 或 4,665 PIT-valid evaluated denominator：

- 先在 10C score cache 上按 §3.4.1 slice 字段组过滤，必须审计 `slice_filtered_primary_denominator_row_n`，并满足 `slice_filtered_primary_denominator_row_n == pre_scope_primary_denominator_row_n`（预期约 15,802，按 §4.2 与 11A1 risk_on scope audit / 10A population contract 对账）；
- 在过滤后的 primary-denominator slice 内，`duplicate_reject_join_key_n == 0`（no duplicate）；
- 再按 `reject_join_key` join / filter 到 11B `risk_on` pre-PIT scope，必须审计 `slice_joined_risk_on_pre_pit_row_n`，并满足 `slice_joined_risk_on_pre_pit_row_n == risk_on_pre_pit_row_n`（预期约 11,293）；
- 最后按同一 `reject_join_key` join 到 11B PIT-valid evaluated denominator，必须审计 `slice_joined_pit_valid_row_n`，并满足 `slice_joined_pit_valid_row_n == evaluated_denominator_row_n`（预期约 4,665）；
- `risk_on_pre_pit_reject_join_unmatched_n == 0` 且 `pit_valid_reject_join_unmatched_n == 0`；
- 并 cross-check `instrument` / `event_t0_date` / `split` 一致。

若 primary-denominator slice 行数与 upstream primary denominator 不一致、join 到 risk_on pre-PIT 后行数与 `risk_on_pre_pit_row_n` 不一致、join 后 PIT-valid 行数与 evaluated denominator 不能 1:1 对齐（有重复、漏行、错 join 或多 slice 残留），最终状态不得高于 `11B_archetype_protected_retention_statistics_incomplete`；若 slice 完全无法定位（slice 字段组过滤后 0 行）则 `11B_archetype_protected_retention_input_blocked`。

#### 3.4.3 reject 决策派生规则（运行前冻结）

- runner 从过滤后的 slice 派生每个 event 的 `rejected_flag`：优先使用 10C 已物化的 reject/keep 决策列；若只存在连续 score，则使用该 slice 物化的 `keep_9000` 阈值还原 reject，并标 `reject_flag_reconstructed_from_threshold`。
- `retained_flag = NOT rejected_flag`。
- 11B 不得平移、重选或重训该阈值；不得对 score 重新分桶。
- 必须输出 `rejector_decision_reconstruction_audit.csv`，记录 `rejector_slice_mode`、slice 字段组、`slice_selected_flag`、join key、还原方式、`slice_filtered_primary_denominator_row_n`、`pre_scope_primary_denominator_row_n`、`slice_joined_risk_on_pre_pit_row_n`、`risk_on_pre_pit_row_n`、`slice_joined_pit_valid_row_n`、`evaluated_denominator_row_n`、`duplicate_reject_join_key_n`、`risk_on_pre_pit_reject_join_unmatched_n`、`pit_valid_reject_join_unmatched_n` 与命中率。

### 3.5 价格、PIT universe 与状态数据（必需，用于 PIT scope 与 left-tail 完整性）

与 11A1 §3.7 相同：

- PIT executable universe: `topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv`
- board metadata: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/instrument_metadata_target_universe.csv`
- SH name history dir: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/sh_name_history`
- SZ name history: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/stock_info_sz_change_name_short.csv`

PIT/status 数据用于 strict PIT inner join 与 denominator completeness（退市 / ST / 停牌不得使 left tail 失真）。

## 4. Evaluated denominator 与对账

### 4.1 重建规则

按 11A1 §3.2 / §3.5 口径重建 evaluated denominator：

```text
10A post_dedup_risk_on_r_core (admitted, readout_only=false)
  -> analysis_regime_bucket == risk_on
  -> strict PIT inner join on (instrument, event_t0_date) = (instrument, membership_date)
     WHERE is_listed=true AND is_st=false AND is_suspended=false
```

join key 与 canonical id policy 沿用 11A1 §4.1。

### 4.2 三层 scope 对账

11B 有三层 scope / denominator，必须都对账：

1. **score-cache scope（pre-regime primary denominator）**：10A `population_id = 10A__same_instrument_cooldown_10d`、`denominator_id = post_dedup_risk_on_r_core`、`admission_status = admitted`、`readout_only_flag = false` 的全 regime primary denominator（约 15,802 rows）。该 scope 只用于验证 10C score cache slice coverage，不进入 retention gate。
2. **rejector-operating scope（risk_on pre-PIT）**：`risk_on` R-core（约 11,293 rows），用于把 11B 重算的 winner_retention 与 10C 已发布 frontier 对账，确认 reject 决策被正确还原。
3. **primary scope（PIT-valid）**：`risk_on ∩ PIT-valid`，与 11A1/11A2 一致（约 4,665 evaluated rows）。所有 final status 由该 scope 决定。

必须输出 `scope_reconciliation_vs_upstream.csv`，按 split 比较：

- `split`
- `b_pre_scope_primary_denominator_row_n` / `a1_pre_scope_primary_denominator_row_n`
- `b_risk_on_pre_pit_row_n` / `a1_risk_on_pre_pit_row_n`
- `b_pit_valid_evaluated_row_n` / `a1_pit_valid_evaluated_row_n` / `a2_pit_valid_evaluated_row_n`
- `primary_denominator_row_n_match_flag`
- `pre_pit_row_n_match_flag`
- `pit_valid_row_n_match_flag`
- `reconciliation_status`

并输出 `rejector_retention_reconciliation_vs_10c.csv`，在 pre-PIT scope 上比较 11B 重算的 split 级 winner_retention 与 10C frontier 的 `train/validation/robustness_winner_retention`：

- `split`
- `b_recomputed_winner_retention`
- `c10c_published_winner_retention`
- `winner_retention_abs_diff`
- `retention_reconciliation_status`

若任一 split 的 `pre_scope_primary_denominator_row_n`、`risk_on_pre_pit_row_n` 或 `pit_valid_evaluated_row_n` 与 11A1 差异 `> denominator_drift_ceiling`（默认 0.5%），或 risk_on pre-PIT winner_retention 与 10C frontier 差异超过 `retention_recon_abs_diff_ceiling`（默认 0.02），最终状态不得高于 `11B_archetype_protected_retention_statistics_incomplete`。

`pit_valid_evaluated_row_n` 是 11B 的 **scope denominator**（预期 4,665），用于 scope 对账与整体计数；它不是 retention ratio 的直接分母。retention ratio 的分母是 §6.1 定义的 **eligible denominator**（horizon-complete 且 reject 决策可得的 winner / nonwinner）。`class_unresolved`（当前 11A2 为 2）只进入计数审计，不进入任何 retention ratio 分母。若 scope denominator 为空，最终状态为 `11B_archetype_protected_retention_input_blocked`。

## 5. Protected subgroup 定义

### 5.1 primary protected subgroup（gate-eligible）

| subgroup_id | 定义 | tier | gate 资格 |
| --- | --- | --- | --- |
| `winner_120_protected` | `winner_120 == true ∧ horizon_complete_120d == true` | primary | 唯一决定 final status |
| `nonwinner_reference` | `winner_120 == false ∧ horizon_complete_120d == true` | reference | 非歧视比较基准 |

retention gate 只由 `winner_120_protected` 相对 `nonwinner_reference` 的 retention 决定。

### 5.2 secondary readout subgroups（仅 readout，不决定 final status）

以下子群仅用于解释「rejector 误伤集中在哪类 winner」，**不**进入 gate，并按信息可得时点标注 tier：

| subgroup_id | 定义来源 | category | 说明 |
| --- | --- | --- | --- |
| `winner_shakeout_seed` | archetype profiling seed（shakeout） | A_t0_visible 若可得，否则 C_retrospective | profiling 报告显示 10C rejected winner 集中于 shakeout |
| `winner_volatile_chop_seed` | archetype profiling seed（volatile chop） | A_t0_visible 若可得，否则 C_retrospective | 同上 |
| `winner_gap_event_seed` | archetype profiling seed（gap event） | A_t0_visible 若可得，否则 C_retrospective | 同上 |

约束：

- 若某 seed 子群定义需要 forward / path 信息，必须标 `category = C_retrospective` 并只作 readout，绝不进入 gate 或 final status。
- 这些子群只在 `protected_subgroup_retention_readout.csv` 输出 retention 与计数；样本不足时标 `subgroup_underpowered`，不得给出歧视判定。

### 5.3 类别计数审计

必须输出 `protected_subgroup_count_audit.csv`：

- `split`
- `subgroup_id`（覆盖 §5.1 两类与 §5.2 全部 seed 子群，外加 `class_unresolved`）
- `category`
- `row_n`
- `weight_sum`（`final_sample_weight`，缺失记 1 并标 `weight_missing_fallback`）
- `unique_instrument_n`
- `subgroup_rate`

## 6. Retention 度量

### 6.1 基础 retention 量（每个 split × scope × subgroup）

分母层级明确为三层，不得混用：

- **scope denominator** = `pit_valid_evaluated_row_n`（§4.2，预期 4,665），只用于 scope 对账与整体计数。
- **eligible denominator** = 该 subgroup 中 `horizon_complete_120d == true` 且 reject 决策可得的行，是 retention ratio 的分母。
- **unresolved** = `class_unresolved`（horizon 不完整），单独计数审计，不进入任何 ratio 分母。

对每个 (split, scope, subgroup) 输出：

- `eligible_n`（horizon-complete 且 reject 决策可得的 winner / nonwinner；即 eligible denominator）
- `retained_n`
- `retention_rate = retained_n / eligible_n`
- `weighted_retention_rate`（按 `final_sample_weight`）
- `unique_instrument_n`
- `unresolved_excluded_n`（该 cell 因 horizon 不完整被排除、未进分母的行数）

scope ∈ {`pit_valid`（primary）, `pre_pit`（reconciliation-only）}。

### 6.2 非歧视度量（primary gate metric）

对每个 (split) 在 primary scope（pit_valid）上输出：

- `overall_retention = retained_n / eligible_n`（全 evaluated denominator）
- `winner_retention`（`winner_120_protected`）
- `nonwinner_retention`（`nonwinner_reference`）
- `relative_retention_winner_vs_nonwinner = winner_retention / nonwinner_retention`（**primary gate metric**）
- `relative_retention_winner_vs_overall = winner_retention / overall_retention`（secondary readout）
- `retention_gap_winner_minus_nonwinner = winner_retention - nonwinner_retention`

方向约定：`relative_retention_winner_vs_nonwinner < 1` 表示 winner 被 reject 得比非 winner 更多（潜在歧视方向）；`>= 1` 表示 winner 至少被同等保留。

### 6.3 bootstrap CI

- bootstrap_n: 1000
- random_seed: 20260617
- primary block level: `instrument`
- secondary block level: `binding_canonical_event_id`（仅 sensitivity）
- 每次 bootstrap 重算 §6.2 的 `relative_retention_winner_vs_nonwinner` 与 `retention_gap_winner_minus_nonwinner`。
- 输出 median、5%/95% CI，以及 `P(relative_retention_winner_vs_nonwinner < relative_retention_floor)`（歧视概率）与 `P(relative_retention_winner_vs_nonwinner >= 1.0)`。
- 若 secondary event-block 与 primary instrument-block 的歧视方向冲突，标 `episode_block_retention_conflict`。

## 7. 非歧视 gate

### 7.1 单轴 gate 定义

非歧视 gate 只在 primary scope（pit_valid）的 `train` 与 `robustness` 上判定（与讨论一致：retention gate 只在 train+robustness 上算）；`validation` 带 power guard 仅作 readout；`all` 仅展示。

对每个 split（train / robustness）：

```text
split_retention_status =
  non_discriminatory   if  winner_n >= retention_min_winner_n
                        AND unique_winner_instrument_n >= retention_min_winner_instrument_n
                        AND bootstrap_CI_low(relative_retention_winner_vs_nonwinner) >= relative_retention_floor
  discriminatory       if  winner_n / instrument 满足 power floor
                        AND bootstrap_CI_high(relative_retention_winner_vs_nonwinner) < relative_retention_floor
  ambiguous            if  power floor 满足但 CI 跨越 relative_retention_floor
  retention_underpowered  otherwise
```

- `relative_retention_floor`：§8 config 预注册，默认 `0.90`（winner retention 不得低于非 winner retention 的 90%）。
- power floor：`retention_min_winner_n`（默认 60）、`retention_min_winner_instrument_n`（默认 30）。

### 7.2 跨 split 汇总

```text
overall_retention_gate =
  non_discriminatory   if  train 与 robustness 均 non_discriminatory
  discriminatory       if  train 或 robustness 任一 discriminatory（且该 split 满足 power floor）
  ambiguous            if  train/robustness 至少一个 ambiguous，且无 discriminatory，且两个 split 都满足 power floor
  inconclusive_underpowered  if  train 与 robustness 均 retention_underpowered
  inconclusive_mixed_power   if  恰好一个 split retention_underpowered，另一个 split 为 non_discriminatory 或 ambiguous
                              （即单边有功率但不成对，不足以跨 split 定性）
```

优先级：discriminatory > ambiguous > inconclusive_mixed_power > inconclusive_underpowered > non_discriminatory。即只要任一满功率 split 判 discriminatory 或 ambiguous，先走该分支；仅当唯一满功率 split 为 non_discriminatory 而另一 split 欠功率时，才走 `inconclusive_mixed_power`。validation 的 split 结果不得改写 train/robustness 的汇总，也不得据此单独判 `discriminatory`。

### 7.3 validation power guard

- 仅当 validation 的 `winner_120_protected` 与 `nonwinner_reference` 两侧均满足 `row_n >= validation_min_class_n`（默认 30）且各侧 `unique_instrument_n >= validation_min_instrument_n`（默认 20）时，才允许写 validation 的歧视/非歧视结论；否则标 `validation_low_power`，只作 readout。
- 鉴于 11A1 报告 validation winner 仅约 16 个，本条预期触发 `validation_low_power`，这不是负面结论。

## 8. Config Contract（运行前冻结，入 manifest hash）

所有阈值与参数必须在 `configs/config_11b_archetype_protected_retention_readout.yaml` 预注册，运行前冻结，并在 manifest 记录 `config_sha256`：

| config key | 默认 | 用途 |
| --- | --- | --- |
| `relative_retention_floor` | `0.90` | §7.1 非歧视下限（winner vs nonwinner retention 比） |
| `retention_min_winner_n` | `60` | §2.4 / §7.1 winner 子群 power floor（row_n） |
| `retention_min_winner_instrument_n` | `30` | §2.4 / §7.1 winner 子群 power floor（unique instrument） |
| `validation_min_class_n` | `30` | §7.3 validation power guard 最小单侧 row_n |
| `validation_min_instrument_n` | `20` | §7.3 validation power guard 最小单侧 unique instrument |
| `denominator_drift_ceiling` | `0.005` | §4.2 与 11A1 scope drift 上限 |
| `retention_recon_abs_diff_ceiling` | `0.02` | §4.2 与 10C frontier winner_retention 对账上限 |
| `class_unresolved_ceiling` | `0.30` | §9.2 horizon 不完整占比上限 |
| `bootstrap_n` | `1000` | block bootstrap 次数 |
| `bootstrap_seed` | `20260617` | bootstrap seed |
| `multiple_comparison_null_n` | `500` | §8.1 子群 retention null permutation 次数 |
| `multiple_comparison_null_seed` | `20260617` | null permutation seed |

任何 config 项缺失，或与预注册默认不一致但未在 manifest 记录时，最终状态不得高于 `11B_archetype_protected_retention_statistics_incomplete`。

### 8.1 multiple-comparison audit（secondary 子群）

§5.2 的 seed 子群 retention 是多次比较，必须显式审计，防止把随机起伏读成「某类 winner 被歧视」。输出 `subgroup_multiple_comparison_audit.csv`：

- `total_tested_subgroup_cells`（seed_subgroup × split）
- `significant_cells_n`（CI 低于 floor 的 cell）
- `null_simulation_n`（>= 500，seed `20260617`）
- `null_expected_significant_cells_n`
- `null_significant_cells_p95`
- `actual_exceeds_null_p95_flag`
- `multiple_comparison_status`

null simulation：在每个 split 内随机置换 `retained_flag`，保持 marginal retention 不变，重算各 seed 子群 relative retention。该审计只用于校准 secondary 子群解释，**不得**用于事后增删子群或改写 §7 的 primary gate。

## 9. Diagnostic status 分类

11B 不授权任何东西，最终 `retention_summary.csv` 给出唯一 `final_status`：

| status | 条件 |
| --- | --- |
| `11B_archetype_protected_retention_non_discriminatory` | scope/对账/power 完整；§7.2 `overall_retention_gate == non_discriminatory`（train 与 robustness 均 non_discriminatory，CI 下界 >= floor），无 `episode_block_retention_conflict` 推翻 |
| `11B_archetype_protected_retention_discriminatory` | scope/对账/power 完整；§7.2 `overall_retention_gate == discriminatory`（train 或 robustness 满足 power floor 且 CI 上界 < floor），即 10C `keep_9000` reference slice 在 winner 子群上系统性过度 reject |
| `11B_archetype_protected_retention_ambiguous` | scope/对账/power 完整，但 §7.2 为 `ambiguous`（CI 跨越 floor，方向未定） |
| `11B_archetype_protected_retention_inconclusive_underpowered` | train 与 robustness 的 winner 子群均 `retention_underpowered`，无法定性（§2.4 条款 1 触发，不得降 floor 救活） |
| `11B_archetype_protected_retention_inconclusive_mixed_power` | §7.2 为 `inconclusive_mixed_power`：恰好一个 split 欠功率，另一个 split 为 non_discriminatory 或 ambiguous，跨 split 证据不足以定性 |
| `11B_archetype_protected_retention_statistics_incomplete` | 输入可读，但 scope 对账、slice 过滤 / join、reject 还原、horizon、power 或 config 审计不完整 |
| `11B_archetype_protected_retention_input_blocked` | global input gates 失败 |

### 9.1 global input gates（任一失败 -> input_blocked）

- 主输入文件缺失（10A / 09B / 08 / 09A / 10C scores / 10C manifest / PIT universe / 11A1 scope 审计表）。
- evaluated denominator 为空。
- 10C reference slice 无法在 scores cache 上定位（§3.4.1 slice 字段组过滤后 0 行）或 reject 决策无法还原（`rejected_flag` 全缺失或还原命中率为 0）。
- `risk_on ∩ PIT-valid` 重建与 11A1 无法对账（无任何 split 可比）。

### 9.2 不得 input_blocked、但 ceiling 到 statistics_incomplete

- 与 11A1 denominator drift `> denominator_drift_ceiling`。
- §3.4.2 slice 过滤后与三层 scope 不能逐层 1:1 对齐（primary-denominator coverage、risk_on pre-PIT join、PIT-valid join 任一重复 / 漏行 / 多 slice 残留）。
- pre-PIT winner_retention 与 10C frontier 对账差异 `> retention_recon_abs_diff_ceiling`。
- horizon 完整性导致 `class_unresolved` 占比 `> class_unresolved_ceiling`（默认 0.30）。
- PIT-valid evaluated denominator 无法识别 delisted/ST/left-tail 状态（`denominator_completeness_st_delist_audit.csv` 标 `left_tail_status_audit_incomplete`）。
- config contract 缺失或未入 manifest hash。

### 9.3 预注册结论

- 若 `non_discriminatory`：预注册结论为「在当前 `risk_on ∩ PIT-valid` 数据与 10C `keep_9000` diagnostic reference slice 上，winner 子群相对非 winner 没有显著 retention 歧视；该结论只描述 reference slice，不构成对任何已部署 rejector 工作点的背书；11C 在设计 two-stage policy 时无需为 winner retention 单独引入 carve-out，但仍须在 11C 计算带成本与可成交性的策略 EV」。
- 若 `discriminatory`：预注册结论为「10C `keep_9000` reference slice 在 winner 子群上 retention 显著偏低，11C 必须把 winner retention 损失作为显式成本纳入策略 EV，并在 11C（而非 11B）评估是否需要 rejector carve-out / 工作点调整；11B 本身不放宽、不重选 10C」。
- 若 `ambiguous` / `inconclusive_underpowered` / `inconclusive_mixed_power`：预注册结论为「当前数据不足以判定 reference slice 对 winner 的非歧视性，retention 维度暂作 readout-only，不得据此放宽或收紧 10C」。
- 若 `statistics_incomplete` / `input_blocked`：先补数据完整性 / scope 对账，不做策略化解释。

## 10. 输出文件

### 10.1 publishable tables

输出目录：

```text
outputs/publishable/tables/11B_archetype_protected_retention_readout/
```

必须生成：

- `input_artifact_audit.csv`
- `scope_reconciliation_vs_upstream.csv`
- `denominator_contract_audit.csv`
- `denominator_completeness_st_delist_audit.csv`
- `rejector_decision_reconstruction_audit.csv`
- `rejector_retention_reconciliation_vs_10c.csv`
- `protected_subgroup_count_audit.csv`
- `retention_rate_readout.csv`（split × scope × subgroup）
- `non_discrimination_metric_readout.csv`（split，含 relative retention、gap、CI）
- `protected_subgroup_retention_readout.csv`（§5.2 seed 子群 readout）
- `bootstrap_retention_readout.csv`（含 median / CI / 歧视概率）
- `subgroup_multiple_comparison_audit.csv`
- `retention_summary.csv`（唯一 final_status）

### 10.2 local cache

输出目录：

```text
outputs/local_cache/11B_archetype_protected_retention_readout/
```

允许生成（只能包含 strict PIT 后的 `risk_on ∩ PIT-valid` evaluated rows，外加 pre-PIT reconciliation rows 单独标注 scope）：

- `retention_evaluated_denominator.parquet`
- `bootstrap_samples.parquet`

manifest 必须记录每个 cache 的 path、sha256、row_count、schema。

### 10.3 report 与 manifest

必须生成：

- `outputs/publishable/reports/11B_archetype_protected_retention_readout_report.md`
- `outputs/publishable/manifest_11B_archetype_protected_retention_readout.json`

报告必须包含：

1. 数据来源、与 11A1/11A2 的 scope 对账结果、与 10C frontier 的 winner_retention 对账结果。
2. evaluated denominator row count 与 `winner_120_protected` / `nonwinner_reference` 计数（分 split）。
3. primary scope 下各 split 的 `overall_retention` / `winner_retention` / `nonwinner_retention` / `relative_retention_winner_vs_nonwinner` 与 bootstrap CI。
4. §7 非歧视 gate 的 split 级与汇总结果（train/robustness 决定，validation 标 power guard）。
5. §5.2 seed 子群 retention readout 与 multiple-comparison 审计（明确这些只是 readout，不决定 final status）。
6. `final_status` 与 §9.3 预注册结论。
7. 明确边界声明：11B 仅诊断 retention 非歧视性，不授权 routing/entry/exit、不放宽 10C、不 claim 策略 EV。

## 11. 验证要求

### 11.1 单元测试

`tests/test_archetype_protected_retention_readout.py` 至少覆盖：

- evaluated denominator 重建与 11A1/11A2 scope 对账（drift 阈值触发 statistics_incomplete）。
- slice mode 选择：当 10C manifest `selected_capacity_id` 为 null / `selected_cascade_status != supported` 时，`rejector_slice_mode == keep_9000_reference_slice`，且 report/审计标 `slice_selected_flag = false`、不得使用「已部署 rejector 工作点」措辞；仅当 manifest 真有 selected gate 时才 `rejector_slice_mode == selected_gate`。
- 10C reference slice 还原：先按 slice 字段组 `(model_id, ablation_id, capacity_id, threshold_id, population_id, denominator_id)` 过滤到 score-cache primary denominator，要求 `slice_filtered_primary_denominator_row_n == pre_scope_primary_denominator_row_n`；再按 composite key `sample_id|selected_target_id|denominator_id|input_event_key` join/filter 到 risk_on pre-PIT scope，要求 `slice_joined_risk_on_pre_pit_row_n == risk_on_pre_pit_row_n`；最后 join 到 PIT-valid evaluated denominator，要求 `slice_joined_pit_valid_row_n == evaluated_denominator_row_n`；任一层 mismatch、duplicate 或 unmatched 触发 statistics_incomplete；slice 字段组过滤后 0 行触发 input_blocked。
- 不得用 `(instrument, event_t0_date)` 作为 10C reject 主 join。
- `retained_flag = NOT rejected_flag`；reject 决策全缺失或还原命中率为 0 触发 input_blocked。
- pre-PIT winner_retention 与 10C frontier（train 0.896 / validation 0.758 / robustness 0.871 数量级）对账，差异超阈触发 statistics_incomplete。
- 分母三层语义：scope denominator = `pit_valid_evaluated_row_n`（4,665）；retention ratio 分母 = winner/nonwinner horizon-complete eligible；`class_unresolved` 单独审计、不进入任何 ratio 分母。
- `winner_120_protected` 与 `nonwinner_reference` 互斥且并集等于 horizon-complete evaluated denominator；horizon 不完整 -> `class_unresolved`。
- primary gate metric 为 `relative_retention_winner_vs_nonwinner`，gate 单轴，不混入 false_repair capture / EV / failure exposure。
- power floor：winner 子群样本不足 -> `retention_underpowered`；train 与 robustness 同时欠功率 -> `inconclusive_underpowered`；恰好一个 split 欠功率、另一个 non_discriminatory/ambiguous -> `inconclusive_mixed_power`；且不得通过降低 floor 改判。
- gate 只在 train/robustness 上判定；validation 触发 `validation_low_power` 时不得写 discriminatory，也不得改写汇总。
- gate 方向：CI 下界 >= floor -> non_discriminatory；CI 上界 < floor -> discriminatory；CI 跨 floor -> ambiguous。
- bootstrap：instrument-block 重采样重算 relative retention 与 gap，输出歧视概率；event-block 方向冲突标 `episode_block_retention_conflict`。
- secondary seed 子群只进 readout 与 multiple-comparison audit，不进入 gate / final status；retrospective 定义的子群标 `category = C_retrospective`。
- multiple-comparison null permutation：置换 `retained_flag` 保持 marginal retention，输出 `actual_exceeds_null_p95_flag`，且不得据此改写 primary gate。
- config contract：所有 §8 阈值入 manifest `config_sha256`；`relative_retention_floor == 0.90`；缺失或未记录时 ceiling 到 statistics_incomplete。
- regime scope：仅 `risk_on ∩ PIT-valid` 进入判定，`risk_off`/`transition` 只计数。
- final status precedence（input_blocked / statistics_incomplete / non_discriminatory / discriminatory / ambiguous / inconclusive_mixed_power / inconclusive_underpowered）。

### 11.2 运行验证

实现后至少运行：

```bash
uv run python -m pytest tests/test_archetype_protected_retention_readout.py
uv run python src/run_11b_archetype_protected_retention_readout.py --config configs/config_11b_archetype_protected_retention_readout.yaml
```

若无 `uv` 环境，允许使用项目既有 Python runner，但必须在 report 中记录实际命令。

### 11.3 artifact validation

- publishable CSV 均非空，除非 final_status 是 input_blocked。
- manifest 中所有 publishable artifact sha256 可复算。
- `retention_summary.csv` 只有一个 final_status。
- report 引用的核心数值能在 CSV 中定位。

## 12. 报告措辞约束

报告不得使用以下措辞：

- “11B 证明 rejector 应该放行某些 winner”
- “可以据此 override 10C”
- “11B 给出策略 EV”
- “retention 通过 = 策略有效”

允许使用：

- “protected retention readout”
- “non-discriminatory / discriminatory retention”
- “winner retention 相对非 winner 非劣 / 受损”
- “diagnostic-only readout”
- “retention 维度暂作 readout-only”

## 13. 后续依赖

11B 的唯一合法下游用途是为 `11C_two_stage_observed_state_policy_replay_v0` 提供 rejector 非歧视维度的输入：

- 若 `non_discriminatory`：11C 在围绕 11A2 的 `K*=3` two-stage 结构设计策略时，无需为 winner retention 单独引入 carve-out，但 retention 仍只是诊断，策略 EV 必须在 11C 带成本、可成交性、组合容量重新计算。
- 若 `discriminatory`：11C 必须把 winner retention 损失作为显式成本纳入策略 EV，并在 11C 评估是否需要 rejector carve-out / 工作点调整。11B 本身不放宽 10C。
- 若 `ambiguous` / `inconclusive_underpowered`：retention 维度暂作 readout-only，不得据此放宽或收紧 10C；如需结论，需先补样本 / 功率。
- 若 `statistics_incomplete` / `input_blocked`：先补数据完整性 / scope 对账，不做策略化解释。

> 最关键的一句话：**11A1 证明没有 t0 proxy 值得放行，11A2 证明 t0 后第 3 日存在可交易的早期路径解耦；11B 只回答一个对称问题——现有 10C rejector 在压制 false_repair 的同时，是否对 big winner 子群非歧视。只有 11A1（screen）、11A2（separation）、11B（non-discrimination）三个诊断都到位，11C 才能在带成本与组合容量的前提下第一次计算策略 EV。**

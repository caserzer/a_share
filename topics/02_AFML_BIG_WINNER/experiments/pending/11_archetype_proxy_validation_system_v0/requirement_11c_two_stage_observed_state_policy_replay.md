# 需求：11C Two-stage Observed-state Policy Replay

## 0. 本需求要回答的问题

11A1 已经证明：在 `risk_on ∩ strict PIT-valid` 分母内，t0 snapshot proxy 会同时抬高 winner 与 failure 暴露，结论是 t0 处 winner/failure 纠缠，而不是 t0 完全无信息。

11A2 已经进一步证明：同一 frozen denominator 内，C1 主对比（`class_big_winner` vs `class_big_failure_proxy_nonwinner`）在 t0 后第 3 个交易日形成 full-cohort dual-channel Tier3 confirmed divergence，且 `winner_median_ep_mfe_to_Kstar / mfe_120_recomputed = 4.331%`，状态为 `tradable_window_open`。

11B 则提供 10C `keep_9000` diagnostic reference slice 对 winner 子群的 protected retention readout。11C 必须把 11B 作为上游诊断输入，但不得把 11B 的 retention 读数解释成 10C override 授权。

11C 不再回答「K=3 能不能分离」。11C 只回答一个策略化问题：

> 在 `risk_on ∩ strict PIT-valid` 分母内，基于 K=3 early-path observed state 的 two-stage policy，是否在真实执行约束、交易成本、资金占用、涨跌停成交约束、容量与集中度约束之后，优于当前 baseline？

11C 的成功标准不是收益均值最高，而是：

1. 相对 current baseline，net EV per exposure-day 提升。
2. failure exposure 不恶化。
3. right-tail winner capture 不塌缩。
4. 结果不依赖少数 top-k instrument / episode。
5. 容量、现金拖累、涨跌停未成交、跌停无法退出和交易成本没有把收益吃掉。

11C 是 policy replay，不是上线授权。任何正向结论只能说明「two-stage observed-state policy 值得继续进入更严格 execution/backtest」，不得写成 production-ready strategy。

## 1. 实验名称与状态

- experiment_id: `11_archetype_proxy_validation_system_v0`
- primary_run_id: `11C_two_stage_observed_state_policy_replay_v0`
- parent_experiment_id: `10_riskon_layered_rejector_system_v0`
- upstream_run_ids:
  - `11A1_archetype_proxy_robust_payoff_risk_audit`
  - `11A2_post_t0_archetype_path_divergence_diagnostic`
  - `11B_archetype_protected_retention_readout`
  - `10C_false_repair_rejector`
- status: `spec_frozen_pending_implementation`
- expected_entrypoint: `src/run_11c_two_stage_observed_state_policy_replay.py`
- expected_config: `configs/config_11c_two_stage_observed_state_policy_replay.yaml`
- expected_test_file: `tests/test_two_stage_observed_state_policy_replay.py`

## 2. 核心原则

### 2.1 11C 与 11A2 的边界

11A2 的合法用途只有一个：证明 K=3 observed state 值得付费做 replay。11C 不得重复包装 11A2 的分离读数作为策略结论。

11C 必须从实际 replay ledger 出发，计算：

- 什么时候能买入；
- 买入多少；
- 是否因为涨停、停牌、现金不足而未成交；
- 什么时候升级、退出或继续持有；
- 退出是否因为跌停、停牌、退市而失败；
- 扣除成本后收益、暴露天数、资金占用和集中度如何；
- winner capture 与 failure exposure 相对 baseline 如何变化。

### 2.2 不得 override 10C

11A2 不授权替代 10C。11C 不得出现以下逻辑：

```text
K3 state-positive => override 10C at t0
```

#### 2.2.1 10C 当前状态（运行前必须承认）

当前 10C manifest 为 `decision = 10C_false_repair_feature_source_supported`、`decision_block_reasons = ["no_train_supported_capacity"]`、`selected_capacity_id = null`、`selected_threshold_id = null`、`selected_cascade_status = blocked`、`source_caveated = true`。也就是说 **10C 没有一个被选中、被部署的 false-repair rejector 工作点**。

因此 11C 的 deployed baseline cascade 只能是 **10A admitted + 10B selected gate（`keep_9400`）**；10C 只以 `keep_9000` **diagnostic reference slice** 进入 lane 划分，且必须显式标注「这是诊断切片，不是已部署 rejector」。11C 不得宣称自己在替代 / 放宽一个已部署的 10C 工作点（因为它根本不存在）。

11C 必须把 10C `keep_9000` reference slice 处理为 lane replay：

| lane_id | 样本 | 合法解释 |
| --- | --- | --- |
| `lane_A_10C_ref_kept` | 10C `keep_9000` reference slice 未 rejected 的候选（且 10B 未 reject） | 研究 K3 state 是否改善 upgrade / hold / exit / sizing |
| `lane_B_10C_ref_rejected` | 10C `keep_9000` reference slice rejected 的候选 | 只做 delayed-confirmation rescue counterfactual / readout；不得改写 B0 deployed baseline，B0 仍包含这些 10B-kept 行的 current-baseline exposure |

Lane B 不得被写成「放宽 10C」。正确解释是：

```text
10C 当前没有已部署工作点；keep_9000 只是诊断切片；
被该切片标记 rejected 的样本如果后续路径自证，只能作为新的 observed-state event 进入 delayed replay。
```

若 Lane B 的 state-positive entry 样本量或 winner 数不足，Lane B rescue 只能 readout，不得进入 policy conclusion；但该低功率状态不得阻断 Lane A / whole-deployed-baseline 的 two-stage policy conclusion。

### 2.3 label tautology 防线

11A2 已经指出：K=10 时 EP8B touch 与 fast-fail 标签完全重合；K=5 时 fast-fail touch overlap 已有 35.19%。因此 11C 主 policy feature 只能来自 K=3 真实可观察价格/成交状态，不得使用 label-overlap 字段。

Allowed primary observed-state feature family：

- `K3_return_from_executable_anchor`
- `K3_max_drawdown_path_damage`
- `K3_close_position_reclaim_status`
- `K3_liquidity_volume_confirmation`
- `K3_executable_status`

Readout-only / forbidden primary：

- `selected_fast_fail_touch_pos`
- `selected_fast_fail_touch_offset_sessions`
- `selected_fast_fail_touch_date`
- `selected_fast_fail_barrier_id`
- any label-derived barrier field
- future `MFE` / `MAE` beyond K=3
- `winner_120`
- `forward_return_120d`
- any 20D / 120D outcome or horizon-complete flag as state feature

fast-fail touch 只能进入 `label_overlap_policy_audit.csv`，不得进入 `observed_state_definition_registry.csv` 的 primary rows、policy routing、sizing、entry、exit 或 final decision。

### 2.4 denominator 不得扩张

11C 主分母必须沿用 11A1/11A2 frozen denominator：

```text
10A post-dedup R-core
  -> analysis_regime_bucket == risk_on
  -> strict PIT-valid at event_t0_date
  -> 4,665 evaluated rows
```

不得把 11A1 中被 PIT 排除的 6,628 行混回主分母。那些样本尤其包含 `before_first_pit_membership` winner-rate 偏高的问题，是另一个「入池前 winner」课题，不属于当前可执行 universe。

被 PIT 排除行只能进入 out-of-scope diagnostic，不得进入 policy metrics、bootstrap、top-k sensitivity、capacity utilization 或 final status。

## 3. 必需输入

### 3.1 11A / 11B frozen diagnostic 输入

11C 必须读取并对账以下 11A / 11B artifact：

- `outputs/publishable/manifest_11A1_archetype_proxy_robust_payoff_risk_audit.json`
- `outputs/publishable/manifest_11A2_post_t0_archetype_path_divergence_diagnostic.json`
- `outputs/publishable/manifest_11B_archetype_protected_retention_readout.json`
- `outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/risk_on_scope_filter_audit.csv`
- `outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/pit_universe_scope_filter_audit.csv`
- `outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/pit_universe_exclusion_diagnostic.csv`
- `outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/diagnostic_summary.csv`
- `outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/divergence_onset_readout.csv`
- `outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/tradability_lag_readout.csv`
- `outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/early_path_feature_registry.csv`
- `outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/label_overlap_tautology_audit.csv`
- `outputs/publishable/tables/11B_archetype_protected_retention_readout/retention_summary.csv`
- `outputs/publishable/tables/11B_archetype_protected_retention_readout/non_discrimination_metric_readout.csv`
- `outputs/publishable/tables/11B_archetype_protected_retention_readout/rejector_decision_reconstruction_audit.csv`

若存在以下 local cache，11C 可以消费其 K3 feature values，但必须校验 manifest hash，并且只能使用 `K == 3` 且 `cohort == full_cohort` 的 4,665 行：

- `outputs/local_cache/11A2_post_t0_archetype_path_divergence_diagnostic/early_path_feature_matrix.parquet`

身份约束：当前 11A2 `early_path_feature_matrix.parquet` 是 K/cohort 展开矩阵，可能只含 `row_id`、`instrument`、`event_t0_date`，不保证含 `sample_id` / `selected_target_id` / `denominator_id` / `input_event_key`。因此 11C 不得把 11A2 `row_id` 单独当作 cross-artifact join key。若直接消费 11A2 cache，runner 必须满足下列任一条件：

- 读取一个 manifest 记录且可 hash 的 `row_id -> policy_row_id` mapping artifact；
- 或按 §4.2 从 10A frozen evaluated denominator 重建同一 4,665 行顺序，并输出 `k3_row_id_rehydration_audit.csv`，证明 `(row_id, instrument, event_t0_date, split)` 与 10A composite identity 一一对应、无重复、无 unmatched。

若上述 identity rehydration 不能证明一一对应，runner 必须按 11A2 公式从 10A evaluated denominator 和 qfq/status 数据重建 K3 feature matrix，并保留 §4.2 的 `policy_row_id`；不得只用 `(instrument, event_t0_date)` 作为主 join。

11C input gate：

| 字段 | 必须满足 |
| --- | --- |
| 11A2 final_status | `11A2_post_t0_archetype_path_divergence_separation_detected_tradable` |
| C1 full-cohort confirmed K* | `3` |
| evaluated row count | `4665` |
| unique instruments | `593` |
| winner realized fraction status | `tradable_window_open` |
| 11B final_status | one of `11B_archetype_protected_retention_non_discriminatory`, `11B_archetype_protected_retention_discriminatory`, `11B_archetype_protected_retention_ambiguous`, `11B_archetype_protected_retention_inconclusive_underpowered`, `11B_archetype_protected_retention_inconclusive_mixed_power` |

若 11A2 gate 任一项不满足，11C 必须 `11C_two_stage_policy_input_blocked`，不得继续输出 policy conclusion。若 11B artifact 缺失、hash 不可复算、`retention_summary.csv` 没有唯一 final_status，或 11B final_status 为 `statistics_incomplete` / `input_blocked`，11C 最终状态不得高于 `11C_two_stage_policy_statistics_incomplete`，不得输出 positive policy conclusion。

11B 对 11C 的解释作用：

- 若 11B `non_discriminatory`：11C 不需要为 winner retention 单独加入 carve-out，但仍必须按 §9.4 检查 winner capture。
- 若 11B `discriminatory`：11C 必须把 10C `keep_9000` reference-slice 的 winner-retention 损失作为显式 diagnostic cost 写入 report，并在 failure-mode table 中单独标注；不得把 Lane B rescue 写成放宽 10C。
- 若 11B `ambiguous` / `inconclusive_underpowered` / `inconclusive_mixed_power`：11C 可以继续 replay，但 retention 维度只能 readout；final report 必须声明 10C reference-slice retention 证据不足，不能据此支持 carve-out。

### 3.2 10A / 10B / 10C current baseline 输入

11C 必须读取：

- `../10_riskon_layered_rejector_system_v0/outputs/manifests/10A_density_rule_system_manifest.json`
- `../10_riskon_layered_rejector_system_v0/outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet`
- `../10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10A_density_rule_system/post_dedup_population_contract.csv`
- `../10_riskon_layered_rejector_system_v0/outputs/manifests/10B_fast_fail_structural_gate_manifest.json`
- `../10_riskon_layered_rejector_system_v0/outputs/local_cache/10B_fast_fail_structural_gate/post_dedup_fast_fail_scores.parquet`
- `../10_riskon_layered_rejector_system_v0/outputs/manifests/10C_false_repair_rejector_manifest.json`
- `../10_riskon_layered_rejector_system_v0/outputs/local_cache/10C_false_repair_rejector/post_dedup_false_repair_scores.parquet`
- `../10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10C_false_repair_rejector/false_repair_threshold_frontier.csv`
- `../10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10C_false_repair_rejector/cascade_overlap_attribution.csv`

#### 3.2.1 deployed baseline gate（10A + 10B selected）

deployed baseline cascade 仅由 **10A admitted + 10B selected gate** 构成。10B selected gate 必须来自 10B manifest authoritative selected fields，不得硬编码：

```text
10B.manifest.selected_model_id
10B.manifest.selected_capacity_id
10B.manifest.selected_threshold_id
10B.manifest.selected_population_id
10B.manifest.selected_denominator_id
10B.manifest.selected_operating_point.ablation_id
```

当前 10B 预期值为 `selected_model_id = regularized_logistic_fast_fail_10d_l2_v1`、`selected_capacity_id = keep_9400`、`selected_threshold_id = keep_9400`、`selected_population_id = 10A__same_instrument_cooldown_10d`、`selected_denominator_id = post_dedup_risk_on_r_core`、`selected_operating_point.ablation_id = full`。`actual_10b_selected_*` 字段属于 10C manifest 的交叉审计字段，不得作为 10B selected gate 的 authoritative source。若 10B manifest-selected gate 与 scores cache 无法一一过滤出 row-level selected flags，deployed baseline 不可重建，final status 必须为 `11C_two_stage_policy_input_blocked`。

#### 3.2.2 10C reference slice（非 deployed gate，运行前冻结）

runner 必须先读 10C manifest 判断是否存在 selected gate：

```text
if 10C.manifest.selected_capacity_id is not null
   and 10C.manifest.selected_threshold_id is not null
   and 10C.manifest.selected_cascade_status == "supported":
     tenc_slice_mode = selected_gate            # 使用 manifest selected (capacity_id, threshold_id)
else:
     tenc_slice_mode = keep_9000_reference_slice  # 当前 10C 实际状态
```

当前 10C manifest 为 `selected_capacity_id = null`、`selected_cascade_status = blocked`、`decision = 10C_false_repair_feature_source_supported`，因此 **本轮预期 `tenc_slice_mode = keep_9000_reference_slice`**。该模式下 10C 的 reject flag 来自 `keep_9000` diagnostic reference slice（`false_repair_threshold_frontier.csv` 中 `selected_flag = false`、`decision_block_reason = not_selected`），只用于 lane 划分与 §10 Lane B 诊断，**不进入 deployed baseline，不构成对已部署 rejector 的替代或放宽**。

关键纪律：10C **没有** selected gate 不得触发 `11C_two_stage_policy_input_blocked`；只有 deployed baseline（10A + 10B selected）不可重建，或 10C `keep_9000` reference slice 在 scores cache 上无法定位（slice 字段组过滤后 0 行）时，才 input_blocked。runner 必须在 `lane_population_audit.csv` 记录 `tenc_slice_mode`、`tenc_slice_selected_flag`、`tenc_slice_decision_block_reason`。

### 3.3 label / outcome readout 输入

Outcome labels 只用于评估，不得用于 K3 state 或 policy decision：

- `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet`
- `../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet`
- `topics/02_AFML_BIG_WINNER/configs/labels.yaml`

必须至少可获得或重建：

- `winner_120`
- `forward_return_120d`
- `selected_fast_fail_10_label`
- `frozen_false_repair_20d_label`
- `selected_cost_bad_10_20_target`
- `horizon_complete_10d`
- `horizon_complete_20d`
- `horizon_complete_120d`
- `event_t0_date`
- `event_window_anchor_date`
- `event_window_anchor_pos`
- `trade_time`（作为 executable anchor cross-check）

这些字段不得进入 `observed_state_definition_registry.csv` 的 primary feature rows。

### 3.4 price / PIT / status 输入

11C 是 replay，因此价格与状态数据是一等输入：

- PIT executable universe: `topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv`
- qfq primary dir: `topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq`
- qfq fallback dir: `topics/02_AFML_BIG_WINNER/data/interim/qlib_csv/day`
- board metadata: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/instrument_metadata_target_universe.csv`
- SH name history dir: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/sh_name_history`
- SZ name history: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/stock_info_sz_change_name_short.csv`

qfq daily bar 至少包含：`instrument`, `date`, `open`, `high`, `low`, `close`, `volume`, `money`。

PIT/status scope：

- strict PIT eligibility 只在 `event_t0_date` 判断：`is_listed=true ∧ is_st=false ∧ is_suspended=false`。
- 11C 不处理 post-t0 / future-ST 状态：t0 之后进入 ST 不触发 fill、剔除、exit、capacity ceiling 或 final status。
- t0 之后的停牌、无成交、退市必须进入 execution replay 和 failed-exit audit。

## 4. 主分母与 row identity

### 4.1 evaluated denominator

主分母固定为：

```text
population_id = 10A__same_instrument_cooldown_10d
denominator_id = post_dedup_risk_on_r_core
admission_status = admitted
readout_only_flag = false
analysis_regime_bucket = risk_on
strict PIT-valid at event_t0_date
```

预期规模：

| item | expected |
| --- | ---: |
| evaluated_row_n | 4,665 |
| unique_instrument_n | 593 |
| class_big_winner_n | 446 |
| class_big_failure_proxy_nonwinner_n | 1,533 |
| subclass_fast_fail_n | 436 |
| subclass_false_repair_only_n | 1,097 |

若重建 row count 与 11A2 发布值不一致，且差异不能由 manifest hash 变更解释，final status 不得高于 `11C_two_stage_policy_statistics_incomplete`。

### 4.2 row identity

所有 replay rows 必须保留稳定主键：

```text
policy_row_id =
  sample_id | selected_target_id | denominator_id | event_t0_date | instrument
```

若上游缺少 `sample_id`，允许以 10A `input_event_key` 的已验证 components 补齐，但必须输出 `row_identity_source = input_event_key_components`。不得只用 `(instrument, date)` 去重，因为同一 instrument/date 可能对应多个 target/denominator 语义。

K3 feature join 必须以 `policy_row_id` 为主键。若使用 11A2 `early_path_feature_matrix.parquet`，必须先按 §3.1 完成 `row_id` identity rehydration；若无法 rehydrate，则重建 K3 feature matrix。`k3_observed_state_matrix.parquet` 必须包含 `policy_row_id`、`sample_id`、`selected_target_id`、`denominator_id`、`input_event_key`、`instrument`、`event_t0_date`、`split`，且 `(policy_row_id)` 唯一。

### 4.3 split 使用规则

split 必须沿用上游 frozen split：

- `train`
- `validation`
- `robustness`

K3 state definition / threshold / arm selection 只能用 train split 冻结。validation / robustness 只能阻断或确认，不得参与选 state、选 arm、选 trial size、选 upgrade size。

## 5. Policy lanes 与 arms

### 5.1 Lane 构造

row-level flags（10B 为 deployed selected gate；10C 为 `keep_9000` reference slice，见 §3.2）：

```text
tenb_rejected_flag = 10B manifest-selected candidate_rejected_flag         # deployed
tenc_ref_rejected_flag = 10C keep_9000 reference-slice candidate_rejected_flag  # diagnostic, NOT deployed
deployed_baseline_kept_flag = (not tenb_rejected_flag)                     # 当前已部署 cascade = 10A admitted + 10B selected
```

Lane A / B（lane 划分用 deployed baseline 与 10C reference slice 联合定义）：

```text
lane_A_10C_ref_kept:
  deployed_baseline_kept_flag == true AND tenc_ref_rejected_flag == false

lane_B_10C_ref_rejected:
  deployed_baseline_kept_flag == true AND tenc_ref_rejected_flag == true
```

说明：

- Lane 只在 deployed baseline 已保留（10B 未 reject）的样本内，按 10C `keep_9000` reference slice 是否 reject 再分 A/B。被 10B reject 的样本不进入 Lane A/B（它们已被 deployed cascade 在 t0 排除，不属于 11C 的 K3 two-stage 研究范围）。
- `tenb_rejected_flag` 与 `tenc_ref_rejected_flag` 必须分别输出，不得只输出合并 rejected 状态。
- 由于 10C 当前无 selected gate，`tenc_ref_rejected_flag` 必须标注来源 `tenc_slice_mode = keep_9000_reference_slice`，不得叙述为已部署 rejector 的决策。

### 5.2 Policy arms

11C 至少 replay 以下 arms：

| arm_id | lane | entry / sizing contract | 解释 |
| --- | --- | --- | --- |
| `B0_deployed_baseline` | A ∪ B | deployed cascade kept rows（10A admitted + 10B selected，忽略 10C reference slice），按 §7.4 同一 exit contract 重放；B0 的 entry timing 固定为 `t0+1` executable open full entry（与 B1 同 entry，作为 deployed 对照锚点） | 当前已部署 cascade 对照组 |
| `B1_immediate_full_entry` | A ∪ B | `t0+1` executable open full entry，按同一 exit contract；candidate set 与 B0 相同，用作 replay registry / timing sanity check，预期与 B0 ledger 完全一致 | 不等待 K3 的 full exposure 对照 |
| `B2_wait_confirm_K3` | A policy + B baseline carry | Lane A：t0 不建仓；t0+3 close 计算 K3 state；t0+4 open 只进入 state-positive。Lane B：保持 B0 current-baseline exposure，不由 K3 改写 | observation-first composite policy |
| `B3_trial_then_upgrade_K3` | A policy + B baseline carry | Lane A：t0+1 open trial size；t0+3 close 计算 K3 state；t0+4 open state-positive upgrade，state-negative exit/no-upgrade。Lane B：保持 B0 current-baseline exposure，不由 K3 改写 | staged sizing composite policy |
| `LB0_rejected_no_trade` | B | diagnostic-only reference no-trade counterfactual；不是 deployed baseline | Lane B rescue 对照 |
| `LB2_delayed_rescue_K3` | B | t0 不建仓；K3 state-positive 才在 t0+4 open 作为新 observed-state event entry | delayed-confirmation rescue readout |

Lane B 不允许 `B2_wait_confirm_K3` 或 `B3_trial_then_upgrade_K3` 的 K3 routing 作为 top-level policy conclusion，因为这会变成 t0 override 10C reference slice。`B0_deployed_baseline` / `B1_immediate_full_entry` 必须包含 Lane B，因为 10C reference slice 不是 deployed gate；B2/B3 的 top-level policy ledger 必须是 composite ledger：Lane A 应用 K3 policy，Lane B 使用 B0 current-baseline exposure carry-through。若额外输出 Lane B 的 immediate-only 分解 rows，只能标 `deployed_baseline_component_readout`，不得叙述为 override。

#### 5.2.1 B0 与 B1 的关系（防止退化为同一臂）

在全 deployed baseline kept 集合内，B0（deployed baseline）与 B1（immediate full entry）使用相同 candidate set、entry timing（t0+1 full）与 exit contract，因此 **B0 与 B1 预期是同一条 ledger**。这是有意的：B0 是 deployed cascade 的对照锚点，B1 保留为 replay registry / timing sanity check，防止后续实现把 B0 偷偷缩成 Lane A 子集。必须在 `policy_arm_registry.csv` 显式落表：

- B0 的 candidate set = Lane A ∪ Lane B（所有 10A admitted + 10B selected kept rows，忽略 10C reference slice）。
- B1 的 candidate set = Lane A ∪ Lane B（与 B0 完全一致）。
- runner 必须输出 `b0_b1_deployed_set_identical_flag = true`；若该 flag 为 false，final status 不得高于 `11C_two_stage_policy_statistics_incomplete`。
- report 必须说明 B1 不提供独立收益结论；所有 policy lift 的主比较锚点是 B0。
- B2/B3 的 top-level comparison candidate set 也必须覆盖 Lane A ∪ Lane B；Lane A 部分是 K3 two-stage policy，Lane B 部分是 B0 carry-through。runner 必须输出 `b2_b3_composite_candidate_set_flag = true`；若 B2/B3 只剩 Lane A 子集却直接对比 B0，final status 不得高于 `11C_two_stage_policy_statistics_incomplete`。
- B0/B1/B2/B3 必须使用同一个 exit contract。不得让 B0 使用一个更宽松或更严格的 exit，从而把 entry-timing 效果和 exit-policy 效果混在一起。

### 5.3 Sizing grid

必须预注册离散 grid：

```text
trial_size in {0.00, 0.10, 0.25}
upgrade_size in {0.50, 1.00}  # target total position size after K3 confirmation, not incremental add size
```

约束：

- `upgrade_size` 定义为 K3 confirmation 后的 **目标总仓位**，不是追加仓位；因此 `final_position_size = upgrade_size`，不得用 `trial_size + upgrade_size` 计算最终仓位。
- `incremental_upgrade_order_size = max(upgrade_size - current_filled_trial_size, 0.00)`；若 trial entry 未成交，`current_filled_trial_size = 0.00`。
- 有效 grid 必须满足 `0.00 <= trial_size <= upgrade_size <= 1.00`。当前预注册组合全部有效，不允许 runner 事后剔除 `0.10 + 1.00` 或 `0.25 + 1.00`。
- `trial_size = 0.00` 的 B3 ledger 等价于同一 `upgrade_size` / target size 下的 B2 wait-confirm ledger；runner 必须输出 `trial_zero_wait_confirm_equivalence_flag = true`。
- 若 `state_negative`，B3 在 t0+4 open 尝试退出 trial；若跌停/停牌无法退出，必须继续持有并记录 `exit_failure_reason`。
- sizing grid selection 只能基于 train split；validation/robustness 不得改变 selected grid。

## 6. K3 observed-state 定义

### 6.1 K3 timing

K3 state 的信息可见时间固定为：

```text
state_observation_window = (t0, t0+3]
state_decision_time = t0+3 close after market close
state_action_time = t0+4 executable open
```

任何 t0+4 open 之后的数据不得参与 K3 state。

### 6.2 Allowed primary features

`observed_state_feature_registry.csv` 必须把每个 feature 标为 `primary_allowed` / `readout_only` / `forbidden`。

Primary allowed feature 必须只来自 `(t0, t0+3]`：

| family | feature_id examples | direction |
| --- | --- | --- |
| return | `ep_ret_t0_to_3`, `ep_close_vs_t0_close_at_3` | higher is better |
| path damage | `ep_max_drawdown_to_3`, `ep_breach_t0_low_through_3_flag` | less damage is better |
| reclaim | `ep_close_above_t0_high_at_3_flag`, `ep_recovery_from_min_to_3` | reclaim is better |
| liquidity | `ep_volume_ratio_3d_vs_20d`, `ep_money_ratio_3d_vs_20d` | higher/liquid is better |
| executable | `entry_t0p4_executable_flag`, `suspended_through_K3_flag`, `limit_up_locked_t0p4_flag` | executable is required |

Liquidity features must be computed from historical volume/money with rolling denominators available no later than t0+3. If rolling denominator is unavailable, the feature status is `feature_insufficient_history` and cannot silently become 0.

### 6.3 State definition registry

11C may use a small predeclared grid of observed-state definitions, but must freeze it in `observed_state_definition_registry.csv`.

Minimum required definitions:

| state_id | formula |
| --- | --- |
| `S0_return_damage_basic` | `ep_ret_t0_to_3 >= 0` AND `ep_max_drawdown_to_3 >= -0.08` AND `entry_t0p4_executable_flag == true` |
| `S1_reclaim_damage` | `ep_close_vs_t0_close_at_3 >= 0` AND `ep_breach_t0_low_through_3_flag == false` AND `entry_t0p4_executable_flag == true` |
| `S2_return_reclaim_liquidity` | `ep_ret_t0_to_3 >= 0` AND `ep_close_above_t0_high_at_3_flag == true` AND `ep_money_ratio_3d_vs_20d >= 1.0` AND `entry_t0p4_executable_flag == true` |

允许额外加入 train-quantile thresholds，但必须满足：

- thresholds 只由 train split 的 K3 observed features 计算。
- quantile grid 必须预注册在 config，例如 `return_quantile in {0.50, 0.60, 0.70}`，`drawdown_floor in {-0.03, -0.05, -0.08}`。
- selected `state_id` 只能由 train split 的 policy utility package 选出。
- selected `state_id` 必须原样应用到 validation / robustness。

### 6.4 State selection gate

state/arm/sizing 选择的 train objective 不是 raw mean return，而是：

```text
train_policy_selection_score =
    net_ev_per_exposure_day_lift_vs_B0
  - failure_exposure_penalty
  - winner_capture_penalty
  - topk_dependency_penalty
  - execution_failure_penalty
```

其中 penalty 必须在 config 中冻结。默认允许的 train selection 候选必须先满足：

- `state_positive_entry_n >= 100` in train。
- `state_positive_winner_n >= 20` in train。
- `net_ev_per_exposure_day_lift_vs_B0 > 0` in train。
- `winner_120_capture_rate >= B0_winner_120_capture_rate - 0.05`。
- `big_failure_proxy_entry_rate <= B0_big_failure_proxy_entry_rate + 0.005`。
- `limit_up_unfilled_rate <= 0.20`。
- `limit_down_exit_failure_rate <= 0.10`。

若没有 candidate 通过 train pre-gate，final status 为 `11C_two_stage_policy_not_supported_diagnostic`。

## 7. Execution replay contract

### 7.1 Price basis

Return 计算使用 qfq price basis：

- entry fill price: qfq open on scheduled executable entry date；
- upgrade fill price: qfq open on scheduled upgrade date；
- exit fill price: qfq open on scheduled exit date，若触发日开盘越过 stop/exit threshold，则按 open 执行，不使用更优 barrier price；
- mark-to-market: qfq close。

所有 gross return、net return、MAE/MFE、drawdown 都必须使用同一 qfq basis。不得混用 raw price 计算收益。

### 7.2 Next-open executable proxy

日频 OHLCV 不能真实观测开盘排队成交，只能做保守 proxy。11C 必须 fail closed：

```text
missing_open_or_volume:
  qfq_open missing OR volume <= 0 OR money <= 0 OR daily bar missing
  -> unfilled_missing_open_or_volume

limit_rule_unavailable:
  board / limit threshold cannot be determined
  -> unfilled_limit_rule_unavailable

limit_up_locked_buy:
  one-price upper-limit locked day on scheduled buy/upgrade open
  -> buy_unfilled_limit_up_locked

limit_down_locked_sell:
  one-price lower-limit locked day on scheduled sell/exit open
  -> sell_unfilled_limit_down_locked, carry position forward
```

One-price locked proxy：

```text
qfq_open == qfq_high == qfq_low == qfq_close
AND abs(raw_or_qfq_open / previous_close - 1) >= board_limit_proxy_used
```

If raw price is unavailable, qfq return may be used only if factor continuity audit passes; otherwise mark `limit_basis_unavailable` and treat scheduled action as unfilled.

Board limit proxy defaults:

| board | limit proxy |
| --- | ---: |
| main_board | 0.095 |
| chinext_star | 0.195 |
| st | not used post-t0; t0 ST already excluded |
| unknown_fallback | 0.095 with `board_unknown` audit |

### 7.3 Entry / upgrade / exit timing

For a candidate with event date t0:

| action | scheduled date |
| --- | --- |
| immediate entry / trial entry | session_after(t0) = t0+1 open |
| K3 state observation | t0+3 close |
| wait-confirm entry | t0+4 open |
| upgrade | t0+4 open |
| state-negative trial exit | t0+4 open |

If t0+4 open is not executable:

- wait-confirm entry remains unfilled and does not chase later unless config `allow_delayed_entry_chase=true`; default must be `false` for primary replay.
- upgrade remains unfilled; existing trial position remains at trial size unless exit rule triggers.
- state-negative trial exit attempts again on next executable open until filled or max holding horizon.

### 7.4 Exit contract

Main replay must use a single exit contract for B0/B1/B2/B3/LB2 so entry timing and sizing are the only intentional differences.

11C requires an explicit `exit_contract_id` in config. Minimum supported exit contract:

```text
exit_contract_id = common_exit_120d_with_risk_stop_v1
max_holding_sessions = 120
risk_stop_drawdown_from_cost_basis = -0.10
time_exit = t0+120 close or first executable open after max horizon
delist_exit = last_tradable_close * (1 - delist_haircut)
delist_haircut = 1.0 primary; 0.0 sensitivity
```

Risk stop rule:

- `risk_stop_anchor_price` is the current position weighted-average cost basis in qfq price units.
- For B0/B1/B2 single-fill entries, `risk_stop_anchor_price = entry_fill_price`.
- For B3, after trial fill only, `risk_stop_anchor_price = trial_fill_price`; after any filled upgrade, recompute immediately at that open as `position_weighted_average_cost = total_filled_cost / total_filled_share` using all filled trial/upgrade lots. If upgrade is unfilled, keep the previous anchor.
- MAE / drawdown / risk-stop threshold for B3 must use this current weighted-average cost basis, not an arbitrary first-fill or last-fill price.
- If daily low after a position exists touches `risk_stop_anchor_price * (1 - 0.10)`, schedule exit at next executable open.
- If next executable open is lower than stop threshold, fill at open.
- If exit open is lower-limit locked or missing, carry position and record `limit_down_exit_failure`.

If an upstream current exit artifact exists in future, 11C may add `E0_upstream_existing_exit` as sensitivity, but current final status must not depend on an undocumented exit artifact. If the implementation chooses to make upstream existing exit the primary exit, its path, schema, hash, and row-level join coverage must be frozen in the config and manifest; otherwise final status is `11C_two_stage_policy_input_blocked`.

### 7.5 Transaction cost

Main replay must report three cost scenarios:

| cost_scenario | buy_cost_bps | sell_cost_bps | role |
| --- | ---: | ---: | --- |
| `zero_cost_decomposition` | 0 | 0 | decomposition only |
| `base_cost` | 8 | 13 | primary final decision |
| `stress_cost` | 15 | 25 | sensitivity |

Costs apply per filled notional. Trial entry + upgrade + exit are three separate filled actions if all occur. Unfilled orders incur no cost but must enter unfilled audit.

Final status must use `base_cost`. A policy that works only under zero cost is `11C_two_stage_policy_gross_only_not_tradable`.

### 7.6 Portfolio capital model

11C must produce both event-level and portfolio-constrained readouts. Final status uses portfolio-constrained readout.

Primary portfolio assumptions:

```text
initial_capital = 1.0
max_gross_exposure = 1.0
primary_capacity_slots = 50
per_position_full_size_notional = 1.0 / primary_capacity_slots
max_instrument_weight = 0.05
max_board_weight = 0.40
max_industry_weight = 0.25 if industry is available; otherwise report industry_unavailable
order_priority = event_action_date, split order train/validation/robustness preserved only for reporting, instrument, policy_row_id
```

Capacity sensitivity must also report `capacity_slots in {20, 50, 100}`.

If cash is insufficient at an entry/upgrade action, the order is unfilled with `unfilled_cash_constraint`. Cash drag is:

```text
cash_drag_day = 1 - gross_exposure_day
cash_drag_mean = mean(cash_drag_day over replay calendar)
```

## 8. 主指标包

11C 不得只看 `forward_return mean`。每个 arm/lane/split/cost_scenario/capacity_slots 必须输出：

1. `net_median_return`
2. `net_winsorized_mean_return_1_99`
3. `net_ev_per_exposure_day`
4. `winner_120_retention_rate`
5. `winner_120_capture_rate`
6. `big_failure_proxy_entry_rate`
7. `false_repair_entry_rate`
8. `fast_fail_realized_loss_rate`
9. `mae_p50`, `mae_p95`, `max_drawdown_p95`
10. `turnover_notional`
11. `transaction_cost_bps_paid`
12. `capital_utilization_mean`
13. `cash_drag_mean`
14. `max_concurrent_positions`
15. `board_concentration_hhi`
16. `industry_concentration_hhi`
17. `limit_up_unfilled_rate`
18. `limit_down_exit_failure_rate`
19. `topk_removal_net_ev_per_exposure_day_lift`
20. `instrument_block_bootstrap_ci_low/high`

Metric denominators must be explicit:

- `entry_rate` denominator is evaluated rows in that lane/split, not filled trades.
- `winner_capture_rate` denominator is all winner rows in that lane/split.
- `winner_retention_rate` denominator is B0 captured winners in the same lane/split.
- `net_ev_per_exposure_day` denominator is filled position exposure-days after portfolio constraints.
- `fast_fail_realized_loss_rate` denominator is filled entries with fast-fail label evaluable.
- `limit_up_unfilled_rate` denominator is scheduled buy/upgrade orders.
- `limit_down_exit_failure_rate` denominator is scheduled sell/exit orders.

## 9. Robustness package

### 9.1 Top-k sensitivity

Must report top-k removal by instrument and episode:

```text
top_k in {1, 3, 5, 10}
ranking_metric = contribution_to_net_pnl
removal_scope = train-selected policy applied unchanged to each split
```

Final positive status requires:

- net EV per exposure-day lift remains positive after top-5 instrument removal in train and robustness;
- top-1 instrument contribution share <= 35%;
- top-5 instrument contribution share <= 60%;
- no single episode family contributes more than 35% of net PnL lift.

### 9.2 Instrument-block bootstrap

Must run deterministic instrument-block bootstrap:

```text
bootstrap_n = 1000
block_key = instrument
seed = config.bootstrap_seed
metric = net_ev_per_exposure_day_lift_vs_B0 under base_cost and primary_capacity_slots
```

Final positive status requires:

- train bootstrap CI low > 0;
- robustness bootstrap CI low > 0;
- validation is confirmatory only when it passes power guard: `validation_winner_n >= validation_min_winner_n` and `validation_state_positive_winner_n >= validation_min_state_positive_winner_n` under the selected policy. Default thresholds must be config-frozen as `validation_min_winner_n = 30` and `validation_min_state_positive_winner_n = 10`.
- if validation fails this power guard, set `validation_low_power = true`; validation bootstrap CI is readout-only and cannot block a positive train+robustness conclusion.
- if validation passes power guard and validation bootstrap CI high < 0, final status cannot be positive.

### 9.3 Failure exposure gate

Relative to B0 current baseline, selected policy must satisfy under base_cost and primary capacity:

```text
big_failure_proxy_entry_rate_lift <= 0.005
false_repair_entry_rate_lift <= 0.005
fast_fail_realized_loss_rate_lift <= 0.005
mae_p95_lift <= 0.02
```

If net EV improves but failure exposure worsens beyond these tolerances, final status must be `11C_two_stage_policy_failure_exposure_worse`.

### 9.4 Right-tail capture gate

Selected policy must not destroy right-tail capture:

```text
winner_120_capture_rate >= B0_winner_120_capture_rate - 0.05
winner_120_retention_rate >= 0.85
```

If the policy improves median/EV by avoiding too many winners, final status must be `11C_two_stage_policy_right_tail_capture_collapsed`.

### 9.5 Execution and capacity gate

Final positive status requires:

```text
limit_up_unfilled_rate <= 0.20
limit_down_exit_failure_rate <= 0.10
cash_drag_mean <= B0_cash_drag_mean + 0.10
max_concurrent_positions <= primary_capacity_slots
board_concentration_hhi <= B0_board_concentration_hhi + 0.10
```

If EV lift disappears under `capacity_slots=20`, report `capacity_sensitive`; this does not automatically block final positive status, but report must state capacity risk before conclusion.

## 10. Lane B rescue readout power rule

Lane B delayed rescue (`LB2_delayed_rescue_K3`) is a diagnostic readout, not a top-level policy arm. It may be marked `lane_b_rescue_power_supported_for_future_research` only if all conditions hold after applying selected K3 state:

```text
lane_B_state_positive_entry_n >= 100 in train
lane_B_state_positive_winner_n >= 20 in train
lane_B_state_positive_entry_n >= 50 in robustness
lane_B_state_positive_winner_n >= 10 in robustness
```

If any condition fails:

- Lane B rescue substatus must be `lane_b_rescue_readout_only_low_power`;
- LB2 metrics may be shown;
- no final status may say rescue is supported;
- report must explicitly say 10C reference-slice rejected rescue is not authorized.

If Lane B is effective only in train and not robustness, Lane B rescue substatus is `lane_b_rescue_not_supported_oos`.

`lane_b_rescue_status` is a separate field in `final_policy_decision.csv` and must never be the top-level `final_status`. If LB2 is promising, top-level `final_status` still depends on the B0/B2/B3 composite policy package; Lane B can only appear as `lane_b_rescue_status` and as a future-research note. Lane B low power or OOS failure must remain a side readout and must not block `11C_two_stage_policy_supported`, `11C_two_stage_policy_observation_first_preferred`, or `11C_two_stage_policy_staged_sizing_candidate`.

## 11. Final status state machine

Exactly one final status must be emitted:

| final_status | Meaning |
| --- | --- |
| `11C_two_stage_policy_supported` | Selected two-stage policy beats B0 under base_cost, primary capacity, robustness gates, top-k sensitivity, failure exposure, right-tail capture, and execution gates |
| `11C_two_stage_policy_gross_only_not_tradable` | Gross or zero-cost readout works, but base/stress cost or execution constraints remove edge |
| `11C_two_stage_policy_topk_dependent` | EV lift depends on top-k instruments / episodes |
| `11C_two_stage_policy_failure_exposure_worse` | EV improves but big_failure / false_repair / fast_fail / MAE exposure worsens beyond tolerance |
| `11C_two_stage_policy_right_tail_capture_collapsed` | EV improves by sacrificing too much winner capture |
| `11C_two_stage_policy_observation_first_preferred` | B2 wait-confirm dominates B3 trial-entry after cost and robustness |
| `11C_two_stage_policy_staged_sizing_candidate` | B3 trial-entry dominates B2 and passes all gates; only authorizes further staged-sizing research |
| `11C_two_stage_policy_not_supported_diagnostic` | Inputs readable, but no policy passes pre-registered gates |
| `11C_two_stage_policy_statistics_incomplete` | Non-blocking but conclusion-critical metrics incomplete, hash mismatch, or denominator drift |
| `11C_two_stage_policy_input_blocked` | Required inputs missing, baseline not reconstructable, leakage detected, or execution replay impossible |

Precedence:

```text
input_blocked
  > statistics_incomplete
  > gross_only_not_tradable
  > topk_dependent
  > failure_exposure_worse
  > right_tail_capture_collapsed
  > supported / observation_first_preferred / staged_sizing_candidate
  > not_supported_diagnostic
```

If B2 wait-confirm clearly beats B3 trial-entry, report conclusion must be:

```text
系统改成 observation-first，而不是 small trial entry。
```

If B3 trial-entry clearly beats B2, report conclusion must be:

```text
继续研究 staged sizing，但仍要单独看成本、容量、涨跌停。
```

## 12. 预注册失败模式

11C 必须在 report 中逐条判定以下 cases：

| case | condition | required conclusion |
| --- | --- | --- |
| Case 1 | K3 wait-confirm gross 有效，但 net after cost 无效 | trajectory separability 存在，但不可交易 |
| Case 2 | trial-entry 优于 wait-confirm 只来自少数 top-k instrument | 不支持 policy，回到 diagnostic |
| Case 3 | K3 state-positive 提高 winner capture，但 big_failure / false_repair 同步上升 | 复现 11A1 纠缠，只是延迟到 K3，不支持 |
| Case 4 | 只在 Lane A（10C reference-slice kept）有效，Lane B（reference-slice rejected）无效 | 只允许 upgrade/hold，不允许 rescue / override |
| Case 5 | 只在 Lane B（10C reference-slice rejected）有效，但 power 不足 | 只允许 readout，不授权交易 |
| Case 6 | wait-confirm 明显优于 trial-entry | observation-first 优先 |
| Case 7 | trial-entry 明显优于 wait-confirm | staged sizing candidate，但还需成本/容量/涨跌停复核 |

## 13. Required outputs

### 13.1 publishable tables

Output directory:

```text
outputs/publishable/tables/11C_two_stage_observed_state_policy_replay_v0/
```

Required tables:

- `input_artifact_audit.csv`
- `scope_reconciliation_vs_11a1_11a2.csv`
- `k3_row_id_rehydration_audit.csv`
- `lane_population_audit.csv`
- `policy_arm_registry.csv`
- `observed_state_feature_registry.csv`
- `observed_state_definition_registry.csv`
- `state_selection_readout.csv`
- `execution_fill_audit.csv`
- `limit_execution_audit.csv`
- `policy_performance_summary.csv`
- `robust_metric_package.csv`
- `winner_capture_readout.csv`
- `failure_exposure_readout.csv`
- `mae_drawdown_distribution.csv`
- `turnover_cost_readout.csv`
- `capital_utilization_readout.csv`
- `concentration_readout.csv`
- `topk_removal_sensitivity.csv`
- `instrument_block_bootstrap_ci.csv`
- `lane_b_rescue_power_readout.csv`
- `label_overlap_policy_audit.csv`
- `failure_mode_decision_table.csv`
- `final_policy_decision.csv`

### 13.2 local cache

Output directory:

```text
outputs/local_cache/11C_two_stage_observed_state_policy_replay_v0/
```

Allowed cache files:

- `policy_replay_base_denominator.parquet`
- `k3_observed_state_matrix.parquet`
- `event_level_trade_ledger.parquet`
- `portfolio_daily_ledger.parquet`
- `bootstrap_samples.parquet`

manifest must record path, sha256, row_count, and schema for every cache.

### 13.3 report and manifest

Required:

- `outputs/publishable/reports/11C_two_stage_observed_state_policy_replay_v0_report.md`
- `outputs/publishable/manifest_11C_two_stage_observed_state_policy_replay_v0.json`

Report must be Chinese and include:

1. Scope reconciliation against 11A1/11A2/11B, including why 6,628 PIT-excluded rows remain out-of-scope.
2. 11A2 prerequisite check: K*=3, tradable window open, and diagnostic-only boundary.
3. 11B prerequisite check: protected retention final_status, non-discrimination metric summary, and whether retention is non_discriminatory / discriminatory / readout-only.
4. Lane A / Lane B population counts、deployed baseline（10A + 10B selected）provenance、以及 10C `tenc_slice_mode`（当前预期 `keep_9000_reference_slice`，非已部署 gate）。
5. K3 observed-state registry, selected state definition, and leakage/label-overlap audit.
6. B0/B1/B2/B3/LB0/LB2 replay result under zero/base/stress cost.
7. Event-level and portfolio-constrained readouts, with final status using portfolio-constrained base-cost result.
8. Winner capture, failure exposure, MAE/drawdown, turnover, cost, capital utilization, cash drag, max concurrent positions.
9. Limit-up unfilled and limit-down exit failure rates.
10. Board/sector concentration.
11. Top-k removal and instrument-block bootstrap.
12. Lane B power and whether rescue remains readout-only.
13. Seven pre-registered failure modes.
14. Final status and exact reason list.

## 14. Validation requirements

### 14.1 Unit tests

`tests/test_two_stage_observed_state_policy_replay.py` must cover:

- 11A1/11A2 denominator reconciliation, including expected `4665` row count and fail-closed behavior on drift.
- 11A2 prerequisite status: only `separation_detected_tradable` with K*=3 allows policy replay.
- 11B upstream contract：manifest/report tables are readable and hashable; `retention_summary.csv` has exactly one final_status; 11B `statistics_incomplete` / `input_blocked` ceilings 11C to `statistics_incomplete`; 11B `discriminatory` forces report to carry winner-retention loss as diagnostic cost; 11B ambiguous/underpowered/mixed-power remains readout-only.
- PIT-excluded rows never enter policy metrics.
- 10B deployed selected gate 从 10B manifest authoritative `selected_*` fields 与 `selected_operating_point.ablation_id` 读取（非硬编码，且不得使用 10C manifest 的 `actual_10b_selected_*` 作为 source）；deployed baseline 不可重建时 input_blocked。
- 10C 无 selected gate（`selected_capacity_id == null` / `selected_cascade_status == blocked`）时，`tenc_slice_mode == keep_9000_reference_slice`，且该状态**不**触发 input_blocked；仅当 deployed baseline 不可重建或 10C `keep_9000` slice 在 scores cache 上 0 行时才 input_blocked。
- Lane A/B 由 deployed_baseline_kept_flag 与 10C reference-slice rejected flag 联合构造；被 10B reject 的样本不进 Lane A/B。
- B0 与 B1 必须覆盖同一 deployed baseline candidate set（Lane A ∪ Lane B），输出 `b0_b1_deployed_set_identical_flag = true`；10C reference-slice rejected rows 不得从 B0/B1 中丢失。
- B2/B3 top-level comparison 必须是 composite ledger：Lane A 应用 K3 policy，Lane B carry B0 exposure；输出 `b2_b3_composite_candidate_set_flag = true`，不得只用 Lane A 子集直接对比 B0。
- B0/B1/B2/B3/LB0/LB2 arm registry completeness.
- 若使用 11A2 `early_path_feature_matrix.parquet`，必须过滤 `K == 3` 且 `cohort == full_cohort`，并通过 `k3_row_id_rehydration_audit.csv` 证明 `row_id` 到 `policy_row_id` 一一对应；否则必须重建 K3 feature matrix。
- K3 state observation uses only `(t0, t0+3]`; action happens no earlier than t0+4 open.
- Forbidden features (`selected_fast_fail_*`, `winner_120`, future MFE/MAE, `forward_return_120d`) cannot enter primary state registry.
- State thresholds are train-only and applied unchanged to validation/robustness.
- `upgrade_size` is target total position size, not incremental add size; `final_position_size = upgrade_size`; `incremental_upgrade_order_size = max(upgrade_size - current_filled_trial_size, 0)`; all predeclared grid combinations are valid; `trial_size=0` B3 ledger equals B2 wait-confirm under the same `upgrade_size` and sets `trial_zero_wait_confirm_equivalence_flag = true`.
- B3 risk stop, MAE, and drawdown use current position weighted-average cost basis; after any filled upgrade, `risk_stop_anchor_price` is recomputed from filled trial/upgrade lots.
- Validation bootstrap has a power guard: when `validation_low_power = true`, validation CI is readout-only and cannot block positive train+robustness; only powered validation with CI high < 0 can block positive status.
- Limit-up locked buy is unfilled; limit-down locked exit carries forward and records failure.
- Missing open/volume/money fails closed.
- Post-t0 ST does not trigger fill, exit, exclusion, or ceiling.
- Transaction costs apply per filled action.
- Portfolio cash constraints create `unfilled_cash_constraint` and cash drag.
- Net EV per exposure-day denominator is filled exposure-days.
- Winner capture and entry-rate denominators are pre-filled lane denominators.
- Top-k removal uses contribution ranking and does not reselect policy.
- Instrument-block bootstrap resamples instruments, not rows.
- Lane B low-power / OOS state only sets `lane_b_rescue_status`; it must never become top-level `final_status` and must not globally block Lane A / whole-deployed-baseline policy conclusion.
- Final status precedence.
- Report forbidden phrases are absent.

### 14.2 Run validation

Implementation must at least run:

```bash
python -m py_compile experiments/pending/11_archetype_proxy_validation_system_v0/src/run_11c_two_stage_observed_state_policy_replay.py
python -m pytest experiments/pending/11_archetype_proxy_validation_system_v0/tests/test_two_stage_observed_state_policy_replay.py -q
python experiments/pending/11_archetype_proxy_validation_system_v0/src/run_11c_two_stage_observed_state_policy_replay.py --config experiments/pending/11_archetype_proxy_validation_system_v0/configs/config_11c_two_stage_observed_state_policy_replay.yaml
```

若从 `topics/02_AFML_BIG_WINNER` topic root 运行，则相对路径可省略 topic prefix；report 必须记录实际命令。

### 14.3 Artifact validation

- All publishable CSVs must be non-empty unless final status is `input_blocked`.
- Manifest sha256 must be reproducible for report, tables, config, and local caches.
- `final_policy_decision.csv` must contain exactly one final_status.
- Report values must be traceable to CSV rows.
- No `__pycache__` or temporary debug output may be staged for publish.

## 15. 报告措辞约束

Report must not say:

- “11A2 证明策略有效”
- “K3 state 可以 override 10C”
- “10C reference-slice rejected 可以直接放宽”
- “MFE 收益”
- “production-ready strategy”
- “收益最高所以支持”

Allowed phrasing:

- “two-stage observed-state replay”
- “after-cost / capacity-constrained readout”
- “Lane B delayed-confirmation rescue readout”
- “observation-first preferred”
- “staged sizing candidate”
- “trajectory separability exists but is not tradable after costs”

## 16. 后续依赖

If final status is positive:

- `observation_first_preferred` can feed a future 11D execution/backtest design using B2-style delayed entry.
- `staged_sizing_candidate` can feed a future 11D staged-sizing design, but only after cost/capacity/limit-up/limit-down risk is revalidated.
- Lane B can feed a future rescue-research requirement only if Lane B power and OOS gates pass; this remains a diagnostic follow-up note, not a current 11C policy authorization.

If final status is non-positive:

- no 10C override;
- no delayed rescue authorization;
- return to diagnostic or single-layer rejector improvement;
- do not weaken t0 rejectors using 11A2 separation alone.

Most important boundary:

> 11A2 showed K=3 path divergence can appear before most winner upside is realized. 11C must decide whether that divergence survives execution, cost, sizing, and capacity. If it does not, the correct conclusion is not "no separation"; it is "separation exists but is not yet tradable under this policy contract."

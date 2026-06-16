# 需求：11A1 Archetype Proxy Robust Payoff-Risk Audit

## 0. 本需求要回答的问题

`10_riskon_layered_rejector_system_v0` 已经完成了 winner-first archetype profiling、10A 密度规则、10C false-repair rejector 与 10D safe-false-repair 修复方向的前置研究。当前讨论给出的下一步不是直接设计买入策略，而是先判断：

> 能否用 **t0 可见、可预注册、可全分母打分** 的 proxy，把 winner archetype 从事后描述转化为一个稳健的 payoff-risk screen？

11A1 只做诊断和审计，不授权交易、不放宽 rejector、不改变 10A/10B/10C 的既有产物。

本轮 11A1 的验证范围固定为 `analysis_regime_bucket == risk_on`。原因是 10 号实验已经显示 big winner 在 `risk_on` / `risk_off` / `transition` 下的分布不同，直接跨 regime 合并会把 regime composition 差异混入 proxy payoff-risk 判断。本轮先只回答 `risk_on` 内 proxy 是否稳健；`risk_off` 与 `transition` 不在本轮 supported/empty 判定范围内。

## 1. 实验名称与状态

- experiment_id: `11_archetype_proxy_validation_system_v0`
- primary_run_id: `11A1_archetype_proxy_robust_payoff_risk_audit`
- parent_experiment_id: `10_riskon_layered_rejector_system_v0`
- status: `implemented_and_run`
- expected_entrypoint: `src/run_11a1_archetype_proxy_robust_payoff_risk_audit.py`
- expected_config: `configs/config_11a1_archetype_proxy_robust_payoff_risk_audit.yaml`
- expected_test_file: `tests/test_archetype_proxy_robust_payoff_risk_audit.py`

## 2. 核心原则

### 2.1 proxy 的角色

proxy 不是买入信号，也不是 winner 标签的替代品。它的作用是：

1. 把 winner archetype 从事后路径描述转化为 t0 可见的候选筛选维度。
2. 在完整候选分母上检查该维度是否同时改善右尾捕获与风险暴露。
3. 为后续 11B/11C 提供是否值得进入策略建模的证据。

### 2.2 archetype 与 proxy 的边界

- archetype: 来源于 winner-first profiling，可包含事后路径信息，用于提出假设。
- proxy: 必须在 t0 或 t0 之前可见，可在 full denominator 上打分，用于统计检验。
- retrospective path metric: 只能用于解释 archetype，不能进入 11A1 的 supported proxy registry。

### 2.3 11A1 不做的事

11A1 明确不做以下事项：

- 不输出交易策略、仓位、组合收益、手续费后策略 EV。
- 不把 MFE 当成可实现收益；MFE 只作为上界型路径读数。
- 不用 `winner_120`、`mfe_*`、`mae_*`、`forward_return_*` 或未来路径构造 proxy。
- 不根据 outcome 结果反向挑选 proxy 或阈值。
- 不修改 10A/10B/10C/10D 的输入、输出或既有结论。
- 不用 11A1 结果直接降低 10C rejector 的保留底线。
- 不比较或解释 `risk_off`、`transition` 下的 proxy 支持性；这些 regime 只能作为 out-of-scope row count 审计。

### 2.4 本轮 regime scope

11A1 是 `risk_on-only` proxy audit：

- primary evaluated denominator 必须满足 §3.2 的 10A R-core 条件，且 §3.5 的 `analysis_regime_bucket == risk_on`。
- 在 `analysis_regime_bucket == risk_on` 之后，必须先对 PIT executable universe 做 strict inner join，只保留 PIT 命中且 t0 可执行状态有效的行进入最终 evaluated denominator。
- `risk_off`、`transition`、`regime_missing_after_backfill` 行不得进入 proxy threshold fitting、proxy membership evaluation、matched base、bootstrap、top-k sensitivity、multiple-comparison simulation、rejected-subpopulation override supported readout 或 final supported/empty 判定。
- runner 必须输出被排除的非 `risk_on` / missing row count，用于确认 scope，而不是把这些 row 当作负面证据。
- 本轮报告不得把 `risk_on` 结论外推到 `risk_off` 或 `transition`。

## 3. 上游输入

### 3.1 讨论与需求输入

以下文件作为需求与解释来源，不作为可变数据输入：

- `../10_riskon_layered_rejector_system_v0/next_step_discussion.md`
- `../10_riskon_layered_rejector_system_v0/requirement_big_winner_archetype_profiling.md`
- `../10_riskon_layered_rejector_system_v0/outputs/publishable/reports/big_winner_archetype_profiling_report.md`

runner 必须在 `input_artifact_audit.csv` 中记录这些文件的 path、sha256、mtime。

### 3.2 10A 分母与事件绑定

必需输入：

- `../10_riskon_layered_rejector_system_v0/outputs/manifests/10A_density_rule_system_manifest.json`
- `../10_riskon_layered_rejector_system_v0/outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet`
- `../10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10A_density_rule_system/post_dedup_population_contract.csv`
- `../10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10A_density_rule_system/post_dedup_false_repair_power_audit.csv`
- `../10_riskon_layered_rejector_system_v0/outputs/publishable/tables/10A_density_rule_system/power_audit_config.csv`

必须使用的主分母为 10A admitted post-dedup R-core：

| 字段 | 固定取值 |
| --- | --- |
| `population_id` | `10A__same_instrument_cooldown_10d` |
| `rule_arm_id` | `same_instrument_cooldown_10d` |
| `input_denominator_id` | `risk_on_r_core_horizon_complete` |
| `denominator_id` | `post_dedup_risk_on_r_core` |
| `admission_status` | `admitted` |
| `readout_only_flag` | `false` |

该分母是 11A1 的完整候选分母，必须保留 winner 与 non-winner、后续被 10C reject 与未被 reject 的样本。不得只在 winner episode 上评估 proxy。

在完成 §3.5 的 `analysis_regime_bucket` 回填后，evaluated denominator 必须进一步限制为：

```text
analysis_regime_bucket == risk_on
```

该过滤是本轮实验 scope，不是 outcome-driven sample selection。被排除的 `risk_off`、`transition`、missing/invalid regime 行必须保留在 `risk_on_scope_filter_audit.csv` 中计数，但不得进入任何 proxy 支持性判定。

随后必须在 11A1 evaluated denominator 形成之前执行 strict PIT universe filter：

```text
10A_risk_on_row.instrument + 10A_risk_on_row.event_t0_date
  INNER JOIN pit_largecap_main_chinext_executable_daily.instrument + membership_date
WHERE is_listed = true
  AND is_st = false
  AND is_suspended = false
```

只有该过滤后的 `risk_on ∩ PIT-valid` 行允许进入 09B weights、proxy threshold fitting、proxy membership、matched base、bootstrap、top-k、multiple-comparison 与 final accepted/empty 判定。PIT 未命中或状态不可执行的行必须进入 `pit_universe_scope_filter_audit.csv` 与 `pit_universe_exclusion_diagnostic.csv`，不得作为 11A1 proxy payoff-risk 分母。

### 3.3 09B t0 feature foundation

必需输入：

- `../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09B_feature_foundation_ablation_manifest.json`
- `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09B_feature_foundation/feature_contract.csv`
- `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09B_feature_foundation/feature_transform_contract.json`
- `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09B_feature_foundation/feature_stationarity_audit.csv`
- `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/feature_matrix.parquet`
- `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet`

11A1 supported proxy 只能使用 `feature_contract.csv` 中同时满足以下条件的字段：

- `allowed_for_09C_flag == true`
- `t0_visible_flag == true`
- 字段存在于 `feature_matrix.parquet`

### 3.4 08 label 与 forward path readout

必需输入：

- `../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet`
- `../08_risk_on_transition_recall_exploration_v0/outputs/manifests/run_manifest.json`

使用范围：

- label reconciliation
- `forward_return_20d`
- `forward_return_60d`
- `forward_return_120d`
- `confirm_20_touch_pos`
- `mfe_20d`
- `mfe_60d`
- `mfe_120d`
- `mae_20d`
- `mae_60d`
- `mae_120d`
- horizon complete flags

这些字段全部属于 outcome/readout，不允许进入 proxy 计算。

### 3.5 09A label frontier、regime source 与 hard-failure reconciliation

必需输入：

- `../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09A_fast_fail_label_frontier_manifest.json`
- `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet`
- `topics/02_AFML_BIG_WINNER/configs/labels.yaml`

用途：

- 提供 `episode_regime_bucket` 与 `event_regime_bucket` 的 PIT regime source。
- 对账 10A frozen labels 与 09A label frontier labels。
- 冻结 `labels.label_families.winner_120.hard_failure_first_blocks_winner`。
- 输出 hard-failure-first conditioning 对 winner 分母的影响。

regime scope 必须使用：

```text
analysis_regime_bucket =
  coalesce_non_empty(
    09A.episode_regime_bucket,
    10A.event_regime_bucket,
    09A.event_regime_bucket
  )
```

允许值仅为：

- `risk_on`
- `risk_off`
- `transition`

若以上三层均缺失或不在允许值内，必须输出 `regime_missing_after_backfill`；残余缺失率大于 0 时，最终状态不得高于 `11A1_archetype_proxy_robust_payoff_risk_statistics_incomplete`。不得把 missing 当成独立 regime 解释。

本轮只保留 `analysis_regime_bucket == risk_on` 进入 evaluated denominator。`risk_off` 和 `transition` 只输出 out-of-scope count；不得在本轮报告中比较不同 regime 的 payoff-risk 或 big winner 分布，也不得把非 `risk_on` 结果纳入 `proxy_supported` / `screen_empty` 判定。

### 3.6 10C rejector score 与 rejected subpopulation readout

必需输入：

- `../10_riskon_layered_rejector_system_v0/outputs/manifests/10C_false_repair_rejector_manifest.json`
- `../10_riskon_layered_rejector_system_v0/outputs/local_cache/10C_false_repair_rejector/post_dedup_false_repair_scores.parquet`

主读数使用 10C 的 frozen reference slice：

| 字段 | 固定取值 |
| --- | --- |
| `model_id` | `regularized_logistic_false_repair_20d_l2_v1` |
| `ablation_id` | `full` |
| `capacity_id` | `keep_9000` |
| `threshold_id` | `keep_9000` |
| `population_id` | `10A__same_instrument_cooldown_10d` |
| `denominator_id` | `post_dedup_risk_on_r_core` |

10C score 和 reject flag 只能用于 rejected-subpopulation override readout，不允许作为 11A1 proxy 特征。

### 3.7 价格、PIT universe 与状态数据

runner 必须读取以下明确数据源，用于 denominator completeness、ST/delist 与价格路径审计：

- PIT executable universe: `topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv`
- qfq primary dir: `topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq`
- qfq fallback dir: `topics/02_AFML_BIG_WINNER/data/interim/qlib_csv/day`
- board metadata: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/instrument_metadata_target_universe.csv`
- SH name history dir: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/sh_name_history`
- SZ name history: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/stock_info_sz_change_name_short.csv`

qfq daily bar 至少包含：`instrument`, `date`, `open`, `high`, `low`, `close`, `volume`, `money`, `turnover_rate`。

PIT universe/status 至少能判断样本 t0 是否属于 PIT universe，以及是否存在 ST/delist/停牌造成的不可评价状态。

11A1 strict 版本必须把 PIT universe 从“完整性审计”提升为“evaluated denominator 前置过滤”：

- join key 固定为 `instrument + event_t0_date = instrument + membership_date`。
- `pit_valid` 定义为 PIT membership 命中，且 `is_listed == true`、`is_st == false`、`is_suspended == false`。
- PIT 未命中、非上市、ST、停牌行必须从最终 evaluated denominator 中排除，并在审计表中记录排除原因。
- 若 PIT source 不存在或 PIT-valid evaluated denominator 为空，最终状态必须为 `11A1_archetype_proxy_robust_payoff_risk_input_blocked`。

如果过滤后的 evaluated denominator 仍无法识别 delisted/ST/left-tail 状态，11A1 不得静默通过，必须在 `denominator_completeness_st_delist_audit.csv` 中给出 `left_tail_status_audit_incomplete`，最终状态不得高于 `11A1_archetype_proxy_robust_payoff_risk_statistics_incomplete`。

## 4. 主分母与 join contract

### 4.1 join key 与 canonical id policy

10A `post_dedup_event_bindings.parquet` 已提供用途明确的物化 join key，runner 必须优先使用这些字段，不得把 `split(input_event_key, "|")[3]` 作为主 join 逻辑：

| 10A 字段 | 用途 |
| --- | --- |
| `feature_matrix_join_key` | 10A -> 09B feature matrix |
| `cost_bad_sample_weight_join_key` | 10A -> 09B cost_bad sample weights |
| `fast_fail_sample_weight_join_key` | 10A -> 09B fast_fail sample weights |
| `input_event_key` | 10A -> 10C score 与 cross-check |

`binding_canonical_event_id` 的来源优先级：

1. 若 10A 未来版本已提供 `binding_canonical_event_id`，直接使用。
2. 否则使用 10A primary denominator 与 10C frozen reference slice 按 `input_event_key`, `sample_id`, `selected_target_id`, `instrument`, `event_t0_date` join 后取得 `10C.binding_canonical_event_id`。
3. 若 10C 对个别 row 缺失，允许从 `feature_matrix_join_key` 的第 4 段解析作为 fallback，并标记 `canonical_id_fallback_to_join_key_parse`。

`input_event_key` / `feature_matrix_join_key` 的 pipe split 只能用于 cross-check 与 fallback 审计。必须输出：

- `canonical_id_source`
- `canonical_id_10c_join_success_rate`
- `canonical_id_parse_crosscheck_mismatch_n`
- `canonical_id_fallback_to_join_key_parse_n`
- `input_event_key_parse_success_rate`
- malformed key examples, 最多输出 20 行

若 `canonical_id_fallback_to_join_key_parse_n / primary_denominator_row_n > 0.005`，最终状态不得高于 `11A1_archetype_proxy_robust_payoff_risk_statistics_incomplete`。

### 4.2 10A 到 09B feature matrix

左表：10A primary denominator。
右表：09B `feature_matrix.parquet`。

join keys：

| 10A 字段 | 09B 派生字段 |
| --- | --- |
| `feature_matrix_join_key` | `sample_id + "|" + selected_target_id + "|" + denominator_id + "|" + canonical_event_id` |

join 后必须校验：

- `10A.split == 09B.event_split`
- `10A.instrument == 09B.instrument`
- `10A.event_t0_date == 09B.event_t0_date`
- composite key join 与 `sample_id` / `selected_target_id` / `input_denominator_id` / `binding_canonical_event_id` 分列 join 结果一致

任何校验失败都必须进入 `label_join_reconciliation_audit.csv` 和 `denominator_contract_audit.csv`。

### 4.3 10A 到 08 label path

左表：10A primary denominator。
右表：08 `candidate_family_event_labels.parquet`。

join keys：

| 10A 字段 | 08 字段 |
| --- | --- |
| `binding_canonical_event_id` | `event_id` |

join 后必须校验：

- `instrument`
- `event_t0_date`
- `split` 或 `event_split`

主 outcome 只使用 horizon complete 的样本：

- 20d risk readout 要求 `horizon_complete_20d == true`
- 60d payoff readout 要求 `horizon_complete_60d == true`
- 120d right-tail readout 要求 `horizon_complete_120d == true`

缺 horizon 的样本不得丢弃出分母，必须保留并在每个 readout 的 eligible denominator 中单独计数。

### 4.4 10A 到 09A label frontier / regime source

左表：10A primary denominator。
右表：09A `selected_label_event_bindings.parquet`。

join keys：

| 10A 字段 | 09A 字段 |
| --- | --- |
| `sample_id` | `sample_id` |
| `selected_target_id` | `selected_target_id` |
| `input_denominator_id` | `denominator_id` |
| `binding_canonical_event_id` | `canonical_event_id` |

join 后必须校验：

- `10A.split == 09A.event_split`
- `10A.instrument == 09A.instrument`
- `10A.event_t0_date == 09A.event_t0_date`

09A 是 label-frontier selection，不保证覆盖每一个 10A post-dedup admitted row。`10A -> 09A` join 成功率低于 99.5% 时不得直接 `input_blocked`；runner 必须继续使用 `10A.event_regime_bucket` 和 08 labels 完成主 readout，但最终状态不得高于 `11A1_archetype_proxy_robust_payoff_risk_statistics_incomplete`，并在 `regime_source_reconciliation_audit.csv` 与 `hard_failure_conditioning_reconciliation.csv` 中记录 `09a_join_partial_coverage`。

使用字段：

- `episode_regime_bucket`
- `event_regime_bucket`
- `horizon_complete_10d`
- `horizon_complete_20d`
- `horizon_complete_120d`
- `candidate_outcome_120d_status`
- `selected_fast_fail_10_label`
- `selected_fast_fail_touch_pos`
- `selected_fast_fail_barrier_id`
- `frozen_false_repair_20d_label`
- `event_big_winner_120d_label`
- `winner_censoring_status`
- `censoring_status`

必须输出 `regime_source_reconciliation_audit.csv`：

- `split`
- `analysis_regime_bucket`
- `risk_on_scope_flag`
- `episode_regime_bucket_n`
- `event_regime_backfill_n`
- `residual_missing_n`
- `residual_missing_rate`
- `invalid_regime_n`
- `regime_source_status`

必须输出 `risk_on_scope_filter_audit.csv`：

- `split`
- `pre_scope_primary_denominator_row_n`
- `risk_on_evaluated_row_n`，表示 strict PIT 前的 `analysis_regime_bucket == risk_on` row count
- `risk_off_out_of_scope_row_n`
- `transition_out_of_scope_row_n`
- `regime_missing_after_backfill_row_n`
- `invalid_regime_row_n`
- `risk_on_evaluated_rate`
- `scope_filter_status`

必须输出 `pit_universe_scope_filter_audit.csv`：

- `split`
- `pre_pit_risk_on_row_n`
- `pit_membership_joined_row_n`
- `pit_membership_join_rate`
- `pit_valid_evaluated_row_n`
- `pit_valid_evaluated_rate`
- `pit_excluded_row_n`
- `pit_excluded_rate`
- `non_listed_excluded_row_n`
- `st_excluded_row_n`
- `suspended_excluded_row_n`
- `pit_universe_event_date_col`
- `pit_universe_date_key`
- `pit_scope_filter_status`

必须输出 `pit_universe_exclusion_diagnostic.csv`，至少按 `all`、`split`、`event_year`、`board_bucket`、`source_family_id` 分解：

- `dimension_name`
- `dimension_value`
- `pit_scope_filter_reason`
- `row_n`
- `unique_instrument_n`
- `winner_120_row_n`
- `winner_120_rate`
- `big_failure_proxy_row_n`
- `big_failure_proxy_rate`

`pit_scope_filter_reason` 至少包含：

- `pit_valid`
- `instrument_never_in_pit`
- `before_first_pit_membership`
- `after_last_pit_membership`
- `not_pit_member_on_event_t0_date`
- `not_listed_on_event_t0_date`
- `st_on_event_t0_date`
- `suspended_on_event_t0_date`

`pit_valid_evaluated_row_n` 是 11A1 后续所有 proxy、matched base、bootstrap 与 acceptance 计算的唯一分母。若 strict PIT 前 `risk_on_evaluated_row_n == 0` 或 strict PIT 后 `pit_valid_evaluated_row_n == 0`，最终状态必须为 `11A1_archetype_proxy_robust_payoff_risk_input_blocked`。

必须输出 `hard_failure_conditioning_reconciliation.csv`，在 `risk_on` evaluated denominator 内按 `split` 至少包含；`analysis_regime_bucket` 作为固定审计字段输出，取值应为 `risk_on`：

- `labels_yaml_hard_failure_first_blocks_winner`
- `primary_denominator_row_n`
- `winner_120_n_10a`
- `winner_120_n_09a`
- `winner_label_mismatch_n`
- `fast_fail_10_n_10a`
- `fast_fail_10_n_09a`
- `fast_fail_label_mismatch_n`
- `fast_fail_first_before_or_at_confirm_20_n`
- `fast_fail_first_before_or_at_confirm_20_winner_n`
- `candidate_outcome_120d_status_censored_n`
- `reconciliation_status`

`fast_fail_first_before_or_at_confirm_20_n` 的可计算规则：

```text
selected_fast_fail_10_label == true
AND selected_fast_fail_touch_pos is not null
AND (
  08.confirm_20_touch_pos is null
  OR 08.confirm_20_touch_pos < 0
  OR selected_fast_fail_touch_pos <= 08.confirm_20_touch_pos
)
```

其中 `08.confirm_20_touch_pos` 来自 08 `candidate_family_event_labels.parquet`；`-1` 或负数表示 horizon 内未触及 confirm barrier。该表是 hard-failure conditioning 审计，不改变 10A frozen labels。若 09A 或 08 缺少上述字段，则必须输出 `hard_failure_reconciliation_source_incomplete`，最终状态不得高于 `11A1_archetype_proxy_robust_payoff_risk_statistics_incomplete`。

### 4.5 10A 到 09B uniqueness weights

左表：10A primary denominator。
右表：09B `sample_uniqueness_weights.parquet`。

join keys 与选择规则：

| 优先级 | 10A 字段 | 09B weight 派生字段 | 额外过滤 |
| --- | --- | --- | --- |
| 1 | `cost_bad_sample_weight_join_key` | `sample_id + "|" + selected_target_id + "|" + denominator_id + "|" + canonical_event_id + "|" + weight_horizon_id` | `weight_horizon_id == cost_bad_10_20_20d`, `scope_usage == supported_training`, `supported_training_scope_flag == true` |
| 2 | `fast_fail_sample_weight_join_key` | 同上 | `weight_horizon_id == fast_fail_10d`, `scope_usage == supported_training`, `supported_training_scope_flag == true` |

若 primary denominator row 无 `supported_training` 权重，允许 fallback 到同一 join key 的 `readout_only` row，但必须标记 `weight_scope_fallback_to_readout_only`。若同一 join key、同一 `weight_horizon_id`、同一 `scope_usage` 下对应多个 weight row，必须 blocker，不得任意选取。

输出必须保留：

- `final_sample_weight`
- `average_uniqueness`
- `time_decay_weight`
- `active_interval_start`
- `active_interval_end`
- `scope_usage`
- `supported_training_scope_flag`
- `weight_status`

### 4.6 10A 到 10C rejector score

左表：10A primary denominator。
右表：10C frozen reference slice。

join keys：

| 10A 字段 | 10C 字段 |
| --- | --- |
| `input_event_key` | `input_event_key` |
| `sample_id` | `sample_id` |
| `selected_target_id` | `selected_target_id` |
| `instrument` | `instrument` |
| `event_t0_date` | `event_t0_date` |

输出字段：

- `binding_canonical_event_id`
- `candidate_false_repair_score`
- `candidate_rank`
- `candidate_rejected_flag`
- `fast_fail_rejected_flag`
- `cascade_bucket`
- `active_interval_calendar_day_n`

这些字段只用于 readout，不允许进入 proxy membership。

## 5. 标签与 readout 定义

### 5.1 primary labels

| label | 来源 | 定义 |
| --- | --- | --- |
| `winner_120` | 10A | frozen 120d big winner label |
| `fast_fail_10` | 10A | `selected_fast_fail_10_label` |
| `false_repair_20` | 10A | `frozen_false_repair_20d_label` |
| `e1_missed_winner` | 10A | `E1_missed_winner_flag` |

### 5.2 composite risk exposure

`big_failure_proxy` 是审计型复合风险暴露，不是新的训练标签：

```text
big_failure_proxy = fast_fail_10 OR false_repair_20
```

所有报告必须同时列出：

- `fast_fail_10_rate`
- `false_repair_20_rate`
- `big_failure_proxy_rate`

不得只报告 composite 而隐藏 component。

### 5.3 payoff 与 path readout

| readout | 来源 | 用途 |
| --- | --- | --- |
| `forward_return_20d` | 08 | 短期 outcome readout |
| `forward_return_60d` | 08 | primary payoff readout |
| `forward_return_120d` | 08 | right-tail horizon readout |
| `mfe_20d/60d/120d` | 08 | capturable upper-bound readout |
| `mae_20d/60d/120d` | 08 | adverse path readout |

主 payoff 采用 `forward_return_60d`，因为它位于 20d repair/failure 与 120d big-winner 标签之间，既不过度短视，也不直接等价于 winner 标签。`winner_120_rate` 是右尾捕获主读数。

## 6. Proxy registry

### 6.1 registry 约束

11A1 最多允许 8 个预注册 proxy family。所有 supported proxy 必须满足：

- 只使用 §3.3 中 t0-visible feature。
- 阈值只在 train split 上拟合。
- 阈值拟合过程 outcome-blind。
- 每个 proxy 的字段、方向、阈值、类别必须输出到 `proxy_definition_registry.csv` 与 `proxy_threshold_registry.csv`。

### 6.2 proxy category

| category | 是否可进入 supported decision | 说明 |
| --- | --- | --- |
| `A_t0_feature_contract` | 是 | 09B t0-visible feature 构造 |
| `B_early_path_readout_only` | 否 | t0 后 3/5/10 日路径，只能作为后续 11A2 方向 |
| `C_retrospective_archetype_only` | 否 | winner profiling 的事后路径解释，不可全分母预测 |

11A1 的 `screen_supported` 只能来自 category A。

### 6.3 train-only quantile policy

所有数值阈值使用 primary denominator 的 train split 拟合，且在 label/outcome join 前完成。必须固定输出：

- `threshold_fit_split = train`
- `threshold_fit_denominator_id = post_dedup_risk_on_r_core`
- `threshold_fit_regime_scope = risk_on`
- `threshold_fit_population_id = 10A__same_instrument_cooldown_10d`
- `threshold_operator`
- `threshold_quantile`
- `threshold_value`
- `fit_row_n`
- `pre_imputation_non_null_n`
- `pre_imputation_missing_rate`
- `post_09b_transform_missing_rate`
- `missing_rate_source`

`pre_imputation_non_null_n` 与 `pre_imputation_missing_rate` 必须优先来自 09B `feature_transform_contract.json` 的 `missing_rate_before_impute`，并用 `feature_stationarity_audit.csv.raw_missing_rate` cross-check。不得用 09B 已 train-median-impute 后的 feature matrix 非空率冒充原始可用性。

所有 threshold quantile、`fit_row_n` 与 power floor 都必须在 `analysis_regime_bucket == risk_on` 的 train evaluated denominator 内计算。若某字段 train pre-imputation 非空样本少于 500，包含该字段的 proxy family 必须标记为 `proxy_input_underpowered`。若 pre-imputation missing audit 不可得，则该字段标记为 `pre_imputation_missing_audit_unavailable`；proxy 可继续计算，但最终状态不得高于 `11A1_archetype_proxy_robust_payoff_risk_statistics_incomplete`。

### 6.4 预注册 proxy family

#### P1_gap_event_proxy

category: `A_t0_feature_contract`

字段：

- `gap_open_pct`
- `intraday_range_atr_norm`
- `close_position_in_range`
- `amount_ratio_20d`
- `turnover_ratio_20d`
- `family_count`
- `channel_count`

membership:

```text
gap_open_pct >= train_p70
OR intraday_range_atr_norm >= train_p70
OR (amount_ratio_20d >= train_p70 AND close_position_in_range >= train_p60)
```

解释：捕捉事件日跳空、放量、日内位置较强的显性 event shock。

#### P2_shakeout_prior_path_proxy

category: `A_t0_feature_contract`

字段：

- `close_to_high_60`
- `close_to_high_120`
- `upper_shadow_pct`
- `close_position_in_range`
- `atr_pct_rank_60d`
- `stock_vs_board_20d`

membership:

```text
(close_to_high_60 <= train_p30 OR close_to_high_120 <= train_p30)
AND (upper_shadow_pct >= train_p60 OR close_position_in_range >= train_p50)
AND atr_pct_rank_60d >= train_p40
```

解释：捕捉前期不在高位、但事件附近有震荡或洗盘痕迹的路径。

#### P3_volatile_chop_proxy

category: `A_t0_feature_contract`

字段：

- `direction_entropy_20d`
- `atr_pct_rank_60d`
- `range_width_ratio_20d_60d`
- `intraday_range_pct`
- `return_20d_sigma_norm`

membership:

```text
direction_entropy_20d >= train_p60
AND atr_pct_rank_60d >= train_p60
AND range_width_ratio_20d_60d >= train_p60
```

解释：捕捉方向熵高、波动抬升、短期 range 扩张的震荡型候选。

#### P4_early_momentum_proxy

category: `A_t0_feature_contract`

字段：

- `return_5d`
- `return_20d`
- `stock_vs_market_20d`
- `stock_vs_board_20d`
- `ema20_slope_20d`
- `close_to_ema20`
- `momentum_percentile_20d`

membership:

```text
momentum_percentile_20d >= train_p70
AND return_20d >= train_p60
AND close_to_ema20 >= train_p50
```

解释：捕捉 t0 前已有相对强势和均线支撑的早动量候选。

#### P5_late_bloomer_proxy

category: `A_t0_feature_contract`

字段：

- `return_20d`
- `atr_pct_rank_60d`
- `prior_event_count_60d`
- `ema60_positive_run`
- `close_to_ema60`

membership:

```text
return_20d >= train_p35
AND return_20d <= train_p65
AND atr_pct_rank_60d <= train_p60
AND (prior_event_count_60d >= train_p50 OR ema60_positive_run >= train_p50)
```

解释：捕捉 t0 前不极端强势、但有事件重复或中期趋势基础的 late bloomer。

#### P6_clean_repair_proxy

category: `A_t0_feature_contract`

字段：

- `close_to_ema20`
- `close_to_ema60`
- `ema20_slope_20d`
- `ema60_slope_20d`
- `atr_pct_rank_60d`

membership:

```text
close_to_ema20 >= train_p50
AND close_to_ema60 >= train_p50
AND ema20_slope_20d >= train_p50
AND atr_pct_rank_60d <= train_p70
```

解释：捕捉均线结构较干净、波动不过度扩张的 repair 型候选。

#### P7_flow_confirmation_proxy

category: `A_t0_feature_contract`

字段：

- `amount_ratio_20d`
- `amount_ratio_60d`
- `turnover_ratio_20d`
- `turnover_ratio_60d`
- `quality_amount_flag`

membership:

```text
quality_amount_flag == 1
OR (amount_ratio_20d >= train_p70 AND turnover_ratio_20d >= train_p60)
```

解释：捕捉成交额与换手确认的流动性/关注度 proxy。

#### P8_recurrence_density_proxy

category: `A_t0_feature_contract`

字段：

- `prior_event_count_20d`
- `prior_event_count_60d`
- `family_count`
- `channel_count`
- `raw_cluster_event_count`

membership:

```text
prior_event_count_60d >= train_p70
OR raw_cluster_event_count >= train_p70
OR (family_count >= train_p60 AND channel_count >= train_p60)
```

解释：捕捉同标的或同事件簇重复出现的密度型候选。

## 7. Matched base

### 7.1 为什么需要 matched base

proxy-positive 与 full base 的直接比较可能混入时间、source pool 与事件密度差异。11A1 必须先过滤到 `analysis_regime_bucket == risk_on`，再提供 matched base，判断 proxy 是否在同一 regime 的可比分母下仍有 payoff-risk 优势。

### 7.2 primary matched cell

每个 proxy family 单独在 `risk_on` evaluated denominator 内构造 matched base。proxy-positive rows 与 proxy-negative rows 使用以下 cell 对齐：

```text
split
event_year_quarter
source_family_id
```

其中：

- `event_year_quarter` 从 `event_t0_date` 派生。
- `source_family_id` 来自 10A，是 primary matched cell 的事件族控制轴。
- `source_pool_id` 来自 10A，仅作为审计字段和 fallback，不作为 primary matched cell。
- 若 `source_family_id` 缺失，则使用 `source_pool_id` fallback，并把该 cell 标记为 `matched_base_source_family_fallback_to_source_pool`。
- 若两者均缺失，则该 cell 标记为 `matched_base_source_family_missing`。

matched base 采用 deterministic cell reweighting，不做随机抽样：

```text
matched_base_weight(row in negative cell c)
= proxy_positive_total_weight(c) / proxy_negative_total_weight(c) * row_weight
```

`row_weight` 使用 §4.5 的 `final_sample_weight`，缺失时为 1 并记录 `weight_missing_fallback_flag`。

zero/empty cell 处理：

- 若 cell 有 proxy-positive weight 但无 proxy-negative weight，该 cell 不得参与 matched base 计算。
- 被排除的 proxy-positive weight 必须进入 `unmatched_positive_weight`.
- `matched_positive_weight / total_positive_weight` 必须计入 §7.3 floor。
- 若 cell 有 proxy-negative weight 但无 proxy-positive weight，该 cell 对该 proxy 的 matched base 权重为 0。
- 禁止用全局 negative pool 填补空 cell，除非输出为单独 diagnostic，不得进入 supported 判定。

### 7.3 matched base 最低要求

每个 proxy 的每个 split 必须满足：

- proxy-positive eligible rows >= 100
- matched negative eligible rows >= 300
- 至少覆盖 6 个 `event_year_quarter`
- matched positive weight / total positive weight >= 0.8

否则该 split 标记为 `matched_base_underpowered`。如果 train 或 robustness underpowered，该 proxy 不得进入 supported。

### 7.4 risk_on scope audit

本轮不做 `risk_on` / `risk_off` / `transition` matched readout。`analysis_regime_bucket` 只用于 scope filtering：

- `risk_on` 行进入 evaluated denominator。
- `risk_off`、`transition`、`regime_missing_after_backfill` 行只进入 `risk_on_scope_filter_audit.csv`。
- supported/empty 判定不得引用非 `risk_on` 行的 payoff、winner 或 failure 读数。

## 8. Robust payoff-risk metrics

### 8.1 基础 count 与 coverage

每个 proxy family、split、matched status 必须在 `risk_on` evaluated denominator 内输出：

- `denominator_row_n`
- `proxy_positive_row_n`
- `proxy_positive_weight_sum`
- `proxy_coverage_rate`
- `winner_120_n`
- `winner_120_rate`
- `fast_fail_10_n`
- `fast_fail_10_rate`
- `false_repair_20_n`
- `false_repair_20_rate`
- `big_failure_proxy_n`
- `big_failure_proxy_rate`
- `e1_missed_winner_n`
- `e1_missed_winner_rate`

### 8.2 payoff distribution

对 `forward_return_20d`, `forward_return_60d`, `forward_return_120d` 输出：

- weighted mean
- winsorized mean, 1%/99%
- trimmed mean, 5%/95%
- median
- p05
- p25
- p75
- p90
- p95
- p99
- negative return rate

主比较字段为：

```text
median_forward_return_60d_delta_vs_matched_base
winsorized_mean_forward_return_60d_delta_vs_matched_base
```

### 8.3 path distribution

对 `mfe_20d`, `mfe_60d`, `mfe_120d`, `mae_20d`, `mae_60d`, `mae_120d` 输出同样分位数读数。报告中必须注明：

- MFE 是 capturable upper bound，不是 realized return。
- MAE 是 adverse path readout，不是止损策略结果。

### 8.4 exposure-day diagnostic readout

输出：

```text
return_60d_per_rejector_active_day_diagnostic
= weighted_sum(forward_return_60d * final_sample_weight)
  / weighted_sum(exposure_day_n * final_sample_weight)
```

`exposure_day_n` 来源优先级：

1. 10C `active_interval_calendar_day_n`
2. 09B weights `active_interval_end - active_interval_start + 1`

该指标只用于 capital-efficiency diagnostic，不是策略 EV，也不是严格的 horizon-normalized realized return。`forward_return_60d` 是固定 horizon outcome，`active_interval_calendar_day_n` 是 rejector/label active interval，两者时间概念不同；因此该指标不得进入 `proxy_supported` 判定。必须输出 `exposure_day_source`、fallback 比例，以及 `exposure_day_metric_status = diagnostic_only_mixed_time_concept`。

## 9. 稳健性审计

### 9.1 split 约束

阈值只在 `risk_on` train evaluated denominator 内拟合。评估必须在 `risk_on` evaluated denominator 内分别输出：

- `train`
- `validation`
- `robustness`
- `all`

`all` 只能是展示读数，不能作为 supported 判定依据。

### 9.2 bootstrap

每个 proxy family 必须做 block bootstrap：

- bootstrap_n: 1000
- random_seed: 20260616
- primary block level: `instrument`
- secondary robustness block level: `binding_canonical_event_id`
- 每次 bootstrap 同时重算 proxy-positive 与 matched base delta。
- acceptance probabilities 只使用 primary instrument-block bootstrap。
- secondary `binding_canonical_event_id` bootstrap 必须输出，但只作为 sensitivity readout；若 secondary 与 primary 方向冲突，报告标记 `episode_block_bootstrap_direction_conflict`。

输出：

- median delta
- 5% CI
- 95% CI
- probability(delta > 0)
- probability(risk_delta <= margin)
- `bootstrap_block_level`
- `bootstrap_usage_scope` in `{acceptance_primary, sensitivity_secondary}`

### 9.3 top-k sensitivity

对每个 proxy family，按 `weighted_forward_return_60d_contribution` 排序，分别删除：

- top 1 instrument
- top 3 instruments
- top 5 instruments
- top 1 event
- top 3 events
- top 5 events

重算：

- `winner_120_rate_delta`
- `median_forward_return_60d_delta`
- `winsorized_mean_forward_return_60d_delta`
- `big_failure_proxy_rate_delta`

删除后的读数输出到 `topk_sensitivity_readout.csv`。

### 9.4 overlap 与 incremental value

必须输出：

- proxy overlap matrix：任意两 proxy 的 Jaccard、intersection_n、union_n。
- conditional incremental readout：在已通过 proxy 集合之外，单个 proxy 的增量 coverage、winner_120 增量、big_failure 增量。

如果多个 proxy 高度重叠，报告不得重复计算为独立证据。

### 9.5 multiple-comparison audit

11A1 预注册 8 个 proxy family，但仍必须显式审计多重比较风险。runner 必须生成 `multiple_comparison_audit.csv`：

- `pre_registered_proxy_family_n`
- `evaluated_proxy_family_n`
- `supported_proxy_n`
- `diagnostic_candidate_proxy_n`
- `hard_veto_failed_proxy_n`
- `null_simulation_n`
- `null_expected_supported_proxy_n`
- `null_supported_proxy_n_p95`
- `actual_supported_exceeds_null_p95_flag`
- `multiple_comparison_status`

null simulation 规则：

1. 只在 `risk_on` evaluated denominator 内运行。
2. 在每个 `split + event_year_quarter + source_family_id` cell 内随机置换 proxy membership，保持每个 proxy 的 coverage 不变。
3. 每次 simulation 重新计算 hard veto、required evidence items 与 `evidence_score`。
4. 至少运行 500 次，random_seed 使用 `20260616`。

该审计解释为：proxy family 是否优于同 coverage、同时间/source-family 分布的随机 proxy；它不是总体 power test，也不用于重估 base rate。

`multiple_comparison_audit.csv` 是解释性审计，不得用于事后新增或删除 proxy family。若 `supported_proxy_n <= null_supported_proxy_n_p95`，最终 status 可以仍为 `screen_supported`，但报告必须标记 `supported_with_multiple_comparison_caveat`，并禁止把结果描述为强 family-wise evidence。

## 10. Rejected-subpopulation override readout

### 10.1 目的

该读数只回答：

> 被 10C reject 的样本中，是否存在某些 proxy 子群体具有足够右尾价值和可控风险，值得后续单独研究 override？

11A1 不允许直接推翻 10C rejector。

### 10.2 子分母

使用 `risk_on` evaluated denominator 内的 10C frozen reference slice：

```text
candidate_rejected_flag == true
```

按 proxy family 输出 rejected 子群体读数：

- rejected_proxy_row_n
- rejected_proxy_weight_sum
- rejected_proxy_winner_120_n
- rejected_proxy_winner_120_rate
- rejected_proxy_fast_fail_10_rate
- rejected_proxy_false_repair_20_rate
- rejected_proxy_big_failure_proxy_rate
- rejected_proxy_forward_return_60d_distribution
- rejected_proxy_mfe_120d_distribution

### 10.3 underpowered 规则

若任一 proxy 的 rejected 子群体满足以下任一条件：

- `rejected_proxy_row_n < 100`
- `rejected_proxy_winner_120_n < 30`
- `rejected_proxy_weight_sum < 50`

则该 proxy 的 override readout 必须标记为：

```text
override_readout_underpowered
```

underpowered 不代表负面结论，但禁止在报告中称其支持 override。

## 11. Acceptance rules

### 11.1 global input gates

以下任一失败，最终状态必须为 `11A1_archetype_proxy_robust_payoff_risk_input_blocked`：

- 主输入文件缺失。
- 10A primary denominator 为空。
- `analysis_regime_bucket == risk_on` 的 evaluated denominator 为空。
- 10A -> 09B feature join 成功率 < 99.5%。
- 10A -> 08 label join 成功率 < 99.5%。
- 所有 category A proxy 都因字段缺失或阈值 underpowered 无法计算。
- proxy registry 超过 8 个 family。
- category A proxy 使用了 outcome/path/rejector score 字段。

以下情形不得 `input_blocked`，但最终状态不得高于 `11A1_archetype_proxy_robust_payoff_risk_statistics_incomplete`：

- 10A -> 09A label frontier join 成功率 < 99.5%。
- 09A regime source 部分缺失但可由 10A `event_regime_bucket` 回填。
- `risk_off` 或 `transition` 行被 scope filter 排除。
- hard-failure conditioning reconciliation 所需字段部分不可得。
- pre-imputation missing audit 不可得。

### 11.2 proxy-level pass rules

单个 proxy family 的判定分成 hard veto 与 evidence score。不得把所有读数都写成生死门，避免在小样本下把真实但不稳定的方向过早杀死。

#### 11.2.1 hard veto

以下任一失败，则该 proxy 必须标记为 `proxy_hard_veto_failed`，不得进入 `proxy_supported`：

1. pre-registration / PIT / t0-validity 失败：
   - proxy family 未在 §6.4 预注册。
   - proxy family 使用 outcome/path/rejector score 字段。
   - proxy 阈值不是 train-only outcome-blind 拟合。
2. power 与 matched-base 失败：
   - train split underpowered。
   - robustness split underpowered。
   - train 或 robustness matched base coverage 不满足 §7.3。
3. CI-aware failure exposure 变差：
   - train 或 robustness 的 primary instrument-block bootstrap 中 `probability(big_failure_proxy_rate_delta_vs_matched_base <= 0.005) < 0.80`
   - train 或 robustness 的 primary instrument-block bootstrap 中 `probability(false_repair_20_rate_delta_vs_matched_base <= 0.005) < 0.75`
   - train 或 robustness 的 primary instrument-block bootstrap 中 `probability(fast_fail_10_rate_delta_vs_matched_base <= 0.005) < 0.75`
   - train 或 robustness 的 primary instrument-block bootstrap 中 `big_failure_proxy_rate_delta_vs_matched_base_p95 > 0.015`
4. top-k sensitivity 失败：
   - 删除 top 3 instruments 后 `median_forward_return_60d_delta < -0.003`
   - 删除 top 3 events 后 `median_forward_return_60d_delta < -0.003`

failure rate point estimates 与 top-k 后的 failure deltas 必须输出，但不得单独作为 hard veto；hard veto 使用上述 bootstrap/CI-aware failure criterion。

#### 11.2.2 evidence score

hard veto 全部通过后，runner 必须计算 `evidence_score`。每项通过得 1 分，最高 6 分：

| evidence item | 条件 |
| --- | --- |
| `median_payoff_noninferior` | train 与 robustness 中 `median_forward_return_60d_delta_vs_matched_base >= -0.002` |
| `winsorized_payoff_noninferior` | train 与 robustness 中 `winsorized_mean_forward_return_60d_delta_vs_matched_base >= -0.002` |
| `right_tail_capture_noninferior` | train 与 robustness 中 `winner_120_rate_delta_vs_matched_base >= 0` |
| `strict_advantage_marker` | robustness 中至少一个成立：`winner_120_rate_delta_vs_matched_base >= 0.005`，或 `median_forward_return_60d_delta_vs_matched_base >= 0.002`，或 `winsorized_mean_forward_return_60d_delta_vs_matched_base >= 0.002` |
| `bootstrap_payoff_stable` | `probability(median_forward_return_60d_delta > 0) >= 0.60` |
| `validation_not_conflicting` | validation split 未触发 `validation_direction_conflict` |

required evidence items：

- `right_tail_capture_noninferior`
- `strict_advantage_marker`

proxy family 状态：

| proxy_status | 条件 |
| --- | --- |
| `proxy_supported` | hard veto 通过，required evidence items 全部通过，且 `evidence_score >= 4` |
| `proxy_diagnostic_candidate` | hard veto 通过，但 `evidence_score < 4` |
| `proxy_hard_veto_failed` | 任一 hard veto 失败 |
| `proxy_underpowered` | 主要失败原因为 train/robustness power 或 matched-base coverage |
| `proxy_input_blocked` | 字段、join、阈值拟合或 t0-validity 失败 |

validation split 只作为 out-of-sample readout，不作为硬门槛；若 validation 方向与 train/robustness 明显冲突，必须在报告中标记 `validation_direction_conflict`.

### 11.3 final experiment status

最终 `acceptance_summary.csv` 必须给出唯一 `final_status`：

| status | 条件 |
| --- | --- |
| `11A1_archetype_proxy_robust_payoff_risk_screen_supported` | global gates 通过，无 statistics-incomplete ceiling，且 `risk_on` evaluated denominator 内至少一个 category A proxy 达到 `proxy_supported` |
| `11A1_archetype_proxy_robust_payoff_risk_screen_empty` | global gates 通过，无 statistics-incomplete ceiling，统计完整，但 `risk_on` evaluated denominator 内无 proxy 达到 `proxy_supported` |
| `11A1_archetype_proxy_robust_payoff_risk_statistics_incomplete` | 输入可读，但 matched base、ST/delist、horizon 或 power 审计不完整，无法给 supported/empty |
| `11A1_archetype_proxy_robust_payoff_risk_input_blocked` | global input gates 失败 |

## 12. 输出文件

### 12.1 publishable tables

输出目录：

```text
outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/
```

必须生成：

- `input_artifact_audit.csv`
- `denominator_contract_audit.csv`
- `join_key_canonical_id_audit.csv`
- `denominator_completeness_st_delist_audit.csv`
- `label_join_reconciliation_audit.csv`
- `regime_source_reconciliation_audit.csv`
- `risk_on_scope_filter_audit.csv`
- `pit_universe_scope_filter_audit.csv`
- `pit_universe_exclusion_diagnostic.csv`
- `hard_failure_conditioning_reconciliation.csv`
- `proxy_definition_registry.csv`
- `proxy_threshold_registry.csv`
- `proxy_membership_count.csv`
- `matched_base_construction_audit.csv`
- `robust_payoff_risk_readout.csv`
- `bootstrap_stability_readout.csv`
- `topk_sensitivity_readout.csv`
- `multiple_comparison_audit.csv`
- `proxy_overlap_matrix.csv`
- `conditional_incremental_value_readout.csv`
- `rejected_subpopulation_override_readout.csv`
- `acceptance_summary.csv`

### 12.2 local cache

输出目录：

```text
outputs/local_cache/11A1_archetype_proxy_robust_payoff_risk_audit/
```

允许生成：

- `proxy_scored_denominator.parquet`
- `matched_base_row_weights.parquet`
- `bootstrap_samples.parquet`

`proxy_scored_denominator.parquet`、`matched_base_row_weights.parquet` 与 `bootstrap_samples.parquet` 均只能包含 strict PIT 后的 `risk_on ∩ PIT-valid` evaluated rows；若保存 pre-scope 或 pre-PIT intermediate cache，必须另命名并在 manifest 标记为 `scope_audit_only`，不得被后续 acceptance 读取。local cache 默认不要求进入 git，但 manifest 必须记录其 path、sha256、row_count、schema。

### 12.3 report 与 manifest

必须生成：

- `outputs/publishable/reports/11A1_archetype_proxy_robust_payoff_risk_audit_report.md`
- `outputs/publishable/manifest_11A1_archetype_proxy_robust_payoff_risk_audit.json`

报告必须包含：

1. 数据来源与 join 成功率。
2. 主分母 row count、`risk_on` scope filter、strict PIT universe filter、PIT/ST/delist 完整性。
3. 每个 proxy 的字段、阈值和 coverage。
4. 每个 proxy 的 payoff-risk matched-base 对比。
5. `risk_on` 内 train/validation/robustness/all 分 split 读数。
6. `analysis_regime_bucket` 的 episode/event 回填来源、`risk_on` pre-PIT row count、PIT-valid evaluated row count、PIT exclusion reason，以及 `risk_off` / `transition` / missing 被排除的 row count；不得输出跨 regime proxy 支持性比较。
7. top-k sensitivity、bootstrap 与 multiple-comparison audit 解释。
8. rejected-subpopulation override readout，并明确 underpowered 状态。
9. final_status 与不能越界使用的说明。

## 13. 验证要求

### 13.1 单元测试

`tests/test_archetype_proxy_robust_payoff_risk_audit.py` 至少覆盖：

- join key 优先级：`feature_matrix_join_key` / sample-weight join keys / `input_event_key`，pipe split 只作为 fallback/cross-check。
- 10A -> 10C 取得 `binding_canonical_event_id`，以及 fallback status。
- proxy registry 不超过 8 个 family。
- category A proxy 字段全部来自 09B t0-visible contract。
- outcome/rejector/path 字段不能进入 proxy membership。
- 10A -> 09A join 与 `analysis_regime_bucket` 回填。
- `hard_failure_conditioning_reconciliation.csv` 的状态优先级。
- train-only quantile threshold fitting。
- pre-imputation missing audit 读取 `feature_transform_contract.json` / `feature_stationarity_audit.csv`。
- `big_failure_proxy = fast_fail_10 OR false_repair_20`。
- `analysis_regime_bucket == risk_on` scope filter：非 `risk_on` 行只进入 `risk_on_scope_filter_audit.csv`，不进入 threshold/matched/bootstrap/acceptance。
- strict PIT universe filter：`risk_on` 后必须先 inner join PIT universe，只保留 PIT-valid 行进入 09B weights、threshold/matched/bootstrap/acceptance；PIT miss/ST/停牌/非上市行只能进入 PIT 审计表。
- matched base deterministic cell reweighting 与 zero/empty cell 排除。
- primary instrument bootstrap 与 secondary event bootstrap 分离。
- hard veto、required evidence items 与 evidence score 分离。
- multiple-comparison audit 的 null simulation 输出。
- final status precedence。

### 13.2 运行验证

实现后至少运行：

```bash
uv run python -m pytest tests/test_archetype_proxy_robust_payoff_risk_audit.py
uv run python src/run_11a1_archetype_proxy_robust_payoff_risk_audit.py --config configs/config_11a1_archetype_proxy_robust_payoff_risk_audit.yaml
```

若项目当前没有 `uv` 环境，允许使用项目既有 Python runner，但必须在 report 中记录实际命令。

### 13.3 artifact validation

runner 完成后必须校验：

- publishable CSV 均非空，除非 final_status 是 input_blocked。
- manifest 中所有 publishable artifact sha256 可复算。
- `acceptance_summary.csv` 只有一个 final_status。
- report 中引用的核心数值能在 CSV 中定位。

## 14. 报告措辞约束

报告不得使用以下措辞：

- “proxy 是买入信号”
- “MFE 收益”
- “11A1 证明策略有效”
- “可以直接 override 10C”

允许使用：

- “proxy-positive 子群体”
- “matched-base 相对优势”
- “right-tail capture”
- “risk exposure”
- “diagnostic support”
- “underpowered，不足以支持 override”

## 15. 后续依赖

11A1 的唯一合法下游用途：

- 若 `screen_supported`：进入 11B，设计 rejector-safe proxy interaction 或 candidate ranking diagnostic。
- 若 `screen_empty`：停止 archetype proxy 方向，不放宽 gate。
- 若 `statistics_incomplete`：先补数据完整性或 matched-base power，不做策略化。
- 若 `input_blocked`：先修数据 contract，不做统计解释。

11C 的策略 EV 或组合级回测必须另立需求，不能由 11A1 report 直接外推。

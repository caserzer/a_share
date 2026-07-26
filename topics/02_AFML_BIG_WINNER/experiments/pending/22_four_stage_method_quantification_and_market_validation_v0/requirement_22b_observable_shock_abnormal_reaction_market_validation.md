# Requirement 22B：Observable Market/Group Shock Abnormal-Reaction Market Validation

## 0. 不可协商范围

22B 只验证 M1：

> 市场共同价格冲击、板块/行业特异 residual 价格冲击发生时，板块/行业相对其因果预期反应的异常强弱，是否对后续
> group-level price/path outcome 具有超过简单相对强弱的稳定历史增量。

研究顺序固定为：

```text
L0 market common shock
    -> L1 exchange-board / genuine-industry abnormal reaction
    -> L2 group internal breadth / dispersion / liquidity structure
    -> L3 stock relative-to-group reaction, deferred
```

本 requirement 定义 22B 的探索边界，并允许在 EP22 范围内直接实现、运行本地历史诊断、读取按 PIT/as-of checkpoint 分离的
outcome，以及迭代 competing variants；不需要逐阶段人工授权。22B 不建设综合决策路由器，不把 M1 与 M2–M6 合并，不生成
生产仓位、交易或对冲动作。

22B 允许：

- 绑定 22A 的 versioned working checkpoint，或生成等价的本地 compatibility checkpoint；
- 把现有 `U_project`/OHLCV 设为 B0 baseline，并对通过 22A D0–D3 的新增 source 建立 B1 augmented arms；
- outcome-blind 校验市场冲击、group residual 冲击、pair state 与 online episode；
- 对通过 source/PIT/readiness audit 的 exchange-board 或 genuine-industry arm 生成 group-level historical outcome；
- 完整比较 G0–G5 nested baselines；
- 报告 continuation 与 reversal 两个预注册 competing mechanisms；
- 做 shock-episode/date-block inference、时间稳定性、集中度和影响分析；
- 形成一个互斥 terminal state 和有限 claim ceiling；
- 若 gate 全部通过，最多提出 `forward_freeze_candidate` 复核。

22B 禁止：

- 在没有 22A-compatible source/PIT/as-of checkpoint 或本地等价 compatibility audit 时读取 outcome；
- 用 current industry、2025 taxonomy 或 concept/theme snapshot 回填历史；
- 把市值加权指数越线直接称为 market-wide shock，而不执行冻结的 breadth contract；
- 把行业原始涨跌直接称为 industry shock，而不先剥离 market/common response；
- 用未来收益、未来恢复、未来高低点或未来传播选择 shock cutoff、event type 或 episode boundary；
- 把只有官方行业指数收益的数据写成拥有成分股 breadth/dispersion；
- 把同一 shock-date 下的 group rows 当作独立统计证据；
- 在 G3 不优于 G2 时用 G4/G5 掩盖 residual 失败；
- 从 secondary horizon、方向、group family 或 event type 中挑选最好结果升级 primary；
- 生成个股 ranking、个股 future label、stock-level action 或 Big Winner cohort；
- 声称识别了真实新闻来源、市场共识、语义 surprise、过度反应或不足反应；
- 声称 historical result 是 true OOS、forward support、可部署 alpha 或真实交易策略。

固定治理语义：

```text
module_id = M1
phase_id = 22B
evidence_role = design_contaminated_historical_real_market_evidence
primary_reaction_unit = eligible_group_portfolio
primary_inference_unit = market_or_group_shock_episode_plus_date_block
stock_level_arm = deferred_out_of_22B_scope
semantic_event_arm = data_blocked_without_timestamped_source
price_shock_causal_origin = unidentified
exploratory_historical_support_claim_allowed = true
confirmatory_support_claim_allowed = false
forward_support_claim_allowed = false
decision_router_authorized = false
cross_module_model_authorized = false
position_sizing_authorized = false
portfolio_backtest_authorized = false
deployment_authorized = false
live_trading_authorized = false
routine_local_implementation_allowed = true
routine_historical_exploration_allowed = true
public_read_only_data_discovery_allowed = true
public_read_only_download_and_cache_allowed = true
per_stage_human_authorization_required = false
mandatory_intermediate_seal = false
```

若只运行价格冲击 proxy，22B 的最高历史终态只能是：

```text
component_proxy_only_historically_informative
```

不得输出 `component_directly_measurable_historically_stable`。

本文的 `freeze/frozen` 默认表示“在当前 attempt 内固定，防止 outcome 后调参或改口径”，不是人工授权或 immutable seal。
探索者可以通过新 `attempt_id` 尝试其他预先记录的方向；只有 `formal_forward_freeze` 才是跨 attempt 的正式不可变合同。

本 requirement 中某个 arm 的 `data_blocked` 不等于 M1 永久关闭。只有关联 data gap 的 source-search budget 已完成，或 source
明确需要尚未批准的凭据、付费或许可，才可把对应 data limitation 升级为 module terminal。

---

## 1. 身份、文件与探索边界

```text
experiment_id = 22_four_stage_method_quantification_and_market_validation_v0
phase_id = 22B
module_id = M1
run_id = 22B_observable_shock_abnormal_reaction_market_validation_v0
contract_version = 22B_M1_v0
requirement_status = exploration_specification_ready
requirement_file = requirement_22b_observable_shock_abnormal_reaction_market_validation.md
research_plan_file = research_plan.md
config_file = configs/config_22b_observable_shock_abnormal_reaction_market_validation.yaml
runner_file = src/run_22b_observable_shock_abnormal_reaction_market_validation.py
test_file = tests/test_22b_observable_shock_abnormal_reaction_market_validation.py
output_root = outputs/22B_observable_shock_abnormal_reaction_market_validation_v0
```

探索执行模式：

```text
requirement_revision_allowed = true
local_implementation_allowed = true
preoutcome_execution_allowed = true
historical_outcome_exploration_allowed = true
variant_iteration_allowed = true
per_stage_human_authorization_required = false
public_read_only_data_discovery_allowed = true
public_read_only_download_and_cache_allowed = true
formal_forward_freeze_allowed = false
L3_stock_scope = deferred_to_separate_exploratory_variant
production_or_live_execution_allowed = false
```

在 EP22 数据探究范围内，可以直接创建或修订 config、runner、tests，物化 preoutcome checkpoint，发现和缓存无需新凭据或付费的
公开 read-only 数据，并在内部 PIT/schema/hash 校验通过后自动继续 historical outcome。每次 variant 必须有独立 `attempt_id`、
config/input/code/source identity 和 search-accounting 记录。正式 forward freeze、生产部署、live trading、外部系统写操作或
付费/新凭据数据仍需另行授权。

working attempt 可以修复和重跑；checkpointed attempt 不得静默覆盖。以下任一变化至少要求新 `attempt_id`，语义不兼容时要求
新 contract version：

- market benchmark、market breadth source/布尔组合或 shock cutoff；
- group taxonomy、membership source、index source、weighting 或 group family；
- expected-response model、lookback、minimum pairs、rest-of-market policy 或 controls；
- group residual cutoff、localized-share cutoff、event type 或 episode rule；
- primary horizon/outcome、secondary family、baseline、effect floor 或 sample floor；
- split、purge、embargo、bootstrap、multiplicity 或 terminal-state mapping；
- timing、return source、missingness、tradability、corporate-action 或 execution semantics。

### 1.1 Config contract

未来 config 必须是 22A registry 或本地 22A-compatibility registry 的 machine-resolved snapshot。探索 variant 可以显式修改值，
但必须形成新 attempt 并进入 search accounting，不得保留为隐含运行时人工选择。

至少包含：

```text
identity:
    experiment_id, phase_id, module_id, run_id, contract_version

paths:
    requirement_file, research_plan_file, upstream_22a_root,
    project_universe_file, benchmark_file, trading_calendar_file,
    security_master_file, raw_daily_root, qfq_daily_root,
    eligible_group_index_files, eligible_group_membership_files,
    candidate_source_cache_roots, data_gap_registry_file,
    source_incremental_value_experiment_registry_file,
    output_root

upstream:
    22A_contract_version, 22A_terminal_state, 22A_manifest_sha256,
    22A_output_hashes_sha256, M1_22A_module_status,
    22A_snapshot_state, local_compatibility_checkpoint_or_null,
    M1_eligible_arm_ids, M1_claim_ceiling

boundary:
    history_date_min, history_date_max, calendar_alias

market_shock:
    benchmark_alias, return_semantics,
    center_method, center_lookback_sessions,
    scale_method, scale_lookback_sessions, minimum_history_sessions,
    positive_z_cutoff, negative_z_cutoff,
    absolute_return_floor_or_null,
    breadth_source_ids, breadth_boolean_rule,
    positive_breadth_cutoff, negative_breadth_cutoff,
    minimum_supported_group_n, market_wide_scope_policy

group:
    primary_group_family, eligible_group_ids,
    group_return_source_mode, weighting_mode,
    membership_availability_lag, weight_availability_lag,
    rest_of_market_policy, benchmark_contamination_policy,
    expected_response_model, expected_response_lookback_sessions,
    expected_response_minimum_pairs, expected_response_controls,
    residual_scale_method, residual_scale_lookback_sessions,
    positive_group_z_cutoff, negative_group_z_cutoff,
    localized_group_share_maximum,
    style_cluster_detection_policy

data_value:
    baseline_arm_id, augmented_arm_ids,
    source_attempt_ids, source_lineage_hashes,
    universe_pairing_policy, common_date_pairing_policy,
    common_group_pairing_policy, denominator_attribution_policy,
    source_search_family_id, source_multiplicity_family_id

episode:
    cooldown_sessions, maximum_age_sessions,
    same_direction_merge_rule, opposite_direction_merge_rule,
    propagation_update_rule

internal_structure:
    enabled_arm_ids, breadth_definition, residual_breadth_definition,
    dispersion_definition, contribution_definition,
    leader_top_k, amount_anomaly_lookback,
    turnover_anomaly_lookback, liquidity_definition,
    limit_status_source, suspension_source

outcome:
    entry_clock, primary_horizon_sessions,
    secondary_horizon_sessions, primary_return_semantics,
    abnormal_return_semantics, path_sampling_clock,
    mae_definition, mfe_definition, recovery_definition,
    missing_path_policy

baseline:
    required_arm_ids = [G0,G1,G2,G3,G4,G5],
    EP20B_SRC_like_group_comparator_formula

modeling:
    primary_estimand_formula, frozen_event_type_interactions,
    frozen_direction_interactions,
    feature_standardization_method,
    linear_solver, singular_design_policy,
    chronological_crossfit_schedule,
    minimum_train_episode_n,
    prediction_metric_ids,
    block_incremental_test_ids,
    coefficient_orientation_registry

split:
    chronological_fold_registry, purge_sessions, embargo_sessions,
    sample_role_registry

inference:
    primary_family_id, multiplicity_method,
    bootstrap_method, bootstrap_block_length_sessions,
    bootstrap_repetitions, bootstrap_seed,
    confidence_level, adjusted_interval_rule

gates:
    every value from versioned 22A or compatibility power/effect/stability registries

serialization:
    json_allow_nan=false, csv_float_format="%.12g",
    csv_encoding=utf-8, csv_line_ending=LF,
    parquet_engine=pyarrow, parquet_compression=zstd,
    gzip_compresslevel=9, gzip_mtime=0
```

Unknown key、缺失 key、requirement/config/22A registry 不一致或未记录的 CLI override 必须 fail closed。合法 variant 通过新
`attempt_id` 和显式 resolved config 表达。

---

## 2. 共享基线与探索运行条件

### 2.1 22A 是优先共享基线，不是人工授权闸门

22B 优先读取 `checkpointed` 或 `validated_working_result` 的 22A snapshot：

```text
22A_terminal_state in {
    22A_contract_ready_for_selected_component_validation,
    22A_partial_data_ready_with_blocked_modules
}

M1_22A_module_status in {exploration_ready, exploration_ready_low_power}
M1_construct_status not in {construct_blocked}
selected_22B_arm_data_status in {
    eligible_for_downstream_exploration,
    eligible_but_low_power
}
```

若完整 22A snapshot 尚未生成，22B 可以在 `preoutcome/local_22a_compatibility/` 物化本 requirement 实际需要的 source、PIT、
threshold、split、effect/support 与 claim-ceiling 子集，并用相同 schema/hash 规则记录。此时：

```text
upstream_mode = local_22a_compatibility_checkpoint
provisional = true
maximum_claim = exploratory_historical_M1_only
```

它可以继续 historical exploration，但必须在报告中列出与正式 22A 的未对齐项。无论使用哪种模式，都不需要逐 stage 人工批准。

22A 至少必须提供并由 22B 复算 hash：

```text
source_claim_registry.csv
data_gap_and_candidate_source_registry.csv
source_discovery_and_acquisition_attempt_log.csv
data_source_availability_and_pit_audit.csv
candidate_source_field_coverage_profile.csv
candidate_source_pit_reconstructability_audit.csv
source_construct_and_support_gain_registry.csv
source_incremental_value_experiment_registry.csv
field_availability_timestamp_registry.csv
module_estimand_registry.csv
module_primary_secondary_metric_registry.csv
module_baseline_registry.csv
historical_split_and_sample_role_registry.csv
multiplicity_family_registry.csv
power_and_support_preflight.csv
m1_group_taxonomy_and_source_registry.csv
m1_group_membership_and_weight_pit_audit.csv
m1_common_shock_date_census.csv
m1_market_group_shock_episode_census.csv
m1_group_reaction_asof_panel.csv
m1_shock_threshold_power_and_support_preflight.csv
module_research_readiness.csv
claim_ceiling_registry.csv
manifest.json
output_hashes.csv
```

在 shared-22A 模式下，任何 required artifact 缺失、hash mismatch、schema mismatch 或 M1 行不唯一时，切换到显式
`local_22a_compatibility_checkpoint` 或停止该 attempt；不得静默补猜：

```text
upstream_22a_integrity_gate = fail
terminal_state = component_run_incomplete_working
historical_outcome_read_allowed =
    true only after local compatibility checkpoint passes
```

### 2.2 计划时本地 inventory，不是运行时 authority

本 requirement 生成时只确认以下候选存在：

```text
project_universe:
    topics/02_AFML_BIG_WINNER/data/processed/universe/
    pit_topn_400_100_executable_daily.csv

benchmark_panel:
    topics/02_AFML_BIG_WINNER/data/processed/index/
    benchmark_indices_daily.csv
    aliases = {all_a, csi300, chinext_index}

benchmark_source_audit:
    topics/02_AFML_BIG_WINNER/data/processed/index/
    benchmark_indices_source_audit.csv

trading_calendar:
    topics/02_AFML_BIG_WINNER/data/raw/akshare/status/
    trading_calendar.csv

security_master:
    topics/02_AFML_BIG_WINNER/data/raw/akshare/status/
    instrument_metadata_target_universe.csv

daily_price_roots:
    topics/02_AFML_BIG_WINNER/data/raw/akshare/day/raw
    topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq
```

当前未发现可直接使用的 historical genuine-industry index/membership source。该观察不等于运行时证明；22A 或本地 compatibility
checkpoint 必须重新审计。新文件出现后可以在新 attempt 中审计和尝试，但不得未经审计自动提高 claim ceiling。

### 2.3 Arm eligibility matrix

每个 arm 独立判断 readiness、独立输出状态：

| arm_id | 所需数据 | 数据通过时可做 | 数据不通过时 |
|---|---|---|---|
| `MKT_CENSUS` | official market benchmark + frozen breadth | market shock/date/episode | `data_blocked` |
| `EXCHANGE_BOARD_RETURN` | PIT board membership + daily price | board return/residual/outcome | `data_blocked` |
| `EXCHANGE_BOARD_STRUCTURE` | 上述数据 + constituent status/amount | board breadth/dispersion/liquidity | `data_blocked` |
| `INDUSTRY_RETURN_ONLY` | audited historical official industry-index OHLCV | industry return/residual/outcome | `data_blocked` |
| `INDUSTRY_INTERNAL_STRUCTURE` | PIT industry membership + constituent fields | industry breadth/dispersion/liquidity | `data_blocked` |
| `L3_STOCK_DECOMPOSITION` | separate exploratory requirement | 不在 22B scope | `deferred_out_of_scope` |

`INDUSTRY_RETURN_ONLY` 通过不自动使 `INDUSTRY_INTERNAL_STRUCTURE` eligible。行业 arm 阻断不阻止可运行的 exchange-board arm，但
final report 必须明确结论不等于行业结论。

### 2.4 Existing-data baseline 与 candidate-source augmented arms

22B 的默认 B0：

```text
B0_existing_local_baseline =
    U_project PIT top-400 main board + top-100 ChiNext
    + local official benchmark panel
    + local raw/qfq OHLCV
    + existing status/security-master fields
```

B0 是可复现 baseline，不是 M1 数据上限。通过 22A D0–D3 或本地 compatibility audit 的新增 source 必须作为独立 B1+ arm：

```text
B1_broad_PIT_universe_breadth
B2_official_industry_index_return
B3_PIT_industry_membership_and_internal_structure
B4_PIT_free_float_or_improved_weighting
B5_auction_or_intraday_first_executable_timing
B6_timestamped_semantic_event_secondary
```

每个 augmented arm 必须绑定 `source_attempt_id`、raw/source hash、timestamp/revision contract、coverage profile、claim ceiling 和
search family。不得把新 source 静默写入 B0。

数据 usefulness 分两步：

```text
contract gain:
    construct fidelity、coverage、group/event/date support、benchmark contamination、
    missingness 与 executable timing 是否改善

empirical gain:
    在 paired/common denominator 上，
    B1+ 相对 B0 是否增加 G3-over-G2 增量、稳定性或可证伪能力
```

必须同时发布：

```text
source_contract_gain_readout.csv
source_incremental_empirical_value_readout.csv
source_search_and_multiplicity_accounting.csv
```

`source_incremental_empirical_value_readout.csv` 至少包含：

```text
source_attempt_id
baseline_arm_id
augmented_arm_id
incremental_estimand_id
common_date_n
common_episode_n
common_group_n
denominator_added_n
denominator_removed_n
construct_gain_state
support_gain
B0_effect
B1_effect
B1_minus_B0
adjusted_interval
stability_delta
concentration_delta
claim_ceiling_delta
empirical_value_state
```

`empirical_value_state` 只能为：

```text
source_adds_incremental_historical_evidence
source_changes_or_falsifies_prior_interpretation
source_no_incremental_value
source_empirical_value_unstable
source_empirical_value_low_power
source_not_evaluable_due_to_PIT_or_pairing
```

source 选择属于 multiplicity/search accounting。不能从多个 provider、taxonomy、universe 或 timestamp 版本中只报告最有利结果。

---

## 3. 研究问题、冻结假设与 claim ceiling

### 3.1 Primary question

```text
在 outcome-blind 预注册的 market/group shock dates 上，
group reaction residual 是否相对 simple group-minus-market RS
对后续 group-adjusted payoff、continuation/reversal 或 path damage
具有稳定增量？
```

### 3.2 Secondary questions

1. `pure_market_common_shock` 与 `group_specific_residual_shock` 的 forward path 是否不同？
2. `market_shock_with_group_amplification` 与 `market_shock_with_group_resistance` 是否具有不同的后续形态？
3. group breadth、residual breadth、dispersion、volume/liquidity 和 concentration 是否对 G3 提供预注册增量？
4. 关系是否跨方向、年份、fold、board/industry source 与 market state 稳定？
5. 结果是否只是 EP20B-SRC-like group trailing residual continuation 的重命名？
6. broad PIT universe、genuine industry、improved weighting、intraday timing 或 semantic-event source 相对 B0 是否增加 construct、
   support 或 empirical value，还是只是更多数据但没有增量？

### 3.3 冻结假设

```text
H1a:
market common shock 下，group reaction residual 对后续 group-adjusted path
相对 G2 具有稳定增量。

H1b:
group-specific residual shock 与 pure market common shock 是不同 estimand，
其 forward association 在预注册方向和时间 fold 中可复现。

H1c:
G4/G5 对 G3 的增量不是少数权重 group/name、raw return、beta、
volatility、liquidity 或 benchmark concentration 的机械贡献。

H1d:
结果不是 EP20B-SRC-like group trailing residual continuation。
```

Continuation 与 reversal 是 competing mechanisms，不预先把 residual 写成“低估/高估”：

```text
continuation:
    sign(group_reaction_residual_t)
    == sign(forward_group_abnormal_return)

reversal:
    sign(group_reaction_residual_t)
    != sign(forward_group_abnormal_return)
```

两者必须同时进入冻结的 multiplicity family。不得看到结果后只报告其中一个。

### 3.4 不回答的问题

22B 不回答：

- 哪条新闻导致冲击；
- 当时市场一致预期是多少；
- 价格相对基本面究竟过度还是不足；
- 哪个个股可以买卖；
- 如何分配板块仓位；
- 如何与 M2–M6 组合；
- 是否存在成本后可部署策略。

### 3.5 Claim ceiling

若结果通过：

```text
allowed_claim =
    在限定数据、group taxonomy、PIT 时点和历史样本中，
    observable group reaction residual 对后续 group path
    存在超过简单 group-relative-strength 的稳定历史关联。
```

禁止升级为：

```text
semantic_event_surprise_identified
market_expectation_error_identified
fundamental_mispricing_identified
tradable_industry_rotation_strategy
true_out_of_sample_support
```

---

## 4. Staged exploration 与 outcome separation

### 4.1 五阶段执行

```text
S0 contract_resolve_and_upstream_integrity
    reads: requirement, research plan, 22A working snapshot or local compatibility inputs
    writes: contract resolution + input/hash/scope audit
    outcome access: forbidden

S0D candidate_source_discovery_and_contract_profile
    reads: public read-only source metadata/payload and 22A gap registry
    writes: source attempt/cache/PIT/coverage/construct-gain audit
    outcome access: forbidden

S1 preoutcome_replay_and_formula_qa
    reads: only PIT-eligible price/membership/status inputs
    writes: independently verified shock/group/as-of audit bundle
    outcome access: forbidden

S2 preoutcome_checkpoint
    checkpoints: exact as-of bundle hash, eligible rows, event/episode membership
    writes: preoutcome manifest + checkpoint receipt
    outcome access: forbidden

S3 historical_outcome_materialization
    requires: S2 internal PIT/schema/hash checks pass
    reads: only post-first-usable-time prices required by frozen horizons
    writes: forward outcome bundle

S4 inference_report_and_working_snapshot
    reads: checkpointed S2 + S3 only
    writes: B0/B1 comparisons, inference, source-value readout,
            terminal decision, report, manifest, hashes
```

S0–S4 是防止 outcome 泄漏和保留可复现性的计算顺序，不是人工授权关卡。单次本地探索命令可以在每个内部 gate 通过后自动推进到
下一 stage；失败时保留 attempt checkpoint 并允许修复后用新 attempt 重跑。

S0–S2 不得读取包含以下字段或其可逆代理的任何 artifact：

```text
forward_return
forward_abnormal_return
future_high
future_low
mae
mfe
recovery_date
time_to_recovery
continuation_flag
reversal_flag
big_winner
winner_episode
future_market_state
```

### 4.2 Stage-specific read whitelist

每次文件读取都必须写入：

```text
preoutcome/access_audit.csv
```

字段：

```text
stage_id
access_sequence
artifact_path
artifact_sha256
declared_role
allowed_by_whitelist
contains_outcome_or_proxy
access_timestamp
status
blocking_reason
```

未列入 config whitelist 的路径、其他 working episode output、报告文字反推的逐行数据、validation/robustness outcome 都必须 fail。

### 4.3 Automatic stage transition binding

S2 checkpoint 至少包含：

```text
checkpoint_schema_version
run_id
contract_version
attempt_id
next_stage = S3_historical_outcome_materialization
preoutcome_bundle_sha256
eligible_event_set_semantic_sha256
eligible_group_pair_set_semantic_sha256
config_sha256
requirement_sha256
checkpointed_at
internal_validation_status
```

只有 `internal_validation_status = pass` 且所有 hash 匹配时，runner 才能自动读取 future outcome。hash 不匹配时停止当前 attempt，
不需要等待人工批准；修复后生成新 checkpoint。

---

## 5. 时间、calendar、return 与 stable-key 合同

### 5.1 Primary clock

```text
shock_observation_time = close(t)
feature_cutoff = close(t)
first_usable_time = next executable open after t
outcome_start = first_usable_time
```

close `t` 才形成的 benchmark return、group return、breadth、dispersion、amount 和 liquidity 不得在 close `t` 成交。

Overnight/open shock 不属于 v0 primary。没有集合竞价/分钟级 first-executable source 时：

```text
open_shock_arm = not_run_due_to_non_executable_same_open_timing
```

### 5.2 Trading calendar

- 唯一 session 顺序来自 22A/compatibility checkpoint 判定可用的 trading calendar；
- benchmark、group index 和 stock rows 必须映射到同一 canonical session；
- `t+H` 指从 first usable session 起按 canonical session 计数，不是自然日；
- benchmark/group/constituent calendar mismatch 不得 forward-fill；
- 同一 date 的 unavailable group 不得从 future row 回填。

### 5.3 Return source

Market/group-index arm 使用经 checkpoint 审计可用的 index OHLCV。自建 group arm 使用 checkpoint 记录的 raw/qfq continuity policy。

至少区分：

```text
raw_close_return
provider_qfq_close_return
official_index_close_return
forward_open_to_open_return
```

不得把 provider qfq 称为 exact total-return database。raw/qfq discontinuity、除权除息、停复牌和涨跌停状态必须进入 audit。

### 5.4 Stable keys

```text
market_shock_key =
    run_id | shock_date | market_benchmark_alias | shock_policy_id

group_pair_key =
    market_shock_key | group_family_id | group_id

group_shock_key =
    run_id | shock_date | group_family_id | group_id | group_shock_policy_id

episode_key =
    run_id | episode_scope | scope_id | episode_start_date | episode_policy_id

outcome_key =
    group_pair_key | outcome_semantics | horizon_sessions
```

Key 必须由 canonical strings 生成稳定 SHA256；不得依赖 dataframe row order 或 Python process hash。

### 5.5 Chronological split

Exact fold、purge 和 embargo 由绑定的 22A/compatibility checkpoint 冻结。单个 attempt 内 runner 只能复制，不能根据 outcome
重选。所有 market/group rows belonging to the
same episode 必须进入同一 fold。若 episode 跨 split boundary，按 22A 冻结的 whole-episode assignment 或 exclusion policy 处理。

---

## 6. Market common shock 公式

### 6.1 Causal standardized magnitude

```text
market_return_t =
    benchmark_close_t / benchmark_close_t-1 - 1

market_center_t-1 =
    center(market_return through t-1; frozen lookback)

market_scale_t-1 =
    robust_scale(market_return through t-1; frozen lookback)

market_shock_z_t =
    (market_return_t - market_center_t-1) / market_scale_t-1
```

Center、scale、lookback、minimum history、positive/negative cutoff 和 zero-scale policy 必须来自 22A。Scale 非有限或非正时该 row
不可评估，不得设为零或 epsilon 后继续。

```text
market_magnitude_pass_t =
    market_shock_z_t >= positive_z_cutoff
    OR market_shock_z_t <= negative_z_cutoff

absolute_floor_pass_t =
    true, if absolute_return_floor is null
    otherwise abs(market_return_t) >= absolute_return_floor
```

`1%` 只可由 22A 选择为 `absolute_return_floor` 候选，不能在 22B outcome 后调整。

### 6.2 Breadth confirmation

Breadth source 和布尔组合完全继承 22A：

```text
group_direction_breadth_t =
    count(eligible groups with return sign == market shock sign)
    / count(evaluable eligible groups)

instrument_direction_breadth_t =
    count(PIT eligible instruments with return sign == market shock sign)
    / count(PIT eligible instruments with finite eligible return)

market_breadth_pass_t =
    frozen_boolean_rule(group_direction_breadth_t,
                        instrument_direction_breadth_t,
                        other_pre_registered_confirmation)

market_common_shock_t =
    market_magnitude_pass_t
    AND absolute_floor_pass_t
    AND market_breadth_pass_t
```

Denominator 必须逐日发布。若支持 group 数低于冻结 floor，不能把两三个 group 的同向变化称为 market-wide confirmation。

### 6.3 Index-concentrated state

```text
index_concentrated_or_group_led_move_t =
    market_magnitude_pass_t
    AND absolute_floor_pass_t
    AND NOT market_breadth_pass_t
```

该状态不得进入 `pure_market_common_shock`，但必须保留在 denominator/audit 中，不能静默删除。

### 6.4 Shock-threshold immutability

`market_shock_date_census` 必须保留 minimum-history 通过后的全部 evaluable sessions，包括未越线和
`index_concentrated_or_group_led_move`；不得只发布 selected shock dates。这样才能复核 denominator、threshold membership，
也才能在市场未冲击的日期识别 group-specific residual shock。

22B 必须复算 22A candidate census 与 selected policy membership：

```text
expected_market_event_set_sha256
observed_recomputed_market_event_set_sha256
expected_group_event_set_sha256
observed_recomputed_group_event_set_sha256
expected_pair_state_panel_semantic_sha256
observed_pair_state_panel_semantic_sha256
```

不一致即 upstream/formula integrity fail。22B 不得重新比较阈值的 future performance。

---

## 7. Group return、预期反应与 residual shock

### 7.1 Group return source modes

```text
official_index:
    使用 audited historical group-index OHLCV

self_built_pit_portfolio:
    使用 membership/weight available no later than t-1
```

Self-built group 的 membership 与 weights 必须由 `t-1` 或更早信息冻结。默认不能用 close `t` market cap 重算当日 group weights。
Weighting mode 由 22A 冻结，至少输出 weight-sum、max weight、effective constituent N 和 coverage。

### 7.2 Industry eligibility

```text
INDUSTRY_RETURN_ONLY:
    official historical industry index passed source/timestamp audit

INDUSTRY_INTERNAL_STRUCTURE:
    PIT industry membership + constituent mapping + availability passed
```

只有前者时，internal-structure 字段必须：

```text
value = null
status = structural_missing_no_pit_membership
```

不得用当前成分回填。

### 7.3 Rest-of-market

自建 group primary：

```text
rest_of_market_return_ex_g,t =
    weighted return of PIT eligible market constituents excluding group g
```

Official-index-only group 若无法构造 rest-of-market，必须使用 22A 冻结的 fallback benchmark，并输出：

```text
rest_of_market_status
group_weight_in_fallback_benchmark_or_unknown
benchmark_contamination_status
claim_ceiling_adjustment
```

污染不可量化且 checkpoint 未登记 eligible fallback 时，该 group-specific arm fail closed。

### 7.4 Causal expected response

```text
expected_group_return_g,t =
    alpha_g,t-1
    + beta_market_g,t-1 * rest_of_market_return_ex_g,t
    + sum_k beta_k,g,t-1 * eligible_control_k,t
```

所有 coefficient 只使用 `<= t-1` 的 paired observations。Lookback、minimum pairs、controls、missingness 和 singular-matrix policy
由 22A 冻结。禁止：

- 用包含 `t` 的 regression；
- 用 full-history coefficient；
- 在 validation/robustness 中重新选择 controls；
- 为不同 group outcome 后选择不同模型；
- 把 target group 自身机械放入 rest-of-market。

### 7.5 Group reaction residual 与 shock

```text
group_reaction_residual_g,t =
    observed_group_return_g,t - expected_group_return_g,t

group_residual_scale_g,t-1 =
    causal robust scale of model residuals through t-1

group_shock_z_g,t =
    group_reaction_residual_g,t / group_residual_scale_g,t-1

group_specific_shock_g,t =
    group_shock_z_g,t >= positive_group_z_cutoff
    OR group_shock_z_g,t <= negative_group_z_cutoff
```

Residual scale 非有限或非正、minimum pairs 不足或 source ineligible 时，该 pair 不可评估，不得以 raw group return 替代 G3。

---

## 8. Pair state、date state 与 online episode

### 8.1 Pair-state truth table

每个 `(date t, group g)` 必须且只能进入一个状态：

| market common shock | group residual shock | pair_state |
|---|---|---|
| false | false | `no_qualified_shock` |
| true | false | `market_common_response_within_expected_band` |
| false | true | `group_specific_residual_shock` |
| true | true，同向 | `market_shock_with_group_amplification` |
| true | true，反向 | `market_shock_with_group_resistance` |

Pair-state panel 的 materialization universe 是全部 evaluable group-date pairs，不是 market-shock dates 的子集。Primary inference
再按冻结 event states 取 cohort；不得在物化时丢掉 `false/false` denominator 或 market-false/group-true rows。

同向/反向以 `market_return_t` 与 `group_reaction_residual_g,t` 的 sign 比较；零值和 tolerance policy 由 config 冻结。

### 8.2 Date-level state

```text
pure_market_common_shock_date:
    market_common_shock_t
    AND no evaluable group has group_specific_shock_g,t

group_specific_residual_shock_date:
    NOT market_common_shock_t
    AND positive group-specific count
    AND group-specific share <= localized_group_share_maximum

joint_market_group_shock_date:
    market_common_shock_t
    AND at least one evaluable group is amplification or resistance

latent_common_or_style_cluster_date:
    multiple groups move residually together beyond frozen localization rule

index_concentrated_or_group_led_move_date:
    Section 6.3 state
```

Date-level states 必须互斥。无法互斥时是 formula bug，不允许按优先顺序静默覆盖。

### 8.3 Style-cluster guard

多个相同 board/style 的行业 residual 同向越线时，必须按 22A 冻结 mapping 审计 `style_cluster_shock`。若 mapping 不可得：

```text
style_cluster_status = not_evaluable
industry_specific_claim_ceiling = downgraded
```

不得机械生成多个独立行业证据。

### 8.4 Online episode

```text
episode_start = first causal trigger
episode_end = pre-registered cooldown or maximum_age
```

Episode state 只能由到当前 session 为止的信息更新：

```text
t group-only, t+1 market shock:
    t pair/date state remains unchanged
    episode update at t+1 = group_led_market_spillover

t market shock, t+1 group amplification:
    t pair/date state remains unchanged
    episode update at t+1 = delayed_group_amplification
```

Future recovery、高低点、future winner hit 或 outcome 不能定义 episode。所有 episode rows 进入同一 fold。

---

## 9. Group internal structure

只有 `group_internal_structure_arm = eligible` 时才计算本节。

### 9.1 Denominator

每个 group/date 的 denominator 是：

```text
membership valid by t-1
AND instrument in eligible PIT universe if required by scope
AND finite eligible return at t
AND status policy resolved without future information
```

必须报告：

```text
registered_constituent_n
evaluable_constituent_n
missing_return_n
suspended_n
limit_status_unknown_n
weight_coverage
```

### 9.2 Required observables

公式由 22A registry 冻结，至少支持：

```text
group_direction_breadth_t =
    share of evaluable constituents moving with observed group return

group_residual_breadth_t =
    share of evaluable constituents whose causal stock residual
    moves with group reaction residual

group_dispersion_t =
    frozen robust dispersion of constituent returns

leader_concentration_t =
    contribution share of frozen top-k contributors

group_amount_anomaly_t =
    current group amount / causal trailing group amount baseline - 1

group_turnover_anomaly_t =
    current group turnover / causal trailing group turnover baseline - 1

group_liquidity_change_t =
    frozen PIT liquidity proxy change
```

用于 `group_residual_breadth_t` 的 stock residual 只测量个股相对共同市场冲击的同期反应：

```text
expected_stock_common_response_i,t =
    alpha_i,t-1
    + beta_market_i,t-1 * rest_of_market_return_ex_group_g,t
    + eligible controls checkpointed by 22A/compatibility audit

stock_common_reaction_residual_i,t =
    observed_stock_return_i,t - expected_stock_common_response_i,t
```

Coefficient、minimum pairs、lookback 与 scaler 只用 `<= t-1`。不得把 contemporaneous observed group return 作为必选 control 后再声称
该 breadth 测量 group-wide abnormal reaction；若 checkpoint 允许 group control sensitivity，自建 group return 对目标股票必须
leave-one-out，并与 primary market-common residual breadth 分开。

Stock causal residual 仅允许聚合为 L2 group observable；不得发布 stock future labels、stock ranks 或 stock action。

### 9.3 Structural missingness

缺 membership、weight、amount、turnover、limit 或 suspension source 时，必须逐字段输出 status。不得以零填补，不得把缺字段的
group 与完整 group 混在同一 G4/G5 denominator。

---

## 10. Nested baselines 与 comparator

### 10.1 Frozen estimand 与 design matrix

Primary continuous estimand 是：

```text
effect_unit =
    bps of forward_group_abnormal_return
    per +1 causal train-standardized unit of group_reaction_residual

primary_incremental_question =
    after conditioning on G2 simple group-minus-market RS and frozen shock controls,
    does group_reaction_residual add stable forward information?
```

不得把“预测 top group 的收益”设为唯一 primary，因为 group 数可能过少且会混入 action/ranking 语义。

所有 feature transform 只在 train/expanding-past block 内拟合。默认分析 family 必须由 22A 在 outcome 前冻结为无超参数或完全固定
超参数的线性 nested model；若使用 OLS：

```text
solver = frozen deterministic least-squares solver
intercept = true
regularization = none
singular_or_rank_deficient_design = fail_closed_for_that_fold
```

若 22A 选择固定 ridge 等其他 family，必须在 22A registry 中给出 exact alpha、scaler、solver 和 coefficient semantics；22B
不得利用 outcome 搜索 hyperparameter。

Nested design matrix 至少遵循：

```text
G0:
    frozen market/group shock magnitude controls

G1:
    G0 + raw group return

G2:
    G0 + simple group-minus-market relative strength

G3:
    G2 + causal beta-adjusted group reaction residual

G4:
    G3 + eligible group breadth / residual breadth / dispersion block

G5:
    G4 + eligible volume / turnover / liquidity / concentration block
```

G1 与 G2 都必须报告，但 primary nested chain 是 `G2 -> G3 -> G4 -> G5`。Event-type、shock-direction 和 group-family
interaction 是否进入 pooled design，必须由 22A 固定；不得在结果后拆分或合并。

### 10.2 Chronological cross-fit

```text
for each evaluation fold:
    fit scaler and coefficients on eligible train/expanding-past episodes only
    freeze model
    score evaluation episodes without refit
    retain all group rows from one date/episode in the same side
```

Validation/robustness rows不得用于 scaler、orientation、feature selection、interaction selection 或 coefficient fitting。每个 fold
必须输出 train/evaluation episode N、design rank、condition status、coefficient vector hash 和 prediction hash。

Primary readout 同时包括：

```text
partial coefficient / adjusted interval for G3 residual term
G3 versus G2 out-of-fold prediction loss delta
G3 versus G2 out-of-fold economic association delta
```

Exact loss、economic association metric 和 directionally correct bound 由 22A 冻结。只改善 in-sample fit 不构成增量。

### 10.3 Common denominator

所有 G0–G5 使用同一可比较 denominator。若某字段缺失导致 G4/G5 denominator 缩小，必须同时输出：

```text
full_G3_denominator
common_G3_G4_denominator
common_G4_G5_denominator
denominator_delta_attribution
```

不得把 denominator 变化误写为 feature 增量。

### 10.4 Primary incremental comparison

```text
primary_incremental_test = G3 versus G2
```

若 G3 不优于 G2：

```text
G3_incremental_gate = fail
G4_G5_rescue_allowed = false
```

G4/G5 仍可作为 failure diagnosis，但不能形成 positive M1 terminal。

G4/G5 的 feature block 必须做 joint incremental test；不得从 block 内挑出显著单字段后把整个 arm 判 pass。

### 10.5 EP20B-SRC-like comparator

必须在本次 eligible group universe 上重新因果构造：

```text
group_trailing_residual_continuation_score =
    frozen 5D/10D aggregation of daily group market residual
```

不得直接使用 EP20B-SRC stock-level outcome 作为同口径 comparator。若 22B 只是在 group 上重跑 trailing residual momentum：

```text
terminal_state = component_duplicate_research_closed
```

### 10.6 Ranking/contrast mode

Analysis mode 由 22A 仅按 group 数和 support 冻结：

```text
cross_group_rank_mode
two_group_contrast_mode
continuous_pair_panel_mode
```

不得在 outcome 后根据哪个模式显著而切换。Cross-group rank 必须达到 22A 冻结的 minimum evaluable group N；否则不可生成
top-minus-bottom spread。

---

## 11. Forward outcome contract

### 11.1 Outcome origin

所有 outcome 从 `first_usable_time` 开始。Primary horizon 由当前 attempt 的 22A/compatibility checkpoint 冻结；候选只有：

```text
H1, H3, H5, H10, H20 trading sessions
```

其余 horizon 禁止。

### 11.2 Group forward return

Official-index arm：

```text
forward_group_open_to_open_return_g,t,H =
    group_index_open_at_horizon_exit
    / group_index_open_at_first_usable_time - 1
```

Self-built arm 使用 event-time frozen constituent set 和 frozen entry weights。不得在 outcome window 内按未来市值重平衡。Exact
missing constituent、delisting、suspension 和 blocked-exit policy 由 22A 冻结；无法解析时 group outcome 不可评估。

### 11.3 Forward abnormal return

```text
forward_group_abnormal_return_g,t,H =
    forward_group_return_g,t,H
    - beta_market_g,t-1 * forward_rest_of_market_return_ex_g,t,H
    - eligible_checkpointed_control_component
```

必须使用 event 前冻结的 beta，不得用 outcome-window regression。

### 11.4 Path outcomes

按冻结的 daily mark 计算：

```text
MAE_H
MFE_H
realized_volatility_H
downside_tail_proxy_H
time_to_recovery_H
```

Recovery threshold 和 censoring 必须在 22A outcome registry 中冻结。未在 horizon 内恢复时输出 censored 状态，不得填 horizon+1
冒充精确恢复日。

### 11.5 Competing-mechanism labels

```text
continuation_flag =
    sign(group_reaction_residual_t)
    == sign(forward_group_abnormal_return_primary_H)

reversal_flag =
    sign(group_reaction_residual_t)
    != sign(forward_group_abnormal_return_primary_H)
```

零/tolerance 和非有限处理由 config 冻结。Labels 只存在于 S3 outcome bundle，禁止出现在 S0–S2。

### 11.6 Big Winner boundary

```text
big_winner_or_plus_50_group_outcome = forbidden
stock_big_winner_bridge = deferred_to_separate_L3_requirement
```

---

## 12. Statistics、multiplicity 与稳定性

### 12.1 Inference unit

Primary independent evidence unit 是 shock episode/date block，不是 group row。

至少同时报告：

- raw pair/group row N；
- distinct shock-date N；
- distinct episode N；
- effective independent block N；
- direction × event-type × fold support；
- evaluable group N 分布；
- missingness 与 denominator coverage。

### 12.2 Required estimates

每个 primary/secondary readout 至少发布：

```text
point_estimate
economic_unit
baseline_delta
standard_error_or_bootstrap_scale
nominal_interval
multiplicity_adjusted_interval_or_pvalue
effect_floor
directionally_correct_bound
distinct_date_n
distinct_episode_n
effective_block_n
```

### 12.3 Block inference

Exact method 来自 22A。最低要求：

- resample unit 不小于 episode/date block；
- 同一 date 的所有 groups 一起 resample；
- overlapping horizon 使用 purge/embargo、HAC 或 stationary/block bootstrap；
- bootstrap seed/repetitions 固定；
- 同一 episode 不跨 fold；
- cross-group top/bottom spread 按 date paired。

### 12.4 Multiplicity

Primary family 至少覆盖：

```text
positive versus negative market shock
positive versus negative group residual
continuation versus reversal
eligible primary event types
primary horizon
```

Secondary horizons、G4/G5、group families 和 sensitivity 进入各自冻结 family，使用 Holm、FDR 或更严格 correction。不得只报告
nominal p-value。

### 12.5 Stability

至少报告：

- chronological folds；
- calendar year；
- early/late；
- leave-one-year-out 或 leave-block-out；
- market state sensitivity；
- exchange-board versus eligible industry；
- shock direction；
- event type；
- pre/post major market-structure period；
- top-date/top-group influence。

### 12.6 Concentration guard

22A 必须冻结：

```text
maximum_top_date_contribution_share
maximum_top_episode_contribution_share
maximum_top_group_contribution_share
minimum_direction_support
minimum_fold_support
```

超过上限时 positive terminal 不允许；不得只删掉影响点后报告更好结果。

---

## 13. Gates 与 terminal state machine

### 13.1 Ordered gates

Gate 顺序固定：

```text
GATE_00_upstream_22A_integrity
GATE_01_exploration_scope_and_attempt_identity
GATE_02_source_and_PIT
GATE_02D_candidate_source_search_and_lineage
GATE_02E_candidate_source_contract_gain
GATE_03_construct_and_taxonomy
GATE_04_market_shock_magnitude_and_breadth
GATE_05_group_residual_formula
GATE_06_event_state_and_episode
GATE_07_minimum_effective_support
GATE_08_outcome_timing_and_materialization
GATE_09_G3_incremental_over_G2
GATE_09D_B1_incremental_data_value_over_B0
GATE_10_effect_floor_and_adjusted_inference
GATE_11_time_direction_scope_stability
GATE_12_concentration_guard
GATE_13_duplicate_research_guard
GATE_14_claim_ceiling_and_publication
```

早期 gate fail 后，后续需要 outcome 的 gate 不得伪造 `pass`，必须标为 `not_run_due_to_prior_gate_failure`。

### 13.2 Support/effect values

22B 不在同一 attempt 的 outcome 后决定以下值；必须逐字复制绑定的 22A/compatibility checkpoint：

```text
minimum_distinct_shock_dates
minimum_distinct_episodes
minimum_effective_blocks
minimum_years
minimum_direction_support
minimum_group_coverage
primary_effect_floor
G3_minus_G2_increment_floor
adjusted_confidence_bound_rule
stability_tolerance
concentration_limits
```

22A 未冻结任一值时：

```text
GATE_07_or_10 = blocked
terminal_state = component_run_incomplete_working
```

不得由 22B 补猜。

### 13.3 Arm status

每个 arm 一个状态：

```text
exploration_ready_and_evaluable
exploration_ready_but_low_power
data_blocked
construct_blocked
deferred_out_of_scope
not_run_due_to_prior_gate_failure
completed
```

不得用 exchange-board arm 通过掩盖 industry arm 阻断，反之亦然。

每个 candidate-source augmented arm 还必须输出独立 `empirical_value_state`。B1 无增量不等于 M1 被证伪；它只说明该 source 在当前
合同下没有增加研究价值。反之，B1 改变 B0 结论时，必须报告 `source_changes_or_falsifies_prior_interpretation`，不能只保留更漂亮
的一侧。

### 13.4 Terminal-state truth table

按优先级裁决一个 module terminal：

```text
if run incomplete or working snapshot not validated:
    component_run_incomplete_working

elif required source/PIT unavailable:
    component_data_blocked

elif event/group construct invalid:
    component_construct_invalid

elif duplicate guard triggered:
    component_duplicate_research_closed

elif effective support below frozen floor:
    component_not_evaluable_low_power

elif adequate power and primary direction/incremental gate fails:
    component_historically_falsified

elif direction positive but stability/concentration gate fails:
    component_measurable_but_historically_unstable

elif all proxy-only positive gates pass:
    component_proxy_only_historically_informative
```

`component_directly_measurable_historically_stable` 对本 price-shock-only contract 非法。

### 13.5 Forward-freeze eligibility

只有 `component_proxy_only_historically_informative` 可进入：

```text
forward_freeze_candidate = review_required
```

仍不得自动创建 forward registry、运行 forward cohort 或形成 support。

---

## 14. Required artifacts 与 schema

### 14.1 Preoutcome bundle

```text
preoutcome/contract_resolution.json
preoutcome/upstream_22a_integrity_audit.csv
preoutcome/input_artifact_audit.csv
preoutcome/access_audit.csv
preoutcome/source_and_timestamp_audit.csv
preoutcome/data_gap_and_candidate_source_registry.csv
preoutcome/source_discovery_and_acquisition_attempt_log.csv
preoutcome/candidate_source_pit_and_coverage_audit.csv
preoutcome/source_contract_gain_readout.csv
preoutcome/source_augmented_arm_registry.csv
preoutcome/arm_readiness_registry.csv
preoutcome/group_taxonomy_registry.csv
preoutcome/group_membership_and_weight_pit_audit.csv
preoutcome/shock_formula_registry.csv
preoutcome/group_expected_response_formula_registry.csv
preoutcome/baseline_registry.csv
preoutcome/outcome_registry_without_values.csv
preoutcome/multiplicity_and_gate_registry.csv
preoutcome/market_shock_date_census.csv.gz
preoutcome/market_group_pair_state_panel.csv.gz
preoutcome/market_group_shock_episode_census.csv.gz
preoutcome/group_reaction_asof_panel.parquet
preoutcome/formula_replay_audit.csv
preoutcome/preoutcome_manifest.json
preoutcome/preoutcome_output_hashes.csv
```

### 14.2 Historical outcome bundle

```text
historical/group_forward_outcome_panel.parquet
historical/outcome_resolution_audit.csv
historical/path_outcome_panel.parquet
historical/continuation_reversal_panel.csv.gz
historical/historical_manifest.json
historical/historical_output_hashes.csv
```

### 14.3 Inference/final bundle

```text
analysis/group_baseline_comparison.csv
analysis/model_fold_audit.csv
analysis/event_type_direction_readout.csv
analysis/fold_year_stability_readout.csv
analysis/concentration_and_influence_audit.csv
analysis/multiplicity_adjusted_inference.csv
analysis/duplicate_research_comparator_audit.csv
analysis/source_incremental_empirical_value_readout.csv
analysis/source_search_and_multiplicity_accounting.csv
analysis/gate_results.csv
analysis/arm_terminal_states.csv
decision/22B_M1_terminal_decision.json
reports/22B_observable_shock_abnormal_reaction_market_validation_report.md
stage_status_registry.csv
manifest.json
output_hashes.csv
checkpoint_receipt.json
```

### 14.4 Input/upstream audit schema

```text
artifact_id
artifact_path
artifact_role
expected_sha256
observed_sha256
expected_schema_version
observed_schema_version
eligible_by_22A_or_compatibility_checkpoint
stage_read_allowed
status
blocking_reason
```

### 14.5 Group taxonomy registry schema

```text
group_family_id
group_id
group_name
group_type
return_source_mode
index_alias_or_null
membership_source_or_null
membership_availability_semantics
weighting_mode
weight_availability_semantics
return_arm_status
internal_structure_arm_status
claim_ceiling
readiness_source_row_key
```

唯一键：`group_family_id + group_id`。

### 14.6 Market shock date census schema

```text
shock_date
market_shock_key
benchmark_alias
market_return
market_center_t_minus_1
market_scale_t_minus_1
market_shock_z
shock_direction
shock_policy_id
absolute_floor_pass
market_magnitude_pass
group_breadth_value
group_breadth_denominator
instrument_breadth_value
instrument_breadth_denominator
market_breadth_pass
market_common_shock
index_concentrated_or_group_led_move
feature_cutoff
first_usable_time
fold_id
sample_role
row_status
non_evaluable_reason
```

唯一键：`market_shock_key`。

### 14.7 Market/group pair-state schema

```text
group_pair_key
market_shock_key
shock_date
group_family_id
group_id
observed_group_return
rest_of_market_return_ex_group
rest_of_market_status
expected_group_return
group_reaction_residual
group_residual_scale_t_minus_1
group_shock_z
group_specific_shock
market_common_shock
pair_state
date_state
style_cluster_status
benchmark_contamination_status
feature_cutoff
first_usable_time
fold_id
sample_role
row_status
non_evaluable_reason
```

唯一键：`group_pair_key`。

### 14.8 Episode schema

```text
episode_key
episode_scope
scope_id
episode_start_date
episode_last_update_date
episode_end_date_or_null
episode_status
first_trigger_type
current_online_state
propagation_update_state
member_shock_key
member_group_pair_key_or_null
fold_id
sample_role
```

`member_shock_key/member_group_pair_key` 可形成多行 membership；唯一键为
`episode_key + member_shock_key + member_group_pair_key_or_null`。

### 14.9 Group reaction as-of schema

```text
group_pair_key
event_id
episode_key
shock_date
group_family_id
group_id
group_type
group_membership_status
registered_constituent_n
evaluable_constituent_n
observed_group_return
rest_of_market_return_ex_group
expected_group_return
group_reaction_residual
group_shock_z
group_direction_breadth
group_residual_breadth
group_dispersion
group_amount_anomaly
group_turnover_anomaly
group_liquidity_change
leader_concentration
limit_up_share
limit_down_share
suspension_share
internal_structure_status
feature_cutoff
first_usable_time
fold_id
sample_role
asof_feature_semantic_sha256
```

不得包含任何 forward 字段。

### 14.10 Forward outcome schema

```text
outcome_key
group_pair_key
episode_key
group_family_id
group_id
first_usable_time
horizon_sessions
outcome_semantics
entry_price_or_index_level
exit_price_or_index_level
forward_group_return
forward_rest_of_market_return
forward_group_abnormal_return
mae
mfe
realized_volatility
downside_tail_proxy
time_to_recovery
recovery_censor_status
continuation_flag
reversal_flag
outcome_status
non_evaluable_reason
```

唯一键：`outcome_key`。

### 14.11 Model fold audit schema

```text
model_fold_key
arm_id
fold_id
train_sample_role
evaluation_sample_role
train_distinct_episode_n
evaluation_distinct_episode_n
feature_set_id
ordered_feature_names
scaler_state_semantic_sha256
design_rank
design_condition_status
solver_id
coefficient_vector_semantic_sha256
residual_term_coefficient
oof_prediction_semantic_sha256
oof_loss_metric_id
oof_loss_value
economic_association_metric_id
economic_association_value
fold_status
blocking_reason
```

唯一键：`model_fold_key`。不得只保存 prediction 而不保存可复核的 scaler/design/coefficient identity。

### 14.12 Baseline comparison schema

```text
comparison_key
estimand_id
event_type
shock_direction
group_family_id
horizon_sessions
baseline_left
baseline_right
common_denominator_pair_n
distinct_date_n
distinct_episode_n
effective_block_n
left_effect
right_effect
incremental_delta
effect_floor
nominal_interval_lower
nominal_interval_upper
adjusted_interval_lower
adjusted_interval_upper
adjusted_pvalue
direction_gate
incremental_gate
denominator_comparability_status
```

### 14.13 Gate schema

```text
gate_order
gate_id
gate_scope
required
evaluated
metric_name
observed_value
threshold_operator
threshold_value
status
blocking_reason
source_artifact
source_row_key
```

### 14.14 Terminal decision schema

```json
{
  "schema_version": "S_22B_M1_TERMINAL_DECISION_V0",
  "run_id": "22B_observable_shock_abnormal_reaction_market_validation_v0",
  "contract_version": "22B_M1_v0",
  "attempt_id": "",
  "snapshot_state": "working",
  "provisional": true,
  "module_id": "M1",
  "primary_group_family": "",
  "primary_event_family": "",
  "primary_horizon_sessions": 0,
  "terminal_state": "component_run_incomplete_working",
  "arm_states": {},
  "gates": {},
  "claim_ceiling": "price_shock_proxy_only",
  "exploratory_historical_support_claim_allowed": true,
  "confirmatory_support_claim_allowed": false,
  "forward_freeze_candidate": "not_eligible",
  "L3_stock_authorized": false,
  "decision_router_authorized": false,
  "deployment_authorized": false
}
```

只有通过 post-run validation 的 attempt 才可标记 `snapshot_state = validated_working_result` 并输出完整 terminal。未完成 attempt 的
terminal 必须为 `component_run_incomplete_working`。普通 EP22 历史探索不要求 `sealed=true`。

---

## 15. Report contract

中文报告至少按以下顺序：

1. 结论摘要与 terminal state；
2. 研究对象、不可声称内容与 historical evidence role；
3. 22A/compatibility source、PIT 与 arm readiness；
4. data-gap、candidate-source 搜索/试采、访问成本与失败记录；
5. B0 existing-data baseline 与 B1+ augmented arm 的 contract gain；
6. market shock magnitude + breadth 定义；
7. group expected response 与 residual 定义；
8. pair/date state 与 online episode；
9. 数据覆盖、denominator 和 effective support；
10. G0–G5 primary baseline comparison；
11. B1+ 相对 B0 的 paired empirical data-value comparison；
12. pure market/group-only/amplification/resistance readout；
13. continuation 与 reversal competing mechanisms；
14. fold/year/direction/group-family 稳定性；
15. concentration、influence、duplicate comparator 与 source-search multiplicity；
16. arm-level blocked/construct/source-value caveat；
17. gate replay、terminal state 与 allowed claim；
18. 下一步是 stop、继续补数、data repair 或 forward-freeze review。

报告必须逐字包含：

```text
22B 只识别 observable market/group price shock 及其 group-level reaction residual；没有 timestamped semantic event、当时市场共识和 expected magnitude，因此不能把 residual 称为已识别的过度或不足定价。

所有 historical 结果都是 design-contaminated historical real-market evidence。它们可以在冻结口径下支持、削弱或证伪 M1，
也可以形成 forward-freeze candidate，但不能形成 true OOS、forward support、可部署行业轮动策略或个股交易授权。

同一 shock-date 下的 group rows 不是独立证据。统计推断、sample floor 与稳定性以 shock episode/date block 为核心。

只有行业指数收益而没有 PIT membership 时，行业内部 breadth、dispersion、leader concentration 与成分确认均不可评估；本报告没有使用 current industry 回填历史。

G3 不优于 G2 时，G4/G5 的结果只能用于失败诊断，不能挽救 group reaction residual 的 primary claim。
```

若 industry arm blocked，必须在摘要中明确，不能只放 appendix。

---

## 16. Manifest、hash 与 iterative checkpoint publication

### 16.1 Canonical serialization

- JSON：UTF-8、sorted keys、2-space indent、末尾 LF、禁止 NaN/Infinity；
- CSV：UTF-8、LF、冻结列顺序、float `%.12g`、空值为空字符串；
- gzip：`compresslevel=9`、`mtime=0`；
- Parquet：pyarrow + zstd、冻结列顺序与 schema metadata；
- 所有 datetime 使用明确 timezone 或 canonical date，不得混用 naive timestamp；
- semantic hash 必须基于 canonical key-sorted logical records，不依赖文件压缩字节。

### 16.2 Hash closure

为避免 self-hash cycle：

```text
output_hashes.csv:
    hashes every substantive artifact except
    output_hashes.csv, manifest.json, checkpoint_receipt.json

manifest.json:
    records output_hashes.csv sha256 and bundle semantic sha256
    does not record its own byte hash

checkpoint_receipt.json:
    records manifest.json sha256 and output_hashes.csv sha256
    excluded from output_hashes.csv
```

`output_hashes.csv` 字段：

```text
relative_path
artifact_role
byte_sha256
semantic_sha256_or_blank
row_count_or_blank
schema_version
```

### 16.3 Artifact universe

Manifest 必须列出 exact allowed relative paths。Staging root 中出现未注册文件、`__pycache__`、临时文件、日志、notebook checkpoint
或额外 report 时 validation fail。

### 16.4 Iterative checkpoint publication

```text
working
  -> checkpointed
  -> preoutcome_checked
  -> historical_outcome_complete
  -> diagnostic_complete
  -> validated_working_result
  -> optional_formal_freeze
```

每个 attempt 写入 `output_root/attempts/<attempt_id>.working`；内部校验通过后原子更新 attempt 状态并移动 `latest.json`。working
attempt 可修复，checkpointed attempt 的语义变化使用新 attempt。已存在 formally frozen/sealed bundle 时不得覆盖。

---

## 17. Test 与 validation contract

### 17.1 Unit tests

至少覆盖：

1. market return/center/scale 只用 `<= t-1`；
2. `1%` floor 为 null/启用时的精确边界；
3. magnitude pass 但 breadth fail 进入 index-concentrated state；
4. market breadth denominator/missingness；
5. rest-of-market 正确剔除 target group；
6. expected-response coefficient 不读取 `t`；
7. zero/non-finite residual scale fail closed；
8. 五类 pair state truth table；
9. date-level state 互斥；
10. multi-group residual 触发 style/common guard；
11. online episode 不被 future propagation 回写；
12. same episode 不跨 fold；
13. official-index-only industry arm 的 internal fields structural missing；
14. current-industry backfill 被拒绝；
15. self-built membership/weights 只用 `<= t-1`；
16. stock residual 只可聚合，不能输出 stock outcome；
17. G2/G3/G4/G5 design matrix 严格 nested；
18. scaler/coefficients 只在 train/expanding-past 拟合；
19. validation/robustness 不参与 hyperparameter 或 orientation；
20. singular design 按冻结 policy fail closed；
21. G3/G4/G5 common-denominator attribution；
22. G3 fail 时 G4/G5 rescue 被拒绝；
23. G4/G5 block joint test 不挑单字段；
24. first usable time 为 next executable open；
25. outcome-window beta refit 被拒绝；
26. continuation/reversal labels 只出现在 S3；
27. shock threshold/event membership 与 22A semantic hash 一致；
28. date/episode block bootstrap 同步 resample groups；
29. terminal-state truth table；
30. manifest/output-hash/checkpoint-receipt 无自循环；
31. artifact-universe extra file fail；
32. public read-only source cache 保留 endpoint/query/time/raw hash；
33. credential/payment source 被正确阻断；
34. B0/B1 common-denominator pairing；
35. source-search multiplicity accounting；
36. source coverage gain 不会自动变成 empirical-value pass；
37. B1 改写 B0 结论时两侧均保留。

### 17.2 Synthetic integration tests

必须构造确定性小样本：

- broad market shock：指数越线且多数 group/stock 同向；
- index-concentrated move：指数越线但 breadth 不通过；
- pure group shock：市场不越线、单行业 residual 越线；
- amplification：市场与 group residual 同向越线；
- resistance：市场与 group residual 反向越线；
- industry-led spillover：`t` group-only、`t+1` market shock；
- delayed group amplification：`t` market、`t+1` group；
- official-index-only industry：return 可算、internal structure 禁止；
- insufficient support：正确落入 low-power terminal；
- duplicate comparator：正确落入 duplicate terminal。
- candidate source：PIT/coverage 通过但无 empirical increment；
- candidate source：扩大 universe 后改变 B0 结论；
- credential-required source：不访问并登记 blocked state。

每个 fixture 必须断言 stable keys、row counts、event/date states、fold、hash 与 terminal state。

### 17.3 Real-data validation

实现后可直接运行：

```bash
python -m pytest \
  topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/tests/test_22b_observable_shock_abnormal_reaction_market_validation.py \
  -q

python topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/src/run_22b_observable_shock_abnormal_reaction_market_validation.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/configs/config_22b_observable_shock_abnormal_reaction_market_validation.yaml \
  --stage preoutcome

python topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/src/run_22b_observable_shock_abnormal_reaction_market_validation.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/configs/config_22b_observable_shock_abnormal_reaction_market_validation.yaml \
  --stage historical-outcome

python topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/src/run_22b_observable_shock_abnormal_reaction_market_validation.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/configs/config_22b_observable_shock_abnormal_reaction_market_validation.yaml \
  --stage finalize

python topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/src/run_22b_observable_shock_abnormal_reaction_market_validation.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/configs/config_22b_observable_shock_abnormal_reaction_market_validation.yaml \
  --validate-only
```

`historical-outcome` 命令没有通过内部校验且 hash 匹配的 S2 checkpoint 时必须失败。通过后可自动继续，不等待人工授权。

### 17.4 Static checks

```bash
git diff --check
```

另外必须检查：

- Markdown code fences 平衡；
- requirement/config/manifest identity 一致；
- schema required columns 与 actual columns 一致；
- stable-key uniqueness；
- preoutcome bundle 不含 outcome/proxy 字段；
- event/episode membership 与 22A semantic hash 一致；
- output artifact universe 完整且无额外文件；
- report headline、gate CSV 与 terminal JSON 一致；
- output hash closure 可复算。

---

## 18. Definition of Done

Requirement generation 完成条件：

- [x] requirement 文件创建；
- [x] 与 research plan 的 group-first M1、market/group shock 分类和 PIT 边界一致；
- [x] 明确 22A/compatibility checkpoint 是科学基线而不是人工授权闸门；
- [x] 输入、公式、时钟、state、episode、baseline、outcome、gate、terminal、schema、test 已落盘；
- [x] L3 个股不在 22B scope；策略、部署与 live trading 仍禁止。

未来 exploratory implementation 完成条件：

- [ ] 22A validated working snapshot 或 local compatibility checkpoint 完整；
- [ ] config 逐值绑定 22A registry/hash；
- [ ] runner/tests 实现且 unit/synthetic tests 通过；
- [ ] S0–S2 preoutcome checkpoint 完成内部 PIT/schema/hash validation；
- [ ] S3 自动转换精确绑定 S2 hash；
- [ ] S3 historical outcome 完整；
- [ ] G0–G5、inference、stability、concentration、duplicate guard 完整；
- [ ] material data gaps 有 candidate-source 搜索与 acquisition accounting；
- [ ] B0 existing-data baseline 与 B1+ augmented arms 独立保留；
- [ ] source contract gain 与 empirical gain 分开；
- [ ] source/provider/taxonomy/universe variants 进入 multiplicity accounting；
- [ ] 每个 arm 有独立状态；
- [ ] module terminal 唯一且符合 truth table；
- [ ] 中文报告与 machine decision 一致；
- [ ] manifest/hash/artifact-universe validation 通过；
- [ ] attempt 标为 validated working result，或诚实保留 incomplete。

---

## 19. Requirement review checklist

- [ ] 是否仍误把 group 当作个股 expected-response 控制项，而不是 primary reaction unit？
- [ ] 是否明确 market shock 必须 magnitude + frozen breadth，而非单指数越线？
- [ ] 是否明确 industry shock 是 market-adjusted residual shock，而非原始行业涨跌？
- [ ] 是否区分 pair state 与 date-level state？
- [ ] 是否把 market-only、group-only、amplification、resistance、index-concentrated 状态互斥实现？
- [ ] 是否防止大权重 group 机械污染 market benchmark？
- [ ] 是否区分 official-industry-return arm 与 PIT-membership internal-structure arm？
- [ ] 是否禁止 current industry/concept backfill？
- [ ] 是否冻结 close `t` / next executable open 时钟？
- [ ] 是否把 as-of 与 forward outcome 物理分表并按内部 checkpoint 分阶段？
- [ ] 是否禁止 future path 定义 shock、state 或 episode？
- [ ] 是否以 episode/date block 而不是 group row 做 inference？
- [ ] 是否固定 G3 versus G2 为 primary incremental test？
- [ ] 是否禁止 G4/G5 挽救 G3 failure？
- [ ] 是否在当前 group universe 重建 EP20B-SRC-like comparator？
- [ ] 是否将 continuation/reversal 作为 competing mechanisms 而非事后叙事？
- [ ] 是否按 22A 冻结 sample/effect/stability/multiplicity values？
- [ ] 是否把现有 PIT universe 当作 B0 baseline 而不是数据上限？
- [ ] 是否为新增 source 发布 B0/B1 paired comparison？
- [ ] 是否区分 source 可访问、PIT 可重建、coverage gain、construct gain 与 empirical value？
- [ ] 是否完整记录 source/provider/taxonomy/universe search family？
- [ ] 是否保留 arm-level blocked 状态，不用可运行 arm 掩盖？
- [ ] 是否强制 proxy-only claim ceiling？
- [ ] 是否禁止 L3 stock ranking/outcome/action？
- [ ] 是否避免 manifest/self-hash cycle？
- [ ] 是否明确 exploration readiness 不等于 historical support、forward support 或 production authorization？

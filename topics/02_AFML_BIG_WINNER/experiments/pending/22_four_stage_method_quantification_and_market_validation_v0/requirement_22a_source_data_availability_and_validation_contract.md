# Requirement 22A：Source、Data Availability、PIT Timing 与 Validation Contract

## 0. 不可协商范围

22A 是 EP22 的共同 preoutcome contract。它只回答：

> practitioner narrative 中哪些 statement 可以被转换成可观测、PIT-valid、可证伪的模块命题；本地或明确提供的数据能否支持这些
> 命题；后续单模块验证必须使用什么时点、denominator、estimand、baseline、split、multiplicity、power、stability 和 claim ceiling。

22A 不验证 M1–M6 的历史 outcome，不判断哪个组件“有效”，也不建设完整四阶段决策路由。

22A 允许：

- 登记来源 statement、testable hypothesis、direct measurement、proxy 和不可测 construct；
- 审计本地 source、field、coverage、schema、timestamp、PIT lineage 和 hash；
- 建立 data-gap registry，主动发现、试采、缓存并 profile 无需新凭据或付费的公开 read-only 数据；
- 比较 existing-data baseline 与 candidate-source augmented contract 的 construct、coverage 和 effective-support 增量；
- outcome-blind 地构造 M1 市场/group shock census、online episode 与 group reaction as-of panel；
- 仅根据 source、coverage、missingness、maturity 和 effective-support geometry 冻结候选公式、阈值、primary horizon 与统计合同；
- 冻结所有模块的 primary/secondary metric、baseline、split、purge、embargo、multiplicity、effect floor、MDE 和 stability gate；
- 对 M1、M2、M3A、M3B、M4、M5、M6A、M6B 分别给出数据与 construct 状态；
- 形成一个 22A terminal state，并保存可供后续 requirement 绑定的可复现 working checkpoint。

22A 禁止：

- 读取、生成或推导任何模块的 forward return、future distribution、MAE、MFE、recovery、future risk、future label 或策略收益；
- 用 future outcome 选择 source、threshold、horizon、feature、state 数、bucket、baseline、effect floor 或 module；
- 把 OHLCV 写成投资者身份、主力、机构、情绪真值、持仓真值或 capital-flow accounting identity；
- 用 current industry、current concept/theme 或 2025 taxonomy 回填历史；
- 把 official industry-index return source 等同于 PIT constituent membership；
- 把 total shares、listed circulating shares 或成交额自动解释成 official free float、资金净流入或真实 capacity；
- 从 EP21 `.building`、不明 lineage 的 working bundle、报告文字或下游 22B–22G outcome 反推输入；
- 生成跨模块 score、action、position sizing、portfolio optimization、policy replay、回测、部署或实盘建议；
- 把 research readiness 解释成历史有效、forward support 或生产授权。

固定治理语义：

```text
phase_id = 22A
evidence_role = preoutcome_source_data_and_validation_contract
historical_market_data_role = design_contaminated_historical_real_market_evidence
outcome_read_allowed = false
module_effect_estimation_allowed = false
historical_support_claim_allowed = false
forward_support_claim_allowed = false
cross_module_combination_authorized = false
decision_router_authorized = false
position_sizing_authorized = false
portfolio_backtest_authorized = false
deployment_authorized = false
live_trading_authorized = false
routine_local_implementation_allowed = true
routine_22A_execution_allowed = true
public_read_only_data_discovery_allowed = true
public_read_only_download_and_cache_allowed = true
per_stage_human_authorization_required = false
mandatory_intermediate_seal = false
```

22A 的四个互斥 terminal states 固定为：

```text
22A_contract_ready_for_selected_component_validation
22A_partial_data_ready_with_blocked_modules
22A_all_material_modules_data_blocked
22A_pit_or_construct_contract_blocked
```

本文的 `freeze/frozen` 默认表示“在当前 attempt 内固定，防止 outcome 后选择”，不是人工授权或 immutable seal。只有
`formal_forward_freeze` 才表示跨 attempt 的正式不可变合同。

本文的 `data_blocked` 默认是 source/arm-level 状态。只有 material gap 的公开 source-search budget 已完成，或 source 明确需要
尚未批准的凭据、付费或许可时，才可裁决 module-level `component_data_blocked`。

---

## 1. 身份、文件与探索执行模式

```text
experiment_id = 22_four_stage_method_quantification_and_market_validation_v0
phase_id = 22A
run_id = 22A_source_data_availability_and_validation_contract_v0
contract_version = 22A_common_contract_v0
requirement_status = exploration_specification_ready
requirement_file = requirement_22a_source_data_availability_and_validation_contract.md
research_plan_file = research_plan.md
config_file = configs/config_22a_source_data_availability_and_validation_contract.yaml
runner_file = src/run_22a_source_data_availability_and_validation_contract.py
test_file = tests/test_22a_source_data_availability_and_validation_contract.py
output_root = outputs/22A_source_data_availability_and_validation_contract_v0
```

探索执行模式：

```text
requirement_revision_allowed = true
local_implementation_allowed = true
local_22A_execution_allowed = true
local_historical_exploration_allowed = true
variant_iteration_allowed = true
per_stage_human_authorization_required = false
public_read_only_data_discovery_allowed = true
public_read_only_download_and_cache_allowed = true
external_side_effect_or_paid_data_acquisition_allowed = false
formal_forward_freeze_allowed = false
production_or_live_execution_allowed = false
```

在 EP22 已定义的数据探究范围内，可以直接创建或修订 config、runner、tests，运行本地 22A，并发现、下载、缓存、profile
无需新凭据或付费的公开 read-only 数据，无需逐阶段人工授权。每次尝试必须记录 requirement/config/code/input identity、
source URL/API identity、retrieval time、license note 与 search-path lineage。若动作扩展到修改外部系统、付费或新凭据数据、
正式 forward freeze、生产部署、live trading 或破坏既有 sealed bundle，仍需另行明确授权。

执行工作目录：

```bash
cd topics/02_AFML_BIG_WINNER
```

所有路径必须是 repository-relative path 或从 config 中的 alias 解析。实现不得硬编码 `/home/xiaolv/...`。

working output 可以在保留 checkpoint/change log 的前提下原位修复和重跑；既有 formally frozen 或 sealed bundle 不得覆盖。
以下任一变化都必须增加 `attempt_id`，若语义不兼容则增加 contract version：

- source/field/timestamp 语义；
- universe、benchmark、group taxonomy、membership 或 weighting；
- M1 shock、expected-response、residual、episode 或 as-of panel 公式；
- module estimand、primary outcome、horizon、baseline 或 inference unit；
- split、purge、embargo、multiplicity、effect floor、MDE、support 或 stability gate；
- readiness enum、claim ceiling、terminal mapping；
- output schema、canonical serialization 或 hash closure。

### 1.1 Future config contract

未来 config 至少包含：

```text
identity:
    experiment_id, phase_id, run_id, contract_version

paths:
    requirement_file, research_plan_file,
    project_universe_file, benchmark_file, benchmark_source_audit_file,
    trading_calendar_file, security_master_file, cache_manifest_file,
    raw_daily_root, qfq_daily_root, share_history_root,
    candidate_external_source_roots, output_root

boundary:
    requested_history_start, requested_history_end,
    canonical_calendar_alias, evidence_role

source_audit:
    allowed_source_types, forbidden_path_patterns,
    required_hash_algorithm, directory_snapshot_policy,
    schema_probe_row_limit

data_discovery:
    gap_registry, candidate_source_registry,
    public_read_only_acquisition_policy,
    credential_and_payment_policy,
    retrieval_cache_root, request_rate_limit,
    source_search_budget, source_attempt_budget_per_gap,
    license_note_policy, raw_response_hash_policy,
    baseline_vs_augmented_pairing_policy

timing:
    feature_cutoff, default_first_usable_time,
    timestamp_precedence, unknown_timestamp_policy

module_registry:
    required_module_ids = [M1,M2,M3A,M3B,M4,M5,M6A,M6B]

m1:
    every candidate and selection rule in Sections 9–12

split:
    every value in Section 8

statistics:
    every value in Sections 7–8

serialization:
    json_allow_nan=false, csv_float_format="%.12g",
    csv_encoding=utf-8, csv_line_ending=LF,
    parquet_engine=pyarrow, parquet_compression=zstd,
    gzip_compresslevel=9, gzip_mtime=0
```

Unknown key、缺失 key、CLI 未记录覆盖冻结值或 requirement/config 不一致必须 fail closed。合法探索 variant 必须写入新
`attempt_id` 和 search-accounting registry，不能通过隐藏 CLI override 产生。

---

## 2. 研究问题

22A 只回答 preoutcome questions：

```text
Q1. 每条 source statement 的证据身份是什么，能否转写成可证伪 hypothesis？

Q2. 每个 hypothesis 所需 field 是 direct measurement、proxy、
    deferred policy construct、data-blocked 还是 construct-invalid？

Q3. 每个 source/field 的 observation、publication、availability、
    revision、first-market-usable timestamp 能否证明？

Q4. 当前本地数据的 date、instrument、event、group、report-vintage、
    calendar 和 missingness coverage 能否支持最低限度的 component validation？

Q5. M1 的 market shock、group taxonomy、group return、membership、
    weight、expected response、residual shock、episode 和 as-of panel
    能否在不连接 future outcome 的情况下被完整重建并 checkpoint？

Q6. 每个 module 的 primary estimand、outcome semantics、horizon、
    baseline、inference unit、split、multiplicity 和 claim ceiling 是什么？

Q7. 每个 module 的 minimum effective support、economic floor/MDE、
    adjusted-bound、stability 与 concentration gate 如何在 outcome 前冻结？

Q8. 哪些 module/arm exploration-ready，哪些必须 data-blocked、
    construct-blocked、low-power 或 deferred？

Q9. stable snapshot 与 working output 如何区分；后续阶段如何读取带版本、hash 与 provisional 标记的 artifacts？

Q10. 22A 完成后最多允许说什么，哪些结论必须等单模块 historical validation
     或真实 forward cohort？

Q11. 每个 blocked/weak-proxy construct 有哪些候选公开、vendor 或用户可提供 source？

Q12. 候选 source 的访问条件、许可、字段、覆盖、timestamp、revision 和 PIT
     reconstructability 是什么？

Q13. 候选 source 相对 existing-data baseline 是否改善 construct fidelity、
     universe scope、denominator coverage、event count 或 effective support？

Q14. 哪些 source 值得进入 module-specific B0/B1 empirical-value attempt，
     哪些应判为 unavailable、non-PIT、redundant 或 low-value？
```

22A 不回答：

- M1 abnormal reaction 是否预测未来；
- M2 state 是否区分未来市场分布；
- M3 supply/demand event 是否有市场效应；
- M4 style relation 是否稳定；
- M5 quality/value 是否有长期收益；
- M6 primitive 是否校准、hedge 是否有效；
- 任一 component 是否可交易；
- 多个 component 是否应组合。

---

## 3. Staged exploration 与 outcome separation

22A 必须按以下 stage 运行：

```text
S0_contract_resolution
S1_source_and_timestamp_inventory
S1D_data_gap_and_candidate_source_discovery
S2D_public_read_only_source_acquisition_and_pit_profile
S2_construct_estimand_and_claim_freeze
S3_outcome_blind_support_preflight
S4_m1_preoutcome_census_and_asof_checkpoint
S5_module_readiness_and_terminal_decision
S6_post_run_validation_and_working_snapshot
```

状态只能单向推进：

```text
working
  -> contract_resolved
  -> source_audit_complete
  -> candidate_source_profile_complete
  -> preoutcome_support_complete
  -> decision_complete
  -> checkpointed
  -> validated_working_result
```

中断时：

```text
status = working_or_incomplete
checkpoint_status = incomplete
terminal_state = 22A_pit_or_construct_contract_blocked
downstream_read_allowed = provisional_only_if_required_rows_are_complete
```

S0–S6 是科学计算顺序，不是人工批准关卡。同一次本地探索 run 可以在内部 schema/PIT/integrity check 通过后自动连续执行。

### 3.1 Stage read whitelist

| Stage | 可读内容 | 禁止内容 |
|---|---|---|
| S0 | requirement、research plan、config | 任何 market data 与 downstream output |
| S1 | whitelist 中的 source metadata、schema、timestamps、hash、coverage | 任何 forward-derived column |
| S1D | public documentation、API schema、license/access metadata、candidate-source samples | module outcome 与未来标签 |
| S2D | 无需新凭据/付费的 public read-only payload；用户已提供的数据 | event-aligned future outcome；外部系统写操作 |
| S2 | S1 audit 与 research plan | realized future outcome、module effect |
| S3 | calendar、source availability、row/date/group/event maturity geometry | realized outcome values |
| S4 | 当期/滞后 benchmark、PIT universe、group membership/weight、当期 OHLCV | shock 后收益、future path、future label |
| S5 | S0–S4 产物 | 22B–22G outcome |
| S6 | 本次 working snapshot | 新市场计算 |

### 3.2 Forbidden paths and columns

实现必须在读取前扫描 path/columns。至少以下 path pattern 默认禁止：

```text
**/22B_*/historical/**
**/22B_*/analysis/**
**/22C_*/historical/**
**/22D_*/historical/**
**/22E_*/historical/**
**/22F_*/historical/**
**/22G_*/historical/**
**/*.building/**
```

至少以下列名 pattern 默认禁止进入 22A：

```text
forward_*
future_*
label_*
target_*
mae*
mfe*
recovery*
winner*
payoff*
pnl*
strategy_return*
oracle*
```

`source_claim_registry` 中的自然语言出现这些词不触发 column guard；只有数据字段触发。确需读取文件以确认它是 working/stable
状态时，只能读取 manifest/status，不得读取 payload。

### 3.3 Access audit

每次文件访问都写入：

```text
access_audit.csv
```

至少包含：

```text
access_seq
stage_id
artifact_path
artifact_role
read_scope
observed_sha256_or_directory_snapshot_sha256
allowed
authorization_basis
contains_forbidden_column
status
blocking_reason
```

`authorization_basis` 在 EP22 中表示 scope/read-policy basis，不是人工签字。任一超出 stage whitelist 的 payload read 发生后，
本 attempt 必须标记 `invalid_due_to_access_scope_violation`，修复后以新 attempt 重跑；不要求等待人工批准。

---

## 4. Path aliases 与候选输入

路径 alias：

```text
REPO_ROOT = ../../..
TOPIC_ROOT = .
EXPERIMENT_ROOT = experiments/pending/22_four_stage_method_quantification_and_market_validation_v0

DATA_ROOT = data
PROJECT_UNIVERSE_ROOT = data/processed/universe
INDEX_ROOT = data/processed/index
RAW_AKSHARE_ROOT = data/raw/akshare
RAW_DAILY_ROOT = data/raw/akshare/day/raw
QFQ_DAILY_ROOT = data/raw/akshare/day/qfq
SHARE_HISTORY_ROOT = data/raw/akshare/market_cap
STATUS_ROOT = data/raw/akshare/status
EXTERNAL_ROOT = data/external

SOURCE_EP05_ROOT = experiments/pending/05_pit_topn_400_100_universe_v0
SOURCE_EP19_ROOT = experiments/pending/19_entry_universe_pit_tradability_preflight
SOURCE_EP20_ROOT = experiments/pending/20_ohlcv_positive_beta_exposure_research
SOURCE_EP21_ROOT = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0
```

计划时已观察到但必须由 22A 重新审计的候选：

```text
PROJECT_UNIVERSE_ROOT/pit_topn_400_100_executable_daily.csv
PROJECT_UNIVERSE_ROOT/pit_topn_400_100_membership_daily.csv
PROJECT_UNIVERSE_ROOT/pit_topn_400_100_intervals.csv
INDEX_ROOT/benchmark_indices_daily.csv
INDEX_ROOT/benchmark_indices_source_audit.csv
STATUS_ROOT/trading_calendar.csv
STATUS_ROOT/instrument_metadata_target_universe.csv
RAW_AKSHARE_ROOT/cache_manifest.csv
RAW_DAILY_ROOT/*.csv
QFQ_DAILY_ROOT/*.csv
SHARE_HISTORY_ROOT/*_shares.csv
SOURCE_EP05_ROOT/outputs/manifests/run_manifest.json
```

这些路径在 requirement 生成时的存在性不是运行时 authority。22A 必须重新：

- resolve canonical path；
- 检查 file type、size、schema、row count、date min/max；
- 计算 SHA256；
- 验证 stable key uniqueness；
- 验证 source audit 与 payload 一致；
- 验证 availability semantics；
- 标记 formally_frozen/versioned_working/external；
- 记录是否允许用于 construct、support、downstream outcome。

### 4.1 Candidate source roles

| source_id | 候选用途 | 初始 ceiling |
|---|---|---|
| `SRC_PROJECT_U` | `U_project` PIT membership、board、status、market-cap proxy | `within_U_project_only` |
| `SRC_BENCHMARK` | official market benchmark price shock | `official_index_return_only` |
| `SRC_RAW_DAILY` | raw OHLCV、amount、turnover、corporate-action continuity audit | `provider_daily_market_data` |
| `SRC_QFQ_DAILY` | research return/path candidate | `provider_qfq_not_exact_total_return` |
| `SRC_SECURITY_MASTER` | listing/delisting/exchange/board | `field_level_pit_audit_required` |
| `SRC_SHARE_HISTORY` | total/listed-circulating share candidates | `not_official_free_float` |
| `SRC_CANDIDATE_PUBLIC` | 公开 read-only 公告、财务、flow、industry、universe、hedge source | `discovery_and_pit_audit_required` |
| `SRC_EXTERNAL_USER` | 用户另行提供的数据 | `source_and_pit_audit_required` |

22A 必须主动探索无需新凭据、付费或外部写操作的公开 read-only source，并允许下载到 attempt-specific raw cache。候选 source
缺失时先登记 gap 与搜索尝试，不能立即把 module 永久关闭。每次 acquisition 至少记录 URL/API/function、query、retrieval time、
HTTP/provider status、raw bytes hash、license/access note、rate-limit behavior 与 cache path。

需要新凭据、付费、许可承诺或修改外部系统时，记录：

```text
source_status = blocked_pending_external_access_decision
```

再请求用户决定；不得伪造数据或绕过访问限制。

优先 candidate-source families：

```text
D_UNIVERSE_BROAD_PIT
D_INDUSTRY_INDEX_HISTORY
D_INDUSTRY_PIT_MEMBERSHIP
D_ANNOUNCEMENT_TIMESTAMP_AND_REVISION
D_ISSUER_CAPITAL_ACTION
D_ETF_FUND_MARGIN_FLOW
D_AS_REPORTED_FUNDAMENTALS
D_SHARE_AND_FREE_FLOAT_HISTORY
D_EXECUTABLE_HEDGE_MECHANICS
D_AUCTION_OR_INTRADAY_EXECUTABLE_TIMING
```

### 4.2 Upstream artifact rules

允许继承的 upstream 内容：

- EP05 的 PIT top-N universe lineage 与对应 manifest；
- project-level raw/qfq/index/security-master 数据，但必须本次重新 hash；
- EP19 的 PIT/tradability 原则与 versioned schema 作为参考；
- EP20B-SRC 的 closure/公式身份，仅用于 duplicate-research comparator registry。

禁止继承为正向结论：

- realized-winner universe、future episode boundary、future phase；
- EP16/EP18 的 survival/payoff score；
- EP20/EP21 的正收益、模型能力或 outcome；
- EP21 `.building` payload；
- EP13/EP14 event formula 的有效性；
- EP8 regime label 的真实性。

### 4.3 Data-gap、source-search 与 usefulness contract

现有本地 PIT universe 是所有 module 的 `B0_existing_local_baseline`，不是固定 universe ceiling。每个 gap 必须先进入：

```text
data_gap_and_candidate_source_registry.csv
```

最小字段：

```text
gap_id
module_id
claim_id
missing_construct_or_field
current_baseline_proxy_or_null
current_claim_ceiling
candidate_source_family
candidate_provider_or_repository
candidate_endpoint_or_artifact
access_mode
credential_required
payment_required
license_or_terms_note
expected_date_coverage
expected_entity_coverage
required_timestamp_semantics
expected_module_unblock
priority
status
```

每次 source 搜索或 acquisition 写入：

```text
source_discovery_and_acquisition_attempt_log.csv
```

至少记录：

```text
source_attempt_id
gap_id
attempt_id
query_or_endpoint
request_parameters_semantic_sha256
retrieval_started_at
retrieval_completed_at
provider_status
response_media_type
raw_byte_size
raw_sha256
cache_path_or_null
rate_limit_observed
credential_used
payment_or_license_commitment
result_status
failure_reason
next_search_action
```

候选 source 的 contract usefulness 由以下三张表裁决：

```text
candidate_source_field_coverage_profile.csv
candidate_source_pit_reconstructability_audit.csv
source_construct_and_support_gain_registry.csv
```

`source_construct_and_support_gain_registry.csv` 至少包含：

```text
source_attempt_id
module_id
baseline_arm_id = B0_existing_local_baseline
augmented_arm_id
construct_fidelity_before
construct_fidelity_after
date_coverage_before
date_coverage_after
entity_or_event_coverage_before
entity_or_event_coverage_after
effective_block_n_before
effective_block_n_after
claim_ceiling_before
claim_ceiling_after
maintenance_complexity
license_or_cost_status
contract_usefulness_state
blocking_reason
```

`contract_usefulness_state` 只能为：

```text
source_not_found
source_access_blocked
source_available_but_not_PIT_reconstructable
source_PIT_usable_but_coverage_insufficient
source_redundant_with_existing_proxy
source_improves_construct_or_support
source_unblocks_component
```

22A 不用 module outcome 裁决 empirical usefulness。D3 通过的 source 必须进入：

```text
source_incremental_value_experiment_registry.csv
```

最小字段：

```text
source_attempt_id
module_id
baseline_arm_id
augmented_arm_id
paired_denominator_rule
incremental_estimand_id
required_module_requirement
search_family_id
exploratory_attempt_status
empirical_result_state
```

`empirical_result_state` 在 22A 中固定为 `pending_module_specific_outcome_attempt`。后续 module 可以输出：

```text
source_adds_incremental_historical_evidence
source_changes_or_falsifies_prior_interpretation
source_no_incremental_value
source_empirical_value_unstable
source_empirical_value_low_power
```

---

## 5. Source statement、construct 与 claim registry

`source_claim_registry.csv` 必须至少登记下列 claim family：

| claim_id | module_id | practitioner statement family | testable construct | default measurement class |
|---|---|---|---|---|
| `C_M1_01` | M1 | 实际反应－应有反应体现相对强弱 | observable market/group price shock 下的 causal expected group response residual | `proxy` |
| `C_M2_01` | M2 | 情绪脉络可形成状态 | breadth/volatility/turnover/crowding observable state | `proxy` |
| `C_M2_02` | M2 | 持仓结构影响博弈 | timestamped holdings/positioning fields | `data_gated_direct_or_proxy` |
| `C_M3A_01` | M3A | issuer equity supply/action 影响市场 | timestamped announcement/eligibility/execution/completion events | `data_gated_direct_event` |
| `C_M3B_01` | M3B | aggregate capital demand/flow 影响市场 | timestamped fund/ETF/margin aggregate flow | `data_gated_direct_or_proxy` |
| `C_M4_01` | M4 | 大小盘/风格的价格响应效率不同 | PIT style return/turnover/liquidity/market-cap relation | `proxy_for_price_impact_efficiency` |
| `C_M5_01` | M5 | 长期价值势能来自质量与估值 | as-reported PIT fundamental quality/value | `data_gated_direct_financial_fields` |
| `C_M6A_01` | M6A | 单项风险预算原件应校准 | volatility/liquidity/tail primitive calibration | `direct_for_forecast_proxy_for_capacity` |
| `C_M6B_01` | M6B | 对冲可隔离 exposure | beta decomposition、shadow/executable hedge mechanics | `shadow_or_executable_data_gated` |

以下 statement 必须逐项登记为：

```text
measurement_class = deferred_policy_construct_not_tested_in_EP22
module_exploration_status = deferred_out_of_scope
```

- 短线/波段/趋势仓具体权重；
- `t+1/t+3/t+5` 观察后的真实加减仓动作；
- 情景树概率更新与主导变量切换；
- 现金余量规则；
- 综合 risk budget；
- 个股失效退出与 hedge 动态选择；
- 跨模块决策路由。

每个 claim row 必须具有：

```text
claim_id
source_statement_id
source_role
module_id
construct_name
construct_definition
measurement_class
required_observable
forbidden_interpretation
testable_hypothesis_id
construct_status
data_status
maximum_claim_ceiling
downstream_requirement_id
```

不得把同一个 proxy 同时当作多个不可交换 construct 的 direct evidence。

### 5.1 Source statement map

`source_statement_to_testable_hypothesis_map.csv` 必须保留：

```text
source_statement_id
source_statement_summary
source_role
module_id
hypothesis_id
estimand_id
observable_or_deferred
falsification_condition
required_source_ids
prohibited_claim
mapping_status
```

`source_role` 固定为：

```text
practitioner_narrative_design_hypothesis
```

不得写成 verified performance、verified strategy 或 causal truth。

---

## 6. Data availability 与 PIT timestamp contract

每个 source 与 field 必须分别审计。文件存在不等于 field 可用于 PIT research。

### 6.1 Source-level audit

`data_source_availability_and_pit_audit.csv` 每个 source/arm 至少记录：

```text
source_id
source_type
provider
artifact_path_or_null
artifact_state
file_exists
stability_state
sha256_or_directory_snapshot_sha256
schema_version_or_null
date_min
date_max
row_n
instrument_n
group_n
event_n
coverage_scope
publication_timestamp_available
revision_lineage_available
pit_reconstructable
construct_use_allowed
support_preflight_use_allowed
downstream_outcome_use_eligible
claim_ceiling
status
blocking_reason
```

`artifact_state` 只能为：

```text
formally_frozen_local
validated_working_local
working_local
external_user_supplied
missing
quarantined
```

### 6.2 Field-level time semantics

`field_availability_timestamp_registry.csv` 每个 field 至少记录：

```text
field_id
source_id
module_id
physical_column
semantic_definition
unit
observation_time
event_effective_time_or_null
provider_publication_time_or_null
exchange_publication_time_or_null
provider_ingestion_time_or_null
revision_time_or_null
availability_time
decision_information_cutoff
first_usable_time
timestamp_evidence
timestamp_quality
revision_policy
pit_usable
downstream_use
blocking_reason
```

时间优先级：

```text
first_market_usable_time =
    max(exchange_publication_time,
        provider_publication_time,
        proven_provider_availability_time,
        required_processing_completion_time)
```

如果精确时间未知：

```text
date_only_after_close_source -> next canonical session open
date_only_unknown_intraday_source -> next canonical session open
report_period_end_without_publication_time -> PIT unusable
current_snapshot_without_history -> historical PIT unusable
```

不得用 provider ingestion 的当前时间伪造历史 availability。

### 6.3 Price and status timing

通用日频语义：

```text
feature_cutoff = close(t)
first_usable_time = next executable open after t
outcome_start = first_usable_time
```

close `t` 才完整的 benchmark return、stock/group return、breadth、amount、turnover、volatility 与 market cap 不得假设在 close `t`
成交。

公告/财务/flow source 必须区分：

```text
event_effective_date
announcement_timestamp
exchange_publication_timestamp
provider_ingestion_timestamp
first_market_usable_time
revision_timestamp
```

### 6.4 qfq、corporate action 与 units

至少审计：

- raw/qfq calendar、instrument 与 OHLC row alignment；
- qfq factor discontinuity 与 unadjusted overnight gap；
- volume unit、money unit、turnover unit；
- `money / volume` 不是交易所逐笔 VWAP；
- suspension、resume、limit-up/down、delisting 与 ST status；
- total shares 与 listed-circulating shares 的 as-of date；
- benchmark/stock calendar mismatch；
- duplicate date、non-monotonic date、non-positive price、negative volume/money。

`qfq_status` 只能判定为：

```text
provider_qfq_research_price_with_continuity_audit
```

不得标为 exact total-return database。

### 6.5 Universe and scope ceiling

`B0_existing_local_baseline` 默认：

```text
stock_cross_section_scope = within_U_project
project_breadth != full_A_breadth
within_U_project_relative_small != A_share_small_cap
market_shock_source = official_benchmark_series
market_wide_supply_or_flow_claim = data_blocked_without_broad_source
```

若未另建并审计宽截面 PIT universe，B0 的股票、breadth、size、issuer 或 style 结论必须保留 `within_U_project`。22A 必须把
宽截面 PIT universe 作为 `D_UNIVERSE_BROAD_PIT` 主动探索；通过 source/PIT/coverage audit 后建立独立
`B1_expanded_PIT_universe` arm，并保留与 B0 的 denominator、composition、coverage 和结果配对，不能静默替换 B0。

---

## 7. Module estimand、metric 与 baseline freeze

22A 必须为以下八个独立 adjudication rows 建立合同：

```text
M1
M2
M3A
M3B
M4
M5
M6A
M6B
```

M3A/M3B 与 M6A/M6B 是 sibling；一个通过不替代另一个。

### 7.1 Module estimand registry

`module_estimand_registry.csv` 至少包含：

```text
module_id
claim_id
estimand_id
estimand_question
exposure_or_state
primary_outcome_semantics
primary_horizon
secondary_horizons
feature_cutoff
first_usable_time
outcome_start
primary_inference_unit
required_source_ids
construct_status
data_status
evidence_role
claim_ceiling
```

初始合同骨架：

| module | primary estimand | candidate primary horizon | primary inference unit |
|---|---|---|---|
| M1 | group reaction residual 对 future group abnormal return/path 的 G3-over-G2 增量 | H5 sessions | shock episode + date block |
| M2 | filtered observable state 对 future market distribution 的区分 | H20 sessions | state segment + non-overlapping calendar block |
| M3A | issuer executed capital-action event 对 issuer abnormal return/liquidity 的差异 | H20 sessions | issuer-event episode + issuer/calendar block |
| M3B | aggregate demand/flow innovation 对 market return/liquidity 的关联 | H20 sessions | non-overlapping aggregate calendar block |
| M4 | PIT style exposure 下 return/turnover/liquidity 的 price-response efficiency 差异 | H20 sessions | style-date block |
| M5 | as-reported quality/value 对 long-horizon return/risk 的差异 | 12 months | firm-report cohort + calendar vintage |
| M6A | 单项 volatility/liquidity/tail forecast primitive 的 calibration | H20 sessions | risk-forecast/date block |
| M6B | beta/hedge 对目标 exposure 的隔离程度 | H20 sessions | portfolio/date or hedge-roll block |

候选 primary horizon 只有 source maturity/support preflight 通过时才可冻结。否则该 module：

```text
primary_horizon = null
module_status in {data_blocked, construct_blocked, deferred_out_of_scope}
```

不得为了保留 module 而把 M5 降成短线、把 M3A announcement 改成 execution、把 M6B shadow 改称 executable。

### 7.2 Primary and secondary metric registry

`module_primary_secondary_metric_registry.csv` 必须逐 metric 冻结：

```text
module_id
metric_id
metric_role
metric_formula
economic_unit
orientation
horizon
denominator
missingness_policy
effect_floor
mde
adjusted_bound_rule
multiplicity_family_id
```

最低要求：

- 每个 module 只有一个 primary metric family；
- point estimate、interval、baseline delta、effective block N 与 missingness 同时报告；
- M1 primary effect unit 为 `bps of H5 forward group abnormal return per +1 train-standardized residual`；
- M2 不以状态命名本身为 outcome；
- M3A announcement/eligibility/execution/completion 分开；
- M3B 不把不同资金项无量纲相加；
- M4 turnover/market-cap change 不写成 signed flow；
- M5 使用 first-publication time，不用 report-period end；
- M6A volatility、liquidity、tail primitive 分开裁决；
- M6B shadow 与 executable 分开裁决。

### 7.3 Baseline registry

`module_baseline_registry.csv` 至少冻结：

| module | required baseline |
|---|---|
| M1 | G0–G5；primary `G3 vs G2`；EP20B-SRC-like group trailing residual comparator |
| M2 | unconditional distribution、simple observable regime、persistence/null-state baseline |
| M3A | calendar/issuer matched non-event、announcement-only、eligibility-only、execution-only arms |
| M3B | autoregressive market baseline、same-calendar null、single-source arms |
| M4 | raw style return、size-only、liquidity-only、turnover-only controls |
| M5 | size/value simple sorts、quality-only、value-only、sector/board controls when PIT-valid |
| M6A | rolling historical volatility/liquidity/tail baseline、naive unconditional forecast |
| M6B | unhedged、market-only shadow、style-only shadow；executable arm only with full mechanics |

每行至少包含：

```text
module_id
baseline_id
baseline_role
formula
required_sources
common_denominator_rule
incremental_comparison_id
hyperparameter_policy
status
blocking_reason
```

---

## 8. Historical split、sample role、multiplicity 与 power freeze

### 8.1 Historical evidence role

所有 2017-01 至 2026-05 的现有历史均固定为：

```text
design_contaminated_historical_real_market_evidence
```

任何名称包含 `holdout` 都只是内部 design holdout，不是 true OOS 或 forward evidence。

### 8.2 Calendar and split registry

唯一 session 顺序来自经审计的 `trading_calendar.csv`。默认历史边界：

```text
history_start = 2017-01-03
history_end = 2026-05-29
```

固定 sample roles：

```text
design_train:
    2017-01-03 through 2021-12-31

design_validation:
    2022-01-04 through 2024-12-31

design_holdout:
    2025-01-02 through 2026-05-29
```

如果 canonical calendar 缺少上述 boundary session，使用边界内第一个/最后一个实际 session，并在 registry 中保留 requested 与
resolved date。不得根据 event/outcome density 移动 split。

`historical_split_and_sample_role_registry.csv` 至少包含：

```text
module_id
fold_id
sample_role
requested_start
requested_end
resolved_start
resolved_end
fit_allowed
threshold_selection_allowed
outcome_read_allowed_in_22A
purge_sessions
embargo_sessions
whole_episode_assignment_rule
evidence_role
```

规则：

- 22A 所有 row 的 `outcome_read_allowed_in_22A = false`；
- rolling moments、scaler、state mapping、beta、bucket edge 只可在 design_train/expanding-past 拟合；
- design_validation 不得反向影响 formula/threshold；
- design_holdout 不得用于任何 selection；
- 同一 episode 不跨 fold；
- episode 跨边界时整体分配给 episode start 所在 fold；若其 outcome maturity 会穿越禁止边界，则 downstream 排除；
- purge 至少为 module primary horizon；
- embargo 至少为 primary horizon，或由 overlap audit 证明更严格值。

默认 purge/embargo：

| module | purge | embargo |
|---|---:|---:|
| M1 | 20 sessions | 20 sessions |
| M2 | 20 sessions | 20 sessions |
| M3A | 60 sessions | 60 sessions |
| M3B | 20 sessions | 20 sessions |
| M4 | 20 sessions | 20 sessions |
| M5 | 252 sessions | 252 sessions |
| M6A | 20 sessions | 20 sessions |
| M6B | 20 sessions | 20 sessions |

若冻结 primary horizon 更长，取 `max(default, primary_horizon)`。

### 8.3 Multiplicity

`multiplicity_family_registry.csv` 至少冻结：

```text
family_id
module_id
family_role
included_hypothesis_ids
included_directions
included_horizons
included_group_families
correction_method
alpha
adjusted_interval_rule
selection_prohibited
```

默认：

```text
primary_alpha = 0.05
primary_correction = Holm
secondary_correction = Benjamini-Hochberg FDR at 0.05
adjusted_bound_rule =
    directionally correct 95% family-adjusted confidence bound
    must clear the frozen economic floor
```

M1 primary family 必须同时覆盖：

```text
positive/negative market shock
positive/negative group residual shock
continuation/reversal
eligible primary event types
primary horizon
```

### 8.4 Effect floor and MDE

`power_and_support_preflight.csv` 不得读取 event-aligned realized outcome。它只使用：

- eligible date/event/group/report-vintage count；
- horizon maturity count；
- missingness/censor geometry；
- block/episode overlap；
- pre-registered scale source；
- analytical或 simulation-based detectable-effect formula with fixed seed。

需要 standardized effect scale 时，只能使用事件识别之前可得的 rolling/unconditional scale，或独立外部锁定的 scale：

```text
causal_pre_event_unconditional_scale_estimate
or
independent_external_locked_scale
```

不得把 event 后 observation 对齐为 outcome，不得用 estimated effect direction、association 或 performance 选择 threshold/horizon。

默认 minimum standardized effect floor：

```text
M1 = max(10 bps at H5, 0.10 pre-event unconditional group-return SD per +1 residual SD)
M2 = 0.10 standardized distributional separation
M3A = max(20 bps at H20, 0.10 independent locked scale)
M3B = 0.10 standardized association
M4 = 0.10 standardized incremental association
M5 = max(200 bps annualized, 0.10 independent locked scale)
M6A = 5% relative proper-loss improvement or 5 percentage-point coverage-error reduction
M6B_shadow = 10% relative target-beta or variance reduction without 10% larger non-target exposure
M6B_executable = same as shadow plus positive conservative cost-adjusted margin
```

这些是判断数量级是否值得继续的 ex-ante floors，不是 expected returns，也不授权交易。

### 8.5 Minimum effective support

22A 必须冻结并逐 module 输出：

```text
minimum_raw_rows
minimum_distinct_dates
minimum_distinct_episodes_or_segments
minimum_effective_blocks
minimum_years
minimum_fold_support
minimum_direction_support
minimum_group_or_instrument_coverage
maximum_missing_rate
maximum_top_date_contribution_share
maximum_top_episode_contribution_share
maximum_top_group_or_name_contribution_share
```

默认最低值：

| module | effective blocks | years | fold support | additional support |
|---|---:|---:|---:|---|
| M1 | 40 | 6 | 12 episodes | 25 shock dates per direction；2 exchange groups |
| M2 | 48 | 6 | 12 blocks | 每个 primary state 至少 12 blocks |
| M3A | 60 | 6 | 15 events | 每个 primary event type 至少 30 issuer episodes |
| M3B | 48 | 6 | 12 blocks | primary flow source coverage ≥ 80% sessions |
| M4 | 48 | 6 | 12 blocks | 每日每端至少 30 instruments |
| M5 | 40 | 6 | 10 vintages | 每端至少 100 firm-report rows，至少 3 reporting vintages/year |
| M6A | 48 | 6 | 12 blocks | 每个 primitive 独立满足 |
| M6B | 48 | 6 | 12 blocks | executable arm 必须覆盖 roll/cost/basis ledger |

默认 concentration limits：

```text
maximum_top_date_contribution_share = 0.10
maximum_top_episode_contribution_share = 0.10
maximum_top_group_contribution_share = 0.70 for two-group M1
maximum_top_group_or_name_contribution_share = 0.25 otherwise
```

M1 下游必须逐值复制的 support/stability registry 固定为：

```text
minimum_distinct_shock_dates = 50
minimum_distinct_episodes = 40
minimum_effective_blocks = 40
minimum_years = 6
minimum_direction_support = 25 distinct dates
minimum_fold_support = 12 effective episodes_or_blocks
minimum_group_coverage = 2 eligible exchange groups
maximum_missing_rate = 0.20
maximum_top_date_contribution_share = 0.10
maximum_top_episode_contribution_share = 0.10
maximum_top_group_contribution_share = 0.70

stability_tolerance =
    primary effect has the registered direction in at least 2 of 3 sample roles
    AND no evaluable sample role has an opposite effect whose magnitude
        exceeds the frozen primary effect floor
    AND leave-one-year-out sign support is at least 0.70
```

如果 group 数不足以做 cross-group rank：

```text
cross_group_rank_mode = not_evaluable
analysis_mode = two_group_contrast_mode or continuous_pair_panel_mode
```

不得降低 support floor 来保留某个 module。support 不足输出 `exploration_ready_low_power` 或 `data_blocked`，不得伪装成
充分支持。

---

## 9. M1 group taxonomy 与 source eligibility

M1 必须把 group 类型分开：

```text
exchange_board
genuine_industry
style_group
concept_or_theme
```

### 9.1 Arm matrix

| arm_id | required data | maximum research use |
|---|---|---|
| `MKT_CENSUS` | official benchmark + frozen breadth | market shock census |
| `EXCHANGE_BOARD_RETURN` | PIT board membership + daily price | board return/residual/as-of/outcome in 22B |
| `EXCHANGE_BOARD_STRUCTURE` | 上述 + constituent status/amount | board breadth/dispersion/liquidity |
| `INDUSTRY_RETURN_ONLY` | audited historical official industry-index OHLCV | industry return residual；无内部结构 |
| `INDUSTRY_INTERNAL_STRUCTURE` | PIT industry membership + constituent fields | industry internal structure |
| `STYLE_GROUP_RETURN` | train-only PIT style buckets + daily price | style group sensitivity，非行业 |
| `CONCEPT_THEME` | historical membership + revision timestamps | 默认 `data_blocked_until_audited` |
| `L3_STOCK_DECOMPOSITION` | separate exploratory variant | `deferred_out_of_22A_scope` |

`m1_group_taxonomy_and_source_registry.csv` 至少包含：

```text
group_family_id
group_id
group_name
group_type
return_source_mode
index_alias_or_null
membership_source_or_null
membership_timestamp_semantics
weighting_mode
weight_timestamp_semantics
return_arm_status
internal_structure_arm_status
claim_ceiling
readiness_status
blocking_reason
```

### 9.2 Industry boundary

只有 official historical industry-index OHLCV 时：

```text
INDUSTRY_RETURN_ONLY = eligible
INDUSTRY_INTERNAL_STRUCTURE = data_blocked
```

只有逐时点 membership、instrument mapping 与 `t-1` weights 通过审计时，internal structure 才 eligible。current industry、current
concept/theme、2025 snapshot 或无 revision timestamp 的 mapping 一律不可回填。

`m1_group_membership_and_weight_pit_audit.csv` 至少包含：

```text
group_family_id
group_id
session
membership_source
membership_asof_time
weight_source
weight_asof_time
registered_constituent_n
evaluable_constituent_n
weight_sum
maximum_weight
effective_constituent_n
missing_return_n
membership_pit_gate
weight_pit_gate
internal_structure_gate
blocking_reason
```

### 9.3 Primary M1 group and weighting

若本地计划时 inventory 通过审计，v0 primary 冻结为：

```text
market_benchmark_alias = all_a
primary_group_family = exchange_board
primary_group_ids = [main_board, chinext]
group_return_source_mode = pit_constituent_portfolio
primary_weighting = t_minus_1_total_market_cap_weight
sensitivity_weighting = equal_weight
market_cap_ceiling = raw_close_times_total_share_asof_not_free_float
```

若 B0 任一 primary source/PIT gate 不通过，B0 arm 标为 `data_blocked`，不得静默替代。允许在 D0–D3 中寻找新 source，并以新的
`candidate_source_augmented` arm、attempt ID、公式和 claim ceiling 继续探索。

---

## 10. M1 market common-shock freeze

22A 可以读取当日与过去 benchmark/group/stock data 来定义 preoutcome events，但不得连接 event 后 outcome。

### 10.1 Primary clock and formula

```text
shock_observation_time = close(t)
feature_cutoff = close(t)
first_usable_time = next executable open after t

market_return_t =
    benchmark_close_t / benchmark_close_t-1 - 1

market_center_t_minus_1 =
    rolling_median(market_return through t-1, 252 sessions)

market_scale_t_minus_1 =
    1.4826 * rolling_MAD(market_return through t-1, 252 sessions)

minimum_history_sessions = 126

market_shock_z_t =
    (market_return_t - market_center_t_minus_1)
    / market_scale_t_minus_1
```

非有限或非正 scale 时 row 不可评估，不得加 epsilon。

### 10.2 Threshold candidates and deterministic selection

只允许以下 candidate grid：

```text
z_cutoff_abs in {1.5, 2.0, 2.5}
absolute_return_floor in {null, 0.01}
instrument_direction_breadth_cutoff in {0.55, 0.60, 0.65}
```

Primary breadth 固定使用：

```text
within_U_project_instrument_breadth
```

exchange-board breadth 只做 diagnostic，因为两个 group 不足以独立证明 market-wide breadth。

Candidate selection 不读取 outcome，且只使用 `design_train` 的事件支持，按以下 lexicographic rule：

```text
1. source/PIT/coverage gate pass；
2. design_train positive 与 negative distinct shock dates 各 >= 12；
3. design_train 至少 3 calendar years 每方向有事件；
4. design_train shock-date top-year share <= 0.50；
5. 在满足 1–4 的候选中选择最大 abs(z cutoff)；
6. 再选择 absolute_return_floor = 0.01；
7. 再选择最高 breadth cutoff；
8. 仍并列时按 canonical policy_id 升序。
```

选择后才对固定 policy 做非选择性的 validation/holdout coverage gate：

```text
full-history positive 与 negative distinct shock dates 各 >= 25
design_validation 每方向 >= 8
design_holdout 每方向 >= 8
full-history 至少 6 calendar years 每方向有事件
full-history shock-date top-year share <= 0.35
```

coverage gate 失败时不得退回选择次优 candidate。若无 design-train candidate 或冻结 policy 的后续 coverage gate 不通过：

```text
MKT_CENSUS = exploration_ready_low_power
selected_shock_policy_id = null
M1_exploration_readiness_status = exploration_ready_low_power
```

不得 outcome 后改阈值。

### 10.3 Breadth

```text
instrument_direction_breadth_t =
    count(PIT eligible instruments with return sign == market shock sign)
    / count(PIT eligible instruments with finite eligible return)

market_breadth_pass_t =
    instrument_direction_breadth_t >= selected directional cutoff

market_common_shock_t =
    abs(market_shock_z_t) >= selected z cutoff
    AND selected absolute-floor rule
    AND market_breadth_pass_t

index_concentrated_or_group_led_move_t =
    magnitude pass
    AND absolute-floor pass
    AND NOT market_breadth_pass_t
```

Denominator 逐日保留。`within_U_project_instrument_breadth` 不得写成 full-A breadth。

### 10.4 Required census

`m1_common_shock_date_census.csv` 必须保留 minimum-history 通过后的全部 evaluable sessions，不只保留 shock date。

至少包含：

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
instrument_breadth_value
instrument_breadth_denominator
group_breadth_value
group_breadth_denominator
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

---

## 11. M1 group expected response、residual shock 与 pair state

### 11.1 Group return

自建 group return：

```text
group_return_g,t =
    sum(weight_i,t-1 * qfq_close_return_i,t)
    over PIT members evaluable at t
```

同时发布：

```text
registered_constituent_n
evaluable_constituent_n
weight_sum_before_normalization
maximum_weight
effective_constituent_n
missing_return_share
```

默认 group daily eligibility：

```text
evaluable_constituent_n >= 30
weight_coverage >= 0.80
maximum_weight <= 0.35
```

不满足时 row 不可评估。

### 11.2 Expected response

v0 primary：

```text
expected_response_model = causal_OLS_alpha_plus_market_beta
lookback_sessions = 252
minimum_pairs = 126
fit_cutoff = t-1 close
intercept = true
regularization = none
solver = deterministic_SVD_least_squares
rank_deficient_or_nonfinite = fail_row
```

```text
expected_group_return_g,t =
    alpha_g,t-1 + beta_g,t-1 * market_return_t

group_reaction_residual_g,t =
    observed_group_return_g,t - expected_group_return_g,t
```

`rest_of_market_ex_group` 为 group-specific shock 的优先 benchmark。若无法因果构造，必须记录 benchmark contamination；
未经 22A readiness registry 明确登记 eligible fallback 时 group-specific arm 阻断。

### 11.3 Residual scale and candidate selection

```text
group_residual_center_t_minus_1 =
    rolling_median(group residual through t-1, 252 sessions)

group_residual_scale_t_minus_1 =
    1.4826 * rolling_MAD(group residual through t-1, 252 sessions)

minimum_residual_history = 126 sessions
group_shock_z =
    (residual - residual_center) / residual_scale
```

Candidate grid：

```text
group_z_cutoff_abs in {1.5, 2.0, 2.5}
localized_group_share_maximum in {0.25, 0.50}
```

只按 design-train preoutcome support 选择：

```text
each residual direction has >= 12 distinct group-shock dates
>= 3 design-train calendar years represented
style-cluster/common-shock overlap is measurable
choose highest z cutoff, then lowest localized share, then policy_id
```

冻结后必须做：

```text
full-history each residual direction >= 25 distinct group-shock dates
design_validation and design_holdout each direction >= 8 dates
full-history >= 6 calendar years represented
```

失败时不得切换 candidate；group-specific arm 输出 `exploration_ready_low_power`。

### 11.4 Pair-state truth table

每个 market-date/group pair 必须互斥映射为：

```text
no_material_shock
pure_market_common_shock
market_shock_with_group_amplification
market_shock_with_group_resistance
group_specific_positive_residual_shock
group_specific_negative_residual_shock
index_concentrated_or_group_led_move
non_evaluable
```

正负 market shock 与正负 residual 的 orientation 必须由公式确定，不得由 future continuation/reversal 命名。

### 11.5 Online episode

默认：

```text
cooldown_sessions = 5
maximum_age_sessions = 20
same_direction_trigger_within_cooldown = merge_and_update_online
opposite_direction_trigger = close_previous_then_start_new
future_recovery_or_future_high_boundary = forbidden
whole_episode_fold_assignment = episode_start_fold
```

`m1_market_group_shock_episode_census.csv` 至少包含：

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

### 11.6 Pair panel

M1 pair panel 至少保留：

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

不得包含任何 forward field。

---

## 12. M1 reaction as-of panel 与 power preflight

`m1_group_reaction_asof_panel.csv` 是 22A 唯一可物化的 M1 feature panel。它必须在连接任何 future outcome 前完成内部校验、
记录 semantic hash 并 checkpoint；不要求人工批准或 immutable seal。

至少包含：

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

所有 rolling anomaly 只使用 `<= t-1` fit state；当日 observable value 可在 close `t` 进入 as-of row。

### 12.1 M1 baseline/model freeze for 22B

若 M1 exploration-ready，22A 必须 checkpoint：

```text
primary_horizon_sessions = 5
secondary_horizon_sessions = [1,3,10,20]
analysis_mode = two_group_contrast_mode plus continuous_pair_panel_mode
cross_group_rank_mode = not_evaluable_unless_eligible_group_n >= 5

model_family = OLS
solver = deterministic_SVD_least_squares
regularization = none
intercept = true
feature_scaling = train_only_zscore
singular_design_policy = fail_fold

primary_loss = date_balanced_RMSE_of_forward_group_abnormal_return
primary_economic_association =
    bps of forward_group_abnormal_return per +1 train-standardized residual
primary_effect_floor =
    max(10 bps, 0.10 causal pre-event unconditional group-return SD)
G3_minus_G2_increment_floor =
    non_positive date-balanced RMSE delta with adjusted upper bound < 0
    AND residual coefficient adjusted directional bound clears effect floor
```

M1 nested baseline 固定：

```text
G0 = frozen market/group shock magnitude controls
G1 = G0 + raw group return
G2 = G0 + simple group-minus-market relative strength
G3 = G2 + causal beta-adjusted group reaction residual
G4 = G3 + eligible breadth/dispersion block
G5 = G4 + eligible volume/turnover/liquidity/concentration block
```

G3 不优于 G2 时，G4/G5 不得 rescue positive terminal。

### 12.2 M1 downstream outcome semantics freeze

22A 只冻结下列语义，不物化任何值：

```text
entry_clock = next canonical session open after shock close
horizon_clock = canonical trading sessions from entry open
primary_horizon_sessions = 5
exit_clock = open exactly H sessions after entry open
primary_return_semantics = open_to_open

official_index_arm =
    official group index open_at_exit / open_at_entry - 1

self_built_group_arm =
    event-time PIT constituent set
    + t-1 frozen weights
    + no outcome-window rebalancing

entry_blocked_constituent_policy =
    exclude at common entry open and renormalize only if
    frozen entry-weight coverage >= 0.80

exit_missing_constituent_policy =
    no forward-fill across suspension or delisting;
    mark constituent non-evaluable and renormalize only if
    frozen entry-weight exit coverage >= 0.80

group_outcome_non_evaluable =
    entry or exit frozen-weight coverage < 0.80
    OR benchmark/rest-of-market path unavailable

forward_abnormal_return =
    forward_group_return
    - event-preceding frozen beta * forward_rest_of_market_return_ex_group
    - eligible checkpointed control component

path_mark_clock = each canonical session close after entry
MAE = minimum cumulative abnormal return through H
MFE = maximum cumulative abnormal return through H
realized_volatility = standard deviation of daily abnormal returns through H
downside_tail_proxy = minimum daily abnormal return through H

negative_shock_recovery =
    first close through H at which group level regains shock-date close
recovery_tolerance_bps = 1
positive_shock_recovery = not_applicable
not_recovered_by_H = right_censored_at_H

continuation_zero_tolerance_bps = 1
abs(forward abnormal return) <= 1 bp =
    neither_continuation_nor_reversal
```

这些字段进入 `module_primary_secondary_metric_registry.csv`，但 22A artifact 中不得出现 entry/exit price、future return、path mark、
MAE、MFE 或 recovery value。

### 12.3 M1 power preflight

`m1_shock_threshold_power_and_support_preflight.csv` 每个 candidate policy 至少包含：

```text
market_policy_id
group_policy_id
z_cutoff_abs
absolute_return_floor
instrument_breadth_cutoff
group_z_cutoff_abs
localized_group_share_maximum
evaluable_session_n
positive_market_shock_date_n
negative_market_shock_date_n
positive_group_shock_date_n
negative_group_shock_date_n
distinct_episode_n
effective_block_n
year_n
fold_direction_min_n
top_year_share
group_coverage
missing_rate
support_gate
power_method
assumed_effect_floor
minimum_detectable_effect
power_at_effect_floor
selection_rank
selected
blocking_reason
```

不得包含 realized future outcome 或 estimated module effect。

### 12.4 Semantic hashes

至少计算：

```text
market_event_set_semantic_sha256
group_event_set_semantic_sha256
pair_state_panel_semantic_sha256
episode_membership_semantic_sha256
group_reaction_asof_semantic_sha256
```

hash 输入必须按稳定 key 排序、canonical float/string/null serialization；不得依赖 dataframe row order。

---

## 13. Module research readiness 与 claim ceiling

`module_research_readiness.csv` 每个 module/arm 一行。状态 enum：

```text
exploration_ready
exploration_ready_low_power
data_blocked
construct_blocked
deferred_out_of_scope
```

另设独立字段：

```text
data_construct_status in {
    eligible_for_downstream_exploration,
    eligible_but_low_power,
    data_blocked,
    construct_blocked,
    deferred_out_of_scope
}

local_implementation_allowed = true
local_preoutcome_execution_allowed = true
local_historical_outcome_exploration_allowed = true
formal_forward_freeze_allowed = false
```

这些字段表达研究 readiness 与 scope，不是人工授权。`exploration_ready_low_power` 允许尝试，但报告必须以低功效为首要限制。

至少包含：

```text
module_id
arm_id
construct_status
data_status
support_status
exploration_readiness_status
data_construct_status
eligible_source_ids
eligible_field_ids
eligible_estimand_ids
primary_horizon
claim_ceiling_id
local_implementation_allowed
local_preoutcome_execution_allowed
local_historical_outcome_exploration_allowed
formal_forward_freeze_allowed
blocking_reason
next_required_action
```

### 13.1 Readiness truth table

```text
if construct cannot distinguish the claimed object:
    exploration_readiness_status = construct_blocked

elif required direct/proxy source or PIT timestamp is unavailable:
    exploration_readiness_status = data_blocked

elif effective support is below frozen minimum:
    exploration_readiness_status = exploration_ready_low_power
    data_construct_status = eligible_but_low_power

elif source, PIT, construct and support gates pass:
    exploration_readiness_status = exploration_ready
    data_construct_status = eligible_for_downstream_exploration
```

22A 不得判定：

```text
component_directly_measurable_historically_stable
component_proxy_only_historically_informative
component_measurable_but_historically_unstable
component_historically_falsified
```

这些需要 downstream outcome。

### 13.2 Claim ceiling registry

`claim_ceiling_registry.csv` 至少包含：

```text
claim_ceiling_id
module_id
arm_id
measurement_class
scope
allowed_claim_template
forbidden_claims
historical_support_claim_allowed
forward_support_claim_allowed
execution_claim_allowed
upgrade_requirements
status
```

固定 ceiling 示例：

```text
M1 price-only arm:
    price_shock_proxy_only

M2 OHLCV breadth/state arm:
    observable_sentiment_positioning_proxy_only

M3A timestamped executed issuer action:
    direct_event_measurement_without_causal_or_flow_identity_claim

M3B incomplete flow fields:
    source_specific_flow_proxy_only

M4:
    within_U_project_style_price_response_relation_only

M5:
    as_reported_PIT_quality_value_relation_only

M6A liquidity:
    liquidity_capacity_proxy_only

M6B shadow:
    non_executable_exposure_attribution_only
```

---

## 14. Ordered gates 与 terminal decision

Gate 顺序固定：

```text
GATE_00_contract_and_attempt_identity
GATE_01_access_firewall
GATE_02_required_local_source_integrity
GATE_03_source_role_and_stability_state
GATE_03D_data_gap_and_candidate_source_search_accounting
GATE_03E_candidate_source_access_cost_license_and_cache_lineage
GATE_04_field_timestamp_and_revision_lineage
GATE_04D_candidate_source_PIT_construct_and_support_gain
GATE_05_universe_calendar_security_master_alignment
GATE_06_raw_qfq_units_and_corporate_action
GATE_07_construct_and_statement_mapping
GATE_08_estimand_metric_baseline_completeness
GATE_09_split_multiplicity_and_effect_floor_freeze
GATE_10_module_support_and_power_preflight
GATE_11_m1_group_taxonomy_and_membership
GATE_12_m1_shock_formula_threshold_and_census
GATE_13_m1_episode_and_asof_panel_integrity
GATE_14_module_readiness_truth_table
GATE_15_claim_ceiling
GATE_16_manifest_hash_and_working_checkpoint
```

前序 gate fail 后，依赖它的后续 gate 必须：

```text
status = not_run_due_to_prior_gate_failure
```

不得伪造 pass。

### 14.1 Terminal-state mapping

```text
if run incomplete, access violation, hash mismatch, schema mismatch,
   timestamp contract incoherent, or common contract cannot be frozen:
    22A_pit_or_construct_contract_blocked

elif every material module in {M1,M2,M3A,M3B,M4,M5,M6A,M6B}
     is data_blocked or construct_blocked
     AND every material data gap has exhausted the frozen public-source search budget
     or is explicitly blocked by credential/payment/license:
    22A_all_material_modules_data_blocked

elif at least one module is exploration_ready
     and at least one other material module is data_blocked,
     construct_blocked, exploration_ready_low_power, or deferred_out_of_scope:
    22A_partial_data_ready_with_blocked_modules

elif at least one selected module is exploration_ready
     and all other rows have a coherent non-blocking contract:
    22A_contract_ready_for_selected_component_validation
```

“all other rows have coherent contract”不等于全部 module 可执行；它只表示不存在破坏共同合同的 PIT/construct 矛盾。

### 14.2 Terminal decision schema

```json
{
  "schema_version": "S_22A_TERMINAL_DECISION_V0",
  "run_id": "22A_source_data_availability_and_validation_contract_v0",
  "contract_version": "22A_common_contract_v0",
  "attempt_id": "",
  "snapshot_state": "working",
  "terminal_state": "22A_pit_or_construct_contract_blocked",
  "evidence_role": "preoutcome_source_data_and_validation_contract",
  "module_states": {},
  "exploration_ready_requirement_ids": [],
  "outcome_read_occurred": false,
  "historical_support_claim_allowed": false,
  "forward_support_claim_allowed": false,
  "local_downstream_exploration_allowed": true,
  "formal_forward_freeze_allowed": false,
  "decision_router_authorized": false,
  "deployment_authorized": false
}
```

downstream 可以读取 `checkpointed` 或 `validated_working_result` snapshot；读取方必须绑定 attempt/config/input/semantic hashes 并继承
`provisional=true`。只有 `optional_formal_freeze` 才产生 immutable 语义，但 22A 常规完成不要求该状态。

---

## 15. Required artifacts

完整输出：

```text
preflight/contract_resolution.json
preflight/exploration_scope_and_attempt_audit.csv
preflight/access_audit.csv
preflight/input_artifact_audit.csv
preflight/source_directory_snapshot.csv
preflight/source_schema_and_key_audit.csv
preflight/calendar_alignment_audit.csv
preflight/raw_qfq_corporate_action_and_unit_audit.csv

source_claim_registry.csv
source_statement_to_testable_hypothesis_map.csv
data_gap_and_candidate_source_registry.csv
source_discovery_and_acquisition_attempt_log.csv
candidate_source_access_cost_and_license_registry.csv
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
m1_market_group_pair_state_panel.csv
m1_market_group_shock_episode_census.csv
m1_group_reaction_asof_panel.csv
m1_shock_threshold_power_and_support_preflight.csv
m1_formula_and_semantic_hash_registry.csv

module_research_readiness.csv
claim_ceiling_registry.csv
gate_results.csv
stage_status_registry.csv
decision/22A_terminal_decision.json
reports/22A_source_data_availability_and_validation_contract_report.md
manifest.json
output_hashes.csv
checkpoint_receipt.json
```

如果任一 publishable table 过大，可改为：

```text
*.csv.gz with gzip_mtime=0
or
*.parquet with pyarrow/zstd
```

但 logical artifact name、schema、row-count audit 与 semantic hash 必须保留；downstream 通过 manifest 解析 physical path，不得猜扩展名。

### 15.1 Input artifact audit schema

```text
artifact_id
artifact_path
artifact_role
artifact_state
expected_sha256_or_null
observed_sha256
size_bytes
schema_version_or_null
date_min
date_max
row_n
read_stage
scope_eligible
status
blocking_reason
```

### 15.2 Gate schema

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

### 15.3 Output hash schema

```text
logical_artifact_id
relative_path
media_type
schema_version
row_n_or_null
byte_size
sha256
semantic_sha256_or_null
required
```

`output_hashes.csv` 不得包含自身与 `checkpoint_receipt.json`，避免递归 hash。

---

## 16. Report contract

中文报告必须按以下顺序：

1. terminal state 与一句话结论；
2. 22A 的 preoutcome 身份、没有读取什么；
3. source statement 与 construct 分类；
4. data-gap registry、candidate-source search coverage 与 acquisition failures；
5. 本地 baseline 和新增 source inventory、stable/working 状态与 hash；
6. candidate-source access/cost/license、field coverage、PIT 与 revision audit；
7. B0/B1 construct、coverage 与 effective-support gain；
8. universe、calendar、raw/qfq、corporate action 与 unit audit；
9. M1–M6A/B estimand、metric、baseline 与 claim ceiling；
10. historical split、sample role、purge、embargo 与 multiplicity；
11. power/support preflight，明确它不含 realized effect；
12. M1 group taxonomy、industry data boundary 与 eligible arms；
13. M1 market/group shock policy、candidate selection 和 denominator；
14. M1 episode/as-of panel coverage 与 semantic hashes；
15. 每个 module/arm 的 readiness、blocked reason 和 next action；
16. source incremental-value experiment handoff；
17. 允许与禁止的 claims；
18. terminal mapping、checkpoint 与 downstream handoff。

报告必须显式写出：

```text
22A did not evaluate component outcomes.
research readiness is not historical support or production authorization.
historical data are design-contaminated and do not provide forward support.
M1 price shock does not identify semantic news surprise or mispricing.
within_U_project breadth is not full-A breadth.
industry return-only is not industry internal-structure evidence.
shadow hedge is not executable hedge.
```

不得写：

- “六个模块全部值得做”；
- “M1/M2/M4 已有效”；
- “真实市场验证已完成”；
- “四阶段方法已被复现”；
- “14 亿元业绩已核验”；
- “可进入实盘”。

---

## 17. Manifest、hash closure 与 iterative checkpoint publication

### 17.1 Manifest

`manifest.json` 至少包含：

```text
schema_version
experiment_id
phase_id
run_id
contract_version
attempt_id
created_at
completed_at
git_commit_or_null
dirty_worktree_at_run
requirement_sha256
research_plan_sha256
resolved_config_sha256
input_artifacts
output_artifacts
semantic_hashes
stage_states
terminal_state
snapshot_state
provisional
```

### 17.2 Canonical serialization

- CSV：UTF-8、LF、固定 column order、`%.12g`、空值为空字符串；
- JSON：sorted keys、UTF-8、无 NaN/Infinity；
- gzip：`mtime=0`；
- parquet：pyarrow + zstd，固定 schema；
- timestamps：ISO-8601，带 timezone 或明确 `Asia/Shanghai`；
- dates：`YYYY-MM-DD`；
- booleans：CSV 中只用 `true/false`；
- stable keys：canonical strings 的 SHA256。

### 17.3 Iterative checkpoint publication

写入：

```text
OUTPUT_ROOT/attempts/<attempt_id>.working
```

完成后依次：

1. 校验 required artifacts；
2. 校验 schema、unique key、row count 与 referential integrity；
3. 复算 input/output/semantic hashes；
4. 确认 access audit 无 violation；
5. 确认 terminal decision 与 readiness truth table 一致；
6. 写入 `checkpoint_receipt.json`；
7. 将 attempt 状态原子更新为 `checkpointed` 或 `validated_working_result`；
8. 更新 `OUTPUT_ROOT/latest.json` 指向当前 validated attempt。

同一 attempt 的临时文件可以在运行中更新；一旦 checkpointed，后续语义变化使用新 `attempt_id`。`latest.json` 可移动，但历史
attempt checkpoint 不得静默覆盖。普通 EP22 探索不创建 mandatory seal；正式 forward freeze 使用单独流程。

---

## 18. Test contract

### 18.1 Unit tests

至少覆盖：

1. config unknown/missing key fail；
2. hidden attempt/config override fail；
3. path whitelist 与 forbidden path guard；
4. forbidden forward column guard；
5. source state enum 与 stable/working 判定；
6. file/directory deterministic hash；
7. timestamp precedence 与 next-session usable mapping；
8. current snapshot 不可回填 PIT；
9. raw/qfq calendar alignment；
10. volume/money/turnover unit guard；
11. universe stable-key uniqueness；
12. split boundary resolution；
13. episode whole-fold assignment；
14. multiplicity family completeness；
15. outcome-blind power preflight；
16. M1 rolling median/MAD 使用 `<= t-1`；
17. zero/nonfinite scale fail row；
18. instrument breadth denominator；
19. shock candidate lexicographic selection；
20. group t-1 membership/weight；
21. group return coverage/max-weight guard；
22. causal beta fit cutoff；
23. residual candidate selection；
24. pair-state truth table exhaustive and mutually exclusive；
25. online episode 不用 future recovery；
26. as-of panel 无 forward columns；
27. semantic hash row-order invariance；
28. module readiness truth table；
29. terminal-state precedence；
30. output-hash closure、attempt lineage 与 checkpoint publication；
31. public read-only acquisition allowlist 与 credential/payment guard；
32. raw response/cache deterministic hash；
33. gap-to-source-attempt referential integrity；
34. B0/B1 construct/coverage/support paired comparison；
35. D3 contract usefulness 不会被误写成 empirical usefulness。

### 18.2 Synthetic integration tests

至少构造：

- 两个 exchange-board、一个 benchmark、一个 PIT membership 变化；
- 一个正 market shock、一个负 market shock；
- 一个 index-concentrated move；
- 一个 group-specific positive residual shock；
- 一个 group-specific negative residual shock；
- 一次 membership late arrival；
- 一次 qfq discontinuity；
- 一个 zero-MAD window；
- 一次 episode same-direction merge 与 opposite-direction close；
- 一个 current-industry backfill trap；
- 一个 forward-return column trap；
- 一个 low-power module；
- 一个 missing-source module。
- 一个 public source 可访问但缺历史 timestamp；
- 一个 source 增加 coverage 但不改善 effective support；
- 一个需要新 credential 的 source；

断言：

```text
no future field is read
all pair states are mutually exclusive
all rolling fits stop at t-1
late membership is not backfilled
industry return-only does not make internal structure eligible
low power remains explicit exploration_ready_low_power
missing source does not silently substitute OHLCV
public read-only source can be cached with full lineage
credentialed or paid source is blocked pending access decision
contract usefulness does not become empirical usefulness
terminal state follows the truth table
```

### 18.3 Real-data validation

实现后至少执行：

```bash
python -m pytest -q \
  experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/tests/test_22a_source_data_availability_and_validation_contract.py

python experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/src/run_22a_source_data_availability_and_validation_contract.py \
  --config experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/configs/config_22a_source_data_availability_and_validation_contract.yaml
```

运行后验证：

```bash
python -m compileall \
  experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/src \
  experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/tests

git diff --check
```

实现可增加专用 validator，但不得以 validator 修补 runner 已产出的不一致 artifact。

---

## 19. Definition of Done

只有同时满足以下条件，22A 才完成：

- [ ] requirement、research plan、config、code 与 attempt identity 均 hash-bound；
- [ ] access firewall 无 violation；
- [ ] source inventory、schema、key、coverage、stable/working 状态完整；
- [ ] 每个 material data gap 有 candidate-source registry 与搜索尝试记录；
- [ ] public read-only source acquisition 保留 endpoint/query/time/raw hash/cache/license lineage；
- [ ] candidate source 的 PIT、revision、coverage、construct 与 effective-support gain 已分别审计；
- [ ] B0 existing-data baseline 与 B1 augmented-source contract 没有静默替换；
- [ ] D3 contract usefulness 与 D4 empirical usefulness 明确分开；
- [ ] 值得继续的 source 已进入 module-specific incremental-value experiment registry；
- [ ] 每个 field 有 availability/first-usable/revision 语义；
- [ ] raw/qfq、calendar、status、corporate action 与 units 已审计；
- [ ] 所有 practitioner statements 已映射或明确 deferred；
- [ ] M1、M2、M3A、M3B、M4、M5、M6A、M6B 均有独立 estimand row；
- [ ] primary/secondary metric、baseline、split、purge、embargo、multiplicity 已冻结；
- [ ] effect floor、MDE、effective support 与 low-power terminal 已 outcome-blind 冻结；
- [ ] M1 group taxonomy、industry boundary 与 arm eligibility 明确；
- [ ] M1 market/group shock candidate selection 不使用 future outcome；
- [ ] M1 full denominator census、pair state、episode 与 as-of panel 完整；
- [ ] M1 as-of panel 不含 forward field；
- [ ] 每个 module/arm 的 exploration readiness 与 data/construct status 分离；
- [ ] claim ceiling 不夸大 direct/proxy/scope；
- [ ] terminal state 按优先级唯一裁决；
- [ ] manifest、output hashes、semantic hashes 与 checkpoint receipt 闭合；
- [ ] report 明确 22A 未验证任何 component outcome；
- [ ] tests、real-data validation、static checks 全部通过；
- [ ] validated attempt 为 `validated_working_result`，incomplete attempt 不冒充完成。

22A 完成后，允许的最大 handoff 是：

```text
selected module local implementation and historical exploration may continue
under a new versioned attempt without per-stage human approval
```

仍然：

```text
local downstream exploration allowed = true
per-stage human authorization required = false
historical support claim = false
forward support claim = false
decision router authorization = false
deployment authorization = false
```

---

## 20. Requirement review checklist

### 20.1 Scope

- [x] 只做共同 source/data/PIT/statistical contract；
- [x] 不读取 module outcome；
- [x] 不构造决策路由、仓位、回测或部署；
- [x] 允许在 EP22 范围内继续 22B–22H 探索，但不自动升级为生产或 forward support。

### 20.2 Source and timing

- [x] practitioner narrative 与 verified evidence 分开；
- [x] 文件存在与 PIT usable 分开；
- [x] 现有 PIT universe 是 baseline，不是数据上限；
- [x] 数据发现、试采和 usefulness evaluation 是一等研究方向；
- [x] observation/publication/availability/first-usable/revision 分开；
- [x] current industry/theme 禁止回填；
- [x] official index return 与 constituent membership 分开；
- [x] total shares 与 official free float 分开。

### 20.3 Estimand and statistics

- [x] M1–M6A/B 独立裁决；
- [x] M3A/M3B、M6A/M6B 为 sibling；
- [x] primary metric、baseline、inference unit、horizon 已有冻结方法；
- [x] split、purge、embargo、multiplicity 与 effect floor outcome-blind；
- [x] low power 不会被写成无效或有效。

### 20.4 M1

- [x] market shock 需要 magnitude + breadth；
- [x] breadth 明确为 `within_U_project`；
- [x] group expected response 只用 `<= t-1`；
- [x] market/group shock、pair state、episode 与 as-of panel 可复核；
- [x] group layer 未通过前，L3 必须作为独立 exploratory variant，不得掩盖 group failure；
- [x] G3-over-G2 与 EP20B-SRC-like comparator 已冻结；
- [x] price shock claim ceiling 固定为 proxy-only。

### 20.5 Governance

- [x] readiness、historical evidence 与 production authorization 分离；
- [x] stage/read whitelist 与 access audit 完整；
- [x] terminal-state precedence 明确；
- [x] iterative checkpoint、manifest、hash 与 attempt lineage 完整；
- [x] Definition of Done 可执行。

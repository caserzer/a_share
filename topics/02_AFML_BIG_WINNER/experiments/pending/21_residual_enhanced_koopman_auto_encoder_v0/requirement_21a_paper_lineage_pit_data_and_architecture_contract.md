# Requirement：21A 论文血缘、PIT 数据与 REAKA Architecture Contract

## 0. 不可协商范围

21A 是 EP21 当前唯一获授权生成的可执行 requirement；本次请求只生成 spec，不授权实现或执行。它只定义：

```text
paper source / formula / claim lineage
official code and appendix availability audit
PIT membership / timing / denominator contract
qfq / raw OHLCV / VWAP / volume-semantics audit
installed Alpha158 expression extraction and hash
feature-only sequence-support preflight
source / teacher / inference graph freeze
tensor-shape / gradient-flow / loss-reduction freeze
mandatory arm / nested-attribution / fairness freeze
chronological split / purge / holdout-firewall freeze
primary config / sensitivity / seed / search-accounting freeze
runtime dependency lock audit
synthetic-only GPU memory and graph dry-run
metric / margin / multiplicity / power freeze
21F comparator and deterministic-refit protocol freeze
immutable pre-outcome bundle and Chinese contract report
```

21A **不得训练或评价任何 outcome model**。禁止生成真实股票 score、读取或计算未来收益、RankIC、MSE、TopK return、PnL、
operator assignment、residual error、winner label、MFE/MAE 或任何 score-outcome join。真实市场数据只可用于 schema、lineage、
feature-only trailing-window coverage、PIT timing 和无 outcome 的 sequence-support 审计。

21A 的唯一成功状态是：

```text
decision_state = 21A_preoutcome_architecture_contract_ready
```

它只表示 paper-grounded project adaptation、PIT feature route、architecture graph、统计设计和可复现运行合同均已冻结；不表示模型
有预测力、论文结果已复现或任何策略可部署。成功后：

```text
next_allowed_requirement = requirement_21b_alpha158_sequence_baseline_benchmark.md
next_requirement_generation_authorized = true
next_requirement_execution_authorized = false
outcome_model_training_authorized = false
historical_holdout_readout_authorized = false
policy_training_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

Fail-closed states：

```text
21A_human_restart_or_scope_blocked
21A_paper_source_lineage_blocked
21A_alpha158_expression_contract_blocked
21A_feature_materialization_contract_blocked
21A_pit_timing_or_denominator_contract_blocked
21A_architecture_graph_or_shape_contract_blocked
21A_split_search_or_statistics_contract_blocked
21A_dependency_lock_or_gpu_contract_blocked
21A_outcome_firewall_violated
21A_manifest_or_hash_blocked
21A_contract_not_impl_ready
```

以下是非阻断 capability/status，不得误写成整个 21A 失败：

```text
official_code_not_disclosed_in_allowlisted_sources
paper_appendix_not_disclosed
exact_replication_not_reachable
alpha158_full_vwap_route_unavailable
alpha158_no_vwap_adaptation_selected
gpu_batch_size_mechanically_reduced
historical_sample_design_contaminated
forward_not_yet_observed
```

## 1. 身份、路径与执行阶段

```text
experiment_id = 21_residual_enhanced_koopman_auto_encoder_v0
phase_id = 21A
run_id = 21A_paper_lineage_pit_data_and_architecture_contract
contract_version = 21A_v2
requirement_file = requirement_21a_paper_lineage_pit_data_and_architecture_contract.md
config_file = configs/config_21a_paper_lineage_pit_data_and_architecture_contract.yaml
runner_file = src/run_21a_paper_lineage_pit_data_and_architecture_contract.py
test_file = tests/test_21a_paper_lineage_pit_data_and_architecture_contract.py
output_root = outputs/21A_paper_lineage_pit_data_and_architecture_contract_v2
```

`21A_v2` 是对已保留 `21A_v1` sealed bundle 的 fail-closed boundary amendment。v1 将数据最后一天
`2026-05-29` 的空 `usable_trade_date` 同时计为 U02 membership-integrity failure 与 U03 timing failure；但该日下一 exchange
session 尚未进入本地行情数据，按本 requirement 的 `RIGHT_CENSORED_DATA_CUTOFF` 应整日右删失。v2 只修正：

```text
U02 membership integrity = listed AND non-ST AND available by decision close AND nonempty instrument
U03 non-cutoff rows = usable_trade_date exactly equals next exchange session
U03 terminal cutoff rows = expected next session is after observed market-data max date
                           AND raw usable_trade_date is blank or equals expected next session
                           AND whole terminal day is RIGHT_CENSORED_DATA_CUTOFF
```

Cutoff exception 只能命中连续数据末端的完整 decision day；任何早于 observed market-data max date 的 blank/mismatch 仍使 U03 fail。
Right-censored rows保留 outcome-independent denominator/feature-support 血缘，但未来训练、RankIC 和交易回放必须整日
`not_evaluable`。v2 不改变论文公式、Alpha158 route、model arms、search budget、统计门或 execution contract。

执行工作目录：

```bash
cd topics/02_AFML_BIG_WINNER
```

21A 只允许三个 stage：

```text
acquire-sources
freeze
finalize
```

- 显式 dependency environment bootstrap 不是 runner stage；它只能按 Section 15.0 在任何 stage 前人工执行一次；
- 下列“只读/只写”均指 audit hook 启用后的 **stage data I/O**；interpreter/stdlib/runner/locked-package import 只允许走
  Section 15.0 的 hash-closed `process_bootstrap`，不能借 bootstrap 读取 config、论文、市场数据或 project metadata；
- `acquire-sources` 的 stage data I/O 只读 requirement/config、本地论文和 Section 6 URL allowlist，只写 `references/21a/`；不得读取市场数据；
- `acquire-sources` 生成 source manifest、formula review packet 和 draft registry，不产生研究 decision；
- `freeze` 只读 Section 5 白名单输入，做 pre-outcome contract/materialization/dry-run 审计，只写 `output_root/freeze/`；
- `freeze` 必须先写完整 artifacts，再事务性 seal manifest/hash；
- `finalize` 的唯一 data input 是已密封 freeze bundle，生成 root-level access audit、gate evidence、decision、中文报告、manifest 和
  output hashes；
- `finalize` 不得重读 PDF、市场数据、上游 artifact、环境 package metadata 或 GPU；
- 同一 `run_id + contract_version` 不得覆盖 sealed bundle；输入、requirement、config、dependency lock 或 formula authorization
  变化必须升级 version 并保留旧 bundle。

实现阶段允许新增本 requirement 明列的 config/runner/test 和显式 dependency declaration；runner 运行时不得静默执行
`pip install`、`uv add`、`uv lock` 或修改 source tree。

## 2. Human restart、planning authority 与上游真值

EP21 是人类明确发起的 architecture diagnostic，不是 EP20 自动 handoff。21A 必须冻结：

```text
episode_id = 21_residual_enhanced_koopman_auto_encoder_v0
restart_type = topic_level_human_restart_for_architecture_diagnostic
upstream_automatic_authorization = false
primary_claim_ceiling = paper_architecture_grounded_project_adaptation
historical_sample_role = design_contaminated_historical
historical_support_claim_allowed = false
support_source = post_final_candidate_seal_forward_only
```

Planning authority：

```text
EXPERIMENT_ROOT/research_plan.md
EXPERIMENT_ROOT/requirement_21a_paper_lineage_pit_data_and_architecture_contract.md
```

当前 research-plan identity 预期：

```text
research_plan_sha256_expected = cb3e45f874df5c632950a2586e45a4465e36b3e6c5d5cc65c0f7ff3118784c95
paper_sha256_expected = 1041d8693c5ef80fcafc613d77f09bf3ec2a2df673f468785255da27d7d9a472
paper_page_count_expected = 5
paper_doi = 10.1109/ICASSP55912.2026.11465125
```

若 research plan 在 21A 实现前有经过人工评审的修改，必须同时升级 `contract_version` 并在 requirement 中更新 expected hash；
runner 不得通过“接受任意新 hash”绕过 lineage gate。

EP19/EP20A 只提供以下上游合同事实：

- EP19：PIT membership、signal close / next-session usable、tradability、next-open、blocked fill/exit 与成本；
- EP20A：本地 qfq/raw/benchmark/security-master 的 pre-outcome schema/coverage audit 和 execution inheritance；
- 这些输出必须重新 hash；21A 不读取 EP19/EP20 的 outcome reports/tables；
- EP20A 的 `project_adaptation_reachable=true` 不能替代 EP21 自己的 Alpha158/VWAP/architecture readiness gate。

Required：

```text
freeze/human_restart_authorization.json
freeze/upstream_scope_and_lineage_audit.csv
```

`human_restart_authorization.json` 至少包含：

```text
episode_id
phase_id
contract_version
authorization_type
authorization_source
authorization_recorded_date = 2026-07-13
restart_type
upstream_automatic_authorization
research_plan_path
research_plan_sha256
research_plan_sha256_expected
requirement_path
requirement_sha256
primary_claim_ceiling
historical_sample_role
historical_support_claim_allowed
```

## 3. 21A 只回答的问题

```text
Q1. 本地 5 页 version-of-record 的身份、hash、公式、图、实验设置、未披露项和 claim ceiling 是否可审计？

Q2. 官方 conference/publisher 页面是否披露 appendix 或 official code；若未披露，能否明确保持 official_code_unavailable？

Q3. pyqlib 0.9.7 实际生成的 Alpha158 158 expressions、源码 hash 与本地字段映射是否可冻结？

Q4. qfq OHLC、raw money、raw-share volume 和 raw/qfq ratio 能否形成通过 range/unit 审计的 qfq VWAP；若不能，
    no-VWAP adaptation 是否可机械物化且不冒充 Alpha158-158？

Q5. membership_date=t、close-observed signal、usable_trade_date=t+1、U_t_decision 和整日 outcome-resolution contract
    是否能在不读取 label outcome 的条件下冻结？

Q6. full shifted-sequence source/teacher/inference graph、teacher isolation、gradient flow、tensor shape、loss reduction、
    score index 和 diffusion sampling 是否唯一可实现？

Q7. M0/M1/M2/M3/A0/K1/K1C/K2/R1/R2 的 nested role、共同样本/预算、公平性和 parameter-matching 是否可冻结？

Q8. chronological split、12-session purge、validation selection、historical holdout firewall、search budget、seeds、
    multiplicity、metric margins和 forward power 是否可机械化？

Q9. project dependency lock 是否包含 exact pyqlib/lightgbm/torch runtime，且 12GB GPU 是否能完成 synthetic-only
    full graph forward/backward/inference dry-run？

Q10. 21F 的 M1/M3 comparators、deterministic refit 和 static first cohort 是否在 historical outcome access 前冻结？
```

21A 不回答 Alpha158、Koopman、adaptive operator、MLP residual、diffusion 或 Top-30 是否有效。

## 4. Allowed / forbidden work 与 outcome firewall

### 4.1 允许工作

```text
1. Hash Section 5 的 planning、paper、dependency、PIT universe、OHLCV、calendar 和 pre-outcome upstream inputs。
2. 读取 header/dtype/row count/key uniqueness/date min/max/missingness/unit/source metadata。
3. 基于 trailing-only expressions 物化 feature-only Alpha158 cache 和 sequence-support counts。
4. 计算 raw/qfq same-date factor ratio、VWAP range/unit audit、factor-jump window row counts；不得连接未来收益。
5. 计算 membership/timing/history-ready/feature-ready counts，冻结 U_t_decision construction；不得汇总 label 值。
6. 用 synthetic tensors 执行 architecture shape、gradient、loss、determinism 和 GPU memory dry-run。
7. 冻结 paper formula、project adaptation、arm role、split、seed、search、metric、economic、power、forward-refit contracts。
8. 输出 machine-readable gates、immutable hashes 和中文 contract report。
```

### 4.2 禁止工作

```text
1. 不读取或生成 future return、LABEL0、Y_rank、Y_exec、MFE、MAE、winner、hit、pnl、nav-return、RankIC 或 score 字段。
2. 不实例化带默认 label 的 Alpha158 handler；21A 只能调用 feature-config extraction 或 feature-only loader。
3. 不使用 Ref(..., negative offset) 的 feature/label expression；Alpha158 registry 中的 feature expressions 必须 trailing/current-only。
4. 不 materialize close(t+1)/close(t)-1、Qlib gap label或 next-open return；只冻结公式字符串和 synthetic tests。
5. 不训练 LightGBM/LSTM/AE/Koopman/DDPM，不做 early stopping，不生成真实 score/checkpoint/operator assignment。
6. 不读取 historical holdout 的 outcome summary、论文 result 作为 threshold、EP19/EP20 outcome artifact 或任何策略报告。
7. 不按真实 feature coverage 删除某个 Alpha158 expression；只有 Section 8 的 deterministic VWAP route 可以改变 feature set。
8. 不根据 GPU dry-run 更改 latent width/operator count/diffusion steps；OOM 只能按冻结 batch fallback ladder 减 batch。
9. 不把 ambient Python package 当 dependency lock，不在 runner 内安装或升级 torch/qlib/lightgbm。
10. 不授权 21B 执行、policy、portfolio optimization 或 deployment。
```

### 4.3 数据字段与派生 firewall

市场输入允许字段：

```text
date / trade_date / membership_date / usable_trade_date / source_trade_date / source_asof_date
available_time / membership_available_time
instrument / ts_code / board_bucket / exchange / name
is_listed / is_st / is_suspended / listing_date / delist_date
board_rank_by_market_cap / board_quota / quota_fill_rate / total_market_cap_cny
history_ready_240d_flag / history_observed_sessions_before_usable_date / minimum_history_sessions
open / high / low / close / volume / money / turnover_rate
raw_unadjusted_close / source_volume_unit / source_turnover_unit
source_* / *_rule_version / *_status / *_reason
```

允许派生：

```text
row/file/instrument/date counts
date min/max
missing/finite/zero/negative rates
duplicate key count
same-date qfq/raw factor ratio
qfq VWAP candidate and OHLC range pass flag
factor-jump flag and trailing-window intersection flag
feature expression/value coverage
history/feature/sequence-ready flag using <= t only
split membership and purge counts
schema/artifact/root-inventory hashes
synthetic tensor/loss/gradient/memory values
```

Forbidden detector 必须大小写不敏感并覆盖嵌套/前后缀：

```text
label / target_value / future / forward_return / return_t_plus / y_rank / y_exec
rankic / icir / mfe / mae / winner / first_hit / pnl / realized_utility
score_outcome / topk_return / strategy_return / model_prediction
Ref($close,-1) / Ref($close,-2) or any negative-offset realized expression
```

`label_semantics_freeze.csv` 中作为**纯字符串合同**保存的三条公式是例外；它们不得被执行或连接真实 bar。任一实际 outcome read：

Forbidden scanner 扫描 market/upstream dataframe columns、feature-cache columns、derived runtime frame columns和执行过的 expression；
不把以下 schema metadata names本身计为 outcome read：

```text
label_semantics_freeze.csv: label_id,formula,role,materialized_in_21a,selection_allowed,status
decision_universe_and_label_resolution_contract.csv: status_id,trigger,valuation_rule,row_or_day_action
21A_contract_decision.csv: feature_label_alignment_gate,outcome_firewall_gate,outcome_model_training_authorized
gate_evidence_21a.csv: observed_value,required_value
```

这些 metadata fields 只允许 string/bool contract values，不得承载 instrument-date realized value。任何未列明 metadata exception 或任一
numeric/date-indexed outcome value仍使 detector fail。

```text
outcome_firewall_gate = fail
decision_state = 21A_outcome_firewall_violated
bundle_disposition = invalid_do_not_promote
```

## 5. 输入、路径别名与 hash

禁止硬编码 `/home/xiaolv/...`。所有路径 repository-relative 或从以下 alias 解析：

```text
REPO_ROOT = ../..
TOPIC_ROOT = .
EXPERIMENT_ROOT = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0
EP19_ROOT = experiments/pending/19_entry_universe_pit_tradability_preflight
EP20_ROOT = experiments/pending/20_ohlcv_positive_beta_exposure_research

PAPER_FILE = EXPERIMENT_ROOT/paper/Residual-Enhanced_Adaptive_Koopman_Autoencoder_A_Deep_Latent_Dynamics_Model_for_Stock_Prediction.pdf
REFERENCE_ROOT = EXPERIMENT_ROOT/references/21a

MEMBERSHIP_FILE = data/processed/universe/pit_topn_400_100_membership_daily.csv
EXECUTABLE_UNIVERSE_FILE = data/processed/universe/pit_topn_400_100_executable_daily.csv
UNIVERSE_INTERVAL_FILE = data/processed/universe/pit_topn_400_100_intervals.csv
QFQ_ROOT = data/raw/akshare/day/qfq
RAW_OHLCV_ROOT = data/raw/akshare/day/raw
BENCHMARK_FILE = data/processed/index/benchmark_indices_daily.csv
TRADING_CALENDAR_FILE = data/raw/akshare/status/trading_calendar.csv
SECURITY_MASTER_FILE = data/raw/akshare/status/instrument_metadata_target_universe.csv
NAME_HISTORY_ROOT = data/raw/akshare/status/sh_name_history

EP19_19A_OUTPUT_ROOT = EP19_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract
EP19_EXECUTION_FILE = EP19_19A_OUTPUT_ROOT/entry_execution_convention_audit.csv
EP19_COST_FILE = EP19_19A_OUTPUT_ROOT/replay_cost_assumption_freeze.csv
EP19_CENSOR_FILE = EP19_19A_OUTPUT_ROOT/censoring_treatment_freeze.csv
EP19_DECISION_FILE = EP19_19A_OUTPUT_ROOT/entry_universe_preflight_decision.csv
EP19_MANIFEST_FILE = EP19_19A_OUTPUT_ROOT/manifest_19a_entry_universe_pit_lineage_tradability_and_data_contract.json
EP19_HASHES_FILE = EP19_19A_OUTPUT_ROOT/output_hashes_19a_entry_universe_pit_lineage_tradability_and_data_contract.json

EP20_20A_OUTPUT_ROOT = EP20_ROOT/outputs/20A_paper_lineage_data_and_replication_contract
EP20_DECISION_FILE = EP20_20A_OUTPUT_ROOT/20A_preoutcome_contract_decision.csv
EP20_QFQ_AUDIT_FILE = EP20_20A_OUTPUT_ROOT/freeze/qfq_schema_unit_and_coverage_audit.csv
EP20_EXECUTION_AUDIT_FILE = EP20_20A_OUTPUT_ROOT/freeze/execution_and_cost_inheritance_audit.csv
EP20_FILL_RULE_FILE = EP20_20A_OUTPUT_ROOT/freeze/execution_fill_and_exit_rule_freeze.csv
EP20_LABEL_RULE_FILE = EP20_20A_OUTPUT_ROOT/freeze/label_completion_and_censoring_rule_freeze.csv
EP20_COST_CAPACITY_FILE = EP20_20A_OUTPUT_ROOT/freeze/turnover_cost_capacity_formula_freeze.csv
EP20_NAV_FILE = EP20_20A_OUTPUT_ROOT/freeze/stateful_portfolio_accounting_and_nav_freeze.csv
EP20_PRICE_LIMIT_FILE = EP20_ROOT/references/market_rules/a_share_price_limit_rules_v1.csv
EP20_MANIFEST_FILE = EP20_20A_OUTPUT_ROOT/manifest_20a_paper_lineage_data_and_replication_contract.json
EP20_HASHES_FILE = EP20_20A_OUTPUT_ROOT/output_hashes_20a_paper_lineage_data_and_replication_contract.json

PROJECT_PYPROJECT = pyproject.toml
PROJECT_REQUIREMENTS = requirements.txt
PROJECT_UV_LOCK = uv.lock
```

### 5.1 必需输入

```text
EXPERIMENT_ROOT/research_plan.md
EXPERIMENT_ROOT/requirement_21a_paper_lineage_pit_data_and_architecture_contract.md
EXPERIMENT_ROOT/configs/config_21a_paper_lineage_pit_data_and_architecture_contract.yaml
PAPER_FILE
MEMBERSHIP_FILE
EXECUTABLE_UNIVERSE_FILE
UNIVERSE_INTERVAL_FILE
QFQ_ROOT/*.csv
RAW_OHLCV_ROOT/*.csv
BENCHMARK_FILE
TRADING_CALENDAR_FILE
SECURITY_MASTER_FILE
EP19_EXECUTION_FILE
EP19_COST_FILE
EP19_CENSOR_FILE
EP19_DECISION_FILE
EP19_MANIFEST_FILE
EP19_HASHES_FILE
EP20_DECISION_FILE
EP20_QFQ_AUDIT_FILE
EP20_EXECUTION_AUDIT_FILE
EP20_FILL_RULE_FILE
EP20_LABEL_RULE_FILE
EP20_COST_CAPACITY_FILE
EP20_NAV_FILE
EP20_PRICE_LIMIT_FILE
EP20_MANIFEST_FILE
EP20_HASHES_FILE
PROJECT_PYPROJECT
PROJECT_REQUIREMENTS
PROJECT_UV_LOCK
REFERENCE_ROOT/source_availability_manifest.csv
REFERENCE_ROOT/paper_formula_registry_draft.csv
REFERENCE_ROOT/formula_review_packet.md
REFERENCE_ROOT/formula_review_authorization.json
```

`NAME_HISTORY_ROOT` 是 optional-but-audited；缺失不阻断 architecture contract，但关闭 confirmed terminal-price resolution
capability。任何额外输入必须在 config 的显式 allowlist 中；空列表写 `[]`，禁止 filesystem-wide 猜测。

### 5.2 Hash 规则

- 小文件逐文件 SHA-256；
- qfq/raw 两个 root 分别生成按相对路径排序的 `path|size|sha256` inventory，再对 UTF-8 bytes 做 root digest；
- paper 必须同时验证 SHA-256、PDF version 和 5-page count；
- research plan 必须匹配 Section 2 expected hash；
- upstream manifest/output-hashes 必须双向校验，不只检查文件存在；
- dependency audit 同时 hash `pyproject.toml`、`requirements.txt`、`uv.lock`；
- mtime、Git tracked 状态和文件数量不得替代 content hash；
- 计划中的“约 4,597 只”只用于 anomaly warning，不是 exact pass condition。

## 6. Paper source、公式与 claim ceiling

### 6.1 Acquire-sources allowlist

```text
local_pdf = PAPER_FILE
doi_resolver = https://doi.org/10.1109/ICASSP55912.2026.11465125
ieee_xplore = https://ieeexplore.ieee.org/document/11465125
official_conference_program = https://www.cmsworkshops.com/ICASSP2026/view_paper.php?PaperNum=6131
official_code_candidate_urls = []
official_appendix_candidate_urls = []
```

Runner 不做任意搜索引擎或 GitHub 全站搜索；只有人工在 config 明确加入、且 owner/author identity 可验证的 URL 才能成为
official-code candidate。第三方博客、论文求助站、ResearchGate 引用和非作者仓库只能记为 `third_party_unverified`，不得改变
official code 状态。

当 candidate lists 为空时，`official_code_availability_audit.csv` 仍必须输出一行 sentinel：

```text
candidate_id = NO_ALLOWLISTED_OFFICIAL_CODE_CANDIDATE
url = empty
code_disclosed = false
official_status = not_disclosed_in_allowlisted_sources
status = pass_nonblocking
```

零行 audit 不允许 pass。

### 6.2 `paper_source_registry.csv`

至少一行 `reaka_icassp_2026_vor`，schema：

```text
run_id
source_id
source_role
title
authors
venue
publication_year
doi
official_url
local_path
local_sha256
expected_sha256
page_count
version_status
full_text_available
appendix_status
official_code_status
retrieved_or_verified_at_utc
identity_gate
notes
```

身份必须冻结为 5 位作者：Lei Liao、Yang Zhang、Jun Wang、Jinghua Tan、Yinchao Liao。PDF/DOI/title/author 任一不一致，
`paper_source_lineage_gate=fail`。

### 6.3 Formula review packet 与 authorization

`acquire-sources` 输出：

```text
references/21a/source_availability_manifest.csv
references/21a/paper_formula_registry_draft.csv
references/21a/formula_review_packet.md
```

人工 review 后提供：

```text
references/21a/formula_review_authorization.json
```

authorization 至少包含：

```text
paper_sha256
formula_registry_draft_sha256
review_packet_sha256
reviewed_source_id
reviewed_formula_ids
page_anchor_verified
equation_or_figure_anchor_verified
reviewer_role = human
reviewed_at_utc
authorization_status
```

`freeze` 不得自行把 draft 升级为 verified。缺少 human authorization 时仍可产出 blocked bundle，但
`paper_formula_contract_gate=fail`。

### 6.4 `paper_formula_and_architecture_registry.csv`

每个 formula/claim 一行：

```text
run_id
formula_id
source_id
paper_page
paper_section
equation_figure_table_anchor
paper_claim_summary
paper_formula_canonical
input_symbols
output_symbols
paper_disclosed
paper_exact_or_project_choice
project_formula_canonical
project_adaptation_reason
implementation_owner_stage
primary_or_sensitivity
claim_ceiling
human_verified
status
```

至少覆盖：

```text
P01_INPUT_RETURN_AND_FEATURE_SEQUENCES
P02_DUAL_LSTM_ENCODERS
P03_SIGMOID_FEATURE_GATE
P04_LATENT_FUSION_Z_AND_Z_PLUS
P05_OPERATOR_CODEBOOK
P06_GUMBEL_SOFTMAX_SELECTOR
P07_SELECTED_KOOPMAN_PROPAGATION
P08_LATENT_RESIDUAL
P09_CONDITIONAL_DDPM_FORWARD_NOISE
P10_DDPM_EPSILON_LOSS
P11_REVERSE_RESIDUAL_SAMPLE
P12_RESIDUAL_ENHANCED_LATENT
P13_RETURN_DECODER
P14_L_REC_L_KOOP_L_DIFF
P15_T10_LOOKBACK
P16_RANKIC_AND_RANKICIR
P17_TOPK30_DIAGNOSTIC
A01_FULL_T_SHIFTED_SEQUENCE_INDEXING
A02_FINAL_STEP_SCORE_INDEX
A03_MEAN_LOSS_REDUCTION_AXES
A04_TEACHER_GRADIENT_AND_INFERENCE_ISOLATION
A05_EIGHT_DRAW_POINT_PREDICTION_MEAN
A06_PROJECT_PIT_UNIVERSE_AND_TIMING
```

公式 registry 禁止 `see paper`、空 page、空 anchor 或仅自然语言而无 canonical mapping。

### 6.5 Reproducibility gap 与 claim ceiling

`paper_reproducibility_gap_registry.csv` 至少覆盖：operator count、latent width、LSTM depth、Gumbel schedule、DDPM steps、
beta schedule、optimizer、batch size、normalization、seed、inference sampling、TopK rebalance、cost、official code 和 appendix。

每行：

```text
gap_id
paper_disclosure_status
local_evidence
frozen_project_choice
choice_source
sensitivity_allowed
exact_replication_impact
blocking_for_project_adaptation
status
```

固定结论：

```text
exact_replication_reachable = false
primary_claim_ceiling = paper_architecture_grounded_project_adaptation
paper_result_reproduced_claim_allowed = false
CSI300_result_reproduced_claim_allowed = false
REAKA_profitability_confirmed_claim_allowed = false
```

Official code/appendix 未披露是非阻断 gap；伪造官方仓库、把第三方代码写成官方或省略 gap 则阻断 paper contract。

## 7. PIT membership、timing、label 与 denominator contract

### 7.1 Signal-time universe

Primary raw membership universe：

```text
U_t_membership = rows in MEMBERSHIP_FILE
    where membership_date = decision_date t
```

`U_t_membership` 是纯 PIT membership denominator，不得提前应用 history、feature、suspension 或未来 outcome 条件。Membership
contract 的 `is_listed=true`、`is_st=false`、`usable_trade_date=next exchange session` 必须作为完整性断言验证；任一 member row
违反时 `pit_membership_timing_gate=fail`，不得静默过滤。`is_suspended` 不改变 membership；它只进入 Section 7.5 的 source-row
处理和未来 execution state machine。

`pit_membership_signal_execution_timing_audit.csv` 至少验证：

```text
(membership_date, instrument) uniqueness
membership_available_time <= decision close contract
usable_trade_date strictly after membership_date
usable_trade_date equals next exchange session
membership/executable row mapping uniqueness
board quota/rank fields present
no current-constituent backfill
qfq/raw filename overlap
```

Signal rows必须保留：

```text
decision_date
membership_date
membership_available_time
usable_trade_date
instrument
board_bucket
board_rank_by_market_cap
total_market_cap_cny
history_ready_240d_flag
membership_rule_version
```

CSI300 只能进入未来 descriptive regime context，不能成为 constituent filter。

### 7.2 Feature-ready denominator

```text
U_t_decision = U_t_membership
    AND is_listed = true
    AND is_st = false
    AND usable_trade_date = next exchange session after t
    AND history_ready_240d_flag = true
    AND all T=10 source rows exist under frozen suspension/missing policy
    AND required trailing Alpha158 warm-up is complete
    AND frozen primary feature route can produce finite-or-policy-imputed input
```

21A 只计算 `U_t_membership` 与 `U_t_decision` 的 counts/coverage；不得读取 `t+1` outcome 决定 row inclusion。
必须同时输出 `membership_n`、`membership_integrity_n`、`history_ready_n`、`sequence_ready_n`、`feature_ready_n` 和
`U_t_decision_n`，使每层 loss 可加总回上一层；不得把 history-not-ready row 从 `U_t_membership` count 中删除。

Minimum support：

```text
minimum_primary_cross_section_n = 100
minimum_complete_train_decision_days = 750
minimum_complete_validation_decision_days = 200
minimum_holdout_calendar_days_for_future_readout = 400
```

这些门只使用 feature/history/date coverage。任一 day 的 `U_t_decision < 100` 时，该日预先标为
`feature_support_not_evaluable`，不能在看 label 后恢复。

### 7.3 三种 return/label 语义仅作合同冻结

`label_semantics_freeze.csv` 固定：

```text
Y_rank_primary(t) = qfq_close(t+1) / qfq_close(t) - 1
Y_qlib_gap_diagnostic(t) = qfq_close(t+2) / qfq_close(t+1) - 1
Y_exec_1d(t) = qfq_open(next_session_after_entry) / qfq_open(entry_session) - 1
entry_session = usable_trade_date = t+1
```

Roles：

```text
Y_rank_primary = future training/evaluation target; not executable PnL
Y_qlib_gap_diagnostic = frozen-score timing sensitivity only; no retraining/selection
Y_exec_1d = future economic bridge only
```

21A 不执行这些公式。Unit tests 必须使用 synthetic bars，真实数据 derivation count 必须为 0。

### 7.4 Outcome-resolution contract

`decision_universe_and_label_resolution_contract.csv` 必须冻结：

```text
NORMAL_NEXT_SESSION_CLOSE
LISTED_SUSPENDED_CARRY
CONFIRMED_TERMINAL_PRICE
UNKNOWN_DATA_GAP
RIGHT_CENSORED_DATA_CUTOFF
```

Rules：

```text
NORMAL_NEXT_SESSION_CLOSE -> next exchange-session qfq close
LISTED_SUSPENDED_CARRY -> close(t) carry, return 0
CONFIRMED_TERMINAL_PRICE -> only auditable official terminal/settlement price
UNKNOWN_DATA_GAP -> whole decision day not_evaluable_data_integrity
RIGHT_CENSORED_DATA_CUTOFF -> whole decision day right-censored
```

Future requirement 必须满足：

```text
U_t_resolved == U_t_decision for a primary RankIC day
all mandatory arms score exactly U_t_decision
no per-arm or score/label intersection denominator
model score missing -> coverage/pipeline failure
```

21A 只冻结 rule table 和 synthetic state-machine tests，不统计真实 historical resolution status。

### 7.5 Sequence missing/suspension policy

Primary 固定：

```text
source_sequence_length = 10
source_sequence_end = decision_date t
non-exchange-calendar gap = not a missing row
listed suspension with no print inside source sequence = carry last qfq OHLC mark; volume=0; money=0; suspension indicator=1
unknown provider gap = sequence invalid
prelisting row = unavailable; never impute
future row fill = forbidden
```

Suspension indicator 必须作为 missingness/status audit 字段，但不得改变 Alpha158 expression count。为保持 research plan 的
`x_source=[B,T,158]`，primary 固定为 `status_indicator_direct_model_input=false`；所有 arms 共享同一 carry/imputation policy。
任何直接加入 status/missing indicator 的模型只能另列 sensitivity，不能替代 primary 或进入 C0–C4。

## 8. qfq/raw、VWAP、Alpha158 与 feature normalization

### 8.1 qfq/raw schema and unit audit

Required qfq fields：

```text
date, open, high, low, close, volume, money, turnover_rate, instrument,
source_volume_unit, source_turnover_unit
```

Required raw fields 至少同 key 的 raw OHLC、volume、money。Audit：

```text
(instrument,date) unique
open/high/low/close finite and nonnegative
high >= max(open,low,close)
low <= min(open,high,close)
volume unit normalized to shares exactly once
money unit CNY
turnover ratio/percent detected then normalized by frozen rule
qfq/raw calendar and key overlap
```

`source_volume_unit=hands` 时只允许 `shares=hands*100`；已是 `shares` 时禁止再次乘 100。Unit unknown 时相关 file/status fail。

### 8.2 qfq factor 与 VWAP primary route

Same-date candidate：

```text
factor_close = qfq_close / raw_close
factor_open  = qfq_open  / raw_open
factor_high  = qfq_high  / raw_high
factor_low   = qfq_low   / raw_low
factor_consensus = median(valid factor_open/high/low/close)
vwap_raw = raw_money / raw_volume_shares
vwap_qfq_candidate = vwap_raw * factor_consensus
```

单个 factor field只有 raw/qfq对应 OHLC均 finite positive时 valid。至少3个 factor fields valid才计算 median；cross-field pass iff
`max(abs(factor_field/factor_consensus-1)) <= 1e-4`。少于3个 valid fields记 `unknown`，不得进入 pass denominator或被当0。

Frozen thresholds：

```text
factor_cross_field_relative_tolerance = 1e-4
vwap_range_tolerance = max(0.01 CNY, 0.001 * qfq_close)
minimum_factor_cross_field_pass_rate = 0.995
minimum_vwap_inside_qfq_range_rate = 0.995
minimum_qfq_raw_key_overlap_rate = 0.99
minimum_vwap_auditable_row_rate_global = 0.95
minimum_vwap_auditable_row_rate_board_year = 0.90
minimum_board_year_base_rows_for_gate = 100
```

VWAP coverage denominator 先固定：

```text
vwap_audit_base_row = qfq/raw overlapped key
    and finite positive raw/qfq OHLC
vwap_auditable_row = vwap_audit_base_row
    and raw_volume_shares > 0
    and finite raw_money > 0
vwap_auditable_row_rate = count(vwap_auditable_row) / count(vwap_audit_base_row)
factor_cross_field_pass_rate = count(base rows with factor pass) / count(vwap_audit_base_row)
qfq_raw_key_overlap_rate = count(qfq keys intersect raw keys) / count(qfq keys)
vwap_inside_range_rate = in_range_n / auditable_row_n
```

只有 `vwap_auditable_row` 进入 range pass-rate denominator。Global coverage 必须 `>=0.95`；任一 base rows `>=100` 的
board-year slice 必须 `>=0.90`。小于 100 rows 的 slice 标 `not_evaluable_small_slice`，但仍计入 global denominator。
任一 global denominator为0时对应 rate留空且 full route不可达，禁止填0后误判。
`vwap_qfq_unit_and_range_audit.csv` 必须按 instrument/year/board 与全局输出 base/auditable/pass/fail/unknown counts；不得只给
aggregate，也不得以缩小 range denominator 隐藏 zero/invalid volume-money coverage。

Feature route selection 只按 pre-outcome audit：

```text
if factor/range/unit/auditable-coverage gates pass:
    primary_feature_route_id = ALPHA158_QFQ_VWAP_FULL
    primary_feature_route_class = canonical_full_route
    alpha158_exact_local_materialization = true
else if all non-VWAP expressions are materializable:
    primary_feature_route_id = ALPHA158_NO_VWAP_REGISTERED_ADAPTATION
    primary_feature_route_class = registered_primary_route_adaptation
    alpha158_exact_local_materialization = false
else:
    feature_materialization_route_gate = fail
```

Route selection 不得读取 feature-outcome 关系。No-VWAP route 必须从 canonical expressions 中机械删除直接或传递引用 `$vwap` 的项，
输出保留 feature count/hash，名称不得包含 `Alpha158-158`。若该 route 按上述 precedence 被选择，它就是本 run 唯一 primary feature
route，必须被全部 mandatory arms、C0-C4 和 economic replay 共同使用；不得在训练失败或看到 validation/holdout outcome 后切回 full
route、混用两条 route 或把它降为 optional diagnostic。

### 8.3 Canonical Alpha158 extraction

必须从 locked `pyqlib==0.9.7` source 运行：

```text
fields, names = Alpha158.get_feature_config(None)
```

这是 unbound feature-only method call；不得实例化 `Alpha158.__init__`，也不得直接调用一个手写 conf 的 `Alpha158DL`。必须 hash
`qlib/contrib/data/handler.py` 和该 method source，并验证返回 `(fields,names)` 长度/顺序一致。禁止手写近似 expressions。Registry：

```text
feature_index
feature_name
expression
direct_fields
max_trailing_window
uses_vwap
uses_volume
uses_money
uses_future_offset
qlib_distribution_version
qlib_source_file
qlib_source_file_sha256
canonical_order
route_inclusion_full
route_inclusion_no_vwap
status
```

Hard gates：

```text
locked_pyqlib_version == 0.9.7
canonical_full_expression_count == 158
duplicate_feature_name_count == 0
future_offset_expression_count == 0
expression_list_sha256 is nonempty and stable
feature loader label config absent
```

`alpha158_expression_hash.txt` bytes 固定为：

```text
SHA256(UTF8(join("\n", [feature_index + "|" + feature_name + "|" + expression]))) + "\n"
```

### 8.4 Volume corporate-action semantics

Primary：

```text
volume_primary_semantics = raw shares after exactly-once hands-to-shares normalization
volume_factor_adjustment = forbidden
factor_jump_threshold_abs_log = 1e-4
factor_jump_quarantine_radius_sessions = 60
```

`alpha158_volume_corporate_action_audit.csv` 只计算 factor jump 和 trailing feature-window exposure counts。未来
`alpha158_factor_jump_window_quarantine_sensitivity` 删除任何 source sequence/maximum feature window 与 ±60-session jump window
相交的 sample；它是 sensitivity，不替换 primary，不按 outcome 决定 radius。

### 8.5 Feature-only materialization 与 normalization

21A 可以生成临时/缓存 feature values用于 coverage，但：

- expression 使用 bar `<= feature_date`；
- loader 不得包含 label；
- primary historical transform 为 original-train fitted robust center/scale；
- robust center=`median`，scale=`IQR/1.349`，scale<=`1e-12` 的列标 constant；
- transform order固定为：在 original-train finite values拟合 median/IQR；invalid raw value先填 train median；
  `z=(filled-median)/max(IQR/1.349,1e-12)`；最后 clip `[-10,10]`；constant column全部输出0；
- missing indicator在填充值前计算并输出audit，但 primary不作为direct input；
- return sequence 保持 raw qfq one-step close return，不做 decision-date CS target normalization；
- validation/holdout 只 apply original-train transform；
- final refit 可按 Section 14 重新拟合一次，随后 forward 静态 apply；
- decision-date CS-rank transform 仅注册为 sensitivity，不进入 primary。

任一 retained feature 的 original-train finite count为0时 `feature_materialization_route_gate=fail`；finite count>0但
`IQR/1.349<=1e-12` 时按 constant-column rule输出0，不得删除该 feature。

21A 不需要发布大型 feature panel，只输出 `feature_sequence_support_audit.csv` 和 cache manifest/hash；任何临时 cache 必须位于
ignored local cache，不能成为 freeze bundle 的未审计输入。

## 9. Source / teacher / inference graph、shape 与 loss contract

### 9.1 Sample indexing

每个未来训练 sample 的 forecast origin 是 decision close `t`：

```text
source_dates          = [t-T+1, ..., t]
teacher_shifted_dates = [t-T+2, ..., t+1]  # train only
T = 10
score_index = decoded_shifted[:, -1]
```

21A 只用 synthetic dates/tensors 验证 indexing；不得用真实 `t+1` row 实例化 teacher。

### 9.2 Source-only inference graph 与 train-only teacher path

`train_teacher_inference_graph_contract.csv` 必须逐 node/edge 冻结：

Source-only inference forecast graph：

```text
x_source, y_source
  -> dual LSTM encoder / sigmoid gate
  -> Z_source[1:T]
  -> state-conditioned selector[1:T] and K_selected[1:T]
  -> Z_hat_shifted[1:T]
  -> residual reverse chain(condition=Z_source[1:T], inference_noise)
  -> Z_tilde_shifted[1:T]
  -> return decoder
  -> decoded_shifted[1:T]
  -> score_next = decoded_shifted[T]
```

Train-only teacher/target/noising graph：

```text
x_teacher_shifted, y_teacher_shifted
  -> shared dual encoder / gate
  -> Z_teacher_shifted[1:T]
  -> residual_target = Z_teacher_shifted - Z_hat_shifted
  -> x_s train-only noisy residual input
  -> epsilon_hat(condition=Z_source, noising_input=x_s)
  -> R_hat_train_shifted
  -> Z_tilde_train_shifted
  -> decoded_shifted_train
  -> train-only L_rec/L_diff
```

Teacher 因此**允许**成为 `residual_target`、`x_s`、training reconstruction 和 training loss 的祖先；`x_s` 是 train-only noising
input，不是 selector/gate/DDPM conditioning context。上述允许边不得出现在 validation/test/inference graph。

Hard isolation：

```text
teacher value -> L_koop target/loss             allowed train-only
teacher value -> residual_target -> x_s         allowed train-only
teacher value -> selector input                 forbidden
teacher value -> GateNet source input           forbidden
teacher value -> residual conditioning context  forbidden
teacher value -> decoder skip/concat            forbidden
teacher value -> inference function signature   forbidden
teacher value -> any inference-score ancestor   forbidden
L_koop gradient -> shared teacher encoder        required for primary
```

Perturbing synthetic teacher tensors while holding source/RNG fixed may change only the enumerated train-only target/noising/reconstruction/loss
path，but must not change inference graph structure or score。
Inference graph source code/trace must contain no teacher placeholder or future-date field。

### 9.3 Tensor shape contract

`tensor_shape_contract.csv` 必须逐 tensor 保存 producer、consumer、dtype、train/inference availability 和 exact shape：

```text
y_source:          [B, T, 1]
x_source:          [B, T, D_x]
D_x:               158 for full route; frozen retained count for registered primary no-VWAP route adaptation
H_y_source:        [B, T, d]
H_x_source:        [B, T, d]
Z_source:          [B, T, d]
Z_t:               [B, d]

y_teacher_shifted: [B, T, 1]       # train only
x_teacher_shifted: [B, T, D_x]     # train only
Z_teacher_shifted: [B, T, d]       # train only, gradient-enabled primary

selector_source:   [B, T, N]
K_codebook:        [N, d, d]
K_selected:        [B, T, d, d]
Z_hat_shifted:     [B, T, d]
R_target_shifted:  [B, T, d]       # train teacher target only

ddpm_x_s:                  [B, T, d]       # R2 train only
ddpm_epsilon:              [B, T, d]       # R2 train only
ddpm_epsilon_hat:          [B, T, d]       # R2 train only
R_hat_train_shifted:       [B, T, d]       # R2 train only
Z_tilde_train_shifted:     [B, T, d]       # R2 train only
R_hat_inference_draws:     [B, 8, T, d]    # R2 inference only
Z_tilde_inference_draws:   [B, 8, T, d]    # R2 inference only

R_hat_mlp_shifted:         [B, T, d]       # R1
Z_tilde_mlp_shifted:       [B, T, d]       # R1

decoded_source:    [B, T]
decoded_shifted_train:     [B, T]
decoded_shifted_draws:     [B, 8, T]
direct_score_M2:           [B]
direct_score_M3:           [B]
direct_score_A0:           [B]
score_draws_R2:            [B, 8]
score_next:        [B]
```

禁止 implicit broadcasting 改变 batch/time/latent 语义。`K_selected @ Z_source` 必须通过显式 einsum/batched matmul unit test。
Canonical orientation 是
`Z_hat_shifted[b,t,i] = sum_j K_selected[b,t,i,j] * Z_source[b,t,j]`；禁止转置 K 或使用 row-vector right multiply。
Full route 的 `D_x != 158` 或 primary 只计算最后 transition 时，`architecture_shape_gate=fail`。

### 9.4 Encoder、gate 与 selector canonical contract

```text
H_y = LSTM_y(y_source)
H_x = LSTM_x(x_source)
GateNet_logits = Linear_gate(H_x)
G = sigmoid(GateNet_logits)
Z_source = H_y * G + H_x * (1-G)

selector_logits = LeakyReLU(W_selector concat[Z_source, H_y])
selector_train = GumbelSoftmax(selector_logits, tau, differentiable=true)
selector_inference = one_hot(argmax(selector_logits))
K_selected = sum_n selector[...,n] * K_codebook[n]
Z_hat_shifted = K_selected @ Z_source
```

Train selector exact：

```text
u = Uniform(0,1) from gumbel_seed stream, clamped to [1e-10,1-1e-10]
g = -log(-log(u))
selector_train = softmax((selector_logits + g) / tau, dim=operator)
```

上式是 K2/R1/R2 的 per-cell state-dependent selector。K1C 必须使用以下 override，不能复用 `[B,T,N]` independent Gumbel draws：

```text
K1C_context = ones[1,128] non-trainable buffer
K1C_global_logits = LeakyReLU(W_selector(K1C_context))[0]       # [N]

# training: exactly one operator-length draw per optimizer step, shared by all valid rows/cells
u_global = Uniform(0,1,size=[N]) from gumbel_seed stream, clamped to [1e-10,1-1e-10]
g_global = -log(-log(u_global))
K1C_selector_train_global = softmax((K1C_global_logits + g_global) / tau, dim=operator)
K1C_selector_train[b,t,:] = K1C_selector_train_global for every valid (b,t)

# inference: deterministic global hard selection, also shared by every row/cell
K1C_selector_inference_global = one_hot(argmax(K1C_global_logits), tie=smallest_operator_index)
K1C_selector_inference[b,t,:] = K1C_selector_inference_global for every valid (b,t)
```

K1C 的 expand 只能是无新随机数的 view/copy；训练与推断都必须逐元素验证跨 batch/time mixture 相等。它可以随 optimizer step
更新 global logits、随 frozen tau schedule 改变 soft weights，但不能读取 row、instrument、date、`Z_source` 或 `H_y`。

Inference 不采样；`argmax` tie 固定选择最小 operator index。禁止 straight-through/hard training primary。

Primary train uses soft differentiable Gumbel weights; hard/straight-through train 只能注册 sensitivity。Inference 必须 hard argmax；
historical outcome 后不得切换。

#### 9.4.1 Frozen module topology and initialization

论文未披露的实现细节固定为 project choices：

```text
return_encoder = unidirectional LSTM(input=1, hidden=64, layers=1, dropout=0, batch_first=true)
feature_encoder = unidirectional LSTM(input=D_x, hidden=64, layers=1, dropout=0, batch_first=true)
Linear_gate = Linear(64,64); sigmoid is applied exactly once outside the module
selector = Linear(concat[Z,H_y]=128, N) followed by LeakyReLU(0.01)
decoder = Linear(64,1)
M2_direct_head = Linear(64,1)
M3_direct_head = Linear(64,1)
A0_direct_head = Linear(64,1)

DDPM_timestep_embedding = sinusoidal, dim=32
DDPM_denoiser_input = concat[x_s(64), condition_Z(64), timestep_embedding(32)]
DDPM_denoiser = Linear(160,128) -> SiLU -> Linear(128,128) -> SiLU -> Linear(128,64)
```

两个 LSTM 的 initial hidden/cell state均为 per-sample zeros；禁止跨 batch、instrument或date carry recurrent state。

For integer `s in 1..S` and `i in 0..15`：

```text
timestep_embedding[s,2i]   = sin(s / 10000^(2i/32))
timestep_embedding[s,2i+1] = cos(s / 10000^(2i/32))
```

Embedding dtype/device跟随 fp32 residual tensor，无 learned projection、normalization 或 frequency rescaling。

R1 MLP receives `Z_source` and predicts residual directly：

```text
R1_residual_mlp(w) = Linear(64,w) -> SiLU -> Linear(w,w) -> SiLU -> Linear(w,64)
R_hat_mlp_shifted = R1_residual_mlp(Z_source)                 # [B,T,d]
Z_tilde_mlp_shifted = Z_hat_shifted + R_hat_mlp_shifted
```

Hidden width从 `[128,160,192,224,256]` 中机械选择使 trainable parameter count最接近 R2 denoiser，tie 取较小 width。该选择只依赖
parameter count，不能读取 outcome。

Initialization：

```text
Linear weights = Xavier uniform; bias = 0
LSTM input weights = Xavier uniform
LSTM recurrent weights = orthogonal
LSTM forget-gate bias = 1; all other bias = 0
K_codebook[n] = Identity + Normal(0, 0.01) using weight_init_seed
K1C constant selector context = non-trainable ones[128] buffer
```

M1 LightGBM project config：

```text
objective = regression_l2
learning_rate = 0.05
num_leaves = 31
max_depth = -1
min_data_in_leaf = 20
feature_fraction = 1.0
bagging_fraction = 1.0
lambda_l1 = 0.0
lambda_l2 = 0.0
max_boosting_rounds = 100
early_stopping_rounds = 10
deterministic = true
force_col_wise = true
num_threads = 1
verbosity = -1
```

M1 的 `seed/feature_fraction_seed/bagging_seed/data_random_seed` 均等于当前 `model_seed`；使用同一三 seed registry，best-seed
LightGBM 不能替代 ensemble。

### 9.5 Residual DDPM 与 point prediction

```text
R_shifted = Z_teacher_shifted - Z_hat_shifted
x_s = sqrt(alpha_bar_s) * R_shifted + sqrt(1-alpha_bar_s) * epsilon
epsilon_hat = epsilon_theta(x_s, s, Z_source)
L_diff = Mean((epsilon_hat - epsilon)^2)
R_hat_train_shifted = (x_s - sqrt(1-alpha_bar_s) * epsilon_hat) / sqrt(alpha_bar_s)
Z_tilde_train_shifted = Z_hat_shifted + R_hat_train_shifted
decoded_shifted during R2 training = Decoder(Z_tilde_train_shifted)
```

`L_rec` 的 R2 training path 只使用上述同一 sampled timestep 的 differentiable `R_hat_train_shifted`，不在每个 optimizer step内
运行20-step reverse chain，也不得把真实 `R_shifted` 直接加回 forecast path。Full reverse chain只用于 validation/test/inference score。

Exact DDPM project sampling contract：

```text
S = 20
beta_s = linspace(1e-4, 2e-2, S)[s], s in 1..S
alpha_s = 1 - beta_s
alpha_bar_s = product_{j=1..s}(alpha_j)
alpha_bar_0 = 1
posterior_variance_s = beta_s * (1-alpha_bar_{s-1}) / (1-alpha_bar_s)

training timestep s is sampled independently and uniformly from {1..S} per valid (batch,time) cell
epsilon ~ Normal(0,I) with exact residual tensor shape

inference x_S ~ Normal(0,I)
for s = S..1:
    epsilon_hat = epsilon_theta(x_s, s, Z_source)
    mu = (x_s - beta_s/sqrt(1-alpha_bar_s) * epsilon_hat) / sqrt(alpha_s)
    if s > 1:
        z_s ~ Normal(0,I)
        x_{s-1} = mu + sqrt(posterior_variance_s) * z_s
    else:
        x_0 = mu
R_hat_shifted = x_0
```

Primary 不做 residual clipping、dynamic thresholding、DDIM、learned variance 或 eta adjustment。每个 stable row-key seed初始化一个独立
`torch.Generator`，并以固定 `[x_S,z_S,...,z_2]`、C-contiguous `[T,d]` draw order消费随机数；不得共享 batch-global inference RNG。

Primary point prediction：

```text
inference_residual_draws = 8
draw_aggregation = arithmetic_mean_of_decoded_score
single_draw_primary = false
draw_seed_independent_of_batch_order = true
```

每个 draw seed：

```text
uint64_prefix(SHA256(run_id|arm_id|model_seed|instrument|decision_date|draw_id)) mod 2^63
```

字符串使用 UTF-8；分隔符是单字节 `|`；`instrument` 使用 canonical uppercase `SH/SZ/BJ` prefix；date 使用 `YYYY-MM-DD`；
`uint64_prefix` 是 digest 前 8 bytes 的 unsigned big-endian integer。

21A synthetic test 用 `synthetic_instrument_id`；未来真实 inference 必须使用 stable row key，不得用 dataloader position。

### 9.6 Exact loss reduction

```text
L_source_rec = MeanValid((Decoder(Z_source) - y_source_raw)^2)
L_shifted_observed_rec = MeanValid_j<T((decoded_shifted[j] - y_teacher_shifted_raw[j])^2)
L_history_reconstruction = 0.5 * (L_source_rec + L_shifted_observed_rec)
L_forecast = MeanBatch((decoded_shifted[T] - Y_rank_primary_raw(t))^2)
L_rec = L_history_reconstruction + L_forecast

L_koop = MeanValid_B,T,D((Z_teacher_shifted - Z_hat_shifted)^2)
L_diff = MeanValid_B,T,D,noise((epsilon_hat - epsilon)^2)
L_total_R2 = 1.0 * L_rec + 1.0 * L_koop + 1.0 * L_diff
```

“MeanValid” 顺序固定为：对 element/latent 求 mean，再对 valid batch/time cell 求 mean。禁止 time sum、先按样本长度加权或将
`L_forecast` 作为第四个 top-level loss 再加一次。

### 9.7 Synthetic graph tests

`gradient_flow_and_teacher_isolation_audit.csv` 至少覆盖：

```text
source_encoder_receives_gradient_from_L_rec
source_encoder_receives_gradient_from_L_koop
teacher_shared_encoder_receives_gradient_from_L_koop
selector_receives_no_direct_teacher_input
residual_condition_receives_no_teacher_value
inference_signature_has_no_teacher_tensor
teacher_perturbation_does_not_change_fixed_source_inference_score
all_T_transitions_contribute_to_L_koop
loss_mean_invariant_to_exact_batch_duplication
score_index_is_last_shifted_scalar
train_and_inference_score_shape_match
NaN_and_inf_fail_closed
```

## 10. Mandatory arms、nested attribution 与公平性

### 10.1 Arm registry

`model_arm_registry.csv` 必须包含且只将以下 10 个 arm 标为 mandatory：

| arm_id | 输入/结构 | Future role |
|---|---|---|
| `M0_HASH_NULL_SCORE` | stable hash(`instrument`,`decision_date`) | pipeline/null sanity；不训练 |
| `M1_LIGHTGBM_ALPHA158` | decision-date Alpha features | non-sequence strong baseline |
| `M2_RETURN_LSTM` | return T-sequence | paper w/o gating baseline |
| `M3_GATED_DUAL_PATH_LSTM` | return + Alpha dual LSTM/gate, direct head | primary direct-sequence comparator |
| `A0_VANILLA_AUTOENCODER` | dual encoder/decoder, no Koopman/residual | vanilla AE ablation |
| `K1_SINGLE_KOOPMAN_AE` | one Koopman matrix | fixed latent dynamics comparator |
| `K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL` | K2-sized codebook/selector, constant context | capacity-matched nonadaptive control |
| `K2_ADAPTIVE_KOOPMAN_AE` | state-dependent multi-operator AKS | adaptive dynamics test |
| `R1_AKS_MLP_RESIDUAL` | K2 + parameter-matched MLP residual | generic residual comparator |
| `R2_REAKA_DIFFUSION` | K2 + conditional DDPM residual | full project adaptation |

Registry columns：

```text
arm_id
mandatory
paper_reported_or_project_control
input_feature_route
uses_return_sequence
uses_feature_sequence
uses_gate
operator_mode
selector_context
residual_mode
loss_terms
score_head
primary_comparator_role
parameter_match_target
historical_stage
forward_eligible
claim_if_pass
claim_if_fail
```

GRU/TCN/ADGATs/FactorVAE/MASTER 缺失不阻断 21A，且不得加入 mandatory family。外部 comparator 以后只有独立 requirement
明确授权且不扩大 outcome-driven search 才可加入。

### 10.2 Per-arm loss and score

`per_arm_loss_and_score_index_contract.csv` 固定：

```text
M0: no train graph; deterministic outcome-independent hash score
M1: LightGBM regression_l2 on x_source[:,T-1,:]; tabular decision-date score
M2: H_y_source[:,T-1,:] -> M2_direct_head -> score; L_forecast_direct
M3: Z_source[:,T-1,:] -> M3_direct_head -> score; L_forecast_direct
A0: Z_source -> decoder for source reconstruction; Z_source[:,T-1,:] -> A0_direct_head -> score;
    L_A0_source_rec + L_forecast_direct; no teacher/Koopman/residual node
K1: one K matrix -> Z_hat_shifted -> decoder; L_rec + L_koop; last decoded shifted score
K1C: state-independent global mixture -> Z_hat_shifted -> decoder; L_rec + L_koop; last decoded shifted score
K2: state-dependent selector -> Z_hat_shifted -> decoder; L_rec + L_koop; last decoded shifted score
R1: K2 graph -> R_hat_mlp_shifted -> Z_tilde_mlp_shifted -> decoder;
    L_rec_mlp + L_koop + L_residual_mlp; last decoded shifted score
R2: K2 graph -> DDPM residual draws -> Z_tilde_shifted -> decoder;
    L_rec + L_koop + L_diff; mean of eight last decoded shifted scores
```

全部可学习 arms 的 forecast target、raw-return scale、sample rows、split 和 score date 相同。M0 不能进入 positive baseline gate。

Exact arm losses：

```text
L_forecast_direct(head, state) = MeanBatch((head(state[:,T-1,:]) - Y_rank_primary_raw(t))^2)
L_A0_source_rec = MeanValid((Decoder(Z_source) - y_source_raw)^2)

R_target_shifted = Z_teacher_shifted - Z_hat_shifted
L_residual_mlp = MeanValid_B,T,D((R_hat_mlp_shifted - R_target_shifted)^2)

decoded_mlp_shifted = Decoder(Z_tilde_mlp_shifted)
L_shifted_observed_rec_mlp = MeanValid_j<T((decoded_mlp_shifted[j] - y_teacher_shifted_raw[j])^2)
L_history_reconstruction_mlp = 0.5 * (L_source_rec + L_shifted_observed_rec_mlp)
L_forecast_mlp = MeanBatch((decoded_mlp_shifted[T] - Y_rank_primary_raw(t))^2)
L_rec_mlp = L_history_reconstruction_mlp + L_forecast_mlp
L_total_R1 = 1.0 * L_rec_mlp + 1.0 * L_koop + 1.0 * L_residual_mlp
```

M0 score bytes/数值映射唯一化：

```text
canonical_key = "M0_HASH_NULL_SCORE|" + canonical_instrument + "|" + YYYY-MM-DD(decision_date)
digest = SHA256(UTF8(canonical_key))
u64 = unsigned_big_endian_integer(digest[0:8])
score = u64 / 2^64                                      # [0,1)
```

禁止使用 Python `hash()`、row position、filesystem order 或 run-time RNG。M1 custom validation metric必须按 Section 14 的完整
decision-day denominator计算；LightGBM built-in row-level L2只能作为优化 objective，不能替代 frozen early-stopping metric。

### 10.3 Capacity matching

```text
K1C codebook count/shape = K2 codebook count/shape
K1C selector network parameterization = K2 selector-sized parameterization
K1C selector input = non-trainable ones[128] context, never Z/H_y/instrument/date
K1C train mixture weights = one shared Gumbel draw and identical across all valid batch/time rows per optimizer step
K1C inference mixture weights = deterministic hard argmax and identical across all batch/time rows
K1C trainable parameter count = K2 trainable parameter count exactly

R1 residual MLP parameter count target = R2 denoiser trainable parameter count
parameter_match_relative_tolerance = 0.10
primary_R2_denoiser_parameter_n = 45376
primary_R1_hidden_width = 160
primary_R1_residual_parameter_n = 46464
primary_R1_vs_R2_absolute_delta = 1088
primary_R1_vs_R2_relative_delta = 1088 / 45376 = 0.0239774321
```

若无法在 ±10% 内匹配，必须记录 absolute/relative delta；相关 C2b 或 C4 mechanism attribution 自动降级，但 predictive C1
仍可评价。不得通过扩大 K2/R1 隐藏匹配失败。

### 10.4 Fair-comparison freeze

所有 arms 共享：

```text
PIT rows and split IDs
primary feature route and tensor
primary label timing
normalization / missing / suspension policy
neural-arm maximum epochs/data-pass ceiling=100; M1 maximum boosting rounds=100
early-stopping metric and patience where applicable
seed list
score-to-Top30 mapping
execution / cost replay
```

未来每个 arm 必须输出 parameter count、GPU time、peak memory、epochs、data passes、inference latency 和 score coverage。
M1 boosting round不冒充 neural epoch；compute不是matched estimand，必须分列报告，不得据此形成mechanism attribution。

## 11. Primary config、search budget 与 randomness

### 11.1 Frozen primary config

```yaml
architecture:
  lookback_T: 10
  feature_dim: "resolved from primary_feature_route_id"
  latent_dim: 64
  lstm_layers: 1
  n_operator: 4
  selector_activation: leaky_relu
  selector_negative_slope: 0.01
  gumbel_tau_start: 1.0
  gumbel_tau_end: 0.1
  gumbel_anneal: linear_by_training_step
  gumbel_train_mode: soft
  gumbel_inference_mode: hard_argmax
  diffusion_steps: 20
  beta_schedule: linear
  beta_start: 0.0001
  beta_end: 0.02
  inference_residual_draws: 8
  decoder_output_dim: 1
loss:
  rec_weight: 1.0
  koop_weight: 1.0
  diff_weight: 1.0
  reduction: mean_valid
training:
  precision: fp32
  amp: false
  optimizer: AdamW
  learning_rate: 0.001
  weight_decay: 0.00001
  adam_betas: [0.9, 0.999]
  adam_eps: 0.00000001
  adam_amsgrad: false
  learning_rate_scheduler: none
  max_epochs: 100
  early_stopping_patience: 10
  early_stopping_metric: validation_mean_daily_rankic
  early_stopping_mode: max
  early_stopping_min_delta: 0.0
  evaluate_every_epochs: 1
  checkpoint_tie_break: earliest_epoch
  gradient_clip_norm: 1.0
  train_shuffle_each_epoch: true
  dataloader_drop_last: false
  training_sample_unit: instrument_decision_date
  training_sample_weight: 1.0
  day_balanced_loss: false
  seed_count: 3
```

这些是 project choices，不是 paper facts。21A 不训练；只在 synthetic dry-run 验证它们能形成 graph。
Future early stopping在每个 epoch末计算一次完整 validation metric；只有 metric严格大于 prior best 才重置 patience，连续10次未改善后停止，
并恢复 earliest best checkpoint。Gradient clipping在 `backward()` 后、`optimizer.step()` 前按全部 trainable parameters 的 global L2 norm
执行；train shuffle由 `dataloader_seed + epoch_index` 机械派生。

Exact schedules：

```text
planned_total_steps = max_epochs * ceil(train_sample_n / selected_batch_size)
progress = min(1, global_optimizer_step / max(1, planned_total_steps-1))
gumbel_tau = 1.0 + progress * (0.1 - 1.0)
diffusion_beta[s] = linspace(0.0001, 0.02, 20)[s]
```

Early stopping 只提前结束训练，不重新压缩 tau schedule；checkpoint 必须记录实际 final tau。

### 11.2 Batch-size mechanical ladder

```text
batch_size_candidates_desc = [256, 128, 64, 32, 16]
gpu_peak_memory_fraction_cap = 0.90
selected_batch_size = largest candidate that passes full R2 forward + backward + optimizer-state estimate + 8-draw inference
minimum_acceptable_batch_size = 16
```

OOM/peak-memory failure只能下降到下一 candidate；不得改变 latent/operator/diffusion/precision。没有 candidate 通过时
`gpu_dry_run_gate=fail`。

### 11.3 Sensitivity/search accounting

Primary R2 config 只有一个。One-factor-at-a-time sensitivity cells：

```text
S01 n_operator=2
S02 n_operator=8
S03 latent_dim=32
S04 latent_dim=128
S05 diffusion_steps=10
S06 diffusion_steps=50
```

```text
primary_R2_config_n = 1
scheduled_R2_sensitivity_n = 6
scheduled_R2_config_family_n = 7
learning_rate_search_n = 0
joint_grid_allowed = false
```

Feature route 是 pre-outcome deterministic precedence，不属于 winner search：

```text
primary_feature_route_registry = [
  ALPHA158_QFQ_VWAP_FULL,
  ALPHA158_NO_VWAP_REGISTERED_ADAPTATION
]
```

若 No-VWAP route 按 Section 8.2/17.2 被选择，它是 `registered_primary_route_adaptation`，不是可在 outcome 后 promote 的
diagnostic adaptation；它必须进入全部 mandatory arms 与 C0-C4。以下才是不得替换 primary 或进入 C0-C4 的非 primary
adaptations：

```text
non_primary_diagnostic_adaptation_ids = [
  LAST_TRANSITION_ONLY_ADAPTATION,
  TARGET_ENCODER_STOP_GRADIENT,
  TARGET_CS_NORMALIZATION,
  FACTOR_JUMP_WINDOW_QUARANTINE
]
```

所有 started/completed/OOM/NaN/failed/early-stop run 都必须进入未来 `model_search_accounting_manifest.csv`；失败 run 不得删除。

### 11.4 Seeds and deterministic mapping

```text
model_seeds = [20260713, 20260714, 20260715]
bootstrap_seed = 20260713
seed_ensemble = arithmetic_mean_score_across_three_seeds
best_seed_primary_allowed = false
```

每个 model seed 派生：

```text
python_seed = model_seed
numpy_seed = model_seed + 11
torch_seed = model_seed + 23
dataloader_seed = model_seed + 37
weight_init_seed = model_seed + 53
gumbel_seed = model_seed + 71
diffusion_train_noise_seed = model_seed + 89
```

Inference draw 使用 Section 9 stable row-key hash，不使用全局递增 RNG。未来必须报告 seed dispersion、worst seed、seed rank
stability；单个最佳 seed 不得替代 ensemble。

## 12. Chronological split、purge 与 historical-holdout firewall

### 12.1 Nominal and effective split

Nominal：

```text
train_nominal = 2018-01-02 .. 2022-12-30
validation_nominal = 2023-01-03 .. 2023-12-29
historical_design_holdout_nominal = 2024-01-02 .. 2026-05-29
validation_early_end = 2023-06-30
holdout_early = 2024 calendar year
holdout_late = 2025-01-01 .. data cutoff
```

Effective train start：

```text
max(2018-01-02, first exchange session whose U_t_decision >= 100 and all primary trailing windows are available)
```

不得按 label、RankIC 或 feature-outcome quality 顺延。若 effective support 不满足 Section 7 minimum days，split gate fail。

### 12.2 Purge

```text
purge_sessions = T input sessions + maximum registered label/execution horizon = 12 exchange sessions
purge_side = tail of earlier split
for each earlier nominal split with sorted eligible decision dates d[0..n-1]:
    purged_dates = d[n-12 .. n-1]                     # exactly 12 dates
    earlier_effective_end = d[n-13]
later split nominal/effective start is never shifted by purged rows
```

必须输出 nominal/effective boundaries、calendar session IDs、dropped decision dates/rows 和原因。不得用 calendar-day subtraction，
不得把 purge 行移入相邻 split。若 earlier split不足 13 个 eligible decision dates，`split_purge_gate=fail`。

### 12.3 Validation selection

Validation 以后只允许决定：

```text
early-stopping epoch / boosting iteration within a frozen arm
checkpoint within the same frozen arm/config/seed
validation futility gate
```

不允许决定：

```text
feature route or feature deletion
label timing
primary operator count / latent width / diffusion steps
residual module type
TopK / cost / risk budget
shock/regime slice definition
terminal-state definition
```

Learning rate primary 已固定为 `0.001`，21B–21D 不授权 learning-rate search。

### 12.4 Historical holdout firewall

21A 可读取 holdout 期间的**feature-only** bar/schema/coverage，用于判断未来是否有数据支持；禁止读取/生成任何 holdout label、
return summary 或 score join。以后：

```text
21B-21D training/early stopping/futility access = train + validation only
historical holdout outcome access before all mandatory checkpoints sealed = 0
historical holdout unseal = once, after M/K/R mandatory arms and primary sensitivities are complete and hashed
post-unseal retraining/config replacement/new arm = forbidden
pipeline defect after unseal = new run version, full restart, old bundle retained
```

`split_purge_embargo_freeze.csv` 必须包含 `outcome_access_allowed=false` for 21A，且为每个阶段记录 allowed feature/outcome scope。

## 13. Dependency lock、runtime fingerprint 与 synthetic GPU dry-run

### 13.1 Dependency contract

Resolved runtime requirements：

```text
python >=3.10,<3.13; exact patch recorded
pyqlib == 0.9.7 resolved in uv.lock
lightgbm == 4.6.0 resolved in uv.lock
torch == 2.8.0 direct optional dependency for REAKA runtime
torch CUDA build/runtime recorded exactly
numpy >=1.26,<2.0 resolved exactly
pandas >=2.2,<3.0 resolved exactly
```

Pre-implementation dependency baseline：

```text
pyproject_sha256_before = c6362216fda3f4741abe896e57d04b1d823b29fc8d015f260922f020b41fdc71
requirements_sha256_before = 9ebe795329363d23241e4eadeb62f1b12aca3ce55cd327baed3a0618239c616d
uv_lock_sha256_before = c082833af9dda1e7930814a9fecc1da96e37e22e1973fa21d8743bf78a227025
```

本 requirement 只预定义未来 implementation 的 dependency change surface。只有用户后续明确授权 implementation 后，才可增加
如下可审阅的 optional dependency group：

```toml
[project.optional-dependencies]
reaka = ["torch==2.8.0"]
```

并在 `requirements.txt` 增加单独一行 `torch==2.8.0`，随后于执行前人工运行 lock refresh。允许的 dependency diff 只有：

```text
pyproject.toml: add optional group reaka=["torch==2.8.0"]
requirements.txt: add torch==2.8.0
uv.lock: update root project optional metadata and add torch plus its transitive dependency closure
```

所有 pre-existing non-root package 的 `(name,version,source)` 必须与 baseline lock 相同；额外升级、降级、source/index 切换或删除均使
`dependency_lock_gate=fail`。Torch wheel source、artifact hash、platform marker、resolved CUDA build和全部新增 transitive packages必须
由 `uv.lock`/runtime audit记录。`freeze` runner itself不得修改 lock；dependency declaration 与 Section 15.0 显式 environment
bootstrap 不得静默漂移。

Pass requires：

```text
project lock contains exact torch resolution
runtime interpreter packages match lock
qlib expression source version/hash recorded
no ambient-only dependency satisfies gate
no install command executed by runner
explicit uv sync --frozen occurs only before stages; all stage/test commands use recorded .venv/bin/python
process_bootstrap reads only hash-closed interpreter/stdlib/runner/locked-package code
```

如果当前 shell 有 torch 但 project lock 没有，状态仍是 `dependency_unlocked`，不能 pass。

### 13.2 Runtime fingerprint

`runtime_dependency_gpu_audit.csv` 至少包含：

```text
python_version
platform
pyproject_sha256
requirements_sha256
uv_lock_sha256
pyqlib_version
pyqlib_distribution_hash_or_source_inventory_hash
lightgbm_version
torch_version
torch_cuda_version
cuda_available
cuda_driver_version
cuda_device_name
cuda_total_memory_mib
cudnn_version
deterministic_algorithms_enabled
cublas_workspace_config
deterministic_debug_mode
known_nondeterministic_ops
dependency_lock_gate
```

Primary deterministic flags：

```text
torch.use_deterministic_algorithms(true)
torch.backends.cudnn.benchmark = false
torch.backends.cudnn.deterministic = true
CUBLAS_WORKSPACE_CONFIG = :4096:8
```

若某 required op 在目标 CUDA 上无法 deterministic，必须列明 op 和 repeat-delta；未获新 contract version 前不能将 deterministic
gate改为 advisory。

### 13.3 Full-graph synthetic dry-run

Dry-run 输入只能是 seeded synthetic tensors：

```text
B in [256,128,64,32,16]
T=10
D_x=resolved primary feature count
d=64
N=4
teacher/source tensors finite random values
no real instrument/date/bar/label
```

每个 batch candidate 执行：

```text
1. R2 train forward with all T transitions
2. compute L_rec/L_koop/L_diff
3. backward and AdamW optimizer-state allocation
4. zero grad and repeat same seed to test determinism
5. inference graph without teacher, eight residual draws
6. record peak allocated/reserved memory and wall time
7. K1C train/inference global-mixture equality plus K1C and R1 parameter-count probes
```

Pass：

```text
selected_batch_size >= 16
peak_reserved_memory <= 0.90 * total_device_memory
all required shapes exact
all losses/gradients/scores finite
same-seed repeated score max_abs_delta <= 1e-7 in fp32
teacher-isolation tests pass
K1C train mixture max_abs_delta across valid B/T cells = 0
K1C inference mixture max_abs_delta across B/T cells = 0
K1C Gumbel random vector count per optimizer step = 1
K1C-vs-K2 and R1-vs-R2 parameter delta disclosed
```

GPU dry-run 只证明 graph/compute feasibility，不证明真实 training runtime、convergence 或 predictive support。

## 14. Metrics、multiplicity、economic boundaries 与 forward freeze

### 14.1 Predictive metric contract

Future primary metric：

```text
denominator = full U_t_resolved == U_t_decision
minimum N = 100
canonical row order before metric = canonical instrument ASC
rank method = average rank for exact ties, ascending values
tie jitter / ordinal row-order tie break = forbidden
RankIC_d = Pearson(float64_average_rank(score_i,d), float64_average_rank(Y_rank_primary_i,d))
evidence unit = complete decision day
RankICIR = mean(daily RankIC) / std(daily RankIC, ddof=1)
```

一个 primary metric day 只有在 `U_t_resolved == U_t_decision`、`N>=100`、所有 denominator rows 的 score/label finite，且 score-rank
与 label-rank 两者 sample variance 均严格大于 0 时才 complete。任一条件失败，整日 `RankIC_d=undefined`、
`metric_day_status=not_evaluable`，不能删 row、取 arm intersection、填 0 或加 jitter。Constant score 或 constant label 都按此规则处理；M0
仅 pipeline sanity，不进入 information gate。Average-rank 后的 Pearson correlation 是本合同对 Spearman 的唯一实现，禁止依赖库的其他
tie/NaN default。

Future validation/outcome-complete-day minima 与 Section 7 的 feature-only support counts 分开冻结：

```text
minimum_validation_full_metric_complete_days = 200
minimum_validation_early_metric_complete_days = 80     # <= 2023-06-30
minimum_validation_late_metric_complete_days = 80      # > 2023-06-30
minimum_historical_representation_complete_days = 252
minimum_historical_economic_complete_days = 252
minimum_forward_representation_evaluable_complete_days = 60
minimum_forward_economic_evaluable_complete_days = 60
```

若 full validation 少于 200 complete metric days，任何 epoch/boosting iteration 都不得被选为 checkpoint，baseline information/futility
gate 固定 `not_evaluable` 且复杂模型 continuation 不授权。若 early 或 late 任一少于 80，stability/futility gate 同样不能 pass。上述
threshold 不得用 feature-ready calendar days、股票行数或删去 undefined day 后的 arm-specific vector替代。

### 14.2 Primary contrasts and margins

```text
C0  = K1 - M3      margin 0.000
C1  = R2 - M3      margin 0.005
C2a = K2 - K1      margin 0.000
C2b = K2 - K1C     margin 0.000
C3a = R1 - K2      margin 0.000
C3b = R2 - K2      margin 0.000
C4  = R2 - R1      margin 0.000
```

Pass means the Section 14.2.1 Holm step-down one-sided lower confidence bound `> margin`，不是 point estimate > margin。C1 不能推导
任何 module contrast。

Inference freeze：

```text
familywise_alpha = 0.05
primary_contrast_n = 7
correction = Holm step-down
bootstrap = Politis-Romano stationary paired decision-day bootstrap
bootstrap_repetitions = 5000
stationary_bootstrap_mean_block_length_sessions = 20
bootstrap_seed = 20260713
HAC_sensitivity_lag = 20
calendar_month_cluster = sensitivity
```

Seeds、six config sensitivities、diagnostic horizons/slices全部记账，但不得从中选新 primary。

#### 14.2.1 Exact stationary-bootstrap and Holm algorithm

七个 contrasts 在相同、按 date 升序的 complete decision-day vector 上联合重采样；只有全部七个 contrasts 所需 arms 在当天均按
Section 14.1 产生 defined daily RankIC，该日才进入 shared vector。同一次 replicate 对所有 contrasts 使用同一 index vector，以保留跨
arm/contrast 相关性。Family size 始终为 `m=7`，不得删除失败或不可评价 hypothesis。Historical representation shared vector 少于
252 complete days 时整个 family `not_evaluable`；historical economic family 的 shared complete executable-ledger-day vector 少于252天时
整个 economic family `not_evaluable`。

Stationary-bootstrap index vector 长度等于 observed complete-day count `n`：

```text
p_restart = 1 / 20
index[0] = UniformInteger(0, n-1)
for j = 1..n-1:
    with probability p_restart:
        index[j] = UniformInteger(0, n-1)
    otherwise:
        index[j] = (index[j-1] + 1) mod n
```

RNG 固定为 NumPy `PCG64(bootstrap_seed)`；先完整生成 5000 个 shared index vectors，再按 `contrast_id` 顺序计算。每个 contrast：

```text
delta[d] = daily_RankIC_arm_left[d] - daily_RankIC_arm_right[d]
theta_hat = Mean(delta)
theta_boot[b] = Mean(delta[index_b])
error_boot[b] = theta_boot[b] - theta_hat
raw_one_sided_p = (1 + count(error_boot >= theta_hat - margin)) / (5000 + 1)
```

按 `(raw_one_sided_p ASC, contrast_id ASC)` 排序。对 rank `k=1..7`：

```text
alpha_k = 0.05 / (7-k+1)
critical_error_k = empirical_quantile(error_boot, 1-alpha_k, method="higher")
holm_step_lower_bound = theta_hat - critical_error_k
holm_step_pass = all earlier ranks passed AND holm_step_lower_bound > margin
```

首个失败后所有后续 hypotheses 都是 `holm_step_pass=false`，但仍输出 raw p、rank 和 bound。缺日、非 finite、arm coverage failure
或 complete days不足时，该 contrast固定 `raw_one_sided_p=1`、`holm_step_lower_bound` 为空、`status=not_evaluable`；它仍占 family
名额并使到达该 rank 的 step-down 停止。严禁改用 iid row bootstrap、独立 contrast index vectors、two-sided alpha、自动 block-length
selection 或 percentile-CI library default。

Other confirmatory families复用同一算法，只替换 family size、registered delta/margin和 seed；不得跨 family 合并排序：

```text
historical_representation: m=7, seed=20260713, contrasts=C0..C4 as Section 14.2
historical_economic:       m=3, seed=20260714, R2-M3|R2-M1|R2-full_PIT_equal_weight
forward_representation:   m=2, seed=20260715, R2-M3|R2-M1
forward_economic:         m=3, seed=20260716, R2-M3|R2-M1|R2-full_PIT_equal_weight
```

`metric_margin_power_freeze.csv` 必须为 validation_full/validation_early/validation_late、historical_representation、
historical_economic、forward_representation 和 forward_economic 各输出 `record_type=minimum_complete_day` row，并在 `n_required`
分别写 `200/80/80/252/252/60/60`；forward family 另以 `record_type=confirmatory_power` 写 `n_required=291`。Contrast-only fields
留空，不得写 0。

Economic `delta[d]` 使用同一 complete executable ledger day 的 paired daily net-utility contribution；representation 使用 paired daily
RankIC。Absolute cash hurdle、drawdown、ES、holdings/concentration gates不进入 Holm family，必须独立全部通过。

### 14.3 Frozen diagnostic slices

所有 slice 使用 decision-date `<=t` 信息，threshold 只在 original training period 拟合：

```text
high_vol = benchmark trailing-20d realized volatility >= training p80
large_index_move = abs(benchmark return at t) >= training p90
limit_heavy = fraction of U_t_membership at price limit on t >= training p90
main_board / ChiNext = frozen board_bucket
benchmark_up_down = sign of benchmark return at t
```

只有 `C4` 的 high-vol/large-index-move/limit-heavy family 参与预注册 diffusion-tail diagnostic；其余 slice 均 descriptive。

### 14.4 Forward MDE and power

21A 不使用 observed RankIC variance。Planning assumptions：

```text
forward_representation_contrast_n = 2
forward_familywise_alpha = 0.05
forward_power = 0.80
forward_MDE_daily_RankIC_delta = 0.01
planning_sigma_daily_delta = 0.05
planning_lag1_autocorrelation = 0.10
z_1_minus_alpha_over_2m = 2.2414027276
z_power = 0.8416212336
design_effect = (1+rho)/(1-rho)
n_iid = ceil(((z_1_minus_alpha_over_2m + z_power) * sigma / MDE)^2)
n_required = max(252, ceil(n_iid * design_effect)) = 291 complete decision days
```

Evidence ladder：

```text
<60 complete days = not evaluable
60-125 = interim only
126-290 = directional, non-confirmatory
>=291 and all frozen completeness/power gates = confirmatory-evaluable
```

若未来 actual complete-day dependence 比 planning assumption 更强，只能提高 required N；不能在看到效果后降低门槛。

### 14.5 Economic/execution contract freeze

21A 继承并 re-hash EP19/EP20A values：

```text
decision_time = after close t
entry_attempt = next executable exchange open exactly once
TopK = 30
target_weight = equal weight
initial_AUM_cny = 10000000
portfolio_ledger = one continuous no-injection stateful NAV per arm
blocked_buy = unfilled allocation remains cash
blocked_exit = position retained, marked, consumes capital
active_weight_rescaling = false
commission_buy_bps = 2.5
commission_sell_bps = 2.5
minimum_commission_cny = 5.0
stamp_tax = inherited effective-dated schedule
slippage_bps = 5.0
ADV20 = mean raw money over 20 exchange-open sessions ending before order
maximum_ADV_participation_rate = 0.01
```

Score-to-Top30 mapping固定为：在完整 `U_t_decision` 上按 finite raw ensemble score降序，tie按 canonical instrument升序；恰取前30。
任一 non-finite/missing score是 arm/day coverage failure，不得少取、补 baseline score或缩 denominator。`U_t_decision<100` 的日已在
feature-support阶段标为不可评价，不能进入 replay。

Future economic gates：

```text
cash_inclusive_net_return_hurdle = 0.0
paired_net_utility_margin_vs_M3 = 0.0
paired_net_utility_margin_vs_M1 = 0.0
paired_net_utility_margin_vs_full_PIT_equal_weight = 0.0
economic_pair_correction = Holm, familywise alpha 0.05
maximum_drawdown_cap = 0.35
daily_ES10_loss_cap = 0.03
minimum_break_even_cost_multiple = 1.0
minimum_effective_holdings_p10 = 20
single_instrument_weight_cap = 0.10
top10_instrument_weight_cap = 0.50
```

Paper close-to-close Top30 gross proxy 与 executable next-open stateful NAV 必须分表；前者不计成本且不得写成 PnL support。

### 14.6 21F comparator/refit freeze

Forward comparators 在 holdout outcome access 前固定：

```text
R2_REAKA_DIFFUSION
M1_LIGHTGBM_ALPHA158
M3_GATED_DUAL_PATH_LSTM
```

Deterministic final refit：

```text
refit only R2/M1/M3
architecture/features/loss/TopK/cost/seeds unchanged
final_refit_cutoff = last fully resolved pre-seal decision date
refit window = original train start .. final_refit_cutoff
selected_train_steps(seed,arm) = pre-holdout validation-frozen value
no refit early stopping
transform refit once on final refit window
only shape/finite/hash/coverage integrity tests after refit
forward start = first exchange session strictly after final candidate seal
no rolling retrain/normalizer refresh/comparator replacement within first 291 complete days
```

Forward representation family `R2-M3`、`R2-M1` 用 Holm；economic family另做 Holm。K1/K1C/K2/R1 不进入 minimum forward，
所以 21C/21D module flags 永远保持 `historical_design_diagnostic`。

### 14.7 Terminal-state registry freeze

`metric_margin_power_freeze.csv` 的 `record_type=terminal_state` rows 必须冻结 research plan 的互斥 primary terminal states：

```text
21_paper_lineage_or_data_contract_blocked
21_compute_or_dependency_contract_blocked
21_baseline_information_not_supported
21_historical_representation_not_supported
21_historical_representation_candidate_only
21_representation_supported_execution_failed
21_historical_executable_candidate_only
21_forward_interim_not_support
21_forward_directional_not_confirmatory
21_forward_confirmation_not_supported
21_forward_representation_supported_execution_unresolved
21_forward_representation_supported_execution_failed
21_forward_executable_reaka_candidate_supported
```

`priority` 按上列顺序固定为 `1..13`；terminal rows 的 contrast-only fields 留空，不能填 0。

Future closed run 只能一个 primary terminal state；module outcomes 是 nullable/nonexclusive diagnostic flags。未评价 contrast 的 flag
必须 `not_evaluable`，不能把 missing 当 pass/fail。21A 本身只输出 21A readiness decision，不触发上述 outcome terminal states。

## 15. Stage isolation、transactional publication 与 hash closure

### 15.0 Environment bootstrap 与 process-bootstrap boundary

Dependency environment mutation 只能作为人工可见、stage 外的显式 prerequisite 执行：

```text
environment_bootstrap_command = uv sync --frozen --extra reaka --extra dev
environment_bootstrap_occurs_before_any_runner_stage = true
runner_invokes_package_manager_count = 0
stage_commands_use_interpreter = .venv/bin/python
uv_run_for_stage_or_test_allowed = false
```

`uv lock --check` 与上述 `uv sync --frozen` 可以读取 `pyproject.toml`/`uv.lock` 并改变 `.venv`，但不属于
`acquire-sources/freeze/finalize`。必须先人工审阅 dependency change set，再执行一次；执行后由 freeze 记录 lock hash、interpreter path/hash、
package inventory/hash。任何 runner 内 `pip/uv/conda` 调用、自动 sync、未 frozen lock 解析或 stage 期间 environment mutation 都使
`dependency_lock_gate=fail`。

每个 runner stage 的 `process_bootstrap` 仅允许读取已记录 hash 的 `.venv/bin/python`、stdlib、runner source 与 locked package code；
CLI parse 后、第一次 stage data open 前必须启用 access audit。Bootstrap 不得读取 config、PDF、URL、market/upstream artifact、
`pyproject.toml`、`uv.lock` 或 package metadata；这些若是某 stage 的允许 data input，必须在 audit 启用后按 stage data access 记录。
Process-bootstrap expected/observed hashes不一致即 fail closed，不得自动修复环境。

### 15.1 Acquire-sources isolation

排除并另行核验 Section 15.0 的 hash-closed `process_bootstrap` 后，`acquire-sources` 的 stage data I/O 只能读取
requirement/config/PAPER_FILE 和 Section 6 URL allowlist，只写 `REFERENCE_ROOT`。Hard counts：

```text
market_data_read_count = 0
upstream_artifact_read_count = 0
outcome_read_count = 0
resolved_domain_outside_allowlist_count = 0
source_manifest_complete = true
```

网络失败时可保留本地 PDF 与 URL-unreachable 状态，但 DOI/title/PDF identity 仍必须闭合。Official page unavailable 不得被写成
official code unavailable 的肯定事实；状态应是 `not_evaluable_network_unavailable`。

### 15.2 Freeze transactional rules

`freeze` 先写：

```text
output_root/.building/<run_uuid>/freeze/
```

只有 structural schema/file-set/hash validation 和 `outcome_firewall_gate` 通过后才原子 promote；其他 substantive critical gate 可以
为 fail，并由完整 sealed bundle/final decision审计为 blocked。禁止 partial `.building`、outcome-firewall violation 或 structural-invalid
bundle 成为 final。Seal 顺序：

```text
1. materialize all required freeze artifacts
2. run schemas, forbidden-column scan, synthetic graph tests and all non-HB preseal predicates; do not emit final decision
3. choose sealed_at_utc once
4. write contract_freeze_21a.json and 21A_contract_freeze.md
5. write freeze_bundle_manifest.json with the exact expected_paths set; its output_hashes exclude itself and freeze_output_hashes_21a.json
6. write freeze_output_hashes_21a.json covering every required freeze artifact including manifest, excluding itself
7. freeze_bundle_hash = SHA256(bytes of freeze_output_hashes_21a.json)
8. never write freeze_bundle_hash back into freeze artifacts
9. prohibit overwrite
```

File-set closure 使用 `manifest.expected_paths`，不是 `manifest.output_hashes.keys()`：

```text
manifest.expected_paths = exact Section 16.1 relative-path set, including manifest and freeze output-hashes
manifest.output_hashes.keys = expected_paths - {manifest, freeze output-hashes}
freeze_output_hashes.hashes.keys = expected_paths - {freeze output-hashes}
actual promoted freeze paths = manifest.expected_paths
```

因此两个自引用文件是显式 exclusion，不是 extra。Any required artifact missing、expected set外 extra、hash mismatch 或 schema drift：

```text
freeze_bundle_hash_gate = fail
bundle_disposition = blocked_not_promoted
```

### 15.3 Preoutcome access log

`preoutcome_access_log.csv` 每次 file/directory/package/GPU access 一行：

```text
run_id
stage
accessed_at_utc
artifact_path_or_resource
artifact_sha256_or_root_hash
dataset_role
columns_or_metadata_read
derived_fields
feature_date_constraint
outcome_columns_detected
outcome_formula_executed
selection_or_tuning_allowed
purpose
access_gate
```

Hard counts：

```text
outcome_columns_detected_count = 0
outcome_formula_executed_count = 0
real_label_materialization_count = 0
real_model_score_count = 0
selection_or_tuning_allowed_count = 0
historical_holdout_outcome_access_count = 0
```

上述 sealed log 只覆盖 `acquire-sources` 与 `freeze`，不得预填尚未发生的 finalize access。

### 15.4 Finalize

`finalize` CLI 只接受 `--stage finalize --output-root <repository-relative path>`，不得接受或读取 config。Runner/source import 遵守
Section 15.0 `process_bootstrap`；finalize module 必须 lazy-import，禁止触发 qlib/torch、网络、GPU 或 package metadata probe。Finalize
使用 freeze 阶段已记录 interpreter hash/path 的 `.venv/bin/python` 直接启动，不通过 `uv run` 再解析 project metadata。它的唯一 data
input 是 freeze manifest/hashes 和 manifest 中列明的 freeze artifacts，并在 root 输出
`finalize_access_audit.csv`。该 audit 每个 read access 一行；`finalize_raw_input_read_count=0`、
`finalize_unmanifested_freeze_read_count=0` 才可 pass。Root-level hash rule：

Audit hook 从 runner entry/CLI parse 完成后、第一次 data open 前启用；interpreter/runner import 是单独的 `process_bootstrap` hash check，
不得借此读取 config、project metadata或stage-specific package。Audit 内 `operation` 固定为 `read`。

```text
final manifest.output_hashes excludes final manifest and final output-hashes file
final output-hashes includes final manifest, finalize-access audit, gate evidence, decision and report; excludes itself
root decision.freeze_bundle_hash = SHA256(bytes of freeze/freeze_output_hashes_21a.json)
```

任何 finalize raw input read 或 hash mismatch 映射到 `21A_manifest_or_hash_blocked`。

## 16. Required outputs 与 schemas

### 16.0 Acquire-sources review artifacts

```text
REFERENCE_ROOT/source_availability_manifest.csv
REFERENCE_ROOT/paper_formula_registry_draft.csv
REFERENCE_ROOT/formula_review_packet.md
REFERENCE_ROOT/formula_review_authorization.json      # human-written/reviewed input to freeze
```

`source_availability_manifest.csv` exact columns/order：

```text
source_id,source_role,requested_url,resolved_url,resolved_domain,http_status,
content_sha256,content_type,retrieved_at_utc,inside_allowlist,identity_status,availability_status
```

Sort key=`source_id,requested_url`。`paper_formula_registry_draft.csv` 使用 Section 6.4 schema，额外增加
`draft_registry_sha256_input`，所有 `human_verified=false`。`formula_review_packet.md` 必须逐 required formula_id 显示 page crop/text
anchor、paper formula、project mapping和gap；其 SHA-256 被 authorization 绑定。Authorization JSON 使用 Section 6.3 exact keys，
额外禁止未知 top-level key；人工只能把完整 required formula set整体批准或拒绝，不能 partial approval 后让 gate pass。

### 16.1 Freeze artifacts

```text
freeze/resolved_config.yaml
freeze/human_restart_authorization.json
freeze/upstream_scope_and_lineage_audit.csv
freeze/input_artifact_audit.csv
freeze/source_data_inventory.csv
freeze/paper_source_registry.csv
freeze/paper_formula_and_architecture_registry.csv
freeze/paper_reproducibility_gap_registry.csv
freeze/official_code_availability_audit.csv
freeze/alpha158_expression_registry.csv
freeze/alpha158_local_field_mapping.csv
freeze/alpha158_expression_hash.txt
freeze/vwap_qfq_unit_and_range_audit.csv
freeze/alpha158_volume_corporate_action_audit.csv
freeze/alpha158_factor_jump_window_quarantine_sensitivity.csv
freeze/pit_membership_signal_execution_timing_audit.csv
freeze/feature_sequence_support_audit.csv
freeze/feature_cache_manifest.json
freeze/feature_normalization_and_missingness_contract.csv
freeze/label_semantics_freeze.csv
freeze/decision_universe_and_label_resolution_contract.csv
freeze/train_teacher_inference_graph_contract.csv
freeze/gradient_flow_and_teacher_isolation_audit.csv
freeze/per_arm_loss_and_score_index_contract.csv
freeze/split_purge_embargo_freeze.csv
freeze/model_arm_registry.csv
freeze/tensor_shape_contract.csv
freeze/hyperparameter_and_search_budget_freeze.csv
freeze/seed_and_randomness_freeze.csv
freeze/dependency_lock_change_and_runtime_contract.csv
freeze/runtime_dependency_gpu_audit.csv
freeze/metric_margin_power_freeze.csv
freeze/forward_refit_and_comparator_freeze.csv
freeze/preoutcome_access_log.csv
freeze/contract_freeze_21a.json
freeze/21A_contract_freeze.md
freeze/freeze_bundle_manifest.json
freeze/freeze_output_hashes_21a.json
```

### 16.2 Final artifacts

```text
21A_contract_decision.csv
finalize_access_audit.csv
gate_evidence_21a.csv
21A_paper_lineage_pit_data_and_architecture_contract_report.md
manifest_21a_paper_lineage_pit_data_and_architecture_contract.json
output_hashes_21a_paper_lineage_pit_data_and_architecture_contract.json
```

### 16.3 Stable output rules

- CSV UTF-8、LF、固定列序和明确 sort key；
- bool 只允许 lowercase `true/false`；unknown/not-evaluable 不得写成 false；
- missing 用空字段或 schema 枚举，不得用隐式 0；
- float 至少 10 位有效数字；
- timestamp UTC ISO-8601；
- path repository-relative；
- JSON `sort_keys=true`、indent=2、末尾 newline；
- YAML resolved config 必须展开 defaults，不保留 environment-dependent placeholder；
- 每个 artifact 绑定 `run_id/contract_version`，或由 manifest 显式绑定；
- 所有未来 outcome/value columns 在 21A outputs 中禁止。

Status enums exact：

```text
generic status = pass | fail | not_evaluable | pass_nonblocking
critical gate field = pass | fail
schema_status / identity_gate / identity_status / unit_gate / access_gate = pass | fail
support_status = ready | feature_support_not_evaluable | blocked
route_status = primary_unchanged | sensitivity_ready | sensitivity_not_evaluable | blocked
availability_status = available | not_disclosed | not_evaluable_network_unavailable
official_status = official_available | not_disclosed_in_allowlisted_sources | not_evaluable_network_unavailable
authorization_status = approved | rejected
bundle_disposition = promoted_ready | promoted_blocked | blocked_not_promoted | invalid_do_not_promote
```

任何未列 enum、大小写漂移或空 critical status 都是 schema failure。

### 16.4 Tabular schema registry

以下为 exact columns 和顺序；不得增加、删除、改名或重排。新增审计字段必须升级 `contract_version` 并修改本 registry：

| artifact | minimum columns / keys | primary sort key |
|---|---|---|
| `upstream_scope_and_lineage_audit.csv` | `artifact_id,path,sha256,expected_role,preoutcome_only,manifest_verified,allowed,status,blocking_reason` | `artifact_id` |
| `input_artifact_audit.csv` | `artifact_id,path,artifact_type,exists,size_bytes,sha256_or_root_hash,schema_status,read_authorized,status` | `artifact_id` |
| `source_data_inventory.csv` | `source_id,relative_path,file_n,row_n,date_min,date_max,instrument_n,root_hash,status` | `source_id,relative_path` |
| `paper_source_registry.csv` | Section 6.2 fields | `source_id` |
| `paper_formula_and_architecture_registry.csv` | Section 6.4 fields | `formula_id` |
| `paper_reproducibility_gap_registry.csv` | Section 6.5 fields | `gap_id` |
| `official_code_availability_audit.csv` | `candidate_id,url,owner_identity,source_role,http_status,code_disclosed,official_status,checked_at_utc,status` | `candidate_id` |
| `alpha158_expression_registry.csv` | Section 8.3 fields | `feature_index` |
| `alpha158_local_field_mapping.csv` | `qlib_field,local_source,source_scale,transform,availability_time,route_id,unit_gate,status` | `route_id,qlib_field` |
| `vwap_qfq_unit_and_range_audit.csv` | `scope,instrument,year,board_bucket,qfq_key_n,raw_key_n,overlap_key_n,overlap_rate,base_row_n,factor_pass_n,factor_fail_n,factor_unknown_n,factor_pass_rate,auditable_row_n,auditable_row_rate,in_range_n,out_of_range_n,unknown_n,range_pass_rate,coverage_threshold,range_threshold,status` | `scope,board_bucket,instrument,year` |
| `alpha158_volume_corporate_action_audit.csv` | `instrument,jump_date,factor_before,factor_after,abs_log_jump,window_start,window_end,exposed_feature_row_n,status` | `instrument,jump_date` |
| `alpha158_factor_jump_window_quarantine_sensitivity.csv` | `split,decision_day_n,source_row_n,quarantine_row_n,remaining_row_n,remaining_day_n,route_status` | `split` |
| `pit_membership_signal_execution_timing_audit.csv` | `check_id,scope,observed_value,required_value,status,blocking_reason` | `check_id,scope` |
| `feature_sequence_support_audit.csv` | `split,decision_date,feature_route_id,U_membership_n,membership_integrity_n,history_ready_n,sequence_ready_n,feature_ready_n,U_decision_n,invalid_n,layer_count_reconciled,support_status` | `split,decision_date` |
| `feature_normalization_and_missingness_contract.csv` | `field_group,fit_split,center_rule,scale_rule,clip_lower,clip_upper,invalid_fill,indicator_direct_input,apply_splits,status` | `field_group` |
| `label_semantics_freeze.csv` | `label_id,formula,role,materialized_in_21a,selection_allowed,status` | `label_id` |
| `decision_universe_and_label_resolution_contract.csv` | `status_id,trigger,valuation_rule,row_or_day_action,primary_denominator_allowed,synthetic_test_status` | `status_id` |
| `train_teacher_inference_graph_contract.csv` | `graph_id,node_id,node_role,input_nodes,output_shape,train_only,inference_present,teacher_value_allowed,status` | `graph_id,node_id` |
| `gradient_flow_and_teacher_isolation_audit.csv` | `test_id,expected,observed,max_abs_delta,status,blocking_reason` | `test_id` |
| `per_arm_loss_and_score_index_contract.csv` | `arm_id,loss_terms,target_id,score_tensor,score_index,draw_n,aggregation,status` | `arm_id` |
| `split_purge_embargo_freeze.csv` | `split_id,nominal_start,nominal_end,effective_start,effective_end,purge_side,purge_sessions,dropped_day_n,outcome_access_allowed,status` | `split_id` |
| `model_arm_registry.csv` | Section 10.1 fields | `arm_id` |
| `tensor_shape_contract.csv` | `graph_id,tensor_id,producer,consumer,dtype,train_shape,inference_shape,train_only,broadcast_allowed,status` | `graph_id,tensor_id` |
| `hyperparameter_and_search_budget_freeze.csv` | `config_id,role,parameter,primary_value,sensitivity_value,one_factor_only,promotion_allowed,status` | `config_id,parameter` |
| `seed_and_randomness_freeze.csv` | `model_seed,stream_name,derived_seed_or_rule,batch_order_invariant,status` | `model_seed,stream_name` |
| `dependency_lock_change_and_runtime_contract.csv` | `dependency,required_spec,baseline_version,lock_resolved_version,runtime_version,direct_or_transitive,baseline_source,resolved_source,lock_action,allowed_change,status` | `dependency` |
| `runtime_dependency_gpu_audit.csv` | `check_id,observed_value,required_value,batch_size,peak_memory_mib,repeat_delta,status` | `check_id,batch_size` |
| `metric_margin_power_freeze.csv` | `record_type,family_id,contrast_id,terminal_state_id,priority,metric,margin,alpha,correction,evidence_unit,block_length,MDE,sigma,rho,n_required,status` | `record_type,family_id,contrast_id,terminal_state_id` |
| `forward_refit_and_comparator_freeze.csv` | `contract_id,field,frozen_value,selection_time,change_resets_clock,status` | `contract_id,field` |
| `finalize_access_audit.csv` | `access_seq,accessed_at_utc,operation,path_or_resource,freeze_manifest_listed,raw_input,allowed,status` | `access_seq` |
| `gate_evidence_21a.csv` | `gate_id,check_id,evidence_artifact,evidence_selector,observed_value,required_value,status,blocking_reason` | `gate_id,check_id` |

### 16.5 Decision schema

`21A_contract_decision.csv` 恰好一行，并按下列 exact order包含全部且仅这些 columns：

```text
run_id
contract_version
decision_state
human_restart_scope_gate
paper_source_lineage_gate
paper_formula_contract_gate
official_code_status
alpha158_expression_gate
vwap_qfq_unit_contract_gate
volume_corporate_action_semantics_gate
feature_materialization_route_gate
primary_feature_route_id
primary_feature_route_class
alpha158_exact_local_materialization
pit_membership_timing_gate
decision_denominator_contract_gate
feature_sequence_support_gate
feature_label_alignment_gate
train_teacher_inference_graph_gate
gradient_teacher_isolation_gate
architecture_shape_gate
loss_reduction_gate
model_arm_and_fairness_gate
split_purge_gate
historical_holdout_firewall_gate
search_budget_gate
seed_randomness_gate
dependency_lock_gate
gpu_dry_run_gate
metric_multiplicity_gate
economic_execution_freeze_gate
forward_refit_contract_gate
outcome_firewall_gate
freeze_bundle_hash_gate
implementation_readiness_gate
paper_architecture_project_adaptation_reachable
exact_replication_reachable
official_code_available
selected_batch_size
historical_sample_role
historical_support_claim_allowed
forward_confirmatory_required_complete_days
next_allowed_requirement
next_requirement_generation_authorized
next_requirement_execution_authorized
outcome_model_training_authorized
historical_holdout_readout_authorized
policy_training_authorized
portfolio_optimization_authorized
deployment_authorized
freeze_bundle_hash
gate_evidence_sha256
blocking_reasons
```

`blocking_reasons` 是 JSON-array text，按 Section 17.5 precedence 后接 `gate_id ASC` 排序，例如
`["feature_label_alignment_gate","split_purge_gate"]`；无阻断时必须为 `[]`，不得使用自由文本或逗号拼接。

### 16.6 Non-tabular schemas and canonical hash maps

`resolved_config.yaml` 顶层 keys 恰好包含：

```text
identity, paths, source_allowlist, input_hash_expectations, paper_contract,
feature_contract, universe_contract, architecture, arms, split, dependencies,
metrics, execution, forward, gates, output
```

`feature_cache_manifest.json` 必须包含：

```text
schema_version,run_id,contract_version,cache_role,cache_published,
primary_feature_route_id,primary_feature_route_class,feature_count,expression_list_sha256,
input_root_hashes,split_hash,normalization_contract_hash,
cache_relative_path,cache_content_hash,cache_row_n,key_columns,
date_min,date_max,label_columns_present,outcome_formula_count,status
```

其中 `cache_published=false`；`cache_content_hash` 绑定 ignored local cache bytes/root inventory，未来使用前必须重验。Cache 缺失可机械
重算，但 hash 不匹配不得继续。

`contract_freeze_21a.json` 必须包含：

```text
schema_version,run_id,contract_version,created_at_utc,sealed_at_utc,
requirement_sha256,resolved_config_sha256,research_plan_sha256,paper_sha256,
input_artifact_hashes,primary_feature_route_id,primary_feature_route_class,feature_expression_sha256,
architecture_contract_hash,arm_registry_hash,split_contract_hash,
dependency_contract_hash,metric_contract_hash,forward_contract_hash,
preoutcome_hard_counts,claim_ceiling
```

`21A_contract_freeze.md` 是上述 JSON 和 tabular contracts 的非权威 human-readable rendering，固定 sections 为
`Identity, Inputs, Paper, Feature Route, Universe, Graph, Arms, Split, Runtime, Statistics, Execution, Forward, Firewall`；不得包含无法从
manifest-listed machine artifact定位的独立数值或 gate decision。

`freeze_bundle_manifest.json` 必须包含：

```text
schema_version,run_id,contract_version,sealed_at_utc,bundle_role,
expected_paths,manifest_hash_exclusion_paths,output_hashes,input_hashes,
schema_registry_version,sort_contract_version
```

并固定：

```text
manifest_hash_exclusion_paths = [
  "freeze/freeze_bundle_manifest.json",
  "freeze/freeze_output_hashes_21a.json"
]
```

`freeze_output_hashes_21a.json` 必须包含：

```text
schema_version,run_id,contract_version,hash_algorithm="sha256",
excluded_paths=["freeze/freeze_output_hashes_21a.json"],hashes
```

Root final manifest 使用相同 schema，`expected_paths` 恰好为 Section 16.2 六个文件；其 exclusion paths 是 final manifest 和 final
output-hashes。其 `bundle_role=final_root`、file-set scope只包含 output-root 直属文件；`freeze/` subtree 由
`freeze_bundle_hash`/freeze manifest独立闭合，不算 root extra。Root final output-hashes 只排除自身，并覆盖 manifest、finalize-access
audit、gate evidence、decision、report。

所有 hash-map key 使用 `/` 分隔的 output-root-relative path，按 Unicode code point 升序；value 是 lowercase 64-char SHA-256。
JSON canonical bytes 固定为 UTF-8、`sort_keys=true`、indent=2、`ensure_ascii=false`、LF、末尾一个 newline。数组顺序是 schema
顺序，不允许 serializer 自行重排。`alpha158_expression_hash.txt` 继续使用 Section 8.3 的专用 bytes contract。

## 17. Gate logic 与 final decision

### 17.1 Critical gates

```text
human_restart_scope_gate
paper_source_lineage_gate
paper_formula_contract_gate
alpha158_expression_gate
vwap_qfq_unit_contract_gate
volume_corporate_action_semantics_gate
feature_materialization_route_gate
pit_membership_timing_gate
decision_denominator_contract_gate
feature_sequence_support_gate
feature_label_alignment_gate
train_teacher_inference_graph_gate
gradient_teacher_isolation_gate
architecture_shape_gate
loss_reduction_gate
model_arm_and_fairness_gate
split_purge_gate
historical_holdout_firewall_gate
search_budget_gate
seed_randomness_gate
dependency_lock_gate
gpu_dry_run_gate
metric_multiplicity_gate
economic_execution_freeze_gate
forward_refit_contract_gate
outcome_firewall_gate
freeze_bundle_hash_gate
implementation_readiness_gate
```

### 17.1.1 Binary gate evidence and truth table

所有 critical gate 只允许 lowercase `pass/fail`；`unknown`、`not_evaluable`、缺 row、重复 row 或异常都按 `fail`。实现必须输出
`gate_evidence_21a.csv`，每个 `(gate_id,check_id)` 恰好一行。Gate 的唯一计算规则：

```text
gate_id = pass iff
    observed check_id set == required check_id set below
    and every required row.status == pass
otherwise gate_id = fail
```

禁止 runner 根据 report prose、overall intuition 或另一个 gate 的最终值补写当前 gate。Required truth table：

```text
human_restart_scope_gate:
  H01 episode/phase/version/restart type exact
  H02 research-plan expected/observed hash equal
  H03 requirement observed hash equals authorization record
  H04 automatic authorization and all training/policy/deployment flags false

paper_source_lineage_gate:
  P01 local PDF expected/observed SHA256 equal and page_count=5
  P02 DOI/title/venue/year exact
  P03 ordered author list exactly Lei Liao|Yang Zhang|Jun Wang|Jinghua Tan|Yinchao Liao
  P04 every network access resolves inside Section 6 allowlist
  P05 source registry has no identity conflict or unaccounted source

paper_formula_contract_gate:
  PF01 formula draft/review-packet/authorization hashes form one closed chain
  PF02 authorization_status=approved and reviewer_role=human
  PF03 P01-P17 plus A01-A06 each present exactly once; any extra row has unique X-prefix ID and separate human authorization
  PF04 every required formula row has page, anchor, canonical paper/project mapping and human_verified=true
  PF05 all paper gaps enumerated and claim ceiling remains project adaptation

alpha158_expression_gate:
  A01 locked/runtime pyqlib version both 0.9.7
  A02 canonical expression count=158, names unique, order contiguous 0..157
  A03 future-offset count=0 and label config absent
  A04 expression hash bytes independently recompute exactly
  A05 every direct/transitive local field mapping accounted

vwap_qfq_unit_contract_gate:
  V01 qfq/raw keys unique and OHLC ordering/finite rules pass
  V02 hands-to-shares conversion applied exactly once and money unit=CNY
  V03 factor consensus formula/tolerance and all denominators reproducible
  V04 global/base/board-year auditable coverage rows complete, including failed/unknown rows
  V05 route-selection inputs contain no outcome field/access

volume_corporate_action_semantics_gate:
  VC01 primary volume is raw shares and volume factor adjustment is forbidden
  VC02 factor-jump threshold=1e-4 and radius=60 sessions exactly
  VC03 every detected jump has exposure counts and no unaccounted row
  VC04 quarantine sensitivity is date/window-only and never promoted to primary

feature_materialization_route_gate:
  F01 full/no-VWAP inclusion lists derive mechanically from canonical expressions
  F02 exactly one primary route selected by Section 17.2 precedence
  F03 retained route fields all mapped and feature count/hash nonempty
  F04 feature loader is label-free and every materialized expression uses bars <= feature_date
  F05 feature cache manifest closes route/config/input/expression hashes
  F06 selected route class is canonical_full_route or registered_primary_route_adaptation and one shared route enters all mandatory arms/C0-C4

pit_membership_timing_gate:
  U01 membership key unique and U_t_membership is the unfiltered membership-date row set
  U02 every row is listed/non-ST and membership availability is no later than decision close
  U03 every non-cutoff usable_trade_date is exactly the next exchange session and mapping is unique; the sole terminal
      data-cutoff day may retain blank mapping only when expected next session is after observed market-data max date and the
      whole day is registered RIGHT_CENSORED_DATA_CUTOFF
  U04 no history/feature/suspension/outcome filter changes U_t_membership count
  U05 no current-constituent or CSI300 constituent backfill/filter

decision_denominator_contract_gate:
  D01 membership->integrity->history->sequence->feature->decision counts reconcile per day
  D02 U_t_decision predicate equals Section 7.2 exactly
  D03 synthetic t+1 bar/value perturbation cannot change U_t_decision
  D04 no per-arm/per-label intersection denominator is allowed
  D05 all resolution states/triggers/day actions are unique and exhaustive

feature_sequence_support_gate:
  FS01 T=10 and maximum trailing warm-up use exchange sessions ending at t
  FS02 suspension/gap/prelisting policy matches Section 7.5
  FS03 train complete days>=750 and validation complete days>=200
  FS04 future holdout calendar support days>=400 and primary evaluable day requires U_t_decision>=100
  FS05 support counts use no outcome field/formula

feature_label_alignment_gate:
  FL01 synthetic source dates=[t-T+1..t], teacher dates=[t-T+2..t+1]
  FL02 score index is shifted step T and label formula is close(t+1)/close(t)-1
  FL03 Qlib-gap and execution labels have distinct IDs/roles and are not selection targets
  FL04 real label materialization count=0 and negative-offset expression execution count=0

train_teacher_inference_graph_gate:
  G01 required source/train-teacher/inference node and edge sets exactly match Section 9
  G02 teacher branch absent from inference signature and every inference-score ancestor; only enumerated train-only target/noising edges exist
  G03 all T transitions are present; last-transition-only is not primary
  G04 each mandatory arm has exactly one score producer and one frozen graph role

gradient_teacher_isolation_gate:
  GI01-GI12 exact synthetic tests listed in Section 9.7 all pass
  GI13 teacher perturbation changes only allowed train targets/losses, inference delta=0
  GI14 L_koop gradient reaches shared encoder; forbidden selector/gate/condition/inference teacher paths are zero while allowed train-only paths remain

architecture_shape_gate:
  S01 exact tensor ID set and train/inference shapes match Section 9.3
  S02 full route D_x=158; registered primary no-VWAP route adaptation D_x equals retained expression count
  S03 no implicit batch/time/latent broadcast and batched K product matches einsum reference
  S04 GateNet has exactly one sigmoid and every mandatory arm graph builds on synthetic tensors

loss_reduction_gate:
  L01 source/history/forecast/Koopman/DDPM/R1 formulas match Sections 9.6 and 10.2
  L02 every top-level loss weight exact and L_forecast appears once
  L03 MeanValid axis order/count exact and batch-duplication invariance passes
  L04 R1 residual target/reduction and R2 epsilon target/reduction are finite and unique

model_arm_and_fairness_gate:
  M01 mandatory arm set equals the exact 10 IDs in Section 10.1
  M02 every arm has unique graph/loss/score/input role; M0 hash mapping exact
  M03 shared rows/splits/label/normalization/seed/early-stop contract exact
  M04 K1C train/inference mixtures are each global across batch/time and never read row state; K1C/K2 and R1/R2 counts/deltas disclosed
  M05 parameter mismatch >10% downgrades only named mechanism flag and cannot be hidden/promoted

split_purge_gate:
  SP01 nominal boundaries exactly match Section 12.1
  SP02 effective train start uses only feature/support predicates
  SP03 purge uses exactly 12 exchange sessions from earlier-split tail
  SP04 dropped dates/rows reconcile and no purged row enters another split
  SP05 random-row or calendar-day split count=0

historical_holdout_firewall_gate:
  HF01 21A and pre-unseal historical outcome access counts=0
  HF02 21B-21D allowed scope is train+validation only
  HF03 unseal trigger requires all mandatory checkpoints/sensitivities sealed
  HF04 post-unseal retrain/config/new-arm authorization=false

search_budget_gate:
  SB01 primary R2 config count=1 and scheduled sensitivity IDs exactly S01-S06
  SB02 every sensitivity changes exactly one frozen primary field
  SB03 learning-rate search count=0 and joint-grid authorization=false
  SB04 non_primary_diagnostic_adaptation_ids cannot replace primary or enter C0-C4
  SB05 selected primary feature route follows pre-outcome precedence and is shared by every mandatory arm and C0-C4

seed_randomness_gate:
  SR01 model seeds exactly 20260713|20260714|20260715
  SR02 all training RNG stream derivations equal Section 11.4
  SR03 inference draw key encoding/hash is exact and batch-order invariant
  SR04 primary ensemble is arithmetic mean of three seeds; best-seed promotion=false

dependency_lock_gate:
  DL01 pyproject/requirements/uv.lock change set obeys Section 13.1 allowlist
  DL02 resolved/runtime pyqlib=0.9.7, lightgbm=4.6.0, torch=2.8.0 and versions match lock
  DL03 Python/numpy/pandas constraints resolve and runtime matches selected lock environment
  DL04 no ambient-only dependency, runner-invoked install/sync command or runner source mutation
  DL05 explicit environment bootstrap is uv sync --frozen before stages; stage/test interpreter is recorded .venv/bin/python

gpu_dry_run_gate:
  GPU01 device is CUDA RTX 4070 SUPER with recorded runtime/memory fingerprint
  GPU02 largest passing batch follows 256->128->64->32->16 ladder and is >=16
  GPU03 R2 full train forward/backward/optimizer plus eight-draw inference passes
  GPU04 peak reserved<=90%, all values finite, repeat score delta<=1e-7
  GPU05 dry-run market/instrument/date/real-label access counts=0

metric_multiplicity_gate:
  MM01 RankIC uses full-denominator float64 average-rank Pearson with no jitter and exact undefined-day rules
  MM02 primary contrast IDs/margins exactly C0,C1,C2a,C2b,C3a,C3b,C4
  MM03 stationary-bootstrap/Holm algorithm and parameters exactly match Section 14.2.1
  MM04 family size remains 7 and not-evaluable hypotheses are not removed
  MM05 validation/historical/forward complete-day minima and shared-family vector rules equal Section 14
  MM06 diagnostic slices/threshold fit scope and C4-only tail role exact
  MM07 forward power assumptions/formula independently recompute n_required=291

economic_execution_freeze_gate:
  E01 EP19/20 decision/manifest/hash chains verify
  E02 timing/Top30/AUM/cost/fill/NAV/ADV values exactly match Section 14.5
  E03 gross close proxy and next-open executable ledger roles remain distinct
  E04 economic Holm family/margins/risk limits all non-placeholder

forward_refit_contract_gate:
  FR01 comparator set exactly R2|M1|M3 before holdout access
  FR02 refit window/cutoff/step rule and no-refit-early-stop exact
  FR03 first cohort starts strictly after seal and target complete days=291
  FR04 rolling retrain/normalizer refresh/comparator replacement/version splice=false
  FR05 forward module-attribution authorization=false

outcome_firewall_gate:
  OF01 all Section 15.3 hard counts plus finalize raw/unmanifested read counts=0
  OF02 every access-log row is allowlisted and purpose/columns/derived fields close
  OF03 forbidden-column/expression scanner has no unapproved match
  OF04 only label-semantics string rows use the documented metadata exception

freeze_bundle_hash_gate:
  HB01 required freeze path set equals manifest expected path set under Section 15 exclusions
  HB02 manifest artifact hashes and independently generated output-hashes agree
  HB03 output-hashes covers every required freeze artifact except itself, including manifest
  HB04 canonical JSON bytes reproduce freeze_bundle_hash and sealed bundle is not overwritten
  HB05 schema/version/run/config/input hashes all close with no extra file

implementation_readiness_gate:
  IR01 every required input/output/schema/sort/status enum is present
  IR02 all formulas/graphs/shapes/arms/gates have one machine-executable interpretation
  IR03 all numeric choices/dependencies/splits/search/statistics are non-placeholder
  IR04 all required test IDs and validation commands are present and path-correct
  IR05 resolved config contains no TBD/TODO/choose-later/best-effort value
```

`GI01-GI12` 顺序绑定 Section 9.7 的 12 个测试条目；不得通过减少 required check set 令 gate pass。每个 evidence row 至少保存
`gate_id,check_id,evidence_artifact,evidence_selector,observed_value,required_value,status,blocking_reason`。

Noncritical capability/status：

```text
official_code_available
paper_appendix_available
alpha158_exact_local_materialization
confirmed_terminal_price_resolution_available
gpu_batch_size_mechanically_reduced
exact_replication_reachable
```

### 17.2 Feature-route logic

```text
vwap_qfq_unit_contract_gate = pass iff
    unit/factor/range audit is complete
    and every failed/unknown row is accounted
    and route-selection rule is applied without outcome access

full_route_reachable =
    alpha158_expression_gate == pass
    and factor_cross_field_pass_rate >= 0.995
    and vwap_inside_range_rate >= 0.995
    and qfq_raw_key_overlap_rate >= 0.99
    and vwap_auditable_row_rate_global >= 0.95
    and every board-year slice with base_row_n >= 100 has vwap_auditable_row_rate >= 0.90

no_vwap_route_reachable =
    alpha158_expression_gate == pass
    and non_vwap_expression_count > 0
    and every retained expression has complete field mapping
    and no retained expression references vwap

if full_route_reachable:
    primary_feature_route_id = ALPHA158_QFQ_VWAP_FULL
    primary_feature_route_class = canonical_full_route
    feature_materialization_route_gate = pass
elif no_vwap_route_reachable:
    primary_feature_route_id = ALPHA158_NO_VWAP_REGISTERED_ADAPTATION
    primary_feature_route_class = registered_primary_route_adaptation
    feature_materialization_route_gate = pass
else:
    feature_materialization_route_gate = fail
```

No-VWAP route can pass 21A project adaptation but must set：

```text
alpha158_exact_local_materialization = false
exact_replication_reachable = false
feature_claim = registered_no_vwap_project_adaptation
mandatory_arm_feature_route_ids = singleton(primary_feature_route_id)
primary_contrast_feature_route_ids = singleton(primary_feature_route_id)
```

### 17.3 Architecture/readiness logic

```text
paper_architecture_project_adaptation_reachable =
    paper_source_lineage_gate == pass
    and paper_formula_contract_gate == pass
    and vwap_qfq_unit_contract_gate == pass
    and volume_corporate_action_semantics_gate == pass
    and feature_materialization_route_gate == pass
    and pit_membership_timing_gate == pass
    and decision_denominator_contract_gate == pass
    and feature_sequence_support_gate == pass
    and feature_label_alignment_gate == pass
    and train_teacher_inference_graph_gate == pass
    and gradient_teacher_isolation_gate == pass
    and architecture_shape_gate == pass
    and loss_reduction_gate == pass
    and model_arm_and_fairness_gate == pass
    and split_purge_gate == pass
    and historical_holdout_firewall_gate == pass
    and search_budget_gate == pass
    and seed_randomness_gate == pass
    and dependency_lock_gate == pass
    and gpu_dry_run_gate == pass
    and metric_multiplicity_gate == pass
    and economic_execution_freeze_gate == pass
    and forward_refit_contract_gate == pass
```

Success：

```text
21A_preoutcome_architecture_contract_ready =
    all(critical_gates == pass)
    and paper_architecture_project_adaptation_reachable == true
    and exact_replication_reachable == false
    and historical_sample_role == design_contaminated_historical
    and historical_support_claim_allowed == false
    and outcome_columns_detected_count == 0
    and outcome_formula_executed_count == 0
    and real_model_score_count == 0
```

### 17.4 Implementation-readiness gate

`implementation_readiness_gate=pass` 需要：

```text
all identity/path aliases resolve without absolute path
all output artifacts and minimum schemas enumerated
all primary numeric choices non-placeholder
all formula/page anchors human-authorized
all shape/loss/graph choices unique
all split/purge dates/rules unique
all arm/search/seed/multiplicity choices closed
all dependency specs exact and lock-auditable
all decision states and precedence enumerated
all validation commands present
no TBD / TODO / choose later / best effort in resolved config
```

### 17.5 Failure precedence

`blocking_reasons` 列出全部失败 gate。`decision_state` 按固定 first-match：

```text
1  outcome_firewall_gate fail
   -> 21A_outcome_firewall_violated

2  freeze_bundle_hash_gate fail
   -> 21A_manifest_or_hash_blocked

3  human_restart_scope_gate fail
   -> 21A_human_restart_or_scope_blocked

4  paper_source_lineage_gate or paper_formula_contract_gate fail
   -> 21A_paper_source_lineage_blocked

5  alpha158_expression_gate fail
   -> 21A_alpha158_expression_contract_blocked

6  vwap_qfq_unit_contract_gate or volume_corporate_action_semantics_gate
   or feature_materialization_route_gate or feature_sequence_support_gate fail
   -> 21A_feature_materialization_contract_blocked

7  pit_membership_timing_gate or decision_denominator_contract_gate
   or feature_label_alignment_gate fail
   -> 21A_pit_timing_or_denominator_contract_blocked

8  train_teacher_inference_graph_gate or gradient_teacher_isolation_gate
   or architecture_shape_gate or loss_reduction_gate or model_arm_and_fairness_gate fail
   -> 21A_architecture_graph_or_shape_contract_blocked

9  split_purge_gate or historical_holdout_firewall_gate or search_budget_gate
   or seed_randomness_gate or metric_multiplicity_gate or economic_execution_freeze_gate
   or forward_refit_contract_gate fail
   -> 21A_split_search_or_statistics_contract_blocked

10 dependency_lock_gate or gpu_dry_run_gate fail
   -> 21A_dependency_lock_or_gpu_contract_blocked

11 implementation_readiness_gate fail
   -> 21A_contract_not_impl_ready
```

Official code/appendix unavailable、exact replication false、full VWAP route unavailable但 no-VWAP route ready、batch size机械下降都不能
覆盖上述顺序或单独造成 21A failure。

## 18. 中文 report contract

`21A_paper_lineage_pit_data_and_architecture_contract_report.md` 至少包含：

1. 一页 decision summary 和 blocking/capability 表；
2. human restart、历史污染与授权边界；
3. local PDF/DOI/author/page/hash、formula authorization 和 official code/appendix 状态；
4. exact replication false 与 project adaptation claim ceiling；
5. PIT membership、signal/execution timing、U_t_membership/U_t_decision；
6. 三种 label 语义和“21A 未 materialize label”的证据；
7. qfq/raw unit、factor/VWAP audit和 primary feature route；
8. Alpha158 canonical count/expression hash、no-VWAP route与 volume factor-jump sensitivity；
9. feature-only support、normalization/missingness 和 split/purge；
10. source/teacher/inference graph、shape、teacher isolation、loss reductions；
11. 10 mandatory arms、K1C train/inference global-mixture、K1C/R1 matching、公平性与 nested contrasts；
12. primary config、batch ladder、seed/search budget；
13. dependency lock、GPU fingerprint、synthetic dry-run与 selected batch；
14. RankIC tie/undefined-day规则、validation/historical complete-day minima、Holm family、291-day forward power和 economic boundaries；
15. 21F M1/M3 comparator、deterministic refit、static cohort 与 module-attribution边界；
16. next requirement generation/execution authorization。

报告必须逐字包含：

```text
21A 没有训练或评价任何真实 outcome model，也没有生成真实股票 score、RankIC 或策略 PnL。

EP21 只能声明 paper_architecture_grounded_project_adaptation，不能声明 exact_replication 或 paper_result_reproduced。

历史 2017-01 至 2026-05 已被本 topic 反复观察，只能作为 design_contaminated_historical；可信支持只能来自最终候选密封后的 forward cohort。

U_t_decision 在 outcome 前固定；unknown data gap 和 data cutoff 使整日不可评价，不允许逐股静默删除后改变 denominator。

Primary REAKA 对全部 T 个 shifted transitions 计算 Koopman 和 residual loss；last-transition-only 只能是独立 diagnostic adaptation。

Teacher tensors 只允许构造 train-only Koopman/residual target，并经 residual_target->x_s 影响训练重构/loss；不进入 selector、gate、residual condition 或任何 inference-score ancestor。

Official code 或 appendix 未披露不阻断 project adaptation，但必须限制复现 claim。

21F 只前瞻确认 R2 相对预冻结 M1/M3 的预测与执行；21C/21D 模块归因仍是 historical_design_diagnostic。

21A 成功只允许生成并人工评审 21B requirement，不授权 21B 执行、historical holdout readout、policy、optimization 或 deployment。
```

所有数字必须来自 machine-readable freeze artifacts；不得手写与 CSV/JSON 不一致的报告数字。

## 19. Implementation pattern 与测试要求

### 19.1 Implementation pattern

建议 runner 内部保持以下纯函数边界：

```text
resolve_paths_and_hashes(config) -> input audits
audit_paper_sources_and_authorization(...) -> paper registries
extract_canonical_alpha158_from_locked_qlib(...) -> expression registry/hash
audit_qfq_raw_units_and_vwap(...) -> feature route decision
build_feature_only_support(...) -> U_t_decision counts/cache manifest
freeze_label_and_resolution_contracts(...) -> pure contract tables
build_synthetic_architecture(config) -> graph/shape/parameter registry
run_synthetic_graph_and_gpu_tests(...) -> dry-run audits
freeze_split_search_metric_forward_contracts(...) -> contract tables
evaluate_21a_gates(...) -> one decision row
seal_freeze_bundle(...) -> immutable hashes
finalize_from_freeze_only(...) -> report/decision/final hashes
```

Network acquisition、market audit、synthetic architecture 和 finalize 不得混成单一函数。Gate evaluation 只能消费 machine-readable
artifacts，不能依赖 report prose。

Tests that invoke any stage must use `tmp_path`/temporary output and reference roots。测试不得调用 runner 覆盖 production
`REFERENCE_ROOT`、sealed freeze bundle、root report、manifest或hash files；production bundle tests只能 read/verify。

### 19.2 Required tests

测试至少覆盖：

```text
1. Identity、contract version、config/runner/test/output path 与 requirement 完全一致。
2. 所有 alias repository-relative；source/output 中不出现 /home/xiaolv 或 file://。
3. research plan hash和 paper SHA/page count mismatch fail closed。
4. PDF/DOI/title/five-author identity 任一不一致使 paper source gate fail。
5. acquire-sources 只访问 URL allowlist，market/upstream/outcome read counts为0。
6. official-code candidate list为空时输出 not_disclosed，不伪造 official repo且不阻断 project adaptation。
7. formula draft/hash/review packet/human authorization四者一致；缺授权时 formula gate fail。
8. formula registry每个 required formula有 page/anchor/canonical project mapping；`see paper` 不通过。
9. exact replication与 paper-result claims恒 false，不能被 local data coverage改写。

10. forbidden-column scanner大小写/前后缀/嵌套派生名均 fail closed。
11. label formula字符串只允许出现在 label contract；任何真实执行 negative Ref 或 t+1 join fail。
12. default Alpha158 label loader不得实例化；feature-only extraction可运行。
13. pyqlib resolved version必须0.9.7；source hash变化导致 expression gate fail/new version。
14. canonical expression count恰好158、顺序稳定、名字唯一、future-offset count=0。
15. alpha158_expression_hash bytes和公式可独立复算。
16. full/no-VWAP route从 expression dependency机械生成，不能手写 feature allowlist。

17. qfq/raw key uniqueness、OHLC ordering、shares/hands exactly-once conversion可复算。
18. factor consensus和 VWAP candidate在 synthetic corporate-action bars上方向正确。
19. factor/range/overlap/auditable-coverage thresholds边界值使用 >=；base/auditable/range denominators逐层可复算。
20. Full VWAP fail而 non-VWAP pass时 deterministic选择 registered primary route adaptation、exact-local=false，并被所有arms/C0-C4共享。
21. 两条 route都不可用时 feature materialization gate fail。
22. factor jump threshold/radius固定；quarantine只按date/window，不读取 outcome。
23. robust median/IQR scale、constant-column、clip和invalid fill在synthetic features上可复算。

24. membership key唯一，membership_date到usable_trade_date严格下一 exchange session。
25. executable universe不能替代 signal-time membership；CSI300 current constituents不能参与filter。
26. U_t_decision只依赖<=t history/feature readiness，t+1 bar presence变化不能改变构造函数输出。
27. suspension carry、unknown gap、prelisting和non-exchange day policy synthetic tests通过。
28. U_t_resolved必须完整等于U_t_decision；unknown/data cutoff触发整日不可评价。
29. model-specific score missing不能通过intersection缩小denominator。
30. train/validation/holdout support counts只用feature/date，不包含label summary。

31. Nominal/effective split和12-session left-tail purge按exchange calendar精确复算。
32. random row split、calendar-day purge或把purged rows移到右split均fail。
33. validation allowed/forbidden selection字段完全闭合。
34. historical holdout outcome access count为0；unseal policy只能一次且在全部checkpoint seal后。

35. 所有Section 9 tensors exact shape，无implicit broadcasting。
36. K_selected batched matrix multiplication与显式einsum reference一致。
37. Source相同、teacher扰动时inference score不变；只允许train target/noising/reconstruction/loss变化。
38. Teacher可走residual_target->x_s训练边，但不在selector/gate/residual condition或任何inference-score ancestor graph。
39. Primary L_koop gradient到shared encoder；stop-gradient primary会fail。
40. 所有T transitions对L_koop/L_diff有贡献；last-only不能标primary。
41. MeanValid loss在batch精确复制时数值不变；time sum实现fail。
42. L_forecast只在L_rec内出现一次；score index为last shifted scalar。
43. DDPM eight-draw mean和stable row-key seed对batch reorder不变。
44. Module topology、initialization、tau和beta schedule与contract完全一致；GateNet恰好一次sigmoid。

45. mandatory arm恰好10个，M0不训练、不进入positive baseline gate。
46. 每个arm DAG/loss/score contract完整且共享target/split/feature route；A0 direct forecast和R1 residual loss可独立复算。
47. K1C每个training step只抽一个global Gumbel vector，train/inference mixture均跨batch/time相同且不读取Z/H_y/row key。
48. R1 hidden width只按parameter-count closest rule选择；不读取outcome；±10% gate可复算。
49. Primary config恰好1个，scheduled R2 sensitivity恰好6个且one-factor-at-a-time。
50. Selected no-VWAP primary route可进入C0-C4；仅non_primary_diagnostic_adaptation_ids禁止promote/进入C0-C4；attempts全保留。
51. 三model seeds及各RNG stream派生规则完全一致；best seed不能primary。

52. Project lock缺torch时即使ambient torch存在，dependency gate仍fail。
53. Locked/runtime版本不一致fail；只允许stage外显式uv sync --frozen，runner install/sync count=0且stage/test不用uv run。
54. GPU dry-run只用synthetic tensors；real instrument/date/bar access count为0。
55. Batch ladder只按256->128->64->32->16下降；不得变architecture/precision。
56. Peak memory cap、finite gradients、same-seed 1e-7 determinism和minimum batch gate可复算。

57. RankIC使用float64 average-rank Pearson；score/label ties、zero variance、nonfinite和full-denominator day failure语义冻结。
58. Validation full/early/late=200/80/80、historical representation/economic=252/252 complete-day minima边界精确。
59. 七个contrast/margin与Section 14.2.1 shared-index stationary bootstrap/Holm算法逐replicate完全一致。
60. Slice thresholds只在training period用<=t fields拟合；C4 tail之外均diagnostic。
61. Forward power公式独立复算为291 complete days；股票行不得当iid evidence。
62. 60/126/291 evidence ladder边界无off-by-one。
63. EP19/20 execution/cost/AUM/ADV rules逐字段一致，hash mismatch fail。
64. Top30 gross proxy与next-open executable ledger分表且claim role不同。
65. M1/M3 comparator身份在holdout前固定；final refit不允许新early stopping。
66. First 291 complete forward days无rolling retrain/normalizer refresh/version拼接。
67. Forward minimum scope不声明module attribution。

68. Preoutcome access log hard counts全部为0且文件访问白名单闭合。
69. Freeze manifest expected_paths/output_hashes/exclusion sets和actual files双向一致，无extra/missing且self exclusions exact。
70. Sealed bundle不能覆盖；输入变化要求新contract version。
71. Finalize access audit只含manifest-listed freeze reads；raw/unmanifested input read count=0。
72. Gate evidence required check sets exact；missing/duplicate/not-evaluable row使对应gate fail；decision恰好一行且precedence稳定。
73. Success不要求official code、appendix、exact replication或full VWAP route，但必须有可行primary feature route。
74. Success时next requirement只允许generation，不允许execution；所有policy/deployment flags=false。
75. 中文报告包含Section 18全部边界短语，数字与machine-readable artifacts一致。
76. 所有stage-invoking tests使用temporary roots；测试前后production report/manifest/hash bytes完全不变。
77. authoring/reference与两个manifest expected_paths中的全部publishable text（含untracked生成物）逐文件no-index whitespace check通过。
```

## 20. Validation commands

在实现完成、dependency extra 已人工评审后：

```bash
uv lock --check
uv sync --frozen --extra reaka --extra dev

PYTHON=.venv/bin/python
test -x "$PYTHON"

"$PYTHON" \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21a_paper_lineage_pit_data_and_architecture_contract.py \
  --config experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/configs/config_21a_paper_lineage_pit_data_and_architecture_contract.yaml \
  --stage acquire-sources

# Mandatory human pause: review formula_review_packet.md and create the authorization JSON manually.
test -f \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/references/21a/formula_review_authorization.json

"$PYTHON" \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21a_paper_lineage_pit_data_and_architecture_contract.py \
  --config experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/configs/config_21a_paper_lineage_pit_data_and_architecture_contract.yaml \
  --stage freeze

"$PYTHON" \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21a_paper_lineage_pit_data_and_architecture_contract.py \
  --stage finalize \
  --output-root experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/outputs/21A_paper_lineage_pit_data_and_architecture_contract_v2

"$PYTHON" -m pytest \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/tests/test_21a_paper_lineage_pit_data_and_architecture_contract.py -q

git diff --check -- \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0 \
  pyproject.toml requirements.txt uv.lock

# This set includes untracked authoring/reference files, both manifests' expected_paths,
# and every actual publishable text file under the output root, so generated text cannot escape whitespace checks.
while IFS= read -r path; do
  test -s "$path" || exit 1
  check_output="$(git diff --no-index --check /dev/null "$path" 2>&1)"
  rc=$?
  if test "$rc" -gt 1 || test -n "$check_output"; then
    printf '%s\n' "$check_output" >&2
    exit 1
  fi
done < <(
  "$PYTHON" - <<'PY'
import json
from pathlib import Path

episode = Path("experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0")
output_root = episode / "outputs/21A_paper_lineage_pit_data_and_architecture_contract_v2"
text_suffixes = {".csv", ".json", ".lock", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
paths = {
    Path("pyproject.toml"),
    Path("requirements.txt"),
    Path("uv.lock"),
    episode / "requirement_21a_paper_lineage_pit_data_and_architecture_contract.md",
    episode / "configs/config_21a_paper_lineage_pit_data_and_architecture_contract.yaml",
    episode / "src/run_21a_paper_lineage_pit_data_and_architecture_contract.py",
    episode / "tests/test_21a_paper_lineage_pit_data_and_architecture_contract.py",
}
references = episode / "references/21a"
paths.update(p for p in references.rglob("*") if p.is_file() and p.suffix.lower() in text_suffixes)

manifest_paths = [
    output_root / "freeze/freeze_bundle_manifest.json",
    output_root / "manifest_21a_paper_lineage_pit_data_and_architecture_contract.json",
]
for manifest_path in manifest_paths:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative_path in manifest["expected_paths"]:
        artifact = output_root / relative_path
        if not artifact.is_file():
            raise SystemExit(f"manifest expected path missing: {artifact}")
        if artifact.suffix.lower() in text_suffixes:
            paths.add(artifact)

paths.update(p for p in output_root.rglob("*") if p.is_file() and p.suffix.lower() in text_suffixes)
for path in sorted(paths, key=lambda value: value.as_posix()):
    if not path.is_file():
        raise SystemExit(f"publishable text path missing: {path}")
    print(path.as_posix())
PY
)

# After explicit narrow staging for publish:
git diff --cached --check -- \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0 \
  pyproject.toml requirements.txt uv.lock
```

本 requirement 的生成不授权执行上述命令；只有用户后续明确要求 implementation/run 才执行。

## 21. Acceptance checklist

```text
[ ] 21A scope只包含pre-outcome paper/data/architecture/statistics/runtime contract。
[ ] Research-plan和PDF expected hashes匹配。
[ ] Paper identity、formula page/anchor和human authorization闭合。
[ ] Official code/appendix状态真实，claim ceiling不超过project adaptation。
[ ] Alpha158从locked pyqlib 0.9.7提取，count=158且expression hash可复算。
[ ] Alpha158 feature loader不含default future label。
[ ] qfq/raw factor、VWAP和unit thresholds完整；full/no-VWAP route deterministic且selected route被全部arms/C0-C4共享。
[ ] Raw-share volume、factor-jump radius和quarantine sensitivity冻结。
[ ] PIT membership/timing、U_t_decision和整日resolution contract闭合。
[ ] 21A没有materialize真实label、score、RankIC或PnL。
[ ] Feature-only support、normalization和missingness合同闭合。
[ ] Full T-step graph冻结允许的teacher train-noising edges与禁止的inference ancestors，shape、gradient和loss唯一。
[ ] DDPM topology、sampling和batch-order-independent RNG冻结。
[ ] Mandatory arms恰好10个；K1C train/inference均为global mixture，K1C和R1容量匹配规则可复算。
[ ] Primary config唯一、six sensitivities、adaptation边界和三seed冻结。
[ ] Chronological split、12-session purge、validation selection和holdout firewall闭合。
[ ] Project lock包含exact torch runtime；显式frozen bootstrap与stage process-bootstrap边界闭合，无ambient-only或runner silent install。
[ ] Synthetic GPU full-graph dry-run通过且selected batch>=16。
[ ] RankIC average-rank/tie/undefined规则、validation/historical最小complete days、七contrast、Holm和291-day power冻结。
[ ] Top30 execution/cost/risk与EP19/20A一致且hash闭合。
[ ] M1/M3 forward comparator、deterministic refit和static cohort冻结。
[ ] 所有required artifacts/schema存在，manifest/hash双向一致。
[ ] Outcome firewall hard counts全部为0。
[ ] Finalize无raw input read。
[ ] 中文报告包含全部claim/authorization边界。
[ ] Success只授权生成21B requirement，不授权21B执行或deployment。
```

## 22. 失败解释与 handoff 边界

21A 的失败只能解释为 paper/data/architecture/runtime/statistics contract 尚不可实现，不能解释为 Alpha158、Koopman、adaptive
operator、diffusion 或 Top30 无效。

必须区分：

```text
official_code_not_disclosed:
    只限制exact replication claim；不阻断paper-grounded project adaptation。

alpha158_full_vwap_route_unavailable_but_adaptation_ready:
    只能运行明确命名的no-VWAP project adaptation；不得称Alpha158-158。

feature_materialization_blocked:
    full和no-VWAP routes都无法物化；不得跳到21B手写近似features。

dependency_or_gpu_blocked:
    runtime lock或12GB full graph不可复现；不得在21B静默安装、改architecture或用CPU结果冒充GPU contract。

outcome_firewall_violated:
    当前bundle失去pre-outcome资格，必须废弃并以新contract version全量重跑。

historical_design_contaminated:
    不是21A failure，但永久禁止把历史readout写成可信support。
```

若 `21A_preoutcome_architecture_contract_ready`，handoff 仅是生成并人工评审
`requirement_21b_alpha158_sequence_baseline_benchmark.md`。21B execution、21C–21F requirement generation、historical holdout
readout、policy、optimization 和 deployment 均需后续独立人工授权。

# Requirement：20A 论文血缘、数据可得性与复制层级冻结

## 0. 不可协商范围

20A 是 EP20 的第一个、也是当前唯一获授权的可执行 requirement。它只完成以下工作：

```text
paper source and formula lineage
data availability and schema audit
exact-vs-adaptation replication ceiling
EP19 2025 static board proxy contract
U_paper vs U_project separation
execution / cost / return-semantics freeze
warm-up and sample-support preflight
economic / risk / multiplicity gate freeze
post-freeze forward boundary freeze
CNN training-support preflight
immutable pre-outcome bundle
```

20A **不得读取、连接、推导或汇总任何未来收益 outcome**，包括未来 fixed return、MFE、MAE、winner label、first-hit、
候选分组收益、策略 PnL 或 forward cohort 的结果。它不得训练因子、形成 top bucket、选择阈值、评价 TrendPV/
Residual Momentum 是否有效，也不得授权 policy、portfolio optimization 或 deployment。

本 requirement 的 primary objective 是为 `deployable_positive_beta` 建立可实现合同，不是搜索 alpha。Scale matching、
within-vol sort、factor regression 和 board control 在后续阶段只用于解释收益来源；matching 后增量为零不得在 20A 被
预注册为失败。

20A 的唯一成功 decision state 是：

```text
decision_state = 20A_preoutcome_contract_ready
```

它只表示 `project_adaptation_reachable=true`、`forward_beta_test_reachable=true` 且所有 pre-outcome 合同已冻结。
`exact_replication_reachable` 可以为 false 而不阻断该成功态。成功后也不能自动运行 20B；必须另有人工批准。

成功时：

```text
next_allowed_requirement = requirement_20b_trendpv_residual_momentum_design_and_replication_diagnostic.md
next_requirement_generation_authorized = true
next_requirement_execution_authorized = false
policy_training_authorized = false
policy_replay_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

Fail-closed states：

```text
20A_human_restart_lineage_blocked
20A_paper_contract_blocked
20A_project_data_contract_blocked
20A_execution_contract_blocked
20A_residual_primary_contract_blocked
20A_outcome_firewall_violated
20A_forward_contract_blocked
20A_economic_gate_not_frozen
20A_search_accounting_blocked
20A_manifest_or_hash_blocked
20A_contract_not_impl_ready
```

以下是非阻断的 capability 状态，不得误写为整个 20A 失败：

```text
exact_replication_not_reachable
historical_design_underpowered
historical_pit_industry_unavailable
risk_free_or_ch3_factor_unavailable
cnn_underpowered_not_evaluable
```

## 1. 身份与执行阶段

```text
experiment_id = 20_ohlcv_positive_beta_exposure_research
phase_id = 20A
run_id = 20A_paper_lineage_data_and_replication_contract
contract_version = 20A_v2
requirement_file = requirement_20a_paper_lineage_data_and_replication_contract.md
config_file = configs/config_20a_paper_lineage_data_and_replication_contract.yaml
runner_file = src/run_20a_paper_lineage_data_and_replication_contract.py
test_file = tests/test_20a_paper_lineage_data_and_replication_contract.py
```

执行工作目录：

```bash
cd topics/02_AFML_BIG_WINNER
```

20A 只允许三个 stage：

```text
acquire-sources
freeze
finalize
```

- `acquire-sources` 只允许从 Section 6 的论文 URL allowlist 下载/缓存论文与 appendix，并基于这些本地材料生成
  `paper_formula_registry_draft.csv`；不得读取市场数据或 outcome，draft 不得自行获得 human-verified 状态；
- `freeze` 读取 Section 5 白名单输入，只计算 coverage/schema/lineage/support，不读取 outcome；
- `freeze` 完成后必须先密封 immutable manifest/hash bundle；
- `finalize` 只能读取已经密封的 freeze artifacts，生成 root-level decision 与中文报告；
- `finalize` 不得重新读取原始市场数据、论文文件、EP19 文件或任何 outcome；
- 同一个 `run_id + contract_version` 不得覆盖已密封 bundle；输入变化必须生成新 version。

## 2. Human restart 与上游真值

EP20 是人类明确授权的 topic-level restart，不是 EP19 pipeline 自动 handoff。20A 必须从 EP20 research plan 冻结以下
事实：

```text
episode_id = 20_ohlcv_positive_beta_exposure_research
supersedes_draft_id = 20_ohlcv_directional_alpha_replication
restart_type = topic_level_human_restart
primary_objective = deployable_positive_beta
incremental_alpha_required = false
EP19_B2_role = frozen_daily_event_reference_not_project_arm
historical_sample_role = design_contaminated_historical
support_source = post_contract_freeze_forward_only
```

权威 planning input：

```text
EXPERIMENT_ROOT/research_plan.md
EXPERIMENT_ROOT/requirement_20a_paper_lineage_data_and_replication_contract.md
```

EP19 的 final report 和 outcome tables 不是 20A 的 objective authority，也不在 `freeze` 读取白名单中。20A 不得因为
EP19 报告中保留了旧的 `directional-alpha-first` 草案文字而恢复 alpha gate。B2 的 role 与约 +33% exposure 描述只从
EP20 research plan 读取；20A 不复算 B2 outcome。

必须输出：

```text
freeze/human_restart_authorization.json
freeze/upstream_scope_audit.csv
```

`human_restart_authorization.json` 至少包含：

```text
episode_id
phase_id
authorization_type
authorization_source = user_requested_20A_requirement_generation
authorization_recorded_date = 2026-07-10
primary_objective
incremental_alpha_required
upstream_automatic_authorization
research_plan_path
research_plan_sha256
requirement_path
requirement_sha256
```

## 3. 20A 只回答的问题

```text
Q1. 每篇核心论文的 version-of-record、完整正文、附录/代码、公式、样本、warm-up、universe、
    weighting、holding period 和限制能否形成可复算 registry？

Q2. 当前本地数据能否支持 U_project 上的 paper-grounded adaptation？

Q3. 当前或显式配置的数据能否支持 U_paper 的 exact replication；若不能，具体阻断在宽截面 PIT
    market-cap、E/P、historical industry、risk-free、CH-3 vintage 还是历史长度？

Q4. EP19 2025-01-02 东方财富概念板块 snapshot 能否作为冻结的 multi-label static industry proxy，
    同时不声称它是 historical PIT industry？

Q5. TrendPV、total momentum、residual adaptation、Low Vol、FIP、MA20 与 CNN 的公式和研究角色能否在
    outcome access 前冻结？

Q6. U_paper 与 U_project、paper return 与 executable return、exact 与 adaptation 能否保持不同 denominator
    和 claim semantics？

Q7. 1-month next-open label、成本、现金、容量、正 beta、左尾/回撤和 multiplicity gates 能否在 outcome access
    前冻结？

Q8. post-freeze forward 的日期边界、6/12/126 decision-month evidence 分级和 label-complete 规则能否机械化？

Q9. CNN 是否具备足够 train/validation/test 日历支持；若不足，能否 fail closed 为 not evaluable？
```

20A 不回答任何信号是否有效，也不回答 exact paper result 是否可复制。

## 4. Allowed / forbidden work 与 outcome firewall

### 4.1 允许工作

```text
1. 读取并 hash Section 5 白名单的 planning、schema、OHLCV、calendar、universe、board 和 cost inputs。
2. 读取文件名、header、dtype、row count、key uniqueness、date min/max、missingness 和 instrument coverage。
3. 计算仅依赖历史可见数据长度的 warm-up eligibility 和 calendar support。
4. 计算 U_project 与 qfq/board proxy 的 instrument overlap；不得连接 future return。
5. 建立 paper source、formula、field mapping、role 和 claim registry。
6. 对可选 exact-data path 做存在性、schema、PIT timing 和 coverage audit。
7. 冻结 project adaptation 公式、paper-exact 公式和 deferred routes。
8. 冻结 execution、cost、cash、capacity、risk、multiplicity 与 forward boundary。
9. 输出 machine-readable go/no-go、immutable hashes 和中文 contract report。
10. 只读 Section 5 明列的 EP19 B2 pre-outcome manifests/registries，核对 family/grid/parameter/trim rule hashes。
```

### 4.2 禁止工作

```text
1. 不读取任何列名匹配 future_*, forward_return*, MFE*, MAE*, winner*, hit_*, label*, pnl*。
2. 不读取 EP19 19B/19B1/19B2/19B3 的 outcome tables 或 reports 以选择 arm/gate；Section 5 明列且
   `frozen_before_*_outcome=true` 的 B2 rule manifests/registries 是唯一例外。
3. 不计算 next-month/5d/20d/60d/120d forward returns。
4. 不生成 signal score、rank IC、bucket return、top-minus-bottom、matched lift 或 strategy NAV。
5. 不训练 regression/CNN，不估计 factor beta，不选择 ridge penalty、window、bucket 或 threshold。
6. 不把 qfq 文件数量近似全市场解释为宽截面 PIT universe 已可用。
7. 不把 2025 board proxy 解释为 2025 年以前的 PIT industry。
8. 除 `acquire-sources` 的论文 URL allowlist 外，不通过网络下载 E/P、risk-free、CH-3、industry 或市场数据；
   新增 market/fundamental 源必须先显式写入 config。
9. 不用缺失 exact-data 状态阻断已满足的 project adaptation contract。
10. 不授权 20B 执行、policy、replay、optimization 或 deployment。
```

### 4.3 字段级 firewall

`freeze` 中允许读取的市场字段白名单：

```text
date / trade_date / usable_trade_date / source_trade_date / source_asof_date
instrument / ts_code / con_code / board_bucket / board_ts_code / board_name / idx_type
exchange / name / listing_date / delist_date / is_delisted
open / high / low / close / volume / money / turnover_rate
is_listed / is_st / is_suspended
raw_unadjusted_close / total_share_asof / total_market_cap_cny
membership_date / membership_available_time / available_time
source_* / *_rule_version / *_status / *_reason
minimum_history_sessions / history_observed_sessions_before_usable_date / history_ready_240d_flag
rule_id / is_st / effective_start_date / effective_end_date / listing_session_min / listing_session_max
daily_limit_up_rate / daily_limit_down_rate / no_limit_flag / tick_size / rounding_rule / human_verified
transfer_fee_buy_bps / transfer_fee_sell_bps
```

只允许派生：

```text
row_count
unique_instrument_count
unique_date_count
date_min / date_max
missing_rate
duplicate_key_count
history_session_count_asof_date
warmup_eligible_flag
normalized_instrument
listing_session_number
verified_rule_mapping_flag
order_lot_rule_mapping_flag
schema_hash / artifact_hash / root_inventory_hash
instrument_overlap_count / overlap_rate
monthly_eligible_count
```

任何 forbidden column 被读取或任何 outcome-derived artifact 被发现进入输出：

```text
outcome_firewall_gate = fail
decision_state = 20A_outcome_firewall_violated
```

## 5. 输入与路径别名

所有路径必须是 repository-relative 或从以下 alias 解析。禁止硬编码 `/home/xiaolv/...`。

```text
REPO_ROOT = ../..
TOPIC_ROOT = .
EXPERIMENT_ROOT = experiments/pending/20_ohlcv_positive_beta_exposure_research
EP19_ROOT = experiments/pending/19_entry_universe_pit_tradability_preflight

PROJECT_UNIVERSE_FILE = data/processed/universe/pit_topn_400_100_executable_daily.csv
QFQ_ROOT = data/raw/akshare/day/qfq
RAW_OHLCV_ROOT = data/raw/akshare/day/raw
BENCHMARK_FILE = data/processed/index/benchmark_indices_daily.csv
TRADING_CALENDAR_FILE = data/raw/akshare/status/trading_calendar.csv
SECURITY_MASTER_FILE = data/raw/akshare/status/instrument_metadata_target_universe.csv
SH_NAME_HISTORY_ROOT = data/raw/akshare/status/sh_name_history
STATUS_ROOT = data/raw/akshare/status

PAPER_CACHE_ROOT = EXPERIMENT_ROOT/references/papers
PAPER_SOURCE_MATERIAL_ROOT = PAPER_CACHE_ROOT/source_materials
PAPER_FORMULA_DRAFT_FILE = PAPER_CACHE_ROOT/paper_formula_registry_draft.csv
MARKET_RULE_REGISTRY_FILE = EXPERIMENT_ROOT/references/market_rules/a_share_price_limit_rules_v1.csv

EP19_19A_OUTPUT_ROOT = EP19_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract
EP19_COST_FILE = EP19_19A_OUTPUT_ROOT/replay_cost_assumption_freeze.csv
EP19_EXECUTION_FILE = EP19_19A_OUTPUT_ROOT/entry_execution_convention_audit.csv

EP19_B2_SELECTED_MANIFEST = EP19_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/selected_family_cell_manifest.csv
EP19_B2_GRID_MANIFEST = EP19_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/grid_cell_manifest.csv
EP19_B2_FEATURE_MAP = EP19_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/simple_rule_feature_source_map.csv
EP19_B2_OUTPUT_HASHES = EP19_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/output_hashes_19b0_fast_rule_grid_enrichment_scan.json
EP19_B2_BUDGET_REGISTRY = EP19_ROOT/outputs/19B3_b2_positive_exposure_left_tail_budget_frontier/freeze/b2_arm_registry.csv

EP19_BOARD_ROOT = EP19_ROOT/outputs/tushare_dc_yearly_board_snapshot
EP19_BOARD_2025_INDEX_FILE = EP19_BOARD_ROOT/by_year/2025/dc_index_2025_20250102_概念板块.csv
EP19_BOARD_2025_MEMBER_FILE = EP19_BOARD_ROOT/by_year/2025/dc_member_2025_20250102.csv
EP19_BOARD_README = EP19_BOARD_ROOT/README.md
EP19_BOARD_MAPPING_FILE = EP19_BOARD_ROOT/metadata/classification_year_snapshot_mapping.csv
EP19_BOARD_SUMMARY_FILE = EP19_BOARD_ROOT/metadata/dataset_summary.csv
```

### 5.1 必需输入

```text
EXPERIMENT_ROOT/research_plan.md
EXPERIMENT_ROOT/requirement_20a_paper_lineage_data_and_replication_contract.md
PROJECT_UNIVERSE_FILE
QFQ_ROOT/*.csv
RAW_OHLCV_ROOT/*.csv
BENCHMARK_FILE
TRADING_CALENDAR_FILE
SECURITY_MASTER_FILE
SH_NAME_HISTORY_ROOT/*.csv
EP19_COST_FILE
EP19_EXECUTION_FILE
EP19_B2_SELECTED_MANIFEST
EP19_B2_GRID_MANIFEST
EP19_B2_FEATURE_MAP
EP19_B2_OUTPUT_HASHES
EP19_B2_BUDGET_REGISTRY
EP19_BOARD_2025_INDEX_FILE
EP19_BOARD_2025_MEMBER_FILE
EP19_BOARD_README
EP19_BOARD_MAPPING_FILE
EP19_BOARD_SUMMARY_FILE
PAPER_CACHE_ROOT/source_acquisition_manifest.csv
PAPER_SOURCE_MATERIAL_ROOT/*
PAPER_FORMULA_DRAFT_FILE
PAPER_CACHE_ROOT/formula_review_authorization.json
MARKET_RULE_REGISTRY_FILE
```

### 5.2 可选 exact-data 输入

Config 必须显式包含以下列表；当前没有可信文件时必须是空列表 `[]`，不得做 filesystem-wide 猜测：

```yaml
optional_exact_sources:
  wide_pit_market_cap_files: []
  pit_earnings_to_price_files: []
  historical_pit_industry_files: []
  risk_free_return_files: []
  china_ch3_factor_files: []
  corporate_action_factor_vintage_files: []
```

新增文件只能在首次 `freeze` seal 前由人工更新 config。`freeze` 密封后不得原地增加；必须升级 `contract_version`。

### 5.3 输入 hash

- 小文件逐文件 SHA-256；
- `QFQ_ROOT` 每个 CSV 逐文件 SHA-256，并对按相对路径排序的 `path|size|sha256` 记录再做 root digest；
- 不得以 mtime 代替内容 hash；
- 可选输入即使为空也必须在 manifest 记录空列表 hash；
- `git_tracked` 只作信息字段；本地未被 Git 跟踪不等于不可用，但必须可复算 lineage。

## 6. Paper source registry

`freeze/paper_source_registry.csv` 至少覆盖以下 source families：

| source_id | 版本与用途 |
|---|---|
| `trend_china_vor_2024` | Liu, Liu, Zhou, Zhu，RAPS 14(2), 348–380，DOI `10.1093/rapstu/raae003` |
| `trend_china_full_working_paper` | 完整方法与 appendix working paper |
| `trend_china_internet_appendix` | 作者 internet appendix |
| `residual_momentum_vor_2011` | Blitz, Huij, Martens，JEF 18(3), 506–521，DOI `10.1016/j.jempfin.2011.01.003` |
| `china_anomalies_vor_2021` | Jansen, Swinkels, Zhou，PBFJ 68, 101607，DOI `10.1016/j.pacfin.2021.101607` |
| `china_size_value_vor_2019` | Liu, Stambaugh, Yuan，JFE 134(1), 48–69，DOI `10.1016/j.jfineco.2019.03.008` |
| `fip_vor_2014` | Da, Gurun, Warachka，RFS 27(7), 2171–2218，DOI `10.1093/rfs/hhu003` |
| `china_low_vol_vor_2021` | Blitz, Hanauer, van Vliet，JAM 22, 338–349，DOI `10.1057/s41260-021-00218-0` |
| `ma_portfolio_timing_vor_2013` | Han, Yang, Zhou，JFQA 48(5), 1433–1461，DOI `10.1017/S0022109013000586` |
| `ohlcv_cnn_vor_2023` | Jiang, Kelly, Xiu，JF 78(6), 3193–3249，DOI `10.1111/jofi.13268` |
| `technical_fdr_vor_2012` | Bajgrowicz, Scaillet，JFE 106(3), 473–491，DOI `10.1016/j.jfineco.2012.06.001` |

`acquire-sources` 的 full-text allowlist 固定为：

```text
trend_china_full_working_paper =
https://acfr.aut.ac.nz/__data/assets/pdf_file/0014/324113/Y-Liu-New-TrendChina_12_1_WithAppendix.pdf

trend_china_internet_appendix =
https://guofuzhou.github.io/TrendChina_Appendix.pdf

residual_momentum_full_paper =
https://repub.eur.nl/pub/22252/ResidualMomentum-2011.pdf

china_anomalies_full_paper =
https://pure.eur.nl/ws/files/58642799/Anomalies_in_the_China_A_share_market.pdf

china_size_value_full_paper =
https://faculty.wharton.upenn.edu/wp-content/uploads/2018/03/Size-and-Value-in-China.pdf

china_size_value_appendix =
https://finance.wharton.upenn.edu/~stambaug/size_value_china_appendix_2_rev.pdf

fip_full_working_paper =
https://business.uq.edu.au/sites/default/files/events/files/mitch-warachka-paper.pdf

china_low_vol_full_article =
https://link.springer.com/article/10.1057/s41260-021-00218-0

ma_portfolio_timing_full_paper =
https://www.nowandfutures.com/large/TA_profitability_ssrn-id1656460.pdf

ohlcv_cnn_full_paper =
https://economics.yale.edu/sites/default/files/2023-11/The%20Journal%20of%20Finance%20-%202023%20-%20JIANG%20-%20Re%25E2%2580%2590%20Imag%20in%20ing%20Price%20Trends_0.pdf

technical_fdr_accepted_manuscript =
https://archive-ouverte.unige.ch/unige:79889
```

若 allowlist URL 返回 HTML landing page，`acquire-sources` 必须保存 landing-page hash 并解析官方 PDF link；不得跟随到
非 allowlist domain。下载文件必须通过 PDF magic/header 或显式 `content_role=official_html_full_article` 检查。

下载的 PDF 或 official full-article HTML 一律写入 `PAPER_SOURCE_MATERIAL_ROOT`；manifest、draft registry 和人工授权文件
只能写在 `PAPER_CACHE_ROOT` 根目录，不得混入 source-material glob。

`PAPER_CACHE_ROOT/source_acquisition_manifest.csv` 至少包含：

```text
source_id
requested_url
resolved_url
resolved_domain
content_role
http_status
content_type
local_path
byte_size
sha256
acquired_at_utc
allowlist_gate
content_validation_gate
```

`acquire-sources` 重跑时若远端内容 hash 改变，不得覆盖旧文件；使用 content hash 后缀保存，并由人工决定是否升级
contract version。

Columns 至少为：

```text
source_id
family_id
title
authors
year
journal
volume_issue_pages
doi
version_role
version_of_record_url
full_text_url
appendix_url
replication_code_url
method_scope_used
sample_scope
paper_claim_scope
project_claim_allowed
local_copy_path
local_copy_sha256
url_metadata_status
source_registry_gate
```

`registered_not_fetched_in_20A` 只允许非核心补充 source。TrendPV、Residual Momentum、China anomalies、China
Size/Value、FIP、Low Vol、MA timing、CNN 和 technical-FDR 每个 family 至少有一份本地完整材料 hash；否则原则上
`paper_material_gate=fail`。完整 URL 必须与 research plan Section 12 一致。

`20A_v2` 接受一次性、显式、人工签署的 material waiver：

```text
waived_source_ids = {trend_china_full_working_paper, ma_portfolio_timing_full_paper}
waiver_reason = human_formula_review_completed_but_two_remote_full_text_files_are_temporarily_not_cached
local_full_text_claim_allowed_for_waived_sources = false
waiver_changes_formula_or_economic_gate = false
```

只有当 config、source manifest 和 `formula_review_authorization.json` 三者列出的 waiver source ID 完全一致、其余核心
source 全部通过 content validation、全部 formula rows 已由人工核验为 `pass`，且 authorization hash 与当前 manifest/draft
一致时，waiver 才可使 `paper_material_gate=pass`。报告必须逐项披露 waived source 没有本地 full-text/hash；不得把 waiver
写成 acquisition success，也不得据此提高 replication claim。新增或替换任何 waiver source 必须再次升级 contract version。

`paper_contract_gate` 必须同时要求：

```text
paper_material_gate = pass
all core local_copy_sha256 nonmissing
all primary formula rows have paper_section_or_equation
all implementation-choice fields in Section 7.2 nonmissing
human_formula_review_status = verified
```

不能用 requirement 自己的公式摘要循环证明 `paper_formula_verified`。

`PAPER_FORMULA_DRAFT_FILE` 必须由本地 full-text/appendix 逐行抽取形成，schema 与 Section 7.1 的最终 registry 相同，
但 `formula_gate` 只能是 `pending_human_review` 或 `pass`。`formula_review_authorization.json` 必须在 source acquisition
与 draft registry 形成后、freeze 前由人工批准，至少包含：

```text
authorization_type = paper_formula_registry_human_review
reviewed_at
reviewer
source_acquisition_manifest_sha256
reviewed_source_ids
reviewed_formula_ids
formula_registry_draft_sha256
all_implementation_choices_resolved
authorization_granted
```

`authorization_granted=false`、source/formula hash 漂移、或 v2 waiver 三方 ID 不一致时，freeze 不得开始。

## 7. Formula、arm 与 claim registry

### 7.1 Formula registry schema

`freeze/paper_formula_registry.csv` 每行一个公式/步骤，至少包含：

```text
formula_id
family_id
arm_id
arm_role
replication_role
promotion_eligible
source_id
paper_section_or_equation
formula_text
input_fields
input_frequency
lag_rule
warmup_rule
universe_rule
weighting_rule
holding_rule
missing_data_rule
regression_intercept_rule
cross_section_weighting_rule
preprocessing_and_winsorization_rule
coefficient_initialization_rule
minimum_observation_rule
zero_return_or_zero_volume_rule
tie_and_breakpoint_rule
score_standardization_rule
exact_data_dependencies
project_adaptation_changes
outcome_independent
frozen_before_outcome
formula_gate
```

### 7.2 必须冻结的公式

```text
TMOM_12_1:
    cumulative total return over prior 12 months excluding latest month

TRENDPV_MP_L / TRENDPV_MV_L:
    L in {3,5,10,20,50,100,200,300,400}
    MP = mean(close over L) / current close
    MV = mean(volume over L) / current volume

TRENDPV_MONTHLY_CS_REG:
    at each month t, regress month-t stock return on price/volume signals known at t-1;
    the project raw score is the sum of current signals multiplied by their
    pre-outcome forecast coefficients

TRENDPV_COEF_EMA:
    E_t[beta_(t+1)] = 0.98 * E_(t-1)[beta_t] + 0.02 * beta_t

TRENDPV_FULL_FACTOR:
    smallest-30%-excluded, Size median, E/P and trend 30/70, 2x3x3,
    value weighted, high-trend six minus low-trend six

RESMOM_EXACT_CH3:
    past 36 monthly excess returns on China market/size/E-P value factors;
    standardized residual performance over prior 12 months excluding latest month

RESMOM_R2_MARKET_ONLY_ADAPTATION:
    at each month s, fit stock monthly total return on an intercept and CSI300 monthly total return
    using only months s-36 ... s-1, then compute one-step residual e_i,s after month s closes;
    at each decision month-end, exclude the latest completed residual month and use the 11 residual months
    immediately preceding it; score = mean(e_i,s) / std(e_i,s, ddof=1) over those exact 11 months;
    risk-free is not required for this project adaptation

RESMOM_R3_BOARD_ADAPTATION:
    stage 1 = the same sequential 36-month market regression as R2, producing e_i,s;
    stage 2 = for each residual month s, cross-sectionally regress e_i,s on
              lagged log(total_market_cap_cny) as of s-1 and frozen EP19-2025 multi-hot board exposures;
              ridge alpha = 1.0, fit_intercept = true, predictors standardized within month;
              the resulting residual is v_i,s;
    at each decision month-end, exclude the latest completed residual month and use the 11 residual months
    immediately preceding it; score = mean(v_i,s) / std(v_i,s, ddof=1) over those exact 11 months

LOWVOL_36M:
    standard deviation of preceding 36 complete monthly total returns

FIP_ID:
    PRET = prior 12-month cumulative return excluding latest month
    ID = sign(PRET) * (% negative-return days - % positive-return days)

MA20_OVERLAY:
    sleeve held only when prior sleeve close > prior 20-session sleeve moving average

CNN_MAIN_DEFERRED:
    lookback = 20 sessions
    image_width = 60 pixels
    image_height = 64 pixels
    price_panel = OHLC bars + MA20, per-image min/max scaled
    volume_panel = bottom 20% of image
    label = sign(next 20-session return)
    exact architecture/optimizer deferred to 20F before any CNN outcome read;
    image geometry, label horizon and family count are frozen in 20A
```

`paper_formula_registry.csv` 不得只保存上面的摘要。TrendPV/Residual Momentum 的 primary/exact formula rows 必须明确：

```text
OLS/intercept and cross-sectional weighting
signal scaling/winsorization
coefficient EMA initialization and first eligible month
suspension and missing-month treatment
zero current volume treatment
36-month complete/minimum observation rule
risk-free unavailable behavior
residual score numerator/denominator and ddof
portfolio breakpoint and tie rule
```

FIP row必须明确 zero-return day 是否进入百分比分母。上述任一字段为 `unknown`、空或只写 `see paper`，
`paper_formula_gate=fail`。值必须能追溯到本地 full-text hash + page/equation/table；项目适配值另写
`project_adaptation_changes`，不得冒充论文定义。

R3 使用 2025 static board proxy 是项目适配，不是论文 exact formula。不得把“横截面收益先减去当月 CSI300 常数”冒充
market control；market residual 必须来自 stage-1 rolling time-series regression。Ridge `alpha=1.0` 是 pre-outcome fixed constant，
不得在 20B/20C 用收益选择。若后续实现认为该形式不可识别，必须回到 requirement 层修订并产生新的 contract version；
不能运行多个 penalty 后择优。

### 7.3 Arm role registry

`freeze/arm_role_registry.csv` 必须至少有：

| arm_id | role | exact claim | project positive-beta eligibility |
|---|---|---|---|
| `C0_ALL_ELIGIBLE` | full-capital baseline | no | comparator |
| `C1_TMOM_12_1` | incumbent paper comparator | paper formula | comparator |
| `C2_TRENDPV_RAW_ADAPTATION` | project primary 1 | no | yes |
| `C3_RESMOM_R3_BOARD_ADAPTATION` | preferred project primary 2 when board gate passes | no | conditional yes |
| `C3A_RESMOM_R2_MARKET_ONLY` | deterministic fallback project primary 2 | no | conditional yes |
| `P2_TREND_FULL_EXACT` | paper diagnostic | only if exact gates pass | no automatic promotion |
| `P3_RESMOM_CH3_EXACT` | paper diagnostic | only if exact gates pass | no automatic promotion |
| `C4_LOWVOL` | risk/scale comparator | no | comparator |
| `C5_EP19_B2_MONTH_END_ADAPTATION` | month-end adaptation of frozen B2 rule | no transfer of EP19 effect size | comparator |
| `C5R2_EP19_B2_MONTH_END_VOL60_TRIM` | causal same-day risk-controlled adaptation | no transfer of 19B3 effect size | comparator |
| `D1_FIP_INCREMENT` | ordered deferred challenger | no | only after historical beta-design gate |
| `E2_MA20_OVERLAY` | portfolio risk overlay | no | not an entry arm |
| `F1_CNN_ORACLE` | representation oracle | no | no policy promotion |

### 7.4 EP19 B2 rule lineage 与 EP20 timing adaptation

EP19 的原始 B2 是日频 event stream，带 10-session instrument cooldown、next-executable-open entry 和 event-conditioned
denominator；它只作为已消费的 historical reference，不直接成为 EP20 月频 project arm。必须冻结：

```text
reference_id = EP19_B2_DAILY_EVENT_REFERENCE
family_id = B2_relative_strength_breakout
grid_cell_id = B2-relative-strength-breakout__182b3d0f30f5
parameter_hash = 182b3d0f30f5c407544f209b2597ca6959a1ad8e8f94d6957345c7931da6e1a2
close_to_ema60_min = 0.0
market_regime_filter = all
return_60d_rank_pct_min = 0.9
stock_vs_market_20d_min = 0.15
selection_track = positive_beta_exposure
residual_alpha_claim_allowed = false
original_decision_frequency = daily_event_stream
original_cooldown_sessions = 10
original_entry = next_executable_open
EP19_effect_size_transfer_to_month_end_allowed = false
```

EP20 的可执行 comparator 明确改名为 adaptation：

```text
arm_id = C5_EP19_B2_MONTH_END_ADAPTATION
decision_frequency = last_SSE_open_session_of_calendar_month
formula = apply frozen B2 feature thresholds on that month-end U_project cross-section
entry = EP20 stateful portfolio next-open execution contract

arm_id = C5R2_EP19_B2_MONTH_END_VOL60_TRIM
q_vol60 = average-rank percentile of match_vol60 within the same decision-date full executable universe
candidate_p70 = pandas linear 70th percentile of q_vol60 among same-date month-end B2 candidates
formula = weight = 1[q_vol60 < same_date_candidate_p70]
tie_rule = remove_equal_threshold
cross_date_or_forward_batch_threshold_estimation_allowed = false
cash_treatment = unallocated_weight_remains_cash_no_redistribution
```

20A 只能读取 Section 5 白名单中的 pre-outcome manifests/registries，核对 B2 family/grid/parameter/feature lineage 以及
19B3 的 quantile method/tie/cash-treatment lineage。`same_date_candidate_p70` 是 EP20 新冻结的 causal timing adaptation，
不是声称从 EP19 artifact 读取的 absolute threshold。不得读取 B2/R2 的 MFE、MAE、return 或 decision outcome。必须输出：

```text
freeze/ep19_b2_preoutcome_lineage_audit.csv
```

若 family/grid/parameter hash、原始 cooldown/entry lineage 或 quantile/tie/cash rule 不一致：

```text
B2_lineage_gate = fail
decision_state = 20A_project_data_contract_blocked
```

### 7.5 Project sleeve construction freeze

Project arms 的 long-only 形成规则在 outcome access 前固定；paper-exact long-short 仍按各自 paper registry，不能与下表
混用：

| arm_id | decision-month selection | pre-trade target weight |
|---|---|---|
| `C0_ALL_ELIGIBLE` | 全部当月 U_project executable eligible | `1 / eligible_n` |
| `C1_TMOM_12_1` | score 最高 10%，见下述 tie rule | `1 / selected_n` |
| `C2_TRENDPV_RAW_ADAPTATION` | score 最高 10% | `1 / selected_n` |
| `C3_RESMOM_R3_BOARD_ADAPTATION` | score 最高 10% | `1 / selected_n` |
| `C3A_RESMOM_R2_MARKET_ONLY` | score 最高 10% | `1 / selected_n` |
| `C4_LOWVOL` | `LOWVOL_36M` 最低 10% | `1 / selected_n` |
| `C5_EP19_B2_MONTH_END_ADAPTATION` | 在同一 month-end 对 U_project 应用冻结 B2 feature rule | `1 / month_end_B2_selected_n` |
| `C5R2_EP19_B2_MONTH_END_VOL60_TRIM` | 同日 B2 candidates 中保留低于 causal q_vol60 p70 的名称 | 保留未 trim arm 的原 target weight；被 trim 权重留 cash |

共同规则：

```text
project_signal_breakpoint_scope = same-decision-month U_project signal-eligible rows
top_bucket_fraction = 0.10
selected_n = ceil(signal_eligible_n * 0.10)
rank_tie_break = (score direction, instrument ascending); exactly selected_n rows
minimum_signal_eligible_n = 300
below_minimum_signal_eligible_action = contract violation for that arm-month; stop the ledger from that decision onward,
                                      no return row and never silently substitute an all-cash target
no_selected_B2_action = valid target portfolio is 100% cash after confirming full rule coverage;
                        attempt to sell existing holdings, but blocked legacy positions remain and NAV return need not be 0
signal_missing_row = not rank eligible
blocked_fill_weight_redistribution_to_other_names = false
unfilled_target_weight = cash
leverage_allowed = false
short_allowed = false
```

`C5R2` 的 `q_vol60` 必须先在同一 decision date 的完整 executable universe 内用 average-rank percentile 计算，再只用
当日 month-end B2 candidates 计算 causal linear p70。阈值相等全部 remove。不得跨日期或在整个 forward batch 上估计
threshold，也不得用 outcome 处理 ties。报告必须并列展示原 EP19 daily reference 与 EP20 month-end adaptation 的频率、
cooldown、entry、denominator 差异，不得把 EP19 的约 +33% exposure 复制到该 arm 描述中。

Reference capital 与 order-cost contract：

```text
primary_reference_portfolio_notional_cny = 10000000
diagnostic_notional_grid_cny = {1000000, 10000000, 100000000}
primary_claim_notional = primary_reference_portfolio_notional_cny only
portfolio_accounting_mode = one_independent_stateful_NAV_ledger_per_arm
external_capital_injection_after_initialization = false
historical_ledger_start = first common signal-eligible decision month across all registered executable project arms in the readout
forward_ledger_start = first sealed forward decision month; all frozen arms initialize as cash on the same timestamp
target_order_notional = pretrade_target_weight * current_pretrade_NAV - current_position_market_value
buy_share_rounding = verified market-rule lot contract, round down
rounding_residual = cash
commission_per_order_cny = max(order_notional * commission_bps / 10000, minimum_commission_cny)
notional_grid_role = cost_and_capacity_sensitivity_only; no arm selection
```

Stateful ledger 必须按每个 arm 独立维护：

```text
1. decision month-end close:
       compute next target weights; do not trade at the close
2. next exchange-open rebalance:
       mark existing positions at the executable qfq/raw-linked open
       process executable sells/reductions; blocked sells remain as locked positions and consume NAV
       compute positive target gaps from the same current NAV
       remove blocked buy orders without reallocating their target weight
       if executable positive gaps plus costs exceed available cash, scale all executable positive gaps
       by one common cash_constraint_factor in [0,1]; choose the largest factor whose lot-rounded orders plus
       all costs fit available cash, using deterministic bisection tolerance 1e-12; no borrowing and no instrument-order priority
3. between rebalances:
       mark every position through qfq return relatives; suspension carries the last valid marked value
       maintain cash, position value, accrued costs and total NAV daily
4. later executable exit:
       sell the carried position, charge costs at actual execution, and release only actual proceeds
5. corporate-action bridge:
       raw open determines executable notional/lot rounding; qfq open/close relatives determine economic PnL
       every raw/qfq file hash and implied adjustment-factor continuity is audited; hash an explicit adjustment file when available
       unknown or discontinuous raw-to-qfq mapping makes the affected arm-month not evaluable
```

`cash_constraint_factor` 是真实资本约束，不是事后优化；必须单列 `locked_capital_weight`、`blocked_buy_cash_weight` 和
`cash_constraint_unfilled_weight`。不得为保持 target exposure 再注资或在下一 decision month 重置为 1000 万。

必须将上述值写入 `freeze/arm_role_registry.csv`、`freeze/return_and_cash_semantics_freeze.csv` 和
`freeze/stateful_portfolio_accounting_and_nav_freeze.csv`。任何 AUM、bucket、weight、tie、ledger 或 lot-size 变化都需要
新 contract version。

```text
stateful_portfolio_accounting_gate = pass iff every ledger/valuation/cash-constraint/corporate-action field above is nonmissing,
                                    no monthly capital reset is allowed, and locked positions remain in NAV
```

## 8. 本地数据合同

### 8.1 U_project

Primary project universe：

```text
PROJECT_UNIVERSE_FILE
primary_key = (usable_trade_date, instrument)
instrument_format = SH600000 / SZ000001 / BJxxxxxx when applicable
decision_eligibility_time = membership_available_time / available_time
```

必需字段：

```text
usable_trade_date
instrument
membership_date
membership_available_time
available_time
board_bucket
is_listed
is_st
is_suspended
raw_unadjusted_close
total_share_asof
total_market_cap_cny
source_trade_date
source_asof_date
candidate_universe_source
membership_rule_version
board_rank_by_market_cap
board_quota
minimum_history_sessions
history_observed_sessions_before_usable_date
```

Project contract minimums：

```text
duplicate_primary_key_count = 0
unique_instrument_count >= 1700
date_min <= 2017-01-31
median_month_end_eligible_instrument_n >= 350
total_market_cap_cny_nonmissing_rate >= 0.95
membership_available_time_nonmissing_rate = 1.00
```

实际值必须计算后写入 audit；以上门不得因为当前 observation 轻微不符而静默降低。

### 8.2 qfq OHLCV

每个 `QFQ_ROOT/*.csv` 必需：

```text
date, open, high, low, close, volume, instrument
```

可选：

```text
money, turnover_rate, source_function, source_volume_unit, source_turnover_unit
```

Primary key `(instrument,date)` 必须唯一。20A 只审计覆盖，不计算 forward return。

最低 project coverage：

```text
qfq_file_n >= 4500
qfq_unique_instrument_n >= 4500
qfq_instrument_overlap_with_U_project >= 0.98
qfq_max_date >= PROJECT_UNIVERSE_FILE.max(usable_trade_date)
OHLC_nonmissing_rate_on_U_project_dates >= 0.99
```

`source_volume_unit` 可能为 shares/hands 且 `turnover_rate` 可能为 ratio/percent。20A 必须输出 unit inventory；后续
TrendPV volume signal 在 unit normalization 未冻结前不得标 `implementation_ready`。Normalization 固定为：

```text
source_volume_unit = shares  -> normalized_volume_shares = volume
source_volume_unit = hands   -> normalized_volume_shares = 100 * volume
source_turnover_unit = ratio -> normalized_turnover_rate = turnover_rate
source_turnover_unit = percent -> normalized_turnover_rate = turnover_rate / 100
unknown unit -> row not signal-eligible and qfq_unit_semantics_gate fail if U_project coverage falls below floor
```

同一 instrument 的 `source_function` 或 unit 在历史中切换时必须输出 continuity row；不得把切换点当真实 volume jump。

qfq 是当前下载时点的复权序列，不自动证明 historical adjustment-factor vintage。20A 必须将其 exact role 记录为：

```text
project_price_history = allowed_with_adjustment_semantics_audit
paper_exact_corporate_action_vintage = not_proven_without_optional vintage source
```

### 8.3 Benchmark

`BENCHMARK_FILE` 至少包含：

```text
date / trade_date
open, high, low, close
index_alias
instrument
source_trade_date
```

Primary project market comparator 固定 `index_alias=csi300`；若缺失则使用 config 明确列出的唯一 fallback，不能 outcome 后
选择 benchmark。Benchmark calendar 用于 date/warm-up/forward boundary，不生成未来标签。

### 8.4 Cost 与 execution inheritance

20A 必须逐字段继承并 hash EP19 19A 已冻结合同：

```text
commission_buy_bps = 2.5
commission_sell_bps = 2.5
minimum_commission_cny = 5.0
stamp_tax_sell_bps_by_effective_date = 2023-08-28:5.0
slippage_bps = 5.0
transfer_fee_schedule = MARKET_RULE_REGISTRY_FILE verified effective-date rows
next_open_execution_delay_sessions = 1
limit_up_buy_handling = blocked_unfilled
limit_down_exit_failure_handling = delayed_to_next_executable_open
blocked_fill_opportunity_loss_policy = count_as_unfilled_opportunity_loss
```

除 transfer fee 外，若 EP19 源文件值与以上不一致，不得静默覆盖；`execution_contract_gate=fail`，回 requirement 层决定
版本升级。Transfer fee 是 EP20 为完整净成本新增的 verified schedule，不声称来自 EP19 19A；缺失或 effective-date coverage
不完整同样使 `execution_contract_gate=fail`。

### 8.5 Tradability、price-limit 与 security-master lineage

20A 必须审计并 hash：

```text
RAW_OHLCV_ROOT/*.csv
TRADING_CALENDAR_FILE
SECURITY_MASTER_FILE
SH_NAME_HISTORY_ROOT/*.csv
PROJECT_UNIVERSE_FILE daily is_st/is_suspended/board_bucket fields
```

Raw OHLCV primary key `(instrument,date)` 必须唯一，至少包含：

```text
date, open, high, low, close, volume, money, instrument
```

未来 execution contract 冻结为：

```text
suspension:
    exchange calendar open and no valid raw bar -> suspended_or_no_trade

entry:
    each positive target-gap order is attempted once at the scheduled next exchange open
    fill only when status is known, raw open > 0, money > 0,
    not suspended and not conservatively limit-up blocked
    missing bar, unknown ST/board/limit rule or blocked entry -> no buy;
    the corresponding unfilled amount remains cash and is not reallocated

exit:
    sell/reduction target is attempted at each scheduled rebalance exchange open
    if suspended or conservatively limit-down blocked, carry the actual position and locked capital
    exit at first later raw open with known executable status
    charge all frozen costs at actual exit
```

Price-limit registry 必须按 `exchange × board_bucket × ST status × effective-date range × listing-session bucket` 输出：

```text
freeze/price_limit_rule_registry.csv
```

其唯一权威输入是 `MARKET_RULE_REGISTRY_FILE`，至少包含：

```text
rule_id
exchange
board_bucket
is_st
effective_start_date
effective_end_date
listing_session_min
listing_session_max
daily_limit_up_rate
daily_limit_down_rate
no_limit_flag
tick_size
rounding_rule
minimum_buy_order_shares
buy_order_increment_shares
sell_remainder_rule
transfer_fee_buy_bps
transfer_fee_sell_bps
official_source_url
official_source_title
source_checked_date
human_verified
```

至少覆盖 main-board 10%、ST 5%、STAR/ChiNext 20%、Beijing 30% 以及各板块 IPO/no-limit effective periods。
每行必须有 rule source、effective dates、tick rounding、upper/lower rate 和 verified status。20A 不允许凭股票代码硬猜；
任一 active U_project row 无法映射到 verified rule 时，`tradability_source_gate=fail`。

保守 fill 判定：

```text
entry_limit_up_blocked = raw_open >= theoretical_limit_up_price - 0.005
exit_limit_down_blocked = raw_open <= theoretical_limit_down_price + 0.005
```

若某日属于 verified no-limit listing window，则两个 blocked flags 均为 false，但仍要求 raw bar 和 money > 0。

Required outputs：

```text
freeze/tradability_source_and_schema_audit.csv
freeze/price_limit_rule_registry.csv
freeze/execution_fill_and_exit_rule_freeze.csv
```

## 9. EP19 2025 static board proxy 合同

### 9.1 Source identity

固定 source：

```text
snapshot_trade_date = 20250102
classification_year = 2025
snapshot_policy = exact_year_first_open_snapshot
source_api = dc_index / dc_member
idx_type = 概念板块
index_row_n = 458
member_row_n = 43468
listed_board_n = 458
boards_with_member_rows = 314
```

上述行数不含 header。任一 source identity 漂移必须 fail closed，不得自动换成 2026 snapshot。

### 9.2 Instrument normalization

```text
600000.SH -> SH600000
000001.SZ -> SZ000001
*.BJ      -> BJ + six_digit_code
```

无法解析的 `con_code` 写入 invalid row audit，不得猜测 exchange。

### 9.3 Semantics

```text
proxy_id = ep19_dc_2025_static_board_proxy
industry_semantics = ep19_2025_static_concept_board_proxy
membership_shape = multi_label
historical_pit_industry_claim = false
alpha_claim = false
```

时间角色：

```text
decision_date < 2025-01-02:
    design_only_non_pit_proxy

2025-01-02 <= decision_date <= contract_freeze_date:
    design_contaminated_historical_proxy

decision_date > contract_freeze_date:
    frozen_preknown_forward_board_proxy
```

所有 freeze 前历史都不能形成 support；上面的区分只说明 snapshot timing，不恢复 OOS。

Forward 中还必须冻结：

```text
snapshot_refresh_within_contract_version_allowed = false
board_membership_currentness_claim = false
board_snapshot_age_months = decision_month - 2025-01
R2_market_only_comparator_required = true
cohort_pooling_across_board_snapshot_versions_allowed = false
```

若未来更新 board snapshot，必须升级 contract version 并重新开始新 cohort；旧/新 snapshot cohorts 不得合并为同一个
confirmatory sample。报告必须逐月披露 snapshot age，尤其在约 2037 年的 confirmatory horizon 下不得把 2025 membership
描述为“当前行业”。

### 9.4 Multi-label transform freeze

R3 的 board exposure matrix 固定为：

```text
one column per board_ts_code with at least 10 U_project-overlap instruments
binary membership in {0,1}
all-zero vector for valid instruments absent from snapshot
drop exact duplicate board columns by lexicographically smallest board_ts_code retention
standardize non-constant columns within each formation month
no outcome-based board selection
no single primary-industry assignment
ridge alpha = 1.0
```

20A 只物化 schema/coverage audit，不物化 monthly regression residual。

Required output `freeze/ep19_2025_static_board_proxy_audit.csv` 至少包含：

```text
proxy_id
source_path
source_sha256
snapshot_trade_date
snapshot_policy
raw_member_row_n
raw_board_n
valid_member_row_n
valid_board_n
unique_instrument_n
U_project_overlap_instrument_n
U_project_overlap_rate
multi_membership_mean
multi_membership_p50
multi_membership_p90
all_zero_project_instrument_n
eligible_board_column_n
duplicate_board_column_n
invalid_instrument_row_n
historical_pit_claim_allowed
forward_control_allowed
board_proxy_gate
blocking_reason
```

Board proxy gate 最低要求：

```text
source identity exact
invalid_instrument_row_n = 0
U_project_overlap_rate >= 0.80
eligible_board_column_n >= 50
historical_pit_claim_allowed = false
forward_control_allowed = true
```

若 gate 失败，R3 不可用，R2 market-only 按 Section 14 的 pre-outcome branch 自动成为 residual primary。Board gate
不是整个 20A 的 critical gate；只有 R2 本身也不可实现、因而无法选出 residual primary 时，才进入
`20A_residual_primary_contract_blocked`。

## 10. U_paper、U_project 与 replication ceiling

### 10.1 Universe roles

```text
U_project:
    PIT top-N 400/100 executable universe
    primary role = positive-beta deployment research

U_paper:
    broad A-share cross-section after paper-specific exclusions
    primary role = exact replication diagnostic
```

二者必须用不同 `universe_id`、denominator、breakpoints、weights 和 claims。不得用 U_project 的 top-N 结果称 full paper
replication；不得用 U_paper 中不可执行股票支撑 project sleeve。

### 10.2 Exact data requirements

Trend full factor exact 至少要求：

```text
broad PIT A-share membership/status
broad PIT total shares and market cap
PIT E/P with publication/availability timestamp
paper-specific smallest-30% exclusion
value-weighted return construction
post-warmup_month_n >= 120
median eligible instrument n >= 1000
```

CH-3 residual exact 至少要求：

```text
China market/size/E-P value factor with explicit vintage
or locally reconstructed broad PIT factor inputs
risk-free return with date/vintage
36 complete monthly observations
12-1 residual score
post-warmup_month_n >= 120
```

Low Vol paper diagnostic exact 至少要求：

```text
broad paper-like investable universe
36 complete monthly returns
paper weighting/breakpoints
post-warmup_month_n >= 120
```

当前 qfq 接近全市场只满足 price-side coverage，不能替代上述 PIT market-cap/E/P/universe fields。

## 11. Return、execution 与 claim semantics freeze

20A 不计算 return，但必须冻结两套未来口径：

```text
paper_return_semantics:
    paper-defined month-end close-to-close total return
    role = replication diagnostic only

project_return_semantics:
    decision = after close on the last SSE open session of each calendar month
    portfolio = one continuous no-injection stateful NAV ledger per arm
    rebalance = first exchange-open session after each decision
    blocked buy = unfilled amount remains cash, no later retry and no redistribution
    blocked sell = actual position remains marked-to-market and consumes capital until executable
    primary monthly return = calendar month-end close NAV / previous calendar month-end close NAV - 1
    trade costs = charged to NAV at the actual transaction timestamp
    role = primary positive-beta economic estimand
```

Cash treatment：

```text
cash_hurdle_primary_monthly = 0.0
risk_free_cash_return = diagnostic when valid source exists
uninvested_or_unfilled_weight_return = cash_hurdle
no rescaling of invested names to hide cash
no monthly reset of reference capital
locked positions remain in full-capital denominator
```

Primary claim：

```text
positive_beta_support does not require matched alpha
matched/regression residual = attribution only
gross-only result cannot support
active-position-only result cannot support
long-short-only result cannot support project sleeve
```

## 12. Warm-up 与历史样本角色

`freeze/warmup_and_monthly_support_audit.csv` 必须对每个 formula × universe 输出：

```text
formula_id
universe_id
source_date_min
source_date_max
raw_month_n
price_warmup_sessions
regression_warmup_months
score_warmup_months
first_feature_eligible_date
last_feature_eligible_date
post_warmup_month_n
monthly_eligible_n_p10
monthly_eligible_n_p50
monthly_eligible_n_p90
history_support_floor
history_support_gate
historical_design_common_month_n
historical_design_early_start / historical_design_early_end
historical_design_late_start / historical_design_late_end
sample_role
claim_allowed
```

固定 warm-up：

```text
TMOM_12_1 = 12 complete months, latest month excluded
TrendPV raw = 400 sessions plus coefficient-initialization rule from paper registry
Residual exact = paper-defined 36-month regression plus 12-1 score
Residual R2/R3 adaptation = 36 prior months for the first one-step market residual plus 11 residual-score months and one skipped month;
                            first eligible formation requires 47 complete prior months
Low Vol = 36 complete monthly returns
FIP = 12 months excluding latest month plus daily sign coverage
CNN = image lookback plus Section 16 calendar-support gate
```

历史设计最低支持：

```text
project_adaptation_post_warmup_month_n >= 60
paper_exact_post_warmup_month_n >= 120
monthly_project_eligible_n_p10 >= 300
```

无论是否达到：

```text
all decision_date <= contract_freeze_date
sample_role = design_contaminated_historical
support_claim_allowed = false
```

Historical design fold 只按 pre-outcome calendar 冻结：取两个 project primary arms 都 signal-eligible 的共同月份，按日期排序；
前 `floor(N/2)` 个为 early，剩余为 late。未来 20B/20C 的 historical beta-design direction gate 要求两个 block 的
stateful net mean 都高于 cash hurdle，但永远只产生 design authorization，不能产生 support。不得按收益移动边界、删除月份
或改成表现更好的 regime folds。

## 13. 数据可得性 go/no-go

`freeze/ep20a_data_replication_go_no_go.csv` 一行一个 gate：

```text
gate_id
route_id
data_requirement
required_paths
required_fields
minimum_coverage
observed_paths
observed_fields
observed_coverage
status
blocking_scope
highest_allowed_role
blocked_arms
fallback_arm
evidence_paths
evidence_hashes
reason
```

必须包含：

| gate_id | pass 后最高角色 | fail 后行为 |
|---|---|---|
| `wide_qfq_status_gate` | U_paper price-side candidate | 只用 U_project |
| `wide_pit_market_cap_gate` | size exclusion/weights exact-capable | full Trend/CH-3 exact blocked |
| `pit_ep_timing_gate` | full Trend/China value exact-capable | T2/R1 exact blocked |
| `historical_pit_industry_gate` | exact industry analysis | 使用 2025 static proxy，不升级 exact |
| `board_proxy_gate` | R3 forward control | deterministic fallback R2，20A 可继续 |
| `risk_free_vintage_gate` | excess/factor exact-capable | raw-return beta remains evaluable |
| `ch3_factor_vintage_gate` | residual exact-capable | R1 blocked, R2/R3 remain |
| `paper_exact_history_support_gate` | paper diagnostic has minimum calendar | historical pipeline QA only |
| `project_adaptation_gate` | 20B/20C design work can be specified | 20A blocked |
| `forward_contract_gate` | future post-freeze test reachable | 20A blocked |
| `cnn_training_support_gate` | 20F evaluable | CNN not evaluable, nonblocking |

Root-level capability columns：

```text
exact_replication_reachable
trend_full_exact_reachable
resmom_ch3_exact_reachable
lowvol_paper_exact_reachable
C2_trendpv_adaptation_reachable
R2_market_adaptation_reachable
project_adaptation_reachable
R3_board_adaptation_reachable
forward_beta_test_reachable
cnn_oracle_reachable
```

当前可选 exact source lists 若为空，exact flags 应机械为 false；这不是 implementation error。

## 14. Primary family 与 multiplicity freeze

Project primary family 始终为 2 个 family；residual arm 由 pre-outcome data gate 确定：

```text
if board_proxy_gate == pass:
    residual_primary_arm = C3_RESMOM_R3_BOARD_ADAPTATION
else:
    residual_primary_arm = C3A_RESMOM_R2_MARKET_ONLY

F_primary = {C2_TRENDPV_RAW_ADAPTATION, residual_primary_arm}
family_size = 2
correction = Holm step-down
alpha_familywise = 0.05
selection_basis = preoutcome_data_availability_only
```

Comparators：

```text
C0_ALL_ELIGIBLE
C1_TMOM_12_1
C3A_RESMOM_R2_MARKET_ONLY when not selected as residual primary
C4_LOWVOL
C5_EP19_B2_MONTH_END_ADAPTATION
C5R2_EP19_B2_MONTH_END_VOL60_TRIM
```

Paper-exact arms 只回答 replication，不得替 project primary pass/fail；project adaptation 也不得升级 exact claim。FIP 是
ordered deferred test；CNN 是 separate oracle family。任何未来新增 primary arm 必须升级 requirement/contract version，
不能只改 config。

Required output：

```text
freeze/multiple_testing_and_search_accounting_freeze.csv
```

至少包含所有 registered arms、family、role、hypothesis count、correction、promotion eligibility 和 deferred gate。
必须输出 `residual_primary_arm`、board gate status 和 selection basis；不得根据任何 return/outcome 改分支。

## 15. 正 beta economic / risk gate freeze

20A 只冻结，不评价以下 gates。所有数值必须写入 `freeze/positive_beta_economic_and_risk_gate_freeze.csv`：

### 15.1 Primary positive-beta gates

```text
primary_horizon = one_month
primary_return = project cash-inclusive full-capital net return
cash_hurdle_monthly = 0.0
minimum_directional_evidence_mean_floor = 0.0
confirmatory_mean_net_return_CI_lower_floor = 0.0
confirmatory_hypothesis_rule = Holm step-down on one-sided Newey-West HAC p-values
confirmatory_ci_rule = per-arm one-sided 97.5% Bonferroni simultaneous lower confidence bound
confirmatory_per_arm_alpha_worst_case = 0.025
nominal_95pct_two_sided_CI_role = diagnostic_only
positive_month_rate_role = diagnostic_only
positive_month_rate_reference = 0.50
```

12-month minimum directional evidence 只要求 point estimate 高于 0；它不能被称为 confirmatory support。Positive-month rate
不进入 pass/fail，避免误杀依赖少数厚右尾盈利的正 beta sleeve。

Right-tail 分成两个明确 diagnostics：

```text
one_month_upper_tail_contribution_10 =
    for each complete decision month:
        rank entered positions by net position return within month;
        numerator = sum(max(capital_weight * net_position_return, 0)) in the top return decile;
        denominator = sum(max(capital_weight * net_position_return, 0)) across all entered positions;
        month statistic is undefined when denominator = 0;
    report the equal-weight mean across defined complete months and the defined-month count

big_winner_exposure_ratio_50_120 =
    for each decision month with complete 120-session paths:
        sleeve_rate = capital-weighted P(MFE_120 >= 0.50 | sleeve entered positions)
        baseline_rate = equal-weight P(MFE_120 >= 0.50 | same-date U_project executable eligible rows)
        month_ratio = sleeve_rate / baseline_rate when baseline_rate > 0;
    report the equal-weight mean of month_ratio across defined months and the defined-month count
```

两个 right-tail diagnostics 都必须同时报告 undefined-month count，不得以 0 填充 undefined。它们是 secondary Big Winner
bridge，不阻断 1-month positive-beta evidence，也不得把 1-month forward 等待期重新拉长为 120 sessions。

### 15.2 Risk budget

```text
monthly_ES10_loss_cap = 0.15
monthly_p10_return_floor = -0.12
max_drawdown_cap = 0.35
single_instrument_weight_cap = 0.10
top10_instrument_weight_cap = 0.50
minimum_effective_holdings = 20
maximum_ADV_participation_rate = 0.01
parameter_source = human_positive_beta_risk_budget_20A_v1
parameter_role = ex_ante_absolute_cap_not_historical_fit
```

Loss cap 使用正数损失幅度；即 `ES10_loss <= 0.15`。

Risk metrics 必须全部来自同一 stateful ledger：

```text
monthly_return_series = fixed calendar-month continuous NAV returns
monthly_ES10_loss = mean(-return | return at or below empirical p10), reported only when month_n >= 20
monthly_p10_return = empirical linear p10 of monthly_return_series
max_drawdown = max_t(1 - daily_NAV_t / running_max(daily_NAV through t))
target_single_instrument_weight = max intended pre-execution target weight at each rebalance
target_top10_instrument_weight = sum of largest 10 intended target weights
realized_effective_holdings = (sum(actual_posttrade_position_weight))^2
                              / sum(actual_posttrade_position_weight^2), or 0 when invested weight = 0
minimum_effective_holdings_gate = p10(realized_effective_holdings across evaluable rebalances) >= 20
locked_capital_weight = blocked-exit position market value / pretrade NAV
```

Target concentration caps 约束 signal construction；realized/locked concentration 必须另外逐月报告，不能用目标权重掩盖。
当 `month_n < 20` 时 ES10/p10 只作 provisional descriptive statistics，不得通过 confirmatory risk gate。

Capacity contract：

```text
ADV_window_sessions = 20
ADV20_cny_asof_order = mean(raw money over the 20 exchange-open sessions ending before the order session)
listed_but_missing_raw_bar_in_ADV_window = raw money 0 for that exchange session
prelisting_session_in_ADV_window = unavailable; fewer than 20 post-listing exchange sessions -> missing ADV20
entry_participation = intended executable buy notional / ADV20_cny_asof_order
exit_participation = intended sell notional / ADV20_cny_asof_order
capacity_scope = every intended order, including an order later blocked by price limit/suspension
missing_or_nonpositive_ADV20 = capacity_fail_for_that_order
capacity_gate = max(entry_participation, exit_participation) <= 0.01 over all evaluable orders
capacity_based_order_scaling_allowed = false
```

容量门评价“策略在 reference AUM 下是否可部署”，不改变回测成交量；不得只看实际成交单而删除被阻塞的大单。

### 15.3 Cost gate

```text
gross_and_net_both_required = true
gross_shadow_ledger = identical decisions/fills/share quantities as net ledger, with transaction costs added back;
                      saved costs are not reinvested and cannot change later orders
break_even_one_way_cost_multiple_vs_frozen_cost = 1.25
unfilled_weight_remains_cash = true
active_position_rescaling_allowed = false
cash_constraint_common_factor_scaling_allowed = true only as specified in Section 7.5

realized_one_way_turnover_t = (executed_buy_notional_t + executed_sell_notional_t)
                               / (2 * pretrade_NAV_t)
attempted_one_way_turnover_t = (intended_buy_notional_t + intended_sell_notional_t)
                                / (2 * pretrade_NAV_t)
transaction_cost_return_t = all actual commission + stamp + transfer fee + slippage costs / pretrade_NAV_t
break_even_cost_multiple = mean(gross_monthly_return - cash_hurdle_monthly)
                           / mean(transaction_cost_return)
break_even_gate = finite break_even_cost_multiple >= 1.25
```

若 mean transaction cost 为 0，break-even multiple 为 undefined 而不是 infinity；若 gross mean 不高于 cash hurdle，
`break_even_gate=fail`。Blocked orders 进入 attempted turnover/容量，但只在实际成交时进入 realized turnover 与成本。

```text
cost_capacity_formula_gate = pass iff ADV, attempted/realized turnover, every cost component,
                             break-even and missing-value behavior above are fully frozen
```

### 15.4 Attribution status

```text
matched_alpha_required = false
scale_independence_required = false
risk_source_attribution_required = true
```

未来 decision labels：

```text
positive_beta_supported_scale_explained
positive_beta_supported_with_incremental_alpha
scale_exposure_unholdable_risk_budget
```

20A 不产生其中任何一个 label，只冻结定义。

### 15.5 Ex-ante MDE / power freeze

Confirmatory support 的时间序列证据数不能固定为 12。20A 冻结：

```text
evidence_unit = distinct scheduled decision month with complete labels
cross_sectional_row_independence_claim = false
serial_independence_claim = false
test_direction = one_sided_positive
familywise_alpha = 0.05
Holm_worst_case_per_arm_alpha = 0.025
target_power = 0.80
primary_economic_effect_monthly = 0.02
primary_design_long_run_monthly_volatility = 0.08
confirmatory_mean_se = Newey-West HAC on the decision-month return series
newey_west_lag_rule = max(1, floor(4 * (complete_forward_month_n / 100)^(2/9)))
newey_west_prewhitening = false
z_1_minus_alpha = 1.9599639845
z_power = 0.8416212336
n_required_primary = ceil(((z_1_minus_alpha + z_power)
                           * primary_design_long_run_monthly_volatility
                           / primary_economic_effect_monthly)^2)
                   = 126 complete decision-month evidence units
```

同时输出 sensitivity grid：

```text
effect_monthly in {0.01, 0.02, 0.03}
monthly_volatility in {0.05, 0.08, 0.12}
alpha in {0.025}
power in {0.80}
```

Required output：

```text
freeze/forward_mde_and_power_freeze.csv
```

8% 是包含 serial dependence 的 ex-ante long-run monthly volatility 假设，不是把 decision months 或股票行声明为 iid。
这些参数不使用历史或 forward outcome。任何缩短 `n_required_primary`、改 HAC lag 或用观察波动率重算 sample floor 的
行为必须升级 contract version；不得根据已观察结果选择更有利的推断口径。

## 16. CNN training-support gate

CNN 只有以下全部达到才可在未来 20F 标 `evaluable`：

```text
train_calendar_month_n >= 72
validation_calendar_month_n >= 18
frozen_test_calendar_month_n >= 24
train_unique_instrument_n >= 1500
train_image_n >= 300000
validation_image_n >= 60000
frozen_test_image_n >= 80000
distinct_market_regime_n >= 3
strict_time_order = train < validation < frozen_test
random_cross_time_split_allowed = false
```

Market regimes 只按 pre-outcome benchmark calendar/volatility rule 冻结，20A 不根据未来模型表现选择 regime。若支持不足：

```text
cnn_oracle_reachable = false
cnn_status = cnn_underpowered_not_evaluable
daily_ohlcv_closure_claim_allowed_from_cnn = false
```

Required output：

```text
freeze/cnn_training_support_preflight.csv
```

20A 不生成图片，不训练 CNN。

## 17. Forward boundary 与 evaluability freeze

### 17.1 Forward 起点

```text
contract_freeze_timestamp_source = freeze_manifest_20a.json.sealed_at_utc
first_forward_decision_date = first scheduled project month-end decision timestamp
                              strictly after contract_freeze_timestamp
confirmatory_calendar_earliest_rule = month containing the 126th complete decision-month label
```

`freeze/forward_boundary_and_support_freeze.csv` 只冻结上述 rule 和 timestamp source，不预写 seal 尚未发生时的实际
`contract_freeze_timestamp`。`freeze_manifest_20a.json` 写入最终 `sealed_at_utc` 后，`finalize` 才可将该时间复制到
root-level decision。不得为了预先填日期而修改已密封 artifact。

规则：

- 本地数据是否在 freeze 前被程序读取不决定 OOS；只看 exchange decision timestamp；
- freeze 前已经发生但以后才 backfill 的数据仍是 historical；
- forward decision 必须使用 20A seal 时已冻结的 formula、universe、cost、board snapshot 和 gates；
- 任何修订 primary formula/gate 后，旧 forward cohort 不得继续用于新 version support。

### 17.2 Fixed-month NAV label 与 unresolved-state handling

```text
primary_label = next calendar-month continuous stateful NAV return
primary_label_formula = month_end_close_NAV_t / month_end_close_NAV_(t-1) - 1
label_complete = next month-end NAV is mechanically valuatable under the rule below
decision_month_count_unit = distinct scheduled decision month
```

Primary valuation/blocked-exit rule：

```text
entry blocked:
    no position is opened; allocated amount remains cash and stays in NAV

exit blocked:
    position remains invested, marked with the last valid qfq-linked value and consumes capital
    the fixed calendar-month NAV label remains complete; position-resolution delay is audited separately
    no maximum-delay censoring, no deletion and no external replacement capital

delisted / corporate action before executable exit:
    use verified delisting cash recovery when available
    if recovery is unavailable, assign -100% terminal return and mark conservative_resolution

decision month complete:
    every cash/position component has a valid month-end marked value or conservative terminal resolution

unknown valuation bridge / unresolved delisting proceeds:
    complete_forward_month_n does not advance
```

这既避免删除长期停牌股票造成 survivorship bias，也避免把 variable-horizon delayed-exit return 冒充 one-month return。
Position 可以未退出但月度 NAV label 已完成；`exit_delay_sessions` 与 locked-capital path 另作 execution burden。20A 必须输出：

```text
freeze/label_completion_and_censoring_rule_freeze.csv
freeze/stateful_portfolio_accounting_and_nav_freeze.csv
```

### 17.3 Support floors

```text
complete_forward_month_n < 6:
    forward_not_evaluable

6 <= complete_forward_month_n < 12:
    forward_interim_not_support

12 <= complete_forward_month_n < n_required_primary:
    forward_minimum_directional_evidence_not_confirmatory

complete_forward_month_n >= n_required_primary:
    forward_confirmatory_support_evaluable
```

Confirmatory early/late stability 固定为：

```text
ordered_months = all complete forward decision months sorted ascending
early_block = first floor(complete_forward_month_n / 2) months
late_block = remaining months
early_late_gate_evaluable = complete_forward_month_n >= 126 and each block month_n >= 60
early_late_direction_gate = mean_net_return_early > 0 and mean_net_return_late > 0
block_CI_support_claim_allowed = false
```

最终 support 还必须满足 20G 的 row/instrument/effective-n、Holm/HAC、Bonferroni lower-bound、economic/risk/capacity 与
early/late direction gates。`n_required_primary=126` 来自 Section 15.5 的 ex-ante power design，不使用未来 outcome。

若 freeze 约在 2026-08，预期 6-month interim 最早约 2027 年初，12-month minimum directional evidence 最快约
2027 年中至第三季度；它不是 confirmatory support。126 个完整 decision months 的确认性日历下限约为 **2037 Q1**。
报告必须同时写出 2027 minimum-evidence 与 2037 confirmatory 两个时间点，并标“预计”；实际日期由
calendar/label-complete audit 决定。

Required outputs：

```text
freeze/forward_boundary_and_support_freeze.csv
freeze/forward_evaluability_preflight.csv
```

`forward_evaluability_preflight.csv` 只允许日期/支持计数，禁止 outcome 值。在 seal 前它只能输出
`local_data_max_date`、`boundary_rule`、`complete_forward_month_n=0` 和
`preflight_state=forward_not_yet_observed_at_freeze`；实际 first forward decision 和 label-complete month count 由未来
20G 使用 sealed timestamp 计算。

## 18. Stage、manifest、hash 与 outcome-access 审计

### 18.0 Acquire-sources isolation

`acquire-sources` 只能读取 requirement/config 和 Section 6 URL allowlist，只能写 `PAPER_CACHE_ROOT`。硬约束：

```text
market_data_read_count = 0
EP19_artifact_read_count = 0
outcome_read_count = 0
resolved_domain_outside_allowlist_count = 0
source_acquisition_manifest_complete = true
```

该 stage 不产生研究 decision；只有完整 source cache 和 manifest，或 Section 6 明列且三方一致的 v2 material waiver，
才能成为 `freeze` 输入。

### 18.1 Freeze outputs immutable

Output root：

```text
EXPERIMENT_ROOT/outputs/20A_paper_lineage_data_and_replication_contract
```

`freeze` 只能写 `output_root/freeze/`。Seal 顺序：

```text
1. materialize all required freeze CSV/JSON/MD
2. run schema and no-outcome scans
3. choose sealed_at_utc and write the final freeze_manifest_20a.json;
   manifest.output_hashes covers required freeze artifacts but excludes
   freeze_manifest_20a.json and freeze_output_hashes_20a.json
4. write freeze_output_hashes_20a.json covering all required freeze artifacts
   including the final freeze_manifest_20a.json, excluding itself
5. define freeze_bundle_hash = SHA256(bytes of freeze_output_hashes_20a.json);
   do not write this value back into any freeze artifact
6. prohibit overwrite
```

### 18.2 Outcome access audit

`freeze/outcome_access_audit.csv` 每次数据读取一行：

```text
run_id
stage
accessed_at
artifact_path
artifact_sha256_or_root_hash
dataset_role
columns_read
derived_fields
outcome_columns_detected
outcome_access_authorized
selection_or_tuning_allowed
purpose
access_gate
```

20A 硬约束：

```text
outcome_read_count = 0
outcome_columns_detected_count = 0
selection_or_tuning_allowed_count = 0
EP19_outcome_artifact_read_count = 0
EP19_preoutcome_rule_artifact_read_count = 5
finalize_raw_input_read_count = 0
```

Hash-only read of required planning/lineage files必须记录；不在白名单的文件即使只 hash 也禁止。

### 18.3 Finalize

`finalize` 只读 `freeze_manifest_20a.json`、freeze hashes 和 required freeze artifacts，输出 root-level final artifacts。
Final hash 规则：

```text
final manifest.output_hashes excludes final manifest and final output-hashes file
final output-hashes includes final manifest and all required final artifacts
final output-hashes excludes itself
root-level freeze_bundle_hash = SHA256(bytes of freeze/freeze_output_hashes_20a.json)
```

任一 hash 不匹配：

```text
manifest_hash_gate = fail
decision_state = 20A_manifest_or_hash_blocked
```

## 19. Required outputs 与 schema

### 19.1 Freeze artifacts

```text
freeze/resolved_config.yaml
freeze/human_restart_authorization.json
freeze/upstream_scope_audit.csv
freeze/input_artifact_audit.csv
freeze/source_data_inventory.csv
freeze/paper_source_registry.csv
freeze/paper_formula_registry.csv
freeze/paper_to_local_field_mapping.csv
freeze/arm_role_registry.csv
freeze/ep19_b2_preoutcome_lineage_audit.csv
freeze/project_universe_schema_and_coverage_audit.csv
freeze/qfq_schema_unit_and_coverage_audit.csv
freeze/benchmark_schema_and_calendar_audit.csv
freeze/execution_and_cost_inheritance_audit.csv
freeze/tradability_source_and_schema_audit.csv
freeze/price_limit_rule_registry.csv
freeze/execution_fill_and_exit_rule_freeze.csv
freeze/optional_exact_source_availability_audit.csv
freeze/ep19_2025_static_board_proxy_audit.csv
freeze/universe_role_and_denominator_freeze.csv
freeze/return_and_cash_semantics_freeze.csv
freeze/stateful_portfolio_accounting_and_nav_freeze.csv
freeze/turnover_cost_capacity_formula_freeze.csv
freeze/warmup_and_monthly_support_audit.csv
freeze/ep20a_data_replication_go_no_go.csv
freeze/multiple_testing_and_search_accounting_freeze.csv
freeze/positive_beta_economic_and_risk_gate_freeze.csv
freeze/forward_mde_and_power_freeze.csv
freeze/cnn_training_support_preflight.csv
freeze/forward_boundary_and_support_freeze.csv
freeze/forward_evaluability_preflight.csv
freeze/label_completion_and_censoring_rule_freeze.csv
freeze/outcome_access_audit.csv
freeze/contract_freeze_20a.json
freeze/20A_contract_freeze.md
freeze/freeze_manifest_20a.json
freeze/freeze_output_hashes_20a.json
```

### 19.2 Final artifacts

```text
20A_preoutcome_contract_decision.csv
20A_paper_lineage_data_and_replication_contract_report.md
manifest_20a_paper_lineage_data_and_replication_contract.json
output_hashes_20a_paper_lineage_data_and_replication_contract.json
```

### 19.3 Stable output rules

- 所有 CSV 使用稳定列顺序与明确 sort keys；
- 布尔值只能 `true/false`；status 只能使用 registry 中枚举；
- missing 使用空字段，不得用隐式 0；
- float 至少 10 位有效数字；
- path 使用 repository-relative；
- 每个 artifact 包含 `run_id` 或由 manifest 显式绑定；
- 禁止输出任何 future return/outcome 字段。

### 19.4 Decision schema

`20A_preoutcome_contract_decision.csv` 单行至少包含：

```text
run_id
contract_version
decision_state
primary_objective
incremental_alpha_required
human_restart_lineage_gate
paper_material_gate
paper_contract_gate
project_data_contract_gate
qfq_unit_semantics_gate
benchmark_schema_and_calendar_gate
execution_contract_gate
stateful_portfolio_accounting_gate
cost_capacity_formula_gate
board_proxy_gate
residual_primary_selection_gate
residual_primary_arm
B2_lineage_gate
tradability_source_gate
label_censoring_freeze_gate
project_adaptation_gate
outcome_firewall_gate
economic_gate_freeze_gate
power_gate_freeze
search_accounting_gate
forward_contract_gate
manifest_hash_gate
implementation_readiness_gate
wide_qfq_status_gate
paper_universe_gate
paper_exact_history_support_gate
exact_replication_reachable
trend_full_exact_reachable
resmom_ch3_exact_reachable
lowvol_paper_exact_reachable
C2_trendpv_adaptation_reachable
R2_market_adaptation_reachable
project_adaptation_reachable
R3_board_adaptation_reachable
forward_beta_test_reachable
cnn_oracle_reachable
historical_sample_role
historical_support_claim_allowed
primary_portfolio_accounting_mode
primary_return_semantics
board_snapshot_age_rule
first_forward_decision_rule
forward_interim_month_floor
forward_minimum_evidence_month_floor
forward_confirmatory_support_month_floor
n_required_primary
confirmatory_calendar_earliest_estimate
next_allowed_requirement
next_requirement_generation_authorized
next_requirement_execution_authorized
policy_training_authorized
policy_replay_authorized
portfolio_optimization_authorized
deployment_authorized
freeze_bundle_hash
blocking_reasons
```

## 20. Gate logic 与 final decision

Critical gates：

```text
human_restart_lineage_gate
paper_contract_gate
project_data_contract_gate
qfq_unit_semantics_gate
execution_contract_gate
stateful_portfolio_accounting_gate
cost_capacity_formula_gate
residual_primary_selection_gate
B2_lineage_gate
tradability_source_gate
label_censoring_freeze_gate
project_adaptation_gate
outcome_firewall_gate
economic_gate_freeze_gate
power_gate_freeze
search_accounting_gate
forward_contract_gate
manifest_hash_gate
implementation_readiness_gate
```

Noncritical capability gates：

```text
wide_pit_market_cap_gate
pit_ep_timing_gate
historical_pit_industry_gate
board_proxy_gate
risk_free_vintage_gate
wide_qfq_status_gate
paper_universe_gate
benchmark_schema_and_calendar_gate
ch3_factor_vintage_gate
paper_exact_history_support_gate
cnn_training_support_gate
```

成功逻辑：

```text
20A_preoutcome_contract_ready =
    all(critical_gates == pass)
    and project_adaptation_reachable == true
    and forward_beta_test_reachable == true
    and historical_support_claim_allowed == false
    and outcome_read_count == 0
```

Exact capability 逻辑：

```text
trend_full_exact_reachable =
    wide_qfq_status_gate
    and wide_pit_market_cap_gate
    and pit_ep_timing_gate
    and paper_exact_history_support_gate
    and paper_universe_gate

resmom_ch3_exact_reachable =
    wide_qfq_status_gate
    and wide_pit_market_cap_gate
    and pit_ep_timing_gate
    and risk_free_vintage_gate
    and ch3_factor_vintage_gate
    and paper_exact_history_support_gate
    and paper_universe_gate

lowvol_paper_exact_reachable =
    wide_qfq_status_gate
    and paper_exact_history_support_gate
    and paper_universe_gate

exact_replication_reachable =
    trend_full_exact_reachable
    or resmom_ch3_exact_reachable
    or lowvol_paper_exact_reachable
```

Project adaptation / fallback 逻辑：

```text
C2_trendpv_adaptation_reachable =
    project_data_contract_gate
    and qfq_unit_semantics_gate
    and project_adaptation_post_warmup_month_n >= 60

R2_market_adaptation_reachable =
    project_data_contract_gate
    and qfq_unit_semantics_gate
    and benchmark_schema_and_calendar_gate
    and project_adaptation_post_warmup_month_n >= 60

R3_board_adaptation_reachable =
    project_data_contract_gate
    and qfq_unit_semantics_gate
    and benchmark_schema_and_calendar_gate
    and board_proxy_gate
    and project_adaptation_post_warmup_month_n >= 60

if board_proxy_gate == pass:
    residual_primary_arm = C3_RESMOM_R3_BOARD_ADAPTATION
    residual_primary_selection_gate = R3_board_adaptation_reachable
else:
    residual_primary_arm = C3A_RESMOM_R2_MARKET_ONLY
    residual_primary_selection_gate = R2_market_adaptation_reachable

project_adaptation_reachable =
    C2_trendpv_adaptation_reachable and residual_primary_selection_gate

forward_beta_test_reachable =
    project_adaptation_reachable
    and execution_contract_gate
    and stateful_portfolio_accounting_gate
    and cost_capacity_formula_gate
    and tradability_source_gate
    and label_censoring_freeze_gate
    and forward_contract_gate
```

不得把 `exact_replication_reachable=false` 映射到 20A failure。

多个 critical gate 同时失败时，`blocking_reasons` 必须列全，单一 `decision_state` 按以下固定优先级选择，不得依赖代码
分支遍历顺序：

```text
1  outcome_firewall_gate fail                    -> 20A_outcome_firewall_violated
2  manifest_hash_gate fail                       -> 20A_manifest_or_hash_blocked
3  human_restart_lineage_gate fail               -> 20A_human_restart_lineage_blocked
4  paper_contract_gate fail                      -> 20A_paper_contract_blocked
5  project_data/qfq/B2/project_adaptation fail   -> 20A_project_data_contract_blocked
6  execution/stateful-ledger/tradability/label-censoring fail -> 20A_execution_contract_blocked
7  residual_primary_selection_gate fail          -> 20A_residual_primary_contract_blocked
8  forward_contract_gate fail                    -> 20A_forward_contract_blocked
9  economic/cost-capacity/power freeze fail       -> 20A_economic_gate_not_frozen
10 search_accounting_gate fail                   -> 20A_search_accounting_blocked
11 implementation_readiness_gate fail            -> 20A_contract_not_impl_ready
```

## 21. Report contract

中文报告至少包含：

1. 一页 decision summary；
2. “追求正 beta，不要求 alpha”的目标声明；
3. 20A 未读取任何 outcome 的证据；
4. allowlisted paper acquisition、local full-text hashes 与 page/equation-anchored formula registry 摘要；
5. 当前本地数据覆盖和 schema；
6. `U_project != U_paper` 的 denominator 影响；
7. exact vs adaptation go/no-go 表；
8. 宽截面 PIT market-cap/E/P/industry/risk-free/CH-3 每个缺口；
9. EP19 2025 board proxy 的 43,468 membership、multi-label、非 PIT 边界、snapshot age 和 forward staleness role；
10. qfq unit/corporate-action 语义风险；
11. warm-up 后历史月份和 `design_contaminated_historical` 角色；
12. stateful NAV、locked capital、turnover/cost/capacity、economic/risk/multiplicity 与 ex-ante MDE/power gates；
13. CNN training support 结论；
14. forward boundary、6-month interim、12-month minimum evidence、约 2037 Q1 的 126-month confirmatory floor；
15. next requirement 的生成/执行授权边界。

报告必须逐字包含：

```text
EP20 的 primary objective 是可部署的正 beta，不要求 matched alpha。

Scale matching 只解释收益来源，不是正 beta 的淘汰门。

2017–2026-05 的本地历史已经被 topic 反复消费，只能提供设计证据；唯一可信支持来自 post-freeze forward。

U_project 的 top-N 截面不能冒充论文的全 A 股 U_paper。

EP19 2025 板块数据是冻结的 multi-label concept-board proxy，不是 historical PIT industry。

每个 arm 只有一条 continuous no-injection NAV ledger；blocked exit 必须继续占用真实资本。

EP19 daily B2 reference 不等于 EP20 B2 month-end adaptation；EP19 effect size 不得直接转移。

20A 没有评价任何信号收益，也没有授权 20B 执行、policy、optimization 或 deployment。
```

## 22. Implementation 与测试要求

测试至少覆盖：

```text
1. Identity/path aliases 与文件名完全一致，无绝对路径。
2. research plan 的 episode ID、superseded draft ID、正 beta objective 和 B2 role 被准确冻结。
3. EP19 final report/outcome artifacts 不在 read whitelist；B2 pre-outcome manifests 是唯一例外且只读规则/hash。
4. outcome forbidden-column scanner 对大小写、前后缀和嵌套 derived names 都 fail closed。
5. outcome_access_audit 的 outcome/selection counts 全为 0。
6. U_project primary key 唯一、date/instrument/market-cap/timing coverage 可复算。
7. qfq root inventory hash 稳定，4597 左右的本地文件变化会改变 hash 而非静默忽略。
8. qfq shares/hands 与 ratio/percent unit inventory 被识别，未归一前不得 signal-ready。
9. benchmark csi300 唯一且 calendar/date coverage 可复算。
10. EP19 cost/execution source values与 Section 8.4 完全一致；新增 transfer-fee effective-date registry 覆盖完整。
11. raw OHLCV/security master/calendar/status paths 可连接，price-limit 与 order-lot registry 覆盖所有 active rows。
12. 每个 arm 只有一条 no-injection stateful ledger；entry 只在计划 next-open 尝试，blocked buy 留 cash，blocked exit 持续占用
    NAV；下一月不得重置 1000 万资本。
13. delisting recovery 缺失时使用 -100% conservative resolution，censoring 可复算。
14. EP19 daily B2 family/grid/parameter/cooldown/entry lineage 可复算；EP20 month-end adaptation 使用同日 causal candidate p70，
    不读取 absolute spent threshold、不跨日期估计，也不继承 EP19 effect size。
15. board index 458 行、member 43,468 行、314 个有成员板块与 snapshot identity 可复算。
16. `600000.SH -> SH600000` 等 instrument normalization 可复算且 invalid rows fail closed。
17. pre-2025 board proxy 永远标 non-PIT；post-freeze 才允许 preknown forward control。
18. multi-label board transform 不做 outcome selection，不产生单一主行业。
19. board gate 失败时 residual primary 只按 preoutcome branch 从 R3 切到 R2，family size 仍为 2。
20. 可选 exact source list 为空时 exact flags=false，但 project adaptation 可为 true。
21. qfq 近似全市场不能单独使 U_paper/exact gate 通过。
22. acquire-sources 只访问论文 allowlist；核心 full-text/hash 缺失时 paper gate fail，唯一例外是 v2 明列、三方 ID 一致且
    不允许本地 full-text claim 的两项 material waiver；source material 与根目录控制文件不混放。
23. formula draft hash、source manifest hash 与 human authorization 三者一致；formula registry 的 page/equation 与所有实现选择
    字段非空；`see paper` 不通过。
24. formula registry 窗口、lambda=0.02、36m、12-1、ridge alpha=1.0、MA20/CNN geometry 固定；R3 residual 对先做 sequential
    market residual，再做 size/board cross-sectional residual，不能用减去市场常数替代。
25. project primary family 恰好 2 个，Holm alpha=0.05；comparators 不被误计为择优 arms；top-decile、tie、AUM、lot rounding、
    locked capital、cash-constraint scaling 与 continuous NAV 可机械复算。
26. matched alpha/scale independence 均为非必需，risk-source attribution 为必需。
27. positive-month rate 与两个 right-tail metrics 均不被误作 1-month primary gate；right-tail undefined month 不得填 0。
28. positive-beta economic/risk constants、ADV20、attempted/realized turnover、transfer fee、break-even multiple 与 daily-NAV
    drawdown 公式完全一致且有 parameter source。
29. MDE power formula复算为 126 complete decision-month evidence units，12 months 只标 minimum evidence；HAC lag、Holm p-value、
    Bonferroni lower bound 与 early/late split 可复算，股票行/月份均不被声明为 iid。
30. warm-up audit 不计算任何 future return，只计算历史长度、eligibility 与 primary-common-calendar early/late fold boundaries。
31. 所有 freeze 前月份均标 design_contaminated_historical/support=false。
32. CNN 任何支持门不足都输出 underpowered_not_evaluable，不能产生 OHLCV closure authorization。
33. first forward date 严格晚于 freeze seal；backfill 不能变成 forward。
34. 6–11 months 只能 interim；12–125 months 不是 confirmatory support；>=126 才可评价 confirmatory support；约 2037 Q1
    的日历预期写入报告。
35. freeze seal 后无法覆盖；输入变化要求新 contract version。
36. finalize 只读 freeze bundle，raw input read count=0。
37. stage/final manifests 与 output hashes 双向一致。
38. decision success 不要求 exact replication reachable，但要求 adaptation 与 forward pipeline reachable。
39. 所有 policy/replay/optimization/deployment authorization 恒为 false。
40. 中文报告包含 Section 21 全部边界短语，所有数字来自 machine-readable artifacts。
```

推荐命令：

```bash
python experiments/pending/20_ohlcv_positive_beta_exposure_research/src/run_20a_paper_lineage_data_and_replication_contract.py \
  --config experiments/pending/20_ohlcv_positive_beta_exposure_research/configs/config_20a_paper_lineage_data_and_replication_contract.yaml \
  --stage acquire-sources

python experiments/pending/20_ohlcv_positive_beta_exposure_research/src/run_20a_paper_lineage_data_and_replication_contract.py \
  --config experiments/pending/20_ohlcv_positive_beta_exposure_research/configs/config_20a_paper_lineage_data_and_replication_contract.yaml \
  --stage freeze

python experiments/pending/20_ohlcv_positive_beta_exposure_research/src/run_20a_paper_lineage_data_and_replication_contract.py \
  --config experiments/pending/20_ohlcv_positive_beta_exposure_research/configs/config_20a_paper_lineage_data_and_replication_contract.yaml \
  --stage finalize

python -m pytest experiments/pending/20_ohlcv_positive_beta_exposure_research/tests/test_20a_paper_lineage_data_and_replication_contract.py -q

git diff --check -- experiments/pending/20_ohlcv_positive_beta_exposure_research
```

## 23. Acceptance checklist

```text
[ ] 20A scope 只包含 pre-outcome contract/data audit。
[ ] 正 beta 目标和 alpha 非必要性写入 config、registry、decision、report。
[ ] 必需输入存在且 hashes 完整。
[ ] 核心论文 full text/appendix 已 allowlist 获取、hash，并完成人工 formula verification。
[ ] 可选 exact inputs 只从显式 config 读取。
[ ] paper source/formula registry 完整且版本角色清楚。
[ ] U_project/U_paper、paper/project return semantics 分离。
[ ] exact/adaptation claims 分离。
[ ] 2025 board proxy source identity、multi-label transform 和非 PIT 边界通过。
[ ] qfq units、adjustment semantics、coverage 通过 project gate。
[ ] cost/execution 与 EP19 19A 冻结值一致。
[ ] tradability/security-master/price-limit/blocked-exit/censoring lineage 闭合。
[ ] 每个 arm 的 stateful no-injection NAV、locked capital、fixed calendar-month return 和 corporate-action bridge 闭合。
[ ] EP19 daily B2 只作 reference；两个 EP20 month-end B2 adaptations 的 timing/entry/denominator 差异和 lineage hashes 明确。
[ ] warm-up/support audit 无 outcome。
[ ] go/no-go 表给出每条路线最高允许证据等级。
[ ] project primary family=2 且 Holm correction 冻结。
[ ] board gate 失败时 deterministic R2 fallback 不改变 hypothesis count。
[ ] economic/risk gates 全部是具体常数，无 placeholder。
[ ] ADV20、attempted/realized turnover、break-even、transfer fee、early/late stability 全部机械可复算。
[ ] CNN underpowered 状态 fail closed 且非阻断 project beta。
[ ] forward boundary、6/12/126 months、约 2037 Q1 预期和 MDE/power 机械可复算。
[ ] historical support claim 恒为 false。
[ ] outcome read/selection count 全为 0。
[ ] freeze bundle immutable，finalize 无 raw input read。
[ ] 20A success 不自动授权 20B execution。
[ ] policy/replay/optimization/deployment 全为 false。
```

## 24. 失败解释与 handoff 边界

20A 的失败只能解释为合同/数据/lineage 尚不可实现，不能解释为 TrendPV、Residual Momentum、B2 或 OHLCV 无效。

必须区分：

```text
exact_replication_not_reachable:
    缺少宽截面 PIT market-cap/E/P/CH-3/risk-free/history；不阻断 project adaptation。

historical_design_underpowered:
    warm-up 后月份太少；只降低历史诊断能力，不是信号证伪。

board_proxy_unavailable_nonblocking:
    2025 static proxy 失败只关闭 R3，并自动选择预注册的 R2 market-only fallback，不阻断 20A。

residual_primary_contract_blocked:
    R3 因 board gate 不可用，且 R2 market-only 也因必需的 benchmark/history/schema 缺失而不可实现；无法保持冻结的
    two-family primary design，20A 才被阻断。

cnn_underpowered_not_evaluable:
    不能评价 CNN，也不能据此关闭 daily OHLCV 主线。

outcome_firewall_violated:
    20A 失去 pre-outcome freeze 资格，必须废弃 bundle、修复后用新 contract version 重跑。

project_data_or_execution_blocked:
    当前不能形成可执行正 beta 测试；不得跳到历史 signal run。
```

若 `20A_preoutcome_contract_ready`，handoff 只能是生成并人工评审 20B requirement。20B 的所有历史结果仍必须标记
`design_contaminated_historical`，真正 support 只能来自冻结后的 20G forward。

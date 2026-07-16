# Requirement 20B-P4-PORTSENS：D8/D9/D10、板块集中度倾斜、交易成本与硬止损敏感性诊断

> 文档状态：`v5_policy_id_materialization_blocked_v6_repair_authorized_execution_in_progress`
>
> 生成日期：2026-07-16
>
> Experiment ID：`20_ohlcv_positive_beta_exposure_research`
>
> Phase ID：`20B_P4_PORTSENS`
>
> Run ID：`20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_v6`
>
> Contract version：`20B_P4_PORTSENS_v6`
>
> Claim ceiling：`design_contaminated_posthoc_portfolio_sensitivity_only`

## 0. 一页执行结论与不可协商范围

本 requirement 只回答四个组合层问题：

1. `S0_SELECTED_FULL` 的 D8、D9、D10 分别持有时，毛收益、净收益、换手、左尾和回撤有何差异？
2. 在持有桶内部，进一步提高本来已被该桶过度代表的概念板块权重，会改善还是恶化收益和集中度？
3. 结果对交易摩擦，特别是每边 slippage 的变化有多敏感，break-even slippage 在哪里？
4. 对持仓实施相对持仓成本基础的 `5%/10%/15%/20%` 日内 low-trigger 硬止损，会削弱左尾还是同时截断反弹？

固定研究身份：

```text
primary_scored_model_id = S0_SELECTED_FULL
mandatory_comparator_scored_model_id = B0_P4_RAW_RANK
sample_scope = sealed_robustness_21_decision_months_only
portfolio_style = long_only_monthly_rebalanced_stateful_NAV
research_role = posthoc_portfolio_sensitivity
sector_weighting_semantics = bucket_overrepresentation_concentration_tilt
board_reference_universe_dependency = retrospective_full_sample_universe_dependency
market_trading_crowding_claim_allowed = false
model_repair_claim_allowed = false
historical_support_claim_allowed = false
true_out_of_sample_claim_allowed = false
deployment_authorized = false
parameter_selection_authorized = false
```

本轮不得把 D8、D9、D10 中事后最好的一桶、板块倾斜强度、成本情景或止损阈值宣布为新策略。所有网格点必须完整输出，不得依据结果删点、改阈值或只展示最好组合。

### 0.1 四个问题的冻结解释

```text
D8 = 只持有 bucket_id 8，不包含 D9/D10
D9 = 只持有 bucket_id 9，不包含 D10
D10 = 只持有 bucket_id 10
```

`D8+D9+D10`、`D9+D10`、Top-N、动态选桶或按桶收益回看后切换，不属于 v1。若要研究累计顶部桶，必须升级 contract version。

用户提出的“拥挤板块更多权重”在 v1 固定为**板块集中度放大敏感性**，不是市场成交、资金流或关注度 crowding：

> 在同一 decision date、同一 scored model、同一持有桶内，以该桶相对完整 P4 eligible universe 的 2025 静态概念板块过度代表程度计算 concentration-tilt score；过度代表程度越高，股票目标权重乘数越大。

因此本分支回答：`已集中 -> 进一步放大集中` 的收益、左尾与集中度变化。它不回答成交额、换手率、涨停扩散、资金流或新闻关注度意义上的市场拥挤。

文件名和 run ID 中保留的 `sector_crowding` 只是 draft v1 的 legacy path token；机器语义必须读取 `sector_weighting_semantics=bucket_overrepresentation_concentration_tilt`，不得从文件名反推研究定义。

这里的板块数据是 2025-01-02 静态多标签概念板块快照，不是 2021—2026 历史 PIT 行业成员。因此：

```text
sector_tilt_lambda = 0.0 -> 不使用板块信息，可作不含板块穿越的组合基线
sector_tilt_lambda > 0.0 -> retrospective_non_PIT_board_sensitivity_only
historical_PIT_sector_claim_allowed = false
```

“硬止损”固定为相对连续持仓 spell 的 qfq-linked 加权成本基础的固定价格止损，不是 trailing stop、收盘止损、组合回撤止损或止盈。

### 0.2 禁止的捷径

- 不得用下一月收益、事件标签、当月最终板块收益或 stop 后反弹结果决定当月权重；
- 不得把 companion report 中五个事件月删除、降权或作为 switch 标签；
- 不得把 2025 静态板块成员描述成历史 PIT 行业成员；
- 不得把本轮的 bucket overrepresentation tilt 写成市场交易 crowding；
- 不得按结果挑选 D8/D9/D10、`lambda`、slippage 或 stop threshold；
- 不得把止损触发价直接当成必然成交价；gap、停牌、跌停阻塞必须进入执行路径；
- 不得把 target-weight turnover 当成真实成交换手；attempted、executed 和 target turnover 必须分开；
- 不得在止损后把释放的现金同月重新分配给其他股票；
- 不得在月末重置 NAV、补充资本或忽略未能退出的 locked position；
- 不得重训模型、重算 score、修改原 bucket assignment 或回写 sealed 20B-P4-MLRANK bundle；
- 不得把任何 sensitivity row 用作 `20C`、实盘或模型修复授权。

## 1. 身份、文件与授权边界

```text
experiment_id = 20_ohlcv_positive_beta_exposure_research
phase_id = 20B_P4_PORTSENS
run_id = 20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_v6
contract_version = 20B_P4_PORTSENS_v6
requirement_file = requirement_20b_p4_d8_d10_sector_crowding_cost_stoploss_sensitivity.md
config_file = configs/config_20b_p4_d8_d10_sector_crowding_cost_stoploss_sensitivity.yaml
runner_file = src/run_20b_p4_d8_d10_sector_crowding_cost_stoploss_sensitivity.py
test_file = tests/test_20b_p4_d8_d10_sector_crowding_cost_stoploss_sensitivity.py
output_root = outputs/20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_v6
```

执行谱系说明：v1 replay A 已通过 preflight，但因 runner 未给 `board_overrepresentation` 挂载 closed schema 要求的 `run_id/contract_version` 两列而密封为 `P1_BOARD_BLOCKED`；其 immutable output root 保留不覆盖。该问题属于实现缺陷而非研究数据 gate，v2 仅修复已冻结 schema 的物化，不改变研究公式、样本、网格或 claim ceiling。

v2 在 `P2_EXECUTION_BLOCKED` 暴露出 Top-N executable universe 只包含当日成员、不能覆盖离开 Top-N 后仍在持仓期内的证券状态。v3 冻结完整 security-state reconstruction：上市区间与 board 来自 security master；SH `is_st` 沿用上游 lifetime-ST 名称历史规则；SZ `is_st` 使用带日期更名记录 as-of；`is_suspended` 使用 exchange-open calendar 上 raw bar 是否存在，缺 bar 一律保守视为 suspended-or-unavailable；已有 project-universe 行必须与重建状态 exact 一致。该修复不改变 target population，只补齐真实持仓期执行状态。

v3 首次物化时把 SH 名称历史的 `akshare_no_tables_found_interpreted_as_no_recorded_sh_name_change` 占位文件误判为 schema failure，密封为 P2。v4 exact 恢复上游 `sh_lifetime_st_flag` 语义：名称字段存在时扫描 ST marker；明确无名称变更记录的占位文件返回 lifetime-ST=false。

v4 完成状态重建后发现原 market-rules v1 缺少 `SZ/chinext/is_st=true` 唯一命中行，并密封为 P2。深交所正式规则明确：创业板风险警示股票在注册制改革实施后涨跌幅限制为20%。v5 保留 v1 不改，新增 `a_share_price_limit_rules_v2.csv`，冻结改革前5%、改革后20%及过户费切换行；全部新增行 `human_verified=true` 且带官方来源。

v5 对 `MARKET_RULE_REGISTRY_FILE` 构成显式、单项的 20A binding supersession：20A 中 v1 的路径/hash 仅保留为 lineage evidence，v5 的执行 authority 是本 requirement 冻结的 v2 路径/hash。除该单项外，其余20A audited exact paths/hashes 继续保持 authority，不得扩展 supersession。

v5 进入 policy replay 后因 registry index 中的 `policy_id` 未回填到 simulation payload 而密封为 P2。v6 只修复该 materialization plumbing，并要求正式 replay A/B 前先执行同输入、不同 scratch root 的 unpublished diagnostic replay；diagnostic 失败不得发布 v6 bundle。

2026-07-16 用户先以 `impl it` 授权创建 config、runner 与 tests，随后以 `授权并执行` 明确授权完整历史回放、portfolio replay 与正式 output bundle 发布：

```text
requirement_generation_authorized = true
requirement_execution_authorized = true
implementation_authorized = true
historical_outcome_execution_authorized = true
portfolio_replay_authorized = true
deployment_authorized = false
```

本轮允许读取冻结的历史 outcome、执行 replay A/B、比较 core hashes，并按 P0—P5 completed-stage profile 创建正式 immutable output bundle。执行授权仍不得被误写成参数选择、模型修复或部署授权。

同一个 `run_id + contract_version` 不得覆盖任何已有成功或失败 bundle。公式、阈值、成本网格、板块源、执行语义、bucket scope、模型集合或输出 schema 发生 material change 时必须升级 contract version 和 output root。

### 1.1 Config、CLI 与 resolved contract

Config 必须 exact 冻结以下字段组：

```text
identity:
    experiment_id, phase_id, run_id, contract_version
paths:
    requirement_file, MLRANK_ROOT, CONTRACT20A_ROOT, BOARD_MEMBER,
    RAW_OHLCV_ROOT, QFQ_ROOT, TRADING_CALENDAR_FILE,
    PROJECT_UNIVERSE_FILE, SECURITY_MASTER_FILE, SH_NAME_HISTORY_ROOT,
    SZ_NAME_HISTORY_FILE,
    MARKET_RULE_REGISTRY_FILE, output_root, replay_a_scratch_root,
    replay_b_scratch_root
upstream_hashes:
    Section 3 全部 frozen SHA256
population:
    scored_model_ids, bucket_ids, split, exact date bounds,
    decision_month_n
board_concentration:
    reference_universe_rule, reference_universe_dependency,
    minimum_reference_member_n,
    duplicate_column_rule, no_board_id, fractional_membership_rule,
    no_board_tilt_rule, percentile_formula, lambda_grid, target_weight_formula,
    single_instrument_weight_cap, classified_concentration_formula,
    concentration_observation_timing
stop:
    threshold_grid, basis formula, trigger order, tick mapping,
    raw_fill_domain_rule, blocked-exit latch, re-entry rule,
    event-attribution horizon
execution:
    initial_AUM, decision/rebalance timing, lot rules,
    price-limit rules, cash constraint, suspension/corporate-action rules,
    terminal_liquidation_shadow_rule
cost:
    commission, minimum commission, stamp/transfer schedules,
    slippage grid, reference slippage, cost-shadow accounting,
    target_turnover_formula, break-even terminal-wealth formula,
    root status precedence/bracket/tolerance/max_iterations
statistics:
    month scopes, paired comparison registry, bootstrap method,
    block length, repetitions, RNG, seed, random-consumption order,
    incomplete-calendar rule, sampled-block count, quantiles
serialization:
    CSV/JSON float format, Parquet engine/compression,
    row_group_size, timestamp/date format, stable sort keys
output_contract:
    profile registry, exact artifact universe, manifest schema,
    output-hashes exclusion and finalization rules
```

唯一允许的 CLI 参数：

```text
--config <exact path>
--output-root <must exact-match config>
--replay-id {replay_a,replay_b}
```

未知 config key、缺失冻结 key、environment override、或 CLI 覆盖冻结值必须 fail closed。Preflight 必须将 exact resolved config 写入 `preflight/resolved_config.yaml`，记录 requirement/config SHA256；runner 后续阶段只读 resolved config，不得重新解析环境变量或自动发现路径。

## 2. 只回答与不回答的问题

### 2.1 只回答

1. D8、D9、D10 单桶 long-only 组合的 gross/net return、turnover、drawdown 和 tail-risk 差异；
2. 相同 D bucket 下 concentration tilt `lambda=0.5/1.0` 相对等权 `lambda=0.0` 的 paired delta；
3. 组合在不同 slippage 假设下的净收益曲线与 break-even slippage；
4. 固定硬止损相对 no-stop 的损失规避、反弹截断、成交延迟和 realized loss overshoot；
5. 上述形态在 `S0_SELECTED_FULL` 与原始 `B0_P4_RAW_RANK` 之间是否一致；
6. 五个已识别事件月的组合表现仅作事后 attribution，不参与 gate 或参数选择。

### 2.2 不回答

- 哪个参数可用于未来部署；
- 板块拥挤能否被历史 PIT 数据复现；
- 静态板块倾斜是否提供独立 alpha；
- 动态 regime switching、cash/bond timing 或 event prediction；
- Top-N、累计顶部桶、日频换仓、杠杆、做空、止盈或 trailing stop；
- 真实订单簿冲击、排队成交概率或可部署容量；
- 21个月设计污染样本是否提供 confirmatory support。

## 3. 上游 immutable 输入与完整性合同

路径别名：

```text
EXPERIMENT_ROOT = topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research
MLRANK_ROOT = EXPERIMENT_ROOT/outputs/20B_P4_learned_monotonic_return_ranking_diagnostic_v1
MLRANK_REGISTRY = MLRANK_ROOT/output_hashes_20b_p4_mlrank.json
MLRANK_MANIFEST = MLRANK_ROOT/manifest_20b_p4_mlrank.json
MLRANK_DECISION = MLRANK_ROOT/20B_P4_learned_monotonic_return_ranking_diagnostic_decision.csv
BUCKET_ASSIGNMENT = MLRANK_ROOT/scores/robustness_model_bucket_assignment.parquet

CONTRACT20A_ROOT = EXPERIMENT_ROOT/outputs/20A_paper_lineage_data_and_replication_contract
CONTRACT20A_REGISTRY = CONTRACT20A_ROOT/output_hashes_20a_paper_lineage_data_and_replication_contract.json
CONTRACT20A_MANIFEST = CONTRACT20A_ROOT/manifest_20a_paper_lineage_data_and_replication_contract.json
CONTRACT20A_FREEZE_REGISTRY = CONTRACT20A_ROOT/freeze/freeze_output_hashes_20a.json
EXECUTION_FREEZE = CONTRACT20A_ROOT/freeze/execution_fill_and_exit_rule_freeze.csv
COST_FREEZE = CONTRACT20A_ROOT/freeze/turnover_cost_capacity_formula_freeze.csv
NAV_FREEZE = CONTRACT20A_ROOT/freeze/stateful_portfolio_accounting_and_nav_freeze.csv
PRICE_LIMIT_REGISTRY = CONTRACT20A_ROOT/freeze/price_limit_rule_registry.csv
OUTCOME_ACCESS_AUDIT = CONTRACT20A_ROOT/freeze/outcome_access_audit.csv

BOARD_MEMBER = topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/outputs/tushare_dc_yearly_board_snapshot/by_year/2025/dc_member_2025_20250102.csv
RAW_OHLCV_ROOT = topics/02_AFML_BIG_WINNER/data/raw/akshare/day/raw
QFQ_ROOT = topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq
TRADING_CALENDAR_FILE = topics/02_AFML_BIG_WINNER/data/raw/akshare/status/trading_calendar.csv
PROJECT_UNIVERSE_FILE = topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
SECURITY_MASTER_FILE = topics/02_AFML_BIG_WINNER/data/raw/akshare/status/instrument_metadata_target_universe.csv
SH_NAME_HISTORY_ROOT = topics/02_AFML_BIG_WINNER/data/raw/akshare/status/sh_name_history
SZ_NAME_HISTORY_FILE = topics/02_AFML_BIG_WINNER/data/raw/akshare/status/stock_info_sz_change_name_short.csv
MARKET_RULE_REGISTRY_FILE = EXPERIMENT_ROOT/references/market_rules/a_share_price_limit_rules_v2.csv
```

若 20A sealed audit 中实际路径与上面 alias 不一致，preflight 必须以 20A `outcome_access_audit.csv` 的 audited exact path 为 authority，并要求 config 显式 exact-match；不得自动搜索替代文件。

冻结 hash：

```text
MLRANK_REGISTRY_sha256 = c535431f2f71cb6a87a738b495266662b3a8d002c173f8673defe23f855453c8
MLRANK_MANIFEST_sha256 = 052531faec928e0e2d4266dd65db60becf9803b90e105099fd943173d1982ab1
MLRANK_DECISION_sha256 = b1758469b0b43cc21543d7e469a7d531ea08cbe5c9c08110ac345df2fac5c1cf
BUCKET_ASSIGNMENT_sha256 = 9611aad6cd4b8933c882a8d3ae0e04561e8c360820f9c474a9de3a5840e5e846
CONTRACT20A_REGISTRY_sha256 = cbd05bc7bf39c084ce488fafb40d3362b805e4065fc252e67e21964f64d27f6b
CONTRACT20A_MANIFEST_sha256 = 5af3b27b0189dfc935b3622cf004a250de793b5e1aef07917866cb3b8245eda4
CONTRACT20A_FREEZE_REGISTRY_sha256 = da5902ac7a987ec061cdffc33e8735ad34c22f1ae771a43540fe005fd77acb05
BOARD_MEMBER_sha256 = e7da98e4f1e38d2f547e3c2e8a99a02aca82345e0201766a4d63e51bd43f0905
SH_NAME_HISTORY_ROOT_hash = 20879d674fe5def485776188c65c916fbfca9cc03f925822ff974f19c6de3159
SZ_NAME_HISTORY_FILE_sha256 = 10b869499050656f356f91bea9fe22760bfe6ea1964368112595073cd15041b7
MARKET_RULE_REGISTRY_FILE_sha256 = eab9e78aeb5191542426afb33f03decde073e90adb369b5eaddbf3a286d0b097
```

Preflight 必须：

1. exact 验证上述 registry、manifest、assignment 和 board member hashes；
2. 复算 MLRANK registry 与 20A freeze registry 的全部 entries；
3. 验证 MLRANK manifest 的 `immutable=true` 及 run/contract identity；
4. 解析 MLRANK decision 并 exact 验证：

   ```text
   decision_state = 20B_P4_MLRANK_metric_materialization_blocked
   selected_scored_model_id = S0_SELECTED_FULL
   baseline_scored_model_id = B0_P4_RAW_RANK
   robustness_evaluable_month_n = 21
   portfolio_optimization_authorized = false
   20C_requirement_generation_authorized = false
   20C_execution_authorized = false
   deployment_authorized = false
   ```

5. 验证 bucket assignment 不含 outcome columns，且 stable key 唯一；
6. 从 20A audited inputs 复算本轮读取的 raw/qfq/calendar/universe exact file inventory hash，并与 `OUTCOME_ACCESS_AUDIT.artifact_sha256_or_root_hash` 比较；
7. 将每个输入的 path、bytes、mtime、sha256 和 role 写入 `preflight/input_integrity_audit.csv`；
8. 任一 mismatch fail closed 为 `upstream_input_integrity_blocked`，不得接受“更新后的等价数据”。

Execution preflight 还必须对全部21个月、582只 target-union 股票的每个潜在持仓 session，使用 `exchange × board_bucket × is_st × effective date × listing-session bucket` exact join `PRICE_LIMIT_REGISTRY`。要求 rule 唯一命中、`human_verified=true`、tick/lot/transfer fields 完整；0-hit 或 multi-hit 均进入 `execution_contract_blocked`，不得到 runner 中临时猜规则。

Markdown companion report 不是机器输入 authority，runner 不得读取它来构造事件月份、参数、板块或执行规则。

## 4. 冻结样本、模型与 bucket population

从 `BUCKET_ASSIGNMENT` 只取：

```text
split = robustness
scored_model_id in {S0_SELECTED_FULL, B0_P4_RAW_RANK}
bucket_id in {8, 9, 10}
decision_date_min = 2024-07-31
decision_date_max = 2026-03-31
decision_month_n = 21
```

完整 score universe 用同一文件中该 scored model、decision date 的全部 bucket 1—10 rows。两个模型必须有完全相同的 `(decision_date, instrument_id)` population；不一致则 fail closed。

冻结审计 expectation：

```text
scored_model_n = 2
row_n_per_scored_model_all_buckets = 9300
decision_month_n_per_scored_model = 21
bucket_count_per_model_month = 10
reference_universe_union_instrument_n = 582
target_bucket_union_instrument_n = 582
minimum_bucket_n >= 1
```

每个 `(scored_model_id, decision_date, instrument_id)` 唯一，`bucket_id` 为整数 1—10。不得从 model score 重新分桶，不得更改 tie-breaker，不得因 daily bar 缺失把股票从 target population 删除；缺失只进入执行/可评价状态。

`label_month` 仅用于确定该 decision 对应的 calendar-month NAV评价窗口，不得读取 MLRANK 的 realized security label 来模拟执行。

## 5. 月度目标组合与 D8/D9/D10

每个 decision date 收盘后形成 target，下一 exchange-open session 执行。对每个 `scored_model_id × bucket_id × sector_tilt_lambda × stop_threshold` 建立一条独立、连续、无资本注入的 stateful ledger。

无板块倾斜时：

```text
candidate_set_t = exact bucket members at decision t
target_weight_i,t = 1 / candidate_n_t
target_cash_weight_t = 0
```

目标权重以总 NAV 为 denominator。blocked buy、lot rounding 或成本现金约束造成的未投资权重留现金，不得向其余股票重分配。

在 scheduled rebalance：

1. 先标记现有持仓；
2. 处理已 latch 的 stop exit 与正常 target reduction/sell；
3. 再处理 target increase/buy；
4. 若成本使现金不足，只允许复用 20A 的 common-factor scaling；
5. 不允许按 instrument 顺序选择性成交来满足现金约束。

同一 instrument 连续两个月仍在目标桶且目标股数未变时不人为先卖后买。目标差额为零不产生换手或成本。

## 6. 2025 静态多标签板块集中度与 overrepresentation tilt

### 6.1 板块成员语义

固定 source：

```text
proxy_id = ep19_dc_2025_static_board_proxy
snapshot_trade_date = 2025-01-02
classification_year = 2025
board_semantics = concept_board_multi_label
historical_PIT_industry_claim_allowed = false
board_membership_currentness_claim = false
```

`con_code` 必须按 20A 冻结映射标准化为项目 `instrument_id`。每个股票可属于多个板块；不得选一个“主板块”，不得用 outcome 选择板块子集。

板块字典只允许全局冻结一次：

```text
BOARD_REFERENCE_UNIVERSE =
    union of instrument_id over all 21 decision dates and all buckets 1..10
    after S0/B0 population exact-set equality passes

board_reference_universe_dependency =
    retrospective_full_sample_universe_dependency

retained_board = unique BOARD_REFERENCE_UNIVERSE member_n >= 10
duplicate_test_population = BOARD_REFERENCE_UNIVERSE
duplicate_rule = exact-equal binary member vector over reference universe
duplicate_retention = lexicographically smallest board_ts_code
```

这里有意保留 21 个 decision dates 的全样本并集，以确保 retained-board set 和重复列去留在整个 sensitivity 网格中唯一。该选择会让早期月份的板块字典依赖后续月份进入样本的股票，必须显式标记 `retrospective_full_sample_universe_dependency`；不得声称 board dictionary、`lambda>0` 权重或集中度结果只依赖当时可得 universe，也不得用于 ex-ante、PIT 或部署解释。

不得逐月改变 retained-board set 或重复列去留。股票未命中任何全局 retained board 时进入 synthetic `__NO_BOARD__`，不得丢弃。`__NO_BOARD__` 仅表示静态代理未覆盖，不是概念板块。全局结果必须写入 `preflight/retained_board_registry.csv`。

### 6.2 Bucket overrepresentation 公式

对股票 `i` 与板块 `b`：

```text
k_i = stock i matched retained board count
a_i,b = 1 / k_i, if i belongs to b and k_i > 0
a_i,__NO_BOARD__ = 1, if k_i = 0
a_i,b = 0 otherwise
```

因此每只股票的 fractional board memberships 加总为1，避免多标签股票机械获得更高总计数。

对同一 `scored_model_id=m`、decision date `t`、目标 bucket `d`：

```text
U_m,t = all bucket 1..10 instruments
C_m,t,d = instruments in target bucket d

universe_share_b = sum(i in U) a_i,b / |U|
bucket_share_b = sum(i in C) a_i,b / |C|
overrepresentation_ratio_b = (bucket_share_b + 1e-12) / (universe_share_b + 1e-12)
```

只在当月 `universe_share_b > 0` 的真实全局 retained boards 中，对 `overrepresentation_ratio_b` 升序排列；synthetic `__NO_BOARD__` 永不参与排名。设有效真实板块数为 `B_t`，板块 `b` 的 one-based average tie rank 为 `r_b`：

```text
tie_method = average
deterministic_secondary_sort = board_ts_code ASC

if B_t > 1:
    board_overrepresentation_pct_b = (r_b - 1) / (B_t - 1)
else:
    board_overrepresentation_pct_b = 0.5

board_overrepresentation_pct___NO_BOARD__ = 0.5
percentile_evaluable___NO_BOARD__ = false
average_tie_rank___NO_BOARD__ = missing

stock_concentration_tilt_score_i =
    if k_i > 0:
        sum over real retained boards b of
            a_i,b * board_overrepresentation_pct_b
    else:
        0.5
```

真实板块 percentile 机械映射到 `[0,1]`，最小值为0、最大值为1；所有 ties 取相同 average rank。未覆盖股票固定为中性 score `0.5`，既不因分类缺失被奖励，也不被惩罚。`stock_concentration_tilt_score` 使用当月冻结 bucket assignment、2025 静态 board membership，以及上文显式披露的全样本 retained-board dictionary；不得读取当月未来成交量、收益或新闻。它是 retrospective 集中度放大 score，不得命名或解释为 market crowding score，也不得声称 decision-time-information-only。

### 6.3 权重函数

冻结 sensitivity：

```text
sector_tilt_lambda in {0.0, 0.5, 1.0}
raw_weight_i = exp(sector_tilt_lambda * (stock_concentration_tilt_score_i - 0.5))
target_weight_i = raw_weight_i / sum(raw_weight over C)
```

`lambda=0` 必须 bitwise 等价于等权，且板块字段不得参与 target-weight decision。`lambda>0` 必须满足 concentration-tilt score 更高的股票拥有不低于 score 更低股票的权重乘数；若实现不满足则 fail closed。

目标单票权重必须 `<=10%`。若公式产生超限，不得事后 clipping 或重新优化，该 arm-month 标记 `target_concentration_blocked`。本样本 bucket 正常应有约40只以上股票，但 runner 必须机械检查而非依赖该预期。

### 6.4 板块集中度

每个 target 和实际持仓都必须报告 fractional board exposure：

```text
invested_position_weight = sum_i position_weight_i
no_board_position_weight =
    sum_i position_weight_i * a_i,__NO_BOARD__
classified_position_weight =
    invested_position_weight - no_board_position_weight

raw_board_weight_b =
    sum_i position_weight_i * a_i,b
    for real retained board b only

classified_board_coverage_ratio =
    classified_position_weight / invested_position_weight
    if invested_position_weight > 0, else missing

if classified_position_weight > 0:
    normalized_board_weight_b =
        raw_board_weight_b / classified_position_weight
    board_HHI = sum_b normalized_board_weight_b^2
    top1_board_weight = max_b normalized_board_weight_b
    top3_board_weight =
        sum of largest min(3, evaluable real board count)
        normalized_board_weight_b
    concentration_status = evaluable
else:
    board_HHI/top1_board_weight/top3_board_weight = missing
    concentration_status = not_evaluable_no_classified_board_weight
```

`__NO_BOARD__` 不得计入 HHI、Top1 或 Top3，也不得参与 tilt 排名；必须通过 `no_board_position_weight` 与 `classified_board_coverage_ratio` 单独披露覆盖缺失。因为真实板块仍是重叠概念代理，这些归一化值只能解释为已分类持仓内部的 concept-board proxy concentration，不得称为标准行业集中度或市场交易拥挤度。

Observation timing 与权重分母冻结为：

```text
target scope:
    observation = decision-date frozen target weights before execution
    position_weight_i = target_weight_i

realized_posttrade scope:
    observation = scheduled rebalance session after pending exits,
                  scheduled reductions and scheduled increases,
                  but before that session's intraday stop events
    position_weight_i = marked_position_value_i / scenario_NAV

if scenario_NAV <= 0:
    all realized concentration fields = missing
    concentration_status = not_evaluable_shadow_nav_nonpositive

mean_stock_concentration_tilt_score =
    sum_i position_weight_i * stock_concentration_tilt_score_i
    / invested_position_weight
    when invested_position_weight > 0, else missing
```

`monthly_portfolio_returns` 中的 board/no-board fields 固定取该 decision 对应的 `realized_posttrade` observation；target scope 只进入 `board_concentration_readout` 和 summary 中明确带 `target` 的指标。

## 7. 硬止损合同

### 7.1 阈值与 basis

冻结 stop 网格：

```text
stop_threshold in {none, 0.05, 0.10, 0.15, 0.20}
stop_type = fixed_hard_stop_from_position_cost_basis
trigger_price = qfq_linked_cost_basis * (1 - stop_threshold)
trailing = false
take_profit = false
portfolio_level_stop = false
```

每个 continuous holding spell 维护 qfq-linked share-weighted gross fill basis：

```text
new_basis_after_buy =
    (old_shares * old_basis + bought_shares * qfq_linked_gross_fill_price)
    / (old_shares + bought_shares)

basis_after_partial_sell = old_basis
basis_after_full_exit = null
```

Slippage、commission、tax 不进入 trigger basis，另进入 net PnL。Qfq adjustment 负责公司行动连续性；raw/qfq implied factor 不连续且无法验证时，该 instrument path fail closed，不得用 raw 未复权成本与 qfq low 混算。

### 7.2 日内 trigger 与 fill proxy

从实际买入 fill session 起，每个 exchange-open session 按以下顺序：

1. 若 session open 已低于或等于 trigger，记录 `gap_through_stop`；
2. 否则若 session low 低于或等于 trigger，记录 `intraday_touch_stop`；
3. 否则无 trigger。

执行价 proxy：

```text
gap_through_stop and executable -> qfq-linked session open
intraday_touch_stop and executable -> trigger price mapped to raw tick then back to qfq
gross proxy fill price is identical across cost scenarios
slippage -> Section 8 cost debit only; never shifts trigger, fill timestamp or gross fill price
```

Raw/qfq mapping exact：

```text
ratio_x = qfq_x / raw_x for x in {open,high,low,close} when both are finite > 0
all four ratios required on a stop trigger/fill session
factor_d = median(ratio_open, ratio_high, ratio_low, ratio_close)
relative_ratio_spread = (max(ratio_x) - min(ratio_x)) / factor_d
mapping_warning = relative_ratio_spread > 0.002
factor_mapping_pass = factor_d > 0 and relative_ratio_spread <= 0.01

raw_trigger_unrounded = qfq_trigger / factor_d
raw_trigger_tick = floor(raw_trigger_unrounded / tick_size + 1e-12) * tick_size
raw_fill_domain_lower = raw_low - 0.5 * tick_size
raw_fill_domain_upper = raw_high + 0.5 * tick_size
fill_domain_pass =
    raw_fill_domain_lower <= raw_trigger_tick <= raw_fill_domain_upper
mapping_pass = factor_mapping_pass and fill_domain_pass
qfq_linked_gross_stop_fill = raw_trigger_tick * factor_d
```

`0.002/0.01` 分别是复权价格独立两位小数落盘的 warning/block tolerance，不是收益调参阈值；必须逐日输出 spread 与 warning。Sell proxy 使用向下 tick rounding，避免向上美化成交。映射后的 intraday fill 必须落在 observed raw daily range 的 half-tick conservative boundary 内；越界时不得 clipping 到 low/high，也不得继续使用该虚构价格，必须令该 policy path 从该事件起 `raw_fill_domain_blocked` 并按 Section 10 fail closed。

Gap-through 直接使用同日 raw/qfq open pair，不经过 trigger tick；其 `fill_domain_pass` 固定检查 `raw_low - 0.5*tick_size <= raw_open <= raw_high + 0.5*tick_size`。任何 mapping/tick/rule missing、spread 超过1%或 fill-domain 检查失败都使该 policy path fail closed。

Intraday path 只有 daily OHLC，无法证明 stop-market 的真实排队成交。因此 `intraday_touch_stop` 必须标记 `daily_bar_execution_proxy=true`，不得声明真实可执行成交。

若停牌、交易状态未知或全天封死跌停：

```text
stop_latched = true
same_day_fill = false
position_remains_invested = true
locked_capital = true
retry = every later exchange-open session at first executable raw open
rebound_does_not_cancel_latched_stop = true
```

“全天封死跌停”至少要求 raw open/low/high 均位于规则下限价的 half-tick conservative boundary 内。若仅 low 触及跌停但全天并非锁死，不得机械判成无法成交。

### 7.3 Re-entry、现金与月度换仓冲突

- stop fill 后资金留现金，直到下一个 scheduled decision；
- 同一 decision cycle 内不得因股票仍在 bucket 而重新买入；
- 若 stop 已成交，股票只有在 `strictly after stop_fill_date` 的第一个 scheduled decision 后仍在目标桶时，才可作为新 holding spell 重新买入并重置 basis；
- 若 stop 已 latch 但尚未成交，下个 decision 不得增加该股票；pending exit 优先；
- stop latch 期间形成的 target 不产生延迟买入权；实际退出后必须等待退出日之后的新 decision；
- scheduled rebalance open 先执行既有 pending exit/target reduction，再开始当日新买入；当日开盘后的 low 只作用于开盘后仍持有的股数；
- blocked stop exit 跨月时，持仓继续按 daily qfq-linked mark 进入 NAV 和实际板块集中度。

### 7.4 止损不保证最大亏损

报告必须同时输出：

```text
configured_stop_threshold
trigger_to_fill_delay_sessions
gross_loss_at_fill_vs_basis
net_loss_at_fill_vs_basis
stop_overshoot = max(0, -gross_loss_at_fill_vs_basis - configured_stop_threshold)
gap_through_count
limit_down_or_suspension_block_count
```

不得把 10% 止损描述成亏损必然不超过10%。

### 7.5 止损事件反事实归因

组合层主比较始终是相同 `scored_model/bucket/lambda/cost scenario` 下 `stop arm monthly return - no-stop arm monthly return`。除此以外，每个已成交 stop event 只允许一个冻结的股票级反事实：

```text
counterfactual_horizon =
    first scheduled rebalance execution session strictly after stop_fill_date

terminal fallback =
    if no later scheduled rebalance exists, final label-month last open;
    set counterfactual_horizon_truncated = true

share_scope = exact shares sold by the stop fill
stop_proceeds_at_horizon = net stop proceeds held at cash hurdle 0
no_stop_value_at_horizon =
    same shares marked at qfq-linked horizon open when valid,
    otherwise the last valid pre-horizon mark,
    minus a mark-to-liquidation cost estimate at reference 5bps

stop_exit_vs_hold_delta_cny =
    stop_proceeds_at_horizon - no_stop_value_at_horizon

stop_avoided_loss_cny = max(stop_exit_vs_hold_delta_cny, 0)
stop_missed_rebound_cny = max(-stop_exit_vs_hold_delta_cny, 0)
```

该事件归因固定使用 reference 5bps，不随 cost shadow 展开；blocked stop 从实际 fill date 开始计算。Horizon mark-to-liquidation cost 不声称当时真实可成交，并必须设置 `counterfactual_exit_is_cost_estimate=true`。若 horizon raw/qfq mark 或 cost estimate 不可验证，三个 attribution 字段均为 missing，并记录 exact reason；不得填0。该反事实不改变任何 NAV、交易或 gate，且不得与完整 no-stop portfolio 的递归资本路径混称为因果效应。

对 `STOPNONE` policies，trigger/fill/blocked counts 固定为0，其余 stop-conditional metrics 为 missing、`status=not_applicable_no_stop`。对启用止损但 trigger N=0 的 policy，counts为0，delay/overshoot/attribution metrics为 missing、`status=not_evaluable_no_trigger`；不得用0填充条件均值。

## 8. 交易成本敏感性

### 8.1 法定与经纪成本固定

所有情景均继承：

```text
commission_buy_bps = 2.5
commission_sell_bps = 2.5
minimum_commission_cny = 5.0 per order
stamp_tax_sell_bps = 5.0 effective from 2023-08-28
transfer_fee = verified 20A effective-date registry
```

不得对 stamp tax 或 transfer fee 做任意倍数放大；它们按实际有效日期固定。

### 8.2 Slippage 网格

冻结每个已执行买卖边的 slippage：

```text
slippage_bps_per_executed_side in {0.0, 5.0, 10.0, 20.0, 40.0}
reference_slippage_bps = 5.0
gross_scenario = all transaction costs added back
```

`GROSS` 的 commission/stamp/transfer/slippage（包括 terminal shadow）全部为0；`SLIP000` 只把 slippage 设为0，法定和经纪成本仍按 Section 8.1 收取。

每条 policy execution path 只执行一次，并生成 fixed-execution cost shadows：

```text
same decision, attempted order, fill status, fill timestamp and share quantity across cost shadows
reference 5bps ledger alone enforces cash/no-borrowing constraints and determines future target shares
different commission/tax/transfer/slippage accumulated cost liability only in shadows
cost savings are not reinvested
cost shadow does not alter later target shares or fills
```

Cost-shadow accounting 固定为：

```text
gross_shadow_cash_d = reference_net_cash_d + cumulative_reference_cost_through_d
gross_shadow_NAV_d = gross_shadow_cash_d + identical marked positions

scenario_cost_liability_d = cumulative scenario cost through d
scenario_cash_after_cost_d = gross_shadow_cash_d - scenario_cost_liability_d
scenario_NAV_d = gross_shadow_NAV_d - scenario_cost_liability_d

reference_5bps_shadow_NAV_d must equal reference_stateful_net_NAV_d
```

高成本 shadow 不反向改变历史成交。若 `scenario_cash_after_cost < 0`，记录 `shadow_cash_deficit_cny` 和 `shadow_self_financing=false`，但不得把它伪装成可执行账本；若 `scenario_NAV <= 0`，该 scenario 从该日后进入 `shadow_nav_nonpositive`，当日及以后 daily/monthly percentage return 设为 missing、`scenario_evaluable=false`。但是 fixed path 的成交名义金额、累计成本负债和代数 `scenario_NAV` 仍必须推进至 terminal date，专供成本负债审计和下文 break-even terminal-wealth root；不得在 NAV 非正时停止累计后续固定成交路径成本。Gross/低成本 savings 留在 shadow cash，不再投资。

这样回答的是纯交易成本敏感性，不把成本变化引起的递归仓位差异混入结果。`reference_slippage=5bps` 的 stateful net ledger 是唯一 execution ledger；其余均显式标记 `counterfactual_cost_shadow=true` 和 `deployment_interpretation_allowed=false`。

### 8.3 成本公式

```text
buy_slippage_cost = executed_buy_notional * slippage_bps / 10000
sell_slippage_cost = executed_sell_notional * slippage_bps / 10000
commission = max(executed_notional * 2.5 / 10000, 5 CNY) per filled order
stamp_tax = executed_sell_notional * effective_stamp_bps / 10000
transfer_fee = executed_notional * effective_transfer_fee_bps / 10000

target_weight_i,t = frozen pre-execution target weight before any
                    stop, blocked-order, locked-position or cash adjustment
TARGET_UNION_t = union of instrument_id in target at t and t-1
target_weight_i,0 = 0 for every instrument before the first decision

target_one_way_turnover_t =
    0.5 * sum(i in TARGET_UNION_t)
          abs(target_weight_i,t - target_weight_i,t-1)

attempted_one_way_turnover_t =
    (intended_buy_notional_t + intended_sell_notional_t) / (2 * pretrade_NAV_t)

realized_one_way_turnover_t =
    (executed_buy_notional_t + executed_sell_notional_t) / (2 * pretrade_NAV_t)
```

Target turnover 是 formation diagnostic：股票在一侧缺失时权重按0，现金不进入求和，首个 decision 相对全零股票 target vector，因此全额等权建仓的首月值为0.5。它必须对全部21个月计算；相同 `scored_model/bucket/lambda` 的不同 stop/cost arms 必须 exact 相同。Blocked order、pending exit、locked holding 与止损现金只影响 attempted/realized turnover，不得回写 target turnover。月度成本必须按实际执行日进入连续 NAV，不得简单用 target turnover 乘一个 bps。

Break-even slippage 不允许假设月收益对 bps 线性。对相同 fixed-execution path 定义：

```text
executed_slippage_notional =
    sum of executed buy notional + executed sell notional through terminal date
fixed_live_cost =
    total commission + stamp tax + transfer fee through terminal date

live_terminal_wealth(bps) =
    gross_shadow_final_NAV
    - fixed_live_cost
    - executed_slippage_notional * bps / 10000

liquidation_terminal_wealth(bps) =
    live_terminal_wealth(bps)
    - terminal sell commission/stamp/transfer fee
    - terminal_mark_notional * bps / 10000

live_root_value(bps) = live_terminal_wealth(bps) / initial_AUM - 1
liquidation_root_value(bps) =
    liquidation_terminal_wealth(bps) / initial_AUM - 1

live_nav_break_even_slippage_bps =
    bps at which live_root_value(bps) = 0

liquidation_adjusted_break_even_slippage_bps =
    bps at which liquidation_root_value(bps) = 0

root_method = deterministic bisection
root_bracket_bps = [0, 2000]
root_tolerance_bps = 1e-8
max_iterations = 200
```

Root status first-match 固定为：

```text
1. bps-sensitive notional = 0
   -> value=missing, status=undefined_no_turnover
2. root_value(0) <= 0
   -> value=0.0, status=not_positive_at_zero_slippage
3. root_value(2000) > 0
   -> value=missing, status=above_registered_bracket
4. otherwise
   -> lo=0, hi=2000
      while iteration < 200 and hi-lo > 1e-8:
          mid=(lo+hi)/2
          if root_value(mid) > 0: lo=mid
          else: hi=mid
      value=(lo+hi)/2, status=root_found
```

Live 与 liquidation-adjusted root 分别执行上述状态机；后者的 bps-sensitive notional 包含 terminal mark notional。即使任一中间 shadow NAV 已非正，root 仍使用完整 fixed path 的代数 terminal wealth，不读取已置 missing 的 daily/monthly percentage return。不得写成无穷大。网格点只用于曲线展示和复核，不替代上述 root algorithm。

## 9. 冻结 arm registry 与网格治理

Policy execution paths：

```text
scored_model_id: 2 values
bucket_id: 3 values
sector_tilt_lambda: 3 values
stop_threshold: 5 values including none
execution_path_n = 2 * 3 * 3 * 5 = 90
```

每条 execution path 生成：

```text
gross + five slippage cost scenarios
economic_scenario_n_per_path = 6
total_economic_series_n = 540
```

Stable policy ID：

```text
{scored_model_id}__D{bucket_id}__L{lambda_token}__STOP{stop_token}
```

例如：

```text
S0_SELECTED_FULL__D10__L000__STOPNONE
S0_SELECTED_FULL__D10__L100__STOP10
B0_P4_RAW_RANK__D8__L050__STOP20
```

`lambda_token` 分别为 `000/050/100`；stop token 为 `NONE/05/10/15/20`。Config 和 preflight registry 必须 exact-set 90 rows，unknown/missing/duplicate row fail closed。

Primary OFAT anchors：

```text
bucket_anchor = S0_SELECTED_FULL, lambda=0, stop=none, reference cost; compare D8/D9/D10
sector_anchor = S0_SELECTED_FULL, D10, stop=none, reference cost; compare lambda
stop_anchor = S0_SELECTED_FULL, D10, lambda=0, reference cost; compare thresholds
cost_anchor = S0_SELECTED_FULL, D10, lambda=0, stop=none; compare cost scenarios
model_anchor = same bucket/lambda/stop/cost; compare S0 vs B0
```

Cost scenario IDs exact-set：

```text
{GROSS, SLIP000, SLIP005, SLIP010, SLIP020, SLIP040}
```

`preflight/policy_arm_registry.csv` stable key `(policy_id)`，exact 90 rows；payload columns exact 为 `scored_model_id`、`bucket_id`、`sector_tilt_lambda`、`stop_threshold`、`board_semantics_role`、`execution_role`、`claim_ceiling`。`preflight/cost_scenario_registry.csv` stable key `(cost_scenario_id)`，exact 6 rows；payload columns exact 为 `slippage_bps_per_side`、`statutory_costs_enabled`、`commission_enabled`、`gross_scenario`、`reference_execution_scenario`、`counterfactual_cost_shadow`、`deployment_interpretation_allowed`。

Paired comparison registry 必须 exact 包含：

```text
OFAT_BUCKET: 3
OFAT_SECTOR_CONCENTRATION: 2
OFAT_STOP: 4
OFAT_COST: 5
MODEL_S0_VS_B0_FULL_GRID: 3 * 3 * 5 * 6 = 270
paired_comparison_n = 284
```

每个 comparison row 必须冻结 lhs/rhs `policy_id + cost_scenario_id`、唯一变化维度、favorable direction 和 role。前14行是 primary OFAT；270个 model rows 是 mandatory full-grid comparator，不参与选参。

完整 factorial 只用于检查 interaction morphology；不得用90×6大网格选优。报告必须先展示 OFAT anchors，再展示完整网格 heatmap/appendix。

## 10. Stateful NAV、执行与可评价规则

继承 20A：

```text
initial_AUM_cny = 10,000,000
capital_injection_allowed = false
monthly_reset_allowed = false
leverage_allowed = false
short_allowed = false
decision = after close on last SSE open session of decision month
scheduled_rebalance = next exchange-open session
entry_limit_up = blocked_unfilled
scheduled_or_stop_exit_limit_down = delayed to next executable open
unfilled_weight = cash
blocked_exit = carried position consuming capital
```

Daily NAV：

```text
ledger_start_date = 2024-07-31
ledger_end_date = 2026-04-30
ledger_trade_date_n = 423
NAV_d = cash_d + sum(marked_position_value_i,d)
monthly_return_t = NAV_at_label_month_last_open / NAV_at_prior_month_last_open - 1
```

首个 prior month-end NAV 固定为 initial AUM。Suspension 使用 last valid qfq-linked mark。Corporate action bridge 按 20A；无法验证则保守 `-100% terminal position return` 并披露，不能删除股票。

最后一个 label month 末不做虚构强制清仓，primary continuous NAV 保持真实 open inventory。为避免有限样本成本曲线漏掉最后一条卖出腿，必须另外生成不改变交易路径的 terminal-liquidation cost shadow：

```text
terminal_mark_date = final label-month last open
terminal_mark_notional_i = shares_i * qfq-linked terminal close mark

terminal_liquidation_cost_shadow_cny(cost_scenario) =
    sum_i sell commission including minimum
    + effective stamp tax
    + effective transfer fee
    + terminal_mark_notional_i * scenario slippage bps / 10000

liquidation_adjusted_final_NAV =
    primary_or_cost_shadow_final_NAV - terminal_liquidation_cost_shadow_cny
```

该 shadow 不声称 terminal close 可成交，不检查次日涨跌停，也不产生实际 fill；它只补齐有限窗口的 round-trip cost estimate。必须同时报告 `terminal_open_position_weight`、逐成本情景的 cost shadow、live-NAV compound return 与 liquidation-adjusted compound return；后者不得覆盖 primary monthly NAV series。

可评价规则：

- 任一 ledger 的核心 raw/qfq mapping 不可验证时，该 policy path 从首个受影响时点进入 fail-closed，不得局部删除股票后继续；
- 某股票 entry blocked 不使整月 missing，资金留现金；
- stop fill 使用 daily-bar proxy 不使月份 missing，但必须计入 proxy count；
- 21 个 scheduled decision months 必须逐月保留，包括五个事件月；
- `event_month` 标记只能在 metrics 阶段从冻结 date list 加入，不能进入交易逻辑。

冻结 post-hoc event label months：

```text
2024-10, 2025-02, 2025-08, 2025-09, 2026-04
```

这五个月只用于 companion attribution summary；`event` 与 `non_event` 结果均不得作为参数 gate。

## 11. 指标、paired comparison 与统计单位

### 11.1 收益与风险

每条 economic series 至少输出：

```text
month_n
mean_monthly_return
median_monthly_return
compound_return
annualized_return = product(1+r)^(12/month_n)-1
annualized_volatility = std(monthly_return, ddof=1)*sqrt(12)
zero_hurdle_sharpe = mean/std*sqrt(12)
positive_month_rate
worst_month_return
empirical_p10_monthly_return
ES10_loss
max_drawdown_from_daily_NAV
event_month_mean_return
non_event_month_mean_return
```

`ES10` 以经验 p10 及以下月份的平均负收益定义；21个月只作描述，不宣称稳定 tail estimate。Sharpe 的 cash hurdle 为0，仅作比较。

### 11.2 换手、成本与持仓

```text
mean_target_one_way_turnover
mean_attempted_one_way_turnover
mean_realized_one_way_turnover
total_commission_cny
total_stamp_tax_cny
total_transfer_fee_cny
total_slippage_cny
total_cost_return
live_nav_break_even_slippage_bps
liquidation_adjusted_break_even_slippage_bps
mean_invested_weight
mean_cash_weight
mean_locked_capital_weight
minimum_effective_holdings
maximum_single_instrument_weight
terminal_open_position_weight
terminal_liquidation_cost_shadow_cny
live_nav_compound_return
liquidation_adjusted_compound_return
maximum_shadow_cash_deficit_cny
shadow_self_financing
raw_qfq_mapping_warning_n
max_relative_ratio_spread
```

### 11.3 板块与止损

```text
mean_target_board_HHI
mean_realized_board_HHI
max_top1_board_weight
max_top3_board_weight
mean_target_no_board_position_weight
mean_realized_no_board_position_weight
minimum_target_classified_board_coverage_ratio
minimum_realized_classified_board_coverage_ratio
mean_stock_concentration_tilt_score
stop_trigger_n
stop_fill_n
stop_blocked_n
mean_trigger_to_fill_delay_sessions
mean_stop_overshoot
stopped_capital_weight
stop_exit_vs_hold_delta_cny
stop_avoided_loss_cny
stop_missed_rebound_cny
stop_attribution_missing_n
```

事件级三个 stop attribution 字段严格使用 Section 7.5 的相同 shares、冻结 horizon 与 reference 5bps 公式；组合级 stop 敏感性只使用 stop/no-stop paired monthly ledger。两者均标记 `ex_post_counterfactual_attribution_only`，不得相互替代。

### 11.4 Paired deltas

按共同 calendar month 计算：

```text
D9_minus_D8
D10_minus_D9
D10_minus_D8
lambda_050_minus_000
lambda_100_minus_000
each_stop_minus_no_stop
each_cost_scenario_minus_reference_5bps
S0_minus_B0
```

至少报告 paired mean、median、win-month rate、worst paired month、event/non-event paired mean。

统计单位固定为 decision/label month，不得把股票行当独立样本。Block bootstrap：

```text
method = circular moving-block bootstrap on paired monthly deltas
block_length_months = 3
repetitions = 20000
seed = 20260716
RNG = numpy.random.Generator(numpy.random.PCG64(seed))
bootstrap_statistic = paired mean monthly delta
CI = percentile 2.5% / 50% / 97.5%, method=linear
```

每个 comparison 先按 `decision_date ASC` 取得21个冻结月份。若任一月份 `paired_evaluable=false`，保留 bootstrap readout 行，但 `CI_lower/CI_median/CI_upper=missing`、`status=not_evaluable_incomplete_calendar`；不得删除缺失月后把不相邻月份拼成 circular block。只有21个月全部可评价时才执行：

```text
n = 21
sampled_block_n = ceil(n / block_length_months) = 7
for repetition in 0..19999:
    draw 7 start indices independently with RNG.integers(0, n)
    for each start in draw order append:
        delta[(start + 0) mod n],
        delta[(start + 1) mod n],
        delta[(start + 2) mod n]
    concatenate in draw order and retain first n values
    bootstrap_value[repetition] = arithmetic mean of retained values

CI_lower/CI_median/CI_upper =
    numpy.quantile(bootstrap_value, [0.025, 0.5, 0.975], method="linear")
status = evaluable
```

RNG 只能为每个完整 run 初始化一次，并严格按 `comparison_id ASC`、每个 comparison 内 repetition 升序消费随机数；不得为 comparison 重新播种。Bootstrap CI 只用于不确定度展示，不形成参数 promotion gate，不做“CI>0即可部署”的解释。

## 12. 决策状态与 gate

本 requirement 不设置收益胜出 gate。最终机器状态只描述物化完整性：

```text
20B_P4_PORTSENS_upstream_input_integrity_blocked
20B_P4_PORTSENS_arm_registry_blocked
20B_P4_PORTSENS_board_materialization_blocked
20B_P4_PORTSENS_execution_materialization_blocked
20B_P4_PORTSENS_metric_materialization_blocked
20B_P4_PORTSENS_determinism_blocked
20B_P4_PORTSENS_seal_integrity_blocked
20B_P4_PORTSENS_sensitivity_materialized_posthoc_only
```

Candidate decision first-match 与 artifact profile：

```text
1. not upstream_integrity_gate
   -> upstream_input_integrity_blocked, P0_PREFLIGHT_BLOCKED
2. not arm_registry_gate
   -> arm_registry_blocked, P0_PREFLIGHT_BLOCKED
3. not board_formula_gate
   -> board_materialization_blocked, P1_BOARD_BLOCKED
4. not (execution_contract_gate and stop_path_gate and cost_shadow_gate)
   -> execution_materialization_blocked, P2_EXECUTION_BLOCKED
5. not metric_completeness_gate
   -> metric_materialization_blocked, P3_METRIC_BLOCKED
6. not determinism_gate
   -> determinism_blocked, P4_DETERMINISM_BLOCKED
7. otherwise
   -> sensitivity_materialized_posthoc_only, P5_SENSITIVITY_MATERIALIZED
```

只允许 first-match，不得用 later-stage `not_run` 抢占 earlier blocker。以上先产生待发布 candidate state/profile；`seal_integrity_gate` 是其后的 publication gate，不属于可在 bundle 内自证失败的 candidate profile：

```text
if candidate bundle final seal validation passes:
    seal_integrity_gate = true in published decision.csv
    publish candidate state/profile
else:
    publish no output root and no decision/manifest/hash registry
    parent_process_state = 20B_P4_PORTSENS_seal_integrity_blocked
    artifact_profile_id = NO_PUBLISHED_BUNDLE
    process_exit_code = 74
```

`seal_integrity_blocked` 只能通过 process exit status 和 parent orchestration log 返回，不能写入一个未通过密封验证的自称 immutable bundle。退出前 stderr 最后一行必须为单行 JSON：UTF-8、`ensure_ascii=false`、`sort_keys=true`、`separators=(",", ":")`、`allow_nan=false`、行末单个 LF；exact keys 为 `run_id`、`contract_version`、`parent_process_state`、`artifact_profile_id`、`blocking_reason`，其中 state/profile 必须分别为上文固定值。它会覆盖 parent 观察到的 candidate state，但不得回写或修补 `.building` 内已参与 hash 的 decision/manifest/registry。

成功状态：

```text
sensitivity_materialization_gate =
    upstream_integrity_gate
    and arm_registry_gate
    and board_formula_gate
    and execution_contract_gate
    and stop_path_gate
    and cost_shadow_gate
    and metric_completeness_gate
    and determinism_gate
    and seal_integrity_gate
```

即使所有结果为正，最终仍必须：

```text
historical_support_claim_allowed = false
model_repair_claim_allowed = false
parameter_selection_authorized = false
deployment_authorized = false
```

## 13. 必需输出与 stable schema

本节每个表的 exact schema 定义为：`stable-key columns（按声明顺序） + 声明的 payload columns（按文本/代码块顺序） + run_id + contract_version`。下文“payload columns”均为 closed set，不允许未注册额外列。日期为 `YYYY-MM-DD` string，ID/reason/status 为 UTF-8 string，`*_n/*_sessions/event_sequence` 为 nullable int64，数值指标为 float64，flags 为 boolean。任何 schema 扩展都属于 material change，必须升级 contract version。

输出 inventory：

```text
preflight/contract_snapshot.json
preflight/resolved_config.yaml
preflight/input_integrity_audit.csv
preflight/policy_arm_registry.csv
preflight/cost_scenario_registry.csv
preflight/paired_comparison_registry.csv
preflight/board_membership_audit.csv
preflight/retained_board_registry.csv
stage_failure_audit.csv

materialized/monthly_target_weights.parquet
materialized/board_overrepresentation_monthly.csv.gz
materialized/daily_execution_ledger.parquet
materialized/daily_nav.parquet
materialized/stop_event_ledger.csv.gz
materialized/cost_shadow_ledger.parquet

historical/monthly_portfolio_returns.csv.gz
historical/portfolio_summary.csv
historical/paired_sensitivity_delta.csv
historical/block_bootstrap_readout.csv
historical/turnover_cost_readout.csv
historical/board_concentration_readout.csv
historical/stoploss_attribution_readout.csv
historical/event_regime_slice_readout.csv
historical/terminal_liquidation_shadow.csv

20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_decision.csv
20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_report_cn.md
manifest_20b_p4_portsens.json
output_hashes_20b_p4_portsens.json
determinism/determinism_comparison.csv
determinism/replay_b_core_hashes.json
```

### 13.0 Preflight authority artifacts

`preflight/contract_snapshot.json` exact top-level keys：

```text
schema_version, run_id, contract_version, requirement_sha256,
config_sha256, resolved_config_sha256, execution_authority,
implementation_authorized, historical_outcome_execution_authorized,
portfolio_replay_authorized, frozen_upstream_hashes,
sector_weighting_semantics, board_reference_universe_dependency,
claim_flags
```

`preflight/input_integrity_audit.csv` stable key `(artifact_role, artifact_path)`；payload columns exact 为 `expected_sha256_or_root_hash`、`observed_sha256_or_root_hash`、`byte_size`、`mtime_utc`、`hash_match`、`schema_match`、`status`、`blocking_reason`。

`preflight/board_membership_audit.csv` stable key `(proxy_id)`；payload columns exact 为 `snapshot_trade_date`、`source_path`、`source_sha256`、`raw_member_row_n`、`normalized_member_row_n`、`invalid_instrument_row_n`、`reference_universe_instrument_n`、`reference_overlap_instrument_n`、`retained_board_n`、`duplicate_board_n`、`no_board_instrument_n`、`board_reference_universe_dependency`、`historical_PIT_industry_claim_allowed`、`board_membership_currentness_claim`、`board_formula_gate`、`blocking_reason`。

`preflight/resolved_config.yaml` 是 Section 1.1 所有冻结 key 的 canonical YAML materialization；key order 按 Section 1.1 字段组与组内字典序，禁止 YAML anchor、alias、自定义 tag 和 implicit timestamp。

### 13.1 `monthly_target_weights.parquet`

Stable key：`(policy_id, decision_date, instrument_id)`。Payload columns exact 为：

```text
scored_model_id, bucket_id, sector_tilt_lambda, stop_threshold
instrument_id, nominal_bucket_n
board_membership_n, stock_concentration_tilt_score
raw_weight_multiplier, target_weight
target_weight_sum, target_concentration_pass
source_bucket_assignment_sha256, board_member_sha256
```

`preflight/retained_board_registry.csv` stable key 为 `(source_board_ts_code)`；必须包含全部 raw board 以及 synthetic `__NO_BOARD__`，payload columns exact 为 `reference_member_n`、`minimum_member_pass`、`duplicate_group_id`、`retained_board_id`、`retained`、`synthetic`、`board_member_sha256`。同一 `retained_board_id` 只能对应一个 retained source row。

`materialized/board_overrepresentation_monthly.csv.gz` stable key 为 `(scored_model_id, decision_date, bucket_id, retained_board_id)`；每个 model-month-bucket 必须输出全局 retained boards 加 `__NO_BOARD__` 的完整集合，包括当月 universe share 为0的行。Payload columns exact 为：

```text
universe_member_fraction, bucket_member_fraction
overrepresentation_ratio
percentile_evaluable, average_tie_rank
board_overrepresentation_pct
retained_board_n_global, valid_board_n_this_month
```

真实 retained board 在 `universe_member_fraction=0` 时 ratio/rank/pct 均 missing、`percentile_evaluable=false`；不得删除该 registry row。Synthetic `__NO_BOARD__` 的 ratio 仍按覆盖缺失比例计算，仅供审计；其 `average_tie_rank=missing`、`board_overrepresentation_pct=0.5`、`percentile_evaluable=false`，且 `valid_board_n_this_month` 与 `retained_board_n_global` 均只统计真实板块。

### 13.2 `daily_execution_ledger.parquet`

Stable key：`(policy_id, trade_date, event_sequence, instrument_id)`。Payload columns exact 为：

```text
event_type in {scheduled_rebalance, stop_trigger, pending_exit_retry}
intended_side, intended_shares, intended_notional
fill_status, blocking_reason, executed_shares
raw_proxy_fill_price, qfq_linked_gross_fill_price
raw_qfq_factor, relative_ratio_spread, mapping_warning
factor_mapping_pass, raw_session_low, raw_session_high
raw_trigger_tick, raw_fill_domain_lower, raw_fill_domain_upper
fill_domain_pass, mapping_pass
position_shares_before, position_shares_after
cost_basis_before, cost_basis_after, trigger_price
cash_before, cash_after, NAV_before, NAV_after
locked_capital_weight, daily_bar_execution_proxy
```

同日顺序固定：pending exits、scheduled reductions、scheduled increases、intraday stop events；`event_sequence` 必须严格递增。

`materialized/daily_nav.parquet` stable key 为 `(policy_id, cost_scenario_id, trade_date)`；对 Section 10 的423日完整 exchange calendar 输出 `90 × 6 × 423 = 228,420` rows，即使当日无交易也必须保留。Payload columns exact 为：

```text
gross_shadow_cash, scenario_cost_liability
scenario_cash_after_cost, marked_position_value
scenario_NAV, daily_return
shadow_cash_deficit_cny, shadow_self_financing
locked_capital_weight, invested_weight
scenario_evaluable, exclusion_reason
```

其中 `SLIP005` 必须逐日 exact 等于 reference stateful net ledger；`GROSS` 的 cost liability 恒为0。

`materialized/cost_shadow_ledger.parquet` stable key 为 `(policy_id, cost_scenario_id, trade_date, event_sequence, instrument_id)`；对每个 reference executed event 输出6个 cost scenarios，row count 必须等于 `6 × reference_executed_event_n`。Payload columns exact 为：

```text
side, executed_shares, executed_notional
commission_cny, stamp_tax_cny, transfer_fee_cny, slippage_cny
total_event_cost_cny, cumulative_cost_liability_cny
counterfactual_cost_shadow, deployment_interpretation_allowed
```

### 13.3 `monthly_portfolio_returns.csv.gz`

Stable key：`(policy_id, cost_scenario_id, decision_date)`。Payload columns exact 为：

```text
label_month, gross_return, net_return
commission_return, stamp_tax_return, transfer_fee_return, slippage_return
target_one_way_turnover, attempted_one_way_turnover, realized_one_way_turnover
invested_weight, cash_weight, locked_capital_weight
effective_holdings, board_HHI, top1_board_weight, top3_board_weight
no_board_position_weight, classified_board_coverage_ratio
stop_trigger_n, stop_fill_n, stop_blocked_n
shadow_cash_deficit_cny, shadow_self_financing
month_evaluable, exclusion_reason
event_month_posthoc
```

若所有路径均完整，row count 必须为 `90 × 6 × 21 = 11,340`；blocked/month missing 仍保留 key row并设置 `month_evaluable=false`，不得缩短表。

### 13.4 `portfolio_summary.csv`

Stable key：`(policy_id, cost_scenario_id, month_scope)`，`month_scope` 只允许 `all/event_posthoc/non_event_posthoc`。必须含 Section 11 全部适用指标和 claim flags。

若 metric stage reached，row count 必须为 `90 × 6 × 3 = 1,620`。`event_posthoc` 固定5个月、`non_event_posthoc` 固定16个月；不足时保留行并记录 missing reason。

### 13.5 Paired comparison 与 bootstrap

`preflight/paired_comparison_registry.csv` stable key 为 `(comparison_id)`，必须 exact 284 rows；payload columns exact 为 `comparison_family`、`lhs_policy_id`、`lhs_cost_scenario_id`、`rhs_policy_id`、`rhs_cost_scenario_id`、`changed_dimension`、`only_one_dimension_changed`、`primary_OFAT`、`favorable_direction`。

`historical/paired_sensitivity_delta.csv` stable key 为 `(comparison_id, decision_date)`，必须保留 `284 × 21 = 5,964` rows；payload columns exact 为 `lhs_monthly_return`、`rhs_monthly_return`、`paired_delta`、`lhs_evaluable`、`rhs_evaluable`、`paired_evaluable`、`event_month_posthoc`、`missing_reason`。OFAT row 若不只改变一个冻结维度必须 fail closed。

`historical/block_bootstrap_readout.csv` stable key 为 `(comparison_id, month_scope)`；`month_scope` 只允许 `all`，必须 exact 284 rows。Payload columns exact 为 `paired_month_n`、`required_calendar_month_n`、`mean_delta`、`median_delta`、`win_month_rate`、`worst_delta`、`bootstrap_method`、`rng_bit_generator`、`seed`、`block_length_months`、`sampled_block_n`、`repetitions`、`bootstrap_statistic`、`quantile_method`、`CI_lower`、`CI_median`、`CI_upper`、`status`、`missing_reason`。Event/non-event 只在 descriptive paired summary 输出，不在5个月 event slice上运行 block bootstrap。

### 13.6 Stop、成本、集中度与 terminal readouts

`stop_event_ledger.csv.gz` stable key 为 `(policy_id, holding_spell_id, stop_event_id)`；只包含非 `NONE` stop policies 的实际 trigger。Exact columns：

```text
policy_id, holding_spell_id, stop_event_id, instrument_id
configured_stop_threshold, basis_qfq, trigger_price_qfq
trigger_date, trigger_type, gap_through, daily_bar_execution_proxy
fill_date, fill_status, blocking_reason, trigger_to_fill_delay_sessions
shares_stopped, gross_fill_price_qfq
raw_trigger_tick, fill_domain_pass
gross_loss_at_fill_vs_basis, reference_net_loss_at_fill_vs_basis
stop_overshoot
counterfactual_horizon_date, counterfactual_horizon_truncated
counterfactual_exit_is_cost_estimate
stop_proceeds_at_horizon_cny, no_stop_value_at_horizon_cny
stop_exit_vs_hold_delta_cny, stop_avoided_loss_cny, stop_missed_rebound_cny
attribution_evaluable, attribution_missing_reason
attribution_cost_scenario_id, attribution_role
```

`attribution_cost_scenario_id` 必须恒为 `SLIP005`。

其余 readouts stable keys：

```text
turnover_cost_readout.csv:
    (policy_id, cost_scenario_id)

board_concentration_readout.csv:
    (policy_id, cost_scenario_id, decision_date, concentration_scope)
    concentration_scope in {target, realized_posttrade}

stoploss_attribution_readout.csv:
    (policy_id, aggregation_scope)
    aggregation_scope in {all,event_posthoc,non_event_posthoc}

event_regime_slice_readout.csv:
    (policy_id, cost_scenario_id, event_scope)
    event_scope in {event_posthoc,non_event_posthoc}

terminal_liquidation_shadow.csv:
    (policy_id, cost_scenario_id)
```

Non-terminal readout payload columns exact：

```text
turnover_cost_readout:
    mean_target_one_way_turnover, mean_attempted_one_way_turnover,
    mean_realized_one_way_turnover, total_commission_cny,
    total_stamp_tax_cny, total_transfer_fee_cny, total_slippage_cny,
    total_cost_return, maximum_shadow_cash_deficit_cny,
    shadow_self_financing, live_nav_break_even_slippage_bps,
    live_nav_break_even_status,
    liquidation_adjusted_break_even_slippage_bps,
    liquidation_adjusted_break_even_status, raw_qfq_mapping_warning_n,
    max_relative_ratio_spread, source_table_content_hash,
    historical_support_claim_allowed, deployment_authorized

board_concentration_readout:
    board_HHI, top1_board_weight, top3_board_weight,
    no_board_position_weight, classified_position_weight,
    classified_board_coverage_ratio, concentration_status,
    mean_stock_concentration_tilt_score, effective_holdings,
    source_table_content_hash, historical_PIT_sector_claim_allowed,
    market_trading_crowding_claim_allowed

stoploss_attribution_readout:
    stop_trigger_n, stop_fill_n, stop_blocked_n,
    mean_trigger_to_fill_delay_sessions, mean_stop_overshoot,
    stopped_capital_weight, stop_exit_vs_hold_delta_cny,
    stop_avoided_loss_cny, stop_missed_rebound_cny,
    stop_attribution_missing_n, source_table_content_hash,
    ex_post_counterfactual_attribution_only, status, missing_reason

event_regime_slice_readout:
    month_n, mean_monthly_return, median_monthly_return,
    compound_return, positive_month_rate, worst_month_return,
    source_table_content_hash, posthoc_slice_only,
    parameter_selection_authorized
```

若对应 stage reached，exact row counts：

```text
turnover_cost_readout = 90 * 6 = 540
board_concentration_readout = 90 * 6 * 21 * 2 = 22,680
stoploss_attribution_readout = 90 * 3 = 270
event_regime_slice_readout = 90 * 6 * 2 = 1,080
terminal_liquidation_shadow = 90 * 6 = 540
```

`terminal_liquidation_shadow.csv` payload columns exact 为 `terminal_mark_date`、`open_position_n`、`open_position_weight`、`open_position_notional_cny`、`sell_commission_cny`、`sell_stamp_tax_cny`、`sell_transfer_fee_cny`、`sell_slippage_cny`、`total_shadow_cost_cny`、`live_final_NAV`、`liquidation_adjusted_final_NAV`、`live_nav_compound_return`、`liquidation_adjusted_compound_return`、`live_nav_break_even_slippage_bps`、`live_nav_break_even_status`、`liquidation_adjusted_break_even_slippage_bps`、`liquidation_adjusted_break_even_status`、applicable claim flags 和 `source_table_content_hash`。

### 13.7 Decision 与报告

Decision 单行必须包含：

```text
run_id, contract_version, decision_state
artifact_profile_id, reached_stage
upstream_integrity_gate, arm_registry_gate, board_formula_gate
execution_contract_gate, stop_path_gate, cost_shadow_gate
metric_completeness_gate, determinism_gate, seal_integrity_gate
execution_path_n, economic_series_n, decision_month_n
sector_weighting_semantics, board_reference_universe_dependency
market_trading_crowding_claim_allowed
historical_PIT_sector_claim_allowed
historical_support_claim_allowed
model_repair_claim_allowed
parameter_selection_authorized
deployment_authorized
blocking_reason
```

中文报告必须先回答用户的四个问题，再给完整网格附录；必须显著披露：21个月、post-hoc、静态板块非PIT、`retrospective_full_sample_universe_dependency`、`__NO_BOARD__` 中性且不进入集中度、daily-bar stop fill proxy、S0原机器失败状态以及不可选参边界。

### 13.8 Blocked-run profiles 与 hash finalization

`stage_failure_audit.csv` stable key 为 `(stage_id, check_id)`，所有 reached checks 均保留；payload columns exact 为 `status`、`expected`、`observed`、`affected_artifacts` 和 `blocking_reason`。

Artifact profile first-match：

```text
P0_PREFLIGHT_BLOCKED:
    config/input/upstream integrity blocked
P1_BOARD_BLOCKED:
    preflight and base arm registries passed;
    retained-board/target formula blocked
P2_EXECUTION_BLOCKED:
    board/target materialized; execution/stop/cost materialization blocked
P3_METRIC_BLOCKED:
    materialized ledgers reached; historical metric completeness blocked
P4_DETERMINISM_BLOCKED:
    metrics reached; replay comparison blocked
P5_SENSITIVITY_MATERIALIZED:
    all gates passed
```

Exact artifact groups：

```text
G0_FINAL_AUDIT =
    preflight/contract_snapshot.json
    preflight/resolved_config.yaml
    preflight/input_integrity_audit.csv
    stage_failure_audit.csv
    decision.csv
    report_cn.md
    manifest.json
    output_hashes.json

G1_BASE_REGISTRIES =
    preflight/policy_arm_registry.csv
    preflight/cost_scenario_registry.csv
    preflight/paired_comparison_registry.csv

G2_BOARD_TARGETS =
    preflight/board_membership_audit.csv
    preflight/retained_board_registry.csv
    materialized/monthly_target_weights.parquet
    materialized/board_overrepresentation_monthly.csv.gz

G3_LEDGERS =
    materialized/daily_execution_ledger.parquet
    materialized/daily_nav.parquet
    materialized/stop_event_ledger.csv.gz
    materialized/cost_shadow_ledger.parquet

G4_METRICS = all 9 historical/* files enumerated in Section 13 inventory

G5_DETERMINISM =
    determinism/determinism_comparison.csv
    determinism/replay_b_core_hashes.json
```

上面 `decision.csv/report_cn.md/manifest.json/output_hashes.json` 是 Section 13 inventory 中四个 exact long filenames 的别名，不是额外文件。Profile exact unions：

```text
P0 = G0
P1 = G0 + G1_BASE_REGISTRIES
P2 = G0 + G1_BASE_REGISTRIES + G2_BOARD_TARGETS
P3 = G0 + G1_BASE_REGISTRIES + G2_BOARD_TARGETS + G3
P4 = G0 + G1_BASE_REGISTRIES + G2_BOARD_TARGETS + G3 + G4 + G5
P5 = G0 + G1_BASE_REGISTRIES + G2_BOARD_TARGETS + G3 + G4 + G5
```

Config 必须逐路径复制上述 matrix，不得扩展。未 reached stage 的文件必须不存在；每个 artifact group 只能在组内全部 artifacts 通过 temporary schema/content validation 后整体进入 profile，失败 group 的 partial payload 不发布，细节只进 `stage_failure_audit.csv`。因此 board stage 在 retained-board 或 target 物化失败时只允许 P1，不能要求或发布任何 G2 partial。Manifest 的 actual file set 必须与选中 profile 双向 exact-match，任何 extra/missing path 都是 seal failure。Config 语法、identity 或 output-root 本身无法解析时属于 launch failure，必须在创建 `.building` 前退出，不发布半成品 bundle。

Finalization 顺序固定：

1. 在预先不存在的 `<output_root>.building` 写 profile 允许的 payload、decision 和 report；
2. 写 `manifest_20b_p4_portsens.json`；manifest 不得包含自身 hash、top-level output registry hash 或 bundle hash；
3. 写 `output_hashes_20b_p4_portsens.json`，其 exact sorted mapping 包含所有 regular payload 与 manifest，但排除 registry 自身；
4. `bundle_hash = SHA256(exact output-hashes registry bytes)` 只返回给 parent/log，不回写 bundle 内任何已 hash 文件；
5. 复算 registry 全部 entries、profile file-set、serialization 和 no-self-reference checks；
6. 若任一 seal check 失败：不得修改 candidate bytes 以生成失败 decision；删除 runner 自己创建的 `.building`，保持正式 output root 不存在，并仅向 parent 返回 `20B_P4_PORTSENS_seal_integrity_blocked`；
7. 若全部 seal checks 通过：published `decision.csv` 中 `seal_integrity_gate` 必须已经为 `true`，registry 写成后不得再修改任何 bundle bytes；
8. output root 必须预先不存在，以 atomic rename 将 `.building` 发布为 immutable root。

Manifest exact top-level keys：

```text
schema_version, run_id, contract_version, artifact_profile_id,
decision_state, reached_stage, immutable, requirement_sha256,
resolved_config_sha256, upstream_bindings, claim_flags, payload_files
```

`payload_files` 是按 POSIX relative path 排序的 `{path,byte_size,sha256,artifact_role}` records，排除 manifest 和 output-hashes registry。Registry 是按 path 排序的 JSON object，值为 lowercase SHA256；JSON key/order/indent/newline 必须按 Section 14 冻结。任何 manifest/registry/payload 当前阶段 self-hash、parent-directory escape、symlink 或 undeclared regular file 都使 publication gate 失败，并按上文 `NO_PUBLISHED_BUNDLE` 处理；不得发布 P0—P5 中的任何 profile。

## 14. Determinism、serialization 与密封

必须从同一 immutable inputs 独立执行 replay A/B。排序固定：

```text
policy registry: scored_model_id, bucket_id, lambda, stop threshold
weights: policy_id, decision_date, instrument_id
events: policy_id, trade_date, event_sequence, instrument_id
metrics: declared stable keys ASC
```

Serialization exact freeze：

```text
CSV:
    encoding=utf-8, newline=LF, index=false, na_rep="",
    float_format="%.12g", boolean in {true,false}, date=YYYY-MM-DD
GZIP CSV:
    compression=gzip, compresslevel=9, mtime=0, filename=""
JSON:
    UTF-8, ensure_ascii=false, sort_keys=true, indent=2,
    separators=(",", ": "), allow_nan=false, final_newline=true
Parquet:
    engine=pyarrow, version=2.6, compression=zstd,
    compression_level=9, use_dictionary=false,
    write_statistics=true, data_page_version=2.0,
    row_group_size=65536
```

所有 publishable float 写出前统一 `-0.0 -> 0.0`；NaN/inf 禁止进入 JSON，CSV/Parquet missing 只能来自 schema 明确允许的 non-evaluable fields。Column order 和 dtype 必须由 config exact schema registry 冻结，不得由 dataframe 当前列顺序推断。

Replay 必须 core-hash exact-match：resolved config、arm/cost/comparison/retained-board registries、target weights、board overrepresentation、execution ledger、cost shadows、daily NAV、monthly returns、summary、paired deltas、bootstrap、stop ledger/readout、terminal liquidation shadow 和 decision。图片和 Markdown bytes 不作为 core determinism gate，但其数据源 hash 必须记录。

成功后 output root immutable；不得在原地增补说明。后续叙事只能写 sibling companion report，或升级 contract version 重跑。

## 15. 最低测试合同

Tests 至少覆盖：

1. upstream hashes exact，任一 byte drift fail closed；
2. 2×3×3×5 exact 90 policy paths 与540 economic series；
3. S0/B0 同月 population exact；
4. D8、D9、D10 为互斥单桶，不自动累计；
5. `lambda=0` bitwise 等权；
6. fractional multi-label memberships 对每只股票 sum=1；
7. 21个月全样本 retained-board dictionary 唯一、`retrospective_full_sample_universe_dependency` exact，且不得逐月变更字典；
8. overrepresentation ratio、真实板块 percentile endpoints、weight monotonicity 与 duplicate-board deterministic drop；
9. `__NO_BOARD__` score恒为0.5、不参与排名/HHI/Top exposure，并单独报告覆盖率；
10. target weights sum=1 且单票不超过10%；
11. next-open execution、blocked buy留现金、blocked exit占资；
12. unchanged holding 不产生虚构 round trip；
13. stop basis 在加仓时加权、减仓时不变、清仓时清空；
14. gap-through、intraday touch、全天跌停、停牌和 rebound-after-latch cases；
15. intraday raw trigger tick 与 gap open 的 half-tick fill-domain 检查，越界 fail closed 且不得 clipping；
16. stop 后同 decision cycle 不 re-entry；
17. 5/10/15/20% thresholds exact，none arm 不读 daily low 做交易决策；
18. reference ledger 与 cost shadows fill/share path exact 相同，SLIP005 shadow逐日等于reference NAV；
19. commission minimum、stamp effective date、transfer fee、slippage、cost liability 与 high-cost shadow deficit 分项正确；
20. target turnover 使用21个月、股票并集、前一期缺失权重0、首月全零向量且不含现金；attempted/realized turnover 的分母与 blocked-order 处理正确；
21. final open inventory 不强制清仓，terminal liquidation shadow只扣成本且不覆盖primary NAV；
22. monthly NAV return 使用固定 calendar month-end；
23. stop overshoot 可大于 threshold 且不会被截断；
24. OFAT paired rows只改变一个维度；
25. event labels 不可进入 target、fill 或 stop逻辑；
26. bootstrap 的21月完整性、PCG64、单次播种、comparison消费顺序、7个circular blocks、截断和linear quantile exact；
27. blocked synthetic cases 给出预期 decision state；
28. replay A/B core hashes exact；
29. raw/qfq four-price factor、relative spread tolerance、sell tick-down mapping exact；
30. price-limit registry 对全部582只 target-union股票潜在持仓日 unique-hit；
31. cost break-even 使用完整 fixed path algebraic terminal wealth 与冻结 bisection；中间NAV非正也继续累计成本负债；
32. stop event hold-to-next-rebalance counterfactual、truncated terminal fallback 与 missing behavior exact；
33. cost scenario IDs exact 6、paired comparison registry exact 284；
34. monthly return 11,340 rows、summary 1,620 rows、paired monthly delta 5,964 rows；
35. daily NAV 与 cost-shadow stable key/cardinality、GROSS zero liability；
36. P0—P5 的 G0/G1_BASE/G2_BOARD_TARGETS/G3/G4/G5 allowed/required file set 双向 exact；
37. seal failure 使用 exit code 74 和 canonical stderr record 返回 `NO_PUBLISHED_BUNDLE` parent state，且不发布 output root；
38. manifest/output registry 无 self-hash，registry 排除自身，final registry 后 bytes 不再变化；
39. unknown config/CLI/environment override fail closed，resolved config hash稳定。

## 16. 验收清单

- [x] 本轮已授权并完成 config/runner/tests 实现，并已明确授权完整历史回放与 output bundle 发布。
- [x] S0 primary 与 B0 mandatory comparator 固定。
- [x] 只使用21个 sealed robustness decision months，五个事件月不删除。
- [x] D8/D9/D10 被定义为三个互斥单桶组合。
- [x] 目标明确为 bucket overrepresentation 的板块集中度放大，不解释为市场交易 crowding。
- [x] 全样本 retained-board universe 可机械复算，并显式标记 `retrospective_full_sample_universe_dependency`。
- [x] `__NO_BOARD__` 中性、不参与板块排名/集中度，覆盖缺失单独披露。
- [x] Fractional multi-label、真实板块 percentile 和权重公式可机械复算。
- [x] `lambda={0,0.5,1}` 完整，静态2025板块的 non-PIT claim ceiling 显著。
- [x] 交易成本拆分法定费用与 `{0,5,10,20,40}` bps slippage shadows。
- [x] 固定成交路径成本敏感性与 reference stateful net ledger 不混淆。
- [x] 高成本 shadow deficit、完整 fixed-path terminal wealth、break-even bisection 与 terminal liquidation cost shadow闭合。
- [x] stop `{none,5%,10%,15%,20%}`、basis、trigger、gap、raw fill-domain、blocked exit、re-entry 全部冻结。
- [x] 止损后现金不在同月重分配，blocked exit 持续占资。
- [x] 90 execution paths、540 economic series exact-set。
- [x] 收益、回撤、tail、换手、成本、板块集中度、止损 attribution 输出齐全。
- [x] OFAT anchors 先于 factorial appendix，禁止事后选优。
- [x] 284个 paired comparisons 与全部输出 cardinality/stable schema冻结。
- [x] 决策只评价物化完整性，不产生策略 pass/deploy label。
- [x] P0—P5 completed-stage artifact profiles、seal-failure no-publish、serialization、manifest、no-self-hash 和 immutable finalization完整。

## 17. 实现 handoff gate

本轮 reviewer 指出的研究语义与执行闭合项已转为 config、runner 与 tests，不再保留 runner 自由选择。未来获得明确历史执行授权后，preflight 必须机械验证：

1. exact paths/hashes 与20A audited inputs一致；
2. 582只 target-union股票的 raw/qfq 文件覆盖完整，所有实际 stop session 的 four-price mapping 与 raw fill-domain 通过；
3. price-limit/security-state registry 对每个潜在持仓日唯一命中；
4. reference 5bps ledger自融资，其他 cost shadows不反向改变 shares/fills并正确披露 deficit；
5. 静态2025概念板块只形成带 `retrospective_full_sample_universe_dependency` 的 concentration tilt，`__NO_BOARD__` 保持中性，所有 claim flags保持false；
6. 90 paths、540 series、284 comparisons、schemas/cardinalities和P0—P5 artifact profile exact；
7. replay、manifest、registry、no-self-hash、seal-failure no-publish 和 atomic immutable publish闭合。

除 launch failure 与 seal failure 按 Section 13.8 不发布 bundle 外，任何一项失败都必须进入 Section 12 对应 blocked state/profile；不得在 runner 内临时发明 fallback。本轮历史回放与 output bundle 发布已授权，但不构成参数选择、模型修复或部署授权。

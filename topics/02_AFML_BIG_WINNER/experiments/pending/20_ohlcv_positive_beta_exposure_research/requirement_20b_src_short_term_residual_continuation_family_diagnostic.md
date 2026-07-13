# Requirement 20B-SRC：Short-Term Residual Continuation Family 设计诊断

## 0. 不可协商范围

20B-SRC 新建一个独立的 **short-term residual continuation** family，用日频、逐日因果更新的 market residual，检验
1 周与 2 周形成期是否对应 1 周与 2 周的正向收益暴露。

它不是 20B P4 的短持有期 appendix，也不得回写、覆盖或重新解释已经密封的 20B v5。两条 family 必须保持分离：

```text
20B P4 = monthly sequential market residual + 12-1 residual score + 1-month primary holding
20B-SRC = daily sequential market residual + 5D/10D continuation score + 5D/10D forward labels
```

20B-SRC 只允许：

- 公式 QA 与日频 timing audit；
- 固定 weekly decision calendar 上的 5D/10D formation × 5D/10D holding 完整诊断；
- favorable bucket 绝对 gross return、排序 morphology、时间稳定性与 fragility readout；
- 相对同周期 total-return continuation、Low Vol 与 all-eligible baseline 的 paired attribution；
- 判断该 family 更像独立 sleeve 线索、短期 participation/meta-label 线索，还是无效方向。

20B-SRC 不允许：

- 声称复制 Blitz et al. 或 Jansen et al. 的 12-1 residual momentum；
- 用 5D/10D 结果修复 20B v5 的 `43 < 60` sample gate；
- 从 formation/holding grid 中挑选最好组合并隐藏其余组合；
- 缩短 beta estimation window、改变 benchmark、winsorize、neutralize 或调 bucket 后仍沿用同一 contract version；
- 生成或执行现有 Stage 20C；
- policy training、policy replay、portfolio optimization 或 deployment；
- 把 close-to-close cohort return 冒充 next-open、成本后、cash-inclusive、full-capital stateful NAV。

固定语义：

```text
family_id = short_term_market_residual_continuation_adaptation
primary_objective = short_horizon_positive_beta_design
incremental_alpha_required = false
historical_sample_role = design_contaminated_historical
historical_support_claim_allowed = false
exact_replication_claim_allowed = false
best_horizon_selection_allowed = false
existing_20C_authorization_impact = none
tradability_assumption = all_registered_denominator_rows_tradable
daily_suspension_source_required = false
suspension_carry_allowed = false
missing_qfq_mark_policy = unknown_data_gap_fail_closed
```

报告必须逐字披露：

```text
20B-SRC 是 outcome-contaminated historical design diagnostic。它在 20B 月度 P4 结果已被观察后提出，任何历史结果都不能形成 true OOS support。

20B-SRC 改变了 signal formation frequency 与 formula family；它不是 20B P4 的 1 周/2 周 holding sensitivity，也不是论文 12-1 Residual Momentum 的 exact replication。

Weekly rows 与 10-session overlapping labels 不是独立证据。样本量、HAC、block bootstrap 和 fold 统计必须按冻结的 weekly/calendar block 口径报告，不能把 instrument rows 或重叠 cohort rows当作独立 N。

Favorable-minus-unfavorable 为正不能替代 favorable bucket 绝对收益为正。A 股 long-only 正 beta 判断不得依赖不可执行 short leg。

本阶段没有 next-open fill、blocked entry/exit、持续资本、现金腿、实际费用扣账、实际滑点或容量；只有继承 20A 冻结成本的
target-turnover pressure-test proxy，因此任何结果都不能称为 deployable sleeve 或 net strategy。

20B-SRC 不读取、不推断逐日停牌状态。所有进入 registered decision denominator 的股票均假设可交易；这是一项乐观的设计近似，不能作为成交可行性或 executable/deployable 证据。缺失 qfq mark 仍按 unknown data gap fail closed，不得因“假设可交易”而 carry、补零或插值。
```

---

## 1. 身份、文件与授权边界

```text
experiment_id = 20_ohlcv_positive_beta_exposure_research
phase_id = 20B_SRC
run_id = 20B_SRC_short_term_residual_continuation_family_diagnostic_v0
contract_version = 20B_SRC_v0
requirement_file = requirement_20b_src_short_term_residual_continuation_family_diagnostic.md
config_file = configs/config_20b_src_short_term_residual_continuation_family_diagnostic.yaml
runner_file = src/run_20b_src_short_term_residual_continuation_family_diagnostic.py
test_file = tests/test_20b_src_short_term_residual_continuation_family_diagnostic.py
output_root = outputs/20B_SRC_short_term_residual_continuation_family_diagnostic_v0
signal_authorization_relative_path = authorizations/signal_materialization_authorization.json
outcome_authorization_relative_path = authorizations/outcome_materialization_authorization.json
```

本 requirement 的生成由 workspace user 当前指令直接授权，但生成 spec 不等于授权实现或读取新 outcome：

```text
requirement_generation_authorized = true
implementation_authorized = false
historical_signal_execution_authorized = false
historical_outcome_execution_authorized = false
true_forward_execution_authorized = false
20C_requirement_generation_authorized = false
20C_execution_authorized = false
policy_training_authorized = false
policy_replay_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

只有用户完成 requirement 评审并明确发出实施/运行指令，才可创建 config、runner、tests 或访问新的 5D/10D outcome。

同一 `run_id + contract_version` 不得覆盖已密封 bundle。下列任一变化都必须新建 contract version：

- decision frequency 或 weekly calendar；
- beta estimation window/minimum pairs/benchmark；
- formation window、holding horizon 或 matched-primary mapping；
- return、missingness、delisting 或 tradability assumption；
- universe timing、bucket、weighting、sample floor 或 gate；
- comparator、cost proxy 或 inference method。

### 1.1 Config contract

未来 config 必须逐值冻结并由 runner fail-closed 校验：

```text
identity: run_id, experiment_id, phase_id, contract_version
paths: requirement, research_plan, upstream_20a_root, upstream_20b_root,
       project_universe, qfq_root, benchmark, trading_calendar, security_master, output_root
boundary: history_date_min, history_date_max
calendar: decision_frequency, week_definition
residual: estimation_calendar_sessions=252, minimum_paired_observation=200,
          benchmark_alias=csi300, rcond=1e-12
formation: [5, 10]
holding: [5, 10]
sorting: bucket_counts=[5,10], primary_bucket_count=10, weightings=[EW,VW]
inference: hac_lag_weeks=4, block_length_weeks=13,
           bootstrap_repetitions=5000, bootstrap_seed=20020
style: warning_minimum_finite_week_n=52, jaccard_common_population_minimum_n=100
tradability: assumption=all_registered_denominator_rows_tradable,
             daily_suspension_source_required=false, suspension_carry_allowed=false,
             missing_qfq_mark_policy=unknown_data_gap_fail_closed
residualization_value: minimum_paired_favorable_delta_bps_per_session=1.0,
                       favorable_nondegradation_tolerance_bps_per_session=-0.5,
                       minimum_paired_spread_delta_bps_per_session=1.0,
                       maximum_paired_volatility_ratio=0.95,
                       maximum_paired_ES10_loss_ratio=0.95
cost_proxy: source_contract=20A_v2, break_even_one_way_cost_multiple_floor=1.25,
            minimum_commission_included=false,
            stamp_tax_proxy_mode=current_5bps_applied_uniformly_to_history,
            transfer_fee_mode=verified_effective_date_schedule
serialization: json_allow_nan=false, csv_float_format="%.12g", parquet_engine=pyarrow,
               parquet_compression=zstd, gzip_compresslevel=9, gzip_mtime=0
sample_floors: every value in Section 12.1
authorization: signal_authorization_relative_path, outcome_authorization_relative_path,
               signal/outcome authorization records and bound bundle hashes
```

Unknown config key、requirement/config 值不一致或未绑定 authorization hash 必须 fail；不得让 CLI flag 静默覆盖冻结公式参数。

---

## 2. 上游事实与不继承的授权

### 2.1 必须核验的上游 artifacts

路径别名：

```text
TOPIC_ROOT = topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/20_ohlcv_positive_beta_exposure_research
UPSTREAM_20A_ROOT = EXPERIMENT_ROOT/outputs/20A_paper_lineage_data_and_replication_contract
UPSTREAM_20B_ROOT = EXPERIMENT_ROOT/outputs/20B_trendpv_residual_momentum_design_and_replication_diagnostic_v5
PROJECT_UNIVERSE_FILE = TOPIC_ROOT/data/processed/universe/pit_topn_400_100_executable_daily.csv
QFQ_ROOT = TOPIC_ROOT/data/raw/akshare/day/qfq
BENCHMARK_FILE = TOPIC_ROOT/data/processed/index/benchmark_indices_daily.csv
TRADING_CALENDAR_FILE = TOPIC_ROOT/data/raw/akshare/status/trading_calendar.csv
SECURITY_MASTER_FILE = TOPIC_ROOT/data/raw/akshare/status/instrument_metadata_target_universe.csv
UPSTREAM_20A_COST_AUDIT = UPSTREAM_20A_ROOT/freeze/execution_and_cost_inheritance_audit.csv
UPSTREAM_20A_COST_FORMULA_FREEZE = UPSTREAM_20A_ROOT/freeze/turnover_cost_capacity_formula_freeze.csv
UPSTREAM_20A_EXECUTION_RULE_FREEZE = UPSTREAM_20A_ROOT/freeze/execution_fill_and_exit_rule_freeze.csv
UPSTREAM_20A_PRICE_LIMIT_RULE_REGISTRY = UPSTREAM_20A_ROOT/freeze/price_limit_rule_registry.csv
UPSTREAM_20A_OUTCOME_ACCESS_AUDIT = UPSTREAM_20A_ROOT/freeze/outcome_access_audit.csv
UPSTREAM_EP19_COST_FREEZE = TOPIC_ROOT/experiments/pending/19_entry_universe_pit_tradability_preflight/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/replay_cost_assumption_freeze.csv
```

冻结的上游身份：

```text
20A_contract_version = 20A_v2
20A_freeze_bundle_hash = da5902ac7a987ec061cdffc33e8735ad34c22f1ae771a43540fe005fd77acb05
20B_contract_version = 20B_v5
20B_decision_state = 20B_underpowered_design_diagnostic
20B_historical_bundle_hash = bac77bc13efcd7b75df5b18f44940bcc24e57589e62dde593bd0ef748705426f
20B_20C_requirement_generation_authorized = false
20A_price_limit_rule_registry_sha256 = d9fcdb64142a261bfe785f834067874281f8242d508ec02d1ddd6cf7f55c980b
20A_linked_EP19_cost_freeze_sha256 = 2b164c5aff823b1ebddb679a93936dc3a637b4252ca10c8d4252d92e3bfee7ac
```

Preflight 必须复算 20A/20B machine manifests 与 output hashes。20B v5 报告存在 post-seal narrative 增补，因此：

- 只能把 sealed machine decision、historical artifacts、manifest 与 hash registry 用作上游 authority；
- 不得要求增补后 Markdown 字节等于旧 final manifest 中的 report hash；
- 不得从报告叙事反向提取、重建或修改 v5 machine decision；
- report 只可作为研究动机与人工解释输入，不是新 family 的 signal/outcome source。

`upstream_integrity_gate` 同时要求 20A/20B bundle identities、两条显式 cost-source hashes、20A outcome-access 中对 EP19 cost source
的 recorded hash，以及所有 referenced sealed cost artifacts 全部匹配。任一 source/hash mismatch 进入 upstream-integrity blocked，
不能降格成普通 cost-infeasible economic state。

Required preoutcome output：

```text
preoutcome/upstream_integrity_audit.csv
```

最少字段：

```text
artifact_id
artifact_path
artifact_role
expected_sha256
observed_sha256
expected_value
observed_value
status
blocking_reason
```

### 2.2 继承与不继承

允许继承：

- `U_project` 与 qfq/provider proxy 的数据 lineage；
- CSI300 是 R2 market-only adaptation benchmark 的身份；
- provider-qfq 不是 exact total-return database 的声明边界；
- 20A v2 冻结的 commission、stamp tax、slippage、transfer-fee schedule 与 `1.25` break-even cost multiple；
- design-contaminated historical、no support、no deployment 的治理语义；
- favorable bucket 与 long-short spread 分离的正 beta 目标。

明确不继承：

- 20B P4 的 monthly beta、monthly residual rows、12-1 score 或 monthly bucket assignments；
- 20B P4 的 sample floor、early/late fold 或 20C family bridge authorization；
- P5 static board residualization；
- 20B 1/3/6/12-month holding registry；
- 任何现有 20C generation/execution authorization。

---

## 3. 研究问题、冻结假设与解释角色

### 3.1 只回答的问题

20B-SRC 只回答：

1. 使用严格逐日 causal rolling market regression，能否稳定物化 5D 与 10D market residual continuation score？
2. 5D residual formation 对未来 5 sessions、10D residual formation 对未来 10 sessions 的 favorable bucket 绝对 gross return 是否同方向为正？
3. 5D/10D cross mappings 是否显示快速衰减、延迟兑现或反转？
4. residualization 相对相同 formation/holding 的 total-return continuation 是否带来正收益、spread、波动或 left-tail 改善？
5. 结果是否主要重合于 Low Vol、size 或单一月份/股票？
6. 该 family 应进入 true-forward 冻结候选、降级为 participation/meta-label 候选，还是停止？

### 3.2 不回答的问题

本 requirement 不回答：

- 5D 与 10D 哪个“最好”；
- 20/40/60/120/252/756-session beta window 哪个最好；
- 是否存在独立 alpha；
- 是否可以直接交易；
- 是否可替代 20B P4/P5、Low Vol 或现有 C3；
- 是否通过现有 20C gate。

### 3.3 冻结假设

```text
H1_5x5:
    5D market-residual continuation 高分组未来 5 sessions 的绝对 gross return 为正。

H2_10x10:
    10D market-residual continuation 高分组未来 10 sessions 的绝对 gross return 为正。

H3_residualization_value:
    在相同 formation/holding、decision week 与 return semantics 下，residual continuation 相对 total-return continuation
    至少在 favorable return、spread、volatility 或 ES10 中达到 Section 12.5 冻结的 material improvement，且 early/late
    favorable paired delta 均不超过容忍恶化；不能靠任意 epsilon 改善或 unfavorable bucket 更差通过。

H4_path_shape:
    5D/10D 完整矩阵可以区分 fast decay、delayed realization 与 persistent short-horizon continuation；不得按 outcome
    选择其中一个 horizon 作为事后 primary。
```

H1/H2 是 matched primary。H3 是 residualization attribution，不是 incremental-alpha 必要门。H4 是机制 readout。

---

## 4. Staged execution、read whitelist 与 outcome firewall

### 4.1 四阶段执行

未来实现必须分四阶段：

```text
stage 1 = preflight
    verify upstream bundles and input schemas;
    freeze calendar, universe timing, arms, formulas, horizons, sample floors, folds and gates;
    do not read any newly computed 5D/10D forward outcome;
    seal preoutcome bundle.

stage 2 = signal-materialization
    require explicit human authorization bound to preoutcome bundle hash;
    materialize row-causal daily returns, rolling market models, daily residuals, weekly scores and bucket assignments;
    enforce feature_max_date <= decision_date for every row;
    seal signal bundle before forward labels or portfolio returns are joined.

stage 3 = outcome-materialization
    require explicit human authorization bound to signal bundle hash;
    join only registered H=5/H=10 outcomes to sealed assignments;
    materialize every registered arm/horizon, including missing and failed rows;
    prohibit formula, arm, bucket or threshold changes.

stage 4 = finalize
    read only sealed preoutcome, signal and outcome artifacts;
    create decision, report and final manifests;
    do not reread raw qfq/universe/benchmark data.
```

Signal/outcome authorization records 必须分别包含：

```text
authorization_stage
authorized_by
authorization_source
authorized_at_utc
bound_run_id
bound_contract_version
bound_input_bundle_hash
allowed_read_scope
authorization_record_sha256
```

冻结的治理输入路径：

```text
BUILD_ROOT = OUTPUT_ROOT with literal suffix `.building`
SIGNAL_AUTHORIZATION_RELATIVE_PATH = authorizations/signal_materialization_authorization.json
OUTCOME_AUTHORIZATION_RELATIVE_PATH = authorizations/outcome_materialization_authorization.json
before final publication: authorization file = BUILD_ROOT / registered relative path
after final publication verification: authorization file = OUTPUT_ROOT / registered relative path
SIGNAL_AUTHORIZATION_FILE / OUTCOME_AUTHORIZATION_FILE = the corresponding resolved active-root path
```

Authorization JSON 使用 Section 16 的 canonical JSON writer；`authorization_record_sha256` 是先移除该字段后，对其余对象按
canonical compact JSON 计算的 SHA256。Runner 必须复算并要求：signal record 的 `bound_input_bundle_hash` 等于 sealed
preoutcome bundle hash，outcome record 的值等于 sealed signal bundle hash；文件路径、stage、run/version、hash 或
`allowed_read_scope` 任一不匹配均 fail closed。Authorization 文件是 human-provided governance input，runner 不得自行生成、补写
或把 CLI 中单独提供的 hash 冒充 human authorization。

`historical_signal_execution_authorization_gate` 只有在 signal authorization 绑定 sealed preoutcome hash 时为 pass；
`historical_outcome_execution_authorization_gate` 只有在 outcome authorization 绑定 sealed signal hash 时为 pass。不得用一次未绑定
hash 的笼统授权同时通过两级 gate。

### 4.2 Stage-specific read whitelist

`preoutcome/read_whitelist.json` 必须为四个 stage 各物化一条冻结记录。允许范围如下。

Preflight 允许读取：

```text
this requirement and research_plan.md
20A/20B sealed manifests, decisions and schema metadata
20A sealed cost/transfer-fee artifacts and the single EP19 cost-freeze file hash-linked by 20A
PROJECT_UNIVERSE_FILE headers, key/date inventory and availability columns
QFQ_ROOT file names, headers, date ranges, unit metadata and full `instrument` identity column only
BENCHMARK_FILE identity, headers and date range only
TRADING_CALENDAR_FILE
SECURITY_MASTER_FILE schema/status lineage only
future config
```

Preflight 禁止读取或计算：

```text
new forward_return_5d / forward_return_10d
new bucket returns or horizon comparisons
future_return*, MFE*, MAE*, winner*, strategy NAV/PnL
any unregistered formation or holding horizon
```

Signal-materialization 只允许读取：

```text
sealed preoutcome bundle and verified SIGNAL_AUTHORIZATION_FILE
PROJECT_UNIVERSE_FILE rows/columns registered by preoutcome schema
QFQ_ROOT registered files, including complete physical files
BENCHMARK_FILE registered CSI300 rows
TRADING_CALENDAR_FILE
SECURITY_MASTER_FILE identity/listing/delisting columns only
```

Signal stage 禁止读取任何 historical outcome artifact、forward-return table、旧策略 PnL/NAV 或未注册 horizon。Raw qfq
中 decision 之后的 rows 可以被物理加载，但贡献规则严格服从 Section 4.3。

Outcome-materialization 只允许读取：

```text
sealed preoutcome bundle, sealed signal bundle and verified OUTCOME_AUTHORIZATION_FILE
QFQ_ROOT registered files
TRADING_CALENDAR_FILE
SECURITY_MASTER_FILE identity/listing/delisting columns only
```

Outcome stage 不得重读 `PROJECT_UNIVERSE_FILE` 后重建 denominator，不得重算 signal/rank/bucket/target weight，也不得读取未注册
outcome family。Finalize 只允许读取 sealed preoutcome/signal/historical bundles 与两份 verified authorization records；不得读取任何
raw qfq、universe、benchmark、calendar 或 security-master 文件。

### 4.3 Signal-stage causal firewall

日频文件同时承载历史 feature 与后续 outcome，因此 signal stage 必须通过 row-level causal audit，而不能只靠文件级白名单：

```text
for every daily residual row:
    regression_max_date < residual_date

for every weekly signal row:
    feature_max_date <= decision_date
    universe_membership_available_time <= decision_date close

for every outcome row:
    outcome_start_date > decision_date
    outcome_end_date == registered H-th future exchange session
```

Signal stage 不得生成或保留任何以 decision date 之后价格构造的 feature/label 列。除注册的 access-audit lineage 字段
`future_rows_loaded/future_rows_contributed/outcome_class/outcome_role_table_access_count` 外，signal feature/materialization tables
中出现 `forward_* / future_* / label_* / outcome_* / MFE* / MAE* / winner*` 必须 fail closed。

由于原始 qfq 文件同时包含 decision 之前与之后的 rows，firewall 必须区分“物理读取文件”与“row 对 signal 的贡献”：

```text
outcome_role_table_access_count = 0
future_rows_loaded_from_raw_qfq >= 0
future_rows_contributed_to_signal = 0
max_contributing_date <= decision_date for every weekly signal row
```

Signal stage 可以一次性读取完整 raw qfq 文件；这会记入 `max_date_read/future_rows_loaded`，但不能仅因此判 firewall fail。
只有 registered outcome-role table 被读取、future row 对 signal 计算有贡献，或无法证明 `max_contributing_date <= decision_date`
时才 fail closed。`outcome_access_count` 若保留为兼容字段，必须定义为 outcome-role table access count，不得把 raw qfq 的物理
读取误记为 outcome access。

### 4.4 Access audit

每次读取必须追加：

```text
access_sequence_id
stage
accessed_at_utc
artifact_path
artifact_sha256_or_root_hash
dataset_role
max_date_read
max_date_contributed
decision_date_context
allowed_by_whitelist
outcome_class
row_count
future_rows_loaded
future_rows_contributed
```

Required outputs：

```text
preoutcome/read_whitelist.json
signal/signal_access_audit.csv
historical/outcome_access_audit.csv
```

任何未注册 outcome access、`future_rows_contributed > 0`、或 signal lineage 的 `max_date_contributed > decision_date_context`
导致 terminal state `20B_SRC_outcome_firewall_violated`。`max_date_read > decision_date_context` 本身不构成违规。

---

## 5. Input、boundary 与数据质量合同

### 5.1 Frozen historical boundary

```text
history_date_min = 2017-01-03
history_date_max = 2026-05-29
same_contract_future_data_refresh_allowed = false
backfilled_history_role = historical_design_only
```

不得因本地数据在 implementation 时已更新到更晚日期而扩大 `20B_SRC_v0`。若需要使用 2026-05-29 之后数据，必须新建
contract version，并把 freeze 之后真实形成的 cohort 与 historical backfill 分开。

### 5.2 Trading calendar

`TRADING_CALENDAR_FILE` 是唯一 exchange-session authority。必须：

- `trade_date` 唯一、严格递增；
- 与 CSI300 dates 对账；
- 不用自然日替代 exchange-session offset；
- 所有 5D/10D 均表示 5/10 个未来 exchange sessions，不表示 7/14 个 calendar days。

### 5.3 U_project daily timing

Weekly decision `t` 在该周最后一个 exchange session 收盘形成，下一 exchange session 为 `entry_date(t)`。Decision denominator
使用：

```text
PROJECT_UNIVERSE_FILE rows where usable_trade_date = entry_date(t)
membership_available_time <= decision_date(t) close
available_time <= decision_date(t) close
```

这使 universe 与 next-session 可用池一致，但本 requirement 仍只计算 close-to-close design labels，不声称实际成交。

必须验证：

```text
key = (usable_trade_date, instrument)
duplicate key = fail
usable_trade_date > source_membership_date
membership_available_time <= decision close
total_market_cap_cny is finite and > 0 when used for VW
```

本地 availability fields 的冻结 parser 只接受 `YYYY-MM-DD close`；其 date component 必须是 exchange session，且
`available_date <= decision_date` 即视为不晚于 decision close。同日 close 允许；任何其他 token/time、unparseable value 或未来 date
均使该 denominator row timing-invalid，不得用字符串 lexical comparison 猜测。

不得用 label-end 仍在 universe、未来 membership/status、未来 market cap 或完整样本存活条件筛选 denominator。

### 5.4 Provider-qfq daily mark

股票与 benchmark return 都使用 simple close-to-close return：

```text
r_i,d = marked_qfq_close(i,d) / marked_qfq_close(i,prev_session(d)) - 1
r_m,d = CSI300_close(d) / CSI300_close(prev_session(d)) - 1
```

`r_i,d` 只能标为 `provider_qfq_price_return_proxy`，不是 exact total return。禁止 log-return 与 simple-return 混用。

股票日度 mark resolution：

```text
valid_qfq_mark:
    use observed qfq close.

confirmed_delisting_terminal:
    observed valid qfq mark always wins on that session;
    otherwise, when security master has is_delisted=true, finite delist_date <= current exchange session,
    the previous resolved mark is finite and terminal has not yet been applied, set current resolved mark to zero
    and daily return to -1 once;
    later dates are post_terminal_not_eligible, not repeated -1.

unknown_data_gap_or_corporate_action_bridge:
    daily return missing; never silently carry, zero-fill or interpolate.
```

Tradability 语义冻结为：

```text
tradability_assumption = all_registered_denominator_rows_tradable
daily_suspension_lookup = prohibited
daily_suspension_inference_from_missing_bar = prohibited
suspension_carry = prohibited
missing_qfq_mark = unknown_data_gap
```

因此 `SECURITY_MASTER_FILE` 只用于 canonical identity、listing date 与 confirmed delisting terminal lineage，不要求或伪造逐日
suspension 字段。`U_project` 已冻结的 denominator row 不因停牌状态二次筛除；但假设可交易不等于假设价格存在，缺失 qfq mark
仍使相关 feature/outcome fail closed。该简化必须在所有 decision/report 中标为 `optimistic_tradability_assumption=true`。

`daily_return_resolution_gate=pass` 当且仅当所有 rows 使用上述四态枚举、没有 suspension lookup/inference/carry、terminal -1 不重复，
且 unknown qfq gap 没有贡献给 feature。任何按 missing bar 推断 suspension 或 carry return=0 都必须 fail。

`delist_date` 先映射为 `first exchange session S[d] where S[d] >= delist_date`。若该 session 仍存在 finite observed qfq mark，
该 mark 仍按 `valid_qfq_mark` 处理，terminal 延后到其后第一个无 valid mark 的 exchange session；不得覆盖 observed mark。Terminal
状态在同一 instrument 的 daily mark path 中只施加一次。多个已在 terminal 前建立且 horizon 穿越 terminal 的 forward labels 可以
各自得到 `-1`，这不是重复施加 daily terminal event。

形成期要求 exact L 个 finite residuals，因此 unknown formation day 会使对应 score missing。Regression estimation window 可排除
unknown paired days，但必须满足 Section 8 的 frozen pair floor。

### 5.5 Input inventory 与 hash

Preflight 必须生成：

```text
preoutcome/input_inventory.csv
preoutcome/input_schema_audit.csv
preoutcome/input_file_set_hashes.json
```

Required source columns 冻结为：

```text
PROJECT_UNIVERSE_FILE: usable_trade_date, instrument, source_membership_date,
    membership_available_time, available_time, total_market_cap_cny
QFQ csv: date, close, instrument, source_function, source_volume_unit, source_turnover_unit
BENCHMARK_FILE: date, close, index_alias, instrument, source_trade_date
TRADING_CALENDAR_FILE: trade_date
SECURITY_MASTER_FILE: instrument, listing_date, delist_date, is_delisted, metadata_source
```

Date columns 必须可按 strict ISO date 解析；close/cap 必须 numeric；identity/status fields 不得全空。Input schema audit 必须逐列记录
required/observed dtype 与 null count，不得依赖 pandas inference 后静默 coercion unknown strings 为 NaN。

QFQ root hash 必须绑定排序后的 relative path、file size 与 file SHA256；不得只 hash 目录 mtime 或文件数量。
Signal 与 outcome stage 在使用 raw inputs 前必须复算各自 registered file-set hash，并与 sealed preoutcome 值逐项相等；任一 file
新增、删除、size/hash 变化均视为 input drift，禁止继续。不能只比较 root aggregate 后隐藏具体 mismatch。

### 5.6 Canonical instrument mapping

```text
canonical_instrument_id = PROJECT_UNIVERSE_FILE.instrument
benchmark row = BENCHMARK_FILE where index_alias == csi300 and instrument == SH000300
```

QFQ mapping 不引用不存在的隐式 20A mapping artifact，而冻结为 exact identity contract：

```text
qfq_filename_stem = basename(relative_path, ".csv")
qfq_internal_instrument = the single unique non-null `instrument` value across every row in that file
qfq_filename_stem == qfq_internal_instrument
qfq_internal_instrument == canonical_instrument_id for every instrument used by U_project
SECURITY_MASTER_FILE.instrument joins canonical_instrument_id by exact equality when status lineage is required
one qfq file per canonical instrument; one canonical instrument per qfq file
```

禁止 substring/fuzzy join、仅检查首行 instrument 或从六位 code 猜 exchange。必须输出
`preoutcome/instrument_mapping_audit.csv`，记录 `relative_path, filename_stem, internal_instrument,
internal_instrument_unique_n, canonical_instrument_id, security_master_match_n, mapping_rule_id, source_sha256, status,
blocking_reason`；唯一 key 为 `relative_path`。任一 used instrument mismatch/duplicate/unmapped 必须使 mapping gate fail。

Decision denominator 只允许当周 U_project；rolling regression/formation 可以使用 instrument 进入 U_project 以前已经真实存在、
且在对应 session 因果可得的 qfq history。不得用未来 U_project membership 反向决定历史回归 row 是否保留。

Signal materialization instrument scope 冻结为 `U_ever = sorted unique PROJECT_UNIVERSE_FILE.instrument within frozen boundary`，不是
全部 4,597 个 qfq symbols。Daily stock return audit 对 `U_ever × every boundary exchange session` 物化显式 status row，另加 CSI300
benchmark rows；rolling-model/residual panels 对 `U_ever × residual-calendar-possible sessions` 物化显式 success/failure row。Prelisting、
unknown 与 post-terminal rows 不删除。QFQ root 中从未进入 U_ever 的文件仍进入 inventory/root hash/identity audit，但不生成 signal rows。

---

## 6. Weekly calendar、fold 与 stable keys

### 6.1 Decision calendar

```text
decision_frequency = weekly
week_definition = ISO week
scheduled_decision_date = last exchange-open session in each ISO week
signal_asof = scheduled_decision_date close
entry_date = next exchange-open session after scheduled_decision_date
decision exists only when entry_date <= history_date_max
```

Signal warm-up、universe availability 或 outcome completeness 不得改变 scheduled calendar；它们只能改变 row status。

### 6.2 Formation/holding session sets

对 decision session index `j`：

```text
formation_5d = sessions[j-4 : j] inclusive, exactly 5 sessions
formation_10d = sessions[j-9 : j] inclusive, exactly 10 sessions
holding_5d = sessions[j+1 : j+5] inclusive, exactly 5 sessions
holding_10d = sessions[j+1 : j+10] inclusive, exactly 10 sessions
```

Formation 不 skip 最近 1 天；本 family 研究的是 immediate residual continuation。不得事后改成 5-1、10-1、20-5 或其他
skip convention。

### 6.3 Frozen early/late fold

Preoutcome 只用 scheduled decision calendar 与以下固定 warm-up rule 构造 `calendar_signal_possible` weeks，不读取 outcome。
令 history boundary 内严格递增的 exchange sessions 为零基 `S[0..T-1]`，decision date 为 `S[j]`：

```text
daily return on S[d] requires d >= 1
residual on S[s] uses return dates S[s-252] ... S[s-1]
the earliest return S[s-252] requires close S[s-253]
residual_calendar_possible(S[s]) iff s >= 253
10D formation ending S[j] requires residuals S[j-9] ... S[j]
calendar_signal_possible(decision S[j]) iff j >= 262 and entry_date <= history_date_max
```

`calendar_signal_possible` 是纯 calendar readiness；不读取逐股价格、回归成功数、universe coverage 或 outcome completeness。
5D 形成期会更早可算，但为了同一 fold 同时支持完整注册 matrix，fold population 固定采用 10D residual arm 的最晚 warm-up，
即 `j >= 262`。
将这些 weeks 按日期排序，在中点切分：

```text
early = first floor(N_calendar_signal_possible / 2) weeks
late = remaining weeks
fold boundary is frozen in preoutcome/calendar_freeze.csv
missing signals/outcomes do not move the boundary
```

### 6.4 Stable keys

```text
daily mark key = (asset_role, instrument_id, session_date)
rolling regression key = (instrument_id, residual_date)
daily residual key = (instrument_id, residual_date, residual_model_id)
weekly signal key = (instrument_id, decision_date, arm_id)
bucket assignment key = (instrument_id, decision_date, arm_id, bucket_count)
forward label key = (instrument_id, decision_date, holding_sessions, return_semantics)
bucket return key = (decision_date, arm_id, formation_sessions, holding_sessions,
                     return_semantics, weighting, bucket_count, bucket_id)
summary key = (arm_id, formation_sessions, holding_sessions, return_semantics,
               weighting, bucket_count, series_role, fold_id)
```

任一 duplicate key 必须 fail closed。

---

## 7. Arm registry 与冻结 horizon matrix

### 7.1 Arms

| arm_id | score | role | favorable |
|---|---|---|---|
| `SRC0_ALL_ELIGIBLE_BASELINE` | no score | same-week U_project equal-weight baseline | all eligible |
| `SRC1_TOTAL_CONT_5D` | 5D standardized total-return continuation | mandatory comparator | high score |
| `SRC2_TOTAL_CONT_10D` | 10D standardized total-return continuation | mandatory comparator | high score |
| `SRC3_MKT_RESID_CONT_5D` | 5D standardized sequential market residual continuation | matched primary | high score |
| `SRC4_MKT_RESID_CONT_10D` | 10D standardized sequential market residual continuation | matched primary | high score |
| `SRC5_LOWVOL_20D_COMPARATOR` | trailing 20D realized volatility | scale/opportunity-cost comparator | low score |

禁止添加：

- 3D/15D/20D formation；
- beta-neutral、size-neutral、board-neutral 或 learned combination；
- 5D+10D ensemble；
- 事后只保留表现较好的 arm。

### 7.2 Complete matrix

每个 scored arm 必须同时输出 `holding_sessions in {5, 10}`。Primary mapping 冻结为：

```text
matched_primary_5x5 = SRC3_MKT_RESID_CONT_5D × H5
matched_primary_10x10 = SRC4_MKT_RESID_CONT_10D × H10
cross_decay_5x10 = SRC3_MKT_RESID_CONT_5D × H10, diagnostic only
cross_decay_10x5 = SRC4_MKT_RESID_CONT_10D × H5, diagnostic only
```

对应 total-return comparator：

```text
total_matched_5x5 = SRC1_TOTAL_CONT_5D × H5
total_matched_10x10 = SRC2_TOTAL_CONT_10D × H10
```

Low Vol 与 all-eligible baseline 同时输出 H5/H10，但永远不能单独使 residual family gate 通过。

Required preoutcome output：

```text
preoutcome/arm_and_horizon_registry.csv
```

最少字段：

```text
arm_id
family_id
formula_id
formation_sessions
holding_sessions
return_semantics
weighting
bucket_count
matrix_role
primary_gate_eligible
comparator_only
favorable_direction
claim_ceiling
```

Registry 唯一 key 为 `(arm_id, holding_sessions, return_semantics, weighting, bucket_count)`。每个 scored arm 展开
`holding={5,10} × semantics={project_conservative_close_to_close_proxy,qfq_complete_case_sensitivity} × weighting={EW,VW} ×
bucket_count={5,10}`；all-eligible baseline 只注册 `weighting=EW,bucket_count=0` 的 H5/H10 × 两种 semantics。`formula_id` 标识
signal formula，不因 holding/return semantics/weighting/bucket count 改变。Primary-gate eligible 只允许 matched holding + project
semantics + EW + decile 的两行。

因此 `arm_and_horizon_registry.csv` expected row count 固定为 `5*2*2*2*2 + 1*2*2*1*1 = 84`；formula registry expected
row count 固定为 6。任一缺失、额外或重复 row 使 `arm_grid_completeness_gate=fail`。

所有 registered rows 必须在 outcome bundle 中出现，即使 `not_evaluable`。

---

## 8. Frozen formulas

### 8.1 Sequential daily market model

对每只股票 `i`、每个需要形成 residual 的 session `s`，只使用 `s` 之前的 252 个 exchange sessions 作为 calendar
estimation window：

```text
estimation_calendar_sessions = s-252, ..., s-1 exactly 252 scheduled sessions
paired rows = sessions where stock return and CSI300 return are both finite
minimum_paired_observation = 200
minimum_paired_coverage = 200 / 252
r_i,u = alpha_i,s + beta_i,s * r_m,u + error_i,u
fit_intercept = true
numeric_dtype = float64
predictor_order = intercept, CSI300_daily_simple_return
estimator = numpy.linalg.lstsq(X, y, rcond=1e-12)
sample_weight = none
winsorization = none
required_design_rank = 2
```

`252 sessions / 200 paired rows` 是本项目为新日频 adaptation 冻结的一年 beta 稳定性 heuristic，不来自 12-1 residual-
momentum 论文，也不允许在 outcome 后与 60/120/756-session window 比较择优。

若 paired N < 200、rank != 2、beta/nonfinite 或 benchmark window 不完整，则该 `i,s` residual missing；不得缩短 window、
前向填充 beta、使用 full-sample beta 或换 benchmark。
`benchmark window 不完整` 精确定义为 252 个 estimation sessions 中任一 CSI300 return missing；stock return 可以 missing 并从 paired
rows 排除，但仍须 paired N>=200。计算当日 residual 时 `r_i,s` 与 `r_m,s` 两者都必须 finite。

用只截至 `s-1` 的系数计算 session `s` residual：

```text
e_SRC(i,s) = r_i,s - (alpha_i,s + beta_i,s * r_m,s)
regression_max_date < s
```

这是 `rolling_252d_sequential_market_residual_adaptation`，不是 CH-3、FF3 或 monthly R2 exact replication。

### 8.2 Residual continuation scores

对 decision `t` 与 `L in {5,10}`：

```text
formation_sessions_L = exact last L exchange sessions ending t
require exactly L finite e_SRC(i,s)
SRC_L_mean = mean(e_SRC(i,s))
SRC_L_std = sample_std(e_SRC(i,s), ddof=1)
SRC_L_score = SRC_L_mean / SRC_L_std
SRC_L_std <= 1e-12 or nonfinite -> signal missing
```

`SRC_L_score` 高表示预期未来收益高。禁止 compound residual、取 residual sum 后不标准化、rank-average 5D/10D 或改变
`ddof`。

### 8.3 Total-return continuation comparators

用完全相同的 formation dates 与标准化方式，仅把 residual 换为 stock simple return：

```text
TOT_L_mean = mean(r_i,s over exact L formation sessions)
TOT_L_std = sample_std(r_i,s, ddof=1)
TOT_L_score = TOT_L_mean / TOT_L_std
TOT_L_std <= 1e-12 or nonfinite -> signal missing
```

该 comparator 用于判断 residualization 是否有增量，不得换成累计 return 后声称 paired formula comparison。

### 8.4 Low Vol comparator

```text
VOL20(i,t) = sample_std(r_i,t-19...t, ddof=1)
minimum_observation = exactly 20 finite daily returns
lower VOL20 is favorable
```

不得扫描 VOL10/VOL60/VOL120 后择优。

### 8.5 Required formula audit

`signal/rolling_market_model_audit.csv.gz` 至少包含：

```text
instrument_id
residual_date
estimation_start_date
estimation_end_date
calendar_session_n
paired_observation_n
paired_coverage
design_rank
alpha
beta
rcond
fit_row_key_hash
max_input_date
status
failure_reason
```

`signal/weekly_signal_panel.parquet` 至少包含：

```text
instrument_id
decision_date
entry_date
arm_id
formation_sessions
feature_start_date
feature_end_date
feature_observation_n
raw_signal
signal_eligible
signal_missing_reason
universe_membership_available_time
max_date_read
max_contributing_date
future_rows_loaded
future_rows_contributed
feature_row_key_hash
```

Weekly signal panel 必须对每个 `scheduled decision with entry_date within boundary × registered denominator instrument × 5 scored arms`
物化一行，包括 missing signal；baseline 不进入 signal panel。Warm-up `calendar_signal_possible=false` rows 显式标记
`signal_missing_reason=calendar_warmup_not_ready`，不得删除。Assignment panel 再把每条 weekly scored-arm row 展开为
bucket_count=5/10 两行；warm-up rows 保留 denominator，但 rank/bucket/weights missing 且 status 明确。

---

## 9. Sorting、weighting 与 denominator contract

### 9.1 Bucket assignment

每个 `decision_date × arm_id` 独立形成：

```text
primary bucket_count = 10
secondary morphology bucket_count = 5
minimum_signal_eligible_n_for_decile = 100
minimum_bucket_n = 10
```

先按 raw signal ascending，再按 instrument_id ascending 打破 ties：

```text
rank = 1..N
bucket_k = 1 + floor((rank - 1) * k / N)
```

SRC/Total favorable 是最高分 bucket `k`；Low Vol favorable 是最低分 bucket `1`。不足 decile floor 时 decile
`not_evaluable`，不得用 quintile 替代 primary。

Bucket assignment 只能使用 signal-eligible rows，不能按 future outcome completeness 重排或重新分桶。所有 denominator rows
都必须保留，记录未入桶原因。

### 9.2 Weighting

固定并行输出：

```text
EW = equal target weight within bucket
VW = PIT total_market_cap_cny from U_project entry-date row, known by decision close
```

EW 对所有 bucket-assigned rows 归一到 1。VW 只在 cap finite 且 `>0` 的 bucket rows 内按 cap 归一到 1；缺 cap row 显式
`vw_eligible=false`，不得回填或切 EW。VW retained N < 10 时该 bucket-week VW 不可评价。Primary gate 只用 EW；VW 是
capacity/size morphology diagnostic，必须单独报告 denominator、retained N 与 retention rate。

### 9.3 All-eligible baseline

`SRC0_ALL_ELIGIBLE_BASELINE` 使用同一 decision denominator、同一 outcome resolution 与 EW。它没有 bucket，不进入
signal morphology gate，只提供绝对市场环境与 paired opportunity-cost readout。Schema sentinel 冻结为：

```text
formation_sessions = 0
weighting = EW
bucket_count = 0
bucket_id = ALL
series_role = all_eligible_baseline
```

不得复制成 VW baseline 或把 `bucket_count=0` 混入 bucket exact-count tests。

### 9.4 Required assignment evidence

`signal/weekly_bucket_assignment.parquet` 每个 denominator row × registered scored arm × bucket_count 物化一行，至少包含：

```text
instrument_id
decision_date
entry_date
arm_id
formation_sessions
bucket_count
denominator_eligible
signal_eligible
raw_signal
rank
bucket_id
favorable_bucket
ew_target_weight
vw_target_weight
total_market_cap_cny
assignment_status
assignment_reason
```

同一 `instrument/decision/arm` 的 raw signal 在 bucket_count=5/10 rows 必须逐字节一致。

---

## 10. Forward label 与 portfolio-return contract

### 10.1 Primary return semantics

Primary 只使用：

```text
return_semantics = project_conservative_close_to_close_proxy
signal_mark = resolved qfq close on decision_date
label_end_H = H-th exchange session strictly after decision_date
forward_return_H = resolved_mark(label_end_H) / resolved_mark(decision_date) - 1
H in {5,10}
```

这是 provider-qfq close-to-close gross design proxy。不得称 next-open executable return。

### 10.2 Outcome resolution

对每个 `instrument × decision × H`：

```text
valid_marks:
    use qfq mark ratio.

confirmed_delisting_minus_one:
    if signal mark is finite, label-end observed mark is absent, security master has is_delisted=true and
    delist_date <= label_end_H, terminal position value is zero and forward return is -1;
    an observed finite label-end qfq mark wins over synthetic terminal resolution.

unknown_data_gap:
    instrument outcome unresolved.

right_censored:
    label_end beyond history_date_max or required future session absent.
```

Outcome stage 同样不读取或推断逐日停牌。Registered denominator rows 一律采用
`all_registered_denominator_rows_tradable` 假设；缺失 signal/end qfq mark 仍是 `unknown_data_gap`，不得 carry 或插值。
`confirmed_delisting_minus_one` 必须由 sealed daily terminal lineage 或上述 exact security-master rule 复算一致；不得仅因 qfq 文件停止
就推断退市。若 `label_end_H > history_date_max`，先判 `right_censored`，不得以未来已知 delist metadata 绕过 frozen boundary。

`project_conservative_close_to_close_proxy` bucket rule：任何 positive target-weight row 为 unknown/right-censored，则整个
`decision × arm × H × weighting × bucket` 不可评价；不得对 complete rows renormalize。

必须并行输出 `qfq_complete_case_sensitivity`：只允许 complete rows 后显式 renormalize，且不能进入任何 gate。两条
return semantics 都必须注册在 `preoutcome/arm_and_horizon_registry.csv` 并完整物化，不得按结果省略 sensitivity。

### 10.3 Bucket returns 与 spreads

```text
bucket_return = sum(ex_ante_target_weight * resolved_forward_return)
favorable_minus_unfavorable = favorable extreme - unfavorable extreme
favorable_minus_middle = favorable extreme - mean(middle bucket(s))
middle buckets for k=5 = bucket 3
middle buckets for k=10 = equal-weight mean of bucket 5 and bucket 6 returns
```

`historical/bucket_return_panel.csv.gz` 的 `series_role/bucket_id` 枚举冻结为：

```text
physical bucket row: series_role=bucket, bucket_id in 1..k
favorable derived row: series_role=favorable_bucket, bucket_id=FAVORABLE
unfavorable derived row: series_role=unfavorable_bucket, bucket_id=UNFAVORABLE
middle derived row: series_role=middle_bucket_mean, bucket_id=MIDDLE
spread derived row: series_role=favorable_minus_unfavorable, bucket_id=F_MINUS_U
middle spread row: series_role=favorable_minus_middle, bucket_id=F_MINUS_M
all-eligible row: series_role=all_eligible_baseline, bucket_id=ALL, bucket_count=0
```

Derived rows 的 registered/signal/bucket/outcome counts 继承其组成 rows 的可评价状态；不适用的单一 count 使用 null，不得伪造相加。
`arm_summary_statistics.csv`、stability、dominance 与 inference 只允许上述非-`bucket` derived roles；paired attribution 固定在同一
row 同时保存 favorable 与 spread metrics，不使用 `series_role`。Primary gate 明确使用 `series_role=favorable_bucket`，sort gate
使用 `series_role=favorable_minus_unfavorable`。所有 enum/sentinel 区分大小写，
不得另造 `spread/top/bottom` 别名。

Bucket-return panel 对每个 scheduled decision 与 84 registry rows 完整展开：`bucket_count=k>0` 时恰有 `k` physical bucket rows + 5
derived rows；baseline row 恰有 `ALL` 一行。Warm-up、signal failure、right-censor 与 whole-bucket unknown 都保留相同行，只改变
`evaluable/not_evaluable_reason/gross_return`。`arm_grid_completeness_gate` 按此 expected Cartesian count 校验，不能只发布有收益值的 rows。

Primary positive-beta 判断使用 favorable bucket 绝对 gross return。Spread 只判断 cross-sectional morphology。

必须另外输出但不进入 gate：

```text
raw_stock_spearman = Spearman(raw_signal, resolved_forward_return)
    on same-week signal-eligible rows with finite complete-case outcome only

aligned_bucket_spearman = Spearman(bucket_id, bucket_return)
    multiply by -1 for Low Vol so positive always means favorable-direction monotonicity
```

Raw stock Spearman 的 denominator 与 project whole-bucket return 不同，必须显式标为 complete-case diagnostic；不得用它替代
project positive-exposure 或 spread gate。所有 Spearman 使用 Section 11.4 的 average-midrank Pearson convention，finite paired
`n<3` 或任一 rank vector constant 时 missing。

### 10.4 Path decomposition

同一 sealed outcomes 必须生成：

```text
R_1_5 = return from decision close through session +5
R_1_10 = return from decision close through session +10
R_6_10 = (1 + R_1_10) / (1 + R_1_5) - 1
```

`R_6_10` 只在 H5 与 H10 均可评价时计算。不得把 `R_1_5 + R_6_10` 当作简单加法复原 H10。
三者先用同一 decision-date ex-ante bucket weights 聚合得到 cohort portfolio values：`V5=sum(w_i*(1+R_i,1_5))`、
`V10=sum(w_i*(1+R_i,1_10))`，再令 `R_1_5=V5-1`、`R_1_10=V10-1`、`R_6_10=V10/V5-1`；不得先算
instrument-level `R_i,6_10` 后用原始 weights 求均值。

### 10.5 Overlap semantics

H10 labels 在相邻 weekly decisions 间重叠。每行仍是 formation-cohort endpoint return：

- 不做跨 cohort 1/H capital allocation；
- 不声称 continuous NAV；
- 不把重叠 weekly rows当作独立 observation；
- inference 必须使用 Section 11 的 HAC/block rules。

若未来需要 continuously invested weekly sleeve，必须新建 executable bridge requirement。

---

## 11. Statistics、paired attribution 与 fragility

### 11.1 Required summary statistics

每个 `arm × formation × holding × weighting × bucket/series × fold` 至少输出：

```text
registered_decision_week_n
signal_ready_week_n
project_evaluable_week_n
distinct_calendar_month_n
distinct_calendar_year_n
mean_return
median_return
annualized_arithmetic_mean = mean_return * (252 / holding_sessions)
annualized_volatility = sample_std * sqrt(252 / holding_sessions)
diagnostic_sharpe = annualized_arithmetic_mean / annualized_volatility
positive_rate
p10
ES10_loss
worst_single_cohort_return
nominal_hac_ci_low/high
nominal_hac_pvalue
block_bootstrap_ci_low/high
block_bootstrap_pvalue
```

对按 `decision_date` 升序排列的 finite cohort returns `x`，冻结：

```text
n = len(x)
mean_return = numpy.mean(x)
median_return = numpy.median(x)
unannualized_horizon_volatility = numpy.std(x, ddof=1), only when n >= 2
positive_rate = mean(x > 0); zero return is not positive
p10 = numpy.quantile(x, 0.10, method="linear")
tail_n = max(1, ceil(0.10 * n))
ES10_loss = -mean(sort(x ascending)[0:tail_n])
worst_single_cohort_return = min(x)
```

`ES10_loss` 使用固定 worst-`ceil(10%N)` order-statistic tail，不使用 `mean(x <= q10)` 的布尔均值，也不因 q10 ties 扩大 tail。
`n=0` 时所有 return statistics missing；`n=1` 时 volatility/Sharpe/inference missing。所有 missing 必须以 status/reason 表示，不能
用 0 代替。

年化值只作可比 readout；overlapping cohort 与非 stateful endpoint returns 使其不能解释为策略 CAGR/Sharpe。

### 11.2 HAC 与 block bootstrap

```text
HAC estimator = Newey-West/Bartlett
hac_lag_weeks = 4 for every registered weekly series
bootstrap = moving calendar-week block bootstrap
block_length_weeks = 13
bootstrap_repetitions = 5000
bootstrap_seed = 20020
```

两类 inference 的 estimand 都是 weekly cohort mean，null=`mean_return=0`，alternative=`two_sided`。每个 scope 先 reindex 到
preoutcome frozen weekly decision calendar；missing cohort 保持 missing，不能压缩 calendar 后把跨 gap rows 当相邻。

HAC 精确公式：令 `T` 为 scope calendar slots、`I_t=1` 表示 `x_t` finite、`n=sum(I_t)`、`mu=sum(I_t*x_t)/n`、
`L=min(4,T-1)`。对 `h=0..L`：

```text
gamma_h = sum_{t=h..T-1, I_t=I_(t-h)=1} ((x_t-mu)*(x_(t-h)-mu)) / n
long_run_variance = gamma_0 + 2 * sum_{h=1..L} (1 - h/(L+1)) * gamma_h
variance_of_mean = long_run_variance / n
standard_error = sqrt(variance_of_mean)
z = mu / standard_error
two_sided_pvalue = 2 * (1 - NormalCDF(abs(z)))
nominal_95pct_CI = mu +/- 1.959963984540054 * standard_error
```

`NormalCDF` 固定为 `scipy.stats.norm.cdf` 的 float64 result。

`n<2`、variance nonfinite 或 `<=0` 时 inference missing/fail-reason，不得返回显著。Moving-block bootstrap 使用同一 frozen
calendar slots、non-circular contiguous blocks、block length `min(13,T)`；每次从合法 start index 均匀有放回抽 blocks，拼接后截断到
T。每个 scope 独立使用 `scope_seed = 20020 + {FULL:0, EARLY:1, LATE:2}[fold_id]` 与
`numpy.random.Generator(numpy.random.PCG64(scope_seed))`；同一 `fold_id/T` 的 5000 条 sampled calendar-index paths 在所有 series
间共享。每个 replicate 对抽中的 finite values 求 mean；无 finite value则该 replicate missing。CI 使用 finite replicate
means 的 `numpy.quantile([0.025,0.975], method="linear")`；two-sided centered p-value 为
`(1 + count(abs(boot_mean - mu) >= abs(mu))) / (finite_repetition_n + 1)`。Finite repetitions `<4500` 时 bootstrap status fail。

Inference table 为每个 registered test 分别物化 `estimator=newey_west_bartlett` 与
`estimator=moving_calendar_week_block_bootstrap` 两行；不得把两类 CI 混在同一含义不明的 row。

H5/H10 matched-primary 的 HAC nominal two-sided p-values 使用 Holm step-down correction，先按 `(pvalue, test_id)` ascending
稳定排序，`adjusted_p_(i)=max_{j<=i}(min(1,(m-j+1)*p_(j)))`，再映回原 test，family size `m=2`、`alpha=0.05`。显著性只作 diagnostic，
不进入 positive-exposure sign gate，也不允许把未显著写成无效或把显著写成 support。Holm family 只包含两条 matched-primary
EW-decile favorable-mean tests；cross mappings、spread、VW、quintile 与 comparator p-values 不得混入或替换这两个 tests。

`test_id` 冻结为
`MEAN::<arm_id>::F<formation_sessions>::H<holding_sessions>::<return_semantics>::<weighting>::K<bucket_count>::<series_role>::<fold_id>`。
每个 arm-summary registered series/fold 都产生两种 estimator rows；Holm family id 固定
`HOLM_MATCHED_PRIMARY_EW_DECILE_FAVORABLE_FULL`，只包含两条 `fold_id=FULL` 的 SRC3-H5 与 SRC4-H10 HAC rows。非 Holm rows 的
`holm_family_id/size/adjusted_pvalue` 为 null。

### 11.3 Paired residualization attribution

配对必须按相同 `decision_date × formation_sessions × holding_sessions × return_semantics × weighting × bucket_count`：

```text
SRC3_MKT_RESID_CONT_5D vs SRC1_TOTAL_CONT_5D
SRC4_MKT_RESID_CONT_10D vs SRC2_TOTAL_CONT_10D
```

只在双方同一 key 可评价时计算：

```text
paired_favorable_delta = SRC favorable return - Total favorable return
paired_spread_delta = SRC spread - Total spread
paired_volatility_delta = sample_std(SRC paired-week favorable series) - sample_std(Total paired-week favorable series)
paired_ES10_loss_delta = ES10_loss(SRC paired-week favorable series) - ES10_loss(Total paired-week favorable series)
```

禁止用两条 unpaired arm means 的差替代 paired delta。
`registered_pair_week_n` 等于对应 fold 的 `calendar_signal_possible` weeks；`paired_evaluable_week_n` 只计 residual/total 两臂在同一
week 的 favorable 与 favorable-minus-unfavorable rows 全部 project-evaluable。Paired favorable/spread means、volatility 与 ES
全部只用这一个共同 paired week set，不能为每个 metric 使用不同 N。

### 11.4 Style/morphology attribution

每个 decision week 输出：

```text
Spearman(SRC score, total-continuation score)
Spearman(SRC score, -VOL20)
Spearman(SRC score, log(total_market_cap_cny))
top-decile Jaccard(SRC, Total)
top-decile Jaccard(SRC, LowVol favorable)
favorable bucket weighted mean rolling beta
```

所有 score correlation/Jaccard 只在同一 decision week、双方均 signal-eligible 的 common instrument population 上计算；
不得用各自全体 population 的两个 summary 代替 row-level paired attribution。

精确复现口径：

```text
Spearman = Pearson correlation of each score's average midranks on the finite common population
minimum common population n = 3; either rank vector constant -> missing
Jaccard common population minimum n = 100
for Jaccard, rerank both raw scores independently inside the same common population using Section 9.1
top decile = bucket_id 10 for SRC/Total; LowVol favorable = bucket_id 1
Jaccard = intersection_n / union_n; empty union -> missing
weekly median = numpy.median over finite weekly statistics only
```

Jaccard 的 common-population rerank 只用于 style attribution，不回写 sealed primary bucket assignment。`favorable bucket weighted
mean rolling beta` 固定使用该 SRC arm 已 sealed 的 EW decile favorable assignment，以及 decision-date residual model 的
`beta_i,t`；只在 finite beta rows 上按原 EW target weights renormalize。若任一 positive target-weight row beta missing，则该 weekly
beta attribution missing，不得 complete-case 美化。

预注册 warning，不是硬淘汰门：

```text
SRC_5D_scale_dependence_warning =
    abs(median weekly Spearman(SRC3_MKT_RESID_CONT_5D, -VOL20)) >= 0.70
    or median weekly top-decile Jaccard(SRC3_MKT_RESID_CONT_5D, LowVol favorable) >= 0.60

SRC_10D_scale_dependence_warning =
    abs(median weekly Spearman(SRC4_MKT_RESID_CONT_10D, -VOL20)) >= 0.70
    or median weekly top-decile Jaccard(SRC4_MKT_RESID_CONT_10D, LowVol favorable) >= 0.60

SRC_5D_size_dependence_warning =
    abs(median weekly Spearman(SRC3_MKT_RESID_CONT_5D, log_market_cap)) >= 0.70

SRC_10D_size_dependence_warning =
    abs(median weekly Spearman(SRC4_MKT_RESID_CONT_10D, log_market_cap)) >= 0.70

scale_dependence_warning = SRC_5D_scale_dependence_warning or SRC_10D_scale_dependence_warning
size_dependence_warning = SRC_5D_size_dependence_warning or SRC_10D_size_dependence_warning
```

每个 arm 的 full-history weekly median 必须只用该 arm 与 comparator 同周共同 signal-eligible 的 instrument population；不得把
5D 与 10D rows 混池后计算一个 median。Overall warning 仅是两个 per-arm warning 的布尔 OR。这些阈值是 preoutcome
morphology heuristic，不能称经济或统计显著性阈值。

每个 correlation/Jaccard warning component 独立要求至少 52 个 finite weekly statistics；不足时该 component=`not_evaluable`，不是
false。Arm-level 与 overall OR 均按三态聚合：任一 component/arm=true 则 true；全部为 false 则 false；其余为
`not_evaluable`。Warning 不进入 terminal positive gate，但其 evaluability 必须进入 report/decision modifiers。

### 11.5 Dominance 与 stability

Primary matched series 必须输出：

- full/early/late；
- leave-one-decision-week-out mean min/max；
- leave-one-calendar-month-out mean min/max；
- leave-one-instrument-out spread range；
- 最大单周绝对贡献占总绝对贡献比例；
- top-3 weeks contribution；
- 各 calendar year mean 与 evaluable N；
- H5/H10 return correlation 与 nested-path decomposition。

LOIO 使用 sealed bucket assignment：删除目标 instrument 后只在原 bucket 内按原 target weights 等比例 renormalize，不重新排序、
不移动其他 instrument bucket。LOMO 删除该 calendar month 的所有 decision weeks 后重算 summary；不得把每周分别删除后冒充
leave-one-month-out。

LODO/LOMO/LOIO 均固定在 base full-fold project-evaluable week set 上，不得因删除 observation 而引入原先不可评价 week。令 favorable
weekly series 为 `x_t`：`maximum_single_week_absolute_contribution_share=max(abs(x_t))/sum(abs(x_t))`，
`top3_week_absolute_contribution_share=sum(largest 3 abs(x_t))/sum(abs(x_t))`；denominator `<=0` 时 missing。LOIO spread 对每个曾进入
sealed favorable 或 unfavorable bucket 的 instrument，跨全部 base weeks 删除后重算 weekly spread mean，再报告这些 instrument-level
means 的 min/max。

H5/H10 correlation 固定按同一 arm、EW decile favorable、project primary semantics、full fold 且 H5/H10 joint-evaluable decision weeks
计算 Pearson correlation；SRC3 与 SRC4 各输出一行，不把两种 formation arm 混在一起。`n<3` 或任一 series constant 时 missing。

### 11.6 Turnover 与 break-even cost proxy

Preflight 必须从 sealed 20A v2 cost artifacts 复核并冻结：

```text
commission_buy_bps = 2.5
commission_sell_bps = 2.5
minimum_commission_cny = 5.0
source_stamp_tax_sell_bps_by_effective_date = 2023-08-28:5.0
stamp_tax_proxy_bps_for_every_historical_transition = 5.0
stamp_tax_proxy_mode = current_5bps_applied_uniformly_to_history
slippage_buy_bps = 5.0
slippage_sell_bps = 5.0
transfer_fee_buy_bps = matched verified effective-date row
transfer_fee_sell_bps = matched verified effective-date row
break_even_one_way_cost_multiple_floor = 1.25
```

20A/EP19 的 stamp-tax freeze 只为 `2023-08-28:5.0`，没有覆盖本研究 2017-2023 的完整历史税率；本 requirement 不得自行补一套
未注册历史税表。为保持 proxy 可机械实现，5 bps current-vintage sell stamp tax 统一应用于所有 historical transitions，并标记
`historical_stamp_tax_schedule_replication=false`。Transfer fee 则使用 20A verified effective-date rows。任一值或 sealed source hash 与
20A authority 不一致，`frozen_cost_source_integrity_gate=fail` 且 `upstream_integrity_gate=fail`。只有 source hashes 全部匹配后才
评价字段/公式；任一 inherited value、effective-date coverage 或 formula 不一致使 `frozen_cost_contract_gate=fail`。本阶段没有
reference AUM，因此不能机械应用 5 CNY minimum commission；
cost proxy 明确采用 `minimum_commission_included=false`。统一 5 bps stamp tax、忽略 minimum commission 均使早期历史成本偏乐观，
必须报告。
`preoutcome/frozen_cost_contract_audit.csv` 至少包含
`source_artifact, source_sha256, cost_field, effective_start_date, expected_value, observed_value, inherited_value, status,
blocking_reason`，唯一 key 为 `(source_artifact, cost_field, effective_start_date)`。

对 favorable bucket 的相邻 weekly target weights，使用 union instrument set：

```text
cost_transition_scope C_H = later decision weeks t where:
    t and its immediately previous scheduled decision week t-1 both have sealed favorable target weights;
    no scheduled week lies between them;
    the project-primary favorable gross return for t at holding H is evaluable.
target_turnover_t = 0.5 * sum_i(abs(w_i,t - w_i,t-1))
valid_transition_n = len(C_H)
mean_target_turnover = mean(target_turnover_t over t in C_H)
mean_gross_return = mean(favorable_gross_return_t over the same t in C_H)
break_even_one_way_cost_bps = mean_gross_return / (2 * mean_target_turnover) * 10000

frozen_round_trip_cost_bps_t =
    commission_buy_bps + slippage_buy_bps + transfer_fee_buy_bps_t
    + commission_sell_bps + slippage_sell_bps + stamp_tax_proxy_bps(=5.0) + transfer_fee_sell_bps_t
frozen_one_way_equivalent_cost_bps_t = frozen_round_trip_cost_bps_t / 2
turnover_weighted_frozen_one_way_cost_bps =
    sum_t(target_turnover_t * frozen_one_way_equivalent_cost_bps_t) / sum_t(target_turnover_t)
break_even_cost_multiple_proxy =
    break_even_one_way_cost_bps / turnover_weighted_frozen_one_way_cost_bps
cost_feasible = finite break_even_cost_multiple_proxy >= 1.25
```

每个 `arm × formation × holding × weighting × bucket` 单独计算；只使用两个相邻 scheduled decision weeks 都有 sealed target
weights 且 later-week return evaluable 的同一 `C_H`；不得让 mean return 与 mean turnover 使用不同 week population，不跨 missing
scheduled week 连接。`valid_transition_n=0` 或 `mean_target_turnover <= 0` 时 break-even missing。

Transfer-fee schedule 使用 transition 的 later decision date 对应 effective-date row；stamp-tax proxy 始终为 5 bps。
对每个 transition date，20A registry 中所有覆盖该日期且 `human_verified=true` 的 rows，其 buy bps 与 sell bps 各自必须只有一个
unique finite value；否则 `frozen_cost_contract_gate=fail`。本 proxy 不按 instrument/board 选择 price-limit row。
`sum(target_turnover_t) <= 0`、gross mean `<=0`、
cost denominator missing/nonpositive 或 multiple nonfinite 时 `cost_feasible=false`，不得把 undefined 当 infinity。该值忽略 drift、
H10 cohort overlap、blocked fills、minimum commission 与冲击成本，只是筛查频繁换仓是否明显吞噬 gross edge；不得将其称
actual turnover、actual cost 或 net return。

---

## 12. Sample floors、gates 与 horizon interpretation

### 12.1 Sample-support gate

每个 matched primary 独立要求：

```text
full_project_evaluable_week_n >= 156
early_project_evaluable_week_n >= 78
late_project_evaluable_week_n >= 78
full_distinct_calendar_month_n >= 36
full_distinct_calendar_year_n >= 4
median_weekly_signal_coverage >= 0.70
minimum_weekly_signal_eligible_n >= 100
```

对每个 matched primary arm，sample metrics 的 denominator 冻结为该 fold 内全部 `calendar_signal_possible=true` weeks：

```text
registered_decision_week_n = number of calendar_signal_possible weeks in fold
registered_denominator_n_t = U_project rows at entry_date(t) satisfying Section 5.3 timing
signal_eligible_n_t = denominator rows with finite valid arm score
signal_coverage_t = signal_eligible_n_t / registered_denominator_n_t
    if registered_denominator_n_t <= 0: signal_coverage_t=0 and signal_eligible_n_t=0
signal_ready_week = signal_eligible_n_t >= 100 and every decile bucket has n >= 10
project_evaluable_week = primary EW-decile favorable project-return row is evaluable
median_weekly_signal_coverage = median(signal_coverage_t across every registered week in fold)
minimum_weekly_signal_eligible_n = min(signal_eligible_n_t across every registered week in fold)
distinct_calendar_month/year_n = distinct decision-date month/year among project_evaluable weeks
```

不得只在 signal-ready/evaluable weeks 上计算 coverage median/minimum，也不得删除 denominator=0 week。Full/early/late 使用同一
preoutcome fold membership；`full_project_evaluable_week_n` 是 full fold 的 project-evaluable count，early/late 同理。

机械映射：

```text
SRC_5x5_sample_support_gate =
    all seven floors above evaluated on SRC3_MKT_RESID_CONT_5D × H5

SRC_10x10_sample_support_gate =
    all seven floors above evaluated on SRC4_MKT_RESID_CONT_10D × H10

SRC_5x5_paired_attribution_support_gate =
    paired_evaluable_week_n(FULL/EARLY/LATE) >= 156/78/78 for SRC3 vs SRC1 × H5

SRC_10x10_paired_attribution_support_gate =
    paired_evaluable_week_n(FULL/EARLY/LATE) >= 156/78/78 for SRC4 vs SRC2 × H10
```

Paired support gates 固定使用 project primary semantics、EW、decile，并要求同一 week 的 residual/total favorable 与 spread rows
全部可评价；只满足其中一项不得计入 paired N。

这些是 historical design-readout floors，不把 weekly rows升级为独立 confirmatory evidence。任一 matched-primary 或 paired
attribution support 不足时状态必须
`underpowered`，不得重切 fold、放宽 missingness 或改 bucket。

### 12.2 Formula/materialization gate

```text
SRC_formula_integrity_gate =
    upstream_integrity_gate
    and preoutcome_manifest_hash_gate
    and input_schema_gate
    and instrument_mapping_gate
    and trading_calendar_gate
    and universe_timing_gate
    and stage_read_whitelist_gate
    and frozen_cost_contract_gate
    and daily_return_resolution_gate
    and rolling_regression_causality_gate
    and rolling_regression_rank_gate
    and formation_exactness_gate
    and arm_grid_completeness_gate
    and assignment_no_outcome_gate
    and signal_access_lineage_gate
    and signal_manifest_hash_gate

SRC_outcome_integrity_gate =
    historical_signal_execution_authorization_gate
    and historical_outcome_execution_authorization_gate
    and outcome_firewall_gate
    and outcome_access_scope_gate
    and label_horizon_exactness_gate
    and outcome_resolution_gate
    and assignment_signal_bundle_hash_match_gate
    and historical_manifest_hash_gate

SRC_5x5_registered_row_completeness_gate =
    every registered SRC3_MKT_RESID_CONT_5D x H5 assignment/outcome/bucket/summary row exists
    with a valid evaluable or not_evaluable status

SRC_10x10_registered_row_completeness_gate =
    every registered SRC4_MKT_RESID_CONT_10D x H10 assignment/outcome/bucket/summary row exists
    with a valid evaluable or not_evaluable status

SRC_5x5_materialization_gate =
    SRC_formula_integrity_gate
    and SRC_outcome_integrity_gate
    and SRC_5x5_registered_row_completeness_gate

SRC_10x10_materialization_gate =
    SRC_formula_integrity_gate
    and SRC_outcome_integrity_gate
    and SRC_10x10_registered_row_completeness_gate
```

`registered_row_completeness_gate` 只检查 registered key 全部物化（允许显式 `not_evaluable` row）、schema/key/integrity 与公式
状态，不包含任何 sample floor。这样 data/formula block 与 underpowered state 可以按 Section 13 顺序机械区分。

### 12.3 Positive-exposure gates

只使用 matched primary、EW decile favorable bucket、`project_conservative_close_to_close_proxy`：

```text
SRC_5x5_positive_exposure_design_gate =
    SRC_5x5_materialization_gate
    and SRC_5x5_sample_support_gate
    and favorable_mean_full_5x5 > 0
    and favorable_mean_early_5x5 > 0
    and favorable_mean_late_5x5 > 0

SRC_10x10_positive_exposure_design_gate =
    SRC_10x10_materialization_gate
    and SRC_10x10_sample_support_gate
    and favorable_mean_full_10x10 > 0
    and favorable_mean_early_10x10 > 0
    and favorable_mean_late_10x10 > 0
```

### 12.4 Sort-morphology gates

```text
SRC_5x5_sort_morphology_gate =
    SRC_5x5_materialization_gate
    and SRC_5x5_sample_support_gate
    and spread_mean_full_5x5 > 0
    and spread_mean_early_5x5 > 0
    and spread_mean_late_5x5 > 0

SRC_10x10_sort_morphology_gate =
    SRC_10x10_materialization_gate
    and SRC_10x10_sample_support_gate
    and spread_mean_full_10x10 > 0
    and spread_mean_early_10x10 > 0
    and spread_mean_late_10x10 > 0
```

Sort gate 不是 positive-exposure 必要门；只靠 unfavorable bucket 为负形成的 spread 不得提升 family。

### 12.5 Residualization-value classification

对 matched primary `H in {5,10}`，先冻结 materiality 与 non-degradation 阈值：

```text
minimum_paired_favorable_delta_H = H * 0.0001
paired_favorable_nondegradation_tolerance_H = -H * 0.00005
minimum_paired_spread_delta_H = H * 0.0001
maximum_paired_volatility_ratio = 0.95
maximum_paired_ES10_loss_ratio = 0.95

paired_volatility_ratio = sample_std(SRC paired favorable) / sample_std(Total paired favorable)
paired_ES10_loss_ratio = SRC paired ES10_loss / Total paired ES10_loss
```

比率仅在 numerator finite 且 comparator denominator finite、严格 `>0` 时可评价。`H * 0.0001` 表示每个 holding
session 至少 1 bp 的 full-fold paired 改善；non-degradation tolerance 表示 early/late 每个 session 最多容忍 0.5 bp 的 paired
favorable 恶化。它们是冻结的 design materiality heuristic，不是统计显著性阈值。

```text
SRC_5x5_residualization_value =
    SRC_5x5_paired_attribution_support_gate
    and paired_favorable_delta_early_5x5 >= -0.00025
    and paired_favorable_delta_late_5x5 >= -0.00025
    and (
        paired_favorable_delta_full_5x5 >= 0.0005
        or (paired_spread_delta_full_5x5 >= 0.0005
            and paired_favorable_delta_full_5x5 >= -0.00025)
        or (paired_volatility_ratio_full_5x5 <= 0.95
            and paired_favorable_delta_full_5x5 >= -0.00025)
        or (paired_ES10_loss_ratio_full_5x5 <= 0.95
            and paired_favorable_delta_full_5x5 >= -0.00025)
    )

SRC_10x10_residualization_value =
    SRC_10x10_paired_attribution_support_gate
    and paired_favorable_delta_early_10x10 >= -0.0005
    and paired_favorable_delta_late_10x10 >= -0.0005
    and (
        paired_favorable_delta_full_10x10 >= 0.0010
        or (paired_spread_delta_full_10x10 >= 0.0010
            and paired_favorable_delta_full_10x10 >= -0.0005)
        or (paired_volatility_ratio_full_10x10 <= 0.95
            and paired_favorable_delta_full_10x10 >= -0.0005)
        or (paired_ES10_loss_ratio_full_10x10 <= 0.95
            and paired_favorable_delta_full_10x10 >= -0.0005)
    )
```

Paired attribution table 分别物化 `fold_id=FULL/EARLY/LATE`。每行保存本 fold 的 paired metrics 与 thresholds；全局
`residualization_value/classification_reason` 只在 `fold_id=FULL` row 保存最终三态值与理由，EARLY/LATE rows 使用
`residualization_value=not_applicable`。FULL row 的分类必须显式读取同一 pair 的 EARLY/LATE favorable deltas；任一 required fold
metric missing 时全局值为 `not_evaluable`，不得按 false 继续通过 OR 分支。Decision gate 只有值严格为 true 时才视为有
residualization value。

这是用途分类，不是 alpha gate。若 positive exposure 成立但两条 residualization value 都为 false，结论必须写成
`short_term_total_continuation_explains_result_design_only`，不能声称 residualization 提供必要增量。

### 12.6 Cost-feasibility gates

只使用 matched primary、FULL fold、EW decile favorable bucket、project primary semantics 与 Section 11.6 proxy：

```text
SRC_5x5_cost_feasibility_gate =
    SRC_5x5_materialization_gate
    and frozen_cost_contract_gate
    and cost_feasible(SRC3_MKT_RESID_CONT_5D x H5) = true

SRC_10x10_cost_feasibility_gate =
    SRC_10x10_materialization_gate
    and frozen_cost_contract_gate
    and cost_feasible(SRC4_MKT_RESID_CONT_10D x H10) = true
```

这些是 gross design 的成本压力测试，不是 executable net-return gate。Persistent/delayed independent-sleeve 候选必须通过对应
cost gate；5D-only participation/meta-label 候选是对其他 policy 的输入，不要求把 SRC 自身作为独立 weekly sleeve 成交，但必须
披露其 5x5 cost gate 与 multiple，不得把未通过写成低成本信号。

### 12.7 Horizon interpretation truth table

| 5x5 positive | 10x10 positive | 允许的解释 |
|---|---|---|
| True | True | `persistent_short_horizon_residual_continuation_candidate_design_only` |
| True | False | `ultrashort_participation_or_entry_filter_candidate_design_only` |
| False | True | `delayed_short_horizon_realization_candidate_design_only` |
| False | False，任一 sort gate True | `short_horizon_sort_morphology_only_no_positive_beta` |
| False | False，sort gates 也 False | `short_term_residual_continuation_not_identified` |

若 5x5=True、10x10=False 且 `R_6_10 < 0`，报告必须明确讨论 fast decay/reversal；不得把 5D arm直接称独立 sleeve。

### 12.8 Forward recommendation 与 authorization

```text
short_term_true_forward_freeze_recommended =
    SRC_5x5_positive_exposure_design_gate
    and SRC_10x10_positive_exposure_design_gate
    and (SRC_5x5_residualization_value or SRC_10x10_residualization_value)
    and SRC_5x5_cost_feasibility_gate
    and SRC_10x10_cost_feasibility_gate
    and outcome_firewall_gate
    and preoutcome_manifest_hash_gate
    and signal_manifest_hash_gate
    and historical_manifest_hash_gate

participation_meta_label_research_recommended =
    SRC_5x5_positive_exposure_design_gate
    and not SRC_10x10_positive_exposure_design_gate
    and SRC_5x5_residualization_value
```

无论 recommendation 为何：

```text
next_requirement_generation_authorized = false
true_forward_execution_authorized = false
20C_requirement_generation_authorized = false
20C_execution_authorized = false
```

用户必须另行评审并明确授权新的 forward/executable requirement。

---

## 13. Terminal decision state machine

固定优先级：

```text
1. 20B_SRC_outcome_firewall_violated
2. 20B_SRC_upstream_integrity_blocked
3. 20B_SRC_historical_run_not_authorized
4. 20B_SRC_manifest_or_hash_blocked
5. 20B_SRC_data_or_formula_materialization_blocked
6. 20B_SRC_underpowered_design_diagnostic
7. 20B_SRC_gross_direction_but_cost_infeasible_design_only
8. 20B_SRC_persistent_short_horizon_candidate_design_only
9. 20B_SRC_ultrashort_participation_filter_candidate_design_only
10. 20B_SRC_delayed_short_horizon_candidate_design_only
11. 20B_SRC_sort_morphology_only_design_only
12. 20B_SRC_total_continuation_explained_design_only
13. 20B_SRC_not_identified_design_only
```

判定顺序：

```text
if firewall fail -> state 1
elif upstream fail -> state 2
elif signal run authorization absent -> state 3
elif signal run authorized and any required preoutcome/signal manifest or hash fails -> state 4
elif outcome run authorization absent -> state 3
elif outcome run authorized and any required historical manifest or hash fails -> state 4
elif formula/materialization blocked for any registered arm/horizon or comparator row -> state 5
elif any matched-primary sample support or paired-attribution support gate fails -> state 6
elif both positive gates pass:
    if neither residualization value -> state 12
    elif not (SRC_5x5_cost_feasibility_gate and SRC_10x10_cost_feasibility_gate) -> state 7
    else -> state 8
elif only 5x5 positive:
    if SRC_5x5_residualization_value -> state 9
    else -> state 12
elif only 10x10 positive:
    if not SRC_10x10_residualization_value -> state 12
    elif not SRC_10x10_cost_feasibility_gate -> state 7
    else -> state 10
elif any sort morphology gate -> state 11
else -> state 13
```

这里 `fail` 只表示对应 audit 已物化并发现 affirmative violation；`not_run/not_evaluated/not_applicable` 不等于 fail。
尤其在尚未授权 signal run 时，缺少 signal firewall audit 不得伪装成已发生 firewall violation。

未获得 signal authorization 的初始 spec 状态必须是 `20B_SRC_historical_run_not_authorized`；不得因为尚未生成 signal/historical
manifest 而提前落入 manifest/hash blocked。只有某 stage 已获授权并按顺序应当存在时，缺失或错误的该 stage manifest/hash 才
优先判为 state 4。

若 scale/size warning 触发但 positive gates 同时通过，decision CSV 必须保留 primary terminal state，并另列
`scale_dependence_warning/size_dependence_warning`；不得只靠 warning 抹掉正向点估计，也不得隐去 warning。

---

## 14. Required artifacts 与 schema

### 14.0 Governance authorization inputs

```text
authorizations/signal_materialization_authorization.json
authorizations/outcome_materialization_authorization.json
```

这些文件位于 `BUILD_ROOT`，不是 runner 生成的研究结果；但必须保留原始 bytes，并把 file SHA256、semantic
`authorization_record_sha256` 与 bound bundle hash 写入对应 stage manifest。最终整包发布时两份记录随 bundle 一起保留。

### 14.1 Preoutcome bundle

```text
preoutcome/upstream_integrity_audit.csv
preoutcome/input_inventory.csv
preoutcome/input_schema_audit.csv
preoutcome/input_file_set_hashes.json
preoutcome/instrument_mapping_audit.csv
preoutcome/frozen_cost_contract_audit.csv
preoutcome/calendar_freeze.csv
preoutcome/arm_and_horizon_registry.csv
preoutcome/formula_registry.csv
preoutcome/sample_floor_and_gate_registry.csv
preoutcome/read_whitelist.json
preoutcome/preoutcome_manifest_20b_src.json
preoutcome/preoutcome_output_hashes_20b_src.json
```

### 14.2 Signal bundle

```text
signal/signal_access_audit.csv
signal/daily_return_resolution_audit.csv.gz
signal/rolling_market_model_audit.csv.gz
signal/daily_market_residual_panel.parquet
signal/weekly_signal_panel.parquet
signal/weekly_bucket_assignment.parquet
signal/signal_coverage_audit.csv
signal/signal_manifest_20b_src.json
signal/signal_output_hashes_20b_src.json
```

### 14.3 Historical outcome bundle

```text
historical/outcome_access_audit.csv
historical/forward_return_resolution.parquet
historical/bucket_return_panel.csv.gz
historical/arm_summary_statistics.csv
historical/horizon_path_decomposition.csv
historical/paired_residual_vs_total_attribution.csv
historical/style_morphology_attribution.csv
historical/fold_and_year_stability.csv
historical/month_instrument_dominance_audit.csv
historical/turnover_break_even_cost_readout.csv
historical/hac_and_block_bootstrap_inference.csv
historical/historical_manifest_20b_src.json
historical/historical_output_hashes_20b_src.json
```

### 14.4 Final bundle

```text
20B_SRC_short_term_residual_continuation_family_decision.csv
20B_SRC_short_term_residual_continuation_family_diagnostic_report.md
manifest_20b_src_short_term_residual_continuation_family_diagnostic.json
output_hashes_20b_src_short_term_residual_continuation_family_diagnostic.json
```

### 14.5 Decision CSV required fields

单行，至少包含：

```text
experiment_id
phase_id
run_id
contract_version
terminal_state
historical_sample_role
historical_support_claim_allowed
exact_replication_claim_allowed
tradability_assumption
daily_suspension_source_required
suspension_carry_allowed
optimistic_tradability_assumption
requirement_generation_authorized
implementation_authorized
historical_signal_execution_authorized
historical_outcome_execution_authorized
historical_signal_execution_authorization_gate
historical_outcome_execution_authorization_gate
upstream_integrity_gate
instrument_mapping_gate
stage_read_whitelist_gate
signal_access_lineage_gate
outcome_access_scope_gate
outcome_firewall_gate
preoutcome_manifest_hash_gate
signal_manifest_hash_gate
historical_manifest_hash_gate
SRC_formula_integrity_gate
SRC_outcome_integrity_gate
SRC_5x5_registered_row_completeness_gate
SRC_10x10_registered_row_completeness_gate
SRC_5x5_materialization_gate
SRC_10x10_materialization_gate
SRC_5x5_sample_support_gate
SRC_10x10_sample_support_gate
SRC_5x5_paired_attribution_support_gate
SRC_10x10_paired_attribution_support_gate
SRC_5x5_positive_exposure_design_gate
SRC_10x10_positive_exposure_design_gate
SRC_5x5_sort_morphology_gate
SRC_10x10_sort_morphology_gate
SRC_5x5_residualization_value
SRC_10x10_residualization_value
frozen_cost_contract_gate
frozen_cost_source_integrity_gate
stamp_tax_proxy_mode
historical_stamp_tax_schedule_replication
minimum_commission_included
SRC_5x5_cost_feasibility_gate
SRC_10x10_cost_feasibility_gate
SRC_5x5_break_even_cost_multiple_proxy
SRC_10x10_break_even_cost_multiple_proxy
SRC_5D_scale_dependence_warning
SRC_10D_scale_dependence_warning
SRC_5D_size_dependence_warning
SRC_10D_size_dependence_warning
scale_dependence_warning
size_dependence_warning
style_warning_evaluability
short_term_true_forward_freeze_recommended
participation_meta_label_research_recommended
next_requirement_generation_authorized
true_forward_execution_authorized
20C_requirement_generation_authorized
20C_execution_authorized
policy_training_authorized
policy_replay_authorized
portfolio_optimization_authorized
deployment_authorized
preoutcome_bundle_hash
signal_bundle_hash
historical_bundle_hash
blocking_reasons
interpretation_modifiers
```

Decision 中 `historical_*_execution_authorized` 只有对应 authorization gate pass 时为 true；存在文件但 hash/scope/binding fail 时必须为
false。`implementation_authorized` 记录实施动作的独立 human provenance，不得由 signal/outcome record 反推；本 requirement 当前值
仍为 false。所有 `*_authorized` 字段必须是严格 boolean，gate 字段使用 `pass/fail/not_evaluated` enum。
`blocking_reasons/interpretation_modifiers` 是按 ASCII ascending 去重后的 string arrays，并以 Section 16
`canonical_compact_json` 写入单个 CSV cell；空值固定为 `[]`，不得使用自由文本分隔符。

### 14.6 Bucket-return panel minimum fields

```text
decision_date
fold_id
calendar_year
arm_id
formation_sessions
holding_sessions
matrix_role
return_semantics
weighting
bucket_count
bucket_id
series_role
registered_denominator_n
signal_eligible_n
bucket_target_n
outcome_resolved_n
evaluable
not_evaluable_reason
gross_return
```

### 14.7 Summary table minimum fields

```text
arm_id
formation_sessions
holding_sessions
matrix_role
return_semantics
weighting
bucket_count
series_role
fold_id
registered_decision_week_n
signal_ready_week_n
project_evaluable_week_n
distinct_calendar_month_n
distinct_calendar_year_n
mean_return
median_return
annualized_arithmetic_mean
unannualized_horizon_volatility
annualized_volatility
diagnostic_sharpe
positive_rate
p10
ES10_loss
worst_single_cohort_return
mean_raw_stock_spearman
mean_aligned_bucket_spearman
nominal_hac_ci_low
nominal_hac_ci_high
nominal_hac_pvalue
block_bootstrap_ci_low
block_bootstrap_ci_high
block_bootstrap_pvalue
holm_adjusted_pvalue
summary_status
failure_reason
```

`unannualized_horizon_volatility = sample_std(weekly cohort endpoint returns, ddof=1)`；annualized volatility 仅是同比例
diagnostic scaling，两者都不得解释为 non-overlapping stateful strategy risk。
Summary table 对每个 scored registry row × 5 derived series roles × `FULL/EARLY/LATE`，以及每个 baseline registry row ×
`all_eligible_baseline` × 三 folds 完整物化，expected row count=`80*5*3 + 4*1*3 = 1212`；无 evaluable weeks 也保留 status/missing
statistics。Physical `series_role=bucket` 不进入 summary。

所有 CSV 必须有固定列序、UTF-8、`\n` newline、无 index；日期使用 ISO `YYYY-MM-DD`，唯一例外是 Section 14.12 明确注册的
`decision_date=SUMMARY` summary sentinel。Parquet schema 与 row count/hash
必须写入 manifest。

### 14.8 Daily-return resolution schema

`signal/daily_return_resolution_audit.csv.gz` 唯一 key 为 `(asset_role, instrument_id, session_date)`，至少包含：

```text
asset_role
instrument_id
session_date
previous_session_date
qfq_close
previous_qfq_close
raw_simple_return
resolved_simple_return
resolution_state
listing_date
delist_date
terminal_event_session
delist_rule_applied
all_tradable_assumption_applied
daily_suspension_lookup_performed
source_file_sha256
source_row_key_hash
feature_use_allowed
failure_reason
```

`resolution_state` 枚举固定为
`valid_mark / confirmed_delisting_terminal / unknown_data_gap / post_terminal_not_eligible`；
`daily_suspension_lookup_performed` 必须恒为 false，不得出现 suspension carry state。
`asset_role=stock` 使用完整四态；`asset_role=benchmark` 固定 `instrument_id=SH000300`，只允许
`valid_mark/unknown_data_gap`，listing/delisting/terminal fields 为 null。Benchmark missing return 会使涉及该 session 的 regression
paired row missing；不得对 benchmark carry/interpolate。

### 14.9 Daily residual-panel schema

`signal/daily_market_residual_panel.parquet` 唯一 key 为
`(instrument_id, residual_date, residual_model_id)`，至少包含：

```text
instrument_id
residual_date
residual_model_id
stock_simple_return
benchmark_simple_return
estimation_start_date
estimation_end_date
calendar_session_n
paired_observation_n
paired_coverage
design_rank
alpha
beta
residual
max_date_read
max_contributing_date
future_rows_loaded
future_rows_contributed
status
failure_reason
input_row_key_hash
```

Regression lineage 必须满足 `estimation_end_date < residual_date`；由于 `e_SRC(i,s)` 合法使用当日 `r_i,s/r_m,s`，daily residual
row 必须满足 `max_contributing_date == residual_date`，而不是 `< residual_date`。相对该 residual row 的
`future_rows_contributed=0`；物理读取更晚 raw qfq rows 只记录在 `max_date_read/future_rows_loaded`。Weekly signal row 仍满足
`max_contributing_date <= decision_date`。

### 14.10 Forward-return resolution 与 path schema

`historical/forward_return_resolution.parquet` 唯一 key 为
`(instrument_id, decision_date, holding_sessions, return_semantics)`，至少包含：

```text
instrument_id
decision_date
entry_date
holding_sessions
return_semantics
signal_mark_date
signal_mark
label_end_date
label_end_mark
resolved_forward_return
outcome_resolution_state
right_censored
delist_date
terminal_event_session
all_tradable_assumption_applied
source_file_sha256
source_row_key_hash
assignment_bundle_hash
affected_assignment_key_hash
failure_reason
```

`outcome_resolution_state` 枚举与优先级固定为：`right_censored`（label end 越界）→ `valid_mark`（signal/end marks 都 finite）→
`confirmed_delisting_minus_one`（满足 Section 10.2）→ `unknown_data_gap`。Right-censored row 的 outcome fields 保持 missing；不得读取
boundary 之后 mark 后再回填。
`affected_assignment_key_hash` 是该 forward-label row 对应的 sealed assignment keys
`(instrument_id,decision_date,arm_id,bucket_count)` 按 tuple ascending 排序后取 `stable_object_hash`；为空集合必须 fail，因为 outcome
stage 不得生成未被 sealed assignment 引用的 label。
Forward-resolution panel 对 sealed assignment 中 unique `(instrument_id,decision_date)` × H5/H10 × 两种 return semantics 各物化一行，
包括 warm-up/missing-signal instruments；不得只物化进入 favorable bucket 或 complete outcome 的 rows。

`historical/horizon_path_decomposition.csv` 唯一 key 为
`(decision_date, arm_id, formation_sessions, weighting, bucket_count, bucket_id, return_semantics)`，至少包含：

```text
decision_date
arm_id
formation_sessions
weighting
bucket_count
bucket_id
return_semantics
R_1_5
R_1_10
R_6_10
H5_evaluable
H10_evaluable
joint_evaluable
not_evaluable_reason
```

### 14.11 Paired residualization schema

`historical/paired_residual_vs_total_attribution.csv` 唯一 key 为
`(residual_arm_id, total_arm_id, formation_sessions, holding_sessions, return_semantics, weighting, bucket_count,
fold_id)`，至少包含：

```text
residual_arm_id
total_arm_id
formation_sessions
holding_sessions
return_semantics
weighting
bucket_count
fold_id
registered_pair_week_n
paired_evaluable_week_n
SRC_favorable_mean
Total_favorable_mean
paired_favorable_delta
SRC_spread_mean
Total_spread_mean
paired_spread_delta
SRC_favorable_volatility
Total_favorable_volatility
paired_volatility_delta
paired_volatility_ratio
SRC_ES10_loss
Total_ES10_loss
paired_ES10_loss_delta
paired_ES10_loss_ratio
minimum_paired_favorable_delta
paired_favorable_nondegradation_tolerance
minimum_paired_spread_delta
maximum_paired_volatility_ratio
maximum_paired_ES10_loss_ratio
residualization_value
classification_reason
```

Table 完整展开两组 matched pairs × 2 return semantics × 2 weightings × 2 bucket counts × 3 folds，expected row count=`48`；
cross-holding mappings 不进入 paired residualization table。

### 14.12 Style/morphology schema

`historical/style_morphology_attribution.csv` 唯一 key 为 `(record_type, decision_date, src_arm_id)`；summary row 使用
`record_type=FULL_SUMMARY,decision_date=SUMMARY` sentinel；weekly row 使用 `record_type=WEEKLY` 与 ISO decision date。至少包含：

```text
record_type
decision_date
src_arm_id
common_total_population_n
common_lowvol_population_n
common_size_population_n
spearman_SRC_vs_total
spearman_SRC_vs_negative_VOL20
spearman_SRC_vs_log_market_cap
top_decile_jaccard_SRC_vs_total
top_decile_jaccard_SRC_vs_lowvol
favorable_bucket_weighted_mean_beta
beta_attribution_weighting
valid_lowvol_spearman_week_n
valid_lowvol_jaccard_week_n
valid_size_spearman_week_n
warning_minimum_week_n
full_history_median_spearman_SRC_vs_negative_VOL20
full_history_median_lowvol_jaccard
full_history_median_spearman_SRC_vs_log_market_cap
arm_scale_dependence_warning
arm_size_dependence_warning
overall_scale_dependence_warning
overall_size_dependence_warning
style_status
failure_reason
```

Expected rows=`2 * (scheduled_decision_n + 1)`：SRC3/SRC4 每个 scheduled decision 各一条 WEEKLY row，并各一条 FULL_SUMMARY；
warm-up weekly rows保留为 not-evaluable。

### 14.13 Stability 与 dominance schemas

`historical/fold_and_year_stability.csv` 唯一 key 为
`(arm_id, formation_sessions, holding_sessions, return_semantics, weighting, bucket_count, slice_type, slice_id)`，至少包含：

```text
arm_id
formation_sessions
holding_sessions
return_semantics
weighting
bucket_count
slice_type
slice_id
registered_decision_week_n
evaluable_week_n
favorable_mean_return
spread_mean_return
favorable_positive
spread_positive
stability_status
failure_reason
```

只物化两条 matched-primary project/EW/decile arms。`slice_type=FOLD` 时 `slice_id=FULL/EARLY/LATE`；`slice_type=YEAR` 时
`slice_id=YYYY`，并对 frozen calendar 中每个 year 保留一行，即使 evaluable N=0。不得为 complete-case/VW/quintile/cross mapping
复制 stability rows。

`historical/month_instrument_dominance_audit.csv` 唯一 key 为
`(arm_id, formation_sessions, holding_sessions, return_semantics, weighting, bucket_count, audit_type, omitted_id)`，至少包含：

```text
arm_id
formation_sessions
holding_sessions
return_semantics
weighting
bucket_count
audit_type
omitted_id
base_favorable_mean
recomputed_favorable_mean
favorable_delta_from_base
base_spread_mean
recomputed_spread_mean
spread_delta_from_base
minimum_favorable_recomputed_mean
maximum_favorable_recomputed_mean
minimum_spread_recomputed_mean
maximum_spread_recomputed_mean
maximum_single_week_absolute_contribution_share
top3_week_absolute_contribution_share
sealed_assignment_reused
reranking_performed
status
failure_reason
```

同样只使用两条 matched-primary project/EW/decile FULL base。`audit_type` 枚举为 `LODO_WEEK/LOMO_MONTH/LOIO_INSTRUMENT/SUMMARY`：
前三者 `omitted_id` 分别为 ISO decision date、`YYYY-MM`、canonical instrument；SUMMARY 使用 `omitted_id=SUMMARY`，保存 min/max
与 contribution shares。非 SUMMARY rows 的 aggregate min/max/contribution fields 为 null，SUMMARY row 的 recomputed/delta fields 为
null。LOIO universe 是 sealed favorable/unfavorable assignments 的 instrument union。

### 14.14 Turnover/cost schema

`historical/turnover_break_even_cost_readout.csv` 唯一 key 为
`(arm_id, formation_sessions, holding_sessions, weighting, bucket_count, bucket_id, return_semantics)`，至少包含：

```text
arm_id
formation_sessions
holding_sessions
weighting
bucket_count
bucket_id
return_semantics
cost_transition_scope_id
valid_transition_n
gross_return_week_n
turnover_week_n
same_population_gate
mean_target_turnover
mean_gross_return
break_even_one_way_cost_bps
commission_buy_bps
commission_sell_bps
slippage_buy_bps
slippage_sell_bps
mean_transfer_fee_buy_bps
mean_transfer_fee_sell_bps
mean_stamp_tax_sell_bps
stamp_tax_proxy_mode
historical_stamp_tax_schedule_replication
minimum_commission_included
turnover_weighted_frozen_one_way_cost_bps
break_even_cost_multiple_proxy
break_even_one_way_cost_multiple_floor
frozen_cost_contract_gate
cost_feasible
failure_reason
```

Cost table 对 80 个 scored arm registry rows 各物化一行，`bucket_id=FAVORABLE`；baseline 不进入，expected row count=80。

### 14.15 Inference schema

`historical/hac_and_block_bootstrap_inference.csv` 唯一 key 为
`(test_id, estimator, arm_id, formation_sessions, holding_sessions, return_semantics, weighting, bucket_count, series_role,
fold_id)`，至少包含：

```text
test_id
estimator
arm_id
formation_sessions
holding_sessions
return_semantics
weighting
bucket_count
series_role
fold_id
calendar_slot_n
evaluable_week_n
null_value
alternative
hac_lag_weeks
block_method
block_length_weeks
bootstrap_repetitions
finite_bootstrap_repetitions
bootstrap_seed
scope_seed
bootstrap_rng
ci_method
estimate
standard_error
ci_low
ci_high
nominal_pvalue
holm_family_id
holm_family_size
holm_adjusted_pvalue
inference_status
failure_reason
```

HAC row 使用 `ci_method=normal_1.959963984540054`，bootstrap-only fields 为 null；bootstrap row 使用
`ci_method=percentile_linear_2.5_97.5`，`standard_error/hac_lag_weeks` 为 null。两行 `estimate` 都是 observed mean，不能把 bootstrap
mean 当 estimate。`nominal_pvalue` 保存对应 estimator 的 two-sided p-value；Holm fields 只允许 HAC matched-primary FULL rows非空。
Inference expected row count 固定为 `1212 summary rows * 2 estimators = 2424`，包括 not-evaluable rows；后者保留 key/config fields，
statistics missing 并写 failure reason。

### 14.16 Remaining registry/audit schemas

以下辅助 artifacts 同样不得由实现者临时猜 schema：

```text
preoutcome/input_inventory.csv
    key = (artifact_id, relative_path)
    fields = artifact_id, relative_path, dataset_role, file_size, row_count, date_min, date_max, sha256, status,
             blocking_reason

preoutcome/input_schema_audit.csv
    key = (artifact_id, column_name)
    fields = artifact_id, column_name, required, expected_dtype, observed_dtype, nullable_allowed, observed_null_n,
             status, blocking_reason

preoutcome/calendar_freeze.csv
    key = decision_date
    fields = decision_date, zero_based_session_index, iso_year, iso_week, entry_date, entry_within_boundary,
             residual_10D_calendar_ready, calendar_signal_possible, fold_id

preoutcome/formula_registry.csv
    key = formula_id
    fields = formula_id, arm_id, residual_model_id, estimation_sessions, minimum_paired_observation,
             formation_sessions, standardization_ddof, rcond, frozen_formula_text_sha256

preoutcome/sample_floor_and_gate_registry.csv
    key = (gate_id, metric_name, scope_id)
    fields = gate_id, metric_name, scope_id, operator, threshold, fold_id, primary_gate_eligible,
             preoutcome_frozen

signal/signal_coverage_audit.csv
    key = (decision_date, arm_id)
    fields = decision_date, arm_id, registered_denominator_n, signal_eligible_n, signal_coverage,
             decile_eligible, minimum_bucket_n_observed, missing_reason_mode, status

signal/signal_access_audit.csv and historical/outcome_access_audit.csv
    key = (stage, access_sequence_id)
    fields = access_sequence_id plus every Section 4.4 access-audit field
```

Formula registry 每个 signal formula 只物化一行：baseline 使用 `formula_id=NO_SCORE_BASELINE`，不适用数值字段为 null；holding 与
return semantics 只存在于 arm/horizon registry，不能为了同一 signal 的两个 holdings 复制 formula row。

`calendar_signal_possible=false` 的 calendar row 使用 `fold_id=NOT_IN_FOLD`；不得删除 warm-up rows 或以 null fold 隐藏。

`preoutcome/input_file_set_hashes.json`、各 stage manifest 与 output-hash JSON 使用 Section 16 的 canonical sorted-key JSON
serialization；`preoutcome/read_whitelist.json` 至少冻结 `stage, allowed_dataset_roles, allowed_path_patterns,
forbidden_column_patterns, raw_qfq_full_file_read_allowed, future_row_contribution_allowed`，其中最后一项必须为 false。
该 JSON 顶层为 `{"records": [...]}`，`stage` 唯一且必须恰好覆盖
`preflight/signal-materialization/outcome-materialization/finalize`；records 严格按
`[preflight, signal-materialization, outcome-materialization, finalize]` 顺序保存。Authorization
`allowed_read_scope` 必须等于对应 whitelist record 的 `stable_object_hash`，不能只写自由文本。

---

## 15. Report contract

报告顺序固定：

1. 一页 decision、terminal state 与授权边界；
2. 为什么它是新 family，不是 P4 holding appendix；
3. input lineage、history boundary、outcome contamination 与 all-tradable 乐观假设；
4. weekly calendar、daily rolling regression 与 timing audit；
5. 5D/10D signal coverage、missingness 与 beta distribution；
6. 完整 2 × 2 formation/holding matrix，不得只展示最好格；
7. favorable absolute return 与 spread 分离；
8. full/early/late、year、LOMO/LOIO 与 dominance；
9. residual vs total paired attribution、materiality margin 与 early/late non-degradation；
10. Low Vol/size/beta overlap 与 morphology warnings；
11. H5/H10 path decomposition、fast decay/delayed realization 判断；
12. turnover、继承的 frozen cost、break-even multiple 与 matched-primary cost gates；
13. AFML utility classification：sleeve hypothesis、meta-label/participation filter 或停止；
14. gate truth table、next-step recommendation 与明确的 no-authorization footer。

报告禁止：

- `replicated`, `supported`, `OOS`, `deployable`, `alpha` 等越权措辞；
- 用 annualized endpoint mean 冒充 strategy CAGR；
- 只报告 +spread 而不报告 favorable absolute return；
- 把 weekly instrument rows当 sample N；
- 隐藏 cross mappings、失败 folds、Low Vol comparator 或 style warning；
- 把 all-tradable 假设写成已验证的成交能力，或把缺失 qfq mark 当作停牌 carry；
- 把 target-turnover cost proxy 写成实际成交成本、net return 或完整 executable gate；
- 以新 family 结果重写 20B v5 decision。

---

## 16. Manifest、hash 与 transactional publication

整次 run 使用：

```text
BUILD_ROOT = Path(str(OUTPUT_ROOT) + ".building")
stage candidate = BUILD_ROOT/.<stage>.candidate
sealed build-stage path = BUILD_ROOT/<stage>
final published root = OUTPUT_ROOT
```

Preflight 创建不存在的 `BUILD_ROOT`；若 `OUTPUT_ROOT` 已存在则 immutable fail，若 `BUILD_ROOT` 已存在则必须显式 resume 同一
run/version 且先验证已有 sealed stage，禁止清空重建。每个 stage 先写 sibling candidate，完成 schema、row count、key uniqueness、
file-set 双向 hash 与 authorization 校验后，以单次 same-filesystem `os.replace(candidate, BUILD_ROOT/<stage>)` 发布。Finalize 在
`BUILD_ROOT` 根生成 final artifacts，复核三个 sealed stage 与 authorizations 后，以单次 `os.replace(BUILD_ROOT, OUTPUT_ROOT)` 发布
整个 run；因此不会逐文件发布半成品。Finalize 失败时 `OUTPUT_ROOT` 必须仍不存在。
若目标 sealed stage 已存在且验证通过，stage command 只返回 `already_sealed`；若 candidate 已存在、目标验证失败或 run/version
不一致则 fail 并保留现场，不得自动删除或覆盖。

### 16.1 Canonical serialization 与 bundle hash

冻结 helper semantics：

```text
file_sha256 = SHA256 of exact file bytes, streamed in binary mode
canonical_compact_json(value) = json.dumps(value, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":"), allow_nan=False)
stable_object_hash = SHA256(UTF-8 bytes of canonical_compact_json(value))
published_json_writer = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                                   allow_nan=False) + "\n"
CSV writer = UTF-8, index=false, lineterminator="\n", float_format="%.12g", missing=""
CSV.gz = deterministic gzip, compresslevel=9, mtime=0, empty embedded filename
relative paths in registries = POSIX paths relative to the bundle root
```

NaN/Infinity 在 JSON 中禁止；使用 null。CSV boolean 固定 `True/False`，日期按各 schema 的 ISO/sentinel contract。Parquet 固定
`engine=pyarrow, compression=zstd, index=false`，并在 manifest 记录 Python、pandas、numpy、scipy、pyarrow 与 platform versions；
同一 sealed artifact 只按 exact bytes 验证，不声称跨不同 pyarrow version byte-identical。
每张 CSV/Parquet 在写入前必须按其注册 unique key ascending stable-sort（nulls last），列严格按 schema order；JSON arrays 按各自
registry key stable-sort。未注册 row order 或依赖 hash-map iteration 的输出必须 fail schema/reproducibility gate。

每个 stage 的普通 publishable files 集合记为 `F`，不含 manifest 与 output-hash registry：

```text
artifact_hashes = {relative_path: file_sha256(path) for relative_path in sorted(F)}
manifest.output_hashes = artifact_hashes
write manifest with published_json_writer
output_hashes = artifact_hashes plus {manifest_relative_path: file_sha256(manifest)}
write output-hash registry with published_json_writer
bundle_hash = file_sha256(output-hash registry)
output-hash registry excludes itself; manifest excludes itself and the registry
```

Manifest 与 registry 的 key set、目录实际普通文件 set 必须双向相等；允许排除项只有 manifest 与其 output-hash registry，且按上述
规则分别处理。不得把 mtime、directory inode、absolute path 或生成顺序纳入 hash。

Manifest 至少包含：

```text
run_id
contract_version
stage
created_at_utc
requirement_sha256
config_sha256
upstream_bundle_hashes
input_file_set_hashes
authorization_record
history_date_min/max
registered_arm_horizon_rows
file_path
file_size
row_count
schema_hash
sha256
runtime_versions
```

Manifest `stage` 枚举固定为 `preoutcome/signal/historical/final`，分别对应四个 CLI stages；不得混用 CLI verb 作为另一套值。

`file_path/file_size/row_count/schema_hash/sha256` 在 manifest 中是 `artifacts` list 内的 object fields；list 严格按 `file_path`
ascending，不是重复的顶层 scalar，也不是 path-keyed object。CSV schema hash 对 ordered `(column_name,dtype)` 列表取
`stable_object_hash`；Parquet schema hash 对 ordered Arrow schema
的 canonical string/metadata-free representation 取 hash；JSON schema hash 对 requirement 注册的 ordered key/type tree 取 hash；
Markdown `schema_hash=null`。JSON/Markdown row_count 使用 null，CSV/Parquet 使用 data rows，不含 header。
Preoutcome manifest 的 `authorization_record=null`；signal/historical manifest 分别嵌入对应 authorization object、raw file SHA256 与
semantic hash；final manifest 使用 `authorization_records={signal:..., outcome:...}`，不得用自由文本摘要替代原值。

双向 file-set gate：

- manifest 中每个文件必须存在且 hash/size 相符；
- stage 目录中除 manifest/hash registry 外的每个 publishable 文件必须在 manifest；
- final root 允许的子目录严格为 `preoutcome, signal, historical, authorizations`；前三者分别通过自身 bundle gate，authorizations
  目录严格包含 Section 14.0 两个文件；final manifest 的普通 artifact set 只包含 root-level decision/report；
- extra、missing、duplicate logical artifact 一律 fail；
- finalized report 必须在 final manifest 中，密封后不得人工追加叙事；
- final manifest 还必须记录三个 stage bundle hashes、两份 authorization file hashes 与 authorization semantic hashes；
- 若需修改报告或任何 artifact，升级 contract/run version，不得覆盖。

---

## 17. Test 与 validation contract

未来实现至少覆盖：

1. ISO week holiday calendar 仍只产生一个 decision；
2. `usable_trade_date=next_session(decision)` 且 membership availability 不晚于 decision close；
3. rolling regression window 恰为前 252 scheduled sessions，paired floor=200；
4. `max_estimation_date < residual_date` 且 daily residual `max_contributing_date == residual_date`；full-sample beta 测试必须失败；
5. 5D/10D formation exact、包含 decision day、不含 future session；
6. total continuation 与 residual continuation 标准化公式仅差 residualization；
7. H5/H10 label end 恰为第 5/10 个未来 exchange session；
8. outcome incomplete 不改变 bucket assignment；
9. unknown positive-weight row 使 project bucket-week fail closed；
10. decile不足不得降为 quintile冒充 primary；
11. 2 × 2 residual matrix 与所有 comparators 完整出现；
12. 5x10/10x5 不进入 positive-exposure gate；
13. spread positive、favorable negative 时 positive gate=false；
14. paired residual-vs-total 只用共同 evaluable weeks；
15. early/late boundary 不因 missing outcome 重切；
16. H10 overlap 使用 HAC/block inference，naive independent-N 字段不得进入报告；
17. style warning thresholds 可机械复算；
18. turnover与 break-even formula 可机械复算；
19. signal feature tables 出现未豁免的 outcome-like column fail；注册的 access-lineage 字段不误报；
20. duplicate stable key fail；
21. stage authorization/hash 不匹配 fail；
22. final file-set 双向 hash gate。
23. 不查询或推断逐日停牌，registered denominator row 恒采用 all-tradable；
24. qfq mark 缺失仍解析为 `unknown_data_gap`，不得 carry/zero-fill/interpolate；
25. full raw qfq file 可被物理加载且 `max_date_read > decision_date` 不单独触发 firewall；
26. 任一 future row 对 signal 有贡献、`max_contributing_date > decision_date` 或读取 outcome-role table 必须触发 firewall；
27. 零基 exchange calendar 上 residual 最早 `s=253`，完整 10D formation decision 最早 `j=262`；
28. `calendar_signal_possible` 与 early/late split 不因逐股 signal coverage 或 missing outcome 改变；
29. 仅任意 epsilon 的 favorable/spread/volatility/ES 改善不能通过 residualization value；
30. full materiality 与 early/late non-degradation threshold 均可按 H=5/H=10 机械复算；
31. frozen cost components/hash 与 20A v2 不一致时 `frozen_cost_contract_gate=false`；
32. break-even multiple nonfinite、gross mean nonpositive或 `<1.25` 时对应 cost gate=false；
33. 5D/10D style warnings 分别计算，overall warning 恰为两个 per-arm warning 的 OR；
34. 未获 signal authorization 时 terminal state 为 not-authorized，不因不存在后续 manifest 误判 hash-blocked；
35. Section 14 每张 required table 的 column order、key uniqueness、enum 与 sentinel schema 全部校验。
36. registered rows 缺失进入 data/formula blocked；rows 完整但 sample floor 不足进入 underpowered，不得互相混淆。
37. stamp tax proxy 对所有历史 transitions 固定 5 bps、transfer fee 按 effective date，且两个乐观限制进入 decision/report。
38. signal/outcome authorization 文件路径、semantic hash、bound bundle hash 与 whitelist-scope hash 任一不匹配均 fail。
39. 四 stage whitelist 完整；signal 读取 outcome-role table、outcome 重读 universe、finalize 重读 raw 任一必须 fail。
40. qfq 每一 row 的唯一 internal instrument 必须等于 filename stem/canonical id；不能只抽首行。
41. delist session 有 valid mark 时 observed mark 优先；其后首个 missing session 才施加一次 terminal，right-censor 优先于未来 metadata。
42. ES10 使用 fixed `ceil(10%N)` worst-order tail、linear q10；ties 不扩大 tail，布尔均值实现必须失败。
43. coverage median/minimum 使用全部 calendar-signal-possible weeks，删除 denominator=0 或未 ready weeks 的实现必须失败。
44. cost mean return 与 turnover 使用完全相同 `C_H` later-week population，不得跨 missing scheduled week。
45. Spearman midrank、common-population Jaccard rerank、52-week warning evaluability 与三态 OR 可机械复算。
46. calendar-aware HAC 不压缩 missing gaps；shared-PCG64 moving-block paths、CI/pvalue/Holm 可由冻结公式复算。
47. arm registry 恰为 84 rows、formula registry 6 rows、summary 1212 rows，且 bucket/series sentinels 无 duplicate/alias。
48. summary 字段名与 Section 11 完全一致，decision 包含两级 authorization gates 与 `policy_replay_authorized=false`。
49. canonical JSON/CSV writers、manifest exclusions、bundle hash 与双向 file-set 可复算。
50. stage candidate 与最终 BUILD_ROOT rename 失败注入测试证明不会出现半发布 OUTPUT_ROOT。
51. daily return/model/residual panel 恰按 U_ever × frozen calendar 物化显式状态，未入 U_ever qfq 不生成 signal rows。
52. warm-up scheduled weeks 的 weekly signal/assignment rows 保留且 status 明确，但不进入 sample-support denominator。

未来标准命令：

```bash
python -m pytest -q tests/test_20b_src_short_term_residual_continuation_family_diagnostic.py

python src/run_20b_src_short_term_residual_continuation_family_diagnostic.py \
  --config configs/config_20b_src_short_term_residual_continuation_family_diagnostic.yaml \
  --stage preflight

python src/run_20b_src_short_term_residual_continuation_family_diagnostic.py \
  --config configs/config_20b_src_short_term_residual_continuation_family_diagnostic.yaml \
  --stage signal-materialization \
  --preoutcome-bundle-hash <SEALED_HASH> \
  --authorization-file outputs/20B_SRC_short_term_residual_continuation_family_diagnostic_v0.building/authorizations/signal_materialization_authorization.json

python src/run_20b_src_short_term_residual_continuation_family_diagnostic.py \
  --config configs/config_20b_src_short_term_residual_continuation_family_diagnostic.yaml \
  --stage outcome-materialization \
  --signal-bundle-hash <SEALED_HASH> \
  --authorization-file outputs/20B_SRC_short_term_residual_continuation_family_diagnostic_v0.building/authorizations/outcome_materialization_authorization.json

python src/run_20b_src_short_term_residual_continuation_family_diagnostic.py \
  --config configs/config_20b_src_short_term_residual_continuation_family_diagnostic.yaml \
  --stage finalize
```

这些命令只定义未来接口；本 requirement 生成不授权执行。

---

## 18. Definition of Done

Requirement review-ready 当且仅当：

- 新 family 与 monthly P4/论文 exact residual momentum 的身份边界明确；
- weekly calendar、daily beta、5D/10D formation/holding 与完整 matrix 无歧义；
- denominator、all-tradable 假设、qfq mark、missingness、delisting、bucket 与 weighting 可机械实现；
- favorable absolute return、spread、residualization attribution 与 style warning 分工明确；
- residualization materiality/non-degradation 与 inherited-cost multiple 可机械复算；
- stage-specific whitelist、两级 authorization artifact/path/hash 与 CLI 接口闭合；
- ES/HAC/bootstrap/sample-support/cost-transition population 与 series-role enum 无实现选择空间；
- overlap/inference/sample floor 不把 weekly rows夸大成独立支持；
- state machine 能区分 persistent、ultrashort filter、delayed、morphology-only 与 null；
- 所有 output/schema/hash/authorization contract 完整；
- canonical serialization、bundle hash 与 whole-run atomic publication 可失败注入验证；
- 明确 `implementation_authorized=false`、`20C_requirement_generation_authorized=false` 与
  `deployment_authorized=false`。

实现完成的 Definition of Done 另要求：

- 所有 tests 通过；
- preoutcome、signal、historical、final 四级 bundle 全部密封且双向 hash 通过；
- 完整 2 × 2 grid 与所有失败行均发布；
- report 与 decision CSV 一致；
- 没有读写或修改 20B v5 sealed artifacts；
- 最终 git diff 只包含获授权的新 family artifacts。

---

## 19. Requirement review checklist

- [ ] 这是独立 `short_term_market_residual_continuation_adaptation`，没有冒充 12-1 residual momentum。
- [ ] 生成 spec 获授权，但 implementation/outcome run 未授权。
- [ ] 20B v5 decision 与 20C authorization 完全不受影响。
- [ ] History boundary 固定为 2017-01-03 至 2026-05-29。
- [ ] Weekly decision 是 ISO week 最后一个交易日，所有 horizon 使用 exchange sessions。
- [ ] U_project 使用 next-session `usable_trade_date` 且在 decision close 已可得。
- [ ] 不读取/推断逐日停牌；registered denominator rows 全部假设可交易，并明确标记乐观偏差。
- [ ] 缺失 qfq mark 仍 fail closed，不因 all-tradable 假设 carry、补零或插值。
- [ ] QFQ filename、全文件 internal instrument 与 canonical id 使用 exact 1:1 mapping。
- [ ] Delisting observed-mark precedence、terminal session 与 right-censor precedence 已冻结。
- [ ] Rolling beta 使用前 252 scheduled sessions、至少 200 paired rows、严格 sequential。
- [ ] Calendar warm-up 使用零基 `s>=253` 与完整 matrix decision `j>=262`，fold 不由 coverage/outcome 改写。
- [ ] 5D/10D formation 包含 decision day，不 skip 最近一天。
- [ ] 5D/10D full matrix 全注册，5x5 与 10x10 是唯一 matched primary。
- [ ] Total continuation 公式除 residualization 外完全同口径。
- [ ] Low Vol 只作 comparator，不能授权 family。
- [ ] EW decile favorable absolute return 是 positive-exposure gate。
- [ ] Spread、VW、quintile 与 complete-case 不替代 primary gate。
- [ ] H10 overlap 使用 HAC 4 weeks 与 13-week block bootstrap。
- [ ] ES10 order tail、calendar-gap HAC、shared deterministic bootstrap 与 Holm 公式可机械复算。
- [ ] Sample floors 同时约束 weeks、months、years、folds 与 coverage。
- [ ] Coverage/minimum 使用全部 calendar-signal-possible weeks，paired attribution 有独立 support gate。
- [ ] Residual-vs-total 必须 paired，不用 unpaired means。
- [ ] Residualization value 达到冻结 materiality 且 early/late 不超 tolerance，不由 epsilon 改善触发。
- [ ] 5D/10D Style overlap 分臂计算，overall warning 是 per-arm warning 的 OR。
- [ ] Turnover/break-even 继承 20A cost fields 并要求 `>=1.25`；仍只作 proxy，不声称 net strategy。
- [ ] Cost mean return/turnover 使用同一 transition population，transfer fee active rows 唯一值校验。
- [ ] Signal firewall 区分 raw-file rows loaded 与 rows contributed；只允许贡献日期不晚于 decision。
- [ ] Signal/outcome/finalize 各自 read whitelist 与 authorization path/hash/bundle binding 完整。
- [ ] Terminal states 与 truth table 可机械复算。
- [ ] 未授权优先于尚不应存在的下游 manifest/hash 缺失。
- [ ] 所有 stage 都有 access audit、manifest、output hashes 与 transactional publication。
- [ ] Canonical writers、manifest exclusions、bundle hash、stage rename 与 final BUILD_ROOT rename 已冻结。
- [ ] Final footer 明确 no forward/20C/policy/optimization/deployment authorization。

# Requirement 20B：TrendPV 与 Residual Momentum 历史设计 / 复制诊断

## 0. 不可协商范围

20B 只做 **paper-grounded historical formula QA、排序方向诊断、effect sizing 与 20C 设计授权判断**。

它不是：

- true OOS / forward support；
- alpha 搜索；
- 可执行 long-only portfolio 回测；
- 参数优化、窗口扫描或阈值修复；
- EP19 B2 效果复算；
- 20C、policy、portfolio optimization 或 deployment 的执行授权。

固定目标语义：

```text
primary_objective = deployable_positive_beta
incremental_alpha_required = false
historical_sample_role = design_contaminated_historical
historical_support_claim_allowed = false
matched_alpha_required = false
scale_independence_required = false
```

20B 必须逐字披露：

```text
20B 使用的是已被 topic 反复消费的历史样本；所有收益结果只能用于公式排错、方向诊断和下一阶段设计，不能形成 support。

20B 的 long-short、decile 和 paper-semantics 结果不是可部署 long-only 正 beta sleeve。

20B 必须把 paper sort morphology 与正收益暴露分开：high-minus-low 为正不是正 beta 的必要条件；20C 生成门使用 favorable bucket 的绝对 gross return 方向，不要求相对低分组存在 alpha。

P2/P3 exact routes 因 20A 数据门失败而 registered-not-run；project adaptation 不得升级 exact replication claim。

EP19 2025 concept-board proxy 在 2025 年以前是 retrospective look-ahead sensitivity，不是 historical PIT industry。

20B 不要求 matched alpha；scale、size、board 与 volatility 分解只解释收益来源。
```

---

## 1. 身份、上游授权与执行边界

```text
experiment_id = 20_ohlcv_positive_beta_exposure_research
phase_id = 20B
run_id = 20B_trendpv_residual_momentum_design_and_replication_diagnostic
contract_version = 20B_v1
requirement_file = requirement_20b_trendpv_residual_momentum_design_and_replication_diagnostic.md
config_file = configs/config_20b_trendpv_residual_momentum_design_and_replication_diagnostic.yaml
runner_file = src/run_20b_trendpv_residual_momentum_design_and_replication_diagnostic.py
test_file = tests/test_20b_trendpv_residual_momentum_design_and_replication_diagnostic.py
output_root = outputs/20B_trendpv_residual_momentum_design_and_replication_diagnostic
```

唯一上游 authority：

```text
20A decision_state = 20A_preoutcome_contract_ready
20A contract_version = 20A_v2
20A freeze_bundle_hash = da5902ac7a987ec061cdffc33e8735ad34c22f1ae771a43540fe005fd77acb05
20A next_allowed_requirement = requirement_20b_trendpv_residual_momentum_design_and_replication_diagnostic.md
20A next_requirement_generation_authorized = true
20A next_requirement_execution_authorized = false
```

因此，本文件的生成已获授权，但 **20B 实现和任何历史 outcome 读取仍未获授权**：

```text
requirement_generation_authorized = true
implementation_authorized = false
historical_outcome_execution_authorized = false
policy_training_authorized = false
policy_replay_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

只有用户在本 requirement 评审通过后明确发出实施/运行指令，才可创建 runner、读取历史 monthly return 或生成
20B result bundle。Requirement 生成本身不得读取或计算任何新 outcome。

### 1.1 Staged execution

未来实现必须分四阶段：

```text
stage 1 = preflight
    verify immutable 20A bundle;
    freeze arm/formula/calendar/universe/bucket/statistical contracts;
    do not read t+1 return or any outcome column;
    seal preoutcome bundle.

stage 2 = authorize-run
    require explicit human authorization bound to preoutcome bundle hash;
    authorization must predate the first historical outcome read.

stage 3 = run-historical
    read only frozen historical outcome fields;
    materialize all registered tracks, including failures and unavailable rows;
    prohibit parameter or arm changes.

stage 4 = finalize
    read only sealed preoutcome bundle plus sealed historical-run artifacts;
    create decision/report/manifests;
    do not reread raw data.
```

同一个 `run_id + contract_version` 不得覆盖 sealed bundle。任何公式、track、窗口、bucket、sample floor、paper-sort gate、positive-exposure gate 或
outcome 口径变化都必须升级 contract version。

---

## 2. 20B 只回答的问题

20B 只回答：

1. 冻结的 TrendPV raw-score adaptation 在本地 U_project 上能否正确物化；高分组下一月绝对 gross return 是否为正；高减低 paper-sort morphology 是否同方向？
2. Total Momentum 12-1 与 Low Vol 是否提供合理的固定 comparator 形态？
3. sequential market-only residual momentum（R2/P4）是否能正确物化，且排序方向是否与 residual-momentum 文献一致？
4. R3/P5 在先做 R2 market residual 后，再做 lagged size + static board ridge residualization，能否机械复现？
5. P5 相对 P4 的差异来自哪里；2025 board proxy 的 retrospective look-ahead 与 staleness 边界是否被完整披露？
6. exact Trend / CH-3 residual routes 为什么不可运行，fallback 是否没有被误写成 exact replication？
7. 公式、月份支持、favorable bucket 绝对 gross return、paper spread、early/late、dominance 与 missingness 是否足以授权生成 20C requirement？

20B 不回答：

- 哪个参数最好；
- 哪个持有期收益最高；
- long-only full-capital sleeve 是否成本后可部署；
- 未来 126 个月是否提供确认性证据；
- 是否存在独立于 beta/scale 的 alpha。

---

## 3. 上游 immutable bundle 与 lineage gate

路径别名：

```text
EXPERIMENT_ROOT = topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research
20A_ROOT = EXPERIMENT_ROOT/outputs/20A_paper_lineage_data_and_replication_contract
20A_FREEZE = 20A_ROOT/freeze
20A_DECISION = 20A_ROOT/20A_preoutcome_contract_decision.csv
20A_FREEZE_MANIFEST = 20A_FREEZE/freeze_manifest_20a.json
20A_FREEZE_HASHES = 20A_FREEZE/freeze_output_hashes_20a.json
20A_FINAL_MANIFEST = 20A_ROOT/manifest_20a_paper_lineage_data_and_replication_contract.json
20A_FINAL_HASHES = 20A_ROOT/output_hashes_20a_paper_lineage_data_and_replication_contract.json
```

20B preflight 必须：

1. 复算 20A freeze/final manifests 与 output hashes；
2. 验证 `SHA256(bytes(20A_FREEZE_HASHES))` 等于冻结的 bundle hash；
3. 验证 20A decision 单行且所有 20B 必需 critical gates 为 `pass`；
4. 验证 `historical_support_claim_allowed=false`；
5. 验证 exact flags 均为 false、P2/P3 不得运行；
6. 验证 material waiver 只影响本地 source-cache 声明，不改变 formula/economic gate；
7. hash 本 requirement 与未来 config，然后密封 20B preoutcome bundle。

Required output：

```text
preoutcome/upstream_20a_integrity_audit.csv
```

最少字段：

```text
artifact_id
path
expected_sha256
observed_sha256
required_value
observed_value
status
blocking_reason
```

任一必需 hash、decision 或 gate 不一致：

```text
upstream_20a_integrity_gate = fail
decision_state = 20B_upstream_contract_blocked
historical_outcome_execution_authorized = false
```

---

## 4. 20A 已知 metadata inconsistency 与 20B resolution

20B preflight 必须显式记录以下上游 metadata/role resolutions；不得静默继承：

### 4.1 R2 universe-role inconsistency

20A `paper_formula_registry.csv` 的 `RESMOM_R2_MARKET_ONLY_ADAPTATION` 行把 `universe_rule` 写为 `U_paper`，但以下
冻结 authority 一致指向 project adaptation：

```text
20A decision.R2_market_adaptation_reachable = true
20A arm_role_registry.C3A_RESMOM_R2_MARKET_ONLY = fallback residual project arm
research_plan R2 = market_only_residual_momentum_adaptation
U_paper paper_exact_allowed = false
```

20B resolution：

```text
P4 decision denominator = U_project
P4 time-series lookback may use the instrument's causal qfq history before it entered U_project
P4 replication_role = project_adaptation
P4 exact_replication_claim_allowed = false
```

### 4.2 R2 arm-promotion 与 residual-family bridge role

20A 冻结 `C3A_RESMOM_R2_MARKET_ONLY` 为 comparator 且 `promotion_eligible=false`；20B 不得把 P4/R2 静默升级为
primary arm。与此同时，P4 是历史期唯一不依赖 2025 static-board look-ahead 的 residual-family 方向诊断，因此允许它判断
是否值得生成 20C 去测试 **20A 已冻结的 R3 residual primary**。

冻结为两个不同字段：

```text
P4_arm_promotion_eligible = false
P4_residual_family_bridge_authorizer = true
P4_pass_does_not_change_residual_primary = true
residual_primary_arm_frozen = C3_RESMOM_R3_BOARD_ADAPTATION
```

P4 gate 通过只授权生成包含 R2 comparator 与 R3 frozen primary 的 20C requirement；不得把 P4 写成 promoted primary、
不得删除 R3，也不得改变 20A multiple-testing family。

### 4.3 TrendPV warm-up inconsistency

20A `warmup_and_monthly_support_audit.csv` 把 Trend rows 估为 97 post-warmup months，但 paper methodology 明确：

```text
skip first 400 trading sessions for MA signals
then require/burn first 38 complete coefficient-estimation months
```

20B 不得使用 97 作为 observed support。必须从实际 calendar、完整 signal rows 和 coefficient path 重算最早
decision month 与 post-warmup month count。

Required output：

```text
preoutcome/upstream_metadata_resolution_registry.csv
```

每行至少有：

```text
inconsistency_id
source_artifact
source_field
observed_value
resolved_value
resolution_authority
outcome_used_for_resolution
claim_impact
status
```

硬约束：

```text
outcome_used_for_resolution = false
R2_universe_resolution_gate = pass
R2_family_bridge_role_resolution_gate = pass
TrendPV_warmup_resolution_gate = pass
```

否则 20B 不得进入 historical run。

---

## 5. Allowed inputs、read whitelist 与 outcome firewall

### 5.1 Preflight 允许读取

```text
20A sealed artifacts
research_plan.md
this requirement
future 20B config
PROJECT_UNIVERSE_FILE from 20A resolved_config
qfq root headers, dates and unit metadata only
benchmark dates/identity only
EP19 board index/member schema and membership only
trading calendar
security master/status lineage
```

Preflight 禁止读取：

```text
next-month stock return
monthly bucket return
future_return*
MFE*
MAE*
winner*
hit_*
strategy PnL/NAV
any EP19 outcome table or report
any post-20A-seal decision outcome
```

### 5.2 Historical run 允许读取

只有 human run authorization 通过后，historical run 才能读取：

```text
qfq OHLCV through the frozen local_data_max_date
benchmark OHLC through the same boundary
frozen U_project PIT rows
frozen board membership
preoutcome-frozen decision calendar and arm registry
```

Historical run 仍禁止读取：

```text
decision timestamps strictly after 20A seal
EP19 B/B1/B2/B3 return, MFE, MAE or winner tables
120-session Big Winner paths
20C stateful strategy results
unregistered repair arms
```

### 5.3 Historical boundary

```text
history_date_max = min(20A frozen local_data_max_date, 2026-05-29)
decision_date <= last project month-end whose next calendar-month label is complete by history_date_max
post_20A_seal_decision_rows_allowed = false
backfilled_pre-seal_rows_role = historical_design_only
```

20B 不得因未来数据更新而扩大同一 contract version 的历史样本。

### 5.4 Outcome access audit

所有读取逐次记录：

```text
stage
accessed_at_utc
artifact_path
artifact_sha256_or_root_hash
dataset_role
columns_read
derived_fields
historical_outcome_access_authorized
forward_outcome_detected
selection_or_tuning_allowed
purpose
access_gate
```

任何 forward outcome、未注册 outcome artifact 或 tuning read：

```text
outcome_firewall_gate = fail
decision_state = 20B_outcome_firewall_violated
```

---

## 6. Arm 与 track registry

20B 固定以下 arms；不得增加、删除、合并或重命名：

| 20B arm | 20A formula/arm | universe | role | run status | 20C role |
|---|---|---|---|---|---|
| `P0_TOTAL_MOMENTUM_12_1` | `TMOM_12_1 / C1` | U_project | paper comparator | run | comparator only |
| `P1_TRENDPV_RAW_ADAPTATION` | `TRENDPV_SIGNALS + TRENDPV_MONTHLY_CS_REG / C2` | U_project | TrendPV project adaptation | run | 20C design input |
| `P2_TREND_FULL_EXACT` | `TRENDPV_FULL_FACTOR / P2` | U_paper | exact paper diagnostic | registered-not-run | none |
| `P3_RESMOM_CH3_EXACT` | `RESMOM_EXACT_CH3 / P3` | U_paper | exact paper diagnostic | registered-not-run | none |
| `P4_RESMOM_R2_MARKET_ONLY_ADAPTATION` | `RESMOM_R2... / C3A` | U_project | clean project adaptation comparator | run | residual-family bridge authorizer; arm promotion remains false |
| `P5_RESMOM_R3_BOARD_ADAPTATION` | `RESMOM_R3... / C3` | U_project | frozen residual primary / board sensitivity | run | cannot authorize alone |
| `P6_LOWVOL_36M_COMPARATOR` | `LOWVOL_36M / C4` | U_project | low-risk comparator | run | comparator only |

P2/P3 必须各输出一行：

```text
run_status = registered_not_run
reason = 20A exact data/history/universe gates failed
row_n = 0
exact_replication_claim_allowed = false
```

不得以 qfq 有约 4,597 文件为由运行 exact route。

### 6.1 Fixed semantic tracks

P1 固定两条 semantics track，不视为可择优 arms：

```text
paper_fill_sensitivity:
    suspended price = last valid close carry-forward;
    volume signal requires >L/2 trading records and a current-month trading record;
    otherwise carry the last available same-L volume signal;
    role = paper-semantics formula diagnostic only.

project_strict_primary:
    last L observed instrument bars ending at decision month-end, with no forward fill;
    current close and current normalized volume must be positive/nonmissing;
    no carried signal;
    missing any required input makes that stock-month ineligible;
    role = clean input to 20C design decision.
```

P5 固定一个 full-history diagnostic track，并把每个 score row 分入三个互斥 date scopes。Scope 由 snapshot date 与
11 个 score residual months 机械决定，不得只看 decision date：

```text
full_history_retrospective_proxy:
    track containing all evaluable historical rows;
    never enters 20C generation gate.

pre_snapshot_decision_retrospective:
    decision_date < 2025-01-02;
    formation is retrospective look-ahead;
    row scope is retrospective only.

mixed_post_snapshot_decision:
    decision_date >= 2025-01-02;
    at least one of the 11 score residual months has board_known_by_predictor_asof=false;
    post-snapshot decision label does not make its formation causal;
    contaminated descriptive window only.

fully_post_snapshot_score:
    every one of the 11 score residual months has board_known_by_predictor_asof=true;
    first eligible decision month must be derived from the frozen calendar, not hard-coded;
    expected local support is only about 2026-01 through 2026-04 and must be reported exactly;
    cannot alone authorize 20C.
```

不得按 outcome 选择 track 或 scope。

Required output：

```text
preoutcome/arm_and_track_registry.csv
```

Registry 必须分别列出 `signal_semantic_track`、`return_semantics`、`P5_date_scope`、`arm_promotion_eligible` 与
`family_bridge_authorizer`；不得把这些不同维度压成一个含混的 `track` 字符串。

---

## 7. Calendar、universe 与 monthly panel contract

### 7.1 Decision calendar

```text
scheduled_decision_date = last exchange-open session in each calendar month
signal_asof = scheduled_decision_date close
formation_month = calendar month containing scheduled_decision_date
primary_paper_holding = next complete calendar month
label_end = last exchange-open session of next calendar month
decision month t is complete at signal_asof
12-1 convention at decision t = use t-11...t-1 and skip just-completed month t
```

冻结 decision calendar 时只能使用 dates，不得读取 return values。

### 7.2 U_project denominator

每个 decision month 的 denominator：

```text
usable_trade_date == scheduled_decision_date
is_listed == true
membership/source timing known by decision close
history_ready rule is arm-specific, not silently inherited from generic 240d flag
```

`is_suspended`：

- paper-fill sensitivity 可保留并按 Section 6.1 填充；
- project-strict primary 必须排除当前月末 suspended/missing-current-bar 名称；
- denominator、signal eligible 与 bucket eligible 三个 N 必须分开报告。

### 7.3 Monthly price/return 与 outcome-resolution tracks

```text
month_end_close = qfq close on the last valid exchange session under the selected semantics track
monthly_return_t = month_end_close_t / month_end_close_(t-1) - 1
next_month_return_(t+1) = month_end_close_(t+1) / month_end_close_t - 1
```

qfq ratio 只能标为 `provider_qfq_price_return_proxy`，不能声称是论文数据库的 exact total return。所有 split/dividend
调整语义沿用 20A qfq audit。

Signal semantics 与 return semantics 是两个独立维度。所有 primary 1-month bucket 必须并行输出：

```text
paper_qfq_complete_case_sensitivity:
    valid qfq month-end ratio only;
    incomplete rows may be excluded and analysis weights renormalized;
    diagnostic only; cannot enter positive-exposure gate or 20C authorization.

project_conservative_primary:
    target weights are fixed at decision t before reading t+1 outcome;
    valid label-end mark -> use qfq month-end ratio;
    suspended/no label-end trade with a valid valuation bridge -> carry last valid marked close;
    confirmed delisting with missing recovery -> terminal return = -1.0;
    unknown valuation/corporate-action bridge -> entire arm-track-bucket-month is not evaluable;
    never drop one incomplete selected instrument and renormalize the survivors;
    only this track may enter positive-exposure gate.
```

上述 `project_conservative_primary` 继承 20A `label_completion_and_censoring_rule_freeze.csv` 的 terminal resolution，但仍是
20B close-to-close gross design proxy，不得冒充 20C next-open、stateful、cash-inclusive net NAV。

每个 selected row 必须记录唯一 outcome resolution：

```text
valid_mark
suspension_carry_mark
delisting_minus_one
unknown_bridge_arm_month_not_evaluable
```

Required output：

```text
historical/outcome_resolution_audit.csv.gz
```

### 7.4 Normalized volume

```text
source_volume_unit == shares -> normalized_volume_shares = volume
source_volume_unit == hands  -> normalized_volume_shares = volume * 100
unknown unit -> missing and unit gate fail for affected row
zero current volume -> TrendPV volume signal missing
```

### 7.5 Stable keys

```text
daily key = (instrument, date)
monthly feature key = (instrument, decision_date, arm_id, semantic_track)
primary 1m bucket return key = (decision_date, arm_id, semantic_track, return_semantics, weighting, bucket_count, bucket_id)
overlapping portfolio return key = (evaluation_month, arm_id, semantic_track, weighting, bucket_count, bucket_id, holding_month_n)
```

重复 key 必须 fail closed。

---

## 8. Frozen formulas

### 8.1 P0 Total Momentum 12-1

对 decision month `t`：

```text
formation_months = t-11, ..., t-1 exactly 11 complete monthly returns
r(i,m) = project_conservative_primary resolved monthly return
TMOM_12_1(i,t) = product(1 + r(i,m) for m in formation_months) - 1
just-completed decision month t is excluded
minimum_observation = exactly 11 nonmissing returns
```

高分预期高收益。不得改成 12-0、6-1 或最佳窗口。

### 8.2 P1 TrendPV signals

窗口固定：

```text
L = {3, 5, 10, 20, 50, 100, 200, 300, 400} exchange sessions
MP(i,L,t) = mean(close over exact L sessions ending t) / close(i,t)
MV(i,L,t) = mean(normalized_volume_shares over exact L sessions ending t) / normalized_volume_shares(i,t)
```

得到 18 个 predictors：9 price + 9 volume。禁止 log-transform、winsorize、rank-transform、删除窗口或新增窗口。

### 8.3 P1 monthly cross-sectional coefficient path

月 `m` 的 realized coefficient 只能使用月 `m-1` signals 解释月 `m` return：

```text
r(i,m) = beta_0(m)
         + sum_L beta_P(L,m) * MP(i,L,m-1)
         + sum_L beta_V(L,m) * MV(i,L,m-1)
         + epsilon(i,m)
```

Coefficient fit population 必须因果冻结：

```text
membership_asof = last project decision close in m-1
row_selection = U_project membership and semantic-track eligibility known at m-1 close
predictor_asof = m-1 close
project-strict response = month-m project_conservative_primary resolved return
paper-fill diagnostic response = month-m paper_qfq_complete_case_sensitivity return
unknown bridge may remove a preselected regression row but may not add a row
month-m universe membership, month-end status, size rank or board state may not select the fit population
```

必须逐月保存 `m-1 selected N`、`month-m return-complete N`、各 exclusion reason 和最终 fit row keys。不得使用
月 `m` 末仍留在 U_project 的条件形成 survivorship intersection。

冻结：

```text
fit_intercept = true
numeric_dtype = float64
predictor_order = intercept, MP_L ascending L, MV_L ascending L
estimator = numpy.linalg.lstsq(X, y, rcond=1e-12)
sample_weight = none
winsorization = none
minimum_complete_cross_section_n = 190
minimum_complete_cross_section_n_source = 10 observations per 19 fitted parameters; preoutcome numerical-stability heuristic
required_design_rank = 19 including intercept
rank_rule = lstsq returned rank == 19 under frozen rcond
rank_deficient_month = coefficient unavailable; do not drop predictors
zero return = retained
```

系数预测：

```text
lambda = 0.02
let complete realized coefficient months be m_1 < m_2 < ...
ema_state_1 = realized_beta(m_1)
forecast_beta_for_(m_1+1) = ema_state_1
for j >= 2: ema_state_j = (1-lambda) * ema_state_(j-1) + lambda * realized_beta(m_j)
forecast_beta_for_(m_j+1) = ema_state_j
coefficient_burn_in = first 38 complete realized-coefficient months after 400-session signal readiness
first_score_allowed = decision month m_38 after ema_state_38 incorporates realized_beta(m_38)
```

某月 coefficient unavailable 时：

```text
EMA state is not advanced
burn-in complete-month count is not advanced
no imputation from future month
after burn-in, score may use the retained last state and must report coefficient_staleness_calendar_month_n
```

Trend score：

```text
TrendPV(i,t) = sum_L forecast_beta_P(L,t+1) * MP(i,L,t)
             + sum_L forecast_beta_V(L,t+1) * MV(i,L,t)
```

高 score 预期高下一月 return。

必须另外保存、但不得作为择优 arm：

```text
price_component = sum_L forecast_beta_P * MP
volume_component = sum_L forecast_beta_V * MV
total_score = price_component + volume_component
```

### 8.4 P2 full Trend exact route

注册公式：排除最小 30%、Size 2 × EP 3 × Trend 3、18 个 VW portfolios、high six minus low six。

机械状态：

```text
wide_pit_market_cap_gate = fail
pit_ep_timing_gate = fail
paper_universe_gate = fail
paper_exact_history_support_gate = fail
P2 run_status = registered_not_run
```

不得用 U_project market cap、静态 E/P 或 raw TrendPV decile 冒充 P2。

### 8.5 P4 sequential market-only residual adaptation

对每个 instrument、每个 residual month `s`：

```text
estimation_months = s-36, ..., s-1 exactly 36 complete paired stock/CSI300 months
stock return semantics = project_conservative_primary resolved monthly return
benchmark return semantics = complete CSI300 month-end close ratio
r_i,u = alpha_i,s + beta_i,s * r_mkt,u + error_i,u
fit_intercept = true
numeric_dtype = float64
predictor_order = intercept, CSI300_return
estimator = numpy.linalg.lstsq(X, y, rcond=1e-12)
required_design_rank = 2 under frozen rcond
sample_weight = none
minimum_observation = exactly 36
```

用只截至 `s-1` 的系数计算当月 residual：

```text
e_R2(i,s) = r_i,s - (alpha_i,s + beta_i,s * r_mkt,s)
```

Decision month `t` 的 score：

```text
score_months = t-11, ..., t-1 exactly 11 R2 residual months
R2_score(i,t) = mean(e_R2) / sample_std(e_R2, ddof=1)
zero or nonfinite std -> missing
```

高 score 预期高下一月 return。不得用 `r_i,s - r_mkt,s` 替代回归残差，不得使用 full-sample beta。

### 8.6 P5 two-stage size/board residual adaptation

P5 必须先逐行复用 P4 的 `e_R2(i,s)`，然后在 residual month `s` 做横截面 ridge：

```text
target = e_R2(i,s)
predictors = lagged log(total_market_cap_cny) as of s-1
             + frozen EP19-2025 eligible multi-hot board columns
```

Ridge fit population 与标准化总体必须冻结为：

```text
membership_asof = last project decision close in s-1
causal_row_selection = U_project membership and lagged size known at s-1 close
board_snapshot_date = 2025-01-02
board_known_by_predictor_asof = board_snapshot_date <= membership_asof
board_snapshot_age_month_n = signed whole calendar-month distance from 2025-01 to residual month s
full_history_retrospective_proxy may use board_known_by_predictor_asof=false only with look-ahead flag
target_availability = e_R2(i,s) complete after the causal row selection
month-s universe membership, status or size rank may not add/select rows
standardization_fit_population = exact final ridge fit row set in residual month s
ridge_fit_row_set = residual_output_row_set
```

`e_R2(i,s)` 是当月被解释 target，可以在 historical outcome authorization 后读取；但不得用 `s` 月末 universe/status
选择横截面。每月必须输出 preselected N、target-complete N、final fit N、exclusion reason、标准化均值/标准差、最终
row-key hash、`board_snapshot_age_month_n`、`board_known_by_predictor_asof` 与 `formation_contains_pre_snapshot_residual`。

Board transform 继承 20A：

```text
binary membership
board must have >=10 U_project-overlap instruments
all-zero vector for valid absent instruments
drop exact duplicate columns; retain lexicographically smallest board_ts_code
standardize every nonconstant predictor within residual month using population std ddof=0
constant predictor rule = population_std <= 1e-12; exclude from that month fit and record
no primary-industry assignment
no outcome-based board selection
```

Ridge：

```text
numeric_dtype = float64
predictor_order = lagged_log_market_cap, then retained board_ts_code lexicographic ascending
estimator = sklearn.linear_model.Ridge(alpha=1.0, fit_intercept=true, solver="svd", copy_X=true)
sample_weight = none
continuous size preprocessing = log then within-month z-score
board preprocessing = within-month z-score for nonconstant binary columns
zscore_ddof = 0
intercept is not penalized
minimum_complete_cross_section_n = 100
minimum_complete_cross_section_n_source = preoutcome board-diagnostic stability floor; P5 is non-promoting in 20B
missing lagged size -> row unavailable
```

```text
e_R3(i,s) = ridge residual
R3_score(i,t) = mean(e_R3 over t-11...t-1) / sample_std(e_R3, ddof=1)
formation_contains_pre_snapshot_residual(i,t) = any(board_known_by_predictor_asof(s) == false for s in t-11...t-1)
fully_post_snapshot_score(i,t) = not formation_contains_pre_snapshot_residual(i,t)
```

必须输出 `P5_minus_P4` score/return difference，但只作 board-attribution diagnostic。P5 historical result 不得改变
20A preoutcome-selected residual primary，也不得独自授权 20C。

### 8.7 P3 exact CH-3 residual route

注册 36-month market/size/value residual + 12-1 score，但由于 risk-free、CH-3 vintage、U_paper 和 exact history gates
失败：

```text
P3 run_status = registered_not_run
```

P4/P5 不得升级 P3。

### 8.8 P6 Low Vol comparator

```text
lookback = preceding 36 complete monthly qfq return proxies through decision month t
return semantics = project_conservative_primary resolved monthly return
VOL36(i,t) = sample_std(r_i,t-35...t, ddof=1)
minimum_observation = exactly 36
lower score is expected to have higher next-month return than high-vol bucket
```

不得扫描 VOL12/VOL60 后择优；其他 lookback 属于 20E/新 contract。

---

## 9. Sorting、weighting 与 holding contract

### 9.1 Bucket assignment

每个 arm × decision month × semantic track 分别形成：

```text
primary bucket_count = 10
secondary descriptive bucket_count = 5
```

先按 signal ascending，再按 instrument ascending 打破 ties：

```text
rank = 1..N
bucket_k = 1 + floor((rank-1) * k / N)
```

P0/P1/P4/P5：bucket k 为 high-score；P6：bucket 1 为 low-vol favorable bucket。

```text
minimum_signal_eligible_n_for_decile = 100
minimum_bucket_n = 10
```

不满足则该 month-arm track 不可评价，不得降为 quintile 后冒充 primary。

### 9.2 Weighting

固定并行输出：

```text
EW = equal weight within bucket
VW = weight by PIT total_market_cap_cny known at decision close
target weights are frozen at decision close before t+1 outcome access
```

VW missing cap rows不得回填或切 EW；分别报告 denominator/retention。Primary formula-direction readout 使用 EW；VW 只作
paper/capacity morphology diagnostic。

### 9.3 Return portfolios

```text
paper_qfq_complete_case_sensitivity bucket_return = weighted mean among complete rows after explicit diagnostic renormalization
project_conservative_primary bucket_return = sum(ex_ante_target_weight * resolved_next_month_return)
project_conservative_primary unknown bridge in any positive target-weight row -> bucket-month not evaluable
high_minus_low = favorable extreme bucket - unfavorable extreme bucket
top_minus_middle = favorable extreme - middle bucket(s)
```

P6 的 favorable extreme 是 low-vol bucket 1；其他 arms 是 high-score bucket k。

### 9.4 Holding horizons

Primary horizon 对所有 runnable arms 固定为 1 month。

Residual paper sensitivity 可另外输出 3/6/12-month overlapping holding returns，但：

- 必须在 preoutcome registry 中注册；
- 使用下述唯一 overlapping-cohort formula；
- 只作 appendix diagnostic；
- 不进入 paper-sort gate、positive-exposure gate、20C 授权或 arm 选择；
- 不允许报告表现最佳 horizon 而隐去其他 horizon。

对 `H in {3,6,12}`：

```text
cohort_formation_date = decision month t
cohort_active_evaluation_months = t+1, ..., t+H
within_cohort instrument weights = frozen EW or VW weights at formation t; no constituent replacement
portfolio evaluation month q starts only when exactly H registered cohorts are active
capital weight per active cohort = 1/H
monthly overlapping return(q,H) = sum(active cohort capital weight * resolved cohort monthly return in q)
return_semantics = project_conservative_primary
unknown bridge in any positive-weight active cohort -> q,H portfolio month not evaluable
```

不得把 close-to-close `H` 月累计收益直接当作 overlapping monthly portfolio return。Required sealed evidence：

```text
historical/residual_overlapping_cohort_assignment.parquet
historical/residual_overlapping_portfolio_returns.csv.gz
```

row key：

```text
(arm_id, semantic_track, weighting, bucket_count, bucket_id, holding_month_n,
 cohort_formation_date, evaluation_month, instrument_id)
```

至少包含 `cohort_age_month`、`within_cohort_target_weight`、`cohort_capital_weight`、`resolved_monthly_return`、
`outcome_resolution` 和 `portfolio_month_evaluable`。

TrendPV、TMOM、LowVol 不新增 horizon scan。

---

## 10. Historical evidence role、folds 与统计量

### 10.1 Arm-specific 与 common decision months

每个 arm 必须先按 outcome-free 的理论 readiness calendar 冻结时间折；另外冻结 P1 project-strict 与 P4 的
common-month calendar：

```text
scheduled_arm_months = calendar months where fixed warm-up/lookback is theoretically complete and next-month label window exists
common_months = intersection(P1_project_strict_scheduled_arm_months, P4_scheduled_arm_months)
ordered ascending and split before any return value is inspected
early = first floor(N/2)
late = remaining months

P1_minimum_arm_month_n = 48
P1_minimum_fold_month_n = 24
P4_minimum_arm_month_n = 60
P4_minimum_fold_month_n = 30
minimum_common_month_n = 48
minimum_common_fold_month_n = 24
```

这些不是运行后按结果放宽的门。Preoutcome calendar feasibility 必须披露：按当前冻结历史边界，400 sessions + 38
complete coefficient months 后 P1 理论可用月数上限约 55、时间折约 27/28，因此原统一 `60/30` 对 P1 机械不可达；
`48/24` 冻结为至少四年总样本、每折至少两年的 design-feasibility floor，只授权较低功效的 diagnostic，不形成
support。该值来自 outcome-free calendar feasibility，不来自 return、spread 或显著性。P4 保留原 `60/30`，不得因 P1
历史较短而同步降门。按修正后的 decision-month `12-1 = t-11...t-1`，P4 理论最早 decision 约为 2021-01、截至
2026-04 理论上限约 64 个月；preoutcome 必须从实际 calendar 重算并禁止复用旧 `t-12...t-2` 的 63-month schedule。

`preoutcome/statistical_and_fold_freeze.csv` 必须为 P1、P4 和 common calendar 分别保存：

```text
arm_or_calendar_id
first_formula_ready_month
last_label_complete_decision_month
theoretical_max_month_n
observed_nonoutcome_ready_month_n
minimum_arm_month_n
minimum_fold_month_n
early_start
early_end
late_start
late_end
threshold_source
outcome_used_for_threshold
```

硬约束：`outcome_used_for_threshold=false`。

实际 coefficient、signal、decile 或 label 不完整只会使对应 scheduled month 在冻结 fold 内变为 `evaluable=false`；不得删除该月后
重新切分 early/late。各 fold 的 minimum month floor 按该固定 fold 内最终 `evaluable=true` 的月份数判断。

Fold boundary 只能由 dates 与理论 formula readiness 决定，不能由 realized return、missing-return pattern、spread、方向或
显著性移动。
若 common-month 门失败，只阻断 P1-vs-P4 paired comparison，不得掩盖任一 arm 独立且完整的设计门。

### 10.2 Required statistics

每个 arm × signal track × return semantics × weighting × bucket/horizon 至少输出：

```text
month_n
mean_monthly_return
median_monthly_return
monthly_volatility
annualized_mean = 12 * mean_monthly_return
annualized_volatility = sqrt(12) * monthly_volatility
annualized_sharpe = sqrt(12) * mean / volatility
positive_month_rate
p10
p50
p90
ES10_loss
max_drawdown_of_compounded_gross_series
Newey_West_lag = max(1, floor(4*(month_n/100)^(2/9)))
HAC_t_stat
HAC_two_sided_p_value
nominal_95pct_CI
```

所有 CI/p-value 标记：

```text
inference_role = design_only_not_support
cross_sectional_row_independence_claim = false
```

20B 不使用统计显著性作为 pass/fail；不把 paper sample reported t-stat 当本地 floor。

### 10.3 Monotonicity

每月输出：

```text
Spearman(bucket_id, bucket_return)
favorable_extreme_minus_unfavorable_extreme
favorable_extreme_minus_middle
```

汇总：

```text
mean spread
median spread
positive spread month rate
mean bucket-return Spearman
full-sample bucket means
```

### 10.4 Dominance audit

```text
monthly_contribution = spread_m / sum(abs(spread_m))
max_abs_month_contribution
top3_abs_month_contribution
leave_one_month_out_mean_min
leave_one_instrument_out sensitivity for bucket-level pooled stock returns
```

这些是 fragility diagnostics；不得删除支配月份/股票后重报“修复结果”。

### 10.5 Paper benchmark context

报告可以并列论文中的代表性统计量，但必须带：

```text
source_id
paper_sample
paper_universe
paper_weighting
paper_holding
paper_value
local_value
direct_comparability = false
reason = sample/universe/data/return semantics differ
```

不得使用“未达到论文 Sharpe”作为失败门，也不得用同方向点估计声称 exact replication passed。

---

## 11. Positive-exposure、paper-sort diagnostics 与 20C generation gate

### 11.1 Formula materialization gates

```text
P1_formula_integrity_gate =
    exact windows and units pass
    and causal m-1 coefficient-fit population pass
    and OLS/EMA timing pass
    and no future coefficient or return leakage

P1_paper_fill_formula_integrity_gate =
    paper-fill carry rules and volume-record floor pass
    and causal m-1 coefficient-fit population pass
    and paper_qfq_complete_case_sensitivity response semantics pass
    and OLS/EMA timing pass
    and no future coefficient or return leakage

P1_sample_support_gate =
    project-strict evaluable_month_n >= 48
    and early_month_n >= 24
    and late_month_n >= 24

P1_direction_metric_completeness_gate =
    project_conservative_primary full/early/late EW direction metrics are finite

P1_materialization_gate =
    P1_formula_integrity_gate
    and P1_sample_support_gate
    and P1_direction_metric_completeness_gate

P4_formula_integrity_gate =
    exact 36-month sequential regressions pass
    and exact 11 residual score months pass
    and no future regression coefficient or membership leakage

P4_sample_support_gate =
    evaluable_month_n >= 60
    and early_month_n >= 30
    and late_month_n >= 30

P4_direction_metric_completeness_gate =
    project_conservative_primary full/early/late EW direction metrics are finite

P4_materialization_gate =
    P4_formula_integrity_gate
    and P4_sample_support_gate
    and P4_direction_metric_completeness_gate

P5_materialization_gate =
    P4_formula_integrity_gate
    and board transform/ridge pass
    and causal s-1 membership/lagged-size row selection pass
    and look-ahead scope flags complete

P5_fully_post_snapshot_materialization_gate =
    P5_materialization_gate
    and fully_post_snapshot_score_month_n > 0
    and all included score formation residuals have board_known_by_predictor_asof == true
```

### 11.2 Paper-sort morphology gates

只使用 1-month EW high-minus-low、project-strict signal semantics 与 `project_conservative_primary` return semantics：

```text
P1_paper_sort_direction_gate =
    P1_materialization_gate
    and P1_mean_spread_full > 0
    and P1_mean_spread_early > 0
    and P1_mean_spread_late > 0

P4_paper_sort_direction_gate =
    P4_materialization_gate
    and P4_mean_spread_full > 0
    and P4_mean_spread_early > 0
    and P4_mean_spread_late > 0

P1_paper_fill_sort_diagnostic_gate =
    P1_paper_fill_formula_integrity_gate
    and paper_fill_evaluable_month_n >= 48
    and paper_fill_early_month_n >= 24
    and paper_fill_late_month_n >= 24
    and paper_fill_mean_spread_full > 0
    and paper_fill_mean_spread_early > 0
    and paper_fill_mean_spread_late > 0

P5_retrospective_sort_diagnostic_gate =
    P5_materialization_gate
    and retrospective_evaluable_month_n >= 60
    and retrospective_early_month_n >= 30
    and retrospective_late_month_n >= 30
    and retrospective_mean_spread_full > 0
    and retrospective_mean_spread_early > 0
    and retrospective_mean_spread_late > 0
```

前两个 primary gate 与后两个 auxiliary diagnostic gate 都只判断 paper-style cross-sectional ranking morphology。它们不是
positive-beta、alpha 或 20C generation 的必要条件；高分组绝对收益为正但 high-minus-low 不为正时，不得因此拒绝正
beta 候选。任何 auxiliary full/early/late metric missing/nonfinite 时，对应 diagnostic gate=false 并记录原因。

### 11.3 Positive-exposure design gates

只使用 1-month EW favorable extreme bucket 的**绝对** gross return、project-strict signal semantics 与
`project_conservative_primary` return semantics：

```text
P1_positive_exposure_design_gate =
    P1_materialization_gate
    and P1_favorable_extreme_mean_full > 0
    and P1_favorable_extreme_mean_early > 0
    and P1_favorable_extreme_mean_late > 0

P4_positive_exposure_design_gate =
    P4_materialization_gate
    and P4_favorable_extreme_mean_full > 0
    and P4_favorable_extreme_mean_early > 0
    and P4_favorable_extreme_mean_late > 0
```

这里的零门槛是 cash gross-return hurdle，不是 all-stock、low bucket、market、size、volatility 或 matched-alpha hurdle。
允许低分组收益更高；scale independence 与 incremental alpha 仍不作为门。该 gate 只能表示
`historical_positive_exposure_candidate_design_only`，不能写成 positive beta supported 或 deployable。

P5、P0、P6、paper-fill track、VW 或 residual multi-horizon sensitivities 不得进入 positive-exposure gate，也不得独自授权
20C。

### 11.4 20C requirement generation

```text
20C_requirement_generation_authorized =
    upstream_20a_integrity_gate == pass
    and R2_family_bridge_role_resolution_gate == pass
    and preoutcome_manifest_hash_gate == pass
    and historical_run_authorization_gate == pass
    and outcome_firewall_gate == pass
    and historical_manifest_hash_gate == pass
    and (
        P1_positive_exposure_design_gate
        or (P4_residual_family_bridge_authorizer and P4_positive_exposure_design_gate)
    )

20C_execution_authorized = false
policy_training_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

即使 20C generation 获授权，20C 必须同时运行 C2、R2、R3、C0、TMOM、LowVol、B2 month-end 与 causal VOL60 trim；
20B 不得根据历史 return 删除 frozen comparator 或改写 20A residual primary。

---

## 12. Exact vs adaptation verdict

20B 必须输出：

```text
exact_replication_reachable = false
P2_exact_status = exact_replication_not_evaluable_data_gap
P3_exact_status = exact_replication_not_evaluable_data_gap
P1_claim = raw_TrendPV_U_project_adaptation
P4_claim = market_only_residual_momentum_U_project_adaptation
P5_claim = market_size_static_board_residual_U_project_adaptation
local_replication_passed_phrase_allowed = false
```

Paper-fill P1 若 paper spread 为正，只能称 `paper_semantics_sort_direction_reproduced_design_only`；P1 project-strict/P4
若 favorable bucket 绝对 gross return 门通过，只能称 `historical_positive_exposure_candidate_design_only`。任何 spread
结果都不得替代 positive-exposure gate，任何 positive-exposure design 结果也不得升级为 support。

Material waiver 边界：

- Trend main working paper 本地未缓存，不得声称 local full-text hash；
- MA paper 不属于 20B runnable arm；
- waiver 不影响 P2 exact 不可运行状态；
- formula page/equation anchors 继承人工核验，不新增 paper claim。

---

## 13. Terminal states

固定优先级：

```text
1. 20B_outcome_firewall_violated
2. 20B_manifest_or_hash_blocked
3. 20B_upstream_contract_blocked
4. 20B_preoutcome_registry_inconsistent
5. 20B_historical_run_not_authorized
6. 20B_data_or_formula_materialization_blocked
7. 20B_underpowered_design_diagnostic
8. 20B_positive_exposure_candidate_identified_design_only
9. 20B_paper_sort_or_semantics_only_design_only
10. 20B_mixed_direction_design_only
11. 20B_positive_exposure_not_identified_design_only
```

定义：

```text
20B_outcome_firewall_violated:
    any unauthorized outcome access, post-boundary outcome, tuning read or forward outcome is detected.

20B_manifest_or_hash_blocked:
    outcome firewall has not failed, but any required upstream/preoutcome/historical/final manifest or hash fails.

20B_upstream_contract_blocked:
    hashes pass, but required 20A decision, lineage, R2 universe resolution, P4 family-bridge role resolution or Trend warm-up resolution fails.

20B_preoutcome_registry_inconsistent:
    upstream passes, but any frozen arm/formula/calendar/universe/fit-population/bucket/statistical registry is incomplete or inconsistent.

20B_historical_run_not_authorized:
    preoutcome bundle passes, but no valid human authorization bound to its exact hash predates outcome access.

P1_partial_underpowered = P1_formula_integrity_gate and not P1_sample_support_gate
P4_partial_underpowered = P4_formula_integrity_gate and not P4_sample_support_gate
partial_formula_failure = xor(P1_formula_integrity_gate, P4_formula_integrity_gate)
P1_metric_materialization_failure =
    P1_formula_integrity_gate and P1_sample_support_gate and not P1_direction_metric_completeness_gate
P4_metric_materialization_failure =
    P4_formula_integrity_gate and P4_sample_support_gate and not P4_direction_metric_completeness_gate
partial_metric_materialization_failure =
    (P1_metric_materialization_failure or P4_metric_materialization_failure)
    and (P1_materialization_gate or P4_materialization_gate)
partial_underpowered =
    (P1_partial_underpowered or P4_partial_underpowered)
    and (P1_materialization_gate or P4_materialization_gate)
global_underpowered =
    (P1_formula_integrity_gate or P4_formula_integrity_gate)
    and not P1_materialization_gate
    and not P4_materialization_gate
    and not (P1_metric_materialization_failure or P4_metric_materialization_failure)

global_metric_materialization_failure =
    not P1_materialization_gate
    and not P4_materialization_gate
    and (P1_metric_materialization_failure or P4_metric_materialization_failure)

primary_materialized_any = P1_materialization_gate or P4_materialization_gate
primary_positive_exposure_any =
    P1_positive_exposure_design_gate
    or (P4_residual_family_bridge_authorizer and P4_positive_exposure_design_gate)

P1_partial_positive =
    P1_materialization_gate
    and P1_favorable_extreme_mean_full > 0
    and not P1_positive_exposure_design_gate

P4_partial_positive =
    P4_materialization_gate
    and P4_favorable_extreme_mean_full > 0
    and not P4_positive_exposure_design_gate

project_partial_positive_any = P1_partial_positive or P4_partial_positive
auxiliary_sort_positive_any =
    P1_paper_sort_direction_gate
    or P4_paper_sort_direction_gate
    or P1_paper_fill_sort_diagnostic_gate
    or P5_retrospective_sort_diagnostic_gate

all_materialized_primary_full_nonpositive =
    primary_materialized_any
    and (not P1_materialization_gate or P1_favorable_extreme_mean_full <= 0)
    and (not P4_materialization_gate or P4_favorable_extreme_mean_full <= 0)

20B_data_or_formula_materialization_blocked:
    historical run is authorized,
    and (
        (not P1_formula_integrity_gate and not P4_formula_integrity_gate)
        or global_metric_materialization_failure
    ).
    A failure in only one arm is a partial flag and may not mask the other complete arm.

20B_underpowered_design_diagnostic:
    global_underpowered == true.
    Underpower in only one arm is a companion flag and may not override a complete arm result.

20B_positive_exposure_candidate_identified_design_only:
    primary_positive_exposure_any == true;
    authorizes 20C requirement generation only.

20B_paper_sort_or_semantics_only_design_only:
    primary_positive_exposure_any == false
    and project_partial_positive_any == false
    and auxiliary_sort_positive_any == true;
    does not authorize 20C.

20B_mixed_direction_design_only:
    primary_positive_exposure_any == false
    and project_partial_positive_any == true;
    no tuning or repair; 20C generation remains false.

20B_positive_exposure_not_identified_design_only:
    primary_positive_exposure_any == false
    and project_partial_positive_any == false
    and auxiliary_sort_positive_any == false
    and all_materialized_primary_full_nonpositive == true.
```

比较规则固定为 `>0` versus `<=0`；精确 0 归入 nonpositive。任何用于上述布尔量的 full/early/late metric 若 missing/nonfinite，
对应 arm 的 materialization gate 必须为 false，不得把 missing 当 false 或 0。按 priority 1–11 首个为 true 的状态取值；
在状态 6/7 未触发时，8–11 必须恰有一个为 true。

Priority 6/7 是**全局**失败态；`partial_formula_failure`、`partial_metric_materialization_failure`、
`P1_partial_underpowered`、`P4_partial_underpowered` 与 `partial_underpowered` 必须作为 decision flags 同时报告。只要另一 arm 完整，状态判断继续到
8–11，不得被局部失败提前截断。State 8 优先于 9–11；state 9 只有在 state 8 不成立时才可使用。

所有 terminal state 都必须同时包含：

```text
historical_sample_role = design_contaminated_historical
historical_support_claim_allowed = false
exact_replication_reachable = false
```

---

## 14. Required artifacts

### 14.1 Preoutcome bundle

```text
preoutcome/resolved_config.yaml
preoutcome/upstream_20a_integrity_audit.csv
preoutcome/upstream_metadata_resolution_registry.csv
preoutcome/input_artifact_audit.csv
preoutcome/arm_and_track_registry.csv
preoutcome/formula_execution_registry.csv
preoutcome/decision_calendar_freeze.csv
preoutcome/universe_and_denominator_freeze.csv
preoutcome/trendpv_ols_ema_initialization_freeze.csv
preoutcome/residual_regression_and_score_freeze.csv
preoutcome/board_ridge_transform_freeze.csv
preoutcome/outcome_resolution_semantics_freeze.csv
preoutcome/bucket_weighting_holding_freeze.csv
preoutcome/statistical_and_fold_freeze.csv
preoutcome/exact_route_status_freeze.csv
preoutcome/outcome_access_audit.csv
preoutcome/preoutcome_contract_20b.json
preoutcome/20B_preoutcome_contract.md
preoutcome/preoutcome_manifest_20b.json
preoutcome/preoutcome_output_hashes_20b.json
```

### 14.2 Historical run artifacts

```text
historical/human_historical_run_authorization.json
historical/monthly_signal_support.csv
historical/trendpv_coefficient_path.csv.gz
historical/trendpv_component_diagnostic.csv
historical/residual_time_series_regression_audit.csv.gz
historical/residual_board_ridge_audit.csv.gz
historical/instrument_month_signal_bucket_assignment.parquet
historical/residual_overlapping_cohort_assignment.parquet
historical/residual_overlapping_portfolio_returns.csv.gz
historical/outcome_resolution_audit.csv.gz
historical/monthly_bucket_returns.csv.gz
historical/sort_monotonicity_readout.csv
historical/arm_summary_statistics.csv
historical/early_late_direction_readout.csv
historical/month_instrument_dominance_audit.csv
historical/p4_p5_board_attribution_readout.csv
historical/paper_benchmark_context.csv
historical/exact_route_status.csv
historical/outcome_access_audit.csv
historical/historical_manifest_20b.json
historical/historical_output_hashes_20b.json
```

### 14.3 Final artifacts

```text
20B_trendpv_residual_momentum_design_and_replication_diagnostic_decision.csv
20B_trendpv_residual_momentum_design_and_replication_diagnostic_report.md
manifest_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json
output_hashes_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json
```

### 14.4 Stable output rules

- CSV 固定列顺序和 sort keys；
- bool 只用 `true/false`；
- missing 为空，不得用 0；
- float 至少 10 位有效数字；
- 所有 path 为 repository-relative；
- 大 panel 使用 gzip/parquet cache，不把任意行序列当 evidence unit；
- report 数字必须来自 machine-readable artifacts；
- 失败、underpowered、missing arms 仍必须物化行。

---

## 15. Key output schemas

### 15.1 `monthly_signal_support.csv`

```text
run_id
arm_id
semantic_track
decision_date
denominator_n
signal_eligible_n
decile_eligible_n
next_month_complete_n
project_label_resolved_n
project_unknown_bridge_n
coverage_rate
coefficient_complete
warmup_complete
lookahead_proxy_scope
board_snapshot_age_month_n
formation_contains_pre_snapshot_residual
evaluable
missing_reason
```

### 15.2 `instrument_month_signal_bucket_assignment.parquet`

这是所有分桶收益、dominance、leave-one-instrument-out 与 EW/VW 复算的 sealed evidence table。至少包含：

```text
run_id
instrument_id
decision_date
label_month
arm_id
semantic_track
universe_eligible
signal_eligible
bucket_eligible
exclusion_reason
raw_signal
price_component
volume_component
residual_component
bucket_count
bucket_id
bucket_role
ex_ante_ew_target_weight
ex_ante_vw_target_weight
paper_ew_analysis_weight
paper_vw_analysis_weight
project_ew_analysis_weight
project_vw_analysis_weight
paper_proxy_next_month_return
project_resolved_next_month_return
outcome_resolution
project_bucket_month_evaluable
lookahead_proxy_scope
board_snapshot_date
board_snapshot_age_month_n
board_known_by_predictor_asof
formation_contains_pre_snapshot_residual
historical_sample_role
input_snapshot_hash
```

不适用的 component 为空，不得填 0。该表 row key 为
`(instrument_id, decision_date, arm_id, semantic_track, bucket_count)`，必须唯一；所有 primary 1-month summary 必须仅由本
sealed table 加对应 sealed coefficient/regression audits 复算，不得回读 raw outcome。3/6/12-month appendix 只从
`residual_overlapping_cohort_assignment.parquet` 复算。

每个 U_project denominator row 必须为注册的 `bucket_count=5` 与 `bucket_count=10` 各物化一行；不 eligible 时保留行，
`bucket_id/bucket_role/weights` 为空并填写唯一 exclusion reason。不得只输出最终入桶或 return-complete 的幸存样本。

`outcome_resolution_audit.csv.gz` 至少包含 `(instrument_id, decision_date, label_end, source_last_trade_date,
security_status, raw_qfq_return, outcome_resolution, resolved_return, affected_arm_bucket_keys, resolution_source_hash)`；
同一 instrument-decision 只能有一个 project resolution。

### 15.3 `residual_overlapping_cohort_assignment.parquet`

```text
run_id
arm_id
semantic_track
weighting
bucket_count
bucket_id
bucket_role
holding_month_n
cohort_formation_date
evaluation_month
cohort_age_month
instrument_id
within_cohort_target_weight
cohort_capital_weight
resolved_monthly_return
outcome_resolution
portfolio_month_evaluable
input_snapshot_hash
```

只允许 `holding_month_n in {3,6,12}`；每个 evaluable evaluation month 必须恰有 H 个 active cohorts，且每个 cohort 的
`cohort_capital_weight=1/H`。本表不得进入任何 gate。

`residual_overlapping_portfolio_returns.csv.gz` 是上述 cohort table 的唯一月度汇总，至少包含：

```text
arm_id
semantic_track
weighting
bucket_count
bucket_id
bucket_role
holding_month_n
evaluation_month
active_cohort_n
portfolio_month_evaluable
gross_overlapping_monthly_return
inference_role
```

硬约束：`active_cohort_n == holding_month_n` 才可评价，`inference_role=appendix_design_only_not_gate`。

### 15.4 `monthly_bucket_returns.csv.gz`

本表只保存 primary `holding_month_n=1` 的 decision-to-next-month bucket returns；不得混入 overlapping H-month
evaluation rows。

```text
run_id
arm_id
semantic_track
decision_date
holding_month_n
weighting
return_semantics
bucket_count
bucket_id
bucket_role
instrument_n
weight_sum
next_month_complete_n
valid_mark_n
suspension_carry_n
delisting_minus_one_n
unknown_bridge_n
bucket_month_evaluable
gross_bucket_return
historical_sample_role
inference_role
```

### 15.5 `sort_monotonicity_readout.csv`

```text
arm_id
semantic_track
return_semantics
weighting
bucket_count
holding_month_n
month_scope
month_n
favorable_extreme_mean
middle_mean
unfavorable_extreme_mean
favorable_minus_unfavorable_mean
favorable_minus_middle_mean
spread_positive_month_rate
mean_bucket_spearman
HAC_t_stat
HAC_p_value
inference_role
paper_sort_direction_gate
positive_exposure_design_gate
```

### 15.6 Decision schema

单行至少包含：

```text
run_id
contract_version
decision_state
primary_objective
incremental_alpha_required
upstream_20a_integrity_gate
R2_universe_resolution_gate
TrendPV_warmup_resolution_gate
R2_family_bridge_role_resolution_gate
preoutcome_manifest_hash_gate
historical_run_authorization_gate
outcome_firewall_gate
historical_manifest_hash_gate
final_manifest_hash_gate
P0_materialization_gate
P1_formula_integrity_gate
P1_paper_fill_formula_integrity_gate
P1_sample_support_gate
P1_direction_metric_completeness_gate
P1_materialization_gate
P2_run_status
P3_run_status
P4_formula_integrity_gate
P4_sample_support_gate
P4_direction_metric_completeness_gate
P4_materialization_gate
P5_materialization_gate
P5_fully_post_snapshot_materialization_gate
P6_materialization_gate
P1_project_strict_evaluable_month_n
P4_evaluable_month_n
P5_retrospective_evaluable_month_n
P5_fully_post_snapshot_score_month_n
P1_early_month_n
P1_late_month_n
P4_early_month_n
P4_late_month_n
P1_paper_sort_direction_gate
P4_paper_sort_direction_gate
P1_paper_fill_sort_diagnostic_gate
P5_retrospective_sort_diagnostic_gate
P1_mean_spread_full
P1_mean_spread_early
P1_mean_spread_late
P4_mean_spread_full
P4_mean_spread_early
P4_mean_spread_late
P1_favorable_extreme_mean_full
P1_favorable_extreme_mean_early
P1_favorable_extreme_mean_late
P4_favorable_extreme_mean_full
P4_favorable_extreme_mean_early
P4_favorable_extreme_mean_late
P1_positive_exposure_design_gate
P4_positive_exposure_design_gate
P4_arm_promotion_eligible
P4_residual_family_bridge_authorizer
P4_pass_does_not_change_residual_primary
primary_materialized_any
primary_positive_exposure_any
P1_partial_positive
P4_partial_positive
project_partial_positive_any
auxiliary_sort_positive_any
all_materialized_primary_full_nonpositive
partial_formula_failure
P1_metric_materialization_failure
P4_metric_materialization_failure
partial_metric_materialization_failure
P1_partial_underpowered
P4_partial_underpowered
partial_underpowered
global_underpowered
global_metric_materialization_failure
residual_primary_arm_frozen
residual_primary_changed_by_20B
exact_replication_reachable
historical_sample_role
historical_support_claim_allowed
20C_requirement_generation_authorized
20C_execution_authorized
policy_training_authorized
policy_replay_authorized
portfolio_optimization_authorized
deployment_authorized
preoutcome_bundle_hash
historical_bundle_hash
blocking_reasons
```

硬约束：

```text
residual_primary_arm_frozen = C3_RESMOM_R3_BOARD_ADAPTATION
residual_primary_changed_by_20B = false
P4_arm_promotion_eligible = false
P4_residual_family_bridge_authorizer = true
P4_pass_does_not_change_residual_primary = true
exact_replication_reachable = false
historical_support_claim_allowed = false
positive-exposure gates use project_conservative_primary only
20C_execution_authorized = false
all policy/optimization/deployment authorizations = false
```

---

## 16. Manifest 与 immutability

Preoutcome seal：

```text
1. write all required preoutcome artifacts
2. scan columns/paths for forbidden outcomes
3. write final preoutcome_manifest excluding itself and hash file
4. write preoutcome_output_hashes including manifest, excluding itself
5. preoutcome_bundle_hash = SHA256(bytes(preoutcome_output_hashes))
6. prohibit overwrite
```

Historical seal 与 final seal 使用同一规则。Historical authorization 必须包含：

```text
authorization_type = 20B_historical_design_outcome_read
authorized_at_utc
reviewer
preoutcome_bundle_hash
registered_arm_ids
registered_semantic_tracks
history_date_max
authorization_granted
```

Hash mismatch 时不得自动重建或继续：

```text
decision_state = 20B_manifest_or_hash_blocked
```

Seal 必须使用 transactional temporary directory：先写完整候选 bundle、复算全部 hash 并做双向验证，全部通过后才 atomic
rename 到 immutable output path。Final decision 可以预写 `final_manifest_hash_gate=pass`，但只有 transaction 验证成功才允许发布。

若任何 seal 验证失败：

```text
do not publish or mutate the candidate sealed decision
write failure/final_seal_failure.json outside the sealed bundle
failure record contains decision_state=20B_manifest_or_hash_blocked, stage, path, expected_hash, observed_hash
failure record is operational evidence, not a valid final result bundle
```

不得为了把 blocked state 写回 decision 而修改已参与 hash 的 decision CSV。

Finalize 必须记录：

```text
finalize_raw_input_read_count = 0
finalize_outcome_recompute_count = 0
```

---

## 17. Report contract

中文报告至少包含：

1. 一页 decision summary；
2. 正 beta、非 alpha 目标；
3. 20A bundle/hash 与 authorization lineage；
4. R2 universe、P4 family-bridge role 与 Trend warm-up metadata resolution；
5. P2/P3 exact registered-not-run 表；
6. P0/P1/P4/P5/P6 实际支持月份、股票数与 missingness；
7. Trend 18 signals、OLS coefficient path、38-month burn-in 与 price/volume component；
8. 月末决策 `12-1=t-11...t-1`、R2 sequential 36m regression与 residual score；
9. R3 two-stage ridge、board age、retrospective/mixed/fully-post-snapshot 三类 scope；
10. paper complete-case 与 project-conservative outcome resolution、停牌/退市/未知桥数量；
11. EW/VW decile/quintile morphology、favorable bucket 绝对 gross return、monotonicity 与 1-month spread；
12. 3/6/12 residual overlapping-cohort appendix 与不可用于 gate 的边界；
13. arm-specific 48/24 与 60/30 样本门、early/late、dominance、HAC design-only diagnostics；
14. 文献统计量与本地数值不可直接比较的原因；
15. P1/P4 paper-sort gates、positive-exposure design gates、P4 family bridge 与 20C generation authorization；
16. outcome access、outcome resolution 和 manifest 证据；
17. 所有 execution/policy/deployment authorization 仍为 false。

禁止标题/结论：

```text
local replication passed
OOS confirmed
positive beta supported
alpha discovered
deployable strategy
```

---

## 18. 测试要求

测试至少覆盖：

1. 20A freeze/final hashes 与固定 bundle hash 可复算；
2. 20A decision 只授权 requirement generation，不授权 20B execution；
3. 未签 historical authorization 时，历史 outcome 读取在文件 open 前失败；
4. forward/post-seal date 进入历史 run 时 fail closed；
5. EP19 outcome/report 不在 whitelist；
6. R2 `U_paper` inconsistency 被解析为 U_project adaptation，P4 只获 family-bridge authorization 且 promotion 恒 false；
7. Trend support 不复用错误的 97 months，按 400 sessions + 38 coefficients 重算；
8. Trend 9 个固定窗口和 18 predictors 完整；
9. Trend OLS 用 t-1 signal 解释 t return，fit population 只由 t-1 已知成员/eligibility 选择，score t 只预测 t+1；
10. OLS float64、predictor order、rcond、rank rule 可复算；
11. EMA lambda=0.02、首个 state、逐 complete-month update、38-month first-score 与 staleness 可复算；
12. paper-fill 与 project-strict tracks 不混 denominator；
13. hands/shares volume normalization、zero-volume 和 missing rule；
14. P2/P3 必须 registered-not-run 且 row_n=0；
15. P4 逐月 36m regression 不含当月，不能等价为减 market constant，且 float64/rcond/rank 可复算；
16. P0/P4/P5 在月末 decision t 都使用 `t-11...t-1` 并只跳过 t；P4 理论首月/64-month 上限可复算；
17. P5 必须复用 P4 residual 后再做 size/board ridge；
18. R3 predictor order、z-score ddof、constant rule、solver、alpha=1.0 与 float64 可复算；
19. P5 retrospective/mixed/fully-post-snapshot scope 按全部 11 个 residual months 判定；
20. P4 comparator 无论 P5 结果如何都保留；P4 pass 不改变 frozen R3 primary；
21. P6 固定 36m；
22. bucket exact-count、tie、ex-ante EW/VW target weights 可复算；
23. paper complete-case 不能进入 gate；project conservative 不得删除 incomplete row 后重权重；
24. suspension carry、delisting -1、unknown bridge whole bucket-month unavailable 与 20A 一致；
25. 3/6/12 residual sensitivity 使用恰好 H 个 active cohorts、1/H capital weight，且不进入 gate；
26. P1 `48/24`、P4 `60/30` 与 common `48/24` 门以及 early/late boundary 在 outcome read 前冻结；
27. HAC lag、dominance、LOMO 指标可复算且都是 design-only；
28. 任何显著性不能产生 support；
29. paper-sort gate 与 positive-exposure gate 分离，后者只用 EW 1m project-strict + project-conservative return；
30. P5、paper-fill、VW、P0/P6 不能独自授权 20C；
31. P4 只能通过 family-bridge field 参与 20C generation，不要求 high-minus-low 为正；
32. instrument-month 表复算全部 primary 1m；cohort 表与 overlapping portfolio return 表复算 3/6/12；
33. terminal truth table 对正、零、负、missing 穷尽且 8–11 恰一为 true；
34. global/partial formula、metric-materialization 与 underpowered 状态不互相遮蔽；
35. residual primary 不因 20B outcome 改变；
36. exact flags 恒 false；
37. 20C 只可生成 requirement，execution 恒 false；
38. preoutcome/historical/final manifests 各自防覆盖、hash 双向一致；
39. finalize raw read count=0；
40. report 所有数字来自 sealed tables；
41. 全部 policy/replay/optimization/deployment authorization 为 false。

推荐命令仅用于未来获明确实施授权后：

```bash
python experiments/pending/20_ohlcv_positive_beta_exposure_research/src/run_20b_trendpv_residual_momentum_design_and_replication_diagnostic.py \
  --config experiments/pending/20_ohlcv_positive_beta_exposure_research/configs/config_20b_trendpv_residual_momentum_design_and_replication_diagnostic.yaml \
  --stage preflight

python experiments/pending/20_ohlcv_positive_beta_exposure_research/src/run_20b_trendpv_residual_momentum_design_and_replication_diagnostic.py \
  --config experiments/pending/20_ohlcv_positive_beta_exposure_research/configs/config_20b_trendpv_residual_momentum_design_and_replication_diagnostic.yaml \
  --stage run-historical

python experiments/pending/20_ohlcv_positive_beta_exposure_research/src/run_20b_trendpv_residual_momentum_design_and_replication_diagnostic.py \
  --config experiments/pending/20_ohlcv_positive_beta_exposure_research/configs/config_20b_trendpv_residual_momentum_design_and_replication_diagnostic.yaml \
  --stage finalize

python -m pytest experiments/pending/20_ohlcv_positive_beta_exposure_research/tests/test_20b_trendpv_residual_momentum_design_and_replication_diagnostic.py -q
```

---

## 19. Paper lineage

20B 公式只来自 20A frozen registry 与以下论文；本节不新增可调参数：

1. Liu, Yang; Zhou, Guofu; Zhu, Yingzi. “Trend Factor in China: The Role of Large Individual Trading.”
   *Review of Asset Pricing Studies* 14(2), 348–380, 2024. DOI `10.1093/rapstu/raae003`。
   - 20A source ID：`trend_china_full_working_paper`（material waiver；无本地 hash）；
   - Internet appendix source ID：`trend_china_internet_appendix`；
   - appendix local SHA256：`5704faa6a07acd3c768a2ff233a4734a679f2e798f17668a78aeb8e4f182563b`；
   - relevant equations：1–7；400 sessions + 38 coefficient months。

2. Blitz, David; Huij, Joop; Martens, Martin. “Residual Momentum.” *Journal of Empirical Finance* 18(3),
   506–521, 2011. DOI `10.1016/j.jempfin.2011.01.003`。
   - 20A source ID：`residual_momentum_full_paper`；
   - local SHA256：`db0ebbbe9de1d46deccef39cc4160416a5df39fd46b5a5ca4045df5b3ec227ee`；
   - relevant definition：36-month factor regression, 12-1 standardized residual momentum, 1/3/6/12-month holdings。

3. Jansen, Maarten; Swinkels, Laurens; Zhou, Weili. “Anomalies in the China A-share Market.”
   *Pacific-Basin Finance Journal* 68, 101607, 2021. DOI `10.1016/j.pacfin.2021.101607`。
   - 20A source ID：`china_anomalies_full_paper`；
   - local SHA256：`f3a7452cff08c6ca7b2346e277b5918b8d77d7e7db25a9b7debf0aded7601729`。

4. Liu, Jianan; Stambaugh, Robert F.; Yuan, Yu. “Size and Value in China.” *Journal of Financial Economics*
   134(1), 48–69, 2019. DOI `10.1016/j.jfineco.2019.03.008`。
   - 20A source ID：`china_size_value_full_paper`；
   - local SHA256：`40178157c95564532881da380111f8cdaa042b1b3f41c8fa6caa53043cbeb347`；
   - exact CH-3 dependency remains unavailable in 20B。

5. Blitz, David; Hanauer, Matthias X.; van Vliet, Pim. “The Volatility Effect in China.”
   *Journal of Asset Management* 22, 338–349, 2021. DOI `10.1057/s41260-021-00218-0`。
   - 20A source ID：`china_low_vol_full_article`；
   - local SHA256：`a4bcf93229408898cf45f426d72e935e38a40d8be175f54e3a686f005b176c33`。

原论文 sample statistic 只作 context，不进入任何本地 gate。

---

## 20. Acceptance checklist

```text
[ ] 本 requirement 生成未读取任何新 outcome。
[ ] 20A immutable bundle/hash/authorization 被唯一绑定。
[ ] implementation 与 historical execution 仍为 false，等待用户明确授权。
[ ] 目标是正 beta；alpha/scale independence 均非门。
[ ] R2 universe、P4 family-bridge role 和 Trend warm-up metadata 已显式 resolution。
[ ] P2/P3 exact routes 注册但禁止运行。
[ ] P0/P1/P4/P5/P6 formulas、timing、missing、warm-up 完整；P0/P4/P5 的 12-1 均为 `t-11...t-1`。
[ ] Trend 400 sessions + 38 coefficient months，而不是 20A planning 97-month estimate。
[ ] R3 是 two-stage market residual then size/board ridge。
[ ] P5 retrospective/mixed/fully-post-snapshot scopes 按全部 11 个 formation residual months 判定。
[ ] pre-snapshot board proxy 不进入 20C generation gate。
[ ] positive-exposure primary outcome 是 1-month project-conservative gross bucket return；不是 stateful deployable return。
[ ] paper complete-case return 只作 diagnostic；停牌、退市、未知估值桥不静默删除并重权重。
[ ] EW/VW、decile/quintile 和 paper holding sensitivity 分工明确。
[ ] 所有历史 evidence 标 design_contaminated_historical / not support。
[ ] Trend coefficient fit rows 按 m-1 已知成员冻结；R3 membership/size rows 按 s-1 已知信息冻结，board knowledge 单独标记。
[ ] OLS/EMA/Ridge 的 dtype、排序、rcond/rank、z-score ddof、solver 与 seed/update path 完整冻结。
[ ] P1 使用预注册 `48/24` 低功效设计门；P4 保持 `60/30`；局部 underpower 不遮蔽另一 arm。
[ ] paper-sort gate 与 positive-exposure gate 分离；20C 不要求 high-minus-low 为正。
[ ] 20C gate 只用 P1/P4 project-strict EW 1m + project-conservative favorable bucket 绝对 gross return。
[ ] P4 只能授权 residual-family bridge，arm promotion 恒 false，R3 primary 不变。
[ ] instrument-month 表复算 primary 1m；overlapping-cohort 与 portfolio-return 表复算 3/6/12 appendix。
[ ] terminal truth table 对正/零/负/missing 穷尽，8–11 恰一为 true。
[ ] 20B 不改变 20A residual primary。
[ ] 20C 最多只获 requirement-generation authorization。
[ ] outcome firewall、stage seals 与 finalize-only-from-sealed-artifacts 完整。
[ ] 中文报告禁止 replication passed / OOS confirmed / deployable 等越权措辞。
```

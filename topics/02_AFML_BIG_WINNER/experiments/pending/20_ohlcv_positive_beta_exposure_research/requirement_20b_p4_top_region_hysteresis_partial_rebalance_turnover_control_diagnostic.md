# Requirement 20B-P4-TURNCTL：D8-D10 连续顶部区域、持仓缓冲、部分再平衡与换手上限诊断

> 文档状态：`v0_historical_replay_executed_execution_fidelity_failed`
>
> 生成日期：2026-07-17
>
> Experiment ID：`20_ohlcv_positive_beta_exposure_research`
>
> Phase ID：`20B_P4_TURNCTL`
>
> Run ID：`20B_P4_top_region_hysteresis_partial_rebalance_turnover_control_v0`
>
> Contract version：`20B_P4_TURNCTL_v0`
>
> Claim ceiling：`design_contaminated_portfolio_execution_feasibility_only`

## 0. 一页执行结论与不可协商边界

本 requirement 把两个问题严格拆开：

```text
prediction layer = 冻结 S0_SELECTED_FULL 连续分数、rank 与 bucket assignment
portfolio layer  = D8-D10 资本配比、旧持仓缓冲、部分再平衡、换手上限
```

本轮只检验：在不改变现有 Full 排序的前提下，能否用组合层状态机显著降低 D8 单桶换手，同时保留可审计的一部分 D8 事件弹性。

冻结研究身份：

```text
scored_model_id = S0_SELECTED_FULL
split = robustness
decision_month_n = 21
label_month_range = 2024-08 through 2026-04
portfolio_style = long_only_stateful_NAV_monthly_signal
candidate_entry_region = D8-D10
reference_cost = statutory_costs + 5bps_per_executed_side
sector_tilt_lambda = 0
hard_stop = none
leverage_allowed = false
short_allowed = false
unallocated_capital = cash
model_training_authorized = false
score_recomputation_authorized = false
bucket_recomputation_authorized = false
parameter_selection_authorized = false
deployment_authorized = false
historical_support_claim_allowed = false
true_out_of_sample_claim_allowed = false
```

预先指定、唯一进入正式 design-feasibility guardrails 的 primary policy：

```text
candidate pool = D8 + D9 + D10
capital mix = D8 40% / D9 30% / D10 30%
entry bucket floor = D8
exit bucket floor = D7
partial rebalance rho = 0.50
monthly planned one-way turnover cap = 0.40
reference cost = statutory costs + 5bps/side
```

`D8/D9/D10 = 1/3/1/3/1/3` 使用相同缓冲、`rho=0.50`、`cap=0.40` 作为预先指定 secondary policy，但不参与 primary gate 的替代或补选。

### 0.1 研究动机，不是新 outcome 真值

下表来自冻结成员与 close-to-close 毛收益的设计估算，不是本 requirement 的 stateful、成本后验证结果：

| 组合 | 月均目标换手 | 21月毛收益 | 5个事件月毛收益 | 解释 |
|---|---:|---:|---:|---|
| D8 单桶 | 80.37% | +54.45% | +13.14% | 弹性最高、换手极高 |
| D9+D10 各50% | 36.10% | +33.54% | -0.59% | 低换手、事件弹性不足 |
| D8/D9/D10 各1/3 | 31.11% | +40.35% | +3.85% | 换手最低、仍保留D8 |
| D8/D9/D10=40/30/30 | 35.96% | +41.73% | +4.76% | 更偏弹性 |
| D8/D9/D10=30/30/40 | 32.12% | +38.57% | +2.76% | 更偏稳定 |

这些数字只用于预注册 policy 与阈值；runner 不得把它们读成 expected output，不得据此覆盖新结果，也不得要求复现这些数字才算实现正确。

### 0.2 禁止的捷径

- 不得重训模型、平滑 P1、修改 Full 系数、重新计算 score 或重新分桶；
- 不得训练“下个月是否仍在 D8”标签；
- 不得用 realized return、五个事件月标签或未来 bucket 决定当月成员、权重、`rho` 或 cap；
- 不得从 75 个 policy 中事后选择最好参数并称为策略；
- 不得删除失败 policy、失败月份或五个事件月；
- 不得把 target/planned turnover 写成真实成交换手；
- 不得用 close-to-close 设计估算替代 stateful execution/NAV；
- 不得把 cap 导致的延迟退出、blocked order 或现金仓静默忽略；
- 不得在同月把未配置资金事后分给表现最好的股票；
- 不得修改或覆盖 sealed MLRANK、PORTSENS v6 bundle；
- 不得把本轮结果写成模型 alpha 获得历史支持、20C 授权或部署授权。

## 1. 身份、文件与授权

```text
experiment_id = 20_ohlcv_positive_beta_exposure_research
phase_id = 20B_P4_TURNCTL
run_id = 20B_P4_top_region_hysteresis_partial_rebalance_turnover_control_v0
contract_version = 20B_P4_TURNCTL_v0
requirement_file = requirement_20b_p4_top_region_hysteresis_partial_rebalance_turnover_control_diagnostic.md
config_file = configs/config_20b_p4_top_region_hysteresis_partial_rebalance_turnover_control.yaml
runner_file = src/run_20b_p4_top_region_hysteresis_partial_rebalance_turnover_control.py
test_file = tests/test_20b_p4_top_region_hysteresis_partial_rebalance_turnover_control.py
output_root = outputs/20B_P4_top_region_hysteresis_partial_rebalance_turnover_control_v0
```

当前用户已先后明确发出 `impl it` 与 `授权 并执行`，因此授权创建并验证 config/runner/tests，以及执行冻结的正式历史 portfolio replay：

```text
requirement_generation_authorized = true
implementation_authorized = true
historical_outcome_execution_authorized = true
portfolio_replay_authorized = true
model_training_authorized = false
deployment_authorized = false
```

该授权仅覆盖本 requirement 冻结的 replay A/replay B、确定性校验和正式 output bundle；仍不得解释为模型训练、score/bucket 重算、参数选择、20C 或部署授权。

同一个 `run_id + contract_version` 不得覆盖任何成功或失败 bundle。成员状态机、policy 网格、执行优先级、成本、gate、输出 schema 或输入 hash 发生 material change 时，必须升级 contract version 与 output root。

### 1.1 Config、CLI 与 resolved contract

Config 必须 exact 冻结：

```text
identity: experiment_id, phase_id, run_id, contract_version
paths: requirement/config/input registry/score/bucket/feature/raw/qfq/calendar/
       security-state/market-rule/output/replay scratch exact paths
upstream_hashes: Section 3 全部 SHA256
population: scored_model_id, split, 21 decision dates, 674 union instruments
policy_grid: Section 5 exact mixes/exit floors/rho/caps/comparators/IDs
membership: quotas, decision-close incumbent definition, stable priority,
            off-population exit, actual holding cap, realized-slot admission
execution: timing, initial AUM, rho, cash-inclusive one-way cap, sell-before-buy,
           lot, suspension, price-limit, cash scaling, realized weight guardrails
cost: statutory schedules, reference 5bps/side
statistics: scopes, bootstrap, seed, gate thresholds
worker_firewall: process roles, exact read whitelist, read-purpose/date rules
serialization: CSV/JSON/Parquet formats and stable sorts
output_contract: stage profiles, schemas, exact/conditional file sets
```

唯一允许 CLI：

```text
--config <exact path>
--output-root <must exact-match config>
--replay-id {replay_a,replay_b}
```

未知 config key、缺少冻结 key、环境变量覆盖、自动发现替代输入或 CLI 改写冻结值必须 fail closed。P0 必须写 `preflight/resolved_config.yaml`；后续阶段只读该文件，不重新解释环境。

## 2. 只回答与不回答的问题

### 2.1 只回答

1. 累计顶部区域固定配比是否机械降低相邻月目标换手；
2. D7/D6 退出缓冲是否减少 D7/D8 边界反复交易；
3. `rho=0.25/0.50` 是否减少短期信号抖动造成的完整买卖；
4. `20%/30%/40%` planned one-way cap 对真实成交、现金与响应延迟的影响；
5. 预指定 primary policy 在 reference 成本后能否保留最低限度的 D8 收益与事件弹性；
6. 换手下降是否伴随低波代理暴露、D8 实际资本权重、最大回撤或响应速度的显著漂移；
7. 哪些机制只降低 formation turnover，哪些机制确实降低 attempted/realized turnover 与交易成本。

### 2.2 不回答

- P1 EMA、P1 强正则或 score 时间稳定性 loss 是否改善模型；
- D8 是否应成为训练标签；
- 哪个网格点是未来最优参数；
- 动态事件预测、regime switching、cash/bond timing；
- 成本约束优化器中的最优 `kappa/gamma/Sigma`；
- 板块倾斜、硬止损、杠杆、做空、日频换仓；
- 21个月设计污染样本能否提供 confirmatory 或部署证据。

## 3. 上游 immutable 输入与哈希

路径别名：

```text
EXPERIMENT_ROOT = topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research

MLRANK_ROOT = EXPERIMENT_ROOT/outputs/20B_P4_learned_monotonic_return_ranking_diagnostic_v1
MLRANK_OUTPUT_HASHES = MLRANK_ROOT/output_hashes_20b_p4_mlrank.json
MLRANK_MANIFEST = MLRANK_ROOT/manifest_20b_p4_mlrank.json
MLRANK_DECISION = MLRANK_ROOT/20B_P4_learned_monotonic_return_ranking_diagnostic_decision.csv
SCORE_BUNDLE_MANIFEST = MLRANK_ROOT/scores/score_bundle_manifest.json
SCORE_BUNDLE_HASHES = MLRANK_ROOT/scores/score_bundle_output_hashes.json
BUCKET_ASSIGNMENT = MLRANK_ROOT/scores/robustness_model_bucket_assignment.parquet
SCORE_PANEL = MLRANK_ROOT/scores/robustness_model_score_panel.parquet
FEATURE_PANEL = MLRANK_ROOT/materialized/feature_panel.parquet

PORTSENS_ROOT = EXPERIMENT_ROOT/outputs/20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_v6
PORTSENS_OUTPUT_HASHES = PORTSENS_ROOT/output_hashes_20b_p4_portsens.json
PORTSENS_MANIFEST = PORTSENS_ROOT/manifest_20b_p4_portsens.json
PORTSENS_DECISION = PORTSENS_ROOT/20B_P4_d8_d10_sector_crowding_cost_stoploss_sensitivity_decision.csv
PORTSENS_RESOLVED_CONFIG = PORTSENS_ROOT/preflight/resolved_config.yaml
PORTSENS_CONTRACT_SNAPSHOT = PORTSENS_ROOT/preflight/contract_snapshot.json
PORTSENS_INPUT_AUDIT = PORTSENS_ROOT/preflight/input_integrity_audit.csv
PORTSENS_COST_REGISTRY = PORTSENS_ROOT/preflight/cost_scenario_registry.csv
```

冻结 SHA256：

| 输入 | SHA256 |
|---|---|
| `MLRANK_OUTPUT_HASHES` | `c535431f2f71cb6a87a738b495266662b3a8d002c173f8673defe23f855453c8` |
| `MLRANK_MANIFEST` | `052531faec928e0e2d4266dd65db60becf9803b90e105099fd943173d1982ab1` |
| `MLRANK_DECISION` | `b1758469b0b43cc21543d7e469a7d531ea08cbe5c9c08110ac345df2fac5c1cf` |
| `SCORE_BUNDLE_MANIFEST` | `8cba8402335b77a530c41efe48e93fd27c2887b588af7af9cd8b66f867d851ff` |
| `SCORE_BUNDLE_HASHES` | `aea4f0811ad8306af690e48a63a519bfffa90322c89daff5984e369dcd1b2974` |
| `BUCKET_ASSIGNMENT` | `9611aad6cd4b8933c882a8d3ae0e04561e8c360820f9c474a9de3a5840e5e846` |
| `SCORE_PANEL` | `56622631cd8fac004509e5c3ef3a862a02e3eb753a1054a2b7da803ab8ee5118` |
| `FEATURE_PANEL` | `22eeb61aee3c1d2e52a122896d4b494cd2079200b3e9e1a5eaa9fe23fa89c618` |
| `PORTSENS_OUTPUT_HASHES` | `7de9cb4dcf6ec4edba696efa1bb6cae4579b3fec0eb873d67ed3814ec39d9523` |
| `PORTSENS_MANIFEST` | `e133bc06251e6ab40dfd33c3c1d974e9153b494aa065aaf69675489439dc4f11` |
| `PORTSENS_DECISION` | `219df8e5f4a5ac1681a55bfb3cc53759c385baed79006bcc73bb694a87dec3f8` |
| `PORTSENS_RESOLVED_CONFIG` | `22fd757476c81973d67cdb7bd7bcf638efeda69be4ab99211ece47539034635f` |
| `PORTSENS_CONTRACT_SNAPSHOT` | `e5f5b1cdaa1c7b6217a95c8d8dca02940fd86b5a444f5421e597983f107c0cd5` |
| `PORTSENS_INPUT_AUDIT` | `669c5d5a1bb4e3efac7d6840e725103540f38eaa41c5588035527187f2461f6d` |
| `PORTSENS_COST_REGISTRY` | `cdf716e2962f4cd9d1c2da7b81e070de25f6072b1e6fcc1247b0197d7f6627c0` |

所有 registry 必须先验证自身 hash，再按 registry 重算其 exact file set。软链接、路径逃逸、重复逻辑路径、registry 未登记的替代输入或 hash mismatch 一律 fail closed。

### 3.1 MLRANK blocked 状态的使用边界

MLRANK 的最终 decision state 是 `20B_P4_MLRANK_metric_materialization_blocked`，原因属于 M2 validation metric 非有限；本 requirement 不把它解释为模型获得支持，也不使用其 terminal gate 授权任何策略。

本轮只读取已密封并已被 PORTSENS v6 使用的 `S0_SELECTED_FULL` score/bucket bundle，角色固定为：

```text
frozen_design_input_only = true
MLRANK_support_gate_inherited = false
MLRANK_model_promotion_inherited = false
```

`SCORE_BUNDLE_HASHES`、score panel、bucket assignment 或 `S0_SELECTED_FULL` identity 任一不一致，必须在 preflight 阻塞，不能回退到 B0、重新 fit 或重新分桶。

### 3.2 执行数据继承

价格、交易日历、证券状态、涨跌停、lot、commission、印花税、过户费、qfq/raw 映射与 next-open execution 语义，必须逐项继承 `PORTSENS_RESOLVED_CONFIG + PORTSENS_CONTRACT_SNAPSHOT + PORTSENS_INPUT_AUDIT`。

runner 必须重新验证其中列出的外部输入 path/hash，不得只相信旧 audit 的 `pass` 字符串。PORTSENS 的历史 position、daily NAV、order 或 return 不得作为本轮新 policy 的执行输入；它们只允许作为独立 comparator QA，不得复制成交路径。

## 4. 样本、population 与事件月

只允许：

```text
scored_model_id = S0_SELECTED_FULL
split = robustness
decision dates = MLRANK sealed 21 scheduled decision dates
label months = 2024-08 ... 2026-04
all-bucket row_n = 9300
bucket_id domain = integer 1..10
```

冻结审计 expectation：

```text
decision_month_n = 21
all_bucket_row_n = 9300
union_instrument_n = 674
D8_member_n_per_month_min = 43
D8_member_n_per_month_max = 45
D9_D10_member_n_per_month_min = 87
D9_D10_member_n_per_month_max = 89
D8_D10_member_n_per_month_min = 130
D8_D10_member_n_per_month_max = 134
```

每个 `(decision_date, instrument_id)` 必须唯一；`bucket_id`、`model_score`、`model_score_rank` 必须与 `BUCKET_ASSIGNMENT` 原值一致。不得因当日 bar 缺失、停牌或买入阻塞从 formation population 删除股票；这些情况进入执行状态。

执行状态使用21个月 `S0_SELECTED_FULL` population 的全期并集674只股票。某只已持有股票若下月不再出现在当月 S0 population：

```text
in_current_population = false
entry_eligible = false
buffer_eligible = false
hard_target_weight = 0
exit_reason = left_current_S0_population
```

它仍必须保留在 stateful shares/order/NAV 面板中，并按 `rho -> cap -> tradability` 路径退出；不得因为当月 bucket assignment 没有该行而删除持仓、按零价格清算或立即假定成交。

五个 post-hoc event label months 固定为：

```text
2024-10
2025-02
2025-08
2025-09
2026-04
```

它们只用于 attribution。`event_month_flag` 不得进入 formation、权重、cap、order 或 gate 输入；正式 gate 只允许使用已经预注册的 event-return retention readout，不允许用事件身份切换 policy。

## 5. Policy registry：75 个 policy 必须全量输出

### 5.1 两个累计顶部区域 capital mix

```text
MIX_TOP3_EQUAL:
    D8 sleeve = 1/3
    D9 sleeve = 1/3
    D10 sleeve = 1/3

MIX_TOP3_ELASTIC:
    D8 sleeve = 0.40
    D9 sleeve = 0.30
    D10 sleeve = 0.30
```

对这两个 mix 做完整 factorial：

```text
exit_bucket_floor in {D8, D7, D6}
rho in {0.25, 0.50, 1.00}
monthly_one_way_turnover_cap in {none, 0.20, 0.30, 0.40}
```

因此：

```text
2 mixes * 3 exit floors * 3 rho * 4 caps = 72 policies
```

`exit_bucket_floor=D8` 是无 hysteresis control；只有 `D7/D6` 是缓冲 policy。

### 5.2 三个额外 comparator

```text
C_D8_ONLY_XD8_R100_CNONE:
    sleeves = D8 100%
    exit_floor = D8
    rho = 1
    cap = none

C_D9D10_EQUAL_XD8_R100_CNONE:
    sleeves = D9 50% / D10 50%
    exit_floor = D8
    rho = 1
    cap = none

C_MIX303040_XD8_R100_CNONE:
    sleeves = D8 30% / D9 30% / D10 40%
    exit_floor = D8
    rho = 1
    cap = none
```

总 policy 数必须 exact 为：

```text
72 factorial + 3 extra comparators = 75 unique policy_id
```

等权与 40/30/30 的无缓冲、`rho=1`、uncapped row 已包含于 factorial，不得重复创建 comparator row。

每个 registry row 必须包含：

```text
policy_id
policy_role
capital_mix_id
d8_sleeve_weight
d9_sleeve_weight
d10_sleeve_weight
entry_bucket_floor
exit_bucket_floor
partial_rebalance_rho
monthly_one_way_turnover_cap
actual_holding_cap
new_entry_priority_rule
slot_admission_session_rule
initial_formation_full_rebalance
reference_cost_id
sector_tilt_lambda
stop_threshold
primary_gate_eligible
secondary_readout
```

Policy ID 编码固定为：

```text
factorial:
    F_{MIX333|MIX403030}_X{D8|D7|D6}_R{025|050|100}_C{NONE|020|030|040}

comparators:
    C_D8_ONLY_XD8_R100_CNONE
    C_D9D10_EQUAL_XD8_R100_CNONE
    C_MIX303040_XD8_R100_CNONE
```

不得创建 alias row、用显示名替代 `policy_id`，或让 primary/secondary 额外增加 registry 行数。

只有一个 row `primary_gate_eligible=true`：

```text
policy_id = F_MIX403030_XD7_R050_C040
```

只有一个预指定 secondary：

```text
policy_id = F_MIX333_XD7_R050_C040
```

## 6. 成员状态机：固定股票数，旧持仓优先

### 6.1 三个 sleeve 的目标名额

对每个 decision date `t`：

```text
quota_D8_t = current sealed D8 member count
quota_D9_t = current sealed D9 member count
quota_D10_t = current sealed D10 member count
target_position_n_t = quota_D8_t + quota_D9_t + quota_D10_t
```

这是冻结的**目标股票数规则**，不是事后常数。每月 target 总名额必须等于当月 sealed D8-D10 member count。

Policy-specific 实际持仓上限使用 sealed 21个月 target count 的预先可知最大值，固定为常数：

```text
C_D8_ONLY_XD8_R100_CNONE:
    actual_holding_cap = max_t(quota_D8_t) = 45

C_D9D10_EQUAL_XD8_R100_CNONE:
    actual_holding_cap = max_t(quota_D9_t + quota_D10_t) = 89

all top3 policies:
    actual_holding_cap = max_t(target_position_n_t) = 134
```

这些最大值只来自 sealed bucket membership count，不读取收益。`actual_holding` 定义为 `executed_shares > 0`，不得用 target weight、经济权重阈值或“忽略 dust”减少计数。月度 target 名额仍按当月桶数变化；cap 允许尚未归零的旧仓暂时与较小的当月 target 并存，但真实股票数永远不得超过45/89/134。Target 名额与实际持仓 cap 必须同时满足；只满足 target 数量不算通过。

### 6.2 D9 与 D10 核心 sleeve

```text
D9 sleeve members_t = all current D9 members
D10 sleeve members_t = all current D10 members
```

股票从 D8 升到 D9、D9 升到 D10 时，不先平仓再重建，只计算同一 instrument 的净目标差额。

### 6.3 D8 卫星 sleeve 与 hysteresis

定义 incumbent：在本次 scheduled decision close 已持有 `decision_close_shares > 0`。不得用 prior target 非零替代真实持仓，也不得用下一交易日 open/mark 判断 incumbent。

对 top3 policy，D8 sleeve candidate set：

```text
current S0 population 中的 current D8 members
UNION
current S0 population 中，current bucket 位于 exit_bucket_floor 到 D7
且真实持有的 incumbents
```

示例：

```text
exit_floor D8 -> 无额外缓冲成员
exit_floor D7 -> 当前 D7 incumbent 可继续竞争 D8 sleeve 名额
exit_floor D6 -> 当前 D6/D7 incumbent 可继续竞争 D8 sleeve 名额
```

D8 sleeve candidate 使用以下稳定排序，并只取前 `quota_D8_t`：

```text
1. incumbent DESC
2. current_bucket_id DESC
3. model_score DESC
4. decision_close_position_weight DESC
5. instrument_id ASC
```

这使旧持仓获得优先权，但不会扩大名额。被缓冲 incumbent 占用的每一个 D8 sleeve 名额，必须机械排除排序末端的一个新 D8 candidate；不得额外扩仓。

### 6.4 进入、继续持有与退出目标

```text
new entry:
    only current D8-D10 and selected into a sleeve

continue holding target:
    selected current D8-D10
    OR selected buffered incumbent in D7/D6 according to exit floor

exit target:
    not selected into any sleeve
    OR left current S0 population
```

“exit target”表示 hard target weight 为0，不保证受 `rho/cap/tradability` 约束后当月一定完全成交。任何未完成退出都必须保留 position、原因和 exit-delay age，不能伪装成已退出。

若 D8 candidate 少于 `quota_D8_t`、同一 instrument 被分配两个 sleeve、D9/D10 成员不完整、或 target name count 不等于冻结规则，policy-month fail closed，不允许把空缺资本重分给其他 sleeve。

### 6.5 真实持仓 admission cap：完成退出后才允许新进入

部分再平衡和 blocked exit 会令旧仓继续存在，因此 target name count 本身不能防止实际持仓膨胀。每个 execution session 必须按以下顺序执行：

```text
1. 执行已有 pending exit 与本月 sell/reduction orders；
2. 用 sell fills 后的 executed_shares 重新计算 post_sell_actual_holding_n；
3. available_new_holding_slots =
       max(0, actual_holding_cap - post_sell_actual_holding_n)；
4. 只有 shares=0、hard_target_weight>0 的新成员需要占用 slot；
5. 最多授权 available_new_holding_slots 个新成员下 buy order；
6. existing holding 的增持不占新 slot；
7. buy fills 后必须满足 actual_holding_n <= actual_holding_cap。
```

新成员 admission priority 固定为：

```text
1. sleeve D10 before D9 before D8
2. model_score DESC
3. instrument_id ASC
```

没有 slot 的目标成员保留：

```text
hard_target_weight > 0
entry_authorized = false
entry_queue_status = queued_no_realized_holding_slot
actual_weight = 0
```

Slot admission 只在每月 scheduled next-open rebalance session、该 session 的 sell fills 完成后评价一次：

```text
midmonth_late_buy_after_slot_release = forbidden
queued_entry_order_lifetime = current scheduled rebalance session only
queued_entry_reassessment = next scheduled decision using then-current target
```

不得为了凑齐 D9/D10 核心桶突破实际持仓 cap。Blocked exit 不产生 slot；attempted sell、planned full exit 或接近零的残仓也不产生 slot，只有 `executed_shares=0` 才释放 slot。若 pending exit 在月中才成交，释放的 slot 保持为空直到下个 scheduled rebalance，不得触发月中追买。新进入因无 slot 延迟时，未配置资本留现金，并进入响应延迟与 core-sleeve shortfall readout。

## 7. Hard target 权重与集中度约束

每个 sleeve 内等权：

```text
hard_target_weight_i,t = sleeve_capital_weight / selected_member_n_in_sleeve
hard_target_cash_weight_t = 1 - sum_i(hard_target_weight_i,t)
```

正常 top3 policy 的 `hard_target_cash_weight=0`。执行阻塞、lot rounding、成本和 cap 留下的现金不得向其他股票重分配。

固定约束：

```text
sum(hard target stock weights) + hard target cash weight = 1
hard_target_weight_i >= 0
hard_target_weight_i <= 0.03
leverage = 0
short = 0
```

超过3%时不得 clip；对应 policy-month 标记 `hard_target_concentration_blocked`。3%是实现安全上限，不是优化器权重 grid。

真实持仓风险阈值另行冻结：

```text
realized_single_weight_soft_limit = 0.03
realized_single_weight_emergency_limit = 0.05
```

价格漂移、cap 或 blocked sell 可能令真实权重超过3%，因此3%不能被描述成无条件 realized hard cap。执行规则为：

```text
actual weight > 3%:
    hard target remains <=3%
    reduction uses the same rho and common cap_scale
    sell attempt occurs before any buy attempt

actual weight > 5%:
    emergency_reduction_required = true
    consumes the same frozen turnover cap
    if tradable but no maximum-permitted reduction is attempted:
        execution_contract_breach = true
    if blocked by suspension/price limit:
        realized_risk_guardrail = false
        retain position and blocking reason
```

不得用卖不出的事实把实际权重改写成5%。所有日度与月度 `>3%`、`>5%` 暴露天数、最大权重和 blocked reason 必须全量报告。

必须同时保存两种暴露：

```text
sleeve exposure = 按 D8/D9/D10 sleeve identity 汇总
current-bucket exposure = 按当月 sealed current bucket 汇总
```

缓冲的 D7/D6 incumbent 属于 D8 sleeve，但不得伪装成 current D8 资本。

## 8. 部分再平衡与换手 cap

### 8.1 Pretrade drift 权重

每个 scheduled decision close 先密封 membership snapshot：

```text
decision_close_shares
decision_close_mark
decision_close_position_weight
decision_close_cash
decision_close_NAV
```

`decision_close_mark/NAV` 必须使用 PORTSENS v6 daily-NAV 相同的 mark、停牌与 staleness 规则。Section 6 的 incumbent、buffer membership 和 priority 只能读取该 snapshot、当月 frozen score/bucket；不得读取下一交易日 open、fill 或 label-month future bar。

任一 `decision_close_shares>0` 的股票若无法按继承规则得到 finite positive mark、position weight 或 NAV，必须 `execution_contract_blocked`；不得把 missing weight 填0来改变 incumbent priority。

下一 exchange-open execution session 才使用 reference net ledger 的实际 shares、execution-session pretrade mark、现金与 pretrade NAV 计算：

```text
w_stock_i,t_minus = marked_position_value_i / pretrade_NAV
w_cash_t_minus = cash / pretrade_NAV
```

不得使用上月 target weight 代替 drift weight。

### 8.2 部分再平衡

除首月外：

```text
w_partial_i,t = w_i,t_minus
                + rho * (hard_target_weight_i,t - w_i,t_minus)
```

cash 为 residual：

```text
w_partial_cash_t = 1 - sum_i(w_partial_i,t)
```

不得分别归一化股票权重，否则会消除 `rho` 的真实现金/漂移语义。

首个 decision 从现金启动，固定：

```text
initial_formation_full_rebalance = true
rho_effective = 1
turnover_cap_effective = none
```

首月只报告 launch turnover，不进入20个相邻月 turnover-control gate，避免把启动建仓与持续换手混为一谈。

### 8.3 Planned one-way turnover cap

对首月后的每个 scheduled rebalance：

```text
partial_delta_i = w_partial_i,t - w_i,t_minus
planned_buy_weight = sum_i(max(partial_delta_i, 0))
planned_sell_weight = sum_i(max(-partial_delta_i, 0))
partial_planned_one_way_turnover =
    max(planned_buy_weight, planned_sell_weight)

if cap is none or partial_planned_turnover <= cap:
    cap_scale = 1
else:
    cap_scale = cap / partial_planned_one_way_turnover

w_exec_plan_i,t = w_i,t_minus + cap_scale * partial_delta_i
w_exec_plan_cash_t = 1 - sum_i(w_exec_plan_i,t)
```

上式股票向量的 domain 是全期674只 instrument 并集，不只是当月 S0 population；因此退出 population 但仍持有的股票必然进入 delta、cap 与退出延迟审计。

该 one-way 定义等价于把 cash 作为一个资产后的完整 half-L1：

```text
0.5 * (
    sum_i(abs(stock_weight_delta_i))
    + abs(cash_weight_delta)
) = max(total_buy_weight, total_sell_weight)
```

因此纯现金加仓40%记为40%，不是20%。Formation target turnover 仍可保留不含现金的 `0.5 * stock L1` 作为成员变化 diagnostic，但不得用于 cap gate。

cap 对全部股票 delta 同比例缩放，禁止按事后收益、instrument 顺序或 bucket 单独挑选交易。这样保持买卖方向与 hard target 一致，也明确披露：跌出 exit floor 的仓位可能因 cap 而分多月退出。

数值要求：

```text
planned_one_way_turnover_after_cap <= cap + 1e-12
planned_buy_weight_after_cap <= cap + 1e-12
planned_sell_weight_after_cap <= cap + 1e-12
0 <= cap_scale <= 1
sign(w_exec_plan - w_minus) = sign(hard_target - w_minus), unless delta=0
no weight overshoot beyond hard target
```

### 8.4 三类 turnover 必须分开

```text
formation_target_turnover_t =
    0.5 * sum_i(abs(hard_target_weight_i,t - hard_target_weight_i,t-1))

planned_stateful_turnover_t =
    max(
        sum_i(max(w_exec_plan_i,t - w_i,t_minus, 0)),
        sum_i(max(w_i,t_minus - w_exec_plan_i,t, 0))
    )

attempted_one_way_turnover_t =
    max(intended_buy_notional, intended_sell_notional) / pretrade_NAV

realized_one_way_turnover_t =
    max(executed_buy_notional, executed_sell_notional) / pretrade_NAV

legacy_symmetric_attempted_turnover_t =
    (intended_buy_notional + intended_sell_notional) / (2 * pretrade_NAV)

legacy_symmetric_realized_turnover_t =
    (executed_buy_notional + executed_sell_notional) / (2 * pretrade_NAV)
```

formation turnover 的 prior vector 使用 prior hard target；planned/attempted/realized 使用真实 stateful drift。Legacy symmetric 指标只用于与既有报告对照，不进入 cap 或 gate。首月各项均保留，但 gate 与均值默认使用 `transition_month_n=20`。

## 9. 执行、成本与 NAV

### 9.1 时间顺序

严格继承 PORTSENS v6：

```text
decision information cutoff = scheduled decision date close
target formation = after decision close
execution attempt = next exchange-open session
sell/reduction attempts before buy/increase attempts
same-instrument delta netting = required
```

同一股票从 D8 到 D9 或 D9 到 D10 只交易净差额，禁止先全部卖出再买回。停牌、涨跌停、lot、现金不足、最小佣金、gap 与 blocked order 必须沿用 v6 状态机。

### 9.2 Reference 成本

唯一正式经济路径：

```text
reference_slippage = 5bps per executed buy/sell side
commission = inherited statutory schedule
stamp_tax = inherited effective-date sell schedule
transfer_fee = inherited effective-date schedule
```

同时维护同成交 shares/path 的 gross shadow NAV，用于分离 alpha/组合形态与实际成本：

```text
gross_shadow = same fills, zero commission/tax/transfer/slippage liability
reference_net = same fills, actual frozen reference costs
```

本轮不做额外 cost grid，不得从 PORTSENS 复制固定成交路径 cost shadow 冒充新 policy 的执行结果。

### 9.3 现金与自融资

```text
initial_AUM_cny = 10000000.0
capital_injection = forbidden
borrowing = forbidden
negative_cash_after_execution = forbidden
unfilled allocation = cash
same-month redistribution = forbidden
```

现金不足时只允许沿用 PORTSENS 的 common-factor buy scaling；不得按 instrument 顺序选择性成交。若即使 common scaling 仍不能满足约束，policy-path fail closed。

## 10. 必须报告的指标

### 10.1 收益与风险

对每个 policy 的 gross/reference-net 路径全量报告：

```text
month_n
compound_return
annualized_return
mean_monthly_return
median_monthly_return
annualized_volatility
zero_hurdle_sharpe
positive_month_rate
worst_month_return
empirical_p10_monthly_return
ES10_loss
max_drawdown_from_daily_NAV
terminal_NAV
total_cost_return
```

21个月 tail/Sharpe 只作 descriptive，不宣称稳定推断。

### 10.2 换手与执行

```text
mean_formation_target_turnover_transition20
mean_planned_stateful_turnover_transition20
mean_attempted_turnover_transition20
mean_realized_turnover_transition20
mean_legacy_symmetric_attempted_turnover_transition20
mean_legacy_symmetric_realized_turnover_transition20
median_realized_turnover_transition20
max_realized_turnover_transition20
cap_binding_month_n
cap_scale_mean_when_binding
holding_cap_binding_month_n
queued_new_entry_month_n
maximum_queued_new_entry_n
maximum_exit_delay_age_months
blocked_buy_month_n
blocked_sell_month_n
mean_cash_weight
max_cash_weight
mean_invested_weight
minimum_label_month_average_invested_weight
total_commission
total_stamp_tax
total_transfer_fee
total_slippage
```

cap 是 planned-weight 约束，不保证 realized notional 指标逐点完全相等；差异必须由 lot、price move、blocked order 和 cost 明确归因。

### 10.3 实际资本暴露

按每个 decision 后首个 execution session close，以及 label month 日均两种口径报告：

```text
D8_sleeve_capital_weight
D9_sleeve_capital_weight
D10_sleeve_capital_weight
current_D6_weight
current_D7_weight
current_D8_weight
current_D9_weight
current_D10_weight
below_exit_floor_weight
outside_current_S0_population_weight
cash_weight
maximum_single_instrument_weight
actual_holding_n
actual_holding_cap
holding_cap_headroom
queued_new_entry_n
core_sleeve_shortfall_weight
single_weight_above_3pct_n
single_weight_above_5pct_n
effective_holding_n = 1 / sum(stock_weight_i^2)
```

每个交易日的 current bucket identity 使用该 label month 对应 decision date 的 sealed assignment，月内不重分桶。`G5 D8_capital_presence` 唯一使用：先对每个 label month 的 daily close `current_D8_weight` 取交易日日均，再对21个 label months 等权平均；不得以首个 execution close、target sleeve weight 或只在有成交日的均值替代。

### 10.4 高波/低波代理暴露

只使用 `FEATURE_PANEL.p6_rank_t`，其 raw arm 是月度波动率、rank 为 ascending：

```text
low_vol_proxy = p6_rank_t <= 0.20
middle_vol_proxy = 0.20 < p6_rank_t < 0.80
high_vol_proxy = p6_rank_t >= 0.80
missing_vol_proxy = p6_missing = 1 or nonfinite p6_rank_t
```

报告四类 realized capital weight、capital-weighted mean `p6_rank_t`，并禁止把 proxy 分组写成基本面成长、真实 beta 或未来波动预测。

### 10.5 事件月与非事件月

每个 policy 报告：

```text
event_month_n = 5
non_event_month_n = 16
event_compound_return
event_mean_return
event_positive_rate
non_event_compound_return
non_event_mean_return
non_event_positive_rate
event_minus_non_event_mean
```

gross 与 reference net 都必须输出。事件标签不进入 policy 选择，报告必须同时展示五个月逐月收益，不能只展示聚合。

### 10.6 信号变化后的响应延迟

对每个 `(policy_id, instrument_id, transition_decision_date)` 识别：

```text
entry_transition = prior hard target 0 and current hard target > 0
exit_transition = prior hard target > 0 and current hard target = 0
sleeve_transition = prior sleeve != current sleeve while both targets > 0
```

保存：

```text
anchor_start_weight
anchor_hard_target_weight
anchor_target_delta
planned_delta_after_rho_cap
executed_delta_first_session
one_month_response_fraction_raw
one_month_response_fraction_clipped
months_to_90pct_of_anchor_target
transition_censored
censor_reason
blocked_execution_day_n
entry_queue_month_n
anchor_target_change_n
```

```text
anchor_start_weight = execution-session pretrade drift weight
anchor_hard_target_weight = transition decision frozen hard target
anchor_delta = anchor_hard_target_weight - anchor_start_weight

one_month_response_fraction_raw =
    sign(anchor_delta)
    * (actual_weight_after_first_execution_session - anchor_start_weight)
    / abs(anchor_delta)

one_month_response_fraction_clipped =
    clip(one_month_response_fraction_raw, 0, 1)
```

分母为0时 raw/clipped 均 missing。Raw ratio 必须保留，不能用 clipped 值隐藏价格漂移、overshoot 或反向成交。

响应 clock 以 scheduled execution session 为单位。首次满足下式的 session 定义为达到90%：

```text
sign(anchor_delta)
* (actual_posttrade_weight - anchor_start_weight)
>= 0.90 * abs(anchor_delta)
```

后续 hard target 改变时继续用原 anchor 测量，并累计 `anchor_target_change_n`；若新 hard target 反向，或其同方向目标幅度已经低于 anchor 90%阈值，则 censor。Censor precedence 固定为：

```text
1. target_direction_reversed
2. target_reduced_below_anchor_90pct
3. instrument_left_observable_execution_domain
4. terminal_sample_end
```

Blocked order、无 realized holding slot 和 cash scaling 是响应延迟原因，不是 censor；只要 anchor 方向仍有效就继续计时。终点截尾不得填0或当作失败达到时点。

## 11. 配对比较、bootstrap 与 Pareto 披露

### 11.1 Mandatory paired comparisons

至少固定以下 comparator：

```text
primary vs C_D8_ONLY_XD8_R100_CNONE
primary vs same MIX_TOP3_ELASTIC with EXITD8/RHO100/CAPNONE
primary vs secondary
secondary vs C_D8_ONLY_XD8_R100_CNONE
each factorial policy vs same mix EXITD8/RHO100/CAPNONE
```

比较必须使用相同21个月；turnover 使用相同20个相邻 transition months。不得按各 policy 可得月份分别计算；任一正式路径缺月则对应 paired comparison 不可评价。

### 11.2 Inference

```text
bootstrap = moving_block_bootstrap on paired monthly delta
block_length_months = 3
repetitions = 10000
seed = 20260717
confidence_interval = two-sided 90%
random_consumption_order = comparison_id ASC, replicate_id ASC
```

收益、turnover、event/non-event 和 drawdown delta 的区间只作 design sensitivity。不得以 p-value 或 CI 从75个 policy 中补选赢家。

### 11.3 Pareto frontier

允许按以下冻结轴生成 descriptive frontier：

```text
maximize reference_net_compound_return
minimize mean_realized_turnover_transition20
minimize max_drawdown
maximize event_reference_net_compound_return
```

必须保留全部75行及 `dominated_by_policy_ids`。Pareto membership 不授权参数选择，报告不得只展示 frontier 或只展示最好点。

## 12. Primary utility gate 与 decision state

### 12.1 Gate 只读取预指定 primary

正式 gate 只比较：

```text
primary = F_MIX403030_XD7_R050_C040
secondary = F_MIX333_XD7_R050_C040
turnover comparator = C_D8_ONLY_XD8_R100_CNONE
return/event comparator = C_D8_ONLY_XD8_R100_CNONE
```

阈值冻结：

```text
G0 integrity_and_determinism:
    all required artifacts complete
    all 75 policies complete for 21 months
    replay A/B core hashes exact

G1 turnover_control:
    primary mean_planned_stateful_turnover_transition20 <= 0.40 + 1e-12
    primary mean_realized_turnover_transition20
        <= 0.60 * C_D8_ONLY_XD8_R100_CNONE mean_realized_turnover_transition20

G2 return_retention:
    if C_D8_ONLY_XD8_R100_CNONE reference_net_terminal_gain > 0:
        primary reference_net_terminal_gain /
        C_D8_ONLY_XD8_R100_CNONE reference_net_terminal_gain >= 0.70
    else: gate = not_evaluable

G3 posthoc_event_damage_guardrail:
    primary event_reference_net_compound_return >= 0
    and, if C_D8_ONLY_XD8_R100_CNONE event_reference_net_compound_return > 0:
        primary event_reference_net_compound_return /
        C_D8_ONLY_XD8_R100_CNONE event_reference_net_compound_return >= 0.25

G4 execution_fidelity:
    actual_holding_n <= actual_holding_cap on every posttrade observation
    mean daily invested_weight over the full path >= 0.90
    minimum label-month daily-average invested_weight >= 0.80
    tradable_above_5pct_without_max_permitted_reduction_n = 0
    execution_contract_breach_n = 0

G5 D8_capital_presence:
    primary mean of 21 label-month daily-average current_D8_weight >= 0.30

G6 drawdown_noncatastrophic:
    primary max_drawdown >= C_D8_ONLY_XD8_R100_CNONE max_drawdown - 0.05
```

收益保留率使用 terminal gain：

```text
terminal_gain = terminal_NAV / initial_NAV - 1
```

不得用年化收益比、负数绝对值比或 gross return 替代。`event_compound_return=product(1+r_event)-1`，不得构造非连续事件子序列 NAV。`max_drawdown` 为负数，因此 G6 表示 primary 不得比 D8 多回撤超过5个百分点。

G3 使用已知五个事件月，只是 known-sample damage guardrail：

```text
event_evidence_role = posthoc_guardrail_only
affirmative_support_contribution = false
parameter_selection_contribution = false
```

通过 G3 不能增加证据等级；失败只说明预指定设计连已知事件弹性底线都没有保住。

### 12.2 Terminal decision states

优先级从上到下：

```text
20B_P4_TURNCTL_input_integrity_blocked
20B_P4_TURNCTL_policy_registry_blocked
20B_P4_TURNCTL_worker_firewall_blocked
20B_P4_TURNCTL_execution_blocked
20B_P4_TURNCTL_determinism_blocked
20B_P4_TURNCTL_metric_materialization_blocked
20B_P4_TURNCTL_primary_not_evaluable
20B_P4_TURNCTL_execution_fidelity_failed
20B_P4_TURNCTL_turnover_control_not_achieved
20B_P4_TURNCTL_return_retention_not_achieved
20B_P4_TURNCTL_posthoc_event_guardrail_failed
20B_P4_TURNCTL_d8_capital_or_drawdown_guardrail_failed
20B_P4_TURNCTL_design_feasibility_passed
```

`design_feasibility_passed` 只表示：在这21个已查看、设计污染月份中，预指定组合状态机没有违反冻结的工程可行性与损害 guardrails。它不包含 `supported` 语义，不等于策略支持、模型支持或部署支持。

`next_allowed_requirement` 映射固定为：

```text
design_feasibility_passed:
    requirement_generation_only_20B_P4_forward_portfolio_control_confirmation

any non-blocked failed guardrail:
    human_review_required_no_automatic_optimizer_or_retraining

any blocked state:
    none_until_blocker_repaired
```

无论 terminal state：

```text
parameter_selection_authorized = false
historical_support_claim_allowed = false
20C_execution_authorized = false
portfolio_optimizer_execution_authorized = false
model_retraining_authorized = false
deployment_authorized = false
```

## 13. 必需输出与 schema

### 13.1 Exact artifact universe

成功路径至少生成：

```text
preflight/contract_snapshot.json
preflight/resolved_config.yaml
preflight/input_integrity_audit.csv
preflight/policy_registry.csv
preflight/event_month_registry.csv
preflight/execution_contract_audit.csv
preflight/worker_read_whitelist.json
preflight/static_input_snapshot_manifest.json
preflight/static_input_snapshot_hashes.json

materialized/policy_membership_and_target_weights.parquet
materialized/monthly_policy_state.parquet
materialized/signal_transition_ledger.parquet
materialized/daily_execution_ledger.parquet
materialized/daily_nav.parquet
materialized/execution_bundle_manifest.json
materialized/execution_bundle_output_hashes.json

audit/static_worker_access_audit.csv
audit/execution_worker_access_audit.csv
audit/metric_worker_access_audit.csv
audit/static_worker_exit.json
audit/execution_worker_exit.json
audit/metric_worker_exit.json

historical/monthly_portfolio_returns.csv.gz
historical/policy_summary.csv
historical/turnover_decomposition.csv
historical/capital_exposure_readout.csv
historical/volatility_proxy_exposure.csv
historical/event_regime_slice.csv
historical/response_delay_readout.csv
historical/paired_policy_delta.csv
historical/block_bootstrap_readout.csv
historical/pareto_frontier_readout.csv
historical/historical_manifest.json
historical/historical_output_hashes.json

determinism/replay_b_core_hashes.json
determinism/determinism_comparison.csv

20B_P4_top_region_hysteresis_partial_rebalance_turnover_control_decision.csv
20B_P4_top_region_hysteresis_partial_rebalance_turnover_control_report_cn.md
stage_failure_audit.csv
manifest_20b_p4_turnctl.json
output_hashes_20b_p4_turnctl.json
```

失败 profile 只能输出已完成阶段的 exact artifact subset；不得创建空 success table 冒充完成。

### 13.2 关键行数与 stable keys

```text
policy_registry.csv:
    stable key = policy_id
    exact row_n = 75

policy_membership_and_target_weights.parquet:
    stable key = (policy_id, decision_date, instrument_id)
    exact row_n = 75 * 9300 = 697500
    row domain = 当月 S0 population rows

monthly_policy_state.parquet:
    stable key = (policy_id, decision_date, instrument_id)
    exact row_n = 75 * 21 * 674 = 1061550
    row domain = 每个 policy-date 对全期674只 instrument 并集完整 cross join

monthly_portfolio_returns.csv.gz:
    stable key = (policy_id, label_month, return_path)
    return_path in {gross_shadow, reference_net}
    exact row_n = 75 * 21 * 2 = 3150

policy_summary.csv:
    stable key = (policy_id, return_path)
    exact row_n = 75 * 2 = 150

turnover_decomposition.csv:
    stable key = (policy_id, decision_date)
    exact row_n = 75 * 21 = 1575
```

`turnover_decomposition.csv` 至少包含：

```text
policy_id
decision_date
prior_decision_date
launch_month
rho
turnover_cap
planned_buy_weight_before_cap
planned_sell_weight_before_cap
cap_scale
planned_buy_weight_after_cap
planned_sell_weight_after_cap
planned_cash_weight_delta
formation_target_turnover
planned_stateful_one_way_turnover
intended_buy_notional
intended_sell_notional
executed_buy_notional
executed_sell_notional
attempted_one_way_turnover
realized_one_way_turnover
legacy_symmetric_attempted_turnover
legacy_symmetric_realized_turnover
post_sell_actual_holding_n
actual_holding_cap
available_new_holding_slots
authorized_new_entry_n
queued_new_entry_n
holding_cap_breach
```

`planned_*` 来自 rho/cap 后、slot admission 前的完整目标差额；`intended_buy_notional` 只包含 sell fills 后实际获得 slot 且通过 cash scaling 的 buy orders。Queued entry 不得计入 intended/executed buy。

### 13.3 `monthly_policy_state.parquet` 最低字段

```text
run_id
contract_version
policy_id
decision_date
label_month
instrument_id
current_bucket_id
model_score
model_score_rank
in_current_population
decision_close_shares
decision_close_position_weight
pretrade_shares
pretrade_drift_weight
incumbent
entry_eligible
buffer_eligible
selected
sleeve_id
sleeve_quota
membership_priority_rank
hard_target_weight
partial_target_weight
cap_scale
execution_plan_weight
entry_authorized
entry_queue_status
available_new_holding_slots
actual_posttrade_weight
actual_posttrade_holding_n
actual_holding_cap
exit_target
exit_reason
exit_delay_age_months
order_status
blocking_reason
```

### 13.4 Decision row 最低字段

唯一一行，至少包含：

```text
run_id
contract_version
decision_state
claim_ceiling
policy_n
decision_month_n
transition_month_n
primary_policy_id
secondary_policy_id
turnover_comparator_policy_id
integrity_gate
determinism_gate
worker_firewall_gate
turnover_control_gate
return_retention_gate
posthoc_event_damage_guardrail
event_affirmative_support_contribution
execution_fidelity_gate
d8_capital_presence_gate
drawdown_gate
primary_mean_planned_turnover
primary_mean_realized_turnover
d8_mean_realized_turnover
primary_net_compound_return
d8_net_compound_return
net_terminal_gain_retention_ratio
primary_event_net_compound_return
d8_event_net_compound_return
event_gain_retention_ratio
primary_max_actual_holding_n
primary_actual_holding_cap
primary_holding_cap_breach_n
primary_min_actual_holding_headroom
primary_mean_invested_weight
primary_minimum_label_month_average_invested_weight
primary_maximum_single_instrument_weight
primary_single_weight_above_5pct_day_n
primary_max_exit_delay_age_months
primary_mean_current_D8_weight
primary_max_drawdown
d8_max_drawdown
historical_support_claim_allowed
parameter_selection_authorized
portfolio_optimizer_execution_authorized
model_retraining_authorized
deployment_authorized
next_allowed_requirement
blocking_reason
```

## 14. Stage、密封与 determinism

### 14.1 Worker firewall

三个 fresh-process worker 权限固定为：

```text
static worker:
    may read = sealed score/bucket/feature identities and frozen config only
    may write = policy registry and static input snapshot
    forbidden = raw forward bars, event registry, returns, existing reports

sequential execution worker:
    may read = sealed static snapshot, decision-time score/bucket,
               prior portfolio state, frozen raw/qfq/calendar/security execution inputs
    may write = month-by-month membership, target, orders, fills, shares, NAV
    forbidden = event registry, historical metric tables, existing reports,
                any realized-return field used in formation/weight decisions

metric worker:
    starts only after execution bundle seal verifies
    may read = sealed execution bundle, event registry
    may write = returns, exposure, paired/bootstrap, guardrails, report payload
    forbidden = modification of membership/order/fill/NAV artifacts
```

每个 access audit 的 stable key 为 `(worker_id, path_role, path, read_purpose)`，其中 `read_purpose` 只允许 `decision_logic / execution_fill / nav_mark / metric_only`。至少记录：

```text
process_pid
open_count
bytes_read
minimum_date_read
maximum_date_read
decision_input_max_date
outcome_column_read_count
event_flag_read_count
allowed
status
blocking_reason
```

Static/execution worker 任一 `event_flag_read_count>0`，或 `read_purpose=decision_logic` 的 `decision_input_max_date > scheduled_decision_date`，必须 fail closed。`execution_fill/nav_mark` 可在对应成交或估值日期读取 bar，但不得把该 payload 回流到已经密封的 membership/hard target。Worker exit JSON 只能由 parent 在 child 退出后写，记录 exit code、时间、payload hashes 与 access-audit hash；worker 不得自证退出状态。

### 14.2 顺序 stage

执行阶段：

```text
P0 preflight
P1 static policy registry and input snapshot
P2 month-by-month membership plus execution replay A
P3 historical metrics
P4 end-to-end replay B and determinism
P5 final decision/report/seal
```

P1 不得物化依赖 incumbent 的21个月 membership。P2 必须按 decision date 升序，在同一 policy state machine 中依次执行：

```text
decision-close state seal
-> membership/hard target
-> next-session rho/cap plan
-> sell fills
-> realized slot admission
-> buy fills
-> shares/cash/NAV continuation
-> next decision month
```

因此 `policy_membership_and_target_weights.parquet` 与 `monthly_policy_state.parquet` 都属于 P2 output。每阶段完成后先写该阶段 manifest/hash，再进入下一阶段。失败时停止后续读取/写入，创建 `stage_failure_audit.csv` 并密封 reached-stage profile。

Replay A/B 必须使用不同 scratch root、相同 resolved config，并分别从初始现金状态完整重放 P1-P3；不得从 replay A 的动态 membership 或 ledger 启动 replay B。至少比较：

```text
policy_registry
membership_and_target_weights
monthly_policy_state
signal_transition_ledger
daily_execution_ledger
daily_nav
monthly_returns
policy_summary
turnover_decomposition
capital/volatility/event/response readouts
paired deltas
bootstrap readout
decision row excluding run timestamp fields
```

CSV/JSON 使用固定 float format、UTF-8、stable key 排序；Parquet engine/compression/row-group/timestamp 单位必须在 config 冻结。Manifest 不得把自身或 final output-hashes 文件纳入递归 hash。

## 15. 测试要求

单元与集成测试至少覆盖：

1. 只读取 `S0_SELECTED_FULL/robustness`，任何 fallback/rebucket/refit 都失败；
2. policy registry exact 75行、ID 编码 exact、primary/secondary 各唯一一行且无 alias row；
3. D7 buffer incumbent 占用一个 D8 quota 时，排除一个低优先级新 D8，target count 不增加；
4. D6 buffer 只在 `exit_floor=D6` eligible；
5. 已持仓股票退出当月 S0 population 时仍留在674只完整 state panel，目标为0并按 rho/cap/可交易性退出；
6. incumbent 与 priority 只读 decision-close shares/weight；注入 next-open gap 不得改变 membership；
7. incumbent、bucket、score、decision-close weight ties 最终由 instrument id 稳定打破；
8. P1 只生成静态 registry，动态 membership 必须在 P2 与 execution 月序联合生成；
9. blocked/partial exit 未归零时不释放 slot，新目标进入 queued；
10. sell fill 归零后只授权实际可用 slot 数，新进入按 D10>D9>D8、score、instrument 排序；
11. 月中 pending exit 成交释放 slot 后不追买，queued entry 只在下次 scheduled decision 重评；
12. 每个 posttrade observation 的 `actual_holding_n <= actual_holding_cap`；
13. D8->D9、D9->D10 同 instrument 只生成净 order，不先卖后买；
14. `rho=0.25/0.50/1.00` 公式 exact，cash residual 保持权重和为1；
15. 首月强制 `rho=1/cap=none`，且不进入 transition20 gate；
16. 纯现金买入40%时 one-way turnover=40%，不是20%；
17. cap binding 时全部674只股票 delta 同比例缩放，buy/sell 两侧均不超过 cap；
18. cap 导致 exit 未完成时 position 与 `exit_delay_age` 延续；
19. formation/planned/attempted/realized 与 legacy symmetric turnover 不混用；
20. blocked buy/sell、lot rounding、price limit、suspension 与 cash scaling 继承 v6；
21. reference net 与 gross shadow shares/fills exact 相同，差异只来自成本负债；
22. target<=3%、realized>3% reduction、realized>5% emergency/blocked 语义正确；
23. D7/D6 buffer 资本计入 sleeve D8，但 current-bucket exposure 保留真实 bucket；
24. P6 rank proxy 四类权重加现金后可审计，不把 missing 混入 middle；
25. static/execution worker 读取 event flag 或形成时点之后的 decision input 必须 fail closed；
26. metric worker 不能修改 sealed membership/order/fill/NAV；
27. 五个 event months 与16个 non-event months exact，G3 只标记 posthoc guardrail；
28. response raw ratio 保留 overshoot；blocked/queued 不 censor，反向/降目标/终点按优先级 censor；
29. 所有75 policy、21个月、20 transitions 全量输出，缺一 fail closed；
30. primary gate 不能被 secondary 或 Pareto 最优 policy 替代；
31. terminal gain、event compound、invested-weight 与负 drawdown 的 guardrail 符号正确；
32. replay B 从初始现金完整重放，不复用 replay A 动态 membership；
33. replay A/B core hashes exact；
34. manifest/output-hashes 重算一致且无自引用。

## 16. 后续路线：本 contract 明确延期

### 16.1 成本约束优化器

更正规的优化形式可以是：

```text
maximize alpha' w - kappa * ||w - w_minus||_1 - gamma * w' Sigma w
```

并约束候选来自 D8-D10、long-only、无杠杆、单票上限、D8 下限、D10 上限、换手 cap 与现金 residual。但本 v0 不冻结 `alpha` 标准化、`Sigma` PIT window、shrinkage、`kappa/gamma` grid、solver/tolerance 或 infeasibility fallback，因此：

```text
optimizer_implementation_in_this_contract = forbidden
optimizer_requirement_generation = requires separate user instruction
```

只有本轮完整输出后，才允许基于明确的失败形态起草独立 optimizer requirement；不得把优化器作为 v0 失败后的同 run 自动 fallback。

### 16.2 P1 稳定性与模型重训

当前讨论中的相邻月 rank 持续性估算：

```text
P6 = 0.989
P0 = 0.891
P4 = 0.889
P1 = 0.079
```

以及 P1 Full 系数约 `-0.0181`，只作为后续研究动机，不进入本轮执行或 gate。以下变体全部延期到独立 contract：

```text
P1 raw
P1 EMA3
P1 EMA6
P1 raw + EMA
stronger P1 regularization
score temporal-stability penalty
```

任何后续模型 requirement 都必须保持：

```text
do_not_train_D8_retention_label = true
selection_metrics_include = net return, D8-D10 return, turnover,
                            event elasticity, non-event stability,
                            max drawdown, D8 return retention
```

本 v0 的失败不会自动授权重训；必须先区分是成员边界、执行 cap、成本、响应延迟还是 alpha 本身造成失败。

## 17. 实现验收清单

```text
[ ] requirement/config/runner/tests/output root identity exact。
[ ] 上游 registry 与 leaf hashes 全部重算通过。
[ ] 明确记录 MLRANK blocked state，不继承模型支持。
[ ] S0 score、rank、bucket bitwise/read-exact，不训练、不重分桶。
[ ] 75 policy registry exact，primary/secondary 唯一。
[ ] D8 sleeve quota replacement 保证 target name count 闭合；realized-slot admission 保证实际持仓不超过45/89/134。
[ ] membership 只读 decision-close shares/weight；next-open mark 只用于执行 sizing/fill。
[ ] 首月完整建仓；后续 rho -> cap -> execution 顺序固定。
[ ] stateful drift 来自真实 shares/marks/NAV，不来自 prior target。
[ ] cash-inclusive one-way cap 与 formation/legacy symmetric turnover 分开，gate 使用20 transitions。
[ ] realized 3%/5% 权重、投资比例、退出延迟和 queued entry guardrails 完整。
[ ] static/execution/metric worker firewall 与 parent-written exit audit 通过。
[ ] reference 法定成本 + 5bps/side，gross/net 同成交路径。
[ ] D8 实际资本、P6高低波代理、事件/非事件、响应延迟完整。
[ ] 五个事件月只作 posthoc damage guardrail，不产生 affirmative support。
[ ] 全75 policy 披露，不能事后只留最好参数。
[ ] primary gate 不被其他 policy 替换。
[ ] replay A/B determinism 与 manifest seal 通过。
[ ] 所有授权字段保持 false，除非用户另行明确授权。
```

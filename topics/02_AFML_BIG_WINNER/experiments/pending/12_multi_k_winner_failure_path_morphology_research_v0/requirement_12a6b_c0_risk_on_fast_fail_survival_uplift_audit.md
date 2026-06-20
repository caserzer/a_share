# 需求：12A6b C0 Risk-on Fast-fail Survival Uplift Audit

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 每个被读取的输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status。
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、entry executability 不可证明时 fail closed。

12A6b 必需的全局 market regime calendar 来自：

```text
global_regime_calendar_source =
  experiments/pending/11_archetype_proxy_validation_system_v0/
  outputs/publishable/tables/11A0_regime_pit_availability_audit/
  regime_daily_series_audit.csv

required_columns =
  date
  daily_regime_bucket
  daily_regime_conflict_n
  daily_regime_conflict_flag
```

构造规则：

```text
1. 读取 `date`、`daily_regime_bucket`、`daily_regime_conflict_n`、
   `daily_regime_conflict_flag`。
2. 只保留 `date` 满足 `YYYY-MM-DD` 的真实交易日行；例如
   `__calendar_reconciliation__` 这类汇总行必须排除，并记录到 audit notes。
3. 将 `date` 标准化为 YYYY-MM-DD，将 `daily_regime_bucket` 重命名为
   `market_regime_bucket`。
4. 每个 date 必须且只能对应一个 market_regime_bucket。
5. 任一真实交易日若 `daily_regime_conflict_flag = true` 或
   `daily_regime_conflict_n > 0`，`global_regime_calendar_status =
   blocked_regime_conflict_date` 并 fail closed。
6. 若任一 date 对应多个 regime，`global_regime_calendar_status =
   blocked_multi_regime_date`
   并 fail closed。
```

该 CSV 必须进入 `input_artifact_audit.csv`。R-core risk_on join 和 random baseline risk_on 候选池都必须使用这个 `date -> market_regime_bucket` 映射，不得从 event key 字符串解析 regime。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A6b
run_id = 12A6b_c0_risk_on_fast_fail_survival_uplift_audit
status = spec_draft_pending_review
expected_entrypoint = src/run_12a6b_c0_risk_on_fast_fail_survival_uplift_audit.py
expected_config = configs/config_12a6b_c0_risk_on_fast_fail_survival_uplift_audit.yaml
expected_test_file = tests/test_12a6b_c0_risk_on_fast_fail_survival_uplift_audit.py
```

12A6b 是 12A6 的口径修正和前置验证，不训练模型，不做 policy replay，不声明交易 alpha。它只回答两个问题：

```text
Q1. 在 risk_on scope 内，C0 相对 matched random entry 和 R-core benchmark，
    是否降低 10d / 20d 内 fast-fail 风险？

Q2. survival 的主定义是否应改为 no-fast-fail filter，
    而不是 12A6 当前的 upper-first triple-barrier survival？
```

## 2. 背景与为什么需要 12A6b

12A6 已完成 C0-local upper-first survival audit，并输出了以下结果：

```text
12A6 decision = 12A6_survival_threshold_candidates_supported
selected candidate = survival_U0.10_L0.20_H120
selected train upper_first / lower_first = 65.5% / 27.8%
selected robustness upper_first / lower_first = 71.0% / 19.9%
```

这个结果证明 C0 event 的 forward path 中存在可统计的 upper-first survival structure，但它没有完全回答当前研究最关心的两个问题。

第一，12A6 只在 C0 自身分母内选择 survival threshold，没有严格证明 C0 相对 baseline 有 edge。C0 可能只是 risk_on 市场本身上涨、或者 PIT universe 自身质量较高的结果。因此必须在同一个 risk_on scope 内对比：

```text
C0 risk_on
matched random risk_on executable entries
R-core risk_on benchmark entries
```

对比必须使用同一套 entry、OHLC、PIT membership 和 horizon completeness 规则，不能用不同阶段的 frozen label 混合比较。

第二，12A6 把 survival 主标签定义为 `upper_first`，即先触达 upper barrier 且没有先被 lower barrier 杀掉。这个定义更接近 “continuation opportunity” 或 “upper-first outcome”，不是当前想要的 survival filter。

当前对 survival 的研究定义应更窄、更早：

```text
survival = 在 10d / 20d 较短窗口内不要快速失败。
fast_fail = entry 后在 H sessions 内触达 lower barrier。
no_fast_fail = 没有触达 lower barrier。
```

upper barrier 不应参与 survival 主标签。它应作为 no-fast-fail cohort 之后的 continuation readout：

```text
P(touch +10% within 20d | no fast-fail)
P(touch +15% within 20d | no fast-fail)
P(touch +20% within 20d | no fast-fail)
```

12A6 的现有 path matrix 已显示这个方向更合理。以 C0 all-C0 分母为例：

```text
L=-10%, H=10:
  fast_fail = 21.6%
  no_fast_fail = 78.4%

L=-10%, H=20:
  fast_fail = 35.4%
  no_fast_fail = 64.6%
```

在 `L=-10%, H=20` 的 no-fast-fail cohort 内：

```text
upper +10% within 20d = 51.3%
upper +15% within 20d = 33.4%
upper +20% within 20d = 22.5%
```

这说明 `U=+15%, L=-10%, H=20` 不应被当成一个单一 triple-barrier survival label，而应拆成两层：

```text
stage_1_survival_filter = no_fast_fail_L10_H20
stage_2_continuation_readout = upper15_touch_H20_given_no_fast_fail
```

12A6b 的目标就是把这个口径写实并做 baseline uplift 验证。

## 3. 上游冻结事实

12A6b 承接以下已发布事实：

```text
12A1 decision = 12A1_r_core_recall_benchmark_only
12A2 decision = 12A2_state_change_candidate_generation_supported
12A3 decision = 12A3_state_change_backbone_partial_feature_source
12A4 decision = 12A4_meta_label_partial_feature_source
12A5A decision = 12A5A_no_decoupling_stop_keep_feature_source
12A6 decision = 12A6_survival_threshold_candidates_supported
```

关键解释：

```text
C0 是低密度、低重复、PIT 可执行的 state-change feature source。
C0 不是已证明的 standalone big-winner selector。
R-core 只能作为 recall benchmark / stress pool，不能被重新提升为训练正样本 denominator。
12A6 的 upper-first candidate 是 continuation readout，不是最终 fast-fail survival definition。
```

12A3 关键读数：

```text
C0 event_n = 28,691
R-core event_n = 47,914
C0 low_to_high recall = 98.60%
R-core low_to_high recall = 97.43%
C0 low_to_high event precision = 5.32%
R-core low_to_high event precision = 6.39%
C0 same-instrument 10d duplicate = 7.25%
R-core same-instrument 10d duplicate = 57.83%
C0 first event minus low median = 9 sessions
R-core first event minus low median = 14 sessions
```

12A6b 不重新评审 big-winner precision。它只检验 risk_on fast-fail survival uplift。

## 4. Primary Scope

### 4.1 C0 Primary Risk-on Population

主研究分母固定为 12A2 C0 canonical supported events 中的 risk_on 子集：

```text
source_artifact =
  outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/
  state_change_candidate_event_canonical.csv.gz

source_scope_id = 12A2_C0_primary_canonical_union
primary_scope_id = c0_risk_on
expected_primary_risk_on_event_n = 15,113
```

Primary filter：

```text
candidate_generation_status = supported_canonical_event
non_executable_next_open = false
event_t0_pit_status = pass
trade_open_pit_status = pass
trade_open_price is not null
market_regime_bucket = risk_on
canonical_event_id is unique
```

### 4.2 R-core Benchmark Population

R-core benchmark 只用于 baseline comparison，不参与 C0 label selection。

首选输入：

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/
  r_core_arm_event_registry.csv.gz
```

R-core filter：

```text
arm_id = 08_R_core_event_regime_gated_raw
event_registry_status = available
admission_status = admitted
event_execution_status = executable_next_open
event_execution_date is not null
event_execution_pos is not null
```

12A6b 的 R-core headline baseline 只允许 `event_execution_status = executable_next_open`。这是有意收窄的 entry discipline：C0 primary 使用 next executable open，R-core baseline 也必须使用可证明的 next-open entry。`executable_trade_open` 或其他历史 registry 状态不得混入 headline baseline；若实现输出这些状态，只能作为 diagnostic population。

已知对账要求：

```text
12A3 quoted raw R-core event_n = 47,914
12A6b headline executable_next_open R-core expected_n = 47,849
expected_difference_n = 65
```

报告必须解释 47,914 与 47,849 的差异，并在 `population_entry_executability_audit.csv` 中输出：

```text
r_core_registry_raw_event_n
r_core_executable_next_open_event_n
r_core_excluded_non_next_open_n
r_core_excluded_missing_execution_date_or_pos_n
r_core_entry_status_policy = headline_requires_executable_next_open
```

如果实际差异不是 65，必须标记 `r_core_count_drift_flag = true` 并在报告中说明上游 hash / schema 是否变化。

如果 `r_core_arm_event_registry.csv.gz` 缺少 `market_regime_bucket`，实现必须用 §0 的全局 regime calendar 对 `event_signal_date` 或 `event_execution_date` 重新赋值，并在 `population_membership_audit.csv` 中说明使用哪个日期口径。headline 口径使用 `event_signal_date` 判定 risk_on；`event_execution_date` 只作为敏感性读数。不能用字符串解析 `event_key` 代替 regime join。

必须在报告中注明入场口径的不对称风险：

```text
C0 entry = 12A2 canonical trade_open_date / trade_open_pos / trade_open_price
R-core entry = r_core registry event_execution_date / event_execution_pos
both must be executable_next_open for headline comparability,
but the source registry construction differs and must be audited rather than assumed identical.
```

R-core 旧字段 `fast_fail_10d_label`、`false_repair_20d_label`、`winner_120_label` 只能作为 parity / sanity readout。12A6b 的 primary fast-fail 读数必须从同一套 OHLC path 重算。

### 4.3 Matched Random Baseline

random baseline 不是全市场随便抽样，而是同一 PIT executable universe 内的 matched entry baseline。

随机候选池：

```text
pit_executable_daily =
  topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv

stock_daily_csv_dir =
  topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq

stock_daily_required_columns =
  date
  open
  high
  low
```

每个 C0 risk_on event 应匹配 random entry：

```text
match dimensions:
  event_split
  board_bucket
  calendar_month(event_t0_date)
  market_regime_bucket = risk_on
  PIT membership executable on entry date

entry rule:
  random_event_t0_date = sampled usable_trade_date
  random_trade_open_date = next executable open after sampled date

exclusion rule:
  headline random candidate pool must exclude exact C0 canonical keys
  `(instrument, event_t0_date)` from the C0 risk_on primary population.
```

Random `event_split` 赋值规则：

```text
1. 从 12A2 C0 canonical events 中读取 `event_split` 与 `event_t0_date`。
2. 构造 split date intervals：
     train_start <= date <= train_end
     validation_start <= date <= validation_end
     robustness_start <= date <= robustness_end
   每个 split interval 取该 split C0 event_t0_date 的 min / max。
3. random_event_t0_date 按这些 date intervals 赋 split。
4. 若 random date 不落入任何 split interval，不能进入 headline random candidate pool。
5. split boundary 必须输出到 `population_membership_audit.csv`。
```

Random risk_on 判定规则：

```text
random_event_t0_date 必须用 §0 的 global regime calendar 映射为 risk_on。
random_trade_open_date 只用于 entry executability，不用于 regime 判定。
```

random baseline 必须使用多 seed：

```text
random_seed_n >= 100
sample_size_per_seed = C0 risk_on event_n for the matching split / board / month cells
sampling = without replacement inside each matching cell when possible;
           if cell size is insufficient, sample with replacement and record replacement rate.
```

Random sampled entries 必须显式落盘，避免 path cache 去重后丢失放回抽样的样本权重：

```text
matched_random_sampled_entries.csv.gz

one row per sampled draw, not one row per unique path
sample_weight = 1 for each sampled draw
duplicate sampled entries are allowed only when replacement_used_flag = true
aggregation must use sampled draws or sample_weight, not unique cache rows
```

Cell 稀疏性规则：

```text
if random_candidate_cell_n = 0:
  cell_status = blocked_empty_candidate_cell
  random baseline gate fails

elif random_candidate_cell_n < c0_cell_event_n:
  sample with replacement
  replacement_rate = 1 - random_candidate_cell_n / c0_cell_event_n

if replacement_rate > 0.25 for any headline cell:
  cell_status = degraded_high_replacement
  headline random p05/p50/p95 still reported,
  but decision_state cannot be full_supported unless a documented fallback cell-merge rule is applied.
```

Allowed fallback cell merge, only when predeclared in config:

```text
merge calendar_month into calendar_quarter within same split / board / risk_on.
Do not merge board.
Do not merge split.
Report both original-cell and merged-cell replacement rates.
```

输出必须报告 random baseline 的分布，而不是只报一个 seed：

```text
random_fast_fail_rate_p05 / p50 / p95
random_no_fast_fail_rate_p05 / p50 / p95
random_upper_touch_given_no_fast_fail_p05 / p50 / p95
```

### 4.4 Scope Discipline

12A6b headline decision 只在 `risk_on` scope 内做。其他 scope 只做 diagnostic：

```text
headline scopes:
  c0_risk_on
  r_core_risk_on
  matched_random_risk_on

diagnostic scopes:
  c0_all
  c0_risk_on_by_board
  c0_risk_on_by_family
  c0_risk_on_by_year
  r_core_risk_on_by_board
  matched_random_risk_on_by_board
```

不得用 risk_off / transition 的好看结果回头支持 12A6b。12A6b 是 risk_on uplift audit。

## 5. Fast-fail Survival Label Definition

### 5.1 Primary Label

Primary survival label：

```text
label_id = no_fast_fail_L10_H20
entry = next executable open after event_t0
lower_barrier_pct = -0.10
horizon_sessions = 20
fast_fail = first low <= entry_price * (1 - 0.10) within 20 sessions
no_fast_fail = not fast_fail
same_bar_priority = irrelevant for fast-fail-only label
```

`no_fast_fail_L10_H20` 是 primary label 的默认候选，但 12A6b 必须同时输出以下 grid：

```text
horizon_sessions = [10, 20]
lower_barrier_pct = [-0.06, -0.08, -0.10, -0.12, -0.15, -0.20]
```

### 5.2 Secondary Continuation Readouts

upper barrier 只作为 conditional readout，不参与 primary survival label：

```text
primary_condition_label_id = no_fast_fail_L10_H20
condition_lower_barrier_pct = -0.10
condition_horizon_sessions = 20
upper_horizon_sessions = 20
upper_barrier_pct = [0.10, 0.15, 0.20, 0.25, 0.30]
upper_touch_H20 = first high >= entry_price * (1 + upper_barrier_pct) within 20 sessions
upper_touch_given_no_fast_fail =
  upper_touch_H20 among rows with no_fast_fail_L10_H20 = true
```

headline conditional continuation 只对 `no_fast_fail_L10_H20` cohort 输出并参与 gate。若实现额外输出其他 `lower_barrier_pct × horizon_sessions` 的 conditional readout，必须标记为 `diagnostic_only_flag = true`，不得混入 headline decision。

必须输出 unconditional 与 conditional 两套读数：

```text
upper_touch_rate_total
upper_touch_rate_given_no_fast_fail
uplift_given_no_fast_fail =
  upper_touch_rate_given_no_fast_fail / upper_touch_rate_total
```

这样才能回答：

```text
fast-fail filter 是否只是排除了亏损，
还是同时保留 / 富集了后续 +10% / +15% / +20% continuation？
```

### 5.3 Why Not Upper-first Survival

12A6b 不再把 `upper_first` 作为 primary survival label。原因：

```text
1. upper-first 混合了两件事：不快速失败 + 触达收益目标。
2. fast-fail survival 的业务含义是风险过滤，而不是收益命中。
3. 如果 upper barrier 太高，会把 survival label 再次变成低 base-rate continuation 目标。
4. 如果 horizon 太长，会把“早期失败排除”变成趋势持有结局，偏离当前建模需求。
```

`upper_first` 可以保留为 report 中的 diagnostic，但不能决定 12A6b final decision。

## 6. Forward Path 重算规则

所有 population 都必须使用同一套 forward path engine：

```text
entry_price = trade_open_price
entry_pos = trade_open_pos
path window = sessions [entry_pos, entry_pos + H]
fast_fail touch = any low <= entry_price * (1 + lower_barrier_pct)
upper touch = any high >= entry_price * (1 + upper_barrier_pct)
horizon_complete = entry_pos + H < len(daily)
entry_blocked = cannot prove executable entry / PIT membership / price row
```

`path window = [entry_pos, entry_pos + H]` 包含 entry bar。若 entry 当日开盘成交后同一日 low 触达 lower barrier，该 row 计为 fast-fail。这是对入场后盘中风险的保守定义，必须由测试固定。

`time_to_fast_fail_sessions` 定义：

```text
entry bar touch => 0
next session touch => 1
...
touch at entry_pos + H => H
```

`median_time_to_fast_fail_sessions` 和 `p75_time_to_fast_fail_sessions` 只在 fast-fail rows 上统计；no-fast-fail rows 是 label-negative survival rows，不作为 time-to-fast-fail 的 censored observations 进入分位数。

### 6.0 Path Matrix Cache

为避免 100 seed random baseline 重复扫描 OHLC，必须先生成 entry-level path cache：

```text
outputs/local_cache/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/
  entry_forward_path_cache.parquet
```

cache 粒度：

```text
one row per unique (instrument, entry_date, entry_pos, entry_price)
path_key = stable hash of (instrument, entry_date, entry_pos, entry_price)
```

`matched_random_sampled_entries.csv.gz` 中的每个 sampled draw 必须带 `path_key`。C0 / R-core population rows 也必须能映射到同一套 `path_key`。cache 只负责 path 计算复用，不代表随机样本分母；所有 random seed 分位数必须按 sampled draw 或 `sample_weight` 聚合。

必须一次性计算并缓存：

```text
min_low_return_10d
min_low_return_20d
max_high_return_20d
time_to_lower_minus_06_10d
time_to_lower_minus_08_10d
time_to_lower_minus_10_10d
time_to_lower_minus_12_10d
time_to_lower_minus_15_10d
time_to_lower_minus_20_10d
time_to_lower_minus_06_20d
...
time_to_lower_minus_20_20d
time_to_upper_plus_10_20d
time_to_upper_plus_15_20d
time_to_upper_plus_20_20d
time_to_upper_plus_25_20d
time_to_upper_plus_30_20d
horizon_complete_10d
horizon_complete_20d
entry_blocked
```

All grid tables must be derived from this cache. The implementation must not reread the same instrument OHLC path for every lower / upper / seed combination.

日线 high/low touch 是乐观触达读数，必须在报告中注明：

```text
high/low barrier touch = path diagnostic upper bound, not guaranteed executable fill
```

### 6.1 Censored 分母

rate 分母必须排除：

```text
entry_blocked = true
horizon_complete = false
```

同时输出：

```text
event_n
entry_blocked_n
censored_n
complete_executable_event_n
```

如果任一 headline population 的 `complete_executable_event_n < 500`，12A6b 必须 block。

### 6.2 PIT Membership Recompute

所有 C0、R-core、random entry 必须重新证明：

```text
PIT membership row exists on trade_open_date
is_listed = true
is_st = false
is_suspended = false
price row exists
trade_open_date / trade_open_pos alignment passes
open price is not null
```

PIT membership 文件较大，实现必须按 instrument / date 过滤或 streaming chunk 读取，不得全量无过滤载入。

## 7. Uplift Metrics

### 7.1 Fast-fail Uplift

headline uplift 只在 baseline 可自然对齐的 slice 上计算：

```text
headline slices:
  all risk_on
  split
  board_bucket
  calendar_year

diagnostic-only slices:
  primary_family_id
```

`primary_family_id` 是 C0 canonical 的事件机制字段，R-core 与 matched random 没有天然 family 归属。per-family row 必须标记 `diagnostic_only_flag = true`；除非实现显式启用 family-specific matched random（按该 family 的 C0 split / board / month 分布重采样 random），否则 per-family row 的 baseline delta 字段必须置空，不得用 all-random 或 all-R-core 读数冒充 family baseline。

对每个可比较 slice 输出：

```text
fast_fail_n
fast_fail_rate
no_fast_fail_n
no_fast_fail_rate
fast_fail_abs_delta_vs_random_p50 =
  c0_fast_fail_rate - random_fast_fail_rate_p50
fast_fail_abs_delta_vs_r_core =
  c0_fast_fail_rate - r_core_fast_fail_rate
fast_fail_relative_reduction_vs_random =
  1 - c0_fast_fail_rate / random_fast_fail_rate_p50
fast_fail_relative_reduction_vs_r_core =
  1 - c0_fast_fail_rate / r_core_fast_fail_rate
```

注意方向：

```text
fast_fail_rate 越低越好。
no_fast_fail_rate 越高越好。
```

### 7.2 Conditional Continuation Readout

在 `no_fast_fail_L10_H20` cohort 内输出：

```text
upper10_touch_rate_given_no_fast_fail
upper15_touch_rate_given_no_fast_fail
upper20_touch_rate_given_no_fast_fail
upper30_touch_rate_given_no_fast_fail
```

并相对 baseline 输出：

```text
random_upper_touch_rate_given_no_fast_fail_p05
random_upper_touch_rate_given_no_fast_fail_p50
random_upper_touch_rate_given_no_fast_fail_p95
conditional_upper_touch_abs_delta_vs_random_p50
conditional_upper_touch_abs_delta_vs_r_core
conditional_upper_touch_ratio_vs_random_p50
conditional_upper_touch_ratio_vs_r_core
```

primary support 不要求 C0 在所有 upper readout 上都优于 baseline；但 train 的 `upper10` 或 `upper15` 至少一个必须不劣于 random p50，robustness 的 `upper10` 或 `upper15` 至少一个必须不劣于 random p05。否则 fast-fail filter 可能只是“少亏但也少涨”的无效保守过滤。

### 7.3 Retention / Coverage

12A6b 需要输出 no-fast-fail filter 对 C0 的保留比例：

```text
c0_retention_after_no_fast_fail = no_fast_fail_n / complete_executable_event_n
```

如果 primary `no_fast_fail_L10_H20` 的 C0 retention 低于 50%，该 label 过于激进，需要降级为 diagnostic。当前 12A6 path matrix 的先验读数是 all 64.6%、train 61.5%、validation 63.8%、robustness 71.7%，因此 50% 是合理的 fail-safe 而不是目标值。

## 8. Decision Gates

### 8.1 Input Gates

必须全部通过：

```text
12A2 C0 canonical input read/schema pass
12A0/12A1 R-core registry read/schema pass
global regime calendar read/schema pass and date -> regime uniqueness pass
PIT executable daily read/schema pass
stock daily csv dir read pass and required OHLC schema pass
C0 risk_on event_n = 15,113 unless upstream artifact hash changed and report explains drift
C0 entry parity gate pass
R-core entry parity gate pass or R-core baseline marked diagnostic_unavailable
random baseline non-empty coverage gate pass after configured fallback, if any
random baseline sampling status recorded, including high-replacement degradation
```

如果 R-core baseline 因缺少 entry position / regime join 无法可靠重算，12A6b 仍可输出 C0 vs random 的 decision，但必须：

```text
r_core_baseline_status = diagnostic_unavailable
decision_state cannot be full_supported
```

### 8.2 Headline Support Gate

`12A6b_c0_fast_fail_survival_uplift_supported` 需要同时满足：

```text
primary label = no_fast_fail_L10_H20

train:
  c0_complete_executable_event_n >= 500
  c0_fast_fail_rate <= random_fast_fail_rate_p50 - 0.03
  c0_fast_fail_rate <= r_core_fast_fail_rate - 0.02
  c0_no_fast_fail_rate >= 0.50

robustness:
  c0_fast_fail_rate <= random_fast_fail_rate_p50 - 0.02
  c0_fast_fail_rate <= r_core_fast_fail_rate
  c0_no_fast_fail_rate >= 0.50

conditional continuation:
  train:
    upper10_touch_rate_given_no_fast_fail >= random_upper10_given_no_fast_fail_p50
    OR upper15_touch_rate_given_no_fast_fail >= random_upper15_given_no_fast_fail_p50
  robustness:
    upper10_touch_rate_given_no_fast_fail >= random_upper10_given_no_fast_fail_p05
    OR upper15_touch_rate_given_no_fast_fail >= random_upper15_given_no_fast_fail_p05
```

Validation 只作 readout，不作为 hard support gate；但如果 validation 同时出现：

```text
c0_fast_fail_rate > random_fast_fail_rate_p95
and upper10_touch_rate_given_no_fast_fail < random_upper10_given_no_fast_fail_p05
```

则 decision 必须降级为 partial。

### 8.3 Partial / Blocked Decision States

```text
12A6b_c0_fast_fail_survival_uplift_supported
12A6b_c0_fast_fail_survival_uplift_partial
12A6b_no_c0_fast_fail_survival_uplift
12A6b_blocked_input_or_baseline_failure
```

Decision mapping：

```text
if input gate fails:
  decision = 12A6b_blocked_input_or_baseline_failure
elif random baseline has unresolved empty headline cells after configured fallback:
  decision = 12A6b_blocked_input_or_baseline_failure
elif C0 vs random passes but R-core unavailable:
  decision = 12A6b_c0_fast_fail_survival_uplift_partial
elif random baseline high-replacement degradation exists and no fallback cell merge is applied:
  decision = 12A6b_c0_fast_fail_survival_uplift_partial
elif support gate passes:
  decision = 12A6b_c0_fast_fail_survival_uplift_supported
elif C0 no_fast_fail retention >= 0.50 but uplift is inconsistent:
  decision = 12A6b_c0_fast_fail_survival_uplift_partial
else:
  decision = 12A6b_no_c0_fast_fail_survival_uplift
```

## 9. Required Outputs

### 9.1 Publishable Tables

All outputs go under:

```text
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/
```

Required tables:

```text
input_artifact_audit.csv
population_entry_executability_audit.csv
population_membership_audit.csv
matched_random_sampling_audit.csv
matched_random_sampled_entries.csv.gz
fast_fail_survival_grid.csv
fast_fail_uplift_vs_baselines.csv
conditional_continuation_readout.csv
survival_filter_retention_by_slice.csv
fast_fail_decision.csv
random_seed_distribution.csv
```

### 9.2 `fast_fail_survival_grid.csv`

Required columns:

```text
population_id
baseline_role
scope_id
split
board_bucket
primary_family_id
calendar_year
horizon_sessions
lower_barrier_pct
event_n
entry_blocked_n
censored_n
complete_executable_event_n
fast_fail_n
fast_fail_rate
no_fast_fail_n
no_fast_fail_rate
median_time_to_fast_fail_sessions
p75_time_to_fast_fail_sessions
label_status
diagnostic_only_flag
```

`population_id` values:

```text
c0_risk_on
r_core_risk_on
matched_random_risk_on_seed_<N>
matched_random_risk_on_p50
matched_random_risk_on_p05
matched_random_risk_on_p95
```

### 9.3 `matched_random_sampled_entries.csv.gz`

Required columns:

```text
seed
sample_draw_id
path_key
split
board_bucket
calendar_month
calendar_quarter
random_event_t0_date
random_trade_open_date
instrument
entry_pos
entry_price
c0_match_cell_id
replacement_used_flag
replacement_draw_index
sample_weight
exact_c0_key_excluded_flag
sampling_status
```

This table must contain one row per sampled draw. If a duplicated random entry is drawn with replacement, it must appear as multiple sampled draw rows or carry equivalent `sample_weight`; downstream random seed metrics must honor this sampled-draw denominator.

### 9.4 `fast_fail_uplift_vs_baselines.csv`

Required columns:

```text
scope_id
split
slice_type
board_bucket
primary_family_id
calendar_year
horizon_sessions
lower_barrier_pct
c0_complete_executable_event_n
c0_fast_fail_rate
random_fast_fail_rate_p05
random_fast_fail_rate_p50
random_fast_fail_rate_p95
r_core_fast_fail_rate
fast_fail_abs_delta_vs_random_p50
fast_fail_abs_delta_vs_r_core
fast_fail_relative_reduction_vs_random_p50
fast_fail_relative_reduction_vs_r_core
uplift_status
diagnostic_only_flag
```

### 9.5 `conditional_continuation_readout.csv`

Required columns:

```text
population_id
scope_id
split
condition_label_id
condition_horizon_sessions
condition_lower_barrier_pct
upper_horizon_sessions
upper_barrier_pct
complete_executable_event_n
no_fast_fail_n
upper_touch_n_total
upper_touch_rate_total
upper_touch_n_given_no_fast_fail
upper_touch_rate_given_no_fast_fail
uplift_given_no_fast_fail_vs_total
random_upper_touch_rate_given_no_fast_fail_p05
random_upper_touch_rate_given_no_fast_fail_p50
random_upper_touch_rate_given_no_fast_fail_p95
r_core_upper_touch_rate_given_no_fast_fail
conditional_readout_status
diagnostic_only_flag
```

### 9.6 `fast_fail_decision.csv`

Required columns:

```text
decision_state
primary_label_id
primary_horizon_sessions
primary_lower_barrier_pct
c0_train_fast_fail_rate
random_train_fast_fail_rate_p50
r_core_train_fast_fail_rate
c0_robustness_fast_fail_rate
random_robustness_fast_fail_rate_p50
r_core_robustness_fast_fail_rate
c0_validation_fast_fail_rate
random_validation_fast_fail_rate_p50
r_core_validation_fast_fail_rate
c0_train_no_fast_fail_rate
c0_robustness_no_fast_fail_rate
upper10_given_no_fast_fail_train
upper15_given_no_fast_fail_train
random_upper10_given_no_fast_fail_train_p50
random_upper15_given_no_fast_fail_train_p50
upper10_given_no_fast_fail_robustness
upper15_given_no_fast_fail_robustness
random_upper10_given_no_fast_fail_robustness_p05
random_upper15_given_no_fast_fail_robustness_p05
gate_failure_reasons
next_allowed_requirement
```

### 9.7 Report / Manifest

Required report:

```text
outputs/publishable/reports/c0_risk_on_fast_fail_survival_uplift_report.md
```

Report must be written in Chinese and include:

1. 为什么 12A6b 修正 12A6 的 survival 口径；
2. C0 vs random vs R-core 的 risk_on denominator 对齐；
3. fast-fail grid 的 10d / 20d 读数；
4. `no_fast_fail_L10_H20` 是否通过；
5. no-fast-fail 后的 +10% / +15% / +20% continuation readout；
6. board / family / year 的稳定性；
7. 为什么该结果仍不是交易收益策略；
8. 下一步是否允许进入 meta-label 训练。

Required manifest:

```text
outputs/manifests/12A6b_c0_risk_on_fast_fail_survival_uplift_audit_manifest.json
```

Manifest must include all input / output hashes and decision state.

## 10. Random Baseline Reproducibility

Random sampling must be deterministic:

```text
base_seed = 120600
random_seed_n = 100
seed_i = base_seed + i
```

`matched_random_sampling_audit.csv` must report:

```text
seed
split
board_bucket
calendar_month
calendar_quarter
c0_cell_event_n
random_candidate_cell_n
exact_c0_key_excluded_n
sampled_event_n
replacement_used_flag
replacement_rate
fallback_merge_applied_flag
fallback_merge_rule
merged_random_candidate_cell_n
merged_replacement_rate
cell_status
```

If any headline cell has `random_candidate_cell_n = 0`, random baseline gate fails.

If any headline cell has `replacement_rate > 0.25`, `cell_status = degraded_high_replacement`; full support is allowed only if the configured fallback merge rule is applied and the merged-cell `replacement_rate <= 0.25`.

### 10.1 `population_membership_audit.csv`

Required columns:

```text
population_id
source_artifact_id
raw_event_n
after_status_filter_event_n
risk_on_join_date_field
risk_on_join_status
global_regime_calendar_status
non_date_calendar_row_n
regime_conflict_date_n
multi_regime_date_n
split_assignment_source
split_assignment_status
entry_status_policy
expected_event_n
actual_event_n
count_drift_n
count_drift_flag
notes
```

### 10.2 `population_entry_executability_audit.csv`

Required columns:

```text
population_id
event_n
entry_status_policy
executable_entry_n
entry_blocked_n
missing_price_file_n
missing_entry_date_n
missing_entry_pos_n
missing_entry_price_n
entry_date_pos_mismatch_n
pit_membership_missing_n
pit_membership_not_executable_n
r_core_registry_raw_event_n
r_core_executable_next_open_event_n
r_core_excluded_non_next_open_n
r_core_excluded_missing_execution_date_or_pos_n
entry_parity_gate_pass
```

### 10.3 Local Cache Manifest Fields

The local cache itself is not required to be committed, but the run manifest must record:

```text
entry_forward_path_cache_row_n
entry_forward_path_cache_column_n
entry_forward_path_cache_sha256_if_publishable
path_cache_reuse_status
```

## 11. Tests

Required tests:

1. `no_fast_fail` label is true when no lower touch occurs within H and false when lower touch occurs.
2. Lower touch on day H counts as fast-fail; lower touch after H does not.
3. Entry-bar same-day low touch counts as fast-fail with `time_to_fast_fail_sessions = 0`.
4. Horizon incomplete rows are excluded from rate denominator and counted as censored.
5. Entry blocked rows are excluded from rate denominator and counted in entry audit.
6. Upper touch does not affect primary survival label.
7. `median_time_to_fast_fail_sessions` uses fast-fail rows only.
8. Conditional continuation readout is computed only inside no-fast-fail cohort.
9. Global regime calendar blocks if one date maps to multiple regimes.
10. Global regime calendar filters non-date reconciliation rows before building `date -> regime`.
11. Stock daily schema gate blocks if `date/open/high/low` is missing.
12. Random split assignment uses C0 split date intervals and excludes dates outside intervals.
13. Random baseline sampling is deterministic for a fixed seed.
14. Random baseline matches split / board / calendar_month / risk_on cells.
15. Random baseline excludes exact C0 `(instrument, event_t0_date)` keys from headline candidate pool.
16. Random sampled entries preserve replacement duplicates through sampled draw rows or `sample_weight`.
17. Random cell with replacement_rate > 0.25 marks degraded and cannot produce full supported without fallback merge.
18. Conditional continuation headline gate uses only `no_fast_fail_L10_H20` and `upper_horizon_sessions = 20`.
19. R-core old `fast_fail_10d_label` is not used as primary label when recompute path exists.
20. R-core executable_next_open count audit reports 47,914 vs 47,849 expected reconciliation or drift flag.
21. Support decision direction treats lower fast_fail_rate as better.
22. Validation conflict downgrades supported to partial.
23. Missing R-core baseline allows partial only if C0 vs random passes; it cannot produce full supported.
24. Required output schema test for every publishable table.
25. Manifest report hash sync test.

## 12. Non-goals

12A6b 明确不做：

- 不训练 LightGBM / meta-label / rejector model。
- 不改 12A2 C0 generation。
- 不重新构建 06 big-winner registry。
- 不用 big-winner overlap 作为 primary label。
- 不用 12A6 upper-first selected candidate 作为主结论。
- 不把 random baseline 的单个 seed 当作结论。
- 不在 risk_off / transition 里寻找更好结果后反推 risk_on 支持。

## 13. Expected Next Requirement

12A6 已发布的 report / manifest 中曾给出：

```text
next_allowed_requirement = requirement_12a7_c0_survival_meta_label_feasibility.md
```

12A6b 是对 12A6 survival 口径的修正阶段，因此它取代原来的 `12A6 -> 12A7` 直连边。任何 fast-fail survival meta-label 训练必须先等待 12A6b decision，不得直接使用 12A6 的 `survival_U0.10_L0.20_H120` upper-first candidate 进入训练。

如果：

```text
decision_state = 12A6b_c0_fast_fail_survival_uplift_supported
```

则下一步允许进入：

```text
requirement_12a7_c0_fast_fail_survival_meta_label_feasibility.md
```

12A7 的目标应是预测 / 过滤 fast-fail risk，而不是直接预测 rare big-winner。

如果：

```text
decision_state = 12A6b_c0_fast_fail_survival_uplift_partial
```

则下一步应先写：

```text
requirement_12a6c_fast_fail_scope_or_threshold_revision.md
```

用于调整 `H=10/20`、`L=-8/-10/-12` 或 random matching 口径。

如果：

```text
decision_state in (
  12A6b_no_c0_fast_fail_survival_uplift,
  12A6b_blocked_input_or_baseline_failure
)
```

则不得进入 fast-fail survival meta-label 训练；C0 只能继续作为 diagnostic feature source。

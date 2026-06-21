# 需求：12A6c Two-stage Fast-fail Rejector And Continuation Feasibility

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
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、entry executability 不可证明时 fail closed；不得从报告文本或聚合表反推出事件、标签或特征。

12A6c 必需的全局 market regime calendar 来自与 12A6b 相同的来源：

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

构造规则与 12A6b §0 完全一致：只保留 `YYYY-MM-DD` 真实交易日行，每个 date 必须且只能对应一个 `market_regime_bucket`，任一 date 出现 regime conflict 或 multi-regime 时 fail closed。该 CSV 必须进入 `input_artifact_audit.csv`，所有 risk_on join 都必须使用这个 `date -> market_regime_bucket` 映射，不得从 event key 字符串解析 regime。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A6c
run_id = 12A6c_two_stage_fast_fail_rejector_continuation_feasibility
status = spec_draft_pending_review
expected_entrypoint = src/run_12a6c_two_stage_fast_fail_rejector_continuation_feasibility.py
expected_config = configs/config_12a6c_two_stage_fast_fail_rejector_continuation_feasibility.yaml
expected_test_file = tests/test_12a6c_two_stage_fast_fail_rejector_continuation_feasibility.py
```

12A6c 是 12A6b partial decision 声明的 next_allowed_requirement 的落地实现。12A6b 把它登记为 `requirement_12a6c_fast_fail_scope_or_threshold_revision.md`；本 spec 在保持同一 lineage 位的同时，把 scope / threshold revision 与 two-stage rejector framing 合并为一个 feasibility 需求：

```text
declared_next_allowed_requirement_in_12a6b =
  requirement_12a6c_fast_fail_scope_or_threshold_revision.md
realized_by =
  requirement_12a6c_two_stage_fast_fail_rejector_continuation_feasibility.md
```

12A6c 回答的核心问题是：

```text
Q1. 在 risk_on scope 内，能否只用 t0-PIT 特征训练一个 stage-1 fast-fail rejector，
    把 C0 留存 cohort 的 no_fast_fail_L10_H20 fast-fail rate 压到
    matched random p50 以下，并在 robustness 成立？

Q2. 对 stage-1 留存且到第 20 个 session 仍存活的 cohort，
    用 t0 特征 + 已实现 0-20d 路径特征，
    能否把 20d 之后的 continuation 分层到明显高于 survivor base rate 的 top bucket？
```

12A6c 是 modeling feasibility（与 12A4 同级），允许训练低容量 meta-label 模型；但不做 policy replay、不做仓位、不声明交易 alpha。

## 2. 背景与为什么需要 12A6c

12A6b 的结论是 partial，核心读数：

```text
12A6b decision = 12A6b_c0_fast_fail_survival_uplift_partial
primary_label = no_fast_fail_L10_H20
C0 risk_on fast_fail_rate (L=-10%, H=20) = 37.27%
matched random p50 = 32.93%
C0 - random p50 = +4.34 pp
R-core fast_fail_rate = 40.89%
C0 - R-core = -3.62 pp
```

12A6b 证明了两件事，并留下一件未证：

```text
established_1:
  C0 不是 standalone short-horizon survival filter。
  C0 本身 fast-fail rate 高于 matched random p50，
  C0 membership 不能直接当成 survival edge。

established_2:
  no-fast-fail cohort 内 continuation 被显著富集。
  全 risk_on +10% / +15% / +20% given no-fast-fail = 53.64% / 36.20% / 25.06%，
  conditional uplift vs total = 1.30x - 1.46x，
  train / validation / robustness 全部高于 matched random。

not_yet_established:
  能否在 t0 用 PIT 特征提前拒掉 fast-fail，
  使留存 cohort 的 fast-fail rate 跑赢 matched random p50。
```

12A6b 的 Insight 已经把研究目标改写为 two-stage：

```text
C0 is a continuation-opportunity source that still needs a fast-fail rejector.
```

因此 12A6c 把问题拆成两个串行决策点，而不是继续找一个 C0-only survival definition：

```text
stage_1 (decision at t0):
  fast-fail rejector。只用 t0-PIT 特征，
  目标是把 no_fast_fail_L10_H20 的 fast-fail rate 压低，
  且 keep cohort 跑赢 matched random p50 与 C0 baseline。

stage_2 (decision at entry + 20 sessions, conditional on survived):
  continuation classifier。用 t0 特征 + 已实现 0-20d 路径特征，
  目标是在 day-20 survivor 内，把 20d 之后的 continuation 分层。
```

为什么 stage-2 的决策点选在 entry+20：

```text
1. 12A6b 读数：C0 all risk_on fast-fail 的 median time-to-fast-fail = 8 sessions，
   p75 = 13 sessions；primary label 本身就是 H=20 下障碍。
   因此到第 20 个 session，fast-fail 基本已被解析。
2. 到第 20 个 session 仍存活的 cohort，约等于 12A6b 中 continuation 被富集的
   no_fast_fail cohort。
3. 在 entry+20 决策点上，[entry, entry+20] 的已实现路径是过去信息，
   可以合法作为 stage-2 特征，而 20d 之后的路径只能作为 stage-2 label。
   这干净地满足 12A5A no_future_feature 纪律。
```

## 3. 上游冻结事实

12A6c 承接以下已发布事实：

```text
12A1 decision = 12A1_r_core_recall_benchmark_only
12A2 decision = 12A2_state_change_candidate_generation_supported
12A3 decision = 12A3_state_change_backbone_partial_feature_source
12A4 decision = 12A4_meta_label_partial_feature_source
12A5A decision = 12A5A_no_decoupling_stop_keep_feature_source
12A6 decision = 12A6_survival_threshold_candidates_supported
12A6b decision = 12A6b_c0_fast_fail_survival_uplift_partial
```

关键解释：

```text
C0 是低密度、低重复、PIT 可执行的 state-change feature source。
C0 不是已证明的 standalone big-winner selector，也不是 standalone survival filter。
R-core 只能作为 recall benchmark / stress pool，不能被重新提升为训练正样本 denominator。
12A4 / 12A5A 显示当前 PIT 特征能做局部风险尾部剔除，
但没有证明 clean winner 与 bad-side 在当前特征空间稳定可分。
12A6c 的 stage-1 gate 必须直接对抗这个未证项，不能假定 rejector 一定成立。
```

12A6b risk_on 已知读数（headline 复用，不重新评审）：

```text
C0 risk_on primary event_n = 15,113
C0 risk_on complete_executable_event_n = 15,113
C0 risk_on fast_fail_rate (L=-10%, H=20) = 37.27%
matched random p50 fast_fail_rate = 32.93%
R-core risk_on fast_fail_rate = 40.89%
no_fast_fail retention (all risk_on) = 62.73%
upper10 / upper15 / upper20 given no_fast_fail = 53.64% / 36.20% / 25.06%
robustness fast_fail C0 - random p50 = +6.18 pp
90-session dedup (risk_on-only) C0 - random p50 = +2.50 pp
```

## 4. 非目标

12A6c 明确不做：

- 不修改 12A2 family formula、threshold、canonicalization priority 或 C0 primary union；
- 不重新构建 06 big-winner registry，不把 big-winner overlap 当作 stage-1 或 stage-2 主标签；
- 不把 R-core 重新提升为训练正样本 denominator；R-core 只作 benchmark / prior interaction feature / readout；
- 不搜索或优化 `risk_on` / `transition` / `risk_off` regime filter，不让 `transition` / `risk_off` 进入 primary scoring；
- 不用 robustness / OOS 结果回头挑选更好看的 feature、threshold、horizon、model 或 family；
- 不做 policy replay、仓位、entry / exit、交易成本或资金曲线；
- 不声明最终可交易 alpha；
- 不训练高容量黑箱模型；
- stage-1 不得使用任何 entry 之后（t0 之后）的已实现路径、low / high / MFE / MAE / future return / episode label；
- stage-2 不得使用 20d 之后（决策点 entry+20 之后）的已实现路径或 future label；
- 不用事后 board / regime 修订值替代 t0 PIT context；
- 不把单个 random seed 当作 baseline 结论。

## 5. 必需输入

### 5.1 12A6b survival audit 输出

必需输入：

```text
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/fast_fail_decision.csv
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/fast_fail_survival_grid.csv
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/conditional_continuation_readout.csv
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/matched_random_sampled_entries.csv.gz
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/population_membership_audit.csv
outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/population_entry_executability_audit.csv
outputs/manifests/12A6b_c0_risk_on_fast_fail_survival_uplift_audit_manifest.json
```

12A6b gate：

```text
fast_fail_decision.decision_state in [
  12A6b_c0_fast_fail_survival_uplift_partial,
  12A6b_c0_fast_fail_survival_uplift_supported
]
fast_fail_decision.primary_label_id = no_fast_fail_L10_H20
```

若 12A6b 为 `12A6b_no_c0_fast_fail_survival_uplift` 或 `12A6b_blocked_input_or_baseline_failure`，12A6c 必须 fail closed。

### 5.2 12A2 state-change 事件输入

必需输入：

```text
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_candidate_event_canonical.csv.gz
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_candidate_event_instances.csv.gz
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_family_formula_spec.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_canonicalization_spec.csv
outputs/manifests/12A2_state_change_backbone_candidate_generator_manifest.json
```

Primary state-change population（与 12A6b §4.1 一致）：

```text
candidate_generation_status = supported_canonical_event
non_executable_next_open = false
event_t0_pit_status = pass
trade_open_pit_status = pass
trade_open_price is not null
market_regime_bucket = risk_on
canonical_event_id is unique
expected_primary_risk_on_event_n = 15,113
```

`state_change_candidate_event_instances.csv.gz` 只能用于 same-day family trigger count、secondary family flags、freshness / overlap features；不得重新生成 primary event。

### 5.3 R-core benchmark 输入

必需输入：

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_arm_event_registry.csv.gz
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_demote_or_keep_decision.csv
outputs/manifests/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit_manifest.json
```

R-core gate：

```text
r_core_demote_or_keep_decision.decision = 12A1_r_core_recall_benchmark_only
```

R-core 只用于 benchmark baseline 和 prior interaction feature；不得把 `source_arm_is_r_core` 当作 primary model 的分类特征训练 pooled 模型。

### 5.4 PIT 市场、价格、执行和 regime 输入

必需输入：

```text
topics/02_AFML_BIG_WINNER/configs/labels.yaml
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/index/benchmark_indices_daily.csv
```

所有 path / return / volatility / turnover / rank feature 必须在对应决策点收盘后可得（见 §7 availability 分区）。PIT membership 文件较大，实现必须按 instrument / date 过滤或 streaming chunk 读取，不得全量无过滤载入。

## 6. Two-stage Decision Design

### 6.1 统一事件主键与分母

12A6c 必须物化一个统一的 C0 risk_on 决策池：

```text
two_stage_event_universe.csv.gz
```

Row contract：

```text
one row = one C0 canonical risk_on event after scope filter
canonical_event_id is unique
same canonical_event_id cannot appear in multiple rows
```

统一主键：

```text
canonical_event_id
instrument
event_t0_date
event_t0_pos
trade_open_date
trade_open_pos
trade_open_price
event_split
board_bucket
market_regime_bucket
primary_family_id
```

Risk-on scope filter、split 边界、entry executability 必须复用 12A6b 的口径；若任一 row 的 entry / PIT membership / regime 不可证明，从 universe 排除并写入 `two_stage_scope_exclusion_audit.csv`。

### 6.2 Stage-1：t0 fast-fail rejector

```text
decision_point = event_t0_close (t0)
population = C0 risk_on two_stage_event_universe（全部 complete_executable rows）
feature_set = §7 stage_1 allowed features only (availability_time = event_t0_close)
target = stage_1_fast_fail_target（见 §8.1）
model = low-capacity meta-label classifier（见 §10）
action = keep / reject，by predeclared score threshold
```

Stage-1 输出每个 event 的 `stage1_keep_flag`。keep cohort 进入 stage-2 候选；reject cohort 退出。

### 6.3 Stage-2：entry+20 survivor continuation classifier

```text
decision_point = close at (entry_pos + 20)
population = stage-1 keep cohort 中 no_fast_fail_L10_H20 = true 且 day-20 决策点可执行的 survivors
feature_set = §7 stage_1 features + §7.12 realized 0-20d path features
target = stage_2_continuation_target（见 §8.2）
model = low-capacity meta-label classifier（见 §10）
action = continue / stand-down，by predeclared score threshold
```

Stage-2 分母必须显式声明为 day-20 survivor only，并处理 day-20 决策点的 executability 和 horizon completeness（见 §8.2、§9）。

### 6.4 决策点时间纪律

```text
stage_1_feature_availability_cutoff = event_t0_close
stage_2_decision_pos = entry_pos + 20
stage_2_feature_availability_cutoff = close at (entry_pos + 20)
stage_2_reference_pos = entry_pos + 21
stage_2_reference_price = executable open at stage_2_reference_pos
```

硬约束：

```text
no_future_feature_stage_1:
  stage-1 feature 不得使用任何 pos > event_t0_pos 的行情或 label。
no_future_feature_stage_2:
  stage-2 feature 不得使用任何 pos > (entry_pos + 20) 的行情或 label。
label_only:
  stage_1_fast_fail_target / stage_2_continuation_target 是 label，
  不得回流进任何 stage 的 feature matrix。
```

## 7. PIT Feature Contract

12A6c 的 feature 定义**继承 12A4 §7 PIT Feature Contract**，不重复发明。继承来源：

```text
inherited_feature_contract =
  requirement_12a4_state_change_meta_label_filter_feasibility.md §7
```

12A6c 必须输出：

```text
two_stage_feature_matrix.parquet
two_stage_feature_dictionary.csv
two_stage_feature_pit_audit.csv
```

每个 feature 必须在 dictionary 中记录（沿用 12A4 §7 字段，并新增 stage 归属）：

```text
feature_name
feature_group
source_artifact
calculation_rule
availability_time
lookback_window
missing_policy
pit_status
allowed_for_stage_1
allowed_for_stage_2
```

### 7.1 继承的 t0 feature groups（stage-1 与 stage-2 共用）

下列 12A4 §7 feature group 按原定义、原 PIT 规则、原 redundancy / winsorization / train-frozen 纪律继承到 12A6c，作为 `availability_time = event_t0_close` 的 t0 特征：

```text
12A4 §7.1  Event-native features
12A4 §7.2  Freshness / decay features        (第一优先 group，沿用)
12A4 §7.4  Density / crowding features
12A4 §7.5  Risk-on market context features
12A4 §7.6  Instrument pre-event path features
12A4 §7.7  Entropy / path disorder features  (含 redundancy audit 与 diagnostic-only 规则)
12A4 §7.8  Volume acceleration / decay features (含 redundancy audit)
12A4 §7.9  Cross-sectional rank features
12A4 §7.10 Failure / false-repair risk features (含 split_time_boundary_audit 与 expanding-prior 替代)
12A4 §7.11 R-core interaction features        (仅 primary-allowed 子集)
```

继承时必须保持 12A4 §7 的全部硬约束，重申其中对本需求最关键的几条：

```text
1. §7.1 source_arm_is_c0 / source_arm_is_r_core 只用于 population audit / benchmark readout，
   allowed_for_stage_1 = false，allowed_for_stage_2 = false。
   stage-1 / stage-2 primary model 训练行均来自 C0 risk_on population，
   不得依赖 source-arm identity 产生 uplift。
2. §7.7 / §7.8 凡 max_abs_redundancy_corr >= 0.95 的 entropy / volume-accel feature，
   allowed_for_stage_1 = false（diagnostic-only），stage-2 同样禁止。
3. §7.10 family_prior_train_* 若 split 时间边界不满足，
   只能用 expanding-prior-by-date 替代，不得直接进入 primary model。
4. §7.11 has_future_r_core_within_5_sessions 等 t0 不可知 feature 仍是 diagnostic-only，
   allowed_for_stage_1 = false，allowed_for_stage_2 = false。
```

继承的 t0 feature 在两个 stage 的可用性默认值：

```text
allowed_for_stage_1 = true  (除上述被 audit 降级者)
allowed_for_stage_2 = true  (t0 特征到 entry+20 决策点仍是过去信息，可继续作为上下文)
```

### 7.2 新增 stage-2 realized path feature group（§7.12 of 12A6c）

这是 12A6c 相对 12A4 §7 的唯一新增 group。它刻画 entry 后 [entry_pos, entry_pos + 20] 的已实现路径，只在 stage-2 决策点 entry+20 可用：

```text
feature_group = realized_path_0_20d
availability_time = close at (entry_pos + 20)
allowed_for_stage_1 = false
allowed_for_stage_2 = true
```

必需 feature（全部基于 [entry_pos, entry_pos + 20] 的 qfq OHLCV，相对 entry_price 归一）：

```text
realized_ret_to_close_20d
realized_max_high_return_0_20d
realized_min_low_return_0_20d
realized_close_to_max_high_drawup_0_20d
realized_close_to_min_low_drawdown_0_20d
realized_path_volatility_0_20d
realized_up_session_ratio_0_20d
realized_max_consecutive_up_sessions_0_20d
realized_max_consecutive_down_sessions_0_20d
sessions_since_min_low_0_20d
sessions_since_max_high_0_20d
realized_close_above_entry_session_ratio_0_20d
realized_turnover_zscore_trend_0_20d
realized_volume_zscore_trend_0_20d
realized_distance_to_20d_high_at_day20
realized_distance_to_60d_high_at_day20
realized_ma_5_20_spread_at_day20
realized_late_window_ret_10_20d
realized_early_window_ret_0_10d
realized_momentum_accel_early_late_0_20d
```

Construction rules：

```text
1. 全部窗口为 [entry_pos, entry_pos + 20]，闭区间，含 entry bar。
2. 任一 session 缺价或 volume <= 0，不参与该 feature 的 slope / ratio 计算；
   若有效 session 少于窗口的 0.8，feature 置 null，feature_status = insufficient_history。
3. 所有 ratio / acceleration feature 用 train-frozen p1 / p99 winsorization cutoffs，
   validation / robustness 只能复用 train cutoffs。
4. 这些 feature 严禁使用 pos > (entry_pos + 20) 的任何行情或 label。
5. realized path feature 不得回流进 stage-1 feature matrix。
```

12A6c 必须输出 realized-path redundancy audit：

```text
realized_path_feature_redundancy_audit.csv
```

字段与 12A4 §7.7 / §7.8 redundancy audit 同构：

```text
feature_name
split
coverage_rate
pearson_corr_vs_realized_ret_to_close_20d
spearman_corr_vs_realized_ret_to_close_20d
max_abs_redundancy_corr
redundancy_status
allowed_for_stage_2_after_audit
```

Redundancy rule：

```text
if max_abs_redundancy_corr >= 0.95:
  allowed_for_stage_2_after_audit = false
  redundancy_status = diagnostic_only_redundant_with_realized_return
if coverage_rate < 0.80:
  allowed_for_stage_2_after_audit = false
  redundancy_status = diagnostic_only_sparse_coverage
```

### 7.3 Single-feature frontier baselines

为判断每个 stage 的 uplift 是否只是单特征排序带来的，12A6c 必须输出 non-model single-feature frontier：

```text
stage_1_single_feature_frontier.csv   (按每个 stage-1-allowed feature 单独排序的 fast-fail 分层)
stage_2_single_feature_frontier.csv   (按每个 stage-2-allowed feature 单独排序的 continuation 分层)
```

任何 stage 的 supported decision 都必须证明 model top bucket 优于其最佳单特征 frontier，否则只能 partial。

## 8. Labels / Targets

12A6c 必须输出：

```text
two_stage_event_targets.csv.gz
```

Target 是 label，不得进入任何 stage 的 feature matrix。所有 barrier 触达用 qfq high / low，是乐观上界，必须在报告中注明 `high/low barrier touch = optimistic upper bound, not guaranteed executable fill`。

### 8.1 Stage-1 fast-fail target

Primary stage-1 target 复用 12A6b primary label：

```text
stage_1_fast_fail_target = fast_fail_L10_H20
entry = next executable open after event_t0
lower_barrier_pct = -0.10
horizon_sessions = 20
fast_fail = first low <= entry_price * (1 - 0.10) within 20 sessions
positive_class_for_rejector = fast_fail = true
```

12A6c 必须同时输出 stage-1 label grid，用于 scope / threshold revision（承接 12A6b §5.1）：

```text
horizon_sessions = [10, 20]
lower_barrier_pct = [-0.06, -0.08, -0.10, -0.12, -0.15, -0.20]
```

primary 仍固定为 `fast_fail_L10_H20`；其余 grid 只作 scope-revision readout，不得用 robustness 回头改 primary。

### 8.2 Stage-2 continuation target

Stage-2 决策点为 `entry_pos + 20` 收盘，target 是从下一可执行开盘向前的 triple-barrier continuation：

```text
stage_2_decision_pos = entry_pos + 20
stage_2_reference_pos = entry_pos + 21
stage_2_reference_price = executable open at stage_2_reference_pos
  (next executable open after the entry+20 decision close;
   if stage_2_reference_pos 不存在或 open 不可执行，
   stage_2_entry_blocked = true and row leaves stage-2 denominator)
```

Primary stage-2 target：

```text
stage_2_continuation_target = continuation_U20_L10_H2_20
upper_barrier_pct = +0.20
lower_barrier_pct = -0.10
horizon_sessions_h2 = 20
continuation = first high >= stage_2_reference_price * 1.20
               within stage_2_reference_pos ... stage_2_reference_pos + h2 inclusive
               and not first low <= stage_2_reference_price * 0.90
same_bar_priority = lower_first (conservative)
```

Horizon 口径必须和 12A6b 保持一致：`h2 = 20` 表示从 `stage_2_reference_pos`
到 `stage_2_reference_pos + 20` 的闭区间扫描（含 reference bar，共 21 个
daily rows）。如果实现选择“不含 reference bar”的替代口径，只能作为
diagnostic readout，不能进入 primary gate。

12A6c 必须同时输出 stage-2 target grid：

```text
horizon_sessions_h2 = [20, 40]
upper_barrier_pct = [0.10, 0.15, 0.20, 0.30]
lower_barrier_pct = [-0.08, -0.10, -0.12]
```

Stage-2 denominator rules：

```text
stage_2_candidate = stage1_keep_flag = true
stage_2_survivor = stage_2_candidate AND no_fast_fail_L10_H20 = true
stage_2_evaluable = stage_2_survivor
                    AND stage_2_entry_blocked = false
                    AND stage_2_horizon_complete = true
stage_2_horizon_complete = (stage_2_reference_pos + h2) < len(daily)
```

所有 stage-2 rate 的分母必须是 `stage_2_evaluable`，并显式输出 `stage_2_entry_blocked_n` 与 `stage_2_censored_n`。

Anchor 说明（必须在报告中写明）：

```text
stage_2 continuation 以 entry+20 close 后的 next executable open 为锚，
回答的是“在 entry+20 决策点是否值得继续持有 / 加仓”的边际问题，
不是从原始 entry 锚定的整体持有结局。
entry-anchored continuation 只作为 readout，不作为 stage-2 primary target。
```

### 8.3 Label completeness

```text
label_h20_complete   (stage-1 H=20 可观测)
label_stage2_h2_complete (stage-2 h2 可观测)
multi_episode_overlap_n  (同 instrument 多 episode window 重叠计数，仅 readout)
```

近端样本（horizon 不足）必须从对应 rate 分母剔除并单列，避免时间端点偏差。

## 9. Matched Random Baseline

两个 stage 都必须有 matched random baseline，复用 12A6b 的 matched random 机制和已落盘 sampled entries。

### 9.1 复用 12A6b sampled entries

```text
reuse_source =
  outputs/publishable/tables/12A6b_c0_risk_on_fast_fail_survival_uplift_audit/
  matched_random_sampled_entries.csv.gz
```

复用规则：

```text
1. random entries 已按 split / board_bucket / calendar_month / risk_on / PIT executable 匹配，
   并已排除 exact C0 keys；12A6c 不重新抽样，除非 12A6b sampled entries 不可读，
   此时必须用 12A6b §4.3 / §10 完全相同的协议重抽，base_seed = 120600，random_seed_n >= 100。
2. random entries 必须能映射到同一套 forward path，用于 stage-1 与 stage-2 baseline。
3. 所有 random 分位数必须按 sampled draw 或 sample_weight 聚合，不得按 unique path 去重。
```

### 9.2 Stage-1 baseline

```text
stage_1_random_fast_fail_rate_p05 / p50 / p95
```

判定方向：fast_fail_rate 越低越好。stage-1 keep cohort 必须与“在同等 keep 预算下随机保留”的 matched random 对比：

```text
keep_budget = stage1_keep_n / complete_executable_event_n
stage_1_random_keep_fast_fail_rate_pXX =
  在 matched random 中按相同 keep_budget 随机保留时的 fast_fail_rate 分布
```

stage-1 的 edge 必须体现为：rejector keep cohort 的 fast-fail rate 低于“随机保留相同比例”的 random p50。

### 9.3 Stage-2 baseline

Stage-2 必须对比 matched-random survivors（12A6b 已提供 `random_upper_touch_rate_given_no_fast_fail`），并按 day-20 anchored 口径重算：

```text
stage_2_random_continuation_rate_given_survivor_p05 / p50 / p95
```

stage-2 的 edge 必须体现为：continue cohort 的 continuation rate 高于“在 random survivors 中按相同 continue 预算随机保留”的 random p50。

### 9.4 Same-budget random retention protocol

所有 same-budget random baseline 必须 deterministic、label-free、feature-free，并在审计表中可复现。

```text
random_retention_cell = split x board_bucket x calendar_month
random_retention_rank =
  replacement_draw_index ASC,
  sample_draw_id ASC,
  instrument ASC,
  random_trade_open_date ASC,
  path_key ASC
```

C0 侧若字段名为 `event_split`，必须在 baseline join 前显式映射为 random artifact
中的 `split`；输出审计表统一使用 `split`。

Stage-1 random keep：

```text
for each seed and random_retention_cell:
  c0_cell_keep_budget =
    c0_stage1_keep_n_cell / c0_complete_executable_event_n_cell
  random_keep_n_cell =
    floor(c0_cell_keep_budget * random_complete_executable_n_cell)
  if floor gives 0 but c0_stage1_keep_n_cell > 0:
    random_keep_n_cell = 1
  select first random_keep_n_cell rows by random_retention_rank
```

Stage-2 random continue：

```text
for each seed and random_retention_cell:
  random_stage2_survivor =
    random_stage1_keep_flag = true
    AND random_no_fast_fail_L10_H20 = true
    AND random_stage_2_entry_blocked = false
    AND random_stage_2_horizon_complete = true
  c0_cell_continue_budget =
    c0_stage2_continue_n_cell / c0_stage2_evaluable_n_cell
  random_continue_n_cell =
    floor(c0_cell_continue_budget * random_stage2_survivor_n_cell)
  if floor gives 0 but c0_stage2_continue_n_cell > 0:
    random_continue_n_cell = 1
  select first random_continue_n_cell survivors by random_retention_rank
```

分位数聚合：

```text
1. 每个 seed 先得到一个 same-budget rate。
2. p05 / p50 / p95 对 seed-level rates 取分位数。
3. 若 12A6b sampled entries 提供 sample_weight，seed-level rate 必须用 sample_weight 加权。
4. 不得按 unique symbol-date 去重；重复 sampled draw 是 baseline 分布的一部分。
5. random_same_budget_audit 必须输出每个 split / cell / seed 的 model budget、random selected n、random denominator n。
```

## 10. Model / Threshold Protocol

### 10.1 模型容量

```text
primary_allowed_model = L2 logistic OR shallow decision tree depth <= 3
diagnostic_challenger_model = single LightGBM GBDT with capped depth/leaves
lightgbm_max_num_leaves <= 15
lightgbm_max_depth <= 3
lightgbm_min_data_in_leaf >= 100
lightgbm_n_estimators <= 100
no stacking, no deep nets, no AutoML search over hundreds of configs
```

Primary gate 只能由 `primary_allowed_model` 触发。LightGBM 若优于 primary，只能写入
diagnostic / challenger readout；若只有 LightGBM 通过 gate，最终 decision 至多为
partial，不能写成 `12A6c_two_stage_supported`。

每个 stage 独立训练，互不共享标签信息：

```text
stage_1_model fits on C0 risk_on full executable rows.
stage_2_model fits on stage_2_evaluable survivors only.
stage_2_model 不得使用 stage_1 的 fast-fail label 作为 feature。
```

### 10.2 预注册与多重比较防护

承接 12A4 §7.4.1 / research_plan 纪律：

```text
pre_registered_rule:
  每个 stage 的 score threshold 选择规则、keep_budget、continue_budget
  必须在跑 robustness / OOS 前写定于 config。
primary_budget:
  stage_1_keep_budget_primary = 0.50
  stage_2_continue_budget_primary = 0.50
diagnostic_budget_frontier:
  stage_1_keep_budget_grid = [0.30, 0.50, 0.70]
  stage_2_continue_budget_grid = [0.30, 0.50, 0.70]
single_candidate_in_sample:
  primary gate 固定使用 primary_budget；
  threshold 只由 train score quantile 冻结：
    stage-1 keep = lowest fast-fail risk scores at stage_1_keep_budget_primary
    stage-2 continue = highest continuation scores at stage_2_continue_budget_primary
oos_validate_only:
  robustness / OOS 只验证，不调参；
  禁止用 OOS 回头挑更好看的 threshold / horizon / feature / family。
```

Threshold ties 必须用 stable key 打破：

```text
tie_break_key = instrument_id ASC, event_t0_date ASC, entry_date ASC, event_key ASC
threshold_selection_source = train_only_fixed_budget
budget_tolerance_abs <= 0.005
```

若因为 score ties 或样本不足导致实际 retention/continue budget 偏离超过 tolerance，
必须在 `stage_threshold_health.csv` 中标记 `budget_health = fail`，该 stage 不能 supported。

### 10.3 Split 纪律

```text
split in [train, validation, robustness]
train: fit + threshold selection
validation: base-rate health + readout（薄片，不作 hard gate）
robustness: OOS validation only
```

`family_prior_*` 与任何 train-frozen 量必须严格只用 train 拟合后冻结，应用到 validation / robustness 不变。

## 11. Decision Gates

### 11.1 Input gates

必须全部通过：

```text
12A6b decision in [partial, supported] and primary_label = no_fast_fail_L10_H20
12A2 C0 canonical input read/schema pass
12A0/12A1 R-core registry read/schema pass
global regime calendar read/schema pass and date -> regime uniqueness pass
PIT executable daily read/schema pass
stock daily csv dir read pass and required OHLC schema pass
C0 risk_on event_n = 15,113 unless upstream artifact hash changed and report explains drift
matched random sampled entries reused or re-sampled under identical protocol
no_future_feature audit pass for both stages
```

### 11.2 Stage-1 support gate

内部 gate status `stage_1_status = supported` 需要同时满足：

```text
primary target = fast_fail_L10_H20
primary model family in primary_allowed_model
stage_1_threshold_health = pass
stage_1_random_same_budget_audit_status = pass

train:
  stage1_keep_n >= 500
  stage1_keep_fast_fail_rate <= stage_1_random_keep_fast_fail_rate_p50 - 0.03
  stage1_keep_fast_fail_rate <= c0_baseline_fast_fail_rate - 0.03
  stage1_keep_retention >= 0.50

robustness:
  stage1_keep_n >= 300
  stage1_keep_fast_fail_rate <= stage_1_random_keep_fast_fail_rate_p50 - 0.02
  stage1_keep_fast_fail_rate <= c0_baseline_fast_fail_rate - 0.02
  stage1_keep_retention >= 0.50

model_vs_single_feature:
  stage-1 model keep-cohort fast-fail rate 必须优于
  stage_1_single_feature_frontier 的最佳单特征同预算读数。
```

Stage-1 partial 只允许以下情形：

```text
stage_1_status = partial_train_only:
  train 满足所有 supported 条件，但 robustness 未同时跑赢 random p50 与 C0 baseline。
stage_1_status = partial_c0_only:
  train / robustness 跑赢 C0 baseline，但未稳健跑赢 same-budget random p50。
stage_1_status = partial_challenger_only:
  LightGBM challenger 满足 gate，但 primary_allowed_model 未满足 gate。
```

除此之外，stage-1 记为 `failed`。

### 11.3 Stage-2 support gate

内部 gate status `stage_2_status = supported` 需要同时满足（且 stage-1 必须先 supported 或 partial）：

```text
primary target = continuation_U20_L10_H2_20
primary model family in primary_allowed_model
stage_2_threshold_health = pass
stage_2_random_same_budget_audit_status = pass

train:
  stage_2_evaluable_n >= 300
  stage2_continue_n >= 150
  stage2_continue_continuation_rate >= stage_2_random_continuation_rate_given_survivor_p50 + 0.03

robustness:
  stage_2_evaluable_n >= 200
  stage2_continue_n >= 100
  stage2_continue_continuation_rate >= stage_2_random_continuation_rate_given_survivor_p50 + 0.02

model_vs_single_feature:
  stage-2 model continue-cohort continuation rate 必须优于
  stage_2_single_feature_frontier 的最佳单特征同预算读数。

realized_path_value:
  stage-2 (t0 features + realized_path_0_20d) top bucket 必须优于
  仅用 t0 features 的 stage-2 ablation top bucket，
  否则 realized path group 标记为 no_incremental_value 且 stage-2 只能 partial。
```

Stage-2 partial 只允许以下情形：

```text
stage_2_status = partial_p05_only:
  train 满足 supported 条件，robustness 未达到 random p50 + 0.02，
  但仍 >= random p05，且 sample-size gates pass。
stage_2_status = partial_no_realized_path_increment:
  continuation edge 成立，但 realized_path group 相对 t0-only ablation 没有增量。
stage_2_status = partial_challenger_only:
  LightGBM challenger 满足 gate，但 primary_allowed_model 未满足 gate。
```

Validation 只作 readout；若 validation 同时出现 stage-2 continue cohort continuation rate < random p05 且 base-rate health 不足，stage-2 降级 partial。若 stage-2 sample-size gates fail，stage-2 必须记为 `failed_insufficient_stage2_denominator`，不能 partial-supported。

### 11.4 Decision states

```text
12A6c_two_stage_supported
12A6c_stage1_supported_stage2_partial
12A6c_stage1_partial
12A6c_no_two_stage_feasibility
12A6c_blocked_input_or_baseline_failure
```

Decision mapping：

```text
if input gate fails:
  decision = 12A6c_blocked_input_or_baseline_failure
elif stage_1_status = failed:
  decision = 12A6c_no_two_stage_feasibility
elif stage_1_status startswith partial:
  decision = 12A6c_stage1_partial
elif stage_1_status = supported and stage_2_status startswith partial:
  decision = 12A6c_stage1_supported_stage2_partial
elif stage_1_status = supported and stage_2_status = failed:
  decision = 12A6c_stage1_supported_stage2_partial
elif stage_1_status = supported and stage_2_status = supported:
  decision = 12A6c_two_stage_supported
else:
  decision = 12A6c_stage1_partial
```

`next_allowed_requirement` 写入 decision：

```text
if 12A6c_two_stage_supported:
  next_allowed_requirement = requirement_12a7_two_stage_meta_label_oos_validation.md
elif 12A6c_stage1_supported_stage2_partial:
  next_allowed_requirement = requirement_12a6d_stage2_continuation_feature_revision.md
elif 12A6c_stage1_partial:
  next_allowed_requirement = requirement_12a6d_stage1_rejector_feature_or_label_revision.md
else:
  next_allowed_requirement = requirement_12a6d_fast_fail_scope_or_source_rethink.md
```

## 12. Required Outputs

### 12.1 Publishable tables

All outputs go under:

```text
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/
```

Required tables:

```text
input_artifact_audit.csv
two_stage_event_universe.csv.gz
two_stage_scope_exclusion_audit.csv
two_stage_feature_dictionary.csv
two_stage_feature_pit_audit.csv
two_stage_event_targets.csv.gz
realized_path_feature_redundancy_audit.csv
stage_threshold_health.csv
stage_1_model_card.csv
stage_2_model_card.csv
stage_1_score_bucket_readout.csv
stage_2_score_bucket_readout.csv
stage_1_single_feature_frontier.csv
stage_2_single_feature_frontier.csv
stage_1_random_same_budget_audit.csv
stage_2_random_same_budget_audit.csv
stage_2_ablation_readout.csv
stage_1_rejector_readout.csv
stage_2_continuation_readout.csv
stage_1_label_grid_readout.csv
stage_2_target_grid_readout.csv
two_stage_decision.csv
split_time_boundary_audit.csv
```

Required feature matrix (may be local cache if large, hash recorded in manifest):

```text
two_stage_feature_matrix.parquet
```

### 12.2 `stage_1_rejector_readout.csv`

Required columns:

```text
scope_id
split
model_id
model_family
primary_or_challenger
feature_list_hash
keep_budget
score_threshold
threshold_selection_source
budget_health
stage1_keep_n
stage1_keep_retention
stage1_keep_fast_fail_rate
c0_baseline_fast_fail_rate
stage_1_random_keep_fast_fail_rate_p05
stage_1_random_keep_fast_fail_rate_p50
stage_1_random_keep_fast_fail_rate_p95
fast_fail_abs_delta_vs_random_p50
fast_fail_abs_delta_vs_c0_baseline
best_single_feature_keep_fast_fail_rate
model_minus_best_single_feature
stage_1_status
diagnostic_only_flag
```

### 12.3 `stage_2_continuation_readout.csv`

Required columns:

```text
scope_id
split
model_id
model_family
primary_or_challenger
feature_list_hash
continue_budget
score_threshold
threshold_selection_source
budget_health
stage_2_evaluable_n
stage_2_entry_blocked_n
stage_2_censored_n
stage2_continue_n
stage2_continue_retention
stage2_continue_continuation_rate
survivor_base_continuation_rate
stage_2_random_continuation_rate_given_survivor_p05
stage_2_random_continuation_rate_given_survivor_p50
stage_2_random_continuation_rate_given_survivor_p95
continuation_abs_delta_vs_random_p50
best_single_feature_continue_continuation_rate
model_minus_best_single_feature
t0_only_ablation_continuation_rate
realized_path_incremental_value
stage_2_status
diagnostic_only_flag
```

### 12.4 `two_stage_decision.csv`

Required columns:

```text
decision_state
input_gate_status
stage_1_status
stage_2_status
stage_1_target_id
stage_1_model_id
stage_1_model_family
stage_1_keep_budget
stage_1_score_threshold
stage_1_threshold_health
stage_1_train_keep_fast_fail_rate
stage_1_train_random_keep_fast_fail_rate_p50
stage_1_train_c0_baseline_fast_fail_rate
stage_1_robustness_keep_fast_fail_rate
stage_1_robustness_random_keep_fast_fail_rate_p50
stage_2_target_id
stage_2_model_id
stage_2_model_family
stage_2_continue_budget
stage_2_score_threshold
stage_2_threshold_health
stage_2_train_continue_continuation_rate
stage_2_train_random_continuation_rate_given_survivor_p50
stage_2_robustness_continue_continuation_rate
stage_2_robustness_random_continuation_rate_given_survivor_p05
stage_2_robustness_random_continuation_rate_given_survivor_p50
realized_path_incremental_value
same_budget_random_audit_hash
feature_matrix_hash
gate_failure_reasons
next_allowed_requirement
```

### 12.5 Audit table minimum schemas

`stage_threshold_health.csv` required columns：

```text
stage
split
model_id
primary_budget
actual_budget
budget_abs_delta
score_threshold
threshold_selection_source
tie_break_key
budget_health
failure_reason
```

`stage_1_model_card.csv` / `stage_2_model_card.csv` required columns：

```text
stage
model_id
model_family
primary_or_challenger
fit_split
target_id
feature_list_hash
hyperparameter_json
class_weight_policy
train_event_n
train_positive_rate
threshold_selection_source
diagnostic_only_flag
```

`stage_1_random_same_budget_audit.csv` / `stage_2_random_same_budget_audit.csv`
required columns：

```text
stage
seed
split
board_bucket
calendar_month
model_budget
random_denominator_n
random_selected_n
sample_weight_sum
random_rate
retention_rank_rule
```

`stage_2_ablation_readout.csv` required columns：

```text
scope_id
split
model_id
feature_group
continue_budget
stage2_continue_n
continuation_rate
random_p50
incremental_value_vs_t0_only
ablation_status
```

### 12.6 Report / Manifest

Required report:

```text
outputs/publishable/reports/two_stage_fast_fail_rejector_continuation_report.md
```

Report 必须用中文，并包含：

1. 为什么从 12A6b partial 走向 two-stage（fast-fail rejector + continuation）；
2. 两个决策点的 PIT 时间纪律与 no-future-feature 边界；
3. stage-1 keep cohort 相对 matched random（同 keep 预算）与 C0 baseline 的 fast-fail uplift；
4. stage-2 day-20 survivor continuation 相对 matched random survivors 的 uplift；
5. realized 0-20d path feature group 是否提供增量价值（vs t0-only ablation）；
6. model 是否优于最佳单特征 frontier；
7. board / family / year 稳定性与 robustness 读数；
8. 为什么该结果仍不是交易收益策略；
9. 下一步是否允许进入 12A7 OOS validation。

Required manifest:

```text
outputs/manifests/12A6c_two_stage_fast_fail_rejector_continuation_feasibility_manifest.json
```

Manifest 必须包含所有 input / output hashes、feature matrix hash 和 decision state。

## 13. Tests

Required tests:

1. Stage-1 feature matrix contains no feature with `availability_time` after `event_t0_close`.
2. Stage-2 feature matrix contains no feature with `availability_time` after `close at entry_pos + 20`.
3. `realized_path_0_20d` features are `allowed_for_stage_1 = false` and never appear in stage-1 fit.
4. `stage_1_fast_fail_target` / `stage_2_continuation_target` never appear in any feature matrix.
5. `fast_fail_L10_H20` is true when a lower touch occurs within 20 sessions and false otherwise; day-20 touch counts, day-21 touch does not.
6. Entry-bar same-day low touch counts as fast-fail with `time_to_fast_fail_sessions = 0`.
7. Stage-2 denominator is `stage_2_evaluable`; survivors with `stage_2_entry_blocked` or incomplete h2 are excluded and counted.
8. Stage-2 reference price uses next executable open after the day-20 decision close; non-executable rows leave the stage-2 denominator.
9. Stage-2 continuation uses `lower_first` priority on same-bar conflicts.
10. Matched random reuse preserves sampled-draw / `sample_weight` denominator; no unique-path de-duplication.
11. Stage-1 random baseline uses the same `keep_budget` as the rejector keep cohort.
12. Stage-2 random baseline is computed among matched-random survivors at the same day-20 anchored horizon.
13. Threshold selection is fit on train only; robustness reuses train-frozen thresholds unchanged.
14. `family_prior_*` and any train-frozen cutoff are not refit on validation / robustness.
15. Single-feature frontier is computed for each allowed feature in each stage.
16. Stage-2 t0-only ablation is computed; `realized_path_incremental_value` reflects model-with-realized vs t0-only.
17. Global regime calendar blocks if one date maps to multiple regimes and filters non-date reconciliation rows.
18. Stock daily schema gate blocks if `date/open/high/low` is missing.
19. C0 risk_on event_n = 15,113 unless upstream hash changed and drift is reported.
20. Decision mapping: stage-1 gate failure yields `12A6c_no_two_stage_feasibility`; stage-1 supported + stage-2 fail yields `12A6c_stage1_supported_stage2_partial`.
21. Redundancy rule: realized-path feature with `max_abs_redundancy_corr >= 0.95` is `allowed_for_stage_2_after_audit = false`.
22. Required output schema test for every publishable table.
23. Manifest report hash sync test.
24. Stage-2 off-by-one test: `h2 = 20` scans `stage_2_reference_pos ... stage_2_reference_pos + 20` inclusive and `stage_2_horizon_complete` fails when the terminal bar is missing.
25. Fixed-budget test: primary stage-1 keep budget and stage-2 continue budget equal 0.50 within `budget_tolerance_abs`; diagnostic budget frontier cannot change primary gates.
26. Same-budget random audit test: every split / cell / seed selected n matches the deterministic cell budget rule and uses `random_retention_rank`.
27. Primary-vs-challenger test: LightGBM-only gate pass cannot produce `12A6c_two_stage_supported`.
28. Model-card and threshold-health schema tests for both stages, including `feature_list_hash`, `hyperparameter_json`, `threshold_selection_source`, and `budget_health`.

## 14. Non-goals

12A6c 明确不做：

- 不训练高容量黑箱模型、不做 AutoML 大规模搜索；
- 不做 policy replay、仓位、entry / exit、交易成本或资金曲线；
- 不声明最终可交易 alpha；
- 不改 12A2 C0 generation 或 12A6b primary label；
- 不把 big-winner overlap 当作 stage-1 或 stage-2 primary target；
- 不把 R-core 当作训练正样本 denominator；
- stage-1 不使用任何 t0 之后路径；stage-2 不使用任何 entry+20 之后路径；
- 不用 robustness / OOS 回头挑 threshold / feature / horizon / family；
- 不把单个 random seed 当作 baseline 结论；
- 不在 risk_off / transition 里找更好结果后反推 risk_on 支持。

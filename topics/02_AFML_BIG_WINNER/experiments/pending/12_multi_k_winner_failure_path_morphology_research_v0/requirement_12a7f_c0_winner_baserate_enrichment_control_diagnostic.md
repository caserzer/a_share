# 需求：12A7f C0 Winner Base-rate Enrichment Control Diagnostic

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
4. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag。
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、regime 日历冲突、winner label 不可复现、控制组配对不可证明时 fail closed。
6. 不得从报告文本或聚合表反推出事件、winner label 或逐行 path 结果。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A7f
run_id = 12A7f_c0_winner_baserate_enrichment_control_diagnostic
status = spec_draft_pending_review
expected_entrypoint = src/run_12a7f_c0_winner_baserate_enrichment_control_diagnostic.py
expected_config = configs/config_12a7f_c0_winner_baserate_enrichment_control_diagnostic.yaml
expected_test_file = tests/test_12a7f_c0_winner_baserate_enrichment_control_diagnostic.py
research_plan_source = research_plan_2_stage2_random_baseline_and_defense_participation.md
upstream_requirement_a = requirement_12a7d_stage2_random_baseline_support_triage.md
upstream_requirement_b = requirement_12a7e_defense_participation_frontier.md
```

本需求是 `research_plan_2_stage2_random_baseline_and_defense_participation.md` 之后的“步骤 0 回退诊断”。它**不实现** research_plan 中已编号的 12A8 / 12A9，而是先回答一个更上游、决定后续回退深度的问题。

本需求回答一个问题，且只回答一个问题：

```text
Q. C0 risk_on event 选出的人群，在 big-winner 右尾上是否相对一个同期、同 regime、
   同 board、同日历的“非 C0 可交易宇宙”控制组真正富集？
```

必须输出一个单一裁决：

```text
c0_winner_enrichment_status
```

## 2. 背景与核心动机

### 2.1 为什么现在必须做这个诊断

12A6c → 12A7 → 12A7b → 12A7c → 12A7d → 12A7e 的实跑链条得到一个高度一致的结构：

```text
stage-1 downside defense (volatility_20d asc) is supported on robustness:
  12A7b robustness delta_vs_random_p50 = -8.20pp, CI [-9.96pp, -6.37pp].

stage-2 big-winner continuation has never been strict-null supported:
  12A7c chained valid_seed_n = 0 / 100;
  12A7d best outcome = 12A7d_stage2_signal_diagnostic_only;
  12A7e stage-2 strict random support = insufficient for every stage1_X
       (max 29 valid seeds, all X).
```

12A7e 进一步证明：

```text
stage-1 X is a participation throttle, not a winner separator;
stage-2 selected positives expand roughly proportionally with the survivor denominator;
no single stage-1 X jointly preserves downside defense and recovers winner participation;
12A7e decision = 12A7e_x030_defense_optimal_for_downside_not_winner.
```

所有 winner 侧失败的共同形态是：**正样本稀薄、分母太薄、strict null 凑不齐 seed**。这种形态用 calibration（修概率刻度）或加模型容量都无法解决——它指向更上游的两个嫌疑：

```text
suspect_1 = winner label 定义（固定 +20% / -10% / 20 日 barrier）武断且 base-rate 非平稳
suspect_2 = C0 event 选错人群（C0 可能富集“不易暴跌也不易暴涨”的平庸标的）
```

### 2.2 这个诊断是回退深度的分水岭

```text
若 C0 相对控制组在 winner 右尾上明显富集:
  event 没选错 -> 回退到 label 层（vol-scaled winner label）并拆解串联架构。

若 C0 相对控制组在 winner 右尾上持平或更低:
  event 选错人群 -> 必须回退到 event 定义层重做，label / 架构修补无意义。
```

因此本诊断在任何 label 改造、calibration、policy replay 之前先做。它极便宜：不训练模型、不做 rank、不做 operating point，只比较两个无条件 base rate。

### 2.3 已有的部分证据与缺口

12A6c §0 已记录 C0 **内部**的无条件 winner base rate：

```text
全 risk_on, given no-fast-fail:
  +10% = 53.64%
  +15% = 36.20%
  +20% = 25.06%
```

但这只是 C0 自身的纵向数字，**缺少同期非 C0 控制组的同口径对照**。没有控制组，就无法判断 25.06% 是“高”还是“低”。本需求补的就是这个控制组，并把 C0 winner base rate 与之做配对比较。

## 3. 非目标

本需求明确不做：

- 不新增或修改 C0 state-change family formula、canonicalization priority 或 risk_on scope；
- 不重新定义 fast-fail / continuation / winner barrier，本需求**沿用现有固定 barrier**做对照（label 改造留给后续 label 层 requirement）；
- 不训练任何 stage-1 / stage-2 模型，不做 PIT trailing-rank，不做 operating point；
- 不做 probability calibration、Platt、isotonic、base-rate posterior correction；
- 不做 defense-participation frontier（已由 12A7e 完成）；
- 不声明可交易 alpha，不做仓位、交易成本、slippage、资金曲线或 policy replay；
- 不用控制组结果回头修改 C0 family、label 或任何上游 operating point；
- 不把本诊断当作 stage-2 selector 的支持证据；本诊断只裁决 event-level enrichment。

## 4. 必需输入

### 4.1 C0 event universe 与 winner label 来源

必需输入：

```text
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_candidate_event_canonical.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_universe.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_event_targets.csv.gz
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/two_stage_decision.csv
outputs/publishable/tables/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/split_time_boundary_audit.csv
outputs/local_cache/12A6c_two_stage_fast_fail_rejector_continuation_feasibility/stage2_path_cache.parquet
outputs/manifests/12A6c_two_stage_fast_fail_rejector_continuation_feasibility_manifest.json
```

`two_stage_event_universe.csv.gz` 是 C0 arm 的权威 event 来源，必须提供：

```text
meta_event_id
source_event_id
source_arm_id
instrument
event_t0_date
event_t0_pos
trade_open_date
trade_open_pos
trade_open_price
entry_date
entry_pos
entry_price
path_key
split
board_bucket
calendar_month
calendar_year
source_arm_is_c0
market_regime_bucket
stage_1_evaluable
entry_blocked
no_fast_fail_L10_H20
horizon_complete_20d
stage_2_decision_pos
stage_2_reference_pos
stage_2_reference_price
stage_2_entry_blocked
stage_2_horizon_complete_20d
stage_2_horizon_complete_40d
```

`two_stage_decision.csv` 必须提供：

```text
decision_state
input_gate_status
gate_failure_reasons (optional; missing -> empty string in audit)
```

`stage2_path_cache.parquet` 必须在 `input_artifact_audit.csv` 中证明以下 schema 与 join-key 唯一性：

```text
join_key =
  path_key
  instrument
  entry_pos
  entry_price

required_columns =
  path_key
  instrument
  entry_pos
  entry_price
  stage_2_decision_pos
  stage_2_reference_pos
  stage_2_reference_price
  stage_2_entry_blocked
  stage_2_horizon_complete_20d
  stage_2_horizon_complete_40d
  continuation_U10_L10_H2_20 (if present; else recompute)
  continuation_U15_L10_H2_20 (if present; else recompute)
  continuation_U20_L10_H2_20
  continuation_U20_L10_H2_40 (if present; else recompute)
```

若 `two_stage_event_universe.csv.gz` 缺少必需存活 / horizon / entry 列，但这些列可由 `stage2_path_cache.parquet` 或 qfq 日线通过唯一 join 重建，则必须在 `input_artifact_audit.csv` 标注 `schema_status = rebuilt_from_audited_cache`；否则 `input_gate_status = fail` 并 fail closed。

C0 winner label 必须从 `two_stage_event_targets.csv.gz` / `stage2_path_cache.parquet` / qfq 日线复现，不得从报告或聚合表反推。

### 4.2 控制组宇宙与日线来源

必需输入：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
```

`pit_topn_400_100_executable_daily.csv` 必须提供：

```text
usable_trade_date
instrument
source_membership_date
membership_date
membership_available_time
available_time
board_bucket
is_listed
is_st
is_suspended
```

控制组的 PIT 时间轴必须显式化：

```text
control_decision_date = source_membership_date
control_entry_date = usable_trade_date
control_entry_reference = qfq open on control_entry_date

control_split = split_time_boundary_audit bucket containing control_decision_date
control_calendar_month = month(control_decision_date)
control_calendar_year = year(control_decision_date)
control_market_regime_bucket = global regime calendar mapped on control_decision_date
```

若 `source_membership_date` 缺失、晚于 `usable_trade_date`、或不能证明在 `control_entry_date` 开盘前可得，则 `pit_gate_status = fail`。不得用 `usable_trade_date` 直接替代 decision date 来构造 match cell，除非该替代在 `input_artifact_audit.csv` 中被标为 explicit fallback 且与 C0 的 next-open 口径一致。

qfq 日线必须至少提供：

```text
date
open
high
low
```

全局 regime calendar 必须与 12A6b / 12A6c 完全同源：

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

Regime 映射规则与 12A6c §0 一致：只保留真实交易日，每个 date 必须且只能对应一个 `market_regime_bucket`；任一 date regime conflict 或 multi-regime 时 `global_regime_calendar_status = fail` 并 fail closed。所有 risk_on join 必须使用这个 `date -> market_regime_bucket` 映射，不得从 event key 字符串解析 regime。

### 4.3 输入闸

12A7f 可以执行的前提：

```text
12A6c two_stage_decision.input_gate_status = pass
12A2 state_change canonical events read_status = pass
global_regime_calendar_status = pass
pit_topn_400_100_executable_daily read_status = pass
stock daily csv dir read pass and required OHLC schema (date/open/high/low) pass
```

若任一前提失败：

```text
decision_state = 12A7f_blocked_input_or_pit_failure
```

## 5. Winner Label 定义（固定 barrier，分清 reference point）

本需求沿用现有固定 barrier，并在同一把尺子下度量 C0 与控制组；但必须区分两个 reference point，不得把 entry 起算的 event-level winner 与 12A6c stage-2 survivor continuation 混为同一口径。

```text
entry_reference = next executable open after event_t0 close（与 12A6b / 12A6c 一致）
fast_fail_label = fast_fail_L10_H20
  = [entry, entry+20] 内先触达 -10% lower barrier
no_fast_fail_L10_H20 = NOT fast_fail_L10_H20 且 stage-1 path 可评估
```

### 5.1 Primary label family: direct-entry event winner

Primary label family 用于本需求的最终裁决，回答“C0 event 入场后是否天然富集 big-winner”：

```text
label_family = direct_entry

direct_entry_win_up_10_h20 =
  [entry_reference, entry_reference+20] 内触达 +10% upper barrier 先于 -10% lower

direct_entry_win_up_15_h20 =
  [entry_reference, entry_reference+20] 内触达 +15% upper barrier 先于 -10% lower

direct_entry_win_up_20_h20 =
  [entry_reference, entry_reference+20] 内触达 +20% upper barrier 先于 -10% lower

direct_entry_win_up_20_h40 =
  [entry_reference, entry_reference+40] 内触达 +20% upper barrier 先于 -10% lower
```

`direct_entry_win_up_20_h40` 需要 entry+40 horizon，必须显式检查 horizon completeness；horizon 不完整的行计入 `winner_label_not_evaluable_n`，不得静默丢弃。

### 5.2 Secondary label family: post-survivor continuation reconciliation

Secondary label family 只用于复核 12A6c survivor continuation 口径与解释链条，不驱动 primary event-level enrichment 裁决：

```text
label_family = post_survivor_continuation

post_survivor_reference =
  stage_2_reference_pos / stage_2_reference_price
  （12A6c stage-2 continuation reference；不得用 entry_reference 代替）

post_survivor_continuation_U10_L10_H2_20 =
  no_fast_fail_L10_H20 survivor 从 post_survivor_reference 起算，
  20d 内触达 +10% upper barrier 先于 -10% lower

post_survivor_continuation_U15_L10_H2_20 =
  no_fast_fail_L10_H20 survivor 从 post_survivor_reference 起算，
  20d 内触达 +15% upper barrier 先于 -10% lower

post_survivor_continuation_U20_L10_H2_20 =
  no_fast_fail_L10_H20 survivor 从 post_survivor_reference 起算，
  20d 内触达 +20% upper barrier 先于 -10% lower

post_survivor_continuation_U20_L10_H2_40 =
  no_fast_fail_L10_H20 survivor 从 post_survivor_reference 起算，
  40d 内触达 +20% upper barrier 先于 -10% lower
```

12A6c §0 的 53.64% / 36.20% / 25.06% 只能作为 `post_survivor_continuation` family 的 C0 内部对账目标；不得用这些数字声称 `direct_entry` family 已复现 12A6c 口径。

### 5.3 Readout views

三个 readout 视角，必须分别报告：

```text
unconditional_winner_rate:
  label_family = direct_entry
  分母 = entry 可评估的全部事件（不先过 fast-fail）
  这是“event 入场后直接抓到 winner”的无条件视角

survivor_conditional_winner_rate:
  label_family = direct_entry
  分母 = no_fast_fail_L10_H20 = true 的 survivor
  这是“先活过 stage-1 防守后，entry 起算 winner 是否仍富集”的诊断视角

post_survivor_continuation_rate:
  label_family = post_survivor_continuation
  分母 = no_fast_fail_L10_H20 = true 且 stage-2 path 可评估的 survivor
  这是与 12A6c stage-2 continuation 同 reference-point 的对账视角
```

Winner label 必须对 C0 arm 与控制组用**完全相同的 barrier 引擎和同一份 qfq 日线**计算，禁止两侧使用不同的价格源或 horizon 口径。

`winner_label_source_audit.csv` 必须记录 `label_family`、`winner_barrier`、`reference_pos_source`、`label_source`、`horizon_complete_flag` 与 `reconciliation_status`。任一 primary label 不可复现时 `winner_label_reproduction_status = fail` 并 fail closed；secondary reconciliation 失败时必须报告，但只有当失败来自输入 schema / PIT / price path 不可证明时才阻塞 primary 裁决。

## 6. C0 Arm 定义

C0 primary scope：

```text
source_arm_is_c0 = true
market_regime_bucket = risk_on
stage_1_evaluable = true
entry_blocked = false
```

C0 arm 的 winner label 优先复用 12A6c 已落地的 path 结果；当某个 winner barrier（尤其 `direct_entry_win_up_20_h40` 或 `post_survivor_continuation_U20_L10_H2_40`）在 12A6c artifacts 中不存在时，必须用 §5 的同一引擎在 qfq 日线上重算，并在 `winner_label_source_audit.csv` 标注来源（`reused_from_12a6c` 或 `recomputed_in_12a7f`）。

## 7. 控制组定义与配对

### 7.1 控制组宇宙

控制组是“非 C0 的同期可交易宇宙入场点”。

```text
control_universe_source = pit_topn_400_100_executable_daily
control_entry_eligible:
  instrument 在 control_entry_date = usable_trade_date 属于 executable universe
  且 control_entry_date open 可成交（非停牌、有 qfq open）
  且 control_decision_date = source_membership_date 在 control_entry_date 开盘前可得
control_market_regime_bucket = risk_on（用同一 regime calendar 映射到 control_decision_date）
control_is_not_c0:
  control_decision_key = instrument x control_decision_date
    不得命中任何 C0 canonical event 的 instrument x event_t0_date
  control_entry_key = instrument x control_entry_date
    不得命中任何 C0 primary-scope event 的 instrument x entry_date / trade_open_date
```

控制组入场点的 entry reference / fast-fail / winner barrier 必须与 C0 arm 用 §5 完全相同的规则计算。控制组的 synthetic event row 必须显式生成：

```text
control_uid = stable_hash(instrument, control_decision_date, control_entry_date)
control_event_t0_date = control_decision_date
control_trade_open_date = control_entry_date
control_entry_pos = qfq date_pos(control_entry_date)
control_entry_price = qfq open(control_entry_date)
```

C0 match cell 使用 `event_t0_date` 所在的 split / calendar_month / market_regime_bucket；control match cell 使用 `control_decision_date` 所在的 split / calendar_month / market_regime_bucket。不得把 C0 的 `entry_date` 与 control 的 `usable_trade_date` 直接拿来做 regime / month cell。

### 7.2 配对协议（核心，防止 regime / board / calendar 混淆）

C0 与控制组的比较**必须在配对单元内**进行，不得用全样本平均直接相减。

```text
match_cell_key =
  split
  board_bucket
  calendar_month
  market_regime_bucket (= risk_on)
```

控制组抽样：

```text
for each match_cell:
  c0_entry_n = count(C0 primary scope events in cell)
  draw control entries from control_entry_eligible rows in the same cell
control sampling must be reproducible:
    seed-driven, without replacement inside each match_cell,
    stable ordering by instrument, control_decision_date, control_entry_date, then control_uid
  控制组每 cell 抽取数量 = control_match_multiplier * c0_entry_n
    （control_match_multiplier 在 config 预注册，默认 = 1；可设 >1 以降低控制组抽样方差）
```

Primary readout 使用一份 canonical control sample：

```text
control_sample_seed = 120713
control_sampling_mode = without_replacement_fixed_canonical_sample
```

Bootstrap 默认在 canonical sample 内重抽，不得在每个 bootstrap replicate 偷偷改 seed 或从全 eligible pool 重新抽样。若实现选择额外报告 control sampling sensitivity，必须预注册 `control_seed_sensitivity_seed_n`，并作为诊断附录输出；不得用 sensitivity 中的 best seed 改写 primary decision。

配对有效性：

```text
match_cell_status = matched
  iff control_entry_eligible_n_in_cell >= control_match_multiplier * c0_entry_n

match_cell_status = control_short
  iff 0 < control_entry_eligible_n_in_cell < control_match_multiplier * c0_entry_n

match_cell_status = control_zero
  iff control_entry_eligible_n_in_cell = 0
```

短缺处理（fail-closed，不得静默放宽）：

```text
matched_c0_entry_coverage =
  sum(c0_entry_n for matched cells) / sum(c0_entry_n for all cells)

if matched_c0_entry_coverage < control_match_min_coverage (config, 默认 0.90):
  control_match_status = fail
  decision_state = 12A7f_blocked_control_match_failure
```

`control_short` / `control_zero` 的 cell 必须全部记录在 `control_match_cell_audit.csv`，包括短缺数量与原因，不得用更粗 cell 粒度回填后冒充 matched。

## 8. Enrichment 度量

对每个 label family、winner barrier、readout 视角（unconditional / survivor_conditional / post_survivor_continuation）、每个 split，计算：

```text
label_family
readout_view
winner_barrier
split
c0_entry_n
c0_survivor_n
c0_denominator_n
c0_winner_positive_n
c0_winner_rate
control_entry_n
control_survivor_n
control_denominator_n
control_winner_positive_n
control_winner_rate
winner_rate_diff = c0_winner_rate - control_winner_rate
winner_rate_ratio = c0_winner_rate / control_winner_rate
matched_c0_entry_coverage
fast_fail_rate_c0
fast_fail_rate_control
fast_fail_rate_diff = fast_fail_rate_c0 - fast_fail_rate_control
```

Denominator 规则：

```text
if readout_view = unconditional:
  c0_denominator_n = c0_entry_evaluable_n
  control_denominator_n = control_entry_evaluable_n

if readout_view = survivor_conditional:
  c0_denominator_n = c0_no_fast_fail_survivor_n
  control_denominator_n = control_no_fast_fail_survivor_n

if readout_view = post_survivor_continuation:
  c0_denominator_n = c0_no_fast_fail_survivor_stage2_path_evaluable_n
  control_denominator_n = control_no_fast_fail_survivor_stage2_path_evaluable_n
```

`c0_entry_n` / `control_entry_n` 必须保留为审计列，但不得在 survivor_conditional 或 post_survivor_continuation 视角中冒充 denominator。

配对差值必须在 match_cell 内计算后再聚合（cell-weighted），不得用两侧全样本均值直接相减：

```text
cell_winner_rate_diff = c0_cell_winner_rate - control_cell_winner_rate
aggregated_winner_rate_diff =
  sum(c0_denominator_n_cell * cell_winner_rate_diff) / sum(c0_denominator_n_cell)
```

方向：

```text
winner_rate_diff > 0 表示 C0 在该 winner barrier 上相对控制组富集
fast_fail_rate_diff < 0 表示 C0 在 downside 上更安全（与既有 stage-1 结论应一致）
```

## 9. 统计闸

Bootstrap 设置：

```text
seed = 120713
n_resamples >= 2000
ci_low_q = 0.025
ci_high_q = 0.975
bootstrap_min_c0_denominator_n = 100
bootstrap_min_winner_positive_n = 30
bootstrap_min_valid_replicates = 1500
```

配对 CI：

```text
使用 paired-by-cell bootstrap。
每个 replicate 先按 match_cell 重抽 cell，再在 cell 内从 C0 rows 与 canonical control sample rows 中有放回重抽 denominator rows，
重算 aggregated_winner_rate_diff，再取 CI。

canonical 字段：
  winner_rate_diff_ci95_low / high
```

Bootstrap 不得在 replicate 内重新生成 canonical control sample；control sampling uncertainty 只可通过预注册的 sensitivity appendix 单独报告。

主裁决基于 robustness split 的 `label_family = direct_entry`、`readout_view = unconditional`、`direct_entry_win_up_20_h20` 与 `direct_entry_win_up_20_h40` 两个 big-winner barrier。`survivor_conditional` 与 `post_survivor_continuation` 视角必须报告，但不改变 primary event-level enrichment 裁决，除非它们暴露输入/PIT/label 复现失败。

Enrichment 判定（robustness）：

```text
c0_winner_enrichment = positive_for_barrier iff
  matched_c0_entry_coverage >= control_match_min_coverage
  c0_denominator_n >= 100
  c0_winner_positive_n >= 30
  bootstrap_replicate_valid_n >= 1500
  winner_rate_diff >= +0.02
  winner_rate_diff_ci95_low > 0

c0_winner_enrichment = negative_for_barrier iff
  matched_c0_entry_coverage >= control_match_min_coverage
  c0_denominator_n >= 100
  bootstrap_replicate_valid_n >= 1500
  winner_rate_diff <= -0.02
  winner_rate_diff_ci95_high < 0

c0_winner_enrichment = uncertain_for_barrier otherwise
```

注意：本需求**不要求** stage-2 strict random support；它度量的是 event-level enrichment，不是 stage-2 selector。

## 10. 稳定性诊断

必需切片：

```text
split
calendar_year
board_bucket
market_regime_bucket (= risk_on)
```

每个 `c0_denominator_n >= 100` 的切片，报告：

```text
label_family
readout_view
winner_barrier
c0_entry_n
c0_denominator_n
c0_winner_rate
control_winner_rate
winner_rate_diff
matched_c0_entry_coverage
enrichment_direction_status
```

`enrichment_direction_status`：

```text
positive = winner_rate_diff > 0 且 cell 配对覆盖充分
flat = abs(winner_rate_diff) <= 0.01
negative = winner_rate_diff < -0.01
insufficient_n = c0_denominator_n < 100
```

robustness 中出现 sign inversion（部分 winner barrier 富集、部分为负）必须在报告中显式指出，并影响最终裁决等级。

## 11. Decision Map

```text
12A7f_c0_winner_enriched_event_supported:
  robustness 下 label_family = direct_entry、readout_view = unconditional 的
  direct_entry_win_up_20_h20 与 direct_entry_win_up_20_h40 均达到 positive_for_barrier；
  含义：C0 event 确实富集 big-winner -> 回退到 label 层，不必回退 event 层。

12A7f_c0_winner_enrichment_weak_or_horizon_dependent:
  robustness 下 primary direct-entry big-winner barrier 没有任何 negative_for_barrier，
  且满足以下任一条件：
    a) direct_entry_win_up_20_h20 与 direct_entry_win_up_20_h40 只有一个 positive_for_barrier；
    b) direct_entry_win_up_10_h20 或 direct_entry_win_up_15_h20 positive_for_barrier，
       但两个 +20% big-winner barrier 均为 uncertain_for_barrier；
  含义：C0 抓到的是“小涨”而非 big-winner -> label 层需重定义 winner 形态，
        event 层暂不推翻但需在 label requirement 中重审 C0 适配性。

12A7f_c0_winner_not_enriched_event_revision_required:
  robustness 下任一 primary direct-entry big-winner barrier negative_for_barrier，
  或两个 primary direct-entry big-winner barrier 均不为 positive_for_barrier，
  且低阈值 / 短 horizon 也无法触发 weak_or_horizon_dependent；
  含义：C0 未富集 big-winner -> 必须回退到 event 定义层重做，
        label / calibration / 架构修补对 winner 目标无意义。

12A7f_blocked_control_match_failure:
  控制组配对覆盖不足，无法构造可信对照。

12A7f_blocked_input_or_pit_failure:
  必需输入、PIT、regime 日历或 winner label 复现失败。
```

Decision precedence（互斥）：

```text
1. 若 input / PIT / regime / winner-label 复现失败:
     decision_state = 12A7f_blocked_input_or_pit_failure

2. 否则若控制组配对覆盖 < control_match_min_coverage:
     decision_state = 12A7f_blocked_control_match_failure

3. 否则若 robustness 下 direct_entry / unconditional 的
   direct_entry_win_up_20_h20 与 direct_entry_win_up_20_h40 均 positive_for_barrier:
     decision_state = 12A7f_c0_winner_enriched_event_supported

4. 否则若 primary direct-entry big-winner barrier 没有 negative_for_barrier，
   且（只有一个 +20% big-winner barrier positive_for_barrier，
      或仅 direct_entry_win_up_10_h20 / direct_entry_win_up_15_h20 positive_for_barrier）:
     decision_state = 12A7f_c0_winner_enrichment_weak_or_horizon_dependent

5. 否则:
     decision_state = 12A7f_c0_winner_not_enriched_event_revision_required
```

`next_allowed_requirement` 映射：

```text
if decision_state = 12A7f_c0_winner_enriched_event_supported:
  next_allowed_requirement = none
  recommended_internal_followup = vol_scaled_winner_label_and_decoupled_selector_redesign

if decision_state = 12A7f_c0_winner_enrichment_weak_or_horizon_dependent:
  next_allowed_requirement = none
  recommended_internal_followup = winner_label_form_revision_with_c0_fitness_recheck

if decision_state = 12A7f_c0_winner_not_enriched_event_revision_required:
  next_allowed_requirement = none
  recommended_internal_followup = event_definition_layer_rebuild_before_any_label_work

if decision_state starts with 12A7f_blocked:
  next_allowed_requirement = none
  recommended_internal_followup = gate_specific_failure_triage
```

## 12. 必需输出

publishable tables：

```text
outputs/publishable/tables/12A7f_c0_winner_baserate_enrichment_control_diagnostic/
```

必需表：

```text
input_artifact_audit.csv
scope_universe_audit.csv
winner_label_source_audit.csv
control_match_cell_audit.csv
c0_vs_control_winner_baserate_readout.csv
winner_baserate_bootstrap_ci.csv
enrichment_stability_slice_audit.csv
c0_winner_enrichment_decision.csv
```

`control_match_cell_audit.csv` 必需字段：

```text
split
board_bucket
calendar_month
calendar_year
market_regime_bucket
c0_entry_n
control_entry_eligible_n
control_sampled_n
control_match_multiplier
match_cell_status
control_shortfall_n
matched_c0_entry_coverage_contribution
control_sample_seed
control_sampling_mode
```

`c0_vs_control_winner_baserate_readout.csv` 必需字段：

```text
label_family
readout_view
winner_barrier
split
c0_entry_n
c0_survivor_n
c0_denominator_n
c0_winner_positive_n
c0_winner_rate
control_entry_n
control_survivor_n
control_denominator_n
control_winner_positive_n
control_winner_rate
winner_rate_diff
winner_rate_ratio
matched_c0_entry_coverage
fast_fail_rate_c0
fast_fail_rate_control
fast_fail_rate_diff
winner_label_reproduction_status
winner_label_reconciliation_status
```

`winner_baserate_bootstrap_ci.csv` 必需字段：

```text
label_family
readout_view
winner_barrier
split
n_resamples
bootstrap_replicate_valid_n
bootstrap_min_valid_replicates
winner_rate_diff
winner_rate_diff_ci95_low
winner_rate_diff_ci95_high
c0_denominator_n
c0_winner_positive_n
control_denominator_n
control_winner_positive_n
barrier_enrichment_status
control_sample_seed
bootstrap_control_redraw_flag
```

`enrichment_stability_slice_audit.csv` 必需字段：

```text
slice_type
slice_value
label_family
readout_view
winner_barrier
c0_entry_n
c0_denominator_n
control_denominator_n
c0_winner_rate
control_winner_rate
winner_rate_diff
matched_c0_entry_coverage
enrichment_direction_status
```

`c0_winner_enrichment_decision.csv` 必需字段：

```text
decision_state
input_gate_status
global_regime_calendar_status
control_match_status
matched_c0_entry_coverage
c0_winner_enrichment_status
primary_label_family
primary_readout_view
winner_label_reproduction_status
winner_label_reconciliation_status
primary_barrier_direct_entry_win_up_20_h20_winner_rate_diff
primary_barrier_direct_entry_win_up_20_h20_ci95_low
primary_barrier_direct_entry_win_up_20_h20_ci95_high
primary_barrier_direct_entry_win_up_20_h40_winner_rate_diff
primary_barrier_direct_entry_win_up_20_h40_ci95_low
primary_barrier_direct_entry_win_up_20_h40_ci95_high
robustness_fast_fail_rate_diff
next_allowed_requirement
recommended_internal_followup
```

Report：

```text
outputs/publishable/reports/c0_winner_baserate_enrichment_control_report.md
```

Manifest：

```text
outputs/manifests/12A7f_c0_winner_baserate_enrichment_control_diagnostic_manifest.json
```

Local cache：

```text
outputs/local_cache/12A7f_c0_winner_baserate_enrichment_control_diagnostic/c0_arm_winner_label_matrix.parquet
outputs/local_cache/12A7f_c0_winner_baserate_enrichment_control_diagnostic/control_arm_winner_label_matrix.parquet
outputs/local_cache/12A7f_c0_winner_baserate_enrichment_control_diagnostic/bootstrap_replicates.parquet
```

Manifest 必须包含每个 publishable table、report、config、requirement、local-cache artifact 的 sha256；report 与 manifest hash 必须在报告生成后同步。

## 13. 报告要求

报告须用中文，并 lead with：

```text
final decision_state
c0_winner_enrichment_status
control_match_coverage
direct_entry_win_up_20_h20 / direct_entry_win_up_20_h40 的 C0 vs control winner rate 与配对 diff + CI（robustness）
primary direct-entry unconditional 视角，以及 survivor_conditional / post_survivor_continuation 二级视角对照
fast_fail_rate_diff（应复核与既有 stage-1 防守结论一致）
回退裁决：label 层 / event 层 / 阻塞
recommended next step
```

报告必须显式说明：

```text
本诊断只度量 event-level winner enrichment，不度量 stage-2 selector，不声明 alpha。
Winner label 沿用现有固定 barrier；primary 裁决使用 direct-entry family，post-survivor continuation 只作 12A6c 口径对账。
控制组是同 decision-date split x board x month x risk_on 配对的非 C0 可交易宇宙入场点。
结论只适用于 C0 risk_on scope 与当前固定 -10% / +20% 口径。
```

必答 findings：

```text
1. C0 相对控制组在 direct-entry big-winner 右尾上是否富集，富集多少，CI 是否过零。
2. 富集是否只存在于低阈值 / 单一 horizon（即 C0 抓的是“小涨”还是“大赢家”）。
3. post-survivor continuation 对账是否与 12A6c survivor continuation 口径一致。
4. C0 的 downside 优势（fast_fail_rate_diff）是否与既有 stage-1 结论一致。
5. 回退裁决：应回退到 label 层还是 event 定义层，理由。
```

## 14. 测试清单

1. 路径解析覆盖 `topics/` / `data/` / `outputs/` / `configs/` / `src/` / `tests/` 前缀。
2. Input artifact audit 记录每个必需输入的 sha256 / row count / schema / read status，缺失即 fail-closed；`two_stage_decision.csv`、`stage2_path_cache.parquet` 与 PIT executable schema 必须被显式校验。
3. C0 arm scope 严格限定 `source_arm_is_c0 = true`、`market_regime_bucket = risk_on`、`stage_1_evaluable = true`、`entry_blocked = false`。
4. Regime 映射来自 global regime calendar，date conflict / multi-regime 时 fail-closed；不得从 event key 解析 regime。
5. 控制组时间轴固定为 `control_decision_date = source_membership_date`、`control_entry_date = usable_trade_date`；split/month/regime 必须从 decision date 派生，不得用 entry date 偷换。
6. 控制组同时排除所有 C0 canonical decision key 与 primary-scope entry key（instrument x date 去重排除）。
7. C0 与控制组使用**同一** winner barrier 引擎和同一 qfq 日线，价格源/horizon 不一致即 fail-closed。
8. `direct_entry_win_up_20_h40` 与 `post_survivor_continuation_U20_L10_H2_40` horizon 不完整的行计入 `winner_label_not_evaluable_n`，不得静默丢弃。
9. direct-entry 与 post-survivor continuation 两个 label family 使用不同 reference point；post-survivor continuation 才允许与 12A6c §0 survivor continuation 数字对账。
10. 配对在 `split x board_bucket x calendar_month x risk_on` cell 内进行；全样本均值直接相减被禁止（test 验证 cell-weighted 聚合）。
11. `matched_c0_entry_coverage < control_match_min_coverage` 时 `decision_state = 12A7f_blocked_control_match_failure`。
12. `control_short` / `control_zero` cell 全部记录，且不得用更粗粒度回填冒充 matched。
13. unconditional、survivor_conditional、post_survivor_continuation 三个视角都被计算并独立报告；survivor/post-survivor 视角使用 `c0_denominator_n` 而非 `c0_entry_n`。
14. 控制组 primary sample 必须是 fixed canonical sample；bootstrap 不得在 replicate 内重新抽 control seed。
15. paired-by-cell bootstrap 计算 `winner_rate_diff_ci95_low/high`；非配对 bootstrap 被禁止。
16. Enrichment 主裁决使用 robustness split 的 `direct_entry_win_up_20_h20` 与 `direct_entry_win_up_20_h40`，且二者都 positive 才能进入 enriched_event_supported。
17. 本需求不依赖、不要求 stage-2 strict random support。
18. Decision precedence 互斥；blocked 状态优先于 enrichment 裁决。
19. Required output schemas 与实际输出列一致；新增/缺失核心列必须在 schema audit 中 fail-closed。
20. Report 与 manifest hash 同步；report 复现 decision.csv headline 数字。

## 15. One-line Thesis

12A7f 在任何 label 改造或 calibration 之前先做一件最便宜的事：用同期、同 regime、同 board、同日历配对的非 C0 控制组，判定 C0 event 到底有没有富集 big-winner 右尾——富集就回退到 label 层，不富集就必须回退到 event 定义层重做，从而避免在一个选错人群的 event 上继续堆叠 stage-2 / calibration 工作。

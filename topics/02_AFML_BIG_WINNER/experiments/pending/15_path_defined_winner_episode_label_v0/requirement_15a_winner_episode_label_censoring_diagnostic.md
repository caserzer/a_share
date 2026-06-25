# 需求：15A Path-Defined Winner Episode Label Censoring Diagnostic

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/15_path_defined_winner_episode_label_v0
SOURCE_EP14_ROOT = TOPIC_ROOT/experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0
SOURCE_EP13_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
SOURCE_EP12_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 以 `SOURCE_EP14_ROOT/`、`SOURCE_EP13_ROOT/`、`SOURCE_EP12_ROOT/` 表达的路径必须先解析到对应 episode root，再写入 `input_artifact_audit.csv`。
5. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
6. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、universe membership 不可证明、price path completeness 不可证明、censoring boundary 不可证明时 fail closed。
7. 不得从报告文本、图像、人工讨论文本、聚合 readout 或未来标签反推出逐行 universe、episode membership、label、split 边界、entry 价格或 decision point。

## 1. 实验身份

```text
experiment_id = 15_path_defined_winner_episode_label_v0
phase_id = 15A
run_id = 15A_winner_episode_label_censoring_diagnostic
status = spec_ready_for_implementation_review
expected_entrypoint = src/run_15a_winner_episode_label_censoring_diagnostic.py
expected_config = configs/config_15a_winner_episode_label_censoring_diagnostic.yaml
expected_test_file = tests/test_15a_winner_episode_label_censoring_diagnostic.py
source_plan = EXPERIMENT_ROOT/research_plan.md
upstream_requirement_14a = SOURCE_EP14_ROOT/requirement_14a_full_native_sparse_state_change_event_utility_preflight.md
upstream_requirement_12a7g = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
```

15A 是 Episode 15 的第一份执行 requirement，也是整个 topic 第一次正面质疑 **winner label 定义本身**。Episodes 01-14 全部继承同一个 fixed-horizon、vol-scaled triple-barrier label，并在其上反复失败：

```text
ranking / recall / probability readout repeatedly exists,
but it does not transport into after-cost full-denominator entry utility,
and positive signal repeatedly collapses back into compression / drawdown-reversal morphology.
```

15A 检验一个更底层的、此前从未被检验过的怀疑：

```text
fixed-horizon winner label right-censors slow big winners.
当一个标的的真实大涨幅 episode 走完所需的交易日数超过固定 horizon 时，
它在 fixed-horizon label 下不被标记为 winner，反而被当作 negative，
从而系统性地把研究推向短期爆发 / compression / reversal 形态。
```

15A 的目标不是寻找信号，不是入场，不是建模。15A 只回答一个 label 定义问题：

```text
用 path-defined、无 horizon 上限、显式右删失隔离的 winner episode label，
相对当前 fixed-horizon label，到底漏掉了多少大赢家、漏掉的是什么形态、
right-censoring 是否被正确隔离而非污染 negative 类。
```

术语冻结：

```text
15A 的 primary 统计单位是 anchor row，不是去重后的唯一市场 episode。
anchor_record_unit = instrument x reference_date
label_record_unit = instrument x reference_date x threshold_id

"winner episode label" 表示：从该 anchor 的 next-open entry 出发，未来 price path
是否首次触达预注册 threshold。所有 winner / slow-winner rate 都是 anchor-row rate。

15A 不得把 anchor-row count 解释成 unique market episode count。
为避免连续 anchor 对同一上涨 episode 重复计数被误读，必须另行输出
episode_overlap_density_audit.csv，报告 anchor-row overlap density。
```

15A 不得产生任何交易、仓位、alpha、entry、meta-labeling、模型或 label 部署授权。即使 15A 显示 fixed-horizon label 严重漏标，15A 也只能授权新建：

```text
requirement_15b_path_defined_winner_separability_diagnostic.md
```

## 2. 核心问题

15A 回答以下问题：

```text
Q1. 在当前 PIT topn 400/100 universe 上，能否用 raw qfq bars 确定性地构造
    path-defined winner episode label：从某个 anchor 起，首次累计涨幅达到阈值，
    无 horizon 上限，未达标且走到数据末尾的标记为 right-censored？

Q2. 相对 fixed-horizon baseline label（vol-scaled triple barrier H20，以及
    primary fixed 120d / 50% contrast + 三档 threshold-matched fixed120 sensitivity），
    path-defined label 多标记了多少 winner？
    多标记的这批的 time-to-threshold 分布是什么（130 天？300 天？）？

Q3. 被 fixed-horizon 漏掉、但被 path-defined 标记的 "slow winner"，其 t0-close
    可观测形态是否与 Episodes 13/14 反复重新发现的 compression / drawdown-reversal
    形态不同（即是否提供了一个新的、未被证伪的 morphology surface）？

Q4. right-censored anchor rows（走到数据末尾仍未达标）有多少？它们是否被正确隔离为
    censored，而不是被当作 confirmed negative 污染对照？

Q5. 阈值在 {50%, 100%, 150%} 三档下，winner base rate、slow-winner share、
    censoring rate 如何变化？哪一档既有足够 winner 密度、又有可管理的 censoring？
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. Scope Boundary

15A 允许做：

```text
1. 复用 14A / 13A native opportunity universe lineage 与 split boundary；
2. 从 PIT universe 与 raw qfq bars 重建 t0-close 可观测的 anchor 与 price path；
3. 构造 path-defined、无 horizon 上限、右删失隔离的 winner episode label（50% / 100% / 150% 三档）；
4. 构造 fixed-horizon baseline label：vol-scaled triple-barrier H20（继承 12A7g）与三档 threshold-matched fixed120 grid；
5. 量化 path-defined vs fixed-horizon 的 winner set 差异、slow-winner share、time-to-threshold 分布；
6. 对 slow-winner 做 t0-close 可观测 morphology readout，与 13/14 已失败形态做 overlap 诊断；
7. 量化 right-censoring rate 并审计其隔离正确性；
8. 输出确定性 next-research decision map。
```

15A 明确不是：

```text
signal / feature search
separability test
event mining
sequence mining
meta-labeling
model training
entry / exit / holding policy
cohort normalization
cost model
portfolio backtest
defense overlay
label deployment authorization
```

15A 不得用 validation / robustness 选择任何阈值、anchor、morphology 或 label 变体。三个阈值档全部预注册冻结，不允许事后增减。

## 4. 继承边界

### 4.1 允许继承

15A 可以继承：

```text
anchor_record_unit = instrument x reference_date
label_record_unit = instrument x reference_date x threshold_id
primary_count_unit = anchor_row
reference_date = PIT executable row date
reference_pos = qfq daily position at reference_date
decision_time = reference_date close
anchor_pos = reference_pos
split boundary from 12A7g / 13A / 14A
universe definition from PIT topn 400/100 executable membership
cost is out of scope for 15A (label diagnostic only)
```

15A 必须读取以下 lineage artifacts：

```text
SOURCE_EP14_ROOT/outputs/publishable/tables/14A_full_native_sparse_state_change_event_utility_preflight/full_native_sparse_state_change_event_utility_decision.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_definition_audit.csv
SOURCE_EP13_ROOT/outputs/publishable/tables/13A_full_pit_native_token_cartography_preflight/native_universe_frozen_thresholds.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/label_formula_audit.csv
SOURCE_EP12_ROOT/outputs/publishable/tables/12A7g_vol_scaled_label_panel_c0_separability_triage/full_universe_split_boundary_audit.csv
```

15A 可以使用 14A / 13A local cache 作为加速输入与对照：

```text
SOURCE_EP14_ROOT/outputs/local_cache/14A_full_native_sparse_state_change_event_utility_preflight/native_rebuild_panel.parquet
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_universe_panel.parquet
SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_label_panel.parquet
```

若使用 local cache，runner 必须验证：

```text
row key uniqueness on (instrument, reference_date)
instrument x reference_date coverage
split boundary equality
universe membership equality
reference_pos / qfq position rebuild equality for audited rows
sha256 / schema hash when manifest provides it
```

Cache 缺失或校验失败时，runner 必须从 raw PIT universe 与 qfq bars 重建，不得 fail open。

### 4.2 fixed-horizon baseline lineage

15A 必须沿用 12A7g 选出的 fixed-horizon label identity 作为对照基线之一：

```text
baseline_label_id = vol20d_kup2p0_kdn1p0_H20
label_type = vol_scaled
vol_reference_id = volatility_20d
vol_reference_unit = daily_return_std
k_up = 2.0
k_dn = 1.0
horizon_sessions = 20
documented_path_window = reference_pos_through_reference_pos_plus_horizon_inclusive
row_level_lineage_fields = winner_positive / horizon_complete / max_high_return / upper_barrier
same_bar_priority = lower_first
lineage_usage = read_or_audit_equal_from_13A_14A_row_level_cache
```

并额外构造一组三档 threshold-matched fixed-horizon 对照：

```text
explicit_fixed_baseline_grid =
  fixed_120d_up50pct
  fixed_120d_up100pct
  fixed_120d_up150pct
fixed_horizon_sessions = 120
fixed_threshold_return matches threshold_id:
  up50pct -> 0.50
  up100pct -> 1.00
  up150pct -> 1.50
fixed_anchor = next executable open
fixed_window = entry_pos_through_entry_pos_plus_120_inclusive
fixed_winner = max high return over fixed_window >= fixed_threshold_return
```

这些 `fixed_120d_*` 是 15A 自己定义的诊断基线，用来直接演示 "走完涨幅超过 120 天反而没被算进 winner" 这一 fixed-horizon 截断现象。它们不是 12A7g lineage label，必须在 `baseline_label_definition_audit.csv` 中标记 `baseline_role = diagnostic_fixed_horizon_contrast`。`fixed_120d_up50pct` 是与 research question 最直接对位的 primary contrast；`up100pct` / `up150pct` 只作为 threshold sensitivity。

#### 4.2.1 `volscaled_H20` row-level lineage adapter freeze

`baseline_volscaled_H20` 的 row-level authoritative source 必须按以下优先级解析：

```text
1. SOURCE_EP14_ROOT/outputs/local_cache/14A_full_native_sparse_state_change_event_utility_preflight/native_rebuild_panel.parquet
   if present and adapter audit passes
2. SOURCE_EP13_ROOT/outputs/local_cache/13A_full_pit_native_token_cartography_preflight/native_universe_panel.parquet
   if present and adapter audit passes
3. raw qfq rebuild of the 13A implemented entry-anchor label
   only if cache is missing or invalid
```

`SOURCE_EP13_ROOT/.../native_label_panel.parquet` 只能作为 cross-check source，不能作为 primary source，因为它不包含 `entry_date`、`entry_pos`、`entry_price`、`reference_pos`、`label_id`、`horizon_close_return` 等字段。

Primary adapter mapping 冻结为：

```text
source row key = (instrument, reference_date, row_id)

native_universe_panel.split -> split_bucket
native_universe_panel.upper_barrier -> upper_barrier_return
native_universe_panel.lower_barrier -> lower_barrier_return
native_universe_panel.winner_positive -> volscaled_h20_winner
native_universe_panel.horizon_complete -> volscaled_h20_horizon_complete
native_universe_panel.upper_first -> volscaled_h20_upper_first
native_universe_panel.lower_first -> volscaled_h20_lower_first
native_universe_panel.same_bar_conflict -> volscaled_h20_same_bar_conflict
native_universe_panel.entry_date -> entry_date
native_universe_panel.entry_pos -> entry_pos
native_universe_panel.entry_price -> entry_price
native_universe_panel.reference_pos -> reference_pos
native_universe_panel.label_id -> volscaled_h20_label_id
native_universe_panel.horizon_sessions -> volscaled_h20_horizon_sessions
native_universe_panel.horizon_close_return -> volscaled_h20_terminal_return_20d
```

若 primary source 是 14A `native_rebuild_panel.parquet`，已派生字段 `split_bucket`、`upper_barrier_return`、`lower_barrier_return`、`winner`、`terminal_return_20d` 可以读取，但必须逐行审计其与原始 source fields 一致；不一致时 cache invalid and rebuild required。

Cross-check 规则：

```text
cross_check_source = SOURCE_EP13_ROOT/.../native_label_panel.parquet
cross_check_key = (instrument, reference_date, row_id)
cross_check_fields =
  split
  upper_barrier
  lower_barrier
  winner_positive
  upper_first
  lower_first
  same_bar_conflict
  horizon_complete
```

若 `native_label_panel` 在 overlapping selected-label fields 上与 primary source 不一致，或 cross-check key coverage 不完整，`upstream_lineage_gate_status = fail`，runner 必须尝试从 raw qfq bars 重建 13A implemented entry-anchor label。若重建失败或重建结果不能解释 cache mismatch，则 `decision_state = 15A_input_blocked`。

Path-window reconciliation 必须显式审计：

```text
selected_label_identity_source = 12A7g label_formula_audit
upstream_formula_path_window = value from 12A7g label_formula_audit.path_window
implemented_path_window = entry_pos_through_entry_pos_plus_horizon_inclusive
entry_anchor = next executable open
primary_label_path_window_source = 13A/14A implemented native label lineage
```

Allowed `path_window_reconciliation_status` values:

```text
pass_same_as_upstream_formula
pass_with_documented_13a_entry_anchor
fail_13a_entry_anchor_not_reproducible
fail_unexpected_path_window_conflict
```

15A primary `volscaled_H20` comparison 使用 13A/14A implemented entry-anchor lineage。不得把 12A7g 文本中的 `reference_pos_through_reference_pos_plus_horizon_inclusive` 与 13A implemented `entry_pos_through_entry_pos_plus_horizon_inclusive` 静默混为同一个 artifact；不得在 13A entry-anchor lineage 不可复现时退回 reference-pos window 后继续通过 gate。Reference-pos window 只能作为 diagnostic mismatch readout，不得进入 baseline winner count。

### 4.3 禁止继承 / 禁止主张

15A 明确不得继承或复活：

```text
13A selected dense token
13A volatility_20d__bottom_20pct dense state
13A2 directional filter shortlist
13A3 / 13C compression-repair composite state
13E nonlinear model scores
13F delayed-entry arms
13G overlay actions
14A sparse event families / cohort ranks
```

15A 不能主张：

```text
path-defined label is deployable.
slow winners are tradable.
a new winner-entry signal exists.
fixed-horizon label was wrong in a way that authorizes any entry thesis.
```

15A 只能主张：

```text
fixed-horizon winner label does / does not materially right-censor slow big winners,
and the censored slow-winner population does / does not present a morphology surface
distinct from previously falsified compression / drawdown-reversal morphology.
```

## 5. 必需输入

### 5.1 Universe 与行情

必需输入：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
```

PIT executable universe 必须至少提供：

```text
instrument
usable_trade_date
board_bucket
is_listed
is_st
is_suspended
```

qfq daily bar 必须至少提供：

```text
date
open
high
low
close
```

这些文件是本地大数据 artifact，可能不在 VCS 内，其存在不能由 git 或 file-search 索引推断。runner 必须对每个必需输入做直接 filesystem 读取、sha256、row count、schema audit。必需本地数据缺失必须映射到：

```text
decision_state = 15A_input_blocked
gate_failure = required_local_data_artifact_missing
```

### 5.2 Row identity 与 split

逐行身份：

```text
anchor_record_unit = instrument x reference_date
label_record_unit = instrument x reference_date x threshold_id
source_row_key = instrument x reference_date x row_id
reference_date = PIT executable row date
reference_pos = qfq daily position at reference_date
anchor_pos = reference_pos
entry_date = immediate next executable open after reference_date
entry_pos = qfq daily position at entry_date
entry_price = qfq open at entry_pos
decision_time = reference_date close
split_bucket in {train, validation, robustness}
```

同一 `(instrument, reference_date)` 只能保留一行。若继承 13A/14A cache，`row_id` 必须保留为 lineage key，不得在 join / cache / report 生成过程中丢弃。重复 row 必须进入 audit 并 fail closed，除非可由完全相同内容去重且 sha256 lineage 可证明。

所有 publishable winner / slow-winner / censoring rate 的 primary denominator 都是 anchor-row denominator。若报告 unique episode 相关数字，只能来自 `episode_overlap_density_audit.csv`，且必须标记为 overlap diagnostic，不得替代 primary decision denominator。

Split boundary 必须从 12A7g / 13A / 14A 可审计 artifact 读取。不得从 label 结果、episode 结果或报告文本反推 split。若 split boundary 不可证明，状态为：

```text
15A_input_blocked
gate_failure = split_boundary_unavailable
```

## 6. Path-Defined Winner Episode Label Freeze

### 6.1 Anchor 与 entry

```text
anchor_pos = reference_pos
entry_pos = immediate next executable open after reference_date
entry_price = qfq open at entry_pos
```

所有 path-defined label 的累计涨幅都相对 `entry_price` 计算，使用 next-open entry，与全 topic 的 entry 约定一致。决策点 t0 = reference_date close；label 本身使用未来 path（这是 label 的本质，允许），但任何 t0-close morphology readout 只能使用 `reference_pos` 及之前的数据。

### 6.2 First-passage threshold label（无 horizon 上限）

冻结三档阈值：

```text
threshold_grid = {0.50, 1.00, 1.50}
threshold_id in {up50pct, up100pct, up150pct}
```

对每个 `(instrument, reference_date, threshold)`，定义：

```text
cumulative_high_return[s] = high[entry_pos + s] / entry_price - 1, for s = 0, 1, 2, ...
first_passage_offset =
  smallest s >= 0 such that cumulative_high_return[s] >= threshold
available_forward_sessions =
  number of qfq rows available from entry_pos to the last bar of this instrument
last_observed_pos =
  last qfq row position for this instrument
```

Label 取值（每个 threshold 一套）：

```text
if first_passage_offset exists within available_forward_sessions:
  path_winner = true
  is_censored = false
  confirmed_non_winner = false
  time_to_threshold_sessions = first_passage_offset
elif available_forward_sessions reaches the instrument's last available bar
     without crossing threshold:
  path_winner = false
  is_censored = true
  confirmed_non_winner = false
  censoring_type = right_censored_at_data_end
  time_to_threshold_sessions = null
```

在 no-horizon path-defined label 下，未触达阈值的 row 不能被确认为 negative；它只能被标记为 `is_censored = true`。因此 primary no-horizon label 必须满足：

```text
confirmed_non_winner_n = 0 for every threshold_id x split_bucket
path_winner_n + censored_n = record_n
```

为支持形态 readout，可以冻结一个只读 control：

```text
non_hit_control_min_sessions = 250
observed_non_hit_control_flag =
  path_winner = false
  and is_censored = true
  and available_forward_sessions >= non_hit_control_min_sessions
observed_non_hit_control_role = readout_only_censored_control_not_negative
```

`observed_non_hit_control_flag` 不能改变 label、base-rate、decision state 或 15B 授权；它只允许在 morphology table 中给 slow / fast winner 增加一个长观察未触达阈值的参照组。

Censoring 隔离规则（核心纪律，不得违反）：

```text
is_censored = true 的 row 不得被计入 confirmed negative / confirmed non-winner 类。
它可以计入 record_n 与 censored_n / censored_rate。
它只有在 observed_non_hit_control_flag = true 时才可进入 morphology control readout，
且该 control 必须标记为 readout_only_censored_control_not_negative。
任何把 censored row 当作 confirmed non-winner 的实现，censoring isolation gate fail closed。
```

`first_passage` 使用 `high`（盘中最高价触及阈值即算达标），与 topic 既有 triple-barrier upper-touch 约定一致。必须额外输出一个 `close_based` 变体作为 readout-only 对照：

```text
close_based_first_passage_offset =
  smallest s such that close[entry_pos + s] / entry_price - 1 >= threshold
close_based_role = readout_only_not_for_primary_decision
```

Primary decision 使用 high-based first passage；close-based 仅用于计算 `high_based_close_based_agreement_rate`，不得单独报告 close-based time-to-threshold distribution、winner-set distribution 或 decision readout。

### 6.3 Episode end 边界定义（用于 morphology 与 duration readout）

为支持 duration 与 slow-winner 形态分析，对 `path_winner = true` 的 row 记录 episode 起止：

```text
episode_start_pos = entry_pos
episode_threshold_pos = entry_pos + first_passage_offset
episode_peak_pos = argmax of high over [entry_pos, episode_threshold_pos]
episode_peak_return = max high return over [entry_pos, episode_threshold_pos]
```

`episode_peak_*` 仅用于描述 slow-winner 的涨幅规模分布，不进入 primary decision gate。

### 6.4 Fixed-horizon baseline labels（对照）

```text
baseline_volscaled_H20 = 12A7g vol20d_kup2p0_kdn1p0_H20 (continue to inherit, audited via §4.2)
baseline_fixed_120d_threshold_matched:
  window = entry_pos through entry_pos + 120 inclusive
  fixed_threshold_return = threshold_return for threshold_id
  fixed_winner = (max high return over window) >= fixed_threshold_return
  horizon-incomplete rows (fewer than 121 forward bars) excluded from this baseline,
    counted separately as fixed_baseline_horizon_incomplete_n
```

`baseline_volscaled_H20` 的 authoritative value 应优先从 13A/14A row-level cache 的 `winner_positive` / `horizon_complete` / `label_id` 读取并审计 lineage 一致性；如果 runner 选择重建，它必须在 `baseline_label_definition_audit.csv` 中同时记录 12A7g documented path window 与 13A/14A implemented row-level fields，不能把 next-open rebuilt baseline 与 12A7g documented `reference_pos` window 混为同一个 artifact。

## 7. Censoring 与差异度量

### 7.1 Winner set 差异

对每个 `(threshold_id, split_bucket)`，以 threshold-matched `baseline_fixed_120d_*` 与 `baseline_volscaled_H20` 为对照，输出：

```text
record_n
path_winner_n
path_winner_rate_all_records
censored_n
censored_rate
confirmed_non_winner_n
observed_non_hit_control_n
fixed120_horizon_complete_n
fixed120_horizon_incomplete_n
fixed120_winner_n
fixed120_winner_rate
volscaled_h20_winner_n
volscaled_h20_winner_rate
slow_winner_n
slow_winner_rate_all_records
slow_winner_share_of_path_winners
fast_winner_n
overlap_path_and_fixed120_n
path_only_winner_n
fixed120_only_winner_n
```

定义：

```text
slow_winner =
  path_winner = true and time_to_threshold_sessions > 120
fast_winner =
  path_winner = true and time_to_threshold_sessions <= 120
path_only_winner =
  path_winner = true and fixed120_winner = false
fixed120_only_winner =
  fixed120_winner = true and path_winner = false
path_winner_rate_all_records =
  path_winner_n / record_n
slow_winner_rate_all_records =
  slow_winner_n / record_n
slow_winner_share_of_path_winners =
  slow_winner_n / path_winner_n when path_winner_n > 0 else null
```

`confirmed_non_winner_n` 对 primary no-horizon label 必须为 0；该字段保留是为了审计 censored row 未被污染进 negative 类。`observed_non_hit_control_n` 是 readout-only control，不是 negative 类。

`fixed120_winner_rate` 的分母必须是 `fixed120_horizon_complete_n`，不是 `record_n`。`volscaled_h20_winner_rate` 的分母必须是对应 lineage 的 horizon-complete denominator。

`fixed120_only_winner` 预期应为 0（threshold-matched path-defined high-based 无上限理论上是 fixed120 的超集，前提是同一 entry、同一 high 序列、同一 bar alignment）。若 `fixed120_only_winner_n > 0`，必须在 `path_defined_label_rebuild_audit.csv` 中记录 `fixed120_only_winner_explained_n` 与 `fixed120_only_winner_explanation_code_list`，并在 row-level cache 保留可追溯 explanation code；无法解释则 label rebuild gate fail closed。

允许的 row-level explanation code 仅限：

```text
none
bar_alignment_mismatch
fixed120_horizon_complete_but_path_truncated
entry_window_boundary_mismatch
```

`none` 只能用于 `fixed120_only_winner = false` 的 row。任何不在上述集合内的 code、空 code、或 `fixed120_only_winner = true` 但 code 为 `none`，均视为 unexplained，`label_rebuild_gate_status = fail`。

### 7.2 Time-to-threshold 分布

对 `path_winner = true` 的 row，按 threshold_id x split_bucket 输出：

```text
time_to_threshold_p10
time_to_threshold_p25
time_to_threshold_median
time_to_threshold_p75
time_to_threshold_p90
time_to_threshold_max
share_within_20d
share_within_60d
share_within_120d
share_beyond_120d
share_beyond_250d
```

`share_beyond_120d = slow_winner_n / path_winner_n`，是本诊断的关键数字：它直接量化 path-defined winners 中会被 120d fixed horizon 漏掉的比例。`slow_winner_rate_all_records = slow_winner_n / record_n` 量化它在全 anchor-row universe 中的密度。两者必须同时进入 decision table，不能互相替代。

### 7.3 Censoring 审计

对每个 threshold_id x split_bucket：

```text
censored_n
censored_rate
censored_median_available_forward_sessions
counted_in_confirmed_non_winner_n
counted_in_control_without_flag_n
censored_isolation_status
```

`censored_isolation_status = pass` 仅当：

```text
confirmed_non_winner_n = 0
counted_in_confirmed_non_winner_n = 0
counted_in_control_without_flag_n = 0
censored rows are excluded from slow / fast winner morphology cohorts
censored rows enter morphology control only when observed_non_hit_control_flag = true
```

任何违反则 `censored_isolation_status = fail` 且 `decision_state = 15A_input_blocked`。

## 8. Slow-Winner Morphology Readout

15A 必须检验 slow-winner（被 fixed120 漏掉的那批）的 t0-close 可观测形态是否区别于 13/14 已失败形态。

仅使用 `reference_pos` 及之前可观测的特征。最小特征集（从 13A native_universe_panel 复用或用 raw qfq 重建）：

```text
volatility_20d
volatility_60d
max_drawdown_20d
max_drawdown_60d
ret_20d
ret_60d
distance_to_20d_high
distance_to_60d_high
distance_to_20d_low
trend_ma_20_60_spread
vol_compression_20d_60d
rebound_from_20d_low
```

对每个 threshold_id，按以下三组对比 readout（每特征输出 median 与 p25/p75）：

```text
cohort A = slow_winner (time_to_threshold > 120)
cohort B = fast_winner (time_to_threshold <= 120)
cohort C = observed_non_hit_control
           (path_winner false, is_censored true,
            observed_non_hit_control_flag true,
            readout_only_censored_control_not_negative)
```

Cohort observation-window mismatch 是已知且接受的诊断限制：

```text
cohort A slow_winner minimum observable path length is at least the >120-session threshold-crossing window.
cohort C observed_non_hit_control requires available_forward_sessions >= 250.
distinct_surface_present must not be interpreted as proving that duration exposure cannot explain part of the morphology difference.
```

15A 只做 label/censoring diagnostic，不做因果推断或 deployable morphology claim。

并对 13/14 已失败形态做显式 overlap readout：

```text
compression_state_share =
  share of cohort with vol_compression_20d_60d <= train 20th percentile
drawdown_reversal_state_share =
  share of cohort with max_drawdown_20d <= train 20th percentile
threshold_source_split = train
threshold_freeze_scope = all train anchor rows with finite feature value
```

Morphology 结论字段：

```text
slow_winner_morphology_distinct_status
```

取值：

```text
distinct_surface_present
  if selected threshold 的 slow_winner cohort 的 compression_state_share 与
  drawdown_reversal_state_share 都明显低于 fast_winner cohort
  （预注册：fast_winner_share - slow_winner_share >= 0.10），
  说明 slow winner 不是 compression / reversal 的换名。

overlaps_known_failed_morphology
  if slow_winner cohort 在 compression 或 drawdown-reversal 上与 fast_winner 相当或更高。

inconclusive_insufficient_n
  if selected threshold 的 train slow_winner_n < 200.
```

此 readout 不授权任何信号搜索，只用于判断 15B 是否值得开。

若没有任何 threshold 满足 material censoring，`slow_winner_morphology_distinct_status` 必须为 `not_evaluated_no_material_censoring`，decision precedence 不得因为 morphology 未评估而覆盖 no-material-censoring stop state。

## 9. Gate 定义

15A 必须输出以下 gate：

```text
input_gate_status
upstream_lineage_gate_status
universe_membership_gate_status
price_path_completeness_gate_status
label_rebuild_gate_status
censoring_isolation_gate_status
winner_set_difference_gate_status
search_accounting_gate_status
```

### 9.1 label_rebuild_gate

Pass 仅当：

```text
all three thresholds rebuilt deterministically from raw qfq bars
fixed120_only_winner_n explained or zero for all threshold/split
high-based and close-based first passage both computed
volscaled_H20 baseline read from 13A/14A row-level lineage or rebuilt and audited equal
confirmed_non_winner_n = 0 for no-horizon path-defined label
```

### 9.2 censoring_isolation_gate

Pass 仅当所有 threshold x split 的 `censored_isolation_status = pass`。

### 9.3 winner_set_difference_gate

这是一个 readout gate，不判 go/no-go，但必须 pass schema：所有 §7.1 / §7.2 / §7.3 字段非空且 denominator 自洽：

```text
path_winner_n + censored_n == record_n
confirmed_non_winner_n == 0
slow_winner_n + fast_winner_n == path_winner_n
fixed120_winner_rate denominator = fixed120_horizon_complete_n
volscaled_h20_winner_rate denominator = volscaled_h20_horizon_complete_n
slow_winner_share_of_path_winners denominator = path_winner_n
```

### 9.4 search_accounting_gate

Pass 仅当：

```text
threshold_grid 恰为 {0.50, 1.00, 1.50}，无增减
no validation / robustness used to select threshold, anchor, morphology band
selected_threshold_recommendation selected only from split_bucket = train using fixed priority order
all close-based / episode_peak / observed_non_hit_control / episode_overlap readouts marked readout_only
close_based_first_passage used only for high_based_close_based_agreement_rate
episode_overlap_role = readout_only_anchor_overlap_density_not_primary_denominator
```

## 10. Decision State Mapping

15A decision table 必须包含：

```text
decision_state
next_allowed_requirement
label_deployment_authorized
signal_search_authorized
selection_split_bucket
selected_threshold_recommendation
selected_threshold_reason
primary_failure_reason
gate_failure
input_gate_status
upstream_lineage_gate_status
universe_membership_gate_status
price_path_completeness_gate_status
label_rebuild_gate_status
censoring_isolation_gate_status
winner_set_difference_gate_status
search_accounting_gate_status
slow_winner_morphology_distinct_status
material_censoring_threshold_count
selected_threshold_share_beyond_120d
selected_threshold_slow_winner_rate_all_records
selected_threshold_censored_rate
share_beyond_120d_up50pct
share_beyond_120d_up100pct
share_beyond_120d_up150pct
slow_winner_rate_all_records_up50pct
slow_winner_rate_all_records_up100pct
slow_winner_rate_all_records_up150pct
censored_rate_up50pct
censored_rate_up100pct
censored_rate_up150pct
```

确定性 decision precedence：

```text
1. 任何 required input / lineage / split / universe / price-path / censoring-isolation 失败：
   decision_state = 15A_input_blocked
   next_allowed_requirement = none

2. label_rebuild_gate 失败（无法确定性重建，或 fixed120_only_winner 无法解释）：
   decision_state = 15A_label_rebuild_failed
   gate_failure = label_rebuild_gate_failed
   next_allowed_requirement = none

3. fixed-horizon label 没有实质 censoring
   （material_censoring = false，即 train split 没有任何 threshold 同时满足
    share_beyond_120d >= 0.10、slow_winner_rate_all_records >= 0.02、
    slow_winner_n >= 200）：
   decision_state = 15A_no_material_censoring_fixed_horizon_label_adequate
   next_allowed_requirement = none

4. 存在实质 censoring，但 selected threshold 的
   slow_winner_morphology_distinct_status = inconclusive_insufficient_n：
   decision_state = 15A_diagnostic_inconclusive_insufficient_slow_winner
   next_allowed_requirement = none

5. 存在实质 censoring，但 selected threshold 的 slow winner 仍重新落入已失败形态：
   decision_state = 15A_material_censoring_but_slow_winner_overlaps_known_failed_morphology
   gate_failure = none
   next_allowed_requirement = none

6. 存在实质 censoring，且 selected threshold 的 slow winner 呈现区别于已失败形态的新表面：
   decision_state = 15A_material_censoring_with_distinct_slow_winner_surface
   next_allowed_requirement = requirement_15b_path_defined_winner_separability_diagnostic.md
```

实质 censoring 定义（预注册）：

```text
readout_threshold_material_censoring_flag[threshold_id, split_bucket] =
  share_beyond_120d >= 0.10
  and slow_winner_rate_all_records >= 0.02
  and slow_winner_n >= 200

decision_threshold_material_censoring_flag[threshold_id] =
  readout_threshold_material_censoring_flag[threshold_id, split_bucket = train]

material_censoring =
  any threshold with decision_threshold_material_censoring_flag = true

selected_threshold_recommendation =
  first threshold in fixed priority order {up50pct, up100pct, up150pct}
  with decision_threshold_material_censoring_flag = true,
  else none

selection_split_bucket =
  train when selected_threshold_recommendation != none,
  else none

selected_threshold_reason =
  lowest_pre_registered_material_censoring_threshold
  or none_no_material_censoring
```

Selection discipline:

```text
Only split_bucket = train may select `selected_threshold_recommendation`.
split_bucket in {validation, robustness, all} is readout-only for materiality display.
validation / robustness / all must not change selected threshold, morphology band, or decision precedence.
```

Material censoring gate deliberately combines three different denominator types:

```text
share_beyond_120d:
  severity among path_winner rows; asks how much of the winner set fixed120 would miss.
slow_winner_rate_all_records:
  anchor-row population density; asks whether the missed population is large enough in the full universe.
slow_winner_n:
  absolute train support; asks whether morphology readout has enough rows to be meaningful.
```

这三个条件不是可加权打分，也不能互相替代；必须在 train split 同时满足才允许 selection。Validation / robustness / all split 只能报告同一三条件 readout，不能改变 material censoring decision。

所有非 step-6 状态必须设：

```text
label_deployment_authorized = false
signal_search_authorized = false
```

step-6 状态可以设：

```text
signal_search_authorized = true   (仅授权 15B 在新 label 上做 separability 诊断)
label_deployment_authorized = false
```

15A 即使到 step-6，也只授权写 15B separability 诊断，不授权任何 entry、模型、仓位或 label 部署。

## 11. 必需输出

### 11.1 Publishable tables

```text
outputs/publishable/tables/15A_winner_episode_label_censoring_diagnostic/
```

必须包含：

```text
input_artifact_audit.csv
upstream_lineage_audit.csv
universe_membership_audit.csv
price_path_completeness_audit.csv
baseline_label_definition_audit.csv
path_defined_label_rebuild_audit.csv
winner_set_difference_readout.csv
time_to_threshold_distribution_readout.csv
censoring_isolation_audit.csv
slow_winner_morphology_readout.csv
known_failed_morphology_overlap_readout.csv
episode_overlap_density_audit.csv
search_accounting_audit.csv
winner_episode_label_censoring_decision.csv
```

### 11.2 Local cache

```text
outputs/local_cache/15A_winner_episode_label_censoring_diagnostic/
```

允许的 cache 文件：

```text
universe_rebuild_panel.parquet
path_defined_label_panel.parquet
slow_winner_morphology_panel.parquet
```

Cache 仅为加速器，不得替代 publishable audit。

### 11.3 Manifest 与 report

```text
outputs/manifests/15A_winner_episode_label_censoring_diagnostic_manifest.json
outputs/publishable/reports/winner_episode_label_censoring_diagnostic_report.md
```

Report（中文）必须包含：

1. 单行裁决与 `decision_state`。
2. 15A 为什么存在：fixed-horizon label 的 right-censoring 怀疑。
3. Input / lineage / split / universe / price-path / censoring-isolation audit summary。
4. 三档阈值的 winner set 差异、slow-winner share、path_only vs fixed120_only 计数。
5. Time-to-threshold 分布，尤其 `share_beyond_120d`（fixed-120d 漏标比例）。
6. Censoring rate 与隔离正确性。
7. Slow-winner morphology readout，及其与 13/14 compression / drawdown-reversal 的 overlap。
8. Anchor-row overlap density，明确 winner / slow-winner count 不是 unique market episode count。
9. 是否授权 15B，以及原因。
10. 明确声明：15A 不授权 entry、模型、仓位、label 部署；所有 readout 不得被解释为可交易 alpha。

## 12. Output Schema Requirements

### 12.1 `input_artifact_audit.csv`

Required columns:

```text
artifact_role
artifact_path
resolved_path
required_flag
lineage_role
read_status
row_count
column_count
sha256
schema_status
required_column_missing_list
```

### 12.2 `upstream_lineage_audit.csv`

Required columns:

```text
upstream_artifact_role
upstream_path
upstream_sha256
upstream_row_count
upstream_schema_status
lineage_claim
lineage_status
selected_label_id
primary_row_level_source
primary_row_level_source_role
cross_check_source
cross_check_key
cross_check_key_coverage_rate
cross_check_mismatch_n
upstream_formula_path_window
implemented_path_window
path_window_reconciliation_status
path_window_reconciliation_reason
blocking_reason
```

### 12.3 `universe_membership_audit.csv`

Required columns:

```text
split_bucket
calendar_year
source_row_n
unique_anchor_row_n
duplicate_anchor_row_n
membership_row_n
membership_match_rate
split_boundary_source
split_boundary_status
universe_membership_status
blocking_reason
```

### 12.4 `price_path_completeness_audit.csv`

Required columns:

```text
instrument
anchor_row_n
qfq_row_n
missing_qfq_file_flag
missing_reference_pos_n
missing_entry_pos_n
missing_entry_price_n
min_available_forward_sessions
median_available_forward_sessions
max_available_forward_sessions
price_path_status
blocking_reason
```

### 12.5 `baseline_label_definition_audit.csv`

Required columns:

```text
baseline_id
baseline_role
threshold_id
threshold_return
anchor_definition
window_definition
horizon_sessions
source_artifact
source_label_id
source_path_window
primary_row_level_source
primary_row_level_source_role
row_level_key
cross_check_source
cross_check_status
path_window_reconciliation_status
path_window_reconciliation_reason
winner_definition
horizon_complete_denominator_rule
baseline_definition_status
```

`baseline_role` allowed values:

```text
lineage_volscaled_h20
diagnostic_fixed_horizon_contrast
```

### 12.6 `path_defined_label_rebuild_audit.csv`

Required columns:

```text
threshold_id
split_bucket
record_n
path_winner_n
censored_n
confirmed_non_winner_n
observed_non_hit_control_n
fixed120_horizon_complete_n
fixed120_horizon_incomplete_n
fixed120_only_winner_n
fixed120_only_winner_explained_n
fixed120_only_winner_explanation_code_list
high_based_close_based_agreement_rate
row_level_explanation_available
rebuild_status
```

`confirmed_non_winner_n` must be 0 for every row. `row_level_explanation_available` must be true whenever `fixed120_only_winner_n > 0`. `fixed120_only_winner_explanation_code_list` must contain only the pre-registered codes in §7.1; unknown or missing codes fail closed.

### 12.7 `winner_set_difference_readout.csv`

Required columns:

```text
threshold_id
split_bucket
record_n
path_winner_n
path_winner_rate_all_records
censored_n
censored_rate
confirmed_non_winner_n
observed_non_hit_control_n
fixed120_horizon_complete_n
fixed120_horizon_incomplete_n
fixed120_winner_n
fixed120_winner_rate
volscaled_h20_horizon_complete_n
volscaled_h20_winner_n
volscaled_h20_winner_rate
slow_winner_n
slow_winner_rate_all_records
slow_winner_share_of_path_winners
fast_winner_n
overlap_path_and_fixed120_n
path_only_winner_n
fixed120_only_winner_n
threshold_material_censoring_flag
winner_set_difference_status
```

### 12.8 `time_to_threshold_distribution_readout.csv`

Required columns:

```text
threshold_id
split_bucket
path_winner_n
time_to_threshold_p10
time_to_threshold_p25
time_to_threshold_median
time_to_threshold_p75
time_to_threshold_p90
time_to_threshold_max
share_within_20d
share_within_60d
share_within_120d
share_beyond_120d
share_beyond_250d
distribution_status
```

### 12.9 `censoring_isolation_audit.csv`

Required columns:

```text
threshold_id
split_bucket
record_n
censored_n
censored_rate
censored_median_available_forward_sessions
confirmed_non_winner_n
counted_in_confirmed_non_winner_n
counted_in_control_without_flag_n
observed_non_hit_control_n
censored_isolation_status
```

`counted_in_confirmed_non_winner_n` and `counted_in_control_without_flag_n` must be 0; non-zero values fail closed.

### 12.10 `slow_winner_morphology_readout.csv`

Required columns:

```text
threshold_id
split_bucket
cohort_id
cohort_role
feature_id
feature_observation_boundary
feature_n
feature_missing_n
feature_p25
feature_median
feature_p75
feature_readout_status
```

Allowed `cohort_id` values:

```text
slow_winner
fast_winner
observed_non_hit_control
```

`cohort_role` for `observed_non_hit_control` must be `readout_only_censored_control_not_negative`.

### 12.11 `known_failed_morphology_overlap_readout.csv`

Required columns:

```text
threshold_id
split_bucket
cohort_id
state_id
state_threshold_feature
state_threshold_value
threshold_source_split
state_share
fast_minus_slow_share_delta
slow_winner_morphology_distinct_status
overlap_readout_status
```

Allowed `cohort_id` values:

```text
slow_winner
fast_winner
observed_non_hit_control
```

Allowed `state_id` values:

```text
compression_state
drawdown_reversal_state
```

### 12.12 `episode_overlap_density_audit.csv`

Required columns:

```text
threshold_id
split_bucket
path_winner_anchor_row_n
slow_winner_anchor_row_n
approx_episode_cluster_n
median_anchor_rows_per_episode_cluster
p90_anchor_rows_per_episode_cluster
max_anchor_rows_per_episode_cluster
cluster_definition
readout_role
overlap_density_status
```

`cluster_definition` must be deterministic. Minimum acceptable definition:

```text
cluster_input_rows =
  rows with path_winner = true and finite entry_pos and finite episode_threshold_pos

censored rows do not enter cluster_input_rows.
confirmed_non_winner rows do not exist for primary no-horizon label.

interval =
  [entry_pos, episode_threshold_pos] inclusive

cluster_scope =
  split_bucket x instrument x threshold_id

cluster_rule =
  union-find transitive interval merge within cluster_scope:
  anchors whose intervals overlap directly or through an overlap chain belong to the same cluster.

transitive example =
  if A overlaps B and B overlaps C, A/B/C are one cluster even when A does not overlap C.

approx_episode_cluster_n =
  count of merged clusters over cluster_input_rows in the threshold_id x split_bucket group.
```

This table is diagnostic only and must not replace anchor-row denominators in decision fields.

### 12.13 `search_accounting_audit.csv`

Required columns:

```text
threshold_grid
threshold_grid_status
threshold_priority_order
selected_threshold_recommendation
selected_threshold_source_split
selection_split_bucket
threshold_selection_scope
validation_used_for_selection
robustness_used_for_selection
close_based_role
episode_peak_role
observed_non_hit_control_role
episode_overlap_role
search_accounting_status
```

`selected_threshold_source_split` must be `train_only` when a threshold is selected, else `none`. `selection_split_bucket` must be `train` when a threshold is selected, else `none`. `threshold_selection_scope` must state `train_split_only_fixed_priority_order`; validation / robustness / all rows are readout-only.

`episode_overlap_role` must be `readout_only_anchor_overlap_density_not_primary_denominator`.

### 12.14 `winner_episode_label_censoring_decision.csv`

Required columns:

```text
decision_state
next_allowed_requirement
label_deployment_authorized
signal_search_authorized
selection_split_bucket
selected_threshold_recommendation
selected_threshold_reason
selected_threshold_share_beyond_120d
selected_threshold_slow_winner_rate_all_records
selected_threshold_censored_rate
primary_failure_reason
gate_failure
input_gate_status
upstream_lineage_gate_status
universe_membership_gate_status
price_path_completeness_gate_status
label_rebuild_gate_status
censoring_isolation_gate_status
winner_set_difference_gate_status
search_accounting_gate_status
slow_winner_morphology_distinct_status
material_censoring_threshold_count
share_beyond_120d_up50pct
share_beyond_120d_up100pct
share_beyond_120d_up150pct
slow_winner_rate_all_records_up50pct
slow_winner_rate_all_records_up100pct
slow_winner_rate_all_records_up150pct
censored_rate_up50pct
censored_rate_up100pct
censored_rate_up150pct
```

## 13. Implementation Notes

```text
1. Load and audit required inputs (PIT universe, qfq bars, lineage artifacts).
2. Rebuild or validate universe membership and split boundary.
3. Build reference_pos / entry_pos / entry_price per (instrument, reference_date).
4. For each instrument, compute forward high path from entry_pos to last available bar.
5. Compute first-passage offset for thresholds {0.50, 1.00, 1.50}, high-based and close-based.
6. Assign path_winner / is_censored / confirmed_non_winner=false with strict censoring isolation.
7. Assign observed_non_hit_control_flag for readout-only morphology control.
8. Compute threshold-matched fixed120 and lineage volscaled_H20 baselines; volscaled_H20 must use the frozen 13A/14A entry-anchor adapter, native_label_panel cross-check, and path-window reconciliation audit.
9. Compute winner-set difference, time-to-threshold distribution, censoring audit.
10. Compute t0-close slow-winner morphology readout and known-failed-morphology overlap.
11. Compute anchor-row episode overlap density audit.
12. Emit deterministic decision table, report, cache, manifest.
```

Implementation 必须保持以下列在 row-level cache 与 publishable 输出间稳定：

```text
instrument
reference_date
row_id
split_bucket
entry_date
entry_pos
entry_price
threshold_id
threshold_return
first_passage_offset
close_based_first_passage_offset
time_to_threshold_sessions
path_winner
is_censored
censoring_type
confirmed_non_winner
observed_non_hit_control_flag
observed_non_hit_control_role
fixed120_winner
fixed120_baseline_id
fixed120_horizon_complete
fixed120_only_winner_explanation_code
volscaled_h20_winner
volscaled_h20_horizon_complete
volscaled_h20_label_id
volscaled_h20_source_artifact
slow_winner_flag
fast_winner_flag
available_forward_sessions
episode_threshold_pos
episode_peak_pos
episode_peak_return
```

Implementation 必须优先确定性重建与显式 join，不得从 markdown 报告解析数据，不得用 validation / robustness 选择阈值或形态带，不得把 censored row 当作 negative。

## 14. Test Expectations

最小测试：

```text
test_input_artifact_audit_fail_closed
test_required_local_data_missing_maps_to_input_blocked
test_split_boundary_unavailable_fails_closed
test_first_passage_high_based_offset_correct
test_first_passage_no_horizon_cap
test_censored_row_when_threshold_never_reached_to_last_bar
test_censored_row_not_counted_as_non_winner
test_no_horizon_confirmed_non_winner_always_zero
test_path_winner_plus_censored_sums_to_record_n
test_observed_non_hit_control_is_readout_only_not_negative
test_threshold_matched_fixed120_baselines_for_50_100_150
test_volscaled_h20_baseline_uses_13a_14a_entry_anchor_adapter
test_volscaled_h20_winner_rate_denominator_is_horizon_complete_n
test_native_label_panel_is_cross_check_only_not_primary_source
test_path_window_reconciliation_status_required_for_h20_baseline
test_row_id_preserved_for_upstream_lineage_join
test_fixed120_only_winner_must_be_explained_or_zero
test_fixed120_only_winner_explanation_code_allowlist
test_slow_winner_defined_as_time_to_threshold_gt_120
test_time_to_threshold_share_beyond_120d_computed
test_close_based_first_passage_only_feeds_agreement_rate
test_material_censoring_gate_combines_severity_density_and_support
test_threshold_grid_frozen_50_100_150
test_validation_not_used_to_select_threshold_or_morphology
test_slow_winner_morphology_uses_only_t0_observable_features
test_morphology_observation_window_mismatch_is_reported_as_limitation
test_known_failed_morphology_overlap_allowed_cohorts_include_control
test_selected_threshold_uses_train_split_only
test_validation_robustness_all_are_readout_only_for_threshold_selection
test_selected_threshold_uses_train_only_fixed_priority_order
test_decision_table_contains_selected_threshold_metrics_and_all_threshold_readouts
test_episode_overlap_density_does_not_replace_anchor_denominator
test_episode_overlap_role_value_is_readout_only_anchor_overlap_density
test_episode_overlap_density_uses_union_find_transitive_interval_merge
test_episode_overlap_density_excludes_censored_rows
test_material_censoring_with_distinct_surface_maps_to_15b
test_no_material_censoring_maps_to_stop_state
test_inconclusive_insufficient_slow_winner_maps_to_stop
test_decision_precedence_input_blocked_before_diagnostic_states
test_manifest_contains_report_and_all_publishable_tables
```

Synthetic fixtures 可用更小 universe 与更短 path，但必须保留：

```text
no-horizon-cap first passage
censoring isolation
slow / fast winner split at 120 sessions
threshold grid {0.50, 1.00, 1.50}
t0-observable-only morphology
row_id-based upstream lineage join
13A/14A entry-anchor H20 baseline adapter and native_label_panel cross-check mismatch
train-only threshold selection with validation/robustness/all readout-only rows
fixed120_only explanation-code allowlist
transitive interval-overlap cluster and censored-row exclusion
volscaled_h20 horizon-complete denominator check
close-based first-passage agreement-rate-only behavior
known-failed morphology overlap control cohort coverage
decision precedence
```

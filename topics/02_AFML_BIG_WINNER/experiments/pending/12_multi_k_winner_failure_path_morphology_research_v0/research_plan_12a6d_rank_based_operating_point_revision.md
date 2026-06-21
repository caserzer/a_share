# 12A7 Trailing-rank Operating Point Validation Research Plan

## 0. 阶段定位

本计划从 `12A7` 开始，不再占用 `12A6d` 编号。`12A6c` 已经完成 two-stage feasibility 与 threshold-transport 失败诊断；下一阶段应作为 12A7 的 trailing-rank operating-point validation，而不是再追加 12A6d requirement。本文只修正研究路线，不生成新的 requirement。

本计划承接 12A6c `two_stage_fast_fail_rejector_continuation_report.md`，但吸收 reviewer 对第一版 rank-operating-point plan 的方法论批评。第一版把 “cross-sectional rank percentile” 当成 rank transport 的 primary operating point，并写了 `rank50 actual budget within tolerance by construction`。这个定义有隐患：

```text
如果在整个月、整个 split 或 OOS cohort 上排名来保证 50% budget，
就会使用决策时尚不可见的未来候选事件；
这等价于 OOS operating-point 重选或 look-ahead cohort rank。
```

因此 12A7 必须改为：

```text
headline operating point = PIT trailing-rank / trailing-percentile rule
whole-month or whole-split rank = diagnostic upper bar only, not deployable primary rule
OOS actual budget drift = required readout, not assumed pass by construction
```

一句话：12A7 仍然验证 rank transport，但验证对象不是“未来可知 cohort 的横截面分位”，而是 event-driven single-name deployment 下可用的 trailing empirical score distribution。

## 1. 12A6c 诊断复盘

### 1.1 当前失败状态

```text
12A6c decision = 12A6c_stage1_partial
input gate = pass
stage_1_threshold_health = fail
stage_2_threshold_health = fail
next_allowed_requirement = requirement_12a6d_stage1_rejector_feature_or_label_revision.md
```

`12A6c` 当时给出的 `12A6d` next_allowed_requirement 代表“不要进入 12A7 OOS validation”；经过 reviewer 复盘后，本研究路线把新阶段重新定位为 12A7 trailing-rank operating-point validation，而不是继续追加 12A6d requirement。

Primary logistic regression 的 train-frozen absolute threshold 外推结果：

| stage | split | target budget | actual budget | interpretation |
|---|---:|---:|---:|---|
| stage-1 keep low fast-fail risk | train | 50.0% | 50.0% | train budget exact |
| stage-1 keep low fast-fail risk | validation | 50.0% | 84.5% | OOS probability scale shifted lower; keep rule 放水 |
| stage-1 keep low fast-fail risk | robustness | 50.0% | 78.4% | OOS probability scale shifted lower; keep rule 放水 |
| stage-2 select high continuation | train | 50.0% | 50.0% | train budget exact |
| stage-2 select high continuation | validation | 50.0% | 37.7% | OOS probability scale shifted lower; high-score rule 收紧 |
| stage-2 select high continuation | robustness | 50.0% | 31.7% | OOS probability scale shifted lower; high-score rule 收紧 |

两个 stage 的预算朝相反方向漂移，但根因一致：prior probability shift。OOS base rate 比 train 低时，模型输出概率整体下移；stage-1 的“留低风险”会放水，stage-2 的“选高 continuation”会收紧。

### 1.2 Rank signal 仍然存在

Stage-1 fast-fail score bucket 在三个 split 中都有明显排序：

| split | lowest-risk bucket fast-fail rate | highest-risk bucket fast-fail rate | spread |
|---|---:|---:|---:|
| train | 0.1367 | 0.7116 | 0.5750 |
| validation | 0.1601 | 0.5930 | 0.4329 |
| robustness | 0.1180 | 0.5612 | 0.4431 |

Stage-2 continuation score bucket 也有排序：

| split | highest-score bucket continuation rate | lowest-score bucket continuation rate | spread |
|---|---:|---:|---:|
| train | 0.2910 | 0.0434 | 0.2476 |
| validation | 0.1236 | 0.0463 | 0.0772 |
| robustness | 0.1738 | 0.0772 | 0.0966 |

所以 12A6c 不是 signal collapse，而是 absolute threshold transport failure。12A7 必须把 rank transport 和 probability calibration transport 拆开。

### 1.3 Budget confound 必须拆开

Stage-1 robustness 中，模型和 best single feature 的预算不同：

| comparison | model budget | comparator budget | comparable |
|---|---:|---:|---|
| model vs random p50 | 3,651 / 78.4% | 3,651 / 78.4% | yes |
| model vs best single feature | 3,651 / 78.4% | 2,330 / 50.0% | no |

因此 `model_minus_best_single_feature = +0.0816` 不能直接解释为模型劣势；一部分是 78% vs 50% 的 budget artifact。12A7 需要补同预算 trailing-rank / rank-diagnostic 读数。

Stage-2 更值得警惕：robustness 下 model 只选 31.7% 却只有 0.1689 continuation，而 single feature 在 50% 预算下有 0.1831。更挑剔的预算反而更低，这是 stage-2 多特征模型没有赚到复杂度的实质证据。

## 2. 部署模型

12A7 必须先冻结 deployment model，因为 operating point 依赖它。

当前 C0 是 event-driven single-name signal：

```text
一个 instrument 在 event_t0 出现 C0；
可执行进入点是 next executable open；
决策时只能看到该事件自身、同日之前已发生事件、以及历史事件；
不能看到同月后续会出现哪些 C0。
```

所以 primary deployable operating point 不是 same-month cross-sectional rank，而是：

```text
trailing-rank / trailing-percentile:
  在决策时，用过去已发生的可比 C0 events 的 score empirical distribution
  给当前 event 计算 percentile；
  stage-1 保留低风险 percentile <= X；
  stage-2 选择 continuation percentile >= 1-X。
```

允许的 cohort history：

```text
global trailing window:
  all prior C0 risk_on events before current event_t0

board trailing window:
  prior C0 risk_on events in same board_bucket before current event_t0

fallback rule:
  if board trailing window sample_n < min_history_n, fall back to global trailing window
```

不允许作为 primary gate：

```text
same calendar_month full-cohort rank:
  uses later events in the month, look-ahead

whole validation / robustness split rank:
  reselects OOS operating point, anti-cherry-pick violation

board x month full-cohort rank:
  also look-ahead unless restricted to events already known at decision time
```

这些 non-deployable ranks 可作为 diagnostic upper bar，但必须在 output 中标记：

```text
diagnostic_only_flag = true
lookahead_rank_upper_bar = true
not_allowed_for_decision = true
```

## 3. 修订后的研究主假设

### H1. 失败主要来自 prior probability shift

固定 -10% / +20% barrier 在不同 volatility / year / board regime 下含义不同，导致 base rate 非平稳。Train absolute probability threshold 过拟合了 train base rate。

12A7 不应继续修补单一绝对概率阈值，而应先测试 trailing-rank 是否能稳定迁移。

### H2. Trailing-rank 比 absolute threshold 更接近可部署规则

Trailing-rank 在决策时只使用历史 score distribution，因此 PIT。它不会保证 OOS 预算精确等于 X；如果 score distribution 漂移，actual budget 仍会漂移。这个漂移必须输出和解释。

```text
required readout:
  actual_budget_by_split
  budget_abs_delta_vs_train_selected_X
  trailing_history_n_distribution
  fallback_to_global_history_rate
```

### H3. Stage-1 与 stage-2 volatility 方向相反是两阶段设计的正证据

12A6c single-feature frontier 显示：

```text
stage-1:
  low volatility / defensive state -> fewer fast-fails

stage-2:
  high realized path volatility / post-survival thrust -> more continuation
```

这不是矛盾，而是条件集不同：入场前挑平静，幸存后挑有推力。12A7 应保留 two-stage decomposition，并显式测试 simple backbone 是否已经足够。

### H4. Single-feature challenger 是主 gate，不是附属诊断

Random baseline 只是 lower bound。12A7 的主 gate 必须要求 model 在 robustness 下打赢 train-frozen single-feature / simple-backbone challenger，并且差异要有统计约束。

正式 single-feature challenger 必须在 train 冻结：

```text
select_feature_on_train_only
select_orientation_on_train_only
select_budget_X_on_train_only
apply unchanged to validation / robustness
```

OOS best-single 只能作为 diagnostic upper bar。

## 4. 12A7 Scope

Reviewer 建议把第一版计划拆小。修订后，12A7 只覆盖 A + C + E：

```text
A. PIT trailing-rank operating point audit
C. defensive single-feature / low-capacity monotone challenger gate
E. stage-2 decoupled and chained survivor diagnostics
```

12A7 不包含：

```text
B. probability calibration / prior-shift correction
   -> split to future 12A8 probability calibration / prior-shift audit

D. vol-scaled barrier label revision
   -> split to future 12A9 vol-scaled barrier stability / separability audit

F. policy-layer sizing / abstention
   -> out of 12A7 operating-point validation scope
```

## 5. Direction A：PIT Trailing-rank Operating Point

### 5.1 Primary rule

Stage-1：

```text
score = stage1_fast_fail_score
history = prior C0 risk_on events before event_t0
percentile = empirical_percentile(score within history)
keep = percentile <= X
direction = lower score is better
```

Stage-2：

```text
score = stage2_continuation_score
history = prior stage-2 evaluable survivor events before stage2_decision_date
percentile = empirical_percentile(score within history)
continue = percentile >= 1 - X
direction = higher score is better
```

X grid：

```text
30%, 50%, 70%
```

Primary X selection：

```text
Use train only.
Pre-register selection rule before validation / robustness readout.
Default primary X = 50% unless train lift curve shows monotone failure.
```

The plan must report OOS actual budget; it must not assert budget pass by construction.

### 5.2 Minimum history and fallback

Trailing rank requires enough prior events:

```text
min_history_n_stage1 = 500 for global history
min_history_n_stage1_board = 150 for board-specific history
min_history_n_stage2 = 250 for global survivor history
min_history_n_stage2_board = 75 for board-specific survivor history
```

If board-specific history is insufficient, fallback to global history. If global history is insufficient, row is `rank_not_evaluable` for the operating readout and remains diagnostic-only.

### 5.3 Diagnostic upper bars

The following are allowed only for interpretation:

```text
same_month_full_cohort_rank
board_month_full_cohort_rank
whole_split_rank
```

They answer:

```text
If look-ahead cohort membership were known, how much separation is theoretically available?
```

They cannot enter support gate or next_allowed_requirement.

## 6. Direction C：Single-feature / Simple-backbone Gate

Stage-1 defensive backbone candidates：

```text
volatility_20d ascending
volatility_60d ascending
max_drawdown_60d ascending
distance_to_60d_low ascending
distance_to_120d_low ascending
rebound_from_60d_low ascending
```

Stage-2 continuation backbone candidates：

```text
realized_path_volatility_0_20d descending
realized_max_high_return_0_20d descending
realized_early_window_ret_0_10d descending
realized_ma_5_20_spread_at_day20 descending
distance_to_120d_low descending
```

Allowed model families：

```text
few-feature logistic regression
low-capacity logistic regression
monotone-constrained model only if dependency and monotonicity map are available
shallow decision tree diagnostic-only
```

Formal challenger selection：

```text
single_feature_challenger selected on train only
orientation selected on train only
feature list hash recorded
applied unchanged to validation and robustness
```

## 7. Direction E：Stage-2 Decoupling and Chained Readouts

Stage-2 needs two readouts:

### 7.1 Decoupled ground-truth survivor diagnostic

```text
denominator = ground_truth no_fast_fail_L10_H20 survivors
purpose = isolate whether stage-2 signal exists without stage-1 denominator pollution
deployable = false
```

This is diagnostic only. It must not be interpreted as a deployable strategy.

### 7.2 Chained trailing-rank survivor readout

```text
denominator = stage-1 trailing-rank keep AND no_fast_fail_L10_H20 path-evaluable
purpose = test whether fixing stage-1 operating point de-pollutes stage-2 denominator
deployable = yes if all PIT gates pass
```

Headline stage-2 decision should report both:

```text
stage2_decoupled_signal_status
stage2_chained_operating_status
```

## 8. Metrics and Statistical Gates

### 8.1 Rank-quality metrics

The rank gate must not use trivial finite-only checks.

Required：

```text
auc_train
auc_validation
auc_robustness
rank_ic_train
rank_ic_validation
rank_ic_robustness
decile_lift_train
decile_lift_validation
decile_lift_robustness
```

Suggested floors：

```text
stage1_auc_robustness >= 0.55
stage2_auc_robustness >= 0.55
rank_ic sign consistent across train / validation / robustness
robustness decile lift direction correct
```

Validation is a readout, not a hard support gate, because 12A6c validation is thin and low-base-rate. Robustness remains the primary OOS gate.

### 8.2 Bootstrap confidence intervals

Headline deltas require bootstrap CIs:

```text
model_vs_random_delta_ci95
model_vs_single_feature_delta_ci95
model_vs_t0_only_delta_ci95 for stage-2
```

Supported requires:

```text
CI excludes zero in the correct direction
and point estimate exceeds positive min_delta
```

Initial margins：

```text
stage1_min_delta_vs_random = 0.02 absolute fast-fail-rate reduction
stage1_min_delta_vs_single = 0.01 absolute fast-fail-rate reduction
stage2_min_delta_vs_random = 0.02 absolute continuation-rate increase
stage2_min_delta_vs_single = 0.01 absolute continuation-rate increase
```

If CI is too wide because of sample size, state is partial or diagnostic, not supported.

### 8.3 Minimum sample size

Cells below minimum sample size cannot be headline gates:

```text
headline_split_min_selected_n = 300
stage2_headline_min_selected_n = 150
slice_min_selected_n = 100
bootstrap_min_positive_n = 30
```

Sub-threshold board / family / year cells remain diagnostic-only.

### 8.4 Lift curve first

Decision should not hinge only on 50% budget. Required curve:

```text
X = 30%, 50%, 70%
decile and quintile lift
tail lift for lowest-risk / highest-score bucket
```

The report should lead with AUC + lift curve + budget curve, then show primary X.

## 9. Concept Drift and Follow-up Routing

12A7 should include a diagnostic concept-drift readout, but not calibration correction:

```text
for train-frozen single-feature candidates:
  estimate univariate relationship sign by split/year/board
  report whether sign/slope direction is stable
```

Interpretation:

```text
stable sign + calibration failure:
  likely prior / calibration drift -> route to 12A8

sign inversion or slope collapse:
  concept drift -> calibration alone unlikely to fix
```

Vol-scaled label audit is routed to future 12A9 and must include separability, not only base-rate flatness:

```text
flat base rate without single-feature separability = not useful
```

## 10. Required Outputs

12A7 primary outputs:

```text
input_artifact_audit.csv
trailing_rank_score_quality_metrics.csv
trailing_rank_operating_point_readout.csv
trailing_rank_budget_drift_audit.csv
trailing_rank_random_same_budget_audit.csv
trailing_rank_single_feature_challenger.csv
trailing_rank_decile_lift_readout.csv
trailing_rank_budget_curve_readout.csv
stage2_ground_truth_survivor_readout.csv
stage2_chained_trailing_rank_readout.csv
concept_drift_univariate_stability_audit.csv
diagnostic_lookahead_rank_upper_bar.csv
trailing_rank_decision.csv
```

Report:

```text
outputs/publishable/reports/trailing_rank_operating_point_validation_report.md
```

Manifest:

```text
outputs/manifests/12A7_trailing_rank_operating_point_validation_manifest.json
```

## 11. Decision Map

```text
12A7_trailing_rank_supported:
  stage-1 and stage-2 chained trailing-rank rules beat random and train-frozen single-feature
  on robustness with CI support and sample-size gates.

12A7_stage1_trailing_rank_supported_stage2_partial:
  stage-1 supported; stage-2 chained partial or decoupled-only.

12A7_simple_backbone_supported_complex_model_not_supported:
  simple train-frozen challenger works; complex model does not beat it.

12A7_rank_signal_diagnostic_only:
  AUC / lift exists, but bootstrap or sample-size gate blocks supported status.

12A7_no_rank_transport:
  rank signal fails robustness AUC / rank-IC / lift / random baseline.

12A7_blocked_input_or_pit_failure:
  required input, PIT, leakage, or split boundary gate fails.
```

## 12. Recommended Landing Sequence

12A7 v1 should be landable and narrow:

```text
1. trailing-rank operating point
2. train-frozen single-feature / simple-backbone challenger
3. AUC / rank-IC / decile lift / budget curve
4. bootstrap CI for model-vs-random and model-vs-single deltas
5. stage-2 ground-truth survivor diagnostic
6. stage-2 chained trailing-rank readout
7. diagnostic-only look-ahead rank upper bar
```

Then route follow-ups:

```text
if trailing rank works but absolute threshold failed:
  write / implement 12A8 calibration prior-shift audit

if rank fails or concept drift is visible:
  write / implement 12A9 vol-scaled label stability and separability audit

if simple backbone wins but complex model fails:
  consider simple defensive backbone requirement before 12A8 / 12A9 follow-up
```

## 13. One-line Thesis

12A7 should validate deployable trailing-rank transport under an event-driven single-name C0 workflow. It must not guarantee OOS budget by ranking over future-known cohorts; it must report residual budget drift, beat train-frozen single-feature challengers with bootstrap support, and keep calibration and vol-scaled label work as later follow-up requirements.

# 12A6d Rank-based Operating Point Revision Research Plan

## 0. 计划定位

本计划承接 12A6c `two_stage_fast_fail_rejector_continuation_report.md` 的结论和后续讨论，用于定义 12A6d 的研究方向。12A6d 不应直接进入 12A7 OOS validation；它应先修正 12A6c 暴露出的 operating-point 问题。

12A6c 的核心结论不是“没有信号”，而是：

```text
C0 risk_on 内 fast-fail / continuation 形态可排序；
但 train-frozen absolute probability threshold 无法稳定迁移到 base-rate 非平稳的 OOS 总体。
```

因此 12A6d 的核心任务不是调模型超参，而是重新定义可部署、PIT、anti-cherry-pick 的 operating point，并把主 gate 从“跑赢 random”升级到“跑赢 train-frozen single-feature frontier”。

## 1. 12A6c 关键证据

### 1.1 当前失败状态

```text
12A6c decision = 12A6c_stage1_partial
input gate = pass
stage_1_threshold_health = fail
stage_2_threshold_health = fail
next_allowed_requirement = requirement_12a6d_stage1_rejector_feature_or_label_revision.md
```

Primary logistic regression 的 train-frozen threshold 外推结果：

| stage | split | target budget | actual budget | interpretation |
|---|---:|---:|---:|---|
| stage-1 keep low fast-fail risk | train | 50.0% | 50.0% | train budget exact |
| stage-1 keep low fast-fail risk | validation | 50.0% | 84.5% | OOS probability scale shifted lower; keep rule 放水 |
| stage-1 keep low fast-fail risk | robustness | 50.0% | 78.4% | OOS probability scale shifted lower; keep rule 放水 |
| stage-2 select high continuation | train | 50.0% | 50.0% | train budget exact |
| stage-2 select high continuation | validation | 50.0% | 37.7% | OOS probability scale shifted lower; high-score rule 收紧 |
| stage-2 select high continuation | robustness | 50.0% | 31.7% | OOS probability scale shifted lower; high-score rule 收紧 |

这两个方向相反的预算漂移来自同一个机制：prior probability shift。OOS base rate 比 train 低时，模型输出概率整体下移；在 stage-1 的“留低风险”规则上表现为更多样本低于阈值，在 stage-2 的“选高 continuation”规则上表现为更少样本高于阈值。

### 1.2 Rank signal 仍然存在

Stage-1 fast-fail score bucket 在 train / validation / robustness 都有明显单调性：

| split | lowest-risk bucket fast-fail rate | highest-risk bucket fast-fail rate | spread |
|---|---:|---:|---:|
| train | 0.1367 | 0.7116 | 0.5750 |
| validation | 0.1601 | 0.5930 | 0.4329 |
| robustness | 0.1180 | 0.5612 | 0.4431 |

Stage-2 continuation score bucket 同样有排序能力：

| split | highest-score bucket continuation rate | lowest-score bucket continuation rate | spread |
|---|---:|---:|---:|
| train | 0.2910 | 0.0434 | 0.2476 |
| validation | 0.1236 | 0.0463 | 0.0772 |
| robustness | 0.1738 | 0.0772 | 0.0966 |

这说明 12A6c 的失败不能被解释为 signal collapse；更准确的解释是 absolute probability threshold transport failed。

### 1.3 Budget confound 必须拆开

12A6c 中部分 “model vs single-feature” 读数被预算差异污染。

Stage-1 robustness：

| comparison | model budget | comparator budget | comparable |
|---|---:|---:|---|
| model vs random p50 | 3,651 / 78.4% | 3,651 / 78.4% | yes |
| model vs best single feature | 3,651 / 78.4% | 2,330 / 50.0% | no |

因此，stage-1 `model_minus_best_single_feature = +0.0816` 不能直接解释为模型劣势；其中相当一部分可能是 budget artifact。12A6d 必须补一个 budget-matched rank-50% 实验：model rank-50% vs random-50% vs train-frozen single-feature-50%。

Stage-2 的情况更严峻：robustness 下 model 只选 31.7% 却拿到 0.1689 continuation，而 single feature 在 50% 预算下拿到 0.1831。更挑剔的预算反而低于单特征，说明 stage-2 多特征模型确实没有赚到复杂度。

## 2. 研究主假设

### H1. 当前主要失败来自 prior probability shift

固定 -10% / +20% barrier 在不同 volatility / year / board regime 下含义不同，导致 base rate 非平稳。Train 上拟合的绝对概率阈值，本质上过拟合了 train base rate。

12A6d 必须把 score rank transport 和 probability calibration transport 分离审计。

### H2. Rank-based operating point 更接近可部署规则

横截面 rank 分位规则在决策时只使用当期 cohort 内的 score 排序：

```text
stage-1:
  在当期 cohort 内保留 fast-fail risk score 最低的 X%

stage-2:
  在当期 survivor cohort 内选择 continuation score 最高的 X%
```

模型、特征、分位 X、tie-break rule 都在 train 冻结；OOS 只执行规则。rank 是在决策时对当期可见候选集合计算，因此仍然 PIT，不违反 anti-cherry-pick。

### H3. Stage-1 和 stage-2 的 volatility 方向相反是两阶段设计的正证据

12A6c single-feature frontier 显示：

```text
stage-1 best stable signal:
  low volatility / defensive state
  volatility_20d or volatility_60d ascending

stage-2 best stable signal:
  realized path volatility / post-survival thrust
  realized_path_volatility_0_20d descending
```

这不是矛盾，而是条件集不同。入场前要挑平静、低 fast-fail 风险的 C0；survive 20d 后，要挑已经证明有推力的路径。这个方向差异支持 two-stage decomposition；pooled one-shot model 可能会把两个相反机制互相抵消。

### H4. Single-feature frontier 应升级为主基准

Random baseline 只能证明模型不是随机；它不足以证明复杂模型有研究价值。12A6d 的主 gate 应要求 robustness 下 model rank rule 同时打赢：

```text
matched random same-budget p50
train-frozen single-feature frontier same-budget
```

其中 single-feature challenger 必须在 train 冻结，不能用 OOS split 事后挑最优特征作为正式 gate。OOS best-single 可作为 diagnostic upper bar。

### H5. Vol-scaled barrier 可能是修复 base-rate 非平稳的根本方向

固定百分比 barrier 会把不同 volatility regime 下的路径放在同一 label 尺度上，天然制造 base-rate drift。AFML meta-labeling 更正统的做法是使用 volatility-scaled triple barrier。

12A6d 不必立刻全量替换标签，但应加入轻量 base-rate stability audit：

```text
fixed barrier:
  lower = -10%, upper = +20%

vol-scaled barrier:
  lower = -k1 * pre-event realized volatility or ATR
  upper = +k2 * pre-event realized volatility or ATR
```

先比较跨 split / year / board / family 的 base-rate 稳定性，再决定是否进入全量 vol-scaled label revision。

## 3. 研究方向与优先级

### 方向 A：Rank-based Operating Point Audit

优先级：P0。成本最低，信息量最高。

核心问题：

```text
当 operating point 从 absolute probability threshold 改成 cross-sectional rank percentile，
stage-1 和 stage-2 的 rank signal 是否能在 robustness 下打赢 random 与 train-frozen single-feature?
```

部署规则：

```text
cohort_unit candidates:
  calendar_month
  board_bucket x calendar_month
  rolling_decision_window

stage-1:
  within cohort, sort by stage1_fast_fail_score ascending
  keep lowest-risk X%

stage-2:
  within survivor cohort, sort by stage2_continuation_score descending
  continue highest-score X%

X grid:
  30%, 50%, 70%
primary X:
  selected on train only by pre-registered rule
```

必需输出：

```text
rank_operating_point_readout.csv
rank_budget_matched_random_audit.csv
rank_single_feature_frontier.csv
rank_score_quality_metrics.csv
rank_decision.csv
rank_operating_point_report.md
```

必测指标：

| metric | purpose |
|---|---|
| per-split AUC | 判断 rank signal 是否跨 split 存在 |
| Spearman rank-IC | 判断 score 与 label 的 rank relation |
| decile lift | 判断 top/bottom decile 是否稳定分层 |
| budget curve 30/50/70 | 判断 operating point 是否敏感 |
| model vs random same-budget | 判断是否超过随机路径 |
| model vs train-frozen single-feature same-budget | 判断复杂模型是否有增量 |

Stage-1 primary gate：

```text
robustness_model_rank50_fast_fail_rate
  < robustness_random_rank50_fast_fail_rate_p50

robustness_model_rank50_fast_fail_rate
  < robustness_train_frozen_single_feature_rank50_fast_fail_rate

rank50 actual budget within tolerance by construction
```

Stage-2 primary gate：

```text
robustness_model_rank50_continuation_rate
  > robustness_random_rank50_continuation_rate_p50

robustness_model_rank50_continuation_rate
  > robustness_train_frozen_single_feature_rank50_continuation_rate

realized_path_incremental_value_vs_t0_only > 0
```

Decision states：

```text
12A6d_rank_operating_point_supported
12A6d_stage1_rank_supported_stage2_partial
12A6d_stage1_rank_partial
12A6d_no_rank_transport
12A6d_blocked_input_or_pit_failure
```

### 方向 B：Probability Calibration / Prior-shift Audit

优先级：P1。只有方向 A 显示 rank works 后才值得做。

核心问题：

```text
如果 rank signal 可以迁移，但 absolute threshold 不行，
能否通过 train-only / pre-decision-only calibration 把概率刻度修回来?
```

候选方法：

- expanding-window Platt scaling；
- expanding-window isotonic calibration；
- base-rate-adjusted posterior correction；
- cohort-level intercept shift using only prior historical labels；
- score quantile normalization within PIT cohort。

必需纪律：

```text
calibrator_fit_data <= decision_time
no validation / robustness label used to tune calibrator
calibration window and update frequency pre-registered
```

输出：

```text
calibration_drift_audit.csv
calibrated_threshold_health.csv
calibrated_vs_rank_comparison.csv
```

解释目标：

- 如果 rank works 且 calibration fixes threshold health，问题主要是 prior shift / calibration drift。
- 如果 rank works 但 calibration still fails，可能是 concept drift 或 cohort composition drift。
- 如果 rank fails，12A6c 的 bucket evidence 可能只是局部 / coarse sorting artifact。

### 方向 C：Defensive Single-feature Backbone and Low-capacity Monotone Model

优先级：P1。

Stage-1 当前最稳的单特征是低波动方向；stage-2 当前最稳的是 realized path volatility / early momentum。12A6d 应把这些单特征从 diagnostic 提升为 formal challenger。

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

Allowed low-capacity models：

```text
few-feature logistic regression
monotone-constrained GBDT if dependency available
shallow decision tree diagnostic only
```

主 gate：

```text
complex_model must beat train-frozen single-feature / simple-backbone challenger on robustness.
```

如果 complex model 不能打赢 simple backbone，12A6d 应输出 simple-backbone-supported 或 complex-model-not-supported，而不是把 random uplift 误读为模型成功。

### 方向 D：Vol-scaled Barrier Base-rate Stability Audit

优先级：P2。潜在回报高，但不应先全量重构。

核心问题：

```text
固定 -10% / +20% barrier 是否是 base-rate drift 的制造机？
vol-scaled barrier 是否能显著平滑 split/year/board/family base rate?
```

轻量审计设计：

```text
pre_event_vol_sources:
  volatility_20d
  volatility_60d
  ATR proxy if available

lower_grid:
  -1.0x, -1.5x, -2.0x pre-event vol

upper_grid:
  +2.0x, +3.0x, +4.0x pre-event vol

horizon:
  stage-1 H20
  stage-2 H2_20
```

主要输出：

```text
vol_scaled_label_base_rate_audit.csv
fixed_vs_vol_scaled_base_rate_stability.csv
vol_scaled_label_decision.csv
```

主指标：

| metric | interpretation |
|---|---|
| split base-rate range | 越小越稳定 |
| year base-rate std | 越小越稳定 |
| board base-rate gap | 越小越稳定 |
| positive rate floor | 不能过稀 |
| label-event coverage | 不能牺牲太多分母 |

只有当 vol-scaled label 明显改善 base-rate stability，才进入后续全量 label revision。

### 方向 E：Stage-2 Ground-truth Survivor Decoupling

优先级：P1。

12A6c 的 headline stage-2 denominator 依赖 stage-1 predicted keep，而 stage-1 keep 自身发生 OOS budget drift。为了判断 stage-2 是否值得独立投入，需要做一个解耦读数：

```text
stage2_denominator =
  ground_truth no_fast_fail_L10_H20 survivors
  not stage1 predicted keep survivors
```

这不是可部署策略，只是 diagnostic feasibility：

```text
Q. 如果先验知道哪些 C0 没有 fast-fail，
   day-20 realized path + t0 features 能否稳定筛出 continuation?
```

输出：

```text
stage2_ground_truth_survivor_readout.csv
stage2_ground_truth_survivor_single_feature_frontier.csv
stage2_ground_truth_survivor_decision.csv
```

解释：

- 如果 ground-truth survivor stage-2 仍输 single-feature，则 stage-2 complex model 暂停。
- 如果 ground-truth survivor stage-2 明显支持，但 chained stage-2 不支持，问题主要在 stage-1 denominator pollution。

### 方向 F：Policy-layer Reinterpretation of Stage-1

优先级：P3，远期。

如果 stage-1 稳健核心只是低波动 / 低回撤，二元 keep/reject 可能不是最佳表达。后续可以考虑：

```text
vol-scaled position sizing
high-volatility abstention
risk budget haircut
```

但这属于 policy layer，不应进入 12A6d 主线。12A6d 仍然只做 modeling / label feasibility，不做仓位、交易成本或资金曲线。

## 4. 12A6d 推荐实验结构

### 4.1 Primary arm

```text
arm_id = rank_based_operating_point
purpose = test rank transport under PIT cross-sectional percentile operating rule
```

步骤：

1. 复用 12A6c 的 C0 risk_on universe、t0 features、stage-1 label、stage-2 label、matched random baseline。
2. 训练模型仍只在 train。
3. 在 train 上冻结：
   - feature list；
   - model family；
   - rank budget X；
   - cohort definition；
   - tie-break rule；
   - formal single-feature challenger。
4. 在 validation / robustness 上只执行 frozen rank rule。
5. 输出 model vs random vs single-feature 的 budget-matched readout。

### 4.2 Diagnostic arms

```text
arm_id = prior_shift_calibration_audit
purpose = separate calibration drift from rank drift
```

```text
arm_id = vol_scaled_label_base_rate_audit
purpose = test whether fixed barriers cause base-rate non-stationarity
```

```text
arm_id = stage2_ground_truth_survivor_decoupling
purpose = test stage-2 signal without stage-1 denominator pollution
```

### 4.3 Explicit non-goals

12A6d 不做：

- 不进入 12A7 OOS validation；
- 不做 policy replay；
- 不声明可交易 alpha；
- 不用 OOS split 选择 feature、budget、cohort、threshold、label；
- 不用 post-event future path 做 stage-1 feature；
- 不把 stage-2 ground-truth survivor diagnostic 误读为可部署策略；
- 不把 random uplift 当作复杂模型成功的充分条件。

## 5. Gate 设计

### 5.1 Input gate

输入 gate 继承 12A6c：

```text
12A6c decision in [
  12A6c_stage1_partial,
  12A6c_stage1_supported_stage2_partial,
  12A6c_two_stage_supported
]

input_artifact_audit all pass
C0 risk_on event_n = 15113
feature matrix no target leakage
split_time_boundary_audit pass
```

### 5.2 Rank transport gate

Rank transport gate 关注排序，不关注 absolute probability calibration：

```text
auc_train, auc_validation, auc_robustness all finite
rank_ic_train, rank_ic_validation, rank_ic_robustness all finite
decile_lift_robustness direction correct
budget-matched rank readout present for X = 30%, 50%, 70%
```

### 5.3 Stage-1 support gate

Primary stage-1 rank rule supported if：

```text
robustness_model_rank50_fast_fail_rate
  <= robustness_random_rank50_fast_fail_rate_p50 - min_delta

robustness_model_rank50_fast_fail_rate
  <= robustness_train_frozen_single_feature_rank50_fast_fail_rate - min_delta_vs_single

validation_model_rank50_fast_fail_rate
  <= validation_random_rank50_fast_fail_rate_p50

rank_budget_health = pass by construction
```

建议初始门槛：

```text
min_delta = 0.02 absolute fast-fail rate
min_delta_vs_single = 0.00 for first feasibility
```

如果无法打赢 single-feature，输出 partial，不支持复杂模型。

### 5.4 Stage-2 support gate

Primary stage-2 rank rule supported if：

```text
robustness_model_rank50_continuation_rate
  >= robustness_random_rank50_continuation_rate_p50 + min_delta

robustness_model_rank50_continuation_rate
  >= robustness_train_frozen_single_feature_rank50_continuation_rate + min_delta_vs_single

realized_path_incremental_value_vs_t0_only > 0
```

建议初始门槛：

```text
min_delta = 0.02 absolute continuation rate
min_delta_vs_single = 0.00 for first feasibility
```

### 5.5 Vol-scaled label gate

Vol-scaled label audit supported if：

```text
base_rate_year_std_vol_scaled < base_rate_year_std_fixed
base_rate_board_gap_vol_scaled < base_rate_board_gap_fixed
positive_rate not too sparse
coverage_rate acceptable
```

该 gate 只决定是否值得开启后续 label revision，不直接决定 12A6d rank model support。

## 6. Required outputs

建议 12A6d 至少输出以下 publishable tables：

```text
input_artifact_audit.csv
rank_score_quality_metrics.csv
rank_operating_point_readout.csv
rank_budget_matched_random_audit.csv
rank_single_feature_frontier.csv
rank_decile_lift_readout.csv
rank_budget_curve_readout.csv
calibration_drift_audit.csv
stage2_ground_truth_survivor_readout.csv
vol_scaled_label_base_rate_audit.csv
fixed_vs_vol_scaled_base_rate_stability.csv
rank_decision.csv
```

建议输出报告：

```text
outputs/publishable/reports/rank_based_operating_point_revision_report.md
```

建议输出 manifest：

```text
outputs/manifests/12A6d_rank_based_operating_point_revision_manifest.json
```

## 7. Decision map

```text
12A6d_rank_operating_point_supported:
  stage-1 rank rule and stage-2 rank rule both beat random and train-frozen single-feature on robustness.
  next = 12A7 rank-based OOS validation.

12A6d_stage1_rank_supported_stage2_partial:
  stage-1 rank rule supported, stage-2 not supported.
  next = stage-1 rejector OOS validation or stage-2 continuation simplification.

12A6d_stage1_rank_partial:
  stage-1 beats random but not single-feature, or validation/robustness mixed.
  next = simple defensive backbone requirement.

12A6d_no_rank_transport:
  rank signal fails AUC/rank-IC/decile-lift or fails random baseline.
  next = label revision / vol-scaled barrier study.

12A6d_blocked_input_or_pit_failure:
  required inputs, PIT, leakage, or split boundary gate fails.
```

## 8. Recommended landing sequence

第一步只做方向 A + 必要 diagnostics：

```text
12A6d v1:
  rank-based operating point
  AUC / rank-IC / decile lift
  budget-matched model vs random vs train-frozen single-feature
  stage2 ground-truth survivor diagnostic
```

第二步再做低成本标签诊断：

```text
12A6d v2:
  vol-scaled label base-rate stability audit
  calibration / prior-shift decomposition
```

第三步才决定是否写 12A7：

```text
if rank-based stage-1 supported:
  consider 12A7 rank-based OOS validation

if rank-based model fails but simple backbone works:
  write simple-backbone requirement

if rank also fails:
  stop model path and move to vol-scaled label revision
```

## 9. One-line thesis

12A6d 应验证的是 rank transport，而不是继续修补 absolute threshold transport。C0 risk_on 已经显示 fast-fail / continuation 可排序，下一步必须用 PIT 横截面分位 operating point、budget-matched single-feature gate 和 vol-scaled label audit，判断这个排序信号是否能变成稳定的两阶段研究主线。

# EP4 Requirement 03a: Probability-Only Survival-Step Feasibility V1

## 1. Requirement Metadata

- Requirement id: `ep4_r03a_probability_survival_step_feasibility_v1`
- Short name: `r03a_probability_survival_step_feasibility_v1`
- Status: implementation-ready probability-only diagnostic requirement
- Owner workflow: EP4
- Upstream discussion: `ep4/discussion3.md`
- Upstream prior diagnostic requirement: `ep4/requirement_02_1_prior_probability_diagnostic_v1.md`
- Upstream prior diagnostic output root: `ep4/outputs/r02_1_prior_probability_diagnostic_v1/`
- Required output root: `ep4/outputs/r03a_probability_survival_step_feasibility_v1/`
- Required config path: `ep4/configs/r03a_probability_survival_step_feasibility_v1.yaml`
- Required runner path: `ep4/scripts/run_r03a_probability_survival_step_feasibility.py`
- Required validator path: `ep4/scripts/validate_r03a_probability_survival_step_feasibility.py`
- Date: 2026-05-14

## 2. Purpose

本需求把 `discussion3.md` 的 staged evidence / 1R build-budget 讨论收缩成第一版可执行合同：

```text
probability-only survival-step feasibility audit
```

它只回答：

```text
在 R02 已冻结 family signal 形成的 seed episode 上，
T0 probe + train-frozen survival checkpoint step-up
是否在 validation / robustness 中优于
T0 full-entry、T0 probe-only、T0 probe + simple survival step-up baseline？
```

本需求不是完整 R03 risk-budget experiment。由于 R02.1 已确认：

```text
ev_r_ready = blocked_missing_ev_r
global_prior_ready = blocked_missing_denominator
split_stability_ready = blocked_unstable_split
```

R03a 不得输出最终 1R allocation、EV_R sizing、交易策略或 production signal。所有 `R` 值只允许作为固定 exposure schedule label / scenario label，用于比较路径质量和风险状态；不得解释为已验证仓位规模。

如果 R03a 不能在 train-frozen 规则下证明 staged posterior / survival logic 相对 `baseline_3` 有增量价值，则结论必须是：

```text
no incremental staged-posterior edge over survival step-up
```

并停止 validation 后调参。

## 3. Hard Scope

允许：

- 复用 R02.1 已生成的 prior / posterior / survival checkpoint / split stability artifacts；
- 复用 R02 family signal 120D path query 的 next-open entry 和 path label 口径；
- 在 episode-first-trigger grain 上重算 T0 prior 与 T+3 / T+5 / T+10 survivor posterior；
- 只在 train split 上选择 survival checkpoint、probability gate、fallback grain 和 fixed exposure schedule label；
- 在 validation / robustness 上只读评估 train-frozen candidate；
- 比较 `baseline_1`、`baseline_2`、`baseline_3` 与 R03a candidate 的概率路径质量；
- 输出 bundle / context / fresh evidence 的描述性解释表；
- 输出 null-result audit 和后续 R03b / fresh-sequence backlog。

禁止：

- 搜索新的 technical indicator、threshold、window、family 或 composite；
- 根据 validation / robustness 调整 survival checkpoint、threshold、bucket fallback 或 candidate；
- 使用 naive Bayes、shrinked log-odds 相加或 family LR 相乘；
- 将 same-day 多个 family 触发拆成多份 risk budget；
- 将 `same_day_bundle_key`、`context_bucket_id` 或 `fresh_evidence_status` 作为 primary gate，除非本需求明示允许且通过 sample / split gate；
- 使用 `EV_R_diagnostic`、`EV_R_lower`、terminal EV 或 expected R 作为 selection / promotion gate；
- 输出 buy / sell / add / reduce action；
- 输出 final 1R sizing、position size、portfolio simulation 或 production strategy；
- 使用 R02.1 缺失的 global action-time prior 伪装 market-wide background baseline；
- 引入新的在线数据抓取。

## 4. Required Input Artifacts

主输入必须来自本地 artifact，不得在线抓取：

```text
ep4/outputs/r02_1_prior_probability_diagnostic_v1/
```

必须读取并校验：

- `reports/r02_1_r03_input_readiness.csv`
- `reports/r02_1_single_family_prior.csv`
- `reports/r02_1_same_day_family_count_prior.csv`
- `reports/r02_1_same_day_bundle_prior.csv`
- `reports/r02_1_context_bucket_prior.csv`
- `reports/r02_1_survival_checkpoint_prior.csv`
- `reports/r02_1_fresh_evidence_prior.csv`
- `reports/r02_1_fresh_evidence_offset_distribution.csv`
- `reports/r02_1_split_stability_diagnostics.csv`
- `reports/r02_1_ev_r_input_audit.csv`
- `manifests/r02_1_prior_probability_diagnostic_manifest.json`
- `manifests/r02_1_prior_probability_diagnostic_validation.json`

必须同时读取 R02 path query lineage：

```text
ep4/outputs/r02_family_signal_120d_path_query_v1/
```

用于校验 frozen family signal、episode source、next-open anchor 和 path label authority。

如果任一 required input 缺失，runner 必须 fail closed，不得降级为从原始行情临时重算。

## 5. Upstream Blocker Contract

Runner 必须先读取 `r02_1_r03_input_readiness.csv`，并执行以下 gating。

允许继续 R03a 的最小条件：

```text
single_family_prior_ready = ready
same_day_bundle_prior_ready = ready
context_bucket_prior_ready = ready
survival_checkpoint_prior_ready = ready
fresh_evidence_prior_ready = ready
```

允许的已知 blocker：

```text
ev_r_ready = blocked_missing_ev_r
global_prior_ready = blocked_missing_denominator
split_stability_ready = blocked_unstable_split
```

这些 blocker 不阻止 R03a，但必须写入所有 manifest 和 final report：

```text
risk_budget_status = probability_only_ev_r_blocked
background_denominator_status = blocked_missing_denominator
split_stability_status = partial_only
```

如果 `ev_r_ready` 不是 `blocked_missing_ev_r` 也不是 `ready`，runner 必须 fail closed。

如果 `ev_r_ready = ready`，本需求仍不得升级为 R03b；只能把 EV_R 可用性记录为：

```text
ev_r_available_but_not_used_by_r03a
```

## 6. Frozen Signal Universe

R03a 的 signal universe 必须逐字继承 R02.1 / R02 path-analysis 的 7 个 single family：

```text
momentum_rps
oscillator
price_trend
pullback_drawdown
range_breakout
volatility_band
volume_money
```

实现必须从 upstream manifest / config 中校验：

```text
family_id
signal_id
condition_group_id
formula_hash or formula_text
```

Validator 必须 fail closed：

- family 数量不是 7；
- 任一 family id / signal id / condition group 与 R02.1 不一致；
- 任一 formula 使用新指标、新阈值或新窗口；
- 从 review composite 反推或扩展新的 single family；
- 将 review composite 作为 candidate gate。

4 个 review composite 只允许作为 descriptive lineage / comparison rows，不得作为 R03a candidate 来源。

## 7. Analysis Grain

### 7.1 Primary Grain: Episode-First-Trigger

R03a 的所有 primary comparison 必须使用同一 grain：

```text
seed_episode_id
instrument_id
seed_trade_date
seed_entry_date
seed_entry_price
seed_same_day_bundle_key
seed_same_day_family_count
seed_family_set
seed_type
seed_primary_family_id
split
year
```

Episode construction 必须继承 R02.1：

```text
seed starts on the first trade_date with any frozen family trigger
episode build window = seed_trade_date + 0 .. seed_trade_date + 30 trading days
new seed for the same instrument is allowed only after the previous build window ends
```

R03a 必须重算同粒度 T0 与 survival prior，不能直接把 R02.1 的 signal-event prior 和 survivor-episode posterior 相减。

`seed_primary_family_id` 的定义必须是确定性的：

```text
if seed_same_day_family_count == 1:
  seed_type = single_family_seed
  seed_primary_family_id = the only family in seed_same_day_bundle_key

else:
  seed_type = multi_family_bundle_seed
  seed_primary_family_id = multi_family_bundle
```

For multi-family same-day bundles, the implementation must not choose one component family as primary by ranking, observed outcome, train performance, or file order. The sorted family set is retained in `seed_family_set` / `seed_same_day_bundle_key` for descriptive lineage only.

### 7.2 Secondary Grains

以下 grain 只允许用于 descriptive / audit：

```text
same_day_bundle_key
same_day_family_count
single_family
context_bucket_id
fresh_evidence_status
fresh_offset_bucket
```

`same_day_family_count` 可作为 weak stratification / audit 字段。除非 train split 明确通过稳定性和样本门槛，否则不得作为 primary candidate gate。

`fresh_evidence_status` 在 R03a 中永远不得作为 primary gate。它只能用于解释和后续 fresh-sequence diagnostic backlog。

## 8. Entry And Path Anchor

所有 path label 和 survival checkpoint 必须沿用 R02 path-analysis convention：

```text
entry_date = first executable next-open date after seed_trade_date
entry_price = next executable open
path horizon = 120 trading days after entry
max gain price = high
max loss price = low
max drawdown policy = prior_peak_only
```

如果 episode 缺少 executable next-open entry 或 forward path，不得进入 headline denominator。必须记录：

```text
censored_or_invalid_count
censored_or_invalid_rate
invalid_reason
```

## 9. Mutually Exclusive Path Label

Primary label 继承 R02.1：

```text
bad_path
good_path
neutral_path
censored_or_invalid
```

固定优先级：

```text
1. if entry invalid or required forward path unavailable:
     label = censored_or_invalid

2. else if bad condition is true:
     label = bad_path

3. else if good condition is true:
     label = good_path

4. else:
     label = neutral_path
```

Headline posterior denominator 只能使用：

```text
label in {bad_path, good_path, neutral_path}
```

并必须满足：

```text
P_good + P_bad + P_neutral = 1
```

### 9.1 Bad Path

```text
early_failure_flag == true
OR first_minus5_offset <= 10
OR max_loss_before_first_plus10 <= -0.06
```

### 9.2 Good Path

```text
hit_plus10_before_minus5 == true
OR path_quality_flag in {clean_continuation, tradable_continuation}
```

如果同一样本同时满足 bad 和 good，必须按优先级标记为 `bad_path`。

## 10. Probability Estimation

R03a 使用 direct posterior table，不做 naive Bayes，不做 LR 相乘。

每个可评估 bucket 输出：

```text
label_denominator_count
good_count
bad_count
neutral_count
P_good
P_bad
P_neutral
P_good_lower
P_good_upper
P_bad_lower
P_bad_upper
credible_interval_width_good
credible_interval_width_bad
sample_sufficiency_status
split_stability_status
prior_source
fallback_level
```

Every probability-bearing output table must include this full probability schema. It is not valid to report only `P_good_lower` and `P_bad_upper` in downstream comparison tables.

### 10.1 Dirichlet-Multinomial Posterior

R03a 的 probability interval 必须使用 Dirichlet-Multinomial。

标签空间：

```text
label in {good_path, bad_path, neutral_path}
```

默认 prior：

```text
alpha_good = 0.5
alpha_bad = 0.5
alpha_neutral = 0.5
alpha_source = Jeffreys_prior
```

R03a v1 不允许 alternative prior。唯一允许的 prior 是：

```text
alpha_source = Jeffreys_prior
alpha_vector = {0.5, 0.5, 0.5}
```

The following prior is explicitly forbidden in R03a v1 because it reuses train labels for both prior formation and train scoring:

```text
train_empirical_fallback_prior
```

Validation / robustness 不得重新估计 `alpha`。

Credible interval level is fixed:

```text
credible_interval_level = 0.90
P_good_lower = posterior marginal quantile(P_good, 0.05)
P_good_upper = posterior marginal quantile(P_good, 0.95)
P_bad_lower = posterior marginal quantile(P_bad, 0.05)
P_bad_upper = posterior marginal quantile(P_bad, 0.95)
credible_interval_width_good = P_good_upper - P_good_lower
credible_interval_width_bad = P_bad_upper - P_bad_lower
```

The implementation may use deterministic Monte Carlo, closed-form beta marginal quantiles, or an equivalent deterministic numerical method. The method, random seed if any, and tolerance must be recorded in the manifest.

Train candidate selection must avoid in-sample posterior scoring:

```text
train_scoring_mode = train_inner_cv_out_of_fold
train_inner_cv_fold_count = 5
train_inner_cv_assignment = deterministic_hash(seed_episode_id, train_only_selection_seed)
```

For every train episode, `episode_probability_score` must be assigned from a posterior table fitted on train folds that do not contain that episode. Leave-one-episode-out is allowed only as the deterministic special case `train_inner_cv_fold_count = train_episode_count`.

After train selection, the runner may materialize a full-train frozen posterior table for validation / robustness scoring. Validation / robustness episode inclusion must use that frozen train table and must not use validation / robustness labels to choose a bucket, threshold, fallback grain, or candidate.

### 10.2 Probability-Only Score

R03a has exactly one episode-level probability gate score:

```text
episode_probability_score =
prob_feasibility_score =
  P_good_lower - P_bad_upper
```

The baseline-relative score is allowed only for candidate-row selection and reporting after `candidate_episode_included` has already been materialized:

```text
prob_edge_vs_baseline =
  (P_good_lower - baseline_P_good)
  - (P_bad_upper - baseline_P_bad)
```

`baseline` 必须来自 same split、same grain 或明示 fallback grain。

`prob_edge_vs_baseline` must not be used as `episode_probability_score`.

These scores can only decide:

```text
candidate allowed for validation
bucket fallback level
null result status
```

不得决定：

```text
stage cap
position size
expected R
final trading action
```

### 10.3 Candidate Pass / Fail Formula

Candidate success must be evaluated against `baseline_3_same_scope`, not against a global baseline.

Allowed `seed_scope_id` values:

```text
all
seed_type=single_family_seed
seed_type=multi_family_bundle_seed
seed_primary_family_id=<one of frozen 7 family ids>
seed_primary_family_id=multi_family_bundle
seed_same_day_family_count=<1..7>
same_day_bundle_key=<stable sufficient bundle key>
context_bucket_id=<stable sufficient context bucket id>
```

`same_day_bundle_key` and `context_bucket_id` scopes are allowed only as secondary fallback scopes after Section 14 gates pass. They must not create multiple same-day risk units.

No other family-group search is allowed. In particular, train may not create arbitrary subsets such as `range_breakout|volume_money` unless that exact set is already represented by an allowed stable `same_day_bundle_key` scope.

For every episode and candidate, define:

```text
episode_in_selected_seed_scope =
  episode seed attributes match seed_scope_id

episode_survived_selected_checkpoint =
  entry valid
  AND no observable -5% breach before or at selected_survival_checkpoint
  AND path not censored before selected_survival_checkpoint

episode_probability_bucket_key =
  deterministic bucket selected by fallback_grain
  using only fields observable on or before selected_survival_checkpoint

episode_probability_score =
  P_good_lower - P_bad_upper assigned to episode_probability_bucket_key
  from train-frozen posterior table or fallback table

candidate_episode_included =
  episode_in_selected_seed_scope
  AND episode_survived_selected_checkpoint
  AND episode_probability_score >= probability_gate_threshold
```

The `probability_gate_threshold` is selected in train only. Validation / robustness must apply the same threshold and fallback-grain mapping without recomputing bucket selection from validation outcomes.

For train rows, `episode_probability_score` must be the out-of-fold value from Section 10.1. For validation / robustness rows, it must be the value from the train-frozen posterior table.

`baseline_3_same_scope_episode_included` must use:

```text
episode_in_selected_seed_scope
AND episode_survived_selected_checkpoint
```

and must not apply `episode_probability_score >= probability_gate_threshold`.

For every train-selected candidate, define:

```text
candidate_scope_id =
  seed_scope_id
  + selected_survival_checkpoint
  + fallback_grain

baseline_3_same_scope =
  baseline_3_probe_survival_step_up
  using the same seed_scope_id
  and the same selected_survival_checkpoint
  but without the candidate probability-only gate
```

The only allowed difference between candidate and `baseline_3_same_scope` is the train-frozen probability-only gate. If the candidate uses a seed scope, seed type, or fallback grain, `baseline_3_same_scope` must use the same seed scope, seed type, and fallback grain. Otherwise the comparison measures scope selection rather than staged posterior edge.

### 10.4 Train Selection Grid And Tie-Breaker

Train selection must evaluate a finite deterministic grid only.

Allowed grid:

```text
seed_scope_id_grid =
  all allowed seed_scope_id values from Section 10.3
  after applying sample / stability gates

survival_checkpoint_grid = {T+3, T+5, T+10}

fallback_grain_grid = {
  same_day_family_count,
  seed_primary_family_id,
  seed_type,
  same_day_bundle_key,
  context_bucket_id
}

probability_gate_threshold_grid = {
  -0.50, -0.45, -0.40, -0.35, -0.30,
  -0.25, -0.20, -0.15, -0.10, -0.05,
   0.00,  0.05,  0.10,  0.15,  0.20
}
```

`same_day_bundle_key` and `context_bucket_id` may appear in `seed_scope_id_grid` or `fallback_grain_grid` only when Section 14 marks the bucket `sufficient_and_stable`. `fresh_evidence_status` must not appear in any train-selection grid.

Degenerate probability gates are forbidden. A candidate row must be excluded before ranking if, within the selected seed scope and selected survival checkpoint on train, the selected `fallback_grain` produces fewer than two distinct `episode_probability_bucket_key` values before thresholding.

Grid multiplicity limits:

```text
max_train_grid_total_candidate_count = 50000
max_train_eligible_candidate_count_after_gate = 200
```

If the generated grid exceeds `max_train_grid_total_candidate_count`, runner must fail closed with `invalid_requirement_violation`. If rows after denominator / stability / non-degenerate filtering exceed `max_train_eligible_candidate_count_after_gate`, no candidate may be selected and final decision must be `blocked_grid_multiplicity_excessive`.

Default train selection metric:

```text
selection_metric =
  train_prob_edge_vs_baseline_3
```

Candidate rows are eligible for train selection only if:

```text
train_candidate_split_pass = true
train_denominator_gate_pass = true
r03a_gate_status = sufficient_and_stable
```

Tie-breaker order is fixed:

```text
1. higher train_prob_edge_vs_baseline_3
2. lower train_P_bad_upper
3. higher train_P_good_lower
4. lower train_drawdown_severity_120d_p90
5. higher train_upside_capture_ratio_vs_baseline3
6. higher train_label_denominator
7. survival_checkpoint order: T+10, then T+5, then T+3
8. seed_scope_id lexicographic ascending
9. fallback_grain order:
   same_day_family_count,
   seed_primary_family_id,
   seed_type,
   same_day_bundle_key,
   context_bucket_id
10. lower probability_gate_threshold
```

Exactly one eligible row may be selected. If no row is eligible, no candidate may be selected and final decision must be `blocked_no_stable_candidate_bucket`.

Default pass thresholds:

```text
min_abs_bad_upper_improvement_vs_baseline3 = 0.02
max_abs_good_lower_loss_vs_baseline3 = 0.03
min_upside_capture_ratio_vs_baseline3 = 0.90
max_abs_drawdown_severity_worsening_vs_baseline3 = 0.005
```

All thresholds must be fixed in train config before validation / robustness readout.

Define:

```text
drawdown_loss_120d =
  abs(min(max_drawdown_120d, 0))

drawdown_severity_120d_p90 =
  quantile(drawdown_loss_120d, 0.90)

upside_capture_ratio_vs_baseline3 =
  candidate.max_gain_120d_p75
  / max(baseline_3_same_scope.max_gain_120d_p75, epsilon)
```

Raw `max_drawdown_120d_p90` is not a tail-risk metric because `max_drawdown_120d` is negative. It may be reported descriptively, but pass/fail must use `drawdown_severity_120d_p90`.

Use `epsilon = 1e-12` only to avoid division by zero. If baseline upside is non-positive, `upside_capture_ratio_vs_baseline3` must be marked `NA` and the pass component must be `blocked_nonpositive_baseline_upside`.

Candidate passes a split only if all are true:

```text
split_specific_N_min =
  N_min_train for train
  N_min_validation for validation
  N_min_robustness for robustness

candidate_label_denominator_count >= split_specific_N_min
baseline_3_same_scope_label_denominator_count >= split_specific_N_min

candidate_P_bad_upper
  <= baseline_3_same_scope_P_bad_upper
     - min_abs_bad_upper_improvement_vs_baseline3

candidate_P_good_lower
  >= baseline_3_same_scope_P_good_lower
     - max_abs_good_lower_loss_vs_baseline3

upside_capture_ratio_vs_baseline3
  >= min_upside_capture_ratio_vs_baseline3

candidate_drawdown_severity_120d_p90
  <= baseline_3_same_scope_drawdown_severity_120d_p90
     + max_abs_drawdown_severity_worsening_vs_baseline3
```

Final candidate pass requires both:

```text
validation_split_pass = true
robustness_split_pass = true
```

If train passes but either validation or robustness fails, final decision must be:

```text
failed_validation_or_robustness
```

If candidate does not improve `P_bad_upper` versus `baseline_3_same_scope` but `baseline_3` itself improves versus T0 same-grain prior, final decision should be:

```text
r03a_survival_step_baseline_sufficient_no_incremental_posterior_edge
```

## 11. Survival Checkpoint Contract

R03a 必须在 episode-first-trigger grain 上生成 survival lift 表。

Required survival lift grouping:

```text
survival_lift_grain in {global, by_seed_primary_family_id}
```

Required checkpoints：

```text
T+3
T+5
T+10
```

Survival definition：

```text
entry valid
AND no observable -5% breach before or at checkpoint
AND path not censored before checkpoint
```

Required outputs per checkpoint：

```text
pre_checkpoint_episode_count
survivor_episode_count
non_survivor_episode_count
survival_lift_grain
seed_primary_family_id_or_all
survivor_rate
survivor_label_denominator_count
survivor_P_good
survivor_P_bad
survivor_P_neutral
survivor_P_good_lower
survivor_P_good_upper
survivor_P_bad_lower
survivor_P_bad_upper
survivor_credible_interval_width_good
survivor_credible_interval_width_bad
non_survivor_label_denominator_count
non_survivor_P_good
non_survivor_P_bad
non_survivor_P_neutral
non_survivor_P_good_lower
non_survivor_P_good_upper
non_survivor_P_bad_lower
non_survivor_P_bad_upper
non_survivor_credible_interval_width_good
non_survivor_credible_interval_width_bad
survival_lift_good_vs_t0_same_grain
survival_lift_bad_vs_t0_same_grain
split_stability_status
```

This table is the authority for deciding whether survival checkpoint improvement is real enough to test. R02.1 `r02_1_survival_checkpoint_prior.csv` is an upstream input, but not a substitute for same-grain R03a recomputation.

## 12. Baselines And Candidate

R03a must compare exactly these baselines.

Because EV_R is blocked, exposure labels must not change path probabilities, drawdown metrics, return metrics, or pass/fail results. `baseline_1_t0_full_entry` and `baseline_2_t0_probe_only` use the same T0 entry population and therefore are expected to have identical path metrics. Their role is to preserve the scenario boundary and prevent the report from implying validated sizing. They are not allowed to decide candidate pass/fail.

Validator must fail if `baseline_1_t0_full_entry` and `baseline_2_t0_probe_only` have different path metrics beyond numerical tolerance, except for fields explicitly named as exposure labels or scenario labels.

Only `baseline_3_same_scope` is the mandatory candidate control.

### 12.1 Baseline 1: T0 Full Entry Scenario

```text
baseline_id = baseline_1_t0_full_entry
entry = T0 next-open
exposure_schedule_label = full_1r_at_t0
```

This is a counterfactual scenario for path-quality comparison only. It is not validated 1R sizing.

### 12.2 Baseline 2: T0 Probe Only

```text
baseline_id = baseline_2_t0_probe_only
entry = T0 next-open
exposure_schedule_label = fixed_probe_only
default_probe_label = scenario_probe_label
no_step_up
```

`scenario_probe_label` must match the probe label used by candidate / baseline_3 in the same comparison scenario. If no scenario probe is selected, the default report-only label is `0.25R`. It must be reported as `proxy_risk_label`, not as validated position size.

### 12.3 Baseline 3: T0 Probe + Survival Step-Up

```text
baseline_id = baseline_3_probe_survival_step_up
entry = T0 next-open
initial_exposure_schedule_label = fixed_probe
step_up_authority = survival_checkpoint_only
allowed_checkpoint_grid = {T+3, T+5, T+10}
fresh_evidence_ignored_for_gate = true
bundle_context_ignored_for_gate = true
```

This is the strongest mandatory control. R03a candidate must beat baseline_3, not just baseline_1 or baseline_2.

For candidate comparison, `baseline_3` must be recomputed in the same candidate scope as defined in Section 10.3. A global `baseline_3` row may be reported, but it must not be used for pass/fail unless the candidate scope is also global.

### 12.4 Candidate: Train-Frozen Probability Survival Step

```text
candidate_id = candidate_probability_survival_step
entry = T0 next-open
initial_exposure_schedule_label = fixed_probe
step_up_authority = train_frozen_survival_checkpoint + probability_only_gate
allowed_checkpoint_grid = {T+3, T+5, T+10}
allowed_primary_gates = {
  seed_primary_family_id,
  seed_type,
  survival_checkpoint_state,
  probability_only_score
}
```

Forbidden candidate gates:

```text
fresh_evidence_status
same_day_bundle_key, unless r03a_gate_status = sufficient_and_stable and used only as secondary fallback
context_bucket_id, unless r03a_gate_status = sufficient_and_stable and used only as secondary fallback
EV_R_diagnostic
EV_R_lower
winner_h120 alone
validation-tuned threshold
```

For `seed_primary_family_id`, the only allowed multi-family value is the literal `multi_family_bundle`. The candidate must not select a component family inside a multi-family same-day bundle.

## 13. Train / Validation / Robustness Rules

R03a must use the existing split labels from upstream artifacts.

Train split may choose:

```text
survival_checkpoint
probability gate threshold from the fixed grid in Section 10.4
fallback grain
fixed exposure schedule label from allowed grid
seed_scope_id from allowed enum in Section 10.3
```

Sample sufficiency thresholds are not train-selectable. The runner must read fixed `N_min_train`, `N_min_validation`, and `N_min_robustness` values from config before train grid construction, and record them in the manifest.

Validation / robustness may only evaluate.

Forbidden:

```text
validation threshold tuning
validation bucket merge
family replacement after validation
post-hoc checkpoint switch
fresh evidence promotion after seeing validation
EV_R threshold insertion
```

If candidate wins train but fails validation or robustness, final decision must not be `passed`.

## 14. Sample And Stability Gates

Default minimum denominator:

```text
N_min_train = 300
N_min_validation = 100
N_min_robustness = 100
```

These thresholds are fixed denominator gates. They must not be optimized, bucket-specific, or changed after seeing train / validation / robustness outcomes.

Allowed status:

```text
sufficient_and_stable
thin_report_only
too_sparse_use_fallback
unstable_do_not_freeze
missing_split
unusable
```

R03a must normalize upstream R02.1 statuses before candidate selection.

Required normalization:

| upstream `sample_sufficiency_status` | upstream `stability_status` | R03a `r03a_gate_status` |
|:--|:--|:--|
| `sufficient` | `stable_enough_for_requirement_input` | `sufficient_and_stable` |
| `sufficient` | `unstable_do_not_freeze` | `unstable_do_not_freeze` |
| `sufficient` | `insufficient_sample` | `too_sparse_use_fallback` |
| `sufficient` | `missing_split` | `missing_split` |
| `thin_bucket_report_only` | any | `thin_report_only` |
| `too_sparse_use_fallback` | any | `too_sparse_use_fallback` |
| `unusable` | any | `unusable` |

The implementation may add a derived `r03a_stability_status = stable_enough_for_candidate` only if it is computed from a documented stricter rule and recorded in the manifest. It must not replace or overwrite the upstream `stability_status`.

Primary candidate gate may use only rows with:

```text
r03a_gate_status = sufficient_and_stable
upstream_stability_status = stable_enough_for_requirement_input
if r03a_stability_status exists:
  r03a_stability_status = stable_enough_for_candidate
```

Train selection must additionally satisfy:

```text
train_candidate_label_denominator_count >= N_min_train
train_baseline_3_same_scope_label_denominator_count >= N_min_train
```

Validation / robustness pass flags must separately check:

```text
validation_candidate_label_denominator_count >= N_min_validation
validation_baseline_3_same_scope_label_denominator_count >= N_min_validation

robustness_candidate_label_denominator_count >= N_min_robustness
robustness_baseline_3_same_scope_label_denominator_count >= N_min_robustness
```

If any denominator gate fails, the corresponding split pass must be false and `comparison_vs_baseline_3_status` must record:

```text
blocked_insufficient_denominator
```

If no candidate row satisfies this condition, runner must still output baseline tables and final report, but final decision must be:

```text
blocked_no_stable_candidate_bucket
```

## 15. Fixed Exposure Schedule Labels

Because EV_R is blocked, R03a exposure values are labels only.

Allowed grid:

```text
probe_label in {0.15R, 0.20R, 0.25R}
survival_step_label in {0.40R, 0.50R}
confirmation_label = not_used_in_r03a
final_1r_label = not_used_in_r03a
```

R03a must not select a true optimal size. It may only report which fixed label was used for scenario comparison.

Every output table containing an exposure label must include:

```text
risk_budget_status = probability_only_ev_r_blocked
exposure_label_is_validated_size = false
```

## 16. Fresh Evidence Boundary

R03a must preserve fresh evidence as descriptive-only.

Required descriptive fields:

```text
fresh_evidence_status
fresh_offset_bucket
fresh_family_id_first
fresh_before_observable_failure_rate
fresh_without_prior_observable_failure_rate
same_survival_checkpoint_conditioning_status
```

Forbidden:

```text
fresh_evidence_status as candidate gate
fresh offset as stage cap release condition
fresh/no-fresh comparison without same survival checkpoint conditioning
first-fresh offset distribution used to reject T+11..T+30 information
```

If the report discusses fresh evidence, it must say:

```text
fresh evidence is descriptive in R03a and requires separate sequence / hazard diagnostic before gate use
```

## 17. Same-Day Bundle And Context Boundary

Same-day bundle and context bucket are descriptive by default.

They may enter candidate evaluation only if all are true:

```text
train sample >= N_min_train
validation sample >= N_min_validation
robustness sample >= N_min_robustness
r03a_gate_status = sufficient_and_stable
bucket was selected in train before validation readout
```

Even then, they may only refine fallback selection; they may not create multiple same-day risk units.

Every bundle/context output must include:

```text
primary_gate_allowed
fallback_level
sample_sufficiency_status
split_stability_status
r03a_gate_status
```

## 18. Required Output Tables

### 18.1 Input Readiness Audit

Output:

```text
reports/r03a_input_readiness_audit.csv
```

Required fields:

```text
input_name
input_path
required
exists
hash_or_mtime
validation_status
readiness_status
blocker_status
```

### 18.2 Episode Panel

Output:

```text
cache/r03a_episode_first_trigger_panel.parquet
```

This is a candidate-augmented episode panel produced after train selection. The upstream raw episode construction rule must be verified by hash, not by prose equivalence.

Required fields:

```text
seed_episode_id
instrument_id
seed_trade_date
seed_entry_date
seed_entry_price
seed_same_day_bundle_key
seed_same_day_family_count
seed_family_set
seed_type
seed_primary_family_id
split
year
label
censored_or_invalid_reason
good_path_flag
bad_path_flag
neutral_path_flag
first_minus5_offset
hit_plus10_before_minus5
path_quality_flag
max_drawdown_120d
max_gain_120d
close_return_t20
close_return_t60
close_return_t120
train_inner_cv_fold_id
selected_candidate_id
candidate_scope_id
baseline_3_scope_id
episode_in_selected_seed_scope
episode_survived_selected_checkpoint
episode_probability_bucket_key
episode_probability_score
candidate_episode_included
baseline_3_same_scope_episode_included
```

### 18.3 T0 Episode Prior

Output:

```text
reports/r03a_t0_episode_prior.csv
```

Required grouping:

```text
all
split
year
seed_primary_family_id
seed_same_day_family_count
```

Each grouping row must include the full Section 10 probability schema:

```text
label_denominator_count
good_count
bad_count
neutral_count
P_good
P_bad
P_neutral
P_good_lower
P_good_upper
P_bad_lower
P_bad_upper
credible_interval_width_good
credible_interval_width_bad
sample_sufficiency_status
split_stability_status
prior_source
fallback_level
```

### 18.4 Same-Grain Survival Lift

Output:

```text
reports/r03a_survival_same_grain_lift.csv
```

Required checkpoint rows:

```text
T+3
T+5
T+10
```

This is the headline diagnostic table for survival-step feasibility.

Required fields are the Section 11 checkpoint fields, including complete survivor and non-survivor probability CI fields.

### 18.5 Candidate Grid Train Selection

Output:

```text
reports/r03a_candidate_grid_train_selection.csv
```

Required fields:

```text
candidate_id
candidate_scope_id
baseline_3_scope_id
seed_scope_id
seed_scope_type
survival_checkpoint
probe_label
survival_step_label
probability_gate_threshold
fallback_grain
probability_gate_threshold_grid_id
episode_probability_score_formula
train_scoring_mode
train_inner_cv_fold_count
train_grid_total_candidate_count
train_eligible_candidate_count_after_gate
train_grid_multiplicity_status
train_distinct_probability_bucket_count
degenerate_probability_gate_status
credible_interval_level
upstream_sample_sufficiency_status
upstream_stability_status
r03a_stability_status
r03a_gate_status
train_label_denominator
train_baseline_3_same_scope_label_denominator
train_denominator_gate_pass
train_P_good
train_P_bad
train_P_neutral
train_P_good_lower
train_P_good_upper
train_P_bad_lower
train_P_bad_upper
train_credible_interval_width_good
train_credible_interval_width_bad
train_prob_feasibility_score
train_prob_edge_vs_baseline_3
train_baseline_3_same_scope_P_good
train_baseline_3_same_scope_P_bad
train_baseline_3_same_scope_P_neutral
train_baseline_3_same_scope_P_good_lower
train_baseline_3_same_scope_P_good_upper
train_baseline_3_same_scope_P_bad_lower
train_baseline_3_same_scope_P_bad_upper
train_baseline_3_same_scope_credible_interval_width_good
train_baseline_3_same_scope_credible_interval_width_bad
train_upside_capture_ratio_vs_baseline3
train_drawdown_severity_120d_p90
train_baseline_3_same_scope_drawdown_severity_120d_p90
train_candidate_split_pass
selection_metric
selection_metric_value
tie_breaker_tuple
min_abs_bad_upper_improvement_vs_baseline3
max_abs_good_lower_loss_vs_baseline3
min_upside_capture_ratio_vs_baseline3
max_abs_drawdown_severity_worsening_vs_baseline3
selection_rank
selected_in_train
selection_reason
```

Only one row may have:

```text
selected_in_train = true
```

If no candidate qualifies, all rows must be `selected_in_train = false`.

### 18.6 Baseline Comparison

Output:

```text
reports/r03a_baseline_comparison.csv
```

Required rows:

```text
baseline_1_t0_full_entry
baseline_2_t0_probe_only
baseline_3_probe_survival_step_up
candidate_probability_survival_step
```

Required fields:

```text
scenario_id
comparison_role
candidate_scope_id
baseline_3_scope_id
split
year
selected_checkpoint
proxy_exposure_schedule_label
risk_budget_status
exposure_label_is_validated_size
path_metric_denominator_policy
seed_episode_count
censored_or_invalid_count
censored_or_invalid_rate
label_denominator_count
P_good
P_bad
P_neutral
P_good_lower
P_good_upper
P_bad_lower
P_bad_upper
credible_interval_width_good
credible_interval_width_bad
max_drawdown_120d_p50
max_drawdown_120d_p10
max_drawdown_120d_p75
max_drawdown_120d_p90
drawdown_loss_120d_p90
drawdown_severity_120d_p90
max_gain_120d_p50
max_gain_120d_p75
max_gain_120d_p90
close_return_t20_p50
close_return_t60_p50
close_return_t120_p50
upside_capture_proxy
upside_capture_ratio_vs_baseline3
early_failure_rate
candidate_split_pass
comparison_vs_baseline_3_status
```

No EV_R or expected R field is allowed in this table.

Allowed `path_metric_denominator_policy` values:

```text
episode_first_trigger_label_denominator
episode_first_trigger_survivor_label_denominator
episode_first_trigger_candidate_included_label_denominator
```

### 18.7 Validation / Robustness Read-Only Audit

Output:

```text
reports/r03a_validation_robustness_readonly.csv
```

Required fields:

```text
candidate_id
frozen_from_train
evaluation_split
candidate_scope_id
baseline_3_scope_id
threshold_changed_after_train
checkpoint_changed_after_train
bucket_changed_after_train
validation_seed_episode_count
validation_censored_or_invalid_count
validation_censored_or_invalid_rate
validation_label_denominator
validation_baseline_3_same_scope_label_denominator
validation_denominator_gate_pass
validation_P_good
validation_P_bad
validation_P_neutral
validation_P_good_lower
validation_P_good_upper
validation_P_bad_lower
validation_P_bad_upper
validation_credible_interval_width_good
validation_credible_interval_width_bad
validation_baseline_3_same_scope_P_good
validation_baseline_3_same_scope_P_bad
validation_baseline_3_same_scope_P_neutral
validation_baseline_3_same_scope_P_good_lower
validation_baseline_3_same_scope_P_good_upper
validation_baseline_3_same_scope_P_bad_lower
validation_baseline_3_same_scope_P_bad_upper
validation_baseline_3_same_scope_credible_interval_width_good
validation_baseline_3_same_scope_credible_interval_width_bad
validation_prob_edge_vs_baseline_3
validation_upside_capture_ratio_vs_baseline3
validation_drawdown_severity_120d_p90
validation_baseline_3_same_scope_drawdown_severity_120d_p90
validation_candidate_pass
robustness_seed_episode_count
robustness_censored_or_invalid_count
robustness_censored_or_invalid_rate
robustness_label_denominator
robustness_baseline_3_same_scope_label_denominator
robustness_denominator_gate_pass
robustness_P_good
robustness_P_bad
robustness_P_neutral
robustness_P_good_lower
robustness_P_good_upper
robustness_P_bad_lower
robustness_P_bad_upper
robustness_credible_interval_width_good
robustness_credible_interval_width_bad
robustness_baseline_3_same_scope_P_good
robustness_baseline_3_same_scope_P_bad
robustness_baseline_3_same_scope_P_neutral
robustness_baseline_3_same_scope_P_good_lower
robustness_baseline_3_same_scope_P_good_upper
robustness_baseline_3_same_scope_P_bad_lower
robustness_baseline_3_same_scope_P_bad_upper
robustness_baseline_3_same_scope_credible_interval_width_good
robustness_baseline_3_same_scope_credible_interval_width_bad
robustness_prob_edge_vs_baseline_3
robustness_upside_capture_ratio_vs_baseline3
robustness_drawdown_severity_120d_p90
robustness_baseline_3_same_scope_drawdown_severity_120d_p90
robustness_candidate_pass
readonly_status
```

All change flags must be false.

### 18.8 Descriptive Bundle / Context Prior

Output:

```text
reports/r03a_descriptive_bundle_context_prior.csv
```

This table may reuse R02.1 rows but must add R03a-specific gate flags:

```text
primary_gate_allowed
reason_if_not_allowed
fallback_level
upstream_sample_sufficiency_status
upstream_stability_status
r03a_stability_status
r03a_gate_status
used_by_candidate
```

If reused upstream rows contain probability estimates, those estimates must be normalized to the full Section 10 probability schema before this table is written.

For R03a v1, default `used_by_candidate` is false.

### 18.9 Fresh Evidence Descriptive Audit

Output:

```text
reports/r03a_fresh_evidence_descriptive_audit.csv
```

Required fields:

```text
fresh_evidence_status
fresh_offset_bucket
survival_checkpoint_conditioning
label_denominator_count
P_good
P_bad
P_neutral
P_good_lower
P_good_upper
P_bad_lower
P_bad_upper
credible_interval_width_good
credible_interval_width_bad
fresh_before_observable_failure_rate
fresh_without_prior_observable_failure_rate
split_stability_status
gate_use_allowed
reason_if_not_allowed
```

`gate_use_allowed` must be false for R03a v1.

### 18.10 Null Result Audit

Output:

```text
reports/r03a_null_result_audit.csv
```

Required fields:

```text
null_condition
observed_status
triggered
evidence_table
evidence_row_id
required_conclusion_if_triggered
```

Required null conditions:

```text
candidate_not_better_than_baseline_3_on_P_bad
candidate_loses_too_much_upside_capture_vs_baseline_3
candidate_only_wins_in_train
candidate_depends_on_sparse_bucket
candidate_depends_on_fresh_evidence_gate
candidate_requires_ev_r_sizing
baseline_1_2_path_metric_mismatch
candidate_compared_to_global_baseline3
multi_family_seed_component_selected_as_primary
upstream_enum_not_normalized
candidate_inclusion_formula_missing
credible_interval_level_not_fixed
drawdown_severity_uses_raw_p90_wrong_tail
denominator_gate_not_applied
candidate_train_scoring_used_in_sample_posterior
candidate_grid_multiplicity_excessive
candidate_eligibility_threshold_smaller_than_ci_halfwidth
candidate_degenerate_probability_gate
episode_construction_rule_hash_mismatch
```

## 19. Final Report

Output:

```text
reports/r03a_probability_survival_step_feasibility_report.md
```

The report must be in Chinese and must include:

1. 为什么 R03a 是 probability-only feasibility，不是 EV_R sizing；
2. R02.1 blocker summary: EV_R missing, global denominator missing, split stability partial；
3. same-grain T0 prior vs T+3 / T+5 / T+10 survivor posterior；
4. baseline_1 / baseline_2 / baseline_3 / candidate comparison；
5. why baseline_1 and baseline_2 are expected to have identical path metrics under EV_R-blocked label-only exposure；
6. the exact candidate pass/fail thresholds and whether candidate beats `baseline_3_same_scope` in validation / robustness；
7. the episode inclusion formula, selected seed scope, probability bucket mapping, and denominator-gate pass/fail；
8. train scoring mode, inner-CV fold count, grid multiplicity count, and whether the selected candidate avoided in-sample posterior scoring；
9. why drawdown pass/fail uses `drawdown_severity_120d_p90` rather than raw `max_drawdown_120d_p90`；
10. whether the result supports staged posterior edge, survival-only structure, or null result；
11. why fresh evidence remains descriptive only, including why first-fresh offset distribution is not a valid gate for rejecting T+11..T+30 information；
12. why same-day bundle/context remain descriptive or fallback-only；
13. concrete next action: stop, run R03b after EV_R materialization, or run fresh-sequence diagnostic；
14. final decision using only allowed enum.

Allowed final decision:

```text
r03a_probability_feasibility_passed
r03a_survival_step_baseline_sufficient_no_incremental_posterior_edge
blocked_no_stable_candidate_bucket
blocked_grid_multiplicity_excessive
blocked_missing_required_input
failed_validation_or_robustness
invalid_requirement_violation
```

Forbidden report language:

```text
production-ready
buy signal
sell signal
validated 1R allocation
expected R positive
EV_R passed
fresh evidence gate validated
portfolio-ready
```

## 20. Manifest

Output:

```text
manifests/r03a_probability_survival_step_feasibility_manifest.json
```

Required manifest fields:

```text
requirement_id
short_name
generated_at
input_artifact_hashes
upstream_validation_status
frozen_family_universe
episode_grain
label_priority_order
survival_checkpoints
alpha_source
credible_interval_level
probability_score_formula
train_scoring_mode
train_inner_cv_fold_count
train_inner_cv_assignment_hash
fallback_grain_order
allowed_seed_scope_ids
probability_gate_threshold_grid
fixed_sample_denominator_thresholds
train_grid_total_candidate_count
train_eligible_candidate_count_after_gate
max_train_grid_total_candidate_count
max_train_eligible_candidate_count_after_gate
grid_multiplicity_status
degenerate_probability_gate_exclusion_status
train_selection_metric
train_selection_tie_breaker
candidate_episode_inclusion_formula
status_normalization_mapping
train_only_selection_fields
upstream_r02_1_episode_construction_rule_hash
r03a_episode_construction_rule_hash
path_metric_denominator_policy_enum
selected_candidate_id
selected_candidate_scope_id
r03a_pass_fail_thresholds
risk_budget_status
background_denominator_status
ev_r_status
fresh_evidence_gate_allowed
bundle_context_primary_gate_allowed
validation_readonly_status
baseline_1_2_path_metric_equivalence_status
baseline_3_same_scope_comparison_status
final_decision
```

## 21. Validator Fail-Closed Checks

Validator must fail if:

- any required input artifact is missing;
- upstream R02.1 validation did not pass;
- frozen 7-family universe differs from R02.1 / R02 path-analysis;
- analysis grain is not episode-first-trigger for headline comparisons;
- `upstream_r02_1_episode_construction_rule_hash` differs from `r03a_episode_construction_rule_hash`;
- T0 prior and survival posterior are compared across different grains;
- label priority is not bad before good;
- `alpha_source` is not exactly `Jeffreys_prior` or the forbidden `train_empirical_fallback_prior` appears in config / manifest;
- `P_good + P_bad + P_neutral` differs from 1 beyond tolerance;
- credible interval level is not exactly `0.90`, or `P_good_lower` / `P_bad_upper` are not the q05 / q95 posterior marginal quantiles;
- `credible_interval_width_good` or `credible_interval_width_bad` is missing or inconsistent with q95 minus q05;
- any probability-bearing output table omits `P_good`, `P_bad`, `P_neutral`, `P_good_lower`, `P_good_upper`, `P_bad_lower`, `P_bad_upper`, `credible_interval_width_good`, or `credible_interval_width_bad`;
- `episode_probability_score` is not exactly `P_good_lower - P_bad_upper`;
- selected `probability_gate_threshold` is not in the fixed Section 10.4 grid;
- sample sufficiency thresholds are selected, tuned, or changed after initial config load instead of using fixed `N_min_train`, `N_min_validation`, and `N_min_robustness`;
- train candidate scoring uses an in-sample posterior table instead of `train_inner_cv_out_of_fold`;
- `train_inner_cv_fold_count`, fold assignment hash, or train scoring mode is missing from the manifest;
- train grid total candidate count or eligible candidate count is missing from outputs / manifest;
- `train_grid_total_candidate_count > max_train_grid_total_candidate_count`;
- `train_eligible_candidate_count_after_gate > max_train_eligible_candidate_count_after_gate` but a candidate is selected;
- a candidate row with fewer than two distinct train `episode_probability_bucket_key` values is ranked or selected;
- selected train candidate does not match the Section 10.4 selection metric and tie-breaker order;
- selection metric calculation does not match the Section 10.4 formula;
- train creates a family-group scope outside the allowed `seed_scope_id` enum;
- validation / robustness changes train-frozen threshold, checkpoint, fallback grain, or candidate;
- candidate uses fresh evidence as primary gate;
- candidate uses EV_R / expected R / final 1R sizing;
- candidate episode inclusion omits any required component of `candidate_episode_included`;
- `baseline_3_same_scope_episode_included` applies the candidate probability gate;
- candidate pass/fail uses a global baseline_3 when candidate scope is not global;
- candidate pass/fail omits any threshold from Section 10.3;
- candidate pass/fail uses raw `max_drawdown_120d_p90` instead of `drawdown_severity_120d_p90`;
- candidate or baseline_3 same-scope denominator is below the configured split-specific `N_min` but the split pass flag is true;
- `path_metric_denominator_policy` is outside the allowed enum;
- seed episode, censored / invalid, and label denominator counts are missing from baseline comparison or validation / robustness outputs;
- candidate passes without both validation and robustness passing Section 10.3 conditions;
- same-day multiple family triggers create multiple same-day risk units;
- a multi-family same-day seed assigns one component family as `seed_primary_family_id` instead of `multi_family_bundle`;
- upstream R02.1 sample / stability statuses are not normalized into `r03a_gate_status`;
- `baseline_1_t0_full_entry` and `baseline_2_t0_probe_only` have different path metrics beyond tolerance, except exposure / scenario label fields;
- `baseline_3` is missing;
- `baseline_3` is not used as the main control for candidate comparison;
- output report describes the result as a trading strategy or validated risk allocation;
- manifest omits `risk_budget_status = probability_only_ev_r_blocked`.

## 22. Implementation Readiness Checklist

- [ ] Required R02.1 inputs exist and validation passed.
- [ ] R03a output root / config / runner / validator paths are fixed.
- [ ] Frozen 7-family universe is inherited without new formulas.
- [ ] Episode-first-trigger panel is the headline denominator.
- [ ] T0 prior and T+3 / T+5 / T+10 survivor posterior are recomputed on the same grain.
- [ ] Baseline_3 is mandatory and treated as the strongest control.
- [ ] Baseline_1 and baseline_2 are validated as path-metric-equivalent label-only scenarios.
- [ ] Candidate is compared against baseline_3 in the same candidate scope.
- [ ] Candidate episode inclusion formula is materialized as row-level flags.
- [ ] Candidate pass/fail thresholds are fixed before validation / robustness readout.
- [ ] Probability gate threshold grid, train selection metric, and tie-breaker are fixed and recorded.
- [ ] Episode probability score is fixed to `P_good_lower - P_bad_upper`.
- [ ] Train candidate scoring uses inner-CV out-of-fold posterior tables, not in-sample posterior scoring.
- [ ] `train_empirical_fallback_prior` is forbidden in v1.
- [ ] Grid multiplicity counts and caps are recorded, and excessive eligible grids block selection.
- [ ] Degenerate probability gates with fewer than two train buckets are excluded before ranking.
- [ ] Credible interval level is fixed to 90% and recorded in the manifest.
- [ ] All probability-bearing output tables include the full Section 10 probability schema.
- [ ] Drawdown severity uses row-level drawdown loss p90, not raw max-drawdown p90.
- [ ] Train / validation / robustness denominator gates are applied to both candidate and baseline_3 same-scope rows.
- [ ] Sample sufficiency thresholds are fixed before train selection and recorded in the manifest.
- [ ] Episode construction rule hash is matched against the upstream R02.1 manifest.
- [ ] Seed episode count, censored / invalid count, and label denominator count are all reported.
- [ ] Multi-family same-day seeds use `seed_primary_family_id = multi_family_bundle`.
- [ ] R02.1 sample / stability statuses are normalized into `r03a_gate_status`.
- [ ] Candidate selection is train-only.
- [ ] Validation / robustness are read-only.
- [ ] Fresh evidence is descriptive-only.
- [ ] Bundle / context buckets are descriptive or fallback-only unless stable and sufficient.
- [ ] EV_R and final 1R allocation are explicitly blocked.
- [ ] Null-result contingency is machine-readable.

## 23. Non-Goals

This requirement intentionally does not answer:

```text
最终应该释放多少 R？
T+10 后是否应该加到 0.60R 或 1.00R？
同 1R 预算下 expected R 是否为正？
fresh evidence 是否可以作为加仓 gate？
哪个 bundle 是最终 production entry？
```

Those questions belong to:

```text
R03b EV_R-materialized risk-budget experiment
or
fresh-sequence / hazard diagnostic
```

depending on which blocker is addressed first.

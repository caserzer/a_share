# 12 State-Change Event Backbone Rebuild Research Plan

## 0. Renamed Experiment

Proposed experiment name:

```text
12_state_change_event_backbone_rebuild_v0
```

Legacy directory retained for now:

```text
12_multi_k_winner_failure_path_morphology_research_v0
```

The physical directory is intentionally not renamed in this edit, because the current diagnostics under `outputs/diagnostics/` already point to this path. A later path rename should be done as a separate mechanical change after this research plan is accepted.

### 0.1 What Changed

The prior name, `Multi-K Winner / Failure Path Morphology`, assumed the next research step was to separate winner and failure paths inside the current 08/10/11 candidate chain.

That assumption is now too late in the pipeline.

The updated interpretation is:

```text
R-core is a high-recall momentum / leadership stress pool,
not a clean event backbone.

Before winner/failure morphology, 12 must first ask whether
the event backbone itself is valid.
```

So experiment 12 is reframed from:

```text
Can multi-K observed path separate winners from failures?
```

to:

```text
Can we replace or demote R-core with a cleaner state-change event backbone,
then only run multi-K morphology on the accepted backbone?
```

### 0.2 Current Research Position

12 is not:

- a continuation of 11C K3 hard-rule tuning;
- a direct winner/failure classifier on R-core;
- a policy replay;
- a new buy/sell rule;
- a probability model requirement.

12 is:

```text
an event-backbone validity and replacement study.
```

The first deliverable should be a research contract that decides whether R-core can remain a backbone, must be demoted to a feature/source pool, or should be replaced by state-change event families.

---

## 1. Why the Rename Is Necessary

### 1.1 R-core Is Not a CUSUM / State-Change Backbone

The 08 R-core scope is a union of R1/R2/R6/R7/R8 event-regime-gated variants:

```text
R1 relative strength breakout
R2 near-high volume expansion
R6 market breadth thrust + stock leadership
R7 cross-sectional momentum rank jump
R8 persistent distance above EMA60
```

These are mainly momentum, leadership, breadth, rank, and high-position triggers.

They are not cumulative residual-change or CUSUM-style state-change triggers. The CUSUM-like families were in the T family, especially T1/T2/T6/T7, with T1/T2 blocked by PIT industry data and T6/T7 acting as fallback / transition diagnostics.

This matters because R-core can fire repeatedly after strength is already visible. That is useful for recall, but bad for event precision, first-trigger discipline, and episode timing.

### 1.2 The Empirical Evidence Says R-core Is a Recall Stress Pool

08 showed that risk_on R-core has strong episode / bridge coverage:

```text
risk_on R-core post-replay recall:
  train      98.2%
  robustness 94.5%

E1-missed captured by R-core:
  train      80 / 83
  robustness 84 / 92
```

But the same R-core population is too dense:

```text
08_R_core_event_regime_gated:
  events                 47,914
  density / inst-year    13.227
  p95 density            38.12
  rolling 10d duplicate  57.83%
  fast-fail 10d          24.20%
  false-repair 20d       31.11%
```

Experiment C made the interpretation explicit:

```text
Risk-on R-core has real bridge coverage,
but density, duplicate, fast-fail, and false-repair fail together.
```

Therefore the right conclusion is not:

```text
R-core has no signal.
```

It is:

```text
R-core has signal, but it is not a clean entry backbone.
```

### 1.3 09/10/11 Did Not Solve the Backbone Problem

09 proved that t0-visible features can sort some bad-side labels, but not enough to make the R-core pool tradable:

- 09B fast-fail-only models had AUC signal.
- In actual rejection buckets, OOS precision remained limited.
- 09C hybrid rejector failed winner retention and fast-fail attribution.
- The `break_swing_low_20` fast-fail label is a low-capacity structural stop filter, not a 20%-30% cost rejector.

10 improved the operating discipline but did not create a broad high-precision event pool:

- 10A `same_instrument_cooldown_10d` compressed R-core from 30,790 to 15,802 supported rows.
- 10B `keep_9400` is useful as a small fast-fail safety gate.
- 10C false-repair rejector had signal but failed winner-safe retention.

11 confirmed that the observed-state layer is diagnostic, not a finished solution:

- 11A1 found no accepted t0 proxy screen.
- 11A2 found K3/K5 path divergence, but this is readout-level evidence.
- 11C K3 wait-confirm reduced failure exposure but lost winner capture and remained negative after costs.

So the system has not yet solved the event-backbone question.

### 1.4 The 06 vs 11 Winner Population Mismatch Must Be Frozen First

The current diagnostics show that 06 and 11 are not the same winner population:

```text
06 risk_on episodes: 428
11A2 risk_on PIT-valid big-winner rows: 446
exact same date alignment: 0
06 risk_on episodes with any 11 row pre120-to-high: 120
06 risk_on episodes without 11 row pre120-to-high: 308
```

This means 11A2 strict PIT rows cannot be treated as the complete episode target. They are a candidate-chain / PIT subset readout, not a replacement for the 06 episode registry.

Experiment 12 must keep two targets separate:

```text
episode target:
  06 risk_on big-winner episodes = 428

strict PIT candidate/readout target:
  11A2 risk_on PIT-valid big-winner rows = 446
```

Any plan that mixes these two denominators will recreate the 06-08-11 drift.

---

## 2. Core Research Thesis

The new 12 thesis is:

```text
Do not optimize R-core first.
First rebuild the event backbone around observable state changes.
Then use R-core as a recall backstop, context feature, or stress benchmark.
Only after a cleaner backbone exists should multi-K winner/failure morphology be run.
```

This shifts the research order:

```text
old order:
  R-core / 11 candidate chain
    -> winner/failure morphology
    -> probability / policy

new order:
  winner registry reconciliation
    -> R-core demotion audit
    -> state-change backbone candidates
    -> episode precision / recall frontier
    -> optional filter layer
    -> optional multi-K morphology
```

---

## 3. Primary Research Questions

### 3.1 Backbone Question

```text
Can a state-change event family match enough of the 06 risk_on winner episode recall
while materially improving event precision, density, duplicate rate, and bad-side exposure
relative to raw R-core?
```

This is the primary question.

### 3.2 R-core Demotion Question

```text
Should R-core be demoted from backbone to one of:
  feature source,
  recall stress pool,
  candidate backstop,
  or diagnostic benchmark?
```

R-core can still be valuable. It just should not automatically define the event universe.

### 3.3 State-Change Candidate Question

```text
Which observable state-change families produce earlier, cleaner, less repeated triggers
than momentum-union R-core?
```

Candidate families must be t0-visible / PIT-safe and next-open executable.

### 3.4 Downstream Morphology Question

```text
If a cleaner backbone exists, does multi-K observed path add incremental separation
beyond the state-change event itself?
```

This is now downstream. It is not the first question in 12.

---

## 4. Denominator Discipline

### 4.1 Primary Episode Target

Primary episode target:

```text
06_topn_risk_on_big_winner_episodes_428
```

Use this for:

- episode-level recall;
- event-to-episode timing;
- before-low / low-to-high / after-high positioning;
- missed-episode diagnostics;
- first-trigger timing.

### 4.2 Strict PIT Candidate Readout

Strict PIT candidate readout:

```text
11A2 risk_on PIT-valid big-winner rows = 446
```

Use this for:

- PIT-executable candidate-chain diagnostics;
- compatibility with 11A1/11A2/11C;
- optional morphology readout after backbone acceptance.

Do not use the 446 rows as the full winner-episode target.

### 4.3 R-core Benchmark

R-core benchmark:

```text
08_R_core_event_regime_gated
```

Use this only as:

- high-recall stress pool;
- density / duplicate / bad-side benchmark;
- context feature source;
- backstop comparison.

Do not make R-core the default denominator for model training unless 12A1 explicitly proves it remains acceptable.

### 4.4 10A / 10B Benchmark

10A/10B benchmark:

```text
10A__same_instrument_cooldown_10d
10B keep_9400 fast-fail safety gate
```

Use these as:

- post-dedup operating baseline;
- small-capacity safety-filter benchmark;
- evidence that time de-dup and small fast-fail filtering help but do not solve backbone selection.

---

## 5. Candidate State-Change Backbones

### B1 Relative Residual CUSUM Break

Purpose:

```text
detect cumulative stock-specific strength changes
instead of repeated high-position momentum confirmations.
```

Candidate signals:

- stock vs market residual CUSUM;
- stock vs board residual CUSUM;
- board vs market CUSUM;
- 5d impulse after 20d residual accumulation;
- first positive residual break after prior compression.

Important distinction:

```text
relative return threshold is not enough;
the family should require accumulated residual change or regime break.
```

### B2 Compression to Directional Expansion

Purpose:

```text
capture a state transition from quiet / compressed path to directional expansion.
```

Candidate signals:

- entropy compression then positive expansion;
- ATR/range contraction then close-in-upper-range breakout;
- volatility burst after low realized range;
- volume / money confirmation on the expansion day;
- first expansion after a minimum quiet period.

### B3 Low-Reclaim / Repair Transition

Purpose:

```text
capture transition from damage to repair near the future episode base,
instead of chasing already obvious momentum.
```

Candidate signals:

- reclaim EMA20 / EMA60 after drawdown;
- reclaim prior local low / swing damage;
- VWAP or amount-weighted reclaim if available;
- relative reclaim vs board / market;
- first reclaim after a controlled damage window.

This is closest to the reverse-lifecycle logic and should be evaluated against 06 episode timing.

### B4 Breadth / Regime Context

Purpose:

```text
separate market backdrop from stock-specific event timing.
```

Use as context, not primary trigger:

- market breadth thrust;
- board breadth thrust;
- board-relative risk-on state;
- R6-style breadth leadership.

B4 can improve conditioning, but if it becomes the event trigger itself it may recreate R-core density.

### B5 First-Trigger Density Discipline

Every candidate backbone must define first-trigger logic:

- one event per instrument per state-change episode unless a reset condition is met;
- explicit cooldown only after state-change confirmation;
- separate same-day cross-family collision from repeated same-instrument triggers;
- event density reported before any model training.

This is a backbone requirement, not a post-hoc cleanup.

---

## 6. Phase Plan

### Phase 12A0: Winner Registry and Lineage Audit

Goal:

```text
freeze all target populations before generating any new event family.
```

Tasks:

- Reconcile 06 risk_on 428 episode registry.
- Reconcile 11A2 446 PIT-valid winner rows.
- Explain instrument/date lineage for rows that do not align.
- Freeze episode timing fields:
  - episode_low_date;
  - episode_high_date;
  - first_50pct_date if available;
  - low-to-high window;
  - pre120-to-high window.
- Freeze candidate-chain fields:
  - event_t0_date;
  - event_t0_pos;
  - next-open execution anchor;
  - PIT validity;
  - qfq path availability.
- Output a target registry contract.

Required outputs:

- `winner_registry_lineage_summary.csv`
- `episode_target_registry_06_risk_on_428.csv`
- `pit_candidate_winner_registry_11a2_446.csv`
- `population_bridge_audit.csv`
- `12A0_scope_decision_report.md`

Gate:

```text
No downstream modeling if 06 episode target and 11 PIT readout are not clearly separated.
```

Failure status:

```text
12A0_population_lineage_incomplete
```

### Phase 12A1: R-core Backbone Demotion Audit

Goal:

```text
decide whether R-core is a backbone, a feature source, or only a recall benchmark.
```

Tasks:

- Recompute R-core event-to-episode alignment against the 06 risk_on 428 episodes.
- Report event precision using multiple windows:
  - pre120-to-high;
  - low-to-high;
  - low-to-first-50pct;
  - after-high false timing.
- Compare:
  - raw R-core;
  - 10A same-instrument cooldown;
  - 10B fast-fail safety gate;
  - R6-only;
  - T6/T7 CUSUM fallback if available.
- Report density, duplicate, fast-fail, false-repair, and winner retention.
- Explicitly identify whether R-core precision failure is timing, density, or label-quality driven.

Required outputs:

- `r_core_backbone_demotion_readout.csv`
- `r_core_episode_alignment_by_window.csv`
- `r_core_density_badside_tradeoff.csv`
- `r_core_demote_or_keep_decision.md`

Decision states:

```text
12A1_r_core_backbone_supported
12A1_r_core_feature_source_only
12A1_r_core_recall_benchmark_only
12A1_r_core_population_blocked
```

Expected current prior:

```text
R-core should be demoted to feature source / recall benchmark,
not retained as primary backbone.
```

### Phase 12A2: State-Change Backbone Candidate Generator

Goal:

```text
generate PIT-safe state-change event candidates that are earlier and cleaner than R-core.
```

Candidate families:

- B1 relative residual CUSUM break;
- B2 compression-to-expansion;
- B3 low-reclaim / repair transition;
- B4 breadth/regime context;
- B5 first-trigger density discipline.

Minimum event contract:

- t0 close confirmation;
- next-open executable convention;
- no future return / MFE / episode label as feature;
- no label-derived touch coordinate;
- qfq path consistency;
- PIT board / market context frozen;
- first-trigger and reset rules frozen.

Required outputs:

- `state_change_candidate_event_canonical.csv.gz`
- `state_change_family_formula_spec.csv`
- `state_change_feature_pit_audit.csv`
- `state_change_density_audit.csv`
- `state_change_candidate_generation_report.md`

Failure status:

```text
12A2_state_change_candidate_generation_blocked
```

### Phase 12A3: Episode Precision / Recall Frontier

Goal:

```text
compare state-change candidates against R-core on episode-level recall and event precision.
```

Primary metrics:

- episode recall against 06 risk_on 428 episodes;
- event precision inside pre120-to-high;
- event precision inside low-to-high;
- event timing relative to episode low;
- events per captured episode;
- outside-episode event rate;
- same-instrument 10d duplicate;
- p95 event density;
- fast-fail / false-repair exposure;
- PIT executable coverage.

Useful readout:

```text
R-core may win raw recall.
State-change backbone must win precision, density, and timing quality
while preserving enough episode recall to be useful.
```

Required outputs:

- `backbone_episode_recall_precision_frontier.csv`
- `backbone_event_timing_distribution.csv`
- `backbone_captured_episode_density.csv`
- `backbone_missed_episode_diagnostics.csv`
- `backbone_frontier_decision_report.md`

Decision states:

```text
12A3_state_change_backbone_supported
12A3_state_change_backbone_partial_feature_source
12A3_no_backbone_improvement_over_r_core
```

### Phase 12A4: Optional Filter Layer Feasibility

Trigger:

```text
Only run if 12A3 finds a candidate backbone with better precision/density tradeoff.
```

Goal:

```text
test whether a small, interpretable filter improves the accepted backbone
without turning the experiment into winner/failure modeling.
```

Allowed filters:

- 10B-like fast-fail small safety gate;
- first-trigger cooldown;
- execution/tradability filter;
- context stratification by board / market regime;
- low-capacity bad-timing filter.

Forbidden at this phase:

- direct winner/failure classifier;
- probability model;
- policy replay;
- arbitrary threshold search over future payoff.

Required outputs:

- `backbone_filter_frontier.csv`
- `filter_winner_retention_readout.csv`
- `filter_badside_exposure_readout.csv`
- `12A4_filter_layer_decision_report.md`

Decision states:

```text
12A4_filter_supported
12A4_filter_diagnostic_only
12A4_filter_rejected_winner_injury
```

### Phase 12A5: Multi-K Morphology on Accepted Backbone

Trigger:

```text
Only run after 12A3 or 12A4 accepts a backbone.
```

Goal:

```text
test whether K1/K3/K5/K10 observed paths add incremental separation
on a cleaner event backbone.
```

This phase inherits part of the old 12 plan, but with a different denominator.

Allowed observed-state families:

- return path increments;
- drawdown / damage timing;
- recovery / reclaim shape;
- volume / money confirmation;
- volatility sequence;
- relative path vs board / market;
- execution / tradability state.

Primary baseline:

```text
accepted_backbone + t0 state
```

not:

```text
raw R-core + 11A2 strict PIT row set
```

Required outputs:

- `multi_k_incremental_separability_on_backbone.csv`
- `multi_k_path_feature_registry.csv`
- `multi_k_label_overlap_audit.csv`
- `multi_k_morphology_decision_report.md`

Decision states:

```text
12A5_multi_k_incremental_supported
12A5_multi_k_no_incremental_freedom
12A5_morphology_deferred_power_or_leakage
```

---

## 7. Decision Gates

### Gate 0: Population Freeze

Pass conditions:

- 06 episode registry and 11 PIT row registry are both frozen.
- Alignment gaps are explained.
- No target population is silently substituted.

Fail:

```text
12_population_lineage_blocked
```

### Gate 1: R-core Backbone Decision

Pass as backbone only if R-core satisfies:

- acceptable episode recall;
- acceptable event precision;
- density within predeclared budget;
- duplicate within budget;
- bad-side exposure not materially worse than benchmark;
- first-trigger timing not dominated by after-high / repeated momentum events.

Otherwise demote:

```text
R-core = feature source / recall benchmark
```

### Gate 2: State-Change Candidate Support

A state-change backbone can be supported only if it improves at least one of:

- event precision;
- outside-episode suppression;
- event density;
- duplicate rate;
- timing near episode low / before acceleration;
- bad-side exposure;

without destroying episode recall.

### Gate 3: Filter Layer Support

A filter layer is supported only if:

- winner retention remains acceptable;
- precision or bad-side exposure improves;
- improvement is not only reduced exposure;
- split behavior is not train-only.

### Gate 4: Multi-K Morphology Eligibility

Multi-K morphology is eligible only after an event backbone is accepted.

If no accepted backbone exists, 12 must stop at:

```text
12_no_valid_backbone_for_morphology
```

---

## 8. Metrics

### 8.1 Episode Metrics

- `episode_recall_pre120_to_high`
- `episode_recall_low_to_high`
- `episode_recall_low_to_first_50pct`
- `captured_episode_event_count_median`
- `captured_episode_first_event_days_from_low`
- `missed_episode_count`
- `missed_episode_regime / board / liquidity profile`

### 8.2 Event Precision Metrics

- `event_inside_pre120_to_high_rate`
- `event_inside_low_to_high_rate`
- `event_outside_episode_rate`
- `event_after_high_rate`
- `event_before_low_rate`
- `event_nearest_episode_distance`

### 8.3 Density Metrics

- events per instrument-year;
- same-instrument 10d duplicate;
- same-instrument 20d duplicate;
- p95 event density;
- event-day concentration;
- top instrument contribution;
- top board / family contribution.

### 8.4 Bad-Side Metrics

- fast-fail rate;
- false-repair rate;
- big-failure proxy rate;
- winner retention;
- E1-missed retention if applicable;
- 10B safety gate compatibility.

### 8.5 Execution Metrics

- next-open executable rate;
- limit-up locked next-open;
- limit-down exit risk;
- suspension through K;
- qfq path completeness;
- capacity / turnover proxy.

---

## 9. Non-Goals

12 does not:

- train a winner/failure classifier on raw R-core;
- tune `keep_0800`, 09C `keep_7000`, or 10C `keep_9000`;
- treat 11A2 K3 as a final strategy point;
- treat the 11A2 446 rows as the full 06 episode target;
- use future MFE, future return, or label touch coordinates as features;
- run policy replay;
- create position sizing;
- authorize a buy/sell rule.

---

## 10. Recommended Requirement Split

After this plan is accepted, write requirements in this order:

```text
requirement_12a0_winner_registry_lineage_audit.md
requirement_12a1_r_core_backbone_demotion_audit.md
requirement_12a2_state_change_backbone_candidate_generator.md
requirement_12a3_episode_precision_recall_frontier.md
requirement_12a4_backbone_filter_layer_feasibility.md
requirement_12a5_multi_k_morphology_on_accepted_backbone.md
```

Do not start with 12A5.

The first implementation unit should be 12A0 + 12A1, because they determine whether the old morphology direction is even valid.

---

## 11. Expected Outcomes

### Outcome A: R-core Demoted, State-Change Backbone Supported

Best case:

```text
R-core remains useful as recall stress pool / feature source,
but a state-change backbone becomes the primary event population.
```

Then proceed to 12A4 / 12A5.

### Outcome B: R-core Demoted, No Replacement Yet

Useful negative result:

```text
R-core is not good enough,
but current state-change candidates are also not good enough.
```

Then the next research step is new event-family discovery, not winner/failure morphology.

### Outcome C: R-core Retained Only After Compression

Possible but unlikely:

```text
10A / 10B style compression makes R-core acceptable enough
as a feature-source backbone, but not as raw event backbone.
```

Then morphology can run only on the compressed population.

### Outcome D: No Valid Backbone for Morphology

Stop state:

```text
12_no_valid_backbone_for_morphology
```

This is a valid research result. It prevents spending more work on downstream models whose denominator is already broken.

---

## 12. Immediate Next Step

Write and review:

```text
requirement_12a0_winner_registry_lineage_audit.md
requirement_12a1_r_core_backbone_demotion_audit.md
```

The first requirement freezes the target population. The second decides the status of R-core.

Only after those two pass should 12 generate new state-change candidates.

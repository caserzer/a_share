# AFML Big Winner Research

Restarting the A-share BIG WINNER / +50% stock discovery project with an
AFML-style research pipeline.

## 1. Project Goal

This project aims to build a slow, event-driven quantitative research system
for identifying and managing potential BIG WINNER stocks in the A-share market.

The target opportunity is not ordinary short-term alpha. The system focuses on:

- Finding early candidate episodes that may become large winners.
- Preserving high recall for future right-tail winners.
- Failing fast when a signal is false.
- Reducing false-positive exposure-days.
- Managing winners through confirmation, continuation, sizing, and exit logic.

The project is restarted based on the framework of *Advances in Financial
Machine Learning* because prior experiments showed that dense daily prediction,
raw factor libraries, and fixed-horizon labels were not sufficient.

## 2. Core Research Thesis

The system should not directly predict this question from dense daily stock-day
samples:

> Will this stock rise +50% in 120 trading days?

Instead, the system should be structured as:

```text
Event Generator
    ->
Episode Builder
    ->
Failure Filter
    ->
Confirmation Model
    ->
Continuation / Winner Model
    ->
Bet Sizing
    ->
Backtesting and Robustness Evaluation
```

The core thesis:

> BIG WINNER discovery is an episode lifecycle problem, not a one-step
> classification problem.

## 3. Background from Prior Exploration

This section summarizes lessons checked against the existing results under
`topics/01_askhare_qlib/`. The directory name uses `askhare`, not
`askshare`. Artifact paths in this section are repo-root relative.

### 3.1 Original Objective and Evidence Boundary

Earlier work targeted stocks capable of large moves, especially:

- +50% within roughly 120 trading days.
- Earlier entry than obvious breakout confirmation.
- Fast failure handling when the setup is false.
- Continued holding and sizing when a right-tail path starts to develop.

The evidence says this should not be treated as a dense daily prediction task.
The strongest support comes from the PIT big-winner profile in
`topics/01_askhare_qlib/Explore8/outputs/reports/explore8_big_winner_profile_report.md`:

- PIT annual +50% winners are not rare in high-opportunity years.
- Annual slicing cuts many full winner lifecycles into partial fragments.
- `first_ema60_reclaim` is usually earlier than `first_breakout_signal`.
- Existing rules mostly miss winners through `no_signal`, `late_signal`,
  `market_filtered`, or `early_exit`, not through liquidity or coverage failure.

Conclusion:

> BIG WINNER discovery should be framed as early episode discovery plus
> lifecycle management, not as a one-shot `winner_120` classifier.

### 3.2 Static Universe and Dense Factor Baselines

`topics/01_askhare_qlib/Explore1/outputs/reports/explore1_report.md`
completed the first Qlib workflow with Alpha158 / LightGBM and a static
`2025-12-31` large-cap universe. The workflow ran end to end, but the report
explicitly warned that the universe had survivor and future-date bias. It also
showed that attractive portfolio results coexisted with weak ranking quality,
so the result could not be interpreted as proof that dense Alpha158 ranking had
solved the problem.

Lessons:

- A runnable factor pipeline is useful infrastructure, not alpha proof.
- Static future universes and current-as-of industry labels contaminate
  historical conclusions.
- Dense stock-day ranking can look good because of universe, market regime, and
  portfolio construction effects.

### 3.3 EMA Trend, Pullback, and Early Rule Systems

`Explore3` built a rule-only EMA trend system with market, breadth, industry,
EMA state, breakout/pullback entry, structural stops, time stop, and EMA60 exit.
The observed 2025-2026 replication looked strong, but
`topics/01_askhare_qlib/Explore3/outputs/reports/explore3_verification_report.md`
still kept the static-universe and observed-period caveats.

`Explore4` and `Explore5` then showed the weak point. In rolling validation,
risk-unit sizing and industry caps reduced drawdown and concentration but did
not make the candidate set reliably positive. The repeated failure pattern was:

- Pullback entries were the main negative contributor.
- `stop_loss` and `time_stop` were the dominant loss exits.
- Trailing / EMA exits generated much of the positive tail.
- Stronger risk controls often created high cash and lower exposure rather than
  better signal quality.

Evidence paths:

- `topics/01_askhare_qlib/Explore4/outputs/reports/final_test_report.md`
- `topics/01_askhare_qlib/Explore4/outputs/reports/pullback_failure_analysis_report.md`
- `topics/01_askhare_qlib/Explore5/outputs/reports/explore5_final_report.md`
- `topics/01_askhare_qlib/Explore8/outputs/reports/explore8_deep_dive_analysis_report.md`

Conclusion:

> A simple trend rule is not enough. The system needs event structure,
> path-dependent labels, failure filtering, and continuation management.

### 3.4 Point-in-Time and Observability Corrections

Several later reports corrected the reliability boundary before further alpha
search:

- `Explore3` verified signal/execution alignment and portfolio reconciliation.
- `Explore4` separated observed replication from true unseen testing.
- `Explore7` replaced the static `2025-12-31` universe with PIT daily
  membership and PIT industry membership for pullback rebuild diagnostics.
- `Explore8` resolved provider coverage gaps and moved the analysis from data
  coverage failure to rule-shape and regime diagnostics.

Lessons:

- Every feature and label needs a clear as-of time.
- Observed-period replication must not be promoted to final-test evidence.
- Episode-level denominators are safer than repeated raw trigger rows.
- Before searching for alpha, the event and label pipeline must be
  point-in-time correct.

### 3.5 Seed Density, Recall, and Fail-Fast

EP4 R01 directly tested a high-recall seed plus fail-fast probe:
`topics/01_askhare_qlib/ep4/outputs/r01_high_recall_probe_fail_fast/reports/r01_final_report.md`.

The wide seed improved big-winner recall versus the EP2 bridge:

- Validation recall improved from `1.90%` to `9.49%`.
- Robustness recall improved from `6.22%` to `18.26%`.

But it failed hard density gates:

- Validation seed-day rate was `8.12%` versus a `1.48%` cap.
- Robustness seed-day rate was `11.42%` versus a `1.96%` cap.
- Episode-level density looked less alarming only because repeated daily signals
  were compressed after the fact.

R01.1 then tested deterministic emission throttling and cooling entry:
`topics/01_askhare_qlib/ep4/outputs/r01_1_emission_throttled_cooling_entry_probe_fail_fast/reports/r01_1_final_report.md`.
It fixed the density side, but failed validation recall-retention and
incremental cost / exposure gates. The repair reduced emissions, but also
discarded too many future winners.

Conclusion:

> Candidate events must be sparse at the executable seed-day level, not only
> after episode deduplication. A density repair is not acceptable if it destroys
> big-winner recall or pushes incremental loss/exposure per added winner beyond
> the frozen gates.

### 3.6 Fixed Horizon and Hold / Exit Experiments

EP4 R04 showed that `single_momentum_rps` retained some right-tail information
but was not a reusable action-time entry edge:
`topics/01_askhare_qlib/ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/reports/r04_dynamic_momentum_exposure_eligibility_final_report.md`.

R04b then replayed hold / exit / risk-budget policies:
`topics/01_askhare_qlib/ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/reports/r04b_fixed_entry_hold_exit_risk_budget_cta_final_report.md`.
The selected validation policy reduced left-tail losses and retained many
potential +50% winners, but robustness failed on mean payoff. Aggressive
CTA/trailing/time-stop variants often looked good in validation by cutting
right-tail opportunity.

Lessons:

- `H20`, `H60`, and `H120` style horizons are diagnostics, not a solution by
  themselves.
- Exit insurance can reduce bad paths but still be too expensive in strong
  years.
- Holding value should be modeled as a staged lifecycle decision: fail,
  confirm, continue, size, or exit.

### 3.7 Alpha191 / GTJA191 Feature Experiments

EP5 tested GTJA191 / Alpha191 features more rigorously:

- R04 equal-weight residual composites did not support H10 long-only alpha:
  `topics/01_askhare_qlib/ep5/outputs/r04_gtja191_short_horizon_residual_composite_feasibility_v0/reports/r04_final_report.md`.
- R05 train-only factor engineering, clustering, neutralization, and
  representative selection still failed:
  `topics/01_askhare_qlib/ep5/outputs/r05_gtja191_train_only_factor_engineering_residual_feasibility_v0/reports/r05_final_report.md`.
- R06 found local short-horizon information traces, mainly around H1/H3
  volume-price and VWAP families, but no family passed information,
  monotonicity, persistent-name, style-clean, and cost gates together:
  `topics/01_askhare_qlib/ep5/outputs/r06_gtja191_factor_decay_information_content_audit_v0/reports/r06_final_report.md`.

Conclusion:

> Alpha191 / Alpha158 / GTJA191 style features may be useful as train-only
> feature banks or low-level expressions, but the prior results do not support
> treating raw composites or validation-tuned factor blends as direct alpha.

### 3.8 Short-Horizon State and Transferability Experiments

EP5 R07 and R08 refined the short-horizon signal question:

- R07 found `14` local short-horizon pockets, mostly H1/H3, but none were clean
  unconditionally; state slicing was mostly sample-blocked:
  `topics/01_askhare_qlib/ep5/outputs/r07_short_horizon_timing_failure_attribution_audit_v0/reports/r07_final_report.md`.
- R08's single split was blocked by instrument-segment sample thickness:
  `topics/01_askhare_qlib/ep5/outputs/r08_h3_volume_price_single_stock_state_transferability_audit_v0/reports/r08_final_report.md`.
- R08.1 improved sample thickness with 5-fold OOF, but weekly `vwap_deviation`
  H3 still failed transferability cleanliness:
  `topics/01_askhare_qlib/ep5/outputs/r08_1_vwap_deviation_h3_kfold_transferability_sensitivity_audit_v0/reports/r08_1_final_report.md`.
- R08.2 changed to daily close-observed `vwap_deviation` and supported an H3
  transferability diagnostic, while explicitly not authorizing any strategy:
  `topics/01_askhare_qlib/ep5/outputs/r08_2_daily_observed_vwap_deviation_h3_h5_h10_transferability_diagnostic_v0/reports/r08_2_final_report.md`.
- R08.3 showed that the R08.2 result did not generalize to the other
  volume/rank families:
  `topics/01_askhare_qlib/ep5/outputs/r08_3_daily_observed_volume_rank_families_h3_h5_h10_transferability_diagnostic_v0/reports/r08_3_final_report.md`.

Updated conclusion:

> Weak short-horizon information exists in specific state/family definitions,
> especially daily `vwap_deviation` H3, but it remains diagnostic-only. The
> broader lesson is still that single-factor or simple exposure lines are not
> enough; the restart needs event families, episode-level labels, failure
> filters, confirmation logic, and robust validation.

## 4. Key Concepts

### 4.1 Event

An event is a point in time when a stock becomes worth evaluating.

Examples:

- Positive CUSUM event.
- Breakout near 120D high.
- Volatility contraction followed by expansion.
- DIB / signed amount confirmation.
- Industry strength confirmation.
- Structural break in relative strength.

An event answers:

> When should we look?

It is not yet a trade.

### 4.2 Episode

An episode is the lifecycle of one potential opportunity.

Definition:

> For one stock and one side, an episode starts when the stock first triggers a
> valid opportunity condition while no active episode exists, and ends when the
> opportunity fails, confirms and completes, structurally breaks, or reaches
> maximum observation time.

Episode-level analysis prevents the same opportunity from being counted
repeatedly as many daily samples.

### 4.3 Primary Side

The initial system is long-only. Therefore, the primary side can often be:

```text
side = +1
```

The primary layer does not need to predict both long and short directions at the
beginning.

### 4.4 Failure Filter

The first learned gate should likely focus on:

```text
failure_10
```

It asks:

> Does this candidate fail quickly within 10 trading days?

The objective is not simply to minimize failure, because the trivial solution is
not trading.

The correct objective is:

```text
minimize accepted failure_10 rate
subject to retaining enough big-winner recall
```

### 4.5 Meta-Labeling

Meta-labeling is used after a primary side exists.

It does not answer:

> Will the stock go up or down?

It answers:

> Given that this is a long candidate, is it worth taking?

For this project, meta-labeling may be split into:

- `failure_10`
- `confirm_20`
- `continuation_60`
- `winner_120`

The first layer should focus on failure and confirmation. The long-horizon
winner label should be episode-level and should not be the only entry target.

## 5. Proposed Label System

These labels are research candidates, but each experiment that consumes them
must freeze a concrete label contract in `config.yaml` before running. The
contract must define:

- `t0`: signal date after all close-observed features are available.
- `trade_time`: first executable entry time after `t0`, after limit,
  suspension, and liquidity filters.
- `t1`: first barrier-touch date or the maximum horizon end.
- Price fields, adjustment policy, and whether barriers use close, high/low,
  or executable prices.
- Upper barrier, lower barrier, drawdown, support-break, and confirmation
  thresholds.
- Touch priority when multiple barriers are reached on the same bar.
- Censoring policy when the horizon is incomplete or no executable trade
  exists.
- Label end timestamp used by purged CV, sample uniqueness, and concurrency.

### 5.1 `failure_10`

Purpose:

- Fast failure detection.

Initial contract intent:

```text
failure_10 = 1 if, within 10 trading days after trade_time,
    a configured lower barrier, drawdown barrier, episode-start low break,
    or structural support break is touched before any configured confirmation
    or upper barrier condition.
```

Thresholds are configuration-frozen per experiment; they must not be inferred
from the full sample after labels are built.

Use:

- Entry gate.
- Trial-position filter.
- False-positive exposure reduction.

### 5.2 `confirm_20`

Purpose:

- Short-term confirmation.

Initial contract intent:

```text
confirm_20 = 1 if, within 20 trading days after trade_time,
    a configured confirmation threshold, valid new-high condition,
    or upper barrier is touched before the configured lower barrier.
```

The contract must define the executable observation rule for new highs and
same-bar tie handling.

Use:

- Determine whether the candidate deserves execution.
- Determine whether a trial position can be upgraded.

### 5.3 `continuation_60`

Purpose:

- Medium-term trend continuation.

Initial contract intent:

```text
continuation_60 = 1 if, within 60 trading days after trade_time,
    the configured trend-integrity condition remains valid,
    MFE reaches the configured continuation threshold,
    and drawdown remains below the configured failure threshold.
```

The contract must define whether continuation is evaluated only after
`confirm_20`, or independently for all accepted episodes.

Use:

- Holding decision.
- Add-on decision.
- Continuation sizing.

### 5.4 `winner_120`

Purpose:

- Right-tail episode evaluation.

Initial contract intent:

```text
winner_120 = 1 if, within 120 trading days after trade_time,
    MFE reaches the configured right-tail threshold
    and no configured hard-failure barrier is touched first.
```

The threshold can be `+30%`, `+50%`, or another predeclared target, but it must
be frozen before the run and reported with winner recall.

Use:

- Episode-level post-entry evaluation.
- Payoff model.
- Winner recall measurement.
- Position cap adjustment.

Important rule:

> `winner_120` should not be the only entry label.

## 6. AFML Chapter Mapping

### Chapter 2 - Financial Data Structures

Project use:

- Event-based sampling.
- CUSUM events.
- Imbalance features.
- Episode construction.
- Avoid dense daily stock-day sampling.

### Chapter 3 - Labeling

Project use:

- Path-dependent labels.
- Triple-barrier-inspired labels.
- Staged labels:
  - `failure_10`
  - `confirm_20`
  - `continuation_60`
  - `winner_120`

### Chapter 4 - Sample Weights

Project use:

- Store `t0` and `t1` for every sample.
- Compute concurrency.
- Compute average uniqueness.
- Use return attribution.
- Apply time decay.
- Reject event families with extremely low uniqueness.

### Chapter 5 - Fractionally Differentiated Features

Project use:

- Use only on selected memory-bearing continuous series.
- Candidate series:
  - `log(close / industry_index)`
  - `log(close / market_index)`
  - `log(industry / market)`
  - `log(amount)`
  - VWAP-related series.

Do not blindly apply fracdiff to:

- Returns.
- Ranks.
- Event dummies.
- Labels.

### Chapter 6 - Ensemble Methods

Project use:

- Bagging / random forest as robust baselines.
- Boosting as challenger model only after event quality is acceptable.
- Monitor base classifier correlation.
- Avoid boosting noisy dense stock-day labels.

### Chapter 7 - Cross-Validation in Finance

Project use:

- Use purged K-fold.
- Use embargo.
- Store:
  - Feature start time.
  - Event time `t0`.
  - Label end time `t1`.
- Final evaluation still needs chronological walk-forward.

### Chapter 8 - Feature Importance

Project use:

- Group features by family.
- Use SFI, MDA, and group MDA.
- Use MDI only as supporting evidence.
- Handle substitution effects.
- Avoid full-sample feature selection leakage.

### Chapter 10 - Bet Sizing

Project use:

```text
size =
    base_size
    * (1 - P(failure_10))
    * P(confirm_20)
    * P(continuation_60)
    * payoff_score
    * regime_adjustment
    * volatility_adjustment
```

Bet sizing is a risk translation layer, not just another probability model.

### Chapter 12 - Backtesting through Cross-Validation

Project use:

- Evaluate models across purged CV paths.
- Compare raw event system, failure-filtered system, and
  confirmation-filtered system.
- Focus on robustness, not one lucky historical path.

### Chapter 13 - Backtesting on Synthetic Data

Project use:

- Stress-test exit rules.
- Test stop-loss, profit-taking, trailing stop, and max holding period.
- Inspect heatmaps for stable regions.
- Do not use synthetic data as proof of alpha.

### Chapter 14 - Backtest Statistics

Track:

- Winner recall.
- Seed density.
- False-positive density.
- Exposure-days.
- MFE / MAE.
- Payoff ratio.
- Hit ratio.
- Average win/loss.
- Max drawdown.
- Time under water.
- Calmar.
- Turnover.
- Capacity.

### Chapter 17 - Structural Breaks

Project use:

- CUSUM on market and style ratios.
- SADF on market / growth / small-cap relative indexes.
- Detect broad market break, growth break, small-cap break, defensive break, and
  speculative explosive states.

Structural break features are regime context features, not standalone buy
signals.

### Chapter 18 - Entropy Features

Candidate entropy features:

- `entropy_sign_stock_vs_industry_60`
- `lz_stock_vs_industry_120`
- `sigma_entropy_industry_vs_market_60`
- `entropy_growth_vs_large_120`
- `gaussian_joint_entropy_market_60`

Entropy should be treated as a feature family.

## 7. Initial Project Directory Structure

```text
02_AFML_BIG_WINNER/
|-- README.md
|-- pyproject.toml
|-- requirements.txt
|-- uv.lock
|-- configs/
|   |-- universe.yaml
|   |-- data.yaml
|   |-- events.yaml
|   |-- labels.yaml
|   |-- features.yaml
|   |-- cv.yaml
|   |-- models.yaml
|   `-- backtest.yaml
|-- data/
|   |-- raw/
|   |-- interim/
|   |-- processed/
|   |-- qlib/
|   `-- external/
|-- src/
|   `-- afml_big_winner/
|       |-- config.py
|       |-- manifest.py
|       |-- cli.py
|       |-- data/
|       |-- events/
|       |-- labels/
|       |-- features/
|       |-- sample_weights/
|       |-- validation/
|       |-- models/
|       |-- sizing/
|       |-- backtest/
|       `-- diagnostics/
|-- notebooks/
|   |-- 00_data_audit.ipynb
|   |-- 01_event_quality.ipynb
|   |-- 02_label_diagnostics.ipynb
|   |-- 03_feature_diagnostics.ipynb
|   |-- 04_model_baseline.ipynb
|   |-- 05_meta_labeling.ipynb
|   |-- 06_bet_sizing.ipynb
|   `-- 07_backtest_review.ipynb
|-- experiments/
|   |-- README.md
|   |-- templates/
|   |   `-- experiment_template/
|   |       |-- README.md
|   |       |-- config.yaml
|   |       |-- code/
|   |       |   |-- run.py
|   |       |   `-- diagnostics.py
|   |       |-- notebooks/
|   |       |-- outputs/
|   |       |   |-- data/
|   |       |   |-- metrics/
|   |       |   |-- tables/
|   |       |   |-- figures/
|   |       |   |-- reports/
|   |       |   |-- manifests/
|   |       |   |-- publishable/
|   |       |   |-- local_cache/
|   |       |   `-- large_raw/
|   |       |-- tests/
|   |       `-- notes/
|   |-- pending/
|   |   `-- .gitkeep
|   `-- completed/
|       `-- .gitkeep
|-- reports/
|   |-- figures/
|   |-- tables/
|   `-- final/
`-- tests/
    |-- test_no_future_leakage.py
    |-- test_purged_cv.py
    |-- test_triple_barrier.py
    |-- test_episode_builder.py
    `-- test_sample_weights.py
```

Experiment names are intentionally not fixed at project start. Each experiment
should live in its own folder copied from `experiments/templates/experiment_template/`
and should keep code, configuration, outputs, figures, reports, manifests, and
notes together. Shared reusable library code belongs in top-level `src/`; code
that is specific to one experiment belongs inside that experiment's `code/`
folder.

`outputs/publishable/` is for small artifacts intended to be reviewed and
committed. `outputs/local_cache/` and `outputs/large_raw/` are local generated
state and should be ignored, compressed, or summarized before publication. Each
completed experiment should write a run manifest with the command, config hash,
input paths, output file hashes, data cutoff, and final decision.

Basic environment and template checks:

```bash
uv sync --extra dev
uv run python -m compileall src experiments/templates/experiment_template/code
uv run python experiments/templates/experiment_template/code/run.py
uv run pytest
```

## 8. Minimum Required Sample Schema

Every sample should contain:

- `sample_id`
- `asset`
- `event_family`
- `episode_id`
- `side`
- `feature_start_time`
- `t0`
- `trade_time`
- `t1`
- `label_name`
- `label_value`
- `sample_weight`

For episode-level samples:

- `episode_start`
- `episode_end`
- `end_reason`
- `MFE`
- `MAE`
- `max_drawdown`
- `time_to_failure`
- `time_to_confirm`
- `time_to_peak`

## 9. Research Principles

### 9.1 No Future Leakage

Every feature must be point-in-time.

Forbidden features:

- `future_ret`
- `future_high`
- `future_low`
- `future_barrier_touch`
- Label-derived variables.
- Post-event volume.

### 9.2 Train-Only Selection

Feature selection, scaling, PCA, thresholds, and model tuning must be fit inside
training folds only.

No full-sample feature ranking before CV.

### 9.3 Event Before Model

Do not begin with a large flat feature library and ask the model to discover
everything.

First define meaningful event families and episode logic.

### 9.4 Recall First, But Not at Any Cost

The event generator should maximize big-winner episode recall under constraints:

- Seed density acceptable.
- Average uniqueness acceptable.
- Failure rate acceptable.
- Matched-random uplift positive.

### 9.5 Failure Filter Must Preserve Winners

A `failure_10` model is useful only if it reduces quick failures while
preserving enough future winners.

Main constraint:

```text
winner_recall_retention must remain high
```

### 9.6 `winner_120` Is for Episode Evaluation

`winner_120` should not be the sole entry label.

Use staged labels:

- `failure_10`
- `confirm_20`
- `continuation_60`
- `winner_120`

### 9.7 Seal Only After the Complete Run

Do not seal or make data and outputs immutable at the beginning of an
experiment or during a partial run. Data, intermediate artifacts, manifests,
hash registries, and reports must remain open to repair and rerun until the
entire authorized execution and its post-run validation are complete.

The required lifecycle is:

```text
working
    -> preflight_checked
    -> diagnostic_complete
    -> full_run_complete
    -> post_run_validation_complete
    -> sealed
```

Only the final transition may create an immutable output bundle. A preflight
failure, diagnostic failure, interrupted run, partial materialization, or
failed validation must be recorded as an auditable working-state event, not
published or sealed as a final bundle. It must remain possible to repair the
same working lineage and rerun it to completion.

After the complete run has passed its frozen cardinality, integrity,
determinism, and report checks, the final data and report bundle may be sealed.
Once sealed, its files, manifest, and hash chain are immutable; later analysis
must use a new version or a clearly linked companion artifact. Existing sealed
historical bundles are not retroactively modified by this principle.

### 9.8 EP22 Uses Exploratory Data-Discovery Mode

Episode 22 is a data-exploration and hypothesis-testing workspace. Its purpose is
to try multiple measurable interpretations of the practitioner narrative,
inspect real-market data, and support, weaken, or falsify component hypotheses.
Routine exploration must not be slowed by per-stage human authorization or by a
requirement that every intermediate bundle be sealed.

Within the documented EP22 scope, the agent may autonomously:

- create and revise research plans, requirements, configs, code, and tests;
- run local historical-data audits, diagnostics, ablations, and competing
  variants;
- discover, download, cache, and profile public read-only data sources that do
  not require new credentials, payment, or mutation of an external system;
- treat the current project PIT universe and OHLCV bundle as a reproducible
  baseline rather than a ceiling on what EP22 may investigate;
- read outcomes after the relevant PIT/as-of inputs have been materialized and
  logged;
- iterate on failed or ambiguous formulations and preserve both positive and
  negative findings;
- update working reports and manifests as evidence develops.

The EP22 exploratory lifecycle is:

```text
working
    -> checkpointed
    -> diagnostic_complete
    -> validated_working_result
    -> optional_formal_freeze
```

`checkpointed` means the current config, inputs, code identity, and outputs are
recorded well enough to reproduce or compare the attempt. It is not an
immutable seal. EP22 working artifacts may be repaired, extended, or rerun in
place when their lineage and changes remain auditable. Hashes, manifests, and
stage logs are reproducibility tools, not human-approval gates.

The following scientific controls still apply during exploration:

- point-in-time timing and no future leakage;
- clear separation of direct measurement, proxy, and unavailable construct;
- train-only selection where a predictive claim is being tested;
- honest denominator, multiplicity, stability, and concentration reporting;
- explicit distinction between exploratory historical support, falsification,
  low power, and data blockage;
- no promotion of exploratory historical evidence to true forward support.

Data discovery itself is a first-class EP22 research question. Candidate data
must be assessed at two different levels:

```text
contract usefulness:
    coverage + PIT reconstructability + timestamp/revision lineage
    + construct fidelity + effective-support improvement

empirical usefulness:
    incremental historical evidence versus the existing-data baseline
    under a versioned module-specific attempt
```

An available source is not automatically useful, and a source that improves
coverage is not automatically predictive. EP22 must preserve source-search
accounting and may conclude that a candidate source is unavailable, not
PIT-reconstructable, redundant, low-value, or genuinely component-unblocking.

Explicit human approval and a formal immutable freeze are required only when
EP22 moves beyond routine local exploration into a materially different action,
including production deployment, live trading, mutation of external systems,
paid or newly credentialed data acquisition, a formal forward-confirmation claim, or
destructive modification of an already sealed historical bundle. Cross-module
decision routing and production position sizing remain outside EP22 unless the
user separately expands the project scope.

## 10. Initial Research Workstreams

These are research workstreams, not fixed experiment names. Actual experiment
folder names should be assigned only when a concrete requirement, label
contract, and validation gate are frozen.

### Data and Schema Audit

Goal:

- Build clean point-in-time dataset and sample schema.

Outputs:

- Universe definition.
- Adjusted price data.
- Trade calendar.
- Feature availability audit.
- Leakage audit.

### Event Generator Baseline

Goal:

- Build sparse high-recall candidate event families.

Candidate event families:

- CUSUM positive event.
- Breakout near 120D high.
- VCP / volatility contraction.
- DIB / signed amount confirmation.
- Industry strength confirmation.
- Market regime filter.

Metrics:

- Winner episode recall.
- Seed density.
- MFE uplift vs matched random.
- `failure_10` rate.
- Average uniqueness.

### Episode Builder

Goal:

- Convert dense repeated stock-day events into clean opportunity episodes.

Outputs:

- Episode table.
- Start/end rules.
- End reason distribution.
- Internal event count.
- Uniqueness improvement.

### Failure Filter

Goal:

- Predict and reduce `failure_10`.

Optimization:

```text
minimize accepted failure_10
subject to winner recall retention
```

Metrics:

- Accepted failure rate.
- Failure capture rate.
- Winner recall retention.
- Exposure-days reduction.
- MAE reduction.

### Confirmation Model

Goal:

- Predict `confirm_20` among candidates that pass the failure filter.

Metrics:

- Precision@top.
- Top-bucket EV.
- Monotonicity by probability bucket.
- Calibration.
- Confirm uplift vs primary candidates.

### Continuation / Winner Model

Goal:

- Predict `continuation_60` and `payoff_score_120`.

Metrics:

- Continuation precision.
- MFE/MAE improvement.
- Winner recall among accepted episodes.
- Payoff ratio.
- Right-tail capture.

### Regime Features

Goal:

- Add structural break and entropy features.

Candidate features:

- Market trend score.
- Growth vs large-cap break.
- Small-cap vs large-cap break.
- SADF overheat flag.
- Entropy of stock vs industry.
- Entropy of industry vs market.

Metrics:

- Group MDA.
- Regime-conditioned success rate.
- False-positive reduction by regime.

### Bet Sizing and Exit Rules

Goal:

- Convert probabilities and payoff scores into position sizes.

Test:

- Fixed size.
- Probability-based size.
- Failure-adjusted size.
- Continuation-adjusted size.
- Volatility target.
- Regime-adjusted size.

Synthetic path tests:

- Stop-loss heatmaps.
- Profit-taking heatmaps.
- Trailing stop tests.
- Max holding period tests.

## 11. Non-Goals for the Restart

This restart should not:

- Directly optimize a dense daily stock-day `winner_120` classifier.
- Use full-sample feature selection.
- Search thousands of parameter combinations on validation.
- Treat Alpha191 / Alpha158 as direct alpha.
- Trust ordinary K-fold.
- Treat synthetic data as proof of alpha.
- Select isolated best heatmap cells.
- Ignore sample overlap and uniqueness.
- Use future data in feature construction.
- Confuse event signal with executable trade.

## 12. Project Motto

Find sparse candidate episodes.
Fail fast.
Confirm early.
Hold right tails.
Size by probability, payoff, and risk.
Validate without leakage.

# EP6 Paper Replica Requirement 07: Weekly Idiosyncratic Momentum Risk Horse Race V0

## 1. Requirement Metadata

requirement_id: `ep6_paper_replica_07_weekly_idiosyncratic_momentum_risk_horse_race_v0`

short_name: `r07_weekly_idiosyncratic_momentum_risk_horse_race_v0`

status: `requirement-draft-revised`

workflow: `EP6`

created_date: `2026-05-26`

requirement_path: `ep6/papers/replica/requirement_07_weekly_idiosyncratic_momentum_risk_horse_race_v0.md`

source_paper:

- local_pdf: `ep6/papers/07_horse_race_weekly_idiosyncratic_momentum_china_shi_zhou_2021_arxiv.pdf`
- title: `Horse race of weekly idiosyncratic momentum strategies with respect to various risk metrics: Evidence from the Chinese stock market`
- authors: `Huai-Long Shi, Wei-Xing Zhou`
- version: `arXiv:1910.13115v2`
- paper_date: `2022-10-08`
- paper_sample: `China A-share common stocks, 1997-01 to 2017-12`

primary_output_namespace: `ep6/outputs/r07_weekly_idiosyncratic_momentum_risk_horse_race_v0/`

authorization_scope:

```text
authorized_strategy_requirement = false
```

This requirement is a diagnostic replication contract only. It must not be interpreted as a live strategy, production allocator, or permission to trade long-short A-share books.

## 2. Research Positioning

This requirement replicates the paper's weekly **idiosyncratic momentum** (`IMOM`) horse-race idea under the local EP5 universe and data discipline.

The local research question is:

```text
Using the EP5 PIT mcap500 mainboard universe,
does weekly residual-return momentum outperform raw-return momentum,
and do IVOL / IMD risk filters improve the IMOM readout out of sample?
```

This is a replication diagnostic, not a strategy authorization.

The requirement does not attempt to replicate:

```text
full CSMAR stock universe
CSMAR Fama-French 5 factor residuals
CSMAR risk-free-rate excess returns
Baker-Wurgler sentiment index
IPO / closed-end fund discount sentiment inputs
paper's 1997-2017 historical sample
production short book or portfolio allocator
```

Because the local repository does not currently contain CSMAR daily FF5 factors or risk-free rates, this requirement is:

```text
paper-inspired local weekly IMOM horse-race diagnostic
not exact FF5 idiosyncratic momentum replication
```

Every final report under this requirement must include the caveat:

```text
local_residual_model_not_paper_FF5_equivalent
```

## 3. Paper Result To Reproduce Directionally

The paper's main setup:

```text
Data:
  CSMAR A-share common stocks, 1997-01 to 2017-12

Raw MOM:
  rank stocks by cumulative raw return over past J weeks

IMOM:
  estimate daily FF5 residual returns
  rank stocks by cumulative idiosyncratic return over past J weeks

Skip:
  one week between formation and holding

J:
  2, 3, 4, 8, 13, 26, 52 weeks

K:
  1, 2, 3, 4, 8, 13, 26, 52 weeks

Portfolio:
  equal-weight top decile minus bottom decile
```

Key paper readouts to reproduce directionally:

| Paper result | Directional target |
|:--|:--|
| raw weekly momentum | mostly contrarian in China after early sample |
| weekly IMOM | positive and significant across most J/K portfolios |
| strongest IMOM region | short formation / holding windows, especially J around 2-4 weeks and K around 1-4 weeks |
| idiosyncratic risk relation | most idiosyncratic risk metrics negatively related to future returns |
| strongest risk metrics | `IVOL` and `IMD` |
| best risk-adjusted IMOM variants | `IVOL-IMOM` and `IMD-IMOM`, especially under bivariate double sort |
| conditional performance | stronger in upside markets, high liquidity, and high sentiment states |

Local replication is not expected to match the paper's magnitudes because it uses a different universe, shorter local sample, and a market-model residual in place of CSMAR FF5 residuals. The target is to test whether the paper's ordering survives locally:

```text
IMOM better than raw MOM
IVOL / IMD risk-aware IMOM better than weaker risk metrics
short-horizon weekly windows stronger than long-horizon windows
```

## 4. EP5 Universe And Data Inheritance

The replication must inherit EP5's local universe and timing discipline:

| Component | Required path / value |
|:--|:--|
| Qlib provider | `data/qlib/cn_data_pit` |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` |
| PIT instrument map | `data/universe/pit_qlib_instrument_universe.csv` |
| PIT industry membership | `data/targets/pit_industry_membership.csv` |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` |
| Qlib instrument file | `data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt` |
| Market benchmark / residual benchmark | `SH000300` |
| Market benchmark feature directory | `data/qlib/cn_data_pit/features/sh000300` |
| Provider load end | `2026-04-30` |

The universe is:

```text
PIT mcap500 mainboard universe as of each weekly signal date.
```

Constituent eligibility on each weekly signal date must require:

1. instrument is a PIT universe member as of the signal date;
2. instrument has enough daily close history for the relevant J window;
3. instrument has enough as-of observations for residual estimation and risk metrics;
4. instrument has enough as-of observations to compute the relevant signal value;
5. no stock outside the PIT universe may enter any portfolio;
6. all joins must be keyed by `date + instrument`.

Forward holding-period price availability must not be used in signal-date eligibility, ranking, or leg assignment. Future label availability is evaluated only after a portfolio is fixed and must be reported separately with:

```text
signal_eligibility_status
holding_label_status
assigned_leg_count
label_evaluable_leg_count
```

The universe is not the old `selected` 36-stock pool and not the static `mcap500_mainboard_20251231` Explore1 universe.

## 5. Local Data Availability Contract

Local data scan as of this requirement:

| Local source | Available fields |
|:--|:--|
| `data/qlib/cn_data_pit/features/*` | `open`, `close`, `high`, `low`, `volume`, `money`, `factor` |
| `data/universe/pit_mcap500_mainboard_daily.csv` | PIT membership, `total_share`, `market_cap_asof_T`, listing/status metadata |
| `data/targets/pit_industry_membership.csv` | PIT industry membership |
| `data/qlib/cn_data_pit/features/sh000300` / `data/targets/target_history.csv` | SH000300 index OHLCV |

Local data scan did not find:

```text
daily CSMAR FF3 / FF5 factor returns
daily risk-free rate
Baker-Wurgler sentiment inputs
IPO count and first-day IPO returns
closed-end fund discount
dividend premium
equity issuance share
```

The run must create a local data availability manifest:

`r07_input_availability_manifest.csv`

Required columns:

```text
input_id
paper_required_input
local_source
availability_status
replication_action
local_proxy_id
asof_policy
coverage_train_weeks
coverage_validation_weeks
coverage_robustness_weeks
block_reason
```

Allowed `availability_status` values:

```text
available_full
available_partial
missing_required_factor_source
missing_required_sentiment_source
missing_required_price_fields
missing_asof_timestamp
blocked_not_reproducible
```

Allowed `replication_action` values:

```text
retain
retain_local_proxy
remove
diagnostic_only
```

Mandatory availability decisions:

| Paper input | Local action | Reason |
|:--|:--|:--|
| raw stock returns | `retain` | provider close available |
| FF5 residual returns | `retain_local_proxy` | replace with local market-model residual |
| idiosyncratic risk metrics | `retain_local_proxy` | compute from local residual returns |
| market state | `retain_local_proxy` | compute from SH000300 cumulative return |
| liquidity state | `retain_local_proxy` | compute local Amihud aggregate from return and `money` |
| sentiment state | `remove` | required BW sentiment inputs unavailable locally |

Local price-adjustment contract:

```text
price_adjustment_mode = provider_ohlc_already_adjusted
primary_return_price = close from Qlib provider
do_not_reapply_factor_day_bin_to_ohlc = true
```

The local `factor` field may be used only as an audit field to confirm provider lineage. It must not be multiplied into OHLC prices in this requirement.

## 6. Weekly Calendar And Sample Split

Weekly endpoints must be derived from the local trading calendar:

```text
calendar_week_id = ISO week whose calendar Friday is the week anchor
candidate_week_trading_days =
  all local trading-calendar days from Monday through Friday of calendar_week_id

week_end W_t =
  max(candidate_week_trading_days) if candidate_week_trading_day_count > 0
  else null

skip week if candidate_week_trading_day_count <= 2

weekly_return_{i,t} =
  close_{i,W_t} / close_{i,W_{t-1_retained}} - 1
```

If Friday is not a trading day, `W_t` rolls back to the last local trading day in that Monday-Friday calendar week. If a week is skipped, the next retained week uses the most recent previous retained `W_{t-1_retained}` as the return denominator. The weekly calendar artifact must record:

```text
calendar_week_id
calendar_friday
candidate_week_trading_day_count
week_end
week_retained
skip_reason
previous_retained_week_end
```

Formation and holding must follow the paper's one-week skip:

```text
formation window for signal t:
  weeks t-J-1 through t-2

skip week:
  week t-1

holding window:
  weeks t through t+K-1
```

Portfolio construction for holding week `t` may only use data available no later than `W_{t-1}`.

The local evaluation split is:

| Split | Calendar window | Notes |
|:--|:--|:--|
| warmup | `2017-01-03` to first complete signal date | used only for residual/risk/formation history |
| train | `2018-07-01` to `2021-12-31` | nominal train window; cell-specific evaluable start may be later |
| validation | `2022-01-01` to `2023-12-31` | primary out-of-sample decision window |
| robustness | `2024-01-01` to `2025-12-31` | post-validation robustness window |

Long formation windows may become evaluable after the nominal train start. In particular, `J=52` requires both a 52-week residual signal window and a preceding 130-trading-day residual beta window. The implementation must not backfill or relax history requirements to force train-start availability. Instead, it must compute and publish:

```text
first_evaluable_signal_week_by_J
first_evaluable_portfolio_week_by_JK
effective_split_start_by_JK
train_weeks_lost_to_warmup_by_JK
```

If `J=52` or any other canonical cell first becomes evaluable after `2018-07-01`, that is an expected local-sample constraint and must be recorded in `r07_validation_manifest.json`, not treated as an implementation failure.

Split assignment is based on the first week of the holding window. If a J/K portfolio cannot complete the full holding window before provider end, mark:

```text
holding_status = blocked_incomplete_future_return_label
```

and exclude that portfolio-week from metrics. Do not impute missing holding returns.

For all other missing holding labels, the implementation must preserve the already assigned portfolio membership and then mark the affected instrument or portfolio-week after the fact:

```text
holding_label_status = complete | missing_provider_price | delisted_or_untradable | blocked_incomplete_future_return_label
```

No future label status may change the signal-date universe, rank order, bucket assignment, or long/short leg membership.

## 7. Local Idiosyncratic Return Model

The paper uses daily FF5 residuals. This local requirement freezes a simpler model before any validation returns are observed:

```text
local_residual_model_id = market_model_sh000300_ols_v0
```

The local residual is a **market-model residual**, not a full paper-equivalent FF5 idiosyncratic return. Artifacts may use the shorthand `IMOM`, but the run manifest and final report must also state:

```text
local_imom_interpretation = market_residual_momentum_not_ff5_idiosyncratic_momentum
```

Daily residuals are generated point-in-time. For each stock `i` and residual date `d`, estimate a rolling daily market model using only daily returns before `d`:

```text
r_{i,d} = alpha_i + beta_i * r_{mkt,d} + epsilon_{i,d}
```

where:

```text
r_{i,d} = close_{i,d} / close_{i,d-1} - 1
r_{mkt,d} = close_{SH000300,d} / close_{SH000300,d-1} - 1
```

The OLS estimation window is:

```text
residual_beta_window_for_date_d:
  130 trading days ending at d-1
```

The residual for date `d` is then computed as:

```text
epsilon_{i,d} = r_{i,d} - alpha_hat_{i,d-1} - beta_hat_{i,d-1} * r_{mkt,d}
```

Because `r_{i,d}` is known only after close on `d`, a residual can enter a signal for holding week `t` only if `d` is no later than the final trading day of week `t-2`.

Valid paired observations for beta estimation and residual generation are defined as:

```text
valid_stock_return_day =
  close_{i,d} is finite
  close_{i,d-1} is finite
  volume_{i,d} > 0
  money_{i,d} > 0

valid_market_return_day =
  close_{SH000300,d} is finite
  close_{SH000300,d-1} is finite

valid_paired_observation =
  valid_stock_return_day and valid_market_return_day
```

Suspended or non-trading stock days are excluded from the OLS sample and residual signal window. They must not be filled with zero returns. New stocks with fewer than the required valid paired observations in the fixed 130-trading-day beta window are ineligible for that residual date; expanding or shortened beta windows are not allowed.

`market_return_variance` is evaluated only on the valid paired observations retained inside the same fixed 130-trading-day beta window.

Risk-free adjustment is omitted because no local daily risk-free source is available. The run manifest must record:

```text
risk_free_mode = omitted_missing_local_source
```

Minimum residual-estimation coverage:

```text
lookback_days_for_residual_beta = 130 trading days
min_valid_days_for_residual_beta = 90
lookback_days_for_risk_metrics = 130 trading days
min_valid_residual_days_for_risk_metrics = 90
min_valid_residual_days_for_J_signal = max(10, ceil(0.60 * J * 5))
market_return_variance over valid paired observations > 0
```

The primary IMOM signal uses the daily residuals from the local market model. A diagnostic variant may also report raw market-adjusted returns:

```text
ret_minus_mkt_{i,d} = r_{i,d} - r_{mkt,d}
```

but this diagnostic may not replace the primary residual model unless a later requirement explicitly changes the residual model.

## 8. Signal Definitions

Canonical J values:

```text
2, 3, 4, 8, 13, 26, 52 weeks
```

Canonical K values:

```text
1, 2, 3, 4, 8, 13, 26, 52 weeks
```

Raw momentum signal:

```text
MOM_{i,t,J} =
  product over weeks u = t-J-1 through t-2 of (1 + weekly_return_{i,u}) - 1
```

Local idiosyncratic momentum signal:

```text
IMOM_{i,t,J} =
  product over trading days d in weeks t-J-1 through t-2 of (1 + epsilon_{i,d}) - 1
```

Primary short-horizon cluster:

```text
J in {2, 3, 4, 8, 13}
K in {1, 2, 3, 4}
```

Long-horizon diagnostics:

```text
J in {26, 52}
K in {8, 13, 26, 52}
```

No J/K subset may be selected after validation returns are observed. The final report may highlight the paper's short-horizon cluster, but it must still publish all canonical J/K tables.

## 9. Idiosyncratic Risk Metrics

Risk metrics are computed from local daily residual returns over the past 130 trading days ending no later than the final trading day of week `t-2`.

Retained primary risk metrics:

| metric_id | Local definition | Action |
|:--|:--|:--|
| `IVOL` | standard deviation of daily residual returns | primary |
| `IMD` | maximum drawdown of cumulative residual-return curve | primary |

Retained diagnostic risk metrics:

| metric_id | Local definition | Action |
|:--|:--|:--|
| `ISKEW` | skewness of daily residual returns | diagnostic |
| `IKURT` | kurtosis of daily residual returns | diagnostic |
| `IES5` | expected shortfall of residual returns at 5% left tail | diagnostic |
| `IVAR5` | VaR of residual returns at 5% left tail | diagnostic |
| `IES1` | expected shortfall of residual returns at 1% left tail | diagnostic |
| `IVAR1` | VaR of residual returns at 1% left tail | diagnostic |

Metric sign convention:

```text
IVOL, IMD, IES, IVAR are positive risk magnitudes.
higher value means higher idiosyncratic risk.
ISKEW and IKURT keep their natural statistical sign/value.
```

The risk-only portfolio buys the lowest-risk decile and shorts the highest-risk decile. If a metric has no stable economic ordering, such as `IKURT`, it remains diagnostic and cannot be used for primary conclusions.

## 10. Portfolio Construction Rules

For each signal week `t`, J, K, and portfolio family:

1. Build eligible stock universe from EP5 PIT universe as of `W_{t-1}`.
2. Drop instruments only for insufficient as-of formation, residual, risk, or signal data.
3. Sort by the relevant signal using deterministic tie rules:

```text
sort by signal_value ascending, instrument_id ascending
split into 10 near-equal decile buckets
```

4. Construct equal-weight decile portfolios.
5. Compute calendar-time overlapping portfolio returns for K-week holding windows.

Do not drop an instrument at step 2 because its future K-week holding label is missing. Missing holding labels are handled after portfolio assignment through `holding_label_status` and label-evaluable coverage metrics.

Primary long-short return conventions:

```text
raw_mom_return = winner_decile_return - loser_decile_return
raw_contrarian_return = loser_decile_return - winner_decile_return

imom_return = high_IMOM_decile_return - low_IMOM_decile_return
risk_only_return = low_risk_decile_return - high_risk_decile_return
```

The paper reports raw momentum in a way that highlights contrarian effects. This local requirement stores the raw W-minus-L series and may show the contrarian L-minus-W view only as its deterministic sign flip:

```text
raw_mom_W_minus_L
raw_contrarian_L_minus_W = -raw_mom_W_minus_L
```

Bivariate risk-adjusted IMOM is the primary risk-horse-race test. To keep the local PIT mcap500 sample evaluable, the primary local bivariate sort uses independent 5 x 5 buckets, not decile x decile intersections:

```text
bivariate_sort_bucket_count = 5

long leg:
  intersection of highest IMOM quintile and lowest risk quintile

short leg:
  intersection of lowest IMOM quintile and highest risk quintile

risk_adjusted_imom_return:
  long_leg_return - short_leg_return
```

The paper-style decile x decile intersection may be reported as a diagnostic only if both legs satisfy coverage. It may not replace the primary 5 x 5 bivariate decision.

Direct risk-adjusted IMOM is diagnostic only:

```text
direct_adjusted_signal = IMOM / risk_metric
```

Direct adjustment is allowed only for strictly positive risk metrics:

```text
IVOL, IMD, IES5, IVAR5, IES1, IVAR1
```

It is not allowed for `ISKEW` because negative skewness values create sorting ambiguity.

Minimum portfolio coverage:

```text
signal_eligible_instrument_count >= 120
univariate_decile_count_min >= 10
bivariate_sort_bucket_count = 5
bivariate_intersection_count_min >= 5 per assigned leg
label_evaluable_leg_count_min >= 3 per leg
label_evaluable_leg_share_min >= 0.60 per assigned leg
```

For bivariate portfolios, if either the long-leg or short-leg intersection has fewer than 5 assigned instruments, the entire portfolio-week is blocked. There is no fallback to a looser bucket, alternate metric, or direct-adjusted signal.

If a portfolio-week fails coverage, set:

```text
portfolio_week_status = blocked_insufficient_portfolio_coverage
```

Coverage failures after leg assignment must not rewrite the original signal membership. They only determine whether that portfolio-week contributes to return metrics.

The implementation must report block counts separately by split, family, J, K, and block reason:

```text
assigned_intersection_too_small
label_evaluable_leg_count_too_small
label_evaluable_leg_share_too_low
insufficient_signal_eligible_universe
```

## 11. Cost And Executability Diagnostics

Paper-style replication must report gross returns first. Because weekly long-short books are reconstructed from stock constituents, after-cost diagnostics are mandatory unless the run is data-blocked before portfolio construction.

EP5-style transaction-cost assumptions:

```text
buy_cost_bps = 30
sell_cost_bps = 80
round_trip_cost_bps = 110
execution_mode = weekly_stock_constituent_replay_after_cost_mode
drift_adjusted_weights_reported = false by default
```

Overlapping K-week portfolios must be replayed through explicit vintage accounting:

```text
vintage_signal_week = s
vintage_holding_weeks = s through s+K-1
active_vintages_for_calendar_week h =
  all vintages s where h is in [s, s+K-1]

calendar_week_weight_vector_h =
  equal-weight average of active vintage target weight vectors
```

Each vintage target weight vector is equal-weight inside its assigned long and short legs. The combined calendar-week weight vector is rebalanced at the close immediately before the holding week starts. If fewer than K vintages are active because the sample is warming up, average over the active vintages and record `active_vintage_count`.

For each calendar-week replayed portfolio:

```text
buy_turnover_t =
  sum positive changes from previous combined signed stock weights to current combined signed stock weights

sell_turnover_t =
  sum absolute negative changes from previous combined signed stock weights to current combined signed stock weights

first_active_week_previous_weight = 0

after_cost_return_t =
  gross_return_t
  - buy_turnover_t * 30bps
  - sell_turnover_t * 80bps
```

Turnover is computed from target combined weekly weights, not from a later optimized allocator. Return-drift-adjusted weights are optional diagnostic output only if `drift_adjusted_weights_reported` is explicitly frozen in `r07_weekly_imom_horse_race_v0.yaml` before any validation or robustness metrics are computed. Even when reported, drift-adjusted weights must not replace target-weight turnover as the primary after-cost series.

The report must explicitly separate:

```text
gross paper-style diagnostic
after-cost executability diagnostic
long-leg return
short-leg return
```

The final report must not assume shorting is freely available in A shares. Any positive long-short result remains diagnostic unless a later requirement defines a feasible long-only or hedge-instrument implementation.

## 12. Conditional State Diagnostics

Market state diagnostics are retained:

```text
upside_market_26w:
  cumulative SH000300 return over prior 26 weeks > 0

downside_market_26w:
  cumulative SH000300 return over prior 26 weeks <= 0

upside_market_52w:
  cumulative SH000300 return over prior 52 weeks > 0

downside_market_52w:
  cumulative SH000300 return over prior 52 weeks <= 0
```

Liquidity diagnostics are retained with local Amihud aggregate:

```text
ILLIQ_{i,d} = abs(r_{i,d}) / money_{i,d}
money_unit_assumed = CNY

liquidity_state_window =
  skip week t-1 plus the 3 retained weeks before skip week t-1

AILLIQ_signal_t =
  equal-weight mean over signal-eligible stocks and valid trading days in liquidity_state_window

high_liquidity:
  AILLIQ_signal_t below train-only median

low_liquidity:
  AILLIQ_signal_t above train-only median

extreme_high_liquidity:
  AILLIQ_signal_t below train-only 20th percentile

extreme_low_liquidity:
  AILLIQ_signal_t above train-only 80th percentile
```

The train-only liquidity thresholds are computed from the train split's weekly `AILLIQ_signal_t` time series. Validation and robustness weeks compare their current weekly cross-sectional aggregate `AILLIQ_signal_t` against those frozen train-period weekly thresholds. Full-sample thresholds are not allowed.

The run manifest must record `money_unit_assumed = CNY`. The report bundle must also include an audit table or manifest field with `money` descriptive statistics for the first 10 sampled trading dates used in this diagnostic:

```text
sample_date
instrument_count
money_min
money_p25
money_median
money_p75
money_max
```

Sentiment diagnostics are blocked:

```text
sentiment_status = blocked_missing_Baker_Wurgler_inputs
```

Do not replace Baker-Wurgler sentiment with turnover alone in this requirement. Turnover already enters local liquidity and risk diagnostics.

## 13. Required Artifacts

The implementation must create:

```text
ep6/outputs/r07_weekly_idiosyncratic_momentum_risk_horse_race_v0/
  configs/
    r07_weekly_imom_horse_race_v0.yaml
  manifests/
    r07_input_availability_manifest.csv
    r07_weekly_imom_run_manifest.json
    r07_environment_snapshot.json
    r07_validation_manifest.json
    r07_money_unit_audit.csv
  weekly/
    r07_weekly_calendar.csv
    r07_weekly_stock_returns.parquet
    r07_weekly_signal_eligibility_audit.csv
  residuals/
    r07_residual_model_manifest.csv
    r07_weekly_residual_signal_panel.parquet
  signals/
    r07_mom_signal_panel.parquet
    r07_imom_signal_panel.parquet
    r07_risk_metric_panel.parquet
    r07_bivariate_imom_risk_signal_panel.parquet
  returns/
    r07_raw_mom_jk_returns.csv
    r07_imom_jk_returns.csv
    r07_risk_only_jk_returns.csv
    r07_bivariate_risk_adjusted_imom_jk_returns.csv
    r07_direct_risk_adjusted_imom_jk_returns.csv
    r07_portfolio_week_label_status.csv
  reports/
    r07_jk_summary_raw_mom.csv
    r07_jk_summary_imom.csv
    r07_jk_summary_risk_only.csv
    r07_jk_summary_bivariate_risk_adjusted_imom.csv
    r07_metric_horse_race_summary.csv
    r07_conditional_state_summary.csv
    r07_gate_decision_summary.csv
    r07_final_report.md
```

Parquet may be replaced by CSV only if the implementation records the reason in `r07_weekly_imom_run_manifest.json`.

`r07_environment_snapshot.json` must include:

```text
python_version
platform
executable
package_freeze
uv_lock_hash_if_available
git_commit_or_worktree_status
created_at
```

## 14. Required Metrics

Each J/K portfolio family must report by split:

```text
week_count
active_portfolio_count
active_vintage_count_mean
signal_eligible_instrument_count_mean
signal_eligible_instrument_count_min
assigned_long_leg_count_mean
assigned_short_leg_count_mean
label_evaluable_long_leg_count_mean
label_evaluable_short_leg_count_mean
label_evaluable_long_leg_share_mean
label_evaluable_short_leg_share_mean
weekly_mean_return
annualized_mean_return = weekly_mean_return * 52
weekly_volatility
annualized_volatility = weekly_volatility * sqrt(52)
sharpe_ratio
t_stat_weekly_mean_newey_west
newey_west_lag_used = K
positive_week_share
max_drawdown
mean_buy_turnover
mean_sell_turnover
after_cost_weekly_mean_return
after_cost_annualized_mean_return
after_cost_weekly_volatility
after_cost_t_stat_newey_west
after_cost_sharpe_ratio
long_leg_weekly_mean_return
short_leg_weekly_mean_return
```

Primary summary rows:

```text
raw_mom_W_minus_L
raw_contrarian_L_minus_W = -raw_mom_W_minus_L
imom
IVOL_risk_only
IMD_risk_only
IVOL_IMOM_bivariate
IMD_IMOM_bivariate
```

`raw_mom_W_minus_L` is the stored raw-return series. `raw_contrarian_L_minus_W` is a derived sign-flipped reporting view used only to make the paper's reversal interpretation explicit; it must not be treated as an independent portfolio family.

Diagnostic summary rows:

```text
ISKEW_risk_only
IKURT_risk_only
IES5_risk_only
IVAR5_risk_only
IES1_risk_only
IVAR1_risk_only
IES5_IMOM_bivariate
IVAR5_IMOM_bivariate
IES1_IMOM_bivariate
IVAR1_IMOM_bivariate
direct_adjusted_IMOM variants
```

The final report must include a compact paper-reference comparison table using the directional claims listed in Section 3:

| Paper claim | Local test | Supported locally? |
|:--|:--|:--|
| raw weekly MOM is mostly contrarian | raw W-L table; negative W-L implies L-W reversal | yes/no/mixed |
| IMOM is positive and stronger than raw-return directions | IMOM vs raw W-L and derived raw L-W short-cluster tables | yes/no/mixed |
| IVOL and IMD are strongest risk metrics | horse-race summary | yes/no/mixed |
| bivariate risk-adjusted IMOM improves results | IVOL/IMD-IMOM vs pure IMOM | yes/no/mixed |
| upside market strengthens IMOM | conditional SH000300 state table | yes/no/mixed |
| high liquidity strengthens IMOM | conditional local Amihud table | yes/no/mixed |
| high sentiment strengthens IMOM | blocked | unavailable locally |

## 15. Validation Gates

This requirement has no strategy-authorization gate. It has only diagnostic gates.

Cluster aggregation is fixed:

```text
short_cluster = J in {2,3,4,8,13}, K in {1,2,3,4}
short_cluster_cell_count = 20

short_cluster_family_mean =
  equal-weight mean of weekly_mean_return across evaluable short-cluster J/K cells

short_cluster_family_after_cost_mean =
  equal-weight mean of after_cost_weekly_mean_return across evaluable short-cluster J/K cells

short_cluster_raw_best_direction_mean =
  max(short_cluster_raw_mom_W_minus_L_mean,
      short_cluster_raw_contrarian_L_minus_W_mean)
```

Data sufficiency gate:

```text
validation_evaluable_short_cluster_cell_count >= 16
robustness_evaluable_short_cluster_cell_count >= 16
validation_short_cluster_min_week_count_per_cell >= 52
robustness_short_cluster_min_week_count_per_cell >= 52
```

Primary IMOM diagnostic gate:

```text
validation_short_cluster_imom_mean > validation_short_cluster_raw_best_direction_mean
validation_short_cluster_imom_mean > 0
validation_short_cluster_imom_t_stat_newey_west > 0

robustness_short_cluster_imom_mean > 0
robustness_short_cluster_imom_t_stat_newey_west > 0
```

Risk horse-race gate requires one fixed metric to pass both splits. The implementation may evaluate `IVOL` and `IMD`, but it must not use different winning metrics for validation and robustness:

```text
exists metric_id in {IVOL, IMD} such that:

  validation_short_cluster_metric_id_IMOM_bivariate_mean
    >= validation_short_cluster_imom_mean

  robustness_short_cluster_metric_id_IMOM_bivariate_mean
    >= robustness_short_cluster_imom_mean
```

After-cost diagnostic guard:

```text
validation_short_cluster_imom_after_cost_mean > 0
validation_short_cluster_imom_after_cost_t_stat_newey_west > 0
robustness_short_cluster_imom_after_cost_mean > 0
robustness_short_cluster_imom_after_cost_t_stat_newey_west > 0
```

First-match final decision priority:

```text
1. If required local inputs or sample coverage are unavailable:
   ep6_weekly_imom_data_blocked

2. Else if portfolio replay, overlapping vintage accounting, or after-cost replay cannot be produced:
   ep6_weekly_imom_execution_replay_blocked

3. Else if data sufficiency gate fails:
   ep6_weekly_imom_sample_insufficient

4. Else if primary IMOM validation gate fails:
   ep6_weekly_imom_local_proxy_not_supported

5. Else if validation passes but robustness IMOM mean or t-stat sign fails:
   ep6_weekly_imom_local_proxy_validation_only_not_robust

6. Else if primary IMOM gates pass but no single IVOL or IMD bivariate metric passes both splits:
   ep6_weekly_imom_positive_risk_filter_not_supported

7. Else if gross gates pass but after-cost guard fails:
   ep6_weekly_imom_gross_positive_after_cost_not_supported

8. Else:
   ep6_weekly_imom_local_proxy_positive_diagnostic_only
```

Weak or mixed support may be used only as a report interpretation label, not as the machine-readable final decision. The risk-filter weak-support label applies only when the same metric in `{IVOL, IMD}` improves IMOM in validation and has the same positive improvement sign in robustness, but fails the full strong-support gate.

```text
ep6_weekly_imom_local_proxy_mixed_positive_diagnostic
risk_filter_weak_support_same_metric_validation_positive_robustness_same_sign
```

Even if all diagnostic gates pass, the final report must state:

```text
authorized_strategy_requirement = false
```

## 16. Reproducibility Rules

All configuration choices must be frozen in:

```text
configs/r07_weekly_imom_horse_race_v0.yaml
```

before validation and robustness metrics are computed.

The run manifest must record:

```text
git_commit_or_worktree_status
created_at
python_version
qlib_provider_path
universe_path
calendar_path
benchmark_feature_dir
benchmark_feature_dir_hash
price_adjustment_mode
residual_model_id
local_imom_interpretation
risk_free_mode
residual_beta_window
risk_metric_window
valid_return_day_policy
first_evaluable_signal_week_by_J
first_evaluable_portfolio_week_by_JK
effective_split_start_by_JK
train_weeks_lost_to_warmup_by_JK
J_values
K_values
split_boundaries
bivariate_sort_bucket_count
weekly_calendar_policy
cluster_aggregation_policy
liquidity_threshold_policy
liquidity_state_window
money_unit_assumed
cost_assumptions
overlapping_vintage_accounting_policy
drift_adjusted_weights_reported
label_availability_policy
newey_west_lag_policy
raw_contrarian_derivation_policy
blocked_inputs
final_decision
```

No rule may be tuned after observing validation or robustness returns:

```text
J/K subset
residual model
risk metric sign convention
winsorization
minimum coverage thresholds
cost assumptions
split boundaries
bivariate sort bucket count
liquidity state thresholds
liquidity state window
cluster aggregation
drift-adjusted diagnostic inclusion
Newey-West lag policy
```

If a bug fix changes historical metrics, the implementation must regenerate all downstream artifacts and document the change in `r07_validation_manifest.json`.

# R05b Sleeve Allocator / Exposure Composition Diagnostic Final Report

R05b does not discover alpha.
R05b does not reinterpret R04e union as alpha.
R05b does not rescue R05 Preflight failed primitives.
R05b only tests whether failed / relative-improvement pools have limited sleeve value.

## 结论

本次 R05b 的最终决策是 `r05b_risk_on_full_exposure_failed`，不是因为上游 artifact 或 validator 失败，而是因为 validation 期的 `risk_on` 全仓 primary sleeve 本身不赚钱，触发了 §8 的 hard kill。具体证据是 validation 期 `risk_on_full_exposure_period_return = -7.91%`，`risk_on_full_exposure_daily_mean = -0.07%`。

这意味着 market-state allocator 的核心前提没有成立：即使只在模型判定为 `risk_on` 的日期给 R04e primary sleeve 满 exposure，primary path 仍然是负收益。后续 cash allocator 虽然降低了回撤和左尾，但它没有把 validation 期组合收益变成正数，也没有保住足够的右尾收益，因此不能构成 diagnostic pass。

## 上游状态

- R04e validation: passed / r04e_union_not_viable_validation
- R05 Preflight validation: passed / r05_preflight_stop_no_absolute_floor
- R05 Preflight candidate pass count: 0
- R05a status: abandoned_preflight_blocked

这些状态满足 R05b 的进入条件：R04e 已经是 portfolio-level not viable，R05 Preflight 没有 standalone candidate pass，R05a 已被 preflight-blocked。因此本报告解释的是 sleeve allocator 诊断失败，而不是上游状态漂移。

## 决策结果

- final_decision: `r05b_risk_on_full_exposure_failed`
- selected_allocator_policy_id: ``
- terminal_stop_flag: `True`
- allowed_next_requirement: `ep5_escape_hatch_only`
- blocking_reason: `risk_on_full_exposure_validation_net_not_positive`

## 失败原因 1: Risk-on full exposure 先验失败

R05b 要求 allocator 不能只是靠降 exposure 避开亏损；如果 `risk_on` 日期里的 full-exposure primary sleeve 本身不赚钱，则不能把 cash allocator 解释为有效的组合层修复。这个 hard kill 在 validation 期被触发。

| split      |   risk_on_day_count | risk_on_day_share   | full_exposure_primary_period_return   | risk_on_full_exposure_period_return   | risk_on_full_exposure_daily_mean   | risk_on_full_exposure_gate_status   | blocking_reason                    |
|:-----------|--------------------:|:--------------------|:--------------------------------------|:--------------------------------------|:-----------------------------------|:------------------------------------|:-----------------------------------|
| train      |                 403 | 36.74%              | 39.89%                                | 18.50%                                | 0.05%                              | pass                                |                                    |
| validation |                 104 | 21.49%              | -22.81%                               | -7.91%                                | -0.07%                             | fail                                | risk_on_full_exposure_not_positive |
| robustness |                 207 | 42.68%              | 37.09%                                | 17.88%                                | 0.08%                              | pass                                |                                    |

在 validation 期，`risk_on` 共有 104 个交易日，占 21.49%。但这些日期上 full-exposure primary 的累计收益是 -7.91%，日均收益是 -0.07%。这不是单纯 exposure 太高的问题，而是 `risk_on` 状态没有筛出正期望 primary exposure。

对比来看，train 期同一口径为 18.50%，robustness 期为 17.88%。validation 的失败说明这个 market-state rule 在关键验证区间不稳定，robustness 的好表现按需求只能作为只读信息，不能救回 validation failure。

## 失败原因 2: Cash allocator 降低损失，但没有通过 validation gate

`market_state_cash_allocator_v1` 的确降低了风险暴露：validation 平均 gross exposure 为 46.18%，cash-only day share 为 29.13%，没有触发 mostly-cash illusion 阈值。它也改善了左尾和回撤：monthly p10 delta 为 2.26%，max drawdown delta 为 9.64%。

但是它仍然没有满足 pass 条件：validation period return 仍为 -14.68%，daily mean 为 -0.03%。同时 right-tail retention 只有 0.4622，低于 validation 阈值 0.60，`right_tail_gate_status = right_tail_fail`。因此它只是把亏损压小，并没有形成可通过 gate 的正收益 allocator。

## 失败原因 3: Secondary sleeve 没有形成有效激活样本

`market_state_cash_plus_basebreakout_secondary_v1` 在 validation 期被 `secondary_sleeve_insufficient_activation` 阻断。虽然 base breakout secondary sleeve 在很多日期内部有 active positions，但 policy 只有在 `market_state == risk_on` 且 primary active_count < 20 且 secondary active_count > 0 时才允许占用 20% sleeve。这个三条件交集在 validation 期为 0 天。

| split      |   validation_trading_day_count |   risk_on_day_count |   primary_active_lt20_day_count |   secondary_active_day_count |   secondary_activation_day_count | secondary_activation_day_share   |   activation_day_count_min | activation_day_share_min   | secondary_activation_status              | robustness_secondary_activation_status              |
|:-----------|-------------------------------:|--------------------:|--------------------------------:|-----------------------------:|---------------------------------:|:---------------------------------|---------------------------:|:---------------------------|:-----------------------------------------|:----------------------------------------------------|
| validation |                            484 |                 104 |                               2 |                          411 |                                0 | 0.00%                            |                         20 | 2.00%                      | secondary_sleeve_insufficient_activation |                                                     |
| robustness |                            485 |                 207 |                               1 |                          440 |                                0 | 0.00%                            |                         20 | 2.00%                      |                                          | robustness_secondary_sleeve_insufficient_activation |

具体看 validation：risk_on 日期 104 天，primary active_count < 20 的日期只有 2 天，secondary active 日期 411 天，但三者交集 `secondary_activation_day_count = 0`。这低于要求的 20 天和 2% active share。robustness 期同样是 0 天，因此 secondary sleeve 没有证明可复用。

## 失败原因 4: 不是 replay 或数据完整性导致的假失败

R05 Preflight-derived sleeves 的 replay censor audit 通过，base breakout validation complete share 为 95.89%，lookahead censored event count 为 0。Diagnostic sleeves 也满足 complete share 阈值。因此失败主要来自 allocator/gate 经济含义，而不是 frozen event replay 不完整。

| sleeve_id                          | candidate_id                               |   source_event_count |   complete_replay_event_count | complete_replay_event_share   |   lookahead_censored_event_count | replay_censor_status   |
|:-----------------------------------|:-------------------------------------------|---------------------:|------------------------------:|:------------------------------|---------------------------------:|:-----------------------|
| base_breakout_vcp_secondary_sleeve | base_breakout_vcp_preflight                |                   73 |                            70 | 95.89%                        |                                0 | pass                   |
| low_vol_uptrend_diagnostic_sleeve  | low_vol_uptrend_preflight                  |                  574 |                           553 | 96.34%                        |                                0 | pass                   |
| low_beta_low_vol_diagnostic_sleeve | cross_sectional_low_beta_low_vol_preflight |                  810 |                           776 | 95.80%                        |                                0 | pass                   |

## Validation Gate 细节

| policy                                           | gate_status                                      | validation_return   | daily_mean   | p10_delta   | drawdown_delta   | worst20d_delta   | avg_gross   | cash_only_share   | right_tail      |   right_tail_retention | blocking_reason                          |
|:-------------------------------------------------|:-------------------------------------------------|:--------------------|:-------------|:------------|:-----------------|:-----------------|:------------|:------------------|:----------------|-----------------------:|:-----------------------------------------|
| full_exposure_primary_baseline                   | baseline_reference_only                          | -22.81%             | -0.05%       | 0.00%       | 0.00%            | 0.00%            | 100.00%     | 0.00%             | right_tail_pass |                 1      |                                          |
| market_state_cash_allocator_v1                   | validation_fail                                  | -14.68%             | -0.03%       | 2.26%       | 9.64%            | 1.62%            | 46.18%      | 29.13%            | right_tail_fail |                 0.4622 | validation_gate_condition_failed         |
| market_state_cash_plus_basebreakout_secondary_v1 | blocked_secondary_sleeve_insufficient_activation | -14.68%             | -0.03%       | 2.26%       | 9.64%            | 1.62%            | 46.18%      | 29.13%            | right_tail_fail |                 0.4622 | secondary_sleeve_insufficient_activation |

表中可以看到：baseline 只是 reference，不参与 pass/fail；cash allocator 是 `validation_fail`；secondary policy 是 `blocked_secondary_sleeve_insufficient_activation`。两条 selectable policies 都没有通过 validation。

## Mostly-cash illusion 检查

本次失败不是因为 allocator 过度空仓。`market_state_cash_allocator_v1` 在 validation 期 average gross exposure 为 46.18%，高于 35% 下限；cash-only day share 为 29.13%，低于 65% 上限。也就是说，allocator 失败不是因为暴露过低，而是在足够暴露下仍没有正收益和右尾保留。

## Validation 期最差月份

下表列出 full exposure baseline 和 cash allocator 在 validation 期各自最差的月份。cash allocator 能缓解部分月份的损失，但不能改变整段 validation 为负的事实。

| view                           | month   | monthly_return   | full_exposure_primary_monthly_return   | monthly_return_delta_vs_full_exposure   | average_gross_exposure   | cash_only_day_share   |   risk_on_day_count |   risk_neutral_day_count |   risk_off_day_count |
|:-------------------------------|:--------|:-----------------|:---------------------------------------|:----------------------------------------|:-------------------------|:----------------------|--------------------:|-------------------------:|---------------------:|
| full_exposure_primary_baseline | 2022-01 | -12.74%          | -12.74%                                | 0.00%                                   | 100.00%                  | 0.00%                 |                   2 |                       17 |                    0 |
| full_exposure_primary_baseline | 2022-03 | -8.70%           | -8.70%                                 | 0.00%                                   | 100.00%                  | 0.00%                 |                   0 |                        3 |                   20 |
| full_exposure_primary_baseline | 2023-08 | -6.36%           | -6.36%                                 | 0.00%                                   | 100.00%                  | 0.00%                 |                   9 |                       14 |                    0 |
| full_exposure_primary_baseline | 2022-09 | -6.03%           | -6.03%                                 | 0.00%                                   | 100.00%                  | 0.00%                 |                   0 |                        6 |                   15 |
| full_exposure_primary_baseline | 2022-07 | -5.00%           | -5.00%                                 | 0.00%                                   | 100.00%                  | 0.00%                 |                  12 |                        9 |                    0 |
| full_exposure_primary_baseline | 2022-04 | -4.75%           | -4.75%                                 | 0.00%                                   | 100.00%                  | 0.00%                 |                   0 |                        0 |                   19 |
| market_state_cash_allocator_v1 | 2022-01 | -9.56%           | -12.74%                                | 3.18%                                   | 55.26%                   | 0.00%                 |                   2 |                       17 |                    0 |
| market_state_cash_allocator_v1 | 2022-07 | -5.15%           | -5.00%                                 | -0.15%                                  | 78.57%                   | 0.00%                 |                  12 |                        9 |                    0 |
| market_state_cash_allocator_v1 | 2023-08 | -4.81%           | -6.36%                                 | 1.56%                                   | 69.57%                   | 0.00%                 |                   9 |                       14 |                    0 |
| market_state_cash_allocator_v1 | 2023-05 | -2.15%           | -4.28%                                 | 2.13%                                   | 50.00%                   | 0.00%                 |                   0 |                       20 |                    0 |
| market_state_cash_allocator_v1 | 2022-12 | -2.10%           | -2.00%                                 | -0.10%                                  | 93.18%                   | 0.00%                 |                  19 |                        3 |                    0 |
| market_state_cash_allocator_v1 | 2023-11 | -1.46%           | -1.82%                                 | 0.35%                                   | 40.91%                   | 18.18%                |                   0 |                       18 |                    4 |

## Robustness 为什么不能救回

robustness 期 cash allocator period return 为 14.28%，right-tail 通过，平均 gross exposure 为 66.80%。但 requirement 明确规定 robustness 是 read-only guardrail，不能用 robustness 好表现反向选择或救回 validation failure。因此 robustness 只能说明该现象在后续区间有反弹，不能推翻 validation hard kill。

## 实验含义

R05b 原问题是：失败的 alpha pools 是否还能在 sleeve / exposure composition 层面产生有限诊断价值。结果显示，在当前 frozen market-state classifier、R04e primary path 和 R05 Preflight sleeves 下，答案是否定的：

- primary 的 `risk_on` exposure 在 validation 期不是正期望；
- cash allocator 主要减少亏损和回撤，但仍为负收益，右尾 retention 不足；
- base breakout secondary 的 activation 条件过窄，validation 和 robustness 都没有有效激活样本；
- replay 完整性和 lookahead audit 没有解释失败。

因此当前 R05b 不能支持继续做 R05c/R05d 的 sleeve variant。若要继续，需要进入 EP5，改变 universe、horizon、hedge leg、execution model 或问题 framing。

## 完整 Policy Summary

| allocator_policy_id                              | split      |   period_return |   daily_mean |   monthly_p10 |   monthly_p90 | right_tail_gate_mode       | right_tail_gate_status   |   absolute_p90_floor_min |   max_drawdown |   worst_20d_return |   average_gross_exposure |   cash_only_day_share |   right_tail_retention_vs_full_exposure | secondary_activation_status              | robustness_secondary_activation_status              | validation_gate_status                           | robustness_readonly_status   | blocking_reason                          |
|:-------------------------------------------------|:-----------|----------------:|-------------:|--------------:|--------------:|:---------------------------|:-------------------------|-------------------------:|---------------:|-------------------:|-------------------------:|----------------------:|----------------------------------------:|:-----------------------------------------|:----------------------------------------------------|:-------------------------------------------------|:-----------------------------|:-----------------------------------------|
| full_exposure_primary_baseline                   | validation |       -0.228052 | -0.000475786 |    -0.0626449 |     0.0608554 | retention_vs_full_exposure | right_tail_pass          |                     0.02 |       0.220946 |         -0.111806  |                 1        |             0         |                                1        | not_applicable                           | not_applicable                                      | baseline_reference_only                          | baseline_reference_only      |                                          |
| full_exposure_primary_baseline                   | robustness |        0.370857 |  0.000706747 |    -0.0310447 |     0.0653538 | retention_vs_full_exposure | right_tail_pass          |                     0.01 |       0.134801 |         -0.0773965 |                 1        |             0         |                                1        | not_applicable                           | not_applicable                                      | baseline_reference_only                          | baseline_reference_only      |                                          |
| market_state_cash_allocator_v1                   | validation |       -0.146839 | -0.000313036 |    -0.040085  |     0.0281294 | retention_vs_full_exposure | right_tail_fail          |                     0.02 |       0.124556 |         -0.0955735 |                 0.461777 |             0.291322  |                                0.462234 | not_applicable                           | not_applicable                                      | validation_fail                                  | robustness_readonly_pass     | validation_gate_condition_failed         |
| market_state_cash_allocator_v1                   | robustness |        0.142792 |  0.000298747 |    -0.027808  |     0.0401699 | retention_vs_full_exposure | right_tail_pass          |                     0.01 |       0.125295 |         -0.057976  |                 0.668041 |             0.0907216 |                                0.614653 | not_applicable                           | not_applicable                                      | validation_fail                                  | robustness_readonly_pass     | validation_gate_condition_failed         |
| market_state_cash_plus_basebreakout_secondary_v1 | validation |       -0.146839 | -0.000313036 |    -0.040085  |     0.0281294 | retention_vs_full_exposure | right_tail_fail          |                     0.02 |       0.124556 |         -0.0955735 |                 0.461777 |             0.291322  |                                0.462234 | secondary_sleeve_insufficient_activation | robustness_secondary_sleeve_insufficient_activation | blocked_secondary_sleeve_insufficient_activation | robustness_readonly_pass     | secondary_sleeve_insufficient_activation |
| market_state_cash_plus_basebreakout_secondary_v1 | robustness |        0.142792 |  0.000298747 |    -0.027808  |     0.0401699 | retention_vs_full_exposure | right_tail_pass          |                     0.01 |       0.125295 |         -0.057976  |                 0.668041 |             0.0907216 |                                0.614653 | secondary_sleeve_insufficient_activation | robustness_secondary_sleeve_insufficient_activation | blocked_secondary_sleeve_insufficient_activation | robustness_readonly_pass     | secondary_sleeve_insufficient_activation |

## Terminal Stop

EP4 terminated.
Do not create R05c/R05d sleeve variants.
Further work requires EP5 with a changed universe, horizon, hedge leg, execution model, or problem framing.

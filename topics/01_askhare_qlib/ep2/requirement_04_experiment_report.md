# EP2 Requirement 04 Holding / Exit Winner-Capture Extension 实验报告

生成日期：2026-05-09

本文汇总 Requirement 04 的实现状态、实验结果、失败原因、机制解释、已验证事实和当前推测。结论基于当前本地 artifacts：

- `ep2/requirement_04_holding_exit_winner_capture_extension.md`
- `ep2/configs/requirement_04_holding_exit_winner_capture_extension.yaml`
- `ep2/outputs/requirement_04_holding_exit_winner_capture_extension/`

## 1. 总体结论

Requirement 04 已完成实现和产出，但实验没有通过 promotion gates。

| 项目 | 结果 |
| --- | --- |
| validation_status | `failed_tail_risk` |
| next_phase_proceed_status | `failed_tail_risk` |
| recommendation | `reframe_EP2_as_risk_filter_overlay` |
| selected_requirement_04_schedule_id | 空，无 promoted schedule |
| gate_count | 70 |
| passed_gate_count | 59 |
| failed_gate_count | 11 |

核心结论：

1. R04 的 holding extension 确实提高了 validation big-winner strict capture。
2. 但所有 promotion-eligible schedule 都在 validation tail-risk gates 上失败。
3. 失败不是因为 turnover 或 concentration，而是因为延长持有后 `mean_after_cost_return`、`p05_after_cost_return` 和部分 schedule 的 `exposure_day_multiple` 不达标。
4. `R03_confirmed_H60` / `R03_confirmed_H120` 能抓到更多 +50% winner，但资金占用和左尾恶化过大。
5. `R03_confirmed_H20` / `R03_winner_state_hold_H120` 的资金占用较可控，但只多抓 1 个 winner，同时 p05 和 mean 仍轻微越过硬门槛。
6. 当前证据不支持把 EP2 升级为 big-winner holding system。更合理的下一步是 risk-filter overlay、partial-exit / profit-protection 研究，或把 EP2 定位为 short-horizon event sleeve。

## 2. 实现与输入边界

Requirement 04 作为 R03 schedule-extension phase 实现，只读取 R03 已冻结 schedule artifacts，不重新训练、不重新选择 R02 threshold、不修改 R01/R02/R03/BaseRate artifacts。

新增实现文件：

| 文件 | 作用 |
| --- | --- |
| `ep2/configs/requirement_04_holding_exit_winner_capture_extension.yaml` | R04 冻结合约、schedule matrix、gate、PIT authority 配置 |
| `ep2/scripts/requirement_04_holding_exit_winner_capture_extension_common.py` | R04 主实现、模拟、指标、selection、validator 公共逻辑 |
| `ep2/scripts/run_requirement_04_holding_exit_winner_capture_extension.py` | R04 runner CLI |
| `ep2/scripts/validate_requirement_04_holding_exit_winner_capture_extension.py` | R04 fail-closed validator CLI |

主要输出 artifacts：

| artifact | 行数 |
| --- | ---: |
| `requirement_04_schedule_action_panel.parquet` | 20025 |
| `requirement_04_exposure_daily_panel.parquet` | 160927 |
| `requirement_04_episode_schedule_summary.parquet` | 36660 |
| `requirement_04_winner_state_event_panel.parquet` | 2284 |
| `requirement_04_schedule_results.csv` | 45 |
| `requirement_04_schedule_comparison.csv` | 42 |
| `requirement_04_big_winner_capture_audit.csv` | 36660 |
| `requirement_04_diagnostic_counterfactuals.csv` | 150 |

## 3. PIT Target 与 Hash Scope

实现时发现 frozen `ep2_path_label_panel.parquet` 没有 50h120 / 100h240 target rows。按照 requirement fallback rule，R04 从 PIT OHLC 重新计算：

- `first_50pct_target_date`
- `first_100pct_target_date`

并扩大 PIT hash scope 到 `launch_effective_date + 240 trading days`。

| 字段 | 结果 |
| --- | --- |
| pit_price_hash_scope | `r03_instruments_and_dates_through_launch_plus_240_trading_days` |
| pit_price_hash_scope_start | 2017-11-01 |
| pit_price_hash_scope_end | 2026-04-30 |
| pit_price_hash_instrument_count | 313 |
| pit_price_hash_row_count | 410030 |

这意味着 R04 的 big-winner target 来源与 R02/R03 的 capture 逻辑一致，但 R04 显式记录了更宽的 PIT hash authority。

## 4. Baseline Replay 状态

`R03_original_H10` 被实现为 baseline-only replay，用于对照 R03 `hazard_probe_confirm_add_fast_fail`。

validation / robustness 的 hard reconciliation 均通过：

| split | episode_count | exposed_count | probe_rate | confirm_add_rate | mean_after_cost_return | p05_after_cost_return | strict capture |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | 532 | 104 | 0.195489 | 0.139098 | 0.008592 | -0.007543 | 0.046512 |
| robustness | 770 | 149 | 0.193506 | 0.142857 | 0.005769 | -0.018225 | 0.023622 |

有一个 train split 的 strict capture reconciliation row 失败：

```text
train R03_original_H10 r03_replay_strict_big_winner_capture_match
R04 value: 0.032432
R03 value: 0.043243
```

该行被标记为 non-hard，因为 requirement 只要求 validation / robustness 满足 R03 replay reconciliation。当前不影响 R04 contract status。

## 5. Promotion-Eligible Schedule Matrix

R04 的 promotion-eligible schedules：

| schedule_id | variant_id | 规则 |
| --- | --- | --- |
| `R03_confirmed_H20` | `h20` | confirm-add 后自然退出延长到 H20；未 confirm 的 probe 仍 H10 |
| `R03_confirmed_H60` | `h60` | confirm-add 后自然退出延长到 H60；未 confirm 的 probe 仍 H10 |
| `R03_confirmed_H120` | `h120` | confirm-add 后自然退出延长到 H120；未 confirm 的 probe 仍 H10 |
| `R03_winner_state_hold_H120` | `winner_state_base` | 正常 H20；满足 close-derived winner-state 后进入 H120 hold mode |

Baseline 与 diagnostics 不能 promotion：

- `R03_original_H10` 是 baseline-only。
- `R03_all_H20`、`R03_all_H40`、`R03_confirmed_H40`、`R03_no_fast_fail`、`R03_relaxed_fast_fail`、winner-state sensitivities 都是 diagnostic-only。

## 6. Validation 主要结果

### 6.1 Validation schedule-level 指标

| schedule | captured winners | strict capture | exposure-weighted capture | partial capture | mean return | p05 return | capital occupancy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R03_original_H10 | 2 / 43 | 0.046512 | 0.030233 | 0.372093 | 0.008592 | -0.007543 | 1.399060 |
| R03_confirmed_H20 | 3 / 43 | 0.069767 | 0.053488 | 0.372093 | 0.007063 | -0.014279 | 2.754323 |
| R03_confirmed_H60 | 7 / 43 | 0.162791 | 0.146512 | 0.372093 | 0.007017 | -0.034528 | 6.624624 |
| R03_confirmed_H120 | 11 / 43 | 0.255814 | 0.239535 | 0.372093 | 0.007071 | -0.058540 | 11.462970 |
| R03_winner_state_hold_H120 | 3 / 43 | 0.069767 | 0.053488 | 0.372093 | 0.007341 | -0.013453 | 2.705451 |

事实发现：

- 所有 primary candidates 都提高了 strict capture。
- `partial_capture_rate_50h120` 全部等于 0.372093，说明 R04 没有改变“是否曾经上车”，只改变“是否持有到 target date”。
- H60/H120 明显提高 captured winner count，但 p05 和 capital occupancy 明显恶化。
- H20/winner-state 的占用可控，但只多抓 1 个 winner，且 p05 / mean 仍不过门。

### 6.2 Validation 相对 R03 的差异

| schedule | strict capture diff | captured count diff | exposure-weighted diff | mean diff | p05 diff | MAE mean diff | turnover multiple | exposure-day multiple |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R03_confirmed_H20 | 0.023256 | 1 | 0.023256 | -0.001529 | -0.006736 | -0.001376 | 1.000000 | 1.968695 |
| R03_confirmed_H60 | 0.116279 | 5 | 0.116279 | -0.001575 | -0.026985 | -0.002860 | 1.000000 | 4.735053 |
| R03_confirmed_H120 | 0.209302 | 9 | 0.209302 | -0.001520 | -0.050998 | -0.004253 | 1.000000 | 8.193336 |
| R03_winner_state_hold_H120 | 0.023256 | 1 | 0.023256 | -0.001251 | -0.005911 | -0.001220 | 1.000000 | 1.933763 |

关键解释：

- turnover multiple 都约为 1，因为 R04 没有增加买入/加仓次数，只延长持有。
- 真实成本不是 turnover，而是 capital occupancy / exposure-days。
- H60/H120 的 exposure-day multiple 超过 3.0 的硬门，说明它们不再是 R03 同类低占用 schedule。

## 7. 失败 Gates 明细

R04 最终失败于 `failed_tail_risk`。这表示：至少有候选 schedule 提高了 validation winner capture，但所有 capture improver 都未能通过 tail-risk / occupancy / support gates。

Validation failed hard gates：

| schedule | failed gate | value | threshold |
| --- | --- | ---: | ---: |
| R03_confirmed_H20 | candidate_mean_return_diff | -0.001529 | -0.001 |
| R03_confirmed_H20 | candidate_p05_return_diff | -0.006736 | -0.005 |
| R03_confirmed_H60 | candidate_mean_return_diff | -0.001575 | -0.001 |
| R03_confirmed_H60 | candidate_p05_return_diff | -0.026985 | -0.005 |
| R03_confirmed_H60 | candidate_exposure_day_multiple | 4.735053 | 3.0 |
| R03_confirmed_H120 | candidate_mean_return_diff | -0.001520 | -0.001 |
| R03_confirmed_H120 | candidate_p05_return_diff | -0.050998 | -0.005 |
| R03_confirmed_H120 | candidate_exposure_day_multiple | 8.193336 | 3.0 |
| R03_winner_state_hold_H120 | candidate_mean_return_diff | -0.001251 | -0.001 |
| R03_winner_state_hold_H120 | candidate_p05_return_diff | -0.005911 | -0.005 |

非 hard failed row：

| split | schedule | failed gate | 说明 |
| --- | --- | --- | --- |
| train | R03_original_H10 | r03_replay_strict_big_winner_capture_match | requirement 不要求 train hard reconciliation，因此不影响 final status |

## 8. 为什么延长持有会失败

### 8.1 Exit reason 变化

Validation exposed episodes 的 exit reason：

| schedule | natural_exit | fast_fail_exit | profit_floor_exit | trailing_exit |
| --- | ---: | ---: | ---: | ---: |
| R03_original_H10 | 96 | 8 | 0 | 0 |
| R03_confirmed_H20 | 87 | 17 | 0 | 0 |
| R03_confirmed_H60 | 75 | 29 | 0 | 0 |
| R03_confirmed_H120 | 63 | 41 | 0 | 0 |
| R03_winner_state_hold_H120 | 80 | 15 | 6 | 3 |

事实发现：

- H 越长，fast-fail exit 越多。
- `R03_original_H10` 的 H10 natural exit 在很多 episode 上提前离开了后续下跌段。
- H60/H120 多抓 winner 的同时，也让更多非 winner 或回吐 winner 进入后续 fast-fail。
- winner-state 通过 trailing / profit-floor 提前退出了一部分 extended hold，但仍没有把 p05 控制到门槛内。

### 8.2 Exposed return 分布恶化

Validation exposed episodes 的收益分布：

| schedule | p05 exposed return | median exposed return | max exposed return |
| --- | ---: | ---: | ---: |
| R03_original_H10 | -0.041194 | 0.017519 | 0.488656 |
| R03_confirmed_H20 | -0.091921 | 0.010173 | 0.626394 |
| R03_confirmed_H60 | -0.104297 | 0.006871 | 0.544608 |
| R03_confirmed_H120 | -0.105918 | -0.009100 | 1.326473 |
| R03_winner_state_hold_H120 | -0.088119 | 0.011854 | 0.626394 |

事实发现：

- H20 已经让 exposed p05 从 -4.12% 扩大到 -9.19%。
- H120 的最大收益明显更高，证明它确实能保留部分大 winner，但 median 已转负。
- R04 的收益改善集中在少数右尾，左尾和中位数恶化更广泛。

### 8.3 Return delta vs R03

每个候选相对 R03 的 validation episode return delta：

| schedule | delta <= -5% | delta <= -10% | delta >= +5% | exposure-days delta mean | exposure-days delta p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| R03_confirmed_H20 | 22 | 11 | 16 | 1.355 | 11 |
| R03_confirmed_H60 | 31 | 18 | 15 | 5.226 | 51 |
| R03_confirmed_H120 | 40 | 26 | 16 | 10.064 | 111 |
| R03_winner_state_hold_H120 | 23 | 10 | 16 | 1.306 | 11 |

事实发现：

- H20/winner-state 的新增 positive tail 个数与新增 negative tail 个数不对称。
- H60/H120 的 positive tail 并没有随持有长度明显增加，但 negative tail 数量和 exposure-days 大幅增加。
- H120 相比 H10 有 40 个 episode 的 return delta 小于 -5%，26 个小于 -10%，而大于 +5% 的只有 16 个。

## 9. Big-Winner Capture 的真实含义

R04 新增 strict capture 的数量：

| schedule | 新增 strict captured winner | 丢失 R03 captured winner |
| --- | ---: | ---: |
| R03_confirmed_H20 | 1 | 0 |
| R03_confirmed_H60 | 5 | 0 |
| R03_confirmed_H120 | 9 | 0 |
| R03_winner_state_hold_H120 | 1 | 0 |

这说明 holding extension 确实能把一些 big winner 持有到 +50% target date。但它没有保证最终 realized return 更高。

典型例子：

```text
SZ000617:
  R03 H10 return: +0.250064
  H20 return:    +0.003604
  delta:         -0.246460
  big_winner_50h120 = true
  H20 strict_capture_50h120 = true
```

解释：

- strict capture 只表示 target date 当天还有 exposure。
- 它不表示最终卖出收益高于 R03。
- 如果 target 后继续持有，仍可能发生大幅回吐。
- 因此 R04 必须同时看 strict capture、exposure-weighted capture、p05、mean、capital occupancy。

## 10. Winner-State 方案分析

`R03_winner_state_hold_H120` 的设计目标是避免所有 confirmed episode 都机械延长，只让表现进入 observable winner-state 的仓位延长。

Validation 结果：

| 指标 | 数值 |
| --- | ---: |
| winner_hold_mode_entry_count | 37 |
| strict capture | 3 / 43 |
| captured count diff vs R03 | +1 |
| mean return diff vs R03 | -0.001251 |
| p05 return diff vs R03 | -0.005911 |
| exposure-day multiple vs R03 | 1.933763 |

事实发现：

- winner-state 的资金占用控制明显好于 H60/H120。
- winner-state 的 capture improvement 只有 +1，与 H20 相同。
- 它仍然轻微失败于 mean 和 p05 gates。
- winner-state as-of audit 通过，未发现 same-close transition 或 future label use。

当前推测：

- 当前 winner-state 条件可能太宽，导致 37 个 entry 中只有少数是真正后续大 winner。
- 也可能是 exit 规则仍不够保护利润：进入 winner-state 后，trailing / profit-floor 对部分 episode 太晚，导致 p05 仍恶化。
- 另一个可能是 winner-state 的 signal 时间太晚，只能多抓与 H20 类似的一小部分 winner，无法补偿额外风险。

## 11. Fast-Fail Diagnostic 观察

Fast-fail diagnostic 输出显示，关闭或放松 fast-fail 没有在 validation 上增加 strict big-winner capture：

| counterfactual | split | capture_delta | mean_return_delta | p05_return_delta | fast_fail_saved_loss_count | false_exit_big_winner_count | false_exit_partial_capture_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_fast_fail | validation | 0.000000 | 0.001536 | 0.004846 | 1 | 0 | 2 |
| relaxed_fast_fail | validation | 0.000000 | 0.001372 | 0.003986 | 1 | 0 | 2 |
| no_fast_fail | robustness | 0.000000 | 0.002123 | 0.008285 | 0 | 0 | 4 |
| relaxed_fast_fail | robustness | 0.000000 | 0.001491 | 0.004053 | 0 | 0 | 4 |

事实发现：

- fast-fail 没有明显错杀最终 strict captured big winner。
- fast-fail 确实错杀了一些 partial capture opportunity，但这些 opportunity 即使放松 fast-fail，也没有转化为 strict capture。
- 当前 diagnostic 下，放松 fast-fail 对 mean / p05 是正向的，但这只是 diagnostic，不能直接 promotion。

当前推测：

- R04 的主要问题不是 fast-fail 太严，而是自然退出/利润保护机制太粗。
- 如果继续研究 fast-fail，应作为 risk-filter / bad-trade overlay 的一部分，而不是简单关闭。

## 12. Robustness Holdout 的参考信息

虽然 selection 在 validation 阶段已经失败，robustness 仍显示一些有用信号：

| schedule | strict capture diff | captured count diff | mean diff | p05 diff | exposure-day multiple |
| --- | ---: | ---: | ---: | ---: | ---: |
| R03_confirmed_H20 | 0.062992 | 8 | 0.009180 | 0.012141 | 1.971313 |
| R03_confirmed_H60 | 0.173228 | 22 | 0.011859 | -0.005228 | 5.057566 |
| R03_confirmed_H120 | 0.228346 | 29 | 0.014766 | -0.030764 | 9.052561 |
| R03_winner_state_hold_H120 | 0.062992 | 8 | 0.008659 | 0.012141 | 1.824028 |

事实发现：

- Robustness 上 H20 和 winner-state 看起来比 validation 好。
- 但 requirement 明确禁止用 robustness 做 selection 或调参。
- 因此不能因为 robustness 更好就绕过 validation hard gates。

当前推测：

- Validation 的 2022-2023 样本可能对延长持有更不友好，存在 regime sensitivity。
- Robustness 改善可能来自市场环境更适合趋势延续，而不是规则本身稳定有效。
- 如果后续要研究 regime-sensitive holding，需要新 requirement 预注册 regime split，而不能在 R04 事后修改。

## 13. Diagnostic-Only Variant 观察

R04 还输出了 diagnostic counterfactuals，用于解释机制，不允许 promotion。

主要用途：

- `R03_all_H20` / `R03_all_H40`：验证“所有 exposure 统一延长”是否比 confirmed-only 更好。
- `R03_confirmed_H40`：检查 H40 中间点。
- `R03_no_fast_fail` / `R03_relaxed_fast_fail`：检查 fast-fail 是否错杀 future winner。
- winner-state gain/trailing sensitivities：检查 state threshold 是否对结果敏感。

当前事实：

- diagnostic rows 共 150 行。
- 所有 diagnostic rows 的 `eligible_for_selection = false`。
- 它们没有改变 final `next_phase_proceed_status`。

当前推测：

- `R03_confirmed_H40` 可能是 H20/H60 之间更平衡的观察点，但它不是当前 primary promotion candidate。
- 单纯固定 H 值的 family 可能过粗，下一步更应该研究 partial exit 和 profit lock，而不是继续扩大 H matrix。

## 14. 对 R04 失败原因的综合判断

### 14.1 已验证事实

1. R04 promotion candidates 全部提高 validation strict capture。
2. 所有 promotion candidates 都没有通过 validation tail-risk gates。
3. 失败门集中在 mean return diff、p05 return diff、exposure-day multiple。
4. Turnover multiple 和 concentration 不是本次失败主因。
5. Partial capture 没有改善，说明 R04 没解决 entry coverage，只改变持有到 target 的概率。
6. H60/H120 的 capture 提升最大，但资金占用和左尾恶化也最大。
7. H20/winner-state 的资金占用可控，但新增 capture 太少，且 mean/p05 仍越界。
8. Winner-state as-of audit 通过，失败不是由 lookahead 或 timing leakage 引起。
9. Fast-fail diagnostic 没显示 fast-fail 大量错杀 strict big winner。

### 14.2 当前推测

1. R03 H10 不是简单“过早退出”，它在 validation 上也承担了重要的风险截断作用。
2. EP2 launch/probe/confirm-add 当前更像短周期 timing alpha，而不是天然 winner-holding alpha。
3. 固定持有 H20/H60/H120 对 winner 和 non-winner 一视同仁，缺少足够的状态区分能力。
4. Winner-state 方向可能有价值，但当前状态定义不够强，无法在 validation 上同时提升 capture 和控制 p05。
5. 真正需要的可能不是继续延长自然退出，而是：
   - partial exit；
   - profit lock；
   - trailing stop 更早生效；
   - post-confirm risk filter；
   - bad-trade avoidance overlay；
   - regime-aware holding rule。
6. 如果目标仍是 big-winner capture，后续 requirement 应避免单纯扩大 H matrix，否则容易变成更多参数搜索。

## 15. 对后续 Requirement 的建议

建议不要直接进入 P1 strategy validation 或 freeze strategy。当前 R04 的正式 recommendation 是：

```text
reframe_EP2_as_risk_filter_overlay
```

可考虑的后续方向：

1. `Requirement 05: BaseRate Integration / Attribution`
   - 把 EP2 作为 BaseRate bad-trade avoidance 或 event-sleeve overlay，而不是独立 long-holding strategy。

   这里的 `event-sleeve overlay` 指的是：EP2 不独立承担完整组合的选股、持仓和长期收益目标，而是作为一个围绕特定事件触发的短周期子模块，叠加在主策略或 BaseRate 框架上。它只在 launch / probe / confirm-add 事件链出现时产生有限 exposure，并且 exposure 的目标是捕捉事件后短窗口的 timing alpha，而不是长期持有到大 winner 终点。

   更具体地说，`event sleeve` 是组合里一个有明确边界的小仓位 sleeve：

   - entry 来源：只来自 EP2 已冻结的 launch/probe/confirm-add 事件，不扩展成全市场选股器；
   - holding 目标：默认短持有、低资金占用，优先保留 R03 的 H10 风险截断特征；
   - capital role：作为主组合旁边的战术仓位，而不是替代 BaseRate / TopK 主组合；
   - risk role：可以帮助识别 BaseRate 没覆盖到的事件机会，也可以作为 BaseRate bad-trade avoidance 的风险过滤器；
   - promotion 条件：必须证明它在叠加后改善组合 attribution 或降低 bad trade，而不是仅凭单独 big-winner capture 提高。

   这个定位和 “独立 long-holding strategy” 的区别很重要。独立 long-holding strategy 需要证明它能自己完成从 entry 到长期退出的完整收益闭环，尤其要证明 H60/H120 或 winner-state hold 在 validation / robustness 上都能控制 p05、资金占用和回撤。R04 已经显示当前规则做不到这一点：固定延长持有虽然多抓 winner，但 validation 左尾和 exposure-days 恶化太快。

   因此，R05 如果走 BaseRate integration，应该回答的是：

   - EP2 exposure 与 BaseRate buy/trade 有多少重叠？
   - EP2 是否能解释 BaseRate 没覆盖但后续表现好的 event opportunity？
   - EP2 是否能过滤 BaseRate 中某些 bad trade 或 tail-risk trade？
   - EP2 作为小仓位 sleeve 加进去后，组合层面的 mean、p05、turnover、capital occupancy 是否改善？
   - 如果 EP2 只保留短周期 H10 / R03-style exposure，它是否仍有正 attribution？

   这个方向承认 R04 的失败结论：EP2 当前不是合格的 winner-holding engine；但它可能仍是一个有效的短周期事件 timing / 风险过滤 overlay。

2. `Requirement 05A: Partial Exit / Profit Protection`
   - 针对 R04 发现的问题，预注册 partial exit 规则；
   - 例如 H10 先锁定部分收益，剩余仓位才进入 H60/H120；
   - 必须限制参数数量，避免搜索空间膨胀。

3. `Requirement 05B: Post-Confirm Risk Filter`
   - 研究 confirm-add 后哪些状态会导致 H20/H60 左尾恶化；
   - 目标不是提高 entry frequency，而是减少延长持有中的 bad extension。

4. `Requirement 05C: Regime Holdout`
   - 如果怀疑 validation/robustness regime 差异明显，应预注册 regime split；
   - 禁止事后按 robustness 好结果修改 R04 selection。

## 16. Go / No-Go 判断

Requirement-gated 判断：

```text
Do not proceed to P1 strategy validation.
Do not freeze a long-holding EP2 strategy.
Do not promote any R04 schedule.
```

可以继续的方向：

```text
Proceed to an attribution / overlay / risk-filter requirement.
Keep EP2 as a short-horizon event sleeve unless a later pre-registered phase proves otherwise.
```

一句话总结：

R04 证明“延长持有可以多抓 big winner”，但也证明“当前固定持有 / 当前 winner-state 规则无法以可接受的 validation tail-risk 代价抓 winner”。因此，这不是一个可以推广的 holding extension，而是一个指向 risk-filter、profit-protection 和 partial-exit 下一阶段研究的问题定位实验。

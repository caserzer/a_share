# 12A2 State-change Backbone Candidate Generator Report

## 结论

12A2 生成结果为 `12A2_state_change_candidate_generation_supported`。本阶段成功把 12A1 中被降级的 R-core 从 backbone 角色移出，重新生成一组 PIT-safe、next-open executable、first-trigger disciplined 的 state-change candidate pool。

核心结果：

- primary canonical events: `28,691`
- raw event instances: `301,629`
- runnable raw instances: `265,682`
- supported raw instances after family/union/first-trigger filters: `59,881`
- next-open executable supported events: `59,881`
- next-open executable rate: `1.0000`
- runnable / diagnostic / blocked family count: `7 / 1 / 4`
- next allowed requirement: `requirement_12a3_episode_precision_recall_frontier.md`

12A2 只证明“候选生成口径可运行且密度受控”，不证明 winner episode recall / precision。episode frontier 必须在 12A3 用 06 target registry 和 frozen execution anchor 单独评估。

## 12A1 Handoff

| field | value |
|:--|:--|
| upstream_12a1_decision | `12A1_r_core_recall_benchmark_only` |
| upstream_population_bridge_status | `pass` |
| upstream_next_allowed_requirement | `stop_no_valid_backbone_for_morphology` |
| handoff_conflict_flag | `False` |
| interpretation | R-core 只保留为 recall benchmark，不再作为 winner/failure morphology backbone |

这里的关键含义是：12A1 要求停止旧的 winner/failure morphology 路径，但不阻止 12A2 作为 replacement backbone diagnostic 运行。12A2 当前支持进入 12A3 frontier，但仍不能回退为“R-core 已可交易”的结论。

## Gate Readout

| gate | result | evidence |
|:--|:--|:--|
| input_gate_pass | `True` | 12A1 decision、R-core density、R-core event registry、12A1 manifest、08 panel、PIT universe、qfq daily、benchmark 均可读 |
| pit_feature_gate_pass | `True` | runnable inputs 均为 t0 close 可得字段 |
| forbidden_feature_gate_pass | `True` | 未使用 future return、episode label、label-derived touch coordinate |
| candidate_nonempty_gate_pass | `True` | primary canonical event_n = `28,691` |
| train_candidate_presence_gate_pass | `True` | train primary canonical event_n = `14,560` |
| robustness_candidate_presence_gate_pass | `True` | robustness primary canonical event_n = `7,271` |
| next_open_executable_gate_pass | `True` | supported raw denominator = `59,881`，executable numerator = `59,881` |
| density_hygiene_gate_pass | `True` | all/train/robustness 均通过 density / duplicate / board concentration / first-trigger gates |

## Key Findings

1. 新 backbone 的密度明显低于 R-core，但仍显著高于 07 E1-only。

   全样本 primary canonical density 为 `7.9204` events / instrument-year，相当于 08 raw R-core 的 `59.88%`，说明 state-change first-trigger 和 C0 cooldown 已经把 R-core 的高密度问题压下来。但它仍是 07 E1-only 的 `4.32x`，所以 12A2 不是最终交易过滤器，只是更干净的候选 backbone。

2. 主要候选贡献来自 B5 / B1 / B8 / B3，而不是单一 momentum rank。

   B5 贡献 `10,887` 个 primary canonical events，占 `37.95%`；B1 贡献 `4,570`，占 `15.93%`；B8 贡献 `3,771`，占 `13.14%`；B3 贡献 `3,508`，占 `12.23%`。这说明新候选池不是单纯 R-core momentum 复刻，而是资金参与、相对残差突破、持续趋势态、低位修复共同组成。

3. B6 raw 很大，但 canonical 后被强烈压缩。

   B6 raw event_n 为 `75,127`，占所有 raw 的 `24.91%`，但 primary canonical 只有 `2,443`，占 `8.51%`，canonical_over_raw 仅 `3.25%`。这说明 rank-entry family 仍有较强的横截面 momentum 密度倾向，但 C0 priority / union cooldown 对它起到了显著降噪作用。12A3 不应直接把 B6 raw 当成可交易信号，只应评估 canonical 后的边际贡献。

4. B3 是最稀疏但保留效率最高的 repair family。

   B3 raw event_n 为 `11,527`，primary canonical 为 `3,508`，canonical_over_raw = `30.43%`，是所有 runnable family 中最高的。这符合 B3 “low-reclaim / repair transition”定位：触发更少，但更容易通过 canonical pipeline 保留下来。它应在 12A3 中被单独看 recall timing 和 precision，而不是被 B1 priority 淹没。

5. B8 补上了“无穿越但趋势在位”的盲区，但 B8 本身不是低密度 family。

   B8 raw event_n 为 `47,201`，primary canonical 为 `3,771`，primary density 约 `1.0410`。B8 与 B1/B3 的 same-day raw overlap 为 `3,120`，但仍有 `32,325` 个 B8 raw events 不与 B1/B3 同日重叠。它确实覆盖了 B1/B3 不容易捕捉的持续趋势态，但需要 12A3 判断这些 B8-only events 是有效 recall 补充还是趋势追随噪声。

6. B1/B3 同日碰撞显示当前 C0 priority 可能牺牲 timing。

   B1/B3 same-day raw overlap 为 `1,367`。同日碰撞时 C0 primary 选择 B1 的事件为 `763`，选择 B3 的事件为 `0`。B1 相对 06 episode_low 的 median lag 为 `16` 个交易日，B3 对应 median lag 为 `8` 个交易日。这个结果支持之前的担忧：B1 priority 高于 B3 可能让 primary anchor 系统性偏晚。12A3 应至少做一个 B3-priority sensitivity。

7. board concentration 仍接近上限，需要在 12A3 继续监控。

   main_board 占 primary canonical `79.46%`，chinext 占 `20.54%`。top_board_event_share = `0.7946`，低于 `0.85` gate，但仍然偏集中。这不是 blocker，但如果 12A3 发现 recall/precision 被 main_board 主导，需要做 board-sliced frontier。

## Density And Concentration

| split | primary_event_n | events_per_instrument_year | density_vs_08_r_core | density_vs_07_E1_only | rolling_10d_duplicate_rate | top_board_event_share | first_trigger_supported_rate |
|:--|--:|--:|--:|--:|--:|--:|--:|
| all | 28,691 | 7.9204 | 0.5988 | 4.3202 | 0.0725 | 0.7946 | 0.9174 |
| train | 14,560 | 4.0194 | 0.5994 | 4.3658 | 0.0735 | 0.7920 | 0.9157 |
| validation | 6,860 | 1.8938 | 0.6431 | 3.8111 | 0.0692 | 0.8074 | 0.9405 |
| robustness | 7,271 | 2.0072 | 0.5613 | 4.3151 | 0.0715 | 0.7877 | 0.8993 |

Board distribution:

| board_bucket | primary_event_n | share |
|:--|--:|--:|
| main_board | 22,797 | 79.46% |
| chinext | 5,894 | 20.54% |

Market-regime distribution:

| market_regime_bucket | primary_event_n | share |
|:--|--:|--:|
| risk_on | 15,113 | 52.68% |
| transition | 7,435 | 25.91% |
| risk_off | 6,143 | 21.41% |

Instrument concentration is low: the largest single instrument has `72` primary events, only `0.25%` of all primary canonical events. The density risk is therefore more board/regime-level than single-instrument-level.

## Raw To Primary Funnel

| stage | event_n | share |
|:--|--:|--:|
| raw event instances | 301,629 | 100.00% of raw |
| runnable raw instances | 265,682 | 88.08% of raw |
| supported raw instances after family/union/first-trigger filters | 59,881 | 22.54% of runnable |
| primary canonical events | 28,691 | 47.91% of supported raw |
| primary canonical events | 28,691 | 9.51% of raw |

Interpretation:

- raw pool deliberately remains broad enough for family diagnostics;
- C0 first-trigger and union cooldown are doing material work;
- only `9.51%` of raw instances survive to primary canonical, so 12A2 should be evaluated from `state_change_candidate_event_canonical.csv.gz`, not from raw instances.

Canonical collision depth:

| triggered_family_count | primary_event_n | share |
|--:|--:|--:|
| 1 | 20,117 | 70.12% |
| 2 | 6,090 | 21.23% |
| 3 | 1,801 | 6.28% |
| 4 | 618 | 2.15% |
| 5 | 63 | 0.22% |
| 6 | 2 | 0.01% |

Most primary events are single-family triggers, but `29.88%` involve at least two triggered families. This is useful for 12A3: multi-family events can be evaluated as a separate confidence tier without changing candidate generation.

## Family Contribution

| family_id | raw_event_n | executable_rate | union_pass_n | union_blocked_n | not_primary_eligible_n | canonical_event_n | raw_share | canonical_share | canonical_over_raw |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| B5 | 93,010 | 99.20% | 24,730 | 10,964 | 57,316 | 10,887 | 30.84% | 37.95% | 11.71% |
| B1 | 19,748 | 99.87% | 6,967 | 12,672 | 109 | 4,570 | 6.55% | 15.93% | 23.14% |
| B8 | 47,201 | 98.45% | 7,171 | 7,055 | 32,975 | 3,771 | 15.65% | 13.14% | 7.99% |
| B3 | 11,527 | 99.89% | 6,685 | 3,559 | 1,283 | 3,508 | 3.82% | 12.23% | 30.43% |
| B2 | 13,135 | 99.45% | 6,554 | 1,665 | 4,916 | 3,143 | 4.35% | 10.95% | 23.93% |
| B6 | 75,127 | 99.31% | 7,178 | 10,507 | 57,442 | 2,443 | 24.91% | 8.51% | 3.25% |
| B4 | 5,934 | 98.70% | 596 | 924 | 4,414 | 369 | 1.97% | 1.29% | 6.22% |
| B7 | 35,947 | 99.65% | 0 | 0 | 35,947 | 0 | 11.92% | 0.00% | 0.00% |

Family-level interpretation:

- B5 is the largest primary source. It captures participation / volume regime shift, but its raw count is also the highest. If 12A3 precision is poor, B5 should be the first family to threshold-sweep.
- B1 is a cleaner replacement for pure momentum because it uses beta-adjusted residual CUSUM and lagmax first-break logic. It contributes meaningfully without dominating raw density.
- B3 has the best raw-to-primary conversion and should be treated as the most timing-sensitive repair family.
- B6 is density-heavy before C0. It should stay below B5/B1/B3 in interpretive confidence until 12A3 validates frontier quality.
- B4 is sparse after requiring market_turn, board_turn, and stock_participation. Its low count is acceptable; the larger issue is that true industry breadth remains unavailable.
- B7 remains diagnostic-only. Its `35,947` raw events show why high-base breakout should not be promoted to primary without a new requirement.

## Canonical Split Distribution

| primary_family_id | all | train | validation | robustness |
|:--|--:|--:|--:|--:|
| B5 | 10,887 | 5,612 | 2,551 | 2,724 |
| B1 | 4,570 | 2,163 | 1,112 | 1,295 |
| B8 | 3,771 | 2,008 | 822 | 941 |
| B3 | 3,508 | 1,772 | 946 | 790 |
| B2 | 3,143 | 1,664 | 749 | 730 |
| B6 | 2,443 | 1,166 | 641 | 636 |
| B4 | 369 | 175 | 39 | 155 |

Robustness split remains populated across all runnable primary families. This is important because 12A3 can evaluate out-of-sample frontier without family collapse into train-only artifacts.

## Formula And Family Status

| family | role | implementation status | interpretation |
|:--|:--|:--|:--|
| B1 | relative residual CUSUM break | runnable, 4 variants | replacement for pure R-core momentum break; uses residual CUSUM and lagmax first-break |
| B2 | compression-to-expansion | runnable, 3 variants | detects volatility/range compression followed by directional expansion |
| B3 | low-reclaim / repair transition | runnable, 2 variants | closest to low-side repair timing; likely important for episode_low alignment |
| B4 | breadth/regime context | runnable proxy, 2 variants | uses Top-N / board / all-A proxy only; industry version blocked |
| B5 | participation / volume regime shift | runnable, 2 variants | high contribution family; likely needs 12A3 precision screening |
| B6 | first leadership rank entry | runnable, 2 variants | rank-jump state-change version; raw density high but C0 suppresses heavily |
| B7 | high-base breakout | diagnostic-only | kept for readout; not eligible for primary canonical |
| B8 | sustained trend state | runnable, 2 variants | covers no-crossing sustained trend winners; must be tested for recall contribution |
| B4_industry / R4 / T1 / T2 | industry / sector rotation | blocked | PIT industry classification unavailable |

Blocked industry dimensions:

- `B4_industry_breadth_context`
- `R4_industry_breadth_expansion`
- `T1_stock_vs_industry_CUSUM_break`
- `T2_industry_vs_market_CUSUM_break`

## PIT And Leakage Audit

| input_source_id | pit_audit_status | future_return | episode_label | label_touch_coordinate | blocked_reason |
|:--|:--|:--|:--|:--|:--|
| stock_daily_qfq_panel | pass | False | False | False |  |
| pit_membership_daily | pass | False | False | False |  |
| pit_executable_daily | pass | False | False | False |  |
| 08_cross_section_feature_panel | pass | False | False | False |  |
| pit_industry_classification | blocked_missing_source | False | False | False | blocked_missing_pit_industry_classification |

The PIT boundary is clean for runnable families:

- event_t0 uses same-day close features and PIT membership / board snapshot;
- trade_open uses executable universe and next-open price;
- future return, MFE/MAE, episode labels, and label-derived touch coordinates are not used as features;
- industry rotation is explicitly blocked instead of silently proxied.

## B1 vs B3 Timing Collision

| split | same-day overlap_n | C0 primary B1 | C0 primary B3 | B1 median lag from episode_low | B3 median lag from episode_low | B1 covered_06_episode_n | B1 missed_06_episode_n |
|:--|--:|--:|--:|--:|--:|--:|--:|
| all | 1,367 | 763 | 0 | 16.0 | 8.0 | 293 | 135 |
| train | 697 | 379 | 0 | 15.0 | 12.0 | 153 | 72 |
| validation | 412 | 225 | 0 | 20.0 | 13.0 | 18 | 4 |
| robustness | 258 | 159 | 0 | 16.0 | 5.0 | 122 | 59 |

Finding:

Current C0 priority makes B1 win over B3 whenever they collide on the same instrument/date. The timing diagnostic suggests B3 is earlier in median lag to episode_low across all splits, especially robustness (`5` vs `16`). This does not mean B3 has better precision, but it does mean 12A3 should include:

- current priority baseline: B1 before B3;
- sensitivity run/readout: B3 before B1;
- family-level frontier: B1-only, B3-only, B1+B3 collision cases.

## B8 Sustained Trend State

| metric | value |
|:--|--:|
| B8 raw_event_n | 47,201 |
| B8 primary canonical event_n | 3,771 |
| B8 primary density | 1.0410 |
| B8 raw executable rate, train | 98.36% |
| B8 raw executable rate, validation | 98.57% |
| B8 raw executable rate, robustness | 98.55% |
| B8 first_observed_sustained_state raw origins | 736 |
| B8 false_to_true_sustained_state raw origins | 46,465 |

B8 overlap with B1/B3:

| split | B8 raw_event_n | B8 canonical_event_n | B8-only raw_event_n vs B1/B3 | B8/B1-or-B3 same-day overlap_n | C0 primary B1 in overlap | C0 primary B3 in overlap | B8 median lag | B1/B3 median lag |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| all | 47,201 | 3,771 | 32,325 | 3,120 | 1,263 | 13 | 21.0 | 14.0 |
| train | 25,213 | 2,008 | 17,161 | 1,493 | 614 | 7 | 22.5 | 15.0 |
| validation | 9,332 | 822 | 6,601 | 614 | 232 | 5 | -10.5 | 18.5 |
| robustness | 12,656 | 941 | 8,563 | 1,013 | 417 | 1 | 18.0 | 9.0 |

Insight:

B8 does cover a real family-design gap: a large number of sustained-trend events do not coincide with B1/B3 same-day state changes. But B8 median timing is not consistently earlier. In all/train/robustness it is later than B1/B3 overlap timing; validation is the exception. Therefore B8 should be treated as a recall-completion candidate, not as a better onset anchor by default.

For 12A3, B8 should be evaluated in two ways:

- B8-only recall contribution: episodes covered by B8 but not by B1/B3/B5;
- B8 precision drag: whether sustained trend confirmation adds too many late non-winner events.

## Research Interpretation

12A2 improves the research state in three ways.

First, it creates a cleaner backbone than R-core. The density ratio vs 08 raw R-core falls to `0.5988`, duplicate rate is low (`0.0725` rolling 10d), and next-open execution is fully covered in the supported denominator.

Second, it exposes where state-change design still has risk. B5 and B6 dominate raw event count; B1 can override earlier B3 repair anchors; B8 fills a design gap but may be late. These are not implementation failures. They are exactly the frontier questions 12A3 should answer.

Third, it prevents hidden scope drift. Industry/sector rotation remains blocked instead of imputed, B7 is diagnostic-only, and R-core remains benchmark-only. That keeps 12A3 focused on episode recall / precision frontier rather than mixing incompatible candidate populations.

## Recommended 12A3 Readouts

Required next readouts:

1. Episode-level recall frontier for primary canonical union:
   - pre120-to-high coverage;
   - low-to-high coverage;
   - event_t0 lag from episode_low;
   - first_50pct lag if available.

2. Family-sliced recall and precision:
   - B1, B2, B3, B4, B5, B6, B8 separately;
   - B5/B6 as likely high-density families;
   - B3 as likely timing-sensitive family;
   - B8-only as sustained-trend recall completion.

3. Priority sensitivity:
   - current C0 priority;
   - B3 before B1;
   - optional B5 down-priority or threshold sweep if precision is poor.

4. Board/regime slices:
   - main_board vs chinext;
   - risk_on / transition / risk_off;
   - monitor whether main_board share near `79.46%` distorts recall or precision.

5. Multi-family confidence tier:
   - single-family events: `70.12%`;
   - two-or-more-family events: `29.88%`;
   - evaluate whether multi-family triggers improve precision enough to be a policy filter.

## Final Status

`12A2_state_change_candidate_generation_supported`

The generated candidate pool is suitable for 12A3 episode precision / recall frontier evaluation. It is not yet suitable for winner/failure morphology modeling or trading-policy filtering without the 12A3 frontier.

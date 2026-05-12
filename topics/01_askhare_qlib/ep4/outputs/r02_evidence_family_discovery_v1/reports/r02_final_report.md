# EP4 R02 Evidence Family Discovery V1 中文研究报告

- Final decision: `archive_family_discovery_no_r03`
- 报告范围：只更新当前 markdown 报告；不修改代码、不重跑实验、不调整阈值。
- 实验范围：R02 只做 action-time evidence family discovery，不做最终 entry / add / exit 模型，不做 30 日建仓，不做 portfolio simulation。
- 重要口径：R02 generic `unit_return_R` 使用 R02 lookback-low diagnostic stop，和 R01 V3 `return_R` not numerically comparable。
- 解释边界：本报告区分 action-time prior、posterior precision、winner coverage diagnostic、EV_R、execution feasibility、label confusion，不把任何结果转换成风险预算。

## 1. 结论

这次 R02 V1 的结论很直接：当前 search space 没有发现可冻结的 3 到 5 个非 baseline evidence family，因此不能进入 R03 evidence accumulation。

关键原因不是没有 forward lift。相反，一些 primitive 的 primary LR 很高，尤其是 gap / relative strength / near-high 类信号。但这些信号无法同时满足 R02 要求的几个条件：

1. density 太高，很多强势状态不是窄 evidence，而是大面积市场状态；
2. R02 generic H20 diagnostic EV_R 多数为负；
3. 少数 EV_R 为正的 volatility contraction 类信号，density / risk-distance 问题又太重；
4. V3 post30 seed 在 action-time 分母下仍有 LR > 1，但 validation EV_R 明显为负，不能作为 R03 family pool 的依据。

我的判断：R02 V1 证明了“右尾 evidence family 不能靠单日强势状态直接搜索出来”。当前 primitive 更像状态描述器，而不是可用于 evidence accumulation 的可冻结 family。下一步不应直接放宽 gate，而应重新设计 search space，把“低风险结构”和“可执行风险距离”前置为候选构造的一部分。

## 2. Run / Artifact 状态

| item | value |
|:--|:--|
| final_decision | `archive_family_discovery_no_r03` |
| action_time_rows | 1,061,176 |
| eligible_action_time_rows | 399,707 |
| single primitive candidates | 58 |
| approved combo candidates | 0 |
| frozen non-baseline families | 0 |
| configured_n_jobs / effective_n_jobs | 12 / 12 |
| deterministic smoke | passed |

说明：当前 validator 已经把 research gate failure 和 contract validation failure 分开。这里是 research failure，不是 artifact contract failure。

## 3. Action-Time 分母与 Effective Window

R02 的关键修正是使用 split-bounded effective label window。也就是说，validation 的 120 日 big-winner label 不能偷看 2024 年之后的结果；robustness 也不能用 split 之外的未来窗口。

| split | label_id | raw_action_time_rows | complete_forward_rows | incomplete_forward_rows | entry_execution_unavailable_rows | effective_label_end | complete_forward_rate |
|:--|:--|--:|--:|--:|--:|:--|--:|
| train | continuation_h20 | 181,227 | 174,010 | 5,205 | 2,092 | 2021-12-03 | 96.02% |
| train | continuation_h60 | 181,227 | 164,172 | 15,153 | 2,092 | 2021-10-08 | 90.59% |
| train | big_winner_forward | 181,227 | 149,755 | 29,762 | 2,092 | 2021-07-07 | 82.63% |
| train | failed_seed_forward | 181,227 | 176,603 | 2,566 | 2,092 | 2021-12-17 | 97.45% |
| train | executable_entry_available | 181,227 | 180,962 | 265 | 2,092 | 2021-12-30 | 99.85% |
| validation | continuation_h20 | 108,970 | 103,712 | 4,159 | 1,125 | 2023-12-01 | 95.17% |
| validation | continuation_h60 | 108,970 | 95,144 | 12,785 | 1,125 | 2023-09-28 | 87.31% |
| validation | big_winner_forward | 108,970 | 81,744 | 26,277 | 1,125 | 2023-07-06 | 75.02% |
| validation | failed_seed_forward | 108,970 | 105,803 | 2,053 | 1,125 | 2023-12-15 | 97.09% |
| validation | executable_entry_available | 108,970 | 108,763 | 207 | 1,125 | 2023-12-28 | 99.81% |
| robustness | continuation_h20 | 109,510 | 103,094 | 5,337 | 1,104 | 2025-12-03 | 94.14% |
| robustness | continuation_h60 | 109,510 | 92,504 | 16,007 | 1,104 | 2025-09-30 | 84.47% |
| robustness | big_winner_forward | 109,510 | 77,866 | 30,782 | 1,104 | 2025-07-08 | 71.10% |
| robustness | failed_seed_forward | 109,510 | 105,730 | 2,690 | 1,104 | 2025-12-17 | 96.55% |
| robustness | executable_entry_available | 109,510 | 109,238 | 272 | 1,104 | 2025-12-30 | 99.75% |

这个表说明一个重要事实：`big_winner_forward` 的可用分母会被 120 日 forward window 大幅收缩。validation 的 raw action-time rows 是 108,970，但 h120 primary label 只有 81,744 行进入分母。之前如果不做 split-boundary，会高估 validation / robustness 的可验证样本。

## 4. Label Base Rate

| split | label | denominator | positive | rate |
|:--|:--|--:|--:|--:|
| train | big_winner_forward | 149,755 | 21,760 | 14.53% |
| train | continuation_h20 | 174,010 | 25,741 | 14.79% |
| train | continuation_h60 | 164,172 | 19,257 | 11.73% |
| train | failed_seed_forward | 176,603 | 45,452 | 25.74% |
| train | executable_entry_available | 180,962 | 63,970 | 35.35% |
| validation | big_winner_forward | 81,744 | 4,182 | 5.12% |
| validation | continuation_h20 | 103,712 | 9,658 | 9.31% |
| validation | continuation_h60 | 95,144 | 4,630 | 4.87% |
| validation | failed_seed_forward | 105,803 | 27,294 | 25.80% |
| validation | executable_entry_available | 108,763 | 30,891 | 28.40% |
| robustness | big_winner_forward | 77,866 | 7,705 | 9.90% |
| robustness | continuation_h20 | 103,094 | 13,192 | 12.80% |
| robustness | continuation_h60 | 92,504 | 8,746 | 9.45% |
| robustness | failed_seed_forward | 105,730 | 17,784 | 16.82% |
| robustness | executable_entry_available | 109,238 | 28,537 | 26.12% |

这里最值得注意的是 validation 的 `big_winner_forward` base rate 只有 5.12%，明显低于 train 的 14.53%。这会让很多 train 上看起来有右尾 lift 的状态，在 validation 上失去足够 posterior precision。我的猜测是 2022-2023 的右尾展开结构更稀疏，单日强势信号更容易变成反弹/噪音，而不是 h120 winner episode。

## 5. Primitive Search 总览

58 个 single primitive 全部被 early rejection 拒绝，没有任何 primitive 进入 approved combo 构造。因此 combo candidates = 0，后续 clustering / family selection 没有非 baseline family 可冻结。

| group_id | candidates | best_LR | best_EV_R | min_density | max_density |
|:--|--:|--:|--:|--:|--:|
| acceleration | 2 | 1.9932 | -0.1511 | 0.0119 | 0.0945 |
| distribution_absence | 2 | 1.0488 | -0.1905 | 0.5012 | 0.5019 |
| industry_market | 6 | 1.1291 | -0.2158 | 0.1900 | 0.5382 |
| price_momentum | 9 | 1.3563 | -0.1156 | 0.0750 | 0.8221 |
| pullback_structure | 8 | 0.9820 | -0.1401 | 0.2364 | 0.9664 |
| relative_strength | 12 | 1.8629 | -0.1239 | 0.2000 | 0.5017 |
| survival_no_failure | 2 | 1.0088 | -0.2217 | 0.9698 | 0.9702 |
| volatility_state | 5 | 1.0854 | 0.1085 | 0.1919 | 0.9862 |
| volume_money | 12 | 1.0242 | -0.0658 | 0.0426 | 0.4063 |

失败规则计数：

| failed rule | count |
|:--|--:|
| min_train_EV_R | 56 |
| max_train_stock_day_density_single | 52 |
| min_train_primary_LR_ci90_lower | 31 |
| min_train_primary_LR | 26 |
| max_train_risk_distance_ineligible_rate | 2 |

这个结果非常集中：几乎所有候选都败在 EV_R 或 density。换句话说，问题不是候选数量太少，而是当前单日 primitive 的信息质量不够。

## 6. Top LR Candidates

| candidate_id | group_id | trigger_count | density | P_winner_given_signal | LR | LR_ci90_lower | EV_R | failed_rules |
|:--|:--|--:|--:|--:|--:|--:|--:|:--|
| acceleration__gap_open_pct__ge_0p03 | acceleration | 2,161 | 1.19% | 25.31% | 1.9932 | 1.7835 | -0.2418 | min_train_EV_R |
| relative_strength__rps60__gt_0p8 | relative_strength | 36,250 | 20.00% | 24.05% | 1.8629 | 1.6898 | -0.1308 | density; EV_R |
| relative_strength__rps20__gt_0p8 | relative_strength | 36,418 | 20.10% | 22.21% | 1.6795 | 1.5606 | -0.1437 | density; EV_R |
| acceleration__gap_open_pct__ge_0p01 | acceleration | 17,135 | 9.45% | 21.92% | 1.6509 | 1.5413 | -0.1511 | min_train_EV_R |
| relative_strength__rps60__gt_0p7 | relative_strength | 54,381 | 30.01% | 21.59% | 1.6200 | 1.5021 | -0.1495 | density; EV_R |
| relative_strength__rps5__gt_0p8 | relative_strength | 36,479 | 20.13% | 20.04% | 1.4746 | 1.3949 | -0.1239 | density; EV_R |
| price_momentum__close_near_high60_pct__ge_0p0 | price_momentum | 13,592 | 7.50% | 18.74% | 1.3563 | 1.2327 | -0.1334 | min_train_EV_R |

我的解读：

- `gap_open_pct >= 3%` 是最强 LR 候选，density 也不高，但 EV_R = -0.2418，说明“右尾概率提升”没有转化成 H20 diagnostic payoff。
- RPS60 / RPS20 强度类候选能抓右尾，但 density 20%-30%，更像 broad regime / momentum state，而不是可单独冻结的 family。
- close near high60 也有可解释的右尾 lift，但 EV_R 仍然负，说明追高后的 H20 诊断成本不理想。

## 7. Top EV_R Candidates

| candidate_id | group_id | trigger_count | density | P_winner_given_signal | LR | LR_ci90_lower | EV_R | failed_rules |
|:--|:--|--:|--:|--:|--:|--:|--:|:--|
| volatility_state__atr20_contraction_ratio__le_0p8 | volatility_state | 34,777 | 19.19% | 15.58% | 1.0854 | 1.0103 | 0.1085 | density; risk_distance |
| volatility_state__atr20_contraction_ratio__le_1p0 | volatility_state | 94,407 | 52.09% | 15.11% | 1.0474 | 1.0164 | 0.0642 | density |
| volume_money__vol_ratio10__gt_2p0 | volume_money | 8,140 | 4.49% | 13.59% | 0.9250 | 0.8737 | -0.0658 | LR; CI; EV_R |
| volatility_state__atr20_pct__le_0p03 | volatility_state | 75,169 | 41.48% | 7.63% | 0.4860 | 0.4381 | -0.0735 | density; LR; EV_R; risk_distance |
| volume_money__vol_ratio10__gt_1p5 | volume_money | 22,287 | 12.30% | 13.86% | 0.9464 | 0.9183 | -0.1023 | density; LR; CI; EV_R |

我的解读：

- 唯一正 EV_R 的候选都来自 volatility contraction，但 density 太高，且 `atr20_contraction_ratio <= 0.8` 的 risk-distance ineligible 也触发失败。
- 这提示“波动收缩”可能是后续 search space 的重要方向，但不能用当前粗 primitive 直接冻结。更合理的 V2 方向可能是：volatility contraction 作为 context，再叠加低风险结构或 pullback hold，而不是把它当作单日 family。

## 8. Mandatory V3 Seed Baseline

V3 post30 seed 现在只作为 mandatory_composite_baseline 报告，不进入 frozen family selection。

| split | trigger_count | density | primary_positive_count | P_signal_given_winner | P_signal_given_non_winner | P_winner_given_signal | LR | EV_R | avg_win_R | avg_loss_R | failed_seed_rate | entry_buyability_rate | risk_distance_ineligible_rate | initial_risk_pct_p50 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 14,428 | 7.96% | 1,944 | 8.93% | 7.67% | 16.54% | 1.1654 | -0.1051 | 2.7063 | -1.7959 | 30.71% | 98.51% | 23.44% | 4.29% |
| validation | 8,429 | 7.74% | 368 | 8.80% | 7.77% | 5.76% | 1.1328 | -0.5000 | 2.1745 | -1.8089 | 27.26% | 98.64% | 29.54% | 4.03% |
| robustness | 8,793 | 8.03% | 656 | 8.51% | 7.59% | 10.97% | 1.1224 | 0.2100 | 2.7662 | -1.6923 | 23.03% | 97.95% | 30.00% | 3.78% |

我的判断：

- V3 seed 的 action-time LR 在三个 split 都大于 1，说明它不是完全无信息。
- 但 validation `P_winner_given_signal` 只有 5.76%，EV_R = -0.5000，是非常强的 warning。
- train / robustness 之间存在较大 regime 差异：robustness EV_R 转正，但 validation 明显恶化，所以不能把 robustness 的恢复解释成稳定 edge。
- risk-distance ineligible rate 在 validation / robustness 接近 30%，说明这个 profile 仍然容易出现在价格已经贴近参考位的位置，导致 R02 generic stop 下可执行风险距离不足。

我的猜测：V3 post30 seed 更像“winner 展开后的状态标记”，不是 evidence accumulation 的底层 family。它也许适合做 observation / tracking feature，但不适合单独作为新增风险预算依据。

## 9. Label Confusion

label confusion matrix 说明：H20 continuation 和 H10 failed_seed 在定义上互斥，H60 continuation 与 failed_seed 可以重叠。

| split | label_left | label_right | true/true count |
|:--|:--|:--|--:|
| train | continuation_h20 | continuation_h60 | 9,502 |
| train | continuation_h20 | failed_seed_forward | 0 |
| train | continuation_h60 | failed_seed_forward | 2,757 |
| validation | continuation_h20 | continuation_h60 | 2,298 |
| validation | continuation_h20 | failed_seed_forward | 0 |
| validation | continuation_h60 | failed_seed_forward | 899 |
| robustness | continuation_h20 | continuation_h60 | 4,258 |
| robustness | continuation_h20 | failed_seed_forward | 0 |
| robustness | continuation_h60 | failed_seed_forward | 745 |

这符合 label 定义：H20 continuation 要求中途不跌破 -6%，因此不会和 failed_seed_forward 同时为真。H60 continuation 没有内置 H10 fail-fast，所以可以先跌破 -6%，后面再走出 H60 continuation。

研究含义：如果后续做 evidence accumulation，不能简单把 failed_seed_forward 当作“彻底失败”。有些 H60 winner 会经历早期 -6% close drawdown。真正要解决的是：早期失败信号如何区分“应停止 build”的失败和“可承受 shakeout”的失败。

## 10. Gate Audit

| gate_id | actual | expected | status |
|:--|:--|:--|:--|
| min_3_non_baseline_families | 0 | >= 3 | failed |
| validation_primary_lr_gt_1 | False | True | failed |
| validation_at_least_2_ev_non_negative | 0 | >= 2 | failed |
| robustness_lr_ge_1 | False | True | failed |
| robustness_ev_ge_minus_005 | False | True | failed |
| no_h20_positive_h60_reverse | True | True | passed |
| validation_execution_feasible | False | True | failed |

这些 gate failure 的根源是没有任何非 baseline frozen family，因此 validation / robustness family-level gate 无法成立。不是“找到了 family 但 OOS 不好”，而是 train discovery 阶段已经没有合格 family。

## 11. Findings

1. 单日 strength/momentum 可以提高 right-tail probability，但不自动带来 positive EV_R。
   这点很关键。R02 的 primary label 是 h120 right-tail，EV_R 是 H20 diagnostic execution。当前结果说明“更像 winner”与“短期可执行成本可控”不是同一个问题。

2. 当前 search space 最大的问题是 primitive 太宽。
   RPS、near-high、industry breadth、survival absence 这类条件经常覆盖 20%-90% 的 eligible action-time rows。它们可做 context feature，但作为 family trigger 太粗。

3. 低 volatility / contraction 有研究价值，但不能原样进入 R03。
   它是少数能给出正 EV_R 的方向，但 density 和 risk-distance 问题没解决。它可能应该变成组合上下文，而不是 standalone family。

4. V3 post30 profile 的作用应降级。
   它仍然有 LR，但 validation EV_R 和 risk-distance 不支持把它当作 R03 family。更适合保留为 baseline comparison / profile marker。

5. R02 V1 的 archive 结论是合理的。
   如果现在进入 R03，会把一个没有 family pool 的问题硬推进到 evidence accumulation，后面只能通过 risk mapping 或 add rules 掩盖前置 discovery 的失败。

## 12. Guesses / 下一步研究方向

这些是猜测，不是当前 R02 V1 已证明的结论：

1. V2 search space 应该先缩小 action candidates，而不是继续扩大 primitive 数量。
   例如先要求 generic risk distance 可执行，或者先要求 pullback / contraction / structure hold，再评价 momentum / RPS / volume 是否提供增量证据。

2. 不要继续找“万能单日 entry signal”。
   当前强 LR 信号多是状态信号。后续更可能需要 episode-level family：例如 contraction period -> breakout day -> pullback hold，而不是单个 stock-day primitive。

3. 可以把 volatility contraction 作为 V2 的 context anchor。
   但它必须和低风险结构、买入可执行性一起定义，否则 density 太高。

4. failed_seed_forward 可能不能直接作为 hard stop label。
   因为 H60 continuation 与 failed_seed_forward 有重叠，说明右尾 episode 可能经历早期 shakeout。后续如果做 build-window，需要区分“失败后继续走强”和“失败后无效”的不同路径。

5. R03 暂时不应启动。
   更合理的是先做 R02 V2：重新定义 family search space，尤其把 execution feasibility 和 low-risk structure 从 diagnostic gate 提前到 candidate construction。

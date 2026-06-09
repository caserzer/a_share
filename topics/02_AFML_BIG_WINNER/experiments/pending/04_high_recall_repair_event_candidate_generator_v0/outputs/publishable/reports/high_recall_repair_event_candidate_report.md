# 高召回修复事件候选生成器 V0 报告

本实验是 event candidate generator，不是 primary model、不是策略、不是回测。高 recall 是主目标，precision / false positive 噪声留给后续模型。

## Final Decision

- decision: `candidate_generator_total_recall_blocked`
- target episodes: 866 total / 169 validation / 412 robustness
- raw family events: 42065
- setup-inclusive canonical-before-density events: 27542
- setup-inclusive canonical events: 6594
- source git revision: `31dc367b3f8f`
- upstream 02 decision: `reverse_lifecycle_sequence_supported_universal_dominance` / manifest hash `8f67723cbfb0` / git `ee0132a74764`
- upstream 03 decision: `event_contract_sample_blocked` / manifest hash `765f17fa8595` / git `db22957d6ea5`

02 提供冻结的 canonical big-winner episode denominator；03 说明严格 observable anchor 不足以形成可靠 edge，因此 04 改为高召回候选池，precision 交给后续 primary/meta 层处理。

## Data Source Check

| input | exists | sha256 prefix |
| :-- | --: | --: |
| upstream_reverse_lifecycle_manifest_json | True | 8f67723cbfb0 |
| upstream_big_winner_episode_reference_parquet | True | eba3a7f0af9a |
| upstream_observable_anchor_manifest_json | True | 765f17fa8595 |
| upstream_strict_event_pool_parquet | True | effd0a006008 |
| vwap_source_policy | True |  |

## Target Denominator

| episode split | episodes |
| :-- | --: |
| robustness | 412 |
| train | 285 |
| validation | 169 |

| market regime | episodes |
| :-- | --: |
| risk_off | 453 |
| risk_on | 210 |
| transition | 203 |

## Co-headline Recall

| metric | total | validation | robustness |
|:--|--:|--:|--:|
| low+30 fixed-window recall | 39.5% | 51.5% | 34.2% |
| before-first-50pct actionable recall | 55.3% | 59.2% | 54.6% |
| low+20 support recall | 23.6% | 29.6% | 21.8% |

fast duration bucket 的 before-first-50pct recall 为 36.9%。这个读数用于检查 low+30 是否对快赢家虚高。

## Union Recall Detail

| window | setup n | setup recall | reclaim n | reclaim recall |
| :-- | --: | --: | --: | --: |
| pre-low 20 | 510 | 58.9% | 36 | 4.2% |
| low+10 | 119 | 13.7% | 161 | 18.6% |
| low+20 | 204 | 23.6% | 311 | 35.9% |
| low+30 | 342 | 39.5% | 405 | 46.8% |
| low+60 | 456 | 52.7% | 534 | 61.7% |
| low+120 | 618 | 71.4% | 641 | 74.0% |
| before first 50% | 479 | 55.3% | 603 | 69.6% |
| before episode high | 494 | 57.0% | 614 | 70.9% |

pre-low 20 是 diagnostic-only。它只能说明候选事件在 retrospective low 附近是否已经出现，不能解释为事前精准识别低点。

## Duration Bucket Actionability

| bucket | episodes | low+30 recall | before-first recall | late share |
| :-- | --: | --: | --: | --: |
| fast | 103 | 39.8% | 36.9% | 7.3% |
| long | 551 | 38.5% | 61.0% | 0.0% |
| medium | 212 | 42.0% | 49.5% | 0.0% |

lead time to first 50pct: mean 50.8, median 50.0, p25/p75 28.0 / 73.0 sessions

## Density / Executability

- setup-inclusive density p95 / mean: 3.33 / 3.33
- reclaim-based density p95 / mean: 1.72 / 1.72
- executable rate: 99.9%
- main 20d label complete rate: 99.7%

| family | union | scope | raw | kept | folded | lost capture | density p95 |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| E0_seed_low_setup | raw_family | raw_family | 23785 | 23785 | 0 | 0 | 39.00 |
| E1_first_ema60_reclaim | raw_family | raw_family | 4724 | 4724 | 0 | 0 | 6.30 |
| E2_reclaim_quality_burst | raw_family | raw_family | 3137 | 3137 | 0 | 0 | 3.00 |
| E3_early_no_false_repair | raw_family | raw_family | 5870 | 5870 | 0 | 0 | 6.95 |
| E4_early_relative_strength_turn | raw_family | raw_family | 2778 | 2778 | 0 | 0 | 3.00 |
| E5_strict_rank_persistence_reference | raw_family | raw_family | 1771 | 1771 | 0 | 0 | 3.00 |
| E_union_reclaim_based_candidate | reclaim_based | canonical_before_density | 3764 | 3137 | 627 | 35 | 4.00 |
| E_union_reclaim_based_candidate | reclaim_based | density_kept_canonical | 3137 | 3137 | 0 | 0 | 3.00 |
| E_union_high_recall_repair_candidate | setup_inclusive | canonical_before_density | 27542 | 6594 | 20948 | 1404 | 44.00 |
| E_union_high_recall_repair_candidate | setup_inclusive | density_kept_canonical | 6594 | 6594 | 0 | 0 | 7.60 |

## Density Loss

| union | window | raw recall | canonical recall | density-kept recall | loss | lost n |
| :-- | --: | --: | --: | --: | --: | --: |
| setup_inclusive | pre_low_20d | 59.5% | 59.5% | 58.9% | 0.6% | 5 |
| setup_inclusive | low_to_plus_10d | 59.1% | 59.1% | 13.7% | 45.4% | 393 |
| setup_inclusive | low_to_plus_20d | 59.5% | 59.5% | 23.6% | 35.9% | 311 |
| setup_inclusive | low_to_plus_30d | 63.4% | 63.4% | 39.5% | 23.9% | 207 |
| setup_inclusive | low_to_plus_60d | 69.1% | 69.1% | 52.7% | 16.4% | 142 |
| setup_inclusive | low_to_plus_120d | 80.5% | 80.5% | 71.4% | 9.1% | 79 |
| setup_inclusive | before_first_50pct | 71.2% | 71.2% | 55.3% | 15.9% | 138 |
| setup_inclusive | before_episode_high | 71.9% | 71.9% | 57.0% | 14.9% | 129 |
| reclaim_based | pre_low_20d | 4.8% | 4.8% | 4.2% | 0.7% | 6 |
| reclaim_based | low_to_plus_10d | 19.2% | 19.2% | 18.6% | 0.6% | 5 |
| reclaim_based | low_to_plus_20d | 36.5% | 36.5% | 35.9% | 0.6% | 5 |
| reclaim_based | low_to_plus_30d | 47.3% | 47.3% | 46.8% | 0.6% | 5 |
| reclaim_based | low_to_plus_60d | 62.2% | 62.2% | 61.7% | 0.6% | 5 |
| reclaim_based | low_to_plus_120d | 74.4% | 74.4% | 74.0% | 0.3% | 3 |
| reclaim_based | before_first_50pct | 70.0% | 70.0% | 69.6% | 0.3% | 3 |
| reclaim_based | before_episode_high | 71.2% | 71.2% | 70.9% | 0.3% | 3 |

## Event Family Ablation

| variant | union | low+30 | before-first | without E0 | E0-only share |
| :-- | --: | --: | --: | --: | --: |
| setup_inclusive_vs_reclaim_based | setup_inclusive | 39.5% | 55.3% | 46.8% | 42.1% |
| reclaim_based_without_E0 | reclaim_based | 46.8% | 69.6% | 46.8% | NA |
| E0_raw_family | raw_family | 62.5% | 70.7% | NA | 26.6% |
| E1_raw_family | raw_family | 47.2% | 69.9% | NA | NA |
| E2_raw_family | raw_family | 46.8% | 69.6% | NA | NA |
| E3_raw_family | raw_family | 42.4% | 61.3% | NA | NA |
| E4_raw_family | raw_family | 44.7% | 65.9% | NA | NA |
| E5_raw_family | raw_family | 11.2% | 39.4% | NA | NA |

Ablation 应与 headline 同级解读：如果 E0-only share 高，说明宽网主要来自 setup-inclusive 低点候选；E1/E2/E4 的价值要看 reclaim-based 与 raw family 行的边际 recall，而不是 headline 数字本身。

## Label Readiness

- setup-inclusive event-anchored 120d big-winner positive rate: 12.8%
- setup-inclusive near-winner 120d rate: 15.1%
- setup-inclusive false-repair 20d rate: 19.9%
- 120d outcome complete rate: 90.8%

| event split | events | big winner | near winner | false 10d | false 20d | cluster pos |
| :-- | --: | --: | --: | --: | --: | --: |
| robustness | 2465 | 21.5% | 20.5% | 6.5% | 16.0% | 400 |
| train | 1926 | 11.7% | 13.8% | 10.1% | 19.7% | 225 |
| validation | 2203 | 6.4% | 11.8% | 11.4% | 24.5% | 140 |

### False-Repair By Regime

| event split | regime | events | false 10d | false 20d |
| :-- | --: | --: | --: | --: |
| robustness | risk_off | 745 | 6.4% | 15.6% |
| robustness | risk_on | 1164 | 6.2% | 16.5% |
| robustness | transition | 556 | 7.0% | 15.6% |
| train | risk_off | 627 | 8.5% | 16.1% |
| train | risk_on | 745 | 11.5% | 24.4% |
| train | transition | 554 | 9.9% | 17.3% |
| validation | risk_off | 998 | 14.0% | 25.6% |
| validation | risk_on | 333 | 10.2% | 26.4% |
| validation | transition | 872 | 8.8% | 22.6% |

| event split | events | positive | negative | 120d complete | avg uniqueness | concurrency p95 |
| :-- | --: | --: | --: | --: | --: | --: |
| robustness | 2465 | 400 | 1464 | 1864 | 0.01 | 423.20 |
| train | 1926 | 225 | 1697 | 1922 | 0.00 | 325.70 |
| validation | 2203 | 140 | 2063 | 2203 | 0.01 | 460.00 |

capture 是 episode-anchored recall；positive label 是 event-anchored 120d outcome。捕获了 target episode 的 event 仍可能因为从自身 t0 往后 MFE 不足 50% 而是 negative，两者不得混算。

confirm_20 / failure_10 只是短期 tradeability / repair durability proxy，不是 120d big-winner 的代理标签。

## Forward Diagnostics

| horizon | complete | mean return | mean MFE | mean MAE |
| :-- | --: | --: | --: | --: |
| 10d | 6586 | 0.4% | 6.2% | -5.3% |
| 20d | 6575 | 1.0% | 9.1% | -7.1% |
| 30d | 6532 | 1.4% | 11.5% | -8.6% |
| 60d | 6287 | 2.0% | 17.1% | -11.9% |
| 120d | 5989 | 3.2% | 26.0% | -16.2% |

## Risk-Off Diagnostic

| metric | value |
| :-- | --: |
| episode recall low+30 / before-first | 47.7% / 61.8% |
| setup events | 2370 |
| 120d positive rate | 15.1% |
| false repair 20d rate | 19.9% |

## Decision Replay

- target count gates: total 866 >= 150; validation 169 >= 30; robustness 412 >= 30
- executable / main label completeness: 99.9% / 99.7%
- total fixed-window recall low+30 / low+20: 39.5% / 23.6%
- validation fixed-window recall low+30 / low+20: 51.5% / 29.6%
- robustness fixed-window recall low+30 / low+20: 34.2% / 21.8%
- density p95 setup/reclaim: 3.33 / 1.72
- before-first recall total/validation/robustness: 55.3% / 59.2% / 54.6%
- final decision by short-circuit order: `candidate_generator_total_recall_blocked`

## Insight

当前候选池的主要风险是 recall 是否足够早，而不是 precision 是否已经像交易信号。若 before-first-50pct 低于 low+30，说明候选事件能覆盖 episode，但对快赢家偏晚；此时应该寻找更早 anchor 或放宽 setup-inclusive 入口，而不是把 E2/E4 质量过滤继续收紧。

## Next Step

若 decision 为 supported/noisy_precision，可进入 primary model / meta-labeling 研究；若为 actionability_late_blocked，下一步应寻找更早 anchor，而不是继续收紧过滤。

# R03b 信号序列 Big-Winner 与路径诊断报告

Final decision: `descriptive_sequence_diagnostic_complete`

## 1. 结论边界

本诊断明确区分 big-winner labels 和 path labels。
P_good / P_bad 不得解读为 P(big winner | signal)。
本实验不产出 production signal。
本实验不产出 position size。
本实验不产出 R03 risk-budget allocation。

本次 R03b 只回答一个描述性问题：在 seed signal 出现后，如果 T+3 到 T+30 之间陆续出现其它 family 的 fresh signal，`big_winner_forward_h120_close_anchor`、`good_path`、`bad_path` 的条件概率是否发生变化。所有 checkpoint pattern 都只使用当时已经可观察的 signal，不能使用 checkpoint 之后才出现的信号。

## 2. 输入与样本完整性

输入 reconciliation 是干净的。7 个 frozen single-family signal 在 path-query CSV 与 precision action-time panel 之间完全对齐：

| family_id | path_signal_count | precision_signal_occurs_count | matched_signal_count | path_only_count | precision_only_count |
|:--|--:|--:|--:|--:|--:|
| momentum_rps | 44,120 | 44,120 | 44,120 | 0 | 0 |
| oscillator | 23,132 | 23,132 | 23,132 | 0 | 0 |
| price_trend | 34,592 | 34,592 | 34,592 | 0 | 0 |
| pullback_drawdown | 56,446 | 56,446 | 56,446 | 0 | 0 |
| range_breakout | 68,679 | 68,679 | 68,679 | 0 | 0 |
| volatility_band | 28,211 | 28,211 | 28,211 | 0 | 0 |
| volume_money | 22,806 | 22,806 | 22,806 | 0 | 0 |

核心输出规模：

| artifact | rows |
|:--|--:|
| seed episode panel | 11,003 |
| signal timeline panel | 249,435 |
| sequence step panel | 87,475 |
| checkpoint state panel | 55,015 |
| offset hazard panel | 2,479 |

## 3. Seed Base Rate

Seed 层面的基础概率如下：

| split | seed_episode_count | big_winner_label_denominator | big_winner_count | big_winner_rate | path_label_denominator | good_count | bad_count | P_good | P_bad | no_fresh_episode_count | fresh_episode_count | failed_before_first_primary_fresh_count |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 5,139 | 4,134 | 628 | 0.1519 | 4,270 | 1,460 | 2,688 | 0.3419 | 0.6295 | 2,288 | 2,851 | 2,227 |
| validation | 2,891 | 2,199 | 122 | 0.0555 | 2,216 | 729 | 1,406 | 0.3290 | 0.6345 | 1,216 | 1,675 | 1,194 |
| robustness | 2,973 | 2,092 | 200 | 0.0956 | 2,123 | 879 | 1,183 | 0.4140 | 0.5572 | 1,156 | 1,817 | 1,079 |
| all | 11,003 | 8,425 | 950 | 0.1128 | 8,609 | 3,068 | 5,277 | 0.3564 | 0.6130 | 4,660 | 6,343 | 4,500 |

第一个重要观察：`fresh_episode_count` 有 6,343，但 `failed_before_first_primary_fresh_count` 也有 4,500。这说明“没有等到 fresh signal”本身很大程度上是 survival 问题，而不是单纯缺少后续信号。后续 fresh-count 的统计必须始终和 survival-bias audit 一起看。

## 4. Checkpoint Fresh-Count 结果

All split 下，fresh distinct family count 与 path label 的关系很强；与 big-winner rate 的关系存在，但明显弱很多。

| checkpoint | fresh_count | seed_episode_count | big_winner_den | big_winner_rate | P_good | P_bad |
|:--|:--|--:|--:|--:|--:|--:|
| T+3 | 0 | 5,764 | 4,395 | 0.0933 | 0.3625 | 0.5938 |
| T+3 | 1 | 1,417 | 1,094 | 0.1362 | 0.4715 | 0.4929 |
| T+3 | 2 | 849 | 661 | 0.1286 | 0.5725 | 0.4068 |
| T+3 | 3plus | 914 | 708 | 0.1723 | 0.7181 | 0.2639 |
| T+5 | 0 | 3,982 | 2,996 | 0.0801 | 0.3647 | 0.5817 |
| T+5 | 1 | 1,421 | 1,129 | 0.1275 | 0.4865 | 0.4672 |
| T+5 | 2 | 1,021 | 793 | 0.1248 | 0.5593 | 0.4111 |
| T+5 | 3plus | 1,613 | 1,255 | 0.1801 | 0.7288 | 0.2541 |
| T+10 | 0 | 1,855 | 1,362 | 0.0881 | 0.4040 | 0.5232 |
| T+10 | 1 | 1,223 | 942 | 0.0966 | 0.5187 | 0.4098 |
| T+10 | 2 | 1,040 | 810 | 0.1037 | 0.5927 | 0.3503 |
| T+10 | 3plus | 2,442 | 1,918 | 0.1684 | 0.7723 | 0.2042 |
| T+20 | 0 | 598 | 414 | 0.1256 | 0.5023 | 0.4206 |
| T+20 | 1 | 682 | 504 | 0.1071 | 0.5786 | 0.3262 |
| T+20 | 2 | 828 | 613 | 0.0897 | 0.6282 | 0.2885 |
| T+20 | 3plus | 2,942 | 2,335 | 0.1666 | 0.8302 | 0.1471 |
| T+30 | 0 | 305 | 208 | 0.1731 | 0.6204 | 0.3287 |
| T+30 | 1 | 430 | 316 | 0.1424 | 0.6544 | 0.2263 |
| T+30 | 2 | 627 | 454 | 0.1013 | 0.6602 | 0.2424 |
| T+30 | 3plus | 2,906 | 2,299 | 0.1744 | 0.8687 | 0.1032 |

初步判断：

- `P_good` 随 fresh count 增加非常稳定，`P_bad` 同步下降也非常稳定。例如 T+10 从 fresh_count=0 到 3plus，`P_good` 从 0.4040 到 0.7723，`P_bad` 从 0.5232 到 0.2042。
- Big-winner rate 的提升没有 path label 那么稳定。T+3/T+5/T+10 的 3plus 都明显高于 0 fresh，但 T+20/T+30 的非 3plus bucket 不单调，T+30 的 0 和 3plus 几乎一样。
- 因此，多 family fresh sequence 更像是“路径继续走强 / 未失败”的描述性证据，而不是可以直接视作 big-winner 捕捉规则。

## 5. Split 稳定性

T+10 是比较有代表性的 checkpoint：

| split | fresh_count | seed_episode_count | big_winner_den | big_winner_rate | P_good | P_bad |
|:--|:--|--:|--:|--:|--:|--:|
| train | 0 | 784 | 656 | 0.1052 | 0.4015 | 0.5309 |
| train | 1 | 544 | 442 | 0.1357 | 0.5131 | 0.4148 |
| train | 2 | 413 | 337 | 0.1306 | 0.5983 | 0.3497 |
| train | 3plus | 1,118 | 933 | 0.2304 | 0.7760 | 0.1979 |
| validation | 0 | 436 | 288 | 0.0660 | 0.3857 | 0.5256 |
| validation | 1 | 318 | 234 | 0.0427 | 0.4895 | 0.4219 |
| validation | 2 | 297 | 228 | 0.0658 | 0.5614 | 0.3553 |
| validation | 3plus | 620 | 494 | 0.0850 | 0.7455 | 0.2244 |
| robustness | 0 | 635 | 418 | 0.0766 | 0.4206 | 0.5093 |
| robustness | 1 | 361 | 266 | 0.0789 | 0.5539 | 0.3903 |
| robustness | 2 | 330 | 245 | 0.1020 | 0.6135 | 0.3466 |
| robustness | 3plus | 704 | 491 | 0.1344 | 0.7920 | 0.1960 |

这里的结论很清楚：

- `P_good / P_bad` 的方向在 train、validation、robustness 三个 split 中都一致。
- Big-winner rate 的方向不如 path label 稳定。train 的 3plus 很强，robustness 有提升，validation 只是从 0.0660 到 0.0850，提升幅度很小。
- 如果后续要做候选规则，不能只看 train 里 T+10 3plus 的 0.2304；validation 的弱提升是必须面对的风险。

## 6. Survival Bias

Survival-bias audit 说明，大量 episode 在 T+30 前已经失败：

| split | failed_before_t3 | failed_t3_to_t5 | failed_t6_to_t10 | failed_t11_to_t20 | failed_t21_to_t30 | survived_t30_no_fresh | survived_t30_with_fresh |
|:--|--:|--:|--:|--:|--:|--:|--:|
| train | 846 | 678 | 747 | 701 | 372 | 61 | 824 |
| validation | 364 | 426 | 424 | 434 | 206 | 22 | 500 |
| robustness | 323 | 297 | 306 | 375 | 204 | 77 | 799 |
| all | 1,533 | 1,401 | 1,477 | 1,510 | 782 | 160 | 2,123 |

这组数据是解释 R03b 的关键：很多样本不是“没有后续信号”，而是先发生了 observable failure，所以根本没有机会积累后续 signal。R03b 的 fresh-count lift 因此不能被解释为“看到更多信号就能预测 big winner”，更合理的解释是：

```text
能活到后续 signal 出现的 episode，本身已经经过了一轮路径过滤。
后续信号越多，越像是持续活跃/持续趋势确认；
但这同时混入了 survival conditioning。
```

## 7. Kth Fresh Step

把第 1、第 2、第 3、第 4plus 个 fresh step 合并看，path label 的改善非常明显；big-winner 改善则更集中在部分 offset bucket：

| kth | status | offset_bucket | seed_episode_count | big_winner_den | big_winner_rate | path_den | P_good | P_bad |
|:--|:--|:--|--:|--:|--:|--:|--:|--:|
| 1 | not_reached | not_reached | 4,660 | 3,511 | 0.0926 | 3,577 | 0.0492 | 0.9374 |
| 1 | reached | t3_t5 | 4,240 | 3,317 | 0.1450 | 3,388 | 0.5741 | 0.3967 |
| 1 | reached | t6_t10 | 1,235 | 951 | 0.0841 | 981 | 0.5678 | 0.3680 |
| 1 | reached | t11_t20 | 713 | 533 | 0.0976 | 546 | 0.5842 | 0.3407 |
| 2 | reached | t3_t5 | 884 | 691 | 0.1910 | 712 | 0.7247 | 0.2570 |
| 2 | reached | t6_t10 | 1,280 | 1,023 | 0.1554 | 1,042 | 0.7207 | 0.2457 |
| 3 | reached | t6_t10 | 448 | 371 | 0.2022 | 379 | 0.8127 | 0.1583 |
| 4plus | reached | t11_t20 | 224 | 191 | 0.2304 | 192 | 0.9010 | 0.0833 |

这里最有价值的观察是：第 2、第 3、第 4plus 个 fresh step 对 path label 的解释力越来越强，但 big-winner rate 不按 step 数稳定递增。尤其第 1 个 fresh 在 T+6..T+20 出现时，big-winner rate 并不突出；第 2/3/4plus 的部分 bucket 才更强。

## 8. Sequence Pattern

足够样本的 sequence pattern 里，`other_sparse_patterns` 的高 depth 行表现最好，但它不是一个具体 pattern，而是多个稀疏 pattern 的合并桶：

| checkpoint / pattern | seed_episode_count | big_winner_den | big_winner_rate | P_good | P_bad |
|:--|--:|--:|--:|--:|--:|
| T+20 other_sparse_patterns depth=4 | 246 | 202 | 0.2327 | 0.9078 | 0.0728 |
| T+30 other_sparse_patterns depth=4 | 371 | 308 | 0.2078 | 0.9132 | 0.0772 |
| T+5 other_sparse_patterns depth=2 | 741 | 581 | 0.1997 | 0.7324 | 0.2508 |
| T+10 other_sparse_patterns depth=3 | 444 | 364 | 0.1978 | 0.8248 | 0.1456 |
| T+3 other_sparse_patterns depth=1 | 810 | 639 | 0.1612 | 0.6575 | 0.3195 |
| T+20 seed:multi_family_bundle depth=0 | 479 | 339 | 0.1445 | 0.5442 | 0.3903 |
| T+3 seed:multi_family_bundle -> fresh:pullback_drawdown | 606 | 468 | 0.1410 | 0.4551 | 0.5073 |
| T+10 seed:multi_family_bundle -> fresh:pullback_drawdown | 293 | 220 | 0.1136 | 0.5200 | 0.4133 |

我的判断：

- depth 越高，path label 越好，这和 fresh-count 结论一致。
- 但具体 sequence pattern 大量落入 sparse / collapsed bucket，说明现在还不适合直接挑某一个 family 顺序。
- `seed:multi_family_bundle -> fresh:pullback_drawdown` 有一定样本，但 big-winner rate 不突出；它更像是路径改善信号，而不是 big-winner 专属信号。

## 9. Signal Arrival Hazard

Fresh signal 的到达并不是均匀的。offset hazard 显示，T+3 是最大集中点：

| offset | fresh_family_id | kth_fresh_step_index | at_risk_episode_count | fresh_event_count | fresh_hazard_rate |
|--:|:--|--:|--:|--:|--:|
| 3 | pullback_drawdown | 1 | 6,517 | 2,070 | 0.3176 |
| 3 | range_breakout | 1 | 1,931 | 590 | 0.3055 |
| 3 | momentum_rps | 1 | 6,619 | 1,441 | 0.2177 |
| 3 | volatility_band | 1 | 6,612 | 755 | 0.1142 |
| 3 | price_trend | 1 | 6,283 | 697 | 0.1109 |
| 3 | oscillator | 1 | 7,040 | 731 | 0.1038 |
| 4 | range_breakout | 1 | 1,818 | 177 | 0.0974 |
| 3 | volume_money | 1 | 5,342 | 395 | 0.0739 |

这说明 first fresh 的 offset 分布本身高度集中。不能用“后段 fresh 少”证明 T+11..T+30 的 fresh signal 无效，因为很多 episode 已经在前段失败，且 fresh arrival hazard 在早期自然更高。

## 10. Big-Winner Label 与 Canonical Reference Audit

`big_winner_forward_h120_close_anchor` 的完整 label 分母为 8,425，占 seed episode 的 76.57%。完整 close-anchor label 内，big-winner rate 为 11.28%。

Canonical reference overlap 明显不是同一个口径：

| audit label | rate |
|:--|--:|
| canonical_ref_after_seed_within_30td | 0.0566 |
| canonical_ref_after_seed_within_120td | 0.1952 |
| close-anchor big_winner_forward_h120 rate | 0.1128 |

这验证了 requirement 的判断：canonical reference overlap 只能做 audit，不应该替代 close-anchor big-winner label。

## 11. 主要发现

1. 多 family fresh signal 对 `good_path / bad_path` 有稳定解释力。
   fresh count 越多，`P_good` 明显上升，`P_bad` 明显下降；这个方向在 train、validation、robustness 都成立。

2. 多 family fresh signal 对 big-winner 的解释力存在，但弱于 path label。
   T+3/T+5/T+10 的 3plus bucket 有更高 big-winner rate，但 validation split 的提升偏弱，T+20/T+30 的非 3plus bucket 不单调。

3. fresh-count lift 混入了 survival conditioning。
   all split 中有 6,703 个 episode 在 T+30 前失败，只有 2,123 个 survived_t30_with_fresh。后续信号更多，部分原因是 episode 先活下来了。

4. “第几个 fresh step”比“有没有 fresh”更有信息，但仍不能直接变成候选规则。
   第 2、第 3、第 4plus 个 fresh step 的 path label 更好，但 big-winner rate 在不同 offset bucket 之间波动较大。

5. sequence pattern 目前适合做候选方向收集，不适合冻结具体规则。
   高表现 pattern 大量来自 `other_sparse_patterns`，说明具体 family 顺序仍然稀疏；需要下一阶段专门设计 pattern pooling 或 family-set pooling。

## 12. 下一步建议

如果继续推进，我建议下一步不要直接做交易规则，而是做一个 R03c：

```text
R03c: checkpoint-observable fresh-count / fresh-step family-set pooling diagnostic
```

重点不是寻找单一 sequence pattern，而是验证更稳的 pooling 口径：

- `fresh_count_bucket` 是否在 validation / robustness 中稳定提升 big-winner rate；
- `kth_fresh_step_index + offset_bucket` 是否比单纯 fresh_count 更有解释力；
- 是否存在 family-set 层面的可复用 grouping，而不是稀疏的完整 sequence pattern；
- 所有分析继续把 big-winner、good_path、bad_path 分开，不允许用 path label 替代 big-winner。

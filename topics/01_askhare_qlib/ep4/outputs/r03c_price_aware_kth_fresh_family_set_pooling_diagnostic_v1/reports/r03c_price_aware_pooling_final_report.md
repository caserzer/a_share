# R03c Price-Aware Kth-Fresh 与 Family-Set Pooling 诊断报告

Final decision: `descriptive_price_aware_pooling_diagnostic_complete`

## 0. 结论摘要

R03c 的核心结论是：后续 fresh signal 的出现确实携带 sequence confirmation 信息，但它不是 fresh-entry alpha。R03c 的三个主问题在本轮数据下都应回答为 No：

1. `kth_fresh_step_bucket + offset_bucket` 没有在 checkpoint-aligned seed-anchor 口径下优于 fresh-count；它用更稀疏的 denominator 换来几乎为零的边际信息。
2. family-set pooling 在当前粒度下统计上塌掉；没有可复用的 stable family-set。
3. 加入 wait-return 后，fresh accumulation 更像 late confirmation，而不是更好的 entry timing。

第一类是 seed-anchor 的事后确认：价格已经上涨越多，seed-anchor 的 `P_good` 和 big-winner rate 往往越高。例如 T+30 checkpoint 中，`fresh_count=3plus` 且 latest fresh entry 已上涨 `up_gt_20pct` 的 seed-anchor big-winner rate 为 `43.0%`，seed `P_good` 为 `99.4%`。这说明它强烈识别了“已经走出来”的 episode。

第二类是 fresh-anchor 的剩余机会：同一批高 wait-return 行，从 fresh signal 之后重新计算 path，往往不再表现为好的 fresh-entry path。仍以上述 T+30 `fresh_count=3plus / up_gt_20pct` 为例，fresh-anchor big-winner rate 降到 `16.6%`，fresh `P_good` 只有 `21.5%`，fresh `P_bad` 为 `78.5%`。这更像 late confirmation，而不是一个可直接转化为 fresh-entry rule 的证据。

因此，R03c 不支持把“等到更多 fresh signal”解释成更好的买点，也不建议进入围绕 R03c outputs 的 formal validation。它真正有价值的产出是方法论上的：价格锚点分离首次定量暴露了 seed-anchor lift 被 wait-return / survival conditioning 偷走了多少；survival audit 则暴露了约 `41%` seed 在第一根 clean fresh 前已经 failure。后续应停止把 fresh-signal accumulation 当作 entry 维度，把它保留为持仓状态或失败解释变量。

## 1. 硬性边界

本诊断明确区分 seed-anchor big-winner、fresh-anchor big-winner 和 path labels。
P_good / P_bad 不得解读为 P(big winner | signal)。
fresh-anchor outcome 不能替代 seed-anchor outcome。
不同 row grain 的 explanatory-power lift 不得直接比较。

本实验不产出 production signal。
本实验不产出 entry rule。
本实验不产出 position size。
本实验不产出 R03 risk-budget allocation。

## 2. 输入完整性与样本规模

本轮 R03c runner 和 validator 均完成，validation status 为 `passed`，failed checks 为空。所有 clean primary fresh step 的 price/path reconciliation 均通过。

| split | seed_episode_count | clean_primary_fresh_step_count |
|:--|--:|--:|
| train | 5,139 | 5,550 |
| validation | 2,891 | 3,150 |
| robustness | 2,973 | 3,602 |
| all | 11,003 | 12,302 |

核心 denominator：

| metric | value |
|:--|--:|
| seed_episode_count | 11,003 |
| clean_primary_fresh_step_count | 12,302 |
| fresh_anchor_big_winner_denominator | 9,567 |
| fresh_path_denominator | 9,771 |
| price_reconciliation_passed_rows | 12,302 |
| price_reconciliation_failed_rows | 0 |

这说明本次诊断的 row-level join 没有发生缺失映射或 same-offset multi-family 不一致问题。需要注意的是，fresh path 有 `2,531` 行为 `censored_or_invalid`，因此 fresh-anchor path rate 的 denominator 小于 fresh-step 总数。

## 3. 等待价格变化：fresh signal 出现时价格已经涨了多少

按 fresh-entry price 计算，等待成本随第几个 fresh step 明显上升。更关键的是，seed-anchor big-winner rate 随 kth 单调上升，而 fresh-anchor big-winner rate 基本不升：

| kth_fresh_step_bucket | fresh_step_count | unique_seed_count | wait_return_p50 | pct_wait_gt_10pct | seed_anchor_big_winner_rate | fresh_anchor_big_winner_rate | fresh_P_good | fresh_P_bad |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| 1 | 6,343 | 6,343 | 2.6% | 6.3% | 12.7% | 10.5% | 36.1% | 60.3% |
| 2 | 3,753 | 3,753 | 5.2% | 17.3% | 14.4% | 10.4% | 37.6% | 59.4% |
| 3 | 1,649 | 1,649 | 7.4% | 30.5% | 15.2% | 9.4% | 34.4% | 62.1% |
| 4plus | 557 | 481 | 10.0% | 50.4% | 17.5%-18.3% | 9.7% | 34.9% | 62.7% |

解释：

- 第 1 个 fresh step 的中位等待收益只有 `2.6%`，其中 `>10%` 的比例为 `6.3%`。
- 到第 3 个 fresh step，中位等待收益升到 `7.4%`，`>10%` 的比例达到 `30.5%`。
- 到第 4plus 个 fresh step，中位等待收益达到 `10.0%`，一半以上 fresh-step 已经上涨超过 `10%`。
- seed-anchor big-winner rate 从约 `12.7%` 上升到约 `17.5%`-`18.3%`，说明 kth 携带“这个 episode 已经跑赢”的状态信息。
- 但 fresh-anchor outcome 没有随 kth 上升而改善：fresh big-winner rate 大致在 `9.4%` 到 `10.5%`，fresh `P_bad` 维持在约 `59%` 到 `63%`。

这意味着 kth 的真实含义不是“第 k 个 fresh signal 后更值得进入”，而是“该 seed episode 已经更可能处于跑赢状态”。这是 R03c 最直接的 take-away：seed-anchor 升，fresh-anchor 平。

## 4. Wait-return bucket 与 fresh-anchor 剩余空间

按 fresh-entry 等待收益分桶：

| wait_return_bucket | fresh_step_count | unique_seed_count | wait_return_p50 | fresh_anchor_big_winner_rate | fresh_P_good | fresh_P_bad |
|:--|--:|--:|--:|--:|--:|--:|
| down_or_flat | 852 | 776 | -0.6% | 7.7% | 39.1% | 55.4% |
| up_0_5pct | 6,247 | 4,413 | 2.5% | 8.6% | 37.2% | 58.5% |
| up_5_10pct | 3,359 | 2,651 | 6.9% | 11.3% | 35.6% | 62.1% |
| up_10_20pct | 1,523 | 1,281 | 12.8% | 14.9% | 35.5% | 63.2% |
| up_gt_20pct | 312 | 269 | 24.8% | 16.5% | 21.1% | 78.9% |
| missing_or_invalid | 9 | 9 | NA | 0.0% | NA | NA |

发现：

- 等待价格上涨越多，fresh-anchor big-winner rate 有一定上升，从 `8.6%` 到 `16.5%`。
- 但 path label 更差：`up_gt_20pct` 的 fresh `P_good` 只有 `21.1%`，fresh `P_bad` 高达 `78.9%`。
- 因此，高 wait-return 的信息不能简单解释为“买入后更优”。更合理的解释是：这些行在 seed-anchor 视角中已经证明趋势很强，但 fresh-entry 之后剩余空间和回撤路径并不稳定。

## 5. Fresh-count 加入价格后是否仍然成立

checkpoint price-conditioned summary 显示，fresh-count 的 seed-anchor lift 主要集中在已经上涨的 bucket 中，尤其是 `up_10_20pct` 和 `up_gt_20pct`。这说明 fresh-count 的一部分解释力来自“价格已经走出来”的确认。

T+10 关键行：

| fresh_count_bucket | wait_bucket | seed_episode_count | seed_anchor_big_winner_rate | seed_P_good | seed_P_bad | fresh_anchor_big_winner_rate | fresh_P_good | fresh_P_bad | wait_return_p50 |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| 0 | no_fresh | 5,528 | 9.4% | 13.3% | 84.2% | NA | NA | NA | NA |
| 1 | up_0_5pct | 1,095 | 7.3% | 35.9% | 57.8% | 6.4% | 24.0% | 72.1% | 1.6% |
| 1 | up_5_10pct | 169 | 16.0% | 73.3% | 24.4% | 13.4% | 25.6% | 73.7% | 6.6% |
| 1 | up_10_20pct | 48 | 34.2% | 97.4% | 2.6% | 21.1% | 18.4% | 81.6% | 13.7% |
| 3plus | up_0_5pct | 914 | 9.7% | 49.4% | 45.8% | 8.9% | 28.0% | 69.7% | 3.6% |
| 3plus | up_5_10pct | 1,134 | 16.4% | 78.6% | 20.4% | 11.1% | 31.2% | 66.8% | 6.9% |
| 3plus | up_10_20pct | 481 | 29.0% | 96.3% | 3.7% | 18.6% | 32.7% | 66.2% | 12.6% |
| 3plus | up_gt_20pct | 81 | 34.8% | 98.5% | 1.5% | 12.3% | 10.6% | 89.4% | 25.4% |

T+30 关键行：

| fresh_count_bucket | wait_bucket | seed_episode_count | seed_anchor_big_winner_rate | seed_P_good | seed_P_bad | fresh_anchor_big_winner_rate | fresh_P_good | fresh_P_bad | wait_return_p50 |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| 0 | no_fresh | 4,660 | 9.3% | 4.9% | 93.7% | NA | NA | NA | NA |
| 1 | up_0_5pct | 751 | 7.3% | 18.5% | 74.3% | 6.5% | 11.6% | 84.3% | 1.6% |
| 1 | up_10_20pct | 52 | 35.0% | 97.5% | 2.5% | 22.5% | 30.8% | 69.2% | 13.5% |
| 1 | up_gt_20pct | 21 | 50.0% | 93.3% | 6.7% | 7.1% | 20.0% | 80.0% | 26.9% |
| 3plus | up_0_5pct | 1,082 | 6.9% | 38.3% | 54.2% | 6.6% | 21.4% | 74.5% | 3.4% |
| 3plus | up_5_10pct | 1,581 | 11.8% | 76.9% | 21.3% | 8.4% | 28.7% | 68.9% | 7.1% |
| 3plus | up_10_20pct | 978 | 23.0% | 98.3% | 1.7% | 13.0% | 35.0% | 63.3% | 12.8% |
| 3plus | up_gt_20pct | 205 | 43.0% | 99.4% | 0.6% | 16.6% | 21.5% | 78.5% | 24.7% |

结论：

- 在 seed-anchor 上，fresh-count 加价格后仍然有描述性区分度。
- 但区分度最强的地方同时也是 wait-return 较高的地方。
- fresh-anchor path 没有同步改善，尤其 `up_gt_20pct` 经常出现 seed `P_good` 极高但 fresh `P_bad` 也极高的情况。

## 6. Checkpoint-aligned explanatory power

下面只比较 checkpoint-aligned schemes。fresh-step grain 与 family-set pooling grain 不能和 checkpoint grain 的 lift 绝对值直接横向比较。

| split | grouping_scheme | outcome_family | evaluated_rows | bucket_count | sufficient_bucket_count | weighted_abs_lift_vs_parent | interpretation_status |
|:--|:--|:--|--:|--:|--:|--:|:--|
| validation | checkpoint_fresh_count | seed_anchor_big_winner | 10,995 | 20 | 20 | 0.0155 | baseline |
| validation | checkpoint_latest_kth_offset | seed_anchor_big_winner | 10,995 | 42 | 14 | 0.0156 | no_gain_more_sparse |
| validation | checkpoint_fresh_count | seed_path_good_bad | 11,080 | 20 | 20 | 0.4207 | baseline |
| validation | checkpoint_latest_kth_offset | seed_path_good_bad | 11,080 | 42 | 14 | 0.4130 | no_gain_more_sparse |
| robustness | checkpoint_fresh_count | seed_anchor_big_winner | 10,460 | 20 | 20 | 0.0234 | baseline |
| robustness | checkpoint_latest_kth_offset | seed_anchor_big_winner | 10,460 | 42 | 15 | 0.0245 | no_material_gain_more_sparse |
| robustness | checkpoint_fresh_count | seed_path_good_bad | 10,615 | 20 | 20 | 0.4276 | baseline |
| robustness | checkpoint_latest_kth_offset | seed_path_good_bad | 10,615 | 42 | 15 | 0.4216 | no_gain_more_sparse |

解释：

- 对 seed-anchor big-winner，`latest kth-offset` 没有超过 `fresh_count`：validation 为 `0.0155` vs `0.0156`，robustness 为 `0.0234` vs `0.0245`。
- 对 seed path good-bad，`latest kth-offset` 也没有超过 `fresh_count`：validation 为 `0.4207` vs `0.4130`，robustness 为 `0.4276` vs `0.4216`。
- denominator 明显变差：bucket 从 `20` 增到 `42`，但 sufficient buckets 从 `20` 掉到 `14`-`15`。
- 对 fresh-anchor outcome，`latest kth-offset` 和 `latest kth-offset + wait` 的 lift 更高，但这是 fresh-anchor grain 的剩余路径诊断，不应拿来替代 seed-anchor precision。

因此，问题“`kth_fresh_step_index + offset_bucket` 是否比单纯 fresh_count 更有解释力”的答案应写得更明确：No。它是净劣化，不只是 similar：更稀疏的 denominator，没有可见信息增益。

## 7. Kth + offset + wait 的具体模式

按 kth/offset/wait 展开后，大样本行显示出一个非常一致的现象：seed-anchor 表现可以很强，但 fresh-anchor path 往往偏弱。

| kth | offset_bucket | wait_bucket | added_family_count_bucket | fresh_step_count | seed_bw_rate | fresh_bw_rate | seed_P_good | seed_P_bad | fresh_P_good | fresh_P_bad | fresh_max_gain_p50 | fresh_max_drawdown_p50 |
|:--|:--|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 1 | t3_t5 | up_0_5pct | 1 | 1,412 | 12.1% | 11.0% | 48.0% | 47.2% | 34.4% | 62.0% | 16.5% | -23.6% |
| 1 | t3_t5 | up_0_5pct | 2plus | 1,349 | 11.7% | 9.9% | 54.5% | 42.5% | 36.9% | 60.2% | 16.8% | -23.1% |
| 1 | t3_t5 | up_5_10pct | 2plus | 622 | 19.7% | 14.2% | 82.1% | 17.5% | 33.8% | 63.7% | 18.6% | -28.9% |
| 2 | t6_t10 | up_5_10pct | 2plus | 245 | 18.6% | 13.1% | 83.3% | 15.3% | 36.9% | 60.1% | 18.6% | -23.7% |
| 2 | t6_t10 | up_5_10pct | 1 | 235 | 13.7% | 7.6% | 82.5% | 15.9% | 36.0% | 61.9% | 15.2% | -25.1% |

这张表的主要启发是：

- seed-anchor 的 `P_good` 很容易在 `up_5_10pct` 后显著抬升。
- 但同一行的 fresh `P_bad` 仍然经常在 `60%` 以上。
- fresh max gain 中位数仍有 `15%` 到 `19%`，但 max drawdown 中位数也在 `-23%` 到 `-29%`。这不应解释为 fresh-entry 路径被特别污染；更准确的判断是，它没有明显优于 R02 single-family baseline，仍处在 baseline 式高回撤路径中。

## 8. Family-set pooling：denominator 够不够，能不能复用

R03c V1 只启用 `fresh_added_family_set`、`cumulative_family_set_after_step`、`family_presence_signature`；不启用 `family_role_set`。

all split 下 sample sufficient 的主要 family-set 行如下：

| pooling_level | pooling_key | kth | offset | wait_bucket | fresh_step_count | seed_bw_rate | fresh_bw_rate | seed_P_good | seed_P_bad | fresh_P_good | fresh_P_bad | wait_p50 | fresh_clean_or_tradable_rate | fresh_early_failure_rate | stability |
|:--|:--|:--|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| fresh_added_family_set | pullback_drawdown | 1 | t3_t5 | up_0_5pct | 536 | 14.8% | 14.1% | 45.4% | 51.2% | 30.8% | 67.6% | 1.9% | 21.1% | 48.1% | unstable |
| fresh_added_family_set | momentum_rps / pullback_drawdown | 1 | t3_t5 | up_0_5pct | 401 | 13.0% | 10.9% | 54.5% | 44.5% | 38.9% | 58.2% | 2.3% | 25.7% | 38.9% | unstable |
| fresh_added_family_set | range_breakout | 1 | t3_t5 | up_0_5pct | 225 | 11.8% | 10.2% | 46.3% | 48.9% | 36.8% | 61.1% | 1.6% | 27.1% | 38.2% | unstable |
| fresh_added_family_set | volume_money | 1 | t6_t10 | up_0_5pct | 220 | 7.3% | 8.0% | 50.0% | 41.0% | 40.1% | 55.8% | 1.3% | 25.0% | 23.2% | unstable |

split stability audit 和 sufficient bucket 比例：

| metric | value |
|:--|--:|
| validation family_set_pooling sufficient buckets | 8 / 258 = 3.1% |
| validation family_set_pooling_wait_bucket sufficient buckets | 4 / 629 = 0.6% |
| stable_descriptive family-set | 0 |
| split_missing | 2,753 |
| denominator_thin | 1,338 |
| unstable | 4 |

方向层面虽然有 `3,072` 行是 `direction_only`，但这些行大多被 `split_missing` 或 `denominator_thin` 拦住；最终没有 `stable_descriptive` family-set。更准确的判断不是“暂时没找到稳定 family-set”，而是：当前粒度下 family-set pooling 完全不能支持复用结论。除非把 pooling 粗化回 `distinct_family_count in {1, 2, 3plus}` 一类结构，或者显著扩大样本，否则继续在完整 family-set 层面找 pattern 是低性价比方向。

## 9. Family-set 是否依赖过高 wait-return

高 wait-return 依赖最明显的是 cumulative family-set，尤其是已经积累到 6 到 7 个 family 的状态。

| pooling_level | pooling_key | total_steps | wait_p50 | pct_wait_gt_10pct | pct_wait_gt_20pct | fresh_bw_rate | fresh_edge |
|:--|:--|--:|--:|--:|--:|--:|--:|
| cumulative_family_set_after_step | momentum_rps / oscillator / price_trend / pullback_drawdown / range_breakout / volatility_band / volume_money | 2,866 | 8.7% | 40.3% | 8.0% | 11.4% | -29.7% |
| cumulative_family_set_after_step | momentum_rps / oscillator / price_trend / pullback_drawdown / range_breakout / volatility_band | 407 | 8.3% | 34.9% | 7.9% | 13.0% | -31.8% |
| fresh_added_family_set | price_trend | 372 | 7.4% | 25.3% | 0.0% | 9.7% | -22.1% |
| fresh_added_family_set | oscillator | 1,534 | 4.1% | 21.6% | 3.8% | 8.7% | -19.1% |
| cumulative_family_set_after_step | oscillator / price_trend / pullback_drawdown / range_breakout / volatility_band / volume_money | 490 | 6.1% | 20.8% | 3.3% | 5.7% | -28.7% |
| fresh_added_family_set | volatility_band | 1,333 | 4.3% | 20.0% | 3.4% | 11.1% | -21.4% |
| fresh_added_family_set | volume_money | 1,625 | 2.4% | 15.8% | 4.9% | 9.2% | -19.5% |
| fresh_added_family_set | pullback_drawdown | 1,122 | 2.5% | 3.0% | 0.3% | 11.6% | -30.6% |

解释：

- `cumulative_family_set_after_step` 的完整 7-family 状态 denominator 最大，`2,866` 行，但 `40.3%` 的 rows 已经上涨超过 `10%`，`8.0%` 超过 `20%`。
- 它的 fresh-edge 为 `-29.7%`，说明 fresh `P_bad` 明显高于 fresh `P_good`。
- 一些 single added-family key，例如 `pullback_drawdown`，wait 依赖较低，`pct_wait_gt_10pct` 只有 `3.0%`，但 fresh-edge 仍为 `-30.6%`。

因此 family-set pooling 的问题不是只有 late confirmation；即便在低 wait-return key 上，fresh-anchor path 的坏路径比例仍偏高。后续如果继续，family-set 不能只按 denominator 或 seed-anchor 表现筛选，必须同时约束 fresh-anchor drawdown/path。

## 10. Seed-anchor 与 fresh-anchor 的差异

典型差异行：

| kth | offset | wait_bucket | fresh_step_count | seed_bw_rate | fresh_bw_rate | seed_P_good | seed_P_bad | fresh_P_good | fresh_P_bad | interpretation |
|:--|:--|:--|--:|--:|--:|--:|--:|--:|--:|:--|
| 1 | t3_t5 | up_0_5pct | 2,761 | 11.9% | 10.4% | 51.1% | 44.9% | 35.6% | 61.1% | seed_anchor_only_stronger |
| 1 | t3_t5 | up_5_10pct | 799 | 20.6% | 15.3% | 81.4% | 18.1% | 34.2% | 63.9% | seed_anchor_only_stronger |
| 1 | t3_t5 | up_10_20pct | 225 | 28.4% | 19.5% | 91.9% | 8.1% | 27.7% | 71.7% | price_cost_high_confirmation_only |
| 1 | t3_t5 | up_gt_20pct | 53 | 26.1% | 4.4% | 97.8% | 2.2% | 4.3% | 95.7% | price_cost_high_confirmation_only |
| 2 | t11_t20 | up_10_20pct | 182 | 25.4% | 13.6% | 100.0% | 0.0% | 43.1% | 56.9% | price_cost_high_confirmation_only |
| 2 | t21_t30 | up_10_20pct | 66 | 10.7% | 5.6% | 100.0% | 0.0% | 27.3% | 69.1% | price_cost_high_confirmation_only |

最重要的发现：

- seed-anchor strong 不等于 fresh-anchor still attractive。
- `up_10_20pct` 和 `up_gt_20pct` 经常是 seed-anchor 近乎完美的 path label，但 fresh-anchor 反而 bad-path 占优。
- 这说明 R03b 的 fresh-count / sequence 发现更像“趋势确认诊断”，不是“等待后买入诊断”。

## 11. Survival price bias

许多 no-fresh episode 并不是“没有后续支持”，而是先发生 observable failure，已经失去进入 fresh-step panel 的机会。

| split | seed_episode_count | failed_before_t3 | failed_t3_to_t5 | failed_t6_to_t10 | failed_t11_to_t20 | failed_t21_to_t30 | failed_before_first_clean_fresh_count | no_clean_fresh_episode_count | first_clean_fresh_episode_count | first_fresh_wait_p50 | first_fresh_gt_10pct |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 5,139 | 846 | 678 | 747 | 701 | 372 | 2,227 | 2,288 | 2,851 | 2.8% | 7.4% |
| validation | 2,891 | 364 | 426 | 424 | 434 | 206 | 1,194 | 1,216 | 1,675 | 2.4% | 3.4% |
| robustness | 2,973 | 323 | 297 | 306 | 375 | 204 | 1,079 | 1,156 | 1,817 | 2.6% | 7.3% |
| all | 11,003 | 1,533 | 1,401 | 1,477 | 1,510 | 782 | 4,500 | 4,660 | 6,343 | 2.6% | 6.3% |

解释：

- all split 有 `4,500 / 11,003 = 40.9%` 的 episode 在 first clean fresh 前已经 failure。
- no-clean-fresh episode 为 `4,660`，数量接近 failed-before-first-clean-fresh。
- 因此，不能把 no-fresh 简化解释为“缺少后续信号支持”；其中大量样本是先失败，后续 sequence 还没有机会形成。
- fresh-step 级别 seed-anchor 表格只在 `first_clean_fresh_episode = 6,343` 这个生存子集上计算。这个子集的 seed-anchor big-winner rate 不能直接和 R03b 全 seed base rate 比较；fresh-count lift 中有一部分来自“活到 first clean fresh”的条件选择。

## 12. 研究判断

1. “等到更多 fresh signal 再进入”的假设应否决。fresh-anchor big-winner rate 在 kth=1..4plus 上稳定在约 `9.4%`-`10.5%`，没有随 kth 改善；等待成本却持续上升。
2. fresh-count 可保留为弱 episode-state 描述，但不能进入 entry/add rule。它主要描述 seed episode 是否已经跑出来，而不是 fresh-entry 之后是否仍有 edge。
3. `kth_fresh_step_bucket + offset_bucket` 在 checkpoint-aligned seed-anchor 口径下净劣化：bucket 更多、sufficient 更少、信息无增益。
4. family-set pooling 当前样本规模下应放弃。stable_descriptive 为 `0`，validation sufficient bucket 比例低于 `3.1%`，wait-bucket 后低于 `0.6%`。
5. fresh-anchor path 没有明显优于 R02 baseline single-family path。它不是特别差，而是没有提供超过 baseline 的额外 forward-from-entry 信息。
6. R03c 的方法论价值应保留：anchor 分离和 survival audit 必须进入后续所有 sequence / fresh-count 诊断。

## 13. 下一阶段建议

不建议进入围绕 R03c outputs 的 formal validation protocol；R03c 已经把它自己的主问题证伪。下一步应收束而不是扩展：

- 重做 R03b headline，把 seed-anchor `P_good / P_bad` 拆成 survival-adjusted / wait-return-adjusted 口径，确认 fresh-count 的剩余信息量是否接近 0。
- 把 `no_fresh`、`failed_before_fresh`、`has_fresh` 三段并列为 baseline 报告口径，禁止只看 has-fresh 子集。
- 放弃完整 family-set pattern，除非后续明确粗化为 outcome-blind 的 family-count / presence-count 类变量。
- 把 entry 研究预算转回 `single-family + entry timing`，例如 next-open / cooling / ATR-rank gating。
- fresh signal accumulation 只作为已持仓 episode 的 hold-state、risk-state 或 exit-monitor 变量继续观察。

## 14. Anchor Mapping 说明

fresh_anchor_big_winner headline 使用 precision panel 的 close-anchor `fresh_big_winner_forward_h120_close_anchor`。
fresh path headline 使用 path-query CSV 的 entry-anchored `fresh_path_label` 与 fresh path metrics。
`fresh_big_winner_forward_h120_close_anchor` 与 `fresh_close_return_t20` 属于不同 price anchor，不得混成同一个可执行收益口径。

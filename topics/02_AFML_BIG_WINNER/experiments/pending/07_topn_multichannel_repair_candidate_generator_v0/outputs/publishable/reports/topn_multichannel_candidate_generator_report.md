# Top-N 多通道修复事件候选生成器报告（07）

最终决策：`topn_multichannel_candidate_generator_density_blocked`

本报告解释 07 全量运行的当前产物。07 在 06 冻结的 PIT Top-N/proxy denominator 上生成多通道修复 / 持续候选事件池，并事后 link 到 06 big-winner episodes。它不是交易信号、不是模型、不是组合回测。

## 1. 核心结论

07 的多通道 union 在 episode-anchored recall 上明显通过预声明目标，但没有通过 density gate。阻塞原因不是总 canonical density mean / p95 超限，而是两个通道在 recommended union 中占用大量 canonical density，却几乎没有带来 incremental recall：

| gate / readout | value | threshold | status |
| :-- | --: | --: | :-- |
| input gate | pass | pass | pass |
| all before-first-50pct any-event recall | 72.0% | >= 55.0% | pass |
| validation before-first-50pct any-event recall | 79.3% | >= 45.0% | pass |
| robustness before-first-50pct any-event recall | 68.9% | >= 45.0% | pass |
| positive unique recall non-E0 channels | 3 | >= 2 | pass |
| canonical density mean | 3.94 / instrument-year | <= 6.00 | pass |
| canonical density p95 | 7.00 / instrument-year | <= 12.00 | pass |
| max channel canonical share | 45.0% | <= 75.0% | pass |
| density drag channel count | 2 | 0 | fail |
| next-open executable rate | 99.9% | >= 95.0% | pass |
| event 120d label completeness | 99.9% | >= 70.0% | pass |
| capture label completeness | 100.0% | >= 90.0% | pass |

直接发现：

1. **候选池覆盖能力强**：before-first-50pct any-event recall 全样本 72.0%，train / validation / robustness 分别为 71.4% / 79.3% / 68.9%。这说明“多通道候选生成器”能早于 +50% touch 覆盖大量 big-winner episodes。
2. **+50 bridge 没有实质改善**：before-first-50pct bridge-positive recall 全样本 34.8%，旧 04 参考值是 35.2%。由于 denominator 不同，这不是严格劣化比较，但它说明 07 的高 any-event recall 并没有自动转化为更高的 event 自身 +50% outcome。
3. **E1 是主要覆盖来源**：E1 alone 捕获 1,773 / 2,493 个 target episodes，recall 71.1%。E2 的 captured episodes 高达 1,765，但全部被 E1 覆盖，没有 incremental recall。E6 捕获 1,402，但 incremental recall 只有 10 个 episode。
4. **E2 / E6 是 density drag**：E2 占 recommended canonical events 的 44.1%，incremental recall 为 0；E6 占 32.5%，incremental recall 为 0.4%。这触发 density-blocked。
5. **precision 不授权**：event-anchored +120d big-winner rate 在 validation 只有 7.2%，forward_20 / forward_60 均为负；clean baseline match coverage 不可用。因此不能写 precision edge supported。
6. **数据完整性较好**：07 event generation 已严格对齐 06 evaluated instrument-days：912,851 / 912,851，cutoff 为 2025-11-26；canonical events 最大日期也是 2025-11-26。forward-120 bridge censoring 很小，before-first-50pct 只排除 4 个 episodes。

## 2. 输入与 Denominator

05 的 `topn_universe_candidate_panel_blocked` 被 06 接受为 available-source Top-N/proxy caveat。本实验继承该 caveat：结果只代表当前可审计数据源上的 PIT Top-N 400/100 proxy，不代表 exact historical top 400/100。

| input item | value |
| :-- | :-- |
| upstream 05 decision | `topn_universe_candidate_panel_blocked` |
| upstream 06 decision | `topn_reverse_lifecycle_sequence_supported_universal_dominance` |
| topn_candidate_gap_accepted | `True` |
| universe_precision_status | `available_source_topn_candidate_gap` |
| source_gap_count / active_source_gap_count | 318 / 229 |
| 06 latest label complete low date | 2025-11-26 |
| old 04 density baseline source | `04_manifest_gate_summary` |

06 frozen denominator:

| scope | raw_topn_instrument_days | evaluated_instrument_days | universe_years_252 | target episodes | episodes / 100 universe-years |
| :-- | --: | --: | --: | --: | --: |
| all | 1,140,000 | 912,851 | 3,622.42 | 2,493 | 68.82 |

Split denominator:

| split | raw_topn_instrument_days | evaluated_instrument_days | universe_years_252 | target episodes |
| :-- | --: | --: | --: | --: |
| train | 608,000 | 452,114 | 1,794.10 | 1,290 |
| validation | 242,000 | 232,965 | 924.46 | 445 |
| robustness | 230,000 | 227,772 | 903.86 | 758 |
| outside_split | 60,000 | 0 | 0.00 | 0 |

07 event-generation universe audit:

| split | raw days | evaluated days | event-generation days | excluded days | main exclusions |
| :-- | --: | --: | --: | --: | :-- |
| train | 608,000 | 452,114 | 452,114 | 155,886 | history_not_ready_250d; missing_stock_daily_csv |
| validation | 242,000 | 232,965 | 232,965 | 9,035 | history_not_ready_250d; missing_stock_daily_csv |
| robustness | 230,000 | 227,772 | 227,772 | 2,228 | history_not_ready_250d; missing_stock_daily_csv |
| outside_split | 60,000 | 0 | 0 | 60,000 | label_incomplete_120d; outside_split |
| all | 1,140,000 | 912,851 | 912,851 | 227,149 | history_not_ready_250d; label_incomplete_120d; outside_split; missing_stock_daily_csv |

关键审计结论：`event_generation_instrument_days = 912,851`，与 06 evaluated denominator 完全一致。07 不再生成 2025-11-26 之后的 event；canonical event date 范围为 2018-01-18 到 2025-11-26。

## 3. Event Pool

07 全量运行生成：

| 产物口径 | count |
| :-- | --: |
| raw event instances, including E0 setup context | 83,698 |
| recommended canonical events | 15,161 |
| target episodes evaluated | 2,493 |

Event instances 按通道分布：

| channel | event instances | train | validation | robustness |
| :-- | --: | --: | --: | --: |
| E0_setup_context | 53,939 | 23,217 | 18,271 | 12,451 |
| E1_early_ema60_repair | 10,323 | 4,892 | 2,874 | 2,557 |
| E2_money_vwap_repair_confirmation | 6,686 | 3,286 | 1,765 | 1,635 |
| E3_rank_persistence | 5,276 | 2,425 | 1,590 | 1,261 |
| E6_continuation_discriminator | 7,474 | 3,476 | 2,181 | 1,817 |

E0 只作为 setup context，不进入 headline canonical density、event precision 或 channel contribution。Recommended canonical events 按 primary channel 分布如下：

| primary channel | canonical events | train | validation | robustness |
| :-- | --: | --: | --: | --: |
| E1_early_ema60_repair | 6,820 | 3,335 | 1,800 | 1,685 |
| E2_money_vwap_repair_confirmation | 11 | 6 | 4 | 1 |
| E3_rank_persistence | 3,437 | 1,626 | 983 | 828 |
| E6_continuation_discriminator | 4,893 | 2,361 | 1,359 | 1,173 |

注意：primary channel 只是同日多通道 canonical event 的展示归因。Density drag 使用 triggered channel 的 canonical membership share，因此 E2 虽然 primary 只有 11 行，但它作为 triggered channel 出现在 6,686 个 canonical events 中。

## 4. Episode-Anchored Recall

### 4.1 Any-event recall

Any-event capture 不要求 event 自身未来达到 +50%，只要求 episode 在指定窗口内至少有一个 recommended canonical event。

| window | all | train | validation | robustness |
| :-- | --: | --: | --: | --: |
| low_plus_20 | 42.0% | 39.4% | 48.8% | 42.5% |
| low_plus_30 | 54.8% | 53.6% | 69.9% | 48.0% |
| low_plus_60 | 67.8% | 66.1% | 80.7% | 63.2% |
| low_plus_120 | 76.7% | 75.8% | 85.2% | 73.2% |
| before_first_50pct | 72.0% | 71.4% | 79.3% | 68.9% |
| before_episode_high | 73.7% | 72.6% | 82.5% | 70.6% |

Headline before-first-50pct any-event detail:

| split | numerator | denominator | excluded | recall |
| :-- | --: | --: | --: | --: |
| all | 1,796 | 2,493 | 0 | 72.0% |
| train | 921 | 1,290 | 0 | 71.4% |
| validation | 353 | 445 | 0 | 79.3% |
| robustness | 522 | 758 | 0 | 68.9% |

发现：recall gate 本身是强通过的。validation 反而最高，robustness 仍远高于 45% hard gate。这说明候选事件的早期覆盖不是 train-only artifact。

### 4.2 Bridge-positive recall

Bridge-positive 要求 before-first-50pct window 内至少有一个 canonical event，并且该 event 从 executable basis 往后 120 个交易日 MFE 达到 +50%。

| window | all | train | validation | robustness |
| :-- | --: | --: | --: | --: |
| low_plus_20 | 15.5% | 16.8% | 14.6% | 13.7% |
| low_plus_30 | 21.0% | 23.6% | 19.6% | 17.5% |
| low_plus_60 | 30.1% | 32.2% | 26.1% | 28.9% |
| low_plus_120 | 37.1% | 39.1% | 29.9% | 37.9% |
| before_first_50pct | 34.8% | 37.3% | 27.0% | 34.9% |
| before_episode_high | 35.6% | 37.9% | 28.8% | 35.6% |

Headline before-first-50pct bridge-positive detail:

| split | numerator | denominator | excluded | recall |
| :-- | --: | --: | --: | --: |
| all | 865 | 2,489 | 4 | 34.8% |
| train | 481 | 1,288 | 2 | 37.3% |
| validation | 120 | 444 | 1 | 27.0% |
| robustness | 264 | 757 | 1 | 34.9% |

发现：any-event recall 高，但 event 自身成为 +50 winner 的 bridge conversion 不高。Validation bridge-positive 只有 27.0%，是 precision / ranking 后续必须处理的核心问题。

### 4.3 Split / Regime / Board

Before-first-50pct any-event recall by regime:

| split | regime | numerator | denominator | recall |
| :-- | :-- | --: | --: | --: |
| train | risk_off | 584 | 761 | 76.7% |
| train | risk_on | 145 | 225 | 64.4% |
| train | transition | 192 | 304 | 63.2% |
| validation | risk_off | 287 | 342 | 83.9% |
| validation | risk_on | 9 | 22 | 40.9% |
| validation | transition | 57 | 81 | 70.4% |
| robustness | risk_off | 392 | 477 | 82.2% |
| robustness | risk_on | 90 | 181 | 49.7% |
| robustness | transition | 40 | 100 | 40.0% |

Before-first-50pct any-event recall by board:

| split | board | numerator | denominator | recall |
| :-- | :-- | --: | --: | --: |
| train | chinext | 232 | 325 | 71.4% |
| train | main_board | 689 | 965 | 71.4% |
| validation | chinext | 88 | 110 | 80.0% |
| validation | main_board | 265 | 335 | 79.1% |
| robustness | chinext | 161 | 244 | 66.0% |
| robustness | main_board | 361 | 514 | 70.2% |

发现：board 分布比较平衡；主要薄弱点是 risk_on / transition 在 validation 或 robustness 下的 recall，尤其 validation risk_on 样本小但只有 40.9%，robustness transition 40.0%。这些不触发 hard gate，但说明后续不能只看 all-split。

## 5. Channel Contribution 与 Overlap

Before-first-50pct channel contribution:

| channel | captured episodes | recall | unique captures | unique recall | incremental captures | incremental recall |
| :-- | --: | --: | --: | --: | --: | --: |
| E1_early_ema60_repair | 1,773 | 71.1% | 1 | 0.04% | 1,773 | 71.1% |
| E2_money_vwap_repair_confirmation | 1,765 | 70.8% | 0 | 0.00% | 0 | 0.0% |
| E3_rank_persistence | 868 | 34.8% | 5 | 0.20% | 13 | 0.5% |
| E6_continuation_discriminator | 1,402 | 56.2% | 10 | 0.40% | 10 | 0.4% |

通道 overlap 解释了为什么 density blocked：

| relationship | overlap |
| :-- | --: |
| E2 captured episodes also captured by E1 | 1,765 / 1,765 = 100.0% |
| E3 captured episodes also captured by E1 | 855 / 868 = 98.5% |
| E6 captured episodes also captured by E1 | 1,384 / 1,402 = 98.7% |
| E6 captured episodes also captured by E2 | 1,377 / 1,402 = 98.2% |
| E1 captured episodes also captured by E6 | 1,384 / 1,773 = 78.1% |

发现：E1 是候选池骨架。E2 更像附着在 E1 已捕获事件上的密集确认标签，并没有增加 episode 覆盖。E6 作为 continuation metadata 有信息量，但作为 headline union 成员几乎不增加新 recall。

## 6. Density 与阻塞原因

Density gate 使用 07 config 中预声明的硬上限。旧 04 density baseline 只作为对照，不作为 07 pass/fail gate。

| scope / channel | canonical events | events / 100 universe-years | mean / instrument-year | p95 / instrument-year | canonical share | incremental recall | density drag |
| :-- | --: | --: | --: | --: | --: | --: | :-- |
| recommended union | 15,161 | 418.5 | 3.94 | 7.00 | 100.0% | NA | no |
| E1 | 6,820 | 188.3 | 1.83 | 3.00 | 45.0% | 71.1% | no |
| E2 | 6,686 | 184.6 | 1.80 | 3.00 | 44.1% | 0.0% | yes |
| E3 | 3,439 | 94.9 | 1.31 | 2.00 | 22.7% | 0.5% | no |
| E6 | 4,920 | 135.8 | 1.51 | 3.00 | 32.5% | 0.4% | yes |

旧 04 density 对照：

| metric | 07 recommended union | old 04 setup-inclusive | old 04 reclaim-based | 07 hard limit |
| :-- | --: | --: | --: | --: |
| events per instrument-year mean | 3.94 | 3.33 | 1.72 | 6.00 |
| events per instrument-year p95 | 7.00 | 3.33 | 1.72 | 12.00 |

发现：07 的 total union density 没有超过 mean / p95 hard limit，但 E2 和 E6 触发 density drag rule。按照 requirement，低 incremental recall 且 canonical share >= 25% 的通道不能静默留在 recommended union。当前 union 因此不能作为下一阶段的正式 candidate pool。

## 7. Event-Anchored Label / Precision Readout

这些指标以 canonical event 为 denominator，不是 episode recall。

按 split 汇总：

| event_split | events | complete 120d | +50 event rate | near-winner rate | confirm20 | failure10 | forward20 mean | forward60 mean |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| train | 7,328 | 99.9% | 16.8% | 17.6% | 27.8% | 18.4% | 0.5% | 0.3% |
| validation | 4,146 | 100.0% | 7.2% | 11.5% | 21.1% | 16.1% | -1.1% | -2.3% |
| robustness | 3,687 | 99.9% | 18.2% | 17.1% | 31.2% | 12.6% | 2.5% | 7.3% |

按 primary channel 汇总：

| primary channel | events | complete 120d | +50 event rate | near-winner rate | confirm20 | failure10 | forward20 mean | forward60 mean |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| E1 | 6,820 | 99.9% | 14.6% | 16.1% | 28.8% | 14.5% | 1.1% | 1.7% |
| E6 | 4,893 | 99.9% | 14.4% | 15.4% | 26.0% | 17.7% | 0.2% | 0.5% |
| E3 | 3,437 | 99.9% | 14.5% | 15.8% | 24.1% | 18.0% | 0.0% | 1.5% |
| E2 | 11 | 100.0% | 9.1% | 27.3% | 9.1% | 18.2% | -0.4% | 3.4% |

发现：validation 是 precision 最弱 split，+50 event rate 只有 7.2%，forward20 / forward60 mean 均为负。即使 recall gate 通过，也不能把本实验解释为 entry edge。当前更合理的定位是“高召回候选池诊断”，不是“可交易信号”。

## 8. False Repair 与 Execution Completeness

False-repair 按 primary channel 汇总：

| primary channel | events | false10 | false10 rate | false20 | false20 rate |
| :-- | --: | --: | --: | --: | --: |
| E1 | 6,820 | 623 | 9.1% | 1,406 | 20.6% |
| E6 | 4,893 | 593 | 12.1% | 1,223 | 25.0% |
| E3 | 3,437 | 448 | 13.0% | 877 | 25.5% |
| E2 | 11 | 1 | 9.1% | 1 | 9.1% |

False-repair 按 split 汇总：

| split | events | false10 rate | false20 rate |
| :-- | --: | --: | --: |
| train | 7,328 | 12.6% | 25.2% |
| validation | 4,146 | 10.3% | 23.5% |
| robustness | 3,687 | 8.5% | 18.5% |

Execution / label completeness:

| scope | events | next-open executable | event 120d label complete | capture label complete |
| :-- | --: | --: | --: | --: |
| train | 7,328 | 99.9% | 99.9% | 100.0% |
| validation | 4,146 | 100.0% | 100.0% | 99.9% |
| robustness | 3,687 | 99.9% | 99.9% | 100.0% |
| all | 15,161 | 99.9% | 99.9% | 100.0% |

发现：execution / label completeness 不是阻塞项。false-repair 仍然是后续模型必须处理的问题，尤其 E3 / E6 的 20 日 false-repair rate 约 25%。

## 9. Lead Time 与 Bridge Censoring

Before-first-50pct captured episodes 的 lead time to first_50pct：

| split | captured episodes | mean sessions | median | p25 | p75 |
| :-- | --: | --: | --: | --: | --: |
| train | 921 | 50.3 | 47.0 | 26.0 | 74.0 |
| validation | 353 | 45.9 | 43.0 | 17.0 | 69.0 |
| robustness | 522 | 36.8 | 33.5 | 6.0 | 56.0 |

Before-episode-high captured episodes 的 lead time to first_50pct proxy:

| split | captured episodes | mean sessions | median | late continuation share |
| :-- | --: | --: | --: | --: |
| train | 936 | 49.0 | 47.0 | 1.4% |
| validation | 367 | 43.8 | 42.0 | 1.6% |
| robustness | 535 | 35.4 | 32.0 | 1.5% |

Bridge-positive censoring is small:

| window | bridge denominator | excluded episodes | label-complete event hits | label-incomplete event hits |
| :-- | --: | --: | --: | --: |
| before_first_50pct | 2,489 | 4 | 4,422 | 7 |
| low_to_first_50pct | 2,489 | 4 | 4,507 | 7 |
| low_plus_120 | 2,493 | 0 | 5,646 | 11 |
| before_episode_high | 2,493 | 0 | 4,948 | 10 |

发现：bridge recall 不是因为 missing labels 被系统性压低。before-first-50pct 只排除 4 个 episodes，主要问题是 candidate event 自身 forward-120 MFE 未必能达到 +50%。

## 10. 补充研究统计

本节把 07 gate 之外、后续研究需要的统计补齐。除特别说明外，episode 统计来自 06 冻结的 `topn_big_winner_episode_reference.parquet` 与 07 的 `topn_episode_capture_audit.csv`；event path 统计来自 07 的 canonical event label cache。90d path 是按 03/04/07 相同 next-open anchor 逻辑做的报告层补充诊断，不改变 07 gate 或 manifest decision。

### 10.1 06 Winner Episode Path Profile

06 denominator 中，target episode 本身并不是同质样本。Validation 的 episode MFE 和持续时间都偏短，robustness 的 low-to-first50 更短，这会影响 event 是否有足够时间在 +50% 之前触发。

| split | episodes | MFE120 median | MFE120 p75 | low-to-first50 median sessions | low-to-first50 p25 / p75 | low-to-high median sessions | low-to-high p25 / p75 |
| :-- | --: | --: | --: | --: | :-- | --: | :-- |
| train | 1,290 | 69.9% | 92.2% | 74 | 44 / 95 | 97 | 71 / 112 |
| validation | 445 | 64.0% | 77.6% | 62 | 33 / 87 | 83 | 52 / 110 |
| robustness | 758 | 69.7% | 96.0% | 60 | 27 / 94 | 95 | 54 / 114 |
| all | 2,493 | 68.3% | 90.8% | 69 | 37 / 94 | 94 | 61 / 112 |

06 episode regime / board composition:

| bucket | episodes | share |
| :-- | --: | --: |
| risk_off | 1,580 | 63.4% |
| transition | 485 | 19.5% |
| risk_on | 428 | 17.2% |
| main_board | 1,814 | 72.8% |
| chinext | 679 | 27.2% |

发现：07 的 recall split 看起来稳定，但 denominator 本身在 validation 更短、更弱，且 risk_off 占 63.4%。后续如果只看 all-split，会低估 risk_on / transition 的覆盖问题。

### 10.2 Event Merge 与集中度

07 不是把所有 raw channel event 原样作为 headline event，而是先生成 recommended raw event instances，再按同一股票同一天合并成 canonical event。

| metric | value |
| :-- | --: |
| recommended raw event instances | 29,759 |
| recommended canonical events | 15,161 |
| raw instances per canonical mean | 1.96 |
| raw cluster event count median / p75 / max | 2 / 2 / 6 |
| triggered channel count median / p75 / max | 1 / 2 / 2 |

Same-day canonical union 的 triggered channel count：

| triggered channel count | canonical events | share |
| --: | --: | --: |
| 1 | 8,457 | 55.8% |
| 2 | 6,704 | 44.2% |

Symbol concentration:

| metric | value |
| :-- | --: |
| symbols with canonical event | 1,092 |
| top 10 symbols event share | 2.9% |
| top 50 symbols event share | 12.9% |
| max events in one symbol | 46 |

发现：event pool 没有被少数股票主导；问题主要不是 symbol concentration，而是同日多通道 tag 的密度与信息增量不匹配。44.2% canonical events 带有两个 triggered channels，因此不能只用 primary channel 分布解释密度。

### 10.3 Captured Episode 内 Event 数量

`before_first_50pct` 口径下，any-event captured episode 通常不是只被一个 event 命中；中位数是 3 个 canonical events。

| group | episodes | event count mean | median | p25 / p75 | min / max |
| :-- | --: | --: | --: | :-- | :-- |
| all denominator | 2,493 | 1.78 | 2 | 0 / 3 | 0 / 6 |
| any-event captured | 1,796 | 2.47 | 3 | 2 / 3 | 1 / 6 |
| bridge-positive captured | 865 | 2.65 | 3 | 2 / 3 | 1 / 6 |
| any captured but bridge-negative | 931 | 2.30 | 2 | 1 / 3 | 1 / 6 |
| missed by any-event | 697 | 0.00 | 0 | 0 / 0 | 0 / 0 |

发现：bridge-positive episode 的 event count 略高于 any-only episode，但差异不大。提高 bridge recall 不太可能只靠继续增加同类 event 数量解决，更需要更早或质量更高的 event。

### 10.4 Event-to-Episode Alignment

下表把 `before_first_50pct` denominator 分成四组：any-event captured、bridge-positive captured、any captured 但 bridge-negative、missed by any-event。

| group | episodes | low-to-first50 median | low-to-high median | first event lag from low median | first event open vs low median | first event lead to first50 median | MFE120 median |
| :-- | --: | --: | --: | :-- | :-- | :-- | :-- |
| any-event captured | 1,796 | 74 | 97 | 18 | 18.2% | 43 | 66.6% |
| bridge-positive captured | 865 | 83 | 108 | 21 | 14.9% | 46 | 85.2% |
| any captured / bridge-negative | 931 | 61 | 78 | 15 | 20.8% | 38 | 59.2% |
| missed by any-event | 697 | 53 | 85 | NA | NA | NA | 74.3% |

Bridge-positive first event 的位置：

| metric | value |
| :-- | :-- |
| first bridge-positive lag from low median / p75 | 24 / 47 sessions |
| first bridge-positive open vs episode low median / p75 | 14.4% / 20.8% |
| first bridge-positive lead to first50 median / p75 | 43 / 67 sessions |

发现：bridge-positive 不是越早越好这么简单。bridge-positive group 的 first event 比 any-only group 略晚，但触发价格相对 episode low 更低，且 episode 本身更强、更长。Any-only group 的 event 触发时已经从 low 上涨 20.8% 中位数，后续要从 event price 再涨 +50% 难度显著更高。

### 10.5 Event 后 Path：全体 Canonical Events

下表是全体 15,161 条 recommended canonical events 的 event-anchored path。Anchor 是 next-open executable price，不是 episode low。

| horizon | complete events | forward median | forward p25 / p75 | positive rate | MFE median | MFE >= 20% | MFE >= 50% | MAE median | MAE <= -10% |
| :-- | --: | --: | :-- | --: | --: | --: | --: | --: | --: |
| 10d | 15,150 | -0.4% | -4.8% / 4.3% | 47.2% | 4.7% | 7.0% | 0.5% | -4.5% | 16.3% |
| 20d | 15,150 | -0.7% | -6.5% / 6.0% | 46.5% | 6.7% | 14.0% | 1.3% | -6.3% | 29.3% |
| 30d | 15,150 | -1.2% | -8.1% / 7.2% | 45.1% | 8.3% | 19.5% | 2.5% | -7.8% | 39.0% |
| 60d | 15,150 | -1.7% | -11.1% / 9.8% | 45.5% | 12.2% | 31.9% | 6.8% | -11.0% | 53.9% |
| 90d | 15,150 | -1.9% | -13.3% / 12.2% | 45.6% | 15.4% | 40.5% | 11.1% | -13.2% | 61.2% |
| 120d | 15,147 | -2.4% | -15.1% / 13.1% | 44.9% | 18.3% | 46.5% | 14.5% | -15.2% | 66.3% |

发现：全体 union 的 median forward return 从 10d 到 120d 都是负的，且 MAE 逐步恶化。这个结果支持“07 是候选池，不是 entry signal”的结论；如果直接把 full union 当交易入口，噪音会很大。

### 10.6 Event 后 Path：命中 Big-Winner Episode 的首个 Event

只看 `before_first_50pct` any-event captured episodes 的首个 event，path 明显更强。这说明 07 event 在 winner episode 内有信息，但 full union 缺少足够的筛选 / ranking。

| horizon | complete events | forward median | forward p25 / p75 | positive rate | MFE median | MFE >= 20% | MFE >= 50% | MAE median | MAE <= -10% |
| :-- | --: | --: | :-- | --: | --: | --: | --: | --: | --: |
| 10d | 1,792 | 3.2% | -1.9% / 9.5% | 66.2% | 8.6% | 17.6% | 1.7% | -3.4% | 10.7% |
| 20d | 1,792 | 6.1% | -1.3% / 14.8% | 69.8% | 13.9% | 33.3% | 3.3% | -4.3% | 17.8% |
| 30d | 1,792 | 7.0% | -2.1% / 17.6% | 70.1% | 18.0% | 44.8% | 6.7% | -5.1% | 24.0% |
| 60d | 1,792 | 14.2% | 1.5% / 27.2% | 77.4% | 30.0% | 71.9% | 19.5% | -6.4% | 33.0% |
| 90d | 1,792 | 20.5% | 4.5% / 36.5% | 80.5% | 39.8% | 89.6% | 33.5% | -7.5% | 38.9% |
| 120d | 1,792 | 18.5% | 1.1% / 38.0% | 76.8% | 46.1% | 94.4% | 43.8% | -8.1% | 42.4% |

发现：命中 winner episode 的首个 event 在 90d 的 forward median 是 20.5%，MFE median 是 39.8%；但全体 event 的 90d forward median 是 -1.9%。下一轮研究的核心不是“07 event 完全无效”，而是要把 winner-like event 从全体 union 里分离出来。

### 10.7 Path by Split 与 Channel

按 split 看，validation 是最弱 path，且越长 horizon 越弱。

| split | horizon | complete events | forward median | positive rate | MFE >= 20% | MFE >= 50% | MAE <= -10% |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| train | 60d | 7,320 | -2.9% | 42.4% | 33.2% | 7.4% | 58.9% |
| train | 90d | 7,320 | -2.5% | 44.6% | 43.1% | 12.4% | 65.5% |
| train | 120d | 7,320 | -2.7% | 44.5% | 49.8% | 16.8% | 70.4% |
| validation | 60d | 4,145 | -3.2% | 39.7% | 22.2% | 2.8% | 57.8% |
| validation | 90d | 4,145 | -5.7% | 35.9% | 28.9% | 5.3% | 67.5% |
| validation | 120d | 4,145 | -7.5% | 34.5% | 34.2% | 7.2% | 73.2% |
| robustness | 60d | 3,685 | 3.1% | 58.0% | 40.1% | 10.3% | 39.8% |
| robustness | 90d | 3,685 | 3.6% | 58.7% | 48.1% | 15.3% | 45.7% |
| robustness | 120d | 3,682 | 3.6% | 57.4% | 53.7% | 18.2% | 50.3% |

按 primary channel 看，各通道在 90d / 120d 的 median forward return 都没有形成稳定正收益；E2 primary 样本只有 11 条，不能单独解释。

| primary channel | horizon | complete events | forward median | positive rate | MFE >= 20% | MFE >= 50% | MAE <= -10% |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| E1 | 90d | 6,812 | -1.3% | 46.7% | 41.0% | 11.1% | 58.8% |
| E1 | 120d | 6,811 | -2.0% | 45.7% | 46.9% | 14.6% | 63.9% |
| E3 | 90d | 3,436 | -2.4% | 44.9% | 40.0% | 11.3% | 63.6% |
| E3 | 120d | 3,435 | -2.7% | 44.5% | 46.5% | 14.5% | 68.4% |
| E6 | 90d | 4,891 | -2.4% | 44.7% | 40.1% | 11.2% | 63.0% |
| E6 | 120d | 4,890 | -3.0% | 44.2% | 45.9% | 14.4% | 68.0% |
| E2 | 90d | 11 | -5.1% | 45.5% | 45.5% | 9.1% | 72.7% |
| E2 | 120d | 11 | -1.0% | 36.4% | 45.5% | 9.1% | 72.7% |

Triggered channel combination 的 90d path:

| triggered combo | events | forward90 median | positive90 | MFE90 >= 20% | MFE90 >= 50% | MAE90 <= -10% |
| :-- | --: | --: | --: | --: | --: | --: |
| E1+E2 | 6,667 | -1.3% | 46.5% | 40.9% | 11.0% | 58.9% |
| E6 | 4,891 | -2.4% | 44.7% | 40.1% | 11.2% | 63.0% |
| E3 | 3,435 | -2.4% | 44.9% | 40.0% | 11.3% | 63.6% |
| E1 | 117 | 2.2% | 55.6% | 43.6% | 12.8% | 51.3% |

发现：E2 与 E1 高度同日重叠，`E1+E2` 的 90d path 并没有明显优于 E1-only small subset。E6 / E3 作为 primary 或 standalone combo 也没有改善 median path。当前更像是“E1 负责召回，其他通道负责描述状态”，而不是多个独立 alpha source 叠加。

### 10.8 Bridge Failure 与 Missed Episode

Bridge-positive event 与 bridge-negative event 的 path 差异很清楚：

| group | horizon | events | forward median | positive rate | MFE >= 20% | MFE >= 50% | MAE <= -10% |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| bridge-positive first positive event | 60d | 865 | 26.1% | 90.2% | 81.2% | 44.6% | 23.9% |
| bridge-positive first positive event | 90d | 865 | 37.0% | 96.0% | 95.8% | 75.5% | 25.1% |
| bridge-positive first positive event | 120d | 865 | 40.0% | 96.3% | 100.0% | 100.0% | 26.5% |
| any captured first event | 60d | 1,792 | 14.2% | 77.4% | 71.9% | 19.5% | 33.0% |
| any captured first event | 90d | 1,792 | 20.5% | 80.5% | 89.6% | 33.5% | 38.9% |
| any captured first event | 120d | 1,792 | 18.5% | 76.8% | 94.4% | 43.8% | 42.4% |
| any captured / bridge-negative first event | 60d | 927 | 7.6% | 68.9% | 67.1% | 0.0% | 38.1% |
| any captured / bridge-negative first event | 90d | 927 | 8.7% | 66.6% | 84.9% | 0.0% | 48.4% |
| any captured / bridge-negative first event | 120d | 927 | 4.5% | 58.8% | 89.3% | 0.0% | 54.2% |

Missed episodes 的 split / regime 分布：

| split | missed episodes | denominator episodes | miss rate |
| :-- | --: | --: | --: |
| train | 369 | 1,290 | 28.6% |
| validation | 92 | 445 | 20.7% |
| robustness | 236 | 758 | 31.1% |

| regime | missed episodes | denominator episodes | miss rate |
| :-- | --: | --: | --: |
| risk_off | 317 | 1,580 | 20.1% |
| risk_on | 184 | 428 | 43.0% |
| transition | 196 | 485 | 40.4% |

发现：missed episode 主要不是 label 完整性问题，而是 event family 对 risk_on / transition 的覆盖不足。Risk_on miss rate 43.0%，transition miss rate 40.4%，远高于 risk_off 的 20.1%。这说明下一轮不能只做 density thinning；还需要检查 risk_on / transition 下是否需要更早的 momentum / breakout 类 event，或者接受这些 regime 的 recall 较低。

### 10.9 Density Repair Frontier

下面是用当前 canonical events 的 triggered channel membership 做的静态 frontier。它不是 rerun，也没有改变 07 config；只是回答“如果 headline union 改成某些通道集合，recall / bridge / density 会怎样”。

| candidate union | canonical events | density vs full | any recall | bridge recall | bridge numerator / denominator |
| :-- | --: | --: | --: | --: | :-- |
| full E1+E2+E3+E6 | 15,161 | 100.0% | 72.0% | 34.8% | 865 / 2,489 |
| E1 only | 6,820 | 45.0% | 71.1% | 32.6% | 810 / 2,488 |
| E1+E3 | 10,257 | 67.7% | 71.6% | 33.7% | 840 / 2,489 |
| E1+E6 | 11,714 | 77.3% | 71.8% | 33.9% | 845 / 2,489 |
| E1+E3+E6 | 15,150 | 99.9% | 72.0% | 34.8% | 865 / 2,489 |
| remove E6 | 10,268 | 67.7% | 71.6% | 33.7% | 840 / 2,489 |

解释：E2 的 density drag 是 triggered membership drag，不是大量 E2-only canonical rows。把 E2 从 headline channel tag 降级为 E1 的 feature，并不会显著减少 canonical rows，因为 E2 几乎都与 E1 同日出现。真正能降低 row-level density 的是 E1-only 或 E1+E3 / remove E6 路线。E1-only 保留 71.1% any recall，只损失 0.9 pct recall，却把 canonical events 降到 full union 的 45.0%；这是 08 最强的起点。

### 10.10 对后续研究的直接含义

1. **07 已经足够证明 E1 backbone 有召回价值**：E1-only recall 71.1%，接近 full union 72.0%，且 density 只有 full union 的 45.0%。
2. **full union 不能直接进入 entry contract**：全体 event 的 120d forward median 为 -2.4%，MAE <= -10% rate 为 66.3%，说明不加筛选的 entry 风险太高。
3. **winner-linked event path 很强**：命中 winner episode 的 first event 在 90d 的 forward median 为 20.5%，MFE median 为 39.8%，说明后续应做 ranking / meta-label，而不是放弃 event 方向。
4. **bridge failure 主要是 event quality / basis 问题**：any-only first event 到 120d 的 MFE >= 20% rate 高达 89.3%，但 MFE >= 50% 为 0，因为这些 event 的 entry basis 已经偏高，或者 episode 自身不够强。
5. **risk_on / transition 是 recall repair 重点**：risk_on miss rate 43.0%，transition miss rate 40.4%；如果 08 只做 density thinning，可能继续保留这一结构性漏召回。
6. **E2 / E6 更适合作为 feature，不适合作为 headline union 通道**：E2 是 E1 同日 confirmation tag，E6 是 continuation readout；二者在 current union 中没有提供足够独立 recall。

## 11. Decision Replay

Decision priority 回放：

1. Input gate passed.
2. Recall gate passed.
3. Density mean / p95 passed.
4. Execution / label gate passed.
5. Density drag gate failed because E2 and E6 are high-share, low-incremental-recall channels.

因此最终 decision 是：

```text
topn_multichannel_candidate_generator_density_blocked
```

这不是“多通道方向失败”。更准确的解释是：当前 recommended union 太宽，E2 / E6 作为 headline union 成员的密度成本过高，必须先做 density repair / channel thinning，才能进入下一阶段 entry contract 或 meta-label 实验。

## 12. 发现与下一步

### 发现 1：E1 可作为候选池骨架

E1 alone 已覆盖 71.1% before-first-50pct target episodes，接近 full union 的 72.0%。它的 density share 45.0%，但 incremental recall 也是 71.1%，不是 drag。下一轮应把 E1 作为 backbone，而不是继续扩张 union。

### 发现 2：E2 不应作为 headline union 通道

E2 捕获 1,765 个 episodes，但这些 episodes 100.0% 都被 E1 捕获；incremental recall 为 0。E2 更适合作为 E1 event 的 feature / confirmation tag，而不是单独进入 headline recommended union。

### 发现 3：E6 应降级为 continuation readout 或二阶段标签

E6 捕获 1,402 个 episodes，但 incremental recall 只有 10 个 episodes，canonical share 32.5%。它可以保留为 continuation / confirmation signal，但不应在当前规则下作为 headline union 的独立通道。

### 发现 4：E3 有少量 unique value，但仍需密度控制

E3 的 canonical share 22.7%，没有触发 25% density drag；它贡献 13 个 incremental captures 和 5 个 unique captures。这个价值不大，但比 E2 更接近“可保留的辅助通道”。下一轮应检查 E3 是否能通过更严格 persistence 或 quality gate 提高 precision。

### 发现 5：高 recall 不等于高 precision

Validation event +50 rate 只有 7.2%，forward20 / forward60 mean 为 -1.1% / -2.3%。这说明当前 event pool 更像“候选召回网”，不是 entry edge。后续需要 ranking / meta-label / density-thinned candidate pool。

### 建议的下一轮实验

下一轮建议不要直接做交易回测。更合适的实验方向是：

1. 构建 `08_topn_density_repaired_candidate_union_v0`。
2. 固定 06 denominator 与 07 的 evaluated universe audit。
3. 以 E1 为 backbone。
4. 将 E2 从 headline union 移除，作为 E1 的 event feature / quality tag。
5. 将 E6 从 headline union 移除或只保留为 continuation readout。
6. 对 E3 做 train-only density / persistence gate repair。
7. 重新计算 recall、bridge-positive recall、density drag、validation precision readout。
8. 只有 density gate 通过后，才进入 meta-label 或 entry contract。

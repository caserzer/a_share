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

## 10. Decision Replay

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

## 11. 发现与下一步

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

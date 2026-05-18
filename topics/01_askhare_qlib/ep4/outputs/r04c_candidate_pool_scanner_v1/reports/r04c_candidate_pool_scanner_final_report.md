# R04c Candidate Pool Scanner V1 诊断报告

R04c is candidate-pool scanner, not hold/exit policy replay.
R04c uses hold120 no-exit baseline only.
Matched baseline_A is mandatory for pool promotion.
Validation and robustness cannot define pool membership.
Robustness is final readout only.
No production entry rule is emitted by this scanner.

## 1. 结论摘要

本次 R04c 的 final decision 是：

```text
r04c_no_candidate_pool_passed_validation
```

含义很直接：在当前已实现的 promotable pool 范围内，没有任何候选池在 validation split 同时满足 R04c 的 hard gates，因此没有冻结 `selected_candidate_pool_id`，也没有进入 robustness final readout。

这不是因为所有 pool 都完全没有信号。相反，R02 family pools 在 validation 上相对 matched baseline_A 明显改善左尾和均值，但它们的绝对 hold120 net mean 仍然为负。R04c 预先规定 validation 必须 `net_return_mean > 0`，所以这些相对改善不能升级为候选池通过。

最重要的判断：

1. `baseline_A` 在 validation 中确实非常差：net mean `-6.38%`，loss<=-5 `57.94%`，+50 rate 只有 `6.33%`。
2. R02 family pools 是当前最有信息量的 descriptive lead，尤其是 `r02_precision_volume_money`，validation matched delta `+4.53%`，loss delta `-10.84%`，但绝对 net 仍为 `-2.07%`。
3. R04-derived 高 RPS 子池保留了右尾，但 validation 的均值和左尾更差，不能作为更好的主候选池。
4. 年份集中不是主要解释。validation 本身年份集中，所有 pool 的 relative year concentration gate 都没有失败。
5. 当前不建议把任何 R04c pool 送入 R04b-style hold/exit/risk-budget replay。继续在这些 pool 上优化 exit policy，证据链仍然不够。

## 2. 运行与验证状态

本次 scanner 已完成运行并通过 validator。

| 项目 | 结果 |
|---|---:|
| pool profile rows | 36 |
| unique replayed pools | 12 |
| hold120 replay events | 65,108 |
| promotable pools in registry | 11 |
| validation gate candidate pools | 2 |
| validation passed pools | 0 |
| validator status | passed |
| validator checks | 51 |
| failed checks | 0 |

输出审计文件：

- `r04c_final_decision.csv`
- `r04c_hold120_pool_profile.csv`
- `r04c_matched_baseline_delta_summary.csv`
- `r04c_train_pool_selection_trace.csv`
- `r04c_validation_gate_audit.csv`
- `r04c_concentration_audit.csv`
- `r04c_overlap_uniqueness_audit.csv`
- `r04c_candidate_pool_scanner_validation_audit.csv`

## 3. Baseline_A Hold120 Profile

R04c 的 baseline_A 是 R04/R04b 的 `baseline_A_r04_included_rps_episode_first_trigger`，固定 entry，hold120 no-exit，fixed size。

| split | event_count | replay_complete | censored | net mean | p10 | loss<=-5 | +50 rate | max_gain120d p90 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 6,656 | 6,403 | 3.80% | 7.64% | -26.76% | 41.70% | 20.80% | 76.57% |
| validation | 3,453 | 3,414 | 1.13% | -6.38% | -29.38% | 57.94% | 6.33% | 41.06% |
| robustness | 2,864 | 2,800 | 2.23% | 6.12% | -19.92% | 35.25% | 11.29% | 53.21% |

这个表解释了 R04b 和 R04c 的核心难点：validation 不是轻微走弱，而是同时出现负均值、高左尾损失、低右尾命中。候选池如果不能在 validation 上至少转正，后续 exit policy 的改善空间很可能只是相对止血，而不是可升级的正期望池。

## 4. Source Readiness 与 Pool 范围

所有 source root 都存在，R04c v1 按 requirement 只允许部分 adapter 成为 promotable。

| source | readiness | adapter | v1 status |
|---|---|---|---|
| r02_family_precision | available | r02_family_precision_frozen_family_occurrence | promotable |
| r02_evidence_family | available | r02_evidence_family | descriptive only |
| r03b_signal_sequence | available | r03b_signal_sequence | descriptive only |
| r03c_family_set_pooling | available | r03c_config_frozen_family_set_pool | conditional, no config keys |
| r02_winner_anchored_v2 | available | r02_winner_anchored_v2 | descriptive only |
| r01_pre60_indicator_search_v2 | available | r01_pre60_indicator_search_v2 | descriptive only |
| r01_post30_indicator_search_v1 | available | r01_post30_indicator_search_v1 | descriptive only |

Registry 中 pool promotability 分布：

| status | pool count |
|---|---:|
| promotable | 11 |
| control_baseline | 1 |
| descriptive_control_not_replayed | 1 |
| descriptive_lead_only_no_config_keys | 1 |

这说明本次 scanner 不是因为 source 缺失而失败。失败发生在 pool quality gates，而不是工程输入缺口。

## 5. Pool Membership Waterfall

| pool_id | source rows | membership rows | episode rows | entry resolved | replay complete |
|---|---:|---:|---:|---:|---:|
| r04_rps95 | 12,973 | 1,685 | 1,685 | 1,685 | 1,623 |
| r04_rps95_money80 | 12,973 | 1,106 | 1,106 | 1,106 | 1,066 |
| r04_rps95_industry80 | 12,973 | 1,269 | 1,269 | 1,269 | 1,219 |
| r04_rps95_industry_relative10 | 12,973 | 212 | 212 | 212 | 207 |
| r02_precision_momentum_rps | 44,120 | 44,120 | 6,056 | 6,056 | 4,675 |
| r02_precision_oscillator | 23,132 | 23,132 | 7,675 | 7,675 | 5,862 |
| r02_precision_price_trend | 34,592 | 34,592 | 6,253 | 6,253 | 4,842 |
| r02_precision_pullback_drawdown | 56,446 | 56,446 | 6,266 | 6,266 | 4,855 |
| r02_precision_range_breakout | 68,679 | 68,679 | 6,558 | 6,558 | 5,002 |
| r02_precision_volatility_band | 28,211 | 28,211 | 7,115 | 7,115 | 5,425 |
| r02_precision_volume_money | 22,806 | 22,806 | 7,940 | 7,940 | 6,090 |
| r03c_config_frozen_family_set_pool | 0 | 0 | 0 | 0 | 0 |

R02 family pools 经过 20 trading days episode collapse 后仍有较大样本，说明它们不是小样本幻觉。R04-derived pools 则明显是 baseline_A 的窄子集，尤其 `r04_rps95_industry_relative10` 只有 207 个 replay-complete events，样本不足以作为主线。

## 6. Train Selection 结果

Train stage 只在同一 `pool_family_id` 内排序，不能用 validation/robustness 反选。

| family | selected in train | score | rank | 备注 |
|---|---|---:|---:|---|
| r04_deterministic_auxiliary | r04_rps95_industry80 | 3.3913 | 1 | 高 RPS + 行业强度，train 中右尾较好 |
| r02_family_precision | r02_precision_volume_money | 2.5433 | 1 | 量价共振 family，train 中综合分最高 |

未被 train 选中的 R02 pools 即使 validation 描述上好看，也不能替换 selected pool。这是 R04c 的关键纪律：validation 只能确认 train-selected pools，不允许反向挑 validation 最好看的 pool。

## 7. Validation Gate 细节

只有两个 train-selected pools 进入 validation hard gate。二者都失败。

| pool | replay_complete | censored | net mean | matched net delta | p10 delta | loss delta | +50 count | +50 rate | matched +50 | ESS | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r02_precision_volume_money | 1,568 | 24.40% | -2.07% | +4.53% | +3.03% | -10.84% | 94 | 5.99% | 5.84% | 3,000 | failed |
| r04_rps95_industry80 | 313 | 2.49% | -8.17% | -1.48% | -3.47% | +3.51% | 48 | 15.34% | 8.59% | 2,008 | failed |

逐条 gate 拆解：

| pool | replay>=300 | censored<=25% | matched sufficient | net>0 | matched net delta>0 | loss delta<0 | +50 ok | concentration ok |
|---|---|---|---|---|---|---|---|---|
| r02_precision_volume_money | pass | pass | pass | fail | pass | pass | pass | pass |
| r04_rps95_industry80 | pass | pass | pass | fail | fail | fail | pass | pass |

`r02_precision_volume_money` 是最值得注意的失败：它几乎只卡在 `net_return_mean > 0`。这说明它相对同年份/同 regime 的 baseline_A 有改善，但 validation split 本身太差，改善后仍没有转正。按 R04c 的设计，这种结果只能作为 descriptive lead，不能升级为新主池。

`r04_rps95_industry80` 的失败更彻底。它保留甚至强化右尾，但均值、p10、loss delta 全部变差。它不能解释为“差一点没过”，而是再次证明 RPS 强化更像右尾富集，不是完整 candidate pool improvement。

## 8. 全部 Validation Pool 的 Matched Baseline 对比

下表包含所有 validation pool，按 matched net delta 排序。注意：只有 train-selected pools 有资格进入 final gate；其他行只是描述性证据。

| pool | adapter | complete | censored | net mean | matched delta | p10 delta | loss delta | +50 rate | matched +50 | ESS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r02_precision_volume_money | r02_family_precision_frozen_family_occurrence | 1,568 | 24.40% | -2.07% | +4.53% | +3.03% | -10.84% | 5.99% | 5.84% | 3,000 |
| r02_precision_range_breakout | r02_family_precision_frozen_family_occurrence | 1,332 | 26.12% | -2.19% | +4.40% | +4.07% | -10.77% | 6.38% | 6.14% | 2,746 |
| r02_precision_pullback_drawdown | r02_family_precision_frozen_family_occurrence | 1,282 | 23.33% | -2.16% | +4.25% | +2.86% | -9.38% | 6.79% | 6.14% | 3,077 |
| r02_precision_oscillator | r02_family_precision_frozen_family_occurrence | 1,515 | 23.17% | -2.76% | +3.95% | +3.31% | -10.54% | 5.68% | 5.69% | 2,913 |
| r02_precision_volatility_band | r02_family_precision_frozen_family_occurrence | 1,430 | 25.44% | -3.11% | +3.47% | +2.12% | -9.04% | 5.87% | 5.96% | 3,083 |
| r02_precision_momentum_rps | r02_family_precision_frozen_family_occurrence | 1,261 | 22.26% | -3.23% | +3.24% | +2.05% | -6.63% | 6.42% | 5.95% | 3,135 |
| r02_precision_price_trend | r02_family_precision_frozen_family_occurrence | 1,285 | 21.31% | -3.35% | +3.03% | +1.65% | -7.81% | 6.30% | 6.18% | 3,069 |
| r04_rps95_industry80 | r04_deterministic_auxiliary | 313 | 2.49% | -8.17% | -1.48% | -3.47% | +3.51% | 15.34% | 8.59% | 2,008 |
| r04_rps95 | r04_deterministic_auxiliary | 433 | 1.81% | -9.13% | -2.38% | -4.77% | +4.89% | 13.63% | 7.60% | 2,585 |
| r04_rps95_money80 | r04_deterministic_auxiliary | 270 | 1.82% | -11.18% | -4.03% | -4.67% | +8.07% | 16.67% | 8.28% | 2,008 |
| r04_rps95_industry_relative10 | r04_deterministic_auxiliary | 66 | 0.00% | -13.43% | -5.49% | -5.81% | +6.52% | 9.09% | 3.72% | 725 |

这里有一个清晰分裂：

- R02 family pools 的 matched delta 全部为正，loss delta 全部为负，说明它们确实改善了相对路径质量。
- 但 R02 family pools 的 validation net mean 全部仍为负，范围约 `-2.07%` 到 `-3.35%`。
- R04-derived pools 的 +50 rate 明显更高，但它们的均值和左尾更差，说明它们只是右尾富集器，不是更好的 hold120 candidate pool。

## 9. Robustness 描述性 Readout

因为 validation 没有冻结 selected pool，robustness 不能参与 final selection。下面只作为描述性 readout。

| pool | complete | net mean | matched delta | loss delta | +50 rate | matched +50 | ESS |
|---|---:|---:|---:|---:|---:|---:|---:|
| r02_precision_price_trend | 1,211 | 8.79% | +1.31% | -3.41% | 10.82% | 11.54% | 2,227 |
| r02_precision_pullback_drawdown | 1,264 | 8.39% | +1.01% | -3.79% | 9.81% | 11.19% | 2,188 |
| r02_precision_volume_money | 1,553 | 7.82% | +0.85% | -6.11% | 10.17% | 11.46% | 2,423 |
| r02_precision_range_breakout | 1,230 | 8.57% | +0.59% | -5.89% | 10.57% | 12.79% | 2,135 |
| r02_precision_oscillator | 1,502 | 7.94% | +0.49% | -4.29% | 9.72% | 11.44% | 2,377 |
| r02_precision_momentum_rps | 1,225 | 7.02% | +0.43% | -2.28% | 9.55% | 11.02% | 2,545 |
| r02_precision_volatility_band | 1,377 | 8.37% | +0.31% | -4.10% | 10.02% | 11.68% | 2,258 |
| r04_rps95_money80 | 243 | 0.92% | -5.35% | +9.04% | 9.05% | 12.41% | 1,663 |
| r04_rps95_industry80 | 272 | 0.81% | -6.38% | +9.21% | 7.35% | 11.87% | 1,533 |
| r04_rps95 | 374 | 0.59% | -6.69% | +8.84% | 7.22% | 12.50% | 1,934 |
| r04_rps95_industry_relative10 | 76 | 5.83% | -8.87% | +11.84% | 11.84% | 17.42% | 641 |

Robustness 的描述性结果对 R02 family pools 比较友好：net mean 普遍为正，matched delta 也为正。但这不能推翻 final decision，原因有三点：

1. R04c 的选择纪律要求 validation 先冻结 selected pool；本次 validation 没有任何 pool 通过。
2. R02 family pools 的 robustness matched delta 只有 `+0.31%` 到 `+1.31%`，小于 robustness final gate 要求的 `+2%`。
3. 多个 R02 pools 的 censored share 在 robustness 中接近或超过 25% 门槛，说明 hold120 可交易完整性仍然不够稳。

所以 robustness 只能说明 R02 family pools 有 descriptive lead，不足以说明存在可升级主池。

## 10. Concentration 与 Overlap

Concentration audit 的关键结果：

| 指标 | 占比 |
|---|---:|
| matched_comparator_status != sufficient | 0.00% |
| pool_promotability_status != promotable | 21.43% |
| top1_calendar_year_share > 0.50 | 69.44% |
| relative year concentration fail | 0.00% |
| validation passed but robustness failed | 无 |

绝对年份集中率很高，但这不是 pool 独有问题。validation split 本身只有 2022/2023 两年，baseline_A 的 top1 year share 就是 `66.58%`。R04c 使用 matched baseline relative concentration gate 后，没有 pool 因年份集中而失败。换句话说，本次失败不是因为 concentration gate 太严，而是 pool 自身的收益/左尾 gate 没过。

Overlap audit 也提供了重要信息：

| pool | overlap with baseline_A | unique event share | 解释 |
|---|---:|---:|---|
| r04_rps95 / money80 / industry80 | 100.00% | 0.00% | 全部是 baseline_A 子集 |
| r02_precision_momentum_rps | 79.16% | 20.84% | 与 RPS baseline 高重叠 |
| r02_precision_price_trend | 40.88% | 59.12% | 有较多新事件 |
| r02_precision_pullback_drawdown | 34.41% | 65.59% | 有较多新事件 |
| r02_precision_range_breakout | 22.02% | 77.98% | 大部分是新事件 |
| r02_precision_volume_money | 21.12% | 78.88% | 大部分是新事件 |

这说明 R02 pools 不是简单复制 baseline_A 的子集。它们确实提供了新的 action-time event universe，但新 universe 目前只做到“相对更少亏”，没有在 validation 上形成正收益主池。

## 11. Findings

### 11.1 R02 family pools 是当前唯一值得保留的线索

R02 family pools 在 validation 中全部表现为：

```text
matched net delta > 0
p10 delta > 0
loss_le_minus5_delta < 0
```

这三个方向一致，说明 R02 family signal 相对 matched baseline_A 能改善路径质量。尤其 `r02_precision_volume_money`：

- validation net mean: `-2.07%`
- matched net delta: `+4.53%`
- p10 delta: `+3.03%`
- loss delta: `-10.84%`
- ESS: `2,999.5`

但它仍然没有达到 `net_return_mean > 0`。因此结论不是“R02 没有信息”，而是“R02 的信息不足以定义 R04b 主池”。

### 11.2 R04-derived 高 RPS 子池不应继续作为主线

R04-derived pools 的 validation 右尾更强：

- `r04_rps95_money80` +50 rate `16.67%`
- `r04_rps95_industry80` +50 rate `15.34%`
- `r04_rps95` +50 rate `13.63%`

但它们的 validation net mean 分别是 `-11.18%`、`-8.17%`、`-9.13%`，且 loss delta 为正，说明亏损路径更差。这个结果和 R04/R04b 的主判断一致：RPS 是右尾富集器，不是 action-time pool quality edge。

### 11.3 Validation 仍是整个 EP4 这条线的主要拦截器

baseline_A validation 已经是 `-6.38%`，R02 最好的 `volume_money` 把它相对 matched baseline 改善到 `-2.07%`，但没有转正。这个改善幅度不小，但还不够。

这对后续研究有约束意义：如果下一版 candidate pool scanner 仍然用 hold120 no-exit 作为入门门槛，就必须找到比 R02 family 更强的 pool selector，而不是继续在 RPS95 这类右尾子集上收窄。

### 11.4 Robustness 的正收益不能用来反选

robustness 中 R02 family pools 普遍正收益，例如：

- `r02_precision_price_trend`: net `8.79%`
- `r02_precision_pullback_drawdown`: net `8.39%`
- `r02_precision_volume_money`: net `7.82%`

但这些结果不能用来反选 pool。R04c 的设计就是防止“validation 不通过，但 robustness 看起来好，于是换 pool”的选择泄漏。当前报告必须维持这个纪律。

## 12. 对 Requirement 问题的逐项回答

1. 是否存在 hold120 baseline 明显优于 R04 baseline_A 的 candidate pool？

   没有达到可升级标准。R02 pools 相对 matched baseline_A 有改善，但 validation 绝对 net mean 仍为负。

2. 改善是否同时出现在 validation 和 robustness？

   描述性看，R02 pools 的 matched delta 在 validation 和 robustness 大多同向为正；但 validation 没有任何 pool 通过 hard gates，因此没有正式 selected pool 可进入 robustness readout。

3. 改善是否相对 matched baseline_A 仍存在？

   R02 family pools 存在。validation matched net delta 为 `+3.03%` 到 `+4.53%`。R04-derived pools 不存在，matched delta 为负。

4. 改善来自更高 net mean、更低 bad path、更高右尾，还是 denominator shrink？

   R02 的改善主要来自左尾压缩和 p10 改善，不来自右尾增强。R04-derived 的改善只体现在右尾富集，但左尾和均值恶化。

5. +50 winner rate 是否没有被牺牲？

   R02 family pools 在 validation 的 +50 rate 大致接近 matched baseline，但没有明显增强。R04-derived pools +50 rate 明显更高，但以更差左尾为代价。

6. 是否存在严重 calendar-year / instrument concentration？

   绝对年份集中高，但 matched baseline 也同样集中，relative concentration 没有失败。只有 `r04_rps95_industry_relative10` 在 validation 有 instrument relative concentration failure，但它本身样本也太小。

7. pool 是否由 train-only selection 得出？

   是。train 只选出 `r04_rps95_industry80` 和 `r02_precision_volume_money`，validation/robustness 没有参与定义或参数选择。

8. 哪些 source 只能 descriptive？

   `r02_evidence_family`、`r03b_signal_sequence`、`r02_winner_anchored_v2`、`r01_pre60_indicator_search_v2`、`r01_post30_indicator_search_v1` 在 v1 中均为 descriptive-only。`r03c_family_set_pooling` 因没有 config-frozen keys，本次也是 descriptive/no replay。

9. 是否有 pool 值得进入下一版 R04b-style replay？

   没有。`r02_precision_volume_money` 是最强 descriptive lead，但 validation net 仍为负，不应进入 R04b replay。

10. validation-frozen selected pool 是否就是 robustness readout 的唯一 final candidate？

   本次没有 validation-frozen selected pool，因此 robustness 没有 final candidate。

## 13. 后续判断

短期不建议做：

- 不建议把 `r04_rps95`、`r04_rps95_money80`、`r04_rps95_industry80` 送入 R04b 做 exit policy 优化。
- 不建议用 robustness 表现反选 R02 pools。
- 不建议把 validation pooled OOS 或 robustness positive result 当作通过依据。

可以保留的研究线索：

- R02 family pools，尤其 `volume_money`、`range_breakout`、`pullback_drawdown`，有稳定的 matched left-tail improvement。
- 如果要做 R04c v2，重点不应是 RPS 子集，而应是寻找能让 validation 绝对 net 转正的 pool selector。
- 如果继续研究 R02 family pools，问题应改写为“相对 matched baseline 的风险形态改善是否能通过更短 horizon 或不同 entry anchor 转成正期望”，而不是直接进入 R04b exit policy。

最终判断：R04c v1 完成了它的筛选职责。它没有找到可升级主池，但明确缩小了后续方向：R04-derived 高 RPS 路线应降级，R02 family pools 只作为 descriptive lead 保留，下一步需要新的 candidate pool source 或重新定义 pool anchor，而不是继续在 baseline_A/RPS 子集上调持有和退出。

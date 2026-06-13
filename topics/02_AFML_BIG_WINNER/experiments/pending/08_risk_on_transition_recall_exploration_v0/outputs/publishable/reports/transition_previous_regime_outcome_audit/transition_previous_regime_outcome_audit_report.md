# Experiment G - Previous-Regime Conditioned Transition Outcome Audit 报告

最终决策：`transition_previous_regime_conditioning_diagnostic_only`

## 0. 实验边界

本实验不训练模型，也不把 transition 子状态当作 PIT 时点可完全识别的标签。它只验证一个轻量假设：**transition 的后续走向可能与它之前的非 transition regime 有关**。

因此这里的 `transition_from_risk_on` / `transition_from_risk_off` 是 PIT context；`transition_continuation` / `transition_conversion` 是 ex-post readout。grid search 只搜索规则约束，不使用 recall、cost、winner outcome 选参。

selected rule:

| field | value |
|:--|:--|
| `grid_rule_id` | `g_base_minprev1_age1_confirm0_outmaxnull` |
| `min_previous_regime_trading_day_n` | 1 |
| `min_segment_age_at_event_t0` | 1 |
| `online_confirmation_trading_day_n` | 0 |
| `outcome_max_transition_trading_day_n` | unlimited / null |
| `selection_reason` | `no_structurally_eligible_rule_use_base_diagnostic` |

Gate / caveat:

- `selected_rule_structural_eligibility_not_met`
- `published_transition_not_reconstructed_share_gt_20pct`
- `supported_cell_low_segment_power_diagnostic`
- `upstream_source_caveated`

## 1. 核心结论

**结论一：前序 regime 确实带有路径信息。**
在 segment catalog 中，已完成 outcome 的 transition segment 共 113 段；若前序是 `risk_off`，后续转化为 `risk_on` 的 segment 为 16/40=40.0%；若前序是 `risk_on`，后续转化为 `risk_off` 的 segment 为 14/74=18.9%。这说明 transition 不是一个孤立状态，它很可能是“从哪里来”决定“往哪里去”的路径状态。

**结论二：这个方向现在只能做 diagnostic/readout，不能升级为 supported taxonomy。**
主要原因不是标签 join 或 leakage，而是 power 和 universe binding：400 个 grid rule 中没有任何一个 structural eligible；selected base rule 虽然 aggregate continuation/conversion 有 power，但 `robustness:transition_conversion` 仍是低 segment power。与此同时，published transition 中有 30.59% 没有被 reconstructed transition 复现，重建一致率只有 81.17%。

**结论三：方向级 conversion 不能单独声称有效。**
`risk_off -> risk_on` 与 `risk_on -> risk_off` 的 conversion 在 robustness 中分别只有 1 段和 2 段，其中 `risk_off -> risk_on` 的 top1 segment episode share=100.0%，`risk_on -> risk_off` 的 top1 segment episode share=93.8%。这些读数可以解释图形和案例，但不能作为稳定证据。

**结论四：R-core 仍然是高 recall source，但这不能证明 G 规则本身可训练。**
在 published & reconstructed transition universe 中，R-core 对各 cell 的 episode recall 基本在 95.7%-100.0%；R6 更稀疏，范围 12.2%-84.8%。这更像是“R-core/R6 作为 recall source 的覆盖差异”，不是 previous-regime rule 的直接可交易优势。

## 2. 数据与组件状态

| component | value |
|:--|:--|
| primary index | `SH000985` |
| index date range | 2017-01-03 到 2026-05-29 |
| index row count | 2281 |
| event-level join rows | 90576 |
| future join count | 0 |
| `market_trend_60d` missing rate | 0.0% |
| `market_drawdown_120d` missing rate | 0.0% |
| reconstructed vs published regime consistency | 81.17% |
| legacy 60d drawdown consistency | 74.49% |
| F component alignment | `aligned_with_experiment_f_component` |
| component reuse policy | `rebuild_from_experiment_f_component_audit` |

Label 对账通过：

| label | compared event n | mismatch n | status |
|:--|--:|--:|:--|
| `failure_10_label` | 17668 | 0 | pass |
| `event_false_repair_20d_label` | 17714 | 0 | pass |

Leakage audit 全部通过：PIT context 只使用前序 regime 与 as-of segment age；outcome label 只作为 readout；grid selection 不使用 recall/cost/winner；validation 不参与 performance tuning；per-direction conversion 固定为 diagnostic-only。

## 3. Universe Binding

primary readout 使用 reconstructed transition universe。published 与 reconstructed 的漂移很大，这是最终 diagnostic-only 的硬约束之一。

| universe binding status | event n | share of all events | share of published transition events |
|:--|--:|--:|--:|
| non-transition out of scope | 56022 | 61.85% |  |
| published and reconstructed transition | 17500 | 19.32% |  |
| published transition not reconstructed transition | 7714 | 8.52% | 30.59% |
| reconstructed transition not published transition | 9340 | 10.31% |  |

解释：

- published transition 总量为 25214 个 event，其中 7714 个没有落入 reconstructed transition。
- reconstructed transition 总量为 26840 个 event，其中 9340 个不在 published transition 中。
- 这不是小误差，说明 G 的路径读数必须被视为 reconstructed-regime diagnostic，而不能直接覆盖 published-regime 结论。

## 4. Grid Search 结果

grid search 是轻量规则搜索，不训练模型。参数空间为：

- `min_previous_regime_trading_day_n`: 1, 3, 5, 10, 20
- `min_segment_age_at_event_t0`: 1, 2, 3, 5
- `online_confirmation_trading_day_n`: 0, 1, 2, 3
- `outcome_max_transition_trading_day_n`: 20, 60, 120, 240, null

总计 400 个 candidate rule。

| metric | n | share |
|:--|--:|:--|
| grid candidates | 400 | 100.0% |
| structural eligible | 0 | 0.0% |
| aggregate power pass | 64 | 16.0% |
| both contexts all splits pass | 360 | 90.0% |
| censored share pass | 64 | 16.0% |

selected base rule 的关键读数：

| metric | value |
|:--|--:|
| candidate event n | 26840 |
| unique transition segment n | 104 |
| censored event share | 0.0% |
| pending or censored event share | 0.0% |
| base direction agreement | 100.0% |
| direction distribution distance | 0.0 |
| aggregate outcome power flag | true |
| low segment power cells | `robustness:transition_conversion` |
| structural eligible flag | false |

解释：base rule 是最宽松、最接近图形直觉的规则。它能保住 aggregate continuation/conversion 的基本覆盖，但过不了 structural eligibility，因为 robustness conversion 的 segment 仍然太少。

## 5. Transition Segment 结构

全 catalog 共 239 段，其中已完成 transition outcome 的 segment 为 113 段，另有 1 段 pending/censored。transition 本身很短：median=3 个交易日，48.67% 的 transition segment 不超过 2 个交易日，31.86% 只有 1 个交易日。

| duration statistic | transition segment trading day n |
|:--|--:|
| count | 113 |
| mean | 5.91 |
| std | 8.53 |
| min | 1 |
| p25 | 1 |
| median | 3 |
| p75 | 7 |
| p90 | 13.8 |
| p95 | 23.6 |
| max | 59 |

按前序 regime 与 outcome 拆分：

| previous regime | outcome | segment n | conversion share within previous regime |
|:--|:--|--:|--:|
| risk_off | continuation | 24 |  |
| risk_off | conversion to risk_on | 16 | 40.0% |
| risk_on | continuation | 59 |  |
| risk_on | conversion to risk_off | 14 | 18.9% |

这组数支持“transition 与前序状态有关”的直觉：从 `risk_off` 进入 transition 时，后续转向 `risk_on` 的比例明显高于从 `risk_on` 进入 transition 后转向 `risk_off` 的比例。但由于它是 segment-level 的历史分布，不是 PIT 预测结果，不能直接转成训练标签。

## 6. Segment Power 与贡献集中度

下表只看 primary focus：`published_and_reconstructed_transition`。这是最可信的交集 universe。

| split | PIT context | outcome | segment n | trading day n | event n | target episode n | top1 episode share | effective segment n | power status |
|:--|:--|:--|--:|--:|--:|--:|:--|--:|:--|
| robustness | from risk_off | continuation | 3 | 11 | 167 | 105 | 62.9% | 1.79 | low_segment_power_diagnostic |
| robustness | from risk_off | conversion | 1 | 18 | 49 | 30 | 100.0% | 1.00 | low_segment_power_diagnostic |
| robustness | from risk_on | continuation | 8 | 39 | 135 | 115 | 31.3% | 4.88 | low_segment_power_caution |
| robustness | from risk_on | conversion | 2 | 24 | 103 | 48 | 93.8% | 1.13 | low_segment_power_diagnostic |
| train | from risk_off | continuation | 7 | 32 | 335 | 241 | 36.5% | 4.24 | low_segment_power_caution |
| train | from risk_off | conversion | 8 | 75 | 832 | 454 | 27.1% | 4.71 | low_segment_power_caution |
| train | from risk_on | continuation | 15 | 76 | 313 | 210 | 18.1% | 7.33 | sufficient_segment_power |
| train | from risk_on | conversion | 4 | 14 | 65 | 49 | 44.9% | 2.60 | low_segment_power_diagnostic |
| validation | from risk_off | continuation | 7 | 38 | 236 | 119 | 37.0% | 3.18 | low_segment_power_caution |
| validation | from risk_off | conversion | 2 | 17 | 59 | 45 | 53.3% | 1.99 | low_segment_power_diagnostic |
| validation | from risk_on | continuation | 5 | 81 | 176 | 71 | 53.5% | 2.52 | low_segment_power_diagnostic |
| validation | from risk_on | conversion | 4 | 29 | 79 | 47 | 51.1% | 2.54 | low_segment_power_diagnostic |

按 aggregate outcome 汇总：

| split | outcome | segment n | trading day n | event n | target episode n | max top1 episode share | min effective segment n |
|:--|:--|--:|--:|--:|--:|:--|--:|
| robustness | continuation | 11 | 50 | 302 | 220 | 62.9% | 1.79 |
| robustness | conversion | 3 | 42 | 152 | 78 | 100.0% | 1.00 |
| train | continuation | 22 | 108 | 648 | 451 | 36.5% | 4.24 |
| train | conversion | 12 | 89 | 897 | 503 | 44.9% | 2.60 |
| validation | continuation | 12 | 119 | 412 | 190 | 53.5% | 2.52 |
| validation | conversion | 6 | 46 | 138 | 92 | 53.3% | 1.99 |

读法：

- train 的 `from risk_on / continuation` 是唯一 sufficient segment power cell。
- robustness 的 conversion 虽然 target episode n=78，但只来自 3 个 segment，其中 `from risk_off / conversion` 只有 1 段。
- 这说明 episode denominator 看起来不小，但贡献高度集中，不能当成稳定 OOS 证据。

## 7. Recall 与 E1-Missed Capture

下表仍只看 `published_and_reconstructed_transition`，并只列核心 recall source：R-core 与 R6。

| split | PIT context | outcome | target episode n | segment n | R-core captured | R-core recall | R6 captured | R6 recall | segment power | concentration |
|:--|:--|:--|--:|--:|:--|:--|:--|:--|:--|:--|
| validation | from risk_on | conversion | 47 | 4 | 45/47 | 95.7% | 23/47 | 48.9% | low_segment_power_diagnostic | single_segment_dominated_diagnostic |
| robustness | from risk_on | conversion | 48 | 2 | 47/48 | 97.9% | 33/48 | 68.8% | low_segment_power_diagnostic | single_segment_dominated_diagnostic |
| train | from risk_on | continuation | 210 | 15 | 207/210 | 98.6% | 104/210 | 49.5% | sufficient_segment_power | not_concentrated |
| validation | from risk_off | continuation | 119 | 7 | 118/119 | 99.2% | 79/119 | 66.4% | low_segment_power_caution | concentrated_low_power_caution |
| train | from risk_off | conversion | 454 | 8 | 451/454 | 99.3% | 340/454 | 74.9% | low_segment_power_caution | concentrated_low_power_caution |
| validation | from risk_on | continuation | 71 | 5 | 69/71 | 97.2% | 48/71 | 67.6% | low_segment_power_diagnostic | single_segment_dominated_diagnostic |
| robustness | from risk_off | continuation | 105 | 3 | 105/105 | 100.0% | 89/105 | 84.8% | low_segment_power_diagnostic | single_segment_dominated_diagnostic |
| train | from risk_off | continuation | 241 | 7 | 241/241 | 100.0% | 152/241 | 63.1% | low_segment_power_caution | concentrated_low_power_caution |
| train | from risk_on | conversion | 49 | 4 | 49/49 | 100.0% | 13/49 | 26.5% | low_segment_power_diagnostic | single_segment_dominated_diagnostic |
| robustness | from risk_on | continuation | 115 | 8 | 113/115 | 98.3% | 14/115 | 12.2% | low_segment_power_caution | concentrated_low_power_caution |
| validation | from risk_off | conversion | 45 | 2 | 44/45 | 97.8% | 11/45 | 24.4% | low_segment_power_diagnostic | single_segment_dominated_diagnostic |
| robustness | from risk_off | conversion | 30 | 1 | 30/30 | 100.0% | 19/30 | 63.3% | low_segment_power_diagnostic | single_segment_dominated_diagnostic |

观察：

- R-core 的 recall 很强，但几乎所有 conversion cell 都是 low power 或 single segment dominated，因此不能把高 recall 解释为 G 规则稳定有效。
- R6 更像稀疏 recall source。它在 `robustness / from risk_off / continuation` 有 84.8%，但在 `robustness / from risk_on / continuation` 只有 12.2%，说明按 previous-regime/outcome 切开后覆盖差异很大。
- E1-missed capture 与 recall 数值一致，因为这些 cell 的 E1-missed denominator 覆盖了全部 target episodes；这说明该读数可用于 recall readout，但不能解决 segment power 问题。

## 8. Cost / Quality Readout

下表列 R-core/R6 的 fast-fail、false-repair 与 120d big-winner rate。它是 readout，不参与 selected rule 选择。

| split | PIT context | outcome | R-core event n | R-core fast-fail | R-core false-repair | R-core big-winner | R6 event n | R6 fast-fail | R6 false-repair | R6 big-winner |
|:--|:--|:--|--:|:--|:--|:--|--:|:--|:--|:--|
| robustness | from risk_off | continuation | 164 | 15.9% | 36.0% | 48.2% | 89 | 14.6% | 33.7% | 47.2% |
| robustness | from risk_off | conversion | 49 | 10.2% | 12.2% | 24.5% | 19 | 5.3% | 10.5% | 26.3% |
| robustness | from risk_on | continuation | 131 | 2.3% | 5.3% | 54.3% | 14 | 0.0% | 7.1% | 78.6% |
| robustness | from risk_on | conversion | 100 | 23.0% | 29.0% | 46.0% | 33 | 33.3% | 42.4% | 57.6% |
| train | from risk_off | continuation | 335 | 15.8% | 20.3% | 46.0% | 152 | 9.9% | 14.5% | 52.0% |
| train | from risk_off | conversion | 818 | 10.0% | 9.4% | 46.5% | 350 | 12.0% | 12.0% | 45.4% |
| train | from risk_on | continuation | 307 | 11.7% | 11.4% | 39.4% | 105 | 10.5% | 10.5% | 47.6% |
| train | from risk_on | conversion | 62 | 24.2% | 14.5% | 25.8% | 13 | 15.4% | 0.0% | 53.8% |
| validation | from risk_off | continuation | 232 | 14.2% | 15.1% | 34.9% | 89 | 9.0% | 12.4% | 38.2% |
| validation | from risk_off | conversion | 58 | 6.9% | 8.6% | 13.8% | 11 | 9.1% | 9.1% | 27.3% |
| validation | from risk_on | continuation | 173 | 16.3% | 22.0% | 15.1% | 59 | 12.1% | 16.9% | 12.1% |
| validation | from risk_on | conversion | 77 | 10.4% | 15.6% | 24.7% | 23 | 4.3% | 8.7% | 30.4% |

解释：

- `from risk_on / conversion` 在 robustness 上的 cost 明显偏高：R-core fast-fail=23.0%、false-repair=29.0%；R6 fast-fail=33.3%、false-repair=42.4%。这符合“risk_on 后转坏”的直觉，但只有 2 个 segment，不能作为 supported。
- `from risk_on / continuation` 在 robustness 上质量最好：R-core fast-fail=2.3%、false-repair=5.3%、big-winner=54.3%；R6 big-winner=78.6%。但 R6 event n 只有 14，且这个 cell 仍然是 concentration caution。
- `from risk_off / conversion` 在 validation/robustness 的 big-winner rate 较低，可能意味着从 risk_off 恢复到 risk_on 的 transition 对当前候选族并不天然更优；也可能只是低 power + segment composition 的结果。

## 9. Density / Overlap Readout

R-core 的 recall 高，但重复密度也明显更高。R6 的 20d duplicate rate 基本为 0，是更稀疏的 source。

| split | PIT context | outcome | R-core event n | R-core rolling20 density | R-core rolling20 duplicate | R6 event n | R6 rolling20 density | R6 rolling20 duplicate |
|:--|:--|:--|--:|--:|:--|--:|--:|:--|
| robustness | from risk_off | continuation | 164 | 1.49 | 36.0% | 89 | 1.00 | 0.0% |
| robustness | from risk_off | conversion | 49 | 1.49 | 38.8% | 19 | 1.00 | 0.0% |
| robustness | from risk_on | continuation | 131 | 1.12 | 12.2% | 14 | 1.00 | 0.0% |
| robustness | from risk_on | conversion | 100 | 1.82 | 53.0% | 33 | 1.00 | 0.0% |
| train | from risk_off | continuation | 335 | 1.29 | 26.0% | 152 | 1.00 | 0.0% |
| train | from risk_off | conversion | 818 | 1.58 | 42.7% | 350 | 1.00 | 0.0% |
| train | from risk_on | continuation | 307 | 1.36 | 31.3% | 105 | 1.00 | 0.0% |
| train | from risk_on | conversion | 62 | 1.24 | 21.0% | 13 | 1.00 | 0.0% |
| validation | from risk_off | continuation | 232 | 1.68 | 41.4% | 89 | 1.00 | 0.0% |
| validation | from risk_off | conversion | 58 | 1.34 | 24.1% | 11 | 1.00 | 0.0% |
| validation | from risk_on | continuation | 173 | 1.97 | 56.1% | 59 | 1.03 | 3.4% |
| validation | from risk_on | conversion | 77 | 1.57 | 41.6% | 23 | 1.00 | 0.0% |

读法：

- R-core 的高 recall 伴随高 duplicate rate，特别是 `robustness / from risk_on / conversion` 达到 53.0%。
- 如果后续要把 previous-regime context 用进筛选逻辑，不能只看 recall；必须结合 cost rejector 或 density de-dup，否则容易把同一段 transition 内的重复信号放大。

## 10. Findings and Insight

1. **previous-regime conditioning 是一个合理的 readout 维度。**
   图形直觉得到了数据支持：transition 的 outcome 与前序状态有明显关联。尤其是 `risk_off -> transition` 的恢复型 conversion 比例高于 `risk_on -> transition` 的恶化型 conversion。

2. **当前最主要的问题是 power，不是标签或泄漏。**
   label join mismatch=0，leakage audit pass；但 selected rule 下 23 个 segment matrix cell 中，17 个是 `low_segment_power_diagnostic`，5 个是 `low_segment_power_caution`，只有 1 个 sufficient。

3. **episode denominator 会掩盖 segment concentration。**
   例如 robustness conversion 有 78 个 target episodes，但只来自 3 个 segment，且一个 cell 完全由 1 个 segment 支配。这种情况下 episode-level recall 很容易看起来稳定，但实际是少数长段在主导。

4. **per-direction conversion 只能做案例解释。**
   `risk_off_to_risk_on_recovery_conversion` 与 `risk_on_to_risk_off_deterioration_conversion` 在 robustness 上分别只有 1 段和 2 段。方向标签有解释力，但不能单独构成 supported evidence。

5. **若要继续推进，不建议训练。**
   更稳妥的下一步是把 previous-regime context 作为 report/readout 切片，或者作为 cost rejector 的可解释分组变量，而不是把它当成一个新的 supervised taxonomy。

## 11. 可用方式

可以使用：

- 把 `transition_from_risk_on` / `transition_from_risk_off` 加入报告分组。
- 在 cost rejector 里把 previous-regime context 作为解释性 stratification，而不是单独 gate。
- 用 aggregate continuation vs conversion 观察成本和 recall 差异。
- 用方向级 conversion 做案例复盘，但必须标注 low power。

不可以声称：

- 不得声称 direct-entry support。
- 不得声称 official train process。
- 不得声称 conversion 是 PIT 可完全识别状态。
- 不得把 selected grid rule 解释为收益最优规则。
- 不得把 per-direction conversion 当成 supported evidence。

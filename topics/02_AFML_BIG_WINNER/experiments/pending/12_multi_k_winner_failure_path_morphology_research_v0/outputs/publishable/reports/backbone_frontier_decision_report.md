# 12A3 Episode Precision / Recall Frontier 决策报告

## 结论

- 决策状态：`12A3_state_change_backbone_partial_feature_source`
- 主候选：`12A2_C0_primary_canonical_union`
- 对照基准：`08_R_core_event_regime_gated_raw`
- R-core timing baseline：`12A3_recomputed_low_to_high_captured_episode_first_event`
- 推荐下一步：`requirement_12a4_filter_feasibility_or_priority_revision.md`

12A3 不支持把 state-change C0 union 直接升级为 winner/failure morphology 的事件 backbone。C0 union 在 428 个 06 risk_on winner episode 上保持了高 episode recall，并且显著降低 event density 与 same-instrument duplicate，低点后首个事件也更早；但它没有赢下核心 precision frontier：low-to-high event precision 只有 5.32%，低于 R-core 的 6.39%，也低于 supported gate 的 8.39%。因此当前最合理定位是 partial feature source，而不是 primary event backbone。

## 读数口径

- Episode recall denominator：06 risk_on `428` 个 episode。
- Event precision denominator：候选 arm 的全部事件数 `event_n`，numerator 是落入 episode window 的 `event_inside_window_n`。
- 主要窗口：
  - `pre120_calendar_to_high`：episode low 前 120 个自然日到 high。
  - `low_to_high`：episode low 到 high。
- supported decision 的关键比较是 state-change C0 union vs R-core，而不是 family 内部排序。

## 全局 Frontier

| 指标 | State-change C0 | R-core | 解释 |
| --- | ---: | ---: | --- |
| event_n | 28,691 | 47,914 | C0 事件量约为 R-core 的 59.9% |
| pre120 captured / eligible | 428 / 428 | 428 / 428 | 两者都覆盖全部 428 episodes |
| pre120 recall | 100.00% | 100.00% | raw recall 不构成 C0 优势 |
| pre120 event precision | 8.42% | 10.11% | C0 低 1.69 pct，precision ratio 0.833 |
| low-to-high captured / eligible | 422 / 428 | 417 / 428 | C0 多捕获 5 个 episode |
| low-to-high recall | 98.60% | 97.43% | C0 recall +1.17 pct |
| low-to-high event precision | 5.32% | 6.39% | C0 precision -1.08 pct，ratio 0.832 |
| low-to-high inside events | 1,526 | 3,064 | C0 的命中事件更少，但总事件也更少 |
| outside event rate | 94.68% | 93.61% | C0 总体噪声占比仍更高 |
| events per captured episode median | 4 | 7 | C0 的 episode 内事件负担更低 |
| events per captured episode p95 | 6 | 14 | C0 明显降低尾部事件密度 |
| events / instrument / year mean | 7.92 | 13.23 | C0 density ratio 0.599 |
| events / instrument / year p95 | 22.18 | 38.12 | C0 也降低高密度 instrument 尾部 |
| same-instrument 10d duplicate | 7.25% | 57.83% | C0 的重复事件问题显著更轻 |
| same-instrument 20d duplicate | 40.26% | 71.14% | C0 中期重复仍存在，但低于 R-core |
| first event minus low median | 9 sessions | 14 sessions | C0 更早锚定 low 后状态变化 |
| bad-side 10/20 rate | 31.97% | 34.46% | C0 的负向暴露略低 |
| winner 120d rate | 16.14% | 16.54% | winner 标签率基本相当 |

关键含义：C0 union 不是 precision 更强的事件定义，而是一个低密度、低重复、较早触发的 state-change feature source。它能更节制地覆盖 winner episode，但每个事件落入 winner lifecycle 的概率没有超过 R-core。

## Gate 结果

- supported gate：`False`
- partial feature source gate：`True`
- 失败 gate：
  - `low_to_high_precision_gate`
  - `low_to_high_precision_abs_delta_gate`
  - `low_to_high_precision_ratio_gate`
  - `pre120_precision_gate`
  - `robustness_stability_gate`

低点到高点 precision gate 的阈值是 8.39%，C0 实际为 5.32%，R-core 为 6.39%。这意味着 C0 不只是没有超过 R-core，它距离 supported gate 还有 3.08 pct 的绝对缺口。Recall、density、duplicate、timing 都是可用读数，但它们不能替代 precision gate。

## Split 稳定性

| Split | Arm | low-to-high recall | low-to-high precision | first event median | density ratio vs R-core | bad-side 10/20 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| train | C0 | 99.56% | 5.83% | 11 | 0.304 | 35.01% |
| train | R-core | 98.67% | 7.50% | 14 | 0.507 | 38.45% |
| robustness | C0 | 96.69% | 7.52% | 9 | 0.152 | 25.81% |
| robustness | R-core | 94.48% | 7.88% | 12 | 0.270 | 29.53% |

Split 读数支持 partial feature source，但不支持 backbone。C0 在 train 和 robustness 都保留 recall 与 lower-density 优势；precision 在 robustness 接近 R-core，但 train gap 更大，且两个 split 都没有形成“state-change precision 明显优于 R-core”的证据。`robustness_stability_gate` 失败说明当前 C0 的优势结构仍依赖样本切片，不能把单一读数外推成稳定 backbone。

## Family Anatomy

| Family | low-to-high captured | recall | event_n | inside events | precision | density ratio | 10d dup | bad-side | first event median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B1 | 228 | 53.27% | 4,570 | 276 | 6.04% | 0.095 | 0.74% | 32.49% | 23 |
| B2 | 125 | 29.21% | 3,143 | 142 | 4.52% | 0.066 | 0.35% | 26.28% | 20 |
| B3 | 117 | 27.34% | 3,508 | 150 | 4.28% | 0.073 | 0.80% | 26.62% | 21 |
| B4 | 19 | 4.44% | 369 | 25 | 6.78% | 0.008 | 0.27% | 54.20% | 47 |
| B5 | 328 | 76.64% | 10,887 | 610 | 5.60% | 0.227 | 1.83% | 32.86% | 23 |
| B6 | 119 | 27.80% | 2,443 | 134 | 5.49% | 0.051 | 0.53% | 32.99% | 38 |
| B8 | 160 | 37.38% | 3,771 | 189 | 5.01% | 0.079 | 0.66% | 35.67% | 36 |

Family 结构显示 C0 的 recall 主要由 B5 和 B1 提供。B5 单独捕获 328 个 episode，是最强 recall family；B1 precision 略高，但捕获只有 228 个 episode。B4 的 precision 最高，但只有 19 个 low-to-high episode，且 bad-side 高达 54.20%，不能作为主干。B8 捕获不少 episode，但首触发偏晚，低点后 median 为 36 sessions。

pre120 读数也支持同一判断：B5 pre120 recall 92.99%，B1 68.46%，B8 53.74%；但这些 family 的 pre120 precision 分别为 8.94%、9.15%、7.74%，没有稳定超过 R-core pre120 precision 10.11%。因此 family 层面的主要价值是状态分解与后续过滤，而不是直接替代 R-core。

## Priority 与 Confidence Diagnostics

| Arm | captured | recall | event_n | precision | median events / episode | density ratio | 10d dup | first event median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C0 canonical union | 422 | 98.60% | 28,691 | 5.32% | 4 | 0.599 | 7.25% | 9 |
| B3-before-B1 sensitivity | 422 | 98.60% | 27,742 | 5.25% | 4 | 0.579 | 0.00% | 9 |
| B5 downpriority sensitivity | 422 | 98.60% | 27,742 | 5.25% | 4 | 0.579 | 0.00% | 9 |
| multi-family trigger >=2 | 297 | 69.39% | 8,574 | 5.46% | 1 | 0.179 | 1.46% | 20 |
| single-family trigger | 396 | 92.52% | 20,117 | 5.26% | 2 | 0.420 | 5.33% | 15 |
| B1/B3 collision current priority | 30 | 7.01% | 748 | 4.14% | 1 | 0.016 | 0.00% | 20 |

Priority sensitivity 没有解决 precision 问题：B3-before-B1 与 B5 downpriority 让 event_n 小幅下降、density 更低，但 low-to-high precision 也从 5.32% 降到 5.25%，recall 不变。Multi-family trigger 提高不了 precision，只把 recall 从 98.60% 砍到 69.39%。这说明“多 family 共振”不是当前数据里的强过滤器；它更像 confidence feature，而不是 event selection rule。

## B8 Incremental

| Window | B8 captured | B1/B3/B5 captured | incremental episodes | incremental recall | incremental share of B8 | incremental event precision | first event median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pre120-to-high | 326 | 426 | 2 | 0.47% | 0.61% | 0.10% | -26 |
| low-to-high | 246 | 410 | 6 | 1.40% | 2.44% | 0.13% | 16 |
| low-to-first-50pct | 246 | 410 | 6 | 1.40% | 2.44% | 0.13% | 16 |

B8 不应被解释为 backbone recall 的核心来源。它低点到高点单独能捕获 246 个 episode，但相对 B1/B3/B5 的真正增量只有 6 个 episode，且增量事件 precision 只有 0.13%。B8 的合理用途是 rare residual / sustained-trend feature，用来解释少量其他 family 未覆盖的趋势延续，而不是提高主干 recall。

低点到高点的 6 个 B8 增量 episode 是：

- `SH600779_20210802_0005`
- `SH600879_20250904_0003`
- `SH603127_20210706_0000`
- `SH603786_20210112_0000`
- `SZ300017_20250904_0002`
- `SZ300123_20190429_0001`

## Board 与 Regime

### Board

| Board | Arm | captured / eligible | recall | event_n | precision | density mean | density p95 | 10d dup | bad-side |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| chinext | C0 | 116 / 119 | 97.48% | 5,894 | 6.87% | 1.63 | 5.00 | 7.40% | 43.28% |
| chinext | R-core | 115 / 119 | 96.64% | 9,992 | 8.04% | 2.76 | 9.71 | 58.50% | 45.51% |
| main_board | C0 | 306 / 309 | 99.03% | 22,797 | 4.92% | 6.29 | 16.03 | 7.21% | 29.05% |
| main_board | R-core | 302 / 309 | 97.73% | 37,922 | 5.96% | 10.47 | 27.11 | 57.66% | 31.55% |

C0 在两个 board 上都降低 density 与 duplicate，但 precision 都低于 R-core。Chinext 的 C0 precision 更高，但 bad-side 也高达 43.28%；main board 更稳，但 precision 只有 4.92%。因此 board filter 可能提高可解释性，却不能单独解决 supported precision gate。

### Market Regime

| Regime | captured / eligible | recall | event_n | inside events | precision | density mean | 10d dup | bad-side |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| risk_on | 402 / 428 | 93.93% | 15,113 | 1,016 | 6.72% | 4.17 | 5.86% | 34.03% |
| transition | 236 / 428 | 55.14% | 7,435 | 383 | 5.15% | 2.05 | 3.77% | 29.40% |
| risk_off | 83 / 428 | 19.39% | 6,143 | 127 | 2.07% | 1.70 | 4.36% | 30.02% |

Regime 是 12A4 最值得优先验证的过滤维度。C0 的有效命中主要集中在 risk_on：recall 93.93%，precision 6.72%，接近但仍低于 supported 门槛。transition 与 risk_off 的 recall 和 precision 都明显偏弱，尤其 risk_off precision 只有 2.07%。这说明 state-change 事件不是一个跨 regime 稳定的 winner lifecycle anchor，而更像 risk_on 状态持续中的低密度确认信号。

## Missed Episode 结构

C0 在 low-to-high 窗口漏掉 6 个 episode，全部来自 robustness split，miss reason 均为 `timing_calendar_gap`。

| Episode | Board | Duration | Low | High | Sessions | MFE120 | nearest event before low | gap sessions |
| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: |
| `SH600489_20251105_0004` | main_board | medium | 2025-11-05 | 2026-01-29 | 59 | 1.0688 | 2025-10-14 | 16 |
| `SH600547_20251105_0006` | main_board | medium | 2025-11-05 | 2026-01-29 | 59 | 0.9538 | 2025-09-09 | 35 |
| `SZ002008_20251017_0000` | main_board | long | 2025-10-17 | 2026-04-16 | 120 | 1.5175 | 2025-09-18 | 15 |
| `SZ300251_20251017_0008` | chinext | long | 2025-10-17 | 2026-02-11 | 81 | 0.8537 | 2025-09-24 | 11 |
| `SZ300383_20251023_0005` | chinext | long | 2025-10-23 | 2026-04-14 | 114 | 0.5016 | 2025-08-18 | 42 |
| `SZ300699_20250801_0007` | chinext | long | 2025-08-01 | 2026-01-12 | 108 | 0.5754 | 2025-05-30 | 44 |

这些 miss 不是“同一 instrument 完全没有 state-change 事件”，而是最近事件都早于 low 11-44 个 trading sessions。问题更像 event carry-forward / decay horizon，而不是 family 缺失。12A4 如果要补 recall，不宜盲目增加新 family；更合理的是验证“low 前最近 state-change 的有效期”是否可以作为特征，而不是把窗口放宽成更多事件。

## 标签与 PIT 可执行性

| Arm | next open executable | event_t0 PIT pass | label20 complete | label120 complete | fast-fail 10d | false-repair 20d | winner 120d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C0 | 100.00% | 100.00% | 100.00% | 99.96% | 21.62% | 28.82% | 16.14% |
| R-core | 100.00% | 100.00% | 100.00% | 99.81% | 24.20% | 31.11% | 16.54% |

State-change 标签重算 parity 通过：

| Label | source events | comparable | matched | parity match | status |
| --- | ---: | ---: | ---: | ---: | --- |
| `failure_10_label` | 331,318 | 330,682 | 330,682 | 100.00% | pass |
| `event_false_repair_20d_label` | 331,318 | 331,318 | 331,318 | 100.00% | pass |
| `event_big_winner_120d_label` | 331,318 | 330,524 | 330,524 | 100.00% | pass |

PIT 与 label 可执行性不是本次失败原因。失败原因集中在 event precision frontier 和 split stability，而不是数据泄漏、不可交易事件或标签重算偏差。

## Findings and Insight

1. C0 的真正优势是“少而早”，不是“准”。它把 R-core 的 47,914 个事件压到 28,691 个，10d duplicate 从 57.83% 降到 7.25%，low 后首触发 median 从 14 sessions 提前到 9 sessions；但 low-to-high precision 仍低于 R-core。

2. Raw recall 已经不是主要矛盾。C0 low-to-high recall 98.60%，比 R-core 97.43% 高，但这个增量只有 5 个 episode；相对地，precision 缺口是 -1.08 pct，supported threshold 缺口是 -3.08 pct。继续追求 recall 不会解决 12A3 的决策问题。

3. B5 是 coverage backbone，B1 是较高 precision 的辅助，B8 是尾部 residual。C0 的主结构应被拆成 feature family，而不是继续当 union 事件看待。

4. Multi-family trigger 没有形成强 confidence filter。`ge2` family 捕获 297 个 episode、precision 5.46%，只比 C0 高 0.14 pct，却损失 29.21 pct recall。它适合作为模型特征，不适合作为硬过滤条件。

5. Risk-on 是最有希望的 12A4 过滤方向。risk_on slice precision 6.72%，是 regime 中唯一接近 R-core 的 state-change 读数；risk_off precision 只有 2.07%，应该优先被降权或排除。

6. Missed episode 暗示要研究 state-change 的有效期，而不是扩大事件集合。6 个 C0 miss 都有同 instrument 事件，但发生在 low 前 11-44 个 sessions；这更适合用 recency/decay 特征处理。

## 12A4 建议

- 不建议：直接把 `12A2_C0_primary_canonical_union` 作为 morphology modeling 的 primary event backbone。
- 建议：进入 `requirement_12a4_filter_feasibility_or_priority_revision.md`，优先测试：
  - risk_on-only 或 regime-weighted filter；
  - B5/B1 主体 + B8 residual feature；
  - board-specific precision/false-repair tradeoff；
  - low 前最近 state-change 的 carry-forward / decay feature；
  - event density、duplicate、first-event timing 作为 feature quality gates，而不是单独的 support 依据。

## 主要产物

- `backbone_episode_recall_precision_frontier.csv`
- `backbone_event_timing_distribution.csv`
- `backbone_captured_episode_density.csv`
- `backbone_missed_episode_diagnostics.csv`
- `backbone_b8_incremental_episode_recall.csv`
- `backbone_frontier_slice_readout.csv`
- `backbone_event_label_exposure.csv`
- `state_change_label_recompute_parity_audit.csv`
- `backbone_frontier_decision.csv`

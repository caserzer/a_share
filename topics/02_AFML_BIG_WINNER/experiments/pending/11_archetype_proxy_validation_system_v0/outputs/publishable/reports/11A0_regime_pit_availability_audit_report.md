# 11A0 Regime PIT Availability Audit Report

## 1. 结论

`11A0` 的最终状态为：

```text
11A0_regime_pit_available_stable_supported
```

含义是：`risk_on` / `risk_off` / `transition` 这三个 regime bucket 在当前 08/09/10 数据链上是 t0 因果可得的；其中 `risk_on` 与 `risk_off` 在 date-level unweighted 口径下通过稳定性 hard gate；10A post-dedup R-core downstream 分母也能 100% 回连到 08/09A authority regime。因此，11A1 可以把 `analysis_event_regime_bucket` 作为 readout dimension，并允许把它作为 matched-base axis 的候选输入。

边界也很明确：11A0 不证明 regime 有 alpha，不定义买入信号，不授权 rejector override。11A1 仍必须在自己的最终 modeling denominator 上重新检查 per-slice sample power、matched-base overlap 和 payoff-risk 证据。

## 2. 输入与审计范围

本次审计读取 19 个输入 artifact，其中 18 个 required 输入全部存在，1 个 optional 输入 `candidate_family_event_instances.csv.gz` 也存在。8 个结构化输入做了 schema check，全部通过。

| 输入类别 | row/file 数量 | 审计结果 |
|---|---:|---|
| 08 canonical events | 90,576 rows | schema ok |
| 08 cross-section feature panel | 912,586 rows | schema ok |
| 08 event-episode membership | 357,450 rows | schema ok |
| 08 candidate family capture | 857,592 rows | schema ok |
| 09A selected label bindings | 41,937 rows | schema ok |
| 09A regime PIT audit | 4 rows | schema ok |
| 10A post-dedup event bindings | 200,250 rows | schema ok |
| PIT executable universe | 470,682 rows | schema ok |
| qfq primary / fallback daily files | 4,598 / 4,598 files | path exists |
| optional event instances | 238,679 rows | available |

关键解释：11A0 的主 row-level audit 以 08 canonical events 的 90,576 行为主表；10A 不是 regime authority，只用于 11A1 downstream coverage 和 slice-power check。

## 3. PIT 因果可得性

PIT 可得性没有发现缺口。

| 指标 | 数值 | 解释 |
|---|---:|---|
| event rows | 90,576 | 08 canonical event 主审计分母 |
| event vs market regime agreement | 100.00% | 08 `event_regime_bucket` 与 `market_regime_bucket` 完全一致 |
| event vs daily regime match | 100.00% | event t0 regime 与 date-level daily mode 完全一致 |
| t0 regime available rate | 100.00% | 所有事件均可在 t0 日期找到有效 regime |
| invalid / missing regime rate | 0.00% | 没有残余 missing regime |
| confirmation time ok | 90,576 / 90,576 | 全部为允许的 t0 close 可审计时点 |
| 09A PIT audit consistency | 100.00% | all/train/validation/robustness 均通过 |

regime authority 实际来源分布：

| authority source | event_n | share |
|---|---:|---:|
| 08 canonical `event_regime_bucket` | 90,576 | 100.00% |

这说明当前数据里 fallback 没有被实际使用。多层 authority chain 仍然有价值，但在本次 run 中它只是防 schema drift 的保护，不是结果来源。

## 4. 交易日历与 daily regime series

primary trading calendar 来自 `cross_section_feature_panel.date`，共 1,911 个交易日。PIT/qfq 可审计交易日集合与 primary calendar 完全一致。

| 指标 | 数值 |
|---|---:|
| primary trading dates | 1,911 |
| PIT/qfq external dates | 1,911 |
| primary-only dates | 0 |
| external-only dates | 0 |
| mismatch dates | 0 |
| mismatch rate | 0.00% |
| daily regime conflict dates | 0 |
| max daily conflict rate | 0.00% |

date-level regime 分布：

| regime | date_n | date share |
|---|---:|---:|
| risk_on | 871 | 45.58% |
| risk_off | 524 | 27.42% |
| transition | 516 | 27.00% |

这里的含义是：regime 本身是 market-wide date property，而不是 event-density property。后续 stability hard gate 因此使用 date-level unweighted 口径。

## 5. Date-Level Stability

11A0 的 hard gate 只看 `risk_on` 与 `risk_off` 的 date-level unweighted 指标。两者均通过所有门槛。

| regime | date_n | forward20 eligible | flip_end_5d | flip_end_20d | lag_not_found_20d | median age | gate |
|---|---:|---:|---:|---:|---:|---:|---|
| risk_on | 871 | 98.28% | 17.91% | 35.28% | 4.25% | 15 | pass |
| risk_off | 524 | 100.00% | 22.71% | 40.27% | 8.02% | 15 | pass |

门槛对照：

| gate | threshold | risk_on | risk_off |
|---|---:|---:|---:|
| date_n | >= 100 | 871 | 524 |
| forward_20d_eligible_rate | >= 90% | 98.28% | 100.00% |
| flip_end_5d_rate | <= 25% | 17.91% | 22.71% |
| flip_end_20d_rate | <= 45% | 35.28% | 40.27% |
| confirmation_lag_not_found_20d_rate | <= 25% | 4.25% | 8.02% |
| median_regime_age_sessions_t0 | >= 3 | 15 | 15 |

transition 按需求只作为 readout/provisional context，不进入 hard stability gate。它的读数明显更不稳定：

| regime | date_n | flip_end_5d | flip_any_5d | flip_end_20d | flip_any_20d | lag_not_found_20d | median age |
|---|---:|---:|---:|---:|---:|---:|---:|
| transition | 516 | 39.73% | 55.19% | 62.43% | 90.61% | 13.57% | 5 |

Insight：`transition` 的性质确实更像状态切换段，而不是稳定 regime。它可以用于解释和分层，但不应在 11A1 里作为 hard matched-base 轴的核心条件。

## 6. Event-Weighted Diagnostic

event-weighted 指标只用于诊断 event-density 是否扭曲 readout，不用于 hard gate。

event 分布：

| split | risk_on | risk_off | transition | total |
|---|---:|---:|---:|---:|
| train | 25,147 | 9,261 | 11,497 | 45,905 |
| validation | 6,902 | 6,047 | 9,104 | 22,053 |
| robustness | 14,424 | 3,581 | 4,613 | 22,618 |
| all | 46,473 | 18,889 | 25,214 | 90,576 |

date-level 与 event-weighted 对照：

| regime | date flip_end_20d | event-weighted flip_end_20d | date median age | event-weighted median age |
|---|---:|---:|---:|---:|
| risk_on | 35.28% | 31.94% | 15 | 13 |
| risk_off | 40.27% | 42.05% | 15 | 19 |
| transition | 62.43% | 66.93% | 5 | 4 |

Insight：event weighting 会改变读数方向和幅度。例如 risk_on 的 20d 翻转率在 event-weighted 口径下降低，而 risk_off / transition 上升。这验证了需求中的设计选择：stability 是日历属性，不应由某些高事件密度日期主导 hard gate。

## 7. Regime Age、Confidence 与 Confirmation Lag

date-level 分布显示 `risk_on` / `risk_off` 有较长的状态年龄，而 `transition` 更短。

| metric | regime | p25 | median | p75 | p95 |
|---|---|---:|---:|---:|---:|
| regime_age_sessions_t0 | risk_on | 6 | 15 | 32 | 65.5 |
| regime_age_sessions_t0 | risk_off | 5 | 15 | 33 | 90.85 |
| regime_age_sessions_t0 | transition | 2 | 5 | 9.25 | 36.25 |
| t0_regime_confidence_score | risk_on | 0.30 | 0.75 | 1.00 | 1.00 |
| t0_regime_confidence_score | risk_off | 0.25 | 0.75 | 1.00 | 1.00 |
| t0_regime_confidence_score | transition | 0.10 | 0.25 | 0.46 | 1.00 |
| ex_post_regime_stability_score_20d | risk_on | 0.55 | 0.90 | 1.00 | 1.00 |
| ex_post_regime_stability_score_20d | risk_off | 0.45 | 0.85 | 1.00 | 1.00 |
| ex_post_regime_stability_score_20d | transition | 0.25 | 0.50 | 0.80 | 1.00 |

confirmation lag 的 median 均为 0，说明大多数日期从 t0 开始就能看到连续 3 session 同 regime。但 p95 上，transition 为 9 session，高于 risk_on / risk_off 的 4 session。

Insight：如果后续 11A1 需要更保守的 regime readout，可以把 `t0_regime_confidence_score` 分层使用。例如 `risk_on/risk_off` 中 confidence 较低的日期仍可单独打标为 low-confidence context；但这应该是 readout 分层，不应回改 11A0 的 PIT availability。

## 8. 10A Downstream Coverage 与 Slice Power

10A downstream check 使用 post-dedup R-core admitted population。该 downstream scope 当前只有 `risk_on`，这是预期的，因为 10A 主分母是 risk-on R-core。

| 指标 | 数值 |
|---|---:|
| 10A downstream rows | 15,802 |
| key parse success rate | 100.00% |
| 10A -> 08 match rate | 100.00% |
| 10A regime field agreement readout-only | 100.00% |
| authority regime coverage for 11A1 | 100.00% |
| key parse conflict n | 0 |
| key parse failed n | 0 |

10A slice-power：

| regime | ten_a_event_n | train | validation | robustness | authority coverage | slice power |
|---|---:|---:|---:|---:|---:|---|
| risk_on | 15,802 | 8,318 | 2,514 | 4,970 | 100.00% | pass |
| risk_off | 0 | 0 | 0 | 0 | n/a | fail / not in scope |
| transition | 0 | 0 | 0 | 0 | n/a | fail / not in scope |

Insight：11A1 的默认 R-core risk_on denominator 可以安全读取 regime context，并且 downstream coverage 没有 join 缺口。但这不等于 11A1 的每一个 proxy-positive / proxy-negative matched cell 都有足够样本。11A1 必须在最终 proxy membership 形成后重新检查 per-slice n 和 matched-base overlap。

## 9. Join Coverage 与 Episode Regime Readout

event-level regime authority 不依赖 09A 或 episode join；它由 08 canonical event 完整提供。其他 join 的用途是 readout 和 reconciliation。

| join | left rows | matched rows | match rate | duplicate key count | conflict count | 用途 |
|---|---:|---:|---:|---:|---:|---|
| 08 canonical -> 09A selected bindings | 90,576 | 30,798 | 34.00% | 9,252 | 9,252 | 非阻塞；09A 是 label-frontier selection |
| 08 canonical -> 08 membership | 90,576 | 17,714 | 19.56% | 334,776 | 0 | episode readout only |
| 08 membership -> 08 capture | 17,714 | 17,714 | 100.00% | 855,099 | 4,937 | episode readout only |

episode/event divergence：

| event regime | event_n | membership_match_n | capture_match_n | divergence_n | divergence_rate |
|---|---:|---:|---:|---:|---:|
| risk_on | 46,473 | 12,208 | 12,208 | 10,009 | 21.54% |
| risk_off | 18,889 | 0 | 0 | 0 | 0.00% |
| transition | 25,214 | 5,506 | 5,506 | 4,429 | 17.57% |
| all | 90,576 | 17,714 | 17,714 | 14,438 | 15.94% |

Insight：episode regime 不适合作为 11A1 的主 authority。它覆盖的是 episode-linked 子集，并且与 event regime 存在明显 divergence。11A1 如需使用 episode regime，只应作为附加 readout，而不是主 matched-base axis。

## 10. Event Regime Gating Diagnostic

`event_regime_gating` 被纳入 readout，但不改变 regime authority。

| view | event_n | gated_event_count | gated_event_share |
|---|---:|---:|---:|
| all | 90,576 | 5,031 | 5.55% |
| train | 45,905 | 2,381 | 5.19% |
| validation | 22,053 | 1,478 | 6.70% |
| robustness | 22,618 | 1,172 | 5.18% |

按 regime 看：

| regime | event_n | gated_event_count | gated_event_share |
|---|---:|---:|---:|
| risk_on | 46,473 | 1,461 | 3.14% |
| risk_off | 18,889 | 0 | 0.00% |
| transition | 25,214 | 3,570 | 14.16% |

Insight：gated events 明显集中在 transition。后续若研究 transition 或 early-path causality，`event_regime_gating` 是值得单独读出的结构变量；但它不应反向修改 event-level regime，也不应在 11A1 中被当成 payoff proxy。

## 11. Downstream Usage Decision

| usage target | allowed | scope | 说明 |
|---|---|---|---|
| 11A1_proxy_readout | true | primary | 可作为 regime-sliced readout dimension |
| 11A1_matched_base_axis | true | primary | 11A0 允许该 axis；11A1 必须重检 slice power |
| 11B_retention_readout | true | diagnostic_only | 可做 retention context |
| 11C_policy_context | true | diagnostic_only | 只能作为后续 policy requirement 的 context |

最终建议：

1. 11A1 可以默认读取 11A0 的 `analysis_event_regime_bucket`，并优先在 risk_on downstream scope 内使用。
2. `risk_on/risk_off` 的 PIT 与 stability 证据足够支持 readout；`transition` 保持 provisional/readout-only。
3. 不要把 11A0 的 `stable_supported` 写成“regime 有 alpha”或“regime 可交易”。它只是证明 regime 作为上下文变量足够干净。
4. 11A1 的关键风险不在 regime 可得性，而在 proxy-positive cell 的样本量、matched-base overlap 和 payoff-risk 是否稳定。

## 12. 总体 Findings

- Finding 1：当前 regime source 很干净。08 canonical event、market bucket、daily mode 三者 100% 对齐，残余 missing 为 0。
- Finding 2：risk_on / risk_off 的 date-level stability 通过 hard gate，且 median age 都是 15 sessions，说明它们不是瞬时噪声标签。
- Finding 3：transition 的 flip rate 和 confidence 明显弱于 risk_on/risk_off，应继续作为 readout/provisional context，不应直接作为 hard policy context。
- Finding 4：10A R-core downstream 是 risk_on-only，但 15,802 行全部可回连到 authority regime，key parse / join / agreement 全部 100%。
- Finding 5：event-weighted 口径会改变稳定性读数，因此不能用 event rows 直接校准 regime stability gate。
- Finding 6：episode regime 覆盖子集较窄且 divergence 明显，不能替代 event-level t0 regime authority。

## 13. 解释边界

本报告只回答 regime 是否 PIT available、是否 date-level stable、是否能供 11A1 downstream 使用。它不回答 proxy 是否有效，不回答 payoff 是否改善，不回答策略 EV，也不允许覆盖 10C rejector 或 10D safe repair 约束。

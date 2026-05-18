# EP4 R04 Dynamic Momentum Exposure Eligibility Audit V1 最终报告

## 1. 结论摘要

本次 R04 v1 的最终结论是：

```text
Final decision: r04_v1_exposure_eligibility_audit_complete_descriptive_only
```

这不是一个可以进入生产的 exposure gate，也不支持继续直接进入 `R04 v2 volume_money / volatility / extension`。更准确的解释是：

```text
single_momentum_rps 仍然包含上行尾部信息；
但 RPS + market + industry 这条 exposure eligibility 路线没有证明稳定的 OOS action-time 增量；
表面改善主要被 denominator shrink、split 不稳定、background regime effect 和 cell 稀疏性挡住。
```

R04 的验证状态是通过的：

| item | value |
|:--|:--|
| validation_status | passed |
| validator_checks | 66 |
| spec_sheet_hash | 5ca0b22ef1006550f98de9b372bf4115b1a553197900ec3be1da63f9a96effcc |
| train_q67_market_realized_vol_60d | 0.2244945069 |
| RPS candidate rows | 16,582 |
| RPS included rows | 12,973 |
| background rows | 1,101,821 |
| background included rows | 305,902 |

本报告只解释 R04 v1 的固定范围：

```text
baseline_A: single_momentum_rps episode-first-trigger candidate pool
baseline_B: RPS + market regime
baseline_C: RPS + market regime + industry regime
```

以下内容仍然不属于 R04 v1：`volume_money`、stock volatility / ATR gate、price extension、risk-budget sizing、CTA / trailing exit、fresh sequence、family order、bad-shape repair。

`ev_r_status = out_of_scope_for_r04_v1`
`big_winner_status = proxy_only`

Validator marker: No production gate, position size, or CTA exit rule is emitted by this audit. `post_drawdown_rebound_hypothesis` and `industry_rebound_from_drawdown` are hypotheses, not default bad gates.

---

## 2. 实验边界与读数方法

R04 v1 的核心问题不是“再找一个更强 entry anchor”，而是：

```text
在冻结的 single_momentum_rps candidate pool 上，
market regime 与 industry regime 是否能解释 action-time forward path 的条件差异？
```

本次所有 headline 结论都使用 action-time / next-open anchor：

```text
anchor_signal_date = episode_start_signal_date 或 background trade_date
entry_execution_date = next tradable open after anchor_signal_date
forward path = from entry_execution_date
primary_metric = plus10_before_minus5_rate
```

`same_offset` 和 `censored_incomplete` 不进入 primary metric denominator，而是单独进入 race ambiguity audit。因此，任何表里的 `metric_denominator` 都小于 path-complete denominator。

本报告中：

- `plus10_before_minus5_rate` 是主指标；
- `bad_path_rate`、`early_failure_rate` 是路径风险约束；
- `max_gain50_proxy_rate` 和 `max_gain_120d_p90` 只作为上行尾部 proxy，不是 canonical big-winner label；
- `matching_background_rate` 是同 split、同 regime cell、按 RPS cell weight 加权后的 background comparator；
- `all` split 只作描述，不用于 pass/fail。

---

## 3. 输入、spec 与验证

所有必需输入均存在，R02 path-query validation 为 `passed`。R04 也通过了背景 path label reconciliation：

| split | sampled_row_count | mismatch_row_count | total_mismatch_count | status |
|:--|--:|--:|--:|:--|
| train | 500 | 0 | 0 | passed |
| validation | 500 | 0 | 0 | passed |
| robustness | 500 | 0 | 0 | passed |

行业归属 join 审计：

| denominator_scope | split | missing membership count | missing rate |
|:--|:--|--:|--:|
| rps_episode_primary | train | 0 | 0.00% |
| rps_episode_primary | validation | 0 | 0.00% |
| rps_episode_primary | robustness | 0 | 0.00% |
| background_action_time | train | 257,774 | 47.01% |
| background_action_time | validation | 45,683 | 17.84% |
| background_action_time | robustness | 33,184 | 12.93% |

解释：RPS candidate 的行业归属完整；background stock-day denominator 的早期样本存在较多 missing industry，因此 industry comparator 在部分 cell 上会更容易触发 insufficient background denominator。这个限制不影响 RPS headline baseline，但会影响 market x industry cell 的可解释性。

---

## 4. Candidate Funnel 与 Raw-vs-Episode 审计

R04 使用 episode-first-trigger grain，而不是 raw repeated-trigger grain。

| split | included | excluded_incomplete_120d_path | excluded_missing_required_field | excluded_duplicate_episode |
|:--|--:|--:|--:|--:|
| train | 6,656 | 1,578 | 11 | 0 |
| validation | 3,453 | 669 | 8 | 0 |
| robustness | 2,864 | 1,322 | 21 | 0 |
| all | 12,973 | 3,569 | 40 | 0 |

Raw trigger 与 episode-first-trigger 的压缩关系如下：

| split | raw rows | episode rows | compression | repeated rows | raw metric | episode metric | delta |
|:--|--:|--:|:--|--:|--:|--:|--:|
| train | 22,272 | 8,245 | 2.70x | 14,027 | 37.29% | 38.06% | -0.76% |
| validation | 10,919 | 4,130 | 2.64x | 6,789 | 31.00% | 31.57% | -0.57% |
| robustness | 10,929 | 4,207 | 2.60x | 6,722 | 35.04% | 35.77% | -0.73% |
| all | 44,120 | 16,582 | 2.66x | 27,538 | 35.12% | 35.82% | -0.70% |

发现：

1. raw repeated-trigger 很多，约 61%-63% raw rows 是 episode 内重复触发。
2. raw metric 比 episode-first-trigger 低约 0.6-0.8 pct，说明 repeated-trigger 没有带来更好的 action-time edge。
3. 使用 episode-first-trigger 是必要的，否则会把同一个动量 episode 的后续重复信号当成多个独立机会。

---

## 5. Requirement 七个问题的直接回答

### Q1. `single_momentum_rps` episode-first-trigger candidate pool 的 action-time baseline outcome 是什么？

Baseline A 的 OOS 结果如下：

| split | metric_denominator | plus10_before_minus5_rate | matching_background_rate | lift_vs_background | bad_path_rate | early_failure_rate | max_gain50_proxy_rate | max_gain_120d_p90 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| validation | 3,453 | 31.57% | 33.09% | -1.52% | 68.23% | 52.97% | 7.41% | 43.67% |
| robustness | 2,863 | 35.77% | 40.25% | -4.49% | 56.37% | 45.93% | 13.55% | 57.34% |

结论：

```text
single_momentum_rps 不是可复用 action-time entry edge。
```

它在 validation 和 robustness 都低于 matching background comparator。更重要的是，bad path 很重：validation bad_path_rate 68.23%，robustness 56.37%。这说明 RPS 不是“买入即有边际优势”的 entry anchor。

但它也不是完全无信息。`max_gain50_proxy_rate` 在 validation / robustness 分别为 7.41% / 13.55%，`max_gain_120d_p90` 分别为 43.67% / 57.34%。这说明 RPS pool 仍有上行尾部，问题是 action-time entry path 风险太重，而不是完全没有 winner potential。

### Q2. 预注册 market regime bucket 是否在 OOS 中稳定区分 path quality？

Market bucket 的 OOS 结果如下：

| split | market_regime_bucket | denom | plus10_before_minus5_rate | lift_vs_A | background_rate | lift_vs_background | bad_path_rate | max_gain50_proxy_rate | status |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|:--|
| validation | downtrend_low_breadth | 351 | 37.61% | +6.04% | 31.05% | +6.55% | 64.67% | 16.81% | sufficient |
| validation | missing_market_regime | 2,411 | 33.60% | +2.03% | 35.95% | -2.35% | 65.24% | 6.35% | sufficient |
| validation | normal_range | 65 | 18.46% | -13.11% | 11.05% | +7.41% | 76.92% | 6.15% | insufficient_rps_denominator |
| validation | normal_uptrend | 626 | 21.73% | -9.84% | 25.72% | -3.99% | 80.83% | 6.39% | sufficient |
| robustness | downtrend_low_breadth | 200 | 52.00% | +16.23% | 50.18% | +1.82% | 47.00% | 8.00% | sufficient |
| robustness | missing_market_regime | 1,476 | 34.01% | -1.76% | 40.64% | -6.63% | 58.74% | 16.26% | sufficient |
| robustness | normal_range | 144 | 65.28% | +29.51% | 65.24% | +0.04% | 32.64% | 15.28% | sufficient |
| robustness | normal_uptrend | 1,043 | 31.06% | -4.70% | 33.76% | -2.70% | 58.10% | 10.55% | sufficient |

结论：

```text
market regime 有解释力，但没有形成可冻结的 RPS 增量 gate。
```

最重要的发现有三点：

1. `normal_uptrend` 并不自然等于好状态。它在 validation / robustness 都低于 RPS baseline，也低于 matching background。
2. `normal_range` 在 robustness 很强，但 validation denominator 只有 65 且表现很差，不能作为 OOS 稳定结论。
3. `downtrend_low_breadth` 反而在两个 OOS split 都方向较好，但 robustness 的 lift_vs_background 只有 +1.82%，说明这里至少有一部分是 market regime 自身的 background effect，不是 RPS 的独立增量。

这直接回应 discussion4：market regime 是必要 context，但第一版 bucket 不能被升级成暴露资格规则。

### Q3. 预注册 industry regime bucket 是否在 RPS + market parent 下提供增量？

核心 pre-registered mask 是：

```text
mask_C_industry_leadership =
  market constructive
  AND industry_regime_bucket in {industry_leading, industry_rebound_from_drawdown}
```

其 OOS 结果如下：

| split | denom | plus10_before_minus5_rate | lift_vs_parent | background_status | denominator_status | bad_path_rate | race_ambiguous_rate | max_gain50_proxy_rate | max_gain50_retention |
|:--|--:|--:|--:|:--|:--|--:|--:|--:|--:|
| validation | 95 | 11.58% | -9.84% | insufficient_background_denominator | insufficient_rps_denominator | 78.95% | 41.36% | 0.00% | 0.00% |
| robustness | 235 | 38.72% | +3.51% | insufficient_background_denominator | sufficient | 45.96% | 18.97% | 8.94% | 80.36% |

结论：

```text
industry leadership 没有在 RPS + market parent 下提供稳定 OOS 增量。
```

validation 是直接失败：denom 只有 95，primary metric 只有 11.58%，bad_path_rate 78.95%，max_gain50_proxy_rate 为 0。robustness 虽然 primary metric 有 +3.51 pct lift，但 background comparator insufficient，且 denominator shrink 达 80.20%。这不是可升级的 exposure eligibility 证据。

Industry-only 的 OOS 结果也不支持稳定增量：

| split | industry bucket | denom | plus10_before_minus5_rate | lift_vs_A | matching_background_rate | lift_vs_background | bad_path_rate | max_gain50_proxy_rate |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|
| validation | industry_leading | 383 | 28.98% | -2.59% | 28.62% | +0.36% | 65.54% | 1.83% |
| validation | industry_rebound_from_drawdown | 86 | 26.74% | -4.82% | 29.56% | -2.81% | 68.60% | 8.14% |
| robustness | industry_leading | 456 | 39.69% | +3.93% | 48.14% | -8.45% | 46.93% | 8.99% |
| robustness | industry_rebound_from_drawdown | 64 | 39.06% | +3.30% | 42.99% | -3.92% | 39.06% | 23.44% |
| robustness | industry_lagging | 361 | 39.06% | +3.29% | 40.36% | -1.30% | 50.42% | 26.32% |

`industry_leading` 在 robustness 看起来更好，但它低于 matching background 8.45 pct；这说明行业状态本身已经解释了相当多的收益，RPS 没有证明额外贡献。

### Q4. market-only / industry-only 在 full background denominator 上是否已经有同等解释力？

是的，很多表面效果已经能在 full background stock-day denominator 中看到。

Market-only background OOS：

| split | market_regime_bucket | background denom | background plus10_before_minus5_rate | lift_vs_background_all | bad_path_rate | max_gain50_proxy_rate |
|:--|:--|--:|--:|--:|--:|--:|
| validation | downtrend_low_breadth | 8,212 | 31.05% | -2.04% | 60.87% | 11.34% |
| validation | missing_market_regime | 56,462 | 35.95% | +2.86% | 53.92% | 5.62% |
| validation | normal_range | 1,774 | 11.05% | -22.04% | 82.64% | 8.85% |
| validation | normal_uptrend | 14,343 | 25.72% | -7.37% | 70.02% | 4.16% |
| robustness | downtrend_low_breadth | 5,610 | 50.18% | +9.92% | 43.71% | 7.83% |
| robustness | missing_market_regime | 40,153 | 40.64% | +0.39% | 40.19% | 10.85% |
| robustness | normal_range | 4,151 | 65.24% | +24.98% | 29.17% | 19.13% |
| robustness | normal_uptrend | 26,959 | 33.76% | -6.49% | 48.92% | 12.99% |

这说明：

```text
market regime 本身已经强烈影响 full background path；
RPS + market 的结果不能直接解释为 RPS 增量。
```

特别是 robustness 的 `normal_range`，RPS bucket 是 65.28%，background bucket 是 65.24%，几乎没有 RPS 增量。这是一个很清楚的 negative ablation 结果。

Industry-only 也类似。`industry_leading` robustness 的 RPS rate 是 39.69%，但 matching background 是 48.14%；`industry_neutral` robustness 的 RPS rate 是 35.69%，matching background 是 44.54%。这些都说明 industry bucket 更像 regime/context，而不是在 RPS 之上提供稳定 alpha。

### Q5. 表面改善是否只是 denominator shrink、年份集中、行业集中或 split drift？

很大程度上是。

核心 mask 的 denominator shrink：

| mask | split | metric_denominator | shrink_vs_parent | race_ambiguity | max_gain50_retention |
|:--|:--|--:|--:|--:|--:|
| market_non_missing | validation | 1,042 | 69.82% | 28.34% | 133.33% |
| market_non_missing | robustness | 1,387 | 51.55% | 12.55% | 78.74% |
| market_constructive | validation | 691 | 79.99% | 32.72% | 85.89% |
| market_constructive | robustness | 1,187 | 58.54% | 14.30% | 82.06% |
| industry_leadership | validation | 95 | 86.25% | 41.36% | 0.00% |
| industry_leadership | robustness | 235 | 80.20% | 18.97% | 80.36% |

年份/行业/个股集中：

| split | group | metric_denominator | top1_year_share | top1_industry_share | top1_instrument_share | top5_instrument_share | warning |
|:--|:--|--:|--:|--:|--:|--:|:--|
| validation | baseline_A_rps_only | 3,453 | 67.19% | 8.77% | 0.84% | 4.11% | True |
| robustness | baseline_A_rps_only | 2,863 | 68.49% | 12.61% | 1.01% | 4.68% | True |

baseline_A 已经有明显 year concentration。market x industry cell 更严重：许多 robustness cell 的 top1_year_share 是 100%，并且若干小 cell 的 top1_industry_share 超过 40%-70%。因此，任何小 cell 的高 primary metric 都不能被解释为稳定规律。

结论：

```text
R04 v1 的主要改善信号没有通过 denominator / concentration / split stability 审计。
```

### Q6. `post_drawdown_rebound` 对 A-share long-only momentum 是风险状态还是机会状态？

本次 R04 v1 不能回答它是风险还是机会，因为 frozen spec 下没有形成该 bucket 的有效样本：

```text
r04_post_drawdown_rebound_audit.csv is empty
post_drawdown_rebound_hypothesis rows: 0
panic_high_vol rows: 0
```

这不是“post-drawdown rebound 无风险”，也不是“post-drawdown rebound 有机会”。只能说明：

```text
在当前 local market proxy、cutpoint 和 R02 eligible universe 下，
market_ret_60d <= -10%、market_ret_20d >= +5%、vol60 >= train_q67
这个组合没有落入可报告的 candidate bucket。
```

discussion4 中对 momentum crash 的迁移边界仍然成立：A-share long-only 不能机械照搬 long-short WML crash 结论。后续若要测试这个问题，必须新开 R04.1 / R04v2 requirement，降低或重写 rebound state 的定义，并在 outcome 前冻结；不能用本次结果事后改断点。

### Q7. 如果 RPS + market + industry 没有 OOS 增量，是否应停止 exposure eligibility 路线并转向 hold / exit / risk-budget diagnostics？

本次 final decision 是 descriptive-only，原因是 mask_C 的 denominator 和 matching background comparator 不满足 proceed 条件。

但从研究方向上，我的判断是：

```text
不应继续把 R04 v2 写成“在 RPS + market + industry 之后继续叠 volume_money / volatility / extension gate”。
```

理由：

1. baseline_A 本身低于 background；
2. market bucket 有解释力，但不少效果来自 background market regime；
3. industry leadership 没有提供稳定 OOS 增量；
4. mask_C validation 直接失败；
5. mask_C robustness 的正向结果被 denominator shrink 和 comparator insufficiency 挡住；
6. baseline_A 仍然有上行尾部，说明更值得测试的是持有、退出、风险预算，而不是继续寻找 action-time eligibility。

因此，下一步更合理的是：

```text
R04b_hold_exit_only / risk-budget diagnostics:
  固定 RPS candidate pool；
  不再声称 new entry / exposure eligibility；
  测试如何保留右尾、降低 bad path、控制 early failure。
```

---

## 6. Discussion4 的关键假设逐条回应

### 6.1 “RPS / momentum 是方向选择器，不是 entry trigger”

本次结果支持这句话。

RPS baseline 的 OOS primary metric 低于 background：

| split | RPS baseline | background comparator | lift |
|:--|--:|--:|--:|
| validation | 31.57% | 33.09% | -1.52% |
| robustness | 35.77% | 40.25% | -4.49% |

但 RPS baseline 的上行尾部仍然存在：

| split | max_gain50_proxy_rate | max_gain_120d_p90 |
|:--|--:|--:|
| validation | 7.41% | 43.67% |
| robustness | 13.55% | 57.34% |

解释：RPS 更像“有右尾的候选池生成器”，不是“action-time 买入锚点”。

### 6.2 “Market regime 决定 momentum exposure 是否值得承担”

方向上支持，但不能形成 gate。

Market bucket 明显改变 path distribution，例如 robustness:

- `normal_range`: 65.28%，但 background 同 bucket 是 65.24%，RPS 几乎没有增量；
- `downtrend_low_breadth`: 52.00%，background 是 50.18%，RPS 增量只有 +1.82%；
- `normal_uptrend`: 31.06%，低于 background 33.76%。

这说明 market regime 是状态变量，但不能直接写成 RPS exposure eligibility。

### 6.3 “Industry regime 判断 momentum 是否有 leadership 支撑”

本次不支持 first-version 的 industry leadership 定义。

`industry_leading` 在 validation 低于 baseline，在 robustness 虽然高于 baseline，但低于 background：

| split | RPS industry_leading | baseline_A | matching_background | interpretation |
|:--|--:|--:|--:|:--|
| validation | 28.98% | 31.57% | 28.62% | 无增量 |
| robustness | 39.69% | 35.77% | 48.14% | 行业背景强于 RPS |

这说明行业 leadership 可能有解释力，但当前 bucket 没有证明“RPS + industry leadership”比行业状态本身更好。

### 6.4 “Volume_money / volatility / extension 应延后”

本次结果支持延后，而且比 discussion4 更严格：

```text
因为 RPS + market + industry 都未通过，
不应在当前证据上继续叠加 volume_money / volatility / extension。
```

否则容易重新落入 R02/R03 已经暴露的问题：高维 same-day composite、late confirmation、denominator shrink 和 crowded point 追高。

### 6.5 “CTA / trailing exit 应作为独立 hold / exit 层”

本次结果支持把 CTA 放到独立 R04b，而不是混入 exposure eligibility。

RPS pool 的问题不是没有右尾，而是 entry path 风险重：

- validation bad_path_rate 68.23%；
- robustness bad_path_rate 56.37%；
- validation early_failure_rate 52.97%；
- robustness early_failure_rate 45.93%。

这更像 holding / exit / risk-budget 问题，而不是继续找另一个 entry filter。

---

## 7. 更细的发现与洞察

### 7.1 “Constructive market” 这个先验没有通过

pre-registered constructive mask 包含：

```text
normal_uptrend
normal_range
post_drawdown_rebound_hypothesis
```

但 OOS 结果是：

| split | mask_B_constructive denom | primary metric | lift_vs_A | bad_path_rate | max_gain50_proxy_rate |
|:--|--:|--:|--:|--:|--:|
| validation | 691 | 21.42% | -10.15% | 80.46% | 6.37% |
| robustness | 1,187 | 35.21% | -0.55% | 55.01% | 11.12% |

这说明“normal_uptrend / normal_range 就更适合做 momentum”的先验过于粗。至少在本次数据中，validation 的 constructive mask 明显更差。

### 7.2 `normal_range` 的 robustness 高收益主要是 market regime 本身

robustness 中 `normal_range`：

| denominator | plus10_before_minus5_rate |
|:--|--:|
| RPS + normal_range | 65.28% |
| full background + normal_range | 65.24% |

这个 cell 看起来很强，但 RPS 几乎没有增量。它更像一个 market state 的收益分布，而不是 RPS 条件化后的 alpha。

### 7.3 `industry_lagging` 反而有右尾，但不稳定

Industry-only robustness 中 `industry_lagging`：

| split | denom | primary metric | max_gain50_proxy_rate | max_gain_120d_p90 |
|:--|--:|--:|--:|--:|
| validation | 595 | 28.74% | 5.88% | 39.78% |
| robustness | 361 | 39.06% | 26.32% | 88.50% |

这个现象不应被写成“lagging industry 更好”。更合理的猜测是：robustness 某些年份/行业里，落后行业中的少数 RPS stock 可能包含反转或补涨右尾；但 validation 不支持，且 concentration warning 很重。它最多是后续 descriptive lead，不是 gate。

### 7.4 Race ambiguity 是一个严重问题

mask_C validation 的 race_ambiguous_rate 达到 41.36%，market constructive validation 也有 32.72%。这说明筛选后留下的很多样本并不是清晰的 `+10 before -5` 或 `-5 before +10`，而是 same-offset / censored-incomplete。对于一个 exposure eligibility gate，这种 ambiguity 太高。

换句话说，即使 primary metric 看起来有提升，也必须先问：

```text
这个提升是不是来自少量可判定样本？
被排除的 ambiguous path 是否已经说明路径质量不可交易？
```

本次 mask_C 没有过这个关。

### 7.5 Background denominator 的高 ambiguity 限制了 comparator 解释

Background denominator 的 race ambiguity 很高：

| denominator | validation ambiguity | robustness ambiguity |
|:--|--:|--:|
| background_all | 67.24% | 68.47% |
| background_market_constructive | 79.20% | 69.45% |

这意味着 background comparator 虽然是必要控制，但可判定 metric denominator 是严格筛过的。报告中不能把 background rate 当成“全市场 raw 胜率”，它只是同一 null policy 下的可判定 path rate。

---

## 8. Kill Criteria 审计

R04 的 kill criteria 全部阻止 proceed：

| criteria_id | status | key details |
|:--|:--|:--|
| mask_C_hard_constraints_validation | failed | lift_vs_parent -9.84 pct；bad_path_rate 增加 10.72 pct；max_gain50_retention 0；denominator shrink 86.25%；race ambiguity 41.36% |
| mask_C_hard_constraints_robustness | failed | lift_vs_parent +3.51 pct；bad_path_rate 下降 10.42 pct；但 denominator shrink 80.20%，background comparator insufficient |
| denominator_or_matching_background_sufficiency | failed | insufficient denominator or comparator |

这说明不能使用 robustness 的正向 mask_C 结果来推进 R04 v2。validation 已失败，robustness 又无法通过 comparator / shrink 约束。

---

## 9. 对后续研究的建议

### 9.1 不建议继续推进的方向

不建议直接进入：

```text
RPS + market + industry + volume_money
RPS + market + industry + volatility
RPS + market + industry + extension
```

原因是三层结构都没有通过。继续叠更多字段，会高度可能变成：

```text
denominator 更小；
年份/行业更集中；
高维同日 composite；
对 crowded / overextended 状态重复惩罚；
看起来改善，但不可复用。
```

### 9.2 可以保留为后续线索的方向

如果继续研究，建议改成两个更窄的问题。

第一，`R04b_hold_exit_only`：

```text
固定 single_momentum_rps candidate pool；
不再寻找 exposure eligibility；
测试如何保留 max_gain50 / p90 右尾，同时降低 bad_path / early_failure。
```

理由：RPS baseline 有右尾，但 action-time path 很差。这是 hold / exit / risk budget 更自然的应用场景。

第二，`market regime descriptive v2`：

```text
不做 gate；
只重新审计 market state 的 path distribution；
尤其是 downtrend_low_breadth、normal_range、post_drawdown_rebound_hypothesis 的定义。
```

理由：market state 有解释力，但本次 post_drawdown_rebound 没有样本，normal_range 的 robustness 效果又几乎完全由 background 解释。

### 9.3 如果未来重启 R04 v2，必须先修正的问题

未来版本如果要引入 volume_money / volatility / extension，必须先做：

1. overlap audit：volume_money、extension、volatility expansion 是否只是同一个 crowded state；
2. denominator shrink audit：每个新增 gate 单独造成多少样本损失；
3. winner retention audit：max_gain50_proxy / canonical big-winner 是否被过度丢弃；
4. same-split background comparator：不能用 global background average；
5. OOS cell sufficiency：validation 和 robustness 都必须过最低 denominator；
6. post_drawdown_rebound 重新定义前必须冻结新 spec，不能回填本次 R04。

---

## 10. 最终判断

本次 R04 v1 的核心结论是：

```text
RPS/momentum 有右尾，但不是 action-time entry edge；
market regime 有解释力，但很多效果来自 background regime；
industry regime 没有在 RPS + market parent 下提供稳定 OOS 增量；
market + industry 的表面改善被 denominator shrink、cell 稀疏、race ambiguity 和 split drift 阻断；
post_drawdown_rebound 在本次 frozen spec 下没有可回答样本；
不应输出 production gate、position size、CTA exit rule。
```

这和 discussion4 的方向基本一致，但结论更收紧：

```text
不要再问“哪个 anchor 最强”；
也暂时不要继续叠加更多 exposure eligibility 条件；
当前最有价值的问题是：
  如何在已有 RPS 右尾中管理持有、退出和风险预算。
```

因此，R04 v1 只应作为诊断型研究完成，不应升级为交易规则。

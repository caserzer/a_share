# EP4 Discussion 3: R02 Path Diagnostics, Same-Day Evidence Bundles, and 1R Build Budget

> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 R03 validation。
>
> 背景：基于 `discussion2.md` 的 evidence accumulation 思路，以及 `requirement_02_family_signal_120d_path_query_v1.md` 产出的 120D path diagnostics。本文记录当前对 11 个 family / review composite 信号的诊断发现，并讨论如何把这些信号从 same-day entry trigger 改写为 R03 的分阶段 evidence / risk-budget 结构。

---

## 1. 当前数据诊断结论

R02 path query 对 7 个 single family 和 4 个 review composite 计算了 next-open entry 后 120 个交易日内的路径表现。核心发现是：

```text
这些信号普遍有后续上冲能力，
但原始触发日不是干净的可执行 entry 点。
```

在 episode-first-trigger 粒度下，整体表现呈现以下特征：

```text
+10% hit rate roughly = 65.8% .. 70.2%
+10% before -5% roughly = 32.9% .. 33.9%
T20 / T60 / T120 median return mostly <= 0
severe drawdown rate roughly = 66.5% .. 81.9%
```

这说明信号不是没有信息量。问题在于路径顺序：

```text
很多样本先触发 -5% / early failure，
之后才出现 +10% / +20% 的上冲机会。
```

因此，当前信号更适合被解释为：

```text
candidate state / evidence family / probe context
```

而不是：

```text
full-size entry trigger
```

---

## 2. Single Family 的相对排序

按 early failure、drawdown、median return 和 tradable continuation 综合看，当前更适合作为 R03 初始候选的 single family 是：

```text
single_range_breakout
single_volume_money
single_oscillator
```

这些 family 的共同特征：

```text
early_failure_rate lower than momentum / price-trend style signals
max_drawdown_120d_p50 less severe
T120 median return closer to zero or slightly better
```

但即使这些相对更稳的 family，也不能直接给完整 1R。它们只能支持 small probe 或 build-window 的初始候选状态。

相对更像 winner-capture evidence 的 family 是：

```text
single_momentum_rps
single_price_trend
single_pullback_drawdown
```

它们通常有更高的 upside / MFE，但也伴随更高 early failure 和更重 drawdown。它们更适合在 survival 后作为加仓或 continuation evidence，而不是裸 entry。

---

## 3. 为什么 Review Composite 的 Early Failure 反而更高

4 个 review composite 都是 same-day AND：

```text
同一 instrument + signal_date 上，
多个 family 同时满足条件。
```

当前诊断显示，同日触发的 single family 数越多，early failure 越高：

| same-day single family count | early_failure_rate | T20 median | MAE20 median | first -5% offset median |
|---:|---:|---:|---:|---:|
| 1 | 38.6% | -0.41% | -5.32% | 11 |
| 2 | 42.6% | -0.48% | -5.84% | 9 |
| 3 | 45.6% | -0.64% | -6.32% | 8 |
| 4 | 50.4% | -0.79% | -6.98% | 7 |
| 5 | 54.1% | -1.19% | -7.85% | 6 |
| 6 | 55.3% | -1.59% | -7.90% | 6 |

这说明 same-day confluence 不等价于更高质量的 entry。它更可能是在筛选：

```text
短期已经很热
多个强势/量能/震荡指标同时过阈值
entry next open 已经接近局部拥挤点
```

所以 review composite 的问题不是 family 信息无效，而是组合方式错了：

```text
same-day AND 把多个相关证据压缩成一个 entry trigger，
没有等待 survival，也没有区分新信息和重复信息。
```

---

## 4. Component Conditional Diagnostics

把 single family 分成 `member_on_composite_day` 和 `member_not_composite_day` 后，可以看到组合日样本明显更差。

典型例子：

```text
single_volume_money:
  non-composite day early failure roughly = 38% .. 39%
  composite day early failure roughly = 50% .. 52%

single_oscillator:
  non-composite day early failure roughly = 41% .. 42%
  composite day early failure roughly = 50% .. 52%

single_range_breakout:
  non-composite day early failure roughly = 41%
  composite day early failure roughly = 51%
```

这说明 composite day 改变了样本分布。多个 family 同日共振时，它们不是提供了多个独立证据，而是共同指向同一个短期过热状态。

---

## 5. Same-Day Evidence Bundle 的概率计算方式

同日触发时，不应该把分项概率相乘。

错误形式：

```text
P(good | A and B and C) ~= P(good | A) * P(good | B) * P(good | C)
```

原因是 family 之间高度相关。R02 precision 产物显示 top4 family 的相关性较高：

```text
combo_max_abs_phi ~= 0.7396
combo_max_jaccard ~= 0.6205
```

正确形式是把同日触发看成一个 evidence bundle：

```text
E_t = {
  volume_money = 1,
  oscillator = 1,
  range_breakout = 1,
  momentum_rps = 0,
  ...
}
```

然后直接估计：

```text
P(good_path | E_t, context)
P(early_failure | E_t, context)
EV_R(E_t, context)
```

这里的 `context` 至少应包含：

```text
split / year / market regime
same-day family count
recent return / extension state
initial risk pct
liquidity / volume state
```

同日 bundle 只能决定初始 probe cap，不能因为有多个同日 family 就释放多个 risk units。

---

## 6. 分项概率如何保留解释价值

虽然同日触发不能相乘，但单项 probability / LR 仍然有价值。它们应被用于解释和增量诊断：

```text
P(good | family_i)
P(early_failure | family_i)
LR_good_i
LR_bad_i
```

对同日 bundle，应额外计算：

```text
P(good | bundle)
P(early_failure | bundle)
```

以及 leave-one-out 增量：

```text
delta_good_i =
  P(good | bundle)
  - P(good | bundle without family_i)

delta_bad_i =
  P(early_failure | bundle)
  - P(early_failure | bundle without family_i)
```

这些 delta 只能用作解释和 family pruning，不应直接映射成 1R 的比例。相关 family 会重复计功。

---

## 7. 贝叶斯先验是否适合

贝叶斯框架适合 R03，但必须收缩相关证据。

不建议使用 naive Bayes：

```text
posterior odds = prior odds * LR_A * LR_B * LR_C
```

因为 same-day family 不是独立证据。更合理的形式是 shrinked log-odds update：

```text
logit(P_good | evidence, context)
  = logit(P_good | context)
  + sum_i shrink_weight_i * log(LR_good_i)

logit(P_bad | evidence, context)
  = logit(P_bad | context)
  + sum_i shrink_weight_i * log(LR_bad_i)
```

其中：

```text
0 <= shrink_weight_i <= 1
correlation higher => shrink_weight lower
incremental lift weaker => shrink_weight lower
same-day repeated evidence => shrink_weight lower
new evidence after survival => shrink_weight higher
```

更稳健的第一版可以不用逐项 LR 相加，而是：

```text
same-day bundle: direct posterior table
sequential new evidence: Bayesian update
```

这意味着：

```text
T0 同日 bundle 只校准初始 prior / probe cap；
T+5 / T+10 / T+20 的新证据才更新 posterior 并释放后续 risk budget。
```

---

## 8. Good / Bad Label 的建议

R03 不应只估 `P(big_winner | signal)`。对于 1R 建仓预算，更关键的是同时估 good path 和 bad path。

建议第一版至少定义：

```text
good_path =
  hit_plus10_before_minus5 == true
  OR path_quality_flag in {clean_continuation, tradable_continuation}

bad_path =
  early_failure_flag == true
  OR first_minus5_offset <= 10
  OR max_loss_before_first_plus10 <= -0.06
```

还可以保留中期 winner label：

```text
winner_h120 =
  close_return_t120 >= threshold
  OR max_gain_120d >= threshold
```

但 winner_h120 不能单独决定加仓，因为它可能伴随很深的先行回撤。

---

## 9. 1R 风险预算的初始拆分结构

总预算：

```text
max_build_risk = 1R
```

核心原则：

```text
同日多个 family 只能触发一次 probe；
后续只有 survival 和新 evidence 才能释放更多 R。
```

一个可讨论的初始结构：

```text
T0: same-day bundle trigger
  allowed_risk <= 0.15R .. 0.25R
  purpose = probe only

T+3 / T+5: no early failure
  if no -5% / -6% breach and structure intact:
    allowed_risk <= 0.35R .. 0.45R

T+10: survival + fresh evidence
  if price recovers / breaks seed high / new family appears after seed:
    allowed_risk <= 0.60R .. 0.75R

T+20: continuation confirmed
  if clean or tradable continuation and drawdown controlled:
    allowed_risk <= 1.00R

After T+30:
  no new build risk
  only hold / trail / reduce / exit
```

这种结构把 1R 拆给“时间上的新信息”，而不是拆给“同一天出现的多个相关信号”。

---

## 10. Risk Budget Gate 的概率形式

每次释放 risk budget 时，至少应同时检查 good posterior、bad posterior 和 expected R。

示意：

```text
if P_bad_upper > 0.45:
  max_risk = 0.20R

elif P_good_lower >= 0.35 and P_bad_upper <= 0.35:
  max_risk = 0.40R

elif survival_H10 and fresh_evidence_after_seed:
  max_risk = 0.70R

elif continuation_H20 and drawdown_control_ok:
  max_risk = 1.00R
```

更完整的形式：

```text
risk_cap_t =
  stage_cap_t
  * f(P_good_lower)
  * g(1 - P_bad_upper)
  * h(initial_risk_pct_quality)
  * k(liquidity_quality)
```

硬约束：

```text
initial_risk_pct must be within configured range
entry must be executable next open
build risk cannot increase after T+30
bad posterior breach freezes additional risk
stop breach exits or blocks further build
```

---

## 11. 对 R03 Requirement 的启发

R03 不应从“选一个最强 entry signal”开始，而应从以下 contract 开始：

```text
1. define seed episode
2. define same-day evidence bundle
3. estimate action-time posterior for bundle
4. define survival gate
5. define fresh evidence after seed
6. map posterior and survival state to staged risk cap
7. evaluate EV_R under deterministic execution
```

R03 第一版不应追求复杂 portfolio simulation。更小的可验证目标是：

```text
同样 1R 总预算下，
staged build 是否比 T0 full-entry 降低 early failure / max drawdown，
同时保留 enough upside capture。
```

最低需要比较的 baselines：

```text
baseline_0: no trade / background prior
baseline_1: T0 full 1R entry on same-day bundle
baseline_2: T0 fixed 0.25R probe only
baseline_3: T0 fixed probe + single survival step-up
candidate: staged posterior + survival-gated build up to 1R
```

`baseline_3` 是关键 control。它用于区分：

```text
staged posterior evidence accumulation 是否真的有增量价值，
还是单纯 "survival 后再加仓" 已经解释了大部分改善。
```

如果 staged build 不能显著降低 early failure 或 drawdown，同时又损失了 winner capture，则 discussion2 的 evidence accumulation 假设不成立，需要回到 family search 或 label 设计。

---

## 12. 当前开放问题

后续进入 requirement 前，还需要明确：

```text
1. good_path / bad_path 的正式 label 是否采用 close、low/high，还是混合路径定义；
2. same-day bundle 的最小样本数和分桶方式；
3. shrink_weight 如何从 phi / Jaccard / incremental lift 映射；R03 v1 是否应先完全不使用 shrink_weight；
4. stage cap 的具体阈值是否由 train 固定、validation 只评估；
5. probe 后的 fresh evidence 是否必须来自不同 family，还是允许同 family 二次触发；
6. survival gate 是否使用 price stop、close stop、structure low，还是 R-based stop；
7. EV_R 是否采用 H20 fail-fast diagnostic execution，还是直接模拟 30D build + 120D hold。
```

这些问题应在 R03 requirement 中收紧为可实现、可验证、无未来函数的合同。

---

## 13. R03 v1 简化原则

为避免在第一版 requirement 中引入过多自由度，R03 v1 应先采用更保守的简化原则。

### 13.1 Posterior 计算

R03 v1 只使用 direct posterior table，不做 naive Bayes，也不做 shrinked log-odds 相加。

```text
posterior table key =
  same_day_bundle_key
  + context_bucket

outputs =
  P_good
  P_bad
  P_neutral
  EV_R
  sample_count
  confidence_interval
```

如果某个 bundle / context 桶样本不足：

```text
sample_count < N_min
```

则该桶不得单独给出 posterior gate，应回退到更粗粒度 bucket：

```text
same_day_family_count bucket
family_group bucket
single_family bucket
global action-time prior
```

LR / log-odds / shrink_weight 只保留为 v2 研究方向。

### 13.2 Candidate Set 冻结

R03 v1 的 candidate family / bundle 必须 train-only 选择。

```text
train:
  compute prior / posterior / EV_R / drawdown diagnostics
  select candidate family or bundle set
  select stage-cap grid result

validation / robustness:
  read-only evaluation
  no threshold tuning
  no family replacement
  no post-hoc bucket merge
```

`single_range_breakout`、`single_volume_money`、`single_oscillator` 当前只能作为 discussion-level candidates。正式 requirement 中必须重新用 train-only evidence 固定候选集，并检查 split stability。

### 13.3 Good / Bad / Neutral 三分类

R03 v1 应定义互斥标签：

```text
bad_path
good_path
neutral_path
```

标签判定必须有固定优先级。建议第一版采用：

```text
1. if bad condition is true:
     label = bad_path
2. else if good condition is true:
     label = good_path
3. else:
     label = neutral_path
```

这样可以保证：

```text
P_good + P_bad + P_neutral = 1
P_good + P_bad <= 1
```

这比同时估非互斥 `P_good` / `P_bad` 更适合 risk gate，避免同一样本既支持加仓又触发风险冻结。

### 13.4 Stage Cap 和阈值来源

所有 stage cap 和 posterior gate 阈值必须由 train split 固定。

```text
stage_cap_grid:
  probe_cap candidates
  survival_step_cap candidates
  confirmation_cap candidates
  final_cap candidates

posterior_gate_grid:
  P_good_lower threshold candidates
  P_bad_upper threshold candidates
```

在 EV_R 输入 materialize 之前，R03a 的 grid 不得包含 `EV_R_lower` 或任何 EV_R 排序阈值。EV_R 相关 gate 只能属于 R03b：

```text
R03a:
  probability-only feasibility gate
  no EV_R threshold
  no 1R sizing conclusion

R03b:
  EV_R inputs materialized
  EV_R_lower threshold candidates allowed
  risk-budget sizing validation allowed
```

validation 只回答：

```text
train-frozen staged build 是否复现降低 early failure / max drawdown；
是否保留足够 upside capture；
是否优于 baseline_2 and baseline_3。
```

### 13.5 Fresh Evidence 的 v1 最小定义

R03 v1 中，fresh evidence 建议先使用最小可执行定义：

```text
fresh_evidence_after_seed =
  a different family from the seed same-day bundle
  triggers for the first time
  at offset >= T+3
  and offset <= T+30
  while the seed episode has not failed
```

第一版不把同 family 连续触发计作 fresh evidence。这样可以避免把同一状态的连续噪声重复计为新信息。

但这个 v1 定义只记录 `first different family fresh trigger`。它不能证明 T+11..T+30 后段 fresh evidence 没有信息，因为 first-fresh offset 分布天然会向较早 offset 偏斜：

```text
P(first fresh at T+k)
  = P(no fresh in T+3..T+k-1)
    * P(fresh at T+k)
```

因此，R03 v1 可以保留 T+3..T+30 的观察窗口，但不能仅凭 first-fresh 分布决定后段窗口是否有效。若 R03 想使用“按时间序列逐个触发”的 fresh evidence，需要先补做 sequence / hazard diagnostic：

```text
fresh_count_in_window
fresh_offset_first
fresh_offset_last
fresh_density
fresh_family_sequence
kth_fresh_offset
per_offset_fresh_hazard
```

如果后续数据说明同 family second trigger 或多次 different-family trigger 有稳定增量，再在 v2 单独评估。

### 13.6 Leave-One-Out Delta 限制

Leave-one-out delta 只作为解释性诊断。

```text
delta_good_i = P(good | bundle) - P(good | bundle without i)
delta_bad_i = P(bad | bundle) - P(bad | bundle without i)
```

仅当两个桶都满足：

```text
sample_count >= N_min
```

才允许报告 delta。否则必须标记为 `NA`，不得用于 family pruning 或 risk-budget mapping。

### 13.7 与 R01 v3 的边界

R03 v1 不应替代 R01 v3 的 probe / fail-fast 主线。

建议关系：

```text
R01 v3:
  defines PIT universe
  defines tradability / next-open execution
  defines probe eligibility
  defines fail-fast / cooling / stop conventions

R03 v1:
  operates inside the R01 v3 executable probe framework
  studies how 1R build budget is released after seed
  compares full-entry, probe-only, survival step-up, and staged posterior build
```

也就是说，R03 v1 是 sizing / build-budget experiment，不是新的独立 entry / exit 策略。

---

## 14. Requirement 前的 Prior Diagnostic

在开启 `requirement_03_staged_evidence_risk_budget_v1.md` 前，应先做一个小型 prior diagnostic。该探查需求已单独记录为 `ep4/requirement_02_1_prior_probability_diagnostic_v1.md`。否则 R03 requirement 会缺少关键分母，容易把 discussion-level 直觉写成冻结合同。

这个 diagnostic 至少要计算：

```text
1. global action-time prior:
   P(good), P_bad, P_neutral, EV_R

2. single family prior:
   P(good | family_i)
   P(bad | family_i)
   EV_R(family_i)

3. same-day bundle prior:
   P(good | bundle_key)
   P(bad | bundle_key)
   EV_R(bundle_key)
   sample_count(bundle_key)

4. same-day family count prior:
   P(good | count = k)
   P(bad | count = k)
   EV_R(count = k)

5. survivor fresh-evidence offset distribution:
   first fresh family trigger offset after seed
   by good / bad / neutral path

6. train / validation / robustness split stability:
   posterior and EV_R drift by split
```

这个 prior diagnostic 的目的不是选最终参数，而是决定 R03 requirement 是否可写：

```text
if bundle buckets are too sparse:
  R03 v1 should use coarser family-count / family-group buckets

if fresh evidence mostly appears after T+30:
  build window must be reconsidered

if single-step survival baseline explains most improvement:
  staged posterior build must prove incremental value over baseline_3

if train-only candidate ranking is not split-stable:
  do not freeze that family set for R03
```

因此，进入 R03 requirement 前，先验比例计算是必要的。它应作为 R03 requirement 的 input evidence，而不是在 R03 validation 阶段才临时补算。

---

## 15. R02.1 Prior Diagnostic 实际结果

`requirement_02_1_prior_probability_diagnostic_v1.md` 已完成实现并重跑。产物位置：

```text
ep4/outputs/r02_1_prior_probability_diagnostic_v1/
```

验证状态：

```text
validation_status = passed
failed_checks = []
```

主要产物行数：

| table | rows |
|:--|--:|
| `r02_1_global_action_time_prior.csv` | 6 |
| `r02_1_single_family_prior.csv` | 63 |
| `r02_1_same_day_bundle_prior.csv` | 907 |
| `r02_1_same_day_family_count_prior.csv` | 63 |
| `r02_1_context_bucket_prior.csv` | 907 |
| `r02_1_survival_checkpoint_prior.csv` | 2,721 |
| `r02_1_fresh_evidence_prior.csv` | 3,882 |
| `r02_1_fresh_evidence_offset_distribution.csv` | 11,003 |
| `r02_1_split_stability_diagnostics.csv` | 1,777 |
| `r02_1_r03_input_readiness.csv` | 1 |

### 15.1 可用性与 blocker

R02.1 最重要的结论不是“可以直接进入 risk-budget 实验”，而是：

```text
single / family-count / survival / fresh evidence 的先验诊断已经可用；
但 EV_R 和 global action-time denominator 仍不可用。
```

当前 readiness：

| field | value |
|:--|:--|
| `global_prior_ready` | `blocked_missing_denominator` |
| `single_family_prior_ready` | `ready` |
| `same_day_bundle_prior_ready` | `ready` |
| `context_bucket_prior_ready` | `ready` |
| `survival_checkpoint_prior_ready` | `ready` |
| `fresh_evidence_prior_ready` | `ready` |
| `ev_r_ready` | `blocked_missing_ev_r` |
| `split_stability_ready` | `blocked_unstable_split` |
| `primary_blocker` | `blocked_missing_ev_r` |
| `secondary_blocker` | `blocked_missing_denominator\|blocked_unstable_split` |

这意味着 R03 可以开始起草 requirement，但第一版不能声称已经具备完整 risk-budget EV 依据。R03 如果涉及 1R 预算映射，必须先补齐 EV_R 输入，或者把 EV_R 明确降级为后续 requirement 的 blocker。

### 15.2 Single Family 先验比例

按互斥 `good_path / bad_path / neutral_path` 重算后，7 个 single family 的先验如下：

| family | row_count | row_label_denominator | P_good | P_bad | P_neutral |
|:--|--:|--:|--:|--:|--:|
| `range_breakout` | 68,679 | 54,069 | 35.42% | 61.57% | 3.02% |
| `volume_money` | 22,806 | 17,900 | 35.72% | 61.62% | 2.66% |
| `oscillator` | 23,132 | 18,293 | 35.45% | 61.72% | 2.83% |
| `volatility_band` | 28,211 | 22,023 | 34.81% | 62.85% | 2.34% |
| `pullback_drawdown` | 56,446 | 44,307 | 32.62% | 66.24% | 1.14% |
| `momentum_rps` | 44,120 | 33,909 | 32.39% | 66.52% | 1.09% |
| `price_trend` | 34,592 | 26,899 | 32.35% | 66.62% | 1.03% |

解释：

```text
range_breakout / volume_money / oscillator 仍然是相对更稳的 single family，
但它们的 P_bad 也都超过 61%。
```

所以它们不能被解释为 full-entry signal，只能作为：

```text
seed candidate
probe context
后续 staged build 的初始 evidence
```

`momentum_rps / price_trend / pullback_drawdown` 的 bad prior 更高，更适合作为 survival 后的 continuation / winner-capture evidence，而不是 T0 裸 entry 依据。

### 15.3 Same-Day Family Count 结果

R02.1 用同一套互斥标签重新确认了前面 path diagnostic 的反直觉结论：

| same_day_family_count | row_count | episode_label_denominator | P_good | P_bad | P_neutral |
|--:|--:|--:|--:|--:|--:|
| 1 | 29,908 | 23,692 | 35.78% | 60.72% | 3.50% |
| 2 | 23,677 | 18,525 | 35.50% | 61.57% | 2.93% |
| 3 | 14,587 | 11,507 | 34.84% | 62.91% | 2.25% |
| 4 | 10,248 | 7,985 | 34.10% | 64.15% | 1.75% |
| 5 | 8,624 | 6,746 | 32.80% | 66.11% | 1.08% |
| 6 | 7,187 | 5,616 | 31.25% | 67.24% | 1.51% |
| 7 | 4,247 | 3,253 | 33.75% | 65.51% | 0.74% |

关键信息：

```text
same-day family count 从 1 到 6 增加时，
P_bad 从 60.72% 上升到 67.24%。
```

这进一步否定了：

```text
同日共振越多 = entry 质量越高
```

更合理的解释是：

```text
同日多 family 触发更多是在识别短期拥挤 / 已经发热 / next-open 位置偏差的状态。
```

因此 R03 不应把同日多个 family 视为可相加的多份 risk budget。T0 same-day bundle 最多只能决定初始 probe cap。

同时，`same_day_family_count` 虽然 split-stable，但判别力有限：

```text
P_good from count=1 to count=6:
  35.78% -> 31.25%

P_bad from count=1 to count=6:
  60.72% -> 67.24%
```

它适合作为 audit / weak stratification，不适合作为 R03a 的主要 stage-cap gate。真正的主分层应优先来自 survival checkpoint。

### 15.4 Context Bucket 与 Bundle 稀疏性

R02.1 共生成 907 个 context bucket。样本充足性：

| sample_sufficiency_status | buckets |
|:--|--:|
| `sufficient` | 105 |
| `thin_bucket_report_only` | 157 |
| `too_sparse_use_fallback` | 628 |
| `unusable` | 17 |

fallback 分布：

| fallback_level | buckets |
|:--|--:|
| `same_day_bundle_key` | 105 |
| `same_day_family_count` | 802 |

解释：

```text
same-day bundle / context bucket 可以作为描述性 posterior 表，
但绝大多数 bucket 不适合在 R03 v1 中直接冻结为细粒度 gate。
```

R03 v1 如果使用 direct posterior table，应默认：

```text
primary fallback grain = same_day_family_count
only use same_day_bundle_key when sample_count >= N_min and split-stable
```

这也意味着 R03 v1 不应追求复杂 bundle-specific sizing。更稳妥的第一版应把细 bundle 作为解释字段，把 survival checkpoint 作为主分层，把 family-count 作为弱分层 / audit 字段，把 fresh-evidence 状态保留为描述性字段。

### 15.5 Survival Checkpoint 结果

survival checkpoint 是 R02.1 最有价值的结果之一。

| checkpoint | pre_rows | survivor_count | survivor_rate | survivor_episode_denominator | survivor_P_good | survivor_P_bad | survivor_P_neutral |
|:--|--:|--:|--:|--:|--:|--:|--:|
| T+3 | 98,478 | 75,269 | 76.43% | 59,491 | 45.13% | 51.58% | 3.28% |
| T+5 | 98,478 | 66,907 | 67.94% | 52,872 | 50.78% | 45.52% | 3.70% |
| T+10 | 98,478 | 54,064 | 54.90% | 42,751 | 62.81% | 32.62% | 4.57% |

这说明：

```text
仅仅要求 seed 在 T+3 / T+5 / T+10 没有 observable failure，
就会显著改善 good / bad path 分布。
```

尤其 T+10：

```text
P_good = 62.81%
P_bad = 32.62%
```

方向上已经明显好于 T0 的 single-family / same-day-count prior，但严格的改善幅度不能直接用这两组表相减。§15.2 是 row-level signal trigger prior，§15.5 是 survivor episode posterior，分母粒度不同。

R03 requirement 必须把 survival 改善幅度重算到同一粒度。推荐口径：

```text
grain = episode-first-trigger

compare:
  T0 episode prior
  vs
  T+3 / T+5 / T+10 survivor posterior
```

在该同粒度结果生成前，`survival improves P_good / P_bad` 可以作为强方向性证据，但不能作为精确 lift 数字引用。

对 R03 的含义：

```text
baseline_3: T0 fixed probe + survival step-up
必须成为强 control。
```

如果未来 staged posterior build 不能显著优于这个 survival-only baseline，则 evidence accumulation 的边际价值不足。也就是说，R03 不能只证明“分阶段比满仓进场好”，还必须证明：

```text
posterior / fresh evidence 比单纯 survival gate 有额外贡献。
```

### 15.6 Fresh Evidence Offset 分布

seed episode 总数：

```text
11,003
```

fresh evidence 状态分布：

| fresh_evidence_status | rows |
|:--|--:|
| `found_within_t3_t30` | 6,343 |
| `seed_failed_before_fresh` | 2,725 |
| `seed_failed_before_t3` | 1,533 |
| `none_within_t3_t30` | 305 |
| `ambiguous_same_offset` | 65 |
| `censored_before_t30` | 32 |

fresh offset bucket：

| fresh_offset_bucket | rows |
|:--|--:|
| `T3_T5` | 4,294 |
| `T6_T10` | 1,244 |
| `T11_T20` | 715 |
| `T21_T30` | 155 |
| `none` | 4,563 |
| `censored` | 32 |

numeric fresh offset median：

```text
T+3
```

解释边界：

```text
这张表是 first-fresh offset distribution，
不是 T+3..T+30 内所有 fresh evidence 的活跃度分布。
```

first-fresh 统计天然会把质量压到较早 offset。即使后续 T+11..T+30 仍有连续 fresh trigger，只要第一次 fresh 已经出现在 T+3..T+10，该 episode 也不会在 first-fresh 表里再次计数。因此，不能仅凭 median = T+3 推断后段 fresh 是噪声。

当前数据支持 R03 v1 继续保留观察窗口：

```text
fresh evidence window = T+3..T+30
```

但 R03 v1 不能把 `T+11..T+30` 直接用于 stage cap 释放，除非先补做 sequence / hazard diagnostic。当前可写入 R03a 的判断是：

```text
first fresh evidence is descriptive only;
fresh sequence evidence requires a separate diagnostic;
stage cap release must not depend on unvalidated late fresh sequence.
```

真正能回答后段 fresh 是否有信息的统计应包括：

```text
per-offset hazard among survived-and-no-prior-fresh episodes
cumulative fresh_count by horizon
second / third fresh family offset distribution
posterior by kth fresh event, aligned on survival checkpoint
```

### 15.7 Fresh Evidence Posterior

按 fresh evidence 状态聚合后的 posterior：

| fresh_evidence_status | fresh_label_denominator | P_good | P_bad | P_neutral |
|:--|--:|--:|--:|--:|
| `found_within_t3_t30` | 5,032 | 57.47% | 38.24% | 4.29% |
| `none_within_t3_t30` | 216 | 62.04% | 32.87% | 5.09% |
| `seed_failed_before_fresh` | 2,115 | 1.99% | 96.26% | 1.75% |
| `seed_failed_before_t3` | 1,195 | 0.00% | 100.00% | 0.00% |
| `ambiguous_same_offset` | 0 | NA | NA | NA |
| `censored_before_t30` | 0 | NA | NA | NA |

`found_within_t3_t30` 的 row-level observable failure 关系：

```text
fresh_before_observable_failure_rate = 66.53%
fresh_without_prior_observable_failure_rate = 100.00%
```

解释：

```text
fresh evidence 出现的 episode 明显优于 T0 prior，
但这里仍然存在 survival selection。
```

`none_within_t3_t30` 看起来更好：

```text
P_good = 62.04%
P_bad = 32.87%
```

但 denominator 只有 216，不能直接推论“没有 fresh 更好”。它更可能表示：

```text
能活过 T+30 且没有 fresh 的样本，本身已经通过了很强的 survival filter。
```

因此 R03 需要区分：

```text
fresh evidence 的增量贡献
survival 本身带来的 selection effect
```

这也是 baseline_3 必须存在的原因。

更严格地说，任何 fresh evidence posterior 比较都必须 condition on 同一个 survival horizon，否则 `found` 与 `none` 不可比。推荐比较口径：

```text
survived_t10 + fresh_found_before_t10
vs
survived_t10 + no_fresh_before_t10

or

survived_t30 + fresh_found_before_t30
vs
survived_t30 + no_fresh_before_t30
```

不能比较：

```text
found_within_t3_t30
vs
none_within_t3_t30
```

因为 `none_within_t3_t30` 已经隐含更长 survival requirement。

### 15.8 Split Stability

split stability 总体结果：

| stability_status | rows |
|:--|--:|
| `stable_enough_for_requirement_input` | 129 |
| `unstable_do_not_freeze` | 22 |
| `insufficient_sample` | 974 |
| `missing_split` | 652 |

按 grouping type：

| grouping_type | status | rows |
|:--|:--|--:|
| `single_family_prior` | stable | 7 |
| `same_day_family_count_prior` | stable | 7 |
| `same_day_bundle_prior` | stable | 28 |
| `same_day_bundle_prior` | unstable | 5 |
| `same_day_bundle_prior` | insufficient | 74 |
| `same_day_bundle_prior` | missing_split | 6 |
| `context_bucket_prior` | stable | 28 |
| `context_bucket_prior` | unstable | 5 |
| `context_bucket_prior` | insufficient | 74 |
| `context_bucket_prior` | missing_split | 6 |
| `survival_checkpoint_prior` | stable | 59 |
| `survival_checkpoint_prior` | unstable | 12 |
| `survival_checkpoint_prior` | insufficient | 237 |
| `survival_checkpoint_prior` | missing_split | 31 |
| `fresh_evidence_prior` | insufficient | 589 |
| `fresh_evidence_prior` | missing_split | 609 |

可用结论：

```text
single family prior 和 same-day family count prior 是 split-stable 的；
survival checkpoint 有部分可用 stable bucket；
bundle / context 只有少量 stable bucket；
fresh_evidence_prior 没有 stable bucket，全部是 insufficient_sample 或 missing_split。
```

所以 R03 v1 的设计应避免：

```text
在很细的 bundle/context/fresh bucket 上冻结具体 sizing 阈值。
```

更稳妥的方式是：

```text
用 seed single family / survival checkpoint 做主分层；
same_day_family_count 只做弱分层或 audit；
bundle/context/fresh bucket 做解释和 coarser fallback；
只有 stable + sufficient 的 bucket 才允许进入 train-only candidate grid。
```

由于 `fresh_evidence_prior` 在 split stability 中没有 stable row，R03a 不得把 fresh evidence 写成 train-frozen gate。fresh evidence 在 R03a 中只能作为 descriptive / hypothesis-generation 字段，除非后续 sequence / hazard diagnostic 产生 split-stable 的 fresh bucket。

### 15.9 对 R03 Requirement 的直接约束

基于 R02.1 结果，R03 requirement 应写成一个受限的 staged evidence audit，而不是直接 risk-budget optimization。

R03 v1 必须包含以下约束：

```text
1. T0 same-day bundle 只允许一次 probe，不按 family 数量拆多份 risk。

2. baseline_3 必须存在：
   T0 fixed probe + survival step-up。
   因为 survival checkpoint 已经单独显著改善 P_good / P_bad。

3. R03a candidate 的主分层应优先使用：
   seed single_family / seed_type
   survival_checkpoint_state
   fixed probe / survival-step baseline state

   same_day_family_count 只能作为 weak stratification / audit；
   fresh_evidence_status 只能 descriptive，不得作为 gate。

4. same_day_bundle_key / context_bucket 只能在 sample sufficient 且 split-stable 时使用；
   否则回退到 family_count 或 single_family。

5. EV_R 当前不可用；
   如果 R03 要做 1R risk-budget 映射，必须先补齐 signal_day_low / prior low / entry risk inputs。

6. global action-time prior 当前不可用；
   R03 如果需要 no-signal background baseline，必须先 materialize count-0 action-time denominator。

7. fresh evidence 不能直接解释为因果增量；
   必须和 survival-only baseline 比较；
   且所有 found / none posterior 比较必须 condition on 同一个 survival checkpoint。

8. T0 vs survival improvement 必须在同一 grain 重算；
   推荐使用 episode-first-trigger grain。

9. T+3..T+30 fresh observation window 暂时保留；
   但 first-fresh offset distribution 不能证明后段 fresh 无效；
   如果要使用序列 fresh evidence，必须先补做 sequence / hazard diagnostic。

10. R03a 不包含 EV_R_lower threshold；
    EV_R threshold 和 1R sizing 只能属于 R03b。
```

### 15.10 当前最强实证判断

R02.1 后，discussion3 的判断应从：

```text
同日多信号不能直接满仓 entry
```

推进到：

```text
R03a 的核心不是“选更强的 T0 信号”，
而是验证 T0 probe + survival checkpoint step-up 是否足以解释大部分改善；
fresh / bundle / context posterior 暂时只能解释，不应主导 sizing gate。
```

目前数据最支持的设计方向是：

```text
T0:
  small probe only

T+3 / T+5:
  first survival check
  block early failed episodes

T+5 / T+10:
  test fixed survival step-up
  compare against T0 full entry and probe-only

T+10:
  survival checkpoint is already a strong signal;
  must not confuse it with staged posterior edge

T+20 / T+30:
  descriptive continuation / fresh-sequence audit only,
  not stage cap release in R03a
```

如果 R03 不能在 train-frozen rules 下证明 staged posterior 的增量价值，则应回退为：

```text
probe + survival step-up + strict fail-fast
```

而不是继续增加 posterior table 复杂度。

### 15.11 EV_R 缺失下的概率可行性测算

在 EV_R 输入尚未 materialize 的情况下，可以使用近似成功概率做前置可行性测算，但它的边界必须非常清楚。

可以回答的问题：

```text
这个 staged evidence idea 是否值得进入 R03 requirement？
某个 survival / fresh evidence 状态是否显著改善 good / bad path odds？
某个 bucket 是否因为样本稀疏或 split drift 不适合冻结？
```

不能回答的问题：

```text
应该释放多少 R？
是否能把 risk cap 从 0.25R 提到 0.60R？
同 1R 预算下的真实期望收益是否为正？
是否可以作为交易策略上线？
```

原因是 EV_R 至少需要：

```text
win probability
average win size
average loss size
entry price
stop / initial risk distance
execution rule
exit / holding rule
```

而 R02.1 当前主要有：

```text
P_good
P_bad
P_neutral
survival posterior
fresh evidence posterior
split stability
bucket denominator
```

这些足以判断路径质量是否改善，但不足以决定 1R 的资金释放比例。

#### 15.11.1 Probability-Only Feasibility Score

在 R03 requirement 前，可以定义一个只用于筛选的 probability-only feasibility score：

```text
prob_feasibility_score =
  P_good_lower - P_bad_upper
```

更稳健的版本应和 baseline 比较：

```text
prob_edge_vs_baseline =
  (P_good_lower - baseline_P_good)
  - (P_bad_upper - baseline_P_bad)
```

其中：

```text
P_good_lower = train posterior 的下置信界 / credible lower bound
P_bad_upper = train posterior 的上置信界 / credible upper bound
baseline = same split、same grain 或 fallback grain 下的 baseline prior
```

使用方式：

```text
if prob_edge_vs_baseline <= 0:
  do not promote to R03 candidate

if P_bad_upper remains high:
  allow probe-only or survival-only baseline only

if survival improves P_good and reduces P_bad:
  allow as R03 hypothesis
  but keep EV_R sizing blocked

if fresh evidence appears useful:
  keep as descriptive hypothesis only
  require survival-aligned and split-stable sequence diagnostic before gate use
```

这类 score 只能决定：

```text
是否值得测试
在哪个 grain 测试
是否需要 fallback
```

不能决定：

```text
stage cap
position size
expected R
final trading action
```

#### 15.11.2 推荐的贝叶斯形式

如果使用贝叶斯先验，R03 前置诊断应使用 Dirichlet-Multinomial，而不是 naive Bayes。

标签空间：

```text
label in {good_path, bad_path, neutral_path}
```

先验：

```text
(P_good, P_bad, P_neutral)
  ~ Dirichlet(alpha_good, alpha_bad, alpha_neutral)
```

观测计数：

```text
n_good
n_bad
n_neutral
```

后验：

```text
posterior =
  Dirichlet(
    alpha_good + n_good,
    alpha_bad + n_bad,
    alpha_neutral + n_neutral
  )
```

输出：

```text
posterior_mean_P_good
posterior_mean_P_bad
posterior_mean_P_neutral
P_good_lower
P_bad_upper
credible_interval_width
sample_sufficiency_status
```

稀疏 bucket 的 prior 来源应按 fallback grain 逐级收缩：

```text
same_day_bundle_key
  -> same_day_family_count
  -> single_family
  -> global_action_time_prior, if materialized
```

如果 global action-time prior 仍不可用，则不能伪造 global prior。可以临时使用更粗的 observed-signal prior，但必须标记：

```text
prior_source = observed_signal_only
background_denominator_status = blocked_missing_denominator
```

R03 requirement 必须固定 `alpha` 来源，否则 `P_good_lower` / `P_bad_upper` 会随主观先验漂移。推荐 v1 采用以下二选一，并在 train 前冻结：

```text
option_a_uninformative:
  alpha_good = 0.5
  alpha_bad = 0.5
  alpha_neutral = 0.5
  source = Jeffreys prior

option_b_empirical_shrinkage:
  alpha vector = fallback grain empirical distribution * fixed_prior_strength
  fixed_prior_strength chosen in train only
  validation / robustness read-only
```

在 global action-time prior materialize 前，不得把 observed-signal prior 伪装成 market-wide background prior。

#### 15.11.3 当前数据下的可行性判断

R02.1 中最适合做 probability-only feasibility 的表是：

```text
same_day_family_count_prior
survival_checkpoint_prior
split_stability_diagnostics
```

`fresh_evidence_prior` 当前只能作为描述性参考，因为它在 split stability 中没有 stable row：

```text
fresh_evidence_prior:
  insufficient_sample = 589
  missing_split = 609
  stable = 0
```

当前最强的概率证据是 survival checkpoint：

```text
T+10 survivor:
  P_good = 62.81%
  P_bad = 32.62%
```

这足以支持：

```text
R03 必须测试 survival step-up baseline。
```

但它仍不足以支持：

```text
T+10 后应该加到 0.60R 或 1.00R。
```

fresh evidence 的概率结果有研究价值，但不能进入 R03a gate：

```text
found_within_t3_t30:
  P_good = 57.47%
  P_bad = 38.24%
```

这个状态混有 survival selection，并且 fresh prior split-stability 未通过。因此 R03 只能把它写成后续诊断假设：

```text
fresh evidence + same survival checkpoint
vs
no fresh evidence + same survival checkpoint
```

否则会把 survival 本身的改善误认为 fresh evidence 的增量贡献。

#### 15.11.4 写入 R03 Requirement 的边界语言

R03 requirement 如果在 EV_R 缺失时启动，应显式写成：

```text
probability-only feasibility diagnostic,
not EV_R sizing,
not final 1R risk-budget allocation.
```

并增加硬门槛：

```text
1. probability-only score 只能用于 candidate / bucket 筛选；
2. stage cap 只能使用固定 probe / survival baseline cap，不得由 probability score 直接映射；
3. 所有 sizing / EV / 1R allocation 结论必须等待 EV_R inputs materialized；
4. validation / robustness 只能评估 train-frozen probability gates，不得调阈值；
5. report 必须把 EV_R status 标为 blocked_missing_ev_r；
6. fresh evidence 在 R03a 中只能 descriptive，不能用于 gate；
7. survival 改善必须在 episode-first-trigger grain 重算。
```

因此，当前可接受的推进方式是：

```text
R03a:
  probability-only survival-step feasibility audit
  fixed probe + fixed survival-step cap
  fresh / bundle / context descriptive only

R03b:
  EV_R-materialized risk-budget experiment
```

如果不拆成两个阶段，也必须在同一个 R03 requirement 中把 probability-only 部分和 EV_R sizing 部分分成两个 lifecycle gate：

```text
Gate 1:
  probability feasibility passed

Gate 2:
  EV_R inputs available and EV_R sizing validated
```

---

## 16. R03a Contract Draft And Null Result Contingency

基于 §15 的数据，R03a 的合同范围应比最初设想更窄。当前证据并不支持一个复杂的 posterior-driven staged sizing system。更合理的 R03a 是：

```text
probability-only survival-step feasibility audit
```

而不是：

```text
full staged posterior risk-budget experiment
```

### 16.1 R03a 最小可执行合同

R03a 应只测试以下核心结构：

```text
seed:
  T0 same-day bundle / single family trigger

initial action:
  fixed small probe

step-up authority:
  survival_checkpoint_state
  especially T+5 / T+10 survivor

comparison baselines:
  baseline_1 = T0 full 1R entry
  baseline_2 = T0 fixed probe only
  baseline_3 = T0 fixed probe + survival step-up

candidate:
  T0 fixed probe + train-frozen survival step-up rule
```

R03a 不应把以下字段作为 primary gate：

```text
fresh_evidence_status
same_day_bundle_key
context_bucket_id
EV_R_diagnostic
```

原因：

```text
fresh_evidence_prior:
  no stable split bucket

same_day_bundle / context:
  mostly sparse or fallback-only

EV_R:
  blocked_missing_ev_r
```

这些字段可以进入 report 解释：

```text
descriptive posterior
bucket sparsity audit
hypothesis generation
future diagnostic backlog
```

但不能决定：

```text
stage cap
risk release
candidate promotion
validation pass/fail
```

### 16.2 必须先补齐的同粒度诊断

R03a requirement 起草前或 requirement 内部第一步，必须重算 survival lift 的同粒度版本：

```text
grain = episode-first-trigger

tables:
  T0_episode_prior
  T+3_survivor_episode_prior
  T+5_survivor_episode_prior
  T+10_survivor_episode_prior
```

输出：

```text
P_good
P_bad
P_neutral
label_denominator
credible interval
split stability
```

这样才能回答：

```text
survival checkpoint 的改善幅度到底有多大？
baseline_3 是否已经解释大部分改善？
```

在该表生成前，§15.5 的 T+10 survivor 数字只能作为强方向性证据，不能作为最终 lift 数字。

### 16.3 Fresh Evidence 后续诊断 backlog

如果仍然希望研究“信号按时间序列逐个触发”的假设，需要追加 fresh-sequence diagnostic。建议输出：

```text
r02_1_fresh_evidence_sequence.csv
```

最小字段：

```text
seed_episode_id
instrument_id
seed_trade_date
seed_same_day_bundle_key
survival_checkpoint_state
fresh_count_t3_t10
fresh_count_t11_t30
fresh_count_t3_t30
fresh_offset_first
fresh_offset_last
fresh_family_sequence
fresh_offset_sequence
per_offset_hazard_denominator
per_offset_hazard_rate
label
split
year
```

这张表要回答：

```text
1. 是否存在持续的 fresh sequence，而不仅是 first fresh？
2. 第二、第三个 fresh family 是否有边际信息？
3. T+11..T+30 的 fresh 是否在控制 survival 后仍有增量？
4. fresh sequence bucket 是否 split-stable？
```

只有当这些问题有稳定正证据时，fresh evidence 才能从 descriptive 字段升级为 R03b 或后续 R03a' 的 gate。

### 16.4 Null Result Contingency

R03a 必须预设 null result 的处理方式，避免在 validation 上反复调参。

R03a 的核心 null hypothesis：

```text
H0:
  staged posterior / extra evidence logic
  does not improve over baseline_3
  after using the same total probe and survival-step framework.
```

如果 R03a 结果满足以下任一情况：

```text
candidate <= baseline_3 on P_bad / drawdown reduction
candidate loses too much upside capture vs baseline_3
candidate only wins in train but not validation / robustness
candidate improvement depends on sparse bundle / fresh bucket
```

则结论应写为：

```text
no incremental staged-posterior edge over survival step-up
```

并停止继续调参。允许的下一步只有：

```text
1. adopt simple probe + survival step-up + strict fail-fast as the current best simple structure;
2. materialize EV_R inputs and run R03b if sizing is still the central question;
3. run fresh-sequence / hazard diagnostic if sequential evidence remains a hypothesis;
4. return to family / label design only if survival-step baseline itself is insufficient.
```

不允许的下一步：

```text
post-hoc merge sparse buckets
tune probability thresholds on validation
promote fresh evidence gate without split-stable diagnostic
convert descriptive posterior tables into sizing rules
```

这意味着 R02.1 已经把 R03a 的实验空间压缩到一个很小但可验证的问题：

```text
T0 probe + T+10 survival step-up 是否已经足够？
```

如果答案是 yes，则复杂 posterior table 暂时不应进入 sizing 合同。

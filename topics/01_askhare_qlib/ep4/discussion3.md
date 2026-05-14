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
  EV_R_lower threshold candidates
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

如果后续数据说明同 family second trigger 有稳定增量，再在 v2 单独评估。

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

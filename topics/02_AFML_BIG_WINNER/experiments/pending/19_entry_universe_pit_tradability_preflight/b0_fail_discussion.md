# 19B0 Fail Discussion: Baseline Quality Block 和 Family Repair Direction

## 1. 本轮状态

19B0 的最终状态：

```text
decision_state = 19B0_baseline_materialization_blocked
blocking_reason = baseline_matching_quality_gate
next_allowed_requirement = none
selected_family_cell_pair_n = 0
```

这个状态不是因为没有候选、不是因为 next-open label 锚点不可用，也不是因为 denominator 不足。本轮真正失败点是 matched baseline quality：

```text
baseline_materialization_gate:
    pass for 489 / 489 baseline-family-cell rows

baseline_matching_quality_gate:
    fail for 489 / 489 baseline-family-cell rows
```

因此本轮不能进入 19B robustness。任何 family 的 train lift 都只能作为 diagnostic / hypothesis，不可解释为稳健 PIT 右尾水库证据。

## 1.1 Evidence sources and scope

本文使用两类证据，结论边界不同：

```text
Contract outputs:
    outputs/19B0_fast_rule_grid_enrichment_scan/entry_universe_19b0_decision.csv
    outputs/19B0_fast_rule_grid_enrichment_scan/baseline_matching_quality_audit.csv
    outputs/19B0_fast_rule_grid_enrichment_scan/baseline_materialization_audit.csv
    outputs/19B0_fast_rule_grid_enrichment_scan/train_cell_metric_readout.csv
    outputs/19B0_fast_rule_grid_enrichment_scan/candidate_cell_denominator_audit.csv
    outputs/19B0_fast_rule_grid_enrichment_scan/family_selection_audit.csv

Diagnostic local-cache readouts:
    outputs/19B0_fast_rule_grid_enrichment_scan/local_cache/universe_feature_panel_v3.parquet
    ad hoc train-only summaries derived from the same executable-entry anchored
    universe feature panel.
```

Contract outputs support the fail-closed decision, gate status, family/cell metric
readout, denominator, and baseline quality facts. Local-cache readouts support
descriptive diagnostics such as single-variable quintile rates and parameter-axis
summaries; they are not standalone decision gates and must not override the
contract outputs.

Reproducibility requirement:

```text
The diagnostic local-cache panel is not a decision gate, but it materially
drives repair direction in this document. Therefore the next requirement must
hash it into an input audit before any outcome readout:

    path = outputs/19B0_fast_rule_grid_enrichment_scan/local_cache/universe_feature_panel_v3.parquet
    required audit fields:
        source_path
        sha256
        row_count
        column_count
        split coverage
        min/max decision_date
        generated_by
        generated_at

Any descriptive quintile / parameter-axis diagnostic cited from this panel must
be reproducible from the audited artifact.
```

## 2. 全局 baseline failure

19B0 使用三类 baseline：

```text
calendar_time_random_same_budget
instrument_matched_random_same_budget
liquidity_size_volatility_matched_same_budget
```

三类 baseline 都能物化 same-budget row count，但 matching quality 全部失败。

| baseline family | rows | pass_n | unmatched median | max SMD median | decision-month delta median |
|---|---:|---:|---:|---:|---:|
| calendar_time_random_same_budget | 163 | 0 | 0.1287 | 1.0640 | 0.0233 |
| instrument_matched_random_same_budget | 163 | 0 | 0.0230 | 1.0918 | 0.0351 |
| liquidity_size_volatility_matched_same_budget | 163 | 0 | 0.2061 | 0.3917 | 0.0233 |

Quality threshold failure count:

| rule | threshold | fail_n / 489 | median | max |
|---|---:|---:|---:|---:|
| unmatched_candidate_rate | <= 0.05 | 328 | 0.1284 | 0.3266 |
| baseline_reuse_rate | <= 0.20 | 0 | 0.0017 | 0.0138 |
| max_standardized_mean_difference_after_matching | <= 0.10 | 489 | 0.9632 | 1.4680 |
| decision_month_coverage_delta | <= 0.02 | 431 | 0.0247 | 0.1053 |
| instrument_coverage_delta | <= 0.05 | 0 | 0.0023 | 0.0078 |

Interpretation:

- row count 不是问题：same-budget rows 都能抽到。
- reuse 不是问题：baseline reuse rate 很低。
- instrument coverage 不是问题：instrument delta 远低于 0.05。
- 真正问题是 covariate balance，尤其 max SMD 全部超阈值。
- LSV baseline 的 SMD 明显比 calendar / instrument baseline 低，但 unmatched rate 高，说明当前 bucket 在一部分候选区域没有足够覆盖。

下一步如果继续做 19B0.x，必须先修 baseline design，否则所有依赖 matched baseline 的 train lift 归因都不成立。

两点必须提前锁定，避免下一轮走偏：

1. balance 与 coverage 之间存在结构性张力。当候选是对某个协变量（这里主要是近期收益 / 相对强势）做极端切分定义时，收紧 bucket / caliper 去压 `max_SMD <= 0.10`，可能会把 `unmatched_candidate_rate` 推过 `<= 0.05`（本轮 LSV 已经是最低 SMD 0.392 但最高 unmatched 0.206）。但当前还没有做预注册 matching-repair sweep，因此"两个质量门联合不可满足"现在只能作为**待检验假设**。只有在 coarser bucket / caliper / nearest-neighbor 等预注册修复后仍无法同时满足 `max_SMD <= 0.10` 与 `unmatched_candidate_rate <= 0.05`，才可升级为终局诊断；届时它本身说明候选相对中性 baseline 的 common support 很差，其 tail lift 主要是暴露而非独立 edge。
2. "无法归因"只适用于**依赖 matched baseline 的结论**。少数 baseline-independent descriptive evidence 当前可成立（例如 B4 与 label 的单变量方向矛盾，见 4.4），但它们仍不是完整 family-level attribution。

终局诊断升级必须落到数据产物，而不是只写在报告叙述中。19B0.1 至少需要输出：

```text
matching_repair_sweep_audit.csv
    family_id
    grid_cell_id
    baseline_family
    repair_variant_id
    matching_method
    bucket_spec_id
    caliper_spec_id
    candidate_n
    matched_candidate_n
    unmatched_candidate_rate
    baseline_reuse_rate
    max_smd_after_matching
    per_feature_smd_json
    decision_month_coverage_delta
    instrument_coverage_delta
    common_support_pass
    baseline_matching_quality_pass
    failure_reason
```

只有该 sweep 证明多个预注册 repair variant 同时无法满足 `max_SMD <= 0.10`
和 `unmatched_candidate_rate <= 0.05`，才能把"联合不可满足"升级为本实验的
common-support 结论。

## 3. 为什么 B2 看起来最接近

B2 best cell:

```text
family_id = B2_relative_strength_breakout
grid_cell_id = B2-relative-strength-breakout__d0f0fb1727c9

stock_vs_market_20d_min = 0.15
return_60d_rank_pct_min = 0.80
close_to_ema60_min = 0.00
market_regime_filter = all
```

Observed:

```text
candidate_n = 5,927
instrument_n = 1,073
instrument_month_n = 4,827
p_candidate_50 = 22.473%
conservative_lift = 1.1036
conservative_adjusted = 0.0036
family_triage_status = train_diagnostic_only
```

B2 的接近并非随机噪音。全 baseline eligible universe 中，`+50 / 120d` 明显偏好相对强势和横截面强势：

```text
stock_vs_market_return_20d:
    highest quintile +50 rate ~= 19.8%

return_60d_cross_section_rank_pct:
    highest quintile +50 rate ~= 20.8%

close_to_ema60:
    highest quintile +50 rate ~= 20.2%
```

B2 正好直接使用这些变量，因此自然最接近。

但是，B2 的 lift 目前不能归因。B2 best cell 的候选和 baseline 在 matching features 上仍严重不平衡，尤其 `match_return20`。

| baseline | candidate match_return20 mean | baseline match_return20 mean | SMD |
|---|---:|---:|---:|
| calendar-time | 28.47% | 2.39% | 1.188 |
| instrument-matched | 28.47% | 3.45% | 1.101 |
| LSV matched | 28.47% | 18.78% | 0.451 |

Conclusion:

B2 是最值得继续修的方向，但当前证据是 “相对强势暴露有 train diagnostic”，不是 “B2 已经是稳健右尾水库”。修复 baseline 前，B2 的 tail lift 可能只是近期强动量暴露没有被 baseline 充分中和。

## 4. Family-by-family failure analysis

### 4.1 B1 Near 120d High + Volume Expansion

Best cell:

```text
amount_ratio_20d_min = 2.0
near_high_120d_pct_max = 0.05
return_20d_min = 0.0
market_regime_filter = all
```

Observed:

```text
candidate_n = 3,927
instrument_n = 915
instrument_month_n = 3,770
p_candidate_50 = 16.552%
conservative_lift = 1.0350
conservative_adjusted = -0.0723
rank = 30
```

Baseline arms:

| baseline | p_candidate_50 | p_matched_50 | lift | adjusted |
|---|---:|---:|---:|---:|
| calendar-time | 16.552% | 14.719% | 1.1246 | 0.0088 |
| instrument-matched | 16.552% | 15.992% | 1.0350 | -0.0723 |
| LSV matched | 16.552% | 15.508% | 1.0673 | -0.0451 |

Failure reason:

B1 近高点 + 放量听起来像突破，但当前定义更像普通强势/放量状态。`amount_ratio_20d` 在全 universe 中对 +50 的单变量解释力很弱，最高分位 +50 率只到约 16.6%。B1 的实际 winner rate 也只有 16.55%，接近整体 baseline eligible pool 的 16.09%。

B1 的 apparent lift 在 calendar baseline 下有一点，但 instrument / LSV baseline 后基本被吃掉。这说明 B1 的优势更多来自时间、股票、流动性/近期收益暴露，而不是独立的突破机制。

Component SMD:

```text
calendar baseline:
    amount SMD ~= 1.382
    return20 SMD ~= 0.771

instrument baseline:
    amount SMD ~= 1.438
    return20 SMD ~= 0.886

LSV baseline:
    amount SMD ~= 0.770
    return20 SMD ~= 0.216
```

Repair direction:

1. 不要把 amount expansion 当主 alpha，只作为 confirmation。
2. 将 “near high” 改成更明确的 breakout / reclaim：
   - close breaks prior 120d high
   - close in top x% of daily range
   - high breakout followed by close hold
3. 增加相对强势条件：
   - `stock_vs_market_20d > 0`
   - `return_60d_rank_pct >= 0.7 / 0.8`
4. B1 应从 “near high + volume” 改成 “relative-strength breakout confirmation”。
5. 修复后的 B1 需要和 B2 做 ablation，避免只是 B2 的弱版本。

### 4.2 B5 Recent High Close + Amount Expansion

Best cell:

```text
amount_ratio_20d_min = 1.2
close_position_in_120d_range_min = 0.7
quality_amount_flag_required = true
return_10d_min = 0.06
```

Observed:

```text
candidate_n = 8,592
instrument_n = 1,092
instrument_month_n = 7,582
p_candidate_50 = 18.878%
conservative_lift = 1.0574
conservative_adjusted = -0.0426
rank = 14
```

Baseline arms:

| baseline | p_candidate_50 | p_matched_50 | lift | adjusted |
|---|---:|---:|---:|---:|
| calendar-time | 18.878% | 15.933% | 1.1848 | 0.0848 |
| instrument-matched | 18.878% | 17.854% | 1.0574 | -0.0426 |
| LSV matched | 18.878% | 17.772% | 1.0622 | -0.0378 |

Failure reason:

B5 是有弱正向效果的，比 B1 更像趋势延续，但 lift 太薄。它选到的是近期强收盘 + 短期上涨 + 放量状态；这些条件确实提高 +50 rate，但 matched baseline 也有较高 base rate，因此 conservative lift 只有 1.057。

Parameter axis diagnostics:

```text
return_10d_min:
    0.03 mean p50 ~= 18.02%
    0.06 mean p50 ~= 18.57%
    0.10 mean p50 ~= 19.73%

close_position_in_120d_range_min:
    0.70 mean p50 ~= 18.88%
    0.85 mean p50 ~= 18.71%
    0.95 mean p50 ~= 18.73%

amount_ratio_20d_min:
    1.2 mean p50 ~= 18.96%
    1.5 mean p50 ~= 18.59%
```

Interpretation:

- `return_10d_min` 越高，p50 越高。
- `close_position` 更高没有明显增益。
- amount threshold 过高反而不更好。

Component SMD:

```text
calendar baseline:
    amount SMD ~= 1.010
    return20 SMD ~= 0.816

instrument baseline:
    amount SMD ~= 1.040
    return20 SMD ~= 0.860

LSV baseline:
    amount SMD ~= 0.383
    return20 SMD ~= 0.233
```

Repair direction:

1. 保留 B5，但定位为 secondary trend-continuation family。
2. 强化短期收益，而不是强化 close position：
   - expand `return_10d_min` to 0.12 / 0.15
3. amount threshold 保持 1.2，不宜盲目提高。
4. 增加相对强度：
   - `stock_vs_market_20d > 0.05 / 0.10`
   - `return_60d_rank_pct >= 0.7`
5. 若修复后仍只剩 1.05-1.07 lift，应降级为 B2 的 confirmation filter。

### 4.3 B6 Low Drawdown Reclaim / EMA Reclaim

Best cell:

```text
close_to_ema60_min = 0.05
early_no_false_repair_10d_required = false_or_missing_allowed
market_drawdown_60d_min = -0.10
return_5d_min = 0.03
```

Observed:

```text
candidate_n = 15,406
instrument_n = 1,215
instrument_month_n = 12,349
p_candidate_50 = 18.155%
conservative_lift = 1.0029
conservative_adjusted = -0.0971
rank = 53
```

Baseline arms:

| baseline | p_candidate_50 | p_matched_50 | lift | adjusted |
|---|---:|---:|---:|---:|
| calendar-time | 18.155% | 16.435% | 1.1047 | 0.0047 |
| instrument-matched | 18.155% | 18.103% | 1.0029 | -0.0971 |
| LSV matched | 18.155% | 17.837% | 1.0178 | -0.0822 |

Failure reason:

B6 在 calendar baseline 下看起来还有 lift，但 instrument matched 后完全消失。表面上这指向：B6 不是独立右尾来源，而是同一批股票在修复期本身具有更高 base rate，更像 participation / market state filter，而非 primary winner family。

Caveat（重要）：这个归因**依赖 instrument-matched baseline**，而该 baseline 本轮 return20 SMD ≈ 1.09，并未平衡，因此它还**不是有效匹配比较**。在 baseline 修复（见 Priority 0）之前，"B6 = participation" 只能作为 hypothesis，不能作为已确认结论。

Parameter axis diagnostics:

```text
close_to_ema60_min:
    0.00 mean p50 ~= 16.50%
    0.02 mean p50 ~= 17.18%
    0.05 mean p50 ~= 18.19%

return_5d_min:
    0.00 mean p50 ~= 17.12%
    0.03 mean p50 ~= 17.46%
```

Interpretation:

站上 EMA60 越强，p50 越高。当前 train diagnostic 更像状态修复暴露，但由于
matched baseline 尚未平衡，"不是相对同股票 baseline 的额外优势" 仍只是待验证
hypothesis，而不是已确认结论。

Component SMD:

```text
calendar baseline:
    amount SMD ~= 0.724
    return20 SMD ~= 0.643

instrument baseline:
    amount SMD ~= 0.766
    return20 SMD ~= 0.703

LSV baseline:
    amount SMD ~= 0.300
    return20 SMD ~= 0.189
```

Repair direction:

1. 在 baseline 修复前，B6 不应提升为 primary winner family。
2. 若 baseline 修复后仍无 residual lift，再将 B6 降级为 regime / participation filter。
3. 如果继续保留，需要加入 relative reclaim：
   - reclaim 后 `stock_vs_market_20d > 0`
   - reclaim 后 `return_20d_rank_pct >= 0.7`
4. market drawdown 条件要更明确：
   - separate market panic rebound vs normal uptrend
5. 更适合和 B2/B5 组合：
   - B2 in favorable reclaim regime
   - B5 only when market drawdown repaired

### 4.4 B4 Volatility Contraction Then Breakout

Best cell:

```text
amount_ratio_20d_min = 1.2
atr_20_pct_rank_max = 0.5
intraday_range_pct_max = 0.08
return_5d_min = 0.03
```

Observed:

```text
candidate_n = 11,772
instrument_n = 967
instrument_month_n = 10,558
p_candidate_50 = 12.504%
conservative_lift = 0.7756
conservative_adjusted = -0.3244
rank = 128
```

Baseline arms:

| baseline | p_candidate_50 | p_matched_50 | lift | adjusted |
|---|---:|---:|---:|---:|
| calendar-time | 12.504% | 16.123% | 0.7756 | -0.3244 |
| instrument-matched | 12.504% | 12.819% | 0.9755 | -0.1245 |
| LSV matched | 12.504% | 14.220% | 0.8793 | -0.2207 |

Failure reason:

B4 的方向和 `+50 / 120d` 标签相反。当前标签明显偏好高波动、高 range：

```text
atr_20_pct_rank:
    low quintile +50 rate ~= 7.9%
    high quintile +50 rate ~= 23.6%

intraday_range_pct:
    low quintile +50 rate ~= 9.9%
    high quintile +50 rate ~= 20.7%
```

B4 选的是 volatility contraction，等于主动避开当前 +50 标签最喜欢的高波动区域。因此 B4 的描述性证据比其他 family 更弱。

注意：这个判断是 **baseline-independent descriptive evidence**，不是完整的
family-level attribution。它只说明在本轮 train baseline-eligible universe 中，
`atr_20_pct_rank` / `intraday_range_pct` 的单变量关系与 B4 的 low-vol 条件方向相反
（low quintile +50 率 ~7.9% vs high quintile ~23.6%）。由于 B4 是多条件规则，
且 matched baseline 仍未通过 SMD，不能把它写成已完成的因果归因；但足以支持
"当前 B4 规则方向需要重写或降级" 的工程判断。

Parameter axis diagnostics:

```text
atr_20_pct_rank_max:
    0.3 mean p50 ~= 9.63%
    0.4 mean p50 ~= 10.37%
    0.5 mean p50 ~= 11.21%

intraday_range_pct_max:
    0.03 mean p50 ~= 9.66%
    0.05 mean p50 ~= 10.62%
    0.08 mean p50 ~= 10.93%

return_5d_min:
    0.00 mean p50 ~= 9.79%
    0.03 mean p50 ~= 11.02%
```

即使放宽 low-vol 约束，p50 也仍明显低于 baseline pool。

Repair direction:

1. 当前 B4 应暂时下线或改写。
2. 不要再用 low ATR / low intraday range 作为 primary entry condition。
3. 若要保留 “volatility spring”，必须改成两阶段：
   - prior compression over past window
   - current expansion / breakout trigger
4. 新 B4 应包含：
   - previous 20/60d volatility contraction
   - current day or recent 3/5d range expansion
   - amount expansion
   - close breakout / close in high range
5. 或将 B4 降级为 false-positive / left-tail filter，而不是右尾 primary source。

### 4.5 EP07 TopN Multichannel Union

Observed:

```text
candidate_n = 5,116
instrument_n = 803
instrument_month_n = 4,889
p_candidate_50 = 16.634%
conservative_lift = 0.9942
conservative_adjusted = -0.1058
rank = 60
```

Baseline arms:

| baseline | p_candidate_50 | p_matched_50 | lift | adjusted |
|---|---:|---:|---:|---:|
| calendar-time | 16.634% | 16.732% | 0.9942 | -0.1058 |
| instrument-matched | 16.634% | 15.715% | 1.0585 | -0.0415 |
| LSV matched | 16.634% | 16.380% | 1.0155 | -0.0845 |

Failure reason:

EP07 union 很宽，p50 只略高于总体 base rate。它可能更像 recall
reservoir，而不像 precision family；但该判断在 baseline 修复前只能作为
hypothesis。整体 union 中可能有有用子通道，混在一起后被稀释。

Caveat：与 B6 同理，"EP07 union 无 precision" 的判断依赖 instrument-matched / LSV baseline（本轮 return20 SMD 仍高），在 baseline 修复前属于 hypothesis。可直接成立的只有描述性事实：EP07 union 的 p50（16.63%）仅略高于总体 base rate（≈16.09%）。

Component SMD:

```text
calendar baseline:
    amount SMD ~= 0.704
    return20 SMD ~= 0.355

instrument baseline:
    amount SMD ~= 0.778
    return20 SMD ~= 0.509

LSV baseline:
    amount SMD ~= 0.249
    return20 SMD ~= 0.027
```

Repair direction:

1. 不把 EP07 union 直接提升为 primary precision family。
2. 按 EP07 source/channel 拆成多个 family，并与整体 union 并行保留 diagnostic。
3. 对每个 channel 单独输出：
   - denominator
   - p_candidate_50
   - matched baseline lift
   - false-positive burden
   - left-tail burden
4. 若 channel 拆分后仍无 residual lift，宽 union 才降级为 recall source。

## 5. Cross-family interpretation

当前 `+50 / 120d` label 的经验结构更偏：

```text
relative strength
high recent return
high cross-sectional rank
high volatility / range
positive trend continuation
```

不偏：

```text
generic volume expansion
generic near high
low volatility contraction
wide repair/reclaim state
broad union candidate set
```

因此各 family 当前表现排序是合理的：

| family | best adjusted conservative | interpretation |
|---|---:|---|
| B2_relative_strength_breakout | 0.0036 | 最接近 label 主驱动，但 baseline 未修干净 |
| B5_recent_high_close_plus_amount_expansion | -0.0426 | 有弱趋势延续效果，但 lift 太薄 |
| B1_near_120d_high_plus_volume_expansion | -0.0723 | 近高点/放量不够尖锐；当前读数是 residual-not-total B1 estimand |
| B6_low_drawdown_reclaim_or_ema_reclaim | -0.0971 | 可能更像 regime / participation state；baseline 修复前仅为 hypothesis |
| EP07_topn_multichannel_recommended_union | -0.1058 | union 可能太宽、信号被稀释；baseline 修复前仅为 hypothesis |
| B4_volatility_contraction_then_breakout | -0.3244 | baseline-independent descriptive evidence 显示 low-vol 条件与 +50/120d 高波动右尾目标方向相反 |

### 5.1 Primary estimand caveat

一个必须正面记录的 finding：

```text
19A 冻结的 primary_tail_lift_50 目前不是跨 family 完全统一的 estimand。
```

原因是 19A 的默认 matching 已经控制了部分协变量（例如 amount 与 recent_20d_return），
而这些字段对 B1/B5 属于规则信号的一部分或信号确认变量。因此 B1/B5 的
`primary_tail_lift_50` 更接近：

```text
residual lift after controlling part of the family signal exposure
```

但对没有把这些字段作为核心 predicate 的 family，同名指标更接近：

```text
total lift versus the frozen matched baseline
```

这不是 19B0.1 内部调参能完全修掉的问题，而是 19A freeze 需要澄清的 contract
问题：下一版 requirement 必须声明每个 family 的 primary estimand 是
`total_vs_neutral_baseline`、`residual_after_partial_signal_control`，还是
`attribution_only_after_signal_control`。否则不同 family 的同名
`primary_tail_lift_50` 会被错误横向比较。

## 6. Repair priority

### Priority 0: baseline repair

必须先修 baseline，否则所有依赖 matched baseline 的 lift 都不能归因。但 baseline
修复不能使用一套全局固定的 "confounder list" 机械套到所有 family。每个 family
必须先声明自己的 signal primitives；只有**不属于该 family signal primitive** 的字段，
才可作为默认 primary baseline 的卫生控制。否则 baseline 会把该 family 的 edge 按构造
定义掉。

Baseline 修复必须严格区分两种本质不同的操作，不得混为一谈：

```text
A. 中和 confounder（合法 baseline 卫生，作为默认 primary baseline）：
   只匹配与该 family signal primitive 无关的混淆维度。
   目标是把时间 / 股票 / 市值 / 非信号流动性 / 非信号波动 / 非信号普通动量暴露中和掉。
   这组必须与 19A 冻结的 baseline_matching_spec 一致。

B. 条件化于信号的 ablation（attribution-only，非默认 primary baseline）：
   额外匹配该 family 的 signal primitives，回答的是：candidate 在剪除自身信号暴露后
       是否还有 residual tail lift。
```

Signal/control locking rule（反操纵规则）：

```text
1. signal primitives must equal exactly the feature_fields that appear in the
   frozen family predicate_formula.
2. Any covariate controlled by 19A that does not appear in that predicate_formula
   remains a controlled confounder by default.
3. A researcher may not reclassify an unfavorable balance covariate as "signal"
   after looking at outcome or matching readouts.
4. The predicate_formula, feature_fields, signal primitive list, default controls,
   and attribution-only controls must be frozen before any outcome readout.
5. If a future family rewrite changes predicate_formula, it creates a new
   family_version_id and cannot silently reuse the old signal/control map.
```

Family-specific signal/control map:

| family | signal primitives in current / proposed rule | default primary baseline controls | attribution-only controls |
|---|---|---|---|
| B2_relative_strength_breakout | `stock_vs_market_20d`, `return_60d_rank`, `close_to_ema60` | calendar, instrument, market cap, non-signal liquidity, non-signal volatility; raw `return_20d` remains a confounder because B2's signal is relative strength / 60d rank / EMA position, not raw 20d return | `stock_vs_market_20d`, `return_60d_rank`, `close_to_ema60` |
| B1_near_120d_high_plus_volume_expansion | near/breakout high, amount expansion, return/confirmation fields | calendar, instrument, market cap, volatility; amount/recent-return controls imply residual-not-total B1 estimand | amount expansion, return confirmation, breakout/near-high primitives |
| B5_recent_high_close_plus_amount_expansion | `return_10d`, close position in 120d range, amount expansion | calendar, instrument, market cap, volatility; amount/recent-return controls imply residual-not-total B5 estimand | `return_10d`, close position, amount expansion |
| B6_low_drawdown_reclaim_or_ema_reclaim | market repair, EMA reclaim, short-term reclaim return | calendar, instrument, market cap, liquidity, volatility not used as reclaim primitive | market repair, `close_to_ema60`, reclaim return |
| B4_volatility_contraction_then_breakout | prior compression and proposed current expansion/breakout | calendar, instrument, market cap, liquidity; volatility controls depend on whether testing compression or expansion | ATR/range compression, expansion trigger, breakout trigger |
| EP07_topn_multichannel_recommended_union | unknown until channel decomposition | calendar, instrument, market cap, broad liquidity/volatility only as diagnostic | channel-specific primitives after decomposition |

Current 19A baseline already matches amount and recent 20d return. Therefore B1/B5 readouts in
19B0 are best interpreted as **residual lift after controlling part of their own signal exposure**,
not total edge of "volume + recent strength" as a full strategy concept. Next requirement must name
the estimand explicitly before changing baseline keys.

关键纠正（本轮原文错误方向）：

```text
1. 不得把 stock_vs_market_20d / return_60d_rank / close_to_ema60 加进默认 baseline。
   这些变量就是 B2 的信号本身；把 baseline 匹配到信号上会按构造把 lift 定义掉，
   任何"edge 就是相对强势"的 family 都会得到 ≈1.0 的假 null。
2. 信号变量匹配只能出现在明确标注 attribution 的 B2 ablation（Priority 1）里，
   不能冒充 19A 冻结的 primary tail-lift 指标。
```

合规路径（必须二选一并写明）：

```text
19B0 禁止修改 19A 冻结的 baseline_matching_spec（见 19B0 §4 forbidden #4）。
因此：
(a) 若要改变默认 matching keys（例如加入 A 组中 19A 未含的维度），
    必须先正式修订 19A，发布 baseline_matching_spec v2；或
(b) 保持 19A 冻结的 A 组不变，把 B 组作为独立的、明确标注 attribution-only 的
    ablation readout，不当作 primary 结论。
```

Required changes:

```text
1. 默认 baseline 只补 family-specific confounder 桶（A 组），不含该 family 的信号变量。
2. output per-feature SMD, not only max SMD（当前输出只有 max SMD）。
3. test coarser bucket / caliper / nearest-neighbor matching，
   并同时报告 unmatched_candidate_rate 的变化。
4. 预注册 matching-repair sweep 后再判断
   "max_SMD<=0.10 与 unmatched<=0.05 是否联合不可满足"：
   对极端切分候选，可能不存在同时过两门的 matched baseline；
   但该结论必须由 sweep 结果支持，不能由本轮单次失败直接断言。
5. keep train-only boundary。
```

### Priority 1: B2 ablation and baseline repair

Goal:

```text
Determine whether B2 has residual tail lift after matching away
stock_vs_market_20d, return_60d_rank, close_to_ema60, amount, volatility,
and recent return exposure.
```

定性声明（必须写入报告）：

```text
B2 ablation 是 attribution-only，不是 19A 冻结的 primary tail-lift。
它回答的是"B2 是否有超出通用动量 / 相对强势暴露的额外 edge"，
而不是"B2 相对中性 baseline 是否富集"。两个 estimand 不可互相替代。
如果 B2 在剪除信号暴露后 residual lift 归零，也不意味着 B2 无价值；
只意味着 B2 的价值与通用动量暴露不可分。
```

Required cells:

```text
B2a: stock_vs_market_20d only
B2b: return_60d_rank only
B2c: stock_vs_market_20d + return_60d_rank
B2d: B2c + close_to_ema60
B2e: B2c + market regime
```

### Priority 2: B5 sharpened trend-continuation scan

Repair:

```text
return_10d_min = 0.06 / 0.10 / 0.12 / 0.15
stock_vs_market_20d_min = 0.05 / 0.10
return_60d_rank_pct_min = 0.70 / 0.80
amount_ratio_20d_min = 1.2
```

B5 should be tested as trend-continuation secondary source, not as a broad standalone family.

### Priority 3: B1 breakout confirmation rewrite

Repair:

```text
replace near_high with actual breakout / reclaim
add close-in-range confirmation
add relative strength
keep volume as confirmation only
```

B1 should become a breakout confirmation family. It should not remain generic near-high + volume.

### Priority 4: EP07 channel decomposition

Repair:

```text
split EP07 union by channel/source
evaluate each channel as its own family
find whether any sub-channel has right-tail enrichment
```

If channel decomposition still shows no residual lift under repaired matching,
EP07 union should remain recall reservoir only.

### Priority 5: B6 downgrade to regime/filter

Repair:

```text
use B6 as market/participation filter for B2/B5
or require relative reclaim vs market
```

B6 should not be promoted as primary family unless it survives repaired matched
baseline after relative strength controls.

### Priority 6: B4 rewrite or remove

Repair:

```text
replace low-vol entry with volatility spring:
    prior compression
    current expansion
    close breakout
    amount expansion
```

If not rewritten, B4 should be removed from primary right-tail scan and possibly reused only as left-tail / false-positive filter.

## 7. Search space decision

下一步需要增加搜索空间，但不能简单扩大当前网格。当前 19B0 的失败不是
`grid_cell_n` 太少，而是两个更基本的问题：

```text
1. baseline quality 全部失败，matched-baseline tail lift 无法归因。
2. 部分 family 的机制方向和 +50 / 120d 标签结构不匹配，或 family 太宽导致信号稀释。
```

因此搜索空间应以 **baseline repair + 机制重构 + family ablation** 的方式增加，而不是
把每个 family 的参数轴机械扩展。简单把 36 个 cell 扩到更多 cell 会提高 train-adaptive
search 和 winner's curse 风险，但不一定解决归因问题。

必须新增的搜索空间：

```text
1. Baseline repair search
   - per-feature SMD
   - coarser bucket sweep
   - caliper / nearest-neighbor matching
   - common-support diagnostics
   - family-specific signal/control map

2. B2 ablation search
   - stock_vs_market_20d only
   - return_60d_rank only
   - stock_vs_market_20d + return_60d_rank
   - with / without close_to_ema60
   - with / without market regime

3. B5 sharpening search
   - return_10d_min = 0.06 / 0.10 / 0.12 / 0.15
   - add stock_vs_market_20d_min
   - add return_60d_rank_pct_min
   - keep amount as lightweight confirmation, not an ever-higher threshold

4. B1 rewrite search
   - actual 120d high breakout
   - close in upper daily range
   - breakout hold / reclaim
   - relative strength confirmation
   - volume as confirmation only

5. B4 replacement search
   - remove current low-vol primary entry
   - test volatility spring:
       prior compression
       current range expansion
       volume expansion
       close breakout

6. EP07 channel split
   - split union by source/channel
   - evaluate each channel separately
   - keep union only as diagnostic / recall reservoir until channel evidence is known

7. B6 interaction search
   - do not expand B6 as independent primary family first
   - test B6 as regime/filter interaction for B2/B5
   - require relative reclaim if keeping B6 as candidate family
```

不建议新增的搜索空间：

```text
1. Blindly expanding all existing parameter axes.
2. More near-high / amount thresholds without relative-strength primitives.
3. More low-volatility contraction cells for B4 under the current +50 / 120d label.
4. More broad EP07 union variants without channel decomposition.
5. More B6 standalone reclaim cells before baseline repair.
```

Search accounting requirements:

```text
1. 所有新增 / 重写的 primary-claim family 和 primary-claim cells 必须进入
   primary all-tried-cells accounting。
2. attribution-only ablation cells 必须进入独立的 attribution all-tried accounting，
   但不得混入 primary family-level correction，除非该 cell 被允许产出 primary claim。
3. 必须重新冻结 N_family_cap、grid_total_cells、primary family-level correction、
   primary cell-level correction、attribution-ablation correction scope 和 selected-cell rule。
4. 必须显式标记 train-adaptive search，因为这些新增空间来自 19B0 train 失败后的诊断。
5. 必须增加 winner's-curse / shrinkage 处理；否则 train 上最接近的 B2-like cell
   很容易被过度解释。
6. 如果新增 primary-claim family 超过 19A 冻结 cap，必须先修订 19A 或在 19B0.1
   中降低/合并 primary family；attribution-only cells 需要单独 cap，不得挤占
   primary family cap。
```

Decision rule:

```text
Search space should expand only if it reduces one of these failure modes:
    baseline imbalance
    signal primitive ambiguity
    family over-breadth
    label-mechanism mismatch

Search space should not expand merely to find a passing train cell.
```

## 8. Proposed next requirement

Recommended next artifact:

```text
requirement_19b0_1_baseline_repair_and_family_ablation_scan.md
```

Scope:

```text
1. repair matched baseline quality on train only，仅补 family-specific confounder 桶；
   不把该 family 的 signal primitives 加进默认 baseline。amount/波动/近期收益是否可控
   必须由 family signal/control map 决定，不能全局硬编码
2. add B2 ablation cells（信号变量匹配，明确标注 attribution-only）
3. sharpen B5 and rewrite B1
4. downgrade B6 / decompose EP07 / rewrite B4
5. no robustness or validation outcome read
6. no model, no policy, no backtest, no trading authorization
7. 先确定合规路径：若默认 matching keys 需变动，先修订 19A 发 baseline_matching_spec v2；
   否则保持 19A 冻结不变，信号匹配仅作 attribution ablation
8. 重新冻结 search accounting：新增/重写的 primary-claim family（B1/B4 重写、
   B5 轴扩展、EP07 primary 通道拆分等）进入 primary multiple-testing correction；
   B2 attribution ablation cells 和其他 attribution-only cells 单独进入 attribution
   accounting，不混入 primary correction；并确认 primary 空间仍在 19A 的
   N_family_cap=10 / grid_total_cells<=300 内（或同步修订）
9. train-adaptive 声明：在看过 train 结果后迭代 family 属 train-adaptive search，
   winner's-curse / 收缩级别必须延伸到这些修复后的 family，才允许进入 19B robustness
```

Success condition:

```text
At least one family/cell passes:
    baseline_matching_quality_gate
    train_triage_pass
    denominator gate
    all three baseline families present

Only then may 19B robustness handoff become non-empty.
```

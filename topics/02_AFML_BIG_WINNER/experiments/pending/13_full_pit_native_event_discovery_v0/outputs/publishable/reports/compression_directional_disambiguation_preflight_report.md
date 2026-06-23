# 13A2 压缩态方向分辨预检报告

## 结论摘要

13A2 的裁决是：

```text
decision_state = 13A2_no_directional_filter_survives_stop_event_mining
sequence_mining_authorized = False
next_allowed_requirement = none
```

本轮不是因为输入、13A lineage、label lineage、base compression cohort 或 candidate grid 失败而停止。所有 lineage gate 均通过，18 个预注册 directional primitive 全部可用，candidate grid 完整展开为 162 个 filter，并且 readout / utility CI 已使用同一套 `instrument_month_block` bootstrap：500 resamples、500 valid replicates、`ci_status = pass`。

真正的停止原因是：在 train selection gate 中，没有任何 candidate 同时满足方向读数、utility 与 control comparability。最关键的瓶颈是 control quality：train split 的 162 个 candidate 中，`control_ok = 0`。因此，本轮不能从固定的 `volatility_20d__bottom_20pct` compression base 授权 13B sequence mining。

这不是 Episode 13 的全局终结。它只说明：在 13A 选出的 fixed compression base 内，当前预注册方向过滤器无法提供可审计、可比较、可部署的单尾方向分辨。

## 数据边界与可复现性

13A2 固定继承 13A 的 native opportunity universe 与 selected compression state：

```text
base_compression_state =
  native_scope
  AND volatility_20d <= 13A train-frozen bottom_20pct threshold

threshold_value = 0.016023
threshold_source_token_id = volatility_20d__bottom_20pct
cost_buffer_return = 0.01
```

Base cohort 规模如下：

| split | native_n | base_n | base_coverage | winner_rate | lower_first_rate | fast_fail_rate | utility_per_entry |
|---|---:|---:|---:|---:|---:|---:|---:|
| all | 408715 | 111299 | 27.23% | 20.05% | 40.43% | 12.25% | -1.02% |
| train | 216794 | 43359 | 20.00% | 23.01% | 43.03% | 13.58% | -0.83% |
| validation | 61307 | 21170 | 34.53% | 14.98% | 48.19% | 13.04% | -2.01% |
| robustness | 130614 | 46770 | 35.81% | 19.61% | 34.49% | 10.65% | -0.75% |

这个表再次确认 13A 的核心问题：compression 不是单尾好事件，而是双尾/左尾压力很强的状态。尤其 validation 的 base lower-first rate 达到 48.19%，utility per entry 为 -2.01%。所以 13A2 的任务不是证明 compression 本身好，而是在 compression 内寻找能把右尾和左尾分开的方向过滤器。

## Feature 与 Candidate Grid

本次 full rerun 后，所有预注册 primitive 均可用：

| family | primitive_n | availability |
|---|---:|---|
| relative_strength | 5 | all available |
| range_position | 4 | all available |
| drawdown_exclusion | 4 | all available |
| participation | 5 | all available |

候选网格完整展开：

| candidate_type | family / pair | candidate_n |
|---|---|---:|
| single_filter | relative_strength | 20 |
| single_filter | range_position | 16 |
| single_filter | drawdown_exclusion | 16 |
| single_filter | participation | 20 |
| two_filter_conjunction | relative_strength + range_position | 18 |
| two_filter_conjunction | relative_strength + drawdown_exclusion | 18 |
| two_filter_conjunction | relative_strength + participation | 18 |
| two_filter_conjunction | range_position + participation | 18 |
| two_filter_conjunction | drawdown_exclusion + participation | 18 |
| total | all | 162 |

新增的 qfq-derived primitive 改变了 grid 的覆盖面：`close_vs_sma20`、`higher_low_slope_10d`、`volume_up_price_not_down_5d`、`amount_ratio_5d_20d`、`up_day_volume_share_20d`、`money_median_5d_vs_20d` 均从 reference-date 可见 rolling window 构造，不再被错误标记为 unavailable。

## Train Selection Gate 分解

Train gate 的逐项通过数量：

| train criterion | pass_n / 162 |
|---|---:|
| treated_n >= 1000 | 162 |
| treated_positive_n >= 100 | 162 |
| winner_rate_diff > 0 | 149 |
| AUC >= 0.55 | 60 |
| lower_first_uplift <= 0.02 | 103 |
| utility_proxy_per_entry > 0 | 9 |
| control_match_quality != insufficient_control | 0 |
| all train criteria pass | 0 |

这说明样本量不是问题，positive support 也不是问题。方向信号也不是完全不存在：149/162 个 candidate 在 train 上 winner diff 为正，60/162 个 AUC 达到 0.55，9 个甚至 train utility per entry 为正。但没有一个 candidate 能提供可接受 control quality。

Top train candidates：

| filter_id | family | treated_n | positive_n | winner_diff | AUC | lower_uplift | utility | control_quality | ratio | max_smd |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| distance_from_20d_low top30 AND turnover_zscore_20d top30 | range + participation | 6232 | 1926 | +9.22pp | 0.569 | -3.00pp | +0.30% | insufficient | 5.96 | 0.701 |
| close_vs_sma20 top30 AND turnover_zscore_20d top30 | relative + participation | 6974 | 2131 | +8.99pp | 0.570 | -2.36pp | +0.17% | insufficient | 5.22 | 2.055 |
| close_position_20d top30 AND turnover_zscore_20d top30 | range + participation | 6876 | 2080 | +8.60pp | 0.567 | -2.10pp | +0.09% | insufficient | 5.30 | 0.918 |
| distance_from_20d_low top40 AND turnover_zscore_20d top40 | range + participation | 9815 | 2898 | +8.42pp | 0.569 | -2.01pp | +0.05% | insufficient | 3.42 | 0.683 |
| distance_to_20d_high top30 AND turnover_zscore_20d top30 | range + participation | 6667 | 2004 | +8.33pp | 0.565 | -2.21pp | +0.02% | insufficient | 5.50 | 0.950 |

这些读数很有研究信息量：它们显示“区间位置/均线强度 + 参与度改善”确实能在 compression 内挑出 winner-rate 更高、lower-first 更低的一批样本。但这些样本相对 compression control 的形态/流动性分布偏移过大，`max_standardized_diff_after_match` 远高于 primary gate 的 0.25，也高于 caveat gate 的 0.50。因此这些 candidate 是“看起来有效但不可比较”的 cohort slice，不能作为可部署方向事件。

## Validation 与 Robustness 读数

逐 split 的主要统计：

| split | candidates | diff>0 | AUC>=0.55 | lower_uplift<=0 | fast_fail_uplift<=0.01 | utility>0 | control_ok |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 162 | 149 | 60 | 65 | 148 | 9 | 0 |
| validation | 162 | 162 | 142 | 159 | 162 | 0 | 0 |
| robustness | 162 | 158 | 6 | 114 | 135 | 0 | 3 |

Validation 看起来最强：几乎所有 filter 都有 positive winner uplift，142 个 AUC 达到 0.55，159 个 lower-first 不增加。但 validation 的 utility 全部不为正，control quality 也全部不合格。换句话说，validation 有强烈的 directional ranking 迹象，但没有转成 cost-adjusted utility，也没有形成可审计 control。

Robustness 更保守：158 个 diff>0，但只有 6 个 AUC 达到 0.55，utility 仍全部不为正。只有 3 个 robustness rows 达到 `coarsened_caveat`，且全部不在 train/validation 同时成立，无法进入 selection 或 final authorization。

Validation 中 winner diff 最大的候选：

| filter_id | treated_n | winner_diff | CI low | AUC | lower_uplift | utility | control_quality | max_smd |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| ret_60d top30 AND volume_up_price_not_down_5d top30 | 3345 | +10.00pp | +7.87pp | 0.619 | -12.11pp | -0.52% | insufficient | 1.228 |
| ret_60d top50 | 14202 | +9.60pp | +8.05pp | 0.617 | -18.59pp | -1.32% | insufficient | 0.657 |
| ret_60d top40 AND volume_up_price_not_down_5d top40 | 5360 | +9.54pp | +7.74pp | 0.619 | -11.56pp | -0.75% | insufficient | 1.143 |
| ret_60d top30 AND amount_ratio_5d_20d top30 | 2698 | +9.40pp | +6.85pp | 0.606 | -12.79pp | -0.48% | insufficient | 1.303 |
| ret_60d top40 | 12109 | +9.29pp | +7.73pp | 0.617 | -16.52pp | -1.18% | insufficient | 0.613 |

Robustness 中 winner diff 最大的候选：

| filter_id | treated_n | winner_diff | CI low | AUC | lower_uplift | utility | control_quality | max_smd |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| max_drawdown_20d top30 AND amount_ratio_5d_20d top30 | 5356 | +6.49pp | +4.74pp | 0.551 | -1.21pp | -0.14% | insufficient | 1.135 |
| max_drawdown_60d top50 | 27253 | +6.42pp | +4.64pp | 0.549 | -7.01pp | -0.33% | insufficient | 0.392 |
| max_drawdown_20d top30 AND turnover_zscore_20d top30 | 5073 | +5.98pp | +4.58pp | 0.553 | -0.28pp | -0.26% | insufficient | 1.165 |
| distance_to_60d_low top30 AND amount_ratio_5d_20d top30 | 5904 | +5.93pp | +4.20pp | 0.546 | -1.75pp | -0.03% | insufficient | 1.120 |
| distance_to_20d_high top40 AND turnover_zscore_20d top40 | 9608 | +5.69pp | +4.47pp | 0.551 | -1.87pp | -0.22% | insufficient | 0.937 |

这里的 insight 很重要：validation 最强候选大量来自 `ret_60d` / drawdown family，robustness 最强候选也大量来自 drawdown / range + participation。它们更像是在 compression 内继续切出“反弹/修复/参与度改善”状态，而不是形成独立、平衡、可比较的方向事件。

## Control Quality 审计

Control quality 的完整分布：

| split | primary_comparable | coarsened_caveat | insufficient_control |
|---|---:|---:|---:|
| train | 0 | 0 | 162 |
| validation | 0 | 0 | 162 |
| robustness | 0 | 3 | 159 |

仅 3 条 robustness row 达到 `coarsened_caveat`：

| filter_id | treated_n | control_n | ratio | max_smd | coarsening |
|---|---:|---:|---:|---:|---|
| max_drawdown_60d top20 | 14382 | 31577 | 2.20 | 0.355 | level_2 |
| turnover_zscore_20d top30 | 12313 | 34447 | 2.80 | 0.458 | level_2 |
| turnover_zscore_20d top20 | 7953 | 38791 | 4.88 | 0.483 | level_2 |

这些 caveat 只出现在 robustness，不出现在 train 和 validation，所以无法作为 train-selected filter 的稳定证据。更重要的是，当前最强 train/validation 候选虽然 effective control ratio 通常不低，但 max SMD 过高，说明 treated 与 control 在 compression severity、liquidity 或 non-self directional decile 上仍然不平衡。

因此，本轮 fail-closed 是正确行为：如果忽略 control quality，会把“更强反弹/更高参与度/更靠近区间上沿”的结构性偏移误读为 PIT-safe directional edge。

## Utility 与 Bad-side

13A2 的 primary gate 不是 AUC，而是 bad-side / utility。当前数据说明：

1. Train 中只有 9/162 个 candidate 的 `utility_proxy_per_entry > 0`。
2. Validation 与 robustness 中 `utility_proxy_per_entry > 0` 的 candidate 数均为 0。
3. 许多 validation candidate 能显著降低 lower-first，但仍无法覆盖 `cost_buffer_return = 1%`。
4. Robustness 的 AUC 和 utility 同时弱化，说明 train/validation 中的强方向读数不够稳定。

最典型的例子是 validation 的 `ret_60d top30 AND volume_up_price_not_down_5d top30`：winner diff 达 +10.00pp，lower-first uplift 为 -12.11pp，但 utility 仍为 -0.52%，control SMD 为 1.228。它是一个很强的 diagnostic slice，但不是可部署 filter。

## Search / Deployability / Morphology

由于没有任何 train candidate 通过 selection gate，本轮没有 selected filter，因此：

```text
compression_directional_morphology_audit.csv: empty with schema
compression_directional_stability_audit.csv: empty with schema
compression_directional_deployability_gate_audit.csv: empty with schema
```

Search audit 仍记录了完整搜索面积：

| candidate_grid_n | effective_search_space_n | fdr_q_value | search_status |
|---:|---:|---:|---|
| 162 | 248 | 0.016218 | fail |

`search_status = fail` 的原因不是 FDR q-value，而是没有 selected filter，`deflated_auc_validation` 与 deflated utility margin 不可计算。这个状态符合 decision precedence：train 没有候选通过，就不能用 validation/robustness 的漂亮 diagnostic readout 反向选择。

## Findings

1. **Compression 内部确实存在方向排序信号，但它不是可审计 edge。**
   大量 candidate 在 validation 中 winner diff 为正，且 lower-first 明显下降。但这些读数主要来自 range/drawdown/participation 的结构性切片，control quality 不足。

2. **最强方向读数来自“位置修复 + 参与度改善”，不是单纯低波动。**
   Train top candidates 集中在 `distance_from_20d_low`、`close_vs_sma20`、`close_position_20d` 与 `turnover_zscore_20d` 的 conjunction。这说明压缩态中，靠近区间上沿且成交参与恢复的股票更容易先上破。

3. **但这些状态同时改变了 denominator。**
   Top candidates 的 effective control ratio 并不低，但 max SMD 显著超标。也就是说，问题不是“找不到 control 数量”，而是“找不到足够相似的 control”。这正是 13A2 需要 fail closed 的地方。

4. **Cost buffer 是关键杀伤项。**
   即使 validation 中 winner diff 和 lower-first 改善都很强，utility 仍全部不为正。这个结果说明 compression 内方向过滤器的收益幅度不足以抵消 1% cost buffer。

5. **13A2 不支持进入 13B。**
   如果继续做 sequence mining，会在一个已经 control-unstable、utility-negative 的 cohort 上寻找序列结构，风险是把 morphology/participation 切片过拟合成事件路径。

## Insight

13A 发现 compression 是双尾放大器；13A2 进一步说明：在 compression 内，方向性信息不是没有，而是“可解释但不可授权”。最强的方向过滤器都在描述一种更具体的市场状态：

```text
低波动压缩
+ 价格位置不弱 / 远离低点 / 接近均线或区间上沿
+ 参与度恢复
```

这类状态很像“压缩后的修复/反弹准备态”。它能提高 upper-first 概率，也能降低 lower-first 概率，但它不是独立、平衡、可比较的方向事件。换句话说，13A2 找到的是研究线索，不是 13B 的可部署入口。

下一步如果继续 Episode 13，不建议在当前 compression base 上做 sequence mining。更合理的选择是另开 requirement，重新固定一个不同的 base state，或者把本轮 top diagnostic slices 当作 morphology/participation 假说，先做 denominator-balanced feasibility audit，而不是直接进入事件序列挖掘。

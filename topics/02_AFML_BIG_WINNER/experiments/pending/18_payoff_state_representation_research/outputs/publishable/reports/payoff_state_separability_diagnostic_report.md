# 18C Payoff-state Separability Diagnostic Report

## 结论

18C 的最终状态是：

```text
decision_state = 18C_payoff_state_signal_weak_or_nonmonotone
next_allowed_requirement = none
all_hard_gates_pass = false
```

当前 18B 的 23 个 PIT-valid、t0-available 特征可以形成一个弱的 payoff 排序信号，但没有达到 18C 对 18D 的严格放行标准。核心原因有两个：

1. robustness payoff rank IC = `0.064398`，低于预设硬门槛 `0.080000`，因此 `rank_ic_support_gate = fail`。
2. 相比同口径 volatility20d defense baseline，rank IC 差值为 `-0.000374`，没有超过 `+0.005000` 的同口径改进要求，因此 `baseline_improvement_gate = fail`。

其他关键边界均通过：18B handoff、输入审计、18A target/cutoff replay、模型注册、train-only fit、bootstrap CI、bucket lift、binary sanity boundary、search accounting 均为 pass。18C 仍是诊断阶段，不授权 entry/exit/holding policy、portfolio backtest、model deployment、production signal 或 live trading。

## 核心读数

| metric | value | gate | interpretation |
|:--|--:|:--|:--|
| robustness payoff rank IC | 0.064398 | fail | 有正相关，但低于 0.080000 materiality floor |
| rank IC materiality floor | 0.080000 | threshold | 18D 放行硬门槛 |
| robustness decile monotonicity | 0.612121 | pass | decile 均值有一定单调结构 |
| robustness top3-bottom3 payoff gap | 0.020020 | pass | 高分 decile 平均 payoff 高于低分 decile |
| bootstrap CI low | 0.020608 | pass | episode-cluster bootstrap 下 rank IC 下界大于 0 |
| rank IC vs volatility20d delta | -0.000374 | fail | 未跑赢同口径风险防御 baseline |
| coarse delta vs 16X external | 0.012521 | context only | 16X 非同口径，仅作为外部上下文 |

## 数据和合同回放

输入审计覆盖 40 个必需 artifact，全部满足读取、schema 和 key/hash reconciliation 要求。18B handoff 决策为 `18B_payoff_state_feature_matrix_ready`，并且 `next_allowed_requirement = requirement_18c_payoff_state_separability_diagnostic.md`。

18C 使用的 labelable_full 分母如下：

| split | labelable rows | neutral rows | episode clusters |
|:--|--:|--:|--:|
| train | 20,245 | 5,283 | 652 |
| robustness | 2,496 | 624 | 204 |
| validation | 664 | 159 | 41 |

18A target/cutoff replay 均通过：

| check | observed |
|:--|:--|
| target lineage hash | `602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3` |
| identity key | `step_id|label_id` |
| full lineage key duplicate n | 0 |
| neutral reclassified as positive/negative | false |
| continue_advantage affine replay max abs diff | 0.0 |
| top30 payoff cutoff | 0.0596330275229357 |
| top20 payoff cutoff | 0.1012285086722715 |
| top10 payoff cutoff | 0.1721071844362347 |
| split-local payoff cutoff recompute used | false |

`continue_advantage` 是 `y_payoff_h20 + 0.005` 的仿射回放，因此 rank IC 与 payoff rank IC 完全一致；它不是独立证据。

## 模型和 OOS 排序

primary model 为 `ridge_payoff_rank_h20_v1`，只在 train split 拟合，使用 18B 产出的 23 个 model-ready features。robustness 和 validation 只做 train-fitted score replay，不做阈值重调或模型选择。

| split | rows | clusters | rank IC | continue_advantage IC | status |
|:--|--:|--:|--:|--:|:--|
| train | 20,245 | 652 | 0.131214 | 0.131214 | train_in_sample |
| robustness | 2,496 | 204 | 0.064398 | 0.064398 | fail |
| validation | 664 | 41 | 0.063768 | 0.063768 | stress_readout_only |

解释：

- train IC = `0.131214`，robustness IC = `0.064398`，出现明显 OOS 衰减。
- validation IC = `0.063768` 与 robustness 接近，但 validation 在 18C 中只是 stress readout，不参与调参或放行。
- robustness IC 为正且 bootstrap 下界为正，说明信号不是纯噪声；但它没有达到 18D 所需的强度，也没有跑赢同口径 volatility baseline。

## Decile 结构

robustness 使用 train-frozen score deciles，未做 split-local decile 重算。decile 均值如下：

| decile | row_n | mean payoff | mean score |
|--:|--:|--:|--:|
| 1 | 182 | 0.013006 | -0.008553 |
| 2 | 96 | 0.031419 | 0.007421 |
| 3 | 118 | 0.020409 | 0.011743 |
| 4 | 134 | 0.045835 | 0.015148 |
| 5 | 186 | 0.027813 | 0.018049 |
| 6 | 224 | 0.038751 | 0.020710 |
| 7 | 315 | 0.031762 | 0.024067 |
| 8 | 382 | 0.042105 | 0.028090 |
| 9 | 439 | 0.036870 | 0.034436 |
| 10 | 420 | 0.040459 | 0.048399 |

| split | decile monotonicity | top3-bottom3 gap |
|:--|--:|--:|
| train | 0.939394 | 0.029471 |
| robustness | 0.612121 | 0.020020 |
| validation | 0.103030 | 0.015458 |

洞察：

- robustness decile monotonicity 刚好越过 0.60 门槛，说明排序方向整体可读。
- 但 decile 曲线不是严格平滑递增，例如 decile 4 的 payoff 高于后续多个 decile，decile 9/10 也没有继续显著抬升。
- 这更像一个弱的 broad payoff-state sorting signal，而不是可以直接桥接 oracle gap 的高置信 payoff-state representation。

## Bucket Lift

top-score bucket 使用 train-frozen score cutoff，不在 robustness/validation 上重算。

| split | bucket | row_n | base event rate | bucket event rate | lift | target |
|:--|:--|--:|--:|--:|--:|:--|
| train | score_top30_bucket | 6,074 | 0.300074 | 0.357425 | 1.191123 | top30_yes_no |
| train | score_top20_bucket | 4,049 | 0.200000 | 0.255866 | 1.279328 | top20_yes_no |
| robustness | score_top30_bucket | 1,241 | 0.341346 | 0.353747 | 1.036329 | top30_yes_no |
| robustness | score_top20_bucket | 859 | 0.234776 | 0.239814 | 1.021459 | top20_yes_no |
| validation | score_top30_bucket | 369 | 0.319277 | 0.308943 | 0.967633 | top30_yes_no |
| validation | score_top20_bucket | 269 | 0.218373 | 0.226766 | 1.038431 | top20_yes_no |

解读：

- robustness top30/top20 lift 均大于 1，bucket_lift_gate 通过。
- 但 lift 幅度很小：top30 lift 只有 `1.036x`，top20 lift 只有 `1.021x`。
- validation top30 lift 低于 1，说明 score bucket 对极端 payoff state 的稳定性不足。
- 这支持“有轻微信号”，但不支持把 score 当作强 payoff-state 分层器。

## Bootstrap 稳定性

episode_cluster_id bootstrap 结果：

| metric | value |
|:--|--:|
| point estimate | 0.064398 |
| CI low | 0.020608 |
| CI high | 0.106144 |
| bootstrap resamples | 2,000 |
| valid resamples | 2,000 |
| bootstrap seed | 20260629 |

洞察：

- CI low > 0，说明 rank IC 在 cluster bootstrap 下不是零附近随机波动。
- 但 CI 区间较宽，上界才达到 `0.106144`，下界只有 `0.020608`。
- 统计上可辨识的弱信号和研究上足够推进 18D 的强信号不是同一个标准；18C 当前属于前者。

## Baseline Boundary

同口径 hard baseline 只使用 `volatility20d_defense_baseline`。16X 是外部粗基准，不参与 `baseline_improvement_gate`。

| comparison | model value | baseline value | delta | required | hard gate | status |
|:--|--:|--:|--:|--:|:--|:--|
| payoff rank IC vs volatility20d | 0.064398 | 0.064772 | -0.000374 | 0.005000 | true | diagnostic_only |
| decile monotonicity vs volatility20d | 0.612121 | 0.139394 | 0.472727 | 0.000000 | false | diagnostic_only |
| payoff rank IC vs 16X external | 0.064398 | 0.051877 | 0.012521 | 0.000000 | false | external_context_only |
| monotonicity vs 16X external | 0.612121 | 0.163636 | 0.448485 | 0.000000 | false | external_context_only |
| bootstrap CI low vs 16X external | 0.020608 | 0.007706 | 0.012902 | 0.000000 | false | external_context_only |

关键判断：

- 与 16X 相比看起来更好，但 16X 的 denominator 是 winner-episode probe rows only，robustness 行数为 1,872；18C 是 labelable_full，robustness 行数为 2,496。两者不能作为 hard improvement claim。
- 与 volatility20d 同口径比较时，primary score 没有改进，反而低 `0.000374`。这就是 baseline_improvement_gate fail 的直接原因。
- risk_only_gate 仍然 pass，因为移除 F4 风险家族后 rank IC retention = `1.154419`，说明当前信号并非只靠 F4 风险防御特征支撑。

## 系数和敏感性

primary ridge 的 top standardized coefficients：

| rank | feature | family | standardized coefficient |
|--:|:--|:--|--:|
| 1 | mr_volume_20d_zscore | F2 | 0.030356 |
| 2 | mr_money_20d_zscore | F2 | -0.019799 |
| 3 | mr_max_drawdown_20d | F4 | -0.017676 |
| 4 | mr_turnover_rate_20d_mean | F2 | -0.014333 |
| 5 | mr_log_total_market_cap_cny | F5 | 0.010391 |
| 6 | mr_volatility_60d | F4 | -0.008486 |
| 7 | mr_distance_to_60d_high | F1 | 0.007941 |
| 8 | mr_ret_20d | F1 | 0.007902 |
| 9 | mr_turnover_rate_20d_zscore | F2 | -0.007437 |
| 10 | mr_ret_5d | F1 | -0.007365 |
| 11 | mr_max_drawdown_60d | F4 | -0.006641 |
| 12 | mr_board_rank_pct | F3 | 0.006345 |

robustness sensitivity：

| removal | sensitivity IC | retention |
|:--|--:|--:|
| top1 coefficient removed | -0.056304 | -0.874321 |
| top3 coefficients removed | 0.019902 | 0.309049 |
| top5 coefficients removed | -0.023142 | -0.359358 |
| F1 removed | 0.035943 | 0.558143 |
| F2 removed | 0.003798 | 0.058980 |
| F3 removed | 0.049548 | 0.769406 |
| F4 removed | 0.074342 | 1.154419 |
| F5 removed | 0.064419 | 1.000331 |

洞察：

- F2 participation/sponsorship 特征是当前弱信号的主要载体。移除 F2 后 rank IC 从 `0.064398` 降到 `0.003798`。
- 单个 `mr_volume_20d_zscore` 对 score 贡献很大，移除后 IC 变为负值。这提示当前 signal capacity 很集中，鲁棒性不够理想。
- F4 risk family 移除后 IC 反而升至 `0.074342`，说明当前失败不是“只学到了低波动/低风险防御”。真正问题是 payoff-state 信号强度不足，而不是风险代理污染单独解释全部结果。
- F5 regime/board/context 基本不改变 IC，说明当前 board/market-cap/tradability context 在这一低容量线性设定下不是主要信息源。

## Binary Sanity Appendix

binary 指标仅作 appendix，不参与 primary support gate，也不决定 next_allowed_requirement。

| model | target | denominator | robustness ROC AUC | AP | precision lift |
|:--|:--|:--|--:|--:|--:|
| ridge_logistic_top30_sanity_v1 | top30_yes_no | labelable_full | 0.522194 | 0.366358 | 0.025012 |
| ridge_logistic_top20_sanity_v1 | top20_yes_no | labelable_full | 0.541156 | 0.267793 | 0.033017 |
| ridge_payoff_rank_h20_v1 | binary_positive_negative | labelable_full | 0.475069 | 0.742543 | -0.007457 |
| 16c_ridge_logistic_bar_state_v1 | binary_positive_negative | binary_primary | 0.672220 | 0.818200 | 0.099183 |

解读：

- top30/top20 binary sanity 的 precision lift 为正，但 ROC AUC 只有 `0.52-0.54`，只是弱分类迹象。
- 16C binary continuation 在 binary_primary denominator 上更强，但它不是 18C 的 payoff-state primary gate，也不使用 labelable_full 的 neutral rows。
- 因此 18C 不应因为 binary appendix 表现而推进 18D。

## Findings

1. 18C 当前是“弱正信号、未达可推进强度”的状态。rank IC 和 bootstrap 都支持存在信息，但 rank IC 没有达到 materiality floor。
2. 失败不是输入合同问题。18B handoff、18A target/cutoff replay、identity key、neutral preservation 和 search accounting 全部通过。
3. 失败也不是简单的 risk-only 问题。F4 removal retention 为 `1.154419`，风险特征移除后并未破坏信号。
4. 主要瓶颈在 F1-F5 当前特征集合对 broad payoff state 的表达能力不足。F2 特征承担了过多解释力，信号集中且 OOS 强度不足。
5. decile monotonicity pass 但形态不够平滑，bucket lift pass 但幅度很小。这说明 score 可以做诊断排序，但不足以作为 18D oracle-gap bridge 的基础表示。

## Research Insight

18C 的结果更接近“participation-driven weak payoff proxy”，而不是“完整 payoff-state representation”。这对后续研究方向有两个含义：

1. 如果目标是推进 18D，需要补充能表达 payoff morphology 的 t0 feature，而不是直接在现有 23 个特征上提高模型复杂度。当前最强来源是成交/资金参与度，缺少对结构性上行空间、供给压力、形态修复质量和 episode 内位置的更直接表达。
2. 如果保持现有 F1-F5 特征集合，它更适合降级为 meta-label 或 participation filter 的候选，而不是作为 payoff-state score 主干。也就是说，它能帮助识别“某些参与结构更可能对应较好 payoff”，但不能稳定区分完整 payoff ordinal state。

## Handoff

因为 `decision_state != 18C_payoff_state_separability_supported`，18D 不可启动。

允许的下一步不是 oracle-gap bridge，而是回到 feature representation research：优先研究新的 t0 payoff morphology feature、episode-local shape feature、或不依赖 delayed outcome 的 state abstraction，再重新做 18B/18C 合同链路。

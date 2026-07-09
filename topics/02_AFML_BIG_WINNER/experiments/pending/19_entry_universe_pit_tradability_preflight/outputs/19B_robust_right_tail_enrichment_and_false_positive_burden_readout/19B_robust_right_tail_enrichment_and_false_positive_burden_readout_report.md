# 19B 稳健右尾富集与假阳性负担读出报告

## 0. 执行结论

本次 19B 只评估 19B0 已冻结并交接的两个 selected family/cell：`B2_relative_strength_breakout` 与
`B5_recent_high_close_plus_amount_expansion`。19B 的问题不是“能不能训练策略”，而是：这些 entry
candidate 是否在 robustness split 上形成可交易、PIT 合法、fill-feasible 的右尾富集水库，并且右尾超额是否足以支付左尾损失和假阳性负担。

最终状态：

```text
decision_state = 19B_false_positive_burden_blocked
next_allowed_requirement = none
blocking_reason = false_positive_burden_blocked
```

解释为：B2 在 +50% forward MFE 口径上确实有正向 exposure，但这个 exposure 被左尾/假阳性负担和 top-k winner concentration 阻断；B5 在 +50% 口径上没有通过稳健 positive-exposure gate。因此 19B 没有给出 residual alpha 支持，也不允许进入 19B1 validation stress 或 19C replay。

边界仍然关闭：

- validation outcome read: `false`
- model / entry policy / exit policy / holding policy / portfolio backtest / production signal / live trading authorization: `false`
- 19C replay remains forbidden unless a later validation-stress requirement authorizes it.
- positive exposure persistence 不是 independent alpha。
- matched-baseline quality failure blocks residual-alpha support only.
- 19B 不授权 19C replay、EP20 policy preflight、entry policy、组合回测、production signal 或 live trading。

## 1. Contract 与样本边界

| 项目 | 结果 |
|---|---:|
| N_family_brought_to_robustness | 2 |
| N_tested_family_cell_pairs | 2 |
| robustness outcome rows loaded | 4,535 |
| validation outcome rows loaded | 0 |
| validation label value access | 0 |
| robustness outcome used to expand/drop survivors | false |
| upstream 19A contract gate | pass |
| upstream 19B0 contract gate | pass |
| output contract gate | pass |

Correction scope 保持冻结：

| scope | 值 | 含义 |
|---|---|---|
| positive_beta_exposure_correction_scope | `2 * positive_exposure_score_50` | B2/B5 两个 selected cells 都计入 positive exposure multiplicity |
| residual_alpha_correction_scope_19b0_frozen | `0 * primary_tail_lift_50` | 19B0 未授权 residual-alpha promotion |
| residual_style_readout_correction_scope_19b | `2 * primary_tail_lift_50` | 19B 只做 residual-style readout，不产生 policy |

## 2. Cell-level 结果

| family | candidate_n | instrument_n | p_candidate_50 | p_eligible_50 | delta | ratio | margin | score | p_value | Sidak alpha | positive pass | burden gate | top-k gate | cell state |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| B2 | 1,552 | 524 | 0.2803 | 0.2104 | 0.0698 | 1.3319 | 0.0421 | 0.0278 | 1.14e-07 | 0.0253 | true | fail | fail | false_positive_burden_blocked |
| B5 | 2,983 | 749 | 0.2270 | 0.2104 | 0.0165 | 1.0785 | 0.0421 | -0.0256 | 3.57e-02 | 0.0253 | false | fail | fail | robustness_not_supported |

关键读法：

- B2 的 +50% 候选命中率为 28.03%，高于 eligible universe baseline 的 21.04%，delta 为 6.98 个百分点，ratio 为 1.33。cluster bootstrap 给出的 delta CI 为 `[0.0448, 0.0970]`，p-value 为 `1.14e-07`，因此 B2 的 positive exposure 在统计上成立。
- B5 的 +50% 候选命中率为 22.70%，只比 eligible universe baseline 高 1.65 个百分点。其 p-value 为 0.0357，高于 Sidak alpha 0.0253，且 margin-adjusted score 为 -0.0256，因此不能判定为稳健右尾富集。
- 即使 B2 通过 positive exposure，cell_positive_exposure_gate 仍为 false，因为 false-positive burden gate 与 top-k gate 均失败。

## 3. Residual-style matched baseline 读出

| family | all original baseline quality | p_candidate_50 | calendar matched p50 | instrument matched p50 | LSV matched p50 | conservative p_matched_50 | primary_tail_lift_50 | margin-adjusted tail lift | residual pass | residual status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| B2 | fail | 0.2803 | 0.2139 | 0.3595 | 0.2706 | 0.3595 | 0.7796 | -0.3210 | false | diagnostic_only_original_frozen_baseline_quality_failed |
| B5 | fail | 0.2270 | 0.2032 | 0.3014 | 0.2642 | 0.3014 | 0.7531 | -0.3469 | false | diagnostic_only_original_frozen_baseline_quality_failed |

这里的 `LSV` 指 liquidity-size-volatility matched baseline。三类 original frozen baseline 没有一个达到质量门槛，所以 residual-style readout 只能作为 diagnostic，不能支持 residual alpha claim。

还有一个重要信号：保守 matched baseline 的 +50% 命中率反而高于 candidate。B2 的 conservative matched p50 为 35.95%，B5 为 30.14%，均高于各自 candidate p50。这不能被直接解释为“信号负 alpha”，因为 baseline quality 失败；但它说明当前 matched baseline 构造无法提供可靠的因果/残差归因，也不支持把 B2 的 eligible-universe exposure 升级为独立 alpha。

## 4. Baseline quality 与 repair sweep

质量门槛：

| 指标 | pass 条件 |
|---|---:|
| unmatched_candidate_rate | <= 0.05 |
| baseline_reuse_rate | <= 0.20 |
| max_standardized_mean_difference_after_matching | <= 0.10 |
| decision_month_coverage_delta | <= 0.02 |
| instrument_coverage_delta | <= 0.05 |

逐 variant 结果：

| family | variant | role | unmatched_rate | reuse_rate | max SMD | decision_month_delta | gate |
|---|---|---|---:|---:|---:|---:|---|
| B2 | original_calendar_time_random_same_budget | primary_original_frozen | 0.0947 | 0.0071 | 1.1168 | 0.0483 | fail |
| B2 | original_instrument_matched_random_same_budget | primary_original_frozen | 0.1424 | 0.0367 | 1.0583 | 0.0483 | fail |
| B2 | original_liquidity_size_volatility_matched_same_budget | primary_original_frozen | 0.4588 | 0.0528 | 0.7781 | 0.0483 | fail |
| B2 | repaired_lsv_return_cem_v1 | diagnostic_repair_only | 0.4588 | 0.0548 | 0.7847 | 0.0483 | fail |
| B2 | repaired_lsv_return_nn_caliper_v1 | diagnostic_repair_only | 0.0947 | 0.0084 | 1.1048 | 0.0483 | fail |
| B5 | original_calendar_time_random_same_budget | primary_original_frozen | 0.0922 | 0.0137 | 0.8955 | 0.0409 | fail |
| B5 | original_instrument_matched_random_same_budget | primary_original_frozen | 0.0721 | 0.0251 | 0.8297 | 0.0751 | fail |
| B5 | original_liquidity_size_volatility_matched_same_budget | primary_original_frozen | 0.3557 | 0.1338 | 0.5351 | 0.0409 | fail |
| B5 | repaired_lsv_return_cem_v1 | diagnostic_repair_only | 0.3557 | 0.1485 | 0.5236 | 0.0409 | fail |
| B5 | repaired_lsv_return_nn_caliper_v1 | diagnostic_repair_only | 0.0922 | 0.0178 | 0.8878 | 0.0409 | fail |

发现：

- 失败主因不是 baseline reuse，而是 common support 与 covariate balance。B2/B5 的 max SMD 全部远高于 0.10；B2 最低仍为 0.7781，B5 最低仍为 0.5236。
- LSV/return repair variants 没有修复质量问题。CEM repair 的 unmatched_rate 仍高，NN caliper repair 的 max SMD 仍高。
- 因此 19B 的结论只能停在 eligible-universe exposure 与 false-positive burden 读出，不能进入 residual-alpha 支持。

## 5. False-positive burden

| family | candidate_n | winner_n at +50 | non_winner_rate | candidate_per_winner | fast_fail_rate | false_repair_rate | MAE_20 p10 | eligible MAE_20 p10 | MAE worsening | cap | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| B2 | 1,552 | 435 | 0.7197 | 3.5678 | 0.4890 | 0.4890 | -0.2288 | -0.1361 | 0.0927 | 0.0200 | fail |
| B5 | 2,983 | 677 | 0.7730 | 4.4062 | 0.4653 | 0.4653 | -0.2063 | -0.1361 | 0.0702 | 0.0200 | fail |

这张表是本次结论的核心。两个 cell 的 candidate_per_winner 都没有超过 6.0，fast_fail_rate 和 false_repair_rate 也没有超过 0.60；真正致命的是 MAE left-tail worsening：

- B2 的 MAE_20 p10 比 eligible universe 差 9.27 个百分点，超过 2 个百分点 cap。
- B5 的 MAE_20 p10 比 eligible universe 差 7.02 个百分点，也超过 cap。

换言之，B2 虽然找到了更多 +50% 右尾事件，但同时带来了明显更厚的 20 日左尾。AFML 决策上，这不是可以直接推进 validation stress 的 entry alpha；更接近“右尾水库里混入了过多假阳性和左尾放大器”。

## 6. Top-k concentration 与 bootstrap

| family | top1 removed score | top3 removed score | max candidate share | max winner share | winner share cap | decision month max share | top-k gate |
|---|---:|---:|---:|---:|---:|---:|---|
| B2 | 0.0210 | 0.0116 | 0.0129 | 0.0368 | 0.0200 | 0.0741 | fail |
| B5 | -0.0292 | -0.0330 | 0.0064 | 0.0222 | 0.0200 | 0.1234 | fail |

B2 在移除 top1/top3 instrument 后 positive score 仍为正，说明 B2 exposure 不是完全由单一股票造成；但 max winner share 为 3.68%，超过 2% cap，因此仍被 concentration gate 阻断。B5 移除 top1/top3 后 score 直接转负，同时 max winner share 也超过 cap。

Bootstrap 读出：

| family | metric | estimate | SE | CI low | CI high | p-value | gate |
|---|---|---:|---:|---:|---:|---:|---|
| B2 | positive_exposure_delta_50 | 0.0698 | 0.0135 | 0.0448 | 0.0970 | 1.14e-07 | pass |
| B5 | positive_exposure_delta_50 | 0.0165 | 0.0092 | -0.0015 | 0.0341 | 3.57e-02 | pass as reproducible CI, but not robustness-pass |

`cluster_bootstrap_gate = pass` 表示 bootstrap 程序和 CI 可复现，不表示 B5 通过 positive exposure robustness。B5 的 CI 穿过 0，且 p-value 未过 Sidak alpha。

## 7. 图表解读

五张图均为 1440x1216 PNG，并进入 output hashes。其中前四张是 19B required figures；第 5 张是新增的 B2 右尾/左尾同步读图，用于直接回应右尾富集是否伴随左尾放大的问题。

### 7.1 `figures/tail_lift_curve.png`

这张图展示不同 MFE threshold 下 candidate 与 eligible universe baseline 的右尾命中率，以及 matched baseline quality pass 时应出现的 matched baseline 线。由于两个 cell 的 original frozen baseline quality 均 fail，matched baseline 线在图中为 diagnostic-only，不作为通过/失败依据。

| family | threshold | p_candidate | p_eligible | lift vs eligible |
|---|---:|---:|---:|---:|
| B2 | 0.20 | 0.6102 | 0.5595 | 1.0905 |
| B2 | 0.30 | 0.4723 | 0.3945 | 1.1973 |
| B2 | 0.50 | 0.2803 | 0.2104 | 1.3319 |
| B2 | 1.00 | 0.0941 | 0.0596 | 1.5788 |
| B5 | 0.20 | 0.5334 | 0.5595 | 0.9532 |
| B5 | 0.30 | 0.3932 | 0.3945 | 0.9969 |
| B5 | 0.50 | 0.2270 | 0.2104 | 1.0785 |
| B5 | 1.00 | 0.0774 | 0.0596 | 1.2997 |

图上最重要的模式是：B2 的 lift 随 threshold 上升而增强，具备“右尾越来越富集”的形态；B5 只有在 +50%/+100% 右尾段略高于 eligible baseline，但 +20%/+30% 不占优，整体形态不稳。

### 7.2 `figures/ccdf_survival_curve.png`

这张图使用 CCDF/survival 视角看同一批 threshold。读法是：横轴越往右，要求的 forward MFE 越高；纵轴表示超过该 threshold 的概率。

结论与 tail lift curve 一致，但视觉重点不同：

- B2 的 candidate survival 曲线在所有 threshold 上都高于 eligible universe，且 high-threshold 处优势更明显。
- B5 的 candidate survival 曲线在 +20%/+30% 几乎不优于 eligible universe，到 +50%/+100% 才出现小幅右尾优势。
- matched baseline 曲线没有成为可用证据，因为 baseline quality fail；图例中的 diagnostic-only 标注提醒 residual-style claim 不可用。

### 7.3 `figures/capture_vs_burden.png`

这张图同时展示 winner capture 与 burden。左轴是 capture/non-winner/fast-fail rate，右轴是 candidate_per_winner。它回答的问题不是“有没有右尾”，而是“为了拿到右尾，要付出多少假阳性和左尾”。

| family | threshold | winner_capture | non_winner_rate | candidate_per_winner | fast_fail_rate |
|---|---:|---:|---:|---:|---:|
| B2 | 0.20 | 0.6102 | 0.3898 | 1.6389 | 0.4890 |
| B2 | 0.50 | 0.2803 | 0.7197 | 3.5678 | 0.4890 |
| B2 | 1.00 | 0.0941 | 0.9059 | 10.6301 | 0.4890 |
| B5 | 0.20 | 0.5334 | 0.4666 | 1.8749 | 0.4653 |
| B5 | 0.50 | 0.2270 | 0.7730 | 4.4062 | 0.4653 |
| B5 | 1.00 | 0.0774 | 0.9226 | 12.9134 | 0.4653 |

B2 在 +50% 处仍有 28.03% winner capture，但同时 71.97% 是 non-winner，且 48.90% 触发 fast-fail。B5 的 +50% winner capture 更低，non-winner burden 更高。图上的核心启示是：提高右尾 threshold 会快速抬高 candidate_per_winner；当前规则不能把右尾富集和左尾负担分离开。

### 7.4 `figures/mfe_mae_joint_scatter.png`

这张散点图横轴是 `MAE_20`，纵轴是 `MFE_120`。竖线 `MAE_20 = -10%` 是 fast-fail 参考线，横线 `MFE_120 = +50%` 是 primary big-winner threshold。理想 entry filter 应该把点推向左上区域较少、右上区域较多；本次结果显示右上有增加，但左尾也明显加厚。

| family | row_scope | n | MFE mean | MFE median | MFE p90 | MAE mean | MAE p10 | fast_fail_rate | +50 winner_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B2 | candidate | 1,552 | 0.4287 | 0.2765 | 0.9629 | -0.1138 | -0.2288 | 0.4890 | 0.2803 |
| B2 | eligible sample | 1,552 | 0.3722 | 0.2422 | 0.7792 | -0.0633 | -0.1339 | 0.2049 | 0.2249 |
| B2 | matched diagnostic sample | 1,552 | 0.5584 | 0.3240 | 1.2859 | -0.0800 | -0.1692 | 0.3099 | 0.3595 |
| B5 | candidate | 2,983 | 0.3626 | 0.2211 | 0.8721 | -0.1046 | -0.2063 | 0.4653 | 0.2270 |
| B5 | eligible sample | 2,983 | 0.3610 | 0.2386 | 0.7805 | -0.0638 | -0.1349 | 0.2058 | 0.2189 |
| B5 | matched diagnostic sample | 2,983 | 0.4637 | 0.2956 | 1.0170 | -0.0724 | -0.1519 | 0.2652 | 0.3014 |

图形含义：

- B2 candidate 的右尾比 eligible sample 更强，但 MAE 明显更差：MAE p10 从 eligible 的 -13.39% 变成 -22.88%，fast_fail_rate 从 20.49% 升到 48.90%。
- B5 candidate 的 MFE mean 与 eligible sample 几乎相同，但 MAE 明显更差，说明 B5 更像噪声/波动放大，而不是稳定右尾水库。
- matched diagnostic sample 的 +50 winner_rate 更高，但因为 baseline quality fail，它只能提示“当前 matching 口径不可信”，不能反向证明 candidate 无效，也不能正向支持 residual alpha。

### 7.5 `figures/b2_right_left_tail_lift_balance.png`

这张新增图只看 B2，并把右尾 enrichment 与左尾 burden 放在同一坐标体系里。口径为 `candidate_primary_denominator` vs 等量抽样的 `eligible_universe_baseline_sample`，与 §7.4 的散点图一致；因此它是 diagnostic visual，不替代 §2 的全量 eligible-universe positive-exposure gate。

| threshold \|x\| | right-tail lift: `MFE_120 >= +x` | left-tail burden lift: `MAE_20 <= -x` |
|---:|---:|---:|
| 5% | 1.00 | 1.48 |
| 10% | 1.01 | 2.39 |
| 15% | 1.00 | 3.96 |
| 20% | 1.04 | 5.59 |
| 30% | 1.15 | 8.86 |
| 50% | 1.25 | n/a |
| 100% | 1.51 | n/a |

读法：

- B2 的右尾 lift 主要出现在更高 MFE threshold：+50% 右尾在等量 eligible sample 口径下为 1.25x，+100% 为 1.51x。
- 但左尾负担在更低 threshold 已经显著放大：-10% MAE event 为 2.39x，-20% 为 5.59x，-30% 为 8.86x。
- 所以 B2 不是“只抬右尾”的 filter，而是同时抬高右尾和左尾；并且左尾 burden lift 的幅度更大。这正是 §5 false-positive burden gate 阻断 B2 的可视化版本。

## 8. Findings 与研究判断

1. B2 是一个可继续研究的 morphology/participation filter 候选，但不是可推进 validation replay 的 alpha。它有稳健 eligible-universe 右尾 exposure，但没有通过 false-positive burden 与 top-k gate。
2. B5 在 19B robustness split 上没有足够 positive exposure。它的 +50 delta 小、margin-adjusted score 为负，且左尾负担同样超标。
3. baseline repair 当前没有解决 residual attribution。无论 original frozen baselines 还是 LSV/return repair variants，质量门槛均 fail。下一步若继续，应先研究 baseline construction/common support，而不是放宽 residual alpha 解释。
4. 本轮最强的负面证据来自左尾：B2/B5 的 MAE_20 p10 比 eligible universe 分别恶化 9.27 和 7.02 个百分点，远超 2 个百分点 cap。这说明右尾富集没有覆盖左尾成本。
5. 从 AFML 决策角度，当前终态应保持 `19_entry_universe_enrichment_only_diagnostic` 上限；不得进入 19C replay、EP20 policy preflight 或任何 production signal。

## 9. Artifact 索引

主要 CSV：

- `robustness_metric_readout.csv`
- `robustness_positive_exposure_readout.csv`
- `robustness_residual_alpha_readout.csv`
- `false_positive_burden_readout.csv`
- `topk_concentration_sensitivity.csv`
- `cluster_bootstrap_ci.csv`
- `robustness_baseline_quality_audit.csv`
- `baseline_repair_sweep_audit.csv`
- `tail_lift_curve_readout.csv`
- `ccdf_survival_curve_readout.csv`
- `capture_vs_burden_readout.csv`
- `mfe_mae_joint_readout.csv`
- `b2_right_left_tail_lift_balance_readout.csv`

Figures：

- `figures/tail_lift_curve.png`
- `figures/ccdf_survival_curve.png`
- `figures/capture_vs_burden.png`
- `figures/mfe_mae_joint_scatter.png`
- `figures/b2_right_left_tail_lift_balance.png`

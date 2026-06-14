# 09C Risk-on Cost Rejector Uplift 最终报告

## 1. 结论摘要

09C 的最终决策是：

```text
09C_riskon_cost_rejector_diagnostic_only_or_no_candidate
```

这意味着 09C 没有进入 research-entry，也不能 claim 已经得到可用的 `risk_on` cost rejector。当前模型确实有 OOS 排序信号，但没有同时满足 cost / recall / fast-fail attribution / density 四类约束。

预冻结主模型与阈值如下：

| item | value |
| --- | --- |
| selected target | `break_swing_low_20__or_false_repair_20d` |
| selected fast-fail label | `break_swing_low_20` |
| selected model | `regularized_logistic_or_elastic_net__hybrid_cost_bad_10_20__full__none` |
| selected threshold | `keep_7000` |
| train selection status | `diagnostic_best_train_frontier` |
| source caveat | `true` |

核心 gate 结果：

| gate | value | pass |
| --- | ---: | --- |
| train cost reduction | 20.3428% | yes |
| train any winner retention | 67.1496% | no |
| robustness cost reduction | 22.5401% | yes |
| robustness any winner retention | 69.5158% | no |
| OOS rejected-fraction spread | 17.9497pp | no |
| fast-fail robustness ROC-AUC | 0.7441 | yes |
| fast-fail attributed cost-reduction share | -0.0854% | no |
| density cap | cap exceeded | no |

最重要的结论是：**09C 证明了 09B feature foundation 对 hybrid cost target 有可分性，但没有证明 `break_swing_low_20` fast-fail 机制本身能带来可用的 cost-rejector uplift。** 当前 selected threshold 的 cost reduction 主要来自 false-repair component，而不是 fast-fail component；同时 winner retention 严重低于 90% gate。

另一个全局约束是：如果只使用当前 `fast_fail_10d = break_swing_low_20` label，R-core supported scope 的理论自然 operating point 大约是 reject 7.0613%、keep 92.9387%、winner retention 96.6730%、non-winner hit 7.8377%。因此纯 fast-fail rejector 的极限不在 09C 当前 70%-85% keep grid，而在接近 `keep_9294` 的小容量 reject 区间。

---

## 2. 输入契约与范围

09C 消费 09A / 09B 冻结产物：

| input | status |
| --- | --- |
| 09A selected label contract | pass |
| 09A selected label event bindings | pass |
| 09B feature matrix | pass |
| 09B sample uniqueness weights | pass |
| 09B transform contract | pass |
| feature leakage audit | pass |
| forbidden feature count | 0 |
| source pool reconstruction | pass |
| E1 baseline reconstruction | pass |

E1 baseline reconstruction 采用 07 canonical events 中 `triggered_channels contains E1_early_ema60_repair` 的规则：

| canonical rows | reconstructed E1 rows | unique E1 events | status |
| ---: | ---: | ---: | --- |
| 15,161 | 6,820 | 6,820 | pass |

scope 解释：

| denominator | role | rows / status |
| --- | --- | ---: |
| `risk_on_r_core_horizon_complete` | 唯一 supported training denominator | 30,790 rows in 09B |
| `risk_on_r6_horizon_complete` | readout-only | 9,260 rows in 09B |
| `risk_off_e1_horizon_complete_readonly` | 上游 binding 对账，不进入 09C fit | 1,887 input rows, 0 scored rows |

Risk-off read-only control 的状态是 `riskoff_readonly_control_input_insufficient`：09A binding 有 1,887 条 risk-off E1 readonly rows，但 09B 没有 materialize risk-off feature matrix，因此 09C 不能对 risk-off 重新 fit，也不能做 risk-off uplift 比较。

---

## 3. 数据与阈值 Frontier

selected model 在 R-core 上的 selected threshold 读数如下。注意 train 的 09C gate denominator 使用 nonzero-weight / horizon-complete 子集，因此 hybrid train 的模型输入为 16,603 rows，但 threshold gate 读数为 16,571 evaluable rows。

| split | evaluable n | selected n | rejected n | selected frac | cost before | cost after | cost reduction | winner n | rejected winner n | recall retention | fast-fail capture |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 16,571 | 11,600 | 4,971 | 70.0018% | 39.0683% | 31.1207% | 20.3428% | 2,968 | 975 | 67.1496% | 32.0800% |
| validation | 4,457 | 3,920 | 537 | 87.9515% | 31.0972% | 27.6531% | 11.0753% | 298 | 81 | 72.8188% | 15.6805% |
| robustness | 9,730 | 7,350 | 2,380 | 75.5396% | 29.5786% | 22.9116% | 22.5401% | 2,024 | 617 | 69.5158% | 19.8630% |

OOS rejected-fraction spread 是本轮硬失败之一：

```text
train rejected fraction      = 29.9982%
validation rejected fraction = 12.0485%
robustness rejected fraction = 24.4604%
max OOS spread               = 17.9497pp
predeclared cap              = 15.0000pp
```

这说明同一个 train-only threshold 在 validation 上明显过松，在 train / robustness 上明显更强。它不是一个稳定的 rejector operating point。

train frontier 也说明没有一个简单 keep fraction 可以同时满足 cost 与 recall：

| threshold | selected frac | train cost reduction | train recall retention | non-winner hit | winner injury | fast-fail capture |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| keep_7000 | 70.0018% | 20.3428% | 67.1496% | 29.3759% | 32.8504% | 32.0800% |
| keep_7250 | 72.5002% | 18.9758% | 69.8450% | 26.9205% | 30.1550% | 29.2000% |
| keep_7500 | 74.9985% | 17.4322% | 72.9111% | 24.5461% | 27.0889% | 27.0400% |
| keep_7750 | 77.4968% | 16.1675% | 76.0108% | 22.1789% | 23.9892% | 24.0800% |
| keep_8000 | 80.0012% | 14.7372% | 79.0094% | 19.7824% | 20.9906% | 21.2800% |
| keep_8250 | 82.4995% | 13.4061% | 81.5701% | 17.2977% | 18.4299% | 18.4800% |
| keep_8500 | 84.9979% | 11.4081% | 84.5687% | 14.9085% | 15.4313% | 15.2000% |

`keep_8000` 已经低于 15% train cost-reduction 下限，而 `keep_8500` 的 recall 仍只有 84.5687%，没有接近 90% recall gate。因此问题不是继续微调 threshold，而是排序目标与 winner preservation 没有对齐。

---

## 4. Component 贡献：hybrid 被 false-repair 主导

09C 按 requirement 拆开 fast-fail-only、false-repair component 和 hybrid target。selected threshold 的 component readout 如下：

| readout component | split | before rate | after rate | relative reduction | recall retention | fast-fail capture |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| fast_fail_only_10d | train | 7.5433% | 7.3190% | 2.9739% | 67.1496% | 32.0800% |
| false_repair_20d_component | train | 38.2717% | 30.0862% | 21.3878% | 67.1496% | 32.0800% |
| hybrid_cost_bad_10_20 | train | 39.0683% | 31.1207% | 20.3428% | 67.1496% | 32.0800% |
| fast_fail_only_10d | validation | 7.5870% | 7.2741% | 4.1237% | 72.8188% | 15.6805% |
| false_repair_20d_component | validation | 29.1900% | 25.5102% | 12.6065% | 72.8188% | 15.6805% |
| hybrid_cost_bad_10_20 | validation | 31.0972% | 27.6531% | 11.0753% | 72.8188% | 15.6805% |
| fast_fail_only_10d | robustness | 6.0138% | 6.3786% | -6.0665% | 69.5158% | 19.8630% |
| false_repair_20d_component | robustness | 27.9959% | 20.8435% | 25.5479% | 69.5158% | 19.8630% |
| hybrid_cost_bad_10_20 | robustness | 29.5786% | 22.9116% | 22.5401% | 69.5158% | 19.8630% |

这张表是本报告最关键的数据。模型在 hybrid 上看起来有 uplift，但 fast-fail-only 的 train reduction 只有 2.9739%，validation 只有 4.1237%，robustness 甚至变成 -6.0665%。换句话说，selected threshold 并没有稳定降低 `break_swing_low_20` fast-fail；它主要是在拒绝 false-repair。

component attribution 进一步确认了这一点：

| split | rejected hybrid positives | total hybrid cost reduction rate | fast-fail attributed cost reduction | fast-fail attributed share | fast-fail-only rejected | false-repair-only rejected | both rejected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 2,864 | 7.9476pp | -0.0068pp | -0.0854% | 12 | 2,463 | 389 |
| validation | 302 | 3.4441pp | 0.0387pp | 1.1240% | 1 | 249 | 52 |
| robustness | 1,194 | 6.6671pp | -0.4253pp | -6.3790% | 2 | 1,078 | 114 |

因此，09A 报告里的 warning 在 09C 得到了验证：`break_swing_low_20` 与 incumbent fast-fail 机制差异很大，但一旦混入 `false_repair_20d`，hybrid target 的主要训练信号被 false-repair 稀释。09C 的 selected model 不能被解释为 fast-fail uplift model。

### 4.1 当前 fast-fail 10D label 的全局上界

为了回答“如果选用现在的 fast-fail 10D label，winner capture 最大比例是多少”，这里直接使用 09A `selected_label_event_bindings.parquet` 计算 label 本身的 oracle 上界，不使用 09C 模型 score。口径为：

```text
fast_fail_10d = selected_fast_fail_10_label
winner = event_big_winner_120d_label (+50%, 120D complete)
主口径 = risk_on_r_core_horizon_complete
```

全局统计如下：

| scope | complete n | winner n | fast-fail n | fast-fail winners | reject fraction | max winner capture if reject all fast-fail | non-winner hit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R-core supported | 30,731 | 5,290 | 2,170 | 176 | 7.0613% | 96.6730% | 7.8377% |
| unique sample global | 32,616 | 5,580 | 2,357 | 188 | 7.2265% | 96.6308% | 8.0226% |
| all binding rows | 41,844 | 7,187 | 3,098 | 248 | 7.4037% | 96.5493% | 8.2234% |

R-core supported split 统计：

| split | complete n | winner n | fast-fail n | fast-fail winners | fast-fail rate | max winner capture | non-winner hit | kill-wrong among fast-fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 16,571 | 2,968 | 1,250 | 110 | 7.5433% | 96.2938% | 8.3805% | 8.8000% |
| validation | 4,455 | 298 | 338 | 5 | 7.5870% | 98.3221% | 8.0106% | 1.4793% |
| robustness | 9,705 | 2,024 | 582 | 61 | 5.9969% | 96.9862% | 6.7830% | 10.4811% |

这组数给出了当前 fast-fail label 的真实边界：

```text
R-core label-oracle natural point:
    reject ≈ 7.06%
    keep ≈ 92.94%
    winner retention ≈ 96.67%
    non-winner hit ≈ 7.84%
    kill-wrong among fast-fail ≈ 8.11%
```

如果允许未来 oracle 只拒绝 fast-fail 中的 non-winner、跳过 fast-fail winner，那么 winner capture 可以达到 100%；但这是未来信息，不是 PIT rejector。这个未来 oracle 只说明当前 `break_swing_low_20` 的真正坏侧容量约为：

```text
fast-fail non-winner capacity = 1,994 / 30,731 = 6.4886%
```

因此，当前 fast-fail label 的上限不是“能支持 20%-30% 大容量 reject”，而是“一个约 6.5%-7.1% 的低容量、高 winner-retention stop filter”。这也解释了 09C 的失败：`keep_7000` 在 train 上 reject 29.9982%，远超当前 fast-fail label 的自然容量，必然开始大量拒绝非 fast-fail winner。

09C 已有 fast-fail-only score 模型可作为实际模型参照。即使用 fast-fail-only 模型，R-core 上在较高 recall 约束下的最强 readout 也仍然体现出同一 trade-off：

| split | recall constraint | best threshold | selected fraction | cost reduction | recall | fast-fail capture | winner injury |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| train | >=85% | keep_8500 | 84.9677% | 37.4821% | 86.1186% | 46.8800% | 13.8814% |
| validation | >=85% | keep_8500 | 81.7059% | 34.8218% | 86.2416% | 46.7456% | 13.7584% |
| robustness | >=85% | keep_8500 | 81.0421% | 34.5005% | 85.0791% | 46.9178% | 14.9209% |

这个模型参照不能替代 label oracle。它说明当前 score 模型即使专门训练 fast-fail-only，也需要 14%左右 winner injury 才能捕获约 47% 的 fast-fail bad side；而 label 本身的“拒绝全部 fast-fail”上界只需要 3.3270% winner injury，但容量只有 7.0613%。下一轮如果要做 pure fast-fail rejector，threshold grid 应补充 `keep_9000`、`keep_9250`、`keep_9300`、`keep_9400` 等小容量区间，而不是沿用 09C 的 `keep_7000` 到 `keep_8500`。

---

## 5. Separability 与 Calibration

selected model 的 R-core separability：

| split | sample n | positive n | positive rate | ROC-AUC | PR-AUC | top-decile lift | monotonicity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 16,603 | 6,484 | 39.0532% | 0.6874 | 0.6268 | 1.7189 | 1.0000 |
| validation | 4,457 | 1,386 | 31.0972% | 0.6803 | 0.5181 | 1.8242 | 1.0000 |
| robustness | 9,730 | 2,878 | 29.5786% | 0.6664 | 0.5027 | 1.9979 | 0.9879 |

这组结果说明：hybrid target 的排序信号是存在的，而且 OOS 没有完全坍塌。但它无法解决 gate 的真实约束：winner retention 不够、threshold spread 不稳、fast-fail attribution 不够。

calibration 只作为 readout，不参与主选择。`none` 是预冻结主路径；Platt 和 isotonic 都只在 R-core train fit，OOS 只读：

| calibration | split | ROC-AUC | PR-AUC | Brier | keep_0800 after cost rate |
| --- | --- | ---: | ---: | ---: | ---: |
| none | train | 0.6874 | 0.6268 | 0.2277 | 33.2932% |
| none | validation | 0.6803 | 0.5181 | 0.2159 | 25.8626% |
| none | robustness | 0.6664 | 0.5027 | 0.2334 | 23.8695% |
| platt | train | 0.6874 | 0.6268 | 0.2187 | 33.2932% |
| platt | validation | 0.6803 | 0.5181 | 0.2047 | 25.8626% |
| platt | robustness | 0.6664 | 0.5027 | 0.2028 | 23.8695% |
| isotonic | train | 0.6897 | 0.6196 | 0.2174 | 34.2609% |
| isotonic | validation | 0.6806 | 0.5102 | 0.2047 | 26.0641% |
| isotonic | robustness | 0.6681 | 0.4965 | 0.2020 | 23.9228% |

Calibration 改善了部分 Brier score，但没有改变 cost / recall frontier，也没有改变 diagnostic-only 的结论。

---

## 6. Feature Status

09C 使用 09B 冻结的 feature matrix 与 transform contract。当前 feature contract 状态：

| feature family | feature n | allowed for 09C | related overlap | direct overlap |
| --- | ---: | ---: | ---: | ---: |
| FS0_baseline_h_features | 10 | 10 | 2 | 0 |
| FS1_event_intrinsic | 4 | 4 | 0 | 0 |
| FS2_basis_path_quality | 10 | 10 | 5 | 0 |
| FS3_vol_range_stop_distance | 9 | 9 | 6 | 0 |
| FS4_amount_volume_vwap_dib | 5 | 5 | 0 | 0 |
| FS5_market_industry_riskon_quality | 8 | 8 | 0 | 0 |
| FS6_recurrence_local_density | 2 | 2 | 0 | 0 |

共 48 个 feature，全部 `allowed_for_09C_flag = true`，forbidden feature count = 0。13 个 feature 与 `break_swing_low_20` structural stop 机制存在 related overlap，集中在 FS2 / FS3；没有 direct overlap feature。

09C 共 materialize 26 个模型：

| model family | model n | status |
| --- | ---: | --- |
| H-style logistic baseline | 3 | fit |
| regularized logistic / elastic net | 20 | fit |
| shallow tree / bagging shallow trees diagnostic | 3 | fit |

主要 ablation 的 feature 使用情况：

| ablation | feature n | family n | related overlap n | rolling / fracdiff n | model n |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline_fs0 | 10 | 1 | 2 | 3 | 3 |
| full | 48 | 7 | 13 | 3 | 8 |
| drop_direct_related_overlap | 35 | 7 | 0 | 3 | 3 |
| drop_fs2_related_subset_only | 43 | 7 | 8 | 3 | 3 |
| drop_fs0_rolling_fracdiff_hygiene | 45 | 7 | 13 | 0 | 3 |
| family_representative_features_only | 7 | 7 | 2 | 0 | 3 |

`drop_direct_overlap` 与 `full` 等价，因为当前没有 direct overlap feature；真正有解释价值的是 `drop_direct_related_overlap`、`drop_fs2_related_subset_only`、`drop_fs0_rolling_fracdiff_hygiene` 和 `family_representative_features_only`。

09B group MDA 的核心结构如下：

| target component | split | top family | group MDA AUC drop | interpretation |
| --- | --- | --- | ---: | --- |
| fast_fail_only_10d | train | FS2_basis_path_quality | 0.2654 | fast-fail 主要看 price/path location |
| fast_fail_only_10d | validation | FS2_basis_path_quality | 0.2299 | OOS 仍稳定 |
| fast_fail_only_10d | robustness | FS2_basis_path_quality | 0.2376 | OOS 仍稳定 |
| false_repair_20d_component | train | FS0_baseline_h_features | 0.1598 | false-repair 更像 H-style / path-history 信号 |
| false_repair_20d_component | validation | FS3_vol_range_stop_distance | 0.1708 | range / stop-distance 在 validation 更强 |
| false_repair_20d_component | robustness | FS0_baseline_h_features | 0.1789 | robustness 回到 FS0 主导 |
| hybrid_cost_bad_10_20 | train | FS0_baseline_h_features | 0.1601 | hybrid 接近 false-repair |
| hybrid_cost_bad_10_20 | validation | FS0_baseline_h_features | 0.1345 | hybrid 接近 false-repair |
| hybrid_cost_bad_10_20 | robustness | FS0_baseline_h_features | 0.1780 | hybrid 接近 false-repair |

这个 feature structure 解释了 09C 的失败：fast-fail-only 的主轴是 FS2，但 selected hybrid model 的主要有效收益来自 false-repair，而 hybrid 的 family importance 更接近 FS0 / FS3。09C 不是没有 feature 信号，而是 target mixture 让模型优化方向偏离 fast-fail uplift。

---

## 7. Stationarity、Weights 与 PCA

09B / 09C 冻结的 transform contract：

| item | frozen rule |
| --- | --- |
| fit scope | `risk_on_r_core_horizon_complete/train` |
| imputer | train median |
| winsorization | train p01 / p99 |
| scaler | continuous feature train standard z；binary flag 保持 0/1 |
| fracdiff | only `log_close_fracdiff_d04`, d = 0.4, max lags = 20 |
| PCA | `not_used` |
| PCA usage | `not_used` |

Stationary hygiene 摘要：

| method | feature n |
| --- | ---: |
| train z | 35 |
| trailing relative return then train z | 2 |
| trailing return then train z | 2 |
| ATR normalization | 1 |
| sigma normalization | 1 |
| rolling z 60d | 1 |
| rolling percentile 60d | 1 |
| selected fracdiff log close d=0.4 | 1 |
| run length / entropy / ratio hygiene | 3 |

缺失率最高的 feature：

| feature | family | raw missing rate | treatment |
| --- | --- | ---: | --- |
| `log_close_fracdiff_d04` | FS0 | 4.7915% | train median + train z |
| `panel_return_20d_rolling_z_60d` | FS0 | 4.6717% | rolling z + train z |
| `panel_return_20d_rolling_pct_60d` | FS0 | 4.6717% | rolling percentile + train z |
| `universe_up_share_z` | FS5 | 1.3084% | train median + train z |
| `stock_vs_board_20d` | FS2 | 1.2809% | board fallback, not industry |
| `board_relative_cusum_20d` | FS5 | 1.2809% | board fallback, not industry |

PCA 没有进入 09C，这是正确的。09C 的核心问题不是 feature 维度太高，而是 target mixture、winner injury 和 threshold stability。用全局 PCA 会进一步压扁 FS2 / FS3 与 structural stop 的机制解释，降低对 fast-fail-only 与 false-repair component 的可诊断性。当前更有价值的是 `family_representative_features_only` 对照：它只用 7 个 family representative features，仍能得到 train cost reduction 20.6737%、robustness cost reduction 25.9179%，但 recall 仍只有 train 65.8693%、robustness 71.0474%。这说明问题不在于高维过拟合，而在于 selected rejector 的 recall / target alignment。

Sample weights 使用两套 horizon：

| target component | weight horizon | intended use |
| --- | --- | --- |
| fast_fail_only_10d | `fast_fail_10d` | 10D fast-fail-only model |
| false_repair_20d_component | `cost_bad_10_20_20d` | 20D false-repair component |
| hybrid_cost_bad_10_20 | `cost_bad_10_20_20d` | hybrid target |

R-core 权重读数：

| component | split | sample n | positive n | zero weight n | avg uniqueness | concurrency mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| fast_fail_only_10d | train | 16,603 | 1,250 | 0 | 0.003992 | 342.6790 |
| fast_fail_only_10d | validation | 4,457 | 338 | 0 | 0.004824 | 259.7875 |
| fast_fail_only_10d | robustness | 9,730 | 584 | 0 | 0.003410 | 347.4827 |
| hybrid_cost_bad_10_20 | train | 16,603 | 6,484 | 32 | 0.002229 | 630.0036 |
| hybrid_cost_bad_10_20 | validation | 4,457 | 1,386 | 2 | 0.002832 | 460.5007 |
| hybrid_cost_bad_10_20 | robustness | 9,730 | 2,878 | 19 | 0.001894 | 634.2017 |

09B 的 whole-scope audit 也显示 20D hybrid 的平均 uniqueness 明显低于 10D fast-fail：

| denominator | horizon | sample n | avg uniqueness mean | concurrency mean | not evaluable n |
| --- | --- | ---: | ---: | ---: | ---: |
| R-core | fast_fail_10d | 30,790 | 0.003929 | 332.1981 | 0 |
| R-core | cost_bad_10_20_20d | 30,790 | 0.002210 | 606.7623 | 53 |
| R6 | fast_fail_10d | 9,260 | 0.012297 | 100.6236 | 0 |
| R6 | cost_bad_10_20_20d | 9,260 | 0.007071 | 178.3404 | 30 |

这说明 20D hybrid target 天然更高并发、更低 uniqueness；与 10D fast-fail-only 的 readout 不应横向直接比较。09C 已按 `weight_horizon_id` 分开使用权重。

---

## 8. Ablation、Baseline 与 Density

H-style baseline replay 使用 09A target + 09B FS0 feature + 09B sample weights，在 09C 内部重新跑，不是复用 08H 旧 target。R-core train `keep_7000` 对照如下：

| baseline target | cost reduction | recall retention | fast-fail capture |
| --- | ---: | ---: | ---: |
| fast_fail_only_10d | 43.0381% | 68.3962% | 60.1600% |
| false_repair_20d_component | 17.4234% | 64.7911% | 27.4400% |
| hybrid_cost_bad_10_20 | 16.7461% | 64.5889% | 30.6400% |

09C selected full hybrid model 相比 H-style hybrid baseline，把 train cost reduction 从 16.7461% 提到 20.3428%，但 recall 只从 64.5889% 提到 67.1496%，仍远低于 90%。这是 uplift，但不是可用的 cost rejector。

关键 ablation：

| ablation | train cost reduction | train recall | robustness cost reduction | robustness recall | interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| full | 20.3428% | 67.1496% | 22.5401% | 69.5158% | selected path |
| drop_direct_related_overlap | 17.4963% | 65.0270% | 20.3397% | 64.5751% | 去掉机制相关 feature 后仍有信号，但 recall 更差 |
| drop_fs2_related_subset_only | 19.8794% | 65.9367% | 24.2808% | 68.5771% | 去掉 FS2 related 后 OOS cost 不降，说明 hybrid 信号不完全来自 swing-low 同源 |
| drop_fs0_rolling_fracdiff_hygiene | 20.2986% | 66.9474% | 22.8603% | 68.1324% | rolling / fracdiff hygiene 不是主要失败来源 |
| family_representative_features_only | 20.6737% | 65.8693% | 25.9179% | 71.0474% | 低维 representative 仍有 cost 信号，但 recall 仍失败 |

Density gate 是另一个独立 blocker：

| metric | value | cap | status |
| --- | ---: | ---: | --- |
| formal_event_day_density | 26.3441 | 7.5000 | cap exceeded |
| p95 density | 59.0000 | 20.0000 | cap exceeded |
| rolling_10d executable event day density | 5.0000 | 1.8000 | cap exceeded |
| rolling_20d executable event day density | 5.0000 | 2.2000 | cap exceeded |
| family concentration | 0.2687 | 0.3000 | pass |
| board concentration | 0.8237 | 0.8500 | pass |

split-level selected density：

| split | selected n | unique event day n | event-day density | top family share | top board share |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 11,623 | 470 | 24.7298 | 26.3185% | 82.1647% |
| validation | 3,920 | 128 | 30.6250 | 29.8469% | 82.3214% |
| robustness | 7,350 | 271 | 27.1218 | 26.1497% | 82.7075% |

family / board concentration 没超 cap，但 event-day density 大幅超 cap。这说明 selected set 仍然太密集，不适合直接进入 portfolio / execution 层。

---

## 9. Findings

### Finding 1：09C 有 OOS 信号，但不是 research-entry 级 rejector

Hybrid ROC-AUC 在 train / validation / robustness 分别为 0.6874 / 0.6803 / 0.6664，top-decile lift 在 robustness 达到 1.9979。这个信号不是噪声。

但 research-entry 需要的是同一个 train-only threshold 同时降低 cost、保留 winner、稳定 OOS rejection、控制 density。09C 只满足了 cost reduction 和部分 separability，没有满足 recall、spread、fast-fail attribution、density。

### Finding 2：主失败不是 AUC，而是 cost/recall frontier 不可用

`keep_7000` 可以给出 20.3428% train cost reduction，但 winner retention 只有 67.1496%。提高 keep fraction 后 recall 上升，但 cost reduction 很快掉到 15% 以下；`keep_8000` 只有 14.7372% cost reduction，`keep_8500` recall 仍只有 84.5687%。这说明排序质量没有把“该拒绝的坏样本”和“需要保留的 winner”分开。

### Finding 3：fast-fail 机制没有贡献到 hybrid uplift

selected model 在 fast-fail-only 上 robustness reduction 为 -6.0665%，fast-fail attributed share 在 train 为 -0.0854%，robustness 为 -6.3790%。这不是一个 fast-fail uplift。当前 hybrid uplift 基本来自 false-repair component。

### Finding 4：当前 fast-fail label 的自然容量只有约 7%

R-core supported scope 中，`break_swing_low_20` fast-fail positive rate 只有 7.0613%。如果完美拒绝全部 fast-fail-positive，winner retention 上限是 96.6730%，但 non-winner hit 只有 7.8377%。这说明它更像低容量 structural stop filter，不是 20%-30% 容量的 cost rejector target。

### Finding 5：09B feature foundation 是有用的，但 hybrid target 把 FS2 fast-fail 结构稀释了

09B 显示 fast-fail-only 主要依赖 FS2 basis/path quality，而 false-repair 和 hybrid 更依赖 FS0 / FS3。09C 的 selected model 是 hybrid target，因此最终收益更像 false-repair rejector，而不是 structural fast-fail rejector。

### Finding 6：PCA 不是下一步的解法

PCA 没进入本轮主流程是正确的。`family_representative_features_only` 已经证明低维 representative feature 也能得到 cost signal，但 recall 仍失败。因此问题不是降维不足，而是 target decomposition、threshold objective 和 density control。

### Finding 7：risk-off 仍应冻结

Risk-off E1 readonly 只有 binding 对账，没有 09B feature matrix，因此 09C 没有任何 risk-off uplift 证据。当前不应把 risk-on 结论推广到 risk-off。

---

## 10. Insight 与后续建议

1. 09C 应被记录为“diagnostic success, gate failure”。
   它成功证明了 09B feature foundation 能稳定产生 hybrid cost sorting signal，但失败于 research-entry gate。

2. 下一轮不要继续调 keep fraction。
   当前 frontier 已经说明 keep fraction 无法解决 cost/recall 同时过线问题。继续在 0.70-0.85 之间调阈值，只会在“杀太多 winner”和“cost reduction 不够”之间移动。

3. 必须拆开 fast-fail-only 与 false-repair。
   如果目标是验证 `break_swing_low_20` 是否有 cost-rejector 价值，下一轮要把 fast-fail-only 作为独立 primary readout / gate，而不是让 hybrid target 继续由 false-repair 主导。

4. pure fast-fail threshold grid 应该移动到小容量区间。
   当前 label-oracle 上界显示自然 reject fraction 约 7.06%，因此后续 fast-fail-only 实验应重点看 `keep_9000`、`keep_9250`、`keep_9300`、`keep_9400`，而不是继续围绕 `keep_7000` 到 `keep_8500`。

5. false-repair rejector 可以作为独立方向保留。
   当前 hybrid uplift 的主要来源是 false-repair component，这不是坏结果，但它回答的是另一个问题：是否能识别 20D false-repair / repair-failure，而不是是否能改善 10D fast-fail。

6. density cap 需要前置。
   selected events 的 event-day density 是 24.7-30.6，远高于 cap。后续即使模型 AUC 更高，也必须先设计 event-day / episode-level de-dup 或 density-aware threshold，否则无法进入 portfolio 层。

7. feature 继续保留 raw / representative / no-overlap 三套对照，不建议引入 global PCA。
   PCA 会让 FS2 structural-stop overlap 与 FS0/FS3 false-repair signal 更难解释；当前最需要的是 component-specific model 和 ablation，而不是全局压缩。

8. transition 和 risk-off 继续不进入主线。
   09C 的证据只覆盖 risk-on R-core supported denominator。R6 是 readout-only，risk-off E1 只有 input audit，没有 scored feature matrix。

最终判断：

```text
09C 没有把 08H 的窄 frontier 推过 research-entry。
它把失败原因定位清楚了：
    cost signal 存在，
    winner retention 不够，
    threshold OOS 稳定性不足，
    fast-fail component 没有贡献 hybrid uplift，
    density 过高。

下一步应该从 hybrid target 拆分为：
    fast-fail-only structural model diagnostic
    false-repair rejector diagnostic
    density-aware post-filter / de-dup diagnostic
而不是继续调 keep fraction 或引入 PCA。
```

---

## 11. 产物索引

核心 09C 产物位于：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/
```

关键文件：

| artifact | purpose |
| --- | --- |
| `threshold_frontier.csv` | train-only threshold frontier 与 split readout |
| `threshold_frontier_by_component.csv` | fast-fail / false-repair / hybrid component readout |
| `component_contribution_readout.csv` | hybrid cost reduction attribution |
| `oos_separability.csv` | ROC-AUC / PR-AUC / lift / monotonicity |
| `model_registry.csv` | 26 个模型的 fit 状态与 feature count |
| `feature_family_usage_audit.csv` | feature / overlap / rolling-fracdiff 使用情况 |
| `weight_horizon_usage_audit.csv` | 10D 与 20D sample weight 使用情况 |
| `density_gate_binding_audit.csv` | density / concentration hard gate |
| `riskoff_readonly_control.csv` | risk-off readonly input-insufficient 说明 |
| `event_scores.csv.gz` | scored events |
| `selected_events.csv.gz` | selected events |
| `rejected_events.csv.gz` | rejected events |

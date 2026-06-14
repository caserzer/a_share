# 09B Feature Foundation / Stationary / Importance 最终报告

## 1. 结论摘要

09B 已完成从 09A label contract 到 09C 可消费 feature foundation 的 materialization。当前决策为 `09B_feature_foundation_complete`，可以作为 09C 的 supported feature / weight / transform 输入，但必须保留两个边界：

1. 09A 决策仍带 `source_caveated = true`，因此 09C 的 supported 结论也应继承 source caveat。
2. 09B 只支持 `break_swing_low_20__or_false_repair_20d`；`fixed_mae10_neg_12__or_false_repair_20d` 已降级为 sensitivity / 对照，不进入 09C supported gate。

当前 09B 冻结了 4 类关键产物：

| artifact | 数量 / 状态 | 说明 |
| --- | ---: | --- |
| target binding | 41,937 rows | 09A selected target binding complete |
| feature matrix | 40,050 rows x 56 cols | R-core 30,790；R6 9,260；48 个 allowed feature |
| sample weights | 80,100 rows | `fast_fail_10d` 与 `cost_bad_10_20_20d` 双 horizon |
| diagnostic importance | 3 models / 432 SFI rows | fast-fail-only、false-repair component、hybrid target 分开评估 |

最重要的研究结论是：**fast-fail-only 与 hybrid target 的主导 feature family 不同。**
`fast_fail_only_10d` 的稳定主轴暂时表现为 `FS2_basis_path_quality`，而 `false_repair_20d_component` 与 `hybrid_cost_bad_10_20` 的主轴明显偏向 `FS0_baseline_h_features` 与 `FS3_vol_range_stop_distance`。这验证了 09A 的警告：如果 09C 只看 hybrid target，fast-fail 机制差异会被 false-repair component 稀释。

但这个结论必须带 caveat：`break_swing_low_20` 是 structural stop label，FS2/FS3 中一部分 price-location、EMA、range feature 与 label 机制同源。当前 09B 能证明“有可分性”，但不能单独证明“有可交易的 cost-rejection 价值”。后者必须由 09C 的 no-overlap ablation、fast-fail-only target 和 cost/recall frontier gate 共同确认。

---

## 2. 输入契约与 scope

09B 的上游契约已通过：

| check | status |
| --- | --- |
| 09A manifest hash | pass |
| selected target binding coverage | complete |
| sample key uniqueness | pass |
| source pool reconstruction | pass |
| feature leakage | pass |
| forbidden feature count | 0 |
| stationarity audit | pass |
| mechanism overlap audit | pass |
| importance split stability | pass |

事件级 target binding 只包含一个 09C supported target：

| selected_target_id | label | usable_for_09C_supported_gate | binding rows | denominators |
| --- | --- | ---: | ---: | --- |
| `break_swing_low_20__or_false_repair_20d` | `break_swing_low_20` | true | 41,937 | R-core / R6 / risk-off E1 readonly |

`sample_key = (sample_id, selected_target_id, denominator_id)` 已冻结为唯一 downstream join key：

| denominator | rows | sample_id unique | sample_key unique | duplicate key rows | status |
| --- | ---: | ---: | ---: | ---: | --- |
| all | 41,937 | 32,685 | 41,937 | 0 | pass |
| risk_on_r_core_horizon_complete | 30,790 | 30,790 | 30,790 | 0 | pass |
| risk_on_r6_horizon_complete | 9,260 | 9,260 | 9,260 | 0 | pass |
| risk_off_e1_horizon_complete_readonly | 1,887 | 1,887 | 1,887 | 0 | pass |

scope 解释：

- `risk_on_r_core_horizon_complete` 是唯一 supported training denominator。
- `risk_on_r6_horizon_complete` 只允许 readout-only，不参与 fit、selection、threshold、09C supported gate。
- `risk_off_e1_horizon_complete_readonly` 只用于上游 binding 对账，不进入 09B feature / weight / importance scope。

---

## 3. Feature Matrix 与 Feature Status

当前 feature matrix 有 40,050 行，其中 R-core 30,790 行，R6 9,260 行：

| denominator | train | validation | robustness | total |
| --- | ---: | ---: | ---: | ---: |
| risk_on_r_core_horizon_complete | 16,603 | 4,457 | 9,730 | 30,790 |
| risk_on_r6_horizon_complete | 4,816 | 1,441 | 3,003 | 9,260 |

48 个 feature 全部 `allowed_for_09C_flag = true` 且 stationarity audit pass：

| feature family | feature_n | allowed | 角色 |
| --- | ---: | ---: | --- |
| FS0_baseline_h_features | 10 | 10 | 08H 已允许 t0 feature + rolling / fracdiff hygiene |
| FS1_event_intrinsic | 4 | 4 | family / channel / cluster event intensity |
| FS2_basis_path_quality | 10 | 10 | price basis、EMA、relative CUSUM、close-to-high |
| FS3_vol_range_stop_distance | 9 | 9 | ATR、range、gap、sigma / ATR normalized distance |
| FS4_amount_volume_vwap_dib | 5 | 5 | amount / turnover / liquidity quality |
| FS5_market_industry_riskon_quality | 8 | 8 | market / board fallback / breadth context |
| FS6_recurrence_local_density | 2 | 2 | prior local event density |

Forbidden leakage 检查结果：

| role | count | status |
| --- | ---: | --- |
| feature | 48 | pass |
| metadata | 8 | pass |

没有任何 label、future outcome、touch result、winner label、`label_t1_date` 或 sample weight 字段进入 feature matrix。

### 3.1 Missingness 与可用性

整体 missingness 可控，最高缺失来自新加入的 rolling / fracdiff feature：

| feature | family | raw_missing_rate | 处理 |
| --- | --- | ---: | --- |
| `log_close_fracdiff_d04` | FS0 | 4.7915% | train median impute + train z |
| `panel_return_20d_rolling_z_60d` | FS0 | 4.6717% | rolling z 后 train z |
| `panel_return_20d_rolling_pct_60d` | FS0 | 4.6717% | rolling percentile 后 train z |
| `universe_up_share_z` | FS5 | 1.3084% | board / market fallback context |
| `stock_vs_board_20d` | FS2 | 1.2809% | board fallback，不解释为 industry |
| `board_relative_cusum_20d` | FS5 | 1.2809% | board fallback，不解释为 industry |

这些缺失主要来自 early panel warmup 或 board fallback coverage，不是未来信息缺失。当前 transform contract 将其统一处理为 train-scope median imputation，再用 train-scope winsor / scaler transform OOS。

### 3.2 Industry / Board PIT

09B 没有构造真正 industry feature，因为 08 artifact 明确声明 PIT industry classification 不可用：

| domain | PIT available | coverage | policy | status |
| --- | ---: | ---: | --- | --- |
| industry | false | 0.0000 | block_industry_features | industry_pit_unavailable |
| style_proxy_board | true | 1.0000 | board_fallback_not_industry | board_fallback_available |
| market_breadth | true | 1.0000 | market_breadth_available | pit_available |

因此，`stock_vs_board_20d`、`board_relative_cusum_20d` 等只能解释为 board / style fallback，不得在 09C 中解释为 industry alpha。

### 3.3 Feature-label Mechanism Overlap

48 个 feature 中，13 个与 `break_swing_low_20` 的 structural / range stop 机制相关：

| overlap_type | feature count | 主要 family |
| --- | ---: | --- |
| related | 13 | FS0:2, FS2:5, FS3:6 |
| none | 35 | FS1/FS4/FS5/FS6 与部分 FS0/FS2/FS3 |

这不是 forbidden，但 09C 必须做一组 no-overlap ablation。否则 `break_swing_low_20` label 与 close-to-high、EMA、ATR/range 特征之间可能形成机制同源解释，导致模型看起来更强，但不一定代表可泛化的排序能力。

更具体地看，`FS2_basis_path_quality` 内部 10 个 feature 中有 5 个是 related：`close_to_ema20`、`close_to_ema60`、`ema20_slope_20d`、`ema60_slope_20d`、`close_to_high_60`。`fast_fail_only_10d` 的 top-10 SFI 中，related feature 占比在 train / validation / robustness 分别为 20% / 20% / 40%。这说明 FS2 领先不是纯粹的机制重叠伪影，因为 `return_20d`、`return_20d_sigma_norm` 等非 related feature 也很强；但 FS2 领先的强度可能被 structural-stop 同源特征放大。

### 3.4 Warmup Missing Split Asymmetry

rolling / fracdiff hygiene feature 的缺失不是随机缺失，而是明显集中在 train split。这是因为这些 feature 需要较长 trailing window，早期样本更容易 warmup 不足：

| denominator | split | `log_close_fracdiff_d04` missing | `panel_return_20d_rolling_z_60d` missing | `panel_return_20d_rolling_pct_60d` missing |
| --- | --- | ---: | ---: | ---: |
| R-core | train | 6.3001% | 6.1374% | 6.1374% |
| R-core | validation | 2.5578% | 2.5129% | 2.5129% |
| R-core | robustness | 2.3741% | 2.2816% | 2.2816% |
| R6 | train | 8.0772% | 7.9527% | 7.9527% |
| R6 | validation | 3.4698% | 3.4004% | 3.4004% |
| R6 | robustness | 2.9637% | 2.8638% | 2.8638% |

这不构成 leakage，也不阻塞 09B complete；但它会影响 rolling / fracdiff feature 的 train-vs-OOS importance 解读。09C 必须报告一组 `without rolling/fracdiff hygiene features` ablation，确认这些 feature 的增益不是 warmup missing pattern 或 imputation pattern 带来的。

---

## 4. Stationary / Transform / PCA

09B transform contract 明确冻结如下规则：

| item | frozen rule |
| --- | --- |
| fit scope | `risk_on_r_core_horizon_complete/train` |
| imputer | train median |
| winsorization | train p01 / p99 |
| scaler | continuous feature train standard z；binary flag 保持 0/1 |
| rolling window | 60 sessions，min periods 20 |
| OOS transform | validation / robustness / R6 只 transform，不 fit |
| PCA | not used |

PCA 在 09B 中没有使用，`pca = not_used`，`pca_usage = not_used`。这是正确选择：当前目标是冻结可解释的 feature foundation 和 family importance，而不是用 PCA 压缩解释空间。09C 如果需要 PCA，也只能在 family 内、train-fold fit，并与 raw / representative feature 对照。

09B 已补齐 stationary hygiene：

| method | feature count | 代表 feature |
| --- | ---: | --- |
| rolling z-score | 1 | `panel_return_20d_rolling_z_60d` |
| rolling percentile | 1 | `panel_return_20d_rolling_pct_60d` |
| ATR normalization | 1 | `intraday_range_atr_norm` |
| sigma normalization | 1 | `return_20d_sigma_norm` |
| selected fracdiff | 1 | `log_close_fracdiff_d04` |
| train z / trailing ratios / run-length | 43 | 其余 t0 feature |

Fracdiff 仅用于 `log(close)`，参数固定为：

| parameter | value |
| --- | ---: |
| d | 0.4 |
| max_lags | 20 |
| weight_threshold | 0.0001 |
| search policy | fixed predeclared d, no full-sample search |

这个设计保守但合理：09B 没有对 returns、ranks、event dummies、labels 或 future-derived fields 做 fracdiff，也没有把 industry series 纳入 fracdiff，因为 PIT industry membership 不可用。

---

## 5. Sample Weights 与 Uniqueness

09B 冻结了两套 horizon 权重：

1. `fast_fail_10d`：用于 fast-fail-only target。
2. `cost_bad_10_20_20d`：用于 hybrid cost target，即 fast-fail OR false-repair 20D。

权重审计如下：

| denominator | horizon | scope | sample_n | avg uniqueness mean | avg uniqueness median | concurrency mean | status |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| R-core | fast_fail_10d | supported_training | 30,790 | 0.003929 | 0.003232 | 332.1981 | complete |
| R-core | cost_bad_10_20_20d | supported_training | 30,790 | 0.002210 | 0.001695 | 606.7623 | complete_with_non_executable_caveat |
| R6 | fast_fail_10d | readout_only | 9,260 | 0.012297 | 0.010388 | 100.6236 | complete |
| R6 | cost_bad_10_20_20d | readout_only | 9,260 | 0.007071 | 0.005394 | 178.3404 | complete_with_non_executable_caveat |
| risk-off E1 readonly | fast_fail_10d | not_09B_scope_readonly | 1,887 | NA | NA | NA | readonly |
| risk-off E1 readonly | cost_bad_10_20_20d | not_09B_scope_readonly | 1,887 | NA | NA | NA | readonly |

20D hybrid 权重存在少量不可评估样本：

| denominator | horizon | complete | not_evaluable_20d |
| --- | --- | ---: | ---: |
| R-core | cost_bad_10_20_20d | 30,737 | 53 |
| R6 | cost_bad_10_20_20d | 9,230 | 30 |

这些样本保留在 feature matrix 中，但在 `sample_uniqueness_weights.parquet` 中 `final_sample_weight = 0`，不得被 09C 当作有效 20D cost target 训练样本。

两个 horizon 的权重不能混用。R-core 中 10D fast-fail 的平均 uniqueness 为 0.003929，高于 20D hybrid 的 0.002210；这符合预期，因为 20D active interval 更长、concurrency 更高。09C 必须用 `weight_horizon_id` 精确选择权重：

- `fast_fail_only_10d` 使用 `fast_fail_10d`。
- `false_repair_20d_component` 和 `hybrid_cost_bad_10_20` 使用 `cost_bad_10_20_20d`。

---

## 6. Diagnostic Model 与 Importance

诊断模型不是 09C 最终模型。当前只用于 feature foundation 评估：

| target_component | estimator | fit_scope | train rows | train positive rate | weight horizon |
| --- | --- | --- | ---: | ---: | --- |
| fast_fail_only_10d | LogisticRegression | R-core train | 16,603 | 7.5288% | fast_fail_10d |
| false_repair_20d_component | LogisticRegression | R-core train | 16,603 | 38.2581% | cost_bad_10_20_20d |
| hybrid_cost_bad_10_20 | LogisticRegression | R-core train | 16,603 | 39.0532% | cost_bad_10_20_20d |

模型配置已冻结，`diagnostic_model_config_hash = 6e712ff3cdb49f019c3f88616f8b52dbf7e57632a44d6f41ec6c234b2ab4cd34`。R6 的 feature matrix / weights 已 materialize 为 readout-only，但 R6 importance 未 materialize，`r6_importance_status = not_materialized`。

### 6.1 Group MDA：family 级主证据

`fast_fail_only_10d` 的 family 排序非常清楚：FS2 是唯一跨 train / validation / robustness 都稳定领先的 family。但这个领先应解读为“待确认的主假说”，不能直接解读为已验证的泛化 fast-fail alpha，因为 FS2 内部有一半 feature 与 swing-low structural stop label 机制相关。

| target | split | baseline AUC | top family | group MDA AUC drop |
| --- | --- | ---: | --- | ---: |
| fast_fail_only_10d | train | 0.805228 | FS2_basis_path_quality | 0.265357 |
| fast_fail_only_10d | validation | 0.755579 | FS2_basis_path_quality | 0.229910 |
| fast_fail_only_10d | robustness | 0.744471 | FS2_basis_path_quality | 0.237637 |

`false_repair_20d_component` 更依赖 FS0 与 FS3：

| target | split | baseline AUC | top family | group MDA AUC drop |
| --- | --- | ---: | --- | ---: |
| false_repair_20d_component | train | 0.699951 | FS0_baseline_h_features | 0.159806 |
| false_repair_20d_component | validation | 0.707565 | FS3_vol_range_stop_distance | 0.170798 |
| false_repair_20d_component | robustness | 0.704150 | FS0_baseline_h_features | 0.178866 |

`hybrid_cost_bad_10_20` 的结构与 false-repair component 更接近，而不是与 fast-fail-only 更接近：

| target | split | baseline AUC | top family | group MDA AUC drop |
| --- | --- | ---: | --- | ---: |
| hybrid_cost_bad_10_20 | train | 0.687364 | FS0_baseline_h_features | 0.160124 |
| hybrid_cost_bad_10_20 | validation | 0.680330 | FS0_baseline_h_features | 0.134467 |
| hybrid_cost_bad_10_20 | robustness | 0.666408 | FS0_baseline_h_features | 0.177962 |

这说明 hybrid target 的排序任务确实被 false-repair component 主导。09C 不能只报告 hybrid AUC，否则无法判断 `break_swing_low_20` fast-fail 机制是否真的改善 cost sorting。

另一个需要注意的点是 AUC 的经济含义。`fast_fail_only_10d` 的 train positive rate 只有 7.5288%，但 baseline AUC 达到 0.805228，robustness AUC 仍有 0.744471；单个 `return_20d` 在 robustness 上也达到 0.759483。这说明 label 与近期弱势、价格位置高度共测，但不等于模型已经具备可交易的 cost rejection 价值。09C 的核心判据必须是同一个 train-only threshold 下的 accepted cost reduction 与 winner recall retention，而不是 AUC 本身。

### 6.2 Split stability

family rank 的 train-to-robustness 稳定性通过：

| target_component | train/robustness Spearman | top3 overlap | status |
| --- | ---: | ---: | --- |
| false_repair_20d_component | 0.964286 | 2 | pass |
| fast_fail_only_10d | 0.821429 | 2 | pass |
| hybrid_cost_bad_10_20 | 1.000000 | 3 | pass |

`hybrid_cost_bad_10_20` 的 family rank 最稳定，但这不代表它最能回答 fast-fail 问题；它更可能说明 false-repair 结构在 hybrid target 中占主导。

### 6.3 Single Feature Importance

SFI 与 group MDA 一致：fast-fail-only 更看价格位置、basis 与结构距离；hybrid / false-repair 更看 volatility / ATR 与 medium-term path。

fast-fail-only 的 top SFI：

| split | top features |
| --- | --- |
| train | `close_to_ema20` 0.725044；`return_10d` 0.713443；`return_20d` 0.682587 |
| validation | `close_to_ema20` 0.736826；`range_width_ratio_20d_60d` 0.726480；`panel_return_20d_rolling_z_60d` 0.717988 |
| robustness | `return_20d` 0.759483；`close_to_ema20` 0.749334；`return_20d_sigma_norm` 0.743132 |

false-repair component 的 top SFI：

| split | top features |
| --- | --- |
| train | `atr_20_pct` 0.663302；`return_60d` 0.625421；`relative_cusum_20d` 0.616492 |
| validation | `atr_20_pct` 0.715768；`intraday_range_pct` 0.635264；`log_close_fracdiff_d04` 0.633645 |
| robustness | `atr_20_pct` 0.722692；`return_60d` 0.644730；`close_to_ema60` 0.636290 |

hybrid target 的 top SFI：

| split | top features |
| --- | --- |
| train | `atr_20_pct` 0.650112；`return_60d` 0.618379；`relative_cusum_20d` 0.600388 |
| validation | `atr_20_pct` 0.691757；`log_close_fracdiff_d04` 0.616969；`intraday_range_pct` 0.614150 |
| robustness | `atr_20_pct` 0.684702；`return_60d` 0.615066；`market_volatility_20d` 0.614713 |

### 6.4 诊断模型偏向

当前 09B 的 importance 全部来自 config-frozen `LogisticRegression`。这符合 09B 的诊断目标，也保持了可解释性；但线性模型天然更容易捕捉单调动量、价格位置、basis 这类线性可分结构，可能低估 volatility / amount / density 的非线性交互。

因此，09B 的 family importance 应作为 09C feature foundation 依据，而不是最终模型选择依据。09C 至少需要增加一个 shallow tree 或 bagging shallow trees 的诊断对照，用来判断 FS3/FS4/FS6 是否在线性模型下被低估。

---

## 7. Findings

1. **09B 已经从 diagnostic-only 变成 09C 可消费的 feature foundation。**
   关键 contract 全部齐备：target binding complete、sample key unique、feature matrix frozen、transform contract frozen、sample weights frozen、forbidden feature count = 0。

2. **fast-fail-only 的主要信息暂时来自 FS2，但这是待 09C 验证的主假说。**
   `fast_fail_only_10d` 的 group MDA 在 train / validation / robustness 中都由 `FS2_basis_path_quality` 领先，robustness AUC drop 仍有 0.237637。`return_20d`、`return_20d_sigma_norm` 等非 related feature 支持“价格位置 / 路径质量 / 结构距离”这一方向；但 FS2 内部 5/10 feature 与 swing-low structural stop label 机制相关，robustness top-10 SFI 中 related feature 占 40%。因此当前不能声称 FS2 已是泛化 fast-fail signal，只能说它是 09C no-overlap ablation 的首要验证对象。

3. **hybrid target 主要学习 false-repair / volatility 结构。**
   `hybrid_cost_bad_10_20` 的 top family 是 FS0，top SFI 则长期由 `atr_20_pct`、`return_60d`、`relative_cusum_20d`、`market_volatility_20d` 主导。这与 false-repair component 的排序结构高度一致。09C 必须单独报告 fast-fail-only，否则 swing-low fast-fail label 的真实增益会被 hybrid target 掩盖。

4. **新增 stationary hygiene feature 有信号，但不是免费午餐。**
   `panel_return_20d_rolling_z_60d` 在 fast-fail validation SFI 达 0.717988，`log_close_fracdiff_d04` 在 false-repair validation SFI 达 0.633645、hybrid validation SFI 达 0.616969。但这三类 feature 也有约 4.7% overall warmup missing，且 R-core train missing rate 约 6.1%-6.3%，明显高于 validation / robustness 的约 2.3%-2.6%。09C 应保留它们，但必须报告 “without rolling/fracdiff hygiene features” 的敏感性。

5. **R-core 权重显示样本重叠很强，不能忽略 uniqueness。**
   R-core 20D hybrid concurrency mean 为 606.7623，明显高于 10D fast-fail 的 332.1981；average uniqueness 也从 0.003929 降到 0.002210。09C 如果不用冻结权重，容易高估密集事件段中的样本有效性。

6. **PCA 不应进入主流程。**
   当前 family-level MDA、SFI、ablation 已能解释差异，而且 FS2 / FS0 / FS3 的目标差异很清楚。全局 PCA 会把 fast-fail 与 false-repair 的机制差异混在一起，降低 09C 的可审计性。

7. **board fallback 不能被解释为 industry alpha。**
   当前没有 PIT industry artifact。`stock_vs_board_20d` 和 `board_relative_cusum_20d` 可以作为 board/style context，但不能写成 industry relative strength。

8. **高 AUC 不等于已具备 cost-rejection 价值。**
   `fast_fail_only_10d` 的正例率只有 7.5288%，但 baseline AUC train / robustness 分别达到 0.805228 / 0.744471。这说明近期弱势、价格位置和 fast-fail label 有强共测关系；但 09C 必须用 cost / recall frontier 证明其交易价值，不能用 AUC 替代 research-entry gate。

---

## 8. Insight 与 09C 必须注意的事项

09C 不应该把 09B 的 48 个 feature 直接塞进一个 hybrid classifier 然后只看 validation AUC。09B 给出的真正结论是：feature foundation 已冻结，但 fast-fail / false-repair / hybrid 三个问题不能混在一起解释。09C 必须按以下约束设计：

1. **target 分拆评估必须成为硬要求。**
   至少同时训练 / 评估：
   - `fast_fail_only_10d`
   - `false_repair_20d_component`
   - `hybrid_cost_bad_10_20`

   其中 `fast_fail_only_10d` 必须单独报告排序、threshold、cost / recall 结果；不能只用 hybrid target 代表 fast-fail 改善。

2. **主模型以 R-core 为 supported training denominator。**
   R6 只做 readout-only，不进入 fit、feature selection、threshold selection 或 supported gate。

3. **权重按 horizon 精确使用。**
   `fast_fail_only_10d` 用 `fast_fail_10d` 权重；false-repair 与 hybrid 用 `cost_bad_10_20_20d` 权重。不要复用一个通用 sample weight。

4. **必须做机制重叠 ablation。**
   对 `break_swing_low_20` label，至少报告：
   - full feature set
   - remove related range / EMA / ATR features
   - remove FS2 related subset only
   - remove FS0 rolling / fracdiff hygiene features
   - family representative features only

   如果 no-overlap 后 fast-fail sorting 明显塌缩，说明 09B 的 FS2 dominance 主要来自 label-mechanism overlap，不能作为 supported entry signal。

5. **必须控制 warmup / imputation 风险。**
   对 `log_close_fracdiff_d04`、`panel_return_20d_rolling_z_60d`、`panel_return_20d_rolling_pct_60d`，09C 必须报告 per-split missing rate，并做 without rolling/fracdiff hygiene ablation。不要让 train 中更高的 warmup missing rate 变成隐式 split cue。

6. **必须有非线性诊断对照，但不能扩大成模型大网格。**
   LogisticRegression 是 09B 的可解释诊断模型；09C 至少增加一个 shallow tree 或 bagging shallow trees 对照，用于检查 FS3/FS4/FS6 的非线性交互是否被线性模型低估。该对照只用于诊断和稳健性，不应引入新的 threshold overfit。

7. **09C 的核心判断标准不应只是 hybrid AUC。**
   更重要的是：fast-fail-only 排序是否提升；hybrid target 通过同一个 train-only threshold 后，是否同时改善 accepted cost 与 winner recall retention。

8. **不能把 09B complete 理解为 research-entry complete。**
   09B 只证明 feature / target / weight contract 可用，且 diagnostic importance 有可解释读数。09C 仍必须通过 train-only threshold、validation / robustness readout、accepted cost reduction、winner recall retention、bridge retention、E1-missed retention、density / concentration cap 等 gate。

最终判断：09B 已经足够支持 09C 启动，但 09C 的实验设计必须保留 fast-fail-only 与 hybrid target 的并行读数，并把 no-overlap ablation、warmup hygiene ablation、shallow-tree 诊断对照写成硬要求。否则 09C 很可能只学到 false-repair / volatility 排序，或者把 swing-low label 的机制同源特征误读为可泛化 alpha，而没有回答 09A 真正提出的问题：`break_swing_low_20` 是否能改善 risk_on fast-fail cost rejector 的局部排序质量。

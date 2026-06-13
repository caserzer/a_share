# Experiment E - Risk-on Post-Filter Cost Rejector 报告

最终决策：`risk_on_cost_rejector_feature_source_caveated_supported`

## 0. 报告定位

本实验只用于验证一件事：在 R-core / R6 已作为 post-replay recall source 的前提下，是否存在一个 t0 可见的 supervised rejector，能够在保留 bridge / E1-missed capture 的同时过滤 fast-fail / false-repair 成本。

本实验不是正式训练流程，也不是可部署模型训练产物。这里没有做正式超参搜索、模型校准、稳定性选择、交易回测或 production admission；validation split 只作为 diagnostic readout，不能用于阈值微调。本报告中的模型、特征处理和阈值只用于验证该方法是否有信号、是否接近 gate、以及下一阶段是否值得把 rejector 作为 feature source 继续推进。

## 1. 上游状态

E 按 D 的 post-replay event-to-episode membership 与 event-level label source 训练 risk_on 成本 rejector。本轮不继续 C 的 entry-ranker / compression 主线；R-core / R6 被视为 recall source，核心问题从“提高 bridge recall”转为“成本侧 reject”。

- A decision: `density_fast_fail_audit_partial_source_complete`
- B decision: `regime_family_matrix_source_caveated_complete`
- C decision: `risk_on_r_series_ranker_source_caveated_complete`
- D decision: `post_replay_retention_source_source_caveated_complete`
- 因上游仍有 source caveat，E 即使通过也只能输出 caveated supported；本次实际输出为 feature-source caveated supported。

## 2. 样本与 Source

本次进入 supervised rejector 的两个主要 source pool 是 `08_R_core_event_regime_gated` 与 `08_R6_event_regime_gated`。最终 selected source 是 `08_R_core_event_regime_gated`，因为它在 recall retention 与成本下降之间给出了更接近 research-entry gate 的边界。

`08_R_core_event_regime_gated` risk_on 样本：

| split | event n | cost-label complete n | complete rate | raw cost_bad_10_20 rate | daily panel joined rate |
|---|---:|---:|---:|---:|---:|
| train | 16,603 | 16,571 | 99.81% | 42.06% | 100.00% |
| validation | 4,457 | 4,455 | 99.96% | 31.45% | 100.00% |
| robustness | 9,730 | 9,711 | 99.80% | 32.22% | 100.00% |

`08_R6_event_regime_gated` risk_on 样本：

| split | event n | cost-label complete n | complete rate | raw cost_bad_10_20 rate | daily panel joined rate |
|---|---:|---:|---:|---:|---:|
| train | 4,816 | 4,794 | 99.54% | 42.99% | 100.00% |
| validation | 1,441 | 1,440 | 99.93% | 29.31% | 100.00% |
| robustness | 3,003 | 2,996 | 99.77% | 31.58% | 100.00% |

标签对账结果：

- R-core event n: 47,914，label joined n: 47,914，duplicate join n: 0，missing label n: 0，membership label mismatch n: 0。
- R6 event n: 16,204，label joined n: 16,204，duplicate join n: 0，missing label n: 0，membership label mismatch n: 0。
- cost-label complete rate 分别为 R-core `99.86%`、R6 `99.78%`，没有触发 label horizon blocked。

scope reconstruction 结果：

- `08_R_core_event_regime_gated` 使用 A audit 认可的 `source_row_count = 47,914` 作为重建基准；published reference count 是 47,929，差异 `-15` 已在 A 中记录并接受，因此不阻断。
- `08_R6_event_regime_gated` reconstructed event count = 16,204，与 source row count / published reference count 一致。

## 3. Feature Contract

本次 feature contract 共 51 行，其中 47 个字段允许作为 t0 feature，4 个字段被明确 blocked。实际模型矩阵在 selected R-core source 上展开为 54 列：43 个数值特征加 11 个 train-vocabulary one-hot categorical 特征。

### 3.1 Event-envelope features

event-envelope 侧允许的特征共 31 个，其中 27 个作为数值输入，4 个作为 categorical 输入。

数值特征：

```text
return_5d, return_10d, return_20d, return_60d,
stock_vs_market_5d, stock_vs_market_10d, stock_vs_market_20d,
amount_ratio_20d, amount_ratio_60d,
turnover_ratio_20d, turnover_ratio_60d,
close_to_high_60, close_to_high_120,
range_width_ratio_20d_60d, direction_entropy_20d, relative_cusum_20d,
momentum_percentile_20d, momentum_percentile_20d_lag20,
universe_up_share, universe_up_share_z, universe_up_share_change_5d,
stock_vs_board_20d, board_relative_cusum_20d,
atr_pct_rank_60d, ema60_positive_run, family_count, channel_count
```

categorical 特征：

```text
source_pool, board_bucket, event_regime_bucket, primary_family_id
```

selected R-core train vocabulary 展开为 11 个 one-hot 列：

- `source_pool`: `08_R_core_event_regime_gated`
- `event_regime_bucket`: `risk_on`
- `board_bucket`: `chinext`, `main_board`
- `primary_family_id`: `R1_relative_strength_breakout`, `R2_near_high_volume_expansion`, `R3_vcp_breakout`, `R5_growth_or_small_style_confirmation`, `R6_market_breadth_thrust`, `R7_cross_sectional_momentum_rank_jump`, `R8_persistent_distance_above_ema`

### 3.2 Daily panel as-of features

daily panel 来自 `cross_section_feature_panel.parquet`，是 `(date, instrument)` 日频面板，不带事件键。E 使用显式 as-of join：

```text
join key = instrument
join policy = latest same-or-prior date <= event_t0_date
future_join_row_count = 0
missing policy = leave_missing_no_future_fill
```

panel 特征共 16 个，统一加 `panel_` 前缀后进入模型：

```text
panel_return_1d, panel_return_5d, panel_return_20d, panel_return_60d,
panel_stock_vs_market_20d, panel_close_to_high_60,
panel_momentum_percentile_20d, panel_momentum_percentile_60d,
panel_universe_up_share, panel_universe_new_high_60_share,
panel_universe_up_share_z, panel_universe_up_share_change_5d,
panel_board_relative_1d, panel_board_relative_cusum_20d,
panel_board_return_20d, panel_stock_vs_board_20d
```

### 3.3 Blocked fields

以下字段不允许作为 t0 feature，只能用于 label 或 readout，因此被 feature contract blocked：

```text
failure_10_label,
event_false_repair_20d_label,
event_big_winner_120d_label,
target_episode_id
```

leakage audit 对这些字段的处理均为 pass：future label 字段只作为 supervised label 使用，`target_episode_id` 只作为 post-replay readout 使用。

## 4. Feature Processing

本实验已经做了基础数值预处理，但该处理只服务于 feasibility verification，不应被视作正式训练规范。

实际处理顺序：

1. daily panel 先按 `instrument` 与 `date <= event_t0_date` 做 as-of join，禁止未来日期 join；本次 `future_join_row_count = 0`。
2. 数值列使用 train split 中位数填补缺失；若 train 中位数仍缺失，再填 0。
3. 对非负且明显偏态的列做 `log1p`：
   `amount_ratio_20d`, `amount_ratio_60d`, `turnover_ratio_20d`, `turnover_ratio_60d`,
   `ema60_positive_run`, `family_count`, `channel_count`。
4. 使用 train split 的 1% / 99% 分位数做 winsorize。
5. 使用 train split 均值和标准差做 z-score 标准化。
6. categorical 列使用 train split vocabulary 做 one-hot；OOS 中未见过的 category 走 all-zero policy。

记录到 model registry 的 preprocessing policy：

```text
train_median_impute__nonnegative_log1p_selected_numeric__train_winsorize_1_99__train_zscore__categorical_train_vocab_one_hot
```

coverage 上有一个需要注意的点：OOS 表中的 `feature_missing_coverage` 是整体平均 missing coverage，selected model 在 train / validation / robustness 上分别为 `99.48%` / `99.95%` / `99.95%`；但 research-entry gate 使用 feature contract 的逐字段 coverage。逐字段 gate 被 `momentum_percentile_20d_lag20` 卡住，该字段 train missing rate 为 `6.70%`，train coverage 只有 `93.30%`，低于 95%。

## 5. Model

本轮训练了两个 source pool 上的三类 baseline supervised rejector，共 6 个模型：

- `supervised_fast_fail_rejector`，target = `fast_fail_bad_10d`
- `supervised_false_repair_rejector`，target = `false_repair_bad_20d`
- `supervised_joint_cost_rejector`，target = `cost_bad_10_20`

模型类型：

```text
logistic_regression_balanced_l2
```

实现参数：

```text
LogisticRegression(max_iter=1000, class_weight="balanced", C=0.5)
```

selected model：

| field | value |
|---|---|
| source_pool | `08_R_core_event_regime_gated` |
| model_id | `supervised_joint_cost_rejector` |
| target_label | `cost_bad_10_20` |
| train sample n | 16,571 |
| train positive n | 6,969 |
| feature count | 54 |
| feature columns hash | `83ea0338b16d1fa4356589aa0f74c6bec91d9d7807faebcb4087e865cb9e5562` |
| preprocessing hash | `e9caa4fe68aba5b317d09e9f2845400bb7a48d09f290fc6ae2c949b7ecd5061d` |

阈值不是直接调 score cutoff，而是在 keep fraction grid 上选点：

```text
1.00, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60, 0.50
```

本次 selected threshold 是：

```text
supervised_joint_cost_rejector__08_R_core_event_regime_gated__keep_080
```

## 6. Selected Threshold Readout

selected threshold 保留 80% 事件，拒绝约 20% 事件。

| split | selected events | rejected events | reject rate | cost rate before | cost rate after | relative cost reduction |
|---|---:|---:|---:|---:|---:|---:|
| train | 13,274 | 3,329 | 20.05% | 42.06% | 36.09% | 14.17% |
| validation | 4,065 | 392 | 8.80% | 31.45% | 28.55% | 9.21% |
| robustness | 7,730 | 2,000 | 20.56% | 32.22% | 25.62% | 20.48% |

retention readout：

| split | any recall retention | bridge recall retention | raw E1-missed capture n | post-filter E1-missed captured n | E1-missed retention |
|---|---:|---:|---:|---:|---:|
| train | 90.05% | 41.63% | 80 | 76 | 95.00% |
| validation | 72.73% | 31.82% | 13 | 8 | 61.54% |
| robustness | 86.55% | 53.80% | 84 | 71 | 84.52% |

validation 样本较小且只作 diagnostic，不参与阈值微调。

## 7. OOS Separability

selected `supervised_joint_cost_rejector` 没有出现 OOS 反转。robustness ROC-AUC 为 `0.686`，PR-AUC 为 `0.524`，高于 prevalence `0.322`；top-decile lift 为 `2.021`，decile monotonicity 为 `monotone_increasing`。

| split | sample n | positive n | prevalence | ROC-AUC | PR-AUC | top-decile lift | bottom-decile cost rate | brier score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 16,571 | 6,969 | 42.06% | 0.692 | 0.609 | 1.708 | 14.05% | 0.221 |
| validation | 4,455 | 1,401 | 31.45% | 0.682 | 0.493 | 1.939 | 11.88% | 0.207 |
| robustness | 9,711 | 3,129 | 32.22% | 0.686 | 0.524 | 2.021 | 20.88% | 0.225 |

解释：这说明 t0 特征对 cost_bad_10_20 有可见排序能力，尤其 robustness 上 top-decile bad-cost lift 仍为正。但这还不是正式模型质量结论，因为本轮没有做 calibration、model selection stability、feature ablation 或交易层净收益验证。

## 8. Threshold Frontier 与 Gate 差距

当前离 `research_entry` gate 不远，但失败原因分为两类：数值边界与契约缺口。

R-core joint rejector 的关键 frontier：

| keep fraction | train cost reduction | robustness cost reduction | train any retention | robustness any retention | train E1 retention | robustness E1 retention | robustness E1 captured n |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.85 | 11.32% | 16.98% | 90.95% | 88.89% | 97.50% | 86.90% | 73 |
| 0.80 | 14.17% | 20.48% | 90.05% | 86.55% | 95.00% | 84.52% | 71 |
| 0.75 | 16.85% | 23.10% | 88.69% | 84.21% | 93.75% | 79.76% | 67 |
| 0.70 | 19.69% | 26.90% | 86.43% | 79.53% | 91.25% | 71.43% | 60 |

核心 tradeoff：

- `keep_080` 保住了 train any recall gate：`90.05% >= 90%`，但 train cost reduction 是 `14.17%`，离 `15%` 只差 `0.83pp`。
- `keep_075` 成本 gate 已经过：train `16.85%`、robustness `23.10%`，但 train any recall 下降到 `88.69%`，低于 90%，因此不能直接选为 research-entry。
- `keep_070` 成本更好，但 robustness any recall `79.53%` 也跌破 80%，且 robustness E1 retention 只剩 `71.43%`，不适合 admission。

这说明方法不是无信号；它已经在很窄的成本-召回边界附近。下一步如果要冲 research-entry，应该优先解决 feature coverage 与 density config，再重新评估阈值选择规则，而不是事后 cherry-pick frontier 上的单点。

## 9. Density / Concentration

本次 density 可以审计，但没有预声明 research-entry 上限，因此触发 `density_gate_not_configured`。这不是模型信号失败，而是 admission contract 尚未配置。

selected threshold readout：

| metric | value |
|---|---:|
| selected event count | 25,069 |
| formal event-day density | 6.921 |
| p95 density | 19.519 |
| density vs E1 | 3.676 |
| rolling 10d executable event-day density | 1.740 |
| rolling 20d executable event-day density | 2.097 |
| rolling 10d duplicate rate | 50.52% |
| rolling 20d duplicate rate | 61.81% |
| family concentration | 27.17% |
| board concentration | 83.59% |
| density status | `auditable_no_predeclared_gate` |

解释：density readout 已经可复现，但 E requirement 要求 formal density、rolling density、p95 density、family concentration、board concentration 都必须和 E config 的预声明上限比较。当前缺少上限，所以不能声称 research-entry pass。

## 10. Gate Failures

本次没有通过 `research_entry`，原因如下：

1. `cost_reduction_lt_15pct`
   - selected `keep_080` 的 train relative cost reduction 为 `14.17%`，低于 15%。
   - robustness 为 `20.48%`，已经通过。
   - 这是数值边界问题，不是完全失败。

2. `feature_coverage_lt_95pct`
   - gate 使用逐字段 train / robustness coverage。
   - `momentum_percentile_20d_lag20` 的 train missing rate 为 `6.70%`，coverage `93.30%`，低于 95%。
   - 其他缺失较高字段均未超过 5% missing；该问题可以通过剔除该 lag20 特征或补齐源数据后重新跑来验证。

3. `density_gate_not_configured`
   - density 已可审计，但没有 E config 预声明上限。
   - 因此 research-entry 不能通过；feature-source caveated supported 仍成立。

## 11. Findings

1. rejector 方向有效。`supervised_joint_cost_rejector` 在 train、validation、robustness 上 ROC-AUC 都约为 `0.68-0.69`，PR-AUC 均高于 prevalence，robustness top-decile lift 为 `2.021`。这说明 t0 特征对 fast-fail / false-repair 合成成本有可用排序信息。

2. R-core 是更合适的下一阶段 source。R6 更 compact，但在当前 gate 下原始 recall retention 较弱；R-core 的 recall 底座更宽，使 post-filter 后仍能保留 robustness any recall `86.55%` 和 E1-missed retention `84.52%`。

3. 当前最主要的瓶颈不是 separability，而是 admission contract。模型已经在 selected threshold 上实现 robustness cost reduction `20.48%`，同时保留 E1-missed captured n `71`；未通过 research-entry 主要因为 train cost 差 `0.83pp`、一个 lag 特征 coverage 不足、以及 density 上限未配置。

4. threshold frontier 已经显示出清晰 tradeoff。`keep_075` 能让成本过线，但 train any recall 不够；`keep_080` 能让 recall 过线，但成本略低。这意味着后续优化应围绕“在不损失 train any recall 的情况下多拒绝一小部分高成本事件”，而不是继续扩大 recall source。

5. 本轮结果支持“post-filter replay / cost rejector”路线作为下一阶段 meta-label / rejector feature source，但不支持直接作为 entry gate 或交易策略上线。

## 12. 下一步建议

如果继续推进，建议保持本实验的定位：先把它作为 feasibility proof 的后续小修正，而不是直接转成正式训练。

优先顺序：

1. 配置 E 的 density / concentration 上限，并把上限写入 manifest 与报告，避免 `density_gate_not_configured`。
2. 对 `momentum_percentile_20d_lag20` 做二选一处理：剔除该特征，或补齐源数据后重新跑；不要用未来填充。
3. 在同一个 selected-threshold 规则下重新评估 `keep_080` 与 `keep_075` 附近的边界，禁止分别从 cost frontier 和 recall frontier cherry-pick 指标。
4. 若仍接近 gate，再做正式训练需求：固定 train/validation/robustness 切分、特征版本、模型候选集、校准方法、ablation、稳定性检查、交易层净收益验证。

## 13. Artifact Row Counts

- `risk_on_cost_rejector_input_audit`: 29
- `risk_on_cost_rejector_binding_audit`: 14
- `risk_on_cost_rejector_scope_reconstruction_audit`: 4
- `risk_on_cost_rejector_split_alignment_audit`: 251
- `risk_on_cost_rejector_regime_role_audit`: 10
- `risk_on_cost_rejector_event_regime_gate_audit`: 12
- `risk_on_cost_rejector_source_overlap_audit`: 16,196
- `risk_on_cost_rejector_feature_contract`: 51
- `risk_on_cost_rejector_label_source_audit`: 2
- `risk_on_cost_rejector_training_sample_summary`: 6
- `risk_on_cost_rejector_model_registry`: 6
- `risk_on_cost_rejector_oos_separability`: 18
- `risk_on_cost_rejector_threshold_frontier`: 54
- `risk_on_cost_rejector_cost_readout`: 3
- `risk_on_cost_rejector_post_filter_retention_by_split`: 3
- `risk_on_cost_rejector_e1_missed_retention`: 3
- `risk_on_cost_rejector_density_readout`: 1
- `risk_on_cost_rejector_oracle_gap_audit`: 24
- `risk_on_cost_rejector_leakage_audit`: 4
- `risk_on_cost_rejector_decision_tiers`: 1

## 14. 不可声称内容

- 本结果不是可部署交易策略。
- 本结果不是正式训练流程，也不是 official model training recipe。
- D 仍是 source-caveated 时，E 只能作为 research admission / feature-source 证据。
- oracle replay 只用于 gap audit，不得作为 t0 entry/rejector。
- validation 只作 diagnostic readout，不得用于阈值微调。
- 未配置 density gate 前，不得声称 research-entry admission pass。

# Explore6 交易级 Meta-label 失败交易过滤报告

## 1. 核心结论

- 没有形成 Explore6 候选版本。
- 训练样本池已从最终可下单的 `pullback_entry` 扩大为 `raw_pullback_candidate`。模型可以学习更宽的 pullback 失败模式，但组合回放里仍只能过滤 `rule_pullback_entry`，不能新增 raw/looser 买入。
- Train 内 inner selection 有 `5` / `5` 个 fold 可训练，`lgbm_pullback_bad_trade_gate` 已进入外层 valid 组合回放。
- LGBM 未被全局停止，已按外层 WF 输出 gate 回放。
- `lgbm_pullback_bad_trade_gate` 合计 `400` 笔交易，平均 fold 收益 `-2.01%`，平均现金 `94.59%`。
- 路径隔离通过：Explore5 result CSV 用于 label/features/replay 均为 `False`，Explore5 config 中输出路径已重写或忽略：`True`。
- 2025-2026 observed replication 只做观察复现，`used_for_selection = False`。

当前最重要的判断是：扩大样本池后，样本不足问题应由 `candidate_pool_audit.csv` 和 inner selection 审计重新判断；最终是否有 alpha 仍以 walk-forward 组合回放为准，而不是只看分类指标。

## 2. 数据隔离与输入审计

- `source_data_audit.csv` 共记录 `28` 条路径记录，其中 `forbidden_result_path` 为 `3` 条。
- forbidden path 进入计算路径数量：`0`。必须为 0，当前为 0。
- `Explore5/outputs/reports/explore5_final_report.md` 只作为背景文本证据，不参与 label、feature、replay 或 model selection。

| category | paths |
| --- | --- |
| background_reference | 9 |
| forbidden_result_path | 3 |
| rewritten_output_path | 9 |
| structural_input | 7 |


## 3. Raw Pullback 候选池审计

`raw_pullback_candidate` 是训练、打分和 threshold 选择的样本池；`rule_pullback_entry` 是组合回放中实际可被过滤的原规则买入候选。两者必须分开统计，避免扩大训练样本后隐含新增订单。

| calendar_year | raw_pullback_shape | raw_pullback_candidate | rule_pullback_entry | gate_applicable_candidates | raw_to_rule_ratio |
| --- | --- | --- | --- | --- | --- |
| 2017 | 6018 | 6018 | 109 | 109 | 55.21x |
| 2018 | 2652 | 2652 | 3 | 3 | 884.00x |
| 2019 | 4903 | 4903 | 121 | 121 | 40.52x |
| 2020 | 4983 | 4983 | 154 | 154 | 32.36x |
| 2021 | 4466 | 4466 | 33 | 33 | 135.33x |
| 2022 | 3836 | 3836 | 13 | 13 | 295.08x |
| 2023 | 5194 | 5194 | 51 | 51 | 101.84x |
| 2024 | 7227 | 7227 | 255 | 255 | 28.34x |
| 2025 | 6916 | 6916 | 271 | 271 | 25.52x |
| 2026 | 1473 | 1473 | 13 | 13 | 113.31x |


Train 内 select 窗口的候选覆盖如下。这里的 `raw_pullback_candidate` 用于判断 inner selection 是否还有样本不足；`gate_applicable_candidates` 才是未来组合里实际可能被模型过滤的候选。

| fold | start | end | raw_pullback_candidate | rule_pullback_entry | gate_applicable_candidates | bad_trade_count | good_or_neutral_count | raw_to_rule_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WF1 | 2018-01-01 | 2018-12-31 | 2549 | 3 | 3 | 2185 | 364 | 849.67x |
| WF2 | 2019-01-01 | 2019-12-31 | 4447 | 113 | 113 | 3291 | 1156 | 39.35x |
| WF3 | 2020-01-01 | 2020-12-31 | 4639 | 150 | 150 | 3425 | 1214 | 30.93x |
| WF4 | 2021-01-01 | 2021-12-31 | 4118 | 30 | 30 | 3194 | 924 | 137.27x |
| WF5 | 2022-01-01 | 2022-12-31 | 3603 | 12 | 12 | 2969 | 634 | 300.25x |


## 4. Label 生成、样本充足性与不平衡

Label 是 Explore6 独立从 T 日 `pullback` 候选生成的 candidate-level replay，不使用 Explore5 已成交交易结果。每个候选按 100 股、T+1 open、同一止损/退出/成本口径独立回放，忽略组合层面的现金、行业 cap 和排序约束。

| label_status | label_skip_reason | candidates |
| --- | --- | --- |
| completed |  | 39191 |
| skipped | entry_limit_blocked | 23 |
| skipped | invalid_entry_open | 19 |
| skipped | invalid_initial_stop | 46 |


| fold | train_labeled_candidates | bad_trade_count | good_or_neutral_count | minority_class_ratio | trainable | status |
| --- | --- | --- | --- | --- | --- | --- |
| WF1 | 8553 | 6225 | 2328 | 27.22% | True | trainable |
| WF2 | 13089 | 9567 | 3522 | 26.91% | True | trainable |
| WF3 | 18171 | 13200 | 4971 | 27.36% | True | trainable |
| WF4 | 22617 | 16466 | 6151 | 27.20% | True | trainable |
| WF5 | 26558 | 19656 | 6902 | 25.99% | True | trainable |


样本不平衡处理只在 Train 内完成。当前 `bad_trade` 是多数类，所以 `scale_pos_weight = 1`，主要使用 balanced sample weight 调整类别权重。

| fold | bad_trade_count | good_or_neutral_count | bad_class_weight | good_class_weight | scale_pos_weight |
| --- | --- | --- | --- | --- | --- |
| WF1 | 6225 | 2328 | 0.687 | 1.837 | 1 |
| WF2 | 9567 | 3522 | 0.6841 | 1.858 | 1 |
| WF3 | 13200 | 4971 | 0.6883 | 1.828 | 1 |
| WF4 | 16466 | 6151 | 0.6868 | 1.838 | 1 |
| WF5 | 19656 | 6902 | 0.6756 | 1.924 | 1 |


按 fold role 看，valid 里的 bad rate 普遍高于 train，说明失败模式存在时间漂移；这也是必须坚持 walk-forward 和 inner selection 的原因。

| fold | group_value | samples | bad_trades | bad_rate |
| --- | --- | --- | --- | --- |
| WF1 | train | 8642 | 6276 | 72.62% |
| WF1 | valid | 9857 | 6996 | 70.97% |
| WF2 | train | 13532 | 9775 | 72.24% |
| WF2 | valid | 9423 | 6912 | 73.35% |
| WF3 | train | 18499 | 13272 | 71.74% |
| WF3 | valid | 8288 | 6492 | 78.33% |
| WF4 | train | 22955 | 16687 | 72.69% |
| WF4 | valid | 9017 | 7068 | 78.39% |
| WF5 | train | 26787 | 19764 | 73.78% |
| WF5 | valid | 12404 | 9091 | 73.29% |


## 5. Train 内 Inner Selection 结果

外层 Train 不能直接用于 threshold 选择，因此每个 fold 再做 inner fit/select。扩大样本池后，是否仍存在 inner select 覆盖不足，以这里的审计结果为准。

| fold | trainable | inner_method | inner_fit_samples | inner_select_samples | selected_param_id | selected_threshold | skip_reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WF1 | True | first_year_fit_second_year_select | 5675 | 2549 | lgbm_01 | 0.5 |  |
| WF2 | True | expanding_last_year_select | 8553 | 4447 | lgbm_06 | 0.6 |  |
| WF3 | True | expanding_last_year_select | 13089 | 4639 | lgbm_06 | 0.55 |  |
| WF4 | True | expanding_last_year_select | 18171 | 4118 | lgbm_01 | 0.5 |  |
| WF5 | True | expanding_last_year_select | 22617 | 3603 | lgbm_01 | 0.5 |  |


selected 行只来自 Train 内 select，不使用外层 valid。若 LGBM 被全局停止，这些结果只作为诊断；若未停止，则它们决定对应外层 fold 的参数和 gate threshold。

| fold | param_id | threshold | trade_ratio_vs_baseline | avg_cash_ratio | stop_time_ratio_reduction | total_return_with_cost |
| --- | --- | --- | --- | --- | --- | --- |
| WF1 | lgbm_01 | 0.5 | 80.00% | 99.58% | 6.25% | -0.18% |
| WF2 | lgbm_06 | 0.6 | 97.18% | 89.85% | 8.53% | -2.10% |
| WF3 | lgbm_06 | 0.55 | 73.47% | 88.73% | 3.11% | 0.31% |
| WF4 | lgbm_01 | 0.5 | 62.50% | 97.66% | 24.71% | -1.10% |
| WF5 | lgbm_01 | 0.5 | 88.89% | 98.70% | 3.57% | -1.75% |


## 6. 完整组合回放：no model / hard gate / LGBM gate

`no_model_gate` 5 个 fold 合计 `552` 笔交易，平均 fold 收益 `-3.63%`，平均现金 `92.63%`。
`rule_pullback_hard_gate` 合计 `183` 笔交易，平均 fold 收益 `0.19%`，平均现金 `96.85%`。
`lgbm_pullback_bad_trade_gate` 合计 `400` 笔交易，平均 fold 收益 `-2.01%`，平均现金 `94.59%`。

判断 gate 是否有效必须同时看收益、回撤、交易数和现金比例。过滤后如果只是交易数大幅下降或现金显著上升，仍不能单独宣称 alpha 改善。

| fold | version | trades | total_return_with_cost | max_drawdown | avg_cash_ratio | stop_time_trade_ratio |
| --- | --- | --- | --- | --- | --- | --- |
| WF1 | no_model_gate | 168 | -5.22% | -12.14% | 87.36% | 62.50% |
| WF1 | rule_pullback_hard_gate | 66 | -0.83% | -7.14% | 94.64% | 65.15% |
| WF1 | lgbm_pullback_bad_trade_gate | 91 | -2.71% | -6.92% | 93.11% | 71.43% |
| WF2 | no_model_gate | 121 | -3.72% | -6.40% | 91.45% | 62.81% |
| WF2 | rule_pullback_hard_gate | 40 | 2.07% | -2.32% | 96.21% | 60.00% |
| WF2 | lgbm_pullback_bad_trade_gate | 105 | -0.91% | -5.75% | 92.20% | 60.95% |
| WF3 | no_model_gate | 46 | -4.89% | -6.39% | 97.69% | 73.91% |
| WF3 | rule_pullback_hard_gate | 14 | -1.93% | -2.32% | 99.00% | 64.29% |
| WF3 | lgbm_pullback_bad_trade_gate | 40 | -4.78% | -6.07% | 97.97% | 72.50% |
| WF4 | no_model_gate | 50 | -1.85% | -3.24% | 96.86% | 78.00% |
| WF4 | rule_pullback_hard_gate | 17 | 0.87% | -1.19% | 98.43% | 76.47% |
| WF4 | lgbm_pullback_bad_trade_gate | 42 | -0.78% | -2.54% | 97.12% | 73.81% |
| WF5 | no_model_gate | 167 | -2.47% | -7.33% | 89.82% | 57.49% |
| WF5 | rule_pullback_hard_gate | 46 | 0.79% | -2.22% | 95.99% | 65.22% |
| WF5 | lgbm_pullback_bad_trade_gate | 122 | -0.85% | -5.74% | 92.54% | 57.38% |


fold 级相对变化：

| fold | base_trades | candidate_trades | trade_ratio_vs_base | base_return | candidate_return | return_delta | base_drawdown | candidate_drawdown | cash_ratio_delta | stop_time_ratio_reduction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WF1 | 168 | 66 | 39.29% | -5.22% | -0.83% | 4.38% | -12.14% | -7.14% | 7.28% | -4.24% |
| WF2 | 121 | 40 | 33.06% | -3.72% | 2.07% | 5.79% | -6.40% | -2.32% | 4.76% | 4.47% |
| WF3 | 46 | 14 | 30.43% | -4.89% | -1.93% | 2.96% | -6.39% | -2.32% | 1.31% | 13.03% |
| WF4 | 50 | 17 | 34.00% | -1.85% | 0.87% | 2.72% | -3.24% | -1.19% | 1.58% | 1.96% |
| WF5 | 167 | 46 | 27.54% | -2.47% | 0.79% | 3.26% | -7.33% | -2.22% | 6.17% | -13.45% |


LGBM gate 相对 no-model 的 fold 级变化：

| fold | base_trades | candidate_trades | trade_ratio_vs_base | base_return | candidate_return | return_delta | base_drawdown | candidate_drawdown | cash_ratio_delta | stop_time_ratio_reduction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WF1 | 168 | 91 | 54.17% | -5.22% | -2.71% | 2.51% | -12.14% | -6.92% | 5.75% | -14.29% |
| WF2 | 121 | 105 | 86.78% | -3.72% | -0.91% | 2.81% | -6.40% | -5.75% | 0.75% | 2.96% |
| WF3 | 46 | 40 | 86.96% | -4.89% | -4.78% | 0.10% | -6.39% | -6.07% | 0.28% | 1.91% |
| WF4 | 50 | 42 | 84.00% | -1.85% | -0.78% | 1.08% | -3.24% | -2.54% | 0.27% | 5.37% |
| WF5 | 167 | 122 | 73.05% | -2.47% | -0.85% | 1.62% | -7.33% | -5.74% | 2.72% | 0.19% |


## 7. 年度维度解读

年度维度用于检查改善是否只集中在少数年份，或是否靠极端压缩交易获得。LGBM 若进入回放，也必须在这里和 no-model 同表比较。

| calendar_year | version | year_return_with_cost | max_drawdown | trades | net_pnl_sum |
| --- | --- | --- | --- | --- | --- |
| 2019 | lgbm_pullback_bad_trade_gate | -0.99% | -3.47% | 35 | -2.176e+04 |
| 2020 | lgbm_pullback_bad_trade_gate | -0.79% | -5.75% | 71 | 1175 |
| 2021 | lgbm_pullback_bad_trade_gate | -1.67% | -3.50% | 22 | -2.423e+04 |
| 2022 | lgbm_pullback_bad_trade_gate | -2.14% | -2.54% | 15.5 | -1.734e+04 |
| 2023 | lgbm_pullback_bad_trade_gate | 1.07% | -2.54% | 25.5 | 1.108e+04 |
| 2024 | lgbm_pullback_bad_trade_gate | -2.01% | -5.74% | 97 | -2.184e+04 |
| 2019 | no_model_gate | -2.80% | -7.01% | 72 | -4.066e+04 |
| 2020 | no_model_gate | -2.25% | -7.31% | 97.5 | -1.276e+04 |
| 2021 | no_model_gate | -1.97% | -3.50% | 25 | -2.705e+04 |
| 2022 | no_model_gate | -2.30% | -2.87% | 18 | -1.888e+04 |
| 2023 | no_model_gate | 0.05% | -3.26% | 32 | 1006 |
| 2024 | no_model_gate | -2.58% | -6.85% | 135 | -2.741e+04 |
| 2019 | rule_pullback_hard_gate | -1.31% | -5.07% | 31 | -2.297e+04 |
| 2020 | rule_pullback_hard_gate | 1.27% | -2.76% | 35.5 | 2.046e+04 |
| 2021 | rule_pullback_hard_gate | -0.27% | -1.38% | 5 | -8009 |
| 2022 | rule_pullback_hard_gate | -1.13% | -1.55% | 8 | -9380 |
| 2023 | rule_pullback_hard_gate | 1.85% | -1.08% | 9 | 1.891e+04 |
| 2024 | rule_pullback_hard_gate | -1.12% | -2.20% | 37 | -1.169e+04 |


年度相对变化：

| year | base_trades | candidate_trades | trade_ratio_vs_base | base_return | candidate_return | return_delta | base_drawdown | candidate_drawdown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 72 | 31 | 43.06% | -2.80% | -1.31% | 1.49% | -7.01% | -5.07% |
| 2020 | 97 | 35 | 36.41% | -2.25% | 1.27% | 3.52% | -7.31% | -2.76% |
| 2021 | 25 | 5 | 20.00% | -1.97% | -0.27% | 1.70% | -3.50% | -1.38% |
| 2022 | 18 | 8 | 44.44% | -2.30% | -1.13% | 1.17% | -2.87% | -1.55% |
| 2023 | 32 | 9 | 28.12% | 0.05% | 1.85% | 1.80% | -3.26% | -1.08% |
| 2024 | 135 | 37 | 27.41% | -2.58% | -1.12% | 1.45% | -6.85% | -2.20% |


LGBM gate 年度相对变化：

| year | base_trades | candidate_trades | trade_ratio_vs_base | base_return | candidate_return | return_delta | base_drawdown | candidate_drawdown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 72 | 35 | 48.61% | -2.80% | -0.99% | 1.81% | -7.01% | -3.47% |
| 2020 | 97 | 71 | 72.82% | -2.25% | -0.79% | 1.46% | -7.31% | -5.75% |
| 2021 | 25 | 22 | 88.00% | -1.97% | -1.67% | 0.30% | -3.50% | -3.50% |
| 2022 | 18 | 15 | 86.11% | -2.30% | -2.14% | 0.16% | -2.87% | -2.54% |
| 2023 | 32 | 25 | 79.69% | 0.05% | 1.07% | 1.02% | -3.26% | -2.54% |
| 2024 | 135 | 97 | 71.85% | -2.58% | -2.01% | 0.56% | -6.85% | -5.74% |


## 8. 失败交易归因

失败退出仍主要通过 `stop_loss` 和 `time_stop` 暴露。hard gate 能减少部分 pullback 暴露，但没有证明可以在所有年份保留足够交易的同时稳定改善失败退出比例。

| version | fold | calendar_year | dimension | group_value | trades | stop_time_ratio | net_pnl_sum | avg_cost_after_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | entry_type | breakout | 23 | 78.26% | -1.766e+04 | -2.91% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | entry_type | pullback | 12 | 50.00% | -4099 | -1.23% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | exit_reason | ema60_exit | 1 | 0.00% | -4316 | -14.87% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | exit_reason | stop_loss | 2 | 100.00% | -5755 | -9.73% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | exit_reason | time_stop | 22 | 100.00% | -2.465e+04 | -4.16% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | exit_reason | trailing_stop | 10 | 0.00% | 1.296e+04 | 4.42% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | industry_sync | industry_sync_on | 35 | 68.57% | -2.176e+04 | -2.33% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | market_trend | market_trend_on | 35 | 68.57% | -2.176e+04 | -2.33% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | pullback_money | not_pullback | 23 | 78.26% | -1.766e+04 | -2.91% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | pullback_money | pullback_money_other | 2 | 100.00% | -4057 | -6.99% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | pullback_money | pullback_money_weak | 10 | 40.00% | -41.38 | -0.07% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | pullback_top10_20 | False | 28 | 75.00% | -2.393e+04 | -3.18% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | pullback_top10_20 | True | 7 | 42.86% | 2169 | 1.07% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | width | width_neutral | 12 | 66.67% | -1.111e+04 | -3.35% |
| lgbm_pullback_bad_trade_gate | WF1 | 2019 | width | width_strong | 23 | 69.57% | -1.065e+04 | -1.80% |
| lgbm_pullback_bad_trade_gate | WF1 | 2020 | entry_type | breakout | 26 | 73.08% | 7209 | 2.74% |
| lgbm_pullback_bad_trade_gate | WF1 | 2020 | entry_type | pullback | 30 | 73.33% | -1.291e+04 | -1.22% |
| lgbm_pullback_bad_trade_gate | WF1 | 2020 | exit_reason | end_of_backtest | 2 | 0.00% | 1.399e+04 | 38.13% |
| lgbm_pullback_bad_trade_gate | WF1 | 2020 | exit_reason | stop_loss | 15 | 100.00% | -3.993e+04 | -9.27% |
| lgbm_pullback_bad_trade_gate | WF1 | 2020 | exit_reason | time_stop | 26 | 100.00% | -3.253e+04 | -4.62% |


## 9. 分类诊断

`fold_model_metrics.csv` 和 `fold_predictions.csv` 已输出外层 valid 诊断；这些结果只用于评估，不反向修改模型、阈值或样本定义。

| fold | param_id | threshold | valid_labeled_candidates | precision_bad_trade | recall_bad_trade | pr_auc | top_decile_bad_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WF1 | lgbm_01 | 0.5 | 9857 | 0.7141 | 0.6366 | 0.72 | 73.12% |
| WF2 | lgbm_06 | 0.6 | 9423 | 0.7621 | 0.3772 | 0.7604 | 80.49% |
| WF3 | lgbm_06 | 0.55 | 8288 | 0.8018 | 0.3085 | 0.7917 | 80.22% |
| WF4 | lgbm_01 | 0.5 | 9017 | 0.7953 | 0.4668 | 0.784 | 77.16% |
| WF5 | lgbm_01 | 0.5 | 12404 | 0.7125 | 0.5171 | 0.7015 | 63.90% |


## 10. 已观察区间复现

2025-2026 已被前序实验观察过，本节只做一次性复现，不参与任何选择。这里 no-model 版本表现较好，hard gate 虽然降低回撤和交易数，但收益也下降，不能用作反向调参依据。

| version | trades | total_return_with_cost | max_drawdown | avg_cash_ratio | used_for_selection |
| --- | --- | --- | --- | --- | --- |
| no_model_gate | 129 | 23.93% | -5.12% | 81.08% | False |
| rule_pullback_hard_gate | 55 | 14.36% | -3.90% | 88.49% | False |
| lgbm_pullback_bad_trade_gate | 121 | 22.24% | -4.71% | 83.07% | False |


## 11. Selection Decision

- candidate_for_future_final_test: `False`
- reason: `selection_checks_not_met`
- positive_valid_years: `1`
- qualified_valid_years: `1`
- stop_time_ratio_reduction: `-2.12%`
- trade_ratio_vs_no_model: `72.46%`

结论解释：只有当 LGBM 在所有 WF fold 可训练，并且收益、回撤、交易数、现金比例、年度分布和 observed replication 约束全部通过时，才允许标记为 future final test 候选。

## 12. 后续建议

- 若扩大 raw 候选池后 LGBM 仍未形成候选，优先检查时间稳定性和组合层暴露约束，而不是单纯扩大参数搜索。
- 继续保留 `raw_pullback_candidate` 与 `rule_pullback_entry` 的分层审计，避免训练样本扩大后无意中改变真实交易规则。
- 如果仍要推进 meta-label，可以进一步细化 label 的风险/退出类别；但必须保持 2025-2026 不参与选择。
- `breakout` 第一版不应并入模型。它交易少但相对干净，应该单独做 coverage 诊断，而不是和 pullback 混在同一个 bad-trade classifier 中。

## 13. 边界说明

- 当前股票池是 2025-12-31 静态宇宙，不是 point-in-time universe。
- 当前行业归属沿用 Explore4 as-of SW2021 membership，不是 point-in-time industry membership。
- 2025-2026 observed replication 不参与模型、参数或阈值选择。
- `breakout` 在第一版保持非模型规则，仅 `pullback` 候选接受 LGBM gate。

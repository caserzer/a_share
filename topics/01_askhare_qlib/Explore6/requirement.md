# Explore6 需求说明：Trade-level Meta-label 失败交易过滤

## 1. 背景

Explore5 的结论是：当前单纯规则信号组合没有形成可冻结版本。`risk_unit_with_industry_cap` 虽然降低了回撤和集中度，但 2019-2024 的 year-weighted 收益没有稳定转正；`breakout_only_diagnostic` 和 `pullback_regime_gated_diagnostic` 只是诊断版本，低回撤很大程度来自高现金和交易数下降。

Explore5 的关键证据：

- `risk_unit_with_industry_cap` 只有 `1` 个 distinct positive year，`qualified_valid_years = 1`，明显低于冻结门槛。
- 排除 `pullback` 平均收益改善约 `+3.54%`，排除 `pullback_money_weak` 平均改善约 `+3.35%`，排除 `pullback_top10_20` 平均改善约 `+1.94%`。
- `pullback` 在固定权重和风险单位版本中都是主要负贡献来源，风险单位仓位只能降低亏损幅度，不能改变负期望。
- `breakout` 子规则相对更干净，但交易太少，不能直接作为最终策略。
- 亏损主要通过 `stop_loss` 和 `time_stop` 暴露，说明失败交易识别太晚。

Explore6 的核心问题改为：

```text
在不重新发明主 alpha 信号、不使用 2025-2026 调参的前提下，
能否用 T 日可观察的 trade-level meta-label 模型，在入场前识别并过滤高失败概率的规则候选交易，
从而改善 2019-2024 walk-forward 稳定性，同时不把组合退化成高现金、低交易数版本？
```

## 2. 与 Explore5 的关系

Explore6 继承 Explore5 的诊断结论，但必须作为独立阶段管理。

必须遵守：

- Explore6 的配置、脚本、输出和报告必须落在 `Explore6` 目录下。
- 可以读取 Explore5 的 requirement、配置和最终报告作为研究背景、参数口径和审计参考。
- `Explore5/configs/walk_forward_v1.yaml` 只能作为结构性参数来源读取。允许读取的键仅限：
  - `qlib`
  - `costs`
  - `rules`
  - `targets`
  - `explore5.folds`
  - `explore5.candidates`
  - `explore5.selection_thresholds`
- 禁止从 `Explore5/configs/walk_forward_v1.yaml` 读取或沿用任何输出路径，包括但不限于 `paths.cache_dir`、`paths.report_dir`、`paths.backtest_dir`、`paths.target_dir`，以及任何指向 `Explore5/outputs` 的路径。
- 不得读取 Explore5 的 signals、daily candidates、trade detail、portfolio daily、regime CSV 或 year metrics 作为 Explore6 的训练样本、label、模型输入或回放结果。
- 不得修改 Explore5 的配置、脚本、输出或报告。
- 不得把 Explore5 的 diagnostic-only 版本直接提升为 Explore6 冻结版本。
- 不得使用 2025-2026 observed replication 训练、调参、选择阈值或选择模型。
- 2025-2026 只能作为已观察区间复现，且必须单独标记 `used_for_selection = false`。

Explore6 不是重新做全市场 topK alpha 模型。第一版只训练 `pullback_bad_trade_gate`，模型只允许作为二级 gate/filter。训练样本池不再限定为 Explore5 最终可下单的 `pullback_entry`，而是扩大为 T 日可观察的 `raw_pullback_candidate` / looser pullback candidates，用来让模型学习更宽的 pullback 失败模式。但组合回放中，LGBM 仍只能过滤原始规则已经产生的 `rule_pullback_entry`，不得把 raw/looser 候选升级成新增买入。`breakout` 候选不参与第一版模型训练，组合回放时按原规则通过。

## 3. 研究边界

### 3.1 默认结论边界

Explore6 的默认定位是诊断实验，不是实盘策略证明。

报告必须持续保留：

- 当前股票池是 `2025-12-31` 静态宇宙，不是 point-in-time universe。
- 当前行业归属沿用 Explore4 / Explore5 的 as-of SW2021 membership，不是 point-in-time industry membership。
- 2019-2024 的结论只能解释为规则候选交易质量诊断，不是历史可投资业绩证明。
- 2025-2026 已被 Explore3 / Explore4 / Explore5 观察过，只能作为 observed replication。

### 3.2 禁止事项

禁止：

- 训练一个全市场每日收益预测器，然后直接选 topK 股票。
- 训练 all-candidate meta-label 模型，除非后续另起 Explore6 扩展需求。
- 用随机切分训练 / 验证 trade rows。
- 用 2025-2026 的表现选择模型、特征、阈值或版本。
- 用未来收益、未来成交额、未来行业状态、未来市场宽度构造特征。
- 用测试集结果反向修改 label 定义或阈值。
- 只报告 AUC / accuracy，不报告组合回放结果。
- 用模型过滤后交易数大幅下降或现金大幅上升的结果宣称 alpha 改善。
- 直接把 meta-label 版本声明为最终冻结版本，除非满足本需求的稳定性门槛并等待 future final test。

## 4. 数据契约

### 4.1 默认输入

Explore6 默认只读取以下结构性输入：

```text
provider_uri: Explore1/data/qlib/cn_data
source_rule_config: Explore4/configs/trend_rule_v1_frozen.yaml
source_walk_forward_config: Explore5/configs/walk_forward_v1.yaml
source_background_report: Explore5/outputs/reports/explore5_final_report.md
universe: Explore1/data/universe/mcap500_mainboard_20251231.csv
provider_required_fields: $open, $high, $low, $close, $volume, $money, $factor
```

Explore5 的输出 CSV 只能用于人工对照或报告背景引用，不得进入任何计算路径。`source_background_report` 只能作为背景文本证据，不得作为 label、feature、replay、模型选择或阈值选择输入。

路径隔离规则：

- 所有 Explore6 output、cache、report、backtest、generated artifact 路径必须以 `Explore6/` 为根。
- 从 `source_walk_forward_config` 读到的所有 `paths.*` 输出路径必须忽略或重写到 `Explore6/`。
- `source_walk_forward_config` 中任何指向 `Explore5/outputs`、`Explore5/outputs/cache`、`Explore5/outputs/reports` 或 `Explore5/outputs/backtests` 的路径都必须分类为 `forbidden_result_path`，不得进入计算路径。
- `run_manifest.json` 必须记录 `explore5_config_paths_rewritten = true`。

Explore6 必须在自己的脚本中独立重算：

- `signals`
- `daily_candidates`
- `market_width`
- `market_regime`
- `industry_regime`
- `candidate_label_replay`
- `no_model_gate` portfolio replay
- `rule_pullback_hard_gate` portfolio replay
- `lgbm_pullback_bad_trade_gate` portfolio replay

所有结构性输入文件 SHA256 必须写入 manifest，并明确记录：

```text
explore5_result_csv_used_for_label = false
explore5_result_csv_used_for_features = false
explore5_result_csv_used_for_replay = false
explore5_config_paths_rewritten = true
```

### 4.2 样本单位

默认样本单位是 T 日 raw/looser pullback 候选交易，不是股票日线全样本，也不再只是最终规则已经允许下单的 `pullback_entry`。

每一行至少包含：

- `fold`
- `signal_date`
- `order_date` / `deal_date`
- `instrument`
- `entry_type`
- `candidate_source`
- `raw_pullback_candidate`
- `rule_pullback_entry`
- `gate_applicable`
- `rule_version`
- `candidate_rank`
- `trend_score`
- `trend_score_pct`
- `money_ratio20`
- 市场宽度状态
- 市场趋势状态
- 行业同步状态
- T 日以前可观察的价格、成交额、波动率和趋势特征
- 后续用于训练 label 的交易结果字段

训练样本必须从 Explore6 独立生成的 `raw_pullback_candidate` / looser pullback 候选和 Explore6 独立计算的 candidate-level label 中构造，不得从 Explore5 已执行交易构造 label。模型打分时覆盖同一口径生成的 T 日 raw/looser pullback 候选池。组合回放时，模型 gate 只能作用于同时满足原始规则 `rule_pullback_entry = true` 的候选；`raw_pullback_candidate = true` 但 `rule_pullback_entry = false` 的样本只用于训练、打分和诊断，不得产生新订单。`breakout` 交易必须从训练集、阈值选择和模型打分样本中排除，只在组合回放中作为原规则交易保留。报告必须区分：

- `train_labeled_candidates`：Explore6 独立生成并完成 candidate-level label replay 的 Train 内 raw/looser pullback 候选样本。
- `scored_candidates`：模型打分的 T 日 raw/looser pullback 候选样本。
- `gate_applicable_candidates`：模型打分后，在组合回放中实际允许被 gate 过滤的原始规则 `rule_pullback_entry` 候选样本。
- `portfolio_replayed_trades`：模型 gate 后完整组合回放实际成交样本。

### 4.2.1 默认 raw/looser pullback candidate 定义

第一版必须同时生成并审计三层 pullback 候选：

1. `raw_pullback_shape`
   - 只描述 T 日回踩形态，不要求 market / width / industry / trend_score top20 通过。
   - 默认公式：
   ```text
   raw_pullback_shape =
       (low <= ema20 * (1 + ema_band_pct)
        or low <= ema30 * (1 + ema_band_pct))
       and low > ema60
       and close >= ema20
       and close > open
   ```

2. `raw_pullback_candidate`
   - 第一版训练样本池。
   - 在 `raw_pullback_shape` 之上保留最小趋势和流动性约束，但不叠加 market / width / industry / trend_score top20 gate。
   - 默认公式：
   ```text
   raw_pullback_candidate =
       raw_pullback_shape
       and ema20 >= ema60
       and close > ema60
       and money_ratio20 <= loose_money_ratio_upper
   ```
   - `loose_money_ratio_upper` 默认 `1.20`，必须写入 Explore6 config。

3. `rule_pullback_entry`
   - 原始 Explore5 组合回放中真正可下单的 pullback entry。
   - 必须保持原始闭合定义，即当前 `pullback_entry` 的口径：
   ```text
   rule_pullback_entry =
       trend_score_top20_entry
       and raw_pullback_shape
       and money_ratio20 <= 1.00
   ```
   - 其中 `trend_score_top20_entry` 已经包含 `ema_state`、broad market trend、market width、industry trend 和 top20 score gate。

模型训练和 threshold 选择使用 `raw_pullback_candidate`；组合回放中 `lgbm_pullback_bad_trade_gate` 只允许过滤 `rule_pullback_entry`。如果某个 raw candidate 不满足 `rule_pullback_entry`，即使模型预测低失败概率，也不得新增买入。必须产出 `candidate_pool_audit.csv`，按 fold、calendar year、inner split 统计 `raw_pullback_shape`、`raw_pullback_candidate`、`rule_pullback_entry`、`gate_applicable_candidates` 的数量和比例。

### 4.3 时间切分

Explore6 沿用 Explore5 的 2019-2024 walk-forward valid 思路，但模型训练必须严格按时间推进。

默认 folds：

| Fold | Train | Valid |
| --- | --- | --- |
| WF1 | 2017-01-01 到 2018-12-31 | 2019-01-01 到 2020-12-31 |
| WF2 | 2017-01-01 到 2019-12-31 | 2020-01-01 到 2021-12-31 |
| WF3 | 2017-01-01 到 2020-12-31 | 2021-01-01 到 2022-12-31 |
| WF4 | 2017-01-01 到 2021-12-31 | 2022-01-01 到 2023-12-31 |
| WF5 | 2017-01-01 到 2022-12-31 | 2023-01-01 到 2024-12-31 |

每个 fold 必须只用该 fold 的 Train 样本训练模型和选择 gate 阈值。Valid 只用于 fold 评估，不得反向调整该 fold 的模型参数。最终报告必须同时输出 fold 维度和 distinct calendar year 维度。

### 4.3.1 Train 内选择纪律

外层 Train 不能同时用于模型拟合结果的原样评估和 threshold 选择。每个外层 fold 必须在 Train 内再做时间序列内层选择。

默认内层选择方式：

- 对外层 Train 生成 inner train / inner select 切分。
- 若外层 Train 覆盖至少 3 个 calendar years，使用 expanding inner folds，最后一年或最后两个半年度窗口作为 inner select。
- 若外层 Train 只有 2 个 calendar years，使用第一年 fit、第二年 select；若样本不足，外层 fold 标记为 `insufficient_inner_selection_coverage`。
- LGBM 参数组合和 gate threshold 只能基于 inner select 或 rolling out-of-fold predictions 选择。
- 不得使用外层 Train 的 in-sample fitted predictions 选择参数或 threshold。
- 选定参数和 threshold 后，才允许在完整外层 Train 上重新拟合最终 fold model，并应用到外层 Valid。

必须产出 `inner_selection_audit.csv`，记录每个外层 fold 的 inner split、fit/select 样本数、可训练状态、入选参数、入选 threshold 和跳过原因。

### 4.4 独立 Label 生成

Explore6 必须先运行独立 label generation 阶段，不能使用 Explore5 的交易结果作为 label。

默认流程：

1. 从 `provider_uri` 和结构性配置重算全窗口 T 日特征、regime 和候选。
2. 对每个 fold 的 Train 和 Valid 分别生成 `raw_pullback_candidate` 候选池，并同时标记其中是否满足原始 `rule_pullback_entry`。
3. 对每个 `raw_pullback_candidate` 执行 candidate-level label replay：
   - 假设该候选在 T+1 open 以 A 股最小可交易单位 `100` 股独立开仓。
   - 使用与 `risk_unit_with_industry_cap` 相同的入场、初始止损、trailing stop、time stop、EMA exit 和交易成本口径。
   - 忽略组合层面的现金、最大持仓数、行业 cap 和同日排序约束。
   - 保留真实停牌、缺价、涨跌停或无法成交的异常状态，并在 `label_generation_audit.csv` 中记录。
4. 用 candidate-level replay 结果生成 `bad_trade`、`good_trade` 和 `three_class_label`。
5. 完整 portfolio replay 仍然只用于评估 `no_model_gate`、`rule_pullback_hard_gate` 和 `lgbm_pullback_bad_trade_gate` 的组合表现。

Candidate-level label replay 的目的只是扩大和去偏训练样本，不代表组合收益。最终选择仍必须依据完整组合回放。

禁止：

- 直接读取 `Explore5/outputs/reports/fold_trade_detail.csv` 作为 label。
- 只给 baseline 已成交交易或最终 `rule_pullback_entry` 打 label，而忽略 raw/looser pullback 候选。
- 用 Valid 或 observed replication 的 label 分布补充 Train 样本。
- 把 candidate-level replay PnL 当作组合 PnL。

### 4.5 Observed Replication

2025-2026 observed replication 不参与任何模型、特征、参数或 threshold 选择。

默认 observed replication 方式：

- 使用 `2017-01-01` 到 `2024-12-31` 作为 observed replication 的 final training window。
- 在该 final training window 内继续使用第 4.3.1 节的 inner selection 纪律选择 LGBM 参数和 threshold。
- 选定后在完整 `2017-2024` final training window 上重新拟合模型，再一次性应用到 2025-2026 observed replication。
- 如果 final training window 样本不足或 inner selection 不足，则 observed replication 只输出 `no_model_gate` 和 `rule_pullback_hard_gate`，不得输出 LGBM observed replication。
- observed replication 报告必须标记 `used_for_selection = false`。

## 5. Label 定义

### 5.1 Primary label

默认 primary label 为失败交易识别：

```text
bad_trade = 1
    if exit_reason in ["stop_loss", "time_stop"]
    or cost_after_return <= -0.02
    or R <= -0.50
else 0
```

如果某些字段不存在，实现者必须在 `label_audit.csv` 中说明实际可用字段和替代逻辑。替代逻辑必须在运行前固定，不得根据 valid 表现调整。

### 5.2 Secondary labels

必须同时产出 secondary label 审计，但默认不用于第一版模型选择：

```text
good_trade = 1
    if exit_reason == "trailing_stop"
    or cost_after_return >= 0.03
    or R >= 1.00

three_class_label:
    good / neutral / bad
```

Secondary labels 用于检查 primary label 是否过度依赖某个 exit_reason，不用于扩大默认搜索空间。

### 5.3 Label 审计

必须输出 label 分布：

- 按 fold。
- 按 calendar year。
- 按 `entry_type`。
- 按 `pullback_money_weak`。
- 按 `pullback_top10_20`。
- 按市场宽度、市场趋势和行业同步状态。

如果某个 fold 的 Train label 样本不足，模型版本必须标记为 `insufficient_label_coverage`，不得进入候选选择。

### 5.4 样本不平衡处理

Explore6 预期会遇到 `bad_trade` 正负样本不平衡，尤其是在按 fold 和 pullback 子集训练时。处理方式必须在 Train 内完成，不得使用 Valid 或 observed replication 的 label 分布。

默认处理流程：

1. 先做样本充足性和 label audit：
   - 样本统计只基于 Explore6 独立生成的 Train 内 `train_labeled_candidates`。
   - 按 fold、calendar year、`pullback_money_weak`、`pullback_top10_20`、市场宽度、市场趋势和行业同步状态统计 `bad_trade` 正负样本。
   - 每个 fold 的 Train 中，`train_labeled_candidates < 100` 时，该 fold 标记为 `insufficient_label_coverage`。
   - 每个 fold 的 Train 中，任一类别样本数低于 `30`，或少数类占比低于 `5%`，该 fold 标记为 `insufficient_label_coverage`。
   - 被标记的 fold 不训练模型，也不得用 Valid 结果、observed replication 结果或 Explore5 结果补救。
   - 若可训练 folds 少于 `3` 个，Explore6 必须停止 LGBM 训练，只输出 label generation、样本充足性和 no-model replay 报告。

2. 优先使用 Train 内 balanced sample weight：
   - 每个 fold 只在 Train 内计算类别权重。
   - `bad_trade = 1` 的样本权重为 `n_total / (2 * n_bad)`。
   - `bad_trade = 0` 的样本权重为 `n_total / (2 * n_good)`。
   - 单类权重必须设置上限，默认 `class_weight_cap = 10`。
   - 实际样本权重为 `min(raw_class_weight, 10)`。
   - 如果实现同时使用 LightGBM `scale_pos_weight`，只有当 `bad_trade` 是少数类时才允许设置 `scale_pos_weight = min(n_good / n_bad, 10)`；如果 `bad_trade` 是多数类，`scale_pos_weight` 必须为 `1`，并使用 sample weight 处理类别平衡。

3. 不默认使用过采样：
   - 第一版禁止 SMOTE、随机过采样和跨年份复制少数类样本。
   - 若后续确需采样，只能作为扩展实验，并且必须标记为 `exploratory`，不得进入候选选择。

4. 阈值选择不固定为 `0.5`：
   - 类别不平衡下，模型概率排序优先于默认分类阈值。
   - gate threshold 仍按第 7.3 节在 Train 内选择。
   - 阈值选择必须同时约束交易数和现金比例，防止模型靠大幅少交易获得改善。

5. 分类指标必须使用不平衡友好的指标：
   - `precision_bad_trade`
   - `recall_bad_trade`
   - `pr_auc`
   - `top_decile_bad_rate`
   - `filtered_trade_bad_rate`
   - `kept_trade_bad_rate`

6. 组合回放必须保持原始候选分布：
   - class weight 只影响模型训练。
   - replay 必须使用原始 T 日候选流和真实交易顺序。
   - 不得为了平衡样本而改变组合回放中的候选数量、日期分布或 entry_type 分布。

样本充足性目标：

- 目标状态：每个可训练 fold 的 Train 至少有 `200` 个 `train_labeled_candidates`。
- 硬门槛：每个可训练 fold 的 Train 至少有 `100` 个 `train_labeled_candidates`，且正负类各不少于 `30`。
- 如果某个 fold 低于目标但高于硬门槛，报告必须标记为 `low_sample_warning`。
- 如果某个 fold 低于硬门槛，该 fold 的模型输出必须为空，组合回放只能使用 `no_model_gate` 和 `rule_pullback_hard_gate`。
- 如果任一外层 fold 不可训练，`lgbm_pullback_bad_trade_gate` 不得被报告为 `candidate_for_future_final_test`；该 fold 在稳定性选择中按失败处理。

## 6. 特征约束

### 6.1 允许特征

只允许使用 T 日收盘前可观察特征。

默认特征组：

1. 规则特征：
   - `entry_type`
   - `trend_score`
   - `trend_score_pct`
   - `candidate_rank`
   - `distance_to_ema20`
   - `distance_to_ema60`
   - `pullback_depth`

2. 成交额和流动性特征：
   - `money_ratio20`
   - `volume_ratio20`
   - `money_zscore20`
   - 近 5 / 20 日成交额变化

3. 趋势和波动特征：
   - 近 5 / 20 / 60 日收益
   - 近 20 日波动率
   - ATR 或同口径风险距离
   - EMA20 / EMA60 斜率
   - 距离近期高点和低点

4. Regime 特征：
   - 市场宽度
   - broad market trend
   - industry trend
   - industry_sync
   - width bucket

5. 风险控制上下文审计字段：
   - initial risk distance
   - planned position weight
   - industry exposure before order
   - current cash ratio before order

风险控制上下文字段在第一版默认不进入 LGBM 模型，只能进入 `feature_audit.csv` 和回放归因。原因是这些字段依赖组合状态和订单顺序，而 candidate-level label replay 忽略现金、最大持仓数、行业 cap 和同日排序约束。若后续要把这些字段纳入模型，必须另起扩展需求，明确它们在未成交候选、hard gate 后候选和 LGBM gate 后候选中的计算方式。

### 6.1.1 默认特征公式

第一版特征必须从 Explore6 独立生成的 `generated_signals.csv`、`generated_market_width.csv`、`generated_market_regime.csv` 和 `generated_industry_regime.csv` 中按固定公式生成。

默认公式：

| 特征 | 默认公式 |
| --- | --- |
| `candidate_rank` | 同一 `signal_date` 内按 `trend_score_pct` 升序排名，缺失值排最后，同分按 `instrument` 升序 |
| `distance_to_ema20` | `close / ema20 - 1` |
| `distance_to_ema60` | `close / ema60 - 1` |
| `pullback_depth` | `close / rolling_high60 - 1` |
| `volume_ratio20` | `volume / rolling_mean(volume, 20)` |
| `money_zscore20` | `(money - rolling_mean(money, 20)) / rolling_std(money, 20)` |
| `ret5` | `close / close.shift(5) - 1` |
| `ret20` | `close / close.shift(20) - 1` |
| `ret60` | `ret60`，若已在 signals 中生成则直接读取，否则按 `close / close.shift(60) - 1` 重算 |
| `volatility20` | `std(daily_return, 20)` |
| `atr20_ratio` | `atr20 / close` |
| `ema20_slope20` | `ema20 / ema20.shift(20) - 1` |
| `ema60_slope20` | `ema60 / ema60.shift(20) - 1` |
| `distance_to_high60` | `close / rolling_high60 - 1` |
| `distance_to_low20` | `close / rolling_low20 - 1` |

如果某个默认特征无法按上述公式从 T 日可观察字段计算，必须从模型输入中剔除，并在 `feature_audit.csv` 记录原因。不得用 Explore5 result CSV 补齐缺失特征。

### 6.2 禁止特征

禁止使用：

- T+1 或更晚的价格、成交额和收益。
- 交易退出后的收益、最大浮盈、最大浮亏、持有天数等结果字段。
- 2025-2026 统计出来的分位数、阈值或 target encoding。
- 使用完整样本预先计算的标准化参数。
- 对 `instrument` 做高泄露的直接 target encoding，除非只在每个 fold 的 Train 内拟合并有单独审计。

所有标准化、缺失值填充、类别编码、分位数截断都必须在每个 fold 的 Train 内拟合，然后应用到 Valid。

## 7. 模型设计

### 7.1 默认模型

默认模型为 LightGBM binary classifier。

第一版只允许以下模型族：

- `constant_gate_baseline`：不使用模型，只用固定规则过滤作为基线。
- `lgbm_pullback_bad_trade_classifier`：唯一允许训练的主实验模型，只训练 `candidate_source = raw_pullback_candidate` 且 `entry_type = pullback` 的样本。

不得在第一版引入神经网络、CatBoost、XGBoost 或大规模 AutoML。若后续引入，必须作为 Explore6 扩展需求单独说明。

### 7.2 默认训练目标

模型目标是预测：

```text
P(bad_trade = 1 | T-day observable raw/looser pullback candidate features)
```

组合使用方式：

```text
skip candidate if bad_trade_probability >= threshold
```

模型不得直接输出目标仓位，不得直接替代原始规则排序。原始规则仍负责产生最终可下单候选和排序，Explore6 模型只负责 gate。

第一版模型只对 `raw_pullback_candidate` 产生 `bad_trade_probability`。组合回放时只对 `rule_pullback_entry = true` 的 pullback 候选应用该概率；`raw_pullback_candidate = true` 但 `rule_pullback_entry = false` 的候选不得新增交易。`entry_type = breakout` 的候选不得送入模型，也不得因为缺少模型分数被过滤。

### 7.3 阈值选择

每个 fold 的 gate threshold 必须只在 Train 内选择，并且只能基于 inner select 或 rolling out-of-fold predictions 选择。不得使用外层 Train 的 in-sample fitted predictions 选择 threshold。

默认阈值候选：

```text
bad_prob_threshold: [0.50, 0.55, 0.60, 0.65, 0.70]
```

选择准则优先级：

1. Inner select / OOF 回放中过滤后交易数不得低于原始 baseline 的 `60%`。
2. Inner select / OOF 回放中平均现金比例不得高于原始 baseline `+10` 个百分点。
3. 在满足 1 和 2 的阈值中，选择 stop_loss + time_stop 占比下降最多者。
4. 若差距小于 `3` 个百分点，选择成本后收益更高者。
5. 若仍并列，选择更低阈值，避免过度乐观过滤。

外层 Valid 和 observed replication 不得用于选择阈值。

### 7.4 搜索纪律

默认只允许一个小规模 LGBM 搜索空间，且只用于 `lgbm_pullback_bad_trade_classifier`：

| 参数 | 候选值 |
| --- | --- |
| `num_leaves` | `15`, `31` |
| `learning_rate` | `0.03`, `0.05` |
| `min_data_in_leaf` | `20`, `50` |
| `feature_fraction` | `0.70`, `0.90` |
| `lambda_l1` | `0`, `10` |
| `lambda_l2` | `10`, `50` |

不得做全量笛卡尔积。默认最多评估 `8` 个预定义组合，组合清单必须写入 config。LGBM 参数组合只能基于 inner select / OOF 结果选择。若实现者增加组合，必须在报告中标记为 `exploratory`，不得进入候选选择。

## 8. 回放要求

模型评估不能停留在分类指标，必须执行完整组合回放。

回放规则：

- 在 T 日原始 `rule_pullback_entry` 候选生成后、订单生成前应用模型 gate。
- 被 gate 过滤的原始规则候选不得在同日下单。
- raw/looser pullback 候选只提供训练和打分覆盖；不满足 `rule_pullback_entry` 的 raw 候选不得进入订单生成。
- 过滤后必须重新计算订单、现金、持仓、行业 cap、风险预算、交易成本和回撤。
- 不得只在交易明细事后删除亏损交易。
- 必须保留 `risk_unit_with_industry_cap` 作为主要 baseline。
- 必须保留一个 `no_model_gate` 基线，使用与 Explore5 candidate baseline 相同的规则口径，但由 Explore6 独立重算信号、订单、成交、持仓和交易结果。

默认比较版本：

1. `no_model_gate`
   - 不使用 meta-label。
   - 作为组合回放基线。

2. `rule_pullback_hard_gate`
   - 固定过滤条件为：
   ```text
   entry_type = pullback
   and (
       0.60 <= money_ratio20 <= 1.00
       or 0.10 < trend_score_pct <= 0.20
   )
   ```
   - 即固定过滤 Explore5 已发现的问题子集 union：`pullback_money_weak OR pullback_top10_20`。
   - 作为唯一非模型 hard-gate baseline。
   - 报告中可以单独拆分 `pullback_money_weak` 和 `pullback_top10_20` 的贡献，但不得改变该 hard-gate baseline 的闭合定义。

3. `lgbm_pullback_bad_trade_gate`
   - 训练和打分使用 `raw_pullback_candidate`。
   - 完整组合回放中只对原始 `rule_pullback_entry` 候选应用模型 gate。
   - 不得把 raw/looser 候选转化为新增买入。
   - 第一优先主实验。

第一版不得包含 `lgbm_all_candidate_bad_trade_gate`。若后续需要 all-candidate 模型，必须另起扩展需求，并重新定义样本、标签、泄露检查和选择准则。

## 9. 选择准则

Explore6 不以 AUC 作为最终选择标准。模型分类指标只作为辅助诊断。

`lgbm_pullback_bad_trade_gate` 若要被报告为 `candidate_for_future_final_test`，必须在 2019-2024 distinct-year 维度同时满足：

1. WF1 到 WF5 全部外层 folds 都满足 Train 样本硬门槛、inner selection 样本门槛，并成功产出 LGBM fold model。
2. `positive_valid_years >= 3`。
3. `qualified_valid_years >= 4`，其中 controlled flat year 定义沿用 Explore5。
4. 相对 `no_model_gate`，`stop_loss + time_stop` 交易占比下降至少 `15%`。
5. 交易笔数不得低于 `no_model_gate` 的 `60%`。
6. 平均现金比例不得高于 `no_model_gate + 10` 个百分点。
7. 最差年度回撤不得比 `no_model_gate` 更差。
8. 任一 distinct year 不得贡献超过全部正收益 year PnL 的 `45%`。
9. 2025-2026 observed replication 不参与任何选择字段。

如果模型版本只通过大幅降低交易数、提高现金或关闭 pullback 获得改善，报告必须降级为：

```text
diagnostic_only: improvement mainly comes from exposure reduction, not proven alpha selection
```

## 10. 产物要求

Explore6 至少产出：

```text
Explore6/requirement.md
Explore6/configs/
Explore6/configs/meta_label_v1.yaml
Explore6/scripts/
Explore6/outputs/reports/run_manifest.json
Explore6/outputs/reports/source_data_audit.csv
Explore6/outputs/reports/generated_signals.csv
Explore6/outputs/reports/generated_daily_candidates.csv
Explore6/outputs/reports/generated_market_width.csv
Explore6/outputs/reports/generated_market_regime.csv
Explore6/outputs/reports/generated_industry_regime.csv
Explore6/outputs/reports/candidate_label_replay.csv
Explore6/outputs/reports/candidate_pool_audit.csv
Explore6/outputs/reports/label_generation_audit.csv
Explore6/outputs/reports/sample_sufficiency_audit.csv
Explore6/outputs/reports/meta_label_dataset.csv
Explore6/outputs/reports/label_audit.csv
Explore6/outputs/reports/class_imbalance_audit.csv
Explore6/outputs/reports/feature_audit.csv
Explore6/outputs/reports/inner_selection_audit.csv
Explore6/outputs/reports/inner_oof_predictions.csv
Explore6/outputs/reports/fold_model_metrics.csv
Explore6/outputs/reports/fold_threshold_selection.csv
Explore6/outputs/reports/fold_predictions.csv
Explore6/outputs/reports/no_model_gate_trade_detail.csv
Explore6/outputs/reports/no_model_gate_portfolio_daily.csv
Explore6/outputs/reports/fold_replay_metrics.csv
Explore6/outputs/reports/year_metrics.csv
Explore6/outputs/reports/trade_failure_attribution.csv
Explore6/outputs/reports/observed_replication_summary.csv
Explore6/outputs/reports/explore6_meta_label_report.md
```

`run_manifest.json` 至少记录：

- 结构性输入文件路径和 SHA256。
- Explore5 background requirement / config / final report 路径和 SHA256。
- `explore5_result_csv_used_for_label`，必须为 `false`。
- `explore5_result_csv_used_for_features`，必须为 `false`。
- `explore5_result_csv_used_for_replay`，必须为 `false`。
- `explore5_config_paths_rewritten`，必须为 `true`。
- provider_uri、market、benchmark、required_fields。
- universe source、universe as-of date、是否 point-in-time。
- industry membership 来源、是否 point-in-time。
- fold 定义。
- label 定义。
- independent label generation 方法、candidate-level replay 口径和异常处理。
- 每个 fold 的样本充足性状态、`train_labeled_candidates`、正负类样本数和是否可训练。
- inner selection / OOF 方法、每个 fold 的 inner split、入选参数和入选 threshold。
- class imbalance 处理方式、每个 fold 的类别分布、balanced class weights、`class_weight_cap` 和可选 `scale_pos_weight`。
- feature 列表和禁止特征检查结果。
- 每个 fold 的 Train / Valid 样本数。
- LGBM 参数组合清单。
- 阈值候选和每个 fold 的入选阈值。
- `observed_replication_used_for_selection`，必须为 `false`。
- 是否形成 `candidate_for_future_final_test`。

## 11. 报告必须回答的问题

Explore6 最终报告必须回答：

- 当前规则候选交易是否存在可被 T 日特征识别的失败模式。
- Explore6 是否独立重算了 signals、候选、label 和 no-model replay，且没有使用 Explore5 result CSV 作为训练或回放输入。
- 每个 fold 的 Train 样本是否足够训练 pullback bad-trade model。
- LGBM pullback gate 是否比简单 hard gate 更好。
- 改善主要来自更好地区分 pullback 质量，还是来自关闭交易、提高现金。
- `pullback_money_weak` 和 `pullback_top10_20` 的失败是否被模型提前识别。
- breakout 在第一版中是否应该继续保持非模型规则，还是需要单独 coverage 诊断。
- 分类指标和组合回放指标是否一致。
- 哪些年份和 folds 仍失败，失败是否集中在 2019、2021-2022 或 2024。
- 模型特征重要性是否稳定，是否过度依赖单个 regime 或 entry_type。
- 是否存在可等待 future final test 的候选版本。
- 如果不存在，下一步应继续做 point-in-time 数据修复、pullback 规则重定义，还是 breakout coverage 研究。

## 12. 测试计划

静态检查：

```text
uv run python -m compileall Explore6/scripts
uv run python Explore6/scripts/run_explore6.py self-test
```

产物生成：

```text
uv run python Explore6/scripts/run_explore6.py all --config Explore6/configs/meta_label_v1.yaml
```

内容验收：

- `source_data_audit.csv` 必须确认结构性输入存在且 SHA256 已记录，并确认 Explore5 result CSV 未用于 label、feature 或 replay。
- `source_data_audit.csv` 必须列出每一个从配置或背景文件读取到的路径，并按以下闭合集合分类：`structural_input`、`background_reference`、`rewritten_output_path`、`forbidden_result_path`。
- 如果任何 `forbidden_result_path` 被用于 label、feature、replay、模型训练、模型选择或 threshold 选择，`self-test` 和 `all` 命令都必须失败。
- `source_data_audit.csv` 必须证明 `source_walk_forward_config` 中的 Explore5 `paths.cache_dir`、`paths.report_dir`、`paths.backtest_dir`、`paths.target_dir` 没有被沿用为 Explore6 计算路径。
- `generated_signals.csv` 和 `generated_daily_candidates.csv` 必须由 Explore6 独立生成。
- `candidate_label_replay.csv` 必须覆盖 Train / Valid 内生成的 `raw_pullback_candidate`，并包含 label 结果、异常状态、`candidate_source` 和 `rule_pullback_entry` 标记。
- `candidate_pool_audit.csv` 必须证明训练样本池从最终 `pullback_entry` 扩大到了 raw/looser pullback candidates，并按 fold/year/inner split 展示各层候选数量。
- `label_generation_audit.csv` 必须记录无法生成 label 的候选及原因。
- `sample_sufficiency_audit.csv` 必须记录每个 fold 的 Train 样本数、正负类样本数、目标门槛、硬门槛和可训练状态。
- `meta_label_dataset.csv` 必须区分 train_labeled_candidates、scored_candidates 和 portfolio_replayed_trades。
- `label_audit.csv` 必须按 fold、year、entry_type 和关键 regime 输出 label 分布。
- `class_imbalance_audit.csv` 必须记录每个 fold 的正负样本数、少数类占比、是否 `insufficient_label_coverage`、balanced class weights、`class_weight_cap` 和可选 `scale_pos_weight`。
- `feature_audit.csv` 必须确认所有特征均为 T 日可观察。
- `inner_selection_audit.csv` 必须证明 LGBM 参数和 threshold 只用 inner select / OOF predictions 选择。
- `inner_oof_predictions.csv` 必须保存 inner select / OOF 样本的 `bad_trade_probability`、真实 label、参数组合、threshold 候选和是否被 gate 过滤。
- 每个 fold 的模型只能使用该 fold Train 数据训练。
- 每个可训练 fold 必须满足 Train 样本硬门槛；不可训练 fold 不得输出 LGBM 模型或 Valid 模型选择结果。
- 模型训练样本必须全部为 `candidate_source = raw_pullback_candidate` 且 `entry_type = pullback`；`breakout` 不得进入训练、阈值选择或模型打分。
- 完整组合回放中，LGBM gate 只能过滤 `rule_pullback_entry = true` 的候选；不得把 `rule_pullback_entry = false` 的 raw candidates 变成新交易。
- `fold_threshold_selection.csv` 必须证明 threshold 只在 Train 的 inner select / OOF predictions 上选择，不使用外层 Train in-sample predictions、外层 Valid 或 observed replication。
- `fold_predictions.csv` 必须保留每个候选的 bad trade probability。
- `fold_replay_metrics.csv` 必须包含 `no_model_gate`、`rule_pullback_hard_gate`、`lgbm_pullback_bad_trade_gate`。
- `year_metrics.csv` 必须覆盖 2019 到 2024 的 distinct calendar years。
- `observed_replication_summary.csv` 必须存在，但 `run_manifest.json` 中 `observed_replication_used_for_selection` 必须为 `false`。
- 如果没有满足选择准则的版本，`explore6_meta_label_report.md` 必须明确写“没有形成 Explore6 候选版本”。

## 13. 后续边界

Explore6 只有在 meta-label gate 同时改善失败退出、保持交易覆盖、降低或不恶化回撤，并在 distinct-year 维度稳定时，才允许报告为 `candidate_for_future_final_test`。

如果模型改善主要来自降低暴露，Explore6 的结论应停留在失败交易诊断，下一步应继续拆分和重定义 pullback，而不是扩大模型搜索。

在真正有 `2026-04-30` 之后至少 20 个可执行交易日之前，不得声明 final test。

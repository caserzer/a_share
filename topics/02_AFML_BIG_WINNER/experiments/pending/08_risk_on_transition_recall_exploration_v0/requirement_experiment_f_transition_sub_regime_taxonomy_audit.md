# 需求：Experiment F - Transition Sub-Regime Taxonomy Audit

## 1. 背景

Experiment A / B / C / D / E 已经把 08 的后续方向分成两条线：

1. `risk_on` 已切换为 post-filter replay / cost rejector 问题。R-core / R6 是足够宽的 recall source，下一步是成本侧过滤。
2. `transition` 不能继续沿用 T4 / T7 / raw R-core 修补。C 显示当前 transition arms 在 robustness 上失稳；D 进一步显示 transition train / validation 的高 recall 与 robustness 的低 recall 之间存在断裂。
3. 当前 `transition` 不是正向定义的单一市场状态，而是 residual bucket：

```text
risk_on  = market_trend_60d >= 0 且 market_drawdown_120d > -10%
risk_off = market_trend_60d < 0 且 market_drawdown_120d <= -10%
transition = 其余完整观测
```

因此 transition 至少混合两类相反过程：

1. recovery transition：`market_trend_60d >= 0` 但 `market_drawdown_120d <= -10%`，更像深回撤后的修复 / risk_off -> risk_on。
2. deterioration transition：`market_trend_60d < 0` 但 `market_drawdown_120d > -10%`，更像高位转弱 / risk_on -> risk_off。

Experiment F 的任务不是找新的 transition family，也不是训练 entry model。F 只回答：

```text
当前 transition 的 robustness collapse 是否主要来自 residual bucket 内部的子状态混合、
split 间子状态构成漂移、或不同子状态下 recall / fast-fail / false-repair 行为不一致？
```

只有 F 通过审计后，才允许进入子状态级的 volatility contraction、VCP、T6 / T8、regime-boundary feature 设计，或重新定义 transition bridge-positive label source。

## 2. Primary Question

Experiment F 必须回答：

```text
Can the residual transition bucket be decomposed into stable, auditable
sub-regimes that explain the train / validation / robustness instability in
R-series and T4/T7 transition recall and cost readouts?
```

中文等价问题：

```text
能否把 residual transition 拆成可审计的子状态，并证明这些子状态在 split 间的占比、
E1 / R-core / R6 / T4/T7 recall、E1-missed capture、fast-fail / false-repair
上存在足以解释 robustness collapse 的差异？
```

## 3. 范围

Experiment F 只覆盖：

1. `transition` target regime。
2. transition 子状态 taxonomy 审计。
3. 默认 deterministic 子状态：recovery / deterioration / boundary-or-mixed。
4. 自动 taxonomy 试验：使用 120 trading-day as-of market-state window，基于 elbow / kNN 等方法尝试自动分类。
5. 每个 taxonomy 下的 split composition drift、recall、E1-missed capture、fast-fail、false-repair、density / overlap 读数。

关键粒度约束：

1. taxonomy assignment 的原始对象是 `date-level market state`，不是 instrument-level event。
2. 每个 `event_t0_date` 只能继承该日期的 transition sub-regime assignment。
3. event-level / episode-level readout 可以按 event / episode 展开，但不得把个股路径、family composition 或 event outcome 用作 market sub-regime 的定义特征。
4. `cross_section_feature_panel.parquet` 只能先聚合为 date-level market / breadth / board-state features，再进入自动 taxonomy；单个 instrument 的 raw return、close-to-high、momentum percentile 等不得直接作为自动 taxonomy feature。

Experiment F 不覆盖：

1. 新 event family 发明。
2. transition-specific family rediscovery。
3. supervised entry model / ranker / rejector 训练。
4. 交易策略、组合回测、仓位模拟、止盈止损。
5. 使用未来 label 对 transition 子状态做监督式划分。

F 的输出只能是 taxonomy / audit / design recommendation。不得输出 direct-entry support。

## 4. Required Inputs

### 4.1 上游 manifests

必须读取：

```text
outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
outputs/manifests/regime_family_matrix/regime_family_matrix_manifest.json
outputs/manifests/risk_on_r_series_bridge_ranker/risk_on_r_series_bridge_ranker_manifest.json
outputs/manifests/post_replay_event_to_episode_retention_source/post_replay_event_to_episode_retention_source_manifest.json
```

允许的上游 final decisions：

| experiment | allowed decisions |
| --- | --- |
| A | `density_fast_fail_audit_complete`, `density_fast_fail_audit_partial_source_complete` |
| B | `regime_family_matrix_complete`, `regime_family_matrix_source_caveated_complete` |
| C | `risk_on_r_series_ranker_complete`, `risk_on_r_series_ranker_source_caveated_complete` |
| D | `post_replay_retention_source_complete`, `post_replay_retention_source_source_caveated_complete` |

若任一必要 manifest 缺失或 decision 不在允许列表，必须停止并输出：

```text
transition_subregime_taxonomy_input_blocked
```

若任一上游是 source-caveated 完成态，F 可以继续，但最终 decision 必须带 `source_caveated` 后缀；报告不得声称 production-ready taxonomy。

### 4.2 Event / label / replay source

必须读取：

```text
outputs/publishable/tables/candidate_family_canonical_events.csv.gz
outputs/publishable/tables/candidate_family_event_instances.csv.gz
outputs/local_cache/candidate_family_event_labels.parquet
outputs/local_cache/candidate_family_capture.parquet
outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_scope_retention_by_split_regime.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_e1_missed_retention_summary.csv
outputs/publishable/tables/regime_family_matrix/transition_event_family_reselection_matrix.csv
outputs/publishable/tables/risk_on_r_series_bridge_ranker/risk_on_r_series_ranker_transition_reselection_readout.csv
```

D local membership 是 post-replay retention / E1-missed capture 的权威 source。F 不得从 pre-replay aggregate table 推断 post-replay retention。

### 4.3 Market index / benchmark source

F 必须显式读取原始 market index panel，用于重建 `market_trend_60d`、`market_drawdown_120d` 与自动 taxonomy 的 date-level path features。默认 required index panel：

```text
data/interim/index_qlib_csv/day/SH000985.csv
```

辅助 diagnostic index panel：

```text
data/interim/index_qlib_csv/day/SH000300.csv
data/interim/index_qlib_csv/day/SZ399006.csv
```

默认解释：

1. `SH000985` 是 all-A / broad-market proxy，作为 deterministic taxonomy 与 auto 120d path features 的 primary benchmark。
2. `SH000300` 与 `SZ399006` 只能用于 sensitivity / board-style context，不能替代 primary benchmark，除非 `SH000985` 缺失。
3. 每个 index panel 必须记录 path、sha256、row count、date min/max、missing close count、duplicate date count。
4. 若 `SH000985.csv` 缺失但 `SH000300.csv` 可用，F 可以降级为 `component_source_status = fallback_benchmark_proxy`，但 final decision 不得超过 diagnostic-only，除非报告证明 fallback 与现有 regime labels 的一致性足够高。
5. 若所有 index panel 缺失，才允许使用 `cross_section_feature_panel.parquet` 的 date-level universe equal-weight proxy；这种情况下必须标记 `component_source_status = universe_proxy_reconstructed`。

### 4.4 Regime component source

F 必须重建或读取 regime-defining components，而不是只消费已经分好的 `market_regime_bucket = transition`：

```text
market_trend_60d
market_drawdown_120d
market_return_20d
market_return_60d
market_return_120d
market_volatility_20d
market_volatility_60d
market_volatility_120d
market_breadth / universe_up_share family
new-high / close-to-high breadth family
board-relative breadth family
```

优先使用可审计的 t0 / as-of date-level source，优先级如下：

```text
data/interim/index_qlib_csv/day/SH000985.csv
outputs/local_cache/cross_section_feature_panel.parquet
candidate_family_canonical_events.csv.gz 中已有的 market_* / universe_* / board_* 字段
```

若存在独立的 market index / benchmark daily panel，必须优先使用该面板重建 regime components。若没有可用 index panel，才允许从 `cross_section_feature_panel.parquet` 聚合出 date-level proxy，但必须满足：

1. 聚合粒度是 `date`，不得保留 `instrument`。
2. 默认 market close proxy 为当日 universe equal-weight cumulative index，或 manifest 中记录的 benchmark proxy。
3. `market_trend_60d` 默认定义为 date-level market close proxy 的 60 trading-day return。
4. `market_drawdown_120d` 默认定义为 `market_close_proxy / rolling_120d_high - 1`，rolling high 只使用 `date <= event_t0_date` 的 120 个已观测交易日。
5. `market_return_20d / 60d / 120d`、`market_volatility_20d / 60d / 120d` 必须来自同一个 date-level market close proxy。
6. breadth features 必须是 date-level cross-section aggregate，例如 universe up share、new-high share、board relative aggregate；不得直接使用单只股票的特征。

如果 `market_trend_60d` 或 `market_drawdown_120d` 不在 event 输入中，F 必须从上述 date-level index / market / universe panel 重建，并在 `transition_subregime_regime_component_audit.csv` 中记录：

1. component source。
2. reconstruction formula。
3. as-of date policy。
4. missing rate。
5. date-level source row count。
6. event-level join row count。
7. future join row count。
8. 与现有 `market_regime_bucket` 的一致率。
9. 若使用 proxy 而非原始 benchmark index，记录 `component_source_status = proxy_reconstructed`。
10. `legacy_regime_component_horizon` 与 `taxonomy_component_horizon`。
11. `regime_label_consistency_status`。

现有 event artifacts 可能只保留 `market_drawdown_60d` 或 `market_return_20d` 等 legacy fields。F 的 taxonomy 仍以 `market_drawdown_120d` 为主，但 component audit 必须同时输出：

```text
legacy_market_drawdown_available_horizon
taxonomy_market_drawdown_horizon = 120
horizon_mismatch_status
```

如果一致率低于 95% 的主要原因是 legacy `market_drawdown_60d` 与 taxonomy `market_drawdown_120d` 的口径差异，且 index panel 可重建两套 horizon 并解释差异，则不得直接 component-block；必须标记：

```text
regime_label_consistency_status = horizon_mismatch_audited
```

并继续输出 diagnostic / supported gate 所需读数。只有在无法重建 `market_trend_60d` 与 `market_drawdown_120d`，或一致率低于 95% 且无法用已记录 horizon / source 差异解释时，默认 deterministic taxonomy 必须 fail closed，final decision 只能是：

```text
transition_subregime_taxonomy_component_blocked
```

自动 taxonomy 可以在 component blocked 时输出 diagnostic-only feature availability report，但不得产生 supported taxonomy。

## 5. Transition Universe

F 的 universe 必须从 event-level 与 episode-level 两个口径同时审计。

### 5.1 Event universe

event universe：

```text
candidate_family_canonical_events where market_regime_bucket == "transition"
```

需要保留：

```text
event_id
canonical_event_id
instrument
event_t0_date
event_t0_pos
trade_open_date
event_split
market_regime_bucket
event_regime_bucket
board_bucket
primary_family_id
triggered_family_ids
triggered_family_variants
family_count
channel_count
```

### 5.2 Episode universe

episode universe 必须来自 D membership：

```text
post_replay_event_episode_membership where market_regime_bucket == "transition"
```

注意 D membership 中列名存在 event-side 与 episode-side 两种 regime：

1. `market_regime_bucket`：event-side regime。
2. `episode_market_regime_bucket` / `market_regime_bucket_episode`：episode-side regime。

F 的 transition 子状态划分必须以 event-side `event_t0_date` / `market_regime_bucket = transition` 为主；episode-side regime 只能用于 replay readout 分组和一致性审计，不能替代 event-side transition。

### 5.3 Mandatory source scopes

至少审计以下 source：

```text
07_E1_only
08_R_core_event_regime_gated
08_R6_event_regime_gated
08_R1_event_regime_gated
08_R2_event_regime_gated
08_R7_event_regime_gated
08_R8_event_regime_gated
08_selected_T4_T7_union
08_T4_gated
08_T7_gated
```

`08_selected_T4_T7_union`、`08_T4_gated`、`08_T7_gated` 是 challenged incumbent / negative-control context，不得因为某个子状态局部读数较好而直接升级为 supported family。

### 5.4 Grain / denominator contract

D membership 是多行结构，至少包含 event、source、window、replay policy 与 episode membership 维度。F 必须先生成并审计 canonical denominator views，不能直接在 raw membership rows 上计算 composition / recall / cost。

必须使用以下 grain：

| readout | grain | denominator policy |
| --- | --- | --- |
| taxonomy assignment | unique `event_t0_date` market-state row，再 join 到 unique event | 每个 date 一个 sub-regime；每个 event 继承 event_t0_date |
| event composition | unique event | `canonical_event_id` 优先；缺失时使用 `event_id` |
| event cost / quality | unique horizon-complete event | 同一 event 只计一次，按 `failure_10_complete` / `event_false_repair_20d_complete` 过滤分母 |
| episode composition | unique target episode | `target_episode_id` 去重；缺失 episode id 的 rows 只能进入 event readout |
| recall / retention | unique target episode within `source_id`, `window`, `replay_policy_id`, `split`, `subregime` | 同一 episode 被同一 source 多个事件捕获只计一次 |
| E1-missed capture | unique target episode missed by E1 within same split/subregime/window | 先定 E1 missed denominator，再计算 source capture |
| density / overlap | event-day / executable event-day | 按 A density contract，不使用 raw membership row count |

必须输出 `transition_subregime_denominator_audit.csv`，记录每个 readout 的 raw row count、deduplicated row count、duplicate drop count、denominator policy 与 blocked reason。

若任一主要 readout 只能基于 raw membership row count 计算，必须停止并输出：

```text
transition_subregime_taxonomy_binding_drift_blocked
```

## 6. Default Deterministic Taxonomy

F 必须先产出默认 deterministic taxonomy。自动 taxonomy 只能作为并列试验，不能替代默认 taxonomy。

默认 deterministic taxonomy 的 assignment 也必须先在 date-level component panel 上计算，再 join 回 transition events。不得对同一日期的不同 instrument 赋予不同 deterministic sub-regime。

### 6.1 默认子状态

每个 transition event 必须被分配到以下之一：

```text
transition_recovery
transition_deterioration
transition_boundary_or_mixed
transition_component_missing
```

默认规则：

1. 若 `market_trend_60d` 或 `market_drawdown_120d` 缺失，标记为 `transition_component_missing`。
2. 若样本处在 regime boundary 附近，优先标记为 `transition_boundary_or_mixed`。
3. 否则若 `market_trend_60d >= 0` 且 `market_drawdown_120d <= -10%`，标记为 `transition_recovery`。
4. 否则若 `market_trend_60d < 0` 且 `market_drawdown_120d > -10%`，标记为 `transition_deterioration`。
5. 其余残差标记为 `transition_boundary_or_mixed`，并在 audit 中列出触发原因。

在 `risk_on / risk_off / transition` 的精确定义下，`transition_recovery` 与 `transition_deterioration` 是 transition 的互斥且穷尽的两个核心象限。也就是说：

```text
transition = transition_recovery union transition_deterioration
```

`transition_boundary_or_mixed` 不是数学上的第三个原始象限，而是对 recovery / deterioration 附近边界样本的 margin-based reclassification。报告必须分别输出：

```text
raw_core_quadrant = recovery / deterioration
boundary_reclassified_flag
boundary_reclassification_reason
final_default_subregime
```

因此，F 的解释必须先看 raw recovery / deterioration 构成，再看 boundary reclassification 是否改善 collapse 解释。不得把 boundary 样本解释成独立经济机制，除非自动 taxonomy 与 market-state readout 给出额外证据。

### 6.2 Boundary / mixed rule

boundary-or-mixed 不是垃圾桶，必须可解释。默认 boundary rule：

```text
abs(market_trend_60d) <= 1.0 percentage point
or abs(market_drawdown_120d + 10%) <= 1.0 percentage point
or market_trend_20d 与 market_trend_60d 方向相反
or market_volatility_20d 位于 train transition p90 以上
```

实现可以调整 boundary margin，但只能来自预声明 config 或 train split 内部 sensitivity。validation / robustness 只能 readout，不得参与 margin selection。若没有显式 config，默认必须使用本节 margin。

若调整 boundary margin，必须在 manifest 记录：

```text
trend_boundary_margin_pp
drawdown_boundary_margin_pp
short_trend_contradiction_rule
volatility_boundary_quantile
margin_selection_source
```

若调整 margin，报告必须同时给出默认 margin 与调整后 margin 的 sensitivity readout。

Boundary margin 不得掏空核心态：

1. 默认 margin 下，每个 split 的 `transition_boundary_or_mixed` event share 若超过 35%，必须标记 `boundary_over_capture_alert`。
2. 调整后 margin 下，每个 split 的 `transition_boundary_or_mixed` event share 若超过 40%，该 taxonomy 只能 diagnostic-only，除非 train 与 robustness 的 recovery / deterioration 两个核心态仍均满足 episode-level power floor。
3. `transition_boundary_or_mixed` 不得单独用于满足 supported gate 中“至少两个主要子状态”的要求；supported gate 必须检查 `transition_recovery` 与 `transition_deterioration` 两个核心态的样本量和 readout。
4. 若 recovery 或 deterioration 在 robustness 的 target_episode_n < 30，但 event_n >= 100，报告必须强制打印 low-power CI 警告，不得只用 event_n 淡化 episode 粒度不确定性。

### 6.3 Default taxonomy gates

默认 taxonomy 必须满足：

1. transition event reconstruction count 与 source event count 一致，或差异有记录且可解释。
2. `transition_component_missing` 在 train 与 robustness 均不超过 5%。
3. train 与 robustness 的 `transition_recovery` 和 `transition_deterioration` 两个核心态都必须有 readout；若任一核心态缺失，final decision 不得超过 diagnostic-only。
4. supported gate 下，train 与 robustness 的 recovery / deterioration 至少应满足 `target_episode_n >= 30`；若某核心态 episode 分母不足但 `event_n >= 100`，可以继续输出 taxonomy readout，但该 cell 必须标记 `episode_low_power_event_supported_only`，final decision 不得超过 `transition_subregime_taxonomy_diagnostic_only`。
5. 每个非 missing 子状态必须有 recall / cost / density readout；低样本 cell 可以 diagnostic-only，但不能静默缺失。
6. 所有 recall / retention 表必须打印每个子态真实 `target_episode_n`、`bridge_episode_denominator_n`、`e1_missed_episode_n` 与 Wilson / bootstrap confidence interval。

## 7. Automatic Taxonomy - 120d As-of Window

除了默认 deterministic 子状态，F 必须增加自动 taxonomy 试验。自动 taxonomy 的目的不是直接产生交易信号，而是检查 residual transition 是否存在数据驱动的状态簇，并与默认 recovery / deterioration / boundary-or-mixed 对齐。

### 7.1 120d 划分周期

自动 taxonomy 必须使用 date-level rolling 120 trading-day as-of window 作为状态划分周期：

```text
auto_taxonomy_window = 120 trading days
window_end_date = event_t0_date
window_start_date = window_end_date - 119 observed trading sessions
taxonomy_assignment_grain = market_date
```

每个 transition event 的自动分类特征只能来自 `event_t0_date` 当日及之前的 120 个已观测交易日。不得使用 `event_t0_date` 之后的市场路径、未来 winner label、fast-fail label、false-repair label、target episode outcome 或 replay oracle。

`auto_period_id` 必须定义为 `window_end_date` 的 date-level id。若实现额外输出非重叠 120d calendar / trading-session period summary，只能作为 diagnostic aggregation，不得替代 rolling 120d event-date assignment。

滚动 120d window 高度重叠，会造成时间自相关与有效样本数膨胀。F 必须把这一点作为正式稳定性审计，而不是只在报告里口头 caveat：

1. 必须输出 rolling window 的 lag-1 / lag-5 / lag-20 feature autocorrelation summary。
2. 必须估计 effective independent window count，默认可用：

```text
effective_n = observed_window_n * (1 - rho_1) / (1 + rho_1)
```

其中 `rho_1` 是主要自动 taxonomy feature 的平均 lag-1 autocorrelation；若公式不可用，必须记录替代方法。
3. 必须构造 non-overlap / block-sampled stability view：
   - 默认每 20 个 trading days 抽取一个 window 作为 block-sampled view。
   - 另输出 non-overlapping 120 trading-day period summary。
   - 这两者不替代 rolling assignment，但用于 cluster stability gate。
4. 如果 rolling window 上的 elbow / silhouette 很强，但 block-sampled view 上 `k_selected` 不一致或 cluster composition 差异过大，`auto_120d_elbow_kmeans` 必须降级为 `elbow_overlap_instability_diagnostic`。

自动 taxonomy 必须记录：

```text
auto_period_id
window_start_date
window_end_date
observed_trading_day_n
window_completeness_rate
event_count_in_period
episode_count_in_period
effective_independent_window_n
lag1_autocorrelation_mean
block_sample_id
```

若某个 event 的 120d window 不完整，允许标记为 `auto_120d_window_incomplete`，但不能用未来数据补齐。

### 7.2 自动分类特征

自动 taxonomy 的 feature set 必须是 market-state / breadth-state 特征，不得包含 candidate outcome label。

自动 taxonomy feature 的构造粒度必须是 date-level 120d window。若输入来自 `cross_section_feature_panel.parquet`，必须先按 `date` 聚合成 market / breadth / board-state 序列，再在该 date-level 序列上滚动计算 120d 特征。禁止把 `instrument` 维度展开为自动 taxonomy feature，禁止把 event family / source_id / primary_family_id / board_bucket one-hot 作为聚类输入。

必选特征族：

1. path / trend：
   - 20d / 60d / 120d return。
   - 20d / 60d trend slope。
   - 120d max drawdown。
   - 120d distance from high。
2. volatility / entropy：
   - 20d / 60d / 120d realized volatility。
   - volatility change 20d vs 60d。
   - direction entropy 20d / 60d。
3. breadth：
   - universe up share mean / min / max / slope over 120d。
   - universe new-high 60 share mean / slope。
   - board relative return / board relative cusum 20d aggregated over 120d。
4. regime boundary：
   - fraction of days in risk_on / risk_off / transition over the 120d window。
   - days since last risk_off。
   - days since last risk_on。
   - current hard-regime boundary distances:
     `market_trend_60d`, `market_drawdown_120d + 10%`。

所有自动 taxonomy 特征必须进入：

```text
transition_auto_120d_feature_contract.csv
```

并记录：

```text
feature_name
source_artifact
source_hash
feature_grain
as_of_policy
window_length_trading_days
missing_rate_train
missing_rate_validation
missing_rate_robustness
allowed_as_unsupervised_taxonomy_feature
uses_future_information
blocked_reason
```

`feature_grain` 只能是：

```text
date_level_market_state
date_level_breadth_state
date_level_board_aggregate_state
```

若出现 `instrument_level`、`event_level_family`、`label_or_outcome`，该字段必须 `allowed_as_unsupervised_taxonomy_feature = false`。

### 7.3 预处理

自动 taxonomy 的预处理必须 train-only：

1. 数值特征使用 train transition 120d windows 的中位数填补。
2. 偏态非负特征可以做 `log1p`，但必须列入 manifest。
3. 使用 train transition 1% / 99% 分位数 winsorize。
4. 使用 train transition 均值 / 标准差 z-score。
5. validation / robustness 只能使用 train 预处理参数。

若实现做 PCA / UMAP / t-SNE：

1. PCA 可以作为 clustering input，但必须 train-fit、OOS transform。
2. UMAP / t-SNE 只能作为 visualization，不得作为 gate 或 final taxonomy input。
3. 降维参数必须进入 manifest。

## 8. Automatic Methods

F 至少实现以下两个自动 taxonomy arms。

### 8.1 `auto_120d_elbow_kmeans`

目标：用 train transition 120d window feature 向量自动选择 cluster count，并把 validation / robustness 分配到 train-fitted centroids。

规则：

1. 候选 `k`：

```text
k in [2, 3, 4, 5, 6, 7, 8]
```

2. 使用 train transition windows fit k-means。
3. 用 elbow 方法选择 `k_selected`：
   - 必须输出 SSE / inertia curve。
   - 必须输出相邻 k 的 marginal improvement。
   - 必须输出 elbow score。
   - 若 elbow 不明显，使用 silhouette / min-cluster-size 作为 tie-breaker。
4. validation / robustness 不得重新 fit；只能 assign 到 train-fitted centroids。
5. 每个 cluster 必须 post-label：
   - 计算 cluster 内 `market_trend_60d`、`market_drawdown_120d`、volatility、breadth、default taxonomy composition 的 median / share。
   - 映射为可解释 label：

```text
auto_recovery_like
auto_deterioration_like
auto_boundary_or_mixed_like
auto_volatility_stress
auto_breadth_recovery
auto_other
```

不得把无解释的 `cluster_0` / `cluster_1` 直接写入 final conclusion。

elbow score 必须可复现。默认公式：

```text
relative_improvement_k = (inertia_{k-1} - inertia_k) / inertia_{k-1}
elbow_score_k = relative_improvement_k - relative_improvement_{k+1}
```

选择规则：

1. 只在 train transition windows 上计算 `inertia`、`relative_improvement`、`elbow_score`、`silhouette` 与 cluster size。
2. 过滤掉任一 cluster train share < 5% 的 k，除非所有 k 都触发该问题；若全部触发，arm 状态为 `elbow_low_cluster_power`.
3. 在可用 k 中选择 `elbow_score_k` 最大且 `relative_improvement_{k+1} < 0.75 * relative_improvement_k` 的最小 k。
4. 若没有明显 elbow，使用 silhouette 最大的 k；若 silhouette 差异 < 0.02，选择更小 k。
5. 必须固定 `random_state` 并记录 `n_init`、`max_iter`、`random_state`。
6. validation / robustness 只能 assign 到 train-fitted centroids，不得重新选择 k。

滚动窗自相关稳定性要求：

1. 必须在 full rolling train windows 与 block-sampled train windows 上分别运行 elbow selection。
2. 必须输出两者的 `k_selected`、cluster size share、centroid distance stability、adjusted rand index 或 normalized mutual information。
3. 若 full rolling 与 block-sampled 的 `k_selected` 不一致，允许继续输出 cluster readout，但 `auto_120d_elbow_kmeans` 状态必须是 `elbow_overlap_instability_diagnostic`，不得支撑 supported gate。
4. 若 effective independent window count < 50，自动 taxonomy 只能 diagnostic-only。

### 8.2 `auto_120d_knn_default_taxonomy`

目标：用 train transition 120d window feature 向量和默认 deterministic taxonomy 作为 seed label，对 validation / robustness 做 kNN 子状态传播，检验默认 taxonomy 是否能在 market-state feature space 中稳定外推。

规则：

1. 候选 neighbor count：

```text
n_neighbors in [3, 5, 7, 11]
```

2. train labels 来自第 6 节默认 taxonomy。
3. 距离度量默认使用 standardized Euclidean；可选 cosine，但必须报告。
4. 采用 distance-weighted voting。
5. `n_neighbors` 只能用 train 内部稳定性选择，不得用 validation / robustness outcome label 选择。
6. 对 validation / robustness 输出：

```text
knn_predicted_subregime
knn_vote_margin
knn_neighbor_distance_mean
knn_assignment_confidence
```

低 vote margin 的样本标记为：

```text
auto_knn_low_confidence
```

kNN train 内部稳定性默认用 blocked date CV：

1. 按 `event_t0_date` 排序，把 train transition dates 切为 5 个连续时间块。
2. 每次用 4 个块 fit kNN reference set，对 held-out train block 预测默认 deterministic taxonomy label。
3. 选择 mean balanced accuracy 最高的 `n_neighbors`。
4. 若 balanced accuracy 差异 < 0.02，选择更小 `n_neighbors`。
5. 同时报告 mean vote margin、low-confidence share、每个默认子状态的 recall。
6. validation / robustness 的 outcome label 不得参与 `n_neighbors` 选择。

### 8.3 Optional arms

允许增加以下 diagnostic-only arms：

```text
auto_120d_agglomerative
auto_120d_gmm_bic
auto_120d_hdbscan
```

optional arms 不得成为唯一 supported taxonomy；它们只能帮助解释是否存在非线性或非球形 cluster。

## 9. Metrics

每个 taxonomy arm 必须按以下维度输出 readout：

```text
taxonomy_method
subregime_id
subregime_label
split
source_id
window
replay_policy_id
assignment_grain
readout_grain
denominator_policy
```

每个 readout 必须能回到第 5.4 节的 grain / denominator contract；无法证明分母口径的 row 必须标记 `denominator_status = blocked`.

### 9.1 Composition drift

必须输出：

1. event count / share。
2. target episode count / share。
3. E1-missed episode count / share。
4. train vs robustness Jensen-Shannon divergence。
5. train vs robustness population stability index。
6. validation sample status，仅 diagnostic。
7. `collapse_explanation_status`：

```text
explained_by_composition_drift
explained_by_subregime_behavior
explained_by_both
not_explained
low_power
```

### 9.2 Recall / retention

必须输出：

1. E1 any recall。
2. source pre-replay any recall。
3. source post-replay any recall。
4. source pre-replay bridge recall。
5. source post-replay bridge recall。
6. E1-missed denominator。
7. source post-replay captures E1-missed n。
8. incremental post-replay capture over E1 n / rate。
9. Wilson confidence interval 或 bootstrap confidence interval。
10. `episode_power_status`：

```text
sufficient_episode_power
episode_low_power_caution
episode_low_power_event_supported_only
insufficient_episode_power
```

至少覆盖：

```text
07_E1_only
08_R_core_event_regime_gated
08_R6_event_regime_gated
08_selected_T4_T7_union
08_T4_gated
08_T7_gated
```

### 9.3 Cost / quality

必须输出：

1. `failure_10_label` complete rate。
2. fast-fail 10d rate。
3. `event_false_repair_20d_label` complete rate。
4. false-repair 20d rate。
5. `event_big_winner_120d_label` complete rate。
6. event-level 120d big-winner rate，仅 diagnostic。

### 9.4 Density / overlap

必须输出：

1. selected event count。
2. formal event-day density。
3. rolling 10d executable event-day density。
4. rolling 20d executable event-day density。
5. rolling duplicate rate。
6. family concentration。
7. board concentration。
8. cross-family collision rate。

Density 口径必须引用 A 的 density contract，不得重新定义。

## 10. Leakage Rules

F 是 taxonomy audit，不是 supervised model。即便如此，所有 taxonomy assignment 仍必须符合 as-of 约束：

1. 默认 taxonomy 只能使用 `event_t0_date` 当日可见或之前可重建的 regime components。
2. 自动 taxonomy 只能使用 `event_t0_date` 之前 120 trading-day window 的 market-state features。
3. `failure_10_label`、`event_false_repair_20d_label`、`event_big_winner_120d_label`、`target_episode_id`、bridge-positive outcome、post-replay capture outcome 不得用于子状态划分。
4. 这些 outcome 只能用于 taxonomy assignment 之后的 readout。
5. elbow / kNN 的 `k` / `n_neighbors` 选择不得读取 validation / robustness outcome。

任一违反，停止并输出：

```text
transition_subregime_taxonomy_leakage_blocked
```

## 11. Decision Gates

### 11.1 Taxonomy audit supported

只有同时满足以下条件，才能输出：

```text
transition_subregime_taxonomy_supported
```

若任一上游 source-caveated，则必须输出：

```text
transition_subregime_taxonomy_source_caveated_supported
```

硬门槛：

1. input / component / leakage audit 全部 pass。
2. 默认 deterministic taxonomy 可覆盖 train 与 robustness，`transition_component_missing <= 5%`。
3. `transition_recovery` 与 `transition_deterioration` 两个核心态在 train 与 robustness 均有 readout，且不被 boundary reclassification 掏空。
4. 两个核心态在 train 与 robustness 的 `target_episode_n >= 30`；若某核心态只有 `event_n >= 100` 但 episode n 不足，可以保留 event-level readout，但 final decision 不得超过 `transition_subregime_taxonomy_diagnostic_only`，且报告必须打印 CI 与 low-power caveat。
5. 每个主要子状态都有 E1 / R-core / R6 / T4/T7 recall 和 fast-fail / false-repair readout。
6. train -> robustness composition drift 可量化，且报告明确说明 drift 是否足以解释 transition recall collapse。
7. `auto_120d_elbow_kmeans` 必须产出完整可审计结果；若 k-means 只能 diagnostic，final decision 不得超过 `transition_subregime_taxonomy_diagnostic_only`。
8. 自动 taxonomy supported 需要 `auto_120d_elbow_kmeans` 选择出稳定 `k_selected`，且没有单 cluster 占比超过 80%，任一 cluster train share 不低于 5%。
9. 自动 taxonomy supported 还必须通过 rolling-vs-block stability gate：full rolling 与 block-sampled `k_selected` 一致，cluster assignment adjusted rand index 或 normalized mutual information >= 0.50，且 `effective_independent_window_n >= 50`。
10. `auto_120d_knn_default_taxonomy` 只能作为默认 taxonomy 的 feature-space 可传播性证据，不能单独支撑 supported；robustness high confidence assignment share >= 70% 只能作为 corroboration。
11. 自动 taxonomy 与默认 taxonomy 的 agreement / confusion matrix 已输出；若 disagreement 高，必须解释差异来源。
12. validation 只作为 diagnostic，不得触发 taxonomy rule 微调。

### 11.2 Diagnostic-only

以下任一情况，final decision 必须是：

```text
transition_subregime_taxonomy_diagnostic_only
```

1. 默认 taxonomy pass，但主要子状态样本量不足。
2. 自动 taxonomy 全部低稳定性，但默认 taxonomy 可给出 composition / recall / cost readout。
3. transition collapse 不能由 composition drift 或 subregime-level behavior 差异解释。
4. 只能输出 taxonomy hypothesis，不能支持下一阶段 family rediscovery。
5. `auto_120d_knn_default_taxonomy` 可用但 `auto_120d_elbow_kmeans` 不稳定或只能 diagnostic。
6. rolling 120d elbow 在 full rolling sample 上稳定，但 block-sampled stability 不通过。
7. recovery / deterioration 能读出方向，但 episode CI 太宽，不能支持下一阶段 family rediscovery。

以下情况才输出 `transition_subregime_taxonomy_sample_power_blocked`：

1. train 或 robustness 的 transition event n < 100 且 target_episode_n < 30，导致所有主要 readout 都不可计算。
2. 默认 taxonomy 的所有非 missing 子状态在 train 或 robustness 均低于 `event_n >= 30` 且 `target_episode_n >= 10`。
3. D membership 无法为 transition 提供任何 unique target episode denominator。

### 11.3 Blocked decisions

可返回的 blocked decisions：

```text
transition_subregime_taxonomy_input_blocked
transition_subregime_taxonomy_component_blocked
transition_subregime_taxonomy_label_join_blocked
transition_subregime_taxonomy_leakage_blocked
transition_subregime_taxonomy_sample_power_blocked
transition_subregime_taxonomy_binding_drift_blocked
```

## 12. Required Outputs

### 12.1 Tables

必须输出：

```text
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_input_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_source_binding_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_regime_role_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_regime_component_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_denominator_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_label_join_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_leakage_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_auto_120d_period_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_auto_120d_autocorrelation_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_auto_120d_block_stability.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_default_subregime_assignment.csv.gz
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_auto_120d_feature_contract.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_auto_120d_window_features.csv.gz
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_auto_120d_elbow_selection.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_auto_120d_cluster_assignments.csv.gz
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_auto_120d_knn_assignments.csv.gz
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_taxonomy_agreement_matrix.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_composition_by_split.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_recall_retention_matrix.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_e1_missed_capture.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_cost_quality_matrix.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_density_overlap_matrix.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_family_readout.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_drift_audit.csv
outputs/publishable/tables/transition_subregime_taxonomy_audit/transition_subregime_decision_tiers.csv
```

若某些 event-level assignment 表过大，可以 gzip；manifest 必须记录压缩后 hash 与 row count。

### 12.2 Reports / manifests

必须输出：

```text
outputs/publishable/reports/transition_subregime_taxonomy_audit/transition_subregime_taxonomy_audit_report.md
outputs/publishable/reports/transition_subregime_taxonomy_audit/transition_subregime_taxonomy_contract.md
outputs/manifests/transition_subregime_taxonomy_audit/transition_subregime_taxonomy_audit_manifest.json
```

manifest 必须记录：

```text
run_id
created_at
requirement_hash
runner_code_hash
input_artifacts
output_hashes
output_row_counts
upstream_decisions
source_caveated
default_taxonomy_parameters
taxonomy_assignment_grain
readout_denominator_policies
regime_component_source_status
regime_component_formulas
component_reconstruction_consistency_rate
regime_label_consistency_status
auto_taxonomy_window_length = 120
auto_taxonomy_periodization_rule
auto_taxonomy_effective_independent_window_n
auto_taxonomy_autocorrelation_summary_hash
auto_taxonomy_block_stability_hash
auto_taxonomy_feature_hash
auto_taxonomy_preprocessing_hash
elbow_candidate_k_values
elbow_selected_k
elbow_selection_formula
elbow_random_state
knn_candidate_neighbor_values
knn_selected_neighbors
knn_selection_formula
collapse_explanation_status
boundary_reclassification_parameters
boundary_over_capture_status
final_decision
blocked_reasons
```

## 13. Report Requirements

报告必须用中文写，并包含：

1. 一句话 final decision。
2. 为什么 transition 是 residual bucket，而不是单一状态。
3. 默认 deterministic taxonomy 的规则、样本占比、split drift。
4. 自动 120d taxonomy 的 feature、预处理、elbow / kNN 方法、selected parameters。
5. rolling 120d window 的自相关、effective independent window n、block-sampled stability。
6. 默认 taxonomy vs 自动 taxonomy 的 agreement / disagreement。
7. 每个子状态下 E1 / R-core / R6 / T4/T7 的 recall、E1-missed capture、fast-fail、false-repair。
8. 每个子状态的真实 `target_episode_n`、`bridge_episode_denominator_n`、`e1_missed_episode_n`、CI 与 low-power warning。
9. 是否能解释 robustness collapse，并明确打印 `collapse_explanation_status`。
10. 下一步建议：进入哪一个子状态级 family rediscovery，或是否需要重定义 transition label source。
11. 如果 negative result，必须按以下模板解释失败来源：

```text
collapse_explanation_status = not_explained / low_power
failure_axis = component_source / sample_power / taxonomy_instability / no_composition_drift / no_subregime_behavior_gap / denominator_unavailable
next_action = rebuild_regime_components / redefine_transition_label_source / stop_transition_family_rediscovery / diagnostic_only
```

12. 明确不可声称内容：
   - 不得声称 direct-entry support。
   - 不得声称 official train process。
   - 不得声称自动 cluster 本身就是经济机制，除非有 default taxonomy / market-state 解释支撑。
   - 不得用 validation 调 taxonomy rule。
   - 不得把 instrument-level cluster 解释为 market sub-regime。
   - 不得让 kNN seed-label propagation 单独支撑 automatic taxonomy supported。

## 14. Expected Interpretation

如果 F 显示 recovery / deterioration / boundary-or-mixed 的 split composition 明显漂移，且 R-core / R6 / T4/T7 在不同子状态下 recall 与 cost 行为不同，则 transition robustness collapse 很可能来自 residual bucket 的状态混合。下一步应转为子状态级 family rediscovery。

如果默认 taxonomy 与自动 120d taxonomy 都不能稳定分解 transition，或者分解后仍无法解释 robustness collapse，则应暂缓 transition family rediscovery，优先重定义 transition label source 或重建 regime taxonomy。

如果自动 taxonomy 找到稳定 cluster，但与默认 recovery / deterioration 不一致，报告必须把它作为 `auto_taxonomy_hypothesis`，不能直接覆盖默认 taxonomy。下一步应先做解释性审计，再决定是否升级为正式 regime definition。

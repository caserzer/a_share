# Explore7 需求说明：PIT Universe 下的 Pullback 子系统重建

## 1. 背景

Explore4 到 Explore6 的结论已经收敛：

- 风险单位仓位和行业上限可以降低回撤和集中度，但不能把负期望信号变成正期望信号。
- pullback 是当前规则组合中最明确的负贡献来源，尤其集中在 `pullback + stop_loss/time_stop`。
- meta-label 可以训练，但没有形成候选版本；继续扩大模型或参数搜索会先学习未清理的候选集合和低暴露状态。
- `2025-12-31` 静态股票池带来幸存者偏差和未来函数风险，不能再作为 Explore7 的默认研究宇宙。

Explore7 的核心问题改为：

```text
在 point-in-time 股票池和 2019-2024 walk-forward 验证下，
pullback 是否可以被拆分并重建为少数可解释、可稳定复现的子规则，
而不是依赖关闭交易、提高现金比例或模型过滤来改善表现？
```

Explore7 不是新的大模型实验，也不是继续调 Explore6 的 LGBM gate。第一版只做 pullback 子系统重建和 PIT 数据真实性修复。

## 2. 与 Explore4 / Explore5 / Explore6 的关系

Explore7 可以读取前序阶段作为背景，但必须独立重跑。

允许读取：

- `Explore4/configs/trend_rule_v1_frozen.yaml`：冻结规则框架、成本、风控和目标列表来源。
- `Explore4/outputs/reports/pullback_failure_analysis_report.md`：pullback 失败样本背景。
- `Explore5/configs/walk_forward_v1.yaml`：fold 定义、风险控制和选择准则参考。
- `Explore5/outputs/reports/explore5_final_report.md`：rolling validation 背景。
- `Explore6/outputs/reports/explore6_meta_label_report.md`：meta-label 失败背景。

来源配置读取必须使用闭合白名单：

| 来源 | 允许读取的键 |
| --- | --- |
| `Explore4/configs/trend_rule_v1_frozen.yaml` | `qlib`, `costs`, `rules`, `targets` |
| `Explore5/configs/walk_forward_v1.yaml` | `qlib`, `costs`, `rules`, `targets`, `explore5.folds`, `explore5.selection_thresholds` |

路径分类必须先识别上表明确允许的历史报告并标记为 `background_reference`；除此之外，任何从来源配置读到的 `paths.*`、`outputs`、`backtests`、`diagnostics`、`cache` 或 result CSV 路径都必须分类为 `forbidden_result_path`，不得进入信号、候选、回放、选择或报告生成的计算路径。允许读取的历史报告只能作为背景文本证据，不得被解析成计算输入。

禁止：

- 读取 Explore4 / Explore5 / Explore6 的 trade detail、signals、daily candidates、portfolio daily、year metrics 或模型预测结果作为 Explore7 的计算输入。
- 把 Explore5 / Explore6 的 diagnostic-only 版本直接提升为 Explore7 候选。
- 使用 2025-2026 observed replication 选择 pullback 分类、阈值、参数或版本。
- 继续把 `mcap500_mainboard_20251231` 当作默认 tradable universe。

Explore7 所有配置、脚本、缓存、回测、报告和 manifest 必须落在 `Explore7/` 下。

## 3. PIT Universe 数据契约

### 3.1 默认口径

Explore7 必须把静态股票池替换为 point-in-time 股票池。

默认 universe 定义：

```text
universe_name: pit_mcap500_mainboard
membership_frequency: daily
eligible_market: 沪深主板 A 股
exclude_boards: 创业板, 科创板, 北交所, B 股
exclude_security_types: ETF, LOF, 场内基金, 债券, 可转债, 指数
exclude_status_asof_T: ST, *ST, 退市整理, 已退市
min_listing_age_trading_days: 120
market_cap_threshold: 500 亿元
market_cap_asof_T: close_asof_T * total_shares_asof_T
benchmark: SH000300
```

PIT 规则：

- 对每个信号日 `T`，只能使用 `T` 日或 `T` 日以前已经可观察的数据判断是否属于股票池。
- `close_asof_T` 必须来自 `T` 日或 `T` 日以前最近一个有效交易日，不得使用未来价格补齐。
- `total_shares_asof_T` 必须来自 `T` 日或 `T` 日以前已经生效的股本数据，不得使用未来股本补齐。
- ST / 退市 / 名称变更状态必须按 `T` 日可观察状态判断，不得用当前名称全样本过滤历史。
- 如果某只股票在某日缺少上市状态、ST 状态、股本或价格，默认从该日 universe 中剔除，并在 audit 中记录原因。

第一版允许把 PIT universe 的数据源实现成独立阶段，但最终 Explore7 valid 结果必须基于 `universe_point_in_time = true`。如果 PIT universe 无法构建，Explore7 只能输出数据阻断报告，不能继续跑策略结论。

### 3.2 Provider 要求

Explore7 不得默认复用只覆盖静态 282 只股票的 Explore1 provider 作为最终交易数据源。

默认目标：

```text
provider_uri: Explore7/data/qlib/cn_data_pit
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
qlib_instruments: Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
required_fields: $open, $high, $low, $close, $volume, $money, $factor
data_start: 2017-01-01
data_end: 2026-04-30
research_window: 2019-01-01 到 2024-12-31
observed_replication: 2025-01-01 到 2026-04-30
```

Provider 覆盖必须满足：

- 覆盖所有 PIT universe 成员在其有效 membership 日期内的日线数据。
- 覆盖 `SH000300` benchmark。
- 每个 fold 的有效可交易日必须有可读 calendar。
- 对 PIT universe 中有 membership 但缺行情的股票，必须输出 `pit_provider_coverage_audit.csv`，并按日期、股票和缺失字段记录。

`qlib_pit_mcap500_mainboard.txt` 只能作为数据可读性的 instrument superset。真正的可交易资格必须以 `pit_mcap500_mainboard_daily.csv` 为唯一来源，并在每个 `signal_date + instrument` 上显式 join。实现不得把 Qlib market 或 instrument 文件解释为连续持有的静态 tradable universe。

如果为了阶段推进先做 `PIT universe ∩ existing provider` 的 dry-run，必须标记为 `coverage_limited_diagnostic`，不得作为 Explore7 候选或最终结论。

### 3.3 行业归属

默认也要求 point-in-time 行业归属。

```text
industry_membership_point_in_time: true
missing_industry: UNKNOWN
```

规则：

- 行业归属必须按 `T` 日有效关系 join。
- 若暂时只能拿到 as-of 行业归属，只能输出 `industry_asof_diagnostic` 数据阻断或覆盖率报告，不得运行候选选择，也不得形成 `candidate_for_future_final_test`。
- `UNKNOWN` 必须参与行业 cap、行业暴露和 regime 分组。

## 4. 时间切分

Explore7 沿用 Explore5 的 2019-2024 walk-forward 验证纪律。

默认 folds：

| Fold | Train | Valid |
| --- | --- | --- |
| WF1 | 2017-01-01 到 2018-12-31 | 2019-01-01 到 2020-12-31 |
| WF2 | 2017-01-01 到 2019-12-31 | 2020-01-01 到 2021-12-31 |
| WF3 | 2017-01-01 到 2020-12-31 | 2021-01-01 到 2022-12-31 |
| WF4 | 2017-01-01 到 2021-12-31 | 2022-01-01 到 2023-12-31 |
| WF5 | 2017-01-01 到 2022-12-31 | 2023-01-01 到 2024-12-31 |

选择规则：

- 所有 pullback 分类阈值如果需要从数据中推导，只能在每个 fold 的 Train 内推导。
- Valid 只用于评估，不得反向修改分类规则。
- 2025-2026 只能做 observed replication，必须记录 `used_for_selection = false`。
- 报告必须同时输出 fold 维度和 distinct calendar year 维度。

## 5. Pullback 子系统分类

Explore7 第一版只分类并重建 pullback，不训练 meta-label 模型。

### 5.1 候选池

所有 pullback 分类都从同一个 T 日可观察候选池出发：

```text
raw_pullback_shape =
    (low <= ema20 * (1 + ema_band_pct)
     or low <= ema30 * (1 + ema_band_pct))
    and low > ema60
    and close >= ema20
    and close > open
```

`raw_pullback_shape` 只是形态，不代表可下单。

候选必须同时保留以下审计字段：

- `signal_date`
- `instrument`
- `pit_universe_member`
- `listing_age_trading_days`
- `market_cap_asof_T`
- `industry_asof_T`
- `trend_score`
- `trend_score_pct`
- `money_ratio20`
- `distance_to_ema20`
- `distance_to_ema60`
- `distance_to_high60`
- `distance_to_low20`
- `ret5`
- `ret20`
- `ret60`
- `volatility20`
- `atr20_ratio`
- `market_width_state`
- `market_trend_state`
- `industry_sync_state`
- `pullback_class`
- `pullback_class_reason`

### 5.2 三类 Pullback

分类必须互斥。默认优先级为：

1. `breakdown_repair`
2. `weak_volume_rebound`
3. `strong_trend_continuation`
4. `unclassified_pullback`

#### strong_trend_continuation

含义：强趋势中的健康中继回踩。

默认条件：

```text
raw_pullback_shape
and trend_score_pct <= 0.10
and market_trend_state = market_trend_on
and market_width_state in [width_strong, width_neutral]
and industry_sync_state = industry_sync_on
and close > ema20
and ema20 > ema60
and distance_to_ema60 > 0
and distance_to_high60 >= -0.15
and money_ratio20 <= 0.80
and no_breakdown_recently = true
```

其中 `no_breakdown_recently` 默认定义为过去 5 个交易日没有收盘跌破 EMA20 且没有触及 EMA60。

#### weak_volume_rebound

含义：看起来像回踩，但更可能只是弱反弹或缩量修复。

默认条件：

```text
raw_pullback_shape
and 0.60 <= money_ratio20 <= 1.00
and (
    trend_score_pct > 0.10
    or market_width_state != width_strong
    or industry_sync_state != industry_sync_on
)
```

该类是 Explore4 / Explore5 证据最明确的风险区域，第一版默认只能作为诊断类，不能直接进入候选版本，除非 Train 内分类重估证明其 distinct-year expectancy 稳定为正。

#### breakdown_repair

含义：已经出现结构破坏后的修复形态，不应和强趋势中继混为一类。

默认条件：

```text
raw_pullback_shape
and (
    close.shift(1) < ema20.shift(1)
    or rolling_low_5 <= ema60
    or distance_to_low20 <= 0.03
    or ret20 < 0
)
```

该类第一版默认只做诊断，不作为可入选交易来源。

#### unclassified_pullback

不满足上述三类的 pullback 候选统一归入 `unclassified_pullback`。它必须被报告，但第一版不得直接进入候选版本。

### 5.3 分类审计

必须产出：

```text
Explore7/outputs/reports/pullback_classification_audit.csv
```

至少包含：

- 每个 fold / year / class 的候选数。
- PIT universe 覆盖数。
- 被剔除原因分布。
- 每类候选进入完整组合回放后的交易数、胜率、平均收益、R 分布、stop_loss + time_stop 占比。
- 每类在 Train 和 Valid 的分布漂移。

如果某类在任一 fold Train 中样本过少，必须标记为 `insufficient_class_coverage`，不得进入候选选择。

## 6. 回放版本

Explore7 默认比较以下版本，全部在 PIT universe 下独立重算。

1. `pit_breakout_core_baseline`
   - 只保留 breakout。
   - 使用 Explore4 / Explore5 的风险单位仓位和行业 cap。
   - 用于判断非 pullback 核心在 PIT universe 下的基准表现。

2. `pit_original_pullback_baseline`
   - 保留原始 pullback 定义。
   - 用于衡量 Explore4 / Explore5 规则迁移到 PIT universe 后的真实表现。

3. `pit_strong_trend_pullback_candidate`
   - 在 `pit_breakout_core_baseline` 上只加入 `strong_trend_continuation` pullback。
   - 第一版唯一允许进入候选选择的 pullback 重建版本。

4. `pit_weak_volume_rebound_diagnostic`
   - 在 `pit_breakout_core_baseline` 上只加入 `weak_volume_rebound` pullback。
   - 只用于证明该类是否应排除或另行处理。

5. `pit_breakdown_repair_diagnostic`
   - 在 `pit_breakout_core_baseline` 上只加入 `breakdown_repair` pullback。
   - 只用于证明该类是否应排除或另行处理。

6. `pit_rebuilt_pullback_candidate`
   - 只能由 Train 内通过样本充足性和 expectancy 检查的 pullback 类组成。
   - 默认第一版等同于 `pit_strong_trend_pullback_candidate`，除非 Train 内审计允许加入其它类。

禁止：

- 事后从 trade detail 删除亏损交易。
- 为了提高收益而只报告低交易数版本。
- 因 observed replication 表现好而把 diagnostic 类改成 candidate 类。

## 7. 选择准则

Explore7 的选择准则必须防止“靠空仓变好”。

`pit_rebuilt_pullback_candidate` 若要被标记为 `candidate_for_future_final_test`，必须在 2019-2024 distinct-year 维度同时满足：

1. 所有 WF1 到 WF5 都成功使用 PIT universe 和 PIT industry membership 回放。
2. `universe_point_in_time = true`。
3. `industry_membership_point_in_time = true`。
4. `positive_valid_years >= 3`。
5. `qualified_valid_years >= 4`。
6. 相对 `pit_original_pullback_baseline`，至少 `4` 个 distinct years 的 `yearly_expectancy` 改善。
7. 相对 `pit_breakout_core_baseline`，至少 `3` 个 distinct years 的组合收益不低于 baseline，且交易覆盖有实质增加。
8. 平均现金比例不得高于 `95%`，且任一 fold 的平均现金比例不得高于 `97%`。
9. 交易笔数不得低于 `pit_original_pullback_baseline` 的 `60%`，且每个 2 年 fold 不得少于 `40` 笔交易。
10. 最差年度回撤不得比 `pit_original_pullback_baseline` 更差。
11. `stop_loss + time_stop` 占比相对 `pit_original_pullback_baseline` 至少下降 `15%`。
12. 任一 distinct year 不得贡献超过全部正收益 year PnL 的 `45%`。
13. 2025-2026 observed replication 不参与任何选择字段。

`yearly_expectancy` 默认定义为：

```text
yearly_expectancy = net_pnl_sum / executed_trades
```

同时必须报告：

- `avg_cost_after_return`
- `avg_r_multiple`
- `median_r_multiple`
- `stop_time_trade_ratio`
- `cash_ratio`
- `trade_ratio_vs_baseline`

如果候选版本改善主要来自交易数显著下降或现金比例升高，报告必须降级为：

```text
diagnostic_only: improvement mainly comes from exposure reduction
```

## 8. 产物要求

Explore7 至少产出：

```text
Explore7/requirement.md
Explore7/configs/pullback_rebuild_v1.yaml
Explore7/scripts/
Explore7/data/universe/pit_mcap500_mainboard_daily.csv
Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
Explore7/data/qlib/cn_data_pit/
Explore7/outputs/reports/run_manifest.json
Explore7/outputs/reports/source_data_audit.csv
Explore7/outputs/reports/pit_universe_audit.csv
Explore7/outputs/reports/pit_provider_coverage_audit.csv
Explore7/outputs/reports/pit_industry_membership_audit.csv
Explore7/outputs/reports/generated_signals.csv
Explore7/outputs/reports/generated_daily_candidates.csv
Explore7/outputs/reports/pullback_classification_audit.csv
Explore7/outputs/reports/fold_replay_metrics.csv
Explore7/outputs/reports/year_metrics.csv
Explore7/outputs/reports/class_expectancy_by_year.csv
Explore7/outputs/reports/fold_trade_detail.csv
Explore7/outputs/reports/fold_portfolio_daily.csv
Explore7/outputs/reports/pullback_rebuild_report.md
```

`run_manifest.json` 至少记录：

- PIT universe 数据源、字段和 SHA256。
- PIT universe 是否真的按日变化。
- 每个 fold 的 PIT universe 成员数量分布。
- provider 覆盖率。
- 行业归属是否 point-in-time。
- `source_data_audit.csv` 的路径分类摘要。
- 是否使用了任何 Explore4 / Explore5 / Explore6 result CSV，必须为 `false`。
- fold 定义。
- pullback 分类闭合规则。
- 所有候选版本和 diagnostic-only 版本。
- 选择准则和是否通过。
- `observed_replication_used_for_selection = false`。

## 9. 报告必须回答的问题

最终报告必须回答：

- PIT universe 构建是否成功，是否替代了静态 `2025-12-31` universe。
- PIT universe 与旧静态 universe 在 2019-2024 的成员数量和行业分布差异。
- 旧 pullback 在 PIT universe 下是否仍是负贡献。
- `strong_trend_continuation` 是否有稳定正 expectancy。
- `weak_volume_rebound` 是否确认应剔除、收紧或另起规则。
- `breakdown_repair` 是否应完全禁止进入默认交易。
- rebuilt pullback 的改善是来自更高 expectancy，还是来自更高现金和更少交易。
- 是否存在可等待 future final test 的候选版本。
- 如果不存在，下一步应继续修 PIT 数据、放弃 pullback、还是做 breakout coverage 研究。

## 10. 测试计划

静态检查：

```text
uv run python -m compileall Explore7/scripts
uv run python Explore7/scripts/run_explore7.py self-test --config Explore7/configs/pullback_rebuild_v1.yaml
```

数据阶段：

```text
uv run python Explore7/scripts/run_explore7.py build-pit-universe --config Explore7/configs/pullback_rebuild_v1.yaml
uv run python Explore7/scripts/run_explore7.py audit-pit-data --config Explore7/configs/pullback_rebuild_v1.yaml
```

策略阶段：

```text
uv run python Explore7/scripts/run_explore7.py run-walk-forward --config Explore7/configs/pullback_rebuild_v1.yaml
uv run python Explore7/scripts/run_explore7.py report --config Explore7/configs/pullback_rebuild_v1.yaml
```

验收：

- `source_data_audit.csv` 必须证明来源配置只读取白名单键，所有历史 output/cache/backtest/diagnostic/result CSV 路径均未进入计算路径。
- PIT universe audit 不得显示使用未来基准日股票池。
- 若 `universe_point_in_time` 为 `false`，策略阶段必须失败。
- 若 `industry_membership_point_in_time` 为 `false`，候选选择必须失败；as-of 行业只能产生数据诊断。
- 若 provider 只覆盖旧静态 universe，策略阶段必须降级为 `coverage_limited_diagnostic` 并禁止形成候选。
- `pullback_classification_audit.csv` 必须覆盖三类 pullback 和 `unclassified_pullback`。
- `year_metrics.csv` 必须覆盖 2019-2024 distinct years。
- 报告必须明确写出是否形成 Explore7 候选版本。

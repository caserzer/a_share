# 需求：PIT Top-N 400/100 Universe V0（05_pit_topn_400_100_universe_v0）

## 1. 目标

在 `topics/02_AFML_BIG_WINNER` 下，参照
`01_data_prepare_pit_largecap_akshare_qlib_v0` 的 PIT 数据准备方式，构建一个新的
**每日固定配额 top-N PIT universe**，用于后续重新运行 02 reverse lifecycle profile。

当前 01 universe 使用固定市值阈值：

```text
main_board: total_market_cap_cny > 50bn
ChiNext:    total_market_cap_cny > 20bn
```

该口径导致早期 universe 明显偏小。04 补充报告显示：

```text
2018 avg daily universe = 91.4
2025 avg daily universe = 346.0
```

这会放大 train / validation / robustness 的机会集非平稳性。因此本实验改为每日 top-N 配额：

```text
main board: daily PIT total_market_cap top 400
ChiNext:    daily PIT total_market_cap top 100
target:     about 500 names per usable trading day
```

本实验是 **universe infrastructure**，不是 alpha 实验、不是事件候选生成器、不是 02/04 重跑。

## 2. 非目标

本实验不得：

- 重新定义 big-winner episode。
- 运行 02 reverse lifecycle profile。
- 运行 03 event contract 或 04 candidate generator。
- 训练 primary / meta / ranking model。
- 运行回测、组合净值、止损止盈或交易策略。
- 为了提高后续 recall 或 precision 调整 top-N 配额。
- 使用 latest-only 市值、latest-only 股本、当前成分股、当前 ST 状态或任何未来信息。

本实验完成后，下一步应是一个独立实验：

```text
rerun_02_reverse_lifecycle_on_topn_universe_v0
```

该后续实验必须基于本实验冻结的 new universe manifest 重新生成 target denominator。

## 3. 输入契约

本实验依赖 01 的数据层与审计结果。

必需输入：

```text
01_data_prepare_pit_largecap_akshare_qlib_v0
  config.yaml
  outputs/manifests/run_manifest.json
  outputs/tables/source_coverage_audit.csv
  outputs/tables/market_cap_source_audit.csv
  outputs/tables/daily_universe_counts.csv
  data/interim/qlib_csv/day 或等价个股日线缓存
  full board-eligible instrument-date market-cap/status panel
  fixed-cap membership files only for overlap/sensitivity audit
```

严禁用 01 的 fixed-cap membership 作为 top-N ranking 的候选全集。原因是 fixed-cap membership
已经按 `main_board > 50bn` / `ChiNext > 20bn` 过滤，若从该表再做 top-N，会把低于旧固定阈值但属于
board top 400/100 的股票永久排除，新 universe 会退化成旧 fixed-cap universe 的子集。

ranking candidate 必须来自全量 board-eligible instrument-date panel。该 panel 可以是 01 已输出的
candidate-before-threshold / candidate-before-status-exclusion 明细，也可以按 01 manifest、config、raw/source
cache 重新生成。无论来源如何，都必须包含所有 main board / ChiNext 普通股票在每个 membership date
的 PIT market cap 与状态字段，不能只包含旧 fixed-cap pass rows。

fixed-cap membership 文件：

```text
data/processed/universe/pit_largecap_main_chinext_membership_daily.csv
data/processed/universe/pit_largecap_main_chinext_executable_daily.csv
```

只允许用于：

```text
fixed_cap_overlap_audit
topn_only_vs_fixed_cap_only_audit
sensitivity baseline metadata
```

不得用于决定 top-N membership。

若 01 的全量候选明细或 processed membership 文件不在当前 checkout 中，允许按 01 的 manifest、config、source
cache 重新生成等价输入；但不得用 publishable summary 伪造成分明细。

必需字段：

```text
membership_date
usable_trade_date
instrument
ts_code
board_bucket
is_listed
is_st
is_suspended
total_market_cap_cny
market_cap_source
price_source
share_source
status_source
membership_rule_version
```

full candidate panel 额外必须支持：

```text
raw_unadjusted_close
total_share_asof 或 authoritative historical total_market_cap_cny
source_trade_date / source_asof_date
candidate_universe_source = full_board_candidate_panel
```

如果缺少 full board candidate panel、`total_market_cap_cny`、historical total share as-of、historical status 或
next-session calendar 映射，本实验必须 fail closed。

## 4. 日期范围

沿用 01 的日期范围：

```text
requested_start_date = 2017-01-01
requested_end_date   = 2026-05-31
```

实际交易日范围必须由 01 的交易日历解析，并写入 manifest：

```text
resolved_start_trading_date
resolved_end_trading_date
trading_session_count
calendar_source
```

所有 membership 以 close-observed raw membership date 和 next-session executable date 两套口径输出。

## 5. Board Buckets

沿用 01 的 board bucket 定义。

Main board：

```text
000, 001, 002, 003, 600, 601, 603, 605
```

ChiNext：

```text
300, 301
```

排除：

```text
STAR / 科创板: 688, 689
北京交易所
基金、指数、债券、优先股、B 股、非普通股
```

## 6. Eligibility 与 Ranking

每日先做 eligibility，再做 top-N 排名。

### 6.1 Eligibility

某股票在 membership date `D` 进入 bucket ranking 的条件：

```text
board_bucket in {main_board, chinext}
is_listed_D is true
is_st_D is false
is_suspended_D is false
total_market_cap_cny_D is finite and > 0
has required daily bar coverage
```

最小历史长度不得作为 top-N membership 的 hard eligibility gate。否则 2017 年和早期新上市股票会被再次系统性压低，
与“让各年份 universe 尽量均衡”的目标冲突。

本实验必须改为输出诊断字段：

```text
minimum_history_sessions = 240
history_observed_sessions_before_usable_date
history_ready_240d_flag
history_ready_missing_reason
```

历史长度按 `usable_trade_date` 之前可用交易日计算。若某股票市值排名足够高但历史长度不足，仍可进入
top-N executable membership，但必须标记：

```text
history_ready_240d_flag = false
history_ready_missing_reason = insufficient_history
```

后续 02 rerun 可以基于 feature/readiness 规则处理缺失历史，但 05 不得把 history readiness 变成 membership gate。

### 6.2 Ranking Field

排名字段：

```text
rank_value = total_market_cap_cny at membership_date close
```

市值必须是 historical total market cap，或由下式按 PIT 股本计算：

```text
total_market_cap_cny_D = raw_unadjusted_close_D * total_share_asof_D
```

禁止使用：

```text
latest spot market cap
latest/current total shares without historical as-of date
current security profile market cap
qfq close * shares
any source with ambiguous units
```

### 6.3 Top-N Rule

对每个 membership date `D`：

```text
main_board_members_D =
  eligible main_board stocks sorted by total_market_cap_cny desc
  keep rank <= 400

chinext_members_D =
  eligible ChiNext stocks sorted by total_market_cap_cny desc
  keep rank <= 100
```

若某 bucket eligible count 小于 quota：

```text
keep all eligible names
quota_fill_rate = kept_count / quota
quota_shortfall_count = quota - kept_count
quota_shortfall_reason = insufficient_eligible_names
```

排序必须 deterministic：

```text
sort by total_market_cap_cny desc, instrument asc
```

所有输出必须保留：

```text
board_rank_by_market_cap
board_quota
quota_fill_rate
rank_cutoff_market_cap_cny
rank_rule_version
history_observed_sessions_before_usable_date
history_ready_240d_flag
history_ready_missing_reason
```

## 7. Point-in-Time Clock

本实验必须严格区分：

```text
membership_date:
  close of D observed after market close

usable_trade_date:
  next trading session after membership_date
```

下游如果在 `usable_trade_date` 的 next open 执行，只能使用前一交易日 close 后已经可知的 membership。

禁止：

```text
用 membership_date close 信息交易 membership_date open
用未来日期排名补当日成分
用 latest/current 成分股回填历史
```

## 8. 输出契约

输出根目录：

```text
topics/02_AFML_BIG_WINNER/experiments/pending/05_pit_topn_400_100_universe_v0/outputs/
```

同时写入可复用 processed universe：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/
```

### 8.1 Processed Outputs

必需 processed files：

```text
data/processed/universe/pit_topn_400_100_membership_daily.csv
data/processed/universe/pit_topn_400_100_executable_daily.csv
data/processed/universe/pit_topn_400_100_intervals.csv
data/processed/universe/qlib_pit_topn_400_100.txt
```

`membership_daily.csv` keyed by:

```text
membership_date, instrument
```

`executable_daily.csv` keyed by:

```text
usable_trade_date, instrument
```

`executable_daily.csv` 每行必须保留来源 membership date：

```text
source_membership_date
membership_available_time = source_membership_date close
usable_trade_date
```

`source_membership_date` 必须严格早于 `usable_trade_date`。

不得存在重复键。

### 8.2 Publishable Tables

必需 publishable tables：

```text
outputs/publishable/tables/daily_universe_counts.csv
outputs/publishable/tables/board_bucket_counts.csv
outputs/publishable/tables/yearly_universe_summary.csv
outputs/publishable/tables/quota_fill_audit.csv
outputs/publishable/tables/rank_cutoff_audit.csv
outputs/publishable/tables/status_exclusion_audit.csv
outputs/publishable/tables/history_coverage_audit.csv
outputs/publishable/tables/fixed_cap_overlap_audit.csv
outputs/publishable/tables/topn_only_vs_fixed_cap_only_audit.csv
outputs/publishable/tables/data_source_coverage_audit.csv
```

`yearly_universe_summary.csv` 必须包含：

```text
year
trading_days
avg_daily_member_count
min_daily_member_count
max_daily_member_count
instrument_days
universe_years_252 = instrument_days / 252
avg_main_board_count
avg_chinext_count
main_board_quota_fill_rate_mean
chinext_quota_fill_rate_mean
history_ready_240d_rate
```

`fixed_cap_overlap_audit.csv` 必须按 date / year / board 输出：

```text
topn_count
fixed_cap_count
intersection_count
topn_only_count
fixed_cap_only_count
jaccard_overlap
```

## 9. 报告要求

主报告：

```text
outputs/publishable/reports/pit_topn_400_100_universe_report.md
```

报告必须包含：

1. Final decision。
2. 输入 source / manifest / hash 审计。
3. Universe rule summary。
4. 每年 avg/min/max daily universe count。
5. 每年 `universe_years_252`。
6. 每年 board mix。
7. 每年 quota fill audit。
8. rank cutoff market cap 分布。
9. top-N universe 与 fixed-cap universe overlap。
10. 历史 readiness 诊断，以及 ST、停牌、缺失日线的排除影响。
11. 明确说明本实验不重跑 02，不产生 target episode denominator。
12. 下一步：在本 universe 上重跑 02 reverse lifecycle profile。

## 10. Manifest

必需 manifest：

```text
outputs/manifests/run_manifest.json
```

manifest 必须记录：

```text
experiment_name
source_git_revision
created_at_utc
config_hash
input_paths
input_hashes
output_paths
output_hashes
upstream_01_manifest_hash
upstream_01_git_revision
resolved_start_trading_date
resolved_end_trading_date
rank_rule_version
quota_main_board = 400
quota_chinext = 100
minimum_history_sessions = 240
candidate_panel_source
decision
gate_summary
```

## 11. Validation Gates

本实验必须 fail closed 或输出 blocked decision，不能静默成功。

### 11.1 Hard Fail

以下情况必须 hard fail：

```text
missing historical market cap / total share as-of
missing full board candidate panel
latest-only market cap used
latest-only status used
calendar mapping unavailable
duplicate membership key
duplicate executable key
instrument outside allowed board buckets enters universe
membership_date not before usable_trade_date
top-N ranking source is old fixed-cap membership instead of full candidate panel
```

### 11.2 Decision Gates

建议 decision values：

```text
topn_universe_supported
topn_universe_source_blocked
topn_universe_pit_clock_blocked
topn_universe_quota_fill_blocked
topn_universe_history_coverage_blocked
topn_universe_candidate_panel_blocked
topn_universe_overlap_diagnostic_only
```

最低支持条件：

```text
all required source audits pass
no latest-only leakage
ranking source is full board candidate panel, not fixed-cap membership
no duplicate keys
daily member count <= 500
main_board_count <= 400
chinext_count <= 100
avg total quota_fill_rate reported, not necessarily >= fixed threshold
yearly universe summary complete for all covered years
fixed-cap overlap audit complete
history readiness reported but not used as membership gate
```

`quota_fill_rate` 低本身不应自动 fail，因为早期 market may not have enough eligible names。若 fill rate 低，报告必须解释是
`insufficient_eligible_names`、`status_exclusion` 还是 `missing_source` 导致。

`topn_universe_quota_fill_blocked` 只能在 fill rate 低是由 source/status/candidate-panel 缺失或 PIT clock 错误导致时使用。
如果 fill rate 低是因为某年某 bucket 的 eligible names 自然不足，则只能作为 diagnostic，不得 blocked。

`topn_universe_history_coverage_blocked` 只能在历史覆盖审计无法计算时使用；不能因为某些股票
`history_ready_240d_flag = false` 而 blocked。

## 12. Tests

必须新增测试覆盖：

```text
tests/test_pit_topn_400_100_universe.py
```

最低测试：

1. Top-N sorting deterministic：市值降序，instrument 升序打破平手。
2. Bucket quota：主板不超过 400，创业板不超过 100。
3. PIT clock：`usable_trade_date` 是 `membership_date` 后的下一交易日。
4. Eligibility：ST、停牌、非上市、市值缺失不得进入 executable universe。
5. No leakage：latest-only 市值 / 股本 source 必须被拒绝。
6. Duplicate keys rejected。
7. Overlap audit count identity：

```text
topn_count = intersection_count + topn_only_count
fixed_cap_count = intersection_count + fixed_cap_only_count
```

8. `universe_years_252 = sum(member_count) / 252`。
9. Ranking source guard：若输入只有 fixed-cap membership rows，测试必须失败。
10. History readiness：缺历史股票可以进入 membership，但必须标记 `history_ready_240d_flag = false`。
11. Executable rows preserve `source_membership_date` and `source_membership_date < usable_trade_date`。

## 13. 后续实验接口

后续 02 rerun 必须读取：

```text
data/processed/universe/pit_topn_400_100_executable_daily.csv
experiments/pending/05_pit_topn_400_100_universe_v0/outputs/manifests/run_manifest.json
```

后续 02 rerun 不得继续使用 fixed-cap denominator，除非作为 sensitivity 对照。

本实验成功后，下一实验的 objective 应写为：

```text
Rerun big winner reverse lifecycle profile on PIT top-N 400/100 universe,
freeze a new target episode denominator, and compare lifecycle dominance
against the fixed-cap baseline.
```

# 15A Path-Defined Winner Episode Label 右删失诊断报告

## 1. 单行裁决

15A 的裁决状态为 `15A_material_censoring_but_slow_winner_overlaps_known_failed_morphology`。结论分成两层：第一，fixed-120d winner label 对慢速大赢家存在实质性右删失；第二，这批 slow winner 没有形成相对既有失败形态足够独立的新表面，因此 `15B`、label deployment、signal search 均不授权。

| item | value |
|---|---|
| decision_state | `15A_material_censoring_but_slow_winner_overlaps_known_failed_morphology` |
| selected_threshold | `up50pct` |
| selected_threshold_reason | `lowest_pre_registered_material_censoring_threshold` |
| selected_threshold_share_beyond_120d | 0.7286 |
| selected_threshold_slow_winner_rate_all_records | 0.4372 |
| selected_threshold_censored_rate | 0.4000 |
| next_allowed_requirement | `none` |
| label_deployment_authorized | `False` |
| signal_search_authorized | `False` |

核心 insight：15A 证明了“120 个交易日窗口会漏掉大量慢速赢家”，但也证明了“这些慢速赢家并不是一个可直接升级为下一轮 alpha 搜索的新形态”。AFML 决策上，这更像 label definition 的风险暴露，而不是一个已经具备 morphology independence 的新交易机会。

## 2. 本实验回答什么

15A 只回答一个边界清晰的问题：如果 winner 由完整 forward path 定义，而不是固定 120d horizon 定义，那么 fixed-120d label 是否会把大量最终会涨到阈值的样本提前当作非赢家或不可见样本。这里不训练模型、不寻找 entry、不定义 exit、不做仓位建议；全部统计单位都是 anchor row。

几个关键口径如下：

| metric | 含义 |
|---|---|
| `path_winner_n` | 在可观察 forward path 中最终达到阈值的 anchor row 数 |
| `fixed120_winner_n` | 120 个交易日内达到阈值的 anchor row 数 |
| `slow_winner_n` | `path_winner_n - fixed120_winner_n`，即 120d 之后才达标的 path winner |
| `share_beyond_120d` | slow winner 占 path winner 的比例，也是 fixed-120d 会漏掉的 path-defined winner 比例 |
| `slow_winner_rate_all_records` | slow winner 占全部 anchor rows 的比例，衡量漏标群体在 universe 中的密度 |
| `censored_rate` | primary no-horizon label 中无法确认为 winner 的右删失比例；这些行不能当作 confirmed negative |

## 3. 输入、lineage 与 fail-closed 审计

所有 gate 均通过，说明本轮报告里的差异不是由输入缺失、split 泄漏、universe mismatch 或 price path 不完整造成。

| gate | status |
|---|---|
| input | `pass` |
| upstream_lineage | `pass` |
| universe_membership | `pass` |
| price_path_completeness | `pass` |
| label_rebuild | `pass` |
| censoring_isolation | `pass` |
| winner_set_difference | `pass` |
| search_accounting | `pass` |

| audit item | value |
|---|---|
| required_input_artifacts | 17 |
| passed_input_artifacts | 17 |
| primary_row_level_source_role | `14A_native_rebuild_panel` |
| primary_row_level_source | `/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0/outputs/local_cache/14A_full_native_sparse_state_change_event_utility_preflight/native_rebuild_panel.parquet` |
| cross_check_key_coverage_rate | 1.0000 |
| cross_check_mismatch_n | 0 |
| path_window_reconciliation_status | `pass_with_documented_13a_entry_anchor` |
| price_path_instrument_n | 1449 |
| min_forward_sessions | 105 |
| median_instrument_forward_sessions | 1128 |

Universe membership 也没有发现 split 边界漂移。

| split | unique_anchor_row_n | membership_match_rate | split_boundary_status | universe_membership_status |
|---|---:|---:|---|---|
| train | 216794 | 1.0000 | `pass` | `pass` |
| validation | 61307 | 1.0000 | `pass` | `pass` |
| robustness | 130614 | 1.0000 | `pass` | `pass` |

## 4. Winner 集合差异

Train split 上，三个预注册阈值都达到 material censoring。`up50pct` 被选中不是因为最强，而是因为它是最低的、预注册的 material censoring threshold。

| threshold | record_n | path_winner_n | path_winner_rate | fixed120_winner_n | fixed120_rate | slow_winner_n | slow_rate_all | share_beyond_120d | censored_rate | path_only_n | fixed120_only_n |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| up50pct | 216794 | 130087 | 0.6000 | 35301 | 0.1628 | 94786 | 0.4372 | 0.7286 | 0.4000 | 94786 | 0 |
| up100pct | 216794 | 81823 | 0.3774 | 7521 | 0.0347 | 74302 | 0.3427 | 0.9081 | 0.6226 | 74302 | 0 |
| up150pct | 216794 | 53491 | 0.2467 | 2042 | 0.0094 | 51449 | 0.2373 | 0.9618 | 0.7533 | 51449 | 0 |

`up50pct` 的跨 split 读数显示，右删失不是 train-only 现象，但不同 split 的路径长度和市场段落会改变强度。

| split | record_n | path_winner_n | path_rate | fixed120_winner_n | fixed120_rate | slow_winner_n | slow_rate_all | share_beyond_120d | censored_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 216794 | 130087 | 0.6000 | 35301 | 0.1628 | 94786 | 0.4372 | 0.7286 | 0.4000 |
| validation | 61307 | 27875 | 0.4547 | 3371 | 0.0550 | 24504 | 0.3997 | 0.8791 | 0.5453 |
| robustness | 130614 | 53089 | 0.4065 | 22053 | 0.1690 | 31024 | 0.2375 | 0.5844 | 0.5935 |
| all | 408715 | 211051 | 0.5164 | 60725 | 0.1486 | 150314 | 0.3678 | 0.7122 | 0.4836 |

发现：在 train 上，`up50pct` 的 path winner rate 是 60.00%，但 fixed-120d winner rate 只有 16.28%；也就是说，120d 口径只捕捉到一小部分最终涨幅达到 50% 的 anchor rows。`fixed120_only_n = 0` 说明 fixed-120d winner 是 path winner 的子集，差异主要来自 path-only slow winners，而不是两个 label 定义互相冲突。

## 5. Time-to-threshold 分布

Train split 上的达标时间分布说明 slow winner 不是 120d 附近的轻微边界误差，而是完整路径上明显更慢的一组上涨。

| threshold | path_winner_n | p10 | p25 | median | p75 | p90 | max | share_within_120d | share_beyond_120d | share_beyond_250d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| up50pct | 130087 | 45 | 112 | 297 | 792 | 1169 | 2014 | 0.2714 | 0.7286 | 0.5405 |
| up100pct | 81823 | 126 | 232 | 569 | 1078 | 1335 | 2025 | 0.0919 | 0.9081 | 0.7265 |
| up150pct | 53491 | 182 | 318 | 818 | 1223 | 1438 | 2026 | 0.0382 | 0.9618 | 0.8274 |

`up50pct` 的跨 split time-to-threshold 显示同一 label 问题在不同样本段上形态不同。

| split | path_winner_n | p10 | p25 | median | p75 | p90 | max | share_beyond_120d | share_beyond_250d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 130087 | 45 | 112 | 297 | 792 | 1169 | 2014 | 0.7286 | 0.5405 |
| validation | 27875 | 93 | 260 | 440 | 634 | 742 | 1062 | 0.8791 | 0.7599 |
| robustness | 53089 | 42 | 79 | 139 | 228 | 339 | 540 | 0.5844 | 0.2190 |
| all | 211051 | 47 | 106 | 240 | 584 | 1017 | 2014 | 0.7122 | 0.4886 |

解读：`up50pct` 在 train 的 median 达标时间为 297 个交易日，p75 为 792，p90 为 1169；`up150pct` 的 median 更达到 818。固定 120d horizon 对这种路径型 winner 的压缩非常强，特别是更高涨幅阈值下，绝大多数 winner 天然落在 120d 之外。

## 6. Censoring isolation

Censoring isolation gate 通过。关键是：censored rows 只进入 `record_n`、`censored_n`、`censored_rate` 的统计，不会被塞进 confirmed non-winner。`observed_non_hit_control` 只是 readout-only control，不能当作训练负样本授权。

| threshold | split | censored_n | censored_rate | median_available_forward_sessions | confirmed_non_winner_n | counted_in_confirmed_non_winner_n | observed_non_hit_control_n | status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| up50pct | train | 86707 | 0.4000 | 1314 | 0 | 0 | 86707 | `pass` |
| up50pct | validation | 33432 | 0.5453 | 805 | 0 | 0 | 33432 | `pass` |
| up50pct | robustness | 77525 | 0.5935 | 279 | 0 | 0 | 39925 | `pass` |
| up100pct | train | 134971 | 0.6226 | 1339 | 0 | 0 | 134971 | `pass` |
| up150pct | train | 163303 | 0.7533 | 1370 | 0 | 0 | 163303 | `pass` |

发现：阈值越高，censored rate 越高。Train 上 `up50pct` censored rate 为 40.00%，`up100pct` 为 62.26%，`up150pct` 为 75.33%。这意味着更高阈值虽然看起来更接近“big winner”，但也更容易被 forward path 观察边界主导，不能简单把未命中样本视为真正失败。

## 7. 已知失败形态重叠

15A 的阻断点在这里。slow winner 的确被 fixed-120d 漏掉，但它没有相对 fast winner 展现出足够强的、预注册意义上的形态独立性。

| threshold | state | slow_share | fast_share | fast_minus_slow_delta | status |
|---|---|---:|---:|---:|---|
| up50pct | compression_state | 0.2110 | 0.1956 | -0.0154 | `overlaps_known_failed_morphology` |
| up50pct | drawdown_reversal_state | 0.1643 | 0.2242 | 0.0599 | `overlaps_known_failed_morphology` |
| up100pct | compression_state | 0.2106 | 0.2246 | 0.0140 | `overlaps_known_failed_morphology` |
| up100pct | drawdown_reversal_state | 0.1717 | 0.2401 | 0.0684 | `overlaps_known_failed_morphology` |
| up150pct | compression_state | 0.2108 | 0.2728 | 0.0620 | `overlaps_known_failed_morphology` |
| up150pct | drawdown_reversal_state | 0.1803 | 0.2674 | 0.0871 | `overlaps_known_failed_morphology` |

对 selected threshold `up50pct`，compression 的 delta 是 -0.0154，说明 slow winner 在 compression_state 上并不比 fast winner 更少，反而略高；drawdown_reversal 的 delta 是 0.0599，也没有达到可解释为 distinct surface 的强度。`up150pct` 的两个 delta 虽然更接近，但仍未达到足以解除阻断的阈值。

AFML insight：label horizon 的错误和可交易 morphology 是两件事。15A 支持“不能用 fixed-120d 轻率否定慢速 winner”，但不支持“slow winner 自身就是独立 alpha 表面”。因此这里应停在诊断结论，而不是进入信号搜索。

## 8. Anchor-row overlap density

这些数字只说明连续 anchor 对同一上涨 interval 的重复计数密度，不替代 primary anchor-row denominator。Primary 统计仍以 anchor row 为单位，但 overlap density 能提醒我们不要把 `path_winner_n` 直接理解成互相独立的市场 episode 数。

| threshold | split | winner_anchor_n | slow_anchor_n | approx_cluster_n | median_rows_per_cluster | p90_rows_per_cluster | max_rows_per_cluster |
|---|---|---:|---:|---:|---:|---:|---:|
| up50pct | train | 130087 | 94786 | 1040 | 64.00 | 340.50 | 472 |
| up50pct | validation | 27875 | 24504 | 477 | 46.00 | 128.00 | 128 |
| up50pct | robustness | 53089 | 31024 | 558 | 54.00 | 255.30 | 271 |
| up50pct | all | 211051 | 150314 | 1459 | 63.00 | 388.20 | 871 |
| up100pct | train | 81823 | 74302 | 670 | 70.50 | 325.10 | 472 |
| up150pct | train | 53491 | 51449 | 456 | 63.00 | 330.00 | 472 |

解读：以 `up50pct` train 为例，130087 个 winner anchor rows 约落在 1040 个重叠 cluster 中，median 每个 cluster 有 64 行，p90 达到 340.5 行。这说明很多 anchor rows 是同一段上涨路径的不同切片。该事实不推翻右删失结论，但会限制后续任何模型评估的有效样本独立性。

## 9. 结论与下一步

15A 的正向发现是明确的：fixed-120d label 会系统性漏掉慢速 path-defined winners，且该现象在 train、validation、robustness 中都可见。`up50pct` 上，all split 的 path winner rate 为 51.64%，fixed120 rate 只有 14.86%，slow winner rate 为 36.78%，`share_beyond_120d` 为 71.22%。

15A 的负向约束同样明确：slow winner 与已知失败形态仍有重叠，selected threshold 没有通过 morphology distinctness 读数。因此当前最稳妥的处理不是推进 15B，也不是把 slow winner label 直接部署到训练或交易，而是把本实验作为 label horizon 风险证据保留。若后续继续研究，应先解决 episode 去重、样本独立性、以及 slow winner 是否存在独立形态的问题，再讨论 separability 或 alpha 搜索。

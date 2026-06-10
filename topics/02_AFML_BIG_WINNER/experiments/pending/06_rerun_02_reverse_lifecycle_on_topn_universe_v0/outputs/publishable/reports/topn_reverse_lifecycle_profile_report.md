# PIT Top-N 反向生命周期画像报告（06）

## 1. 结论摘要

本实验将 `02_big_winner_reverse_lifecycle_profile_v0` 的反向生命周期画像完整迁移到 `05_pit_topn_400_100_universe_v0` 产出的 PIT Top-N 400/100 universe/proxy。最终结论为：

```text
final_decision = topn_reverse_lifecycle_sequence_supported_universal_dominance
semantic_02_replay_decision = reverse_lifecycle_sequence_supported_universal_dominance
universe_precision_status = available_source_topn_candidate_gap
```

核心读数如下：

- Top-N/proxy universe 下识别到 `2,493` 个 `mfe_120 >= 50%` big-winner episode；02 fixed-cap 基线为 `866` 个，增加 `1,627` 个，约为 02 的 `2.88` 倍。
- 分母为 `912,851` 个可评估 instrument-days，即 `3622.42` 个 252 交易日 universe-years。
- 全样本 episode rate 为 `68.82` episodes / 100 universe-years。
- 02 规则不变量审计为 `pass`；除了 universe 输入和 universe 精度标签以外，episode 定义、split、alignment、matching、dominance gate、industry 状态均保持 02 规则。
- 匹配质量没有因为 universe 替换而恶化：low-axis 匹配覆盖率为 `0.9956`，平均每个 winner 有 `4.85` 个 matched controls；EMA60 anchor-axis 匹配覆盖率为 `0.9687`。
- 6 个预设序列中，`S1`、`S2`、`S3`、`S6` 达到跨 train / validation / robustness 同向支持；`S3_repair_rank_persistence_v0` 和 `S6_continuation_discriminator_v0` 是最强的结构性差异。

最重要的解释是：Top-N universe 不是简单放宽口径，而是把机会集从固定市值阈值改成每日排名型大盘/创业板代理。这个替换后，big-winner episode 密度显著上升，尤其集中在 `risk_off` regime 和创业板分母中；同时，序列 dominance 结论仍通过 02 的稳定性门槛。

## 2. Universe 输入与精度 caveat

05 universe 的当前状态不是严格的历史全市场 exact top 400/100，而是可用数据源上的 top-N proxy。06 接受这个输入，但所有结论必须携带同一个 caveat：

```text
upstream_05_decision = topn_universe_candidate_panel_blocked
active_source_gap_count = 229
source_gap_count = 318
exact_topn_supported = False
topn_candidate_gap_accepted = True
```

05 source coverage audit 的 reconciliation 是通过的：`missing_active_source` 且 `active_in_requested_window = true` 的股票数为 `229`，等于 manifest 中的 `active_source_gap_count`。因此本实验可以运行，但结论应表述为“available-source top-N proxy”，不能表述为“精确历史 top 400/100”。

### 2.1 05 source coverage audit 汇总

| support_state           |   instrument_count |
|:------------------------|-------------------:|
| supported               |               4597 |
| missing_active_source   |                229 |
| missing_inactive_source |                 89 |

### 2.2 active / inactive source gap 对账

| support_state           |   inactive_window_count |   active_window_count |
|:------------------------|------------------------:|----------------------:|
| missing_active_source   |                       0 |                   229 |
| missing_inactive_source |                      89 |                     0 |
| supported               |                       0 |                  4597 |

这里的含义是：本地缓存支持 `4,597` 只股票；另有 `229` 只在请求窗口内 active 但缺源数据，另有 `89` 只是 inactive source gap。06 的 denominator 是在可审计可用源上构造的 Top-N 机会集。

## 3. Denominator 与 episode rate

06 的主分母不是 episode 数，也不是股票数，而是满足 PIT clock、250-session prior lookback、120-session label completeness 和 split 范围的可评估 Top-N instrument-days。

### 3.1 总体分母

| scope   |   raw_topn_instrument_days |   evaluated_instrument_days |   instrument_days |   universe_years_252 |   episode_count |   episodes_per_100_universe_years |
|:--------|---------------------------:|----------------------------:|------------------:|---------------------:|----------------:|----------------------------------:|
| all     |                    1140000 |                      912851 |            912851 |            3622.4246 |            2493 |                           68.8213 |

`raw_topn_instrument_days = 1,140,000`，但最终可评估分母为 `912,851`。2017 年因为 250-session prior lookback 不完整而不进入可评估分母；2026 年因为 120-session forward label completeness 不完整而不进入可评估分母。

### 3.2 年度 episode rate

| year | episode_count | universe_years_252 | episodes_per_100_universe_years |
|-----:|--------------:|-------------------:|--------------------------------:|
| 2018 |           353 |           422.2659 |                         83.5966 |
| 2019 |           240 |           456.6746 |                         52.5538 |
| 2020 |           418 |           456.8849 |                         91.4891 |
| 2021 |           279 |           458.2778 |                         60.8801 |
| 2022 |           328 |           457.3929 |                         71.7108 |
| 2023 |           117 |           467.0714 |                         25.0497 |
| 2024 |           405 |           475.2460 |                         85.2190 |
| 2025 |           353 |           428.6111 |                         82.3590 |

年度上，episode rate 的高点出现在 2020 年（`91.49` / 100 universe-years）、2024 年（`85.22`）和 2018 年（`83.60`）；2023 年明显较低（`25.05`）。这说明 Top-N big-winner 密度不是均匀时间分布，而是强烈受市场阶段影响。2024-2025 的高密度也是后续 04 事件候选器需要重点验证的 regime pressure。

### 3.3 split 分母

| split      |   episode_count |   evaluated_instrument_days |   universe_years_252 |   episodes_per_100_universe_years |
|:-----------|----------------:|----------------------------:|---------------------:|----------------------------------:|
| robustness |             758 |                      227772 |             903.8571 |                           83.8628 |
| train      |            1290 |                      452114 |            1794.1032 |                           71.9022 |
| validation |             445 |                      232965 |             924.4643 |                           48.1360 |

- Train：`1,290` episodes，`1,794.10` universe-years，rate `71.90`。
- Validation：`445` episodes，`924.46` universe-years，rate `48.14`。
- Robustness：`758` episodes，`903.86` universe-years，rate `83.86`。

Validation 不是空样本，且 matched control 机会存在，但 episode rate 低于 train 和 robustness。因此，后续不能只看全样本 lift；必须保留 validation split 作为真正的结构筛选和反过拟合检查。

### 3.4 板块分母

| board_bucket   |   episode_count |   universe_years_252 |   episodes_per_100_universe_years |
|:---------------|----------------:|---------------------:|----------------------------------:|
| chinext        |             679 |             682.3929 |                           99.5028 |
| main_board     |            1814 |            2940.0317 |                           61.7000 |

主板贡献更多 episode 绝对数量（`1,814`），但创业板 episode rate 更高（`99.50` vs 主板 `61.70` / 100 universe-years）。这意味着 Top-N universe 的“高密度”并非只来自主板股票数更多；创业板在相同 universe-year 分母下更容易出现 +50% episode。

### 3.5 市场状态分母

| market_regime_bucket   |   episode_count |   universe_years_252 |   episodes_per_100_universe_years |
|:-----------------------|----------------:|---------------------:|----------------------------------:|
| risk_off               |            1580 |             987.6468 |                          159.9762 |
| risk_on                |             428 |            1659.1786 |                           25.7959 |
| transition             |             485 |             975.5992 |                           49.7130 |

`risk_off` 分母下的 episode rate 达到 `159.98` / 100 universe-years，显著高于 `transition` 的 `49.71` 和 `risk_on` 的 `25.80`。这个结果非常重要：Top-N big winners 更像是风险偏弱或压力市场后的反转/修复过程，而不是 risk-on 中的单纯顺势延续。04 的事件候选器如果继续追求高召回，需要单独设计 risk_off repair/transition 通道。

## 4. Episode 样本画像

### 4.1 Episode 数量与结构

| duration_bucket   |   episode_count | denominator_scope                         |
|:------------------|----------------:|:------------------------------------------|
| fast              |             324 | not_applicable_duration_episode_attribute |
| long              |            1578 | not_applicable_duration_episode_attribute |
| medium            |             591 | not_applicable_duration_episode_attribute |

按 duration bucket 看，long episode 为 `1,578` 个，占 `63.3%`；medium 为 `591` 个，占 `23.7%`；fast 为 `324` 个，占 `13.0%`。多数 Top-N big winners 不是几天内完成的尖峰，而是在 60-120 session 的窗口中逐步走出。

### 4.2 MFE 与 low-to-high 时间分布

MFE 分布：

|   quantile |   mfe_120 |
|-----------:|----------:|
|     0.0000 |    0.5000 |
|     0.2500 |    0.5750 |
|     0.5000 |    0.6834 |
|     0.7500 |    0.9078 |
|     0.9000 |    1.2987 |
|     0.9500 |    1.6301 |
|     0.9900 |    2.5870 |
|     1.0000 |    5.4769 |

Low-to-high session 分布：

|   quantile |   low_to_high_sessions |
|-----------:|-----------------------:|
|     0.0000 |                 5.0000 |
|     0.2500 |                61.0000 |
|     0.5000 |                94.0000 |
|     0.7500 |               112.0000 |
|     0.9000 |               118.0000 |
|     0.9500 |               120.0000 |
|     0.9900 |               120.0000 |
|     1.0000 |               120.0000 |

中位数 `mfe_120` 为 `68.34%`，75 分位为 `90.78%`，90 分位为 `129.87%`。这说明 `mfe_120 >= 50%` 不是边缘触线样本；相当一部分 episode 有明显超额空间。low-to-high session 的中位数为 `94`，75 分位为 `112`，95 分位已到 `120`，因此 120-session horizon 是真实约束，不应缩短。

### 4.3 集中度

Top instruments：

| instrument   |   episode_count |
|:-------------|----------------:|
| SH603993     |              11 |
| SZ300339     |              11 |
| SZ300033     |              10 |
| SH601689     |              10 |
| SH600584     |              10 |
| SZ300136     |              10 |
| SH601100     |              10 |
| SZ002384     |              10 |
| SZ300073     |               9 |
| SH603369     |               9 |
| SH600460     |               9 |
| SH600570     |               9 |

Manifest 中 `winner_instrument_max_share = 0.0044`，`winner_year_max_share = 0.1677`。episode 数量虽然从 02 的 866 增加到 2,493，但并没有被少数股票或某一年垄断；这增强了 Top-N rerun 的可用性。

## 5. 与 02 fixed-cap 基线的对比

| metric                          | fixed_cap_02                                             | topn_06                                                       |     delta | notes                                                                |
|:--------------------------------|:---------------------------------------------------------|:--------------------------------------------------------------|----------:|:---------------------------------------------------------------------|
| decision                        | reverse_lifecycle_sequence_supported_universal_dominance | topn_reverse_lifecycle_sequence_supported_universal_dominance |  nan      | Decision comparison only; 06 decision is based on top-N denominator. |
| target_episode_count            | 866                                                      | 2493                                                          | 1627.0000 |                                                                      |
| universe_years_252              | nan                                                      | 3622.4246031746034                                            |  nan      | 02 did not publish an executable universe-year denominator.          |
| episodes_per_100_universe_years | nan                                                      | 68.82130818720688                                             |  nan      | Top-N rate uses evaluated available-source Top-N denominator.        |
| train_winner_episodes           | 285                                                      | 1290                                                          |  nan      |                                                                      |
| validation_winner_episodes      | 169                                                      | 445                                                           |  nan      |                                                                      |
| robustness_winner_episodes      | 412                                                      | 758                                                           |  nan      |                                                                      |
| low_match_coverage              | 0.9826789838337182                                       | 0.99558764540714                                              |  nan      |                                                                      |
| average_controls_per_winner     | 4.549653579676674                                        | 4.851183313277176                                             |  nan      |                                                                      |

对比结论：

- 方向性结论没有改变：02 和 06 都给出 sequence-level universal dominance support。
- Top-N/proxy universe 的 target episode count 从 `866` 提升到 `2,493`，增加 `1,627`。
- Train / validation / robustness 三段均增加，而不是只在某一个 split 增加：train 从 `285` 到 `1,290`，validation 从 `169` 到 `445`，robustness 从 `412` 到 `758`。
- Low-axis control matching 反而更好：coverage 从 `0.9827` 提升到 `0.9956`，平均 controls per winner 从 `4.55` 提升到 `4.85`。
- 02 没有发布 executable universe-year denominator，因此不能直接比较 02 和 06 的 episodes / 100 universe-years；06 rate 只能作为 Top-N/proxy denominator 下的绝对密度。

## 6. Matching 与 validation opportunity

### 6.1 Winner-control matching 质量

| match_axis        | split      |   winner_count |   matched_winner_count |   control_match_count |   match_coverage |   average_controls_per_winner |   unmatched_winner_count |   cross_split_boundary_unusable_count |
|:------------------|:-----------|---------------:|-----------------------:|----------------------:|-----------------:|------------------------------:|-------------------------:|--------------------------------------:|
| shared_axis_low   | all        |           2493 |                   2482 |                 12094 |           0.9956 |                        4.8512 |                       11 |                                     0 |
| shared_axis_low   | train      |           1290 |                   1281 |                  6252 |           0.9930 |                        4.8465 |                        9 |                                     0 |
| shared_axis_low   | validation |            445 |                    443 |                  2186 |           0.9955 |                        4.9124 |                        2 |                                     0 |
| shared_axis_low   | robustness |            758 |                    758 |                  3656 |           1.0000 |                        4.8232 |                        0 |                                     0 |
| shared_axis_ema60 | all        |           2493 |                   2415 |                 11902 |           0.9687 |                        4.7742 |                       78 |                                  1853 |
| shared_axis_ema60 | train      |           1290 |                   1250 |                  6160 |           0.9690 |                        4.7752 |                       40 |                                     0 |
| shared_axis_ema60 | validation |            445 |                    429 |                  2138 |           0.9640 |                        4.8045 |                       16 |                                   260 |
| shared_axis_ema60 | robustness |            758 |                    736 |                  3604 |           0.9710 |                        4.7546 |                       22 |                                  1593 |

Low-axis 全样本中，`2,493` 个 winner 里有 `2,482` 个成功匹配，`12,094` 条 control match，coverage 为 `0.9956`。Robustness split 的 low-axis coverage 达到 `1.0000`，validation coverage 为 `0.9955`。EMA60 anchor-axis coverage 为 `0.9687`，略低但仍可用。

EMA60 axis 的 `cross_split_boundary_unusable_count` 较高，尤其在 robustness 中为 `1,593`。这不是 failure，而是 02 规则下为避免跨 split 污染而剔除的不可用匹配机会。validation opportunity audit 仍标记为 available。

### 6.2 Validation opportunity audit

| split      | match_axis        | split_start   | split_end   |   winner_episode_count |   matched_winner_count |   control_match_count |   cross_split_boundary_unusable_count | opportunity_status   |
|:-----------|:------------------|:--------------|:------------|-----------------------:|-----------------------:|----------------------:|--------------------------------------:|:---------------------|
| train      | shared_axis_low   | 2017-01-03    | 2021-12-31  |                   1290 |                   1281 |                  6252 |                                     0 | available            |
| train      | shared_axis_ema60 | 2017-01-03    | 2021-12-31  |                   1290 |                   1250 |                  6160 |                                     0 | available            |
| validation | shared_axis_low   | 2022-01-01    | 2023-12-31  |                    445 |                    443 |                  2186 |                                     0 | available            |
| validation | shared_axis_ema60 | 2022-01-01    | 2023-12-31  |                    445 |                    429 |                  2138 |                                   260 | available            |
| robustness | shared_axis_low   | 2024-01-01    | 2025-11-26  |                    758 |                    758 |                  3656 |                                     0 | available            |
| robustness | shared_axis_ema60 | 2024-01-01    | 2025-11-26  |                    758 |                    736 |                  3604 |                                  1593 | available            |

## 7. Anchor 与 repair 结构

### 7.1 EMA60 reclaim anchor

| source_group           | split      |   row_count |   anchor_present_count |   missing_event_absent_count |   anchor_occurrence_rate |   anchor_year_coverage | claim_status         |
|:-----------------------|:-----------|------------:|-----------------------:|-----------------------------:|-------------------------:|-----------------------:|:---------------------|
| winner_reference       | robustness |         758 |                    737 |                           21 |                   0.9723 |                      3 | diagnostic_candidate |
| winner_reference       | train      |        1290 |                   1256 |                           34 |                   0.9736 |                      5 | diagnostic_candidate |
| winner_reference       | validation |         445 |                    429 |                           16 |                   0.9640 |                      3 | diagnostic_candidate |
| control_candidate_pool | robustness |        1552 |                   1533 |                           19 |                   0.9878 |                      3 | diagnostic_candidate |
| control_candidate_pool | train      |        3786 |                   3669 |                          117 |                   0.9691 |                      5 | diagnostic_candidate |
| control_candidate_pool | validation |        2152 |                   2121 |                           31 |                   0.9856 |                      3 | diagnostic_candidate |
| matched_low_controls   | robustness |        3656 |                   3591 |                           65 |                   0.9822 |                      3 | diagnostic_candidate |
| matched_low_controls   | train      |        6252 |                   6186 |                           66 |                   0.9894 |                      5 | diagnostic_candidate |
| matched_low_controls   | validation |        2186 |                   2164 |                           22 |                   0.9899 |                      3 | diagnostic_candidate |

Winner reference 中，`first_ema60_reclaim` 可观测次数为 `2422`，缺失 `71` 次。按 split 看，winner anchor occurrence rate 分别为 train `0.9736`、validation `0.9640`、robustness `0.9723`。这说明 EMA60 reclaim 不是只在某个 split 出现的偶然结构。

### 7.2 Winner-only lifecycle stage

| stage         |   episode_rows |   session_count_mean |   return_20d_mean |   amount_ratio_20d_mean |   close_to_ema60_mean |   close_to_derived_daily_vwap_mean |   atr_20_pct_mean |   stock_vs_market_20d_mean |
|:--------------|---------------:|---------------------:|------------------:|------------------------:|----------------------:|-----------------------------------:|------------------:|---------------------------:|
| low_to_high   |           2493 |              85.8901 |            0.0686 |                  1.2042 |                0.0588 |                             0.0014 |            0.0412 |                     0.0485 |
| post_high_30d |           2493 |              30.0000 |            0.0284 |                  0.8671 |                0.0873 |                            -0.0016 |            0.0538 |                     0.0133 |
| pre_low_60d   |           2493 |              61.0000 |            0.0072 |                  1.0113 |                0.0107 |                            -0.0006 |            0.0412 |                     0.0097 |

Winner-only stage profile 给出清晰的反向生命周期图像：

- `pre_low_60d`：20 日收益均值只有 `0.0072`，amount ratio 约 `1.0113`，close-to-EMA60 约 `0.0107`，说明低点前没有强趋势扩张。
- `low_to_high`：20 日收益均值升至 `0.0686`，amount ratio 升至 `1.2042`，close-to-EMA60 升至 `0.0588`，stock-vs-market 20d 升至 `0.0485`，这是典型的修复后加速阶段。
- `post_high_30d`：amount ratio 降至 `0.8671`，但 close-to-EMA60 仍为 `0.0873`，ATR 均值升至 `0.0538`；高点后成交收缩和波动抬升并存，说明追高阶段风险显著增加。

## 8. Sequence dominance 发现

### 8.1 全样本序列结果

| sequence_id                      | sequence_family                         |   winner_count |   control_count |   winner_sequence_rate |   control_sequence_rate |   lift |   absolute_rate_difference |   train_lift |   validation_lift |   robustness_lift | split_stability               | claim_status                           |
|:---------------------------------|:----------------------------------------|---------------:|----------------:|-----------------------:|------------------------:|-------:|---------------------------:|-------------:|------------------:|------------------:|:------------------------------|:---------------------------------------|
| S4_contraction_expansion_v0      | S4_contraction_to_expansion             |           2482 |           12094 |                 0.9210 |                  0.9086 | 1.0136 |                     0.0124 |       1.0083 |            1.0702 |            0.9917 | not_stable_or_sample_blocked  | no_claim                               |
| S5_money_no_distribution_v0      | S5_money_expansion_without_distribution |           2482 |           12094 |                 0.9919 |                  0.9941 | 0.9978 |                    -0.0022 |       0.9946 |            1.0024 |            1.0005 | not_stable_or_sample_blocked  | no_claim                               |
| S3_repair_rank_persistence_v0    | S3_repair_to_rank_persistence           |           2482 |           12094 |                 0.5790 |                  0.1617 | 3.5798 |                     0.4172 |       3.7845 |            3.0878 |            3.7007 | same_positive_sign_all_splits | sequence_supported_universal_candidate |
| S6_continuation_discriminator_v0 | S6_continuation_discriminator           |           2482 |           12094 |                 0.7973 |                  0.3865 | 2.0631 |                     0.4109 |       2.2857 |            2.0184 |            1.8025 | same_positive_sign_all_splits | sequence_supported_universal_candidate |
| S2_repair_money_vwap_v0          | S2_repair_to_money_confirmation         |           2482 |           12094 |                 0.8755 |                  0.7710 | 1.1356 |                     0.1045 |       1.1619 |            1.1966 |            1.0609 | same_positive_sign_all_splits | sequence_supported_universal_candidate |
| S1_context_to_repair_v0          | S1_context_to_repair                    |           2482 |           12094 |                 0.9500 |                  0.8810 | 1.0783 |                     0.0690 |       1.1084 |            1.0963 |            1.0210 | same_positive_sign_all_splits | sequence_supported_universal_candidate |

### 8.2 达到 universal support 的序列

| sequence_id                      |   winner_sequence_rate |   control_sequence_rate |   lift |   absolute_rate_difference |   train_lift |   validation_lift |   robustness_lift |
|:---------------------------------|-----------------------:|------------------------:|-------:|---------------------------:|-------------:|------------------:|------------------:|
| S1_context_to_repair_v0          |                 0.9500 |                  0.8810 | 1.0783 |                     0.0690 |       1.1084 |            1.0963 |            1.0210 |
| S2_repair_money_vwap_v0          |                 0.8755 |                  0.7710 | 1.1356 |                     0.1045 |       1.1619 |            1.1966 |            1.0609 |
| S3_repair_rank_persistence_v0    |                 0.5790 |                  0.1617 | 3.5798 |                     0.4172 |       3.7845 |            3.0878 |            3.7007 |
| S6_continuation_discriminator_v0 |                 0.7973 |                  0.3865 | 2.0631 |                     0.4109 |       2.2857 |            2.0184 |            1.8025 |

4 个序列达到 universal candidate：

- `S1_context_to_repair_v0`：winner sequence rate `0.9500`，control `0.8810`，lift `1.08`，绝对差 `6.90pp`。这是基础 repair context，不是最强 discriminant，但跨 split 同向。
- `S2_repair_money_vwap_v0`：winner `0.8755`，control `0.7710`，lift `1.14`，差 `10.45pp`。量价/VWAP 确认带来更强区分度。
- `S3_repair_rank_persistence_v0`：winner `0.5790`，control `0.1617`，lift `3.58`，差 `41.72pp`。这是最强的 repair persistence 结构，也是后续 04 应优先转化为候选事件族的机制。
- `S6_continuation_discriminator_v0`：winner `0.7973`，control `0.3865`，lift `2.06`，差 `41.09pp`。这说明修复后的延续性确认对区分 winner/control 很关键。

`S4_contraction_expansion_v0` 和 `S5_money_no_distribution_v0` 没有成为 headline claim。S5 的 winner/control 发生率都接近 1，信息量不足；S4 的总体 lift 只有 `1.01`，split 稳定性也不足。

### 8.3 Validation readout 中的序列表现

| feature_or_sequence                     |   winner_count |   control_count |   effect |   lift |   absolute_rate_difference | claim_status                          |
|:----------------------------------------|---------------:|----------------:|---------:|-------:|---------------------------:|:--------------------------------------|
| S1_context_to_repair                    |            443 |            2186 |   0.0858 | 1.0963 |                     0.0858 | sequence_regime_conditional_candidate |
| S2_repair_to_money_confirmation         |            443 |            2186 |   0.1498 | 1.1966 |                     0.1498 | sequence_regime_conditional_candidate |
| S3_repair_to_rank_persistence           |            443 |            2186 |   0.4823 | 3.0878 |                     0.4823 | sequence_regime_conditional_candidate |
| S4_contraction_to_expansion             |            443 |            2186 |   0.0594 | 1.0702 |                     0.0594 | sequence_regime_conditional_candidate |
| S5_money_expansion_without_distribution |            443 |            2186 |   0.0023 | 1.0024 |                     0.0023 | no_claim                              |
| S6_continuation_discriminator           |            443 |            2186 |   0.4226 | 2.0184 |                     0.4226 | sequence_regime_conditional_candidate |

Validation split 中，`S3` 和 `S6` 仍然强：`S3` lift `3.09`，绝对差 `48.23pp`；`S6` lift `2.02`，绝对差 `42.26pp`。这两个序列不是只在 train 中有效。

## 9. Factor / path readout 发现

### 9.1 Claim count 汇总

| metric                                 |   count |
|:---------------------------------------|--------:|
| sequence_supported_universal_candidate |       4 |
| sequence_regime_conditional_candidate  |     207 |
| sequence_no_claim                      |     141 |
| factor_effect_size_candidate           |    6221 |
| factor_no_claim                        |    7199 |
| validation_factor_candidates           |      90 |
| validation_sequence_candidates         |       5 |

### 9.2 Validation factor candidates（按绝对 effect 排序）

| feature_or_sequence        | shared_axis       |   winner_count |   control_count |   effect | claim_status          |
|:---------------------------|:------------------|---------------:|----------------:|---------:|:----------------------|
| max_runup_axis_to_plus_60d | shared_axis_low   |            443 |            2186 |   1.7175 | effect_size_candidate |
| return_60d                 | shared_axis_low   |            443 |            2186 |   1.4729 | effect_size_candidate |
| ema60_slope_20d            | shared_axis_low   |            443 |            2186 |   1.3892 | effect_size_candidate |
| ema60_slope_20d            | shared_axis_ema60 |            429 |            2138 |   1.1627 | effect_size_candidate |
| return_20d                 | shared_axis_low   |            443 |            2186 |   1.1373 | effect_size_candidate |
| return_60d                 | shared_axis_ema60 |            429 |            2138 |   1.1028 | effect_size_candidate |
| stock_vs_market_20d        | shared_axis_low   |            443 |            2186 |   1.0967 | effect_size_candidate |
| max_runup_axis_to_plus_20d | shared_axis_low   |            443 |            2186 |   1.0893 | effect_size_candidate |
| atr_20_pct                 | shared_axis_low   |            443 |            2186 |   0.9936 | effect_size_candidate |
| ema20_slope_20d            | shared_axis_ema60 |            429 |            2138 |   0.9482 | effect_size_candidate |
| stock_vs_market_20d        | shared_axis_ema60 |            429 |            2138 |   0.9348 | effect_size_candidate |
| close_to_ema60             | shared_axis_ema60 |            429 |            2138 |   0.8916 | effect_size_candidate |

Factor readout 的主要含义不是“单因子可交易信号”，而是验证生命周期路径是否可观察。Validation 中最强的 effect 多集中在 low 后 20/60 日的 runup、return、EMA60 slope、相对强度与 ATR：

- `max_runup_axis_to_plus_60d` effect `1.72`；这是 target episode 定义附近的路径强度，不应用作前视交易信号。
- `return_60d`、`ema60_slope_20d`、`return_20d` 在 low 后窗口显著区分 winner/control，说明真正的 winner 在修复后具备持续趋势和斜率改善。
- day-0 的多数基础形态并非强 claim；这与反向生命周期框架一致：单个低点快照不足以解释 big winner，后续修复序列和路径确认更重要。

### 9.3 Market regime dominance diagnostic

| dominance_id                                                  | factor_family   | feature              | bucket                        | shared_axis     |   relative_day |   winner_count |   control_count |   winner_total |   control_total |   winner_rate |   control_rate |     lift |   odds_ratio |   absolute_rate_difference | claim_status   | multiple_test_family   |
|:--------------------------------------------------------------|:----------------|:---------------------|:------------------------------|:----------------|---------------:|---------------:|----------------:|---------------:|----------------:|--------------:|---------------:|---------:|-------------:|---------------------------:|:---------------|:-----------------------|
| shared_axis_low_0_market_regime_risk_on                       | market_regime   | market_regime_bucket | risk_on                       | shared_axis_low |              0 |            423 |            1974 |           2482 |           12094 |        0.1704 |         0.1632 |   1.0441 |       1.0540 |                     0.0072 | diagnostic     | market_regime          |
| shared_axis_low_0_market_regime_risk_off                      | market_regime   | market_regime_bucket | risk_off                      | shared_axis_low |              0 |           1577 |            7776 |           2482 |           12094 |        0.6354 |         0.6430 |   0.9882 |       0.9675 |                    -0.0076 | diagnostic     | market_regime          |
| shared_axis_low_0_market_regime_transition                    | market_regime   | market_regime_bucket | transition                    | shared_axis_low |              0 |            482 |            2344 |           2482 |           12094 |        0.1942 |         0.1938 |   1.0020 |       1.0031 |                     0.0004 | diagnostic     | market_regime          |
| shared_axis_low_0_market_regime_missing_insufficient_lookback | market_regime   | market_regime_bucket | missing_insufficient_lookback | shared_axis_low |              0 |              0 |               0 |           2482 |           12094 |        0.0000 |         0.0000 | nan      |       4.8719 |                     0.0000 | diagnostic     | market_regime          |

市场状态本身在 matched winner/control 中差异很小：risk_off winner rate 与 control rate 分别为 `0.6354` 和 `0.6430`，risk_on 为 `0.1704` 和 `0.1632`。这说明 regime 是 episode density 的重要分母解释变量，但在 matched comparison 内并不是唯一解释。换句话说，risk_off 产生更多机会，但 winner/control 区分仍需要 sequence/path 结构。

## 10. Near-winner 与 false-repair 诊断

### 10.1 Near-winner control

| split      |   winner_count |   near_winner_control_count |   winner_mfe_120_mean |   near_winner_mfe_120_mean |
|:-----------|---------------:|----------------------------:|----------------------:|---------------------------:|
| all        |           2493 |                        6619 |                0.8319 |                     0.4044 |
| train      |           1290 |                        3304 |                0.8292 |                     0.4080 |
| validation |            445 |                         943 |                0.7433 |                     0.4044 |
| robustness |            758 |                        2372 |                0.8884 |                     0.3993 |

Near-winner controls 的平均 MFE 为 `0.4044`，明显低于 winner 的 `0.8319`。这说明 winner 与近似上涨样本之间仍有显著距离，不只是阈值从 49% 到 50% 的边界问题。

S3/S6 与 near-winner 的对比尤其有价值：

| sequence_id                      |   winner_sequence_rate |   near_winner_sequence_rate |   lift |   absolute_rate_difference |
|:---------------------------------|-----------------------:|----------------------------:|-------:|---------------------------:|
| S1_context_to_repair_v0          |                 0.9500 |                      0.9340 | 1.0172 |                     0.0161 |
| S2_repair_money_vwap_v0          |                 0.8755 |                      0.8326 | 1.0515 |                     0.0429 |
| S3_repair_rank_persistence_v0    |                 0.5790 |                      0.2126 | 2.7237 |                     0.3664 |
| S4_contraction_expansion_v0      |                 0.9210 |                      0.9095 | 1.0127 |                     0.0115 |
| S5_money_no_distribution_v0      |                 0.9919 |                      0.9958 | 0.9962 |                    -0.0038 |
| S6_continuation_discriminator_v0 |                 0.7973 |                      0.6075 | 1.3125 |                     0.1898 |

`S3` 对 near-winner 的全样本 lift 为 `2.72`，差 `36.64pp`；它不仅能区分普通 controls，也能区分已经有 30%-50% MFE 的 near-winners。

### 10.2 False repair control

| split      |   control_count |   false_repair_count |   false_repair_rate |   drawdown_anchor_to_plus_10d_mean |   drawdown_anchor_to_plus_20d_mean |   runup_axis_low_to_anchor_plus_20d_mean |
|:-----------|----------------:|---------------------:|--------------------:|-----------------------------------:|-----------------------------------:|-----------------------------------------:|
| all        |           11902 |                 8421 |              0.7075 |                            -0.0606 |                            -0.0774 |                                   0.2122 |
| train      |            6160 |                 4687 |              0.7609 |                            -0.0638 |                            -0.0830 |                                   0.1929 |
| validation |            2138 |                 1473 |              0.6890 |                            -0.0628 |                            -0.0815 |                                   0.2197 |
| robustness |            3604 |                 2261 |              0.6274 |                            -0.0539 |                            -0.0656 |                                   0.2409 |

EMA60 repair-looking controls 中，false repair rate 全样本为 `0.7075`。这说明“出现修复形态”本身远远不够；大量 controls 也会出现 repair，但后续失败。后续 04 需要特别利用 `S3` 和 `S6` 这种 persistence / continuation discriminator，而不是只用“首次修复”作为事件。

## 11. 02 rule invariant audit

| rule_family        | rule_name                 | 02_value                                                                                                                                                                                                                                                                                                                                                                                                                            | 06_value                                                                                                                                                                                                                                                                                                                                                                                                                            | allowed_difference   | status             | blocking   | notes                               |
|:-------------------|:--------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------|:-------------------|:-----------|:------------------------------------|
| episode_extraction | episode_extraction        | {"big_winner_mfe_threshold": 0.5, "forward_horizon_sessions": 120, "local_low_window_sessions": 20, "near_winner_lower_mfe_threshold": 0.3, "near_winner_upper_mfe_threshold": 0.5, "post_high_exhaustion_sessions": 30, "prior_lookback_sessions": 250}                                                                                                                                                                            | {"big_winner_mfe_threshold": 0.5, "forward_horizon_sessions": 120, "local_low_window_sessions": 20, "near_winner_lower_mfe_threshold": 0.3, "near_winner_upper_mfe_threshold": 0.5, "post_high_exhaustion_sessions": 30, "prior_lookback_sessions": 250}                                                                                                                                                                            | False                | pass               | True       | nan                                 |
| splits             | splits                    | {"robustness_start": "2024-01-01", "train_end": "2021-12-31", "train_start": "2017-01-03", "validation_end": "2023-12-31", "validation_start": "2022-01-01"}                                                                                                                                                                                                                                                                        | {"robustness_start": "2024-01-01", "train_end": "2021-12-31", "train_start": "2017-01-03", "validation_end": "2023-12-31", "validation_start": "2022-01-01"}                                                                                                                                                                                                                                                                        | False                | pass               | True       | nan                                 |
| alignment          | alignment                 | {"anchor_factor_relative_days": [-20, 0, 20, 60], "anchor_family": "first_ema60_reclaim", "anchor_panel_end_relative_day": 60, "anchor_panel_start_relative_day": -60, "ema60_window_sessions": 60, "factor_relative_days": [0, 5, 20, 60, 120], "low_panel_end_relative_day": 120, "low_panel_start_relative_day": -60}                                                                                                            | {"anchor_factor_relative_days": [-20, 0, 20, 60], "anchor_family": "first_ema60_reclaim", "anchor_panel_end_relative_day": 60, "anchor_panel_start_relative_day": -60, "ema60_window_sessions": 60, "factor_relative_days": [0, 5, 20, 60, 120], "low_panel_end_relative_day": 120, "low_panel_start_relative_day": -60}                                                                                                            | False                | pass               | True       | nan                                 |
| matching           | matching                  | {"match_fields": ["board_bucket", "market_cap_bucket", "liquidity_bucket", "prior_return_20d_bucket", "prior_return_60d_bucket", "prior_drawdown_bucket", "volatility_bucket"], "max_controls_per_winner": 5, "same_week_required": true}                                                                                                                                                                                           | {"match_fields": ["board_bucket", "market_cap_bucket", "liquidity_bucket", "prior_return_20d_bucket", "prior_return_60d_bucket", "prior_drawdown_bucket", "volatility_bucket"], "max_controls_per_winner": 5, "same_week_required": true}                                                                                                                                                                                           | False                | pass               | True       | nan                                 |
| dominance          | sample_and_claim_gates    | {"absolute_rate_difference_gate": 0.05, "lift_gate": 1.25, "min_anchor_occurrences_for_claim": 50, "min_average_controls_per_winner": 3.0, "min_control_match_coverage": 0.8, "min_feature_non_missing_coverage_for_claim": 0.7, "min_robustness_winner_episodes": 30, "min_sequence_occurrences_for_claim": 50, "min_total_winner_episodes": 150, "min_validation_winner_episodes": 30, "standardized_mean_difference_gate": 0.25} | {"absolute_rate_difference_gate": 0.05, "lift_gate": 1.25, "min_anchor_occurrences_for_claim": 50, "min_average_controls_per_winner": 3.0, "min_control_match_coverage": 0.8, "min_feature_non_missing_coverage_for_claim": 0.7, "min_robustness_winner_episodes": 30, "min_sequence_occurrences_for_claim": 50, "min_total_winner_episodes": 150, "min_validation_winner_episodes": 30, "standardized_mean_difference_gate": 0.25} | False                | pass               | True       | nan                                 |
| industry           | industry_status           | {"caveat": "No PIT industry membership file is present in the v0 data layer.", "status": "unavailable"}                                                                                                                                                                                                                                                                                                                             | {"caveat": "No PIT industry membership file is present in the v0 data layer.", "status": "unavailable"}                                                                                                                                                                                                                                                                                                                             | False                | pass               | True       | nan                                 |
| universe           | target_universe_input     | "data/processed/universe/pit_largecap_main_chinext_executable_daily.csv"                                                                                                                                                                                                                                                                                                                                                            | "data/processed/universe/pit_topn_400_100_executable_daily.csv"                                                                                                                                                                                                                                                                                                                                                                     | True                 | allowed_difference | True       | Controlled 06 universe replacement. |
| universe           | universe_precision_status | "exact fixed-cap universe from 02 contract"                                                                                                                                                                                                                                                                                                                                                                                         | "available_source_topn_candidate_gap"                                                                                                                                                                                                                                                                                                                                                                                               | True                 | allowed_difference | False      | 06-specific exact/proxy caveat.     |

审计结果显示：episode extraction、split、alignment、matching、dominance gate、industry 状态均为 `pass`。唯一允许差异是：

1. target universe input 从 02 的 fixed-cap executable universe 替换为 05 的 PIT Top-N 400/100 executable universe/proxy；
2. universe precision metadata 从 02 的 fixed-cap 语义替换为 `available_source_topn_candidate_gap`。

这意味着 06 可以作为 02 的 universe-only 科学对照，而不是一个重新调参后的新实验。

## 12. 结论与后续 04 handoff

本次 06 rerun 支持以下结论：

1. PIT Top-N/proxy universe 下 big-winner denominator 明显扩大，episode count 从 02 的 `866` 增至 `2,493`。
2. Top-N/proxy 的 episode density 为 `68.82` / 100 universe-years；该数字必须绑定 `available_source_topn_candidate_gap` caveat。
3. Sequence-level 结论保持稳定，最终 decision 为 `topn_reverse_lifecycle_sequence_supported_universal_dominance`。
4. 最可转化为 04 candidate generator 的结构不是简单 low snapshot，而是 `S3_repair_rank_persistence_v0` 与 `S6_continuation_discriminator_v0`。
5. Risk-off 和创业板是 episode density 的重点来源，但 matched comparison 显示 regime 本身不足以解释 winner/control 差异，仍需 repair sequence 和 continuation discriminator。
6. 04 不应复用旧的 `+50 bridge recall` denominator；任何 recall、precision、candidate density 都必须基于这个 06 manifest 和同一个 available-source top-N caveat 重新计算。

因此，06 可以冻结为后续 04 rerun 的新 episode denominator。冻结前需要接受一个明确限制：它不是 exact historical top 400/100，而是当前可审计数据源上的 PIT Top-N 400/100 proxy。

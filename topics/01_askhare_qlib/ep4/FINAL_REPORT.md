# EP4 Final Report: Right-Tail Episode Management Research Closure

Generated at: `2026-05-20T00:14:52.874442+08:00`

## 0. Executive Summary

EP4 的研究问题从一开始就不是“再找一个单点 alpha”，而是：在 EP2/EP3 已经暴露出 winner 稀疏、路径噪声大、事后解释强于事前可交易性的背景下，是否能把 big-winner 视作一个右尾 episode option，通过高召回 probe、证据积累、失败早停、动态 exposure、exit/risk-budget 和 sleeve allocation，形成一个可验证、可执行、可通过 OOS 的体系。

最终答案是否定的。当前终局 artifact 为 R05b，final decision = `r05b_risk_on_full_exposure_failed`，blocking reason = `risk_on_full_exposure_validation_net_not_positive`，terminal stop = `True`，allowed next = `ep5_escape_hatch_only`。这表示 EP4 不应继续在同一 evidence family / 同一 long-only A-share episode 框架里追加 R05c/R05d 细调；后续只有在研究框架发生实质改变时，才进入 EP5 escape hatch。

最核心的失败链条是：

1. R01/R02 证明了覆盖和结构解释可以做出来，但 action-time 的触发密度、LR/EV、execution feasibility 不够。
2. R03a-R03e 证明了 sequence、fresh evidence、stage role、bad-shape 都有描述价值，但没有变成稳定 entry/add/sizing edge。
3. R04-R04e 证明了 left-tail compression、relative improvement、portfolio union 都不能把 validation 变成正期望。
4. R05/R05b 证明了 standalone alpha pool 不过 preflight；R05b 的正式终止驱动是 risk-on full exposure validation 为负，allocator/right-tail/secondary gate 只提供附带证据。

因此 EP4 的价值不是找到可上线策略，而是把一条看似有很多局部证据的研究线收敛到可审计的终止条件。

## 1. Discussion Evolution

| 文件           | 核心问题                                                                        | 对实验设计的影响                                                                             |
|:---------------|:--------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| discussion.md  | EP4 从“预测大 winner”改写为“管理右尾 episode 期权”。                            | 先用 high-recall probe 找到足够覆盖，再要求 fail-fast、延迟入场和 no-harm 约束。             |
| discussion2.md | 后续信号是 evidence accumulation，不天然等于新入场点。                          | 要求 action-time prior、30D build window、LR/posterior/correlation/risk-budget 审计。        |
| discussion3.md | 同日 evidence bundle 与 survival/fresh evidence 容易产生 denominator 偏差。     | R03a 被收紧为 probability-only feasibility，禁止把 winner-anchored 覆盖直接转成 entry rule。 |
| discussion4.md | R03 后不再寻找新 anchor，而转向 dynamic exposure eligibility 与风险预算。       | R04 系列改测 exposure/regime/exit/portfolio 层能否把左尾管理转成 OOS 正期望。                |
| discussion5.md | R04e/R05 后必须区分 alpha pool、relative-improvement pool 与 sleeve allocator。 | R05b 成为 EP4 终局诊断：risk-on full exposure hard kill 先于 allocator gate。                |

这五份 discussion 的共同收敛点是：不能把 winner-anchored 观察、survival 后验、fresh-count 累积、形态解释或 portfolio 组合，直接翻译成交易规则。每一步都必须回到 action-time、next executable price、validation-first、robustness-readonly 的约束下重新验证。

## 2. Experiment Timeline

| 阶段          | 问题                                                        | 最终状态                                                    | 关键证据                                                                                   | 结论                                                                                                                           |
|:--------------|:------------------------------------------------------------|:------------------------------------------------------------|:-------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------|
| R01           | 高召回 seed + fail-fast 是否能形成可控 probe?               | stop_ep4_r01_path                                           | validation seed day rate 7.72% > cap 1.33%                                                 | 覆盖有了，但触发密度过高，不能直接进入 R02/R03 作为生产入口。                                                                  |
| R01.1         | throttle/cooling 能否修复 R01 的触发密度?                   | archive / diagnostic                                        | train emitted seed day rate 1.18%; probe entry day rate 0.79%                              | 密度可压低，但这是流量控制，不等价于 action-time alpha。                                                                       |
| R02           | evidence family discovery 能否给出稳定非 baseline family?   | archive_family_discovery_no_r03                             | hard gates failed 6 / 7                                                                    | 同日 family 组合未证明稳定 LR/EV，也不满足 execution feasible。                                                                |
| R02 V2        | winner-anchored structure profile 能否稳定外推?             | coverage/profile diagnostic only                            | R01 reference overlap 98.81%; validation LR/EV gates 均未通过                              | 可解释 winner 结构，但不能作为 action-time selection rule。                                                                    |
| R03a          | probability-survival step 是否有稳定可选 bucket?            | blocked_no_stable_candidate_bucket                          | candidate grid 180; train eligible after gate 0                                            | survival checkpoint 只能作为风险过滤诊断，不能证明独立 entry edge。                                                            |
| R03b          | fresh signal sequence 是否确认 big-winner path?             | descriptive_sequence_diagnostic_complete                    | seed episodes 11,003; fresh episodes 6,343; failed before first fresh 4,500                | fresh-count 能解释路径状态，但 survival conditioning 很重，不能直接当入场信号。                                                |
| R03c          | kth fresh / price-aware pooling 是否给出新买点?             | descriptive_price_aware_pooling_diagnostic_complete         | 高 wait-return 行 seed-anchor 强，但 fresh-anchor P_good 低、P_bad 高。                    | 后续 fresh 更像 late confirmation，不是更好的 fresh-entry alpha。                                                              |
| R03d          | family 顺序 / stage role 是否有增量?                        | stage_role_only_no_order_increment                          | prefix/order denominator 塌缩；pair-order weighted signed lift 约为 0。                    | stage role 可作为状态变量；family order 不应进入 entry/add/sizing 规则。                                                       |
| R03e          | bad-shape filter 能否剔除 family 信号后的坏路径?            | badshape_filter_no_incremental_edge                         | drop_score_ge5 在 validation/robustness 均未降低 P_bad，big-winner rate 下降。             | 形态坏分不是稳定单调风险过滤器。                                                                                               |
| R04           | RPS + market/industry regime 能否定义 exposure eligibility? | r04_v1_exposure_eligibility_audit_complete_descriptive_only | single_momentum_rps 有右尾信息，但 regime lift 受 denominator shrink 与 split 不稳定限制。 | descriptive-only，不能发 production exposure gate。                                                                            |
| R04b          | fixed-entry 后 exit/risk-budget 能否稳定提升收益?           | r04b_policy_not_robust_hold_exit_diagnostic_complete        | validation net delta vs hold_120d_no_exit +3.57%; robustness same baseline -3.05%          | 左尾可压缩，但 robustness 均值收益不稳。                                                                                       |
| R04c          | candidate pool scanner 能否找到绝对正期望池?                | r04c_no_candidate_pool_passed_validation                    | validation candidate pools 2, passed 0                                                     | relative improvement 存在，但绝对 validation net 仍为负。                                                                      |
| R04d          | volume_money 相对改善池能否经 risk-budget 转正?             | r04d_no_policy_passed_validation                            | train-selected validation pass 0 / 8                                                       | 简单风险管理压左尾，但 winner retention 与正收益门槛无法同时满足。                                                             |
| R04e          | union pool / portfolio-level replay 能否消除单池弱点?       | r04e_union_not_viable_validation                            | gate0_stop_low_quality_union；validation 最好组合仍未通过。                                | 组合层面没有把弱 alpha 拼成可用 portfolio；还有伪分散/活跃库存拥挤问题。                                                       |
| R05 Preflight | 是否存在可作为 standalone alpha pool 的候选?                | r05_preflight_stop_no_absolute_floor                        | candidate pass count 0                                                                     | 没有候选满足绝对收益/样本底线。                                                                                                |
| R05b          | cash allocator + secondary sleeve 是否能保留右尾并改善风险? | r05b_risk_on_full_exposure_failed                           | risk_on_full_exposure_validation_net_not_positive                                          | decision driver 是 risk-on full exposure validation 为负；secondary 不激活和 allocator right-tail retention 失败只是附带证据。 |

Timeline 里的 R01 `stop_ep4_r01_path` 不表示 R02-R05 可以把 R01/R01.1 当作 production entry 继续推进。R02 之后沿用的是已冻结的 evidence sampling / family signal / path-query artifacts，用于诊断 family、path、portfolio 与 allocator 问题；这些下游实验不把 R01 或 R01.1 升级为 production-grade probe。

R04 命名说明：本轮 EP4 没有单独发布 `R04a` artifact；`R04 Dynamic Momentum Exposure Eligibility Audit V1` 就是 exposure/regime 方向的首个 R04 artifact，后续扩展从 R04b 开始。

## 3. Stage Findings

### 3.1 R01/R02: Coverage Is Not Entry Quality

R01 的 high-recall 方向能覆盖一部分右尾 episode，但触发密度直接失败。在最终 R01 V3 中，validation candidate seed day rate 为 7.72%，高于 cap 1.33%。R01.1 的 throttle/cooling 可以把 emitted seed 和 probe entry rate 压到阈值内，但这只解决“太频繁触发”的工程问题，不解决“触发后是否有正期望”的研究问题。

因此，R01/R01.1 的 `stop` / `archive` 语义是禁止 promotion，而不是禁止继续做研究诊断。后续 R02-R05 使用冻结 evidence/path artifacts 来追问“这些观察是否能在更高层被救回来”，但所有报告都必须把它们视为 diagnostic inputs，而不是已经批准的 entry signal。

R02 和 R02 V2 进一步说明，family 结构和 winner-anchored profile 可以提供解释性线索，但不能通过 validation LR/EV/execution gates。R02 V2 的 R01 reference overlap 达到 98.81%，说明它确实是在解释同一类右尾对象；但 validation 中没有足够 family 通过 LR lower-bound 与 EV 门槛。

### 3.2 R03: Path Confirmation Is Not Fresh-Entry Alpha

R03b 是 EP4 中最有解释力的描述性实验之一：all split 有 11,003 个 seed episodes，其中 6,343 个出现过后续 fresh evidence，但 4,500 个在第一根 clean fresh 前已经失败。这直接揭示了 fresh evidence 的 survival conditioning：能等到后续信号本身就筛掉了大量坏路径。

R03c/R03d 把这个问题拆得更细：kth fresh、wait-return、family set、family order 和 stage role 大多是在描述 seed episode 已经走出来的状态。seed-anchor 的 P_good 可以显著改善，但从 fresh signal 之后重新计算的 fresh-anchor 机会并没有同步改善。R03d 的结论更明确：family 有阶段角色，但严格顺序没有可交易增量。

R03e 试图从反面解决问题：如果不能证明谁会成为 winner，能否至少剔除坏形态？结果也不成立。Primary `drop_score_ge5` 的结果如下：

| split      | policy                          | baseline_n   | passed_n   | P_good   | P_bad   | big_winner_rate   | delta_P_bad   | delta_big_winner   |
|:-----------|:--------------------------------|:-------------|:-----------|:---------|:--------|:------------------|:--------------|:-------------------|
| validation | no_badshape_filter_t10_survivor | 2,557        | 2,557      | 11.11%   | 86.95%  | 7.74%             | +0.00%        | +0.00%             |
| validation | drop_score_ge5                  | 2,557        | 1,994      | 11.51%   | 87.31%  | 7.10%             | +0.36%        | -0.65%             |
| robustness | no_badshape_filter_t10_survivor | 4,144        | 4,144      | 16.30%   | 82.97%  | 4.05%             | +0.00%        | +0.00%             |
| robustness | drop_score_ge5                  | 4,144        | 3,500      | 16.12%   | 83.45%  | 3.73%             | +0.48%        | -0.32%             |

validation 中 drop_score_ge5 后 P_bad 从 parent 增加 +0.36%，robustness 中也增加；同时 big-winner rate 下降。当前 BadScore V1 因此不能作为硬过滤器。

### 3.3 R04: Left-Tail Compression Did Not Become Positive Expectancy

R04 系列是 EP4 从 signal/path diagnostic 转向 exposure/portfolio 的关键阶段。R04 v1 发现 single_momentum_rps 仍含右尾信息，但 market/industry regime 带来的改善受 denominator shrink、split instability 和 background regime effect 限制，只能 descriptive-only。

R04b 显示 fixed-entry 后的 exit/risk-budget 可以显著改善 validation 左尾，selected policy validation net delta vs `hold_120d_no_exit` 为 +3.57%，但 robustness 同口径 net delta 为 -3.05%。这说明左尾管理在差 split 上看起来有效，但没有稳定提高期望收益。

R04c 的候选池扫描结果：

| pool_id                    | validation_net   | matched_delta   | p10_delta   | loss<=-5_delta   | gate_pass   |
|:---------------------------|:-----------------|:----------------|:------------|:-----------------|:------------|
| r02_precision_volume_money | -2.07%           | +4.53%          | +3.03%      | -10.84%          | False       |
| r04_rps95_industry80       | -8.17%           | -1.48%          | -3.47%      | +3.51%           | False       |

`r02_precision_volume_money` 是最有用的 relative-improvement lead：validation 相对 matched baseline 少亏，但自身 net return 仍为负。R04d 对这个池做 risk-budget replay，结果如下：

|   rank | policy_id                                                                   | validation_net   | delta_vs_hold120   | p10_delta   | retention   | failed_gate                                                                                                |
|-------:|:----------------------------------------------------------------------------|:-----------------|:-------------------|:------------|:------------|:-----------------------------------------------------------------------------------------------------------|
|      1 | hold_20d__time_stop__time_stop_days10__volatility_scaled                    | -0.58%           | +1.49%             | +18.56%     | 0.88%       | net_return_mean;net_return_mean_delta_vs_volume_money_hold120;max_gain50_retention_vs_volume_money_hold120 |
|      2 | hold_20d__fixed_stop__stop_loss_pctm0p05__volatility_scaled                 | -0.63%           | +1.45%             | +19.93%     | 6.19%       | net_return_mean;net_return_mean_delta_vs_volume_money_hold120;max_gain50_retention_vs_volume_money_hold120 |
|      3 | hold_20d__time_stop__time_stop_days10__fixed_size                           | -0.69%           | +1.38%             | +16.72%     | 0.88%       | net_return_mean;net_return_mean_delta_vs_volume_money_hold120;max_gain50_retention_vs_volume_money_hold120 |
|      4 | hold_20d__fixed_stop__stop_loss_pctm0p05__fixed_size                        | -0.63%           | +1.44%             | +18.93%     | 6.19%       | net_return_mean;net_return_mean_delta_vs_volume_money_hold120;max_gain50_retention_vs_volume_money_hold120 |
|      5 | hold_20d__break_even_after_gain__activation_gain_pct0p08__volatility_scaled | -0.89%           | +1.19%             | +15.78%     | 6.19%       | net_return_mean;net_return_mean_delta_vs_volume_money_hold120;max_gain50_retention_vs_volume_money_hold120 |
|      6 | hold_20d__no_exit__none__volatility_scaled                                  | -0.88%           | +1.19%             | +15.69%     | 6.19%       | net_return_mean;net_return_mean_delta_vs_volume_money_hold120;max_gain50_retention_vs_volume_money_hold120 |
|      7 | hold_20d__break_even_after_gain__activation_gain_pct0p08__fixed_size        | -0.96%           | +1.12%             | +13.39%     | 6.19%       | net_return_mean;net_return_mean_delta_vs_volume_money_hold120;max_gain50_retention_vs_volume_money_hold120 |
|      8 | hold_20d__no_exit__none__fixed_size                                         | -0.96%           | +1.12%             | +13.11%     | 6.19%       | net_return_mean;net_return_mean_delta_vs_volume_money_hold120;max_gain50_retention_vs_volume_money_hold120 |

R04d 的最好 validation policy 也仍为负收益，并且往往牺牲 +50 winner retention。R04e 再把多个弱池合成 union pool，并做 portfolio-level replay，仍未通过 gate0。按 validation period return 排名最高的组合如下：

| portfolio_id                              | cap   | policy_id                                                 | period_return   | monthly_p10   | max_drawdown   |   active_count_p95 |
|:------------------------------------------|:------|:----------------------------------------------------------|:----------------|:--------------|:---------------|-------------------:|
| family_balanced_active_equal_weight_cap20 | cap20 | hold_20d__break_even_after_gain__activation_gain_pct_0p15 | -11.33%         | -7.40%        | 20.00%         |                 20 |
| family_balanced_active_equal_weight_cap20 | cap20 | hold_20d__no_exit__none                                   | -11.56%         | -7.40%        | 20.03%         |                 20 |
| family_balanced_active_equal_weight_cap20 | cap20 | hold_20d__break_even_after_gain__activation_gain_pct_0p1  | -12.10%         | -7.40%        | 20.00%         |                 20 |

这三组最高排名 portfolio 均触及 cap20 active inventory 上限，`active_count_p95 = 20`。因此 portfolio 内实际库存结构高度相似，`monthly_p10` 完全一致不是数据错误，而是 cap20 风险结构主导了组合左尾，exit policy 的微调只改变了 period return 的小幅排序。

这说明 EP4 不能依赖“多个相对改善池组合后自然变成稳健 portfolio”的假设。弱信号组合会带来 active inventory、calendar clustering 和 pseudo-diversification 风险，并不会自动创造绝对正期望。

### 3.4 R05/R05b: Alpha Preflight And Sleeve Allocator Terminal Failure

R05 Preflight 对候选 alpha pool 做了冻结 event replay，结果没有任何候选通过：

| candidate                                  |   validation_events | complete_share   | hold20_mean   | hold20_median   | hold20_p10   | gate_status                        | blocking                         |
|:-------------------------------------------|--------------------:|:-----------------|:--------------|:----------------|:-------------|:-----------------------------------|:---------------------------------|
| low_vol_uptrend_preflight                  |                 574 | 96.86%           | -0.72%        | -1.36%          | -9.46%       | preflight_fail_no_absolute_floor   | validation_absolute_floor_failed |
| base_breakout_vcp_preflight                |                  73 | 95.89%           | +1.00%        | -1.47%          | -7.61%       | preflight_fail_insufficient_sample | validation_event_count_below_min |
| cross_sectional_low_beta_low_vol_preflight |                 810 | 96.05%           | -1.52%        | -1.83%          | -9.24%       | preflight_fail_no_absolute_floor   | validation_absolute_floor_failed |

`base_breakout_vcp` 是唯一 validation hold20 mean 为正的候选，但 validation events 只有 73，触发 insufficient sample。`low_vol_uptrend` 和 `cross_sectional_low_beta_low_vol` 样本更大，但 validation hold20 mean 均为负，触发 absolute floor failure。

`base_breakout_vcp` 的 validation hold20 mean 为 +1.00%，但 median 为 -1.47%，两者同时为真：73 个 events 的正均值主要来自少数右尾样本，而多数样本仍亏损。因此 sample-insufficient gate 的阻断是正确决定，不能把它读成“已有可用 alpha”。

R05b decision precedence 中，risk-on full exposure hard kill 先于 allocator gate / mostly-cash / no-policy-pass。因此只要该 hard kill 触发，final decision 就必须是 `r05b_risk_on_full_exposure_failed`；后续 allocator gate 数据只能作为附带证据，说明即使绕过 hard kill，selectable allocator 也没有 pass。

R05b 首先检查 risk-on full exposure 自身是否在 validation 为正：

| split      | risk_on_share   | full_exposure_return   | risk_on_full_exposure_return   | risk_on_daily_mean   | gate   | blocking                           |
|:-----------|:----------------|:-----------------------|:-------------------------------|:---------------------|:-------|:-----------------------------------|
| train      | 36.74%          | +39.89%                | +18.50%                        | +0.05%               | pass   |                                    |
| validation | 21.49%          | -22.81%                | -7.91%                         | -0.07%               | fail   | risk_on_full_exposure_not_positive |
| robustness | 42.68%          | +37.09%                | +17.88%                        | +0.08%               | pass   |                                    |

validation risk-on full exposure return 为 -7.91%，daily mean 也为负。因此 R05b 在 allocator gate 之前已经触发 terminal blocker。

allocator policy 的 validation gate 进一步确认失败原因：

| policy                                           | validation_status                                | period_return   | monthly_p10_delta   | max_dd_delta   | avg_gross   | cash_only   | right_tail_retention   | right_tail_status   | blocking                                 |
|:-------------------------------------------------|:-------------------------------------------------|:----------------|:--------------------|:---------------|:------------|:------------|:-----------------------|:--------------------|:-----------------------------------------|
| full_exposure_primary_baseline                   | baseline_reference_only                          | -22.81%         | +0.00%              | +0.00%         | 100.00%     | 0.00%       | 1.000 (=100.0%)        | right_tail_pass     |                                          |
| market_state_cash_allocator_v1                   | validation_fail                                  | -14.68%         | +2.26%              | +9.64%         | 46.18%      | 29.13%      | 0.462 (=46.2%)         | right_tail_fail     | validation_gate_condition_failed         |
| market_state_cash_plus_basebreakout_secondary_v1 | blocked_secondary_sleeve_insufficient_activation | -14.68%         | +2.26%              | +9.64%         | 46.18%      | 29.13%      | 0.462 (=46.2%)         | right_tail_fail     | secondary_sleeve_insufficient_activation |

`market_state_cash_allocator_v1` 的 validation return 虽然从 full exposure 的 -22.81% 改善到 -14.68%，也降低了 max drawdown，但 right-tail retention ratio 只有 0.462 (=46.2%)，低于 0.600 gate。`market_state_cash_plus_basebreakout_secondary_v1` 没有带来增量，因为 secondary sleeve validation 激活不足，实际表现与 cash allocator 相同。

## 4. Why EP4 Failed

| 失败层       | 症状                                                                                                                       | 证据                                                                                              |
|:-------------|:---------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------|
| 入口覆盖层   | high-recall seed 可以覆盖右尾，但密度过高；throttle 只修流量，不修期望。                                                   | R01 seed density hard gate failed；R01.1 density pass 但 archive。                                |
| 证据层       | family/fresh/sequence 解释路径状态，但不是稳定 action-time entry edge。                                                    | R03b fresh survival conditioning；R03c seed-anchor 强、fresh-anchor 弱；R03d order no increment。 |
| 过滤层       | bad-shape 不能稳定剔除坏路径，且会损失 winner。                                                                            | R03e drop_score_ge5 未降低 P_bad，big-winner rate 下降。                                          |
| 风险管理层   | exit/sizing 能压左尾，但不能稳定提高 OOS 均值。                                                                            | R04b validation vs hold_120d_no_exit +3.57% net delta，但 robustness 同口径 -3.05%。              |
| 候选池层     | relative improvement pool 仍不是 absolute positive pool。                                                                  | R04c volume_money validation net -2.07%；R04d best policy validation net 仍负。                   |
| 组合层       | union portfolio 不能把弱 alpha 拼成可用组合，反而暴露伪分散和库存拥挤。                                                    | R04e final `r04e_union_not_viable_validation`，gate0 stop。                                       |
| allocator 层 | 正式 hard kill 是 risk-on full exposure 本身 validation 为负；cash allocator 降风险但砍掉右尾，secondary sleeve 也未激活。 | R05b risk-on validation -7.91%；allocator right-tail retention ratio 0.462 (=46.2%)。             |

关键不是某个局部公式失败，而是整条链条每次试图把“描述性改进”升级成“可交易规则”时，都会在 validation-first 的硬约束下被打回。这个模式出现了多次，因此终止不是过早，而是必要。

## 5. Lessons Learned

| lesson                                                            | detail                                                                                                                            |
|:------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------|
| 1. 覆盖率不是 alpha。                                             | 高召回能让研究有样本，但触发太密时，任何后续筛选都可能只是流量管理。必须先看 action-time base rate、密度和执行可行性。            |
| 2. Winner-anchored 解释不能替代 entry-time prior。                | 很多结构在 winner 回看中很漂亮，但一旦回到当时可观察信息，LR/EV 和 sample sufficiency 就消失。                                    |
| 3. Survival conditioning 是最大陷阱。                             | 等到 T+10、等到 kth fresh、等到 price 已经上涨，本身就在筛掉失败路径。必须把 seed-anchor 与 fresh-anchor 分开。                   |
| 4. Fresh evidence 更适合作为持仓状态变量。                        | R03b/R03c/R03d 都支持 fresh/sequence/stage role 的解释价值，但不支持把它们当作新入场或加仓规则。                                  |
| 5. Bad-shape filter 不能凭直觉上线。                              | 如果分数桶不单调、drop policy 不降低 P_bad，就算形态描述合理，也不能成为硬风控。                                                  |
| 6. 左尾改善不等于策略通过。                                       | R04b/R04d 多次证明可以少亏，但少亏必须同时保留右尾并把 validation net 变成正数，否则只能 diagnostic-only。                        |
| 7. Robustness 不能拯救 validation。                               | EP4 多个实验 robustness 看起来更好，但设计上 robustness 是 readonly final readout，不能反过来选择或救活 validation 失败项。       |
| 8. 组合不是弱信号的免费午餐。                                     | union pool 如果没有独立的正期望和低相关暴露，只会把同一类拥挤库存摊开到更多日子和更多股票。                                       |
| 9. Alpha pool、relative-improvement pool、sleeve 是三种不同对象。 | R04c/R04d 的 relative improvement 不能直接宣称是 alpha；R05b 的 sleeve 也必须单独检查激活、gross exposure、right-tail retention。 |
| 10. 好的终止规则本身是研究产出。                                  | EP4 最有价值的不是上线策略，而是把“还能再调一下”的空间压缩成可审计的 stop 条件，避免继续在同一假设族上消耗实验预算。              |

## 6. Final Decision And EP5 Boundary

- EP4 terminal decision: `r05b_risk_on_full_exposure_failed`
- Terminal blocker: `risk_on_full_exposure_validation_net_not_positive`
- Selected allocator: `None`
- Allowed next requirement: `ep5_escape_hatch_only`

EP4 后不建议继续做以下事情：

- 不建议在同一 R02/R03 family set 上再做 R05c/R05d 参数微调。
- 不建议把 R04d 的 volume_money relative improvement 包装成 alpha pool。
- 不建议用 robustness 正收益反推 validation 失败可忽略。
- 不建议把 cash allocator 的回撤改善当作通过，因为它未保留足够右尾。

EP5 只有在问题定义发生实质变化时才值得启动，例如：

- 改变交易对象或样本宇宙，而不是在同一 EP4 universe 内继续筛。
- 改变持有 horizon / execution framing，并重新冻结 as-of 与 next-open 合约。
- 引入对冲腿、market-neutral framing 或 explicit risk overlay，而不是 long-only cash timing。
- 从“寻找 big winner episode”切换到完全不同的 loss-avoidance / relative-value / regime allocation 问题。

## 7. Source Artifact Index

| 用途                        | 路径                                                                                                                              |
|:----------------------------|:----------------------------------------------------------------------------------------------------------------------------------|
| 讨论主线                    | ep4/discussion.md ... ep4/discussion5.md                                                                                          |
| R01 seed/probe              | ep4/outputs/r01_high_recall_probe_fail_fast_v3_post30_profile_seed/                                                               |
| R02/R02.1 priors            | ep4/outputs/r02_evidence_family_discovery_v1/; ep4/outputs/r02_1_prior_probability_diagnostic_v1/                                 |
| R03a-R03e path diagnostics  | ep4/outputs/r03a_* ... ep4/outputs/r03e_*                                                                                         |
| R04-R04e exposure/portfolio | ep4/outputs/r04_dynamic_* ... ep4/outputs/r04e_union_pool_portfolio_level_diagnostic_v1/                                          |
| R05/R05b terminal           | ep4/outputs/r05_preflight_alpha_pool_quick_feasibility_v1/; ep4/outputs/r05b_sleeve_allocator_exposure_composition_diagnostic_v1/ |

本报告只读取上述已生成 artifact，没有重新运行任何实验，也没有改变任何 requirement 或 runner。

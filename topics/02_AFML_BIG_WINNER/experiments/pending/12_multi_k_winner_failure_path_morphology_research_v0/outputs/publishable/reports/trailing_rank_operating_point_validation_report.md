# 12A7 Direction A trailing-rank operating point audit 报告

## 1. 结论

12A7 的最终状态是 `12A7_simple_backbone_supported_complex_model_not_supported`。

这不是 `no_rank_transport`：两个 stage 的 score 在 robustness 仍有可观排序能力。Stage-1 robustness AUC 为 `0.7218`，Spearman rank-IC 为 `0.3540`；stage-2 robustness AUC 为 `0.6041`，rank-IC 为 `0.1183`。但 headline gate 要求复杂模型在 PIT trailing-rank operating rule 下同时打赢 same-budget random 和 train-frozen single-feature challenger。复杂模型在 stage-1 赢了 random，却显著输给单特征低波动 backbone，因此不能升级为 supported。

核心判断：

| item | value |
|---|---:|
| final decision | `12A7_simple_backbone_supported_complex_model_not_supported` |
| input / PIT gate | `pass` |
| score reproduction | `pass_near_miss` |
| stage-1 status | `rank_signal_or_partial` |
| stage-2 status | `failed` |
| failure reason | `stage1_support_gate_failed` |
| recommended follow-up | `12A7b_simple_backbone_operating_rule_validation` |

一句话解释：12A7 证明了 rank 迁移比 12A6c 的 frozen absolute threshold 更合理，但也证明了当前复杂模型没有超过一个很便宜的防御型单特征规则。下一步不应直接做概率校准或更复杂的两阶段模型，而应先把 simple backbone 作为主基准，把复杂模型降维、单调化，再看是否能稳定超过它。

## 2. 数据和可复现边界

本次报告只使用已生成的 12A7 publishable tables 和 manifest，不重新跑代码。

| audit | result |
|---|---:|
| input artifacts | 26 / 26 pass |
| schema checks | 26 / 26 pass |
| split boundary | validation / robustness 均 pass |
| random seeds | 100 |
| random sampled rows | 1,511,300 |
| random path cache matched rows | 1,511,300 |
| random stage-2 cache matched rows | 1,511,300 |
| random no-fast-fail rows | 1,014,118 |
| random stage-2 positives | 189,395 |
| random merge key uniqueness | `pass` |

Score reproduction 的纪律基本可接受：stage-1 是 exact reproduction；stage-2 是 numerical near miss。Stage-2 refit threshold 差异为 `0.000529`，robustness selected_n 从 12A6c reference 的 `882` 变成 reproduced 的 `914`，target-rate 差异只有 `0.000444`。因此它影响的是 reproduction status，而不是本次 trailing-rank 结论的方向。

## 3. Operating rule

Headline policy：

```text
history_policy_id = board_then_global_rolling_504_sessions
history_window_mode = rolling_sessions
trailing_history_window_sessions = 504
stage1_budget_X = 0.50
stage2_budget_X = 0.50
```

规则含义是：当前事件只和当前 decision position 之前、504 session 窗口内的历史事件比较；同 board history 不足时回退到 global history。`rank_not_evaluable` 不可被选中，但仍保留在 total denominator 中，所以预算不是 by construction 等于 50%，而是一个必须审计的部署结果。

## 4. Rank quality

Score 的 rank signal 是存在的，尤其 stage-1 很强，stage-2 较弱但不是噪声。

| stage | split | event_n | positive_n | base_rate | AUC | rank_IC | decile_lift | tail_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| stage-1 | train | 8,303 | 3,476 | 0.4186 | 0.7383 | 0.4072 | 0.6823 | 0.7593 |
| stage-1 | validation | 2,151 | 731 | 0.3398 | 0.6942 | 0.3186 | 0.5260 | 0.6186 |
| stage-1 | robustness | 4,659 | 1,425 | 0.3059 | 0.7218 | 0.3540 | 0.5258 | 0.6288 |
| stage-2 | train | 3,107 | 471 | 0.1516 | 0.6950 | 0.2423 | 0.2797 | 0.3151 |
| stage-2 | validation | 1,292 | 101 | 0.0782 | 0.6133 | 0.1053 | 0.0923 | 0.1231 |
| stage-2 | robustness | 2,786 | 342 | 0.1228 | 0.6041 | 0.1183 | 0.1398 | 0.2079 |

Robustness decile 也支持这个判断。Stage-1 score decile 1 的 fast-fail rate 只有 `0.1030`，decile 10 达到 `0.6288`。Stage-2 decile 1 continuation rate 为 `0.0681`，decile 10 为 `0.2079`。Stage-2 中间 decile 不完全单调，特别是 decile 9 回落到 `0.1223`，说明 stage-2 排序有尾部信号，但稳定性弱于 stage-1。

## 5. Headline primary tuple

### 5.1 Stage-1: 复杂模型赢 random，但输 single-feature

Stage-1 的目标是降低 fast-fail rate，越低越好。Robustness 上复杂模型相对 same-budget random 有明确改善：`0.1965` vs random p50 `0.2339`，差值 `-0.0374`，nested random bootstrap CI 为 `[-0.0528, -0.0215]`。这说明 rank-based operating point 确实修复了 12A6c 中最明显的 random-50 可比性问题。

但复杂模型没有超过 train-frozen single-feature challenger。单特征是 `volatility_60d asc`，即低 60 日波动率优先保留。它在完全相同 selected_n / common denominator 下的 robustness fast-fail rate 是 `0.1788`，比复杂模型的 `0.1965` 更低。模型减 single-feature 的差值为 `+0.0177`，paired event bootstrap CI 为 `[+0.0065, +0.0290]`，方向明确。

| split | denom | rank_eval | selected | budget_total | budget_rank_eval | base | model_rate | random_p50 | delta_random | single_rate | delta_single |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 8,303 | 8,050 | 3,979 | 0.4792 | 0.4943 | 0.4112 | 0.2566 | 0.3228 | -0.0662 | 0.2636 | -0.0070 |
| validation | 2,151 | 2,133 | 1,681 | 0.7815 | 0.7881 | 0.3366 | 0.2802 | 0.3006 | -0.0204 | 0.2772 | +0.0030 |
| robustness | 4,659 | 4,642 | 2,427 | 0.5209 | 0.5228 | 0.3053 | 0.1965 | 0.2339 | -0.0374 | 0.1788 | +0.0177 |

Interpretation：stage-1 不是没有 alpha，而是复杂模型的防御信息没有超过低波动这个便宜 backbone。当前 gate 的失败是合理的：random 只是最低线，single-feature 才是这一类 rejector 的真实机会成本。

### 5.2 Stage-2: 有 random uplift，但 single-feature 证据不足

Stage-2 的目标是提高 continuation rate，越高越好。Robustness headline 下复杂模型 continuation rate 为 `0.1340`，random p50 为 `0.1067`，差值 `+0.0273`，nested random bootstrap CI 为 `[+0.0056, +0.0517]`。这说明 stage-2 模型在 model-kept survivor 条件下确实超过 random。

但 single-feature challenger 是 `distance_to_120d_low desc`，robustness rate 为 `0.1241`。复杂模型只高 `+0.0099`，paired event bootstrap CI 为 `[-0.0094, +0.0280]`，跨 0。这个结果不足以证明复杂模型超过简单 backbone。

| split | denom | rank_eval | selected | budget_total | budget_rank_eval | base | model_rate | random_p50 | delta_random | single_rate | delta_single |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 2,958 | 2,867 | 1,427 | 0.4824 | 0.4977 | 0.1507 | 0.2221 | 0.1790 | +0.0432 | 0.2123 | +0.0098 |
| validation | 1,210 | 1,197 | 497 | 0.4107 | 0.4152 | 0.0777 | 0.1026 | 0.0646 | +0.0380 | 0.0905 | +0.0121 |
| robustness | 1,950 | 1,944 | 806 | 0.4133 | 0.4146 | 0.1034 | 0.1340 | 0.1067 | +0.0273 | 0.1241 | +0.0099 |

Interpretation：stage-2 有“比 random 好”的排序信号，但它还没有通过“比单特征更值得复杂化”的证据门槛。这个差别很重要。12A6c 的 stage-2 绝对阈值失败不能直接推出 continuation 没信号；12A7 说明有信号，但复杂模型收益太薄，CI 不够稳。

## 6. Budget curve 和 operating point 敏感性

Headline X=0.50 不是唯一有信息的位置。Robustness budget curve 显示，stage-1 在更严格的 X=0.30 下 actually 更有吸引力：fast-fail rate `0.1618`，不仅赢 random，也低于 single-feature headline rate `0.1788`。但这只是 curve readout，不是本次 pre-registered headline gate。

| stage | stage1_X | stage2_X | role | selected | budget_total | model_rate | base | random_p50 | delta_random | single_rate | delta_single |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| stage-1 | 0.30 | NA | stage_1_curve | 1,533 | 0.3290 | 0.1618 | 0.3053 | 0.2337 | -0.0719 | 0.1788 | -0.0170 |
| stage-1 | 0.50 | NA | primary | 2,427 | 0.5209 | 0.1965 | 0.3053 | 0.2339 | -0.0374 | 0.1788 | +0.0177 |
| stage-1 | 0.70 | NA | stage_1_curve | 3,279 | 0.7038 | 0.2266 | 0.3053 | 0.2354 | -0.0088 | 0.1788 | +0.0478 |
| stage-2 | 0.50 | 0.30 | stage_2_chained_curve | 412 | 0.2113 | 0.1505 | 0.1034 | 0.1024 | +0.0481 | 0.1241 | +0.0264 |
| stage-2 | 0.50 | 0.50 | primary | 806 | 0.4133 | 0.1340 | 0.1034 | 0.1067 | +0.0273 | 0.1241 | +0.0099 |
| stage-2 | 0.50 | 0.70 | stage_2_chained_curve | 1,214 | 0.6226 | 0.1219 | 0.1034 | 0.1110 | +0.0109 | 0.1241 | -0.0022 |

Insight：stage-1 更像一个“只拒绝最差尾部”的 rejector，而不是 50% 大比例 keep/reject classifier。X=0.30 下复杂模型有可能超过低波动单特征；X=0.50 时，额外放进来的中间区域稀释了优势。Stage-2 也类似：X=0.30 continuation rate 最高，但 selected_n 只有 `412`，CI 和容量约束需要单独审计。

## 7. Budget drift 和 history-window 敏感性

Trailing rank 不是 whole-cohort percentile，因此预算仍会随当前 score 分布和历史窗口漂移。这个设计是 PIT 的，但不是“每期固定 50%”。

Primary tuple 的预算审计：

| stage | split | denom | rank_eval | not_eval_rate | selected | budget_total | budget_rank_eval | board_history_used | history_n_p50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| stage-1 | train | 8,303 | 8,050 | 0.0305 | 3,979 | 0.4792 | 0.4943 | 0.9676 | 2,624 |
| stage-1 | validation | 2,151 | 2,133 | 0.0084 | 1,681 | 0.7815 | 0.7881 | 0.9912 | 2,998 |
| stage-1 | robustness | 4,659 | 4,642 | 0.0036 | 2,427 | 0.5209 | 0.5228 | 0.9959 | 2,403 |
| stage-2 | train | 2,958 | 2,867 | 0.0308 | 1,427 | 0.4824 | 0.4977 | 0.9564 | 1,093 |
| stage-2 | validation | 1,210 | 1,197 | 0.0107 | 497 | 0.4107 | 0.4152 | 0.9884 | 1,278 |
| stage-2 | robustness | 1,950 | 1,944 | 0.0031 | 806 | 0.4133 | 0.4146 | 0.9949 | 1,165 |

Validation 的 stage-1 预算膨胀到 `78.1%`，说明 trailing rank 仍会受到当期 score distribution 相对历史窗口的漂移影响。Robustness 上 stage-1 budget 回到 `52.1%`，比 12A6c absolute threshold 的 `78%+` 更接近目标。Stage-2 robustness budget 只有 `41.3%`，说明 continuation score 在 model-kept survivor 内仍有下移/分布漂移。

History-window diagnostic 也支持“504 sessions 是可用但非完美折中”：

| stage | policy | robustness budget_total | robustness rate |
|---|---|---:|---:|
| stage-1 | rolling 252 | 0.5216 | 0.1979 |
| stage-1 | rolling 504 primary | 0.5209 | 0.1965 |
| stage-1 | rolling 1008 | 0.6370 | 0.2170 |
| stage-1 | expanding | 0.6978 | 0.2169 |
| stage-2 | rolling 252 | 0.4392 | 0.1297 |
| stage-2 | rolling 504 primary | 0.4133 | 0.1340 |
| stage-2 | rolling 1008 | 0.3713 | 0.1391 |
| stage-2 | expanding | 0.3562 | 0.1522 |

Longer窗口和 expanding 对 stage-1 明显更 stale：robustness keep budget 被推到 `63.7%` / `69.8%`，fast-fail rate 也更差。短窗口 252 和 primary 504 在 stage-1 接近；stage-2 的 rate 随窗口变长提高，但预算同步下降，不能直接当作 win，需要 matched selected_n 和 CI 再判断。

## 8. Look-ahead upper bar

Diagnostic look-ahead rank 不允许进入 decision，但它能衡量“如果当期分布完全可见，理论上还有多少空间”。

| stage | rank_method | selected | budget | selected_rate | base_rate | delta_base |
|---|---|---:|---:|---:|---:|---:|
| stage-1 | same_month_full_cohort_rank | 2,330 | 0.5001 | 0.1867 | 0.3059 | -0.1192 |
| stage-1 | board_month_full_cohort_rank | 2,324 | 0.4988 | 0.2083 | 0.3059 | -0.0976 |
| stage-1 | whole_split_rank | 2,330 | 0.5001 | 0.1712 | 0.3059 | -0.1346 |
| stage-2 | same_month_full_cohort_rank | 1,392 | 0.4996 | 0.1688 | 0.1228 | +0.0461 |
| stage-2 | board_month_full_cohort_rank | 1,395 | 0.5007 | 0.1613 | 0.1228 | +0.0385 |
| stage-2 | whole_split_rank | 1,393 | 0.5000 | 0.1565 | 0.1228 | +0.0337 |

Interpretation：whole-split / whole-month upper bar 明显优于 trailing-rank primary，特别是 stage-2。差距说明 score 的“相对当期分布位置”有价值，但完整 whole-month rank 带未来信息，不能直接部署。后续可以考虑更细的 PIT cohort normalization，例如只使用 decision-time 已出现的同月/同周/同 board 分布，但必须重新定义可部署 cohort，不能拿这个 diagnostic 当证据。

## 9. Findings

1. **12A7 修正了 12A6c 的主要比较污染，但没有支持复杂模型。** 12A6c 中 absolute threshold 把 base-rate/prior shift 混进了预算。12A7 用 rolling rank 后，stage-1 robustness 相对 random p50 从不可比变成可比，并得到 `-3.74pp` fast-fail improvement。但复杂模型在同预算、同 denominator、paired bootstrap 下输给 `volatility_60d asc`。

2. **Stage-1 的可交易形态更像“低波动防守 backbone”，不是多特征二元分类器。** Robustness 上 `volatility_60d asc` 单特征 rate 为 `0.1788`，复杂模型为 `0.1965`。这不是预算 artifact，因为 selected_n 都是 `2,427`，common denominator coverage 为 `1.0`。当前多特征模型把中间区域拉进 X=0.50 后，反而削弱了低波动 backbone。

3. **Stage-1 X=0.30 是最值得继续看的 operating point。** 在 robustness curve 中，X=0.30 的 fast-fail rate 是 `0.1618`，低于 single-feature headline 的 `0.1788`，且相对 random p50 改善 `-7.19pp`。这不能回头改 12A7 headline gate，但它给 12A7b 一个清晰假设：rejector 可能应该是 selective tail rejector，而不是 50% gate。

4. **Stage-2 有 continuation 排序，但复杂度收益太薄。** Primary robustness 上 model 比 random 高 `+2.73pp`，random bootstrap CI `[+0.56pp, +5.17pp]`。但 model 比 single-feature 只高 `+0.99pp`，paired CI `[-0.94pp, +2.80pp]` 跨 0。结论应该是 stage-2 signal diagnostic positive，而不是 stage-2 model supported。

5. **Trailing rank 缓解但不消除预算漂移。** Stage-1 robustness budget 是 `52.1%`，接近 headline X=0.50；但 validation 是 `78.1%`。这说明用历史分布 rank 是 PIT 的，但当当前 score distribution 明显下移时，仍会放出更多票。预算 drift 不是 bug，而是这个 operating rule 的经济特性。

6. **Expanding window 明显 stale。** Stage-1 robustness 在 rolling 504 下 budget `52.1%`、fast-fail `0.1965`；expanding 下 budget `69.8%`、fast-fail `0.2169`。这支持 reviewer 提出的“不能用 expanding-from-inception 冒充 trailing”判断，也支持本版 requirement 把 rolling window 作为 primary。

7. **Look-ahead upper bar 显示还有 normalization 空间，但不能直接用。** Stage-2 same-month full-cohort rank 可以到 `0.1688`，远高于 trailing primary `0.1340`。这提示当期 cohort distribution 很重要，但 whole-month rank 有未来信息；下一步只能研究严格 PIT 的 partial-cohort / rolling-cohort normalization。

## 10. 建议的下一步

当前 decision 的 `next_allowed_requirement = none` 是合理的。不要直接进入 12A8 calibration，因为 calibration 解决的是概率刻度，而当前 headline failure 是复杂模型没有超过 simple backbone。

建议 12A7b 聚焦：

1. 把 `volatility_60d asc` / 低波动防守规则设为 stage-1 主 backbone，而不是 challenger。
2. 重新测试 stage-1 X=0.30、0.40、0.50 的 matched random + matched single + bootstrap CI；X 必须在 train 冻结。
3. 用低容量、单调约束模型尝试超过 low-vol backbone，特征方向应显式约束，避免复杂模型吞掉 backbone 的稳定性。
4. Stage-2 暂时作为 diagnostic arm，优先测试 X=0.30 tail selection 和 `distance_to_120d_low desc` backbone；只有在 paired CI 明确超过 single-feature 后再串联进 headline two-stage gate。
5. 保留 vol-scaled label audit 作为后续方向，因为固定 -10% / +20% barrier 仍可能制造 base-rate 非平稳；但它应排在 simple-backbone operating rule 之后。

当前位置的研究结论是：**rank-based operating point 是正确方向，但复杂模型不是当前答案。12A7 应该把研究从“修阈值”推进到“以 simple backbone 为主基准的 selective operating rule”。**

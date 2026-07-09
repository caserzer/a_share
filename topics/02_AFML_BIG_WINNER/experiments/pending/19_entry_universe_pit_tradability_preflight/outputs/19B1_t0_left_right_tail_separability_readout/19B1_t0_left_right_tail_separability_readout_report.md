# 19B1 T0 左尾/右尾可区分性诊断读出

19B1 是 diagnostic-only。
validation outcome read = false。
19C replay authorized = false。
EP20 policy preflight authorized = false。
entry/exit/holding/portfolio/model/production/live trading authorization = false。
T0 separability 不等于 alpha support。
任何后续 left-tail suppressor 必须作为新的 pre-registered requirement，不能从 19B1 直接生成交易规则。

## 结论

本次读出在 19B 冻结的 B2 robustness candidate primary denominator 上，得到 `19B1_t0_left_right_tail_separable_diagnostic`。这表示：在 T0 / as-of-decision-date 已知特征上，左尾坏样本与干净右尾样本存在可重复的统计差异；但这个结论只支持“下一轮预注册 left-tail suppressor 假设”的研究方向，不支持直接生成交易规则、replay、policy preflight 或实盘信号。

核心证据有三层：

1. outcome-space 上，左尾与右尾不是简单同一批样本的完全重叠表现。`P(left_tail_10 | right_tail_50)=0.333333`，而 `P(left_tail_10 | not right_tail_50)=0.549687`，差值为 `0.216353`，cluster bootstrap 95% CI 为 `[0.159893, 0.272173]`，Fisher p-value 为 `1.62e-14`。
2. T0 feature-space 上，19 个预冻结 primary features 全部通过 PIT/source/support gate，其中 4 个特征通过 separability gate，覆盖 3 个 signal group：`volatility_range`、`recent_return`、`relative_strength`。
3. stability 上，top features 在 instrument cluster bootstrap、去除 top1/top3 winner instruments 后方向保持稳定；LOMO 月度检查只有 2 个有效 fold，按 requirement 是 diagnostic-only，不单独否决。

## 冻结样本和门禁

Primary scope 固定为：

| 字段 | 值 |
|---|---|
| family_id | `B2_relative_strength_breakout` |
| grid_cell_id | `B2-relative-strength-breakout__182b3d0f30f5` |
| split | `robustness` |
| row_scope | `candidate_primary_denominator` |
| candidate_n | `1552` |
| instrument_n | `524` |

所有关键 gate 均为 `pass`：

| gate | 结果 |
|---|---|
| config_contract_gate | pass |
| input_artifact_gate | pass |
| upstream_19a_contract_gate | pass |
| upstream_19b0_contract_gate | pass |
| upstream_19b_contract_gate | pass |
| sample_support_gate | pass |
| primary_row_join_gate | pass |
| outcome_overlap_gate | pass |
| t0_feature_pit_gate | pass |
| primary_feature_separability_gate | pass |
| stability_gate | pass |
| policy_authorization_gate | pass |
| output_contract_gate | pass |

解读：本次不是在扩大搜索空间，也不是重新挑选 B2 cell；它只是在 19B 已冻结 rows 内，检查 T0 信息是否能解释“哪些候选更像左尾坏样本、哪些更像干净右尾样本”。

## Outcome Overlap

Outcome 分组如下：

| outcome group | 定义 | 行数 |
|---|---|---:|
| right_tail_event_50 | `MFE_120 >= +0.50` | `435` |
| left_tail_event_10 | `MAE_20 <= -0.10` | `759` |
| left_tail_event_20 | `MAE_20 <= -0.20` | `229` |
| right_clean | 右尾事件且没有 -10% 左尾 | `290` |
| left_bad | -10% 左尾且没有右尾事件 | `614` |
| both | 同时右尾和 -10% 左尾 | `145` |
| neither | 二者都没有 | `503` |

条件概率：

| 指标 | 值 |
|---|---:|
| `P(left_tail_10 | right_tail_50)` | `0.333333` |
| `P(left_tail_10 | not right_tail_50)` | `0.549687` |
| `P(right_tail_50 | left_tail_10)` | `0.191041` |
| `P(right_tail_50 | not left_tail_10)` | `0.365700` |
| `left_tail_conditional_probability_diff_not_right_minus_right` | `0.216353` |
| `right_tail_conditional_probability_diff_not_left_minus_left` | `0.174659` |
| Fisher exact p-value | `1.62e-14` |
| chi-square p-value | `1.89e-14` |
| phi coefficient | `-0.194392` |
| mutual information | `0.019193` |
| cluster bootstrap diff CI | `[0.159893, 0.272173]` |

Finding：左尾坏样本不是右尾样本的简单副产品。右尾样本里仍有三分之一发生 -10% 左尾，但非右尾样本的左尾概率更高，说明 B2 暴露的尾部结构是“不对称且可分层”的。这个结果支持继续寻找 left-tail suppressor，但不说明 suppressor 一定能保留右尾收益。

Insight：B2 当前的问题不是“没有右尾”，而是“右尾 reservoir 中混入了大量 T0 可识别的高左尾风险状态”。因此下一步不应该回到泛化预测 winner，而应预注册一个抑制左尾的 ablation：先固定 suppressor 特征和阈值，再评估是否减少 left_bad 且不显著牺牲 right_clean。

## T0 单变量可区分性

19 个 primary features 全部通过 feature support gate。通过 separability gate 的特征如下：

| feature | signal group | left_bad median | right_clean median | median diff | SMD | oriented AUC | AUC CI low | AUC CI high | BH-FDR p | direction |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `match_vol60` | volatility_range | `0.041490` | `0.035335` | `0.006155` | `0.473168` | `0.626418` | `0.580841` | `0.672588` | `1.54e-08` | positive |
| `atr_20_pct_asof_decision_date` | volatility_range | `0.055880` | `0.048239` | `0.007641` | `0.432884` | `0.614664` | `0.575060` | `0.653171` | `2.40e-07` | positive |
| `return_60d_asof_decision_date` | recent_return | `0.637413` | `0.508847` | `0.128566` | `0.294048` | `0.593564` | `0.551979` | `0.637446` | `3.46e-05` | positive |
| `close_to_ema60_asof_decision_date` | relative_strength | `0.318891` | `0.265761` | `0.053130` | `0.292162` | `0.588773` | `0.550763` | `0.627464` | `7.64e-05` | positive |

未通过但有提示意义的特征：

| feature | signal group | direction | oriented AUC | AUC CI low | BH-FDR p | 未通过原因解读 |
|---|---|---|---:|---:|---:|---|
| `market_drawdown_60d_asof_decision_date` | market_regime | negative | `0.569294` | `0.521152` | `0.002771` | AUC 接近阈值但 SMD 约 `0.199942`，低于 `0.20` 门槛 |
| `match_market_cap` | size | negative | `0.568421` | `0.517603` | `0.002805` | size 有方向，但效应不够强，不应作为核心 suppressor |
| `stock_vs_market_return_20d_asof_decision_date` | relative_strength | positive | `0.564147` | `0.523292` | `0.004963` | 与 relative strength 方向一致，但 AUC 未达 `0.57` |
| `return_20d_asof_decision_date` / `match_return20` | recent_return | positive | `0.556944` | `~0.522` | `0.011951` | 20 日动量有弱信号，但不足以进入 positive diagnostic |

Finding：最强的区分不是单纯“强势更好”，而是“强势同时伴随更高波动时，更容易落入 left_bad”。通过特征中有两个来自 volatility_range，说明左尾风险很可能和入场前已经存在的波动状态有关；recent_return 和 relative_strength 通过，则说明这些 left_bad 并非弱势票，而更像“已显著上涨、偏离均线、波动升高后继续冲高失败或剧烈回撤”的状态。

Insight：这更像一个两阶段机制：B2 成功抓到了右尾 reservoir 的动量/相对强度形态，但 reservoir 内部存在“高波动强势延伸”的左尾污染。后续 suppressor 不应简单删除强势或高收益，因为这会伤害 right_clean；更合理的方向是预注册组合条件，例如“强势状态下的异常波动、ATR、vol60 或过度偏离均线”是否能筛掉 left_bad。

## 稳定性

Top features 的稳定性检查：

| feature | bootstrap direction stable rate | top1 removal AUC | top3 removal AUC | top1/top3 support | 结论 |
|---|---:|---:|---:|---|---|
| `match_vol60` | `1.0000` | `0.632677` | `0.644954` | pass / pass | 去除 winner 集中度后更强，非单一大赢家驱动 |
| `atr_20_pct_asof_decision_date` | `1.0000` | `0.616509` | `0.618783` | pass / pass | 波动信号方向稳定 |
| `return_60d_asof_decision_date` | `1.0000` | `0.594329` | `0.601321` | pass / pass | 60 日动量差异稳定 |
| `close_to_ema60_asof_decision_date` | `1.0000` | `0.589839` | `0.598341` | pass / pass | EMA 偏离差异稳定 |
| `market_drawdown_60d_asof_decision_date` | `1.0000` | `0.569372` | `0.563089` | pass / pass | 方向稳定，但未进入 primary positive feature |

top winner removal 细节：

| 检查 | 去除 instrument 数 | 去除 winner 数 | 影响 |
|---|---:|---:|---|
| top1 winner instrument removal | `1` | `16` | top features 方向保持不变 |
| top3 winner instruments removal | `3` | `39` | top features 方向保持不变 |

LOMO 月度检查只有 `2` 个有效 fold，低于 `leave_one_month_min_effective_fold_n_for_reporting=6`，状态为 `diagnostic_only_insufficient_effective_month_support`。这不能推翻 stability gate，但提醒：月度层面的可重复性证据仍不足，后续 suppressor 不能只依赖本次 LOMO 结果。

B5 negative-control / contrast 使用成功，`B5_negative_control_support_gate=pass`。以 `match_vol60` 对 B5 做 contrast 时，方向仍为 positive，oriented AUC 为 `0.583490`。这说明波动型左尾污染不只出现在 B2，也可能是“强势/突破类候选”的共性风险；但 B5 结果只允许作为 contrast，不允许修改 B2 结论。

## 图表解释

### `figures/b2_outcome_left_right_overlap.png`

这张图展示 B2 primary rows 的四类 outcome group：`right_clean=290`、`left_bad=614`、`both=145`、`neither=503`。最重要的信息是 left_bad 的数量明显大于 right_clean，说明 B2 在 19B 中失败的原因并不是没有右尾，而是左尾负担太大。`both=145` 也说明右尾和左尾并非互斥：部分股票会先经历明显回撤，同时仍在 120 日内出现 +50% MFE。

### `figures/b2_t0_top_feature_distributions.png`

这张图对 top T0 features 展示 left_bad 与 right_clean 的分布差异。分布不会完全分开，所以不能把它理解成一个可交易分类器；但 left_bad 在 `match_vol60`、`atr_20_pct_asof_decision_date` 等波动特征上整体右移。这种“分布右移而非硬阈值分离”的形态，适合生成 suppressor hypothesis，不适合直接生成 entry rule。

### `figures/b2_t0_feature_auc_forest.png`

这张图按 oriented AUC 展示 19 个 primary features 及 bootstrap CI。通过 gate 的特征集中在 `match_vol60`、`atr_20_pct_asof_decision_date`、`return_60d_asof_decision_date`、`close_to_ema60_asof_decision_date`。其中波动类特征的 AUC 最高，并且 CI 下界明显高于 0.50；这说明左尾坏样本在 T0 已经带有更高波动状态，不完全是入场后的随机路径噪声。

### `figures/b2_t0_separability_stability.png`

这张图展示 cluster bootstrap 的 direction stable rate。top features 的方向稳定率均为 `1.0000`，满足 `0.70` 门槛。它说明本次单变量差异不是 bootstrap 重抽样下方向反复翻转的弱信号。需要注意的是，稳定方向不等于可交易收益稳定，只说明本次 diagnostic separability 的方向较稳。

## AFML 判断

本次结果把 B2 的状态从“19B false-positive burden blocked”细化为：

```text
右尾 reservoir 存在，但 reservoir 内部有可由 T0 波动/动量状态识别的左尾污染。
```

这对 AFML 后续设计的含义是：

1. B2 不应直接升级为策略或 19C replay，因为 19B 的 false-positive burden 仍然存在。
2. B2 也不应简单废弃，因为 19B1 显示 left_bad 与 right_clean 在 T0 上可分。
3. 下一步应该是新的预注册 requirement：冻结 left-tail suppressor 候选特征、阈值、支持门槛、评价指标和多重检验口径，然后验证 suppressor 是否降低 left_bad，同时保留足够 right_clean。
4. suppressor 的优先方向应围绕 `volatility_range + recent_return/relative_strength` 的组合，而不是单独按规模、流动性或短期收益粗暴过滤。

最终判断：19B1 给出的不是 alpha 结论，而是一个更清晰的研究方向。B2 的右尾暴露并非完全不可修复；但任何修复必须在新的预注册实验中证明“减少左尾污染且不杀死右尾 reservoir”。

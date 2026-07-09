# 19B2 B2 高波动强势延伸左尾 suppressor 消融报告

19B2 是 diagnostic-only suppressor ablation。
T0 suppressor ablation 不等于 alpha support。
validation outcome read = false。
19C replay authorized = false。
EP20 policy preflight authorized = false。
entry/exit/holding/portfolio/model/production/live trading authorization = false。
任何 delayed confirmation、entry timing 或 left-tail rejector model 都必须作为新的 pre-registered requirement。

## 结论

- decision_state = `19B2_suppressor_improves_burden_but_not_interaction_supported_diagnostic`。
- best variant = `B_vol60_80_ret60_80` / `logical_interaction`。
- B2 四分组事实沿用 19B1：right_clean = 290, left_bad = 614, both = 145, neither = 503。
- best variant 删除率 = 0.120，right_clean kept = 0.897，left_bad removed = 0.161，both removed = 0.214。
- p_candidate_50_after = 0.274，MAE_20_p10_improvement_vs_S0 = 0.013，report-only MAE_worsening_after = 0.080。
- best variant 对比 single-feature `A_ATR20_top10`：efficiency lift = -0.267，CI low = -0.688。

## 读法

both 组同时满足右尾和左尾，不能直接并入 left_bad；过度删除 both 可能意味着问题更接近 exit/holding 风险，而不是 entry suppressor。
tail_risk_score 使用乘法，是为了捕捉高波动和强势延伸同时出现的交互风险；简单相加会把单一高 return 或单一高 volatility 当成同等风险。
single-feature ablation 只用于预算匹配对照，不能单独触发 high-vol-extension supported decision。
common support / market state 只是描述性审计，不是主 suppressor；本轮 support comparator 使用 eligible_universe_primary。
best variant 的 max_SMD_after = 1.505，max_SMD_feature_after = `match_return20`。

## 失败解释

当前结果不能简化写成 “B2 bad”。本轮读数显示：
1. best suppressor 删除了 0.161 的 left_bad，左尾污染有可解释集中，但删除量仍有限。
2. best suppressor 保留 right_clean = 0.897，没有主要失败在误杀 right_clean。
3. MAE_20_p10 相对 S0 改善 0.013，已达到 1 个百分点门槛。
4. p_candidate_50_after = 0.274，低于 S0 的 0.280，但仍高于 primary 门槛 0.24。
5. interaction score 没有同时以点估计和 bootstrap CI 优于 single-feature：lift = -0.267，CI low = -0.688。
6. both_removed_rate = 0.214，both 被单独输出；该风险可能更适合后续 exit / holding policy 诊断，而不是直接并入 left_bad。
7. max_SMD_after = 1.505，common support 仍显示 B2 更像 morphology diagnostic，而不是可直接交易的 entry policy。

## 下一步边界

若要继续，只能把 high-risk bucket 作为新的 hypothesis source，另开 pre-registered requirement。
不得从本报告直接推出交易规则、replay 授权、模型训练授权或生产信号授权。

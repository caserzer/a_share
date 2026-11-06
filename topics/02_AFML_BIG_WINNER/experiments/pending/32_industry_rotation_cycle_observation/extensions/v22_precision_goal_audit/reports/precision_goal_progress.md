# EP32：precision翻倍目标的阶段汇总

目标保持precision≥23.50%、周期recall≥41.25%。本轮累计37个冻结模型、629项不同模型/选择政策，符合两项数值目标的组合数为0；目标尚未完成。选择网格已反复查看历史，不能视为629次独立验证。

原主要候选和当前保召回网格最优对照：

|model|policy|precision|point_recall|event_recall|active_date_fraction|median_delay_days|
|---|---|---|---|---|---|---|
|risk_blend|top_0.1|11.75%|20.35%|45.83%|100.00%|37.88|
|risk_diffusion_min|all_p0.15|17.63%|22.36%|50.18%|63.29%|55.32|

保留召回下限的前十项：

|model|policy|precision|point_recall|event_recall|active_date_fraction|median_delay_days|
|---|---|---|---|---|---|---|
|risk_diffusion_min|all_p0.15|17.63%|22.36%|50.18%|63.29%|55.32|
|rank_one|all_p0.15|16.71%|19.56%|42.45%|99.88%|40.75|
|diffusion_median14|all_p0.2|16.29%|18.00%|41.76%|59.58%|59.85|
|long_blend|all_p0.15|16.24%|20.60%|49.29%|65.52%|52.49|
|long_blend|top10_p0.1|16.01%|16.45%|43.58%|81.54%|50.35|
|diffusion_confirmed|top10_p0.075|15.96%|16.69%|41.40%|86.18%|52.82|
|risk_diffusion_min|top10_p0.1|15.92%|17.44%|44.01%|80.31%|48.12|
|diffusion_confirmed|top10_p0.025|15.90%|18.34%|44.02%|94.04%|49.21|
|risk_tree|all_p0.15|15.86%|26.40%|55.56%|67.51%|53.29|
|risk_prior_blend|all_p0.1|15.78%|35.52%|65.07%|72.31%|42.26|

上述最佳网格点的逐年表现：

|year|precision|point_recall|event_recall|active_date_fraction|
|---|---|---|---|---|
|2021|0.436956265830944|0.250759548915978|0.640079077107379|0.5706603500313029|
|2022|0.3105208533887262|0.2369541598485483|0.4936127230515499|0.6092171717171717|
|2023|0.064703094807848|0.1584337285444662|0.2537043110646437|0.6716666666666666|
|2024|0.0990293022114783|0.1623784928112958|0.3014498024272475|0.6777777777777777|

逐频率表现：

|frequency|precision|point_recall|event_recall|active_date_fraction|
|---|---|---|---|---|
|BW|0.1655406306961207|0.2312188353599508|0.5172269118287042|0.6475903614457831|
|M|0.1998120965122385|0.2280876624586516|0.3637304134779128|0.6208333333333333|
|W|0.1634348038531594|0.2116273111571479|0.6245519129826423|0.6301775147928994|

五步探索分别是：V17调整五个主要模型的选择预算；V18增加条件扩散信息并设同容量对照；V19补齐其余20个旧模型；V20检验持续确认和模型一致性；V21补回6—12个月趋势及市场状态。每步原失败结果、预定网格和数据边界都保留。

precision维持原有日期等权口径，没有已知报警的日期不纳入该均值，因此活跃日期比例必须一起看。周期recall的分母始终为原全部可评价周期，没有随筛选政策缩小。时点recall另外报告。延迟列是各任务中位延迟的平均，基于首次命中的自然日距阶段低点，仅对检出周期计算。

所有结果保留原全二三级行业、周/双周/月、三阈值、双基准，主评价2021年至2024年9月统一24个月随访。未知结果不记负例，2021分类断点覆盖较低；严格PIT仍BLOCKED_DATA，独立前瞻FORWARD_PENDING。更高precision的网格最优尚未替代原主要候选，更未部署。

下一步有待检验的方向是让训练目标更贴近“每个周期至少发现一次”：当前逐时点损失会重复计入同一容易识别的周期。可固定比较按成熟正例周期等权的模型与原逐日期权重模型，并保持正例总权重和同样标签成熟隔离；在完成实验前不声称它能提高precision或recall。本轮没有把这项未执行方案算作完成。

[所有629项组合](../outputs/all_candidates.csv) · [逐年](../outputs/annual_summary.csv) · [逐频率](../outputs/frequency_summary.csv) · [机器可读状态](../outputs/decision.json) · [V17](../../v17_precision_recall_frontier/reports/frontier_observation.md) · [V18](../../v18_conditional_diffusion/reports/conditional_diffusion.md) · [V19](../../v19_remaining_model_frontier/reports/remaining_frontier.md) · [V20](../../v20_persistent_confirmation/reports/observation.md) · [V21](../../v21_long_context/reports/observation.md)

# EP32 报告入口

当前目标已按用户确认的历史汇总标准完成：[V28 最终方法与独立重算](extensions/v28_aggregate_acceptance/reports/accepted_method.md)。precision从11.75%提高至24.65%（2.10倍）；周期recall从45.83%变为44.39%（保留96.86%，高于41.25%下限）。原始预测与市场价格重建名单、逐任务指标核对，共302项检查通过。

最终选择为风险树与扩散树分数都≥0.11，且中证全指过去126个交易日收益>0；所有符合条件行业入选，预算不再固定前10%。周/双周/月度及二三级行业、双基准/三阈值完整保留。

用户明确按汇总门槛验收，并保留局限：2023年周期recall从47.00%降至18.57%；周度precision22.27%未单独达到23.50%；时点recall降至14.44%；有信号日期约27.45%；选中信号中41.69%结果未知。严格PIT仍BLOCKED_DATA，独立前瞻FORWARD_PENDING，未部署生产。

本轮完成记录：[V23 周期等权](extensions/v23_event_weighting/reports/observation.md)、[V24 短期阶段失效风险](extensions/v24_short_hazard/reports/observation.md)、[V25 高分门槛边界](extensions/v25_event_threshold_extension/reports/high_threshold_observation.md)、[V26 市场状态过滤](extensions/v26_market_regime_filter/reports/market_regime_observation.md)、[V27 近目标区间与未知结果](extensions/v27_regime_threshold_review/reports/threshold_review.md)。全部失败及803项不同模型/选择政策保留。此前[V22 阶段汇总](extensions/v22_precision_goal_audit/reports/precision_goal_progress.md)仍作为当时未达标的记录。

上一阶段结论：[V16 按用户确认的相对RD目标确定研究候选](extensions/v16_relative_goal_decision/reports/relative_goal_decision.md)。用户确认以稳定优于原RD为主，2倍提升为更高目标。保留阶段过滤与风险树各50%的risk_blend：69个可评价任务年度中67个误差改善，周/双周/月度的12个年度汇总全部改善，平均相对Brier降低5.44%。该相对历史研究目标已完成；严格PIT与独立前瞻验证仍未完成。

简约对照rd_gate为69/69改善；进取候选rank_hedged总体前10%命中率12.95%、提升2.08倍，但改善任务年度为62/69。完整稳定性、延迟、45项校正及失败组合见V16；旧的更高标准未通过记录保留，不追溯改写。

已完成的扩展研究：

- [V15 总体概率与行业排序分离](extensions/v15_rank_separation/reports/rank_separation_observation.md)：总体提升超过2倍，逐年及完整要求未通过。
- [V14 相对RD稳定性审计](extensions/v14_relative_baseline_audit/reports/relative_baseline_stability.md)：与旧完整门槛区分报告。
- [V13 已完成阶段历史](extensions/v13_completed_history/reports/completed_history_observation.md)：未取得稳健新增改善。
- [V12 波动尺度与持续性风险](extensions/v12_duration_risk/reports/duration_risk_observation.md)：产生本次主要候选，固定融合权重未调整。
- [V11 误报归因](extensions/v11_error_audit/reports/stability_progress.md)：主要剩余误报为短行情及候选低点被替代。
- [V9 市场上下文](extensions/v9_market_context/reports/market_context_observation.md)、[V8 共享样本模型](extensions/v8_pooled_stage/reports/pooled_stage_observation.md)、[V7 实时阶段过滤](extensions/v7_online_stage/reports/online_stage_observation.md)：已完成，原结果保留。V10标签成熟延迟研究亦已完成，完整结果位于其扩展目录。

最新机制探索：[V6 经济学假设与早期景气验证](extensions/v6_economic_diffusion/reports/economic_hypotheses.md)。固定V5 RD-Agent模型，检验龙头先行、同业扩散、市场调整后的强势；六项主检验均未通过，盈利共同改善因公告版本数据不足而阻断。未追加参数搜索，V1—V5原件保留。

最新识别实验：[V5 RD-Agent：提前启动预测与景气早期识别](extensions/v5_rdagent_onset_forecast/reports/rdagent_observation.md)。先完成30轮“未来1个月内启动”预测，周/双周/月度全部未达到约定标准后，再完成30轮“启动后前3个月”识别。两阶段均未通过完整验收；早期识别有小幅概率误差改善，但命中率提升不足2倍。严格PIT仍为BLOCKED_DATA，原V1—V4保留。

全行业逐项数据：[二级、三级行业完整目录与结果](extensions/v4_all_industry_review/reports/all_industries.md)。覆盖旧、新版全部目录，以及成员记录中的额外代码；逐行业列明有无可用数据、6—18月候选阶段、超18月及未结束阶段、起点市值前三收益和未知项。半导体、通信仅是复查案例。此补充只读展开V4，原V1—V4保持不变。

最新全量重做：[V4 全历史6—18个月自然上涨阶段](extensions/v4_adaptive_6_18_months/reports/adaptive_stage_observation.md)。

V4按价格转折确定可变起止；行业自身上涨并跑赢同期基准；超过18个月不拆分，只标记超范围。三种回撤口径和估值层并列，未结束/左删失/短段/超长段保留。原V1—V3保持不变。

前次复查：[V3 筛选逻辑与2025下半年—2026上半年固定窗口](extensions/v3_screening_review/reports/screening_review.md)。

V3确认存在这段价格/超额现象，拆开进入事件、停牌估值、行业排名、三只共同跑赢及已结束段筛选；原V2全局统计不回改。

完整历史版本：[V2 完整历史与市场超额观察](extensions/v2_full_history_benchmark/reports/full_history_observation.md)。

- 从数据地基2017年起观察；申万二级/三级，2014版与2021版分别计算。
- 沪深300、中证全指并列比较同期收益差，全A等权代理作诊断。
- [跑赢基准的行业及逐股名单](extensions/v2_full_history_benchmark/reports/04_screened_cases.md)。名单为事后查询，不是买入信号。
- [本轮方案及数据边界](extensions/v2_full_history_benchmark/research_plan.md)。严格PIT缺口仍保留。

前一版：[V1 2022年起的价格领先观察](reports/first_observation.md)，原文件及清单保持不变。

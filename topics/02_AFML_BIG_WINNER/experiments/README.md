# Experiment Workspace

Experiment names are not fixed at project start. Copy
`templates/experiment_template/` into `pending/<short_slug>/` only after a
workstream has a concrete requirement, frozen label contract, and validation
gate.

Each experiment folder owns:

- `config.yaml`: all thresholds, paths, label contracts, gates, and data cutoff.
- `code/`: experiment-specific scripts only.
- `outputs/`: generated data, metrics, tables, figures, reports, manifests,
  publishable artifacts, local cache, and large raw artifacts.
- `tests/`: focused checks for the experiment contract.
- `notes/`: design notes, review notes, and decision logs.

Reusable code belongs in top-level `src/afml_big_winner/`, not inside an
experiment folder.

Current pending experiments:

- `pending/01_data_prepare_pit_largecap_akshare_qlib_v0`: prepare the PIT
  large-cap A-share universe and Qlib daily data cache from AkShare.


---

## 当前研究索引（2026-10-21）

下表对应 `topics/02_AFML_BIG_WINNER/experiments/pending/` **已存在的研究目录**。历史产物存放在 `pending` 是现有目录习惯，不代表全部未执行；实验是否完成、是否被阻断以及是否授权使用，以每个Episode的原始报告为准。

总体叙事见 [研究日志](../research_log.md)，当前证据与关闭路线见 [研究结论](../research_conclusions.md)。

| EP | 研究方向 | 证据状态摘要 |
| --- | --- | --- |
| 01 | PIT/Qlib 数据地基 | 已完成，但ST/报价覆盖有偏差 |
| 02 | Winner生命周期画像 | 后验持续/修复结构明确 |
| 03 | 可观测入场锚点 | 匹配覆盖不足，entry不授权 |
| 04 | 高召回事件 | 召回与真正可交易桥接不一致 |
| 05 | PIT Top400/Top100 | 活跃证券源缺口，代理股票池 |
| 06 | Top-N重做生命周期 | 大样本确认路径特征，仍为后验 |
| 07 | 多通道候选 | E1召回强，重复通道拖密度 |
| 08 | Risk-on/Transition | Risk-on有拒绝排序线索，未过cost/retention；Transition不稳 |
| 09 | Fast-fail标签/特征 | 有局部AUC，无可支持的过滤规则 |
| 10 | Layered rejector | 冷却去重可用；winner-safe gate未通过 |
| 11 | Archetype / 两阶段观察 | 错误入场减少，但现金与机会成本抵消 |
| 12 | C0/State-change | 稀疏更优，事件precision不足 |
| 13 | Native event/survival | 有机会信息，防御动作净效用失败 |
| 14 | 稀疏事件效用 | 50bps same-event utility未通过 |
| 15 | Winner路径标签 | 事后形态可分，PIT形态不支持 |
| 16 | 顺序持有 | Survival可分，continuation效用失败；主线关闭 |
| 17 | Oracle Action Value | 未来信息Oracle有上限；不是交易策略 |
| 18 | Payoff-state representation | 排序无法转换为正行动效用 |
| 19 | PIT entry / 双尾 | 右尾与左尾一起增大；无已确认入场Alpha |
| 20 | OHLCV/残差动量 | 部分历史排序线索，样本/稳定性阻断 |
| 21 | REAKA/DRC | 已密封21C late失效；21F仅暂定，反向验证未做 |
| 22 | 实盘经验机制拆解 | 仅计划与需求，未发现正式实证结题 |
| 23 | RD-Agent-Quant | GRU对MLP有增量，未优于股票池等权 |
| 24 | 完整收益概率分布 | 167候选未过原验收；经济价值不稳 |
| 25 | 分布增量 | 估值+财务6月CRPS差于简单基线 |
| 26 | 6月重大亏损概率 | M_R风险排序有效的历史线索，校准漂移 |
| 27 | 市场/行业/公司风险分层 | Full对RMI局部增量，对M_R无总体优势 |
| 28 | 文献机制迁移 | L2风险结构线索，主Brier不确定；退市报价恢复非总收益闭合 |
| 29 | 全局/同行/个股适配 | GI极小增量；联合GPI不优于G |

正式报告快捷入口：

- [EP17 Oracle](pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/reports/ep17_oracle_action_value_diagnostic_report.md)
- [EP19 总结](pending/19_entry_universe_pit_tradability_preflight/outputs/publishable/reports/episode_19_final_report.md)
- [EP21 已密封复现](pending/21_residual_enhanced_koopman_auto_encoder_v0/outputs/21C_full_reaka_pit_proxy_replication_v4_detailed_report_cn.md)
- [EP23 完整报告](pending/23_rdagent_quant_pit_replication_v0/EP23_rdagent_quant_pit_replication_full_report_cn.md)
- [EP24 研究报告](pending/24_conditional_return_distribution_exploration/EP24_research_report.md)
- [EP25 结论](pending/25_incremental_distribution_validation/final_conclusion.md)
- [EP26 结论](pending/26_left_tail_probability_validation/final_conclusion.md)
- [EP27 结论](pending/27_hierarchical_tail_risk_attribution/final_conclusion.md)
- [EP28 结论](pending/28_literature_guided_tail_risk/reports/final_conclusion.md)
- [EP29 结论](pending/29_global_stock_adaptation/reports/final_conclusion.md)

研究结论的最低证据要求：相同可用PIT信息、相同股票/预测日期与标签、竞争性简单基线、重叠标签的时间依赖、真实执行成本及机会成本；反复使用的历史测试集不得重新包装为独立前瞻样本。

## EP30 数据地基补充（2026-10-21）

[30_pit_data_foundation_v1](pending/30_pit_data_foundation_v1/README.md)：D2版本化事实/查询/标签基础、全缓存覆盖普查、真实财报首次/更正回放、D0/D1/D2桥接及受阻裁决。完整历史全市场PIT、权益/退市结算和可执行总收益仍BLOCKED；工程测试通过不升级为数据READY。EP01—EP29原始结论不改写。


EP30 追加 [D2 v2 实际补数](pending/30_pit_data_foundation_v1/reports/backfill_v2.md)（2026-10-21）：独立数据与冻结快照；保留v1及所有旧模型、预测、收益和研究裁决。


2026-10-21：[D2-v3原始资格与权益补数](pending/30_pit_data_foundation_v1/reports/pit_v3.md)追加发布：原文状态、退市权益与扫描件候选、财报版本链和全月份严格标签；全量PIT/执行/终值仍受阻，旧研究结论保留。


2026-10-21：EP30 追加 D2-v4，三组原件证明的连续代码变更修复重复身份及误报退市，删除155个重复证券月；退市披露代码桥接85家，原缺年报期66→43，重建6309144条严格标签，严格已知仍为0。79项测试通过；旧研究与三版封存保留。详见[本轮报告](pending/30_pit_data_foundation_v1/reports/pit_v4.md)。


2026-10-22：EP30 追加 D2-v5，按用户指定将当前收益标签统一为前复权价格变化推断。原 D2 主行情确认未复权；新生成10541309行前复权开收盘可用报价，6309144行标签中6007218行可推断；24只证券的跨供应商复权差异单列标记。旧严格结果保留，未知退市终值不填零。详见[本轮报告](pending/30_pit_data_foundation_v1/reports/pit_v5.md)。

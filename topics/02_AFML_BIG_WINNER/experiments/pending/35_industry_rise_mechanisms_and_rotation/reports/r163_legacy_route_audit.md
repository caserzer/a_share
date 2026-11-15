# R163 原始来源槽位与实际剩余工作核对

## 想验证什么

当前R157入口有41项核验证据，同时登记25个未纳入修复入口的旧槽位。“旧槽位”不等于“尚未执行的实验”：它也可能是原始来源、必须保留的旧试验，或已在另一路径重跑的结果。本轮逐项读取全部文件内容，核对用途及后续证据，避免机械重跑或丢失失败历史。

## 发现什么

25个槽位对应23个唯一来源路径。分类为：historical_snapshot 7项；source_retained 6项；replayed_separately 4项；metadata_refresh_needed 3项；historical_limitation 3项；stopped_diagnostic 2项。

| 槽位 | 分类 | 核对判断 |
|---|---|---|
| profit_company_revisions | source_retained | 报告时钟和券商固定财年修正，不由价格修复改变；R162确认月末日期集合不变。 |
| profit_industry_coverage | source_retained | 固定前月成员与报告覆盖已在R162逐字节复用核验。 |
| profit_model_predictions | replayed_separately | R162已补跑，642预测完全不变；不是待重跑实验。 |
| historical_evidence_monitor | historical_snapshot | R25历史监控保留；不声称与当前多维监控语义完全等价。 |
| current_factor_dictionary | metadata_refresh_needed | 定义目录仍有旧源路径与轮次；需更新到修复来源，不能把28定义当有效因子。 |
| battery_partial_series | historical_snapshot | 部分来源版本应保留，完整81月版本另外列示。 |
| battery_return_pilot | historical_snapshot | 旧部分数据试验保留，不覆盖成完整来源结果。 |
| extended_historical_evidence_monitor | historical_snapshot | R50冻结观察时钟保留，不等于当前经营信息。 |
| latest_battery_series | source_retained | 完整装车量源时间序列无价格依赖，修复实验已复用。 |
| latest_battery_return_pilot | replayed_separately | R140已修复该试验；原槽位不应误作最新模型结果。 |
| reviewed_complete_battery_series | source_retained | 与latest_battery_series同一原文件，不能重复算覆盖。 |
| complete_battery_historical_monitor | historical_snapshot | 原完整装车量监控的历史状态保留，当前入口另有多维证据。 |
| current_requirements_evidence | metadata_refresh_needed | R124叙述尚未吸收R125至R162，后续需分阶段结论与未完成能力。 |
| accounting_source_clock | source_retained | 原始归档时钟独立于股票篮子，仍不可倒填历史。 |
| forecast_realization_common_events | source_retained | 公司报告兑现对比非价格结果；价格比较已单列R144。 |
| stock_path_partial_bounds | historical_limitation | 缺失股票权重的条件界限仍不构成完整可交易路径。 |
| integrated_historical_clock_evidence | historical_snapshot | 原三时钟证据保留，不把归档时钟替换成公告代理。 |
| latest_stage_requirements_audit | metadata_refresh_needed | 与current_requirements_evidence同一文件，不能视为独立缺口。 |
| rank_redundancy_audit | stopped_diagnostic | 旧模型重复秩的代数审计，不增加信息，不需为采用目的反复重训。 |
| fixed_penalty_precision_comparison | stopped_diagnostic | 精度/惩罚分支明确未采用，停止无依据数值搜索。 |
| next_local_mechanism_source_audit | historical_snapshot | 该来源定位已由R113至R119口径研究执行，不是新的待办。 |
| leader_diffusion_branch | replayed_separately | R145已重放龙头分支，未获稳定增量支持。 |
| valuation_basis_and_financial_timing | historical_limitation | 代数与财务口径诊断保留，不证明实际现金流驱动。 |
| financial_change_branch | replayed_separately | R146已重放财务分支，样本和增量限制未解除。 |
| fund_etf_source_search | historical_limitation | R125/126后续查到16端点、10间隔，历史申万映射及拆分不明，0可用资金流间隔。 |

完整原路径、当前哈希、字节数、解析记录数及支持证据路径保存在 `outputs/r163/route_audit.json`。本轮是内容盘点和用途分类；没有重新独立验证全部旧实验，也没有把其核验状态自动升级为预测有效。

## 真正可继续的本地工作

1. 当前28条因子定义仍有旧数据源或轮次引用。须把定义、原始来源与修复后研究输入分别列清，更新最新解释与负结果，保留原定义版本。该工作无需新采集，也不应把字典数量解释成有效因子数量。
2. R16现存F母体/F方法的一级未校准反转模型有1个，期限60日、测试年2026，91条预测。存在固定退出代价诊断的数据条件；应先登记与继续持有/现金/市场切换的比较、费用和未知路径处理，不能补成正式校准概率或保证可执行。
3. 首发修订版本、ETF份额公司行动与历史申万映射、完整可成交股票路径、独立未来样本仍是具体缺口。R125/126已有有限ETF端点并非完全无数据，但0个满足资金流解释的间隔，不能用最新映射或价格涨跌伪造资金流。

## 对整体目标的影响

五个核心问题仍须分别回答，三类任务不得用同一评分替代。已有修复、负结果和局部不足不需要被制造成正结果；同时，来源版本维护和一级反转退出的必要比较仍可执行，不能据数据缺口宣布整体受阻或完成。

本轮没有新变量，因此没有新增领先性、独立信息或因果机制证据；也没有新增成本后配置价值。对已停止的排名冗余、惩罚精度等分支保留失败，不为了减少旧槽位数而重新搜索参数。

## 文件及核验边界

协议 `protocols/r163.json`；执行 `src/audit_legacy_routes_r163.py`；来源盘点 `outputs/r163/route_audit.json`；可执行与数据依赖事项 `next_actions.json`；盘点回执 `verification.json`。执行时要求分类键集合与默认入口全部25旧槽位精确相等，逐个实际解析原文件并记录支持证据哈希。

不修改R157指针，不删除旧文件，不把“分类完成”写成整体要求完成。下一项优先完成字典来源版本整理，并开展独立登记的一级反转退出代价比较。

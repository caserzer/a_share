# E1相对固定REV期限复核完成 2026-11-17

## 原 E1 残差与日期敏感度（2026-11-17）

[完整机制报告](reports/e1_timing_mechanism_20261117/REPORT.md)：四价格状态损益、固定名单日期比较、交易动作和连续账户桥接、残差与匹配覆盖。已定位月初新旧持仓窗口的损益差，残差的独立经济解释仍未完成。


[本轮报告](reports/e1_reversal_validation_20261117/REPORT.md)复用已封存名单，提取相同支持范围的E1/REV子组合，完成H5/H10/H20、逐年路径和具体股票差分核验；未重选、重训或调参。

- H10主比较45个可执行配对，原E1−REV净差+0.173pp，95%[−0.273,+0.575]，p=0.411；H5/H20亦未确认差异。缺失退出不填零，期限样本不同，不据此挑卖出日。
- 原连续账户2021/2022领先，2023/2024及2025截至3月3日落后；终值差仅1.304元/初始100元。全期接近不代表逐年稳定，也不是等价证明。
- 子组合平均占原预算31.60%，资本重叠41.14%；两条完整账户仍保留其余原E1，不是独立全市场反转策略。
- [前瞻合同](reports/e1_reversal_validation_20261117/FORWARD.md)冻结：信号须严格晚于2026-11-17且入场前封存。当前新观测0、AWAITING_NEW_SIGNAL；无调度、交易、重训或发送消息。元数据校验不替代known_at及日历证据。
- 85项测试、311项核验通过，原子组合H10精确复放。历史探索、Historical-proxy和前瞻未完成边界保留，未提交、推送或部署。

---

# 被排除持仓风格检验完成 2026-11-17

[本轮报告](reports/e1_excluded_styles_20261117/REPORT.md)固定上一轮被排除样本、原行业预算及持仓名额，比较反转、动量、低波动、高波动与预设等权混合规则，并尝试严格13风格独立匹配。

- 原E1净CAGR+4.84%，预设REV +4.56%；O−REV日收益差年化+0.247pp，95%[−2.16,+2.64]。是辅助历史线索，不是等价检验或独立反转策略认证；仅替换原总预算约31.60%。
- 主O−MIX日收益差年化+3.78pp，保留原Holm4族后p=0.094；H10差+0.302pp、区间跨零。未通过主裁决。
- 严格匹配521行业日期组：99组原风格缺失、58组同行容量不足、364组不可行，零可识别支持。SM机械等于原账户，统计标为不可用，不能解释为风格剥离后Alpha消失。
- 辅助条件RankIC约0.0099，95%[−0.0129,+0.0334]，未确认独立信息。不同样本与估计量不能直接与上一轮IC差分。
- 80项测试、1625项主核验通过；21条账户完整，原O精确复放。零支持求值修正保留原冻结脚本及名单，另存审计记录；未放宽规则、重训、提交或推送。Historical-proxy和前瞻边界保留。

---

# 原 E1 被排除持仓追查完成 2026-11-17

[本轮报告](reports/e1_excluded_holdings_20261117/REPORT.md)回到原始月初E1组合，仅将可匹配的C池外持仓预算换为同日同行业未入选股票；其余目标保留，不重训、不搜索规则。

- 被排除目标平均占33.19%资金；同行业替换P覆盖其中95.31%，同行业且同排除原因PR覆盖89.10%。这不等于完整风格匹配覆盖。
- 1001日精确复放原E1：O净CAGR+4.84%，P−0.45%，PR−0.44%。主O−P日收益均差年化+5.25pp，95%[+1.80,+8.99]；44个可退出匹配子组合H10事件净差+1.00pp，区间[+0.55,+1.49]，两项本轮Holm通过。
- 2021贡献约57.3%的O−P终值差；去2021及全部50期市值口径仅为事后敏感性，方向仍正。6个事件无法完整退出，未把缺失当零或伪造退出。
- 定位到原C池外的历史行业内选择线索，但其他风格、集中度、持仓数与路径未控制，仍不是独立Alpha或经济原因确认。
- 73项测试、2334项主核验及5项披露核验通过；9条连续账户完整，原模型/预测/历史报告未改。Historical-proxy、严格PIT与前瞻仍未认证，未提交、推送或部署。以下保留前序记录。

---

# 工程特征经济消融完成 2026-11-17

[本轮报告](reports/e1_engineered_ablation_20261117/REPORT.md)固定2021Q4完整模型，执行区间位置、波动回撤残差四组消融，保留原E1和13风格投影参照。

- 同日起点823交易日、41个月初信号、18条完整账户。位置平均净增量点估计+2.56pp，95%[−1.32,+6.54]；风险−1.08pp、交互+1.36pp，三项Holm均未通过，未确认稳定Alpha。
- 固定完整模型净CAGR−0.11%，移除两组−1.66%；共同加入H10净事件差−0.078pp且区间跨零。账户改善主要集中2022，不能以此证明稳定10日信息。
- 分数正交不等于持仓风险中性，完整暴露差与逐月、逐股票贡献已交付；仍是缩减C池、Historical-proxy历史探索。
- 69项测试、681项分析核验和173期结构检查通过，原E1参照精确复放；原输入与模型未改，未提交、推送或部署。保留前序记录如下。

---

# EP36 · 沪深300 Alpha 与指数增强

映射变化拆解（2026-11-17）：**固定2021Q4完整78特征模型与后续E1平均排序相关约0.916，H10 RankIC约0.0306。13风格压缩的映射变化主要在数据/分布/标准化项，而非季度模型更新。**

- [本轮报告](reports/e1_mapping_drift_20261117/REPORT.html) · [Markdown](reports/e1_mapping_drift_20261117/REPORT.md) · [两因素分解方法](reports/e1_mapping_drift_20261117/METHOD.md) · [工程特征审计](reports/e1_mapping_drift_20261117/FEATURES.md)
- 较长固定首日跨度：模型项约7%—8.5%、数据项约91.5%—93%；数字指映射变化分数能量分配，不是收益来源。
- 13风格未重建分数的带符号分配中，区间位置组约65%，pos60约56.8%；该组单独H10排序区间仍跨零，不能据此宣称pos60有可交易Alpha。
- 173期原分数精确复放，65项测试、867项核验通过。未重训、调参、新建组合、提交、推送或部署；真实前瞻仍未完成。

过去信息复制（2026-11-17）：**固定13风格过去分数复制未保住E1排序。** 首次合格拟合2021Q4，统一从2021-10-11至2025-03-03新建账户；同口径I净年化+1.68%、季度复制Q−6.74%、首次锁定LOCK−7.28%。不能与原完整E1全期年化直接混比。

- [总报告](reports/e1_past_style_copy_20261117/REPORT.html) · [Markdown](reports/e1_past_style_copy_20261117/REPORT.md) · [时序合同](reports/e1_past_style_copy_20261117/METHOD.md) · [完整统计](reports/e1_past_style_copy_20261117/DETAILS.md)
- 13项过去风格线性映射未稳定跨时点迁移，不代表所有复制方法不可能，也不构成原E1独立Alpha认证。
- 8条账户完整共同823日；61项测试、304项主核验和82项原名单身份核验通过。预测接口拒绝当日E1及未来收益；当前/未来教师改写不改变过去拟合。
- 未重训原E1、未训练未来收益目标、未调参、未提交/推送/部署；真实前瞻仍未完成。以下历史结果保留。

风格组追查（2026-11-17）：**约束收益损失主要落在动量/反转价格组；参考B是有方向的强势回撤组合，不能把贴近B解释为全面风险中性化。**

- [本轮总报告](reports/e1_style_channels_20261117/REPORT.html) · [Markdown](reports/e1_style_channels_20261117/REPORT.md) · [约束与股票替换](reports/e1_style_channels_20261117/CHANNELS.md) · [简单规则及复制](reports/e1_style_channels_20261117/REPLICATION.md)
- 仅加价格组：I净年化0.88%→−4.59%；从全部约束去掉价格组：−6.42%→−1.49%。零成本仍有相近差额，不能主要归因于交易费用。
- 独立REV/MOM/MIX未复制I；依赖当日E1的COPY约0.66%，接近I的0.88%但区间宽，不是独立替代模型或原完整E1复制。
- 400次固定约束优化、30条完整账户；57项测试、1261项核验通过。未训练收益模型、调参、提交、推送或部署。以下历史判断保留。

原账户优势拆解（2026-11-17）：**原E1 → 缩小股票池 → 减少数量 → 改行业预算 → 加风格约束，净年化依次4.84%、2.65%、5.26%、0.88%、−6.42%。** 优势并非主要消失在排除股票这一步；相对B的风格约束影响更大，反向顺序方向一致、幅度不同，不能当作唯一因果归因。

- [完整报告](reports/e1_advantage_bridge_20261117/REPORT.html) · [Markdown](reports/e1_advantage_bridge_20261117/REPORT.md) · [被排除持仓](reports/e1_advantage_bridge_20261117/EXCLUSIONS.md) · [逐步及逆序明细](reports/e1_advantage_bridge_20261117/STEPS.md)
- 8条账户、50个原调仓日、1001交易日完成；原始与受约束两端精确复放，54项测试及1351项检查通过。
- 原未知贡献19.39元中约16.16元来自最小行业规模规则，约2.88元来自换手率缺失。旧逐股周信号存在365条滞后分类，已另给统一周/月时钟审计，原报告保留。
- 没有新训练、参数搜索、提交、推送或部署；真实前瞻仍未完成。以下按时间保留此前研究。

机制实验已执行（2026-11-17）：**三个主检验均未确认增量。** 强势回撤条件系数、月初H10净J−B、E1剩余条件系数的Holm p分别约0.450、0.999、0.450。原账户收益来源仍未完整解释。

- [本轮总报告](reports/e1_alpha_mechanism_20261117/REPORT.html) · [Markdown](reports/e1_alpha_mechanism_20261117/REPORT.md) · [执行及修复记录](reports/e1_alpha_mechanism_20261117/EXECUTION.md)
- 24季度原分数复放、592次约束解、50个月初主净比较、9条连续账户完成；51项测试和955项核验通过。
- 主样本平均只覆盖原Q5约65.4%目标预算，实际股票资本约66.7%；严格逐股匹配和随机安慰剂覆盖不足，属于部分识别。
- [前瞻登记](reports/e1_alpha_mechanism_20261117/FORWARD.md)已建立，未来数据刷新和E1出分流程尚未具备，尚未生成真实前瞻信号。未重训、提交、推送或部署。以下原方案状态和旧结果按历史保留。

下一轮方案（2026-11-17）：[行业内回撤修复与 E1 信息增量完整实验方案](reports/e1_alpha_mechanism_20261117/PROTOCOL.md) · [设计配置](configs/e1_alpha_mechanism_20261117.json)。方案已创建，尚未执行；三个主检验分别裁决条件机制、成本后增量及 E1 剩余信息，前瞻仍 FORWARD_PENDING。

最新归因（2026-11-17）：**原始E1月度账户的超额已逐日对到账本。主区间初始100元，E1期末120.67元、指数78.04元；42.63元财富差可按月份、行业、股票、费用和现金精确加总。**

- [原始E1收益来源总报告](reports/e1_return_attribution_20261117/REPORT.html) · [Markdown](reports/e1_return_attribution_20261117/REPORT.md)
- [逐年逐月](reports/e1_return_attribution_20261117/TIME.md) · [行业和股票](reports/e1_return_attribution_20261117/HOLDINGS.md) · [同日起点行业内对照](reports/e1_return_attribution_20261117/CONTROLS.md)
- 约10.90pp年化差的反事实差额链：等权结构/基准口径2.73pp、评分池0.07pp、行业预算/路径1.60pp、行业内具体持仓/集中度/执行6.50pp。最后一项仍可能含已知风格，不是严格独立Alpha认证。
- 2021与2024贡献最大，2023几乎没有超额；前三贡献月占45.3%。全部归因、原E1及EW逐日复放、对照链检查通过；完整测试46项通过。旧账户、预测与报告保留。

最新续轮（2026-11-17）：**已补取并审计历史总市值／流通市值，完成A2、B1、B2历史代理实验。未确认Ridge相对风格复制组合的稳定净增量，也未确认模型特有的月初优势。**

- [A2/B1/B2完整总报告](reports/alpha_economics_20261117/REPORT.html) · [Markdown](reports/alpha_economics_20261117/REPORT.md)
- 独立报告：[市值与A1补充](reports/alpha_economics_20261117/A1_CAPS.md)、[A2净增量](reports/alpha_economics_20261117/A2.md)、[B1相位](reports/alpha_economics_20261117/B1.md)、[B2期限与成本](reports/alpha_economics_20261117/B2.md)
- 54条连续账户全部至2026-10-21；主区间保持至2025-03-03。41项测试、2788项检查及3072个换仓窗口对账通过。
- S0是依赖原预测的风格复制分数，并非独立训练的强风格模型；固定目标风险匹配不等于成交后全程精确风险中性。市值首发版本仍未认证，随机安慰剂覆盖有限，真实前瞻仍FORWARD_PENDING。
- [完整协议与冻结凭据](reports/alpha_economics_20261117/PROTOCOL.md)。以下首批和旧轮状态按历史保留，不表示本轮仍未执行。

首批状态（下述缺口及待执行项已由上方续轮推进）

最新补充（2026-11-17）：**A1 可用风格剥离已完成。E1 主区间 H10 原分数 RankIC 0.0412，加入行业、风险及流动性后残差为0.0084，95%区间跨零；辅助收益回归和较长区间仍有正向线索，不能宣布 Alpha 已被解释完。**

- [A1 完整报告](reports/alpha_falsification_20261117/REPORT.html) · [Markdown](reports/alpha_falsification_20261117/REPORT.md)
- [A/B 下一轮协议及执行边界](reports/alpha_falsification_20261117/PROTOCOL.md)
- [冻结清单](outputs/diagnostics/alpha_falsification_20261117/freeze.json) · [173项结果核验](outputs/diagnostics/alpha_falsification_20261117/validation.json)
- 11项数值风格加历史行业代理，完整市值控制缺失；A2/B1/B2仅登记指标与边界，完整组合构造尚未执行级冻结、经济实验未执行。真实前瞻仍为FORWARD_PENDING。原模型和预测未改，完整测试34项通过。

当前交付（2026-11-16）：**已完成排序、Q5周期与执行机制、等权及行业／近期涨跌匹配验证。存在历史正向线索，但稳定独立净增量未获确认，正式B指数增强仍未认证。**

用户于 2026-11-16 回复 `execute`，授权执行 GOAL.md 定义的研究，随后授权 `commit and push` 发布研究成果。原目标文档保留不改，其“仅生成文档”说明已被后续授权覆盖。未进行实盘、监控或消息发送。

- 最新完整探索报告：[HTML（含图表、各阶段全文及完整逐月记录）](reports/exploration_summary_20261116/REPORT.html) · [Markdown](reports/exploration_summary_20261116/REPORT.md)
- 综合结论简版：[SYNTHESIS.md](reports/exploration_summary_20261116/SYNTHESIS.md)
- 来源及交付核验：[manifest.json](reports/exploration_summary_20261116/manifest.json)
- 初始阶段报告（保留原裁决）：[中文总报告](reports/REPORT.md)
- 独立裁决：[A 排序与 Q5](reports/A_report_cn.md)、[B 受约束增强](reports/B_report_cn.md)
- 主表：[model_comparison.csv](outputs/model_comparison.csv)
- 年度/季度：[annual_performance.csv](outputs/annual_performance.csv)、[quarterly_performance.csv](outputs/quarterly_performance.csv)
- 交付检查：[final_validation.json](outputs/manifests/final_validation.json)
- Q5 周度／双周／月度敏感性：[完整报告](reports/q5_rebalance_20261116/REPORT.md)
- E1/E2/E3 完整逐月记录：[逐月报告](reports/q5_rebalance_20261116/monthly_records/MONTHLY.md)、[Excel](outputs/sensitivity/q5_rebalance_20261116/monthly_records/E1_E2_E3_monthly_returns.xlsx)
- 扣费后相对沪深300全收益诊断：[报告](outputs/diagnostics/net_excess_20261116/REPORT.md)

## 最新研究判断与后续调查

- E1/E2/E3主窗口RankIC分别约0.0398、0.0227、0.0430；E1跨训练窗口相对稳定，E2/E3未证明复杂度增量。
- 共同区间2021-01-08至2025-03-03，月内第1信号Q5主成本净年化约4.84%、4.67%、2.73%，但其他月内相位明显较弱，不能泛化为所有月度调仓都有效。
- 同周期Q5对成分等权的九项比较区间均跨零；缓冲降低换手，却未证明稳定提高收益。
- 固定名单延迟、买卖分解及同日新旧名单检验指向执行路径与新增买入；不支持直接只买不卖或更频繁刷新名单。
- 排除原新增股票后，E1相对同行业替代股票有正向支持；进一步匹配20日涨跌，三模型账户层面区间均跨零，且仅覆盖约57%—61%的新增预算。不能断言全部优势被风格解释。
- 后续优先冻结简单基线与模型方案进行独立确认，不继续在同一历史上搜索最优日历／阈值。尚未开展真实前瞻；暂不处理数据缺口。

后续详细报告：

1. [等权对照、月度相位与缓冲](reports/q5_controls_phases_buffers_20261116/REPORT.html)
2. [相位来源与固定名单延迟](reports/q5_phase_investigation_20261116/REPORT.html)
3. [买卖分解与信号年龄](reports/q5_trade_leg_investigation_20261116/REPORT.html)
4. [新增股票匹配与排除自身对照](reports/q5_entry_matched_controls_20261116/REPORT.html)

最新完整测试集26项通过。报告中的独立窗口收益差不是年化收益；原生账户的不同可用终点不直接横向排名。初始发布与后续新增研究分别保留，本次文档更新不表示后续文件已经提交或推送。

## 可复核范围

607 只历史成分，501 个完整周信号，2017 年起准备数据；外层 2021Q1—2026Q4（末季度不完整）。行情截止 2026-10-21。

7 个登记模型；expanding 与 rolling36 各 24 折；E2/E3 各固定 3 个 seed，固定等权组合；48 个 Ridge、288 个最终 LightGBM 模型（另有 288 次内层早停拟合）。没有外层参数搜索。

192 个严格账户分支 = 2 条路径 × 8 个模型/对照 × 3 种成本 × 4 个单因素时钟/窗口设定。全部运行并明确记录估值阻断。另有 32 个主成本停牌估值敏感性账户，不替代严格结果。

`historical_simulated_oos`；真实前瞻始终 `FORWARD_PENDING`。

## 文件与数据

- `configs/protocol.json`、`feature_dictionary.csv`：首次训练前冻结；78 核心 + 12 扩展特征。
- `configs/execution_v2.json`：看过初版执行诊断后登记的停复牌补数版本。
- `configs/valuation_sensitivity.json`：已知停牌估值和折价情景，明确后登记。
- `outputs/fold_predictions/`：长表封存预测；不含未来标签。
- `outputs/manifests/`：数据、模型、预测、消费者和账本的独立哈希。
- `outputs/data_audit/`：逐证券、逐周、单位、执行、权重与缺价清单。
- `outputs/archive/`：初版及修正前的结果，保留失败历史。
- `private/`：原始供应商数据、归一化行情、标签、模型和完整账本。已在本目录 `.gitignore` 排除，不能随公开代码提交。

旧 EP 数据只读，读取的 EP30 文件逐个对照其封存清单 SHA256。任何新的模型或经济参数变更都应登记新版本，不覆盖本轮预测。当前数据缺口不等于 alpha 假说被否定。

## 复核命令

以下命令在本目录执行，依赖版本见 `requirements.txt` / `outputs/manifests/environment.json`。LightGBM 和 OSQP 已隔离安装在 `private/vendor`，其他库来自当前研究环境。凭据仅由采集器读取既有 `.env`，不写入输出。

```bash
OPENBLAS_NUM_THREADS=4 python -m pytest tests -q
OPENBLAS_NUM_THREADS=4 python src/replay_models.py
OPENBLAS_NUM_THREADS=4 python src/audit_delivery.py
```

已封存数据下的重建顺序：

```bash
python src/build_panel.py
python src/execution_status.py
python src/audit_inputs.py
python src/train.py expanding
python src/train.py rolling36
python src/evaluate_ranking.py expanding
python src/evaluate_ranking.py rolling36
python src/backtest.py expanding weekly
python src/backtest.py expanding biweekly
python src/backtest.py expanding delay1
python src/backtest.py rolling36 weekly
python src/suspension_sensitivity.py 0
python src/suspension_sensitivity.py 0.2
python src/ranking_sensitivity.py
python src/summarize.py
python src/replay_models.py
python src/audit_delivery.py
python src/report.py
```

采集器 `acquire_sources.py`、`acquire_members.py`、`acquire_limits.py`、`acquire_suspensions.py` 使用现有权限及可恢复缓存。新的供应商响应不应静默替换已封存输入。首次输入审计后保存的代码清单不在重跑时覆盖。

## 需补齐才能升级的证据

1. 历史指数权重的真实发布时间、精确调样生效及其间权重；并处理新增成分和公司行动，不能用未来月末权重倒填。
2. 海通证券等吸收合并/换股、退市和终值权益流水；不能虚构清仓、永久沿用旧价或无依据归零。
3. 股票前复权代理与完整权益账本、基准计价语义进一步闭合。后续已取得H00300全收益收盘并用于诊断，但不虚构其开盘值，也不把前复权单位当作完整分红／换股权益流水。
4. 独立冻结后的真实前瞻观察。当前未创建任何前瞻任务。

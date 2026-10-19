> **目标修正（2026-10-19）**：此前 R01–R09 完成声明仅适用于旧实验，不能作为当前目标完成证据。当前主线是 1、3、6、12 个日历月上涨/下跌及涨跌幅区间概率，验证概率可信度；策略收益与仓位实验退为历史记录。见 [修正方案](notes/r10_probability_goal.md)。四期限研究实现及可信度判断已完成；结论为尚未证明概率可信，见当前概率报告。

# EP24：A股四期限条件收益概率分布探索

当前活动目标：**概率误差降低20%，方向命中率相对提高20%**，两者同时达到。固定R15基础模型B、相同股票和预测月份，分别检查1/3/6个月。最新完成研究见 **[R47成熟历史学习的概率校准](mature_neural_calibration_report.md)**、**[R46当期股票池概率水平锚定](cohort_probability_anchor_report.md)**、**[R45神经网络强正则化](neural_regularization_report.md)**、**[R44小型神经网络七档概率](neural_probability_models_report.md)**、**[R43标准化分布取消基线混合](scaled_unmixed_report.md)**、**[R42风险标准化的逐期限与共享模型](scaled_horizon_models_report.md)**、**[R41跨期限共享概率模型](shared_horizon_models_report.md)**、**[R40概率评分驱动的森林分裂](probability_loss_forests_report.md)**、**[R39个股历史偏差收缩校准](issuer_calibration_report.md)**、**[R38国内期权成交与持仓结构](option_activity_models_report.md)**、**[R37公告时间、修订及标题信息](guidance_event_models_report.md)**、[R36股东户数水平与变化](holder_count_models_report.md)、[R35训练内秩变换与正则化联合概率](regularized_information_report.md)、[R34联合信息、模型容量与混合比例](joint_information_report.md)、[R33国内景气、通胀与融资信息](domestic_macro_report.md)、[R32历史行业身份、状态与幅度分布](historical_industry_report.md)、[R31财报质量与同季度变化](financial_quality_report.md)、[R30多来源组合与方向校准](diverse_ensemble_report.md)、[R29海外风险、汇率与美债信息](global_risk_report.md)、[R28条件分布森林](conditional_forests_report.md)、[R27融资融券信息消融](margin_information_report.md)、[R26直接方向学习与分层分布](direction_first_models_report.md)、[R25历史联动股票信息](historical_peer_models_report.md)，此前为[R23量价交互、价格路径与模型容量](price_volume_models_report.md)、[R22预序列校准与组合](probability_recalibration_report.md)、[R21市场状态与训练时段](market_time_models_report.md)、[R20盈利输入与预期修正](earnings_revision_report.md)、[R19原始盈利预测](eps_expectations_report.md)、[R18分析师预期](analyst_expectations_report.md)、[R17市场广度](market_information_report.md)和[R16双目标改进](improvement_search_report.md)。已完整评分的167个候选均未达标，包含[R24分位数分布](distribution_shape_report.md)。完成一轮实验不等于达到目标。

补充诊断：[事后市场共同分布极限](shared_distribution_diagnostic.md)。即使事后知道每个月全体股票的真实未来分布，同月同分布的三项概率误差改善仅约5%—16%，九项误差门槛均不足20%；共同方向的理想命中率改善可超过20%。这说明仅改进市场整体预测不足以满足双目标，还需要有效的个股概率差异。该诊断明确使用未来答案，不计为模型、预测成绩或达标证据。R35正则化联合输入实验已完整评分，仍未达到双20%目标。

R36完成户数水平/变化/合并三组、两种原算法六候选，72项20%单项门槛均未通过。极端随机树变化组1/3/6月命中率53.68%/57.18%/49.84%；3月相对B三项误差改善2.21%/0.44%/1.11%，方向相对提高7.42%。相对同算法参考的方向增量三个期限95%区间均跨零。输入检查排除行情覆盖前的比较记录，修正82个测试股票月的年度比较特征，全部样本保留；旧中间运行隔离未计数。127项测试、1152次拟合核验和496800条新预测重建通过。来源见[数据检查](holder_count_data_probe.md)。

R37完成四候选、两种原算法匹配消融，48项20%门槛均未通过。完整公告组合极端随机树1/3/6月命中率52.95%/56.52%/49.43%，相对同算法参考的三个方向增量95%区间均跨零，未见稳定信息增益。14,164条匹配公告覆盖1153/1242只股票，原预测样本全部保留；金额解析未入模。144项测试、768次拟合核验和331,200条新概率重建通过。见[结果](guidance_event_models_report.md)和[来源与边界](company_guidance_data_probe.md)。

R38完成四候选，48项20%门槛全部未通过。新增期权活动多数指标差于同算法对照，未见稳定增益。91个快照、168个标的日和四项月报数值核对通过；固定两交易日滞后，原预测样本全部保留。148项测试、768次成熟训练核验和331,200条新概率重建通过。见[结果](option_activity_models_report.md)、[来源](option_activity_data_probe.md)和[评分前方案](notes/r38_option_activity.md)。

R39完成个股历史方向/七档校准、原B/极端随机树两组原分布四候选，48项20%门槛均未通过。相对各自原对照，36项概率误差点估计全部变差；极端随机树七档版6月命中率49.65%→51.00%，但1/3月命中率及6月个股排序变弱，不支持替换原模型。153项测试、384组成熟历史校准核验和331,200条新概率重建通过。见[结果](issuer_calibration_report.md)和[评分前方案](notes/r39_issuer_calibration.md)。

R40完成有序/联合概率损失、独立/混合四候选，48项20%门槛均未通过。联合混合版1/3/6月命中率53.42%/57.48%/51.06%；6月方向较原分类森林增加1.41个百分点，95%区间+0.49至+2.36，但三项概率增量区间均跨零，且早段误差反而变差。158项测试、384次成熟训练/损失/叶概率核验和331,200条新概率重建通过。见[结果](probability_loss_forests_report.md)和[评分前方案](notes/r40_probability_loss_forests.md)。

R41完成跨期限共享四候选，48项20%门槛均未通过。极端随机树共享1/3/6月使6月三项概率误差较原算法改善0.58%/0.15%/0.30%，配对增量区间均为正，但命中率约49.65%不变，3月命中率56.89%→54.88%。加入12月标签未见稳定增益。162项测试、256次共享拟合、448个期限成熟切片和331,200条新预测重建通过。见[结果](shared_horizon_models_report.md)和[评分前方案](notes/r41_shared_horizon_models.md)。

R42完成风险标准化逐期限/共享四候选，48项20%门槛均未通过。相对结构匹配原尺度版本，五档Brier和CRPS全部24个点估计改善，但只有9个区间下界为正，12个方向比较均无正增量区间下界。极端随机树逐期限版1/3/6月命中率53.77%/56.88%/50.07%，相对原B各概率指标改善均不足2%。166项测试、512次拟合、768个成熟切片和331,200条预测核验通过。见[结果](scaled_horizon_models_report.md)和[评分前方案](notes/r42_scaled_horizon_models.md)。

R43完成取消混合四候选，48项20%门槛均未通过。相对各自混合版，五档Brier和CRPS全部24个点估计变差；极端随机树共享独立版6月命中率49.56%→53.66%，但1/3月方向及6月五档/CRPS变差。8项相关测试、512份原缓存哈希、331,200条旧混合和331,200条新独立预测重建及混合恒等式通过；没有新拟合。见[结果](scaled_unmixed_report.md)和[评分前方案](notes/r43_scaled_unmixed.md)。

R47完成成熟历史校准四候选，48项20%门槛均未通过。独立方向校准1月命中率56.60%（对B相对+8.89%），但五档误差仍变差，对原网络方向增量区间跨零；3/6月三项误差均变差，6月四候选上涨及五档Brier对自身源的退化区间均为负。180项测试、584次有效拟合、768次成熟历史核验及331,200条重建通过；76,188条预热预测逐值原样并全部参与验收。见[结果](mature_neural_calibration_report.md)和[评分前方案](notes/r47_mature_neural_calibration.md)。

R46完成当期原B总体概率锚定四候选，48项20%门槛均未通过。方向版严格保留每月条件上涨AUC，但独立方向版6月命中率51.58%（对B相对+3.11%）、三项误差仅改善0.46%/0.14%/0.11%，自身参考增量区间均跨零；同一候选1/3月命中率反而降低。176项测试、768份校准及331,200条预测重建通过。见[结果](cohort_probability_anchor_report.md)和[评分前方案](notes/r46_cohort_probability_anchor.md)。

R45完成强正则化四候选，48项20%门槛均未通过。alpha=16独立版1月命中率54.50%（对B相对+4.85%），但五档误差仍变差；3月虽修复R44的部分误差，对原B三项误差仍变差；6月四候选命中率均低于50%。月内排序与总体概率水平出现分离，不能以排序点估计替代双目标。171项测试、384次成熟训练/输入一致性/参数前向核验及331,200条重建通过；固定60轮未确认收敛。见[结果](neural_regularization_report.md)和[评分前方案](notes/r45_neural_regularization.md)。

R44完成小型神经网络四候选，48项20%门槛均未通过。原输入混合版1月命中率54.41%、三项误差较原B改善1.35%/1.26%/1.59%，但3/6月三项误差全部变差；联合输入及独立版表现更差。169项测试、384次成熟训练/秩设计/网络前向核验及331,200条预测重建通过。固定60轮并记录384条迭代上限提示，未声称优化收敛。见[结果](neural_probability_models_report.md)和[评分前方案](notes/r44_neural_probability_models.md)。

R35完成原38项/联合131项、两档L2强度与独立/混合分布八个候选，96项20%单项门槛均未通过。C=1相对C=10的36个概率评分对照中35个点估计更好，但八候选6个月三项概率误差全部差于B。原输入C=1独立版1月命中率51.98%→54.16%，3月53.23%→52.42%；6月50.02%→50.72%，上涨Brier却恶化4.50%。1月命中率增益主要在2024年后，早段方向反而下降。122项测试、768次成熟训练/变换/系数核验及662400条新预测重建通过。

R34将七组93项输入与原38项控制合并为131项，完成同容量对照和独立/混合分布共7个新增候选，84个20%单项门槛全部未通过。联合混合模型在两种容量、三个期限的三项概率误差均差于各自同容量控制；浅层3月命中率54.30%→50.15%。本轮6月命中率最高为未增加联合输入的浅层独立模型52.60%，相对B提高5.14%，三项概率误差改善1.43%/0.50%/0.79%，仍未达标。118项测试、576次新拟合时点核验及579600条新预测重建通过。目标保持active。

R33加入14项国内景气/通胀/融资特征，两种原算法六组消融，72个单项20%门槛均未通过。极端随机树融资组1月命中率52.78%→53.42%（同算法对照），增益主要来自2024年后；3月56.89%→55.18%、6月49.65%→48.81%。全部88个月覆盖、114项测试及496800条预测重建通过。采用统计月末45天后的保守可用假设，实际观测年龄54—62天；不能消除后续修订和社融统计范围变化风险。扩大核对发现一个未入模贷款分项的明显不一致，已收紧口径结论，未修改输入、样本或模型。

R32取得19期公开历史行业分类PDF，身份覆盖99.64%、同行走势覆盖83.43%；23.34%的测试股票月使用超过一年未更新的最后已知分类，最长811天。三个新增候选36个单项20%门槛全部未通过。行业身份6月命中率49.32%→50.00%（同算法对照），仍未超过B50.02%；1/3月方向下降。110项测试、248400条新预测重建、公开发布日期/历史前缀与类别幅度回退核验通过。历史行业数据可用不等于预测有效。

R31新增基础财报、质量水平和同季度年度变化三组输入，在两种固定算法上完成6组消融，72个20%单项门槛全部未通过。完整财报组的极端随机树3月命中率56.94%，同算法对照56.89%，仅提高约0.05个百分点且三项概率误差略差；6月最高命中率49.92%，仍低于B的50.02%。测试财报新鲜度窗口覆盖54.43%，扣非ROE仅12.52%，缺失行全部保留。104项测试、1152次拟合时点/填补核验及662400条候选与对照预测重建通过。两对照统一使用精确B，方向判断无变化。

R30完成七条不同来源的完整分布组合、三项概率误差联合优化与方向校准，共5个候选，60个20%门槛均未通过。等权组合6月命中率50.02%→52.30%（相对+4.56%），上涨Brier/五档/CRPS改善1.56%/0.50%/0.79%；学习权重和方向校准未带来稳定增益。584次有效元模型拟合按当时成熟历史重跑，全部414000条预测重建，76188条早期回退记录逐值保留，99项测试通过。另发现原B的float32缓存仅影响1条分档概率；已按原算法恢复float64分布，与冻结报告全部评分逐项完全一致，原报告/旧缓存不改，方向判断无变化。

R29新增12项海外风险/利率汇率信息，覆盖全部88个月及原27,600测试股票月，在两种原算法上完成6组消融，72个20%单项门槛均未通过。极端随机树加利率汇率的3月命中率56.66%，低于同算法原对照56.89%；6月命中率49.65%→50.37%，相对原B50.02%仍只有小幅改善。海外风险组未呈现稳定增益。93项测试、全部496800条新预测重建、原始来源与历史前缀核验通过。美联储汇率按周发布，采用14天保守滞后，未将观测日期冒充发布日期。

R28完成随机森林/极端随机树及档内分布局部化6个新候选，72个20%单项门槛均未通过。极端随机树局部混合版3月命中率53.23%→56.89%（相对+6.87%），上涨Brier/五档/CRPS改善1.83%/0.40%/1.01%；6月命中率反而略低于B。3月改善主要来自2024年以后，早段仍略弱于B。89项测试、所有496800条新预测重建及叶内质量/训练内填补核验通过；局部与全局幅度版本方向边际逐值一致。

R27完成89个月公开两融快照与3个新增候选，36个20%单项门槛均未通过。原测试样本明细覆盖96.49%，未删去缺失样本。3月个股两融命中率54.09%，低于同参数对照54.30%；6月市场两融上涨Brier相对B改善1.58%，但命中率50.02%→49.44%。84项测试、全部248400条新预测重建及源数据/时点/单位/特征独立复算通过，目标保持active。

R25四候选三期限评分完成，48个20%单项门槛均未通过。1月当日联动版本命中率52.50%，相对自身动量对照51.59%提高0.91个百分点，但相对旧R23参考52.44%仅高0.06个百分点，概率误差仍差于B。6月加入两种联动信息均使三项概率误差比自身动量对照更差。75项测试及全部331200条新预测重建核验通过；没有把输入覆盖率约94%当成预测有效。

R23完成6个同样本候选，新增16个量价/路径特征，并设置两种容量的匹配对照。浅层全部特征模型6月上涨Brier/五档/CRPS改善1.41%/0.59%/0.85%，方向命中率却从50.02%降至48.80%；提高容量未带来同步优势。同容量6月新增特征增量小，配对区间跨零。65项测试通过，全部预测概率重建、源文件哈希和历史特征前缀核验完成。目标保持active。

R24已完成：[分位数分布与风险标准化完整结果](distribution_shape_report.md)。6候选三期限72个20%门槛均未通过。独立直接分位数6月命中率相对提高2.29%，但上涨Brier恶化3.87%；名义90%区间在1/3/6月实际覆盖82.76%/83.35%/82.46%。风险标准化未带来同步优势。评分前的年化单位错误已修正，错误缓存隔离，三只真实股票单位核验及全部496800条新预测重建通过。

R26已完成：[直接方向学习与分层分布结果](direction_first_models_report.md)。4候选48个20%门槛均未通过。独立方向重加权6月命中率50.02%→53.49%（相对+6.93%），上涨Brier/五档/CRPS改善1.41%/0.40%/0.76%；1/3月命中率下降，6月前后阶段差异明显。79项测试及全部331200条新预测重建通过，两个幅度结构的方向边际和决策逐值一致，没有调整方向阈值。

R22完成4种仅用已到期旧预测的校准、固定平均及学习组合。校准多数概率评分变差；学习组合6月方向相对改善2.72%，概率评分改善不足1%。584个有效校准拟合均完成时点/概率重建核验，61项测试通过。

R21完成市场输入、月份平衡、36月窗口、24月衰减及匹配对照6个新候选。3月市场状态/月等权模型方向相对改善2.29%、上涨Brier降低1.27%，但其他期限没有同步优势。早晚阶段反向变化明显。57项测试与全量窗口/权重/概率缓存重建核验通过；下一步待检验仅用已到期预测的校准。

R20完成6个新候选及逐值复用的R19参考。增长预期修正覆盖26.2%；同覆盖6月方向命中率从无盈利51.47%、加盈利51.59%到加修正51.76%，增量很小。全量覆盖及取消混合未达到目标。同月排序略有信息，但市场整体方向和校准仍弱。54项测试与全量技术核验通过。

R19已完成14,571篇原文获取、全量复核和5组同样本实验。EPS预测覆盖37.2%的测试股票月，加归母净利润代理后覆盖61.3%；来源替换增量很小。浅层分类6月方向命中率相对改善3.13%，概率评分改善均不足1%，未达标。过程见[方案与数据核验](notes/r19_eps_expectations.md)。

此前追加：**[信用利差、PE分位、前瞻收益率三因素消融（R15）](three_factor_ablation_report.md)**。1/3/6月、8组合、同样本逐月重训；前瞻收益率为历史盈利/估值情景代理。核验见 `outputs/r15_three_factor_ablation/completion_audit.json`。

此前追加：**[1、3、6个月 Walk-forward 验证（R14）](walk_forward_report.md)**。按月重训与冻结预测新增到期补验均已完成；核验见 `outputs/r14_completion_audit.json`。

历史状态：四期限探索性实验、当前输入示例与可信度判断已完成。R10 已补齐 1/3/6/12 个日历月；R11 检验只使用已到期预测的概率校准；R12 直接分类对照。这些历史完成记录不构成当前20%改进目标的完成证据。

- **[当前股票四期限概率与可信度示例](current_probability_example.md)**
- **[四期限概率研究报告](probability_research_report.md)**
- [旧 R01–R09 报告（历史记录）](EP24_research_report.md)
- [整体方案](research_plan.md)
- [原始讨论](notes/original_discussion_20261019.txt)
- [逐轮发现与下一问题](notes/round_log.md)
- [数据缺口及处置](notes/data_gaps.md)
- 数据核验：`outputs/data_audit.json`、`price_coverage.csv`、`missing_by_year.csv`
- 实验结果：`outputs/r01_price_pilot/` 至 `outputs/r09_total_return_sensitivity/`
- 历史预测输出示例：`outputs/report/historical_prediction_example.json`，包含上涨/跑赢基准/收益阈值概率与尾部分位点；不是当前投资信号。

## 复跑

从 `topics/02_AFML_BIG_WINNER` 目录执行；使用已有 `.venv`，增加依赖见 `requirements.txt`。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/prepare_panel.py"
.venv/bin/python "$EP/src/run_price_pilot.py"
.venv/bin/python "$EP/src/run_calibration_probe.py"
.venv/bin/python -m pytest -q "$EP/tests"
```

R17追加命令（复用R16冻结目标与R15分布缓存）：

```bash
.venv/bin/python "$EP/src/build_market_breadth.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_market_information.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_market_breadth import DEST; evaluate(DEST)"
.venv/bin/python "$EP/src/report_market_information.py"
```

公开预告版本复核：`src/probe_earnings_vintages.py`，优先复用原响应缓存；单份原始研报核验见`outputs/r17_market_information/historical_analyst_forecast_example.json`，尚非批量预测面板。

R18追加命令（下载器默认单连接低速、优先复用缓存；完整年份才构建因子）：

```bash
.venv/bin/python "$EP/src/fetch_historical_reports.py"
.venv/bin/python "$EP/src/build_analyst_features.py"
.venv/bin/python "$EP/src/analyze_analyst_coverage.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_analyst_expectations.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from fetch_historical_reports import DEST; evaluate(DEST)"
.venv/bin/python "$EP/src/report_analyst_expectations.py"
```

公开数据读取需网络；按本地缓存断点续传，不改上游数据：

```bash
.venv/bin/python "$EP/src/fetch_valuation.py"
.venv/bin/python "$EP/src/fetch_financials.py"
.venv/bin/python "$EP/src/fetch_yields.py"
.venv/bin/python "$EP/src/enrich_panel.py"
.venv/bin/python "$EP/src/run_information_probe.py"
.venv/bin/python "$EP/src/compare_information.py"
.venv/bin/python "$EP/src/run_peer_probe.py"
.venv/bin/python "$EP/src/run_holdout.py"
.venv/bin/python "$EP/src/run_portfolio_probe.py"
.venv/bin/python "$EP/src/run_sensitivities.py"
.venv/bin/python "$EP/src/run_holdout.py" --target excess
.venv/bin/python "$EP/src/fetch_corporate_actions.py"
.venv/bin/python "$EP/src/check_total_returns.py"
.venv/bin/python "$EP/src/build_research_figures.py"
.venv/bin/python "$EP/src/build_final_report.py"
.venv/bin/python "$EP/src/audit_completion.py"
```

原始下载和月度面板保存在已被仓库忽略的 `outputs/local_cache/`，不复制进正式历史数据。尚未原生验证总收益口径、历史行业、完整无偏股票池或财报初始版本。研究所用 126/252 交易日是 6/12 个月近似。

每个模型只使用预测时已经兑现的标签。2021—2023 为探索阶段；2024以后R05按事先记录的规则评分，R07—R09是看到结果后追加的诊断，不重复宣称独立验证。

精确复跑需要保留当前原始缓存和月度面板。公开接口现时返回的历史数据可能修订；重新下载后应重新核验来源与差异，不能默认与本轮字节一致。收益主实验使用复权代理，R09补充独立分红送转再投资敏感性；不声称完整解决配股、特殊重整及全部公司行动。

## 当前主线复跑

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/run_four_horizons.py"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/run_direct_probability.py"
.venv/bin/python "$EP/src/calibrate_four_horizons.py"
.venv/bin/python "$EP/src/evaluate_four_horizons.py"
.venv/bin/python "$EP/src/report_four_horizons.py"
.venv/bin/python "$EP/src/predict_probability.py" --stock SH600000 --asof 2026-04-30 --model peers_full
```

预测入口要求精确日期，历史行情不可当作今天。当前概率输出和检验在 `outputs/r10_four_horizons/`；大规模分布缓存置于被忽略的 `outputs/local_cache/r10_distributions/`。

当前快照预测入口见 `src/fetch_current_snapshot.py`、`src/predict_from_snapshot.py`；独立的概率目标核验见 `outputs/r10_four_horizons/probability_scope_audit.json`。该核验确认研究交付完整，不把负面的可信度判断变成预测优势。训练面板时效、原始数据版本与全市场覆盖限制仍保留。

## R16双目标探索复跑

依赖已完成的R15共同面板及冻结预测；保持`target_contract.json`不变。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/diagnose_prediction_target.py"
.venv/bin/python "$EP/src/build_improvement_features.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_improvement_round1.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_market_residual_search.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_prequential_search.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_rank_residual_search.py"
.venv/bin/python "$EP/src/evaluate_improvement_search.py" --round round1
.venv/bin/python "$EP/src/evaluate_improvement_search.py" --round market_residual
.venv/bin/python "$EP/src/evaluate_improvement_search.py" --round prequential
.venv/bin/python "$EP/src/evaluate_improvement_search.py" --round rank_residual
.venv/bin/python "$EP/src/report_improvement_search.py"
.venv/bin/python -m pytest -q "$EP/tests"
```

## R23量价与价格路径复跑

复用原日线、R21市场面板和冻结B缓存，不重新下载历史数据。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/build_price_volume_features.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_price_volume_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_price_volume_features import DEST; evaluate(DEST)"
.venv/bin/python "$EP/src/report_price_volume_models.py"
```

## R24分位数分布复跑

依赖R23面板、参考预测和冻结B缓存；不要在已有训练进程仍运行时重复启动。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_distribution_shape_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from run_distribution_shape_models import DEST; evaluate(DEST)"
.venv/bin/python "$EP/src/report_distribution_shape_models.py"
```

## R25历史联动股票消融复跑

[事前方案](notes/r25_historical_peers.md)：固定自身动量对照及两种历史形成窗口，共4候选。112个月完整特征面板、1647个源文件、112000成员行、全部形成时点和真实前缀重建核验通过，原预测人群不变；75项测试通过。三期限训练、评分及概率/评分全量重建均完成，仍未达标。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/build_historical_peers.py"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/audit_historical_peer_features.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_historical_peer_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_historical_peers import DEST; evaluate(DEST)"
.venv/bin/python "$EP/src/report_historical_peer_models.py"
```

## R26直接方向模型复跑

复用R25自身动量对照的冻结分布及同38个输入，计划与源文件哈希保持一致。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_direction_first_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from run_direction_first_models import DEST; evaluate(DEST)"
.venv/bin/python "$EP/src/report_direction_first_models.py"
```

## R27融资融券信息复跑

[事前方案](notes/r27_margin_information.md)。公开交易所数据只读下载，可复用完整缓存；深市个股使用精确Excel，并核验网页日期、记录数和展示单位。三个新增消融与原样自身动量对照比较。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/build_margin_information.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_margin_information_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_margin_information import DEST; evaluate(DEST)"
.venv/bin/python "$EP/src/report_margin_information_models.py"
```

## R28条件分布森林复跑

[事前方案](notes/r28_conditional_forests.md)。复用R25的原38项输入，六个固定候选。当前sklearn 1.9抽样权重语义已经核验；换版本必须重新确认，不能把抽样权重重复乘进叶节点。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_conditional_forests.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from run_conditional_forests import DEST; evaluate(DEST)"
.venv/bin/python "$EP/src/report_conditional_forests.py"
```

## R29海外风险与宏观信息复跑

[事前方案与来源](notes/r29_global_risk.md)。FRED下载超时后改用可访问的Cboe、美联储历史表、财政部XML及新浪公开纳指行情。缓存优先，原始数据与来源凭证保留。滞后是假设，尚非原始历史版本认证。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/download_global_risk.py"
.venv/bin/python "$EP/src/build_global_risk.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_global_risk_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_global_risk import DEST; evaluate(DEST)"
.venv/bin/python "$EP/src/report_global_risk.py"
```

## R30多来源组合复跑

[事前方案](notes/r30_diverse_ensemble.md)。固定七组件、五个正式候选；只用当时已到期的旧预测学习，原样保留早期等权回退。精度恢复另存新缓存，不覆盖R15的预测或原缓存。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/recover_baseline_precision.py"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/prepare_diverse_sources.py"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/run_diverse_ensemble.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from prepare_diverse_sources import DEST; evaluate(DEST)"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/report_diverse_ensemble.py"
```

## R31财报质量与年度变化复跑

[评分前方案](notes/r31_financial_quality.md)。沿用已缓存的公开财报，三组嵌套输入、两种固定算法。新增字段按456天新鲜度规则置缺失，保留原样本；对照与新增模型统一使用R30恢复的精确B。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/build_financial_quality.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_financial_quality_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_financial_quality import DEST; evaluate(DEST)"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/report_financial_quality.py"
```

## R32历史行业信息复跑

[评分前方案](notes/r32_historical_industry.md)。公开协会分类表保留发布日期和原始PDF；跨2021—2023发布空档明确标记陈旧分类。仅使用当时历史研究池构建同行状态。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/download_historical_industry.py"
.venv/bin/python "$EP/src/parse_historical_industry.py"
.venv/bin/python "$EP/src/build_historical_industry.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_historical_industry_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_historical_industry import DEST; evaluate(DEST)"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/report_historical_industry.py"
```

## R33国内宏观信息复跑

[评分前方案](notes/r33_domestic_macro.md)、[社融口径澄清](notes/r33_data_semantics.md)。PMI、CPI/PPI、M2与商务部社融增量公开序列；统一按统计月末45天以后可用，仍保留历史修订和统计范围变化限制。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/download_domestic_macro.py"
.venv/bin/python "$EP/src/build_domestic_macro.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_domestic_macro_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_domestic_macro import DEST; evaluate(DEST)"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/report_domestic_macro.py"
```

## R34联合信息与容量复跑

[评分前方案](notes/r34_joint_information.md)。七组已审查输入与38项控制合并为131项。相同数据、两套固定容量，完整保留独立和50%B混合预测；原样参考复用R31，浅层控制概率复用R25。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/build_joint_information.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_joint_information.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_joint_information import DEST; evaluate(DEST)"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/report_joint_information.py"
```

## R35训练内秩变换与正则化复跑

[评分前方案](notes/r35_regularized_information.md)。原38项与联合131项、C=1/10、独立及50%B混合八个候选。每个成熟训练月总权重1，变换仅使用训练样本；两个浅层树参考逐值保留。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_regularized_information.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from run_regularized_information import DEST; evaluate(DEST)"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/report_regularized_information.py"
```

## R36股东户数信息消融复跑

[评分前方案与输入修正](notes/r36_holder_counts.md)。水平/变化/合并三组、两种原算法六候选，原样复用无新增信息参考。原中间运行因上市前比较基数问题中断隔离；正式输入限制到已有行情覆盖期间，未改变样本或目标。

```bash
EP=experiments/pending/24_conditional_return_distribution_exploration
.venv/bin/python "$EP/src/download_holder_counts.py"
.venv/bin/python "$EP/src/verify_holder_count_filings.py"
.venv/bin/python "$EP/src/audit_holder_count_coverage.py"
.venv/bin/python "$EP/src/build_holder_counts.py"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python "$EP/src/run_holder_count_models.py"
.venv/bin/python -c "import sys; sys.path.insert(0, '$EP/src'); from evaluate_improvement_search import evaluate; from build_holder_counts import DEST; evaluate(DEST)"
OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/report_holder_count_models.py"
```

## 归档与复现

本次提交范围、数据保留位置和精确复现边界见[归档说明](notes/publication_scope.md)，文件大小与SHA256见[归档清单](outputs/publication/file_manifest.json)。大体积预测、原始响应与既有缓存保留本地，未随Git上传。

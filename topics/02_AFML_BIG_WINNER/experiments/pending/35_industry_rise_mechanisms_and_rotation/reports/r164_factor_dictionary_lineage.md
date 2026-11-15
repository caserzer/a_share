# R164 因子字典的来源版本与解释附录

## 想验证什么

R163发现当前28条因子定义保留旧来源与轮次，使用者可能把旧数据路径误作已修复输入。本轮保留全部原定义，逐项增加当前研究证据与解释，避免把不同财务、预期或产业变量合并成一个已验证因子。

## 实际修改

新增 `outputs/r164/factor_dictionary.json`，每条包含完整原定义、原顺序、当前状态、当前解释及证据文件路径/哈希/字节数。原R124字典按字节保存为 `original_dictionary.json`。所有28条的理论、公式、方向、行业、经济日、发布日期、可用时间、频率、来源、修订、聚合、缺失与失效条件原样保留。

原 `source` 字段放在 `original_definition` 内，明确属于历史定义；`current_evidence` 是修复后结果或当前限制的证据位置，不能一概当作可直接建模的数据表。共65项引用检查通过，同一文件被多个因子引用不增加独立证据数量。所有条目保留未获预测采用、未认证严格PIT。

## 逐项结果

| 模块 | 因子 | 当前状态 | 解释 |
|---|---|---|---|
| F | mom20/mom60 | repaired_inputs_verified | R130修复面板、R131模型与R132排序分别举证；尚无稳定因子增量或预测采用。 |
| F | vol20 | repaired_inputs_verified | R130修复面板、R131模型与R132排序分别举证；尚无稳定因子增量或预测采用。 |
| F | dd60 | repaired_inputs_verified | R130修复面板、R131模型与R132排序分别举证；尚无稳定因子增量或预测采用。 |
| H | breadth21/breadth63 | repaired_inputs_verified | R130修复面板、R131模型与R132排序分别举证；尚无稳定因子增量或预测采用。 |
| H | turn_rank504 | repaired_inputs_verified | R130修复面板、R131模型与R132排序分别举证；尚无稳定因子增量或预测采用。 |
| G | pe_rank504 | repaired_inputs_verified | R130修复面板、R131模型与R132排序分别举证；尚无稳定因子增量或预测采用。 |
| C | dedt_change | price_repair_followup_pending | 原R03/R07短样本与时钟限制保留；R146的TTM变化不是本因子的修复证据。 |
| C | margin_delta | price_repair_followup_pending | 原R03/R07短样本与时钟限制保留；R146的TTM变化不是本因子的修复证据。 |
| B | industry_spread_inventory | continuous_source_missing | 产品价差/供需库存连续序列未补齐；会计库存和公司现金流不能替代。 |
| D | fixed_fy_eps_revision | replayed_no_adoption | R141修复的是固定财年EPS分支，R162利润值分支另列，不合并称同一实验。 |
| E | fund_etf_allocation | mapping_and_flow_semantics_missing | R125/126定位有限份额端点，但无合格资金流间隔，历史申万映射未认证。 |
| D | same_broker_fixed_FY_profit_revision | replayed_no_adoption | R162利润修正12模型642预测不变；严格母体不足，局部诊断非全行业增量。 |
| A | PMI_M2_prior_sensitivity_interaction | replayed_no_adoption | R158全量宏观敏感度复核；10主比较无通过项，不调窗口。 |
| B | reviewed_company_operating_evidence | case_evidence_not_predictor | 原五公司13观测保留；R149至R154的另10公司材料是单独案例，非严格PIT或连续产业数据。 |
| F | past_excess20/past_excess60 | repaired_inputs_verified | R130修复面板、R131模型与R132排序分别举证；尚无稳定因子增量或预测采用。 |
| F | log_members | repaired_inputs_verified | R130修复面板、R131模型与R132排序分别举证；尚无稳定因子增量或预测采用。 |
| F | typical_member_log_market_cap | replayed_no_adoption | R142规模控制修复并保留微小结果变号，未确立稳定独立增量。 |
| B | china_power_battery_installation_log_yoy | replayed_no_adoption | 完整装车量源不因价格修复改变；R140重放收益/分类，样本与增量限制保留。 |
| E | industry_financing_balance_intensity | replayed_no_adoption | R143融资修复，覆盖母体与模型结果另列，不代表资金因果。 |
| F | market_beta126 | repaired_controls_not_full_style | R133/R135/R136重放共同控制与退出，仍非完整风格控制或有效择时。 |
| F | residual_vol126 | repaired_controls_not_full_style | R133/R135/R136重放共同控制与退出，仍非完整风格控制或有效择时。 |
| B | long_asset_cash_spending_yoy_direction | repaired_accounting_evidence | R147修复会计母体；R154明确现金流与归母利润方向比较不是利润现金含量比率或因果。 |
| B | inventory_turnover_days_yoy_evidence | repaired_accounting_evidence | R147修复会计母体；R154明确现金流与归母利润方向比较不是利润现金含量比率或因果。 |
| B/C | capital_cashflow_profit_joint_evidence | repaired_accounting_evidence | R147修复会计母体；R154明确现金流与归母利润方向比较不是利润现金含量比率或因果。 |
| H | prior_ranked_leader_follower_return_spread | replayed_no_adoption | R145重放事前规模龙头/跟随者，未获得稳定独立增量，停止变体搜索。 |
| G/C | price_pe_implied_earnings_decomposition | basis_diagnostic_not_economic_attribution | 价格/PE/股本恒等与财务口径核验保留；不能代替现金流驱动证据。 |
| C/G | reported_ttm_vs_pe_implied_profit_diagnostic | basis_diagnostic_not_economic_attribution | 价格/PE/股本恒等与财务口径核验保留；不能代替现金流驱动证据。 |
| C | consecutive_reported_ttm_bounded_change | replayed_no_adoption | R146重放TTM盈利变化；模型结果不变，严格覆盖及二元任务样本不足。 |

## 这次核对揭示的实际遗漏

扣非利润变化 `dedt_change`、利润率变化 `margin_delta` 仍只有R03/R07的短样本和时钟诊断。后来的TTM盈利变化定义不同，R146修复不能代替这两项。它们明确标为 `price_repair_followup_pending`，而不是宣称全部财务变量都已复核；后续可保持原口径，用R130面板完成必要传导比较。

产品价差/产业库存连续序列仍缺；会计库存周转天数、资本支出、公司经营现金流和产品库存不能相互替代。原五公司13条观测与新增10公司财报案例也分别解释，不扩大为连续行业历史。

ETF份额有限端点已经找到，但历史映射和公司行动解释仍不足；字典从“未接入”进一步说明具体障碍，不制造资金流变量。EPS修正与利润值修正分别引用R141、R162，不用一个分支的核验覆盖另一个。

## 为什么不代表因子有效

来源路径与结论更新不增加领先信息或因果证据。价格、预期、宏观、融资、龙头和财务分支的负结果与样本不足均保留；没有改变阈值、权重、模型或标签。成本后配置、实际可交易性、完整风格控制和独立前瞻仍需分别检验。28条研究定义也不等于28个有效因子，更不等于方正69项完整复现。

## 使用与验证

优先阅读本附录判断当前研究证据，再查看内嵌原定义了解公式与时钟。R157默认研究入口仍保持原状，本轮附录独立定位，不覆盖历史注册槽位。协议 `protocols/r164.json`；生成 `src/dictionary_lineage_r164.py`；验证 `src/verify_dictionary_lineage_r164.py`。

验证器逐项确认28条原定义完整相等、必需字段存在、映射覆盖完整、65项当前文件哈希及字节数一致，并明确核查两个不同财务因子的待复核状态。整体目标仍未完成；下一项应执行这些已定位的必要比较，而不是把元数据整理当作研究成功。

# EP38 沪深300周度至月度选股研究总览

截至2026年11月23日，共完成133轮。研究已暂停。**尚无一条新增规则同时展示稳定的整组合扣费增量，并获得真正前瞻收益验证。** 唯一冻结作前瞻观察的是第16轮的三级行业观察池换股规则。其名单历史重放已核对，新增前瞻预测为0，到期前瞻窗口也为0。后续历史复核下调了对它的评价。[研究目标](GOAL.md) · [冻结规则](forward/industry_pool_v1/PROTOCOL.md) · [采集核验](forward/industry_pool_v1/capture_verification.json)

## 基线本身赚了多少

原E1用78个特征预测未来十日标准化收益，收益秩模型用相同特征预测收益的横截面排名。默认买入收益秩最高十分组，收盘形成信号，下一交易日开盘成交，十个交易日后到期，连续入选只按差额交易。候选的首要问题是：在同样的钱、日期、可成交条件下，能给这套原方法增加多少净收益？跑赢沪深300全收益指数是另一项检验。[首轮账户与全部基准](REPORT.md)

| 首轮原时钟 | 组合 | 净年化 | 最大回撤 | 指数年化 | 相对指数年化差 |
|---|---|---:|---:|---:|---:|
| 主 | 原 E1 | 2.46% | -37.81% | -5.82% | +8.28 个百分点 |
| 后 | 原 E1 | 9.23% | -21.47% | 9.64% | -0.41 个百分点 |
| 主 | 收益秩 | 5.56% | -34.70% | -5.82% | +11.38 个百分点 |
| 后 | 收益秩 | 7.41% | -14.90% | 9.64% | -2.23 个百分点 |

主段从2021-01-11开盘至2025-03-03开盘，100个非重叠十日窗口；后段至2026-10-12开盘，39个。后续部分实验补入2018、2019、2020年及全部十个换仓起点。不同起点使用重叠行情。指数用收盘端点，模型间比较用相同开盘端点。普通费用为买入10、卖出20 bp，双费为20、40 bp，1 bp 等于0.01个百分点。下文未另注明的主后段配对差以整组合每十日为单位。事件金额、月均差、年化差分别标出；各轮收益不可相加。[账户口径](REPORT.md) · [公司行动与连续账本](rounds/26_merger_continuity/REPORT.md)

## 最接近可用的四条线索

| 路线 | 为什么曾值得继续 | 哪次检验改变了判断 | 当前结论 |
|---|---|---|---|
| 三级行业观察池换股 | 少量替换即可在原时钟主、后段分别多3.69、0.93 bp；平移五日仍多0.79、1.62 bp。原时钟连续139期净年化6.95%，收益秩6.14%。 | 补齐另外八个起点后，主、后段平均只多0.10、少0.10 bp；去各段最好三个月后月均少2.14、6.19 bp。 | 保留原规则影子观察，尚无前瞻结果。[起点挑战](rounds/38_all_phases/REPORT.md) |
| 训练时暂缓纳入最近数据 | 同样训练十日标签，仅去掉最近十个交易日的训练样本，主、后段多2.42、5.88 bp。 | 单改行业席位就能解释大半近期增量；放回2019、2020年，席位改动分别多0.40、少0.83 bp。 | 保留为训练样本和行业配置效应，证据不足以更换生产模型。[交叉账户](rounds/54_industry_seats/REPORT.md) · [早年复核](rounds/55_earlier_seats/REPORT.md) |
| 财务和股东信息分配已有资金 | 利润率改善在原持仓四段均有正增量；股东户数收缩分配新增买单，五段中四段扣费为正。 | 利润率剔除最佳三股后仅2020年月均仍正；户数规则主段去最佳三股后从+0.83降至−1.29 bp/月，后段从+3.71降至+0.84。 | 两条公司特征均保留历史结果；现有资金收益不足以升级。[利润率归因](rounds/89_peer_trade_attribution/REPORT.md) · [户数归因](rounds/123_holder_issuer_attribution/REPORT.md) |
| 推迟尚未持续领先的新股换入 | 等到中点确认才换，主段多3.22 bp；932对触发，929对实际成交。 | 后段仍比原组合少0.05 bp。同额均匀换入已能实现大部分表现，动态选择相对它主、后段只多0.37、0.22 bp，两个区间均跨零。 | 有节省换手的价值，未取得稳定的新增选股收益。[逐对成交](rounds/132_crossing_midpoint_orders/REPORT.md) · [同额对照](rounds/133_midpoint_matched_orders/REPORT.md) |

## 其余实验共同解释了什么

- **全池排序有用，最高组内部的仓位却很难再优化。** 用全池分数继续给已入选股加权，主后段分别少1.63和4.04 bp。避开模型预测的左尾确实降低了后来跌入左尾的资金比例，但同时卖掉了右尾机会。行业、市值和指数权重也会改变基准结果：第60轮后段选股相对合格等权池有27.23 bp毛差，费用消耗20.76 bp，而等权池自身已经落后指数9.16 bp。[持仓内部排序](rounds/42_within_top/REPORT.md) · [尾部预测](rounds/43_tail_targets/REPORT.md) · [基准分解](rounds/60_benchmark_bridge/REPORT.md)
- **公告可以引起显著的个股反应，可部署资金可能很少。** 解禁公告的部分年份、月份有很大的四腿事件净差，放回真实底仓却只改变2,069个信号日中的144日，触发日平均转移0.117%资金。最后主、后段每十日只多0.0179、少0.0115 bp。扣非财务数据的另一类问题是覆盖：严格取当时可得日期，早年许多窗口没有可用输入。[事件归入底仓](rounds/97_unlock_portfolio/REPORT.md) · [财务覆盖](rounds/14_core_earnings/results/coverage.csv)
- **价格路径的可重复毛差，常被成本、资金占用或阶段反向吃掉。** 2017年成交均价同行配对十日毛差为+23.37 bp，计入换仓及恢复底仓后为−36.72 bp；延至二十日仍为负。延迟卖股若只看旧股，五段均有正贡献；同步推迟靠卖股现金购买的新股之后，主段为−0.13 bp/月。入选频率、同行补涨、上涨均匀度与涨幅出现时点也分别经过早年、镜像或同资金对照，均未形成可升级规则。[成交均价](rounds/107_vwap_early_challenge/REPORT.md) · [现金机会成本](rounds/114_funded_delay/REPORT.md) · [上涨时点](rounds/127_early_entry_orders/REPORT.md)
- **研究留下了可复用的交易账本。** 合并换股、停牌、受限订单、现金、实际费用、逐股逐月贡献都能影响结论。原行业候选四套名单在276个日期重放，31,892条股票权重全部吻合；1亿元限量成交情景下仍留下约7.92%现金。历史可重放、实际可部署规模、事前登记后的收益应分别评价。[前瞻采集回执](forward/industry_pool_v1/capture_verification.json) · [限量成交](rounds/28_partial_execution/REPORT.md)

## 第1–133轮逐项结果

每行是一轮研究的主要问题、结果及原始入口。早期没有独立报告的轮次同时链接方案和结果目录。反复在同一批历史上提出新问题，意味着这里的133轮不能视为133次独立验证。[完整迭代记录](RESEARCH_LOG.md)

### 1–15　基线、预测时效与业绩公告

| 轮次 | 检验的问题 | 结果和取舍 |
|---:|---|---|
| 1 | [两模型混合、行业内低波动](REPORT.md) | 低波动主段少3.28、后段多4.60 bp；混合规则也未稳定改善原收益秩。 |
| 2 | [模型切换与研报利润下修](rounds/02_adaptive_revision/PROTOCOL.md) · [结果](rounds/02_adaptive_revision/results/) | 按已到期表现切换模型只猜对44/92和24/38次；研报下修平均只动用约3%至4%资金。 |
| 3 | [换手推算成本](rounds/03_cost_basis/PROTOCOL.md) · [结果](rounds/03_cost_basis/results/) | 按成交成本位置调权，两段分别少1.9和8.1 bp，转向较早年份检验反向解释。 |
| 4 | [价格位置反向验证](rounds/04_price_location_falsification/PROTOCOL.md) · [结果](rounds/04_price_location_falsification/results/) | 早期84个窗口的残差秩相关为−0.0257，取反解释未获支持。 |
| 5 | [跨周评分确认](rounds/05_signal_persistence/PROTOCOL.md) · [结果](rounds/05_signal_persistence/results/) | 新旧收益秩各半，两段少7.8和15.0 bp；旧分稀释了当前信息。 |
| 6 | [持仓中点重选](rounds/06_midwindow_refresh/PROTOCOL.md) · [结果](rounds/06_midwindow_refresh/results/) | 第六日开盘刷新，主段少11.97、后段多19.40 bp；主段毛优势不足以付费。 |
| 7 | [换股门槛](rounds/07_marginal_refresh/PROTOCOL.md) · [结果](rounds/07_marginal_refresh/results/) | 用成熟配对估算毛差并要求超过30 bp，主段仅执行2对且均为强制替换；后段双费转负。 |
| 8 | [只用当天收盘的新周榜](rounds/08_same_close/PROTOCOL.md) · [结果](rounds/08_same_close/results/) | 46次更新，主段少3.03、后段多13.81 bp；后段去最佳三月转负。 |
| 9 | [五日训练标签](rounds/09_horizon_target/PROTOCOL.md) · [结果](rounds/09_horizon_target/results/) | 同训练行、同成交机会下，H5标签两段均落后直接H10标签对照。 |
| 10 | [业绩预告价格反应](rounds/10_guidance_reaction/PROTOCOL.md) · [结果](rounds/10_guidance_reaction/results/) | 负向反应股随后弱于同行，但放进账户只改变约1%至2%资金，两段约多0.7、少2.5 bp。 |
| 11 | [公告后立即替换](rounds/11_event_time_risk/PROTOCOL.md) · [结果](rounds/11_event_time_risk/results/) | 原持仓实际触发主段25笔、后段2笔，无法支持稳定的账户结论。 |
| 12 | [借指数底仓做事件换股](rounds/12_index_event_budget/PROTOCOL.md) · [结果](rounds/12_index_event_budget/results/) | 计入换股与买回四笔费用，按已投入资金算早期亏、主后段赚；删最佳月份后后段反向。 |
| 13 | [按指数权重分组](rounds/13_index_weight_interaction/PROTOCOL.md) · [结果](rounds/13_index_weight_interaction/results/) | 低权重组早、主、后段单位投入净差分别为−0.79%、−0.41%、+0.23%，无法事前界定有效组。 |
| 14 | [季度扣非利润加速](rounds/14_core_earnings/PROTOCOL.md) · [结果](rounds/14_core_earnings/results/) | 严格公告与更新口径下主段没有可用同行排名；后段仅9个窗口换股，加速度近乎无增量。 |
| 15 | [单独预测行业内排名](rounds/15_peer_target/PROTOCOL.md) · [结果](rounds/15_peer_target/results/) | 固定行业席位，主段少约0.5、后段多约3.6 bp；比相同训练样本的全池目标略优。 |

### 16–30　行业观察池、持有期限及执行容量

| 轮次 | 检验的问题 | 结果和取舍 |
|---:|---|---|
| 16 | [三级行业观察池换股](rounds/16_industry_pool/PROTOCOL.md) · [结果](rounds/16_industry_pool/results/) | 用已发布周目录在同一级行业替换少量买单，原时钟两段均正，成为冻结观察规则。 |
| 17 | [平移五日换仓](rounds/17_calendar_challenge/PROTOCOL.md) · [结果](rounds/17_calendar_challenge/results/) | 移位后主、后段仍多0.79、1.62 bp，但两个起点使用重叠行情。 |
| 18 | [拆分行业与公司贡献](rounds/18_industry_attribution/PROTOCOL.md) · [结果](rounds/18_industry_attribution/results/) | 行业项只在四格之一为正；四个分块区间均含零，收益依赖部分月份。 |
| 19 | [买入端安慰剂](rounds/19_placebo/PROTOCOL.md) · [结果](rounds/19_placebo/results/) | 同业、模型近分的非入池替代股在移位后段更好；原规则冻结作影子观察。 |
| 20 | [卖出端安慰剂](rounds/20_sell_side/PROTOCOL.md) · [结果](rounds/20_sell_side/results/) | 换掉的旧股没有稳定弱于可比留存股，四格去最佳三月均负。 |
| 21 | [买卖两端都能匹配才换](rounds/21_dual_support/PROTOCOL.md) · [结果](rounds/21_dual_support/results/) | 四格都胜安慰剂，但相对原收益秩有一格负、去最佳三月全负，停止此筛选。 |
| 22 | [固定持有二十日](rounds/22_monthly_hold/PROTOCOL.md) · [结果](rounds/22_monthly_hold/results/) | 四格H20净增量从−38.73到+80.39 bp，方向依赖起点，不能统一延长持有。 |
| 23 | [排名前两成留存](rounds/23_rank_buffer/PROTOCOL.md) · [结果](rounds/23_rank_buffer/results/) | 每十日节省约5.15至5.53 bp费用，但四格去最佳三月均负。 |
| 24 | [极端单日上涨](rounds/24_upside_spike/PROTOCOL.md) · [结果](rounds/24_upside_spike/results/) | 早期残差RankIC为+0.0014，未支持极端上涨后减配；移位两段均亏。 |
| 25 | [融资余额增加是否拥挤](rounds/25_margin_demand/PROTOCOL.md) · [结果](rounds/25_margin_demand/results/) | 早期残差RankIC接近零，四格去最佳三月均负，停止月度减配规则。 |
| 26 | [合并换股的连续账本](rounds/26_merger_continuity/REPORT.md) | 计入海通证券换股交付后，原时钟139期观察池净年化6.95%，收益秩6.14%，E1为4.37%。 |
| 27 | [资金规模与成交容量](rounds/27_order_capacity/REPORT.md) | 1亿元情景中1,703笔超过过去日均额1%，缺少集合竞价深度，不能认定实际可成交。 |
| 28 | [限制每次成交数量](rounds/28_partial_execution/REPORT.md) | 1亿元模拟平均留现金7.92%，全期多2.57 bp/十日，后39期少0.11 bp。 |
| 29 | [下跌日放量](rounds/29_down_volume/REPORT.md) | 早期全池没有预期弱势，移位日历两段账户均落后。 |
| 30 | [行业换股只持首周](rounds/30_first_week/REPORT.md) | 两个时钟、两个时段都落后同频再平衡且持满两周的对照。 |

### 31–48　行业机制、现金流、尾部预测与除息

| 轮次 | 检验的问题 | 结果和取舍 |
|---:|---|---|
| 31 | [入池公司当时可见盈利](rounds/31_earnings_attribution/REPORT.md) | 同季度、足够新鲜的扣非改善配对仅8和1个，资料不足以判断机制。 |
| 32 | [随后公布的公司盈利](rounds/32_subsequent_earnings/REPORT.md) | 四格换入股胜出率约39%至53%，未支持其随后普遍改善。 |
| 33 | [同行随后盈利](rounds/33_peer_earnings/REPORT.md) | 剔除换入和对照公司后，其他同行也未显示稳定盈利改善。 |
| 34 | [同行先涨、落后股补涨](rounds/34_peer_catchup/REPORT.md) | 早期全池RankIC为+0.0148，但两个时钟主段的持仓净差均负。 |
| 35 | [经营现金流收益率](rounds/35_operating_cash_yield/REPORT.md) | 控制盈利收益率、行业及市值后，原时钟两段正，移位主段少0.24 bp。 |
| 36 | [现金流收益率变化](rounds/36_cash_yield_change/REPORT.md) | 评分与60日前高度相关，追逐近期改善在移位两段均落后。 |
| 37 | [平滑现金流评分](rounds/37_persistent_cash/REPORT.md) | 相对原等权四格正，但两后段不及同覆盖的当期评分，去最佳三月仅一格仍正。 |
| 38 | [补齐其余八个调仓起点](rounds/38_all_phases/REPORT.md) | 新增八起点相对收益秩的主、后平均仅+0.10、−0.10 bp，行业候选历史证据降级。 |
| 39 | [行业换股时序归因](rounds/39_swap_timing/REPORT.md) | 换入股的主要相对上涨已发生在信号前，可交易的完整十日毛差接近零。 |
| 40 | [延迟至第六日买行业候选](rounds/40_delayed_swap/REPORT.md) | 相对同频收益秩仅+0.06、−0.48 bp，停止延迟方案。 |
| 41 | [十个起点错峰及订单净额](rounds/41_staggered_execution/REPORT.md) | 同时开盘可抵消订单很少，后17个共同月节省为零。 |
| 42 | [在最高组内继续按原分数配权](rounds/42_within_top/REPORT.md) | 主、后段少1.63、4.04 bp；全池排序未直接转化为组内金额配置。 |
| 43 | [训练左右尾模型](rounds/43_tail_targets/REPORT.md) | 回避左尾降低实际尾部暴露，也错过右尾，主段多1.03、后段少0.46 bp。 |
| 44 | [合成左右尾预测](rounds/44_tail_balance/REPORT.md) | 尝试分离方向与波动后，两段少0.90和2.13 bp。 |
| 45 | [控制波动后回避左尾](rounds/45_volatility_control/REPORT.md) | 仍降低真实左尾暴露，但两段净差为−1.31和−4.38 bp。 |
| 46 | [单独检验低波动](rounds/46_low_vol_attribution/REPORT.md) | 两段均有小幅正差，去最好三月均负，保留作防守对照。 |
| 47 | [现金除息后盘中走弱](rounds/47_ex_dividend/REPORT.md) | 相对单一同行，事件净差早、主段正，后段负。 |
| 48 | [精确匹配除息日盘中跌幅](rounds/48_dividend_balanced/REPORT.md) | 改用同行组合后早期反向，三段去最佳三月全负，停止建账户。 |

### 49–70　训练样本、指数基准与资金配置

| 轮次 | 检验的问题 | 结果和取舍 |
|---:|---|---|
| 49 | [用二十日标签、十日调仓](rounds/49_monthly_training/REPORT.md) | 降低换手，但相同训练样本下比十日标签少1.28和4.62 bp。 |
| 50 | [拆解训练样本与截止日](rounds/50_training_support/REPORT.md) | 收益改善来自额外排除最近十个交易日的训练样本，主、后段多2.42、5.88 bp。 |
| 51 | [更早年份复核训练截止](rounds/51_earlier_replication/REPORT.md) | 2019年多1.00 bp，2020年两种长停牌估值下均少约0.27 bp。 |
| 52 | [删除其他训练周作安慰剂](rounds/52_training_placebos/REPORT.md) | 延后截止在主后段均胜三个安慰剂平均，但仍有早期年份反证。 |
| 53 | [拆训练收益集中度](rounds/53_cutoff_concentration/REPORT.md) | 去最大三股仍正，去最好三季度后主段只剩0.44 bp/月。 |
| 54 | [行业席位与行业内排序交叉替换](rounds/54_industry_seats/REPORT.md) | 近期提升主要来自行业席位变化，换行业内排序贡献很小。 |
| 55 | [在早期年份重放行业席位](rounds/55_earlier_seats/REPORT.md) | 2019、2020年分别多0.40、少0.83 bp，效果不普遍。 |
| 56 | [以行业篮子替换个股](rounds/56_sector_baskets/REPORT.md) | 2020年行业方向本身也亏，近期改善不能完全归于独立行业轮动。 |
| 57 | [剔除最近训练周的行业平均标签](rounds/57_recent_industry_labels/REPORT.md) | 四段相对原收益秩净差为正，但2019、2020年仅多0.18、0.37 bp。 |
| 58 | [打乱行业标签](rounds/58_industry_label_placebos/REPORT.md) | 真实行业只在主、后两个近期段胜等规模伪行业，2019和2020年均未胜出。 |
| 59 | [保持幅度分布再置换](rounds/59_shock_size_control/REPORT.md) | 早期两年真实行业标签均不及置换平均，停止升级。 |
| 60 | [合格等权池至指数的收益分解](rounds/60_benchmark_bridge/REPORT.md) | 后段选股毛差+27.23 bp，费用−20.76 bp，合格等权池本身落后指数9.16 bp。 |
| 61 | [指数权重的影响](rounds/61_benchmark_weights/REPORT.md) | 同一匹配股票上，等权与指数权重差异解释约−7.60 bp。 |
| 62 | [按五档指数权重分配资金](rounds/62_weight_matched_selection/REPORT.md) | 后段相对原收益秩仅多0.58 bp，相对全收益指数仍少7.44 bp。 |
| 63 | [按指数权重组查选股能力](rounds/63_size_bucket_skill/REPORT.md) | 最大权重组的组内选股毛差从主段+76.58变成后段−14.45 bp。 |
| 64 | [按最近成熟成绩切换主动和被动](rounds/64_mature_group_switch/REPORT.md) | 各组过去六个窗口的成绩未能可靠指示下一期应否主动选股。 |
| 65 | [等主动资金比较集中与连续倾斜](rounds/65_continuous_rank/REPORT.md) | 集中配置四段胜线性排名；相对被动在2019和后段仍亏。 |
| 66 | [拆开加最高分与避最低分](rounds/66_transfer_tails/REPORT.md) | 后段主要损失来自避开低分股，单独避低少11.47 bp。 |
| 67 | [控制低分股此前价格路径](rounds/67_bottom_path/REPORT.md) | 匹配短中期价格强弱后，后段避低仍有6.93 bp理想毛损失。 |
| 68 | [只避两模型共同低分](rounds/68_bottom_agreement/REPORT.md) | 后段仍落后被动7.74 bp。 |
| 69 | [低分股触及涨跌停](rounds/69_limit_close/REPORT.md) | 检查触板能否解释低分股后续反弹，再进实际账户。 |
| 70 | [保留触板低分股](rounds/70_touch_retention/REPORT.md) | 后段仅收回0.74 bp，其余三段均未改善。 |

### 71–90　历史反证与利润率

| 轮次 | 检验的问题 | 结果和取舍 |
|---:|---|---|
| 71 | [2018年复核集中倾斜](rounds/71_2018_concentration/REPORT.md) | 相对被动多9.74 bp，但相对同资金线性排名少1.61 bp，推翻此前四段全胜的泛化。 |
| 72 | [等权与漂移被动组合](rounds/72_passive_weighting/REPORT.md) | 等权只在两个近期段胜，后段多3.29 bp，需拆行业配置。 |
| 73 | [分离行业预算与个股权重](rounds/73_passive_sector_split/REPORT.md) | 后段等权收益主要来自行业配置。 |
| 74 | [账面、收入等基本面权重](rounds/74_fundamental_weights/REPORT.md) | 固定行业预算后，账面或收入倾斜仅在主段为正。 |
| 75 | [同资金比净利率与盈利／权益](rounds/75_profitability/REPORT.md) | 净利率五段均略胜直接对照，但主段仍不及漂移基准。 |
| 76 | [用最近一季度的利润率变化](rounds/76_margin_change/REPORT.md) | 五段中四段不及利润率水平。 |
| 77 | [严格披露时点的TTM净利率](rounds/77_reported_margin/REPORT.md) | 仅2026年129个信号日实际改变持仓，覆盖期内代理与财报账户吻合。 |
| 78 | [原件能支持多少组合资金](rounds/78_original_coverage/REPORT.md) | 可用年报仅5份涉及股票池，最高单日覆盖0.126%资金。 |
| 79 | [用披露原件复核两家公司](rounds/79_filing_pair/REPORT.md) | 验证选定的食品饮料配对，扩大到同一组全部六家公司。 |
| 80 | [复核组内全部六股](rounds/80_filing_cell/REPORT.md) | 十二份原件支持全部十五对名次，但随后十日的整组合贡献为−2.37 bp。 |
| 81 | [三级行业归因](rounds/81_margin_subindustry/REPORT.md) | 后段利润率增量约7.09 bp，其中6.41 bp来自行业配置；主段该项为负。 |
| 82 | [改为二十日持有](rounds/82_monthly_peer_margin/REPORT.md) | 延长期限仍依赖少数月份。 |
| 83 | [用其他规模组同行定行业权重](rounds/83_external_peer_margin/REPORT.md) | 主段仍落后漂移基准。 |
| 84 | [冻结2017年末利润率](rounds/84_fixed_margin_vintage/REPORT.md) | 缺少可执行的共同覆盖，无法判断固定版本表现。 |
| 85 | [逐年冻结对比实时更新](rounds/85_annual_margin_freeze/REPORT.md) | 四个可评价区间中更新均优于固定值，但区间均未排除零。 |
| 86 | [同组、同资金置换利润率变化](rounds/86_margin_change_placebo/REPORT.md) | 四段均胜三个置换，仍不足以证明对原选股有价值。 |
| 87 | [只在原名单内按利润率改善调权](rounds/87_selected_margin_change/REPORT.md) | 四段分别多1.66、4.31、0.39、1.01 bp，主段双费仅多0.02 bp。 |
| 88 | [固定三级行业预算](rounds/88_selected_margin_subindustry/REPORT.md) | 同行内调权四段仍正，主后段都只多0.25 bp。 |
| 89 | [逐股核算利润率贡献](rounds/89_peer_trade_attribution/REPORT.md) | 剔除最大三家公司后，只有2020年的月均净差为正。 |
| 90 | [用利润率决定边缘换入](rounds/90_margin_boundary/REPORT.md) | 主段接近零、后段少1.02 bp，停止边缘换股。 |

### 91–109　供给事件、入选频率与成交均价

| 轮次 | 检验的问题 | 结果和取舍 |
|---:|---|---|
| 91 | [指数快照权重剩余变化](rounds/91_index_weight_residual/REPORT.md) | 剔除价格和舍入影响后，仅2020年有较清楚的正收益。 |
| 92 | [月末动量及镜像反转](rounds/92_month_end_reversal/REPORT.md) | 动量五段不及漂移，反转仍四段不赚钱。 |
| 93 | [从成交量及换手率推断供给跳变](rounds/93_float_supply_step/REPORT.md) | 4,418个跳变匹配3,537对，避开扩张者的四腿事件差五段均负。 |
| 94 | [分母变化日与公开文件核对](rounds/94_supply_calendar/REPORT.md) | 两个极值可与披露核对；后段季末外事件差大，折整组合仅+0.008 bp/十日。 |
| 95 | [一月解禁预告与上市日](rounds/95_announced_unlock/REPORT.md) | 提前回避的可交易期中位数仅2日，各段未收回成本。 |
| 96 | [四月目录复核解禁后买入](rounds/96_april_unlock_rebound/REPORT.md) | 2018–2020及2021–2025披露组事件净差正，2026年和一月对照不支持普遍成立。 |
| 97 | [解禁事件放回连续底仓](rounds/97_unlock_portfolio/REPORT.md) | 2,069个信号日仅144日改权，主、后段仅+0.0179、−0.0115 bp。 |
| 98 | [按过去二十日入选频率调权](rounds/98_d10_frequency/REPORT.md) | 平均动用10.28%资金，前四段赢、后段少2.75 bp。 |
| 99 | [频率与当前分数是否同向](rounds/99_frequency_agreement/REPORT.md) | 后段的主要损失出在高频且当前高分的一组。 |
| 100 | [以长期入选率校正近期频率](rounds/100_selection_acceleration/REPORT.md) | 未修复后段失效。 |
| 101 | [历史成员和报价资格复核](rounds/101_eligible_history/REPORT.md) | 补入4,868个配对后，校正规则后段仍少1.48 bp。 |
| 102 | [只在前五日或后五日倾斜](rounds/102_frequency_half_window/REPORT.md) | 相对同频等权，两个半期方案在五段均落后。 |
| 103 | [只给同时新增的股票按频率配钱](rounds/103_frequency_orders/REPORT.md) | 6,000对新买单后段十相位全负，零费仍少2.40 bp。 |
| 104 | [用最近六个到期结果决定是否调权](rounds/104_frequency_feedback/REPORT.md) | 后段仍少1.86 bp，并输给慢调整仓位对照。 |
| 105 | [配平事前估计的市场贝塔](rounds/105_frequency_beta/REPORT.md) | 后段相对等权少2.86 bp，相对同资金对照少0.77 bp。 |
| 106 | [拆开收盘相对成交均价和日内价格位置](rounds/106_close_vwap/REPORT.md) | 收盘高于成交均价的方向四段落后；主后段均不及只用价格位置。 |
| 107 | [2017年独立日期挑战成交均价](rounds/107_vwap_early_challenge/REPORT.md) | 2,602个可交易同行配对有+23.37 bp毛差，换仓和恢复底仓后为−36.72 bp。 |
| 108 | [把成交均价用于原新增买单](rounds/108_vwap_new_orders/REPORT.md) | 主段多0.50、后段少1.39 bp；后段零费仍少0.49 bp。 |
| 109 | [同一批配对延至二十日](rounds/109_vwap_monthly/REPORT.md) | 毛差增至+34.31 bp，四腿净差仍为−25.85 bp。 |

### 110–127　日内收益、外部同行、股东户数与价格路径

| 轮次 | 检验的问题 | 结果和取舍 |
|---:|---|---|
| 110 | [分解过去一月的日内和隔夜涨幅](rounds/110_overnight_composition/REPORT.md) | 偏向日内上涨方五段落后；镜像去最佳三月五段均负。 |
| 111 | [把随后十日毛贡献按交易时段拆开](rounds/111_return_session_attribution/REPORT.md) | 日内项五段为正，隔夜回吐，提出自然买单时序检验。 |
| 112 | [同开盘原有买单分先后](rounds/112_entry_session/REPORT.md) | 新股先后顺序多段胜镜像，但五段均输给两只都在开盘买入。 |
| 113 | [到期原卖单推至收盘](rounds/113_exit_session/REPORT.md) | 两个顺序五段均多收钱；该诊断尚未计被占用的替换买单。 |
| 114 | [同步推迟卖单和依赖其现金的买单](rounds/114_funded_delay/REPORT.md) | 主、后段相对全开盘为−0.13、+2.57 bp/月，去最佳三月五段全负。 |
| 115 | [活跃同行是否领先](rounds/115_liquid_peer/REPORT.md) | 活跃股五段优于冷门同行，但相对原等权主段少2.47、后段多1.04 bp。 |
| 116 | [只做同行信号改变本股反转方向的交易](rounds/116_peer_disagreement/REPORT.md) | 2,038对、动用1.72%资金，主段少0.01、后段多0.46 bp。 |
| 117 | [剔除本股涨幅，只看外部同行价差](rounds/117_external_spread/REPORT.md) | 主段少0.70、后段多0.42 bp；后段双费转负。 |
| 118 | [股东户数季度收缩](rounds/118_shareholder_counts/REPORT.md) | 五段零费为正，标准费下主段少0.03、后段多1.70 bp。 |
| 119 | [只在双方披露后十日使用](rounds/119_holder_disclosure_clock/REPORT.md) | 主段未改善，后段双费转负；较早年份的有效时段不一致。 |
| 120 | [户数收缩只分配自然新增买单](rounds/120_holder_entry_orders/REPORT.md) | 8,394对、四段扣费为正；主段+0.35、后段+1.77 bp。 |
| 121 | [按同一报告季的价格涨跌配对](rounds/121_holder_quarter_price/REPORT.md) | 户数方向主后段各约多0.5 bp，双费均负。 |
| 122 | [用外部成分股剔除股价的解释部分](rounds/122_holder_price_residual/REPORT.md) | 校正后主、后段−0.04、+0.32 bp，两段均不及直接用户数。 |
| 123 | [逐股核对户数买单](rounds/123_holder_issuer_attribution/REPORT.md) | 主段去前三股由+0.83变为−1.29 bp/月，后段由+3.71降至+0.84 bp/月。 |
| 124 | [上涨分散于多少有效交易日](rounds/124_upday_dispersion/REPORT.md) | 偏向有效上涨日数多的股票，五段扣费后均落后。 |
| 125 | [固定实际上涨天数，再看涨幅均匀度](rounds/125_equal_updays/REPORT.md) | 均匀和集中两个方向均未在主后段胜出。 |
| 126 | [检验涨幅出现的早晚](rounds/126_upday_timing/REPORT.md) | 追近期上涨五段零费仍亏；偏向早涨五段有毛优势，主后段付费后亏。 |
| 127 | [用早涨方向分配自然买单](rounds/127_early_entry_orders/REPORT.md) | 前四段标准费为正，后段净差−2.09 bp、零费也少1.14 bp。 |

### 128–133　边缘换股与中点确认

| 轮次 | 检验的问题 | 结果和取舍 |
|---:|---|---|
| 128 | [同业边缘换股等五日排名确认](rounds/128_rank_crossing/REPORT.md) | 2,718对尚未持续领先，保留旧股主段多2.99、后段少0.47 bp。 |
| 129 | [保留相同金额的对照](rounds/129_rank_crossing_budget/REPORT.md) | 选择性保留相对均匀保留主段多1.15、后段少0.22 bp。 |
| 130 | [要求E1也支持旧股](rounds/130_crossing_second_score/REPORT.md) | 只触发248对、涉及0.42%资金，五段去最好三月均负。 |
| 131 | [把保留旧股分成两个五日](rounds/131_crossing_half_window/REPORT.md) | 后段零费损失在前后半均出现，单纯缩短留存未解决。 |
| 132 | [中点只执行再次确认的换股](rounds/132_crossing_midpoint_orders/REPORT.md) | 932对触发、929对成交；主段多3.22、后段少0.05 bp。 |
| 133 | [中点换入金额和席位配平](rounds/133_midpoint_matched_orders/REPORT.md) | 只有408天能区分选择，主后段相对同额均匀对照分别多0.37、0.22 bp；后段仍输原组合。 |

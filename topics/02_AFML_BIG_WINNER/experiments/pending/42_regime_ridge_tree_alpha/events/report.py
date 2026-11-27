from event_account import *
import json
def main():
    sections=['# EP42 D4 外部信息如何改变中证800的实际买单\n',
    '实验以 2021-01-11 至 2026-10-12 的历史成分重放。三段各自从现金起账，按 28、20、18 个完整月配对。下表给出每月净收益差的算术平均，单位为 bp；1 bp 等于 0.01 个百分点。区间来自各段内三个相邻月的移动块、10,000 次重抽，固定种子 4201。所有条目均属探索，区间用于描述抽样不确定性，未据此作多重显著性宣称。\n',
    '## 资金和时钟\n',
    '股票信号采用收盘时的当期资格，下一交易日开盘入场。只有发布日期时，必须过该日期后的第一个交易日收盘才能决策，再下一日执行。全池保留 1,076,242 个股票日，1,381 个截面，原头部一共 39,871 席。以实际净买付 10 bp、净卖付 20 bp，从各袖现金中扣除，保留限价、停牌、公司行动及跨袖净额，并重算双费。同股票多家同日触发只买一笔。H20 采用 20 个等资本袖，避免持续全额开仓时把风险暴露翻倍。\n',
    '全池、同覆盖、事件、ETF 和具名关系各自保留原始逐日净值、现金、费用、目标、逐袖净订单与未知估值终止日。各账户的 annual.csv 给出逐年、逐段净收益、同期中证800全收益、同池等权和 Ridge。分段间不拼净值。部分等权比较在出现无法估值的旧仓后为空。capital.csv 同列目标增量、净买增量和全部净买，也分列原对照未买的新增名字金额。\n',
    '## D4.1–D4.5　全池融合与同覆盖资金\n',
    '用 EP40 已封存的 23 季 Ridge 对当日 78 项量价特征逐行核平，最大绝对误差为零。只在各来源有值的股票内以截距和冻结的填补、缩放特征做最小范数投影，再把残差变成居中秩。校准系数用当季以前已成熟的扩展周频折外收益秩减同期 Ridge 值拟合，限定在零到一。无剩余自由度或无有效变动时自动回到 Ridge。缺来源的股票继承原分；在“锁住未覆盖”账户中，它们还继承原持仓席位。\n',
    '|编号与来源|有值股票日|原头部有值席|全池换席|全池对 Ridge（95%区间）|锁住未覆盖对 Ridge|\n|---|---:|---:|---:|---:|---:|']
    comp={k:pd.read_csv(OUT/k/'comparisons.csv').set_index(['arm','comparator','stage']) for k in ['fusion','same_coverage','events_h10','events_h20','events_h20_restart','etf','supply']}
    def row(k,a,b,stage='all'):return comp[k].loc[a,b,stage]
    def metric(k,a,b):r=row(k,a,b);return f'{r.bp:+.2f} [{r.low:+.2f}, {r.high:+.2f}]'
    def point(k,a,b):return f'{row(k,a,b).bp:+.2f}'
    def seg(k,a,b):return ' / '.join(f'{row(k,a,b,str(i)).bp:+.2f}' for i in [1,2,3])
    support=pd.read_parquet(OUT/'same_coverage/support.parquet').groupby('arm').sum(numeric_only=True)
    change=pd.read_parquet(OUT/'fusion/support.parquet').groupby('arm').changed_seats.sum()
    for n,label in [('eps20','D4.1 EPS修正20日'),('eps60','D4.1 60日半衰期'),('target20','D4.2 目标价'),('coverage_delta','D4.3 独立机构数变化'),('sue20','D4.4 首次盈利意外'),('mixed','D4.5 EPS与盈利意外')]:
        sections.append(f'|{label}|{support.loc[n,"covered"]:,}|{support.loc[n,"covered_head"]:,}|{change.at[n]}|{metric("fusion",n,"ridge")}|{point("same_coverage",n,"ridge")}|')
    sections+=['',
    'EPS 修正按公司、券商、财政年度比较连续两次 EPS，主表只取当前财年的最近20个交易日各券商最新方向，另取过去180日、半衰期60日。原档按报告月份抽样，最晚发布为 2026-04-29。4月29日后不把归档中止算作评级下降。20日信号及半衰期信号的全池变动都发生在第一账户段。\n',
    '目标价来自逐研报上、下限，双端齐全用中点，单端用该端。同券商比较两个已公开目标价；剔除港元、H股、目标市值等标题歧义、同日价格冲突，以及两次间价格复权因子变化或缺失；近20日每家取最新，然后取机构中位数。共12,922条有效目标记录进入审核，标题歧义26条，同日冲突4条，有前值但复权变化或缺失3,044条。A股人民币来源仍属标题与市场映射代理；缺逐篇币种字段。\n',
    '机构数用相邻两个不重叠60交易日窗口、同财政年度的不同机构数之差。只有一侧出现的公司可以作为在本档中出现或消失，不将未采集机构称为实际新增或退出。与当前机构数、原始变化、纯覆盖标志的对照均可在融合月表复查。规模/行业分布、档内券商及研报逐月数量均已保存。\n',
    '季度 SUE 只在首个已知披露后的20交易日内生效，新的有效值替换旧值。同日同时有归母金额和基本EPS时优先同口径的归母金额。可用事件全为年报财期。23季 SUE 的折外系数均为零，两源同股同日成对重排也未带来实际换席。EPS和SUE等权的全池变化与单EPS相同。\n',
    '[融合分段、全对照及删强月](results/fusion/comparisons.csv) · [锁住未覆盖席位的对照](results/same_coverage/comparisons.csv) · [逐季系数及成熟边界](results/fusion/folds.csv) · [行业及流通市值分位覆盖](results/fusion/sector_and_size_coverage.parquet) · [券商档案月份](results/fusion/monthly_archived_forecasts.csv) · [目标价排除数量](results/target_source_receipt.json)\n',
    '## D4.6–D4.8　公告与研报事件账户\n',
    '共识需至少两家独立机构，分别取相关预告、快报、定报最早公开前的最新同财期同口径预测。归母预告按上下限中点并将万元换为人民币元；正式归母实际取合并报表。按发行人、财季和披露类型，用此前最多8个同类误差的样本标准差，至少两期且分母为正。首次和后续披露分开；快报用稀释 EPS，只按代理解释。归母口径新算出408个首次正式、135个首次预告有标准化值。年报基本EPS、快报稀释EPS另列；同一年度绝不相加成独立样本。\n',
    '单季营收和扣非净利由当年累计减当时已公开的前季累计，第一季度直接取原数。与上年同季比较仅保留正基数，再减前一季同比得到加速度。要求各环节的合并报表公司类型相同，且该类型在指标公布时已有可查报表。公司类型改变或未公开即排除；同类别内部的具体会计政策重述仍无法逐公司认证，结果为最早可见报表值代理；没有同指标可核的季度共识时，只解释为增长路径。公告财务库覆盖2016Q1–2026Q3、43个财季。\n',
    '事件比较在同日、同申万一级行业、自由流通市值百分位差不高于0.10的原合格池内配对，最小化市值差，再优先 Ridge 高分，未知行业与市值的席位不出资。无匹配席在两边都保留现金。普通正上修与大幅上修的直接比较使用同日共同席数与分母，避免仅仅比较两类不同的事件日。大幅上修要求旧EPS为正、增幅至少20%，当前或未来财年均须与该券商上一份预测同财年；大幅和温和组以同股同日去重并互斥。\n',
    '|编号与事件|合格股票日|匹配席|H10 对匹配股（95%区间）|H20 对匹配股（95%区间）|\n|---|---:|---:|---:|---:|']
    es=pd.read_parquet(OUT/'event_details/support.parquet').groupby('arm')[['eligible','matched']].sum()
    for n,label in [('quarter1','D4.6 Q1首次'),('quarter2','半年报首次'),('quarter3','前三季度首次'),('guidance','年预告首次'),('annual_profit','年报归母首次'),('annual_eps','年报基本EPS首次'),('flash_eps_proxy','年快报稀释EPS首次'),('revenue_accel','D4.7 营收加速度'),('deducted_accel','扣非净利加速度'),('eps_large','D4.8 大幅上修'),('eps_small','温和上修'),('eps_large_current_fy','大幅上修仅本财年')]:
        a,b=es.loc[n]
        def outcome(k):return metric(k,n,n+'_match') if b else '未触发'
        sections.append(f'|{label}|{a:,}|{b:,}|{outcome("events_h10")}|{outcome("events_h20")}|')
    sections+=['',f'同日直接比较中，营收加速度相对简单增速 H10 / H20 为 {point("events_h10","revenue_accel_direct","revenue_growth_direct")} / {point("events_h20","revenue_accel_direct","revenue_growth_direct")}；扣非净利对应 {point("events_h10","deducted_accel_direct","deducted_growth_direct")} / {point("events_h20","deducted_accel_direct","deducted_growth_direct")}。大幅上修相对温和上修为 {point("events_h10","eps_large_direct","eps_small_direct")} / {point("events_h20","eps_large_direct","eps_small_direct")}。单独看大幅上修相对行业匹配股的收益，会高估20%门槛自身的证据。\n',
    'H20 的扣非加速度对照与营收简单增长第一段因持仓缺价在2022-06-29结束，原配对仅54个完整月。对受影响两组另在7月1日重新等本金起账，得到64个共同完整月。两组分别为 '+metric('events_h20_restart','deducted_accel','deducted_accel_match')+' 和 '+metric('events_h20_restart','revenue_growth','revenue_growth_match')+'。\n',
    '对14,569份已核准归档研报正文另按显式财季、归母净利、数额与单位提取中期预测，仅11条能通过这一文本条件，均未在该公司该财期首次披露之前形成合格事前截面。报告接口抽查也缺乏足量同公司、同财季、两家机构且可估历史误差的中期样本。Q1、半年和前三季登记保留，资金触发为零。\n',
    '[公告财季与覆盖](results/period_evidence.csv) · [11条中期原句](results/interim_disclosed_forecast_spans.parquet) · [供应商财期查询核对](results/report_rc_period_probe.json) · [H10全对照](results/events_h10/comparisons.csv) · [H20全对照](results/events_h20/comparisons.csv) · [H20缺价后的独立起账](results/events_h20_restart/comparisons.csv) · [实际配对明细](results/event_details/pairs.parquet)\n',
    '## D4.9–D4.10　ETF 申赎的方向\n',
    '两只300基金为510300、159919；扩展预选510500、512100、588000、512800、512880、512010，对应500、1000、科创50、银行、证券和医药。以历史当日篮子的股票数量乘前收和已公告单位，按前一交易日已记录的五日份额变化估计名义需求，再除当时 ADV20。剔除已知拆分与份额、净值反向跳变所污染的五日差分。主规格取可实物交付的成分，另列包含退补篮子。每只基金的单位、变更公告、记录日期、份额、现金替代、缺篮子均可逐日核对。\n',
    '每个可比原席同时存在同行业、流通市值分位相差不超过0.10的正向与反向候选，才允许更换。每一方向、过去篮子权重变化、固定哈希都更换相同日期、相同席数。原席在 Ridge 对照保留。扩展与旧双基金在300共同支持上的比较额外锁住两者都能更换的原席。各自篮子账户在当日有可比行情及冻结Ridge的成分内新建独立同资金基线，1000股篮子的800域外股票在覆盖分母中单列。完整 ETF 份额与PCF没有逐日可认证的首次公开时刻，按滞后一日历史代理解释。\n',
    '|基金范围|配对席次|顺流对同资金 Ridge（95%区间）|逆流对同资金 Ridge（95%区间）|\n|---|---:|---:|---:|']
    ec=pd.read_parquet(OUT/'etf/opportunities.parquet').groupby('group').exchanged.sum()
    for n,label in [('two','D4.9 原两只'),('expanded','D4.10 八只全池'),('two_common300','原两只、共同300席'),('expanded_common300','八只、共同300席'),('only500','500单一来源'),('only1000','1000单一来源'),('only_star','科创50单一来源'),('industry','三个行业ETF'),('native500','500篮子内重排'),('native1000','1000篮子与800可评分交集'),('nativestar','科创50篮子内重排'),('nativeindustry','行业篮子内重排')]:
        b=n+'_ridge' if n.startswith('native') else 'ridge'
        count=int(ec.at['both_common300_final'] if n.endswith('common300') else ec.at[n])
        sections.append(f'|{label}|{count:,}|{metric("etf",n+"_flow",b) if count else "未触发"}|{metric("etf",n+"_reverse",b) if count else "未触发"}|')
    reserve=pd.read_csv(OUT/'etf_original_reserve/mean.csv',index_col=0).bp_month
    occ=pd.read_csv(OUT/'etf_original_reserve/opportunities.csv')
    sections+=['',f'另按 EP41 N6 原来的后段候补购买名单、行业、规模、动量和指数权重入口逐日重建。必须同一原席既有更高又有更低流量的候选，出现 {occ.changed.sum()} 席，18 个完整月的顺流、逆流、过去指数权重对原候补 Ridge 分别为 {reserve.flow:+.2f}、{reserve.reverse:+.2f}、{reserve.weight:+.2f} bp/月。较全池的7,727个可换席，这个原预算难以区分两种方向。[原候补机会复算](results/etf_original_reserve/mean.csv)\n',f'在同一批可更换300席上，八只减原两只，顺流为 {metric("etf","expanded_common300_flow","two_common300_flow")}，逆流为 {metric("etf","expanded_common300_reverse","two_common300_reverse")}。篮子外没有冻结的800合格 Ridge 排序和严格可交易账本，不能将覆盖内表现外推到全部中证1000成分。供应商全清单含1,746只有效、130只退市、76只待上市产品，已保留退市标记。试验以八只可核产品为限，历史更名与换指数无法逐日认证。\n',
    '[基金申赎单位与管理人原文](unit_history.csv) · [逐基金逐日覆盖与现金替代金额](results/etf/source_coverage.parquet) · [份额拆分排除](results/etf/splits.csv) · [全部配对差、费用和删强月](results/etf/comparisons.csv) · [实际改动资金](results/etf/capital.csv)\n',
    '## D4.11　供应与采购方向\n',
    '原四条边来自有日期的具名合同。本次补入华友—容百、容百—宁德、福莱特—晶澳、福莱特—隆基、福莱特—晶科五条，保留实际可知日、合同有效起止及原文。后公告追述的早期合同从本次找到的公开日以后才入样。按两个方向分别比较关联方过去五日收益、剔除自身的同行业平均动量、与真关联方同业的等数量伪边、原 Ridge。伪边排除自身与截至该日已经公开的真实关系。每个有效日每组只调用一份到期袖预算，在相同目标池选一只；当日只有一个合格目标时四臂自然相同。\n',
    '|关系范围与选股方向|有事件日|有实际不同选择的日期|相对同行动量|相对伪关系（95%区间）|相对 Ridge|\n|---|---:|---:|---:|---:|---:|']
    sc=pd.read_parquet(OUT/'supply/support.parquet')
    for grp,label in [('original','原四条'),('expanded','扩展九条')]:
        for direction,label2 in [('supplier','选供应商'),('buyer','选采购方')]:
            z=sc[(sc.history==grp)&(sc.direction==direction)]
            n=grp+'_'+direction+'_';sections.append(f'|{label}{label2}|{sum(z.covered>0)}|{sum(z.alternative_choices>1)}|{point("supply",n+"partner",n+"industry")}|{metric("supply",n+"partner",n+"pseudo")}|{point("supply",n+"partner",n+"ridge")}|')
    sections+=['','扩展后供货侧和采购侧方向不同，高集中度明显。后三条新边共用福莱特，有效上市公司和独立产业链的数量远少于有信号日期。该试验不能识别一般供应链传导收益。\n',
    '[九条具名关系与公司原文](results/named_contracts.csv) · [逐日真边与伪边](results/supply/signals.parquet) · [净收益、区间与分段反转](results/supply/comparisons.csv)\n',
    '## 复算与审计\n',
    '本目录的 fetch_sources.py 读取项目现有供应商授权，任何收据均不含密钥。原始响应保存返回码、查询参数、行数、UTC 抓取时刻及哈希；抓取时刻是本次归档时刻。可认证基金单位页面的公开历史与未获授权的逐日单位接口在来源记录中并存。财报原始初版、研报第一次网络出现时刻与连续完备覆盖无法由事后档案认证，因此整组历史结果均未作为未来样本。\n',
    '从本目录依次运行 prepare_features.py、disclosures.py、signals.py、fusion.py、same_coverage.py、event_books.py、h20_restart.py、supply.py、etf_books.py、source_audit.py、account_audit.py、report.py。原始财报与ETF数据收集入口为 fetch_sources.py 的 financial、basis、etfs、industry_compact、repair1000、units；报告接口额外使用 vendor_consensus_probe.py。原候补预算复算运行 reserve_etf.py，最终执行 verify.py 生成全部哈希与逐项登记收据。逐日证券和日历整数索引分别对应 instrument_map.csv 和 trading_calendar.csv。\n']
    (HERE/'REPORT.md').write_text('\n'.join(sections))
if __name__=='__main__':main()

"""Generate readable research reports and an explicitly historical monitoring snapshot."""
import pandas as pd
from common import *
from evaluate_r01 import scores


def table(df):
    def cell(v):
        if pd.isna(v):return '—'
        if isinstance(v,(float,np.floating)):return f'{v:.5f}'
        return str(v).replace('|','/')
    return '| '+' | '.join(map(str,df.columns))+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(cell(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))+'\n'


def write(name,text):
    (ROOT/name).write_text(text.rstrip()+'\n')


def factor_dictionary():
    rows=[]
    specs=[
        ('F','mom20/mom60','信息缓慢扩散','NAV_t/NAV_t-h -1','正','全行业可用篮子','日','EP32 verified daily / EP35 L1','可复现代理','未来收益不延续；共同市场/风格解释'),
        ('F','vol20','风险与趋势质量','std(daily return,20)*sqrt(252)','负','全行业可用篮子','日','同上','可复现代理','低波并不等于高收益；行业风险溢价替代解释'),
        ('F','dd60','趋势维持','NAV_t/max(NAV last60)-1','正','全行业可用篮子','日','同上','可复现代理','接近高位可能均值回归'),
        ('H','breadth21/breadth63','信息扩散','前月成分中h日涨幅>0的有效成员比例','正，待检验','全行业可用篮子','日','EP32 verified constituents / EP35 L1','可复现代理','广度变化被既有价格解释；不得直接当反转'),
        ('H','turn_rank504','行为与拥挤','个股换手率504日分位（至少378日有效）的行业中位数；至少5成员且80%有效','负，待检验','L2/L3','日','EP32 joint_pe_v35 inherited turn_rank504','可代理；非交易+持仓双拥挤','高活跃继续上涨；持仓拥挤缺失'),
        ('G','pe_rank504','估值与预期要求','个股正TTM PE过去504日分位；>=75%窗口有效，行业取中位数且>=80%成员有效','负，待检验','L2/L3且正PE有效覆盖','日','EP32 joint_pe_v35；供应商PE known_at缺失','历史代理；非Forward PE','利润下修低估值陷阱；亏损行业选择偏差'),
        ('C','dedt_change','盈利兑现','(本年累计扣非-上年同期扣非)/(abs本年+abs上年)','正，待检验','当前已恢复四季度财务且成员覆盖充分行业','季','R03 all-market archived fina_indicator_vip pages','公告时点历史代理+归档快照','非主营利润变化；盈利已被市场计价'),
        ('C','margin_delta','经营改善','本年毛利率-上年同期毛利率（百分点）','正，待检验','同上；行业可比性需另审','季','同上','公告时点历史代理+归档快照','组合变化/会计口径导致毛利率变化'),
        ('A','macro_state_x_sensitivity','增长信用与折现','待登记：PMI/信用冲量×仅用历史估计的行业敏感度','行业依赖','宏观敏感行业','月','国家统计局/央行候选；本轮未取得历史发布版本','未实现；来源待补','同日共享变量不能独立排序；价格先行'),
        ('B','industry_spread_inventory','产业组织与资本周期','待按行业登记：产品价格-投入成本；订单/库存/产能','上下游不同','机制明确的少量行业','周/月','本地经营观测待核查；外部采集未开展','未实现；需序列和可用时间','产品涨价但盈利不改善；供给扩张压低利润'),
        ('D','fixed_fy_eps_revision','预期修正','同固定预测年度、同分析师或明确样本变化下EPS修正与广度','正，待检验','有历史预期记录的公司聚合行业','日/周','本轮来源未定位到固定年度历史预期面板','数据缺口；不以已实现利润替代','年度滚动/样本更替伪修正；追随价格'),
        ('E','fund_etf_allocation','资金配置','待登记：披露后基金超配变化、ETF份额净变化','待检验','有可靠历史披露及映射行业','季/日','持仓/ETF历史面板未接入','数据缺口；不以换手替代','披露滞后；申赎追随价格而无领先')]
    for module,name,theory,formula,direction,scope,freq,source,status,fail in specs:
        financial=module=='C';unimplemented=module in ['A','B','D','E']
        rows.append(dict(module=module,factor=name,theory=theory,formula=formula,direction=direction,applicable_industries=scope,
            economic_date='财报期末' if financial else '待定义' if unimplemented else '交易日',
            publication_date='供应商ann_date/f_ann_date，未验证完整修订历史' if financial else '缺口' if unimplemented else '当日收盘信息；PE历史发布时点未知',
            available_at='max公告日后的下一交易日代理；另保留真实retrieved_at' if financial else '缺口' if unimplemented else '研究信号t收盘，t+1收盘入点；非严格PIT证明',
            frequency=freq,source=source,historical_revisions='未证明全量版本完整',
            aggregation='C等权组内合成；行业公司因子等权且有效>=5、覆盖>=80%' if financial else 'R01协议；变体先组内合成，再模块等权；G使用中位数',
            missing_rule='保留缺失，不填0；配对样本与全母体覆盖分别报告',failure_condition=fail,replication_status=status,
            horizon='主20/次60交易日；未实现因子待事前登记'))
    pd.DataFrame(rows).to_csv(ROOT/'outputs/factor_dictionary.csv',index=False)


def run():
    factor_dictionary()
    r1=pd.read_csv(ROOT/'outputs/r01/paired_increments.csv');r2=pd.read_csv(ROOT/'outputs/r02/paired_increments.csv')
    r3=pd.read_csv(ROOT/'outputs/r03/summary.csv');r4=pd.read_csv(ROOT/'outputs/r04/summary.csv');r5=pd.read_csv(ROOT/'outputs/r05/paired_increments.csv')
    rec=json.loads((ROOT/'outputs/r02/run_receipt.json').read_text());fin=json.loads((ROOT/'outputs/r03/archive_receipt.json').read_text())
    write('reports/R01_固定排序与增量.md',f'''# R01 固定排序、扩散、拥挤与估值

2026-11-13。想验证：价格趋势信息之外，更广的参与、更低交易拥挤或更低估值要求，能否改善行业未来相对收益排序。

机制是候选假说，不是已证实因果：扩散可能支持趋势持续，也可能只反映同期价格；高交易活跃可能过热，也可能是新信息进入；低PE分位可能便宜，也可能反映盈利恶化。

协议：`protocols/r01.json`。月末形成信号，下一交易日收盘开始计算20/60交易日收益，相对中证全指。分类时代、层级分别评价，排名先于观察未来结果。F为价格组等权；FD加入扩散，FC加入负向交易拥挤，FG加入低PE分位，FDG加入扩散和估值。它们不是方正原报告复现。配对控制严格使用同日期和同可用行业，另报缺失损失。

## 发现（主期限20交易日）

{table(r1[r1.horizon.eq(20)][['era','level','cohort','months','delta_ic','ci95_low','ci95_high','multiplicity_low','result']])}

交易拥挤的SW2021均值改善，但多重检验后的区间仍包含零；扩散和估值没有普遍改善。没有扩展达到本轮登记的稳定增量标准。这里的未确立不等于经济机制被普遍否定：部分PE配对样本月份很少，且亏损/缺失行业选择性明显。

是否领先：收益窗口明确在信号之后，但仍是反复研究历史上的预测相关性。是否独立：与固定价格分数组合的同母体比较仅是第一层增量检验；共同市场和风格控制并未完整。适用边界：SW2014、SW2021与L2、L3各自成立的结果不相互外推。成本：固定持有诊断按每边0/20/50bps扣除，不是换手组合收益；月度真实换手另见R04。

统计边界：按日期6个月区块bootstrap处理行业间相关和持有期重叠；2000次重采样对多重调整后的极端分位精度有限，且未解决研究者重复使用历史的问题。

完整产物：`outputs/r01/date_metrics.csv`、`annual.csv`、`paired_coverage.csv`、`panel_coverage.csv`、`paired_increments.csv`。决定：不继续搜索权重/窗口；用已登记的R02低复杂度模型检查是否只是等权合成限制。
''')
    write('reports/R02_三任务模型与校准.md',f'''# R02 三项任务必须分开评价

想验证：价格控制下的扩散、交易拥挤和估值，是否分别改善弱转强、相对收益与趋势内回撤风险。协议见`protocols/r02.json`；未搜索标签或模型参数。

收益用Ridge alpha=10；两项分类用Logit C=1，再用测试年前7—12月的独立过去窗口做Platt校准。训练标签必须在训练截止前成熟，校准标签在测试年开始前成熟。分类时代与行业层级分开训练。共训练{rec['trained_folds']}个任务/母体/年份折，跳过{rec['skipped_folds']}折，生成{rec['rows']:,}条预测（包含方法、期限、样本和缺失结局，不能视为独立机会数量）。跳过原因见fold_ledger，不降低最低样本要求。

启动：过去20日相对收益<=0的行业，未来20日绝对收益>=5%且相对>=3%；60日对应10%/5%。这是月末弱转强代理，不是完整日频启动过程召回。反转：已有绝对与相对60日上涨趋势，入点后相对财富最低下降8%/12%；这是相对入点的损失风险，不是从未来最高点量出的最大回撤。

## 主期限的配对增量

正数代表改善（收益为IC增加；分类为Brier损失降低）。

{table(r2[r2.horizon.eq(20)][['era','level','cohort','task','months','increment','adjusted_low','result']])}

没有比较达到本轮预先登记的增量标准；多项分类比较仅有10—22个评价月，样本不足是关键限制，不能写成所有变量都无效。校准并非自动改善：部分折的校准后Brier比未校准更差，原始与校准后结果均在summary中保留，未按表现挑选替换。

风险预警代价同时保留：top20%风险警报中，后来仍有正相对收益的比例与错失收益见summary。对启动行同名警报字段只表示正收益比例，不能解释成退出决策。`pending`字段在当前CSV表示所有未知结局，包含尾部未成熟和区段中断，不能全部解释成等待未来。

已验证：216,740条预测可用保存的缩放、系数、校准参数独立重放，最大误差0；配对行和标签一致；成熟时间检查通过。未验证：全风格独立性、经济因果、跨更多年份稳定性、日频及时性及可交易配置效果。决定：不增加复杂模型；补充真实信息来源和组合可实现性，保留失败与样本不足的分支。
''')
    write('reports/R03_财务数据补充与初步对照.md',f'''# R03 从本地完整分页补充基本面

想验证：不等待全数据齐备，能否恢复可追溯的盈利兑现信息，并检查它是否比既有价格多提供信息。

从本地`golden_loop_artifacts/.../20261010-data-v1/inputs/provider_responses.zip`恢复{fin['pages']}页、{fin['raw_rows']:,}条记录、{fin['issuers']:,}个证券代码。四个财报期为2025Q1/H1和2026Q1/H1，包含利润表、现金流和财务指标。逐页原文SHA256与回执匹配，offset连续且最后一页不足上限。使用全响应，不继承原2320家公司/19行业固定池。来源代码不等于独立发行人数量，实际行业计算依照历史成员映射。

两只时钟：公告日期后的下一交易日仅用于历史代理；真实归档时刻保留在archived_available_at。原始数据在2026-10-10获取，不能宣称其中历史修订值在2025年已掌握。公告早于期末的{fin['invalid_timing_rows']}条记录不进入历史可用计算；相同公司、期末、可用日的值冲突保留缺失，未按update_flag擅选。

另外15条原文核验的PIT-reconstructed财务事实保留在financial_timed_facts，只涉及2家公司，不能冒充全行业PIT。

因子：同季度累计扣非利润的对称变化、毛利率同比差。按前月历史成员等权聚合，至少5家且有效覆盖>=80%；两项缺一不重分权重。行业研究母体仍是全可用目录，缺失行业在覆盖表中保留。

{table(r3[r3.horizon.eq(20)])}

发现：全市场归档显著改善覆盖，但只有5个20日成熟月、3个60日成熟月，主任务无法据此形成稳定统计结论。财务因子与价格混合在部分月份改善，在另一些月份恶化。盈利兑现并不等于分析师预期上修，当前数据不能回答固定预测年度的预期领先问题。

能否下结论：不能宣称独立预测能力，也不能宣称因果机制成立。年度、行业和修订边界都不够。可继续的方向是补齐可验证历史版本、做披露时点/延迟对照和机制适用性检查；不扩大无依据窗口搜索。全数据与来源留在本地data目录并被Git忽略。
''')
    valid=r4[r4.cost.eq('net20')&r4.whole_path_valid]
    write('reports/R04_月度换手成本与风险.md',f'''# R04 固定信号后的月度配置诊断

想验证：R01固定信号在月度实际换仓、权重漂移和每边20/50bps成本下还剩多少表现。未按R01结果调整分位数或参数。信号月末形成，次交易日收盘换仓，持有至下一次换仓；行业等权、动量、F、FD、FC使用共同事前可用母体。首笔建仓与末笔清仓计费。

成本按新权重与漂移旧权重绝对差之和扣除；完整换手的买卖两侧都计入。输入仍是按股票重建的研究篮子，并非官方行业指数、ETF或可实际执行的股票组合。

## 可以计算完整路径的组合（每边20bps）

{table(valid[['era','level','method','valid_intervals','monthly_turnover_mean','cagr','drawdown','vol','beta','benchmark_cagr']])}

区间边界以intervals.csv entry/exit为准；SW2021完整组合覆盖2022年启动后的52个月度区间，从2022-06-01至2026-10-08。FC历史收益高于F不构成可靠预测结论：R01/R02的独立增量标准未通过，研究者已反复使用历史。

其余组合至少一个被选行业的未来日路径缺失，或者运行中信号母体不足。没有用零收益或替换持仓掩盖缺口，因此其完整CAGR、回撤、波动和Beta被抑制。valid interval均值仅是条件描述，受缺失选择影响，不允许当作全时期组合绩效；缺失后重新开始的换手也不能当作连续策略成本。

补充成分级审计：431个行业日中395个被成员少于5家的原规则排除，36个未达80%有效价格覆盖；见constituent_gap_diagnosis.csv。信号选样与持仓估值应另立协议区分，不能直接放宽原规则。

尚未解决：等权对照的完整路径、股票成分重叠、流动性/停牌/涨跌停、真实成交成本、风格集中和压力情景。下一项应定位缺口、核查原价与调整链、做有依据的保守边界；不得简单放宽覆盖阈值补出漂亮曲线。
''')
    write('reports/R05_一级行业独立基准.md',f'''# R05 一级行业独立重建

想验证：一级行业也应有自己的母体和结果，不能把二三级研究结果外推。

核验5756个原始股票价格分区，按SW2021二级到一级分类映射合并历史月度成员，重建31个一级行业的35,402条日记录、1,767条月末记录。没有直接平均二级行业收益。前月成员固定用于下一月，价格冲突与复权链变化保留缺失，断续区段不连算。

局限：当前SW2021父子目录作为历史映射代理，不能声称逐期父子关系PIT；SW2014一级目录尚未恢复。没有将二级PE或拥挤分数强行拼到一级。评价仍为月末信息、下一交易日收盘入点、20/60日相对中证全指。

{table(r5)}

发现：扩散加入一级价格排序的平均增量为负，区间包含零，未达到预登记标准。该结果与二三级固定扩散等权未普遍改善的发现相容，但不证明广度毫无用处或经济机制不存在。一级top6诊断详见date_metrics.csv，不能称方正报告完整复现。下一步需完成一级独立模型/组合及完整分类母体缺口核对。
''')
    monitor=[]
    base=pd.read_parquet(ROOT/'data/monthly_panel.parquet');l1=pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')
    combined=pd.concat([base[base.level.eq('L2')],base[base.level.eq('L3')],l1.dropna(axis=1,how='all')],ignore_index=True)
    for level,g in combined.query("era=='SW2021' and price_ready").groupby('level'):
        g=g[g.date.eq(g.date.max())].copy();sc=scores(g);g['price_score']=sc.F;g['price_rank']=g.price_score.rank(ascending=False,method='min')
        g['snapshot_type']='historical replay created 2026-11-13; not a contemporaneous signal'
        monitor.append(g[['date','era','level','industry_code','industry_name','coverage','members','price_score','price_rank','mom20','mom60','breadth21','breadth63','turn_rank504','pe_rank504','snapshot_type']])
    m=pd.concat(monitor,ignore_index=True);m.to_csv(ROOT/'outputs/historical_monitor.csv',index=False)
    catalogue=pd.read_csv(ROOT/'outputs/r01/industry_catalog.csv')
    daily_l1=pd.read_parquet(ROOT/'data/l1_daily.parquet')
    for code,g in daily_l1.groupby('industry_code'):
        mask=catalogue.era.eq('SW2021')&catalogue.level.eq('L1')&catalogue.industry_code.eq(code)
        catalogue.loc[mask,'rows']=len(g);catalogue.loc[mask,'start']=str(g.date.min().date());catalogue.loc[mask,'end']=str(g.date.max().date());catalogue.loc[mask,'basket_present']=True
    latest=m[KEY].assign(latest_month_price_ready=True)
    catalogue=catalogue.merge(latest,on=KEY,how='left',validate='one_to_one')
    catalogue['latest_month_price_ready']=catalogue.latest_month_price_ready.eq(True)
    catalogue.to_csv(ROOT/'outputs/universe_current.csv',index=False)
    write('reports/监控快照说明.md','''# 历史监控快照，不是实时推荐

生成日2026-11-13；源价截至2026-10-21；最新完整月末信号截至2026-09-30。当前快照已陈旧，不能作为今日配置建议或当时已经发出的前瞻信号。

`outputs/historical_monitor.csv`保留全部价格可评价行业的独立层级排名、价格变化、扩散证据及拥挤/估值可用性。缺少字段保留空值。覆盖不足和缺篮子行业另在industry_catalog与panel_coverage列示，不能理解为零风险或零收益。

没有输出加总100%的阶段概率。价格强、广度高、PE低只是各自证据维度，不直接证明潜伏、启动、扩散或反转经济阶段。盈利、预期、产业驱动尚未整合进持续跟踪，不生成虚构的驱动解释。

更新方式：冻结输入可用run_local.py reproduce重放；验证用verify；新增数据必须新建来源版本和研究协议，不能覆盖旧来源后称原判断当时有效。下一次有效更新需比2026-10-21更晚的可核验本地价格/成员版本，并重新审查数据和标签成熟。尚未设置定时任务、生产部署或外部发布。
''')
    print('REPORTS AND HISTORICAL MONITOR WRITTEN',len(m),'rows')

if __name__=='__main__':run()

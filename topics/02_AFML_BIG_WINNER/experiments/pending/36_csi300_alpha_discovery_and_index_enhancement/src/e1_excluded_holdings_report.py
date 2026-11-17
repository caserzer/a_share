"""Report partial identification without confusing benchmark attribution and selection."""
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from e1_excluded_holdings import *
def table(a,percent=()):
 a=a.copy()
 for c in percent:a[c]*=100
 return a.to_markdown(index=False,floatfmt='.4f')
def link(f):return f'../../outputs/diagnostics/{RUN}/{f}'
def report(name,text):
 (R/(name+'.md')).write_text(text)
 (R/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>E1 被排除持仓追查</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd}th{background:#edf3f5}img{max-width:100%}a{color:#146887}</style>'+markdown.markdown(text,extensions=['tables','fenced_code'])+'</html>')
def main():
 for n in ['freeze','selection_complete','accounts_complete','analysis_complete']:verify(n)
 audit=json.loads((D/'disclosure_audit.json').read_text())
 for f in audit['files']+audit['source']:assert sha(f['path'])==f['sha256']
 met=pd.read_csv(D/'metrics.csv');stats=pd.read_csv(D/'statistics.csv');cov=pd.read_csv(D/'coverage_summary.csv');reasons=pd.read_csv(D/'original_excluded_reasons.csv');years=pd.read_csv(D/'replacement_periods.csv');origyears=pd.read_csv(D/'original_excluded_years.csv');stocks=pd.read_csv(D/'original_excluded_stocks.csv');replacement=pd.read_csv(D/'replacement_stocks.csv');profiles=pd.read_csv(D/'profile_summary.csv');sens=pd.read_csv(D/'disclosure_sensitivity.csv');rank=json.loads((D/'excluded_rank_statistics.json').read_text());v=json.loads((D/'validation.json').read_text())
 yr=years[(years.comparison=='O-P')&(years.freq=='Y')];m=met[met.cost=='main']
 fig,axes=plt.subplots(1,2,figsize=(12,4.5))
 for st in ['O','P','PR']:
  a=pd.read_csv(D/'accounts'/(st+'__main.csv'),parse_dates=['date']);axes[0].plot(a.date,a.nav,label=st)
 axes[0].axhline(1,color='gray',ls=':');axes[0].xaxis.set_major_locator(mdates.YearLocator());axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y'));axes[0].set_title('Original O vs excluded-budget replacement');axes[0].set_ylabel('NAV from initial cash = 1');axes[0].legend()
 axes[1].bar(yr.period.astype(str),yr.wealth_contribution,color='#25877a');axes[1].axhline(0,color='gray');axes[1].set_title('O minus P: linked yearly contribution');axes[1].set_ylabel('Wealth gap per initial 100')
 fig.tight_layout();fig.savefig(R/'accounts_years.png',dpi=170);plt.close(fig)
 events=pd.read_csv(D/'events.csv',parse_dates=['signal_date'])
 piv=events.pivot(index='signal_date',columns='strategy',values='net_return');mark=events.pivot(index='signal_date',columns='strategy',values='marked_return');net=piv.SELECTED-piv.PEERS;marked=mark.SELECTED-mark.PEERS
 fig,ax=plt.subplots(figsize=(11,4));ax.bar(net.index,net*100,width=16,label='Executable net H10 (44 pairs)');ax.scatter(marked.index[net.isna()],marked[net.isna()]*100,color='#ba5e44',marker='x',s=60,label='Unliquidated endpoint mark (6 pairs)');ax.axhline(0,color='gray');ax.set_ylabel('Matched-sleeve return difference (pp)');ax.set_title('Original excluded picks minus same-industry peers');ax.xaxis.set_major_locator(mdates.YearLocator());ax.legend();fig.tight_layout();fig.savefig(R/'event_differences.png',dpi=170);plt.close(fig)
 report('REPORT',f'''# 原 E1 被排除持仓：更明确的行业内选择线索

**本轮定位到一块此前被缩减股票池排除、但具有较强历史选择收益的持仓。** 只将其中能匹配的预算换成同行业未入选股票，原E1净年化由+4.84%降为约−0.45%；可完成退出的H10事件中，原选股平均领先约1.00个百分点。它比此前单看分数解释份额更接近经济证据，但仍不是独立Alpha或经济原因的最终确认。

## 先区分被排除的是什么

C池要求13风格、价格信息完整且行业至少有10只合格股票。这会删除一些在沪深300样本中股票数量较少的行业。**“行业不足10只”不是小盘股定义，也不代表该行业在经济上规模小。**

原月初目标中平均33.19%资金落在C池外。按原账户每日相对指数贡献、使用最近月度决策时点分类，这部分贡献约20.76元/初始100元；交易费与现金单列，不算作该部分收益。

{table(reasons)}

其中行业不足10只约17.25元，缺换手率约2.90元。上述20.76是原E1相对指数财富差的账本分摊，**不是删除这批股票后必然损失20.76元**。旧周度分类口径的UNKNOWN约19.39元与本表也不同，不能混用。

## 同日期同行业替换实验

保留原E1其余股票及权重、模型、月初交易日期、费用和交易约束。对被排除的原持仓：

- P：把可匹配预算等分给当时同行业、原E1有分数、未被原组合选中的全部股票。
- PR：进一步要求对照股票与原持仓的排除原因相同。
- 未知行业、没有独立同行等无法匹配部分保留原持仓，不放宽规则，也不假定收益为零。
- O：原组合精确复放，净值与此前原账本一致。

预算加权覆盖率P为95.31%，PR为89.10%；对应原总资金平均31.63%和29.57%。这是**同行业对照的覆盖率**，不是此前13风格严格匹配的覆盖率，不能说完整风险匹配已经解决。

{table(cov,['mean_excluded_budget','mean_matched_budget','budget_weighted_coverage','mean_date_coverage','min_date_coverage','max_target_weight'])}

覆盖率、预算和max_target_weight单位%；mean_control_count为目标持仓数。P平均约105只，PR约81只，原约59只。共享少数同行时单只对照目标权重最高10%；并非所有日期都更分散、更低风险。

## 成本后账户：原选股确有更强历史表现

同日起点2021-01-11至2025-03-03，共1001交易日、50个月初决策。

{table(m,['cagr'])}

cagr为%，换手为年单边倍数，nav是初始1元终值。O−P复合年化差约5.29个百分点；下表统计量是**日净收益差均值×252**，与CAGR差不同。

{table(stats[stats.primary][['metric','comparison','n','mean','ci_low','ci_high','p_holm']],['mean','ci_low','ci_high'])}

两个预设主检验均在本轮Holm校正后通过：账户差约+5.25pp/年，普通95%区间[+1.80,+8.99]；独立匹配子组合H10约+1.00pp/事件，区间[+0.55,+1.49]。这只是已反复观察历史上的统计支持，校正不能抹掉此前研究选择偏差。

![账户与逐年贡献](accounts_years.png)

PR结果接近P；零成本O−P日收益差年化约5.34pp，主成本5.25pp，压力成本5.02pp，不能把差异主要解释为交易费用。相同的是行业目标资本占比，不是完全相同的风险、持仓数和集中度。

## H10与无法退出的事件

对每个月可匹配的被排除持仓单独建立初始1元的子组合，与其同行业对照比较，两边按当期匹配预算归一化。同一股票集合持有10交易日后独立尝试卖出。

50期中44期两边能完整退出；其余6期至少一边受交易限制，净退出收益保留缺失。44期结果不是原账户收益的机械分解，也不是所有50期都能实现的收益保证。

![固定期限事件](event_differences.png)

作为**结果后披露检查**，将全部50期按期末市值计算、只扣已发生入场成本，不假装完成退出，平均差约+0.948pp，区间[+0.514,+1.366]。这支持方向并非仅由删去6期造成，但市值收益不等于可执行净收益。

## 是否仅由2021年贡献

O−P终值差约22.44元/初始100元，其中2021年贡献约12.86元，约57.3%；2022、2023、2024及2025截至3月3日的贡献均为正。

{table(yr[['period','wealth_contribution']])}

2025为不完整年份。看到这一集中度后做的辅助留段检查：仅看原账户路径2022年以后的每日收益差，年化约+2.89pp、区间[+0.07,+5.67]；34个可退出H10事件差约+0.906pp、区间[+0.374,+1.491]。这是事后敏感性检查，不是新的盲测，也不是2022年重新现金开仓的账户。

## 买入时能够看到什么

这批股票的选择确实由当时已有的E1分数作出，未使用本轮未来收益重新挑名单。对被排除、行业已知的候选股票，每期在至少3只可评分股票的行业内计算RankIC，再按股票数汇总，周度H10 RankIC约{rank['mean']:.4f}，普通95%区间[{rank['ci_low']:.4f},{rank['ci_high']:.4f}]，共{rank['n']}个有效周信号。这是辅助排序证据，不是风格调整后的条件IC。

原选股相对同行通常具有更弱的近期收益，平均1日、5日、20日收益更低，60日收益略高，波动略高；市值对数并不更小。完整覆盖率和差异见[决策证据](DETAILS.md)。这些是信号时点已有特征的描述，尚未检验它们是否解释收益差，不能直接把原因命名为“反转”或“趋势回撤”。

## 本轮裁决

现在可以更有依据地说：**原E1在C池之外有值得继续验证的行业内选择信息；此前只在C池做机制实验，不能代表原组合全部Alpha。** 当前“行业内”仍混有其他风格、集中度、持有漂移和执行差异。

下一步应固定本轮股票范围、账户与对照合同，检验这块选择收益能否被简单反转、动量、波动等已知信息重建，并报告风险匹配支持范围；不要重新搜索pos窗口或从这些赢家反推新规则。此前完整13风格严格匹配覆盖不足，必须保留未识别部分。真正独立确认仍需冻结后才产生的信号及收益。

[方法与边界](METHOD.md) · [完整逐月、逐股票及信号时点证据](DETAILS.md) · [冻结协议](PROTOCOL.md) · [冻结配置](../../configs/{RUN}.json)。

73项测试、{v['count']}项主核验及{audit['count']}项披露核验通过；9条连续账户完整，原E1精确复放。模型、原预测和旧报告未改；Historical-proxy、严格PIT未认证、前瞻未完成。未提交、推送或部署。
''')
 original_top=stocks.groupby('instrument').wealth_contribution.sum().sort_values(ascending=False)
 rep=replacement[replacement.comparison=='O-P'].set_index('instrument').wealth_contribution.sort_values(ascending=False)
 prof=profiles[(profiles['mode']=='P')&profiles.feature.isin(['mom1','mom5','mom20','mom60','vol20','vol60','log_total_mv','turnover20'])]
 cases=pd.read_csv(D/'decision_cases.csv')
 report('DETAILS',f'''# 被排除持仓完整证据

## 原账户相对指数：逐年贡献

{table(origyears)}

以下全部为原排除持仓的相对指数贡献，不是同行业替换差。费用与现金仍单列在原账户，未强行分摊至排除持仓。

## 原排除持仓：正负各十只股票

{table(pd.concat([original_top.head(10),original_top.tail(10)]).rename_axis('instrument').reset_index())}

[完整股票×行业×原因]({link('original_excluded_stocks.csv')}) · [全部行业]({link('original_excluded_industries.csv')}) · [逐月×原因]({link('original_excluded_months.csv')}) · [按可匹配状态分摊]({link('original_excluded_by_matching.csv')})。持有延续但非当期目标的股票标为NOT_CURRENT_TARGET_LEGACY，不能冒充本期新买入。

## O−P替换实验：正负各十项贡献

{table(pd.concat([rep.head(10),rep.tail(10)]).rename_axis('instrument').reset_index())}

预算覆盖率不等于收益贡献覆盖率。原排除持仓20.76元贡献中，可直接对上当期匹配目标的贡献约17.29元；其余包括未知行业、无独立同行、延续持仓等，完整状态表已保留。

这张表与上一张回答不同问题：它包含买入原股票、避免买入同行对照、权重漂移及费用差；正贡献不一定是原买入股票自身上涨。

## O−P逐月终值差分配

{table(years[(years.comparison=='O-P')&(years.freq=='M')][['period','wealth_contribution']])}

单一共同链接尺度使各股票、各月份分别精确加总到22.44元左右；不是每月收益率直接相加。完整P/PR股票差和时期差见[股票]({link('replacement_stocks.csv')})、[时期]({link('replacement_periods.csv')})。

## 买入时特征，不用赢家反推规则

{table(prof[['feature','n_dates','mean_selected','mean_peers','mean_gap','selected_coverage','peer_coverage']])}

收益与波动为原小数单位，市值为对数；表内coverage为0到1。对每期已知权重单独归一化，再在日期间平均；两侧缺失支持可能不同。例如换手率原持仓覆盖低于对照，不能把差异当作同样本效应。

完整[特征表]({link('profile_summary.csv')})、[逐期原始特征均值及已知预算]({link('signal_profiles.csv')})、[全部{len(cases)}个原被排除目标决策]({link('decision_cases.csv')})均保留。决策表包括原E1分数、行业内分位、原13风格、原特征组分数贡献、同行候选清单、H10标签及该月原账本相对贡献。原始H10标签为价格窗口收益，可能无法执行；不与执行事件净收益混同。组分数贡献是模型会计，不是利润归因。

## 全部统计与缺失事件

{table(stats[['metric','comparison','cost','primary','n','mean','ci_low','ci_high','p','p_holm']],['mean','ci_low','ci_high'])}

日收益年化或H10每事件单位均pp，按metric区分。只有primary为True的两项属于本轮预设检验族，其余为辅助。所有历史研究选择偏差仍存在。

{table(sens[['metric','sample','n','mean','ci_low','ci_high']],['mean','ci_low','ci_high'])}

此表为看到结果后加做的披露检查，未改变目标和主裁决；2022_onward保留原账户路径，不是重新起点回测。标记到市值结果只扣入场成本，不假造退出可交易性。

[原始事件退出情况]({link('events.csv')}) · [周度行业内RankIC]({link('excluded_rank_ic.csv')}) · [全部逐期匹配与未匹配原因]({link('matching.csv')}) · [原账户逐年逐月收益]({link('periods.csv')})。
''')
 report('METHOD',f'''# 原持仓排除审计与对照合同

## 冻结与时间顺序

先冻结本轮分类、替换规则、统计族及成本，再封存完整目标，最后读取收益执行。旧结果已观察，属于历史探索；冻结本轮不构成真正事前独立确认。

使用原E1月初Q5实际目标，而不是缩减池重新选出的Q5。信号日行业分类来自原行业历史代理，且要求与候选面板一致；不一致保留原持仓。参考股票只要求同日原E1有限分数和已知同行，不要求13项风格完整或行业至少10只。选股不读取下一开盘的可交易性；执行时由原交易限制决定成交。

对每个原被排除股票，P选择全部同行业且不在任何原目标名单的候选，等分该股票目标预算。PR再筛选相同排除原因。不同原股票可共享同行，权重累加；因此控制持仓数、个股集中度与原组合不同。未知行业不能相互充作“同行”，无独立候选时不改变原持仓。

所有未改变原持仓在目标权重层面保持一致；账户随后的绝对持仓资金会因净值路径不同而变化。目标行业占比精确相同，成交和持有漂移后的行业比重未强制逐日相同。风格也未精确匹配。因此本轮属于部分识别。

P覆盖的是被排除预算的95.31%，不是整个原组合95.31%；占原总资金平均31.63%。PR相应为89.10%和29.57%。同业覆盖高不能替代此前严格13风格匹配覆盖低的事实。

## 原账本归因与替换效应分开

原相对指数归因沿用上一轮封存的monthly_decision分类，每个收益日只使用严格早于该日的最近月度信号。股票可能因涨跌、持仓漂移及指数表现而贡献相对财富；不能据此证明信号可预测，也不等同于从持仓删除该股的效果。费用、现金另列；旧周度状态分类19.39元不改写。

替换对照从相同现金1元开始完整执行，9条账户对应O/P/PR与三档成本。O须精确复放原1001日净值。主指标O−P日净收益差均值×252；65日循环块5000次，固定种子。O−PR、零成本、压力成本是预设辅助。

事件对照只抽取当期可匹配原排除持仓及其对应同行，将两边各自归一化到1元，H10独立持有后尝试完整清算。50个月是计划样本，未完成退出不能计算可执行净事件收益。有效44期按日期等权；不是按原账户每月资金占比加权的结果。月度3块Bootstrap5000，缺失月份仍留在日历网格。该事件比较与账户比较构成Holm2检验族，区间是普通点对点95%，不是多重校正同时区间。

## 辅助排序与已知信息

在被排除候选内，行业有至少3只成熟标签股票才计算当日E1 Spearman，再按候选数加权到日期；未知行业不纳入。没有把原来的至少10只要求换成优化后的最好门槛，只按冻结统计可计算下限3。13周日历块5000，全部辅助，不改变主检验。

决策表在分析结束后才合并H10和账本贡献；保留所有正负贡献，禁止按未来收益选新规则。source_date不晚于signal_date的形式核验只检查数据日期，不等于真实发布时间known_at认证。Historical-proxy标签保留。

## 证据与复核

73项测试；主分析{v['count']}项核验包括每条账户每日账本闭合、原净值复放、每期资金和行业占比、未匹配股票保留、同行与原名单不重叠、链接差分闭合。披露审计{audit['count']}项。

[冻结]({link('freeze.json')}) · [名单封存]({link('selection_complete.json')}) · [账户封存]({link('accounts_complete.json')}) · [分析封存]({link('analysis_complete.json')}) · [主校验]({link('validation.json')}) · [结果后披露审计]({link('disclosure_audit.json')})。本地完整目标与交易单保存在private/{RUN}/，旧模型和旧报告只读复用。

仍缺：严格PIT、独立前瞻、同其他风格与集中度的可行对照，以及可复现的经济原因。统计支持不能代替这几项。
''')
 save_json(R/'manifest.json',dict(files=record(sorted(R.glob('*.md'))+sorted(R.glob('*.html'))+sorted(R.glob('*.png'))),sources=record([Path(__file__),EP/'src/e1_excluded_holdings.py',EP/'src/e1_excluded_holdings_audit.py',EP/'tests/test_e1_excluded_holdings.py']),tests=73,main_checks=v['count'],disclosure_checks=audit['count'],visual_review='PENDING',forward='FORWARD_PENDING'))
 print('reports ready',flush=True)
if __name__=='__main__':main()

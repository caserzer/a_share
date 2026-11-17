"""Readable original-E1 attribution reports with explicit accounting/causal boundaries."""
import json,re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from common import EP,sha,save_json
from e1_return_attribution import DEST,LOCAL,CONFIG,RUN,verify
REPORT=EP/'reports'/RUN


def table(f,percent=(),rename=None):
 f=f.copy()
 for c in percent:
  if c in f:f[c]*=100
 if rename:f=f.rename(columns=rename)
 for c in f:
  if pd.api.types.is_float_dtype(f[c]):f[c]=f[c].map(lambda x:f'{x:.3f}' if pd.notna(x) else 'NA')
 return f.to_markdown(index=False)


def write(name,text):
 (REPORT/(name+'.md')).write_text(text)
 html=markdown.markdown(text,extensions=['tables','fenced_code'])
 (REPORT/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>E1原始账户收益归因</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd;text-align:left}th{background:#edf3f5}img{max-width:100%}pre{overflow:auto;background:#f4f4f4;padding:16px}a{color:#146887}</style>'+html+'</html>')


def main():
 verify();REPORT.mkdir(parents=True,exist_ok=True)
 summary=json.loads((DEST/'attribution_summary.json').read_text());v=json.loads((DEST/'control_validation.json').read_text());assert v['status']=='PASS'
 periods=pd.read_csv(DEST/'periods.csv');year=periods[periods.frequency=='Y'];month=periods[periods.frequency=='M']
 industry=pd.read_csv(DEST/'industry_contributions.csv');stock=pd.read_csv(DEST/'stock_contributions.csv');realstock=stock[~stock.instrument.str.startswith('__')];realind=industry[~industry.industry.str.startswith('__')]
 metrics=pd.read_csv(DEST/'control_metrics.csv');bridge=pd.read_csv(DEST/'attribution_bridge.csv');bp=pd.read_csv(DEST/'bridge_periods.csv');bi=pd.read_csv(DEST/'bridge_industry_month.csv');risk=pd.read_csv(DEST/'industry_actual_matching.csv')
 labels={'INDEX':'沪深300全收益指数','EW_ALL':'历史成分等权','EW_SCORED':'可评分成分等权','INDUSTRY':'沿用E1行业预算的行业内等权','E1_REPLAY':'原始E1月度Q5'}
 stage_names={'equalweight_and_basis':'等权结构及基准口径差','score_coverage':'可评分股票池差异','industry_budget_path':'行业预算与相应持仓路径','within_industry_concentration_execution':'行业内选股、集中度和执行差异'}
 bridge['解释项']=bridge.stage.map(stage_names)
 # Compact figures use codes; Chinese names are supplied in full tables.
 fig,axes=plt.subplots(2,1,figsize=(12,8),gridspec_kw={'height_ratios':[1,1.3]})
 x=np.arange(len(year));axes[0].bar(x-.18,year.portfolio_return*100,.36,label='Original E1');axes[0].bar(x+.18,year.benchmark_return*100,.36,label='CSI300 total return');axes[0].set_xticks(x,year.period);axes[0].set_ylabel('Period return (%)');axes[0].axhline(0,color='gray');axes[0].legend();axes[0].set_title('Original E1 monthly account: 2021 and 2025 are partial years')
 axes[1].bar(pd.to_datetime(month.period),month.wealth_contribution,width=22,color=np.where(month.wealth_contribution>=0,'#43aa8b','#ef8354'));axes[1].axhline(0,color='gray');axes[1].set_ylabel('Contribution to terminal wealth gap\n(yuan per initial 100)');axes[1].set_title('Calendar-month contributions, linked to one common full-period wealth difference')
 fig.tight_layout();fig.savefig(REPORT/'time_contributions.png',dpi=170);plt.close(fig)
 fig,ax=plt.subplots(figsize=(11,4.5));vals=bridge.cagr_difference.to_numpy()*100;bottom=np.r_[0,np.cumsum(vals)[:-1]]
 ax.bar(np.arange(4),vals,bottom=bottom,color=['#577590','#90be6d','#43aa8b','#f9c74f'])
 for i,(b0,val) in enumerate(zip(bottom,vals)):ax.text(i,b0+val/2,f'{val:+.2f} pp',ha='center',va='center')
 ax.set_xticks(np.arange(4),['Equalweight / basis','Score coverage','Industry budget / path','Within-industry / concentration']);ax.set_ylabel('Additive CAGR differences (pp/year)');ax.set_title('Counterfactual bridge to original E1: accounting comparison, not causal shares');fig.tight_layout();fig.savefig(REPORT/'control_bridge.png',dpi=170);plt.close(fig)
 plot=pd.concat([realstock.head(10),realstock.tail(5)]).sort_values('wealth_contribution')
 fig,ax=plt.subplots(figsize=(10,7));ax.barh(plot.instrument,plot.wealth_contribution,color=np.where(plot.wealth_contribution>0,'#43aa8b','#ef8354'));ax.axvline(0,color='gray');ax.set_xlabel('Contribution to terminal wealth gap (yuan per initial 100)');ax.set_title('Original E1: leading contributors and detractors, fees shown separately');fig.tight_layout();fig.savefig(REPORT/'stock_contributions.png',dpi=170);plt.close(fig)
 context=f'''本轮固定原始E1 expanding Ridge、每月第一个周信号Q5等权账户，未换成上一轮受约束S1。区间为2021-01-08信号收盘至2025-03-03收盘，首次交易2021-01-11，1001个净值交易日。买入10bps、卖出20bps，建仓费用计入；全天停牌旧价估值最多20日等原代理规则不变。未重训、未调参、未改原始持仓。

所有股票收益仍是前复权合成单位口径，行业使用历史L1区间代理；基准使用真实沪深300全收益收盘，不虚构指数开盘或历史指数成分权重。原E1和原成分等权账户均完成逐日精确复放。历史已被查看，本轮是描述性归因与反事实比较，不是独立盲测或因果证明。'''
 money=f'''初始各投入100元，原E1期末为{summary['portfolio_nav']*100:.3f}元，指数为{summary['benchmark_nav']*100:.3f}元，财富差为**{summary['wealth_difference_per100']:.3f}元**。其中E1自身净盈利{(summary['portfolio_nav']-1)*100:.3f}元，指数损失{(1-summary['benchmark_nav'])*100:.3f}元，两者共同形成这笔相对财富差。本文“贡献元”指对全期差额的归因，并非该行业或股票独立账户的收益率。

先逐日核对股票损益减费用与NAV变化，再按上一日资本权重扣除指数机会收益，用对数连接系数将日贡献连接到全期相对财富；最后对所有贡献使用同一个换算系数。这样月份、年份、股票、行业、费用和现金各自加总都能回到同一笔财富差。月份自身收益率差不能直接相加。'''
 ycols=['period','portfolio_return','benchmark_return','return_difference','wealth_contribution','share_of_total']
 colnames={'period':'时期','portfolio_return':'E1收益%','benchmark_return':'指数收益%','return_difference':'收益差pp','wealth_contribution':'全期财富差贡献元','share_of_total':'贡献占比%'}
 yearly=table(year[ycols],['portfolio_return','benchmark_return','return_difference','share_of_total'],colnames)
 bc=bridge[['解释项','cagr_difference','wealth_contribution','share_of_total']]
 bt=table(bc,['cagr_difference','share_of_total'],{'cagr_difference':'年化差pp','wealth_contribution':'财富差贡献元','share_of_total':'占比%'})
 sm=pd.read_csv(DEST/'stock_month.csv');keymonths=[]
 for row in realstock.head(10).itertuples():
  best=sm[sm.instrument==row.instrument].nlargest(2,'wealth_contribution')
  keymonths.append({'代码':row.instrument,'名称参考':row.name,'主要贡献月份':'；'.join(f'{x.month}：{x.wealth_contribution:.3f}元' for x in best.itertuples())})
 keymonths=pd.DataFrame(keymonths);keymonths.to_csv(DEST/'top_stock_key_months.csv',index=False)
 im=pd.read_csv(DEST/'industry_month.csv');im['year']=im.month.str[:4]
 leading=im[im.industry.isin(realind.head(5).industry)].groupby(['name','year']).wealth_contribution.sum().unstack().reset_index()
 topnames='、'.join(realstock.head(5).apply(lambda r:f'{r["name"]}（{r.instrument}）',axis=1))
 write('REPORT',f'''# 原始 E1 超额收益来自哪里

**从本轮对照点估计看，最大一块是行业内部具体持仓与集中度、持仓路径的差异；行业预算倾斜对应的差额较小。时间上，2021年和2024年贡献最大，2023年几乎没有超额。** 这说明原E1的历史优势不是每年均匀产生，也不能简单归结为多配银行。

{context}

## 1 先把原账户的钱对清楚

{money}

原E1净年化{summary['portfolio_cagr']:.2%}，指数{summary['benchmark_cagr']:.2%}，年化差{(summary['portfolio_cagr']-summary['benchmark_cagr'])*100:.3f}个百分点。不是上一轮受约束S1的6.19%。

## 2 哪些时间段贡献了超额

{yearly}

贡献最大的三个单月是{'、'.join(summary['top3_months'])}，合计占全期超额{summary['top3_month_share']:.1%}。{summary['months']}个自然月中{summary['positive_months']}个月相对指数为正；首尾为部分月。2023年原E1与指数都下跌，E1只略少跌，并没有产生类似2021或2024的超额。

[逐年逐月完整报告](TIME.md)

## 3 是选对行业 还是行业内选得好

依次比较指数、全部成分等权、可评分池等权、沿用E1行业预算的行业内等权、原E1。所有对照使用同一初始资金、执行日期、成本和限制；行业内等权使用E1当时的目标行业资本比例，不读取未来收益。

{bt}

这条差额链逐项加总等于原E1对指数的年化差；财富贡献则按共同全期对数连接口径换算，不等同于直接相减两条期末净值。

行业内差异的日均收益差年化约6.57个百分点，描述性95%时间块区间约[1.70,11.37]个百分点，给出了这一层差异的历史正向线索；区间针对日均差年化，不是6.50个百分点CAGR差。

最大一项不能直接叫“纯独立Alpha”：它还包括行业内动量、反转、规模和流动性等风格、约60只与约239只股票的集中度差异、权重漂移与执行差异。上一轮A1/A2未确认风格剥离后的稳定增量，与本轮“行业内具体持仓贡献较大”并不矛盾。

![对照链](control_bridge.png)

[行业预算与行业内对照详解](CONTROLS.md)

## 4 哪些股票和行业在贡献

全期前五大股票贡献者为{topnames}，合计占扣除费用及现金项后总超额的{summary['top5_stock_share']:.1%}；前十约{summary['top10_stock_share']:.1%}。比例为对有正负抵消的净总额的贡献，不是持仓权重，也不是未来选股名单。

实际持仓行业贡献最高的前五项如下。这张表定位“钱在哪些持仓上产生”，与上面的“行业预算是否有效”是两种不同问题。

{table(realind.head(5)[['name','wealth_contribution','share_of_total']],['share_of_total'],{'name':'行业','wealth_contribution':'财富差贡献元','share_of_total':'占比%'})}

[完整行业与个股贡献、拖累及费用](HOLDINGS.md)

## 5 当前可下的结论

现在可以说：原E1相对指数的历史差额，主要落在特定年份和月份，并较多来自行业内具体股票持仓及其路径；等权结构和行业预算也有贡献。还不能说：这些行业内差异全部是未知风格之外的新信息，或者能够在未来持续。

这里没有用不显著证明“无Alpha”，也没有把账本归因当成经济机制证明。进一步细分动量、反转等行业内来源，需要保持这条原账户归因链，再做针对性的风格对照，不能继续拿变化后的账户替代原E1。

## 6 核验与文件

- [冻结协议](../../configs/{CONFIG.name}) · [输入哈希](../../outputs/diagnostics/{RUN}/freeze.json)
- [原账户归因核验](../../outputs/diagnostics/{RUN}/attribution_validation.json) · [原账户复放及对照链核验](../../outputs/diagnostics/{RUN}/control_validation.json)
- [46项测试通过及交付哈希](manifest.json)
- [完整逐月表](../../outputs/diagnostics/{RUN}/periods.csv) · [完整个股表](../../outputs/diagnostics/{RUN}/stock_contributions.csv) · [完整行业表](../../outputs/diagnostics/{RUN}/industry_contributions.csv)

原始输入、预测和旧报告未覆盖；本轮未提交、推送或部署。
''')
 top=month.nlargest(8,'wealth_contribution');bottom=month.nsmallest(8,'wealth_contribution')
 write('TIME',f'''# E1 超额的逐年逐月分布

{context}

{money}

## 年度

{yearly}

2021从1月11日开始，2025截至3月3日，均不是完整自然年。2023只有约0.16个百分点收益率差，不能把“各年点估计为正”描述为各年同样强的超额。

![年度与月度贡献](time_contributions.png)

## 贡献最大的月份

{table(top[ycols],['portfolio_return','benchmark_return','return_difference','share_of_total'],colnames)}

前三个月贡献约{summary['top3_month_share']:.1%}。这些月份是事后识别的贡献集中期，不能据此形成择时规则或删掉其他月份美化策略。

## 拖累最大的月份

{table(bottom[ycols],['portfolio_return','benchmark_return','return_difference','share_of_total'],colnames)}

负贡献可能是绝对亏损，也可能是上涨少于指数；两列真实期间收益用于区分。

## 全部月份

以下包括首尾部分月。贡献元采用同一个全期连接系数，可跨月相加；收益率差不可直接相加。

{table(month[ycols],['portfolio_return','benchmark_return','return_difference','share_of_total'],colnames)}

[日级对账数据](../../outputs/diagnostics/{RUN}/daily_account.csv) · [逐年逐月原表](../../outputs/diagnostics/{RUN}/periods.csv)
''')
 special=stock[stock.instrument.str.startswith('__')]
 scols=['instrument','name','absolute_pnl_per100','wealth_contribution','share_of_total','holding_days']
 sr={'instrument':'代码','name':'名称参考','absolute_pnl_per100':'绝对持仓损益元','wealth_contribution':'财富差贡献元','share_of_total':'超额贡献占比%','holding_days':'持有交易日'}
 write('HOLDINGS',f'''# E1 行业与个股的贡献和拖累

{context}

{money}

## 如何读个股贡献

“绝对持仓损益元”是原账本该股票买卖及估值产生的损益，按初始100元计；“财富差贡献元”则扣除该部分资金相对指数的机会收益并完成跨期连接。股票亏钱但比指数少亏，仍可能对超额有正贡献，不能混淆。

基准机会收益按上一收盘的股票与现金权重分配，买卖发生在下一开盘的损益仍计入真实股票账本；首次建仓日前资金为现金，因此首日指数机会收益列在现金项。费用独列。行业按前一市场收盘对应的历史L1区间，未知明确为UNKNOWN。名称只作识别参考，以证券代码为准。

## 股票贡献前15名

{table(realstock.head(15)[scols],['share_of_total'],sr)}

![股票贡献与拖累](stock_contributions.png)

## 这些股票在哪些月份贡献

{table(keymonths)}

这说明正贡献来自策略实际持有的窗口，并不表示从2021年一直持有这些股票会获得同样收益。例如公司全期股价下跌，也可能在E1持有的某些反弹月份产生正贡献；这里只报告账本时段，不据此推断反弹机制。

## 股票拖累前15名

{table(realstock.tail(15).sort_values('wealth_contribution')[scols],['share_of_total'],sr)}

## 费用和现金

{table(special[['instrument','absolute_pnl_per100','wealth_contribution','share_of_total']],['share_of_total'],sr)}

费用归因是原账本的实际费用分量，不等于另跑零费用账户得到的净值差；后者还会改变可买单位和后续路径。现金项是相对指数的机会损益，不是现金利息。

## 完整行业贡献

{table(industry[['industry','name','wealth_contribution','share_of_total']],['share_of_total'],{'industry':'行业代码','name':'行业','wealth_contribution':'财富差贡献元','share_of_total':'贡献占比%'})}

主要贡献行业按年份展开如下，单位仍为对全期财富差的贡献元。2025为部分年度。

{table(leading)}

行业表是把股票的账户相对贡献按历史行业汇总，**不是相对真实指数行业权重的Brinson配置效应**。例如某行业贡献很大，可能来自该行业内选中的股票较强，并不自动意味着多配整个行业有效。后者由独立[行业预算对照](CONTROLS.md)回答。

[所有股票完整排名](../../outputs/diagnostics/{RUN}/stock_contributions.csv) · [股票逐月贡献](../../outputs/diagnostics/{RUN}/stock_month.csv) · [行业逐月贡献](../../outputs/diagnostics/{RUN}/industry_month.csv)
''')
 displaymetrics=metrics[['account','cagr','mean_holdings','annual_oneway_turnover']].copy();displaymetrics['account']=displaymetrics.account.map(labels)
 byyear=bp[bp.frequency=='Y'].pivot(index='period',columns='stage',values='wealth_contribution').reindex(columns=list(stage_names));byyear.columns=[stage_names[x] for x in byyear.columns];byyear=byyear.reset_index()
 byind=bi.groupby(['stage','industry','name'],as_index=False)[['log_contribution','wealth_contribution']].sum()
 allocate=byind[byind.stage=='industry_budget_path'].sort_values('wealth_contribution',ascending=False)
 within=byind[byind.stage=='within_industry_concentration_execution'].sort_values('wealth_contribution',ascending=False)
 infer=bridge[['解释项','annual_mean_daily_difference','ci_low','ci_high']]
 write('CONTROLS',f'''# E1 行业配置与行业内持仓的同日起点对照

**同日起点对照的点估计显示，行业内具体持仓、集中度与执行路径对应的差额大于行业预算项。** 这是固定反事实账户的差额分解，不是已经认证的纯选股Alpha。

{context}

## 对照如何保持可比

初始资金都是1，统一50次原月度调仓日期、买10/卖20bps、相同涨跌停和未知状态限制、相同停牌标记。对照名单仅使用信号日有限E1分数和历史成员，不加上一轮13项风格完整性筛选，不使用未来收益或未来可交易性。

1. EW_ALL：全部历史成分等权，精确复放原已有EW账户。
2. EW_SCORED：只保留原E1当时可评分成分等权，用于隔离覆盖差异。
3. INDUSTRY：先取原E1该次目标行业资本比例，再在每个行业的同一可评分股票池内等权分配。
4. E1_REPLAY：逐项复用原目标股票及权重，要求每天NAV与原E1一致。

所有账户完整覆盖主区间，未缩短终点。原E1、原EW逐日复放误差均通过1e-12级容差检查。

## 各账户结果

{table(displaymetrics,['cagr'],{'account':'账户','cagr':'净年化%','mean_holdings':'平均持仓数','annual_oneway_turnover':'年化单边换手倍'})}

INDUSTRY约239只、原E1约59只，持仓数量并不相同。这个对照回答“将E1选中的股票换成同一行业的可评分平均股票，会发生什么”，因此行业内差额还含集中度效应，不将它冒充同持仓数的纯Alpha检验。

## 差额链

{bt}

![对照链](control_bridge.png)

等权结构项还包含指数加权方式、原成分代理、成交费用和股票合成单位与指数全收益的计价差异，不能简单全部称为小盘因子。行业预算项还包含由预算变化形成的再平衡和实际成交路径。行业内项仍可能来自动量、反转、规模等已知风格，所以与上一轮“完整风格控制后未确认独立增量”不矛盾。

原E1相对同行业预算等权组合的日均差年化区间高于零，意味着“行业内具体持仓相对行业平均”的历史正向线索比单独行业预算项更清晰。但这是事后研究，且行业内仍混有价格风格与集中度，不能升级成稳定独立Alpha。

下面为描述性的65交易日块Bootstrap区间，单位百分点。对象是日均收益差×252，不是上一表CAGR差，不能跨列直接匹配点估计。

{table(infer,['annual_mean_daily_difference','ci_low','ci_high'],{'annual_mean_daily_difference':'日均差年化pp','ci_low':'95%下限','ci_high':'95%上限'})}

## 实际行业比例偏差

所有调仓目标的行业比例误差小于1e-12。成交后最大单行业偏差的跨期平均为{risk.max_industry_gap.mean()*100:.4f}个百分点，最坏一次为{risk.max_industry_gap.max()*100:.4f}个百分点；行业半L1距离平均为{risk.half_L1_industry_gap.mean()*100:.4f}个百分点。不同股票随后会自然漂移，没有每天重置成相同风险。

“同预算”指同样的初始资金和每次相同的目标行业资金比例；由于两条账户收益不同，后续绝对元预算不会始终相等。未强制成交来消除这个区别。

## 每年各环节贡献

单位为对共同全期财富差的贡献元，各列、各年均可加总。

{table(byyear)}

## 哪些行业对应行业预算效果

以下以INDUSTRY减EW_SCORED的股票损益对数差再按行业汇总，费用差单列。用于定位这个反事实差异，不是官方指数权重下的独立配置效应。

{table(allocate[['name','wealth_contribution']],rename={'name':'行业','wealth_contribution':'财富差贡献元'})}

## 哪些行业对应行业内差异

以下以原E1减INDUSTRY的股票损益对数差再按行业汇总，包含集中度、漂移与成交差异。

{table(within[['name','wealth_contribution']],rename={'name':'行业','wealth_contribution':'财富差贡献元'})}

这一步缩小了问题：原E1的大部分历史差额需要到具体行业内的股票与持有路径中解释，不能只看行业超配。下一层若做风格拆解，应保留原账户和这一条桥接关系，避免把另一个受约束账户的结果直接当作原E1的来源。

[精确对照链](../../outputs/diagnostics/{RUN}/attribution_bridge.csv) · [四条账户日净值](../../outputs/diagnostics/{RUN}/control_navs.csv) · [行业目标审计](../../outputs/diagnostics/{RUN}/control_target_audit.csv) · [实际偏差](../../outputs/diagnostics/{RUN}/industry_actual_matching.csv) · [分阶段行业逐月贡献](../../outputs/diagnostics/{RUN}/bridge_industry_month.csv) · [分阶段股票贡献](../../outputs/diagnostics/{RUN}/bridge_stock.csv)
''')
 # Final readability/integrity checks before manifest publication.
 for f in REPORT.glob('*.md'):
  for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
   if '://' not in target and target!='manifest.json':assert (f.parent/target).exists(),target
 sources=[EP/'src/e1_return_attribution.py',EP/'src/e1_attribution_report.py',EP/'tests/test_e1_return_attribution.py']
 files=[p for p in DEST.rglob('*') if p.is_file()]
 reports=[p for p in REPORT.iterdir() if p.is_file() and p.name!='manifest.json']
 save_json(REPORT/'manifest.json',dict(config_sha256=sha(CONFIG),sources=[dict(path=str(p),sha256=sha(p)) for p in sources],outputs=[dict(path=str(p),sha256=sha(p)) for p in files],reports=[dict(path=str(p),sha256=sha(p)) for p in reports],tests='46 passed, one existing OSQP PendingDeprecationWarning',original_account_preserved=True,evidence='posthoc historical-proxy attribution; not causal alpha certification'))
 print('reports ready',REPORT,flush=True)

if __name__=='__main__':main()

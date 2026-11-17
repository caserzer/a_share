"""Human-readable fixed factorial economic results, all hypotheses retained."""
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from e1_engineered_ablation import *
def table(a,percent=()):
 a=a.copy()
 for c in percent:a[c]*=100
 return a.to_markdown(index=False,floatfmt='.4f')
def link(f):return f'../../outputs/diagnostics/{RUN}/{f}'
def report(name,text):
 (R/(name+'.md')).write_text(text)
 (R/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>E1 工程特征经济消融</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd}th{background:#edf3f5}img{max-width:100%}a{color:#146887}</style>'+markdown.markdown(text,extensions=['tables','fenced_code'])+'</html>')
def main():
 for name in ['freeze','selection_complete','accounts_complete','analysis_complete']:verify(name)
 metrics=pd.read_csv(D/'metrics.csv');co=pd.read_csv(D/'comparisons.csv');ev=pd.read_csv(D/'event_statistics.csv');ic=pd.read_csv(D/'ic_statistics.csv');period=pd.read_csv(D/'joint_period_contributions.csv');stocks=pd.read_csv(D/'joint_stock_contributions.csv');ex=pd.read_csv(D/'exposure_gaps.csv')
 mainm=metrics[metrics.cost=='main'];primary=co[co.primary];v=json.loads((D/'validation.json').read_text())
 fig,axes=plt.subplots(1,2,figsize=(12,4.5))
 for st in STRATEGIES:
  a=pd.read_csv(D/'accounts'/(st+'__main.csv'),parse_dates=['date'])
  axes[0].plot(a.date,a.nav,label=st,lw=1.3)
 axes[0].xaxis.set_major_locator(mdates.YearLocator());axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y'));axes[0].axhline(1,color='gray',ls=':');axes[0].set_title('Same-start accounts, main cost');axes[0].legend(ncol=3,fontsize=8);axes[0].set_ylabel('NAV (initial cash = 1)')
 x=np.arange(len(primary));axes[1].errorbar(x,primary['mean']*100,yerr=np.vstack([primary['mean']-primary.ci_low,primary.ci_high-primary['mean']])*100,fmt='o',capsize=5)
 axes[1].set_xticks(x,primary.comparison);axes[1].axhline(0,color='gray',ls='--');axes[1].set_ylabel('Annualized daily-return contrast (pp)');axes[1].set_title('Primary effects: ordinary 95% intervals')
 fig.tight_layout();fig.savefig(R/'accounts_effects.png',dpi=170);plt.close(fig)
 annual=period[period.freq=='Y']
 fig,ax=plt.subplots(figsize=(8,4));ax.bar(annual.period.astype(str),annual.wealth_gap_contribution,color=['#278677' if x>0 else '#bd6565' for x in annual.wealth_gap_contribution]);ax.axhline(0,color='gray');ax.set_ylabel('Contribution per initial 100');ax.set_title('BOTH minus NONE: linked calendar contributions');fig.tight_layout();fig.savefig(R/'year_contributions.png',dpi=170);plt.close(fig)
 names={'NONE':'移除两组残差','POS':'仅加回区间位置残差','RISK':'仅加回波动与回撤残差','BOTH':'完整固定78特征模型','STYLE':'固定完整模型的当日13风格投影','E1':'原季度更新E1参照'}
 display=mainm.copy();display['说明']=display.strategy.map(names)
 report('REPORT',f'''# E1 工程特征能否贡献经济增量

**本轮未确认“区间位置 × 波动回撤”是稳定超额来源。** 区间位置对连续账户有正向点估计，但区间跨零；波动与回撤没有显示正向平均增量；组合交互也未通过预设检验。不能根据单个组合更好就宣布发现Alpha。

## 想验证什么

上一轮发现，区间位置解释了大量无法被13项风格重建的分数。这只能证明它改变模型排序，不能证明它赚钱。本轮把相同2021Q4模型中的两组残差信息有控制地删除、加回，直接检验账户与同日期H10收益。

固定原2021Q4整套78特征Ridge，不重新训练。股票样本仍为缩减C池，平均约192只，行业至少10只且13风格完整；不是原始沪深300完整覆盖。使用2021-10-08至2025-02-28的173个信号，其中41个月初信号交易；2021-10-11至2025-03-03账户共823交易日。原始2021-01-08起点的+4.84%不能直接放进本表对比。

“删除”只移除该组不能被13风格解释的分数贡献；该组可被风格解释的部分留在公共基底中。NONE并非没有任何位置或风险信息，POS/RISK也不是单因子策略。

## 实际账户结果

主成本买入10bps、卖出20bps，所有组合同日入场、行业名额相同、约39只等权，交易限制与缺失估值规则沿用原引擎。

{table(display[['strategy','说明','cagr','annual_oneway_turnover','max_drawdown']],['cagr','max_drawdown'])}

cagr、max_drawdown为%；annual_oneway_turnover为每年单边换手倍数。BOTH −0.11%，NONE −1.66%，仅加回位置POS +0.32%，仅加回风险RISK −3.47%；原更新E1 +1.68%。固定完整模型相对NONE的复合年化差约+1.55pp，但不能代替下面的配对统计。

![账户与主检验](accounts_effects.png)

## 三个预设主检验

主指标是日收益差的均值×252，不是两条账户CAGR相减。position是“有/无风险组”两种环境下加回位置的平均效应；risk反之；interaction衡量组合共同使用是否超过两组单独加入效应之和。三个双侧检验作Holm校正，普通95%区间未作同时区间调整。

{table(primary[['comparison','n','mean','ci_low','ci_high','p_holm']],['mean','ci_low','ci_high'])}

收益与区间单位pp。位置约+2.56pp，95%[−1.32,+6.54]，校正p约0.589；风险约−1.08pp；交互约+1.36pp，二者也不明确。结论均为**INCONCLUSIVE / 未确认正向经济增量**，而不是证明真实效应恰好为零。

Ridge分数本身是线性加总，本轮没有新增乘积项。这里的交互来自排序选股、持仓和交易路径的非线性，不是“模型学到非线性关系”的证明。

## 固定10日窗口没有重复账户改善

{table(ev[['comparison','n','mean','ci_low','ci_high']],['mean','ci_low','ci_high'])}

单位为每事件pp。两组共同加入相对NONE的H10净差约−0.078pp，95%[−0.387,+0.247]；位置平均效应约−0.007pp。full_vs_style只有40个有效配对，其余41个；未完成退出的事件保留缺失，未填零。

月度连续账户的正向点估计没有在H10固定窗口中同步出现，因此暂不能解释为稳定的10日预测收益。不同持有路径、实际持有超过10日、换手与特定时期都可能影响；本轮没有进一步辨认它们的因果份额。

零成本joint日收益差年化约+1.28pp，主成本约+1.47pp，压力成本约+1.98pp，三个区间均跨零。较低换手改善了一部分相对收益，但没有证据把全部差异解释为成本。

## 改善集中在哪里

BOTH相对NONE从初始100元形成约4.96元的终值差。对股票、费用、现金作对数链接后，按年份精确加总：

{table(annual)}

2021和2025为不完整年份。2022年贡献约+8.09元，随后2023、2024及2025截至终点均为负；这条差异没有表现出逐年稳定改善。每年贡献取决于所选链接规则，是账本分摊，不是可预测性证明。

![逐年贡献](year_contributions.png)

完整逐月与逐股票贡献、正负贡献名单见[逐项证据](DETAILS.md)。不只展示获利股票。

## 仍然不能解释什么

分数残差对13风格线性正交，**不保证选出的组合风险暴露相同**。例如BOTH相对NONE的平均vol20暴露更低约0.12个截面标准差；同一风格逐期最大差约0.39。行业目标名额严格相同，但交易受限后持仓与持有期间行业权重仍可不同。本轮不构成严格同风险净Alpha识别。

本轮是冻结完整模型的机制实验，不是原季度更新E1全股票池的因果分解；它也不覆盖此前约三分之一不在C池的原组合资金。所有历史均已反复研究，提前冻结本轮比较不能重新创造未见样本。行业与部分数据仍属Historical-proxy，严格PIT及前瞻未认证。

## 当前裁决与后续边界

保留“位置特征影响排序且可能影响持仓路径”这一弱线索；停止把位置+风险组合当成已经解释清楚的Alpha，也不据此搜索pos窗口、交互权重或调仓日。不能事后选择POS成为新主策略。

下一步若继续解释原E1，应优先审计尚未覆盖的原持仓与C池删样差异，并将原模型的逐期净贡献落实到具体股票和可获得信息；若缺少历史可用数据，就明确部分识别。需要独立前瞻才能判断稳定性，继续在相同历史做分数组合不能解决这点。

[方法](METHOD.md) · [逐项证据](DETAILS.md) · [原冻结协议](PROTOCOL.md) · [配置](../../configs/{RUN}.json) · [验证]({link('validation.json')})。

69项测试、{v['count']}项分析核验通过，另有173期分数代数与正交检查；18条账户完整、无估值中断，原E1参照精确复放。未重训、提交、推送或部署。
''')
 dictionary=pd.read_csv(OUT/'diagnostics/e1_alpha_mechanism_20261117/feature_groups.csv')
 report('METHOD',f'''# 四组消融合同与统计口径

固定2021Q4原模型含训练中位数、均值、标准差和Ridge系数。每期使用信号时点原工程特征，未来收益不参与选择。原历史输入可用时间仍未认证，故只称历史模拟。

1. 令完整分数作截面标准化、行业去均值为y，13风格同样截面标准化并行业去均值为X。
2. 对位置组和波动回撤组分别计算原系数×变换后特征的贡献，除以完整分数标准差并行业去均值，再取对X的线性投影残差p和v；rcond=1e-12。
3. NONE=y−p−v，POS=y−v，RISK=y−p，BOTH=y。四组分数共享全部其他信息；STYLE=projection(X,y)，E1为原季度更新参照。
4. 每组使用同一股票池、行业配额、ceil(n/5)只等权、同日原月初相位、下一交易日开盘执行。无阈值调整、无组合权重优化。

{table(dictionary[dictionary.mechanism_group.isin(['range_position','volatility_drawdown'])])}

NONE含其余工程特征残差及全部风格投影；STYLE不含任何工程残差。STYLE依赖当日固定完整模型的分数，是压缩诊断，不是独立的收益训练模型。

主检验以日净收益为r：
- position = ((rBOTH−rRISK)+(rPOS−rNONE))/2；
- risk = ((rBOTH−rPOS)+(rRISK−rNONE))/2；
- interaction = rBOTH−rPOS−rRISK+rNONE。
- joint = rBOTH−rNONE等其余比较预先列为辅助，不能事后升级为主检验。

823日共同时间轴，65交易日循环块Bootstrap5000次、种子20261117。近似双侧p使用中心化Bootstrap分布；三个主检验Holm校正。普通95%区间为点对点描述区间。自相关、非平稳、少数年度与长期重复探索限制仍存在，校正不能消除先前研究选择偏差。

H10每个原月初信号独立现金入场、固定股票单位、10交易日后独立尝试卖出，沿用主成本与交易限制；3个月块5000次。缺失腿使整个相应配对缺失；41期中STYLE一例无法完成退出。不能将事件收益机械串为账户收益。

辅助RankIC使用173期原周信号，其中171期具有截至终点成熟的H10标签，13周日历块5000次，缺周保留。BOTH用行业去均值分数，与上一轮原始FIXED78跨行业分数的0.0306不同；两者行业内排序与本轮选股相同，不应把本轮BOTH约0.0250误读为模型变了。

股票归因：每日账本组件先用log(1+r)/r链接，BOTH减NONE，各组件之和等于两账户终值比的对数；再用终值差/对数差缩放为初始100元的财富差分配。费用和现金作为独立组件保留。逐年逐月和逐股票各自闭合；不是个股简单持有收益，也不是因果配对。

冻结记录：[输入与代码]({link('freeze.json')})、[收益读取前名单封存]({link('selection_complete.json')})、[账户与交易单封存]({link('accounts_complete.json')})、[分析封存]({link('analysis_complete.json')})。所有原模型和原报告只读复用。
''')
 top=pd.concat([stocks.sort_values('wealth_gap_contribution',ascending=False).head(10),stocks.sort_values('wealth_gap_contribution').head(10)])
 report('DETAILS',f'''# 全部辅助结果与贡献证据

## 零成本、主成本、压力成本

{table(metrics,['cagr','max_drawdown'])}

{table(co[['cost','comparison','primary','mean','ci_low','ci_high','p','p_holm']],['mean','ci_low','ci_high'])}

比较单位pp，非主检验p仅辅助；不能挑一行最好的数字作为发现。

## 各信号的H10排序

{table(ic[['strategy','n','periods','mean','ci_low','ci_high']])}

均为原未来收益的Spearman，不是成本后收益，也不是控制所有风格的条件IC。NONE仍有正向IC，说明不能把完整模型预测力全部归给两组残差。E1跨行业原分数与其他去行业均值分数口径不同，表只作辅助观察。

## 逐月精确链接贡献

{table(period[period.freq=='M'])}

## 正、负各十项贡献

{table(top)}

证券代码保留，未猜测公司名称；完整证券、费用和现金见[全部贡献]({link('joint_stock_contributions.csv')})。这是BOTH−NONE的账户差异贡献，买入和少买均可能贡献正负，不能据此倒推出买入时的可预测理由。

## 持仓风格暴露差异

以下为BOTH相对各对照的目标权重加权截面标准分差，非实现持仓暴露；mean_gap带符号，mean_abs_gap和max_abs_gap反映逐期偏离。

{table(ex)}

[原始目标暴露]({link('target_exposures.csv')}) · [逐期IC]({link('rank_ic.csv')}) · [事件退出及缺失原因]({link('events.csv')}) · [各账户逐年逐月收益]({link('periods.csv')})。目标和交易单包含完整证券列表，保存在本地private/{RUN}/，未把缺失数据当成零。
''')
 save_json(R/'manifest.json',dict(files=record(sorted(R.glob('*.md'))+sorted(R.glob('*.html'))+sorted(R.glob('*.png'))),tests=69,analysis_checks=v['count'],structural_signal_checks=173,visual_review='PENDING',sources=record([Path(__file__),EP/'src/e1_engineered_ablation.py',EP/'tests/test_e1_engineered_ablation.py']),forward='FORWARD_PENDING'))
 print('reports ready',flush=True)
if __name__=='__main__':main()

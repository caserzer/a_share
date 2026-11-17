"""Fixed style tests, including explicit zero-support and exploratory-selection limits."""
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from e1_excluded_styles import *
def table(a,percent=()):
 a=a.copy()
 for c in percent:a[c]*=100
 return a.to_markdown(index=False,floatfmt='.4f')
def link(f):return f'../../outputs/diagnostics/{RUN}/{f}'
def report(name,text):
 (R/(name+'.md')).write_text(text)
 (R/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>E1 被排除持仓风格检验</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd}th{background:#edf3f5}img{max-width:100%}a{color:#146887}</style>'+markdown.markdown(text,extensions=['tables','fenced_code'])+'</html>')
def main():
 for n in ['freeze','selection_complete','accounts_complete','analysis_complete']:verify(n)
 audit=json.loads((D/'support_audit.json').read_text())
 for f in audit['files']+audit['sources']:assert sha(f['path'])==f['sha256']
 amendment=json.loads((D/'evaluation_amendment.json').read_text())
 for f in amendment['original_source']+amendment['evaluation_source']:assert sha(f['path'])==f['sha256']
 metrics=pd.read_csv(D/'metrics.csv');stats=pd.read_csv(D/'statistics.csv');coverage=pd.read_csv(D/'coverage_summary.csv');support=pd.read_csv(D/'support.csv');feas=pd.read_csv(D/'feasibility_summary.csv');ic=json.loads((D/'conditional_statistics.json').read_text());v=json.loads((D/'validation.json').read_text())
 mainm=metrics[(metrics.cost=='main')&(metrics.strategy!='SM')].copy();primary=stats[stats.primary]
 fig,axes=plt.subplots(1,2,figsize=(12,4.5))
 for st in ['O','REV','MIX','MOM','LOWVOL','HIGHVOL']:
  a=pd.read_csv(D/'accounts'/(st+'__main.csv'),parse_dates=['date']);axes[0].plot(a.date,a.nav,label=st,lw=1.4 if st in ['O','REV'] else .9)
 axes[0].axhline(1,color='gray',ls=':');axes[0].set_title('Same-count style replacements, main cost');axes[0].set_ylabel('NAV from initial cash = 1');axes[0].xaxis.set_major_locator(mdates.YearLocator());axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y'));axes[0].legend(ncol=3,fontsize=8)
 chosen=stats[(stats.cost=='main')&(stats.metric=='annual_daily')&stats.comparison.ne('O-SM')];x=np.arange(len(chosen))
 axes[1].errorbar(x,chosen['mean']*100,yerr=np.vstack([chosen['mean']-chosen.ci_low,chosen.ci_high-chosen['mean']])*100,fmt='o',capsize=4);axes[1].axhline(0,color='gray',ls='--');axes[1].set_xticks(x,chosen.comparison,rotation=25);axes[1].set_ylabel('Annualized daily-return difference (pp)');axes[1].set_title('Ordinary 95% intervals; most contrasts auxiliary')
 fig.tight_layout();fig.savefig(R/'style_accounts.png',dpi=170);plt.close(fig)
 sm=support[support.test=='SM'].groupby('status').agg(groups=('budget','size'),budget=('budget','sum')).reset_index()
 fig,ax=plt.subplots(figsize=(9,4));ax.barh(sm.status,sm.groups,color='#b86b63');ax.set_xlabel('Industry-date groups');ax.set_title('Strict style matching: zero supported groups');fig.tight_layout();fig.savefig(R/'matching_support.png',dpi=170);plt.close(fig)
 report('REPORT',f'''# 被排除持仓：短期反转成为优先核验线索

**预设的简单反转规则给出了接近原E1的账户表现，但尚不能宣布它解释了全部Alpha。** 严格13风格匹配没有可行支持；辅助条件排序也未确认控制风格后的独立信息。

## 这次只改变什么

固定上一轮P对照可匹配的原被排除持仓，以及原50个月初交易日期。在各自行业内，以原匹配股票和同行未入选股票的并集为候选，重新按简单规则选相同数量股票，保留同样行业预算；其他原E1持仓不变。简单规则允许选回原股票。

可支持比较的预算平均占原总资金31.60%，占被排除预算约95.21%。因此下面策略都仍含大部分未改变的原E1持仓，并使用E1确定的行业预算和研究范围；**不是独立的全市场反转策略，也不是从零复制整个E1。**

- REV：1日、5日收益分位均值的相反数，买近期跌得较多者。
- MOM：20日、60日收益分位均值，买趋势较强者。
- LOWVOL/HIGHVOL：20日、60日波动分位均值的负/正方向，两者均固定保留。
- MIX：反转、动量、高波动三个组件再取分位、等权相加。高波动方向参考了上一轮已观察的特征差异，不属于独立发现。

无新模型训练，无窗口、权重或调仓日期搜索。原行业至少10只限制未重新引入。

## 同数量、同行业预算账户结果

共同区间2021-01-11至2025-03-03，1001交易日。买入10bps、卖出20bps。

{table(mainm[['strategy','cagr','nav','annual_oneway_turnover','holdings']],['cagr'])}

CAGR为%，单边换手为年倍数，holdings为实际日均持仓。目标持仓数每期与原组合严格相同；成交和旧仓延续导致实际持仓数略有不同。

原E1净年化+4.84%，REV +4.56%；二者复合年化相差约0.29个百分点。配对日收益差均值年化仅约+0.247pp，普通95%区间[−2.16,+2.64]。该比较是预先列出的辅助项，**未显著不同不等于统计等价**；本轮没有预先定义等价界限，不能说收益已被完全复制。

![账户与差异](style_accounts.png)

按行业组等权计算，REV与原选股的平均名单重叠约34.9%，所以也不是简单选回全部原股票后机械获得同样收益。但这种近似表现是否稳定、是否覆盖同一收益路径，仍待下一轮冻结检验。

## 预设主检验没有确认新独立Alpha

{table(primary[['metric','comparison','status','n','mean','ci_low','ci_high','p_holm']],['mean','ci_low','ci_high'])}

年化日收益或H10事件收益的单位均为pp，按metric区分。O−MIX日收益差年化+3.78pp，普通区间[+0.59,+7.12]，但保留原计划Holm4检验族后p约0.094，未通过。没有因为两个匹配检验不可估计而缩小检验族。

在归一化的可支持子组合中，原E1−MIX的H10净事件差约+0.302pp，普通区间[−0.372,+1.008]，46个可执行配对，未通过。REV并非本轮主基准，不能看到其接近原E1后事后改成主检验；本轮也没有额外补跑REV的H10来寻找有利结论。

## 为什么严格风格匹配无法裁决

在原被排除且能找到同行的521个行业日期组内，要求不使用任何原选中股票、13风格暴露差各不超过0.25个全截面标准差、对照个股权重不超过该组原个股最大权重：

{table(sm)}

结果是0组可行：99组原股票风格缺失，58组同行数量不足以容纳预算和权重上限，364组线性约束不可行。所有不支持组保留原持仓，因此SM账户机械等于原O。

**SM相等是没有发生替换，不是匹配后Alpha消失。** 该分支的收益估计、p值标为不可用，样本数为0；不能读取SM净年化+4.84%作比较结论。

![匹配失败原因](matching_support.png)

额外的纯结构审计发现，364个不可行组中331组，仅看至少一个单独风格在权重上限下的可达到范围，就已经无法满足0.25容差；其余33组属于联合约束。详细范围见[证据](DETAILS.md)。这证明在当前合同下缺少可比支持，不证明是哪项风格创造了收益；容差和权重上限未放宽。

## 控制风格后的排序信息

辅助周度检验保留被排除、行业已知、13风格完整的候选，不要求行业至少10只。将E1和H10收益的截面分位分别对13风格分位与行业哑变量回归，计算两组残差的相关：

条件RankIC **{ic['mean']:.4f}**，普通95%区间 **[{ic['ci_low']:.4f},{ic['ci_high']:.4f}]**，{ic['n']}个有效周信号，未确认独立关联。

这只控制所指定的线性秩关系，且仍删除缺失风格样本；它与上一轮行业内原始RankIC的估计量和覆盖不同，不能简单相减作为“解释了多少Alpha”。

## 当前判断与下一步

这轮使“短期反转能够解释部分表现”成为更具体、可证伪的候选，而不是继续围绕pos60或复杂交互寻找解释。但目前既不能确认Ridge有独立Alpha，也不能断言全部收益只是反转。

下一轮应保留REV原公式、原比较范围与交易合同，冻结原E1相对REV的固定期限净收益、逐年路径和前瞻差异检验；不能从本轮五个规则中挑赢家，再把同一历史包装为新确认。严格匹配缺乏支持的问题要单独保留，不能靠继续放宽风险边界得到结论。

[完整证据](DETAILS.md) · [方法与零支持修正](METHOD.md) · [冻结协议](PROTOCOL.md) · [配置](../../configs/{RUN}.json)。

80项测试、{v['count']}项主核验通过；21条账户完整，原O精确复放。旧模型、预测、报告未改；历史反复探索、Historical-proxy、严格PIT未认证、前瞻未完成。未提交、推送或部署。
''')
 periods=pd.read_csv(D/'period_contributions.csv');profiles=feas.sort_values('groups_blocked',ascending=False)
 report('DETAILS',f'''# 固定风格比较的全部证据

## 全部成本与账户

{table(metrics,['cagr'])}

SM是原持仓的零支持回退复放，不是成功匹配的投资组合；表中数值仅用于账本核验。主成本10/20bps，零成本0/0，压力成本30/80bps。

## 全部比较

{table(stats[['metric','comparison','cost','primary','status','n','mean','ci_low','ci_high','p','p_holm']],['mean','ci_low','ci_high'])}

缺失不是零。REV、MOM和两个波动方向的p是辅助，不能据此重新选择主模型或主结论。所有区间为普通点对点95%，非同时区间；多重校正仍不能清除此前历史搜索偏差。

## 支持范围

{table(coverage,['mean_covered_total_budget','excluded_budget_coverage','prior_P_budget_coverage'])}

预算覆盖单位%。BASE只有一个行业日期组因原输入缺失而保留；SM所有组均不支持。[逐组原因]({link('support.csv')}) · [逐期资金覆盖]({link('coverage.csv')}) · [各规则行业组名单重叠]({link('baseline_overlap.csv')})。

## 不可行约束的可达到范围

{table(profiles)}

groups_blocked表示单独看这一风格已经不可行的组数，各风格可以同时阻断同一个组，不能相加。max_required_gap是对照个股权重上限下离原均值最近仍需容忍的差，单位全截面标准差；只作支持范围诊断，未拿它搜索更宽容差。

[逐行业日期、逐风格的目标与可达上下界]({link('feasibility_ranges.csv')})。364个LP不可行组中331组被至少一个单变量界限阻断，另外33组仅在联合约束下不可行。

## O−MIX逐年和逐月贡献

{table(periods[periods.comparison=='O-MIX'])}

这是对两条账户终值差的链接分摊，非逐期收益率直接相加，也不是经济因果。[完整股票贡献]({link('stock_contributions.csv')})。O−SM零差异对应未替换，不能归因到任何风格机制。

## 辅助条件排序

{table(pd.DataFrame([ic]))}

[每周样本数、剩余自由度及条件IC]({link('conditional_ic.csv')})。晚期未成熟标签保留不可估计。缺失样本不补零。原始分数、目标与交易单在本地private/{RUN}/，完整原预算和行业规则保留。

[事件退出情况]({link('events.csv')}) · [账户逐年逐月收益]({link('periods.csv')}) · [主核验]({link('validation.json')}) · [匹配结构核验]({link('support_audit.json')})。
''')
 report('METHOD',f'''# 固定风格规则与部分识别合同

## 无未来收益的名单生成

固定上一轮P可匹配原被排除名单与每个股票的同行候选，并集内允许简单规则重新选回原股票。原其他持仓完全保留；候选不包括这些保留股票。行业内原匹配名额k与总预算固定，简单规则按分数降序、证券代码升序选k只等权。

所有六个基础输入mom1/mom5/mom20/mom60/vol20/vol60必须有限；候选缺失者不评分，若原匹配股票有任何一只缺失，则整个行业组对全部简单规则保留原配置。各规则共用同一候选支持范围，不能为某条规则单独扩大。

各输入在当期行业候选内转百分位，REV为短期两项负均值，MOM为中期两项均值，HIGHVOL为两项波动均值，LOWVOL取负；MIX将REV/MOM/HIGHVOL组件再转分位等权平均。没有训练系数和优化窗口。高波动方向基于已经观察过的描述线索，因此MIX仍属历史探索设计。

## 严格13风格匹配

对原P行业组要求原股票13风格均已知，对照池仅为原P中未被原选中的同行、13风格完整者。全信号日所有风格完整原评分股票作为标准化基准，不使用行业至少10只门槛。

原组风格目标按原权重求均值。线性规划限制总预算相同、每个对照权重不超过原组个股最大权重、13项各自偏差不超过0.25SD；目标函数为对照距原风格均值的平方距离加权和，微小代码顺序项用于确定性选择。目标函数不含E1或未来收益。

不可行、原风格缺失或同行容量不足均保留原组，不降标准，不减少必要风格。匹配组为空时，没有可识别处理差。实际SM账户只是原配置复放，不能拿零差当作假设成立。

## 统计族与时序

原计划四项主检验：O−MIX日净收益差均值年化、归一化可支持原子组合−MIX的H10净事件差、O−SM日差、匹配原子组合−独立风格对照H10差。每日65交易日循环块5000，事件3个月日历块5000，固定种子20261117。未支持项为NaN且n=0；仍按预设4项Holm而不是缩小族，故O−MIX校正p约0.094。

事件是同日新现金入场、固定单位持有H10、尝试完整退出，不等同于月度连续账户。46/50个BASE事件两边可执行退出，无法退出不填零。SM无匹配事件。

条件排序是辅助：在每周被排除样本中取13风格完整、已知行业、成熟H10，控制13风格分位与行业哑变量；对E1分位和未来收益分位分别取回归残差，残差相关即所报告条件RankIC。要求剩余自由度至少30；该筛选用于统计可计算性，非交易规则。13周日历块5000，无确认性宣称。

## 零支持求值修正

原冻结脚本未覆盖“0个匹配组产生无列CSV、无子组合事件列”的边界。支持计算完成后、查看本轮经济结果前，保留原脚本与目标不变，新建仅供求值的副本，增加空表与缺列处理，并将零支持统计显式标为不可用。没有改动规则、阈值、名单、费用、原检验族或原冻结文件。

[修正记录]({link('evaluation_amendment.json')})记录原代码与求值副本的哈希；源码分别为src/e1_excluded_styles.py和src/e1_excluded_styles_evaluate.py。结构支持诊断另存src/e1_excluded_styles_support.py，只检查可达范围，未生成新组合。

## 边界与核验

相同目标持仓数和行业预算不保证持有期间风险相同；保留部分原E1是本实验控制设计的一部分，不能把REV的账户称作独立可部署的反转模型。未显著收益差不等于等价，未预设等价界限，也没有重新命名事后赢家为主规则。

80项测试、{v['count']}项主核验涵盖账本闭合、原O复放、行业预算、原目标数量、无支持组保留、SM机械复放与链接归因。额外结构审计验证了零支持估计不可用及不可行风格范围。

[冻结]({link('freeze.json')}) · [名单封存]({link('selection_complete.json')}) · [账户封存]({link('accounts_complete.json')}) · [分析封存]({link('analysis_complete.json')})。严格PIT、独立前瞻与经济因果仍未认证。
''')
 save_json(R/'manifest.json',dict(files=record(sorted(R.glob('*.md'))+sorted(R.glob('*.html'))+sorted(R.glob('*.png'))),sources=record([Path(__file__),EP/'src/e1_excluded_styles.py',EP/'src/e1_excluded_styles_evaluate.py',EP/'src/e1_excluded_styles_support.py',EP/'tests/test_e1_excluded_styles.py']),tests=80,main_checks=v['count'],visual_review='PENDING',forward='FORWARD_PENDING'))
 print('reports ready',flush=True)
if __name__=='__main__':main()

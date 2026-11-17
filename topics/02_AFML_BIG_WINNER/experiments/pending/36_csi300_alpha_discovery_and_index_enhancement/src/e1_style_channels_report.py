"""Group diagnostics with explicit teacher dependence and benchmark limitations."""
import re
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from e1_style_channels import *
LABELS={'price':'价格动量与反转','risk':'波动与市场风险','liquidity':'流动性','size':'市值'}

def table(a,percent=()):
 a=a.copy()
 for c in percent:a[c]*=100
 return a.to_markdown(index=False,floatfmt='.3f')
def link(x):return f'../../outputs/diagnostics/{RUN}/{x}'
def report(name,text):
 (R/(name+'.md')).write_text(text);html=markdown.markdown(text,extensions=['tables','fenced_code']);(R/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>E1 风格约束来源</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd;text-align:left}th{background:#edf3f5}img{max-width:100%}a{color:#146887}</style>'+html+'</html>')

def main():
 verify();verify('selection_complete');verify('accounts_complete');verify('analysis_complete')
 metrics=pd.read_csv(D/'metrics.csv');m=metrics[metrics.cost=='main'].set_index('strategy');comparisons=pd.read_csv(D/'comparisons.csv');c=comparisons[comparisons.cost=='main'].set_index('comparison');exposure=pd.read_csv(D/'I_exposure_summary.csv');recon=pd.read_csv(D/'score_reconstruction.csv');overlap=pd.read_csv(D/'target_overlap.csv');events=pd.read_csv(D/'event_comparisons.csv');replacements=pd.read_csv(D/'replacement_outcomes.csv');stock=pd.read_csv(D/'stock_contributions.csv');periods=pd.read_csv(D/'period_contributions.csv');validation=json.loads((D/'validation.json').read_text());assert validation['status']=='PASS'
 groups=[]
 for g in GROUPS:groups.append(dict(风格组=LABELS[g],仅加该组净年化=m.loc['only_'+g,'cagr'],相对I年化差=c.loc['only_'+g,'cagr_difference'],去掉该组净年化=m.loc['without_'+g,'cagr'],相对F年化改善=c.loc['remove_'+g,'cagr_difference']))
 groups=pd.DataFrame(groups);percent=list(groups.columns[1:]);base=m.loc[['I','F','B','REV','MOM','MIX','COPY']].reset_index()
 fig,ax=plt.subplots(figsize=(10,4));x=np.arange(4);ax.bar(x-.18,[c.loc['only_'+g,'cagr_difference']*100 for g in GROUPS],.36,label='Only group minus I');ax.bar(x+.18,[c.loc['remove_'+g,'cagr_difference']*100 for g in GROUPS],.36,label='Remove group minus F');ax.set_xticks(x,list(GROUPS));ax.axhline(0,color='gray');ax.set_ylabel('Net CAGR difference (pp)');ax.set_title('Fixed group diagnostics: effects overlap, do not add');ax.legend();fig.tight_layout();fig.savefig(R/'group_effects.png',dpi=160);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,5));ax.barh(exposure['style'],exposure.mean_I_minus_B);ax.axvline(.25,color='gray',ls='--');ax.axvline(-.25,color='gray',ls='--');ax.axvline(0,color='black',lw=.6);ax.set_xlabel('Mean target exposure I minus B (cross-sectional SD)');ax.set_title('B is a directional style reference, not a neutral portfolio');fig.tight_layout();fig.savefig(R/'reference_exposures.png',dpi=160);plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,4));ax.bar(base.strategy,base.cagr*100,color=['#577590','#ef8354','#f9c74f','#90be6d','#90be6d','#90be6d','#43aa8b']);ax.axhline(0,color='gray');ax.set_ylabel('Net CAGR (%)');ax.set_title('Same industry slots: independent rules vs teacher-dependent COPY');fig.tight_layout();fig.savefig(R/'replication.png',dpi=160);plt.close(fig)
 context='主区间2021-01-08信号至2025-03-03，原月初50次调仓、1001交易日。沿用上轮C样本、每期约39只、相同行业名额和10/20bps费用；I是仅固定行业名额的E1，F是加全部风格约束的E1，均不是原完整E1账户。原模型、预测、阈值未修改。'
 report('REPORT',f'''# E1 风格约束的收益损失来自哪里

**本轮损失最集中在价格动量与反转组。更关键的是，约束参考B本身偏向中期强势加短期回撤：把E1限制在B附近，是把组合推向这一特定风格，并非只移除风险。因此，约束后亏损不能直接证明原E1的收益都由已知风格解释。**

{context}

## 四组固定对照

I净年化约+0.88%，F约−6.42%。每组分别做“只加入该组”和“在全部约束中去掉该组”，没有按收益搜索最佳子集。

{table(groups,percent)}

单位均为百分数或百分点。价格组包括1/5/20/60日收益；风险组为20/60日波动、60日beta与特质波动；流动性组三项、市值组两项。组效应有交互，不能把四组改善加总或叫作唯一贡献比例。

![固定风格组](group_effects.png)

只加价格组，净年化约−4.59%；相对I下降约5.47pp。从全部约束中去掉价格组，净年化回到−1.49%，相对F改善约4.93pp。日均差年化的描述性区间分别约[−10.29,−0.78]pp和[+1.55,+8.97]pp。其他组的对应区间均跨零；多项结果只作历史描述，不作独立确认或择优部署。

零费用下只加价格组仍使年化下降约5.53pp，全部约束下降约7.38pp。因此这个差异主要不是额外交易成本造成的；仍包含具体持仓与路径变化。

## 为什么 B 会改变 E1 的方向

I相对B的目标暴露平均差：5日收益约+0.552个截面标准差，60日收益约−0.443个标准差。换言之，B的5日收益更低、60日收益更高。I在5日收益维度有92%的调仓超出B±0.25标准差，在60日维度有72%。这两项经常要求调整股票。

“B近期跌得更多、中期更强”是相对比较，并不保证绝对收益符号。约束接近边界不等于已识别该变量的因果贡献；本轮只独立识别到四项价格约束这一组，未事后逐个挑选期限。

![参照暴露](reference_exposures.png)

B在当前样本与交易合同下净年化约−7.75%。把E1向一个表现差且有明确方向的参照靠拢后变差，不能视作公平的“全部风格中性化认证”。此前P1/P2/P3证据不足的结果仍保留，但也不能将其解读为原E1不存在Alpha。

## 简单风格能否复制

{table(base[['strategy','cagr','fees','annual_oneway_turnover']],['cagr'])}

REV为短期反转，MOM为20/60日动量，MIX为两者等权，均不读取E1、不拟合收益权重。它们没有复现I账户表现。COPY用当日13项风格与行业拟合E1分数，净年化约+0.66%，接近I的+0.88%，但二者差异的描述性区间很宽，不能宣布经济等价。

COPY平均解释约{recon.r2.mean():.1%}分数方差、排序相关约{recon.rankcorr.mean():.3f}、留一股票重建Q²约{recon.loo_Q2.mean():.3f}。这给出“E1包含可由风格组合重建的信息”的线索；COPY仍需要E1分数，不是可独立替代模型。且这里只复制了行业名额受约束的I，尚未复制原完整E1的4.84%账户。

![复制比较](replication.png)

## 当前判断

1. 价格组是本轮约束损失的主要定位，尤其应注意B对短期与中期收益的方向要求；尚未逐项识别哪个期限是独立来源。
2. 简单反转、动量及等权组合未复制E1；不能用它们的失败否定更一般的风格组合，也不能继续搜索最佳混合权重。
3. 风格复制分数具有一定重建能力，经济表现接近I但依赖E1。接下来若要证明“可以简化模型”，必须建立不借用当日E1的独立复制方法，并保留新数据验证；本轮未训练新模型。

全部结果属于反复查看后的历史代理探索。没有发现经过独立确认的Alpha，也没有证实已知风格完全解释原策略。真实前瞻仍未完成。

[风格约束与股票替换](CHANNELS.md) · [简单规则与复制边界](REPLICATION.md) · [执行记录](EXECUTION.md) · [全部30条账户指标]({link('metrics.csv')}) · [完整逐年逐月]({link('periods.csv')})。
''')
 industry=pd.read_parquet(PRIVATE/'industry.parquet');industry['instrument']=industry.ts_code.str[-2:]+industry.ts_code.str[:6];names=industry.sort_values('in_date').groupby('instrument')['name'].last()
 ss=stock[stock.comparison=='only_price'].copy();ss['name']=ss.instrument.map(names).fillna(ss.instrument);sp=pd.concat([ss.nsmallest(10,'wealth_difference_contribution'),ss.nlargest(5,'wealth_difference_contribution')]);pp=periods[(periods.comparison=='only_price')&(periods.freq=='M')];pp=pd.concat([pp.nsmallest(6,'wealth_difference_contribution'),pp.nlargest(4,'wealth_difference_contribution')]);rep=replacements[replacements.strategy=='only_price'].copy();freq=rep.groupby(['direction','instrument']).size().rename('signal_count').reset_index();freq['name']=freq.instrument.map(names);freq=pd.concat([g.nlargest(10,'signal_count') for _,g in freq.groupby('direction')]);write(freq,'frequent_price_replacements.csv')
 report('CHANNELS',f'''# 风格约束接触与持仓替换

想验证什么：哪类约束实际改变E1名单，以及这种变化对应哪些收益差。

怎么比较：13项风格划为四个不重叠组，400次固定优化全部保留。组合行业名额、持仓数和原E1排序目标不变；参考仍为B，容差固定0.25截面标准差。没有将最赚钱的删除组设置为新策略。

各维度I与B的平均暴露差和超出容差的调仓比例：

{table(exposure,['outside_fraction'])}

outside_fraction按百分数展示。所有目标暴露、F及各组接近边界的情况完整保存。整数选股不存在可以简单解释为收益因果的连续影子价格；本轮未作这种归因。

主成本下各组配对日收益差年化和描述性95%区间：

{table(comparisons[(comparisons.cost=='main')&~comparisons.comparison.str.startswith('replicate_')][['comparison','annual_daily_difference','ci_low','ci_high']],['annual_daily_difference','ci_low','ci_high'])}

## 价格组频繁换掉或加入的股票

以下为相对I的目标名单变化，名称为参考；ADDED/REMOVED只说明实际选择变化。它们不是一一匹配的因果对照。

{table(freq)}

对应账户的股票贡献差，负数意味着价格约束后的账户在该股票项上更差，既可能是卖掉赢家，也可能是买入亏损者；不能只看负号区分两者。这里每项贡献按该对账户的终值财富差连接，其他组使用自己的连接系数，不跨组加总。

{table(sp[['instrument','name','wealth_difference_contribution']])}

主要月份：

{table(pp[['period','wealth_difference_contribution']])}

完整替换记录同时给出当期E1分数、13项标准化暴露及后续H10毛收益。H10是描述性标记，不是连续账户贡献；不能将被换出股票后来的收益作为当时可知原因。

[全部目标暴露]({link('target_exposures.csv')}) · [所有替换及H10结果]({link('replacement_outcomes.csv')}) · [目标重合]({link('target_overlap.csv')}) · [股票贡献差]({link('stock_contributions.csv')}) · [月份贡献差]({link('period_contributions.csv')}) · [成交后风险偏离]({link('actual_rebalance_risk.csv')})。
''')
 report('REPLICATION',f'''# 简单规则与风格重建验证

想验证什么：不升级模型，简单价格风格能否复制E1；已知风格能重建多少E1排序。

规则在读取新结果前固定：REV=−平均rank(mom1),rank(mom5)；MOM=平均rank(mom20),rank(mom60)；MIX=(REV+MOM)/2。COPY是截面OLS：E1分数=截距+13项风格+行业。COPY从未读取未来收益，但读取E1，不能叫独立模型。

全部采用与I相同C样本、行业名额及k，按各自分数选股；不再加入数值风格约束。因此不是让简单规则额外拥有更宽行业预算。

{table(base[['strategy','cagr','nav','fees','annual_oneway_turnover']],['cagr'])}

相对I的日均收益差年化及区间：

{table(comparisons[(comparisons.cost=='main')&comparisons.comparison.str.startswith('replicate_')][['comparison','cagr_difference','annual_daily_difference','ci_low','ci_high']],['cagr_difference','annual_daily_difference','ci_low','ci_high'])}

固定月初H10净事件对照：

{table(events[events.comparison.str.startswith('replicate_')],['mean_net_H10'])}

缺少完整可交易退出的事件保持未知，配对数48—50，不用未来退出条件重新选股。H10事件差不机械外推连续账户。

重建平均R²={recon.r2.mean():.4f}、分数秩相关={recon.rankcorr.mean():.4f}、留一股票PRESS Q²={recon.loo_Q2.mean():.4f}。留一诊断仅检验截面分数重建，并非时间上的未来收益样本外。COPY的经济结果接近I但区间宽，不能证明两者等价，更不能代表复制了原完整E1。

下一步边界：若继续独立复制，需要另冻结只能用过去数据确定的规则或模型、成熟标签隔离、预测期限和前瞻检验。本轮没有训练该模型，也没有从REV/MOM/MIX中挑胜者部署。

[逐日重建]({link('score_reconstruction.csv')}) · [全部费用对照]({link('comparisons.csv')}) · [逐事件执行结果]({link('events.csv')}) · [原始冻结配置](../../configs/{RUN}.json)。
''')
 report('EXECUTION',f'''# 风格来源实验执行记录

先冻结四组风格、两种消融、独立简单规则和教师依赖COPY，再无标签构造名单，封存后计算收益。模型与旧预测未改，所有旧输入及输出哈希复核通过。

- 50个原月初日期，平均C样本约192只，约39只持仓，完整主区间1001日。
- 15种固定账户口径，主费用与零费用各一次，共30条账户；无择优扩展。I/F主费用逐日净值精确复放上轮两端。
- 400次约束优化与全部目标保存，失败不得放宽条件。每期同样行业名额、数量及相应风格边界逐一验收。
- 连续账户股票损益与费用重建逐日收益；各比较股票贡献精确回到相对终值，不混用不同配对的财富连接系数。
- {validation['count']}项核验通过，57项测试通过；只有既有OSQP默认值弃用提示。图表和相对链接已检查。

[代码输入冻结]({link('freeze.json')}) · [无标签名单凭据]({link('selection_complete.json')}) · [账户凭据]({link('accounts_complete.json')}) · [分析完成]({link('analysis_complete.json')}) · [完整核验]({link('validation.json')})。

私有完整名单、分数和成交位于private/{RUN}。没有提交、推送、部署或新增前瞻任务；行业、复权及市值首发版本仍为Historical-proxy。本轮比较是事后历史解释，区间不是多重检验后的独立确认。
''')
 errors=[]
 for p in R.glob('*.md'):
  for u in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in u and not (p.parent/u).exists():errors.append((p.name,u))
 assert not errors,errors
 save_json(R/'manifest.json',dict(status='COMPLETE_HISTORICAL_DIAGNOSTIC',files=record(list(R.glob('*.md'))+list(R.glob('*.html'))+list(R.glob('*.png'))),sources=record([Path(__file__),EP/'src/e1_style_channels.py',EP/'tests/test_e1_style_channels.py']),tests=57,checks=validation['count'],visual_review='pending',source_inputs_unchanged=True))
 print('reports complete',flush=True)

if __name__=='__main__':main()

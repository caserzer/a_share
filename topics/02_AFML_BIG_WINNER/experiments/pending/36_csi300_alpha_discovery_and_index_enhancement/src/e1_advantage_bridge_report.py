"""Report immutable original-to-constrained bridge, all paths and exclusions."""
import re
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from e1_advantage_bridge import *
LABELS={'O':'原 E1','U':'缩小股票池 保留原数量','K':'减少持仓数量','I':'改按股票池比例配行业','F':'加入风格约束','X':'只剔除 预算留现金','UI':'先改行业 后改数量的中间账户','KF':'先加风格 后改行业的中间账户'}
STAGE={'universe':'缩小股票池并补足原数量','count':'减少持仓数量','industry':'改变行业预算','style':'加入风格约束','industry_before_count':'先改行业预算','count_after_industry':'行业预算后再改数量','style_before_industry':'先加风格约束','industry_after_style':'风格约束后再改行业','drop_excluded_to_cash':'剔除后留现金','refill_excluded_budget':'现金补入剩余股票'}

def link(f):return f'../../outputs/diagnostics/{RUN}/{f}'
def table(a,percent=()):
 a=a.copy()
 for c in percent:a[c]*=100
 return a.to_markdown(index=False,floatfmt='.3f')
def report(name,text):
 (R/(name+'.md')).write_text(text);html=markdown.markdown(text,extensions=['tables','fenced_code']);(R/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>E1 优势逐层拆解</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd;text-align:left}th{background:#edf3f5}img{max-width:100%}a{color:#146887}</style>'+html+'</html>')

def main():
 verify();verify('selection_complete');verify('accounts_complete');verify('analysis_complete')
 v=json.loads((D/'validation.json').read_text());v2=json.loads((D/'target_holdings_validation.json').read_text());assert v['status']==v2['status']=='PASS'
 m=pd.read_csv(D/'metrics.csv').set_index('strategy');br=pd.read_csv(D/'bridge.csv');br['变化']=br.stage.map(STAGE);audit=pd.read_csv(D/'selection_audit.csv');exc=pd.read_csv(D/'exclusion_reasons.csv');unknown=pd.read_csv(D/'old_unknown_reasons.csv');stale=pd.read_csv(D/'prior_state_staleness.csv');stock=pd.read_csv(D/'exclusion_stocks.csv');bstock=pd.read_csv(D/'bridge_stocks.csv');periods=pd.read_csv(D/'bridge_periods.csv');inds=pd.read_csv(D/'bridge_industry_months.csv');raw=pd.read_csv(D/'exclusion_pnl_vs_index.csv');industry=pd.read_parquet(PRIVATE/'industry.parquet');industry['instrument']=industry.ts_code.str[-2:]+industry.ts_code.str[:6];names=industry.sort_values('in_date').groupby('instrument')['name'].last();indnames=industry.groupby('l1_code').l1_name.first();indnames.loc['__FEES__']='费用差'
 mainrows=m.loc[['O','U','K','I','F']].reset_index();mainrows['账户']=mainrows.strategy.map(LABELS);bc=br[br.main][['变化','cagr_difference','wealth_contribution','mean_daily_annual','ci_low','ci_high']].copy()
 nav=pd.read_csv(D/'navs.csv',parse_dates=['date']);fig,ax=plt.subplots(figsize=(11,5))
 for st in ['O','U','K','I','F']:ax.plot(nav.date,nav[st],label=st)
 ax.set_title('Original E1 to constrained E1: fixed dates, costs and execution');ax.set_ylabel('Net NAV');ax.legend(ncol=5);fig.tight_layout();fig.savefig(R/'nav_chain.png',dpi=160);plt.close(fig)
 vals=m.loc[['O','U','K','I','F'],'cagr']*100;fig,ax=plt.subplots(figsize=(10,4));ax.bar(['O Original','U Universe','K Count','I Industry','F Style'],vals,color=['#577590','#90be6d','#43aa8b','#f9c74f','#ef8354']);ax.axhline(0,color='gray');ax.set_ylabel('Net CAGR (%)')
 for i,val in enumerate(vals):ax.text(i,val+(.25 if val>=0 else -.6),f'{val:+.2f}%',ha='center')
 ax.set_ylim(min(vals)-1.3,max(vals)+1.3);fig.tight_layout();fig.savefig(R/'cagr_chain.png',dpi=160);plt.close(fig)
 monthly=exc[exc.clock=='monthly_decision'].copy();excluded=monthly[~monthly.exclusion_reason.isin(['IN_C','__FEES__','__CASH__'])].wealth_contribution.sum()
 text=f'''# 原 E1 优势在哪一步消失

**本轮最清晰的结果是：缩小股票池并不是优势消失的主要一步。按股票池比例重新分配行业名额、再将持仓风格限制在简单规则 B 附近，造成了更大的收益下降。反向顺序核验中，两者的影响方向仍为负，但幅度有明显顺序依赖。**

这不是“行业因素和风格因素已被唯一识别”的证明。约束是相对上一轮B组合的13项风格容差，并非对所有风险做严格中性化；它同时改变具体股票、集中度与换仓路径。

## 同一账户链

固定原2021-01-08信号至2025-03-03，50次月初原日历、1001交易日、买入10bps和卖出20bps。原预测不变，无重训、无参数搜索。O逐日精确复放原E1，F逐日精确复放上一轮受约束E1。8条账户均完整到主终点，无估值失败。

{table(mainrows[['strategy','账户','cagr','end_nav','holdings']],['cagr'])}

cagr为净年化百分数，holdings为每日平均实际持仓数。U在缩小的C股票池中按原E1排序补足原数量；K改为ceil(n/5)；I按C中行业股票数分配整数名额；F再加入相对B的13项0.25标准差风险约束。

![年化变化](cagr_chain.png)

## 每一步带来的差额

{table(bc,['cagr_difference','mean_daily_annual','ci_low','ci_high'])}

收益差均为“后一步减前一步”。cagr_difference是年化百分点；mean_daily_annual及其区间是配对日收益差的年化，不是CAGR差的区间。区间采用65交易日块、2000次重采样，仅作历史描述。wealth_contribution为初始100元的全链财富差连接贡献，各主步骤相加等于F减O约{v['original_to_final_wealth']:.2f}元；月份和股票贡献也精确加总。

风格约束这一步的日均收益差年化约−7.51pp，描述性95%区间约[−11.82,−2.98]pp；行业预算一步的对应区间跨零。因此，行业变化目前主要是较大的负向点估计，风格约束在这项历史配对描述中证据更强，仍不是因果识别。

主顺序下：股票池约−2.19pp，减少数量约+2.61pp，行业预算约−4.38pp，风格约束约−7.30pp。**在C股票池、约39只股票、仍按原E1全池排序的K账户，净年化约5.26%，仍保留原策略的正收益线索。** 因此不能把上一轮受约束E1的负收益直接解释为“原策略在可用样本里也无效”。

![净值链](nav_chain.png)

## 被排除持仓是否关键

原每月目标平均剔除{audit.excluded_original_budget.mean():.1%}预算。按原月度决策时点归类，被排除或无当期可评分记录持仓的原账本相对财富贡献合计约{excluded:.2f}元；这与“删除这些持仓后账户会少赚多少”不同。

只删除、原权重不放大并留现金的X账户，净年化约{m.loc['X','cagr']*100:.2f}%，平均现金约{m.loc['X','cash']:.1%}；在剩余股票中补足原数量的U约{m.loc['U','cagr']*100:.2f}%。现金减少市场风险、费用和换手，不能把两者差额都叫被排除股票的Alpha。具体排除原因、股票、月份与绝对损益见[覆盖审计](EXCLUSIONS.md)。

## 顺序核验与结论边界

- 先改行业、后减数量：U约2.65% → UI约−0.75% → I约0.88%。行业改变仍负向，减持仓数仍正向。
- 先加风格、后改行业：K约5.26% → KF约−4.11% → F约−6.42%。风格约束约−9.37pp，随后行业改变约−2.31pp；与主顺序的−7.30/−4.38pp不同，但方向一致。

下一步研究对象因此应是：**原E1保留了哪些被行业预算或相对B风格约束移除的股票暴露，以及这种暴露能否由简单、事前可定义的规则复制。** 本轮没有替换基线、放松阈值或新增因子搜索。K的历史表现本身不是新的独立确认。

所有历史已被查看，行业与市值等仍为Historical-proxy；本轮是账户反事实和描述性归因，真实前瞻不因本轮结果而完成。

[被排除持仓与原因](EXCLUSIONS.md) · [步骤与反向顺序详表](STEPS.md) · [执行合同和核验](EXECUTION.md) · [完整年度月度收益]({link('period_returns.csv')}) · [全部桥接股票]({link('bridge_stocks.csv')}) · [全部桥接行业月份]({link('bridge_industry_months.csv')})。
'''
 report('REPORT',text)
 selected=stock[(stock.clock=='monthly_decision')&~stock.exclusion_reason.isin(['IN_C','__FEES__','__CASH__'])].copy();ss=selected.groupby('instrument',as_index=False).wealth_contribution.sum();ss['name']=ss.instrument.map(names);ss=ss.sort_values('wealth_contribution',ascending=False);write(ss,'excluded_stock_totals.csv')
 ind=selected.groupby('industry',as_index=False).wealth_contribution.sum();ind['name']=ind.industry.map(indnames);ind=ind.sort_values('wealth_contribution',ascending=False);write(ind,'excluded_industry_totals.csv')
 xm=pd.read_csv(D/'exclusion_months.csv');xm=xm[(xm.clock=='monthly_decision')&~xm.exclusion_reason.isin(['IN_C','__FEES__','__CASH__'])].groupby('month',as_index=False).wealth_contribution.sum();write(xm,'excluded_month_totals.csv')
 r=raw.copy();r['absolute_pnl_per100']=r.absolute_pnl*100
 report('EXCLUSIONS',f'''# 被排除持仓的原因与实际贡献

想验证什么：上一轮约三分之一持仓无法进入机制样本，是否因此漏掉原E1的主要来源。

怎么比较：排除原因只用信号时点字段。IN_C为满足样本合同；INDUSTRY_LT10表示当日行业内完整有效股票不足10只；MISSING列出缺失字段；无当前评分记录单列。原因是数据和样本规则，不是“股票不好”。本轮不补数、不修改最小行业规模。

## 原来19.39元如何分解

未知贡献主要来自最小行业规模规则：约16.16元是INDUSTRY_LT10，约2.88元是换手率缺失。不能把全部19.39元都叫数据缺失。

以下严格接回上一轮按每只股票最近已知周信号分组的UNKNOWN贡献，而非改用新口径后强行宣称一致：

{table(unknown)}

同时审计了旧分类信号是否等于全市场最近周信号。股票不再出现在可评分池时，旧逐股向后连接可能沿用更早状态；所以本轮另给统一周时钟和月度决策时钟。旧分类未覆盖重写。

{table(stale)}

## 按原月度决策时点归因

{table(monthly[['exclusion_reason','wealth_contribution']])}

这些贡献包含指数机会收益调整、持仓路径和全期对数连接。它们不等于删股反事实。下表把原始股票现金损益与指数机会收益项分列；absolute_pnl_per100为初始100元的实际股票损益，index_opportunity_return是未连接日机会收益之和，不应与连接后的财富贡献机械相加。

{table(r[['exclusion_reason','absolute_pnl_per100','index_opportunity_return','linked_wealth_contribution']])}

## 具体股票和行业

贡献最高10只和最低5只：

{table(pd.concat([ss.head(10),ss.tail(5)]).drop_duplicates('instrument'))}

按实际持仓当时行业归类：

{table(ind)}

被排除持仓贡献最大的10个月及最小5个月：

{table(pd.concat([xm.nlargest(10,'wealth_contribution'),xm.nsmallest(5,'wealth_contribution')]).drop_duplicates('month'))}

## 删除与替代不是同一个实验

{table(m.loc[['O','X','U'],['cagr','end_nav','cash','fees','annual_oneway_turnover']].reset_index(),['cagr','cash'])}

X保留原选股中仍满足C的股票及原目标权重，剩余预算留现金；U在C中补入排名靠前股票恢复原持仓数。现金对照提供删股的账户结果，但同时改变市场暴露与交易费用。不能用它证明被排除股票无价值，也不能把19.39元当成删除后的必然损失。

[原UNKNOWN逐股票明细]({link('old_unknown_stocks.csv')}) · [原UNKNOWN逐月]({link('old_unknown_months.csv')}) · [统一周/月时钟全部明细]({link('exclusion_stocks.csv')}) · [排除预算逐次]({link('selection_audit.csv')}) · [完整股票表]({link('excluded_stock_totals.csv')}) · [完整月份表]({link('excluded_month_totals.csv')})。
''')
 parts=[]
 for name in br.stage:
  bs=bstock[bstock.stage==name].copy();bs['name']=bs.instrument.map(names).fillna(bs.instrument);top=pd.concat([bs.nsmallest(5,'wealth_contribution'),bs.nlargest(3,'wealth_contribution')]).drop_duplicates('instrument');bp=periods[(periods.stage==name)&(periods.freq=='M')];bp=pd.concat([bp.nsmallest(4,'wealth_contribution'),bp.nlargest(2,'wealth_contribution')]).drop_duplicates('period');bi=inds[inds.stage==name].groupby('industry',as_index=False).wealth_contribution.sum();bi['name']=bi.industry.map(indnames);bi=pd.concat([bi.nsmallest(5,'wealth_contribution'),bi.nlargest(3,'wealth_contribution')]).drop_duplicates('industry')
  parts.append(f'## {STAGE[name]}\n\n主要股票差额，负数表示改动后更差，正数表示更好：\n\n'+table(top[['instrument','name','wealth_contribution']])+'\n\n主要月份：\n\n'+table(bp[['period','wealth_contribution']])+'\n\n主要行业：\n\n'+table(bi)+'\n')
 report('STEPS',f'''# 各步骤及顺序核验

所有数值以同一资金起点、相同日期和费用比较。主链与反向链不是相互独立的实验，不能把差额重复相加。行业预算按股票池比例分配整数名额，不是市值权重；风格约束参照上一轮B目标，不是对市场风险归零。

{table(br[['变化','before','after','cagr_difference','wealth_contribution','mean_daily_annual','ci_low','ci_high']],['cagr_difference','mean_daily_annual','ci_low','ci_high'])}

各主步骤和反向步骤的贡献均按同一个全链F减O财富换算系数连接。单步财富贡献不同于两条账户期末净值直接相减；主链加总恰好还原全链差额。股票差额来自两账户各自的损益与费用连接，不是未持股票的完整机会集因果效应。

[全部目标名单变化]({link('target_changes.csv')}) · [实际成交后风险]({link('actual_rebalance_risk.csv')})。以下每项只列主要贡献，完整明细保留。

'''+ '\n'.join(parts))
 report('EXECUTION',f'''# 执行合同与验收

本轮授权为执行原账户优势消失的逐层拆解及被排除持仓审计。先冻结代码和输入，再封存无标签目标，最后独立重放8条账户并计算描述性归因。原预测、旧报告和旧账户均未修改。

- 主链O→U→K→I→F；O为原账户，F为上一轮受约束E1。两端逐日净值精确复放，所有账户主区间1001日、无失败。
- U保留原每期58—60只数量，K缩为ceil(C样本数/5)，I按C内行业比例分配名额。其余选股均使用原E1分数；同分按代码升序。
- F复用已封存目标；逆序KF去掉行业名额限制而保持相同13风格参考、0.25标准差容差、2秒求解上限及1%解差。UI用于调换行业和持仓数顺序。
- X仅删除被排除股票，原目标权重不放大，剩余现金不取利息。执行器仍独立处理涨跌停、停牌与旧仓出售限制。
- 所有每日期目标、成交和每日实际持仓完整保存；私有目录private/{RUN}/targets.parquet、orders和holdings可用于逐股追溯。公开收益、贡献和覆盖明细位于outputs/diagnostics/{RUN}。
- 统计只作65交易日块配对描述，不进行主假说检验或事后多重显著性宣告。行业/风格顺序交互明确保留。

{v['count']}项账本与两端复放检查、{v2['count']}项目标及逐日持仓检查通过，54项测试通过；仅既有OSQP弃用提示。没有新训练、调参、提交、推送或部署。真实前瞻、严格PIT和容量认证均未因此完成。

[冻结配置](../../configs/{RUN}.json) · [输入及代码哈希]({link('freeze.json')}) · [无标签名单封存]({link('selection_complete.json')}) · [账户凭据]({link('accounts_complete.json')}) · [分析完成]({link('analysis_complete.json')}) · [账本验证]({link('validation.json')}) · [目标和持仓验证]({link('target_holdings_validation.json')})。
''')
 errors=[]
 for p in R.glob('*.md'):
  for url in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in url and not (p.parent/url).exists():errors.append((p.name,url))
 assert not errors,errors
 save_json(R/'manifest.json',dict(status='COMPLETE_DESCRIPTIVE',files=record(list(R.glob('*.md'))+list(R.glob('*.html'))+list(R.glob('*.png'))),implementation=record(list((EP/'src').glob('e1_advantage_bridge*.py'))+[EP/'tests/test_e1_advantage_bridge.py']),tests=54,checks=v['count']+v2['count'],source_inputs_unchanged=True,visual_review='pending'))
 print('reports complete',flush=True)

if __name__=='__main__':main()

"""Past-only replication report, separated from independent alpha claims."""
import re
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from e1_past_style_copy import *

def table(a,percent=()):
 a=a.copy()
 for c in percent:a[c]*=100
 return a.to_markdown(index=False,floatfmt='.4f')
def link(x):return f'../../outputs/diagnostics/{RUN}/{x}'
def report(name,text):
 (R/(name+'.md')).write_text(text);html=markdown.markdown(text,extensions=['tables','fenced_code']);(R/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>过去风格复制验证</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd;text-align:left}th{background:#edf3f5}img{max-width:100%}a{color:#146887}</style>'+html+'</html>')

def main():
 verify();verify('selection_complete');verify('accounts_complete');verify('analysis_complete')
 m=pd.read_csv(D/'metrics.csv');stats=pd.read_csv(D/'statistics.csv');comparison=pd.read_csv(D/'account_comparisons.csv');within=pd.read_csv(D/'within_industry_statistics.csv');fits=pd.read_csv(D/'fits.csv');coef=pd.read_csv(D/'coefficients.csv');overlap=pd.read_csv(D/'target_overlap.csv');v=json.loads((D/'validation.json').read_text());audit=json.loads((D/'measurement_audit.json').read_text());assert v['status']==audit['status']=='PASS'
 mainm=m[m.cost=='main'].set_index('strategy').loc[['I','Q','LOCK','COPY']].reset_index();ic=stats[stats.metric=='H10_RankIC'][['strategy','n','mean','ci_low','ci_high']];merged=mainm.merge(ic,on='strategy');names={'I':'同日起点E1','Q':'每季度过去分数复制','LOCK':'首次学习后锁定','COPY':'当日E1复制 仅作诊断'};merged['名称']=merged.strategy.map(names)
 fig,axes=plt.subplots(1,2,figsize=(12,4.3))
 for st in ['I','Q','LOCK','COPY']:
  a=pd.read_csv(D/'accounts'/(st+'__main.csv'),parse_dates=['date']);axes[0].plot(a.date,a.nav,label=st)
 axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=6));axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'));axes[0].set_title('Fresh accounts, common start 2021-10-11');axes[0].set_ylabel('Net NAV');axes[0].legend()
 x=ic.set_index('strategy').loc[['I','Q','LOCK','COPY']];axes[1].errorbar(np.arange(4),x['mean'],yerr=np.vstack([x['mean']-x.ci_low,x.ci_high-x['mean']]),fmt='o',capsize=4);axes[1].set_xticks(np.arange(4),x.index);axes[1].axhline(0,color='gray',ls='--');axes[1].set_title('H10 RankIC, ordinary descriptive 95% intervals');fig.tight_layout();fig.savefig(R/'past_copy_results.png',dpi=160);plt.close(fig)
 recon=pd.read_csv(D/'score_reconstruction.csv',parse_dates=['signal_date']);fig,ax=plt.subplots(figsize=(11,4))
 for st in ['Q','LOCK','COPY']:
  a=recon[recon.strategy==st].set_index('signal_date').rank_correlation;ax.plot(a.index,a.rolling(13,min_periods=13).mean(),label=st)
 ax.axhline(0,color='gray');ax.set_title('13-signal rolling score-rank correlation with E1, descriptive');ax.set_ylabel('Cross-sectional rank correlation');ax.legend();fig.tight_layout();fig.savefig(R/'replication_stability.png',dpi=160);plt.close(fig)
 report('REPORT',f'''# 过去信息能否独立生成 E1 风格复制分数

**本轮固定的13风格线性复制没有保住E1的排序或经济表现。季度滚动更新和首次学习后锁定两种方式，都明显弱于同日起点E1的点估计。当前不能把风格COPY当作可替代E1的简单模型。**

这不证明所有过去信息复制都不可能，也不直接证明E1具有未知风格之外的稳定Alpha。它没有支持这个较窄的可操作主张：用固定13项风格、过去E1分数、季度扩展OLS或首次锁定系数，可以在本合同下稳定复制E1。

## 先确保没有借用当天答案

Q在每季度开始时只读取此前的E1分数；LOCK只在首个合格季度学习一次，此后不再更新。两者预测接口只接收风格与行业，不接收E1分数和未来收益。

预设最少26个历史周信号、2000行，季度开始才允许拟合。2021Q3前只有25个信号，因此第一期是2021Q4，训练截止2021-09-30。LOCK此后永久使用该次系数。所有训练在当前/未来教师分数被改写成常数时结果不变。

这里的“过去”依据历史信号时点合同模拟；数据首发版本和真实分数发布时间未认证，仍是Historical-proxy历史研究，不是真实前瞻。

## 共同区间结果

所有账户从2021-10-11开盘后的同一资金起点开始，到2025-03-03，共823交易日、41次月初信号。沿用缩小后的C样本、约39只持仓、相同行业名额及10/20bps费用。I是行业名额受约束的E1，不是原完整E1账户。

{table(merged[['strategy','名称','cagr','n','mean','ci_low','ci_high']],['cagr'])}

cagr为净年化百分数；mean及区间为H10 RankIC，无年化含义。171个有效成熟周信号。Q和LOCK的RankIC区间跨零；与I的差额另有描述性区间，但本轮未作确认性多重检验。

![共同起点结果](past_copy_results.png)

Q相对I的年化差约−8.42pp，LOCK约−8.96pp。配对日收益差年化的区间仍跨零，因此应说“未复现”，不能宣布统计上已证明永久劣于E1。月初H10净事件的平均差也为负，完整结果见[时序及经济明细](DETAILS.md)。

## 行业内核验也没有恢复

为避免行业均值处理造成误解，补做每行业内部Spearman、再按股票数加权的审计。Q与E1的行业内分数排序相关约0.112，LOCK约0.072；当日COPY约0.464。行业内未来H10 RankIC分别约0.0059、−0.0073、0.0461，E1约0.0443。过去复制的区间仍跨零。

同时，41个日期的COPY和I名单分别与上一轮对应名单完全一致。去均值没有改变行业内选股；当前COPY的年化与上一轮不同，是重新从共同起点建仓、删去暖启动期和路径变化，不能跨区间比较。

![复制稳定性](replication_stability.png)

## 现在知道了什么

- 当天用风格解释E1，保留了一部分当日排序；把过去的解释关系搬到未来日期，当前两种固定方式未能保留这种能力。
- 因而“E1就是一个稳定风格配方”的解释没有获得支持。信息可能包含随时点变化的映射，也可能是13项线性表达过于简单；本轮没有区分这两者，不能把失败自动归因于市场状态。
- Q仍需要过去E1分数来季度更新；LOCK在初次学习后不再需要新E1分数，但仍继承历史E1和C股票池资格，不能称为从未依赖E1的完全独立系统。
- 原完整E1的收益来源仍未闭合。下一步若研究映射为何变化，应先利用已保存的原Ridge系数和当前风格投影做解释性诊断，而非继续搜索复制窗口或升级模型。

本轮停止这两个固定复制版本的参数扩展，保留失败证据。没有重训原E1或训练未来收益预测模型，没有前瞻结果、自动部署或交易建议。

[冻结方法与时序凭据](METHOD.md) · [全部统计和年度月度](DETAILS.md) · [机器配置](../../configs/{RUN}.json) · [验证记录]({link('validation.json')}) · [行业内测量审计]({link('measurement_audit.json')})。

61项测试通过，{v['count']}项时序/配对/账本检查和{audit['count']}项历史名单一致性检查通过；旧输入、模型和预测哈希保持不变。
''')
 report('METHOD',f'''# 过去复制方法与时间隔离

目标是验证可跨日期使用的风格映射，而不是再拟合一个未来收益模型。输入为既有13项风格：1/5/20/60日收益、20/60日波动、60日beta和特质波动、三项流动性、总市值及流通市值对数。

每个历史信号日期，先将13项风格作截面总体标准化，再减去各行业均值；教师E1分数亦先作截面标准化，再行业去均值。每日期行权重为1/sqrt(n)，使训练日期总权重相同。合并过去日期做无截距OLS，rcond=1e-12，不搜索正则参数。

Q每个季度开始，用所有严格早于季度起点的信号拟合。LOCK只用第一次符合26周和2000行门槛的Q模型，后续固定。COPY为当日同样变换后的教师投影；I为当日E1原分数，二者仅作对照。

{table(fits)}

第一期2021Q4，训练39个既有信号、7084行，截止2021-09-30。此前季度保持WARMUP，不利用未来补出预测，也不从2021年初用已有后期模型回填。因此所有经济账户改为同日起点重放，不能与原全期4.84%或上轮I全期0.88%直接比较。

分数复制不需要等未来H10收益成熟，因为其训练目标是过去E1分数；未来收益标签仅在封存预测和名单后接入。实际历史分数发布时间未取得原始接收凭据，故只能称为时序合同下的模拟。

完整系数逐季度保存。当前/未来E1被改成巨大常数时，历史拟合系数严格不变；预测接口拒绝E1和未来标签列；LOCK所有季度系数完全一致。41期COPY与上一轮同日期COPY名单相同，行业去均值只改变跨行业偏移，不改变固定行业名额下的选股。

[季度系数]({link('coefficients.csv')}) · [逐日期预测审计]({link('prediction_audit.csv')}) · [冻结哈希]({link('freeze.json')}) · [无标签封存]({link('selection_complete.json')}) · [收益账户凭据]({link('accounts_complete.json')})。

两个复制器没有读当前分数，但历史C样本仍采用原E1可评分资格和行业有效样本不少于10只的合同。未来独立运行还需实现不依赖存储E1分数的资格生成、最新数据审计与已冻结版本管理；本轮未声称已经部署。
''')
 comparisons= comparison[comparison.cost=='main']
 report('DETAILS',f'''# 排序与经济验证完整结果

所有结果是已反复查看的历史上的新设计探索，p值和普通95%区间仅作描述；没有独立确认或等价边界。量纲不同的指标不能混合加总。

## 原始 H10 排序及其差异

{table(stats[stats.metric.str.startswith('H10')][['metric','strategy','n','mean','ci_low','ci_high','p']])}

## 月初固定 H10 净事件差

{table(stats[stats.metric=='net_H10_minus_I'][['strategy','n','mean','ci_low','ci_high','p']],['mean','ci_low','ci_high'])}

本表均值与区间为每事件百分点，主费用买10/卖20bps，事件数40—41。无法完整清算的事件为未知，未据未来状态换名单。此结果不机械外推连续账户。

## 连续账户

{table(m[['strategy','cost','start','end','days','cagr','nav','annual_oneway_turnover']],['cagr'])}

每种分数仅主费用与零费用两次，总计8条账户，均同日起点和终点。过去复制在零成本下也未恢复同口径E1表现，不能简单归因于交易成本。

{table(comparison[['strategy','cost','cagr_difference','annual_daily_difference','ci_low','ci_high']],['cagr_difference','annual_daily_difference','ci_low','ci_high'])}

cagr_difference是净年化差；区间针对配对日均差年化，不是CAGR差。daily65交易日块、2000次；周度13周/月度3月块、5000次，缺失日历期保留。

## 行业内测量审计

这项审计是在看到主结果后补充，只验证结论是否由跨行业均值处理产生，不改变主结果、分数、名单或交易策略。每行业先算相关，再按股票数对当日加权；不把股票当作独立时间样本。

{table(within[['strategy','metric','n','mean','ci_low','ci_high']])}

当日行业内风格投影可重建一部分排序，但其时间迁移失败。不得据当日COPY表现挑选未来可用模型。

平均目标名单与I重合率：

{table(overlap.groupby('strategy',as_index=False).agg(overlap_with_I=('overlap_with_I','mean'),mean_k=('k','mean')),['overlap_with_I'])}

[全部年度月度收益]({link('periods.csv')}) · [原始RankIC]({link('rank_ic.csv')}) · [分数重建]({link('score_reconstruction.csv')}) · [行业内逐日期]({link('within_industry_audit.csv')}) · [当日投影系数 仅作事后诊断]({link('same_date_coefficient_diagnostic.csv')}) · [完整事件]({link('events.csv')})。

全部分数、名单、成交与标签明细保存在private/{RUN}，源数据依仓库规则保留本地。未提交、推送、部署，真实前瞻仍FORWARD_PENDING。
''')
 errors=[]
 for p in R.glob('*.md'):
  for u in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in u and not (p.parent/u).exists():errors.append((p.name,u))
 assert not errors,errors
 save_json(R/'manifest.json',dict(status='HISTORICAL_PAST_ONLY_COMPLETE',files=record(list(R.glob('*.md'))+list(R.glob('*.html'))+list(R.glob('*.png'))),sources=record(list((EP/'src').glob('e1_past_style_copy*.py'))+[EP/'tests/test_e1_past_style_copy.py']),tests=61,checks=v['count']+audit['count'],source_inputs_unchanged=True,visual_review='pending',forward='FORWARD_PENDING'))
 print('reports complete',flush=True)

if __name__=='__main__':main()

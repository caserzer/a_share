"""Explain score mapping drift without confusing score variance with profits."""
import re
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from e1_mapping_drift import *

def table(a,percent=()):
 a=a.copy()
 for c in percent:a[c]*=100
 return a.to_markdown(index=False,floatfmt='.4f')
def link(f):return f'../../outputs/diagnostics/{RUN}/{f}'
def report(name,text):
 (R/(name+'.md')).write_text(text);html=markdown.markdown(text,extensions=['tables','fenced_code']);(R/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>E1 风格映射变化</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd;text-align:left}th{background:#edf3f5}img{max-width:100%}a{color:#146887}</style>'+html+'</html>')

def main():
 verify();verify('structure_complete');verify('analysis_complete');summary=pd.read_csv(D/'decomposition_summary.csv');groups=pd.read_csv(D/'residual_group_summary.csv');features=pd.read_csv(D/'feature_residual_summary.csv');replay=pd.read_csv(D/'replay.csv');ranking=pd.read_csv(D/'ranking_statistics.csv');v=json.loads((D/'validation.json').read_text());fa=json.loads((D/'feature_audit.json').read_text());assert v['status']==fa['status']=='PASS'
 selected=summary[summary['sample']=='all'];names={'market_common':'共同市场项','range_position':'区间位置','returns_trend':'收益与趋势','volatility_drawdown':'波动与回撤','volume_liquidity':'量价与流动性'};groups['特征组']=groups.group.map(names)
 fig,ax=plt.subplots(figsize=(10,4.5));labels=selected.clock+' / '+selected.scope;x=np.arange(len(selected));ax.bar(x,selected.model_share*100,label='Frozen model bundle change');ax.bar(x,selected.data_share*100,bottom=selected.model_share*100,label='Data / distribution / normalization');ax.set_xticks(x,labels);ax.set_ylabel('Signed allocation (%)');ax.set_title('Mapping-change score energy allocation, NOT profit attribution');ax.legend(loc='upper right');fig.tight_layout();fig.savefig(R/'mapping_split.png',dpi=160);plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,4));ax.bar(groups.group,groups.signed_share*100);ax.set_ylabel('Signed residual-score energy allocation (%)');ax.set_title('What 13 styles fail to reconstruct, NOT alpha contribution');ax.tick_params(axis='x',rotation=15);fig.tight_layout();fig.savefig(R/'residual_groups.png',dpi=160);plt.close(fig)
 chosen=ranking[(ranking.metric=='rank_ic')&ranking.score.isin(['E1','FIXED78','EXPLAINED13','RESIDUAL13'])].set_index('score').loc[['E1','FIXED78','EXPLAINED13','RESIDUAL13']]
 fig,ax=plt.subplots(figsize=(9,4));ax.errorbar(np.arange(4),chosen['mean'],yerr=np.vstack([chosen['mean']-chosen.ci_low,chosen.ci_high-chosen['mean']]),fmt='o',capsize=5);ax.set_xticks(np.arange(4),chosen.index);ax.axhline(0,color='gray',ls='--');ax.set_ylabel('H10 RankIC');ax.set_title('Auxiliary historical diagnostics, ordinary 95% intervals');fig.tight_layout();fig.savefig(R/'ranking.png',dpi=160);plt.close(fig)
 report('REPORT',f'''# E1 风格映射为何不能稳定复制

**本轮更支持“13项风格压缩丢失了工程特征表达”，而不是“原 Ridge 每季度更新导致映射剧烈漂移”。** 冻结2021Q4完整78特征模型后，与后续E1的平均截面排序相关仍约{replay.raw_rank_fixed78.mean():.3f}；过去13风格复制的相关则很低。

这里定位的是分数表达与映射变化，不是已经找到了可交易Alpha的经济原因。区间位置特征是重点候选，但其单独预测价值尚未确认。

## 原模型不更新 仍保留多少信息

固定2021Q4的原Ridge，包括系数、训练均值/标准差和缺失值中位数；应用到之后每个日期的78项原工程特征，不重训。共同研究信号为2021-10-08至2025-02-28，H10成熟标签终点不超过2025-03-03。

{table(chosen.reset_index()[['score','n','mean','ci_low','ci_high']])}

E1是原滚动季度模型；FIXED78是固定2021Q4原模型；EXPLAINED13是当日风格投影；RESIDUAL13是对应残差。表为171个成熟信号的原始未来收益RankIC，不是成本后收益或严格条件RankIC。

固定完整模型约0.0306，原E1约0.0471；保留了正向排序线索，但不能据此说季度更新没有价值。固定完整模型与过去13风格复制的失败也不能混为一谈：它们保留的特征不同。本轮没有回测固定完整模型的经济账户。

![排序诊断](ranking.png)

## 映射变化主要落在哪一项

每次把旧/新模型与旧/新数据交叉，得到四个13风格投影，再做对称两因素分解。模型项包括完整预处理更新；数据项包括股票特征、风格协方差、截面标准化、行业与股票池变化。

{table(selected[['clock','scope','pairs','model_share','data_share']],['model_share','data_share'])}

adjacent为相邻周信号；anchor为固定2021-10-08首日。native允许两期各自股票池，common只用两期共有股票。数字是映射变化在新日期分数空间的带符号分配，不是收益比例，也不是唯一经济因果份额。

相邻周模型通常不更新，所以模型份额小并不意外。仅看实际季度模型切换的14个相邻配对，模型份额仍约5.6%—5.7%，数据项约94%；固定首日的较长跨度，模型约7%—8.5%、数据约91.5%—93%。共同股票核验未改变主要方向。

![模型与数据分解](mapping_split.png)

这说明：同一个相对稳定的完整模型，在不同数据截面上，投影到简化13风格时所需权重可以变化很大。数据项仍混合标准化、共线性与分布变化，不能直接命名为“市场状态Alpha”。

## 13项风格主要漏掉了什么

把原78项特征的实际分数贡献，逐项剥离同一13风格投影后，精确加总回剩余分数：

{table(groups[['特征组','signed_share']],['signed_share'])}

区间位置组约65%，其中pos60约56.8%、pos20约8.95%、pos5约−0.75%。负份额表示对总残差的抵消；这些都是**残差分数的解释份额，不是超额收益贡献**，不能说pos60创造了56.8%的利润。

pos60的定义是“当日收盘距过去60日最低价的距离，除以过去60日最高价与最低价之差”。它不仅看60日首尾涨幅，还包含期间路径和高低区间。相同60日收益的股票，区间位置可以不同，因此mom60不能直接替代pos60。

![残差分数组](residual_groups.png)

区间位置残差组单独的H10 RankIC约0.0046，95%区间约[−0.0119,+0.0196]，未获得明确支持。完整残差约0.0137、普通区间为正，也只是新样本/新区间的辅助历史结果，不能覆盖此前主实验的INCONCLUSIVE裁决。当前仍没有成本后独立Alpha认证。

## 下一步应怎样收敛

研究重点应从“寻找更好的13风格复制权重”转向“完整工程特征中哪些表达不可被简单收益风格替代”。优先检查区间位置与波动/回撤之间的组合关系，但不要把本轮分数分配直接变成只买高pos60的新策略。

若继续，应保留当前模型和交易合同，先验证这些特征对未来收益的增量及可执行经济价值，再考虑简化。当前未调参、未重训或建立新收益模型。

[分解方法与时序](METHOD.md) · [工程特征和辅助统计](FEATURES.md) · [原冻结配置](../../configs/{RUN}.json) · [验证]({link('validation.json')}) · [逐特征分配审计]({link('feature_audit.json')})。

65项测试、{v['count']+fa['count']}项核验通过；全部173个信号精确复放原分数，旧模型、预测与数据未改。真实前瞻仍未完成，未提交、推送或部署。
''')
 report('METHOD',f'''# 映射变化的模型与数据分解

本轮只解释此前复制失败，不搜索收益参数。先冻结两种时间跨度、两个样本口径和分解公式，再计算结构，封存结构后才接入H10标签。

每个数据截面将13风格作总体标准化并行业去均值，得到X。原Ridge分数作总体标准化并行业去均值，得到y。令gamma=pinv(X)y，rcond=1e-12。两个日期可能有不同股票数量，但gamma始终为相同13维风格坐标。

用M0/M1表示旧/新原Ridge整套模型，D0/D1表示旧/新数据。计算gamma00、gamma10、gamma01、gamma11：
- 模型分配=0.5×[(gamma10−gamma00)+(gamma11−gamma01)]。
- 数据分配=0.5×[(gamma01−gamma00)+(gamma11−gamma10)]。
- 二者相加精确等于gamma11−gamma00。
- 使用新数据的X1将三者映射到股票分数空间；不是用易受共线性影响的系数欧氏距离直接作经济归因。

对每个日期用平均股票平方变化定义能量。某项带符号分配为该项分数变化与总变化的内积，再除以总变化平方和；汇总先加各日期分子分母再求比。分配可能负值或超过100%，并非互相独立的正方差，也不是利润份额。

{table(summary,['model_share','data_share'])}

相邻周的同季度模型完全一致，模型分配必须为零；此外单列模型确实更换的边界配对。固定首日2021-10-08的比较跨越多个季度，减少“多数周不更新”的机械影响。common口径只用两期共有股票，但仍保留各期特征、行业和标准化；不是固定整个市场环境。

**新模型放到旧数据上属于事后交叉诊断，可能使用旧日期之后的信息，不能生成可交易历史预测。** 唯一辅助未来预测对照FIXED78使用2021Q4已训练模型向后应用，未读取未来模型。

模型项包含系数、训练均值/标准差、中位数填补变化；数据项也包含标准化和行业分类变化。本轮不进一步把它们分别命名为因果机制。

[四格投影系数]({link('mapping_cells.csv')}) · [逐配对分解]({link('mapping_decomposition.csv')}) · [原分数复放]({link('replay.csv')}) · [输入代码冻结]({link('freeze.json')}) · [无未来收益的结构封存]({link('structure_complete.json')}) · [分析完成]({link('analysis_complete.json')})。
''')
 fs=features[features.group=='range_position'];condition=pd.read_csv(D/'projection_conditioning.csv')
 report('FEATURES',f'''# 工程特征残差分数与预测诊断

每项特征的分数贡献使用原季度TrainTransform与Ridge系数，不能把不同季度的标准化系数直接当作相同原始单位的效应。各项先除以当日完整分数标准差、行业去均值，再用同一13风格投影取残差。

逐项残差加总必须精确回到完整残差；组分配定义为组残差与总残差的内积，占总残差平方和的比例。原冻结特征组保持不变。

{table(groups[['group','signed_allocation','own_energy','signed_share']],['signed_share'])}

own_energy是该组自身平方和，组间有相关性，因此各组own_energy不应加总当成整体平方和。signed_share才是本合同下可加总的带符号分配。

## 区间位置组三项

{table(fs[['feature','signed_share','min_coefficient','max_coefficient']],['signed_share'])}

pos5、pos20、pos60分别采用5/20/60日最低low和最高high计算区间位置。当前模型系数中pos60、pos20为正，pos5为负，但这只解释分数方向，未证明单项净收益。特征级细分在看到组结果后补充，明确属于事后记账，不进行78项未来收益筛选。

示意而非真实回测：两只股票同样从90涨到100，首尾涨幅相同；若一只期间最低80、最高120，区间位置为0.5；另一只最低90、最高100，区间位置为1。简单累计收益无法区分这样的路径。

## 未来收益辅助检查

{table(ranking[['score','metric','n','mean','ci_low','ci_high']])}

rank_ic为分数与原始H10未来收益的Spearman；industry_ic为先逐行业计算相关再按有效股票数加权。不是严格条件因果统计。时间块13周、5000次，普通95%区间未做本轮辅助族的多重校正；不得从其中最好的组升级主结论。

市场共同项在行业去均值后近乎零，不能形成股票排序，其相关记未知，不填零。其他组单独正点估计也不能替代成本后组合验证。

## 为什么与早期 A1 不同

本轮采用缩小C样本、2021-10-08后共同区间、标准化并行业去均值的教师分数和对应残差；早期A1使用不同样本、区间及投影合同。因此本轮残差IC的正区间不能重写早期主裁决，也不能称为又一次独立确认。

13风格矩阵当前信号均满秩；条件数中位约{condition.condition_number.median():.2f}、最大约{condition.condition_number.max():.2f}。仍有共线性，尤其市值字段；本轮用映射后的分数变化作比较，不能宣称已消除所有数值敏感性。

[逐特征完整分配]({link('feature_residual_summary.csv')}) · [每期特征贡献]({link('feature_residual_allocation.csv')}) · [逐期RankIC]({link('rank_ic.csv')}) · [投影条件数]({link('projection_conditioning.csv')})。

当前结构平均可解释约{replay.r2.mean():.1%}的行业去均值分数平方量；其分母与此前含行业均值的总分数R²不同，不能直接对比成“解释率下降”。原模型没有重训，未生成新组合策略。
''')
 errors=[]
 for p in R.glob('*.md'):
  for u in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in u and not (p.parent/u).exists():errors.append((p.name,u))
 assert not errors,errors
 save_json(R/'manifest.json',dict(status='COMPLETE_DESCRIPTIVE',files=record(list(R.glob('*.md'))+list(R.glob('*.html'))+list(R.glob('*.png'))),sources=record(list((EP/'src').glob('e1_mapping_drift*.py'))+[EP/'tests/test_e1_mapping_drift.py']),tests=65,checks=v['count']+fa['count'],visual_review='pending',no_new_model_or_portfolio=True,forward='FORWARD_PENDING'));print('reports complete',flush=True)

if __name__=='__main__':main()

"""Self-contained Chinese research report with complete comparisons and artifacts."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from run import ROOT, CACHE, OUT, MAN, config, dump, sha

NAMES={'E1_78':'78特征 原收益MSE','RIC_78':'78特征 RankIC目标','RANK_MSE_78':'78特征 收益秩MSE','JR_11':'旧11特征 J_R','EW':'共同股票池等权'}
ORDER=['E1_78','RIC_78','RANK_MSE_78','JR_11']


def table(rows,headers):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])


def pct(x):return f'{x:.2%}' if pd.notna(x) else '未认证完整区间'


def main():
    stats=pd.read_csv(OUT/'rankic_summary.csv');acs=pd.read_csv(OUT/'accounts.csv')
    tests=pd.read_csv(OUT/'primary_tests.csv');groups=pd.read_csv(OUT/'decile_summary.csv')
    fold=pd.read_csv(OUT/'folds.csv');curve=pd.read_csv(OUT/'validation_checkpoints.csv')
    data=json.loads((MAN/'data.json').read_text());validation=json.loads((MAN/'validation.json').read_text())
    daily=pd.read_parquet(CACHE/'daily_accounts.parquet')
    figdir=OUT/'figures';figdir.mkdir(exist_ok=True)
    primary=stats.loc[stats.scope.eq('primary')].set_index('model')
    fig,axs=plt.subplots(1,2,figsize=(12,4.3),layout='constrained')
    colors=['#61758a','#217a66','#c18b30','#aa6571']
    for i,mid in enumerate(ORDER):
        r=primary.loc[mid];axs[0].errorbar(i,r['mean'],yerr=[[r['mean']-r.low],[r.high-r['mean']]],fmt='o',capsize=5,color=colors[i])
        d=groups.loc[groups.scope.eq('primary')&groups.model.eq(mid)].sort_values('decile')
        axs[1].plot(d.decile,d.mean_h10*100,marker='o',color=colors[i],label=mid)
    axs[0].set_xticks(range(4),ORDER,rotation=15);axs[0].axhline(0,color='#999',lw=.8)
    axs[0].set_title('Mean H10 RankIC and descriptive 95% interval')
    axs[1].set_title('All ten groups: mean known H10 return')
    axs[1].set_xlabel('Score decile (10 = highest)');axs[1].set_ylabel('Return per 10 sessions (%)');axs[1].legend()
    for ax in axs:ax.grid(axis='y',alpha=.2)
    fig.savefig(figdir/'ranking.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.5),layout='constrained')
    for mid,color in zip(ORDER,colors):
        d=daily.loc[daily.scope.eq('primary')&daily.valuation.eq('flat')&daily.cost.eq('main')&daily.portfolio.eq('D10')&daily.model.eq(mid)].sort_values('date')
        ax.plot(d.date,d.nav,label=mid,color=color)
    ax.set_title('D10 after fees: fixed H10, labelled suspension valuation proxy')
    ax.set_ylabel('NAV (initial = 1)');ax.legend();ax.grid(alpha=.2)
    fig.savefig(figdir/'nav.png',dpi=160);plt.close(fig)
    mainacc=acs.loc[acs.scope.eq('primary')&acs.valuation.eq('flat')&acs.portfolio.eq('D10')].set_index(['model','cost'])
    rows=[]
    for mid in ORDER:
        r=primary.loc[mid];a=mainacc.loc[(mid,'main')];z=mainacc.loc[(mid,'zero')]
        rows.append([NAMES[mid],f"{r['mean']:.4f}",f'[{r.low:.4f}, {r.high:.4f}]',pct(z.cagr),pct(a.cagr),pct(a.max_drawdown)])
    summary=table(rows,['模型','平均RankIC','描述性95%区间','D10零成本年化','D10主成本净年化','主成本最大回撤'])
    testtable=table([[r.test,f'{r.mean:.5f}',f'[{r.low:.5f}, {r.high:.5f}]',r.n,f'{r.holm_p:.4f}'] for r in tests.itertuples()],['预登记配对检验','均值差','95%区间','有效窗口','Holm p'])
    dec=groups.loc[groups.scope.eq('primary')].pivot(index='decile',columns='model',values='mean_h10')
    dectable=table([[f'D{d}']+[pct(dec.loc[d,m]) for m in ORDER] for d in range(1,11)],['十分组']+[NAMES[m] for m in ORDER])
    ext=stats.loc[stats.scope.eq('extended')].set_index('model')
    extacc=acs.loc[acs.scope.eq('extended')&acs.valuation.eq('flat')&acs.cost.eq('main')&acs.portfolio.eq('D10')].set_index('model')
    exttable=table([[NAMES[m],f"{ext.loc[m,'mean']:.4f}",int(ext.loc[m,'n']),str(extacc.loc[m,'end']),pct(extacc.loc[m,'cagr'])] for m in ORDER],['模型','扩展RankIC','窗口数','D10账户实际终点','完整扩展净年化'])
    annual=pd.read_csv(OUT/'yearly_rankic.csv').pivot(index='year',columns='model',values='rankic')
    annualtable=table([[y]+[f'{annual.loc[y,m]:.4f}' for m in ORDER] for y in annual.index],['年份']+[NAMES[m] for m in ORDER])
    top=acs.loc[acs.scope.eq('primary')&acs.valuation.eq('flat')&acs.cost.eq('main')&acs.portfolio.eq('TOP20')].set_index('model')
    toptable=table([[NAMES[m],pct(mainacc.loc[(m,'main'),'cagr']),pct(top.loc[m,'cagr'])] for m in ORDER],['模型','D10净年化','D9+D10净年化'])
    choices=fold.loc[fold.model.eq('RIC_78'),'chosen_steps'].value_counts().sort_index().to_dict()
    initial=curve.loc[curve.step.eq(0),['fold','validation_mean_rankic']].rename(columns={'validation_mean_rankic':'initial'})
    selected=curve.loc[curve.chosen].merge(initial,on='fold');improved=int((selected.validation_mean_rankic>selected.initial).sum())
    infos=json.loads((MAN/'accounts.json').read_text())
    failures=pd.DataFrame([dict(model=x['model'],portfolio=x['portfolio'],scope=x['scope'],valuation=x['valuation'],cost=x['cost'],failure=x['failure']) for x in infos if not x['valuation_complete']])
    failurestr='；'.join(sorted(set(str(x['failure']['date'])[:10]+' '+x['failure']['instruments'] for x in infos if x['scope']=='extended' and x['valuation']=='flat' and x['cost']=='main' and x['portfolio']=='D10' and not x['valuation_complete'])))
    weekly=pd.read_csv(OUT/'weekly_rankic_by_date.csv');weekly=weekly.loc[weekly.exit_date.le('2025-03-03')].groupby('model').rankic.agg(['mean','count'])
    text=f'''# EP37 原78特征与RankIC训练实验报告

本轮按用户要求，保留EP36全部78项原特征，重新训练以RankIC为目标的简单线性模型。原11特征实验、EP36源文件和既有结果保持原样；本报告属于独立追加分支。训练完成于2026-11-18，证据为已被反复检视的历史模拟样本外探索，真实前瞻仍为FORWARD_PENDING。

**恢复完整78特征与每周训练样本后，排序能力明显恢复。RankIC目标模型的平均RankIC为0.0552，高于原收益MSE模型的0.0406；但D10净年化为−1.69%，低于原收益MSE的+0.11%。收益秩MSE对照的RankIC为0.0692、D10净年化为+2.81%。因此，本轮支持继续研究原特征中的排序信息，不支持宣称直接优化RankIC已经带来更好的可交易Alpha。**

## 相同口径的主结果

主区间为2021-01-11开盘至2025-03-03开盘，100个不重叠H10窗口。四模型按同日、同股票池比较；D10是预测分数最高10%，等权配置，持仓计划为10个交易日。主成本为买入10bp、卖出20bp，H10到期全卖后重买，重复入选也支付两侧费用。

{summary}

上述净值和年化使用**明确标记的停牌估值代理**：仅已确认全天停牌可沿用先前收盘价，最多20个交易日；这不是对未知价格任意前填。所有严格报价账户均受缺失报价限制，无法给出完整严格实盘认证收益。股票报价为qfq合成单位，历史成员与报价并非严格PIT、公司行动权益台账未完成。

![排序与十分组](figures/ranking.png)

![成本后净值](figures/nav.png)

旧J_R在这里是共同池重算，净年化为−11.72%，与原报告原生股票池的−11.84%略有差异。新分支从原EP37的{data['source_EP37_rows']:,}个预测股票日期中，剔除{data['excluded_rows']}个不足80%原特征覆盖的股票日期，剩余{data['rows']:,}条；资格判断只读当时特征，**不因未来收益缺失删除选股候选**。所有模型都使用这一共同池，不能把这些微小口径变化藏进模型增益。

## 保留了什么与改变了什么

78项包含20项原日收益滞后、20项横截面标准化日收益滞后、6项动量、2项分段收益、12项波动幅度回撤位置、9项成交量成交额换手率相对值、9项市场变量。完整有序清单见[原78特征字典](original_78_features.csv)。原有重复列、截面常数列也保留，没有新增交互项、特征筛选或对输入再做秩变换。动量、短期收益及其他路径特征共同进入同一个线性评分函数；反转方向由训练权重决定。

训练恢复EP36原每周样本，而交易与评估仍每10个交易日一次。首折恢复52,724条训练记录，最后一折140,039条。缺失值用训练集列中位数填补，再用训练集均值和总体标准差标准化，常数标准差设为1，与原EP36一致。训练窗口为季度扩展窗口，只允许季度开始前已到期的H10标签。

因此“78特征对旧11特征”的对照同时恢复了特征和训练采样频率，不能把全部改善单独归因于特征数量；**三种78特征模型之间**使用相同数据、同样训练行和输入变换，才是本轮训练目标比较。

## RankIC如何进入训练

RankIC是每个信号日股票预测分数与未来H10收益的Spearman相关系数，最后按日期等权平均。它检验整个横截面的排序，而非只检验D10。

真实硬排序的导数几乎处处为零或未定义，不能直接把硬RankIC接到普通梯度优化器后声称完成训练。[可微排序研究](https://proceedings.mlr.press/v119/blondel20a.html)讨论了这一问题；本实现采用透明的两两sigmoid软秩近似，**没有声称复刻该论文的快速投影算法**。最终评价使用真实Spearman，定义参考[SciPy文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html)。

对同一天的线性分数先中心化并除以截面总体标准差，记为z；软秩为 `soft_rank_i = sum_j sigmoid((z_i-z_j)/0.1)`。目标收益采用真实平均秩，损失是软预测秩与目标真实秩的Pearson相关系数的负值，再按日期等权平均。训练批次包含16个日期，填充行完全排除；同一日期内比较，不把不同日期的股票混在一起排序。

主模型RIC_78仅有78个线性系数。以同一训练分区上的原Ridge权重初始化，Adam学习率0.005，系数每步归一化，固定随机种子20261118。过去12个月作为内层验证，内层训练标签到期日严格早于验证首个入场日；30、60、120步三个预先登记检查点以**真实验证集平均RankIC**选择，平局取更少步数，再在本季度所有成熟训练样本上重训。0步仅作为诊断，不参与主模型选取。

24折选中步数分布为{choices}，其中{improved}/24折选中的正步数模型验证RankIC高于0步初始模型。所有参数在查看本分支外层表现前冻结，没有按结果扩大搜索，也没有把收益秩MSE对照事后替换成主模型。此轮得到的是有限训练预算下的RankIC近似优化结果，不是全局最优解证明。

对照模型E1_78仍最小化收益z-score的MSE，Ridge alpha=10；RANK_MSE_78最小化同日收益秩的MSE，alpha也固定10。**拟合收益秩不等于优化RankIC**，所以将两者分别保存和报告。

## 改善是否足够可靠

主检验家族只包含预登记的三项，使用6个H10日期的循环移动块、2,000次重采样、双侧检验并作Holm修正。缺失事件保留日历位置，不把股票当作独立样本。

{testtable}

RIC_78对E1_78的RankIC增量约0.0147，95%区间跨零；对旧11特征的改善较大，但三项校正后仍未达到0.05阈值。D10配对净收益差只在98个双方均可完整退出的窗口计算，均值约每10日−0.0425个百分点；其区间也跨零。主表每个模型自身RankIC的区间是描述性结果，不能替代模型增量或独立Alpha检验。

历史已在前期研究中被检视，本轮没有新增独立未来样本，也没有完成控制动量、行业、规模等暴露后的独立Alpha认证。收益秩MSE对照的较高点估计值得保留，但不是事后重选后的独立确认。

## 十分组与头部组合

下表是每个日期各组已知H10报价收益的等权均值，再按日期平均；不是连续账户年化，也未扣成本。未知收益不填零，完整已知数量和选择数量见[分组汇总](decile_summary.csv)及[逐期分组](deciles_by_date.csv)。所有十分组都保留，未按结果挑选获利组。

{dectable}

头部组合使用同一交易引擎时的主成本净年化如下，TOP20固定为D9与D10合并，不改变原排序：

{toptable}

整体RankIC可以在中间或底部分组排序更准确时提高，D10却未必选到更高回报股票。本轮RIC_78零成本D10年化为6.03%，低于原收益MSE的7.97%，所以它的头部收益弱化在扣费前已存在；固定H10全量换手又将前者净年化压到−1.69%。不能把全部问题都归为手续费，也不能拿排序相关系数替代可交易收益。

## 时间稳定性与扩展样本

以下年度RankIC使用每年本分支全部可评价H10窗口，2025年包括主区间之后的数据，2026年截至现有完整窗口：

{annualtable}

RIC_78在2021年仍为负，2025年又弱于原收益MSE，说明排序增益并不在每年都成立。

{exttable}

扩展排序可评估至2026-10-12，共139个窗口。连续持仓账户更严格：E1_78、RIC_78、RANK_MSE_78的D10账户在{failurestr}遇未知持仓估值而停止认证，不能将其部分收益与旧J_R的完整扩展年化横排。完整停止原因与终点见[账户回执](../manifests/accounts.json)。

原EP36每周日历的次级诊断，主区间共{int(weekly.loc['E1_78','count'])}个信号：E1_78平均RankIC为{weekly.loc['E1_78','mean']:.4f}、RIC_78为{weekly.loc['RIC_78','mean']:.4f}、RANK_MSE_78为{weekly.loc['RANK_MSE_78','mean']:.4f}。该诊断没有另开每周交易账户，也没有据此重新选择参数。

## 交付与复核

本轮完成72个最终季度模型。78项特征在150,300条EP36原记录上逐项比对，共11,723,400个值及缺失位置一致，最大误差0；24季度原E1训练行数和预测全部复现，预测误差0。7项单元测试覆盖梯度数值检查、填充排除、按日期计算、训练变换、标签隔离、合成排序与确定性、尺度平移不变性。最终保存模型重放72份、主成本代理账户账本重建18条均通过；全部{validation['frozen_input_hashes']}个冻结输入与代码哈希保持不变。

- [冻结合同](../config.json)、[来源和环境快照](../manifests/freeze.json)、[最终核验](../manifests/validation.json)。
- [每折训练范围](folds.csv)、[各验证检查点](validation_checkpoints.csv)、[EP36原预测复现](original_E1_reproduction.csv)。
- [所有股票完整预测排序](all_rankings.csv.gz)、[全部目标持仓](all_target_holdings.csv.gz)、[逐期RankIC](rankic_by_date.csv)。
- [全部账户汇总](accounts.csv)、[全部十分组可执行事件](events.csv)、[主检验](primary_tests.csv)。
- 完整模型、连续账户逐日净值、实际成交与逐日持仓在本分支`local_cache/`中；[2026Q4 RankIC模型](../local_cache/models/2026Q4_RIC_78.json)。这些大体积本地派生文件被Git忽略，不等于未生成。

固定结果可用 `PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=4 python -m pytest test_model.py -q` 和 `PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=4 python validate.py` 复核。完整复现阶段为`run.py prepare/train/select/economics/analyze`及`report.py`，应复制到新输出版本后运行，以保留本轮结果。没有接入实盘、发送通知或启动定时任务。
'''
    (OUT/'REPORT.md').write_text(text)
    body=markdown.markdown(text,extensions=['tables','fenced_code'])
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EP37 原78特征与RankIC训练</title><style>body{max-width:1180px;margin:36px auto;padding:0 28px;font:16px/1.8 system-ui,sans-serif;color:#243442;background:#fbfcfa}h1,h2{line-height:1.35;color:#174a43}h2{margin-top:42px}table{width:100%;border-collapse:collapse;font-size:14px;display:block;overflow:auto}th,td{padding:8px 12px;border-bottom:1px solid #d8e2df;text-align:left;white-space:nowrap}th{background:#e8f0ed}img{max-width:100%;background:white;border:1px solid #dce4e0}a{color:#176c5a}code{background:#edf1ef;padding:2px 4px}p{margin:14px 0}</style>'''+body+'</html>'
    (OUT/'REPORT.html').write_text(html)
    latest=fold.loc[fold.model.eq('RIC_78')].iloc[-1]
    dump(MAN/'latest_model.json',dict(model='RIC_78',fold=latest.fold,path=latest.model_path,sha256=latest.model_sha256,
         feature_count=78,chosen_steps=int(latest.chosen_steps),fit_cutoff=latest.cutoff,max_label_maturity=latest.max_label_maturity,
         production_enabled=False,forward_status='FORWARD_PENDING'))
    dump(MAN/'report.json',dict(files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in [OUT/'REPORT.md',OUT/'REPORT.html',*sorted(figdir.glob('*.png'))]],
         main_conclusion='Ranking improves versus original11; direct RankIC surrogate does not prove economic improvement over original78 Ridge',status='COMPLETE_WITH_LIMITATIONS'))
    print('report generated',flush=True)


if __name__=='__main__':main()

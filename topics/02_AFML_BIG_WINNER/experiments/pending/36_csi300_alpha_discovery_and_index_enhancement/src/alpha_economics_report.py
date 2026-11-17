"""Independent Chinese reports for A2, B1 and B2 with complete artifact links."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from common import EP,sha,save_json
from alpha_economics import DEST,LOCAL,CONFIG,RUN,verify
REPORT=EP/'reports'/RUN


def table(f,percent=()):
 f=f.copy()
 for c in percent:
  if c in f:f[c]=f[c]*100
 for c in f:
  if pd.api.types.is_float_dtype(f[c]):f[c]=f[c].map(lambda x:f'{x:.4f}' if pd.notna(x) else 'NA')
 return f.to_markdown(index=False)


def write(name,text):
 (REPORT/(name+'.md')).write_text(text)
 html=markdown.markdown(text,extensions=['tables','fenced_code'])
 (REPORT/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>EP36 Alpha信息与时间结构验证</title><style>body{max-width:1150px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd;text-align:left}th{background:#edf3f5}img{max-width:100%}pre{overflow:auto;background:#f4f4f4;padding:16px}a{color:#146887}</style>'+html+'</html>')


def figures():
 curve=pd.read_csv(DEST/'event_curve.csv');a=curve[(curve.scope=='primary')&(curve.model=='E1')&(curve.phase==1)]
 fig,ax=plt.subplots(figsize=(10,4.7))
 for contrast,color in [('S1-S0','#247ba0'),('S2-S0','#c8553d')]:
  g=a[a.contrast==contrast];x=g.horizon.to_numpy();y=g['mean'].to_numpy()*100
  ax.plot(x,y,label=contrast,color=color);ax.fill_between(x,g.ci_low.to_numpy()*100,g.ci_high.to_numpy()*100,alpha=.14,color=color)
 ax.axhline(0,color='gray',lw=1);ax.set(xlabel='Trading sessions after entry',ylabel='Cumulative relative P&L (percentage points)',title='E1 phase 1: fixed event basket, entry fee included, exit fee excluded')
 ax.legend();ax.grid(alpha=.15);fig.tight_layout();fig.savefig(REPORT/'event_curve.png',dpi=170);plt.close(fig)
 metrics=pd.read_csv(DEST/'account_metrics.csv');g=metrics[(metrics.scope=='primary_common')&(metrics.model=='E1')&(metrics.strategy=='S1')]
 fig,ax=plt.subplots(figsize=(9,4.7));x=np.arange(3)
 for i,(cost,label,color) in enumerate([('zero','Zero cost','#577590'),('main','Buy10 / Sell20 bps','#43aa8b'),('stress','Buy30 / Sell80 bps','#f3722c')]):
  y=g[g.cost==cost].set_index('frequency').loc[['1w','2w','1m'],'cagr'].to_numpy()*100
  ax.bar(x+(i-1)*.24,y,.24,label=label,color=color)
 ax.set_xticks(x,['Weekly','Calendar biweekly','First weekly signal / month']);ax.set(ylabel='CAGR (%)',title='E1 constrained S1: independent continuous accounts')
 ax.axhline(0,color='gray',lw=1);ax.legend();fig.tight_layout();fig.savefig(REPORT/'cost_and_frequency.png',dpi=170);plt.close(fig)
 pairs=pd.read_csv(DEST/'monthly_pairs.csv');g=pairs[(pairs.scope=='primary')&(pairs.model=='E1')&(pairs.cost=='main')&(pairs.horizon==10)&(pairs.contrast=='S1-S0')]
 fig,ax=plt.subplots(figsize=(12,4.3));x=pd.to_datetime(g.month);y=g.phase_difference.to_numpy()*100
 ax.bar(x,y,width=20,color=np.where(y>=0,'#43aa8b','#f3722c'));ax.axhline(0,color='gray',lw=1)
 ax.set(ylabel='Phase1 minus Phase2 increment (pp)',title='B1 E1 H10: monthly paired relative returns; missing months remain gaps')
 fig.tight_layout();fig.savefig(REPORT/'phase_pairs.png',dpi=170);plt.close(fig)


def main():
 verify();REPORT.mkdir(parents=True,exist_ok=True)
 v=json.loads((DEST/'validation.json').read_text());assert v['status']=='PASS'
 cap=json.loads((DEST/'cap_audit.json').read_text())
 a1=pd.read_csv(DEST/'a1_caps_summary.csv');events=pd.read_csv(DEST/'event_summary.csv');accounts=pd.read_csv(DEST/'account_metrics.csv');contrasts=pd.read_csv(DEST/'account_contrasts.csv');windows=pd.read_csv(DEST/'marginal_net_windows.csv');coverage=pd.read_csv(DEST/'event_coverage.csv');risk=pd.read_csv(DEST/'event_exposures.csv');arisk=pd.read_csv(DEST/'account_exposures.csv');overlap=pd.read_csv(DEST/'selection_overlap.csv');placebo=pd.read_csv(DEST/'placebo_summary.csv');pcov=pd.read_csv(DEST/'placebo_coverage.csv');stability=pd.read_csv(DEST/'stability.csv');contrib=pd.read_csv(DEST/'rebalance_contribution_summary.csv')
 figures()
 general='''本轮沿用封存 E1 Ridge 和 E2 预测，未训练新模型、未运行 E3、未优化相位或调仓参数。新增总市值与流通市值来自信号日前一个交易日的供应商快照，仍为 Historical-proxy；历史行业、前复权合成单位和停牌估值也保留原代理身份。所有历史已反复查看，结果属于历史模拟样本外探索，真实前瞻为 FORWARD_PENDING。

S0 是以当天已覆盖风格拟合原模型分数后的 Q5；S1 用原分数、S2 用残差分数，在 S0 附近的固定暴露约束内选股。**S0 仍依赖原模型分数，并非独立训练的强风格收益模型，不能据此宣布可以直接替换 Ridge。**

每期同一可评分池、相同持仓数及等权目标；数值风格目标差不超过截面0.25个标准差、单行业权重差不超过2个百分点。容差在收益计算前冻结，无事后放宽。约束控制目标组合，成交受限与持仓漂移仍会改变实际暴露；净收益结论是这一固定近似匹配合同下的部分识别，不是精确风险中性的认证 Alpha。'''
 mainrows=events[events.holm_p.notna()][['experiment','contrast','n','planned_periods','mean','ci_low','ci_high','holm_p']]
 monthly=accounts[(accounts.scope=='primary_common')&(accounts.cost=='main')&(accounts.frequency=='1m')][['model','strategy','cagr','annual_oneway_turnover']]
 write('REPORT',f'''# EP36 Alpha 信息增量与时间结构验证结果

**A2 未确认 Ridge 相对风格复制组合的稳定净增量；B1 未确认模型特有的月初优势；B2 未识别到稳定的正向残差收益兑现期限。** 月度账户仍较好，但风格复制组合也有类似表现，且双周对月度在零成本下已落后，不能把优势全归因于交易费用。

这是对现有结论的证伪式检查，不是把“不显著”写成“没有 Alpha”。独立强风格模型尚未训练，严格 PIT 与真实前瞻也尚未完成。

## 1 本轮完成范围

- 补取296个信号对应的前一交易日市值快照，审计88,698条历史成分记录，接受88,687条，剔除11条股本／市值恒等式冲突。
- 完成加入市值的 A1 补充、E1/E2 三种策略的组合约束选股、A2固定窗口净收益、B1两相位配对及分层随机对照、B2固定事件曲线与独立连续账户。
- 54条账户全部运行至原行情终点2026-10-21。主比较仍固定为2021-01-08信号至2025-03-03，共1001个净值交易日，首次执行2021-01-11并计入建仓费用。
- 41项测试、{v['check_count']}项目标／账本／结果检查通过；换仓贡献另有3072个窗口完成对账。原预测、输入和旧报告未覆盖。

## 2 三项主检验

下表均为每事件或每配对月份的收益差，单位为百分点，**不是年化收益**。三项共同构成事先登记的 E1 主检验族；95%为未作多重校正的3个月块 Bootstrap 百分位区间，Holm p 单列。

{table(mainrows,percent=['mean','ci_low','ci_high'])}

三项区间均跨零，不能确认正向净增量。原始点估计偏负，也不能把它们当成已证明负 Alpha。

## 3 连续账户与固定事件不能混用

月内第1信号、主成本买10/卖20bps、共同主区间的连续账户如下。CAGR为年化百分比，单边换手为每年倍数。

{table(monthly,percent=['cagr'])}

E1 的风格复制组合约7.70%，受约束原分数组合约6.19%，残差组合约5.20%。这些是本轮共同样本与固定约束下的新账户，**不是旧原始Q5账户的直接复跑**；不能用6.19%对比旧4.84%宣称策略改进。

{general}

## 4 独立报告与裁决

| 项目 | 报告 | 当前裁决 |
|---|---|---|
| 市值与 A1 补充 | [A1及数据审计](A1_CAPS.md) | 加入市值后残差排序主区间仍未确认，条件收益关联仍偏正 |
| A2 信息净增量 | [A2详细报告](A2.md) | 在本轮风格复制对照及固定容差下，未确认稳定净增量 |
| B1 月内相位 | [B1详细报告](B1.md) | 第1相位相对第2相位的模型额外优势未确认；随机对照覆盖不足 |
| B2 信号与账户寿命 | [B2详细报告](B2.md) | 无稳定正向残差兑现段；月度优势同时包含路径和成本因素 |
| 原始研究边界 | [执行协议](PROTOCOL.md) | Historical-proxy、部分风险匹配、历史选择偏差均保留 |

## 5 下一步意味着什么

现有证据不支持继续升级复杂模型或搜索更漂亮的历史调仓参数。值得保留的是已冻结的对照体系和失败分支。若未来比较独立训练的强风格模型，须另行登记并只使用当时成熟收益；若开始前瞻，须在新信号未来收益尚未被观察时封存。二者本轮均未执行，不能用本轮 S0 或长历史补充区间代替。

## 6 可复核交付

- [精确配置](../../configs/{CONFIG.name}) · [输入与源代码冻结](../../outputs/diagnostics/{RUN}/freeze.json) · [选股先于收益的封存凭据](../../outputs/diagnostics/{RUN}/selection_complete.json)
- [事件汇总](../../outputs/diagnostics/{RUN}/event_summary.csv) · [逐月配对](../../outputs/diagnostics/{RUN}/monthly_pairs.csv) · [完整账户逐月收益](../../outputs/diagnostics/{RUN}/account_monthly.csv)
- [验证清单](../../outputs/diagnostics/{RUN}/validation.json) · [换仓贡献核验](../../outputs/diagnostics/{RUN}/rebalance_contribution_validation.json)
- [全部文件哈希](manifest.json)

在EP36目录执行：

```bash
OPENBLAS_NUM_THREADS=4 python -m pytest tests -q
OPENBLAS_NUM_THREADS=4 python src/alpha_economics.py verify
OPENBLAS_NUM_THREADS=4 python src/alpha_economics_validate.py
OPENBLAS_NUM_THREADS=4 python src/alpha_economics_report.py
```

未提交、推送、部署或启动自动监控。原始供应商响应、分解分数、组合名单与账本留在被忽略的 private/{RUN}/ 和 private/style_caps_20261117/；公开交付为研究汇总、源码和核验凭据。
''')
 ap=a1[(a1.scope=='primary')&(a1.horizon=='h10')][['model','metric','n','mean','ci_low','ci_high']]
 cv=pd.read_csv(DEST/'coverage.csv');c=cv[cv.signal_date.between('2021-01-08','2025-03-03')]
 write('A1_CAPS',f'''# EP36 市值补充与 A1 条件信息验证

**加入总市值和流通市值后，E1 主区间残差 RankIC 约0.0085，区间仍跨零；这没有推翻首批 A1 的裁决。** 条件收益回归仍有正向线索，不能把排序与收益幅度的不同检验合并成一个结论。

{general}

## 数据从哪里来

使用既有权限调用 Tushare daily_basic，获取296个信号日前一市场交易日的确切快照。供应商说明该接口提供总市值、流通市值等字段，通常于交易日15至17点更新，单次最多6000行。[官方字段文档](https://tushare.pro/document/2?doc_id=32)

本轮每次响应均少于6000行，按日期和股票键检查重复，并保存原文SHA256、参数和 observed_at。日志不保存令牌。总市值 total_mv、流通市值 circ_mv 的单位都是万元；circ_mv不是自由流通市值，不把两者混称。

利用同日 close×total_share 与 total_mv、close×float_share 与 circ_mv 的恒等关系审计，允许1e-4相对舍入差；另与封存未复权收盘价核对，容差0.01元加1e-5相对差。88,698行中11行恒等式冲突被剔除，价格冲突0行。缺少行与冲突均不填补。总计88,687行通过。

前一交易日滞后可降低当日更新时钟风险，但不能证明历史数据未修订；known_at仍未认证，保持Historical-proxy身份。该滞后下的市值也是明确的一日旧值，不是信号日实时市值。

## 共同样本与指标

主日期范围内原成分股票信号行{int(c.original.sum()):,}，13项数值风格与两模型共同分数完整行{int(c.common.sum()):,}；每期约{int(c.common.min())}至{int(c.common.max())}只股票。主要覆盖限制仍来自原有换手率窗口，新增市值冲突不会被偷偷填零。

以下为H10主区间结果，共210个有效信号。IC无单位；conditional_slope为每一原分数截面标准差对应的收益小数，例如0.001216等于0.1216个百分点。此补充未替换首批冻结检验族，也未把辅助 p 值纳入新的“成功”裁决。

{table(ap)}

## 能说明与不能说明什么

解释分数仍保留较强排序关联，但完整复制程度不等于经济收益等价。加入市值后的残差排序没有获主区间支持；条件收益系数仍偏正。这种分歧正是继续做经济对照的原因，不能选其中有利的一项作为结论。

本轮没有独立未见过的历史，不能把市值补充称为真正确认性检验。原首批A1文件与哈希保持不变，本轮使用独立目录。

[市值审计](../../outputs/diagnostics/{RUN}/cap_audit.json) · [共同样本](../../outputs/diagnostics/{RUN}/coverage.csv) · [全部 A1 补充](../../outputs/diagnostics/{RUN}/a1_caps_summary.csv) · [周级原始统计](../../outputs/diagnostics/{RUN}/a1_caps_weekly.csv)
''')
 a2=events[(events.scope=='primary')&(events.horizon==10)&(events.cost=='main')&events.experiment.isin(['A2_phase1','A2_phase2','A2_executed_risk_subset'])][['model','experiment','contrast','n','planned_periods','mean','ci_low','ci_high','holm_p']]
 con=contrasts[(contrasts.scope=='primary_common')&(contrasts.cost=='main')][['model','frequency','contrast','cagr_difference','annual_mean_active','ci_low','ci_high','tracking_error','relative_max_drawdown']]
 cov=coverage[(coverage.scope=='primary')&(coverage.cost=='main')&(coverage.horizon==10)][['model','strategy','planned_events','rows_present','known_net','mean_unfilled_buy','mean_unsold']]
 riskm=risk.groupby('model').agg(event_bound_pass=('risk_within_target_bounds','mean'),mean_numeric_gap=('numeric_gap','mean'),mean_industry_gap=('industry_gap','mean')).reset_index()
 ar=arisk.groupby(['model','frequency']).agg(account_bound_pass=('within_bounds','mean'),mean_unmapped_weight=('unmapped_weight','mean')).reset_index()
 ov=overlap.groupby('model')[['q5_overlap','s1_s0_overlap','s2_s0_overlap']].mean().reset_index()
 write('A2',f'''# EP36 A2 同风格组合的净信息增量

**主区间未确认 S1 或 S2 相对 S0 的稳定正向净收益增量。** 月初H10固定事件平均差偏负；连续账户不同频率的结果有正有负，区间均不足以确认稳定提升。

## 想验证什么

在同日股票池、持仓数、成本和相近风险暴露下，原Ridge分数或残差分数，是否比其已知风格解释部分更有经济价值？这里的“净”包括实际成交的入场和可执行退出成本，而不是只看未扣费标签均值。

{general}

## 组合如何构造

S0取风格解释分数的Q5，持仓数使用原floor分组规则。S1/S2在全共同样本内最大化对应分数秩，二元选股、相同k只、每只1/k权重，施加相对S0的13项数值暴露与行业限制。求解器时间上限2秒、相对目标gap上限1%，不根据收益调整。592个模型×信号对应的1184次约束求解全部取得通过独立约束复验的解，最大报告gap小于1%。有限gap意味着不声称每次都获得唯一精确最优名单。

名单平均重合比例：

{table(ov,percent=['q5_overlap','s1_s0_overlap','s2_s0_overlap'])}

q5_overlap 是受约束S1相对本轮共同样本原分数Q5的重合比例。它不是旧全样本Q5的复刻率。S1仍由原分数选股，但约13.5%的E1名单平均发生改变，解释时须保留这一条件。

## 固定 H10 事件主结果

单位为每事件收益差百分点。第1相位是A2主比较；第2相位和成交后风险合格子集是辅助。各项共同按信号月保留空档，3个月块Bootstrap，2000次。主族Holm p只有两项A2与一项B1，不向辅助结果扩张。

{table(a2,percent=['mean','ci_low','ci_high'])}

E1主比较计划50个月，其中46个月可完成成对净收益评价。没有把其余月份填零，也没有只保留可顺利退出的股票来重建名单。评价阶段的缺失仍可能有选择性，因此是部分识别。

## 成交与风险匹配的实际边界

主区间第1与第2相位合计100个计划事件的覆盖如下；known_net要求持有路径可估值且该策略能在规定开盘完全退出。

{table(cov,percent=['mean_unfilled_buy','mean_unsold'])}

全可用区间的事件建仓后风险容差通过率如下：

{table(riskm,percent=['event_bound_pass','mean_industry_gap'])}

独立连续账户在各自再平衡日，成交后相对S0的同日冻结风格暴露检查如下。未映射权重来自旧持仓不在当日共同可评分池，不能按零风险处理。

{table(ar,percent=['account_bound_pass','mean_unmapped_weight'])}

容差通过率并非100%，也没有逐日重新中性化持仓。不能把这些账户说成全程精确同风险组合。主表保留冻结的全可评价样本；事后风险合格子集仅辅助，不替换主族。

## 独立连续账户

主区间主成本结果如下，收益、区间、跟踪误差和相对回撤单位为百分比或百分点。cagr_difference是两个CAGR之差；annual_mean_active及其65交易日块区间是日收益差均值×252，二者不是同一估计量。

{table(con,percent=['cagr_difference','annual_mean_active','ci_low','ci_high','tracking_error','relative_max_drawdown'])}

E1月度S1相对S0的CAGR差约−1.51个百分点，S2约−2.51个百分点。它们的日均差年化区间跨零。双周S1点估计偏正，同样不能单独挑出来作为策略成功。

## 当前裁决

没有确认稳定独立净增量；也没有设置等价界限来证明简单策略完全复制了Ridge。S0依赖原预测，尚不能作为独立替代模型。没有理由因本轮历史结果增加E3或搜索新阈值。

[全部事件汇总](../../outputs/diagnostics/{RUN}/event_summary.csv) · [全部连续账户指标](../../outputs/diagnostics/{RUN}/account_metrics.csv) · [完整逐月收益](../../outputs/diagnostics/{RUN}/account_monthly.csv) · [实际暴露](../../outputs/diagnostics/{RUN}/account_exposures.csv)
''')
 b1=events[(events.scope=='primary')&(events.horizon==10)&(events.cost=='main')&(events.experiment=='B1_phase1-phase2')][['model','contrast','n','planned_periods','mean','ci_low','ci_high','holm_p']]
 pv=placebo.groupby('model').agg(replicates=('replicate','count'),min_paired_months=('n','min'),median_paired_months=('n','median'),max_paired_months=('n','max'),mean_effect=('mean','mean'),min_effect=('mean','min'),max_effect=('mean','max')).reset_index()
 pc=pcov.groupby('model').agg(planned_draws=('accepted','size'),accepted=('accepted','sum'),acceptance=('accepted','mean')).reset_index()
 years=pd.read_csv(DEST/'event_yearly.csv');yrs=years[years.contrast=='S1-S0'][['model','year','paired_months','phase_difference']]
 write('B1',f'''# EP36 B1 风格控制后的月内相位优势

**未确认第1个周信号存在相对风格复制组合的额外 H10 优势。** E1相位差点估计约−0.097个百分点，95%区间约[−0.350,+0.163]个百分点，不能解释为已证明负效应或已证明全部由日历造成。

## 想验证什么

每个月先在第1相位计算S1−S0，再在第2相位计算同一差异，最后取前者减后者。两次使用各自次日开盘和固定H10窗口，不把账户长期路径差混进固定期限事件。只要求第1、第2相位共同有效，不沿用旧四相位共同月份。

{general}

## 配对相位结果

单位为每月配对差百分点。E1 S1−S0属于三项主族，其余是辅助。

{table(b1,percent=['mean','ci_low','ci_high'])}

![逐月相位增量差](phase_pairs.png)

E1共有42/50个月能完整评价两相位的S1与S0净收益；图中未评价月份保持空档，不能作为零收益月份。以下逐年分解仅用于查看集中度，2025年是部分年度，不按年度切换策略。

{table(yrs,percent=['phase_difference'])}

## 随机分层安慰剂

在同日行业内分别按总市值和20日收益的中位数切分，形成行业×规模×动量单元；每个单元随机选择与S1相同的股票数量，固定20个重复、统一种子，每个重复最多100次尝试。只有同时满足相对S0原数值／行业容差的抽样才保留。不通过就记缺失，不改分层、不增加次数、不放宽容差。

{table(pc,percent=['acceptance'])}

下表的effect是 `(S1−随机对照)_phase1 − (S1−随机对照)_phase2`，单位百分点；所有预定重复均保留，没有挑选有利seed。随机对照可能与原名单重合，不宣称完全独立股票配对。

{table(pv,percent=['mean_effect','min_effect','max_effect'])}

E1每重复通常只有约15个共同月份，E2更少，覆盖远不足以作强安慰剂裁决。20个重复不是20份独立市场样本；其均值区间不能直接解释为20倍证据。约52.8%的候选重复通过了固定抽样与风险门槛，其余失败抽样及缺失退出月份不能被外推。

## 当前裁决

风格匹配后没有确认模型特有的月初相对优势。但缺失事件、近似风险容差、代理数据和较少月份意味着“月初效应完全由日历解释”也没有被证明。配对差异中之差没有随机分配交易日期，不作严格因果识别。

较长区间也未确认E1正向相位增量，不能用扩展区间替代原主检验。完整明细见下方，不再搜索第3、第4相位或其他调仓日。

[相位与其他主副检验](../../outputs/diagnostics/{RUN}/event_summary.csv) · [逐月完整配对](../../outputs/diagnostics/{RUN}/monthly_pairs.csv) · [全部随机重复](../../outputs/diagnostics/{RUN}/placebo_summary.csv) · [抽样覆盖](../../outputs/diagnostics/{RUN}/placebo_coverage.csv)
''')
 win=windows[(windows.scope=='primary')&(windows.phase==1)][['model','contrast','window','n','planned_periods','mean','ci_low','ci_high']]
 costs=accounts[(accounts.scope=='primary_common')&(accounts.strategy=='S1')][['model','frequency','cost','cagr','annual_oneway_turnover']]
 st=stability.groupby(['model','strategy'])[['rank_stability','retained_fraction']].mean().reset_index()
 ct=contrib[contrib.strategy=='S1']
 roots=json.loads((DEST/'breakeven.json').read_text())
 write('B2',f'''# EP36 B2 信号兑现期限与组合交易周期

**没有识别到稳定的正向残差收益段，因此不能宣布 Alpha 在第10天衰减或持续到第20天。** 连续账户显示：月度优于双周不仅来自费用；周度对月度则确有明显的成本影响。这些是本轮受约束策略的历史路径结果，不是新调仓规则。

## 想验证什么

固定信号名单后，1至5日、6至10日、11至20日是否持续产生相对风格对照的增量？然后独立检验不同交易频率在实际费用与持仓漂移下的表现。事件曲线不拼接成账户净值，H10训练标签也不直接决定最优持有期。

{general}

## 固定事件的边际净收益

每次从次日开盘建立固定股票与单位，不再重选。H5/H10/H20分别对应进入后第5/10/20个市场交易日的开盘退出。无法卖出的持仓不假设已变现，未知估值不沿用无依据旧价。

下表使用同一批可完整观察且H20可完全退出的事件。1至5日含一次入场费；6至10日不虚构交易；11至20日含实际H20退出费。三段相加严格等于该H20事件的净相对收益，不在每段重复扣往返费。单位为每事件初始资本的收益差百分点。

{table(win,percent=['mean','ci_low','ci_high'])}

E1 S1−S0三段约为+0.018、−0.082、−0.124个百分点，区间均跨零。不同对照组合的共同有效事件数不同，不能拿各段单独挑选不同样本。S2也未出现稳定正向兑现段。

![固定事件累计相对损益](event_curve.png)

图中路径为扣入场费、未扣退出费的每日标记损益；阴影为逐点95%区间，不是全曲线同时置信带。表格末段另计实际退出费，图末端不能直接读作可执行净退出收益。H5/H10/H20各自独立退出的净收益另在事件汇总中，不能与这条固定H20路径混淆。

## 独立连续账户与成本

以下CAGR为百分比，单边换手为每年倍数。双周沿用日历周锚点，月度沿用月内第1信号，并非精确每10/20个交易日调仓。

{table(costs,percent=['cagr'])}

![费用与频率](cost_and_frequency.png)

E1零成本周度约13.28%，月度约9.02%；主成本后周度约4.41%，月度约6.19%，说明成本确实会改变这两个周期的排序。另一方面，双周零成本约6.01%，已经低于月度9.02%，说明双周对月度差异不能仅由费用解释。

**这不证明月度是最优周期。** 月度路径也可能反映信号采样、市场状态与历史选择偏差；未新增日历或缓冲参数搜索。

## 盈亏平衡成本

按预先登记的双周对月度S1比较，固定卖出费用为买入费用2倍，在买入0至100bps、每10bps网格上做账户重放，再对变号区间二分求根。E1和E2都没有出现网格变号区间；零成本时双周已经落后。

{table(pd.DataFrame([dict(model=r['model'],zero_cost_terminal_gap=r['zero_cost_terminal_gap'],at100bps_terminal_gap=r['at100bps_terminal_gap'],buy_bps_roots=str(r['buy_bps_roots'])) for r in roots]),percent=['zero_cost_terminal_gap','at100bps_terminal_gap'])}

terminal_gap为双周减月度的期末净值差，按初始资本折算为百分点，不是CAGR差。这里只能说审计网格未找到变号交点，不能证明所有连续成本值都没有切点或多个交点。没有用“年化差除以换手”替代重放，也没有把求根结果变成推荐费用或周期。

## 换仓边际贡献与名单稳定性

下面的换仓分解是看到主结果后的机制诊断，不属于主检验族。对每个实际再平衡，比较已成交持仓与“保留完全相同的交易前股票及现金”到下次原定再平衡开盘的差异；买入贡献、卖出贡献和费用逐项对账。没有假设额外成交，也没有选择盈利月份。

单位为每次决策窗口的初始NAV百分点，窗口长度不同；不能相加或机械年化为策略收益。

{table(ct,percent=['mean_buy','mean_sell','mean_fees','mean_total'])}

全可用信号相邻周的分数秩相关和实际选股名单留存比例：

{table(st,percent=['retained_fraction'])}

这些统计描述更新幅度，不自动说明该换仓值得执行。连续账户完整逐月记录及所有成本分支均已保存。

## 当前裁决

B2没有观察到足够稳定的正向相对路径，不能据此重定义训练标签。成本后月度账户较好与“信号可预测20天”是两回事；本轮没有把二者合并。真实预测寿命仍需新的冻结前瞻信号观察。

[边际净收益](../../outputs/diagnostics/{RUN}/marginal_net_windows.csv) · [逐事件对账](../../outputs/diagnostics/{RUN}/marginal_net_events.csv) · [完整曲线](../../outputs/diagnostics/{RUN}/event_curve.csv) · [成本重放](../../outputs/diagnostics/{RUN}/breakeven_replays.csv) · [换仓贡献](../../outputs/diagnostics/{RUN}/rebalance_contributions.csv) · [全部逐月账户](../../outputs/diagnostics/{RUN}/account_monthly.csv)
''')
 write('PROTOCOL',f'''# EP36 A2 B1 B2 执行协议与登记顺序

本轮是在首批A1已知结果后登记的新版本。原首批协议、结果与哈希保留，不将本轮包装为独立盲测。

1. 先获取历史市值并保存原响应和时间，明确Historical-proxy，剔除单位恒等式与封存收盘冲突。
2. 收益计算前冻结[完整JSON配置](../../configs/{CONFIG.name})与[源代码／输入哈希](../../outputs/diagnostics/{RUN}/freeze.json)。
3. 仅用信号时点分数与风格计算S0/S1/S2、约束名单、20组分层随机名单，封存[选股凭据](../../outputs/diagnostics/{RUN}/selection_complete.json)。
4. 冻结[分析脚本及主检验定义](../../outputs/diagnostics/{RUN}/analysis_registration.json)，再运行固定事件与独立连续账户。
5. A2主比较是E1、主区间、月初H10、主成本S1−S0及S2−S0；B1主比较是同条件的两相位差异中之差。三项Holm校正；E2、辅助期限、其他成本、长期区间与连续账户结果均为辅助。
6. B2曲线与净收益段采用固定名单，入场费一次、最终退出费一次；H5/H10/H20单独退出结果单列。曲线逐点区间不是同时置信带。
7. 双周对月度盈亏平衡重放的0至100买入bps范围、1:2买卖费比、10bps网格和12次二分步骤在配置中预先登记，没有根据收益扩大范围。
8. 换仓贡献分解在看到主结果后补充，仅为用户所要求的机制诊断，登记为[事后描述](../../outputs/diagnostics/{RUN}/rebalance_contribution_registration.json)，不改变主检验或任何交易参数。

## 执行合同的具体限制

{general}

## 独立裁决

A2、B1、B2分别回答信息增量、时间条件优势和收益路径，任何一项“不显著”不自动否定另一项。三项主族区间跨零，不等于已证明经济等价。数据缺失、随机对照覆盖不足及实际风险偏离均在报告中保留。

完整严格PIT和真实前瞻仍未完成；没有独立训练的强风格收益基线。正式指数增强B路径的历史权重与权益流水认证也不因本轮Q5研究而被补齐。
''')
 files=[p for p in DEST.rglob('*') if p.is_file()]
 sources=[EP/'src'/n for n in ['alpha_economics.py','alpha_economics_analyze.py','alpha_economics_validate.py','alpha_economics_report.py','alpha_rebalance_contribution.py','acquire_style_caps.py']]
 reports=[p for p in REPORT.iterdir() if p.is_file() and p.name!='manifest.json']
 save_json(REPORT/'manifest.json',dict(run=RUN,config_sha256=sha(CONFIG),validation_sha256=sha(DEST/'validation.json'),sources=[dict(path=str(p),sha256=sha(p)) for p in sources],outputs=[dict(path=str(p),sha256=sha(p)) for p in files],reports=[dict(path=str(p),sha256=sha(p)) for p in reports],tests='41 passed; one preexisting OSQP PendingDeprecationWarning',evidence='Historical-proxy post-selection exploration',forward='FORWARD_PENDING'))
 print('reports',REPORT,flush=True)

if __name__=='__main__':main()

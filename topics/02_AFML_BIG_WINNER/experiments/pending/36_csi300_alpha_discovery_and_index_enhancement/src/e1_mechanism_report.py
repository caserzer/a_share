"""Readable reports for executed historical mechanism experiment."""
import json,re
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from e1_mechanism import D,L,R,EP,OUT,RUN,END,sha,save_json,verify

def table(df,percent=()):
 d=df.copy()
 for c in percent:d[c]*=100
 return d.to_markdown(index=False,floatfmt='.4f')

def report(name,text):
 (R/(name+'.md')).write_text(text)
 html=markdown.markdown(text,extensions=['tables','fenced_code'])
 (R/(name+'.html')).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>EP36 机制实验</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#223}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:7px 12px;border:1px solid #ccd;text-align:left}th{background:#edf3f5}img{max-width:100%}a{color:#146887}</style>'+html+'</html>')

def link(name):return f'../../outputs/diagnostics/{RUN}/{name}'

def main():
 verify();verify('selection_complete');verify('evaluation_complete');verify('analysis_complete')
 validation=json.loads((D/'validation.json').read_text());assert validation['status']=='PASS'
 p=pd.read_csv(D/'primary_tests.csv');bridge=pd.read_csv(D/'state_wealth_bridge.csv');en=pd.read_csv(D/'state_enrichment.csv');metrics=pd.read_csv(D/'account_metrics.csv');coverage=pd.read_csv(D/'coverage.csv',parse_dates=['signal_date']);coverage=coverage[coverage.signal_date<=END];match=pd.read_csv(D/'matched_budget_coverage.csv',parse_dates=['signal_date']);placebo=pd.read_csv(D/'placebo_coverage.csv',parse_dates=['signal_date']);risk=pd.read_csv(D/'actual_daily_risk.csv',parse_dates=['date']);overlap=pd.read_csv(D/'selection_overlap.csv');cases=pd.read_csv(D/'case_examples_enriched.csv');groups=pd.read_csv(D/'q5_score_group_differences.csv',parse_dates=['signal_date']);groups=groups[groups.signal_date<=END]
 state_names={'strong_pullback':'中期强势且短期回撤','strong_no_pullback':'中期强势且短期未回撤','weak_pullback':'中期弱势且短期回撤','weak_no_pullback':'中期弱势且短期未回撤','UNKNOWN':'状态未知或不属于本轮样本','__FEES__':'交易费用','__CASH__':'现金机会收益'}
 bridge['状态']=bridge.state.map(state_names)
 pt=p[['test','n','mean','ci_low','ci_high','holm_p','verdict']].copy();pt['test']=pt.test.map({'P1':'P1 状态条件系数','P2':'P2 J减B净事件收益','P3':'P3 E1剩余条件系数'});pt.columns=['主检验','有效期数','均值pp','95%下界pp','95%上界pp','Holm p','裁决'];pt.iloc[:,2:5]*=100
 # Three compact static figures, labels intentionally ASCII with adjacent Chinese explanation.
 fig,ax=plt.subplots(figsize=(9,4));x=p['mean'].to_numpy()*100;lo=p.ci_low.to_numpy()*100;hi=p.ci_high.to_numpy()*100;ax.errorbar(x,np.arange(3),xerr=np.vstack([x-lo,hi-x]),fmt='o',capsize=5);ax.axvline(0,color='gray',ls='--');ax.set_yticks(np.arange(3),['P1: joint-state slope','P2: net J minus B','P3: E1 conditional slope']);ax.set_xlabel('Return percentage points (different estimands)');ax.set_title('Historical primary tests: ordinary 95% intervals, Holm p used for decisions');fig.tight_layout();fig.savefig(R/'primary_tests.png',dpi=160);plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,4));ax.bar(bridge.state,bridge.wealth_contribution,color=np.where(bridge.wealth_contribution>=0,'#43aa8b','#ef8354'));ax.tick_params(axis='x',rotation=25);ax.set_ylabel('Wealth-gap contribution per initial 100');ax.set_title('Original E1: descriptive state attribution including UNKNOWN and costs');fig.tight_layout();fig.savefig(R/'state_bridge.png',dpi=160);plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,4))
 for st in ['B','J','E1']:
  a=pd.read_csv(D/'accounts'/(st+'_main.csv'),parse_dates=['date']);a=a[a.date<=END];ax.plot(a.date,a.nav,label=st+' new constrained universe')
 original=pd.read_csv(OUT/'sensitivity/q5_rebalance_20261116/accounts/suspend_flat__E1__1m__main.csv',parse_dates=['date']);original=original[original.date<=END];ax.plot(original.date,original.nav,label='Original E1 (different portfolio)',ls='--',color='black');ax.legend();ax.set_title('Monthly net accounts: original E1 is reference, not same-sample comparator');ax.set_ylabel('NAV');fig.tight_layout();fig.savefig(R/'accounts.png',dpi=160);plt.close(fig)
 context='主历史区间为2021-01-08信号至2025-03-03，原E1为expanding Ridge。没有重训、修改原预测或调仓搜索。行业、市值首发版本和复权估值仍为Historical-proxy，历史已被多次查看。本轮全部历史结果为探索性证据，真实前瞻尚未运行。'
 mainmetrics=metrics[(metrics.scope=='primary')&(metrics.cost=='main')][['strategy','days','cagr','end_nav','annual_oneway_turnover','average_cash']]
 body=f'''# EP36 行业内回撤修复机制实验结果

**本轮没有确认“行业内中期强势股票的短期回撤修复”具有独立且可兑现的 Alpha，也没有确认 E1 在该状态与既有风格之外仍有稳定信息。三个主检验均为 INCONCLUSIVE。** 这不是证明市场不存在该机制，也不是证明原 E1 没有收益，而是这套预先固定的验证未提供足够支持。

{context}

## 三个主检验

{table(pt)}

P1为标准化共同状态J的条件收益系数，P3为标准化E1分数秩的剩余条件收益系数；二者不是账户年化。P2为每个月初同日H10净事件收益差，买10/sell20bps。P2覆盖50/50个月初事件，点估计约−0.00016pp，区间约[−0.2245,+0.2151]pp。没有用不显著证明等价。13周/3个月时间块、5000次Bootstrap，三项Holm校正。

![主检验](primary_tests.png)

## 为什么暂时不能解释原 E1

原E1有约42.63元/初始100元的累计相对财富差。按每日持仓在此前最近已知信号的状态分组，结果如下。它是对原账本的描述性分配，不是状态的独立回测。

{table(bridge[['状态','wealth_contribution']].rename(columns={'wealth_contribution':'财富差贡献元'}))}

强势回撤对应约8.12元；弱势回撤对应约16.95元，不能将这些数额直接解释为某种预测因子的效果。未知状态贡献约19.39元，且持仓状态会随新信号改变；这种归因不是按买入状态固定分组，也不是各组独立净收益。

本轮每行业至少10只有效股票的约束，平均只保留约{coverage.common.mean():.1f}只股票，主区间原Q5目标预算平均覆盖{coverage.q5_budget_coverage.mean():.1%}；实际每日已知状态持仓占股票资本平均{validation['original_capital_coverage_mean']:.1%}。原账户不能被这个缩小样本完全解释。

![原账本状态贡献](state_bridge.png)

## 简单规则没有交付可用的经济证据

B是趋势与回撤秩的平均，J是二者较小值；都不读取E1、不训练收益模型。新E1在同一样本和风险约束下选股，**不是原60只左右的E1月初账户**。新账户约40只、行业名额按新样本分配。

{table(mainmetrics,['cagr','average_cash'])}

表中cagr和average_cash以百分数展示，换手为年化单边倍数。原E1的4.84%净年化不能与新受约束E1的−6.42%直接作“模型损失”的因果比较：股票池、行业预算、持仓数、风格约束和路径都改变了。J相对B的连续账户年化点估计略高，也不能代替未通过的固定H10主检验。

![账户参考图](accounts.png)

## 对照覆盖和实施限制

严格逐股13风格匹配平均仅覆盖原Q5约{match.original_budget_coverage.mean():.1%}预算（扩展区间描述）；随机安慰剂成功{int(placebo.accepted.sum())}/{len(placebo)}次，仅{placebo.accepted.mean():.2%}。这些分支保留完整失败记录，裁决为PARTIAL_IDENTIFICATION，不能当作有效的全样本反证或认证。

9条连续账户均覆盖主区间1001交易日。扩展期B/J至2026-10-21，新受约束E1因2026-10-19持仓收盘估值未知，停在2026-10-16；三策略共同终点表采用2026-10-16。没有填价延续账户。

## 下一步裁决

本轮候选机制没有获得主检验支持，按方案停止本版本的阈值与窗口扩展。不因为“弱势回撤贡献更大”就立即改成另一个胜者规则；那是已看结果后的新假说，需要另立版本。E1仍有原始收益线索，但来源解释未闭合。

前瞻登记已生成，计划窗口2026-12至2029-11、24个月仅描述、36个月后待最后标签成熟统一检验。但本地封存数据截止2026-10-21，缺少经验证的最新数据和未来E1出分流程，因此状态为FORWARD_PENDING、FORWARD_BLOCKED_DATA_REFRESH及FORWARD_BLOCKED_MODEL；没有自动任务、实际前瞻信号或部署。

## 完整证据

- [模型解释与原账本](MODEL.md) · [条件收益与独立规则](MECHANISM.md) · [共同反弹与时间路径](TIMING.md) · [前瞻状态](FORWARD.md)
- [原方案](PROTOCOL.md) · [执行记录](EXECUTION.md)
- [主检验原表]({link('primary_tests.csv')}) · [全部辅助检验]({link('all_tests.csv')}) · [全部案例事件]({link('all_case_events.csv')})
- [验证记录]({link('validation.json')})：{validation['count']}项核验通过，51项测试通过，原输入/预测哈希未变。一次格式兼容修复留存旧版本，主结果核对一致。
'''
 report('REPORT',body)
 enr=en.groupby('state')[['pool_share','q5_share']].mean().reset_index();enr['state']=enr.state.map(state_names)
 differences=groups.drop(columns='signal_date').mean().rename('Q5_minus_nonQ5_mean_score').reset_index()
 report('MODEL',f'''# 原 E1 选股解释与账本桥接

想验证什么：E1是否偏好强势回撤状态，该状态是否解释原账户超额。

怎么比较：24个季度原模型与变换器逐行复放；每项beta乘变换后特征，78项固定归入5组。最大分数误差2.11×10⁻¹⁵。季度系数、训练均值及标准差完整保存，没有重训。市场共同项在同一截面不改变股票相对排序。

发现什么：有效样本内强势回撤占池子约24%，占原Q5已覆盖部分约28%；同时强势未回撤也有富集，因此不能把模型简化为单一回撤买入。

{table(enr,['pool_share','q5_share'])}

主区间Q5与未入选股票的分数组均值差：

{table(differences)}

区间位置和收益趋势组分数差较大；这是选股分数构成，不是收益贡献。特征共线性意味着不能据此宣布哪组创造Alpha。季度系数变化、分数组相关性和完整映射见链接。

为什么不能下结论：原股票资本仅约三分之二可归入本轮状态，未知部分仍贡献大量收益；原账本分组不能作为因果分解。每个交易日使用严格早于当天的最新周信号，包含换入、换出及持仓漂移。费用和现金独立归因，各组逐日相加回到原账本。

{table(bridge[['状态','wealth_contribution']])}

固定案例为最高5个、最低5个、其余固定随机10个。代码为权威键，名称是参考，不代表历史时点名称认证。

{table(cases[['case','instrument','name_reference','signal_date','state','wealth_contribution','u','v','raw_q5']])}

[78项映射]({link('feature_groups.csv')}) · [季度系数]({link('coefficients.csv')}) · [逐季复放]({link('model_replay.csv')}) · [分数组均值]({link('score_group_means.csv')}) · [分数组相关]({link('score_group_correlations.csv')}) · [逐月状态贡献]({link('state_month_contributions.csv')}) · [实际持仓资本覆盖]({link('original_capital_coverage.csv')}) · [全部案例事件]({link('all_case_events.csv')})。

逐股完整特征和标签表保存在private/{RUN}/stock_signal_detail.parquet，原始数据依仓库规则保留本地。
''')
 allstats=pd.read_csv(D/'all_tests.csv');ic=pd.read_csv(D/'rank_ic.csv',parse_dates=['exit_date']);ic=ic[(ic.horizon==10)&(ic.exit_date<=END)].groupby('score').agg(mean_rank_ic=('ic','mean'),dates=('ic','count')).reset_index()
 report('MECHANISM',f'''# 候选机制条件收益与经济验证

想验证什么：非重叠55日趋势和最近5日回撤的共同状态，是否超出各自主效应；E1是否在此之外还有信息。

怎么比较：J=min(u,v)，B=(u+v)/2。P1控制13项风格、行业以及u/v在0.25/0.5/0.75的固定折线；P3再加入J控制。H10原始开盘标签与旧封存标签完全一致；可执行事件另加交易状态与费用。风格和分数标准化在标签接入前完成，标签缺失不改变名单。

{table(pt)}

全部期限和扩展区间仅辅助：

{table(allstats[['scope','horizon','test','n','mean','ci_low','ci_high','p']],['mean','ci_low','ci_high'])}

H10原始排序的主区间描述：

{table(ic)}

经济规则的每期行业名额完全一致，目标13项数值风格差不超过0.25标准差。592次约束优化均成功。J与B名单重合率平均{overlap.J_B_overlap.mean():.1%}，并未完全退化为同一名单；J平均共同状态分数改善{overlap.J_score_gain.mean():.4f}。仍然没有主净增量支持。

{table(metrics[metrics.scope=='primary'][['strategy','cost','cagr','annual_oneway_turnover','fees']],['cagr'])}

为什么不能下结论：普通95%区间不是同时区间；三个主裁决使用Holm p。连续账户相对B的正点估计、辅助期限或扩展期的正系数，都不能替换主检验失败。未来是否可用尚无数据。

[每日期条件回归]({link('conditional.csv')}) · [逐月P2配对]({link('primary_p2_months.csv')}) · [逐年与留一年影响]({link('influence.csv')}) · [连续账户逐年逐月]({link('account_periods.csv')}) · [完整账户指标]({link('account_metrics.csv')}) · [共同扩展终点]({link('common_extended_accounts.csv')}) · [目标重合]({link('selection_overlap.csv')})。
''')
 timing=pd.read_csv(D/'timing_comparisons.csv',parse_dates=['exit_date']);timing=timing[timing.exit_date<=END];ts=timing.groupby('strategy')[['immediate_minus_delayed','fresh_minus_delayed']].agg(['count','mean']);ts.columns=['_'.join(c) for c in ts.columns];ts=ts.reset_index()
 paths=pd.read_csv(D/'marginal_paths.csv',parse_dates=['signal_date','exit_date']);paths=paths[(paths.exit_date<=END)&paths.net20.notna()];sch=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date']);paths=paths.merge(sch,on='signal_date');paths=paths[paths.phase==1];wp=paths.pivot(index='signal_date',columns='strategy',values=['first5','next5','last10']);mr=[]
 for col in ['first5','next5','last10']:
  delta=wp[(col,'J')]-wp[(col,'B')];mr.append(dict(segment=col,n=int(delta.notna().sum()),J_minus_B=delta.mean()))
 rr=risk[(risk.date<=END)&(risk.cost=='main')].copy();rr['within_bound']=(rr.max_style_gap<=.25+1e-7)&rr.complete;rs=rr.groupby('strategy').agg(mean_gap=('max_style_gap','mean'),maximum_gap=('max_style_gap','max'),unknown_weight=('unknown_weight','mean'),within_bound_fraction=('within_bound','mean')).reset_index()
 report('TIMING',f'''# 共同反弹对照与交易时间路径

想验证什么：收益是否来自普遍反弹、共同风险或日期与名单刷新。

怎么比较：市场状态仅用信号前20日总收益和波动，波动阈值取此前252日中位数；未知历史保持UNKNOWN。匹配为同行业13风格每项0.5标准差以内，允许控制股重复，不能保证因果可比。

发现什么：严格股票匹配预算覆盖约{match.original_budget_coverage.mean():.1%}，安慰剂通过{int(placebo.accepted.sum())}/{len(placebo)}次。匹配和随机分支均为PARTIAL_IDENTIFICATION，不能从其很小的成功子样本判定M2成立或排除M2。

固定H10的日期比较，均为新规则账户名单，不是原E1名单。单位为pp，数量为各差值已知配对数：

{table(ts,[c for c in ts if c.endswith('_mean')])}

立即与延迟差异同时包含信号老化和日期；同日新名单与旧名单差异定位刷新效应。这里仅作描述，不从负点估计宣布“第二周更优”，不选择新相位。

月初同一H20路径、J减B的阶段贡献，单位pp；路径包括一次入场费及末段一次退出费，各段加总已核对：

{table(pd.DataFrame(mr),['J_minus_B'])}

目标匹配并不等于成交后风险中性。下表是每日持仓按最近调仓信号的冻结风格衡量，未知旧仓权重单列；不是每日更新风险模型：

{table(rs,['unknown_weight','within_bound_fraction'])}

为何不能下结论：主净增量未确认、随机和逐股对照覆盖不足；时间路径只能描述当前规则，并未建立原E1月初优势的完整解释。保持原相位，不据此调参。

[匹配失败及结果]({link('matched_outcomes.csv')}) · [匹配预算覆盖]({link('matched_budget_coverage.csv')}) · [随机通过记录]({link('placebo_coverage.csv')}) · [各随机副本比较]({link('placebo_comparisons.csv')}) · [预先市场状态]({link('market_regimes.csv')}) · [状态分层结果]({link('regime_events.csv')}) · [完整日期配对]({link('timing_comparisons.csv')}) · [阶段路径]({link('marginal_paths.csv')}) · [每日实际风险]({link('actual_daily_risk.csv')})。
''')
 fwd=json.loads((D/'forward_registration.json').read_text())
 report('FORWARD',f'''# 前瞻登记与未完成条件

当前不是正在运行的前瞻验证。历史实验已执行，真实前瞻仍FORWARD_PENDING；最新输入刷新为FORWARD_BLOCKED_DATA_REFRESH，E1未来出分为FORWARD_BLOCKED_MODEL。没有安装定时任务，也没有把历史末端之后已经发生的收益冒充盲测。

登记计划为2026-12-01至2029-11-30的36个完整自然月；候选首个完整周信号为2026-12-04，必须在实际可得数据、完整交易周和事前时间戳满足后才有效。2028-11月底仅做描述性审阅；2029-11月底且最后H20标签成熟后统一进行三项正式检验。计划日期不是已经产生信号的事实。

若首次信号未能及时产生，记漏报；不能回填。开始日期发生变化须另留版本，不覆盖本登记。36个月内不足36个有效月度配对时P2只做部分样本估计；不自动延长以补齐显著性。

根据本轮P2时间块均值方差粗估，80%功效和保守三项校正下，24个月最小可检出净事件差约{fwd['power'][0]['approximate_min_detectable_event_return']*100:.3f}pp，36个月约{fwd['power'][1]['approximate_min_detectable_event_return']*100:.3f}pp。该近似假定依赖结构和方差稳定，说明小幅增量可能仍需很长观察，不保证实际功效。

未来记录必须包括信号时点、输入接收时间、模型/规则版本、原始数据哈希、名单、交易门槛、执行模拟、未成交预算和每个期限的成熟标签。B/J可以不训练模型生成；E1仍需要另行验证原有更新流程，本轮没有新增训练。

[机器可读前瞻登记]({link('forward_registration.json')})。本轮历史裁决为证据不足，不应把前瞻登记理解为策略已获上线认可。
''')
 report('EXECUTION',f'''# 实验执行记录与验收

本轮用户授权为“执行方案”。原方案和设计配置保持原样，执行状态以本报告为准。

1. G0/G1：核对数据、原季度模型、执行引擎及标签，冻结输入与代码；78项特征分组固定。既有结果已见，新机制结果当时未算。
2. G2：不读取标签，生成状态、样本排除、592个约束解、匹配和14000个随机尝试记录；原24季度分数复放一致，封存名单及哈希。
3. G3：封存统计脚本后计算标签、固定事件与9条独立连续账户。原标签与本轮毛收益逐行核对；事件净收益独立处理可交易性。
4. G4：主族三项均INCONCLUSIVE；原账本状态贡献逐日对齐。新E1扩展期估值未知按原规则停账，不补值。
5. G5：形成前瞻登记和功效限制，真实未来观察、数据刷新与模型出分仍未完成；没有部署和自动调度。

分析首次运行在市场状态字符串格式化处遇到NumPy兼容错误。原脚本、登记与已生成结果保存在attempt1；修复版本改用np.char.add，实际风险估值使用与账户相同的停牌标记。修复时已见主结果，这一点已登记。没有改分数、阈值、样本、标签、主统计或成本；三个主检验的点估计、区间及p值与修复前完全一致。

[首次分析登记]({link('analysis_registration.json')}) · [修复版本登记]({link('analysis_registration_v2.json')}) · [初始封存]({link('freeze.json')}) · [无标签名单封存]({link('selection_complete.json')}) · [收益计算封存]({link('evaluation_complete.json')}) · [分析完成]({link('analysis_complete.json')})。

{validation['count']}项验证包括全目标风险与行业名额、原标签一致性、原分数复放、仅历史截断的窗口核对、未清算事件不生成净收益、账本逐日加总及修复前后主结果一致。51项测试通过，只有既有OSQP未来默认值弃用提示。验证范围是本实现的口径一致性，不等于严格PIT或因果认证。

可复现入口依次为src/e1_mechanism.py的freeze/prepare/evaluate，src/e1_mechanism_analyze_v2.py的analyze，src/e1_mechanism_validate.py和src/e1_mechanism_report.py。已有freeze/selection/evaluation完成凭据时拒绝重复覆盖；重新运行须使用新目录与版本。旧源数据、预测和报告未改，未提交、推送、部署或发送消息。
''')
 files=list(R.glob('*.md'))+list(R.glob('*.html'))+list(R.glob('*.png'))
 errors=[]
 for path in R.glob('*.md'):
  for url in re.findall(r'\]\(([^)]+)\)',path.read_text()):
   if '://' not in url and not (path.parent/url).exists():errors.append((path.name,url))
 assert not errors,errors
 save_json(R/'execution_manifest.json',dict(status='HISTORICAL_EXECUTION_COMPLETE_FORWARD_PENDING',tests=51,validation_checks=validation['count'],files=[dict(path=str(p),sha256=sha(p)) for p in files],source_inputs_unchanged=True,uncompleted=['strict PIT','future data refresh','future E1 model generation','36 month prospective outcomes','full-coverage stock matching and placebo inference'],reports_visual_review='pending'))
 print('reports written',len(files),flush=True)
if __name__=='__main__':main()

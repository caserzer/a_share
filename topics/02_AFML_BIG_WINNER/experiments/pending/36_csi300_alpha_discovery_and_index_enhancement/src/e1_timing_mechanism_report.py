"""Readable evidence reports, plots and independent arithmetic audits."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from e1_timing_mechanism_evaluate_v2 import *
LABEL={'UP_DOWN':'中期涨／短期跌','UP_UP':'中期涨／短期涨','DOWN_DOWN':'中期跌／短期跌','DOWN_UP':'中期跌／短期涨','ZERO':'精确零','UNKNOWN':'价格状态未知','__CASH__':'现金机会成本','__FEES__':'费用'}
def read(name):return pd.read_csv(D/(name+'.csv'))
def table(f):return f.to_markdown(index=False,floatfmt='.4f')
def write(name,text):(R/name).write_text(text,encoding='utf-8')
def interval(row,scale=100):return f"{row['mean']*scale:+.3f} [{row['ci_low']*scale:+.3f}, {row['ci_high']*scale:+.3f}]"
def link(name):return f'[{name}.csv](../../outputs/diagnostics/{RUN}/evaluation_v2/{name}.csv)'

def build():
 verify(True);R.mkdir(exist_ok=True)
 original=read('01_original_state');budget=read('target_budget');gap=read('continuous_gap_state');summary=read('event_summary');cov=read('05_coverage');path=read('path_segments_v2_summary');res=read('04_residual_association');checks=[]
 def audit(name,ok):assert bool(ok),name;checks.append(dict(check=name,passed=True))
 ev=read('events');st=read('event_states');keys=['signal_date','cost','delay','clock','horizon']
 audit('one_row_per_planned_event',not ev.duplicated(keys).any())
 for metric in ['mark','net']:
  totals=st.groupby(keys)[metric].sum(min_count=1).rename('component').reset_index();joined=totals.merge(ev[keys+[metric]],on=keys,validate='one_to_one');known=joined[metric].notna();audit('state_'+metric+'_closure',np.allclose(joined.loc[known,metric],joined.loc[known,'component'],atol=1e-10))
 audit('original_cash_pnl_closure',np.isclose(original.absolute_cash_pnl_per100.sum(),20.6737869,atol=1e-5))
 audit('absolute_linked_equals_cash_pnl_total',np.isclose(original.absolute_linked_contribution.sum(),original.absolute_cash_pnl_per100.sum(),atol=1e-9))
 audit('budget_complete',np.isclose(budget.mean_target_budget.sum(),1))
 audit('primary_four_state_holm',len(read('02_state_timing').query("clock=='equal_horizon' and horizon==10").holm_p.dropna())==4)
 audit('zero_all13_support_not_zero_alpha',cov.loc[cov.tier.eq('all13'),'supported_budget'].iloc[0]==0 and read('residual_excess_summary').query("tier=='all13'")['mean'].isna().all())
 audit('correct_january_phase2',pd.read_csv(D/'schedule.csv').iloc[0].phase2_date=='2021-01-18')
 expected=gap.wealth_gap.sum();audit('bridge_terminal',np.isclose(path.loc[path.component.eq('total'),'linked_wealth'].iloc[0],expected,atol=1e-8))
 for name in ['validation','path_validation','path_segments_v2_validation']:
  r=json.loads((D/(name+'.json')).read_text());audit(name,r['status']=='PASS');checks.extend(r['checks'])
 save_json(D/'final_validation.json',dict(status='PASS',checks=checks,total_checks=len(checks)))

 t=original.merge(budget[['state','mean_target_budget']],on='state',how='left').merge(gap,on='state',how='left');t['组别']=t.state.map(LABEL);t['目标资金占比%']=t.mean_target_budget*100
 main=t[['组别','目标资金占比%','absolute_cash_pnl_per100','wealth_contribution','wealth_gap']].rename(columns={'absolute_cash_pnl_per100':'绝对现金损益','wealth_contribution':'相对指数终值贡献','wealth_gap':'原账户相对延迟终值贡献'})
 event=summary.query("cost=='main' and horizon==10 and delay=='phase2' and metric=='net'")
 equal=event[event.clock.eq('equal_horizon')].iloc[0];common=event[event.clock.eq('common_exit')].iloc[0]
 pv=path.set_index('component');rr=res.query("state=='ALL' and metric=='conditional_rank_ic'").set_index('outcome')
 memo=f'''# 原 E1 残差与日期敏感度：完整执行结果

执行日期：2026-11-17。主对象是原 E1 月初 Q5，原持仓全量保留。历史区间：2021-01-08 信号至2025-03-03估值，1001交易日、50个月度决策。主成本买10/卖20bps。全部为已有历史上的机制诊断；历史行业、价格复权、停牌估值等仍是 Historical-proxy。

## 本轮把解释推进到了哪里

**原 E1 的已实现收益更偏向弱势股票的反弹，而非单纯“强趋势中的回调”。日期差主要发生在月初立即换入新名单、延迟账户仍持有旧名单的窗口。分数残差目前仍不能独立解释这些损益。**

这里的“反弹”描述已实现价格路径，并不是已证明的风险补偿或投资者行为因果。四组是信号日前价格状态，不是把 Ridge 的系数机械拆成四个可独立交易的 Alpha。

### 主表1：损益究竟来自哪组

下表后三列单位均为“每初始100元的元数”；资金占比是50次目标权重的均值。绝对现金损益逐笔计算；相对贡献采用统一对数链接，不能把两种列逐行相减当成基准收益。

{table(main)}

“中期跌／短期跌”只有19.69%的目标预算，却贡献相对指数终值差28.45元，以及相对延迟账户终值差16.85元。它是本轮最大的来源；“中期涨／短期跌”也有正贡献，但不是唯一主角。“中期涨／短期涨”配置最多，绝对损益为负。费用单列，未任意摊入四组。

原账户绝对获利20.67元，相对指数终值差42.63元，相对延迟账户终值差31.73元。三个数字对应不同基准。不能把其中一个叫作“残差 Alpha 收益”。

### 主表2：固定期限是否也显示巨大日期优势

主比较：同一原名单和权重，在真实第一、第二周信号后的开盘分别建仓，各持有10个交易日，实际退出受限则净收益NA。

- H10等期限净收益差：**{interval(equal)}个百分点**，{int(equal['n'])}/50个月有效。
- 原入场锚定H10共同退出日：**{interval(common)}个百分点**，{int(common['n'])}/50个月有效。
- 四状态的主检验均未通过Holm校正。H5/H10/H20共同有效月份为42，换到该共同样本也未确认等期限日期优势。

因此，“连续账户差很多”不能直接翻译成“原名单的10日预测能力过一周就消失”。固定期限比较仍有较大不确定性，不显著不等于日期不重要。

### 主表3：连续账户的日期差被拆到了哪里

每个月复制原账户A和延迟账户B的真实开盘前持仓/现金，分别执行A/B两套既有日历，形成四个可融资账户。两种分解顺序取平均；50个月的归因严格回到31.73元终值差。

{table(path[path.component.isin(['early_stock','early_fee','late_stock','late_fee','inherited','total'])][['component','linked_wealth']].assign(component=lambda f:f.component.map({'early_stock':'原执行日至延迟执行日前：股票损益','early_fee':'该早期窗口：费用入账差','late_stock':'延迟执行日后：股票损益','late_fee':'延迟执行日后：费用入账差','inherited':'跨月继承的持仓构成差','total':'合计'})))}

单列费用以后，早期股票损益贡献{pv.loc['early_stock','linked_wealth']:.3f}元，延迟执行后股票损益仅{pv.loc['late_stock','linked_wealth']:.3f}元。也就是说，几乎全部股票收益差出现在两次执行日之间，而非之后继续扩大。

整体当月执行效应为{pv.loc['timing','linked_wealth']:.3f}元，跨月继承构成效应为{pv.loc['inherited','linked_wealth']:.3f}元。**费用发生的日期不同，会把“早段/晚段”的净收益拆分扭曲；必须同时看股票损益与费用。** 此处“当月执行”包含新旧持仓、现金、交易门槛以及实际市场路径，仍不等于某种纯日历异常。

从原账户相同期初状态做“原月初完整换仓 vs 暂不换仓”独立事件，也显示点估计主要来自新开仓。各动作区间见详细报告；不能把买入点估计占比当成稳定因果占比。

### 主表4：分数残差能否解释收益与日期差

全可评分股票、不要求行业至少10只，对13风格和行业剥离后，再控制固定趋势与REV：

| 条件关联 | 月均相关与95%区间 |
|---|---|
| 残差与立即入场H10净收益 | {interval(rr.loc['immediate'],1)} |
| 残差与立即减延迟H10净收益 | {interval(rr.loc['date_gap'],1)} |

均未形成稳定正向解释。原持仓内部、四状态内部、同行业收益差也做了核对，少量辅助结果不能升级为主结论。未知和无支持部分均保留。

### 主表5：尚未解释的覆盖缺口

{table(cov.rename(columns={'tier':'对照层级','planned_budget':'原预算','recorded_budget':'行业已知预算','supported_budget':'匹配支持预算','residual_scored_budget':'残差可评分预算'}))}

同行业支持约98.44%预算；加上固定短期/中期价格匹配只剩15.18%；逐项全13风格严格匹配为0。**不能据此宣布“剩余收益已经被风格完全解释”，也不能以全13匹配无结果证明它有独立 Alpha。** 后两层仅给部分识别，未扩大容差。

## 如何重新校准解释

1. 把原来泛称的“复合动量和反转”收窄为可核查的描述：弱势状态反弹是主贡献，强势回调是另一个贡献，但逐年有变号，不能称每年稳定。
2. 日期问题优先解释新旧名单在月初窗口的相对价格路径。固定名单等H10几乎没有同等强度的证据，跨月初始构成也不是主要差异来源。
3. 分数残差的独立经济解释仍未完成。可复核的描述性归因已经闭合；对日历、市场反弹和真实独立信息的区分仍有限。既有“同一较晚日期旧名单 vs 新名单”也未确认稳定改善。
4. 本轮没有重新训练、改模型、挑日期或输出新策略。下一轮若继续，应围绕已经定位的月初新旧持仓窗口做机制核验，而不是把日期敏感度当作调参机会。

## 详细证据与复现

- [账本、逐年逐月、行业和股票](01_LEDGER.md)
- [固定名单、等期限、共同退出及分段](02_TIMING.md)
- [交易动作、账户路径与费用日期](03_PATH.md)
- [残差、同行业与严格匹配](04_RESIDUAL.md)
- [覆盖、修订记录与验证边界](05_AUDIT.md)
- [事前协议](PROTOCOL.md)

![四状态损益与固定H10日期差](mechanism.png)

校验：{len(checks)}项通过，另有5个独立单元测试。最终结果位于evaluation_v2；首轮初始化日历结果及修订前代码全部保留。结论不会因账本闭合自动成为因果识别。
'''
 write('REPORT.md',memo)
 yr=read('original_year_state').pivot(index='year',columns='state',values='wealth_contribution').fillna(0).rename(columns=LABEL).reset_index()
 parts=[]
 for name,key in [('original_month_state','month'),('original_industry_state','industry'),('original_stock_state','instrument')]:
  f=read(name);parts.append('### 中期跌／短期跌组：'+key+'的正贡献前六\n\n'+table(f[f.state.eq('DOWN_DOWN')].nlargest(6,'wealth_contribution')[[key,'wealth_contribution']])+'\n\n完整表：'+link(name))
 write('01_LEDGER.md',f'''# 原账户损益来源

想验证：到底哪些资金在赚钱，是否只是配得多。

中期是不重叠的55交易日收益 close[t-5]/close[t-60]-1，短期是5交易日收益。状态在原月度信号日固定，当月旧持仓也按当前可知状态分类；私有明细保留原实际买入日和实际加减仓类别。

{table(main)}

绝对现金损益不分摊费用，四股票组因此是股票毛损益，完整账户净损益包含费用行。每组持仓天数、资本天数、单位资本日收益在{link('01_original_state')}；单位资本日收益是描述统计，不能拼成子策略净值。原全持仓无C池限制，未知未填零。

## 逐年归因

{table(yr)}

2025仅截至3月3日。中期跌／短期跌在2021、2022、2024贡献较大，在2023与2025部分区间为负；中期涨／短期跌2022年反而拖累。不能把全期正收益称作每年稳定。

{chr(10).join(parts)}

## 行业相对状态复核

从各股票信号日收益减去同行业可评分股票中位数后重分组，结果如下。中位数等值产生的ZERO不是缺失，也没有行业至少10只的筛选。

{table(read('industry_relative_state').assign(relative_state=lambda f:f.relative_state.map(LABEL)))}

行业内相对弱势的贡献仍存在，支持继续观察个股路径；这只是描述性归因，不等于严格风险匹配后的 Alpha。
''')
 z=read('02_state_timing').query("clock=='equal_horizon' and horizon==10");paired=read('paired_state_means').query("clock=='equal_horizon' and horizon==10")
 z=z.merge(paired[['state','immediate_paired_mean','delayed_paired_mean']],on='state');z['组别']=z.state.map(LABEL)
 display=z[['组别','n','immediate_paired_mean','delayed_paired_mean','mean','ci_low','ci_high','holm_p']].copy()
 for col in ['immediate_paired_mean','delayed_paired_mean','mean','ci_low','ci_high']:display[col]*=100
 write('02_TIMING.md',f'''# 固定名单的日期敏感度

想验证：同一批股票是否仅因晚买一周就失去固定期限收益。

50个月原名单与权重冻结，阶段标签不随延迟日期重算。延迟执行只用当时的成员和交易门槛，不重新归一化受阻预算。主成本10/20bps；H10主，H5/H20辅助；+1/+3/+5交易日作为固定辅助，不择优。

## 等H10四状态主表

下表收益列单位百分点，按原总账户资金计算，并非该组预算归一化收益。立即与延迟均用同一46个月有效配对样本。其余4个月不是零收益。

{table(display)}

所有主四组Holm校正p=1。最大正贡献组中期跌／短期跌的H10等期限日期差接近零，不能说它一周后就失效。

## 全部期限与共同样本

{table(summary.query("cost=='main' and delay=='phase2' and metric=='net'")[['clock','horizon','n','mean','ci_low','ci_high']])}

以上收益单位小数。H5共同退出日大多早于/等于延迟入场，只有4个月，不能作普遍期限结论。共同H5/H10/H20等期限样本：

{table(read('joint_horizon_summary')[['horizon','n','mean','ci_low','ci_high']])}

## 分段与实际交易限制

共同退出的标记收益差严格等于：立即入场至延迟日的早期损益 + 共同持有段的头寸差损益 + 延迟账户的入场费用。这里只是标记收益分解，未冒充可清仓净收益。

{link('segment_state_summary')}、{link('event_paths')}、{link('event_coverage')}。净收益要求冻结整组合能退出，任何剩余持仓不强制假卖；未交易预算保留现金。所有期限同样保留未成熟端点NA。

原名单事件前5、5—10、10—20阶段的共同样本标记增量见{link('marginal_marked_segments')}。它们未扣风格基准，不能单独定义独立信息寿命；同日期匹配支持缺口见残差报告。

## 日历与信号年龄

旧连续账户已有A=月初旧名单立即执行4.8446%、B=旧名单延迟-2.9053%、C=较晚日期新名单-2.3602%年化；B−C年均日收益差-0.5304pp，区间[-7.0821,+5.6991]pp。该较晚同日起点对照未确认“换成新信号”稳定修复。旧账本1月共同初始化，新的独立事件1月用真实第二信号2021-01-15后的2021-01-18开盘。

年龄与实际市场日历仍未获得独立随机变化，不能把差异归因到月初资金流等具体经济原因。所有H10之外结果均为辅助。
''')
 # Action CIs must be recomputed on summed monthly components, not sum subgroup CIs.
 actions=read('actions');actions['signal_date']=pd.to_datetime(actions.signal_date);grid=pd.DatetimeIndex(pd.read_csv(D/'schedule.csv').signal_date);ar=[]
 for window,h in actions[actions.reason.eq('OK')].groupby('window'):
  for cat,k in [('all',h)]+list(h.groupby('category')):
   ar.append(dict(window=window,category=cat,**stats(k.groupby('signal_date').increment.sum().reindex(grid))))
 ar=pd.DataFrame(ar);dump(ar,'action_total_summary')
 write('03_PATH.md',f'''# 交易动作与连续账户路径

想验证：日期差是新名单错过收益、旧持仓多留亏损，还是从以前月份继承的账户差异。

## 原账户相同起点动作

每月从原账户真实前收盘单位和现金开始，在同一开盘执行原目标。使用完整换仓的确切成交量，形成不交易→完全退出→减仓→加仓→新开仓链；另验不同卖出/买入组顺序，均无负现金，终点一致。不能把这个固定数量分摊当成重新优化后的独立买入策略。

{table(ar[ar.window.eq('phase2')][['category','n','mean','ci_low','ci_high','p']])}

收益单位小数；实际第二相位开盘为终点，未强制清仓，是持仓标记收益。新开仓点估计约+0.350pp、加仓+0.021pp、完全退出+0.002pp、减仓+0.008pp；区间如上，不称97%稳定来自买入。完整状态交叉表{link('03_actions_state')}。

## 连续账户2×2桥接

每月区间从第一相位执行开盘前到下月第一相位执行开盘前，最后到2025-03-03收盘。A/B各自起点均归一化为同样1元，执行既有A/B目标日历。AA和BB逐月精确重现实际账户。按照两种分解顺序平均分配对数收益差，再统一链接到每初始100元的终值差。

{table(read('path_bridge_summary')[['component','linked_wealth','mean','ci_low','ci_high']])}

这是固定目标、固定日期下的模拟干预分解，不能推出经济因果。“继承差很小”仅指每月初归一化持仓构成差；此前累积资本和月内收益复利已在总账和链接中计入，不能说复利不存在。

## 必须分开费用的发生日期

{table(path[['component','linked_wealth','mean','ci_low','ci_high']])}

早期界线是延迟账户实际执行开盘前。A费用先发生、B费用后发生；若只看早晚净收益，会把同一批换仓成本的错时入账误判为晚段Alpha。early_stock/late_stock才是对应分段的股票损益归因，fee行单列。

区间表的mean/CI是月均对数差，不是终值归因的置信区间。linked_wealth为历史账本确定性归因。

不同链接分段会改变四组分摊的小数值，因此逐日主账本和月度开盘桥接各自闭合、不可逐行混加；全账户31.7254元一致。跨状态完整表{link('path_bridge_state')}，逐月{link('path_segments_v2_months')}。
''')
 write('04_RESIDUAL.md',f'''# 残差是否解释净收益和日期差

想验证：剥离已知风格后的分数高低，能否解释同日起点风险相近股票的净损益，以及日期差。

分数残差是截面E1对13风格+行业的线性投影余项；收益残差是实际成本后个股收益减冻结同行对照收益，两者不是一回事。没有行业至少10只的筛选，没有用残差重新选一套替代E1。

## 全可评分股票

{table(res[['state','outcome','metric','n','mean','ci_low','ci_high']])}

所有个股收益都要求当日可买、终点可卖、窗口估值完整；不把这些统计相关冒充组合净收益。conditional_rank_ic进一步控制信号日非重叠趋势与1日/5日REV。

## 同行对照支持

{table(cov)}

控制层依次是同行业非原Q5、再短/中期价格各在0.25行业SD以内、再全部13风格逐项在0.25行业SD以内。未改门槛，行业未知不配对，全13零支持不是收益零。同行可被多个原持仓复用，不能把这些条件均值当成保持原持仓数的独立可交易组合。

匹配在未来收益评估前封存；实际净收益比较要求所有冻结同行都可观测，失败不事后删掉不方便的同行。分状态结果：{link('residual_excess_summary')}。原持仓内部的残差—净超额及残差—日期差关联：{link('selected_residual_association')}。

一个辅助结果是中期涨／短期跌组内，残差与行业相对日期差的条件相关为负，未校正p约0.019；这既不是事前主检验，也不是正向独立Alpha，不能挑出来当主发现。价格匹配层有效样本更少；无足够股票的相关为NA。

原账本残差不可评分持仓没有丢弃，见{link('ledger_residual_coverage')}。信号目标预算约95.06%可评分，剩余约4.94%保留为未识别。残差预测价值尚未解释清楚，不能以统计不显著宣布其不存在。
''')
 write('05_AUDIT.md',f'''# 覆盖、修订与验证

主结论使用 evaluation_v2。原始首轮输出不覆盖。

1. 原旧phase2日历在2021年1月以第一信号共同初始化。独立事件需要真实第二周信号，因此v2把2021-01-11改为2021-01-18；连续账户仍精确保持旧历史定义。amendment.json记录源文件和修订日历哈希。
2. 常量结果的条件相关必须NA，防止浮点残差被误当相关；该数值校验并入v2。
3. 连续路径首版遇到numpy字符串拼接错误，在生成结果前失败；保留原源码，v2只修拼接。随后增加早晚分段与单列费用，事先封存各分析源码并标记已经看过前一步结果；不声称这些扩展是历史未见确认检验。
4. 固定事件H10净收益：立即47/50有效，延迟48/50有效，共同46/50；失败为退出受阻。等H5/H10/H20共同42个月。共同退出H5多在延迟入场前，只有4个月，区间NA。
5. 价格状态未知、精确零、无匹配、残差不可评分均单列。全13严格匹配零支持；行业+价格匹配约15.18%预算，仍是部分识别。
6. 日历/年龄/市场反弹没有被随机分离；归因能够回答“哪些头寸、哪些日子贡献”，不能单凭历史收益回答资金流或行为原因。

## 验证

最终审计{len(checks)}项PASS，覆盖原账户净值、股票/费用损益、现金、全体状态加总、事件状态分解、成交门槛、无负现金、完整计划行数、原动作重放、连续账户AA/BB重放、桥接终值闭合和输入哈希。

独立单元测试5项：四组/缺失/零边界、非重叠趋势定义、动作链融资、早/共同段含费恒等式、对数链接终值闭合。未新增训练或更改预测。

复现顺序：e1_timing_mechanism.py freeze/prepare/ledger；修订回执后e1_timing_mechanism_evaluate_v2.py events/actions/residuals/analyze；supplement_v2.py supplement；path_bridge_v2.py bridge；path_segments_v2.py bridge；本报告脚本。已有freeze/selection不能重新冻结，需新run目录，不能覆盖原结果。

输出索引：{link('01_original_state')}、{link('02_state_timing')}、{link('03_actions_state')}、{link('04_residual_association')}、{link('05_coverage')}；所有明细在同目录及private/{RUN}。原始状态/同行成员/目标selection.json封存，final_validation.json与delivery.json分别存验证和交付哈希。
''')
 from matplotlib import font_manager
 font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc')
 plt.rcParams['font.family']=font_manager.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc').get_name();plt.rcParams['axes.unicode_minus']=False
 fig,axs=plt.subplots(1,2,figsize=(13,5));order=['DOWN_DOWN','UP_DOWN','DOWN_UP','UP_UP'];xs=np.arange(4);a=original.set_index('state').loc[order];b=gap.set_index('state').loc[order]
 axs[0].bar(xs-.18,a.wealth_contribution,.36,label='相对指数终值贡献');axs[0].bar(xs+.18,b.wealth_gap,.36,label='原账户减延迟终值贡献');axs[0].set_xticks(xs,[LABEL[x] for x in order],rotation=20);axs[0].axhline(0,color='gray',lw=.7);axs[0].set_ylabel('元／初始100元');axs[0].legend();axs[0].set_title('连续账户：已实现贡献')
 a=z.set_index('state').loc[order];axs[1].errorbar(xs,a['mean']*100,yerr=np.array([a['mean']-a.ci_low,a.ci_high-a['mean']])*100,fmt='o',capsize=4);axs[1].axhline(0,color='gray',lw=.7);axs[1].set_xticks(xs,[LABEL[x] for x in order],rotation=20);axs[1].set_ylabel('每事件原总资金收益差／百分点');axs[1].set_title('等H10日期差：46个月配对、95%区间')
 fig.suptitle('收益来源已定位；固定期限的日期优势尚未确认');fig.tight_layout();fig.savefig(R/'mechanism.png',dpi=160);plt.close(fig)
 files=[p for p in D.iterdir() if p.is_file() and p.name!='delivery.json']+[p for p in R.iterdir() if p.is_file()]+[p for p in L.iterdir() if p.is_file()]+[Path(__file__),EP/'tests/test_e1_timing_mechanism.py',EP/'README.md',EP/'RUN_STATUS.md']
 save_json(D/'delivery.json',dict(created_at=datetime.now(timezone.utc).isoformat(),status='PASS',files=[dict(path=str(p),sha256=sha(p)) for p in files]))
 print('report written',len(checks),'checks',flush=True)

if __name__=='__main__':build()

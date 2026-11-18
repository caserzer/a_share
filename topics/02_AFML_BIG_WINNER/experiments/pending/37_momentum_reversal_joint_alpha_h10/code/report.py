"""Independently readable Chinese reports and full result links."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from core import *
from analyze import scopes

REPORT=OUT/'reports'

def table(df,percent=(),digits=4):
    f=df.copy()
    for c in percent:
        if c in f:f[c]=f[c]*100
    for c in f.select_dtypes(include='number'):
        if not pd.api.types.is_integer_dtype(f[c]):f[c]=f[c].round(digits)
    f=f.astype(object).where(pd.notna(f),'NA')
    return f.to_markdown(index=False,missingval='NA',floatfmt=f'.{digits}f')

def write(name,title,body):
    text='# '+title+'\n\n'+body.strip()+'\n'
    (REPORT/(name+'.md')).write_text(text)
    content=markdown.markdown(text,extensions=['tables','fenced_code','toc'])
    html='<!doctype html><html lang="zh"><meta charset="utf-8"><title>'+title+'</title><style>body{max-width:1120px;margin:36px auto;padding:0 24px;font:16px/1.7 system-ui,sans-serif;color:#17212c}table{border-collapse:collapse;display:block;overflow:auto;font-size:13px}td,th{border:1px solid #d8dfe8;padding:7px 10px;text-align:right}th{background:#edf3fa}td:first-child,th:first-child{text-align:left}img{max-width:100%}a{color:#195ea8}pre{overflow:auto;background:#f4f6f8;padding:16px}h1,h2,h3{line-height:1.35}</style>'+content+'</html>'
    (REPORT/(name+'.html')).write_text(html)

def run():
    REPORT.mkdir(exist_ok=True);fig=REPORT/'figures';fig.mkdir(exist_ok=True)
    tests=pd.read_csv(OUT/'primary_tests.csv');ics=pd.read_csv(OUT/'rank_ic_summary.csv')
    curves=pd.read_csv(OUT/'deciles_summary.csv');acc=pd.read_csv(OUT/'accounts.csv');ev=pd.read_csv(OUT/'event_summary.csv')
    cond=pd.read_csv(OUT/'conditional_information.csv',parse_dates=['signal_date','exit_date'])
    caps=pd.read_csv(OUT/'capitalization_audit.csv');states=pd.read_csv(OUT/'state_summary.csv')
    periods=pd.read_csv(OUT/'periods.csv');daily=pd.read_parquet(CACHE/'daily_accounts.parquet')
    folds=pd.read_csv(OUT/'folds.csv');validation=json.loads((MAN/'final_validation.json').read_text())
    unit=json.loads((MAN/'test_result.json').read_text())
    main=acc.loc[(acc.scheme=='expanding')&(acc.offset==0)&(acc.cost=='main')&(acc.valuation=='flat')]
    primary=main.loc[(main.scope=='primary')&main.portfolio.isin(['D10','EW'])]
    extended=main.loc[(main.scope=='extended')&main.portfolio.isin(['D10','EW'])]
    stat=tests.loc[tests.scope=='primary'];j=primary.loc[primary.model=='J_R'].iloc[0];a=primary.loc[primary.model=='A_R'].iloc[0]
    positive=stat.loc[stat.positive_support,'test'].tolist()
    if len(positive)==6:
        decision='六项主检验均有正向统计支持，形成历史候选Alpha；仍需核对风险、覆盖与真实前瞻。'
    elif not positive:
        decision='六项主检验均未获得Holm校正后的正向支持，本轮未确认联合模型带来稳定独立Alpha。'
    else:
        decision='得到部分正向支持（'+','.join(positive)+'），但六项主证据未同时成立，本轮尚未确认稳定独立Alpha。'
    for scope in ['primary','extended']:
        g=curves.loc[(curves.scope==scope)&(curves.scheme=='expanding')&(curves.offset==0)]
        plt.figure(figsize=(9,4.6))
        for model in ['A_R','J_R','MOM','REV','FIX']:
            x=g.loc[g.model==model].sort_values('decile');plt.plot(x.decile,x.mean_H10*100,marker='o',label=model)
        plt.axhline(0,color='grey',lw=.7);plt.xticks(range(1,11));plt.xlabel('Score decile (D10 = highest)');plt.ylabel('Mean gross H10 label return (%)')
        plt.title('Full decile curve: '+scope);plt.legend(ncol=5);plt.tight_layout();plt.savefig(fig/f'deciles_{scope}.png',dpi=160);plt.close()
        plt.figure(figsize=(10,4.6))
        selected=main.loc[(main.scope==scope)&(main.portfolio.isin(['D10','EW']))&main.model.isin(['J_R','A_R','MOM','REV','FIX','EW'])]
        for r in selected.itertuples():
            d=daily.loc[daily.account==r.account];plt.plot(d.date,d.nav*100,label=r.model+(' [blocked]' if not r.valuation_complete else ''))
        plt.ylabel('NAV per initial 100');plt.title('H10 long-only accounts; main costs; suspension-mark proxy: '+scope)
        plt.legend(ncol=6);plt.tight_layout();plt.savefig(fig/f'nav_{scope}.png',dpi=160);plt.close()
    comp=ics.loc[(ics.scope=='primary')&(ics.scheme=='expanding')&(ics.offset==0),['model','n','mean','low','high']]
    e=ev.loc[(ev.scope=='primary')&(ev.scheme=='expanding')&(ev.offset==0)&(ev.portfolio=='D10')&(ev.cost=='main'),['model','mean_net','known','planned','mean_entry_weight']]
    comp=comp.merge(e,on='model',how='left').merge(primary[['model','cagr','total_return','max_drawdown','valuation_complete','terminal_liquidated']],on='model',how='left')
    comp=comp.rename(columns={'mean':'RankIC','low':'IC低界','high':'IC高界','n':'IC期数','mean_net':'H10净均值%','known':'可退出期数','planned':'计划期数','mean_entry_weight':'平均入场资金%','cagr':'净年化%','total_return':'累计净收益%','max_drawdown':'最大回撤%'})
    pct=['H10净均值%','平均入场资金%','净年化%','累计净收益%','最大回撤%']
    snapshot='''本轮所有实证均为Historical-proxy历史模拟样本外探索。真实前瞻新观测为0。严格报价分支与停牌估值代理分别运行；下列完整账户主表明确使用已确认全天停牌、最多20交易日旧价的代理分支。股票为复权合成单位，尚非完整权益与公司行动账本。'''
    links='''- [完整参数](../../../config.yaml) · [研究合同](../../../GOAL.md)
- [全部预测排名](../all_rankings.csv.gz) · [全部计划持仓](../all_target_holdings.csv.gz)
- [每个H10事件](../events.csv) · [逐股事件损益](../event_stock_details.csv.gz)
- [全部账户](../accounts.csv) · [逐日净值](../daily_accounts.csv.gz) · [完整逐月逐年](../periods.csv)
- [六项主检验](../primary_tests.csv) · [支持样本敏感性](../event_support_sensitivity.csv) · [数据与日历](../calendar.csv)
- [模型与折信息](../folds.csv) · [实际逐日持仓及成交账本](../../local_cache/ledgers/) · [全部核验](../../manifests/final_validation.json)'''
    body=f'''**{decision}**

研究问题是动量与反转的条件关系能否产生增量预测和固定H10净收益。主候选J_R使用4项动量反转输入、4个交互项和3个状态项，以未来H10收益秩为目标；独立训练基线A_R只用4个基础输入。主股票池每个信号按当时历史成员代理和61日价格资格重建，未使用原E1的Q5名单。

{snapshot}

## 1 主区间结果

信号起点2021-01-08，首次入场2021-01-11，最后计划退出2025-03-03开盘，共100个H10窗口。表中H10为可完整退出事件的单位初始资金净收益均值；CAGR和回撤来自独立连续账户，两者不能互相替代。各模型单边事件均值使用的可退出样本不同，不能直接相减作为增量；配对比较见第2节。季度模型另生成末端未成熟预测，它们不进入已实现评价。

{table(comp,pct)}

J_R净年化点估计为{j.cagr*100:.2f}%，A_R为{a.cagr*100:.2f}%；该差值不等于经过风险控制的Alpha，也不代替六项主检验。

![全部十分组](figures/deciles_primary.png)

![主区间净值](figures/nav_primary.png)

## 2 六项主检验

下表P1和P3单位为相关系数，P2a至P2d单位为小数收益率（乘100为每H10窗口的百分点）。区间为6个H10窗口时间块bootstrap的95%区间，Holm按完整6项主族调整。缺失项不缩小主族。

{table(stat[['test','n','calendar_n','mean','low','high','p','holm_p','positive_support']],digits=8)}

P1为J_R相对A_R的RankIC差；P2a/P2b/P2c/P2d分别为D10净事件收益相对A_R/MOM/REV/FIX的差；P3为控制行业、市值、风险、流动性及基础动量反转信息后的条件RankIC。未显著不构成等价或不存在Alpha的证明。

## 3 延伸历史

全部现有数据支持139个完整H10日历窗口，最后退出为2026-10-12开盘。最后39个窗口单独给出，仍为已经观察过的历史。部分连续账户因旧仓后续缺价或权益端点无法闭合而提前停止；独立新建事件仍可继续评价，这不等于连续账户能跨过阻断。下表收益、回撤与仓位单位均为%，不同终点不直接横向排名。

{table(extended[['model','portfolio','end','valuation_complete','terminal_liquidated','cagr','total_return','max_drawdown','average_stock_weight']],['cagr','total_return','max_drawdown','average_stock_weight'])}

![延伸净值](figures/nav_extended.png)

## 4 四状态与训练方式

状态属于信号时的价格背景，十分组属于预测排序。四类比例由模型选择自然形成；另运行两条四状态均衡账户和J_RW样本加权模型，不把EP36双跌历史贡献转成固定超配。

{table(states.loc[(states.scope=='primary')&(states.scheme=='expanding')&(states.offset==0)&(states.decile==10)&states.model.isin(['A_R','J_R','J_RW']),['model','state','average_share','conditional_mean_return','present_rounds','all_rounds']],['average_share','conditional_mean_return'])}

四状态缺席的日期按零预算计入平均占比；条件收益仅在该类出现且标签有效时统计。不能把两列相乘当作连续账户精确利润贡献。

## 5 独立性覆盖与执行边界

主区间P3有{int(stat.loc[stat.test=='P3','n'].iloc[0])}个有效窗口。完整历史平均控制变量覆盖股票比例为{cond.stock_coverage.mean()*100:.2f}%，J_R D10预算覆盖为{cond.D10_budget_coverage.mean()*100:.2f}%。前一交易日市值没有精确缓存的日期保持缺失，未用之后快照回填。详情见[独立性报告](H3_INDEPENDENCE.md)。

主合同每10个市场交易日退出，包括连续入选股票的卖出与重新买入，双边计费。买不到留现金；卖不出继续记录原持仓并重试，H10清仓净收益为NA。主统计只比较确有入场且完整退出的配对事件，并另给全入场与全基线共同支持的敏感性。连续账户保留资金占用与超期持仓。

## 6 验证与交付

{unit['passed']}项单元测试通过；{validation['count']}项验证通过，含{validation['model_replays']}个模型数值重放、{validation['ledger_accounts']}条主成本代理账户的成交与持仓账本重建，以及{validation['event_account_exact_reconciliations']}条无退出阻断账户的独立事件复利核对。全部{validation['source_files']}个冻结输入保持哈希不变。验证证明实现自洽，不替代经济证据。

条件消融按方案仅在联合增量有支持时启动；是否触发及其他执行说明见[执行记录](../../../notes/EXECUTION.md)。未开展真实前瞻调度、实盘或发布。

独立报告：[排序与十分组](H1_RANKING.md)、[账户与兑现](H2_ECONOMICS.md)、[条件信息与缺口](H3_INDEPENDENCE.md)、[训练与稳健性](TRAINING.md)。

{links}
'''
    write('REPORT','EP37 动量与反转联合 Alpha 实验报告',body)
    curve_table=curves.loc[(curves.scope=='primary')&(curves.scheme=='expanding')&(curves.offset==0)].pivot(index='decile',columns='model',values='mean_H10').reset_index()
    h1=f'''想验证什么：联合模型能否在同一候选池上提高H10排序，并让更高的预测分数组有更好的未来表现。

主候选为J_R，基线为A_R；其他收益目标和加权模型是登记对照。D10最高、D1最低。所有十组完整保留，未根据收益选择分组。{snapshot}

## 主区间完整十分组

单位为各信号日期组内H10已知标签收益均值再对日期平均，以下显示百分数；尚未扣费或保证全部可以退出。

{table(curve_table,[c for c in curve_table if c!='decile'])}

![十分组曲线](figures/deciles_primary.png)

## 排序统计

{table(ics.loc[(ics.scheme=='expanding')&(ics.offset==0)],digits=5)}

## 主排序增量检验

{table(tests.loc[tests.test=='P1'])}

需要解释：单个较好的尾部分组不保证整个模型有单调排序；J_Z或J_RW表现更好也不能事后替换主候选J_R。四状态内部关联与全截面排序分开报告。

[每期十分组全部统计](../deciles_by_date.csv) · [四状态内RankIC](../state_ic_by_date.csv) · [四状态与十分组交叉](../state_deciles_by_date.csv) · [全股票完整排名](../all_rankings.csv.gz) · [总报告](REPORT.md)
'''
    write('H1_RANKING','EP37 联合排序与完整十分组',h1)
    econ=main[['scope','model','portfolio','end','valuation_complete','terminal_liquidated','cagr','total_return','max_drawdown','average_stock_weight','overdue_days','blocked_buys','blocked_sells']]
    selected=periods.loc[(periods.scheme=='expanding')&(periods.offset==0)&(periods.scope=='extended')&(periods.frequency=='M')&periods.model.isin(['J_R','A_R','EW'])&periods.portfolio.isin(['D10','EW'])]
    month=selected.pivot(index='period',columns='model',values='net_return').reset_index()
    cost=acc.loc[(acc.scheme=='expanding')&(acc.offset==0)&(acc.scope=='primary')&acc.portfolio.eq('D10')&acc.model.isin(['J_R','A_R'])&(acc.valuation=='flat')]
    h2=f'''想验证什么：联合排序能否在固定H10、全部费用和真实开盘门槛下，转成优于独立基线的净收益。

{snapshot}

## 全部主账户

收益、回撤和仓位列均为百分数。`valuation_complete`表示估值到计划终点，`terminal_liquidated`表示终点真实门槛下已清仓；两者不同。只有共同完整区间才能比较CAGR。主区间至2025-03-03开盘，延伸至2026-10-12开盘。

{table(econ,['cagr','total_return','max_drawdown','average_stock_weight'])}

## 四项经济主检验

P2差为每H10窗口净收益率，以下均值与区间显示百分点；CAGR差不是该估计量。

{table(tests.loc[tests.test.str.startswith('P2')],['mean','low','high'])}

## 费用敏感性

{table(cost[['model','cost','cagr','total_return','max_drawdown','fees']],['cagr','total_return','max_drawdown'])}

## 完整逐月主候选与对照

自然月复利收益，单位%。2021年1月和2026年10月是边界部分月；最后一天使用到期退出开盘端点。

{table(month,[c for c in month if c!='period'])}

严格报价、停牌折价、滚动训练和起点后移的所有分支均在[完整账户表](../accounts.csv)。[每轮实际退出与缺失原因](../events.csv)、[全部计划持仓](../all_target_holdings.csv.gz)、[实际成交及每日持仓](../../local_cache/ledgers/)、[每轮逐股净损益](../event_stock_details.csv.gz)可逐项复核。

不能把不能退出样本填零，也不能把D10−D1影子价差称作可执行融券组合。现金、行业与集中度差异仍需与收益一起解释。[总报告](REPORT.md)
'''
    write('H2_ECONOMICS','EP37 固定十交易日账户与净收益',h2)
    cover=[]
    for scope,g in scopes(cond):
        cover.append(dict(scope=scope,planned=len(g),available=int(g.ic.notna().sum()),stock_coverage=g.stock_coverage.mean(),D10_budget_coverage=g.D10_budget_coverage.mean()))
    h3=f'''想验证什么：联合模型的信息能否超出行业、总市值、波动、市场beta、流动性、基础动量反转及A_R分数的线性控制。

对当期分数和未来H10收益使用同一控制矩阵投影，计算残差的Spearman相关。未来收益只用于评价，不进入预测。矩阵固定伪逆阈值1e-12，至少100行、30个残差自由度；近零分数残差返回NA。

{snapshot}

## 支持范围

{table(pd.DataFrame(cover),['stock_coverage','D10_budget_coverage'])}

{table(caps.groupby('status').agg(signal_dates=('signal_date','size'),source_rows=('rows','sum'),rejected_rows=('rejected','sum')).reset_index())}

精确前一交易日市值缺失导致不少日期不可评价；其他控制缺失也保持未知。覆盖比例是对全部计划信号的均值，不能只对有市值的日期平均后宣称完整覆盖。

## 条件信息主检验

{table(tests.loc[tests.test=='P3'])}

条件RankIC有支持也只对应已登记控制下的可识别样本；未支持部分不能视为零Alpha。相同行业、市值和波动的净组合反事实并未由这项回归自动建立，因此P3不代表全持仓风险中性交易认证。

[逐日期控制覆盖与矩阵秩](../conditional_information.csv) · [精确市值来源审计](../capitalization_audit.csv) · [同支持样本各模型排序](../same_support_rank_ic.csv) · [D10风险暴露及覆盖](../D10_risk_exposures.csv) · [总报告](REPORT.md)
'''
    write('H3_INDEPENDENCE','EP37 条件信息与识别范围',h3)
    train=f'''本轮训练季度推进，共{len(folds)}个最终模型；主expanding含5种目标/特征/样本权重组合，rolling36及后移5交易日仅复核A_R与J_R。正则从1、10、100中用内层最近12月的共同有效日期选择；所有外层目标在出分时隔离。

{table(folds.groupby(['scheme','offset','model','status']).size().rename('fold_count').reset_index())}

## 内层正则选择分布

{table(folds.groupby(['scheme','offset','model','alpha']).size().rename('fold_count').reset_index())}

## 滚动训练与起点敏感性

下表每条策略与其同方案A_R使用相同起止；不同起点的净值不能解释成同日期纯Alpha差。均固定H10。

{table(acc.loc[(acc.cost=='main')&(acc.valuation=='flat')&((acc.scheme=='rolling36')|(acc.offset==5)),['scheme','offset','scope','model','start','end','valuation_complete','cagr','max_drawdown']],['cagr','max_drawdown'])}

## 时间块敏感性

{table(pd.read_csv(OUT/'block_sensitivity.csv').loc[lambda x:x.scope=='primary'])}

[逐折时序及模型哈希](../folds.csv) · [内层候选完整结果](../inner_selection.csv) · [所有模型系数](../coefficients.csv) · [四状态训练权重](../training_state_weights.csv.gz) · [事后集中性描述](../concentration_diagnostics.csv) · [总报告](REPORT.md)
'''
    write('TRAINING','EP37 训练方式与稳健性结果',train)
    dump(MAN/'research_outcome.json',clean(dict(status='RESEARCH_COMPLETE_WITH_LIMITATIONS',decision=decision,
        primary_positive_tests=positive,alpha_confirmed=False,forward='FORWARD_PENDING',conditional_ablation_triggered='P1' in positive,
        report=str((REPORT/'REPORT.md').relative_to(EP)),primary_J_R=j.to_dict(),primary_A_R=a.to_dict())))
    record_stage('reports',list(REPORT.glob('*.md'))+list(REPORT.glob('*.html'))+list(fig.glob('*.png')))
    print(decision,flush=True)

if __name__=='__main__':run()

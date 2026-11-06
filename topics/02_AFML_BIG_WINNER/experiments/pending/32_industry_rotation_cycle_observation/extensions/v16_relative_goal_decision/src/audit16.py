from pathlib import Path
import sys,json,re
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; E=ROOT.parent; OUT=ROOT/'outputs'
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from statistics6 import block_summary,bh
from context6 import sha,js
V7=E/'v7_online_stage';V14=E/'v14_relative_baseline_audit';V15=E/'v15_rank_separation'
checks=[]
def check(name, ok):
    assert bool(ok),name
    checks.append(name)
def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join('|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'

def run():
    previous=json.loads((V15/'outputs/predecessors.json').read_text())
    for root in [V14,V15]:
        manifest=json.loads((root/'outputs/manifest.json').read_text())
        previous.update({str(root/f['path']):f['sha256'] for f in manifest['files']})
        previous[str(root/'outputs/manifest.json')]=sha(root/'outputs/manifest.json')
    check('all frozen predecessors unchanged',all(sha(p)==h for p,h in previous.items()))
    js(OUT/'predecessors.json',previous)
    gains=pd.read_csv(V14/'outputs/monthly_relative_rd.csv').set_index('month')
    gate=pd.read_csv(V7/'outputs/monthly_brier_gains.csv').query("cohort=='fixed24'").set_index('month').rd_gate_gain
    ranks=pd.read_csv(V15/'outputs/monthly_brier_gains.csv').query("cohort=='fixed24'").set_index('month')
    check('identical monthly cohorts',gains.index.equals(gate.index) and gains.index.equals(ranks.index))
    for c in ranks:
        if c.endswith('_gain'):gains[c[:-5]]=ranks[c]+gate
    check('all 21 candidates included',len(gains.columns)==21)
    history=list(pd.read_csv(E/'v6_economic_diffusion/outputs/primary_tests.csv').p_one_sided)
    for version in ['v8_pooled_stage','v9_market_context','v10_label_delay','v12_duration_risk','v13_completed_history','v15_rank_separation']:
        history.extend(pd.read_csv(E/version/'outputs/primary_tests.csv').p_one_sided)
    tests=pd.DataFrame([dict(model=c,**block_summary(gains[c])) for c in gains])
    check('45 unique comparisons',len(history)+len(tests)==45)
    tests['q_bh_45']=bh(np.r_[history,tests.p_one_sided])[-len(tests):]
    tests['supported_relative_rd']=tests.effect.gt(0)&tests.ci_low.gt(0)&tests.q_bh_45.lt(.05)
    tests.to_csv(OUT/'relative_rd_tests.csv',index=False);gains.to_csv(OUT/'monthly_relative_rd.csv')
    annual=pd.read_csv(V15/'outputs/annual_metrics.csv').query("cohort=='fixed24'")
    keys=['frequency','threshold','benchmark','year']
    tasks=annual.groupby(keys+['model']).agg(brier=('brier','mean'),dates=('dates','min'),positives=('positives','sum')).reset_index()
    rd=tasks[tasks.model.eq('rd_selected')][keys+['brier']].rename(columns={'brier':'rd_brier'})
    matched=tasks.merge(rd,on=keys,validate='many_to_one')
    matched['relative_gain']=1-matched.brier/matched.rd_brier
    matched['evaluable']=matched.dates.ge(6)&matched.positives.ge(10)
    matched.to_csv(OUT/'task_year_comparisons.csv',index=False)
    rows=[]
    for name,g in matched[matched.model.isin(gains.columns)].groupby('model'):
        good=g[g.evaluable]
        rows.append(dict(model=name,evaluable_task_years=len(good),improved_task_years=int(good.relative_gain.gt(0).sum()),worst_relative_gain=good.relative_gain.min()))
    overall=pd.read_csv(V15/'outputs/overall.csv').query("cohort=='fixed24'")
    summary=pd.DataFrame(rows).merge(tests,on='model').merge(overall[['model','brier','rd_gain','top10_precision','top10_lift']],on='model')
    summary.to_csv(OUT/'summary.csv',index=False)
    years=pd.read_csv(V15/'outputs/annual_summary.csv').query("cohort=='fixed24'")
    years.to_csv(OUT/'year_frequency_comparisons.csv',index=False)
    events=pd.read_csv(V15/'outputs/event_detection.csv').query("cohort=='fixed24'").groupby('model')[['event_recall','median_delay_days']].mean().reset_index()
    events.to_csv(OUT/'event_tradeoffs.csv',index=False)
    # Distinguish original three baselines from subsequent researcher-added controls.
    contract=[]
    for label,baselines in [('original_three',['prior','logistic','static_tree']),('plus_rd',['prior','logistic','static_tree','rd_selected']),('plus_gate',['prior','logistic','static_tree','rd_selected','rd_gate'])]:
        check('baseline names exist '+label,set(baselines).issubset(set(tasks.model)))
        best=tasks[tasks.model.isin(baselines)].groupby(keys).brier.min().rename('best_baseline')
        d=matched.merge(best,on=keys)
        for identity,g in d[d.model.isin(gains.columns)&d.evaluable].groupby(['model','frequency','threshold','benchmark']):
            contract.append(dict(zip(['model','frequency','threshold','benchmark'],identity),contract=label,eligible_years=len(g),all_eligible_years_brier_better=bool(g.brier.lt(g.best_baseline).all())))
    pd.DataFrame(contract).to_csv(OUT/'annual_baseline_contracts.csv',index=False)
    selected=summary.set_index('model').loc['risk_blend']
    check('risk_blend 67 of 69 improve',selected.improved_task_years==67 and selected.evaluable_task_years==69)
    check('risk_blend all 12 year frequency aggregates improve',len(years[years.model.eq('risk_blend')])==12 and years.loc[years.model.eq('risk_blend'),'rd_gain'].gt(0).all())
    check('risk_blend supported versus RD in expanded family',selected.supported_relative_rd)
    old=pd.read_csv(V14/'outputs/summary.csv').set_index('model')
    for c in ['rd_gain','top10_precision','top10_lift','worst_relative_gain']:
        check('prior audit reproduced '+c,np.allclose(summary.set_index('model').loc[old.index,c],old[c]))
    check('V15 original failure preserved',json.loads((V15/'outputs/verdict.json').read_text())['status']=='NO_SATISFACTORY_RESULT')
    decision=dict(status='HISTORICAL_RELATIVE_RD_CANDIDATE_IDENTIFIED',main_candidate='risk_blend',simple_reference='rd_gate',stretch_candidate='rank_hedged',goal_basis='user explicitly prioritizes stable improvement versus original RD; 2x is stretch',original_complete_gate_passed=False,strict_PIT='BLOCKED_DATA',independent_forward_validation='FORWARD_PENDING',selection_is_retrospective=True,production_deployed=False)
    js(OUT/'decision.json',decision)
    names={'rd_gate':'简单阶段过滤','risk_blend':'主要候选：阶段过滤与风险树各50%','risk_prior_blend':'风险/阶段/先验融合','rank_hedged':'进取候选：排序与风险先验融合各50%'}
    d=summary[summary.model.isin(names)].copy()
    table=pd.DataFrame({'方法':d.model.map(names),'较RD误差改善':d.rd_gain.map(lambda x:f'{x:.2%}'),'前10%命中率':d.top10_precision.map(lambda x:f'{x:.2%}'),'同期基准率倍数':d.top10_lift.map(lambda x:f'{x:.2f}'),'改善任务年度':[f'{int(a)}/{int(b)}' for a,b in zip(d.improved_task_years,d.evaluable_task_years)],'最差任务年度改善':d.worst_relative_gain.map(lambda x:f'{x:+.2%}'),'45项校正q':d.q_bh_45.map(lambda x:f'{x:.3f}')})
    yearly=years[years.model.isin(['risk_blend','rank_hedged'])].groupby(['model','year'])[['rd_gain','top10_precision','top10_lift']].mean().reset_index()
    for c in ['rd_gain','top10_precision']:yearly[c]=yearly[c].map(lambda x:f'{x:.2%}')
    yearly.top10_lift=yearly.top10_lift.map(lambda x:f'{x:.2f}')
    eventtable=events[events.model.isin(['rd_selected','rd_gate','risk_blend','rank_hedged'])].copy()
    eventtable.event_recall=eventtable.event_recall.map(lambda x:f'{x:.2%}')
    eventtable.median_delay_days=eventtable.median_delay_days.map(lambda x:f'{x:.2f}')
    bad=matched[matched.model.eq('risk_blend')&matched.evaluable&matched.relative_gain.le(0)][keys+['brier','rd_brier','relative_gain']].copy()
    bad.relative_gain=bad.relative_gain.map(lambda x:f'{x:+.2%}')
    text='''# EP32 V16：按相对原RD目标确定历史研究候选

用户已确认以“稳定优于原RD基线”为主，2倍命中率提升作为更高目标。按这一目标，已有历史证据支持保留 **risk_blend（阶段过滤与波动风险树各50%）**。本轮完成候选选择和复核，没有新增训练或改标签。它不是每个组合都改善，也不是独立前瞻验收通过。

## 经济学假设与方法

待检验的解释是：市场逐步吸收行业改善的信息，价格趋势会表现出一定持续性；但短期反弹也会产生类似涨幅，因此要结合趋势所处阶段、上涨相对噪声的强度、距回撤终止线的距离，区分可能持续的早期趋势与短行情。这只是价格可观测假设，现有结果不能证明订单、利润或资本开支的基本面机制。

执行时仅用观察日及此前的信息维护候选低点；不可能仍处于起点后三个月的行业先过滤。对其余行业使用27个状态、动量、宽度与波动风险变量的固定树，季度训练只纳入当时已成熟标签，输出与过滤后原RD概率各占50%。周、双周、月度分别更新；每次在二级/三级行业内各取前10%。三种回撤阈值及沪深300/中证全指仍并列，不挑表现最好的单一口径。

目标始终是识别事后被确认的6—18个月价格上涨且跑赢基准阶段的起点后三个月；不是提前一个月预测。超18个月不拆分。前三市值龙头和同业扩散机制先前未获得稳健增量，不能作为本方法已证实的经济解释。

## 同样历史主样本的比较

'''+md(table)+'''
原RD命中率为7.73%，提升倍数为1.26。表中倍数相对于同日可比总体的正例率，不是相对于RD命中率；各任务倍数再平均，所以不能用汇总命中率直接相除重建。Brier改善同样先按细任务计算比例再平均。

所有21个候选都进入相对RD检验，连同不重复的24个既有机制/过滤增量检验，共45项BH校正；三个月市场月份区块重抽样沿用原设置。与原RD的比较成立，不等于证明风险模型优于简单过滤：后者增量的既有累计校正未通过，原结果完整保留。简单过滤是应保留的简约对照。

69个任务年度按频率×阈值×基准×年度定义，要求至少6个日期、合计至少10个已知正例，组合相互重叠，不能当作69个独立试验。主要候选的两个回退组合：

'''+md(bad)+'''
逐年汇总如下；逐频率全部结果另存表中。主要候选12个年度×频率汇总全部优于RD，不能据此声称每个行业、每个年度或每个阈值都更好。

'''+md(yearly)+'''
## 检出率与及时性的取舍

'''+md(eventtable)+'''
事件检出率和延迟均先在任务中统计再等权平均；延迟列是“各任务中位延迟的平均”，不是所有周期合并后的中位数。增强模型可能多检出一些原先漏掉的周期，同时平均识别更晚，不能把它宣传成更早发现。

## 决策与证据边界

主要候选按稳定性保留risk_blend；rd_gate作为简单对照；rank_hedged作为争取2倍提升的进取候选，其总体超过2倍不意味着逐年都超过2倍。权重沿用实验原值，没有按本轮结果调整。不把2倍重新设成主要目标的硬门槛，也不把这次用户确认追溯改写成原实验已通过。

历史数据从2017年开始，主评价为2021年至2024年9月并统一24个月标签跟踪；后端未成熟样本不强行计负。2021分类断点的已知标签覆盖约37%，其余主要年份约95%—98%。未知样本上的真实表现尚不确定。全部历史已反复用于探索，统计校正不能消除选择偏差；此次选择是历史研究结论。

严格PIT仍为BLOCKED_DATA（缺历史可得性凭证），独立前瞻验证为FORWARD_PENDING，未部署生产。现有V5后的每日转折标签也不同于V4月末转折描述，两者不应混作同一个事件集合。本次不修改任何事件定义。

原始基线为先验与静态模型；后续研究另加原RD和简单过滤作更严对照。旧报告将额外要求并称“原完整标准”的措辞在此澄清。逐年三套基线比较全部输出，不能把“未优于额外基线”误写成“所有原始组合均失败”。原来频率级多阈值、双基准及2倍等完整标准的未通过记录保留；当前相对RD研究目标与该标准明确分开。

[全部候选](../outputs/summary.csv) · [任务年度](../outputs/task_year_comparisons.csv) · [逐年逐频率](../outputs/year_frequency_comparisons.csv) · [基线口径审计](../outputs/annual_baseline_contracts.csv) · [统计检验](../outputs/relative_rd_tests.csv) · [机器可读决策](../outputs/decision.json) · [固定模型实现](../../v12_duration_risk/src/experiment12.py)
'''
    (ROOT/'reports/relative_goal_decision.md').write_text(text)
    (ROOT/'README.md').write_text('# EP32 V16\n\n[相对RD目标结论](reports/relative_goal_decision.md)。\n\n只读审计既有结果；运行src/audit16.py复核。\n')
    for p in ROOT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if '://' not in target and not target.startswith('#'):check('link '+str(p.relative_to(ROOT))+' '+target,(p.parent/target.split('#')[0]).exists())
    check('predecessors unchanged after decision',all(sha(p)==h for p,h in previous.items()))
    js(OUT/'validation.json',dict(status='PASS',checks=checks,checks_count=len(checks),relative_goal_historical_candidate=True,original_gate_passed=False))
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files)))
    print(summary[summary.model.isin(names)].to_string(index=False))
    print(eventtable.to_string(index=False));print('PASS',len(checks),'checks;',len(files),'files')

if __name__=='__main__':run()

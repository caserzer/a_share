import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from context7 import ROOT,OUT

NAMES={'prior':'历史先验','logistic':'静态逻辑回归','static_tree':'静态树','rd_selected':'原RD-Agent模型',
       'rd_gate':'原模型加阶段过滤','rd_state':'加入实时阶段特征','rd_conditional':'候选阶段条件模型'}


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def run():
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    m=pd.read_csv(OUT/'metrics.csv');a=pd.read_csv(OUT/'annual_metrics.csv')
    cov=pd.read_csv(OUT/'coverage.csv');tests=pd.read_csv(OUT/'primary_tests.csv')
    verdict=json.loads((OUT/'verdict.json').read_text())
    keys=['cohort','frequency','threshold','benchmark','level']
    ref=m[m.model.eq('rd_selected')][keys+['brier']].rename(columns={'brier':'rd_brier'})
    c=m.merge(ref,on=keys,validate='many_to_one');c['rd_relative_gain']=1-c.brier/c.rd_brier
    c.to_csv(OUT/'matched_comparisons.csv',index=False)
    summary=c.groupby(['cohort','frequency','model'])[['brier','rd_relative_gain','top10_precision','top10_lift','pr_auc']].mean().reset_index()
    summary.to_csv(OUT/'summary.csv',index=False)
    overall=c.groupby(['cohort','model'])[['brier','rd_relative_gain','top10_precision','top10_lift']].mean().reset_index()
    overall.to_csv(OUT/'overall.csv',index=False)
    d=overall[overall.cohort.eq('fixed24')].set_index('model').reindex(NAMES).reset_index()
    view=pd.DataFrame({'方法':d.model.map(NAMES),'Brier误差':d.brier.map(lambda x:f'{x:.6f}'),
        '较原RD相对改善':d.rd_relative_gain.map(lambda x:f'{x:+.2%}'),
        '前10%命中率':d.top10_precision.map(lambda x:f'{x:.2%}'),'命中率提升倍数':d.top10_lift.map(lambda x:f'{x:.2f}')})
    freqrows=[]
    for name,values in verdict['frequency_gates'].items():
        for freq,v in values.items():freqrows.append({'方法':NAMES[name],'频率':freq,
            '两基准均通过的回撤口径':','.join(f'{t:.0%}' for t in v['passed_thresholds']) or '无',
            '完整验收':'通过' if v['passed'] else '未通过'})
    keys=['cohort','frequency','threshold','benchmark','level','year']
    ref=a[a.model.eq('rd_selected')][keys+['brier']].rename(columns={'brier':'rd_brier'})
    ac=a.merge(ref,on=keys,validate='many_to_one');ac['rd_relative_gain']=1-ac.brier/ac.rd_brier
    annual=ac.groupby(['cohort','year','frequency','model'])[['brier','rd_relative_gain','top10_precision','top10_lift']].mean().reset_index()
    annual.to_csv(OUT/'annual_summary.csv',index=False)
    basecov=cov[cov.model.eq('rd_selected')].groupby(['cohort','year'])[['observations','known','unknown','positives']].sum().reset_index()
    basecov['known_fraction']=basecov.known/basecov.observations
    basecov.to_csv(OUT/'label_maturity_by_year.csv',index=False)
    displaytests=pd.DataFrame({'方法':tests.candidate.map(NAMES),'绝对Brier改善':tests.effect.map(lambda x:f'{x:+.6f}'),
        '95%区间':[f'[{l:+.6f},{h:+.6f}]' for l,h in zip(tests.ci_low,tests.ci_high)],
        'BH调整q':tests.q_bh.map(lambda x:f'{x:.3f}'),'统计增量':tests.supported.map({True:'通过',False:'未通过'})})
    passing=[f'{NAMES[n]}（{f}）' for n,v in verdict['frequency_gates'].items() for f,g in v.items() if g['passed']]
    result='达到本轮历史验收的组合：'+('；'.join(passing) if passing else '无')+'。'
    text=('# EP32 V7：实时阶段状态与早期识别\n\n'+result+'\n\n'
        '最关键的变化是先判断“当前是否仍可能位于起点后三个月”，再估计未来是否发展成符合定义的6—18个月景气。'
        '原模型主要看收益、宽度和波动，没有直接表示当前上涨阶段已经持续多久。\n\n'
        '实时状态只读取当日及以前的价格，逐日更新候选低点和已确认上行起点；已确认上行的起点不会随未来数据回改。'
        '如果起点已在三个月之外，或者属于初始左删失阶段，当前观察不符合早期定义。'
        '在计算范围内，该约束没有排除任何既有已知正例；追加未来价格不改变历史状态。\n\n'
        '这是与目标定义一致的实时阶段约束，不是用未来低点做输入，也不是新的需求或盈利证据。'
        '仅加过滤在已知标签上的误差改善部分来自排除逻辑上不可能的负例；这不能自动证明候选阶段的后续持续性预测很强。'
        '因此同时保留前10%命中率、四个基线和逐年验收，不能只以Brier下降宣布成功。\n\n'+md(view)+'\n'
        '各频率、回撤口径、市场基准和行业层级等权汇总；相对改善先在同一任务内计算再平均。'
        '主要评价为2021-01-01至2024-09-30，每条标签统一跟踪24个日历月；尚未解决者仍为未知。'
        '底层数据从2017年起，训练仅用当时已成熟标签。\n\n'+md(pd.DataFrame(freqrows))+'\n'
        '完整验收要求：误差低于历史先验、静态逻辑回归、静态树及原RD模型；前10%命中率至少为同日基准率的2倍；'
        '至少两个可评价年度且所有可评价年度均优于四个基线。每频率至少两个回撤口径在两市场基准同时成立，并通过下列增量检验。\n\n'
        +md(displaytests)+'\n'
        '三项固定候选统一BH校正；置信区间按同市场月份连续三个月成块重抽样，不把重复股票/行业/频率当作独立样本。\n\n'
        '年度标签覆盖（跨频率、基准与阈值有重复，条数不是独立事件）：\n\n'
        +md(basecov[basecov.cohort.eq('fixed24')].drop(columns='cohort').assign(known_fraction=lambda z:z.known_fraction.map(lambda x:f'{x:.1%}')))+'\n'
        '历史选择限制：2021—2022年曾用于V5模型搜索，2024年也已在前轮查看；整轮是历史探索，不是未触碰的独立检验。'
        '统一跟踪24个月减轻观察时长不同的问题，但仍条件于标签可解决样本；2021年行业分类断点造成的未知不能忽略。'
        '主表命中率仅针对已知标签；另给出把所有未知分别当失败或成功的[命中率上下界](../outputs/unknown_label_bounds.csv)，'
        '用于检查缺标签能造成多大不确定性，这些上下界不回填原始标签。'
        '原口径2024年至末端结果单独保留在legacy_current，2026年正例未充分成熟，不用于宣称跨年稳定。\n\n'
        '严格PIT仍为BLOCKED_DATA，独立前瞻验证FORWARD_PENDING。历史成员及股本known_at、复权价格和基本面公告版本的旧边界不变。\n\n'
        '[逐年结果](../outputs/annual_summary.csv)；[完整任务结果](../outputs/task_metrics.csv)；'
        '[事件去重后的检出与延迟](../outputs/event_detection.csv)；[未知及选中覆盖](../outputs/coverage.csv)；'
        '[验收明细](../outputs/verdict.json)；[固定方案](../research_plan.md)。\n')
    (reports/'online_stage_observation.md').write_text(text)
    fig,axes=plt.subplots(1,3,figsize=(12,3.7),sharey=True,layout='constrained')
    for ax,freq in zip(axes,['W','BW','M']):
        d=annual[annual.cohort.eq('fixed24')&annual.frequency.eq(freq)]
        for name in ['rd_gate','rd_state','rd_conditional']:
            g=d[d.model.eq(name)];ax.plot(g.year,g.rd_relative_gain*100,marker='o',label=name)
        ax.axhline(0,color='gray',linestyle='--');ax.set_title(freq);ax.set_xticks([2021,2022,2023,2024])
    axes[0].set_ylabel('Brier improvement vs RD baseline (%)');axes[-1].legend(fontsize=8)
    fig.savefig(reports/'annual_gains.png',dpi=150);plt.close(fig)
    with (reports/'online_stage_observation.md').open('a') as h:h.write('\n![年度相对误差改善](annual_gains.png)\n')
    (ROOT/'README.md').write_text('# EP32 V7\n\n[实时阶段识别结果](reports/online_stage_observation.md)。\n\n'
        '顺序运行src/state7.py、src/experiment7.py、src/score7.py、src/report7.py、src/validate7.py。'
        '实验使用RD-Agent虚拟环境，所有参数固定，未启动新的参数搜索。逐条面板和预测保存在私有online_v7缓存。\n')
    print(result,flush=True)


if __name__=='__main__':run()

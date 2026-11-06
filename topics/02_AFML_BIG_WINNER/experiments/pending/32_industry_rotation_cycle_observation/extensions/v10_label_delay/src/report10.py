import json
import pandas as pd
from context10 import ROOT,OUT


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def run():
    names={'prior':'历史先验','logistic':'静态逻辑回归','static_tree':'静态树','rd_selected':'原RD模型',
        'rd_gate':'简单阶段过滤','pool_tree':'V8共享状态树','lag12_tree':'训练等待12个月',
        'lag24_tree':'训练等待24个月','delay_weighted_tree':'等待12个月并修正成熟概率'}
    m=pd.read_csv(OUT/'metrics.csv');a=pd.read_csv(OUT/'annual_metrics.csv')
    keys=['cohort','frequency','threshold','benchmark','level']
    for name,alias in [('rd_selected','rd'),('rd_gate','gate')]:
        ref=m[m.model.eq(name)][keys+['brier']].rename(columns={'brier':alias+'_brier'})
        m=m.merge(ref,on=keys,validate='many_to_one');m[alias+'_gain']=1-m.brier/m[alias+'_brier']
    m.to_csv(OUT/'matched_comparisons.csv',index=False)
    cols=['brier','rd_gain','gate_gain','top10_precision','top10_lift']
    overall=m.groupby(['cohort','model'])[cols].mean().reset_index();overall.to_csv(OUT/'overall.csv',index=False)
    m.groupby(['cohort','frequency','model'])[cols].mean().reset_index().to_csv(OUT/'summary.csv',index=False)
    for name,alias in [('rd_selected','rd'),('rd_gate','gate')]:
        ref=a[a.model.eq(name)][keys+['year','brier']].rename(columns={'brier':alias+'_brier'})
        a=a.merge(ref,on=keys+['year'],validate='many_to_one');a[alias+'_gain']=1-a.brier/a[alias+'_brier']
    a.groupby(['cohort','year','frequency','model'])[cols].mean().reset_index().to_csv(OUT/'annual_summary.csv',index=False)
    d=overall[overall.cohort.eq('fixed24')].set_index('model').reindex(names).reset_index()
    table=pd.DataFrame({'方法':d.model.map(names),'Brier':d.brier.map(lambda x:f'{x:.6f}'),
        '较原RD改善':d.rd_gain.map(lambda x:f'{x:+.2%}'),'较简单过滤改善':d.gate_gain.map(lambda x:f'{x:+.2%}'),
        '前10%命中率':d.top10_precision.map(lambda x:f'{x:.2%}'),'提升倍数':d.top10_lift.map(lambda x:f'{x:.2f}')})
    verdict=json.loads((OUT/'verdict.json').read_text());gates=[];passing=[]
    for name,v in verdict['frequency_gates'].items():
        for freq,g in v.items():
            gates.append({'方法':names[name],'频率':freq,'通过阈值':','.join(f'{x:.0%}' for x in g['passed_thresholds']) or '无','完整验收':'通过' if g['passed'] else '未通过'})
            if g['passed']:passing.append(names[name]+' '+freq)
    status='通过完整历史验收的组合：'+('；'.join(passing) if passing else '无')+'。'
    tests=pd.read_csv(OUT/'primary_tests.csv')
    t=pd.DataFrame({'方法':tests.candidate.map(names),'较简单过滤的绝对Brier增量':tests.effect.map(lambda x:f'{x:+.6f}'),
        '95%区间':[f'[{x:+.6f},{y:+.6f}]' for x,y in zip(tests.ci_low,tests.ci_high)],
        '累计18项BH的q':tests.q_bh.map(lambda x:f'{x:.3f}'),'支持增量':tests.supported.map({True:'是',False:'否'})})
    r=ROOT/'reports';r.mkdir(exist_ok=True)
    text=('# EP32 V10：训练标签成熟速度不同的影响\n\n'+status+'\n\n'
        '长行情正例往往较晚确认，负例常较早解决。直接使用所有已知标签可能让较新训练样本偏向快速解决者。'
        '本轮固定比较等待12个月、24个月，以及等待12个月后按旧样本估计的成熟概率逆数加权。'
        '未知结果仍为未知，权重不超过5，逐日/行业层级总权重重新归一，历史参考也必须在当时可得。\n\n'
        +md(table)+'\n'+md(pd.DataFrame(gates))+'\n'+md(t)+'\n'
        '主评价与标签保持不变：2021-01-01至2024-09-30统一24个月跟踪，条件于已知结果。'
        '完整验收仍要求优于四项原基线和简单阶段过滤、至少2倍前10%命中率、所有可评价年度均改善，'
        '且每频率至少两个阈值在两市场基准通过。上述相对值先按同任务计算再等权平均。\n\n'
        '延迟加权并不自动正确：它假设旧参考中的类别成熟速度可以用于较新样本，且当前类别有足够已观察机会。'
        '12个月等待及权重上限只能缓解问题，不能创造未观察的正例，也不能解决真实周期启动率的年度变化。'
        '24个月内仍未解决的阶段保持未知，未被计为负例。\n\n'
        '这些年份已用于探索；2021分类断点和近期标签不成熟限制结论。严格PIT仍BLOCKED_DATA，独立前瞻确认仍FORWARD_PENDING。\n\n'
        '[逐年结果](../outputs/annual_summary.csv)；[逐频率结果](../outputs/summary.csv)；'
        '[周期检出与延迟](../outputs/event_detection.csv)；[覆盖](../outputs/coverage.csv)；'
        '[未知标签界限](../outputs/unknown_label_bounds.csv)；[完整验收](../outputs/verdict.json)；[事前方案](../research_plan.md)。\n')
    (r/'label_delay_observation.md').write_text(text)
    (ROOT/'README.md').write_text('# EP32 V10\n\n[标签成熟延迟实验](reports/label_delay_observation.md)。\n\n'
        '顺序运行src/experiment10.py、src/score10.py、src/report10.py、src/validate10.py；模型使用RD-Agent虚拟环境。'
        '私有预测缓存为delay_v10，旧版只读。\n')
    print(status,flush=True)


if __name__=='__main__':run()

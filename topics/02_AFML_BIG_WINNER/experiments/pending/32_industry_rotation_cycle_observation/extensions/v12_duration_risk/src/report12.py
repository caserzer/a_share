import json
import pandas as pd
from context12 import ROOT,OUT


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def run():
    names={'prior':'历史先验','logistic':'静态逻辑回归','static_tree':'静态树','rd_selected':'原RD模型',
        'rd_gate':'简单阶段过滤','pool_tree':'V8共享状态树','risk_tree':'波动尺度树',
        'risk_blend':'波动尺度与阶段过滤各50%','risk_prior_blend':'波动尺度与先验融合'}
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
        '累计21项BH的q':tests.q_bh.map(lambda x:f'{x:.3f}'),'支持增量':tests.supported.map({True:'是',False:'否'})})
    r=ROOT/'reports';r.mkdir(exist_ok=True)
    text=('# EP32 V12：波动尺度与短行情风险\n\n'+status+'\n\n'
        'V11指出多数已解决误报是短于六个月的行情。本轮将转折阈值相对于波动率的尺度、漂移相对噪声、当前回撤距离和阶段年龄显式加入共享树，'
        '同时检验固定融合。波动尺度是描述变量，不是对真实行业周期长度的精确公式。\n\n'
        +md(table)+'\n'+md(pd.DataFrame(gates))+'\n'+md(t)+'\n'
        '主评价及验收不变：2021-01-01至2024-09-30、每条统一24个月跟踪，未知不当负例；误差须低于四个原基线及简单过滤，'
        '前10%命中率至少2倍、所有可评价年度改善、每频率至少两个阈值在两市场基准通过。相对值先按任务计算，再等权平均。\n\n'
        '风险特征只使用当时的年化波动换算日波动、历史收益和在线阶段；不读取V11事后误报分类。'
        '八项变换、三个候选和融合权重在预测前固定，本轮累计21项BH校正。\n\n'
        '理论动机参考[Magdon-Ismail等关于布朗运动回撤的研究](https://work.caltech.edu/pub/Magdon-Ismail2004drawdown.pdf)，'
        '该文不证明A股周期符合布朗运动，也不把当前启发式变量变成行业盈利解释。\n\n'
        '历史已经被查看，2021分类断点及标签未知限制独立性和覆盖；严格PIT仍BLOCKED_DATA，前瞻确认仍FORWARD_PENDING。\n\n'
        '[逐年结果](../outputs/annual_summary.csv)；[逐频率结果](../outputs/summary.csv)；'
        '[周期检出与延迟](../outputs/event_detection.csv)；[覆盖](../outputs/coverage.csv)；'
        '[未知标签界限](../outputs/unknown_label_bounds.csv)；[完整验收](../outputs/verdict.json)；[事前方案](../research_plan.md)。\n')
    (r/'duration_risk_observation.md').write_text(text)
    (ROOT/'README.md').write_text('# EP32 V12\n\n[波动尺度与持续性实验](reports/duration_risk_observation.md)。\n\n'
        '顺序运行src/experiment12.py、src/score12.py、src/report12.py、src/validate12.py；模型使用RD-Agent虚拟环境。'
        '私有预测缓存为duration_v12，旧版只读。\n')
    print(status,flush=True)


if __name__=='__main__':run()

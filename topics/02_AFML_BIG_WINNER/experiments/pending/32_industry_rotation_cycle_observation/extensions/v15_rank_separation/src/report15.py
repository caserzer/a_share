import json
import pandas as pd
from context15 import ROOT,OUT


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def run():
    names={'prior':'历史先验','logistic':'静态逻辑回归','static_tree':'静态树','rd_selected':'原RD模型',
        'rd_gate':'简单阶段过滤','pool_tree':'V8共享状态树','risk_prior_blend':'V12风险与先验融合','rank_half':'排序强度0.5',
        'rank_one':'排序强度1','rank_hedged':'排序与原融合各50%'}
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
        '累计42项BH的q':tests.q_bh.map(lambda x:f'{x:.3f}'),'支持增量':tests.supported.map({True:'是',False:'否'})})
    r=ROOT/'reports';r.mkdir(exist_ok=True)
    text=('# EP32 V15：分离总体概率与行业排序\n\n'+status+'\n\n'
        '本轮保持V12风险与先验融合的每个观察日总体概率水平，单独用同日同层级排序学习器重新分配可行行业间的概率。'
        '截距只根据当日模型分数和已有平均概率求解，不使用当期结果；这是排序方法，不是新的基本面数据。\n\n'
        +md(table)+'\n'+md(pd.DataFrame(gates))+'\n'+md(t)+'\n'
        '90棵树、7叶、深3、截断31及三项概率分配强度/融合权重均事前固定。每个日期/层级的概率总质量保持，'
        '但保留总体均值不保证组内概率校准，因此必须同时检查Brier和前10%命中率。\n\n'
        '原完整标准仍为优于四个原基线及简单过滤、至少2倍命中率、所有可评价年度改善，'
        '并在每频率至少两个阈值与两个基准通过。本轮三项检验连同此前39个不重复比较一起BH校正，共42项。\n\n'
        '主要样本仍为2021年至2024年9月、固定24个月标签跟踪；未知不记负例。历史重复探索、2021分类断点、'
        '严格PIT BLOCKED_DATA及独立前瞻验证FORWARD_PENDING的边界不变。\n\n'
        '[逐年结果](../outputs/annual_summary.csv)；[逐频率结果](../outputs/summary.csv)；'
        '[周期检出与延迟](../outputs/event_detection.csv)；[覆盖](../outputs/coverage.csv)；'
        '[未知标签界限](../outputs/unknown_label_bounds.csv)；[完整验收](../outputs/verdict.json)；[事前方案](../research_plan.md)。\n')
    (r/'rank_separation_observation.md').write_text(text)
    (ROOT/'README.md').write_text('# EP32 V15\n\n[总体概率与排序实验](reports/rank_separation_observation.md)。\n\n'
        '顺序运行src/experiment15.py、src/score15.py、src/report15.py、src/validate15.py；模型使用RD-Agent虚拟环境。'
        '私有预测缓存为rank_v15，旧版只读。\n')
    print(status,flush=True)


if __name__=='__main__':run()

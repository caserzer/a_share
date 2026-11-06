import json
import pandas as pd
from context13 import ROOT,OUT


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def run():
    names={'prior':'历史先验','logistic':'静态逻辑回归','static_tree':'静态树','rd_selected':'原RD模型',
        'rd_gate':'简单阶段过滤','pool_tree':'V8共享状态树','risk_prior_blend':'V12波动尺度与先验融合','history_tree':'行业历史持续性树',
        'history_blend':'历史持续性与过滤各50%','history_prior_blend':'历史持续性与先验融合'}
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
        '累计24项BH的q':tests.q_bh.map(lambda x:f'{x:.3f}'),'支持增量':tests.supported.map({True:'是',False:'否'})})
    r=ROOT/'reports';r.mkdir(exist_ok=True)
    text=('# EP32 V13：已结束阶段的行业持续性历史\n\n'+status+'\n\n'
        '检验过去经常出现短反弹的行业，与过去持续性较强的行业，是否具有可用的差异。'
        '新增历史阶段数量、短段/合格段比例、持续时间及最近阶段信息；每条历史必须在观察日已确认结束。'
        '行业自身历史不跨分类版本冒认，全行业已知均值提供10个伪阶段的收缩。\n\n'
        +md(table)+'\n'+md(pd.DataFrame(gates))+'\n'+md(t)+'\n'
        '模型使用V12风险特征加七项历史特征，树参数与融合权重固定；无自身历史的最近阶段指标保留未知。'
        '未来阶段追加不改变过去特征、确认日边界、左删失及跨版本隔离均有针对性测试。\n\n'
        '主评价仍为2021年至2024年9月、统一24个月跟踪。完整验收保持五项对照、2倍命中率、跨年改善、'
        '每频率至少两个回撤阈值在两市场基准通过；三个新检验纳入累计24项BH校正。\n\n'
        '历史已被查看，标签未知和分类断点仍限制推断；历史持续性不是盈利或需求因果证据。'
        '严格PIT仍BLOCKED_DATA，独立前瞻确认仍FORWARD_PENDING。\n\n'
        '[逐年结果](../outputs/annual_summary.csv)；[逐频率结果](../outputs/summary.csv)；'
        '[周期检出与延迟](../outputs/event_detection.csv)；[覆盖](../outputs/coverage.csv)；'
        '[未知标签界限](../outputs/unknown_label_bounds.csv)；[完整验收](../outputs/verdict.json)；[事前方案](../research_plan.md)。\n')
    (r/'completed_history_observation.md').write_text(text)
    (ROOT/'README.md').write_text('# EP32 V13\n\n[历史阶段持续性实验](reports/completed_history_observation.md)。\n\n'
        '顺序运行src/experiment13.py、src/score13.py、src/report13.py、src/validate13.py；模型使用RD-Agent虚拟环境。'
        '私有预测缓存为history_v13，旧版只读。\n')
    print(status,flush=True)


if __name__=='__main__':run()

import json
import pandas as pd
from context9 import ROOT,OUT


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def run():
    names={'prior':'历史先验','logistic':'静态逻辑回归','static_tree':'静态树','rd_selected':'原RD模型',
        'rd_gate':'简单阶段过滤','rd_state':'分任务状态树','rd_conditional':'分任务条件树',
        'pool_logistic':'共享逻辑回归','pool_tree':'共享状态树','pool_blend':'共享逻辑回归融合',
        'context_tree':'加入市场阶段的共享树','context_blend':'市场阶段树与简单过滤各50%','context_cap':'两模型较低概率'}
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
        '相对原RD改善':d.rd_gain.map(lambda x:f'{x:+.2%}'),'相对简单过滤改善':d.gate_gain.map(lambda x:f'{x:+.2%}'),
        '前10%命中率':d.top10_precision.map(lambda x:f'{x:.2%}'),'提升倍数':d.top10_lift.map(lambda x:f'{x:.2f}')})
    verdict=json.loads((OUT/'verdict.json').read_text());gates=[];passing=[]
    for name,v in verdict['frequency_gates'].items():
        for freq,g in v.items():
            gates.append({'方法':names[name],'频率':freq,'通过阈值':','.join(f'{x:.0%}' for x in g['passed_thresholds']) or '无','完整验收':'通过' if g['passed'] else '未通过'})
            if g['passed']:passing.append(names[name]+' '+freq)
    status='通过完整历史验收的组合：'+('；'.join(passing) if passing else '无')+'。'
    tests=pd.read_csv(OUT/'primary_tests.csv')
    t=pd.DataFrame({'方法':tests.candidate.map(names),'相对简单过滤的绝对Brier增量':tests.effect.map(lambda x:f'{x:+.6f}'),
        '95%区间':[f'[{x:+.6f},{y:+.6f}]' for x,y in zip(tests.ci_low,tests.ci_high)],
        '累计15项BH的q':tests.q_bh.map(lambda x:f'{x:.3f}'),'支持增量':tests.supported.map({True:'是',False:'否'})})
    r=ROOT/'reports';r.mkdir(exist_ok=True)
    text=('# EP32 V9：行业起点相对市场周期的位置\n\n'+status+'\n\n'
        '假设是市场共同周期影响行业反弹的持续性。新增市场在线低点龄、方向、回撤和涨幅，行业相对市场低点的位置，'
        '以及当前同行的上行覆盖面、超额强度和相对排名。全部只用当前及以前数据，不使用事后牛熊年份。\n\n'
        +md(table)+'\n'+md(pd.DataFrame(gates))+'\n'+md(t)+'\n'
        '三候选及融合权重事前固定；主检验比较简单阶段过滤，累计V6—V9十五项一起BH校正。'
        '指标按频率、阈值、基准、行业层级任务等权，改善比例在同任务内计算后平均。\n\n'
        '主要评价仍为2021-01-01至2024-09-30、固定24个月标签跟踪。既有四项基线和简单过滤均须被超越，'
        '前10%命中率至少2倍，各可评价年度误差均改善，每频率至少两个阈值同时在两基准通过；未降低标准。\n\n'
        '历史重复探索限制依旧：2021—2022被用于旧模型选择，2024已经查看；2021分类断点导致大量未知。'
        '标签未成熟者不填负例，主命中率条件于已知标签，未知影响另列。'
        '市场阶段特征不能替代订单、盈利证据，严格PIT仍为BLOCKED_DATA，独立前瞻确认仍为FORWARD_PENDING。\n\n'
        '[逐年比较](../outputs/annual_summary.csv)；[逐频率比较](../outputs/summary.csv)；'
        '[事件检出和延迟](../outputs/event_detection.csv)；[未知标签界限](../outputs/unknown_label_bounds.csv)；'
        '[覆盖](../outputs/coverage.csv)；[完整验收](../outputs/verdict.json)；[事前方案](../research_plan.md)。\n')
    (r/'market_context_observation.md').write_text(text)
    (ROOT/'README.md').write_text('# EP32 V9\n\n[市场阶段与行业早期识别](reports/market_context_observation.md)。\n\n'
        '顺序运行src/experiment9.py、src/score9.py、src/report9.py、src/validate9.py；实验使用RD-Agent虚拟环境。'
        '私有面板保存在context_v9缓存，前版保留。\n')
    print(status,flush=True)


if __name__=='__main__':run()

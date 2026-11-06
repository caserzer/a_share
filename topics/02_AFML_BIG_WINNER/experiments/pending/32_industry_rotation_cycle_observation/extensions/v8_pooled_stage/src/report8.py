import json
import pandas as pd
from context8 import ROOT,OUT,V7

NAMES={'prior':'历史先验','logistic':'原静态逻辑回归','static_tree':'原静态树','rd_selected':'原RD模型',
       'rd_gate':'V7简单阶段过滤','rd_state':'V7状态树','rd_conditional':'V7条件树',
       'pool_logistic':'共享简化逻辑回归','pool_tree':'共享状态树','pool_blend':'50%逻辑回归+50%阶段过滤'}


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def run():
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    m=pd.read_csv(OUT/'metrics.csv');a=pd.read_csv(OUT/'annual_metrics.csv');tests=pd.read_csv(OUT/'primary_tests.csv')
    verdict=json.loads((OUT/'verdict.json').read_text())
    keys=['cohort','frequency','threshold','benchmark','level']
    for name,alias in [('rd_selected','rd'),('rd_gate','gate')]:
        ref=m[m.model.eq(name)][keys+['brier']].rename(columns={'brier':alias+'_brier'})
        m=m.merge(ref,on=keys,validate='many_to_one');m[alias+'_gain']=1-m.brier/m[alias+'_brier']
    m.to_csv(OUT/'matched_comparisons.csv',index=False)
    cols=['brier','rd_gain','gate_gain','top10_precision','top10_lift']
    overall=m.groupby(['cohort','model'])[cols].mean().reset_index();overall.to_csv(OUT/'overall.csv',index=False)
    summary=m.groupby(['cohort','frequency','model'])[cols].mean().reset_index();summary.to_csv(OUT/'summary.csv',index=False)
    d=overall[overall.cohort.eq('fixed24')].set_index('model').reindex(NAMES).reset_index()
    table=pd.DataFrame({'方法':d.model.map(NAMES),'Brier':d.brier.map(lambda x:f'{x:.6f}'),
        '相对原RD改善':d.rd_gain.map(lambda x:f'{x:+.2%}'),'相对简单过滤改善':d.gate_gain.map(lambda x:f'{x:+.2%}'),
        '前10%命中率':d.top10_precision.map(lambda x:f'{x:.2%}'),'提升倍数':d.top10_lift.map(lambda x:f'{x:.2f}')})
    keys+=['year']
    for name,alias in [('rd_selected','rd'),('rd_gate','gate')]:
        ref=a[a.model.eq(name)][keys+['brier']].rename(columns={'brier':alias+'_brier'})
        a=a.merge(ref,on=keys,validate='many_to_one');a[alias+'_gain']=1-a.brier/a[alias+'_brier']
    annual=a.groupby(['cohort','year','frequency','model'])[cols].mean().reset_index();annual.to_csv(OUT/'annual_summary.csv',index=False)
    rows=[];passed=[]
    for name,v in verdict['frequency_gates'].items():
        for freq,g in v.items():
            rows.append({'方法':NAMES[name],'频率':freq,'通过阈值':','.join(f'{x:.0%}' for x in g['passed_thresholds']) or '无','完整验收':'通过' if g['passed'] else '未通过'})
            if g['passed']:passed.append(f'{NAMES[name]}（{freq}）')
    status='达到完整历史验收的组合：'+('；'.join(passed) if passed else '无')+'。'
    t=pd.DataFrame({'方法':tests.candidate.map(NAMES),'较简单过滤的绝对Brier增量':tests.effect.map(lambda x:f'{x:+.6f}'),
        '95%区间':[f'[{x:+.6f},{y:+.6f}]' for x,y in zip(tests.ci_low,tests.ci_high)],
        '跨轮12项BH的q':tests.q_bh.map(lambda x:f'{x:.3f}'),'支持增量':tests.supported.map({True:'是',False:'否'})})
    text=('# EP32 V8：共享样本、简化模型与稳定性\n\n'+status+'\n\n'
        'V7的阶段过滤是已确认的相对改进，但状态树在部分年份概率偏高。本轮把同一行业同日的重复频率训练记录去重，'
        '共享一个简化条件逻辑回归或固定状态树，并检验与简单过滤各50%的保守融合。权重和参数在结果计算前固定。\n\n'
        +md(table)+'\n'
        '主表使用相同观察样本、相同标签、相同前10%预算。相对值先在频率/阈值/基准/行业层级任务内计算，再等权平均；'
        '不同列不能用总体平均数相除来重算。主要评价2021-01-01至2024-09-30，每条统一24个月跟踪，未解决标签仍为未知。\n\n'
        +md(pd.DataFrame(rows))+'\n'
        '完整验收保持严格：Brier低于先验、原静态逻辑回归、静态树、原RD模型及V7简单过滤；前10%命中率至少2倍于同日基准率；'
        '至少两个可评价年度且每个可评价年度均优于上述五个基线；每个频率至少两个阈值在两个基准下成立，并通过增量统计检验。\n\n'
        +md(t)+'\n'
        '显著性按市场月份连续三个月成块重抽样；本轮把V6六项、V7三项和V8三项共12项一起BH校正，'
        '避免每试一轮就重新采用较小检验族。V7已经披露的结果保持原样。\n\n'
        '不能把历史改进说成独立确认：2021—2022用于过旧模型选择，2024亦曾被查看；2021年分类断点导致标签已知覆盖约37%。'
        '主指标条件于可解决标签，未知范围见[命中率界限](../outputs/unknown_label_bounds.csv)和[完整覆盖](../outputs/coverage.csv)。'
        'legacy_current是原2024年至数据末端口径，只作对照；2026正例不足以验证稳定性。\n\n'
        '阶段状态反映价格路径，不能证明需求或盈利改善。严格PIT仍为BLOCKED_DATA，独立前瞻验证为FORWARD_PENDING。\n\n'
        '[逐年结果](../outputs/annual_summary.csv)；[逐频率结果](../outputs/summary.csv)；'
        '[周期去重后的检出与延迟](../outputs/event_detection.csv)；[验收明细](../outputs/verdict.json)；'
        '[固定方案](../research_plan.md)；[V7完整结果](../../v7_online_stage/reports/online_stage_observation.md)。\n')
    (reports/'pooled_stage_observation.md').write_text(text)
    (ROOT/'README.md').write_text('# EP32 V8\n\n[共享模型与稳定性结果](reports/pooled_stage_observation.md)。\n\n'
        '先运行src/experiment8.py（RD-Agent虚拟环境），再运行src/score8.py、src/report8.py、src/validate8.py。'
        '只读复用V7在线阶段和冻结基线，私有面板位于pooled_v8缓存。\n')
    print(status,flush=True)


if __name__=='__main__':run()

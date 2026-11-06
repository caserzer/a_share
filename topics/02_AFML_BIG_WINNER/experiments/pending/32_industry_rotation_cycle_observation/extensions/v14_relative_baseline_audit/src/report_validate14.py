from pathlib import Path
import sys,json,re
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs';E=ROOT.parent
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import sha,js


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def run():
    summary=pd.read_csv(OUT/'summary.csv');tasks=pd.read_csv(OUT/'task_year_comparisons.csv')
    years=pd.read_csv(OUT/'year_frequency_comparisons.csv');reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    names={'rd_gate':'简单阶段过滤','risk_blend':'50%风险模型+50%阶段过滤','risk_prior_blend':'风险模型+阶段过滤+先验'}
    d=summary[summary.model.isin(names)].copy()
    table=pd.DataFrame({'方法':d.model.map(names),'较原RD误差改善':d.rd_gain.map(lambda x:f'{x:.2%}'),
        '前10%命中率':d.top10_precision.map(lambda x:f'{x:.2%}'),'提升倍数':d.top10_lift.map(lambda x:f'{x:.2f}'),
        '优于原RD的可评价组合':[f'{int(a)}/{int(b)}' for a,b in zip(d.improved_task_years,d.evaluable_task_years)],
        '最差组合变化':d.worst_relative_gain.map(lambda x:f'{x:+.2%}'),'39项校正q':d.q_bh_39.map(lambda x:f'{x:.3f}')})
    bad=tasks[tasks.model.eq('risk_blend')&tasks.evaluable&tasks.relative_gain.le(0)].copy()
    bad['relative_gain']=bad.relative_gain.map(lambda x:f'{x:+.2%}')
    annual=years[years.model.eq('risk_blend')][['year','frequency','rd_gain','top10_precision','top10_lift']].copy()
    for c in ['rd_gain','top10_precision']:annual[c]=annual[c].map(lambda x:f'{x:.2%}')
    annual['top10_lift']=annual.top10_lift.map(lambda x:f'{x:.2f}')
    text=('# EP32 V14：相对原RD基线的稳定性与原门槛分开审计\n\n'
        '**在已解决标签的历史样本中，已找到稳定优于原RD的固定方法；原完整验收门槛仍未通过。** '
        '不能用前一结论替代后一结论，也不能声称独立前瞻确认。\n\n'
        '若优先考虑相对原RD的稳定性，风险模型与阶段过滤各50%的固定融合值得保留；'
        '它在69个可评价任务年度中67个误差更低，最差回退约1.62%。风险/过滤/先验的组合命中率略高，但回退组合更多。\n\n'
        +md(table)+'\n'
        '原RD在同样主样本中的前10%已知标签命中率为7.73%。任务是频率×回撤阈值×基准；'
        '任务年度可评价要求至少6个观察日期、两行业层级合计至少10个已知正例。69个组合相互重叠，不能看成69次独立试验。'
        '表内误差相对改善先在细任务中计算再平均；统计检验另按市场月份聚合。\n\n'
        '50%固定融合的逐年、逐频率汇总：\n\n'+md(annual)+'\n'
        '其两个回退任务的原值完整列示：\n\n'+md(bad[['frequency','threshold','benchmark','year','brier','rd_brier','relative_gain']])+'\n'
        '周期层面也存在取舍：任务等权的事件检出率从原RD约36.96%升至固定50%融合的45.83%；'
        '各任务内首次检出的中位延迟再取平均，从约32.61天变为37.88天。融合检出更多周期，但通常晚一些；'
        '这仍在前三个月定义内，不是提前一个月预测启动。原始分任务数据见[事件结果](../../v13_completed_history/outputs/event_detection.csv)。\n\n'
        '方法执行顺序：\n\n'
        '1. 按原历史行业成员篮子更新净值，只用截至观察日的价格维护候选低点和已确认上行起点。\n'
        '2. 如果已不可能处于起点后三个日历月，概率置零；其他行业保留原RD的概率，得到简单阶段过滤概率。\n'
        '3. 使用原V8的19个状态/价格特征，加V12固定的八个波动尺度变量，按季度只用当时已成熟标签拟合固定树。频率重合记录先去重。\n'
        '4. 输出概率为上述风险树与简单过滤各50%，权重没有按年度结果调整。周/双周/月观察仍分别更新，按日期/行业层级选前10%。\n\n'
        '这不是识别基本面盈利景气，也不是保证以后持续上涨；目标仍是事后可被确认的6—18个月价格阶段起点后三个月。'
        '此前采用的2倍提升、逐年优于所有基线、两阈值与两市场基准完整门槛，三种方法均未通过。\n\n'
        '相对原RD的全部18个候选一并审计，并与不重复的旧检验一起校正，共39项。'
        '设计已经多次看过这些历史，校正不能消除探索性；此审计的q值不替换原来“相对简单过滤增量”的失败结果。\n\n'
        '主要评价2021年至2024年9月，统一24个月跟踪；2021分类断点使已知标签覆盖约37%，未解决标签保留未知。'
        '底层训练数据从2017年起，严格PIT仍BLOCKED_DATA，独立前瞻验证FORWARD_PENDING。\n\n'
        '[全部候选稳定性](../outputs/summary.csv)；[所有任务年度](../outputs/task_year_comparisons.csv)；'
        '[月份差值](../outputs/monthly_relative_rd.csv)；'
        '[V12原始完整验收](../../v12_duration_risk/outputs/verdict.json)；'
        '[固定模型实现](../../v12_duration_risk/src/experiment12.py)。\n')
    (reports/'relative_baseline_stability.md').write_text(text)
    (ROOT/'README.md').write_text('# EP32 V14\n\n[相对原RD的稳定性审计](reports/relative_baseline_stability.md)。\n\n'
        '运行src/audit14.py后运行src/report_validate14.py。不新增预测模型，不替换原完整门槛。\n')
    checks=[]
    def check(name,ok):
        assert bool(ok),name
        checks.append(name)
    audit=json.loads((OUT/'audit.json').read_text())
    check('frozen audit code',sha(ROOT/'src/audit14.py')==audit['code_sha256'])
    check('all read monthly inputs unchanged',all(sha(p)==h for p,h in audit['inputs'].items()))
    previous=json.loads((OUT/'predecessors.json').read_text())
    check('all older research unchanged',all(sha(p)==h for p,h in previous.items()))
    check('eighteen candidates reported',len(summary)==18 and summary.model.nunique()==18)
    r=summary.set_index('model').loc['risk_blend']
    check('67 of 69 improved',r.evaluable_task_years==69 and r.improved_task_years==67)
    check('two negative cells preserved',len(bad)==2)
    check('every year-frequency aggregate improves',years.loc[years.model.eq('risk_blend'),'rd_gain'].gt(0).all())
    check('original complete gate remains fail',json.loads((E/'v12_duration_risk/outputs/verdict.json').read_text())['status']=='NO_SATISFACTORY_RESULT')
    for p in ROOT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if '://' in target or target.startswith('#'):continue
            check('link '+str(p.relative_to(ROOT))+' '+target,(p.parent/target.split('#')[0]).exists())
    js(OUT/'validation.json',dict(status='PASS',checks=checks,checks_count=len(checks),original_gate_passed=False,independent_holdout=False))
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and p.name!='manifest.json' and not any(x in p.parts for x in ['__pycache__','.pytest_cache'])]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files),bytes=sum(f['bytes'] for f in files)))
    print('V14 audit PASS',len(checks),'checks;',len(files),'files',flush=True)


if __name__=='__main__':run()

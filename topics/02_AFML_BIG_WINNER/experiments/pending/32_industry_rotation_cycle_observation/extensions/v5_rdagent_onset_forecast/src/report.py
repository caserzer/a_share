"""Research delivery including failed hypotheses, maturity and frequency comparisons."""
import json
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import CACHE, ROOT, OUT, EP, sha, js, verify_predecessors
from outer import evaluate_rows


def table(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def supplement(stage):
    dest=OUT/f'stage_{stage}';receipt=json.loads((dest/'prediction_receipt.json').read_text())
    p=pd.read_parquet(receipt['path']);assert sha(receipt['path'])==receipt['sha256']
    lab=pd.read_parquet(CACHE/('labels.parquet' if stage=='a' else 'stage_b_labels.parquet'))
    merged=p.merge(lab,on=['row_id','threshold','benchmark'],validate='many_to_one')
    known=merged[merged.y.notna()].copy();known['loss']=(known.prob-known.y)**2
    keys=['frequency','threshold','benchmark','level','date']
    daily=known.groupby(keys+['model']).loss.mean().unstack('model')
    contrast=daily[['prior','logistic','static_tree']].sub(daily.rd_selected,axis=0).reset_index()
    contrast['month']=contrast.date.dt.to_period('M').astype(str)
    monthly=contrast.groupby(['frequency','month'])[['prior','logistic','static_tree']].mean()
    rng=np.random.default_rng(32);bounds=[]
    for frequency,g in monthly.groupby(level=0):
        for comparator in ['prior','logistic','static_tree']:
            v=g[comparator].to_numpy();samples=rng.choice(v,size=(1000,len(v)),replace=True).mean(axis=1)
            bounds.append(dict(frequency=frequency,comparator=comparator,months=len(v),
                monthly_equal_weight_brier_improvement=v.mean(),ci025=np.quantile(samples,.025),ci975=np.quantile(samples,.975)))
    pd.DataFrame(bounds).to_csv(dest/'month_block_uncertainty.csv',index=False)
    dates={freq:set(g.date) for freq,g in p.groupby('frequency')};common=set.intersection(*dates.values())
    rows=[]
    for key,g in known[known.date.isin(common)].groupby(['frequency','threshold','benchmark','model']):
        for r in evaluate_rows(g):r.update(zip(['frequency','threshold','benchmark','model'],key));rows.append(r)
    pd.DataFrame(rows).to_csv(dest/'identical_origin_metrics.csv',index=False)
    js(dest/'identical_origin_audit.json',dict(dates=sorted(str(x.date()) for x in common),
        count=len(common),note='exact common issuance dates only; small diagnostic sample, not a replacement holdout'))
    selected=p[p.model.eq('rd_selected')].copy()
    last=selected.groupby(['frequency','threshold','benchmark','level']).date.transform('max')
    selected=selected[selected.date.eq(last)]
    names=pd.read_parquet(CACHE/'features.parquet',columns=['row_id','industry_name'])
    selected.merge(names,on='row_id',validate='many_to_one').to_csv(dest/'last_available_research_scores.csv',index=False)
    runtime=json.loads((dest/'runtime.json').read_text())
    token_files=list(Path(runtime['trace']).glob('**/token_cost/**/*.pkl'))
    token_rows=[pickle.loads(x.read_bytes()) for x in token_files]
    js(dest/'llm_accounting.json',dict(native_token_records=len(token_rows),
        estimated_prompt_tokens=sum(int(x.get('prompt_tokens',0)) for x in token_rows),
        estimated_completion_tokens=sum(int(x.get('completion_tokens',0)) for x in token_rows),
        token_source='RD-Agent tokenizer estimates; not provider usage receipts',
        provider_billed_cost=None,provider_cost_status='not independently verified; native zero cost is not free billing',
        request_files=len(list((dest/'llm').glob('*_request.json'))),
        response_files=len(list((dest/'llm').glob('*_response.txt')))))
    rounds=[]
    for path in sorted((dest/'candidates').glob('rd_*/summary.json')):
        candidate=path.parent.name;number=int(candidate.split('_')[-1])
        spec=json.loads((path.parent/'spec.json').read_text());summary=json.loads(path.read_text())
        decision=json.loads((path.parent/'decision.json').read_text())
        responses=sorted((dest/'llm').glob(f'round_{number:02d}_*_response.txt'))
        hypothesis=reason=''
        if responses:
            raw=responses[-1].read_text().strip()
            if raw.startswith('```'):raw=raw.split('\n',1)[1].rsplit('```',1)[0]
            reply=json.loads(raw);hypothesis=reply.get('hypothesis','');reason=reply.get('reason','')
        rounds.append(dict(round=number+1,candidate=candidate,hypothesis=hypothesis,reason=reason,
            model=spec['model'],features=len(spec['features']),inner_brier_skill=summary['objective'],
            replaces_previous_best=decision['decision'],selected=candidate==json.loads((dest/'frozen_selection.json').read_text())['winner']['candidate']))
    pd.DataFrame(rounds).to_csv(dest/'round_inventory.csv',index=False)
    phases=pd.read_parquet(CACHE/'daily_phases.parquet')
    groups={k:g.to_dict('records') for k,g in phases.groupby(['era','level','industry_code','threshold'])}
    false=merged[merged.model.eq('rd_selected') & merged.alert & merged.y.eq(0)].copy()
    reasons=[]
    for r in false.itertuples():
        s=groups.get((r.era,r.level,r.industry_code,r.threshold),[])
        lo=r.date if stage=='a' else r.date-pd.DateOffset(months=3)
        hi=r.horizon_end
        inside=[x for x in s if lo<x['start_date']<=hi and x['status']=='CONFIRMED' and not x['left_censored']]
        good=[x for x in inside if x['industry_return']>0 and x['industry_return']>x['benchmark_return_'+r.benchmark]]
        if any(x['end_date']>x['start_date']+pd.DateOffset(months=18) for x in good):reason='UP_AND_BEAT_BUT_LONG_GT18'
        elif any(x['end_date']<x['start_date']+pd.DateOffset(months=6) for x in good):reason='UP_AND_BEAT_BUT_SHORT_LT6'
        elif inside:reason='NO_QUALIFYING_RELATIVE_RETURN'
        else:reason='NO_CONFIRMED_ONSET_IN_TARGET_WINDOW'
        reasons.append(reason)
    false['diagnostic_reason']=reasons
    false.groupby(['frequency','threshold','benchmark','level','diagnostic_reason']).size().rename('false_alerts').reset_index().to_csv(dest/'false_alert_diagnostics.csv',index=False)


def build():
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    summaries=[];pass_any=False;plotdata=[]
    for stage in ['a','b']:
        dest=OUT/f'stage_{stage}'
        if not (dest/'verdict.json').exists():continue
        supplement(stage)
        verdict=json.loads((dest/'verdict.json').read_text())
        selection=json.loads((dest/'frozen_selection.json').read_text())
        metrics=pd.read_csv(dest/'frequency_metrics.csv')
        view=metrics[metrics.model.eq('rd_selected')].groupby('frequency').agg(
            base_rate=('prevalence','mean'),brier_skill=('brier_skill','mean'),
            precision=('top10_precision','mean'),lift=('top10_lift','mean'),pr_auc=('pr_auc','mean')).reset_index()
        view['gate']=view.frequency.map(lambda x:'通过探索性门槛' if verdict['frequency_gates'][x]['passed'] else '未通过')
        display=pd.DataFrame({'频率':view.frequency.map({'W':'周','BW':'双周','M':'月'}),
            '基准正例率':view.base_rate.map(lambda x:f'{x:.2%}'),
            'Brier相对先验改善':view.brier_skill.map(lambda x:f'{x:+.2%}'),
            '前10%候选命中率':view.precision.map(lambda x:f'{x:.2%}'),
            '命中率提升倍数':view.lift.map(lambda x:f'{x:.2f}'), '验收':view.gate})
        title='未来1个月内启动' if stage=='a' else '识别启动后前3个月'
        done=json.loads((dest/'run_complete.json').read_text())
        completed=done['completed_history']
        candidates=list((dest/'candidates').glob('rd_*/summary.json'))
        text=(f'# 阶段{stage.upper()}：{title}\n\n'
            f'原生RD-Agent完成{completed}轮，取得{len(candidates)}份可评分候选反馈。'
            f'内验证选中 `{selection["winner"]["candidate"]}`，配置在外层评分前冻结。\n\n'+table(display)+
            '\n表中先按观察日等权、再按行业层级/转折阈值/基准任务等权汇总。'
            '“Brier相对先验改善”为1减模型误差/先验误差，正数才是改善；'
            '前10%候选在全部可预测行业中先排名，再仅用已成熟标签评分，未知不能当负例。'
            '提升倍数是各任务比值的均值，未必等于两列平均命中率直接相除。\n\n'
            '实际门槛逐基准、逐阈值判断：同时胜过先验、逻辑回归、静态树模型，命中率提升至少2倍，'
            '并有至少两个可评分年份持续改善；两基准均满足、至少两个转折阈值通过，才算该频率通过。'
            '因此汇总均值为正也不能自动通过。\n\n'
            f'[逐频率阈值基准指标](../outputs/stage_{stage}/frequency_metrics.csv)；'
            f'[年度指标](../outputs/stage_{stage}/annual_metrics.csv)；'
            f'[完整门槛裁决](../outputs/stage_{stage}/verdict.json)；'
            f'[样本与未成熟告警](../outputs/stage_{stage}/outer_coverage.csv)。\n\n'
            f'[误报原因分解](../outputs/stage_{stage}/false_alert_diagnostics.csv)：'
            '本任务的0仅表示没有命中“6—18个月且跑赢”的目标，不能解释成行业没有上涨。'
            '后续上涨且跑赢但短于6月或长于18月的告警单独列示；长行情仍不拆分。\n\n'
            f'[事件去重与提前天数](../outputs/stage_{stage}/event_detection.csv)：'
            '同一景气段被连续多次预测只记一次。阶段B的负提前天数表示启动后的识别滞后，不是提前预测。\n\n'
            f'[同一观察日期比较](../outputs/stage_{stage}/identical_origin_metrics.csv)、'
            f'[共同日期清单](../outputs/stage_{stage}/identical_origin_audit.json)；'
            '只用周、双周、月度实际发行日交集，样本较少，不用频率更密冒充独立证据更多。\n\n'
            f'[市场月份成块重抽样](../outputs/stage_{stage}/month_block_uncertainty.csv)为等月诊断区间，'
            '没有将同日多个行业或重叠标签当作独立样本，也没有声称对30轮搜索完成独立统计确认。\n\n'
            f'[最后可用日期的全行业研究分数](../outputs/stage_{stage}/last_available_research_scores.csv)'
            '明确标注各自预测日期，不能称作2026年11月实时信号，也没有经过独立概率校准确认。\n\n'
            f'[冻结配置](../outputs/stage_{stage}/frozen_selection.json)、'
            f'[30轮逐项假设与结果](../outputs/stage_{stage}/round_inventory.csv)、'
            f'[预测先落盘凭证](../outputs/stage_{stage}/prediction_receipt.json)、'
            f'[RD-Agent原生循环凭证](../outputs/stage_{stage}/run_complete.json)。\n')
        if stage=='b':text+='\n阶段B因阶段A未通过才启动，已经复用历史外层时期，只能称二次探索，不能升级为独立验证。\n'
        (reports/f'stage_{stage}.md').write_text(text)
        summaries.append(f'阶段{stage.upper()}：{title}\n\n'+table(display))
        plotdata.append((stage,pd.read_csv(dest/'round_inventory.csv'),view))
        pass_any |= verdict['status']=='EXPLORATORY_GATE_PASS'
    data=json.loads((OUT/'daily_input_audit.json').read_text())
    text=('# EP32 V5：RD-Agent 行业价格景气研究\n\n'
        '用户确认先用30轮预测未来1个月内启动；全部频率未通过验收才转向景气早期识别。'
        '周、双周、月度改变更新频率，目标期限一致。覆盖所有有可用价格路径的二级、三级行业，未只研究半导体或通信。\n\n'+
        '\n'.join(summaries)+'\n'
        f'冻结输入覆盖{data["calendar_start"]}—{data["calendar_end"]}，读取{data["stock_partitions"]}个证券日线分区，'
        f'重建{data["daily_industry_rows"]}条行业日线；{data["monthly_reconciliation_rows"]}条完整月份收益与V4逐条对齐。'
        '本轮转折从日线识别，不能把阶段数量与V4月线阶段直接作同口径比较。\n\n'
        '训练只接收当时已成熟标签，正例等到段末回撤确认；负例需要后续低点确认见证。'
        '搜索反馈限于2021—2022年，成熟截止2024年初；外层2024年起按季度滚动，预测先封存再评分。'
        '原V4看过全期间现象，所以外层仍为探索性历史回放；真正前瞻必须用配置冻结后的新数据。\n\n'
        '分类成员没有完整原始known_at版本，复权价格也是历史推断，严格PIT仍为BLOCKED_DATA。'
        '本轮价格景气不等同基本面景气，尚未引入财报公告、订单、库存或利润修订。\n\n'
        '搜索空间是23个历史价格、波动、成交、行业宽度和市场相对强弱特征，最多8个受限组合表达式，'
        '模型限逻辑回归和小容量梯度提升树。每轮只提交一个配置；失败或不改善都保留。'
        '未通过仅代表本次数据与搜索范围内未取得满意结果，不能推出行业景气原则上不可预测。\n\n'
        '实现复用[Microsoft RD-Agent](https://github.com/microsoft/RD-Agent)的原生研发循环，'
        '本地固定提交及适配差异哈希保存在runtime.json；行业标签和成熟评估由本实验专用Scenario提供。\n\n'
        '[阶段A详细报告](stage_a.md)；'+ ('[阶段B详细报告](stage_b.md)；' if (reports/'stage_b.md').exists() else '')+
        '[执行方案](../research_plan.md)。\n')
    (reports/'rdagent_observation.md').write_text(text)
    fig,axes=plt.subplots(1,len(plotdata),figsize=(6*len(plotdata),4),squeeze=False,layout='constrained')
    for ax,(stage,rounds,view) in zip(axes[0],plotdata):
        ax.plot(rounds['round'],100*rounds.inner_brier_skill,label='Inner feedback candidate')
        ax.plot(rounds['round'],100*rounds.inner_brier_skill.cummax(),label='Best inner feedback',linestyle='--')
        ax.axhline(100*view.brier_skill.mean(),color='red',label='Frozen outer replay average')
        ax.axhline(0,color='gray',linewidth=.7)
        ax.set(title='Stage '+stage.upper()+': search vs later replay',xlabel='RD-Agent round',ylabel='Brier skill vs prior (%)')
        ax.legend(fontsize=8)
    figures=reports/'figures';figures.mkdir(exist_ok=True)
    fig.savefig(figures/'search_and_replay.png',dpi=150);plt.close(fig)
    with (reports/'rdagent_observation.md').open('a') as handle:
        handle.write('\n![内验证搜索与冻结后历史回放](figures/search_and_replay.png)\n\n'
            '图中搜索与回放来自不同时期，不能把搜索曲线持续改善直接当成外层有效；'
            '不同频率的外层值在图中仅作等任务均值展示，验收仍逐项执行。\n')
    (ROOT/'README.md').write_text('# EP32 V5\n\n[完整报告](reports/rdagent_observation.md)；[冻结方案](research_plan.md)。\n\n'
        '项目虚拟环境运行data.py、labels.py；RD-Agent虚拟环境运行engine.py、run_agent.py、outer.py。'
        '阶段A全部未通过后，依次early_labels.py、engine.py --stage-b、run_agent.py --stage-b、outer.py --stage-b。'
        '最后运行report.py与validate.py。大型面板、原生trace和完整预测在私有缓存中。\n')
    assert verify_predecessors()
    js(OUT/'report_status.json',dict(strict_PIT='BLOCKED_DATA',independent_confirmation=False,
        any_exploratory_gate_pass=pass_any,original_versions_unchanged=True))


if __name__=='__main__':build()

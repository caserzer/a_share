from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs';EP=ROOT.parents[1]
CACHE=Path.home()/'.cache/a_share/ep32/error_v11'
sys.path.insert(0,str(ROOT.parent/'v5_rdagent_onset_forecast/src'))
from common import sha,js


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def run():
    audit=json.loads((OUT/'audit.json').read_text());x=pd.read_parquet(CACHE/'alert_attribution.parquet')
    checks=[]
    def check(name,ok):
        assert bool(ok),name
        checks.append(name)
    check('frozen diagnostic input',sha(CACHE/'alert_attribution.parquet')==audit['saved_attribution_sha256'])
    check('frozen diagnostic source',sha(ROOT/'src/audit11.py')==audit['code_sha256'])
    previous=json.loads((OUT/'predecessors.json').read_text())
    check('all prior versions unchanged',all(sha(p)==h for p,h in previous.items()))
    check('unknown never relabeled negative',x.category.eq('UNKNOWN').equals(x.y.isna()))
    check('positive classification matches labels',x.category.eq('TRUE_EARLY').equals(x.y.eq(1)))
    check('no unexplained known false observations',not x.category.eq('OTHER_KNOWN_FALSE').any())
    short=x[x.category.eq('SHORT_PHASE')];long=x[x.category.eq('LONG_PHASE')]
    check('short phases outside calendar duration range',short.in_range_6_18.eq(False).all() and short.duration_days.lt(185).all())
    check('long phases outside calendar duration range',long.in_range_6_18.eq(False).all() and long.duration_days.gt(540).all())
    check('all models keep same alert budget',x.groupby('model').size().nunique()==1)
    check('known label followup bounded',x.loc[x.y.notna(),'label_available_at'].le(x.loc[x.y.notna(),'date']+pd.DateOffset(months=24)).all())
    false=x[x.y.eq(0)]
    d=false.groupby(['model','category']).size().rename('observations').reset_index()
    d['fraction_of_known_false']=d.observations/d.groupby('model').observations.transform('sum')
    d.to_csv(OUT/'known_false_summary.csv',index=False)
    x[x.phase_id.notna()].groupby(['model','category']).phase_id.nunique().rename('distinct_phase_ids').reset_index().to_csv(OUT/'matched_phase_counts.csv',index=False)
    names={'CANDIDATE_LOW_NOT_FINAL':'候选低点未成为最终起点','SHORT_PHASE':'不足6个月','LONG_PHASE':'超过18个月',
        'NOT_OUTPERFORMING':'期限合格但未跑赢市场','OUTSIDE_EARLY_STATE':'不在可行早期位置','ZERO_PROBABILITY_BUDGET_FILL':'零概率预算补位'}
    view=d[d.model.eq('rd_gate')].copy();view['category']=view.category.map(names);view['fraction_of_known_false']=view.fraction_of_known_false.map(lambda v:f'{v:.2%}')
    view=view.drop(columns='model').rename(columns={'category':'已知误报原因','observations':'观察次数','fraction_of_known_false':'占已知误报'})
    report=ROOT/'reports';report.mkdir(exist_ok=True)
    text=('# EP32 V11：稳定性探索汇总与误报归因\n\n'
        '**目前只确认了简单阶段过滤相对原RD模型的稳定改进；完整识别标准尚未达到，目标继续进行。**\n\n'
        'V7—V10共固定比较12项新候选，未修改6—18个月、前三个月早期和收益差标签，也未降低2倍命中率与跨年要求。'
        '主要评价统一为2021年至2024年9月、24个月标签跟踪，使用既有2017年起数据训练。\n\n'
        '|方法|相对原RD的平均任务Brier改善|前10%已知标签命中率|完整验收|\n|---|---|---|---|\n'
        '|原RD模型|—|7.73%|未通过|\n|简单阶段过滤|2.48%|10.02%|未通过|\n'
        '|共享状态树|6.40%|12.12%|未通过，跨年不稳定|\n'
        '|训练等待12个月|3.69%|10.65%|未通过|\n\n'
        '简单过滤只剔除在当时价格路径下已不可能属于起点后三个月的观察；在全部已知正例中没有误删。'
        '它的各年汇总误差均下降，但命中率提升仍不足2倍。复杂方法的较高总体改善不能替代逐年验收。\n\n'
        '为了定位失败，本轮将四种方法的前10%观察与事后阶段表匹配，仅作诊断。简单过滤的已知误报构成为：\n\n'
        +md(view)+'\n'
        '主要问题是短行情和未形成最终低点。未跑赢市场和超过18个月在已解决误报中占比较少；'
        '但未解决长周期仍在UNKNOWN，不能据此断言全体长行情很少。\n\n'
        '上表是重复观察计数，周频会比月频更密，不能当作独立周期或直接重算前表的日期等权命中率。'
        '真实阶段去重计数另存；尚未形成最终起点者不假造phase_id。事后归因绝不回灌预测特征。\n\n'
        '下一步的明确方向：检验波动率相对于转折阈值的尺度能否识别短行情风险，区分“刚启动”与“可能持续足够久”。'
        '这仍须固定规则后验证，不能把误报原因当成已找到可预测信号。\n\n'
        '[完整归因频数](../outputs/attribution_counts.csv)；[按年归因](../outputs/annual_counts.csv)；'
        '[已匹配阶段去重](../outputs/matched_phase_counts.csv)；'
        '[V7阶段状态](../../v7_online_stage/reports/online_stage_observation.md)；'
        '[V8共享模型](../../v8_pooled_stage/reports/pooled_stage_observation.md)；'
        '[V9市场阶段](../../v9_market_context/reports/market_context_observation.md)；'
        '[V10标签成熟](../../v10_label_delay/reports/label_delay_observation.md)。\n\n'
        '严格PIT仍为BLOCKED_DATA，历史已被反复查看，独立前瞻验证仍待进行；未知标签始终保留。\n')
    (report/'stability_progress.md').write_text(text)
    (ROOT/'README.md').write_text('# EP32 V11\n\n[稳定性探索进展与误报归因](reports/stability_progress.md)。\n\n'
        '先运行src/audit11.py，再运行src/report_validate11.py。事后阶段只用于诊断，私有逐条结果保存在error_v11缓存。\n')
    js(OUT/'validation.json',dict(status='PASS',checks=checks,checks_count=len(checks),rows=len(x),unknown=int(x.y.isna().sum()),strict_PIT='BLOCKED_DATA'))
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and p.name!='manifest.json' and not any(v in p.parts for v in ['__pycache__','.pytest_cache'])]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files),bytes=sum(p['bytes'] for p in files)))
    print('V11 attribution audited',len(checks),'checks',flush=True)


if __name__=='__main__':run()

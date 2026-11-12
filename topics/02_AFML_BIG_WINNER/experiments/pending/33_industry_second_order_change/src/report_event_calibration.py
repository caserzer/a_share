"""R16-R18 complete scorecards, release gates and probability reliability evidence."""
import json
import numpy as np
import pandas as pd
from pool_evaluation import EP

def pct(x):return '—' if pd.isna(x) else f'{100*x:.2f}%'
def pp(x):return '—' if pd.isna(x) else f'{100*x:+.2f}'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    tables=[];gates=[];snapshots=[];reliability=[];quarter=[]
    registry=pd.read_csv(EP/'outputs/r09/universe_registry.csv.gz',parse_dates=['date']);registry=registry[registry.date.eq(registry.date.max())]
    for round_id in ['r16','r17','r18']:
        out=EP/'outputs'/round_id;s=pd.read_csv(out/'summary.csv');scores=pd.read_parquet(out/'scored_outcomes.parquet');rows=[]
        for _,r in s[s.unit.eq('entry')&s.horizon.eq(126)].iterrows():
            rows.append([r.model,f'{int(r.wins)}/{int(r.known)}',int(r.total-r.known),pct(r.win_rate),pp(r.uplift),pct(r.success_week_recall),pct(r.calibration_gap),'通过' if r.accepted else '未通过'])
            gates.append(dict(round=round_id,model=r.model,protocol='pool_metric_v1',metric_pass=bool(r.accepted),failed_gates=r.failed_gates,production_authorized=False))
        tables.append(table(['版本','成功/成熟事件','结果未知','胜率','同期增量/百分点','成功机会周覆盖','入池校准误差','验收'],rows))
        for model,g in scores.groupby('model'):
            for scope,flag in [('candidates',g.candidate_event),('admitted',g.entry)]:
                k=g[flag&g.calibration_supported&g.probability.notna()&g.win126.notna()]
                for bin_value,a in k.groupby(pd.cut(k.probability,np.linspace(0,1,11),include_lowest=True),observed=True):
                    reliability.append(dict(round=round_id,model=model,scope=scope,bin=str(bin_value),known=len(a),wins=a.win126.sum(),mean_prediction=a.probability.mean(),actual=a.win126.mean()))
            for fold,a in g.groupby('fold'):
                cand=a[a.candidate_event&a.win126.notna()&a.probability.notna()];entered=a[a.entry&a.win126.notna()]
                quarter.append(dict(round=round_id,model=model,fold=fold,supported=bool(a.calibration_supported.all()),candidates=len(cand),candidate_prediction=cand.probability.mean(),candidate_actual=cand.win126.mean(),known_entries=len(entered),entry_prediction=entered.probability.mean(),entry_actual=entered.win126.mean()))
            cols=['date','era','industry_code','score','reference_probability','predicted_uplift','calibration_supported','score_domain','candidate_event','entry','admitted','opportunity_id','fold']
            z=registry.merge(g[g.date.eq(registry.date.max())][cols],on=['date','era','industry_code'],how='left',validate='one_to_one')
            z['round']=round_id;z['model']=model;z['production_authorized']=False
            z['score_status']=np.where(z.score.notna(),'EXPERIMENTAL_UNVALIDATED_PROBABILITY',np.where(z.calibration_supported.eq(False),'MODEL_CALIBRATION_UNKNOWN','UNKNOWN_PRICE_INPUT'))
            snapshots.append(z)
    pd.DataFrame(reliability).to_csv(EP/'outputs/event_probability_reliability.csv',index=False)
    pd.DataFrame(quarter).to_csv(EP/'outputs/event_probability_quarters.csv',index=False)
    pd.concat(snapshots,ignore_index=True).to_csv(EP/'outputs/event_probability_industry_scores.csv',index=False)
    (EP/'outputs/event_probability_release_gate.json').write_text(json.dumps({'protocol':'pool_metric_v1','thresholds_changed':False,'models':gates,'original_goal_complete':False},ensure_ascii=False,indent=2)+'\n')
    text='''# EP33 R16–R18：唯一事件概率校准的执行、反思与扩展

执行日期：2026-11-11。**完成三轮预登记实验，全部10个版本未通过原量化标准。** 原泛行业高胜率研究池目标保持开放，没有获准模型。

## 标准与时序纪律

原pool_metric_v1文件哈希与R12一致：126交易日行业上涨且跑赢中证全指；入池概率>=60%且高于同日全行业均值>=5个百分点；实际唯一入池胜率>=60%、同期增量>=5个百分点、成功行业周覆盖>=10%、成熟事件>=100、26周块95%增量区间下界>0、入池概率误差<=5个百分点。63/252日只作敏感性。

基础分数来自R12当时生成的封存预测。校准每季度只使用end126严格早于拟合日的历史记录，候选事件为当时可执行状态机生成，不用未来成功反选。校准训练纳入全部历史候选，而非仅曾被新模型接受的事件。每个候选只有一次决策，拒绝后同簇不择日重试。

事件映射只用于唯一候选决策行，其他行业周使用状态映射；当日全行业参考为各行实际条件下的预测均值。不能将事件条件概率外推为全部行业的无条件概率。事件/状态分数类型、拟合截止、校准支持情况均留档。

最初2024年缺少足够成熟事件或日期，整折保留MODEL_CALIBRATION_UNKNOWN，不回填预测，也不从全期成功机会覆盖分母删除；另作共同可评分日期比较。历史已被反复查看，全部是自适应历史模拟，不是独立前瞻验证。

## R16：把校准对象改为唯一事件

对levels/second两个基础模型分别比较：state_oof状态校准对照、event_offset事件截距校准、event_platt事件单调斜率及截距。固定正则强度、训练支持条件和门槛，无参数搜索。

'''+tables[0]+'''

关键反例：levels事件Platt在全部191个可校准成熟候选上平均预测54.13%、实际52.88%，均值误差仅1.25个百分点；但达到入池门槛的38个事件只有8次成功，实际21.05%，预测62.45%，误差41.40个百分点。**全候选均值校准良好不能替代高分入池可靠性。**

R15 levels全期59.69%，在本轮具备校准支持的相同日期为52.88%；新方法不能直接与包含2024年良好阶段的59.69%比较。即使纠正时间范围，新方法仍没有通过准入质量标准。

## R17：固定增加三个事件条件

根据R16反思，加入确认耗时、首次提示至确认的相对价格变化、确认时市场126日收益。只用当时可见值和已成熟历史事件拟合，标准化也不看测试数据。没有调整期限、模型基础分数或门槛。

'''+tables[1]+'''

有限事件条件没有建立高分优势。执行后补做容量审计，发现一个应该更早检查的约束：R16/R17只能从R15窄池再筛选，加上校准未知季度，接受全部可支持日期的父池状态也最多覆盖5.09%/4.88%的全期成功行业周，低于10%。这是本历史样本的确定性上限，不是未来市场断言。继续在该宇宙内调校准不可能通过覆盖验收。

## R18：扩大观察宇宙，但不降低正式入池门槛

解除旧模型60分对观察阶段的前置过滤，改用已有价格变化提示price_eligible且rate_change>0建立观察簇，第二次提示形成唯一候选。观察提示不是正式入池；正式准入仍必须通过新事件概率60分/+5个百分点及全部验收数值。沿用R17同样的事件模型、特征和正则，不重新拟合基础预测模型。

每个基础模型观察到1316个唯一候选，校准支持仍从2025Q1开始；覆盖上限增至20.15%，已高于10%。这解决了容量不可能达标的问题，但不是预测能力提升的证据。

'''+tables[2]+'''

levels188个成熟入池仅57次成功，second184个仅58次成功；平均预测约67%，实际仅30%–32%。当前高分选择没有形成可靠机会池，不能批准。所有原失败项和未知结果均保留。

## 本次反思与后续边界

本轮已把“针对唯一事件校准”落实为可运行、可追溯、严格成熟时间约束的模型，也检验了事件条件和观察容量。证据不支持通过继续调整这组固定分数的校准系数来获得高胜率。

下一步应回到唯一事件的预测模型本身：检验是否存在能稳定区分结果的新信息或建模方式，仍以原协议验收。当前结果不证明所有模型或二阶信息无效，但否定这些固定版本的准入资格。暂不继续遍历阈值、等待次数、主期限或收缩权重来凑达标。

一期完整循环的失败也是可复核结论，不等于原目标已经完成。只报告均值概率准确、候选数量扩大、某个正增量或单一高收益年份均不足以验收。

## 文件与管控

- [验收闸门](../outputs/event_probability_release_gate.json)：10个模型/事件版本全部未批准，正式生产授权为false。
- [全行业历史评分与唯一机会状态](../outputs/event_probability_industry_scores.csv)：2026-10-16的347行业×10版本；264行业可计算实验分数，83行业保留价格输入UNKNOWN，不是实时或已认证概率。
- [候选与准入概率分箱](../outputs/event_probability_reliability.csv)、[季度诊断](../outputs/event_probability_quarters.csv)。
- [R16完整指标](../outputs/r16/summary.csv)、[候选/准入诊断](../outputs/r16/event_calibration_diagnostics.csv)、[同期间对照](../outputs/r16/same_period_comparison.csv)。
- [R17指标](../outputs/r17/summary.csv)、[旧观察池容量上限](../outputs/r17/coverage_ceiling_audit.csv)。
- [R18指标](../outputs/r18/summary.csv)、[新观察池容量上限](../outputs/r18/coverage_ceiling_audit.csv)。
- [R16反思](../rounds/r16_reflection.md)、[R17反思](../rounds/r17_reflection.md)、[R18反思](../rounds/r18_reflection.md)。
- [R16验证](../outputs/r16/validation.json)、[R17验证](../outputs/r17/validation.json)、[R18验证](../outputs/r18/validation.json)。

28项测试通过。逐折核对校准行身份、成熟终点、状态/事件域，复算预测与验收算术，校验协议和封存文件哈希。评价验证通过不表示模型有效。没有新增采集、交易、部署、发送消息或Git发布。
'''
    (EP/'reports/event_calibration_r16_r18.md').write_text(text)
    print('R16-R18 report and model gates generated.')
if __name__=='__main__':main()

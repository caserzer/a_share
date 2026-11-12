"""R14-R15 report, unchanged-threshold release gates and historical score inventory."""
import json
import numpy as np
import pandas as pd
from pool_evaluation import EP

def pct(x):return '—' if pd.isna(x) else f'{100*x:.2f}%'
def pp(x):return '—' if pd.isna(x) else f'{100*x:+.2f}'
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    tables=[];gates=[];diag=[];quarter=[];snapshots=[]
    registry=pd.read_csv(EP/'outputs/r09/universe_registry.csv.gz',parse_dates=['date']);registry=registry[registry.date.eq(registry.date.max())]
    for round_id in ['r14','r15']:
        out=EP/'outputs'/round_id;s=pd.read_csv(out/'summary.csv');scores=pd.read_parquet(out/'scored_outcomes.parquet');rows=[]
        for _,r in s[s.unit.eq('entry')&s.horizon.eq(126)].iterrows():
            rows.append([r.model,f'{int(r.wins)}/{int(r.known)}',int(r.total-r.known),pct(r.win_rate),pp(r.uplift),pct(r.success_week_recall),pct(r.calibration_gap),'通过' if r.accepted else '未通过'])
            gates.append(dict(round=round_id,model=r.model,metric_pass=bool(r.accepted),production_authorized=False,failed_gates=r.failed_gates,protocol='pool_metric_v1'))
        tables.append(table(['模型/映射','成功/已知机会','未知','胜率','同期增量/百分点','成功行业周覆盖','校准误差','验收'],rows))
        for model,g in scores.groupby('model'):
            k=g[g.win126.notna()]
            diag.append(dict(round=round_id,model=model,known=len(k),brier=((k.probability-k.win126)**2).mean(),predicted=k.probability.mean(),actual=k.win126.mean(),outside_market_calibration_fraction=g.market_outside_cal_range.mean()))
            for fold,a in g.groupby('fold'):
                b=a[a.win126.notna()];quarter.append(dict(round=round_id,model=model,fold=fold,known=len(b),predicted=b.probability.mean(),actual=b.win126.mean(),entries=int(a.entry.sum()),pool_rows=int(a.admitted.sum())))
            cols=['date','era','industry_code','score','reference_probability','predicted_uplift','admitted','entry','fold']
            if 'opportunity_id' in g:cols+=['opportunity_id','raw_gate','state_edge']
            z=registry.merge(g[g.date.eq(registry.date.max())][cols],on=['date','era','industry_code'],how='left',validate='one_to_one')
            z['round']=round_id;z['model']=model;z['production_authorized']=False
            z['score_status']=np.where(z.score.notna(),'EXPERIMENTAL_UNVALIDATED_PROBABILITY','UNKNOWN_NO_VALID_INPUT')
            snapshots.append(z)
    pd.DataFrame(diag).to_csv(EP/'outputs/r14_r15_probability_diagnostics.csv',index=False)
    pd.DataFrame(quarter).to_csv(EP/'outputs/r14_r15_quarter_diagnostics.csv',index=False)
    pd.concat(snapshots,ignore_index=True).to_csv(EP/'outputs/r14_r15_industry_scores.csv',index=False)
    (EP/'outputs/r14_r15_release_gate.json').write_text(json.dumps({'protocol':'pool_metric_v1','thresholds_changed':False,'models':gates,'original_goal_complete':False},ensure_ascii=False,indent=2)+'\n')
    text='''# EP33 R14–R15：条件校准、唯一机会与二次确认

执行日期：2026-11-11。**已执行两轮反思驱动实验，量化验收标准未改，仍无模型通过。** R15一次性二次确认的较好版本为271/454=59.69%，不是达标的60%；同期增量和概率误差亦不合格。

## 固定目标与研究范围

未来126交易日行业收益>0且跑赢中证全指；信号后下一交易日收盘起算。实验入池分数>=60且概率高于同日全行业均值至少5个百分点；验收要求真实首次入池胜率>=60%、同期增量>=5个百分点、成功行业周覆盖>=10%、成熟事件>=100、26周时间块增量95%区间下界>0、入池平均概率校准误差<=5个百分点。

协议原文件哈希与R12保持一致。只使用既有历史数据，末期2026-10-16完整周；2024Q1起12季度历史模拟，历史已被多次查看，不是独立前瞻验证。所有固定分支和63/126/252日期限结果均保留。

## R14：校准与重复计数分开检验

保留原来的levels/second两个逻辑回归，不改变原模型训练。identity为R13复现；ridge_global为向恒等映射收缩的单调全局校准；ridge_market仅多加当时市场21/126日收益、63日波动和行业广度。两种新校准使用相同固定正则强度，不搜索参数。标准化只用当时成熟的校准数据，预测时超校准范围的比例另存。

'''+tables[0]+'''

市场条件校准改善了部分全局校准结果，但不能超过原始分数，更未达到验收标准。给校准增加当前市场变量不足以解决概率失真。

重复事件另分三类：原始首次进入、126交易日簇首、簇内重复；同时测试连续4个有效周离池后才重新激活。levels恒等映射簇首胜率44.24%、同期基准44.78%；重复部分胜率63.17%、同期基准58.60%。重复部分自身仍未通过增量与校准标准，也不能当独立新机会。冷却改变了入池时机和市场暴露，因此胜率下降不能全部归因于重复计数。

## 根据反思执行R15：每簇只在第二次确认时正式入池一次

第一个已知false→true提示进入观察；不足126交易日内第二个原始提示触发本簇唯一正式准入。第三次及以上只更新原机会，不增加样本。达到簇期限后必须有新的真实提示才能开始新机会；数据断档清空状态，未知边界不触发。该规则可逐周执行，未使用后续结果挑选哪次提示。

这轮改变的是具体准入流程，不是事后删除不利样本。原始分数、概率门槛和验收数值不变；正式研究池周覆盖按新流程重新计算，不借用R14的宽口径。

'''+tables[1]+'''

levels恒等映射观察736簇，577簇得到二次确认；454个入池结果已知、271个成功，剩余123个未成熟或缺失仍单列。增量+3.27个百分点，26周块区间约[-3.16,+7.56]个百分点；覆盖12.75%、已知数454通过对应门槛，但胜率、增量、置信区间和校准误差4项失败。

二阶特征版本只有56.76%的入池胜率，仍未显示稳定优势。某些市场条件分支增量超过5个百分点，但绝对胜率、覆盖和校准不满足要求，不能只报通过的一项。

## 确认代价、去重与年度稳定性

levels恒等映射等待中位数29交易日/6周，90%分位90.4交易日。期间行业涨幅中位数+0.59%，相对市场−0.60个百分点；并非总是追涨，但确实更晚。该流程是“观察后确认”，不能称为更早预测起点。

完整可观察126日窗口的607簇中499簇得到确认；另129簇窗口未完整或被截断，不能当作永久失败。完整簇与未完整簇、未确认簇全部保留在确认登记表。

同一最终确认簇在第一次提示和第二次入池的标签配对仅是事后描述；当时不知道哪些簇后来会确认，不能把这种条件化结果作为“第一次提示就只买这些行业”的策略。

每簇一次不保证相邻簇的126日结果窗口完全不重叠。追加正式入池126日冷却后，levels版本400个已知事件胜率58.50%、增量2.09个百分点、校准误差10.67个百分点，仍不过关。

levels唯一入池：2024已知263次胜率64.64%，2025已知161次59.01%，2026已成熟30次20.00%。2026未成熟居多，不代表全年；不能只选2024作为胜率。周状态126日64.46%和首次入池252日66.50%也不能替代已冻结的首次入池126日主指标。

## 当前结论与下一问题

校准问题未解决，重复问题已变成明确、可复核的机会身份与状态机。此次的改进是可验证的具体准入流程，不是已建立高胜率优势。

下一项值得检验的是“面向唯一入池事件的时序概率校准”：当前模型/校准主要拟合全行业周状态，而实际验收发生在筛选后的事件。只能用历史模型事前生成、当时已成熟的事件预测训练校准，不能拿本轮测试事件校准自身。暂不继续遍历确认次数、阈值、冷却长度或正则强度。

## 交付与复核

- [模型验收闸门](../outputs/r14_r15_release_gate.json)：12个模型/流程组合均未通过，无生产批准。
- [全行业历史分数与机会状态](../outputs/r14_r15_industry_scores.csv)：347行业×12组合，264行业每组合有实验分数，其余保留UNKNOWN；不是实时或已认证概率。
- [R14量化结果](../outputs/r14/summary.csv)、[重复事件对照](../outputs/r14/episode_summary.csv)、[机会身份登记](../outputs/r14/opportunity_registry.csv.gz)。
- [R15量化结果](../outputs/r15/summary.csv)、[确认代价汇总](../outputs/r15/confirmation_summary.csv)、[逐簇确认登记](../outputs/r15/confirmation_registry.csv.gz)。
- [R14反思](../rounds/r14_reflection.md)、[R15反思](../rounds/r15_reflection.md)、[季度概率诊断](../outputs/r14_r15_quarter_diagnostics.csv)。
- [R14验证](../outputs/r14/validation.json)：协议未变、35项输入/预测哈希、504条模型预测复现、40个市场特征前缀重建。
- [R15验证](../outputs/r15/validation.json)：227124条分数不变、2294次唯一正式准入核对、48组前缀回放。23项测试通过。

所有概率先封存后评价。代码正确、验收算术正确不等于模型有效；没有新增采集、交易、部署、对外发送或Git发布。原泛行业高胜率研究池目标保持开放。
'''
    (EP/'reports/calibration_episodes_r14_r15.md').write_text(text)
    print('R14/R15 report, full-industry state and release gates written.')
if __name__=='__main__':main()

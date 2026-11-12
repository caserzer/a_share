"""Generate reviewable R09-R11 report and historical all-industry disposition."""
import json
import pandas as pd
from pool_evaluation import EP,HORIZONS,sha

NAMES={'slowdown':'价格恶化减速','pressure_easing':'新低压力缓解','improvement_acceleration':'价格改善加速','broad_confirmation':'广泛确认','long_confirmation':'长期确认','old_top10':'旧top10参考'}
def pct(x):return '—' if pd.isna(x) else f'{100*x:.2f}%'
def pp(x):return '—' if pd.isna(x) else f'{100*x:+.2f}'
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    s=pd.read_csv(EP/'outputs/r09/summary.csv');r10=pd.read_csv(EP/'outputs/r10/conditional_summary.csv');r11=pd.read_csv(EP/'outputs/r11/conditional_summary.csv')
    registry=pd.read_csv(EP/'outputs/r09/universe_registry.csv.gz',parse_dates=['date']);last=registry[registry.date.eq(registry.date.max())].copy()
    p=pd.read_parquet(EP/'outputs/r11/coverage30/evaluation_panel.parquet');recent=p[p.date.eq(last.date.max())]
    cols=['era','industry_code','rate20','rate_change','breadth21','finance_count','finance_coverage','growth','finance_acceleration']+list(NAMES)+['fin_improving','fin_slowing']
    last=last.merge(recent[cols],on=['era','industry_code'],how='left',validate='one_to_one')
    last['approved_high_win_pool']=False
    last['disposition']=last.status.map({'ELIGIBLE':'OBSERVABLE_NO_VALIDATED_ADMISSION_RULE','NO_PRICE_PATH':'UNKNOWN_NO_PRICE_PATH','INSUFFICIENT_HISTORY_OR_COVERAGE':'UNKNOWN_INSUFFICIENT_HISTORY_OR_COVERAGE'})
    last['reason']='R09-R11尚无通过验收的高胜率准入规则；未准入不等于不存在机会'
    last.to_csv(EP/'outputs/pool_latest_disposition.csv',index=False)
    rows=[]
    for method in NAMES:
        for unit in ['state','entry']:
            a=s[s.method.eq(method)&s.unit.eq(unit)].set_index('horizon')
            rows.append([NAMES[method],{'state':'周状态','entry':'首次进入'}[unit]]+[pct(a.loc[h,'pooled_win_rate']) for h in HORIZONS]+[int(a.loc[126,'known']),pp(a.loc[126,'paired_all_delta']),f"{a.loc[126,'mean_pool']:.1f}"])
    text='''# EP33 R09–R11：泛行业高胜率研究池的连续检验

执行日期：2026-11-11。**三轮已执行，原目标保持开放，尚无通过验收的高胜率准入规则。** 这不是对行业不存在机会的判断，而是当前固定代理不足以支持准入。

成功严格定义为：下一交易日收盘起算，行业收益>0且同期行业收益−中证全指收益>0。分别评价63/126/252交易日（约3/6/12个月），未挑选最优期限。行业历史价格与财报均为既有代理数据，截止2026-10-21；最后完整周为2026-10-16，清单不是实时推荐。

## 覆盖与统计口径

全目录按分类制度分别登记，2021–2026共296个市场周、97,072个行业×周记录；其中68,439可准入、4,360历史或覆盖不足、24,273无价格路径。末期347行业中264可观察、83无价格路径。数据缺口不是无机会。

周状态反映持续跟踪，首次进入反映新机会，两者不能混用。R09另外保留R07的8周冷却事件敏感性（仅2021–2025）；R10、R11的研究期初无法确认前状态，保留边界未知。R11财务刚恢复可用的状态也不冒充新改善。

下表胜率为合并成熟可评价样本比例；增量是相同信号日期先做差、再等权平均，不能用表中的合并胜率直接相减。每周数量包含全市场周历（包括不可观察周）；完整结果逐项列出已知成功/失败、未成熟与路径缺失、未知上下界、空池及集中度。

## R09：已有价格变化规则

'''+table(['规则','观察单位','3个月胜率','6个月胜率','12个月胜率','6个月已知数','6个月较同期全行业增量/百分点','每周数量'],rows)+'''

改善加速和更多确认没有建立高胜率优势。旧top10虽可高于同容量动量，却低于同期全行业，不能据此批准。首次进入口径下，六种规则的6个月同期全行业增量均为负。早期性亦未解决：R07/R08已有证据显示等待广泛确认通常延迟约2–3周；那是过程比较，不能把过程持续率当本表胜率。此次未通过胜率关卡，未调整入池时间来制造更好结果。

## R10：分离市场环境、一阶状态与二阶增量

根据R09反思，冻结12个环境×状态分支，检验二阶信息是否在同日、同一阶方向与相近速度下仍有增量。使用当时中证全指126日收益>0划分UP，其余已知为NONUP。以下为周状态相对速度匹配对照增量（百分点）：

'''
    rows=[]
    for method in ['up__slowdown','nonup__slowdown','up__pressure_easing','nonup__pressure_easing']:
        a=r10[r10.method.eq(method)&r10.unit.eq('state')].set_index('horizon');rows.append([method]+[pp(a.loc[h,'delta']) for h in HORIZONS])
    text+=table(['分支','3个月','6个月','12个月'],rows)+'''

没有跨环境一致的正增量；EP32的市场上涨门槛不能直接移植为新联合标签的准入条件。NONUP下相对弱势池本身就有部分表面优势，不能归功于二阶减速。

## R11：换用已有营收二阶信息

按R10反思转向营收YoY及其变化。最低3家公司、30%覆盖是既有口径；50%覆盖作事前登记敏感性。财务可用行业周分别为28,361（价格可用池的41.4%）和13,131（19.2%），绝非完整基本面覆盖。

负增长但下滑放缓的结果如下；最后一列控制同日增长方向与价格速度，仅是探索性匹配：

'''
    rows=[]
    for threshold in ['coverage30','coverage50']:
        a=pd.read_csv(EP/f'outputs/r11/{threshold}/summary.csv')
        for unit in ['state','entry']:
            g=a[a.method.eq('fin_slowing')&a.unit.eq(unit)].set_index('horizon')
            c=r11[r11.threshold.eq(threshold)&r11.method.eq('fin_slowing')&r11.unit.eq(unit)&r11.horizon.eq(252)].iloc[0]
            rows.append([threshold,unit]+[pct(g.loc[h,'pooled_win_rate']) for h in HORIZONS]+[int(g.loc[252,'known']),pp(c.delta),f'[{pp(c.lo)}, {pp(c.hi)}]'])
    text+=table(['覆盖要求','单位','3个月胜率','6个月胜率','12个月胜率','12个月已知数','12个月匹配增量/百分点','描述性95%区间'],rows)+'''

30%覆盖的一年期周状态有线索，但换成首次进入或50%覆盖后不稳。首次进入的一年期111个已知样本中57个成功；并非1,595个独立新机会。重复周、较少同层对照及长持有期重叠都削弱证据。该结果支持继续追问信息新鲜度，不支持当前批准准入。

## 自我反思与下一轮方向

1. R09否定“过程持续/收益均值较好即可推断联合高胜率”，转向同日期基准。
2. R10未证实价格二阶信息独立增量，停止在同类差分窗口上反复调参，转向已有财务信息。
3. R11发现状态观察日与首次入池的差别，拒绝将53.4%的单项结果作为泛行业准入依据。

下一项具体假说：**新披露推动的行业财务状态变化，是否比旧状态持续更能识别新机会？** 需从已有公司财务事件重建“新增信息占比/信息年龄”，并区分披露更新与成员、覆盖变化，随后冻结事件级比较。当前聚合字段不足以回答，不能伪称已执行或已有高胜率结果。本次在完成三个有依据的实验循环后收束，未进行无理由的参数遍历。

## 交付与限制

- [全行业末期状态清单](../outputs/pool_latest_disposition.csv)：每个行业数据状态、各探索规则命中、财务覆盖；高胜率正式准入为0，含义是无已验证规则，不是断言市场无机会。
- [R09全量结果](../outputs/r09/summary.csv)、[年度](../outputs/r09/annual.csv)、[逐期对照](../outputs/r09/weekly_comparison.csv.gz)、[全行业覆盖](../outputs/r09/universe_registry.csv.gz)。
- [R10结果](../outputs/r10/summary.csv)、[同类增量](../outputs/r10/conditional_summary.csv)、[年度增量](../outputs/r10/conditional_annual.csv)。
- [R11主结果](../outputs/r11/coverage30/summary.csv)、[覆盖敏感性](../outputs/r11/coverage50/summary.csv)、[同类增量](../outputs/r11/conditional_summary.csv)。
- [R09反思](../rounds/r09_reflection.md)、[R10反思](../rounds/r10_reflection.md)、[R11反思](../rounds/r11_reflection.md)。
- [一致性验证](../outputs/pool_validation.json)：540项原始结果抽查、17项输入哈希检查、210行汇总及全部候选/对照成员对账，12项测试通过。

所有历史曾被使用，三轮是自适应探索，没有独立前瞻验证。区间按整周横截面、连续时间块重采样，500次；未做多重比较调整，一年期仅少量有效时间块，不构成统计认证。2021分类制度终止导致长标签缺失，2026未成熟样本较多，各年成熟窗口不同。财报修订、部分缺失及行业价格代理限制均保留。用户未指定最终期限、最低胜率与研究容量；未擅自设成70%或固定top10。

没有部署、交易、发送消息、新数据采集或Git发布。
'''
    (EP/'reports/pool_research_r09_r11.md').write_text(text)
    print('Report and 347-industry disposition saved.')
if __name__=='__main__':main()

"""Readable outcome, economic interpretation and all predeclared limitations."""
from common35 import *

LABEL={'levels':'多尺度水平','paths':'扩张路径','stage':'在线阶段'}
FREQ={'W':'周','BW':'双周','M':'月'}
def pct(x):return '—' if pd.isna(x) else f'{100*x:.2f}%'
def pp(x):return '—' if pd.isna(x) else f'{100*x:+.2f}'
def ci(lo,hi):return f'[{100*lo:+.2f}, {100*hi:+.2f}]' if pd.notna(lo) else '—'

def run():
    econ=pd.read_csv(OUT/'economics_primary.csv');primary=econ.query("unit=='six_month_launches' and months==6")
    c=pd.read_csv(OUT/'classification_primary.csv')
    intervals=pd.read_csv(OUT/'paired_intervals.csv')
    main=intervals.query("unit=='six_month_launches' and scope=='full'")
    cells=pd.read_csv(OUT/'four_cells.csv');cells=cells[cells.year.eq('ALL')]
    coverage=pd.read_csv(OUT/'eligible_coverage.csv');coverage=coverage[coverage.year.eq('ALL')]
    validation=json.loads((OUT/'validation.json').read_text())
    comparisons=[];classification=[];brier=[];control=[];ablation=[]
    for frequency in ['W','BW','M']:
        row={'频率':FREQ[frequency]}
        for method,label in [('baseline','原38项基线'),('pe','仅新增PE'),('levels','仅新增交易水平'),('joint_levels','PE＋交易水平')]:
            value=primary[(primary.frequency==frequency)&(primary.method==method)].iloc[0]
            row[label]=pct(value.mean_excess)
        ablation.append(row)
        for family in ACTIVITY:
            a=primary[(primary.frequency==frequency)&(primary.method==family)].iloc[0]
            j=primary[(primary.frequency==frequency)&(primary.method=='joint_'+family)].iloc[0]
            m=primary[(primary.frequency==frequency)&(primary.method=='missing_'+family)].iloc[0]
            i=main[(main.frequency==frequency)&(main.family==family)].iloc[0]
            old=c[(c.frequency==frequency)&(c.method==family)].iloc[0]
            new=c[(c.frequency==frequency)&(c.method=='joint_'+family)].iloc[0]
            comparisons.append(dict(frequency=frequency,family=family,activity_mean_excess=a.mean_excess,
                joint_mean_excess=j.mean_excess,launch_mean_delta=j.mean_excess-a.mean_excess,
                joint_launches=int(j.signals),known_returns=int(j.known_returns),paired_dates=int(i.paired_dates),
                paired_estimate=i.estimate,lower95=i.lower95,upper95=i.upper95,lower9=i.lower9,upper9=i.upper9))
            classification.append({'频率':FREQ[frequency],'交易家族':LABEL[family],
                '原precision':pct(old.precision),'联合precision':pct(new.precision),
                '原周期recall':pct(old.cycle_recall),'联合周期recall':pct(new.cycle_recall),
                '联合时点recall':pct(new.point_recall),'联合延迟中位天':new.median_delay})
            brier.append(dict(frequency=frequency,family=family,activity=old.brier,joint=new.brier,
                              relative_improvement=(old.brier-new.brier)/old.brier))
            control.append({'频率':FREQ[frequency],'家族':LABEL[family],
                '交易模型超额':pct(a.mean_excess),'缺失指示模型超额':pct(m.mean_excess),'联合模型超额':pct(j.mean_excess)})
    comp=pd.DataFrame(comparisons);comp.to_csv(OUT/'main_comparisons.csv',index=False)
    b=pd.DataFrame(brier);b.to_csv(OUT/'brier_relative_improvement.csv',index=False)
    e=comp.copy();e['频率']=e.frequency.map(FREQ);e['家族']=e.family.map(LABEL)
    e['仅交易']=e.activity_mean_excess.map(pct);e['加入PE']=e.joint_mean_excess.map(pct);e['差值pp']=e.launch_mean_delta.map(pp)
    e['启动/可评价']=e.joint_launches.astype(str)+'/'+e.known_returns.astype(str)
    e=e[['频率','家族','仅交易','加入PE','差值pp','启动/可评价']]
    statistical=comp.copy();statistical['频率']=statistical.frequency.map(FREQ);statistical['家族']=statistical.family.map(LABEL)
    statistical['配对日期']=statistical.paired_dates;statistical['日期配对差值pp']=statistical.paired_estimate.map(pp)
    statistical['95%区间pp']=[ci(r.lower95,r.upper95) for r in statistical.itertuples()]
    statistical['九重校正区间pp']=[ci(r.lower9,r.upper9) for r in statistical.itertuples()]
    statistical=statistical[['频率','家族','配对日期','日期配对差值pp','95%区间pp','九重校正区间pp']]
    bm=b.copy();bm['频率']=bm.frequency.map(FREQ);bm['家族']=bm.family.map(LABEL)
    bm['Brier相对改善']=bm.relative_improvement.map(pct);bm=bm[['频率','家族','activity','joint','Brier相对改善']]
    cv=coverage.copy();cv['频率']=cv.frequency.map(FREQ);cv['家族']=cv.family.map(LABEL)
    cv['共同完整率']=cv.complete_fraction.map(pct)
    cv=cv[['频率','家族','eligible_rows','complete_rows','共同完整率','accepted_alerts','complete_alerts']]
    ct=cells.copy();ct['频率']=ct.frequency.map(FREQ)
    ct['组']=ct.cell.map(dict(BOTH='双扩张',PE_ONLY='仅PE扩张',ACTIVITY_ONLY='仅交易扩张',NEITHER='均不扩张',UNKNOWN='未知'))
    ct['命中率']=ct.precision.map(pct);ct['平均超额']=ct.mean_excess.map(pct);ct['中位超额']=ct.median_excess.map(pct)
    ct=ct[['频率','组','signals','known_returns','cycle_known','命中率','平均超额','中位超额']]
    annual=pd.read_csv(OUT/'annual_economics.csv').query("unit=='six_month_launches'")
    rows=[]
    for family in ACTIVITY:
        j=annual[annual.method.eq('joint_'+family)].merge(annual[annual.method.eq(family)],on=['frequency','year'],suffixes=('_joint','_activity'))
        for r in j.itertuples():rows.append(dict(frequency=r.frequency,family=family,year=r.year,delta=r.mean_excess_joint-r.mean_excess_activity))
    annual_delta=pd.DataFrame(rows);annual_delta.to_csv(OUT/'annual_increment.csv',index=False)
    av=annual_delta.pivot(index=['frequency','family'],columns='year',values='delta').reset_index()
    for col in [2021,2022,2023,2024]:av[col]=av[col].map(pp)
    av['frequency']=av.frequency.map(FREQ);av['family']=av.family.map(LABEL)
    diagnostics=intervals.query("unit=='six_month_launches' and scope=='missing_control' and lower95>0")
    complete=intervals.query("unit=='six_month_launches' and scope=='complete'")
    decision=dict(status='NO_STABLE_INCREMENT',primary_comparisons=9,
        full_launch_mean_positive=int(comp.launch_mean_delta.gt(0).sum()),
        primary_positive_95=int(main.lower95.gt(0).sum()),primary_positive_adjusted=int(main.lower9.gt(0).sum()),
        complete_positive_95=int(complete.lower95.gt(0).sum()),
        brier_improved=int(b.relative_improvement.gt(0).sum()),
        missingness_diagnostic_positive_95=diagnostics[['frequency','family']].to_dict('records'),
        strict_PIT='BLOCKED_DATA',independent_forward='FORWARD_PENDING',policy_change=False,
        descriptive_cells_are_not_causal=True,source_survivorship_bias_unresolved=True)
    js(OUT/'decision.json',decision)
    text=f'''# EP32 V35：估值扩张＋交易活跃度扩张联合实验

## 结论

**本轮没有验证出稳定的联合增量，不据此替换现有方案。** 三类交易特征分别加入同一组多尺度 PE 后，九项主比较没有一项六个月超额收益改善的95%区间排除零，九重校正后同样为0；九组 Brier 概率误差全部变差。全部启动的平均超额收益仅周度路径和周度阶段两项小幅提高，其余七项降低。结果说明这次固定变量与模型未找到稳定增量，不能扩大为“估值信息永远无效”。

主源为 D2 V6 新补的 Eastmoney 历史 PE，2018—2026可用；主评价仍是2021-01-01—2024-09-30、三级行业、15%周期阈值、中证全指。原本全A/沪深300的目标在本轮继承V34的中证全指主基准，沪深300及其他阈值保留分类敏感性。全部数据仍为 Historical-proxy，不是认证的全历史 PIT；原财报分母版本未知、退市证券缺口集中，独立前瞻尚未发生。

## 想验证什么，如何区分四种解释

H1想验证：行业预期改善可能引发估值重估，同时新增关注和资金交易提升交易活跃度，两者能否一起提高早期景气识别，而非仅伴随已经发生的上涨。

对照为原38特征基线、仅交易扩张、仅PE、交易＋PE。交易扩张保留 V34 的多尺度水平、扩张路径、在线阶段三家族，不按结果择优挑一种。原特征中已有动量、风险、扩散和简单量比，因此联合模型必须超过已有价格和交易信息。另做三个只加 PE 缺失指示的诊断模型，不含 PE 数值。

PE组固定为21/63/126/252日成员log变化、504/756日历史正PE秩、21日PE扩张广度。正PE变化窗口要求连续有效，行业聚合使用上月已固定成员，至少5人且80%完整成员可用。成员变化中位数只是估值变化代理，不是总市值/总盈利的行业聚合PE。没有追加调参、按结果换窗或改门槛。

共14个非空季度，7个新模型/季度，共98个模型检查点，产出404,274行多任务预测；2022Q1原分类样本为空，保留原空档。固定模型为240树、15叶、深度4、minchild200、lr=.03、L2=25、seed32，只使用每季度前已成熟标签。

## 六个月经济结果

以下单位为行业同一价格连续块中，六自然月冷却期内的首次信号；下一个交易日收盘进入，持有六自然月。**这不是事后独立景气周期计数，也不是可直接执行的投资组合收益。** 同期中证全指收益用差值扣除。各方法每期原始报警数K一致；冷却后启动数可能不同。未知后续收益保留并单列，没有只看成功周期。

先展示完整四种模型对照（平均超额收益，交易组先列多尺度水平）：

{md(pd.DataFrame(ablation))}

再列全部三个交易家族的联合增量：

{md(e)}

差值按全部可评价启动的均值相减。主置信区间另按两方法都有可评价启动的日期配对，对日期均值差做12自然月块、5,000次bootstrap。两种加权和样本不同，因此数值甚至符号可以不同，不能混为同一估计。

{md(statistical)}

主配对只剩7—24个日期，统计辨别力有限。这是未获得稳定证据，不是证明真实效应严格为零。原始报警的辅助区间和全部3/6/12月收益、回撤、固定成本敏感性均保留在 CSV；主结论未改用更有利的辅助口径。

辅助的未去重原始报警口径中，周度“水平＋PE”有正向95%区间，月度“路径＋PE”有负向95%区间；它们不能替代预先冻结的六个月去重主比较，也没有形成跨频率一致结果。

## Precision、recall 与延迟

precision沿用原验收的“有已知标签报警的日期先算命中率，再对日期平均”；CSV另有合并时点precision。时点recall=命中的正例时点/全部正例时点；周期recall=至少命中一次的周期数/完整可评价周期数，不把同一周期的多次报警当多个周期。未知标签既不填0也不当负例。延迟为首次命中时点减事后周期起点的日历日，只对捕捉到的周期计算，未捕捉周期通过recall体现。

{md(pd.DataFrame(classification))}

这些是本轮固定主任务的指标，不能直接与此前跨行业层级/阈值/基准汇总的24.65% precision混比。每年、每频率及36个分类任务全表保留。

{md(bm)}

负的“Brier相对改善”表示概率误差上升。九项均变差，幅度约{-b.relative_improvement.max():.2%}—{-b.relative_improvement.min():.2%}。

## 共同样本与缺失模式

新PE没有改变原训练/评价母体，缺失由树原生处理。下面是在线早期且市场126日上涨母体内，全部PE及对应交易特征共同完整的覆盖；共同样本的所有模型都用相同母体和相同K。

{md(cv)}

共同完整观测仅约11%—12%，不能代表所有行业；共同样本九项比较同样没有正向95%下界。长窗口不足、亏损、供应商缺口均可导致未知，不能通过删去这些行冒充完整行业池。

{md(pd.DataFrame(control))}

阶段联合模型相对“仅缺失指示”对照，在周度、月度的日期配对95%诊断区间出现正向下界，已完整保留；但没有超过对应原阶段模型的主证据，不能据此宣布联合方案通过。缺失指示还包含亏损、历史长度不足等状态，不是纯粹的退市泄漏标签；这个对照只能检查一部分解释，不能消除供应商幸存者偏差。

## 四组切片与经济含义

PE21变化>0、短期换手率扩张>0形成四组，未知单列。先从原早期＋市场上涨母体按统一六个月时钟选择首次观察，再分组，而不是每组重新启动冷却期。周/双周/月度的首次观察时点不同，所以组内样本并非相同；特别是周度双扩张只有27次启动、20次已知收益，不应将频率差异解释成机制定律。

四格来自未按模型分数排名的候选池，与前文模型报警不是同一筛选母体，不能直接比较二者precision来判定哪种模型更优。

{md(ct)}

发现：双周和月度“双扩张”组有正平均超额收益，但“均不扩张”组更高；周度双扩张接近零。双扩张可与后续上涨共存，目前不是稳定的排序优势。四格的命中率是已知标签启动的合并比例，和上文按报警日期宏平均的precision不同。这是描述性关联，不是因果估计，也不等于可实现的最高点收益。

为什么不能直接验证基本面景气：PE=P/E，PE上涨既可能来自股价上涨和预期重估，也可能来自盈利分母下降；真实利润修复还可能使PE下降。此次没有可认证的财报首次披露版本，所以不能从PE或价格反推出财务事实，不能把“PE扩张失败”解释为“行业基本面没有扩张”。若后续继续研究，盈利改善与估值重估应分开定义，先补可得时间明确的利润/盈利修正证据。

## 年度稳定性与结论边界

各年联合模型相对对应交易模型的六个月平均超额变化（百分点）：

{md(av)}

没有一家族跨三频率、跨年份稳定改善。2024仅评价至9月30日；不同年度可评价启动、标签未知和剩余价格期限分布不同，详见年度与覆盖表。九项主比较在已多次使用的历史上进行，本轮没有独立前瞻数据，也没有生产部署或替换冻结策略。

## 验证与可复核资料

{validation['checks_count']}项检查通过，包括71项公式/时间检查、原基线和三个交易模型2021Q1精确重放、全部旧分类与收益控制结果复核、同K和共同母体验证、六个月观察时钟前缀验证、全部源文件与旧研究哈希保护。私有缓存：`{CACHE}`；112个季度模型/预测检查点均记录哈希。

[冻结方案](../research_plan.md) · [九项主比较](../outputs/main_comparisons.csv) · [分类明细](../outputs/classification_primary.csv) · [区间与全部诊断](../outputs/paired_intervals.csv) · [共同覆盖](../outputs/eligible_coverage.csv) · [四组经济结果](../outputs/four_cells.csv) · [逐年分类](../outputs/annual_classification.csv) · [验证](../outputs/validation.json) · [判定](../outputs/decision.json)
'''
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/pe_activity_joint.md').write_text(text)
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files)))
    print(json.dumps(decision,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':run()

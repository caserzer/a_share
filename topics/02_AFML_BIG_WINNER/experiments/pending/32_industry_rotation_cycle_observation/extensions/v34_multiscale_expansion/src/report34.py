from common34 import *


def table(frame,cols,percent=()):
    g=frame[cols].copy()
    for c in percent:g[c]=g[c].map(lambda x:f'{x:.2%}' if pd.notna(x) else '未知')
    return md(g)


def run():
    econ=pd.read_csv(OUT/'economics_primary.csv')
    main=econ.query("months==6 and unit=='six_month_launches' and method in ['baseline','levels','paths','stage']")
    classification=pd.read_csv(OUT/'classification_primary.csv').query("method in ['accepted','baseline','levels','paths','stage']")
    intervals=pd.read_csv(OUT/'paired_intervals.csv')
    primary=intervals.query("unit=='six_month_launches' and scope=='full'")
    common=intervals.query("unit=='six_month_launches' and scope=='complete'")
    annual=pd.read_csv(OUT/'annual_economics.csv').query("unit=='six_month_launches' and method in ['baseline','levels','paths','stage']")
    baseline=main[main.method.eq('baseline')].set_index('frequency')
    gain=main[~main.method.eq('baseline')].copy()
    gain['mean_excess_increment']=gain.mean_excess-gain.frequency.map(baseline.mean_excess)
    gain.to_csv(OUT/'six_month_increment.csv',index=False)
    pe=json.loads((OUT/'pe_verdict.json').read_text())
    coverage=pd.read_csv(OUT/'feature_coverage.csv')
    coverage=coverage.query("level=='L3' and year>=2021 and year<=2024").copy()
    coverage['complete_fraction']=coverage.complete/coverage.rows
    decision=dict(status='FIXED_THREE_FAMILY_EXPERIMENT_COMPLETED',families={},PE_joint_test='BLOCKED_DATA',
        main_PE_feature_rows=pe['main_pe_feature_rows'],combinations_tried=0,window_search_performed=False,
        strict_PIT='BLOCKED_DATA',independent_forward_validation='FORWARD_PENDING',independent_holdout=False)
    for family in GROUPS:
        g=primary[primary.family.eq(family)]
        decision['families'][family]=dict(positive_point_estimates=int(g.estimate.gt(0).sum()),
            positive95_intervals=int(g.lower95.gt(0).sum()),positive9_adjusted_intervals=int(g.lower9.gt(0).sum()),
            all_frequency_adjusted_positive=bool(len(g)==3 and g.lower9.gt(0).all()),
            complete_support_positive95=int(common[common.family.eq(family)].lower95.gt(0).sum()))
    js(OUT/'decision.json',decision)
    brier=classification.pivot(index='frequency',columns='method',values='brier')
    brier_improvement=pd.DataFrame({family:(brier.baseline-brier[family])/brier.baseline for family in GROUPS}).reset_index()
    brier_improvement.to_csv(OUT/'brier_relative_improvement.csv',index=False)
    passed=[name for name,v in decision['families'].items() if v['all_frequency_adjusted_positive']]
    finding=('没有任何组在三个频率的主比较中均取得校正后正收益增量，本轮不升级现有模型。' if not passed else
             '在三个频率校正区间均为正的组：'+','.join(passed)+'；仍只属反复查看历史后的探索线索。')
    (ROOT/'reports').mkdir(exist_ok=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,5))
    plot=primary.sort_values(['family','frequency']).reset_index(drop=True)
    for i,row in plot.iterrows():
        ax.plot([row.lower9*100,row.upper9*100],[i,i],color='#b9c5d0',lw=2)
        ax.plot([row.lower95*100,row.upper95*100],[i,i],color='#2266aa',lw=5)
        ax.scatter([row.estimate*100],[i],color='#111111',s=20,zorder=3)
    ax.axvline(0,color='#bb4444',ls='--');ax.set_yticks(range(len(plot)),plot.family+' / '+plot.frequency)
    ax.set_xlabel('Paired date-average 6-month excess-return increment (percentage points)')
    ax.set_title('Feature-family increment vs frozen same-capacity baseline\nBlue: 95%; gray: nine-comparison adjusted block-bootstrap interval')
    ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(ROOT/'reports/increment_intervals.png',dpi=180);plt.close(fig)
    report='''# EP32 V34：多尺度交易扩张与PE可用性实验

'''+finding+'''

在线阶段变量的概率误差有局部改善，但误差改善、分类命中率和实际后续收益是不同目标，不能互相替代。PE与成交共同扩张因缺少主样本PE序列尚未检验，不能把纯成交结果解释为PE假设失败。

执行用户确认的三组候选，未只使用63/252日，未遍历窗口或搜索新门槛。主实验三级行业、15%转折、中证全指，周/双周/月分别评价。原V1—V33与FOLLOWUP.md保持不变。

## 实际检验了什么

|组|新增内容|经济含义|
|---|---|---|
|levels 多尺度水平|换手率21日/此前63日，63日/此前126日；成交股数21日/此前63日；换手率504/756日历史位置；行业可用池成交额占比的短期变化|相对过去是否更活跃、处在长期什么位置|
|paths 扩张路径|平滑换手率63日斜率、21日增速变化、6个21日阶段的提高比例、成员放量广度及变化|扩张是否持续、加速并扩散到更多成员|
|stage 在线阶段|相对当时已知候选低点的换手率、成交份额、放量广度变化及单位交易日速度|当前候选行情启动以来参与度如何变化|

基线为原V18扩散树38项特征，包含原volume_ratio。三候选分别仅增加一组，模型容量、季度成熟标签训练、参数和随机种子全部相同；原2021Q1模型预测精确复现。三组未组合，未按结果调整窗口。特征按截至当时数据计算，但底层价格/成员/供应商换手率仍为Historical-proxy。

## PE审计：联合假设没有被偷换成纯成交结论

封存PE共529,304条：2017年仅1个日期、3,039只证券；2026年有101个日期、5,239只证券。所有记录known_at缺失。2021—2024主评价区间没有PE时间序列，PE特征可用行数为0，因此“PE扩张×成交扩张”四组比较仍BLOCKED_DATA，未估计。

2026年有限记录可以产生部分21/63日正PE变化代理，已列覆盖；不能用2017单日与2026记录跨缺口滚动，也不能补成2017年以来完整估值。成员PE变化中位数不被称为聚合行业PE；负PE及缺失不作为PE收缩样本，不用PE反推财务事实。本轮只完成交易扩张三组特征的预测增量检验，不能宣称证实或否定估值共同扩张机制。

## 主经济结果：相同原报警数量

在原早期状态+市场条件通过的候选池中，各模型按当期当前V28报警数K选前K；基线也用同K排名。先选名单，后检查未来收益，未因未来未知删样本。随后各方法独立采用V31的6月观察段首次报警规则；因此原报警数相同，最终首次启动数可能不同。

从信号后下一交易日收盘起算6个月收益，含误报及周期标签未知记录。表中mean_excess是每个已知结果的首次启动等权，非组合资金收益，缺失不补零。

'''+table(main,['frequency','method','signals','known_returns','mean_return','median_return','mean_excess','median_excess','mean_max_drawdown'],
    ['mean_return','median_return','mean_excess','median_excess','mean_max_drawdown'])+'''
与冻结同容量基线的首次启动等权平均超额收益差：

'''+table(gain,['frequency','method','mean_excess_increment'],['mean_excess_increment'])+'''
## 九项事前主比较与不确定性

以下比较为双方均有已知结果的共同启动日期上，先计算各日平均超额差，再跨日期等权。它与上表每启动等权不是同一权重。12自然月时间块bootstrap，5000次；95%为描述性区间，lower9/upper9为三组×三频率九项主比较的Bonferroni 99.444%区间。稀少共同日期、长时间重叠和历史反复探索使证据有限，校正不构成独立前瞻验证。

'''+table(primary,['family','frequency','paired_dates','estimate','lower95','upper95','lower9','upper9'],['estimate','lower95','upper95','lower9','upper9'])+'''
![收益增量及区间](increment_intervals.png)

## 完整特征支持范围的同样本检查

为避免仅因新特征覆盖改变样本构成，分别只在各组当时全部新特征已知的候选池中比较基线和该候选；K为原V28在该池内的报警数。未来标签/收益未知不影响入池。该检查是条件样本对照，不替代主结果，也不证明缺失模式无影响。

'''+table(common,['family','frequency','paired_dates','estimate','lower95','upper95'],['estimate','lower95','upper95'])+'''
三级行业特征覆盖（含不同阈值/频率重复观察，只用于覆盖审计，不是独立事件数）：

'''+table(coverage,['year','family','rows','complete','complete_fraction'],['complete_fraction'])+'''
长历史位置特征需要足够历史，2022年分类切换还影响路径和阶段计算。未把缺失填为0；树原生处理缺失，因此全样本模型也可能利用可得性模式。

## 分类与年度结果

周期指标沿用每个原任务完整可评价周期分母；precision按已知报警日期平均。下面的baseline采用同K扩散树排名，accepted为原双模型0.11政策，两者不能混称原模型。

'''+table(classification,['frequency','method','all_alerts','unknown_alerts','precision','cycle_recall','point_recall','median_delay','brier'],['precision','cycle_recall','point_recall'])+'''
'''+table(annual,['frequency','method','year','signals','known_returns','mean_return','mean_excess'],['mean_return','mean_excess'])+'''
其它阈值、行业层级和市场基准的分类分解在classification_all_tasks.csv；3/12月收益和固定0.11辅助政策在economics_primary.csv。辅助结果不用于挑选本轮最优窗口或门槛。

## 如何解释

只有跨频率、年度及完整覆盖检查仍保持改善，才值得进一步组合。单个方向为正、某个频率区间为正或特征重要性高，都不等于“成交扩张导致景气”。树可能使用收缩或过热特征，增量预测不自动验证假设方向。未见稳健增量的组应保留证据不足，不继续在同历史上搜索更多天数来追求达标。

本轮没有实盘部署、调度、交易或提交推送；没有新真实前瞻。严格PIT BLOCKED_DATA、独立前瞻FORWARD_PENDING。结论按decision.json逐组保留，包括正向点估计、95%区间和九项校正区间的数量。

[冻结方案](../research_plan.md) · [全部经济指标](../outputs/economics_primary.csv) · [主比较区间](../outputs/paired_intervals.csv) · [首次信号明细](../outputs/primary_six_month_launches.csv.gz) · [PE覆盖](../outputs/pe_raw_coverage.csv) · [逐组结论](../outputs/decision.json) · [公式与因果核验](../outputs/feature_validation.json)
'''
    (ROOT/'reports/multiscale_expansion.md').write_text(report)
    print(json.dumps(decision,ensure_ascii=False,indent=2))


if __name__=='__main__':run()

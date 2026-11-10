from common31 import *


def display(frame, columns, percentages=()):
    frame=frame[columns].copy()
    for c in percentages:
        frame[c]=frame[c].map(lambda x:f'{x:.2%}' if pd.notna(x) else '未知')
    return md(frame)


def run():
    p=pd.read_csv(OUT/'primary_metrics.csv')
    accepted=p.query("method=='accepted' and unit=='six_month_launches'")
    six=accepted.query('months==6')
    controls=p.query("months==6 and unit=='six_month_launches' and method in ['accepted','same_date_universe','early_market_all','momentum_top10','momentum_matched','capacity_matched','diffusion_matched','no_market']")
    ci=pd.read_csv(OUT/'paired_block_intervals.csv').query("unit=='six_month_launches' and control=='momentum_matched'")
    cycles=pd.read_csv(OUT/'cycle_metrics.csv').query("level=='L3' and threshold==0.15 and benchmark=='CSI_ALL'")
    annual=pd.read_csv(OUT/'primary_annual.csv').query("method=='accepted' and unit=='six_month_launches'")
    strata=pd.read_csv(OUT/'label_strata.csv').query("unit=='six_month_launches' and label_status in ['POSITIVE','NEGATIVE','UNKNOWN']")
    robust=bool(ci.lower.gt(0).all())
    decision=dict(status='POSITIVE_HISTORICAL_EXCESS_INCREMENT_NOT_ESTABLISHED' if not robust else 'EXPLORATORY_INCREMENT_OBSERVED',
        primary_scope=dict(level='L3',threshold=.15,benchmark='CSI_ALL',frequencies=['W','BW','M']),
        observation_window=['2021-01-01','2024-09-30'],entry='next market trading day close',
        economic_unit='first alert per industry per causal six-month observation lockout',
        positive_mean_excess_all_frequencies=bool(six.mean_excess.gt(0).all()),
        increment_vs_matched_momentum_interval_positive_all_frequencies=robust,
        strict_PIT='BLOCKED_DATA',independent_forward_validation='FORWARD_PENDING',
        unchanged_V28_acceptance=True,not_realized_strategy_returns=True)
    js(OUT/'decision.json',decision)
    report='''# EP32 V31：去重后的全部信号经济价值

结论：主口径下全部首次信号具有正的历史6个月平均超额，但相对同日同数量动量对照的改善区间均跨零。复杂模型的稳健经济增量尚未确立。部分简单对照更好；2023年出现“行业绝对收益为负但跑赢更弱市场”。不能将正超额等同于赚钱或可执行净收益。

## 固定口径与两个统计单位

主口径为三级行业、15%转折、中证全指，周/双周/月分别评价。原二级/10%/20%/沪深300全部保留在all_task_metrics.csv，不混入主表。原V28所有36任务的报警、已知标签、检出周期和precision逐项复现；原验收不被新统计单位替换。

周期统计：每个明确phase_id取首次正确报警，未来6—18月资格和前3个月早期定义不变。全部信号经济统计：不按成败筛选，每行业从首次报警开始锁定一个6月观察段，次交易日收盘起算，6月后的首个交易日到期，期间重复报警不再启动；到期时收盘后的新信号允许开启下段。不同频率独立计算，分类/价格块不跨接。这是因果可执行的研究计数规则，不是把每段都当真实经济周期。

此段规则未用未来标签/峰值决定是否启动。所有报警逐条的辅助结果同样保存在表中，用以显示频率和重复报警权重的影响。各行业同期结果具有共同市场暴露，不是独立样本，也没有模拟资金占用与组合仓位。

## 全部首次信号：6个月收益

'''+display(six,['frequency','signals','known_returns','missing_returns','mean_return','median_return','mean_excess','median_excess','positive_excess','mean_max_drawdown','excess_q10'],
    ['mean_return','median_return','mean_excess','median_excess','positive_excess','mean_max_drawdown','excess_q10'])+'''
signals为全部启动，known_returns为未来价格完整者。收益均值和中位数仅对后者计算，缺失不填零。最大回撤是每个观察段内从当时运行峰值至后续低点的最大跌幅，再对观察段汇总。

## 固定期限敏感性

'''+display(accepted,['frequency','months','signals','known_returns','mean_return','median_return','mean_excess','median_excess'],['mean_return','median_return','mean_excess','median_excess'])+'''
三组期限使用同一6月启动规则，12月观察窗口因此可能重叠；没有把它们当独立持仓。2021分类断点造成显著缺失，12月已知样本更少，不可把不同期限样本差异全归因于持有时长。

## 同口径对照

'''+display(controls,['frequency','method','signals','known_returns','mean_excess','median_excess'],['mean_excess','median_excess'])+'''
same_date_universe为当前方案有原报警的日期、全部当时可用三级行业；early_market_all为早期状态及市场条件通过的全部行业；momentum_top10为该候选池63日动量前10%；matched系列在每日期匹配当前原报警数，再各自运行6月锁定。故原报警数相同，最终首次启动数可以不同，不能声称启动数量/日期完全匹配。

capacity_matched与diffusion_matched使用相同树容量，只有是否添加扩散特征不同。no_market去除市场条件，其观察日期变化，不是随机分配实验。

## 相同有结果日期的成对比较

下面是当前方案减同K动量的“各日期平均6月超额收益之差”，再跨日期等权。它不同于上表每启动记录等权的收益差。按12个自然月块、1000次重采样得到描述性95%区间，行业横截面共同移动；历史已经多次探索，不能把该区间视为新样本确认。

'''+display(ci,['frequency','paired_dates','estimate','lower','upper','months'],['estimate','lower','upper'])+'''
共同启动日期很少，跨度月份不等于有效独立月份；数据覆盖、市场过滤和6月锁定均压缩样本。不能以大量行业记录伪造大样本置信度。

## 年度表现与标签分解

'''+display(annual,['frequency','year','signals','known_returns','mean_return','mean_excess','median_excess'],['mean_return','mean_excess','median_excess'])+'''
'''+display(strata,['frequency','label_status','signals','known_returns','mean_return','mean_excess'],['mean_return','mean_excess'])+'''
UNKNOWN周期标签中仍有已知固定期限收益，已纳入主统计。负周期标签不必对应固定6月负收益；它也可能是短于6月、起点被替代、期限或超额不满足等情况。不能拿分类precision直接乘成功样本涨幅计算总收益。

## 单一周期定义下的成功捕捉空间

'''+display(cycles,['frequency','detected_cycles','evaluable_cycles','precision','cycle_recall','mean_remaining_gain','median_remaining_gain','mean_days_to_peak','median_days_to_peak'],['precision','cycle_recall','mean_remaining_gain','median_remaining_gain'])+'''
这一表沿用信号日收盘至事后周期峰值，仅回答成功条件下空间；全部信号收益则从下一交易日收盘起算，不能混用。周/双周/月不相加。此前41.05%的跨定义汇总被上述固定单一任务表替代用于本轮主分析。

## 风险、成本和验证边界

全表提供50/100bp总成本扣减敏感性、10%收益下侧分位、最大回撤，以及用信号前252个完整交易日估计beta后的累计对数收益残差。该残差只是市场暴露的描述性调整，不是已证明的因果alpha；行业篮子月度重置、股票流动性和实际资金组合尚未完整模拟，成本扣减不代表真实交易成本测算。

独立抽样核对180个原始价格路径的起终点、收益、回撤及beta，并验证启动规则的前缀因果性，未知不补零。所有原始制品和输入哈希保持。严格PIT仍BLOCKED_DATA，独立前瞻FORWARD_PENDING。

[主结果](../outputs/primary_metrics.csv) · [全部36任务与对照](../outputs/all_task_metrics.csv) · [全部主口径信号明细](../outputs/primary_accepted_outcomes.csv.gz) · [缺失覆盖](../outputs/selection_coverage.csv) · [独立数值核验](../outputs/independent_numerical_validation.json) · [冻结方案](../research_plan.md)
'''
    (ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/all_signal_economics.md').write_text(report)
    checks=json.loads((OUT/'evaluation_checks.json').read_text())['checks']
    checks+=json.loads((OUT/'independent_numerical_validation.json').read_text())['checks']
    freeze=json.loads((OUT/'freeze.json').read_text())
    assert sha(ROOT/'research_plan.md')==freeze['plan_sha256']
    js(OUT/'final_code_receipt.json',dict(files={str(p):sha(p) for p in sorted((ROOT/'src').glob('*.py'))}))
    finish(checks+['research plan unchanged'])
    print(decision)


if __name__=='__main__':run()

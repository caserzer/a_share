import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from context6 import ROOT,OUT,V5,js


def md(d):
    return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join(
        '|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'


def build():
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    tests=pd.read_csv(OUT/'primary_tests.csv');metrics=pd.read_csv(OUT/'ablation_metrics.csv')
    verdict=json.loads((OUT/'hypothesis_verdicts.json').read_text())
    keys=['cohort','frequency','threshold','benchmark','level']
    baseline=metrics[metrics.model.eq('base')][keys+['brier']].rename(columns={'brier':'base_brier'})
    matched=metrics.merge(baseline,on=keys,validate='many_to_one')
    matched['relative_brier_improvement']=1-matched.brier/matched.base_brier
    matched.to_csv(OUT/'matched_model_comparisons.csv',index=False)
    summary=matched.groupby(['cohort','model']).agg(brier=('brier','mean'),
        relative_brier_improvement=('relative_brier_improvement','mean'),top10_precision=('top10_precision','mean'),
        top10_lift=('top10_lift','mean'),pr_auc=('pr_auc','mean')).reset_index()
    summary.to_csv(OUT/'summary.csv',index=False)
    titles={'base':'原模型，同样本重训','H1':'加入龙头先行','H2':'加入同业扩散','H3':'加入市场调整后的强势',
            'joint':'三个机制一起加入','other_leader':'跨行业龙头对照','reverse':'同业领先龙头对照'}
    common=summary[summary.cohort.eq('common')].set_index('model').reindex(titles).reset_index()
    view=pd.DataFrame({'模型':common.model.map(titles),'Brier误差':common.brier.map(lambda x:f'{x:.6f}'),
        '相对同样本基线改善':common.relative_brier_improvement.map(lambda x:f'{x:+.2%}'),
        '前10%命中率':common.top10_precision.map(lambda x:f'{x:.2%}'),
        '命中率提升倍数':common.top10_lift.map(lambda x:f'{x:.2f}')})
    display=pd.DataFrame({'检验':tests.test,'效应':tests.effect.map(lambda x:f'{x:+.6f}'),
        '95%区间':[f'[{a:+.6f}, {b:+.6f}]' for a,b in zip(tests.ci_low,tests.ci_high)],
        'BH调整后q':tests.q_bh.map(lambda x:f'{x:.3f}'),'支持预定正方向':tests.positive_supported.map({True:'是',False:'否'})})
    cov=pd.read_csv(OUT/'feature_coverage.csv');ratio=cov.common_complete.sum()/cov.rows.sum()
    descriptions={
      'H1':('龙头先行：大公司的信息先传到其他公司',
        '如果较大公司先吸收行业共同信息，其过去21日正超额收益应预测其余成员未来21日超额；反向和其他行业龙头应较弱。',
        '每月开始按上月末总市值前三固定龙头，跟随者严格排除这三只。共同样本、自己的过去21/63日收益和波动控制不变。正、负收益分别估计。',
        '任何行业内相关性都可能来自共同因子、流动性或反转。真正支持“龙头先行”需要正向斜率、优于反向/跨行业对照及早期识别增量同时成立。'),
      'H2':('同业扩散：从少数公司上涨走向更广覆盖',
        '上一个21日窗口的龙头领先差为正，随后非龙头上涨比例扩大，应比单纯行业已经上涨更有识别价值。',
        '用非龙头21日上涨比例、与更早21日窗口的变化、前期龙头领先差及二者正向交互；原模型自身动量和全行业宽度保持。',
        '即便加特征改善了树模型，也不代表模型按假设方向使用它；没有方向性和基本面证据时，只能称增量特征候选。'),
      'H3':('行业特有改善：区别于全市场反弹',
        '若信号来自行业自身变化，扣除过去估计的市场暴露后，残差强势和市场下跌日的相对韧性仍应提供增量。',
        '126日滚动beta至少63日样本、滞后一日；21日残差和63日市场下跌日残差均只用过去信息。目标仍为收益差，不改成回归alpha。',
        '一个市场beta不能排除规模、风格、流动性及行业自身风险溢价变化；风险溢价下降同样可能使价格上涨。'),
      'H4':('盈利共同改善：需求与经营杠杆的基本面证据',
        '若价格景气由需求恢复推动，应出现收入改善、利润率/盈利改善的公司覆盖面扩大，之后还应有现金流或库存周转验证。',
        '要求原始报告/更正版本、公告可得时间、历史成员映射，并按当时版本计算单季度指标；不能用今日修订后的历史值回填。',
        '目前EP30最新审核汇总仅15条财务事实、3个报告版本、5个字段，且为选定样例，不能支持全行业检验。价格结果不能替代这一证据。')}
    for h,(title,want,method,boundary) in descriptions.items():
        t=tests[tests.hypothesis.eq(h)]
        d=display.loc[t.index]
        s=summary[summary.model.eq(h)]
        result=verdict[h]['status']
        text=f'# {h} {title}\n\n想验证什么：{want}\n\n如何检验：{method}\n\n本轮结果：**{result}**。\n\n'
        if len(t):text+=md(d)+'\n'
        if len(s):
            text+='同样本固定模型的汇总：\n\n'+md(pd.DataFrame({'样本层':s.cohort,
                'Brier相对基线改善':s.relative_brier_improvement.map(lambda x:f'{x:+.2%}'),
                '前10%命中率':s.top10_precision.map(lambda x:f'{x:.2%}'),
                '提升倍数':s.top10_lift.map(lambda x:f'{x:.2f}')}))+'\n'
        text+='为什么不能直接下经济因果结论：'+boundary+'\n\n'
        text+='[全假设检验](../outputs/primary_tests.csv)；[逐频率/阈值/行业层级结果](../outputs/ablation_metrics.csv)；[年度结果](../outputs/annual_metrics.csv)。\n'
        (reports/f'{h}.md').write_text(text)
    text=('# EP32 V6：用经济学假设解释价格景气早期\n\n'
        '**结论：六项主检验均未通过预定标准，暂不能把“龙头先行—同业扩散”用作可靠的早期景气判定。** '
        'H3市场调整后的强势只有较小的平均误差改善，前10%候选的命中率下降，不能据此升级为可用信号。\n\n'
        '主假设：行业共同的需求或盈利预期改善可能逐步进入价格；较大公司先反映，随后同业扩散。'
        '竞争解释是行业共同风险、一般动量/反转，以及单纯市场反弹。该假设需要验证，不是预设结论。\n\n'
        '理论来自[Hong与Stein的信息渐进扩散模型](https://users.ssc.wisc.edu/~cengel/IMF/HongSteinJF1999.pdf)和'
        '[Hou的行业内领先滞后研究](https://papers.ssrn.com/abstract=463005)。'
        '[坏消息传播较慢的研究](https://www.nber.org/system/files/working_papers/w6553/w6553.pdf)提醒我们，'
        '负面信息的扩散不能直接证明利好也由龙头先行；本轮正负收益分开。其他市场的发现不作为A股结论。\n\n'
        '直接检验使用同业未来21日收益，避免把已经上涨当成领先证据；识别增量仍沿用V5的6—18个月景气、起点后前3个月标签。'
        '固定上一轮RD-Agent胜出模型的参数，每次只加一个预先指定特征组，未再搜索30轮挑最好结果。\n\n'+md(view)+'\n'
        '改善为正表示误差下降。命中率与提升倍数按日期、频率、阈值、基准和行业层级等权汇总；两个均值相除不一定等于平均提升倍数。'
        '这些是同样本对照，不能把剔除缺数据后的基线直接与V5全样本均值比较。\n\n'
        '表内相对改善是各任务相对值的均值；主检验另按市场月份等权计算绝对误差差，权重不同，接近零时可能异号。'
        'H1在两种汇总下都几乎没有改善，不应强调其中一个微小正值。\n\n'
        f'共同完整机制特征覆盖原可预测记录的{ratio:.1%}；市值排名或价格缺口保留为未知。'
        '另保留H3不依赖龙头排名的较宽样本结果，防止排名缺失驱动结论。旧版本结果未被改写。\n\n'
        '六项预定主检验采用同市场月份、连续三个月成块重抽样，并统一BH-FDR调整；表中Brier效应为绝对误差下降，'
        '机制效应为风险尺度归一化后的回归斜率，不能解释为策略收益。\n\n'+md(display)+'\n'
        '[H1 龙头先行](H1.md)；[H2 同业扩散](H2.md)；[H3 行业特有改善](H3.md)；[H4 盈利改善与数据缺口](H4.md)。\n\n'
        '经济学解释的边界：本轮最多检验价格层面的可观察含义，未完成需求、订单或盈利冲击的因果识别。'
        '同业先行、共同因子、流动性差异都可能造成相关性。即使某组有预测增量，也不能因此确认基本面景气。\n\n'
        '2024年起的历史已经被V5查看，本轮是机制引导的再次探索，不是新的独立holdout。'
        '未成熟标签不记负例，历史分类和股本known_at不足、复权价格推断仍使严格PIT为BLOCKED_DATA。\n\n'
        '底层历史从2017年开始，用于历史特征与训练；滚动评价从2024年开始。'
        '概率检验只有34个市场月份，领先滞后检验33个月，不能把大量重叠行业记录当作独立证据。'
        '尤其2026年共同样本合计70,980条已知标签中仅20条正例（不同频率、阈值、基准存在重复，并非20个独立事件），'
        '零命中不能解释成该年没有景气；近期指标受选择性标签成熟影响。'
        '2024年H3误差低于基线，2025年反而高于基线，改善也不具备跨年一致性。\n\n'
        '[完整固定方案](../research_plan.md)；[匹配样本比较](../outputs/matched_model_comparisons.csv)；'
        '[覆盖](../outputs/feature_coverage.csv)；[年度结果](../outputs/annual_metrics.csv)；'
        '[对照机制回归](../outputs/lead_lag_summary.csv)；[财务数据审计](../outputs/fundamental_audit.json)。\n')
    (reports/'economic_hypotheses.md').write_text(text)
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    d=tests[tests.test.str.endswith('brier_increment')]
    effect=d.effect.to_numpy()*10000;low=d.ci_low.to_numpy()*10000;high=d.ci_high.to_numpy()*10000
    ax.errorbar(effect,np.arange(len(d)),xerr=np.array([effect-low,high-effect]),fmt='o',capsize=4)
    ax.set_yticks(np.arange(len(d)),d.hypothesis);ax.axvline(0,color='gray',linestyle='--')
    ax.set(xlabel='Brier reduction vs matched baseline (x 1e-4)',title='Fixed economic hypotheses: 3-month block intervals')
    fig.savefig(reports/'brier_increments.png',dpi=150);plt.close(fig)
    with (reports/'economic_hypotheses.md').open('a') as h:h.write('\n![机制特征的增量与不确定区间](brier_increments.png)\n')
    (ROOT/'README.md').write_text('# EP32 V6\n\n[经济学假设与验证](reports/economic_hypotheses.md)。\n\n'
        '依次运行src/features6.py、src/mechanism6.py、src/evaluate6.py、src/statistics6.py、src/report6.py、src/validate6.py。'
        '模型沿用V5冻结RD-Agent参数，不重新搜索；大面板和预测保存在私有缓存economic_v6。\n')


if __name__=='__main__':build()
